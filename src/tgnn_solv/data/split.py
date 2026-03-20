"""
Scaffold-based train / validation / test splitting.

Uses greedy bin-packing: each scaffold is assigned to whichever
split is most under-filled relative to its target size.
This guarantees non-empty splits regardless of scaffold size distribution.
"""

from collections import defaultdict
from typing import Tuple

import numpy as np
import pandas as pd

from .utils import get_scaffold


def scaffold_split(
    df: pd.DataFrame,
    train_frac: float = 0.8,
    val_frac: float = 0.1,
    test_frac: float = 0.1,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split by Murcko scaffolds using greedy bin-packing.

    Each scaffold goes entirely to one split (no leakage).
    Scaffolds are assigned to whichever split is most under-filled,
    ensuring all splits get approximately the target fraction.
    """
    print("\n" + "=" * 60)
    print("Scaffold-based splitting")
    print("=" * 60)

    # Compute scaffold for each solute
    scaffolds = defaultdict(list)  # scaffold SMILES → [row indices]
    no_scaffold = []

    for idx, row in df.iterrows():
        s = get_scaffold(row["solute_smiles"])
        if s:
            scaffolds[s].append(idx)
        else:
            no_scaffold.append(idx)

    print(f"  Unique scaffolds: {len(scaffolds):,}")
    print(f"  No-scaffold: {len(no_scaffold):,}")

    # Shuffle scaffolds deterministically
    scaffold_list = list(scaffolds.items())
    rng = np.random.RandomState(seed)
    rng.shuffle(scaffold_list)

    # Sort by size (largest first) — greedy bin-packing works best this way
    scaffold_list.sort(key=lambda x: len(x[1]), reverse=True)

    # Target sizes
    n = len(df)
    targets = {
        "train": int(n * train_frac),
        "val": int(n * val_frac),
        "test": n - int(n * train_frac) - int(n * val_frac),
    }
    current = {"train": 0, "val": 0, "test": 0}
    buckets = {"train": [], "val": [], "test": []}

    # Greedy assignment: each scaffold goes to the most under-filled split
    for _, indices in scaffold_list:
        deficits = {k: targets[k] - current[k] for k in targets}
        best = max(deficits, key=deficits.get)
        buckets[best].extend(indices)
        current[best] += len(indices)

    # No-scaffold records go to train
    buckets["train"].extend(no_scaffold)

    train_df = df.loc[df.index.isin(buckets["train"])].reset_index(drop=True)
    val_df = df.loc[df.index.isin(buckets["val"])].reset_index(drop=True)
    test_df = df.loc[df.index.isin(buckets["test"])].reset_index(drop=True)

    # Verify no scaffold leakage
    train_scaf = {
        get_scaffold(s) for s in train_df["solute_smiles"].unique()
    } - {None}
    val_scaf = {
        get_scaffold(s) for s in val_df["solute_smiles"].unique()
    } - {None}
    test_scaf = {
        get_scaffold(s) for s in test_df["solute_smiles"].unique()
    } - {None}

    tv_leak = train_scaf & val_scaf
    tt_leak = train_scaf & test_scaf

    for name, split in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
        n_sol = split["has_solubility"].sum() if "has_solubility" in split else len(split)
        n_tm = split["has_T_m"].sum() if "has_T_m" in split else 0
        pct = len(split) / n * 100
        print(
            f"  {name:5s}: {len(split):6,d} ({pct:4.1f}%)  "
            f"{n_sol:6,d} solubility, {n_tm:5,d} T_m"
        )

    status_tv = "clean" if len(tv_leak) == 0 else f"LEAK ({len(tv_leak)})"
    status_tt = "clean" if len(tt_leak) == 0 else f"LEAK ({len(tt_leak)})"
    print(f"  Train↔Val:  {status_tv}")
    print(f"  Train↔Test: {status_tt}")

    return train_df, val_df, test_df