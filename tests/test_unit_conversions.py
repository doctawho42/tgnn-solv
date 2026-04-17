from __future__ import annotations

import numpy as np
import pandas as pd

from tgnn_solv.benchmark_adapters import _safe_pred_logS
from tgnn_solv.external_benchmarking import (
    MAX_FINITE_LN_X2_FOR_LOGS,
    build_benchmark_artifacts,
    clip_ln_x2_for_logS,
    ln_x2_from_logS,
    logS_from_ln_x2,
)


def test_ln_x2_logS_roundtrip_for_supported_solvents() -> None:
    df = pd.DataFrame(
        {
            "solvent_smiles": ["O", "CCO", "CO"],
            "ln_x2": [-8.0, -2.5, -0.5],
        }
    )
    log_s = logS_from_ln_x2(df)
    roundtrip = ln_x2_from_logS(
        pd.DataFrame(
            {
                "solvent_smiles": df["solvent_smiles"],
                "logS": log_s,
            }
        ),
        logS_col="logS",
    )
    assert np.isfinite(log_s.to_numpy(dtype=float)).all()
    assert np.allclose(
        roundtrip.to_numpy(dtype=float),
        df["ln_x2"].to_numpy(dtype=float),
        atol=1e-10,
        rtol=0.0,
    )


def test_clip_ln_x2_for_logS_prevents_infinite_predictions() -> None:
    clipped = clip_ln_x2_for_logS(np.array([0.0, 0.2, -1.0], dtype=float))
    assert clipped[0] == MAX_FINITE_LN_X2_FOR_LOGS
    assert clipped[1] == MAX_FINITE_LN_X2_FOR_LOGS
    assert clipped[2] == -1.0

    predictions = pd.DataFrame(
        {
            "solvent_smiles": ["O", "CCO"],
            "ln_x2_pred": [0.0, -1.0],
        }
    )
    log_s = _safe_pred_logS(predictions, "ln_x2_pred")
    assert np.isfinite(log_s.to_numpy(dtype=float)).all()


def test_benchmark_artifacts_separate_ln_x2_and_finite_logS_subsets() -> None:
    eval_df = pd.DataFrame(
        {
            "row_index": [0, 1],
            "solute_smiles": ["CCO", "CCO"],
            "solvent_smiles": ["O", "CCO"],
            "temperature": [298.15, 298.15],
            "ln_x2": [0.0, -1.0],
            "has_solubility": [True, True],
        }
    )
    artifacts = build_benchmark_artifacts(
        model_name="dummy",
        eval_df=eval_df,
        pred_ln_x2=np.array([0.0, -1.0], dtype=float),
    )

    overall = artifacts.report["overall"]
    subsets = artifacts.report["evaluation_subsets"]
    coverage = subsets["policy"]["coverage"]

    assert overall["n_samples"] == 2
    assert subsets["ln_x2_all_supervised"]["n_samples"] == 2
    assert subsets["logS_finite_subset"]["n_samples"] == 1
    assert coverage["n_exact_ln_x2_eq_0_rows"] == 1
    assert coverage["n_finite_logS_eval_rows"] == 1
    assert coverage["n_logS_rows_excluded"] == 1
    assert artifacts.predictions["logS_eval_mask"].tolist() == [False, True]
