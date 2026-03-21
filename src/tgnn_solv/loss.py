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
  direct_reg : Keep direct prediction close to physics
  direct_nll : Heteroskedastic NLL on direct path
  moe_balance: Encourage balanced MoE expert usage
"""

from typing import Dict, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import TGNNSolvConfig


class TGNNSolvLoss(nn.Module):
    """Multi-component loss with adaptive physics correction support."""

    def __init__(
        self,
        cfg: TGNNSolvConfig,
        weights: Optional[Dict[str, float]] = None,
    ):
        super().__init__()
        self.cfg = cfg

        self.default_weights = {
            "sol": 1.0,
            "T_m": 0.3,
            "dH": 0.3,
            "hansen": 0.2,
            "gamma_inf": 0.5,
            "mono": 0.1,
            "res": 0.01,
            "bridge": 0.05,
            "tau_reg": 0.01,
            "phys_pref": 0.1,
            "direct_reg": 0.05,
            "direct_nll": 0.2,
            "moe_balance": 0.02,
        }
        if weights is not None:
            self.default_weights.update(weights)

        self.S_Tm = 50.0
        self.S_dH = 5000.0
        self.S_hansen = 5.0
        self.S_bridge = 3.0
        self.huber_delta = 1.0

    def huber_loss(
        self, pred: torch.Tensor, target: torch.Tensor, delta: float = None
    ) -> torch.Tensor:
        if delta is None:
            delta = self.huber_delta
        r = pred - target
        ar = r.abs()
        return torch.where(
            ar <= delta, 0.5 * r ** 2, delta * (ar - 0.5 * delta)
        ).mean()

    def masked_mse(
        self,
        pred: torch.Tensor,
        target: torch.Tensor,
        mask: torch.Tensor,
        scale: float = 1.0,
    ) -> torch.Tensor:
        if mask is None or mask.sum() == 0:
            return torch.tensor(0.0, device=pred.device)
        return ((pred[mask] - target[mask]) / scale).pow(2).mean()

    def forward(
        self,
        output: Dict,
        targets: Dict,
        weights: Optional[Dict[str, float]] = None,
        compute_mono: bool = False,
        T: Optional[torch.Tensor] = None,
        model: Optional[nn.Module] = None,
        solute_data=None,
        solvent_data=None,
        solvent_type: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
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
                    model, solute_data, solvent_data, T, solvent_type
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
        # 12. MoE balance (expert usage)
        # ============================================================
        moe_gate = output.get("moe_gate")
        if moe_gate is not None and w.get("moe_balance", 0) > 0:
            avg_gate = moe_gate.mean(dim=0)
            target = torch.full_like(
                avg_gate, 1.0 / max(avg_gate.numel(), 1)
            )
            losses["moe_balance"] = (avg_gate - target).pow(2).mean()

        # ============================================================
        # Weighted sum
        # ============================================================
        total = torch.tensor(0.0, device=dev)
        for key, val in losses.items():
            wt = w.get(key, 0.0)
            if wt > 0:
                total = total + wt * val

        return total, {k: v.item() for k, v in losses.items()}

    def _bridge_loss(self, output: Dict, T: torch.Tensor) -> torch.Tensor:
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

    def _monotonicity_loss(
        self, model, solute_data, solvent_data, T, solvent_type=None
    ) -> torch.Tensor:
        """Penalize dx₂/dT < 0. Forces explicit mode."""
        T_var = T.detach().requires_grad_(True)

        saved = model.cfg.use_implicit_diff
        model.cfg.use_implicit_diff = False

        try:
            with torch.enable_grad():
                out = model(
                    solute_data, solvent_data, T_var,
                    solvent_type=solvent_type,
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
