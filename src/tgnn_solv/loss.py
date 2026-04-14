"""
Multi-component physics-constrained loss for TGNN-Solv.

Components:
  sol        : Huber loss on ln(x₂) — only for records WITH solubility
  T_m        : MSE on melting point (masked)
  dH         : MSE on fusion enthalpy (masked)
  hansen     : MSE on Hansen parameters (masked)
  gamma_inf  : MSE on ln(γ∞) (masked)
  mono       : Monotonicity penalty (dx₂/dT ≥ 0)
  res        : L2 on effective correction (ln_x2 - ln_x2_physics)
  bridge     : Consistency between Hansen and NRTL γ∞
  tau_reg    : L2 on NRTL τ parameters
  phys_pref  : Encourage high physics confidence
  direct_reg : Keep residual proposal close to physics
  direct_nll : Heteroskedastic NLL on residual proposal
  pair_temp_rank : Same-pair temperature ranking consistency
  vant_hoff_local : Local linearity in ln(x₂) vs 1/T for same-pair batches
  moe_balance: Encourage balanced MoE expert usage
  walden    : Walden-rule entropy-of-fusion consistency for unsupervised samples
  hansen_contrastive_* : Align molecular / TIMP-channel / pair latent distances
                         with Hansen distances when enabled
  aux_direct_sol : training-only direct solubility head on pair representation
                   to feed gradients into interaction layers
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor

from .config import TGNNSolvConfig
from .hansen_contrastive import (
    ChannelHansenContrastiveLoss,
    HansenContrastiveLoss,
    PairHansenContrastiveLoss,
    channel_orthogonality_penalty,
)

if TYPE_CHECKING:
    from .model import TGNNSolv

MIN_VANT_HOFF_INV_T_DIFF = 1.0e-4
MAX_VANT_HOFF_PAIR_LOSS = 100.0


class TGNNSolvLoss(nn.Module):
    """Multi-component loss with adaptive physics correction support."""

    def __init__(
        self,
        cfg: TGNNSolvConfig,
        weights: dict[str, float] | None = None,
    ) -> None:
        super().__init__()
        self.cfg = cfg

        self.default_weights = {
            "sol": 1.0,
            "T_m": 0.3,
            "dH": 0.3,
            "hansen": 0.2,
            "timp_disp_hansen": 0.0,
            "timp_polar_hansen": 0.0,
            "gamma_inf": 0.5,
            "mono": 0.1,
            "res": 0.01,
            "bridge": cfg.bridge_loss_weight,
            "tau_reg": 0.01,
            "phys_pref": 0.1,
            "direct_reg": 0.05,
            "direct_nll": 0.2,
            "pair_temp_rank": 0.0,
            "vant_hoff_local": 0.0,
            "moe_balance": 0.02,
            "descriptor_prior": 0.0,
            "group_prior": 0.0,
            "hansen_contrastive_mol": 0.0,
            "hansen_contrastive_channel": 0.0,
            "hansen_contrastive_pair": 0.0,
            "hansen_channel_orth": 0.0,
            "aux_direct_sol": 0.0,
        }
        if weights is not None:
            self.default_weights.update(weights)

        self.S_Tm = 50.0
        self.S_dH = 5000.0
        self.S_hansen = 5.0
        self.S_bridge = 3.0
        self.huber_delta = 1.0
        self.hansen_contrastive = HansenContrastiveLoss(
            temperature=cfg.hansen_contrastive_temperature
        )
        self.channel_hansen_contrastive = ChannelHansenContrastiveLoss(
            temperature=cfg.hansen_contrastive_temperature
        )
        self.pair_hansen_contrastive = PairHansenContrastiveLoss(
            temperature=cfg.hansen_contrastive_temperature
        )

    def huber_loss(
        self, pred: Tensor, target: Tensor, delta: float | None = None
    ) -> Tensor:
        if delta is None:
            delta = self.huber_delta
        r = pred - target
        ar = r.abs()
        return torch.where(
            ar <= delta, 0.5 * r ** 2, delta * (ar - 0.5 * delta)
        ).mean()

    def masked_mse(
        self,
        pred: Tensor,
        target: Tensor,
        mask: Tensor,
        scale: float = 1.0,
    ) -> Tensor:
        if mask is None or mask.sum() == 0:
            return torch.tensor(0.0, device=pred.device)
        return ((pred[mask] - target[mask]) / scale).pow(2).mean()

    def _find_grad_anchor(self, value: object) -> Tensor | None:
        """Find a tensor with autograd history inside a nested output structure."""
        if isinstance(value, Tensor):
            return value if value.requires_grad else None
        if isinstance(value, dict):
            for child in value.values():
                anchor = self._find_grad_anchor(child)
                if anchor is not None:
                    return anchor
            return None
        if isinstance(value, (list, tuple)):
            for child in value:
                anchor = self._find_grad_anchor(child)
                if anchor is not None:
                    return anchor
        return None

    def forward(
        self,
        output: dict[str, object],
        targets: dict[str, object],
        weights: dict[str, float] | None = None,
        compute_mono: bool = False,
        T: Tensor | None = None,
        model: TGNNSolv | None = None,
        solute_data: object | None = None,
        solvent_data: object | None = None,
        solvent_type: Tensor | None = None,
        solute_morgan_fp: Tensor | None = None,
        solvent_morgan_fp: Tensor | None = None,
        solute_descriptors: Tensor | None = None,
        solvent_descriptors: Tensor | None = None,
        solute_descriptor_prior_features: Tensor | None = None,
        solvent_descriptor_prior_features: Tensor | None = None,
        solute_group_prior_features: Tensor | None = None,
        solvent_group_prior_features: Tensor | None = None,
        T_m_gc: Tensor | None = None,
        dH_fus_gc: Tensor | None = None,
        dCp_fus_gc: Tensor | None = None,
        detach_crystal_from_encoder: bool = False,
    ) -> tuple[Tensor, dict[str, float]]:
        w = weights if weights is not None else self.default_weights
        losses = {}
        dev = output["ln_x2"].device

        # ============================================================
        # 1. Solubility loss (masked by has_solubility)
        # ============================================================
        sol_mask = targets.get("has_solubility")
        if sol_mask is None:
            sol_mask = torch.ones(
                output["ln_x2"].shape[0], dtype=torch.bool, device=dev
            )
        else:
            sol_mask = sol_mask.to(dev)

        if w.get("sol", 0) > 0 and sol_mask.any():
            losses["sol"] = self.huber_loss(
                output["ln_x2"][sol_mask],
                targets["ln_x2"].to(dev)[sol_mask],
            )

        if (
            w.get("aux_direct_sol", 0) > 0
            and sol_mask.any()
            and isinstance(output.get("ln_x2_aux"), Tensor)
        ):
            losses["aux_direct_sol"] = self.huber_loss(
                output["ln_x2_aux"][sol_mask],
                targets["ln_x2"].to(dev)[sol_mask],
            )

        if (
            w.get("direct_nll", 0) > 0
            and sol_mask.any()
            and "ln_x2_direct" in output
            and "ln_x2_direct_log_sigma" in output
        ):
            mu = output["ln_x2_direct"][sol_mask]
            log_sigma = output["ln_x2_direct_log_sigma"][sol_mask]
            true = targets["ln_x2"].to(dev)[sol_mask]
            res = mu - true
            inv_var = torch.exp(-2.0 * log_sigma)
            losses["direct_nll"] = (
                0.5 * inv_var * res.pow(2) + log_sigma
            ).mean()

        # ============================================================
        # 2. Melting point
        # ============================================================
        if "T_m" in targets and targets.get("T_m_mask") is not None:
            if w.get("T_m", 0) > 0:
                losses["T_m"] = self.masked_mse(
                    output["fusion_params"]["T_m"],
                    targets["T_m"].to(dev),
                    targets["T_m_mask"].to(dev),
                    scale=self.S_Tm,
                )

        # ============================================================
        # 3. Fusion enthalpy
        # ============================================================
        if "dH_fus" in targets and targets.get("dH_mask") is not None:
            if w.get("dH", 0) > 0:
                losses["dH"] = self.masked_mse(
                    output["fusion_params"]["dH_fus"],
                    targets["dH_fus"].to(dev),
                    targets["dH_mask"].to(dev),
                    scale=self.S_dH,
                )

        # ============================================================
        # 4. Hansen parameters
        # ============================================================
        if "hansen_sol" in targets and targets.get("hansen_mask") is not None:
            if w.get("hansen", 0) > 0:
                mask = targets["hansen_mask"].to(dev)
                if mask.sum() > 0:
                    pred_h = output["hansen_sol"][mask]
                    tgt_h = targets["hansen_sol"].to(dev)[mask]
                    losses["hansen"] = (
                        ((pred_h - tgt_h) / self.S_hansen).pow(2).mean()
                    )
            if (
                "timp_channel_probes" in output
                and isinstance(output["timp_channel_probes"], dict)
            ):
                mask = targets["hansen_mask"].to(dev)
                probes = output["timp_channel_probes"]
                target_hansen = targets["hansen_sol"].to(dev)
                if w.get("timp_disp_hansen", 0) > 0 and mask.sum() > 0:
                    pred_delta_d = probes["delta_d"][mask]
                    true_delta_d = target_hansen[mask, 0]
                    losses["timp_disp_hansen"] = (
                        ((pred_delta_d - true_delta_d) / self.S_hansen).pow(2).mean()
                    )
                if w.get("timp_polar_hansen", 0) > 0 and mask.sum() > 0:
                    pred_delta_p = probes["delta_p"][mask]
                    pred_delta_h = probes["delta_h"][mask]
                    true_delta_p = target_hansen[mask, 1]
                    true_delta_h = target_hansen[mask, 2]
                    losses["timp_polar_hansen"] = (
                        ((pred_delta_p - true_delta_p) / self.S_hansen).pow(2).mean()
                        + ((pred_delta_h - true_delta_h) / self.S_hansen).pow(2).mean()
                    )

        # ============================================================
        # 5. Infinite dilution activity coefficient
        # ============================================================
        if "ln_gamma_inf" in targets and targets.get("gamma_mask") is not None:
            if w.get("gamma_inf", 0) > 0:
                mask = targets["gamma_mask"].to(dev)
                if mask.sum() > 0:
                    losses["gamma_inf"] = (
                        output["physics"]["ln_gamma_inf"][mask]
                        - targets["ln_gamma_inf"].to(dev)[mask]
                    ).pow(2).mean()

        # ============================================================
        # 6. Monotonicity penalty (dx₂/dT ≥ 0)
        # ============================================================
        if compute_mono and T is not None and model is not None:
            if w.get("mono", 0) > 0:
                losses["mono"] = self._monotonicity_loss(
                    model,
                    solute_data,
                    solvent_data,
                    T,
                    targets=targets,
                    solvent_type=solvent_type,
                    solute_morgan_fp=solute_morgan_fp,
                    solvent_morgan_fp=solvent_morgan_fp,
                    solute_descriptors=solute_descriptors,
                    solvent_descriptors=solvent_descriptors,
                    solute_descriptor_prior_features=solute_descriptor_prior_features,
                    solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                    solute_group_prior_features=solute_group_prior_features,
                    solvent_group_prior_features=solvent_group_prior_features,
                    T_m_gc=T_m_gc,
                    dH_fus_gc=dH_fus_gc,
                    dCp_fus_gc=dCp_fus_gc,
                    detach_crystal_from_encoder=detach_crystal_from_encoder,
                )

        # ============================================================
        # 7. Effective correction magnitude
        # ============================================================
        if "correction" in output:
            if w.get("res", 0) > 0:
                losses["res"] = output["correction"].pow(2).mean()

        # ============================================================
        # 8. Hansen-NRTL bridge consistency
        # ============================================================
        if ("hansen_sol" in output and "hansen_slv" in output
                and T is not None):
            if w.get("bridge", 0) > 0:
                losses["bridge"] = self._bridge_loss(output, T.to(dev))

        # ============================================================
        # 9. τ regularization
        # ============================================================
        physics = output.get("physics", {})
        if "tau_12" in physics:
            if w.get("tau_reg", 0) > 0:
                losses["tau_reg"] = (
                    physics["tau_12"].pow(2).mean()
                    + physics["tau_21"].pow(2).mean()
                )

        # ============================================================
        # 10. Physics preference: encourage high confidence
        # ============================================================
        if "confidence" in output:
            if w.get("phys_pref", 0) > 0:
                losses["phys_pref"] = (1.0 - output["confidence"]).mean()

        # ============================================================
        # 11. Direct path regularization
        # ============================================================
        if "ln_x2_direct" in output and "physics" in output:
            if w.get("direct_reg", 0) > 0:
                losses["direct_reg"] = (
                    output["ln_x2_direct"]
                    - output["physics"]["ln_x2"].detach()
                ).pow(2).mean()

        # ============================================================
        # 12. Same-pair temperature consistency
        # ============================================================
        pair_keys = targets.get("pair_key")
        if pair_keys is not None and T is not None:
            if w.get("pair_temp_rank", 0) > 0 or w.get("vant_hoff_local", 0) > 0:
                pair_losses = self._pair_temperature_losses(
                    output["ln_x2"],
                    T.to(dev),
                    pair_keys,
                )
                if w.get("pair_temp_rank", 0) > 0:
                    losses["pair_temp_rank"] = pair_losses["pair_temp_rank"]
                if w.get("vant_hoff_local", 0) > 0:
                    losses["vant_hoff_local"] = pair_losses["vant_hoff_local"]

        # ============================================================
        # 13. MoE balance (expert usage)
        # ============================================================
        moe_gate = output.get("moe_gate")
        if moe_gate is not None and w.get("moe_balance", 0) > 0:
            avg_gate = moe_gate.mean(dim=0)
            target = torch.full_like(
                avg_gate, 1.0 / max(avg_gate.numel(), 1)
            )
            losses["moe_balance"] = (avg_gate - target).pow(2).mean()

        descriptor_prior_reg = output.get("descriptor_prior_reg")
        if (
            isinstance(descriptor_prior_reg, Tensor)
            and w.get("descriptor_prior", 0) > 0
        ):
            losses["descriptor_prior"] = descriptor_prior_reg

        group_prior_reg = output.get("group_prior_reg")
        if (
            isinstance(group_prior_reg, Tensor)
            and w.get("group_prior", 0) > 0
        ):
            losses["group_prior"] = group_prior_reg

        if self.cfg.use_hansen_contrastive:
            representations = output.get("representations", {})
            if not isinstance(representations, dict):
                representations = {}
            g_sol = representations.get("g_sol_pre")
            if (
                isinstance(g_sol, Tensor)
                and w.get("hansen_contrastive_mol", 0) > 0
            ):
                hansen_target = targets.get(
                    "hansen_sol_effective",
                    targets.get("hansen_sol"),
                )
                hansen_mask = targets.get(
                    "hansen_contrastive_mask",
                    targets.get("hansen_mask"),
                )
                if isinstance(hansen_target, Tensor) and isinstance(hansen_mask, Tensor):
                    sample_weight = targets.get("hansen_sol_contrastive_weight")
                    losses["hansen_contrastive_mol"] = self.hansen_contrastive(
                        g_sol,
                        hansen_target.to(dev),
                        hansen_mask.to(dev),
                        sample_weight=(
                            sample_weight.to(dev)
                            if isinstance(sample_weight, Tensor)
                            else None
                        ),
                    )

            timp_channels = output.get("timp_channels", {})
            if not isinstance(timp_channels, dict):
                timp_channels = {}
            g_disp = timp_channels.get("solute_disp")
            g_polar = timp_channels.get("solute_polar")
            if w.get("hansen_contrastive_channel", 0) > 0:
                hansen_target = targets.get(
                    "hansen_sol_effective",
                    targets.get("hansen_sol"),
                )
                hansen_mask = targets.get(
                    "hansen_contrastive_mask",
                    targets.get("hansen_mask"),
                )
                if isinstance(hansen_target, Tensor) and isinstance(hansen_mask, Tensor):
                    sample_weight = targets.get("hansen_sol_contrastive_weight")
                    losses["hansen_contrastive_channel"] = (
                        self.channel_hansen_contrastive(
                            g_disp if isinstance(g_disp, Tensor) else None,
                            g_polar if isinstance(g_polar, Tensor) else None,
                            hansen_target.to(dev),
                            hansen_mask.to(dev),
                            sample_weight=(
                                sample_weight.to(dev)
                                if isinstance(sample_weight, Tensor)
                                else None
                            ),
                        )
                    )
            if (
                isinstance(g_disp, Tensor)
                and isinstance(g_polar, Tensor)
                and w.get("hansen_channel_orth", 0) > 0
            ):
                losses["hansen_channel_orth"] = channel_orthogonality_penalty(
                    g_disp,
                    g_polar,
                )

            g_pair = representations.get("g_pair")
            pair_Ra = targets.get("pair_Ra")
            pair_mask = targets.get("pair_hansen_mask")
            if (
                isinstance(g_pair, Tensor)
                and isinstance(pair_Ra, Tensor)
                and isinstance(pair_mask, Tensor)
                and w.get("hansen_contrastive_pair", 0) > 0
            ):
                pair_weight = targets.get("pair_hansen_weight")
                losses["hansen_contrastive_pair"] = self.pair_hansen_contrastive(
                    g_pair,
                    pair_Ra.to(dev),
                    pair_mask.to(dev),
                    sample_weight=(
                        pair_weight.to(dev)
                        if isinstance(pair_weight, Tensor)
                        else None
                    ),
                )

        if self.cfg.use_walden_check and self.cfg.walden_weight > 0:
            losses["walden"] = self._walden_loss(output, targets, dev)

        # ============================================================
        # Weighted sum
        # ============================================================
        anchor = self._find_grad_anchor(output)
        if anchor is not None:
            total = anchor.sum() * 0.0
        else:
            total = torch.zeros((), device=dev)
        for key, val in losses.items():
            wt = w.get(key, 0.0)
            if wt > 0:
                total = total + wt * val
        if self.cfg.use_walden_check and self.cfg.walden_weight > 0:
            total = total + self.cfg.walden_weight * losses["walden"]

        return total, {k: v.item() for k, v in losses.items()}

    def _bridge_loss(self, output: dict[str, object], T: Tensor) -> Tensor:
        """Consistency: Hansen-estimated γ∞ ≈ NRTL γ∞."""
        h_sol = output["hansen_sol"]
        h_slv = output["hansen_slv"]
        diff_sq = (h_sol - h_slv).pow(2).sum(dim=-1)

        V2 = output.get("aux_sol", {}).get(
            "V_m", torch.full_like(T, 100.0)
        )
        lng_hansen = V2 * diff_sq / (self.cfg.R * T)
        lng_nrtl = output["physics"]["ln_gamma_inf"]

        return ((lng_nrtl - lng_hansen) / self.S_bridge).pow(2).mean()

    def _walden_loss(
        self,
        output: dict[str, object],
        targets: dict[str, object],
        dev: torch.device,
    ) -> Tensor:
        """Penalize implausible fusion entropy only on unsupervised samples."""
        fusion_params = output.get("fusion_params", {})
        T_m_pred = fusion_params.get("T_m")
        dH_fus_pred = fusion_params.get("dH_fus")
        if not isinstance(T_m_pred, Tensor) or not isinstance(dH_fus_pred, Tensor):
            return torch.zeros((), device=dev)

        T_m_mask = targets.get("T_m_mask")
        if T_m_mask is None:
            T_m_mask = targets.get("has_T_m")
        dH_mask = targets.get("dH_mask")
        if dH_mask is None:
            dH_mask = targets.get("has_dH_fus")

        if isinstance(T_m_mask, Tensor) and isinstance(dH_mask, Tensor):
            mask_unsup = ~(T_m_mask.to(dev).bool() & dH_mask.to(dev).bool())
        else:
            mask_unsup = torch.ones_like(T_m_pred, dtype=torch.bool, device=dev)

        if not mask_unsup.any():
            return torch.zeros((), device=dev)

        dS_fus = dH_fus_pred / T_m_pred.clamp_min(self.cfg.eps)
        deviation = (dS_fus - self.cfg.walden_target).abs()
        walden_penalty = (
            torch.clamp(deviation - self.cfg.walden_tolerance, min=0.0) ** 2
        )
        mask_unsup_f = mask_unsup.float()
        return (walden_penalty * mask_unsup_f).sum() / mask_unsup_f.sum().clamp_min(1.0)

    def _pair_temperature_losses(
        self,
        pred_ln_x2: Tensor,
        T: Tensor,
        pair_keys: list[str] | tuple[str, ...],
    ) -> dict[str, Tensor]:
        """Same-pair temperature ranking and local van't Hoff consistency."""
        groups: dict[str, list[int]] = {}
        for idx, key in enumerate(pair_keys):
            groups.setdefault(str(key), []).append(idx)

        rank_losses = []
        vant_hoff_losses = []

        for indices in groups.values():
            if len(indices) < 2:
                continue

            idx_tensor = torch.tensor(indices, device=pred_ln_x2.device, dtype=torch.long)
            T_group = T[idx_tensor]
            pred_group = pred_ln_x2[idx_tensor]
            order = torch.argsort(T_group)
            T_sorted = T_group[order]
            pred_sorted = pred_group[order]

            delta_pred = pred_sorted[1:] - pred_sorted[:-1]
            rank_losses.append(F.relu(-delta_pred).mean())

            if len(indices) >= 3:
                inv_T = 1.0 / T_sorted.clamp(min=self.cfg.eps)
                inv_T_diff = inv_T[1:] - inv_T[:-1]
                inv_T_sign = torch.where(
                    inv_T_diff < 0,
                    -torch.ones_like(inv_T_diff),
                    torch.ones_like(inv_T_diff),
                )
                inv_T_diff_safe = inv_T_sign * torch.clamp(
                    inv_T_diff.abs(),
                    min=MIN_VANT_HOFF_INV_T_DIFF,
                )
                local_slopes = (
                    pred_sorted[1:] - pred_sorted[:-1]
                ) / inv_T_diff_safe
                per_pair_vh = (local_slopes[1:] - local_slopes[:-1]).pow(2)
                per_pair_vh = torch.clamp(
                    per_pair_vh,
                    max=MAX_VANT_HOFF_PAIR_LOSS,
                )
                vant_hoff_losses.append(per_pair_vh.mean())

        zero = pred_ln_x2.new_zeros(())
        return {
            "pair_temp_rank": torch.stack(rank_losses).mean() if rank_losses else zero,
            "vant_hoff_local": (
                torch.stack(vant_hoff_losses).mean() if vant_hoff_losses else zero
            ),
        }

    def _monotonicity_loss(
        self,
        model: TGNNSolv,
        solute_data: object,
        solvent_data: object,
        T: Tensor,
        targets: dict[str, object] | None = None,
        solvent_type: Tensor | None = None,
        solute_morgan_fp: Tensor | None = None,
        solvent_morgan_fp: Tensor | None = None,
        solute_descriptors: Tensor | None = None,
        solvent_descriptors: Tensor | None = None,
        solute_descriptor_prior_features: Tensor | None = None,
        solvent_descriptor_prior_features: Tensor | None = None,
        solute_group_prior_features: Tensor | None = None,
        solvent_group_prior_features: Tensor | None = None,
        T_m_gc: Tensor | None = None,
        dH_fus_gc: Tensor | None = None,
        dCp_fus_gc: Tensor | None = None,
        detach_crystal_from_encoder: bool = False,
    ) -> Tensor:
        """Penalize dx₂/dT < 0 using the configured solver path."""
        T_var = T.detach().requires_grad_(True)
        saved = model.cfg.use_implicit_diff
        if model.cfg.monotonicity_force_explicit:
            model.cfg.use_implicit_diff = False

        try:
            with torch.enable_grad():
                out = model(
                    solute_data,
                    solvent_data,
                    T_var,
                    solvent_type=solvent_type,
                    solute_morgan_fp=solute_morgan_fp,
                    solvent_morgan_fp=solvent_morgan_fp,
                    solute_descriptors=solute_descriptors,
                    solvent_descriptors=solvent_descriptors,
                    solute_descriptor_prior_features=solute_descriptor_prior_features,
                    solvent_descriptor_prior_features=solvent_descriptor_prior_features,
                    solute_group_prior_features=solute_group_prior_features,
                    solvent_group_prior_features=solvent_group_prior_features,
                    T_m_gc=T_m_gc,
                    dH_fus_gc=dH_fus_gc,
                    dCp_fus_gc=dCp_fus_gc,
                    targets=targets,
                    detach_crystal_from_encoder=detach_crystal_from_encoder,
                )
                d_lnx2_dT = torch.autograd.grad(
                    out["ln_x2"].sum(),
                    T_var,
                    create_graph=False,
                    retain_graph=False,
                )[0]
        finally:
            model.cfg.use_implicit_diff = saved

        violation = F.relu(-d_lnx2_dT)
        return violation.mean()
