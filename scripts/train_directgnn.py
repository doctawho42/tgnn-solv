#!/usr/bin/env python3
"""CLI wrapper for training the DirectGNN baseline."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile

from pathlib import Path

import _bootstrap  # noqa: F401
import pandas as pd
import torch
from torch.utils.data import DataLoader

from tgnn_solv.artifacts import build_model_card, build_run_manifest, write_json
from tgnn_solv.baselines.direct_gnn import DirectGNN, DirectGNNTrainer
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import make_loader
from tgnn_solv.experiment_logger import ExperimentLogger
from tgnn_solv.features import compute_descriptor_normalization_stats
from tgnn_solv.seed import set_seed


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Train the DirectGNN baseline for solubility prediction.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        default=None,
        help="Optional path to the test CSV file.",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="checkpoints/directgnn.pt",
        help="Path to save the trained model checkpoint.",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to a saved training checkpoint to resume from.",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=0,
        help="Save a resumable checkpoint every N epochs (0 disables periodic saves).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Requested training device.",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs/directgnn",
        help="Root directory for experiment logs.",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Experiment name (auto-generated from timestamp if not provided).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Optional batch-size override for data loading.",
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


def load_data(
    df: pd.DataFrame,
    config: TGNNSolvConfig,
    shuffle: bool,
    seed: int,
) -> DataLoader:
    """Wrap a dataframe in a DataLoader with the requested feature paths."""
    return make_loader(
        df,
        batch_size=config.batch_size,
        shuffle=shuffle,
        num_workers=0,
        cache=True,
        use_pair_temperature_batching=(
            shuffle and config.use_pair_temperature_batching
        ),
        pair_temperature_min_group_size=config.pair_temperature_min_group_size,
        pair_temperature_group_chunk_size=config.pair_temperature_group_chunk_size,
        use_morgan_features=config.use_morgan_features,
        morgan_radius=config.morgan_radius,
        morgan_n_bits=config.morgan_n_bits,
        use_descriptor_augmentation=config.use_descriptor_augmentation,
        use_descriptor_priors=config.use_descriptor_priors,
        use_group_priors=config.use_group_priors,
        use_gc_priors_crystal=config.use_gc_priors_crystal,
        seed=seed,
    )


def atomic_torch_save(payload: dict, path: Path) -> None:
    """Atomically save a checkpoint to avoid partial writes on interruption."""
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
    model: DirectGNN,
    config: TGNNSolvConfig,
    seed: int,
    experiment_name: str,
    trainer: DirectGNNTrainer,
    resume_state: dict | None,
    train_metrics: dict[str, float] | None,
    test_metrics: dict[str, float] | None,
) -> dict:
    """Build a DirectGNN checkpoint that supports both inference and resume."""
    checkpoint = {
        "model_state": model.state_dict(),
        "model_state_dict": model.state_dict(),
        "config": dataclasses.asdict(config),
        "seed": seed,
        "experiment_name": experiment_name,
        "model_class": model.__class__.__name__,
        "trainer_state_dict": trainer.state_dict(),
        "resume_state": resume_state,
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
    }
    if config.use_descriptor_augmentation:
        checkpoint["descriptor_mean"] = model.descriptor_mean.detach().cpu()
        checkpoint["descriptor_std"] = model.descriptor_std.detach().cpu()
    return checkpoint


def save_checkpoint(
    checkpoint_path: Path,
    model: DirectGNN,
    config: TGNNSolvConfig,
    seed: int,
    experiment_name: str,
    trainer: DirectGNNTrainer,
    resume_state: dict | None,
    train_metrics: dict[str, float] | None,
    test_metrics: dict[str, float] | None,
) -> None:
    """Save model weights and training metadata."""
    checkpoint = build_checkpoint_payload(
        model=model,
        config=config,
        seed=seed,
        experiment_name=experiment_name,
        trainer=trainer,
        resume_state=resume_state,
        train_metrics=train_metrics,
        test_metrics=test_metrics,
    )
    atomic_torch_save(checkpoint, checkpoint_path)


def main() -> None:
    """Run the DirectGNN training pipeline."""
    try:
        args = parse_args()

        config_path = _bootstrap.resolve_path(args.config)
        train_path = _bootstrap.resolve_path(args.train_data)
        val_path = _bootstrap.resolve_path(args.val_data)
        test_path = _bootstrap.resolve_path(args.test_data) if args.test_data else None
        checkpoint_path = _bootstrap.resolve_path(args.checkpoint)
        log_dir = _bootstrap.resolve_path(args.log_dir)

        print("=" * 70)
        print("DirectGNN Training Pipeline")
        print("=" * 70)

        resume_checkpoint = None
        if args.resume is not None:
            resume_path = _bootstrap.resolve_path(args.resume)
            print(f"\n1. Loading resume checkpoint from {resume_path}...")
            resume_checkpoint = torch.load(
                resume_path,
                map_location="cpu",
                weights_only=False,
            )
            config = TGNNSolvConfig(**resume_checkpoint["config"])
            args.seed = int(resume_checkpoint.get("seed", args.seed))
        else:
            print(f"\n1. Loading configuration from {config_path}...")
            config = TGNNSolvConfig.from_yaml(str(config_path))
        device = resolve_device(args.device)
        if args.batch_size is not None:
            config.batch_size = int(args.batch_size)
            print(f"   Applying batch_size override: {config.batch_size}")

        print(f"   Device: {device}")
        print(f"   Seed: {args.seed}")

        print("\n2. Setting random seed...")
        set_seed(args.seed, deterministic=True)

        print("\n3. Loading dataframes...")
        train_df = pd.read_csv(train_path)
        val_df = pd.read_csv(val_path)
        test_df = pd.read_csv(test_path) if test_path is not None else None

        descriptor_mean = None
        descriptor_std = None
        if config.use_descriptor_augmentation:
            if resume_checkpoint is not None:
                descriptor_mean = resume_checkpoint.get("descriptor_mean")
                descriptor_std = resume_checkpoint.get("descriptor_std")
            if descriptor_mean is None or descriptor_std is None:
                smiles_series = pd.concat(
                    [
                        train_df["solute_smiles"].astype(str),
                        train_df["solvent_smiles"].astype(str),
                    ],
                    axis=0,
                    ignore_index=True,
                )
                descriptor_mean, descriptor_std = compute_descriptor_normalization_stats(
                    smiles_series.tolist()
                )
            config.descriptor_dim = int(torch.as_tensor(descriptor_mean).shape[0])
            print(
                "   Descriptor augmentation enabled: "
                f"{config.descriptor_dim} RDKit descriptors."
            )

        print("\n4. Initializing experiment logger...")
        experiment_name = args.experiment_name
        if experiment_name is None and resume_checkpoint is not None:
            experiment_name = resume_checkpoint.get("experiment_name")
        logger = ExperimentLogger(str(log_dir), experiment_name)
        logger.log_config(config)
        print(f"   Experiment: {logger.experiment_name}")
        print(f"   Log directory: {logger.exp_dir}")

        print("\n5. Loading datasets...")
        print("   Train:")
        train_loader = load_data(train_df, config, shuffle=True, seed=args.seed)
        print("   Val:")
        val_loader = load_data(val_df, config, shuffle=False, seed=args.seed)
        test_loader = None
        if test_path is not None:
            print("   Test:")
            if test_df is None:
                raise ValueError("test_df must be loaded when test_path is provided.")
            test_loader = load_data(test_df, config, shuffle=False, seed=args.seed)

        print("\n6. Initializing DirectGNN...")
        model = DirectGNN(cfg=config).to(device)
        if resume_checkpoint is not None:
            state = resume_checkpoint.get(
                "model_state_dict",
                resume_checkpoint.get("model_state"),
            )
            if state is None:
                raise ValueError("Resume checkpoint is missing model weights.")
            model.load_state_dict(state)
        if config.use_descriptor_augmentation:
            if descriptor_mean is None or descriptor_std is None:
                raise ValueError("Descriptor normalization statistics were not computed.")
            model.set_descriptor_normalization(descriptor_mean, descriptor_std)
        logger.log_model_summary(model)
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(
            p.numel() for p in model.parameters() if p.requires_grad
        )
        print(f"   Total parameters: {total_params:,}")
        print(f"   Trainable parameters: {trainable_params:,}")

        print("\n7. Training model...")
        trainer = DirectGNNTrainer(model, device=device)
        if resume_checkpoint is not None:
            trainer.load_state_dict(resume_checkpoint.get("trainer_state_dict"))

        checkpoint_path = Path(checkpoint_path)

        def maybe_save_resume_checkpoint(state: dict) -> None:
            if args.checkpoint_every <= 0:
                return
            next_epoch = int(state["next_epoch"])
            total_epochs = int(state["total_epochs"])
            if next_epoch % args.checkpoint_every != 0 and next_epoch < total_epochs:
                return
            save_checkpoint(
                checkpoint_path=checkpoint_path,
                model=model,
                config=config,
                seed=args.seed,
                experiment_name=logger.experiment_name,
                trainer=trainer,
                resume_state=state,
                train_metrics=None,
                test_metrics=None,
            )
            print(
                "   Saved resume checkpoint "
                f"(epoch {next_epoch}/{total_epochs}) to {checkpoint_path}"
            )

        resume_state = (
            resume_checkpoint.get("resume_state")
            if resume_checkpoint is not None
            else None
        )
        if resume_state and resume_state.get("status") == "completed":
            print("   Resume checkpoint already marks training as completed; skipping fit.")
            train_metrics = resume_checkpoint.get("train_metrics")
        else:
            train_metrics = trainer.train(
                train_loader,
                val_loader,
                n_epochs=config.epochs_phase2,
                lr=config.lr_phase2,
                patience=config.patience,
                start_epoch=int(resume_state.get("next_epoch", 0)) if resume_state else 0,
                optimizer_state_dict=(
                    resume_state.get("optimizer_state_dict")
                    if resume_state and resume_state.get("status") == "in_progress"
                    else None
                ),
                scheduler_state_dict=(
                    resume_state.get("scheduler_state_dict")
                    if resume_state and resume_state.get("status") == "in_progress"
                    else None
                ),
                on_epoch_end=maybe_save_resume_checkpoint,
            )
        logger.log_artifact("train_metrics", train_metrics)

        test_metrics = None
        if test_loader is not None:
            print("\n8. Evaluating on test set...")
            test_metrics = trainer.evaluate(test_loader)
            print(json.dumps(test_metrics, indent=2))
            logger.log_artifact("test_metrics", test_metrics)
        else:
            print("\n8. Skipping test evaluation (no --test-data provided).")

        print("\n9. Saving checkpoint...")
        save_checkpoint(
            checkpoint_path=checkpoint_path,
            model=model,
            config=config,
            seed=args.seed,
            experiment_name=logger.experiment_name,
            trainer=trainer,
            resume_state={
                "status": "completed",
                "next_epoch": int(config.epochs_phase2),
                "total_epochs": int(config.epochs_phase2),
                "trainer_state_dict": trainer.state_dict(),
            },
            train_metrics=train_metrics,
            test_metrics=test_metrics,
        )
        print(f"   Model saved to {checkpoint_path}")

        manifest = build_run_manifest(
            "training_run",
            model_name=checkpoint_path.name,
            model_family="direct_gnn",
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
            model_family="direct_gnn",
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

        print("\n10. Finalizing experiment...")
        logger.finalize(test_metrics if test_metrics is not None else train_metrics)

        print("\n" + "=" * 70)
        print("Training completed successfully!")
        print("=" * 70)
        print(f"Model saved to: {checkpoint_path}")
        print(f"Logs saved to: {logger.exp_dir}")
        print("=" * 70)

    except ImportError as exc:
        print(f"ImportError: {exc}", file=sys.stderr)
        print(
            "TODO: DirectGNN dependencies are missing in the current environment.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        print(f"\n{'=' * 70}", file=sys.stderr)
        print("DirectGNN training failed with error:", file=sys.stderr)
        print(f"{'=' * 70}", file=sys.stderr)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"{'=' * 70}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
