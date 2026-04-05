#!/usr/bin/env python
"""
Lightweight evaluation pipeline for TGNN-Solv checkpoints.

This script runs:
1. Inference on a CSV test set
2. Standard regression metrics
3. Temperature-stratified metrics
4. Solubility-range-stratified metrics
5. JSON export for downstream reporting and plotting

Usage:
  python scripts/evaluate_complete.py \
      --test-data notebooks/data/processed/test.csv \
      --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
      --output benchmarks/complete_evaluation.json \
      --verbose

Based on: AGENTS.md, BENCHMARKING_GUIDE.md
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Dict

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

if importlib.util.find_spec("torch") is None:
    print("ERROR: PyTorch not installed")
    sys.exit(1)

from tgnn_solv.data.utils import canonicalize
from tgnn_solv.data.split_registry import build_split_metadata
from tgnn_solv.artifacts import build_benchmark_card, build_run_manifest, write_json
from tgnn_solv.inference import load_model, predict_solubility
from tgnn_solv.reporting import build_report_payload


def load_test_data(csv_path: str, n_samples: int = None) -> pd.DataFrame:
    """Load test CSV."""
    df = pd.read_csv(csv_path).reset_index().rename(columns={"index": "row_index"})
    if n_samples and len(df) > n_samples:
        df = df.sample(n_samples, random_state=42).reset_index(drop=True)
    return df


def solubility_supervision_mask(df: pd.DataFrame) -> np.ndarray:
    """Return the rows that carry experimental solubility supervision.

    Canonical training/evaluation only scores rows with `has_solubility=True`.
    Auxiliary-only rows may still be present in the CSV and can carry placeholder
    `ln_x2` values, so lightweight evaluation must apply the same mask.
    """
    if "has_solubility" not in df.columns:
        return np.ones(len(df), dtype=bool)

    series = df["has_solubility"]
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).to_numpy(dtype=bool)

    normalized = series.fillna(False).astype(str).str.strip().str.lower()
    true_values = {"true", "1", "yes", "y", "t"}
    return normalized.isin(true_values).to_numpy(dtype=bool)


def supervised_eval_view(
    df: pd.DataFrame,
    y_pred: np.ndarray,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Filter a `(df, predictions)` pair down to supervised solubility rows."""
    if len(df) != len(y_pred):
        raise ValueError("Prediction array length must match dataframe length.")
    mask = solubility_supervision_mask(df)
    return df.loc[mask].reset_index(drop=True), y_pred[mask]


def predict_batch(
    model: object,
    df_batch: pd.DataFrame,
    verbose: bool = False,
) -> np.ndarray:
    """Predict ln(x2) for a batch."""
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
        
        except Exception:
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


def solvent_metrics(df: pd.DataFrame, y_pred: np.ndarray) -> tuple[Dict[str, Dict], Dict[str, Dict]]:
    """Compute solvent-type and top-solvent metrics."""
    y_true = df["ln_x2"].values
    solvent_smiles = df["solvent_smiles"].astype(str)
    water_smiles = canonicalize("O")

    by_solvent_type: Dict[str, Dict] = {}
    water_mask = solvent_smiles == water_smiles
    organic_mask = ~water_mask
    if np.any(water_mask):
        by_solvent_type["water"] = compute_regression_metrics(y_true[water_mask], y_pred[water_mask])
    if np.any(organic_mask):
        by_solvent_type["organic"] = compute_regression_metrics(y_true[organic_mask], y_pred[organic_mask])

    by_solvent: Dict[str, Dict] = {}
    top_solvents = solvent_smiles.value_counts().head(5)
    for smi in top_solvents.index:
        mask = solvent_smiles == smi
        if np.any(mask):
            by_solvent[str(smi)] = compute_regression_metrics(y_true[mask], y_pred[mask])

    return by_solvent_type, by_solvent


def aux_data_metrics(df: pd.DataFrame, y_pred: np.ndarray) -> Dict[str, Dict]:
    """Compute metrics stratified by auxiliary-label availability."""
    y_true = df["ln_x2"].values
    results: Dict[str, Dict] = {}
    if "has_T_m" in df.columns:
        has_tm = df["has_T_m"].fillna(False).astype(bool).values
        if np.any(has_tm):
            results["with_T_m"] = compute_regression_metrics(y_true[has_tm], y_pred[has_tm])
        if np.any(~has_tm):
            results["without_T_m"] = compute_regression_metrics(y_true[~has_tm], y_pred[~has_tm])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-data', type=str, default='notebooks/data/processed/test.csv')
    parser.add_argument('--tgnn-checkpoint', type=str, default='checkpoints/tgnn_solv_trained.pt')
    parser.add_argument('--output', type=str, default='benchmarks/complete_evaluation.json')
    parser.add_argument('--n-samples', type=int, default=None)
    parser.add_argument(
        '--split-mode',
        type=str,
        default=None,
        help='Optional explicit split label for report metadata.',
    )
    parser.add_argument('--verbose', action='store_true')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("COMPLETE TGNN-Solv EVALUATION")
    print("=" * 70)
    
    args.test_data = str(_bootstrap.resolve_path(args.test_data))
    args.tgnn_checkpoint = str(_bootstrap.resolve_path(args.tgnn_checkpoint))
    args.output = str(_bootstrap.resolve_path(args.output))

    # Load data
    print(f"\n[1/4] Loading test data from {args.test_data}...")
    df = load_test_data(args.test_data, args.n_samples)
    n_supervised = int(solubility_supervision_mask(df).sum())
    print(f"✓ Loaded {len(df)} samples ({n_supervised} with solubility labels)")
    
    # Load model
    print(f"\n[2/4] Loading model from {args.tgnn_checkpoint}...")
    model, config = load_model(args.tgnn_checkpoint)
    print(f"✓ Model loaded (hidden_dim={config.hidden_dim})")
    
    # Predict
    print("\n[3/4] Running inference...")
    y_pred = predict_batch(model, df, verbose=args.verbose)
    n_valid = np.sum(~np.isnan(y_pred))
    print(f"✓ Got {n_valid}/{len(df)} valid predictions")
    
    # Compute metrics
    print("\n[4/4] Computing metrics...")
    
    metric_df, metric_pred = supervised_eval_view(df, y_pred)
    y_true = metric_df['ln_x2'].values
    overall_metrics = compute_regression_metrics(y_true, metric_pred)
    temp_metrics = temperature_stratified_metrics(metric_df, metric_pred)
    solubility_metrics = solubility_range_metrics(metric_df, metric_pred)
    solvent_type_metrics, by_solvent = solvent_metrics(metric_df, metric_pred)
    aux_metrics = aux_data_metrics(metric_df, metric_pred)
    
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
            print("    Insufficient data")
    
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
            print("    Insufficient data")
    
    # Save results
    valid_mask = ~(np.isnan(y_true) | np.isnan(metric_pred))

    results = build_report_payload(
        "evaluation",
        metadata={
            "checkpoint": args.tgnn_checkpoint,
            "test_data": args.test_data,
            "sample_random_state": 42 if args.n_samples else None,
            "split": build_split_metadata(
                split_mode=args.split_mode,
                test_data=args.test_data,
            ),
            "config": {
                "hidden_dim": config.hidden_dim,
                "n_gnn_layers": config.n_gnn_layers,
                "n_cross_attn_layers": config.n_cross_attn_layers,
                "use_implicit_diff": config.use_implicit_diff,
            },
            "test_samples": int(len(df)),
            "supervised_test_samples": int(len(metric_df)),
            "n_model_predictions": int(n_valid),
            "n_valid_predictions": int(valid_mask.sum()),
        },
        overall=overall_metrics,
        stratified={
            "temperature": temp_metrics,
            "solubility": solubility_metrics,
            "solvent_type": solvent_type_metrics,
            "solvent": by_solvent,
            "aux_data": aux_metrics,
        },
        predictions={
            "true_ln_x2": y_true[valid_mask].tolist(),
            "pred_ln_x2": metric_pred[valid_mask].tolist(),
            "row_indices": metric_df.loc[valid_mask, "row_index"].astype(int).tolist(),
        },
    )
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    output_path = Path(args.output)
    manifest = build_run_manifest(
        "evaluation_report",
        model_name=Path(str(args.tgnn_checkpoint)).name,
        model_family="tgnn_solv",
        inputs={
            "checkpoint": args.tgnn_checkpoint,
            "test_data": args.test_data,
        },
        outputs={"report": output_path},
        metadata={"split": results.get("split")},
    )
    card = build_benchmark_card(
        results,
        metadata={"model_family": "tgnn_solv"},
    )
    write_json(output_path.with_suffix(".manifest.json"), manifest)
    write_json(output_path.with_suffix(".card.json"), card)
    
    print(f"\n✓ Results saved to {args.output}")
    print("=" * 70)


if __name__ == '__main__':
    main()
