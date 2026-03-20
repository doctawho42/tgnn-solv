"""
Run baseline and compare with TGNN-Solv.
"""

import time
from typing import Dict, Optional

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from ..config import TGNNSolvConfig
from ..model import TGNNSolv
from ..evaluate import Evaluator
from .direct_gnn import DirectGNN, DirectGNNTrainer


def run_baseline(
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader,
    cfg: TGNNSolvConfig,
    device: torch.device,
    n_epochs: int = 200,
    lr: float = 1e-4,
    patience: int = 20,
) -> Dict[str, float]:
    """
    Train DirectGNN baseline and evaluate on test set.

    Returns metrics dict.
    """
    print("\n" + "=" * 60)
    print("Training DirectGNN Baseline")
    print("  (same GNN + cross-attention, no physics layer)")
    print("=" * 60)

    t0 = time.time()

    model = DirectGNN(cfg=cfg).to(device)
    trainer = DirectGNNTrainer(model, device)
    trainer.train(
        train_loader, val_loader,
        n_epochs=n_epochs, lr=lr, patience=patience,
    )
    metrics = trainer.evaluate(test_loader)
    metrics["time_s"] = time.time() - t0

    print(f"\n  DirectGNN test results:")
    print(f"    MAE  = {metrics['mae']:.3f}")
    print(f"    RMSE = {metrics['rmse']:.3f}")
    print(f"    R²   = {metrics['r2']:.4f}")

    return metrics


def compare_with_tgnn(
    tgnn_model: TGNNSolv,
    tgnn_cfg: TGNNSolvConfig,
    baseline_metrics: Dict[str, float],
    test_loader: DataLoader,
    test_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Evaluate TGNN-Solv and compare with baseline.

    Returns DataFrame with both rows.
    """
    print("\n" + "=" * 60)
    print("Comparing TGNN-Solv vs DirectGNN")
    print("=" * 60)

    evaluator = Evaluator(tgnn_model, tgnn_cfg)
    report = evaluator.evaluate(test_loader, test_df)
    tgnn_metrics = report["overall"]
    tgnn_metrics["name"] = "TGNN-Solv"

    rows = [baseline_metrics, tgnn_metrics]
    df = pd.DataFrame(rows)

    print(f"\n  {'Model':15s} {'MAE':>8s} {'RMSE':>8s} {'R²':>8s}")
    print("  " + "-" * 45)
    for _, row in df.iterrows():
        print(f"  {row['name']:15s} {row['mae']:8.3f} "
              f"{row['rmse']:8.3f} {row['r2']:8.4f}")

    # Improvement
    bl_mae = baseline_metrics["mae"]
    tgnn_mae = tgnn_metrics["mae"]
    delta = bl_mae - tgnn_mae
    pct = delta / bl_mae * 100 if bl_mae > 0 else 0

    print(f"\n  TGNN-Solv improvement over DirectGNN:")
    print(f"    ΔMAE = {delta:+.3f} ({pct:+.1f}%)")

    if delta > 0:
        print("    → Physics-informed approach helps ✓")
    else:
        print("    → Physics layer does not help ✗")
        print("    → Investigate: ablation study needed")

    return df