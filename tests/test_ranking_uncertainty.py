"""Tests for Phase C: solvent-ranking and uncertainty-calibration evaluation."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))


def _load(modname: str, relpath: str):
    spec = importlib.util.spec_from_file_location(modname, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ndcg_perfect_and_reversed() -> None:
    rk = _load("rank_eval", "scripts/analysis/run_ranking_eval.py")
    true = np.array([1.0, 2.0, 3.0, 4.0])
    assert rk._ndcg(true, true, 3) > 0.999
    assert rk._ndcg(true, -true, 3) < rk._ndcg(true, true, 3)


def test_calibration_metrics_well_and_over_confident() -> None:
    cal = _load("uq_cal", "scripts/analysis/run_uncertainty_calibration.py")
    rng = np.random.default_rng(0)
    n = 20000
    mean = rng.normal(0, 2, n)
    std = np.full(n, 0.5)
    true = mean + rng.normal(0, 0.5, n)  # correctly calibrated
    m = cal.calibration_metrics(true, mean, std, noise_floor=0.16)
    # PICP at 90% should be close to 0.90 for a well-calibrated Gaussian
    assert abs(m["picp"]["90"] - 0.90) < 0.03
    assert m["regression_ece"] < 0.03
    # std 0.5 > floor 0.16 -> not overconfident
    assert m["overconfident_fraction_std_below_floor"] == 0.0

    # Overconfident: tiny std below the noise floor
    m2 = cal.calibration_metrics(true, mean, np.full(n, 0.05), noise_floor=0.16)
    assert m2["overconfident_fraction_std_below_floor"] == 1.0
    assert m2["picp"]["90"] < 0.5  # intervals far too narrow


def test_conformal_guarantees_coverage(tmp_path: Path) -> None:
    cf = _load("conf_cal", "scripts/analysis/run_conformal_calibration.py")
    # Heavy-tailed errors: model std would be miscalibrated, conformal must still cover.
    rng = np.random.default_rng(0)
    n = 8000
    mu = rng.normal(0, 3, n)
    true = mu + rng.standard_t(df=3, size=n) * 0.8  # fat tails
    df = pd.DataFrame({"ln_x2_true": true, "ln_x2_pred": mu, "has_solubility": True})
    csv = tmp_path / "p.csv"
    df.to_csv(csv, index=False)
    out = tmp_path / "conf.json"
    res = subprocess.run(
        [sys.executable, "scripts/analysis/run_conformal_calibration.py",
         "--predictions-csv", str(csv), "--out-json", str(out),
         "--levels", "0.8,0.9,0.95"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    import json
    d = json.loads(out.read_text())
    for lv in ("80", "90", "95"):
        cov = d["absolute"][lv]["empirical_coverage"]
        nominal = d["absolute"][lv]["nominal"]
        # Marginal coverage guarantee (allow small finite-sample slack).
        assert cov >= nominal - 0.03, (lv, cov)


def test_ranking_eval_cli_sign(tmp_path: Path) -> None:
    # 3 solutes x 5 solvents at one T; pred == true (perfect ranking).
    rows = []
    for s in range(3):
        for v in range(5):
            true = float(v) + 0.1 * s
            rows.append({"solute_smiles": f"C{'C'*s}O", "solvent_smiles": f"O{'C'*v}",
                         "T": 298.15, "ln_x2_true": true, "ln_x2_pred": true,
                         "has_solubility": True})
    csv = tmp_path / "pred.csv"
    pd.DataFrame(rows).to_csv(csv, index=False)
    out = tmp_path / "rank.json"
    res = subprocess.run(
        [sys.executable, "scripts/analysis/run_ranking_eval.py",
         "--predictions-csv", str(csv), "--out-json", str(out), "--min-solvents", "3"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    import json
    summ = json.loads(out.read_text())
    assert summ["spearman"]["mean"] > 0.99
    assert summ["best_solvent_top1_accuracy"]["mean"] == 1.0
