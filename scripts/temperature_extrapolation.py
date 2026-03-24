#!/usr/bin/env python3
"""Run temperature-extrapolation experiments for TGNN-Solv and DirectGNN."""

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


METRICS = ("mae", "rmse", "r2", "pearson_r")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Train below a temperature cutoff and test above it.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/paper_config.yaml",
        help="Path to the base YAML configuration file.",
    )
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="Path to the combined dataset CSV.",
    )
    parser.add_argument(
        "--t-cuts",
        type=str,
        default="298.15,323.15,348.15,373.15",
        help="Comma-separated temperature cutoffs in Kelvin.",
    )
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=3,
        help="Number of sequential seeds per cutoff.",
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
        default="results/temperature_extrapolation.json",
        help="Path to save aggregated results.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Device string forwarded to training scripts.",
    )
    parser.add_argument(
        "--min-pairs",
        type=int,
        default=50,
        help="Minimum number of cross-temperature pairs required for a cutoff.",
    )
    return parser.parse_args()


def parse_t_cut_specs(raw: str) -> list[tuple[str, float]]:
    """Parse and validate temperature cutoffs."""
    specs: list[tuple[str, float]] = []
    seen: set[str] = set()
    for token in raw.split(","):
        label = token.strip()
        if not label or label in seen:
            continue
        try:
            value = float(label)
        except ValueError as exc:
            raise ValueError(f"Invalid temperature cutoff: {label}") from exc
        specs.append((label, value))
        seen.add(label)
    if not specs:
        raise ValueError("At least one temperature cutoff must be provided.")
    return specs


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


def filter_valid_solubility_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows with usable solubility targets and temperatures."""
    filtered = df.copy()
    if "has_solubility" in filtered.columns:
        filtered = filtered[filtered["has_solubility"].astype(bool)]
    filtered = filtered[np.isfinite(filtered["ln_x2"].to_numpy(dtype=float))]
    filtered = filtered[np.isfinite(filtered["temperature"].to_numpy(dtype=float))]
    return filtered.reset_index(drop=True)


def find_cross_temperature_pairs(
    df: pd.DataFrame,
    t_cut: float,
) -> list[tuple[str, str]]:
    """Return solute-solvent pairs observed on both sides of a temperature cutoff."""
    pairs: list[tuple[str, str]] = []
    grouped = df.groupby(["solute_smiles", "solvent_smiles"], sort=False)
    for pair, group in grouped:
        temps = group["temperature"].to_numpy(dtype=float)
        if np.any(temps <= t_cut) and np.any(temps > t_cut):
            pairs.append(pair)
    return pairs


def split_by_temperature(
    df: pd.DataFrame,
    pairs: list[tuple[str, str]],
    t_cut: float,
    val_frac: float = 0.1,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split eligible pairs into train/val below the cutoff and test above it."""
    pair_df = pd.DataFrame(pairs, columns=["solute_smiles", "solvent_smiles"])
    eligible = df.merge(pair_df, on=["solute_smiles", "solvent_smiles"], how="inner")

    lower = eligible[eligible["temperature"] <= t_cut].copy()
    test = eligible[eligible["temperature"] > t_cut].copy()
    if lower.empty or test.empty:
        return lower.iloc[0:0].copy(), lower.iloc[0:0].copy(), test.iloc[0:0].copy()

    unique_pairs = (
        lower[["solute_smiles", "solvent_smiles"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    rng = np.random.RandomState(seed)
    n_pairs = len(unique_pairs)
    if n_pairs > 1:
        n_val_pairs = min(max(1, int(round(n_pairs * val_frac))), n_pairs - 1)
    else:
        n_val_pairs = 0

    if n_val_pairs > 0:
        val_pair_idx = rng.choice(n_pairs, size=n_val_pairs, replace=False)
        val_pairs = unique_pairs.iloc[val_pair_idx]
        val = lower.merge(val_pairs, on=["solute_smiles", "solvent_smiles"], how="inner")
        train = lower.merge(val_pairs, on=["solute_smiles", "solvent_smiles"], how="left", indicator=True)
        train = train[train["_merge"] == "left_only"].drop(columns="_merge")
    else:
        train = lower.copy()
        val = lower.iloc[0:0].copy()

    return (
        train.reset_index(drop=True),
        val.reset_index(drop=True),
        test.reset_index(drop=True),
    )


def build_training_command(
    script_name: str,
    config_path: Path,
    train_path: Path,
    val_path: Path,
    test_path: Path,
    seed: int,
    checkpoint_path: Path,
    device: str,
    log_dir: Path,
) -> list[str]:
    """Build the subprocess command for one neural-model run."""
    script_path = _bootstrap.resolve_path(f"scripts/{script_name}")
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


def run_model_via_subprocess(
    script_name: str,
    config_path: Path,
    train_path: Path,
    val_path: Path,
    test_path: Path,
    seed: int,
    device: str,
    work_dir: Path,
) -> dict[str, Any] | None:
    """Train a model via CLI and extract its final test metrics."""
    checkpoint_path = work_dir / f"{script_name.replace('.py', '')}_seed_{seed}.pt"
    log_dir = work_dir / "logs" / script_name.replace(".py", "") / f"seed_{seed}"
    cmd = build_training_command(
        script_name=script_name,
        config_path=config_path,
        train_path=train_path,
        val_path=val_path,
        test_path=test_path,
        seed=seed,
        checkpoint_path=checkpoint_path,
        device=device,
        log_dir=log_dir,
    )

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"WARNING: {script_name} seed {seed} failed.", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
        return None

    try:
        metrics = extract_last_json_block(result.stdout)
    except ValueError as exc:
        print(f"WARNING: {script_name} seed {seed}: {exc}", file=sys.stderr)
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


def compute_summary(t_cut_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Summarize cross-cutoff trends."""
    valid_rows = []
    for label, result in t_cut_results.items():
        tgnn = result.get("tgnn_solv")
        direct = result.get("direct_gnn")
        if not tgnn or not direct:
            continue
        if tgnn.get("mae_mean") is None or direct.get("mae_mean") is None:
            continue
        valid_rows.append(
            (
                float(label),
                float(tgnn["mae_mean"]),
                float(direct["mae_mean"]),
                float(result["improvement_pct"]) if result.get("improvement_pct") is not None else None,
            )
        )

    if len(valid_rows) < 2:
        avg_improvement = [
            row[3] for row in valid_rows if row[3] is not None and math.isfinite(row[3])
        ]
        return {
            "tgnn_solv_degrades_slower": None,
            "average_improvement_over_directgnn": float(np.mean(avg_improvement)) if avg_improvement else None,
            "tgnn_slope_mae_per_k": None,
            "direct_gnn_slope_mae_per_k": None,
        }

    valid_rows.sort(key=lambda row: row[0])
    cuts = np.asarray([row[0] for row in valid_rows], dtype=float)
    tgnn_mae = np.asarray([row[1] for row in valid_rows], dtype=float)
    direct_mae = np.asarray([row[2] for row in valid_rows], dtype=float)
    improvement = np.asarray([row[3] for row in valid_rows if row[3] is not None], dtype=float)

    tgnn_slope = float(np.polyfit(cuts, tgnn_mae, 1)[0])
    direct_slope = float(np.polyfit(cuts, direct_mae, 1)[0])

    return {
        "tgnn_solv_degrades_slower": abs(tgnn_slope) <= abs(direct_slope),
        "average_improvement_over_directgnn": float(np.mean(improvement)) if improvement.size else None,
        "tgnn_slope_mae_per_k": tgnn_slope,
        "direct_gnn_slope_mae_per_k": direct_slope,
    }


def print_results_table(t_cut_specs: list[tuple[str, float]], results: dict[str, dict[str, Any]]) -> None:
    """Print the aggregated extrapolation table."""
    print()
    print("Temperature Extrapolation Results")
    header = (
        f"{'T_cut (K)':<12} | {'N_train':>8} | {'N_test':>8} | "
        f"{'TGNN-Solv MAE':>16} | {'DirectGNN MAE':>16} | {'Improvement':>11}"
    )
    print(header)
    print("-" * len(header))

    for label, _ in t_cut_specs:
        result = results.get(label)
        if result is None:
            continue

        def mae_text(model_key: str) -> str:
            model_data = result.get(model_key)
            if not model_data or model_data.get("mae_mean") is None:
                return "n/a"
            return f"{model_data['mae_mean']:.3f} ± {model_data['mae_std']:.3f}"

        improvement = result.get("improvement_pct")
        improvement_text = "n/a" if improvement is None else f"{improvement:.1f}%"
        print(
            f"{label:<12} | "
            f"{result['n_train']:>8} | "
            f"{result['n_test']:>8} | "
            f"{mae_text('tgnn_solv'):>16} | "
            f"{mae_text('direct_gnn'):>16} | "
            f"{improvement_text:>11}"
        )


def main() -> int:
    """Run the temperature-extrapolation experiment."""
    args = parse_args()

    config_path = _bootstrap.resolve_path(args.config)
    data_path = _bootstrap.resolve_path(args.data)
    output_path = _bootstrap.resolve_path(args.output)
    t_cut_specs = parse_t_cut_specs(args.t_cuts)
    seeds = [args.base_seed + i for i in range(args.n_seeds)]

    df = filter_valid_solubility_rows(pd.read_csv(data_path))

    print("=" * 72)
    print("TGNN-Solv Temperature Extrapolation")
    print("=" * 72)
    print(f"Config:   {config_path}")
    print(f"Data:     {data_path}")
    print(f"T cuts:   {', '.join(label for label, _ in t_cut_specs)}")
    print(f"Seeds:    {seeds}")
    print(f"Min pairs:{args.min_pairs}")
    print("=" * 72)

    t_cut_results: dict[str, dict[str, Any]] = {}
    has_direct_script = _bootstrap.resolve_path("scripts/train_directgnn.py").is_file()
    if not has_direct_script:
        print("WARNING: scripts/train_directgnn.py not found; DirectGNN runs will be skipped.")

    with tempfile.TemporaryDirectory(prefix="tgnn_temp_extrap_") as tmp_dir:
        tmp_root = Path(tmp_dir)

        for label, t_cut in t_cut_specs:
            pairs = find_cross_temperature_pairs(df, t_cut)
            if len(pairs) < args.min_pairs:
                print(
                    f"WARNING: Skipping T_cut={label} because only {len(pairs)} cross-temperature pairs were found."
                )
                continue

            print()
            print(f"[T_cut={label}] pairs={len(pairs)}")
            per_seed_tgnn: list[dict[str, Any]] = []
            per_seed_direct: list[dict[str, Any]] = []
            final_train = None
            final_val = None
            final_test = None

            for seed in seeds:
                train_df, val_df, test_df = split_by_temperature(
                    df=df,
                    pairs=pairs,
                    t_cut=t_cut,
                    val_frac=0.1,
                    seed=seed,
                )

                if train_df.empty or val_df.empty or test_df.empty:
                    print(
                        f"WARNING: T_cut={label} seed={seed} produced an empty split; skipping this seed."
                    )
                    continue

                final_train = train_df
                final_val = val_df
                final_test = test_df

                run_root = tmp_root / label.replace(".", "p") / f"seed_{seed}"
                run_root.mkdir(parents=True, exist_ok=True)
                train_path = run_root / "train.csv"
                val_path = run_root / "val.csv"
                test_path = run_root / "test.csv"
                train_df.to_csv(train_path, index=False)
                val_df.to_csv(val_path, index=False)
                test_df.to_csv(test_path, index=False)

                print(
                    f"  Seed {seed}: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}"
                )

                tgnn_record = run_model_via_subprocess(
                    script_name="train.py",
                    config_path=config_path,
                    train_path=train_path,
                    val_path=val_path,
                    test_path=test_path,
                    seed=seed,
                    device=args.device,
                    work_dir=run_root / "tgnn_solv",
                )
                if tgnn_record is not None:
                    per_seed_tgnn.append(tgnn_record)

                if has_direct_script:
                    direct_record = run_model_via_subprocess(
                        script_name="train_directgnn.py",
                        config_path=config_path,
                        train_path=train_path,
                        val_path=val_path,
                        test_path=test_path,
                        seed=seed,
                        device=args.device,
                        work_dir=run_root / "direct_gnn",
                    )
                    if direct_record is not None:
                        per_seed_direct.append(direct_record)

            if final_train is None or final_test is None:
                print(f"WARNING: No successful splits for T_cut={label}; skipping cutoff.")
                continue

            entry: dict[str, Any] = {
                "n_train": int(len(final_train)),
                "n_val": int(len(final_val)) if final_val is not None else 0,
                "n_test": int(len(final_test)),
                "n_pairs": int(len(pairs)),
                "test_T_range": [
                    float(final_test["temperature"].min()),
                    float(final_test["temperature"].max()),
                ],
            }

            if per_seed_tgnn:
                entry["tgnn_solv"] = aggregate_runs(per_seed_tgnn)
            if per_seed_direct:
                entry["direct_gnn"] = aggregate_runs(per_seed_direct)

            tgnn_mae = entry.get("tgnn_solv", {}).get("mae_mean")
            direct_mae = entry.get("direct_gnn", {}).get("mae_mean")
            if tgnn_mae is not None and direct_mae is not None and direct_mae > 0:
                delta_mae = float(direct_mae - tgnn_mae)
                improvement_pct = float(100.0 * delta_mae / direct_mae)
            else:
                delta_mae = None
                improvement_pct = None
            entry["delta_mae"] = delta_mae
            entry["improvement_pct"] = improvement_pct

            t_cut_results[label] = entry

    summary = compute_summary(t_cut_results)
    print_results_table(t_cut_specs, t_cut_results)

    payload = {
        "t_cuts": t_cut_results,
        "summary": summary,
        "n_seeds": args.n_seeds,
        "base_seed": args.base_seed,
        "seeds": seeds,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print()
    print(f"Saved temperature extrapolation results to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
