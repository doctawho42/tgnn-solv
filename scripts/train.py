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
from pathlib import Path

import _bootstrap  # noqa: F401
import torch
from torch.utils.data import DataLoader

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import make_loader
from tgnn_solv.experiment_logger import ExperimentLogger
from tgnn_solv.features import NODE_FEAT_DIM, EDGE_FEAT_DIM
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
        seed=seed,
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
        print(f"\n1. Loading configuration from {args.config}...")
        config = TGNNSolvConfig.from_yaml(args.config)
        device = resolve_device(args.device)
        
        # Apply CLI overrides
        if args.hidden_dim is not None:
            config.hidden_dim = args.hidden_dim
        if args.n_gnn_layers is not None:
            config.n_gnn_layers = args.n_gnn_layers
        if args.batch_size is not None:
            config.batch_size = args.batch_size
        if args.lr is not None:
            config.lr_phase2 = args.lr
        
        print(f"   Device: {device}")
        print(f"   Seed: {args.seed}")
        
        # Set random seed
        print("\n2. Setting random seed...")
        set_seed(args.seed, deterministic=True)
        
        # Create experiment logger
        print("\n3. Initializing experiment logger...")
        logger = ExperimentLogger(args.log_dir, args.experiment_name)
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
        logger.log_model_summary(model)
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"   Total parameters: {total_params:,}")
        print(f"   Trainable parameters: {trainable_params:,}")
        
        # Initialize trainer
        print("\n6. Initializing trainer...")
        trainer = TGNNSolvTrainer(model, config)
        
        # Train model
        print("\n7. Starting training (3-phase curriculum)...")
        trainer.train_full(train_loader, val_loader)
        
        # Save checkpoint
        print("\n8. Saving checkpoint...")
        checkpoint_path = Path(args.checkpoint)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        
        checkpoint = {
            "model_state": model.state_dict(),
            "model_state_dict": model.state_dict(),
            "config": dataclasses.asdict(config),
            "node_feat_dim": NODE_FEAT_DIM,
            "edge_feat_dim": EDGE_FEAT_DIM,
            "seed": args.seed,
        }
        torch.save(checkpoint, checkpoint_path)
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
