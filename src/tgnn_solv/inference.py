"""
Inference utilities for TGNN-Solv.

Functions:
  predict_solubility  — single (solute, solvent, T) prediction
  temperature_scan    — solubility vs temperature curve
  interpret_prediction — human-readable report
  save_model / load_model — checkpoint I/O
"""

import math
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Batch

from .config import TGNNSolvConfig
from .features import NODE_FEAT_DIM, EDGE_FEAT_DIM, smiles_to_graph
from .model import TGNNSolv


# ================================================================== #
#  Single prediction                                                  #
# ================================================================== #

@torch.no_grad()
def predict_solubility(
    model: TGNNSolv,
    solute_smiles: str,
    solvent_smiles: str,
    T: float = 298.15,
    device: torch.device = None,
) -> Dict:
    """
    Predict solubility for a single (solute, solvent, T) system.

    Returns a dict with all predicted quantities and intermediates.
    """
    if device is None:
        device = next(model.parameters()).device

    model.eval()

    sol_graph = smiles_to_graph(solute_smiles)
    slv_graph = smiles_to_graph(solvent_smiles)
    if sol_graph is None:
        raise ValueError(f"Cannot parse solute SMILES: {solute_smiles}")
    if slv_graph is None:
        raise ValueError(f"Cannot parse solvent SMILES: {solvent_smiles}")

    sol_batch = Batch.from_data_list([sol_graph]).to(device)
    slv_batch = Batch.from_data_list([slv_graph]).to(device)
    T_tensor = torch.tensor([T], device=device)

    output = model(sol_batch, slv_batch, T_tensor)

    return {
        "solute": solute_smiles,
        "solvent": solvent_smiles,
        "T": T,
        "x2": output["x2"].item(),
        "ln_x2": output["ln_x2"].item(),
        "x_ideal": output["physics"]["x_ideal"].item(),
        "gamma_2": math.exp(output["physics"]["ln_gamma_2"].item()),
        "ln_gamma_2": output["physics"]["ln_gamma_2"].item(),
        "Phi": output["physics"]["Phi"].item(),
        "T_m": output["fusion_params"]["T_m"].item(),
        "dH_fus": output["fusion_params"]["dH_fus"].item(),
        "dCp_fus": output["fusion_params"]["dCp_fus"].item(),
        "dg_12": output["nrtl_params"]["dg_12"].item(),
        "dg_21": output["nrtl_params"]["dg_21"].item(),
        "alpha_12": output["nrtl_params"]["alpha_12"].item(),
        "hansen_sol": output["hansen_sol"][0].tolist(),
        "hansen_slv": output["hansen_slv"][0].tolist(),
        "Ra": output["Ra"].item(),
        "correction": output["correction"].item(),
        "gate": output["gate"].item(),
    }


# ================================================================== #
#  Temperature scan                                                   #
# ================================================================== #

@torch.no_grad()
def temperature_scan(
    model: TGNNSolv,
    solute_smiles: str,
    solvent_smiles: str,
    T_min: float = 270.0,
    T_max: float = 340.0,
    n_points: int = 15,
    device: torch.device = None,
) -> pd.DataFrame:
    """
    Predict solubility at multiple temperatures.

    Returns DataFrame with columns:
      T, x2, ln_x2, x_ideal, gamma_2, correction
    """
    T_values = np.linspace(T_min, T_max, n_points)
    results = []
    for T_val in T_values:
        r = predict_solubility(
            model, solute_smiles, solvent_smiles, float(T_val), device,
        )
        results.append(r)

    df = pd.DataFrame(results)
    return df[["T", "x2", "ln_x2", "x_ideal", "gamma_2", "correction"]]


# ================================================================== #
#  Interpretation                                                     #
# ================================================================== #

def interpret_prediction(result: Dict) -> str:
    """Generate a human-readable report from a prediction dict."""
    lines = []
    lines.append("=" * 60)
    lines.append("Solubility Prediction Report")
    lines.append("=" * 60)
    lines.append(f"Solute:  {result['solute']}")
    lines.append(f"Solvent: {result['solvent']}")
    lines.append(
        f"T = {result['T']:.1f} K ({result['T'] - 273.15:.1f} °C)"
    )

    # Solubility
    lines.append("")
    lines.append("PREDICTED SOLUBILITY:")
    lines.append(f"  x₂ = {result['x2']:.5f} (mole fraction)")
    lines.append(f"  ln(x₂) = {result['ln_x2']:.3f}")
    if result["x2"] > 0.1:
        lines.append("  → High solubility (>10 mol%)")
    elif result["x2"] > 0.01:
        lines.append("  → Moderate solubility (1–10 mol%)")
    elif result["x2"] > 1e-4:
        lines.append("  → Low solubility (0.01–1 mol%)")
    else:
        lines.append("  → Very low solubility (<0.01 mol%)")

    # Decomposition
    lines.append("")
    lines.append("DECOMPOSITION:")
    lines.append("  ln(x₂) = -Φ - ln(γ₂) + correction")
    lines.append(
        f"  = {-result['Phi']:.3f} + "
        f"{-result['ln_gamma_2']:.3f} + "
        f"{result['correction']:.3f}"
    )
    total_mag = abs(result["Phi"]) + abs(result["ln_gamma_2"]) + 1e-8
    pct_ideal = abs(result["Phi"]) / total_mag * 100
    lines.append(
        f"  Crystal term (-Φ): {-result['Phi']:.3f} "
        f"({pct_ideal:.0f}% of total)"
    )
    lines.append(
        f"  Non-ideal term (-ln γ₂): {-result['ln_gamma_2']:.3f} "
        f"({100 - pct_ideal:.0f}%)"
    )
    if abs(result["correction"]) > 0.5:
        lines.append(
            f"  ⚠ Large correction ({result['correction']:.3f}) — "
            f"NRTL may be inadequate"
        )

    # Crystal properties
    lines.append("")
    lines.append("CRYSTAL PROPERTIES (solute):")
    lines.append(
        f"  T_m = {result['T_m']:.1f} K "
        f"({result['T_m'] - 273.15:.1f} °C)"
    )
    lines.append(f"  ΔH_fus = {result['dH_fus']:.0f} J/mol")
    lines.append(f"  ΔCp_fus = {result['dCp_fus']:.1f} J/(mol·K)")
    dS = result["dH_fus"] / result["T_m"]
    ok = "OK" if 20 < dS < 120 else "⚠ unusual"
    lines.append(f"  ΔS_fus = {dS:.1f} J/(mol·K) ({ok}; Walden ≈ 56.5)")

    # Activity coefficient
    lines.append("")
    lines.append("ACTIVITY COEFFICIENT:")
    lines.append(f"  γ₂ = {result['gamma_2']:.3f}")
    if result["gamma_2"] > 100:
        lines.append("  → Strong positive deviation")
    elif result["gamma_2"] > 5:
        lines.append("  → Moderate positive deviation")
    elif result["gamma_2"] > 0.5:
        lines.append("  → Near-ideal to weak positive deviation")
    else:
        lines.append("  → Negative deviation (favorable interactions)")

    # NRTL
    lines.append("")
    lines.append("NRTL PARAMETERS:")
    lines.append(f"  Δg₁₂ = {result['dg_12']:.0f} J/mol")
    lines.append(f"  Δg₂₁ = {result['dg_21']:.0f} J/mol")
    lines.append(f"  α₁₂ = {result['alpha_12']:.3f}")

    # Hansen
    h_sol = result["hansen_sol"]
    h_slv = result["hansen_slv"]
    lines.append("")
    lines.append("HANSEN PARAMETERS:")
    lines.append(
        f"  Solute:  δd={h_sol[0]:.1f}, δp={h_sol[1]:.1f}, "
        f"δh={h_sol[2]:.1f}"
    )
    lines.append(
        f"  Solvent: δd={h_slv[0]:.1f}, δp={h_slv[1]:.1f}, "
        f"δh={h_slv[2]:.1f}"
    )
    lines.append(f"  Ra = {result['Ra']:.1f} MPa^½")
    if result["Ra"] < 8:
        lines.append("  → Good match ('like dissolves like')")
    elif result["Ra"] < 15:
        lines.append("  → Moderate match")
    else:
        lines.append("  → Poor match")

    return "\n".join(lines)


# ================================================================== #
#  Model I/O                                                          #
# ================================================================== #

def save_model(
    model: TGNNSolv,
    cfg: TGNNSolvConfig,
    path: str,
    metadata: Optional[Dict] = None,
):
    """Save model checkpoint with config and metadata."""
    checkpoint = {
        "model_state": model.state_dict(),
        "config": cfg.__dict__,
        "node_feat_dim": NODE_FEAT_DIM,
        "edge_feat_dim": EDGE_FEAT_DIM,
        "metadata": metadata or {},
    }
    torch.save(checkpoint, path)
    print(f"Model saved to {path}")


def load_model(
    path: str,
    device: torch.device = None,
) -> Tuple[TGNNSolv, TGNNSolvConfig]:
    """Load model from checkpoint."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    checkpoint = torch.load(path, map_location=device, weights_only=False)
    cfg = TGNNSolvConfig(**checkpoint["config"])
    model = TGNNSolv(
        checkpoint["node_feat_dim"],
        checkpoint["edge_feat_dim"],
        cfg,
    ).to(device)
    model.load_state_dict(checkpoint["model_state"])

    print(f"Model loaded from {path}")
    if checkpoint.get("metadata"):
        for k, v in checkpoint["metadata"].items():
            print(f"  {k}: {v}")

    return model, cfg