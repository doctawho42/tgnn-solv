"""Unit tests for crystal-property group-contribution priors."""

from __future__ import annotations

import sys

sys.path.insert(0, "src")

from tgnn_solv.group_contribution import compute_gc_priors, fit_tm_gc_calibration


KNOWN_MELTING_POINTS = {
    "c1ccc2ccccc2c1": 353.4,  # naphthalene
    "CC(=O)Oc1ccccc1C(=O)O": 408.2,  # aspirin
    "CC(=O)NC1=CC=C(C=C1)O": 442.0,  # paracetamol
    "O=C(O)c1ccccc1": 395.0,  # benzoic acid
    "O=C(O)c1ccccc1O": 432.0,  # salicylic acid
}


def test_known_molecule_tm_estimates_are_reasonable() -> None:
    """The GC priors should land in a usable melting-point range."""
    for smiles, expected_tm in KNOWN_MELTING_POINTS.items():
        priors = compute_gc_priors(smiles)
        assert priors["T_m_gc"] is not None
        assert priors["dH_fus_gc"] is not None
        assert priors["dCp_fus_gc"] is not None
        assert abs(priors["T_m_gc"] - expected_tm) <= 60.0


def test_invalid_smiles_returns_none_priors() -> None:
    """Invalid SMILES should surface as missing priors instead of crashing."""
    priors = compute_gc_priors("not-a-smiles")
    assert priors == {
        "T_m_gc": None,
        "dH_fus_gc": None,
        "dCp_fus_gc": None,
    }


def test_partial_fragmentation_still_returns_usable_priors() -> None:
    """Incomplete fragmentation should not force the hard-coded fallback."""
    priors = compute_gc_priors("O=C1NS(=O)(=O)c2ccccc21")
    assert priors["T_m_gc"] is not None
    assert priors["dH_fus_gc"] is not None
    assert priors["dCp_fus_gc"] is not None
    assert abs(priors["T_m_gc"] - 400.0) > 1.0e-6


def test_tm_gc_calibration_fits_affine_mapping() -> None:
    """Train-set GC calibration should recover a simple affine relationship."""
    scale, bias = fit_tm_gc_calibration(
        raw_tm_gc=[100.0, 200.0, 300.0, 400.0],
        tm_true=[580.0, 600.0, 620.0, 640.0],
    )
    assert abs(scale - 0.2) < 1.0e-8
    assert abs(bias - 560.0) < 1.0e-8
