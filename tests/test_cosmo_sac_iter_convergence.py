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

import torch

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
    eval_self_gaps: list[float] = []

    for T_val in TEMPERATURES:
        T = torch.tensor([float(T_val)])

        # polar solute in nonpolar solvent (largest residual term)
        g_train_pn = layer._residual_ln_gamma2(
            polar, nonpolar, A_polar, A_nonpolar, x2, T, n_iter=n_train
        )
        g_eval_pn  = layer._residual_ln_gamma2(
            polar, nonpolar, A_polar, A_nonpolar, x2, T, n_iter=n_eval
        )
        g_more_pn  = layer._residual_ln_gamma2(
            polar, nonpolar, A_polar, A_nonpolar, x2, T, n_iter=n_eval + 20
        )

        # nonpolar solute in polar solvent (complementary case)
        g_train_np = layer._residual_ln_gamma2(
            nonpolar, polar, A_nonpolar, A_polar, x2, T, n_iter=n_train
        )
        g_eval_np  = layer._residual_ln_gamma2(
            nonpolar, polar, A_nonpolar, A_polar, x2, T, n_iter=n_eval
        )
        g_more_np  = layer._residual_ln_gamma2(
            nonpolar, polar, A_nonpolar, A_polar, x2, T, n_iter=n_eval + 20
        )

        gap = max(
            float((g_train_pn - g_eval_pn).abs().max()),
            float((g_train_np - g_eval_np).abs().max()),
        )
        gaps.append(gap)

        # eval must itself be converged: n_eval vs n_eval+20
        eval_self_gaps.append(max(
            float((g_eval_pn - g_more_pn).abs().max()),
            float((g_eval_np - g_more_np).abs().max()),
        ))

    max_gap = max(gaps)
    assert max_gap < TOL, (
        f"Segment fixed-point gap too large: {max_gap:.4f} ln-units "
        f"(n_train={n_train}, n_eval={n_eval}, TOL={TOL}). Per-T gaps: "
        + ", ".join(f"T={T}K→{g:.4f}" for T, g in zip(TEMPERATURES, gaps))
        + ". Bump cosmo_sac_gamma_iter_train in config.py:184."
    )

    max_eval_self = max(eval_self_gaps)
    assert max_eval_self < TOL, (
        f"Eval operator not self-converged: {max_eval_self:.4f} ln-units between "
        f"n_iter={n_eval} and n_iter={n_eval + 20} (TOL={TOL}). Per-T gaps: "
        + ", ".join(f"T={T}K→{g:.4f}" for T, g in zip(TEMPERATURES, eval_self_gaps))
        + ". Bump cosmo_sac_gamma_iter_eval in config.py:185."
    )


def test_segment_converged_for_stiff_water_solvent() -> None:
    """Sharp bimodal (water-like) solvent is the stiffest fixed point.

    Smooth Gaussians under-represent the hardest convergence regime; a real
    water σ-profile has two narrow HB donor/acceptor peaks that make the
    segment fixed point stiffest at low T.  This pins that n_iter_train matches
    n_iter_eval *and* that eval itself is converged for such an input, at the
    coldest experimental temperature (273.15 K).
    """
    cfg = TGNNSolvConfig()
    layer = CosmoSacLayer(cfg)
    g = layer.sigma_grid

    # Bimodal water-like solvent: sharp HB donor (-) / acceptor (+) peaks,
    # total area ~43 Å² (close to a real water cavity).  _gauss returns
    # shape (1, n_bins); summing two keeps that shape.
    water = _gauss(g, -0.0155, 0.0020, 21.5) + _gauss(g, 0.0155, 0.0020, 21.5)
    nonpolar = _gauss(g, 0.0, 0.004, 150.0)
    A_w = water.sum(-1)        # ~43 Å²
    A_np = nonpolar.sum(-1)    # ~150 Å²
    x2 = torch.tensor([1e-4])  # near infinite dilution
    T = torch.tensor([273.15])

    g_train = layer._residual_ln_gamma2(
        nonpolar, water, A_np, A_w, x2, T, n_iter=layer.n_iter_train
    )
    g_eval = layer._residual_ln_gamma2(
        nonpolar, water, A_np, A_w, x2, T, n_iter=layer.n_iter_eval
    )
    g_more = layer._residual_ln_gamma2(
        nonpolar, water, A_np, A_w, x2, T, n_iter=layer.n_iter_eval + 20
    )

    train_eval_gap = float((g_train - g_eval).abs().max())
    eval_self_gap = float((g_eval - g_more).abs().max())

    # train(n_train) vs eval(n_eval): operators equivalent for stiff in-dist input
    assert train_eval_gap < TOL, (
        f"Stiff-water train/eval gap {train_eval_gap:.4f} >= TOL={TOL} "
        f"(n_train={layer.n_iter_train}, n_eval={layer.n_iter_eval})."
    )
    # eval must itself be converged: n_eval vs n_eval+20
    assert eval_self_gap < TOL, (
        f"Stiff-water eval not self-converged: {eval_self_gap:.4f} >= TOL={TOL} "
        f"(n_iter={layer.n_iter_eval} vs {layer.n_iter_eval + 20})."
    )
