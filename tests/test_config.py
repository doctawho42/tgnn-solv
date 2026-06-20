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
    assert cfg.weight_decay == 5.0e-4
    assert cfg.gc_prior_residual_freeze_epochs == 5


def test_descriptor_hidden_dim_alias_prefers_new_config_field() -> None:
    """The new descriptor augmentation alias should resolve without breaking old configs."""
    cfg = TGNNSolvConfig(
        descriptor_hidden_dim=64,
        descriptor_augmentation_hidden_dim=96,
    )

    assert cfg.resolved_descriptor_hidden_dim == 96


def test_config_yaml_round_trip_preserves_water_supervision_flag(tmp_path: Path) -> None:
    """Data-prep compatibility flags should survive YAML round-trip."""
    cfg = TGNNSolvConfig(
        include_water_solubility=False,
        explicit_h_small_molecules=True,
        explicit_h_max_heavy_atoms=3,
    )
    path = tmp_path / "config.yaml"

    cfg.to_yaml(str(path))
    loaded = TGNNSolvConfig.from_yaml(str(path))

    assert loaded.include_water_solubility is False
    assert loaded.explicit_h_small_molecules is True
    assert loaded.explicit_h_max_heavy_atoms == 3


def _load_train_module():
    import importlib.util
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "scripts"))  # train.py imports `_bootstrap`
    spec = importlib.util.spec_from_file_location(
        "train_for_test", repo_root / "scripts" / "train.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_set_override_coerces_by_declared_type_including_optional_fields() -> None:
    """`--set` must coerce by the DECLARED field type, not the current value.

    Optional[...] fields default to None, so the old value-based coercion stored
    them as raw strings (a latent type bug). This guards the type-aware fix.
    """
    train = _load_train_module()
    cfg = TGNNSolvConfig()
    train.apply_set_overrides(
        cfg,
        [
            "sigma_aux_phase1_weight=0.3",       # Optional[float], default None
            "early_stopping_patience=15",         # Optional[int], default None
            "use_temperature_in_encoder=false",   # bool
            "activity_model=cosmo_sac",           # str
            "hidden_dim=64",                      # int
        ],
    )

    assert cfg.sigma_aux_phase1_weight == 0.3
    assert isinstance(cfg.sigma_aux_phase1_weight, float)
    assert cfg.early_stopping_patience == 15
    assert isinstance(cfg.early_stopping_patience, int)
    assert cfg.use_temperature_in_encoder is False
    assert cfg.activity_model == "cosmo_sac"
    assert cfg.hidden_dim == 64 and isinstance(cfg.hidden_dim, int)

    with pytest.raises(ValueError):
        train.apply_set_overrides(cfg, ["nonexistent_field=1"])


def test_config_yaml_round_trip_preserves_branch_training_mode(tmp_path: Path) -> None:
    """Branch-aware training mode should survive config serialization."""
    cfg = TGNNSolvConfig(
        branch_training_mode="coordinate_descent",
        detach_crystal_from_encoder=True,
        detach_crystal_params_in_sle=True,
    )
    path = tmp_path / "config.yaml"

    cfg.to_yaml(str(path))
    loaded = TGNNSolvConfig.from_yaml(str(path))

    assert loaded.branch_training_mode == "coordinate_descent"
    assert loaded.detach_crystal_from_encoder is True
    assert loaded.detach_crystal_params_in_sle is True


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
        ("configs/paper_config_tuned_tgnn_descriptors.yaml", {
            "use_gc_priors_crystal": False,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": False,
        }),
        ("configs/paper_config_tuned_regularized.yaml", {
            "use_gc_priors_crystal": False,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": False,
        }),
        ("configs/paper_config_tuned_regularized_gc.yaml", {
            "use_gc_priors_crystal": True,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": False,
        }),
        ("configs/paper_config_tuned_regularized_descriptors.yaml", {
            "use_gc_priors_crystal": False,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": False,
        }),
        ("configs/paper_config_tuned_pretrained.yaml", {
            "use_gc_priors_crystal": False,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": False,
        }),
        ("configs/paper_config_tuned_pretrained_descriptors.yaml", {
            "use_gc_priors_crystal": False,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": False,
        }),
        ("configs/paper_config_tuned_gps.yaml", {
            "use_gc_priors_crystal": False,
            "bridge_loss_weight": 0.0,
            "use_walden_check": False,
            "use_oracle_injection": False,
        }),
    ],
)
def test_variant_configs_preserve_tuned_schedule(
    path: str,
    expected_flags: dict[str, float | bool],
) -> None:
    """Every maintained variant should keep the tuned dropout/LR schedule."""
    cfg = TGNNSolvConfig.from_yaml(path)

    expected_dropout = (
        0.15
        if path in {
            "configs/paper_config_tuned_tgnn_descriptors.yaml",
            "configs/paper_config_tuned_pretrained_descriptors.yaml",
            "configs/paper_config_tuned_regularized.yaml",
            "configs/paper_config_tuned_regularized_gc.yaml",
            "configs/paper_config_tuned_regularized_descriptors.yaml",
            "configs/paper_config_tuned_gps.yaml",
        }
        else 0.012430793241475136
    )
    assert cfg.dropout == expected_dropout
    assert cfg.lr_phase1 == 2.558463206591171e-4
    assert cfg.lr_phase2 == 8.528210688637237e-5
    assert cfg.lr_phase3 == 8.528210688637239e-6
    assert cfg.warmup_epochs == 0
    assert cfg.grad_clip == 2.0
    assert cfg.gc_prior_residual_freeze_epochs == 5
    if path in {
        "configs/paper_config_tuned_tgnn_descriptors.yaml",
        "configs/paper_config_tuned_pretrained_descriptors.yaml",
        "configs/paper_config_tuned_regularized_descriptors.yaml",
    }:
        assert cfg.use_descriptor_augmentation is True
        assert cfg.resolved_descriptor_hidden_dim == 128
    if path in {
        "configs/paper_config_tuned_regularized.yaml",
        "configs/paper_config_tuned_regularized_gc.yaml",
        "configs/paper_config_tuned_regularized_descriptors.yaml",
    }:
        assert cfg.weight_decay == pytest.approx(1.0e-4)
        assert cfg.early_stopping_patience == 15
        assert cfg.early_stopping_phase3_patience == 5
        assert cfg.phase2_loss_weights is not None
        assert cfg.phase2_loss_weights["tau_reg"] == pytest.approx(0.01)
    if path == "configs/paper_config_tuned_gps.yaml":
        assert cfg.encoder_type == "gps"
        assert cfg.gps_num_heads == 8
        assert cfg.gps_use_edge_attr is True
        assert cfg.gps_positional_encoding == "laplacian"
        assert cfg.gps_pe_dim == 16
    for key, expected in expected_flags.items():
        assert getattr(cfg, key) == expected
