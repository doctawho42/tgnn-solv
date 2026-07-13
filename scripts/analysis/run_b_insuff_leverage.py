#!/usr/bin/env python3
"""Leverage / label-robustness of the keystone verdict (review gating issue #3).

The verdict B_closure > B_insuff (i.e. B_insuff^LOTV < MSE/2) is carried by
associating IDAC systems, and a referee flagged that a few high-leverage,
physically suspect points dominate the error (e.g. 1-hexanamine in methanol,
ln gamma_inf = +2.62 ~ gamma_inf 13.7 for two miscible H-bonders, vs its reverse
-0.97). The paper's "invariant to zero-mean noise" defense does not cover an
outlier / systematic-bias point. This script does the checks the review requires:

  (1) leave-one-PAIR-out: recompute the deployed-convention margin
      (MSE - B_insuff^LOTV) - B_insuff^LOTV dropping each pair; report whether the
      verdict survives every single-pair deletion, and the most influential pairs.
  (2) TRIMMED / adversarial robustness: drop the top-k HIGHEST-error pairs (which
      SHRINKS B_closure -- the hardest direction for the verdict) and recompute;
      this tests whether closure-dominance is carried by a few suspect points.
  (3) external IDAC noise floor: sigma_eta^2 from inter-source replicate spread
      (idac_expanded.csv). Zero-mean noise inflates the ESTIMATED B_insuff by
      sigma_eta^2, so the noise-corrected true B_insuff is even smaller -- reported
      for context (the verdict's real exposure is leverage, not zero-mean noise).
  (4) leverage audit: the top-SSE pairs + amine<->methanol reverse asymmetry.

Reuses the matched-pair table + estimators from run_b_insuff_decomposition.py; no
COSMO-SAC re-run. CPU, deterministic.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_b_insuff_leverage.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MATCHED = REPO / "results/b_insuff/matched_pairs.csv"
SIGMA = REPO / "results/sigma_profile_artifact/sigma_profiles.csv"
IDAC_EXP = REPO / "notebooks/data/raw/idac_expanded.csv"
OUT = REPO / "results/b_insuff/leverage_robustness.json"


def _load_decomp_module():
    spec = importlib.util.spec_from_file_location(
        "b_insuff_decomp", HERE / "run_b_insuff_decomposition.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["b_insuff_decomp"] = mod
    spec.loader.exec_module(mod)
    return mod


def _rf():
    return RandomForestRegressor(n_estimators=500, min_samples_leaf=3, random_state=0)


def verdict_lotv(mod, m, g, bins=6):
    """(MSE, B_insuff^LOTV, B_closure_lb, holds) on a subset, deployed convention."""
    mse = float(np.mean((m - g) ** 2))
    b = mod.lotv_binning(g, m, n_bins=min(bins, max(2, len(m) // 6)))
    return mse, b, mse - b, bool(b < mse / 2)


def main():
    mod = _load_decomp_module()
    pairs = pd.read_csv(MATCHED)
    table = mod.load_sigma_profiles(str(SIGMA))
    Z = mod.z_star(pairs, table)
    m = pairs["m"].to_numpy(float)
    g = pairs["g_res"].to_numpy(float)
    err2 = (m - g) ** 2
    order = np.argsort(err2)[::-1]        # descending error
    mse0, b0, lb0, ok0 = verdict_lotv(mod, m, g)
    out = {"n": len(pairs), "mse_res": round(mse0, 4), "binsuff_lotv": round(b0, 4),
           "bclosure_lb": round(lb0, 4), "verdict_holds_full": ok0}

    # (1) leave-one-pair-out --------------------------------------------------
    holds, margins = 0, []
    worst = None
    for i in range(len(m)):
        keep = np.ones(len(m), bool); keep[i] = False
        mse_i, b_i, lb_i, ok_i = verdict_lotv(mod, m[keep], g[keep])
        holds += ok_i
        margins.append(lb_i - b_i)
        if worst is None or (lb_i - b_i) < worst[1]:
            worst = (i, lb_i - b_i, ok_i)
    out["leave_one_pair_out"] = {
        "n": len(m), "n_holding": int(holds),
        "min_margin": round(float(min(margins)), 3),
        "median_margin": round(float(np.median(margins)), 3),
        "most_weakening_pair": {
            "solute": str(pairs.iloc[worst[0]]["solute_name"]),
            "solvent": str(pairs.iloc[worst[0]]["solvent_name"]),
            "margin_when_dropped": round(float(worst[1]), 3),
            "verdict_holds": bool(worst[2])},
    }

    # (2) trimmed / adversarial: drop top-k highest-error pairs ----------------
    trim = []
    for k in (0, 1, 2, 3, 5, 8):
        keep = np.ones(len(m), bool)
        keep[order[:k]] = False
        mse_k, b_k, lb_k, ok_k = verdict_lotv(mod, m[keep], g[keep])
        b_rf = mod.oof_var(_rf, Z[keep], m[keep])
        trim.append({"dropped_top_error": k, "n": int(keep.sum()),
                     "mse": round(mse_k, 3), "binsuff_lotv": round(b_k, 3),
                     "binsuff_rf": round(b_rf, 3), "mse_over_2": round(mse_k / 2, 3),
                     "bclosure_lb": round(lb_k, 3),
                     "holds_lotv": ok_k, "holds_rf": bool(b_rf < mse_k / 2)})
    out["trim_top_error_pairs"] = trim

    # (3) external IDAC noise floor -------------------------------------------
    noise = mod.label_noise(pairs, str(IDAC_EXP), 298.15, 1.0)
    if noise.get("available"):
        s2 = noise["sigma_eta_sq_mean_var"]
        noise["note"] = ("zero-mean noise inflates ESTIMATED B_insuff by sigma_eta^2, so the "
                         "noise-corrected TRUE B_insuff is ~%.3f smaller -> verdict easier, not harder"
                         % s2)
        noise["binsuff_lotv_noise_corrected"] = round(max(0.0, b0 - s2), 4)
    out["external_idac_noise_floor"] = noise

    # (4) leverage audit ------------------------------------------------------
    top = pairs.assign(err2=err2).sort_values("err2", ascending=False).head(6)
    out["top_leverage_pairs"] = [
        {"solute": str(r["solute_name"]), "solvent": str(r["solvent_name"]),
         "m": round(float(r["m"]), 2), "g_res": round(float(r["g_res"]), 2),
         "sq_error": round(float(r["err2"]), 2),
         "pct_of_SSE": round(100 * float(r["err2"]) / err2.sum(), 1)}
        for _, r in top.iterrows()]
    out["top2_pct_of_SSE"] = round(100 * err2[order[:2]].sum() / err2.sum(), 1)

    OUT.write_text(json.dumps(out, indent=2))

    # ---- console ----
    print(f"n={out['n']}  MSE={mse0:.3f}  B_insuff^LOTV={b0:.3f}  B_clos_lb={lb0:.3f}  holds={ok0}")
    lp = out["leave_one_pair_out"]
    print(f"(1) leave-one-pair-out: holds {lp['n_holding']}/{lp['n']}, min margin={lp['min_margin']} "
          f"(worst drop: {lp['most_weakening_pair']['solute']} in {lp['most_weakening_pair']['solvent']})")
    print(f"(2) trim top-error pairs (top2 = {out['top2_pct_of_SSE']}% of SSE):")
    for t in trim:
        print(f"    drop {t['dropped_top_error']}: n={t['n']} MSE={t['mse']} MSE/2={t['mse_over_2']} "
              f"B_insuff^LOTV={t['binsuff_lotv']} (holds={t['holds_lotv']})  RF={t['binsuff_rf']} (holds={t['holds_rf']})")
    nf = out["external_idac_noise_floor"]
    if nf.get("available"):
        print(f"(3) IDAC noise floor: sigma_eta^2={nf['sigma_eta_sq_mean_var']:.3f} "
              f"(replicate sd median={nf['replicate_sd_median']:.2f}), n_with_replicates={nf['n_pairs_with_replicates']}")
    else:
        print(f"(3) IDAC noise floor: unavailable ({nf.get('reason')})")
    print(f"(4) top leverage: " + "; ".join(
        f"{t['solute'][:16]}/{t['solvent'][:10]} {t['pct_of_SSE']}%" for t in out["top_leverage_pairs"][:3]))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
