"""Tests for config serialization helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from tgnn_solv.config import TGNNSolvConfig


def test_config_yaml_round_trip_preserves_tuple_fields(tmp_path: Path) -> None:
    """Tuple-valued fields should round-trip through safe YAML serialization."""
    cfg = TGNNSolvConfig(
        use_gc_priors_crystal=True,
        gc_prior_dH_residual_factor=(0.25, 2.5),
        gc_prior_tm_scale=0.5,
        gc_prior_tm_bias=125.0,
        gc_prior_residual_freeze_epochs=7,
    )
    path = tmp_path / "config.yaml"

    cfg.to_yaml(str(path))
    loaded = TGNNSolvConfig.from_yaml(str(path))

    assert loaded.use_gc_priors_crystal is True
    assert loaded.gc_prior_dH_residual_factor == (0.25, 2.5)
    assert loaded.gc_prior_tm_scale == 0.5
    assert loaded.gc_prior_tm_bias == 125.0
    assert loaded.gc_prior_residual_freeze_epochs == 7


def test_config_yaml_round_trip_preserves_phase_loss_weights(tmp_path: Path) -> None:
    """Top-level phase-loss-weight dicts must survive to_yaml/from_yaml round-trip."""
    cfg = TGNNSolvConfig(
        phase1_loss_weights={"T_m": 1.0, "gamma_inf": 0.5},
        phase2_loss_weights={"sol": 1.0, "bridge": 0.01},
        phase3_loss_weights={"mono": 0.1, "res": 0.02},
    )
    path = tmp_path / "config.yaml"

    cfg.to_yaml(str(path))
    loaded = TGNNSolvConfig.from_yaml(str(path))

    assert loaded.phase1_loss_weights == {"T_m": 1.0, "gamma_inf": 0.5}
    assert loaded.phase2_loss_weights == {"sol": 1.0, "bridge": 0.01}
    assert loaded.phase3_loss_weights == {"mono": 0.1, "res": 0.02}


def test_tuned_config_loads_expected_overrides() -> None:
    """The tuned paper config should expose the searched schedule values."""
    cfg = TGNNSolvConfig.from_yaml("configs/paper_config_tuned.yaml")

    assert cfg.activity_model == "nrtl"
    assert cfg.dropout == 0.012430793241475136
    assert cfg.lr_phase2 == 8.528210688637237e-5
    assert cfg.warmup_epochs == 0
    assert cfg.grad_clip == 2.0
    assert cfg.gc_prior_residual_freeze_epochs == 5


@pytest.mark.parametrize(
    ("path", "expected_flags"),
    [
        ("configs/paper_config_tuned.yaml", {
            "use_gc_priors_crystal": False,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": False,
        }),
        ("configs/paper_config_gc_priors.yaml", {
            "use_gc_priors_crystal": True,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": False,
        }),
        ("configs/paper_config_oracle.yaml", {
            "use_gc_priors_crystal": False,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": True,
        }),
        ("configs/paper_config_no_bridge.yaml", {
            "use_gc_priors_crystal": False,
            "bridge_loss_weight": 0.0,
            "use_walden_check": True,
            "use_oracle_injection": False,
        }),
        ("configs/paper_config_combined.yaml", {
            "use_gc_priors_crystal": True,
            "bridge_loss_weight": 0.0,
            "use_walden_check": True,
            "use_oracle_injection": True,
        }),
    ],
)
def test_variant_configs_preserve_tuned_schedule(
    path: str,
    expected_flags: dict[str, float | bool],
) -> None:
    """Every maintained variant should keep the tuned dropout/LR schedule."""
    cfg = TGNNSolvConfig.from_yaml(path)

    assert cfg.dropout == 0.012430793241475136
    assert cfg.lr_phase1 == 2.558463206591171e-4
    assert cfg.lr_phase2 == 8.528210688637237e-5
    assert cfg.lr_phase3 == 8.528210688637239e-6
    assert cfg.warmup_epochs == 0
    assert cfg.grad_clip == 2.0
    assert cfg.gc_prior_residual_freeze_epochs == 5
    for key, expected in expected_flags.items():
        assert getattr(cfg, key) == expected
