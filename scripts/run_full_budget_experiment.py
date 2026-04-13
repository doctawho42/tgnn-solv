#!/usr/bin/env python3
"""Run the canonical full-budget TGNN-vs-DirectGNN experiment with diagnostics."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
import torch

from tgnn_solv.baselines.direct_gnn import DirectGNN, DirectGNNTrainer
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import make_loader
from tgnn_solv.inference import load_model
from tgnn_solv.reporting import json_safe


INTERPRETATION_GUIDE = """# Full-Budget Experiment Interpretation Guide

If TGNN MAE < DirectGNN MAE AND T_m correlation > 0.8:
  -> Physics bottleneck WORKS. Current issues are purely budget-related.
  -> Proceed with Modifications A-E to improve further.

If TGNN MAE ~= DirectGNN MAE AND T_m correlation > 0.8:
  -> Physics is neutral. Bottleneck is in NRTL parameterization.
  -> Try UNIQUAC (fewer params) and oracle injection.

If TGNN MAE > DirectGNN MAE (regardless of T_m correlation):
  -> Physics bottleneck is HARMFUL. Consider architecture v3 (soft physics).

If T_m correlation < 0.5:
  -> "Garbage factorization" confirmed. The model found physically
     meaningless parameter combinations. GC priors are essential.
"""


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the canonical full-budget TGNN-Solv vs DirectGNN experiment, "
            "save intermediate physics diagnostics, and compare against oracle "
            "crystal-parameter inference."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/paper_config_tuned.yaml",
        help="Base TGNN-Solv config file.",
    )
    parser.add_argument("--train-data", type=str, required=True)
    parser.add_argument("--val-data", type=str, required=True)
    parser.add_argument("--test-data", type=str, required=True)
    parser.add_argument(
        "--seeds",
        type=str,
        default="42",
        help="Comma-separated random seeds, e.g. 42,123,456.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/full_budget_experiment",
        help="Directory for checkpoints, per-seed outputs, and aggregate reports.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Device passed to the training scripts and used for post-hoc evaluation.",
    )
    parser.add_argument(
        "--tau-sum-threshold",
        type=float,
        default=None,
        help=(
            "Threshold used in diagnostics for the fraction of samples where "
            "tau_12 + tau_21 exceeds the chosen cutoff. Defaults to cfg.tau_clamp."
        ),
    )
    parser.add_argument(
        "--force-retrain",
        action="store_true",
        help="Ignore existing checkpoints and retrain all seeds from scratch.",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=5,
        help="Save resumable checkpoints every N epochs in both training scripts.",
    )
    return parser.parse_args()


def resolve_device(device_str: str) -> torch.device:
    """Resolve a requested device with a safe fallback."""
    requested = device_str.strip().lower()
    if requested.startswith("cuda") and not torch.cuda.is_available():
        print("WARNING: CUDA requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    if requested == "mps" and not torch.backends.mps.is_available():
        print("WARNING: MPS requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    return torch.device(device_str)


def parse_seeds(spec: str) -> list[int]:
    """Parse a comma-separated seed list."""
    seeds: list[int] = []
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        seeds.append(int(item))
    if not seeds:
        raise ValueError("At least one seed must be provided.")
    return seeds


def safe_float(value: object) -> float | None:
    """Convert a value to a finite float when possible."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def pearson_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    """Compute Pearson correlation using NumPy."""
    if len(x) < 2 or len(y) < 2:
        return None
    if np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    value = float(np.corrcoef(x, y)[0, 1])
    return value if math.isfinite(value) else None


def metric_summary(values: list[float | None]) -> dict[str, Any]:
    """Aggregate a scalar metric across seeds."""
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not clean:
        return {"mean": None, "std": None, "min": None, "max": None, "values": []}
    mean = float(np.mean(clean))
    std = float(np.std(clean, ddof=1)) if len(clean) > 1 else 0.0
    return {
        "mean": mean,
        "std": std,
        "min": float(np.min(clean)),
        "max": float(np.max(clean)),
        "values": clean,
    }


def regression_metrics(pred: np.ndarray, true: np.ndarray) -> dict[str, Any]:
    """Compute standard regression metrics."""
    pred = np.asarray(pred, dtype=float)
    true = np.asarray(true, dtype=float)
    if pred.size == 0 or true.size == 0:
        return {
            "n": 0,
            "mae": None,
            "rmse": None,
            "r2": None,
            "bias": None,
            "pearson_r": None,
        }
    errors = pred - true
    ss_res = float(np.sum(errors ** 2))
    ss_tot = float(np.sum((true - np.mean(true)) ** 2))
    return {
        "n": int(len(pred)),
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
        "r2": float(1.0 - ss_res / (ss_tot + 1e-10)),
        "bias": float(np.mean(errors)),
        "pearson_r": pearson_corr(pred, true),
    }


def histogram_payload(values: np.ndarray, bins: int = 20) -> dict[str, list[float] | list[int]]:
    """Build a histogram payload for JSON export."""
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"bin_edges": [], "counts": []}
    counts, edges = np.histogram(finite, bins=bins)
    return {
        "bin_edges": [float(v) for v in edges.tolist()],
        "counts": [int(v) for v in counts.tolist()],
    }


def distribution_summary(values: np.ndarray, bins: int = 20) -> dict[str, Any]:
    """Summarize a numeric distribution."""
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {
            "n": 0,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "q05": None,
            "q50": None,
            "q95": None,
            "histogram": {"bin_edges": [], "counts": []},
        }
    return {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "std": float(np.std(finite, ddof=1)) if finite.size > 1 else 0.0,
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "q05": float(np.quantile(finite, 0.05)),
        "q50": float(np.quantile(finite, 0.50)),
        "q95": float(np.quantile(finite, 0.95)),
        "histogram": histogram_payload(finite, bins=bins),
    }


def build_loader(
    df: pd.DataFrame,
    cfg: TGNNSolvConfig,
    *,
    seed: int,
) -> torch.utils.data.DataLoader:
    """Create a non-shuffled loader with the feature paths needed by the config."""
    return make_loader(
        df,
        batch_size=cfg.batch_size,
        shuffle=False,
        num_workers=0,
        cache=True,
        drop_last=False,
        use_pair_temperature_batching=False,
        use_morgan_features=cfg.use_morgan_features,
        morgan_radius=cfg.morgan_radius,
        morgan_n_bits=cfg.morgan_n_bits,
        use_descriptor_augmentation=cfg.use_descriptor_augmentation,
        use_descriptor_priors=cfg.use_descriptor_priors,
        use_group_priors=cfg.use_group_priors,
        use_gc_priors_crystal=cfg.use_gc_priors_crystal,
        use_gasteiger_charges=cfg.use_gasteiger_charges,
        use_phys_edge_features=cfg.use_phys_edge_features,
        use_pseudo_hansen=cfg.use_hansen_contrastive and cfg.use_pseudo_hansen,
        pseudo_hansen_weight_discount=cfg.pseudo_hansen_weight_discount,
        seed=seed,
    )


def build_direct_full_budget_config(
    base_config_path: Path,
    output_dir: Path,
) -> tuple[Path, TGNNSolvConfig]:
    """Create a DirectGNN config with a single-stage epoch budget matching TGNN total epochs."""
    base_cfg = TGNNSolvConfig.from_yaml(str(base_config_path))
    direct_cfg = replace(
        base_cfg,
        epochs_phase2=base_cfg.epochs_phase1 + base_cfg.epochs_phase2 + base_cfg.epochs_phase3,
    )
    generated_dir = output_dir / "_generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    generated_path = generated_dir / "direct_full_budget.yaml"
    direct_cfg.to_yaml(str(generated_path))
    return generated_path, direct_cfg


def run_training_subprocess(
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
    force_retrain: bool,
    checkpoint_every: int,
) -> None:
    """Train one model if its checkpoint is missing or retraining was requested."""
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
    ]
    if checkpoint_path.is_file() and not force_retrain:
        print(f"  Resuming or reusing checkpoint: {checkpoint_path}")
        cmd.extend(["--resume", str(checkpoint_path)])
    else:
        print(f"  Training from scratch -> {checkpoint_path}")
    print(f"  Training via {' '.join(cmd[:3])} ...")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n=== Training seed {seed} with {train_script.name} ===\n")
        handle.flush()
        result = subprocess.run(
            cmd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)


def load_direct_checkpoint(
    checkpoint_path: Path,
    device: torch.device,
) -> tuple[DirectGNN, TGNNSolvConfig]:
    """Load a DirectGNN checkpoint saved by scripts/train_directgnn.py."""
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    cfg = TGNNSolvConfig(**checkpoint["config"])
    model = DirectGNN(cfg=cfg).to(device)
    state = checkpoint.get("model_state_dict", checkpoint.get("model_state", checkpoint))
    model_state = model.state_dict()
    compatible_state = {
        key: value
        for key, value in state.items()
        if key in model_state and tuple(model_state[key].shape) == tuple(value.shape)
    }
    model.load_state_dict(compatible_state, strict=False)
    if cfg.use_descriptor_augmentation:
        descriptor_mean = checkpoint.get("descriptor_mean")
        descriptor_std = checkpoint.get("descriptor_std")
        if descriptor_mean is not None and descriptor_std is not None:
            model.set_descriptor_normalization(descriptor_mean, descriptor_std)
    model.eval()
    return model, cfg


def collect_direct_metrics(
    model: DirectGNN,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
) -> dict[str, Any]:
    """Evaluate DirectGNN on a test loader."""
    trainer = DirectGNNTrainer(model, device=device)
    return trainer.evaluate(loader)


def _invoke_tgnn(
    model: torch.nn.Module,
    *,
    sol_batch: object,
    slv_batch: object,
    targets: dict[str, Any],
    force_oracle_injection: bool = False,
) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
    """Run TGNN-Solv with intermediate export enabled."""
    output = model(
        sol_batch,
        slv_batch,
        targets["T"],
        solvent_type=targets.get("solvent_type"),
        solute_morgan_fp=targets.get("solute_morgan_fp"),
        solvent_morgan_fp=targets.get("solvent_morgan_fp"),
        solute_descriptor_prior_features=targets.get("solute_descriptor_prior_features"),
        solvent_descriptor_prior_features=targets.get("solvent_descriptor_prior_features"),
        solute_group_prior_features=targets.get("solute_group_prior_features"),
        solvent_group_prior_features=targets.get("solvent_group_prior_features"),
        T_m_gc=targets.get("T_m_gc"),
        dH_fus_gc=targets.get("dH_fus_gc"),
        dCp_fus_gc=targets.get("dCp_fus_gc"),
        targets=targets,
        force_oracle_injection=force_oracle_injection,
        return_intermediates=True,
    )
    if isinstance(output, tuple) and len(output) == 2:
        return output[0], output[1]
    raise ValueError("Expected TGNNSolv(return_intermediates=True) to return (output, intermediates).")


def collect_tgnn_intermediates(
    model: torch.nn.Module,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
    *,
    force_oracle_injection: bool = False,
) -> pd.DataFrame:
    """Collect TGNN predictions and intermediate physics quantities in loader order."""
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
            output, intermediates = _invoke_tgnn(
                model,
                sol_batch=sol_batch,
                slv_batch=slv_batch,
                targets=targets_dev,
                force_oracle_injection=force_oracle_injection,
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


def build_diagnostics(
    df: pd.DataFrame,
    *,
    tau_sum_threshold: float,
    oracle_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Build the requested diagnostics payload from TGNN intermediates."""
    tm_mask = df["has_T_m"].astype(bool).to_numpy()
    dh_mask = df["has_dH_fus"].astype(bool).to_numpy()
    sol_mask = df["has_solubility"].astype(bool).to_numpy()

    tm_pred = df.loc[tm_mask, "T_m_pred"].to_numpy(dtype=float)
    tm_true = df.loc[tm_mask, "T_m_true"].to_numpy(dtype=float)
    dh_pred = df.loc[dh_mask, "dH_fus_pred"].to_numpy(dtype=float)
    dh_true = df.loc[dh_mask, "dH_fus_true"].to_numpy(dtype=float)

    delta_s_fus = (
        df["dH_fus_pred"].to_numpy(dtype=float)
        / np.clip(df["T_m_pred"].to_numpy(dtype=float), 1e-8, None)
    )
    walden_deviation = np.abs(delta_s_fus - 56.5)
    walden_outside = walden_deviation > 30.0

    correction_mag = df.loc[sol_mask, "correction_magnitude"].to_numpy(dtype=float)
    abs_error = df.loc[sol_mask, "abs_error"].to_numpy(dtype=float)

    tau_12 = df["tau_12_pred"].to_numpy(dtype=float)
    tau_21 = df["tau_21_pred"].to_numpy(dtype=float)
    alpha = df["alpha_pred"].to_numpy(dtype=float)
    tau_sum = tau_12 + tau_21

    return {
        "T_m_parity": {
            "n_samples": int(len(tm_pred)),
            "pearson_r": pearson_corr(tm_pred, tm_true),
            "mae_K": safe_float(np.mean(np.abs(tm_pred - tm_true))) if len(tm_pred) else None,
            "scatter": {
                "pred": [float(v) for v in tm_pred.tolist()],
                "true": [float(v) for v in tm_true.tolist()],
            },
        },
        "dH_fus_parity": {
            "n_samples": int(len(dh_pred)),
            "pearson_r": pearson_corr(dh_pred, dh_true),
            "mae_J_per_mol": safe_float(np.mean(np.abs(dh_pred - dh_true))) if len(dh_pred) else None,
            "scatter": {
                "pred": [float(v) for v in dh_pred.tolist()],
                "true": [float(v) for v in dh_true.tolist()],
            },
        },
        "walden_consistency": {
            "target_J_per_mol_K": 56.5,
            "tolerance_J_per_mol_K": 30.0,
            "distribution": distribution_summary(delta_s_fus),
            "out_of_tolerance_fraction": (
                float(np.mean(walden_outside)) if len(walden_outside) else None
            ),
        },
        "correction_analysis": {
            "mean_correction_magnitude": safe_float(np.mean(correction_mag)) if len(correction_mag) else None,
            "std_correction_magnitude": safe_float(np.std(correction_mag, ddof=1)) if len(correction_mag) > 1 else (0.0 if len(correction_mag) == 1 else None),
            "mean_gate_value": safe_float(df["gate_value"].mean()),
            "correlation_with_abs_error": pearson_corr(correction_mag, abs_error),
        },
        "nrtl_parameter_analysis": {
            "tau_sum_threshold": tau_sum_threshold,
            "tau_12": distribution_summary(tau_12),
            "tau_21": distribution_summary(tau_21),
            "alpha": distribution_summary(alpha),
            "tau_sum_above_threshold_fraction": (
                float(np.mean(tau_sum > tau_sum_threshold)) if len(tau_sum) else None
            ),
        },
        "oracle_comparison": oracle_metrics,
    }


def aggregate_model_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate MAE/RMSE/R2/Bias/Pearson across seeds."""
    aggregate = {}
    for metric in ("mae", "rmse", "r2", "bias", "pearson_r"):
        aggregate[metric] = metric_summary([record.get(metric) for record in records])
    return aggregate


def aggregate_diagnostics(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate scalar diagnostic summaries across seeds."""
    def pull(path: tuple[str, ...]) -> list[float | None]:
        values: list[float | None] = []
        for payload in per_seed:
            cursor: Any = payload
            for key in path:
                if not isinstance(cursor, dict):
                    cursor = None
                    break
                cursor = cursor.get(key)
            values.append(safe_float(cursor))
        return values

    return {
        "T_m_parity": {
            "pearson_r": metric_summary(pull(("T_m_parity", "pearson_r"))),
            "mae_K": metric_summary(pull(("T_m_parity", "mae_K"))),
        },
        "dH_fus_parity": {
            "pearson_r": metric_summary(pull(("dH_fus_parity", "pearson_r"))),
            "mae_J_per_mol": metric_summary(pull(("dH_fus_parity", "mae_J_per_mol"))),
        },
        "walden_consistency": {
            "out_of_tolerance_fraction": metric_summary(
                pull(("walden_consistency", "out_of_tolerance_fraction"))
            ),
        },
        "correction_analysis": {
            "mean_correction_magnitude": metric_summary(
                pull(("correction_analysis", "mean_correction_magnitude"))
            ),
            "std_correction_magnitude": metric_summary(
                pull(("correction_analysis", "std_correction_magnitude"))
            ),
            "mean_gate_value": metric_summary(
                pull(("correction_analysis", "mean_gate_value"))
            ),
            "correlation_with_abs_error": metric_summary(
                pull(("correction_analysis", "correlation_with_abs_error"))
            ),
        },
        "nrtl_parameter_analysis": {
            "tau_sum_above_threshold_fraction": metric_summary(
                pull(("nrtl_parameter_analysis", "tau_sum_above_threshold_fraction"))
            ),
        },
        "oracle_comparison": {
            "delta_mae": metric_summary(
                pull(("oracle_comparison", "delta_vs_standard", "mae"))
            ),
            "delta_rmse": metric_summary(
                pull(("oracle_comparison", "delta_vs_standard", "rmse"))
            ),
            "delta_r2": metric_summary(
                pull(("oracle_comparison", "delta_vs_standard", "r2"))
            ),
        },
    }


def evaluate_seed(
    *,
    seed: int,
    seed_dir: Path,
    tgnn_checkpoint: Path,
    direct_checkpoint: Path,
    test_path: Path,
    device: torch.device,
    tau_sum_threshold: float,
) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any]]:
    """Load checkpoints, evaluate models, and build per-seed outputs."""
    test_df = pd.read_csv(test_path, low_memory=False)

    tgnn_model, tgnn_cfg = load_model(str(tgnn_checkpoint), device=device)
    tgnn_loader = build_loader(test_df, tgnn_cfg, seed=seed)
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

    standard_mask = tgnn_standard_df["has_solubility"].astype(bool).to_numpy()
    tgnn_metrics = regression_metrics(
        tgnn_standard_df.loc[standard_mask, "ln_x2_final"].to_numpy(dtype=float),
        tgnn_standard_df.loc[standard_mask, "ln_x2_true"].to_numpy(dtype=float),
    )
    oracle_metrics = regression_metrics(
        tgnn_oracle_df.loc[standard_mask, "ln_x2_final"].to_numpy(dtype=float),
        tgnn_oracle_df.loc[standard_mask, "ln_x2_true"].to_numpy(dtype=float),
    )
    oracle_delta = {
        metric: (
            safe_float(oracle_metrics.get(metric)) - safe_float(tgnn_metrics.get(metric))
            if safe_float(oracle_metrics.get(metric)) is not None
            and safe_float(tgnn_metrics.get(metric)) is not None
            else None
        )
        for metric in ("mae", "rmse", "r2", "bias")
    }
    oracle_summary = {
        "standard": tgnn_metrics,
        "oracle": oracle_metrics,
        "delta_vs_standard": oracle_delta,
        "oracle_available_fraction_T_m": safe_float(
            np.mean(tgnn_standard_df["has_T_m"].astype(bool).to_numpy())
        ),
        "oracle_available_fraction_dH_fus": safe_float(
            np.mean(tgnn_standard_df["has_dH_fus"].astype(bool).to_numpy())
        ),
    }

    diagnostics = build_diagnostics(
        tgnn_standard_df,
        tau_sum_threshold=tau_sum_threshold,
        oracle_metrics=oracle_summary,
    )

    direct_model, direct_cfg = load_direct_checkpoint(direct_checkpoint, device)
    direct_loader = build_loader(test_df, direct_cfg, seed=seed)
    direct_metrics = collect_direct_metrics(direct_model, direct_loader, device)

    tgnn_standard_df = tgnn_standard_df.copy()
    tgnn_standard_df.insert(0, "seed", seed)

    seed_metrics = {
        "seed": seed,
        "tgnn_solv": {
            "checkpoint": str(tgnn_checkpoint),
            **tgnn_metrics,
        },
        "direct_gnn": {
            "checkpoint": str(direct_checkpoint),
            **direct_metrics,
        },
        "tgnn_solv_oracle": {
            "checkpoint": str(tgnn_checkpoint),
            **oracle_metrics,
            "delta_mae_vs_standard": oracle_delta["mae"],
            "delta_rmse_vs_standard": oracle_delta["rmse"],
            "delta_r2_vs_standard": oracle_delta["r2"],
        },
    }

    seed_metrics_path = seed_dir / "metrics.json"
    seed_diagnostics_path = seed_dir / "diagnostics.json"
    seed_intermediates_path = seed_dir / "tgnn_intermediates.csv"
    seed_intermediates_path.parent.mkdir(parents=True, exist_ok=True)
    tgnn_standard_df.to_csv(seed_intermediates_path, index=False)
    seed_metrics_path.write_text(
        json.dumps(json_safe(seed_metrics), indent=2),
        encoding="utf-8",
    )
    seed_diagnostics_path.write_text(
        json.dumps(json_safe(diagnostics), indent=2),
        encoding="utf-8",
    )

    return seed_metrics, tgnn_standard_df, diagnostics


def write_readme(output_dir: Path) -> None:
    """Write the interpretation guide into the output directory."""
    (output_dir / "README.md").write_text(INTERPRETATION_GUIDE, encoding="utf-8")


def main() -> int:
    """Run the end-to-end full-budget experiment."""
    args = parse_args()
    config_path = _bootstrap.resolve_path(args.config)
    train_path = _bootstrap.resolve_path(args.train_data)
    val_path = _bootstrap.resolve_path(args.val_data)
    test_path = _bootstrap.resolve_path(args.test_data)
    output_dir = _bootstrap.resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_readme(output_dir)

    device = resolve_device(args.device)
    seeds = parse_seeds(args.seeds)
    base_cfg = TGNNSolvConfig.from_yaml(str(config_path))
    direct_config_path, direct_cfg = build_direct_full_budget_config(config_path, output_dir)
    tau_sum_threshold = (
        float(args.tau_sum_threshold)
        if args.tau_sum_threshold is not None
        else float(base_cfg.tau_clamp)
    )

    print("=" * 80)
    print("TGNN-Solv Full-Budget Experiment")
    print("=" * 80)
    print(f"TGNN config:         {config_path}")
    print(f"DirectGNN config:    {direct_config_path}")
    print(f"Train data:          {train_path}")
    print(f"Val data:            {val_path}")
    print(f"Test data:           {test_path}")
    print(f"Seeds:               {seeds}")
    print(f"Device:              {device}")
    print(f"Tau sum threshold:   {tau_sum_threshold}")
    print(f"Output directory:    {output_dir}")
    print("=" * 80)

    seed_metric_rows: list[dict[str, Any]] = []
    per_seed_diagnostics: list[dict[str, Any]] = []
    all_intermediates: list[pd.DataFrame] = []

    for seed in seeds:
        seed_dir = output_dir / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        tgnn_checkpoint = seed_dir / "tgnn_solv.pt"
        direct_checkpoint = seed_dir / "direct_gnn.pt"

        print()
        print(f"[seed {seed}] Training/evaluating TGNN-Solv and DirectGNN")

        run_training_subprocess(
            train_script=_bootstrap.resolve_path("scripts/train.py"),
            config_path=config_path,
            train_data=train_path,
            val_data=val_path,
            test_data=test_path,
            checkpoint_path=tgnn_checkpoint,
            log_dir=seed_dir / "logs" / "tgnn_solv",
            log_path=seed_dir / "train_tgnn.log",
            seed=seed,
            device=args.device,
            force_retrain=args.force_retrain,
            checkpoint_every=args.checkpoint_every,
        )
        run_training_subprocess(
            train_script=_bootstrap.resolve_path("scripts/train_directgnn.py"),
            config_path=direct_config_path,
            train_data=train_path,
            val_data=val_path,
            test_data=test_path,
            checkpoint_path=direct_checkpoint,
            log_dir=seed_dir / "logs" / "direct_gnn",
            log_path=seed_dir / "train_direct_gnn.log",
            seed=seed,
            device=args.device,
            force_retrain=args.force_retrain,
            checkpoint_every=args.checkpoint_every,
        )

        seed_metrics, seed_intermediates, seed_diagnostics = evaluate_seed(
            seed=seed,
            seed_dir=seed_dir,
            tgnn_checkpoint=tgnn_checkpoint,
            direct_checkpoint=direct_checkpoint,
            test_path=test_path,
            device=device,
            tau_sum_threshold=tau_sum_threshold,
        )
        seed_metric_rows.append(seed_metrics)
        per_seed_diagnostics.append(seed_diagnostics)
        all_intermediates.append(seed_intermediates)

        print(
            f"[seed {seed}] TGNN MAE={seed_metrics['tgnn_solv']['mae']:.4f}, "
            f"DirectGNN MAE={seed_metrics['direct_gnn']['mae']:.4f}, "
            f"Oracle TGNN MAE={seed_metrics['tgnn_solv_oracle']['mae']:.4f}"
        )

    metrics_payload = {
        "seeds": seeds,
        "tgnn_config": str(config_path),
        "direct_gnn_config": str(direct_config_path),
        "models": {
            "tgnn_solv": {
                "per_seed": [
                    {"seed": row["seed"], **row["tgnn_solv"]}
                    for row in seed_metric_rows
                ],
                "aggregate": aggregate_model_records(
                    [{"seed": row["seed"], **row["tgnn_solv"]} for row in seed_metric_rows]
                ),
            },
            "direct_gnn": {
                "per_seed": [
                    {"seed": row["seed"], **row["direct_gnn"]}
                    for row in seed_metric_rows
                ],
                "aggregate": aggregate_model_records(
                    [{"seed": row["seed"], **row["direct_gnn"]} for row in seed_metric_rows]
                ),
            },
            "tgnn_solv_oracle": {
                "per_seed": [
                    {"seed": row["seed"], **row["tgnn_solv_oracle"]}
                    for row in seed_metric_rows
                ],
                "aggregate": aggregate_model_records(
                    [{"seed": row["seed"], **row["tgnn_solv_oracle"]} for row in seed_metric_rows]
                ),
            },
        },
    }

    diagnostics_payload = {
        "seeds": seeds,
        "tau_sum_threshold": tau_sum_threshold,
        "per_seed": {
            str(seed): diagnostics
            for seed, diagnostics in zip(seeds, per_seed_diagnostics, strict=True)
        },
        "aggregate": aggregate_diagnostics(per_seed_diagnostics),
    }

    metrics_path = output_dir / "metrics.json"
    diagnostics_path = output_dir / "diagnostics.json"
    intermediates_path = output_dir / "tgnn_intermediates.csv"
    metrics_path.write_text(
        json.dumps(json_safe(metrics_payload), indent=2),
        encoding="utf-8",
    )
    diagnostics_path.write_text(
        json.dumps(json_safe(diagnostics_payload), indent=2),
        encoding="utf-8",
    )
    pd.concat(all_intermediates, axis=0, ignore_index=True).to_csv(
        intermediates_path,
        index=False,
    )

    print()
    print("Aggregate summary")
    print("-" * 80)
    for model_name in ("tgnn_solv", "direct_gnn", "tgnn_solv_oracle"):
        aggregate = metrics_payload["models"][model_name]["aggregate"]
        mae = aggregate["mae"]["mean"]
        mae_std = aggregate["mae"]["std"]
        r2 = aggregate["r2"]["mean"]
        r2_std = aggregate["r2"]["std"]
        mae_text = "n/a" if mae is None else f"{mae:.4f} ± {mae_std:.4f}"
        r2_text = "n/a" if r2 is None else f"{r2:.4f} ± {r2_std:.4f}"
        print(f"{model_name:<18} MAE={mae_text:<18} R2={r2_text}")

    print()
    print(f"Saved aggregate metrics to {metrics_path}")
    print(f"Saved aggregate diagnostics to {diagnostics_path}")
    print(f"Saved concatenated intermediates to {intermediates_path}")
    print(f"Saved interpretation guide to {output_dir / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
