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

import math
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch_geometric.data import Batch

from .model import TGNNSolv
from .features import smiles_to_graph


# ================================================================== #
#  Helpers                                                            #
# ================================================================== #

def _enable_dropout(model: nn.Module):
    """Force all Dropout layers into training mode (stochastic)."""
    for m in model.modules():
        if isinstance(m, (nn.Dropout, nn.MultiheadAttention)):
            m.train()


def _prepare_inputs(
    solute_smiles: str,
    solvent_smiles: str,
    T: float,
    device: torch.device,
):
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


def _summarize_samples(samples: Dict[str, List[float]]) -> Dict[str, float]:
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

    def __init__(self, model: TGNNSolv, n_samples: int = 30):
        self.model = model
        self.n_samples = n_samples
        self.device = next(model.parameters()).device

    @torch.no_grad()
    def predict(
        self,
        solute_smiles: str,
        solvent_smiles: str,
        T: float = 298.15,
    ) -> Dict[str, float]:
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

        for _ in range(self.n_samples):
            out = self.model(sol_b, slv_b, T_t)
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
        systems: List[tuple],
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
        for sol, slv, T in systems:
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

    def __init__(self, models: List[TGNNSolv]):
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
    ) -> Dict[str, float]:
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

        for model in self.models:
            model.eval()
            out = model(sol_b, slv_b, T_t)
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
    predictions: List[Dict],
    true_ln_x2: List[float],
) -> Dict[str, float]:
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
