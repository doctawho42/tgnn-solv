"""
TGNNSolv — main model assembling all components.

Architecture overview:
  1. GNNEncoder processes solute and solvent graphs (shared backbone)
  2. Cross-attention lets solute atoms attend to solvent atoms
  3. PhysicsAwareReadout pools atom features into graph vectors
  4. PairRepresentation combines solute + solvent vectors
  5. Prediction heads output physical parameters
  6. SLE solver computes solubility from those parameters (0 learnable params)
  7. GatedResidualCorrection adds a small learned correction

Key principle: the GNN predicts PHYSICAL PARAMETERS, not solubility
directly.  All thermodynamics is hardcoded and differentiable.
"""

from typing import Dict, List, Optional

import torch
import torch.nn as nn
from torch_geometric.data import Batch

from .config import TGNNSolvConfig
from .features import NODE_FEAT_DIM, EDGE_FEAT_DIM
from .layers import (
    GNNEncoder,
    SoluteSolventCrossAttention,
    PhysicsAwareReadout,
    pad_atom_features,
)
from .heads import (
    PairRepresentation,
    FusionHead,
    NRTLHead,
    HansenHead,
    AuxPropsHead,
)
from .heads import AdaptivePhysicsCorrection
from .solver import SLESolver


class TGNNSolv(nn.Module):
    """
    Thermodynamic Graph Neural Network for Solubility Prediction.

    Parameters
    ----------
    node_feat_dim : int
        Atom feature dimension (default from features.py).
    edge_feat_dim : int
        Bond feature dimension (default from features.py).
    cfg : TGNNSolvConfig
        Full model configuration.
    """

    def __init__(
        self,
        node_feat_dim: int = NODE_FEAT_DIM,
        edge_feat_dim: int = EDGE_FEAT_DIM,
        cfg: TGNNSolvConfig = TGNNSolvConfig(),
    ):
        super().__init__()
        self.cfg = cfg
        F = cfg.hidden_dim

        # --- Encoder ---
        self.gnn = GNNEncoder(
            node_feat_dim, edge_feat_dim,
            hidden_dim=F, n_layers=cfg.n_gnn_layers,
        )

        # --- Cross-attention stack ---
        self.cross_attn_layers = nn.ModuleList([
            SoluteSolventCrossAttention(F, cfg.n_attn_heads)
            for _ in range(cfg.n_cross_attn_layers)
        ])

        # --- Readout ---
        self.readout = PhysicsAwareReadout(F)
        D_r = self.readout.output_dim  # hidden_dim * 3

        # --- Pair representation ---
        self.pair_repr = PairRepresentation(D_r, cfg.pair_dim)

        # --- Prediction heads ---
        self.head_fusion = FusionHead(D_r, cfg)
        self.head_nrtl = NRTLHead(cfg.pair_dim, cfg)
        self.head_hansen = HansenHead(D_r, cfg)
        self.head_aux = AuxPropsHead(D_r)

        # --- Physics solver (0 learnable params) ---
        self.sle_solver = SLESolver(cfg)

        # --- Learned correction ---
        self.correction = AdaptivePhysicsCorrection(
            cfg.pair_dim, n_param_features=6,
        )

    def _encode_and_readout(
        self, data: Batch, role: str = "solute"
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Run GNN + readout on a batched graph."""
        h_atoms = self.gnn(
            data.x, data.edge_index, data.edge_attr, role=role,
        )
        g_mol = self.readout(h_atoms, data.batch)
        return h_atoms, g_mol

    def _split_atoms_by_graph(
        self, h_atoms: torch.Tensor, batch: torch.Tensor
    ) -> List[torch.Tensor]:
        """Split flat atom tensor into per-graph list."""
        graphs = []
        for i in range(batch.max().item() + 1):
            mask = batch == i
            graphs.append(h_atoms[mask])
        return graphs

    def forward(
        self,
        solute_data: Batch,
        solvent_data: Batch,
        T: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """
        Full forward pass.

        Parameters
        ----------
        solute_data : PyG Batch of solute graphs
        solvent_data : PyG Batch of solvent graphs
        T : (B,) temperature in Kelvin

        Returns
        -------
        dict with keys:
          ln_x2, x2           — final predictions
          physics              — SLE solver outputs
          fusion_params        — (T_m, dH_fus, dCp_fus)
          nrtl_params          — (dg_12, dg_21, alpha_12, a_T12, a_T21)
          hansen_sol, hansen_slv — Hansen parameters
          aux_sol, aux_slv     — auxiliary properties
          Ra                   — Hansen distance
          correction, gate     — residual correction
          attn_maps            — cross-attention weights (detached)
        """
        # ---- 1. Encode both molecules ----
        h_sol_atoms, g_sol_pre = self._encode_and_readout(
            solute_data, "solute"
        )
        h_slv_atoms, g_slv_pre = self._encode_and_readout(
            solvent_data, "solvent"
        )

        # ---- 2. Auxiliary heads (before cross-attention) ----
        hansen_sol = self.head_hansen(g_sol_pre)
        hansen_slv = self.head_hansen(g_slv_pre)
        aux_sol = self.head_aux(g_sol_pre)
        aux_slv = self.head_aux(g_slv_pre)

        # ---- 3. Cross-attention: solute attends to solvent ----
        sol_atoms_list = self._split_atoms_by_graph(
            h_sol_atoms, solute_data.batch
        )
        slv_atoms_list = self._split_atoms_by_graph(
            h_slv_atoms, solvent_data.batch
        )

        h_sol_padded, sol_mask = pad_atom_features(sol_atoms_list)
        h_slv_padded, slv_mask = pad_atom_features(slv_atoms_list)

        attn_maps = []
        for cross_layer in self.cross_attn_layers:
            h_sol_padded, attn_w = cross_layer(
                h_sol_padded, h_slv_padded, sol_mask, slv_mask
            )
            attn_maps.append(attn_w.detach())

        # ---- 4. Post-cross-attention readout for solute ----
        h_sol_cross = h_sol_padded[sol_mask]  # unpad back to flat
        g_sol_post = self.readout(h_sol_cross, solute_data.batch)
        g_slv_post = g_slv_pre  # solvent unchanged

        # ---- 5. Pair representation ----
        g_pair = self.pair_repr(g_sol_post, g_slv_post)

        # ---- 6. Prediction heads ----
        fusion_params = self.head_fusion(g_sol_pre)
        nrtl_params = self.head_nrtl(g_pair)

        # ---- 7. SLE solver (float32 for numerical stability) ----
        with torch.amp.autocast(device_type='cpu', enabled=False):
            T_f32 = T.float()
            fus_f32 = {k: v.float() for k, v in fusion_params.items()}
            nrtl_f32 = {k: v.float() for k, v in nrtl_params.items()}
            physics_out = self.sle_solver(T_f32, fus_f32, nrtl_f32)

        # ---- 8. Hansen distance ----
        Ra = self.sle_solver.hansen_layer(hansen_sol, hansen_slv)

        # ---- 9. Adaptive physics correction ----
        param_summary = torch.stack([
            (fusion_params["T_m"] - 400.0) / 200.0,
            (fusion_params["dH_fus"] - 20000.0) / 10000.0,
            nrtl_params["dg_12"] / self.cfg.S_g,
            nrtl_params["dg_21"] / self.cfg.S_g,
            (nrtl_params["alpha_12"] - 0.3) / 0.15,
            (T - 300.0) / 50.0,
        ], dim=-1)

        ln_x2_physics = physics_out["ln_x2"]

        ln_x2, confidence, ln_x2_direct = self.correction(
            g_pair, param_summary, ln_x2_physics
        )

        return {
            "ln_x2": ln_x2,
            "x2": torch.exp(ln_x2).clamp(0, 1),
            "physics": physics_out,
            "fusion_params": fusion_params,
            "nrtl_params": nrtl_params,
            "hansen_sol": hansen_sol,
            "hansen_slv": hansen_slv,
            "aux_sol": aux_sol,
            "aux_slv": aux_slv,
            "Ra": Ra,
            "confidence": confidence,
            "ln_x2_direct": ln_x2_direct,
            "correction": ln_x2 - ln_x2_physics,  # effective correction
            "gate": confidence.mean(),  # for logging compatibility
            "attn_maps": attn_maps,
        }