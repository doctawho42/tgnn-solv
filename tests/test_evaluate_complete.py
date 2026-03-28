"""Regression tests for the lightweight evaluation script."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import evaluate_complete  # noqa: E402


def test_solubility_supervision_mask_accepts_common_csv_values() -> None:
    df = pd.DataFrame(
        {
            "has_solubility": [True, False, "True", "false", 1, 0, "yes", "no"],
        }
    )

    mask = evaluate_complete.solubility_supervision_mask(df)

    assert mask.tolist() == [True, False, True, False, True, False, True, False]


def test_supervised_eval_view_excludes_aux_only_rows_from_metrics() -> None:
    df = pd.DataFrame(
        {
            "row_index": [10, 11, 12],
            "ln_x2": [-1.0, 0.0, -2.0],
            "has_solubility": [True, False, True],
            "temperature": [298.15, 298.15, 310.0],
            "solvent_smiles": ["O", "O", "CCO"],
        }
    )
    y_pred = np.array([-1.5, -5.0, -1.0], dtype=float)

    metric_df, metric_pred = evaluate_complete.supervised_eval_view(df, y_pred)
    metrics = evaluate_complete.compute_regression_metrics(
        metric_df["ln_x2"].to_numpy(),
        metric_pred,
    )

    assert metric_df["row_index"].tolist() == [10, 12]
    assert metric_pred.tolist() == [-1.5, -1.0]
    assert metrics["n_samples"] == 2
    assert metrics["mae"] == 0.75
