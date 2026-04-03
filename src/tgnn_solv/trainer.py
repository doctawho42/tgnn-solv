"""
Three-phase curriculum trainer for TGNN-Solv.

Phase 1 — Property pretraining (no solubility loss):
  Train heads to predict T_m, ΔH_fus, Hansen, γ∞.
  Correction gate frozen at 0.

Phase 2 — Full SLE training:
  Add solubility loss. Correction gate unfreezes via
  cfg.phase2_correction_unfreeze_epoch (default: 20).
  Early stopping on validation MAE.

Phase 3 — Fine-tuning with monotonicity:
  Lower LR. Stronger monotonicity and correction penalties.
  Restores best model at the end.
"""

from __future__ import annotations

import gc
import logging
import math
from typing import Callable, TypeAlias

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
from .progress import progress

HistoryDict: TypeAlias = dict[str, list[float | int]]
MetricDict: TypeAlias = dict[str, float]
ModelOutput: TypeAlias = dict[str, object]
TrainerStateDict: TypeAlias = dict[str, object]
ResumeStateDict: TypeAlias = dict[str, object]
TrainEpochStats: TypeAlias = dict[str, object]

LOGGER = logging.getLogger(__name__)

DEFAULT_PHASE_WEIGHTS = {
    1: {
        "sol": 0.0, "T_m": 1.0, "dH": 1.0, "hansen": 1.0,
        "gamma_inf": 1.0,
        "mono": 0.0, "res": 0.0, "bridge": 0.0, "tau_reg": 0.0,
        "phys_pref": 0.0, "direct_reg": 0.0, "direct_nll": 0.0,
        "pair_temp_rank": 0.0, "vant_hoff_local": 0.0,
        "moe_balance": 0.0, "descriptor_prior": 0.0, "group_prior": 0.0,
    },
    2: {
        "sol": 1.0, "T_m": 0.05, "dH": 0.05, "hansen": 0.05,
        "gamma_inf": 0.1,
        "mono": 0.0, "res": 0.01, "bridge": 0.0,
        "tau_reg": 0.002,
        "phys_pref": 0.01,
        "direct_reg": 0.01,
        "direct_nll": 0.01,
        "pair_temp_rank": 0.005,
        "vant_hoff_local": 0.001,
        "moe_balance": 0.005,
        "descriptor_prior": 0.0,
        "group_prior": 0.0,
    },
    3: {
        "sol": 1.0, "T_m": 0.03, "dH": 0.03, "hansen": 0.03,
        "gamma_inf": 0.05,
        "mono": 0.1, "res": 0.02, "bridge": 0.0,
        "tau_reg": 0.002,
        "phys_pref": 0.01,
        "direct_reg": 0.02,
        "direct_nll": 0.02,
        "pair_temp_rank": 0.01,
        "vant_hoff_local": 0.001,
        "moe_balance": 0.01,
        "descriptor_prior": 0.0,
        "group_prior": 0.0,
    },
}

class TGNNSolvTrainer:
    """Curriculum trainer with three phases."""

    def __init__(self, model: TGNNSolv, cfg: TGNNSolvConfig) -> None:
        self.model = model
        self.cfg = cfg
        self.loss_fn = TGNNSolvLoss(cfg)
        self.device = next(model.parameters()).device
        self._base_oracle_injection_prob = cfg.oracle_injection_prob

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
        self._last_confidence = 0.0
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

    def _effective_loss_weight(
        self,
        loss_name: str,
        weights: dict[str, float],
    ) -> float:
        """Resolve the effective scalar weight for a loss component."""
        if loss_name == "walden":
            if self.cfg.use_walden_check and self.cfg.walden_weight > 0:
                return float(self.cfg.walden_weight)
            return 0.0
        return float(weights.get(loss_name, 0.0))

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
        bridge_explicitly_overridden = (
            overrides is not None and "bridge" in overrides
        )
        if overrides is not None:
            defaults.update(overrides)
        if not bridge_explicitly_overridden:
            defaults["bridge"] = self.cfg.bridge_loss_weight
        if phase >= 2 and self.cfg.descriptor_prior_reg_weight > 0:
            defaults["descriptor_prior"] = self.cfg.descriptor_prior_reg_weight
        if phase >= 2 and self.cfg.group_prior_reg_weight > 0:
            defaults["group_prior"] = self.cfg.group_prior_reg_weight
        return defaults

    def state_dict(self) -> TrainerStateDict:
        """Serialize trainer state required for checkpointed resume."""
        return {
            "history": self.history,
            "best_val_loss": self.best_val_loss,
            "best_state": self.best_state,
            "patience_counter": self.patience_counter,
            "last_confidence": self._last_confidence,
            "base_oracle_injection_prob": self._base_oracle_injection_prob,
            "current_oracle_injection_prob": self.cfg.oracle_injection_prob,
        }

    def load_state_dict(self, state: TrainerStateDict | None) -> None:
        """Restore trainer state from a checkpoint payload."""
        if not state:
            return

        history = state.get("history")
        if isinstance(history, dict):
            self.history = {
                str(key): list(value)
                for key, value in history.items()
            }
        self.best_val_loss = float(state.get("best_val_loss", self.best_val_loss))
        self.best_state = state.get("best_state")
        self.patience_counter = int(state.get("patience_counter", 0))
        self._last_confidence = float(state.get("last_confidence", 0.0))
        self._base_oracle_injection_prob = float(
            state.get(
                "base_oracle_injection_prob",
                self._base_oracle_injection_prob,
            )
        )
        current_oracle_prob = float(
            state.get(
                "current_oracle_injection_prob",
                self.cfg.oracle_injection_prob,
            )
        )
        self.cfg.oracle_injection_prob = current_oracle_prob
        self.model.cfg.oracle_injection_prob = current_oracle_prob

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

    def _set_oracle_injection_prob(self, phase: int, epoch: int, n_epochs: int) -> None:
        """Update oracle-injection probability according to the training schedule."""
        if not self.cfg.use_oracle_injection:
            return

        prob = self._base_oracle_injection_prob
        if phase == 2:
            anneal_epochs = min(50, n_epochs)
            anneal_start = max(n_epochs - anneal_epochs, 0)
            if epoch >= anneal_start:
                frac = (epoch - anneal_start + 1) / max(anneal_epochs, 1)
                prob = self._base_oracle_injection_prob * (1.0 - frac)
        elif phase >= 3:
            prob = 0.0

        prob = min(max(float(prob), 0.0), self._base_oracle_injection_prob)
        self.cfg.oracle_injection_prob = prob
        self.model.cfg.oracle_injection_prob = prob

    def _set_gc_prior_residual_freeze(self, phase: int, epoch: int) -> None:
        """Freeze GC crystal residual branches for the configured early Phase 1 window."""
        if not self.cfg.use_gc_priors_crystal:
            return
        freeze_epochs = max(int(self.cfg.gc_prior_residual_freeze_epochs), 0)
        frozen = phase == 1 and epoch < freeze_epochs
        self.model.fusion_head.set_residual_frozen(frozen)

    # -------------------------------------------------------------- #
    #  Phase 1 forward (no SLE solve)                                 #
    # -------------------------------------------------------------- #

    def _forward_phase1(
        self,
        sol_batch: Batch,
        slv_batch: Batch,
        T: Tensor,
        solvent_type: Tensor | None = None,
        solute_morgan_fp: Tensor | None = None,
        solvent_morgan_fp: Tensor | None = None,
        solute_descriptor_prior_features: Tensor | None = None,
        solvent_descriptor_prior_features: Tensor | None = None,
        solute_group_prior_features: Tensor | None = None,
        solvent_group_prior_features: Tensor | None = None,
        T_m_gc: Tensor | None = None,
        dH_fus_gc: Tensor | None = None,
        dCp_fus_gc: Tensor | None = None,
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
        if model.cfg.use_morgan_features:
            if solute_morgan_fp is None or solvent_morgan_fp is None:
                raise ValueError(
                    "Morgan fingerprint features are enabled, but the batch does not "
                    "provide solute_morgan_fp/solvent_morgan_fp."
                )
            sol_fp_emb = model.solute_fp_adapter(solute_morgan_fp.to(g_sol))
            slv_fp_emb = model.solvent_fp_adapter(solvent_morgan_fp.to(g_slv))
            g_sol = g_sol + model.fp_pre_scale * sol_fp_emb
            g_slv = g_slv + model.fp_pre_scale * slv_fp_emb
        sol_prior = None
        slv_prior = None
        if model.cfg.use_descriptor_priors:
            sol_prior, slv_prior = model._require_descriptor_prior_features(
                solute_descriptor_prior_features,
                solvent_descriptor_prior_features,
            )
            sol_prior = sol_prior.to(g_sol)
            slv_prior = slv_prior.to(g_slv)
        elif model.cfg.use_group_priors:
            sol_prior, slv_prior = model._require_group_prior_features(
                solute_group_prior_features,
                solvent_group_prior_features,
            )
            sol_prior = sol_prior.to(g_sol)
            slv_prior = slv_prior.to(g_slv)
        if model.cfg.use_gc_priors_crystal:
            T_m_gc, dH_fus_gc, dCp_fus_gc = model._require_crystal_gc_priors(
                T_m_gc,
                dH_fus_gc,
                dCp_fus_gc,
            )
            T_m_gc = model._calibrate_gc_tm_prior(T_m_gc.to(g_sol))
            dH_fus_gc = dH_fus_gc.to(g_sol)
            dCp_fus_gc = dCp_fus_gc.to(g_sol)
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
        fusion_params = model.head_fusion(
            g_sol,
            T_m_gc=T_m_gc,
            dH_fus_gc=dH_fus_gc,
            dCp_fus_gc=dCp_fus_gc,
        )
        nrtl_params = model.head_nrtl(g_pair, temp_feat=nrtl_t_feat)
        hansen_sol_parts = model.head_hansen(
            g_sol,
            prior_features=sol_prior,
            return_parts=(model.cfg.use_descriptor_priors or model.cfg.use_group_priors),
        )
        hansen_slv_parts = model.head_hansen(
            g_slv,
            prior_features=slv_prior,
            return_parts=(model.cfg.use_descriptor_priors or model.cfg.use_group_priors),
        )
        aux_sol_parts = model.head_aux(
            g_sol,
            prior_features=sol_prior,
            return_parts=(model.cfg.use_descriptor_priors or model.cfg.use_group_priors),
        )
        aux_slv_parts = model.head_aux(
            g_slv,
            prior_features=slv_prior,
            return_parts=(model.cfg.use_descriptor_priors or model.cfg.use_group_priors),
        )
        hansen_sol = (
            hansen_sol_parts["value"]
            if isinstance(hansen_sol_parts, dict)
            else hansen_sol_parts
        )
        hansen_slv = (
            hansen_slv_parts["value"]
            if isinstance(hansen_slv_parts, dict)
            else hansen_slv_parts
        )

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
            "aux_sol": {"V_m": aux_sol_parts["V_m"]},
            "aux_slv": {"V_m": aux_slv_parts["V_m"]},
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
    ) -> tuple[float, TrainEpochStats]:
        """Train for one epoch and summarize raw/weighted loss components."""
        self.model.train()
        total_loss = 0.0
        n_batches = 0
        loss_accum: dict[str, float] = {}
        weighted_loss_accum: dict[str, float] = {}
        sol_fraction_accum = 0.0
        sol_fraction_count = 0
        sol_fraction_min: float | None = None
        regularizer_domination_count = 0
        max_regularizer_ratio: float | None = None

        weights = self.phase_weights[phase].copy()

        # Unfreeze correction mid-Phase 2
        if phase == 2 and epoch >= self.cfg.phase2_correction_unfreeze_epoch:
            self._freeze_correction(False)

        for batch_idx, (sol_batch, slv_batch, targets) in enumerate(
            progress(
                loader,
                desc=f"Phase {phase} train",
                leave=False,
            ),
            start=1,
        ):
            sol_batch = sol_batch.to(self.device)
            slv_batch = slv_batch.to(self.device)
            targets = {
                k: v.to(self.device) if isinstance(v, torch.Tensor) else v
                for k, v in targets.items()
            }
            T = targets["T"]
            solvent_type = targets.get("solvent_type")
            solute_morgan_fp = targets.get("solute_morgan_fp")
            solvent_morgan_fp = targets.get("solvent_morgan_fp")
            solute_descriptor_prior_features = targets.get(
                "solute_descriptor_prior_features"
            )
            solvent_descriptor_prior_features = targets.get(
                "solvent_descriptor_prior_features"
            )
            solute_group_prior_features = targets.get(
                "solute_group_prior_features"
            )
            solvent_group_prior_features = targets.get(
                "solvent_group_prior_features"
            )
            T_m_gc = targets.get("T_m_gc")
            dH_fus_gc = targets.get("dH_fus_gc")
            dCp_fus_gc = targets.get("dCp_fus_gc")

            if phase == 1 and not self._has_phase1_supervision(targets):
                continue

            optimizer.zero_grad()

            if phase == 1:
                output = self._forward_phase1(
                    sol_batch,
                    slv_batch,
                    T,
                    solvent_type,
                    solute_morgan_fp=solute_morgan_fp,
                    solvent_morgan_fp=solvent_morgan_fp,
                    solute_descriptor_prior_features=solute_descriptor_prior_features,
                    solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                    solute_group_prior_features=solute_group_prior_features,
                    solvent_group_prior_features=solvent_group_prior_features,
                    T_m_gc=T_m_gc,
                    dH_fus_gc=dH_fus_gc,
                    dCp_fus_gc=dCp_fus_gc,
                )
            else:
                output = self.model(
                    sol_batch,
                    slv_batch,
                    T,
                    solvent_type=solvent_type,
                    solute_morgan_fp=solute_morgan_fp,
                    solvent_morgan_fp=solvent_morgan_fp,
                    solute_descriptor_prior_features=solute_descriptor_prior_features,
                    solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                    solute_group_prior_features=solute_group_prior_features,
                    solvent_group_prior_features=solvent_group_prior_features,
                    T_m_gc=T_m_gc,
                    dH_fus_gc=dH_fus_gc,
                    dCp_fus_gc=dCp_fus_gc,
                    targets=targets,
                )

            loss, loss_dict = self.loss_fn(
                output, targets, weights=weights,
                compute_mono=(compute_mono and phase >= 2),
                T=T,
                model=self.model if compute_mono else None,
                solute_data=sol_batch,
                solvent_data=slv_batch,
                solvent_type=solvent_type,
                solute_morgan_fp=solute_morgan_fp,
                solvent_morgan_fp=solvent_morgan_fp,
                solute_descriptor_prior_features=solute_descriptor_prior_features,
                solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                solute_group_prior_features=solute_group_prior_features,
                solvent_group_prior_features=solvent_group_prior_features,
                T_m_gc=T_m_gc,
                dH_fus_gc=dH_fus_gc,
                dCp_fus_gc=dCp_fus_gc,
            )

            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(), self.cfg.grad_clip,
            )
            optimizer.step()
            self._maybe_release_device_cache()

            total_loss += loss.item()
            n_batches += 1
            for k, v in loss_dict.items():
                raw_value = float(v)
                loss_accum[k] = loss_accum.get(k, 0.0) + raw_value
                weighted_loss_accum[k] = (
                    weighted_loss_accum.get(k, 0.0)
                    + self._effective_loss_weight(k, weights) * raw_value
                )

            total_loss_value = float(loss.item())
            sol_weight = self._effective_loss_weight("sol", weights)
            sol_weighted = sol_weight * float(loss_dict.get("sol", 0.0))
            if total_loss_value > 0.0 and sol_weight > 0.0 and "sol" in loss_dict:
                sol_fraction = sol_weighted / total_loss_value
                sol_fraction_accum += sol_fraction
                sol_fraction_count += 1
                if sol_fraction_min is None:
                    sol_fraction_min = sol_fraction
                else:
                    sol_fraction_min = min(sol_fraction_min, sol_fraction)

            if sol_weighted > 0.0:
                regularizer_ratio = total_loss_value / max(sol_weighted, 1.0e-12)
                if max_regularizer_ratio is None:
                    max_regularizer_ratio = regularizer_ratio
                else:
                    max_regularizer_ratio = max(max_regularizer_ratio, regularizer_ratio)
                if total_loss_value > 10.0 * sol_weighted:
                    regularizer_domination_count += 1
                    if regularizer_domination_count <= 3:
                        LOGGER.warning(
                            "Regularizer domination detected: total=%.1f, sol=%.1f. "
                            "Consider reducing regularizer weights. "
                            "phase=%d epoch=%d batch=%d",
                            total_loss_value,
                            sol_weighted,
                            phase,
                            epoch,
                            batch_idx,
                        )
            # Track confidence for logging
            if "confidence" in output:
                self._last_confidence = output["confidence"].mean().item()
            elif hasattr(self.model.correction, "w0"):
                self._last_confidence = self.model.correction.w0.item()

        avg_loss = total_loss / max(n_batches, 1)
        avg_raw_components = {
            k: v / max(n_batches, 1) for k, v in loss_accum.items()
        }
        avg_weighted_components = {
            k: v / max(n_batches, 1) for k, v in weighted_loss_accum.items()
        }
        self._maybe_release_device_cache(force=True)
        return avg_loss, {
            "raw": avg_raw_components,
            "weighted": avg_weighted_components,
            "weights": {
                key: self._effective_loss_weight(key, weights)
                for key in avg_raw_components
            },
            "sol_fraction": (
                sol_fraction_accum / sol_fraction_count
                if sol_fraction_count > 0
                else None
            ),
            "sol_fraction_min": sol_fraction_min,
            "regularizer_domination_count": regularizer_domination_count,
            "max_regularizer_ratio": max_regularizer_ratio,
        }

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
            solute_morgan_fp = targets.get("solute_morgan_fp")
            solvent_morgan_fp = targets.get("solvent_morgan_fp")
            solute_descriptor_prior_features = targets.get(
                "solute_descriptor_prior_features"
            )
            solvent_descriptor_prior_features = targets.get(
                "solvent_descriptor_prior_features"
            )
            solute_group_prior_features = targets.get(
                "solute_group_prior_features"
            )
            solvent_group_prior_features = targets.get(
                "solvent_group_prior_features"
            )
            T_m_gc = targets.get("T_m_gc")
            dH_fus_gc = targets.get("dH_fus_gc")
            dCp_fus_gc = targets.get("dCp_fus_gc")

            if phase == 1 and not self._has_phase1_supervision(targets):
                continue

            if phase == 1:
                output = self._forward_phase1(
                    sol_batch,
                    slv_batch,
                    T,
                    solvent_type,
                    solute_morgan_fp=solute_morgan_fp,
                    solvent_morgan_fp=solvent_morgan_fp,
                    solute_descriptor_prior_features=solute_descriptor_prior_features,
                    solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                    solute_group_prior_features=solute_group_prior_features,
                    solvent_group_prior_features=solvent_group_prior_features,
                    T_m_gc=T_m_gc,
                    dH_fus_gc=dH_fus_gc,
                    dCp_fus_gc=dCp_fus_gc,
                )
            else:
                output = self.model(
                    sol_batch,
                    slv_batch,
                    T,
                    solvent_type=solvent_type,
                    solute_morgan_fp=solute_morgan_fp,
                    solvent_morgan_fp=solvent_morgan_fp,
                    solute_descriptor_prior_features=solute_descriptor_prior_features,
                    solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                    solute_group_prior_features=solute_group_prior_features,
                    solvent_group_prior_features=solvent_group_prior_features,
                    T_m_gc=T_m_gc,
                    dH_fus_gc=dH_fus_gc,
                    dCp_fus_gc=dCp_fus_gc,
                    targets=targets,
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

        self._maybe_release_device_cache(force=True)
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
        *,
        start_epoch: int = 0,
        optimizer_state_dict: dict | None = None,
        scheduler_state_dict: dict | None = None,
        on_epoch_end: Callable[[ResumeStateDict], None] | None = None,
    ) -> None:
        """Run a single training phase."""
        print(f"\n{'=' * 60}")
        print(f"Phase {phase}: {n_epochs} epochs")
        active = {k: v for k, v in self.phase_weights[phase].items() if v > 0}
        print(f"Active losses: {active}")
        if start_epoch > 0:
            print(f"Resuming from epoch {start_epoch}/{n_epochs}")
        print(f"{'=' * 60}")

        # Reset early stopping between phases only when starting a phase fresh.
        if start_epoch == 0:
            self.patience_counter = 0
            if phase >= 2:
                self.best_val_loss = float("inf")

        # Freeze correction in Phase 1 and early Phase 2.
        if phase == 1:
            self._freeze_correction(True)
        elif phase == 2:
            self._freeze_correction(
                start_epoch < self.cfg.phase2_correction_unfreeze_epoch
            )
        else:
            self._freeze_correction(False)
        self._set_gc_prior_residual_freeze(phase, start_epoch)

        optimizer = self._build_optimizer(phase)
        scheduler = self._build_scheduler(optimizer, phase, n_epochs)
        if optimizer_state_dict is not None:
            optimizer.load_state_dict(optimizer_state_dict)
        if scheduler_state_dict is not None:
            scheduler.load_state_dict(scheduler_state_dict)

        for epoch in progress(
            range(start_epoch, n_epochs),
            desc=f"Phase {phase} epochs",
        ):
            self._set_oracle_injection_prob(phase, epoch, n_epochs)
            self._set_gc_prior_residual_freeze(phase, epoch)
            compute_mono = phase >= 2 and epoch % 5 == 0

            train_loss, train_stats = self.train_epoch(
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
            print(log)
            raw_components = train_stats.get("raw", {})
            weighted_components = train_stats.get("weighted", {})
            component_weights = train_stats.get("weights", {})
            for name in sorted(raw_components):
                print(
                    "    "
                    f"loss/{name}_raw={raw_components[name]:.4f} "
                    f"loss/{name}_weighted={weighted_components.get(name, 0.0):.4f} "
                    f"weight={component_weights.get(name, 0.0):.4g}"
                )
            sol_fraction = train_stats.get("sol_fraction")
            sol_fraction_min = train_stats.get("sol_fraction_min")
            max_regularizer_ratio = train_stats.get("max_regularizer_ratio")
            sol_fraction_str = (
                f"{float(sol_fraction):.3f}"
                if sol_fraction is not None
                else "NA"
            )
            sol_fraction_min_str = (
                f"{float(sol_fraction_min):.3f}"
                if sol_fraction_min is not None
                else "NA"
            )
            max_regularizer_ratio_str = (
                f"{float(max_regularizer_ratio):.2f}"
                if max_regularizer_ratio is not None
                else "NA"
            )
            print(
                "    "
                f"loss/total={train_loss:.4f} "
                f"loss/sol_fraction={sol_fraction_str} "
                f"loss/sol_fraction_min={sol_fraction_min_str} "
                f"loss/max_regularizer_ratio={max_regularizer_ratio_str} "
                f"loss/regularizer_domination_count="
                f"{int(train_stats.get('regularizer_domination_count', 0))}"
            )
            if sol_fraction is not None and float(sol_fraction) < 0.1:
                LOGGER.warning(
                    "Solubility loss fraction dropped below 0.1: "
                    "phase=%d epoch=%d sol_fraction=%.3f",
                    phase,
                    epoch,
                    float(sol_fraction),
                )
            if (
                sol_fraction_min is not None
                and float(sol_fraction_min) < 0.1
            ):
                LOGGER.warning(
                    "Minimum solubility loss fraction dropped below 0.1: "
                    "phase=%d epoch=%d sol_fraction_min=%.3f",
                    phase,
                    epoch,
                    float(sol_fraction_min),
                )

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
            if on_epoch_end is not None:
                on_epoch_end(
                    {
                        "status": "in_progress",
                        "phase": phase,
                        "epoch_in_phase": epoch,
                        "next_epoch_in_phase": epoch + 1,
                        "phase_epochs": n_epochs,
                        "optimizer_state_dict": optimizer.state_dict(),
                        "scheduler_state_dict": scheduler.state_dict(),
                        "trainer_state_dict": self.state_dict(),
                    }
                )

            if phase >= 2 and self.patience_counter >= self.cfg.patience:
                print(f"  Early stopping at epoch {epoch}")
                break

    # -------------------------------------------------------------- #
    #  Full training pipeline                                         #
    # -------------------------------------------------------------- #

    def train_full(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        *,
        resume_state: ResumeStateDict | None = None,
        on_epoch_end: Callable[[ResumeStateDict], None] | None = None,
    ) -> None:
        """Run all three training phases sequentially."""
        phase_epochs = {
            1: self.cfg.epochs_phase1,
            2: self.cfg.epochs_phase2,
            3: self.cfg.epochs_phase3,
        }
        resume_phase = int(resume_state.get("phase", 1)) if resume_state else 1
        resume_epoch = (
            int(resume_state.get("next_epoch_in_phase", 0))
            if resume_state
            else 0
        )
        optimizer_state_dict = (
            resume_state.get("optimizer_state_dict")
            if resume_state and resume_state.get("status") == "in_progress"
            else None
        )
        scheduler_state_dict = (
            resume_state.get("scheduler_state_dict")
            if resume_state and resume_state.get("status") == "in_progress"
            else None
        )

        for phase in (1, 2, 3):
            n_epochs = phase_epochs[phase]
            if phase < resume_phase:
                continue

            start_epoch = resume_epoch if phase == resume_phase else 0
            if start_epoch >= n_epochs:
                optimizer_state_dict = None
                scheduler_state_dict = None
                continue

            self.train_phase(
                phase,
                train_loader,
                val_loader,
                n_epochs,
                start_epoch=start_epoch,
                optimizer_state_dict=optimizer_state_dict,
                scheduler_state_dict=scheduler_state_dict,
                on_epoch_end=on_epoch_end,
            )
            optimizer_state_dict = None
            scheduler_state_dict = None
            resume_epoch = 0

        if self.best_state is not None:
            self.model.load_state_dict(self.best_state)
            print(
                f"\nRestored best model (val MAE = {self.best_val_loss:.4f})"
            )
