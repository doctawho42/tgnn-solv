"""Tests for ionic/contact-pair feature helpers."""

from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, "src")

from tgnn_solv.ionic_features import (  # noqa: E402
    IONIC_FEATURE_DIM,
    applicability_domain_flags,
    compute_ionic_features,
    flag_no_melting_point,
    ionic_feature_summary,
    solvent_dielectric,
)


DELPHINIDIN_CHLORIDE = "Oc1cc(O)c2cc(O)c(-c3cc(O)c(O)c(O)c3)[o+]c2c1.[Cl-]"


def test_delphinidin_chloride_is_curated_as_no_melting_point() -> None:
    """Curated anthocyanidin chloride should bypass the standard fusion branch."""
    assert flag_no_melting_point(DELPHINIDIN_CHLORIDE) == "exclude_from_crystal_branch"


def test_ionic_feature_vector_marks_explicit_low_eps_salt() -> None:
    """Delphinidin chloride in acetone should be classified as a contact-pair case."""
    features = compute_ionic_features(DELPHINIDIN_CHLORIDE, "CC(C)=O")
    summary = ionic_feature_summary(DELPHINIDIN_CHLORIDE, "CC(C)=O")

    assert features.shape == (IONIC_FEATURE_DIM,)
    assert features.dtype == np.float32
    assert summary.is_explicit_salt
    assert not summary.is_zwitterion
    assert summary.solvent_eps_r == solvent_dielectric("CC(C)=O")
    assert summary.solvent_eps_r < 30.0
    assert features[3] == 1.0


def test_applicability_flags_cover_no_melt_and_ion_pair_regime() -> None:
    """AD flags should make the delphinidin/acetone caveat visible at inference."""
    flags = applicability_domain_flags(
        DELPHINIDIN_CHLORIDE,
        "CC(C)=O",
        has_T_m=False,
        predicted_ln_x2=-16.0,
    )
    joined = "\n".join(flags)

    assert "decomposes_before_melting" in joined
    assert "ion_pair_regime" in joined
    assert "extreme_low_solubility" in joined
