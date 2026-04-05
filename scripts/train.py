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

import _bootstrap  # noqa: F401
import torch
from torch.utils.data import DataLoader

from tgnn_solv.artifacts import build_model_card, build_run_manifest, write_json
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import make_loader
from tgnn_solv.experiment_logger import ExperimentLogger
from tgnn_solv.features import NODE_FEAT_DIM, EDGE_FEAT_DIM
from tgnn_solv.group_contribution import (
    GC_FALLBACK_PRIORS,
    compute_gc_priors,
    fit_tm_gc_calibration,
)
from tgnn_solv.model import TGNNSolv
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
        required=True,
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
) -> dict:
    """Build a training checkpoint that supports both inference and resume."""
    return {
        "model_state": model.state_dict(),
        "model_state_dict": model.state_dict(),
        "config": dataclasses.asdict(config),
        "node_feat_dim": NODE_FEAT_DIM,
        "edge_feat_dim": EDGE_FEAT_DIM,
        "seed": seed,
        "experiment_name": experiment_name,
        "trainer_state_dict": trainer.state_dict(),
        "resume_state": resume_state,
    }


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
        use_descriptor_priors=config.use_descriptor_priors,
        use_group_priors=config.use_group_priors,
        use_gc_priors_crystal=config.use_gc_priors_crystal,
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
        
        print("=" * 70)
        print("TGNN-Solv Training Pipeline")
        print("=" * 70)
        
        # Load configuration from YAML
        resume_checkpoint = None
        if args.resume is not None:
            print(f"\n1. Loading resume checkpoint from {args.resume}...")
            resume_checkpoint = torch.load(args.resume, map_location="cpu")
            config = TGNNSolvConfig(**resume_checkpoint["config"])
            args.seed = int(resume_checkpoint.get("seed", args.seed))
        else:
            print(f"\n1. Loading configuration from {args.config}...")
            config = TGNNSolvConfig.from_yaml(args.config)
        device = resolve_device(args.device)

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
        elif any(
            override is not None
            for override in (
                args.hidden_dim,
                args.n_gnn_layers,
                args.lr,
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

        if resume_checkpoint is None:
            maybe_fit_gc_tm_calibration(args.train_data, config)
        
        print(f"   Device: {device}")
        print(f"   Seed: {args.seed}")
        
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
            model.load_state_dict(
                resume_checkpoint.get(
                    "model_state_dict",
                    resume_checkpoint["model_state"],
                )
            )
        logger.log_model_summary(model)
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"   Total parameters: {total_params:,}")
        print(f"   Trainable parameters: {trainable_params:,}")
        
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
            )
            atomic_torch_save(payload, checkpoint_path)
            print(
                "  Saved resume checkpoint "
                f"(phase {state['phase']} epoch {next_epoch}/{phase_epochs}) "
                f"to {checkpoint_path}"
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
                on_epoch_end=maybe_save_resume_checkpoint,
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
            },
            outputs={
                "checkpoint": checkpoint_path,
            },
            metadata={
                "experiment_name": logger.experiment_name,
                "log_dir": str(logger.exp_dir),
                "seed": int(args.seed),
                "device": str(device),
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
