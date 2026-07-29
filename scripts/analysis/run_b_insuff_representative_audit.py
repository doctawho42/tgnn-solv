#!/usr/bin/env python3
"""Round-2 audit of the representative-set (n=477) decomposition.

Answers, with numbers, the questions the referee raised about the set that now carries the
closure-dominance verdict:

  (1) CONDITIONING VARIABLE.  The closure is evaluated at each row's own temperature, so
      g = g(z*, T).  This script therefore states and audits the conditioning variable
      (z*, T): the number of DISTINCT solute-solvent pairs among the 477 rows, the
      rows-per-pair distribution, dim((z*,T))/n and dim/(distinct pairs), and -- most
      directly -- the PAIR-COARSENING bound E[Var(m | pair)], which is a valid upper bound
      on E[Var(m | z*, T)] because pair identity is coarser than (z*, T), and which needs
      no binning at all.  It also re-runs the out-of-fold estimators with folds BLOCKED on
      the molecule pair, which removes the near-twin (same pair, neighbouring T) leakage.

  (2) PROVENANCE OF THE EXPANDED PULL.  Method mix, DOI and journal composition of the 477
      rows; the margin re-estimated on the gas-chromatography-only subset (the cut that
      inverted the enlarged corner in Limitation (i)); and a DOI-clustered bootstrap of the
      margin, so that the source clustering the corner cannot support is supplied here.

  (3) THE FIDELITY-LEVER REVERSAL.  The 2002-vs-2010(dispersion off) contrast restricted to
      the 57 corner pairs that sit inside the representative set at 298 K, and on the
      complementary 420 rows, so that the profile-database factor is separated from the
      chemistry/temperature-coverage factor.

  (4) THE CORNER FLOOR CHECK, SAME-DATABASE.  The LOTV bound on the 60 corner molecule pairs
      computed with z* = the UD profile pair, so that the fair-2002 UD MSE (1.757) can be
      charged against a floor measured on the UD profiles rather than against the VT-2005
      floor of Table 2.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_representative_audit.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, RDLogger
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, KFold

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer, CosmoSac2010Layer  # noqa: E402

UD = Path.home() / "COSMOSAC" / "profiles" / "UD"
IDAC = ROOT / "notebooks" / "data" / "raw" / "idac_expanded.csv"
IDAC_RAW = ROOT / "notebooks" / "data" / "raw" / "idac_expanded_raw.csv"
MATCHED = ROOT / "results" / "b_insuff" / "matched_pairs.csv"
OUT = ROOT / "results" / "b_insuff" / "representative_audit.json"


# --------------------------------------------------------------------------- helpers
def _resolver():
    exact, by14 = {}, {}
    for ln in (UD / "complist.txt").read_text().splitlines()[1:]:
        t = ln.split()
        if len(t) < 5:
            continue
        ik = t[-1]
        exact[ik] = ik
        by14.setdefault(ik.split("-")[0], ik)

    def resolve(smi):
        mol = Chem.MolFromSmiles(str(smi))
        if mol is None:
            return None
        k = Chem.MolToInchiKey(mol)
        return exact.get(k) or by14.get(k.split("-")[0])
    return resolve


def _parse(path):
    meta, vals = {}, []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.startswith("# meta:"):
            meta = json.loads(line[len("# meta:"):].strip())
        elif line and not line.startswith("#"):
            vals.append(float(line.split()[1]))
    p = np.asarray(vals, float)
    return (p, float(p.sum()), float(meta.get("volume [A^3]") or 0.0),
            float(meta.get("disp. e/kB [K]") or 0.0))


def _profiles(su, sv):
    f = [UD / "sigma" / f"{su}.sigma", UD / "sigma" / f"{sv}.sigma",
         UD / "sigma3" / f"{su}.sigma", UD / "sigma3" / f"{sv}.sigma"]
    if not all(x.exists() for x in f):
        return None
    pu_s, Au_s, _, _ = _parse(f[0])
    pu_v, Au_v, _, _ = _parse(f[1])
    pt_s, At_s, V_s, eps_s = _parse(f[2])
    pt_v, At_v, V_v, eps_v = _parse(f[3])
    if pu_s.size != 51 or pu_v.size != 51 or pt_s.size != 153 or pt_v.size != 153:
        return None
    return dict(pu_s=pu_s, pu_v=pu_v, Au_s=Au_s, Au_v=Au_v, pt_s=pt_s, pt_v=pt_v,
                At_s=At_s, At_v=At_v, V_s=V_s, V_v=V_v, eps_s=eps_s, eps_v=eps_v)


def lotv(g, m, n_bins, ddof):
    q = np.quantile(g, np.linspace(0.0, 1.0, n_bins + 1))
    q[0] -= 1e-9
    q[-1] += 1e-9
    idx = np.digitize(g, q[1:-1])
    tot = 0.0
    for b in range(n_bins):
        mm = m[idx == b]
        if len(mm) > ddof:
            tot += (len(mm) / len(m)) * float(mm.var(ddof=ddof))
    return tot


def group_coarsen_bound(m, groups, ddof):
    """E[Var(m | group)] -- a valid upper bound on E[Var(m | z*,T)] when `group` is a
    coarsening of (z*,T).  Singleton groups contribute zero mass at ddof=1."""
    tot, mass = 0.0, 0
    for g in np.unique(groups):
        mm = m[groups == g]
        if len(mm) > ddof:
            tot += len(mm) * float(mm.var(ddof=ddof))
            mass += len(mm)
    return tot / len(m), mass


def two_way(vals, su, sv, n_boot=4000, seed=0):
    rng = np.random.default_rng(seed)
    U, V = np.unique(su), np.unique(sv)
    iu = {s: i for i, s in enumerate(U)}
    iv = {s: i for i, s in enumerate(V)}
    isu = np.array([iu[s] for s in su])
    isv = np.array([iv[s] for s in sv])
    out = []
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, len(U), len(U)), minlength=len(U))
        cv = np.bincount(rng.integers(0, len(V), len(V)), minlength=len(V))
        w = cs[isu] * cv[isv]
        if w.sum() == 0:
            continue
        out.append(float(np.sum(w * vals) / np.sum(w)))
    out = np.array(out)
    return float(np.mean(out > 0)), [float(np.percentile(out, 5)), float(np.percentile(out, 95))]


def two_way_margin(g, m, su, sv, n_bins, ddof, n_boot=3000, seed=0):
    rng = np.random.default_rng(seed)
    U, V = np.unique(su), np.unique(sv)
    iu = {s: i for i, s in enumerate(U)}
    iv = {s: i for i, s in enumerate(V)}
    isu = np.array([iu[s] for s in su])
    isv = np.array([iv[s] for s in sv])
    out = []
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, len(U), len(U)), minlength=len(U))
        cv = np.bincount(rng.integers(0, len(V), len(V)), minlength=len(V))
        w = cs[isu] * cv[isv]
        if w.sum() < 30:
            continue
        idx = np.repeat(np.arange(len(m)), w)
        mm, gg = m[idx], g[idx]
        out.append(float(np.mean((mm - gg) ** 2)) - 2 * lotv(gg, mm, n_bins, ddof))
    out = np.array(out)
    return float(np.mean(out > 0)), [float(np.percentile(out, 5)), float(np.percentile(out, 95))]


def cluster_margin(g, m, clusters, n_bins, ddof, n_boot=3000, seed=0):
    """One-way cluster bootstrap of the margin over an arbitrary clustering (e.g. source DOI)."""
    rng = np.random.default_rng(seed)
    C = np.unique(clusters)
    idx_by_c = {c: np.where(clusters == c)[0] for c in C}
    out = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(C), len(C))
        idx = np.concatenate([idx_by_c[C[p]] for p in pick])
        if len(idx) < 30:
            continue
        mm, gg = m[idx], g[idx]
        out.append(float(np.mean((mm - gg) ** 2)) - 2 * lotv(gg, mm, n_bins, ddof))
    out = np.array(out)
    return float(np.mean(out > 0)), [float(np.percentile(out, 5)), float(np.percentile(out, 95))]


# --------------------------------------------------------------------------- main
def main() -> int:
    resolve = _resolver()
    idac = pd.read_csv(IDAC, low_memory=False)
    idac["Tn"] = pd.to_numeric(idac["temperature"], errors="coerce")
    idac = idac.dropna(subset=["ln_gamma_inf", "Tn"]).copy()
    idac["su"] = idac["solute_smiles"].map(resolve)
    idac["sv"] = idac["solvent_smiles"].map(resolve)
    idac = idac.dropna(subset=["su", "sv"])

    # measurement method: join the aggregated pull back onto the raw extraction, which
    # carries ThermoML's own `method` field.
    raw = pd.read_csv(IDAC_RAW, low_memory=False)
    raw["Tn"] = pd.to_numeric(raw["temperature"], errors="coerce")
    key = ["solute_smiles", "solvent_smiles", "Tn"]
    meth = (raw.dropna(subset=["Tn"]).groupby(key)["method"]
               .agg(lambda s: s.dropna().iloc[0] if s.notna().any() else "unreported"))
    jour = (raw.dropna(subset=["Tn"]).groupby(key)["journal"]
               .agg(lambda s: s.dropna().iloc[0] if s.notna().any() else "unreported"))
    idac["method"] = [meth.get((a, b, round(float(t), 10)), meth.get((a, b, t), "unreported"))
                      for a, b, t in zip(idac.solute_smiles, idac.solvent_smiles, idac.Tn)]
    idac["journal"] = [jour.get((a, b, round(float(t), 10)), jour.get((a, b, t), "unreported"))
                       for a, b, t in zip(idac.solute_smiles, idac.solvent_smiles, idac.Tn)]

    by_T = {}
    for _, r in idac.iterrows():
        pr = _profiles(r["su"], r["sv"])
        if pr is None or pr["eps_s"] == 0 or pr["eps_v"] == 0:
            continue
        by_T.setdefault(round(float(r["Tn"]), 2), []).append(
            {**pr, "su": r["su"], "sv": r["sv"], "m": float(r["ln_gamma_inf"]),
             "T": float(r["Tn"]), "doi": str(r["idac_source_dois"]),
             "method": str(r["method"]), "journal": str(r["journal"])})

    l02 = CosmoSacLayer().double().eval(); l02.n_iter_eval = 300
    l10 = CosmoSac2010Layer().double().eval(); l10.n_iter_eval = 300
    st = lambda recs, k: torch.tensor(np.asarray([r[k] for r in recs]), dtype=torch.float64)

    flat, g02f, g02r, g10f = [], [], [], []
    for Tval, recs in by_T.items():
        T = torch.full((len(recs),), Tval, dtype=torch.float64)
        with torch.no_grad():
            a = l02.ln_gamma_inf(st(recs, "pu_s"), st(recs, "pu_v"), st(recs, "Au_s"),
                                 st(recs, "Au_v"), st(recs, "V_s"), st(recs, "V_v"), T).numpy()
            ar = l02.ln_gamma_inf(st(recs, "pu_s"), st(recs, "pu_v"), st(recs, "Au_s"),
                                  st(recs, "Au_v"), None, None, T).numpy()
            l10.use_dispersion = False
            b = l10.ln_gamma_inf(st(recs, "pt_s"), st(recs, "pt_v"), st(recs, "At_s"),
                                 st(recs, "At_v"), st(recs, "V_s"), st(recs, "V_v"), T).numpy()
        g02f += list(a); g02r += list(ar); g10f += list(b); flat += recs

    m = np.array([r["m"] for r in flat])
    su = np.array([r["su"] for r in flat]); sv = np.array([r["sv"] for r in flat])
    Ts = np.array([r["T"] for r in flat])
    doi = np.array([r["doi"] for r in flat])
    method = np.array([r["method"] for r in flat])
    journal = np.array([r["journal"] for r in flat])
    g02f, g02r, g10f = map(np.array, (g02f, g02r, g10f))
    zstar = np.stack([np.concatenate([r["pu_s"], r["pu_v"]]) for r in flat])
    pair = np.array([f"{a}|{b}" for a, b in zip(su, sv)])

    mse_f = float(np.mean((g02f - m) ** 2))
    mse_r = float(np.mean((g02r - m) ** 2))
    out = {"n": len(m), "mse_2002_full": round(mse_f, 4), "mse_2002_res": round(mse_r, 4),
           "var_m": round(float(m.var(ddof=0)), 4)}

    # ------------------------------------------------ (1) conditioning variable & design
    cnt = Counter(pair)
    sizes = np.array(sorted(cnt.values(), reverse=True))
    out["design"] = {
        "n_distinct_pairs": int(len(cnt)),
        "dim_zstar": int(zstar.shape[1]),
        "dim_zstar_plus_T": int(zstar.shape[1] + 1),
        "dim_over_n_rows": round((zstar.shape[1] + 1) / len(m), 3),
        "dim_over_n_distinct_pairs": round((zstar.shape[1] + 1) / len(cnt), 3),
        "rows_per_pair": {"max": int(sizes.max()), "median": float(np.median(sizes)),
                          "mean": round(float(sizes.mean()), 2),
                          "n_pairs_with_1_row": int((sizes == 1).sum()),
                          "n_pairs_with_ge5_rows": int((sizes >= 5).sum()),
                          "rows_in_multirow_pairs": int(sizes[sizes > 1].sum())},
        "n_distinct_T": int(len(set(np.round(Ts, 2)))),
        "T_range_K": [float(Ts.min()), float(Ts.max())],
        "closure_evaluated_at_each_rows_own_T": True,
    }

    # How much of m's spread lives on the temperature axis at a fixed profile pair.  Pair identity
    # is a coarsening of (z*,T), so this is the within-pair variance the conditioning change could
    # possibly move; it is NOT itself a bound over the whole set, because singleton pairs (118 of
    # 185) carry no estimate and are entered as zero.
    b_pair_be, mass_be = group_coarsen_bound(m, pair, ddof=1)
    out["within_pair_variance_across_T"] = {
        "rows_in_multirow_pairs": int(mass_be),
        "mean_within_pair_var_over_those_rows": round(b_pair_be * len(m) / max(mass_be, 1), 4),
        "as_a_share_of_Var_m": round((b_pair_be * len(m) / max(mass_be, 1))
                                     / float(m.var(ddof=0)), 4),
    }

    # out-of-fold estimators with folds blocked on the molecule pair
    def oof(make, groups=None):
        p = np.zeros_like(m)
        if groups is None:
            splitter = KFold(5, shuffle=True, random_state=0).split(zstar)
        else:
            splitter = GroupKFold(5).split(zstar, m, groups)
        for tr, te in splitter:
            r = make(); r.fit(zstar[tr], m[tr]); p[te] = r.predict(zstar[te])
        return round(float(np.mean((m - p) ** 2)), 4)

    zt = np.column_stack([zstar, Ts])

    def oof_zt(make, groups):
        p = np.zeros_like(m)
        for tr, te in GroupKFold(5).split(zt, m, groups):
            r = make(); r.fit(zt[tr], m[tr]); p[te] = r.predict(zt[te])
        return round(float(np.mean((m - p) ** 2)), 4)

    rf = lambda: RandomForestRegressor(n_estimators=400, random_state=0, n_jobs=-1)
    rg = lambda: Ridge(alpha=1.0)
    out["oof_estimators"] = {
        "rf_random_folds": oof(rf), "ridge_random_folds": oof(rg),
        "rf_folds_blocked_on_pair": oof(rf, pair), "ridge_folds_blocked_on_pair": oof(rg, pair),
        "rf_blocked_on_pair_zstar_plus_T": oof_zt(rf, pair),
        "rf_folds_blocked_on_solute": oof(rf, su),
        "threshold_mse_over_2_full": round(mse_f / 2, 4),
    }

    # ------------------------------------------------ (2) provenance of the expanded pull
    out["provenance_of_the_477"] = {
        "method_mix": {k: int(v) for k, v in Counter(method).most_common()},
        "n_distinct_dois": int(len(set(doi))),
        "largest_doi_share_rows": int(Counter(doi).most_common(1)[0][1]),
        "journals": {k: int(v) for k, v in Counter(journal).most_common()},
    }
    gc = np.array([str(x).startswith("Chromatography") for x in method])
    if gc.sum() > 30:
        mse_gc = float(np.mean((g02f[gc] - m[gc]) ** 2))
        b_gc = lotv(g02f[gc], m[gc], 8, 1)
        P_gc, ci_gc = two_way_margin(g02f[gc], m[gc], su[gc], sv[gc], 8, 1)
        out["gas_chromatography_only"] = {
            "n": int(gc.sum()), "mse_2002_full": round(mse_gc, 4),
            "b_insuff_up_8bins_Bessel": round(b_gc, 4),
            "margin": round(mse_gc - 2 * b_gc, 4),
            "P_margin_positive_two_way": round(P_gc, 3),
            "ci90": [round(c, 3) for c in ci_gc],
        }
    nongc = ~gc
    if nongc.sum() > 0:
        out["non_chromatography_rows"] = {
            "n": int(nongc.sum()),
            "methods": {k: int(v) for k, v in Counter(method[nongc]).most_common()},
        }
    P_doi, ci_doi = cluster_margin(g02f, m, doi, 8, 1)
    out["margin_bootstrap_clustered_on_source_doi"] = {
        "n_clusters": int(len(set(doi))), "P_positive": round(P_doi, 3),
        "ci90": [round(c, 3) for c in ci_doi]}
    P_pair, ci_pair = cluster_margin(g02f, m, pair, 8, 1)
    out["margin_bootstrap_clustered_on_molecule_pair"] = {
        "n_clusters": int(len(cnt)), "P_positive": round(P_pair, 3),
        "ci90": [round(c, 3) for c in ci_pair]}

    # collapse to one row per distinct pair: the design-point view of the same verdict
    keep = []
    for p in np.unique(pair):
        w = np.where(pair == p)[0]
        keep.append(w[np.argmin(np.abs(Ts[w] - 298.15))])
    keep = np.array(sorted(keep))
    mc_, gc_ = m[keep], g02f[keep]
    mse_c = float(np.mean((gc_ - mc_) ** 2))
    coll = {"n": int(len(keep)), "mse_2002_full": round(mse_c, 4),
            "var_m": round(float(mc_.var(ddof=0)), 4)}
    for nb in (5, 8, 10):
        b = lotv(gc_, mc_, nb, 1)
        coll[f"{nb}bins_Bessel"] = {"b_insuff_up": round(b, 4), "margin": round(mse_c - 2 * b, 4)}
    Pc, cic = two_way_margin(gc_, mc_, su[keep], sv[keep], 8, 1)
    coll["P_margin_positive_two_way_8bins_Bessel"] = round(Pc, 3)
    coll["ci90"] = [round(c, 3) for c in cic]
    out["collapsed_to_one_row_per_distinct_pair"] = coll

    # the modern kernel's floor on ITS OWN typed latent, on the representative set
    mse10 = float(np.mean((g10f - m) ** 2))
    own10 = {"mse_2010_dspoff_full": round(mse10, 4)}
    for nb in (5, 8, 16):
        for ddof, lab in ((0, "ML"), (1, "Bessel")):
            b = lotv(g10f, m, nb, ddof)
            own10[f"{nb}bins_{lab}"] = {"b_insuff_up": round(b, 4),
                                        "b_clos_lb": round(mse10 - b, 4),
                                        "margin": round(mse10 - 2 * b, 4)}
    P10m, ci10m = two_way_margin(g10f, m, su, sv, 8, 1)
    own10["P_margin_positive_two_way_8bins_Bessel"] = round(P10m, 3)
    own10["ci90"] = [round(c, 3) for c in ci10m]
    out["representative_2010_on_its_own_typed_latent"] = own10

    # ------------------------------------------------ (3) the fidelity-lever reversal
    corner = pd.read_csv(MATCHED)
    cres = {(resolve(a), resolve(b)) for a, b in zip(corner.solute_key, corner.solvent_key)}
    shared = np.array([(a, b) in cres and abs(t - 298.15) <= 1.0
                       for a, b, t in zip(su, sv, Ts)])
    d = (g02f - m) ** 2 - (g10f - m) ** 2      # positive => 2010 better
    near298 = np.abs(Ts - 298.15) <= 1.0
    blocks = {}
    for lab, mask in (("shared_57_rows", shared), ("complement_420_rows", ~shared),
                      ("complement_rows_at_298K", (~shared) & near298),
                      ("complement_rows_off_298K", (~shared) & (~near298)),
                      ("all_477", np.ones(len(m), bool))):
        if mask.sum() < 5:
            continue
        P, ci = two_way(d[mask], su[mask], sv[mask])
        blocks[lab] = {
            "n": int(mask.sum()),
            "mse_2002_full": round(float(np.mean((g02f[mask] - m[mask]) ** 2)), 4),
            "mse_2010_dspoff_full": round(float(np.mean((g10f[mask] - m[mask]) ** 2)), 4),
            "delta_2002_minus_2010": round(float(np.mean(d[mask])), 4),
            "P_2010_better": round(P, 3), "ci90_delta": [round(c, 3) for c in ci],
        }
    # the same 57 chemistries at 298 K but on VT-2005 profiles, for reference
    out["fidelity_lever_by_block"] = blocks

    # ------------------------------------------------ (4) corner floor on the UD profiles
    crecs = []
    for _, r in corner.iterrows():
        a, b = resolve(r["solute_key"]), resolve(r["solvent_key"])
        if a is None or b is None:
            continue
        pr = _profiles(a, b)
        if pr is None:
            continue
        crecs.append({**pr, "su": a, "sv": b, "m": float(r["m"])})
    T = torch.full((len(crecs),), 298.15, dtype=torch.float64)
    with torch.no_grad():
        cg_f = l02.ln_gamma_inf(st(crecs, "pu_s"), st(crecs, "pu_v"), st(crecs, "Au_s"),
                                st(crecs, "Au_v"), st(crecs, "V_s"), st(crecs, "V_v"), T).numpy()
        cg_r = l02.ln_gamma_inf(st(crecs, "pu_s"), st(crecs, "pu_v"), st(crecs, "Au_s"),
                                st(crecs, "Au_v"), None, None, T).numpy()
    cm = np.array([r["m"] for r in crecs])
    csu = np.array([r["su"] for r in crecs]); csv_ = np.array([r["sv"] for r in crecs])
    corner_ud = {"n": len(cm), "mse_2002_full_UD": round(float(np.mean((cg_f - cm) ** 2)), 4),
                 "mse_2002_res_UD": round(float(np.mean((cg_r - cm) ** 2)), 4),
                 "var_m": round(float(cm.var(ddof=0)), 4)}
    for nb in (6, 8, 10):
        for ddof, lab in ((0, "ML"), (1, "Bessel")):
            bf = lotv(cg_f, cm, nb, ddof)
            corner_ud[f"full_{nb}bins_{lab}"] = {
                "b_insuff_up": round(bf, 4),
                "margin": round(float(np.mean((cg_f - cm) ** 2)) - 2 * bf, 4)}
    P_c, ci_c = two_way_margin(cg_f, cm, csu, csv_, 8, 1)
    corner_ud["P_margin_positive_two_way_8bins_Bessel"] = round(P_c, 3)
    corner_ud["ci90"] = [round(c, 3) for c in ci_c]
    out["corner_on_UD_profiles"] = corner_ud

    # ------------------------------- corner floor on the 2010 kernel's OWN typed latent
    l10.use_dispersion = False
    with torch.no_grad():
        cg10 = l10.ln_gamma_inf(st(crecs, "pt_s"), st(crecs, "pt_v"), st(crecs, "At_s"),
                                st(crecs, "At_v"), st(crecs, "V_s"), st(crecs, "V_v"), T).numpy()
    mse_c10 = float(np.mean((cg10 - cm) ** 2))
    c10 = {"n": len(cm), "mse_2010_dspoff_full_UD_typed": round(mse_c10, 4)}
    for nb in (6, 8, 10):
        for ddof, lab in ((0, "ML"), (1, "Bessel")):
            b = lotv(cg10, cm, nb, ddof)
            c10[f"{nb}bins_{lab}"] = {"b_insuff_up": round(b, 4),
                                      "b_clos_lb": round(mse_c10 - b, 4),
                                      "margin": round(mse_c10 - 2 * b, 4)}
    Pc10, cic10 = two_way_margin(cg10, cm, csu, csv_, 8, 1)
    c10["P_margin_positive_two_way_8bins_Bessel"] = round(Pc10, 3)
    c10["ci90"] = [round(c, 3) for c in cic10]
    out["corner_2010_on_its_own_typed_latent"] = c10

    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"[saved] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
