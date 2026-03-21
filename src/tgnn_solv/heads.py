"""
Prediction heads for TGNN-Solv.

Each head maps a learned representation to physically meaningful
parameters.  Constrained activations ensure outputs stay in
valid ranges (e.g. T_m > 0, α ∈ [0.1, 0.6]).

Heads
-----
PairRepresentation     : (g_sol, g_slv) → pair vector
FusionHead             : g_solute → (T_m, ΔH_fus, ΔCp_fus)
NRTLHead               : g_pair  → (Δg12, Δg21, α12, aT12, aT21)
HansenHead             : g_mol   → (δd, δp, δh)
AuxPropsHead           : g_mol   → (V_m, ε_r, μ, n_D)
GatedResidualCorrection: (g_pair, summary) → scalar correction
"""

from typing import Dict

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import TGNNSolvConfig


# ================================================================== #
#  Pair Representation                                                #
# ================================================================== #

class PairRepresentation(nn.Module):
    """
    Build a pair vector from solute and solvent graph-level vectors.

    Input:  g_sol (B, D_r), g_slv (B, D_r)
    Output: g_pair (B, pair_dim)

    Concatenates: [g_sol, g_slv, g_sol * g_slv, |g_sol - g_slv|]
    """

    def __init__(self, readout_dim: int, pair_dim: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(readout_dim * 4, pair_dim * 2),
            nn.SiLU(),
            nn.Dropout(0.2),
            nn.Linear(pair_dim * 2, pair_dim),
            nn.SiLU(),
            nn.Dropout(0.1),
        )

    def forward(self, g_sol: torch.Tensor, g_slv: torch.Tensor) -> torch.Tensor:
        pair_input = torch.cat(
            [g_sol, g_slv, g_sol * g_slv, (g_sol - g_slv).abs()],
            dim=-1,
        )
        return self.mlp(pair_input)


class SolventTypeMoE(nn.Module):
    """
    Mixture-of-Experts conditioned on solvent type.

    Uses a type embedding + gating MLP to mix expert transformations
    of the pair representation. Residual-scaled for safety.
    """

    def __init__(
        self,
        input_dim: int,
        num_types: int,
        num_experts: int = 4,
        type_emb_dim: int = 16,
        hidden_dim: int = 128,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.type_embed = nn.Embedding(num_types, type_emb_dim)
        self.gate = nn.Sequential(
            nn.Linear(input_dim + type_emb_dim, hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_experts),
        )
        self.experts = nn.ModuleList([
            nn.Sequential(
                nn.Linear(input_dim, input_dim),
                nn.SiLU(),
                nn.Dropout(dropout),
                nn.Linear(input_dim, input_dim),
            )
            for _ in range(num_experts)
        ])
        self.res_scale = nn.Parameter(torch.tensor(0.0))

    def forward(
        self, g_pair: torch.Tensor, solvent_type: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        type_ids = solvent_type.long().view(-1)
        type_emb = self.type_embed(type_ids)
        gate_logits = self.gate(torch.cat([g_pair, type_emb], dim=-1))
        gate = torch.softmax(gate_logits, dim=-1)
        expert_out = torch.stack(
            [expert(g_pair) for expert in self.experts], dim=1
        )  # (B, E, D)
        mixed = torch.sum(gate.unsqueeze(-1) * expert_out, dim=1)
        scale = torch.tanh(self.res_scale)
        return g_pair + scale * mixed, gate


# ================================================================== #
#  Fusion Head — crystal properties of the solute                     #
# ================================================================== #

class FusionHead(nn.Module):
    """
    Predict melting point and fusion thermodynamics from solute vector.

    Outputs (all per-sample):
      T_m     : melting temperature [K], sigmoid-bounded [T_m_min, T_m_max]
      dH_fus  : enthalpy of fusion [J/mol], softplus-bounded > 0
      dCp_fus : heat capacity change [J/(mol·K)], unbounded
    """

    def __init__(self, input_dim: int, cfg: TGNNSolvConfig):
        super().__init__()
        self.cfg = cfg
        self.mlp = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.SiLU(),
            nn.Linear(256, 128),
            nn.SiLU(),
            nn.Linear(128, 3),
        )

    def forward(self, g_solute: torch.Tensor) -> Dict[str, torch.Tensor]:
        z = self.mlp(g_solute)  # (B, 3)
        T_m = self.cfg.T_m_min + (
            (self.cfg.T_m_max - self.cfg.T_m_min) * torch.sigmoid(z[:, 0])
        )
        dH_fus = F.softplus(z[:, 1]) * self.cfg.S_H
        dCp_fus = z[:, 2] * self.cfg.S_Cp
        return {"T_m": T_m, "dH_fus": dH_fus, "dCp_fus": dCp_fus}


# ================================================================== #
#  NRTL Head — binary interaction parameters                          #
# ================================================================== #

class NRTLHead(nn.Module):
    """
    Predict NRTL parameters from the pair representation.

    Outputs:
      If cfg.nrtl_tau_mode == "abc":
        tau_a12, tau_b12, tau_c12 : tau(T) coefficients for 1->2
        tau_a21, tau_b21, tau_c21 : tau(T) coefficients for 2->1
        alpha_12                  : non-randomness, sigmoid-bounded [α_min, α_max]
      If cfg.nrtl_tau_mode == "legacy":
        dg_12, dg_21 : energy parameters [J/mol]
        alpha_12     : non-randomness, sigmoid-bounded [α_min, α_max]
        a_T12, a_T21 : temperature-dependence coefficients

    Initialization:
      - tau outputs zero-initialized → near-ideal starting point
      - alpha bias set to give α ≈ 0.3 at init
    """

    def __init__(self, input_dim: int, cfg: TGNNSolvConfig):
        super().__init__()
        self.cfg = cfg

        self.backbone = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.SiLU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(512, 256),
            nn.SiLU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(256, 128),
            nn.SiLU(),
            nn.Dropout(cfg.dropout),
        )
        self.output = nn.Linear(128, 7)

        # Careful initialization: start near ideal (γ ≈ 1)
        with torch.no_grad():
            self.output.weight.zero_()
            self.output.bias.zero_()
            if cfg.nrtl_tau_mode == "legacy":
                self.output.bias[2] = -0.405   # alpha index in legacy mode
            else:
                self.output.bias[6] = -0.405   # alpha index in abc mode

    def forward(self, g_pair: torch.Tensor) -> Dict[str, torch.Tensor]:
        h = self.backbone(g_pair)
        z = self.output(h)  # (B, 7)

        if self.cfg.nrtl_tau_mode == "legacy":
            dg_12 = z[:, 0] * self.cfg.S_g
            dg_21 = z[:, 1] * self.cfg.S_g
            alpha_12 = self.cfg.alpha_min + (
                (self.cfg.alpha_max - self.cfg.alpha_min)
                * torch.sigmoid(z[:, 2])
            )
            a_T12 = z[:, 3] * self.cfg.S_aT
            a_T21 = z[:, 4] * self.cfg.S_aT
            return {
                "dg_12": dg_12,
                "dg_21": dg_21,
                "alpha_12": alpha_12,
                "a_T12": a_T12,
                "a_T21": a_T21,
            }

        tau_a12 = z[:, 0] * self.cfg.S_tau_a
        tau_b12 = z[:, 1] * self.cfg.S_tau_b
        tau_c12 = z[:, 2] * self.cfg.S_tau_c
        tau_a21 = z[:, 3] * self.cfg.S_tau_a
        tau_b21 = z[:, 4] * self.cfg.S_tau_b
        tau_c21 = z[:, 5] * self.cfg.S_tau_c
        alpha_12 = self.cfg.alpha_min + (
            (self.cfg.alpha_max - self.cfg.alpha_min)
            * torch.sigmoid(z[:, 6])
        )

        return {
            "tau_a12": tau_a12,
            "tau_b12": tau_b12,
            "tau_c12": tau_c12,
            "tau_a21": tau_a21,
            "tau_b21": tau_b21,
            "tau_c21": tau_c21,
            "alpha_12": alpha_12,
        }


# ================================================================== #
#  Hansen Head — solubility parameters                                #
# ================================================================== #

class HansenHead(nn.Module):
    """
    Predict Hansen solubility parameters (δd, δp, δh) in MPa^0.5.

    All three are non-negative → softplus activation.
    """

    def __init__(self, input_dim: int, cfg: TGNNSolvConfig):
        super().__init__()
        self.cfg = cfg
        self.mlp = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.SiLU(),
            nn.Linear(128, 3),
        )

    def forward(self, g_mol: torch.Tensor) -> torch.Tensor:
        z = self.mlp(g_mol)
        return F.softplus(z) * self.cfg.S_delta  # (B, 3)


# ================================================================== #
#  Auxiliary Properties Head                                          #
# ================================================================== #

class AuxPropsHead(nn.Module):
    """
    Predict auxiliary molecular properties.

    V_m   : molar volume [cm³/mol], softplus → (30, +∞)
    eps_r : relative permittivity, softplus → (1, +∞)
    mu    : dipole moment [Debye], softplus → (0, +∞)
    n_D   : refractive index, sigmoid → (1.0, 1.8)
    """

    def __init__(self, input_dim: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.SiLU(),
            nn.Linear(128, 4),
        )

    def forward(self, g_mol: torch.Tensor) -> Dict[str, torch.Tensor]:
        z = self.mlp(g_mol)
        V_m = F.softplus(z[:, 0]) * 50.0 + 30.0
        eps_r = 1.0 + F.softplus(z[:, 1]) * 10.0
        mu = F.softplus(z[:, 2]) * 2.0
        n_D = 1.0 + 0.8 * torch.sigmoid(z[:, 3])
        return {"V_m": V_m, "eps_r": eps_r, "mu": mu, "n_D": n_D}


class AdaptivePhysicsCorrection(nn.Module):
    """
    Adaptive correction that learns when physics is unreliable.

    Instead of a single scalar gate, predicts a per-sample
    mixing weight between physics prediction and learned correction.

    ln(x₂) = σ(w) · ln(x₂)_physics + (1 - σ(w)) · ln(x₂)_learned

    When the model is confident in physics (familiar molecule),
    σ(w) → 1 and physics dominates.
    When physics is unreliable (novel scaffold, unusual T_m),
    σ(w) → 0 and the learned path dominates.

    Initialized so that σ(w) ≈ 0.9 (physics-first).
    """

    def __init__(self, pair_dim: int, n_param_features: int = 6):
        super().__init__()

        # Confidence network: estimates how reliable physics is
        self.confidence_net = nn.Sequential(
            nn.Linear(pair_dim + n_param_features, 128),
            nn.SiLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.SiLU(),
            nn.Linear(64, 1),
        )

        # Direct prediction path (bypass physics): mean + log_sigma
        self.direct_net = nn.Sequential(
            nn.Linear(pair_dim + n_param_features, 128),
            nn.SiLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.SiLU(),
            nn.Linear(64, 2),
        )

        # Initialize confidence bias high → σ(2.2) ≈ 0.9
        with torch.no_grad():
            self.confidence_net[-1].bias.fill_(2.2)

    def forward(
        self, g_pair: torch.Tensor, param_summary: torch.Tensor,
        ln_x2_physics: torch.Tensor,
    ) -> tuple:
        """
        Returns
        -------
        ln_x2_final : (B,) blended prediction
        confidence  : (B,) physics confidence σ(w)
        ln_x2_direct : (B,) direct (non-physics) prediction (mean)
        ln_x2_direct_log_sigma : (B,) log sigma for direct path
        """
        inp = torch.cat([g_pair, param_summary], dim=-1)

        # Physics confidence: how much to trust SLE output
        confidence = torch.sigmoid(
            self.confidence_net(inp).squeeze(-1)
        )  # (B,) in [0, 1]

        # Direct prediction path
        direct_out = self.direct_net(inp)
        ln_x2_direct = direct_out[:, 0]
        ln_x2_direct_log_sigma = direct_out[:, 1].clamp(-6.0, 2.0)

        # Blend
        ln_x2_final = (
            confidence * ln_x2_physics
            + (1.0 - confidence) * ln_x2_direct
        )

        return (
            ln_x2_final,
            confidence,
            ln_x2_direct,
            ln_x2_direct_log_sigma,
        )
