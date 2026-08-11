"""Guards on the COSMO-SAC-2010 sigma grid, where a threshold sits exactly at zero.

The 2010 hydrogen-bond mask is a STRICT test, ``sigma_m * sigma_n < 0``, so the centre bin has to
be exactly zero or the mask misfires. It used to be built with ``torch.linspace``, which puts the
centre bin at -8.149e-10 (float32) / +8.674e-19 (float64) rather than on zero. Because
``sigma_25 * sigma_n`` and ``sigma_25 * sigma_(50-n)`` then carry opposite signs, exactly one of
every mirrored pair passed the test: 75 of 153 entries on the centre row were awarding a full
``c_hb * (sigma_m - sigma_n)^2`` to a segment that carries no screening charge and cannot hydrogen
bond. The NIST reference has the same strict comparison and is spared only because its
``-0.025 + delta*m`` arithmetic lands on an exact zero, so this was a divergence from the
reference rather than a shared convention.

It never fired on tabulated data -- UD profiles put a zero-charge segment in the NHB type, where
c_hb is zero -- which is exactly why it needed a test rather than a passing validation run. A
predicted profile carries no such guarantee.
"""
from __future__ import annotations

import torch

from tgnn_solv.layers import CosmoSac2010Layer

N_BINS = 51
N_TYPE = 3


def _sigma_from_sumsq(layer):
    """Recover |sigma_m| from the stored (sigma_m + sigma_n)^2 diagonal."""
    return torch.sqrt(torch.diagonal(layer.sumsq)[:N_BINS]) / 2.0


def _conjugation_index():
    """Charge conjugation: reverse sigma within each type block."""
    return torch.cat([torch.arange(t * N_BINS + N_BINS - 1, t * N_BINS - 1, -1)
                      for t in range(N_TYPE)])


def test_centre_bin_is_exactly_zero_in_both_precisions():
    for layer in (CosmoSac2010Layer().eval(), CosmoSac2010Layer().double().eval()):
        sigma = _sigma_from_sumsq(layer)
        centre = float(sigma[(N_BINS - 1) // 2])
        assert centre == 0.0, (
            f"centre bin is {centre!r}, not exactly zero, so the strict sigma_m*sigma_n < 0 "
            f"hydrogen-bond mask misfires on the centre row (dtype {layer.sumsq.dtype})"
        )


def test_a_zero_charge_segment_never_hydrogen_bonds():
    centre = (N_BINS - 1) // 2
    for layer in (CosmoSac2010Layer().eval(), CosmoSac2010Layer().double().eval()):
        for t in range(N_TYPE):
            row = layer.sign_neg[t * N_BINS + centre]
            fired = int(row.sum())
            assert fired == 0, (
                f"{fired} of {row.numel()} entries fire the hydrogen-bond term for a segment at "
                f"sigma = 0 in type block {t}; a segment with no screening charge cannot "
                f"hydrogen bond"
            )


def test_kernel_is_exactly_invariant_under_charge_conjugation():
    """delta_w(-s_m, -s_n) = delta_w(s_m, s_n): the misfit is even and the hb term's donor and
    acceptor factors swap. Exact, not approximate -- a non-zero residual here means the grid or
    the mask has drifted off centre again."""
    idx = _conjugation_index()
    for layer in (CosmoSac2010Layer().eval(), CosmoSac2010Layer().double().eval()):
        for temperature in (273.15, 298.15, 373.15):
            dw = layer._delta_w(torch.tensor([temperature], dtype=layer.sumsq.dtype))[0]
            residual = float((dw - dw[idx][:, idx]).abs().max())
            assert residual == 0.0, (
                f"kernel is not bit-identical under charge conjugation at {temperature} K: "
                f"max|dw - J dw J| = {residual:.4e} (dtype {layer.sumsq.dtype})"
            )


def test_grid_matches_the_nist_construction():
    """NIST builds the grid as sigma_min + delta*m in double (COSMO.hpp get_DELTAW). Reproduce it
    here and require agreement, so a future refactor cannot silently reintroduce linspace.

    Compared through the stored ``sumsq`` rather than through a square root: recovering sigma as
    sqrt(sumsq)/2 is not bit-exact and would make this test fail on correct code. The expectation
    is built at the layer's OWN storage dtype, because the layer computes the grid in float64 and
    then stores at the default dtype; comparing a float32 buffer against a float64 expectation
    fails by 3.5e-10 on correct code, which is a property of the storage and not of the grid."""
    smin, smax = -0.025, 0.025
    delta = (smax - smin) / (N_BINS - 1)
    layer = CosmoSac2010Layer().eval()
    nist = torch.tensor([smin + delta * m for m in range(N_BINS)],
                        dtype=torch.float64).to(layer.sumsq.dtype).repeat(N_TYPE)
    expected = (nist.view(-1, 1) + nist.view(1, -1)) ** 2
    assert torch.equal(layer.sumsq, expected), (
        f"the (sigma_m + sigma_n)^2 buffer differs from the NIST construction by "
        f"{float((layer.sumsq - expected).abs().max()):.3e}"
    )
