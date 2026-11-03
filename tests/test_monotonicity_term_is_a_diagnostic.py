"""The `mono` term is a working detector that cannot train, and nothing it detects occurs.

WHY THIS FILE EXISTS. The `mono` penalty carries weight 0.1 in Phase 3 of
``configs/cosmo_sac.yaml`` and 0.0 everywhere else, so it is the only loss component exclusive
to that phase. Across every arm of ``sigma_arms`` its raw value was 0.0000 in all 27 logged
occurrences, which reads as "monotonicity is satisfied" -- a reading that would make Phase 3 the
place where that property is earned. Measured 2026-11-03, both halves of that reading are wrong:

  * The term CANNOT TRAIN. ``_monotonicity_loss`` takes ``torch.autograd.grad(...,
    create_graph=False)``, so the gradient it differentiates is detached. Forcing the term to
    1.0 (its value on a real violation) and comparing weight 0.1 against weight 0.0 moves the
    reported total by exactly +0.1 and leaves all 343788 parameter gradients bit-identical.
    It inflates the number that is printed and contributes nothing to the number that is learnt.

  * Its zero is STRUCTURAL, not earned. An untrained, randomly initialised model already scores
    0.0000 on both the NRTL and the COSMO-SAC path, so the zeros in the arm logs are not evidence
    that training achieved anything. ``ln x2 = -Phi(T) - ln gamma2`` with Phi decreasing in T
    makes the solver path non-decreasing in T by construction.

The detector itself is correct -- it returns 1.0 on a model whose ln x2 falls with temperature --
so this is not broken arithmetic. It is a diagnostic wearing a penalty's weight.

WHAT ACTUALLY TRAINS TEMPERATURE MONOTONICITY is ``pair_temp_rank`` (live, and carrying gradient),
weighted 0.005 in Phase 2 and 0.01 in Phase 3. Turning Phase 3 off therefore removes a term that
could never act and halves nothing that matters. Tests for that term live in ``test_loss.py``.

These tests pin all three statements so that re-enabling Phase 3, or "fixing" the term, starts
from what was measured rather than from the reading the logs invite.
"""
from __future__ import annotations

import sys

import pytest
import torch
from torch_geometric.data import Batch, Data

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.loss import TGNNSolvLoss
from tgnn_solv.model import TGNNSolv

N_FEAT, E_FEAT, BATCH = 35, 8, 6


def _graphs(seed: int, n_atoms: int = 6) -> Batch:
    gen = torch.Generator().manual_seed(seed)
    datas = []
    for _ in range(BATCH):
        ei = torch.stack([torch.arange(n_atoms - 1), torch.arange(1, n_atoms)])
        ei = torch.cat([ei, ei.flip(0)], dim=1)
        datas.append(Data(x=torch.randn(n_atoms, N_FEAT, generator=gen), edge_index=ei,
                          edge_attr=torch.randn(ei.shape[1], E_FEAT, generator=gen)))
    return Batch.from_data_list(datas)


def _config(**kw) -> TGNNSolvConfig:
    return TGNNSolvConfig(hidden_dim=32, n_gnn_layers=2, n_cross_attn_layers=1, n_attn_heads=4,
                          pair_dim=64, solvent_moe_hidden=64, solvent_type_emb_dim=8,
                          n_iter_train=3, n_iter_eval=3, set2set_steps=2, **kw)


def _targets(t: torch.Tensor) -> dict:
    gen = torch.Generator().manual_seed(3)
    return {
        "T": t,
        "ln_x2": torch.randn(BATCH, generator=gen) - 3.0,
        "has_solubility": torch.ones(BATCH, dtype=torch.bool),
        "T_m": torch.full((BATCH,), 400.0),
        "dH_fus": torch.full((BATCH,), 20000.0),
        "has_T_m": torch.ones(BATCH, dtype=torch.bool),
        "has_dH_fus": torch.ones(BATCH, dtype=torch.bool),
        "pair_key": ["p"] * 3 + ["q"] * 3,
    }


class _FallsWithTemperature:
    """A model whose ln x2 moves with T at a fixed slope -- the stimulus the detector is for."""

    def __init__(self, cfg: TGNNSolvConfig, slope: float) -> None:
        self.cfg, self.slope = cfg, slope

    def __call__(self, *args, **kwargs) -> dict:
        return {"ln_x2": self.slope * args[2]}


@pytest.mark.parametrize("slope,expected", [(-1.0, 1.0), (1.0, 0.0), (0.0, 0.0)])
def test_the_detector_fires_on_a_violation_and_only_on_a_violation(slope, expected) -> None:
    """Without this, "the value is zero" could not be distinguished from "the code is broken"."""
    cfg = _config()
    loss_fn = TGNNSolvLoss(cfg)
    t = torch.full((BATCH,), 298.15)
    value = loss_fn._monotonicity_loss(
        _FallsWithTemperature(cfg, slope), _graphs(7), _graphs(8), t, targets=_targets(t)
    )
    assert value.item() == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("activity_model", ["nrtl", "cosmo_sac"])
def test_the_term_carries_no_gradient_and_an_untrained_model_already_scores_zero(
    activity_model,
) -> None:
    """Both halves of the misreading, on both activity paths.

    ``create_graph=False`` detaches the derivative the penalty is built from, so the returned
    tensor has no graph at all; and the value is already 0 before any training, so a zero in a
    log says nothing about what training did.
    """
    cfg = _config(activity_model=activity_model)
    torch.manual_seed(0)
    model = TGNNSolv(cfg=cfg)
    loss_fn = TGNNSolvLoss(cfg)
    t = torch.full((BATCH,), 298.15)

    value = loss_fn._monotonicity_loss(model, _graphs(7), _graphs(8), t, targets=_targets(t))

    # POLARITY. This pins a measurement, not a requirement. If it fails because someone made
    # the derivative differentiable (create_graph=True), that is a deliberate change to the
    # training path, not a regression: update this file, re-declare WANT_COMMIT in
    # results/sigma_arms/run_arm.sh, and treat everything trained afterwards as a new arm
    # family. Note also that a live term still contributes nothing while no violation occurs,
    # since relu'(x) = 0 wherever the constraint holds -- which it does on an untrained model.
    assert value.requires_grad is False, (
        "the term now carries a graph, so it CAN train -- see the polarity note above before "
        "treating this as a failure"
    )
    assert value.grad_fn is None
    assert value.item() == pytest.approx(0.0, abs=1e-9), (
        "an untrained model already satisfies the constraint, so the zeros in the arm logs are "
        "structural rather than earned"
    )


def test_the_mono_weight_changes_no_parameter_gradient_even_when_the_term_fires() -> None:
    """The statement on the surface that actually trains, not on the helper in isolation.

    The term is forced to 1.0, which is what it returns on a real violation, and the only
    difference between the two passes is its weight. The reported total must move by exactly the
    weight, and every parameter gradient must stay bit-identical.
    """
    weights = {"sol": 1.0, "T_m": 0.03, "dH": 0.03, "res": 0.02, "bridge": 0.02,
               "pair_temp_rank": 0.01, "vant_hoff_local": 0.001}
    t = torch.full((BATCH,), 298.15)
    targets = _targets(t)

    def run(mono_weight: float) -> tuple[float, torch.Tensor]:
        torch.manual_seed(0)
        cfg = _config(activity_model="cosmo_sac")
        model, loss_fn = TGNNSolv(cfg=cfg), TGNNSolvLoss(cfg)
        loss_fn._monotonicity_loss = lambda *a, **k: torch.tensor(1.0)
        solute, solvent = _graphs(7), _graphs(8)
        out = model(solute, solvent, t, targets=targets)
        total, _ = loss_fn(out, targets, weights={**weights, "mono": mono_weight},
                           compute_mono=True, T=t, model=model,
                           solute_data=solute, solvent_data=solvent)
        for p in model.parameters():
            p.grad = None
        total.backward()
        flat = torch.cat([p.grad.flatten() for p in model.parameters() if p.grad is not None])
        return float(total), flat

    total_on, grads_on = run(0.1)
    total_off, grads_off = run(0.0)

    assert total_on - total_off == pytest.approx(0.1, abs=1e-5), (
        "the term is expected to enter the REPORTED total; if it stopped doing so this test is "
        "no longer measuring what it claims"
    )
    assert torch.equal(grads_on, grads_off), (
        "the weight moved a parameter gradient, so the term can train and this file is stale"
    )
