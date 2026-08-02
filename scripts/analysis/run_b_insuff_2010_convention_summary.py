#!/usr/bin/env python3
"""Convention summary for the 2010 typed-latent floor check, from the deposited row tables.

Reads the two deposited row-level tables written by ``run_b_insuff_convention_audit.py``
(which now carries the residual-only 2010 column ``g_2010_dsp_off_res``) and prints /
saves the four quantities the convention rule needs, on both sets and under both
conventions: MSE, the LOTV B_insuff upper bound (8 equal-count bins, ddof=1), the margin
MSE - 2*B_insuff, and the clustered bootstraps on the 477-row set.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_2010_convention_summary.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB_REP = ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv"
TAB_COR = ROOT / "paper" / "si_tables" / "vt2005_matched_set_60.csv"
OUT = ROOT / "results" / "b_insuff" / "kernel_2010_convention.json"


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


def two_way_delta(d, su, sv, n_boot=3000, seed=0):
    """Bootstrap P(mean d > 0) for a per-row contrast d."""
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
        out.append(float(np.average(d, weights=w)))
    out = np.array(out)
    return float(np.mean(out > 0)), [float(np.percentile(out, 5)), float(np.percentile(out, 95))]


def main() -> int:
    rep = pd.read_csv(TAB_REP)
    m = rep["m_ln_gamma_inf"].to_numpy(float)
    su = rep["solute_ud_key"].to_numpy(str)
    sv = rep["solvent_ud_key"].to_numpy(str)
    doi = rep["source_doi"].to_numpy(str)
    pair = np.array([f"{a}|{b}" for a, b in zip(su, sv)])

    res = {"representative_477": {}, "corner_60": {}}
    arms = {"2010_full": "g_2010_dsp_off_full", "2010_res": "g_2010_dsp_off_res",
            "2002_full": "g_2002_full", "2002_res": "g_2002_res"}
    for name, col in arms.items():
        g = rep[col].to_numpy(float)
        mse = float(np.mean((g - m) ** 2))
        b = lotv(g, m, 8, 1)
        P2, ci2 = two_way_margin(g, m, su, sv, 8, 1)
        Pp, cip = cluster_margin(g, m, pair, 8, 1)
        Pd, cid = cluster_margin(g, m, doi, 8, 1)
        res["representative_477"][name] = {
            "mse": round(mse, 4), "b_insuff_up_8bins_Bessel": round(b, 4),
            "b_clos_lb": round(mse - b, 4), "margin": round(mse - 2 * b, 4),
            "bias_mean_g_minus_m": round(float(np.mean(g - m)), 4),
            "P_two_way_solute_x_solvent": round(P2, 3),
            "ci90_two_way": [round(c, 3) for c in ci2],
            "P_clustered_on_pair": round(Pp, 3), "ci90_pair": [round(c, 3) for c in cip],
            "P_clustered_on_doi": round(Pd, 3), "ci90_doi": [round(c, 3) for c in cid],
        }
        print(f"[rep {name:9s}] MSE {mse:.4f}  B {b:.4f}  margin {mse-2*b:+.4f}  "
              f"P2 {P2:.3f}  Ppair {Pp:.3f}  Pdoi {Pd:.3f}", flush=True)

    # min-over-conventions for the 2010 kernel: B_insuff = E[Var(m|z*,T)] does not depend
    # on the closure convention, so the tighter of the two binning bounds is admissible.
    b10f = lotv(rep["g_2010_dsp_off_full"].to_numpy(float), m, 8, 1)
    b10r = lotv(rep["g_2010_dsp_off_res"].to_numpy(float), m, 8, 1)
    mse10r = float(np.mean((rep["g_2010_dsp_off_res"].to_numpy(float) - m) ** 2))
    res["representative_477"]["min_over_conventions_2010"] = {
        "b_insuff_up": round(min(b10f, b10r), 4),
        "margin_against_deployed_res_mse": round(mse10r - 2 * min(b10f, b10r), 4),
    }

    # the same convention switch on the 2002 -> 2010 fidelity-lever row
    for conv in ("full", "res"):
        g02 = rep[f"g_2002_{conv}"].to_numpy(float)
        g10 = rep[f"g_2010_dsp_off_{conv}"].to_numpy(float)
        d = (g02 - m) ** 2 - (g10 - m) ** 2     # positive => 2010 better
        P, ci = two_way_delta(d, su, sv)
        res["representative_477"][f"fidelity_lever_2002_minus_2010_{conv}"] = {
            "delta": round(float(np.mean(d)), 4), "P_2010_better": round(P, 3),
            "ci90_delta": [round(c, 3) for c in ci],
        }
        print(f"[lever {conv}] delta {np.mean(d):+.4f}  P(2010 better) {P:.3f}", flush=True)

    cor = pd.read_csv(TAB_COR)
    cm = cor["m"].to_numpy(float)
    csu = cor["solute_key"].to_numpy(str)
    csv_ = cor["solvent_key"].to_numpy(str)
    carms = {"2010_full": "g_2010_dsp_off_full_UD", "2010_res": "g_2010_dsp_off_res_UD",
             "2002_full": "g_2002_full_UD", "2002_res": "g_2002_res_UD"}
    for name, col in carms.items():
        g = cor[col].to_numpy(float)
        mse = float(np.mean((g - cm) ** 2))
        b = lotv(g, cm, 8, 1)
        P2, ci2 = two_way_margin(g, cm, csu, csv_, 8, 1)
        res["corner_60"][name] = {
            "mse": round(mse, 4), "b_insuff_up_8bins_Bessel": round(b, 4),
            "b_clos_lb": round(mse - b, 4), "margin": round(mse - 2 * b, 4),
            "bias_mean_g_minus_m": round(float(np.mean(g - cm)), 4),
            "P_two_way_solute_x_solvent": round(P2, 3),
            "ci90_two_way": [round(c, 3) for c in ci2],
        }
        print(f"[cor {name:9s}] MSE {mse:.4f}  B {b:.4f}  margin {mse-2*b:+.4f}  "
              f"P2 {P2:.3f}", flush=True)

    Path(OUT).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print(f"[saved] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
