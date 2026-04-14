#!/usr/bin/env python3
"""Aggregate proxy-comparison JSON outputs into one compact summary table."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate MAE/RMSE/R² from results/proxy_comparison JSON artifacts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--results-dir", type=str, default="results/proxy_comparison")
    parser.add_argument("--output", type=str, default=None)
    return parser.parse_args()


def finite_float(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def metric_from_mapping(data: dict[str, Any], names: tuple[str, ...]) -> float | None:
    for name in names:
        value = finite_float(data.get(name))
        if value is not None:
            return value
    return None


def extract_metrics(data: dict[str, Any]) -> dict[str, float | None] | None:
    """Support the metric shapes used by training, evaluation and RF scripts."""
    candidates: list[dict[str, Any]] = []
    if isinstance(data.get("overall"), dict):
        candidates.append(data["overall"])
    if isinstance(data.get("test_metrics"), dict):
        candidates.append(data["test_metrics"])
    if isinstance(data.get("metrics"), dict):
        candidates.append(data["metrics"])
    candidates.append(data)

    for candidate in candidates:
        mae = metric_from_mapping(candidate, ("mae", "test_mae", "MAE"))
        rmse = metric_from_mapping(candidate, ("rmse", "test_rmse", "RMSE"))
        r2 = metric_from_mapping(candidate, ("r2", "test_r2", "R2", "r²"))
        if mae is not None:
            return {"MAE": mae, "RMSE": rmse, "R2": r2}

    aggregated = data.get("aggregated")
    if isinstance(aggregated, dict):
        mae = finite_float((aggregated.get("mae") or {}).get("mean"))
        rmse = finite_float((aggregated.get("rmse") or {}).get("mean"))
        r2 = finite_float((aggregated.get("r2") or {}).get("mean"))
        if mae is not None:
            return {"MAE": mae, "RMSE": rmse, "R2": r2}
    return None


def extract_split_comparison_metrics(data: dict[str, Any]) -> dict[str, dict[str, float | None]]:
    """Extract RF-style nested metrics from run_split_comparisons output."""
    rows: dict[str, dict[str, float | None]] = {}
    splits = data.get("splits")
    if not isinstance(splits, dict):
        return rows

    for split_name, split_payload in splits.items():
        if not isinstance(split_payload, dict):
            continue
        models = split_payload.get("models")
        if not isinstance(models, dict):
            continue
        for model_name, model_payload in models.items():
            if not isinstance(model_payload, dict):
                continue
            metrics = extract_metrics(model_payload)
            if metrics is None:
                continue
            key = str(model_name)
            if len(splits) > 1:
                key = f"{split_name}_{key}"
            rows[key] = metrics
    return rows


def model_name_for_file(path: Path, results_dir: Path) -> str:
    if path.name == "metrics.json":
        return str(path.parent.relative_to(results_dir)).replace("/", "_")
    return path.stem


def iter_result_json(results_dir: Path) -> list[Path]:
    skip_suffixes = {".manifest", ".card", ".model_card"}
    paths: list[Path] = []
    for path in sorted(results_dir.rglob("*.json")):
        if path.name == "summary.json":
            continue
        if any(path.stem.endswith(suffix) for suffix in skip_suffixes):
            continue
        if path.name in {"channel_check.json"}:
            continue
        paths.append(path)
    return paths


def main() -> None:
    args = parse_args()
    results_dir = Path(args.results_dir).resolve()
    output_path = Path(args.output).resolve() if args.output else results_dir / "summary.json"

    summary: dict[str, dict[str, float | None]] = {}
    for path in iter_result_json(results_dir):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        nested = extract_split_comparison_metrics(data)
        if nested:
            summary.update(nested)
            continue
        metrics = extract_metrics(data)
        if metrics is None:
            continue
        summary[model_name_for_file(path, results_dir)] = metrics

    print(f"{'Model':<34} {'MAE':>8} {'RMSE':>8} {'R²':>8}")
    print("-" * 64)
    for name, metrics in sorted(summary.items(), key=lambda item: item[1].get("MAE") or 99.0):
        mae = f"{metrics['MAE']:.3f}" if metrics.get("MAE") is not None else "—"
        rmse = f"{metrics['RMSE']:.3f}" if metrics.get("RMSE") is not None else "—"
        r2 = f"{metrics['R2']:.3f}" if metrics.get("R2") is not None else "—"
        print(f"{name:<34} {mae:>8} {rmse:>8} {r2:>8}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
