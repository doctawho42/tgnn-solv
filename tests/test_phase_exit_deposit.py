"""The per-phase hook must hand out the state the NEXT phase starts from.

Phase 3 restores its own best at the end, and on every arm measured so far that best is the
state it was handed, so the end-of-run checkpoint already carries these weights. It carries them
by coincidence. The first time Phase 3 improves on its entry state, that entry state is
overwritten and the cost of the phase stops being computable at all. ``on_phase_end`` exists so
the entry state is written down either way.

The order is the whole contract. A hook that fired before the per-phase restore would deposit
the degraded last-epoch weights, and nothing downstream would reveal it: the file would exist,
carry the right name, and be wrong.
"""

from __future__ import annotations

import sys
import types

import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer


def make_small_config() -> TGNNSolvConfig:
    """Create a lightweight config for trainer-orchestration tests."""
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


def test_train_full_threads_on_phase_end_to_every_phase() -> None:
    cfg = make_small_config()
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    received: list[tuple[int, object]] = []

    def fake_train_phase(self, phase, train_loader, val_loader, n_epochs, **kwargs):
        received.append((phase, kwargs.get("on_phase_end")))

    def hook(phase: int) -> None:
        return None

    trainer.train_phase = types.MethodType(fake_train_phase, trainer)
    trainer.train_full(None, None, on_phase_end=hook)

    assert [phase for phase, _ in received] == [1, 2, 3]
    assert all(seen is hook for _, seen in received), "the hook did not reach every phase"


def test_on_phase_end_fires_after_the_restore_so_it_sees_the_phase_best() -> None:
    """The hook must run after the tail restore, and this must be able to fail.

    Early stopping restores the best state inside the loop, before ``break``, so a phase that
    stops early has already been restored by the time the tail runs. A test written on that path
    passes wherever the hook sits, which is no test at all. This phase therefore runs to its full
    length with its best at epoch 0: nothing is restored until the tail, so a hook placed before
    it observes no restore at all.
    """
    cfg = make_small_config()
    cfg.early_stopping_min_epochs = 10  # longer than the phase, so early stopping cannot fire
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)

    validation_sequence = iter(
        [
            {"val_loss": 1.0, "mae": 0.50, "r2": 0.0},  # phase-start baseline
            {"val_loss": 0.9, "mae": 0.40, "r2": 0.0},  # epoch 0 improves, and stays the best
            {"val_loss": 1.1, "mae": 0.60, "r2": 0.0},  # epoch 1 is worse
            {"val_loss": 1.2, "mae": 0.70, "r2": 0.0},  # epoch 2 is worse still, and is last
        ]
    )
    snapshot_sequence = iter([100.0, 200.0])
    restored_markers: list[float] = []
    seen: list[tuple[int, list[float]]] = []

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

    trainer.train_phase(
        2,
        None,
        None,
        n_epochs=3,
        on_phase_end=lambda phase: seen.append((phase, list(restored_markers))),
    )

    assert len(seen) == 1, "the hook must fire exactly once per phase"
    phase, markers_at_hook_time = seen[0]
    assert phase == 2
    assert markers_at_hook_time, (
        "the hook fired before the tail restore, so it would deposit the last-epoch weights"
    )
    assert markers_at_hook_time[-1] == 200.0, (
        "the hook saw a state other than the phase best, so the deposited checkpoint would "
        "be the wrong weights under the right name"
    )


def test_on_phase_end_is_optional() -> None:
    """Every existing caller omits the hook, and must keep working untouched."""
    cfg = make_small_config()
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    calls: list[int] = []

    def fake_train_phase(self, phase, train_loader, val_loader, n_epochs, **kwargs):
        calls.append(phase)
        assert kwargs.get("on_phase_end") is None

    trainer.train_phase = types.MethodType(fake_train_phase, trainer)
    trainer.train_full(None, None)

    assert calls == [1, 2, 3]


def test_zero_epoch_phase_is_skipped_entirely_and_never_fires_the_hook() -> None:
    """configs/cosmo_sac.yaml now runs Phase 3 at zero epochs, so the skip must stay a skip.

    A loop that entered a zero-length phase would train nothing, reach the tail with the
    phase's own best unset, and deposit that under a Phase 3 name. The config change rests
    entirely on this branch, so the branch gets a test rather than a reading of the loop.
    """
    cfg = make_small_config()
    cfg.epochs_phase3 = 0
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    trained: list[int] = []
    hooked: list[int] = []

    def fake_train_phase(self, phase, train_loader, val_loader, n_epochs, **kwargs):
        trained.append(phase)
        hook = kwargs.get("on_phase_end")
        if hook is not None:
            hook(phase)

    trainer.train_phase = types.MethodType(fake_train_phase, trainer)
    trainer.train_full(None, None, on_phase_end=hooked.append)

    assert trained == [1, 2], "a phase configured for zero epochs must not be entered"
    assert hooked == [1, 2], "the hook must not fire for a phase that never ran"
