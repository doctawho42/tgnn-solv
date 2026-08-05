#!/usr/bin/env python3
r"""SCORING PASS for the cross-fitted B_insuff^up pre-declaration.

The declaration is `scripts/analysis/run_b_insuff_crossfit_estimator.py'
(sha256 d158989fe9cfdc79b10a5a89a255761df42c07754bf763a611df001ae2caca1c, git-staged).  Nothing
in that file is altered by this one -- it is a separate module, and it IMPORTS the pinned
constants rather than restating them, so a drift between the declaration and the scoring is a
NameError rather than a silent disagreement.

What is run here is exactly Sec. 1-6 of the declaration and nothing else:

  * z* = [sigma_solute(51), A_solute, sigma_solvent(51), A_solvent, T_K], v_cosmo EXCLUDED;
  * RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=0);
  * 5-fold GroupKFold on pair_key (primary) and on source_doi (conservative);
  * rhat fitted GLOBALLY per (set, unit, scheme, model); within-stratum is a sensitivity;
  * both estimators printed for EVERY cell; the per-cell minimum is never formed;
  * the admissibility rule, the stratification, the maximality reduction, the bootstrap and the
    multiplicity null are imported unchanged from the deposited machinery.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_crossfit_scoring.py --stage all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

RDLogger.DisableLog("rdApp.*")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from run_b_insuff_estimator_grid import lotv, two_way_margin_boot            # noqa: E402
from run_b_insuff_stratified_map import (                                    # noqa: E402
    COARSE, MIN_BOUNDABLE, N_BINS, DDOF, N_BOOT, T_REF, prepare, stable_seed, strata_of,
    pair_unit, ADMISSIBILITY_RULE,
)
from run_b_insuff_map_multiplicity_null import (                             # noqa: E402
    OVERLAP_DEMOTION, build_strata, maximal_row_sets,
)
import run_b_insuff_crossfit_estimator as DECL                               # noqa: E402

OUTDIR = ROOT / "results" / "b_insuff"
DECL_PATH = ROOT / "scripts" / "analysis" / "run_b_insuff_crossfit_estimator.py"
DECL_SHA = "d158989fe9cfdc79b10a5a89a255761df42c07754bf763a611df001ae2caca1c"

RF_KWARGS = dict(DECL.RF_KWARGS)
RIDGE_ALPHA = DECL.RIDGE_ALPHA
N_SPLITS = DECL.N_SPLITS
RF_NJOBS = -1          # parallel tree construction only; the fitted forest is unchanged

BASELINE = dict(DECL.BASELINE)
GATE = dict(DECL.GATE)


# ==================================================================================================
# z*
# ==================================================================================================
def profile_table() -> tuple[dict, dict]:
    """VT-2005 profiles keyed by InChIKey; exact map and first-block map (the declared rule)."""
    sp = pd.read_csv(DECL.SIGMA)
    cols = [f"sigma_p_{i}" for i in range(DECL.SIGMA_BINS)]
    exact: dict[str, np.ndarray] = {}
    by14: dict[str, np.ndarray] = {}
    for rec in sp.itertuples(index=False):
        d = rec._asdict()
        mol = Chem.MolFromSmiles(str(d["smiles"]))
        if mol is None:
            continue
        ik = Chem.MolToInchiKey(mol)
        vec = np.array([float(d[c]) for c in cols] + [float(d["sigma_area"])], float)
        exact.setdefault(ik, vec)
        by14.setdefault(ik.split("-")[0], vec)
    return exact, by14


_IK_CACHE: dict[str, str | None] = {}


def _ik(smiles: str) -> str | None:
    s = str(smiles)
    if s not in _IK_CACHE:
        mol = Chem.MolFromSmiles(s)
        _IK_CACHE[s] = None if mol is None else Chem.MolToInchiKey(mol)
    return _IK_CACHE[s]


def resolve(smiles: str, exact: dict, by14: dict):
    ik = _ik(smiles)
    if ik is None:
        return None, None
    if ik in exact:
        return exact[ik], "exact"
    blk = ik.split("-")[0]
    if blk in by14:
        return by14[blk], "first_block"
    return None, None


def attach_zstar(df: pd.DataFrame, exact: dict, by14: dict) -> tuple[pd.DataFrame, np.ndarray, dict]:
    """Restrict to rows whose BOTH profiles resolve; return the restricted frame and z*."""
    keep, rows, rule_u, rule_v = [], [], [], []
    for su, sv, T in zip(df["solute_smiles"], df["solvent_smiles"], df["T_K"].astype(float)):
        a, ra = resolve(su, exact, by14)
        b, rb = resolve(sv, exact, by14)
        if a is None or b is None:
            keep.append(False)
            continue
        keep.append(True)
        rows.append(np.concatenate([a, b, [float(T)]]))
        rule_u.append(ra)
        rule_v.append(rb)
    keep = np.asarray(keep, bool)
    sub = df.loc[keep].reset_index(drop=True).copy()
    sub["zstar_rule_solute"] = rule_u
    sub["zstar_rule_solvent"] = rule_v
    Z = np.vstack(rows) if rows else np.zeros((0, 2 * (DECL.SIGMA_BINS + 1) + 1))
    dropped = df.loc[~keep]
    info = {
        "n_in": int(len(df)), "n_out": int(len(sub)), "n_dropped": int((~keep).sum()),
        "dropped_solutes": sorted(set(map(str, dropped["solute_smiles"]))),
        "dropped_sources": sorted(set(map(str, dropped["source_doi"]))),
        "zstar_dim": int(Z.shape[1]),
        "match_rule_solute": pd.Series(rule_u).value_counts().to_dict(),
        "match_rule_solvent": pd.Series(rule_v).value_counts().to_dict(),
    }
    return sub, Z, info


# ==================================================================================================
# the cross-fitted estimator
# ==================================================================================================
def splits_for(scheme: str, groups: np.ndarray):
    ng = len(np.unique(groups))
    if ng < 3:
        return None
    return list(GroupKFold(n_splits=min(N_SPLITS, ng)).split(np.arange(len(groups)),
                                                             groups=groups))


def oof_sq(Z: np.ndarray, m: np.ndarray, groups: np.ndarray, pair: np.ndarray,
           source: np.ndarray, model: str = "rf"):
    """Per-row out-of-fold squared residual + the G1 fold-integrity flags."""
    sp = splits_for("g", groups)
    if sp is None:
        return None, None
    oof = np.empty(len(m))
    leak_group = leak_pair = leak_src = False
    for tr, te in sp:
        if set(groups[tr]) & set(groups[te]):
            leak_group = True
        if set(pair[tr]) & set(pair[te]):
            leak_pair = True
        if set(source[tr]) & set(source[te]):
            leak_src = True
        if model == "rf":
            est = RandomForestRegressor(n_jobs=RF_NJOBS, **RF_KWARGS)
            est.fit(Z[tr], m[tr])
            oof[te] = est.predict(Z[te])
        else:
            sc = StandardScaler().fit(Z[tr])
            est = Ridge(alpha=RIDGE_ALPHA).fit(sc.transform(Z[tr]), m[tr])
            oof[te] = est.predict(sc.transform(Z[te]))
    gate = {"n_folds": len(sp), "n_groups": int(len(np.unique(groups))),
            "grouping_var_across_folds": bool(leak_group),
            "pair_across_folds": bool(leak_pair),
            "source_across_folds": bool(leak_src)}
    return (m - oof) ** 2, gate


# ==================================================================================================
# bootstrap -- the same two-way solute x solvent cluster resample, extended to carry fixed residuals
# ==================================================================================================
def two_way_boot_both(g, m, sq, solute, solvent, n_boot=N_BOOT, seed=0):
    """Numerically identical draws to run_b_insuff_estimator_grid.two_way_margin_boot; returns
    (P, lo, hi) for the coarsening and, when `sq' is given, for the cross-fit as well."""
    rng = np.random.default_rng(seed)
    su = np.array(sorted(set(solute)))
    sv = np.array(sorted(set(solvent)))
    iu = {s: i for i, s in enumerate(su)}
    iv = {s: i for i, s in enumerate(sv)}
    row_su = np.array([iu[s] for s in solute])
    row_sv = np.array([iv[s] for s in solvent])
    mb, mc = [], []
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, len(su), size=len(su)), minlength=len(su))
        cv = np.bincount(rng.integers(0, len(sv), size=len(sv)), minlength=len(sv))
        mult = cs[row_su] * cv[row_sv]
        if mult.sum() < 12:
            continue
        idx = np.repeat(np.arange(len(m)), mult)
        mm, gg = m[idx], g[idx]
        mse = float(np.mean((mm - gg) ** 2))
        mb.append(mse - 2.0 * lotv(gg, mm, N_BINS, DDOF))
        if sq is not None:
            mc.append(mse - 2.0 * float(np.mean(sq[idx])))
    out = {}
    for key, arr in (("bin", np.asarray(mb)), ("cf", np.asarray(mc))):
        if len(arr) == 0:
            out[key] = (None, None, None)
        else:
            out[key] = (float(np.mean(arr > 0)),
                        float(np.percentile(arr, 5)), float(np.percentile(arr, 95)))
    return out


# ==================================================================================================
# the map: every cell, both estimators
# ==================================================================================================
def measure_cell(g, m, sq, solute, solvent, boot=True, seed=0):
    n = len(m)
    mse = float(np.mean((m - g) ** 2))
    rec = {"n": int(n), "n_solutes": int(len(set(solute))), "n_solvents": int(len(set(solvent))),
           "mse": mse, "var_m": float(np.var(m, ddof=0)),
           "boundable_at_headline_cell": bool(n >= MIN_BOUNDABLE)}
    if n >= 2 * N_BINS:
        b = lotv(g, m, N_BINS, DDOF)
        rec["b_insuff_bin"] = b
        rec["margin_bin"] = mse - 2 * b
    else:
        rec["b_insuff_bin"] = rec["margin_bin"] = None
    if sq is not None:
        c = float(np.mean(sq))
        rec["b_insuff_cf"] = c
        rec["margin_cf"] = mse - 2 * c
        rec["oof_r2"] = float(1 - c / rec["var_m"]) if rec["var_m"] > 0 else None
    else:
        rec["b_insuff_cf"] = rec["margin_cf"] = rec["oof_r2"] = None
    if rec["b_insuff_bin"] is not None and rec["b_insuff_cf"] is not None:
        rec["delta_bin_minus_cf"] = rec["b_insuff_bin"] - rec["b_insuff_cf"]
        rec["cf_is_tighter"] = bool(rec["delta_bin_minus_cf"] > 0)
    else:
        rec["delta_bin_minus_cf"] = rec["cf_is_tighter"] = None
    rec["P_boot_bin"] = rec["P_boot_cf"] = None
    rec["ci90_bin"] = rec["ci90_cf"] = None
    if boot and n >= 2 * N_BINS and max(rec["n_solutes"], rec["n_solvents"]) >= 2:
        try:
            bb = two_way_boot_both(g, m, sq, np.asarray(solute), np.asarray(solvent), seed=seed)
            if bb["bin"][0] is not None:
                rec["P_boot_bin"] = bb["bin"][0]
                rec["ci90_bin"] = [bb["bin"][1], bb["bin"][2]]
            if bb["cf"][0] is not None:
                rec["P_boot_cf"] = bb["cf"][0]
                rec["ci90_cf"] = [bb["cf"][1], bb["cf"][2]]
        except Exception as exc:
            rec["boot_error"] = type(exc).__name__
    return rec


def deletion_curve(sub: pd.DataFrame, col: str, sq: np.ndarray | None,
                   base_bin: float | None, base_cf: float | None) -> list[dict]:
    """Leave-one-SOURCE-PUBLICATION-out for one stratum.  rhat is NOT refitted (declaration
    Sec. 1.3): the deletion acts on the EVALUATION set only, and the fixed per-row out-of-fold
    residuals are re-averaged over the remainder."""
    m = sub["m"].to_numpy(float)
    g = sub[col].to_numpy(float)
    src = sub["source_doi"].astype(str).to_numpy()
    out = []
    for s in sorted(set(src)):
        keep = src != s
        rec = {"left_out": s, "n_removed": int((~keep).sum()), "n_remaining": int(keep.sum()),
               "remainder_still_boundable": bool(keep.sum() >= MIN_BOUNDABLE)}
        if keep.sum() >= 2 * N_BINS:
            mm, gg = m[keep], g[keep]
            mse = float(np.mean((mm - gg) ** 2))
            b = lotv(gg, mm, N_BINS, DDOF)
            rec["margin_bin"] = mse - 2 * b
            rec["margin_cf"] = (mse - 2 * float(np.mean(sq[keep]))) if sq is not None else None
        else:
            rec["margin_bin"] = rec["margin_cf"] = None
        out.append(rec)
    return out


def verdict_from_curve(base: float | None, curve: list[dict], key: str,
                       boundable: bool) -> tuple[bool, bool, str]:
    """The admissibility rule, verbatim, applied to whichever estimator `key' names."""
    if base is None:
        return False, False, "the fixed cell is undefined at this n"
    n_src = len(curve)
    ev = [c for c in curve if c[key] is not None]
    bd = [c for c in ev if c["remainder_still_boundable"]]
    sgn = 1.0 if base > 0 else -1.0
    if n_src < 2:
        return False, False, f"one source publication ({curve[0]['left_out']}): sign never tested"
    if len(ev) < n_src:
        bad = [c["left_out"] for c in curve if c[key] is None]
        return False, False, (f"{len(bad)} of {n_src} deletions leave fewer than {2 * N_BINS} "
                              f"rows ({', '.join(bad)}): sign not verifiable")
    flips = [c for c in ev if c[key] * sgn <= 0]
    ok_b = not flips
    strict_b = ok_b and len(bd) == n_src
    if flips:
        why = "sign does not survive deletion of " + "; ".join(
            f"{c['left_out']} ({base:+.3f} -> {c[key]:+.3f})" for c in flips)
    elif not strict_b:
        why = (f"sign holds, but {n_src - len(bd)} of {n_src} deletions leave n < "
               f"{MIN_BOUNDABLE}: passes (b), fails its strict variant")
    else:
        why = ""
    if not boundable:
        why = (f"not boundable" + ("; " + why if why else ""))
    return ok_b, strict_b, why


def build_map(df: pd.DataFrame, conv: dict[str, str], sqmap: dict, label: str,
              boot: bool = True) -> tuple[list[dict], list[dict]]:
    """Every stratum x unit x convention, both estimators, plus the admissibility verdicts."""
    units = {"row": df.reset_index(drop=True),
             "pair": pair_unit(df).reset_index(drop=True)}
    cells, adm = [], []
    for uname, d in units.items():
        sq_full = sqmap.get(uname)
        for sname, lab, mask in strata_of(d):
            mm = np.asarray(mask.values if hasattr(mask, "values") else mask, bool)
            if mm.sum() == 0:
                continue
            sub = d[mm]
            sq = sq_full[mm] if sq_full is not None else None
            for cname, col in conv.items():
                seedv = stable_seed(label, uname, cname, f"{sname}::{lab}")
                rec = measure_cell(sub[col].to_numpy(float), sub["m"].to_numpy(float), sq,
                                   sub["solute_smiles"].to_numpy(),
                                   sub["solvent_smiles"].to_numpy(), boot=boot, seed=seedv)
                se = float(np.sum((sub["m"] - sub[col]) ** 2))
                se_tot = float(np.sum((d["m"] - d[col]) ** 2))
                rec.update(set=label, axis=sname, stratum=lab, unit=uname, convention=cname,
                           n_sources=int(sub["source_doi"].nunique()),
                           share_of_squared_error=se / se_tot,
                           share_of_rows=len(sub) / len(d))
                curve = deletion_curve(sub, col, sq, rec["margin_bin"], rec["margin_cf"])
                for key, tag in (("margin_bin", "bin"), ("margin_cf", "cf")):
                    okb, strict, why = verdict_from_curve(
                        rec[key], curve, key, rec["boundable_at_headline_cell"])
                    rec[f"loso_ok_{tag}"] = okb
                    rec[f"loso_strict_{tag}"] = strict
                    rec[f"admissible_{tag}"] = bool(rec["boundable_at_headline_cell"] and okb)
                    rec[f"admissible_strict_{tag}"] = bool(
                        rec["boundable_at_headline_cell"] and strict)
                    rec[f"reason_{tag}"] = why
                    ev = [c[key] for c in curve if c[key] is not None]
                    rec[f"loso_margin_min_{tag}"] = min(ev) if ev else None
                    rec[f"loso_margin_max_{tag}"] = max(ev) if ev else None
                rec["loso_curve"] = curve
                cells.append(rec)
    # rollups over the four cells of a stratum
    roll = defaultdict(list)
    for r in cells:
        roll[(r["axis"], r["stratum"])].append(r)
    for grp in roll.values():
        for tag in ("bin", "cf"):
            n_adm = sum(r[f"admissible_{tag}"] for r in grp)
            n_pos = sum((r[f"margin_{tag}"] or 0) > 0 for r in grp)
            for r in grp:
                r[f"cells_reported"] = len(grp)
                r[f"cells_admissible_{tag}"] = n_adm
                r[f"admissible_in_every_cell_{tag}"] = bool(n_adm == len(grp))
                r[f"positive_in_every_cell_{tag}"] = bool(n_pos == len(grp))
    return cells, adm


# ==================================================================================================
# the multiplicity null, re-run with either estimator
# ==================================================================================================
def cell_verdict_generic(idx, g, m, src, sq):
    gg, mm, ss = g[idx], m[idx], src[idx]
    n = len(mm)
    if n < 2 * N_BINS:
        return {"n": int(n), "margin": None, "boundable": bool(n >= MIN_BOUNDABLE),
                "admissible": False, "positive": None}

    def marg(sel):
        if sel.sum() < 2 * N_BINS:
            return None
        a, b = mm[sel], gg[sel]
        mse = float(np.mean((a - b) ** 2))
        if sq is None:
            return mse - 2.0 * lotv(b, a, N_BINS, DDOF)
        return mse - 2.0 * float(np.mean(sq[idx][sel]))

    all_sel = np.ones(n, bool)
    base = marg(all_sel)
    rec = {"n": int(n), "margin": base, "boundable": bool(n >= MIN_BOUNDABLE),
           "admissible": False, "positive": bool(base > 0)}
    sgn = 1.0 if base > 0 else -1.0
    srcs = np.unique(ss)
    if len(srcs) < 2:
        return rec
    for s in srcs:
        keep = ss != s
        v = marg(keep)
        if v is None or v * sgn <= 0:
            return rec
    rec["admissible"] = bool(rec["boundable"])
    return rec


def search_generic(row_class, row_coarse, row_fine, row_solfam, row_role,
                   units, srcs, gs, ms, sqs):
    n_adm = n_bnd = 0
    per = {}
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
                cells[f"{uname}::{cname}"] = cell_verdict_generic(
                    idx, gs[uname][cname], ms[uname], srcs[uname], sqs[uname])
        if len(cells) < 4:
            continue
        n_adm += sum(c["admissible"] for c in cells.values())
        n_bnd += sum(c["boundable"] and c["margin"] is not None for c in cells.values())
        per[name] = {
            "admissible_in_every_cell": all(c["admissible"] for c in cells.values()),
            "positive_in_every_cell": all(c["positive"] is True for c in cells.values()),
            "headline_margin": cells["row::res"]["margin"],
            "rows": frozenset(np.flatnonzero(msk_row).tolist()),
        }
    adm = [k for k, v in per.items() if v["admissible_in_every_cell"]]
    admpos = [k for k in adm if per[k]["positive_in_every_cell"]]
    cands = [(k, per[k]["rows"], per[k]["headline_margin"]) for k in admpos]
    maximal = maximal_row_sets(cands)
    return {
        "n_strata_searched": len(per),
        "A_cells_admissible": int(n_adm),
        "cells_boundable_with_a_margin": int(n_bnd),
        "B_strata_admissible_in_every_cell": len(adm),
        "B_names": sorted(adm),
        "B_distinct_row_sets": len({per[k]["rows"] for k in adm}),
        "C_distinct_row_sets_admissible_and_positive": len({c[1] for c in cands}),
        "C_names": sorted(admpos),
        "D_max_headline_margin_among_them": max((c[2] for c in cands), default=None),
        "maximal_row_sets": [{"stratum": k, "headline_margin": round(v, 4)} for k, v in maximal],
        "n_maximal": len(maximal),
    }


def run_null(broad: pd.DataFrame, conv: dict, sqmap: dict, n_draws: int, tag: str,
             use_cf: bool) -> dict:
    d = broad.reset_index(drop=True).copy()
    d["_dT"] = (d["T_K"] - T_REF).abs()
    d["_ord"] = np.arange(len(d))
    pair_rows = np.sort(d.sort_values(["pair_key", "_dT", "T_K", "_ord"])
                        .groupby("pair_key", sort=True).head(1)["_ord"].to_numpy())
    units = {"row": np.arange(len(d)), "pair": pair_rows}
    ms = {"row": d["m"].to_numpy(float), "pair": d["m"].to_numpy(float)[pair_rows]}
    gs = {u: {c: d[col].to_numpy(float)[sel] for c, col in conv.items()}
          for u, sel in units.items()}
    srcs = {u: d["source_doi"].astype(str).to_numpy()[sel] for u, sel in units.items()}
    sqs = ({u: sqmap[u] for u in units} if use_cf else {u: None for u in units})

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

    observed = search_generic(*rows_from(np.arange(len(solvents)), np.arange(len(solutes))),
                              units, srcs, gs, ms, sqs)
    rng = np.random.default_rng(20260805)          # the deposited null's seed, unchanged
    draws = []
    t0 = time.time()
    for i in range(n_draws):
        st = search_generic(*rows_from(rng.permutation(len(solvents)),
                                       rng.permutation(len(solutes))),
                            units, srcs, gs, ms, sqs)
        draws.append({k: st[k] for k in (
            "n_strata_searched", "A_cells_admissible", "cells_boundable_with_a_margin",
            "B_strata_admissible_in_every_cell", "B_distinct_row_sets",
            "C_distinct_row_sets_admissible_and_positive",
            "D_max_headline_margin_among_them", "n_maximal")})
        if (i + 1) % 200 == 0:
            print(f"  [{tag}] {i + 1}/{n_draws}  ({time.time() - t0:.0f}s)", flush=True)
    df = pd.DataFrame(draws)
    dmax = df["D_max_headline_margin_among_them"].to_numpy(float)
    finite = dmax[np.isfinite(dmax)]
    obs_c = observed["C_distinct_row_sets_admissible_and_positive"]
    obs_d = observed["D_max_headline_margin_among_them"]
    out = {
        "tag": tag, "estimator": "crossfit" if use_cf else "bin8", "n_draws": n_draws,
        "n_rows": int(len(d)),
        "observed": {k: v for k, v in observed.items()},
        "p_A": float(np.mean(df["A_cells_admissible"] >= observed["A_cells_admissible"])),
        "p_B": float(np.mean(df["B_strata_admissible_in_every_cell"]
                             >= observed["B_strata_admissible_in_every_cell"])),
        "p_C": float(np.mean(df["C_distinct_row_sets_admissible_and_positive"] >= obs_c))
        if obs_c is not None else None,
        "p_D": (float(np.mean(np.nan_to_num(dmax, nan=-np.inf) >= obs_d))
                if obs_d is not None else None),
        "p_D_given_a_certified_cell": (float(np.mean(finite >= obs_d))
                                       if (obs_d is not None and len(finite)) else None),
        "null_medians": {k: float(df[k].median()) for k in df.columns},
        "C_distribution": {str(k): int(v) for k, v in sorted(
            df["C_distinct_row_sets_admissible_and_positive"].value_counts().items())},
        "D_quantiles": {p: (round(float(np.percentile(finite, p)), 4) if len(finite) else None)
                        for p in (50, 90, 95, 99)},
        "n_draws_with_any_certified_cell": int(len(finite)),
    }
    return out


# ==================================================================================================
def jdump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))
    print(f"[saved] {path}")


def _clean(rec: dict) -> dict:
    return {k: (round(v, 6) if isinstance(v, float) else v)
            for k, v in rec.items() if k != "loso_curve"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all")
    ap.add_argument("--null-draws", type=int, default=2000)
    args = ap.parse_args()

    got = hashlib.sha256(DECL_PATH.read_bytes()).hexdigest()
    if got != DECL_SHA:
        raise SystemExit(f"DECLARATION ALTERED: {got} != {DECL_SHA}")
    print(f"[declaration] sha256 {got} verified")

    exact, by14 = profile_table()
    broad_all, conv = prepare(DECL.BROAD, "broad")
    corner_all, cconv = prepare(DECL.CORNER, "corner")
    broad, Zb, info_b = attach_zstar(broad_all, exact, by14)
    corner, Zc, info_c = attach_zstar(corner_all, exact, by14)
    print(f"[rows] broad {info_b['n_in']} -> {info_b['n_out']}   corner "
          f"{info_c['n_in']} -> {info_c['n_out']}   z* dim {info_b['zstar_dim']}")
    assert info_b["n_out"] == DECL.ROW_SET["broad_rows_with_zstar"], info_b
    assert info_c["n_out"] == DECL.ROW_SET["corner_rows"], info_c

    # ------------------------------------------------------------------ folds + oof residuals
    sets = {}
    for label, df, Z, cmap in (("broad_473", broad, Zb, conv), ("corner_60", corner, Zc, cconv)):
        units = {"row": (df.reset_index(drop=True), Z)}
        pu = pair_unit(df)
        units["pair"] = (pu.reset_index(drop=True), Z[pu.index.to_numpy()])
        blk = {"conv": cmap, "df": df, "units": {}}
        for uname, (d, Zu) in units.items():
            pairv = d["pair_key"].astype(str).to_numpy()
            srcv = d["source_doi"].astype(str).to_numpy()
            mv = d["m"].to_numpy(float)
            ent = {"df": d, "Z": Zu, "sq": {}, "gate": {}}
            for scheme, groups in (("pair", pairv), ("source", srcv)):
                for model in ("rf", "ridge"):
                    sq, gate = oof_sq(Zu, mv, groups, pairv, srcv, model)
                    ent["sq"][f"{scheme}/{model}"] = sq
                    if sq is not None:
                        gate = dict(gate)
                        gate["b_insuff_cf"] = float(np.mean(sq))
                        gate["oof_r2"] = float(1 - np.mean(sq) / np.var(mv))
                        gate["b_insuff_bin_res"] = lotv(
                            d[cmap["res"]].to_numpy(float), mv, N_BINS, DDOF)
                        gate["b_insuff_bin_full"] = lotv(
                            d[cmap["full"]].to_numpy(float), mv, N_BINS, DDOF)
                    ent["gate"][f"{scheme}/{model}"] = gate
            blk["units"][uname] = ent
        sets[label] = blk
        for uname, ent in blk["units"].items():
            for k, gt in ent["gate"].items():
                if gt:
                    print(f"[oof] {label:10s} {uname:4s} {k:12s} "
                          f"B_cf={gt['b_insuff_cf']:.4f} R2={gt['oof_r2']:+.4f} "
                          f"B_bin(res)={gt['b_insuff_bin_res']:.4f} "
                          f"folds={gt['n_folds']} groups={gt['n_groups']} "
                          f"leak(pair)={gt['pair_across_folds']}", flush=True)

    # --------------------------------------------------------------------------- THE GATE
    g0 = sets["broad_473"]["units"]["row"]["gate"]["pair/rf"]
    gate = {
        "evaluated_on": "broad_473 / row unit / pair-grouped folds / RF",
        "G1_no_pair_across_folds": bool(not g0["pair_across_folds"]),
        "G1_grouping_var_across_folds": bool(g0["grouping_var_across_folds"]),
        "G2_global_oof_r2": g0["oof_r2"],
        "G2_pass": bool(g0["oof_r2"] > GATE["G2_global_oof_r2_gt"]),
        "G3_b_insuff_cf": g0["b_insuff_cf"],
        "G3_threshold_pair_conditional_var": GATE["G3_not_below_pair_conditional_var"],
        "G3_pass": bool(g0["b_insuff_cf"] >= GATE["G3_not_below_pair_conditional_var"]),
    }
    gate["passes"] = bool(gate["G1_no_pair_across_folds"] and gate["G2_pass"] and gate["G3_pass"])
    gate["headline_estimator"] = "crossfit" if gate["passes"] else "bin8 (gate failed)"
    print("\n[GATE] " + json.dumps(gate, indent=1))

    out = {"declaration": {"file": str(DECL_PATH.relative_to(ROOT)), "sha256": DECL_SHA},
           "row_set": {"broad": info_b, "corner": info_c},
           "estimator": {"features": DECL.FEATURES, "excluded": DECL.EXCLUDED_FEATURE,
                         "rf": RF_KWARGS, "ridge_alpha": RIDGE_ALPHA, "n_splits": N_SPLITS,
                         "primary_group": DECL.PRIMARY_GROUP,
                         "conservative_group": DECL.CONSERVATIVE_GROUP,
                         "fit_scope": DECL.FIT_SCOPE},
           "coarsening_cell": {"n_bins": N_BINS, "ddof": DDOF, "min_boundable": MIN_BOUNDABLE},
           "admissibility_rule_unchanged": ADMISSIBILITY_RULE,
           "gate": gate,
           "baseline_on_disk_477_rows": BASELINE,
           "convention_independence_check": {},
           "oof_summary": {f"{lab}/{u}/{k}": v
                           for lab, blk in sets.items()
                           for u, ent in blk["units"].items()
                           for k, v in ent["gate"].items() if v}}

    # ------------------------------------------------------------------------------- the maps
    if args.stage in ("all", "map"):
        allcells = []
        for label, blk in sets.items():
            for scheme in ("pair", "source"):
                sqmap = {u: blk["units"][u]["sq"][f"{scheme}/rf"] for u in blk["units"]}
                cells, _ = build_map(blk["df"], blk["conv"], sqmap,
                                     label=f"{label}|{scheme}", boot=(scheme == "pair"))
                for c in cells:
                    c["fold_scheme"] = scheme
                    c["model"] = "rf"
                    c["set"] = label
                allcells += cells
                print(f"[map] {label} {scheme}-grouped: {len(cells)} cells", flush=True)
            # ridge sensitivity, primary folds, no bootstrap
            sqmap = {u: blk["units"][u]["sq"]["pair/ridge"] for u in blk["units"]}
            cells, _ = build_map(blk["df"], blk["conv"], sqmap, label=f"{label}|ridge", boot=False)
            for c in cells:
                c["fold_scheme"] = "pair"
                c["model"] = "ridge"
                c["set"] = label
            allcells += cells
        tab = pd.DataFrame([_clean(c) for c in allcells])
        tab.to_csv(OUTDIR / "crossfit_map_table.csv", index=False)
        print(f"[saved] {OUTDIR / 'crossfit_map_table.csv'}  ({len(tab)} rows)")
        jdump({**out, "cells": [_clean(c) for c in allcells]},
              OUTDIR / "crossfit_map.json")

    # ------------------------------------------------------------------------------ the null
    if args.stage in ("all", "null"):
        blk = sets["broad_473"]
        sqmap = {u: blk["units"][u]["sq"]["pair/rf"] for u in blk["units"]}
        nulls = {}
        for tag, use_cf, sm in (("bin8_473", False, sqmap), ("crossfit_473", True, sqmap)):
            nulls[tag] = run_null(blk["df"], blk["conv"], sm, args.null_draws, tag, use_cf)
            print(f"[null] {tag}: C={nulls[tag]['observed']['C_distinct_row_sets_admissible_and_positive']} "
                  f"p_C={nulls[tag]['p_C']} D={nulls[tag]['observed']['D_max_headline_margin_among_them']} "
                  f"p_D={nulls[tag]['p_D']}", flush=True)
        sqmap_src = {u: blk["units"][u]["sq"]["source/rf"] for u in blk["units"]}
        nulls["crossfit_473_source_folds"] = run_null(
            blk["df"], blk["conv"], sqmap_src, args.null_draws, "crossfit_473_src", True)
        jdump({**out, "nulls": nulls}, OUTDIR / "crossfit_multiplicity_null.json")

    # ------------------------------------------------- SENSITIVITY: within-stratum fit scope
    # Declared in Sec. 1.3 as a sensitivity that NEVER headlines: fitting rhat inside a 40-row
    # stratum hands a 105-dimensional regression forty rows.  Computed so its absence is not a
    # hole; the headline scope is the global fit above.
    if args.stage in ("all", "sens"):
        rows = []
        blk = sets["broad_473"]
        for uname, ent in blk["units"].items():
            d = ent["df"]
            Zu = ent["Z"]
            sq_glob = ent["sq"]["pair/rf"]
            for sname, lab, mask in strata_of(d):
                mm = np.asarray(mask.values if hasattr(mask, "values") else mask, bool)
                if mm.sum() < 2 * N_BINS:
                    continue
                sub = d[mm]
                pairv = sub["pair_key"].astype(str).to_numpy()
                srcv = sub["source_doi"].astype(str).to_numpy()
                mv = sub["m"].to_numpy(float)
                sq_w, gt = oof_sq(Zu[mm], mv, pairv, pairv, srcv, "rf")
                if sq_w is None:
                    continue
                rec = {"unit": uname, "axis": sname, "stratum": lab, "n": int(mm.sum()),
                       "boundable": bool(mm.sum() >= MIN_BOUNDABLE),
                       "b_insuff_cf_global": float(np.mean(sq_glob[mm])),
                       "b_insuff_cf_within": float(np.mean(sq_w)),
                       "oof_r2_within": float(1 - np.mean(sq_w) / np.var(mv))}
                for cname, col in blk["conv"].items():
                    g = sub[col].to_numpy(float)
                    mse = float(np.mean((mv - g) ** 2))
                    rec[f"b_insuff_bin_{cname}"] = lotv(g, mv, N_BINS, DDOF)
                    rec[f"margin_bin_{cname}"] = mse - 2 * rec[f"b_insuff_bin_{cname}"]
                    rec[f"margin_cf_global_{cname}"] = mse - 2 * rec["b_insuff_cf_global"]
                    rec[f"margin_cf_within_{cname}"] = mse - 2 * rec["b_insuff_cf_within"]
                rows.append(rec)
        sens = pd.DataFrame(rows)
        sens.round(6).to_csv(OUTDIR / "crossfit_within_stratum_sensitivity.csv", index=False)
        print(f"[saved] {OUTDIR / 'crossfit_within_stratum_sensitivity.csv'} ({len(sens)} rows)")
        b = sens[sens.boundable & (sens.unit == "row")]
        print("[sens] boundable row-unit strata: within-scope tighter than global in "
              f"{int((b.b_insuff_cf_within < b.b_insuff_cf_global).sum())}/{len(b)}; "
              f"tighter than the 8-bin coarsening (res) in "
              f"{int((b.b_insuff_cf_within < b.b_insuff_bin_res).sum())}/{len(b)}")

    (OUTDIR / "crossfit_declaration_sha256.txt").write_text(
        f"{DECL_SHA}  scripts/analysis/run_b_insuff_crossfit_estimator.py\n"
        f"{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}  "
        f"scripts/analysis/run_b_insuff_crossfit_scoring.py\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
