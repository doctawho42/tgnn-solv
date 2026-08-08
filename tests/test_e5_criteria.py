"""A criterion that cannot be evaluated must not read as one that failed.

`run_e5_comparison.evaluate_criteria` scores the two pre-registered criteria of the
sigma-grounding comparison. Both used to collapse to `False` when they could not be
evaluated at all: `rescue` whenever the comparator arm was absent from the run, and
`keeps_constraint` whenever an arm carried no finite `ln_gamma2_pred` spread. The
leak-free A1 gate runs `ungrounded` and `grounded_a` only, so every seed's
comparison.json reported `rescue: false` for arms that no comparator had been measured
against -- a negative that was never established, printed exactly like one that was.

These tests pin the distinction, in both directions: an unevaluable criterion is `None`
and says why, and an evaluable one still answers `True`/`False` as it always did.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analysis" / "run_e5_comparison.py"


@pytest.fixture(scope="module")
def evaluate_criteria():
    spec = importlib.util.spec_from_file_location("_e5_cmp", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_criteria


BAND = (1.0, 2.0)


def test_absent_comparator_is_not_a_failed_rescue(evaluate_criteria):
    """The shape the leak-free gate actually runs: no directgnn arm at all."""
    per_arm = {
        "ungrounded": {"r2": 0.41, "lngamma_std": 1.4},
        "grounded_a": {"r2": 0.55, "lngamma_std": 1.6},
    }
    out = evaluate_criteria(per_arm, direct_label="directgnn", lngamma_band=BAND)
    assert out["rescue"] == {"ungrounded": None, "grounded_a": None}
    # keeps_constraint is independent of the comparator and still answers.
    assert out["keeps_constraint"] == {"ungrounded": True, "grounded_a": True}
    for arm in per_arm:
        assert "no 'directgnn' arm" in out["criteria_not_evaluated"][f"rescue.{arm}"]


def test_present_comparator_still_answers_true_and_false(evaluate_criteria):
    per_arm = {
        "ungrounded": {"r2": 0.41, "lngamma_std": 1.4},
        "grounded_a": {"r2": 0.55, "lngamma_std": 1.6},
        "directgnn": {"r2": 0.50, "lngamma_std": 1.5},
    }
    out = evaluate_criteria(per_arm, direct_label="directgnn", lngamma_band=BAND)
    assert out["rescue"] == {"ungrounded": False, "grounded_a": True, "directgnn": True}
    assert out["matched_direct_r2"] == 0.50
    assert out["criteria_not_evaluated"] == {}


def test_non_finite_r2_on_either_side_is_not_evaluable(evaluate_criteria):
    per_arm = {
        "arm": {"r2": float("nan"), "lngamma_std": 1.5},
        "directgnn": {"r2": 0.5, "lngamma_std": 1.5},
    }
    out = evaluate_criteria(per_arm, direct_label="directgnn", lngamma_band=BAND)
    assert out["rescue"]["arm"] is None
    assert out["rescue"]["directgnn"] is True

    flipped = {
        "arm": {"r2": 0.5, "lngamma_std": 1.5},
        "directgnn": {"r2": float("nan"), "lngamma_std": 1.5},
    }
    out = evaluate_criteria(flipped, direct_label="directgnn", lngamma_band=BAND)
    assert out["rescue"] == {"arm": None, "directgnn": None}


def test_missing_lngamma_spread_is_not_a_violated_constraint(evaluate_criteria):
    """An arm with no ln_gamma2_pred column has not failed the band; it was not measured."""
    per_arm = {
        "in_band": {"r2": 0.5, "lngamma_std": 1.5},
        "out_of_band": {"r2": 0.5, "lngamma_std": 3.0},
        "unmeasured": {"r2": 0.5, "lngamma_std": float("nan")},
    }
    out = evaluate_criteria(per_arm, direct_label="in_band", lngamma_band=BAND)
    assert out["keeps_constraint"] == {
        "in_band": True,
        "out_of_band": False,
        "unmeasured": None,
    }
    why = out["criteria_not_evaluated"]["keeps_constraint.unmeasured"]
    assert "ln_gamma2_pred" in why


def test_unevaluable_serialises_as_json_null(evaluate_criteria):
    """The consumer is a JSON file, so None has to survive the round trip as null."""
    per_arm = {"ungrounded": {"r2": 0.41, "lngamma_std": 1.4}}
    out = evaluate_criteria(per_arm, direct_label="directgnn", lngamma_band=BAND)
    text = json.dumps(out)
    assert '"ungrounded": null' in text
    assert json.loads(text)["rescue"]["ungrounded"] is None
