"""Unit tests for the DirectGNN baseline."""

from __future__ import annotations

import sys

import numpy as np
import pytest
import torch
from torch_geometric.data import Batch

sys.path.insert(0, "src")

import tgnn_solv.baselines.direct_gnn as direct_gnn_module  # noqa: E402
from tgnn_solv.baselines.direct_gnn import (  # noqa: E402
    DESCRIPTOR_Z_CLIP,
    DirectGNN,
    DirectGNNTrainer,
)
from tgnn_solv.config import TGNNSolvConfig  # noqa: E402
from tgnn_solv.features import compute_molecular_descriptors, smiles_to_graph  # noqa: E402


def _make_test_batch() -> tuple[Batch, Batch, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Construct a tiny valid batch for DirectGNN tests."""
    solute_graphs = [
        smiles_to_graph("CCO"),
        smiles_to_graph("CCN"),
    ]
    solvent_graphs = [
        smiles_to_graph("O"),
        smiles_to_graph("CCO"),
    ]
    assert all(graph is not None for graph in solute_graphs)
    assert all(graph is not None for graph in solvent_graphs)

    solute_batch = Batch.from_data_list([graph for graph in solute_graphs if graph is not None])
    solvent_batch = Batch.from_data_list([graph for graph in solvent_graphs if graph is not None])
    temperature = torch.tensor([298.15, 310.0], dtype=torch.float32)

    solute_descriptors = torch.tensor(
        np.stack(
            [
                compute_molecular_descriptors("CCO"),
                compute_molecular_descriptors("CCN"),
            ],
            axis=0,
        ),
        dtype=torch.float32,
    )
    solvent_descriptors = torch.tensor(
        np.stack(
            [
                compute_molecular_descriptors("O"),
                compute_molecular_descriptors("CCO"),
            ],
            axis=0,
        ),
        dtype=torch.float32,
    )
    return solute_batch, solvent_batch, temperature, solute_descriptors, solvent_descriptors


def test_direct_gnn_descriptor_augmentation_forward_backward() -> None:
    """Descriptor-augmented DirectGNN should support forward/backward with saved stats."""
    solute_batch, solvent_batch, temperature, solute_descriptors, solvent_descriptors = _make_test_batch()
    descriptor_dim = int(solute_descriptors.shape[1])
    cfg = TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        set2set_steps=2,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        use_descriptor_augmentation=True,
        descriptor_dim=descriptor_dim,
        descriptor_hidden_dim=16,
        use_morgan_features=False,
    )
    model = DirectGNN(cfg=cfg)
    model.set_descriptor_normalization(
        solute_descriptors.mean(dim=0),
        solute_descriptors.std(dim=0).clamp_min(1.0e-3),
    )

    output = model(
        solute_batch,
        solvent_batch,
        temperature,
        solute_descriptors=solute_descriptors,
        solvent_descriptors=solvent_descriptors,
    )

    loss = output["ln_x2"].sum()
    loss.backward()

    assert output["ln_x2"].shape == (2,)
    assert output["x2"].shape == (2,)
    assert model.descriptor_mean.shape == (descriptor_dim,)
    assert model.descriptor_std.shape == (descriptor_dim,)


def test_direct_gnn_descriptor_buffers_roundtrip_through_state_dict() -> None:
    """Descriptor normalization buffers should survive state-dict save/load."""
    solute_batch, solvent_batch, temperature, solute_descriptors, solvent_descriptors = _make_test_batch()
    descriptor_dim = int(solute_descriptors.shape[1])
    cfg = TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        set2set_steps=2,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        use_descriptor_augmentation=True,
        descriptor_dim=descriptor_dim,
        descriptor_hidden_dim=16,
        use_morgan_features=False,
    )
    model = DirectGNN(cfg=cfg)
    mean = solute_descriptors.mean(dim=0)
    std = solute_descriptors.std(dim=0).clamp_min(1.0e-3)
    model.set_descriptor_normalization(mean, std)

    reloaded = DirectGNN(cfg=cfg)
    reloaded.load_state_dict(model.state_dict())
    output = reloaded(
        solute_batch,
        solvent_batch,
        temperature,
        solute_descriptors=solute_descriptors,
        solvent_descriptors=solvent_descriptors,
    )

    assert torch.allclose(reloaded.descriptor_mean, mean)
    assert torch.allclose(reloaded.descriptor_std, std)
    assert output["ln_x2"].shape == (2,)


def test_direct_gnn_descriptor_encoding_clamps_extreme_z_scores() -> None:
    """Descriptor branch should clip pathological z-scores before projection."""
    cfg = TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        set2set_steps=2,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        use_descriptor_augmentation=True,
        descriptor_dim=3,
        descriptor_hidden_dim=3,
        use_morgan_features=False,
    )
    model = DirectGNN(cfg=cfg)
    model.descriptor_adapter = torch.nn.Identity()
    model.set_descriptor_normalization(
        torch.zeros(3, dtype=torch.float32),
        torch.ones(3, dtype=torch.float32),
    )

    encoded = model._encode_descriptors(
        torch.tensor([[1.0e9, -1.0e9, 3.0]], dtype=torch.float32)
    )

    expected = torch.tensor(
        [[DESCRIPTOR_Z_CLIP, -DESCRIPTOR_Z_CLIP, 3.0]],
        dtype=torch.float32,
    )
    assert torch.allclose(encoded, expected)


def test_direct_gnn_trainer_uses_configured_grad_clip_and_weight_decay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DirectGNNTrainer should honor configured grad clipping and weight decay."""
    solute_batch, solvent_batch, temperature, _, _ = _make_test_batch()
    cfg = TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        set2set_steps=2,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        use_morgan_features=False,
        grad_clip=2.5,
        direct_weight_decay=2.5e-4,
    )
    model = DirectGNN(cfg=cfg)
    trainer = DirectGNNTrainer(model, device=torch.device("cpu"))
    batch = (
        solute_batch,
        solvent_batch,
        {
            "T": temperature,
            "ln_x2": torch.tensor([-1.0, -0.5], dtype=torch.float32),
            "has_solubility": torch.tensor([True, True]),
        },
    )
    captured: list[float] = []
    optimizer_calls: list[dict[str, float]] = []

    def fake_clip(parameters, max_norm, *args, **kwargs):
        captured.append(float(max_norm))
        return torch.tensor(0.0)

    class FakeOptimizer:
        def __init__(self, params, lr, weight_decay):
            list(params)
            optimizer_calls.append(
                {
                    "lr": float(lr),
                    "weight_decay": float(weight_decay),
                }
            )

        def zero_grad(self) -> None:
            return None

        def step(self) -> None:
            return None

        def state_dict(self) -> dict[str, object]:
            return {}

        def load_state_dict(self, state_dict) -> None:
            return None

    class FakeScheduler:
        def __init__(self, optimizer, T_max):
            self.optimizer = optimizer
            self.T_max = T_max

        def step(self) -> None:
            return None

        def state_dict(self) -> dict[str, object]:
            return {}

        def load_state_dict(self, state_dict) -> None:
            return None

    monkeypatch.setattr(direct_gnn_module.nn.utils, "clip_grad_norm_", fake_clip)
    monkeypatch.setattr(direct_gnn_module.torch.optim, "AdamW", FakeOptimizer)
    monkeypatch.setattr(
        direct_gnn_module.torch.optim.lr_scheduler,
        "CosineAnnealingLR",
        FakeScheduler,
    )
    monkeypatch.setattr(
        trainer,
        "_evaluate_loader",
        lambda loader: {
            "n": 2,
            "mae": 1.0,
            "rmse": 1.0,
            "r2": 0.0,
            "bias": 0.0,
        },
    )

    trainer.train([batch], [batch], n_epochs=1, lr=1.0e-4, patience=1)

    assert captured == [2.5]
    assert optimizer_calls == [{"lr": 1.0e-4, "weight_decay": 2.5e-4}]
