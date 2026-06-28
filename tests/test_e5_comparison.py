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


def test_empty_lock_raises():
    # Disjoint pair-keys across arms -> empty intersection.
    a = _frame([("A", "W", 298.0)], [0.0], [0.1], [0.5])
    b = _frame([("Z", "W", 298.0)], [0.0], [0.1], [0.5])
    assert m.intersection_keys({"a": a, "b": b}) == []
    # <2-row guard: R2 is NaN, not a false 1.0.
    assert np.isnan(m.r2(np.array([]), np.array([])))
    assert np.isnan(m.r2(np.array([1.0]), np.array([1.0])))


def test_duplicate_keys_do_not_inflate():
    pairs = [("A", "W", 298.0), ("A", "W", 298.0), ("B", "W", 298.0)]  # row A duplicated
    df = _frame(pairs, [0.0, 0.0, 1.0], [0.1, 0.1, 1.1], [0.5, 0.5, 0.5])
    keys = [("A", "W", 298.0), ("B", "W", 298.0)]
    assert m._metrics_on_keys(df, keys)["n"] == len(keys)  # 2, not inflated to 3


def test_stratification_counts():
    pairs = [("c1ccccc1", "W", 298.0), ("CCCCCC", "W", 298.0)]  # one ring, one acyclic
    df = _frame(pairs, [0.0, 1.0], [0.1, 1.1], [0.5, 0.5])
    keys = m.intersection_keys({"a": df})
    ring_keys = [k for k in keys if m.is_ring_bearing(k[0])]
    acyc_keys = [k for k in keys if not m.is_ring_bearing(k[0])]
    assert len(ring_keys) == 1
    assert len(acyc_keys) == 1
