import importlib

import numpy as np
import pandas as pd

mod = importlib.import_module("scripts.data.build_sigma_profile_aux_stream")
from tgnn_solv.data.utils import scaffold_key


def _pool(n_bins=51):
    # mix of acyclic (alkanes/alcohols) and ring-bearing molecules
    smis = ["CCO", "CCCCCC", "CC(C)O", "CCCCCCCC", "c1ccccc1", "c1ccccc1O",
            "c1ccncc1", "C1CCCCC1", "CCN", "CCCCO", "c1ccc2ccccc2c1", "CC(=O)O"]
    rows = []
    shape = np.full(n_bins, 1.0 / n_bins)
    for i, s in enumerate(smis):
        r = {"solute_smiles": s, "solvent_smiles": s, "has_sigma_profile": True,
             "sigma_area": 40.0 + i}
        for b in range(n_bins):
            r[f"sigma_p_{b}"] = float(shape[b])
        rows.append(r)
    return pd.DataFrame(rows)


def test_split_is_scaffold_disjoint_and_preserves_area():
    df = _pool()
    train, val = mod.split_by_scaffold(df, val_fraction=0.3, seed=0)
    assert len(val) > 0 and len(train) > 0
    train_keys = {scaffold_key(s) for s in train["solute_smiles"]}
    val_keys = {scaffold_key(s) for s in val["solute_smiles"]}
    assert train_keys.isdisjoint(val_keys)  # no scaffold leak
    # area column survives the split untouched
    assert set(train["sigma_area"]).union(val["sigma_area"]) == set(df["sigma_area"])


def test_split_deterministic_under_seed():
    df = _pool()
    a = mod.split_by_scaffold(df, val_fraction=0.3, seed=7)[1]["solute_smiles"].tolist()
    b = mod.split_by_scaffold(df, val_fraction=0.3, seed=7)[1]["solute_smiles"].tolist()
    assert a == b


def test_val_fraction_zero_returns_empty_val():
    df = _pool()
    train, val = mod.split_by_scaffold(df, val_fraction=0.0, seed=0)
    assert len(val) == 0 and len(train) == len(df)
