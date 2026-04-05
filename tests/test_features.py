"""Unit tests for molecular feature helpers."""

from __future__ import annotations

import sys

import numpy as np
import pytest

sys.path.insert(0, "src")

import tgnn_solv.features as features_module  # noqa: E402
from tgnn_solv.features import (  # noqa: E402
    DESCRIPTOR_RAW_ABS_CLIP,
    RDKIT_DESCRIPTOR_DIM,
    compute_descriptor_normalization_stats,
    compute_molecular_descriptors,
    validate_descriptor_normalization_stats,
)


def test_compute_molecular_descriptors_returns_finite_standard_vector() -> None:
    """The shared descriptor helper should expose the full finite RDKit vector."""
    descriptors = compute_molecular_descriptors("CCO")

    assert descriptors is not None
    assert descriptors.shape == (RDKIT_DESCRIPTOR_DIM,)
    assert np.isfinite(descriptors).all()


def test_compute_descriptor_normalization_stats_matches_descriptor_dimension() -> None:
    """Descriptor normalization statistics should align with the shared descriptor set."""
    mean, std = compute_descriptor_normalization_stats(["CCO", "O", "c1ccccc1"])

    assert mean.shape == (RDKIT_DESCRIPTOR_DIM,)
    assert std.shape == (RDKIT_DESCRIPTOR_DIM,)
    assert np.isfinite(mean).all()
    assert np.isfinite(std).all()
    assert (std > 0).all()


def test_compute_molecular_descriptors_clips_extreme_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Descriptor helper should bound pathological raw descriptor magnitudes."""
    original = features_module._RDKIT_DESCRIPTOR_CALCULATOR

    class FakeCalculator:
        def CalcDescriptors(self, mol):  # noqa: N802 - mirrors RDKit API
            return [1.0e12] + [0.0] * (RDKIT_DESCRIPTOR_DIM - 1)

    monkeypatch.setattr(
        features_module,
        "_RDKIT_DESCRIPTOR_CALCULATOR",
        FakeCalculator(),
    )
    try:
        descriptors = compute_molecular_descriptors("CCO")
    finally:
        monkeypatch.setattr(
            features_module,
            "_RDKIT_DESCRIPTOR_CALCULATOR",
            original,
        )

    assert descriptors is not None
    assert descriptors[0] == pytest.approx(DESCRIPTOR_RAW_ABS_CLIP)


def test_validate_descriptor_normalization_stats_accepts_clipped_pipeline() -> None:
    """Shared descriptor normalization stats should validate after clipping."""
    mean, std = compute_descriptor_normalization_stats(["CCO", "O", "c1ccccc1"])

    validated_mean, validated_std = validate_descriptor_normalization_stats(
        mean,
        std,
        descriptor_dim=RDKIT_DESCRIPTOR_DIM,
    )

    assert validated_mean.shape == (RDKIT_DESCRIPTOR_DIM,)
    assert validated_std.shape == (RDKIT_DESCRIPTOR_DIM,)


def test_validate_descriptor_normalization_stats_rejects_unclipped_scale() -> None:
    """Impossible descriptor stats should be rejected before model load/train."""
    mean = np.zeros(RDKIT_DESCRIPTOR_DIM, dtype=np.float32)
    std = np.ones(RDKIT_DESCRIPTOR_DIM, dtype=np.float32)
    std[0] = DESCRIPTOR_RAW_ABS_CLIP * 100.0

    with pytest.raises(ValueError, match="raw descriptor clip"):
        validate_descriptor_normalization_stats(mean, std)
