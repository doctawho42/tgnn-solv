import numpy as np
import pandas as pd
import importlib

m = importlib.import_module("scripts.analysis.run_e5_comparison")


def _frame(pairs, true, pred, lng, has=True):
    return pd.DataFrame({
        "solute_smiles": [p[0] for p in pairs],
        "solvent_smiles": [p[1] for p in pairs],
        "T": [p[2] for p in pairs],
        "ln_x2_true": true, "ln_x2_pred": pred,
        "ln_gamma2_pred": lng,
        "has_solubility": [has] * len(pairs),
    })


def test_intersection_mask_keeps_common_supervised_finite_rows():
    pairs = [("A", "W", 298.0), ("B", "W", 298.0), ("C", "W", 298.0)]
    a = _frame(pairs, [0, 1, 2], [0.1, 1.1, 2.1], [0.5, 0.5, 0.5])
    b = _frame(pairs, [0, 1, 2], [0.2, np.nan, 2.2], [0.4, 0.4, 0.4])  # row B non-finite in arm b
    keys = m.intersection_keys({"a": a, "b": b})
    assert set(keys) == {("A", "W", 298.0), ("C", "W", 298.0)}  # B dropped


def test_ring_bearing_detection():
    assert m.is_ring_bearing("c1ccccc1") is True
    assert m.is_ring_bearing("CCCCCC") is False


def test_rescue_and_constraint_criteria():
    # grounded R2 0.35 >= directgnn 0.30 -> rescue True; std(lng) in band -> keeps True
    per_arm = {
        "directgnn": {"r2": 0.30, "lngamma_std": float("nan")},
        "grounded_a": {"r2": 0.35, "lngamma_std": 1.5},
        "ungrounded": {"r2": -0.31, "lngamma_std": 1.4},
    }
    crit = m.evaluate_criteria(per_arm, direct_label="directgnn", lngamma_band=(1.0, 2.0))
    assert crit["rescue"]["grounded_a"] is True
    assert crit["rescue"]["ungrounded"] is False
    assert crit["keeps_constraint"]["grounded_a"] is True
