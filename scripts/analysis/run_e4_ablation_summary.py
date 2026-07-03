#!/usr/bin/env python3
"""E4 aggregator: ablate the identifiability closers (tests the A-optimality story).

Given several exported prediction CSVs (one per ablation), report for each:
  * downstream ln x2 MAE (supervised rows);
  * crystal T_m MAE = mean |T_m_solver - T_m| on rows with a valid melting point;
  * GC-reference compensation (corr, delta_phi_mean) -- decomposition quality.

The reference run is the full grounded model; each ablation removes one closer
(external crystal pool, GC priors, stop-grad, ...). A closer "matters" if
removing it raises crystal T_m MAE and/or |delta_phi_mean| (worse decomposition).

    python scripts/analysis/run_e4_ablation_summary.py \
        --run full=results/e4/full/predictions.csv \
        --run no_external_crystal=results/e4/no_external_crystal/predictions.csv \
        --run no_gc_priors=results/e4/no_gc_priors/predictions.csv \
        --run no_stopgrad=results/e4/no_stopgrad/predictions.csv \
        --out-json results/e4/ablation_summary.json
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
from tgnn_solv.diagnostics.compensation import _bool_series, gc_reference_summary


def _mae(a: np.ndarray, b: np.ndarray) -> float | None:
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.abs(a[m] - b[m]).mean()) if m.any() else None


def _run_metrics(csv_path: str) -> dict[str, Any]:
    df = pd.read_csv(csv_path, low_memory=False)
    sup = df[_bool_series(df["has_solubility"])] if "has_solubility" in df else df
    lnx2_mae = _mae(
        pd.to_numeric(sup["ln_x2_pred"], errors="coerce").to_numpy(float),
        pd.to_numeric(sup["ln_x2_true"], errors="coerce").to_numpy(float),
    )

    crystal_tm_mae_K: float | None = None
    n_tm = 0
    if "T_m_solver" in df.columns and "T_m" in df.columns:
        valid_col = "has_valid_T_m" if "has_valid_T_m" in df.columns else "has_T_m"
        tm = df[_bool_series(df[valid_col])] if valid_col in df.columns else df
        n_tm = int(len(tm))
        crystal_tm_mae_K = _mae(
            pd.to_numeric(tm["T_m_solver"], errors="coerce").to_numpy(float),
            pd.to_numeric(tm["T_m"], errors="coerce").to_numpy(float),
        )

    comp = gc_reference_summary(df, n_bootstrap=1000)
    return {
        "n_supervised": int(len(sup)),
        "lnx2_mae": lnx2_mae,
        "n_with_Tm": n_tm,
        "crystal_Tm_mae_K": crystal_tm_mae_K,
        "compensation_corr": comp.get("delta_phi_delta_gamma_corr"),
        "compensation_delta_phi_mean": comp.get("delta_phi_mean"),
        "predictions_csv": str(Path(csv_path).resolve()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--run", action="append", required=True, metavar="LABEL=CSV",
                        help="Ablation run as label=predictions.csv (repeatable).")
    parser.add_argument("--reference-label", default="full",
                        help="Label treated as the grounded reference for deltas.")
    parser.add_argument("--out-json", required=True)
    args = parser.parse_args()

    runs: dict[str, dict[str, Any]] = {}
    for spec in args.run:
        if "=" not in spec:
            raise ValueError(f"--run expects LABEL=CSV, got: {spec!r}")
        label, path = spec.split("=", 1)
        runs[label.strip()] = _run_metrics(path.strip())

    ref = runs.get(args.reference_label)
    deltas: dict[str, Any] = {}
    if ref is not None:
        for label, m in runs.items():
            if label == args.reference_label:
                continue
            def _d(key: str) -> float | None:
                a, b = m.get(key), ref.get(key)
                return float(a - b) if a is not None and b is not None else None
            deltas[label] = {
                "lnx2_mae_vs_full": _d("lnx2_mae"),
                "crystal_Tm_mae_K_vs_full": _d("crystal_Tm_mae_K"),
                "abs_delta_phi_mean_vs_full": (
                    abs(m["compensation_delta_phi_mean"]) - abs(ref["compensation_delta_phi_mean"])
                    if m.get("compensation_delta_phi_mean") is not None
                    and ref.get("compensation_delta_phi_mean") is not None
                    else None
                ),
            }

    out = {
        "runs": runs,
        "deltas_vs_reference": deltas,
        "reference_label": args.reference_label,
        "interpretation": (
            "A closer matters if removing it makes crystal_Tm_mae_K_vs_full > 0 "
            "and/or abs_delta_phi_mean_vs_full > 0 (worse decomposition), ideally "
            "without improving lnx2 (compensation, not real fit)."
        ),
    }
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"runs": {k: {kk: vv for kk, vv in v.items() if kk != "predictions_csv"}
                               for k, v in runs.items()}, "deltas_vs_reference": deltas}, indent=2, sort_keys=True))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
