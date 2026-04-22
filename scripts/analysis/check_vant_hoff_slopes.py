#!/usr/bin/env python3
"""Analyze Van't Hoff slope recovery from prediction CSV files.

The script fits ln(x2) = slope * (1/T) + intercept for each
solute-solvent pair and compares true vs predicted slopes. It accepts both
multi-model baseline prediction CSVs and single-model neural prediction CSVs.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--predictions", required=True, help="Prediction CSV path.")
    parser.add_argument("--output-dir", required=True, help="Directory for slope artifacts.")
    parser.add_argument(
        "--model-name",
        default=None,
        help="Model name to use when the CSV has no model column.",
    )
    parser.add_argument(
        "--model-col",
        default="model",
        help="Column containing model names for multi-model CSVs.",
    )
    parser.add_argument(
        "--pair-col",
        default="pair_key",
        help="Column containing pair identifiers. If absent, solute>>solvent is built.",
    )
    parser.add_argument(
        "--temperature-col",
        default=None,
        help="Temperature column. Auto-detected from temperature, T, T_K when omitted.",
    )
    parser.add_argument(
        "--true-col",
        default=None,
        help="True ln(x2) column. Auto-detected from ln_x2_true, ln_x2 when omitted.",
    )
    parser.add_argument(
        "--pred-col",
        default=None,
        help="Predicted ln(x2) column. Auto-detected from ln_x2_pred, ln_x2_final when omitted.",
    )
    parser.add_argument(
        "--eval-split",
        default=None,
        help="Optional eval_split value to keep when the CSV has an eval_split column.",
    )
    parser.add_argument(
        "--min-temps",
        type=int,
        default=2,
        help="Minimum distinct temperatures per pair/model for slope fitting.",
    )
    parser.add_argument(
        "--slope-zero-tol",
        type=float,
        default=1e-9,
        help="Tolerance for excluding effectively zero true slopes from sign accuracy.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=25,
        help="Number of worst pairs to export per model.",
    )
    return parser.parse_args()


def _detect_column(df: pd.DataFrame, explicit: str | None, candidates: tuple[str, ...], label: str) -> str:
    if explicit:
        if explicit not in df.columns:
            raise ValueError(f"Requested {label} column {explicit!r} is absent.")
        return explicit
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    raise ValueError(
        f"Could not detect {label} column. Tried: {', '.join(candidates)}. "
        f"Available columns: {', '.join(map(str, df.columns))}"
    )


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _safe_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2 or np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    value = float(np.corrcoef(x, y)[0, 1])
    return value if math.isfinite(value) else None


def _rank_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    x_rank = pd.Series(x).rank(method="average").to_numpy(dtype=float)
    y_rank = pd.Series(y).rank(method="average").to_numpy(dtype=float)
    return _safe_corr(x_rank, y_rank)


def _fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Return slope, intercept, and R2 for y = slope * x + intercept."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    slope, intercept = np.polyfit(x, y, deg=1)
    pred = slope * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / (ss_tot + 1e-12)
    return float(slope), float(intercept), float(r2)


def _make_pair_key(df: pd.DataFrame, pair_col: str) -> pd.Series:
    if pair_col in df.columns:
        return df[pair_col].astype(str)
    if {"solute_smiles", "solvent_smiles"}.issubset(df.columns):
        return df["solute_smiles"].astype(str) + ">>" + df["solvent_smiles"].astype(str)
    raise ValueError(
        f"Pair column {pair_col!r} is absent and solute_smiles/solvent_smiles are not both available."
    )


def build_pair_slopes(
    df: pd.DataFrame,
    *,
    model_col: str,
    pair_col: str,
    temperature_col: str,
    true_col: str,
    pred_col: str,
    min_temps: int,
) -> pd.DataFrame:
    work = df.copy()
    work["_model"] = work[model_col].astype(str)
    work["_pair_key"] = _make_pair_key(work, pair_col)
    work["_T"] = pd.to_numeric(work[temperature_col], errors="coerce")
    work["_true"] = pd.to_numeric(work[true_col], errors="coerce")
    work["_pred"] = pd.to_numeric(work[pred_col], errors="coerce")
    work = work[np.isfinite(work["_T"]) & np.isfinite(work["_true"]) & np.isfinite(work["_pred"])]
    work = work[work["_T"] > 0.0]

    records: list[dict[str, Any]] = []
    for (model_name, pair_key), group in work.groupby(["_model", "_pair_key"], sort=False):
        distinct_temps = int(group["_T"].nunique(dropna=True))
        if distinct_temps < min_temps:
            continue
        group = group.sort_values("_T")
        x = (1.0 / group["_T"].to_numpy(dtype=float))
        y_true = group["_true"].to_numpy(dtype=float)
        y_pred = group["_pred"].to_numpy(dtype=float)
        if np.std(x) == 0.0:
            continue

        slope_true, intercept_true, r2_true = _fit_line(x, y_true)
        slope_pred, intercept_pred, r2_pred = _fit_line(x, y_pred)
        errors = y_pred - y_true
        records.append(
            {
                "model": model_name,
                "pair_key": pair_key,
                "n_rows": int(len(group)),
                "n_temps": distinct_temps,
                "temperature_min": float(group["_T"].min()),
                "temperature_max": float(group["_T"].max()),
                "temperature_span": float(group["_T"].max() - group["_T"].min()),
                "slope_true": slope_true,
                "slope_pred": slope_pred,
                "slope_error": slope_pred - slope_true,
                "abs_slope_error": abs(slope_pred - slope_true),
                "intercept_true": intercept_true,
                "intercept_pred": intercept_pred,
                "intercept_error": intercept_pred - intercept_true,
                "r2_true": r2_true,
                "r2_pred": r2_pred,
                "pair_bias": float(np.mean(errors)),
                "pair_mae": float(np.mean(np.abs(errors))),
                "pair_rmse": float(np.sqrt(np.mean(errors**2))),
                "true_delta_ln_x2": float(y_true[-1] - y_true[0]),
                "pred_delta_ln_x2": float(y_pred[-1] - y_pred[0]),
            }
        )
    return pd.DataFrame(records)


def summarize_model_slopes(pair_slopes: pd.DataFrame, *, slope_zero_tol: float) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model_name, group in pair_slopes.groupby("model", sort=False):
        slope_error = group["slope_error"].to_numpy(dtype=float)
        abs_slope_error = np.abs(slope_error)
        sign_mask = np.abs(group["slope_true"].to_numpy(dtype=float)) > slope_zero_tol
        if sign_mask.any():
            sign_accuracy = float(
                np.mean(
                    np.sign(group.loc[sign_mask, "slope_pred"].to_numpy(dtype=float))
                    == np.sign(group.loc[sign_mask, "slope_true"].to_numpy(dtype=float))
                )
            )
        else:
            sign_accuracy = None
        rows.append(
            {
                "model": str(model_name),
                "n_pairs": int(len(group)),
                "n_rows": int(group["n_rows"].sum()),
                "slope_mae_K": float(np.mean(abs_slope_error)),
                "slope_rmse_K": float(np.sqrt(np.mean(slope_error**2))),
                "slope_bias_K": float(np.mean(slope_error)),
                "slope_median_abs_error_K": float(np.median(abs_slope_error)),
                "slope_q90_abs_error_K": float(np.quantile(abs_slope_error, 0.90)),
                "slope_pearson_r": _safe_corr(
                    group["slope_true"].to_numpy(dtype=float),
                    group["slope_pred"].to_numpy(dtype=float),
                ),
                "slope_spearman_r": _rank_corr(
                    group["slope_true"].to_numpy(dtype=float),
                    group["slope_pred"].to_numpy(dtype=float),
                ),
                "slope_sign_accuracy": sign_accuracy,
                "mean_true_slope_K": float(group["slope_true"].mean()),
                "mean_pred_slope_K": float(group["slope_pred"].mean()),
                "pred_slope_std_K": float(group["slope_pred"].std(ddof=1)) if len(group) > 1 else 0.0,
                "pair_mae_mean": float(group["pair_mae"].mean()),
                "pair_mae_median": float(group["pair_mae"].median()),
                "pair_bias_mean": float(group["pair_bias"].mean()),
                "r2_true_mean": float(group["r2_true"].mean()),
                "r2_pred_mean": float(group["r2_pred"].mean()),
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["slope_mae_K", "pair_mae_mean"], ascending=[True, True])
    return out


def write_plots(pair_slopes: pd.DataFrame, output_dir: Path) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []

    artifacts: list[str] = []
    for model_name, group in pair_slopes.groupby("model", sort=False):
        safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(model_name))

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        axes[0].scatter(group["slope_true"], group["slope_pred"], alpha=0.45, s=12)
        finite = np.concatenate(
            [
                group["slope_true"].to_numpy(dtype=float),
                group["slope_pred"].to_numpy(dtype=float),
            ]
        )
        finite = finite[np.isfinite(finite)]
        if finite.size:
            lo = float(np.quantile(finite, 0.01))
            hi = float(np.quantile(finite, 0.99))
            if lo == hi:
                lo -= 1.0
                hi += 1.0
            axes[0].plot([lo, hi], [lo, hi], "r--", linewidth=1.0)
            axes[0].set_xlim(lo, hi)
            axes[0].set_ylim(lo, hi)
        axes[0].axhline(0.0, color="gray", linewidth=0.7)
        axes[0].axvline(0.0, color="gray", linewidth=0.7)
        axes[0].set_xlabel("True slope d ln(x2) / d(1/T), K")
        axes[0].set_ylabel("Predicted slope, K")
        axes[0].set_title(f"{model_name}: slope recovery")

        clipped = group["slope_error"].clip(-5000, 5000)
        axes[1].hist(clipped, bins=50, alpha=0.85, color="steelblue")
        axes[1].axvline(0.0, color="red", linestyle="--", linewidth=1.0)
        axes[1].set_xlabel("Slope error, K (clipped to +/-5000)")
        axes[1].set_title("Error distribution")

        fig.tight_layout()
        path = output_dir / f"{safe_name}_slope_diagnostics.png"
        fig.savefig(path, dpi=160, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(str(path))
    return artifacts


def build_markdown(
    *,
    predictions: Path,
    output_dir: Path,
    metrics: pd.DataFrame,
    pair_slopes: pd.DataFrame,
    args: argparse.Namespace,
    artifacts: list[str],
) -> str:
    lines = [
        "# Van't Hoff Slope Diagnostics",
        "",
        f"- Predictions: `{predictions}`",
        f"- Minimum distinct temperatures per pair: `{args.min_temps}`",
        f"- Pair slopes: `{output_dir / 'pair_slopes.csv'}`",
        f"- Metrics: `{output_dir / 'metrics_by_model.csv'}`",
        "",
        "## Metrics",
        "",
    ]
    if metrics.empty:
        lines.append("No eligible pair/model groups were found.")
    else:
        cols = [
            "model",
            "n_pairs",
            "slope_mae_K",
            "slope_bias_K",
            "slope_pearson_r",
            "slope_sign_accuracy",
            "pair_mae_mean",
            "r2_pred_mean",
        ]
        lines.append(metrics[cols].to_markdown(index=False, floatfmt=".4f"))
    lines.extend(["", "## Worst Pairs", ""])
    if not pair_slopes.empty:
        worst = pair_slopes.sort_values("abs_slope_error", ascending=False).head(10)
        lines.append(
            worst[
                [
                    "model",
                    "pair_key",
                    "n_temps",
                    "slope_true",
                    "slope_pred",
                    "abs_slope_error",
                    "pair_mae",
                ]
            ].to_markdown(index=False, floatfmt=".3f")
        )
    if artifacts:
        lines.extend(["", "## Plots", ""])
        for artifact in artifacts:
            lines.append(f"- `{artifact}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    predictions = Path(args.predictions).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(predictions, low_memory=False)
    if args.eval_split is not None and "eval_split" in df.columns:
        df = df[df["eval_split"].astype(str) == str(args.eval_split)].copy()

    model_col = args.model_col
    if model_col not in df.columns:
        model_name = args.model_name or predictions.stem
        df[model_col] = model_name

    temperature_col = _detect_column(
        df,
        args.temperature_col,
        ("temperature", "T", "T_K"),
        "temperature",
    )
    true_col = _detect_column(
        df,
        args.true_col,
        ("ln_x2_true", "ln_x2", "target"),
        "true ln(x2)",
    )
    pred_col = _detect_column(
        df,
        args.pred_col,
        ("ln_x2_pred", "ln_x2_final", "prediction", "pred"),
        "predicted ln(x2)",
    )

    pair_slopes = build_pair_slopes(
        df,
        model_col=model_col,
        pair_col=args.pair_col,
        temperature_col=temperature_col,
        true_col=true_col,
        pred_col=pred_col,
        min_temps=int(args.min_temps),
    )
    metrics = summarize_model_slopes(pair_slopes, slope_zero_tol=float(args.slope_zero_tol))

    pair_csv = output_dir / "pair_slopes.csv"
    metrics_csv = output_dir / "metrics_by_model.csv"
    worst_csv = output_dir / "worst_pairs.csv"
    summary_json = output_dir / "summary.json"
    summary_md = output_dir / "SUMMARY.md"

    pair_slopes.to_csv(pair_csv, index=False)
    metrics.to_csv(metrics_csv, index=False)
    if pair_slopes.empty:
        pd.DataFrame().to_csv(worst_csv, index=False)
    else:
        pair_slopes.sort_values(["model", "abs_slope_error"], ascending=[True, False]).groupby(
            "model", sort=False
        ).head(int(args.top_k)).to_csv(worst_csv, index=False)

    plot_artifacts = write_plots(pair_slopes, output_dir)

    summary = {
        "predictions": str(predictions),
        "output_dir": str(output_dir),
        "eval_split": args.eval_split,
        "columns": {
            "model": model_col,
            "pair": args.pair_col,
            "temperature": temperature_col,
            "true": true_col,
            "pred": pred_col,
        },
        "min_temps": int(args.min_temps),
        "n_input_rows": int(len(df)),
        "n_pair_slope_rows": int(len(pair_slopes)),
        "metrics": metrics.to_dict(orient="records"),
        "artifacts": {
            "pair_slopes_csv": str(pair_csv),
            "metrics_csv": str(metrics_csv),
            "worst_pairs_csv": str(worst_csv),
            "plots": plot_artifacts,
            "summary_md": str(summary_md),
        },
    }
    summary_json.write_text(json.dumps(_json_ready(summary), indent=2), encoding="utf-8")
    summary_md.write_text(
        build_markdown(
            predictions=predictions,
            output_dir=output_dir,
            metrics=metrics,
            pair_slopes=pair_slopes,
            args=args,
            artifacts=plot_artifacts,
        ),
        encoding="utf-8",
    )

    print(f"Wrote slope diagnostics to {output_dir}")
    if metrics.empty:
        print("No eligible pair/model groups found.")
    else:
        print(metrics.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
