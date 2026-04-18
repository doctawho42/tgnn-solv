#!/usr/bin/env python3
"""Build a pairwise solubility-contrastive pretraining CSV.

The output contains same-solvent solute pairs sampled into three classes:

- easy_positive: structurally similar and similar mean ln(x2)
- hard_negative: structurally similar but large mean ln(x2) gap
- easy_negative: structurally dissimilar and large mean ln(x2) gap

This script materializes the data artifact only. It does not modify SLE splits
and does not start pretraining.
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build pairwise solubility contrastive pretraining pairs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input-csv", default="notebooks/data/processed/train.csv")
    parser.add_argument(
        "--output-csv",
        default="notebooks/data/processed_pairwise_contrastive/pairwise_contrastive_train.csv",
    )
    parser.add_argument(
        "--summary-json",
        default="notebooks/data/processed_pairwise_contrastive/summary.json",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--morgan-radius", type=int, default=2)
    parser.add_argument("--morgan-n-bits", type=int, default=2048)
    parser.add_argument("--max-solutes-per-solvent", type=int, default=250)
    parser.add_argument("--max-candidate-pairs-per-solvent", type=int, default=30000)
    parser.add_argument("--max-easy-positive-per-solvent", type=int, default=100)
    parser.add_argument("--max-hard-negative-per-solvent", type=int, default=100)
    parser.add_argument("--max-easy-negative-per-solvent", type=int, default=100)
    parser.add_argument("--target-max-rows", type=int, default=0)
    parser.add_argument("--positive-similarity", type=float, default=0.6)
    parser.add_argument("--hard-negative-similarity", type=float, default=0.6)
    parser.add_argument("--easy-negative-similarity", type=float, default=0.3)
    parser.add_argument("--positive-delta-ln-x2", type=float, default=0.5)
    parser.add_argument("--negative-delta-ln-x2", type=float, default=2.0)
    parser.add_argument("--easy-negative-weight", type=float, default=0.5)
    parser.add_argument("--hard-negative-weight", type=float, default=1.0)
    parser.add_argument("--positive-weight", type=float, default=1.0)
    return parser.parse_args()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _fingerprint(smiles: str, radius: int, n_bits: int):
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)


def _sample_pairs(
    n_items: int,
    max_pairs: int,
    rng: np.random.Generator,
) -> list[tuple[int, int]]:
    total = n_items * (n_items - 1) // 2
    if total <= max_pairs:
        return list(combinations(range(n_items), 2))
    seen: set[tuple[int, int]] = set()
    while len(seen) < max_pairs:
        i = int(rng.integers(0, n_items))
        j = int(rng.integers(0, n_items - 1))
        if j >= i:
            j += 1
        seen.add(tuple(sorted((i, j))))
    return sorted(seen)


def _take_quota(
    rows: list[dict[str, Any]],
    quota: int,
    rng: np.random.Generator,
) -> list[dict[str, Any]]:
    if quota <= 0 or len(rows) <= quota:
        return rows
    idx = rng.choice(len(rows), size=quota, replace=False)
    return [rows[int(i)] for i in np.sort(idx)]


def _load_pair_means(input_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(input_csv, low_memory=False)
    required = {"solute_smiles", "solvent_smiles", "ln_x2"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{input_csv} is missing columns: {sorted(missing)}")
    work = df.dropna(subset=["solute_smiles", "solvent_smiles", "ln_x2"]).copy()
    if "has_solubility" in work.columns:
        has = work["has_solubility"].astype(str).str.lower().isin({"true", "1", "yes"})
        work = work.loc[has].copy()
    work["ln_x2"] = pd.to_numeric(work["ln_x2"], errors="coerce")
    work = work.loc[np.isfinite(work["ln_x2"].to_numpy(dtype=float))].copy()
    return (
        work.groupby(["solvent_smiles", "solute_smiles"], as_index=False)
        .agg(
            mean_ln_x2=("ln_x2", "mean"),
            median_ln_x2=("ln_x2", "median"),
            std_ln_x2=("ln_x2", "std"),
            n_temperature_points=("ln_x2", "size"),
            min_temperature=(
                "temperature",
                "min",
            )
            if "temperature" in work.columns
            else ("ln_x2", "size"),
            max_temperature=(
                "temperature",
                "max",
            )
            if "temperature" in work.columns
            else ("ln_x2", "size"),
        )
    )


def _build_for_solvent(
    solvent: str,
    group: pd.DataFrame,
    args: argparse.Namespace,
    rng: np.random.Generator,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(group) > args.max_solutes_per_solvent:
        idx = rng.choice(len(group), size=args.max_solutes_per_solvent, replace=False)
        group = group.iloc[np.sort(idx)].reset_index(drop=True)
    else:
        group = group.reset_index(drop=True)

    keep_rows = []
    fps = []
    for row in group.itertuples(index=False):
        fp = _fingerprint(
            row.solute_smiles,
            radius=args.morgan_radius,
            n_bits=args.morgan_n_bits,
        )
        if fp is None:
            continue
        keep_rows.append(row)
        fps.append(fp)

    buckets: dict[str, list[dict[str, Any]]] = {
        "easy_positive": [],
        "hard_negative": [],
        "easy_negative": [],
    }
    if len(keep_rows) < 2:
        return [], {
            "solvent_smiles": solvent,
            "n_solutes": len(keep_rows),
            "n_candidate_pairs": 0,
            "easy_positive": 0,
            "hard_negative": 0,
            "easy_negative": 0,
        }

    candidate_pairs = _sample_pairs(
        len(keep_rows),
        max_pairs=args.max_candidate_pairs_per_solvent,
        rng=rng,
    )

    for i, j in candidate_pairs:
        row_a = keep_rows[i]
        row_b = keep_rows[j]
        tanimoto = float(DataStructs.TanimotoSimilarity(fps[i], fps[j]))
        delta = abs(float(row_a.mean_ln_x2) - float(row_b.mean_ln_x2))

        pair_type: str | None = None
        label: int | None = None
        weight: float | None = None
        if (
            tanimoto >= args.positive_similarity
            and delta < args.positive_delta_ln_x2
        ):
            pair_type = "easy_positive"
            label = 1
            weight = float(args.positive_weight)
        elif (
            tanimoto >= args.hard_negative_similarity
            and delta > args.negative_delta_ln_x2
        ):
            pair_type = "hard_negative"
            label = 0
            weight = float(args.hard_negative_weight)
        elif (
            tanimoto <= args.easy_negative_similarity
            and delta > args.negative_delta_ln_x2
        ):
            pair_type = "easy_negative"
            label = 0
            weight = float(args.easy_negative_weight)

        if pair_type is None:
            continue

        buckets[pair_type].append(
            {
                "solvent_smiles": solvent,
                "solute_a_smiles": row_a.solute_smiles,
                "solute_b_smiles": row_b.solute_smiles,
                "mean_ln_x2_a": float(row_a.mean_ln_x2),
                "mean_ln_x2_b": float(row_b.mean_ln_x2),
                "median_ln_x2_a": float(row_a.median_ln_x2),
                "median_ln_x2_b": float(row_b.median_ln_x2),
                "n_temperature_points_a": int(row_a.n_temperature_points),
                "n_temperature_points_b": int(row_b.n_temperature_points),
                "min_temperature_a": float(row_a.min_temperature),
                "max_temperature_a": float(row_a.max_temperature),
                "min_temperature_b": float(row_b.min_temperature),
                "max_temperature_b": float(row_b.max_temperature),
                "tanimoto": tanimoto,
                "delta_ln_x2": delta,
                "pair_type": pair_type,
                "contrastive_label": int(label),
                "sample_weight": float(weight),
            }
        )

    selected = (
        _take_quota(buckets["easy_positive"], args.max_easy_positive_per_solvent, rng)
        + _take_quota(buckets["hard_negative"], args.max_hard_negative_per_solvent, rng)
        + _take_quota(buckets["easy_negative"], args.max_easy_negative_per_solvent, rng)
    )
    rng.shuffle(selected)
    summary = {
        "solvent_smiles": solvent,
        "n_solutes": len(keep_rows),
        "n_candidate_pairs": len(candidate_pairs),
        "easy_positive": len(buckets["easy_positive"]),
        "hard_negative": len(buckets["hard_negative"]),
        "easy_negative": len(buckets["easy_negative"]),
        "selected_easy_positive": sum(row["pair_type"] == "easy_positive" for row in selected),
        "selected_hard_negative": sum(row["pair_type"] == "hard_negative" for row in selected),
        "selected_easy_negative": sum(row["pair_type"] == "easy_negative" for row in selected),
    }
    return selected, summary


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    summary_json = Path(args.summary_json)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)

    pair_means = _load_pair_means(input_csv)
    all_rows: list[dict[str, Any]] = []
    solvent_summaries: list[dict[str, Any]] = []
    grouped = list(pair_means.groupby("solvent_smiles", sort=False))
    for solvent, group in tqdm(grouped, desc="Sampling solvent groups"):
        selected, summary = _build_for_solvent(str(solvent), group, args, rng)
        all_rows.extend(selected)
        solvent_summaries.append(summary)

    out = pd.DataFrame(all_rows)
    if args.target_max_rows > 0 and len(out) > args.target_max_rows:
        out = out.sample(n=args.target_max_rows, random_state=args.seed).reset_index(drop=True)
    else:
        out = out.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)

    out.to_csv(output_csv, index=False)
    solvent_df = pd.DataFrame(solvent_summaries)
    solvent_summary_csv = summary_json.with_name("solvent_sampling_summary.csv")
    solvent_df.to_csv(solvent_summary_csv, index=False)

    pair_type_counts = (
        out["pair_type"].value_counts().to_dict()
        if "pair_type" in out.columns
        else {}
    )
    summary_payload = {
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "solvent_sampling_summary_csv": str(solvent_summary_csv),
        "seed": args.seed,
        "n_pair_mean_rows": int(len(pair_means)),
        "n_solvents_considered": int(len(grouped)),
        "n_output_rows": int(len(out)),
        "pair_type_counts": {str(k): int(v) for k, v in pair_type_counts.items()},
        "label_counts": (
            {str(k): int(v) for k, v in out["contrastive_label"].value_counts().to_dict().items()}
            if "contrastive_label" in out.columns
            else {}
        ),
        "thresholds": {
            "positive_similarity": args.positive_similarity,
            "hard_negative_similarity": args.hard_negative_similarity,
            "easy_negative_similarity": args.easy_negative_similarity,
            "positive_delta_ln_x2": args.positive_delta_ln_x2,
            "negative_delta_ln_x2": args.negative_delta_ln_x2,
        },
        "sampling": {
            "max_solutes_per_solvent": args.max_solutes_per_solvent,
            "max_candidate_pairs_per_solvent": args.max_candidate_pairs_per_solvent,
            "max_easy_positive_per_solvent": args.max_easy_positive_per_solvent,
            "max_hard_negative_per_solvent": args.max_hard_negative_per_solvent,
            "max_easy_negative_per_solvent": args.max_easy_negative_per_solvent,
            "target_max_rows": args.target_max_rows,
        },
    }
    summary_json.write_text(
        json.dumps(_json_safe(summary_payload), indent=2),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary_payload), indent=2))


if __name__ == "__main__":
    main()
