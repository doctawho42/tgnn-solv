"""Regression test: the OUTER SLE loop's two iteration counts, and its damping field.

The SLE fixed point of ``solver.SLESolver`` runs ``cfg.n_iter_train`` times in training
and ``cfg.n_iter_eval`` times at evaluation.  That is a SECOND pair of counts, distinct
from the segment-loop pair ``cosmo_sac_gamma_iter_train/eval`` that
``test_cosmo_sac_iter_convergence.py`` guards, and until 2026-08-11 nothing in the tests
or the manuscript mentioned it.

The Supporting Information now prints the pair (5 and 20), states that ``cfg.damping`` is
one field read by both loops, and quotes what the count is worth
(``scripts/analysis/run_outer_sle_iteration_audit.py``).  This test is the guard on those
sentences: if the schedule or the damping wiring changes, the manuscript's solver
paragraph is wrong and this fails first.

It is NOT a convergence test.  The outer loop at these counts is deliberately reported as
unconverged -- carrying the deposited rows to the fixed point moves the seed-mean MAE a
further +0.017 -- so asserting convergence here would assert something false.  What is
asserted instead is that the counts are the printed ones, that they genuinely change the
answer on a stiff pair (an instrument with teeth), and that a closure with no composition
dependence is count-independent (the null).
"""

from __future__ import annotations

import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import NRTLLayer
from tgnn_solv.solver import _iterate_fixed_point

# What the Supporting Information's "Solver, curriculum and loss" paragraph prints.
PRINTED_N_ITER_TRAIN = 5
PRINTED_N_ITER_EVAL = 20
PRINTED_DAMPING = 0.7
PRINTED_SEGMENT_TRAIN = 16
PRINTED_SEGMENT_EVAL = 30


def _solve(Phi, tau_12, tau_21, alpha, n_iter, tol):
    layer = NRTLLayer()
    G_12 = torch.exp(-alpha * tau_12)
    G_21 = torch.exp(-alpha * tau_21)
    x2, _ = _iterate_fixed_point(
        Phi, tau_12, tau_21, G_12, G_21,
        n_iter=n_iter, damping=PRINTED_DAMPING, min_damping=0.1,
        tol=tol, adaptive_damping=True, nrtl_layer=layer,
    )
    return torch.log(x2 + 1e-10)


def test_printed_outer_counts_match_the_config():
    cfg = TGNNSolvConfig()
    assert cfg.n_iter_train == PRINTED_N_ITER_TRAIN
    assert cfg.n_iter_eval == PRINTED_N_ITER_EVAL
    assert cfg.damping == PRINTED_DAMPING


def test_outer_and_segment_counts_are_different_knobs():
    """Four counts, two loops.  The manuscript prints both pairs and says so."""
    cfg = TGNNSolvConfig()
    assert cfg.cosmo_sac_gamma_iter_train == PRINTED_SEGMENT_TRAIN
    assert cfg.cosmo_sac_gamma_iter_eval == PRINTED_SEGMENT_EVAL
    assert (cfg.n_iter_train, cfg.n_iter_eval) != (
        cfg.cosmo_sac_gamma_iter_train, cfg.cosmo_sac_gamma_iter_eval
    )


def test_one_damping_field_serves_both_loops():
    """``CosmoSacLayer`` reads the SLE loop's damping for its segment loop.

    Two physically unrelated iterations share one hyperparameter, so neither can be
    damped without the other.  The manuscript states this; if the layer ever grows its
    own field, that sentence has to change with it.
    """
    from tgnn_solv.layers import CosmoSacLayer

    cfg = TGNNSolvConfig()
    cfg.damping = 0.41
    assert CosmoSacLayer(cfg).damping == 0.41


def test_the_two_counts_change_the_answer_on_a_stiff_pair():
    """The instrument has teeth: a strongly non-ideal pair moves between 5 and 20."""
    Phi = torch.tensor([6.0])
    tau_12, tau_21 = torch.tensor([9.0]), torch.tensor([1.5])
    alpha = torch.tensor([0.3])
    gap = (_solve(Phi, tau_12, tau_21, alpha, PRINTED_N_ITER_EVAL, 1e-7)
           - _solve(Phi, tau_12, tau_21, alpha, PRINTED_N_ITER_TRAIN, 1e-5)).abs()
    assert gap.item() > 0.05


def test_null_arm_a_composition_independent_closure_is_count_independent():
    """An ideal closure has no x2 dependence, so no count can move it."""
    Phi = torch.linspace(-2.0, 12.0, 64)
    z, alpha = torch.zeros_like(Phi), torch.zeros_like(Phi)
    gap = (_solve(Phi, z, z, alpha, PRINTED_N_ITER_EVAL, 1e-7)
           - _solve(Phi, z, z, alpha, PRINTED_N_ITER_TRAIN, 1e-5)).abs()
    assert gap.max().item() == 0.0
