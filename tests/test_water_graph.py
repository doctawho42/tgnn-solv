"""Regression tests for single-atom water graphs."""

from __future__ import annotations

import sys

import torch
from torch_geometric.data import Batch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig  # noqa: E402
from tgnn_solv.data.solvent_types import solvent_type_id_from_smiles  # noqa: E402
from tgnn_solv.features import (  # noqa: E402
    EDGE_FEAT_DIM,
    NODE_FEAT_DIM,
    get_graph_feature_spec,
    smiles_to_graph,
)
from tgnn_solv.layers import GNNEncoder, PhysicsAwareReadout  # noqa: E402
from tgnn_solv.model import TGNNSolv  # noqa: E402


def _small_tgnn_config() -> TGNNSolvConfig:
    """Return a compact config suitable for forward smoke tests."""
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
    )


def test_smiles_to_graph_builds_nonempty_water_graph() -> None:
    """Water should remain a valid one-node graph with a self-loop edge."""
    graph = smiles_to_graph("O")

    assert graph is not None
    assert graph.num_atoms == 1
    assert graph.x.shape[0] >= 1
    assert graph.edge_index.shape[1] >= 1
    assert graph.edge_attr.shape[0] == graph.edge_index.shape[1]
    assert torch.equal(graph.edge_index, torch.tensor([[0], [0]], dtype=torch.long))


def test_explicit_h_small_molecule_mode_builds_oh_edges_for_water() -> None:
    """The opt-in small-molecule mode should expose O-H bonds for water."""
    graph = smiles_to_graph(
        "O",
        use_gasteiger_charges=True,
        use_phys_edge_features=True,
        explicit_h_small_molecules=True,
        explicit_h_max_heavy_atoms=3,
    )
    spec = get_graph_feature_spec(
        use_gasteiger_charges=True,
        use_phys_edge_features=True,
    )

    assert graph is not None
    assert graph.num_atoms == 3
    assert graph.num_heavy_atoms == 1
    assert bool(graph.explicit_h_small_molecule) is True
    assert graph.x.shape == (3, spec.node_dim)
    assert graph.edge_index.shape == (2, 4)
    assert graph.edge_attr.shape == (4, spec.edge_dim)
    assert graph.edge_attr[:, spec.phys_edge_start_idx].gt(0).all()
    assert torch.isfinite(graph.x).all()
    assert torch.isfinite(graph.edge_attr).all()


def test_gnn_encoder_and_readout_handle_water_graph() -> None:
    """Single-atom water graphs should propagate through the encoder and readout."""
    graph = smiles_to_graph("O")
    assert graph is not None

    batch = Batch.from_data_list([graph])
    encoder = GNNEncoder(
        NODE_FEAT_DIM,
        EDGE_FEAT_DIM,
        hidden_dim=32,
        n_layers=2,
        role_mode="shared_residual",
    )
    readout = PhysicsAwareReadout(hidden_dim=32, set2set_steps=2)

    with torch.no_grad():
        h = encoder(
            batch.x,
            batch.edge_index,
            batch.edge_attr,
            role="solvent",
            batch=batch.batch,
        )
        g = readout(h, batch.batch)

    assert h.shape == (batch.num_nodes, 32)
    assert g.shape == (1, readout.output_dim)
    assert torch.isfinite(h).all()
    assert torch.isfinite(g).all()


def test_tgnn_forward_handles_water_as_solvent() -> None:
    """The full TGNN-Solv forward path should accept water as the solvent graph."""
    solute_graph = smiles_to_graph("CCO")
    solvent_graph = smiles_to_graph("O")
    assert solute_graph is not None
    assert solvent_graph is not None

    solute_batch = Batch.from_data_list([solute_graph])
    solvent_batch = Batch.from_data_list([solvent_graph])
    temperature = torch.tensor([298.15], dtype=torch.float32)
    solvent_type = torch.tensor(
        [solvent_type_id_from_smiles("O")],
        dtype=torch.long,
    )

    model = TGNNSolv(cfg=_small_tgnn_config())
    model.eval()

    with torch.no_grad():
        output, intermediates = model(
            solute_batch,
            solvent_batch,
            temperature,
            solvent_type=solvent_type,
            return_intermediates=True,
        )

    assert output["ln_x2"].shape == (1,)
    assert output["x2"].shape == (1,)
    assert torch.isfinite(output["ln_x2"]).all()
    assert torch.isfinite(output["x2"]).all()
    assert torch.isfinite(intermediates["g_pair"]).all()
    assert torch.isfinite(intermediates["ln_gamma_2"]).all()


def test_timp_forward_handles_explicit_h_water_graph() -> None:
    """TIMP should receive real O-H edges when explicit-H mode is enabled."""
    cfg = _small_tgnn_config()
    cfg.encoder_type = "timp"
    cfg.use_gasteiger_charges = True
    cfg.use_phys_edge_features = True
    cfg.explicit_h_small_molecules = True
    cfg.explicit_h_max_heavy_atoms = 3

    solute_graph = smiles_to_graph(
        "CCO",
        use_gasteiger_charges=True,
        use_phys_edge_features=True,
        explicit_h_small_molecules=True,
    )
    solvent_graph = smiles_to_graph(
        "O",
        use_gasteiger_charges=True,
        use_phys_edge_features=True,
        explicit_h_small_molecules=True,
    )
    assert solute_graph is not None
    assert solvent_graph is not None
    assert solvent_graph.num_atoms == 3
    assert solvent_graph.edge_index.shape[1] == 4

    solute_batch = Batch.from_data_list([solute_graph])
    solvent_batch = Batch.from_data_list([solvent_graph])
    temperature = torch.tensor([298.15], dtype=torch.float32)
    solvent_type = torch.tensor(
        [solvent_type_id_from_smiles("O")],
        dtype=torch.long,
    )

    model = TGNNSolv(cfg=cfg)
    model.eval()

    with torch.no_grad():
        output, intermediates = model(
            solute_batch,
            solvent_batch,
            temperature,
            solvent_type=solvent_type,
            return_intermediates=True,
        )

    assert torch.isfinite(output["ln_x2"]).all()
    assert torch.isfinite(intermediates["g_slv_polar_pre"]).all()
