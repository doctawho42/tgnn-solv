import numpy as np
import pandas as pd

import sys
sys.path.insert(0, "src")

from tgnn_solv.data.builder import DataBuilder, filter_for_sle


def test_builder_gamma_merge_nearest_temperature() -> None:
    solubility_df = pd.DataFrame(
        {
            "solute_smiles": ["CCO", "CCO"],
            "solvent_smiles": ["CO", "CO"],
            "temperature": [300.0, 310.0],
            "ln_x2": [np.log(0.2), np.log(0.25)],
        }
    )
    gamma_df = pd.DataFrame(
        {
            "solute_smiles": ["CCO", "CCO"],
            "solvent_smiles": ["CO", "CO"],
            "ln_gamma_inf": [1.0, 2.0],
            "temperature": [297.0, 304.0],
        }
    )

    builder = DataBuilder()
    builder.add_gamma(gamma_df)
    built = builder.build(solubility_df)

    assert len(built) == 2

    row_300 = built[built["temperature"] == 300.0].iloc[0]
    row_310 = built[built["temperature"] == 310.0].iloc[0]

    assert row_300["has_gamma_inf"]
    assert not row_310["has_gamma_inf"]
    assert row_300["ln_gamma_inf"] == 1.0
    assert row_310["ln_gamma_inf"] == 0.0


def test_builder_gamma_merge_handles_nan_temperature() -> None:
    solubility_df = pd.DataFrame(
        {
            "solute_smiles": ["CCO", "CCO"],
            "solvent_smiles": ["CO", "CO"],
            "temperature": [300.0, np.nan],
            "ln_x2": [np.log(0.2), np.log(0.3)],
        }
    )
    gamma_df = pd.DataFrame(
        {
            "solute_smiles": ["CCO"],
            "solvent_smiles": ["CO"],
            "ln_gamma_inf": [1.0],
            "temperature": [299.0],
        }
    )

    builder = DataBuilder()
    builder.add_gamma(gamma_df)
    built = builder.build(solubility_df)

    row_300 = built[built["temperature"] == 300.0].iloc[0]
    row_nan = built[built["temperature"].isna()].iloc[0]

    assert row_300["has_gamma_inf"]
    assert not row_nan["has_gamma_inf"]


def test_builder_adds_gamma_aux_only_rows_without_pair_overlap() -> None:
    solubility_df = pd.DataFrame(
        {
            "solute_smiles": ["CCO"],
            "solvent_smiles": ["CO"],
            "temperature": [300.0],
            "ln_x2": [np.log(0.2)],
        }
    )
    gamma_df = pd.DataFrame(
        {
            "solute_smiles": ["c1ccccc1"],
            "solvent_smiles": ["O"],
            "ln_gamma_inf": [1.7],
            "temperature": [298.15],
        }
    )

    builder = DataBuilder()
    builder.add_gamma(gamma_df)
    built = builder.build(solubility_df)

    assert len(built) == 2

    gamma_row = built[built["has_gamma_inf"]].iloc[0]
    assert not gamma_row["has_solubility"]
    assert gamma_row["solute_smiles"] == "c1ccccc1"
    assert gamma_row["solvent_smiles"] == "O"
    assert gamma_row["temperature"] == 298.15
    assert gamma_row["ln_gamma_inf"] == 1.7
    assert gamma_row["source"] == "aux_only_gamma"


def test_filter_for_sle_excludes_invalid_and_miscible() -> None:
    df = pd.DataFrame(
        {
            "solute_smiles": [
                "CCO",
                "CCO",
                "CCO",
                "not_a_smiles",
                "[Na+].[Cl-]",
            ],
            "solvent_smiles": [
                "CO",
                "CO",
                "CCO",
                "CO",
                "CO",
            ],
            "ln_x2": [
                np.log(0.2),
                np.log(0.99),
                np.log(0.2),
                np.log(0.2),
                np.log(0.2),
            ],
        }
    )

    filtered = filter_for_sle(df, x2_max=0.98, min_atoms=2, max_atoms=200)

    assert len(filtered) == 1
    assert filtered.iloc[0]["solute_smiles"] == "CCO"
    assert filtered.iloc[0]["solvent_smiles"] == "CO"
