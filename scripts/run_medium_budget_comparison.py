#!/usr/bin/env python3
"""Run the medium-budget architecture comparison on the full scaffold split."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
import torch

from tgnn_solv.baselines.rf_baseline import RFBaseline
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.inference import load_model
from tgnn_solv.reporting import json_safe

from run_full_budget_experiment import (
    _invoke_tgnn,
    build_loader,
    collect_direct_metrics,
    collect_tgnn_intermediates,
    load_direct_checkpoint,
    pearson_corr,
    regression_metrics,
    resolve_device,
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the medium-budget architecture comparison on the full scaffold split "
            "and write aggregate reports under results/medium_budget/."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        default="results/medium_budget",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    parser.add_argument(
        "--force-retrain",
        action="store_true",
        help="Ignore existing checkpoints and retrain all models from scratch.",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=5,
        help="Save resumable checkpoints every N epochs in both training scripts.",
    )
    return parser.parse_args()


def _finite_mean_std(values: np.ndarray) -> dict[str, float | None]:
    """Return mean/std for finite values only."""
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"mean": None, "std": None}
    return {
        "mean": float(np.mean(finite)),
        "std": float(np.std(finite, ddof=1)) if finite.size > 1 else 0.0,
    }


def _tm_metrics(df: pd.DataFrame) -> dict[str, float | int | None]:
    """Compute T_m parity metrics from a TGNN intermediates dataframe."""
    tm_mask = df["has_T_m"].astype(bool).to_numpy()
    tm_true = df.loc[tm_mask, "T_m_true"].to_numpy(dtype=float)
    tm_pred = df.loc[tm_mask, "T_m_pred"].to_numpy(dtype=float)
    if tm_true.size == 0:
        return {
            "n_samples": 0,
            "mae_K": None,
            "pearson_r": None,
        }
    return {
        "n_samples": int(tm_true.size),
        "mae_K": float(np.mean(np.abs(tm_pred - tm_true))),
        "pearson_r": pearson_corr(tm_pred, tm_true),
    }


def _tm_gc_metrics(df: pd.DataFrame) -> dict[str, float | int | None]:
    """Compute GC-prior T_m parity metrics from a TGNN intermediates dataframe."""
    tm_mask = df["has_T_m"].astype(bool).to_numpy()
    tm_true = df.loc[tm_mask, "T_m_true"].to_numpy(dtype=float)
    tm_gc = df.loc[tm_mask, "T_m_gc"].to_numpy(dtype=float)
    if tm_true.size == 0:
        return {
            "n_samples": 0,
            "mae_K": None,
            "pearson_r": None,
        }
    return {
        "n_samples": int(tm_true.size),
        "mae_K": float(np.mean(np.abs(tm_gc - tm_true))),
        "pearson_r": pearson_corr(tm_gc, tm_true),
    }


def _nrtl_stats(df: pd.DataFrame) -> dict[str, dict[str, float | None]]:
    """Compute requested NRTL parameter statistics on the test split."""
    return {
        "tau_12": _finite_mean_std(df["tau_12_pred"].to_numpy(dtype=float)),
        "tau_21": _finite_mean_std(df["tau_21_pred"].to_numpy(dtype=float)),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON artifact with safe numeric conversion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")


def _generate_config(
    *,
    base_path: Path,
    output_path: Path,
    overrides: dict[str, Any],
) -> TGNNSolvConfig:
    """Load a base YAML config, apply overrides, and save the derived config."""
    cfg = TGNNSolvConfig.from_yaml(str(base_path))
    for key, value in overrides.items():
        setattr(cfg, key, value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.to_yaml(str(output_path))
    return cfg


def _run_training_subprocess(
    *,
    train_script: Path,
    config_path: Path,
    train_data: Path,
    val_data: Path,
    test_data: Path,
    checkpoint_path: Path,
    log_dir: Path,
    log_path: Path,
    seed: int,
    device: str,
    batch_size_override: int | None,
    force_retrain: bool,
    checkpoint_every: int,
) -> None:
    """Train one model, resuming from an existing checkpoint when available."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

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
        "--seed",
        str(seed),
        "--checkpoint",
        str(checkpoint_path),
        "--checkpoint-every",
        str(checkpoint_every),
        "--device",
        device,
        "--log-dir",
        str(log_dir),
        "--experiment-name",
        checkpoint_path.stem,
    ]
    if batch_size_override is not None:
        cmd.extend(["--batch-size", str(batch_size_override)])
    if checkpoint_path.is_file() and not force_retrain:
        cmd.extend(["--resume", str(checkpoint_path)])

    run_env = os.environ.copy()
    if device.strip().lower() == "mps":
        run_env.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
        # Keep MPS below the hard cap so failures become recoverable OOMs
        # instead of late SIGKILL from system memory pressure.
        run_env.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.9")
        run_env.setdefault("PYTORCH_MPS_LOW_WATERMARK_RATIO", "0.8")

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n=== Running {' '.join(cmd)} ===\n")
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


def _evaluate_tgnn_model(
    *,
    name: str,
    checkpoint_path: Path,
    test_df: pd.DataFrame,
    output_dir: Path,
    device: torch.device,
    seed: int,
) -> dict[str, Any]:
    """Evaluate one TGNN checkpoint and write per-model diagnostics."""
    model, cfg = load_model(str(checkpoint_path), device=device)
    loader = build_loader(test_df, cfg, seed=seed)

    standard_df = collect_tgnn_intermediates(
        model,
        loader,
        device,
        force_oracle_injection=False,
    )
    oracle_df = _collect_tgnn_tm_only_oracle_intermediates(
        model=model,
        loader=loader,
        device=device,
    )

    sol_mask = standard_df["has_solubility"].astype(bool).to_numpy()
    standard_metrics = regression_metrics(
        standard_df.loc[sol_mask, "ln_x2_final"].to_numpy(dtype=float),
        standard_df.loc[sol_mask, "ln_x2_true"].to_numpy(dtype=float),
    )
    oracle_metrics = regression_metrics(
        oracle_df.loc[sol_mask, "ln_x2_final"].to_numpy(dtype=float),
        oracle_df.loc[sol_mask, "ln_x2_true"].to_numpy(dtype=float),
    )

    tm_metrics = _tm_metrics(standard_df)
    payload = {
        "model": name,
        "checkpoint": str(checkpoint_path),
        "config": dataclasses_asdict_safe(cfg),
        "test_metrics": standard_metrics,
        "oracle_metrics": oracle_metrics,
        "oracle_definition": "T_m_true substituted where available; dH_fus remains predicted.",
        "T_m_metrics": tm_metrics,
        "nrtl_stats": _nrtl_stats(standard_df),
    }
    if cfg.use_gc_priors_crystal:
        payload["T_m_gc_metrics"] = _tm_gc_metrics(standard_df)

    model_dir = output_dir / name
    model_dir.mkdir(parents=True, exist_ok=True)
    standard_df.to_csv(model_dir / "standard_intermediates.csv", index=False)
    oracle_df.to_csv(model_dir / "oracle_tm_intermediates.csv", index=False)
    _write_json(model_dir / "metrics.json", payload)
    return payload


def _collect_tgnn_tm_only_oracle_intermediates(
    *,
    model: torch.nn.Module,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
) -> pd.DataFrame:
    """Collect TGNN intermediates with T_m-only oracle substitution."""
    model.eval()
    dataset_df = loader.dataset.df.reset_index(drop=True)
    rows: list[pd.DataFrame] = []
    cursor = 0

    with torch.no_grad():
        for sol_batch, slv_batch, targets in loader:
            sol_batch = sol_batch.to(device)
            slv_batch = slv_batch.to(device)
            targets_dev = {
                key: value.to(device) if isinstance(value, torch.Tensor) else value
                for key, value in targets.items()
            }

            # Force oracle substitution through the existing solver path, but
            # disable dH_fus oracle availability so the oracle stays T_m-only.
            for mask_key in ("has_dH_fus", "dH_mask"):
                mask_value = targets_dev.get(mask_key)
                if isinstance(mask_value, torch.Tensor):
                    targets_dev[mask_key] = torch.zeros_like(mask_value, dtype=torch.bool)

            output, intermediates = _invoke_tgnn(
                model,
                sol_batch=sol_batch,
                slv_batch=slv_batch,
                targets=targets_dev,
                force_oracle_injection=True,
            )

            batch_size = int(targets_dev["T"].shape[0])
            batch_df = dataset_df.iloc[cursor:cursor + batch_size].copy().reset_index(drop=True)
            cursor += batch_size

            batch_df["ln_x2_true"] = batch_df["ln_x2"].astype(float)
            batch_df["T_m_true"] = batch_df["T_m"].where(batch_df["has_T_m"].astype(bool), np.nan)
            batch_df["dH_fus_true"] = batch_df["dH_fus"].where(batch_df["has_dH_fus"].astype(bool), np.nan)
            batch_df["T_m_gc"] = intermediates["T_m_gc"].detach().cpu().numpy()
            batch_df["dH_fus_gc"] = intermediates["dH_fus_gc"].detach().cpu().numpy()
            batch_df["T_m_pred"] = output["fusion_params"]["T_m"].detach().cpu().numpy()
            batch_df["dH_fus_pred"] = output["fusion_params"]["dH_fus"].detach().cpu().numpy()
            batch_df["T_m_solver"] = output["solver_fusion_params"]["T_m"].detach().cpu().numpy()
            batch_df["dH_fus_solver"] = output["solver_fusion_params"]["dH_fus"].detach().cpu().numpy()
            batch_df["tau_12_pred"] = intermediates["tau_12"].detach().cpu().numpy()
            batch_df["tau_21_pred"] = intermediates["tau_21"].detach().cpu().numpy()
            batch_df["alpha_pred"] = intermediates["alpha_12"].detach().cpu().numpy()
            batch_df["ln_gamma2_pred"] = intermediates["ln_gamma_2"].detach().cpu().numpy()
            batch_df["Phi_pred"] = intermediates["Phi"].detach().cpu().numpy()
            batch_df["ln_x2_physics"] = intermediates["ln_x2_physics"].detach().cpu().numpy()
            batch_df["ln_x2_final"] = intermediates["ln_x2_final"].detach().cpu().numpy()
            batch_df["correction_magnitude"] = np.abs(
                batch_df["ln_x2_final"].to_numpy(dtype=float)
                - batch_df["ln_x2_physics"].to_numpy(dtype=float)
            )
            batch_df["gate_value"] = intermediates["correction_gate"].detach().cpu().numpy()

            oracle_masks = output.get("oracle_injection_masks", {})
            if isinstance(oracle_masks, dict):
                mask_Tm = oracle_masks.get("T_m")
                mask_dH = oracle_masks.get("dH_fus")
                batch_df["oracle_used_T_m"] = (
                    mask_Tm.detach().cpu().numpy().astype(bool)
                    if isinstance(mask_Tm, torch.Tensor)
                    else False
                )
                batch_df["oracle_used_dH_fus"] = (
                    mask_dH.detach().cpu().numpy().astype(bool)
                    if isinstance(mask_dH, torch.Tensor)
                    else False
                )
            else:
                batch_df["oracle_used_T_m"] = False
                batch_df["oracle_used_dH_fus"] = False

            sol_mask = batch_df["has_solubility"].astype(bool)
            batch_df["error"] = np.where(
                sol_mask,
                batch_df["ln_x2_final"].to_numpy(dtype=float) - batch_df["ln_x2_true"].to_numpy(dtype=float),
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
            f"Collected {cursor} rows from loader, expected {len(dataset_df)}."
        )
    return pd.concat(rows, axis=0, ignore_index=True)


def _evaluate_direct_model(
    *,
    name: str,
    checkpoint_path: Path,
    test_df: pd.DataFrame,
    output_dir: Path,
    device: torch.device,
    seed: int,
) -> dict[str, Any]:
    """Evaluate one DirectGNN checkpoint and write per-model metrics."""
    model, cfg = load_direct_checkpoint(checkpoint_path, device)
    loader = build_loader(test_df, cfg, seed=seed)
    metrics = collect_direct_metrics(model, loader, device)

    payload = {
        "model": name,
        "checkpoint": str(checkpoint_path),
        "config": dataclasses_asdict_safe(cfg),
        "test_metrics": metrics,
    }
    model_dir = output_dir / name
    model_dir.mkdir(parents=True, exist_ok=True)
    _write_json(model_dir / "metrics.json", payload)
    return payload


def _evaluate_rf_model(
    *,
    name: str,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Any]:
    """Fit and evaluate the descriptor RF baseline on solubility rows only."""
    baseline = RFBaseline(feature_mode="descriptors", random_state=42)
    baseline.fit(train_df)
    metrics = baseline.evaluate(test_df)
    predictions, valid_idx = baseline.predict(test_df)

    payload = {
        "model": name,
        "feature_mode": "descriptors",
        "test_metrics": metrics,
    }
    model_dir = output_dir / name
    model_dir.mkdir(parents=True, exist_ok=True)
    pred_df = test_df.iloc[valid_idx].copy().reset_index(drop=True)
    pred_df["ln_x2_pred"] = predictions
    pred_df["abs_error"] = np.abs(
        pred_df["ln_x2_pred"].to_numpy(dtype=float)
        - pred_df["ln_x2"].to_numpy(dtype=float)
    )
    pred_df.to_csv(model_dir / "predictions.csv", index=False)
    _write_json(model_dir / "metrics.json", payload)
    return payload


def dataclasses_asdict_safe(cfg: TGNNSolvConfig) -> dict[str, Any]:
    """Serialize config through its YAML-safe method semantics."""
    import dataclasses

    return dataclasses.asdict(cfg)


def _build_summary(
    *,
    args: argparse.Namespace,
    device: torch.device,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    model_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the top-level summary payload."""
    by_name = {result["model"]: result for result in model_results}
    return {
        "setup": {
            "train_data": str(_bootstrap.resolve_path(args.train_data)),
            "val_data": str(_bootstrap.resolve_path(args.val_data)),
            "test_data": str(_bootstrap.resolve_path(args.test_data)),
            "device": str(device),
            "seed": int(args.seed),
            "split": "full_scaffold",
            "row_counts": {
                "train": int(len(train_df)),
                "val": int(len(val_df)),
                "test": int(len(test_df)),
            },
            "budgets": {
                "tgnn": {"phase1": 10, "phase2": 40, "phase3": 10},
                "direct_gnn_epochs": 50,
            },
            "budget_enforcement": {
                "patience_override": 100,
                "oracle_definition": "T_m_true substituted where available; dH_fus remains predicted.",
            },
        },
        "models": by_name,
    }


def _build_markdown(summary: dict[str, Any]) -> str:
    """Render a compact Markdown comparison table."""
    rows = [
        (
            "tgnn_tuned",
            "TGNN tuned baseline",
            summary["models"]["tgnn_tuned"]["test_metrics"],
            summary["models"]["tgnn_tuned"].get("oracle_metrics"),
            summary["models"]["tgnn_tuned"].get("T_m_metrics"),
            summary["models"]["tgnn_tuned"].get("T_m_gc_metrics"),
            summary["models"]["tgnn_tuned"].get("nrtl_stats"),
        ),
        (
            "tgnn_gc_priors",
            "TGNN + GC priors",
            summary["models"]["tgnn_gc_priors"]["test_metrics"],
            summary["models"]["tgnn_gc_priors"].get("oracle_metrics"),
            summary["models"]["tgnn_gc_priors"].get("T_m_metrics"),
            summary["models"]["tgnn_gc_priors"].get("T_m_gc_metrics"),
            summary["models"]["tgnn_gc_priors"].get("nrtl_stats"),
        ),
        (
            "tgnn_no_bridge",
            "TGNN + no bridge",
            summary["models"]["tgnn_no_bridge"]["test_metrics"],
            summary["models"]["tgnn_no_bridge"].get("oracle_metrics"),
            summary["models"]["tgnn_no_bridge"].get("T_m_metrics"),
            summary["models"]["tgnn_no_bridge"].get("T_m_gc_metrics"),
            summary["models"]["tgnn_no_bridge"].get("nrtl_stats"),
        ),
        (
            "tgnn_combined_no_oracle",
            "TGNN + GC priors + no bridge",
            summary["models"]["tgnn_combined_no_oracle"]["test_metrics"],
            summary["models"]["tgnn_combined_no_oracle"].get("oracle_metrics"),
            summary["models"]["tgnn_combined_no_oracle"].get("T_m_metrics"),
            summary["models"]["tgnn_combined_no_oracle"].get("T_m_gc_metrics"),
            summary["models"]["tgnn_combined_no_oracle"].get("nrtl_stats"),
        ),
        (
            "directgnn_tuned",
            "DirectGNN tuned",
            summary["models"]["directgnn_tuned"]["test_metrics"],
            None,
            None,
            None,
            None,
        ),
        (
            "directgnn_descriptors",
            "DirectGNN + descriptors",
            summary["models"]["directgnn_descriptors"]["test_metrics"],
            None,
            None,
            None,
            None,
        ),
        (
            "rf_descriptors",
            "RF descriptors",
            summary["models"]["rf_descriptors"]["test_metrics"],
            None,
            None,
            None,
            None,
        ),
    ]

    lines = [
        "# Medium-Budget Architecture Comparison",
        "",
        f"- Device: `{summary['setup']['device']}`",
        f"- Seed: `{summary['setup']['seed']}`",
        f"- Full scaffold rows: train `{summary['setup']['row_counts']['train']}`, val `{summary['setup']['row_counts']['val']}`, test `{summary['setup']['row_counts']['test']}`",
        "",
        "| Model | Test MAE | RMSE | R² | Oracle MAE (T_m-only) | T_m MAE (K) | T_m Pearson r | T_m_gc MAE (K) | tau_12 mean±std | tau_21 mean±std |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for _name, label, test_metrics, oracle_metrics, tm_metrics, tm_gc_metrics, nrtl_stats in rows:
        test_mae = _fmt_metric(test_metrics.get("mae"))
        rmse = _fmt_metric(test_metrics.get("rmse"))
        r2 = _fmt_metric(test_metrics.get("r2"))
        oracle_mae = _fmt_metric(oracle_metrics.get("mae")) if oracle_metrics else "NA"
        tm_mae = _fmt_metric(tm_metrics.get("mae_K")) if tm_metrics else "NA"
        tm_r = _fmt_metric(tm_metrics.get("pearson_r")) if tm_metrics else "NA"
        tm_gc_mae = _fmt_metric(tm_gc_metrics.get("mae_K")) if tm_gc_metrics else "NA"
        tau12 = _fmt_mean_std(nrtl_stats.get("tau_12")) if nrtl_stats else "NA"
        tau21 = _fmt_mean_std(nrtl_stats.get("tau_21")) if nrtl_stats else "NA"
        lines.append(
            f"| {label} | {test_mae} | {rmse} | {r2} | {oracle_mae} | {tm_mae} | {tm_r} | {tm_gc_mae} | {tau12} | {tau21} |"
        )

    lines.extend(["", "## Per-Model Outputs", ""])
    for name, *_rest in rows:
        lines.append(f"- `{name}`: `results/medium_budget/per_model/{name}`")
    lines.append("")
    return "\n".join(lines)


def _fmt_metric(value: Any) -> str:
    """Format a scalar metric or return NA."""
    if value is None:
        return "NA"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "NA"
    if not math.isfinite(numeric):
        return "NA"
    return f"{numeric:.4f}"


def _fmt_mean_std(payload: dict[str, Any] | None) -> str:
    """Format a mean/std pair for Markdown output."""
    if payload is None:
        return "NA"
    mean = payload.get("mean")
    std = payload.get("std")
    if mean is None or std is None:
        return "NA"
    return f"{float(mean):.3f} ± {float(std):.3f}"


def main() -> int:
    """Run the full medium-budget comparison."""
    args = parse_args()
    output_dir = _bootstrap.resolve_path(args.output_dir)
    per_model_dir = output_dir / "per_model"
    generated_dir = output_dir / "_generated_configs"
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.force_retrain:
        shutil.rmtree(per_model_dir, ignore_errors=True)
        shutil.rmtree(generated_dir, ignore_errors=True)
        for artifact in (
            output_dir / "summary.json",
            output_dir / "comparison_table.md",
        ):
            artifact.unlink(missing_ok=True)
    per_model_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)

    device = resolve_device(args.device)
    train_path = _bootstrap.resolve_path(args.train_data)
    val_path = _bootstrap.resolve_path(args.val_data)
    test_path = _bootstrap.resolve_path(args.test_data)

    train_df = pd.read_csv(train_path, low_memory=False)
    val_df = pd.read_csv(val_path, low_memory=False)
    test_df = pd.read_csv(test_path, low_memory=False)
    rf_train_df = train_df.loc[train_df["has_solubility"].astype(bool)].copy()
    rf_test_df = test_df.loc[test_df["has_solubility"].astype(bool)].copy()
    mps_safe_overrides: dict[str, Any] = {}
    runtime_batch_size_override: int | None = None
    if device.type == "mps":
        mps_safe_overrides = {
            "batch_size": 16,
            "pair_temperature_group_chunk_size": 2,
        }
        runtime_batch_size_override = 16

    common_tgnn_overrides = {
        "epochs_phase1": 10,
        "epochs_phase2": 40,
        "epochs_phase3": 10,
        "patience": 100,
        **mps_safe_overrides,
    }
    model_specs: list[dict[str, Any]] = [
        {
            "name": "tgnn_tuned",
            "kind": "tgnn",
            "base_config": _bootstrap.resolve_path("configs/paper_config_tuned.yaml"),
            "overrides": dict(common_tgnn_overrides),
        },
        {
            "name": "tgnn_gc_priors",
            "kind": "tgnn",
            "base_config": _bootstrap.resolve_path("configs/paper_config_gc_priors.yaml"),
            "overrides": dict(common_tgnn_overrides),
        },
        {
            "name": "tgnn_no_bridge",
            "kind": "tgnn",
            "base_config": _bootstrap.resolve_path("configs/paper_config_no_bridge.yaml"),
            "overrides": dict(common_tgnn_overrides),
        },
        {
            "name": "tgnn_combined_no_oracle",
            "kind": "tgnn",
            "base_config": _bootstrap.resolve_path("configs/paper_config_combined.yaml"),
            "overrides": {
                **common_tgnn_overrides,
                "use_oracle_injection": False,
                "oracle_injection_prob": 0.0,
            },
        },
        {
            "name": "directgnn_tuned",
            "kind": "direct",
            "base_config": _bootstrap.resolve_path("configs/paper_config_directgnn_tuned.yaml"),
            "overrides": {
                "epochs_phase2": 50,
                "patience": 100,
                **mps_safe_overrides,
            },
        },
        {
            "name": "directgnn_descriptors",
            "kind": "direct",
            "base_config": _bootstrap.resolve_path("configs/paper_config_directgnn_tuned.yaml"),
            "overrides": {
                "epochs_phase2": 50,
                "patience": 100,
                "use_descriptor_augmentation": True,
                **mps_safe_overrides,
            },
        },
    ]

    print("=" * 80)
    print("Medium-Budget Architecture Comparison")
    print("=" * 80)
    print(f"Device: {device}")
    print(f"Train data: {train_path}")
    print(f"Val data:   {val_path}")
    print(f"Test data:  {test_path}")
    print(f"Output dir: {output_dir}")
    if mps_safe_overrides:
        print(f"MPS-safe overrides: {mps_safe_overrides}")
    print("=" * 80)

    model_results: list[dict[str, Any]] = []

    for spec in model_specs:
        name = spec["name"]
        kind = spec["kind"]
        model_dir = per_model_dir / name
        config_path = model_dir / "config.yaml"
        checkpoint_path = model_dir / "checkpoint.pt"
        log_dir = model_dir / "logs"
        log_path = model_dir / "train.log"

        cfg = _generate_config(
            base_path=spec["base_config"],
            output_path=config_path,
            overrides=spec["overrides"],
        )
        _write_json(model_dir / "resolved_config.json", dataclasses_asdict_safe(cfg))

        train_script = (
            _bootstrap.resolve_path("scripts/train.py")
            if kind == "tgnn"
            else _bootstrap.resolve_path("scripts/train_directgnn.py")
        )
        print(f"\n[{name}] training via {train_script.name}")
        _run_training_subprocess(
            train_script=train_script,
            config_path=config_path,
            train_data=train_path,
            val_data=val_path,
            test_data=test_path,
            checkpoint_path=checkpoint_path,
            log_dir=log_dir,
            log_path=log_path,
            seed=args.seed,
            device=args.device,
            batch_size_override=runtime_batch_size_override,
            force_retrain=args.force_retrain,
            checkpoint_every=args.checkpoint_every,
        )

        print(f"[{name}] evaluating")
        if kind == "tgnn":
            result = _evaluate_tgnn_model(
                name=name,
                checkpoint_path=checkpoint_path,
                test_df=test_df,
                output_dir=per_model_dir,
                device=device,
                seed=args.seed,
            )
        else:
            result = _evaluate_direct_model(
                name=name,
                checkpoint_path=checkpoint_path,
                test_df=test_df,
                output_dir=per_model_dir,
                device=device,
                seed=args.seed,
            )
        model_results.append(result)

    print("\n[rf_descriptors] fitting/evaluating")
    rf_result = _evaluate_rf_model(
        name="rf_descriptors",
        train_df=rf_train_df,
        test_df=rf_test_df,
        output_dir=per_model_dir,
    )
    model_results.append(rf_result)

    summary = _build_summary(
        args=args,
        device=device,
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        model_results=model_results,
    )
    summary["setup"]["device_adjustments"] = mps_safe_overrides
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "comparison_table.md").write_text(
        _build_markdown(summary),
        encoding="utf-8",
    )

    print()
    print("Completed medium-budget comparison.")
    print(f"Summary: {output_dir / 'summary.json'}")
    print(f"Table:   {output_dir / 'comparison_table.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
