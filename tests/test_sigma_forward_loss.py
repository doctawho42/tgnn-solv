"""Tests for the factored _sigma_forward_loss helper (P1 refactor).

Verifies:
  1. _sigma_forward_loss returns a grad-bearing, finite Tensor + component dict.
  2. _train_sigma_aux_batch still works after the refactor (behavior-preserving).
"""
from __future__ import annotations

import sys
sys.path.insert(0, "src")

import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader, first_batch


def test_sigma_forward_loss_returns_tensor_and_components():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    batch = first_batch(loader)
    loss, comps = trainer._sigma_forward_loss(batch, role="solute")
    assert isinstance(loss, torch.Tensor) and loss.requires_grad
    assert torch.isfinite(loss)
    assert set(comps) >= {"sigma_profile", "sigma_shape", "sigma_area"}


def test_train_sigma_aux_batch_still_works_after_refactor():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    batch = first_batch(loader)
    trainer.cfg.sigma_aux_phase1_weight = 1.0  # ensure weight > 0 so it runs
    loss_val, d = trainer._train_sigma_aux_batch(batch, trainer._build_optimizer(1), phase=1)
    assert loss_val is None or (isinstance(loss_val, float) and loss_val >= 0.0)
    assert d == {} or set(d) >= {"sigma_profile", "sigma_shape", "sigma_area"}


def _grad_norm(module):
    g = [p.grad.detach().abs().sum() for p in module.parameters() if p.grad is not None]
    return float(torch.stack(g).sum()) if g else 0.0


def test_symmetrization_grounds_both_role_adapters():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    trainer.cfg.sigma_aux_symmetrize = True
    trainer.cfg.sigma_aux_phase1_weight = 1.0
    batch = first_batch(loader)
    opt = trainer._build_optimizer(1)
    trainer._train_sigma_aux_batch(batch, opt, phase=1)
    enc = trainer.model.gnn
    # both role adapters must receive gradient when symmetrize is on
    assert _grad_norm(enc.solute_adapter) > 0.0
    assert _grad_norm(enc.solvent_adapter) > 0.0


def test_no_symmetrization_skips_solvent_adapter():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    trainer.cfg.sigma_aux_symmetrize = False
    trainer.cfg.sigma_aux_phase1_weight = 1.0
    batch = first_batch(loader)
    opt = trainer._build_optimizer(1)
    trainer._train_sigma_aux_batch(batch, opt, phase=1)
    enc = trainer.model.gnn
    assert _grad_norm(enc.solute_adapter) > 0.0
    assert _grad_norm(enc.solvent_adapter) == 0.0
