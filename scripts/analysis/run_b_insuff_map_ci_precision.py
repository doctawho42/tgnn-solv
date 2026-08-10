#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Give every interval the stratified map prints a precision its draw count supports.

WHY THIS EXISTS
---------------
``run_b_insuff_glycol_ether_ci.py`` converged ONE of the map's intervals, after two referees
noticed that the glycol-ether margin was printed at four different values.  The cause was never
specific to that cell: the map draws ``N_BOOT = 3000`` bootstrap resamples per stratum and prints
the resulting endpoints to two decimals, and 3000 draws do not determine a second decimal.  The
map's table prints ELEVEN intervals and the four map tables print THIRTY-FIVE cells between them,
over TWENTY-FOUR distinct row sets and FORTY-EIGHT endpoints, all from that one apparatus.
Repairing the instance that was noticed and leaving the class is the defect this manuscript's own
apparatus exists to catch, so this script measures the class and repairs it cell by cell.

WHAT IS MEASURED, AND ON WHAT
-----------------------------
For each row set the map prints an interval for -- row unit, deployed residual-only convention,
the headline cell of eight equal-count bins of g(z*) with the Bessel within-bin variance -- the
script runs the map's OWN bootstrap at the map's OWN 3000 draws over ``MC_SEEDS = 200``
independent seeds (5000+s, the sequence ``run_b_insuff_glycol_ether_ci.py`` used, so the first 40
reproduce that deposit's Monte-Carlo block exactly; the reproduction is asserted, not assumed).
That gives each endpoint a Monte-Carlo standard deviation, which is the quantity the printed
second decimal has to be compared against.

The bootstrap is ``run_b_insuff_estimator_grid.two_way_margin_boot`` with its per-row ``Counter``
replaced by ``np.bincount`` -- same rng, same call order, same ``mult.sum() < 12`` discard.  The
substitution is verified BIT-IDENTICAL at run time against the imported original on the
glycol-ether stratum at its own map seed, and the run aborts if it is not.

THE RULE, DECLARED BEFORE ANY CELL WAS LOOKED AT
------------------------------------------------
The printing rule is the one the converged deposit already declares: an endpoint may be printed
to d decimals only if it stands at least ``BOUNDARY_SE_MIN = 4`` Monte-Carlo standard errors clear
of the nearest ROUNDING BOUNDARY at d decimals (``run_b_insuff_glycol_ether_ci.boundary_margin``,
the fixed version, which measures the distance to the boundary and not to the printable value).
An interval prints both endpoints at one precision, so a cell's precision is the coarser of what
its two endpoints support.

Reaching that clearance at d decimals costs ``3000 * (4 * sd_3000 / boundary_distance) ** 2``
draws, which is the whole of the decision.  Per row set, in this order:

  CONVERGE  if two decimals cost no more than ``--cap`` draws: run there and print two.
  COARSEN   else if ONE decimal costs no more than ``--cap``: run there and print one.  Coarsening
            stops at one decimal.  At zero decimals the map's cells stop being distinguishable
            from each other -- +0.79 and +1.38 both print +1 -- so a cell that one decimal cannot
            determine is STATED rather than coarsened into agreement with its neighbours.
  STATE     else: print two decimals with the endpoint's Monte-Carlo standard deviation beside
            it, so the reader can see that the last digit is not a fact about the data.  The
            deposit records how many draws that cell would need.

The target precision is chosen from the 3000-draw study BEFORE the convergence run and is then
VERIFIED on the run's own standard errors.  A cell may be demoted by that check and never
promoted by it: a run bought for one decimal that happens to land clear at two still prints one,
because the draw count was chosen against a noisy estimate and the choice is not re-opened after
seeing the answer.

DEGENERATE CELLS ARE NOT SUCCESSES
----------------------------------
Two row sets have only one solute or only one solvent AND so few clusters that the two-way
resample has a handful of distinct compositions: ``aldehyde`` (3 solutes x 1 solvent) and
``halogenated | water as solute`` (1 solute x 3 solvents).  Every seed returns the same endpoint,
the standard deviation is zero, and the 4-sd rule passes vacuously.  Their printed digits ARE
reproducible, but because the percentile is taken over about ten atoms and not because 3000 draws
sufficed, so they carry their own verdict and the count of distinct resampled margins that
produced them.  A cell that cannot be moved is not a cell that has been measured.

THE TEST FOR THAT HAD TO BE THE RANGE AND NOT THE STANDARD DEVIATION.  Written as ``sd == 0.0``
it caught ``halogenated | water as solute`` and MISSED ``aldehyde``, whose 200 seeds return the
same two endpoints to the last bit and whose sample standard deviation is nevertheless 7e-17
rather than 0 -- the mean of 200 identical floats is not exactly that float.  A cell missed there
is not merely mislabelled: it is planned as ``converge``, spent 180000 draws, and comes back
labelled ``converged`` at two decimals, which is the vacuous pass wearing the verdict of a
measurement.  The test is now ``max - min == 0`` on both endpoints, which is the property meant --
no seed moved it -- and it does not depend on how a spread of exactly zero is summarised.

THE GLYCOL-ETHER CELL IS READ, NOT RE-RUN
-----------------------------------------
It is already deposited at 1200 x 100000 draws with both endpoints 7.2 and 43.9 standard errors
clear (``glycol_ether_ci_converged.json``); this script quotes that deposit and re-measures only
its 3000-draw Monte-Carlo error, as the validation of this harness against that one.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_map_ci_precision.py --jobs 4

``--cap`` sets the per-cell convergence budget in draws, ``--jobs`` the worker count, and
``--plan-only`` stops after the 3000-draw study and prints what each cell would cost.  The
3000-draw study is cached in ``map_ci_precision_mc3000.csv`` and reused unless ``--remeasure``.

THE CAP IS A BUDGET, DECLARED BEFORE THE CELLS WERE RANKED.  ``DEFAULT_CAP`` is 1.2e6 draws per
row set -- 400 times the map's own count and one per cent of the glycol-ether convergence run --
and it was fixed before any cell's cost was known.  It is not re-opened after seeing which cells
fall on which side of it, because a budget chosen by the answer is not a budget; every cell's
cost at both precisions is deposited, so a reader can price a different one.

WHAT EACH NAME PRINTED IS KEPT.  ``stratified_map_table_pre_rowset_seed.csv`` is the map table as
the submission printed it, with the bootstrap still seeded from the stratum name.  Each cell's
``as_submitted`` block carries every printing of that row set, its distance to a rounding boundary
in units of this cell's Monte-Carlo spread, and the spread ACROSS its names -- which is one
quantity measured several times and was printed as several.  The repair makes those printings
identical, so without this snapshot the evidence for the defect would be erased by its own fix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from run_b_insuff_estimator_grid import lotv, two_way_margin_boot          # noqa: E402
from run_b_insuff_glycol_ether_ci import (BOUNDARY_SE_MIN, boundary_margin,  # noqa: E402
                                          half_up)
from run_b_insuff_stratified_map import (BROAD, DDOF, N_BINS, N_BOOT,      # noqa: E402
                                         prepare, strata_of)

#: What the submission printed: the map table as it stood when the bootstrap was still seeded from
#: the STRATUM NAME, snapshotted before the map was re-run against the repaired seed so that the
#: several values one row set printed under its several names remain readable after the repair
#: makes them identical.  This file is evidence, not an input to any estimate.
AS_SUBMITTED = ROOT / "results" / "b_insuff" / "stratified_map_table_pre_rowset_seed.csv"

OUT = ROOT / "results" / "b_insuff" / "map_ci_precision.json"
OUT_CSV = ROOT / "results" / "b_insuff" / "map_ci_precision_table.csv"
MC_CSV = ROOT / "results" / "b_insuff" / "map_ci_precision_mc3000.csv"
REP_CSV = ROOT / "results" / "b_insuff" / "map_ci_precision_replicates.csv"
CONVERGED_GLYCOL = ROOT / "results" / "b_insuff" / "glycol_ether_ci_converged.json"

UNIT, CONV_NAME, CONV_COL = "row", "res", "g_2002_res"

MC_SEEDS = 200          # independent seeds at the map's own draw count ...
MC_SEED0 = 5000         # ... 5000+s, the sequence the glycol-ether deposit used
MC_DRAWS = N_BOOT       # 3000, the map's own setting

CONV_REPS = 60          # replicates per convergence run; the endpoint is their mean
CONV_SEED0 = 700_000
CONV_DRAWS_MIN, CONV_DRAWS_MAX = 3_000, 100_000
DEFAULT_CAP = 1_200_000  # draws per row set

#: Two decimals is what the submission printed; one is the single step of coarsening allowed.
PRECISIONS = (2, 1)

#: The map's own axis order.  A row set carrying several names is seeded, and quoted, under the
#: first name it takes in this order -- fixed by position, never by the value of an endpoint.
AXIS_ORDER = ["solvent_class", "solvent_class_coarse", "solvent_family_fine",
              "solute_role", "solute_family", "solvent_class_x_solute_role", "whole_set"]

#: Where each row set's interval is printed.  Table assignment follows make_map_table_tex.SI_GROUPS.
TABLE_OF_AXIS = {
    "solvent_class": "tab:map-full", "solvent_class_coarse": "tab:map-full",
    "solvent_family_fine": "tab:map-fine",
    "solute_role": "tab:map-solute", "solute_family": "tab:map-solute",
    "solvent_class_x_solute_role": "tab:map-xtab", "whole_set": "tab:map-xtab",
}


# ------------------------------------------------------------------------------------------- #
# the estimator: the map's own bootstrap, with the per-row Counter replaced by np.bincount
# ------------------------------------------------------------------------------------------- #
def two_way_boot(g, m, solute, solvent, n_boot: int, seed: int):
    """(P, lo, hi, n_used, n_distinct_margins) -- bit-identical to two_way_margin_boot."""
    rng = np.random.default_rng(seed)
    _, ui = np.unique(solute, return_inverse=True)
    _, vi = np.unique(solvent, return_inverse=True)
    nu, nv, n = int(ui.max()) + 1, int(vi.max()) + 1, len(m)
    arange = np.arange(n)
    out = np.empty(n_boot)
    k = 0
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, nu, size=nu), minlength=nu)
        cv = np.bincount(rng.integers(0, nv, size=nv), minlength=nv)
        mult = cs[ui] * cv[vi]
        if mult.sum() < 12:
            continue
        idx = np.repeat(arange, mult)
        gg, mm = g[idx], m[idx]
        out[k] = float(np.mean((mm - gg) ** 2)) - 2.0 * lotv(gg, mm, N_BINS, DDOF)
        k += 1
    out = out[:k]
    return (float(np.mean(out > 0)), float(np.percentile(out, 5)),
            float(np.percentile(out, 95)), k, int(len(np.unique(out))))


def required_draws(sd: float, dist: float) -> float:
    """Draws needed for a mean endpoint to stand BOUNDARY_SE_MIN standard errors off a boundary.

    The standard error of the mean of replicates totalling T draws is sd_3000 * sqrt(3000 / T),
    so T = 3000 * (BOUNDARY_SE_MIN * sd_3000 / dist) ** 2.  It does not depend on how T is split
    into replicates, only on the total.
    """
    if sd <= 0:
        return 0.0
    if dist <= 0:
        return float("inf")
    return MC_DRAWS * (BOUNDARY_SE_MIN * sd / dist) ** 2


# ------------------------------------------------------------------------------------------- #
# the row sets
# ------------------------------------------------------------------------------------------- #
def row_sets(d: pd.DataFrame) -> list[dict]:
    """Every distinct row set the map prints an interval for, with all of its stratum names.

    The identity of a row set is its ROW MEMBERSHIP, computed here from the masks and not read
    off ``stratum_overlap.csv``; the two agree.
    """
    groups: dict[tuple[int, ...], list[tuple[str, str]]] = {}
    for axis, lab, mask in strata_of(d):
        idx = tuple(int(i) for i in np.flatnonzero(np.asarray(mask)))
        if not idx:
            continue
        groups.setdefault(idx, []).append((axis, lab))
    cells = []
    for idx, names in groups.items():
        sub = d.iloc[list(idx)]
        n_sol, n_slv = sub["solute_smiles"].nunique(), sub["solvent_smiles"].nunique()
        # The map draws an interval only where the fixed cell is defined and at least one
        # cluster axis can be resampled -- measure()'s own guard, repeated here.
        if len(idx) < 2 * N_BINS or max(n_sol, n_slv) < 2:
            continue
        names.sort(key=lambda nl: (AXIS_ORDER.index(nl[0]), nl[1]))
        cells.append({
            "row_set_id": hashlib.blake2b(
                ",".join(map(str, idx)).encode(), digest_size=4).hexdigest(),
            "canonical_axis": names[0][0], "canonical_stratum": names[0][1],
            "names": [{"axis": a, "stratum": s, "printed_in": TABLE_OF_AXIS[a]} for a, s in names],
            "n_printings": len(names),
            "idx": idx,
            "n": len(idx),
            "n_solutes": int(n_sol), "n_solvents": int(n_slv),
            "n_pairs": int(sub.groupby(["solute_smiles", "solvent_smiles"]).ngroups),
            "n_sources": int(sub["source_doi"].nunique()),
            "one_way_only": bool(min(n_sol, n_slv) < 2),
        })
    cells.sort(key=lambda c: -c["n"])
    return cells


def as_submitted_of(cell: dict, s: dict) -> dict | None:
    """What each of this row set's names printed in the submission, and whether that digit held.

    One row set, several names, several independent 3000-draw replicates: this block is the
    defect made readable.  Each name's endpoints are the ones in the snapshot taken before the
    seed was repaired, and each is measured against THIS row set's Monte-Carlo standard deviation
    -- the printed value is a single draw, so its distance to a rounding boundary in units of that
    spread is what says whether the digit was a fact about the data or about the name.

    ``spread_across_names`` is the range of a printed endpoint over the names of one row set.  It
    is not an uncertainty: it is the same quantity measured several times, and a reader of the
    submission could not tell.
    """
    if not AS_SUBMITTED.exists():
        return None
    sub = _AS_SUB[0]
    rows = []
    for nm in cell["names"]:
        r = sub[(sub["axis"] == nm["axis"]) & (sub["stratum"] == nm["stratum"])]
        if not len(r):
            continue
        r = r.iloc[0]
        lo, hi = float(r["margin_ci90_lo"]), float(r["margin_ci90_hi"])
        _, k_lo = boundary_margin(lo, s["lo_sd"] if s["lo_sd"] > 0 else float("nan"), 2)
        _, k_hi = boundary_margin(hi, s["hi_sd"] if s["hi_sd"] > 0 else float("nan"), 2)
        rows.append({
            "axis": nm["axis"], "stratum": nm["stratum"], "printed_in": nm["printed_in"],
            "ci90_lo": lo, "ci90_hi": hi,
            "printed_as": [half_up(lo, 2), half_up(hi, 2)],
            "clearance_in_map_sd": {"lo": None if not np.isfinite(k_lo) else round(k_lo, 2),
                                    "hi": None if not np.isfinite(k_hi) else round(k_hi, 2)},
            "digits_supported": bool(np.isfinite(k_lo) and np.isfinite(k_hi)
                                     and min(k_lo, k_hi) >= BOUNDARY_SE_MIN),
        })
    if not rows:
        return None
    return {
        "n_names": len(rows), "printings": rows,
        "spread_across_names": {
            "lo": round(max(r["ci90_lo"] for r in rows) - min(r["ci90_lo"] for r in rows), 4),
            "hi": round(max(r["ci90_hi"] for r in rows) - min(r["ci90_hi"] for r in rows), 4)},
        "distinct_printed_pairs": sorted({tuple(r["printed_as"]) for r in rows}).__len__(),
        "source": str(AS_SUBMITTED.name),
    }


#: Loaded once in main(); a one-slot list so the workers never pickle it.
_AS_SUB: list = []


# ------------------------------------------------------------------------------------------- #
# workers
# ------------------------------------------------------------------------------------------- #
_W: dict = {}


def _init(payload):
    _W.update(payload)


def _task(job):
    cid, seed, draws = job
    g, m, su, sv = _W[cid]
    P, lo, hi, used, ndist = two_way_boot(g, m, su, sv, draws, seed)
    return cid, seed, draws, P, lo, hi, used, ndist


def run_jobs(jobs, payload, jobs_n, label):
    t0 = time.time()
    if jobs_n <= 1:
        _init(payload)
        res = [_task(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=jobs_n, initializer=_init,
                                 initargs=(payload,)) as pool:
            res = list(pool.map(_task, jobs, chunksize=max(1, len(jobs) // (jobs_n * 8))))
    print(f"[{label}] {len(jobs)} replicates, "
          f"{sum(j[2] for j in jobs):,} draws, {time.time() - t0:.0f}s", flush=True)
    return res


# ------------------------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP,
                    help="convergence budget per row set, in draws")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--remeasure", action="store_true",
                    help="re-run the 3000-draw study instead of reading its cache")
    args = ap.parse_args()

    broad, _ = prepare(BROAD, "broad")
    d = broad.reset_index(drop=True)
    cells = row_sets(d)
    if AS_SUBMITTED.exists():
        sub = pd.read_csv(AS_SUBMITTED)
        _AS_SUB.append(sub[(sub["set"] == "broad_477") & (sub["unit"] == UNIT)
                           & (sub["convention"] == CONV_NAME)])
        print(f"[as-submitted] {AS_SUBMITTED.name}: {len(_AS_SUB[0])} strata at the printed cell")
    n_slots = sum(c["n_printings"] for c in cells)
    print(f"{len(cells)} row sets print an interval, in {n_slots} table cells "
          f"({n_slots - len(cells)} of them a second or third printing of a row set already "
          f"printed), {2 * len(cells)} printed endpoints")

    payload = {}
    for c in cells:
        sub = d.iloc[list(c["idx"])]
        payload[c["row_set_id"]] = (sub[CONV_COL].to_numpy(float), sub["m"].to_numpy(float),
                                    sub["solute_smiles"].to_numpy(),
                                    sub["solvent_smiles"].to_numpy())

    # ------------------------------------------------------------------ bit-identity, at run time
    gly = [c for c in cells if c["canonical_stratum"] == "glycol_ether"]
    if len(gly) != 1:
        raise SystemExit("the glycol-ether row set is not where this script expects it")
    gid = gly[0]["row_set_id"]
    g, m, su, sv = payload[gid]
    ref = two_way_margin_boot(g, m, su, sv, N_BINS, DDOF, n_boot=N_BOOT, seed=1964585814)
    got = two_way_boot(g, m, su, sv, N_BOOT, 1964585814)[:3]
    if ref != got:
        raise SystemExit(f"bincount bootstrap is not bit-identical: {ref} vs {got}")
    print(f"[check] bincount == Counter on the glycol-ether stratum at its map seed: {got}")

    # ------------------------------------------------------------- stage A: the 3000-draw study
    if MC_CSV.exists() and not args.remeasure:
        mc = pd.read_csv(MC_CSV)
        print(f"[mc] read {MC_CSV.name} ({len(mc)} replicates)")
    else:
        jobs = [(c["row_set_id"], MC_SEED0 + s, MC_DRAWS)
                for c in cells for s in range(MC_SEEDS)]
        res = run_jobs(jobs, payload, args.jobs, "mc")
        mc = pd.DataFrame(res, columns=["row_set_id", "seed", "draws", "P_boot",
                                        "ci90_lo", "ci90_hi", "n_used", "n_distinct_margins"])
        mc.to_csv(MC_CSV, index=False)
        print(f"[mc] wrote {MC_CSV}")

    stats = {}
    for cid, grp in mc.groupby("row_set_id"):
        grp = grp.sort_values("seed")
        lo, hi = grp["ci90_lo"].to_numpy(), grp["ci90_hi"].to_numpy()
        stats[cid] = {
            "n_seeds": int(len(grp)),
            "lo_mean": float(lo.mean()), "lo_sd": float(lo.std(ddof=1)),
            "lo_min": float(lo.min()), "lo_max": float(lo.max()),
            "hi_mean": float(hi.mean()), "hi_sd": float(hi.std(ddof=1)),
            "hi_min": float(hi.min()), "hi_max": float(hi.max()),
            "P_boot_mean": float(grp["P_boot"].mean()),
            "n_distinct_margins_median": int(np.median(grp["n_distinct_margins"])),
            "half_split_lo_sd": [float(lo[:len(lo) // 2].std(ddof=1)),
                                 float(lo[len(lo) // 2:].std(ddof=1))],
            "half_split_hi_sd": [float(hi[:len(hi) // 2].std(ddof=1)),
                                 float(hi[len(hi) // 2:].std(ddof=1))],
        }

    # ------------------------------------------------- harness validation against the one deposit
    dep = json.loads(CONVERGED_GLYCOL.read_text())
    dep_mc = dep["monte_carlo_error_at_the_maps_own_3000_draws"]
    sub40 = mc[(mc.row_set_id == gid) & (mc.seed < MC_SEED0 + dep_mc["n_seeds"])]
    if len(sub40) != dep_mc["n_seeds"]:
        raise SystemExit("the glycol-ether cell does not carry the deposit's first 40 seeds")
    repro = {
        "n_seeds": dep_mc["n_seeds"],
        "lo_mean": round(float(sub40["ci90_lo"].mean()), 4),
        "lo_sd": round(float(sub40["ci90_lo"].std(ddof=1)), 4),
        "lo_range": [round(float(sub40["ci90_lo"].min()), 4),
                     round(float(sub40["ci90_lo"].max()), 4)],
        "hi_mean": round(float(sub40["ci90_hi"].mean()), 4),
        "hi_sd": round(float(sub40["ci90_hi"].std(ddof=1)), 4),
        "hi_range": [round(float(sub40["ci90_hi"].min()), 4),
                     round(float(sub40["ci90_hi"].max()), 4)],
    }
    for k, v in repro.items():
        if dep_mc[k] != v:
            raise SystemExit(f"harness does not reproduce the deposit at {k}: {v} vs {dep_mc[k]}")
    print(f"[check] first {dep_mc['n_seeds']} seeds reproduce "
          f"{CONVERGED_GLYCOL.name} exactly: {repro['lo_sd']} / {repro['hi_sd']}")

    # ------------------------------------------------------------------- stage B: the plan
    plan = {}
    for c in cells:
        s = stats[c["row_set_id"]]
        sd = max(s["lo_sd"], s["hi_sd"])
        costs = {}
        for dp in PRECISIONS:
            dl, _ = boundary_margin(s["lo_mean"], 1.0, dp)
            dh, _ = boundary_margin(s["hi_mean"], 1.0, dp)
            costs[dp] = max(required_draws(s["lo_sd"], dl), required_draws(s["hi_sd"], dh))
        # Degeneracy is "no seed moved either endpoint", tested on the RANGE.  `sd == 0.0' is not
        # that test: 200 bit-identical floats can average to a sample sd of 7e-17.  See the
        # module docstring.
        immovable = (s["lo_max"] - s["lo_min"] == 0.0) and (s["hi_max"] - s["hi_min"] == 0.0)
        if immovable:
            target, verdict = 2, "degenerate"
        else:
            target = next((dp for dp in PRECISIONS if costs[dp] <= args.cap), None)
            verdict = "state" if target is None else ("converge" if target == 2 else "coarsen")
        plan[c["row_set_id"]] = {"target_decimals": target, "planned_verdict": verdict,
                                 "cost": costs, "sd": sd}
        print(f"  {c['canonical_stratum'][:34]:34s} n={c['n']:>4}  sd {s['lo_sd']:.4f}/"
              f"{s['hi_sd']:.4f}  2dp {costs[2]:.3g}  1dp {costs[1]:.3g}  -> {verdict}"
              + (f" @{target}dp" if target else ""))
    total = sum(min(args.cap, max(CONV_REPS * CONV_DRAWS_MIN, plan[c["row_set_id"]]["cost"][
        plan[c["row_set_id"]]["target_decimals"]]))
        for c in cells if plan[c["row_set_id"]]["planned_verdict"] in ("converge", "coarsen")
        and c["canonical_stratum"] != "glycol_ether")
    print(f"[plan] cap {args.cap:,} draws/cell; convergence total ~{total:,.0f} draws")
    if args.plan_only:
        return 0

    # --------------------------------------------------------------- stage C: the convergence
    jobs, sched = [], {}
    for c in cells:
        cid, p = c["row_set_id"], plan[c["row_set_id"]]
        if p["planned_verdict"] in ("state", "degenerate") or \
                c["canonical_stratum"] == "glycol_ether":
            continue
        want = max(float(CONV_REPS * CONV_DRAWS_MIN), p["cost"][p["target_decimals"]])
        draws = int(min(CONV_DRAWS_MAX, max(CONV_DRAWS_MIN, math.ceil(want / CONV_REPS))))
        sched[cid] = draws
        jobs += [(cid, CONV_SEED0 + s, draws) for s in range(CONV_REPS)]
    res = run_jobs(jobs, payload, args.jobs, "converge") if jobs else []
    rep = pd.DataFrame(res, columns=["row_set_id", "seed", "draws", "P_boot", "ci90_lo",
                                     "ci90_hi", "n_used", "n_distinct_margins"])
    if len(rep):
        rep.to_csv(REP_CSV, index=False)
        print(f"[converge] wrote {REP_CSV}")

    # ------------------------------------------------------------------------- the verdicts
    out_cells, table = [], []
    for c in cells:
        cid = c["row_set_id"]
        s, p = stats[cid], plan[cid]
        rec = {k: v for k, v in c.items() if k != "idx"}
        rec["monte_carlo_at_the_maps_own_draws"] = {
            "n_seeds": s["n_seeds"], "n_draws_each": MC_DRAWS,
            "seed_sequence": f"{MC_SEED0}..{MC_SEED0 + s['n_seeds'] - 1}",
            "lo_mean": round(s["lo_mean"], 5), "lo_sd": round(s["lo_sd"], 5),
            "lo_range": [round(s["lo_min"], 4), round(s["lo_max"], 4)],
            "hi_mean": round(s["hi_mean"], 5), "hi_sd": round(s["hi_sd"], 5),
            "hi_range": [round(s["hi_min"], 4), round(s["hi_max"], 4)],
            "half_split_sd_lo": [round(x, 4) for x in s["half_split_lo_sd"]],
            "half_split_sd_hi": [round(x, 4) for x in s["half_split_hi_sd"]],
            "sd_over_width": round(max(s["lo_sd"], s["hi_sd"])
                                   / max(s["hi_mean"] - s["lo_mean"], 1e-12), 4),
            "distinct_resampled_margins_median": s["n_distinct_margins_median"],
        }
        rec["draws_to_determine"] = {f"{dp}dp": (None if not np.isfinite(p["cost"][dp])
                                                 else round(p["cost"][dp]))
                                     for dp in PRECISIONS}
        rec["planned_verdict"] = p["planned_verdict"]
        rec["as_submitted"] = as_submitted_of(c, s)

        if c["canonical_stratum"] == "glycol_ether":
            ci = dep["converged_interval"]
            lo, hi, se_lo, se_hi = ci["ci90_lo"], ci["ci90_hi"], ci["se_lo"], ci["se_hi"]
            k_lo, k_hi = ci["boundary_margin_se"]["lo"], ci["boundary_margin_se"]["hi"]
            rec.update(verdict="converged", decimals=2, n_replicates=ci["n_replicates"],
                       draws_per_replicate=ci["draws_per_replicate"], n_draws=ci["n_draws"],
                       source=str(CONVERGED_GLYCOL.relative_to(ROOT)))
        elif p["planned_verdict"] == "degenerate":
            lo, hi = s["lo_mean"], s["hi_mean"]
            se_lo = se_hi = 0.0
            k_lo = k_hi = float("inf")
            rec.update(verdict="degenerate", decimals=2, n_replicates=s["n_seeds"],
                       draws_per_replicate=MC_DRAWS, n_draws=s["n_seeds"] * MC_DRAWS,
                       source="this script")
        elif p["planned_verdict"] == "state":
            # The printed value is the mean of the 200 seeds, so its own error is sd/sqrt(200);
            # the SPREAD of one 3000-draw replicate is a different number and both are kept.
            # `boundary_margin_se' is reported here too: a stated cell is one that could not be
            # brought four standard errors clear, and how close it came is part of saying so.
            lo, hi = s["lo_mean"], s["hi_mean"]
            se_lo = s["lo_sd"] / math.sqrt(s["n_seeds"])
            se_hi = s["hi_sd"] / math.sqrt(s["n_seeds"])
            _, k_lo = boundary_margin(lo, se_lo, 2)
            _, k_hi = boundary_margin(hi, se_hi, 2)
            rec.update(verdict="stated", decimals=2, n_replicates=s["n_seeds"],
                       draws_per_replicate=MC_DRAWS, n_draws=s["n_seeds"] * MC_DRAWS,
                       source="this script")
        else:
            grp = rep[rep.row_set_id == cid]
            los, his = grp["ci90_lo"].to_numpy(), grp["ci90_hi"].to_numpy()
            lo, hi = float(los.mean()), float(his.mean())
            se_lo = float(los.std(ddof=1) / np.sqrt(len(los)))
            se_hi = float(his.std(ddof=1) / np.sqrt(len(his)))
            dp = p["target_decimals"]
            _, k_lo = boundary_margin(lo, se_lo, dp)
            _, k_hi = boundary_margin(hi, se_hi, dp)
            ok = min(k_lo, k_hi) >= BOUNDARY_SE_MIN
            if not ok:                       # demoted by the check, never promoted by it
                dp = None
                for cand in [x for x in PRECISIONS if x < p["target_decimals"]]:
                    _, a = boundary_margin(lo, se_lo, cand)
                    _, b = boundary_margin(hi, se_hi, cand)
                    if min(a, b) >= BOUNDARY_SE_MIN:
                        dp, k_lo, k_hi = cand, a, b
                        break
            rec.update(verdict=("converged" if dp == 2 else
                                "coarsened" if dp is not None else "stated"),
                       decimals=dp if dp is not None else 2,
                       n_replicates=int(len(los)), draws_per_replicate=sched[cid],
                       n_draws=int(len(los)) * sched[cid],
                       seed_sequence=f"{CONV_SEED0}..{CONV_SEED0 + len(los) - 1}",
                       source="this script")
            if dp is None:
                # Demoted: the run bought a precision the run itself does not support.  Keep the
                # RUN's standard errors and the clearance it actually reached at two decimals --
                # replacing them with the 3000-draw spread would throw away what the draws bought
                # and overstate the error of the number now printed.
                _, k_lo = boundary_margin(lo, se_lo, 2)
                _, k_hi = boundary_margin(hi, se_hi, 2)
                rec["demoted_by_the_verification_check"] = True

        nd = rec["decimals"]
        rec["interval"] = {"lo": round(lo, 6), "hi": round(hi, 6),
                           "se_lo": round(se_lo, 6), "se_hi": round(se_hi, 6),
                           "boundary_margin_se": {
                               "lo": None if k_lo is None else (
                                   None if not np.isfinite(k_lo) else round(k_lo, 2)),
                               "hi": None if k_hi is None else (
                                   None if not np.isfinite(k_hi) else round(k_hi, 2))},
                           "printed_as": [half_up(lo, nd), half_up(hi, nd)],
                           "printed_decimals": nd,
                           # The superscript a stated interval prints: the standard deviation of
                           # ONE 3000-draw replicate, the map's own apparatus, which is what its
                           # second decimal has to be read against.  `se_lo'/`se_hi' above are a
                           # different quantity -- the error of the mean actually printed.
                           "printed_monte_carlo_sd": (
                               round(max(s["lo_sd"], s["hi_sd"]), 4)
                               if rec["verdict"] == "stated" else None),
                           "monte_carlo_sd_of_one_3000_draw_replicate": {
                               "lo": round(s["lo_sd"], 5), "hi": round(s["hi_sd"], 5)}}
        out_cells.append(rec)
        table.append({
            "row_set_id": cid, "canonical_axis": c["canonical_axis"],
            "canonical_stratum": c["canonical_stratum"], "n_printings": c["n_printings"],
            "names": " ; ".join(f"{x['axis']}::{x['stratum']}" for x in rec["names"]),
            "n": c["n"], "n_solutes": c["n_solutes"], "n_solvents": c["n_solvents"],
            "n_pairs": c["n_pairs"], "n_sources": c["n_sources"],
            "mc_sd_lo": round(s["lo_sd"], 5), "mc_sd_hi": round(s["hi_sd"], 5),
            "mc_lo_range": f"[{s['lo_min']:.4f},{s['lo_max']:.4f}]",
            "mc_hi_range": f"[{s['hi_min']:.4f},{s['hi_max']:.4f}]",
            "draws_to_2dp": rec["draws_to_determine"]["2dp"],
            "draws_to_1dp": rec["draws_to_determine"]["1dp"],
            "verdict": rec["verdict"], "decimals": rec["decimals"],
            "n_draws": rec["n_draws"],
            "ci90_lo": rec["interval"]["lo"], "ci90_hi": rec["interval"]["hi"],
            "se_lo": rec["interval"]["se_lo"], "se_hi": rec["interval"]["se_hi"],
            "boundary_margin_se_lo": rec["interval"]["boundary_margin_se"]["lo"],
            "boundary_margin_se_hi": rec["interval"]["boundary_margin_se"]["hi"],
            "printed_lo": rec["interval"]["printed_as"][0],
            "printed_hi": rec["interval"]["printed_as"][1],
            "printed_monte_carlo_sd": rec["interval"]["printed_monte_carlo_sd"],
        })

    tab = pd.DataFrame(table).sort_values("n", ascending=False)
    tab.to_csv(OUT_CSV, index=False)
    counts = tab["verdict"].value_counts().to_dict()
    n_end = 2 * len(out_cells)

    # How many of the endpoints the submission printed off the 3000-draw apparatus were not
    # supported at the printed precision -- the finding this repairs, recomputed and not quoted.
    # Counted per DISTINCT endpoint: the two glycol-ether endpoints come from the converged
    # deposit and are excluded, leaving 46 of the 48.
    # Two clearances are reported, under names that cannot be swapped: the SMALLEST, which is the
    # endpoint sitting nearest a rounding boundary, and the LARGEST, which is the endpoint that
    # comes nearest to satisfying the 4-sd rule -- the map's best case, and the one a reader will
    # want when asking whether the rule is merely strict.  A degenerate endpoint enters neither.
    unsupported, from_apparatus, clears, degen_endpoints = 0, 0, [], 0
    for c in out_cells:
        s = stats[c["row_set_id"]]
        if c["canonical_stratum"] == "glycol_ether":
            continue
        immovable = (s["lo_max"] - s["lo_min"] == 0.0) and (s["hi_max"] - s["hi_min"] == 0.0)
        for mean, sd in ((s["lo_mean"], s["lo_sd"]), (s["hi_mean"], s["hi_sd"])):
            from_apparatus += 1
            if immovable:
                degen_endpoints += 1
                continue
            _, k = boundary_margin(mean, sd, 2)
            if not (np.isfinite(k) and k >= BOUNDARY_SE_MIN):
                unsupported += 1
            clears.append(float(k))
    closest = min(clears) if clears else float("inf")

    OUT.write_text(json.dumps({
        "what": "One printing precision per row set for every interval the stratified map prints, "
                "chosen from that row set's own Monte-Carlo error at the map's 3000 draws and "
                "verified on the convergence run that bought it.",
        "why": "The map draws N_BOOT=3000 resamples per stratum and printed the endpoints to two "
               "decimals. Two decimals are not determined at that draw count: over "
               f"{MC_SEEDS} seeds the endpoints of the map's own intervals carry Monte-Carlo "
               "standard deviations from 0.0009 to 0.223, so the second decimal of most of them "
               "was a property of the seed. The glycol-ether cell was converged in "
               "glycol_ether_ci_converged.json after two referees noticed it; this deposit is the "
               "same repair applied to the class, cell by cell rather than uniformly.",
        "generated_by": "scripts/analysis/run_b_insuff_map_ci_precision.py",
        "estimator_cell": {
            "set": "broad_477", "unit": UNIT, "convention": CONV_NAME,
            "n_bins": N_BINS, "within_bin_variance": "Bessel (ddof=1)",
            "bootstrap": "two-way solute x solvent cluster, 5th/95th percentiles",
            "map_draw_count": MC_DRAWS,
        },
        "printing_rule": {
            "rule": "an endpoint prints to d decimals only if it stands at least "
                    f"{BOUNDARY_SE_MIN:.0f} Monte-Carlo standard errors clear of the nearest "
                    "ROUNDING BOUNDARY at d decimals; an interval prints both endpoints at the "
                    "coarser of what its two endpoints support",
            "boundary_margin": "run_b_insuff_glycol_ether_ci.boundary_margin (the fixed version, "
                               "which measures the distance to the boundary and not to the "
                               "printable value)",
            "ladder": "CONVERGE at two decimals if it costs at most the cap; else COARSEN to one; "
                      "else STATE two decimals with the Monte-Carlo standard deviation beside "
                      "them. Coarsening stops at one decimal because at zero the map's cells "
                      "stop being distinguishable from one another.",
            "target_chosen_before_the_run_and_only_demoted_after":
                "the precision is chosen from the 3000-draw study, then verified on the "
                "convergence run's own standard errors; the check can demote a cell and never "
                "promotes one",
            "cap_draws_per_row_set": args.cap,
            "convergence_replicates_per_row_set": CONV_REPS,
        },
        "counts": {
            "row_sets_printing_an_interval": len(out_cells),
            "printed_interval_cells": int(tab["n_printings"].sum()),
            "duplicate_printings": int(tab["n_printings"].sum()) - len(out_cells),
            "row_sets_carrying_more_than_one_name": int((tab["n_printings"] > 1).sum()),
            "printed_endpoints": n_end,
            "endpoints_off_the_3000_draw_apparatus": from_apparatus,
            "of_those_degenerate_no_seed_moves_them": degen_endpoints,
            "of_those_unsupported_at_two_decimals": unsupported,
            "closest_endpoint_to_its_boundary_in_sd": round(closest, 2),
            "largest_clearance_of_any_movable_endpoint_in_sd": round(max(clears), 2),
            "median_clearance_of_a_movable_endpoint_in_sd": round(float(np.median(clears)), 2),
            "clearance_is_measured_on": "the mean of the 200 seeds, which is the quantity a "
                                        "convergence run drives; measured instead on the single "
                                        "3000-draw replicate the submission actually printed, "
                                        "the same endpoints give different clearances and the "
                                        "same verdicts (both are deposited per cell)",
            "verdicts": counts,
        },
        "harness_validation": {
            "bincount_vs_Counter_bit_identical_at_the_glycol_map_seed": list(got),
            "first_40_seeds_reproduce_the_converged_deposit": repro,
            "seed_sequence_shared_with": str(CONVERGED_GLYCOL.relative_to(ROOT)),
            "relative_standard_error_of_an_sd_at_this_seed_count":
                round(1.0 / math.sqrt(2 * (MC_SEEDS - 1)), 4),
        },
        "the_mechanism": {
            "defect": "run_b_insuff_stratified_map.stable_seed derived the bootstrap seed from "
                      "the STRATUM NAME, so a row set carrying several names drew an independent "
                      "replicate under each and the table printed them as separate measurements.",
            "fix": "the map now seeds from the ROW SET -- the seed string is the row set's "
                   "canonical name, the first of its names in the map's own axis order -- and "
                   "carries row_set_id in stratified_map_table.csv and admissibility_table.csv, "
                   "so two names of one row set hold the identical interval and say so.",
            "row_sets_with_more_than_one_name": [
                {"row_set_id": c["row_set_id"], "n": c["n"],
                 "names": [f"{x['axis']}::{x['stratum']}" for x in c["names"]],
                 "printed_pairs_in_the_submission": (
                     None if not c.get("as_submitted") else
                     [x["printed_as"] for x in c["as_submitted"]["printings"]]),
                 "spread_across_names": (None if not c.get("as_submitted") else
                                         c["as_submitted"]["spread_across_names"])}
                for c in out_cells if c["n_printings"] > 1],
            "as_submitted_snapshot": str(AS_SUBMITTED.relative_to(ROOT)),
        },
        "cells": out_cells,
        "table_csv": str(OUT_CSV.relative_to(ROOT)),
        "monte_carlo_replicates_csv": str(MC_CSV.relative_to(ROOT)),
        "convergence_replicates_csv": str(REP_CSV.relative_to(ROOT)) if len(rep) else None,
    }, indent=2) + "\n")
    print(f"[saved] {OUT}\n[saved] {OUT_CSV}")
    print("verdicts:", counts)
    print(f"endpoints off the 3000-draw apparatus not supported at two decimals: "
          f"{unsupported} of {from_apparatus} (of {n_end} printed); closest "
          f"{closest:.2f} sd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
