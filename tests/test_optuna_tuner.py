"""Tests for Optuna tuning configuration and loader wiring."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.optuna_tuner import AVAILABLE_MODELS, OptunaTuner


def _make_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "solute_smiles": ["CCO"],
            "solvent_smiles": ["O"],
            "temperature_k": [298.15],
            "ln_x2": [-1.0],
            "has_solubility": [True],
        }
    )


def test_optuna_tuner_uses_base_config_and_overrides() -> None:
    base_cfg = TGNNSolvConfig(
        hidden_dim=384,
        pair_dim=768,
        batch_size=16,
        warmup_epochs=5,
    )
    datasets = tuple(SimpleNamespace(df=_make_df()) for _ in range(3))

    tuner = OptunaTuner(
        datasets=datasets,
        device=torch.device("cpu"),
        base_cfg=base_cfg,
        cfg_overrides={"warmup_epochs": 9},
    )

    assert tuner.base_cfg.hidden_dim == 384
    assert tuner.base_cfg.pair_dim == 768
    assert tuner.base_cfg.batch_size == 16
    assert tuner.base_cfg.warmup_epochs == 9


def test_optuna_tuner_can_represent_paper_like_learning_rate_schedule() -> None:
    base_cfg = TGNNSolvConfig()
    datasets = tuple(SimpleNamespace(df=_make_df()) for _ in range(3))
    tuner = OptunaTuner(
        datasets=datasets,
        device=torch.device("cpu"),
        base_cfg=base_cfg,
        tune_arch=False,
        fixed_batch_size=64,
    )

    class FakeTrial:
        def suggest_categorical(self, name, choices):
            mapping = {
                "nrtl_tau_mode": "ref_invT",
                "lr_phase1_mult": 3.0,
                "lr_phase3_mult": 0.01,
                "warmup_epochs": 5,
                "phase2_correction_unfreeze_epoch": 20,
                "grad_clip": 1.0,
            }
            return mapping[name]

        def suggest_float(self, name, low, high, log=False):
            if name == "lr_base":
                return 1.0e-4
            if name == "dropout":
                return 0.1
            raise KeyError(name)

    cfg, batch_size = tuner._suggest_tgnn_params(FakeTrial(), tune_arch=False)

    assert batch_size == 64
    assert cfg.lr_phase1 == pytest.approx(3.0e-4)
    assert cfg.lr_phase2 == pytest.approx(1.0e-4)
    assert cfg.lr_phase3 == pytest.approx(1.0e-6)
    assert cfg.warmup_epochs == 5
    assert cfg.phase2_correction_unfreeze_epoch == 20
    assert cfg.grad_clip == 1.0


def test_optuna_tuner_build_loaders_uses_canonical_make_loader_flags(
    monkeypatch,
) -> None:
    cfg = TGNNSolvConfig(
        batch_size=32,
        use_pair_temperature_batching=True,
        pair_temperature_min_group_size=3,
        pair_temperature_group_chunk_size=5,
        use_morgan_features=True,
        use_descriptor_augmentation=True,
        use_descriptor_priors=True,
        use_gc_priors_crystal=True,
    )
    datasets = tuple(SimpleNamespace(df=_make_df()) for _ in range(3))
    tuner = OptunaTuner(
        datasets=datasets,
        device=torch.device("cpu"),
        base_cfg=cfg,
    )
    calls: list[dict[str, object]] = []

    def fake_make_loader(df, **kwargs):
        calls.append({"df": df, **kwargs})
        return object()

    monkeypatch.setattr("tgnn_solv.optuna_tuner.make_loader", fake_make_loader)

    train_loader, val_loader, test_loader = tuner._build_loaders(
        cfg,
        batch_size=32,
        seed=17,
        include_test=True,
    )

    assert train_loader is not None
    assert val_loader is not None
    assert test_loader is not None
    assert len(calls) == 3

    train_call, val_call, test_call = calls
    assert train_call["shuffle"] is True
    assert val_call["shuffle"] is False
    assert test_call["shuffle"] is False
    assert train_call["use_pair_temperature_batching"] is True
    assert val_call["use_pair_temperature_batching"] is False
    assert test_call["use_pair_temperature_batching"] is False
    assert train_call["pair_temperature_min_group_size"] == 3
    assert train_call["pair_temperature_group_chunk_size"] == 5
    assert train_call["use_morgan_features"] is True
    assert train_call["use_descriptor_augmentation"] is True
    assert train_call["use_descriptor_priors"] is True
    assert train_call["use_gc_priors_crystal"] is True
    assert train_call["seed"] == 17


def test_optuna_tuner_direct_search_space_matches_proxy_request() -> None:
    base_cfg = TGNNSolvConfig(
        hidden_dim=384,
        n_gnn_layers=8,
        batch_size=16,
        direct_weight_decay=1.0e-5,
    )
    datasets = tuple(SimpleNamespace(df=_make_df()) for _ in range(3))
    tuner = OptunaTuner(
        datasets=datasets,
        device=torch.device("cpu"),
        base_cfg=base_cfg,
        tune_arch=True,
    )

    class FakeTrial:
        def suggest_categorical(self, name, choices):
            mapping = {
                "hidden_dim": 128,
                "n_gnn_layers": 4,
                "batch_size": 32,
            }
            assert mapping[name] in choices
            return mapping[name]

        def suggest_float(self, name, low, high, log=False):
            mapping = {
                "dropout": 0.2,
                "lr": 2.0e-4,
                "weight_decay": 3.0e-5,
                "grad_clip": 4.0,
            }
            value = mapping[name]
            assert low <= value <= high
            return value

    cfg, batch_size, lr = tuner._suggest_direct_params(FakeTrial(), tune_arch=True)

    assert cfg.hidden_dim == 128
    assert cfg.n_gnn_layers == 4
    assert cfg.dropout == pytest.approx(0.2)
    assert cfg.direct_weight_decay == pytest.approx(3.0e-5)
    assert cfg.grad_clip == pytest.approx(4.0)
    assert batch_size == 32
    assert cfg.batch_size == 32
    assert lr == pytest.approx(2.0e-4)


def test_optuna_tuner_supports_gps_and_descriptor_aliases() -> None:
    datasets = tuple(SimpleNamespace(df=_make_df()) for _ in range(3))
    tuner = OptunaTuner(
        datasets=datasets,
        device=torch.device("cpu"),
        base_cfg=TGNNSolvConfig(),
    )

    assert "tgnn_solv_gps" in AVAILABLE_MODELS
    assert "tgnn_solv_descriptors" in AVAILABLE_MODELS
    assert "direct_gnn_descriptors" in AVAILABLE_MODELS

    gps_cfg, model_cls, trainer_cls = tuner._resolve_model_spec(
        "tgnn_solv_gps",
        TGNNSolvConfig(),
    )
    descriptor_cfg, _, _ = tuner._resolve_model_spec(
        "tgnn_solv_descriptors",
        TGNNSolvConfig(),
    )

    assert gps_cfg.encoder_type == "gps"
    assert descriptor_cfg.use_descriptor_augmentation is True
    assert model_cls.__name__ == "TGNNSolv"
    assert trainer_cls.__name__ == "TGNNSolvTrainer"


def test_optuna_tuner_gps_and_descriptor_search_spaces_expose_new_knobs() -> None:
    datasets = tuple(SimpleNamespace(df=_make_df()) for _ in range(3))

    class FakeTrial:
        def suggest_categorical(self, name, choices):
            mapping = {
                "nrtl_tau_mode": "ref_invT",
                "lr_phase1_mult": 3.0,
                "lr_phase3_mult": 0.01,
                "warmup_epochs": 0,
                "phase2_correction_unfreeze_epoch": 20,
                "grad_clip": 1.0,
                "gps_num_heads": 8,
                "gps_positional_encoding": "rwse",
                "gps_pe_dim": 16,
                "descriptor_augmentation_hidden_dim": 256,
            }
            value = mapping[name]
            assert value in choices
            return value

        def suggest_float(self, name, low, high, log=False):
            mapping = {
                "dropout": 0.1,
                "lr_base": 1.0e-4,
                "lr": 2.0e-4,
                "weight_decay": 3.0e-5,
                "grad_clip": 4.0,
            }
            value = mapping[name]
            assert low <= value <= high
            return value

    gps_tuner = OptunaTuner(
        datasets=datasets,
        device=torch.device("cpu"),
        base_cfg=TGNNSolvConfig(encoder_type="gps"),
        tune_arch=False,
        fixed_batch_size=64,
    )
    gps_cfg, gps_batch_size = gps_tuner._suggest_tgnn_params(
        FakeTrial(),
        tune_arch=False,
    )
    assert gps_batch_size == 64
    assert gps_cfg.gps_num_heads == 8
    assert gps_cfg.gps_positional_encoding == "rwse"
    assert gps_cfg.gps_pe_dim == 16

    direct_desc_tuner = OptunaTuner(
        datasets=datasets,
        device=torch.device("cpu"),
        base_cfg=TGNNSolvConfig(use_descriptor_augmentation=True),
        tune_arch=False,
        fixed_batch_size=32,
    )
    direct_cfg, direct_batch_size, _ = direct_desc_tuner._suggest_direct_params(
        FakeTrial(),
        tune_arch=False,
    )
    assert direct_batch_size == 32
    assert direct_cfg.descriptor_augmentation_hidden_dim == 256
import pytest
