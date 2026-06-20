"""Tests for TGNN trainer resume orchestration."""

from __future__ import annotations

import sys
import types

import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer


def make_small_config() -> TGNNSolvConfig:
    """Create a lightweight config for trainer-state tests."""
    return TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        n_iter_train=2,
        n_iter_eval=2,
        set2set_steps=2,
        epochs_phase1=2,
        epochs_phase2=3,
        epochs_phase3=2,
    )


def test_trainer_state_dict_round_trip_preserves_resume_state() -> None:
    cfg = make_small_config()
    model = TGNNSolv(cfg=cfg)
    trainer = TGNNSolvTrainer(model, cfg)

    trainer.history["train_loss"] = [1.0, 0.5]
    trainer.best_val_loss = 1.23
    trainer.best_state = {
        "dummy_weight": torch.tensor([1.0, 2.0]),
    }
    trainer.best_epoch = 7
    trainer.best_phase = 2
    trainer.patience_counter = 4
    trainer._last_confidence = 0.75
    trainer.cfg.oracle_injection_prob = 0.4
    trainer.model.cfg.oracle_injection_prob = 0.4

    restored = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    restored.load_state_dict(trainer.state_dict())

    assert restored.history["train_loss"] == [1.0, 0.5]
    assert restored.best_val_loss == 1.23
    assert restored.best_epoch == 7
    assert restored.best_phase == 2
    assert restored.patience_counter == 4
    assert restored._last_confidence == 0.75
    assert restored.cfg.oracle_injection_prob == 0.4
    assert restored.model.cfg.oracle_injection_prob == 0.4
    assert torch.equal(
        restored.best_state["dummy_weight"],
        torch.tensor([1.0, 2.0]),
    )


def test_train_full_resume_skips_completed_phases_and_reuses_phase_state() -> None:
    cfg = make_small_config()
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    calls: list[tuple[int, int, bool, bool]] = []

    def fake_train_phase(self, phase, train_loader, val_loader, n_epochs, **kwargs):
        calls.append(
            (
                phase,
                kwargs.get("start_epoch", 0),
                kwargs.get("optimizer_state_dict") is not None,
                kwargs.get("scheduler_state_dict") is not None,
            )
        )

    trainer.train_phase = types.MethodType(fake_train_phase, trainer)
    trainer.train_full(
        None,
        None,
        resume_state={
            "status": "in_progress",
            "phase": 2,
            "next_epoch_in_phase": 2,
            "optimizer_state_dict": {"state": {}, "param_groups": []},
            "scheduler_state_dict": {"base_lrs": [1e-4], "last_epoch": 1},
        },
    )

    assert calls == [
        (2, 2, True, True),
        (3, 0, False, False),
    ]


def test_phase1_gc_residual_freeze_schedule_unfreezes_after_configured_epochs() -> None:
    cfg = make_small_config()
    cfg.use_gc_priors_crystal = True
    cfg.gc_prior_residual_freeze_epochs = 1
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    frozen_states: list[tuple[bool, bool]] = []

    def fake_train_epoch(
        self,
        loader,
        optimizer,
        phase,
        epoch,
        compute_mono=False,
        **_kwargs,
    ):
        frozen_states.append(
            (
                all(
                    not param.requires_grad
                    for param in self.model.fusion_head.residual_mlp_Tm.parameters()
                ),
                all(
                    not param.requires_grad
                    for param in self.model.fusion_head.residual_mlp_dH.parameters()
                ),
            )
        )
        return 0.0, {}

    def fake_validate(self, loader, phase, **_kwargs):
        return {"val_loss": 0.0}

    trainer.train_epoch = types.MethodType(fake_train_epoch, trainer)
    trainer.validate = types.MethodType(fake_validate, trainer)

    trainer.train_phase(1, None, None, n_epochs=2)

    assert frozen_states == [(True, True), (False, False)]
    assert all(
        param.requires_grad for param in trainer.model.fusion_head.residual_mlp_Tm.parameters()
    )
    assert all(
        param.requires_grad for param in trainer.model.fusion_head.residual_mlp_dH.parameters()
    )


def test_phase2_early_stopping_restores_best_state() -> None:
    cfg = make_small_config()
    cfg.early_stopping_patience = 1
    cfg.early_stopping_min_epochs = 1
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)

    validation_sequence = iter(
        [
            {"val_loss": 1.0, "mae": 0.50, "r2": 0.0},  # phase-start baseline
            {"val_loss": 0.9, "mae": 0.40, "r2": 0.0},   # epoch 0 improves
            {"val_loss": 1.1, "mae": 0.60, "r2": 0.0},  # epoch 1 triggers stop
        ]
    )
    snapshot_sequence = iter([100.0, 200.0])
    restored_markers: list[float] = []

    def fake_validate(self, loader, phase, **_kwargs):
        return next(validation_sequence)

    def fake_train_epoch(
        self,
        loader,
        optimizer,
        phase,
        epoch,
        compute_mono=False,
        **_kwargs,
    ):
        return 0.0, {"raw": {}, "weighted": {}, "weights": {}}

    def fake_clone_model_state(self):
        return {"marker": torch.tensor([next(snapshot_sequence)])}

    def fake_load_state_dict(state_dict, strict=True):
        restored_markers.append(float(state_dict["marker"].item()))
        return None

    trainer.validate = types.MethodType(fake_validate, trainer)
    trainer.train_epoch = types.MethodType(fake_train_epoch, trainer)
    trainer._clone_model_state = types.MethodType(fake_clone_model_state, trainer)
    trainer.model.load_state_dict = fake_load_state_dict

    trainer.train_phase(2, None, None, n_epochs=3)

    assert trainer.best_val_loss == 0.40
    assert trainer.best_epoch == 0
    assert restored_markers[-1] == 200.0


def test_coordinate_descent_phase2_freezes_crystal_branch_and_keeps_activity_live() -> None:
    cfg = make_small_config()
    cfg.branch_training_mode = "coordinate_descent"
    cfg.use_aux_direct_sol_loss = True
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)

    trainer._configure_phase_branch_training(2)
    weights = trainer._weights_for_epoch(2, epoch=0, n_epochs=cfg.epochs_phase2)

    assert all(not p.requires_grad for p in trainer.model.gnn.parameters())
    assert all(not p.requires_grad for p in trainer.model.head_fusion.parameters())
    assert any(p.requires_grad for p in trainer.model.pair_repr.parameters())
    assert any(p.requires_grad for p in trainer.model.head_nrtl.parameters())
    assert trainer.cfg.detach_crystal_from_encoder is True
    assert trainer.cfg.detach_crystal_params_in_sle is True
    assert weights["sol"] > 0.0
    assert weights["gamma_inf"] > 0.0
    assert weights["T_m"] == 0.0
    assert weights["dH"] == 0.0
    assert weights["hansen"] == 0.0


def test_coordinate_descent_phase3_freezes_activity_branch_and_restores_crystal_gradients() -> None:
    cfg = make_small_config()
    cfg.branch_training_mode = "coordinate_descent"
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)

    trainer._configure_phase_branch_training(3)
    weights = trainer._weights_for_epoch(3, epoch=0, n_epochs=cfg.epochs_phase3)

    assert any(p.requires_grad for p in trainer.model.gnn.parameters())
    assert any(p.requires_grad for p in trainer.model.head_fusion.parameters())
    assert all(not p.requires_grad for p in trainer.model.pair_repr.parameters())
    assert all(not p.requires_grad for p in trainer.model.head_nrtl.parameters())
    assert all(not p.requires_grad for p in trainer.model.correction.parameters())
    assert trainer.cfg.detach_crystal_from_encoder is False
    assert trainer.cfg.detach_crystal_params_in_sle is False
    assert weights["sol"] > 0.0
    assert weights["T_m"] > 0.0
    assert weights["gamma_inf"] == 0.0
    assert weights["gamma_2"] == 0.0


def test_coordinate_descent_phase3_keeps_correction_frozen_during_training() -> None:
    cfg = make_small_config()
    cfg.branch_training_mode = "coordinate_descent"
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    correction_frozen_states: list[bool] = []

    def fake_train_epoch(
        self,
        loader,
        optimizer,
        phase,
        epoch,
        compute_mono=False,
        **_kwargs,
    ):
        correction_frozen_states.append(
            all(not param.requires_grad for param in self.model.correction.parameters())
        )
        return 0.0, {"raw": {}, "weighted": {}, "weights": {}}

    def fake_validate(self, loader, phase, **_kwargs):
        return {"val_loss": 0.0, "mae": 0.0, "r2": 0.0}

    trainer.train_epoch = types.MethodType(fake_train_epoch, trainer)
    trainer.validate = types.MethodType(fake_validate, trainer)

    trainer.train_phase(3, None, None, n_epochs=1)

    assert correction_frozen_states == [True]
