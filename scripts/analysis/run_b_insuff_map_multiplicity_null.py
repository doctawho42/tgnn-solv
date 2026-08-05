#!/usr/bin/env python3
r"""A multiplicity null for the 59-stratum search: how often does the rule certify by chance?

WHY THIS EXISTS.  The map of scripts/analysis/run_b_insuff_stratified_map.py searches 59 strata
and states one of them.  The admissibility rule (boundable at the fixed cell, plus sign-stability
under deletion of each contributing publication, in all four unit x convention cells) is a
STABILITY filter; it is not a multiplicity correction, and the manuscript's limitation (vi) says
so.  This script supplies the missing null: it asks how often a CHEMICALLY BLIND stratification of
the same rows, searched the same way, certifies at least one cell -- and how large the largest
certified margin gets by chance.

THE NULL.  Not a permutation of the rows into blocks: that would destroy the molecule-level
clustering that makes a stratum a stratum, and it would put every publication into every block.
Instead the LABELS are permuted over MOLECULES, which is the chemically blind version of the same
search:

  * each of the 36 solvents keeps its rows and its identity, and receives the label TRIPLE
    (nine-class, coarse, fine family) of a uniformly drawn other solvent, the triple moving
    together so that the nesting between granularities is exactly preserved;
  * each of the 78 solutes likewise receives another solute's (family, role) PAIR;
  * the whole stratum family is then rebuilt from the permuted labels by the same code path --
    the same nine classes, the same five coarse classes, the same fine families, the same two
    solute roles, the same solute families, the same cross-tab -- so the search that is run
    against the null is the search that was run against the chemistry.

Preserved by construction: the number of strata at every granularity, the number of MOLECULES per
stratum, the containment lattice between granularities, and every row's (m, g, source, pair).
Destroyed: the association between chemistry and error, which is the thing under test.

WHAT IS COUNTED.  Per draw, the full pipeline: margin at the fixed cell in all four
unit x convention cells, boundability at n >= 40, leave-one-source-publication-out in every cell,
the admissibility verdict, positivity in all four cells, reduction to distinct row sets, and the
maximality filter.  Four statistics come out, and the observed value of each is computed by the
same code on the true labels:

  A  cells admissible                     (stratum x unit x convention)
  B  strata admissible in all four cells
  C  DISTINCT ROW SETS among those that are also positive in all four cells   <- observed 2
  D  the largest headline-cell margin among them                             <- observed +2.04

C is the referee's question -- how often does a chemically blind partition license anything at
all -- and D is the question the single finding actually poses, since that finding is by
construction the survivor of a search and is quoted at a magnitude.

WHAT THIS NULL CANNOT DO.  Admissibility depends on the SOURCE structure, and sources are
chemistry-correlated -- a publication measures a related set of solvents -- so permuting the
chemistry labels does not leave the provenance structure alone.  Whether that makes the null
permissive or strict is not something to argue, so it is MEASURED
(`is_the_null_permissive_on_the_deletion_test'), and the two effects it finds run in opposite
directions: a label-permuted map has MORE boundable cells than the chemical one, and each passes
the deletion test LESS often.  The reported frequency is therefore not signed, and it is not an
upper or a lower bound on a chance rate.  The exactly matched null would permute chemistry and
provenance jointly, which this design cannot do because the two are confounded in the data; that
is the limit of what can be built here.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_map_multiplicity_null.py [n_draws]
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from run_b_insuff_estimator_grid import lotv  # noqa: E402
from run_b_insuff_stratified_map import (  # noqa: E402
    COARSE, MIN_BOUNDABLE, N_BINS, T_REF, prepare,
)

OUT = ROOT / "results" / "b_insuff" / "map_multiplicity_null.json"
N_DRAWS = 2000
DDOF = 1                      # the fixed cell: 8 equal-count bins, Bessel within-bin variance
OVERLAP_DEMOTION = 0.5        # see `maximal_row_sets'


def margin_at_fixed_cell(g: np.ndarray, m: np.ndarray) -> float | None:
    if len(m) < 2 * N_BINS:
        return None
    return float(np.mean((m - g) ** 2)) - 2.0 * lotv(g, m, N_BINS, DDOF)


def cell_verdict(idx: np.ndarray, g: np.ndarray, m: np.ndarray,
                 src: np.ndarray, n_src_total: int) -> dict:
    """One (stratum, unit, convention) cell: the margin, boundability and the deletion test,
    exactly as scripts/analysis/run_b_insuff_stratified_map.py applies them."""
    gg, mm, ss = g[idx], m[idx], src[idx]
    n = len(mm)
    base = margin_at_fixed_cell(gg, mm)
    rec = {"n": int(n), "margin": base,
           "boundable": bool(n >= MIN_BOUNDABLE), "admissible": False, "positive": None}
    if base is None:
        return rec
    rec["positive"] = bool(base > 0)
    sgn = 1.0 if base > 0 else -1.0
    srcs = np.unique(ss)
    if len(srcs) < 2:                       # one publication: the sign was never put at risk
        return rec
    for s in srcs:
        keep = ss != s
        if keep.sum() < 2 * N_BINS:         # deletion leaves the fixed cell undefined
            return rec
        v = margin_at_fixed_cell(gg[keep], mm[keep])
        if v * sgn <= 0:                    # sign does not survive this deletion
            return rec
    rec["admissible"] = bool(rec["boundable"])
    return rec


def maximal_row_sets(cands: list[tuple[str, frozenset, float]]) -> list[tuple[str, float]]:
    """The paper's last reduction, made explicit.  Among the admissible positive strata, identical
    row sets are one finding; a set that is contained in another, or that overlaps another larger
    set by more than OVERLAP_DEMOTION of its own rows, is not independent evidence and is demoted
    to that other set.  What survives is what may be stated."""
    uniq: dict[frozenset, tuple[str, float]] = {}
    for name, rows, marg in cands:
        if rows not in uniq or marg > uniq[rows][1]:
            uniq[rows] = (name, marg)
    keys = list(uniq)
    out = []
    for a in keys:
        dominated = False
        for b in keys:
            if a is b or a == b:
                continue
            if len(b) < len(a):
                continue
            if a <= b or len(a & b) / len(a) > OVERLAP_DEMOTION:
                dominated = True
                break
        if not dominated:
            out.append((uniq[a][0], uniq[a][1]))
    return sorted(out, key=lambda kv: -kv[1])


def build_strata(row_class: np.ndarray, row_coarse: np.ndarray, row_fine: np.ndarray,
                 row_solfam: np.ndarray, row_role: np.ndarray,
                 n: int) -> list[tuple[str, np.ndarray]]:
    """The same stratum family as the map: whole set, three solvent granularities, two solute
    levels, and the cross-tab of the nine-class solvent axis with the solute role."""
    out: list[tuple[str, np.ndarray]] = [("whole_set::all", np.ones(n, bool))]
    for axis, col in (("solvent_class", row_class), ("solvent_class_coarse", row_coarse),
                      ("solvent_family_fine", row_fine), ("solute_role", row_role),
                      ("solute_family", row_solfam)):
        for lab in np.unique(col):
            out.append((f"{axis}::{lab}", col == lab))
    for lab in np.unique(row_class):
        for role in np.unique(row_role):
            msk = (row_class == lab) & (row_role == role)
            if msk.any():
                out.append((f"solvent_class_x_solute_role::{lab} | {role}", msk))
    return out


def search(row_class, row_coarse, row_fine, row_solfam, row_role,
           units: dict, srcs: dict, gs: dict, ms: dict) -> dict:
    """One full pass of the search: every stratum, every unit x convention cell, the rule."""
    n_cells_adm = n_cells_boundable = 0
    src_counts: list[int] = []
    per_stratum: dict[str, dict] = {}
    strata_row = build_strata(row_class, row_coarse, row_fine, row_solfam, row_role,
                              len(units["row"]))
    for name, msk_row in strata_row:
        cells = {}
        for uname, sel in units.items():
            msk = msk_row if uname == "row" else msk_row[sel]
            idx = np.flatnonzero(msk)
            if len(idx) == 0:
                continue
            for cname in ("full", "res"):
                cells[f"{uname}::{cname}"] = cell_verdict(
                    idx, gs[uname][cname], ms[uname], srcs[uname], 0)
        if len(cells) < 4:
            continue
        n_cells_adm += sum(c["admissible"] for c in cells.values())
        n_cells_boundable += sum(c["boundable"] and c["margin"] is not None
                                 for c in cells.values())
        if cells["row::res"]["boundable"]:
            src_counts.append(int(len(np.unique(srcs["row"][np.flatnonzero(msk_row)]))))
        per_stratum[name] = {
            "cells": cells,
            "admissible_in_every_cell": all(c["admissible"] for c in cells.values()),
            "positive_in_every_cell": all(c["positive"] is True for c in cells.values()),
            "headline_margin": cells["row::res"]["margin"],
            "rows": frozenset(np.flatnonzero(msk_row).tolist()),
        }
    adm = [k for k, v in per_stratum.items() if v["admissible_in_every_cell"]]
    admpos = [k for k in adm if per_stratum[k]["positive_in_every_cell"]]
    cands = [(k, per_stratum[k]["rows"], per_stratum[k]["headline_margin"]) for k in admpos]
    distinct = {c[1] for c in cands}
    maximal = maximal_row_sets(cands)
    return {
        "n_strata_searched": len(per_stratum),
        "A_cells_admissible": int(n_cells_adm),
        # the permissiveness diagnostic: how often the deletion test is passed among the cells
        # it can act on, and how many publications a boundable stratum draws on.  Measured
        # rather than argued, because the direction of the null's bias turns on it.
        "cells_boundable_with_a_margin": int(n_cells_boundable),
        "loso_pass_rate_among_boundable_cells": (
            round(n_cells_adm / n_cells_boundable, 4) if n_cells_boundable else None),
        "median_sources_per_boundable_stratum": (
            float(np.median(src_counts)) if src_counts else None),
        "B_strata_admissible_in_every_cell": len(adm),
        "B_names": sorted(adm),
        "C_distinct_row_sets_admissible_and_positive": len(distinct),
        "C_names": sorted(admpos),
        "D_max_headline_margin_among_them": (max((c[2] for c in cands), default=None)),
        "maximal_row_sets": [{"stratum": k, "headline_margin": round(v, 4)} for k, v in maximal],
        "n_maximal": len(maximal),
    }


def main() -> int:
    n_draws = int(sys.argv[1]) if len(sys.argv) > 1 else N_DRAWS
    broad, conv = prepare(ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv", "broad")
    broad = broad.reset_index(drop=True)

    # the pair unit: one row per pair, nearest T_REF -- independent of the labels, so it is
    # computed once and re-used at every draw
    d = broad.copy()
    d["_dT"] = (d["T_K"] - T_REF).abs()
    d["_ord"] = np.arange(len(d))
    pair_rows = np.sort(d.sort_values(["pair_key", "_dT", "T_K", "_ord"])
                        .groupby("pair_key", sort=True).head(1)["_ord"].to_numpy())

    units = {"row": np.arange(len(broad)), "pair": pair_rows}
    ms = {"row": broad["m"].to_numpy(float), "pair": broad["m"].to_numpy(float)[pair_rows]}
    gs = {u: {c: broad[col].to_numpy(float)[sel] for c, col in conv.items()}
          for u, sel in units.items()}
    srcs = {u: broad["source_doi"].astype(str).to_numpy()[sel] for u, sel in units.items()}

    # molecule-level label vectors, moved as blocks so the granularity nesting is preserved
    solvents = np.array(sorted(broad["solvent_smiles"].unique()))
    solutes = np.array(sorted(broad["solute_smiles"].unique()))
    sv_idx = pd.Series(np.arange(len(solvents)), index=solvents).reindex(
        broad["solvent_smiles"]).to_numpy()
    su_idx = pd.Series(np.arange(len(solutes)), index=solutes).reindex(
        broad["solute_smiles"]).to_numpy()

    sv_class = np.array([broad.loc[broad.solvent_smiles == s, "solvent_class"].iloc[0]
                         for s in solvents])
    sv_fine = np.array([broad.loc[broad.solvent_smiles == s, "solvent_family"].iloc[0]
                        for s in solvents])
    sv_coarse = np.array([COARSE[c] for c in sv_class])
    su_fam = np.array([broad.loc[broad.solute_smiles == s, "solute_family"].iloc[0]
                       for s in solutes])
    su_role = np.where(su_fam == "water", "water_solute", "organic_solute")

    def rows_from(perm_sv: np.ndarray, perm_su: np.ndarray):
        return (sv_class[perm_sv][sv_idx], sv_coarse[perm_sv][sv_idx], sv_fine[perm_sv][sv_idx],
                su_fam[perm_su][su_idx], su_role[perm_su][su_idx])

    ident_sv, ident_su = np.arange(len(solvents)), np.arange(len(solutes))
    observed = search(*rows_from(ident_sv, ident_su), units, srcs, gs, ms)
    print("[observed]", json.dumps({k: v for k, v in observed.items()
                                    if k not in ("B_names", "C_names")}, default=str))
    print("[observed] admissible:", observed["B_names"])
    print("[observed] admissible and positive:", observed["C_names"])
    print("[observed] maximal:", observed["maximal_row_sets"])

    rng = np.random.default_rng(20260805)
    draws = []
    for i in range(n_draws):
        st = search(*rows_from(rng.permutation(len(solvents)), rng.permutation(len(solutes))),
                    units, srcs, gs, ms)
        draws.append({k: st[k] for k in (
            "n_strata_searched", "A_cells_admissible", "cells_boundable_with_a_margin",
            "loso_pass_rate_among_boundable_cells", "median_sources_per_boundable_stratum",
            "B_strata_admissible_in_every_cell",
            "C_distinct_row_sets_admissible_and_positive",
            "D_max_headline_margin_among_them", "n_maximal")})
        if (i + 1) % 250 == 0:
            print(f"  ... {i + 1}/{n_draws}", flush=True)

    df = pd.DataFrame(draws)
    dmax = df["D_max_headline_margin_among_them"].to_numpy(float)
    finite = dmax[np.isfinite(dmax)]

    def q(a, p):
        return round(float(np.percentile(a, p)), 4) if len(a) else None

    obs_d = float(observed["D_max_headline_margin_among_them"])
    out = {
        "design": __doc__,
        "n_draws": n_draws,
        "fixed_cell": {"n_bins": N_BINS, "within_bin_variance": "Bessel (ddof=1)",
                       "boundable_iff_n_at_least": MIN_BOUNDABLE,
                       "cells": ["row::full", "row::res", "pair::full", "pair::res"]},
        "overlap_demotion_threshold": OVERLAP_DEMOTION,
        "observed": {k: v for k, v in observed.items() if k != "rows"},
        "null": {
            "n_strata_searched": {"median": float(df["n_strata_searched"].median()),
                                  "min": int(df["n_strata_searched"].min()),
                                  "max": int(df["n_strata_searched"].max())},
            "A_cells_admissible": {
                "observed": observed["A_cells_admissible"],
                "median": float(df["A_cells_admissible"].median()),
                "p90": q(df["A_cells_admissible"].to_numpy(), 90),
                "p_at_least_observed": round(float(np.mean(
                    df["A_cells_admissible"] >= observed["A_cells_admissible"])), 4)},
            "is_the_null_permissive_on_the_deletion_test": {
                "why_it_matters": (
                    "if a label-permuted stratum passes leave-one-source-out more easily than a "
                    "chemical one, the null certifies more often than chance would under the "
                    "chemistry and every frequency below is an over-estimate; if it passes less "
                    "easily, they are under-estimates. This measures the direction instead of "
                    "arguing it."),
                "loso_pass_rate_among_boundable_cells_observed":
                    observed["loso_pass_rate_among_boundable_cells"],
                "loso_pass_rate_among_boundable_cells_null_median": round(float(
                    df["loso_pass_rate_among_boundable_cells"].median()), 4),
                "cells_boundable_with_a_margin_observed":
                    observed["cells_boundable_with_a_margin"],
                "cells_boundable_with_a_margin_null_median": float(
                    df["cells_boundable_with_a_margin"].median()),
                "median_sources_per_boundable_stratum_observed":
                    observed["median_sources_per_boundable_stratum"],
                "median_sources_per_boundable_stratum_null_median": float(
                    df["median_sources_per_boundable_stratum"].median())},
            "B_strata_admissible_in_every_cell": {
                "observed": observed["B_strata_admissible_in_every_cell"],
                "median": float(df["B_strata_admissible_in_every_cell"].median()),
                "p_at_least_observed": round(float(np.mean(
                    df["B_strata_admissible_in_every_cell"]
                    >= observed["B_strata_admissible_in_every_cell"])), 4),
                "frequency_at_least_one": round(float(np.mean(
                    df["B_strata_admissible_in_every_cell"] >= 1)), 4)},
            "C_distinct_row_sets_admissible_and_positive": {
                "observed": observed["C_distinct_row_sets_admissible_and_positive"],
                "median": float(df["C_distinct_row_sets_admissible_and_positive"].median()),
                "frequency_at_least_one": round(float(np.mean(
                    df["C_distinct_row_sets_admissible_and_positive"] >= 1)), 4),
                "frequency_at_least_two": round(float(np.mean(
                    df["C_distinct_row_sets_admissible_and_positive"] >= 2)), 4),
                "p_at_least_observed": round(float(np.mean(
                    df["C_distinct_row_sets_admissible_and_positive"]
                    >= observed["C_distinct_row_sets_admissible_and_positive"])), 4),
                "distribution": {str(k): int(v) for k, v in sorted(
                    df["C_distinct_row_sets_admissible_and_positive"]
                    .value_counts().items())}},
            "D_max_headline_margin_among_them": {
                "observed": round(obs_d, 4),
                "n_draws_with_any_certified_cell": int(len(finite)),
                "median_over_draws_with_one": q(finite, 50),
                "p90": q(finite, 90), "p95": q(finite, 95), "p99": q(finite, 99),
                "max": (round(float(finite.max()), 4) if len(finite) else None),
                "p_at_least_observed_over_all_draws": round(
                    float(np.mean(np.nan_to_num(dmax, nan=-np.inf) >= obs_d)), 4),
                "p_at_least_observed_given_a_certified_cell": (
                    round(float(np.mean(finite >= obs_d)), 4) if len(finite) else None)},
            "n_maximal": {
                "observed": observed["n_maximal"],
                "median": float(df["n_maximal"].median()),
                "frequency_at_least_one": round(float(np.mean(df["n_maximal"] >= 1)), 4),
                "p_at_least_observed": round(float(np.mean(
                    df["n_maximal"] >= observed["n_maximal"])), 4)},
        },
        "how_to_read_this": (
            "The rule is a stability filter, so the count statistics A-C measure how often a "
            "chemically blind search licenses ANYTHING; they do not measure how often it licenses "
            "something of the observed SIZE. Because the set taken whole has a positive margin at "
            "this cell, a random stratum inherits a positive margin on average, and a null "
            "frequency near one for `at least one certified cell' is expected and is not evidence "
            "against the rule. The statistic that matches the claim -- one stratum, stated at a "
            "magnitude, as the survivor of a 59-fold search -- is D."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print("\n[null]", json.dumps(out["null"], indent=2, default=str))
    print(f"[saved] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
