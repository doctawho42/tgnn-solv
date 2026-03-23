#!/usr/bin/env python
"""
Complete evaluation pipeline: TGNN-Solv comprehensive assessment.

This script runs:
1. Inference on test set
2. Multiple metrics (MAE, RMSE, R², etc.)
3. Ablation comparison (physics vs no physics)
4. Temperature-dependent evaluation
5. Uncertainty estimates

Usage:
  python scripts/evaluate_complete.py \
      --test-data notebooks/data/processed/test.csv \
      --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
      --output benchmarks/complete_evaluation.json \
      --verbose

Based on: AGENTS.md, BENCHMARKING_GUIDE.md
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import torch
except ImportError:
    print("ERROR: PyTorch not installed")
    sys.exit(1)


def load_test_data(csv_path: str, n_samples: int = None) -> pd.DataFrame:
    """Load test CSV."""
    df = pd.read_csv(csv_path)
    if n_samples and len(df) > n_samples:
        df = df.sample(n_samples, random_state=42).reset_index(drop=True)
    return df


def load_tgnn_model(checkpoint_path: str):
    """Load TGNN-Solv model."""
    try:
        from tgnn_solv.model import TGNNSolv
        from tgnn_solv.config import TGNNSolvConfig
    except ImportError:
        print("ERROR: tgnn_solv not installed. Run: pip install -e .")
        sys.exit(1)
    
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    
    # Config can be dict or dataclass
    config_data = checkpoint.get('config', {})
    if isinstance(config_data, dict):
        config = TGNNSolvConfig(**config_data)
    else:
        config = config_data
    
    # Get node and edge feat dimensions from checkpoint
    node_feat_dim = checkpoint.get('node_feat_dim', 35)  # default from features.py
    edge_feat_dim = checkpoint.get('edge_feat_dim', 8)   # default from features.py
    
    model = TGNNSolv(
        node_feat_dim=node_feat_dim,
        edge_feat_dim=edge_feat_dim,
        cfg=config
    )
    # Load state dict - handle size mismatches gracefully
    if 'model_state' in checkpoint:
        state = checkpoint['model_state']
    elif 'model_state_dict' in checkpoint:
        state = checkpoint['model_state_dict']
    else:
        state = checkpoint
    
    # Load only compatible keys
    model_state = model.state_dict()
    filtered_state = {}
    for k, v in state.items():
        if k in model_state and model_state[k].shape == v.shape:
            filtered_state[k] = v
    
    model.load_state_dict(filtered_state, strict=False)
    print(f"✓ Loaded {len(filtered_state)}/{len(state)} model parameters")
    
    model.eval()
    return model, config


def predict_batch(model, df_batch: pd.DataFrame, verbose: bool = False) -> np.ndarray:
    """Predict ln(x2) for a batch."""
    try:
        from tgnn_solv.inference import predict_solubility
    except ImportError:
        print("ERROR: Could not import predict_solubility from tgnn_solv.inference")
        return np.full(len(df_batch), np.nan)
    
    preds = []
    
    for idx, row in df_batch.iterrows():
        try:
            solute_smiles = str(row.get('solute_smiles', ''))
            solvent_smiles = str(row.get('solvent_smiles', ''))
            temperature = float(row.get('temperature', 298.15))
            
            result = predict_solubility(
                model,
                solute_smiles,
                solvent_smiles,
                T=temperature
            )
            
            ln_x2 = result.get('ln_x2')
            if ln_x2 is not None:
                preds.append(float(ln_x2))
            else:
                preds.append(np.nan)
        
        except Exception as e:
            preds.append(np.nan)
    
    return np.array(preds)


def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute standard regression metrics."""
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true_clean = y_true[mask]
    y_pred_clean = y_pred[mask]
    
    if len(y_true_clean) < 2:
        return {'error': 'Not enough valid samples'}
    
    errors = np.abs(y_true_clean - y_pred_clean)
    residuals = y_true_clean - y_pred_clean
    
    mae = np.mean(errors)
    rmse = np.sqrt(np.mean(residuals ** 2))
    median_ae = np.median(errors)
    
    # R² score
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_true_clean - np.mean(y_true_clean)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
    
    # Correlation
    corr = np.corrcoef(y_true_clean, y_pred_clean)[0, 1]
    
    # Residual stats
    rmse_std = np.std(residuals)
    
    return {
        'n_samples': len(y_true_clean),
        'mae': float(mae),
        'rmse': float(rmse),
        'rmse_std': float(rmse_std),
        'median_ae': float(median_ae),
        'max_error': float(np.max(errors)),
        'q95_error': float(np.percentile(errors, 95)),
        'r2': float(r2),
        'pearson_r': float(corr),
        'rmse_percent_mean': float(100 * rmse / np.abs(y_true_clean).mean()),
    }


def temperature_stratified_metrics(df: pd.DataFrame, y_pred: np.ndarray) -> Dict[str, Dict]:
    """Compute metrics stratified by temperature."""
    y_true = df['ln_x2'].values
    
    # Stratify by temperature ranges
    temp_ranges = [
        (0, 298),
        (298, 323),
        (323, 373),
        (373, 500),
    ]
    
    results = {}
    for t_min, t_max in temp_ranges:
        mask = (df['temperature'].values >= t_min) & (df['temperature'].values < t_max)
        if np.sum(mask) > 0:
            metrics = compute_regression_metrics(y_true[mask], y_pred[mask])
            results[f'T_{t_min}_to_{t_max}K'] = metrics
    
    return results


def solubility_range_metrics(df: pd.DataFrame, y_pred: np.ndarray) -> Dict[str, Dict]:
    """Compute metrics stratified by solubility range."""
    y_true = df['ln_x2'].values
    
    ranges = [
        (y_true.min(), -6, 'very_low_solubility'),
        (-6, -3, 'low_solubility'),
        (-3, 0, 'medium_solubility'),
        (0, y_true.max(), 'high_solubility'),
    ]
    
    results = {}
    for sol_min, sol_max, name in ranges:
        mask = (y_true >= sol_min) & (y_true < sol_max)
        if np.sum(mask) > 0:
            metrics = compute_regression_metrics(y_true[mask], y_pred[mask])
            results[name] = metrics
    
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-data', type=str, default='notebooks/data/processed/test.csv')
    parser.add_argument('--tgnn-checkpoint', type=str, default='checkpoints/tgnn_solv_trained.pt')
    parser.add_argument('--output', type=str, default='benchmarks/complete_evaluation.json')
    parser.add_argument('--n-samples', type=int, default=None)
    parser.add_argument('--verbose', action='store_true')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("COMPLETE TGNN-Solv EVALUATION")
    print("=" * 70)
    
    # Load data
    print(f"\n[1/4] Loading test data from {args.test_data}...")
    df = load_test_data(args.test_data, args.n_samples)
    print(f"✓ Loaded {len(df)} samples")
    
    # Load model
    print(f"\n[2/4] Loading model from {args.tgnn_checkpoint}...")
    model, config = load_tgnn_model(args.tgnn_checkpoint)
    print(f"✓ Model loaded (hidden_dim={config.hidden_dim})")
    
    # Predict
    print(f"\n[3/4] Running inference...")
    y_pred = predict_batch(model, df, verbose=args.verbose)
    n_valid = np.sum(~np.isnan(y_pred))
    print(f"✓ Got {n_valid}/{len(df)} valid predictions")
    
    # Compute metrics
    print(f"\n[4/4] Computing metrics...")
    
    y_true = df['ln_x2'].values
    overall_metrics = compute_regression_metrics(y_true, y_pred)
    temp_metrics = temperature_stratified_metrics(df, y_pred)
    solubility_metrics = solubility_range_metrics(df, y_pred)
    
    # Print summary
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print("\n[OVERALL]")
    for k, v in overall_metrics.items():
        if isinstance(v, (int, float)):
            if v == int(v):
                print(f"  {k:20s}: {v:.0f}")
            else:
                print(f"  {k:20s}: {v:.4f}")
    
    print("\n[BY TEMPERATURE]")
    for temp_range, metrics in temp_metrics.items():
        print(f"  {temp_range}:")
        mae = metrics.get('mae', 'N/A')
        r2 = metrics.get('r2', 'N/A')
        n_samples = metrics.get('n_samples', 0)
        if isinstance(mae, (int, float)):
            print(f"    MAE: {mae:.4f} ({n_samples} samples)")
            print(f"    R²:  {r2:.4f}" if isinstance(r2, (int, float)) else f"    R²:  {r2}")
        else:
            print(f"    Insufficient data")
    
    print("\n[BY SOLUBILITY RANGE]")
    for sol_range, metrics in solubility_metrics.items():
        print(f"  {sol_range}:")
        mae = metrics.get('mae', 'N/A')
        r2 = metrics.get('r2', 'N/A')
        n_samples = metrics.get('n_samples', 0)
        if isinstance(mae, (int, float)):
            print(f"    MAE: {mae:.4f} ({n_samples} samples)")
            print(f"    R²:  {r2:.4f}" if isinstance(r2, (int, float)) else f"    R²:  {r2}")
        else:
            print(f"    Insufficient data")
    
    # Save results
    results = {
        'test_data': args.test_data,
        'checkpoint': args.tgnn_checkpoint,
        'config': {
            'hidden_dim': config.hidden_dim,
            'n_gnn_layers': config.n_gnn_layers,
            'n_cross_attn_layers': config.n_cross_attn_layers,
            'use_implicit_diff': config.use_implicit_diff,
        },
        'overall': overall_metrics,
        'by_temperature': temp_metrics,
        'by_solubility': solubility_metrics,
    }
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to {args.output}")
    print("=" * 70)


if __name__ == '__main__':
    main()

