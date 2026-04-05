"""Regression tests for TGNN-Solv descriptor augmentation."""

from __future__ import annotations

import sys

import numpy as np
import torch
from torch_geometric.data import Batch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig  # noqa: E402
from tgnn_solv.features import compute_molecular_descriptors, smiles_to_graph  # noqa: E402
from tgnn_solv.model import TGNNSolv  # noqa: E402


def _make_test_batch() -> tuple[Batch, Batch, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Construct a tiny valid batch with raw RDKit descriptors."""
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
    solvent_type = torch.tensor([0, 1], dtype=torch.long)
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
    return (
        solute_batch,
        solvent_batch,
        temperature,
        solvent_type,
        solute_descriptors,
        solvent_descriptors,
    )


def _make_config(descriptor_dim: int) -> TGNNSolvConfig:
    """Create a reduced TGNN config that exercises the descriptor branch."""
    return TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        set2set_steps=2,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        n_iter_train=2,
        n_iter_eval=2,
        use_descriptor_augmentation=True,
        descriptor_dim=descriptor_dim,
        descriptor_augmentation_hidden_dim=16,
        use_morgan_features=False,
    )


def test_tgnn_descriptor_augmentation_forward_backward_preserves_pair_dim() -> None:
    """Descriptor-augmented TGNN should keep g_pair at pair_dim after projection."""
    (
        solute_batch,
        solvent_batch,
        temperature,
        solvent_type,
        solute_descriptors,
        solvent_descriptors,
    ) = _make_test_batch()
    cfg = _make_config(int(solute_descriptors.shape[1]))
    model = TGNNSolv(cfg=cfg)
    model.set_descriptor_normalization(
        solute_descriptors.mean(dim=0),
        solute_descriptors.std(dim=0).clamp_min(1.0e-3),
    )

    output, intermediates = model(
        solute_batch,
        solvent_batch,
        temperature,
        solvent_type=solvent_type,
        solute_descriptors=solute_descriptors,
        solvent_descriptors=solvent_descriptors,
        return_intermediates=True,
    )

    output["ln_x2"].sum().backward()

    assert output["ln_x2"].shape == (2,)
    assert intermediates["g_pair"].shape == (2, cfg.pair_dim)
    assert model.descriptor_mean.shape == (cfg.descriptor_dim,)
    assert model.descriptor_std.shape == (cfg.descriptor_dim,)


def test_tgnn_descriptor_normalization_buffers_roundtrip_through_state_dict() -> None:
    """Descriptor normalization buffers should survive model state serialization."""
    (
        solute_batch,
        solvent_batch,
        temperature,
        solvent_type,
        solute_descriptors,
        solvent_descriptors,
    ) = _make_test_batch()
    cfg = _make_config(int(solute_descriptors.shape[1]))
    model = TGNNSolv(cfg=cfg)
    mean = solute_descriptors.mean(dim=0)
    std = solute_descriptors.std(dim=0).clamp_min(1.0e-3)
    model.set_descriptor_normalization(mean, std)

    reloaded = TGNNSolv(cfg=cfg)
    reloaded.load_state_dict(model.state_dict())
    output = reloaded(
        solute_batch,
        solvent_batch,
        temperature,
        solvent_type=solvent_type,
        solute_descriptors=solute_descriptors,
        solvent_descriptors=solvent_descriptors,
    )

    assert torch.allclose(reloaded.descriptor_mean, mean)
    assert torch.allclose(reloaded.descriptor_std, std)
    assert output["ln_x2"].shape == (2,)


def test_tgnn_descriptor_augmentation_falls_back_to_gnn_pair_when_descriptors_missing() -> None:
    """Missing descriptor tensors should fall back to the learned GNN pair path."""
    (
        solute_batch,
        solvent_batch,
        temperature,
        solvent_type,
        solute_descriptors,
        _,
    ) = _make_test_batch()
    cfg = _make_config(int(solute_descriptors.shape[1]))
    model = TGNNSolv(cfg=cfg)
    model.set_descriptor_normalization(
        solute_descriptors.mean(dim=0),
        solute_descriptors.std(dim=0).clamp_min(1.0e-3),
    )

    output, intermediates = model(
        solute_batch,
        solvent_batch,
        temperature,
        solvent_type=solvent_type,
        return_intermediates=True,
    )

    assert output["ln_x2"].shape == (2,)
    assert intermediates["g_pair"].shape == (2, cfg.pair_dim)
