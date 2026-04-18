"""Tests for optional Stage 0 pretraining utilities."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.model import TGNNSolv
from tgnn_solv.pretrain import Pretrainer
from tgnn_solv.pretrain_pipeline import (
    apply_pretrained_encoder_checkpoint,
    load_pretraining_smiles,
    load_pretrained_encoder_checkpoint,
    run_stage0_pretraining,
)


def make_small_config(**overrides: object) -> TGNNSolvConfig:
    """Create a compact config for Stage 0 tests."""
    base = dict(
        hidden_dim=32,
        n_gnn_layers=2,
        encoder_role_mode="shared_residual",
        encoder_role_specific_layers=1,
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


def test_load_pretraining_smiles_from_csv(tmp_path: Path) -> None:
    """Local CSV sources should load like `zinc250k`, with optional truncation."""
    csv_path = tmp_path / "pretrain.csv"
    pd.DataFrame({"smiles": ["CCO", "CCN", "O", "c1ccccc1"]}).to_csv(
        csv_path,
        index=False,
    )

    smiles = load_pretraining_smiles(str(csv_path), max_molecules=3)

    assert smiles == ["CCO", "CCN", "O"]


def test_pretrainer_runs_with_gps_encoder() -> None:
    """Stage 0 should pass `batch` through the encoder so GPS can pretrain safely."""
    cfg = make_small_config(
        encoder_type="gps",
        gps_num_heads=4,
        gps_positional_encoding="laplacian",
        gps_pe_dim=8,
    )
    model = TGNNSolv(cfg=cfg)
    pretrainer = Pretrainer(model.gnn, model.readout, cfg, device=torch.device("cpu"))

    history = pretrainer.pretrain(
        ["CCO", "CCN", "O", "c1ccccc1"],
        n_epochs=1,
        batch_size=2,
        lr=1.0e-3,
    )

    assert set(history) == {"total", "atom", "bond", "prop", "contrastive"}
    assert all(len(values) == 1 for values in history.values())


def test_pretrainer_runs_with_pairwise_contrastive_artifact(tmp_path: Path) -> None:
    """Stage 0 can consume materialized pairwise compatibility rows."""
    cfg = make_small_config()
    model = TGNNSolv(cfg=cfg)
    pretrainer = Pretrainer(model.gnn, model.readout, cfg, device=torch.device("cpu"))
    pairwise_path = tmp_path / "pairwise.csv"
    pd.DataFrame(
        {
            "solvent_smiles": ["O", "CCO"],
            "solute_a_smiles": ["CCO", "CCN"],
            "solute_b_smiles": ["CCN", "CCO"],
            "contrastive_label": [1, 0],
            "sample_weight": [1.0, 0.5],
        }
    ).to_csv(pairwise_path, index=False)

    history = pretrainer.pretrain(
        ["CCO", "CCN", "O", "c1ccccc1"],
        n_epochs=1,
        batch_size=2,
        lr=1.0e-3,
        pairwise_contrastive_csv=pairwise_path,
        pairwise_contrastive_weight=0.1,
        pairwise_contrastive_batch_size=2,
    )

    assert set(history) == {
        "total",
        "atom",
        "bond",
        "prop",
        "contrastive",
        "pairwise",
    }
    assert all(len(values) == 1 for values in history.values())


def test_stage0_checkpoint_roundtrip(tmp_path: Path) -> None:
    """Saved Stage 0 checkpoints should restore `gnn` and `readout` exactly."""
    cfg = make_small_config()
    model = TGNNSolv(cfg=cfg)
    smiles_path = tmp_path / "stage0.txt"
    smiles_path.write_text("CCO\nCCN\nO\nc1ccccc1\n", encoding="utf-8")
    checkpoint_path = tmp_path / "pretrained_encoder.pt"

    metadata = run_stage0_pretraining(
        model,
        cfg,
        device=torch.device("cpu"),
        pretrain_source=str(smiles_path),
        pretrain_epochs=1,
        pretrain_batch_size=2,
        pretrain_lr=1.0e-3,
        save_path=checkpoint_path,
    )

    assert checkpoint_path.is_file()
    assert metadata["smiles_count"] == 4
    assert metadata["checkpoint_path"] == str(checkpoint_path.resolve())

    restored_model = TGNNSolv(cfg=cfg)
    checkpoint = load_pretrained_encoder_checkpoint(checkpoint_path)
    load_metadata = apply_pretrained_encoder_checkpoint(restored_model, checkpoint)

    assert load_metadata["gnn_missing_keys"] == []
    assert load_metadata["gnn_unexpected_keys"] == []
    assert load_metadata["readout_missing_keys"] == []
    assert load_metadata["readout_unexpected_keys"] == []

    for (name_a, tensor_a), (name_b, tensor_b) in zip(
        model.gnn.state_dict().items(),
        restored_model.gnn.state_dict().items(),
        strict=True,
    ):
        assert name_a == name_b
        assert torch.allclose(tensor_a, tensor_b)

    for (name_a, tensor_a), (name_b, tensor_b) in zip(
        model.readout.state_dict().items(),
        restored_model.readout.state_dict().items(),
        strict=True,
    ):
        assert name_a == name_b
        assert torch.allclose(tensor_a, tensor_b)
