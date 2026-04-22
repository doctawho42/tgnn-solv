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
from tgnn_solv.ionic_features import flag_no_melting_point, ionic_feature_summary
from tgnn_solv.inference import load_directgnn_model, load_model, predict_solubility
from tgnn_solv.reporting import build_report_payload

import torch

from run_full_budget_experiment import (
    build_loader,
    collect_tgnn_intermediates,
    regression_metrics as batch_regression_metrics,
)


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


def resolve_device(device_str: str) -> torch.device:
    """Resolve requested evaluation device with a safe fallback."""
    requested = device_str.strip().lower()
    if requested.startswith("cuda") and not torch.cuda.is_available():
        print("WARNING: CUDA requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    if requested == "mps" and not torch.backends.mps.is_available():
        print("WARNING: MPS requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    return torch.device(device_str)


def normalize_overall_metrics(metrics: dict) -> dict:
    """Expose both canonical and legacy metric names for downstream scripts."""
    normalized = dict(metrics)
    if "n" in normalized and "n_samples" not in normalized:
        normalized["n_samples"] = normalized["n"]
    for name in ("mae", "rmse", "r2"):
        if name in normalized and f"test_{name}" not in normalized:
            normalized[f"test_{name}"] = normalized[name]
    return normalized


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


def _bool_series(df: pd.DataFrame, column: str, default: bool = False) -> np.ndarray:
    """Parse a boolean dataframe column robustly."""
    if column not in df.columns:
        return np.full(len(df), default, dtype=bool)
    series = df[column]
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(default).to_numpy(dtype=bool)
    normalized = series.fillna(default).astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "yes", "y", "t"}).to_numpy(dtype=bool)


def system_class_metrics(df: pd.DataFrame, y_pred: np.ndarray) -> Dict[str, Dict]:
    """Compute metrics for ionic/no-melting applicability-domain classes."""
    if len(df) != len(y_pred):
        raise ValueError("Prediction array length must match dataframe length.")
    y_true_column = "ln_x2_true" if "ln_x2_true" in df.columns else "ln_x2"
    y_true = df[y_true_column].to_numpy(dtype=float)

    has_valid_tm = _bool_series(
        df,
        "has_valid_T_m",
        default=False,
    )
    if "has_valid_T_m" not in df.columns and "has_T_m" in df.columns:
        has_valid_tm = _bool_series(df, "has_T_m", default=False)
    has_decomposition = _bool_series(df, "has_decomposition_T", default=False)

    explicit_salt_low_eps = []
    possible_dissociation = []
    zwitterion = []
    charged = []
    curated_no_melt = []
    neutral_standard = []
    for _, row in df.iterrows():
        solute = str(row.get("solute_smiles", ""))
        solvent = str(row.get("solvent_smiles", ""))
        summary = ionic_feature_summary(solute, solvent)
        no_melt = flag_no_melting_point(solute) != "standard"
        explicit_salt_low_eps.append(summary.is_explicit_salt and summary.solvent_eps_r < 30.0)
        possible_dissociation.append(summary.n_charged_atoms > 0 and summary.solvent_eps_r > 50.0)
        zwitterion.append(summary.is_zwitterion)
        charged.append(summary.n_charged_atoms > 0)
        curated_no_melt.append(no_melt)
        neutral_standard.append(summary.n_charged_atoms == 0 and not no_melt)

    masks = {
        "with_valid_T_m": has_valid_tm,
        "without_valid_T_m": ~has_valid_tm,
        "decomposition_or_no_melt": has_decomposition | np.asarray(curated_no_melt, dtype=bool),
        "explicit_salt_low_eps": np.asarray(explicit_salt_low_eps, dtype=bool),
        "possible_dissociation_high_eps": np.asarray(possible_dissociation, dtype=bool),
        "zwitterion": np.asarray(zwitterion, dtype=bool),
        "charged_any": np.asarray(charged, dtype=bool),
        "neutral_standard": np.asarray(neutral_standard, dtype=bool),
    }

    results: Dict[str, Dict] = {}
    valid = ~(np.isnan(y_true) | np.isnan(y_pred))
    for name, mask in masks.items():
        combined = mask & valid
        if np.any(combined):
            results[name] = compute_regression_metrics(y_true[combined], y_pred[combined])
    return results


@torch.no_grad()
def collect_direct_predictions(
    model: object,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
) -> np.ndarray:
    """Collect DirectGNN predictions in loader/dataset order."""
    model.eval()
    predictions: list[np.ndarray] = []
    for sol_batch, slv_batch, targets in loader:
        sol_batch = sol_batch.to(device)
        slv_batch = slv_batch.to(device)
        targets_dev = {
            key: value.to(device) if isinstance(value, torch.Tensor) else value
            for key, value in targets.items()
        }
        output = model(
            sol_batch,
            slv_batch,
            targets_dev["T"],
            solvent_type=targets_dev.get("solvent_type"),
            solute_morgan_fp=targets_dev.get("solute_morgan_fp"),
            solvent_morgan_fp=targets_dev.get("solvent_morgan_fp"),
            solute_descriptors=targets_dev.get("solute_descriptors"),
            solvent_descriptors=targets_dev.get("solvent_descriptors"),
            ionic_features=targets_dev.get("ionic_features"),
        )
        predictions.append(output["ln_x2"].detach().cpu().numpy())
    return np.concatenate(predictions, axis=0) if predictions else np.array([], dtype=float)


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
    tm_column = "has_valid_T_m" if "has_valid_T_m" in df.columns else "has_T_m"
    if tm_column in df.columns:
        has_tm = _bool_series(df, tm_column, default=False)
        if np.any(has_tm):
            results["with_T_m"] = compute_regression_metrics(y_true[has_tm], y_pred[has_tm])
        if np.any(~has_tm):
            results["without_T_m"] = compute_regression_metrics(y_true[~has_tm], y_pred[~has_tm])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--test-data', type=str, default='notebooks/data/processed/test.csv')
    parser.add_argument('--tgnn-checkpoint', type=str, default=None)
    parser.add_argument('--directgnn-checkpoint', type=str, default=None)
    parser.add_argument('--output', type=str, default='benchmarks/complete_evaluation.json')
    parser.add_argument('--n-samples', type=int, default=None)
    parser.add_argument('--device', type=str, default='cpu')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument(
        '--intermediates-output',
        type=str,
        default=None,
        help='Optional CSV path for TGNN-Solv intermediate physics quantities.',
    )
    parser.add_argument(
        '--oracle',
        action='store_true',
        help='For TGNN-Solv, force oracle crystal-target substitution where labels exist.',
    )
    parser.add_argument(
        '--split-mode',
        type=str,
        default=None,
        help='Optional explicit split label for report metadata.',
    )
    parser.add_argument('--verbose', action='store_true')
    
    args = parser.parse_args()
    if args.tgnn_checkpoint is None and args.directgnn_checkpoint is None:
        args.tgnn_checkpoint = 'checkpoints/tgnn_solv_trained.pt'
    if args.tgnn_checkpoint is not None and args.directgnn_checkpoint is not None:
        raise ValueError("Use either --tgnn-checkpoint or --directgnn-checkpoint, not both.")
    
    print("=" * 70)
    print("COMPLETE MODEL EVALUATION")
    print("=" * 70)
    
    args.test_data = str(_bootstrap.resolve_path(args.test_data))
    if args.tgnn_checkpoint is not None:
        args.tgnn_checkpoint = str(_bootstrap.resolve_path(args.tgnn_checkpoint))
    if args.directgnn_checkpoint is not None:
        args.directgnn_checkpoint = str(_bootstrap.resolve_path(args.directgnn_checkpoint))
    args.output = str(_bootstrap.resolve_path(args.output))
    device = resolve_device(args.device)

    # Load data
    print(f"\n[1/4] Loading test data from {args.test_data}...")
    df = load_test_data(args.test_data, args.n_samples)
    n_supervised = int(solubility_supervision_mask(df).sum())
    print(f"✓ Loaded {len(df)} samples ({n_supervised} with solubility labels)")

    checkpoint_path = args.tgnn_checkpoint or args.directgnn_checkpoint
    model_family = "tgnn_solv" if args.tgnn_checkpoint is not None else "direct_gnn"

    # Load model
    print(f"\n[2/4] Loading {model_family} model from {checkpoint_path}...")
    if args.directgnn_checkpoint is not None:
        model, config = load_directgnn_model(args.directgnn_checkpoint, device=device)
    else:
        model, config = load_model(args.tgnn_checkpoint, device=device)
    print(f"✓ Model loaded (hidden_dim={config.hidden_dim}, device={device})")

    # Predict and compute metrics in the batch evaluation path. This is much
    # faster than row-by-row inference and supports DirectGNN checkpoints.
    print("\n[3/4] Running batch inference...")
    loader = build_loader(df, config, seed=args.seed)
    if args.directgnn_checkpoint is not None:
        direct_pred_all = collect_direct_predictions(model, loader, device)
        loader_df = loader.dataset.df.reset_index(drop=True)
        metric_df, metric_pred = supervised_eval_view(loader_df, direct_pred_all)
        y_true = metric_df["ln_x2"].to_numpy(dtype=float)
        valid_mask = ~(np.isnan(y_true) | np.isnan(metric_pred))
        overall_metrics = normalize_overall_metrics(
            batch_regression_metrics(metric_pred[valid_mask], y_true[valid_mask])
        )
        temp_metrics = temperature_stratified_metrics(metric_df, metric_pred)
        solubility_metrics = solubility_range_metrics(metric_df, metric_pred)
        solvent_type_metrics, by_solvent = solvent_metrics(metric_df, metric_pred)
        aux_metrics = aux_data_metrics(metric_df, metric_pred)
        system_metrics = system_class_metrics(metric_df, metric_pred)
        row_indices = (
            metric_df["row_index"].astype(int).to_numpy()
            if "row_index" in metric_df.columns
            else metric_df.index.to_numpy(dtype=int)
        )
        predictions_payload = {
            "true_ln_x2": y_true[valid_mask].tolist(),
            "pred_ln_x2": metric_pred[valid_mask].tolist(),
            "row_indices": row_indices[valid_mask].tolist(),
        }
        n_valid = int(valid_mask.sum())
    else:
        tgnn_df = collect_tgnn_intermediates(
            model,
            loader,
            device,
            force_oracle_injection=args.oracle,
        )
        if args.intermediates_output is not None:
            intermediates_path = Path(args.intermediates_output)
            intermediates_path.parent.mkdir(parents=True, exist_ok=True)
            tgnn_df.to_csv(intermediates_path, index=False)
            print(f"✓ Saved TGNN intermediates to {intermediates_path}")
        metric_df = tgnn_df.loc[tgnn_df["has_solubility"].astype(bool)].reset_index(drop=True)
        y_true = metric_df["ln_x2_true"].to_numpy(dtype=float)
        metric_pred = metric_df["ln_x2_final"].to_numpy(dtype=float)
        valid_mask = ~(np.isnan(y_true) | np.isnan(metric_pred))
        overall_metrics = normalize_overall_metrics(
            batch_regression_metrics(metric_pred[valid_mask], y_true[valid_mask])
        )
        temp_metrics = temperature_stratified_metrics(metric_df, metric_pred)
        solubility_metrics = solubility_range_metrics(metric_df, metric_pred)
        solvent_type_metrics, by_solvent = solvent_metrics(metric_df, metric_pred)
        aux_metrics = aux_data_metrics(metric_df, metric_pred)
        system_metrics = system_class_metrics(metric_df, metric_pred)
        row_indices = (
            metric_df["row_index"].astype(int).to_numpy()
            if "row_index" in metric_df.columns
            else metric_df.index.to_numpy(dtype=int)
        )
        predictions_payload = {
            "true_ln_x2": y_true[valid_mask].tolist(),
            "pred_ln_x2": metric_pred[valid_mask].tolist(),
            "row_indices": row_indices[valid_mask].tolist(),
        }
        n_valid = int(valid_mask.sum())
    print(f"✓ Got {n_valid} valid supervised predictions")

    print("\n[4/4] Computing metrics...")
    
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
    if system_metrics:
        print("\n[BY SYSTEM CLASS]")
        for class_name, metrics in system_metrics.items():
            mae = metrics.get("mae", "N/A")
            n_samples = metrics.get("n_samples", 0)
            if isinstance(mae, (int, float)):
                print(f"  {class_name}: MAE={mae:.4f} ({n_samples} samples)")
            else:
                print(f"  {class_name}: insufficient data")
    
    # Save results
    results = build_report_payload(
        "evaluation",
        metadata={
            "checkpoint": checkpoint_path,
            "model_family": model_family,
            "oracle": bool(args.oracle),
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
            "n_valid_predictions": int(n_valid),
        },
        overall=overall_metrics,
        stratified={
            "temperature": temp_metrics,
            "solubility": solubility_metrics,
            "solvent_type": solvent_type_metrics,
            "solvent": by_solvent,
            "aux_data": aux_metrics,
            "system_class": system_metrics,
        },
        predictions=predictions_payload,
    )
    
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    output_path = Path(args.output)
    manifest = build_run_manifest(
        "evaluation_report",
        model_name=Path(str(checkpoint_path)).name,
        model_family=model_family,
        inputs={
            "checkpoint": checkpoint_path,
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
