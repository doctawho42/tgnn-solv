#!/usr/bin/env python
"""Analyze prediction error as a function of nearest train scaffold distance.

For each scaffold-test solute, the script computes the Murcko scaffold,
finds the nearest train-solute scaffold by Morgan Tanimoto similarity, and
correlates scaffold distance (1 - max similarity) with absolute prediction
error.

This is a prediction-only analysis. It does not train or run a model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from rdkit.Chem.Scaffolds import MurckoScaffold


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
    return Chem.MolFromSmiles(smiles)


def _scaffold_mol(mol: Chem.Mol | None) -> Chem.Mol | None:
    if mol is None:
        return None
    try:
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
    except Exception:
        return None
    if scaffold is None or scaffold.GetNumAtoms() == 0:
        # Acyclic solutes have an empty Murcko scaffold. Use the full molecule
        # as the nearest-scaffold proxy rather than making all acyclic cases
        # indistinguishable.
        return mol
    return scaffold


def _scaffold_smiles_and_fp(
    smiles: str | float | None,
    radius: int,
    n_bits: int,
) -> tuple[str | None, DataStructs.ExplicitBitVect | None]:
    mol = _mol_from_smiles(smiles)
    scaffold = _scaffold_mol(mol)
    if scaffold is None:
        return None, None
    scaffold_smiles = Chem.MolToSmiles(scaffold, canonical=True)
    fp = AllChem.GetMorganFingerprintAsBitVect(scaffold, radius, nBits=n_bits)
    return scaffold_smiles, fp


def _pearsonr(x: np.ndarray, y: np.ndarray) -> float | None:
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return None
    x = x[mask]
    y = y[mask]
    if np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _spearmanr(x: np.ndarray, y: np.ndarray) -> float | None:
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 3:
        return None
    try:
        from scipy.stats import spearmanr

        value = spearmanr(x[mask], y[mask]).correlation
        return None if value is None or not np.isfinite(value) else float(value)
    except Exception:
        # Lightweight fallback via pandas rank correlation.
        xr = pd.Series(x[mask]).rank(method="average").to_numpy()
        yr = pd.Series(y[mask]).rank(method="average").to_numpy()
        return _pearsonr(xr, yr)


def _make_error_column(
    pred_df: pd.DataFrame,
    true_col: str | None,
    pred_col: str | None,
    error_col: str | None,
) -> str:
    if error_col is not None:
        if error_col not in pred_df.columns:
            raise ValueError(f"Requested error column not found: {error_col}")
        return error_col
    for col in ERROR_CANDIDATES:
        if col in pred_df.columns:
            return col
    true_col = true_col or _detect_column(pred_df, TRUE_CANDIDATES, "true target")
    pred_col = pred_col or _detect_column(pred_df, PRED_CANDIDATES, "prediction")
    pred_df["abs_error"] = (pred_df[pred_col].astype(float) - pred_df[true_col].astype(float)).abs()
    return "abs_error"


def _bin_metrics(df: pd.DataFrame, distance_col: str, error_col: str) -> list[dict]:
    bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0000001]
    rows = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (df[distance_col] >= lo) & (df[distance_col] < hi)
        values = df.loc[mask, error_col]
        rows.append(
            {
                "distance_bin": f"[{lo:.1f}, {min(hi, 1.0):.1f})",
                "n_rows": int(mask.sum()),
                "mae": None if len(values) == 0 else float(values.mean()),
                "median_abs_error": None if len(values) == 0 else float(values.median()),
                "p90_abs_error": None if len(values) == 0 else float(values.quantile(0.90)),
            }
        )
    return rows


def run_analysis(
    train_path: Path,
    test_predictions_path: Path,
    output_dir: Path,
    train_solute_col: str | None = None,
    test_solute_col: str | None = None,
    true_col: str | None = None,
    pred_col: str | None = None,
    error_col: str | None = None,
    radius: int = 2,
    n_bits: int = 2048,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(train_path)
    pred_df = pd.read_csv(test_predictions_path)

    train_solute_col = train_solute_col or _detect_column(train_df, SOLUTE_CANDIDATES, "train solute")
    test_solute_col = test_solute_col or _detect_column(pred_df, SOLUTE_CANDIDATES, "test solute")
    error_col = _make_error_column(pred_df, true_col, pred_col, error_col)

    train_scaffold_to_fp: dict[str, DataStructs.ExplicitBitVect] = {}
    invalid_train = 0
    for smiles in sorted(set(train_df[train_solute_col].dropna().astype(str))):
        scaffold_smiles, fp = _scaffold_smiles_and_fp(smiles, radius=radius, n_bits=n_bits)
        if scaffold_smiles is None or fp is None:
            invalid_train += 1
            continue
        train_scaffold_to_fp.setdefault(scaffold_smiles, fp)

    train_scaffold_smiles = list(train_scaffold_to_fp.keys())
    train_scaffold_fps = list(train_scaffold_to_fp.values())
    if not train_scaffold_fps:
        raise ValueError("No valid train scaffold fingerprints were generated.")

    solute_distance_rows = []
    solute_to_payload: dict[str, dict] = {}

    for smiles in sorted(set(pred_df[test_solute_col].dropna().astype(str))):
        scaffold_smiles, fp = _scaffold_smiles_and_fp(smiles, radius=radius, n_bits=n_bits)
        if scaffold_smiles is None or fp is None:
            payload = {
                "solute_smiles": smiles,
                "test_scaffold_smiles": None,
                "nearest_train_scaffold_smiles": None,
                "nearest_scaffold_tanimoto": 0.0,
                "nearest_scaffold_distance": 1.0,
                "valid_scaffold": False,
            }
        else:
            similarities = DataStructs.BulkTanimotoSimilarity(fp, train_scaffold_fps)
            best_idx = int(np.argmax(similarities))
            best_sim = float(similarities[best_idx])
            payload = {
                "solute_smiles": smiles,
                "test_scaffold_smiles": scaffold_smiles,
                "nearest_train_scaffold_smiles": train_scaffold_smiles[best_idx],
                "nearest_scaffold_tanimoto": best_sim,
                "nearest_scaffold_distance": float(1.0 - best_sim),
                "valid_scaffold": True,
            }
        solute_to_payload[smiles] = payload
        solute_distance_rows.append(payload)

    solute_distance_df = pd.DataFrame(solute_distance_rows)
    pred_df["test_scaffold_smiles"] = pred_df[test_solute_col].astype(str).map(
        lambda smiles: solute_to_payload.get(smiles, {}).get("test_scaffold_smiles")
    )
    pred_df["nearest_train_scaffold_smiles"] = pred_df[test_solute_col].astype(str).map(
        lambda smiles: solute_to_payload.get(smiles, {}).get("nearest_train_scaffold_smiles")
    )
    pred_df["nearest_scaffold_tanimoto"] = pred_df[test_solute_col].astype(str).map(
        lambda smiles: solute_to_payload.get(smiles, {}).get("nearest_scaffold_tanimoto", 0.0)
    )
    pred_df["nearest_scaffold_distance"] = pred_df[test_solute_col].astype(str).map(
        lambda smiles: solute_to_payload.get(smiles, {}).get("nearest_scaffold_distance", 1.0)
    )

    x_rows = pred_df["nearest_scaffold_distance"].astype(float).to_numpy()
    y_rows = pred_df[error_col].astype(float).to_numpy()

    solute_error_df = (
        pred_df.groupby(test_solute_col, as_index=False)
        .agg(
            mean_abs_error=(error_col, "mean"),
            median_abs_error=(error_col, "median"),
            n_rows=(error_col, "size"),
            nearest_scaffold_distance=("nearest_scaffold_distance", "first"),
            nearest_scaffold_tanimoto=("nearest_scaffold_tanimoto", "first"),
            test_scaffold_smiles=("test_scaffold_smiles", "first"),
            nearest_train_scaffold_smiles=("nearest_train_scaffold_smiles", "first"),
        )
        .rename(columns={test_solute_col: "solute_smiles"})
    )
    x_sol = solute_error_df["nearest_scaffold_distance"].astype(float).to_numpy()
    y_sol = solute_error_df["mean_abs_error"].astype(float).to_numpy()

    summary = {
        "train_path": str(train_path),
        "test_predictions_path": str(test_predictions_path),
        "train_solute_col": train_solute_col,
        "test_solute_col": test_solute_col,
        "error_col": error_col,
        "radius": int(radius),
        "n_bits": int(n_bits),
        "n_train_rows": int(len(train_df)),
        "n_test_prediction_rows": int(len(pred_df)),
        "n_train_unique_solutes": int(train_df[train_solute_col].nunique()),
        "n_test_unique_solutes": int(solute_error_df["solute_smiles"].nunique()),
        "n_train_unique_scaffold_proxies": int(len(train_scaffold_fps)),
        "invalid_train_solutes": int(invalid_train),
        "row_level": {
            "pearson_r_distance_error": _pearsonr(x_rows, y_rows),
            "spearman_r_distance_error": _spearmanr(x_rows, y_rows),
            "mean_nearest_scaffold_distance": float(np.mean(x_rows)),
            "median_nearest_scaffold_distance": float(np.median(x_rows)),
            "bins": _bin_metrics(pred_df, "nearest_scaffold_distance", error_col),
        },
        "solute_level": {
            "pearson_r_distance_error": _pearsonr(x_sol, y_sol),
            "spearman_r_distance_error": _spearmanr(x_sol, y_sol),
            "mean_nearest_scaffold_distance": float(np.mean(x_sol)),
            "median_nearest_scaffold_distance": float(np.median(x_sol)),
            "bins": _bin_metrics(solute_error_df, "nearest_scaffold_distance", "mean_abs_error"),
        },
    }

    pred_df.to_csv(output_dir / "rows_with_scaffold_distance.csv", index=False)
    solute_error_df.to_csv(output_dir / "solute_scaffold_distance_summary.csv", index=False)
    solute_distance_df.to_csv(output_dir / "solute_nearest_scaffolds.csv", index=False)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown(summary, output_dir / "SUMMARY.md")

    return summary


def _fmt(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def _bin_table(rows: list[dict]) -> list[str]:
    lines = [
        "| Distance bin | n | MAE | Median AE | P90 AE |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['distance_bin']} | {row['n_rows']} | "
            f"{_fmt(row['mae'])} | {_fmt(row['median_abs_error'])} | "
            f"{_fmt(row['p90_abs_error'])} |"
        )
    return lines


def _write_markdown(summary: dict, path: Path) -> None:
    row = summary["row_level"]
    sol = summary["solute_level"]
    lines = [
        "# Scaffold Distance vs Error Diagnostic",
        "",
        f"- train: `{summary['train_path']}`",
        f"- predictions: `{summary['test_predictions_path']}`",
        f"- train scaffold proxies: `{summary['n_train_unique_scaffold_proxies']}`",
        "",
        "## Row Level",
        "",
        f"- Pearson r(distance, abs error): `{_fmt(row['pearson_r_distance_error'])}`",
        f"- Spearman r(distance, abs error): `{_fmt(row['spearman_r_distance_error'])}`",
        f"- median nearest scaffold distance: `{_fmt(row['median_nearest_scaffold_distance'])}`",
        "",
        *_bin_table(row["bins"]),
        "",
        "## Unique Solute Level",
        "",
        f"- Pearson r(distance, mean solute abs error): `{_fmt(sol['pearson_r_distance_error'])}`",
        f"- Spearman r(distance, mean solute abs error): `{_fmt(sol['spearman_r_distance_error'])}`",
        f"- median nearest scaffold distance: `{_fmt(sol['median_nearest_scaffold_distance'])}`",
        "",
        *_bin_table(sol["bins"]),
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
    parser.add_argument("--radius", type=int, default=2)
    parser.add_argument("--n-bits", type=int, default=2048)
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
        radius=args.radius,
        n_bits=args.n_bits,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
