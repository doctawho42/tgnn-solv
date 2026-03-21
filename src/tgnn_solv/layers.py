"""
Neural network layers for TGNN-Solv.

Contains:
  - MPNNLayer        : Message-passing with edge features and attention
  - GNNEncoder       : Multi-layer MPNN with solute/solvent role adapters
  - SoluteSolventCrossAttention : Cross-attention between solute and solvent
  - BipartiteMessagePassing : Bipartite message passing alternative
  - AttentionPooling : Learnable attention-based graph readout
  - PhysicsAwareReadout : Multi-strategy pooling (attention + Set2Set)
  - IdealSolubilityLayer : Hardcoded Φ(T) from SLE theory (0 params)
  - NRTLLayer        : Hardcoded NRTL activity coefficient model (0 params)
  - HansenDistanceLayer : Hardcoded Hansen Ra distance (0 params)

Physics layers have ZERO learnable parameters — all thermodynamic
equations are implemented as fixed differentiable functions.
"""

from typing import List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import (
    MessagePassing,
    Set2Set,
)


def make_temperature_features(T: torch.Tensor) -> torch.Tensor:
    """
    Build normalized temperature features.

    Returns (B, 3): [ (T-300)/50, (1/T - 1/300)*300, log(T/300) ].
    """
    t = torch.clamp(T.float(), min=1e-6)
    t_norm = (t - 300.0) / 50.0
    inv_norm = (1.0 / t - 1.0 / 300.0) * 300.0
    log_norm = torch.log(t / 300.0)
    return torch.stack([t_norm, inv_norm, log_norm], dim=-1)


# ================================================================== #
#  Scatter utilities (no torch_scatter dependency)                    #
# ================================================================== #

def scatter_add(
    src: torch.Tensor,
    index: torch.Tensor,
    dim: int = 0,
    dim_size: int = None,
) -> torch.Tensor:
    """Scatter-add using native PyTorch."""
    if dim_size is None:
        dim_size = int(index.max().item()) + 1
    if src.dim() > 1 and index.dim() == 1:
        idx = index.unsqueeze(-1).expand_as(src)
    else:
        idx = index
    out = torch.zeros(dim_size, *src.shape[1:],
                      dtype=src.dtype, device=src.device)
    return out.scatter_add_(dim, idx, src)


def scatter_mean(
    src: torch.Tensor,
    index: torch.Tensor,
    dim: int = 0,
    dim_size: int = None,
) -> torch.Tensor:
    """Scatter-mean using native PyTorch."""
    if dim_size is None:
        dim_size = int(index.max().item()) + 1
    if src.dim() > 1 and index.dim() == 1:
        idx = index.unsqueeze(-1).expand_as(src)
    else:
        idx = index
    out_sum = torch.zeros(dim_size, *src.shape[1:],
                          dtype=src.dtype, device=src.device)
    out_sum.scatter_add_(dim, idx, src)
    count = torch.zeros(dim_size, *src.shape[1:],
                        dtype=src.dtype, device=src.device)
    count.scatter_add_(dim, idx, torch.ones_like(src))
    return out_sum / count.clamp(min=1)


# ================================================================== #
#  Message-Passing GNN                                                #
# ================================================================== #

class MPNNLayer(MessagePassing):
    """
    Single message-passing layer with edge features and attention gating.

    message:  m_ij = MLP([h_i || h_j || e_ij]) * sigmoid(attn(m_ij))
    update:   h_i' = LayerNorm(h_i + MLP([h_i || agg_j m_ij]))
    """

    def __init__(self, hidden_dim: int, edge_dim: int):
        super().__init__(aggr="add")

        self.msg_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2 + edge_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.attn_mlp = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 4),
            nn.SiLU(),
            nn.Linear(hidden_dim // 4, 1),
        )
        self.upd_mlp = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.norm = nn.LayerNorm(hidden_dim)

    def forward(self, x, edge_index, edge_attr):
        out = self.propagate(edge_index, x=x, edge_attr=edge_attr)
        x_new = self.upd_mlp(torch.cat([x, out], dim=-1))
        return self.norm(x + x_new)

    def message(self, x_i, x_j, edge_attr):
        msg_input = torch.cat([x_i, x_j, edge_attr], dim=-1)
        msg = self.msg_mlp(msg_input)
        attn = torch.sigmoid(self.attn_mlp(msg))
        return msg * attn


class GNNEncoder(nn.Module):
    """
    Multi-layer GNN encoder with role-specific adapters.

    The same backbone processes both solute and solvent molecules.
    A lightweight adapter residual distinguishes the two roles,
    allowing shared low-level features with role-specific high-level
    representations.
    """

    def __init__(
        self,
        node_feat_dim: int,
        edge_feat_dim: int,
        hidden_dim: int = 256,
        n_layers: int = 6,
    ):
        super().__init__()

        self.node_embed = nn.Linear(node_feat_dim, hidden_dim)
        self.edge_embed = nn.Linear(edge_feat_dim, hidden_dim)

        self.layers = nn.ModuleList(
            [MPNNLayer(hidden_dim, hidden_dim) for _ in range(n_layers)]
        )

        self.solute_adapter = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.SiLU()
        )
        self.solvent_adapter = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.SiLU()
        )

        self.temp_mlp = nn.Sequential(
            nn.Linear(3, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim * 2),
        )

    def _apply_temp_film(
        self,
        h: torch.Tensor,
        batch: torch.Tensor,
        temp_feat: torch.Tensor,
    ) -> torch.Tensor:
        gamma_beta = self.temp_mlp(temp_feat)  # (B, 2D)
        gamma, beta = gamma_beta.chunk(2, dim=-1)
        gamma = gamma[batch]
        beta = beta[batch]
        return h * (1.0 + gamma) + beta

    def forward(
        self,
        x,
        edge_index,
        edge_attr,
        role: str = "solute",
        batch: Optional[torch.Tensor] = None,
        temp_feat: Optional[torch.Tensor] = None,
    ):
        h = self.node_embed(x)
        e = self.edge_embed(edge_attr)

        for layer in self.layers:
            h = layer(h, edge_index, e)
            if temp_feat is not None and batch is not None:
                h = self._apply_temp_film(h, batch, temp_feat)

        if role == "solute":
            h = h + self.solute_adapter(h)
        else:
            h = h + self.solvent_adapter(h)

        if temp_feat is not None and batch is not None:
            h = self._apply_temp_film(h, batch, temp_feat)

        return h


# ================================================================== #
#  Cross-Attention                                                    #
# ================================================================== #

class SoluteSolventCrossAttention(nn.Module):
    """
    Transformer-style cross-attention: solute atoms attend to solvent atoms.

    One block = MultiheadAttention + LayerNorm + FFN + LayerNorm.
    """

    def __init__(self, hidden_dim: int, n_heads: int = 8):
        super().__init__()
        self.cross_attn = nn.MultiheadAttention(
            hidden_dim, n_heads, batch_first=True, dropout=0.1
        )
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.ffn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 4),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim * 4, hidden_dim),
            nn.Dropout(0.1),
        )
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.temp_mlp = nn.Sequential(
            nn.Linear(3, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim * 2),
        )

    def forward(
        self,
        h_solute: torch.Tensor,
        h_solvent: torch.Tensor,
        solute_mask: Optional[torch.Tensor] = None,
        solvent_mask: Optional[torch.Tensor] = None,
        temp_feat: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Parameters
        ----------
        h_solute : (B, N_sol, D)
        h_solvent : (B, N_slv, D)
        solute_mask : (B, N_sol) bool — True for real atoms
        solvent_mask : (B, N_slv) bool — True for real atoms

        Returns
        -------
        h_out : (B, N_sol, D)
        attn_weights : (B, N_sol, N_slv)
        """
        # nn.MultiheadAttention expects key_padding_mask = True for PADDING
        key_padding_mask = None
        if solvent_mask is not None:
            key_padding_mask = ~solvent_mask

        h_cross, attn_weights = self.cross_attn(
            query=h_solute,
            key=h_solvent,
            value=h_solvent,
            key_padding_mask=key_padding_mask,
            need_weights=True,
            average_attn_weights=True,
        )

        h_out = self.norm1(h_solute + h_cross)
        if temp_feat is not None:
            gamma_beta = self.temp_mlp(temp_feat)  # (B, 2D)
            gamma, beta = gamma_beta.chunk(2, dim=-1)
            h_out = h_out * (1.0 + gamma[:, None, :]) + beta[:, None, :]
        h_out = self.norm2(h_out + self.ffn(h_out))
        return h_out, attn_weights


class BipartiteMessagePassing(nn.Module):
    """
    Bipartite message passing between solute and solvent atoms.

    Each block aggregates messages across the complete bipartite
    graph (solute ↔ solvent) using MLP-based pairwise transforms.
    """

    def __init__(self, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.msg_sol = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.msg_slv = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
        )
        self.norm_sol = nn.LayerNorm(hidden_dim)
        self.norm_slv = nn.LayerNorm(hidden_dim)
        self.temp_mlp = nn.Sequential(
            nn.Linear(3, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim * 2),
        )

    def forward(
        self,
        h_sol: torch.Tensor,
        h_slv: torch.Tensor,
        sol_mask: Optional[torch.Tensor] = None,
        slv_mask: Optional[torch.Tensor] = None,
        temp_feat: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        B, Ns, D = h_sol.shape
        Nv = h_slv.shape[1]

        sol_exp = h_sol[:, :, None, :].expand(-1, -1, Nv, -1)
        slv_exp = h_slv[:, None, :, :].expand(-1, Ns, -1, -1)

        pair_sol = torch.cat([sol_exp, slv_exp], dim=-1)
        msg_sol = self.msg_sol(pair_sol)  # (B, Ns, Nv, D)
        if slv_mask is not None:
            msg_sol = msg_sol * slv_mask[:, None, :, None]
            denom = slv_mask.sum(dim=1).clamp(min=1).view(B, 1, 1)
        else:
            denom = float(Nv)
        agg_sol = msg_sol.sum(dim=2) / denom

        pair_slv = torch.cat([slv_exp, sol_exp], dim=-1)
        msg_slv = self.msg_slv(pair_slv)  # (B, Ns, Nv, D)
        if sol_mask is not None:
            msg_slv = msg_slv * sol_mask[:, :, None, None]
            denom = sol_mask.sum(dim=1).clamp(min=1).view(B, 1, 1)
        else:
            denom = float(Ns)
        agg_slv = msg_slv.sum(dim=1) / denom

        h_sol_out = self.norm_sol(h_sol + agg_sol)
        h_slv_out = self.norm_slv(h_slv + agg_slv)

        if temp_feat is not None:
            gamma_beta = self.temp_mlp(temp_feat)  # (B, 2D)
            gamma, beta = gamma_beta.chunk(2, dim=-1)
            h_sol_out = h_sol_out * (1.0 + gamma[:, None, :]) + beta[:, None, :]
            h_slv_out = h_slv_out * (1.0 + gamma[:, None, :]) + beta[:, None, :]

        return h_sol_out, h_slv_out


def pad_atom_features(
    h_atoms_list: List[torch.Tensor],
) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Pad variable-length atom tensors into a single (B, N_max, D) batch.

    Returns
    -------
    padded : (B, N_max, D)
    mask   : (B, N_max) bool — True for real atoms
    """
    B = len(h_atoms_list)
    D = h_atoms_list[0].shape[-1]
    N_max = max(h.shape[0] for h in h_atoms_list)

    device = h_atoms_list[0].device
    padded = torch.zeros(B, N_max, D, device=device)
    mask = torch.zeros(B, N_max, dtype=torch.bool, device=device)

    for i, h in enumerate(h_atoms_list):
        n = h.shape[0]
        padded[i, :n, :] = h
        mask[i, :n] = True

    return padded, mask


def build_batch_from_lists(
    h_atoms_list: List[torch.Tensor],
    dtype: Optional[torch.dtype] = None,
) -> torch.Tensor:
    """Build a batch vector for concatenated per-graph tensors."""
    device = h_atoms_list[0].device
    if dtype is None:
        dtype = torch.long
    chunks = []
    for i, h in enumerate(h_atoms_list):
        chunks.append(
            torch.full((h.shape[0],), i, device=device, dtype=dtype)
        )
    return torch.cat(chunks, dim=0)


# ================================================================== #
#  Graph-level Readout                                                #
# ================================================================== #

class AttentionPooling(nn.Module):
    """Learnable attention-weighted sum pooling over graph nodes."""

    def __init__(self, hidden_dim: int):
        super().__init__()
        self.gate = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 4),
            nn.Tanh(),
            nn.Linear(hidden_dim // 4, 1),
        )

    def forward(self, h: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        h : (N_total, D)  — all nodes in the batch
        batch : (N_total,) — graph membership indices

        Returns
        -------
        (B, D) graph-level vectors
        """
        attn_logits = self.gate(h)  # (N_total, 1)

        # Subtract per-graph mean for numerical stability
        attn_mean = scatter_mean(attn_logits, batch, dim=0)  # (B, 1)
        attn_logits = attn_logits - attn_mean[batch]

        attn_weights = torch.exp(attn_logits)
        attn_sum = scatter_add(attn_weights, batch, dim=0)  # (B, 1)
        attn_weights = attn_weights / (attn_sum[batch] + 1e-8)

        return scatter_add(h * attn_weights, batch, dim=0)


class PhysicsAwareReadout(nn.Module):
    """
    Multi-strategy readout: attention + Set2Set pooling → concat.

    Output dimension = hidden_dim * 3.
    """

    def __init__(self, hidden_dim: int, set2set_steps: int = 3):
        super().__init__()
        self.attn_pool = AttentionPooling(hidden_dim)
        self.set2set = Set2Set(hidden_dim, processing_steps=set2set_steps)
        self.output_dim = hidden_dim * 3

    def forward(self, h: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
        h_attn = self.attn_pool(h, batch)       # (B, D)
        h_s2s = self.set2set(h, batch)          # (B, 2D)
        return torch.cat([h_attn, h_s2s], dim=-1)  # (B, 3D)


# ================================================================== #
#  Physics Layers (0 learnable parameters)                            #
# ================================================================== #

class IdealSolubilityLayer(nn.Module):
    """
    Ideal solubility contribution Φ(T).

    Φ = (ΔH_fus / R) · (1/T - 1/T_m)
        - (ΔCp_fus / R) · [(T_m/T - 1) - ln(T_m/T)]

    x_ideal = exp(-Φ)
    """

    def __init__(self, R: float = 8.314):
        super().__init__()
        self.R = R

    def forward(
        self,
        T: torch.Tensor,
        T_m: torch.Tensor,
        dH_fus: torch.Tensor,
        dCp_fus: torch.Tensor,
    ) -> torch.Tensor:
        """Return Φ (always ≥ 0 when T ≤ T_m)."""
        term1 = (dH_fus / self.R) * (1.0 / T - 1.0 / T_m)
        ratio = T_m / T
        psi = (ratio - 1.0) - torch.log(ratio + 1e-10)
        term2 = -(dCp_fus / self.R) * psi
        return term1 + term2


class NRTLLayer(nn.Module):
    """
    Non-Random Two-Liquid model for activity coefficients.

    τ_ij = a_ij + b_ij / T + c_ij · ln(T/T_ref)
    G_ij = exp(-α_ij · τ_ij)
    ln γ_2, ln γ_1, ln γ_∞  — standard NRTL expressions.

    Zero learnable parameters.
    """

    def __init__(
        self,
        R: float = 8.314,
        T_ref: float = 298.15,
        tau_clamp: float = 30.0,
        eps: float = 1e-10,
    ):
        super().__init__()
        self.R = R
        self.T_ref = T_ref
        self.tau_clamp = tau_clamp
        self.eps = eps

    def compute_tau_G(
        self, a_12, b_12, c_12, a_21, b_21, c_21, alpha_12, T
    ):
        """Compute τ and G parameters from temperature coefficients."""
        log_term = torch.log(T / self.T_ref + self.eps)
        tau_12 = a_12 + b_12 / T + c_12 * log_term
        tau_21 = a_21 + b_21 / T + c_21 * log_term
        tau_12 = torch.clamp(tau_12, -self.tau_clamp, self.tau_clamp)
        tau_21 = torch.clamp(tau_21, -self.tau_clamp, self.tau_clamp)
        G_12 = torch.exp(-alpha_12 * tau_12)
        G_21 = torch.exp(-alpha_12 * tau_21)
        return tau_12, tau_21, G_12, G_21

    def ln_gamma_1(self, x1, x2, tau_12, tau_21, G_12, G_21):
        """ln γ_1 (solvent activity coefficient)."""
        A = x2 + x1 * G_12 + self.eps
        B = x1 + x2 * G_21 + self.eps
        term1 = tau_21 * (G_21 / B) ** 2
        term2 = tau_12 * G_12 / A ** 2
        return x2 ** 2 * (term1 + term2)

    def ln_gamma_2(self, x1, x2, tau_12, tau_21, G_12, G_21):
        """ln γ_2 (solute activity coefficient)."""
        A = x2 + x1 * G_12 + self.eps
        B = x1 + x2 * G_21 + self.eps
        term1 = tau_12 * (G_12 / A) ** 2
        term2 = tau_21 * G_21 / B ** 2
        return x1 ** 2 * (term1 + term2)

    def ln_gamma_inf(self, tau_12, tau_21, G_21):
        """ln γ_2^∞ (infinite dilution: x_2 → 0)."""
        return tau_12 + tau_21 * G_21

    def forward(
        self, x2, a_12, b_12, c_12, a_21, b_21, c_21, alpha_12, T
    ):
        """Full NRTL forward: returns ln γ_2 and intermediate quantities."""
        x1 = 1.0 - x2
        tau_12, tau_21, G_12, G_21 = self.compute_tau_G(
            a_12, b_12, c_12, a_21, b_21, c_21, alpha_12, T
        )
        lng2 = self.ln_gamma_2(x1, x2, tau_12, tau_21, G_12, G_21)
        return {
            "ln_gamma_2": lng2,
            "tau_12": tau_12,
            "tau_21": tau_21,
            "G_12": G_12,
            "G_21": G_21,
        }


class HansenDistanceLayer(nn.Module):
    """
    Hansen distance Ra between two molecules.

    Ra² = 4·(δd1 - δd2)² + (δp1 - δp2)² + (δh1 - δh2)²

    Zero learnable parameters.
    """

    def forward(
        self, hansen_1: torch.Tensor, hansen_2: torch.Tensor
    ) -> torch.Tensor:
        dd = hansen_1[:, 0] - hansen_2[:, 0]
        dp = hansen_1[:, 1] - hansen_2[:, 1]
        dh = hansen_1[:, 2] - hansen_2[:, 2]
        Ra_sq = 4.0 * dd ** 2 + dp ** 2 + dh ** 2
        return torch.sqrt(Ra_sq + 1e-10)
