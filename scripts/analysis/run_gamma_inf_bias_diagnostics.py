#!/usr/bin/env python
"""Diagnose level bias for direct ln(gamma_inf) TGNN predictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


R = 8.31446261815324


def _finite(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan)


def _metrics(y: np.ndarray, yhat: np.ndarray) -> dict[str, float]:
    err = yhat - y
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return {
        "n": int(len(y)),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "bias": float(np.mean(err)),
        "median_error": float(np.median(err)),
        "r2": float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "true_std": float(np.std(y)),
        "pred_std": float(np.std(yhat)),
        "pred_std_ratio": float(np.std(yhat) / np.std(y)) if np.std(y) > 0 else float("nan"),
    }


def _summarize_quantity(df: pd.DataFrame, col: str, split: str) -> dict[str, float | str | int]:
    if col not in df.columns:
        return {"split": split, "quantity": col, "n": 0}
    x = _finite(df[col]).dropna().to_numpy()
    if len(x) == 0:
        return {"split": split, "quantity": col, "n": 0}
    return {
        "split": split,
        "quantity": col,
        "n": int(len(x)),
        "mean": float(np.mean(x)),
        "std": float(np.std(x)),
        "p05": float(np.percentile(x, 5)),
        "p50": float(np.percentile(x, 50)),
        "p95": float(np.percentile(x, 95)),
    }


def _load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"ln_x2_true", "ln_x2_pred"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    df = df.copy()
    df["ln_x2_true"] = _finite(df["ln_x2_true"])
    df["ln_x2_pred"] = _finite(df["ln_x2_pred"])
    df = df[df["ln_x2_true"].notna() & df["ln_x2_pred"].notna()].reset_index(drop=True)
    return df


def _crystal_replacement(df: pd.DataFrame) -> dict[str, float | int]:
    required = {"T", "T_m", "dH_fus", "Phi", "ln_x2_true", "ln_x2_pred"}
    if not required.issubset(df.columns):
        return {"n": 0, "reason": "missing_columns"}

    has_tm = df.get("has_valid_T_m", df.get("has_T_m", 0))
    has_dh = df.get("has_valid_dH_fus", df.get("has_dH_fus", 0))
    mask = (_finite(has_tm) > 0.5) & (_finite(has_dh) > 0.5)
    cols = ["T", "T_m", "dH_fus", "Phi", "ln_x2_true", "ln_x2_pred"]
    work = df.loc[mask, cols].copy()
    for c in cols:
        work[c] = _finite(work[c])
    work = work.dropna()
    work = work[(work["T"] > 0) & (work["T_m"] > 0) & (work["dH_fus"] > 0)]
    if work.empty:
        return {"n": 0, "reason": "no_valid_crystal_rows"}

    phi_true = work["dH_fus"].to_numpy() / R * (
        1.0 / work["T"].to_numpy() - 1.0 / work["T_m"].to_numpy()
    )
    phi_pred = work["Phi"].to_numpy()
    y = work["ln_x2_true"].to_numpy()
    yhat = work["ln_x2_pred"].to_numpy()
    yhat_crystal = yhat + (phi_pred - phi_true)
    before = _metrics(y, yhat)
    after = _metrics(y, yhat_crystal)
    return {
        "n": int(len(work)),
        "phi_pred_mean": float(np.mean(phi_pred)),
        "phi_true_mean": float(np.mean(phi_true)),
        "phi_pred_minus_true_mean": float(np.mean(phi_pred - phi_true)),
        "bias_before": before["bias"],
        "bias_after_true_crystal": after["bias"],
        "mae_before": before["mae"],
        "mae_after_true_crystal": after["mae"],
    }


def _bin_bias(df: pd.DataFrame) -> pd.DataFrame:
    bins = [-np.inf, -15.0, -12.0, -9.0, -6.0, -3.0, 0.0, np.inf]
    labels = ["<-15", "[-15,-12)", "[-12,-9)", "[-9,-6)", "[-6,-3)", "[-3,0)", ">=0"]
    work = df.copy()
    work["bin"] = pd.cut(work["ln_x2_true"], bins=bins, labels=labels, right=False)
    rows = []
    for label, g in work.groupby("bin", observed=True):
        y = g["ln_x2_true"].to_numpy()
        yhat = g["ln_x2_pred"].to_numpy()
        m = _metrics(y, yhat)
        rows.append({"bin": str(label), **m})
    return pd.DataFrame(rows)


def _prediction_bin_calibration(
    val: pd.DataFrame,
    test: pd.DataFrame,
    n_bins: int,
    statistic: str = "median",
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Fit residual shifts in validation prediction bins and apply them to test."""
    if n_bins < 2:
        raise ValueError("n_bins must be at least 2")
    if statistic not in {"median", "mean"}:
        raise ValueError("statistic must be 'median' or 'mean'")

    val_pred = val["ln_x2_pred"].to_numpy(dtype=float)
    val_resid = (val["ln_x2_true"] - val["ln_x2_pred"]).to_numpy(dtype=float)
    edges = np.quantile(val_pred, np.linspace(0.0, 1.0, n_bins + 1))
    edges = np.unique(edges)
    if len(edges) < 3:
        edges = np.linspace(float(np.min(val_pred)), float(np.max(val_pred)), n_bins + 1)
    edges[0] = -np.inf
    edges[-1] = np.inf

    val_bins = np.digitize(val_pred, edges[1:-1], right=False)
    global_shift = float(np.median(val_resid) if statistic == "median" else np.mean(val_resid))
    rows: list[dict[str, float | int | str]] = []
    shifts: list[float] = []
    for i in range(len(edges) - 1):
        mask = val_bins == i
        if mask.any():
            resid = val_resid[mask]
            shift = float(np.median(resid) if statistic == "median" else np.mean(resid))
            n = int(mask.sum())
        else:
            shift = global_shift
            n = 0
        shifts.append(shift)
        rows.append(
            {
                "pred_bin": i,
                "pred_low": float(edges[i]) if np.isfinite(edges[i]) else "-inf",
                "pred_high": float(edges[i + 1]) if np.isfinite(edges[i + 1]) else "inf",
                "n_val": n,
                "shift_ln_x2": shift,
                "equivalent_activity_bias": -shift,
            }
        )

    test_pred = test["ln_x2_pred"].to_numpy(dtype=float)
    test_bins = np.digitize(test_pred, edges[1:-1], right=False)
    shift_arr = np.asarray(shifts, dtype=float)
    calibrated = test_pred + shift_arr[test_bins]
    test_y = test["ln_x2_true"].to_numpy(dtype=float)
    applied_rows = []
    for i in range(len(edges) - 1):
        mask = test_bins == i
        if not mask.any():
            continue
        row = {
            "pred_bin": i,
            "n_test": int(mask.sum()),
            "shift_ln_x2": float(shift_arr[i]),
        }
        row.update(_metrics(test_y[mask], calibrated[mask]))
        applied_rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(applied_rows), calibrated


def _table(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return df.to_string(index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--val", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--n-pred-bins", type=int, default=5)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    splits = {
        "train": _load(args.train),
        "val": _load(args.val),
        "test": _load(args.test),
    }

    split_metrics = []
    quantity_rows = []
    for split, df in splits.items():
        split_metrics.append({"split": split, **_metrics(df["ln_x2_true"].to_numpy(), df["ln_x2_pred"].to_numpy())})
        for col in ["ln_gamma_inf", "ln_gamma_2", "Phi", "T_m_solver", "dH_fus_solver"]:
            quantity_rows.append(_summarize_quantity(df, col, split))

    split_metrics_df = pd.DataFrame(split_metrics)
    quantity_df = pd.DataFrame(quantity_rows)
    bin_bias_df = _bin_bias(splits["test"])

    val = splits["val"]
    test = splits["test"]
    val_resid = val["ln_x2_true"].to_numpy() - val["ln_x2_pred"].to_numpy()
    mean_shift = float(np.mean(val_resid))
    median_shift = float(np.median(val_resid))
    test_y = test["ln_x2_true"].to_numpy()
    test_pred = test["ln_x2_pred"].to_numpy()
    calibrations = {
        "none": _metrics(test_y, test_pred),
        "val_mean_shift": {
            "shift_ln_x2": mean_shift,
            "equivalent_activity_bias": -mean_shift,
            **_metrics(test_y, test_pred + mean_shift),
        },
        "val_median_shift": {
            "shift_ln_x2": median_shift,
            "equivalent_activity_bias": -median_shift,
            **_metrics(test_y, test_pred + median_shift),
        },
    }
    test_resid = test_y - test_pred
    oracle_median_shift = float(np.median(test_resid))
    calibrations["test_oracle_median_shift"] = {
        "shift_ln_x2": oracle_median_shift,
        "equivalent_activity_bias": -oracle_median_shift,
        **_metrics(test_y, test_pred + oracle_median_shift),
    }
    pred_bin_table, pred_bin_applied, pred_bin_calibrated = _prediction_bin_calibration(
        val=val,
        test=test,
        n_bins=args.n_pred_bins,
        statistic="median",
    )
    calibrations[f"val_pred_bin{args.n_pred_bins}_median_shift"] = {
        "shift_ln_x2": float("nan"),
        "equivalent_activity_bias": float("nan"),
        **_metrics(test_y, pred_bin_calibrated),
    }

    crystal = _crystal_replacement(test)
    summary = {
        "split_metrics": split_metrics,
        "calibration": calibrations,
        "crystal_replacement_on_test": crystal,
    }

    split_metrics_df.to_csv(args.out_dir / "split_metrics.csv", index=False)
    quantity_df.to_csv(args.out_dir / "quantity_distributions.csv", index=False)
    bin_bias_df.to_csv(args.out_dir / "test_bin_bias.csv", index=False)
    pred_bin_table.to_csv(args.out_dir / "prediction_bin_calibration.csv", index=False)
    pred_bin_applied.to_csv(args.out_dir / "prediction_bin_calibration_test_bins.csv", index=False)
    pd.DataFrame(
        [{"calibration": k, **v} for k, v in calibrations.items()]
    ).to_csv(args.out_dir / "calibration_metrics.csv", index=False)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )

    lines = ["# Direct activity bias diagnostics", ""]
    lines.append("## Split metrics")
    lines.append(_table(split_metrics_df))
    lines.append("")
    lines.append("## Calibration")
    lines.append(_table(pd.DataFrame([{"calibration": k, **v} for k, v in calibrations.items()])))
    lines.append("")
    lines.append(f"## Prediction-bin calibration ({args.n_pred_bins} validation bins)")
    lines.append(_table(pred_bin_table))
    lines.append("")
    lines.append("## Prediction-bin calibrated test slices")
    lines.append(_table(pred_bin_applied))
    lines.append("")
    lines.append("## Crystal replacement on test")
    lines.append(json.dumps(crystal, indent=2, ensure_ascii=False))
    lines.append("")
    lines.append("## Test bin bias")
    lines.append(_table(bin_bias_df))
    (args.out_dir / "SUMMARY.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
