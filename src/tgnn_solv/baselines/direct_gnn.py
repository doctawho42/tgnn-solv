"""
Direct GNN baseline: dual-graph encoder + thermometer T + MLP head.

Architecture:
  Solute graph  → GNNEncoder(role=solute)  → Readout → g_sol
  Solvent graph → GNNEncoder(role=solvent) → Readout → g_slv
  Temperature   → ThermometerEncoder → t_enc

  [g_sol || g_slv || g_sol * g_slv || |g_sol - g_slv| || t_enc]
    → MLP → ln(x₂)

Same GNN backbone as TGNN-Solv. Same cross-attention.
No physics layer, no NRTL, no SLE solver.
Pure data-driven prediction.

This is the key ablation: if TGNN-Solv does not beat this,
the physics-informed approach adds no value.
"""

from typing import Dict, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch_geometric.data import Batch

from ..config import TGNNSolvConfig
from ..features import NODE_FEAT_DIM, EDGE_FEAT_DIM
from ..layers import (
    GNNEncoder,
    SoluteSolventCrossAttention,
    PhysicsAwareReadout,
    pad_atom_features,
)
from .temperature import ThermometerEncoder


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
    ):
        super().__init__()
        self.cfg = cfg
        F = cfg.hidden_dim

        # --- Same GNN encoder (shared backbone with role adapters) ---
        self.gnn = GNNEncoder(
            node_feat_dim, edge_feat_dim,
            hidden_dim=F, n_layers=cfg.n_gnn_layers,
        )

        # --- Same cross-attention ---
        self.cross_attn_layers = nn.ModuleList([
            SoluteSolventCrossAttention(F, cfg.n_attn_heads)
            for _ in range(cfg.n_cross_attn_layers)
        ])

        # --- Same readout ---
        self.readout = PhysicsAwareReadout(F)
        D_r = self.readout.output_dim  # hidden_dim * 3

        # --- Temperature encoder ---
        self.temp_encoder = ThermometerEncoder(n_temp_bins, T_min, T_max)

        # --- Pair + temperature → prediction ---
        # Input: g_sol(D_r) + g_slv(D_r) + g_sol*g_slv(D_r) +
        #        |g_sol-g_slv|(D_r) + t_enc(n_temp_bins)
        pair_input_dim = D_r * 4 + n_temp_bins

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

    def _encode_and_readout(self, data, role="solute"):
        h_atoms = self.gnn(
            data.x, data.edge_index, data.edge_attr, role=role
        )
        g_mol = self.readout(h_atoms, data.batch)
        return h_atoms, g_mol

    def _split_atoms_by_graph(self, h_atoms, batch):
        graphs = []
        for i in range(batch.max().item() + 1):
            graphs.append(h_atoms[batch == i])
        return graphs

    def forward(
        self,
        solute_data: Batch,
        solvent_data: Batch,
        T: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass.

        Returns dict with ln_x2, x2 (for compatibility with eval code).
        """
        # --- Encode both molecules ---
        h_sol_atoms, g_sol = self._encode_and_readout(solute_data, "solute")
        h_slv_atoms, g_slv = self._encode_and_readout(solvent_data, "solvent")

        # --- Cross-attention ---
        sol_list = self._split_atoms_by_graph(h_sol_atoms, solute_data.batch)
        slv_list = self._split_atoms_by_graph(h_slv_atoms, solvent_data.batch)

        h_sol_padded, sol_mask = pad_atom_features(sol_list)
        h_slv_padded, slv_mask = pad_atom_features(slv_list)

        for cross_layer in self.cross_attn_layers:
            h_sol_padded, _ = cross_layer(
                h_sol_padded, h_slv_padded, sol_mask, slv_mask
            )

        # Post-cross-attention readout for solute
        h_sol_cross = h_sol_padded[sol_mask]
        g_sol_post = self.readout(h_sol_cross, solute_data.batch)

        # --- Temperature encoding ---
        t_enc = self.temp_encoder.encode(T)  # (B, n_bins)

        # --- Pair features ---
        pair_input = torch.cat([
            g_sol_post,
            g_slv,
            g_sol_post * g_slv,
            (g_sol_post - g_slv).abs(),
            t_enc,
        ], dim=-1)

        # --- Direct prediction ---
        ln_x2 = self.prediction_head(pair_input).squeeze(-1)  # (B,)

        return {
            "ln_x2": ln_x2,
            "x2": torch.exp(ln_x2).clamp(0, 1),
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

    def __init__(self, model: DirectGNN, device: torch.device = None):
        self.model = model
        if device is None:
            self.device = next(model.parameters()).device
        else:
            self.device = device

    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        n_epochs: int = 200,
        lr: float = 1e-4,
        patience: int = 20,
    ) -> Dict[str, float]:
        """
        Train the model. Returns dict with best_val_mae.
        """
        print(f"\n  Training DirectGNN...")
        n_params = sum(p.numel() for p in self.model.parameters())
        print(f"  Parameters: {n_params:,}")

        optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=lr, weight_decay=1e-5
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=n_epochs
        )

        best_val_mae = float("inf")
        best_state = None
        patience_counter = 0

        for epoch in range(n_epochs):
            # --- Train ---
            self.model.train()
            train_loss = 0.0
            n_batches = 0

            for sol_b, slv_b, tgt in train_loader:
                sol_b = sol_b.to(self.device)
                slv_b = slv_b.to(self.device)
                T = tgt["T"].to(self.device)
                mask = tgt["has_solubility"].to(self.device)

                if not mask.any():
                    continue

                optimizer.zero_grad()
                out = self.model(sol_b, slv_b, T)

                pred = out["ln_x2"][mask]
                true = tgt["ln_x2"].to(self.device)[mask]
                loss = nn.functional.huber_loss(pred, true, delta=1.0)

                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()

                train_loss += loss.item()
                n_batches += 1

            scheduler.step()
            avg_train = train_loss / max(n_batches, 1)

            # --- Validate ---
            val_metrics = self._evaluate_loader(val_loader)

            if epoch % 20 == 0 or epoch == n_epochs - 1:
                print(
                    f"    Epoch {epoch:3d}/{n_epochs}: "
                    f"train={avg_train:.4f}, "
                    f"val_MAE={val_metrics['mae']:.3f}, "
                    f"val_R²={val_metrics['r2']:.3f}"
                )

            # --- Early stopping ---
            if val_metrics["mae"] < best_val_mae:
                best_val_mae = val_metrics["mae"]
                patience_counter = 0
                best_state = {
                    k: v.cpu().clone()
                    for k, v in self.model.state_dict().items()
                }
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"    Early stopping at epoch {epoch}")
                    break

        if best_state is not None:
            self.model.load_state_dict(best_state)
            print(f"  Restored best model (val MAE = {best_val_mae:.4f})")

        return {"best_val_mae": best_val_mae}

    @torch.no_grad()
    def _evaluate_loader(self, loader: DataLoader) -> Dict[str, float]:
        """Evaluate on a DataLoader, return metrics dict."""
        self.model.eval()
        all_pred, all_true = [], []

        for sol_b, slv_b, tgt in loader:
            sol_b = sol_b.to(self.device)
            slv_b = slv_b.to(self.device)
            T = tgt["T"].to(self.device)
            mask = tgt["has_solubility"]  # keep on CPU

            if not mask.any():
                continue

            out = self.model(sol_b, slv_b, T)
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

        return {
            "n": len(pred),
            "mae": float(np.abs(errors).mean()),
            "rmse": float(np.sqrt((errors ** 2).mean())),
            "r2": float(1.0 - ss_res / (ss_tot + 1e-10)),
            "bias": float(errors.mean()),
        }

    def evaluate(self, test_loader: DataLoader) -> Dict[str, float]:
        """Final evaluation on test set."""
        metrics = self._evaluate_loader(test_loader)
        metrics["name"] = "DirectGNN"
        return metrics