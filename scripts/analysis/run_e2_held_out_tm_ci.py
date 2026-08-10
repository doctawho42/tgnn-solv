#!/usr/bin/env python3
r"""Interval on the held-out-solute melting-point half of the E2 crystal-grounding arm.

WHY THIS EXISTS
---------------
The E2 comparison (``results/e2_with_crystal/e2_comparison.json``) reports the two arms'
held-out melting-point MAEs as two scalars, 45.003 K without the external crystal pool and
46.596 K with it. A difference of two MAEs over a common solute set is the mean of the paired
per-solute differences, so it admits a solute-clustered bootstrap -- but only if BOTH arms'
per-row predictions exist. Only the grounded arm's were exported, which is why the manuscript
carried this half as a bare point estimate while the pool-side half beside it carried a CI.

Both checkpoints are in the repository and their model cards differ in exactly one key,
``crystal_aux_steps_per_epoch`` (8 with the pool, 0 without), so the ungrounded arm's per-row
predictions are recoverable by re-scoring, not by retraining::

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/export_checkpoint_predictions.py \
        --checkpoint checkpoints/proxy_corrected_cpu/tgnn_mpnn_cpu_h64L3.pt \
        --data notebooks/data/processed/test.csv --model-type tgnn --device cpu \
        --output results/e2_with_crystal/test_predictions_without_crystal.csv

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_e2_held_out_tm_ci.py

THE GATE IS THE IDENTIFICATION.  Nothing here is trusted unless both arms reproduce all four
scalars of ``e2_comparison.json`` exactly (two melting-point MAEs, two ln x2 MAEs); a checkpoint
that does not is not the arm the comparison was run on, and the script stops.

THE CLUSTER IS THE SOLUTE.  One melting point per solute, so the solute is both the observation
and the resampling unit; the 8103 test rows are not 8103 observations of this quantity.

A NULL ARM IS RUN AND PRINTED: the same estimator on an arm compared with itself must return a
degenerate interval at zero.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
TOL = 1e-9


def per_solute_abs_error(csv_path: Path) -> pd.Series:
    """|predicted T_m - labelled T_m| per solute, over rows carrying a usable label."""
    df = pd.read_csv(csv_path, low_memory=False)
    labelled = df[df["has_valid_T_m"] == True]  # noqa: E712
    first = labelled.groupby("solute_smiles")[["T_m", "T_m_solver"]].first()
    return (first["T_m_solver"] - first["T_m"]).abs()


def lnx2_mae(csv_path: Path) -> float:
    df = pd.read_csv(csv_path, low_memory=False)
    sup = df[df["has_solubility"] == True]  # noqa: E712
    return float((sup["ln_x2_pred"] - sup["ln_x2_true"]).abs().mean())


def bootstrap(d: np.ndarray, n_boot: int, seed: int) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    n = len(d)
    draws = np.array([d[rng.integers(0, n, n)].mean() for _ in range(n_boot)])
    return (float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)),
            float((draws > 0).mean()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--with-csv", default="results/e2_with_crystal/test_predictions.csv")
    ap.add_argument("--without-csv",
                    default="results/e2_with_crystal/test_predictions_without_crystal.csv")
    ap.add_argument("--comparison-json", default="results/e2_with_crystal/e2_comparison.json")
    ap.add_argument("--out-json", default="results/e2_with_crystal/held_out_tm_ci.json")
    ap.add_argument("--n-boot", type=int, default=20000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    args = ap.parse_args()

    with_csv = REPO / args.with_csv
    without_csv = REPO / args.without_csv
    ref = json.loads((REPO / args.comparison_json).read_text())

    a = per_solute_abs_error(without_csv)   # ungrounded
    b = per_solute_abs_error(with_csv)      # grounded

    checks = {
        "without_Tm_mae": (float(a.mean()), ref["without"]["Tm_mae"]),
        "with_Tm_mae": (float(b.mean()), ref["with_aux"]["Tm_mae"]),
        "without_lnx2_mae": (lnx2_mae(without_csv), ref["without"]["lnx2_mae"]),
        "with_lnx2_mae": (lnx2_mae(with_csv), ref["with_aux"]["lnx2_mae"]),
    }
    print("identification gate (recomputed vs e2_comparison.json)")
    ok = True
    for name, (got, want) in checks.items():
        hit = abs(got - want) <= TOL
        ok &= hit
        print(f"  {'ok ' if hit else 'FAIL'} {name:18s} {got!r} vs {want!r}")
    if not ok:
        print("STOP: a prediction file does not belong to the arm e2_comparison.json scored.")
        return 1

    common = a.index.intersection(b.index)
    if len(common) != len(a) or len(common) != len(b):
        print(f"STOP: solute sets differ ({len(a)} vs {len(b)}, {len(common)} common).")
        return 1

    d = (b.loc[common] - a.loc[common]).to_numpy(float)   # grounded minus ungrounded, K
    point = float(d.mean())
    intervals = {}
    for s in args.seeds:
        lo, hi, p = bootstrap(d, args.n_boot, s)
        intervals[str(s)] = {"lo": lo, "hi": hi, "p_grounded_worse": p}
        print(f"  seed {s}: [{lo:+.3f}, {hi:+.3f}] K, P(grounded worse) = {p:.4f}")

    lo0, hi0 = intervals[str(args.seeds[0])]["lo"], intervals[str(args.seeds[0])]["hi"]
    nlo, nhi, _ = bootstrap(np.zeros(len(d)), 2000, args.seeds[0])

    print(f"\nn solutes                     {len(d)}")
    print(f"paired mean difference        {point:+.4f} K")
    print(f"95% interval (seed {args.seeds[0]})          [{lo0:+.3f}, {hi0:+.3f}] K")
    print(f"grounded arm worse on         {int((d > 0).sum())} solutes, better on {int((d < 0).sum())}")
    print(f"null arm (arm vs itself)      [{nlo:+.3g}, {nhi:+.3g}] K")
    print(f"per-solute middle half         [{np.percentile(d, 25):+.3f}, "
          f"{np.percentile(d, 75):+.3f}] K   median {np.percentile(d, 50):+.3f}")

    out = {
        "estimand": "paired per-solute |T_m error|, grounded minus ungrounded, held-out test solutes",
        "arms": {
            "grounded": "checkpoints/e2_with_crystal/tgnn_with_aux.pt",
            "ungrounded": "checkpoints/proxy_corrected_cpu/tgnn_mpnn_cpu_h64L3.pt",
            "config_difference": "crystal_aux_steps_per_epoch: 8 vs 0 (the only differing key)",
        },
        "n_solutes": int(len(d)),
        "mae_without_K": float(a.mean()),
        "mae_with_K": float(b.mean()),
        "paired_mean_difference_K": point,
        "ci95_by_seed": intervals,
        # THE SPREAD IS PRINTED IN S6.3 AND WAS NOT EMITTED HERE.  A paragraph whose whole
        # argument is that a number without its inputs on disk should not be printed must not
        # itself print two quantiles no generator emits; these are those quantiles.
        "per_solute_difference_quantiles_K": {
            q: float(np.percentile(d, v)) for q, v in
            (("p05", 5), ("p25", 25), ("median", 50), ("p75", 75), ("p95", 95))},
        "n_worse": int((d > 0).sum()),
        "n_better": int((d < 0).sum()),
        "null_arm_ci95_K": [nlo, nhi],
        "bootstrap": f"solute-clustered, {args.n_boot} draws, percentile interval",
    }
    out_path = REPO / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
