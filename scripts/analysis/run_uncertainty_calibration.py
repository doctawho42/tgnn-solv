#!/usr/bin/env python3
"""Uncertainty-calibration evaluation, noise-floor-aware.

Operates post-hoc on a predictions CSV carrying a predictive mean and std
(e.g. from MCDropoutPredictor.predict_batch -> ln_x2_mean / ln_x2_std), or runs
MC-dropout itself given a checkpoint + test CSV.

Reports, assuming a Gaussian predictive distribution:
  * PICP at nominal levels (observed coverage of mean ± z·std);
  * a regression ECE = mean |observed - nominal| over a coverage grid;
  * sharpness (mean std) and RMSE/MAE;
  * noise-floor awareness: a calibrated model should not claim std below the
    irreducible label-noise floor (Phase A). We report mean-std vs floor and the
    fraction of predictions that are over-confident (std < floor).

    # post-hoc on an MC-dropout CSV
    python scripts/analysis/run_uncertainty_calibration.py \
        --predictions-csv results/uncertainty/mc_dropout.csv \
        --out-json results/uncertainty/calibration.json

    # generate via MC-dropout from a checkpoint
    python scripts/analysis/run_uncertainty_calibration.py \
        --checkpoint checkpoints/proxy/tgnn_mpnn.pt --model-type tgnn \
        --test-data notebooks/data/processed/test.csv \
        --out-json results/uncertainty/calibration.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))
import _bootstrap  # noqa: F401


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--predictions-csv", default=None)
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--model-type", choices=["tgnn", "direct"], default="tgnn")
    p.add_argument("--test-data", default=None)
    p.add_argument("--device", default="cpu")
    p.add_argument("--mc-samples", type=int, default=30)
    p.add_argument("--out-json", required=True)
    p.add_argument("--true-col", default="ln_x2_true")
    p.add_argument("--mean-col", default=None, help="default: ln_x2_mean, else ln_x2_pred")
    p.add_argument("--std-col", default=None, help="default: ln_x2_std, else ln_x2_sigma")
    p.add_argument("--noise-floor", type=float, default=None,
                   help="Irreducible ln x2 noise floor; default reads results/noise_floor/summary.json (mean) else 0.16.")
    return p.parse_args()


def _resolve_noise_floor(arg: float | None) -> float:
    if arg is not None:
        return float(arg)
    p = Path("results/noise_floor/summary.json")
    if p.exists():
        try:
            return float(json.loads(p.read_text())["dedup"]["mean"])
        except Exception:
            pass
    return 0.16


def _generate_mc_dropout(args: argparse.Namespace) -> pd.DataFrame:
    from tgnn_solv.inference import load_directgnn_model, load_model
    from tgnn_solv.uncertainty import MCDropoutPredictor
    device = args.device
    if args.model_type == "direct":
        model, _ = load_directgnn_model(args.checkpoint, device=device)
    else:
        model, _ = load_model(args.checkpoint, device=device)
    df = pd.read_csv(args.test_data, low_memory=False)
    if "has_solubility" in df.columns:
        raw = df["has_solubility"].astype(str).str.lower()
        df = df[raw.isin({"true", "1", "1.0", "yes"}) | (pd.to_numeric(df["has_solubility"], errors="coerce") > 0)]
    systems = list(zip(df["solute_smiles"], df["solvent_smiles"],
                       pd.to_numeric(df["temperature"], errors="coerce")))
    pred = MCDropoutPredictor(model, n_samples=args.mc_samples).predict_batch(systems)
    pred[args.true_col] = pd.to_numeric(df["ln_x2"], errors="coerce").to_numpy()[: len(pred)]
    return pred


def calibration_metrics(
    true: np.ndarray, mean: np.ndarray, std: np.ndarray, noise_floor: float
) -> dict[str, Any]:
    m = np.isfinite(true) & np.isfinite(mean) & np.isfinite(std) & (std > 0)
    true, mean, std = true[m], mean[m], std[m]
    err = mean - true
    z = np.abs(err) / std
    levels = [0.5, 0.68, 0.8, 0.9, 0.95, 0.99]
    picp = {}
    ece_terms = []
    for lv in levels:
        zc = norm.ppf(0.5 + lv / 2.0)
        cov = float(np.mean(z <= zc))
        picp[f"{int(lv*100)}"] = cov
        ece_terms.append(abs(cov - lv))
    return {
        "n": int(true.size),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "mae": float(np.mean(np.abs(err))),
        "picp": picp,
        "regression_ece": float(np.mean(ece_terms)),
        "sharpness_mean_std": float(np.mean(std)),
        "median_std": float(np.median(std)),
        "noise_floor": noise_floor,
        "mean_std_over_floor": float(np.mean(std) / noise_floor) if noise_floor > 0 else None,
        "overconfident_fraction_std_below_floor": float(np.mean(std < noise_floor)),
        "interpretation": (
            "PICP at each level should match the nominal coverage; regression_ece is "
            "the mean gap (lower=better). overconfident_fraction flags predictions "
            "claiming std below the irreducible label-noise floor."
        ),
    }


def main() -> None:
    args = parse_args()
    if args.predictions_csv:
        df = pd.read_csv(args.predictions_csv, low_memory=False)
    elif args.checkpoint and args.test_data:
        df = _generate_mc_dropout(args)
    else:
        raise SystemExit("Provide --predictions-csv OR (--checkpoint and --test-data).")

    mean_col = args.mean_col or ("ln_x2_mean" if "ln_x2_mean" in df.columns else "ln_x2_pred")
    std_col = args.std_col or ("ln_x2_std" if "ln_x2_std" in df.columns else "ln_x2_sigma")
    for c in (args.true_col, mean_col, std_col):
        if c not in df.columns:
            raise SystemExit(f"Missing column '{c}' in predictions; have {list(df.columns)[:12]}...")

    metrics = calibration_metrics(
        pd.to_numeric(df[args.true_col], errors="coerce").to_numpy(float),
        pd.to_numeric(df[mean_col], errors="coerce").to_numpy(float),
        pd.to_numeric(df[std_col], errors="coerce").to_numpy(float),
        _resolve_noise_floor(args.noise_floor),
    )
    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k != "interpretation"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
