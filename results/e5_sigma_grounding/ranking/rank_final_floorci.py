#!/usr/bin/env python3
"""Paired CI for (arm - its OWN shuffled-profile floor), per group, clustered on solute.

The floor's draw-to-draw sd says how precisely the FLOOR MEAN is pinned down; it says
nothing about whether the arm is above it.  Here the floor is reduced to a per-group
EXPECTED value (mean over donor draws) and the paired difference arm-minus-floor is
bootstrapped over solute clusters, so "the oracle picks the best solvent less often
than a wrong solute's profile" gets an interval or is withdrawn.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
REPO = Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv")
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

from rank_final import (ARMS, METRICS, build_groups, cluster_boot, donor_index,  # noqa: E402
                        load_arm, metrics)


def marginal_floor_per_group(groups):
    """Per-group metrics of the solute-blind, label-derived ordering (leave-one-solute-out)."""
    recs = [(g["solute"], s, tv) for g in groups for s, tv in zip(g["solvents"], g["t"])]
    df = pd.DataFrame(recs, columns=["solute", "solvent", "t"])
    tot = df.groupby("solvent")["t"].agg(["sum", "count"])
    own = df.groupby(["solute", "solvent"])["t"].agg(["sum", "count"])
    idx, per = [], {}
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
        per[i] = metrics(g["ctx"], p)
    return idx, per

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
RNG = np.random.default_rng(4242)
N_DRAW = 300


def expected_floor_per_group(groups, idx, donors, arm):
    wide: dict[str, dict[str, list]] = {}
    for g in groups:
        d = wide.setdefault(g["solute"], {})
        for s, v in zip(g["solvents"], g["preds"][arm]):
            d.setdefault(s, []).append(float(v))
    wide = {sol: {s: float(np.mean(v)) for s, v in d.items()} for sol, d in wide.items()}
    acc = {k: {i: [] for i in idx} for k in METRICS}
    for _ in range(N_DRAW):
        for i in idx:
            g = groups[i]
            dl = donors[i]
            d = dl[RNG.integers(len(dl))]
            p = np.array([wide[d][x] for x in g["solvents"]], float)
            if np.std(p) == 0:
                continue
            m = metrics(g["ctx"], p)
            for k in METRICS:
                if np.isfinite(m[k]):
                    acc[k][i].append(m[k])
    return {k: {i: (float(np.mean(v)) if v else np.nan) for i, v in acc[k].items()} for k in METRICS}


def main():
    res = {}
    for seed in (42, 43, 44):
        frames = {a: load_arm(seed, a) for a in ("grounded_a", "oracle")}
        groups, _ = build_groups(frames)
        d_idx, donors = donor_index(groups)
        mg_idx, mg_per = marginal_floor_per_group(groups)
        seedres = {"n_donor_groups": len(d_idx), "n_marginal_groups": len(mg_idx)}
        for arm in ("grounded_a", "oracle"):
            ef = expected_floor_per_group(groups, d_idx, donors, arm)
            block = {}
            for k in METRICS:
                keep = [i for i in d_idx if np.std(groups[i]["preds"][arm]) > 0
                        and np.isfinite(ef[k][i])]
                arr, sol = [], []
                for i in keep:
                    m = metrics(groups[i]["ctx"], groups[i]["preds"][arm])
                    if not np.isfinite(m[k]):
                        continue
                    arr.append(m[k] - ef[k][i])
                    sol.append(groups[i]["solute"])
                block[k] = cluster_boot(np.array(arr, float), np.array(sol), 4000)
            seedres[f"{arm}_minus_own_donor_floor"] = block
            # against the solute-blind label floor (arm-independent ordering)
            blk2 = {}
            for k in METRICS:
                arr, sol = [], []
                for i in mg_idx:
                    if np.std(groups[i]["preds"][arm]) == 0:
                        continue
                    m = metrics(groups[i]["ctx"], groups[i]["preds"][arm])
                    if np.isfinite(m[k]) and np.isfinite(mg_per[i][k]):
                        arr.append(m[k] - mg_per[i][k])
                        sol.append(groups[i]["solute"])
                blk2[k] = cluster_boot(np.array(arr, float), np.array(sol), 4000)
            seedres[f"{arm}_minus_label_marginal_floor"] = blk2
        res[f"seed_{seed}"] = seedres
        print("seed", seed, "done", flush=True)
    (OUT / "rank_final_floorci.json").write_text(json.dumps(res, indent=2, default=str))
    print("WROTE rank_final_floorci.json")


if __name__ == "__main__":
    main()
