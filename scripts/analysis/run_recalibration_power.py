#!/usr/bin/env python
"""How much of the substitution penalty a per-group affine recalibration absorbs OUT of sample,
as a function of how many rows the map is allowed to see.

THE PROBLEM WITH THE NUMBER THAT EXISTS
----------------------------------------
Fitted IN sample, a per-group affine map removes 91% of the MAE gap: +0.426 [+0.30,+0.55] becomes
+0.040 [-0.00,+0.08].  Refitted OUT of sample, leaving out the row it scores, it returns +0.321
[-0.615,+1.202] -- an interval that holds the whole gap and none of it alike.  The manuscript reads
that correctly, as no evidence either way.

But "no evidence" has a cause, and the cause is not that the answer is subtle.  The ranking groups
hold as few as three rows, and a two-parameter map fitted on the other two is EXACTLY DETERMINED:
it interpolates its fitting rows with zero residual and extrapolates to the held-out row with
nothing constraining it.  A handful of such groups is enough to blow the interval open.  Reporting
one number from a design that mixes them with well-determined groups reports the mixture.

WHAT THIS SCRIPT DOES
---------------------
It sweeps a floor on group size and reports the estimate WITH its interval at each floor, so the
reader sees where the design becomes able to answer and what it says there.  Three maps at every
floor, because they cost different numbers of parameters and a user can only deploy the cheap ones:

    none      the raw gap
    offset    one parameter per group (a level shift), the map a user could actually apply
    affine    two parameters (level and scale), the largest concession a miscalibration reading
              can ask for

THIS IS NOT A SEARCH FOR A FLOOR THAT GIVES AN ANSWER.  The whole curve prints, including the
floors where the interval stays open, and the floor that the deposited number uses (three, i.e. no
floor) prints first.  A curve that only becomes significant at its far end, on a tenth of the
groups, is a curve that says the design cannot answer -- and it prints that way.

Usage
-----
    python scripts/analysis/run_recalibration_power.py --root results/e5_sigma_grounding_leakfree
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ARMS = ("grounded_a", "oracle")
FLOORS = (3, 4, 5, 6, 8, 10, 12)


def fit(tt: np.ndarray, pp: np.ndarray) -> tuple[float, float]:
    """OLS of measured on predicted; slope 0 where the fitting rows have no spread."""
    vp = float(np.var(pp))
    b = float(np.cov(pp, tt, bias=True)[0, 1] / vp) if vp > 0 else 0.0
    return float(np.mean(tt) - b * np.mean(pp)), b


def loo_maes(t: np.ndarray, p: np.ndarray) -> dict[str, float]:
    """Per-group MAE under each map, every fit leaving out the row it scores."""
    n = len(t)
    e_none, e_off, e_aff = [], [], []
    for j in range(n):
        m = np.ones(n, bool)
        m[j] = False
        tt, pp = t[m], p[m]
        e_none.append(abs(t[j] - p[j]))
        e_off.append(abs(t[j] - (p[j] + float(np.mean(tt - pp)))))
        a, b = fit(tt, pp)
        e_aff.append(abs(t[j] - (a + b * p[j])))
    return {"none": float(np.mean(e_none)), "offset": float(np.mean(e_off)),
            "affine": float(np.mean(e_aff))}


def cluster_boot(d: np.ndarray, clusters: np.ndarray, draws: int, rng) -> tuple[float, float]:
    groups = [np.flatnonzero(clusters == c) for c in np.unique(clusters)]
    out = []
    for _ in range(draws):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        out.append(float(np.mean(d[idx])))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT / "results/e5_sigma_grounding_leakfree")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--draws", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    # rank_final reads its tree and its arms from the environment, by design -- it refuses to
    # substitute a seed or a tree for a missing arm.  Set them before the import.
    os.environ["RANK_BASE"] = str(a.root.relative_to(ROOT))
    os.environ["RANK_ARMS"] = ",".join(ARMS)
    os.environ["RANK_SEEDS"] = ",".join(str(s) for s in a.seeds)
    sys.path.insert(0, str(ROOT / "results/e5_sigma_grounding/ranking"))
    from rank_final import build_groups, load_arm  # noqa: E402

    per_group: list[dict] = []
    for seed in a.seeds:
        frames = {arm: load_arm(seed, arm) for arm in ARMS}
        groups, _ = build_groups(frames)
        for g in groups:
            row = {"seed": seed, "solute": g["solute"], "n": len(g["t"])}
            for arm in ARMS:
                for k, v in loo_maes(g["t"], g["preds"][arm]).items():
                    row[f"{arm}_{k}"] = v
            per_group.append(row)
    d = pd.DataFrame(per_group)
    print(f"{len(d)} group-seed cells over {d.solute.nunique()} solute clusters, "
          f"group sizes {d.n.min()}-{d.n.max()} (median {int(d.n.median())})\n")

    rng = np.random.default_rng(a.seed)
    print(f"{'floor':>5} {'cells':>6} {'solutes':>8} "
          f"{'raw gap':>22} {'offset':>22} {'affine':>22}")
    curve = []
    for floor in FLOORS:
        sub = d[d.n >= floor]
        if sub.solute.nunique() < 5:
            print(f"{floor:>5} {len(sub):>6}  too few solute clusters to resample")
            continue
        entry: dict = {"floor": floor, "n_cells": int(len(sub)),
                       "n_solutes": int(sub.solute.nunique())}
        cols = []
        for kind in ("none", "offset", "affine"):
            gap = (sub[f"oracle_{kind}"] - sub[f"grounded_a_{kind}"]).to_numpy(float)
            lo, hi = cluster_boot(gap, sub.solute.to_numpy(), a.draws, rng)
            entry[kind] = {"diff": round(float(gap.mean()), 4),
                           "ci95": [round(lo, 4), round(hi, 4)],
                           "width": round(hi - lo, 4),
                           "excludes_zero": bool(lo > 0 or hi < 0)}
            star = "*" if entry[kind]["excludes_zero"] else " "
            cols.append(f"{gap.mean():+.3f} [{lo:+.3f},{hi:+.3f}]{star}")
        curve.append(entry)
        print(f"{floor:>5} {len(sub):>6} {sub.solute.nunique():>8}  " + "  ".join(cols))

    print("\n* the interval excludes zero")
    base = curve[0]
    print(f"\nAt the deposited design (no floor): the affine map's out-of-sample gap is "
          f"{base['affine']['diff']:+.3f} with a width of {base['affine']['width']:.3f}.")
    informative = [c for c in curve if c["affine"]["excludes_zero"]]
    if informative:
        c = informative[0]
        print(f"The first floor at which it excludes zero is {c['floor']}, on "
              f"{c['n_cells']} of {base['n_cells']} cells "
              f"({100 * c['n_cells'] / base['n_cells']:.0f}%): "
              f"{c['affine']['diff']:+.3f} {c['affine']['ci95']}.")
    else:
        print("At NO floor does the affine map's out-of-sample gap exclude zero. The design "
              "cannot answer this question at any group size it contains, and the in-sample 91% "
              "stands as a bound on what such a map CAN absorb when fitted on the answer, not as "
              "an estimate of what it would absorb in use.")

    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps({"root": str(a.root), "seeds": a.seeds,
                                     "draws": a.draws, "curve": curve}, indent=2) + "\n")
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
