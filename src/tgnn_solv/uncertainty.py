"""
Uncertainty estimation for TGNN-Solv predictions.

Two complementary approaches:

1. **MC-Dropout** — Enable dropout at inference time and run
   multiple forward passes.  The variance of predictions
   approximates epistemic (model) uncertainty.
   Cost: N_samples × single forward pass.  No retraining needed.

2. **Deep Ensemble** — Train K independent models (different seeds)
   and average their predictions.  Disagreement = uncertainty.
   Cost: K × full training.  Best calibration.

Usage::

    from tgnn_solv.uncertainty import MCDropoutPredictor, EnsemblePredictor

    # MC-Dropout (single model)
    mc = MCDropoutPredictor(model, n_samples=30)
    result = mc.predict("CC(=O)Nc1ccc(O)cc1", "CCO", T=298.15)
    print(result["ln_x2_mean"], result["ln_x2_std"])

    # Ensemble (multiple models)
    ens = EnsemblePredictor([model1, model2, model3])
    result = ens.predict("CC(=O)Nc1ccc(O)cc1", "CCO", T=298.15)
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch_geometric.data import Batch

from .model import TGNNSolv
from .features import (
    smiles_to_descriptor_prior_features,
    smiles_to_graph,
    smiles_to_group_prior_features,
    smiles_to_morgan_fp,
)
from .group_contribution import GC_FALLBACK_PRIORS, compute_gc_priors
from .progress import progress, trange
from .data.solvent_types import solvent_type_id_from_smiles


# ================================================================== #
#  Helpers                                                            #
# ================================================================== #

def _enable_dropout(model: nn.Module) -> None:
    """Force all Dropout layers into training mode (stochastic)."""
    for m in model.modules():
        if isinstance(m, (nn.Dropout, nn.MultiheadAttention)):
            m.train()


def _prepare_inputs(
    solute_smiles: str,
    solvent_smiles: str,
    T: float,
    device: torch.device,
) -> tuple[Batch, Batch, torch.Tensor]:
    """Build batched graph inputs for a single system."""
    sol_g = smiles_to_graph(solute_smiles)
    slv_g = smiles_to_graph(solvent_smiles)
    if sol_g is None:
        raise ValueError(f"Invalid solute SMILES: {solute_smiles}")
    if slv_g is None:
        raise ValueError(f"Invalid solvent SMILES: {solvent_smiles}")

    sol_batch = Batch.from_data_list([sol_g]).to(device)
    slv_batch = Batch.from_data_list([slv_g]).to(device)
    T_tensor = torch.tensor([T], device=device)
    return sol_batch, slv_batch, T_tensor


def _prepare_forward_kwargs(
    model: TGNNSolv,
    solute_smiles: str,
    solvent_smiles: str,
    device: torch.device,
) -> dict[str, Any]:
    """Build optional forward kwargs required by the current model config."""
    kwargs: dict[str, Any] = {
        "solvent_type": torch.tensor(
            [solvent_type_id_from_smiles(solvent_smiles)],
            device=device,
            dtype=torch.long,
        )
    }

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
            raise ValueError("Failed to compute Morgan fingerprints for uncertainty inference.")
        kwargs["solute_morgan_fp"] = torch.tensor(sol_fp, device=device).unsqueeze(0)
        kwargs["solvent_morgan_fp"] = torch.tensor(slv_fp, device=device).unsqueeze(0)

    if model.cfg.use_descriptor_priors:
        sol_desc = smiles_to_descriptor_prior_features(solute_smiles)
        slv_desc = smiles_to_descriptor_prior_features(solvent_smiles)
        if sol_desc is None or slv_desc is None:
            raise ValueError("Failed to compute descriptor priors for uncertainty inference.")
        kwargs["solute_descriptor_prior_features"] = torch.tensor(
            sol_desc,
            device=device,
        ).unsqueeze(0)
        kwargs["solvent_descriptor_prior_features"] = torch.tensor(
            slv_desc,
            device=device,
        ).unsqueeze(0)
    elif model.cfg.use_group_priors:
        sol_group = smiles_to_group_prior_features(solute_smiles)
        slv_group = smiles_to_group_prior_features(solvent_smiles)
        if sol_group is None or slv_group is None:
            raise ValueError("Failed to compute fixed group priors for uncertainty inference.")
        kwargs["solute_group_prior_features"] = torch.tensor(
            sol_group,
            device=device,
        ).unsqueeze(0)
        kwargs["solvent_group_prior_features"] = torch.tensor(
            slv_group,
            device=device,
        ).unsqueeze(0)

    if model.cfg.use_gc_priors_crystal:
        gc_priors = compute_gc_priors(solute_smiles)
        if any(gc_priors[key] is None for key in ("T_m_gc", "dH_fus_gc", "dCp_fus_gc")):
            gc_priors = GC_FALLBACK_PRIORS
        kwargs["T_m_gc"] = torch.tensor([gc_priors["T_m_gc"]], device=device)
        kwargs["dH_fus_gc"] = torch.tensor([gc_priors["dH_fus_gc"]], device=device)
        kwargs["dCp_fus_gc"] = torch.tensor([gc_priors["dCp_fus_gc"]], device=device)

    return kwargs


def _summarize_samples(samples: dict[str, list[float]]) -> dict[str, float]:
    """Compute mean, std, and confidence intervals from samples."""
    result = {}
    for key, values in samples.items():
        arr = np.array(values)
        result[f"{key}_mean"] = float(arr.mean())
        result[f"{key}_std"] = float(arr.std())
        result[f"{key}_q05"] = float(np.percentile(arr, 5))
        result[f"{key}_q95"] = float(np.percentile(arr, 95))
    return result


# ================================================================== #
#  MC-Dropout Predictor                                               #
# ================================================================== #

class MCDropoutPredictor:
    """
    Monte Carlo Dropout uncertainty estimation.

    Runs N forward passes with dropout enabled, then computes
    statistics over the predictions.

    Parameters
    ----------
    model : TGNNSolv
        Trained model (must have Dropout layers).
    n_samples : int
        Number of stochastic forward passes (default 30).
    """

    def __init__(self, model: TGNNSolv, n_samples: int = 30) -> None:
        self.model = model
        self.n_samples = n_samples
        self.device = next(model.parameters()).device

    @torch.no_grad()
    def predict(
        self,
        solute_smiles: str,
        solvent_smiles: str,
        T: float = 298.15,
    ) -> dict[str, float | int | str]:
        """
        Predict with uncertainty.

        Returns dict with:
          solute, solvent, T,
          ln_x2_mean, ln_x2_std, ln_x2_q05, ln_x2_q95,
          x2_mean, x2_std,
          gamma_2_mean, gamma_2_std,
          T_m_mean, T_m_std,
          dH_fus_mean, dH_fus_std,
          n_samples
        """
        sol_b, slv_b, T_t = _prepare_inputs(
            solute_smiles, solvent_smiles, T, self.device
        )
        forward_kwargs = _prepare_forward_kwargs(
            self.model,
            solute_smiles,
            solvent_smiles,
            self.device,
        )

        # Set model to eval, then re-enable dropout
        self.model.eval()
        _enable_dropout(self.model)

        samples = {
            "ln_x2": [],
            "x2": [],
            "gamma_2": [],
            "T_m": [],
            "dH_fus": [],
            "Phi": [],
            "ln_gamma_2": [],
            "correction": [],
        }

        for _ in trange(self.n_samples, desc="MC-dropout samples", leave=False):
            out = self.model(sol_b, slv_b, T_t, **forward_kwargs)
            samples["ln_x2"].append(out["ln_x2"].item())
            samples["x2"].append(out["x2"].item())
            samples["gamma_2"].append(
                math.exp(out["physics"]["ln_gamma_2"].item())
            )
            samples["T_m"].append(out["fusion_params"]["T_m"].item())
            samples["dH_fus"].append(out["fusion_params"]["dH_fus"].item())
            samples["Phi"].append(out["physics"]["Phi"].item())
            samples["ln_gamma_2"].append(
                out["physics"]["ln_gamma_2"].item()
            )
            samples["correction"].append(out["correction"].item())

        # Restore full eval mode
        self.model.eval()

        result = {
            "solute": solute_smiles,
            "solvent": solvent_smiles,
            "T": T,
            "n_samples": self.n_samples,
        }
        result.update(_summarize_samples(samples))
        return result

    @torch.no_grad()
    def predict_batch(
        self,
        systems: list[tuple[str, str, float]],
    ) -> pd.DataFrame:
        """
        Predict for multiple (solute, solvent, T) systems.

        Parameters
        ----------
        systems : list of (solute_smiles, solvent_smiles, T) tuples

        Returns
        -------
        DataFrame with uncertainty estimates for each system.
        """
        results = []
        for sol, slv, T in progress(
            systems, desc="MC-dropout batch", leave=False
        ):
            try:
                r = self.predict(sol, slv, T)
                results.append(r)
            except ValueError as e:
                print(f"  Skipping {sol}/{slv}: {e}")
        return pd.DataFrame(results)


# ================================================================== #
#  Deep Ensemble Predictor                                            #
# ================================================================== #

class EnsemblePredictor:
    """
    Deep Ensemble uncertainty estimation.

    Averages predictions from K independently trained models.
    Disagreement between models captures epistemic uncertainty.

    Parameters
    ----------
    models : list of TGNNSolv
        K trained models (different random seeds / data folds).
    """

    def __init__(self, models: list[TGNNSolv]) -> None:
        if len(models) < 2:
            raise ValueError("Ensemble requires ≥ 2 models")
        self.models = models
        self.device = next(models[0].parameters()).device

    @torch.no_grad()
    def predict(
        self,
        solute_smiles: str,
        solvent_smiles: str,
        T: float = 298.15,
    ) -> dict[str, float | int | str]:
        """Predict with ensemble uncertainty."""
        sol_b, slv_b, T_t = _prepare_inputs(
            solute_smiles, solvent_smiles, T, self.device
        )

        samples = {
            "ln_x2": [],
            "x2": [],
            "gamma_2": [],
            "T_m": [],
            "dH_fus": [],
            "correction": [],
        }

        for model in progress(
            self.models, desc="Ensemble models", leave=False
        ):
            model.eval()
            forward_kwargs = _prepare_forward_kwargs(
                model,
                solute_smiles,
                solvent_smiles,
                self.device,
            )
            out = model(sol_b, slv_b, T_t, **forward_kwargs)
            samples["ln_x2"].append(out["ln_x2"].item())
            samples["x2"].append(out["x2"].item())
            samples["gamma_2"].append(
                math.exp(out["physics"]["ln_gamma_2"].item())
            )
            samples["T_m"].append(out["fusion_params"]["T_m"].item())
            samples["dH_fus"].append(out["fusion_params"]["dH_fus"].item())
            samples["correction"].append(out["correction"].item())

        result = {
            "solute": solute_smiles,
            "solvent": solvent_smiles,
            "T": T,
            "n_models": len(self.models),
        }
        result.update(_summarize_samples(samples))
        return result


# ================================================================== #
#  Calibration check                                                  #
# ================================================================== #

def calibration_report(
    predictions: list[dict[str, float | int | str]],
    true_ln_x2: list[float],
) -> dict[str, float | int]:
    """
    Check if predicted confidence intervals are well-calibrated.

    A perfectly calibrated model should have ~90% of true values
    falling within the 5th–95th percentile interval.

    Parameters
    ----------
    predictions : list of dicts from MCDropoutPredictor/EnsemblePredictor
    true_ln_x2 : corresponding experimental values

    Returns
    -------
    dict with coverage_90, mean_interval_width, PICP, MPIW, RMSE, MAE
    """
    n = len(predictions)
    inside = 0
    widths = []
    errors = []

    for pred, true_val in zip(predictions, true_ln_x2):
        q05 = pred["ln_x2_q05"]
        q95 = pred["ln_x2_q95"]
        mean = pred["ln_x2_mean"]

        if q05 <= true_val <= q95:
            inside += 1
        widths.append(q95 - q05)
        errors.append(mean - true_val)

    errors = np.array(errors)
    widths = np.array(widths)

    return {
        "n_samples": n,
        "PICP_90": inside / n,                   # Prediction Interval Coverage Probability
        "MPIW": float(widths.mean()),              # Mean Prediction Interval Width
        "MAE": float(np.abs(errors).mean()),
        "RMSE": float(np.sqrt((errors ** 2).mean())),
        "sharpness": float(widths.std()),          # Lower = more consistent
    }
