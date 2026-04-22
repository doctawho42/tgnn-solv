#!/usr/bin/env python3
"""Export row-level predictions from a TGNN-Solv or DirectGNN checkpoint."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
from tgnn_solv.data.dataset import make_loader
from tgnn_solv.inference import load_directgnn_model, load_model


def resolve_device(raw: str) -> torch.device:
    requested = raw.strip().lower()
    if requested.startswith("cuda") and not torch.cuda.is_available():
        return torch.device("cpu")
    if requested == "mps" and not torch.backends.mps.is_available():
        return torch.device("cpu")
    return torch.device(raw)


def tensor_to_numpy(x: torch.Tensor) -> np.ndarray:
    arr = x.detach().cpu().numpy()
    if arr.ndim == 0:
        arr = arr.reshape(1)
    return arr


def numeric_vector(value: Any, n: int) -> np.ndarray | None:
    if not isinstance(value, torch.Tensor):
        return None
    arr = tensor_to_numpy(value)
    if arr.ndim == 1 and arr.shape[0] == n:
        return arr.astype(float, copy=False)
    if arr.ndim == 2 and arr.shape[0] == n and arr.shape[1] == 1:
        return arr[:, 0].astype(float, copy=False)
    return None


def build_loader(df: pd.DataFrame, cfg: Any, batch_size: int, seed: int):
    return make_loader(
        df,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        cache=True,
        drop_last=False,
        use_pair_temperature_batching=False,
        use_morgan_features=cfg.use_morgan_features,
        morgan_radius=cfg.morgan_radius,
        morgan_n_bits=cfg.morgan_n_bits,
        use_descriptor_augmentation=cfg.use_descriptor_augmentation,
        use_ionic_features=cfg.use_ionic_features,
        use_descriptor_priors=cfg.use_descriptor_priors,
        use_group_priors=cfg.requires_group_prior_features,
        use_gc_priors_crystal=cfg.use_gc_priors_crystal,
        use_gasteiger_charges=cfg.use_gasteiger_charges,
        use_phys_edge_features=cfg.use_phys_edge_features,
        explicit_h_small_molecules=cfg.explicit_h_small_molecules,
        explicit_h_max_heavy_atoms=cfg.explicit_h_max_heavy_atoms,
        use_pseudo_hansen=(
            (cfg.use_hansen_contrastive or cfg.use_hansen_delta_loss)
            and cfg.use_pseudo_hansen
        ),
        pseudo_hansen_weight_discount=cfg.pseudo_hansen_weight_discount,
        source_uncertainty_csv=(
            cfg.source_uncertainty_csv if cfg.use_source_uncertainty_weights else ""
        ),
        source_uncertainty_weight_mode=cfg.source_uncertainty_weight_mode,
        source_uncertainty_default_sigma_ln_x2=cfg.source_uncertainty_default_sigma_ln_x2,
        source_uncertainty_min_sigma_ln_x2=cfg.source_uncertainty_min_sigma_ln_x2,
        source_uncertainty_min_weight=cfg.source_uncertainty_min_weight,
        source_uncertainty_max_weight=cfg.source_uncertainty_max_weight,
        seed=seed,
    )


def forward_batch(model_type: str, model: Any, sol_b: Any, slv_b: Any, targets: dict[str, Any], device: torch.device):
    sol_b = sol_b.to(device)
    slv_b = slv_b.to(device)
    moved = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in targets.items()}
    T = moved["T"]
    common = dict(
        solvent_type=moved.get("solvent_type"),
        solute_morgan_fp=moved.get("solute_morgan_fp"),
        solvent_morgan_fp=moved.get("solvent_morgan_fp"),
        solute_descriptors=moved.get("solute_descriptors"),
        solvent_descriptors=moved.get("solvent_descriptors"),
        ionic_features=moved.get("ionic_features"),
    )
    if model_type == "direct":
        out = model(sol_b, slv_b, T, **common)
        return out, {}
    out, intermediates = model(
        sol_b,
        slv_b,
        T,
        **common,
        solute_descriptor_prior_features=moved.get("solute_descriptor_prior_features"),
        solvent_descriptor_prior_features=moved.get("solvent_descriptor_prior_features"),
        solute_group_prior_features=moved.get("solute_group_prior_features"),
        solvent_group_prior_features=moved.get("solvent_group_prior_features"),
        T_m_gc=moved.get("T_m_gc"),
        dH_fus_gc=moved.get("dH_fus_gc"),
        dCp_fus_gc=moved.get("dCp_fus_gc"),
        targets=moved,
        return_intermediates=True,
    )
    return out, intermediates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-type", choices=["tgnn", "direct"], required=True)
    parser.add_argument("--device", default="mps")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--summary", default=None)
    args = parser.parse_args()

    device = resolve_device(args.device)
    if args.model_type == "direct":
        model, cfg = load_directgnn_model(args.checkpoint, device=device)
    else:
        model, cfg = load_model(args.checkpoint, device=device)
    model.eval()

    df = pd.read_csv(args.data, low_memory=False)
    loader = build_loader(df, cfg, args.batch_size, args.seed)

    rows: list[dict[str, Any]] = []
    with torch.no_grad():
        for sol_b, slv_b, targets in loader:
            out, intermediates = forward_batch(args.model_type, model, sol_b, slv_b, targets, device)
            pred = tensor_to_numpy(out["ln_x2"]).astype(float)
            true = tensor_to_numpy(targets["ln_x2"]).astype(float)
            has = tensor_to_numpy(targets["has_solubility"]).astype(bool)
            n = len(pred)
            base_cols = {
                "solute_smiles": targets.get("solute_smiles", [""] * n),
                "solvent_smiles": targets.get("solvent_smiles", [""] * n),
                "pair_key": targets.get("pair_key", [""] * n),
                "source_detail": targets.get("source_detail", [""] * n),
                "crystal_handling": targets.get("crystal_handling", [""] * n),
            }
            numeric_targets = [
                "T", "T_m", "has_T_m", "has_valid_T_m", "has_raw_T_m",
                "has_decomposition_T", "dH_fus", "has_dH_fus", "has_valid_dH_fus",
            ]
            target_arrays = {k: numeric_vector(targets.get(k), n) for k in numeric_targets}
            inter_arrays = {
                k: numeric_vector(v, n)
                for k, v in intermediates.items()
                if k in {
                    "Phi", "Phi_intercept", "Phi_slope", "direct_phi_mask",
                    "ln_gamma_2", "ln_gamma_inf", "tau_12", "tau_21",
                    "ln_x2_physics", "ln_x2_final", "ln_x2_direct",
                    "T_m_solver", "dH_fus_solver", "dCp_fus_solver",
                    "correction_gate", "correction_magnitude",
                }
            }
            for i in range(n):
                row = {
                    "model": args.model_type,
                    "ln_x2_true": float(true[i]),
                    "ln_x2_pred": float(pred[i]),
                    "error": float(pred[i] - true[i]),
                    "abs_error": float(abs(pred[i] - true[i])),
                    "has_solubility": bool(has[i]),
                }
                for k, values in base_cols.items():
                    row[k] = values[i] if isinstance(values, list) else ""
                for k, arr in target_arrays.items():
                    if arr is not None:
                        row[k] = float(arr[i])
                for k, arr in inter_arrays.items():
                    if arr is not None:
                        row[k] = float(arr[i])
                rows.append(row)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_path, index=False)

    supervised = out_df[out_df["has_solubility"]].copy()
    err = supervised["error"].to_numpy(dtype=float)
    y = supervised["ln_x2_true"].to_numpy(dtype=float)
    pred = supervised["ln_x2_pred"].to_numpy(dtype=float)
    ss_res = float(np.square(err).sum())
    ss_tot = float(np.square(y - y.mean()).sum()) if len(y) else float("nan")
    summary = {
        "checkpoint": str(Path(args.checkpoint).resolve()),
        "data": str(Path(args.data).resolve()),
        "output": str(out_path.resolve()),
        "model_type": args.model_type,
        "device": str(device),
        "n_rows": int(len(out_df)),
        "n_supervised": int(len(supervised)),
        "mae": float(np.abs(err).mean()) if len(err) else None,
        "rmse": float(np.sqrt(np.square(err).mean())) if len(err) else None,
        "r2": float(1.0 - ss_res / (ss_tot + 1e-10)) if len(err) else None,
        "bias": float(err.mean()) if len(err) else None,
        "target_std": float(y.std(ddof=0)) if len(y) else None,
        "pred_std": float(pred.std(ddof=0)) if len(pred) else None,
        "pred_std_ratio": float(pred.std(ddof=0) / (y.std(ddof=0) + 1e-12)) if len(pred) else None,
    }
    summary_path = Path(args.summary) if args.summary else out_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
