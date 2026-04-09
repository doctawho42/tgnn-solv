"""Higher-precision verification tests for NRTL and the SLE solver."""

from __future__ import annotations

import sys

import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig  # noqa: E402
from tgnn_solv.layers import NRTLLayer  # noqa: E402
from tgnn_solv.solver import SLESolver  # noqa: E402


DTYPE = torch.float64
DELTA_X = 1.0e-6
DELTA_TAU = 1.0e-4


def _scalar(value: float) -> torch.Tensor:
    """Return a 1-element float64 tensor."""
    return torch.tensor([value], dtype=DTYPE)


def _make_solver(**overrides: float | int | bool) -> SLESolver:
    """Build an SLE solver with float64-friendly defaults for verification."""
    cfg = TGNNSolvConfig(
        n_iter_train=50,
        n_iter_eval=50,
        damping=0.7,
        solver_tol_train=1.0e-10,
        solver_tol_eval=1.0e-10,
        solver_adaptive_damping=True,
        use_implicit_diff=True,
    )
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return SLESolver(cfg)


def _direct_nrtl_params(
    tau_12: torch.Tensor,
    tau_21: torch.Tensor,
    alpha_12: torch.Tensor,
) -> dict[str, torch.Tensor]:
    """Build the direct `(tau_12, tau_21)` NRTL parameter layout."""
    return {
        "tau_12": tau_12,
        "tau_21": tau_21,
        "alpha_12": alpha_12,
    }


def _abc_nrtl_params(
    tau_12: torch.Tensor,
    tau_21: torch.Tensor,
    alpha_12: torch.Tensor,
) -> dict[str, torch.Tensor]:
    """Build a constant-in-temperature ABC parameterization."""
    zeros = torch.zeros_like(tau_12)
    return {
        "tau_a12": tau_12,
        "tau_b12": zeros,
        "tau_c12": zeros,
        "tau_a21": tau_21,
        "tau_b21": zeros,
        "tau_c21": zeros,
        "alpha_12": alpha_12,
    }


def _dg_nrtl_params(
    dg_12: torch.Tensor,
    dg_21: torch.Tensor,
    alpha_12: torch.Tensor,
) -> dict[str, torch.Tensor]:
    """Build the energy-based NRTL parameterization used by the main model."""
    zeros = torch.zeros_like(dg_12)
    return {
        "dg_12": dg_12,
        "dg_21": dg_21,
        "a_T12": zeros,
        "a_T21": zeros,
        "alpha_12": alpha_12,
    }


def _fusion_params(
    *,
    T_m: float,
    dH_fus: float,
    dCp_fus: float = 0.0,
) -> dict[str, torch.Tensor]:
    """Build crystal/fusion parameter tensors."""
    return {
        "T_m": _scalar(T_m),
        "dH_fus": _scalar(dH_fus),
        "dCp_fus": _scalar(dCp_fus),
    }


def _sle_log_residual(
    x2: torch.Tensor,
    ln_gamma_2: torch.Tensor,
    Phi: torch.Tensor,
) -> torch.Tensor:
    """Return the log-form SLE residual F = ln(x2) + ln(gamma2) + Phi."""
    return torch.log(x2) + ln_gamma_2 + Phi


def _fixed_point_trace(
    solver: SLESolver,
    *,
    Phi: torch.Tensor,
    tau_12: torch.Tensor,
    tau_21: torch.Tensor,
    G_12: torch.Tensor,
    G_21: torch.Tensor,
    n_iter: int,
    damping: float,
    tol: float,
) -> tuple[int, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Replay the solver's fixed-point iteration and expose the step count."""
    x2 = torch.exp(-Phi).clamp(1.0e-10, 1.0 - 1.0e-10)
    damping_tensor = torch.full_like(x2, damping)
    prev_residual = torch.full_like(x2, float("inf"))

    for iteration in range(1, n_iter + 1):
        x1 = 1.0 - x2
        ln_gamma_2 = solver.nrtl_layer.ln_gamma_2(
            x1, x2, tau_12, tau_21, G_12, G_21
        )
        x2_candidate = torch.exp(-Phi - ln_gamma_2).clamp(1.0e-10, 1.0 - 1.0e-10)
        residual = (torch.log(x2_candidate) - torch.log(x2)).abs()

        if solver.cfg.solver_adaptive_damping:
            damping_tensor = torch.where(
                residual > prev_residual,
                torch.clamp(damping_tensor * 0.5, min=solver.cfg.solver_min_damping),
                torch.clamp(damping_tensor * 1.05, max=1.0),
            )

        x2 = damping_tensor * x2_candidate + (1.0 - damping_tensor) * x2
        prev_residual = residual
        if residual.max() < tol:
            break

    x1 = 1.0 - x2
    ln_gamma_2 = solver.nrtl_layer.ln_gamma_2(x1, x2, tau_12, tau_21, G_12, G_21)
    final_residual = _sle_log_residual(x2, ln_gamma_2, Phi).abs()
    return iteration, x2, ln_gamma_2, final_residual


def _central_difference(
    fn,
    x: torch.Tensor,
    delta: float,
) -> torch.Tensor:
    """Evaluate a scalar central difference using torch tensors only."""
    delta_tensor = torch.full_like(x, delta)
    return (fn(x + delta_tensor) - fn(x - delta_tensor)) / (2.0 * delta)


def test_gibbs_duhem_nrtl() -> None:
    """The implemented NRTL formulas should satisfy Gibbs-Duhem numerically."""
    nrtl = NRTLLayer()
    T_ref = _scalar(298.15)

    for tau_12_value in (-2.0, 0.0, 1.0, 3.0, 5.0):
        for tau_21_value in (-2.0, 0.0, 1.0, 3.0, 5.0):
            for alpha_value in (0.2, 0.3, 0.47):
                tau_12 = _scalar(tau_12_value)
                tau_21 = _scalar(tau_21_value)
                alpha_12 = _scalar(alpha_value)
                _, _, G_12, G_21 = nrtl.compute_tau_G_from_params(
                    _direct_nrtl_params(tau_12, tau_21, alpha_12),
                    T_ref,
                )

                for x2_value in (0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99):
                    x2 = _scalar(x2_value)
                    x1 = 1.0 - x2

                    def ln_gamma_1_vs_x1(x1_current: torch.Tensor) -> torch.Tensor:
                        x2_current = 1.0 - x1_current
                        return nrtl.ln_gamma_1(
                            x1_current,
                            x2_current,
                            tau_12,
                            tau_21,
                            G_12,
                            G_21,
                        )

                    def ln_gamma_2_vs_x1(x1_current: torch.Tensor) -> torch.Tensor:
                        x2_current = 1.0 - x1_current
                        return nrtl.ln_gamma_2(
                            x1_current,
                            x2_current,
                            tau_12,
                            tau_21,
                            G_12,
                            G_21,
                        )

                    d_ln_gamma_1_dx1 = _central_difference(
                        ln_gamma_1_vs_x1,
                        x1,
                        DELTA_X,
                    )
                    d_ln_gamma_2_dx1 = _central_difference(
                        ln_gamma_2_vs_x1,
                        x1,
                        DELTA_X,
                    )

                    residual = torch.abs(
                        x1 * d_ln_gamma_1_dx1 + x2 * d_ln_gamma_2_dx1
                    )
                    assert residual.item() < 1.0e-5, (
                        "Gibbs-Duhem residual too large for "
                        f"tau_12={tau_12_value}, tau_21={tau_21_value}, "
                        f"alpha={alpha_value}, x2={x2_value}: "
                        f"{residual.item():.3e}"
                    )


def test_sle_solver_ideal() -> None:
    """For an ideal solution, the solver should match the analytic x2 = exp(-Phi)."""
    solver = _make_solver(n_iter_eval=20, solver_tol_eval=1.0e-12)
    solver.eval()

    T = _scalar(298.15)
    fusion = _fusion_params(T_m=400.0, dH_fus=25000.0, dCp_fus=0.0)
    nrtl_params = _direct_nrtl_params(_scalar(0.0), _scalar(0.0), _scalar(0.3))

    with torch.no_grad():
        out = solver(T, fusion, nrtl_params, use_implicit=False)

    Phi = (fusion["dH_fus"] / solver.cfg.R) * (1.0 / T - 1.0 / fusion["T_m"])
    x2_analytical = torch.exp(-Phi)

    assert torch.allclose(out["x2"], x2_analytical, atol=1.0e-8, rtol=0.0)
    assert torch.allclose(out["ln_gamma_2"], torch.zeros_like(out["ln_gamma_2"]))


def test_sle_solver_known_system() -> None:
    """A known water/ethanol NRTL parameter set should converge to a valid root."""
    solver = _make_solver(n_iter_eval=20, solver_tol_eval=1.0e-8, damping=0.7)
    solver.eval()

    T = _scalar(298.15)
    fusion = _fusion_params(T_m=400.0, dH_fus=25000.0, dCp_fus=0.0)
    nrtl_params = _dg_nrtl_params(_scalar(-120.0), _scalar(1450.0), _scalar(0.30))

    with torch.no_grad():
        out = solver(T, fusion, nrtl_params, use_implicit=False)

    Phi = solver.ideal_layer(T, fusion["T_m"], fusion["dH_fus"], fusion["dCp_fus"])
    tau_12, tau_21, G_12, G_21 = solver.nrtl_layer.compute_tau_G_from_params(
        nrtl_params,
        T,
    )
    iterations, x2_trace, ln_gamma_2_trace, final_residual = _fixed_point_trace(
        solver,
        Phi=Phi,
        tau_12=tau_12,
        tau_21=tau_21,
        G_12=G_12,
        G_21=G_21,
        n_iter=20,
        damping=0.7,
        tol=1.0e-8,
    )

    assert iterations <= 20
    assert torch.allclose(out["x2"], x2_trace, atol=1.0e-10, rtol=0.0)
    assert torch.allclose(
        out["ln_gamma_2"],
        ln_gamma_2_trace,
        atol=1.0e-10,
        rtol=0.0,
    )
    assert final_residual.item() < 1.0e-8
    assert _sle_log_residual(out["x2"], out["ln_gamma_2"], out["Phi"]).abs().item() < 1.0e-8


def test_implicit_gradient_vs_finite_difference() -> None:
    """The implicit gradient d(ln x2*)/d(tau_12) should match finite differences."""
    solver = _make_solver(
        n_iter_train=60,
        n_iter_eval=60,
        solver_tol_train=1.0e-10,
        solver_tol_eval=1.0e-10,
        damping=0.7,
    )

    T = _scalar(315.0)
    fusion = _fusion_params(T_m=420.0, dH_fus=22000.0, dCp_fus=40.0)

    tau_a12 = _scalar(0.4).requires_grad_(True)
    base_params = {
        "tau_b12": _scalar(0.0),
        "tau_c12": _scalar(0.0),
        "tau_a21": _scalar(0.2),
        "tau_b21": _scalar(0.0),
        "tau_c21": _scalar(0.0),
        "alpha_12": _scalar(0.3),
    }

    solver.train()
    implicit_params = dict(base_params)
    implicit_params["tau_a12"] = tau_a12
    out_impl = solver(T, fusion, implicit_params, use_implicit=True)
    grad_impl = torch.autograd.grad(out_impl["ln_x2"].sum(), tau_a12)[0]

    solver.eval()

    def eval_ln_x2(tau_value: float) -> torch.Tensor:
        params = dict(base_params)
        params["tau_a12"] = _scalar(tau_value)
        return solver(T, fusion, params, use_implicit=False)["ln_x2"]

    grad_fd = (
        eval_ln_x2(0.4 + DELTA_TAU) - eval_ln_x2(0.4 - DELTA_TAU)
    ) / (2.0 * DELTA_TAU)

    rel_error = (grad_impl - grad_fd).abs() / grad_fd.abs().clamp(min=1.0e-12)
    assert rel_error.item() < 1.0e-3, (
        f"Implicit/FD mismatch: implicit={grad_impl.item():.6e}, "
        f"finite_diff={grad_fd.item():.6e}, rel_error={rel_error.item():.3e}"
    )


def test_damping_convergence() -> None:
    """The damped fixed-point solver should converge for a high-solubility system."""
    solver = _make_solver(n_iter_eval=30, solver_tol_eval=1.0e-8, damping=0.7)
    solver.eval()

    T = _scalar(340.0)
    fusion = _fusion_params(T_m=350.0, dH_fus=20000.0, dCp_fus=0.0)
    nrtl_params = _direct_nrtl_params(_scalar(0.5), _scalar(0.5), _scalar(0.3))

    with torch.no_grad():
        out = solver(T, fusion, nrtl_params, use_implicit=False)

    Phi = solver.ideal_layer(T, fusion["T_m"], fusion["dH_fus"], fusion["dCp_fus"])
    tau_12, tau_21, G_12, G_21 = solver.nrtl_layer.compute_tau_G_from_params(
        nrtl_params,
        T,
    )
    iterations, x2_trace, ln_gamma_2_trace, final_residual = _fixed_point_trace(
        solver,
        Phi=Phi,
        tau_12=tau_12,
        tau_21=tau_21,
        G_12=G_12,
        G_21=G_21,
        n_iter=30,
        damping=0.7,
        tol=1.0e-8,
    )

    assert iterations <= 30
    assert 0.0 < out["x2"].item() < 1.0
    assert torch.isfinite(out["ln_gamma_2"]).all()
    assert torch.allclose(out["x2"], x2_trace, atol=1.0e-10, rtol=0.0)
    assert torch.allclose(out["ln_gamma_2"], ln_gamma_2_trace, atol=1.0e-10, rtol=0.0)
    assert final_residual.item() < 1.0e-8


def test_nrtl_limits() -> None:
    """Check the x2 -> 1 and x2 -> 0 limits of the implemented ln(gamma_2)."""
    nrtl = NRTLLayer()
    T_ref = _scalar(298.15)
    tau_12 = _scalar(1.2)
    tau_21 = _scalar(0.7)
    alpha_12 = _scalar(0.3)
    _, _, G_12, G_21 = nrtl.compute_tau_G_from_params(
        _direct_nrtl_params(tau_12, tau_21, alpha_12),
        T_ref,
    )

    x2_pure = _scalar(0.9999)
    x1_pure = 1.0 - x2_pure
    ln_gamma_2_pure = nrtl.ln_gamma_2(
        x1_pure,
        x2_pure,
        tau_12,
        tau_21,
        G_12,
        G_21,
    )
    assert abs(ln_gamma_2_pure.item()) < 1.0e-6

    x2_dilute = _scalar(1.0e-6)
    x1_dilute = 1.0 - x2_dilute
    ln_gamma_2_dilute = nrtl.ln_gamma_2(
        x1_dilute,
        x2_dilute,
        tau_12,
        tau_21,
        G_12,
        G_21,
    )
    dilute_limit = tau_12 + tau_21 * torch.exp(-alpha_12 * tau_21)
    assert torch.allclose(
        ln_gamma_2_dilute,
        dilute_limit,
        atol=1.0e-5,
        rtol=0.0,
    )
