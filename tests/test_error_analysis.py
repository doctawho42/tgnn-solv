"""Regression tests for error-analysis row alignment."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "scripts")

from error_analysis import align_rows


def make_test_frame() -> pd.DataFrame:
    """Build a small deterministic test dataframe."""
    return pd.DataFrame(
        {
            "solute_smiles": ["CCO", "CCN", "CCC", "CCCl", "CCBr", "CCF"],
            "solvent_smiles": ["O", "O", "CCO", "CCO", "O", "CCN"],
            "temperature": [298.15, 303.15, 310.0, 320.0, 330.0, 340.0],
            "ln_x2": [-1.0, -2.0, -3.0, -4.0, np.nan, -6.0],
        }
    )


def test_align_rows_uses_explicit_row_indices() -> None:
    """Alignment should prefer exact row indices when provided."""
    df = make_test_frame()
    row_indices = np.asarray([3, 1], dtype=int)
    true_values = df.loc[row_indices, "ln_x2"].to_numpy(dtype=float)
    pred_values = np.asarray([-3.8, -1.7], dtype=float)

    aligned = align_rows(
        df,
        true_values=true_values,
        pred_values=pred_values,
        prediction_payload={},
        row_indices=row_indices,
    )

    assert aligned["row_index"].tolist() == [3, 1]
    assert aligned["true_ln_x2"].tolist() == [-4.0, -2.0]
    assert aligned["pred_ln_x2"].tolist() == [-3.8, -1.7]


def test_align_rows_reconstructs_sampled_subset_without_indices() -> None:
    """Legacy sampled evaluation JSON should align via deterministic sampling."""
    df = make_test_frame()
    sampled = df.reset_index().rename(columns={"index": "row_index"}).sample(
        4, random_state=42
    )
    finite_sampled = sampled[np.isfinite(sampled["ln_x2"].to_numpy(dtype=float))].reset_index(
        drop=True
    )
    true_values = finite_sampled["ln_x2"].to_numpy(dtype=float)
    pred_values = true_values + 0.1

    aligned = align_rows(
        df,
        true_values=true_values,
        pred_values=pred_values,
        prediction_payload={"metadata": {"test_samples": 4}},
        row_indices=None,
    )

    assert aligned["row_index"].tolist() == finite_sampled["row_index"].tolist()
    assert aligned["true_ln_x2"].tolist() == finite_sampled["ln_x2"].tolist()
    assert aligned["pred_ln_x2"].tolist() == pred_values.tolist()
