#!/usr/bin/env python
"""The VT-2005-matched set's leave-one-pair-out count, at every estimator cell, from the deposit.

WHY THIS EXISTS.  Sec. 3.5.2 said the set's "aggregate margin of +0.05 collapses ... under 11 of the
60 single-pair deletions".  Three places in the corpus gave three different counts for that quantity
and none of them agreed:

  the article                       11 of 60 fail
  the Supporting Information        56/60 hold, so 4 fail, minimum -0.03
  results/b_insuff/leverage_robustness.json   60/60 hold, minimum +0.158

They disagree because the count depends on the estimator cell and none of the three said which cell
it was computed at, which is the hazard Sec. 2.5 fixes four analyst choices in advance to avoid.
Run over the grid, all three turn out to be right about different cells:

  8 bins, unbiased variance (THE HEADLINE CELL)   margin +0.045   4 of 60 fail, min -0.033
  5 bins, unbiased variance                       margin +0.097  11 of 60 fail
  8 bins, maximum-likelihood variance             margin +0.236   0 of 60 fail, min +0.151

So the article's sentence took its margin from the headline cell and its deletion count from the
five-bin one.  The Supporting Information's 56/60 is the headline cell and reproduces exactly here;
the artifact's 60/60 is the maximum-likelihood variant and reproduces exactly too, its 1.4723 /
0.6180 / +0.2362 being the deployed triple this repository's own notes record.

This script recomputes the whole grid from the deposited row-level table, so the next reader can see
which cell any count belongs to without trusting a sentence.

Usage
-----
    python scripts/analysis/check_vt2005_leverage_counts.py
    python scripts/analysis/check_vt2005_leverage_counts.py --expect-headline-fails 4
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

DEPOSIT = Path("paper/si_tables/vt2005_matched_set_60.csv")
#: Sec. 2.5's estimator cell: eight equal-count bins, unbiased (Bessel-corrected) within-bin
#: variance, row unit, residual-only convention.
HEADLINE_BINS, HEADLINE_DDOF, HEADLINE_COLUMN = 8, 1, "g_res"


def binsuff_upper(g: np.ndarray, m: np.ndarray, n_bins: int, ddof: int) -> float:
    """E[Var(m | bin(g))] over equal-count bins -- Lemma 1(c)'s bound."""
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


def margin(g: np.ndarray, m: np.ndarray, n_bins: int, ddof: int) -> float:
    """MSE - 2 B_insuff^up, the separation margin of Lemma 1."""
    return float(np.mean((m - g) ** 2)) - 2.0 * binsuff_upper(g, m, n_bins, ddof)


def leave_one_pair_out(g: np.ndarray, m: np.ndarray, n_bins: int, ddof: int) -> dict:
    vals = [margin(np.delete(g, i), np.delete(m, i), n_bins, ddof) for i in range(len(m))]
    return {"n": len(m),
            "n_failing": int(sum(v <= 0 for v in vals)),
            "n_holding": int(sum(v > 0 for v in vals)),
            "min_margin": round(float(min(vals)), 4)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--deposit", type=Path, default=DEPOSIT)
    p.add_argument("--expect-headline-fails", type=int, default=None,
                   help="fail unless the headline cell returns this many failing deletions")
    a = p.parse_args()

    d = pd.read_csv(a.deposit)
    m = d["m"].to_numpy(float)
    print(f"deposit {a.deposit}  n={len(m)}  MSE={np.mean((m - d['g_res'].to_numpy(float))**2):.4f}\n")
    print(f"{'conv':5s} {'bins':>5s} {'var':>4s} {'aggregate':>10s} {'fail/60':>8s} {'min margin':>11s}")
    for conv, col in (("res", "g_res"), ("full", "g_full")):
        g = d[col].to_numpy(float)
        for n_bins in range(3, 13):
            for ddof, name in ((0, "ML"), (1, "unb")):
                r = leave_one_pair_out(g, m, n_bins, ddof)
                star = ("  <- headline" if (conv, n_bins, ddof) == ("res", HEADLINE_BINS, HEADLINE_DDOF)
                        else "")
                print(f"{conv:5s} {n_bins:5d} {name:>4s} {margin(g, m, n_bins, ddof):+10.4f} "
                      f"{r['n_failing']:8d} {r['min_margin']:+11.4f}{star}")

    g = d[HEADLINE_COLUMN].to_numpy(float)
    head = leave_one_pair_out(g, m, HEADLINE_BINS, HEADLINE_DDOF)
    if a.expect_headline_fails is not None and head["n_failing"] != a.expect_headline_fails:
        raise SystemExit(f"headline cell returns {head['n_failing']} failing deletions, "
                         f"not the expected {a.expect_headline_fails}")
    print(f"\nheadline cell: margin {margin(g, m, HEADLINE_BINS, HEADLINE_DDOF):+.4f}, "
          f"{head['n_holding']}/{head['n']} hold, {head['n_failing']} fail, "
          f"minimum {head['min_margin']:+.4f}")


if __name__ == "__main__":
    main()
