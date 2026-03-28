"""Tests for DirectGNN trainer resume orchestration."""

from __future__ import annotations

import sys
import types

import torch

sys.path.insert(0, "src")

from tgnn_solv.baselines.direct_gnn import DirectGNN, DirectGNNTrainer  # noqa: E402
from tgnn_solv.config import TGNNSolvConfig  # noqa: E402


def make_small_config() -> TGNNSolvConfig:
    """Create a lightweight DirectGNN config for trainer-state tests."""
    return TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        set2set_steps=2,
        epochs_phase2=4,
    )


def test_direct_gnn_trainer_state_dict_round_trip() -> None:
    cfg = make_small_config()
    trainer = DirectGNNTrainer(DirectGNN(cfg=cfg))

    trainer.best_val_mae = 1.23
    trainer.best_state = {"dummy_weight": torch.tensor([1.0, 2.0])}
    trainer.patience_counter = 3
    trainer.history["train_loss"] = [0.9, 0.5]
    trainer.history["val_mae"] = [1.4, 1.23]
    trainer.history["val_r2"] = [0.1, 0.2]

    restored = DirectGNNTrainer(DirectGNN(cfg=cfg))
    restored.load_state_dict(trainer.state_dict())

    assert restored.best_val_mae == 1.23
    assert restored.patience_counter == 3
    assert restored.history["train_loss"] == [0.9, 0.5]
    assert restored.history["val_mae"] == [1.4, 1.23]
    assert restored.history["val_r2"] == [0.1, 0.2]
    assert torch.equal(
        restored.best_state["dummy_weight"],
        torch.tensor([1.0, 2.0]),
    )


def test_direct_gnn_train_resume_respects_start_epoch_and_emits_resume_state() -> None:
    cfg = make_small_config()
    trainer = DirectGNNTrainer(DirectGNN(cfg=cfg))
    callback_states: list[dict[str, object]] = []

    trainer._evaluate_loader = types.MethodType(  # type: ignore[method-assign]
        lambda self, loader: {
            "n": 1,
            "mae": 1.0,
            "rmse": 1.0,
            "r2": 0.0,
            "bias": 0.0,
        },
        trainer,
    )

    train_metrics = trainer.train(
        [],
        [],
        n_epochs=4,
        patience=10,
        start_epoch=2,
        on_epoch_end=callback_states.append,
    )

    assert train_metrics["best_val_mae"] == 1.0
    assert [state["next_epoch"] for state in callback_states] == [3, 4]
    assert all(state["status"] == "in_progress" for state in callback_states)
    assert all("optimizer_state_dict" in state for state in callback_states)
    assert all("scheduler_state_dict" in state for state in callback_states)
