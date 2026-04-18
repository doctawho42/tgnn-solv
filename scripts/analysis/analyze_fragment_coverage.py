#!/usr/bin/env python
"""Analyze BRICS fragment coverage from train to test solutes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from rdkit import Chem
from rdkit.Chem import BRICS


def brics_fragments(smiles: str) -> tuple[str, ...]:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return tuple()
    fragments = BRICS.BRICSDecompose(mol)
    if not fragments:
        return (Chem.MolToSmiles(mol, canonical=True),)
    return tuple(sorted(fragments))


def load_unique_smiles(path: Path, col: str) -> list[str]:
    df = pd.read_csv(path, low_memory=False)
    if col not in df.columns:
        raise ValueError(f"{path} has no column {col!r}")
    return sorted(set(df[col].dropna().astype(str)))


def run(train: Path, test: Path, output_dir: Path, col: str) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    train_smiles = load_unique_smiles(train, col)
    test_smiles = load_unique_smiles(test, col)

    train_fragments: set[str] = set()
    for smiles in train_smiles:
        train_fragments.update(brics_fragments(smiles))

    rows = []
    for smiles in test_smiles:
        fragments = brics_fragments(smiles)
        if not fragments:
            coverage = 0.0
            n_covered = 0
        else:
            n_covered = sum(1 for frag in fragments if frag in train_fragments)
            coverage = n_covered / len(fragments)

        if coverage == 1.0:
            bucket = "fully_covered"
        elif coverage > 0.5:
            bucket = "partially_covered_gt_50"
        else:
            bucket = "mostly_novel_le_50"

        rows.append(
            {
                "smiles": smiles,
                "n_fragments": len(fragments),
                "n_covered": n_covered,
                "n_novel": len(fragments) - n_covered,
                "coverage": coverage,
                "bucket": bucket,
                "fragments": "|".join(fragments),
                "novel_fragments": "|".join(
                    frag for frag in fragments if frag not in train_fragments
                ),
            }
        )

    out_df = pd.DataFrame(rows)
    bucket_counts = (
        out_df["bucket"].value_counts().rename_axis("bucket").reset_index(name="n_solutes")
    )
    bucket_counts["fraction"] = bucket_counts["n_solutes"] / max(len(out_df), 1)

    summary = {
        "train": str(train),
        "test": str(test),
        "smiles_col": col,
        "n_train_unique_solutes": len(train_smiles),
        "n_test_unique_solutes": len(test_smiles),
        "n_train_unique_brics_fragments": len(train_fragments),
        "mean_test_fragment_coverage": float(out_df["coverage"].mean()) if len(out_df) else None,
        "median_test_fragment_coverage": float(out_df["coverage"].median()) if len(out_df) else None,
        "buckets": bucket_counts.to_dict(orient="records"),
    }

    out_df.to_csv(output_dir / "fragment_coverage_by_solute.csv", index=False)
    bucket_counts.to_csv(output_dir / "fragment_coverage_buckets.csv", index=False)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, output_dir / "SUMMARY.md")
    return summary


def write_markdown(summary: dict, path: Path) -> None:
    lines = [
        "# BRICS Fragment Coverage",
        "",
        f"- train: `{summary['train']}`",
        f"- test: `{summary['test']}`",
        f"- train unique solutes: `{summary['n_train_unique_solutes']}`",
        f"- test unique solutes: `{summary['n_test_unique_solutes']}`",
        f"- train unique BRICS fragments: `{summary['n_train_unique_brics_fragments']}`",
        f"- mean test fragment coverage: `{summary['mean_test_fragment_coverage']:.3f}`",
        f"- median test fragment coverage: `{summary['median_test_fragment_coverage']:.3f}`",
        "",
        "| Bucket | n solutes | fraction |",
        "|---|---:|---:|",
    ]
    for row in summary["buckets"]:
        lines.append(f"| {row['bucket']} | {row['n_solutes']} | {row['fraction']:.3f} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=Path("notebooks/data/processed/train.csv"))
    parser.add_argument("--test", type=Path, default=Path("notebooks/data/processed/test.csv"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--smiles-col", default="solute_smiles")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(args.train, args.test, args.output_dir, args.smiles_col)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
