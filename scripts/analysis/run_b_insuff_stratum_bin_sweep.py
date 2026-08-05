#!/usr/bin/env python3
r"""Bin-count sweep for the admissible strata of the map, at the grid the aggregates get.

WHY THIS EXISTS.  Tables S3 and S4 sweep the bin count for the two sets taken WHOLE, and that
sweep is the paper's own demonstration that the bin count is the analyst choice with the largest
leverage: on the broad IDAC set the deployed margin runs from +0.01 at four bins to +0.96 at
forty-eight, with the headline +0.51 at eight.  Every one of the 59 strata is then computed at
the single fixed eight-bin cell.  The one row set the paper states as a finding -- the
glycol-ether solvents -- is therefore reported at one cell of a grid the paper elsewhere shows to
move by an order of magnitude.  This script runs that grid for the strata the admissibility rule
passes, so the finding is quoted with its range over the choice rather than at a point.

WHAT IS SWEPT.  Exactly the grid of Table S4 (the broad-set aggregate):

    bin count       3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 40, 48
    within-bin var  maximum likelihood (ddof=0) and unbiased/Bessel (ddof=1)
    convention      full and deployed residual-only
    unit            row and pair

with, at every cell, the same two-way (solute x solvent) cluster-bootstrap frequency that the
margin is positive, the bin count held fixed across resamples.  Nothing here is selected: every
cell computed is printed.

WHICH STRATA.  The six cells the admissibility rule of
scripts/analysis/run_b_insuff_stratified_map.py passes on the broad set, which are three distinct
row sets -- the glycol-ether solvents (182 rows, at three granularities), the alkane solutes (129
rows) and the acceptor-only aprotics (57 rows) -- plus the whole set as the reference row, plus
the two remaining nine-class solvent strata that carry an estimate at n >= 40 without being
admissible, so that the sweep is not run only on the cells that pass.

OCCUPANCY.  The paper's stated occupancy rule -- the coarsest binning still leaving fewer than
eight rows per bin -- would ask for about 22 bins at n = 182 and about 16 at n = 129, against the
8 the fixed cell imposes (22.75 and 16.1 rows per bin).  The fixed cell is therefore COARSER than
the rule that fixed it, on both of the positive strata, and a coarser conditioning gives a weaker
LOTV bound.  The occupancy-rule bin count is computed and marked for each stratum so the reader
can see where the fixed cell sits in the sweep rather than being told.

READ THE SIGN, NOT THE VALUE.  The instrument is one-sided: a positive margin certifies
B_clos > 0, a non-positive one licenses nothing.  A sweep is therefore informative in one
direction only -- it can show that a positive finding is or is not a property of the bin count;
it cannot turn a non-positive cell into a reversal.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_stratum_bin_sweep.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from run_b_insuff_estimator_grid import lotv, two_way_margin_boot  # noqa: E402
from run_b_insuff_stratified_map import (  # noqa: E402
    N_BINS, MIN_BOUNDABLE, T_REF, pair_unit, prepare, source_deletion_curve,
)

OUT = ROOT / "results" / "b_insuff" / "stratum_bin_sweep.json"
OUT_CSV = ROOT / "results" / "b_insuff" / "stratum_bin_sweep.csv"

BIN_GRID = (3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 40, 48)
N_BOOT = 3000
MAX_ROWS_PER_BIN = 8       # the paper's occupancy rule: coarsest binning below this


def stable_seed(*parts: str) -> int:
    return int(hashlib.blake2b("\x1f".join(parts).encode(), digest_size=4).hexdigest(), 16) % (
        2 ** 31)


def occupancy_bins(n: int) -> int:
    """The paper's stated occupancy rule: the coarsest binning still leaving fewer than
    MAX_ROWS_PER_BIN rows per bin, i.e. the smallest k with n/k < MAX_ROWS_PER_BIN."""
    return int(n // MAX_ROWS_PER_BIN) + 1


def sweep_one(sub: pd.DataFrame, col: str, tag: str, boot: bool = True) -> list[dict]:
    """Every cell of the bin grid x within-bin variance, for one stratum, one unit, one
    convention.  Nothing is filtered out; a cell that cannot be formed is printed with nulls."""
    m = sub["m"].to_numpy(float)
    g = sub[col].to_numpy(float)
    solute = sub["solute_smiles"].to_numpy()
    solvent = sub["solvent_smiles"].to_numpy()
    n = len(m)
    mse = float(np.mean((m - g) ** 2))
    rows = []
    for nb in BIN_GRID:
        for ddof, lab in ((0, "ML"), (1, "Be")):
            rec = {"n_bins": nb, "within_bin_variance": lab, "n": n,
                   "rows_per_bin": round(n / nb, 2), "mse": round(mse, 4),
                   "b_insuff_up": None, "margin": None, "P_boot": None,
                   "margin_ci90_lo": None, "margin_ci90_hi": None,
                   "cell_defined": bool(n >= 2 * nb)}
            if n >= 2 * nb:
                b = lotv(g, m, nb, ddof)
                rec["b_insuff_up"] = round(b, 4)
                rec["margin"] = round(mse - 2 * b, 4)
                if boot and max(len(set(solute)), len(set(solvent))) >= 2:
                    try:
                        P, lo, hi = two_way_margin_boot(
                            g, m, solute, solvent, nb, ddof, n_boot=N_BOOT,
                            seed=stable_seed(tag, str(nb), lab))
                        if np.isfinite(P):
                            rec["P_boot"] = round(float(P), 3)
                            rec["margin_ci90_lo"] = round(float(lo), 3)
                            rec["margin_ci90_hi"] = round(float(hi), 3)
                    except Exception as exc:
                        rec["boot_error"] = type(exc).__name__
            rows.append(rec)
    return rows


def loso_at_cell(sub: pd.DataFrame, col: str, nb: int, ddof: int) -> dict:
    """Leave-one-source-publication-out at ONE cell of the sweep: does the sign survive the
    deletion test at that bin count, or only at the fixed eight?"""
    m = sub["m"].to_numpy(float)
    g = sub[col].to_numpy(float)
    src = sub["source_doi"].astype(str).to_numpy()
    if len(m) < 2 * nb:
        return {"testable": False, "why": f"cell undefined at n={len(m)}, {nb} bins"}
    base = float(np.mean((m - g) ** 2)) - 2 * lotv(g, m, nb, ddof)
    sgn = 1.0 if base > 0 else -1.0
    margins, undefined = [], []
    for s in sorted(set(src)):
        keep = src != s
        if keep.sum() < 2 * nb:
            undefined.append(s)
            continue
        mm, gg = m[keep], g[keep]
        margins.append((s, float(np.mean((mm - gg) ** 2)) - 2 * lotv(gg, mm, nb, ddof)))
    if not margins:
        return {"testable": False, "why": "every deletion leaves the cell undefined"}
    worst = min(margins, key=lambda kv: kv[1] * sgn)
    return {
        "testable": bool(len(undefined) == 0 and len(margins) >= 2),
        "n_sources": int(len(set(src))),
        "n_deletions_undefined": len(undefined),
        "base_margin": round(base, 4),
        "loso_margin_min": round(min(v for _, v in margins), 4),
        "loso_margin_max": round(max(v for _, v in margins), 4),
        "loso_worst_source": worst[0],
        "loso_worst_margin": round(worst[1], 4),
        "sign_survives_every_defined_deletion": bool(all(v * sgn > 0 for _, v in margins)),
    }


def main() -> int:
    broad, conv = prepare(ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv", "broad")
    units = {"row": broad.reset_index(drop=True),
             "pair": pair_unit(broad).reset_index(drop=True)}

    # The strata swept.  The three admissible row sets, the whole set as reference, and the two
    # further nine-class solvent strata that are boundable at the row unit without being
    # admissible -- so the sweep is not run only where it is expected to look good.
    strata = [
        ("whole_set", "all", lambda d: pd.Series(True, index=d.index)),
        ("solvent_class", "glycol_ether", lambda d: d["solvent_class"] == "glycol_ether"),
        ("solute_family", "alkane", lambda d: d["solute_family"] == "alkane"),
        ("solvent_class", "aprotic_acceptor", lambda d: d["solvent_class"] == "aprotic_acceptor"),
        ("solvent_class", "water", lambda d: d["solvent_class"] == "water"),
        ("solute_role", "organic_solute", lambda d: d["solute_role"] == "organic_solute"),
    ]
    admissible = {("solvent_class", "glycol_ether"), ("solute_family", "alkane"),
                  ("solvent_class", "aprotic_acceptor")}

    out: dict = {
        "what_this_is": (
            "the bin-count sweep of Tables S3/S4, run on the strata of the map rather than on "
            "the sets taken whole, so that the one stated finding is quoted with its range over "
            "the analyst choice with the largest leverage rather than at one cell"),
        "grid": {"n_bins": list(BIN_GRID),
                 "within_bin_variance": ["ML (ddof=0)", "Be (ddof=1, unbiased)"],
                 "convention": ["full", "res (deployed)"],
                 "unit": ["row", "pair"],
                 "bootstrap": f"two-way solute x solvent cluster, {N_BOOT} draws, bin count "
                              "held fixed across resamples, 90% percentile interval"},
        "fixed_cell_of_the_map": {"n_bins": N_BINS, "within_bin_variance": "Be",
                                  "unit": "row", "convention": "res"},
        "occupancy_rule": (f"the coarsest binning still leaving fewer than {MAX_ROWS_PER_BIN} "
                           "rows per bin -- the rule the paper states fixed the eight-bin cell "
                           "on the n=60 set; reported per stratum so the reader can see where "
                           "the fixed cell sits relative to it"),
        "one_sidedness": (
            "a positive margin certifies B_clos > 0; a non-positive margin is failure to "
            "separate and licenses nothing. The sweep can show that a positive finding is or is "
            "not a property of the bin count; it cannot convert a non-positive cell into a "
            "reversal."),
        "strata": {},
    }

    flat: list[dict] = []
    for axis, lab, sel in strata:
        key = f"{axis}::{lab}"
        block: dict = {"axis": axis, "stratum": lab,
                       "admissible_in_every_cell": bool((axis, lab) in admissible)}
        for uname, d in units.items():
            sub = d[sel(d).values].reset_index(drop=True)
            n = len(sub)
            block[f"{uname}::n"] = int(n)
            block[f"{uname}::n_sources"] = int(sub["source_doi"].nunique())
            block[f"{uname}::occupancy_rule_n_bins"] = occupancy_bins(n)
            block[f"{uname}::boundable_at_fixed_cell"] = bool(n >= MIN_BOUNDABLE)
            for cname, col in conv.items():
                tag = f"{key}|{uname}|{cname}"
                cells = sweep_one(sub, col, tag)
                block[f"{uname}::{cname}"] = cells
                for c in cells:
                    flat.append({"axis": axis, "stratum": lab, "unit": uname,
                                 "convention": cname, **c})
                # the sign summary over the sweep, which is what a reader needs
                ev = [c for c in cells if c["margin"] is not None]
                if ev:
                    block[f"{uname}::{cname}::summary"] = {
                        "n_cells_defined": len(ev),
                        "n_cells_positive": sum(1 for c in ev if c["margin"] > 0),
                        "margin_min": min(c["margin"] for c in ev),
                        "margin_max": max(c["margin"] for c in ev),
                        "margin_at_fixed_cell": next(
                            (c["margin"] for c in cells
                             if c["n_bins"] == N_BINS and c["within_bin_variance"] == "Be"), None),
                        "margin_at_occupancy_cell": next(
                            (c["margin"] for c in cells
                             if c["n_bins"] == min(
                                 BIN_GRID, key=lambda b: abs(b - occupancy_bins(n)))
                             and c["within_bin_variance"] == "Be"), None),
                        "nearest_grid_bin_to_occupancy_rule": min(
                            BIN_GRID, key=lambda b: abs(b - occupancy_bins(n))),
                        "cells_nonpositive": [
                            {"n_bins": c["n_bins"], "within_bin_variance":
                             c["within_bin_variance"], "margin": c["margin"]}
                            for c in ev if c["margin"] <= 0],
                    }
        # does the deletion test still pass away from the fixed bin count?
        if (axis, lab) in admissible:
            dl = {}
            for uname, d in units.items():
                sub = d[sel(d).values].reset_index(drop=True)
                for cname, col in conv.items():
                    for nb in BIN_GRID:
                        dl[f"{uname}/{cname}/{nb}"] = loso_at_cell(sub, col, nb, 1)
            block["leave_one_source_out_across_the_sweep"] = dl
            defined = [v for v in dl.values() if v.get("testable")]
            block["loso_summary_across_the_sweep"] = {
                "n_cells_where_the_deletion_test_runs": len(defined),
                "n_cells_where_the_sign_survives_every_deletion": sum(
                    1 for v in defined if v["sign_survives_every_defined_deletion"]),
                "worst_deletion_margin_over_the_sweep": (
                    min(v["loso_worst_margin"] for v in defined) if defined else None),
            }
        out["strata"][key] = block

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    pd.DataFrame(flat).to_csv(OUT_CSV, index=False)

    for key, block in out["strata"].items():
        print(f"\n===== {key}  (admissible: {block['admissible_in_every_cell']})")
        for uname in ("row", "pair"):
            print(f"  {uname}: n={block[f'{uname}::n']}, "
                  f"occupancy rule would use {block[f'{uname}::occupancy_rule_n_bins']} bins, "
                  f"fixed cell uses {N_BINS}")
            for cname in ("full", "res"):
                s = block.get(f"{uname}::{cname}::summary")
                if s:
                    def _f(v):
                        return "undefined" if v is None else f"{v:+.3f}"
                    print(f"    {cname:4s}: {s['n_cells_positive']}/{s['n_cells_defined']} cells "
                          f"positive, range [{s['margin_min']:+.3f}, {s['margin_max']:+.3f}], "
                          f"fixed cell {_f(s['margin_at_fixed_cell'])}, occupancy cell "
                          f"({s['nearest_grid_bin_to_occupancy_rule']} bins) "
                          f"{_f(s['margin_at_occupancy_cell'])}")
        if "loso_summary_across_the_sweep" in block:
            print("    loso:", json.dumps(block["loso_summary_across_the_sweep"]))
    print(f"\n[saved] {OUT}")
    print(f"[saved] {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
