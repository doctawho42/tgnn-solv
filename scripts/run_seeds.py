#!/usr/bin/env python3
"""Run TGNN-Solv training across multiple random seeds and aggregate metrics."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
from tgnn_solv.data.split_registry import build_split_metadata

try:
    from scipy.stats import t as student_t
except Exception:  # pragma: no cover - optional dependency
    student_t = None


METRICS = ("mae", "rmse", "r2", "pearson_r")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Train TGNN-Solv with multiple seeds and aggregate metrics.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--train-script",
        type=str,
        default="scripts/train.py",
        help="Training entrypoint to execute for each seed.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/paper_config.yaml",
        help="Path to YAML configuration file.",
    )
    parser.add_argument(
        "--train-data",
        type=str,
        required=True,
        help="Path to training CSV file.",
    )
    parser.add_argument(
        "--val-data",
        type=str,
        required=True,
        help="Path to validation CSV file.",
    )
    parser.add_argument(
        "--test-data",
        type=str,
        required=True,
        help="Path to test CSV file.",
    )
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=5,
        help="Number of sequential seeds to run.",
    )
    parser.add_argument(
        "--base-seed",
        type=int,
        default=42,
        help="Base seed; each run uses base_seed + i.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/multi_seed_results.json",
        help="Path to save aggregated JSON results.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="checkpoints/seeds/",
        help="Directory for per-seed checkpoints.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Device to pass to scripts/train.py.",
    )
    parser.add_argument(
        "--split-mode",
        type=str,
        default=None,
        help="Optional explicit split label for result metadata.",
    )
    return parser.parse_args()


def _to_float(value: object) -> float | None:
    """Convert a value to a finite float or return None."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def extract_last_json_block(stdout: str) -> dict[str, Any]:
    """Extract the last valid top-level JSON object from stdout."""
    in_string = False
    escape = False
    depth = 0
    block_start = None
    last_object = None

    for idx, char in enumerate(stdout):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            if depth == 0:
                block_start = idx
            depth += 1
            continue

        if char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and block_start is not None:
                candidate = stdout[block_start:idx + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    last_object = parsed

    if last_object is None:
        raise ValueError("Could not find a JSON metrics block in stdout.")

    return last_object


def compute_confidence_interval(values: list[float], mean: float, std: float) -> tuple[float, float]:
    """Compute a 95% confidence interval for the sample mean."""
    n = len(values)
    if n == 0:
        return None, None  # type: ignore[return-value]
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
    """Aggregate a list of metric values."""
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

    n = len(values)
    mean = sum(values) / n
    if n == 1:
        std = 0.0
    else:
        variance = sum((value - mean) ** 2 for value in values) / (n - 1)
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


def build_train_command(args: argparse.Namespace, seed: int) -> tuple[list[str], str]:
    """Build the subprocess command and checkpoint path for one seed."""
    checkpoint_path = str(Path(args.checkpoint_dir) / f"seed_{seed}.pt")
    script_stem = Path(args.train_script).stem or "train"
    log_dir = str(Path("logs") / script_stem / f"seed_{seed}")
    cmd = [
        sys.executable,
        args.train_script,
        "--config",
        args.config,
        "--train-data",
        args.train_data,
        "--val-data",
        args.val_data,
        "--test-data",
        args.test_data,
        "--seed",
        str(seed),
        "--checkpoint",
        checkpoint_path,
        "--device",
        args.device,
        "--log-dir",
        log_dir,
    ]
    return cmd, checkpoint_path


def run_training_for_seed(args: argparse.Namespace, seed: int) -> dict[str, Any] | None:
    """Train a single seed and return extracted metrics."""
    cmd, checkpoint_path = build_train_command(args, seed)
    print(f"\n[seed {seed}] Starting training...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[seed {seed}] Training failed.", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
        return None

    try:
        metrics = extract_last_json_block(result.stdout)
    except ValueError as exc:
        print(f"[seed {seed}] {exc}", file=sys.stderr)
        stdout_tail = result.stdout[-4000:].strip()
        if stdout_tail:
            print(stdout_tail, file=sys.stderr, end="" if stdout_tail.endswith("\n") else "\n")
        return None

    record = {
        "seed": seed,
        "checkpoint": checkpoint_path,
    }
    for metric in METRICS:
        record[metric] = _to_float(metrics.get(metric))

    summary = ", ".join(
        f"{metric}={record[metric]:.4f}" for metric in ("mae", "rmse", "r2")
        if record[metric] is not None
    )
    if summary:
        print(f"[seed {seed}] Completed: {summary}")
    else:
        print(f"[seed {seed}] Completed, but no aggregate metrics were found.")

    return record


def print_summary_table(aggregated: dict[str, dict[str, Any]]) -> None:
    """Print an aggregated metrics table."""
    print()
    print(f"{'Metric':<12} {'Mean':>8} {'± Std':>8} {'95% CI':>20}")
    for metric in METRICS:
        stats = aggregated[metric]
        if stats["mean"] is None:
            mean_str = "n/a"
            std_str = "n/a"
            ci_str = "n/a"
        else:
            mean_str = f"{stats['mean']:.4f}"
            std_str = f"{stats['std']:.4f}"
            ci_str = f"[{stats['ci_95_low']:.4f}, {stats['ci_95_high']:.4f}]"
        print(f"{metric:<12} {mean_str:>8} {std_str:>8} {ci_str:>20}")


def main() -> int:
    """Run multi-seed training and save the aggregated report."""
    args = parse_args()
    args.train_script = str(_bootstrap.resolve_path(args.train_script))
    args.config = str(_bootstrap.resolve_path(args.config))
    args.train_data = str(_bootstrap.resolve_path(args.train_data))
    args.val_data = str(_bootstrap.resolve_path(args.val_data))
    args.test_data = str(_bootstrap.resolve_path(args.test_data))
    args.output = str(_bootstrap.resolve_path(args.output))
    args.checkpoint_dir = str(_bootstrap.resolve_path(args.checkpoint_dir))

    attempted_seeds = [args.base_seed + i for i in range(args.n_seeds)]
    per_seed = []

    Path(args.checkpoint_dir).mkdir(parents=True, exist_ok=True)

    for seed in attempted_seeds:
        result = run_training_for_seed(args, seed)
        if result is not None:
            per_seed.append(result)

    aggregated = {}
    for metric in METRICS:
        metric_values = [
            record[metric]
            for record in per_seed
            if record.get(metric) is not None
        ]
        aggregated[metric] = aggregate_metric(metric_values)

    best_seed = None
    valid_mae = [record for record in per_seed if record.get("mae") is not None]
    if valid_mae:
        best = min(valid_mae, key=lambda record: record["mae"])
        best_seed = {
            "seed": best["seed"],
            "mae": best["mae"],
            "checkpoint": best.get("checkpoint"),
        }

    split_metadata = build_split_metadata(
        split_mode=args.split_mode,
        train_data=args.train_data,
        val_data=args.val_data,
        test_data=args.test_data,
    )
    output_data = {
        "train_script": args.train_script,
        "split": split_metadata,
        "split_mode": split_metadata["mode"],
        "n_seeds": args.n_seeds,
        "seeds": attempted_seeds,
        "aggregated": aggregated,
        "per_seed": per_seed,
        "best_seed": best_seed,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(output_data, handle, indent=2)

    print_summary_table(aggregated)
    print(f"\nSaved aggregated results to {output_path}")
    if best_seed is not None:
        print(f"Best seed: {best_seed['seed']} (mae={best_seed['mae']:.4f})")

    return 0 if per_seed else 1


if __name__ == "__main__":
    raise SystemExit(main())
