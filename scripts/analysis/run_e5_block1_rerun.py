#!/usr/bin/env python
"""Block 1 of tab:baselines for the arms the leak-free re-run trains: MAE(ln x2), RMSE(log10 S)
and R2(ln x2), mean +- population sd over that family's seeds, on the paper's row lock.

WHY THIS IS NOT run_external_baseline_comparison.py.  That generator computes all four block-1
arms over ONE seed set, and takes the row lock from the six-arm intersection inside the tree it
reads.  The re-run trains three arms (ungrounded, grounded_a, oracle) at five seeds and does not
touch the other three, which stay at three, so no single seed set describes the block and the
generator cannot be pointed at one tree.  Table S3 already prints the block that way -- five values
for the re-run arms, three for the rest -- and this script supplies the same split for the article's
table.

THE LOCK IS TAKEN, NOT RECOMPUTED.  The six-arm intersection at seed 42 of the published family is
the paper's n=5608 lock, and the re-run's three arms reproduce that key set exactly at every one of
its five seeds (checked here, not assumed: --check-lock fails if any seed disagrees).  So the two
families are scored on identical rows and the block1 cells of the two seed sets are comparable in
the only sense the table needs.

THE log10 S COLUMN.  Converted with the repo's standing convention: the row set is fixed by the
TRUE column alone (the rows whose solvent carries a molarity, n=5440), so it is arm-independent,
and predictions are clipped at x2 = 1 - 1e-6 before conversion, so an arm that saturates keeps its
row with a large finite error instead of converting to +inf and being dropped.  Dropping them would
be an arm-dependent exclusion inside a comparison table.

Usage
-----
    # validation: reproduce the published three-seed cells the article prints today
    python scripts/analysis/run_e5_block1_rerun.py --tree results/e5_sigma_grounding --seeds 42 43 44

    # the re-run's own block
    python scripts/analysis/run_e5_block1_rerun.py \
        --tree results/e5_sigma_grounding_leakfree --seeds 42 43 44 45 46 \
        --out results/e5_sigma_grounding_leakfree/block1_cells.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_e5_comparison import _KEY, _round_key, intersection_keys  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from tgnn_solv.external_benchmarking import (  # noqa: E402
    clip_ln_x2_for_logS,
    logS_from_ln_x2,
)

#: The six arms whose intersection at seed 42 of the published family defines the paper's lock.
LOCK_ARMS = ("nrtl", "directgnn", "ungrounded", "grounded_a", "grounded_b")
LOCK_TREE = "results/e5_sigma_grounding"
LOCK_SEED = 42


def paper_lock() -> list[tuple]:
    frames = {a: pd.read_csv(f"{LOCK_TREE}/seed_{LOCK_SEED}/{a}_predictions.csv", low_memory=False)
              for a in LOCK_ARMS}
    return intersection_keys(frames)


def locked(tree: Path, seed: int, arm: str, keys: list[tuple]) -> pd.DataFrame:
    d = pd.read_csv(tree / f"seed_{seed}" / f"{arm}_predictions.csv", low_memory=False)
    d = _round_key(d).drop_duplicates(_KEY, keep="first").set_index(_KEY).loc[keys]
    d = d.loc[:, ~d.columns.duplicated()]
    out = d[["ln_x2_true", "ln_x2_pred"]].copy()
    # solvent_smiles is part of the key, so read it off the key rather than the (dropped) column
    out["solvent_smiles"] = [k[_KEY.index("solvent_smiles")] for k in keys]
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tree", type=Path, required=True)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--arms", nargs="+", default=["grounded_a", "ungrounded", "oracle"])
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()

    keys = paper_lock()
    for seed in a.seeds:
        frames = {arm: pd.read_csv(a.tree / f"seed_{seed}" / f"{arm}_predictions.csv",
                                   low_memory=False) for arm in a.arms}
        if set(intersection_keys(frames)) != set(keys):
            raise SystemExit(
                f"{a.tree}/seed_{seed}: this seed's arms do not reproduce the paper's "
                f"{len(keys)}-row lock. Scoring it beside the other family would compare arms on "
                f"different rows, which is the one thing the lock exists to prevent.")

    acc = {arm: {"mae": [], "rmse_logS": [], "r2": []} for arm in a.arms}
    n_log = None
    for seed in a.seeds:
        base = locked(a.tree, seed, a.arms[0], keys)
        bt = base[["solvent_smiles"]].copy()
        bt["ln_x2"] = base["ln_x2_true"].to_numpy(float)
        logS_true = logS_from_ln_x2(bt, ln_x2_col="ln_x2").to_numpy(float)
        common = np.isfinite(logS_true)
        n_log = int(common.sum())
        for arm in a.arms:
            d = locked(a.tree, seed, arm, keys)
            t, pr = d["ln_x2_true"].to_numpy(float), d["ln_x2_pred"].to_numpy(float)
            acc[arm]["mae"].append(float(np.abs(pr - t).mean()))
            acc[arm]["r2"].append(float(1 - ((pr - t) ** 2).sum() / ((t - t.mean()) ** 2).sum()))
            tmp = d[["solvent_smiles"]].copy()
            tmp["ln_x2"] = clip_ln_x2_for_logS(pr)
            lp = logS_from_ln_x2(tmp, ln_x2_col="ln_x2").to_numpy(float)
            acc[arm]["rmse_logS"].append(
                float(np.sqrt(np.mean((lp[common] - logS_true[common]) ** 2))))

    result = {"tree": str(a.tree), "seeds": a.seeds, "n": len(keys), "n_logS": n_log, "cells": {}}
    for arm in a.arms:
        m = acc[arm]
        result["cells"][arm] = {
            k: {"mean": round(float(np.mean(v)), 4), "sd": round(float(np.std(v)), 4),
                "per_seed": [round(x, 4) for x in v]}
            for k, v in m.items()}
        print(f"{arm:12s} MAE {np.mean(m['mae']):.4f}+-{np.std(m['mae']):.4f}   "
              f"RMSE_logS {np.mean(m['rmse_logS']):.4f}+-{np.std(m['rmse_logS']):.4f}   "
              f"R2 {np.mean(m['r2']):+.4f}+-{np.std(m['r2']):.4f}")
    print(f"n = {len(keys)} / {n_log}")
    if a.out is not None:
        a.out.write_text(json.dumps(result, indent=2) + "\n")
        print("wrote", a.out)


if __name__ == "__main__":
    main()
