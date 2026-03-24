import pandas as pd

import sys
sys.path.insert(0, "src")

from tgnn_solv.data.split import scaffold_split
from tgnn_solv.data.split_registry import (
    build_split_metadata,
    infer_split_mode_from_path,
    resolve_split_modes,
    split_filename,
    split_paths,
)


def test_solvent_split_no_overlap() -> None:
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


def test_split_registry_filenames_and_inference() -> None:
    assert split_filename("train", "solute_scaffold") == "train.csv"
    assert split_filename("train", "solute") == "train_solute.csv"
    assert split_filename("train", "solvent") == "train_solvent.csv"

    assert infer_split_mode_from_path("train.csv") == "solute_scaffold"
    assert infer_split_mode_from_path("test_solute.csv") == "solute"
    assert infer_split_mode_from_path("val_solvent.csv") == "solvent"


def test_split_registry_paths_and_metadata(tmp_path) -> None:
    paths = split_paths(tmp_path, "solvent")
    assert paths["train"].name == "train_solvent.csv"
    assert paths["val"].name == "val_solvent.csv"
    assert paths["test"].name == "test_solvent.csv"

    metadata = build_split_metadata(
        split_mode=None,
        train_data=paths["train"],
        val_data=paths["val"],
        test_data=paths["test"],
    )
    assert metadata["mode"] == "solvent"
    assert metadata["display_name"] == "Solvent holdout split"


def test_resolve_split_modes_and_aliases() -> None:
    assert resolve_split_modes("all") == ["solute_scaffold", "solute", "solvent"]
    assert resolve_split_modes("scaffold,solute,solvent_holdout") == [
        "solute_scaffold",
        "solute",
        "solvent",
    ]
