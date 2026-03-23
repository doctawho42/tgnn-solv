#!/usr/bin/env python
"""
Analyze benchmarking results and generate visualizations.

Usage:
    python scripts/analyze_benchmark.py \
        --results benchmarks/tgnn_solv_benchmark.json \
        --output benchmarks/analysis.txt
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd


def analyze_benchmark(results_json: str, output_txt: str = None) -> str:
    """
    Analyze benchmark results and generate report.
    
    Parameters
    ----------
    results_json : str
        Path to benchmark results JSON
    output_txt : str, optional
        Where to save text report
        
    Returns
    -------
    report : str
        Analysis report as string
    """
    
    # Load results
    with open(results_json) as f:
        results = json.load(f)
    
    report_lines = []
    
    # Header
    report_lines.append("=" * 80)
    report_lines.append("BENCHMARK ANALYSIS REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Model: {results.get('model', 'Unknown')}")
    report_lines.append(f"Test Samples: {results.get('test_samples', 'Unknown')}")
    report_lines.append(f"Timestamp: {results.get('timestamp', 'Unknown')}")
    report_lines.append("")
    
    # Overall metrics
    overall = results.get('overall', {})
    report_lines.append("OVERALL PERFORMANCE")
    report_lines.append("-" * 80)
    report_lines.append(f"  Samples:        {overall.get('n', 'N/A'):>10}")
    report_lines.append(f"  MAE:            {overall.get('mae', np.nan):>10.4f}")
    report_lines.append(f"  RMSE:           {overall.get('rmse', np.nan):>10.4f}")
    report_lines.append(f"  R²:             {overall.get('r2', np.nan):>10.4f}")
    report_lines.append(f"  Bias:           {overall.get('bias', np.nan):>10.4f}")
    if overall.get('mape') is not None:
        report_lines.append(f"  MAPE:           {overall.get('mape', np.nan):>10.4f}")
    report_lines.append("")
    
    # Performance assessment
    r2 = overall.get('r2', 0)
    mae = overall.get('mae', float('inf'))
    
    if r2 > 0.8:
        assessment = "✅ Excellent - Model explains >80% of variance"
    elif r2 > 0.7:
        assessment = "✅ Good - Model explains 70-80% of variance"
    elif r2 > 0.5:
        assessment = "⚠️  Moderate - Consider improvements"
    else:
        assessment = "❌ Poor - Model needs significant improvement"
    
    report_lines.append("PERFORMANCE ASSESSMENT")
    report_lines.append("-" * 80)
    report_lines.append(f"  {assessment}")
    report_lines.append("")
    
    # By solvent type
    by_solvent = results.get('by_solvent_type', {})
    if by_solvent:
        report_lines.append("PERFORMANCE BY SOLVENT TYPE")
        report_lines.append("-" * 80)
        
        solvent_data = []
        for solvent_type, metrics in by_solvent.items():
            solvent_data.append({
                'Solvent': solvent_type,
                'N': metrics.get('n', 0),
                'MAE': metrics.get('mae', np.nan),
                'RMSE': metrics.get('rmse', np.nan),
                'R²': metrics.get('r2', np.nan),
            })
        
        if solvent_data:
            df = pd.DataFrame(solvent_data)
            report_lines.append(df.to_string(index=False))
            report_lines.append("")
        
        # Identify best/worst solvent
        best_solvent = max(by_solvent.items(), key=lambda x: x[1].get('r2', 0))
        worst_solvent = min(by_solvent.items(), key=lambda x: x[1].get('r2', float('inf')))
        
        report_lines.append(f"  Best solvent: {best_solvent[0]} (R²={best_solvent[1]['r2']:.4f})")
        report_lines.append(f"  Worst solvent: {worst_solvent[0]} (R²={worst_solvent[1]['r2']:.4f})")
        report_lines.append("")
    
    # By solubility range
    by_range = results.get('by_solubility_range', {})
    if by_range:
        report_lines.append("PERFORMANCE BY SOLUBILITY RANGE")
        report_lines.append("-" * 80)
        
        range_data = []
        for sol_range, metrics in by_range.items():
            range_data.append({
                'Range': sol_range,
                'N': metrics.get('n', 0),
                'MAE': metrics.get('mae', np.nan),
                'RMSE': metrics.get('rmse', np.nan),
                'R²': metrics.get('r2', np.nan),
            })
        
        if range_data:
            df = pd.DataFrame(range_data)
            report_lines.append(df.to_string(index=False))
            report_lines.append("")
        
        # Identify challenging ranges
        challenging = [
            (name, metrics['r2']) 
            for name, metrics in by_range.items() 
            if metrics.get('r2', 0) < 0.7
        ]
        
        if challenging:
            report_lines.append("  ⚠️  Challenging ranges:")
            for name, r2 in challenging:
                report_lines.append(f"    - {name}: R²={r2:.4f}")
            report_lines.append("")
    
    # By temperature
    by_temp = results.get('by_temperature', {})
    if by_temp:
        report_lines.append("PERFORMANCE BY TEMPERATURE")
        report_lines.append("-" * 80)
        
        temp_data = []
        for temp_range, metrics in by_temp.items():
            temp_data.append({
                'Temperature': temp_range,
                'N': metrics.get('n', 0),
                'MAE': metrics.get('mae', np.nan),
                'R²': metrics.get('r2', np.nan),
            })
        
        if temp_data:
            df = pd.DataFrame(temp_data)
            report_lines.append(df.to_string(index=False))
            report_lines.append("")
    
    # Recommendations
    report_lines.append("RECOMMENDATIONS")
    report_lines.append("-" * 80)
    
    recommendations = []
    
    if r2 < 0.7:
        recommendations.append("• Model R² is below target - consider retraining with adjusted hyperparameters")
    if mae > 0.8:
        recommendations.append("• High MAE indicates room for improvement - try ensemble methods")
    
    if by_solvent:
        worst_sol_r2 = min(m.get('r2', 0) for m in by_solvent.values())
        if worst_sol_r2 < best_solvent[1]['r2'] - 0.15:
            recommendations.append("• Large variation in solvent-type performance - investigate data imbalance")
    
    if by_range:
        for name, metrics in by_range.items():
            if metrics.get('n', 0) < 100:
                recommendations.append(f"• {name} range has few samples ({metrics['n']}) - consider stratified resampling")
    
    if not recommendations:
        recommendations.append("✅ Model performance is solid - no critical improvements needed")
    
    for rec in recommendations:
        report_lines.append(f"  {rec}")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    
    # Create report string
    report = "\n".join(report_lines)
    
    # Save if requested
    if output_txt:
        output_path = Path(output_txt)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"✓ Report saved to {output_txt}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument("--results", required=True, help="Path to benchmark results JSON")
    parser.add_argument("--output", default=None, help="Path to save text report")
    
    args = parser.parse_args()
    
    # Generate and print report
    report = analyze_benchmark(
        results_json=args.results,
        output_txt=args.output,
    )
    
    print(report)


if __name__ == "__main__":
    main()

