import pandas as pd

import sys
sys.path.insert(0, "src")

from tgnn_solv.data.split import scaffold_split


def test_solvent_split_no_overlap():
    df = pd.DataFrame(
        {
            "solute_smiles": ["C", "CC", "CCC", "CCCC", "CCCCC", "CCCCCC"],
            "solvent_smiles": ["O", "O", "CCO", "CCO", "CO", "CO"],
            "temperature": [298.15] * 6,
            "ln_x2": [-1.0] * 6,
            "has_solubility": [True] * 6,
            "has_T_m": [False] * 6,
        }
    )

    train_df, val_df, test_df = scaffold_split(
        df, train_frac=0.5, val_frac=0.25, test_frac=0.25, seed=1, mode="solvent"
    )

    train_solvents = set(train_df["solvent_smiles"])
    val_solvents = set(val_df["solvent_smiles"])
    test_solvents = set(test_df["solvent_smiles"])

    assert train_solvents.isdisjoint(val_solvents)
    assert train_solvents.isdisjoint(test_solvents)
    assert val_solvents.isdisjoint(test_solvents)
