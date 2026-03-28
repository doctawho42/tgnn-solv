"""Tests for the full-budget experiment runner orchestration."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_full_budget_experiment as runner  # noqa: E402


def test_run_training_subprocess_resumes_from_existing_checkpoint(
    tmp_path,
    monkeypatch,
) -> None:
    checkpoint_path = tmp_path / "model.pt"
    checkpoint_path.write_text("placeholder", encoding="utf-8")
    train_script = tmp_path / "dummy_train.py"
    log_path = tmp_path / "train.log"
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    runner.run_training_subprocess(
        train_script=train_script,
        config_path=tmp_path / "config.yaml",
        train_data=tmp_path / "train.csv",
        val_data=tmp_path / "val.csv",
        test_data=tmp_path / "test.csv",
        checkpoint_path=checkpoint_path,
        log_dir=tmp_path / "logs",
        log_path=log_path,
        seed=42,
        device="cpu",
        force_retrain=False,
        checkpoint_every=7,
    )

    assert captured
    cmd = captured[0]
    assert "--resume" in cmd
    assert str(checkpoint_path) in cmd
    idx = cmd.index("--checkpoint-every")
    assert cmd[idx + 1] == "7"


def test_run_training_subprocess_starts_fresh_when_force_retrain(
    tmp_path,
    monkeypatch,
) -> None:
    checkpoint_path = tmp_path / "model.pt"
    checkpoint_path.write_text("placeholder", encoding="utf-8")
    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        captured.append(list(cmd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    runner.run_training_subprocess(
        train_script=tmp_path / "dummy_train.py",
        config_path=tmp_path / "config.yaml",
        train_data=tmp_path / "train.csv",
        val_data=tmp_path / "val.csv",
        test_data=tmp_path / "test.csv",
        checkpoint_path=checkpoint_path,
        log_dir=tmp_path / "logs",
        log_path=tmp_path / "train.log",
        seed=42,
        device="cpu",
        force_retrain=True,
        checkpoint_every=3,
    )

    assert captured
    cmd = captured[0]
    assert "--resume" not in cmd
