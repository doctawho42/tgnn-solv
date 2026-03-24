#!/usr/bin/env python3
"""Detailed post-hoc error analysis for TGNN-Solv evaluation outputs."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any
import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

try:
    from scipy.stats import spearmanr
except Exception:  # pragma: no cover - optional dependency
    spearmanr = None

try:
    from tgnn_solv.data.utils import canonicalize
except Exception:  # pragma: no cover - optional dependency
    canonicalize = None


TEMP_BIN_EDGES = [-math.inf, 273.0, 298.0, 323.0, 373.0, math.inf]
TEMP_BIN_LABELS = ["<273K", "273-298K", "298-323K", "323-373K", ">373K"]
SOL_BIN_EDGES = [-math.inf, -15.0, -10.0, -5.0, -2.0, math.inf]
SOL_BIN_LABELS = ["<-15", "-15..-10", "-10..-5", "-5..-2", ">-2"]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run detailed error analysis on evaluate_complete.py outputs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--predictions",
        type=str,
        required=True,
        help="JSON file produced by scripts/evaluate_complete.py.",
    )
    parser.add_argument(
        "--test-data",
        type=str,
        required=True,
        help="CSV test dataset with solute_smiles, solvent_smiles, temperature, ln_x2.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/error_analysis.json",
        help="Path to save the analysis JSON.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Number of worst examples to export in detail.",
    )
    return parser.parse_args()


def to_float_array(values: object, key: str) -> np.ndarray:
    """Convert a JSON array to a finite float numpy array."""
    if not isinstance(values, list):
        raise ValueError(f"Expected '{key}' to be a JSON array.")
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"Expected '{key}' to be a 1D array.")
    return arr


def load_predictions(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Load prediction arrays from evaluate_complete.py output."""
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    true = to_float_array(payload.get("true_ln_x2"), "true_ln_x2")
    pred = to_float_array(payload.get("pred_ln_x2"), "pred_ln_x2")
    if true.shape != pred.shape:
        raise ValueError("true_ln_x2 and pred_ln_x2 must have the same length.")

    return true, pred, payload


def load_test_data(path: Path) -> pd.DataFrame:
    """Load the test CSV and validate required columns."""
    df = pd.read_csv(path)
    required = {"solute_smiles", "solvent_smiles", "temperature", "ln_x2"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns in test data: {missing}")
    return df


def align_rows(
    df: pd.DataFrame,
    true_values: np.ndarray,
    pred_values: np.ndarray,
) -> pd.DataFrame:
    """Align valid prediction rows back to the original test dataframe.

    `evaluate_complete.py` stores only valid `(true, pred)` pairs, so the JSON
    does not include original row indices. This function reconstructs the subset
    by matching the ordered `true_ln_x2` sequence against finite `ln_x2` values
    in the CSV.
    """
    finite_df = df[np.isfinite(df["ln_x2"].to_numpy(dtype=float))].copy()
    finite_df = finite_df.reset_index().rename(columns={"index": "row_index"})
    finite_true = finite_df["ln_x2"].to_numpy(dtype=float)

    if len(true_values) > len(finite_df):
        raise ValueError(
            "Prediction JSON contains more valid targets than the test CSV provides."
        )

    if len(true_values) == len(finite_df) and np.allclose(
        finite_true, true_values, rtol=1e-7, atol=1e-8
    ):
        aligned = finite_df.copy()
    else:
        matched_positions: list[int] = []
        cursor = 0
        for target in true_values:
            found = False
            while cursor < len(finite_true):
                if np.isclose(finite_true[cursor], target, rtol=1e-7, atol=1e-8):
                    matched_positions.append(cursor)
                    cursor += 1
                    found = True
                    break
                cursor += 1
            if not found:
                raise ValueError(
                    "Could not align prediction arrays with test-data rows. "
                    "The evaluation JSON does not expose sample indices."
                )
        aligned = finite_df.iloc[matched_positions].copy()

    aligned = aligned.reset_index(drop=True)
    aligned["true_ln_x2"] = true_values
    aligned["pred_ln_x2"] = pred_values
    aligned["signed_error"] = aligned["pred_ln_x2"] - aligned["true_ln_x2"]
    aligned["abs_error"] = aligned["signed_error"].abs()
    return aligned


def safe_mean(values: pd.Series | np.ndarray) -> float | None:
    """Return a finite mean or None."""
    if len(values) == 0:
        return None
    value = float(np.mean(np.asarray(values, dtype=float)))
    return value if math.isfinite(value) else None


def safe_std(values: pd.Series | np.ndarray) -> float | None:
    """Return a finite sample standard deviation or None."""
    if len(values) == 0:
        return None
    arr = np.asarray(values, dtype=float)
    value = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    return value if math.isfinite(value) else None


def solvent_display_name(smiles: str, solvent_name: object = None) -> str:
    """Return a human-readable solvent label."""
    if isinstance(solvent_name, str) and solvent_name.strip():
        return solvent_name.strip()

    canonical = smiles
    if canonicalize is not None:
        try:
            converted = canonicalize(smiles)
            if converted:
                canonical = converted
        except Exception:
            canonical = smiles

    aliases = {
        "O": "water",
        "CS(=O)C": "DMSO",
        "CCO": "ethanol",
        "CO": "methanol",
        "CC#N": "acetonitrile",
        "CC(=O)C": "acetone",
    }
    return aliases.get(canonical, smiles)


def summarize_top_solvents(df: pd.DataFrame, top_k: int = 5) -> list[dict[str, Any]]:
    """Summarize the most common solvents in a dataframe slice."""
    if len(df) == 0:
        return []

    rows: list[dict[str, Any]] = []
    total = len(df)
    grouped = (
        df.groupby("solvent_smiles", dropna=False)
        .agg(
            count=("solvent_smiles", "size"),
            solvent_name=("solvent_name", "first") if "solvent_name" in df.columns else ("solvent_smiles", "first"),
        )
        .sort_values("count", ascending=False)
        .head(top_k)
    )
    for solvent_smiles, row in grouped.iterrows():
        count = int(row["count"])
        rows.append(
            {
                "solvent_smiles": solvent_smiles,
                "solvent_label": solvent_display_name(solvent_smiles, row.get("solvent_name")),
                "count": count,
                "fraction": count / total,
            }
        )
    return rows


def analyze_worst_predictions(df: pd.DataFrame, top_n: int) -> dict[str, Any]:
    """Analyze the worst 5 percent of predictions by absolute error."""
    if len(df) == 0:
        return {
            "n_samples": 0,
            "mean_abs_error": None,
            "mean_temperature": None,
            "mean_true_ln_x2": None,
            "common_solvents": [],
            "examples": [],
        }

    worst_count = max(int(math.ceil(0.05 * len(df))), 1)
    worst_df = df.nlargest(worst_count, "abs_error").copy()
    example_columns = [
        "row_index",
        "solute_smiles",
        "solvent_smiles",
        "temperature",
        "true_ln_x2",
        "pred_ln_x2",
        "signed_error",
        "abs_error",
    ]
    if "solute_name" in worst_df.columns:
        example_columns.insert(2, "solute_name")
    if "solvent_name" in worst_df.columns:
        example_columns.insert(4, "solvent_name")

    examples = (
        worst_df.nlargest(top_n, "abs_error")[example_columns]
        .to_dict(orient="records")
    )
    return {
        "n_samples": int(worst_count),
        "fraction": worst_count / len(df),
        "mean_abs_error": safe_mean(worst_df["abs_error"]),
        "mean_signed_error": safe_mean(worst_df["signed_error"]),
        "mean_temperature": safe_mean(worst_df["temperature"]),
        "mean_true_ln_x2": safe_mean(worst_df["true_ln_x2"]),
        "common_solvents": summarize_top_solvents(worst_df),
        "examples": examples,
    }


def summarize_bias_by_bins(
    df: pd.DataFrame,
    column: str,
    bin_edges: list[float],
    labels: list[str],
) -> list[dict[str, Any]]:
    """Group signed errors into named bins."""
    bucketed = pd.cut(
        df[column],
        bins=bin_edges,
        labels=labels,
        right=False,
        include_lowest=True,
    )
    rows: list[dict[str, Any]] = []
    for label in labels:
        subset = df[bucketed == label]
        rows.append(
            {
                "bin": label,
                "count": int(len(subset)),
                "mean_signed_error": safe_mean(subset["signed_error"]),
                "std_signed_error": safe_std(subset["signed_error"]),
                "mean_abs_error": safe_mean(subset["abs_error"]),
            }
        )
    return rows


def analyze_by_solvent(df: pd.DataFrame, min_samples: int = 10) -> list[dict[str, Any]]:
    """Compute per-solvent difficulty statistics."""
    rows: list[dict[str, Any]] = []
    grouped = df.groupby("solvent_smiles", dropna=False)
    for solvent_smiles, group in grouped:
        if len(group) < min_samples:
            continue
        solvent_name = group["solvent_name"].dropna().iloc[0] if "solvent_name" in group.columns and group["solvent_name"].notna().any() else None
        rows.append(
            {
                "solvent_smiles": solvent_smiles,
                "solvent_label": solvent_display_name(solvent_smiles, solvent_name),
                "n_samples": int(len(group)),
                "mae": safe_mean(group["abs_error"]),
                "mean_signed_error": safe_mean(group["signed_error"]),
            }
        )
    rows.sort(
        key=lambda item: (
            -float(item["mae"]) if item["mae"] is not None else math.inf,
            -item["n_samples"],
            item["solvent_label"],
        )
    )
    return rows


def analyze_ionic_compounds(df: pd.DataFrame) -> dict[str, Any]:
    """Compute error statistics for ionic or multi-component systems."""
    ionic_mask = (
        df["solute_smiles"].astype(str).str.contains(r"\[\+\]|\[-\]|\.")
        | df["solvent_smiles"].astype(str).str.contains(r"\[\+\]|\[-\]|\.")
    )
    ionic_df = df[ionic_mask]
    non_ionic_df = df[~ionic_mask]
    return {
        "n_ionic": int(len(ionic_df)),
        "n_non_ionic": int(len(non_ionic_df)),
        "ionic_mae": safe_mean(ionic_df["abs_error"]),
        "ionic_mean_signed_error": safe_mean(ionic_df["signed_error"]),
        "non_ionic_mae": safe_mean(non_ionic_df["abs_error"]),
        "non_ionic_mean_signed_error": safe_mean(non_ionic_df["signed_error"]),
    }


def analyze_descriptor_correlations(df: pd.DataFrame) -> dict[str, Any]:
    """Compute RDKit descriptor correlations with absolute error."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors
    except Exception:
        print("WARNING: RDKit not available; skipping descriptor correlations.")
        return {
            "available": False,
            "reason": "rdkit_not_available",
            "top_correlations": [],
        }

    if spearmanr is None:
        print("WARNING: SciPy not available; skipping descriptor correlations.")
        return {
            "available": False,
            "reason": "scipy_not_available",
            "top_correlations": [],
        }

    descriptor_cache: dict[str, dict[str, float] | None] = {}

    def compute_descriptors(smiles: str) -> dict[str, float] | None:
        if smiles in descriptor_cache:
            return descriptor_cache[smiles]
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            descriptor_cache[smiles] = None
            return None
        descriptor_cache[smiles] = {
            "solute_MW": float(Descriptors.MolWt(mol)),
            "solute_LogP": float(Crippen.MolLogP(mol)),
            "solute_HBA": float(Lipinski.NumHAcceptors(mol)),
            "solute_HBD": float(Lipinski.NumHDonors(mol)),
            "solute_TPSA": float(rdMolDescriptors.CalcTPSA(mol)),
            "solute_n_rings": float(rdMolDescriptors.CalcNumRings(mol)),
            "solute_n_rotatable": float(rdMolDescriptors.CalcNumRotatableBonds(mol)),
        }
        return descriptor_cache[smiles]

    rows: list[dict[str, float]] = []
    for row in df.itertuples(index=False):
        descriptor_values = compute_descriptors(str(row.solute_smiles))
        if descriptor_values is None:
            continue
        rows.append(
            {
                **descriptor_values,
                "abs_error": float(row.abs_error),
            }
        )

    if not rows:
        return {
            "available": False,
            "reason": "no_valid_rdkit_molecules",
            "top_correlations": [],
        }

    descriptor_df = pd.DataFrame(rows)
    correlations: list[dict[str, Any]] = []
    for column in descriptor_df.columns:
        if column == "abs_error":
            continue
        subset = descriptor_df[[column, "abs_error"]].dropna()
        if len(subset) < 3 or subset[column].nunique() < 2:
            continue
        corr, p_value = spearmanr(subset[column].to_numpy(), subset["abs_error"].to_numpy())
        if not np.isfinite(corr):
            continue
        correlations.append(
            {
                "descriptor": column,
                "spearman_r": float(corr),
                "p_value": float(p_value) if p_value is not None and np.isfinite(p_value) else None,
                "n_samples": int(len(subset)),
            }
        )

    correlations.sort(key=lambda item: abs(item["spearman_r"]), reverse=True)
    return {
        "available": True,
        "n_valid_samples": int(len(descriptor_df)),
        "top_correlations": correlations[:5],
        "all_correlations": correlations,
    }


def print_summary(
    analysis: dict[str, Any],
    bias_by_temperature: list[dict[str, Any]],
    solvent_analysis: list[dict[str, Any]],
    descriptor_analysis: dict[str, Any],
) -> None:
    """Print a concise human-readable summary."""
    print("=== Error Analysis Summary ===")
    print(f"Total samples: {analysis['total_samples']}")
    print(f"Overall MAE: {analysis['overall_mae']:.4f}")
    print()

    worst = analysis["worst_predictions"]
    print(f"Worst 5% ({worst['n_samples']} samples):")
    print(f"  Mean error: {worst['mean_abs_error']:.4f}" if worst["mean_abs_error"] is not None else "  Mean error: n/a")
    if worst["common_solvents"]:
        solvent_parts = [
            f"{item['solvent_label']} ({100 * item['fraction']:.0f}%)"
            for item in worst["common_solvents"][:5]
        ]
        print(f"  Most common solvents: {', '.join(solvent_parts)}")
    else:
        print("  Most common solvents: n/a")
    print()

    print("Bias by temperature:")
    for row in bias_by_temperature:
        bias = row["mean_signed_error"]
        if bias is None:
            print(f"  {row['bin']}: bias=n/a, n={row['count']}")
            continue
        direction = "overpredict" if bias > 0 else "underpredict" if bias < 0 else "neutral"
        print(f"  {row['bin']}: bias={bias:+.3f} ({direction}), n={row['count']}")
    print()

    print("Top 5 hardest solvents:")
    if not solvent_analysis:
        print("  No solvents with at least 10 samples.")
    else:
        for idx, row in enumerate(solvent_analysis[:5], start=1):
            print(
                f"  {idx}. {row['solvent_label']} "
                f"(MAE={row['mae']:.3f}, n={row['n_samples']})"
            )
    print()

    print("Descriptor correlations with error:")
    if not descriptor_analysis.get("available"):
        print(f"  Skipped ({descriptor_analysis.get('reason', 'unavailable')})")
    else:
        for row in descriptor_analysis.get("top_correlations", []):
            p_text = "n/a" if row["p_value"] is None else f"{row['p_value']:.3g}"
            print(
                f"  {row['descriptor']}: "
                f"r={row['spearman_r']:+.3f} (p={p_text})"
            )


def main() -> int:
    """Run the detailed error analysis pipeline."""
    args = parse_args()

    predictions_path = _bootstrap.resolve_path(args.predictions)
    test_data_path = _bootstrap.resolve_path(args.test_data)
    output_path = _bootstrap.resolve_path(args.output)

    true_values, pred_values, prediction_payload = load_predictions(predictions_path)
    test_df = load_test_data(test_data_path)
    aligned_df = align_rows(test_df, true_values, pred_values)

    overall_mae = float(aligned_df["abs_error"].mean()) if len(aligned_df) else float("nan")
    worst_predictions = analyze_worst_predictions(aligned_df, top_n=args.top_n)
    bias_by_temperature = summarize_bias_by_bins(
        aligned_df,
        column="temperature",
        bin_edges=TEMP_BIN_EDGES,
        labels=TEMP_BIN_LABELS,
    )
    bias_by_solubility = summarize_bias_by_bins(
        aligned_df,
        column="true_ln_x2",
        bin_edges=SOL_BIN_EDGES,
        labels=SOL_BIN_LABELS,
    )
    solvent_analysis = analyze_by_solvent(aligned_df)
    descriptor_analysis = analyze_descriptor_correlations(aligned_df)
    ionic_analysis = analyze_ionic_compounds(aligned_df)

    analysis = {
        "predictions_file": str(predictions_path),
        "test_data_file": str(test_data_path),
        "total_samples": int(len(aligned_df)),
        "n_input_predictions": int(len(true_values)),
        "overall_mae": overall_mae,
        "overall_bias": safe_mean(aligned_df["signed_error"]),
        "overall_rmse": float(np.sqrt(np.mean(np.square(aligned_df["signed_error"])))) if len(aligned_df) else None,
        "prediction_metadata": {
            "n_valid_predictions": prediction_payload.get("n_valid_predictions"),
            "overall_metrics": prediction_payload.get("overall"),
        },
        "worst_predictions": worst_predictions,
        "bias_by_temperature": bias_by_temperature,
        "bias_by_solubility": bias_by_solubility,
        "solvent_analysis": solvent_analysis,
        "descriptor_correlations": descriptor_analysis,
        "ionic_analysis": ionic_analysis,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)

    print_summary(
        analysis=analysis,
        bias_by_temperature=bias_by_temperature,
        solvent_analysis=solvent_analysis,
        descriptor_analysis=descriptor_analysis,
    )
    print()
    print(f"Saved error analysis to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
