"""End-to-end smoke test for Task 7: CLI wiring for sigma-warmup (P1).

Exercises the whole path that scripts/train.py now threads:
  1. run_sigma_warmup_pretraining on a tiny fixture (2 epochs)
  2. _configure_phase_branch_training(2) with freeze_sigma_head_during_sle=True
  3. asserts head_sigma frozen and checkpoint saved
"""
from __future__ import annotations

import sys
sys.path.insert(0, "src")

import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader
from tgnn_solv.pretrain_pipeline import run_sigma_warmup_pretraining


def test_warmup_then_one_sle_step_runs(tmp_path):
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    cfg = trainer.cfg
    cfg.sigma_warmup_epochs = 2
    cfg.sigma_warmup_min_epochs = 1
    cfg.freeze_sigma_head_during_sle = True
    # warmup grounds the head
    meta = run_sigma_warmup_pretraining(
        trainer.model, cfg, device=torch.device("cpu"),
        sigma_train_loader=loader, sigma_val_loader=loader,
        save_path=str(tmp_path / "warm.pt"))
    assert not meta.get("skipped"), f"warmup was unexpectedly skipped: {meta}"
    assert meta["epochs_run"] >= 1
    # freeze takes effect for SLE phases
    trainer._configure_phase_branch_training(2)
    assert all(not p.requires_grad for p in trainer.model.head_sigma.parameters())
    assert (tmp_path / "warm.pt").exists()
