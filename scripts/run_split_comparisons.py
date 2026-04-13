#!/usr/bin/env python3
"""Run multi-model comparisons across all canonical split protocols."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import pandas as pd

from tgnn_solv.data.split_registry import (
    build_split_metadata,
    get_split_display_name,
    resolve_split_modes,
    split_paths,
)
from tgnn_solv.reporting import json_safe

try:
    from scipy.stats import t as student_t
except Exception:  # pragma: no cover - optional dependency
    student_t = None


MODEL_LABELS = {
    "tgnn_solv": "TGNN-Solv",
    "direct_gnn": "DirectGNN",
    "rf_baseline": "RF Baseline",
    "rf_morgan": "RF Morgan",
    "rf_hybrid": "RF Hybrid",
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run split-wise model comparisons for TGNN-Solv and baselines.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--processed-dir",
        type=str,
        default="notebooks/data/processed",
        help="Directory containing processed split CSV files.",
    )
    parser.add_argument(
        "--splits",
        type=str,
        default="all",
        help="Comma-separated split modes or 'all'.",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="tgnn_solv,direct_gnn,rf_baseline",
        help="Comma-separated model names to compare.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/paper_config.yaml",
        help="Config file for TGNN-Solv and DirectGNN.",
    )
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=3,
        help="Number of seeds per split and model.",
    )
    parser.add_argument(
        "--base-seed",
        type=int,
        default=42,
        help="Base seed for sequential seed sweeps.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Device passed to training scripts.",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results/split_comparisons",
        help="Directory for per-split result artifacts.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/split_comparisons.json",
        help="Path for the aggregate split comparison JSON.",
    )
    parser.add_argument(
        "--checkpoint-root",
        type=str,
        default="checkpoints/split_comparisons",
        help="Root directory for split-wise checkpoints.",
    )
    parser.add_argument(
        "--rf-n-estimators",
        type=int,
        default=500,
        help="Number of trees for RF baselines; reduce for local proxy runs.",
    )
    parser.add_argument(
        "--skip-significance",
        action="store_true",
        help="Skip per-split significance testing.",
    )
    return parser.parse_args()


def parse_model_names(models_spec: str) -> list[str]:
    """Parse and validate a comma-separated model list."""
    models = [item.strip() for item in models_spec.split(",") if item.strip()]
    if not models:
        raise ValueError("At least one model must be specified.")

    supported = set(MODEL_LABELS)
    unknown = [model for model in models if model not in supported]
    if unknown:
        raise ValueError(
            f"Unknown model(s): {unknown}. Expected a subset of {sorted(supported)}."
        )
    return models


def to_float(value: object) -> float | None:
    """Convert a value to a finite float when possible."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def compute_confidence_interval(values: list[float], mean: float, std: float) -> tuple[float | None, float | None]:
    """Compute a 95% confidence interval for one metric list."""
    n = len(values)
    if n == 0:
        return None, None
    if n == 1 or std == 0.0:
        return mean, mean

    sem = std / math.sqrt(n)
    if student_t is not None:
        ci_low, ci_high = student_t.interval(0.95, df=n - 1, loc=mean, scale=sem)
        if math.isfinite(ci_low) and math.isfinite(ci_high):
            return float(ci_low), float(ci_high)

    margin = 1.96 * sem
    return mean - margin, mean + margin


def aggregate_metric(values: list[float]) -> dict[str, Any]:
    """Aggregate one metric across multiple seeds."""
    if not values:
        return {
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "ci_95_low": None,
            "ci_95_high": None,
            "values": [],
        }

    mean = sum(values) / len(values)
    if len(values) == 1:
        std = 0.0
    else:
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        std = math.sqrt(variance)
    ci_low, ci_high = compute_confidence_interval(values, mean, std)
    return {
        "mean": mean,
        "std": std,
        "min": min(values),
        "max": max(values),
        "ci_95_low": ci_low,
        "ci_95_high": ci_high,
        "values": values,
    }


def aggregate_per_seed(per_seed: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate standard regression metrics over per-seed rows."""
    metrics = ("mae", "rmse", "r2", "pearson_r")
    aggregated: dict[str, dict[str, Any]] = {}
    for metric in metrics:
        values = [
            value
            for record in per_seed
            if (value := to_float(record.get(metric))) is not None
        ]
        aggregated[metric] = aggregate_metric(values)
    return aggregated


def build_rf_multi_seed_results(
    train_path: Path,
    test_path: Path,
    split_mode: str,
    n_seeds: int,
    base_seed: int,
    output_path: Path,
    feature_mode: str = "descriptors",
    n_estimators: int = 500,
) -> dict[str, Any]:
    """Train and evaluate the RF baseline across seeds on one split."""
    from tgnn_solv.baselines.rf_baseline import RFBaseline

    train_df = pd.read_csv(train_path, low_memory=False)
    test_df = pd.read_csv(test_path, low_memory=False)

    per_seed: list[dict[str, Any]] = []
    seeds = [base_seed + idx for idx in range(n_seeds)]
    for seed in seeds:
        print(f"  [rf:{feature_mode}][seed {seed}] fitting...")
        model = RFBaseline(
            random_state=seed,
            feature_mode=feature_mode,
            n_estimators=n_estimators,
        )
        model.fit(train_df)
        metrics = model.evaluate(test_df)
        per_seed.append(
            {
                "seed": seed,
                "checkpoint": None,
                "mae": to_float(metrics.get("mae")),
                "rmse": to_float(metrics.get("rmse")),
                "r2": to_float(metrics.get("r2")),
                "pearson_r": to_float(metrics.get("pearson_r")),
                "n_samples": int(metrics.get("n_samples", 0)),
                "n_skipped": int(metrics.get("n_skipped", 0)),
            }
        )

    aggregated = aggregate_per_seed(per_seed)
    valid_mae = [record for record in per_seed if record.get("mae") is not None]
    best_seed = None
    if valid_mae:
        best = min(valid_mae, key=lambda record: float(record["mae"]))
        best_seed = {"seed": best["seed"], "mae": best["mae"], "checkpoint": None}

    payload = {
        "model": f"rf_{feature_mode}",
        "n_estimators": int(n_estimators),
        "split": build_split_metadata(
            split_mode=split_mode,
            train_data=train_path,
            test_data=test_path,
        ),
        "split_mode": split_mode,
        "n_seeds": n_seeds,
        "seeds": seeds,
        "aggregated": aggregated,
        "per_seed": per_seed,
        "best_seed": best_seed,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")
    return payload


def run_subprocess(cmd: list[str]) -> None:
    """Run a subprocess and fail loudly on non-zero exit."""
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)


def run_seed_sweep(
    train_script: str,
    *,
    config_path: Path,
    train_path: Path,
    val_path: Path,
    test_path: Path,
    split_mode: str,
    output_path: Path,
    checkpoint_dir: Path,
    device: str,
    n_seeds: int,
    base_seed: int,
) -> dict[str, Any]:
    """Run scripts/run_seeds.py for one model and split."""
    cmd = [
        sys.executable,
        str(_bootstrap.resolve_path("scripts/run_seeds.py")),
        "--train-script",
        str(_bootstrap.resolve_path(train_script)),
        "--config",
        str(config_path),
        "--train-data",
        str(train_path),
        "--val-data",
        str(val_path),
        "--test-data",
        str(test_path),
        "--split-mode",
        split_mode,
        "--n-seeds",
        str(n_seeds),
        "--base-seed",
        str(base_seed),
        "--output",
        str(output_path),
        "--checkpoint-dir",
        str(checkpoint_dir),
        "--device",
        device,
    ]
    run_subprocess(cmd)
    return json.loads(output_path.read_text(encoding="utf-8"))


def summarize_split_rows(split_payload: dict[str, Any], model_order: list[str]) -> dict[str, object]:
    """Build a flat row summary for one split."""
    row: dict[str, object] = {
        "Split": split_payload["split"]["display_name"],
        "Split mode": split_payload["split"]["mode"],
    }
    best_model = None
    best_mae = None
    for model_name in model_order:
        model_payload = split_payload["models"].get(model_name)
        if not isinstance(model_payload, dict):
            continue
        aggregated = model_payload.get("aggregated", {})
        mae = to_float(aggregated.get("mae", {}).get("mean")) if isinstance(aggregated, dict) else None
        std = to_float(aggregated.get("mae", {}).get("std")) if isinstance(aggregated, dict) else None
        if mae is None:
            row[MODEL_LABELS[model_name]] = "n/a"
            continue
        row[MODEL_LABELS[model_name]] = f"{mae:.3f} ± {0.0 if std is None else std:.3f}"
        if best_mae is None or mae < best_mae:
            best_mae = mae
            best_model = MODEL_LABELS[model_name]
    row["Best"] = best_model or "n/a"
    return row


def print_summary_table(payload: dict[str, Any], model_order: list[str]) -> None:
    """Print a compact split-wise comparison table."""
    headers = ["Split", "N_test", *[MODEL_LABELS[model] for model in model_order], "Best"]
    widths = [20, 8, *([18] * len(model_order)), 14]
    print()
    print("Split-wise Comparison Summary")
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))
    print(" | ".join(f"{header:<{width}}" for header, width in zip(headers, widths)))
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))
    for split_mode in payload["split_order"]:
        split_payload = payload["splits"][split_mode]
        test_data = split_payload["split"].get("test_data")
        n_test = "n/a"
        if isinstance(test_data, str) and test_data:
            test_path = Path(test_data)
            if test_path.exists():
                with test_path.open("r", encoding="utf-8") as handle:
                    n_test = str(max(sum(1 for _ in handle) - 1, 0))
        row = summarize_split_rows(split_payload, model_order)
        values = [row["Split"], n_test, *[row.get(MODEL_LABELS[model], "n/a") for model in model_order], row["Best"]]
        print(" | ".join(f"{str(value):<{width}}" for value, width in zip(values, widths)))


def main() -> int:
    """Run the full split-wise comparison workflow."""
    args = parse_args()
    processed_dir = _bootstrap.resolve_path(args.processed_dir)
    config_path = _bootstrap.resolve_path(args.config)
    results_dir = _bootstrap.resolve_path(args.results_dir)
    output_path = _bootstrap.resolve_path(args.output)
    checkpoint_root = _bootstrap.resolve_path(args.checkpoint_root)

    split_modes = resolve_split_modes(args.splits)
    model_order = parse_model_names(args.models)

    results_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_root.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "split_order": split_modes,
        "model_order": model_order,
        "splits": {},
    }

    for split_mode in split_modes:
        paths = split_paths(processed_dir, split_mode)
        missing = [path for path in paths.values() if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                f"Missing processed CSVs for split {split_mode}: {missing}. "
                "Run scripts/prepare_data.py first."
            )

        split_output_dir = results_dir / split_mode
        split_output_dir.mkdir(parents=True, exist_ok=True)
        split_payload = {
            "split": build_split_metadata(
                split_mode=split_mode,
                train_data=paths["train"],
                val_data=paths["val"],
                test_data=paths["test"],
            ),
            "models": {},
        }
        print(f"\n=== {get_split_display_name(split_mode)} ===")

        for model_name in model_order:
            model_output_path = split_output_dir / f"{model_name}_multi_seed_results.json"
            if model_name == "tgnn_solv":
                result = run_seed_sweep(
                    "scripts/train.py",
                    config_path=config_path,
                    train_path=paths["train"],
                    val_path=paths["val"],
                    test_path=paths["test"],
                    split_mode=split_mode,
                    output_path=model_output_path,
                    checkpoint_dir=checkpoint_root / split_mode / model_name,
                    device=args.device,
                    n_seeds=args.n_seeds,
                    base_seed=args.base_seed,
                )
            elif model_name == "direct_gnn":
                result = run_seed_sweep(
                    "scripts/train_directgnn.py",
                    config_path=config_path,
                    train_path=paths["train"],
                    val_path=paths["val"],
                    test_path=paths["test"],
                    split_mode=split_mode,
                    output_path=model_output_path,
                    checkpoint_dir=checkpoint_root / split_mode / model_name,
                    device=args.device,
                    n_seeds=args.n_seeds,
                    base_seed=args.base_seed,
                )
            else:
                rf_mode = {
                    "rf_baseline": "descriptors",
                    "rf_morgan": "morgan",
                    "rf_hybrid": "hybrid",
                }[model_name]
                result = build_rf_multi_seed_results(
                    train_path=paths["train"],
                    test_path=paths["test"],
                    split_mode=split_mode,
                    n_seeds=args.n_seeds,
                    base_seed=args.base_seed,
                    output_path=model_output_path,
                    feature_mode=rf_mode,
                    n_estimators=args.rf_n_estimators,
                )

            split_payload["models"][model_name] = {
                "label": MODEL_LABELS[model_name],
                "result_file": str(model_output_path),
                "aggregated": result.get("aggregated", {}),
                "per_seed": result.get("per_seed", []),
                "best_seed": result.get("best_seed"),
            }

        if len(split_payload["models"]) >= 2 and not args.skip_significance:
            significance_path = split_output_dir / "significance.json"
            result_files = [
                str(split_output_dir / f"{model_name}_multi_seed_results.json")
                for model_name in model_order
                if model_name in split_payload["models"]
            ]
            labels = [MODEL_LABELS[model_name] for model_name in model_order if model_name in split_payload["models"]]
            cmd = [
                sys.executable,
                str(_bootstrap.resolve_path("scripts/statistical_tests.py")),
                "--results",
                *result_files,
                "--labels",
                *labels,
                "--output",
                str(significance_path),
            ]
            run_subprocess(cmd)
            split_payload["significance_file"] = str(significance_path)
            split_payload["significance"] = json.loads(significance_path.read_text(encoding="utf-8"))

        payload["splits"][split_mode] = split_payload

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")

    print_summary_table(payload, model_order)
    print()
    print(f"Saved split comparison results to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
