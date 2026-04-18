#!/usr/bin/env python
"""Analyze scaffold-test errors by BRICS fragment compositionality.

The diagnostic asks whether test solutes are composed only of BRICS fragments
that were observed in train solutes. It then compares prediction errors for:

- composed solutes: every BRICS fragment appears in train
- novel solutes: at least one BRICS fragment is unseen

This is a prediction-only analysis. It does not train or run a model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import BRICS


SOLUTE_CANDIDATES = (
    "solute_smiles",
    "SMILES_Solute",
    "smiles_solute",
    "solute",
)
TRUE_CANDIDATES = ("ln_x2_true", "y_true", "true", "ln_x2", "target")
PRED_CANDIDATES = ("ln_x2_pred", "prediction", "pred", "y_pred")
ERROR_CANDIDATES = ("abs_error", "absolute_error", "ae")


def _detect_column(df: pd.DataFrame, candidates: Iterable[str], label: str) -> str:
    for col in candidates:
        if col in df.columns:
            return col
    raise ValueError(
        f"Could not detect {label} column. Tried: {', '.join(candidates)}. "
        f"Available: {', '.join(df.columns)}"
    )


def _mol_from_smiles(smiles: str | float | None) -> Chem.Mol | None:
    if not isinstance(smiles, str) or not smiles.strip():
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return mol


def _brics_fragments(smiles: str | float | None) -> tuple[str, ...]:
    mol = _mol_from_smiles(smiles)
    if mol is None:
        return tuple()
    fragments = BRICS.BRICSDecompose(mol)
    if not fragments:
        # BRICS returns a singleton for most valid molecules, but keep a robust
        # fallback for edge cases.
        return (Chem.MolToSmiles(mol, canonical=True),)
    return tuple(sorted(fragments))


def _safe_mean(values: pd.Series) -> float | None:
    if len(values) == 0:
        return None
    return float(values.mean())


def _safe_median(values: pd.Series) -> float | None:
    if len(values) == 0:
        return None
    return float(values.median())


def _slice_metrics(df: pd.DataFrame, mask: pd.Series, error_col: str) -> dict[str, float | int | None]:
    values = df.loc[mask, error_col]
    return {
        "n_rows": int(mask.sum()),
        "mae": _safe_mean(values),
        "median_abs_error": _safe_median(values),
        "p90_abs_error": None if len(values) == 0 else float(values.quantile(0.90)),
    }


def _build_train_fragment_set(train_df: pd.DataFrame, solute_col: str) -> set[str]:
    fragments: set[str] = set()
    for smiles in sorted(set(train_df[solute_col].dropna().astype(str))):
        fragments.update(_brics_fragments(smiles))
    return fragments


def run_analysis(
    train_path: Path,
    test_predictions_path: Path,
    output_dir: Path,
    train_solute_col: str | None = None,
    test_solute_col: str | None = None,
    true_col: str | None = None,
    pred_col: str | None = None,
    error_col: str | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(train_path)
    pred_df = pd.read_csv(test_predictions_path)

    train_solute_col = train_solute_col or _detect_column(train_df, SOLUTE_CANDIDATES, "train solute")
    test_solute_col = test_solute_col or _detect_column(pred_df, SOLUTE_CANDIDATES, "test solute")

    if error_col is None:
        error_col = next((col for col in ERROR_CANDIDATES if col in pred_df.columns), None)
    if error_col is None:
        true_col = true_col or _detect_column(pred_df, TRUE_CANDIDATES, "true target")
        pred_col = pred_col or _detect_column(pred_df, PRED_CANDIDATES, "prediction")
        error_col = "abs_error"
        pred_df[error_col] = (pred_df[pred_col].astype(float) - pred_df[true_col].astype(float)).abs()

    train_fragments = _build_train_fragment_set(train_df, train_solute_col)

    unique_solute_rows = []
    solute_to_is_composed: dict[str, bool] = {}
    solute_to_novel_fragments: dict[str, list[str]] = {}
    solute_to_fragments: dict[str, tuple[str, ...]] = {}

    for smiles in sorted(set(pred_df[test_solute_col].dropna().astype(str))):
        fragments = _brics_fragments(smiles)
        novel = sorted(frag for frag in fragments if frag not in train_fragments)
        is_valid = bool(fragments)
        is_composed = is_valid and not novel
        solute_to_is_composed[smiles] = is_composed
        solute_to_novel_fragments[smiles] = novel
        solute_to_fragments[smiles] = fragments
        unique_solute_rows.append(
            {
                "solute_smiles": smiles,
                "n_brics_fragments": len(fragments),
                "n_novel_brics_fragments": len(novel),
                "is_composed_from_train_brics": is_composed,
                "brics_fragments": "|".join(fragments),
                "novel_brics_fragments": "|".join(novel),
            }
        )

    pred_df["is_composed_from_train_brics"] = (
        pred_df[test_solute_col].astype(str).map(solute_to_is_composed).fillna(False)
    )
    pred_df["n_brics_fragments"] = pred_df[test_solute_col].astype(str).map(
        lambda smiles: len(solute_to_fragments.get(smiles, tuple()))
    )
    pred_df["n_novel_brics_fragments"] = pred_df[test_solute_col].astype(str).map(
        lambda smiles: len(solute_to_novel_fragments.get(smiles, []))
    )

    composed_mask = pred_df["is_composed_from_train_brics"].astype(bool)
    novel_mask = ~composed_mask

    row_composed = _slice_metrics(pred_df, composed_mask, error_col)
    row_novel = _slice_metrics(pred_df, novel_mask, error_col)
    row_gap = None
    if row_composed["mae"] is not None and row_novel["mae"] is not None:
        row_gap = float(row_novel["mae"] - row_composed["mae"])

    solute_summary = (
        pred_df.groupby(test_solute_col, as_index=False)
        .agg(
            mean_abs_error=(error_col, "mean"),
            median_abs_error=(error_col, "median"),
            n_rows=(error_col, "size"),
            is_composed_from_train_brics=("is_composed_from_train_brics", "first"),
            n_brics_fragments=("n_brics_fragments", "first"),
            n_novel_brics_fragments=("n_novel_brics_fragments", "first"),
        )
        .rename(columns={test_solute_col: "solute_smiles"})
    )

    sol_composed_mask = solute_summary["is_composed_from_train_brics"].astype(bool)
    sol_novel_mask = ~sol_composed_mask
    sol_composed = _slice_metrics(solute_summary, sol_composed_mask, "mean_abs_error")
    sol_novel = _slice_metrics(solute_summary, sol_novel_mask, "mean_abs_error")
    sol_gap = None
    if sol_composed["mae"] is not None and sol_novel["mae"] is not None:
        sol_gap = float(sol_novel["mae"] - sol_composed["mae"])

    summary = {
        "train_path": str(train_path),
        "test_predictions_path": str(test_predictions_path),
        "train_solute_col": train_solute_col,
        "test_solute_col": test_solute_col,
        "error_col": error_col,
        "n_train_rows": int(len(train_df)),
        "n_test_prediction_rows": int(len(pred_df)),
        "n_train_unique_solutes": int(train_df[train_solute_col].nunique()),
        "n_test_unique_solutes": int(solute_summary["solute_smiles"].nunique()),
        "n_train_unique_brics_fragments": int(len(train_fragments)),
        "row_level": {
            "composed": row_composed,
            "novel": row_novel,
            "mae_gap_novel_minus_composed": row_gap,
            "composed_fraction": float(composed_mask.mean()) if len(pred_df) else None,
        },
        "solute_level": {
            "composed": sol_composed,
            "novel": sol_novel,
            "mae_gap_novel_minus_composed": sol_gap,
            "composed_fraction": float(sol_composed_mask.mean()) if len(solute_summary) else None,
        },
    }

    pred_df.to_csv(output_dir / "rows_with_compositional_flags.csv", index=False)
    solute_summary.to_csv(output_dir / "solute_compositional_summary.csv", index=False)
    pd.DataFrame(unique_solute_rows).to_csv(output_dir / "solute_brics_fragments.csv", index=False)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown(summary, output_dir / "SUMMARY.md")

    return summary


def _fmt(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def _write_markdown(summary: dict, path: Path) -> None:
    row = summary["row_level"]
    sol = summary["solute_level"]
    lines = [
        "# BRICS Compositional Generalization Diagnostic",
        "",
        f"- train: `{summary['train_path']}`",
        f"- predictions: `{summary['test_predictions_path']}`",
        f"- train unique BRICS fragments: `{summary['n_train_unique_brics_fragments']}`",
        "",
        "## Row Level",
        "",
        "| Slice | n | MAE | Median AE | P90 AE |",
        "|---|---:|---:|---:|---:|",
        (
            f"| Composed | {row['composed']['n_rows']} | "
            f"{_fmt(row['composed']['mae'])} | "
            f"{_fmt(row['composed']['median_abs_error'])} | "
            f"{_fmt(row['composed']['p90_abs_error'])} |"
        ),
        (
            f"| Novel | {row['novel']['n_rows']} | "
            f"{_fmt(row['novel']['mae'])} | "
            f"{_fmt(row['novel']['median_abs_error'])} | "
            f"{_fmt(row['novel']['p90_abs_error'])} |"
        ),
        "",
        f"- row composed fraction: `{_fmt(row['composed_fraction'])}`",
        f"- row MAE gap, novel - composed: `{_fmt(row['mae_gap_novel_minus_composed'])}`",
        "",
        "## Unique Solute Level",
        "",
        "| Slice | n | Mean Solute MAE | Median Solute AE | P90 Solute AE |",
        "|---|---:|---:|---:|---:|",
        (
            f"| Composed | {sol['composed']['n_rows']} | "
            f"{_fmt(sol['composed']['mae'])} | "
            f"{_fmt(sol['composed']['median_abs_error'])} | "
            f"{_fmt(sol['composed']['p90_abs_error'])} |"
        ),
        (
            f"| Novel | {sol['novel']['n_rows']} | "
            f"{_fmt(sol['novel']['mae'])} | "
            f"{_fmt(sol['novel']['median_abs_error'])} | "
            f"{_fmt(sol['novel']['p90_abs_error'])} |"
        ),
        "",
        f"- solute composed fraction: `{_fmt(sol['composed_fraction'])}`",
        f"- solute MAE gap, novel - composed: `{_fmt(sol['mae_gap_novel_minus_composed'])}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=Path("notebooks/data/processed/train.csv"))
    parser.add_argument("--test-predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--train-solute-col", default=None)
    parser.add_argument("--test-solute-col", default=None)
    parser.add_argument("--true-col", default=None)
    parser.add_argument("--pred-col", default=None)
    parser.add_argument("--error-col", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_analysis(
        train_path=args.train,
        test_predictions_path=args.test_predictions,
        output_dir=args.output_dir,
        train_solute_col=args.train_solute_col,
        test_solute_col=args.test_solute_col,
        true_col=args.true_col,
        pred_col=args.pred_col,
        error_col=args.error_col,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
