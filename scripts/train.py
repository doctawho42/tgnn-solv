#!/usr/bin/env python3
"""
CLI wrapper for training TGNN-Solv with curriculum learning.

Supports:
  - YAML configuration loading and CLI parameter overrides
  - Three-phase training (property pretraining → SLE → fine-tuning)
  - Experiment logging with metrics, artifacts, and model checkpoints
  - Optional test set evaluation
"""

import argparse
import dataclasses
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import pandas as pd
import torch
from torch.utils.data import DataLoader

from tgnn_solv.artifacts import build_model_card, build_run_manifest, write_json
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import make_loader
from tgnn_solv.experiment_logger import ExperimentLogger
from tgnn_solv.features import (
    EDGE_FEAT_DIM,
    NODE_FEAT_DIM,
    DescriptorNormalizer,
)
from tgnn_solv.group_contribution import (
    GC_FALLBACK_PRIORS,
    compute_gc_priors,
    fit_tm_gc_calibration,
)
from tgnn_solv.model import TGNNSolv
from tgnn_solv.pretrain_pipeline import (
    apply_pretrained_encoder_checkpoint,
    derive_pretrain_checkpoint_path,
    load_pretrained_encoder_checkpoint,
    run_stage0_pretraining,
)
from tgnn_solv.seed import set_seed
from tgnn_solv.trainer import TGNNSolvTrainer


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


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Train TGNN-Solv with curriculum learning.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        default="configs/paper_config.yaml",
        help="Path to YAML configuration file",
    )
    
    # Data paths
    parser.add_argument(
        "--train-data",
        type=str,
        required=True,
        help="Path to training CSV file",
    )
    parser.add_argument(
        "--val-data",
        type=str,
        default=None,
        help="Path to validation CSV file",
    )
    parser.add_argument(
        "--test-data",
        type=str,
        default=None,
        help="Path to test CSV file (optional; evaluate after training if provided)",
    )
    
    # Model checkpoint
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="checkpoints/model.pt",
        help="Path to save trained model checkpoint",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to a saved training checkpoint to resume from",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=0,
        help="Save a resumable checkpoint every N epochs per phase (0 disables periodic saves)",
    )
    
    # Training settings
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device to use (cuda or cpu)",
    )
    
    # Logging
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs/",
        help="Root directory for experiment logs",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Experiment name (auto-generated from timestamp if not provided)",
    )
    
    # CLI overrides for configuration
    parser.add_argument(
        "--hidden-dim",
        type=int,
        default=None,
        help="Override hidden_dim from config",
    )
    parser.add_argument(
        "--n-gnn-layers",
        type=int,
        default=None,
        help="Override n_gnn_layers from config",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override batch_size from config",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=None,
        help="Override learning rate (lr_phase2) from config",
    )
    parser.add_argument(
        "--epochs-phase1",
        type=int,
        default=None,
        help="Override Phase 1 epoch count from config.",
    )
    parser.add_argument(
        "--epochs-phase2",
        type=int,
        default=None,
        help="Override Phase 2 epoch count from config.",
    )
    parser.add_argument(
        "--epochs-phase3",
        type=int,
        default=None,
        help="Override Phase 3 epoch count from config.",
    )
    parser.add_argument(
        "--pretrain",
        action="store_true",
        help="Run Stage 0 pretraining on an external SMILES corpus before standard TGNN training.",
    )
    parser.add_argument(
        "--pretrain-epochs",
        type=int,
        default=30,
        help="Number of Stage 0 pretraining epochs.",
    )
    parser.add_argument(
        "--pretrain-batch-size",
        type=int,
        default=128,
        help="Stage 0 pretraining batch size.",
    )
    parser.add_argument(
        "--pretrain-lr",
        type=float,
        default=3.0e-4,
        help="Learning rate for Stage 0 pretraining.",
    )
    parser.add_argument(
        "--pretrain-data",
        type=str,
        default="zinc250k",
        help="Stage 0 pretraining source (`zinc250k` or a local CSV/text file with SMILES).",
    )
    parser.add_argument(
        "--pretrain-max-molecules",
        type=int,
        default=None,
        help="Optional cap on the number of Stage 0 molecules to load.",
    )
    parser.add_argument(
        "--pretrain-checkpoint",
        type=str,
        default=None,
        help="Load a previously saved Stage 0 encoder/readout checkpoint instead of rerunning pretraining.",
    )
    parser.add_argument(
        "--pretrain-output",
        type=str,
        default=None,
        help="Where to save the Stage 0 encoder/readout checkpoint when `--pretrain` is used.",
    )
    parser.add_argument(
        "--run-descriptor-probe",
        action="store_true",
        help="After training, run the existing Ridge linear probe from `g_sol` to RDKit descriptors.",
    )
    parser.add_argument(
        "--probe-only",
        action="store_true",
        help="Skip training and run only the descriptor probe for --checkpoint.",
    )
    parser.add_argument(
        "--descriptor-probe-output-dir",
        type=str,
        default=None,
        help="Output directory for descriptor probe artifacts. Defaults to `<checkpoint_stem>_descriptor_probe`.",
    )
    parser.add_argument(
        "--descriptor-probe-device",
        type=str,
        default="cpu",
        help="Device for the descriptor probe. Defaults to CPU to avoid contending with training.",
    )
    parser.add_argument(
        "--probe-every",
        type=int,
        default=0,
        help=(
            "During training, run the descriptor linear probe every N epochs "
            "for the selected phases (0 disables probe evolution tracking)."
        ),
    )
    parser.add_argument(
        "--probe-phases",
        type=str,
        default="2",
        help="Comma-separated phases for --probe-every, for example '2' or '1,2,3'.",
    )
    parser.add_argument(
        "--probe-evolution-output",
        type=str,
        default=None,
        help="CSV path for in-training probe evolution. Defaults to <checkpoint>_probe_evolution.csv.",
    )
    
    return parser.parse_args()


def atomic_torch_save(payload: dict, path: Path) -> None:
    """Atomically save a checkpoint to avoid partial files on preemption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.tmp.",
        suffix=".pt",
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        torch.save(payload, tmp_path)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def build_checkpoint_payload(
    *,
    model: TGNNSolv,
    config: TGNNSolvConfig,
    seed: int,
    experiment_name: str,
    trainer: TGNNSolvTrainer,
    resume_state: dict | None,
    pretrain_info: dict[str, Any] | None = None,
) -> dict:
    """Build a training checkpoint that supports both inference and resume."""
    checkpoint = {
        "model_state": model.state_dict(),
        "model_state_dict": model.state_dict(),
        "config": dataclasses.asdict(config),
        "node_feat_dim": int(getattr(model, "node_feat_dim", NODE_FEAT_DIM)),
        "edge_feat_dim": int(getattr(model, "edge_feat_dim", EDGE_FEAT_DIM)),
        "seed": seed,
        "experiment_name": experiment_name,
        "trainer_state_dict": trainer.state_dict(),
        "resume_state": resume_state,
        "pretrain_info": pretrain_info,
    }
    if config.use_descriptor_augmentation:
        checkpoint["descriptor_mean"] = model.descriptor_mean.detach().cpu()
        checkpoint["descriptor_std"] = model.descriptor_std.detach().cpu()
    return checkpoint


def maybe_run_descriptor_probe(
    *,
    checkpoint_path: Path,
    train_data: str,
    test_data: str | None,
    output_dir: str | None,
    device: str,
    logger: ExperimentLogger,
) -> None:
    """Run the existing `g_sol -> descriptors` Ridge probe and log its summary."""
    if test_data is None:
        print("   Skipping descriptor probe because no --test-data path was provided.")
        return

    from probe_gsol_descriptor_recovery import (
        CORE_DESCRIPTOR_NAMES,
        build_descriptor_matrix,
        build_markdown_report,
        extract_solute_embeddings,
        fit_descriptor_probes,
        load_unique_solutes,
        resolve_device as resolve_probe_device,
    )
    from tgnn_solv.inference import load_model
    from tgnn_solv.reporting import json_safe

    probe_output_dir = (
        Path(output_dir).expanduser().resolve()
        if output_dir is not None
        else checkpoint_path.with_name(f"{checkpoint_path.stem}_descriptor_probe")
    )
    probe_output_dir.mkdir(parents=True, exist_ok=True)

    probe_device = resolve_probe_device(device)
    model, cfg = load_model(str(checkpoint_path), device=probe_device)
    model.eval()

    train_path = Path(train_data).resolve()
    test_path = Path(test_data).resolve()
    train_solutes = load_unique_solutes(train_path)
    test_solutes = load_unique_solutes(test_path)

    train_smiles, X_train = extract_solute_embeddings(
        model=model,
        smiles_list=train_solutes,
        device=probe_device,
        batch_size=512,
        temperature_K=298.15,
    )
    test_smiles, X_test = extract_solute_embeddings(
        model=model,
        smiles_list=test_solutes,
        device=probe_device,
        batch_size=512,
        temperature_K=298.15,
    )
    Y_train = build_descriptor_matrix(train_smiles)
    Y_test = build_descriptor_matrix(test_smiles)
    results_df, probe_summary = fit_descriptor_probes(
        X_train=X_train,
        X_test=X_test,
        Y_train=Y_train,
        Y_test=Y_test,
        alpha=1.0,
    )

    core_df = (
        results_df[results_df["descriptor"].isin(CORE_DESCRIPTOR_NAMES)]
        .set_index("descriptor")
        .reindex(CORE_DESCRIPTOR_NAMES)
        .reset_index()
    )

    import math
    import numpy as np

    np.savez_compressed(
        probe_output_dir / "train_solute_embeddings.npz",
        smiles=np.asarray(train_smiles, dtype=object),
        embeddings=X_train.astype(np.float32, copy=False),
    )
    np.savez_compressed(
        probe_output_dir / "test_solute_embeddings.npz",
        smiles=np.asarray(test_smiles, dtype=object),
        embeddings=X_test.astype(np.float32, copy=False),
    )
    results_df.to_csv(probe_output_dir / "descriptor_r2.csv", index=False)

    summary_payload = {
        "checkpoint": str(checkpoint_path),
        "config": {
            "hidden_dim": int(cfg.hidden_dim),
            "encoder_type": str(getattr(cfg, "encoder_type", "mpnn")),
            "use_temperature_in_encoder": bool(cfg.use_temperature_in_encoder),
            "use_morgan_features": bool(cfg.use_morgan_features),
            "use_descriptor_augmentation": bool(cfg.use_descriptor_augmentation),
            "encoder_role_mode": str(cfg.encoder_role_mode),
        },
        "probe": {
            "embedding_name": "g_sol_pre",
            "embedding_temperature_K": 298.15,
            "ridge_alpha": 1.0,
            "device": str(probe_device),
        },
        "dataset": {
            "train_data": str(train_path),
            "test_data": str(test_path),
            "n_train_unique_solutes": int(len(train_smiles)),
            "n_test_unique_solutes": int(len(test_smiles)),
        },
        "summary": probe_summary,
        "core_descriptors": {
            row["descriptor"]: {
                "r2_test": (
                    None if not math.isfinite(float(row["r2_test"])) else float(row["r2_test"])
                ),
                "r2_train": (
                    None if not math.isfinite(float(row["r2_train"])) else float(row["r2_train"])
                ),
                "status": str(row["status"]),
            }
            for _, row in core_df.iterrows()
        },
    }
    (probe_output_dir / "summary.json").write_text(
        json.dumps(json_safe(summary_payload), indent=2),
        encoding="utf-8",
    )
    (probe_output_dir / "report.md").write_text(
        build_markdown_report(
            summary=probe_summary,
            results_df=results_df,
            core_df=core_df,
            checkpoint_path=checkpoint_path,
            device=str(probe_device),
            train_count=len(train_smiles),
            test_count=len(test_smiles),
        ),
        encoding="utf-8",
    )
    logger.log_artifact("descriptor_probe_summary", summary_payload)
    print(f"   Descriptor probe written to {probe_output_dir}")


def parse_probe_phases(raw: str) -> set[int]:
    """Parse a comma-separated phase list for in-training descriptor probes."""
    phases: set[int] = set()
    for item in str(raw).split(","):
        item = item.strip()
        if not item:
            continue
        phase = int(item)
        if phase not in {1, 2, 3}:
            raise ValueError("--probe-phases may only contain 1, 2, and 3.")
        phases.add(phase)
    return phases


def maybe_run_probe_evolution_snapshot(
    *,
    model: TGNNSolv,
    config: TGNNSolvConfig,
    phase: int,
    epoch_in_phase: int,
    global_epoch: int,
    train_data: str,
    test_data: str | None,
    output_csv: Path,
    output_root: Path,
    logger: ExperimentLogger,
) -> None:
    """Run a descriptor linear probe on the live model and append one CSV row."""
    if test_data is None:
        print("   Skipping probe evolution snapshot because no --test-data path was provided.")
        return

    from probe_gsol_descriptor_recovery import (
        CORE_DESCRIPTOR_NAMES,
        build_descriptor_matrix,
        extract_solute_embeddings,
        fit_descriptor_probes,
        load_unique_solutes,
    )
    from tgnn_solv.reporting import json_safe

    probe_device = next(model.parameters()).device
    snapshot_dir = output_root / f"phase{phase}_epoch{epoch_in_phase + 1:04d}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    was_training = model.training
    model.eval()
    try:
        train_path = Path(train_data).resolve()
        test_path = Path(test_data).resolve()
        train_solutes = load_unique_solutes(train_path)
        test_solutes = load_unique_solutes(test_path)

        train_smiles, X_train = extract_solute_embeddings(
            model=model,
            smiles_list=train_solutes,
            device=probe_device,
            batch_size=512,
            temperature_K=298.15,
        )
        test_smiles, X_test = extract_solute_embeddings(
            model=model,
            smiles_list=test_solutes,
            device=probe_device,
            batch_size=512,
            temperature_K=298.15,
        )
        Y_train = build_descriptor_matrix(train_smiles)
        Y_test = build_descriptor_matrix(test_smiles)
        results_df, probe_summary = fit_descriptor_probes(
            X_train=X_train,
            X_test=X_test,
            Y_train=Y_train,
            Y_test=Y_test,
            alpha=1.0,
        )
    finally:
        model.train(was_training)

    results_df.to_csv(snapshot_dir / "descriptor_r2.csv", index=False)
    summary_payload = {
        "phase": int(phase),
        "epoch_in_phase": int(epoch_in_phase + 1),
        "global_epoch": int(global_epoch),
        "config": {
            "encoder_type": str(getattr(config, "encoder_type", "mpnn")),
            "hidden_dim": int(config.hidden_dim),
        },
        "summary": probe_summary,
    }
    (snapshot_dir / "summary.json").write_text(
        json.dumps(json_safe(summary_payload), indent=2),
        encoding="utf-8",
    )

    core_df = (
        results_df[results_df["descriptor"].isin(CORE_DESCRIPTOR_NAMES)]
        .set_index("descriptor")
    )
    tracked = ("MolLogP", "TPSA", "NumHDonors", "NumHAcceptors", "FractionCSP3", "MolWt")
    row: dict[str, float | int | str | None] = {
        "global_epoch": int(global_epoch),
        "phase": int(phase),
        "epoch_in_phase": int(epoch_in_phase + 1),
        "median_R2": probe_summary.get("median_r2_test"),
        "mean_R2": probe_summary.get("mean_r2_test"),
        "n_descriptors": probe_summary.get("n_descriptors_with_finite_r2"),
    }
    for descriptor in tracked:
        if descriptor in core_df.index:
            value = core_df.loc[descriptor, "r2_test"]
            row[f"{descriptor}_R2"] = None if pd.isna(value) else float(value)
        else:
            row[f"{descriptor}_R2"] = None

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    row_df = pd.DataFrame([row])
    if output_csv.exists():
        row_df.to_csv(output_csv, mode="a", header=False, index=False)
    else:
        row_df.to_csv(output_csv, index=False)

    logger.log_artifact(f"probe_evolution_phase{phase}_epoch{epoch_in_phase + 1}", row)
    median = row.get("median_R2")
    median_str = "NA" if median is None else f"{float(median):.3f}"
    print(
        "   Probe evolution snapshot: "
        f"phase={phase}, epoch={epoch_in_phase + 1}, "
        f"global={global_epoch}, median_R2={median_str}"
    )


def load_data(
    csv_path: str,
    config: TGNNSolvConfig,
    *,
    shuffle: bool,
    seed: int,
) -> DataLoader:
    """Load a CSV split and build the configured DataLoader."""
    import pandas as pd

    df = pd.read_csv(csv_path, low_memory=False)

    return make_loader(
        df,
        batch_size=config.batch_size,
        shuffle=shuffle,
        num_workers=0,
        cache=True,
        use_pair_temperature_batching=(
            shuffle and config.use_pair_temperature_batching
        ),
        pair_temperature_min_group_size=(
            config.pair_temperature_min_group_size
        ),
        pair_temperature_group_chunk_size=(
            config.pair_temperature_group_chunk_size
        ),
        use_morgan_features=config.use_morgan_features,
        morgan_radius=config.morgan_radius,
        morgan_n_bits=config.morgan_n_bits,
        use_descriptor_augmentation=config.use_descriptor_augmentation,
        use_descriptor_priors=config.use_descriptor_priors,
        use_group_priors=config.use_group_priors,
        use_gc_priors_crystal=config.use_gc_priors_crystal,
        use_gasteiger_charges=config.use_gasteiger_charges,
        use_phys_edge_features=config.use_phys_edge_features,
        use_pseudo_hansen=(
            config.use_hansen_contrastive and config.use_pseudo_hansen
        ),
        pseudo_hansen_weight_discount=config.pseudo_hansen_weight_discount,
        seed=seed,
    )


def maybe_fit_gc_tm_calibration(
    train_csv_path: str,
    config: TGNNSolvConfig,
) -> None:
    """Fit and store a train-only affine calibration for the GC melting prior."""
    if not config.use_gc_priors_crystal:
        return

    import numpy as np
    import pandas as pd

    df = pd.read_csv(train_csv_path, low_memory=False)
    required_cols = {"solute_smiles", "T_m", "has_T_m"}
    if not required_cols.issubset(df.columns):
        print(
            "   Skipping GC T_m calibration; "
            f"missing columns: {sorted(required_cols - set(df.columns))}"
        )
        return

    unique_tm = (
        df.loc[df["has_T_m"].fillna(False).astype(bool), ["solute_smiles", "T_m"]]
        .drop_duplicates(subset=["solute_smiles"], keep="first")
    )
    if unique_tm.empty:
        print("   Skipping GC T_m calibration; no training rows with T_m labels.")
        return

    raw_tm_gc: list[float] = []
    tm_true: list[float] = []
    fallback_count = 0
    for smiles, tm_value in unique_tm.itertuples(index=False):
        priors = compute_gc_priors(str(smiles))
        tm_gc = priors["T_m_gc"]
        if tm_gc is None or not np.isfinite(tm_gc) or not np.isfinite(tm_value):
            continue
        raw_tm_gc.append(float(tm_gc))
        tm_true.append(float(tm_value))
        if abs(float(tm_gc) - GC_FALLBACK_PRIORS["T_m_gc"]) < 1.0e-6:
            fallback_count += 1

    if not raw_tm_gc:
        print("   Skipping GC T_m calibration; no usable GC priors in training split.")
        return

    scale, bias = fit_tm_gc_calibration(raw_tm_gc, tm_true)
    config.gc_prior_tm_scale = scale
    config.gc_prior_tm_bias = bias

    raw_arr = np.asarray(raw_tm_gc, dtype=float)
    true_arr = np.asarray(tm_true, dtype=float)
    calibrated_arr = scale * raw_arr + bias
    raw_mae = float(np.mean(np.abs(raw_arr - true_arr)))
    calibrated_mae = float(np.mean(np.abs(calibrated_arr - true_arr)))
    fallback_frac = fallback_count / len(raw_tm_gc)

    print(
        "   GC T_m calibration: "
        f"n_unique={len(raw_tm_gc)}, "
        f"fallback={fallback_frac:.1%}, "
        f"raw_mae={raw_mae:.2f} K, "
        f"calibrated_mae={calibrated_mae:.2f} K, "
        f"scale={scale:.6f}, "
        f"bias={bias:.3f}"
    )


def main() -> None:
    """Main training pipeline."""
    try:
        # Parse arguments
        args = parse_args()
        if args.pretrain and args.pretrain_checkpoint is not None:
            raise ValueError(
                "Use either --pretrain or --pretrain-checkpoint, not both."
            )
        if args.probe_only and not args.run_descriptor_probe:
            args.run_descriptor_probe = True
        if not args.probe_only and args.val_data is None:
            raise ValueError("--val-data is required unless --probe-only is used.")
        if args.probe_only and args.test_data is None:
            raise ValueError("--test-data is required for --probe-only descriptor probes.")
        
        print("=" * 70)
        print("TGNN-Solv Training Pipeline")
        print("=" * 70)
        
        # Load configuration from YAML
        resume_checkpoint = None
        pretrain_info: dict[str, Any] | None = None
        if args.resume is not None:
            print(f"\n1. Loading resume checkpoint from {args.resume}...")
            resume_checkpoint = torch.load(args.resume, map_location="cpu")
            config = TGNNSolvConfig(**resume_checkpoint["config"])
            args.seed = int(resume_checkpoint.get("seed", args.seed))
            pretrain_info = resume_checkpoint.get("pretrain_info")
        else:
            print(f"\n1. Loading configuration from {args.config}...")
            config = TGNNSolvConfig.from_yaml(args.config)
        device = resolve_device(args.device)
        descriptor_mean = None
        descriptor_std = None
        if config.use_descriptor_augmentation:
            if resume_checkpoint is not None:
                descriptor_mean = resume_checkpoint.get("descriptor_mean")
                descriptor_std = resume_checkpoint.get("descriptor_std")
            if descriptor_mean is None or descriptor_std is None:
                normalizer = DescriptorNormalizer().fit(
                    pd.read_csv(args.train_data, low_memory=False)
                )
                descriptor_mean = normalizer.mean
                descriptor_std = normalizer.std
            config.descriptor_dim = int(torch.as_tensor(descriptor_mean).shape[0])
            print(
                "   Descriptor augmentation enabled: "
                f"{config.descriptor_dim} RDKit descriptors."
            )

        # Apply CLI overrides. Resumed runs keep model-shape/training-schedule
        # settings from the checkpoint, but data-loader knobs like batch size
        # are safe to override to fit the available device.
        if resume_checkpoint is None:
            if args.hidden_dim is not None:
                config.hidden_dim = args.hidden_dim
            if args.n_gnn_layers is not None:
                config.n_gnn_layers = args.n_gnn_layers
            if args.batch_size is not None:
                config.batch_size = args.batch_size
            if args.lr is not None:
                config.lr_phase2 = args.lr
            if args.epochs_phase1 is not None:
                config.epochs_phase1 = int(args.epochs_phase1)
            if args.epochs_phase2 is not None:
                config.epochs_phase2 = int(args.epochs_phase2)
            if args.epochs_phase3 is not None:
                config.epochs_phase3 = int(args.epochs_phase3)
            if args.probe_every > 0:
                config.probe_every = int(args.probe_every)
        elif any(
            override is not None
            for override in (
                args.hidden_dim,
                args.n_gnn_layers,
                args.lr,
                args.epochs_phase1,
                args.epochs_phase2,
                args.epochs_phase3,
            )
        ):
            print(
                "   Ignoring CLI config overrides for resumed training; "
                "using the checkpoint's saved config."
            )
        if resume_checkpoint is not None and args.batch_size is not None:
            config.batch_size = args.batch_size
            print(
                "   Applying resume-time batch_size override for data loading: "
                f"{config.batch_size}"
            )
        if resume_checkpoint is not None and args.probe_every > 0:
            config.probe_every = int(args.probe_every)

        if resume_checkpoint is None:
            maybe_fit_gc_tm_calibration(args.train_data, config)
        
        print(f"   Device: {device}")
        print(f"   Seed: {args.seed}")
        print(
            "   Epoch budget: "
            f"{config.epochs_phase1}/{config.epochs_phase2}/{config.epochs_phase3}"
        )
        
        # Set random seed
        print("\n2. Setting random seed...")
        set_seed(args.seed, deterministic=True)
        
        # Create experiment logger
        print("\n3. Initializing experiment logger...")
        experiment_name = args.experiment_name
        if experiment_name is None and resume_checkpoint is not None:
            experiment_name = resume_checkpoint.get("experiment_name")
        logger = ExperimentLogger(args.log_dir, experiment_name)
        logger.log_config(config)
        print(f"   Experiment: {logger.experiment_name}")
        print(f"   Log directory: {logger.exp_dir}")

        if args.probe_only:
            checkpoint_path = Path(args.checkpoint)
            if not checkpoint_path.is_file():
                raise FileNotFoundError(f"Checkpoint for --probe-only not found: {checkpoint_path}")
            print("\n4. Running descriptor probe only...")
            maybe_run_descriptor_probe(
                checkpoint_path=checkpoint_path,
                train_data=args.train_data,
                test_data=args.test_data,
                output_dir=args.descriptor_probe_output_dir,
                device=args.descriptor_probe_device,
                logger=logger,
            )
            logger.finalize(None)
            print("\nDescriptor probe completed.")
            return
        
        # Load datasets
        print("\n4. Loading datasets...")
        print("   Train:")
        train_loader = load_data(
            args.train_data,
            config,
            shuffle=True,
            seed=args.seed,
        )
        print("   Val:")
        val_loader = load_data(
            args.val_data,
            config,
            shuffle=False,
            seed=args.seed,
        )
        
        # Initialize model
        print("\n5. Initializing model...")
        model = TGNNSolv(cfg=config).to(device)
        if resume_checkpoint is not None:
            if args.pretrain or args.pretrain_checkpoint is not None:
                print(
                    "   Ignoring Stage 0 options because --resume loads a full model checkpoint."
                )
            model.load_state_dict(
                resume_checkpoint.get(
                    "model_state_dict",
                    resume_checkpoint["model_state"],
                )
            )
        if config.use_descriptor_augmentation:
            if descriptor_mean is None or descriptor_std is None:
                raise ValueError(
                    "Descriptor normalization statistics were not computed."
                )
            model.set_descriptor_normalization(descriptor_mean, descriptor_std)
        logger.log_model_summary(model)
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"   Total parameters: {total_params:,}")
        print(f"   Trainable parameters: {trainable_params:,}")

        if resume_checkpoint is None:
            if args.pretrain_checkpoint is not None:
                print("\n5a. Loading Stage 0 encoder/readout checkpoint...")
                loaded_pretrain = load_pretrained_encoder_checkpoint(
                    args.pretrain_checkpoint,
                    map_location="cpu",
                )
                pretrain_info = apply_pretrained_encoder_checkpoint(
                    model,
                    loaded_pretrain,
                    strict=True,
                )
                pretrain_info["checkpoint_path"] = str(
                    Path(args.pretrain_checkpoint).expanduser().resolve()
                )
                print(
                    "   Loaded pretrained encoder from "
                    f"{pretrain_info['checkpoint_path']}"
                )
            elif args.pretrain:
                print("\n5a. Running Stage 0 pretraining...")
                pretrain_output = (
                    Path(args.pretrain_output).expanduser().resolve()
                    if args.pretrain_output is not None
                    else derive_pretrain_checkpoint_path(args.checkpoint)
                )
                pretrain_info = run_stage0_pretraining(
                    model,
                    config,
                    device=device,
                    pretrain_source=args.pretrain_data,
                    pretrain_epochs=args.pretrain_epochs,
                    pretrain_batch_size=args.pretrain_batch_size,
                    pretrain_lr=args.pretrain_lr,
                    pretrain_max_molecules=args.pretrain_max_molecules,
                    save_path=pretrain_output,
                )
                print(
                    "   Stage 0 complete: "
                    f"{pretrain_info['smiles_count']:,} molecules, "
                    f"{pretrain_info['epochs']} epochs."
                )
                if pretrain_info.get("checkpoint_path") is not None:
                    print(
                        "   Saved pretrained encoder to "
                        f"{pretrain_info['checkpoint_path']}"
                    )
            if pretrain_info is not None:
                logger.log_artifact(
                    "pretrain_summary",
                    {
                        key: value
                        for key, value in pretrain_info.items()
                        if key != "history"
                    },
                )

        # Initialize trainer
        print("\n6. Initializing trainer...")
        trainer = TGNNSolvTrainer(model, config)
        if resume_checkpoint is not None:
            trainer.load_state_dict(
                resume_checkpoint.get("trainer_state_dict")
            )

        # Train model
        print("\n7. Starting training (3-phase curriculum)...")
        checkpoint_path = Path(args.checkpoint)

        def maybe_save_resume_checkpoint(state: dict) -> None:
            if args.checkpoint_every <= 0:
                return
            next_epoch = int(state["next_epoch_in_phase"])
            phase_epochs = int(state["phase_epochs"])
            if next_epoch % args.checkpoint_every != 0 and next_epoch < phase_epochs:
                return
            payload = build_checkpoint_payload(
                model=model,
                config=config,
                seed=args.seed,
                experiment_name=logger.experiment_name,
                trainer=trainer,
                resume_state=state,
                pretrain_info=pretrain_info,
            )
            atomic_torch_save(payload, checkpoint_path)
            print(
                "  Saved resume checkpoint "
                f"(phase {state['phase']} epoch {next_epoch}/{phase_epochs}) "
                f"to {checkpoint_path}"
            )

        probe_phases = parse_probe_phases(args.probe_phases)
        probe_evolution_csv = (
            Path(args.probe_evolution_output).expanduser().resolve()
            if args.probe_evolution_output is not None
            else checkpoint_path.with_name(f"{checkpoint_path.stem}_probe_evolution.csv")
        )
        probe_evolution_root = probe_evolution_csv.with_suffix("")

        def on_epoch_end(state: dict) -> None:
            maybe_save_resume_checkpoint(state)
            probe_every = int(getattr(config, "probe_every", 0))
            if probe_every <= 0:
                return
            phase = int(state["phase"])
            next_epoch = int(state["next_epoch_in_phase"])
            if phase not in probe_phases or next_epoch <= 0:
                return
            if next_epoch % probe_every != 0:
                return
            phase_offsets = {
                1: 0,
                2: int(config.epochs_phase1),
                3: int(config.epochs_phase1 + config.epochs_phase2),
            }
            maybe_run_probe_evolution_snapshot(
                model=model,
                config=config,
                phase=phase,
                epoch_in_phase=next_epoch - 1,
                global_epoch=phase_offsets[phase] + next_epoch,
                train_data=args.train_data,
                test_data=args.test_data,
                output_csv=probe_evolution_csv,
                output_root=probe_evolution_root,
                logger=logger,
            )

        resume_state = (
            resume_checkpoint.get("resume_state")
            if resume_checkpoint is not None
            else None
        )
        if resume_state and resume_state.get("status") == "completed":
            print("   Resume checkpoint already marks training as completed; skipping fit.")
        else:
            trainer.train_full(
                train_loader,
                val_loader,
                resume_state=resume_state,
                on_epoch_end=on_epoch_end,
            )

        # Save checkpoint
        print("\n8. Saving checkpoint...")
        checkpoint = build_checkpoint_payload(
            model=model,
            config=config,
            seed=args.seed,
            experiment_name=logger.experiment_name,
            trainer=trainer,
            resume_state={
                "status": "completed",
                "phase": 4,
                "next_epoch_in_phase": 0,
                "trainer_state_dict": trainer.state_dict(),
            },
            pretrain_info=pretrain_info,
        )
        atomic_torch_save(checkpoint, checkpoint_path)
        print(f"   Model saved to {checkpoint_path}")
        
        # Optional test evaluation
        test_metrics = None
        if args.test_data is not None:
            print("\n9. Evaluating on test set...")
            print("   Test:")
            test_loader = load_data(
                args.test_data,
                config,
                shuffle=False,
                seed=args.seed,
            )
            test_metrics = trainer.validate(test_loader, phase=2)
            
            print("\n   Test Metrics:")
            print(json.dumps(test_metrics, indent=2))
            logger.log_artifact("test_metrics", test_metrics)

        if args.run_descriptor_probe:
            print("\n9a. Running descriptor linear probe...")
            maybe_run_descriptor_probe(
                checkpoint_path=checkpoint_path,
                train_data=args.train_data,
                test_data=args.test_data,
                output_dir=args.descriptor_probe_output_dir,
                device=args.descriptor_probe_device,
                logger=logger,
            )

        manifest = build_run_manifest(
            "training_run",
            model_name=checkpoint_path.name,
            model_family="tgnn_solv",
            inputs={
                "config": args.config,
                "train_data": args.train_data,
                "val_data": args.val_data,
                "test_data": args.test_data,
                "resume_checkpoint": args.resume,
                "pretrain_enabled": bool(args.pretrain),
                "pretrain_checkpoint": args.pretrain_checkpoint,
            },
            outputs={
                "checkpoint": checkpoint_path,
            },
            metadata={
                "experiment_name": logger.experiment_name,
                "log_dir": str(logger.exp_dir),
                "seed": int(args.seed),
                "device": str(device),
                "pretrain_info": pretrain_info,
            },
        )
        model_card = build_model_card(
            checkpoint_path=checkpoint_path,
            model_family="tgnn_solv",
            config=dataclasses.asdict(config),
            metrics=test_metrics or {},
            metadata={
                "experiment_name": logger.experiment_name,
                "log_dir": str(logger.exp_dir),
                "seed": int(args.seed),
                "pretrain_info": pretrain_info,
            },
        )
        write_json(checkpoint_path.with_suffix(".manifest.json"), manifest)
        write_json(checkpoint_path.with_suffix(".model_card.json"), model_card)
        
        # Finalize logging
        print("\n10. Finalizing experiment...")
        logger.finalize(test_metrics if test_metrics else None)
        
        # Print summary
        print("\n" + "=" * 70)
        print("✓ Training completed successfully!")
        print("=" * 70)
        print(f"Model saved to: {checkpoint_path}")
        print(f"Logs saved to: {logger.exp_dir}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n{'=' * 70}", file=sys.stderr)
        print("Training failed with error:", file=sys.stderr)
        print(f"{'=' * 70}", file=sys.stderr)
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        print(f"{'=' * 70}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
