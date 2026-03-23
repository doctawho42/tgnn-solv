#!/usr/bin/env python
"""
Compare multiple TGNN-Solv models and generate comparison report.

Usage:
    python scripts/compare_models.py \
        --models checkpoints/v1.pt checkpoints/v2.pt checkpoints/v3.pt \
        --test-data notebooks/data/processed/test.csv \
        --output benchmarks/comparison_report.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scripts.benchmark_tgnn_solv import benchmark_model


def compare_models(
    model_paths: List[str],
    test_csv: str,
    output_json: str = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Compare multiple models and generate comparison table.
    
    Parameters
    ----------
    model_paths : list of str
        Paths to model checkpoints
    test_csv : str
        Path to test CSV file
    output_json : str, optional
        Where to save comparison results
    verbose : bool
        Whether to print detailed comparison
        
    Returns
    -------
    comparison : dict
        Comparison results for all models
    """
    
    print("=" * 80)
    print("TGNN-SOLV MODEL COMPARISON")
    print("=" * 80)
    
    results = {}
    
    # Benchmark each model
    for i, model_path in enumerate(model_paths, 1):
        model_name = Path(model_path).stem
        print(f"\n[{i}/{len(model_paths)}] Benchmarking {model_name}...")
        
        try:
            result = benchmark_model(
                model_path=model_path,
                test_csv=test_csv,
                output_json=None,
                verbose=False,
            )
            results[model_name] = result
            print(f"  ✓ Complete")
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    # Generate comparison table
    if verbose:
        print("\n" + "=" * 80)
        print("COMPARISON TABLE - OVERALL METRICS")
        print("=" * 80)
        
        # Create comparison dataframe
        comp_data = []
        for model_name, result in results.items():
            overall = result.get('overall', {})
            comp_data.append({
                'Model': model_name,
                'Samples': overall.get('n', 0),
                'MAE': overall.get('mae', np.nan),
                'RMSE': overall.get('rmse', np.nan),
                'R²': overall.get('r2', np.nan),
                'Bias': overall.get('bias', np.nan),
            })
        
        comp_df = pd.DataFrame(comp_data)
        print("\n" + comp_df.to_string(index=False))
        
        # Ranking
        print("\n" + "=" * 80)
        print("RANKINGS")
        print("=" * 80)
        
        rankings = {
            'Best MAE': comp_df.loc[comp_df['MAE'].idxmin(), 'Model'],
            'Best RMSE': comp_df.loc[comp_df['RMSE'].idxmin(), 'Model'],
            'Best R²': comp_df.loc[comp_df['R²'].idxmax(), 'Model'],
            'Lowest Bias': comp_df.loc[np.abs(comp_df['Bias']).idxmin(), 'Model'],
        }
        
        for metric, winner in rankings.items():
            print(f"  {metric}: {winner}")
        
        # Detailed breakdown by category
        print("\n" + "=" * 80)
        print("BY SOLVENT TYPE")
        print("=" * 80)
        
        for model_name, result in results.items():
            print(f"\n  {model_name}:")
            by_solvent = result.get('by_solvent_type', {})
            for solvent, metrics in by_solvent.items():
                mae = metrics.get('mae', np.nan)
                r2 = metrics.get('r2', np.nan)
                n = metrics.get('n', 0)
                print(f"    {solvent:12} MAE={mae:.4f} R²={r2:.4f} (N={n})")
    
    # Save comparison
    comparison_results = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "n_models": len(model_paths),
        "test_file": test_csv,
        "models": results,
        "summary": {
            "best_mae": min(
                (name, result['overall']['mae']) 
                for name, result in results.items()
            )[0],
            "best_r2": max(
                (name, result['overall']['r2']) 
                for name, result in results.items()
            )[0],
        }
    }
    
    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert NaN to None for JSON
        def convert_nan(obj):
            if isinstance(obj, dict):
                return {k: convert_nan(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_nan(v) for v in obj]
            elif isinstance(obj, float) and np.isnan(obj):
                return None
            return obj
        
        results_json = convert_nan(comparison_results)
        
        with open(output_path, 'w') as f:
            json.dump(results_json, f, indent=2)
        print(f"\n✓ Comparison saved to {output_json}")
    
    return comparison_results


def main():
    parser = argparse.ArgumentParser(description="Compare multiple TGNN-Solv models")
    parser.add_argument("--models", nargs='+', required=True, help="Paths to model checkpoints")
    parser.add_argument("--test-data", required=True, help="Path to test CSV file")
    parser.add_argument("--output", default=None, help="Path to save comparison results (JSON)")
    parser.add_argument("--verbose", action="store_true", default=True, help="Print detailed comparison")
    
    args = parser.parse_args()
    
    compare_models(
        model_paths=args.models,
        test_csv=args.test_data,
        output_json=args.output,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()

