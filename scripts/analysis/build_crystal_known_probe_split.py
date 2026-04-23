#!/usr/bin/env python3
"""Build a tiny internal split from rows with known crystal parameters."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input CSV.")
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument(
        "--require-both",
        action="store_true",
        help="Require both T_m and dH_fus masks to be true.",
    )
    return parser.parse_args()


def _mask(df: pd.DataFrame, require_both: bool) -> pd.Series:
    has_tm = df["has_T_m"].astype(bool) if "has_T_m" in df.columns else df["T_m"].notna()
    has_dh = (
        df["has_dH_fus"].astype(bool)
        if "has_dH_fus" in df.columns
        else df["dH_fus"].notna()
    )
    return has_tm & has_dh if require_both else (has_tm | has_dh)


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input, low_memory=False)
    sub = df.loc[_mask(df, args.require_both)].copy()
    if sub.empty:
        raise ValueError("No rows satisfy the requested crystal-known condition.")

    pair_cols = ["solute_smiles", "solvent_smiles"]
    pairs = sub[pair_cols].drop_duplicates().sample(frac=1.0, random_state=args.seed).reset_index(drop=True)
    n_pairs = len(pairs)
    n_train = max(1, int(round(n_pairs * args.train_frac)))
    n_val = max(1, int(round(n_pairs * args.val_frac)))
    if n_train + n_val >= n_pairs:
        n_val = max(1, n_pairs - n_train - 1)
    n_test = n_pairs - n_train - n_val
    if n_test < 1:
        n_test = 1
        if n_train > n_val:
            n_train -= 1
        else:
            n_val -= 1

    train_pairs = pairs.iloc[:n_train].copy()
    val_pairs = pairs.iloc[n_train:n_train + n_val].copy()
    test_pairs = pairs.iloc[n_train + n_val:].copy()

    def select(pair_df: pd.DataFrame) -> pd.DataFrame:
        marked = sub.merge(pair_df.assign(_keep=True), on=pair_cols, how="inner")
        return marked.sort_values(pair_cols + (["temperature"] if "temperature" in marked.columns else [])).reset_index(drop=True)

    train_df = select(train_pairs)
    val_df = select(val_pairs)
    test_df = select(test_pairs)

    train_df.to_csv(out_dir / "train.csv", index=False)
    val_df.to_csv(out_dir / "val.csv", index=False)
    test_df.to_csv(out_dir / "test.csv", index=False)

    summary = {
        "input": str(Path(args.input).resolve()),
        "output_dir": str(out_dir.resolve()),
        "seed": int(args.seed),
        "require_both": bool(args.require_both),
        "n_rows_total": int(len(df)),
        "n_rows_selected": int(len(sub)),
        "n_pairs_selected": int(n_pairs),
        "splits": {
            "train": {
                "rows": int(len(train_df)),
                "pairs": int(train_df[pair_cols].drop_duplicates().shape[0]),
            },
            "val": {
                "rows": int(len(val_df)),
                "pairs": int(val_df[pair_cols].drop_duplicates().shape[0]),
            },
            "test": {
                "rows": int(len(test_df)),
                "pairs": int(test_df[pair_cols].drop_duplicates().shape[0]),
            },
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
