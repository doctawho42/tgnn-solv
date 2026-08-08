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

import _bootstrap  # noqa: E402, F401
from tgnn_solv.data.dataset import make_loader  # noqa: E402
from tgnn_solv.device import default_device, resolve_device  # noqa: E402
from tgnn_solv.inference import load_directgnn_model, load_model  # noqa: E402
from tgnn_solv.sigma_oracle import build_oracle_tensors, load_sigma_profiles  # noqa: E402


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


def forward_batch(model_type: str, model: Any, sol_b: Any, slv_b: Any, targets: dict[str, Any], device: torch.device, *, force_sigma_oracle: bool = False):
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
        force_oracle_injection=targets.get("__force_oracle_injection__", False),
        force_sigma_oracle=force_sigma_oracle,
    )
    return out, intermediates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model-type", choices=["tgnn", "direct"], required=True)
    parser.add_argument(
        "--device",
        default=default_device(prefer_mps=True),
        help=(
            "Requested device; defaults to whichever this box has. Every experiment "
            "driver passes its own DEVICE here, and e5's oracle arm is export-only -- "
            "it has no train step in front of it to notice a missing GPU."
        ),
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--summary", default=None)
    parser.add_argument(
        "--oracle",
        action="store_true",
        help="For TGNN-Solv, force oracle crystal-target substitution where labels exist.",
    )
    parser.add_argument(
        "--sigma-oracle",
        action="store_true",
        help="For cosmo_sac TGNN-Solv, inject ground-truth sigma profiles where available.",
    )
    parser.add_argument(
        "--sigma-oracle-side",
        choices=["solute", "solvent", "both"],
        default="solute",
        help="Which molecule role to inject oracle sigma profiles for (default: solute).",
    )
    parser.add_argument(
        "--sigma-artifact",
        default="results/sigma_profile_artifact/sigma_profiles.csv",
        help="Path to the sigma-profile CSV artifact (default: results/sigma_profile_artifact/sigma_profiles.csv).",
    )
    args = parser.parse_args()

    device = resolve_device(args.device)
    if args.model_type == "direct":
        model, cfg = load_directgnn_model(args.checkpoint, device=device)
    else:
        model, cfg = load_model(args.checkpoint, device=device)
    model.eval()

    df = pd.read_csv(args.data, low_memory=False)
    loader = build_loader(df, cfg, args.batch_size, args.seed)

    sigma_table: dict | None = None
    sigma_n_bins = getattr(cfg, "cosmo_sac_n_bins", 51)
    if args.sigma_oracle:
        sigma_table = load_sigma_profiles(args.sigma_artifact, n_bins=sigma_n_bins)

    rows: list[dict[str, Any]] = []
    with torch.no_grad():
        for sol_b, slv_b, targets in loader:
            if args.oracle:
                targets["__force_oracle_injection__"] = True
            _apply_sigma_oracle = False
            mask_solute: torch.Tensor | None = None
            mask_solvent: torch.Tensor | None = None
            if sigma_table is not None:
                side = args.sigma_oracle_side
                n_bins = sigma_n_bins
                if side in {"solute", "both"}:
                    p_sol, a_sol, mask_solute = build_oracle_tensors(
                        targets["solute_smiles"], sigma_table, n_bins=n_bins
                    )
                    targets["sigma_oracle_p_solute"] = p_sol
                    targets["sigma_oracle_area_solute"] = a_sol
                    targets["sigma_oracle_mask_solute"] = mask_solute
                if side in {"solvent", "both"}:
                    p_slv, a_slv, mask_solvent = build_oracle_tensors(
                        targets["solvent_smiles"], sigma_table, n_bins=n_bins
                    )
                    targets["sigma_oracle_p_solvent"] = p_slv
                    targets["sigma_oracle_area_solvent"] = a_slv
                    targets["sigma_oracle_mask_solvent"] = mask_solvent
                targets["__force_sigma_oracle__"] = True
                _apply_sigma_oracle = True
            out, intermediates = forward_batch(
                args.model_type, model, sol_b, slv_b, targets, device,
                force_sigma_oracle=_apply_sigma_oracle,
            )
            # Extract per-row ln γ₂ (cosmo_sac only; NaN for direct)
            gamma: np.ndarray | None = None
            if isinstance(out, dict) and "physics" in out:
                _phys = out["physics"]
                if isinstance(_phys, dict):
                    _g = _phys.get("ln_gamma_2")
                    if _g is not None:
                        gamma = _g.detach().cpu().numpy()
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
                    "T_m_corrected", "dH_fus_corrected", "dCp_fus_corrected",
                    "tau_12_corrected", "tau_21_corrected",
                    "ln_gamma_2_corrected", "ln_gamma_inf_corrected",
                    "correction_gate", "correction_magnitude",
                    "correction_raw_residual",
                    "delta_T_m", "delta_dH_fraction",
                    "delta_tau_12", "delta_tau_21",
                }
            }
            # Determine per-batch oracle_applied mask for sigma oracle
            _oracle_mask_np: np.ndarray | None = None
            if _apply_sigma_oracle:
                side = args.sigma_oracle_side
                if side == "solute" and mask_solute is not None:
                    _oracle_mask_np = mask_solute.numpy()
                elif side == "solvent" and mask_solvent is not None:
                    _oracle_mask_np = mask_solvent.numpy()
                elif side == "both":
                    # row is "applied" when either molecule was matched
                    _m = None
                    if mask_solute is not None:
                        _m = mask_solute
                    if mask_solvent is not None:
                        _m = _m | mask_solvent if _m is not None else mask_solvent
                    if _m is not None:
                        _oracle_mask_np = _m.numpy()

            for i in range(n):
                row = {
                    "model": args.model_type,
                    "ln_x2_true": float(true[i]),
                    "ln_x2_pred": float(pred[i]),
                    "error": float(pred[i] - true[i]),
                    "abs_error": float(abs(pred[i] - true[i])),
                    "has_solubility": bool(has[i]),
                    "ln_gamma2_pred": float(gamma[i]) if gamma is not None else float("nan"),
                    "sigma_oracle_applied": bool(_oracle_mask_np[i]) if _oracle_mask_np is not None else False,
                    "sigma_oracle_mask_solute": bool(mask_solute[i]) if mask_solute is not None else False,
                    "sigma_oracle_mask_solvent": bool(mask_solvent[i]) if mask_solvent is not None else False,
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
    if args.sigma_oracle:
        oracle_subset = out_df[out_df["sigma_oracle_applied"] & out_df["has_solubility"]].copy()
        n_oracle = int(len(oracle_subset))
        if n_oracle > 0:
            o_err = oracle_subset["error"].to_numpy(dtype=float)
            oracle_metrics: dict[str, Any] = {
                "n_oracle": n_oracle,
                "mae": float(np.abs(o_err).mean()),
                "rmse": float(np.sqrt(np.square(o_err).mean())),
                "bias": float(o_err.mean()),
            }
        else:
            oracle_metrics = {"n_oracle": 0, "mae": None, "rmse": None, "bias": None}
        summary["sigma_oracle"] = oracle_metrics

    summary_path = Path(args.summary) if args.summary else out_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
