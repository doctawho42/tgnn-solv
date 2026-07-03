#!/usr/bin/env python3
"""E2 headline comparison: crystal grounding WITHOUT vs WITH the external pool.

Tests the conditional-optimality claim (T3): grounding the crystal branch on a
large external single-component T_m / dH_fus pool should improve scaffold
extrapolation of the crystal term and the decomposition quality, *especially on
unseen scaffolds*, without hurting downstream ln x2.

Inputs are two prediction CSVs from
``scripts/analysis/export_checkpoint_predictions.py`` (model-type tgnn), one for
each run, plus the training CSV (to define seen vs unseen Bemis-Murcko scaffolds).

For each run it reports, overall and split by scaffold novelty:
  * downstream ln x2 MAE (supervised rows);
  * crystal T_m MAE = mean |T_m_solver - T_m| on rows with a valid melting point;
  * GC-reference compensation (corr, delta_phi_mean) -- decomposition quality.

    python scripts/analysis/run_e2_crystal_grounding_comparison.py \
        --without-csv results/e2/without/predictions.csv \
        --with-csv    results/e2/with/predictions.csv \
        --train-data  notebooks/data/processed/train.csv \
        --out-json    results/e2/comparison.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
from tgnn_solv.data.utils import get_scaffold
from tgnn_solv.diagnostics.compensation import _bool_series, gc_reference_summary


def _train_scaffolds(train_csv: str) -> set[str]:
    df = pd.read_csv(train_csv, usecols=lambda c: c == "solute_smiles", low_memory=False)
    out: set[str] = set()
    for smi in df["solute_smiles"].dropna().astype(str).unique():
        scaf = get_scaffold(smi)
        if scaf:
            out.add(scaf)
    return out


def _mae(a: np.ndarray, b: np.ndarray) -> float | None:
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.abs(a[m] - b[m]).mean()) if m.any() else None


def _run_metrics(df: pd.DataFrame, train_scaffolds: set[str]) -> dict[str, Any]:
    work = df.copy()
    # Seen vs unseen scaffold (the scaffold-extrapolation cut).
    scaf = work["solute_smiles"].astype(str).map(get_scaffold)
    work["_unseen_scaffold"] = ~scaf.isin(train_scaffolds)

    sup = work[_bool_series(work["has_solubility"])] if "has_solubility" in work else work

    def _lnx2_mae(frame: pd.DataFrame) -> dict[str, Any]:
        y = pd.to_numeric(frame["ln_x2_true"], errors="coerce").to_numpy(float)
        p = pd.to_numeric(frame["ln_x2_pred"], errors="coerce").to_numpy(float)
        return {"n": int(len(frame)), "mae": _mae(p, y)}

    lnx2 = {
        "overall": _lnx2_mae(sup),
        "seen_scaffold": _lnx2_mae(sup[~sup["_unseen_scaffold"]]),
        "unseen_scaffold": _lnx2_mae(sup[sup["_unseen_scaffold"]]),
    }

    # Crystal T_m MAE: predicted (T_m_solver) vs measured label (T_m), valid rows.
    crystal: dict[str, Any] = {"available": False}
    if "T_m_solver" in work.columns and "T_m" in work.columns:
        valid_col = "has_valid_T_m" if "has_valid_T_m" in work.columns else "has_T_m"
        tm = work[_bool_series(work[valid_col])] if valid_col in work.columns else work

        def _tm_mae(frame: pd.DataFrame) -> dict[str, Any]:
            pred = pd.to_numeric(frame["T_m_solver"], errors="coerce").to_numpy(float)
            meas = pd.to_numeric(frame["T_m"], errors="coerce").to_numpy(float)
            return {"n": int(len(frame)), "mae_K": _mae(pred, meas)}

        crystal = {
            "available": True,
            "overall": _tm_mae(tm),
            "seen_scaffold": _tm_mae(tm[~tm["_unseen_scaffold"]]),
            "unseen_scaffold": _tm_mae(tm[tm["_unseen_scaffold"]]),
        }

    compensation = {
        "overall": gc_reference_summary(sup, n_bootstrap=2000),
        "unseen_scaffold": gc_reference_summary(
            sup[sup["_unseen_scaffold"]], n_bootstrap=2000
        ),
    }
    return {"ln_x2": lnx2, "crystal_T_m": crystal, "compensation": compensation}


def _delta(with_v: float | None, without_v: float | None) -> float | None:
    if with_v is None or without_v is None:
        return None
    return float(with_v - without_v)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--without-csv", required=True)
    parser.add_argument("--with-csv", required=True)
    parser.add_argument("--train-data", default="notebooks/data/processed/train.csv")
    parser.add_argument("--out-json", required=True)
    args = parser.parse_args()

    train_scaffolds = _train_scaffolds(args.train_data)
    without = _run_metrics(pd.read_csv(args.without_csv, low_memory=False), train_scaffolds)
    with_ = _run_metrics(pd.read_csv(args.with_csv, low_memory=False), train_scaffolds)

    # Headline deltas (WITH - WITHOUT): negative T_m MAE delta on unseen scaffolds
    # and a less-negative compensation delta_phi_mean support T3.
    headline = {
        "n_train_scaffolds": len(train_scaffolds),
        "lnx2_mae_unseen_delta": _delta(
            with_["ln_x2"]["unseen_scaffold"]["mae"],
            without["ln_x2"]["unseen_scaffold"]["mae"],
        ),
        "crystal_Tm_mae_unseen_delta_K": (
            _delta(
                with_["crystal_T_m"].get("unseen_scaffold", {}).get("mae_K"),
                without["crystal_T_m"].get("unseen_scaffold", {}).get("mae_K"),
            )
            if with_["crystal_T_m"].get("available")
            else None
        ),
        "delta_phi_mean_unseen_with": with_["compensation"]["unseen_scaffold"].get(
            "delta_phi_mean"
        ),
        "delta_phi_mean_unseen_without": without["compensation"]["unseen_scaffold"].get(
            "delta_phi_mean"
        ),
    }

    out = {
        "headline": headline,
        "without_crystal_pool": without,
        "with_crystal_pool": with_,
        "interpretation": (
            "T3 is supported if crystal_Tm_mae_unseen_delta_K < 0 (better unseen-"
            "scaffold T_m), |delta_phi_mean_unseen_with| < |..._without| (cleaner "
            "decomposition), and lnx2_mae_unseen_delta <= ~0 (no downstream cost)."
        ),
    }
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(headline, indent=2, sort_keys=True))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
