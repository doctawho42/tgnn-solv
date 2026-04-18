#!/usr/bin/env python
"""Sample solubility cliffs within each solvent.

A cliff is defined as structurally similar solutes in the same solvent with a
large mean-solubility gap. This diagnostic is intentionally lightweight and
uses mean ln(x2) over temperatures for each (solvent, solute) pair.
"""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem


def fp(smiles: str, radius: int, n_bits: int):
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)


def sample_pairs(n: int, max_pairs: int, rng: np.random.Generator) -> list[tuple[int, int]]:
    total = n * (n - 1) // 2
    if total <= max_pairs:
        return list(combinations(range(n), 2))
    seen: set[tuple[int, int]] = set()
    while len(seen) < max_pairs:
        i = int(rng.integers(0, n))
        j = int(rng.integers(0, n - 1))
        if j >= i:
            j += 1
        a, b = sorted((i, j))
        seen.add((a, b))
    return sorted(seen)


def run(
    data: Path,
    output_dir: Path,
    seed: int,
    max_solutes_per_solvent: int,
    max_pairs_per_solvent: int,
    radius: int,
    n_bits: int,
    min_similarity: float,
    cliff_similarity: float,
    positive_delta: float,
    cliff_delta: float,
    easy_negative_similarity: float,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    df = pd.read_csv(data, low_memory=False)
    for col in ("solute_smiles", "solvent_smiles", "ln_x2"):
        if col not in df.columns:
            raise ValueError(f"{data} has no column {col!r}")

    pair_df = (
        df.dropna(subset=["solute_smiles", "solvent_smiles", "ln_x2"])
        .groupby(["solvent_smiles", "solute_smiles"], as_index=False)
        .agg(mean_ln_x2=("ln_x2", "mean"), n_points=("ln_x2", "size"))
    )

    all_rows: list[dict] = []
    solvent_rows: list[dict] = []
    invalid_smiles = 0

    for solvent, group in pair_df.groupby("solvent_smiles", sort=False):
        group = group.reset_index(drop=True)
        if len(group) < 2:
            continue
        if len(group) > max_solutes_per_solvent:
            idx = rng.choice(len(group), size=max_solutes_per_solvent, replace=False)
            group = group.iloc[np.sort(idx)].reset_index(drop=True)

        fps = []
        keep_rows = []
        for row in group.itertuples(index=False):
            f = fp(row.solute_smiles, radius=radius, n_bits=n_bits)
            if f is None:
                invalid_smiles += 1
                continue
            fps.append(f)
            keep_rows.append(row)
        if len(keep_rows) < 2:
            continue

        pairs = sample_pairs(len(keep_rows), max_pairs_per_solvent, rng)
        counts = {
            "n_pairs_analyzed": 0,
            "n_similar_pairs": 0,
            "n_cliffs": 0,
            "n_easy_positive": 0,
            "n_hard_negative": 0,
            "n_easy_negative": 0,
        }
        solvent_sample_rows: list[dict] = []

        for i, j in pairs:
            sim = float(DataStructs.TanimotoSimilarity(fps[i], fps[j]))
            delta = abs(float(keep_rows[i].mean_ln_x2) - float(keep_rows[j].mean_ln_x2))
            counts["n_pairs_analyzed"] += 1
            if sim >= min_similarity:
                counts["n_similar_pairs"] += 1
            is_cliff = sim >= cliff_similarity and delta > cliff_delta
            is_easy_positive = sim >= cliff_similarity and delta < positive_delta
            is_hard_negative = is_cliff
            is_easy_negative = sim < easy_negative_similarity and delta > cliff_delta
            counts["n_cliffs"] += int(is_cliff)
            counts["n_easy_positive"] += int(is_easy_positive)
            counts["n_hard_negative"] += int(is_hard_negative)
            counts["n_easy_negative"] += int(is_easy_negative)

            if is_cliff or is_easy_positive or is_easy_negative:
                solvent_sample_rows.append(
                    {
                        "solvent_smiles": solvent,
                        "solute_a": keep_rows[i].solute_smiles,
                        "solute_b": keep_rows[j].solute_smiles,
                        "mean_ln_x2_a": float(keep_rows[i].mean_ln_x2),
                        "mean_ln_x2_b": float(keep_rows[j].mean_ln_x2),
                        "tanimoto": sim,
                        "delta_ln_x2": delta,
                        "is_cliff": is_cliff,
                        "is_easy_positive": is_easy_positive,
                        "is_easy_negative": is_easy_negative,
                    }
                )

        solvent_summary = {
            "solvent_smiles": solvent,
            "n_solutes_sampled": len(keep_rows),
            **counts,
            "cliff_rate_all_pairs": counts["n_cliffs"] / max(counts["n_pairs_analyzed"], 1),
            "cliff_rate_similar_pairs": counts["n_cliffs"] / max(counts["n_similar_pairs"], 1),
        }
        solvent_rows.append(solvent_summary)
        all_rows.extend(solvent_sample_rows[:200])

    solvent_df = pd.DataFrame(solvent_rows)
    examples_df = pd.DataFrame(all_rows)

    totals = {
        key: int(solvent_df[key].sum()) if key in solvent_df else 0
        for key in [
            "n_pairs_analyzed",
            "n_similar_pairs",
            "n_cliffs",
            "n_easy_positive",
            "n_hard_negative",
            "n_easy_negative",
        ]
    }
    summary = {
        "data": str(data),
        "seed": seed,
        "max_solutes_per_solvent": max_solutes_per_solvent,
        "max_pairs_per_solvent": max_pairs_per_solvent,
        "thresholds": {
            "min_similarity": min_similarity,
            "cliff_similarity": cliff_similarity,
            "positive_delta": positive_delta,
            "cliff_delta": cliff_delta,
            "easy_negative_similarity": easy_negative_similarity,
        },
        "n_solvents_analyzed": int(len(solvent_df)),
        "invalid_smiles": int(invalid_smiles),
        **totals,
        "cliff_rate_all_pairs": totals["n_cliffs"] / max(totals["n_pairs_analyzed"], 1),
        "cliff_rate_similar_pairs": totals["n_cliffs"] / max(totals["n_similar_pairs"], 1),
        "hard_negative_to_easy_positive_ratio": (
            totals["n_hard_negative"] / max(totals["n_easy_positive"], 1)
        ),
    }

    solvent_df.sort_values("n_cliffs", ascending=False).to_csv(
        output_dir / "solvent_cliff_summary.csv", index=False
    )
    examples_df.sort_values("delta_ln_x2", ascending=False).to_csv(
        output_dir / "cliff_and_contrastive_examples.csv", index=False
    )
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, output_dir / "SUMMARY.md")
    return summary


def write_markdown(summary: dict, path: Path) -> None:
    lines = [
        "# Solubility Cliff Statistics",
        "",
        f"- data: `{summary['data']}`",
        f"- solvents analyzed: `{summary['n_solvents_analyzed']}`",
        f"- pairs analyzed: `{summary['n_pairs_analyzed']}`",
        f"- similar pairs: `{summary['n_similar_pairs']}`",
        f"- cliffs: `{summary['n_cliffs']}`",
        f"- cliff rate, all pairs: `{summary['cliff_rate_all_pairs']:.3f}`",
        f"- cliff rate, similar pairs: `{summary['cliff_rate_similar_pairs']:.3f}`",
        f"- easy positives: `{summary['n_easy_positive']}`",
        f"- easy negatives: `{summary['n_easy_negative']}`",
        f"- hard-negative / easy-positive ratio: `{summary['hard_negative_to_easy_positive_ratio']:.3f}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("notebooks/data/processed/train.csv"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-solutes-per-solvent", type=int, default=200)
    parser.add_argument("--max-pairs-per-solvent", type=int, default=20000)
    parser.add_argument("--radius", type=int, default=2)
    parser.add_argument("--n-bits", type=int, default=2048)
    parser.add_argument("--min-similarity", type=float, default=0.4)
    parser.add_argument("--cliff-similarity", type=float, default=0.6)
    parser.add_argument("--positive-delta", type=float, default=0.5)
    parser.add_argument("--cliff-delta", type=float, default=2.0)
    parser.add_argument("--easy-negative-similarity", type=float, default=0.3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(
        data=args.data,
        output_dir=args.output_dir,
        seed=args.seed,
        max_solutes_per_solvent=args.max_solutes_per_solvent,
        max_pairs_per_solvent=args.max_pairs_per_solvent,
        radius=args.radius,
        n_bits=args.n_bits,
        min_similarity=args.min_similarity,
        cliff_similarity=args.cliff_similarity,
        positive_delta=args.positive_delta,
        cliff_delta=args.cliff_delta,
        easy_negative_similarity=args.easy_negative_similarity,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
