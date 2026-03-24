#!/usr/bin/env python3
"""CLI wrapper for training the DirectGNN baseline."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys

from pathlib import Path

import _bootstrap  # noqa: F401
import pandas as pd
import torch
from torch.utils.data import DataLoader

from tgnn_solv.baselines.direct_gnn import DirectGNN, DirectGNNTrainer
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import TGNNSolvDataset, collate_fn
from tgnn_solv.experiment_logger import ExperimentLogger
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


def load_data(csv_path: Path, batch_size: int, shuffle: bool) -> DataLoader:
    """Load a CSV dataset and wrap it in a DataLoader."""
    df = pd.read_csv(csv_path)
    dataset = TGNNSolvDataset(df, cache=True)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=collate_fn,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
        drop_last=shuffle and len(dataset) > batch_size,
    )


def save_checkpoint(
    checkpoint_path: Path,
    model: DirectGNN,
    config: TGNNSolvConfig,
    seed: int,
    train_metrics: dict[str, float] | None,
    test_metrics: dict[str, float] | None,
) -> None:
    """Save model weights and training metadata."""
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "config": dataclasses.asdict(config),
        "seed": seed,
        "model_class": model.__class__.__name__,
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
    }
    torch.save(checkpoint, checkpoint_path)


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

        print(f"\n1. Loading configuration from {config_path}...")
        config = TGNNSolvConfig.from_yaml(str(config_path))
        device = resolve_device(args.device)

        print(f"   Device: {device}")
        print(f"   Seed: {args.seed}")

        print("\n2. Setting random seed...")
        set_seed(args.seed, deterministic=True)

        print("\n3. Initializing experiment logger...")
        logger = ExperimentLogger(str(log_dir))
        logger.log_config(config)
        print(f"   Experiment: {logger.experiment_name}")
        print(f"   Log directory: {logger.exp_dir}")

        print("\n4. Loading datasets...")
        print("   Train:")
        train_loader = load_data(train_path, config.batch_size, shuffle=True)
        print("   Val:")
        val_loader = load_data(val_path, config.batch_size, shuffle=False)
        test_loader = None
        if test_path is not None:
            print("   Test:")
            test_loader = load_data(test_path, config.batch_size, shuffle=False)

        print("\n5. Initializing DirectGNN...")
        model = DirectGNN(cfg=config).to(device)
        logger.log_model_summary(model)
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(
            p.numel() for p in model.parameters() if p.requires_grad
        )
        print(f"   Total parameters: {total_params:,}")
        print(f"   Trainable parameters: {trainable_params:,}")

        print("\n6. Training model...")
        trainer = DirectGNNTrainer(model, device=device)
        train_metrics = trainer.train(
            train_loader,
            val_loader,
            n_epochs=config.epochs_phase2,
            lr=config.lr_phase2,
            patience=config.patience,
        )
        logger.log_artifact("train_metrics", train_metrics)

        test_metrics = None
        if test_loader is not None:
            print("\n7. Evaluating on test set...")
            test_metrics = trainer.evaluate(test_loader)
            print(json.dumps(test_metrics, indent=2))
            logger.log_artifact("test_metrics", test_metrics)
        else:
            print("\n7. Skipping test evaluation (no --test-data provided).")

        print("\n8. Saving checkpoint...")
        save_checkpoint(
            checkpoint_path=checkpoint_path,
            model=model,
            config=config,
            seed=args.seed,
            train_metrics=train_metrics,
            test_metrics=test_metrics,
        )
        print(f"   Model saved to {checkpoint_path}")

        print("\n9. Finalizing experiment...")
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
