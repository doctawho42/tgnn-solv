"""The first epoch of Phase 2 must be written down, and under the right epoch.

On the ``control`` arm's three seeds the best Phase 2 epoch was the 1st, the 24th and the 29th,
and everything the later epochs bought over the first was 0.000, 0.044 and 0.133 of val MAE --
against a 0.313 spread between those same three seeds on test. So "does Phase 2 after its first
epoch buy anything on the surface the claim lives on" is a question about an artifact nobody has:
the only state written out is the best-val one, and the first epoch's weights are overwritten by
the second.

Two failure modes make the deposit useless while leaving every log line intact. It can name the
wrong epoch -- ``next_epoch_in_phase`` is never 0, so a predicate reading that key never fires at
all -- and it can sit behind an unrelated early return, in which case it never runs under the
default config. Both are tested here, the second at source level, because the consumer is a
closure inside ``main`` and only its predicate is importable.
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tgnn_solv.config import TGNNSolvConfig  # noqa: E402
from tgnn_solv.model import TGNNSolv  # noqa: E402
from tgnn_solv.trainer import TGNNSolvTrainer  # noqa: E402
from train import is_phase2_first_epoch  # noqa: E402


def make_small_config() -> TGNNSolvConfig:
    """Lightweight config for trainer-orchestration tests."""
    cfg = TGNNSolvConfig(
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
        epochs_phase1=3,
        epochs_phase2=3,
        epochs_phase3=3,
    )
    # Longer than any phase below, so early stopping cannot truncate a phase and hide a
    # hook that fires on the wrong epoch.
    cfg.early_stopping_min_epochs = 10
    return cfg


def run_phase_and_collect(phase: int, n_epochs: int = 3) -> list[dict]:
    """Drive one phase with fake train/validate and return every epoch-end payload."""
    cfg = make_small_config()
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    payloads: list[dict] = []

    def fake_validate(self, loader, phase, **_kwargs):
        return {"val_loss": 1.0, "mae": 0.5, "r2": 0.0}

    def fake_train_epoch(self, loader, optimizer, phase, epoch, compute_mono=False, **_kwargs):
        return 0.0, {"raw": {}, "weighted": {}, "weights": {}}

    def fake_clone_model_state(self):
        return {"marker": torch.tensor([0.0])}

    trainer.validate = types.MethodType(fake_validate, trainer)
    trainer.train_epoch = types.MethodType(fake_train_epoch, trainer)
    trainer._clone_model_state = types.MethodType(fake_clone_model_state, trainer)
    trainer.model.load_state_dict = lambda state_dict, strict=True: None

    trainer.train_phase(
        phase,
        None,
        None,
        n_epochs=n_epochs,
        on_epoch_end=lambda state: payloads.append(dict(state)),
    )
    return payloads


# ------------------------------------------------------------------ #
#  The predicate                                                      #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("phase", [1, 2, 3])
@pytest.mark.parametrize("epoch_in_phase", [0, 1, 2, 29])
def test_predicate_fires_only_on_the_first_epoch_of_phase_two(phase, epoch_in_phase) -> None:
    state = {
        "phase": phase,
        "epoch_in_phase": epoch_in_phase,
        "next_epoch_in_phase": epoch_in_phase + 1,
    }
    assert is_phase2_first_epoch(state) is (phase == 2 and epoch_in_phase == 0)


def test_predicate_reads_the_zero_based_index_not_the_next_epoch_key() -> None:
    """``next_epoch_in_phase`` is never 0, so a predicate on it would never fire.

    The two keys are made to disagree here on purpose: a reading of the wrong one produces a
    deposit that silently does not exist, which no log line and no exit code reveals.
    """
    closes_first_epoch = {"phase": 2, "epoch_in_phase": 0, "next_epoch_in_phase": 1}
    closes_second_epoch = {"phase": 2, "epoch_in_phase": 1, "next_epoch_in_phase": 2}

    assert is_phase2_first_epoch(closes_first_epoch) is True
    assert is_phase2_first_epoch(closes_second_epoch) is False


# ------------------------------------------------------------------ #
#  The predicate against the trainer that feeds it                    #
# ------------------------------------------------------------------ #

def test_phase_two_hands_the_predicate_exactly_one_matching_call() -> None:
    payloads = run_phase_and_collect(2, n_epochs=3)
    assert len(payloads) == 3, "the epoch-end hook did not fire once per epoch"

    matches = [i for i, s in enumerate(payloads) if is_phase2_first_epoch(s)]
    assert matches == [0], (
        f"expected exactly the first epoch-end call to match, got indices {matches}"
    )
    assert [int(s["epoch_in_phase"]) for s in payloads] == [0, 1, 2]
    assert [int(s["next_epoch_in_phase"]) for s in payloads] == [1, 2, 3]


@pytest.mark.parametrize("phase", [1, 3])
def test_no_other_phase_ever_matches(phase) -> None:
    """A first epoch exists in every phase; only Phase 2's may be deposited."""
    payloads = run_phase_and_collect(phase, n_epochs=3)
    assert payloads, "the hook did not reach this phase at all"
    assert not any(is_phase2_first_epoch(s) for s in payloads)


def test_the_matching_call_lands_after_that_epoch_trained() -> None:
    """The deposit must be the epoch's result, not the state it started from.

    The hook sits after the early-stopping bookkeeping and before any restore, so the live
    model is the epoch's own output. A hook moved above ``train_epoch`` would deposit the
    phase-entry weights under a first-epoch name, and the file would look right.
    """
    cfg = make_small_config()
    trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)
    events: list[str] = []

    def fake_validate(self, loader, phase, **_kwargs):
        events.append("validate")
        return {"val_loss": 1.0, "mae": 0.5, "r2": 0.0}

    def fake_train_epoch(self, loader, optimizer, phase, epoch, compute_mono=False, **_kwargs):
        events.append(f"train_epoch:{epoch}")
        return 0.0, {"raw": {}, "weighted": {}, "weights": {}}

    trainer.validate = types.MethodType(fake_validate, trainer)
    trainer.train_epoch = types.MethodType(fake_train_epoch, trainer)
    trainer._clone_model_state = types.MethodType(
        lambda self: {"marker": torch.tensor([0.0])}, trainer
    )
    trainer.model.load_state_dict = lambda state_dict, strict=True: None

    def record(state: dict) -> None:
        if is_phase2_first_epoch(state):
            events.append("deposit")

    trainer.train_phase(2, None, None, n_epochs=3, on_epoch_end=record)

    assert "deposit" in events, "the deposit never fired"
    before = events[: events.index("deposit")]
    assert "train_epoch:0" in before, (
        "the deposit fired before the first epoch trained, so it would carry the weights "
        "the phase started from"
    )
    assert "validate" in before, (
        "the deposit fired before the epoch was validated, so the checkpoint could not be "
        "paired with a val number"
    )


# ------------------------------------------------------------------ #
#  The wiring                                                         #
# ------------------------------------------------------------------ #

def test_the_deposit_is_not_behind_the_probe_early_return() -> None:
    """``probe_every`` defaults to 0, and its guard returns.

    A deposit placed after that guard never runs on any arm of record, while every log line,
    exit code and metric stays exactly as it is. The consumer is a closure inside ``main`` and
    cannot be imported, so the order is asserted over the source of ``on_epoch_end`` itself.
    """
    src = (ROOT / "scripts/train.py").read_text(encoding="utf8")
    body = re.search(
        r"\n        def on_epoch_end\(state: dict\) -> None:\n(.*?)\n        resume_state",
        src,
        re.DOTALL,
    )
    assert body is not None, "could not locate the on_epoch_end closure in scripts/train.py"
    text = body.group(1)

    call = text.find("save_phase2_first_epoch_state(state)")
    guard = text.find("probe_every")
    assert call >= 0, "scripts/train.py no longer calls save_phase2_first_epoch_state"
    assert guard >= 0, "the probe_every guard moved; re-read this test before trusting it"
    assert call < guard, (
        "the first-epoch deposit sits after the probe_every guard, which returns under the "
        "default config, so the deposit would silently never happen"
    )
