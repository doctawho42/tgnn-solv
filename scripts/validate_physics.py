#!/usr/bin/env python3
"""Validate physical parameter quality and thermodynamic consistency."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any
import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

try:
    import torch
    from torch.utils.data import DataLoader
    from torch_geometric.data import Batch
except ImportError as exc:  # pragma: no cover - hard dependency
    print(f"ERROR: PyTorch/PyG not installed: {exc}", file=sys.stderr)
    sys.exit(1)

try:
    from scipy.stats import spearmanr
except Exception:  # pragma: no cover - optional dependency
    spearmanr = None

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import TGNNSolvDataset, collate_fn
from tgnn_solv.data.solvent_types import solvent_type_id_from_smiles
from tgnn_solv.features import (
    EDGE_FEAT_DIM,
    NODE_FEAT_DIM,
    smiles_to_descriptor_prior_features,
    smiles_to_graph,
    smiles_to_group_prior_features,
    smiles_to_morgan_fp,
)
from tgnn_solv.group_contribution import GC_FALLBACK_PRIORS, compute_gc_priors
from tgnn_solv.model import TGNNSolv


ERROR_RETURN_INTERMEDIATES = (
    "ERROR: Model does not support return_intermediates.\n"
    "This feature needs to be added to TGNNSolv.forward() in model.py.\n"
    "See docs/architecture.md for details."
)
R_GAS = 8.314


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate learned physics and thermodynamic self-consistency.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to the model checkpoint.")
    parser.add_argument("--test-data", type=str, required=True, help="Path to the test CSV file.")
    parser.add_argument(
        "--output",
        type=str,
        default="results/physics_validation.json",
        help="Path to save the validation JSON.",
    )
    parser.add_argument(
        "--n-vanthoff-pairs",
        type=int,
        default=200,
        help="Number of multi-temperature pairs for van't Hoff analysis.",
    )
    parser.add_argument(
        "--n-temp-points",
        type=int,
        default=50,
        help="Number of temperatures to evaluate per pair for van't Hoff analysis.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Requested inference device.",
    )
    return parser.parse_args()


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


def safe_float(value: object) -> float | None:
    """Convert a value to a finite float if possible."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def correlation_pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    """Compute Pearson correlation using NumPy."""
    if len(x) < 2 or len(y) < 2:
        return None
    if np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    value = float(np.corrcoef(x, y)[0, 1])
    return value if math.isfinite(value) else None


def correlation_spearman(x: np.ndarray, y: np.ndarray) -> tuple[float | None, float | None]:
    """Compute Spearman correlation if SciPy is available."""
    if spearmanr is None:
        return None, None
    if len(x) < 2 or len(y) < 2:
        return None, None
    try:
        corr, p_value = spearmanr(x, y)
    except Exception:
        return None, None
    corr_f = safe_float(corr)
    p_value_f = safe_float(p_value)
    return corr_f, p_value_f


def regression_metrics(pred: np.ndarray, true: np.ndarray) -> dict[str, Any]:
    """Compute MAE, RMSE, R2, and Pearson correlation."""
    if len(pred) == 0 or len(true) == 0:
        return {
            "mae": None,
            "rmse": None,
            "r2": None,
            "pearson": None,
            "n_samples": 0,
        }

    pred = np.asarray(pred, dtype=float)
    true = np.asarray(true, dtype=float)
    errors = pred - true
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    ss_res = float(np.sum(errors ** 2))
    ss_tot = float(np.sum((true - np.mean(true)) ** 2))
    r2 = float(1.0 - ss_res / (ss_tot + 1e-10))
    pearson = correlation_pearson(pred, true)
    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "pearson": pearson,
        "n_samples": int(len(pred)),
    }


def histogram_payload(values: np.ndarray, bins: int = 10) -> dict[str, list[float] | list[int]]:
    """Build a histogram payload for JSON export."""
    if len(values) == 0:
        return {"bins": [], "counts": []}
    counts, edges = np.histogram(values, bins=bins, range=(0.0, 1.0))
    return {
        "bins": [float(v) for v in edges.tolist()],
        "counts": [int(v) for v in counts.tolist()],
    }


def top_counts(series: pd.Series, top_n: int = 5) -> list[dict[str, Any]]:
    """Return the top-value counts for a pandas Series."""
    counts = series.astype(str).value_counts().head(top_n)
    return [
        {"value": value, "count": int(count), "fraction": float(count / len(series))}
        for value, count in counts.items()
    ]


def load_model_from_checkpoint(path: Path, device: torch.device) -> tuple[TGNNSolv, TGNNSolvConfig]:
    """Load a TGNN-Solv checkpoint saved in the repo's common formats."""
    checkpoint = torch.load(path, map_location=device, weights_only=False)

    config_data = checkpoint.get("config", {})
    if isinstance(config_data, dict):
        cfg = TGNNSolvConfig(**config_data)
    else:
        cfg = config_data

    node_feat_dim = int(checkpoint.get("node_feat_dim", NODE_FEAT_DIM))
    edge_feat_dim = int(checkpoint.get("edge_feat_dim", EDGE_FEAT_DIM))

    model = TGNNSolv(
        node_feat_dim=node_feat_dim,
        edge_feat_dim=edge_feat_dim,
        cfg=cfg,
    ).to(device)

    if "model_state" in checkpoint:
        state = checkpoint["model_state"]
    elif "model_state_dict" in checkpoint:
        state = checkpoint["model_state_dict"]
    else:
        state = checkpoint

    model_state = model.state_dict()
    compatible_state = {}
    for key, value in state.items():
        if key in model_state and tuple(model_state[key].shape) == tuple(value.shape):
            compatible_state[key] = value
    model.load_state_dict(compatible_state, strict=False)
    model.eval()
    return model, cfg


def make_test_loader(
    test_df: pd.DataFrame,
    cfg: TGNNSolvConfig,
    batch_size: int,
) -> tuple[TGNNSolvDataset, DataLoader]:
    """Create a deterministic test DataLoader."""
    dataset = TGNNSolvDataset(
        test_df,
        cache=True,
        use_morgan_features=cfg.use_morgan_features,
        morgan_radius=cfg.morgan_radius,
        morgan_n_bits=cfg.morgan_n_bits,
        use_descriptor_priors=cfg.use_descriptor_priors,
        use_group_priors=cfg.use_group_priors,
        use_gc_priors_crystal=cfg.use_gc_priors_crystal,
    )
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )
    return dataset, loader


def invoke_model(
    model: TGNNSolv,
    sol_batch: Batch,
    slv_batch: Batch,
    temperatures: torch.Tensor,
    solvent_type: torch.Tensor,
    solute_morgan_fp: torch.Tensor | None = None,
    solvent_morgan_fp: torch.Tensor | None = None,
    solute_descriptor_prior_features: torch.Tensor | None = None,
    solvent_descriptor_prior_features: torch.Tensor | None = None,
    solute_group_prior_features: torch.Tensor | None = None,
    solvent_group_prior_features: torch.Tensor | None = None,
    T_m_gc: torch.Tensor | None = None,
    dH_fus_gc: torch.Tensor | None = None,
    dCp_fus_gc: torch.Tensor | None = None,
) -> tuple[dict[str, torch.Tensor], str]:
    """Try the intermediate-aware forward call, then fall back to the standard one."""
    try:
        output = model(
            sol_batch,
            slv_batch,
            temperatures,
            solvent_type=solvent_type,
            solute_morgan_fp=solute_morgan_fp,
            solvent_morgan_fp=solvent_morgan_fp,
            solute_descriptor_prior_features=solute_descriptor_prior_features,
            solvent_descriptor_prior_features=solvent_descriptor_prior_features,
            solute_group_prior_features=solute_group_prior_features,
            solvent_group_prior_features=solvent_group_prior_features,
            T_m_gc=T_m_gc,
            dH_fus_gc=dH_fus_gc,
            dCp_fus_gc=dCp_fus_gc,
            return_intermediates=True,
        )
        if isinstance(output, tuple) and len(output) == 2 and isinstance(output[0], dict):
            return output[0], "return_intermediates"
        if isinstance(output, dict):
            return output, "return_intermediates"
    except TypeError:
        pass

    output = model(
        sol_batch,
        slv_batch,
        temperatures,
        solvent_type=solvent_type,
        solute_morgan_fp=solute_morgan_fp,
        solvent_morgan_fp=solvent_morgan_fp,
        solute_descriptor_prior_features=solute_descriptor_prior_features,
        solvent_descriptor_prior_features=solvent_descriptor_prior_features,
        solute_group_prior_features=solute_group_prior_features,
        solvent_group_prior_features=solvent_group_prior_features,
        T_m_gc=T_m_gc,
        dH_fus_gc=dH_fus_gc,
        dCp_fus_gc=dCp_fus_gc,
    )
    if isinstance(output, dict) and "physics" in output and "fusion_params" in output:
        return output, "standard_forward"

    print(ERROR_RETURN_INTERMEDIATES, file=sys.stderr)
    raise SystemExit(1)


def collect_intermediates(
    model: TGNNSolv,
    loader: DataLoader,
    dataset_df: pd.DataFrame,
    device: torch.device,
) -> tuple[pd.DataFrame, str]:
    """Run the model over the test set and collect intermediate predictions."""
    rows: list[pd.DataFrame] = []
    mode_used = "unknown"
    cursor = 0

    with torch.no_grad():
        for sol_batch, slv_batch, targets in loader:
            sol_batch = sol_batch.to(device)
            slv_batch = slv_batch.to(device)
            temperatures = targets["T"].to(device)
            solvent_type = targets.get("solvent_type")
            solute_morgan_fp = targets.get("solute_morgan_fp")
            solvent_morgan_fp = targets.get("solvent_morgan_fp")
            solute_descriptor_prior_features = targets.get(
                "solute_descriptor_prior_features"
            )
            solvent_descriptor_prior_features = targets.get(
                "solvent_descriptor_prior_features"
            )
            solute_group_prior_features = targets.get(
                "solute_group_prior_features"
            )
            solvent_group_prior_features = targets.get(
                "solvent_group_prior_features"
            )
            T_m_gc = targets.get("T_m_gc")
            dH_fus_gc = targets.get("dH_fus_gc")
            dCp_fus_gc = targets.get("dCp_fus_gc")
            if solvent_type is None:
                solvent_type = torch.zeros_like(temperatures, dtype=torch.long)
            else:
                solvent_type = solvent_type.to(device)

            output, mode_used = invoke_model(
                model=model,
                sol_batch=sol_batch,
                slv_batch=slv_batch,
                temperatures=temperatures,
                solvent_type=solvent_type,
                solute_morgan_fp=(
                    solute_morgan_fp.to(device)
                    if isinstance(solute_morgan_fp, torch.Tensor)
                    else None
                ),
                solvent_morgan_fp=(
                    solvent_morgan_fp.to(device)
                    if isinstance(solvent_morgan_fp, torch.Tensor)
                    else None
                ),
                solute_descriptor_prior_features=(
                    solute_descriptor_prior_features.to(device)
                    if isinstance(solute_descriptor_prior_features, torch.Tensor)
                    else None
                ),
                solvent_descriptor_prior_features=(
                    solvent_descriptor_prior_features.to(device)
                    if isinstance(solvent_descriptor_prior_features, torch.Tensor)
                    else None
                ),
                solute_group_prior_features=(
                    solute_group_prior_features.to(device)
                    if isinstance(solute_group_prior_features, torch.Tensor)
                    else None
                ),
                solvent_group_prior_features=(
                    solvent_group_prior_features.to(device)
                    if isinstance(solvent_group_prior_features, torch.Tensor)
                    else None
                ),
                T_m_gc=(
                    T_m_gc.to(device)
                    if isinstance(T_m_gc, torch.Tensor)
                    else None
                ),
                dH_fus_gc=(
                    dH_fus_gc.to(device)
                    if isinstance(dH_fus_gc, torch.Tensor)
                    else None
                ),
                dCp_fus_gc=(
                    dCp_fus_gc.to(device)
                    if isinstance(dCp_fus_gc, torch.Tensor)
                    else None
                ),
            )

            batch_size = int(temperatures.shape[0])
            batch_df = dataset_df.iloc[cursor:cursor + batch_size].copy().reset_index(drop=True)
            cursor += batch_size

            batch_df["T_m_pred"] = output["fusion_params"]["T_m"].detach().cpu().numpy()
            batch_df["dH_fus_pred"] = output["fusion_params"]["dH_fus"].detach().cpu().numpy()
            batch_df["dCp_fus_pred"] = output["fusion_params"]["dCp_fus"].detach().cpu().numpy()
            batch_df["gamma2_pred"] = torch.exp(output["physics"]["ln_gamma_2"]).detach().cpu().numpy()
            batch_df["correction_sigma"] = output["confidence"].detach().cpu().numpy()
            batch_df["ln_x2_physics"] = output["physics"]["ln_x2"].detach().cpu().numpy()
            batch_df["ln_x2_direct"] = output["ln_x2_direct"].detach().cpu().numpy()
            batch_df["ln_x2_final"] = output["ln_x2"].detach().cpu().numpy()
            batch_df["hansen_d_pred"] = output["hansen_sol"][:, 0].detach().cpu().numpy()
            batch_df["hansen_p_pred"] = output["hansen_sol"][:, 1].detach().cpu().numpy()
            batch_df["hansen_h_pred"] = output["hansen_sol"][:, 2].detach().cpu().numpy()
            batch_df["abs_error"] = np.abs(batch_df["ln_x2_final"] - batch_df["ln_x2"].astype(float))
            batch_df["signed_error"] = batch_df["ln_x2_final"] - batch_df["ln_x2"].astype(float)
            rows.append(batch_df)

    if not rows:
        raise ValueError("No rows were collected from the test loader.")
    return pd.concat(rows, axis=0, ignore_index=True), mode_used


def property_validation_section(df: pd.DataFrame) -> dict[str, Any]:
    """Validate predicted physical properties against available labels."""
    tm_mask = df.get("has_T_m", pd.Series(False, index=df.index)).astype(bool).to_numpy()
    dh_mask = df.get("has_dH_fus", pd.Series(False, index=df.index)).astype(bool).to_numpy()
    hansen_mask = df.get("has_hansen", pd.Series(False, index=df.index)).astype(bool).to_numpy()

    tm_metrics = regression_metrics(
        df.loc[tm_mask, "T_m_pred"].to_numpy(dtype=float),
        df.loc[tm_mask, "T_m"].to_numpy(dtype=float),
    )
    tm_metrics["frac_in_range"] = float(np.mean((df["T_m_pred"] >= 100.0) & (df["T_m_pred"] <= 700.0)))

    dh_metrics = regression_metrics(
        df.loc[dh_mask, "dH_fus_pred"].to_numpy(dtype=float),
        df.loc[dh_mask, "dH_fus"].to_numpy(dtype=float),
    )
    dh_metrics["frac_in_range"] = float(np.mean((df["dH_fus_pred"] >= 1000.0) & (df["dH_fus_pred"] <= 80000.0)))

    hansen_metrics: dict[str, Any] = {}
    component_map = {
        "hansen_d": "hansen_d_pred",
        "hansen_p": "hansen_p_pred",
        "hansen_h": "hansen_h_pred",
    }
    for target_col, pred_col in component_map.items():
        hansen_metrics[target_col] = regression_metrics(
            df.loc[hansen_mask, pred_col].to_numpy(dtype=float),
            df.loc[hansen_mask, target_col].to_numpy(dtype=float),
        )

    return {
        "T_m": tm_metrics,
        "dH_fus": dh_metrics,
        **hansen_metrics,
    }


def correction_gate_section(df: pd.DataFrame) -> dict[str, Any]:
    """Analyze how the adaptive correction gate behaves."""
    sigma = df["correction_sigma"].to_numpy(dtype=float)
    abs_error = df["abs_error"].to_numpy(dtype=float)
    rho, p_value = correlation_spearman(sigma, abs_error)

    low_sigma_df = df[df["correction_sigma"] < 0.3]
    low_sigma_payload = {
        "n_samples": int(len(low_sigma_df)),
        "fraction": float(len(low_sigma_df) / len(df)) if len(df) else None,
        "mean_temperature": safe_float(low_sigma_df["temperature"].mean()) if len(low_sigma_df) else None,
        "mean_true_ln_x2": safe_float(low_sigma_df["ln_x2"].mean()) if len(low_sigma_df) else None,
        "mean_abs_error": safe_float(low_sigma_df["abs_error"].mean()) if len(low_sigma_df) else None,
        "mean_T_m_pred": safe_float(low_sigma_df["T_m_pred"].mean()) if len(low_sigma_df) else None,
        "mean_dH_fus_pred": safe_float(low_sigma_df["dH_fus_pred"].mean()) if len(low_sigma_df) else None,
        "top_solvents": top_counts(low_sigma_df["solvent_smiles"]) if len(low_sigma_df) else [],
        "top_solutes": top_counts(low_sigma_df["solute_smiles"]) if len(low_sigma_df) else [],
    }

    return {
        "mean_sigma": safe_float(np.mean(sigma)),
        "std_sigma": safe_float(np.std(sigma, ddof=1) if len(sigma) > 1 else 0.0),
        "histogram": histogram_payload(sigma, bins=10),
        "correlation_with_error": {
            "spearman_r": rho,
            "p_value": p_value,
        },
        "low_sigma_molecules": low_sigma_payload,
    }


def predict_pair_temperatures(
    model: TGNNSolv,
    solute_smiles: str,
    solvent_smiles: str,
    temperatures: np.ndarray,
    device: torch.device,
) -> dict[str, np.ndarray]:
    """Predict one pair across a temperature grid in a single batched call."""
    sol_graph = smiles_to_graph(solute_smiles)
    slv_graph = smiles_to_graph(solvent_smiles)
    if sol_graph is None or slv_graph is None:
        raise ValueError("Invalid SMILES for van't Hoff analysis.")

    sol_batch = Batch.from_data_list([sol_graph.clone() for _ in temperatures]).to(device)
    slv_batch = Batch.from_data_list([slv_graph.clone() for _ in temperatures]).to(device)
    t_tensor = torch.tensor(temperatures, dtype=torch.float32, device=device)
    solvent_type = torch.tensor(
        [solvent_type_id_from_smiles(solvent_smiles)] * len(temperatures),
        dtype=torch.long,
        device=device,
    )
    solute_morgan_fp = None
    solvent_morgan_fp = None
    solute_descriptor_prior_features = None
    solvent_descriptor_prior_features = None
    solute_group_prior_features = None
    solvent_group_prior_features = None
    T_m_gc = None
    dH_fus_gc = None
    dCp_fus_gc = None
    if model.cfg.use_morgan_features:
        sol_fp = smiles_to_morgan_fp(
            solute_smiles,
            radius=model.cfg.morgan_radius,
            n_bits=model.cfg.morgan_n_bits,
        )
        slv_fp = smiles_to_morgan_fp(
            solvent_smiles,
            radius=model.cfg.morgan_radius,
            n_bits=model.cfg.morgan_n_bits,
        )
        if sol_fp is None or slv_fp is None:
            raise ValueError("Failed to compute Morgan fingerprints for van't Hoff analysis.")
        solute_morgan_fp = torch.tensor(sol_fp, dtype=torch.float32, device=device).repeat(len(temperatures), 1)
        solvent_morgan_fp = torch.tensor(slv_fp, dtype=torch.float32, device=device).repeat(len(temperatures), 1)
    if model.cfg.use_descriptor_priors:
        sol_desc = smiles_to_descriptor_prior_features(solute_smiles)
        slv_desc = smiles_to_descriptor_prior_features(solvent_smiles)
        if sol_desc is None or slv_desc is None:
            raise ValueError("Failed to compute descriptor priors for van't Hoff analysis.")
        solute_descriptor_prior_features = torch.tensor(
            sol_desc,
            dtype=torch.float32,
            device=device,
        ).repeat(len(temperatures), 1)
        solvent_descriptor_prior_features = torch.tensor(
            slv_desc,
            dtype=torch.float32,
            device=device,
        ).repeat(len(temperatures), 1)
    if model.cfg.use_group_priors:
        sol_group = smiles_to_group_prior_features(solute_smiles)
        slv_group = smiles_to_group_prior_features(solvent_smiles)
        if sol_group is None or slv_group is None:
            raise ValueError("Failed to compute fixed group priors for van't Hoff analysis.")
        solute_group_prior_features = torch.tensor(
            sol_group,
            dtype=torch.float32,
            device=device,
        ).repeat(len(temperatures), 1)
        solvent_group_prior_features = torch.tensor(
            slv_group,
            dtype=torch.float32,
            device=device,
        ).repeat(len(temperatures), 1)
    if model.cfg.use_gc_priors_crystal:
        gc_priors = compute_gc_priors(solute_smiles)
        if any(gc_priors[key] is None for key in ("T_m_gc", "dH_fus_gc", "dCp_fus_gc")):
            gc_priors = GC_FALLBACK_PRIORS
        T_m_gc = torch.tensor(
            [gc_priors["T_m_gc"]],
            dtype=torch.float32,
            device=device,
        ).repeat(len(temperatures))
        dH_fus_gc = torch.tensor(
            [gc_priors["dH_fus_gc"]],
            dtype=torch.float32,
            device=device,
        ).repeat(len(temperatures))
        dCp_fus_gc = torch.tensor(
            [gc_priors["dCp_fus_gc"]],
            dtype=torch.float32,
            device=device,
        ).repeat(len(temperatures))

    with torch.no_grad():
        output, _ = invoke_model(
            model=model,
            sol_batch=sol_batch,
            slv_batch=slv_batch,
            temperatures=t_tensor,
            solvent_type=solvent_type,
            solute_morgan_fp=solute_morgan_fp,
            solvent_morgan_fp=solvent_morgan_fp,
            solute_descriptor_prior_features=solute_descriptor_prior_features,
            solvent_descriptor_prior_features=solvent_descriptor_prior_features,
            solute_group_prior_features=solute_group_prior_features,
            solvent_group_prior_features=solvent_group_prior_features,
            T_m_gc=T_m_gc,
            dH_fus_gc=dH_fus_gc,
            dCp_fus_gc=dCp_fus_gc,
        )

    return {
        "ln_x2": output["ln_x2"].detach().cpu().numpy(),
        "dH_fus": output["fusion_params"]["dH_fus"].detach().cpu().numpy(),
    }


def linear_regression_stats(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Fit y = slope * x + intercept and compute R2."""
    slope, intercept = np.polyfit(x, y, deg=1)
    fitted = slope * x + intercept
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = float(1.0 - ss_res / (ss_tot + 1e-10))
    return float(slope), float(intercept), r2


def vant_hoff_section(
    model: TGNNSolv,
    df: pd.DataFrame,
    n_pairs: int,
    n_temp_points: int,
    device: torch.device,
) -> dict[str, Any]:
    """Check whether predicted solubility curves look van't Hoff-linear."""
    grouped = (
        df.groupby(["solute_smiles", "solvent_smiles"], sort=False)
        .size()
        .reset_index(name="n_obs")
    )
    eligible = grouped[grouped["n_obs"] >= 3].reset_index(drop=True)
    if eligible.empty:
        return {
            "n_pairs_analyzed": 0,
            "median_relative_deviation": None,
            "mean_vantHoff_R2": None,
            "frac_linear": None,
            "worst_5_pairs": [],
        }

    rng = np.random.RandomState(42)
    sample_n = min(int(n_pairs), len(eligible))
    selected_idx = rng.choice(len(eligible), size=sample_n, replace=False)
    selected_pairs = eligible.iloc[selected_idx].reset_index(drop=True)

    temperatures = np.linspace(250.0, 400.0, int(n_temp_points), dtype=float)
    records: list[dict[str, Any]] = []
    for row in selected_pairs.itertuples(index=False):
        try:
            predictions = predict_pair_temperatures(
                model=model,
                solute_smiles=row.solute_smiles,
                solvent_smiles=row.solvent_smiles,
                temperatures=temperatures,
                device=device,
            )
        except Exception:
            continue

        inv_t = 1.0 / temperatures
        ln_x2 = predictions["ln_x2"]
        slope, intercept, r2 = linear_regression_stats(inv_t, ln_x2)
        dH_vant_hoff = -slope * R_GAS
        dH_model = float(np.median(predictions["dH_fus"]))
        rel_dev = None
        if abs(dH_model) > 1e-8:
            rel_dev = abs(dH_vant_hoff - dH_model) / abs(dH_model)

        records.append(
            {
                "solute_smiles": row.solute_smiles,
                "solvent_smiles": row.solvent_smiles,
                "n_observed_points": int(row.n_obs),
                "dH_vantHoff": dH_vant_hoff,
                "dH_model": dH_model,
                "relative_deviation": rel_dev,
                "vantHoff_R2": r2,
                "slope": slope,
                "intercept": intercept,
            }
        )

    if not records:
        return {
            "n_pairs_analyzed": 0,
            "median_relative_deviation": None,
            "mean_vantHoff_R2": None,
            "frac_linear": None,
            "worst_5_pairs": [],
        }

    rel_dev_values = [
        float(item["relative_deviation"])
        for item in records
        if item["relative_deviation"] is not None and math.isfinite(float(item["relative_deviation"]))
    ]
    r2_values = [
        float(item["vantHoff_R2"])
        for item in records
        if item["vantHoff_R2"] is not None and math.isfinite(float(item["vantHoff_R2"]))
    ]
    worst_pairs = sorted(
        records,
        key=lambda item: float(item["relative_deviation"]) if item["relative_deviation"] is not None else -1.0,
        reverse=True,
    )[:5]

    return {
        "n_pairs_analyzed": int(len(records)),
        "median_relative_deviation": float(np.median(rel_dev_values)) if rel_dev_values else None,
        "mean_vantHoff_R2": float(np.mean(r2_values)) if r2_values else None,
        "frac_linear": float(np.mean(np.asarray(r2_values) > 0.95)) if r2_values else None,
        "worst_5_pairs": worst_pairs,
    }


def print_summary(results: dict[str, Any], mode_used: str) -> None:
    """Print a concise summary for the user."""
    prop = results["property_validation"]
    gate = results["correction_gate"]
    vant = results["vant_hoff"]

    print("=" * 72)
    print("Physics Validation Summary")
    print("=" * 72)
    print(f"Forward mode used: {mode_used}")
    print()
    print("Property validation:")
    tm_pearson = "n/a" if prop["T_m"]["pearson"] is None else f"{prop['T_m']['pearson']:.3f}"
    print(
        f"  T_m:     MAE={prop['T_m']['mae']:.2f}, "
        f"R2={prop['T_m']['r2']:.3f}, "
        f"Pearson={tm_pearson}"
        if prop["T_m"]["mae"] is not None and prop["T_m"]["r2"] is not None
        else "  T_m:     n/a"
    )
    dh_pearson = "n/a" if prop["dH_fus"]["pearson"] is None else f"{prop['dH_fus']['pearson']:.3f}"
    print(
        f"  dH_fus:  MAE={prop['dH_fus']['mae']:.1f}, "
        f"R2={prop['dH_fus']['r2']:.3f}, "
        f"Pearson={dh_pearson}"
        if prop["dH_fus"]["mae"] is not None and prop["dH_fus"]["r2"] is not None
        else "  dH_fus:  n/a"
    )
    print(
        f"  Range checks: T_m in range={100 * prop['T_m']['frac_in_range']:.1f}%, "
        f"dH_fus in range={100 * prop['dH_fus']['frac_in_range']:.1f}%"
    )
    print()
    print("Correction gate:")
    print(
        f"  mean sigma={gate['mean_sigma']:.3f}, std={gate['std_sigma']:.3f}"
        if gate["mean_sigma"] is not None and gate["std_sigma"] is not None
        else "  mean sigma=n/a"
    )
    corr = gate["correlation_with_error"]
    if corr["spearman_r"] is not None:
        p_text = "n/a" if corr["p_value"] is None else f"{corr['p_value']:.3g}"
        print(f"  Spearman(sigma, abs_error)={corr['spearman_r']:+.3f} (p={p_text})")
    else:
        print("  Spearman(sigma, abs_error)=n/a")
    print(
        f"  Low-sigma molecules (<0.3): {gate['low_sigma_molecules']['n_samples']} "
        f"({100 * gate['low_sigma_molecules']['fraction']:.1f}%)"
        if gate["low_sigma_molecules"]["fraction"] is not None
        else "  Low-sigma molecules (<0.3): n/a"
    )
    print()
    print("van't Hoff consistency:")
    print(f"  pairs analyzed={vant['n_pairs_analyzed']}")
    if vant["median_relative_deviation"] is not None:
        print(f"  median relative deviation={100 * vant['median_relative_deviation']:.1f}%")
    else:
        print("  median relative deviation=n/a")
    if vant["mean_vantHoff_R2"] is not None:
        print(
            f"  mean van't Hoff R2={vant['mean_vantHoff_R2']:.3f}, "
            f"frac linear={100 * vant['frac_linear']:.1f}%"
        )
    else:
        print("  mean van't Hoff R2=n/a")
    print("=" * 72)


def main() -> int:
    """Run the physics validation pipeline."""
    args = parse_args()

    checkpoint_path = _bootstrap.resolve_path(args.checkpoint)
    test_data_path = _bootstrap.resolve_path(args.test_data)
    output_path = _bootstrap.resolve_path(args.output)
    device = resolve_device(args.device)

    test_df = pd.read_csv(test_data_path)
    model, cfg = load_model_from_checkpoint(checkpoint_path, device=device)
    dataset, loader = make_test_loader(test_df, cfg=cfg, batch_size=cfg.batch_size)

    collected_df, mode_used = collect_intermediates(
        model=model,
        loader=loader,
        dataset_df=dataset.df,
        device=device,
    )

    if spearmanr is None:
        print("WARNING: SciPy not available; Spearman correlations will be omitted.")

    results = {
        "checkpoint": str(checkpoint_path),
        "test_data": str(test_data_path),
        "forward_mode": mode_used,
        "property_validation": property_validation_section(collected_df),
        "correction_gate": correction_gate_section(collected_df),
        "vant_hoff": vant_hoff_section(
            model=model,
            df=collected_df,
            n_pairs=args.n_vanthoff_pairs,
            n_temp_points=args.n_temp_points,
            device=device,
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print_summary(results, mode_used=mode_used)
    print(f"Saved physics validation to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
