"""Regression test: segment fixed-point iteration convergence (train vs eval).

The COSMO-SAC segment fixed point uses ``cosmo_sac_gamma_iter_train`` during
training and ``cosmo_sac_gamma_iter_eval`` during evaluation (config.py:184-185).
Defaults: train=16, eval=30.  This test asserts that the truncation gap
(residual ln Γ₂ at n_iter_train vs n_iter_eval) stays below TOL=0.05 ln-units
across the experimental temperature range.

If this test ever starts failing, bump ``cosmo_sac_gamma_iter_train`` in
config.py:184 to the smallest passing value (try 20, 24, 30) and update the
comment there.  n=8 was the original default and failed with gap=5.86 ln-units
at T=273.15K; n=16 converges to within 6e-5 of n=30.
"""

from __future__ import annotations

import sys

import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer

# ---- tolerance ----
TOL = 0.05  # ln-units; documents that n_iter_train is converged for training


# ---- profile helpers (mirror test_cosmo_sac.py) ----

def _gauss(
    grid: torch.Tensor, center: float, width: float, area: float
) -> torch.Tensor:
    """Gaussian sigma-profile, area-normalised, shape (1, n_bins)."""
    p = torch.exp(-0.5 * ((grid - center) / width) ** 2)
    return (p / p.sum() * area).unsqueeze(0)


def _profiles(layer: CosmoSacLayer):
    """Return (nonpolar, polar) area-weighted profiles (1, n_bins) each."""
    grid = layer.sigma_grid
    nonpolar = _gauss(grid, 0.0, 0.004, 300.0)
    polar = (
        _gauss(grid, 0.0, 0.004, 150.0)
        + _gauss(grid, 0.015, 0.003, 75.0)
        + _gauss(grid, -0.015, 0.003, 75.0)
    )
    return nonpolar, polar


# ---- test ----

def test_segment_fixed_point_converged_at_train_iters() -> None:
    """Max |ln Γ₂(n_iter_train) − ln Γ₂(n_iter_eval)| < TOL=0.05 across T range.

    ``_residual_ln_gamma2`` is called directly with explicit n_iter so the
    comparison is independent of the layer's train/eval mode flag.
    The combinatorial term is the same at both iteration counts and is excluded.
    The test drives from the layer's own n_iter_train / n_iter_eval attributes
    (read from TGNNSolvConfig defaults) so it stays valid if the config is tuned.
    """
    cfg = TGNNSolvConfig()
    layer = CosmoSacLayer(cfg)

    n_train = layer.n_iter_train  # == cfg.cosmo_sac_gamma_iter_train
    n_eval  = layer.n_iter_eval   # == cfg.cosmo_sac_gamma_iter_eval

    nonpolar, polar = _profiles(layer)
    A_nonpolar = torch.tensor([300.0])  # Å²
    A_polar    = torch.tensor([300.0])  # Å²
    x2 = torch.tensor([1e-4])           # near infinite dilution (hardest case)

    TEMPERATURES = (273.15, 298.15, 373.15)
    gaps: list[float] = []

    for T_val in TEMPERATURES:
        T = torch.tensor([float(T_val)])

        # polar solute in nonpolar solvent (largest residual term)
        g_train_pn = layer._residual_ln_gamma2(
            polar, nonpolar, A_polar, A_nonpolar, x2, T, n_iter=n_train
        )
        g_eval_pn  = layer._residual_ln_gamma2(
            polar, nonpolar, A_polar, A_nonpolar, x2, T, n_iter=n_eval
        )

        # nonpolar solute in polar solvent (complementary case)
        g_train_np = layer._residual_ln_gamma2(
            nonpolar, polar, A_nonpolar, A_polar, x2, T, n_iter=n_train
        )
        g_eval_np  = layer._residual_ln_gamma2(
            nonpolar, polar, A_nonpolar, A_polar, x2, T, n_iter=n_eval
        )

        gap = max(
            float((g_train_pn - g_eval_pn).abs().max()),
            float((g_train_np - g_eval_np).abs().max()),
        )
        gaps.append(gap)

    max_gap = max(gaps)
    assert max_gap < TOL, (
        f"Segment fixed-point gap too large: {max_gap:.4f} ln-units "
        f"(n_train={n_train}, n_eval={n_eval}, TOL={TOL}). Per-T gaps: "
        + ", ".join(f"T={T}K→{g:.4f}" for T, g in zip(TEMPERATURES, gaps))
        + ". Bump cosmo_sac_gamma_iter_train in config.py:184."
    )
