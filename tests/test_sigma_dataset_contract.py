import numpy as np
import pandas as pd
import pytest

from tgnn_solv.data.dataset import TGNNSolvDataset


def _sigma_row(n_bins: int, with_area: bool = True) -> pd.DataFrame:
    # Minimum columns required by TGNNSolvDataset.__getitem__ unconditionally.
    row = {
        "solute_smiles": "CCO",
        "solvent_smiles": "CCO",
        "temperature": 298.15,
        "has_solubility": False,
        "has_sigma_profile": True,
        # Hansen parameters (unconditionally read at line ~591)
        "hansen_d": 15.8,
        "hansen_p": 8.8,
        "hansen_h": 19.4,
        "has_hansen": False,
        # Crystal/fusion data (dH_fus unconditionally read at line ~684)
        "dH_fus": 0.0,
        # Activity coefficient (unconditionally read at line ~718)
        "ln_gamma_inf": 0.0,
        "has_gamma_inf": False,
    }
    if with_area:
        row["sigma_area"] = 88.0
    shape = np.full(n_bins, 1.0 / n_bins)
    for i in range(n_bins):
        row[f"sigma_p_{i}"] = float(shape[i])
    return pd.DataFrame([row])


def test_bin_count_mismatch_raises():
    ds = TGNNSolvDataset(_sigma_row(50), cache=False, expected_sigma_bins=51)
    with pytest.raises(ValueError, match="cosmo_sac_n_bins"):
        _ = ds[0]


def test_correct_bin_count_ok():
    ds = TGNNSolvDataset(_sigma_row(51), cache=False, expected_sigma_bins=51)
    sample = ds[0]
    assert sample[2]["sigma_profile_target"].shape[0] == 51


def test_missing_area_raises_when_profile_present():
    ds = TGNNSolvDataset(_sigma_row(51, with_area=False), cache=False, expected_sigma_bins=51)
    with pytest.raises(ValueError, match="sigma_area"):
        _ = ds[0]
