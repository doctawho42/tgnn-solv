from __future__ import annotations

import math

import pandas as pd
import pytest

from tgnn_solv.diagnostics.compensation import annotate_compensation_frame
from tgnn_solv.diagnostics.compensation import compensation_summary
from tgnn_solv.diagnostics.compensation import compute_phi


def test_compute_phi_matches_expected_ideal_term() -> None:
    phi = compute_phi(
        T=[300.0],
        Tm=[400.0],
        dH_fus=[10000.0],
    )[0]
    expected = 10000.0 / 8.31446261815324 * (1.0 / 300.0 - 1.0 / 400.0)
    assert math.isclose(phi, expected, rel_tol=1.0e-12, abs_tol=1.0e-12)


def test_compensation_annotation_and_summary() -> None:
    phi_true = compute_phi(
        T=[300.0, 300.0],
        Tm=[400.0, 400.0],
        dH_fus=[10000.0, 10000.0],
    )
    ln_x2_true = [-4.0, -5.0]
    ln_gamma_required = [-ln_x2_true[i] - phi_true[i] for i in range(2)]

    df = pd.DataFrame(
        {
            "ln_x2_true": ln_x2_true,
            "ln_x2_pred": [-4.2, -4.7],
            "T": [300.0, 300.0],
            "T_m": [400.0, 400.0],
            "dH_fus": [10000.0, 10000.0],
            "Phi": [phi_true[0] + 1.0, phi_true[1] - 1.0],
            "ln_gamma_2": [ln_gamma_required[0] - 0.5, ln_gamma_required[1] + 0.5],
            "solute_smiles": ["CCO", "CCO"],
            "solvent_smiles": ["O", "O"],
        }
    )

    annotated = annotate_compensation_frame(df, label="toy")
    assert annotated["pair_canonical"].nunique() == 1
    assert annotated["run_label"].unique().tolist() == ["toy"]
    assert annotated["delta_phi"].tolist() == pytest.approx([1.0, -1.0])
    assert annotated["delta_gamma"].tolist() == pytest.approx([-0.5, 0.5])
    assert annotated["compensation_sum"].tolist() == pytest.approx([0.5, -0.5])

    summary = compensation_summary(annotated)
    assert math.isclose(summary["delta_phi_delta_gamma_corr"], -1.0, abs_tol=1.0e-12)
    assert math.isclose(summary["mean_abs_compensation_sum"], 0.5, abs_tol=1.0e-12)
    assert math.isclose(summary["opposite_sign_fraction"], 1.0, abs_tol=1.0e-12)


def test_decomposition_identifiability_flags_correlation_as_artifact() -> None:
    """The GC-reference corr is an accounting/shared-reference artifact.

    A model that fits ln x2 but whose crystal/activity terms carry NO learned
    compensation must still show a strongly negative corr -- and a permutation
    null (terms shuffled independently) must reproduce most of it, so the
    ``corr_excess_over_null`` is small. The defensible signal is delta_phi.
    """
    import numpy as np

    from tgnn_solv.diagnostics.compensation import (
        decomposition_identifiability_summary,
    )

    solutes = [
        "CC(=O)Nc1ccc(O)cc1",   # paracetamol
        "c1ccccc1C(=O)O",        # benzoic acid
        "CC(=O)Oc1ccccc1C(=O)O", # aspirin
        "c1ccccc1O",             # phenol
        "c1ccc2ccccc2c1",        # naphthalene
        "Cc1ccccc1C(=O)O",       # o-toluic acid
    ]
    rng = np.random.default_rng(0)
    rows = []
    for smi in solutes:
        for _ in range(10):
            ln_x2_true = -4.0 + rng.normal(0.0, 1.5)
            phi = 2.0 + rng.normal(0.0, 1.0)  # crystal term, independent of phi_gc
            # good-but-imperfect fit: ln x2 ~ -phi - lng2  =>  lng2 = -ln_x2 - phi
            lng2 = -ln_x2_true - phi + rng.normal(0.0, 0.3)
            rows.append(
                {
                    "solute_smiles": smi,
                    "solvent_smiles": "O",
                    "T": 298.15 + rng.normal(0.0, 15.0),
                    "Phi": phi,
                    "ln_gamma_2": lng2,
                    "ln_x2_true": ln_x2_true,
                    "has_solubility": True,
                }
            )
    df = pd.DataFrame(rows)
    out = decomposition_identifiability_summary(df, n_perm=200, n_bootstrap=200)

    assert out["n_clusters"] >= 5
    assert out["n_rows"] >= 40
    # Raw correlation is strongly negative...
    assert out["corr_observed"] < -0.7
    # ...but the permutation null (terms shuffled, no learned coupling) is itself
    # negative (the shared phi_gc structural floor) AND strictly less extreme than
    # the observed, i.e. part of the observed correlation is pure artifact.
    assert out["corr_permutation_null_mean"] < 0.0
    assert out["corr_permutation_null_mean"] > out["corr_observed"]
    # Honest cluster CI for the headline metric is present and ordered.
    lo = out["delta_phi_mean_cluster_ci95_low"]
    hi = out["delta_phi_mean_cluster_ci95_high"]
    assert lo is not None and hi is not None and lo < hi
    assert out["delta_phi_std"] > 0.0
