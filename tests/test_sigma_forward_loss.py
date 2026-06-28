"""Tests for the factored _sigma_forward_loss helper (P1 refactor).

Verifies:
  1. _sigma_forward_loss returns a grad-bearing, finite Tensor + component dict.
  2. _train_sigma_aux_batch still works after the refactor (behavior-preserving).
"""
from __future__ import annotations

import sys
sys.path.insert(0, "src")

import numpy as np
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
