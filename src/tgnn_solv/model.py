"""
TGNNSolv — main model assembling all components.

Key principle: the network predicts physical quantities and lets the
thermodynamic solver do the hard work. Temperature-dependent state enters
the NRTL / correction blocks explicitly instead of leaking into crystal
property heads.
"""

from typing import Dict, List, Optional

import torch
import torch.nn as nn
from torch_geometric.data import Batch

from .config import TGNNSolvConfig
from .data.solvent_types import SOLVENT_TYPE_COUNT, SOLVENT_TYPE_OTHER_ID
from .features import EDGE_FEAT_DIM, NODE_FEAT_DIM
from .heads import (
    AuxPropsHead,
    FusionHead,
    HansenHead,
    NRTLHead,
    PairRepresentation,
    SolventTypeMoE,
)
from .heads import AdaptivePhysicsCorrection
from .layers import (
    BipartiteMessagePassing,
    GNNEncoder,
    PhysicsAwareReadout,
    SoluteSolventCrossAttention,
    build_batch_from_lists,
    make_temperature_features,
    pad_atom_features,
)
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
    ) -> None:
        super().__init__()
        self.cfg = cfg
        F = cfg.hidden_dim

        # --- Encoder ---
        self.gnn = GNNEncoder(
            node_feat_dim, edge_feat_dim,
            hidden_dim=F,
            n_layers=cfg.n_gnn_layers,
            role_mode=cfg.encoder_role_mode,
            role_specific_layers=cfg.encoder_role_specific_layers,
        )

        # --- Interaction stack ---
        self.interaction_mode = cfg.interaction_mode
        self.cross_attn_layers = nn.ModuleList()
        self.bipartite_layers = nn.ModuleList()
        if cfg.interaction_mode == "cross_attn":
            self.cross_attn_layers = nn.ModuleList([
                SoluteSolventCrossAttention(F, cfg.n_attn_heads)
                for _ in range(cfg.n_cross_attn_layers)
            ])
        elif cfg.interaction_mode == "bipartite":
            self.bipartite_layers = nn.ModuleList([
                BipartiteMessagePassing(F, dropout=cfg.dropout)
                for _ in range(cfg.n_cross_attn_layers)
            ])
        else:
            raise ValueError(
                f"Unknown interaction_mode: {cfg.interaction_mode}"
            )

        # --- Readout ---
        self.readout = PhysicsAwareReadout(
            F, set2set_steps=cfg.set2set_steps
        )
        D_r = self.readout.output_dim  # hidden_dim * 3

        # --- Pair representation ---
        self.pair_repr = PairRepresentation(D_r, cfg.pair_dim)
        self.solvent_moe = None
        if cfg.use_solvent_moe:
            self.solvent_moe = SolventTypeMoE(
                cfg.pair_dim,
                SOLVENT_TYPE_COUNT,
                num_experts=cfg.solvent_moe_experts,
                type_emb_dim=cfg.solvent_type_emb_dim,
                hidden_dim=cfg.solvent_moe_hidden,
                dropout=cfg.dropout,
            )

        # --- Prediction heads ---
        self.head_fusion = FusionHead(D_r, cfg)
        self.head_nrtl = NRTLHead(cfg.pair_dim, cfg)
        self.head_hansen = HansenHead(D_r, cfg)
        self.head_aux = AuxPropsHead(D_r)

        # --- Physics solver (0 learnable params) ---
        self.sle_solver = SLESolver(cfg)

        # --- Learned correction ---
        self.correction = AdaptivePhysicsCorrection(
            cfg.pair_dim,
            n_param_features=9,
            Tm_limit=cfg.correction_Tm_max_delta,
            dH_fraction_limit=cfg.correction_dH_fraction,
            tau_limit=cfg.correction_tau_max_delta,
        )

        # --- Global tokens for co-attention ---
        self.sol_token = nn.Parameter(torch.zeros(1, 1, F))
        self.slv_token = nn.Parameter(torch.zeros(1, 1, F))
        nn.init.normal_(self.sol_token, mean=0.0, std=0.02)
        nn.init.normal_(self.slv_token, mean=0.0, std=0.02)
        self.token_proj = nn.Linear(F, D_r)
        self.sol_token_gate = nn.Parameter(torch.tensor(0.0))
        self.slv_token_gate = nn.Parameter(torch.tensor(0.0))

    def _encode_and_readout(
        self,
        data: Batch,
        role: str = "solute",
        temp_feat: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Run GNN + readout on a batched graph."""
        h_atoms = self.gnn(
            data.x,
            data.edge_index,
            data.edge_attr,
            role=role,
            batch=data.batch,
            temp_feat=temp_feat,
        )
        g_mol = self.readout(h_atoms, data.batch)
        return h_atoms, g_mol

    def _encoder_temp_features(
        self,
        temp_feat: torch.Tensor,
    ) -> Optional[torch.Tensor]:
        """Return temperature features for the encoder path if enabled."""
        if self.cfg.use_temperature_in_encoder:
            return temp_feat
        return None

    def _interaction_temp_features(
        self,
        temp_feat: torch.Tensor,
    ) -> Optional[torch.Tensor]:
        """Return temperature features for the interaction path if enabled."""
        if self.cfg.use_temperature_in_interaction:
            return temp_feat
        return None

    def _nrtl_temp_features(
        self,
        temp_feat: torch.Tensor,
    ) -> Optional[torch.Tensor]:
        """Return temperature features for the NRTL head if enabled."""
        if self.cfg.use_temperature_in_nrtl_head:
            return temp_feat
        return None

    def _split_atoms_by_graph(
        self, h_atoms: torch.Tensor, batch: torch.Tensor
    ) -> List[torch.Tensor]:
        """Split flat atom tensor into per-graph list."""
        graphs = []
        for i in range(batch.max().item() + 1):
            mask = batch == i
            graphs.append(h_atoms[mask])
        return graphs

    def _append_global_token(
        self, atoms_list: List[torch.Tensor], token: torch.Tensor
    ) -> List[torch.Tensor]:
        token = token[0]  # (1, D)
        return [torch.cat([h, token.to(h)], dim=0) for h in atoms_list]

    def _slice_padded(
        self,
        padded: torch.Tensor,
        lengths: List[int],
        drop_last: bool = False,
    ) -> List[torch.Tensor]:
        out = []
        for i, length in enumerate(lengths):
            end = length - 1 if drop_last else length
            out.append(padded[i, :end, :])
        return out

    def _extract_tokens(
        self,
        padded: torch.Tensor,
        lengths: List[int],
    ) -> torch.Tensor:
        idx = torch.tensor(
            [length - 1 for length in lengths],
            device=padded.device,
        )
        return padded[torch.arange(padded.size(0), device=padded.device), idx]

    def _build_param_summary(
        self,
        *,
        fusion_params: dict[str, torch.Tensor],
        nrtl_params: dict[str, torch.Tensor],
        physics_out: dict[str, torch.Tensor],
        temp_feat: torch.Tensor,
        Ra: torch.Tensor,
        dtype: torch.dtype,
    ) -> torch.Tensor:
        """Build a compact solver-facing summary for the residual corrector."""
        tau_12 = physics_out["tau_12"].to(dtype)
        tau_21 = physics_out["tau_21"].to(dtype)
        temp_feat = temp_feat.to(dtype)

        return torch.cat([
            ((fusion_params["T_m"] - 400.0) / 200.0).unsqueeze(-1),
            ((fusion_params["dH_fus"] - 20000.0) / 10000.0).unsqueeze(-1),
            (tau_12 / self.cfg.tau_clamp).unsqueeze(-1),
            (tau_21 / self.cfg.tau_clamp).unsqueeze(-1),
            ((nrtl_params["alpha_12"] - 0.3) / 0.15).unsqueeze(-1),
            temp_feat,
            (Ra.to(dtype) / 10.0).unsqueeze(-1),
        ], dim=-1)

    def _build_corrected_fusion_params(
        self,
        fusion_params: dict[str, torch.Tensor],
        param_deltas: dict[str, torch.Tensor],
    ) -> dict[str, torch.Tensor]:
        """Apply bounded correction deltas to crystal-property parameters."""
        T_m = (
            fusion_params["T_m"] + param_deltas["delta_T_m"]
        ).clamp(self.cfg.T_m_min, self.cfg.T_m_max)
        dH_scale = 1.0 + param_deltas["delta_dH_fraction"]
        dH_fus = (fusion_params["dH_fus"] * dH_scale).clamp(min=self.cfg.eps)
        return {
            "T_m": T_m,
            "dH_fus": dH_fus,
            "dCp_fus": fusion_params["dCp_fus"],
        }

    def _build_corrected_nrtl_state(
        self,
        *,
        nrtl_params: dict[str, torch.Tensor],
        physics_out: dict[str, torch.Tensor],
        param_deltas: dict[str, torch.Tensor],
    ) -> dict[str, torch.Tensor]:
        """Build a corrected solver-space NRTL state for the proposal path."""
        return {
            "tau_12": (
                physics_out["tau_12"] + param_deltas["delta_tau_12"]
            ).clamp(-self.cfg.tau_clamp, self.cfg.tau_clamp),
            "tau_21": (
                physics_out["tau_21"] + param_deltas["delta_tau_21"]
            ).clamp(-self.cfg.tau_clamp, self.cfg.tau_clamp),
            "alpha_12": nrtl_params["alpha_12"],
        }

    def forward(
            self,
            solute_data: Batch,
            solvent_data: Batch,
            T: torch.Tensor,
            solvent_type: Optional[torch.Tensor] = None,
            return_intermediates: bool = False,  # ✦ NEW
    ) -> Dict[str, torch.Tensor]:
        """
        Full forward pass.

        Parameters
        ----------
        solute_data : PyG Batch of solute graphs
        solvent_data : PyG Batch of solvent graphs
        T : (B,) temperature in Kelvin
        solvent_type : (B,) optional solvent type indices for MoE
        return_intermediates : if True, return (output_dict, intermediates_dict)
            where intermediates_dict contains flat physical parameters,
            representations, and gate values for analysis.

        Returns
        -------
        If return_intermediates is False:
            dict with keys: ln_x2, x2, physics, fusion_params, nrtl_params,
                hansen_sol, hansen_slv, aux_sol, aux_slv, Ra, confidence,
                ln_x2_direct, ln_x2_direct_log_sigma, ln_x2_direct_sigma,
                correction, gate, moe_gate, attn_maps
        If return_intermediates is True:
            (output_dict, intermediates_dict)
            intermediates_dict has flat keys: T_m, dH_fus, dCp_fus,
                alpha_12, tau_12, tau_21, G_12, G_21, ln_gamma_2, gamma_2,
                ln_gamma_inf, Phi, x_ideal, ln_x2_ideal, ln_x2_physics,
                ln_x2_direct, ln_x2_final, correction_gate,
                correction_magnitude, hansen_sol, hansen_slv, Ra,
                g_sol_pre, g_slv_pre, g_sol_post, g_slv_post, g_pair,
                + all nrtl_params keys (mode-dependent)
        """
        t_feat = make_temperature_features(T)
        encoder_t_feat = self._encoder_temp_features(t_feat)
        interaction_t_feat = self._interaction_temp_features(t_feat)
        nrtl_t_feat = self._nrtl_temp_features(t_feat)

        # ---- 1. Encode both molecules ----
        h_sol_atoms, g_sol_pre = self._encode_and_readout(
            solute_data, "solute", temp_feat=encoder_t_feat
        )
        h_slv_atoms, g_slv_pre = self._encode_and_readout(
            solvent_data, "solvent", temp_feat=encoder_t_feat
        )

        # ---- 2. Auxiliary heads (before cross-attention) ----
        hansen_sol = self.head_hansen(g_sol_pre)
        hansen_slv = self.head_hansen(g_slv_pre)
        aux_sol = self.head_aux(g_sol_pre)
        aux_slv = self.head_aux(g_slv_pre)

        # ---- 3. Cross-attention / Bipartite MP ----
        sol_atoms_list = self._split_atoms_by_graph(
            h_sol_atoms, solute_data.batch
        )
        slv_atoms_list = self._split_atoms_by_graph(
            h_slv_atoms, solvent_data.batch
        )

        # Append global tokens for co-attention
        sol_atoms_list = self._append_global_token(
            sol_atoms_list, self.sol_token
        )
        slv_atoms_list = self._append_global_token(
            slv_atoms_list, self.slv_token
        )
        sol_lengths = [h.shape[0] for h in sol_atoms_list]
        slv_lengths = [h.shape[0] for h in slv_atoms_list]

        h_sol_padded, sol_mask = pad_atom_features(sol_atoms_list)
        h_slv_padded, slv_mask = pad_atom_features(slv_atoms_list)

        attn_maps = []
        if self.interaction_mode == "cross_attn":
            for cross_layer in self.cross_attn_layers:
                sol_prev = h_sol_padded
                slv_prev = h_slv_padded
                h_sol_padded, attn_w = cross_layer(
                    sol_prev,
                    slv_prev,
                    sol_mask,
                    slv_mask,
                    interaction_t_feat,
                )
                attn_maps.append(attn_w.detach())
                h_slv_padded, _ = cross_layer(
                    slv_prev,
                    sol_prev,
                    slv_mask,
                    sol_mask,
                    interaction_t_feat,
                )
        else:
            for mp_layer in self.bipartite_layers:
                h_sol_padded, h_slv_padded = mp_layer(
                    h_sol_padded,
                    h_slv_padded,
                    sol_mask,
                    slv_mask,
                    interaction_t_feat,
                )

        # ---- 4. Post-cross-attention readout for solute ----
        sol_no_token = self._slice_padded(
            h_sol_padded, sol_lengths, drop_last=True
        )
        slv_no_token = self._slice_padded(
            h_slv_padded, slv_lengths, drop_last=True
        )
        sol_batch = build_batch_from_lists(
            sol_no_token, dtype=solute_data.batch.dtype
        )
        slv_batch = build_batch_from_lists(
            slv_no_token, dtype=solvent_data.batch.dtype
        )

        g_sol_post = self.readout(torch.cat(sol_no_token, dim=0), sol_batch)
        g_slv_post = self.readout(torch.cat(slv_no_token, dim=0), slv_batch)
        g_sol_tok = self._extract_tokens(h_sol_padded, sol_lengths)
        g_slv_tok = self._extract_tokens(h_slv_padded, slv_lengths)
        g_sol_post = g_sol_post + self.sol_token_gate * self.token_proj(g_sol_tok)
        g_slv_post = g_slv_post + self.slv_token_gate * self.token_proj(g_slv_tok)

        # ---- 5. Pair representation ----
        g_pair = self.pair_repr(g_sol_post, g_slv_post)
        moe_gate = None
        if self.solvent_moe is not None:
            if solvent_type is None:
                solvent_type = torch.full(
                    (g_pair.shape[0],),
                    SOLVENT_TYPE_OTHER_ID,
                    device=g_pair.device,
                    dtype=torch.long,
                )
            else:
                solvent_type = solvent_type.to(g_pair.device)
            g_pair, moe_gate = self.solvent_moe(g_pair, solvent_type)

        # ---- 6. Prediction heads ----
        fusion_params = self.head_fusion(g_sol_pre)
        nrtl_params = self.head_nrtl(g_pair, temp_feat=nrtl_t_feat)

        # ---- 7. SLE solver (float32 for numerical stability) ----
        with torch.amp.autocast(device_type='cpu', enabled=False):
            T_f32 = T.float()
            fus_f32 = {k: v.float() for k, v in fusion_params.items()}
            nrtl_f32 = {k: v.float() for k, v in nrtl_params.items()}
            physics_out = self.sle_solver(T_f32, fus_f32, nrtl_f32)

        # ---- 8. Hansen distance ----
        Ra = self.sle_solver.hansen_layer(hansen_sol, hansen_slv)

        # ---- 9. Adaptive physics correction ----
        param_summary = self._build_param_summary(
            fusion_params=fusion_params,
            nrtl_params=nrtl_params,
            physics_out=physics_out,
            temp_feat=t_feat,
            Ra=Ra,
            dtype=T.dtype,
        )

        ln_x2_physics = physics_out["ln_x2"]

        confidence, param_deltas, proposal_log_sigma = self.correction(
            g_pair,
            param_summary,
        )

        corrected_fusion_params = self._build_corrected_fusion_params(
            fusion_params,
            param_deltas,
        )
        corrected_nrtl_state = self._build_corrected_nrtl_state(
            nrtl_params=nrtl_params,
            physics_out=physics_out,
            param_deltas=param_deltas,
        )

        with torch.amp.autocast(device_type="cpu", enabled=False):
            proposal_out = self.sle_solver(
                T.float(),
                {k: v.float() for k, v in corrected_fusion_params.items()},
                {k: v.float() for k, v in corrected_nrtl_state.items()},
                use_implicit=False,
            )

        raw_residual = proposal_out["ln_x2"].to(T.dtype) - ln_x2_physics
        bounded_residual = raw_residual.clamp(
            min=-self.cfg.correction_max_abs,
            max=self.cfg.correction_max_abs,
        )
        ln_x2_direct = ln_x2_physics + bounded_residual
        ln_x2_direct_log_sigma = proposal_log_sigma
        ln_x2 = ln_x2_physics + (1.0 - confidence) * bounded_residual

        output = {
            "ln_x2": ln_x2,
            "x2": torch.exp(ln_x2).clamp(0, 1),
            "physics": physics_out,
            "proposal_physics": proposal_out,
            "fusion_params": fusion_params,
            "corrected_fusion_params": corrected_fusion_params,
            "nrtl_params": nrtl_params,
            "corrected_nrtl_state": corrected_nrtl_state,
            "hansen_sol": hansen_sol,
            "hansen_slv": hansen_slv,
            "aux_sol": aux_sol,
            "aux_slv": aux_slv,
            "Ra": Ra,
            "confidence": confidence,
            "ln_x2_direct": ln_x2_direct,
            "ln_x2_direct_log_sigma": ln_x2_direct_log_sigma,
            "ln_x2_direct_sigma": ln_x2_direct_log_sigma.exp(),
            "correction": ln_x2 - ln_x2_physics,
            "gate": confidence.mean(),
            "moe_gate": moe_gate,
            "attn_maps": attn_maps,
        }

        # ✦ NEW — flat intermediates for analysis scripts
        if return_intermediates:
            intermediates = {
                # Crystal / fusion properties
                "T_m": fusion_params["T_m"],
                "dH_fus": fusion_params["dH_fus"],
                "dCp_fus": fusion_params["dCp_fus"],
                "T_m_corrected": corrected_fusion_params["T_m"],
                "dH_fus_corrected": corrected_fusion_params["dH_fus"],
                "dCp_fus_corrected": corrected_fusion_params["dCp_fus"],
                # NRTL binary interaction (all mode-dependent keys)
                "alpha_12": nrtl_params["alpha_12"],
                "tau_12": physics_out["tau_12"],
                "tau_21": physics_out["tau_21"],
                "tau_12_corrected": corrected_nrtl_state["tau_12"],
                "tau_21_corrected": corrected_nrtl_state["tau_21"],
                "G_12": physics_out["G_12"],
                "G_21": physics_out["G_21"],
                # Activity coefficients
                "ln_gamma_2": physics_out["ln_gamma_2"],
                "gamma_2": torch.exp(physics_out["ln_gamma_2"]),
                "ln_gamma_inf": physics_out["ln_gamma_inf"],
                "ln_gamma_2_corrected": proposal_out["ln_gamma_2"],
                "ln_gamma_inf_corrected": proposal_out["ln_gamma_inf"],
                # Ideal solubility contribution
                "Phi": physics_out["Phi"],
                "x_ideal": physics_out["x_ideal"],
                "ln_x2_ideal": torch.log(
                    physics_out["x_ideal"] + self.cfg.eps
                ),
                # Physics path vs learned path vs final
                "ln_x2_physics": physics_out["ln_x2"],
                "ln_x2_direct": ln_x2_direct,
                "ln_x2_final": ln_x2,
                "ln_x2_proposal": proposal_out["ln_x2"],
                # Correction gate: σ(w) per sample
                "correction_gate": confidence,
                "correction_magnitude": ln_x2 - physics_out["ln_x2"],
                "delta_T_m": param_deltas["delta_T_m"],
                "delta_dH_fraction": param_deltas["delta_dH_fraction"],
                "delta_tau_12": param_deltas["delta_tau_12"],
                "delta_tau_21": param_deltas["delta_tau_21"],
                # Hansen solubility parameters
                "hansen_sol": hansen_sol,
                "hansen_slv": hansen_slv,
                "Ra": Ra,
                # Auxiliary properties
                "aux_sol": aux_sol,
                "aux_slv": aux_slv,
                # Learned representations (detached — no grad needed)
                "g_sol_pre": g_sol_pre.detach(),
                "g_slv_pre": g_slv_pre.detach(),
                "g_sol_post": g_sol_post.detach(),
                "g_slv_post": g_slv_post.detach(),
                "g_pair": g_pair.detach(),
            }
            # Include all raw NRTL head outputs (mode-dependent keys)
            for k, v in nrtl_params.items():
                if k not in intermediates:
                    intermediates[f"nrtl_{k}"] = v

            return output, intermediates

        return output
