#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Converge the 90% interval on the map's one stratified finding, and size the map's own
bootstrap error.

WHY THIS EXISTS
---------------
Two referees, independently, reported that the glycol-ether margin's 90% interval is printed at
several different values across the submission:

    [+1.27,+2.83]   abstract, Table 4, Sec. sec:broad, SI map table (solvent class)
    [+1.27,+2.87]   SI map table, solvent family fine
    [+1.23,+2.90]   SI map table, solvent class x solute role
    [+1.260,+2.873] SI, the cross-fit section's coarsening baseline

They are not four quantities and they are not four roundings of one.  They are four independent
3000-draw replicates of ONE bootstrap on ONE row set:

  * the row set is the same 182 rows in every case -- 19 solutes, 4 solvents, 43 pairs, 3
    publications -- and it is the same 182 in the 477-row deposit and in the 473-row cross-fit
    deposit, because none of the four rows the cross-fit declaration drops carries a glycol-ether
    solvent.  MSE, B_insuff^up and the margin are bit-identical across all four printings;
  * `run_b_insuff_stratified_map.stable_seed' derives the bootstrap seed from the STRATUM NAME,
    and this row set has three names (solvent_class::glycol_ether,
    solvent_family_fine::glycol_ether, solvent_class_x_solute_role::glycol_ether|organic_solute).
    Three names, three seeds, three replicates.  `run_b_insuff_crossfit_scoring.py' composes the
    seed string differently again, which is the fourth.

WHAT THIS SCRIPT MEASURES
-------------------------
1.  The Monte-Carlo error of a 3000-draw replicate, over 40 seeds.  It is ~0.020 on each
    endpoint -- twice the resolution the manuscript printed the endpoints to, which is the whole
    of the disagreement.  This is the number that says the second decimal of any single replicate
    is noise, and it is why the map's per-stratum intervals must not be read to that digit.
2.  The converged interval, whose standard error must be small enough that the printed two
    decimals ARE determined.  This is what the manuscript prints everywhere, including in the
    abstract.

The converged value is WIDER than the replicate the abstract had been quoting, [+1.26,+2.87]
against [+1.27,+2.83] -- the replicate that happened to be attached to the coarsest name was also
the narrowest of the four in the document.  That direction is recorded here because it is the
direction that matters.

WHY THE DRAW COUNT ROSE FROM 1.2e6 TO 1.2e8, 2026-08-10
-------------------------------------------------------
"The standard error is 0.001, so two decimals are determined" is not an argument about the
standard error alone.  It is an argument about the standard error MEASURED AGAINST THE DISTANCE
FROM THE VALUE TO THE NEAREST ROUNDING BOUNDARY, and at 12 x 100000 draws the lower endpoint sat
0.0008 above the 1.2550 boundary with a standard error of 0.00091 -- less than one.  So the
SECOND DECIMAL OF A NUMBER IN THE ABSTRACT was a property of the seed set: this one printed
+1.26, and an independent 6 x 40000 set centred the same endpoint at 1.2539, which prints +1.25.
The upper endpoint was never in question (0.0039 clear of its boundary, 3.4 standard errors).

The fix is not to choose.  The 5th percentile of this bootstrap is a definite number, and the
seed dependence is Monte-Carlo error that buys down as 1/sqrt(draws), so the script now runs
until the boundary distance is large in units of the standard error and REPORTS THAT RATIO
(``boundary_margin_se`` in the deposit) rather than the standard error on its own.  A run whose
endpoint lands within 4 standard errors of a boundary has not determined the digit it prints, and
the deposit says so in ``printing_is_determined``; the manuscript's rule is that both endpoints
must be determined before either is printed to two decimals.

The replicates are the same ``two_way_boot`` at the same 100000 draws and the same seed sequence
(900000 + s); only their NUMBER changed, so the 12 replicates of the earlier deposit are the
first 12 of this one and the two estimates are nested rather than independent.

Estimator cell, held fixed and equal to the map's headline cell: broad IDAC set, row unit,
deployed residual-only convention (g_2002_res), eight equal-count bins of g, Bessel (ddof=1)
within-bin variance, two-way solute x solvent cluster bootstrap, 5th/95th percentiles.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_glycol_ether_ci.py

``--replicates``/``--draws`` set the convergence budget and ``--jobs`` spreads the replicates over
processes (the estimator is untouched; each worker runs the same ``two_way_boot`` on its own
seeds).  The defaults are the deposited setting.  ``--replicates 12`` reproduces the 2026-08-07
deposit exactly.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from run_b_insuff_stratified_map import classify_solvent            # noqa: E402

BROAD = ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv"
OUT = ROOT / "results" / "b_insuff" / "glycol_ether_ci_converged.json"

N_BINS, DDOF = 8, 1
MC_SEEDS = 40           # replicates at the map's own 3000 draws, to size its Monte-Carlo error
MC_DRAWS = 3000
CONV_REPS, CONV_DRAWS = 1200, 100_000
CONV_SEED0 = 900_000
#: A printed endpoint is determined when it stands at least this many standard errors clear of the
#: nearest rounding boundary at the decimal it is printed to.  Four, not two: the quantity is
#: reported in an abstract, where it is read without the deposit beside it.
BOUNDARY_SE_MIN = 4.0


def lotv(g: np.ndarray, m: np.ndarray, n_bins: int = N_BINS, ddof: int = DDOF) -> float:
    """E[Var(m | equal-count bin of g)] -- the map's B_insuff^up estimator."""
    edges = np.quantile(g, np.linspace(0.0, 1.0, n_bins + 1))
    edges[0] -= 1e-9
    edges[-1] += 1e-9
    idx = np.digitize(g, edges[1:-1])
    tot = 0.0
    for b in range(n_bins):
        mm = m[idx == b]
        if len(mm) > ddof:
            tot += (len(mm) / len(m)) * mm.var(ddof=ddof)
    return float(tot)


def margin(g: np.ndarray, m: np.ndarray) -> float:
    return float(np.mean((m - g) ** 2)) - 2.0 * lotv(g, m)


def two_way_boot(g, m, solute, solvent, n_boot: int, seed: int):
    """Two-way (solute x solvent) cluster bootstrap of the margin; returns (P, lo, hi, n_used).

    The multiplicity of a row is the product of its solute's and its solvent's resample counts,
    which is the same design as run_b_insuff_estimator_grid.two_way_margin_boot; a draw whose
    total multiplicity falls below 12 cannot fill eight bins and is discarded, as there.
    """
    rng = np.random.default_rng(seed)
    _, ui = np.unique(solute, return_inverse=True)
    _, vi = np.unique(solvent, return_inverse=True)
    nu, nv, n = ui.max() + 1, vi.max() + 1, len(m)
    out = np.empty(n_boot)
    k = 0
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, nu, size=nu), minlength=nu)
        cv = np.bincount(rng.integers(0, nv, size=nv), minlength=nv)
        mult = cs[ui] * cv[vi]
        if mult.sum() < 12:
            continue
        idx = np.repeat(np.arange(n), mult)
        out[k] = margin(g[idx], m[idx])
        k += 1
    out = out[:k]
    return (float(np.mean(out > 0)), float(np.percentile(out, 5)),
            float(np.percentile(out, 95)), k)


#: Module-level so a spawned worker can reach it; the payload is 182 rows, so it travels by value.
_ARGS: dict = {}


def _init(g, m, solute, solvent, draws):
    _ARGS.update(g=g, m=m, solute=solute, solvent=solvent, draws=draws)


def _rep(seed: int):
    return two_way_boot(_ARGS["g"], _ARGS["m"], _ARGS["solute"], _ARGS["solvent"],
                        _ARGS["draws"], seed)


def half_up(value: float, decimals: int = 2) -> float:
    """The manuscript's rounding, half away from zero -- ``make_map_table_tex._round``'s rule.

    ``round`` is half-to-even and its binary floats break ties the other way as often as not, so
    a deposit rounded with it can disagree with the table generator that reads it.
    """
    q = Decimal(1).scaleb(-decimals)
    d = Decimal(repr(abs(value))).quantize(q, rounding=ROUND_HALF_UP)
    return float(-d if value < 0 else d)


def boundary_margin(value: float, se: float, decimals: int = 2) -> tuple[float, float]:
    """Distance from ``value`` to the nearest rounding BOUNDARY at ``decimals``, in units of ``se``.

    The boundaries are the odd multiples of half the last printed digit -- 1.245, 1.255, 1.265 at
    two decimals -- and they are NOT the printable values 1.25, 1.26.  The first version of this
    function measured the distance to the nearest printable VALUE, which is the complement of what
    it wanted, so it read an endpoint sitting 0.00022 from a boundary as "45.8 standard errors
    clear" and an endpoint 0.00432 clear as "2.0".  It reported the safe endpoint as the unsafe one
    and the unsafe one as safe.  That is the same class of error the whole deposit exists to catch,
    one level up, and it is recorded rather than quietly corrected.

    Returned as (distance, distance/se): the ratio is what says whether the printed digit is a fact
    about the data or about the seed set.
    """
    step = 10.0 ** (-decimals)
    half = step / 2.0
    dist = half - abs(((value + half) % step) - half)
    return dist, (dist / se if se > 0 else float("inf"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--replicates", type=int, default=CONV_REPS)
    ap.add_argument("--draws", type=int, default=CONV_DRAWS)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    df = pd.read_csv(BROAD)
    df["cls"] = [classify_solvent(s) for s in df["solvent_smiles"]]
    ge = df[df["cls"] == "glycol_ether"].reset_index(drop=True)

    m = ge["m_ln_gamma_inf"].to_numpy(float)
    g = ge["g_2002_res"].to_numpy(float)
    solute = ge["solute_smiles"].to_numpy()
    solvent = ge["solvent_smiles"].to_numpy()

    print(f"n = {len(ge)} rows, {ge['solute_smiles'].nunique()} solutes, "
          f"{ge['solvent_smiles'].nunique()} solvents, "
          f"{ge.groupby(['solute_smiles', 'solvent_smiles']).ngroups} pairs, "
          f"{ge['source_doi'].nunique()} sources")
    print(f"MSE {np.mean((m - g) ** 2):.6f}   B_insuff^up {lotv(g, m):.6f}   "
          f"margin {margin(g, m):.6f}")

    mc = [two_way_boot(g, m, solute, solvent, MC_DRAWS, 5000 + s)[1:3] for s in range(MC_SEEDS)]
    mc_lo = np.array([a for a, _ in mc])
    mc_hi = np.array([b for _, b in mc])
    print(f"{MC_DRAWS}-draw replicate over {MC_SEEDS} seeds: "
          f"lo {mc_lo.mean():+.4f} sd {mc_lo.std(ddof=1):.4f}, "
          f"hi {mc_hi.mean():+.4f} sd {mc_hi.std(ddof=1):.4f}")

    seeds = [CONV_SEED0 + s for s in range(args.replicates)]
    with ProcessPoolExecutor(max_workers=args.jobs, initializer=_init,
                             initargs=(g, m, solute, solvent, args.draws)) as pool:
        reps = list(pool.map(_rep, seeds, chunksize=4))
    los = np.array([r[1] for r in reps])
    his = np.array([r[2] for r in reps])
    Ps = np.array([r[0] for r in reps])
    se_lo = float(los.std(ddof=1) / np.sqrt(len(los)))
    se_hi = float(his.std(ddof=1) / np.sqrt(len(his)))
    d_lo, k_lo = boundary_margin(float(los.mean()), se_lo)
    d_hi, k_hi = boundary_margin(float(his.mean()), se_hi)
    determined = bool(min(k_lo, k_hi) >= BOUNDARY_SE_MIN)
    print(f"converged ({args.replicates} x {args.draws}): "
          f"[{los.mean():+.5f} (se {se_lo:.5f}), {his.mean():+.5f} (se {se_hi:.5f})] "
          f"-> printed [{los.mean():+.2f}, {his.mean():+.2f}]")
    print(f"boundary margin at 2 dp: lo {d_lo:.5f} = {k_lo:.1f} se, hi {d_hi:.5f} = {k_hi:.1f} se"
          f"   -> printed digits {'DETERMINED' if determined else 'NOT DETERMINED'} "
          f"(rule: >= {BOUNDARY_SE_MIN:.0f} se)")

    # The replicate endpoints, beside the deposit.  Every derived field above is a function of
    # these two columns, so a corrected FORMULA never again costs the hours the draws cost: the
    # first 1200x100000 run had to be repeated in full because the boundary margin was computed
    # the wrong way round and nothing but the two summary means had been kept.
    reps_out = args.out.with_name(args.out.stem + "_replicates.csv")
    pd.DataFrame({"seed": seeds, "ci90_lo": los, "ci90_hi": his, "P_boot": Ps,
                  "draws": args.draws}).to_csv(reps_out, index=False)

    args.out.write_text(json.dumps({
        "what": "Converged 90% two-way (solute x solvent) cluster bootstrap interval on the "
                "glycol-ether margin at the map's headline estimator cell (broad IDAC, row unit, "
                "deployed residual-only convention, 8 equal-count bins, Bessel within-bin "
                "variance), and the Monte-Carlo error of the map's own 3000-draw setting.",
        "why": "The map seeds its bootstrap from the STRATUM NAME, so the three strata that "
               "select the same 182 glycol-ether rows each drew an independent 3000-draw "
               "replicate, and the cross-fit artifact composed the seed string differently again "
               "for a fourth. The submission printed all four as if they were four quantities. "
               "They are one quantity; the spread between them is Monte-Carlo error and it is "
               "larger than the second decimal they were printed to. Every printing now quotes "
               "the converged value below. See the module docstring of "
               "scripts/analysis/run_b_insuff_glycol_ether_ci.py.",
        "generated_by": "scripts/analysis/run_b_insuff_glycol_ether_ci.py",
        "row_set": {
            "n": int(len(ge)),
            "n_solutes": int(ge["solute_smiles"].nunique()),
            "n_solvents": int(ge["solvent_smiles"].nunique()),
            "n_pairs": int(ge.groupby(["solute_smiles", "solvent_smiles"]).ngroups),
            "n_sources": int(ge["source_doi"].nunique()),
            "identical_in_the_477_and_473_row_deposits": True,
            "note": "none of the four rows the cross-fit declaration drops carries a "
                    "glycol-ether solvent, so this stratum is the same 182 rows in "
                    "stratified_map_table.csv (broad_477) and crossfit_map_table.csv (broad_473)",
        },
        "point_estimates": {
            "mse": round(float(np.mean((m - g) ** 2)), 6),
            "b_insuff_up": round(lotv(g, m), 6),
            "margin": round(margin(g, m), 6),
        },
        "converged_interval": {
            "n_replicates": int(args.replicates),
            "draws_per_replicate": int(args.draws),
            "n_draws": int(args.replicates) * int(args.draws),
            "seed_sequence": f"{CONV_SEED0}..{CONV_SEED0 + args.replicates - 1}",
            "ci90_lo": round(float(los.mean()), 5),
            "ci90_hi": round(float(his.mean()), 5),
            "se_lo": round(se_lo, 5),
            "se_hi": round(se_hi, 5),
            "P_boot": round(float(Ps.mean()), 4),
            "printed_as": [half_up(float(los.mean())), half_up(float(his.mean()))],
            "replicates_csv": reps_out.name,
            "printing_rule": "half-up to two decimals, and only if both endpoints stand at least "
                             f"{BOUNDARY_SE_MIN:.0f} Monte-Carlo standard errors clear of the "
                             "nearest rounding boundary",
            "boundary_margin_se": {"lo": round(k_lo, 2), "hi": round(k_hi, 2)},
            "boundary_distance": {"lo": round(d_lo, 5), "hi": round(d_hi, 5)},
            "printing_is_determined": determined,
        },
        "monte_carlo_error_at_the_maps_own_3000_draws": {
            "n_seeds": MC_SEEDS,
            "n_draws_each": MC_DRAWS,
            "lo_mean": round(float(mc_lo.mean()), 4),
            "lo_sd": round(float(mc_lo.std(ddof=1)), 4),
            "lo_range": [round(float(mc_lo.min()), 4), round(float(mc_lo.max()), 4)],
            "hi_mean": round(float(mc_hi.mean()), 4),
            "hi_sd": round(float(mc_hi.std(ddof=1)), 4),
            "hi_range": [round(float(mc_hi.min()), 4), round(float(mc_hi.max()), 4)],
        },
        "the_four_values_the_submission_printed_before_2026_08_07": {
            "[+1.27,+2.83]": {"exact": [1.268, 2.833], "source":
                              "stratified_map_table.csv, solvent_class::glycol_ether"},
            "[+1.27,+2.87]": {"exact": [1.266, 2.873], "source":
                              "stratified_map_table.csv, solvent_family_fine::glycol_ether"},
            "[+1.23,+2.90]": {"exact": [1.226, 2.896], "source":
                              "stratified_map_table.csv, "
                              "solvent_class_x_solute_role::glycol_ether | organic_solute"},
            "[+1.260,+2.873]": {"exact": [1.260269, 2.873223], "source":
                                "crossfit_map_table.csv, broad_473, solvent_class::glycol_ether, "
                                "column ci90_bin (the coarsening arm of the cross-fit table)"},
            "verdict": "same estimator, same 182 rows, four independent bootstrap replicates; "
                       "every endpoint within 1.8 sd of one mean",
        },
    }, indent=2) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
