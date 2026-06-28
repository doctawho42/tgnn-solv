"""Tests for freeze_sigma_head_during_sle (Task 5).

Verifies that:
- When freeze_sigma_head_during_sle=True and phase >= 2, head_sigma parameters
  have requires_grad=False after _configure_phase_branch_training.
- When freeze_sigma_head_during_sle=False (default), head_sigma stays trainable
  in all phases.
"""
from sigma_fixtures import tiny_cosmo_config
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer


def _trainer():
    cfg = tiny_cosmo_config()
    cfg.freeze_sigma_head_during_sle = True
    model = TGNNSolv(cfg=cfg)
    return TGNNSolvTrainer(model, cfg)


def test_head_frozen_in_phase2_unfrozen_in_phase1():
    t = _trainer()
    t._configure_phase_branch_training(1)
    assert all(p.requires_grad for p in t.model.head_sigma.parameters())
    t._configure_phase_branch_training(2)
    assert all(not p.requires_grad for p in t.model.head_sigma.parameters())
    t._configure_phase_branch_training(3)
    assert all(not p.requires_grad for p in t.model.head_sigma.parameters())


def test_flag_off_keeps_head_trainable():
    cfg = tiny_cosmo_config()
    cfg.freeze_sigma_head_during_sle = False
    t = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    t._configure_phase_branch_training(2)
    assert all(p.requires_grad for p in t.model.head_sigma.parameters())
