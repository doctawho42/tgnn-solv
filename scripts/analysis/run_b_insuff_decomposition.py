#!/usr/bin/env python3
"""Reconstruct the closure--insufficiency decomposition (paper Table 2 / sec:measure).

The manuscript ``paper/grounding_paradox.tex`` reports a one-sided bound
decomposition of the *true-input* activity path (Prop.~\\ref{prop:decomp}):

    E[(m - g(z*))^2]  =  E[Var(m|z*)]   (B_insuff, input insufficiency)
                       + E[(E[m|z*] - g(z*))^2]  (B_closure, decoder mis-map)

with m = experimental infinite-dilution ln gamma_2 (IDAC, 298 K), z* the true
concatenated solute+solvent VT-2005 sigma-profile (2 x 51 = 102 dims), and
g(z*) the *fixed* (non-fitted) differentiable COSMO-SAC closure
(``tgnn_solv.layers.CosmoSacLayer``). Because a *fitted* E[m|z*] makes the cross
term non-zero, we report ONE-SIDED BOUNDS, not a point split:

  * B_closure >= (E[m] - E[g])^2                     (assumption-free Jensen)
  * B_insuff  <= E[Var(m | bin(g(z*))))]             (law of total variance)
  * B_insuff  ~  out-of-fold MSE of RF / Ridge m~z*  (upper, estimation error)
  * B_insuff  ~  kNN-in-z* difference estimator      (biased upward)
  * label noise sigma_eta^2 from IDAC inter-lab replicate spread.

Two conventions for g are reported: ``full`` = COSMO-SAC WITH the
Staverman-Guggenheim combinatorial term (a deterministic RDKit molar volume is
used for the size factor), and ``res`` = residual-only (the deployed default,
combinatorial term off). B_insuff (= E[Var(m|z*)]) depends only on (m, z*), so
the RF / Ridge / kNN estimates are convention-independent; MSE, Jensen and the
LOTV binning depend on g and are reported per convention.

NOTE ON PROVENANCE. The paper cited two files that were never committed
(``scratchpad/b_insuff_gate_out.json``, ``scratchpad/master_provenance.csv``)
and no tracked script computed them. This is that missing script, rebuilt from
tracked inputs only, so the table is reproducible from a clean clone.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_b_insuff_decomposition.py \
        --sigma-profiles results/sigma_profile_artifact/sigma_profiles.csv \
        --idac notebooks/data/raw/idac.csv \
        --out-json results/b_insuff/decomposition.json \
        --matched-csv results/b_insuff/matched_pairs.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

import sys

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

from tgnn_solv.data.utils import canonicalize  # noqa: E402
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402

RDLogger.DisableLog("rdApp.*")

N_BINS = 51
T_REF = 298.15
SEED = 0


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def load_sigma_profiles(csv_path: str):
    """Canonical SMILES -> (p_sigma[51], area). Mirrors tgnn_solv.sigma_oracle
    (the deployed sigma-oracle matcher): keyed by RDKit canonical SMILES."""
    df = pd.read_csv(csv_path)
    cols = [f"sigma_p_{i}" for i in range(N_BINS)]
    table: dict[str, tuple[np.ndarray, float]] = {}
    for rec in df.itertuples(index=False):
        d = rec._asdict()
        key = canonicalize(str(d.get("smiles", "")))
        if key is None or key in table:
            continue
        p = np.array([float(d[c]) for c in cols], dtype=float)
        table[key] = (p, float(d.get("sigma_area", p.sum())))
    return table


def _inchikey(smi: str):
    m = Chem.MolFromSmiles(str(smi))
    return Chem.MolToInchiKey(m) if m is not None else None


def match_pairs(idac_csv: str, table, temperature: float, tol: float) -> pd.DataFrame:
    """Return the (solute, solvent) pairs at ~298 K present in BOTH the IDAC
    labels and the sigma-profile table, matched by canonical SMILES (the
    deployed sigma-oracle rule). Replicate labels are averaged."""
    df = pd.read_csv(idac_csv, low_memory=False)
    df["T"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["m"] = pd.to_numeric(df["ln_gamma_inf"], errors="coerce")
    df = df[(df["T"] - temperature).abs() <= tol].dropna(subset=["m"]).copy()
    df["solute_key"] = df["solute_smiles"].map(lambda s: canonicalize(str(s)))
    df["solvent_key"] = df["solvent_smiles"].map(lambda s: canonicalize(str(s)))
    df = df.dropna(subset=["solute_key", "solvent_key"])
    df = df[df["solute_key"].isin(table) & df["solvent_key"].isin(table)]
    agg = (
        df.groupby(["solute_key", "solvent_key"], as_index=False)
        .agg(m=("m", "mean"), n_records=("m", "size"))
    )
    # attach one representative raw name/smiles per pair for the audit CSV
    first = df.drop_duplicates(["solute_key", "solvent_key"])
    meta = first.set_index(["solute_key", "solvent_key"])
    agg["solute_name"] = [meta.loc[(a, b), "solute_name"] if "solute_name" in meta else ""
                          for a, b in zip(agg["solute_key"], agg["solvent_key"])]
    agg["solvent_name"] = [meta.loc[(a, b), "solvent_name"] if "solvent_name" in meta else ""
                           for a, b in zip(agg["solute_key"], agg["solvent_key"])]
    return agg.sort_values(["solute_key", "solvent_key"]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Closure g(z*)
# --------------------------------------------------------------------------- #
def _mol_volume(smiles: str) -> float:
    """Deterministic RDKit molar volume [A^3/molecule] for the Staverman-
    Guggenheim size factor. Fixed embedding seed -> reproducible."""
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return float("nan")
    m = Chem.AddHs(m)
    if AllChem.EmbedMolecule(m, randomSeed=42) != 0:
        AllChem.EmbedMolecule(m, randomSeed=1, useRandomCoords=True)
    try:
        AllChem.MMFFOptimizeMolecule(m)
    except Exception:
        pass
    try:
        return float(AllChem.ComputeMolVolume(m))
    except Exception:
        return float("nan")


def evaluate_closure(pairs: pd.DataFrame, table, convention: str) -> np.ndarray:
    """g(z*) = CosmoSacLayer.ln_gamma_inf on the TRUE profiles, evaluated exactly
    as the model deploys it (eval mode, V=None for 'res', RDKit volume for 'full')."""
    layer = CosmoSacLayer(cfg=None)
    layer.eval()
    p2 = torch.tensor(np.stack([table[k][0] for k in pairs["solute_key"]]), dtype=torch.float)
    A2 = torch.tensor([table[k][1] for k in pairs["solute_key"]], dtype=torch.float)
    p1 = torch.tensor(np.stack([table[k][0] for k in pairs["solvent_key"]]), dtype=torch.float)
    A1 = torch.tensor([table[k][1] for k in pairs["solvent_key"]], dtype=torch.float)
    T = torch.full((len(pairs),), T_REF)
    if convention == "full":
        V2 = torch.tensor([_mol_volume(k) for k in pairs["solute_key"]], dtype=torch.float)
        V1 = torch.tensor([_mol_volume(k) for k in pairs["solvent_key"]], dtype=torch.float)
    else:
        V2 = V1 = None
    with torch.no_grad():
        g = layer.ln_gamma_inf(p2, p1, A2, A1, V2, V1, T)
    return g.numpy()


def z_star(pairs: pd.DataFrame, table) -> np.ndarray:
    """Concatenated true solute+solvent sigma-profiles (n, 102)."""
    return np.stack([
        np.concatenate([table[a][0], table[b][0]])
        for a, b in zip(pairs["solute_key"], pairs["solvent_key"])
    ])


# --------------------------------------------------------------------------- #
# Estimators
# --------------------------------------------------------------------------- #
def lotv_binning(g: np.ndarray, m: np.ndarray, n_bins: int) -> float:
    """B_insuff upper bound: E[Var(m | bin(g))] with equal-count bins (LOTV)."""
    q = np.quantile(g, np.linspace(0.0, 1.0, n_bins + 1))
    q[0] -= 1e-9
    q[-1] += 1e-9
    idx = np.digitize(g, q[1:-1])
    total = 0.0
    for b in range(n_bins):
        mm = m[idx == b]
        if len(mm) > 1:
            total += (len(mm) / len(m)) * float(mm.var(ddof=0))
    return total


def oof_predict(make_reg, Z: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Per-row out-of-fold predictions of m from z* (5-fold, fixed seed)."""
    kf = KFold(n_splits=5, shuffle=True, random_state=SEED)
    pred = np.zeros_like(m)
    for tr, te in kf.split(Z):
        reg = make_reg()
        reg.fit(Z[tr], m[tr])
        pred[te] = reg.predict(Z[te])
    return pred


def oof_var(make_reg, Z: np.ndarray, m: np.ndarray) -> float:
    """Out-of-fold residual MSE of a regressor m ~ z* -> upper estimate of
    E[Var(m|z*)] (E[Var]=oof MSE minus estimation error, so this is an upper bound)."""
    return float(np.mean((m - oof_predict(make_reg, Z, m)) ** 2))


def knn_var(Z: np.ndarray, m: np.ndarray, k: int = 1) -> float:
    """kNN-in-z* difference estimator of E[Var(m|z*)] (biased upward):
    0.5 * mean_i mean_{j in kNN(i)} (m_i - m_j)^2 on standardized z*."""
    Zs = StandardScaler().fit_transform(Z)
    nn = NearestNeighbors(n_neighbors=k + 1).fit(Zs)
    _, ind = nn.kneighbors(Zs)
    diffs = [np.mean([(m[i] - m[j]) ** 2 for j in ind[i][1:]]) for i in range(len(m))]
    return 0.5 * float(np.mean(diffs))


def label_noise(pairs: pd.DataFrame, idac_expanded_csv: str,
                temperature: float, tol: float) -> dict:
    """IDAC inter-lab replicate variance sigma_eta^2 for the matched pairs, read
    from the expanded IDAC aggregate (per-pair std across DOIs), if available."""
    p = Path(idac_expanded_csv)
    if not p.exists():
        return {"available": False, "reason": f"{idac_expanded_csv} not found"}
    exp = pd.read_csv(p, low_memory=False)
    exp["T"] = pd.to_numeric(exp["temperature"], errors="coerce")
    exp["solute_key"] = exp["solute_smiles"].map(lambda s: canonicalize(str(s)))
    exp["solvent_key"] = exp["solvent_smiles"].map(lambda s: canonicalize(str(s)))
    exp = exp[(exp["T"] - temperature).abs() <= tol]
    pairset = set(zip(pairs["solute_key"], pairs["solvent_key"]))
    exp = exp[[(a, b) in pairset for a, b in zip(exp["solute_key"], exp["solvent_key"])]]
    std = pd.to_numeric(exp.get("idac_ln_gamma_std"), errors="coerce").dropna()
    if len(std) == 0:
        return {"available": False, "reason": "no replicate std on matched pairs"}
    return {
        "available": True,
        "n_pairs_with_replicates": int((std > 0).sum()),
        "n_pairs_total": int(len(std)),
        "sigma_eta_sq_mean_var": float((std ** 2).mean()),
        "replicate_sd_mean": float(std.mean()),
        "replicate_sd_median": float(std.median()),
    }


# --------------------------------------------------------------------------- #
# Hedges (manuscript "four hedges we disclose")
# --------------------------------------------------------------------------- #
def hedge_between_solvent(m: np.ndarray, g: np.ndarray,
                          solvent: np.ndarray) -> dict:
    """HEDGE #2 (confound). Split the raw second moment of the closure error
    e = m - g into a between-solvent part (per-solvent mean offsets) and a
    within-solvent part:

        MSE = E[e^2] = E_i[ ebar_{s(i)}^2 ]  +  E_i[ (e_i - ebar_{s(i)})^2 ]
                        \\_______________/         \\____________________/
                        between (== solvent-        within-solvent residual
                        conditional Jensen lower     second moment
                        bound on B_closure)

    grouping by solvent coarsens z*, so within each solvent
    E[(E[m|z*]-g)^2 | s] >= (E[m|s]-E[g|s])^2 = ebar_s^2, hence
    B_closure >= E_s[ebar_s^2]. The raw plug-in E_i[ebar_{s(i)}^2] is biased
    *upward* for small per-solvent n (E[ebar_s^2] = mu_s^2 + sigma_s^2/n_s), so
    the reported LOWER bound subtracts the pooled-within finite-sample bias
    (ANOVA between-groups estimator): valid_lower = raw - n_solv*within/(n-n_solv).
    The between-solvent SHARE = raw / MSE is the confound magnitude."""
    df = pd.DataFrame({"e": m - g, "s": solvent})
    sbar = df.groupby("s")["e"].transform("mean").to_numpy()
    e = df["e"].to_numpy()
    n = len(e)
    n_solv = int(df["s"].nunique())
    mse = float(np.mean(e ** 2))
    between_raw = float(np.mean(sbar ** 2))       # E_i[(mean_s m - mean_s g)^2], biased up
    within = float(np.mean((e - sbar) ** 2))
    if n > n_solv:
        corrected = between_raw - n_solv * within / (n - n_solv)
    else:
        corrected = between_raw                   # all singletons: cannot debias
    # largest single-solvent stratum (manuscript cites pyridine ~ nearly correct)
    counts = df.groupby("s").size()
    big = counts.idxmax()
    big_e = df.loc[df["s"] == big, "e"].to_numpy()
    return {
        "mse_total": mse,
        "between_solvent_plugin": between_raw,        # biased upward
        "within_solvent": within,
        "between_solvent_share": between_raw / mse if mse > 0 else float("nan"),
        "solvent_conditional_jensen_lower": float(corrected),  # valid (debiased) B_closure lower bound
        "largest_solvent": str(big),
        "largest_solvent_n": int(counts.max()),
        "largest_solvent_stratum_mse": float(np.mean(big_e ** 2)),
    }


def _resample_stat(m, g, rf_sq, solvent, idx, lotv_bins):
    """(Jensen_global, B_insuff_RF, B_insuff_LOTV) on a resampled row index."""
    mm, gg, rr = m[idx], g[idx], rf_sq[idx]
    jensen = (mm.mean() - gg.mean()) ** 2
    b_rf = rr.mean()
    b_lotv = lotv_binning(gg, mm, lotv_bins)
    return jensen, b_rf, b_lotv


def hedge_ordering_confidence(m: np.ndarray, g: np.ndarray, rf_oof_pred: np.ndarray,
                              solvent: np.ndarray, lotv_bins: int,
                              n_boot: int = 2000) -> dict:
    """HEDGE #3 (confidence). Bootstrap P(B_closure > B_insuff) for the full
    convention, using the assumption-free Jensen lower bound for B_closure and
    the RF / LOTV upper bounds for B_insuff. Two resampling schemes:

      * cluster  : resample WHOLE solvents with replacement (respects the
                   between-solvent dependence -- the honest scheme);
      * iid_pair : resample pairs i.i.d. (ignores clustering -- optimistic).

    B_insuff_RF is the resample mean of the fixed full-sample per-row RF
    out-of-fold squared residual (a clean plug-in that avoids refit leakage);
    B_insuff_LOTV is recomputed on each resample."""
    rf_sq = (m - rf_oof_pred) ** 2
    solvents = np.unique(solvent)
    rows_by_solvent = {s: np.where(solvent == s)[0] for s in solvents}
    rng = np.random.RandomState(SEED)
    n = len(m)

    def run(cluster: bool) -> dict:
        gt_rf = gt_lotv = 0
        for _ in range(n_boot):
            if cluster:
                chosen = rng.choice(solvents, size=len(solvents), replace=True)
                idx = np.concatenate([rows_by_solvent[s] for s in chosen])
            else:
                idx = rng.randint(0, n, size=n)
            jen, b_rf, b_lotv = _resample_stat(m, g, rf_sq, solvent, idx, lotv_bins)
            gt_rf += int(jen > b_rf)
            gt_lotv += int(jen > b_lotv)
        return {"P_jensen_gt_rf": gt_rf / n_boot,
                "P_jensen_gt_lotv": gt_lotv / n_boot}

    return {
        "convention": "full",
        "n_boot": n_boot,
        "b_closure_jensen_lower_point": float((m.mean() - g.mean()) ** 2),
        "b_insuff_rf_point": float(rf_sq.mean()),
        "b_insuff_lotv_point": float(lotv_binning(g, m, lotv_bins)),
        "cluster_bootstrap_by_solvent": run(cluster=True),
        "iid_pair_bootstrap": run(cluster=False),
    }


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sigma-profiles", default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--idac", default="notebooks/data/raw/idac.csv")
    ap.add_argument("--idac-expanded", default="notebooks/data/raw/idac_expanded.csv",
                    help="Expanded IDAC aggregate with per-pair replicate std (for sigma_eta^2).")
    ap.add_argument("--out-json", default="results/b_insuff/decomposition.json")
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    ap.add_argument("--temperature", type=float, default=T_REF)
    ap.add_argument("--temperature-tol", type=float, default=1.0)
    ap.add_argument("--lotv-bins", type=int, default=8)
    ap.add_argument("--knn-k", type=int, default=1)
    ap.add_argument("--n-boot", type=int, default=2000,
                    help="Bootstrap resamples for the hedge #3 ordering confidence.")
    args = ap.parse_args()

    table = load_sigma_profiles(args.sigma_profiles)
    pairs = match_pairs(args.idac, table, args.temperature, args.temperature_tol)

    # diagnostic: InChIKey overlap count (tautomer-robust), which recovers the
    # formamide / N-methylformamide solvents the deployed canonical matcher misses.
    raw = pd.read_csv(args.idac, low_memory=False)
    raw["T"] = pd.to_numeric(raw["temperature"], errors="coerce")
    raw["m"] = pd.to_numeric(raw["ln_gamma_inf"], errors="coerce")
    raw = raw[(raw["T"] - args.temperature).abs() <= args.temperature_tol].dropna(subset=["m"])
    sig = pd.read_csv(args.sigma_profiles)
    sig_ik = {_inchikey(s) for s in sig["smiles"]}
    sig_ik.discard(None)
    ik_pairs = {
        (_inchikey(a), _inchikey(b))
        for a, b in zip(raw["solute_smiles"], raw["solvent_smiles"])
        if _inchikey(a) in sig_ik and _inchikey(b) in sig_ik
    }

    m = pairs["m"].to_numpy(dtype=float)
    Z = z_star(pairs, table)

    # convention-independent B_insuff estimates (depend only on m, z*)
    rf_pred = oof_predict(lambda: RandomForestRegressor(n_estimators=300, random_state=SEED), Z, m)
    rf = float(np.mean((m - rf_pred) ** 2))
    ridge = oof_var(lambda: Ridge(alpha=1.0), StandardScaler().fit_transform(Z), m)
    knn = knn_var(Z, m, k=args.knn_k)

    solvent = pairs["solvent_key"].to_numpy()
    conventions = {}
    g_by_conv = {}
    for conv in ("full", "res"):
        g = evaluate_closure(pairs, table, conv)
        g_by_conv[conv] = g
        mse = float(np.mean((m - g) ** 2))
        jensen = float((m.mean() - g.mean()) ** 2)
        lotv = lotv_binning(g, m, args.lotv_bins)
        conventions[conv] = {
            "mse_total": mse,
            "b_closure_jensen_lower": jensen,          # (E[m]-E[g])^2, assumption-free
            "b_insuff_lotv_upper": lotv,               # E[Var(m|bin g)]
            "b_closure_via_mse_minus_rf": mse - rf,    # MSE - B_insuff^upper
            "mean_g": float(g.mean()),
        }
        pairs[f"g_{conv}"] = g

    # Hedges (see the manuscript's "four hedges we disclose")
    hedges = {
        "hedge2_between_solvent_confound": {
            conv: hedge_between_solvent(m, g_by_conv[conv], solvent)
            for conv in ("full", "res")
        },
        "hedge3_ordering_confidence": hedge_ordering_confidence(
            m, g_by_conv["full"], rf_pred, solvent, args.lotv_bins,
            n_boot=args.n_boot),
    }

    noise = label_noise(pairs, args.idac_expanded,
                        args.temperature, args.temperature_tol)

    out = {
        "provenance": {
            "sigma_profiles": args.sigma_profiles,
            "idac": args.idac,
            "temperature_K": args.temperature,
            "temperature_tol_K": args.temperature_tol,
            "match_rule": "RDKit canonical SMILES on solute and solvent (deployed sigma-oracle rule)",
            "seed": SEED,
        },
        "n_pairs": int(len(pairs)),
        "n_solutes": int(pairs["solute_key"].nunique()),
        "n_solvents": int(pairs["solvent_key"].nunique()),
        "n_pairs_inchikey_match": len(ik_pairs),
        "n_solutes_inchikey": len({a for a, _ in ik_pairs}),
        "n_solvents_inchikey": len({b for _, b in ik_pairs}),
        "mean_m": float(m.mean()),
        "b_insuff_convention_independent": {
            "rf_oof_upper": rf,
            "ridge_oof_upper": ridge,
            "knn_in_zstar_biased_up": knn,
            "knn_k": args.knn_k,
        },
        "lotv_bins": args.lotv_bins,
        "conventions": conventions,
        "hedges": hedges,
        "label_noise_sigma_eta": noise,
    }

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.matched_csv).parent.mkdir(parents=True, exist_ok=True)
    pairs.to_csv(args.matched_csv, index=False)
    with open(args.out_json, "w") as f:
        json.dump(out, f, indent=2)

    print(json.dumps({k: out[k] for k in
                      ("n_pairs", "n_solutes", "n_solvents",
                       "b_insuff_convention_independent", "conventions",
                       "hedges")},
                     indent=2))


if __name__ == "__main__":
    main()
