#!/usr/bin/env python3
"""Generate publication figures from available experiment results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, TypeAlias

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from tgnn_solv.reporting import normalize_report_payload

PlottingFunctions: TypeAlias = dict[str, Callable[..., object]]


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generate paper figures from TGNN-Solv experiment outputs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results/",
        help="Directory containing experiment result files.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="figures/",
        help="Directory where figures will be saved.",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="pdf",
        choices=["pdf", "png", "svg"],
        help="Output figure format.",
    )
    return parser.parse_args()


def warn(message: str) -> None:
    """Print a non-fatal warning."""
    print(f"Warning: {message}")


def load_json(path: Path) -> object:
    """Load JSON content from disk."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def import_plotting() -> PlottingFunctions:
    """Import plotting utilities lazily.

    Lazy import keeps `--help` and missing-result flows usable even when the
    plotting stack is unavailable in the current environment.
    """
    from tgnn_solv.plotting import (
        setup_plot_style,
        parity_plot,
        residual_plot,
        error_distribution,
        ablation_bar_chart,
        learning_curve_plot,
        split_comparison_plot,
    )

    return {
        "setup_plot_style": setup_plot_style,
        "parity_plot": parity_plot,
        "residual_plot": residual_plot,
        "error_distribution": error_distribution,
        "ablation_bar_chart": ablation_bar_chart,
        "learning_curve_plot": learning_curve_plot,
        "split_comparison_plot": split_comparison_plot,
    }


def load_prediction_arrays(results_dir: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Load prediction targets from JSON or CSV files.

    The preferred source is `full_evaluation.json` with arrays stored under
    `true_ln_x2` and `pred_ln_x2`. If those arrays are not present, the function
    falls back to `predictions.csv` with `true` and `pred` columns.
    """
    json_path = results_dir / "full_evaluation.json"
    if json_path.exists():
        data = normalize_report_payload(load_json(json_path))
        true = data.get("true_ln_x2")
        pred = data.get("pred_ln_x2")
        if true is not None and pred is not None:
            true_arr = np.asarray(true, dtype=float)
            pred_arr = np.asarray(pred, dtype=float)
            if true_arr.shape == pred_arr.shape and true_arr.size > 0:
                return true_arr, pred_arr
        warn(
            f"{json_path} exists but does not contain usable "
            "'true_ln_x2'/'pred_ln_x2' arrays."
        )

    csv_path = results_dir / "predictions.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        if {"true", "pred"}.issubset(df.columns):
            return (
                df["true"].to_numpy(dtype=float),
                df["pred"].to_numpy(dtype=float),
            )
        warn(
            f"{csv_path} exists but does not contain the required "
            "'true' and 'pred' columns."
        )

    return None


def normalize_ablation_results(raw_results: object) -> dict[str, dict[str, float]]:
    """Normalize multiple possible ablation JSON layouts.

    Supported layouts:
    - `{"full": {"mae_mean": ..., "mae_std": ...}, ...}`
    - list of dicts with aggregated fields
    - list of per-seed rows with `ablation` and `mae`
    """
    if isinstance(raw_results, dict):
        if "variants" in raw_results and isinstance(raw_results["variants"], dict):
            summary = raw_results["variants"]
            if all(
                isinstance(value, dict)
                and "mae_mean" in value
                and "mae_std" in value
                for value in summary.values()
            ):
                return summary

        if all(
            isinstance(value, dict)
            and "mae_mean" in value
            and "mae_std" in value
            for value in raw_results.values()
        ):
            return raw_results

        if "summary" in raw_results and isinstance(raw_results["summary"], dict):
            summary = raw_results["summary"]
            if all(
                isinstance(value, dict)
                and "mae_mean" in value
                and "mae_std" in value
                for value in summary.values()
            ):
                return summary

    if isinstance(raw_results, list):
        if not raw_results:
            raise ValueError("Ablation result list is empty.")

        if all(
            isinstance(row, dict)
            and "ablation" in row
            and "mae_mean" in row
            and "mae_std" in row
            for row in raw_results
        ):
            return {
                row["ablation"]: {
                    "mae_mean": float(row["mae_mean"]),
                    "mae_std": float(row["mae_std"]),
                }
                for row in raw_results
            }

        if all(
            isinstance(row, dict)
            and "ablation" in row
            and "mae" in row
            for row in raw_results
        ):
            grouped: dict[str, list[float]] = {}
            for row in raw_results:
                grouped.setdefault(str(row["ablation"]), []).append(float(row["mae"]))

            return {
                name: {
                    "mae_mean": float(np.mean(values)),
                    "mae_std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                }
                for name, values in grouped.items()
            }

    raise ValueError("Unsupported ablation result format.")


def load_learning_curve_results(path: Path) -> dict[str, object]:
    """Load learning-curve JSON content."""
    data = load_json(path)
    if not isinstance(data, dict) or len(data) == 0:
        raise ValueError("Learning-curve data must be a non-empty dict.")
    if "results" in data:
        results = data.get("results")
        if not isinstance(results, dict) or not results:
            raise ValueError("Learning-curve payload does not contain a usable 'results' dict.")
        return results
    return data


def generate_figure_2(results_dir: Path, output_dir: Path, fmt: str) -> Path | None:
    """Generate Figure 2: parity plot."""
    arrays = load_prediction_arrays(results_dir)
    if arrays is None:
        warn("Skipping Figure 2: no usable parity-plot data found.")
        return None

    plotting = import_plotting()
    true, pred = arrays
    save_path = output_dir / f"fig2_parity.{fmt}"
    plotting["parity_plot"](true, pred, title="Parity Plot", save_path=save_path)
    return save_path


def generate_figure_3(results_dir: Path, output_dir: Path, fmt: str) -> Path | None:
    """Generate Figure 3: ablation chart."""
    path = results_dir / "ablation.json"
    if not path.exists():
        warn("Skipping Figure 3: results/ablation.json not found.")
        return None

    plotting = import_plotting()
    ablation_results = normalize_ablation_results(load_json(path))
    save_path = output_dir / f"fig3_ablation.{fmt}"
    plotting["ablation_bar_chart"](ablation_results, save_path=save_path)
    return save_path


def generate_figure_4(results_dir: Path, output_dir: Path, fmt: str) -> Path | None:
    """Generate Figure 4: absolute-error distribution."""
    arrays = load_prediction_arrays(results_dir)
    if arrays is None:
        warn("Skipping Figure 4: no usable error-distribution data found.")
        return None

    plotting = import_plotting()
    true, pred = arrays
    save_path = output_dir / f"fig4_error_dist.{fmt}"
    plotting["error_distribution"](true, pred, save_path=save_path)
    return save_path


def generate_figure_5(results_dir: Path, output_dir: Path, fmt: str) -> Path | None:
    """Generate Figure 5: learning curves."""
    path = results_dir / "learning_curves.json"
    if not path.exists():
        warn("Skipping Figure 5: results/learning_curves.json not found.")
        return None

    plotting = import_plotting()
    learning_results = load_learning_curve_results(path)
    save_path = output_dir / f"fig5_learning_curves.{fmt}"
    plotting["learning_curve_plot"](learning_results, save_path=save_path)
    return save_path


def generate_figure_s1(results_dir: Path, output_dir: Path, fmt: str) -> Path | None:
    """Generate Supplementary Figure S1: residual plot."""
    arrays = load_prediction_arrays(results_dir)
    if arrays is None:
        warn("Skipping Figure S1: no usable residual-plot data found.")
        return None

    plotting = import_plotting()
    true, pred = arrays
    save_path = output_dir / f"figS1_residuals.{fmt}"
    plotting["residual_plot"](true, pred, save_path=save_path)
    return save_path


def generate_figure_s2(results_dir: Path, output_dir: Path, fmt: str) -> Path | None:
    """Generate Supplementary Figure S2: split-wise comparison plot."""
    path = results_dir / "split_comparisons.json"
    if not path.exists():
        warn("Skipping Figure S2: results/split_comparisons.json not found.")
        return None

    payload = load_json(path)
    if not isinstance(payload, dict):
        warn("Skipping Figure S2: split_comparisons.json is not a JSON object.")
        return None

    plotting = import_plotting()
    save_path = output_dir / f"figS2_split_comparison.{fmt}"
    plotting["split_comparison_plot"](payload, save_path=save_path)
    return save_path


def main() -> None:
    """Generate all available paper figures without failing on missing results."""
    args = parse_args()

    results_dir = _bootstrap.resolve_path(args.results_dir)
    output_dir = _bootstrap.resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    figure_builders = [
        ("Figure 2", generate_figure_2),
        ("Figure 3", generate_figure_3),
        ("Figure 4", generate_figure_4),
        ("Figure 5", generate_figure_5),
        ("Figure S1", generate_figure_s1),
        ("Figure S2", generate_figure_s2),
    ]

    generated_files: list[Path] = []
    for label, builder in figure_builders:
        try:
            path = builder(results_dir, output_dir, args.format)
            if path is not None:
                generated_files.append(path)
        except Exception as exc:
            warn(f"Skipping {label}: {exc}")

    print(f"Generated {len(generated_files)} figures in {output_dir}:")
    for path in generated_files:
        print(f"  {path}")


if __name__ == "__main__":
    main()
