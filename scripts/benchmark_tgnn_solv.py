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
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader

from tgnn_solv.data.dataset import TGNNSolvDataset, collate_fn
from tgnn_solv.data.split_registry import build_split_metadata
from tgnn_solv.evaluate import Evaluator
from tgnn_solv.inference import load_model
from tgnn_solv.reporting import build_report_payload, json_safe


def benchmark_model(
    model_path: str,
    test_csv: str,
    output_json: str = None,
    split_mode: str | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
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
    print(f"\n[1/4] Loading model from {model_path}...")
    try:
        model, cfg = load_model(model_path)
        device = next(model.parameters()).device
        print(f"  ✓ Model loaded on {device}")
    except Exception as e:
        print(f"  ✗ Error loading model: {e}")
        raise
    
    # Load test data
    print(f"\n[2/4] Loading test data from {test_csv}...")
    try:
        test_df = pd.read_csv(test_csv)
        print(f"  ✓ Loaded {len(test_df)} test samples")
    except Exception as e:
        print(f"  ✗ Error loading data: {e}")
        raise
    
    # Build dataset and dataloader
    print("\n[3/4] Building dataset...")
    try:
        dataset = TGNNSolvDataset(
            test_df,
            cache=True,
            use_morgan_features=cfg.use_morgan_features,
            morgan_radius=cfg.morgan_radius,
            morgan_n_bits=cfg.morgan_n_bits,
            use_descriptor_priors=cfg.use_descriptor_priors,
            use_group_priors=cfg.use_group_priors,
        )
        loader = DataLoader(
            dataset,
            batch_size=64,
            shuffle=False,
            num_workers=0,
            collate_fn=collate_fn,
        )
        print(f"  ✓ Created dataloader with {len(loader)} batches")
    except Exception as e:
        print(f"  ✗ Error building dataset: {e}")
        raise
    
    # Run evaluation
    print("\n[4/4] Running evaluation...")
    evaluator = Evaluator(model, cfg)
    report = evaluator.evaluate(loader, test_df)
    print("  ✓ Evaluation complete")
    
    benchmark_results = build_report_payload(
        "benchmark",
        metadata={
            "model": Path(model_path).name,
            "checkpoint": model_path,
            "test_data": test_csv,
            "split": build_split_metadata(
                split_mode=split_mode,
                test_data=test_csv,
            ),
            "test_samples": len(test_df),
            "timestamp": pd.Timestamp.now().isoformat(),
            "config": {
                "hidden_dim": cfg.hidden_dim,
                "n_gnn_layers": cfg.n_gnn_layers,
                "n_cross_attn_layers": cfg.n_cross_attn_layers,
                "pair_dim": cfg.pair_dim,
                "use_implicit_diff": cfg.use_implicit_diff,
            },
        },
        overall=report.get("overall", {}),
        stratified={
            "temperature": report.get("by_temp", {}),
            "solubility": report.get("by_range", {}),
            "solvent": report.get("by_solvent", {}),
            "aux_data": report.get("by_aux", {}),
        },
        physics_summary=report.get("physics_summary", {}),
    )
    
    # Print results
    if verbose:
        print("\n" + "=" * 70)
        print("BENCHMARK RESULTS")
        print("=" * 70)
        
        print("\n[Overall Metrics]")
        overall = benchmark_results["overall"]
        print(f"  Samples:        {overall.get('n_samples', overall.get('n', 0))}")
        print(f"  MAE:            {overall.get('mae', np.nan):.4f}")
        print(f"  RMSE:           {overall.get('rmse', np.nan):.4f}")
        print(f"  R²:             {overall.get('r2', np.nan):.4f}")
        print(f"  Bias:           {overall.get('bias', np.nan):.4f}")
        
        if "by_solvent_type" in benchmark_results and benchmark_results["by_solvent_type"]:
            print("\n[By Solvent Type]")
            for solvent_type, metrics in benchmark_results["by_solvent_type"].items():
                print(f"  {solvent_type}:")
                print(f"    N={metrics.get('n_samples', metrics.get('n', 0))}, MAE={metrics.get('mae', np.nan):.4f}, R²={metrics.get('r2', np.nan):.4f}")
        
        if "by_solubility_range" in benchmark_results and benchmark_results["by_solubility_range"]:
            print("\n[By Solubility Range]")
            for sol_range, metrics in benchmark_results["by_solubility_range"].items():
                print(f"  {sol_range}:")
                print(f"    N={metrics.get('n_samples', metrics.get('n', 0))}, MAE={metrics.get('mae', np.nan):.4f}, R²={metrics.get('r2', np.nan):.4f}")
    
    # Save results
    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        results_json = json_safe(benchmark_results)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results_json, f, indent=2)
        print(f"\n✓ Results saved to {output_json}")
    
    return benchmark_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark TGNN-Solv model")
    parser.add_argument("--checkpoint", required=True, help="Path to model checkpoint")
    parser.add_argument("--test-data", required=True, help="Path to test CSV file")
    parser.add_argument("--output", default=None, help="Path to save benchmark results (JSON)")
    parser.add_argument(
        "--split-mode",
        default=None,
        help="Optional explicit split label for report metadata.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed results")
    
    args = parser.parse_args()
    args.checkpoint = str(_bootstrap.resolve_path(args.checkpoint))
    args.test_data = str(_bootstrap.resolve_path(args.test_data))
    if args.output is not None:
        args.output = str(_bootstrap.resolve_path(args.output))
    
    benchmark_model(
        model_path=args.checkpoint,
        test_csv=args.test_data,
        output_json=args.output,
        split_mode=args.split_mode,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
