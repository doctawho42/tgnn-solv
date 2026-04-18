#!/usr/bin/env python
"""Summarize precomputed UNIFAC-prior coverage in processed split copies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def summarize_file(path: Path) -> dict:
    df = pd.read_csv(path, low_memory=False)
    if "has_unifac_gamma_inf" not in df.columns:
        raise ValueError(f"{path} has no 'has_unifac_gamma_inf' column")
    mask = df["has_unifac_gamma_inf"].astype(bool)
    pair_key = df["solute_smiles"].astype(str) + ">>" + df["solvent_smiles"].astype(str)
    pair_df = pd.DataFrame({"pair_key": pair_key, "covered": mask})
    pair_cov = pair_df.groupby("pair_key")["covered"].any()
    solvent_cov = df.groupby("solvent_smiles")["has_unifac_gamma_inf"].mean()
    return {
        "path": str(path),
        "n_rows": int(len(df)),
        "n_unifac_rows": int(mask.sum()),
        "row_coverage": float(mask.mean()) if len(df) else None,
        "n_unique_pairs": int(pair_cov.shape[0]),
        "n_unifac_unique_pairs": int(pair_cov.sum()),
        "unique_pair_coverage": float(pair_cov.mean()) if len(pair_cov) else None,
        "n_solvents": int(df["solvent_smiles"].nunique()),
        "median_solvent_row_coverage": float(solvent_cov.median()) if len(solvent_cov) else None,
    }


def run(input_dir: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(input_dir.glob("*.csv")):
        rows.append(summarize_file(path))
    summary_df = pd.DataFrame(rows)
    summary = {
        "input_dir": str(input_dir),
        "files": rows,
    }
    summary_df.to_csv(output_dir / "unifac_coverage_by_split.csv", index=False)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary_df, output_dir / "SUMMARY.md")
    return summary


def write_markdown(df: pd.DataFrame, path: Path) -> None:
    lines = [
        "# UNIFAC Prior Coverage",
        "",
        "| Split | Row coverage | Unique pair coverage | Rows | Unique pairs |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in df.itertuples(index=False):
        split = Path(row.path).name
        lines.append(
            f"| {split} | {row.row_coverage:.3f} | {row.unique_pair_coverage:.3f} | "
            f"{row.n_rows} | {row.n_unique_pairs} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("notebooks/data/processed_unifac_priors"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(args.input_dir, args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
