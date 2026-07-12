#!/usr/bin/env python3
"""In-regime (higher-gamma) closure/insufficiency decomposition (referee M1).

The keystone is measured on the low-gamma IDAC corner (matched mean ln gamma_inf = 0.75),
while the paradox lives at all gamma. A referee asked for even a partial in-regime test.
We cannot reach finite composition with the VT-2005 oracle, but we CAN stratify the matched
set by gamma and ask whether the verdict B_closure > B_insuff survives in the higher-gamma
half -- the regime closer to the non-ideal systems the paradox spans. Reuses the estimators
and matched-pair table from run_b_insuff_decomposition.py (no COSMO-SAC re-run).

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_b_insuff_regime.py
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

HERE = Path(__file__).resolve().parent
MATCHED = HERE.parents[1] / "results/b_insuff/matched_pairs.csv"
SIGMA = HERE.parents[1] / "results/sigma_profile_artifact/sigma_profiles.csv"
OUT = HERE.parents[1] / "results/b_insuff/regime.json"


def _mod():
    spec = importlib.util.spec_from_file_location(
        "b_insuff_decomp", HERE / "run_b_insuff_decomposition.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _rf():
    return RandomForestRegressor(n_estimators=500, min_samples_leaf=3, random_state=0)


def decompose(mod, Z, m, g, label):
    mse = float(np.mean((m - g) ** 2))
    b_bin = mod.lotv_binning(g, m, n_bins=max(3, len(m) // 8))
    b_rf = mod.oof_var(_rf, Z, m)
    b_knn = mod.knn_var(Z, m, k=1)
    b_up = min(b_bin, b_rf, b_knn)          # tightest valid upper bound on B_insuff
    return {
        "stratum": label, "n": len(m), "mean_lngamma": round(float(m.mean()), 2),
        "mse_true_input": round(mse, 3),
        "binsuff_binning": round(b_bin, 3), "binsuff_rf": round(b_rf, 3),
        "binsuff_knn": round(b_knn, 3), "binsuff_tightest": round(b_up, 3),
        "bclosure_lb": round(mse - b_up, 3),
        "verdict_holds": bool((mse - b_up) > b_up),
    }


def main():
    mod = _mod()
    pairs = pd.read_csv(MATCHED)
    table = mod.load_sigma_profiles(str(SIGMA))
    Z = mod.z_star(pairs, table)
    m = pairs["m"].to_numpy(float)
    g = pairs["g_res"].to_numpy(float)          # deployed convention

    med = float(np.median(m))
    strata = {
        "all": np.ones(len(m), bool),
        "lower_gamma (m<=median)": m <= med,
        "higher_gamma (m>median)": m > med,
        "high_gamma (m>1.5)": m > 1.5,
    }
    out = {"n": len(m), "median_lngamma": round(med, 2), "convention": "res (deployed)",
           "strata": [decompose(mod, Z[k], m[k], g[k], name) for name, k in strata.items()
                      if k.sum() >= 10]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"n={out['n']}, median ln gamma_inf={out['median_lngamma']}")
    for s in out["strata"]:
        print(f"  {s['stratum']:26s} n={s['n']:2d} <lng>={s['mean_lngamma']:+.2f}  "
              f"MSE={s['mse_true_input']:.2f}  B_insuff^up={s['binsuff_tightest']:.2f}  "
              f"B_clos_lb={s['bclosure_lb']:.2f}  holds={s['verdict_holds']}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
