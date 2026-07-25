#!/usr/bin/env python
"""Black-box Study 1a (confirmatory): is the crystal term Phi* decodable from h_BB?

Implements reports/PREREG_blackbox_AMENDMENT_2026-07-25.md, sections A3 and A4. The original
gate `R2(model) - R2(raw) >= 0.1` is NOT used: a measured permutation null fired it on 15-30%
of noise draws, and swapping one arbitrary RDKit descriptor set for another moved it by 1.8x
the whole bar. The rule here is on R2(model) alone against a solute-permutation null, and every
number is accompanied by the eight-item control ladder.

h_BB := `pair_input`, the tensor entering DirectGNN's prediction_head, captured with a
forward pre-hook (no module named *pair* exists; `cfg.pair_dim` is never read by DirectGNN).
Its dimension is MEASURED, not derived.

The null permutes molecule IDENTITY, not Phi* values: each solute is reassigned another
solute's (T_m, dH_fus) and Phi* is recomputed at its own temperatures. That preserves the
temperature structure and the between/within-solute variance split while destroying the
association with molecular identity -- which is what the probe claims to find.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/experiments/blackbox_study1a.py \
        --checkpoints checkpoints/e5_current_split/directgnn_seed4{2,3,4}.pt --n-perm 1000
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))

R_GAS = 8.314462618  # J/mol/K
# open_crystal_solute.csv stores dH_fus in J/mol (median 23 551, i.e. 23.5 kJ/mol -- the
# textbook range for organics), so no unit conversion. Verified, not assumed: a silent
# kJ/J mix-up would rescale Phi* by 1000 and is exactly the class of bug this repo has hit
# before with melting points in C vs K.
DH_SCALE = 1.0
ALPHAS = np.logspace(-1, 7, 25)
GO_R2 = 0.30          # from the measured null: p95 = +0.158, max over 200 draws = +0.267
GO_P = 0.01


# ----------------------------------------------------------------- oracle ----
def build_oracle(split_csv: Path, oracle_csv: Path) -> pd.DataFrame:
    """Supervised rows whose solute has measured T_m and dH_fus, restricted to T < T_m."""
    df = pd.read_csv(split_csv, low_memory=False)
    if "has_solubility" in df.columns:
        df = df[df["has_solubility"].astype(bool)]
    orc = pd.read_csv(oracle_csv, low_memory=False)
    # Use the OPEN merged columns flagged by has_open_crystal_both. The `_curated` columns are
    # the stale pre-expansion ones (32 / 31 non-null) and would silently shrink the oracle to a
    # handful of solutes -- the same stale-mask trap the amendment flags for the split CSVs.
    orc = orc[orc["has_open_crystal_both"].astype(bool)]
    # Rename before merging: the split CSVs carry their own T_m / dH_fus columns, and a silent
    # _x/_y collision would leave us reading the split's values instead of the oracle's.
    orc = (orc[["solute_smiles", "T_m", "dH_fus"]].dropna()
           .drop_duplicates("solute_smiles")
           .rename(columns={"T_m": "T_m_oracle", "dH_fus": "dH_fus_oracle"}))
    m = df.merge(orc, on="solute_smiles", how="inner")
    m = m[m["temperature"] < m["T_m_oracle"]].copy()
    m["phi_star"] = (m["dH_fus_oracle"].to_numpy() * DH_SCALE / R_GAS) * (
        1.0 / m["temperature"].to_numpy() - 1.0 / m["T_m_oracle"].to_numpy())
    return m


# --------------------------------------------------- representation h_BB ----
def extract_hbb(ckpt_path: Path, rows: pd.DataFrame, device) -> np.ndarray:
    """Capture the tensor entering prediction_head. Dimension is measured, not assumed."""
    # tgnn_solv.inference.load_model deliberately refuses DirectGNN checkpoints, so build the
    # baseline directly from its own stored config (the path scripts/train_directgnn.py uses).
    from tgnn_solv.baselines.direct_gnn import DirectGNN
    from tgnn_solv.config import TGNNSolvConfig
    from train import load_data

    ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    cfg = TGNNSolvConfig(**dict(ck["config"]))
    model = DirectGNN(cfg=cfg).to(device)
    state = ck.get("model_state_dict") or ck.get("model_state")
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        print(f"  load: {len(missing)} missing, {len(unexpected)} unexpected keys")
        if missing:
            raise SystemExit(f"DirectGNN state_dict incomplete: {missing[:5]}")
    model.eval()

    captured: list[torch.Tensor] = []

    def hook(_module, args):
        captured.append(args[0].detach().cpu())

    head = getattr(model, "prediction_head", None)
    if head is None:
        raise SystemExit("model has no prediction_head; cannot locate h_BB")
    handle = head.register_forward_pre_hook(hook)

    tmp = Path("/tmp/_bb_study1a_rows.csv")
    rows.to_csv(tmp, index=False)
    cfg.num_workers = 0
    loader = load_data(str(tmp), cfg, shuffle=False, seed=0, batch_size=64)

    with torch.no_grad():
        for sol, slv, tgt in loader:
            T = tgt["T"] if "T" in tgt else tgt.get("temperature")
            model(sol, slv, T,
                  solvent_type=tgt.get("solvent_type"),
                  solute_morgan_fp=tgt.get("solute_morgan_fp"),
                  solvent_morgan_fp=tgt.get("solvent_morgan_fp"),
                  solute_descriptors=tgt.get("solute_descriptors"),
                  solvent_descriptors=tgt.get("solvent_descriptors"))
    handle.remove()
    H = torch.cat(captured, 0).numpy()
    if len(H) != len(rows):
        raise SystemExit(f"h_BB rows {len(H)} != input rows {len(rows)}; loader dropped rows")
    return H


def rdkit_descriptors(smiles: list[str], which: str) -> np.ndarray:
    """Two deliberately different descriptor sets -- their spread IS the baseline's arbitrariness."""
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors

    SET_A = [Descriptors.MolWt, Descriptors.MolLogP, Descriptors.TPSA,
             Descriptors.NumHDonors, Descriptors.NumHAcceptors,
             Descriptors.NumRotatableBonds, Descriptors.RingCount,
             Descriptors.FractionCSP3, Descriptors.HeavyAtomCount,
             Descriptors.NumAromaticRings]
    SET_B = [Descriptors.BalabanJ, Descriptors.BertzCT, Descriptors.Chi0n,
             Descriptors.Chi1v, Descriptors.HallKierAlpha, Descriptors.Kappa2,
             Crippen.MolMR, rdMolDescriptors.CalcNumAmideBonds,
             Descriptors.MaxPartialCharge, Descriptors.MinPartialCharge]
    fns = SET_A if which == "A" else SET_B

    out = []
    for s in smiles:
        mol = Chem.MolFromSmiles(s)
        if mol is None:
            out.append([0.0] * len(fns))
            continue
        vals = []
        for f in fns:
            try:
                v = float(f(mol))
                vals.append(0.0 if not np.isfinite(v) else v)
            except Exception:
                vals.append(0.0)
        out.append(vals)
    return np.asarray(out, dtype=float)


# -------------------------------------------------------------- the probe ----
class RidgeSVD:
    """Ridge over a fixed alpha grid, sharing one SVD across every target and null draw."""

    def __init__(self, X: np.ndarray):
        self.mu = X.mean(0)
        self.sd = X.std(0)
        self.sd[self.sd < 1e-12] = 1.0
        Z = (X - self.mu) / self.sd
        self.U, self.s, self.Vt = np.linalg.svd(Z, full_matrices=False)

    def coefs(self, y: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
        yc = y.mean()
        d = self.s / (self.s ** 2 + alpha)
        w = self.Vt.T @ (d * (self.U.T @ (y - yc)))
        return w, yc

    def predict(self, X: np.ndarray, w: np.ndarray, yc: float) -> np.ndarray:
        return ((X - self.mu) / self.sd) @ w + yc


def r2(y: np.ndarray, p: np.ndarray) -> float:
    ss_res = float(((y - p) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


class CVPlan:
    """Grouped 5-fold CV by solute, with every SVD precomputed once.

    The design matrix is identical across the observed fit and all null draws -- only the
    target changes. Refactoring the SVDs out of the draw loop is what makes 1000 draws with
    per-draw alpha re-selection feasible at all (otherwise ~5000 SVDs of an 11000x788 matrix).
    The fold partition is held fixed across draws so the observed statistic and the null are
    computed under identical CV structure.
    """

    def __init__(self, X: np.ndarray, groups: np.ndarray, rng, n_folds: int = 5):
        X = np.ascontiguousarray(X, dtype=np.float32)
        uniq = np.unique(groups)
        folds = np.array_split(uniq[rng.permutation(len(uniq))], n_folds)
        self.parts = []
        for f in folds:
            te = np.isin(groups, f)
            tr = ~te
            if te.sum() == 0 or tr.sum() == 0:
                continue
            self.parts.append((RidgeSVD(X[tr]), tr, te, X[te]))
        self.full = RidgeSVD(X)

    def select_alpha(self, y: np.ndarray) -> float:
        scores = np.zeros(len(ALPHAS))
        for fit, tr, te, Xte in self.parts:
            # U.T @ y does not depend on alpha, so hoist it out of the alpha loop -- it is the
            # dominant cost (a 788 x n_train pass per evaluation) and repeating it 25 times per
            # fold made the 1000-draw null roughly an order of magnitude slower than necessary.
            ytr = y[tr]
            yc = float(ytr.mean())
            Uty = fit.U.T @ (ytr - yc)
            Zte = (Xte - fit.mu) / fit.sd
            for i, a in enumerate(ALPHAS):
                w = fit.Vt.T @ ((fit.s / (fit.s ** 2 + a)) * Uty)
                scores[i] += r2(y[te], Zte @ w + yc)
        return float(ALPHAS[int(np.argmax(scores))])

    def score(self, y: np.ndarray, Xh: np.ndarray, yh: np.ndarray) -> tuple[float, float]:
        a = self.select_alpha(y)
        w, yc = self.full.coefs(y, a)
        return r2(yh, self.full.predict(Xh, w, yc)), a


def fit_score(Xf, yf, gf, Xh, yh, rng) -> tuple[float, float]:
    return CVPlan(Xf, gf, rng).score(yf, np.ascontiguousarray(Xh, dtype=np.float32), yh)


# ------------------------------------------------------------------- main ----
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoints", nargs="+", required=True)
    ap.add_argument("--oracle", default="results/open_crystal_artifact/open_crystal_solute.csv")
    ap.add_argument("--data-dir", default="notebooks/data/processed")
    ap.add_argument("--n-perm", type=int, default=1000)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    device = torch.device(args.device)
    dd = _REPO / args.data_dir
    oracle = _REPO / args.oracle

    fit_rows = build_oracle(dd / "train.csv", oracle)
    ho_rows = pd.concat([build_oracle(dd / "val.csv", oracle),
                         build_oracle(dd / "test.csv", oracle)], ignore_index=True)
    print(f"fit   : {fit_rows.solute_smiles.nunique()} solutes / {len(fit_rows)} rows")
    print(f"holdout: {ho_rows.solute_smiles.nunique()} solutes / {len(ho_rows)} rows")

    leak = set(ho_rows.solute_smiles) & set(fit_rows.solute_smiles)
    print(f"solute overlap fit/holdout (must be 0): {len(leak)}")
    if leak:
        raise SystemExit("held-out solutes appear in the fit split -- aborting")

    yf = fit_rows["phi_star"].to_numpy()
    yh = ho_rows["phi_star"].to_numpy()
    gf = fit_rows["solute_smiles"].to_numpy()
    gh = ho_rows["solute_smiles"].to_numpy()
    ho_solutes = np.unique(gh)

    between = 1.0 - (ho_rows.groupby("solute_smiles")["phi_star"].transform("mean")
                     .sub(ho_rows["phi_star"]).var() / ho_rows["phi_star"].var())
    print(f"Phi* between-solute variance share (holdout): {between:.3f}")
    print(f"effective n = {len(ho_solutes)} clusters, not {len(yh)} rows")

    results = {"fit_solutes": int(fit_rows.solute_smiles.nunique()),
               "holdout_solutes": int(len(ho_solutes)),
               "holdout_rows": int(len(yh)),
               "between_solute_var_share": float(between),
               "n_perm": args.n_perm, "seeds": {}}

    # ---- raw-feature baselines (levels, never subtrahends) and constant control ----
    rng = np.random.default_rng(0)
    raws = {}
    for which in ("A", "B"):
        Xf_r = rdkit_descriptors(list(fit_rows.solute_smiles), which)
        Xh_r = rdkit_descriptors(list(ho_rows.solute_smiles), which)
        Xf_r = np.column_stack([Xf_r, 1.0 / fit_rows["temperature"].to_numpy()])
        Xh_r = np.column_stack([Xh_r, 1.0 / ho_rows["temperature"].to_numpy()])
        raws[which] = fit_score(Xf_r, yf, gf, Xh_r, yh, rng)[0]
    const_r2 = r2(yh, np.full_like(yh, yf.mean()))
    print(f"\nraw descriptor set A: R2 = {raws['A']:+.4f}")
    print(f"raw descriptor set B: R2 = {raws['B']:+.4f}"
          f"   (spread {abs(raws['A']-raws['B']):.4f} = baseline arbitrariness)")
    print(f"molecule-blind constant: R2 = {const_r2:+.4f}")
    results["raw_A"], results["raw_B"], results["constant"] = raws["A"], raws["B"], const_r2

    # ---- per-seed model probe ----
    tm = dict(zip(fit_rows.solute_smiles, zip(fit_rows.T_m_oracle, fit_rows.dH_fus_oracle)))
    tm.update(dict(zip(ho_rows.solute_smiles, zip(ho_rows.T_m_oracle, ho_rows.dH_fus_oracle))))
    all_solutes = list(tm)

    for ck in args.checkpoints:
        ck = Path(ck)
        print(f"\n=== {ck.name} ===")
        Hf = extract_hbb(ck, fit_rows, device)
        Hh = extract_hbb(ck, ho_rows, device)
        print(f"h_BB measured dimension: {Hf.shape[1]}")

        Hh32 = np.ascontiguousarray(Hh, dtype=np.float32)
        plan = CVPlan(Hf, gf, np.random.default_rng(0))
        obs, alpha = plan.score(yf, Hh32, yh)
        print(f"held-out R2(model) = {obs:+.4f}   (alpha {alpha:g})")

        # Identity-permutation null: give each solute ANOTHER solute's (T_m, dH_fus) and
        # recompute Phi* at its own temperatures. This preserves the temperature structure and
        # the between/within-solute variance split, destroying only molecular identity.
        Tf = fit_rows["temperature"].to_numpy()
        Th = ho_rows["temperature"].to_numpy()
        Tm_arr = np.array([tm[s][0] for s in all_solutes])
        dh_arr = np.array([tm[s][1] for s in all_solutes]) * 1000.0 / R_GAS
        idx_f = np.array([all_solutes.index(s) for s in gf])
        idx_h = np.array([all_solutes.index(s) for s in gh])

        null = []
        for d in range(args.n_perm):
            perm = np.random.default_rng(1000 + d).permutation(len(all_solutes))
            yf_p = dh_arr[perm][idx_f] * (1.0 / Tf - 1.0 / Tm_arr[perm][idx_f])
            yh_p = dh_arr[perm][idx_h] * (1.0 / Th - 1.0 / Tm_arr[perm][idx_h])
            null.append(plan.score(yf_p, Hh32, yh_p)[0])
        null = np.array(null)
        p = float((null >= obs).mean())
        print(f"permutation null: p = {p:.4f}  median {np.median(null):+.4f} "
              f" p95 {np.percentile(null, 95):+.4f}  max {null.max():+.4f}")

        # drop-one-solute jackknife over held-out clusters (one fit, re-scored per exclusion)
        w, yc = plan.full.coefs(yf, alpha)
        pred_h = plan.full.predict(Hh32, w, yc)
        jk = np.array([r2(yh[gh != s], pred_h[gh != s]) for s in ho_solutes])
        flips = int((np.sign(jk) != np.sign(obs)).sum())
        print(f"jackknife R2 range [{jk.min():+.4f}, {jk.max():+.4f}]  sign flips {flips}/{len(jk)}")

        # leverage
        sse = (yh - pred_h) ** 2
        by = pd.Series(sse).groupby(gh).sum().sort_values(ascending=False)
        top1, top3 = by.iloc[0] / by.sum(), by.iloc[:3].sum() / by.sum()
        print(f"leverage: top solute {top1:.1%} of SSE, top-3 {top3:.1%}")

        # random-target selectivity
        rt = fit_score(Hf, np.random.default_rng(7).normal(size=len(yf)), gf,
                       Hh, np.random.default_rng(8).normal(size=len(yh)),
                       np.random.default_rng(9))[0]
        print(f"random-target selectivity control: R2 = {rt:+.4f}")

        verdict = ("GO" if (obs >= GO_R2 and p <= GO_P and jk.min() > 0)
                   else "KILL (not distinguishable from chance at this n)")
        print(f"VERDICT: {verdict}")

        results["seeds"][ck.name] = {
            "hbb_dim": int(Hf.shape[1]), "r2_model": obs, "alpha": alpha,
            "perm_p": p, "null_median": float(np.median(null)),
            "null_p95": float(np.percentile(null, 95)), "null_max": float(null.max()),
            "jk_min": float(jk.min()), "jk_max": float(jk.max()), "sign_flips": flips,
            "leverage_top1": float(top1), "leverage_top3": float(top3),
            "random_target_r2": rt, "verdict": verdict,
        }

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(results, indent=2))
        print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
