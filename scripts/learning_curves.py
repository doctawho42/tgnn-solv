#!/usr/bin/env python3
"""Run learning-curve experiments for TGNN-Solv and baseline models."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from tgnn_solv.device import default_device


SUPPORTED_MODELS = {"tgnn_solv", "direct_gnn", "rf_baseline"}
METRICS = ("mae", "rmse", "r2", "pearson_r")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run learning-curve experiments across training-set fractions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/paper_config.yaml",
        help="Path to the base YAML configuration file.",
    )
    parser.add_argument(
        "--train-data",
        type=str,
        required=True,
        help="Path to the training CSV file.",
    )
    parser.add_argument(
        "--val-data",
        type=str,
        required=True,
        help="Path to the validation CSV file.",
    )
    parser.add_argument(
        "--test-data",
        type=str,
        required=True,
        help="Path to the test CSV file.",
    )
    parser.add_argument(
        "--fractions",
        type=str,
        default="0.01,0.05,0.1,0.2,0.5,1.0",
        help="Comma-separated fractions of the training set to use.",
    )
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=3,
        help="Number of sequential seeds per fraction and model.",
    )
    parser.add_argument(
        "--base-seed",
        type=int,
        default=42,
        help="Base random seed; each run uses base_seed + i.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/learning_curves.json",
        help="Path to save aggregated learning-curve results.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=default_device(),
        help=(
            "Device string forwarded to neural-model training scripts; defaults to "
            "whichever this box has, because the child raises on an accelerator it "
            "cannot deliver."
        ),
    )
    parser.add_argument(
        "--models",
        type=str,
        default="tgnn_solv",
        help="Comma-separated model names: tgnn_solv,direct_gnn,rf_baseline",
    )
    return parser.parse_args()


def parse_fraction_specs(raw: str) -> list[tuple[str, float]]:
    """Parse and validate requested train-set fractions."""
    specs: list[tuple[str, float]] = []
    seen: set[str] = set()
    for token in raw.split(","):
        label = token.strip()
        if not label or label in seen:
            continue
        try:
            value = float(label)
        except ValueError as exc:
            raise ValueError(f"Invalid fraction: {label}") from exc
        if not (0.0 < value <= 1.0):
            raise ValueError(f"Fraction must be in (0, 1]: {label}")
        specs.append((label, value))
        seen.add(label)
    if not specs:
        raise ValueError("At least one fraction must be provided.")
    return specs


def parse_models(raw: str) -> list[str]:
    """Parse and validate requested model names."""
    models: list[str] = []
    for token in raw.split(","):
        model_name = token.strip()
        if not model_name:
            continue
        if model_name not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model '{model_name}'. Expected one of {sorted(SUPPORTED_MODELS)}."
            )
        if model_name not in models:
            models.append(model_name)
    if not models:
        raise ValueError("At least one model must be provided.")
    return models


def to_float(value: object) -> float | None:
    """Convert a value to a finite float."""
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
    start_idx = None
    last_object: dict[str, Any] | None = None

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
                start_idx = idx
            depth += 1
            continue

        if char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start_idx is not None:
                candidate = stdout[start_idx:idx + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    last_object = parsed

    if last_object is None:
        raise ValueError("Could not find a JSON metrics block in stdout.")
    return last_object


def stratified_sample(
    df: pd.DataFrame,
    n: int,
    seed: int,
    group_col: str = "solvent_smiles",
) -> pd.DataFrame:
    """Sample rows while approximately preserving the solvent distribution."""
    if group_col not in df.columns:
        raise ValueError(f"Missing group column: {group_col}")

    total = len(df)
    if total == 0:
        raise ValueError("Training dataframe is empty.")

    n = max(1, min(int(n), total))
    rng = np.random.RandomState(seed)
    groups = list(df.groupby(group_col, dropna=False))
    group_sizes = {group_name: len(group_df) for group_name, group_df in groups}

    if n < len(groups):
        chosen_groups = rng.choice(len(groups), size=n, replace=False)
        sampled_parts = []
        for idx in chosen_groups:
            _, group_df = groups[int(idx)]
            sampled_parts.append(group_df.sample(n=1, random_state=int(rng.randint(0, 2**31 - 1))))
        subset = pd.concat(sampled_parts, axis=0)
        return subset.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    allocations: dict[Any, int] = {}
    for group_name, group_df in groups:
        allocations[group_name] = max(1, int(len(group_df) * n / total))

    allocated = sum(allocations.values())
    if allocated > n:
        reducible = [
            [group_name, allocations[group_name] - 1, group_sizes[group_name]]
            for group_name in allocations
            if allocations[group_name] > 1
        ]
        reducible.sort(key=lambda item: (item[2], item[1]), reverse=True)
        overflow = allocated - n
        idx = 0
        while overflow > 0 and reducible:
            group_name = reducible[idx % len(reducible)][0]
            if allocations[group_name] > 1:
                allocations[group_name] -= 1
                overflow -= 1
            idx += 1

    sampled_parts: list[pd.DataFrame] = []
    sampled_indices: set[int] = set()
    for group_name, group_df in groups:
        take_n = min(allocations.get(group_name, 0), len(group_df))
        if take_n <= 0:
            continue
        sampled = group_df.sample(
            n=take_n,
            random_state=int(rng.randint(0, 2**31 - 1)),
            replace=False,
        )
        sampled_parts.append(sampled)
        sampled_indices.update(int(idx) for idx in sampled.index)

    subset = pd.concat(sampled_parts, axis=0) if sampled_parts else df.sample(n=0)

    if len(subset) < n:
        remaining = df.loc[~df.index.isin(sampled_indices)]
        extra_n = min(n - len(subset), len(remaining))
        if extra_n > 0:
            extra = remaining.sample(
                n=extra_n,
                random_state=int(rng.randint(0, 2**31 - 1)),
                replace=False,
            )
            subset = pd.concat([subset, extra], axis=0)

    if len(subset) > n:
        subset = subset.sample(
            n=n,
            random_state=int(rng.randint(0, 2**31 - 1)),
            replace=False,
        )

    return subset.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def build_training_command(
    model_name: str,
    config_path: Path,
    train_path: Path,
    val_path: Path,
    test_path: Path,
    seed: int,
    checkpoint_path: Path,
    device: str,
    log_dir: Path,
) -> list[str]:
    """Build the subprocess command for a neural baseline run."""
    if model_name == "tgnn_solv":
        script_path = _bootstrap.resolve_path("scripts/train.py")
    elif model_name == "direct_gnn":
        script_path = _bootstrap.resolve_path("scripts/train_directgnn.py")
    else:
        raise ValueError(f"Unsupported subprocess model: {model_name}")

    return [
        sys.executable,
        str(script_path),
        "--config",
        str(config_path),
        "--train-data",
        str(train_path),
        "--val-data",
        str(val_path),
        "--test-data",
        str(test_path),
        "--checkpoint",
        str(checkpoint_path),
        "--seed",
        str(seed),
        "--device",
        device,
        "--log-dir",
        str(log_dir),
    ]


def run_subprocess_model(
    model_name: str,
    config_path: Path,
    subset_train_path: Path,
    val_path: Path,
    test_path: Path,
    seed: int,
    device: str,
    work_dir: Path,
) -> dict[str, Any] | None:
    """Train a neural model via an existing CLI and extract test metrics."""
    if model_name == "direct_gnn" and not _bootstrap.resolve_path("scripts/train_directgnn.py").is_file():
        print("WARNING: scripts/train_directgnn.py not found; skipping DirectGNN.")
        return None

    checkpoint_path = work_dir / f"{model_name}_seed_{seed}.pt"
    log_dir = work_dir / "logs" / model_name / f"seed_{seed}"
    cmd = build_training_command(
        model_name=model_name,
        config_path=config_path,
        train_path=subset_train_path,
        val_path=val_path,
        test_path=test_path,
        seed=seed,
        checkpoint_path=checkpoint_path,
        device=device,
        log_dir=log_dir,
    )

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"WARNING: {model_name} seed {seed} failed.", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
        return None

    try:
        metrics = extract_last_json_block(result.stdout)
    except ValueError as exc:
        print(f"WARNING: {model_name} seed {seed}: {exc}", file=sys.stderr)
        stdout_tail = result.stdout[-4000:].strip()
        if stdout_tail:
            print(stdout_tail, file=sys.stderr, end="" if stdout_tail.endswith("\n") else "\n")
        return None

    record: dict[str, Any] = {
        "seed": seed,
        "checkpoint": str(checkpoint_path),
    }
    for metric in METRICS:
        record[metric] = to_float(metrics.get(metric))
    return record


def run_rf_baseline(
    subset_df: pd.DataFrame,
    test_df: pd.DataFrame,
    seed: int,
) -> dict[str, Any] | None:
    """Train and evaluate the RDKit Random Forest baseline."""
    try:
        from tgnn_solv.baselines.rf_baseline import RFBaseline
    except Exception as exc:
        print(f"WARNING: RF baseline unavailable: {exc}", file=sys.stderr)
        return None

    model = RFBaseline(random_state=seed)
    metrics = model.fit(subset_df).evaluate(test_df)
    record: dict[str, Any] = {"seed": seed}
    for metric in METRICS:
        record[metric] = to_float(metrics.get(metric))
    record["n_samples"] = int(metrics.get("n_samples", 0))
    record["n_skipped"] = int(metrics.get("n_skipped", 0))
    return record


def aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-seed metrics for one model."""
    aggregated: dict[str, Any] = {
        "seeds": [int(run["seed"]) for run in runs],
        "runs": runs,
    }
    for metric in METRICS:
        values = [
            float(run[metric])
            for run in runs
            if metric in run and run[metric] is not None and math.isfinite(float(run[metric]))
        ]
        if values:
            arr = np.asarray(values, dtype=float)
            aggregated[f"{metric}_mean"] = float(arr.mean())
            aggregated[f"{metric}_std"] = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
            aggregated[f"{metric}_values"] = values
        else:
            aggregated[f"{metric}_mean"] = None
            aggregated[f"{metric}_std"] = None
            aggregated[f"{metric}_values"] = []
    return aggregated


def print_summary_table(
    fraction_results: dict[str, dict[str, Any]],
    fraction_specs: list[tuple[str, float]],
    models: list[str],
) -> None:
    """Print the aggregated learning-curve table."""
    model_headers = {
        "tgnn_solv": "TGNN-Solv MAE",
        "direct_gnn": "DirectGNN MAE",
        "rf_baseline": "RF MAE",
    }

    columns = ["Fraction", "N_train"] + [model_headers[model] for model in models]
    widths = [10, 10] + [18 for _ in models]
    header = " | ".join(f"{col:<{width}}" for col, width in zip(columns, widths))
    print()
    print(header)
    print("-" * len(header))

    for label, _ in fraction_specs:
        entry = fraction_results.get(label)
        if entry is None:
            continue
        cells = [f"{label:<10}", f"{entry['n_samples']:<10}"]
        for model in models:
            model_data = entry.get(model)
            if model_data is None or model_data.get("mae_mean") is None:
                text = "n/a"
            else:
                text = f"{model_data['mae_mean']:.3f} ± {model_data['mae_std']:.3f}"
            cells.append(f"{text:<18}")
        print(" | ".join(cells))


def main() -> int:
    """Run the learning-curve sweep."""
    args = parse_args()

    config_path = _bootstrap.resolve_path(args.config)
    train_path = _bootstrap.resolve_path(args.train_data)
    val_path = _bootstrap.resolve_path(args.val_data)
    test_path = _bootstrap.resolve_path(args.test_data)
    output_path = _bootstrap.resolve_path(args.output)

    fraction_specs = parse_fraction_specs(args.fractions)
    models = parse_models(args.models)
    seeds = [args.base_seed + i for i in range(args.n_seeds)]

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    print("=" * 72)
    print("TGNN-Solv Learning-Curve Experiment")
    print("=" * 72)
    print(f"Config:     {config_path}")
    print(f"Train data: {train_path}")
    print(f"Val data:   {val_path}")
    print(f"Test data:  {test_path}")
    print(f"Models:     {', '.join(models)}")
    print(f"Fractions:  {', '.join(label for label, _ in fraction_specs)}")
    print(f"Seeds:      {seeds}")
    print("=" * 72)

    results: dict[str, dict[str, Any]] = {}

    with tempfile.TemporaryDirectory(prefix="tgnn_learning_curves_") as tmp_dir:
        tmp_root = Path(tmp_dir)

        for fraction_label, fraction_value in fraction_specs:
            n_subset = max(1, min(len(train_df), int(len(train_df) * fraction_value)))
            fraction_entry: dict[str, Any] = {
                "fraction": fraction_value,
                "n_samples": n_subset,
            }
            print()
            print(f"[Fraction {fraction_label}] n_train={n_subset}")

            for model_name in models:
                model_runs: list[dict[str, Any]] = []
                print(f"  Model: {model_name}")
                for seed in seeds:
                    subset_df = stratified_sample(train_df, n=n_subset, seed=seed)
                    subset_path = tmp_root / f"train_{fraction_label.replace('.', 'p')}_seed_{seed}.csv"
                    subset_df.to_csv(subset_path, index=False)

                    print(f"    Seed {seed}: subset={len(subset_df)}")
                    if model_name == "rf_baseline":
                        run_result = run_rf_baseline(subset_df, test_df, seed=seed)
                    else:
                        run_work_dir = tmp_root / "runs" / model_name / fraction_label.replace(".", "p") / f"seed_{seed}"
                        run_work_dir.mkdir(parents=True, exist_ok=True)
                        run_result = run_subprocess_model(
                            model_name=model_name,
                            config_path=config_path,
                            subset_train_path=subset_path,
                            val_path=val_path,
                            test_path=test_path,
                            seed=seed,
                            device=args.device,
                            work_dir=run_work_dir,
                        )

                    if run_result is None:
                        continue
                    model_runs.append(run_result)

                if not model_runs:
                    print(f"    WARNING: No successful runs for {model_name}.")
                    continue

                fraction_entry[model_name] = aggregate_runs(model_runs)

            results[fraction_label] = fraction_entry

    print_summary_table(results, fraction_specs, models)

    payload = {
        "fractions": [value for _, value in fraction_specs],
        "models": models,
        "n_seeds": args.n_seeds,
        "base_seed": args.base_seed,
        "seeds": seeds,
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print()
    print(f"Saved learning-curve results to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
