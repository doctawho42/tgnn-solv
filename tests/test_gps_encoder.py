"""Focused tests for the optional GPS graph encoder."""

from __future__ import annotations

import sys

import torch
from torch_geometric.data import Batch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import collate_fn
from tgnn_solv.data.solvent_types import solvent_type_id_from_smiles
from tgnn_solv.features import EDGE_FEAT_DIM, NODE_FEAT_DIM, smiles_to_graph
from tgnn_solv.layers import GPSEncoder
from tgnn_solv.model import TGNNSolv
from tgnn_solv.positional_encoding import PositionalEncoding


def make_gps_config(**overrides: object) -> TGNNSolvConfig:
    """Build a compact GPS config for unit tests."""
    base = dict(
        hidden_dim=32,
        n_gnn_layers=2,
        encoder_type="gps",
        encoder_role_mode="shared_residual",
        encoder_role_specific_layers=1,
        gps_num_heads=4,
        gps_use_edge_attr=True,
        gps_positional_encoding="laplacian",
        gps_pe_dim=8,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        n_iter_train=2,
        n_iter_eval=2,
        set2set_steps=2,
        dropout=0.1,
    )
    base.update(overrides)
    return TGNNSolvConfig(**base)


def make_graph_batch(smiles_list: list[str]) -> Batch:
    """Build a PyG batch from SMILES strings."""
    graphs = [smiles_to_graph(smi) for smi in smiles_list]
    assert all(graph is not None for graph in graphs)
    return Batch.from_data_list(graphs)  # type: ignore[arg-type]


def make_model_inputs(
    pairs: list[tuple[str, str, float]],
) -> tuple[Batch, Batch, torch.Tensor, torch.Tensor]:
    """Create a minimal TGNN batch for smoke testing."""
    samples = []
    for solute_smiles, solvent_smiles, temperature in pairs:
        solute_graph = smiles_to_graph(solute_smiles)
        solvent_graph = smiles_to_graph(solvent_smiles)
        assert solute_graph is not None
        assert solvent_graph is not None
        samples.append(
            (
                solute_graph,
                solvent_graph,
                {
                    "T": torch.tensor(float(temperature), dtype=torch.float32),
                    "solvent_type": torch.tensor(
                        solvent_type_id_from_smiles(solvent_smiles),
                        dtype=torch.long,
                    ),
                },
            )
        )
    solute_batch, solvent_batch, targets = collate_fn(samples)
    return solute_batch, solvent_batch, targets["T"], targets["solvent_type"]


def test_positional_encodings_return_finite_features() -> None:
    """Both supported positional encodings should return finite `(N, pe_dim)` tensors."""
    batch = make_graph_batch(["CCO", "c1ccccc1"])

    for kind in ("laplacian", "rwse"):
        pe = PositionalEncoding(8, kind)(
            batch.edge_index,
            batch.num_nodes,
            batch=batch.batch,
        )
        assert pe.shape == (batch.num_nodes, 8)
        assert torch.isfinite(pe).all()


def test_gps_encoder_preserves_node_hidden_shape() -> None:
    """GPSEncoder must remain a drop-in replacement for the existing node encoder."""
    cfg = make_gps_config(encoder_role_mode="split_late")
    encoder = GPSEncoder(
        NODE_FEAT_DIM,
        EDGE_FEAT_DIM,
        hidden_dim=cfg.hidden_dim,
        n_layers=cfg.n_gnn_layers,
        role_mode=cfg.encoder_role_mode,
        role_specific_layers=cfg.encoder_role_specific_layers,
        gps_num_heads=cfg.gps_num_heads,
        gps_use_edge_attr=cfg.gps_use_edge_attr,
        gps_positional_encoding=cfg.gps_positional_encoding,
        gps_pe_dim=cfg.gps_pe_dim,
        dropout=cfg.dropout,
    )
    batch = make_graph_batch(["CCO", "CCN", "c1ccccc1"])

    out_solute = encoder(
        batch.x,
        batch.edge_index,
        batch.edge_attr,
        role="solute",
        batch=batch.batch,
    )
    out_solvent = encoder(
        batch.x,
        batch.edge_index,
        batch.edge_attr,
        role="solvent",
        batch=batch.batch,
    )

    assert out_solute.shape == (batch.num_nodes, cfg.hidden_dim)
    assert out_solvent.shape == (batch.num_nodes, cfg.hidden_dim)
    assert torch.isfinite(out_solute).all()
    assert torch.isfinite(out_solvent).all()


def test_tgnn_with_gps_encoder_runs_end_to_end() -> None:
    """TGNN should swap in GPS without changing the rest of the forward path."""
    cfg = make_gps_config()
    model = TGNNSolv(cfg=cfg)
    model.eval()
    solute_batch, solvent_batch, temperature, solvent_type = make_model_inputs(
        [("CCO", "O", 298.15), ("CCN", "CCO", 315.0)]
    )

    with torch.no_grad():
        out = model(
            solute_batch,
            solvent_batch,
            temperature,
            solvent_type=solvent_type,
        )

    assert model.gnn.__class__.__name__ == "GPSEncoder"
    assert out["ln_x2"].shape == (2,)
    assert torch.isfinite(out["ln_x2"]).all()
