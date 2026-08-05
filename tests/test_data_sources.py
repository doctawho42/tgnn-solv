

def test_replicate_aggregation_takes_the_median_not_the_first() -> None:
    """A transposed replicate must not win by being first in the file."""
    import pandas as pd

    from tgnn_solv.data.sources import _aggregate_replicates

    df = pd.DataFrame(
        {
            "solute_smiles": ["c1ccccc1"] * 3,
            "solvent_smiles": ["O"] * 3,
            "temperature": [298.15] * 3,
            # The first row is four orders out, as a transposed column would be.
            "ln_x2": [-4.0, -13.7, -13.9],
        }
    )
    out = _aggregate_replicates(df)
    assert len(out) == 1
    assert abs(float(out["ln_x2"].iloc[0]) - (-13.7)) < 1e-9


def test_alcohol_series_screen_drops_an_inverted_interior_member() -> None:
    """Ethanol cannot sit far below both methanol and propanol for the same solute."""
    import pandas as pd

    from tgnn_solv.data.sources import _screen_alcohol_series

    df = pd.DataFrame(
        {
            "solute_smiles": ["c1ccccc1"] * 4,
            "solvent_smiles": ["CO", "CCO", "CCCO", "O"],
            "temperature": [298.15] * 4,
            "ln_x2": [-4.5, -13.7, -4.0, -12.0],
        }
    )
    kept, report = _screen_alcohol_series(df)
    assert set(kept["solvent_smiles"]) == {"CO", "CCCO", "O"}
    assert len(report) == 1
    assert report["solvent_smiles"].iloc[0] == "CCO"
    # Water is not a series member and must survive even though it is far below every alcohol.
    assert "O" in set(kept["solvent_smiles"])


def test_alcohol_series_screen_keeps_a_smooth_series() -> None:
    """An ordinary homologous trend must not be flagged."""
    import pandas as pd

    from tgnn_solv.data.sources import _screen_alcohol_series

    df = pd.DataFrame(
        {
            "solute_smiles": ["c1ccccc1"] * 4,
            "solvent_smiles": ["CO", "CCO", "CCCO", "CCCCO"],
            "temperature": [298.15] * 4,
            "ln_x2": [-4.5, -4.2, -3.9, -3.7],
        }
    )
    kept, report = _screen_alcohol_series(df)
    assert len(kept) == 4
    assert report.empty
