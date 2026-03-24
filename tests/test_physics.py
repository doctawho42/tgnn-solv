"""
tests/test_physics.py
=====================
Unit tests for hardcoded physics layers.

Run with:  pytest tests/test_physics.py -v
"""

import math
import pytest
import torch

import sys
sys.path.insert(0, "src")

from tgnn_solv.layers import IdealSolubilityLayer, NRTLLayer, HansenDistanceLayer
from tgnn_solv.solver import SLESolver
from tgnn_solv.config import TGNNSolvConfig


# ------------------------------------------------------------------ #
#  Fixtures                                                           #
# ------------------------------------------------------------------ #

@pytest.fixture
def ideal() -> IdealSolubilityLayer:
    return IdealSolubilityLayer()


@pytest.fixture
def nrtl() -> NRTLLayer:
    return NRTLLayer()


@pytest.fixture
def solver() -> SLESolver:
    return SLESolver(TGNNSolvConfig())


# ------------------------------------------------------------------ #
#  Ideal solubility                                                   #
# ------------------------------------------------------------------ #

class TestIdealSolubility:
    """Verify Φ(T) against known values."""

    def test_naphthalene(self, ideal: IdealSolubilityLayer) -> None:
        """Naphthalene: T_m=353K, ΔH=19060 J/mol, x_ideal ≈ 0.30."""
        T = torch.tensor([298.15])
        Phi = ideal(T, torch.tensor([353.0]),
                     torch.tensor([19060.0]), torch.tensor([0.0]))
        x_ideal = torch.exp(-Phi).item()
        assert 0.25 < x_ideal < 0.35, f"x_ideal={x_ideal}"

    def test_paracetamol(self, ideal: IdealSolubilityLayer) -> None:
        """Paracetamol: T_m=442K, ΔH=26400 J/mol, x_ideal ≈ 0.07."""
        T = torch.tensor([298.15])
        Phi = ideal(T, torch.tensor([442.0]),
                     torch.tensor([26400.0]), torch.tensor([80.0]))
        x_ideal = torch.exp(-Phi).item()
        assert 0.04 < x_ideal < 0.12, f"x_ideal={x_ideal}"

    def test_at_melting_point(self, ideal: IdealSolubilityLayer) -> None:
        """At T = T_m, Φ → 0 and x_ideal → 1."""
        T_m = torch.tensor([400.0])
        Phi = ideal(T_m, T_m, torch.tensor([20000.0]),
                     torch.tensor([50.0]))
        assert abs(Phi.item()) < 1e-6

    def test_monotonicity(self, ideal: IdealSolubilityLayer) -> None:
        """x_ideal must increase with T."""
        T_range = torch.linspace(270, 340, 20)
        Phi = ideal(T_range, torch.full_like(T_range, 400.0),
                     torch.full_like(T_range, 20000.0),
                     torch.full_like(T_range, 50.0))
        x = torch.exp(-Phi)
        diffs = x[1:] - x[:-1]
        assert (diffs >= -1e-8).all(), "x_ideal not monotonic in T"


# ------------------------------------------------------------------ #
#  NRTL                                                               #
# ------------------------------------------------------------------ #

class TestNRTL:
    """Verify NRTL activity coefficient model."""

    def test_gamma_inf_formula(self, nrtl: NRTLLayer) -> None:
        """ln γ∞ = τ₁₂ + τ₂₁ · G₂₁."""
        tau12 = torch.tensor([2.0])
        tau21 = torch.tensor([1.0])
        alpha = torch.tensor([0.3])
        G21 = torch.exp(-alpha * tau21)

        expected = (tau12 + tau21 * G21).item()
        result = nrtl.ln_gamma_inf(tau12, tau21, G21).item()
        assert abs(result - expected) < 1e-6

    def test_dilute_limit(self, nrtl: NRTLLayer) -> None:
        """At x₂ → 0, ln γ₂ should approach ln γ∞."""
        tau12 = torch.tensor([1.5])
        tau21 = torch.tensor([0.8])
        alpha = torch.tensor([0.3])
        G12 = torch.exp(-alpha * tau12)
        G21 = torch.exp(-alpha * tau21)

        x2 = torch.tensor([1e-8])
        x1 = 1.0 - x2

        lng2 = nrtl.ln_gamma_2(x1, x2, tau12, tau21, G12, G21).item()
        lng_inf = nrtl.ln_gamma_inf(tau12, tau21, G21).item()
        assert abs(lng2 - lng_inf) < 0.01, \
            f"ln γ₂={lng2:.4f}, ln γ∞={lng_inf:.4f}"

    def test_pure_solvent_gamma_one(self, nrtl: NRTLLayer) -> None:
        """At x₂ → 1 (pure solute), ln γ₂ → 0."""
        tau12 = torch.tensor([1.5])
        tau21 = torch.tensor([0.8])
        alpha = torch.tensor([0.3])
        G12 = torch.exp(-alpha * tau12)
        G21 = torch.exp(-alpha * tau21)

        x2 = torch.tensor([0.9999])
        x1 = 1.0 - x2

        lng2 = nrtl.ln_gamma_2(x1, x2, tau12, tau21, G12, G21).item()
        assert abs(lng2) < 0.01, f"ln γ₂={lng2:.4f} (expected ≈ 0)"

    def test_gibbs_duhem(self, nrtl: NRTLLayer) -> None:
        """Gibbs-Duhem consistency: x₁·d(ln γ₁)/dx₂ + x₂·d(ln γ₂)/dx₂ ≈ 0."""
        tau12 = torch.tensor([1.5])
        tau21 = torch.tensor([0.8])
        G12 = torch.exp(torch.tensor([-0.3 * 1.5]))
        G21 = torch.exp(torch.tensor([-0.3 * 0.8]))

        x2 = torch.linspace(0.05, 0.95, 20, requires_grad=True)
        x1 = 1.0 - x2

        lng1 = nrtl.ln_gamma_1(x1, x2, tau12, tau21, G12, G21)
        lng2 = nrtl.ln_gamma_2(x1, x2, tau12, tau21, G12, G21)

        d_lng1 = torch.autograd.grad(lng1.sum(), x2, create_graph=True)[0]
        d_lng2 = torch.autograd.grad(lng2.sum(), x2)[0]

        # Gibbs-Duhem: x1·(-d_lng1) + x2·(-d_lng2) ≈ 0
        # (derivatives w.r.t. x2, and x1 = 1 - x2)
        residual = x1 * (-d_lng1) + x2 * (-d_lng2)

        assert residual.abs().max().item() < 1e-4, \
            f"Max GD residual: {residual.abs().max().item():.2e}"

    def test_ref_invT_matches_abc_equivalent(self, nrtl: NRTLLayer) -> None:
        """The compact reference-temperature form should match its ABC equivalent."""
        T = torch.tensor([280.0, 315.0, 360.0])
        params = {
            "tau_ref_12": torch.tensor([0.6, 0.6, 0.6]),
            "tau_ref_21": torch.tensor([0.2, 0.2, 0.2]),
            "tau_inv_12": torch.tensor([0.8, 0.8, 0.8]),
            "tau_inv_21": torch.tensor([-0.3, -0.3, -0.3]),
            "alpha_12": torch.tensor([0.3, 0.3, 0.3]),
        }

        tau_ref = nrtl.compute_tau_G_from_params(params, T)
        a12, b12, c12, a21, b21, c21, alpha = nrtl.params_to_abc(params)
        tau_abc = nrtl.compute_tau_G(a12, b12, c12, a21, b21, c21, alpha, T)

        for ref_value, abc_value in zip(tau_ref, tau_abc):
            assert torch.allclose(ref_value, abc_value, atol=1e-6, rtol=0.0)


# ------------------------------------------------------------------ #
#  Hansen distance                                                    #
# ------------------------------------------------------------------ #

class TestHansen:
    """Verify Hansen distance calculation."""

    def test_self_distance_zero(self) -> None:
        layer = HansenDistanceLayer()
        h = torch.tensor([[18.0, 5.0, 10.0]])
        Ra = layer(h, h)
        assert abs(Ra.item()) < 1e-4

    def test_known_distance(self) -> None:
        layer = HansenDistanceLayer()
        # Water: (15.5, 16.0, 42.3)
        # Hexane: (14.9, 0.0, 0.0)
        h_water = torch.tensor([[15.5, 16.0, 42.3]])
        h_hexane = torch.tensor([[14.9, 0.0, 0.0]])
        Ra = layer(h_water, h_hexane)
        # Ra² = 4*(0.6)² + 16² + 42.3² = 1.44 + 256 + 1789.29 = 2046.73
        expected = math.sqrt(2046.73)
        assert abs(Ra.item() - expected) < 0.1


# ------------------------------------------------------------------ #
#  SLE Solver                                                         #
# ------------------------------------------------------------------ #

class TestSLESolver:
    """Integration tests for the full SLE solver."""

    def test_ideal_system(self, solver: SLESolver) -> None:
        """With γ₂ ≈ 1 (zero NRTL params), x₂ ≈ x_ideal."""
        solver.eval()
        T = torch.tensor([298.15])
        fus = {"T_m": torch.tensor([353.0]),
               "dH_fus": torch.tensor([19060.0]),
               "dCp_fus": torch.tensor([0.0])}
        nrtl_p = {"tau_a12": torch.tensor([0.0]),
                  "tau_b12": torch.tensor([0.0]),
                  "tau_c12": torch.tensor([0.0]),
                  "tau_a21": torch.tensor([0.0]),
                  "tau_b21": torch.tensor([0.0]),
                  "tau_c21": torch.tensor([0.0]),
                  "alpha_12": torch.tensor([0.3])}

        with torch.no_grad():
            out = solver(T, fus, nrtl_p, use_implicit=False)

        x_ideal = out["x_ideal"].item()
        x2 = out["x2"].item()
        assert abs(x2 - x_ideal) / x_ideal < 0.01, \
            f"x2={x2:.5f}, x_ideal={x_ideal:.5f}"

    def test_positive_deviation(self, solver: SLESolver) -> None:
        """Positive NRTL params → x₂ < x_ideal."""
        solver.eval()
        T = torch.tensor([298.15])
        R = 8.314
        T_ref = 298.15
        fus = {"T_m": torch.tensor([442.0]),
               "dH_fus": torch.tensor([26400.0]),
               "dCp_fus": torch.tensor([80.0])}
        nrtl_p = {"tau_a12": torch.tensor([5000.0 / (R * T_ref)]),
                  "tau_b12": torch.tensor([0.0]),
                  "tau_c12": torch.tensor([0.0]),
                  "tau_a21": torch.tensor([3000.0 / (R * T_ref)]),
                  "tau_b21": torch.tensor([0.0]),
                  "tau_c21": torch.tensor([0.0]),
                  "alpha_12": torch.tensor([0.3])}

        with torch.no_grad():
            out = solver(T, fus, nrtl_p, use_implicit=False)

        assert out["x2"].item() < out["x_ideal"].item()
        assert out["ln_gamma_2"].item() > 0  # positive deviation

    def test_gradient_flow(self, solver: SLESolver) -> None:
        """Gradients must flow through the solver to NRTL params."""
        solver.train()
        T = torch.tensor([298.15])
        R = 8.314
        T_ref = 298.15
        fus = {"T_m": torch.tensor([400.0]),
               "dH_fus": torch.tensor([20000.0]),
               "dCp_fus": torch.tensor([50.0])}

        a12 = torch.tensor([1000.0 / (R * T_ref)], requires_grad=True)
        nrtl_p = {"tau_a12": a12,
                  "tau_b12": torch.tensor([0.0]),
                  "tau_c12": torch.tensor([0.0]),
                  "tau_a21": torch.tensor([500.0 / (R * T_ref)]),
                  "tau_b21": torch.tensor([0.0]),
                  "tau_c21": torch.tensor([0.0]),
                  "alpha_12": torch.tensor([0.3])}

        out = solver(T, fus, nrtl_p, use_implicit=False)
        out["ln_x2"].backward()

        assert a12.grad is not None
        assert a12.grad.abs().item() > 0, "No gradient through solver"

    def test_ref_invT_solver_matches_abc_equivalent(self, solver: SLESolver) -> None:
        """Compact NRTL parameters should produce the same solver output as ABC."""
        solver.eval()
        T = torch.tensor([298.15])
        fus = {
            "T_m": torch.tensor([400.0]),
            "dH_fus": torch.tensor([20000.0]),
            "dCp_fus": torch.tensor([50.0]),
        }
        ref_params = {
            "tau_ref_12": torch.tensor([0.5]),
            "tau_ref_21": torch.tensor([0.2]),
            "tau_inv_12": torch.tensor([0.7]),
            "tau_inv_21": torch.tensor([-0.1]),
            "alpha_12": torch.tensor([0.3]),
        }
        abc_params = {
            "tau_a12": torch.tensor([-0.2]),
            "tau_b12": torch.tensor([0.7 * solver.cfg.T_ref]),
            "tau_c12": torch.tensor([0.0]),
            "tau_a21": torch.tensor([0.3]),
            "tau_b21": torch.tensor([-0.1 * solver.cfg.T_ref]),
            "tau_c21": torch.tensor([0.0]),
            "alpha_12": torch.tensor([0.3]),
        }

        with torch.no_grad():
            out_ref = solver(T, fus, ref_params, use_implicit=False)
            out_abc = solver(T, fus, abc_params, use_implicit=False)

        for key in ("x2", "ln_x2", "ln_gamma_2", "tau_12", "tau_21"):
            assert torch.allclose(out_ref[key], out_abc[key], atol=1e-6, rtol=0.0)

    def test_implicit_temperature_gradient_matches_explicit(self) -> None:
        """Implicit differentiation should retain the temperature gradient."""
        cfg = TGNNSolvConfig(
            n_iter_train=25,
            damping=0.7,
            solver_tol_train=1e-8,
            solver_adaptive_damping=True,
        )
        solver = SLESolver(cfg)
        solver.train()

        fus = {
            "T_m": torch.tensor([420.0]),
            "dH_fus": torch.tensor([22000.0]),
            "dCp_fus": torch.tensor([40.0]),
        }
        nrtl_p = {
            "tau_a12": torch.tensor([0.4]),
            "tau_b12": torch.tensor([120.0]),
            "tau_c12": torch.tensor([0.2]),
            "tau_a21": torch.tensor([0.2]),
            "tau_b21": torch.tensor([80.0]),
            "tau_c21": torch.tensor([0.1]),
            "alpha_12": torch.tensor([0.3]),
        }

        T_impl = torch.tensor([315.0], requires_grad=True)
        out_impl = solver(T_impl, fus, nrtl_p, use_implicit=True)
        grad_impl = torch.autograd.grad(out_impl["ln_x2"].sum(), T_impl)[0]

        T_exp = torch.tensor([315.0], requires_grad=True)
        out_exp = solver(T_exp, fus, nrtl_p, use_implicit=False)
        grad_exp = torch.autograd.grad(out_exp["ln_x2"].sum(), T_exp)[0]

        assert grad_impl is not None
        assert grad_exp is not None
        assert torch.isfinite(grad_impl).all()
        assert torch.isfinite(grad_exp).all()

        denom = grad_exp.abs().clamp(min=1e-6)
        rel_error = ((grad_impl - grad_exp).abs() / denom).item()
        assert rel_error < 0.25, (
            f"Implicit d/dT deviates too much from explicit: "
            f"{grad_impl.item():.6f} vs {grad_exp.item():.6f}"
        )


# ------------------------------------------------------------------ #
#  Run                                                                #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
