"""
Three-phase curriculum trainer for TGNN-Solv.

Phase 1 — Property pretraining (no solubility loss):
  Train heads to predict T_m, ΔH_fus, Hansen, γ∞.
  Correction gate frozen at 0.

Phase 2 — Full SLE training:
  Add solubility loss.  Correction gate unfrozen after epoch 50.
  Early stopping on validation MAE.

Phase 3 — Fine-tuning with monotonicity:
  Lower LR. Stronger monotonicity and correction penalties.
  Restores best model at the end.
"""

from __future__ import annotations

import math
from typing import TypeAlias

import torch
from torch import Tensor
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader
from torch_geometric.data import Batch

from .config import TGNNSolvConfig
from .data.solvent_types import SOLVENT_TYPE_OTHER_ID
from .layers import make_temperature_features
from .model import TGNNSolv
from .loss import TGNNSolvLoss
from .progress import progress, trange

HistoryDict: TypeAlias = dict[str, list[float | int]]
MetricDict: TypeAlias = dict[str, float]
ModelOutput: TypeAlias = dict[str, object]

DEFAULT_PHASE_WEIGHTS = {
    1: {
        "sol": 0.0, "T_m": 1.0, "dH": 1.0, "hansen": 1.0,
        "gamma_inf": 1.0,
        "mono": 0.0, "res": 0.0, "bridge": 0.0, "tau_reg": 0.0,
        "phys_pref": 0.0, "direct_reg": 0.0, "direct_nll": 0.0,
        "pair_temp_rank": 0.0, "vant_hoff_local": 0.0,
        "moe_balance": 0.0,
    },
    2: {
        "sol": 1.0, "T_m": 0.3, "dH": 0.3, "hansen": 0.2,
        "gamma_inf": 0.5,
        "mono": 0.0, "res": 0.03, "bridge": 0.05,
        "tau_reg": 0.01,
        "phys_pref": 0.05,
        "direct_reg": 0.05,
        "direct_nll": 0.05,
        "pair_temp_rank": 0.02,
        "vant_hoff_local": 0.01,
        "moe_balance": 0.02,
    },
    3: {
        "sol": 1.0, "T_m": 0.2, "dH": 0.2, "hansen": 0.1,
        "gamma_inf": 0.3,
        "mono": 0.3, "res": 0.05, "bridge": 0.1,
        "tau_reg": 0.01,
        "phys_pref": 0.03,
        "direct_reg": 0.05,
        "direct_nll": 0.05,
        "pair_temp_rank": 0.05,
        "vant_hoff_local": 0.03,
        "moe_balance": 0.03,
    },
}

class TGNNSolvTrainer:
    """Curriculum trainer with three phases."""

    def __init__(self, model: TGNNSolv, cfg: TGNNSolvConfig) -> None:
        self.model = model
        self.cfg = cfg
        self.loss_fn = TGNNSolvLoss(cfg)
        self.device = next(model.parameters()).device

        self.phase_weights = {
            phase: self._get_phase_weights(phase)
            for phase in (1, 2, 3)
        }

        # Training history
        self.history: HistoryDict = {
            "train_loss": [],
            "val_loss": [],
            "val_mae": [],
            "val_rmse": [],
            "gate": [],
            "phase": [],
        }
        self.best_val_loss = float("inf")
        self.best_state = None
        self.patience_counter = 0

    def _get_phase_weights(self, phase: int) -> dict:
        """Return loss weights for a phase, merging config overrides
        onto hardcoded defaults.

        If ``cfg.phase{N}_loss_weights`` is ``None``, the full default
        dict is used.  If it is a partial dict, only the provided keys
        override the defaults — missing keys keep their default values.
        """
        defaults = DEFAULT_PHASE_WEIGHTS[phase].copy()
        overrides = {
            1: self.cfg.phase1_loss_weights,
            2: self.cfg.phase2_loss_weights,
            3: self.cfg.phase3_loss_weights,
        }.get(phase)
        if overrides is not None:
            defaults.update(overrides)
        return defaults

    # -------------------------------------------------------------- #
    #  Optimizer / scheduler                                          #
    # -------------------------------------------------------------- #

    def _build_optimizer(self, phase: int) -> AdamW:
        lr = {
            1: self.cfg.lr_phase1,
            2: self.cfg.lr_phase2,
            3: self.cfg.lr_phase3,
        }[phase]
        return AdamW(
            self.model.parameters(),
            lr=lr,
            weight_decay=5e-4,  # Slightly stronger regularization for stability.
            betas=(0.9, 0.999),
        )

    def _build_scheduler(
        self, optimizer: AdamW, phase: int, n_epochs: int
    ) -> LambdaLR:
        warmup = self.cfg.warmup_epochs

        def lr_lambda(epoch: int) -> float:
            if epoch < warmup:
                return epoch / max(warmup, 1)
            progress = (epoch - warmup) / max(n_epochs - warmup, 1)
            return 0.5 * (1.0 + math.cos(math.pi * progress))

        return LambdaLR(optimizer, lr_lambda)

    # -------------------------------------------------------------- #
    #  Correction gate control                                        #
    # -------------------------------------------------------------- #

    def _freeze_correction(self, freeze: bool) -> None:
        """Freeze or unfreeze the adaptive correction."""
        for p in self.model.correction.parameters():
            p.requires_grad = not freeze
        if freeze:
            # Reset confidence to high (physics-first)
            with torch.no_grad():
                self.model.correction.confidence_net[-1].bias.fill_(2.2)

    def _has_phase1_supervision(
        self, targets: dict[str, Tensor | object]
    ) -> bool:
        """Return whether a batch contains any Phase 1 auxiliary labels."""
        for key in ("T_m_mask", "dH_mask", "hansen_mask", "gamma_mask"):
            mask = targets.get(key)
            if isinstance(mask, Tensor) and bool(mask.any().item()):
                return True
        return False

    # -------------------------------------------------------------- #
    #  Phase 1 forward (no SLE solve)                                 #
    # -------------------------------------------------------------- #

    def _forward_phase1(
        self,
        sol_batch: Batch,
        slv_batch: Batch,
        T: Tensor,
        solvent_type: Tensor | None = None,
    ) -> ModelOutput:
        """
        Lightweight forward for Phase 1: encode + heads only.

        Skips cross-attention and SLE solver.  Computes ln(γ∞)
        directly for the IDAC loss.
        """
        model = self.model

        t_feat = make_temperature_features(T)
        encoder_t_feat = model._encoder_temp_features(t_feat)
        nrtl_t_feat = model._nrtl_temp_features(t_feat)

        # Encode without leaking temperature into crystal-property heads unless requested.
        _, g_sol = model._encode_and_readout(
            sol_batch, "solute", temp_feat=encoder_t_feat
        )
        _, g_slv = model._encode_and_readout(
            slv_batch, "solvent", temp_feat=encoder_t_feat
        )
        g_pair = model.pair_repr(g_sol, g_slv)
        if model.solvent_moe is not None:
            if solvent_type is None:
                solvent_type = torch.full(
                    (g_pair.shape[0],),
                    SOLVENT_TYPE_OTHER_ID,
                    device=g_pair.device,
                    dtype=torch.long,
                )
            else:
                solvent_type = solvent_type.to(g_pair.device)
            g_pair, _ = model.solvent_moe(g_pair, solvent_type)

        # Heads
        fusion_params = model.head_fusion(g_sol)
        nrtl_params = model.head_nrtl(g_pair, temp_feat=nrtl_t_feat)
        hansen_sol = model.head_hansen(g_sol)
        hansen_slv = model.head_hansen(g_slv)

        # ln(γ∞) from NRTL params directly
        nrtl = model.sle_solver.nrtl_layer
        tau_12, tau_21, G_12, G_21 = nrtl.compute_tau_G_from_params(
            nrtl_params,
            T,
        )
        lng_inf = nrtl.ln_gamma_inf(tau_12, tau_21, G_21)

        B = T.shape[0]
        dummy = torch.zeros(B, device=T.device)

        return {
            "ln_x2": dummy,
            "fusion_params": fusion_params,
            "nrtl_params": nrtl_params,
            "hansen_sol": hansen_sol,
            "hansen_slv": hansen_slv,
            "physics": {
                "ln_gamma_inf": lng_inf,
                "tau_12": tau_12,
                "tau_21": tau_21,
            },
            "correction": dummy,
            "gate": torch.tensor(0.0, device=T.device),
        }

    # -------------------------------------------------------------- #
    #  Train one epoch                                                #
    # -------------------------------------------------------------- #

    def train_epoch(
        self,
        loader: DataLoader,
        optimizer: AdamW,
        phase: int,
        epoch: int,
        compute_mono: bool = False,
    ) -> tuple[float, MetricDict]:
        """Train for one epoch. Returns avg loss and component dict."""
        self.model.train()
        total_loss = 0.0
        n_batches = 0
        loss_accum = {}

        weights = self.phase_weights[phase].copy()

        # Unfreeze correction mid-Phase 2
        if phase == 2 and epoch >= 20:
            self._freeze_correction(False)

        for sol_batch, slv_batch, targets in progress(
            loader,
            desc=f"Phase {phase} train",
            leave=False,
        ):
            sol_batch = sol_batch.to(self.device)
            slv_batch = slv_batch.to(self.device)
            targets = {
                k: v.to(self.device) if isinstance(v, torch.Tensor) else v
                for k, v in targets.items()
            }
            T = targets["T"]
            solvent_type = targets.get("solvent_type")

            if phase == 1 and not self._has_phase1_supervision(targets):
                continue

            optimizer.zero_grad()

            if phase == 1:
                output = self._forward_phase1(
                    sol_batch, slv_batch, T, solvent_type
                )
            else:
                output = self.model(
                    sol_batch, slv_batch, T, solvent_type=solvent_type
                )

            loss, loss_dict = self.loss_fn(
                output, targets, weights=weights,
                compute_mono=(compute_mono and phase >= 2),
                T=T,
                model=self.model if compute_mono else None,
                solute_data=sol_batch,
                solvent_data=slv_batch,
                solvent_type=solvent_type,
            )

            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(), self.cfg.grad_clip,
            )
            optimizer.step()

            total_loss += loss.item()
            n_batches += 1
            for k, v in loss_dict.items():
                loss_accum[k] = loss_accum.get(k, 0.0) + v
            # Track confidence for logging
            if "confidence" in output:
                self._last_confidence = output["confidence"].mean().item()
            elif hasattr(self.model.correction, "w0"):
                self._last_confidence = self.model.correction.w0.item()

        avg_loss = total_loss / max(n_batches, 1)
        avg_components = {
            k: v / max(n_batches, 1) for k, v in loss_accum.items()
        }
        return avg_loss, avg_components

    # -------------------------------------------------------------- #
    #  Validation                                                     #
    # -------------------------------------------------------------- #

    @torch.no_grad()
    def validate(
        self, loader: DataLoader, phase: int
    ) -> MetricDict:
        """Validate and return metrics dict."""
        self.model.eval()
        total_loss = 0.0
        all_pred, all_true = [], []
        n_batches = 0

        weights = self.phase_weights[phase]

        for sol_batch, slv_batch, targets in progress(
            loader,
            desc=f"Phase {phase} val",
            leave=False,
        ):
            sol_batch = sol_batch.to(self.device)
            slv_batch = slv_batch.to(self.device)
            targets = {
                k: v.to(self.device) if isinstance(v, torch.Tensor) else v
                for k, v in targets.items()
            }
            T = targets["T"]
            solvent_type = targets.get("solvent_type")

            if phase == 1 and not self._has_phase1_supervision(targets):
                continue

            if phase == 1:
                output = self._forward_phase1(
                    sol_batch, slv_batch, T, solvent_type
                )
            else:
                output = self.model(
                    sol_batch, slv_batch, T, solvent_type=solvent_type
                )

            loss, _ = self.loss_fn(output, targets, weights=weights)
            total_loss += loss.item()
            n_batches += 1

            # Collect predictions for solubility metrics (Phase 2+)
            if phase >= 2:
                sol_mask = targets.get("has_solubility")
                if sol_mask is not None and sol_mask.any():
                    all_pred.append(output["ln_x2"][sol_mask].cpu())
                    all_true.append(targets["ln_x2"][sol_mask].cpu())

        avg_loss = total_loss / max(n_batches, 1)
        metrics = {"val_loss": avg_loss}

        if all_pred:
            pred = torch.cat(all_pred)
            true = torch.cat(all_true)
            metrics["mae"] = (pred - true).abs().mean().item()
            metrics["rmse"] = (pred - true).pow(2).mean().sqrt().item()
            r2_num = (pred - true).pow(2).sum()
            r2_den = (true - true.mean()).pow(2).sum()
            metrics["r2"] = 1.0 - (r2_num / (r2_den + 1e-8)).item()

        return metrics

    # -------------------------------------------------------------- #
    #  Train one phase                                                #
    # -------------------------------------------------------------- #

    def train_phase(
        self,
        phase: int,
        train_loader: DataLoader,
        val_loader: DataLoader,
        n_epochs: int,
    ) -> None:
        """Run a single training phase."""
        print(f"\n{'=' * 60}")
        print(f"Phase {phase}: {n_epochs} epochs")
        active = {k: v for k, v in self.phase_weights[phase].items() if v > 0}
        print(f"Active losses: {active}")
        print(f"{'=' * 60}")

        # Reset early stopping between phases
        self.patience_counter = 0
        if phase >= 2:
            self.best_val_loss = float("inf")

        # Freeze correction in Phase 1 and early Phase 2
        if phase == 1:
            self._freeze_correction(True)
        elif phase == 2:
            self._freeze_correction(True)
        else:
            self._freeze_correction(False)

        optimizer = self._build_optimizer(phase)
        scheduler = self._build_scheduler(optimizer, phase, n_epochs)

        for epoch in trange(n_epochs, desc=f"Phase {phase} epochs"):
            compute_mono = phase >= 2 and epoch % 5 == 0

            train_loss, train_comp = self.train_epoch(
                train_loader, optimizer, phase, epoch, compute_mono,
            )
            val_metrics = self.validate(val_loader, phase)
            scheduler.step()

            # Record history
            self.history["train_loss"].append(train_loss)
            self.history["val_loss"].append(val_metrics["val_loss"])
            self.history["phase"].append(phase)
            if "mae" in val_metrics:
                self.history["val_mae"].append(val_metrics["mae"])
            gate_val = getattr(self, '_last_confidence', 0.0)
            self.history["gate"].append(gate_val)

            # Logging
            if epoch % 10 == 0 or epoch == n_epochs - 1:
                log = (
                    f"  Epoch {epoch:3d}/{n_epochs}: "
                    f"train={train_loss:.4f}, "
                    f"val={val_metrics['val_loss']:.4f}"
                )
                if "mae" in val_metrics:
                    log += f", MAE={val_metrics['mae']:.3f}"
                    log += f", R²={val_metrics.get('r2', 0):.3f}"
                log += (
                    f", gate={torch.tanh(torch.tensor(gate_val)).item():.3f}"
                )
                # Top 3 loss components
                top = sorted(
                    train_comp.items(), key=lambda x: x[1], reverse=True
                )[:3]
                log += " [" + ", ".join(f"{k}={v:.3f}" for k, v in top) + "]"
                print(log)

            # Early stopping (Phase 2+)
            if phase >= 2:
                criterion = val_metrics.get("mae", val_metrics["val_loss"])
                if criterion < self.best_val_loss:
                    self.best_val_loss = criterion
                    self.patience_counter = 0
                    self.best_state = {
                        k: v.cpu().clone()
                        for k, v in self.model.state_dict().items()
                    }
                else:
                    self.patience_counter += 1
                    if self.patience_counter >= self.cfg.patience:
                        print(f"  Early stopping at epoch {epoch}")
                        break

    # -------------------------------------------------------------- #
    #  Full training pipeline                                         #
    # -------------------------------------------------------------- #

    def train_full(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> None:
        """Run all three training phases sequentially."""
        self.train_phase(1, train_loader, val_loader, self.cfg.epochs_phase1)
        self.train_phase(2, train_loader, val_loader, self.cfg.epochs_phase2)
        self.train_phase(3, train_loader, val_loader, self.cfg.epochs_phase3)

        if self.best_state is not None:
            self.model.load_state_dict(self.best_state)
            print(
                f"\nRestored best model (val MAE = {self.best_val_loss:.4f})"
            )
