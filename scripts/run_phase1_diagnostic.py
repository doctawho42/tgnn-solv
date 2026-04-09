#!/usr/bin/env python3
"""Run a multi-seed TGNN/DirectGNN/RF diagnostic comparison."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
import torch

try:
    from scipy.stats import ttest_rel as scipy_ttest_rel
except Exception:  # pragma: no cover - fallback for partially broken envs
    scipy_ttest_rel = None

from run_full_budget_experiment import (
    build_loader,
    collect_tgnn_intermediates,
    load_direct_checkpoint,
    metric_summary,
    parse_seeds,
    pearson_corr,
    regression_metrics,
    resolve_device,
)
from tgnn_solv.baselines.rf_baseline import RFBaseline
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.post_analysis import parse_training_log
from tgnn_solv.reporting import json_safe


DEFAULT_DIRECT_CONFIG = "configs/paper_config_directgnn_tuned.yaml"
CHECKPOINT_EVERY = 5
RF_MODELS = ("rf_descriptors", "rf_morgan", "rf_hybrid")
RF_FEATURE_MODE = {
    "rf_descriptors": "descriptors",
    "rf_morgan": "morgan",
    "rf_hybrid": "hybrid",
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the multi-seed phase-1 diagnostic wrapper around TGNN-Solv, "
            "DirectGNN, and optional RF baselines."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="42,123,456",
        help="Comma-separated seed list.",
    )
    parser.add_argument(
        "--budget",
        type=str,
        default="50,200,50",
        help="Comma-separated phase budget for TGNN: phase1,phase2,phase3.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/paper_config_tuned.yaml",
        help="Base TGNN-Solv config.",
    )
    parser.add_argument(
        "--train-data",
        type=str,
        default="notebooks/data/processed/train.csv",
    )
    parser.add_argument(
        "--val-data",
        type=str,
        default="notebooks/data/processed/val.csv",
    )
    parser.add_argument(
        "--test-data",
        type=str,
        default="notebooks/data/processed/test.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/phase1_diagnostic",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
    )
    parser.add_argument(
        "--skip-rf",
        action="store_true",
        help="Skip Random Forest descriptor/morgan/hybrid baselines.",
    )
    return parser.parse_args()


def log(message: str) -> None:
    """Print a timestamped progress line."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def parse_budget(spec: str) -> tuple[int, int, int]:
    """Parse a phase budget specification."""
    parts = [part.strip() for part in spec.split(",") if part.strip()]
    if len(parts) != 3:
        raise ValueError(
            f"Budget must contain exactly three comma-separated integers, got: {spec!r}"
        )
    phase1, phase2, phase3 = (int(part) for part in parts)
    for value in (phase1, phase2, phase3):
        if value < 0:
            raise ValueError(f"Budget values must be non-negative, got: {spec!r}")
    return phase1, phase2, phase3


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON payload with repo-wide numeric sanitization."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")


def build_tgnn_budget_config(
    *,
    base_config_path: Path,
    output_dir: Path,
    budget: tuple[int, int, int],
) -> Path:
    """Create a TGNN config with the requested phase budget."""
    base_cfg = TGNNSolvConfig.from_yaml(str(base_config_path))
    derived_cfg = replace(
        base_cfg,
        epochs_phase1=int(budget[0]),
        epochs_phase2=int(budget[1]),
        epochs_phase3=int(budget[2]),
    )
    generated_dir = output_dir / "_generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    generated_path = generated_dir / (
        f"{base_config_path.stem}_budget_{budget[0]}_{budget[1]}_{budget[2]}.yaml"
    )
    derived_cfg.to_yaml(str(generated_path))
    return generated_path


def run_training_command(
    *,
    train_script: Path,
    config_path: Path,
    train_data: Path,
    val_data: Path,
    test_data: Path,
    checkpoint_path: Path,
    log_dir: Path,
    stdout_path: Path,
    seed: int,
    device: str,
    experiment_name: str,
    extra_args: list[str] | None = None,
) -> None:
    """Run a training subprocess, resuming automatically when a checkpoint exists."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(train_script),
        "--config",
        str(config_path),
        "--train-data",
        str(train_data),
        "--val-data",
        str(val_data),
        "--test-data",
        str(test_data),
        "--checkpoint",
        str(checkpoint_path),
        "--checkpoint-every",
        str(CHECKPOINT_EVERY),
        "--seed",
        str(seed),
        "--device",
        device,
        "--log-dir",
        str(log_dir),
        "--experiment-name",
        experiment_name,
    ]
    if checkpoint_path.is_file():
        cmd.extend(["--resume", str(checkpoint_path)])
    if extra_args:
        cmd.extend(extra_args)

    run_env = os.environ.copy()
    if device.strip().lower() == "mps":
        run_env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        run_env.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.9")
        run_env.setdefault("PYTORCH_MPS_LOW_WATERMARK_RATIO", "0.8")

    log(
        f"{train_script.name}: "
        f"{'resume/reuse' if checkpoint_path.exists() else 'train'} -> {checkpoint_path}"
    )
    with stdout_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n=== {datetime.now().isoformat(timespec='seconds')} | "
            f"{train_script.name} | seed={seed} ===\n"
        )
        handle.write(" ".join(cmd) + "\n")
        handle.flush()
        result = subprocess.run(
            cmd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=run_env,
        )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)


def load_split_df(csv_path: Path) -> pd.DataFrame:
    """Load a split and attach a stable row index for paired comparisons."""
    df = pd.read_csv(csv_path, low_memory=False)
    return df.reset_index(drop=False).rename(columns={"index": "row_index"})


def summarize_tgnn_metrics(
    standard_df: pd.DataFrame,
    *,
    oracle_metrics: dict[str, Any],
    train_log_path: Path,
) -> dict[str, Any]:
    """Build the per-seed TGNN metric payload required by the wrapper."""
    sol_mask = standard_df["has_solubility"].fillna(False).astype(bool)
    pred = standard_df.loc[sol_mask, "ln_x2_final"].to_numpy(dtype=float)
    true = standard_df.loc[sol_mask, "ln_x2_true"].to_numpy(dtype=float)
    metrics = regression_metrics(pred, true)

    tm_mask = standard_df["has_T_m"].fillna(False).astype(bool)
    tm_true = standard_df.loc[tm_mask, "T_m_true"].to_numpy(dtype=float)
    tm_pred = standard_df.loc[tm_mask, "T_m_pred"].to_numpy(dtype=float)
    dh_mask = standard_df["has_dH_fus"].fillna(False).astype(bool)
    dh_true = standard_df.loc[dh_mask, "dH_fus_true"].to_numpy(dtype=float)
    dh_pred = standard_df.loc[dh_mask, "dH_fus_pred"].to_numpy(dtype=float)

    parsed_log = parse_training_log(train_log_path)
    final_entry = parsed_log.get("final_entry") or {}
    tau_component = (
        (final_entry.get("loss_components") or {}).get("tau_reg") or {}
    )

    metrics.update(
        {
            "tm_mae": (
                float(np.mean(np.abs(tm_pred - tm_true))) if tm_true.size else None
            ),
            "tm_pearson_r": pearson_corr(tm_pred, tm_true),
            "dh_fus_mae": (
                float(np.mean(np.abs(dh_pred - dh_true))) if dh_true.size else None
            ),
            "sol_fraction_final": final_entry.get("sol_fraction"),
            "tau_reg_final": tau_component.get("raw"),
            "mean_correction_abs": (
                float(
                    standard_df.loc[sol_mask, "correction_magnitude"]
                    .to_numpy(dtype=float)
                    .mean()
                )
                if bool(sol_mask.any())
                else None
            ),
            "oracle_mae": oracle_metrics.get("mae"),
        }
    )
    return metrics


@torch.no_grad()
def collect_direct_predictions(
    model: torch.nn.Module,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
) -> pd.DataFrame:
    """Collect DirectGNN per-sample predictions in loader order."""
    model.eval()
    dataset_df = loader.dataset.df.reset_index(drop=True)
    rows: list[pd.DataFrame] = []
    cursor = 0

    for sol_batch, slv_batch, targets in loader:
        sol_batch = sol_batch.to(device)
        slv_batch = slv_batch.to(device)
        batch_size = int(targets["T"].shape[0])
        batch_df = dataset_df.iloc[cursor:cursor + batch_size].copy().reset_index(drop=True)
        cursor += batch_size

        output = model(
            sol_batch,
            slv_batch,
            targets["T"].to(device),
            solvent_type=targets.get("solvent_type"),
            solute_morgan_fp=(
                targets["solute_morgan_fp"].to(device)
                if isinstance(targets.get("solute_morgan_fp"), torch.Tensor)
                else None
            ),
            solvent_morgan_fp=(
                targets["solvent_morgan_fp"].to(device)
                if isinstance(targets.get("solvent_morgan_fp"), torch.Tensor)
                else None
            ),
            solute_descriptors=(
                targets["solute_descriptors"].to(device)
                if isinstance(targets.get("solute_descriptors"), torch.Tensor)
                else None
            ),
            solvent_descriptors=(
                targets["solvent_descriptors"].to(device)
                if isinstance(targets.get("solvent_descriptors"), torch.Tensor)
                else None
            ),
        )

        batch_df["ln_x2_true"] = batch_df["ln_x2"].astype(float)
        batch_df["ln_x2_pred"] = output["ln_x2"].detach().cpu().numpy()
        sol_mask = batch_df["has_solubility"].fillna(False).astype(bool)
        batch_df["error"] = np.where(
            sol_mask,
            batch_df["ln_x2_pred"].to_numpy(dtype=float)
            - batch_df["ln_x2_true"].to_numpy(dtype=float),
            np.nan,
        )
        batch_df["abs_error"] = np.where(
            sol_mask,
            np.abs(batch_df["error"].to_numpy(dtype=float)),
            np.nan,
        )
        rows.append(batch_df)

    if cursor != len(dataset_df):
        raise ValueError(
            f"Collected {cursor} DirectGNN rows, expected {len(dataset_df)}."
        )
    return pd.concat(rows, axis=0, ignore_index=True)


def evaluate_rf_mode(
    *,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_mode: str,
    seed: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Fit and evaluate one RF baseline."""
    model = RFBaseline(feature_mode=feature_mode, random_state=seed)
    model.fit(train_df)
    predictions, valid_idx = model.predict(test_df)

    if not valid_idx:
        empty = test_df.iloc[[]].copy()
        return {
            "mae": None,
            "rmse": None,
            "r2": None,
            "bias": None,
            "pearson_r": None,
            "n": 0,
            "n_samples": 0,
            "n_skipped": int(len(test_df)),
        }, empty

    valid_df = test_df.iloc[valid_idx].copy().reset_index(drop=True)
    valid_df["ln_x2_true"] = valid_df["ln_x2"].astype(float)
    valid_df["ln_x2_pred"] = np.asarray(predictions, dtype=float)
    valid_df["error"] = (
        valid_df["ln_x2_pred"].to_numpy(dtype=float)
        - valid_df["ln_x2_true"].to_numpy(dtype=float)
    )
    valid_df["abs_error"] = np.abs(valid_df["error"].to_numpy(dtype=float))

    metrics = regression_metrics(
        valid_df["ln_x2_pred"].to_numpy(dtype=float),
        valid_df["ln_x2_true"].to_numpy(dtype=float),
    )
    metrics["n_samples"] = int(len(valid_df))
    metrics["n_skipped"] = int(len(test_df) - len(valid_df))
    return metrics, valid_df


def summarize_model_metrics(per_seed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Aggregate scalar metrics across seeds."""
    metric_names: set[str] = set()
    for payload in per_seed.values():
        for key, value in payload.items():
            if isinstance(value, (int, float)) or value is None:
                metric_names.add(key)
    return {
        metric: metric_summary([payload.get(metric) for payload in per_seed.values()])
        for metric in sorted(metric_names)
    }


def merge_abs_errors(
    left_records: list[pd.DataFrame],
    right_records: list[pd.DataFrame],
    *,
    left_name: str,
    right_name: str,
) -> pd.DataFrame:
    """Align paired absolute errors by seed and row index."""
    if not left_records or not right_records:
        return pd.DataFrame()

    left_df = pd.concat(left_records, axis=0, ignore_index=True)
    right_df = pd.concat(right_records, axis=0, ignore_index=True)
    keep_cols = ["seed", "row_index", "abs_error"]
    merged = left_df[keep_cols].merge(
        right_df[keep_cols],
        on=["seed", "row_index"],
        how="inner",
        suffixes=(f"_{left_name}", f"_{right_name}"),
    )
    return merged.replace([np.inf, -np.inf], np.nan).dropna()


def paired_ttest_payload(
    left_records: list[pd.DataFrame],
    right_records: list[pd.DataFrame],
    *,
    left_name: str,
    right_name: str,
) -> dict[str, Any]:
    """Run a paired t-test on aligned absolute errors."""
    merged = merge_abs_errors(
        left_records,
        right_records,
        left_name=left_name,
        right_name=right_name,
    )
    left_col = f"abs_error_{left_name}"
    right_col = f"abs_error_{right_name}"
    if len(merged) < 2:
        return {
            "t_statistic": None,
            "p_value": None,
            "n_samples": int(len(merged)),
            "significant_at_005": False,
            "p_value_method": None,
            "mean_abs_error_left": (
                float(merged[left_col].mean()) if len(merged) else None
            ),
            "mean_abs_error_right": (
                float(merged[right_col].mean()) if len(merged) else None
            ),
        }

    left_values = merged[left_col].to_numpy(dtype=float)
    right_values = merged[right_col].to_numpy(dtype=float)
    if scipy_ttest_rel is not None:
        t_statistic, p_value = scipy_ttest_rel(
            left_values,
            right_values,
            nan_policy="omit",
        )
        p_value_method = "scipy_ttest_rel"
    else:
        delta = left_values - right_values
        delta_std = float(np.std(delta, ddof=1))
        if delta_std == 0.0:
            t_statistic = 0.0
            p_value = 1.0
        else:
            t_statistic = float(
                np.mean(delta) / (delta_std / math.sqrt(float(delta.size)))
            )
            p_value = float(
                2.0 * (1.0 - NormalDist().cdf(abs(float(t_statistic))))
            )
        p_value_method = "normal_approx_fallback"
    return {
        "t_statistic": float(t_statistic) if math.isfinite(float(t_statistic)) else None,
        "p_value": float(p_value) if math.isfinite(float(p_value)) else None,
        "n_samples": int(len(merged)),
        "significant_at_005": bool(
            math.isfinite(float(p_value)) and float(p_value) < 0.05
        ),
        "p_value_method": p_value_method,
        "mean_abs_error_left": float(merged[left_col].mean()),
        "mean_abs_error_right": float(merged[right_col].mean()),
    }


def format_summary_value(summary: dict[str, Any] | None) -> str:
    """Render mean ± std for a metric summary."""
    if not isinstance(summary, dict):
        return "—"
    mean = summary.get("mean")
    std = summary.get("std")
    if mean is None:
        return "—"
    if std is None:
        return f"{float(mean):.4f}"
    return f"{float(mean):.4f} ± {float(std):.4f}"


def build_summary_markdown(
    *,
    aggregate_metrics: dict[str, Any],
    statistical_tests: dict[str, Any],
) -> str:
    """Build a short markdown summary for the diagnostic run."""
    model_order = [
        "tgnn_solv",
        "tgnn_solv_oracle",
        "direct_gnn",
        "rf_descriptors",
        "rf_morgan",
        "rf_hybrid",
    ]
    lines = [
        "# Phase-1 Diagnostic Summary",
        "",
        "| Model | Seeds | MAE | RMSE | R² | T_m MAE | T_m Pearson r | Oracle MAE |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    models = aggregate_metrics.get("models", {})
    for model_name in model_order:
        payload = models.get(model_name)
        if not isinstance(payload, dict):
            continue
        summary = payload.get("summary", {})
        per_seed = payload.get("per_seed", {})
        lines.append(
            "| "
            f"{model_name} | "
            f"{len(per_seed)} | "
            f"{format_summary_value(summary.get('mae'))} | "
            f"{format_summary_value(summary.get('rmse'))} | "
            f"{format_summary_value(summary.get('r2'))} | "
            f"{format_summary_value(summary.get('tm_mae'))} | "
            f"{format_summary_value(summary.get('tm_pearson_r'))} | "
            f"{format_summary_value(summary.get('oracle_mae'))} |"
        )

    lines.extend(
        [
            "",
            "## Paired t-tests",
            "",
            "| Comparison | n | t-statistic | p-value | p < 0.05 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for key in (
        "tgnn_vs_directgnn",
        "directgnn_vs_rf",
        "tgnn_vs_rf",
        "tgnn_vs_tgnn_oracle",
    ):
        payload = statistical_tests.get(key, {})
        lines.append(
            "| "
            f"{key} | "
            f"{payload.get('n_samples', 0)} | "
            f"{payload.get('t_statistic') if payload.get('t_statistic') is not None else '—'} | "
            f"{payload.get('p_value') if payload.get('p_value') is not None else '—'} | "
            f"{'yes' if payload.get('significant_at_005') else 'no'} |"
        )

    rf_reference_model = statistical_tests.get("rf_reference_model")
    if rf_reference_model:
        lines.extend(["", f"RF reference model for statistical tests: `{rf_reference_model}`"])
    return "\n".join(lines) + "\n"


def main() -> None:
    """Run the phase-1 diagnostic orchestration."""
    args = parse_args()
    seeds = parse_seeds(args.seeds)
    budget = parse_budget(args.budget)
    total_budget = int(sum(budget))
    device = resolve_device(args.device)

    output_dir = Path(args.output_dir).expanduser().resolve()
    train_data = Path(args.train_data).expanduser().resolve()
    val_data = Path(args.val_data).expanduser().resolve()
    test_data = Path(args.test_data).expanduser().resolve()
    tgnn_config_path = Path(args.config).expanduser().resolve()
    direct_config_path = Path(DEFAULT_DIRECT_CONFIG).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    log(f"Seeds: {seeds}")
    log(f"Budget: phase1={budget[0]}, phase2={budget[1]}, phase3={budget[2]}")
    log(f"Device: {device}")
    log(f"Output dir: {output_dir}")

    generated_tgnn_config = build_tgnn_budget_config(
        base_config_path=tgnn_config_path,
        output_dir=output_dir,
        budget=budget,
    )
    log(f"Generated TGNN budget config: {generated_tgnn_config}")

    train_df_full = load_split_df(train_data)
    test_df_full = load_split_df(test_data)
    rf_train_df = train_df_full.loc[
        train_df_full["has_solubility"].fillna(False).astype(bool)
    ].copy()
    rf_test_df = test_df_full.loc[
        test_df_full["has_solubility"].fillna(False).astype(bool)
    ].copy()

    aggregate_models: dict[str, dict[str, Any]] = {
        "tgnn_solv": {"per_seed": {}},
        "tgnn_solv_oracle": {"per_seed": {}},
        "direct_gnn": {"per_seed": {}},
    }
    if not args.skip_rf:
        for model_name in RF_MODELS:
            aggregate_models[model_name] = {"per_seed": {}}

    tgnn_error_records: list[pd.DataFrame] = []
    oracle_error_records: list[pd.DataFrame] = []
    direct_error_records: list[pd.DataFrame] = []
    rf_error_records: dict[str, list[pd.DataFrame]] = {
        model_name: [] for model_name in RF_MODELS
    }

    for seed in seeds:
        log(f"Starting seed {seed}")
        seed_dir = output_dir / f"seed_{seed}"
        tgnn_dir = seed_dir / "tgnn"
        oracle_dir = seed_dir / "tgnn_oracle"
        direct_dir = seed_dir / "directgnn"
        rf_dir = seed_dir / "rf"

        tgnn_checkpoint = tgnn_dir / "checkpoint.pt"
        direct_checkpoint = direct_dir / "checkpoint.pt"
        tgnn_stdout = tgnn_dir / "train.stdout.log"
        direct_stdout = direct_dir / "train.stdout.log"

        run_training_command(
            train_script=Path(__file__).resolve().parent / "train.py",
            config_path=generated_tgnn_config,
            train_data=train_data,
            val_data=val_data,
            test_data=test_data,
            checkpoint_path=tgnn_checkpoint,
            log_dir=tgnn_dir / "logs",
            stdout_path=tgnn_stdout,
            seed=seed,
            device=str(device),
            experiment_name=f"phase1_diag_tgnn_seed_{seed}",
        )

        run_training_command(
            train_script=Path(__file__).resolve().parent / "train_directgnn.py",
            config_path=direct_config_path,
            train_data=train_data,
            val_data=val_data,
            test_data=test_data,
            checkpoint_path=direct_checkpoint,
            log_dir=direct_dir / "logs",
            stdout_path=direct_stdout,
            seed=seed,
            device=str(device),
            experiment_name=f"phase1_diag_directgnn_seed_{seed}",
            extra_args=["--epochs", str(total_budget)],
        )

        log(f"Evaluating TGNN seed {seed}")
        from tgnn_solv.inference import load_model

        tgnn_model, tgnn_cfg = load_model(str(tgnn_checkpoint), device=device)
        tgnn_loader = build_loader(test_df_full, tgnn_cfg, seed=seed)
        tgnn_standard_df = collect_tgnn_intermediates(
            tgnn_model,
            tgnn_loader,
            device,
            force_oracle_injection=False,
        )
        tgnn_oracle_df = collect_tgnn_intermediates(
            tgnn_model,
            tgnn_loader,
            device,
            force_oracle_injection=True,
        )

        tgnn_standard_df.to_csv(tgnn_dir / "intermediates.csv", index=False)

        sol_mask = tgnn_oracle_df["has_solubility"].fillna(False).astype(bool)
        oracle_metrics = regression_metrics(
            tgnn_oracle_df.loc[sol_mask, "ln_x2_final"].to_numpy(dtype=float),
            tgnn_oracle_df.loc[sol_mask, "ln_x2_true"].to_numpy(dtype=float),
        )
        tgnn_metrics = summarize_tgnn_metrics(
            tgnn_standard_df,
            oracle_metrics=oracle_metrics,
            train_log_path=tgnn_stdout,
        )
        write_json(tgnn_dir / "metrics.json", tgnn_metrics)
        write_json(oracle_dir / "metrics.json", oracle_metrics)

        aggregate_models["tgnn_solv"]["per_seed"][str(seed)] = tgnn_metrics
        aggregate_models["tgnn_solv_oracle"]["per_seed"][str(seed)] = oracle_metrics

        tgnn_error_records.append(
            tgnn_standard_df.loc[sol_mask, ["row_index", "abs_error"]]
            .assign(seed=seed)
            .reset_index(drop=True)
        )
        oracle_error_records.append(
            tgnn_oracle_df.loc[sol_mask, ["row_index", "abs_error"]]
            .assign(seed=seed)
            .reset_index(drop=True)
        )

        log(f"Evaluating DirectGNN seed {seed}")
        direct_model, direct_cfg = load_direct_checkpoint(direct_checkpoint, device)
        direct_loader = build_loader(test_df_full, direct_cfg, seed=seed)
        direct_df = collect_direct_predictions(direct_model, direct_loader, device)
        direct_sol_mask = direct_df["has_solubility"].fillna(False).astype(bool)
        direct_metrics = regression_metrics(
            direct_df.loc[direct_sol_mask, "ln_x2_pred"].to_numpy(dtype=float),
            direct_df.loc[direct_sol_mask, "ln_x2_true"].to_numpy(dtype=float),
        )
        direct_df.to_csv(direct_dir / "predictions.csv", index=False)
        write_json(direct_dir / "metrics.json", direct_metrics)
        aggregate_models["direct_gnn"]["per_seed"][str(seed)] = direct_metrics
        direct_error_records.append(
            direct_df.loc[direct_sol_mask, ["row_index", "abs_error"]]
            .assign(seed=seed)
            .reset_index(drop=True)
        )

        if not args.skip_rf:
            log(f"Evaluating RF baselines seed {seed}")
            rf_metrics_payload: dict[str, Any] = {}
            for model_name in RF_MODELS:
                feature_mode = RF_FEATURE_MODE[model_name]
                rf_metrics, rf_predictions = evaluate_rf_mode(
                    train_df=rf_train_df,
                    test_df=rf_test_df,
                    feature_mode=feature_mode,
                    seed=seed,
                )
                rf_predictions.to_csv(rf_dir / f"{model_name}_predictions.csv", index=False)
                rf_metrics_payload[model_name] = rf_metrics
                aggregate_models[model_name]["per_seed"][str(seed)] = rf_metrics
                rf_error_records[model_name].append(
                    rf_predictions.loc[:, ["row_index", "abs_error"]]
                    .assign(seed=seed)
                    .reset_index(drop=True)
                )
            write_json(rf_dir / "metrics.json", rf_metrics_payload)

    for payload in aggregate_models.values():
        payload["summary"] = summarize_model_metrics(payload["per_seed"])

    rf_reference_model: str | None = None
    if not args.skip_rf:
        rf_reference_model = min(
            RF_MODELS,
            key=lambda model_name: (
                aggregate_models[model_name]["summary"].get("mae", {}).get("mean")
                if aggregate_models[model_name]["summary"].get("mae", {}).get("mean")
                is not None
                else float("inf")
            ),
        )

    statistical_tests: dict[str, Any] = {
        "rf_reference_model": rf_reference_model,
        "tgnn_vs_directgnn": paired_ttest_payload(
            tgnn_error_records,
            direct_error_records,
            left_name="tgnn",
            right_name="directgnn",
        ),
        "tgnn_vs_tgnn_oracle": paired_ttest_payload(
            tgnn_error_records,
            oracle_error_records,
            left_name="tgnn",
            right_name="tgnn_oracle",
        ),
    }
    if args.skip_rf or rf_reference_model is None:
        empty_result = {
            "t_statistic": None,
            "p_value": None,
            "n_samples": 0,
            "significant_at_005": False,
            "reason": "rf_skipped" if args.skip_rf else "rf_unavailable",
        }
        statistical_tests["directgnn_vs_rf"] = dict(empty_result)
        statistical_tests["tgnn_vs_rf"] = dict(empty_result)
    else:
        rf_records = rf_error_records[rf_reference_model]
        statistical_tests["directgnn_vs_rf"] = paired_ttest_payload(
            direct_error_records,
            rf_records,
            left_name="directgnn",
            right_name="rf",
        )
        statistical_tests["tgnn_vs_rf"] = paired_ttest_payload(
            tgnn_error_records,
            rf_records,
            left_name="tgnn",
            right_name="rf",
        )

    aggregate_payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "config": str(tgnn_config_path),
        "generated_tgnn_config": str(generated_tgnn_config),
        "direct_config": str(direct_config_path),
        "train_data": str(train_data),
        "val_data": str(val_data),
        "test_data": str(test_data),
        "seeds": seeds,
        "budget": {
            "phase1": budget[0],
            "phase2": budget[1],
            "phase3": budget[2],
            "direct_total_epochs": total_budget,
        },
        "models": aggregate_models,
    }
    write_json(output_dir / "aggregate_metrics.json", aggregate_payload)
    write_json(output_dir / "statistical_tests.json", statistical_tests)

    summary_md = build_summary_markdown(
        aggregate_metrics=aggregate_payload,
        statistical_tests=statistical_tests,
    )
    (output_dir / "summary.md").write_text(summary_md, encoding="utf-8")
    log(f"Wrote aggregate metrics to {output_dir / 'aggregate_metrics.json'}")
    log(f"Wrote statistical tests to {output_dir / 'statistical_tests.json'}")
    log(f"Wrote summary to {output_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
