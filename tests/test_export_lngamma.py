"""Unit tests for Task 3 — per-row ln γ₂ export + σ-oracle injection.

Tests the two new unit-level pieces that the export script depends on:
(a) the cosmo_sac forward output carries physics.ln_gamma_2 of shape (B,);
(b) build_oracle_tensors correctly marks only known SMILES.

These are regression locks for the export's data source.
"""
from __future__ import annotations

import numpy as np
import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader
from tgnn_solv.sigma_oracle import build_oracle_tensors


def test_forward_exposes_ln_gamma_2():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    model = trainer.model
    model.eval()
    sol_b, slv_b, targets = trainer._move_batch_to_device(next(iter(loader)))
    with torch.no_grad():
        out = model(sol_b, slv_b, targets["T"], targets=targets)
    assert "physics" in out and "ln_gamma_2" in out["physics"]
    assert out["physics"]["ln_gamma_2"].shape[0] == len(targets["solute_smiles"])


def test_oracle_tensors_match_only_known_smiles():
    table = {"CCO": (np.zeros(51), 88.0)}
    p, A, mask = build_oracle_tensors(["CCO", "CCCCCC"], table, n_bins=51)
    assert bool(mask[0]) and not bool(mask[1])
