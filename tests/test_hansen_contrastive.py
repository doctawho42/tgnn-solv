from __future__ import annotations

import math

import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.hansen_contrastive import (
    ChannelHansenContrastiveLoss,
    HansenContrastiveLoss,
    PairHansenContrastiveLoss,
    pseudo_hansen_from_smiles,
)
from tgnn_solv.loss import TGNNSolvLoss


def _unit_scale(loss: HansenContrastiveLoss) -> None:
    """Set softplus(alpha) to 1 for deterministic perfect-alignment tests."""
    with torch.no_grad():
        loss.alpha.fill_(math.log(math.e - 1.0))
        loss.beta.zero_()


def test_hansen_contrastive_basic() -> None:
    torch.manual_seed(0)
    embeddings = torch.randn(10, 16)
    hansen = torch.rand(10, 3) * 20.0
    mask = torch.ones(10, dtype=torch.bool)

    loss_fn = HansenContrastiveLoss()
    loss = loss_fn(embeddings, hansen, mask)

    assert torch.isfinite(loss)
    assert loss.item() > 0.0


def test_hansen_contrastive_perfect() -> None:
    hansen = torch.tensor(
        [
            [15.0, 4.0, 8.0],
            [17.0, 7.0, 9.0],
            [19.0, 6.0, 12.0],
            [16.0, 5.0, 10.0],
        ],
        dtype=torch.float,
    )
    embeddings = torch.stack(
        [2.0 * hansen[:, 0], hansen[:, 1], hansen[:, 2]],
        dim=-1,
    )
    mask = torch.ones(hansen.size(0), dtype=torch.bool)

    loss_fn = HansenContrastiveLoss()
    _unit_scale(loss_fn)
    loss = loss_fn(embeddings, hansen, mask)

    assert loss.item() < 1.0e-6


def test_hansen_contrastive_gradient() -> None:
    torch.manual_seed(1)
    embeddings = torch.randn(8, 12, requires_grad=True)
    hansen = torch.rand(8, 3) * 15.0
    mask = torch.ones(8, dtype=torch.bool)

    loss = HansenContrastiveLoss()(embeddings, hansen, mask)
    loss.backward()

    assert embeddings.grad is not None
    assert torch.isfinite(embeddings.grad).all()


def test_channel_contrastive() -> None:
    torch.manual_seed(2)
    g_disp = torch.randn(6, 8)
    g_polar = torch.randn(6, 8)
    hansen = torch.rand(6, 3) * 20.0
    mask = torch.ones(6, dtype=torch.bool)

    loss_fn = ChannelHansenContrastiveLoss()
    loss = loss_fn(g_disp, g_polar, hansen, mask)
    skipped = loss_fn(None, None, hansen, mask)

    assert torch.isfinite(loss)
    assert loss.item() >= 0.0
    assert torch.isfinite(skipped)
    assert skipped.item() == 0.0


def test_pseudo_hansen() -> None:
    ethanol = pseudo_hansen_from_smiles("CCO")
    benzene = pseudo_hansen_from_smiles("c1ccccc1")

    assert ethanol is not None
    assert benzene is not None
    assert all(math.isfinite(value) for value in ethanol)
    assert all(0.0 <= value <= 45.0 for value in ethanol)

    ethanol_true = torch.tensor([15.8, 8.8, 19.4])
    ethanol_pseudo = torch.tensor(ethanol)
    assert torch.linalg.vector_norm(ethanol_pseudo - ethanol_true).item() < 2.0


def test_pair_contrastive() -> None:
    torch.manual_seed(3)
    embeddings = torch.randn(5, 10)
    ra = torch.tensor([2.0, 3.0, 8.0, 12.0, 13.0])
    mask = torch.tensor([True, True, False, True, True])

    loss_fn = PairHansenContrastiveLoss()
    loss = loss_fn(embeddings, ra, mask)
    one_known = loss_fn(embeddings, ra, torch.tensor([True, False, False, False, False]))

    assert torch.isfinite(loss)
    assert loss.item() >= 0.0
    assert torch.isfinite(one_known)
    assert one_known.item() == 0.0


def test_contrastive_does_not_dominate() -> None:
    torch.manual_seed(4)
    cfg = TGNNSolvConfig(use_hansen_contrastive=True)
    loss_fn = TGNNSolvLoss(cfg)
    output = {
        "ln_x2": torch.zeros(6, requires_grad=True),
        "representations": {
            "g_sol_pre": torch.randn(6, 8, requires_grad=True),
            "g_pair": torch.randn(6, 8, requires_grad=True),
        },
    }
    targets = {
        "ln_x2": torch.ones(6),
        "has_solubility": torch.ones(6, dtype=torch.bool),
        "hansen_sol_effective": torch.rand(6, 3) * 5.0,
        "hansen_contrastive_mask": torch.ones(6, dtype=torch.bool),
        "hansen_sol_contrastive_weight": torch.ones(6),
        "pair_Ra": torch.linspace(1.0, 6.0, 6),
        "pair_hansen_mask": torch.ones(6, dtype=torch.bool),
        "pair_hansen_weight": torch.ones(6),
    }
    weights = {
        "sol": 1.0,
        "hansen_contrastive_mol": 0.005,
        "hansen_contrastive_pair": 0.005,
    }

    total, parts = loss_fn(output, targets, weights=weights)
    sol_fraction = weights["sol"] * parts["sol"] / float(total.detach())

    assert torch.isfinite(total)
    assert sol_fraction > 0.5
