#!/usr/bin/env python3
"""Closure--insufficiency decomposition on the REPRESENTATIVE set (n=477 IDAC-cap-UD pairs).

The manuscript's keystone decomposition was previously computed only on the n=60 VT-2005
corner, where dim(z*)/n ~ 1.7. This script runs the identical instrument on the larger
representative set the kernel comparison already uses, where z* is the UD profile pair that
the deployed COSMO-SAC-2002 kernel actually consumes there and dim(z*)/n ~ 0.21, so the
insufficiency floor and the closure error are measured on the SAME data and the same
profile database (no cross-database splice).

It also reports:
  * the construction ladder of the representative set (row counts at each filter),
  * a two-way (solute x solvent) cluster-bootstrap interval on the 2002-vs-2010(dispersion
    off) contrast, which the manuscript previously quoted without one,
  * the same bootstrap on the separation margin MSE - 2*B_insuff^up.

Requires the UD profile database (Fingerhut et al. 2017, redistributed with the benchmark
implementation of Bell et al. 2020) under ~/COSMOSAC/profiles/UD. cCOSMO is NOT required:
only the dispersion-off arms, which are our own NIST-validated differentiable layers, enter.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_b_insuff_representative.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, RDLogger
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer, CosmoSac2010Layer  # noqa: E402

UD = Path.home() / "COSMOSAC" / "profiles" / "UD"
IDAC = ROOT / "notebooks" / "data" / "raw" / "idac_expanded.csv"
MATCHED = ROOT / "results" / "b_insuff" / "matched_pairs.csv"
OUT = ROOT / "results" / "b_insuff" / "representative_decomposition.json"


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
    return p, float(p.sum()), float(meta.get("volume [A^3]") or 0.0), float(meta.get("disp. e/kB [K]") or 0.0)


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


def two_way(vals, su, sv, n_boot=4000, seed=0):
    """Cluster bootstrap of a per-row quantity's mean (pigeonhole solute x solvent)."""
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


def main() -> int:
    resolve = _resolver()
    idac = pd.read_csv(IDAC, low_memory=False)
    ladder = {"raw_rows": int(len(idac))}
    idac["Tn"] = pd.to_numeric(idac["temperature"], errors="coerce")
    idac = idac.dropna(subset=["ln_gamma_inf", "Tn"]).copy()
    ladder["finite_lngamma_and_T"] = int(len(idac))
    idac["su"] = idac["solute_smiles"].map(resolve)
    idac["sv"] = idac["solvent_smiles"].map(resolve)
    idac = idac.dropna(subset=["su", "sv"])
    ladder["both_components_in_UD_complist"] = int(len(idac))

    by_T, n_prof = {}, 0
    for _, r in idac.iterrows():
        pr = _profiles(r["su"], r["sv"])
        if pr is None:
            continue
        n_prof += 1
        if pr["eps_s"] == 0 or pr["eps_v"] == 0:
            continue
        by_T.setdefault(round(float(r["Tn"]), 2), []).append(
            {**pr, "su": r["su"], "sv": r["sv"], "m": float(r["ln_gamma_inf"]), "T": float(r["Tn"])})
    ladder["both_carry_Mullins_and_Hsieh_profiles"] = int(n_prof)
    ladder["both_carry_a_tabulated_dispersion_epsilon"] = int(sum(len(v) for v in by_T.values()))

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
    g02f, g02r, g10f = map(np.array, (g02f, g02r, g10f))
    zstar = np.stack([np.concatenate([r["pu_s"], r["pu_v"]]) for r in flat])

    corner = pd.read_csv(MATCHED)
    cres = {(resolve(a), resolve(b)) for a, b in zip(corner.solute_key, corner.solvent_key)}
    n_corner_inside = int(sum(1 for a, b, t in zip(su, sv, Ts)
                              if (a, b) in cres and abs(t - 298.15) <= 1.0))

    out = {
        "provenance": "UD profile database (Fingerhut et al. 2017; redistributed with Bell et al. 2020); "
                      "IDAC labels from the expanded ThermoML pull; 2002 = in-house CosmoSacLayer on the "
                      "Mullins-averaged profile, 2010(dsp off) = in-house CosmoSac2010Layer on the typed "
                      "Hsieh profile, both NIST-validated",
        "construction_ladder": ladder,
        "n": int(len(m)), "n_solutes": int(len(set(su))), "n_solvents": int(len(set(sv))),
        "n_distinct_temperatures": int(len(set(np.round(Ts, 2)))),
        "T_range_K": [float(Ts.min()), float(Ts.max())],
        "dim_zstar_over_n": round(zstar.shape[1] / len(m), 3),
        "var_m": round(float(m.var(ddof=0)), 4), "mean_m": round(float(m.mean()), 3),
        "n_corner_pairs_inside_at_298K": n_corner_inside,
        "mse": {"2002_full": round(float(np.mean((g02f - m) ** 2)), 4),
                "2002_res": round(float(np.mean((g02r - m) ** 2)), 4),
                "2010_dspoff_full": round(float(np.mean((g10f - m) ** 2)), 4)},
    }

    grid = []
    for conv, g in (("full", g02f), ("res", g02r)):
        mse = float(np.mean((g - m) ** 2))
        for nb in (3, 5, 8, 10, 16, 20, 30, 48):
            for ddof, lab in ((0, "ML"), (1, "Bessel")):
                b = lotv(g, m, nb, ddof)
                grid.append({"convention": conv, "n_bins": nb, "within_bin_variance": lab,
                             "b_insuff_up": round(b, 4), "b_closure_lb": round(mse - b, 4),
                             "margin": round(mse - 2 * b, 4)})
    out["lotv_grid_2002"] = grid
    out["n_grid_cells_margin_nonpositive"] = int(sum(1 for c in grid if c["margin"] <= 0))

    def oof(make):
        kf = KFold(5, shuffle=True, random_state=0)
        p = np.zeros_like(m)
        for tr, te in kf.split(zstar):
            r = make(); r.fit(zstar[tr], m[tr]); p[te] = r.predict(zstar[te])
        return round(float(np.mean((m - p) ** 2)), 4)

    out["b_insuff_other_estimators"] = {
        "rf_oof_random_folds": oof(lambda: RandomForestRegressor(n_estimators=400, random_state=0, n_jobs=-1)),
        "ridge_oof_random_folds": oof(lambda: Ridge(alpha=1.0)),
    }

    P, ci = two_way_margin(g02f, m, su, sv, 8, 1)
    out["margin_bootstrap_2002_full_8bins_Bessel"] = {"P_positive": round(P, 3),
                                                      "ci90": [round(c, 3) for c in ci]}
    P16, ci16 = two_way_margin(g02f, m, su, sv, 16, 1)
    out["margin_bootstrap_2002_full_16bins_Bessel"] = {"P_positive": round(P16, 3),
                                                       "ci90": [round(c, 3) for c in ci16]}
    d = (g02f - m) ** 2 - (g10f - m) ** 2   # positive => the 2010 kernel is better
    P10, ci10 = two_way(d, su, sv)
    out["kernel_contrast_2002_vs_2010_dspoff"] = {
        "delta_mse_2002_minus_2010": round(float(np.mean(d)), 4),
        "P_2010_better": round(P10, 3), "ci90_delta": [round(c, 3) for c in ci10]}

    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "lotv_grid_2002"}, indent=2))
    print(f"[saved] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
