#!/usr/bin/env python
"""
Comprehensive benchmarking script for TGNN-Solv model.

Usage:
    python scripts/benchmark_tgnn_solv.py \
        --checkpoint checkpoints/tgnn_solv_trained.pt \
        --test-data notebooks/data/processed/test.csv \
        --output benchmarks/tgnn_solv_benchmark.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.model import TGNNSolv
from tgnn_solv.inference import load_model, predict_solubility
from tgnn_solv.evaluate import Evaluator
from tgnn_solv.data.dataset import TGNNSolvDataset
from tgnn_solv.data.builder import DataBuilder


def compute_benchmark_metrics(pred: np.ndarray, true: np.ndarray) -> Dict[str, float]:
    """Compute comprehensive benchmark metrics."""
    if len(pred) == 0:
        return {"n": 0, "mae": np.nan, "rmse": np.nan, "r2": np.nan, "bias": np.nan, "mape": np.nan}

    errors = pred - true
    mae = float(np.abs(errors).mean())
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    bias = float(np.mean(errors))
    
    ss_res = float(np.sum(errors ** 2))
    ss_tot = float(np.sum((true - np.mean(true)) ** 2))
    r2 = 1.0 - ss_res / (ss_tot + 1e-10)
    
    # MAPE: Mean Absolute Percentage Error
    # Convert ln(x2) to actual predictions for MAPE
    abs_pct_errors = np.abs((np.exp(pred) - np.exp(true)) / (np.exp(true) + 1e-10))
    mape = float(np.mean(abs_pct_errors[np.isfinite(abs_pct_errors)]))
    
    return {
        "n": len(pred),
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "bias": bias,
        "mape": mape,
    }


def benchmark_model(
    model_path: str,
    test_csv: str,
    output_json: str = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Benchmark TGNN-Solv model on test set.
    
    Parameters
    ----------
    model_path : str
        Path to trained model checkpoint
    test_csv : str
        Path to test CSV file
    output_json : str, optional
        Where to save results. If None, only prints
    verbose : bool
        Whether to print detailed results
        
    Returns
    -------
    benchmark_results : dict
        Comprehensive benchmark metrics
    """
    
    print("=" * 70)
    print("TGNN-SOLV BENCHMARK")
    print("=" * 70)
    
    # Load model
    print(f"\n[1/3] Loading model from {model_path}...")
    try:
        model, cfg = load_model(model_path)
        device = next(model.parameters()).device
        print(f"  ✓ Model loaded on {device}")
    except Exception as e:
        print(f"  ✗ Error loading model: {e}")
        raise
    
    # Load test data
    print(f"\n[2/3] Loading test data from {test_csv}...")
    try:
        test_df = pd.read_csv(test_csv)
        print(f"  ✓ Loaded {len(test_df)} test samples")
    except Exception as e:
        print(f"  ✗ Error loading data: {e}")
        raise
    
    # Build dataset and dataloader
    print("\n[3/3] Building dataset...")
    try:
        builder = DataBuilder()
        data_dict = builder.build_dataset_dict(test_df)
        dataset = TGNNSolvDataset(**data_dict)
        loader = DataLoader(dataset, batch_size=64, shuffle=False, num_workers=0)
        print(f"  ✓ Created dataloader with {len(loader)} batches")
    except Exception as e:
        print(f"  ✗ Error building dataset: {e}")
        raise
    
    # Run evaluation
    print("\n[4/4] Running evaluation...")
    evaluator = Evaluator(model, cfg)
    report = evaluator.evaluate(loader, test_df)
    print(f"  ✓ Evaluation complete")
    
    # Compile benchmark results
    benchmark_results = {
        "model": Path(model_path).name,
        "test_samples": len(test_df),
        "timestamp": pd.Timestamp.now().isoformat(),
        "config": {
            "hidden_dim": cfg.hidden_dim,
            "n_gnn_layers": cfg.n_gnn_layers,
            "n_cross_attn_layers": cfg.n_cross_attn_layers,
            "pair_dim": cfg.pair_dim,
            "use_implicit_diff": cfg.use_implicit_diff,
        },
        "overall": report.get("overall", {}),
        "by_solvent_type": report.get("by_solvent_type", {}),
        "by_solubility_range": report.get("by_solubility_range", {}),
        "by_temperature": report.get("by_temperature", {}),
        "by_aux_data": report.get("by_aux_data", {}),
    }
    
    # Print results
    if verbose:
        print("\n" + "=" * 70)
        print("BENCHMARK RESULTS")
        print("=" * 70)
        
        print("\n[Overall Metrics]")
        overall = benchmark_results["overall"]
        print(f"  Samples:        {overall.get('n', 0)}")
        print(f"  MAE:            {overall.get('mae', np.nan):.4f}")
        print(f"  RMSE:           {overall.get('rmse', np.nan):.4f}")
        print(f"  R²:             {overall.get('r2', np.nan):.4f}")
        print(f"  Bias:           {overall.get('bias', np.nan):.4f}")
        
        if "by_solvent_type" in benchmark_results and benchmark_results["by_solvent_type"]:
            print("\n[By Solvent Type]")
            for solvent_type, metrics in benchmark_results["by_solvent_type"].items():
                print(f"  {solvent_type}:")
                print(f"    N={metrics.get('n', 0)}, MAE={metrics.get('mae', np.nan):.4f}, R²={metrics.get('r2', np.nan):.4f}")
        
        if "by_solubility_range" in benchmark_results and benchmark_results["by_solubility_range"]:
            print("\n[By Solubility Range]")
            for sol_range, metrics in benchmark_results["by_solubility_range"].items():
                print(f"  {sol_range}:")
                print(f"    N={metrics.get('n', 0)}, MAE={metrics.get('mae', np.nan):.4f}, R²={metrics.get('r2', np.nan):.4f}")
    
    # Save results
    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert NaN to None for JSON serialization
        def convert_nan(obj):
            if isinstance(obj, dict):
                return {k: convert_nan(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_nan(v) for v in obj]
            elif isinstance(obj, float) and np.isnan(obj):
                return None
            return obj
        
        results_json = convert_nan(benchmark_results)
        
        with open(output_path, 'w') as f:
            json.dump(results_json, f, indent=2)
        print(f"\n✓ Results saved to {output_json}")
    
    return benchmark_results


def main():
    parser = argparse.ArgumentParser(description="Benchmark TGNN-Solv model")
    parser.add_argument("--checkpoint", required=True, help="Path to model checkpoint")
    parser.add_argument("--test-data", required=True, help="Path to test CSV file")
    parser.add_argument("--output", default=None, help="Path to save benchmark results (JSON)")
    parser.add_argument("--verbose", action="store_true", default=True, help="Print detailed results")
    
    args = parser.parse_args()
    
    benchmark_model(
        model_path=args.checkpoint,
        test_csv=args.test_data,
        output_json=args.output,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()

