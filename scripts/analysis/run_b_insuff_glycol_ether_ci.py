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
2.  The converged interval, 12 x 100000 draws, whose standard error is ~0.001 per endpoint, so
    the printed two decimals ARE determined.  This is what the manuscript now prints everywhere,
    including in the abstract.

The converged value is WIDER than the replicate the abstract had been quoting, [+1.26,+2.87]
against [+1.27,+2.83] -- the replicate that happened to be attached to the coarsest name was also
the narrowest of the four in the document.  That direction is recorded here because it is the
direction that matters.

Estimator cell, held fixed and equal to the map's headline cell: broad IDAC set, row unit,
deployed residual-only convention (g_2002_res), eight equal-count bins of g, Bessel (ddof=1)
within-bin variance, two-way solute x solvent cluster bootstrap, 5th/95th percentiles.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_glycol_ether_ci.py
"""
from __future__ import annotations

import json
import sys
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
CONV_REPS, CONV_DRAWS = 12, 100_000


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


def main() -> int:
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

    reps = [two_way_boot(g, m, solute, solvent, CONV_DRAWS, 900_000 + s)
            for s in range(CONV_REPS)]
    los = np.array([r[1] for r in reps])
    his = np.array([r[2] for r in reps])
    Ps = np.array([r[0] for r in reps])
    print(f"converged ({CONV_REPS} x {CONV_DRAWS}): "
          f"[{los.mean():+.4f} (se {los.std(ddof=1)/np.sqrt(CONV_REPS):.4f}), "
          f"{his.mean():+.4f} (se {his.std(ddof=1)/np.sqrt(CONV_REPS):.4f})] "
          f"-> printed [{los.mean():+.2f}, {his.mean():+.2f}]")

    OUT.write_text(json.dumps({
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
            "n_replicates": CONV_REPS,
            "draws_per_replicate": CONV_DRAWS,
            "n_draws": CONV_REPS * CONV_DRAWS,
            "ci90_lo": round(float(los.mean()), 4),
            "ci90_hi": round(float(his.mean()), 4),
            "se_lo": round(float(los.std(ddof=1) / np.sqrt(CONV_REPS)), 5),
            "se_hi": round(float(his.std(ddof=1) / np.sqrt(CONV_REPS)), 5),
            "P_boot": round(float(Ps.mean()), 4),
            "printed_as": [round(float(los.mean()), 2), round(float(his.mean()), 2)],
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
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
