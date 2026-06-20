"""
Three-phase curriculum trainer for TGNN-Solv.

Phase 1 — Property pretraining (no solubility loss):
  Train heads to predict T_m, ΔH_fus, Hansen, γ∞, and optional finite γ₂.
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
from .loss import TGNNSolvLoss, sigma_profile_emd_loss
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
        "timp_disp_hansen": 0.0, "timp_polar_hansen": 0.0,
        "gamma_inf": 1.0,
        "gamma_2": 1.0,
        "mono": 0.0, "res": 0.0, "bridge": 0.0, "tau_reg": 0.0,
        "phys_pref": 0.0, "direct_reg": 0.0, "direct_nll": 0.0,
        "decorr": 0.0,
        "pair_temp_rank": 0.0, "vant_hoff_local": 0.0,
        "pair_temp_delta": 0.0, "vant_hoff_slope": 0.0,
        "vant_hoff_intercept": 0.0,
        "vh_anchor": 0.0,
        "moe_balance": 0.0, "descriptor_prior": 0.0, "group_prior": 0.0,
        "hansen_contrastive_mol": 0.0,
        "hansen_contrastive_channel": 0.0,
        "hansen_contrastive_pair": 0.0,
        "hansen_channel_orth": 0.0,
        "hansen_delta": 0.0,
        "aux_direct_sol": 0.0,
    },
    2: {
        "sol": 1.0, "T_m": 0.05, "dH": 0.05, "hansen": 0.05,
        "timp_disp_hansen": 0.0, "timp_polar_hansen": 0.0,
        "gamma_inf": 0.1,
        "gamma_2": 0.1,
        "mono": 0.0, "res": 0.01, "bridge": 0.0,
        "tau_reg": 0.002,
        "phys_pref": 0.01,
        "direct_reg": 0.01,
        "direct_nll": 0.01,
        "decorr": 0.0,
        "pair_temp_rank": 0.005,
        "vant_hoff_local": 0.001,
        "pair_temp_delta": 0.0,
        "vant_hoff_slope": 0.0,
        "vant_hoff_intercept": 0.0,
        "vh_anchor": 0.0,
        "moe_balance": 0.005,
        "descriptor_prior": 0.0,
        "group_prior": 0.0,
        "hansen_contrastive_mol": 0.0,
        "hansen_contrastive_channel": 0.0,
        "hansen_contrastive_pair": 0.0,
        "hansen_channel_orth": 0.0,
        "hansen_delta": 0.0,
        "aux_direct_sol": 0.0,
    },
    3: {
        "sol": 1.0, "T_m": 0.03, "dH": 0.03, "hansen": 0.03,
        "timp_disp_hansen": 0.0, "timp_polar_hansen": 0.0,
        "gamma_inf": 0.05,
        "gamma_2": 0.05,
        "mono": 0.1, "res": 0.02, "bridge": 0.0,
        "tau_reg": 0.002,
        "phys_pref": 0.01,
        "direct_reg": 0.02,
        "direct_nll": 0.02,
        "decorr": 0.0,
        "pair_temp_rank": 0.01,
        "vant_hoff_local": 0.001,
        "pair_temp_delta": 0.0,
        "vant_hoff_slope": 0.0,
        "vant_hoff_intercept": 0.0,
        "vh_anchor": 0.0,
        "moe_balance": 0.01,
        "descriptor_prior": 0.0,
        "group_prior": 0.0,
        "hansen_contrastive_mol": 0.0,
        "hansen_contrastive_channel": 0.0,
        "hansen_contrastive_pair": 0.0,
        "hansen_channel_orth": 0.0,
        "hansen_delta": 0.0,
        "aux_direct_sol": 0.0,
    },
}

STANDARD_BRANCH_TRAINING_MODES = {"", "standard", "joint", "default"}
COORDINATE_DESCENT_BRANCH_TRAINING_MODES = {
    "coordinate_descent",
    "crystal_activity_crystal",
    "two_stage_crystal_activity",
}
COORDINATE_DESCENT_ALLOWED_LOSSES = {
    1: {
        "T_m",
        "dH",
        "hansen",
        "timp_disp_hansen",
        "timp_polar_hansen",
        "descriptor_prior",
        "group_prior",
        "hansen_delta",
    },
    2: {
        "sol",
        "gamma_inf",
        "gamma_2",
        "mono",
        "res",
        "tau_reg",
        "phys_pref",
        "direct_reg",
        "direct_nll",
        "decorr",
        "pair_temp_rank",
        "vant_hoff_local",
        "pair_temp_delta",
        "vant_hoff_slope",
        "vant_hoff_intercept",
        "vh_anchor",
        "moe_balance",
        "aux_direct_sol",
    },
    3: {
        "sol",
        "T_m",
        "dH",
        "hansen",
        "timp_disp_hansen",
        "timp_polar_hansen",
        "descriptor_prior",
        "group_prior",
        "hansen_delta",
    },
}

class TGNNSolvTrainer:
    """Curriculum trainer with three phases."""

    def __init__(self, model: TGNNSolv, cfg: TGNNSolvConfig) -> None:
        self.model = model
        self.cfg = cfg
        self.loss_fn = TGNNSolvLoss(cfg)
        self.device = next(model.parameters()).device
        self.loss_fn.to(self.device)
        self._base_oracle_injection_prob = cfg.oracle_injection_prob
        self._base_detach_crystal_from_encoder = bool(cfg.detach_crystal_from_encoder)
        self._base_detach_crystal_params_in_sle = bool(
            cfg.detach_crystal_params_in_sle
        )

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
        self.best_epoch: int | None = None
        self.best_phase: int | None = None
        self.patience_counter = 0
        self._last_confidence = 0.0
        self._cache_release_counter = 0
        self._correction_frozen: bool | None = None

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

    def _resolved_branch_training_mode(self) -> str:
        """Normalize branch-training aliases to a small supported set."""
        mode = str(getattr(self.cfg, "branch_training_mode", "standard")).strip().lower()
        if mode in STANDARD_BRANCH_TRAINING_MODES:
            return "standard"
        if mode in COORDINATE_DESCENT_BRANCH_TRAINING_MODES:
            return "coordinate_descent"
        raise ValueError(
            "branch_training_mode must be 'standard' or 'coordinate_descent', "
            f"got {self.cfg.branch_training_mode!r}."
        )

    def _set_requires_grad(self, target: object | None, requires_grad: bool) -> None:
        """Toggle gradients on a module or standalone parameter."""
        if target is None:
            return
        if isinstance(target, torch.nn.Parameter):
            target.requires_grad = requires_grad
            return
        parameters = getattr(target, "parameters", None)
        if callable(parameters):
            for param in target.parameters():
                param.requires_grad = requires_grad

    def _crystal_branch_targets(self) -> tuple[object | None, ...]:
        """Return modules that define the crystal / pre-interaction property branch."""
        return (
            self.model.gnn,
            self.model.readout,
            self.model.head_fusion,
            self.model.head_hansen,
            self.model.head_aux,
            self.model.solute_fp_adapter,
            self.model.solvent_fp_adapter,
            self.model.timp_disp_probe,
            self.model.timp_polar_probe,
            self.model.fp_pre_scale,
        )

    def _activity_branch_targets(self) -> tuple[object | None, ...]:
        """Return modules that define the interaction / activity branch."""
        return (
            self.model.cross_attn_layers,
            self.model.bipartite_layers,
            self.model.pair_repr,
            self.model.timp_pair_repr_combined,
            self.model.timp_pair_repr_disp,
            self.model.timp_pair_repr_polar,
            self.model.timp_pair_proj,
            self.model.solvent_moe,
            self.model.head_nrtl,
            self.model.aux_direct_sol_head,
            self.model.descriptor_mlp,
            self.model.pair_desc_proj,
            self.model.ionic_feature_adapter,
            self.model.ionic_pair_scale,
            self.model.correction,
            self.model.sol_token,
            self.model.slv_token,
            self.model.token_proj,
            self.model.sol_token_gate,
            self.model.slv_token_gate,
            self.model.fp_post_scale,
        )

    def _set_runtime_detach_flags(
        self,
        *,
        detach_crystal_from_encoder: bool,
        detach_crystal_params_in_sle: bool,
    ) -> None:
        """Set phase-effective detach flags on both config handles."""
        self.cfg.detach_crystal_from_encoder = bool(detach_crystal_from_encoder)
        self.cfg.detach_crystal_params_in_sle = bool(detach_crystal_params_in_sle)
        self.model.cfg.detach_crystal_from_encoder = bool(detach_crystal_from_encoder)
        self.model.cfg.detach_crystal_params_in_sle = bool(detach_crystal_params_in_sle)

    def _configure_phase_branch_training(self, phase: int) -> None:
        """Apply phase-specific freezing for branch-aware training modes."""
        self._set_runtime_detach_flags(
            detach_crystal_from_encoder=self._base_detach_crystal_from_encoder,
            detach_crystal_params_in_sle=self._base_detach_crystal_params_in_sle,
        )
        for param in self.model.parameters():
            param.requires_grad = True
        for param in self.loss_fn.parameters():
            param.requires_grad = True
        self._correction_frozen = None

        if self._resolved_branch_training_mode() != "coordinate_descent":
            return

        if phase == 1:
            for target in self._activity_branch_targets():
                self._set_requires_grad(target, False)
            return
        if phase == 2:
            for target in self._crystal_branch_targets():
                self._set_requires_grad(target, False)
            self._set_runtime_detach_flags(
                detach_crystal_from_encoder=True,
                detach_crystal_params_in_sle=True,
            )
            return
        if phase == 3:
            for target in self._activity_branch_targets():
                self._set_requires_grad(target, False)
            return
        raise ValueError(f"Unsupported training phase: {phase}")

    def _apply_branch_training_mode_to_weights(
        self,
        phase: int,
        weights: dict[str, float],
    ) -> dict[str, float]:
        """Zero loss components that conflict with the active branch schedule."""
        if self._resolved_branch_training_mode() != "coordinate_descent":
            return weights
        allowed = COORDINATE_DESCENT_ALLOWED_LOSSES[phase]
        filtered = {
            key: (float(value) if key in allowed else 0.0)
            for key, value in weights.items()
        }
        filtered["walden"] = 0.0
        return filtered

    def _set_correction_freeze_for_phase(self, phase: int, epoch: int) -> None:
        """Apply the correction-gate freeze schedule after branch freezing."""
        if self._resolved_branch_training_mode() == "coordinate_descent" and phase != 2:
            self._freeze_correction(True)
            return
        if phase == 1:
            self._freeze_correction(True)
        elif phase == 2:
            self._freeze_correction(
                epoch < self.cfg.phase2_correction_unfreeze_epoch
            )
        else:
            self._freeze_correction(False)

    def _effective_loss_weight(
        self,
        loss_name: str,
        weights: dict[str, float],
    ) -> float:
        """Resolve the effective scalar weight for a loss component."""
        if loss_name == "walden":
            if not self.cfg.use_walden_check:
                return 0.0
            if "walden" in weights:
                return float(weights["walden"])
            if self.cfg.walden_weight > 0:
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
        override_keys = set(overrides or {})
        if overrides is not None:
            defaults.update(overrides)
        if not bridge_explicitly_overridden:
            defaults["bridge"] = self.cfg.bridge_loss_weight
        if phase >= 2 and self.cfg.descriptor_prior_reg_weight > 0:
            defaults["descriptor_prior"] = self.cfg.descriptor_prior_reg_weight
        if phase >= 2 and self.cfg.group_prior_reg_weight > 0:
            defaults["group_prior"] = self.cfg.group_prior_reg_weight
        if self.cfg.encoder_type == "timp":
            defaults["timp_disp_hansen"] = 0.05 if phase == 1 else 0.02
            defaults["timp_polar_hansen"] = 0.05 if phase == 1 else 0.02
        if self.cfg.use_hansen_contrastive:
            phase_contrastive = {
                1: {
                    "hansen_contrastive_mol": 0.10,
                    "hansen_contrastive_channel": 0.10,
                    "hansen_contrastive_pair": 0.0,
                },
                2: {
                    "hansen_contrastive_mol": self.cfg.hansen_contrastive_mol_weight,
                    "hansen_contrastive_channel": self.cfg.hansen_contrastive_channel_weight,
                    "hansen_contrastive_pair": self.cfg.hansen_contrastive_pair_weight,
                },
                3: {
                    "hansen_contrastive_mol": 0.02,
                    "hansen_contrastive_channel": 0.02,
                    "hansen_contrastive_pair": 0.01,
                },
            }[phase]
            for key, value in phase_contrastive.items():
                if key not in override_keys:
                    defaults[key] = value
            if "hansen_channel_orth" not in override_keys:
                defaults["hansen_channel_orth"] = self.cfg.hansen_contrastive_orth_weight
        if self.cfg.use_hansen_delta_loss and "hansen_delta" not in override_keys:
            defaults["hansen_delta"] = {
                1: self.cfg.hansen_delta_loss_phase1_weight,
                2: self.cfg.hansen_delta_loss_phase2_weight,
                3: self.cfg.hansen_delta_loss_phase3_weight,
            }[phase]
        if self.cfg.use_aux_direct_sol_loss and "aux_direct_sol" not in override_keys:
            defaults["aux_direct_sol"] = {
                1: 0.0,
                2: self.cfg.aux_direct_sol_loss_weight,
                3: self.cfg.aux_direct_sol_loss_phase3_weight,
            }[phase]
        return defaults

    def _weights_for_epoch(
        self,
        phase: int,
        *,
        epoch: int | None = None,
        n_epochs: int | None = None,
    ) -> dict[str, float]:
        """Return phase weights, optionally with a smooth Phase 2 schedule."""
        weights = self.phase_weights[phase].copy()
        if self.cfg.use_smooth_phase2_curriculum and phase == 2:
            if epoch is None or n_epochs is None:
                progress = 1.0
            else:
                progress = float(epoch) / float(max(int(n_epochs) - 1, 1))
                progress = min(max(progress, 0.0), 1.0)

            crystal_weight = (
                self.cfg.smooth_phase2_crystal_start
                + (
                    self.cfg.smooth_phase2_crystal_end
                    - self.cfg.smooth_phase2_crystal_start
                )
                * progress
            )
            pair_weight = (
                self.cfg.smooth_phase2_pair_start
                + (self.cfg.smooth_phase2_pair_end - self.cfg.smooth_phase2_pair_start)
                * progress
            )

            for key in ("T_m", "dH", "hansen"):
                if key in weights:
                    weights[key] = float(crystal_weight)
            if "sol" in weights:
                weights["sol"] = float(pair_weight)
            if "gamma_inf" in weights:
                weights["gamma_inf"] = float(self.cfg.smooth_phase2_idac_weight)

        return self._apply_branch_training_mode_to_weights(phase, weights)

    def state_dict(self) -> TrainerStateDict:
        """Serialize trainer state required for checkpointed resume."""
        return {
            "history": self.history,
            "best_val_loss": self.best_val_loss,
            "best_state": self.best_state,
            "best_epoch": self.best_epoch,
            "best_phase": self.best_phase,
            "patience_counter": self.patience_counter,
            "last_confidence": self._last_confidence,
            "base_oracle_injection_prob": self._base_oracle_injection_prob,
            "current_oracle_injection_prob": self.cfg.oracle_injection_prob,
            "loss_fn_state_dict": self.loss_fn.state_dict(),
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
        raw_best_epoch = state.get("best_epoch")
        self.best_epoch = int(raw_best_epoch) if raw_best_epoch is not None else None
        raw_best_phase = state.get("best_phase")
        self.best_phase = int(raw_best_phase) if raw_best_phase is not None else None
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
        loss_state = state.get("loss_fn_state_dict")
        if isinstance(loss_state, dict):
            self.loss_fn.load_state_dict(loss_state, strict=False)

    # -------------------------------------------------------------- #
    #  Optimizer / scheduler                                          #
    # -------------------------------------------------------------- #

    def _build_optimizer(self, phase: int) -> AdamW:
        lr = {
            1: self.cfg.lr_phase1,
            2: self.cfg.lr_phase2,
            3: self.cfg.lr_phase3,
        }[phase]
        params = list(self.model.parameters())
        if self.cfg.use_hansen_contrastive:
            params.extend(self.loss_fn.parameters())
        return AdamW(
            params,
            lr=lr,
            weight_decay=float(self.cfg.weight_decay),
            betas=(0.9, 0.999),
        )

    def _build_scheduler(
        self, optimizer: AdamW, phase: int, n_epochs: int
    ) -> LambdaLR:
        warmup = self.cfg.warmup_epochs

        def lr_lambda(epoch: int) -> float:
            if epoch < warmup:
                # +1 so epoch 0 gets a nonzero LR. LambdaLR's construction consumes
                # lr_lambda(0) before the first optimizer.step(), so `epoch / warmup`
                # made the first epoch of EVERY phase train at LR exactly 0 — a
                # wasted epoch per phase under the 3-phase curriculum.
                return (epoch + 1) / max(warmup, 1)
            progress = (epoch - warmup) / max(n_epochs - warmup, 1)
            return 0.5 * (1.0 + math.cos(math.pi * progress))

        return LambdaLR(optimizer, lr_lambda)

    # -------------------------------------------------------------- #
    #  Correction gate control                                        #
    # -------------------------------------------------------------- #

    def _freeze_correction(self, freeze: bool) -> None:
        """Freeze or unfreeze the adaptive correction."""
        if self._correction_frozen is freeze:
            return
        for p in self.model.correction.parameters():
            p.requires_grad = not freeze
        if freeze:
            # Reset confidence to high (physics-first)
            with torch.no_grad():
                self.model.correction.confidence_net[-1].bias.fill_(2.2)
        self._correction_frozen = freeze

    def _has_phase1_supervision(
        self, targets: dict[str, Tensor | object]
    ) -> bool:
        """Return whether a batch contains any Phase 1 auxiliary labels."""
        for key in ("T_m_mask", "dH_mask", "hansen_mask", "gamma_mask", "gamma2_mask"):
            mask = targets.get(key)
            if isinstance(mask, Tensor) and bool(mask.any().item()):
                return True
        return False

    def _idac_aux_weight(self, phase: int) -> float:
        """Resolve the activity-only auxiliary loss weight for a phase."""
        configured = {
            1: self.cfg.idac_aux_phase1_weight,
            2: self.cfg.idac_aux_phase2_weight,
            3: self.cfg.idac_aux_phase3_weight,
        }[phase]
        if configured is not None:
            return float(configured)
        return float(self.phase_weights[phase].get("gamma_inf", 0.0))

    def _crystal_aux_weight(self, phase: int) -> float:
        """Resolve the external-crystal auxiliary loss weight for a phase."""
        configured = {
            1: self.cfg.crystal_aux_phase1_weight,
            2: self.cfg.crystal_aux_phase2_weight,
            3: self.cfg.crystal_aux_phase3_weight,
        }[phase]
        if configured is not None:
            return float(configured)
        # Default to the phase's melting-point weight so the external pool is
        # scaled consistently with the in-corpus crystal supervision.
        return float(self.phase_weights[phase].get("T_m", 0.0))

    def _sigma_aux_weight(self, phase: int) -> float:
        """Resolve the external sigma-profile auxiliary loss weight for a phase."""
        configured = {
            1: self.cfg.sigma_aux_phase1_weight,
            2: self.cfg.sigma_aux_phase2_weight,
            3: self.cfg.sigma_aux_phase3_weight,
        }[phase]
        if configured is not None:
            return float(configured)
        # Default: scale like the crystal grounding (the melting-point weight),
        # so both single-component groundings ramp together across phases.
        return float(self.phase_weights[phase].get("T_m", 0.0))

    def _idac_aux_component_scale(
        self,
        mask: object,
        sample_weight: object,
    ) -> float:
        """Return an absolute scale for an aux-only activity component.

        The loss layer uses normalized weighted means, which is appropriate for
        relative per-row weighting but makes a constant CSV weight a no-op.
        Aux-only streams intentionally use a constant `gamma_weight` or
        `gamma2_weight` to scale the whole sidecar contribution, so the trainer
        folds the mean sample weight into the component loss weight here.
        """
        if not isinstance(mask, Tensor) or not bool(mask.any().item()):
            return 1.0
        if not isinstance(sample_weight, Tensor):
            return 1.0
        active = sample_weight[mask.bool()]
        if active.numel() == 0:
            return 1.0
        active = active[torch.isfinite(active)]
        if active.numel() == 0:
            return 1.0
        return max(float(active.to(dtype=torch.float32).mean().item()), 0.0)

    def _move_batch_to_device(
        self,
        batch: tuple[Batch, Batch, dict[str, object]],
    ) -> tuple[Batch, Batch, dict[str, object]]:
        """Move a standard TGNN batch tuple to the trainer device."""
        sol_batch, slv_batch, targets = batch
        sol_batch = sol_batch.to(self.device)
        slv_batch = slv_batch.to(self.device)
        targets = {
            k: v.to(self.device) if isinstance(v, torch.Tensor) else v
            for k, v in targets.items()
        }
        return sol_batch, slv_batch, targets

    def _train_idac_aux_batch(
        self,
        batch: tuple[Batch, Batch, dict[str, object]],
        optimizer: AdamW,
        phase: int,
    ) -> tuple[float | None, dict[str, float]]:
        """Train one activity-only auxiliary batch via the fast NRTL path."""
        if self._resolved_branch_training_mode() == "coordinate_descent" and phase != 2:
            return None, {}
        phase_gamma_weight = self._idac_aux_weight(phase)
        if phase_gamma_weight <= 0.0:
            return None, {}

        sol_batch, slv_batch, targets = self._move_batch_to_device(batch)
        gamma_mask = targets.get("gamma_mask")
        gamma2_mask = targets.get("gamma2_mask")
        has_gamma_inf = isinstance(gamma_mask, Tensor) and bool(gamma_mask.any().item())
        has_gamma2 = isinstance(gamma2_mask, Tensor) and bool(gamma2_mask.any().item())
        if not has_gamma_inf and not has_gamma2:
            return None, {}

        T = targets["T"]
        optimizer.zero_grad()
        output = self.model(
            sol_batch,
            slv_batch,
            T,
            solvent_type=targets.get("solvent_type"),
            solute_morgan_fp=targets.get("solute_morgan_fp"),
            solvent_morgan_fp=targets.get("solvent_morgan_fp"),
            solute_descriptors=targets.get("solute_descriptors"),
            solvent_descriptors=targets.get("solvent_descriptors"),
            ionic_features=targets.get("ionic_features"),
            solute_descriptor_prior_features=targets.get(
                "solute_descriptor_prior_features"
            ),
            solvent_descriptor_prior_features=targets.get(
                "solvent_descriptor_prior_features"
            ),
            solute_group_prior_features=targets.get("solute_group_prior_features"),
            solvent_group_prior_features=targets.get("solvent_group_prior_features"),
            T_m_gc=targets.get("T_m_gc"),
            dH_fus_gc=targets.get("dH_fus_gc"),
            dCp_fus_gc=targets.get("dCp_fus_gc"),
            targets=targets,
            detach_crystal_from_encoder=(
                self.cfg.detach_crystal_from_encoder and phase == 2
            ),
            gamma_only=True,
        )

        aux_weights = {key: 0.0 for key in self.phase_weights[phase]}
        gamma_inf_scale = self._idac_aux_component_scale(
            gamma_mask,
            targets.get("gamma_weight"),
        )
        gamma2_scale = self._idac_aux_component_scale(
            gamma2_mask,
            targets.get("gamma2_weight"),
        )
        aux_weights["gamma_inf"] = (
            phase_gamma_weight * gamma_inf_scale if has_gamma_inf else 0.0
        )
        aux_weights["gamma_2"] = (
            phase_gamma_weight * gamma2_scale if has_gamma2 else 0.0
        )
        aux_weights["walden"] = 0.0
        loss, loss_dict = self.loss_fn(output, targets, weights=aux_weights, T=T)
        if not torch.isfinite(loss):
            LOGGER.warning("Skipping non-finite IDAC auxiliary loss: %s", loss)
            return None, {}
        loss.backward()
        grad_params = list(self.model.parameters())
        if self.cfg.use_hansen_contrastive:
            grad_params.extend(self.loss_fn.parameters())
        torch.nn.utils.clip_grad_norm_(grad_params, self.cfg.grad_clip)
        optimizer.step()
        self._maybe_release_device_cache()
        return float(loss.item()), loss_dict

    def _train_crystal_aux_batch(
        self,
        batch: tuple[Batch, Batch, dict[str, object]],
        optimizer: AdamW,
        phase: int,
    ) -> tuple[float | None, dict[str, float]]:
        """Train one external single-component crystal batch (T_m / dH_fus only).

        Grounds the crystal branch on a large pure-component label pool. Uses the
        lightweight Phase-1 forward (encoder + heads, no SLE solver) and applies
        only the T_m / dH loss weights, so gradients flow into the crystal head
        and shared encoder. Under coordinate descent the crystal branch trains in
        phases 1 and 3 (not 2), matching the main schedule.
        """
        if self._resolved_branch_training_mode() == "coordinate_descent" and phase == 2:
            return None, {}
        weight = self._crystal_aux_weight(phase)
        if weight <= 0.0:
            return None, {}

        sol_batch, slv_batch, targets = self._move_batch_to_device(batch)
        tm_mask = targets.get("T_m_mask")
        dh_mask = targets.get("dH_mask")
        has_tm = isinstance(tm_mask, Tensor) and bool(tm_mask.any().item())
        has_dh = isinstance(dh_mask, Tensor) and bool(dh_mask.any().item())
        if not has_tm and not has_dh:
            return None, {}

        T = targets["T"]
        optimizer.zero_grad()
        output = self._forward_phase1(
            sol_batch,
            slv_batch,
            T,
            targets.get("solvent_type"),
            solute_morgan_fp=targets.get("solute_morgan_fp"),
            solvent_morgan_fp=targets.get("solvent_morgan_fp"),
            solute_descriptors=targets.get("solute_descriptors"),
            solvent_descriptors=targets.get("solvent_descriptors"),
            ionic_features=targets.get("ionic_features"),
            solute_descriptor_prior_features=targets.get(
                "solute_descriptor_prior_features"
            ),
            solvent_descriptor_prior_features=targets.get(
                "solvent_descriptor_prior_features"
            ),
            solute_group_prior_features=targets.get("solute_group_prior_features"),
            solvent_group_prior_features=targets.get("solvent_group_prior_features"),
            unifac_ln_gamma_inf=targets.get("unifac_ln_gamma_inf"),
            unifac_gamma_mask=targets.get("unifac_gamma_mask"),
            T_m_gc=targets.get("T_m_gc"),
            dH_fus_gc=targets.get("dH_fus_gc"),
            dCp_fus_gc=targets.get("dCp_fus_gc"),
        )

        aux_weights = {key: 0.0 for key in self.phase_weights[phase]}
        aux_weights["T_m"] = weight if has_tm else 0.0
        aux_weights["dH"] = weight if has_dh else 0.0
        aux_weights["walden"] = 0.0
        loss, loss_dict = self.loss_fn(output, targets, weights=aux_weights, T=T)
        if not torch.isfinite(loss):
            LOGGER.warning("Skipping non-finite crystal auxiliary loss: %s", loss)
            return None, {}
        loss.backward()
        grad_params = list(self.model.parameters())
        if self.cfg.use_hansen_contrastive:
            grad_params.extend(self.loss_fn.parameters())
        torch.nn.utils.clip_grad_norm_(grad_params, self.cfg.grad_clip)
        optimizer.step()
        self._maybe_release_device_cache()
        return float(loss.item()), loss_dict

    def _train_sigma_aux_batch(
        self,
        batch: tuple[Batch, Batch, dict[str, object]],
        optimizer: AdamW,
        phase: int,
    ) -> tuple[float | None, dict[str, float]]:
        """Train one external single-component sigma-profile batch (COSMO-SAC only).

        Grounds the activity branch: encodes the solute, predicts its sigma-profile
        via the shared SigmaProfileHead, and supervises it against the external DB
        label with an EMD shape loss + area loss. Gradients flow into the sigma
        head and the shared encoder. Runs in the crystal phases (1/3) under
        coordinate descent so it co-grounds the encoder before SLE training.
        """
        model = self.model
        if getattr(model, "head_sigma", None) is None:
            return None, {}
        if self._resolved_branch_training_mode() == "coordinate_descent" and phase == 2:
            return None, {}
        weight = self._sigma_aux_weight(phase)
        if weight <= 0.0:
            return None, {}

        sol_batch, slv_batch, targets = self._move_batch_to_device(batch)
        mask = targets.get("sigma_profile_mask")
        if not isinstance(mask, Tensor) or not bool(mask.any().item()):
            return None, {}
        target_shape = targets.get("sigma_profile_target")
        target_area = targets.get("sigma_area_target")
        if not isinstance(target_shape, Tensor) or not isinstance(target_area, Tensor):
            return None, {}

        optimizer.zero_grad()
        # Mirror the main forward: when the encoder is temperature-conditioned,
        # ground the sigma head on the SAME temperature-aware solute embedding it
        # receives at SLE/inference time. _encoder_temp_features returns None when
        # use_temperature_in_encoder is off, so the default path is unchanged.
        enc_t_feat = model._encoder_temp_features(make_temperature_features(targets["T"]))
        _, g_payload, _, _ = model._encode_and_readout(
            sol_batch, "solute", temp_feat=enc_t_feat
        )
        g_sol = g_payload["value"]
        if model.cfg.use_morgan_features:
            fp = targets.get("solute_morgan_fp")
            if isinstance(fp, Tensor):
                g_sol = g_sol + model.fp_pre_scale * model.solute_fp_adapter(fp.to(g_sol))
        sig = model.head_sigma(g_sol)
        loss = weight * sigma_profile_emd_loss(
            sig["p_shape"], target_shape, sig["area"], target_area, mask,
            mode=self.cfg.sigma_profile_loss, area_scale=self.cfg.sigma_area_scale,
        )
        if not torch.isfinite(loss):
            LOGGER.warning("Skipping non-finite sigma-profile auxiliary loss: %s", loss)
            return None, {}
        loss.backward()
        torch.nn.utils.clip_grad_norm_(list(self.model.parameters()), self.cfg.grad_clip)
        optimizer.step()
        self._maybe_release_device_cache()
        return float(loss.item()), {"sigma_profile": float(loss.item())}

    def _clone_model_state(self) -> dict[str, Tensor]:
        """Clone the current model weights onto CPU for best-state restore."""
        return {
            key: value.detach().cpu().clone()
            for key, value in self.model.state_dict().items()
        }

    def _phase_early_stopping_patience(self, phase: int) -> int | None:
        """Resolve phase-aware early stopping patience with backward compatibility."""
        if phase == 2:
            if self.cfg.early_stopping_patience is not None:
                return int(self.cfg.early_stopping_patience)
            return int(self.cfg.patience)
        if phase == 3:
            if self.cfg.early_stopping_phase3_patience is not None:
                return int(self.cfg.early_stopping_phase3_patience)
            if self.cfg.early_stopping_patience is not None:
                return int(self.cfg.early_stopping_patience)
            return int(self.cfg.patience)
        return None

    def _phase_early_stopping_min_epochs(self, phase: int) -> int:
        """Resolve minimum epochs before early stopping can trigger."""
        if phase == 2:
            return max(int(self.cfg.early_stopping_min_epochs), 0)
        if phase == 3:
            return max(min(int(self.cfg.early_stopping_min_epochs), 5), 0)
        return 0

    def _initialize_phase_early_stopping(
        self,
        phase: int,
        val_loader: DataLoader,
    ) -> None:
        """Initialize best-state tracking at the start of a new validation phase."""
        if phase < 2:
            return
        baseline_metrics = self.validate(val_loader, phase)
        baseline_criterion = float(
            baseline_metrics.get("mae", baseline_metrics["val_loss"])
        )
        self.best_val_loss = baseline_criterion
        self.best_state = self._clone_model_state()
        self.best_epoch = -1
        self.best_phase = phase
        self.patience_counter = 0
        baseline_msg = (
            f"  Initial Phase {phase} validation: "
            f"val={baseline_metrics['val_loss']:.4f}"
        )
        if "mae" in baseline_metrics:
            baseline_msg += (
                f", MAE={baseline_metrics['mae']:.3f}, "
                f"R²={baseline_metrics.get('r2', 0.0):.3f}"
            )
        print(baseline_msg)

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
        solute_descriptors: Tensor | None = None,
        solvent_descriptors: Tensor | None = None,
        ionic_features: Tensor | None = None,
        solute_descriptor_prior_features: Tensor | None = None,
        solvent_descriptor_prior_features: Tensor | None = None,
        solute_group_prior_features: Tensor | None = None,
        solvent_group_prior_features: Tensor | None = None,
        unifac_ln_gamma_inf: Tensor | None = None,
        unifac_gamma_mask: Tensor | None = None,
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
        _, g_sol_payload, _, _ = model._encode_and_readout(
            sol_batch, "solute", temp_feat=encoder_t_feat
        )
        _, g_slv_payload, _, _ = model._encode_and_readout(
            slv_batch, "solvent", temp_feat=encoder_t_feat
        )
        g_sol = g_sol_payload["value"]
        g_slv = g_slv_payload["value"]
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
            g_sol_payload["value"] = g_sol
            g_slv_payload["value"] = g_slv
        sol_prior = None
        slv_prior = None
        sol_group_for_nrtl = None
        slv_group_for_nrtl = None
        unifac_ln_gamma_for_nrtl = None
        unifac_gamma_mask_for_nrtl = None
        if model.cfg.use_descriptor_priors:
            sol_prior, slv_prior = model._require_descriptor_prior_features(
                solute_descriptor_prior_features,
                solvent_descriptor_prior_features,
            )
            sol_prior = sol_prior.to(g_sol)
            slv_prior = slv_prior.to(g_slv)
        if model.cfg.requires_group_prior_features:
            sol_group_for_nrtl, slv_group_for_nrtl = model._require_group_prior_features(
                solute_group_prior_features,
                solvent_group_prior_features,
            )
            sol_group_for_nrtl = sol_group_for_nrtl.to(g_sol)
            slv_group_for_nrtl = slv_group_for_nrtl.to(g_slv)
            if model.cfg.use_group_priors:
                sol_prior = sol_group_for_nrtl
                slv_prior = slv_group_for_nrtl
        if model.cfg.use_unifac_gamma_prior:
            if unifac_ln_gamma_inf is not None:
                unifac_ln_gamma_for_nrtl = unifac_ln_gamma_inf.to(g_sol)
            if unifac_gamma_mask is not None:
                unifac_gamma_mask_for_nrtl = unifac_gamma_mask.to(g_sol.device)
        if model.cfg.use_gc_priors_crystal:
            T_m_gc, dH_fus_gc, dCp_fus_gc = model._require_crystal_gc_priors(
                T_m_gc,
                dH_fus_gc,
                dCp_fus_gc,
            )
            T_m_gc = model._calibrate_gc_tm_prior(T_m_gc.to(g_sol))
            dH_fus_gc = dH_fus_gc.to(g_sol)
            dCp_fus_gc = dCp_fus_gc.to(g_sol)
        g_pair = model._build_pair_representation(
            g_sol_payload,
            g_slv_payload,
        )
        g_pair = model._augment_pair_representation(
            g_pair,
            solute_descriptors=solute_descriptors,
            solvent_descriptors=solvent_descriptors,
        )
        g_pair = model._augment_pair_with_ionic_features(g_pair, ionic_features)
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
        if model.is_cosmo_sac:
            nrtl_params = model._build_sigma_activity_params(g_sol, g_slv)
        else:
            nrtl_params = model.head_nrtl(
                g_pair,
                temp_feat=nrtl_t_feat,
                solute_group_prior_features=sol_group_for_nrtl,
                solvent_group_prior_features=slv_group_for_nrtl,
                unifac_ln_gamma_inf=unifac_ln_gamma_for_nrtl,
                unifac_gamma_mask=unifac_gamma_mask_for_nrtl,
            )
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

        # ln(γ∞): COSMO-SAC from sigma-profiles, or NRTL params directly.
        if model.is_cosmo_sac:
            cosmo = model.sle_solver.cosmo_sac_layer
            lng_inf = cosmo.ln_gamma_inf(
                nrtl_params["p_solute"], nrtl_params["p_solvent"],
                nrtl_params["A_solute"], nrtl_params["A_solvent"],
                None, None, T,
            )
            tau_12 = lng_inf
            tau_21 = torch.zeros_like(lng_inf)
        else:
            nrtl = model.sle_solver.nrtl_layer
            tau_12, tau_21, G_12, G_21 = nrtl.compute_tau_G_from_params(
                nrtl_params,
                T,
            )
            lng_inf = nrtl.ln_gamma_inf(tau_12, tau_21, G_21)

        B = T.shape[0]
        dummy = torch.zeros(B, device=T.device)
        timp_channel_probes = None
        if (
            model.is_timp
            and model.timp_disp_probe is not None
            and model.timp_polar_probe is not None
            and g_sol_payload["disp"] is not None
            and g_sol_payload["polar"] is not None
        ):
            polar_probe = model.timp_polar_probe(g_sol_payload["polar"])
            timp_channel_probes = {
                "delta_d": model.timp_disp_probe(g_sol_payload["disp"]).squeeze(-1),
                "delta_p": polar_probe[:, 0],
                "delta_h": polar_probe[:, 1],
            }

        output = {
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
            "representations": {
                "g_sol_pre": g_sol,
                "g_slv_pre": g_slv,
                "g_sol_post": g_sol,
                "g_slv_post": g_slv,
                "g_pair": g_pair,
            },
        }
        if (
            model.is_timp
            and g_sol_payload["disp"] is not None
            and g_sol_payload["polar"] is not None
            and g_slv_payload["disp"] is not None
            and g_slv_payload["polar"] is not None
        ):
            output["timp_channels"] = {
                "solute_disp": g_sol_payload["disp"],
                "solute_polar": g_sol_payload["polar"],
                "solute_combined": g_sol_payload["combined"],
                "solvent_disp": g_slv_payload["disp"],
                "solvent_polar": g_slv_payload["polar"],
                "solvent_combined": g_slv_payload["combined"],
            }
        if timp_channel_probes is not None:
            output["timp_channel_probes"] = timp_channel_probes
        return output

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
        idac_loader: DataLoader | None = None,
        crystal_loader: DataLoader | None = None,
        sigma_loader: DataLoader | None = None,
        n_phase_epochs: int | None = None,
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
        idac_aux_loss_accum = 0.0
        idac_aux_steps = 0
        idac_aux_raw_accum: dict[str, float] = {}
        idac_steps_target = max(int(self.cfg.idac_aux_steps_per_epoch), 0)
        idac_iter = iter(idac_loader) if idac_loader is not None and idac_steps_target > 0 else None
        crystal_aux_loss_accum = 0.0
        crystal_aux_steps = 0
        crystal_aux_raw_accum: dict[str, float] = {}
        crystal_steps_target = max(int(self.cfg.crystal_aux_steps_per_epoch), 0)
        crystal_iter = (
            iter(crystal_loader)
            if crystal_loader is not None and crystal_steps_target > 0
            else None
        )
        sigma_aux_loss_accum = 0.0
        sigma_aux_steps = 0
        sigma_steps_target = max(int(self.cfg.sigma_aux_steps_per_epoch), 0)
        sigma_iter = (
            iter(sigma_loader)
            if sigma_loader is not None and sigma_steps_target > 0
            else None
        )

        weights = self._weights_for_epoch(
            phase,
            epoch=epoch,
            n_epochs=n_phase_epochs,
        )
        ramp_epochs = max(int(self.cfg.temperature_rescue_ramp_epochs), 0)
        if phase == 2 and ramp_epochs > 0:
            ramp = min(1.0, float(epoch + 1) / float(ramp_epochs))
            for key in (
                "aux_direct_sol",
                "pair_temp_delta",
                "vant_hoff_slope",
                "vant_hoff_intercept",
                "vh_anchor",
            ):
                if key in weights:
                    weights[key] = float(weights[key]) * ramp

        self._set_correction_freeze_for_phase(phase, epoch)

        for batch_idx, (sol_batch, slv_batch, targets) in enumerate(
            progress(
                loader,
                desc=f"Phase {phase} train",
                leave=False,
            ),
            start=1,
        ):
            sol_batch, slv_batch, targets = self._move_batch_to_device(
                (sol_batch, slv_batch, targets)
            )
            T = targets["T"]
            solvent_type = targets.get("solvent_type")
            solute_morgan_fp = targets.get("solute_morgan_fp")
            solvent_morgan_fp = targets.get("solvent_morgan_fp")
            solute_descriptors = targets.get("solute_descriptors")
            solvent_descriptors = targets.get("solvent_descriptors")
            ionic_features = targets.get("ionic_features")
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
            unifac_ln_gamma_inf = targets.get("unifac_ln_gamma_inf")
            unifac_gamma_mask = targets.get("unifac_gamma_mask")
            T_m_gc = targets.get("T_m_gc")
            dH_fus_gc = targets.get("dH_fus_gc")
            dCp_fus_gc = targets.get("dCp_fus_gc")

            if phase == 1 and not self._has_phase1_supervision(targets):
                if idac_iter is not None and idac_aux_steps < idac_steps_target:
                    try:
                        idac_batch = next(idac_iter)
                    except StopIteration:
                        idac_iter = iter(idac_loader)
                        idac_batch = next(idac_iter)
                    aux_loss, aux_dict = self._train_idac_aux_batch(
                        idac_batch,
                        optimizer,
                        phase,
                    )
                    if aux_loss is not None:
                        idac_aux_loss_accum += aux_loss
                        idac_aux_steps += 1
                        for k, v in aux_dict.items():
                            idac_aux_raw_accum[k] = idac_aux_raw_accum.get(k, 0.0) + float(v)
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
                    solute_descriptors=solute_descriptors,
                    solvent_descriptors=solvent_descriptors,
                    ionic_features=ionic_features,
                    solute_descriptor_prior_features=solute_descriptor_prior_features,
                    solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                    solute_group_prior_features=solute_group_prior_features,
                    solvent_group_prior_features=solvent_group_prior_features,
                    unifac_ln_gamma_inf=unifac_ln_gamma_inf,
                    unifac_gamma_mask=unifac_gamma_mask,
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
                    solute_descriptors=solute_descriptors,
                    solvent_descriptors=solvent_descriptors,
                    ionic_features=ionic_features,
                    solute_descriptor_prior_features=solute_descriptor_prior_features,
                    solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                    solute_group_prior_features=solute_group_prior_features,
                    solvent_group_prior_features=solvent_group_prior_features,
                    T_m_gc=T_m_gc,
                    dH_fus_gc=dH_fus_gc,
                    dCp_fus_gc=dCp_fus_gc,
                    targets=targets,
                    detach_crystal_from_encoder=(
                        self.cfg.detach_crystal_from_encoder and phase == 2
                    ),
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
                solute_descriptors=solute_descriptors,
                solvent_descriptors=solvent_descriptors,
                ionic_features=ionic_features,
                solute_descriptor_prior_features=solute_descriptor_prior_features,
                solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                solute_group_prior_features=solute_group_prior_features,
                solvent_group_prior_features=solvent_group_prior_features,
                T_m_gc=T_m_gc,
                dH_fus_gc=dH_fus_gc,
                dCp_fus_gc=dCp_fus_gc,
                detach_crystal_from_encoder=(
                    self.cfg.detach_crystal_from_encoder and phase == 2
                ),
            )

            loss.backward()
            grad_params = list(self.model.parameters())
            if self.cfg.use_hansen_contrastive:
                grad_params.extend(self.loss_fn.parameters())
            torch.nn.utils.clip_grad_norm_(
                grad_params, self.cfg.grad_clip,
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

            if idac_iter is not None and idac_aux_steps < idac_steps_target:
                try:
                    idac_batch = next(idac_iter)
                except StopIteration:
                    idac_iter = iter(idac_loader)
                    idac_batch = next(idac_iter)
                aux_loss, aux_dict = self._train_idac_aux_batch(
                    idac_batch,
                    optimizer,
                    phase,
                )
                if aux_loss is not None:
                    idac_aux_loss_accum += aux_loss
                    idac_aux_steps += 1
                    for k, v in aux_dict.items():
                        idac_aux_raw_accum[k] = idac_aux_raw_accum.get(k, 0.0) + float(v)

            if crystal_iter is not None and crystal_aux_steps < crystal_steps_target:
                try:
                    crystal_batch = next(crystal_iter)
                except StopIteration:
                    crystal_iter = iter(crystal_loader)
                    crystal_batch = next(crystal_iter)
                aux_loss, aux_dict = self._train_crystal_aux_batch(
                    crystal_batch,
                    optimizer,
                    phase,
                )
                if aux_loss is not None:
                    crystal_aux_loss_accum += aux_loss
                    crystal_aux_steps += 1
                    for k, v in aux_dict.items():
                        crystal_aux_raw_accum[k] = (
                            crystal_aux_raw_accum.get(k, 0.0) + float(v)
                        )

            if sigma_iter is not None and sigma_aux_steps < sigma_steps_target:
                try:
                    sigma_batch = next(sigma_iter)
                except StopIteration:
                    sigma_iter = iter(sigma_loader)
                    sigma_batch = next(sigma_iter)
                aux_loss, _ = self._train_sigma_aux_batch(sigma_batch, optimizer, phase)
                if aux_loss is not None:
                    sigma_aux_loss_accum += aux_loss
                    sigma_aux_steps += 1

        avg_loss = total_loss / max(n_batches, 1)
        avg_raw_components = {
            k: v / max(n_batches, 1) for k, v in loss_accum.items()
        }
        avg_weighted_components = {
            k: v / max(n_batches, 1) for k, v in weighted_loss_accum.items()
        }
        if idac_aux_steps > 0:
            avg_raw_components["idac_aux_total"] = (
                idac_aux_loss_accum / idac_aux_steps
            )
            avg_weighted_components["idac_aux_total"] = (
                idac_aux_loss_accum / idac_aux_steps
            )
            for key, value in idac_aux_raw_accum.items():
                component = f"idac_aux_{key}"
                avg_raw_components[component] = value / idac_aux_steps
                avg_weighted_components[component] = (
                    self._idac_aux_weight(phase)
                    * avg_raw_components[component]
                    if key in {"gamma_inf", "gamma_2"}
                    else 0.0
                )
        if crystal_aux_steps > 0:
            avg_raw_components["crystal_aux_total"] = (
                crystal_aux_loss_accum / crystal_aux_steps
            )
            avg_weighted_components["crystal_aux_total"] = (
                crystal_aux_loss_accum / crystal_aux_steps
            )
            for key, value in crystal_aux_raw_accum.items():
                component = f"crystal_aux_{key}"
                avg_raw_components[component] = value / crystal_aux_steps
                avg_weighted_components[component] = (
                    self._crystal_aux_weight(phase)
                    * avg_raw_components[component]
                    if key in {"T_m", "dH"}
                    else 0.0
                )
        if sigma_aux_steps > 0:
            avg_raw_components["sigma_aux_total"] = sigma_aux_loss_accum / sigma_aux_steps
            avg_weighted_components["sigma_aux_total"] = (
                sigma_aux_loss_accum / sigma_aux_steps
            )
        self._maybe_release_device_cache(force=True)
        component_weights = {
            key: self._effective_loss_weight(key, weights)
            for key in avg_raw_components
        }
        if idac_aux_steps > 0:
            component_weights["idac_aux_total"] = 1.0
            component_weights["idac_aux_gamma_inf"] = self._idac_aux_weight(phase)
            component_weights["idac_aux_gamma_2"] = self._idac_aux_weight(phase)
        if crystal_aux_steps > 0:
            component_weights["crystal_aux_total"] = 1.0
            component_weights["crystal_aux_T_m"] = self._crystal_aux_weight(phase)
            component_weights["crystal_aux_dH"] = self._crystal_aux_weight(phase)
        if sigma_aux_steps > 0:
            component_weights["sigma_aux_total"] = 1.0

        return avg_loss, {
            "raw": avg_raw_components,
            "weighted": avg_weighted_components,
            "weights": component_weights,
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
        self,
        loader: DataLoader,
        phase: int,
        *,
        epoch: int | None = None,
        n_phase_epochs: int | None = None,
    ) -> MetricDict:
        """Validate and return metrics dict."""
        self.model.eval()
        total_loss = 0.0
        all_pred, all_true = [], []
        n_batches = 0

        weights = self._weights_for_epoch(
            phase,
            epoch=epoch,
            n_epochs=n_phase_epochs,
        )

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
            solute_descriptors = targets.get("solute_descriptors")
            solvent_descriptors = targets.get("solvent_descriptors")
            ionic_features = targets.get("ionic_features")
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
                    solute_descriptors=solute_descriptors,
                    solvent_descriptors=solvent_descriptors,
                    ionic_features=ionic_features,
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
                    solute_descriptors=solute_descriptors,
                    solvent_descriptors=solvent_descriptors,
                    ionic_features=ionic_features,
                    solute_descriptor_prior_features=solute_descriptor_prior_features,
                    solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                    solute_group_prior_features=solute_group_prior_features,
                    solvent_group_prior_features=solvent_group_prior_features,
                    T_m_gc=T_m_gc,
                    dH_fus_gc=dH_fus_gc,
                    dCp_fus_gc=dCp_fus_gc,
                    targets=targets,
                    detach_crystal_from_encoder=(
                        self.cfg.detach_crystal_from_encoder and phase == 2
                    ),
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
        idac_train_loader: DataLoader | None = None,
        crystal_train_loader: DataLoader | None = None,
        sigma_train_loader: DataLoader | None = None,
        start_epoch: int = 0,
        optimizer_state_dict: dict | None = None,
        scheduler_state_dict: dict | None = None,
        on_epoch_end: Callable[[ResumeStateDict], None] | None = None,
    ) -> None:
        """Run a single training phase."""
        self._configure_phase_branch_training(phase)
        initial_weights = self._weights_for_epoch(
            phase,
            epoch=start_epoch,
            n_epochs=n_epochs,
        )
        print(f"\n{'=' * 60}")
        print(f"Phase {phase}: {n_epochs} epochs")
        active = {k: v for k, v in initial_weights.items() if v > 0}
        print(f"Active losses: {active}")
        if start_epoch > 0:
            print(f"Resuming from epoch {start_epoch}/{n_epochs}")
        print(f"{'=' * 60}")

        self._set_correction_freeze_for_phase(phase, start_epoch)
        self._set_gc_prior_residual_freeze(phase, start_epoch)

        optimizer = self._build_optimizer(phase)
        scheduler = self._build_scheduler(optimizer, phase, n_epochs)
        if optimizer_state_dict is not None:
            optimizer.load_state_dict(optimizer_state_dict)
        if scheduler_state_dict is not None:
            scheduler.load_state_dict(scheduler_state_dict)

        # Reset early stopping between phases only when starting a phase fresh.
        if start_epoch == 0:
            self.patience_counter = 0
            if phase >= 2:
                self._initialize_phase_early_stopping(phase, val_loader)
        elif phase >= 2 and self.best_state is None:
            self.best_state = self._clone_model_state()
            self.best_epoch = start_epoch - 1
            self.best_phase = phase

        phase_patience = self._phase_early_stopping_patience(phase)
        phase_min_epochs = self._phase_early_stopping_min_epochs(phase)

        for epoch in progress(
            range(start_epoch, n_epochs),
            desc=f"Phase {phase} epochs",
        ):
            self._set_oracle_injection_prob(phase, epoch, n_epochs)
            self._set_gc_prior_residual_freeze(phase, epoch)
            compute_mono = phase >= 2 and epoch % 5 == 0

            train_loss, train_stats = self.train_epoch(
                train_loader,
                optimizer,
                phase,
                epoch,
                compute_mono,
                idac_loader=idac_train_loader,
                crystal_loader=crystal_train_loader,
                sigma_loader=sigma_train_loader,
                n_phase_epochs=n_epochs,
            )
            val_metrics = self.validate(
                val_loader,
                phase,
                epoch=epoch,
                n_phase_epochs=n_epochs,
            )
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
                    self.best_state = self._clone_model_state()
                    self.best_epoch = epoch
                    self.best_phase = phase
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

            if (
                phase >= 2
                and phase_patience is not None
                and phase_patience >= 0
                and (epoch - start_epoch + 1) >= phase_min_epochs
                and self.patience_counter >= phase_patience
            ):
                best_epoch_str = (
                    f"{self.best_epoch + 1}"
                    if self.best_epoch is not None and self.best_epoch >= 0
                    else "start"
                )
                LOGGER.info(
                    "Early stopping in phase %d at epoch %d. Best %.4f at epoch %s",
                    phase,
                    epoch + 1,
                    self.best_val_loss,
                    best_epoch_str,
                )
                print(
                    f"  Early stopping at epoch {epoch + 1}. "
                    f"Best: {self.best_val_loss:.4f} at epoch {best_epoch_str}"
                )
                if self.best_state is not None:
                    self.model.load_state_dict(self.best_state)
                break

        if phase >= 2 and self.best_state is not None:
            self.model.load_state_dict(self.best_state)
            best_epoch_str = (
                f"{self.best_epoch + 1}"
                if self.best_epoch is not None and self.best_epoch >= 0
                else "start"
            )
            print(
                f"  Restored best Phase {phase} model "
                f"(val MAE = {self.best_val_loss:.4f} at epoch {best_epoch_str})"
            )

    # -------------------------------------------------------------- #
    #  Full training pipeline                                         #
    # -------------------------------------------------------------- #

    def train_full(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        *,
        idac_train_loader: DataLoader | None = None,
        crystal_train_loader: DataLoader | None = None,
        sigma_train_loader: DataLoader | None = None,
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
                idac_train_loader=idac_train_loader,
                crystal_train_loader=crystal_train_loader,
                sigma_train_loader=sigma_train_loader,
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
