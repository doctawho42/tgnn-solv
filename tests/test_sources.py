from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, "src")

from tgnn_solv.data import sources


def test_load_idac_reads_local_csv_with_aliases(tmp_path: Path, monkeypatch) -> None:
    idac_path = tmp_path / "idac.csv"
    pd.DataFrame(
        {
            "SMILES_Solute": ["CCO", "invalid"],
            "SMILES_Solvent": ["O", "O"],
            "gamma_inf": [1.23, 4.56],
            "Temperature_K": [300.0, 310.0],
        }
    ).to_csv(idac_path, index=False)

    monkeypatch.setattr(sources, "RAW_DIR", tmp_path)
    monkeypatch.delenv("TGNN_SOLV_IDAC_PATH", raising=False)

    df = sources.load_idac()

    assert len(df) == 1
    assert list(df.columns) == [
        "solute_smiles",
        "solvent_smiles",
        "ln_gamma_inf",
        "temperature",
    ]
    assert df.iloc[0]["solute_smiles"] == "CCO"
    assert df.iloc[0]["solvent_smiles"] == "O"
    assert df.iloc[0]["ln_gamma_inf"] == 1.23
    assert df.iloc[0]["temperature"] == 300.0


def test_load_idac_defaults_temperature_when_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    idac_path = tmp_path / "gamma_inf.csv"
    pd.DataFrame(
        {
            "solute": ["CCO"],
            "solvent": ["CO"],
            "ln_gamma_inf": [0.75],
        }
    ).to_csv(idac_path, index=False)

    monkeypatch.setattr(sources, "RAW_DIR", tmp_path)
    monkeypatch.delenv("TGNN_SOLV_IDAC_PATH", raising=False)

    df = sources.load_idac()

    assert len(df) == 1
    assert df.iloc[0]["temperature"] == 298.15
