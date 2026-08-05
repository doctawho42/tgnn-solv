#!/usr/bin/env python3
"""FINAL ranking analysis of the sigma-grounding paradox, three seeds, three fixes.

Fixes over rank_e5.py / rank_e5_floors.py:
  (1) seed 44 INCLUDED  -- its oracle deposit was repaired 2026-08-05 (8103 rows).
  (2) the shuffled-profile ("donor") floor is built SEPARATELY FOR EACH ARM from that
      arm's own predictions.  The old code built it once from the oracle arm and
      subtracted it from both, although the arms differ ~2x in within-group spread.
  (3) the level-only rejection is redone with per-group AFFINE recalibration
      (slope AND intercept fitted per group), not a per-group offset.

Preserved: mixed-coverage exclusion, leave-one-solute-out jackknife, same-arm seed
replicate noise, permutation floor, solute-blind label-marginal floor.

Outputs <out>/rank_final.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

REPO = Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv")
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
BASE = REPO / "results/e5_sigma_grounding"
SIGMA_ART = REPO / "results/sigma_profile_artifact/sigma_profiles.csv"

MIN_SOLVENTS = 3
T_TOL = 1.0
NDCG_K = 3
KEY = ["solute_smiles", "solvent_smiles", "T6"]
SEEDS = (42, 43, 44)
ARMS = ["grounded_a", "oracle", "directgnn", "ungrounded", "nrtl"]
RNG = np.random.default_rng(20260806)


# ------------------------------------------------------------------ fast metrics
def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    da, db = np.sqrt((a * a).sum()), np.sqrt((b * b).sum())
    if da == 0 or db == 0:
        return float("nan")
    return float((a * b).sum() / (da * db))


def _taub(t: np.ndarray, p: np.ndarray) -> float:
    dt = np.sign(t[:, None] - t[None, :])
    dp = np.sign(p[:, None] - p[None, :])
    iu = np.triu_indices(len(t), 1)
    st, sp = dt[iu], dp[iu]
    num = float((st * sp).sum())
    n0 = len(st)
    n1 = float((st == 0).sum())
    n2 = float((sp == 0).sum())
    den = np.sqrt((n0 - n1) * (n0 - n2))
    return float(num / den) if den > 0 else float("nan")


def _ndcg_from(rel: np.ndarray, pred: np.ndarray, disc: np.ndarray, idcg: float, k: int) -> float:
    order_pred = np.argsort(-pred)[:k]
    dcg = float(((2.0 ** rel[order_pred] - 1.0) * disc).sum())
    return dcg / idcg if idcg > 0 else float("nan")


class GroupCtx:
    """Precomputed per-group truth quantities so a floor draw costs almost nothing."""

    __slots__ = ("t", "rt", "rel", "disc", "idcg", "k", "argmax_t", "n")

    def __init__(self, t: np.ndarray):
        self.t = t
        self.n = len(t)
        self.rt = rankdata(t)
        self.rel = t.argsort().argsort().astype(float)  # verbatim run_ranking_eval._ndcg
        self.k = min(NDCG_K, self.n)
        self.disc = 1.0 / np.log2(np.arange(2, self.k + 2))
        order_ideal = np.argsort(-self.rel)[: self.k]
        self.idcg = float(((2.0 ** self.rel[order_ideal] - 1.0) * self.disc).sum())
        self.argmax_t = int(np.argmax(t))


def metrics(ctx: GroupCtx, p: np.ndarray) -> dict:
    rp = rankdata(p)
    return {
        "spearman": _pearson(ctx.rt, rp),
        "kendall": _taub(ctx.t, p),
        "top1": float(int(np.argmax(p)) == ctx.argmax_t),
        "ndcg": _ndcg_from(ctx.rel, p, ctx.disc, ctx.idcg, ctx.k),
        "argmax_pred": int(np.argmax(p)),
    }


METRICS = ("spearman", "kendall", "top1", "ndcg")


# ------------------------------------------------------------------ data loading
def load_arm(seed: int, arm: str) -> pd.DataFrame:
    df = pd.read_csv(BASE / f"seed_{seed}" / f"{arm}_predictions.csv", low_memory=False)
    df["T6"] = df["T"].round(6)
    sup = df["has_solubility"].astype(str).str.strip().str.lower().isin({"true", "1", "1.0"})
    df = df[sup].drop_duplicates(KEY, keep="first").copy()
    df["Tr"] = (pd.to_numeric(df["T"], errors="coerce") / T_TOL).round() * T_TOL
    return df


def build_groups(frames: dict[str, pd.DataFrame]) -> tuple[list, dict]:
    coll = {
        arm: df.groupby(["solute_smiles", "Tr", "solvent_smiles"]).agg(
            t=("ln_x2_true", "mean"), p=("ln_x2_pred", "mean")).sort_index()
        for arm, df in frames.items()
    }
    ref = coll["grounded_a"]
    groups, info = [], {"n_groups_all": 0, "dropped_true_const": 0}
    for (sol, tr), grp in ref.groupby(level=[0, 1]):
        solvents = sorted(grp.index.get_level_values(2).tolist())
        if len(solvents) < MIN_SOLVENTS:
            continue
        info["n_groups_all"] += 1
        t = grp.droplevel([0, 1]).reindex(solvents)["t"].to_numpy(float)
        if np.std(t) == 0:
            info["dropped_true_const"] += 1
            continue
        preds = {a: coll[a].loc[(sol, tr)].reindex(solvents)["p"].to_numpy(float) for a in frames}
        groups.append({"solute": sol, "T": float(tr), "solvents": solvents,
                       "t": t, "preds": preds, "ctx": GroupCtx(t)})
    return groups, info


# ------------------------------------------------------------------ tables / stats
def arm_table(groups: list, arm: str) -> pd.DataFrame:
    rows = []
    for i, g in enumerate(groups):
        p = g["preds"][arm]
        r = {"gi": i, "solute": g["solute"], "T": g["T"], "n": len(g["solvents"]),
             "pred_const": bool(np.std(p) == 0)}
        r.update(metrics(g["ctx"], p))
        rows.append(r)
    return pd.DataFrame(rows)


def cluster_boot(diff: np.ndarray, solute: np.ndarray, n_boot: int = 4000) -> dict:
    """Bootstrap the mean of `diff` resampling SOLUTE clusters with replacement."""
    ok = np.isfinite(diff)
    diff, solute = diff[ok], solute[ok]
    uniq, inv = np.unique(solute, return_inverse=True)
    ns = len(uniq)
    sums = np.bincount(inv, weights=diff, minlength=ns)
    cnts = np.bincount(inv, minlength=ns).astype(float)
    obs = float(diff.mean())
    pick = RNG.integers(0, ns, size=(n_boot, ns))
    bs = sums[pick].sum(axis=1) / cnts[pick].sum(axis=1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"diff": obs, "ci95": [float(lo), float(hi)],
            "n_groups": int(diff.size), "n_solute_clusters": int(ns)}


def contrast(tab_a: pd.DataFrame, tab_b: pd.DataFrame, col: str, n_boot: int = 4000) -> dict:
    m = tab_a.merge(tab_b, on=["gi", "solute"], suffixes=("_a", "_b"))
    m = m[np.isfinite(m[f"{col}_a"]) & np.isfinite(m[f"{col}_b"])]
    d = (m[f"{col}_a"] - m[f"{col}_b"]).to_numpy(float)
    out = cluster_boot(d, m["solute"].to_numpy(), n_boot)
    out["mean_a"] = float(m[f"{col}_a"].mean())
    out["mean_b"] = float(m[f"{col}_b"].mean())
    return out


# ------------------------------------------------------------------ FIX 2: floors
def donor_index(groups: list) -> tuple[list, dict]:
    """Groups whose solvent set is covered by at least one OTHER solute (arm-independent)."""
    cover: dict[str, set] = {}
    for g in groups:
        cover.setdefault(g["solute"], set()).update(g["solvents"])
    solutes = list(cover)
    donors = []
    for g in groups:
        donors.append([s for s in solutes if s != g["solute"] and cover[s].issuperset(g["solvents"])])
    idx = [i for i, d in enumerate(donors) if d]
    return idx, {i: donors[i] for i in idx}


def donor_floor(groups: list, idx: list, donors: dict, arm: str, n_draw: int = 200) -> dict:
    """FIX 2: built from `arm`'s OWN predictions -- a shuffled profile inside that arm."""
    wide: dict[str, dict[str, list]] = {}
    for g in groups:
        d = wide.setdefault(g["solute"], {})
        for s, v in zip(g["solvents"], g["preds"][arm]):
            d.setdefault(s, []).append(float(v))
    wide = {sol: {s: float(np.mean(v)) for s, v in d.items()} for sol, d in wide.items()}
    acc = {k: [] for k in METRICS}
    for _ in range(n_draw):
        cur = {k: [] for k in METRICS}
        for i in idx:
            g = groups[i]
            dl = donors[i]
            d = dl[RNG.integers(len(dl))]
            p = np.array([wide[d][x] for x in g["solvents"]], float)
            if np.std(p) == 0:
                continue
            m = metrics(g["ctx"], p)
            for k in cur:
                if np.isfinite(m[k]):
                    cur[k].append(m[k])
        for k in acc:
            acc[k].append(float(np.mean(cur[k])))
    return {k: {"mean": float(np.mean(v)), "sd": float(np.std(v))} for k, v in acc.items()}


def perm_floor(groups: list, idx: list, arm: str, n_perm: int = 200) -> dict:
    acc = {k: [] for k in METRICS}
    for _ in range(n_perm):
        cur = {k: [] for k in METRICS}
        for i in idx:
            g = groups[i]
            p = RNG.permutation(g["preds"][arm])
            if np.std(p) == 0:
                continue
            m = metrics(g["ctx"], p)
            for k in cur:
                if np.isfinite(m[k]):
                    cur[k].append(m[k])
        for k in acc:
            acc[k].append(float(np.mean(cur[k])))
    return {k: {"mean": float(np.mean(v)), "sd": float(np.std(v))} for k, v in acc.items()}


def marginal_floor(groups: list) -> tuple[list, dict]:
    """Solute-blind, label-derived: leave-one-solute-out mean ln_x2_true per solvent."""
    recs = [(g["solute"], s, tv) for g in groups for s, tv in zip(g["solvents"], g["t"])]
    df = pd.DataFrame(recs, columns=["solute", "solvent", "t"])
    tot = df.groupby("solvent")["t"].agg(["sum", "count"])
    own = df.groupby(["solute", "solvent"])["t"].agg(["sum", "count"])
    idx, acc = [], {k: [] for k in METRICS}
    for i, g in enumerate(groups):
        p = []
        for s in g["solvents"]:
            ssum, scnt = tot.loc[s, "sum"], tot.loc[s, "count"]
            if (g["solute"], s) in own.index:
                ssum -= own.loc[(g["solute"], s), "sum"]
                scnt -= own.loc[(g["solute"], s), "count"]
            p.append(ssum / scnt if scnt > 0 else np.nan)
        p = np.array(p, float)
        if not np.all(np.isfinite(p)) or np.std(p) == 0:
            continue
        idx.append(i)
        m = metrics(g["ctx"], p)
        for k in acc:
            if np.isfinite(m[k]):
                acc[k].append(m[k])
    return idx, {k: float(np.mean(v)) for k, v in acc.items()}


def arm_means_on(groups: list, idx: list, arm: str) -> dict:
    acc = {k: [] for k in METRICS}
    for i in idx:
        g = groups[i]
        p = g["preds"][arm]
        if np.std(p) == 0:
            continue
        m = metrics(g["ctx"], p)
        for k in acc:
            if np.isfinite(m[k]):
                acc[k].append(m[k])
    return {k: float(np.mean(v)) for k, v in acc.items()} | {"n": len(acc["ndcg"])}


# ------------------------------------------------------------------ FIX 3: affine
def recal_table(groups: list, arm: str) -> pd.DataFrame:
    """Per-group MAE under three concessions: none / offset / affine (slope+intercept)."""
    rows = []
    for i, g in enumerate(groups):
        t, p = g["t"], g["preds"][arm]
        raw = float(np.mean(np.abs(t - p)))
        ctr = float(np.mean(np.abs((t - t.mean()) - (p - p.mean()))))
        vp = float(np.var(p))
        if vp > 0:
            b = float(np.cov(p, t, bias=True)[0, 1] / vp)
        else:
            b = 0.0
        a = float(t.mean() - b * p.mean())
        aff = float(np.mean(np.abs(t - (a + b * p))))
        bpos = max(b, 0.0)
        apos = float(t.mean() - bpos * p.mean())
        affpos = float(np.mean(np.abs(t - (apos + bpos * p))))
        sdt, sdp = float(np.std(t)), float(np.std(p))
        rows.append({"gi": i, "solute": g["solute"], "n": len(t),
                     "mae": raw, "mae_offset": ctr, "mae_affine": aff,
                     "mae_affine_posslope": affpos, "slope": b,
                     "spread_ratio": (sdp / sdt) if sdt > 0 else np.nan})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ integrity
def integrity_block(frames: dict[str, pd.DataFrame]) -> dict:
    keysets = {a: set(map(tuple, f[KEY].itertuples(index=False, name=None))) for a, f in frames.items()}
    ref = keysets["grounded_a"]
    gref = frames["grounded_a"].set_index(KEY).sort_index()
    out = {"n_rows_per_arm": {a: int(len(f)) for a, f in frames.items()},
           "row_keys_identical_to_grounded_a": {a: bool(ks == ref) for a, ks in keysets.items()},
           "ln_x2_true_identical": {}, "phi_max_abs_diff_vs_grounded_a": {},
           "oracle_applied_rows": {}}
    for a, f in frames.items():
        fi = f.set_index(KEY).sort_index()
        out["ln_x2_true_identical"][a] = bool(np.allclose(
            fi["ln_x2_true"].to_numpy(float), gref["ln_x2_true"].to_numpy(float)))
        if "Phi" in fi.columns and "Phi" in gref.columns:
            out["phi_max_abs_diff_vs_grounded_a"][a] = float(np.max(np.abs(
                fi["Phi"].to_numpy(float) - gref["Phi"].to_numpy(float))))
        m = f["sigma_oracle_applied"].astype(str).str.lower().isin({"true", "1", "1.0"})
        out["oracle_applied_rows"][a] = int(m.sum())
    return out


def coverage_flags(groups: list) -> pd.DataFrame:
    from tgnn_solv.data.utils import canonicalize
    tab = pd.read_csv(SIGMA_ART)["smiles"].astype(str).tolist()
    keys = {c for c in (canonicalize(s) for s in tab) if c is not None}
    cache: dict[str, bool] = {}

    def h(s):
        if s not in cache:
            c = canonicalize(str(s))
            cache[s] = c is not None and c in keys
        return cache[s]

    rows = []
    for i, g in enumerate(groups):
        cov = np.array([h(s) for s in g["solvents"]])
        rows.append({"gi": i, "solute": g["solute"], "T": g["T"], "n": len(cov),
                     "solute_matched": h(g["solute"]),
                     "solvent_frac_matched": float(cov.mean()),
                     "all_solvents_matched": bool(cov.all())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ driver
def run_seed(seed: int) -> dict:
    t0 = time.time()
    frames = {a: load_arm(seed, a) for a in ARMS}
    integ = integrity_block(frames)
    groups, ginfo = build_groups(frames)
    tabs = {a: arm_table(groups, a) for a in ARMS}
    cov = coverage_flags(groups)

    per_arm = {a: {"n_groups": int(len(tabs[a])),
                   "n_pred_constant_groups": int(tabs[a]["pred_const"].sum()),
                   **{c: float(tabs[a][c].mean()) for c in METRICS}} for a in ARMS}

    contrasts = {}
    for a, b in [("oracle", "grounded_a"), ("directgnn", "grounded_a")]:
        contrasts[f"{a}_minus_{b}"] = {c: contrast(tabs[a], tabs[b], c) for c in METRICS}

    # best-solvent switching
    m = tabs["grounded_a"].merge(tabs["oracle"], on=["gi", "solute"], suffixes=("_g", "_o"))
    switch = {
        "frac_selected_solvent_changes": float(np.mean(m["argmax_pred_g"] != m["argmax_pred_o"])),
        "both_correct": float(np.mean((m["top1_g"] == 1) & (m["top1_o"] == 1))),
        "grounded_only": float(np.mean((m["top1_g"] == 1) & (m["top1_o"] == 0))),
        "oracle_only": float(np.mean((m["top1_g"] == 0) & (m["top1_o"] == 1))),
        "neither": float(np.mean((m["top1_g"] == 0) & (m["top1_o"] == 0))),
        "n_groups": int(len(m)),
    }

    # FIX 2 -- arm-matched floors
    d_idx, donors = donor_index(groups)
    mg_idx, mg_floor = marginal_floor(groups)
    allidx = list(range(len(groups)))
    floors = {
        "full_set": {"n_groups": len(groups),
                     "arms": {a: arm_means_on(groups, allidx, a) for a in ("grounded_a", "oracle")},
                     "permutation_floor_grounded": perm_floor(groups, allidx, "grounded_a", 200),
                     "permutation_floor_oracle": perm_floor(groups, allidx, "oracle", 200)},
        "donor_subset": {"n_groups": len(d_idx),
                         "arms": {a: arm_means_on(groups, d_idx, a) for a in ("grounded_a", "oracle")},
                         "donor_floor_from_grounded": donor_floor(groups, d_idx, donors, "grounded_a", 200),
                         "donor_floor_from_oracle": donor_floor(groups, d_idx, donors, "oracle", 200)},
        "marginal_subset": {"n_groups": len(mg_idx),
                            "arms": {a: arm_means_on(groups, mg_idx, a) for a in ("grounded_a", "oracle")},
                            "solute_blind_label_floor": mg_floor},
    }

    # FIX 3 -- affine recalibration
    rec = {a: recal_table(groups, a) for a in ("grounded_a", "oracle", "directgnn")}
    recal = {"arm_means": {a: {c: float(rec[a][c].mean()) for c in
                               ("mae", "mae_offset", "mae_affine", "mae_affine_posslope")}
                           | {"slope_median": float(np.median(rec[a]["slope"])),
                              "frac_slope_negative": float(np.mean(rec[a]["slope"] < 0)),
                              "spread_ratio_median": float(np.nanmedian(rec[a]["spread_ratio"]))}
                           for a in rec},
             "oracle_minus_grounded": {c: contrast(rec["oracle"], rec["grounded_a"], c, 4000)
                                       for c in ("mae", "mae_offset", "mae_affine",
                                                 "mae_affine_posslope", "spread_ratio")}}
    # affine on larger groups only (2 params on >=3 points is generous)
    big = set(rec["grounded_a"].loc[rec["grounded_a"]["n"] >= 5, "gi"])
    recal["oracle_minus_grounded_n_ge_5"] = {
        c: contrast(rec["oracle"][rec["oracle"]["gi"].isin(big)],
                    rec["grounded_a"][rec["grounded_a"]["gi"].isin(big)], c, 2000)
        for c in ("mae", "mae_offset", "mae_affine")}

    # mixed-coverage exclusion
    gi_clean = set(cov.loc[cov["all_solvents_matched"], "gi"])
    strata = {
        "all_solvents_matched": {
            "n_groups": len(gi_clean),
            "oracle_minus_grounded": {
                c: contrast(tabs["oracle"][tabs["oracle"]["gi"].isin(gi_clean)],
                            tabs["grounded_a"][tabs["grounded_a"]["gi"].isin(gi_clean)], c, 4000)
                for c in METRICS}},
        "mixed_coverage": {
            "n_groups": int(len(cov) - len(gi_clean)),
            "arm_means": {a: {c: float(tabs[a][~tabs[a]["gi"].isin(gi_clean)][c].mean())
                              for c in METRICS} for a in ("grounded_a", "oracle")}},
        "coverage_summary": {
            "frac_groups_all_solvents_matched": float(cov["all_solvents_matched"].mean()),
            "mean_solvent_frac_matched": float(cov["solvent_frac_matched"].mean()),
            "frac_groups_solute_matched": float(cov["solute_matched"].mean())},
    }

    # leave-one-solute-out jackknife on the mean Spearman gap
    mm = tabs["oracle"].merge(tabs["grounded_a"], on=["gi", "solute"], suffixes=("_o", "_g"))
    d = (mm["spearman_o"] - mm["spearman_g"]).to_numpy(float)
    sol = mm["solute"].to_numpy()
    jk = []
    for s in np.unique(sol):
        keep = sol != s
        jk.append(float(np.nanmean(d[keep])))
    per_solute = pd.DataFrame({"solute": sol, "d": d}).groupby("solute")["d"].mean()
    jack = {"mean_gap": float(np.nanmean(d)), "jack_min": float(np.min(jk)),
            "jack_max": float(np.max(jk)), "n_solutes": int(len(jk)),
            "frac_solutes_worse_under_oracle": float(np.mean(per_solute < 0))}

    return {"seed": seed, "integrity": integ,
            "group_info": ginfo | {"n_groups_scored": len(groups),
                                   "n_distinct_solutes": int(len({g["solute"] for g in groups})),
                                   "n_scored_cells": int(sum(len(g["solvents"]) for g in groups)),
                                   "mean_solvents_per_group": float(
                                       np.mean([len(g["solvents"]) for g in groups]))},
            "per_arm": per_arm, "contrasts": contrasts, "best_solvent_switch": switch,
            "floors": floors, "recalibration": recal, "strata": strata, "jackknife": jack,
            "_tabs": tabs, "_groups": groups, "_rec": rec, "elapsed_s": time.time() - t0}


def main() -> None:
    sys.path.insert(0, str(REPO / "src"))
    res, keep = {}, {}
    for seed in SEEDS:
        r = run_seed(seed)
        keep[seed] = {"tabs": r.pop("_tabs"), "groups": r.pop("_groups"), "rec": r.pop("_rec")}
        for a, tb in keep[seed]["tabs"].items():
            tb.to_csv(OUT / f"final_pergroup_seed{seed}_{a}.csv", index=False)
        res[f"seed_{seed}"] = r
        print(f"seed {seed} done in {r['elapsed_s']:.1f}s", flush=True)

    # --------- pooled over seeds: average the per-group diff across seeds, then cluster boot
    def group_key(g):
        return (g["solute"], g["T"], tuple(g["solvents"]))

    kmaps = {s: {group_key(g): i for i, g in enumerate(keep[s]["groups"])} for s in SEEDS}
    common = sorted(set.intersection(*(set(kmaps[s]) for s in SEEDS)))
    pooled = {"n_common_groups": len(common)}
    solutes = np.array([k[0] for k in common])

    for col in METRICS:
        stack = []
        for s in SEEDS:
            tb_o, tb_g = keep[s]["tabs"]["oracle"], keep[s]["tabs"]["grounded_a"]
            io = {gi: v for gi, v in zip(tb_o["gi"], tb_o[col])}
            ig = {gi: v for gi, v in zip(tb_g["gi"], tb_g[col])}
            stack.append(np.array([io[kmaps[s][k]] - ig[kmaps[s][k]] for k in common], float))
        d = np.nanmean(np.vstack(stack), axis=0)
        pooled[col] = cluster_boot(d, solutes) | {
            "mean_oracle": float(np.mean([np.mean(keep[s]["tabs"]["oracle"][col]) for s in SEEDS])),
            "mean_grounded": float(np.mean([np.mean(keep[s]["tabs"]["grounded_a"][col]) for s in SEEDS])),
        }
    for col in ("mae", "mae_offset", "mae_affine", "mae_affine_posslope"):
        stack = []
        for s in SEEDS:
            ro, rg = keep[s]["rec"]["oracle"], keep[s]["rec"]["grounded_a"]
            io = {gi: v for gi, v in zip(ro["gi"], ro[col])}
            ig = {gi: v for gi, v in zip(rg["gi"], rg[col])}
            stack.append(np.array([io[kmaps[s][k]] - ig[kmaps[s][k]] for k in common], float))
        d = np.nanmean(np.vstack(stack), axis=0)
        pooled[col] = cluster_boot(d, solutes)
    res["pooled_over_seeds"] = pooled

    # --------- same-arm seed replicate noise, all three pairs
    rep = {"n_common_groups": len(common)}
    for arm in ("grounded_a", "oracle", "directgnn"):
        for i, sa in enumerate(SEEDS):
            for sb in SEEDS[i + 1:]:
                ta, tb = keep[sa]["tabs"][arm], keep[sb]["tabs"][arm]
                ia = {gi: v for gi, v in zip(ta["gi"], ta["spearman"])}
                ib = {gi: v for gi, v in zip(tb["gi"], tb["spearman"])}
                d = np.array([ia[kmaps[sa][k]] - ib[kmaps[sb][k]] for k in common], float)
                rep[f"{arm}_seed{sa}_minus_seed{sb}_spearman"] = cluster_boot(d, solutes, 2000)
    res["replicate_noise"] = rep

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rank_final.json").write_text(json.dumps(res, indent=2, default=str))
    print("WROTE", OUT / "rank_final.json")


if __name__ == "__main__":
    main()
