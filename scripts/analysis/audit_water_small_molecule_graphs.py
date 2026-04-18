#!/usr/bin/env python3
"""Audit water and small-molecule graph representations.

This script is intentionally CPU-only. It quantifies:

- how many supervised rows use water or small solvents;
- how legacy H-suppressed graphs differ from the opt-in explicit-H mode;
- current prediction errors on water/small-solvent slices when prediction
  bundles are available.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from rdkit import Chem
except ImportError as exc:  # pragma: no cover
    raise SystemExit("RDKit is required for this audit.") from exc

from tgnn_solv.features import smiles_to_graph


DEFAULT_SPLITS = (
    "train.csv",
    "val.csv",
    "test.csv",
    "train_solute.csv",
    "val_solute.csv",
    "test_solute.csv",
    "train_solvent.csv",
    "val_solvent.csv",
    "test_solvent.csv",
)


def canonicalize(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)


def heavy_atoms(smiles: str) -> int | None:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    return int(mol.GetNumHeavyAtoms())


def load_splits(processed_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for name in DEFAULT_SPLITS:
        path = processed_dir / name
        if path.exists():
            frames[path.stem] = pd.read_csv(path, low_memory=False)
    return frames


def _supervised(frame: pd.DataFrame) -> pd.DataFrame:
    if "has_solubility" in frame.columns:
        return frame[frame["has_solubility"].astype(bool)].copy()
    return frame.copy()


def summarize_split(frame: pd.DataFrame, split_name: str, max_heavy: int) -> dict[str, Any]:
    sup = _supervised(frame)
    if sup.empty:
        return {
            "split": split_name,
            "rows": int(len(frame)),
            "supervised_rows": 0,
        }

    water = canonicalize("O") or "O"
    solvent_heavy = sup["solvent_smiles"].astype(str).map(heavy_atoms)
    solute_heavy = sup["solute_smiles"].astype(str).map(heavy_atoms)
    solvent_canon = sup["solvent_smiles"].astype(str).map(canonicalize)

    water_mask = solvent_canon == water
    small_solvent_mask = solvent_heavy.le(max_heavy).fillna(False)
    small_solute_mask = solute_heavy.le(max_heavy).fillna(False)

    return {
        "split": split_name,
        "rows": int(len(frame)),
        "supervised_rows": int(len(sup)),
        "water_solvent_rows": int(water_mask.sum()),
        "water_solvent_fraction": float(water_mask.mean()),
        "small_solvent_rows": int(small_solvent_mask.sum()),
        "small_solvent_fraction": float(small_solvent_mask.mean()),
        "small_solute_rows": int(small_solute_mask.sum()),
        "small_solute_fraction": float(small_solute_mask.mean()),
        "small_either_rows": int((small_solvent_mask | small_solute_mask).sum()),
        "small_either_fraction": float((small_solvent_mask | small_solute_mask).mean()),
        "unique_water_pairs": int(
            sup.loc[water_mask, ["solute_smiles", "solvent_smiles"]]
            .drop_duplicates()
            .shape[0]
        ),
        "unique_small_solvents": int(
            sup.loc[small_solvent_mask, "solvent_smiles"].nunique()
        ),
        "mean_ln_x2_water": _finite_mean(sup.loc[water_mask, "ln_x2"]),
        "mean_ln_x2_nonwater": _finite_mean(sup.loc[~water_mask, "ln_x2"]),
    }


def _finite_mean(values: pd.Series) -> float | None:
    numeric = pd.to_numeric(values, errors="coerce")
    numeric = numeric[numeric.apply(math.isfinite)]
    if numeric.empty:
        return None
    return float(numeric.mean())


def _json_safe(value: Any) -> Any:
    """Convert pandas/numpy non-finite values into JSON-safe nulls."""
    if isinstance(value, dict):
        return {key: _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def solvent_counts(frames: dict[str, pd.DataFrame], max_heavy: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for split, frame in frames.items():
        sup = _supervised(frame)
        if sup.empty:
            continue
        counts = sup["solvent_smiles"].astype(str).value_counts()
        for smiles, n_rows in counts.items():
            n_heavy = heavy_atoms(smiles)
            if n_heavy is None or n_heavy > max_heavy:
                continue
            rows.append(
                {
                    "split": split,
                    "solvent_smiles": smiles,
                    "canonical_smiles": canonicalize(smiles),
                    "heavy_atoms": n_heavy,
                    "rows": int(n_rows),
                    "fraction": float(n_rows / len(sup)),
                }
            )
    return pd.DataFrame(rows).sort_values(["split", "rows"], ascending=[True, False])


def graph_stats(smiles: str, *, explicit_h: bool, max_heavy: int) -> dict[str, Any]:
    graph = smiles_to_graph(
        smiles,
        use_gasteiger_charges=True,
        use_phys_edge_features=True,
        explicit_h_small_molecules=explicit_h,
        explicit_h_max_heavy_atoms=max_heavy,
    )
    if graph is None:
        return {"smiles": smiles, "explicit_h": explicit_h, "valid": False}

    edge_index = graph.edge_index
    self_loops = int((edge_index[0] == edge_index[1]).sum().item())
    phys_start = 8
    phys_nonzero_fraction = float(
        graph.edge_attr[:, phys_start:].abs().sum(dim=1).gt(0).float().mean().item()
    )
    return {
        "smiles": smiles,
        "canonical_smiles": canonicalize(smiles),
        "explicit_h": explicit_h,
        "valid": True,
        "num_nodes": int(graph.x.shape[0]),
        "num_edges": int(graph.edge_index.shape[1]),
        "self_loop_edges": self_loops,
        "node_dim": int(graph.x.shape[1]),
        "edge_dim": int(graph.edge_attr.shape[1]),
        "num_heavy_atoms": int(getattr(graph, "num_heavy_atoms", heavy_atoms(smiles) or 0)),
        "explicit_h_small_molecule": bool(
            getattr(graph, "explicit_h_small_molecule", False)
        ),
        "phys_edge_nonzero_fraction": phys_nonzero_fraction,
    }


def build_graph_comparison(
    frames: dict[str, pd.DataFrame],
    max_heavy: int,
    examples: list[str],
) -> pd.DataFrame:
    candidate_smiles = set(examples)
    counts = solvent_counts(frames, max_heavy=max_heavy)
    if not counts.empty:
        candidate_smiles.update(counts["solvent_smiles"].head(30).astype(str))

    rows: list[dict[str, Any]] = []
    for smiles in sorted(candidate_smiles):
        rows.append(graph_stats(smiles, explicit_h=False, max_heavy=max_heavy))
        rows.append(graph_stats(smiles, explicit_h=True, max_heavy=max_heavy))
    return pd.DataFrame(rows)


def compute_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    true = pd.to_numeric(frame["ln_x2_true"], errors="coerce")
    pred = pd.to_numeric(frame["ln_x2_pred"], errors="coerce")
    mask = true.notna() & pred.notna()
    true = true[mask]
    pred = pred[mask]
    if true.empty:
        return {"n": 0}
    err = pred - true
    ss_res = float((err**2).sum())
    ss_tot = float(((true - true.mean()) ** 2).sum())
    return {
        "n": int(len(true)),
        "mae": float(err.abs().mean()),
        "rmse": float((err**2).mean() ** 0.5),
        "r2": None if ss_tot <= 0 else float(1.0 - ss_res / ss_tot),
        "mean_true": float(true.mean()),
        "mean_pred": float(pred.mean()),
    }


def prediction_slice_metrics(prediction_dir: Path, max_heavy: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not prediction_dir.exists():
        return pd.DataFrame(rows)

    water = canonicalize("O") or "O"
    for pred_path in sorted(prediction_dir.glob("*/predictions_with_errors.csv")):
        model = pred_path.parent.name
        df = pd.read_csv(pred_path, low_memory=False)
        solvent_canon = df["solvent_smiles"].astype(str).map(canonicalize)
        solvent_heavy = df["solvent_smiles"].astype(str).map(heavy_atoms)
        masks = {
            "all": pd.Series(True, index=df.index),
            "water_solvent": solvent_canon == water,
            "nonwater_solvent": solvent_canon != water,
            f"small_solvent_le_{max_heavy}": solvent_heavy.le(max_heavy).fillna(False),
        }
        for slice_name, mask in masks.items():
            metrics = compute_metrics(df.loc[mask])
            metrics.update(
                {
                    "model": model,
                    "slice": slice_name,
                }
            )
            rows.append(metrics)
    return pd.DataFrame(rows)


def write_summary_md(
    path: Path,
    split_summary: pd.DataFrame,
    graph_comparison: pd.DataFrame,
    error_metrics: pd.DataFrame,
    max_heavy: int,
) -> None:
    water_rows = split_summary.loc[
        split_summary["split"].eq("test"), "water_solvent_rows"
    ]
    water_test = int(water_rows.iloc[0]) if not water_rows.empty else 0
    lines = [
        "# Water / Small-Molecule Graph Audit",
        "",
        f"- Explicit-H threshold audited: <= {max_heavy} heavy atoms.",
        f"- Canonical test water rows: {water_test}.",
        "- Legacy default remains H-suppressed with a self-loop for single-atom graphs.",
        "- Opt-in explicit-H mode turns water into a 3-node / 4-directed-edge graph.",
        "",
        "## Split Summary",
        "",
        split_summary.to_markdown(index=False),
        "",
        "## Graph Comparison",
        "",
        graph_comparison.head(40).to_markdown(index=False),
    ]
    if not error_metrics.empty:
        lines.extend(
            [
                "",
                "## Current Prediction Slices",
                "",
                error_metrics.to_markdown(index=False),
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=Path("notebooks/data/processed"),
    )
    parser.add_argument(
        "--prediction-dir",
        type=Path,
        default=Path("results/prediction_error_slices_latest"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("results/water_small_molecule_audit"),
    )
    parser.add_argument("--max-heavy", type=int, default=3)
    parser.add_argument(
        "--examples",
        nargs="*",
        default=["O", "CO", "CCO", "CC(=O)C", "N", "O=C=O", "Cl"],
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    frames = load_splits(args.processed_dir)
    if not frames:
        raise SystemExit(f"No processed split CSV files found in {args.processed_dir}")

    split_summary = pd.DataFrame(
        [
            summarize_split(frame, split, max_heavy=args.max_heavy)
            for split, frame in frames.items()
        ]
    ).sort_values("split")
    counts = solvent_counts(frames, max_heavy=args.max_heavy)
    graph_comparison = build_graph_comparison(
        frames,
        max_heavy=args.max_heavy,
        examples=list(args.examples),
    )
    error_metrics = prediction_slice_metrics(
        args.prediction_dir,
        max_heavy=args.max_heavy,
    )

    split_summary.to_csv(args.out_dir / "split_water_small_summary.csv", index=False)
    counts.to_csv(args.out_dir / "small_solvent_counts.csv", index=False)
    graph_comparison.to_csv(args.out_dir / "graph_comparison.csv", index=False)
    error_metrics.to_csv(args.out_dir / "prediction_slice_metrics.csv", index=False)

    summary = {
        "processed_dir": str(args.processed_dir),
        "prediction_dir": str(args.prediction_dir),
        "max_heavy": int(args.max_heavy),
        "n_splits": int(len(frames)),
        "split_summary": split_summary.to_dict(orient="records"),
        "water_graph_legacy": graph_stats("O", explicit_h=False, max_heavy=args.max_heavy),
        "water_graph_explicit_h": graph_stats("O", explicit_h=True, max_heavy=args.max_heavy),
    }
    (args.out_dir / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    write_summary_md(
        args.out_dir / "SUMMARY.md",
        split_summary=split_summary,
        graph_comparison=graph_comparison,
        error_metrics=error_metrics,
        max_heavy=args.max_heavy,
    )

    print(f"Wrote water audit to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
