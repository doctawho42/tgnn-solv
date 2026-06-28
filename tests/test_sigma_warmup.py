"""Tests for run_sigma_warmup_pretraining + area-anchor gate + checkpoint (P1 Task 6)."""
from __future__ import annotations

import sys
sys.path.insert(0, "src")

import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader, tiny_cosmo_config
from tgnn_solv.pretrain_pipeline import (
    run_sigma_warmup_pretraining,
    build_pretrain_checkpoint_payload,
    apply_pretrained_encoder_checkpoint,
)


def test_warmup_reduces_train_emd_and_reports_gate():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    cfg = trainer.cfg
    cfg.sigma_warmup_epochs = 8
    cfg.sigma_warmup_min_epochs = 2
    before = trainer.validate_sigma(loader)["sigma_profile"]
    meta = run_sigma_warmup_pretraining(
        trainer.model, cfg, device=torch.device("cpu"),
        sigma_train_loader=loader, sigma_val_loader=loader)
    after = trainer.validate_sigma(loader)["sigma_profile"]
    assert after <= before  # warmup should not worsen the fit on the same data
    assert "area_mae" in meta and "area_gate_passed" in meta


def test_checkpoint_roundtrips_sigma_head():
    cfg = tiny_cosmo_config()
    from tgnn_solv.model import TGNNSolv
    model = TGNNSolv(cfg=cfg)
    payload = build_pretrain_checkpoint_payload(
        model=model, config=cfg, pretrain_history={}, pretrain_source="sigma_warmup",
        pretrain_epochs=0, pretrain_batch_size=0, pretrain_lr=0.0, smiles_count=0)
    assert "sigma_head_state_dict" in payload
    model2 = TGNNSolv(cfg=cfg)
    apply_pretrained_encoder_checkpoint(model2, payload, strict=False)
    for (k, a), (_, b) in zip(model.head_sigma.state_dict().items(),
                              model2.head_sigma.state_dict().items()):
        assert torch.allclose(a, b)


def test_warmup_skips_when_no_head_sigma():
    """Non-cosmo models (no head_sigma) should get skipped gracefully."""
    from tgnn_solv.config import TGNNSolvConfig
    from tgnn_solv.model import TGNNSolv
    from tgnn_solv.data.dataset import make_loader
    import pandas as pd
    import numpy as np

    cfg = TGNNSolvConfig(activity_model="nrtl", hidden_dim=32, n_gnn_layers=2,
                         n_cross_attn_layers=1, n_attn_heads=4, pair_dim=64,
                         solvent_moe_hidden=64, solvent_type_emb_dim=8,
                         n_iter_train=2, n_iter_eval=2, set2set_steps=2)
    cfg.sigma_warmup_epochs = 4
    model = TGNNSolv(cfg=cfg)
    assert getattr(model, "head_sigma", None) is None
    meta = run_sigma_warmup_pretraining(
        model, cfg, device=torch.device("cpu"),
        sigma_train_loader=[], sigma_val_loader=None)
    assert meta.get("skipped") is True


def test_area_gate_warning_not_raise_by_default():
    """With sigma_area_anchor_strict=False the gate only warns, not raises."""
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    cfg = trainer.cfg
    cfg.sigma_warmup_epochs = 2
    cfg.sigma_warmup_min_epochs = 1
    cfg.sigma_area_anchor_mae_tol = 0.0   # force gate to fail
    cfg.sigma_area_anchor_strict = False   # default: warn, not raise
    # Should not raise even with tol=0
    meta = run_sigma_warmup_pretraining(
        trainer.model, cfg, device=torch.device("cpu"),
        sigma_train_loader=loader, sigma_val_loader=loader)
    assert meta["area_gate_passed"] is False


def test_area_gate_raises_when_strict():
    """With sigma_area_anchor_strict=True the gate raises on failure."""
    import pytest
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    cfg = trainer.cfg
    cfg.sigma_warmup_epochs = 2
    cfg.sigma_warmup_min_epochs = 1
    cfg.sigma_area_anchor_mae_tol = 0.0   # force gate to fail
    cfg.sigma_area_anchor_strict = True
    with pytest.raises(RuntimeError, match="sigma area-anchor gate FAILED"):
        run_sigma_warmup_pretraining(
            trainer.model, cfg, device=torch.device("cpu"),
            sigma_train_loader=loader, sigma_val_loader=loader)
