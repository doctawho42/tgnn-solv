#!/usr/bin/env python
"""The solute-clustered bootstrap of Sec. 3.1: the supervision gain, the substitution penalty,
and the leak-deletion bound, pooled over a run family's seeds.

WHY THIS SCRIPT EXISTS.  Three intervals in Sec. 3.1 -- ``+0.198 [+0.06,+0.33]`` for supervision,
``+0.406 [+0.29,+0.53]`` for the evaluation-time substitution, and ``+0.172 [+0.03,+0.31]`` for the
gain with the leak-reachable solutes deleted -- were hand-computed against the published three-seed
family and never had a producer in the tree.  The discharge sheet's row 2 puts Sec. 3.1 entire under
disposition R, so all three have to move to the five-seed leak-free re-run, and moving a number by
hand that was produced by hand is how a family gets half-replaced.  This script produces all three
from the per-row deposits, and it is validated by reproducing the published three-seed values before
it is pointed at the re-run.

THE ESTIMATOR.  Rows are the labelled test rows (``has_solubility``), the cluster is the solute, and
a draw resamples solutes with replacement and takes every row of a drawn solute at every seed.  So
the pooling is over seeds INSIDE the statistic (one MAE per arm over the pooled draw) rather than a
mean of per-seed statistics: the interval prices the draw of test solutes and holds the seed set
fixed, which is what the sentence in Sec. 3.1 says it does.  Percentile interval, uncorrected and
unstudentised, matching every other resampling interval in the paper (Sec. 3).

THE LEAK DELETION.  ``--delete-solutes`` takes a file of canonical SMILES, one per line: the pool
molecules the uncertified stream build can reach.  Deleting them bounds where a leak can act on the
supervision contrast; it does not bound what a leaked profile did to the weights, and the article
says so where it prints the number.

Usage
-----
    python scripts/analysis/run_e5_cluster_bootstrap.py \
        --root results/e5_sigma_grounding_leakfree --seeds 42 43 44 45 46 \
        --delete-solutes results/e5_sigma_grounding/leak_reachable_solutes.txt \
        --out results/e5_sigma_grounding_leakfree/cluster_bootstrap.json

    # validation against the published family, whose printed values are in Sec. 3.1:
    python scripts/analysis/run_e5_cluster_bootstrap.py \
        --root results/e5_sigma_grounding --seeds 42 43 44 --expect-gain 0.198
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

#: The three arms, by the stem of their per-row deposit.
ARMS = {"ungrounded": "ungrounded_predictions.csv",
        "grounded": "grounded_a_predictions.csv",
        "oracle": "oracle_predictions.csv"}


def _load(root: Path, seeds: list[int]) -> pd.DataFrame:
    """One long frame: solute, seed, arm, abs_error, over the labelled rows only."""
    frames = []
    for seed in seeds:
        d = root / f"seed_{seed}"
        for arm, stem in ARMS.items():
            path = d / stem
            if not path.exists():
                raise SystemExit(f"{path} does not exist.  This script does not substitute "
                                 f"another seed or another arm for a missing one.")
            df = pd.read_csv(path, usecols=["has_solubility", "solute_smiles", "abs_error"])
            df = df[df["has_solubility"]].copy()
            df["arm"], df["seed"] = arm, seed
            frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    # THE ROW LOCK IS AN ASSERTION, NOT AN ASSUMPTION.  Every arm at every seed must carry the same
    # labelled rows; a bootstrap over a set that differs by arm would price the arms' row sets.
    counts = out.groupby(["arm", "seed"]).size().unique()
    if len(counts) != 1:
        raise SystemExit(f"arms/seeds disagree on row count: {sorted(counts)}")
    return out


def _mae_by_arm(df: pd.DataFrame) -> dict[str, float]:
    return df.groupby("arm")["abs_error"].mean().to_dict()


def _bootstrap(df: pd.DataFrame, draws: int, seed: int) -> dict:
    """Percentile intervals on the two contrasts, resampling solute clusters."""
    solutes = np.array(sorted(df["solute_smiles"].unique()))
    by_solute = {s: g for s, g in df.groupby("solute_smiles")}
    rng = np.random.default_rng(seed)
    gains, penalties = [], []
    for _ in range(draws):
        drawn = rng.choice(solutes, size=len(solutes), replace=True)
        m = _mae_by_arm(pd.concat([by_solute[s] for s in drawn], ignore_index=True))
        gains.append(m["ungrounded"] - m["grounded"])
        penalties.append(m["oracle"] - m["grounded"])
    point = _mae_by_arm(df)
    return {
        "n_solute_clusters": int(len(solutes)),
        "n_rows_per_arm_per_seed": int(len(df) // (df["arm"].nunique() * df["seed"].nunique())),
        "mae": {k: round(v, 4) for k, v in point.items()},
        "supervision_gain": round(point["ungrounded"] - point["grounded"], 4),
        "supervision_ci95": [round(float(np.percentile(gains, 2.5)), 4),
                             round(float(np.percentile(gains, 97.5)), 4)],
        "substitution_penalty": round(point["oracle"] - point["grounded"], 4),
        "substitution_ci95": [round(float(np.percentile(penalties, 2.5)), 4),
                              round(float(np.percentile(penalties, 97.5)), 4)],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--draws", type=int, default=4000,
                   help="matches the ranking bootstrap of Sec. 3.2")
    p.add_argument("--boot-seed", type=int, default=0)
    p.add_argument("--delete-solutes", type=Path, default=None,
                   help="file of canonical SMILES, one per line: the leak-reachable solutes")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--expect-gain", type=float, default=None,
                   help="validation: fail unless the point gain rounds to this")
    a = p.parse_args()

    df = _load(a.root, a.seeds)
    result = {"root": str(a.root), "seeds": a.seeds, "draws": a.draws,
              "boot_seed": a.boot_seed, "all_solutes": _bootstrap(df, a.draws, a.boot_seed)}

    if a.delete_solutes is not None:
        wanted = [s.strip() for s in a.delete_solutes.read_text().split("\n") if s.strip()]
        present = sorted(set(wanted) & set(df["solute_smiles"]))
        missing = sorted(set(wanted) - set(present))
        kept = df[~df["solute_smiles"].isin(present)]
        result["leak_deleted"] = {
            "requested": len(wanted), "matched_in_test": len(present), "unmatched": missing,
            "rows_removed_per_arm_per_seed":
                int((len(df) - len(kept)) // (df["arm"].nunique() * df["seed"].nunique())),
            **_bootstrap(kept, a.draws, a.boot_seed),
        }

    print(json.dumps(result, indent=2))
    if a.out is not None:
        a.out.write_text(json.dumps(result, indent=2) + "\n")
        print(f"\nwrote {a.out}")
    if a.expect_gain is not None:
        got = result["all_solutes"]["supervision_gain"]
        if round(got, 3) != round(a.expect_gain, 3):
            raise SystemExit(f"VALIDATION FAILED: gain {got} against the expected {a.expect_gain}")
        print(f"\nvalidation: gain {got} reproduces the published {a.expect_gain}")


if __name__ == "__main__":
    main()
