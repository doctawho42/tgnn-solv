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
def ideal():
    return IdealSolubilityLayer()


@pytest.fixture
def nrtl():
    return NRTLLayer()


@pytest.fixture
def solver():
    return SLESolver(TGNNSolvConfig())


# ------------------------------------------------------------------ #
#  Ideal solubility                                                   #
# ------------------------------------------------------------------ #

class TestIdealSolubility:
    """Verify Φ(T) against known values."""

    def test_naphthalene(self, ideal):
        """Naphthalene: T_m=353K, ΔH=19060 J/mol, x_ideal ≈ 0.30."""
        T = torch.tensor([298.15])
        Phi = ideal(T, torch.tensor([353.0]),
                     torch.tensor([19060.0]), torch.tensor([0.0]))
        x_ideal = torch.exp(-Phi).item()
        assert 0.25 < x_ideal < 0.35, f"x_ideal={x_ideal}"

    def test_paracetamol(self, ideal):
        """Paracetamol: T_m=442K, ΔH=26400 J/mol, x_ideal ≈ 0.07."""
        T = torch.tensor([298.15])
        Phi = ideal(T, torch.tensor([442.0]),
                     torch.tensor([26400.0]), torch.tensor([80.0]))
        x_ideal = torch.exp(-Phi).item()
        assert 0.04 < x_ideal < 0.12, f"x_ideal={x_ideal}"

    def test_at_melting_point(self, ideal):
        """At T = T_m, Φ → 0 and x_ideal → 1."""
        T_m = torch.tensor([400.0])
        Phi = ideal(T_m, T_m, torch.tensor([20000.0]),
                     torch.tensor([50.0]))
        assert abs(Phi.item()) < 1e-6

    def test_monotonicity(self, ideal):
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

    def test_gamma_inf_formula(self, nrtl):
        """ln γ∞ = τ₁₂ + τ₂₁ · G₂₁."""
        tau12 = torch.tensor([2.0])
        tau21 = torch.tensor([1.0])
        alpha = torch.tensor([0.3])
        G21 = torch.exp(-alpha * tau21)

        expected = (tau12 + tau21 * G21).item()
        result = nrtl.ln_gamma_inf(tau12, tau21, G21).item()
        assert abs(result - expected) < 1e-6

    def test_dilute_limit(self, nrtl):
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

    def test_pure_solvent_gamma_one(self, nrtl):
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

    def test_gibbs_duhem(self, nrtl):
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


# ------------------------------------------------------------------ #
#  Hansen distance                                                    #
# ------------------------------------------------------------------ #

class TestHansen:
    """Verify Hansen distance calculation."""

    def test_self_distance_zero(self):
        layer = HansenDistanceLayer()
        h = torch.tensor([[18.0, 5.0, 10.0]])
        Ra = layer(h, h)
        assert abs(Ra.item()) < 1e-4

    def test_known_distance(self):
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

    def test_ideal_system(self, solver):
        """With γ₂ ≈ 1 (zero NRTL params), x₂ ≈ x_ideal."""
        solver.eval()
        T = torch.tensor([298.15])
        fus = {"T_m": torch.tensor([353.0]),
               "dH_fus": torch.tensor([19060.0]),
               "dCp_fus": torch.tensor([0.0])}
        nrtl_p = {"dg_12": torch.tensor([0.0]),
                  "dg_21": torch.tensor([0.0]),
                  "alpha_12": torch.tensor([0.3]),
                  "a_T12": torch.tensor([0.0]),
                  "a_T21": torch.tensor([0.0])}

        with torch.no_grad():
            out = solver(T, fus, nrtl_p, use_implicit=False)

        x_ideal = out["x_ideal"].item()
        x2 = out["x2"].item()
        assert abs(x2 - x_ideal) / x_ideal < 0.01, \
            f"x2={x2:.5f}, x_ideal={x_ideal:.5f}"

    def test_positive_deviation(self, solver):
        """Positive NRTL params → x₂ < x_ideal."""
        solver.eval()
        T = torch.tensor([298.15])
        fus = {"T_m": torch.tensor([442.0]),
               "dH_fus": torch.tensor([26400.0]),
               "dCp_fus": torch.tensor([80.0])}
        nrtl_p = {"dg_12": torch.tensor([5000.0]),
                  "dg_21": torch.tensor([3000.0]),
                  "alpha_12": torch.tensor([0.3]),
                  "a_T12": torch.tensor([0.0]),
                  "a_T21": torch.tensor([0.0])}

        with torch.no_grad():
            out = solver(T, fus, nrtl_p, use_implicit=False)

        assert out["x2"].item() < out["x_ideal"].item()
        assert out["ln_gamma_2"].item() > 0  # positive deviation

    def test_gradient_flow(self, solver):
        """Gradients must flow through the solver to NRTL params."""
        solver.train()
        T = torch.tensor([298.15])
        fus = {"T_m": torch.tensor([400.0]),
               "dH_fus": torch.tensor([20000.0]),
               "dCp_fus": torch.tensor([50.0])}

        dg12 = torch.tensor([1000.0], requires_grad=True)
        nrtl_p = {"dg_12": dg12,
                  "dg_21": torch.tensor([500.0]),
                  "alpha_12": torch.tensor([0.3]),
                  "a_T12": torch.tensor([0.0]),
                  "a_T21": torch.tensor([0.0])}

        out = solver(T, fus, nrtl_p, use_implicit=False)
        out["ln_x2"].backward()

        assert dg12.grad is not None
        assert dg12.grad.abs().item() > 0, "No gradient through solver"


# ------------------------------------------------------------------ #
#  Run                                                                #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    pytest.main([__file__, "-v"])