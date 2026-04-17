from pathlib import Path

import pandas as pd
import torch

import sys
sys.path.insert(0, "src")

from tgnn_solv.data import sources
from tgnn_solv.data.dataset import make_loader
from tgnn_solv.data.source_uncertainty import (
    attach_source_uncertainty,
    classify_source_method,
    compute_source_uncertainty_weights,
)


def test_classify_source_method_prefers_text_signals() -> None:
    result = classify_source_method(
        source="10.1021/example",
        title="HPLC determination of solubility in binary solvents",
        abstract="The solubility was quantified by high-performance liquid chromatography.",
    )
    assert result["method_guess"] == "hplc"
    assert result["heuristic_level"] == "text"
    assert result["confidence"] == "high"


def test_classify_source_method_uses_pattern_fallback() -> None:
    result = classify_source_method(
        source="10.1016/example",
        stats={
            "median_temps_per_pair": 6.0,
            "fraction_pairs_multi_temp": 0.85,
            "fraction_pairs_ge5_temps": 0.72,
            "fraction_uniform_step_pairs": 0.55,
            "fraction_rows_at_298_15": 0.05,
            "unique_solutes": 2,
            "unique_solvents": 5,
            "unique_pairs": 10,
        },
    )
    assert result["method_guess"] == "multi_temperature_primary"
    assert result["heuristic_level"] == "pattern"


def test_classify_source_method_ignores_nan_override_fields() -> None:
    result = classify_source_method(
        source="10.1016/example",
        stats={
            "median_temps_per_pair": 6.0,
            "fraction_pairs_multi_temp": 0.85,
            "fraction_pairs_ge5_temps": 0.72,
            "fraction_uniform_step_pairs": 0.55,
            "fraction_rows_at_298_15": 0.05,
            "unique_solutes": 2,
            "unique_solvents": 5,
            "unique_pairs": 10,
        },
        override_method=float("nan"),
        override_confidence=float("nan"),
        override_rationale=float("nan"),
    )
    assert result["method_guess"] == "multi_temperature_primary"
    assert result["heuristic_level"] == "pattern"


def test_classify_source_method_prefers_explicit_measurement_over_modeling() -> None:
    result = classify_source_method(
        source="10.1021/example",
        title="Solubility modeling and molecular simulation of compound X",
        abstract="The equilibrium solubility was determined by a static gravimetric method under atmospheric pressure.",
    )
    assert result["method_guess"] == "gravimetric_equilibrium"
    assert result["heuristic_level"] == "text"
    assert result["confidence"] == "high"


def test_classify_source_method_does_not_treat_acree_name_as_compilation() -> None:
    result = classify_source_method(
        source="10.1016/example",
        title="Solubility of compound X in neat solvents",
        abstract="The authors included William E. Acree, Jr., but this is a primary experimental paper.",
        stats={
            "median_temps_per_pair": 6.0,
            "fraction_pairs_multi_temp": 0.85,
            "fraction_pairs_ge5_temps": 0.72,
            "fraction_uniform_step_pairs": 0.55,
            "fraction_rows_at_298_15": 0.05,
            "unique_solutes": 2,
            "unique_solvents": 5,
            "unique_pairs": 10,
        },
    )
    assert result["method_guess"] == "multi_temperature_primary"
    assert result["heuristic_level"] == "pattern"


def test_load_bigsoldb_can_preserve_source_detail(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_path = tmp_path / "BigSolDBv2.1.csv"
    pd.DataFrame(
        {
            "SMILES_Solute": ["CCO"],
            "Temperature_K": [298.15],
            "Solvent": ["water"],
            "SMILES_Solvent": ["O"],
            "Solubility(mole_fraction)": [0.2],
            "Source": ["10.1021/example.doi"],
        }
    ).to_csv(raw_path, index=False)

    monkeypatch.setattr(sources, "BIGSOLDB_PATH", raw_path)
    monkeypatch.setattr(sources, "download_file", lambda *args, **kwargs: True)
    monkeypatch.setattr(sources, "verify_csv", lambda *args, **kwargs: True)

    df = sources.load_bigsoldb(preserve_source_detail=True)

    assert list(df.columns[:7]) == [
        "solute_smiles",
        "solvent_smiles",
        "temperature",
        "ln_x2",
        "source",
        "source_family",
        "source_raw",
    ]
    assert df.iloc[0]["source"] == "10.1021/example.doi"
    assert df.iloc[0]["source_family"] == "BigSolDBv2.1"
    assert df.iloc[0]["source_raw"] == "10.1021/example.doi"


def test_attach_source_uncertainty_merges_supervised_rows(tmp_path: Path) -> None:
    split_df = pd.DataFrame(
        {
            "solute_smiles": ["CCO", "CCO"],
            "solvent_smiles": ["O", "O"],
            "temperature": [298.15, 310.15],
            "ln_x2": [-2.0, 0.0],
            "has_solubility": [True, False],
        }
    )
    uncertainty_path = tmp_path / "uncertainty.csv"
    pd.DataFrame(
        {
            "solute_smiles": ["CCO"],
            "solvent_smiles": ["O"],
            "temperature": [298.15],
            "ln_x2": [-2.0],
            "source": ["10.1021/example"],
            "method_guess": ["gravimetric_equilibrium"],
            "sigma_ln_x2_guess": [0.20],
            "confidence": ["high"],
            "heuristic_level": ["manual_override"],
            "rationale": ["test"],
        }
    ).to_csv(uncertainty_path, index=False)

    merged = attach_source_uncertainty(
        split_df,
        uncertainty_csv=str(uncertainty_path),
        strict_for_supervised=True,
    )
    assert "source_sigma_ln_x2" in merged.columns
    assert "source_solubility_weight" in merged.columns
    assert merged.loc[0, "source_method_guess"] == "gravimetric_equilibrium"
    assert float(merged.loc[0, "source_sigma_ln_x2"]) == 0.20
    assert float(merged.loc[1, "source_sigma_ln_x2"]) == 0.75
    assert float(merged.loc[1, "source_solubility_weight"]) == 1.0


def test_compute_source_uncertainty_weights_is_bounded() -> None:
    weights = compute_source_uncertainty_weights(
        [0.20, 0.75, 1.00],
        min_sigma_ln_x2=0.20,
        min_weight=0.25,
        max_weight=4.0,
    )
    assert weights.shape == (3,)
    assert weights[0] >= weights[1] >= weights[2]
    assert weights.min() >= 0.25
    assert weights.max() <= 4.0


def test_make_loader_emits_source_uncertainty_targets(tmp_path: Path) -> None:
    split_df = pd.DataFrame(
        {
            "solute_smiles": ["CCO"],
            "solvent_smiles": ["O"],
            "temperature": [298.15],
            "ln_x2": [-2.0],
            "source": ["BigSolDBv2.1"],
            "has_solubility": [True],
            "T_m": [0.0],
            "has_T_m": [False],
            "dH_fus": [0.0],
            "has_dH_fus": [False],
            "hansen_d": [0.0],
            "hansen_p": [0.0],
            "hansen_h": [0.0],
            "has_hansen": [False],
            "ln_gamma_inf": [0.0],
            "has_gamma_inf": [False],
        }
    )
    uncertainty_path = tmp_path / "uncertainty.csv"
    pd.DataFrame(
        {
            "solute_smiles": ["CCO"],
            "solvent_smiles": ["O"],
            "temperature": [298.15],
            "ln_x2": [-2.0],
            "source": ["10.1021/example"],
            "method_guess": ["gravimetric_equilibrium"],
            "sigma_ln_x2_guess": [0.20],
            "confidence": ["high"],
            "heuristic_level": ["manual_override"],
            "rationale": ["test"],
        }
    ).to_csv(uncertainty_path, index=False)

    loader = make_loader(
        split_df,
        batch_size=1,
        shuffle=False,
        source_uncertainty_csv=str(uncertainty_path),
    )
    _, _, tgt = next(iter(loader))
    assert isinstance(tgt["source_sigma_ln_x2"], torch.Tensor)
    assert isinstance(tgt["source_solubility_weight"], torch.Tensor)
    assert torch.isfinite(tgt["source_sigma_ln_x2"]).all()
    assert torch.isfinite(tgt["source_solubility_weight"]).all()
