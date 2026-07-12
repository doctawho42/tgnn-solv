#!/usr/bin/env python3
"""Robustness of the closure/insufficiency verdict (referee M2).

The keystone claim (sec:measure) is B_closure > B_insuff on the n=60 IDAC matched set,
via the convention-independent lower bound B_closure >= MSE - B_insuff^up under the
DEPLOYED residual-only closure. A referee asked whether that verdict survives (a) the
choice of B_insuff estimator, (b) dropping any single solvent, and (c) plausible IDAC
label noise (assumed 0 in the headline). This script answers all three by reusing the
estimators and the matched-pair table from run_b_insuff_decomposition.py -- no COSMO-SAC
re-run (g_res / g_full are already in matched_pairs.csv).

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_b_insuff_robustness.py
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
from sklearn.linear_model import Ridge

HERE = Path(__file__).resolve().parent
MATCHED = HERE.parents[1] / "results/b_insuff/matched_pairs.csv"
SIGMA = HERE.parents[1] / "results/sigma_profile_artifact/sigma_profiles.csv"
OUT = HERE.parents[1] / "results/b_insuff/robustness.json"


def _load_decomp_module():
    spec = importlib.util.spec_from_file_location(
        "b_insuff_decomp", HERE / "run_b_insuff_decomposition.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rf():
    return RandomForestRegressor(n_estimators=500, min_samples_leaf=3, random_state=0)


def binsuff_estimators(mod, Z, m, g):
    """All B_insuff upper-bound estimators (convention-independent in z*; binning uses g)."""
    return {
        "rf_oof":    mod.oof_var(_rf, Z, m),
        "ridge_oof": mod.oof_var(lambda: Ridge(alpha=1.0), Z, m),
        "knn":       mod.knn_var(Z, m, k=1),
        "binning6":  mod.lotv_binning(g, m, n_bins=6),
    }


def verdict(mse, binsuff_up):
    """B_closure lower bound and whether it clears the (most conservative) B_insuff."""
    bclos_lb = mse - binsuff_up
    return bclos_lb, bclos_lb > binsuff_up


def clustered_bootstrap(mod, m, g, solv, n_boot=3000, seed=0):
    """Solvent-clustered bootstrap CI on the convention-independent verdict, using the stable
    LOTV/binning B_insuff bound. Resamples SOLVENTS with replacement (respecting the clustering
    a referee flagged), recomputes MSE_res - B_insuff^up (the B_closure lower bound) and the
    certification margin (B_clos_lb - B_insuff^up), and reports the CI + P(margin>0)."""
    rng = np.random.default_rng(seed)
    solvents = np.array(sorted(set(solv)))
    lbs, margins = [], []
    for _ in range(n_boot):
        drawn = rng.choice(solvents, size=len(solvents), replace=True)
        idx = np.concatenate([np.where(solv == s)[0] for s in drawn])
        mm, gg = m[idx], g[idx]
        if len(mm) < 12:
            continue
        mse = float(np.mean((mm - gg) ** 2))
        binsuff = mod.lotv_binning(gg, mm, n_bins=max(3, len(mm) // 10))
        lb = mse - binsuff
        lbs.append(lb); margins.append(lb - binsuff)
    lbs, margins = np.array(lbs), np.array(margins)
    return {
        "n_boot": len(lbs), "estimator": "LOTV/binning",
        "bclosure_lb_median": round(float(np.median(lbs)), 3),
        "bclosure_lb_ci90": [round(float(np.percentile(lbs, 5)), 3),
                             round(float(np.percentile(lbs, 95)), 3)],
        "margin_median": round(float(np.median(margins)), 3),
        "margin_ci90": [round(float(np.percentile(margins, 5)), 3),
                        round(float(np.percentile(margins, 95)), 3)],
        "P_verdict_holds": round(float(np.mean(margins > 0)), 3),
    }


def main():
    mod = _load_decomp_module()
    pairs = pd.read_csv(MATCHED)
    table = mod.load_sigma_profiles(str(SIGMA))
    Z = mod.z_star(pairs, table)
    m = pairs["m"].to_numpy(float)
    g = pairs["g_res"].to_numpy(float)          # deployed convention (load-bearing)
    solv = pairs["solvent_key"].to_numpy()
    mse = float(np.mean((m - g) ** 2))

    out = {"n": len(pairs), "n_solvents": int(pd.Series(solv).nunique()),
           "convention": "res (deployed)", "mse_true_input": round(mse, 4)}

    # (a) estimator sensitivity ------------------------------------------------
    est = binsuff_estimators(mod, Z, m, g)
    est_rows = {}
    for name, b in est.items():
        lb, ok = verdict(mse, b)
        est_rows[name] = {"binsuff_up": round(b, 4), "bclosure_lb": round(lb, 4),
                          "verdict_holds": bool(ok)}
    binsuff_max = max(est.values())            # most conservative upper bound
    est_rows["_most_conservative"] = {"binsuff_up": round(binsuff_max, 4),
                                      "bclosure_lb": round(mse - binsuff_max, 4),
                                      "verdict_holds": bool((mse - binsuff_max) > binsuff_max)}
    out["estimator_sensitivity"] = est_rows

    # (b) leave-one-solvent-out ------------------------------------------------
    loso = []
    for s in sorted(set(solv)):
        keep = solv != s
        if keep.sum() < 20:
            continue
        mse_s = float(np.mean((m[keep] - g[keep]) ** 2))
        b_rf = mod.oof_var(_rf, Z[keep], m[keep])
        b_bin = mod.lotv_binning(g[keep], m[keep], n_bins=6)
        _, ok_rf = verdict(mse_s, b_rf)
        _, ok_bin = verdict(mse_s, b_bin)
        loso.append({"dropped": str(s), "n": int(keep.sum()), "mse": round(mse_s, 3),
                     "binsuff_rf": round(b_rf, 3), "binsuff_bin": round(b_bin, 3),
                     "holds_rf": bool(ok_rf), "holds_bin": bool(ok_bin)})
    out["leave_one_solvent_out"] = {
        "n_folds": len(loso),
        "n_holding_rf": sum(r["holds_rf"] for r in loso),
        "n_holding_binning": sum(r["holds_bin"] for r in loso),
        "folds": loso,
    }

    # (c) label-noise stress ---------------------------------------------------
    # B_closure = MSE - E[Var(m|z*)] is invariant to zero-mean noise in expectation
    # (both terms rise by sigma_eta^2); we verify the ESTIMATED verdict survives.
    noise = []
    for sd in (0.2, 0.4, 0.6, 0.8):
        lbs = []
        for seed in range(8):
            rng = np.random.default_rng(1000 + seed)
            mn = m + rng.normal(0.0, sd, size=m.shape)
            b = mod.oof_var(_rf, Z, mn)
            mse_n = float(np.mean((mn - g) ** 2))
            lbs.append(mse_n - b)
        lbs = np.array(lbs)
        noise.append({"sigma_eta": sd, "bclosure_lb_mean": round(float(lbs.mean()), 3),
                      "bclosure_lb_sd": round(float(lbs.std()), 3),
                      "holds_all_seeds": bool(np.all(lbs > binsuff_max))})
    out["label_noise_stress"] = {"binsuff_up_ref": round(binsuff_max, 4), "sweep": noise}

    # (d) solvent-clustered bootstrap CI on the verdict --------------------------
    out["clustered_bootstrap"] = clustered_bootstrap(mod, m, g, solv)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    print(f"n={out['n']} pairs, {out['n_solvents']} solvents, MSE_res={mse:.3f}")
    print("(a) estimator sensitivity (B_insuff^up -> B_clos_lb, verdict):")
    for name, r in est_rows.items():
        print(f"    {name:18s} B_insuff^up={r['binsuff_up']:.3f}  "
              f"B_clos_lb={r['bclosure_lb']:.3f}  holds={r['verdict_holds']}")
    lo = out["leave_one_solvent_out"]
    print(f"(b) leave-one-solvent-out: RF-estimator holds {lo['n_holding_rf']}/{lo['n_folds']}, "
          f"binning-estimator holds {lo['n_holding_binning']}/{lo['n_folds']}")
    print("(c) label-noise stress (verdict vs assumed-0 noise):")
    for r in out["label_noise_stress"]["sweep"]:
        print(f"    sigma_eta={r['sigma_eta']}  B_clos_lb={r['bclosure_lb_mean']}"
              f"±{r['bclosure_lb_sd']}  holds_all={r['holds_all_seeds']}")
    cb = out["clustered_bootstrap"]
    print(f"(d) solvent-clustered bootstrap ({cb['n_boot']} reps, LOTV): "
          f"B_clos_lb={cb['bclosure_lb_median']} CI90={cb['bclosure_lb_ci90']}, "
          f"margin={cb['margin_median']} CI90={cb['margin_ci90']}, P(verdict)={cb['P_verdict_holds']}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
