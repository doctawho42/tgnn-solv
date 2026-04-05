"""
Direct GNN baseline: dual-graph encoder + thermometer T + MLP head.

Architecture:
  Solute graph  → GNNEncoder(role=solute)  → Readout → g_sol
  Solvent graph → GNNEncoder(role=solvent) → Readout → g_slv
  Temperature   → ThermometerEncoder → t_enc

  [g_sol || g_slv || g_sol * g_slv || |g_sol - g_slv| || t_enc]
    → MLP → ln(x₂)

Same GNN backbone as TGNN-Solv. Same co-attention with global tokens.
No physics layer, no NRTL, no SLE solver.
Pure data-driven prediction.

This is the key ablation: if TGNN-Solv does not beat this,
the physics-informed approach adds no value.
"""

from __future__ import annotations

import gc
from typing import Any, Callable, Optional, TypeAlias

import torch
import torch.nn as nn
from torch import Tensor
from torch.utils.data import DataLoader
from torch_geometric.data import Batch

from ..config import TGNNSolvConfig
from ..heads import MorganFeatureAdapter
from ..features import (
    DESCRIPTOR_Z_CLIP,
    EDGE_FEAT_DIM,
    NODE_FEAT_DIM,
    validate_descriptor_normalization_stats,
)
from ..layers import (
    SoluteSolventCrossAttention,
    BipartiteMessagePassing,
    PhysicsAwareReadout,
    build_graph_encoder,
    pad_atom_features,
    make_temperature_features,
    build_batch_from_lists,
)
from ..progress import progress
from .temperature import ThermometerEncoder

TensorList: TypeAlias = list[Tensor]
MetricDict: TypeAlias = dict[str, float]
DirectTrainerStateDict: TypeAlias = dict[str, Any]
DirectResumeStateDict: TypeAlias = dict[str, Any]


class DirectGNN(nn.Module):
    """
    Dual-graph GNN with direct solubility prediction.

    Parameters
    ----------
    node_feat_dim, edge_feat_dim : feature dimensions
    cfg : TGNNSolvConfig (reuses architecture hyperparameters)
    n_temp_bins : number of thermometer bins for temperature
    T_min, T_max : temperature range for binning
    """

    def __init__(
        self,
        node_feat_dim: int = NODE_FEAT_DIM,
        edge_feat_dim: int = EDGE_FEAT_DIM,
        cfg: TGNNSolvConfig = TGNNSolvConfig(),
        n_temp_bins: int = 20,
        T_min: float = 200.0,
        T_max: float = 500.0,
    ) -> None:
        super().__init__()
        self.cfg = cfg
        F = cfg.hidden_dim

        # --- Same GNN encoder (shared backbone with role adapters) ---
        self.gnn = build_graph_encoder(node_feat_dim, edge_feat_dim, cfg)

        # --- Same interaction stack ---
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

        # --- Same readout ---
        self.readout = PhysicsAwareReadout(
            F, set2set_steps=cfg.set2set_steps
        )
        D_r = self.readout.output_dim  # hidden_dim * 3

        # --- Global tokens for co-attention ---
        self.sol_token = nn.Parameter(torch.zeros(1, 1, F))
        self.slv_token = nn.Parameter(torch.zeros(1, 1, F))
        nn.init.normal_(self.sol_token, mean=0.0, std=0.02)
        nn.init.normal_(self.slv_token, mean=0.0, std=0.02)
        self.token_proj = nn.Linear(F, D_r)
        self.sol_token_gate = nn.Parameter(torch.tensor(0.0))
        self.slv_token_gate = nn.Parameter(torch.tensor(0.0))

        # --- Temperature encoder ---
        self.temp_encoder = ThermometerEncoder(n_temp_bins, T_min, T_max)
        self.solute_fp_adapter = None
        self.solvent_fp_adapter = None
        self.fp_pre_scale = None
        self.fp_post_scale = None
        if cfg.use_morgan_features:
            self.solute_fp_adapter = MorganFeatureAdapter(
                cfg.morgan_n_bits,
                D_r,
                cfg.morgan_hidden_dim,
                cfg.dropout,
            )
            self.solvent_fp_adapter = MorganFeatureAdapter(
                cfg.morgan_n_bits,
                D_r,
                cfg.morgan_hidden_dim,
                cfg.dropout,
            )
            self.fp_pre_scale = nn.Parameter(torch.tensor(0.5))
            self.fp_post_scale = nn.Parameter(torch.tensor(0.5))

        self.descriptor_adapter = None
        self.register_buffer("descriptor_mean", torch.empty(0))
        self.register_buffer("descriptor_std", torch.empty(0))
        if cfg.use_descriptor_augmentation:
            if cfg.descriptor_dim <= 0:
                raise ValueError("descriptor_dim must be positive when descriptor augmentation is enabled.")
            descriptor_hidden_dim = cfg.resolved_descriptor_hidden_dim
            self.descriptor_adapter = nn.Sequential(
                nn.Linear(cfg.descriptor_dim, descriptor_hidden_dim),
                nn.SiLU(),
                nn.Dropout(cfg.dropout),
                nn.Linear(descriptor_hidden_dim, descriptor_hidden_dim),
                nn.SiLU(),
            )
            self.descriptor_mean = torch.zeros(cfg.descriptor_dim)
            self.descriptor_std = torch.ones(cfg.descriptor_dim)

        # --- Pair + temperature → prediction ---
        # Input: g_sol(D_r) + g_slv(D_r) + g_sol*g_slv(D_r) +
        #        |g_sol-g_slv|(D_r) + t_enc(n_temp_bins)
        pair_input_dim = D_r * 4 + n_temp_bins
        if cfg.use_descriptor_augmentation:
            pair_input_dim += cfg.resolved_descriptor_hidden_dim * 4

        self.prediction_head = nn.Sequential(
            nn.Linear(pair_input_dim, 1024),
            nn.SiLU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(1024, 512),
            nn.SiLU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(512, 256),
            nn.SiLU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(256, 64),
            nn.SiLU(),
            nn.Linear(64, 1),
        )

    def set_descriptor_normalization(
        self,
        mean: Tensor | list[float],
        std: Tensor | list[float],
    ) -> None:
        """Attach precomputed descriptor normalization statistics to the model."""
        mean_arr, std_arr = validate_descriptor_normalization_stats(
            mean,
            std,
            descriptor_dim=self.cfg.descriptor_dim if self.cfg.use_descriptor_augmentation else None,
        )
        mean_tensor = torch.as_tensor(mean_arr, dtype=torch.float32)
        std_tensor = torch.as_tensor(std_arr, dtype=torch.float32)
        buffer_device = self.descriptor_mean.device
        buffer_dtype = self.descriptor_mean.dtype
        self.descriptor_mean = mean_tensor.to(
            device=buffer_device,
            dtype=buffer_dtype,
        ).clone()
        self.descriptor_std = std_tensor.clamp_min(1e-8).to(
            device=buffer_device,
            dtype=buffer_dtype,
        ).clone()

    def _normalize_descriptors(self, descriptors: Tensor) -> Tensor:
        """Normalize raw RDKit descriptors with the fitted train-set statistics."""
        if self.descriptor_adapter is None:
            raise ValueError("Descriptor augmentation is disabled for this DirectGNN instance.")
        if descriptors.size(-1) != self.cfg.descriptor_dim:
            raise ValueError(
                f"Descriptor tensor has dim {descriptors.size(-1)}, "
                f"expected {self.cfg.descriptor_dim}."
            )
        descriptors = descriptors.to(
            device=self.descriptor_mean.device,
            dtype=self.descriptor_mean.dtype,
        )
        return ((descriptors - self.descriptor_mean) / self.descriptor_std.clamp_min(1e-8)).clamp(
            min=-DESCRIPTOR_Z_CLIP,
            max=DESCRIPTOR_Z_CLIP,
        )

    def _encode_descriptors(self, descriptors: Tensor) -> Tensor:
        """Normalize and project raw RDKit descriptors into the pair space."""
        normalized = self._normalize_descriptors(descriptors)
        return self.descriptor_adapter(normalized)

    def _encode_and_readout(
        self,
        data: Batch,
        role: str = "solute",
        temp_feat: Tensor | None = None,
    ) -> tuple[Tensor, Tensor]:
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

    def _split_atoms_by_graph(self, h_atoms: Tensor, batch: Tensor) -> TensorList:
        graphs: TensorList = []
        for i in range(int(batch.max().item()) + 1):
            graphs.append(h_atoms[batch == i])
        return graphs

    def _append_global_token(
        self, atoms_list: TensorList, token: Tensor
    ) -> TensorList:
        token = token[0]
        return [torch.cat([h, token.to(h)], dim=0) for h in atoms_list]

    def _slice_padded(
        self, padded: Tensor, lengths: list[int], drop_last: bool = False
    ) -> TensorList:
        out: TensorList = []
        for i, length in enumerate(lengths):
            end = length - 1 if drop_last else length
            out.append(padded[i, :end, :])
        return out

    def _extract_tokens(self, padded: Tensor, lengths: list[int]) -> Tensor:
        idx = torch.tensor(
            [length - 1 for length in lengths], device=padded.device
        )
        return padded[torch.arange(padded.size(0), device=padded.device), idx]

    def forward(
        self,
        solute_data: Batch,
        solvent_data: Batch,
        T: Tensor,
        solvent_type: Optional[Tensor] = None,
        solute_morgan_fp: Tensor | None = None,
        solvent_morgan_fp: Tensor | None = None,
        solute_descriptors: Tensor | None = None,
        solvent_descriptors: Tensor | None = None,
        return_debug_tensors: bool = False,
    ) -> dict[str, Tensor | dict[str, Tensor]]:
        """
        Forward pass.

        Returns dict with ln_x2, x2, and optional debug tensors.
        """
        t_feat = make_temperature_features(T)
        # --- Encode both molecules ---
        h_sol_atoms, g_sol = self._encode_and_readout(
            solute_data, "solute", temp_feat=t_feat
        )
        h_slv_atoms, g_slv = self._encode_and_readout(
            solvent_data, "solvent", temp_feat=t_feat
        )
        sol_fp_emb = None
        slv_fp_emb = None
        if self.cfg.use_morgan_features:
            if solute_morgan_fp is None or solvent_morgan_fp is None:
                raise ValueError(
                    "Morgan fingerprint features are enabled in the config, "
                    "but solute_morgan_fp/solvent_morgan_fp were not provided."
                )
            sol_fp_emb = self.solute_fp_adapter(solute_morgan_fp.to(g_sol))
            slv_fp_emb = self.solvent_fp_adapter(solvent_morgan_fp.to(g_slv))
            g_sol = g_sol + self.fp_pre_scale * sol_fp_emb
            g_slv = g_slv + self.fp_pre_scale * slv_fp_emb

        # --- Cross-attention / Bipartite MP ---
        sol_list = self._split_atoms_by_graph(h_sol_atoms, solute_data.batch)
        slv_list = self._split_atoms_by_graph(h_slv_atoms, solvent_data.batch)

        sol_list = self._append_global_token(sol_list, self.sol_token)
        slv_list = self._append_global_token(slv_list, self.slv_token)
        sol_lengths = [h.shape[0] for h in sol_list]
        slv_lengths = [h.shape[0] for h in slv_list]

        h_sol_padded, sol_mask = pad_atom_features(sol_list)
        h_slv_padded, slv_mask = pad_atom_features(slv_list)

        if self.interaction_mode == "cross_attn":
            for cross_layer in self.cross_attn_layers:
                sol_prev = h_sol_padded
                slv_prev = h_slv_padded
                h_sol_padded, _ = cross_layer(
                    sol_prev, slv_prev, sol_mask, slv_mask, t_feat
                )
                h_slv_padded, _ = cross_layer(
                    slv_prev, sol_prev, slv_mask, sol_mask, t_feat
                )
        else:
            for mp_layer in self.bipartite_layers:
                h_sol_padded, h_slv_padded = mp_layer(
                    h_sol_padded, h_slv_padded, sol_mask, slv_mask, t_feat
                )

        # Post-cross-attention readout for solute
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
        if self.cfg.use_morgan_features:
            g_sol_post = g_sol_post + self.fp_post_scale * sol_fp_emb
            g_slv_post = g_slv_post + self.fp_post_scale * slv_fp_emb

        # --- Temperature encoding ---
        t_enc = self.temp_encoder.encode(T)  # (B, n_bins)

        # --- Pair features ---
        pair_input = torch.cat([
            g_sol_post,
            g_slv_post,
            g_sol_post * g_slv_post,
            (g_sol_post - g_slv_post).abs(),
            t_enc,
        ], dim=-1)
        normalized_solute_descriptors = None
        normalized_solvent_descriptors = None
        sol_desc = None
        slv_desc = None
        if self.cfg.use_descriptor_augmentation:
            if solute_descriptors is None or solvent_descriptors is None:
                raise ValueError(
                    "Descriptor augmentation is enabled in the config, "
                    "but solute_descriptors/solvent_descriptors were not provided."
                )
            normalized_solute_descriptors = self._normalize_descriptors(solute_descriptors)
            normalized_solvent_descriptors = self._normalize_descriptors(solvent_descriptors)
            sol_desc = self.descriptor_adapter(normalized_solute_descriptors).to(g_sol_post)
            slv_desc = self.descriptor_adapter(normalized_solvent_descriptors).to(g_slv_post)
            pair_input = torch.cat(
                [
                    pair_input,
                    sol_desc,
                    slv_desc,
                    sol_desc * slv_desc,
                    (sol_desc - slv_desc).abs(),
                ],
                dim=-1,
            )

        # --- Direct prediction ---
        ln_x2 = self.prediction_head(pair_input).squeeze(-1)  # (B,)

        return {
            "ln_x2": ln_x2,
            "x2": torch.exp(ln_x2).clamp(0, 1),
            **(
                {
                    "debug_tensors": {
                        "raw_solute_descriptors": solute_descriptors.detach(),
                        "raw_solvent_descriptors": solvent_descriptors.detach(),
                        "normalized_solute_descriptors": normalized_solute_descriptors.detach(),
                        "normalized_solvent_descriptors": normalized_solvent_descriptors.detach(),
                        "descriptor_embedding_solute": sol_desc.detach(),
                        "descriptor_embedding_solvent": slv_desc.detach(),
                        "pair_representation": pair_input.detach(),
                    }
                }
                if return_debug_tensors and self.cfg.use_descriptor_augmentation
                else {}
            ),
        }


# ================================================================== #
#  Trainer                                                            #
# ================================================================== #

class DirectGNNTrainer:
    """
    Trainer for DirectGNN baseline.

    Uses Huber loss on ln(x₂), same as TGNN-Solv primary loss.
    Cosine annealing LR schedule. Early stopping on val MAE.
    """

    def __init__(
        self, model: DirectGNN, device: torch.device | None = None
    ) -> None:
        self.model = model
        if device is None:
            self.device = next(model.parameters()).device
        else:
            self.device = device
        self.best_val_mae = float("inf")
        self.best_state: dict[str, Tensor] | None = None
        self.patience_counter = 0
        self.history: dict[str, list[float]] = {
            "train_loss": [],
            "val_mae": [],
            "val_r2": [],
        }
        self._cache_release_counter = 0

    def _maybe_release_device_cache(self, *, force: bool = False) -> None:
        """Periodically release MPS cached memory to reduce fragmentation."""
        if self.device.type != "mps":
            return
        self._cache_release_counter += 1
        if not force and self._cache_release_counter % 50 != 0:
            return
        gc.collect()
        if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
            torch.mps.empty_cache()

    def state_dict(self) -> DirectTrainerStateDict:
        """Serialize trainer state required for checkpointed resume."""
        best_state = None
        if self.best_state is not None:
            best_state = {
                key: value.detach().cpu().clone()
                for key, value in self.best_state.items()
            }
        return {
            "best_val_mae": self.best_val_mae,
            "best_state": best_state,
            "patience_counter": self.patience_counter,
            "history": {
                key: list(values)
                for key, values in self.history.items()
            },
        }

    def load_state_dict(self, state: DirectTrainerStateDict | None) -> None:
        """Restore trainer state from a saved checkpoint payload."""
        if not state:
            return
        self.best_val_mae = float(state.get("best_val_mae", float("inf")))
        raw_best_state = state.get("best_state")
        if isinstance(raw_best_state, dict):
            self.best_state = {
                key: value.detach().cpu().clone()
                for key, value in raw_best_state.items()
                if isinstance(value, Tensor)
            }
        else:
            self.best_state = None
        self.patience_counter = int(state.get("patience_counter", 0))
        raw_history = state.get("history")
        if isinstance(raw_history, dict):
            self.history = {
                key: [float(v) for v in values]
                for key, values in raw_history.items()
                if isinstance(values, list)
            }
            self.history.setdefault("train_loss", [])
            self.history.setdefault("val_mae", [])
            self.history.setdefault("val_r2", [])

    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        n_epochs: int = 200,
        lr: float = 1e-4,
        patience: int = 20,
        start_epoch: int = 0,
        optimizer_state_dict: dict[str, Any] | None = None,
        scheduler_state_dict: dict[str, Any] | None = None,
        on_epoch_end: Callable[[DirectResumeStateDict], None] | None = None,
    ) -> MetricDict:
        """
        Train the model. Returns dict with best_val_mae.
        """
        print("\n  Training DirectGNN...")
        n_params = sum(p.numel() for p in self.model.parameters())
        print(f"  Parameters: {n_params:,}")

        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=lr,
            weight_decay=float(self.model.cfg.direct_weight_decay),
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=n_epochs
        )
        if optimizer_state_dict is not None:
            optimizer.load_state_dict(optimizer_state_dict)
        if scheduler_state_dict is not None:
            scheduler.load_state_dict(scheduler_state_dict)

        epoch_iterable = progress(
            range(start_epoch, n_epochs),
            desc="DirectGNN epochs",
        )

        for epoch in epoch_iterable:
            # --- Train ---
            self.model.train()
            train_loss = 0.0
            n_batches = 0

            for sol_b, slv_b, tgt in progress(
                train_loader,
                desc="DirectGNN train",
                leave=False,
            ):
                sol_b = sol_b.to(self.device)
                slv_b = slv_b.to(self.device)
                T = tgt["T"].to(self.device)
                solvent_type = tgt.get("solvent_type")
                solute_morgan_fp = tgt.get("solute_morgan_fp")
                solvent_morgan_fp = tgt.get("solvent_morgan_fp")
                solute_descriptors = tgt.get("solute_descriptors")
                solvent_descriptors = tgt.get("solvent_descriptors")
                mask = tgt["has_solubility"].to(self.device)

                if not mask.any():
                    continue

                optimizer.zero_grad()
                out = self.model(
                    sol_b,
                    slv_b,
                    T,
                    solvent_type=solvent_type,
                    solute_morgan_fp=(
                        solute_morgan_fp.to(self.device)
                        if isinstance(solute_morgan_fp, Tensor)
                        else None
                    ),
                    solvent_morgan_fp=(
                        solvent_morgan_fp.to(self.device)
                        if isinstance(solvent_morgan_fp, Tensor)
                        else None
                    ),
                    solute_descriptors=(
                        solute_descriptors.to(self.device)
                        if isinstance(solute_descriptors, Tensor)
                        else None
                    ),
                    solvent_descriptors=(
                        solvent_descriptors.to(self.device)
                        if isinstance(solvent_descriptors, Tensor)
                        else None
                    ),
                )

                pred = out["ln_x2"][mask]
                true = tgt["ln_x2"].to(self.device)[mask]
                loss = nn.functional.huber_loss(pred, true, delta=1.0)

                loss.backward()
                nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    float(self.model.cfg.grad_clip),
                )
                optimizer.step()
                self._maybe_release_device_cache()

                train_loss += loss.item()
                n_batches += 1

            scheduler.step()
            avg_train = train_loss / max(n_batches, 1)
            self.history["train_loss"].append(float(avg_train))

            # --- Validate ---
            val_metrics = self._evaluate_loader(val_loader)
            self.history["val_mae"].append(float(val_metrics["mae"]))
            self.history["val_r2"].append(float(val_metrics["r2"]))

            if epoch % 20 == 0 or epoch == n_epochs - 1:
                print(
                    f"    Epoch {epoch:3d}/{n_epochs}: "
                    f"train={avg_train:.4f}, "
                    f"val_MAE={val_metrics['mae']:.3f}, "
                    f"val_R²={val_metrics['r2']:.3f}"
                )

            # --- Early stopping ---
            if val_metrics["mae"] < self.best_val_mae:
                self.best_val_mae = val_metrics["mae"]
                self.patience_counter = 0
                self.best_state = {
                    k: v.cpu().clone()
                    for k, v in self.model.state_dict().items()
                }
            else:
                self.patience_counter += 1
                if self.patience_counter >= patience:
                    print(f"    Early stopping at epoch {epoch}")
                    break

            if on_epoch_end is not None:
                on_epoch_end(
                    {
                        "status": "in_progress",
                        "next_epoch": epoch + 1,
                        "total_epochs": n_epochs,
                        "optimizer_state_dict": optimizer.state_dict(),
                        "scheduler_state_dict": scheduler.state_dict(),
                        "trainer_state_dict": self.state_dict(),
                    }
                )

        if self.best_state is not None:
            self.model.load_state_dict(self.best_state)
            print(f"  Restored best model (val MAE = {self.best_val_mae:.4f})")

        self._maybe_release_device_cache(force=True)
        return {"best_val_mae": self.best_val_mae}

    @torch.no_grad()
    def _evaluate_loader(self, loader: DataLoader) -> MetricDict:
        """Evaluate on a DataLoader, return metrics dict."""
        self.model.eval()
        all_pred, all_true = [], []

        for sol_b, slv_b, tgt in progress(
            loader,
            desc="DirectGNN eval",
            leave=False,
        ):
            sol_b = sol_b.to(self.device)
            slv_b = slv_b.to(self.device)
            T = tgt["T"].to(self.device)
            solvent_type = tgt.get("solvent_type")
            solute_morgan_fp = tgt.get("solute_morgan_fp")
            solvent_morgan_fp = tgt.get("solvent_morgan_fp")
            solute_descriptors = tgt.get("solute_descriptors")
            solvent_descriptors = tgt.get("solvent_descriptors")
            mask = tgt["has_solubility"]  # keep on CPU

            if not mask.any():
                continue

            out = self.model(
                sol_b,
                slv_b,
                T,
                solvent_type=solvent_type,
                solute_morgan_fp=(
                    solute_morgan_fp.to(self.device)
                    if isinstance(solute_morgan_fp, Tensor)
                    else None
                ),
                solvent_morgan_fp=(
                    solvent_morgan_fp.to(self.device)
                    if isinstance(solvent_morgan_fp, Tensor)
                    else None
                ),
                solute_descriptors=(
                    solute_descriptors.to(self.device)
                    if isinstance(solute_descriptors, Tensor)
                    else None
                ),
                solvent_descriptors=(
                    solvent_descriptors.to(self.device)
                    if isinstance(solvent_descriptors, Tensor)
                    else None
                ),
            )
            all_pred.append(out["ln_x2"].cpu()[mask])
            all_true.append(tgt["ln_x2"][mask])

        if not all_pred:
            return {
                "n": 0, "mae": float("inf"),
                "rmse": float("inf"), "r2": 0.0, "bias": 0.0,
            }

        pred = torch.cat(all_pred).numpy()
        true = torch.cat(all_true).numpy()
        errors = pred - true

        import numpy as np
        ss_res = (errors ** 2).sum()
        ss_tot = ((true - true.mean()) ** 2).sum()

        metrics = {
            "n": len(pred),
            "mae": float(np.abs(errors).mean()),
            "rmse": float(np.sqrt((errors ** 2).mean())),
            "r2": float(1.0 - ss_res / (ss_tot + 1e-10)),
            "bias": float(errors.mean()),
        }
        self._maybe_release_device_cache(force=True)
        return metrics

    def evaluate(self, test_loader: DataLoader) -> dict[str, float | str]:
        """Final evaluation on test set."""
        metrics = self._evaluate_loader(test_loader)
        metrics["name"] = "DirectGNN"
        return metrics
