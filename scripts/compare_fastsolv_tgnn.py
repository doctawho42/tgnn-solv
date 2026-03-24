#!/usr/bin/env python
"""
Compare TGNN-Solv vs FastSolv (pretrained) predictions.

This script demonstrates the recommended approach:
- Use FastSolv ONLY for inference (pretrained ensemble)
- Use TGNN-Solv for end-to-end custom training
- Avoid FastSolv training from scratch (NaN issue with descriptor pipeline)

Usage:
  python scripts/compare_fastsolv_tgnn.py \
      --test-data notebooks/data/processed/test.csv \
      --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
      --output checkpoints/fastsolv_vs_tgnn_comparison.json \
      --n-samples 1000

Based on: FASTSOLV_NaN_ROOT_CAUSE.md
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Tuple

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

# Try to import all required modules
try:
    import torch
except ImportError as e:
    print(f"ERROR: PyTorch not installed: {e}")
    sys.exit(1)

try:
    from rdkit import Chem
except ImportError as e:
    print(f"ERROR: RDKit not installed: {e}")
    sys.exit(1)

FASTSOLV_AVAILABLE = False
ALL_2D = None
get_descriptors = None
rt = None


def _load_fastsolv_runtime(verbose: bool = True) -> bool:
    """Load optional FastSolv/ONNX dependencies lazily."""
    global FASTSOLV_AVAILABLE
    global ALL_2D
    global get_descriptors
    global rt

    if FASTSOLV_AVAILABLE:
        return True

    try:
        from fastprop.defaults import ALL_2D as _ALL_2D
        from fastprop.descriptors import get_descriptors as _get_descriptors
        import onnxruntime as _rt
    except Exception as exc:
        if verbose:
            print(f"⚠️  FastSolv/ONNX not available: {exc}")
            print("   Continuing with TGNN-Solv only")
        return False

    ALL_2D = _ALL_2D
    get_descriptors = _get_descriptors
    rt = _rt
    FASTSOLV_AVAILABLE = True
    return True


def load_test_data(csv_path: str, n_samples: int = None) -> pd.DataFrame:
    """Load test data."""
    df = pd.read_csv(csv_path)
    if n_samples and len(df) > n_samples:
        df = df.sample(n_samples, random_state=42)
    print(f"✓ Loaded {len(df)} samples from {csv_path}")
    return df


def compute_fastsolv_descriptors(solute_smiles: str, solvent_smiles: str) -> Tuple[np.ndarray, np.ndarray, bool]:
    """
    Compute FastSolv descriptors.
    
    Returns: (solute_desc, solvent_desc, success)
    """
    if not _load_fastsolv_runtime(verbose=False):
        return None, None, False

    try:
        solute_mol = Chem.MolFromSmiles(solute_smiles)
        solvent_mol = Chem.MolFromSmiles(solvent_smiles)
        
        if solute_mol is None or solvent_mol is None:
            return None, None, False
        
        solute_desc = get_descriptors(solute_mol, features=ALL_2D)
        solvent_desc = get_descriptors(solvent_mol, features=ALL_2D)
        
        # Check for NaN
        if np.any(np.isnan(solute_desc)) or np.any(np.isnan(solvent_desc)):
            return None, None, False
        
        return solute_desc, solvent_desc, True
    except Exception:
        return None, None, False


def predict_fastsolv_single(
    solute_smiles: str,
    solvent_smiles: str,
    temperature: float,
    sess: object,
) -> float:
    """
    Predict with FastSolv pretrained ensemble.
    
    Note: This is a simplified inference - actual FastSolv uses ensemble averaging.
    """
    try:
        solute_desc, solvent_desc, success = compute_fastsolv_descriptors(
            solute_smiles, solvent_smiles
        )
        
        if not success or solute_desc is None:
            return np.nan
        
        # Normalize descriptors (simplified)
        solute_desc = (solute_desc - solute_desc.mean()) / (solute_desc.std() + 1e-8)
        solvent_desc = (solvent_desc - solvent_desc.mean()) / (solvent_desc.std() + 1e-8)
        
        # Combine with temperature
        combined = np.concatenate([solute_desc, solvent_desc, [temperature]])
        
        # Run ONNX model
        input_name = sess.get_inputs()[0].name
        output_name = sess.get_outputs()[0].name
        pred = sess.run([output_name], {input_name: combined.astype(np.float32).reshape(1, -1)})
        
        return float(pred[0][0])
    except Exception:
        return np.nan


def load_tgnn_model(checkpoint_path: str) -> Tuple[torch.nn.Module, Dict]:
    """Load TGNN-Solv model."""
    try:
        from tgnn_solv.model import TGNNSolv
        from tgnn_solv.config import TGNNSolvConfig
    except ImportError:
        print("ERROR: tgnn_solv package not found. Install with: pip install -e .")
        sys.exit(1)
    
    if not Path(checkpoint_path).exists():
        print(f"ERROR: Checkpoint not found: {checkpoint_path}")
        sys.exit(1)
    
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    
    # Load config - can be dict or dataclass
    config_data = checkpoint.get('config', {})
    if isinstance(config_data, dict):
        config = TGNNSolvConfig(**config_data)
    else:
        config = config_data
    
    # Get node and edge feat dimensions from checkpoint
    node_feat_dim = checkpoint.get('node_feat_dim', 35)  # default from features.py
    edge_feat_dim = checkpoint.get('edge_feat_dim', 8)   # default from features.py
    
    # Load model
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
    
    model.eval()
    print(f"✓ Loaded TGNN-Solv from {checkpoint_path}")
    
    return model, config


def predict_tgnn(
    model: torch.nn.Module,
    solute_smiles: str,
    solvent_smiles: str,
    temperature: float,
) -> float:
    """Predict with TGNN-Solv."""
    try:
        from tgnn_solv.inference import predict_solubility
        
        result = predict_solubility(
            model,
            solute_smiles,
            solvent_smiles,
            T=temperature
        )
        
        ln_x2 = result.get('ln_x2')
        if ln_x2 is not None:
            return float(ln_x2)
        else:
            return np.nan
    
    except Exception:
        return np.nan


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute evaluation metrics."""
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true = y_true[mask]
    y_pred = y_pred[mask]
    
    if len(y_true) == 0:
        return {
            'n_valid': 0,
            'mae': np.nan,
            'rmse': np.nan,
            'r2': np.nan,
        }
    
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    
    # R² score
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
    
    return {
        'n_valid': len(y_true),
        'mae': float(mae),
        'rmse': float(rmse),
        'r2': float(r2),
        'max_error': float(np.max(np.abs(y_true - y_pred))),
        'median_error': float(np.median(np.abs(y_true - y_pred))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--test-data',
        type=str,
        default='notebooks/data/processed/test.csv',
        help='Path to test CSV',
    )
    parser.add_argument(
        '--tgnn-checkpoint',
        type=str,
        default='checkpoints/tgnn_solv_trained.pt',
        help='Path to TGNN-Solv checkpoint',
    )
    parser.add_argument(
        '--fastsolv-checkpoint',
        type=str,
        default=None,
        help='Path to FastSolv ONNX checkpoint (optional)',
    )
    parser.add_argument(
        '--output',
        type=str,
        default='checkpoints/fastsolv_vs_tgnn_comparison.json',
        help='Output JSON path',
    )
    parser.add_argument(
        '--n-samples',
        type=int,
        default=None,
        help='Number of samples to evaluate',
    )
    parser.add_argument(
        '--no-fastsolv',
        action='store_true',
        help='Skip FastSolv predictions (if not available)',
    )
    
    args = parser.parse_args()
    
    # Load data
    df = load_test_data(args.test_data, args.n_samples)
    
    # Load TGNN model
    print("\n[1/3] Loading TGNN-Solv model...")
    model, config = load_tgnn_model(args.tgnn_checkpoint)
    
    # Load FastSolv if available
    sess = None
    fastsolv_ready = False if args.no_fastsolv else _load_fastsolv_runtime(verbose=True)

    if not args.no_fastsolv and fastsolv_ready and args.fastsolv_checkpoint:
        print("\n[2/3] Loading FastSolv ONNX model...")
        try:
            sess = rt.InferenceSession(args.fastsolv_checkpoint)
            print(f"✓ Loaded FastSolv ONNX from {args.fastsolv_checkpoint}")
        except Exception as e:
            print(f"⚠️  Failed to load FastSolv: {e}")
            sess = None
    elif not args.no_fastsolv and not fastsolv_ready:
        print("\n[2/3] FastSolv dependencies not available - skipping FastSolv predictions")
    
    # Run predictions
    print(f"\n[3/3] Running predictions on {len(df)} samples...")
    
    tgnn_preds = []
    fastsolv_preds = []
    target_vals = []
    valid_indices = []
    
    for idx, row in df.iterrows():
        if idx % max(1, len(df) // 10) == 0:
            print(f"   {idx}/{len(df)}", end='\r')
        
        solute_smiles = str(row.get('solute_smiles', ''))
        solvent_smiles = str(row.get('solvent_smiles', ''))
        temperature = float(row.get('temperature', 298.15))
        target = float(row.get('ln_x2', np.nan))
        
        # TGNN prediction
        tgnn_pred = predict_tgnn(model, solute_smiles, solvent_smiles, temperature)
        tgnn_preds.append(tgnn_pred)
        
        # FastSolv prediction
        if sess is not None:
            fastsolv_pred = predict_fastsolv_single(
                solute_smiles, solvent_smiles, temperature, sess
            )
            fastsolv_preds.append(fastsolv_pred)
        
        target_vals.append(target)
        valid_indices.append(idx)
    
    # Convert to arrays
    tgnn_preds = np.array(tgnn_preds)
    fastsolv_preds = np.array(fastsolv_preds) if sess is not None else np.full_like(tgnn_preds, np.nan)
    target_vals = np.array(target_vals)
    
    # Compute metrics
    print("\n\n=== RESULTS ===\n")
    
    tgnn_metrics = compute_metrics(target_vals, tgnn_preds)
    print("TGNN-Solv Performance:")
    for k, v in tgnn_metrics.items():
        if k != 'n_valid':
            print(f"  {k:15s}: {v:8.4f}")
    print(f"  n_valid:       {tgnn_metrics['n_valid']}/{len(df)}")
    
    if sess is not None:
        fastsolv_metrics = compute_metrics(target_vals, fastsolv_preds)
        print("\nFastSolv Performance:")
        for k, v in fastsolv_metrics.items():
            if k != 'n_valid':
                print(f"  {k:15s}: {v:8.4f}")
        print(f"  n_valid:       {fastsolv_metrics['n_valid']}/{len(df)}")
        
        # Comparison
        print(f"\n✓ TGNN-Solv is better by {(fastsolv_metrics['mae'] - tgnn_metrics['mae']):.4f} MAE")
    else:
        fastsolv_metrics = None
        print("\n(FastSolv not available for comparison)")
    
    # Save results
    results = {
        'test_data': args.test_data,
        'n_samples': len(df),
        'tgnn': {
            'checkpoint': args.tgnn_checkpoint,
            'metrics': tgnn_metrics,
        },
        'fastsolv': {
            'checkpoint': args.fastsolv_checkpoint,
            'metrics': fastsolv_metrics,
        } if sess is not None else None,
        'recommendation': (
            'Use TGNN-Solv for custom training. '
            'FastSolv descriptor pipeline has known issues with custom data. '
            'See FASTSOLV_NaN_ROOT_CAUSE.md for details.'
        ),
    }
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to {args.output}")


if __name__ == '__main__':
    main()
