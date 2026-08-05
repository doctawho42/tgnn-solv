#!/usr/bin/env python3
"""OUT-OF-SAMPLE affine recalibration + fitted-slope audit (referee items 1 and 3).

Item 1.  rank_final.py fits the per-group affine map (slope + intercept) on the very
rows it then scores -- two free parameters against groups of as few as three solvents.
Here the same map is refit LEAVE-ONE-ROW-OUT inside each group: for each solvent in the
group the map is fitted on the group's OTHER solvents and the held-out solvent is scored
under it.  Chosen over a half-split because a half-split is undefined for the 103 groups
with exactly three solvents (a two-parameter fit consumes two points and leaves one), and
over fit-on-one-seed-apply-to-another because that reuses the same rows and so tests seed
stability rather than overfitting.  Ladder: raw / offset-only / affine, in sample and
leave-one-out, plus the monotone (slope >= 0) variant.

Item 3.  Per-group fitted slopes per arm: how many are negative (the rank-invariance
argument needs an INCREASING map), and the rank contrast restricted to groups where both
arms' fitted slopes are positive.

Outputs <out>/rank_final_oos.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
REPO = Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv")
sys.path.insert(0, str(REPO / "src"))

from rank_final import (METRICS, arm_table, build_groups, cluster_boot,  # noqa: E402
                        contrast, load_arm, recal_table)

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
SEEDS = (42, 43, 44)
PAIR = ("grounded_a", "oracle")


def _fit(tt: np.ndarray, pp: np.ndarray) -> tuple[float, float]:
    """OLS of t on p; slope 0 if p has no spread on the fitting rows."""
    vp = float(np.var(pp))
    b = float(np.cov(pp, tt, bias=True)[0, 1] / vp) if vp > 0 else 0.0
    return float(np.mean(tt) - b * np.mean(pp)), b


def loo_table(groups: list, arm: str) -> pd.DataFrame:
    """Per-group MAE with every recalibration refit leaving the scored row out."""
    rows = []
    for i, g in enumerate(groups):
        t, p = g["t"], g["preds"][arm]
        n = len(t)
        e_aff, e_pos, e_off, slopes = [], [], [], []
        for j in range(n):
            m = np.ones(n, bool)
            m[j] = False
            tt, pp = t[m], p[m]
            a, b = _fit(tt, pp)
            e_aff.append(abs(t[j] - (a + b * p[j])))
            bp = max(b, 0.0)
            ap = float(np.mean(tt) - bp * np.mean(pp))
            e_pos.append(abs(t[j] - (ap + bp * p[j])))
            c = float(np.mean(tt - pp))  # offset only: slope fixed at 1
            e_off.append(abs(t[j] - (p[j] + c)))
            slopes.append(b)
        rows.append({"gi": i, "solute": g["solute"], "n": n,
                     "mae_loo_affine": float(np.mean(e_aff)),
                     "mae_loo_affine_posslope": float(np.mean(e_pos)),
                     "mae_loo_offset": float(np.mean(e_off)),
                     "loo_slope_median": float(np.median(slopes)),
                     "loo_slope_frac_neg": float(np.mean(np.asarray(slopes) < 0))})
    return pd.DataFrame(rows)


def main() -> None:
    per_seed, keep = {}, {}
    for seed in SEEDS:
        frames = {a: load_arm(seed, a) for a in PAIR}
        groups, ginfo = build_groups(frames)
        tabs = {a: arm_table(groups, a) for a in PAIR}
        rec = {a: recal_table(groups, a) for a in PAIR}          # in-sample
        loo = {a: loo_table(groups, a) for a in PAIR}            # out-of-sample
        for a in PAIR:
            rec[a] = rec[a].merge(loo[a].drop(columns=["solute", "n"]), on="gi")

        cols = ("mae", "mae_offset", "mae_affine", "mae_affine_posslope",
                "mae_loo_offset", "mae_loo_affine", "mae_loo_affine_posslope")
        block = {
            "n_groups": len(groups),
            "group_sizes": {int(k): int(v) for k, v in
                            rec["grounded_a"]["n"].value_counts().sort_index().items()},
            "arm_means": {a: {c: float(rec[a][c].mean()) for c in cols} for a in PAIR},
            "oracle_minus_grounded": {c: contrast(rec["oracle"], rec["grounded_a"], c, 4000)
                                      for c in cols},
        }
        # slope audit (item 3) -- the IN-SAMPLE map is the one the invariance claim is about
        sl = {}
        for a in PAIR:
            s = rec[a]["slope"].to_numpy(float)
            sl[a] = {"n_groups": int(s.size),
                     "n_slope_negative": int((s < 0).sum()),
                     "frac_slope_negative": float((s < 0).mean()),
                     "n_slope_zero": int((s == 0).sum()),
                     "median_slope": float(np.median(s)),
                     "n_loo_any_negative": int((rec[a]["loo_slope_frac_neg"] > 0).sum())}
        both_pos = set(rec["grounded_a"].loc[rec["grounded_a"]["slope"] > 0, "gi"]) & \
                   set(rec["oracle"].loc[rec["oracle"]["slope"] > 0, "gi"])
        sl["n_both_slopes_positive"] = len(both_pos)
        sl["n_either_slope_nonpositive"] = len(groups) - len(both_pos)
        block["slopes"] = sl
        # the rank contrast restricted to groups where the affine map is increasing in BOTH arms
        block["oracle_minus_grounded_rank_both_slopes_positive"] = {
            c: contrast(tabs["oracle"][tabs["oracle"]["gi"].isin(both_pos)],
                        tabs["grounded_a"][tabs["grounded_a"]["gi"].isin(both_pos)], c, 4000)
            for c in METRICS}
        # ... and on the full set, for the side-by-side
        block["oracle_minus_grounded_rank_all"] = {
            c: contrast(tabs["oracle"], tabs["grounded_a"], c, 4000) for c in METRICS}
        # affine, in-sample and LOO, on groups with >= 5 solvents
        big = set(rec["grounded_a"].loc[rec["grounded_a"]["n"] >= 5, "gi"])
        block["n_groups_ge5"] = len(big)
        block["oracle_minus_grounded_n_ge_5"] = {
            c: contrast(rec["oracle"][rec["oracle"]["gi"].isin(big)],
                        rec["grounded_a"][rec["grounded_a"]["gi"].isin(big)], c, 2000)
            for c in ("mae", "mae_affine", "mae_loo_affine")}
        per_seed[f"seed_{seed}"] = block
        keep[seed] = {"groups": groups, "rec": rec, "tabs": tabs, "both_pos": both_pos}
        rec["grounded_a"].to_csv(OUT / f"oos_pergroup_seed{seed}_grounded_a.csv", index=False)
        rec["oracle"].to_csv(OUT / f"oos_pergroup_seed{seed}_oracle.csv", index=False)
        print("seed", seed, "done", flush=True)

    # pooled over seeds: average the per-group difference across seeds, then cluster bootstrap
    def key(g):
        return (g["solute"], g["T"], tuple(g["solvents"]))

    kmaps = {s: {key(g): i for i, g in enumerate(keep[s]["groups"])} for s in SEEDS}
    common = sorted(set.intersection(*(set(kmaps[s]) for s in SEEDS)))
    solutes = np.array([k[0] for k in common])
    pooled = {"n_common_groups": len(common)}
    for col in ("mae", "mae_offset", "mae_affine", "mae_affine_posslope",
                "mae_loo_offset", "mae_loo_affine", "mae_loo_affine_posslope"):
        stack = []
        for s in SEEDS:
            ro, rg = keep[s]["rec"]["oracle"], keep[s]["rec"]["grounded_a"]
            io = dict(zip(ro["gi"], ro[col]))
            ig = dict(zip(rg["gi"], rg[col]))
            stack.append(np.array([io[kmaps[s][k]] - ig[kmaps[s][k]] for k in common], float))
        pooled[col] = cluster_boot(np.nanmean(np.vstack(stack), axis=0), solutes)
        pooled[col]["mean_grounded"] = float(np.mean(
            [keep[s]["rec"]["grounded_a"][col].mean() for s in SEEDS]))
        pooled[col]["mean_oracle"] = float(np.mean(
            [keep[s]["rec"]["oracle"][col].mean() for s in SEEDS]))
    # pooled rank contrast on groups whose affine map is increasing in both arms at ALL seeds
    ok = [k for k in common if all(kmaps[s][k] in keep[s]["both_pos"] for s in SEEDS)]
    pooled["n_common_both_slopes_positive_all_seeds"] = len(ok)
    sol_ok = np.array([k[0] for k in ok])
    for col in METRICS:
        stack = []
        for s in SEEDS:
            to, tg = keep[s]["tabs"]["oracle"], keep[s]["tabs"]["grounded_a"]
            io = dict(zip(to["gi"], to[col]))
            ig = dict(zip(tg["gi"], tg[col]))
            stack.append(np.array([io[kmaps[s][k]] - ig[kmaps[s][k]] for k in ok], float))
        pooled[f"rank_{col}_both_slopes_positive"] = cluster_boot(
            np.nanmean(np.vstack(stack), axis=0), sol_ok)
    per_seed["pooled_over_seeds"] = pooled

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rank_final_oos.json").write_text(json.dumps(per_seed, indent=2, default=str))
    print("WROTE", OUT / "rank_final_oos.json")


if __name__ == "__main__":
    main()
