#!/usr/bin/env python3
"""Estimator grid for the closure/insufficiency separation margin (paper Table S5).

The keystone margin MSE - 2*B_insuff^up depends on three analyst choices that the
manuscript previously reported only at one setting each:

  * the combinatorial convention of g            (full / res),
  * the number of equal-count bins of g(z*)      (3 ... 20),
  * the within-bin variance convention           (maximum likelihood ddof=0 / unbiased ddof=1).

This script evaluates every cell of that 2 x 18 x 2 grid on the deployed n=60 corner and
attaches, to each cell, the two-way (solute x solvent) pigeonhole cluster-bootstrap frequency
that the margin is positive with that cell's estimator held fixed.

NOTE. The headline P_boot quoted in the main text uses the resample-adaptive bin rule
max(3, n_resample // 10) of run_b_insuff_keystone_robustness.py, which conditions on less on
small resamples and is therefore more conservative than the fixed-bin values here; both are
reported so the two are not confused.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_b_insuff_estimator_grid.py
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
MATCHED = ROOT / "results" / "b_insuff" / "matched_pairs.csv"
OUT = ROOT / "results" / "b_insuff" / "estimator_grid.json"
N_BOOT = 3000


def lotv(g: np.ndarray, m: np.ndarray, n_bins: int, ddof: int) -> float:
    """E[Var(m | bin(g))] with equal-count bins; ddof=0 is the maximum-likelihood
    within-bin variance, ddof=1 the unbiased (Bessel-corrected) one."""
    q = np.quantile(g, np.linspace(0.0, 1.0, n_bins + 1))
    q[0] -= 1e-9
    q[-1] += 1e-9
    idx = np.digitize(g, q[1:-1])
    total = 0.0
    for b in range(n_bins):
        mm = m[idx == b]
        if len(mm) > ddof:
            total += (len(mm) / len(m)) * float(mm.var(ddof=ddof))
    return total


def two_way_margin_boot(g, m, solute, solvent, n_bins, ddof, n_boot=N_BOOT, seed=0):
    rng = np.random.default_rng(seed)
    su = np.array(sorted(set(solute)))
    sv = np.array(sorted(set(solvent)))
    row_su = np.array([int(np.where(su == s)[0][0]) for s in solute])
    row_sv = np.array([int(np.where(sv == s)[0][0]) for s in solvent])
    margins = []
    for _ in range(n_boot):
        cs = Counter(rng.integers(0, len(su), size=len(su)))
        cv = Counter(rng.integers(0, len(sv), size=len(sv)))
        mult = np.array([cs.get(row_su[r], 0) * cv.get(row_sv[r], 0) for r in range(len(m))])
        if mult.sum() < 12:
            continue
        idx = np.repeat(np.arange(len(m)), mult)
        mm, gg = m[idx], g[idx]
        margins.append(float(np.mean((mm - gg) ** 2)) - 2.0 * lotv(gg, mm, n_bins, ddof))
    margins = np.array(margins)
    return (float(np.mean(margins > 0)),
            float(np.percentile(margins, 5)), float(np.percentile(margins, 95)))


def adaptive_margin_boot(g, m, solute, solvent, ddof, n_boot=N_BOOT, seed=0):
    """The rule the deposited robustness artifact (and the main text) uses."""
    rng = np.random.default_rng(seed)
    su = np.array(sorted(set(solute)))
    sv = np.array(sorted(set(solvent)))
    row_su = np.array([int(np.where(su == s)[0][0]) for s in solute])
    row_sv = np.array([int(np.where(sv == s)[0][0]) for s in solvent])
    margins = []
    for _ in range(n_boot):
        cs = Counter(rng.integers(0, len(su), size=len(su)))
        cv = Counter(rng.integers(0, len(sv), size=len(sv)))
        mult = np.array([cs.get(row_su[r], 0) * cv.get(row_sv[r], 0) for r in range(len(m))])
        if mult.sum() < 12:
            continue
        idx = np.repeat(np.arange(len(m)), mult)
        mm, gg = m[idx], g[idx]
        nb = max(3, len(mm) // 10)
        margins.append(float(np.mean((mm - gg) ** 2)) - 2.0 * lotv(gg, mm, nb, ddof))
    return float(np.mean(np.array(margins) > 0))


def main() -> int:
    df = pd.read_csv(MATCHED)
    m = df["m"].to_numpy(float)
    solute = df["solute_key"].to_numpy()
    solvent = df["solvent_key"].to_numpy()
    cells, n_neg = [], 0
    for conv in ("full", "res"):
        g = df[f"g_{conv}"].to_numpy(float)
        mse = float(np.mean((m - g) ** 2))
        for nb in range(3, 21):
            for ddof, lab in ((0, "ML"), (1, "Bessel")):
                b = lotv(g, m, nb, ddof)
                P, lo, hi = two_way_margin_boot(g, m, solute, solvent, nb, ddof)
                margin = mse - 2 * b
                n_neg += int(margin <= 0)
                cells.append({"convention": conv, "n_bins": nb, "within_bin_variance": lab,
                              "mse": round(mse, 4), "b_insuff_up": round(b, 4),
                              "b_closure_lb": round(mse - b, 4), "margin": round(margin, 4),
                              "P_margin_positive_fixed_bins": round(P, 3),
                              "margin_ci90": [round(lo, 3), round(hi, 3)]})
    adaptive = {f"{conv}/{lab}": round(adaptive_margin_boot(
        df[f"g_{conv}"].to_numpy(float), m, solute, solvent, ddof), 3)
        for conv in ("full", "res") for ddof, lab in ((0, "ML"), (1, "Bessel"))}
    out = {
        "n": int(len(m)), "n_solutes": int(len(set(solute))), "n_solvents": int(len(set(solvent))),
        "n_cells": len(cells), "n_cells_margin_nonpositive": n_neg,
        "cells_margin_nonpositive": [c for c in cells if c["margin"] <= 0],
        "P_margin_positive_adaptive_bin_rule": adaptive,
        "grid": cells,
    }
    OUT.write_text(json.dumps(out, indent=2))
    print(f"{len(cells)} cells; margin non-positive in {n_neg} "
          f"({[(c['convention'], c['n_bins'], c['within_bin_variance']) for c in out['cells_margin_nonpositive']]})")
    print("adaptive-bin-rule P (matches the deposited robustness artifact):", adaptive)
    print(f"[saved] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
