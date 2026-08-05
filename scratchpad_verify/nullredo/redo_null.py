#!/usr/bin/env python3
r"""REDO of the 59-stratum multiplicity null under the cross-fitted B_insuff^up.

Written independently of scripts/analysis/run_b_insuff_crossfit_scoring.py so that agreement with
its deposited numbers is a replication and not a tautology.  What is imported from that module is
ONLY the pinned estimator (profile table, z*, folds, out-of-fold residuals) -- re-deriving that
would risk deviating from the declaration.  The SEARCH is re-written here from the source of
scripts/analysis/run_b_insuff_map_multiplicity_null.py with exactly one line changed (the
B_insuff term), and the fidelity of that rewrite is PROVEN, not asserted:

    STEP 1  the rewritten search, run with sq=None, is compared to the ORIGINAL module's own
            `search' over the identical 2000 permutations on the identical rows, and every
            per-draw statistic must be equal.  If it is, the estimator hook is inert and the code
            path under the cross-fit is the original code path.

Everything else is the deposited machinery, imported: the chemistry-blind permutation of the
label triples over molecules, the stratum family, the admissibility rule, the maximality
reduction, the seed 20260805, the 2000 draws.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python redo_null.py [n_draws]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

ROOT = Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv")
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import run_b_insuff_map_multiplicity_null as ORIG                    # noqa: E402
from run_b_insuff_estimator_grid import lotv                          # noqa: E402
from run_b_insuff_stratified_map import (                             # noqa: E402
    COARSE, DDOF, MIN_BOUNDABLE, N_BINS, T_REF, pair_unit, prepare,
)
import run_b_insuff_crossfit_scoring as SCORE                         # noqa: E402
import run_b_insuff_crossfit_estimator as DECL                        # noqa: E402

OUT = Path(__file__).resolve().parent / "redo_null.json"
SEED = 20260805                      # the deposited null's seed, unchanged
DECL_SHA = "d158989fe9cfdc79b10a5a89a255761df42c07754bf763a611df001ae2caca1c"


# ==================================================================================================
# the search, re-written from run_b_insuff_map_multiplicity_null.py with ONE line changed
# ==================================================================================================
def _margin(gg, mm, sq_sub):
    """The fixed headline cell.  `sq_sub is None' -> the 8-bin coarsening, verbatim ORIG; else the
    mean of the FIXED per-row out-of-fold squared residuals over the same rows.  The
    `len < 2*N_BINS -> undefined' guard is KEPT under the cross-fit: declaration Sec. 6 keeps the
    admissibility rule verbatim, including the undefinedness clause."""
    if len(mm) < 2 * N_BINS:
        return None
    mse = float(np.mean((mm - gg) ** 2))
    b = lotv(gg, mm, N_BINS, DDOF) if sq_sub is None else float(np.mean(sq_sub))
    return mse - 2.0 * b


def cell_verdict(idx, g, m, src, sq):
    gg, mm, ss = g[idx], m[idx], src[idx]
    sqq = None if sq is None else sq[idx]
    n = len(mm)
    base = _margin(gg, mm, sqq)
    rec = {"n": int(n), "margin": base, "boundable": bool(n >= MIN_BOUNDABLE),
           "admissible": False, "positive": None}
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
        v = _margin(gg[keep], mm[keep], None if sqq is None else sqq[keep])
        if v * sgn <= 0:
            return rec
    rec["admissible"] = bool(rec["boundable"])
    return rec


def search(row_class, row_coarse, row_fine, row_solfam, row_role, units, srcs, gs, ms, sqs):
    n_cells_adm = n_cells_boundable = 0
    src_counts: list[int] = []
    per_stratum: dict[str, dict] = {}
    strata_row = ORIG.build_strata(row_class, row_coarse, row_fine, row_solfam, row_role,
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
                    idx, gs[uname][cname], ms[uname], srcs[uname], sqs[uname])
        if len(cells) < 4:
            continue
        n_cells_adm += sum(c["admissible"] for c in cells.values())
        n_cells_boundable += sum(c["boundable"] and c["margin"] is not None
                                 for c in cells.values())
        if cells["row::res"]["boundable"]:
            src_counts.append(int(len(np.unique(srcs["row"][np.flatnonzero(msk_row)]))))
        per_stratum[name] = {
            "admissible_in_every_cell": all(c["admissible"] for c in cells.values()),
            "positive_in_every_cell": all(c["positive"] is True for c in cells.values()),
            "headline_margin": cells["row::res"]["margin"],
            "rows": frozenset(np.flatnonzero(msk_row).tolist()),
        }
    adm = [k for k, v in per_stratum.items() if v["admissible_in_every_cell"]]
    admpos = [k for k in adm if per_stratum[k]["positive_in_every_cell"]]
    cands = [(k, per_stratum[k]["rows"], per_stratum[k]["headline_margin"]) for k in admpos]
    maximal = ORIG.maximal_row_sets(cands)
    return {
        "n_strata_searched": len(per_stratum),
        "A_cells_admissible": int(n_cells_adm),
        "cells_boundable_with_a_margin": int(n_cells_boundable),
        "loso_pass_rate_among_boundable_cells": (
            round(n_cells_adm / n_cells_boundable, 4) if n_cells_boundable else None),
        "median_sources_per_boundable_stratum": (
            float(np.median(src_counts)) if src_counts else None),
        "B_strata_admissible_in_every_cell": len(adm),
        "B_names": sorted(adm),
        "C_distinct_row_sets_admissible_and_positive": len({c[1] for c in cands}),
        "C_names": sorted(admpos),
        "D_max_headline_margin_among_them": max((c[2] for c in cands), default=None),
        "maximal_row_sets": [{"stratum": k, "headline_margin": round(v, 4)} for k, v in maximal],
        "n_maximal": len(maximal),
    }


# ==================================================================================================
# the harness: everything the permutation does not touch
# ==================================================================================================
def harness(df: pd.DataFrame, conv: dict):
    d = df.reset_index(drop=True).copy()
    dd = d.copy()
    dd["_dT"] = (dd["T_K"] - T_REF).abs()
    dd["_ord"] = np.arange(len(dd))
    pair_rows = np.sort(dd.sort_values(["pair_key", "_dT", "T_K", "_ord"])
                        .groupby("pair_key", sort=True).head(1)["_ord"].to_numpy())
    # the pair unit must be the map's own pair_unit(), or the fixed residual vector misaligns
    assert np.array_equal(pair_rows, np.sort(pair_unit(d).index.to_numpy())), "pair unit mismatch"
    units = {"row": np.arange(len(d)), "pair": pair_rows}
    ms = {"row": d["m"].to_numpy(float), "pair": d["m"].to_numpy(float)[pair_rows]}
    gs = {u: {c: d[col].to_numpy(float)[sel] for c, col in conv.items()}
          for u, sel in units.items()}
    srcs = {u: d["source_doi"].astype(str).to_numpy()[sel] for u, sel in units.items()}

    solvents = np.array(sorted(d["solvent_smiles"].unique()))
    solutes = np.array(sorted(d["solute_smiles"].unique()))
    sv_idx = pd.Series(np.arange(len(solvents)), index=solvents).reindex(
        d["solvent_smiles"]).to_numpy()
    su_idx = pd.Series(np.arange(len(solutes)), index=solutes).reindex(
        d["solute_smiles"]).to_numpy()
    sv_class = np.array([d.loc[d.solvent_smiles == s, "solvent_class"].iloc[0] for s in solvents])
    sv_fine = np.array([d.loc[d.solvent_smiles == s, "solvent_family"].iloc[0] for s in solvents])
    sv_coarse = np.array([COARSE[c] for c in sv_class])
    su_fam = np.array([d.loc[d.solute_smiles == s, "solute_family"].iloc[0] for s in solutes])
    su_role = np.where(su_fam == "water", "water_solute", "organic_solute")

    def rows_from(p_sv, p_su):
        return (sv_class[p_sv][sv_idx], sv_coarse[p_sv][sv_idx], sv_fine[p_sv][sv_idx],
                su_fam[p_su][su_idx], su_role[p_su][su_idx])

    return dict(d=d, units=units, ms=ms, gs=gs, srcs=srcs, rows_from=rows_from,
                n_sv=len(solvents), n_su=len(solutes))


def permutations(n_sv, n_su, n_draws):
    """The deposited draw sequence, materialised once so every estimator sees the same draws."""
    rng = np.random.default_rng(SEED)
    return [(rng.permutation(n_sv), rng.permutation(n_su)) for _ in range(n_draws)]


KEEP = ("n_strata_searched", "A_cells_admissible", "cells_boundable_with_a_margin",
        "loso_pass_rate_among_boundable_cells", "median_sources_per_boundable_stratum",
        "B_strata_admissible_in_every_cell", "C_distinct_row_sets_admissible_and_positive",
        "D_max_headline_margin_among_them", "n_maximal")


def run(h, sqs, perms, tag, use_orig=False):
    t0 = time.time()
    if use_orig:
        obs = ORIG.search(*h["rows_from"](np.arange(h["n_sv"]), np.arange(h["n_su"])),
                          h["units"], h["srcs"], h["gs"], h["ms"])
    else:
        obs = search(*h["rows_from"](np.arange(h["n_sv"]), np.arange(h["n_su"])),
                     h["units"], h["srcs"], h["gs"], h["ms"], sqs)
    draws = []
    for i, (a, b) in enumerate(perms):
        if use_orig:
            st = ORIG.search(*h["rows_from"](a, b), h["units"], h["srcs"], h["gs"], h["ms"])
        else:
            st = search(*h["rows_from"](a, b), h["units"], h["srcs"], h["gs"], h["ms"], sqs)
        draws.append({k: st[k] for k in KEEP})
        if (i + 1) % 500 == 0:
            print(f"  [{tag}] {i + 1}/{len(perms)}  ({time.time() - t0:.0f}s)", flush=True)
    return obs, pd.DataFrame(draws)


def summarise(obs, df, tag):
    dmax = df["D_max_headline_margin_among_them"].to_numpy(float)
    finite = dmax[np.isfinite(dmax)]
    cc = df["C_distinct_row_sets_admissible_and_positive"].to_numpy(int)
    obs_c = obs["C_distinct_row_sets_admissible_and_positive"]
    obs_d = obs["D_max_headline_margin_among_them"]

    def q(a, p):
        return round(float(np.percentile(a, p)), 4) if len(a) else None

    return {
        "tag": tag,
        "n_draws": int(len(df)),
        "observed": {k: v for k, v in obs.items() if k != "rows"},
        "p_A": round(float(np.mean(df["A_cells_admissible"] >= obs["A_cells_admissible"])), 4),
        "p_B": round(float(np.mean(df["B_strata_admissible_in_every_cell"]
                                   >= obs["B_strata_admissible_in_every_cell"])), 4),
        "p_C": round(float(np.mean(cc >= obs_c)), 4),
        "p_D": (round(float(np.mean(np.nan_to_num(dmax, nan=-np.inf) >= obs_d)), 4)
                if obs_d is not None else None),
        "p_D_given_a_certified_cell": (round(float(np.mean(finite >= obs_d)), 4)
                                       if (obs_d is not None and len(finite)) else None),
        "C_freq_at_least_one": round(float(np.mean(cc >= 1)), 4),
        "C_freq_at_least_two": round(float(np.mean(cc >= 2)), 4),
        "C_distribution": {str(k): int(v) for k, v in sorted(pd.Series(cc).value_counts().items())},
        "n_draws_with_any_certified_cell": int(len(finite)),
        "D_quantiles_over_certifying_draws": {str(p): q(finite, p)
                                              for p in (5, 25, 50, 75, 90, 95, 99)},
        "D_max": (round(float(finite.max()), 4) if len(finite) else None),
        "D_observed_minus_null_median": (
            round(float(obs_d - np.median(finite)), 4) if (obs_d is not None and len(finite))
            else None),
        "null_medians": {k: (None if df[k].isna().all() else float(df[k].median()))
                         for k in df.columns},
        "permissiveness_diagnostic": {
            "loso_pass_rate_among_boundable_cells_observed":
                obs["loso_pass_rate_among_boundable_cells"],
            "loso_pass_rate_among_boundable_cells_null_median":
                round(float(df["loso_pass_rate_among_boundable_cells"].median()), 4),
            "cells_boundable_with_a_margin_observed": obs["cells_boundable_with_a_margin"],
            "cells_boundable_with_a_margin_null_median":
                float(df["cells_boundable_with_a_margin"].median()),
            "median_sources_per_boundable_stratum_observed":
                obs["median_sources_per_boundable_stratum"],
            "median_sources_per_boundable_stratum_null_median":
                float(df["median_sources_per_boundable_stratum"].median()),
        },
    }


def main() -> int:
    n_draws = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    got = hashlib.sha256((ROOT / "scripts" / "analysis"
                          / "run_b_insuff_crossfit_estimator.py").read_bytes()).hexdigest()
    if got != DECL_SHA:
        raise SystemExit(f"DECLARATION ALTERED: {got}")
    print(f"[declaration] sha256 {got} verified")
    print("[scoring]     sha256", hashlib.sha256(
        (ROOT / "scripts" / "analysis" / "run_b_insuff_crossfit_scoring.py").read_bytes()
    ).hexdigest())
    print("[null src]    sha256", hashlib.sha256(
        (ROOT / "scripts" / "analysis" / "run_b_insuff_map_multiplicity_null.py").read_bytes()
    ).hexdigest())

    res: dict = {"n_draws": n_draws, "seed": SEED}

    # ------------------------------------------------------------------ the 477-row anchor
    broad477, conv = prepare(DECL.BROAD, "broad")
    h477 = harness(broad477, conv)
    perms477 = permutations(h477["n_sv"], h477["n_su"], n_draws)
    obs, df = run(h477, None, perms477, "bin8_477", use_orig=True)
    res["bin8_477"] = summarise(obs, df, "bin8_477 (ORIGINAL script's own search, unchanged)")
    print(f"[anchor 477] C={obs['C_distinct_row_sets_admissible_and_positive']} "
          f"p_C={res['bin8_477']['p_C']}  D={obs['D_max_headline_margin_among_them']:.4f} "
          f"p_D={res['bin8_477']['p_D']}", flush=True)

    # ------------------------------------------------------------------ the 473-row set + z*
    exact, by14 = SCORE.profile_table()
    broad, Zb, info_b = SCORE.attach_zstar(broad477, exact, by14)
    assert info_b["n_out"] == DECL.ROW_SET["broad_rows_with_zstar"] == 473, info_b
    res["row_set"] = {k: info_b[k] for k in ("n_in", "n_out", "n_dropped", "dropped_solutes",
                                             "zstar_dim")}
    print(f"[rows] {info_b['n_in']} -> {info_b['n_out']}  z* dim {info_b['zstar_dim']}")

    h = harness(broad, conv)
    pu = pair_unit(broad.reset_index(drop=True))
    Zu = {"row": Zb, "pair": Zb[pu.index.to_numpy()]}
    dfu = {"row": broad.reset_index(drop=True), "pair": pu.reset_index(drop=True)}
    assert np.array_equal(pu.index.to_numpy(), h["units"]["pair"]), "pair alignment"

    sq = {}
    gates = {}
    for scheme in ("pair", "source"):
        sq[scheme] = {}
        for u in ("row", "pair"):
            d = dfu[u]
            groups = d[{"pair": "pair_key", "source": "source_doi"}[scheme]].astype(str).to_numpy()
            s, gt = SCORE.oof_sq(Zu[u], d["m"].to_numpy(float), groups,
                                 d["pair_key"].astype(str).to_numpy(),
                                 d["source_doi"].astype(str).to_numpy(), "rf")
            sq[scheme][u] = s
            gt = dict(gt)
            gt["b_insuff_cf"] = float(np.mean(s))
            gt["oof_r2"] = float(1 - np.mean(s) / np.var(d["m"].to_numpy(float)))
            gates[f"{scheme}/{u}"] = gt
            print(f"[oof] {scheme:6s} {u:4s} B_cf={gt['b_insuff_cf']:.4f} "
                  f"R2={gt['oof_r2']:+.4f} folds={gt['n_folds']} groups={gt['n_groups']} "
                  f"leak(pair)={gt['pair_across_folds']}", flush=True)
    res["oof_gates"] = gates
    res["b_insuff_bin_473"] = {
        f"{u}/{c}": lotv(dfu[u][conv[c]].to_numpy(float), dfu[u]["m"].to_numpy(float),
                         N_BINS, DDOF)
        for u in ("row", "pair") for c in ("full", "res")}

    perms = permutations(h["n_sv"], h["n_su"], n_draws)

    # ---------------------------------------------- STEP 1: the fidelity proof, on all draws
    obs_o, df_o = run(h, None, perms, "FIDELITY orig", use_orig=True)
    obs_r, df_r = run(h, {"row": None, "pair": None}, perms, "FIDELITY rewrite")
    ident = {}
    for k in KEEP:
        a, b = df_o[k], df_r[k]
        ident[k] = bool(a.equals(b) or (a.isna() == b.isna()).all()
                        and np.allclose(a.dropna().to_numpy(float),
                                        b.dropna().to_numpy(float), rtol=0, atol=0))
    obs_same = all(obs_o[k] == obs_r[k] or (obs_o[k] is None and obs_r[k] is None) for k in KEEP)
    res["fidelity_rewrite_equals_original"] = {
        "per_draw_statistics_identical": ident,
        "all_identical": bool(all(ident.values())),
        "observed_identical": bool(obs_same),
        "n_draws_compared": n_draws,
        "what_this_proves": (
            "the estimator hook is inert when sq=None, so the cross-fitted run below differs from "
            "run_b_insuff_map_multiplicity_null.py in the B_insuff term and in nothing else"),
    }
    print(f"[fidelity] rewrite == original on all {n_draws} draws: "
          f"{res['fidelity_rewrite_equals_original']['all_identical']} "
          f"(observed identical: {obs_same})", flush=True)
    if not (all(ident.values()) and obs_same):
        raise SystemExit("FIDELITY FAILED -- the rewrite is not the original code path")

    res["bin8_473"] = summarise(obs_o, df_o, "bin8_473")
    frames = {"bin8_473": df_o}

    # ------------------------------------------------------- STEP 2: the cross-fitted nulls
    for scheme, tag in (("pair", "crossfit_473_pairfolds"), ("source", "crossfit_473_sourcefolds")):
        o, dfx = run(h, sq[scheme], perms, tag)
        res[tag] = summarise(o, dfx, tag)
        frames[tag] = dfx
        print(f"[{tag}] C={o['C_distinct_row_sets_admissible_and_positive']} "
              f"p_C={res[tag]['p_C']} D={o['D_max_headline_margin_among_them']} "
              f"p_D={res[tag]['p_D']}", flush=True)

    # ------------------------------------- the paired comparison (same permutations throughout)
    a, b = frames["bin8_473"], frames["crossfit_473_pairfolds"]
    ca = a["C_distinct_row_sets_admissible_and_positive"].to_numpy(int)
    cb = b["C_distinct_row_sets_admissible_and_positive"].to_numpy(int)
    da = np.nan_to_num(a["D_max_headline_margin_among_them"].to_numpy(float), nan=-np.inf)
    db = np.nan_to_num(b["D_max_headline_margin_among_them"].to_numpy(float), nan=-np.inf)
    oda = res["bin8_473"]["observed"]["D_max_headline_margin_among_them"]
    odb = res["crossfit_473_pairfolds"]["observed"]["D_max_headline_margin_among_them"]
    ea, eb = da >= oda, db >= odb
    res["paired_bin8_vs_crossfit"] = {
        "note": "the SAME 2000 permutations drive both columns, so these are paired counts",
        "C_null_mean_bin8": round(float(ca.mean()), 4),
        "C_null_mean_crossfit": round(float(cb.mean()), 4),
        "draws_C_up": int((cb > ca).sum()), "draws_C_down": int((cb < ca).sum()),
        "draws_C_same": int((cb == ca).sum()),
        "D_exceed_observed_both": int((ea & eb).sum()),
        "D_exceed_observed_bin8_only": int((ea & ~eb).sum()),
        "D_exceed_observed_crossfit_only": int((~ea & eb).sum()),
        "D_exceed_observed_neither": int((~ea & ~eb).sum()),
        "mcnemar_discordant_b_minus_c": int((~ea & eb).sum() - (ea & ~eb).sum()),
        "null_certification_rate_bin8": round(float(np.mean(ca >= 1)), 4),
        "null_certification_rate_crossfit": round(float(np.mean(cb >= 1)), 4),
    }

    OUT.write_text(json.dumps(res, indent=2, default=str))
    print(f"\n[saved] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
