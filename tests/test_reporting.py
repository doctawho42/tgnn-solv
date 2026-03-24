"""Tests for shared report-schema normalization helpers."""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from tgnn_solv.reporting import build_report_payload, normalize_report_payload


def test_normalize_legacy_evaluation_payload() -> None:
    payload = {
        "test_data": "notebooks/data/processed/test.csv",
        "checkpoint": "checkpoints/model.pt",
        "config": {"hidden_dim": 256},
        "overall": {
            "n_samples": 3,
            "mae": 0.5,
            "rmse": 0.8,
            "r2": 0.9,
            "pearson_r": 0.95,
        },
        "by_temperature": {
            "T_298_to_323K": {"n_samples": 2, "mae": 0.4, "r2": 0.91},
        },
        "by_solubility": {
            "low_solubility": {"n_samples": 1, "mae": 0.6, "r2": 0.8},
        },
        "true_ln_x2": [-1.0, -2.0, -3.0],
        "pred_ln_x2": [-1.1, -1.9, -2.8],
    }

    normalized = normalize_report_payload(payload)

    assert normalized["report_type"] == "report"
    assert normalized["metadata"]["checkpoint"] == "checkpoints/model.pt"
    assert normalized["overall"]["n_samples"] == 3
    assert normalized["overall"]["n"] == 3
    assert normalized["by_temperature"]["T_298_to_323K"]["n"] == 2
    assert normalized["by_solubility"]["low_solubility"]["n_samples"] == 1
    assert normalized["predictions"]["true_ln_x2"] == [-1.0, -2.0, -3.0]
    assert normalized["predictions"]["pred_ln_x2"] == [-1.1, -1.9, -2.8]
    assert normalized["n_valid_predictions"] == 3


def test_normalize_legacy_benchmark_payload_derives_solvent_type() -> None:
    payload = {
        "model": "checkpoint.pt",
        "test_samples": 10,
        "timestamp": "2026-03-24T12:00:00",
        "overall": {"n": 10, "mae": 0.7, "rmse": 1.0, "r2": 0.82},
        "by_solvent": {
            "water": {"n": 4, "mae": 0.8, "r2": 0.79},
            "organic": {"n": 6, "mae": 0.6, "r2": 0.85},
            "CCO": {"n": 3, "mae": 0.5, "r2": 0.88},
        },
        "by_range": {
            "low": {"n": 5, "mae": 0.75, "r2": 0.8},
        },
        "by_temp": {
            "298.15K": {"n": 7, "mae": 0.65, "r2": 0.84},
        },
        "by_aux": {
            "with_T_m": {"n": 8, "mae": 0.66, "r2": 0.83},
        },
    }

    normalized = normalize_report_payload(payload)

    assert normalized["overall"]["n_samples"] == 10
    assert set(normalized["by_solvent_type"]) == {"water", "organic"}
    assert "CCO" in normalized["by_solvent"]
    assert normalized["by_solubility_range"]["low"]["n_samples"] == 5
    assert normalized["by_temperature"]["298.15K"]["n"] == 7
    assert normalized["by_aux_data"]["with_T_m"]["n_samples"] == 8


def test_build_report_payload_adds_canonical_and_compatibility_views() -> None:
    payload = build_report_payload(
        "evaluation",
        metadata={
            "checkpoint": "checkpoints/model.pt",
            "test_data": "test.csv",
            "test_samples": 2,
        },
        overall={"n_samples": 2, "mae": 0.25, "pearson_r": 0.99},
        stratified={
            "temperature": {"cold": {"n_samples": 1, "mae": 0.2}},
            "solvent_type": {"water": {"n_samples": 2, "mae": 0.25}},
        },
        predictions={
            "true_ln_x2": [-1.0, -2.0],
            "pred_ln_x2": [-1.1, -1.9],
        },
    )

    assert payload["schema_version"] == "1.0"
    assert payload["report_type"] == "evaluation"
    assert payload["metadata"]["checkpoint"] == "checkpoints/model.pt"
    assert payload["overall"]["pearson"] == 0.99
    assert payload["overall"]["pearson_r"] == 0.99
    assert payload["stratified"]["temperature"]["cold"]["n"] == 1
    assert payload["by_temperature"]["cold"]["n_samples"] == 1
    assert payload["by_solvent_type"]["water"]["mae"] == 0.25
    assert payload["true_ln_x2"] == [-1.0, -2.0]
    assert payload["n_valid_predictions"] == 2


def test_normalize_report_payload_exposes_split_alias() -> None:
    payload = build_report_payload(
        "evaluation",
        metadata={
            "checkpoint": "checkpoints/model.pt",
            "test_data": "notebooks/data/processed/test_solute.csv",
            "split": {
                "mode": "solute",
                "display_name": "Random solute split",
                "test_data": "notebooks/data/processed/test_solute.csv",
            },
        },
        overall={"n_samples": 1, "mae": 0.5},
    )

    assert payload["split"]["mode"] == "solute"
    assert payload["metadata"]["split"]["display_name"] == "Random solute split"
