#!/usr/bin/env python3
"""Run ablation variants for TGNN-Solv from the command line."""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
from collections import OrderedDict
from dataclasses import replace
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from tgnn_solv.ablation import (
    NoAuxLossTrainer,
    NoCurriculumTrainer,
    TGNNSolvNoCorrection,
    TGNNSolvNoCrossAttn,
    TGNNSolvNoNRTL,
)
from tgnn_solv.baselines.direct_gnn import DirectGNN, DirectGNNTrainer
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import TGNNSolvDataset, collate_fn
from tgnn_solv.device import default_device, resolve_device
from tgnn_solv.evaluate import Evaluator
from tgnn_solv.features import compute_descriptor_normalization_stats
from tgnn_solv.model import TGNNSolv
from tgnn_solv.seed import set_seed
from tgnn_solv.trainer import TGNNSolvTrainer

try:
    from scipy.stats import ttest_rel, wilcoxon
except Exception:  # pragma: no cover - optional dependency
    ttest_rel = None
    wilcoxon = None


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run TGNN-Solv ablation variants across multiple seeds.",
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
        "--variants",
        type=str,
        default="all",
        help=(
            "Comma-separated variant list or 'all'. Supported names: "
            "full,split_late_encoder,asymmetric_encoder,no_nrtl,no_crossattn,no_cross_attn,no_curriculum,"
            "no_aux,no_aux_losses,no_correction,no_implicit_diff,fixed_group_priors,"
            "direct_gnn,small_model,small_128,large_model,large_512"
        ),
    )
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=3,
        help="Number of sequential seeds to evaluate per variant.",
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
        default="results/ablation.json",
        help="Path to save aggregated ablation results.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=default_device(),
        help="Device for training and evaluation; defaults to whichever this box has.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="checkpoints/ablation/",
        help="Directory for ablation checkpoints.",
    )
    return parser.parse_args()


def make_dataloader(
    dataset: TGNNSolvDataset,
    batch_size: int,
    shuffle: bool,
) -> DataLoader:
    """Build a DataLoader for a cached dataset."""
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        collate_fn=collate_fn,
        pin_memory=torch.cuda.is_available(),
        drop_last=shuffle and len(dataset) > batch_size,
    )


def build_variant_specs(base_cfg: TGNNSolvConfig) -> OrderedDict[str, dict[str, Any]]:
    """Build ablation variants, mirroring definitions in `tgnn_solv.ablation`."""
    specs: list[tuple[str, dict[str, Any]]] = [
            (
                "full",
                {
                    "display_name": "Full TGNN-Solv",
                    "description": "Reference model with full physics and curriculum.",
                    "config": base_cfg,
                    "model_class": TGNNSolv,
                    "trainer_class": TGNNSolvTrainer,
                    "kind": "tgnn",
                },
            ),
    ]
    if not base_cfg.use_group_priors:
        specs.append(
            (
                "fixed_group_priors",
                {
                    "display_name": "Fixed Group Priors",
                    "description": (
                        "Coarse fixed fragment-count group-contribution priors "
                        "for Hansen and V_m with bounded graph residuals."
                    ),
                    "config": replace(
                        base_cfg,
                        use_descriptor_priors=False,
                        use_group_priors=True,
                    ),
                    "model_class": TGNNSolv,
                    "trainer_class": TGNNSolvTrainer,
                    "kind": "tgnn",
                    "config_overrides": {
                        "use_descriptor_priors": False,
                        "use_group_priors": True,
                    },
                },
            )
        )
    specs.extend(
        [
            (
                "split_late_encoder",
                {
                    "display_name": "Split Late Encoder",
                    "description": "Shared early GNN with role-specific late message-passing layers.",
                    "config": replace(
                        base_cfg,
                        encoder_role_mode="split_late",
                        encoder_role_specific_layers=min(
                            max(base_cfg.encoder_role_specific_layers, 1),
                            max(base_cfg.n_gnn_layers - 1, 1),
                        ),
                    ),
                    "model_class": TGNNSolv,
                    "trainer_class": TGNNSolvTrainer,
                    "kind": "tgnn",
                    "config_overrides": {
                        "encoder_role_mode": "split_late",
                        "encoder_role_specific_layers": min(
                            max(base_cfg.encoder_role_specific_layers, 1),
                            max(base_cfg.n_gnn_layers - 1, 1),
                        ),
                    },
                },
            ),
            (
                "no_nrtl",
                {
                    "display_name": "No NRTL",
                    "description": "Ideal solubility plus learned correction only.",
                    "config": base_cfg,
                    "model_class": TGNNSolvNoNRTL,
                    "trainer_class": TGNNSolvTrainer,
                    "kind": "tgnn",
                },
            ),
            (
                "no_cross_attn",
                {
                    "display_name": "No Cross-Attn",
                    "description": "Independent solute and solvent encoders.",
                    "config": base_cfg,
                    "model_class": TGNNSolvNoCrossAttn,
                    "trainer_class": TGNNSolvTrainer,
                    "kind": "tgnn",
                },
            ),
            (
                "no_curriculum",
                {
                    "display_name": "No Curriculum",
                    "description": "All losses active from epoch 0.",
                    "config": base_cfg,
                    "model_class": TGNNSolv,
                    "trainer_class": NoCurriculumTrainer,
                    "kind": "tgnn",
                },
            ),
            (
                "no_aux_losses",
                {
                    "display_name": "No Aux Losses",
                    "description": "Solubility loss only without auxiliary targets.",
                    "config": base_cfg,
                    "model_class": TGNNSolv,
                    "trainer_class": NoAuxLossTrainer,
                    "kind": "tgnn",
                },
            ),
            (
                "no_correction",
                {
                    "display_name": "No Correction",
                    "description": "Physics prediction without adaptive correction.",
                    "config": base_cfg,
                    "model_class": TGNNSolvNoCorrection,
                    "trainer_class": TGNNSolvTrainer,
                    "kind": "tgnn",
                },
            ),
            (
                "no_implicit_diff",
                {
                    "display_name": "No Implicit Diff",
                    "description": "Explicit SLE backward pass only.",
                    "config": replace(base_cfg, use_implicit_diff=False),
                    "model_class": TGNNSolv,
                    "trainer_class": TGNNSolvTrainer,
                    "kind": "tgnn",
                    "config_overrides": {"use_implicit_diff": False},
                },
            ),
            (
                "direct_gnn",
                {
                    "display_name": "DirectGNN",
                    "description": "Same dual-graph backbone with direct prediction.",
                    "config": base_cfg,
                    "model_class": DirectGNN,
                    "trainer_class": DirectGNNTrainer,
                    "kind": "direct_gnn",
                },
            ),
            (
                "small_128",
                {
                    "display_name": "Small Model",
                    "description": "Smaller TGNN-Solv scaling variant.",
                    "config": replace(
                        base_cfg,
                        hidden_dim=128,
                        pair_dim=256,
                        n_gnn_layers=4,
                        n_cross_attn_layers=2,
                    ),
                    "model_class": TGNNSolv,
                    "trainer_class": TGNNSolvTrainer,
                    "kind": "tgnn",
                    "config_overrides": {
                        "hidden_dim": 128,
                        "pair_dim": 256,
                        "n_gnn_layers": 4,
                        "n_cross_attn_layers": 2,
                    },
                },
            ),
            (
                "large_512",
                {
                    "display_name": "Large Model",
                    "description": "Larger TGNN-Solv scaling variant.",
                    "config": replace(
                        base_cfg,
                        hidden_dim=512,
                        pair_dim=1024,
                        n_gnn_layers=8,
                        n_cross_attn_layers=4,
                    ),
                    "model_class": TGNNSolv,
                    "trainer_class": TGNNSolvTrainer,
                    "kind": "tgnn",
                    "config_overrides": {
                        "hidden_dim": 512,
                        "pair_dim": 1024,
                        "n_gnn_layers": 8,
                        "n_cross_attn_layers": 4,
                    },
                },
            ),
        ]
    )
    return OrderedDict(specs)


VARIANT_ALIASES = {
    "full": "full",
    "split_late_encoder": "split_late_encoder",
    "asymmetric_encoder": "split_late_encoder",
    "split_late": "split_late_encoder",
    "fixed_group_priors": "fixed_group_priors",
    "group_priors": "fixed_group_priors",
    "no_nrtl": "no_nrtl",
    "no_crossattn": "no_cross_attn",
    "no_cross_attn": "no_cross_attn",
    "no_curriculum": "no_curriculum",
    "no_aux": "no_aux_losses",
    "no_aux_losses": "no_aux_losses",
    "no_correction": "no_correction",
    "no_implicit_diff": "no_implicit_diff",
    "direct_gnn": "direct_gnn",
    "small_model": "small_128",
    "small_128": "small_128",
    "large_model": "large_512",
    "large_512": "large_512",
}


def resolve_variant_order(
    variant_str: str,
    variant_specs: OrderedDict[str, dict[str, Any]],
) -> list[str]:
    """Resolve requested variants into canonical ordered keys."""
    if variant_str.strip().lower() == "all":
        return list(variant_specs.keys())

    selected: list[str] = []
    for raw_name in variant_str.split(","):
        name = raw_name.strip()
        if not name:
            continue
        canonical = VARIANT_ALIASES.get(name)
        if canonical is None:
            raise ValueError(f"Unknown variant: {name}")
        if canonical not in variant_specs:
            raise ValueError(f"Variant {name} is unavailable for the current config.")
        if canonical not in selected:
            selected.append(canonical)

    if "full" not in selected:
        selected.insert(0, "full")
        print("WARNING: Added 'full' automatically for delta-vs-full comparisons.")

    return selected


def _resolve_union_feature_flags(
    variant_order: list[str],
    variant_specs: OrderedDict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Enable any optional dataset feature path required by selected variants."""
    configs = [variant_specs[name]["config"] for name in variant_order]
    if not configs:
        return {
            "use_morgan_features": False,
            "morgan_radius": 2,
            "morgan_n_bits": 2048,
            "use_descriptor_augmentation": False,
            "use_descriptor_priors": False,
            "use_group_priors": False,
            "use_gc_priors_crystal": False,
            "use_gasteiger_charges": False,
            "use_phys_edge_features": False,
            "explicit_h_small_molecules": False,
            "explicit_h_max_heavy_atoms": 3,
        }

    first_cfg = configs[0]
    if any(cfg.morgan_radius != first_cfg.morgan_radius for cfg in configs):
        raise ValueError("Selected variants disagree on morgan_radius.")
    if any(cfg.morgan_n_bits != first_cfg.morgan_n_bits for cfg in configs):
        raise ValueError("Selected variants disagree on morgan_n_bits.")
    if any(cfg.explicit_h_max_heavy_atoms != first_cfg.explicit_h_max_heavy_atoms for cfg in configs):
        raise ValueError("Selected variants disagree on explicit_h_max_heavy_atoms.")

    return {
        "use_morgan_features": any(cfg.use_morgan_features for cfg in configs),
        "morgan_radius": first_cfg.morgan_radius,
        "morgan_n_bits": first_cfg.morgan_n_bits,
        "use_descriptor_augmentation": any(
            cfg.use_descriptor_augmentation for cfg in configs
        ),
        "use_descriptor_priors": any(
            cfg.use_descriptor_priors for cfg in configs
        ),
        "use_group_priors": any(cfg.requires_group_prior_features for cfg in configs),
        "use_gc_priors_crystal": any(
            cfg.use_gc_priors_crystal for cfg in configs
        ),
        "use_gasteiger_charges": any(cfg.use_gasteiger_charges for cfg in configs),
        "use_phys_edge_features": any(cfg.use_phys_edge_features for cfg in configs),
        "explicit_h_small_molecules": any(
            cfg.explicit_h_small_molecules for cfg in configs
        ),
        "explicit_h_max_heavy_atoms": first_cfg.explicit_h_max_heavy_atoms,
    }


def metric_summary(values: list[float]) -> tuple[float | None, float | None]:
    """Compute mean and sample std for a list of floats."""
    if not values:
        return None, None
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    std = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    return mean, std


def paired_p_value(variant_values: list[float], full_values: list[float]) -> float | None:
    """Compute a paired significance p-value for two metric vectors."""
    if ttest_rel is None and wilcoxon is None:
        return None
    if len(variant_values) != len(full_values) or len(variant_values) < 2:
        return None

    variant = np.asarray(variant_values, dtype=float)
    full = np.asarray(full_values, dtype=float)
    diff = variant - full

    if np.allclose(diff, 0.0):
        return 1.0

    try:
        if len(diff) < 10 and wilcoxon is not None:
            return float(wilcoxon(diff).pvalue)
        if ttest_rel is not None:
            return float(ttest_rel(variant, full).pvalue)
    except Exception:
        return None

    return None


def save_checkpoint(
    checkpoint_path: Path,
    model: torch.nn.Module,
    cfg: TGNNSolvConfig,
    seed: int,
    variant: str,
    model_type: str,
) -> None:
    """Save a checkpoint with enough metadata to inspect the ablation run later."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_state_dict": model.state_dict(),
        "config": dataclasses.asdict(cfg),
        "seed": seed,
        "variant": variant,
        "model_type": model_type,
    }
    torch.save(payload, checkpoint_path)


def run_tgnn_variant(
    variant_name: str,
    spec: dict[str, Any],
    cfg: TGNNSolvConfig,
    seed: int,
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader,
    test_df: pd.DataFrame,
    device: torch.device,
    checkpoint_path: Path,
) -> dict[str, Any]:
    """Train and evaluate one TGNN-based ablation variant."""
    model = spec["model_class"](cfg=cfg).to(device)
    trainer = spec["trainer_class"](model, cfg)
    trainer.train_full(train_loader, val_loader)

    evaluator = Evaluator(model, cfg)
    metrics = evaluator.evaluate(test_loader, test_df)["overall"]

    save_checkpoint(
        checkpoint_path=checkpoint_path,
        model=model,
        cfg=cfg,
        seed=seed,
        variant=variant_name,
        model_type=spec["model_class"].__name__,
    )

    return {
        "seed": seed,
        "checkpoint": str(checkpoint_path),
        **{k: float(v) if isinstance(v, (int, float, np.floating)) else v for k, v in metrics.items()},
    }


def run_direct_gnn_variant(
    variant_name: str,
    spec: dict[str, Any],
    cfg: TGNNSolvConfig,
    seed: int,
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader,
    device: torch.device,
    checkpoint_path: Path,
) -> dict[str, Any]:
    """Train and evaluate the DirectGNN baseline inside the ablation sweep."""
    descriptor_mean = None
    descriptor_std = None
    if cfg.use_descriptor_augmentation:
        train_df = getattr(train_loader.dataset, "df", None)
        if not isinstance(train_df, pd.DataFrame):
            raise ValueError(
                "Descriptor augmentation requires access to the training dataframe."
            )
        descriptor_mean, descriptor_std = compute_descriptor_normalization_stats(
            pd.concat(
                [
                    train_df["solute_smiles"].astype(str),
                    train_df["solvent_smiles"].astype(str),
                ],
                axis=0,
                ignore_index=True,
            ).tolist()
        )
        cfg = dataclasses.replace(
            cfg,
            descriptor_dim=int(descriptor_mean.shape[0]),
        )

    model = spec["model_class"](cfg=cfg).to(device)
    if cfg.use_descriptor_augmentation:
        if descriptor_mean is None or descriptor_std is None:
            raise ValueError("Descriptor normalization statistics were not computed.")
        model.set_descriptor_normalization(descriptor_mean, descriptor_std)
    trainer = spec["trainer_class"](model, device)

    # DirectGNN is a single-stage trainer, so use the main solubility-training
    # epoch budget rather than TGNN-Solv's physics-specific phase split.
    trainer.train(
        train_loader,
        val_loader,
        n_epochs=cfg.epochs_phase2,
        lr=cfg.lr_phase2,
        patience=cfg.patience,
    )
    metrics = trainer.evaluate(test_loader)

    save_checkpoint(
        checkpoint_path=checkpoint_path,
        model=model,
        cfg=cfg,
        seed=seed,
        variant=variant_name,
        model_type=spec["model_class"].__name__,
    )

    return {
        "seed": seed,
        "checkpoint": str(checkpoint_path),
        **{k: float(v) if isinstance(v, (int, float, np.floating)) else v for k, v in metrics.items()},
    }


def aggregate_variant(
    variant_name: str,
    spec: dict[str, Any],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate per-seed runs for one variant."""
    aggregated: dict[str, Any] = {
        "display_name": spec["display_name"],
        "description": spec["description"],
        "kind": spec["kind"],
        "config_overrides": spec.get("config_overrides", {}),
        "seeds": [run["seed"] for run in runs],
        "runs": runs,
    }

    for metric in ("mae", "rmse", "r2", "bias"):
        values = [
            float(run[metric])
            for run in runs
            if metric in run and run[metric] is not None and math.isfinite(float(run[metric]))
        ]
        mean, std = metric_summary(values)
        aggregated[f"{metric}_values"] = values
        aggregated[f"{metric}_mean"] = mean
        aggregated[f"{metric}_std"] = std

    return aggregated


def build_delta_vs_full(
    variants: OrderedDict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Compute paired deltas and significance values against the full model."""
    if "full" not in variants:
        return {}

    full_runs = {run["seed"]: run for run in variants["full"]["runs"]}
    full_r2_by_seed = {
        run["seed"]: float(run["r2"])
        for run in variants["full"]["runs"]
        if "r2" in run and run["r2"] is not None
    }

    deltas: dict[str, dict[str, Any]] = {}
    for variant_name, data in variants.items():
        if variant_name == "full":
            continue

        paired_seeds = [
            seed for seed in data["seeds"]
            if seed in full_runs
        ]
        paired_seeds.sort()

        if not paired_seeds:
            deltas[variant_name] = {
                "paired_seeds": [],
                "delta_mae": None,
                "delta_r2": None,
                "significance_p": None,
            }
            continue

        paired_variant_mae = [float(next(run["mae"] for run in data["runs"] if run["seed"] == seed)) for seed in paired_seeds]
        paired_full_mae = [float(full_runs[seed]["mae"]) for seed in paired_seeds]
        paired_variant_r2 = [
            float(next(run["r2"] for run in data["runs"] if run["seed"] == seed))
            for seed in paired_seeds
            if "r2" in next(run for run in data["runs"] if run["seed"] == seed)
        ]
        paired_full_r2 = [full_r2_by_seed[seed] for seed in paired_seeds if seed in full_r2_by_seed]

        deltas[variant_name] = {
            "paired_seeds": paired_seeds,
            "delta_mae": float(np.mean(np.asarray(paired_variant_mae) - np.asarray(paired_full_mae))),
            "delta_r2": (
                float(np.mean(np.asarray(paired_variant_r2) - np.asarray(paired_full_r2)))
                if len(paired_variant_r2) == len(paired_full_r2) and paired_variant_r2
                else None
            ),
            "significance_p": paired_p_value(paired_variant_mae, paired_full_mae),
        }

    return deltas


def print_summary_table(
    variant_order: list[str],
    variants: OrderedDict[str, dict[str, Any]],
    delta_vs_full: dict[str, dict[str, Any]],
) -> None:
    """Print the ablation summary table."""
    print()
    print(f"{'Variant':<20} | {'MAE (mean±std)':<18} | {'ΔMAE vs Full':<12} | {'p-value':<8}")
    print("-" * 72)
    for variant_name in variant_order:
        data = variants.get(variant_name)
        if data is None:
            continue

        mae_mean = data.get("mae_mean")
        mae_std = data.get("mae_std")
        mae_text = (
            f"{mae_mean:.3f} ± {mae_std:.3f}"
            if mae_mean is not None and mae_std is not None
            else "n/a"
        )

        if variant_name == "full":
            delta_text = "—"
            p_text = "—"
        else:
            delta = delta_vs_full.get(variant_name, {}).get("delta_mae")
            p_value = delta_vs_full.get(variant_name, {}).get("significance_p")
            delta_text = f"{delta:+.3f}" if delta is not None else "n/a"
            p_text = f"{p_value:.3g}" if p_value is not None else "n/a"

        print(
            f"{data['display_name']:<20} | "
            f"{mae_text:<18} | "
            f"{delta_text:<12} | "
            f"{p_text:<8}"
        )


def main() -> None:
    """Run the ablation sweep."""
    args = parse_args()

    config_path = _bootstrap.resolve_path(args.config)
    train_path = _bootstrap.resolve_path(args.train_data)
    val_path = _bootstrap.resolve_path(args.val_data)
    test_path = _bootstrap.resolve_path(args.test_data)
    output_path = _bootstrap.resolve_path(args.output)
    checkpoint_root = _bootstrap.resolve_path(args.checkpoint_dir)

    device = resolve_device(args.device)
    base_cfg = TGNNSolvConfig.from_yaml(str(config_path))
    seeds = [args.base_seed + i for i in range(args.n_seeds)]

    variant_specs = build_variant_specs(base_cfg)
    variant_order = resolve_variant_order(args.variants, variant_specs)
    feature_flags = _resolve_union_feature_flags(variant_order, variant_specs)

    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)
    test_df = pd.read_csv(test_path)

    train_dataset = TGNNSolvDataset(
        train_df,
        cache=True,
        use_morgan_features=feature_flags["use_morgan_features"],
        morgan_radius=feature_flags["morgan_radius"],
        morgan_n_bits=feature_flags["morgan_n_bits"],
        use_descriptor_augmentation=feature_flags["use_descriptor_augmentation"],
        use_ionic_features=feature_flags.get("use_ionic_features", False),
        use_descriptor_priors=feature_flags["use_descriptor_priors"],
        use_group_priors=feature_flags["use_group_priors"],
        use_gc_priors_crystal=feature_flags["use_gc_priors_crystal"],
        use_gasteiger_charges=feature_flags["use_gasteiger_charges"],
        use_phys_edge_features=feature_flags["use_phys_edge_features"],
        explicit_h_small_molecules=feature_flags["explicit_h_small_molecules"],
        explicit_h_max_heavy_atoms=feature_flags["explicit_h_max_heavy_atoms"],
        source_uncertainty_csv=(
            base_cfg.source_uncertainty_csv
            if base_cfg.use_source_uncertainty_weights
            else ""
        ),
        source_uncertainty_weight_mode=base_cfg.source_uncertainty_weight_mode,
        source_uncertainty_default_sigma_ln_x2=base_cfg.source_uncertainty_default_sigma_ln_x2,
        source_uncertainty_min_sigma_ln_x2=base_cfg.source_uncertainty_min_sigma_ln_x2,
        source_uncertainty_min_weight=base_cfg.source_uncertainty_min_weight,
        source_uncertainty_max_weight=base_cfg.source_uncertainty_max_weight,
    )
    val_dataset = TGNNSolvDataset(
        val_df,
        cache=True,
        use_morgan_features=feature_flags["use_morgan_features"],
        morgan_radius=feature_flags["morgan_radius"],
        morgan_n_bits=feature_flags["morgan_n_bits"],
        use_descriptor_augmentation=feature_flags["use_descriptor_augmentation"],
        use_ionic_features=feature_flags.get("use_ionic_features", False),
        use_descriptor_priors=feature_flags["use_descriptor_priors"],
        use_group_priors=feature_flags["use_group_priors"],
        use_gc_priors_crystal=feature_flags["use_gc_priors_crystal"],
        use_gasteiger_charges=feature_flags["use_gasteiger_charges"],
        use_phys_edge_features=feature_flags["use_phys_edge_features"],
        explicit_h_small_molecules=feature_flags["explicit_h_small_molecules"],
        explicit_h_max_heavy_atoms=feature_flags["explicit_h_max_heavy_atoms"],
        source_uncertainty_csv=(
            base_cfg.source_uncertainty_csv
            if base_cfg.use_source_uncertainty_weights
            else ""
        ),
        source_uncertainty_weight_mode=base_cfg.source_uncertainty_weight_mode,
        source_uncertainty_default_sigma_ln_x2=base_cfg.source_uncertainty_default_sigma_ln_x2,
        source_uncertainty_min_sigma_ln_x2=base_cfg.source_uncertainty_min_sigma_ln_x2,
        source_uncertainty_min_weight=base_cfg.source_uncertainty_min_weight,
        source_uncertainty_max_weight=base_cfg.source_uncertainty_max_weight,
    )
    test_dataset = TGNNSolvDataset(
        test_df,
        cache=True,
        use_morgan_features=feature_flags["use_morgan_features"],
        morgan_radius=feature_flags["morgan_radius"],
        morgan_n_bits=feature_flags["morgan_n_bits"],
        use_descriptor_augmentation=feature_flags["use_descriptor_augmentation"],
        use_ionic_features=feature_flags.get("use_ionic_features", False),
        use_descriptor_priors=feature_flags["use_descriptor_priors"],
        use_group_priors=feature_flags["use_group_priors"],
        use_gc_priors_crystal=feature_flags["use_gc_priors_crystal"],
        use_gasteiger_charges=feature_flags["use_gasteiger_charges"],
        use_phys_edge_features=feature_flags["use_phys_edge_features"],
        explicit_h_small_molecules=feature_flags["explicit_h_small_molecules"],
        explicit_h_max_heavy_atoms=feature_flags["explicit_h_max_heavy_atoms"],
        source_uncertainty_csv=(
            base_cfg.source_uncertainty_csv
            if base_cfg.use_source_uncertainty_weights
            else ""
        ),
        source_uncertainty_weight_mode=base_cfg.source_uncertainty_weight_mode,
        source_uncertainty_default_sigma_ln_x2=base_cfg.source_uncertainty_default_sigma_ln_x2,
        source_uncertainty_min_sigma_ln_x2=base_cfg.source_uncertainty_min_sigma_ln_x2,
        source_uncertainty_min_weight=base_cfg.source_uncertainty_min_weight,
        source_uncertainty_max_weight=base_cfg.source_uncertainty_max_weight,
    )

    train_loader = make_dataloader(train_dataset, base_cfg.batch_size, shuffle=True)
    val_loader = make_dataloader(val_dataset, base_cfg.batch_size, shuffle=False)
    test_loader = make_dataloader(test_dataset, base_cfg.batch_size, shuffle=False)

    print("=" * 72)
    print("TGNN-Solv Ablation Study")
    print("=" * 72)
    print(f"Config:        {config_path}")
    print(f"Train data:    {train_path}")
    print(f"Val data:      {val_path}")
    print(f"Test data:     {test_path}")
    print(f"Device:        {device}")
    print(f"Variants:      {', '.join(variant_order)}")
    print(f"Seeds:         {seeds}")
    print(f"Checkpoint dir:{checkpoint_root}")
    print("=" * 72)

    aggregated_variants: OrderedDict[str, dict[str, Any]] = OrderedDict()

    for variant_name in variant_order:
        spec = variant_specs[variant_name]
        cfg = spec["config"]
        variant_runs: list[dict[str, Any]] = []

        for seed in seeds:
            set_seed(seed, deterministic=True)
            checkpoint_path = checkpoint_root / variant_name / f"seed_{seed}.pt"

            print()
            print(f"[Variant={variant_name}] [Seed={seed}]")
            try:
                if spec["kind"] == "direct_gnn":
                    run_result = run_direct_gnn_variant(
                        variant_name=variant_name,
                        spec=spec,
                        cfg=cfg,
                        seed=seed,
                        train_loader=train_loader,
                        val_loader=val_loader,
                        test_loader=test_loader,
                        device=device,
                        checkpoint_path=checkpoint_path,
                    )
                else:
                    run_result = run_tgnn_variant(
                        variant_name=variant_name,
                        spec=spec,
                        cfg=cfg,
                        seed=seed,
                        train_loader=train_loader,
                        val_loader=val_loader,
                        test_loader=test_loader,
                        test_df=test_dataset.df,
                        device=device,
                        checkpoint_path=checkpoint_path,
                    )
                variant_runs.append(run_result)
            except Exception as exc:
                print(f"WARNING: Variant {variant_name} seed {seed} failed: {exc}")
            finally:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        if not variant_runs:
            print(f"WARNING: No successful runs for variant {variant_name}; skipping aggregation.")
            continue

        aggregated_variants[variant_name] = aggregate_variant(
            variant_name=variant_name,
            spec=spec,
            runs=variant_runs,
        )

    if not aggregated_variants:
        raise RuntimeError("No ablation runs completed successfully.")

    delta_vs_full = build_delta_vs_full(aggregated_variants)
    print_summary_table(variant_order, aggregated_variants, delta_vs_full)

    result_payload = {
        "config": str(config_path),
        "train_data": str(train_path),
        "val_data": str(val_path),
        "test_data": str(test_path),
        "device": str(device),
        "n_seeds": args.n_seeds,
        "base_seed": args.base_seed,
        "seeds": seeds,
        "variant_order": variant_order,
        "variants": aggregated_variants,
        "delta_vs_full": delta_vs_full,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result_payload, f, indent=2)

    print()
    print(f"Saved ablation results to {output_path}")


if __name__ == "__main__":
    main()
