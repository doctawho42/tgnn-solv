"""
Solid-Liquid Equilibrium (SLE) solver.

Solves:  x₂ · γ₂(x₂, T) = exp(-Φ(T))

where Φ is the ideal (crystal) contribution and γ₂ comes from NRTL.

Two modes:
  - Successive substitution (always used at eval)
  - Implicit differentiation (optional at training for stable gradients)
"""

from typing import Dict, Optional

import torch
import torch.nn as nn

from .config import TGNNSolvConfig
from .layers import IdealSolubilityLayer, NRTLLayer, HansenDistanceLayer


# ================================================================== #
#  Implicit-differentiation autograd Function                         #
# ================================================================== #

class SLESolverFunction(torch.autograd.Function):
    """
    Custom autograd for the fixed-point SLE solution.

    Forward: run successive substitution (no gradient tracking).
    Backward: use the implicit function theorem to compute exact
    gradients through the converged fixed point.
    """

    @staticmethod
    def forward(
        ctx,
        Phi, a_12, b_12, c_12, a_21, b_21, c_21, alpha_12,
        T, n_iter, damping, nrtl_layer,
    ):
        tau_12, tau_21, G_12, G_21 = nrtl_layer.compute_tau_G(
            a_12, b_12, c_12, a_21, b_21, c_21, alpha_12, T
        )

        x2 = torch.exp(-Phi).clamp(1e-10, 1.0 - 1e-10)

        # Fixed-point iteration (no grad)
        with torch.no_grad():
            for _ in range(n_iter):
                x1 = 1.0 - x2
                lng2 = nrtl_layer.ln_gamma_2(
                    x1, x2, tau_12, tau_21, G_12, G_21
                )
                x2_new = torch.exp(-Phi - lng2).clamp(1e-10, 1.0 - 1e-10)
                x2 = damping * x2_new + (1.0 - damping) * x2

        x1 = 1.0 - x2
        lng2_final = nrtl_layer.ln_gamma_2(
            x1, x2, tau_12, tau_21, G_12, G_21
        )

        ctx.save_for_backward(
            x2, Phi, a_12, b_12, c_12, a_21, b_21, c_21, alpha_12,
            T, tau_12, tau_21, G_12, G_21, lng2_final,
        )
        ctx.nrtl_layer = nrtl_layer
        return x2, lng2_final

    @staticmethod
    def backward(ctx, grad_x2, grad_lng2):
        (
            x2, Phi, a_12, b_12, c_12, a_21, b_21, c_21, alpha_12,
            T, tau_12, tau_21, G_12, G_21, lng2,
        ) = ctx.saved_tensors
        nrtl = ctx.nrtl_layer

        # Custom backward runs under no_grad by default.
        # We need enable_grad for internal autograd.grad calls.
        with torch.enable_grad():
            x2_var = x2.detach().requires_grad_(True)
            x1_var = 1.0 - x2_var
            a12_var = a_12.detach().requires_grad_(True)
            b12_var = b_12.detach().requires_grad_(True)
            c12_var = c_12.detach().requires_grad_(True)
            a21_var = a_21.detach().requires_grad_(True)
            b21_var = b_21.detach().requires_grad_(True)
            c21_var = c_21.detach().requires_grad_(True)
            alpha_var = alpha_12.detach().requires_grad_(True)

            tau12_v, tau21_v, G12_v, G21_v = nrtl.compute_tau_G(
                a12_var, b12_var, c12_var, a21_var, b21_var, c21_var,
                alpha_var, T
            )
            lng2_v = nrtl.ln_gamma_2(
                x1_var, x2_var, tau12_v, tau21_v, G12_v, G21_v
            )

            # d ln(γ₂) / d x₂
            eta = torch.autograd.grad(
                lng2_v.sum(), x2_var,
                retain_graph=True, allow_unused=True,
            )[0]
            if eta is None:
                eta = torch.zeros_like(x2)

            # dF/dx₂ = 1 + x₂ · η
            dF_dx2 = 1.0 + x2 * eta
            sign = torch.sign(dF_dx2)
            sign = torch.where(sign == 0, torch.ones_like(sign), sign)
            dF_dx2 = torch.where(dF_dx2.abs() < 0.01, sign * 0.01, dF_dx2)

            # Implicit multiplier
            implicit_mult = -grad_x2 / dF_dx2

            # ∂F/∂Φ = +x₂
            grad_Phi = implicit_mult * x2

            # Gradients w.r.t. NRTL parameters
            param_vars = [
                a12_var, b12_var, c12_var,
                a21_var, b21_var, c21_var,
                alpha_var,
            ]
            grad_params = torch.autograd.grad(
                lng2_v,
                param_vars,
                grad_outputs=implicit_mult * x2,
                retain_graph=False,
                allow_unused=True,
            )

        # Direct gradient from ln_gamma_2 loss (if present)
        if grad_lng2 is not None:
            with torch.enable_grad():
                x2_v2 = x2.detach().requires_grad_(True)
                x1_v2 = 1.0 - x2_v2
                a12_v2 = a_12.detach().requires_grad_(True)
                b12_v2 = b_12.detach().requires_grad_(True)
                c12_v2 = c_12.detach().requires_grad_(True)
                a21_v2 = a_21.detach().requires_grad_(True)
                b21_v2 = b_21.detach().requires_grad_(True)
                c21_v2 = c_21.detach().requires_grad_(True)
                alpha_v2 = alpha_12.detach().requires_grad_(True)

                t12, t21, g12, g21 = nrtl.compute_tau_G(
                    a12_v2, b12_v2, c12_v2, a21_v2, b21_v2, c21_v2,
                    alpha_v2, T
                )
                lng2_v2 = nrtl.ln_gamma_2(x1_v2, x2_v2, t12, t21, g12, g21)

                direct_grads = torch.autograd.grad(
                    lng2_v2,
                    [
                        a12_v2, b12_v2, c12_v2,
                        a21_v2, b21_v2, c21_v2,
                        alpha_v2,
                    ],
                    grad_outputs=grad_lng2,
                    allow_unused=True,
                )

            grad_params = tuple(
                (g1 if g1 is not None else 0) + (g2 if g2 is not None else 0)
                for g1, g2 in zip(grad_params, direct_grads)
            )

        grad_T = torch.zeros_like(T)

        return (
            grad_Phi,
            grad_params[0], grad_params[1], grad_params[2],
            grad_params[3], grad_params[4], grad_params[5],
            grad_params[6],
            grad_T,
            None, None, None,
        )


# ================================================================== #
#  SLE Solver Module                                                  #
# ================================================================== #

class SLESolver(nn.Module):
    """
    Full SLE solver: ideal solubility + NRTL activity coefficient.

    Given predicted crystal params and NRTL params, solves for x₂
    at temperature T via successive substitution.

    Returns a dict with all intermediate quantities for loss and
    interpretability.
    """

    def __init__(self, cfg: TGNNSolvConfig):
        super().__init__()
        self.ideal_layer = IdealSolubilityLayer(R=cfg.R)
        self.nrtl_layer = NRTLLayer(
            R=cfg.R, T_ref=cfg.T_ref,
            tau_clamp=cfg.tau_clamp, eps=cfg.eps,
        )
        self.hansen_layer = HansenDistanceLayer()
        self.cfg = cfg

    def forward(
        self,
        T: torch.Tensor,
        fusion_params: Dict[str, torch.Tensor],
        nrtl_params: Dict[str, torch.Tensor],
        use_implicit: Optional[bool] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Solve SLE for mole-fraction solubility x₂.

        Parameters
        ----------
        T : (B,) temperature [K]
        fusion_params : dict with T_m, dH_fus, dCp_fus
        nrtl_params : dict with tau_a12, tau_b12, tau_c12, tau_a21,
                      tau_b21, tau_c21, alpha_12
        use_implicit : override config setting

        Returns
        -------
        dict with x2, ln_x2, ln_gamma_2, ln_gamma_inf, Phi, x_ideal,
             tau_12, tau_21, G_12, G_21
        """
        # Ideal contribution
        Phi = self.ideal_layer(
            T, fusion_params["T_m"],
            fusion_params["dH_fus"], fusion_params["dCp_fus"],
        )

        n_iter = self.cfg.n_iter_train if self.training else self.cfg.n_iter_eval
        damping = self.cfg.damping
        use_impl = use_implicit if use_implicit is not None else self.cfg.use_implicit_diff

        if "tau_a12" in nrtl_params:
            a12 = nrtl_params["tau_a12"]
            b12 = nrtl_params["tau_b12"]
            c12 = nrtl_params["tau_c12"]
            a21 = nrtl_params["tau_a21"]
            b21 = nrtl_params["tau_b21"]
            c21 = nrtl_params["tau_c21"]
        else:
            a_T12 = nrtl_params["a_T12"]
            a_T21 = nrtl_params["a_T21"]
            a12 = -a_T12
            a21 = -a_T21
            b12 = nrtl_params["dg_12"] / self.cfg.R + a_T12 * self.cfg.T_ref
            b21 = nrtl_params["dg_21"] / self.cfg.R + a_T21 * self.cfg.T_ref
            c12 = torch.zeros_like(a12)
            c21 = torch.zeros_like(a21)

        # Solve
        if use_impl and self.training:
            x2, lng2 = SLESolverFunction.apply(
                Phi,
                a12, b12, c12, a21, b21, c21,
                nrtl_params["alpha_12"],
                T, n_iter, damping, self.nrtl_layer,
            )
            tau_12, tau_21, G_12, G_21 = self.nrtl_layer.compute_tau_G(
                a12, b12, c12, a21, b21, c21, nrtl_params["alpha_12"], T
            )
        else:
            # Explicit successive substitution
            tau_12, tau_21, G_12, G_21 = self.nrtl_layer.compute_tau_G(
                a12, b12, c12, a21, b21, c21, nrtl_params["alpha_12"], T
            )
            x2 = torch.exp(-Phi).clamp(1e-10, 1.0 - 1e-10)
            lng2 = torch.zeros_like(x2)

            for _ in range(n_iter):
                x1 = 1.0 - x2
                lng2 = self.nrtl_layer.ln_gamma_2(
                    x1, x2, tau_12, tau_21, G_12, G_21
                )
                x2_new = torch.exp(-Phi - lng2).clamp(1e-10, 1.0 - 1e-10)
                x2 = damping * x2_new + (1.0 - damping) * x2

        ln_x2 = torch.log(x2 + self.cfg.eps)
        x_ideal = torch.exp(-Phi)
        lng2_inf = self.nrtl_layer.ln_gamma_inf(tau_12, tau_21, G_21)

        return {
            "x2": x2,
            "ln_x2": ln_x2,
            "ln_gamma_2": lng2,
            "ln_gamma_inf": lng2_inf,
            "Phi": Phi,
            "x_ideal": x_ideal.clamp(0, 1),
            "tau_12": tau_12,
            "tau_21": tau_21,
            "G_12": G_12,
            "G_21": G_21,
        }
