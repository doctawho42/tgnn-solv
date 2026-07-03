#!/usr/bin/env python3
"""Split-conformal prediction intervals (guaranteed marginal coverage).

Phase C showed the model's native (MC-dropout) uncertainty is badly miscalibrated
(PICP@90 ~ 0.13). Split conformal prediction fixes this *by construction*: given a
held-out calibration set it yields intervals with finite-sample marginal coverage
>= 1 - alpha regardless of how wrong the model's own uncertainty is.

Two variants:
  * absolute   : score = |y - yhat|; interval yhat +/- q. Constant width.
  * normalized : score = |y - yhat| / sigma (needs a std column); interval
                 yhat +/- q*sigma. Adaptive width that follows the model's own
                 (uncalibrated) uncertainty but is rescaled to hit coverage.

Reports, on the evaluation split, empirical coverage vs nominal and mean interval
width (in ln and log10 units) at several levels.

    python scripts/analysis/run_conformal_calibration.py \
        --predictions-csv results/uncertainty/mc_dropout.csv \
        --out-json results/uncertainty/conformal.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LN10 = math.log(10.0)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--predictions-csv", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--calib-frac", type=float, default=0.5,
                   help="Fraction of rows used as the conformal calibration set.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--true-col", default="ln_x2_true")
    p.add_argument("--mean-col", default=None, help="default: ln_x2_mean else ln_x2_pred")
    p.add_argument("--std-col", default=None, help="default: ln_x2_std else ln_x2_sigma (optional)")
    p.add_argument("--levels", default="0.5,0.8,0.9,0.95")
    return p.parse_args()


def _conformal_q(scores: np.ndarray, level: float) -> float:
    """Finite-sample conformal quantile of nonconformity scores."""
    n = scores.size
    # rank = ceil((n+1)(1-alpha)); guard against >n (then interval is unbounded -> max).
    k = math.ceil((n + 1) * level)
    if k > n:
        return float(np.max(scores))
    return float(np.sort(scores)[k - 1])


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.predictions_csv, low_memory=False)
    if "has_solubility" in df.columns:
        raw = df["has_solubility"].astype(str).str.lower()
        df = df[raw.isin({"true", "1", "1.0", "yes"}) | (pd.to_numeric(df["has_solubility"], errors="coerce") > 0)]
    mean_col = args.mean_col or ("ln_x2_mean" if "ln_x2_mean" in df.columns else "ln_x2_pred")
    std_col = args.std_col or ("ln_x2_std" if "ln_x2_std" in df.columns
                               else ("ln_x2_sigma" if "ln_x2_sigma" in df.columns else None))
    for c in (args.true_col, mean_col):
        if c not in df.columns:
            raise SystemExit(f"Missing column '{c}'.")

    y = pd.to_numeric(df[args.true_col], errors="coerce").to_numpy(float)
    mu = pd.to_numeric(df[mean_col], errors="coerce").to_numpy(float)
    sigma = (pd.to_numeric(df[std_col], errors="coerce").to_numpy(float)
             if std_col else None)
    m = np.isfinite(y) & np.isfinite(mu) & (np.isfinite(sigma) if sigma is not None else True)
    y, mu = y[m], mu[m]
    sigma = sigma[m] if sigma is not None else None

    rng = np.random.default_rng(args.seed)
    idx = rng.permutation(y.size)
    n_cal = int(args.calib_frac * y.size)
    cal, ev = idx[:n_cal], idx[n_cal:]

    abs_cal = np.abs(y[cal] - mu[cal])
    norm_cal = (abs_cal / np.clip(sigma[cal], 1e-8, None)) if sigma is not None else None
    levels = [float(x) for x in args.levels.split(",") if x.strip()]

    out: dict[str, Any] = {
        "predictions_csv": str(Path(args.predictions_csv).resolve()),
        "n_total": int(y.size), "n_calib": int(cal.size), "n_eval": int(ev.size),
        "std_column_used": std_col,
        "absolute": {}, "normalized": {} if sigma is not None else None,
    }
    for lv in levels:
        q = _conformal_q(abs_cal, lv)
        lo, hi = mu[ev] - q, mu[ev] + q
        cov = float(np.mean((y[ev] >= lo) & (y[ev] <= hi)))
        width_ln = float(2 * q)
        out["absolute"][f"{int(lv*100)}"] = {
            "nominal": lv, "empirical_coverage": cov,
            "mean_width_ln": width_ln, "mean_width_log10": width_ln / LN10,
        }
        if norm_cal is not None:
            qn = _conformal_q(norm_cal, lv)
            w = qn * sigma[ev]
            covn = float(np.mean((y[ev] >= mu[ev] - w) & (y[ev] <= mu[ev] + w)))
            out["normalized"][f"{int(lv*100)}"] = {
                "nominal": lv, "empirical_coverage": covn,
                "mean_width_ln": float(2 * w.mean()),
                "mean_width_log10": float(2 * w.mean() / LN10),
            }
    out["interpretation"] = (
        "Split conformal guarantees empirical_coverage >= nominal on exchangeable "
        "data by construction; compare to the model's raw PICP. 'normalized' gives "
        "adaptive (per-point) widths if a std column is present."
    )
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "interpretation"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
