#!/usr/bin/env python3
"""Crystal-head T_m grounding vs measured melting points, PER UNIQUE SOLUTE.

Grades the model's predicted melting point (``T_m_solver``) against the measured
``T_m`` label in a predictions CSV. Reported per unique solute because
``T_m_solver`` is constant per molecule — per-row metrics pseudo-replicate (~40x
on the supervised slice) and overstate the sample size. Outputs MAE, bias, RMSE,
a SOLUTE-CLUSTER bootstrap CI, skill over a constant-mean baseline, and the Joback
GC reference MAE on the same solutes.

    python scripts/analysis/run_crystal_grounding.py \
        --predictions-csv results/.../test_predictions.csv \
        --out-json results/.../crystal_grounding.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401,E402
from tgnn_solv.diagnostics.compensation import _bool_series  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--predictions-csv", required=True)
    p.add_argument("--out-json", required=True)
    p.add_argument("--pred-col", default="T_m_solver")
    p.add_argument("--true-col", default="T_m")
    p.add_argument("--n-bootstrap", type=int, default=2000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-joback", action="store_true", help="skip the Joback GC comparison")
    args = p.parse_args()

    df = pd.read_csv(args.predictions_csv, low_memory=False)
    if "has_T_m" in df.columns:
        df = df[_bool_series(df["has_T_m"])]
    if "solute_smiles" not in df.columns:
        raise ValueError("predictions CSV needs a solute_smiles column")

    # One row per unique solute (T_m_solver is constant per molecule).
    g = (
        df.groupby("solute_smiles")
        .agg(pred=(args.pred_col, "first"), true=(args.true_col, "first"))
        .dropna()
    )
    g = g[pd.to_numeric(g["true"], errors="coerce") > 0.0]
    err = (
        pd.to_numeric(g["pred"], errors="coerce") - pd.to_numeric(g["true"], errors="coerce")
    ).to_numpy(dtype=float)
    err = err[np.isfinite(err)]
    n = int(err.size)
    out: dict[str, object] = {"n_solutes": n, "predictions_csv": str(Path(args.predictions_csv).resolve())}
    if n < 2:
        Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return

    true = pd.to_numeric(g["true"], errors="coerce").to_numpy(dtype=float)
    mae = float(np.abs(err).mean())
    base = float(np.abs(true - true.mean()).mean())
    rng = np.random.default_rng(args.seed)
    boot = np.array([np.abs(err[rng.integers(0, n, n)]).mean() for _ in range(int(args.n_bootstrap))])
    out.update(
        {
            "Tm_mae_K": mae,
            "Tm_mae_cluster_ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "Tm_bias_K": float(err.mean()),
            "Tm_rmse_K": float(np.sqrt((err**2).mean())),
            "baseline_mean_mae_K": base,
            "skill_over_mean": (float(1.0 - mae / base) if base else None),
        }
    )

    if not args.no_joback:
        from tgnn_solv.group_contribution import compute_gc_priors

        cache: dict[str, float | None] = {}

        def _jb(smi: str) -> float | None:
            if smi not in cache:
                cache[smi] = compute_gc_priors(str(smi)).get("T_m_gc")
            return cache[smi]

        jb = g.assign(jb=[_jb(s) for s in g.index]).dropna(subset=["jb"])
        if len(jb):
            jerr = pd.to_numeric(jb["jb"], errors="coerce") - pd.to_numeric(jb["true"], errors="coerce")
            out["joback_mae_K"] = float(jerr.abs().mean())
            out["joback_n_solutes"] = int(len(jb))

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
