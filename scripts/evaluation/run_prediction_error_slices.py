#!/usr/bin/env python3
"""Slice scaffold prediction errors for any model prediction CSV.

This is a prediction-only companion to the heavier DirectGNN checkpoint
diagnostic. It consumes existing `ln_x2_true` / `ln_x2_pred` CSVs and writes
aligned pair, chemistry, solvent-type, and nearest-neighbor error summaries.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: E402,F401

from rdkit import Chem  # noqa: E402
from rdkit.Chem import Descriptors, rdMolDescriptors  # noqa: E402

from tgnn_solv.data.solvent_types import (  # noqa: E402
    SOLVENT_TYPE_NAMES,
    solvent_type_from_smiles,
)


DEFAULT_PREDICTIONS = [
    (
        "DirectGNN",
        "results/tail_diagnostics_fast_v2/directgnn_scaffold_predictions.csv",
    ),
    (
        "TGNN_MPNN",
        "results/tail_diagnostics_fast_v2/tgnn_mpnn_scaffold_predictions.csv",
    ),
    (
        "RF_hybrid",
        "results/tail_diagnostics_fast_v2/rf_hybrid_scaffold_predictions.csv",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build prediction-only error slices for existing model prediction "
            "CSVs. By default, it processes the current DirectGNN, TGNN_MPNN, "
            "and RF_hybrid scaffold predictions from tail diagnostics."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--prediction",
        action="append",
        default=None,
        metavar="LABEL=CSV",
        help=(
            "Prediction CSV to analyze. Can be repeated. CSV must contain "
            "`ln_x2_pred` and either `ln_x2_true` or `ln_x2`."
        ),
    )
    parser.add_argument(
        "--nearest-neighbors-csv",
        default="results/knn_modelability_smoke/nearest_neighbors.csv",
        help="Optional nearest-neighbor diagnostics CSV from run_knn_modelability.py.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/prediction_error_slices",
        help="Output directory for the comparison bundle.",
    )
    parser.add_argument(
        "--reference-label",
        default="DirectGNN",
        help="Reference model for paired row-wise deltas when available.",
    )
    parser.add_argument(
        "--min-slice-rows",
        type=int,
        default=20,
        help="Minimum row count for highlighting worst chemistry x solvent slices.",
    )
    return parser.parse_args()


def _parse_prediction_specs(raw_specs: list[str] | None) -> list[tuple[str, Path]]:
    specs = raw_specs
    if not specs:
        return [(label, Path(path)) for label, path in DEFAULT_PREDICTIONS]

    out: list[tuple[str, Path]] = []
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"Invalid --prediction spec {spec!r}; expected LABEL=CSV")
        label, path = spec.split("=", 1)
        label = label.strip()
        if not label:
            raise ValueError(f"Invalid --prediction spec {spec!r}; empty label")
        out.append((label, Path(path.strip())))
    return out


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


def pearson_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    if x.size < 2 or y.size < 2:
        return None
    if float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def rank_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    if x.size < 2 or y.size < 2:
        return None
    x_rank = pd.Series(x).rank(method="average").to_numpy(dtype=float)
    y_rank = pd.Series(y).rank(method="average").to_numpy(dtype=float)
    return pearson_corr(x_rank, y_rank)


def regression_metrics(pred: np.ndarray, true: np.ndarray) -> dict[str, Any]:
    pred = np.asarray(pred, dtype=float)
    true = np.asarray(true, dtype=float)
    mask = np.isfinite(pred) & np.isfinite(true)
    pred = pred[mask]
    true = true[mask]
    if pred.size == 0:
        return {
            "n_samples": 0,
            "mae": None,
            "rmse": None,
            "r2": None,
            "bias": None,
            "median_abs_error": None,
            "p90_abs_error": None,
            "p95_abs_error": None,
        }
    err = pred - true
    abs_err = np.abs(err)
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((true - np.mean(true)) ** 2))
    r2 = None if ss_tot == 0.0 else float(1.0 - ss_res / ss_tot)
    return {
        "n_samples": int(pred.size),
        "mae": float(np.mean(abs_err)),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "r2": r2,
        "bias": float(np.mean(err)),
        "median_abs_error": float(np.median(abs_err)),
        "p90_abs_error": float(np.quantile(abs_err, 0.90)),
        "p95_abs_error": float(np.quantile(abs_err, 0.95)),
    }


def _solvent_type_name_from_value(value: Any) -> str:
    if pd.isna(value):
        return "unknown"
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in SOLVENT_TYPE_NAMES:
            return stripped
        try:
            value = int(float(stripped))
        except ValueError:
            return stripped or "unknown"
    try:
        idx = int(value)
    except (TypeError, ValueError):
        return "unknown"
    if 0 <= idx < len(SOLVENT_TYPE_NAMES):
        return SOLVENT_TYPE_NAMES[idx]
    return "unknown"


def load_predictions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False).copy()
    required = {"solute_smiles", "solvent_smiles", "temperature", "ln_x2_pred"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    if "ln_x2_true" not in df.columns:
        if "ln_x2" not in df.columns:
            raise ValueError(f"{path} must contain either `ln_x2_true` or `ln_x2`")
        df["ln_x2_true"] = df["ln_x2"].astype(float)

    if "row_index" not in df.columns:
        df["row_index"] = np.arange(len(df), dtype=int)

    if "pair_key" not in df.columns:
        df["pair_key"] = (
            df["solute_smiles"].astype(str) + ">>" + df["solvent_smiles"].astype(str)
        )

    if "solvent_type_name" not in df.columns:
        if "solvent_type" in df.columns:
            df["solvent_type_name"] = df["solvent_type"].map(_solvent_type_name_from_value)
        else:
            type_map = {
                smi: solvent_type_from_smiles(str(smi))
                for smi in df["solvent_smiles"].dropna().astype(str).unique()
            }
            df["solvent_type_name"] = df["solvent_smiles"].astype(str).map(type_map)

    df["ln_x2_true"] = df["ln_x2_true"].astype(float)
    df["ln_x2_pred"] = df["ln_x2_pred"].astype(float)
    df["signed_error"] = df["ln_x2_pred"] - df["ln_x2_true"]
    df["abs_error"] = df["signed_error"].abs()
    return df


def _coarse_solute_class(features: dict[str, Any]) -> str:
    if features["invalid"]:
        return "invalid"
    if features["has_halogen"] and features["n_aromatic"] >= 1:
        return "halogenated_aromatic"
    if features["has_heterocycle"]:
        return "heterocycle"
    if features["has_sp"]:
        return "sulfur_or_phosphorus"
    if features["has_oh"]:
        return "oxygenated"
    if features["has_nh"]:
        return "nitrogenated"
    if features["n_aromatic"] >= 2:
        return "polyaromatic"
    if features["n_hetero"] == 0 and features["n_rings"] == 0:
        return "hydrocarbon_like"
    return "other"


def describe_solute(smiles: str) -> dict[str, Any]:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return {
            "solute_smiles": str(smiles),
            "invalid": True,
            "has_oh": False,
            "has_nh": False,
            "has_halogen": False,
            "has_sp": False,
            "has_heterocycle": False,
            "n_rings": 0,
            "n_aromatic": 0,
            "n_hetero": 0,
            "mw": math.nan,
            "tpsa": math.nan,
            "hbd": math.nan,
            "hba": math.nan,
            "coarse_class": "invalid",
        }

    ring_info = mol.GetRingInfo()
    has_heterocycle = False
    for ring in ring_info.AtomRings():
        if any(mol.GetAtomWithIdx(idx).GetAtomicNum() not in {6, 1} for idx in ring):
            has_heterocycle = True
            break

    features = {
        "solute_smiles": str(smiles),
        "invalid": False,
        "has_oh": mol.HasSubstructMatch(Chem.MolFromSmarts("[OX2H]")),
        "has_nh": mol.HasSubstructMatch(Chem.MolFromSmarts("[NX3;H1,H2]")),
        "has_halogen": mol.HasSubstructMatch(Chem.MolFromSmarts("[F,Cl,Br,I]")),
        "has_sp": mol.HasSubstructMatch(Chem.MolFromSmarts("[S,P]")),
        "has_heterocycle": has_heterocycle,
        "n_rings": int(rdMolDescriptors.CalcNumRings(mol)),
        "n_aromatic": int(rdMolDescriptors.CalcNumAromaticRings(mol)),
        "n_hetero": int(rdMolDescriptors.CalcNumHeteroatoms(mol)),
        "mw": float(Descriptors.MolWt(mol)),
        "tpsa": float(rdMolDescriptors.CalcTPSA(mol)),
        "hbd": int(rdMolDescriptors.CalcNumHBD(mol)),
        "hba": int(rdMolDescriptors.CalcNumHBA(mol)),
    }
    features["coarse_class"] = _coarse_solute_class(features)
    return features


def metrics_for_frame(df: pd.DataFrame) -> dict[str, Any]:
    return regression_metrics(
        df["ln_x2_pred"].to_numpy(dtype=float),
        df["ln_x2_true"].to_numpy(dtype=float),
    )


def _group_metrics(
    df: pd.DataFrame,
    group_cols: list[str],
    extra_aggs: dict[str, tuple[str, str]] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, grp in df.groupby(group_cols, sort=False, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: key for col, key in zip(group_cols, keys)}
        row.update(metrics_for_frame(grp))
        row["n_rows"] = int(len(grp))
        row["n_solutes"] = int(grp["solute_smiles"].nunique())
        row["n_pairs"] = int(grp["pair_key"].nunique())
        if extra_aggs:
            for name, (col, op) in extra_aggs.items():
                if op == "mean":
                    row[name] = float(grp[col].mean())
                elif op == "median":
                    row[name] = float(grp[col].median())
                elif op == "min":
                    row[name] = float(grp[col].min())
                elif op == "max":
                    row[name] = float(grp[col].max())
                else:
                    raise ValueError(f"Unsupported aggregate op: {op}")
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["n_rows", "mae"],
        ascending=[False, True],
        na_position="last",
        kind="stable",
    )


def attach_solute_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    solute_features = pd.DataFrame(
        [describe_solute(smiles) for smiles in df["solute_smiles"].drop_duplicates()]
    )
    merged = df.merge(solute_features, on="solute_smiles", how="left")
    return merged, solute_features


def pair_error_analysis(df: pd.DataFrame, out_dir: Path) -> dict[str, Any]:
    pair_df = (
        df.groupby(
            ["pair_key", "solute_smiles", "solvent_smiles"],
            as_index=False,
            sort=False,
        )
        .agg(
            n_points=("abs_error", "size"),
            mean_abs_error=("abs_error", "mean"),
            median_abs_error=("abs_error", "median"),
            max_abs_error=("abs_error", "max"),
            mean_signed_error=("signed_error", "mean"),
            temperature_min=("temperature", "min"),
            temperature_max=("temperature", "max"),
            ln_x2_true_mean=("ln_x2_true", "mean"),
            ln_x2_pred_mean=("ln_x2_pred", "mean"),
        )
        .sort_values("mean_abs_error", ascending=False, kind="stable")
        .reset_index(drop=True)
    )
    pair_df.to_csv(out_dir / "pair_errors.csv", index=False)
    pair_df.head(50).to_csv(out_dir / "top_worst_pairs.csv", index=False)

    mae_values = pair_df["mean_abs_error"].to_numpy(dtype=float)
    summary = {
        "n_pairs": int(len(pair_df)),
        "median_pair_mae": float(np.median(mae_values)),
        "p90_pair_mae": float(np.quantile(mae_values, 0.90)),
        "p95_pair_mae": float(np.quantile(mae_values, 0.95)),
        "fraction_pair_mae_lt_0_5": float(np.mean(mae_values < 0.5)),
        "fraction_pair_mae_lt_1_0": float(np.mean(mae_values < 1.0)),
        "fraction_pair_mae_gt_3_0": float(np.mean(mae_values > 3.0)),
        "fraction_pair_mae_gt_5_0": float(np.mean(mae_values > 5.0)),
    }
    (out_dir / "pair_error_summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    return summary


def chemistry_and_solvent_analysis(
    df: pd.DataFrame,
    out_dir: Path,
    *,
    min_slice_rows: int,
) -> dict[str, Any]:
    merged, solute_features = attach_solute_features(df)
    solute_features.to_csv(out_dir / "solute_features.csv", index=False)

    coarse_df = _group_metrics(merged, ["coarse_class"])
    coarse_df.to_csv(out_dir / "chemistry_coarse_class_metrics.csv", index=False)

    flag_rows: list[dict[str, Any]] = []
    for flag in ["has_oh", "has_nh", "has_halogen", "has_sp", "has_heterocycle"]:
        grp = merged.loc[merged[flag].fillna(False).astype(bool)].copy()
        if grp.empty:
            continue
        row = {"flag": flag}
        row.update(metrics_for_frame(grp))
        row["n_rows"] = int(len(grp))
        row["n_solutes"] = int(grp["solute_smiles"].nunique())
        row["n_pairs"] = int(grp["pair_key"].nunique())
        flag_rows.append(row)
    flag_df = pd.DataFrame(flag_rows).sort_values(
        ["n_rows", "mae"],
        ascending=[False, True],
        na_position="last",
        kind="stable",
    )
    flag_df.to_csv(out_dir / "chemistry_flag_metrics.csv", index=False)

    solvent_df = _group_metrics(merged, ["solvent_type_name"])
    solvent_df.to_csv(out_dir / "solvent_type_metrics.csv", index=False)

    cross_df = _group_metrics(merged, ["coarse_class", "solvent_type_name"])
    cross_df.to_csv(out_dir / "chemistry_x_solvent_type_metrics.csv", index=False)

    highlighted = cross_df.loc[cross_df["n_rows"] >= int(min_slice_rows)].sort_values(
        "mae",
        ascending=False,
        na_position="last",
        kind="stable",
    )
    highlighted.head(30).to_csv(out_dir / "worst_chemistry_solvent_slices.csv", index=False)

    halogenated = merged.loc[merged["coarse_class"] == "halogenated_aromatic"].copy()
    if halogenated.empty:
        halogenated_solvent_df = pd.DataFrame()
    else:
        halogenated_solvent_df = _group_metrics(halogenated, ["solvent_type_name"])
    halogenated_solvent_df.to_csv(
        out_dir / "halogenated_aromatic_by_solvent_type.csv",
        index=False,
    )

    largest_class = None if coarse_df.empty else coarse_df.iloc[0].to_dict()
    worst_class = (
        None
        if coarse_df.empty
        else coarse_df.sort_values("mae", ascending=False, na_position="last").iloc[0].to_dict()
    )
    worst_slice = (
        None
        if highlighted.empty
        else highlighted.iloc[0].to_dict()
    )
    halogenated_metrics = (
        None
        if halogenated.empty
        else metrics_for_frame(halogenated)
    )
    summary = {
        "n_test_rows": int(len(df)),
        "n_unique_solutes": int(df["solute_smiles"].nunique()),
        "largest_coarse_class_by_rows": largest_class,
        "worst_coarse_class_by_mae": worst_class,
        "worst_chemistry_solvent_slice_by_mae": worst_slice,
        "halogenated_aromatic_metrics": halogenated_metrics,
    }
    (out_dir / "chemistry_solvent_summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    return summary


def neighbor_error_analysis(
    df: pd.DataFrame,
    nearest_csv: Path,
    out_dir: Path,
) -> dict[str, Any] | None:
    if not nearest_csv.is_file():
        return None

    nn_df = pd.read_csv(nearest_csv, low_memory=False).copy()
    payload_cols = [
        "nearest_train_pair_key",
        "pair_tanimoto",
        "solute_tanimoto",
        "solvent_tanimoto",
        "temperature_delta",
        "abs_delta_ln_x2",
        "is_cliff",
    ]
    available_payload = [col for col in payload_cols if col in nn_df.columns]
    if "row_index" in nn_df.columns and not df["row_index"].duplicated().any():
        merged = df.merge(
            nn_df[["row_index"] + available_payload],
            on="row_index",
            how="left",
        )
    else:
        merge_keys = ["solute_smiles", "solvent_smiles", "temperature"]
        merged = df.merge(
            nn_df[merge_keys + available_payload],
            on=merge_keys,
            how="left",
        )
    merged = merged.rename(columns={"abs_delta_ln_x2": "abs_neighbor_gap"})
    merged.to_csv(out_dir / "nearest_neighbor_error_rows.csv", index=False)

    match_count = int(merged["pair_tanimoto"].notna().sum())
    if match_count == 0:
        return {
            "matched_rows": 0,
            "n_test_rows": int(len(df)),
        }

    good = merged.loc[merged["pair_tanimoto"].notna()].copy()
    pair_tani = good["pair_tanimoto"].to_numpy(dtype=float)
    abs_error = good["abs_error"].to_numpy(dtype=float)
    bins = pd.cut(
        good["pair_tanimoto"],
        bins=[0.0, 0.3, 0.5, 0.7, 0.8, 1.01],
        right=False,
        include_lowest=True,
        labels=["0.00-0.30", "0.30-0.50", "0.50-0.70", "0.70-0.80", "0.80-1.00"],
    )
    bin_df = (
        good.assign(pair_tanimoto_bin=bins)
        .groupby("pair_tanimoto_bin", observed=False)
        .agg(
            n=("pair_tanimoto", "size"),
            mean_pair_tanimoto=("pair_tanimoto", "mean"),
            mae=("abs_error", "mean"),
            median_abs_error=("abs_error", "median"),
            p90_abs_error=("abs_error", lambda s: float(np.quantile(s, 0.90))),
        )
        .reset_index()
    )
    bin_df.to_csv(out_dir / "nearest_neighbor_error_bins.csv", index=False)

    thresholds: dict[str, Any] = {}
    for thr in (0.5, 0.6, 0.7, 0.8):
        mask = pair_tani >= thr
        key = f"pair_tanimoto_gte_{thr:.1f}"
        if not mask.any():
            thresholds[key] = {"n": 0, "mae": None, "median_abs_error": None}
            continue
        subset_err = abs_error[mask]
        thresholds[key] = {
            "n": int(mask.sum()),
            "mae": float(np.mean(subset_err)),
            "median_abs_error": float(np.median(subset_err)),
        }

    summary = {
        "n_test_rows": int(len(df)),
        "matched_rows": match_count,
        "pearson_pair_tanimoto_vs_abs_error": pearson_corr(pair_tani, abs_error),
        "spearman_pair_tanimoto_vs_abs_error": rank_corr(pair_tani, abs_error),
        "mean_abs_error": float(np.mean(abs_error)),
        "median_abs_error": float(np.median(abs_error)),
        "thresholds": thresholds,
    }
    (out_dir / "nearest_neighbor_error_summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    return summary


def summarize_one_model(
    *,
    label: str,
    prediction_path: Path,
    nearest_csv: Path,
    out_root: Path,
    min_slice_rows: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    out_dir = out_root / label
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_predictions(prediction_path)
    df.to_csv(out_dir / "predictions_with_errors.csv", index=False)

    overall = metrics_for_frame(df)
    pair_summary = pair_error_analysis(df, out_dir)
    chemistry_summary = chemistry_and_solvent_analysis(
        df,
        out_dir,
        min_slice_rows=min_slice_rows,
    )
    neighbor_summary = neighbor_error_analysis(df, nearest_csv, out_dir)

    top_level = {
        "label": label,
        "prediction_path": str(prediction_path),
        "overall": overall,
        "pair_error_summary": pair_summary,
        "chemistry_solvent_summary": chemistry_summary,
        "nearest_neighbor_summary": neighbor_summary,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_safe(top_level), indent=2),
        encoding="utf-8",
    )
    (out_dir / "SUMMARY.md").write_text(
        build_model_markdown(top_level),
        encoding="utf-8",
    )
    return df, top_level


def _threshold_value(summary: dict[str, Any] | None, threshold: str, metric: str) -> Any:
    if not summary:
        return None
    thresholds = summary.get("thresholds") or {}
    payload = thresholds.get(threshold) or {}
    return payload.get(metric)


def comparison_row(summary: dict[str, Any]) -> dict[str, Any]:
    overall = summary["overall"]
    pair = summary["pair_error_summary"]
    chem = summary["chemistry_solvent_summary"]
    nn = summary.get("nearest_neighbor_summary")
    worst_class = chem.get("worst_coarse_class_by_mae") or {}
    worst_slice = chem.get("worst_chemistry_solvent_slice_by_mae") or {}
    halogen = chem.get("halogenated_aromatic_metrics") or {}
    return {
        "label": summary["label"],
        "mae": overall.get("mae"),
        "rmse": overall.get("rmse"),
        "r2": overall.get("r2"),
        "bias": overall.get("bias"),
        "median_abs_error": overall.get("median_abs_error"),
        "p90_abs_error": overall.get("p90_abs_error"),
        "median_pair_mae": pair.get("median_pair_mae"),
        "p90_pair_mae": pair.get("p90_pair_mae"),
        "fraction_pair_mae_gt_3": pair.get("fraction_pair_mae_gt_3_0"),
        "worst_coarse_class": worst_class.get("coarse_class"),
        "worst_coarse_class_mae": worst_class.get("mae"),
        "halogenated_aromatic_mae": halogen.get("mae"),
        "worst_chemistry_solvent_slice": (
            None
            if not worst_slice
            else f"{worst_slice.get('coarse_class')} x {worst_slice.get('solvent_type_name')}"
        ),
        "worst_chemistry_solvent_slice_mae": worst_slice.get("mae"),
        "nn_spearman_pair_tanimoto_vs_abs_error": (
            None if not nn else nn.get("spearman_pair_tanimoto_vs_abs_error")
        ),
        "mae_pair_tanimoto_gte_0_5": _threshold_value(
            nn,
            "pair_tanimoto_gte_0.5",
            "mae",
        ),
        "mae_pair_tanimoto_gte_0_8": _threshold_value(
            nn,
            "pair_tanimoto_gte_0.8",
            "mae",
        ),
    }


def paired_deltas(
    frames: dict[str, pd.DataFrame],
    *,
    reference_label: str,
    out_root: Path,
) -> pd.DataFrame:
    if reference_label not in frames or len(frames) < 2:
        return pd.DataFrame()

    ref = frames[reference_label][["row_index", "abs_error", "signed_error"]].rename(
        columns={
            "abs_error": "reference_abs_error",
            "signed_error": "reference_signed_error",
        }
    )
    rows: list[dict[str, Any]] = []
    for label, df in frames.items():
        if label == reference_label:
            continue
        comp = df[["row_index", "abs_error", "signed_error"]].rename(
            columns={
                "abs_error": "model_abs_error",
                "signed_error": "model_signed_error",
            }
        )
        merged = ref.merge(comp, on="row_index", how="inner")
        if merged.empty:
            continue
        delta = merged["model_abs_error"] - merged["reference_abs_error"]
        rows.append(
            {
                "reference_label": reference_label,
                "label": label,
                "n_matched_rows": int(len(merged)),
                "mean_abs_error_delta_vs_reference": float(delta.mean()),
                "median_abs_error_delta_vs_reference": float(delta.median()),
                "fraction_rows_model_better_than_reference": float((delta < 0).mean()),
                "fraction_rows_model_worse_than_reference": float((delta > 0).mean()),
                "abs_error_correlation_with_reference": pearson_corr(
                    merged["reference_abs_error"].to_numpy(dtype=float),
                    merged["model_abs_error"].to_numpy(dtype=float),
                ),
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out.to_csv(out_root / f"paired_deltas_vs_{reference_label}.csv", index=False)
    return out


def build_model_markdown(summary: dict[str, Any]) -> str:
    overall = summary["overall"]
    pair = summary["pair_error_summary"]
    chem = summary["chemistry_solvent_summary"]
    nn = summary.get("nearest_neighbor_summary")
    lines = [
        f"# {summary['label']} Prediction Error Slices",
        "",
        "## Overall",
        "",
        f"- MAE: `{overall['mae']:.3f}`",
        f"- RMSE: `{overall['rmse']:.3f}`",
        f"- R^2: `{overall['r2']:.3f}`",
        f"- Bias: `{overall['bias']:.3f}`",
        "",
        "## Pair-Level",
        "",
        f"- Median pair MAE: `{pair['median_pair_mae']:.3f}`",
        f"- P90 pair MAE: `{pair['p90_pair_mae']:.3f}`",
        f"- Pairs with MAE < 1.0: `{pair['fraction_pair_mae_lt_1_0']:.1%}`",
        f"- Pairs with MAE > 3.0: `{pair['fraction_pair_mae_gt_3_0']:.1%}`",
        "",
        "## Chemistry / Solvent Slices",
        "",
    ]
    worst_class = chem.get("worst_coarse_class_by_mae")
    if isinstance(worst_class, dict):
        lines.append(
            "- Worst coarse class: "
            f"`{worst_class['coarse_class']}` "
            f"(n=`{int(worst_class['n_rows'])}`, MAE=`{float(worst_class['mae']):.3f}`)"
        )
    halogen = chem.get("halogenated_aromatic_metrics")
    if isinstance(halogen, dict) and halogen.get("mae") is not None:
        lines.append(
            f"- Halogenated aromatic MAE: `{float(halogen['mae']):.3f}` "
            f"(n=`{int(halogen['n_samples'])}`)"
        )
    worst_slice = chem.get("worst_chemistry_solvent_slice_by_mae")
    if isinstance(worst_slice, dict):
        lines.append(
            "- Worst chemistry x solvent slice: "
            f"`{worst_slice['coarse_class']} x {worst_slice['solvent_type_name']}` "
            f"(n=`{int(worst_slice['n_rows'])}`, MAE=`{float(worst_slice['mae']):.3f}`)"
        )
    if nn is not None:
        lines += [
            "",
            "## Nearest-Train-Neighbor",
            "",
            f"- Matched rows: `{nn['matched_rows']}` / `{nn['n_test_rows']}`",
        ]
        spearman = nn.get("spearman_pair_tanimoto_vs_abs_error")
        if spearman is None:
            lines.append("- Spearman(pair Tanimoto, abs error): `NA`")
        else:
            lines.append(f"- Spearman(pair Tanimoto, abs error): `{spearman:.3f}`")
    return "\n".join(lines) + "\n"


def build_comparison_markdown(
    comparison_df: pd.DataFrame,
    paired_df: pd.DataFrame,
) -> str:
    lines = [
        "# Prediction Error Slice Comparison",
        "",
        "## Overall",
        "",
        "| Model | MAE | R^2 | Median pair MAE | P90 pair MAE | Halogenated aromatic MAE | NN Spearman |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparison_df.iterrows():
        nn = row.get("nn_spearman_pair_tanimoto_vs_abs_error")
        nn_text = f"{float(nn):.3f}" if pd.notna(nn) else "NA"
        lines.append(
            "| "
            f"{row['label']} | "
            f"{float(row['mae']):.3f} | "
            f"{float(row['r2']):.3f} | "
            f"{float(row['median_pair_mae']):.3f} | "
            f"{float(row['p90_pair_mae']):.3f} | "
            f"{float(row['halogenated_aromatic_mae']):.3f} | "
            f"{nn_text} |"
        )
    if not paired_df.empty:
        lines += [
            "",
            "## Paired Deltas",
            "",
            "| Model | Mean abs-error delta vs reference | Rows better than reference | Abs-error corr |",
            "|---|---:|---:|---:|",
        ]
        for _, row in paired_df.iterrows():
            corr = row.get("abs_error_correlation_with_reference")
            corr_text = f"{float(corr):.3f}" if pd.notna(corr) else "NA"
            lines.append(
                "| "
                f"{row['label']} | "
                f"{float(row['mean_abs_error_delta_vs_reference']):+.3f} | "
                f"{float(row['fraction_rows_model_better_than_reference']):.1%} | "
                f"{corr_text} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    out_root = Path(args.out_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    nearest_csv = Path(args.nearest_neighbors_csv).expanduser().resolve()

    frames: dict[str, pd.DataFrame] = {}
    summaries: list[dict[str, Any]] = []
    for label, raw_path in _parse_prediction_specs(args.prediction):
        prediction_path = raw_path.expanduser().resolve()
        if not prediction_path.is_file():
            raise FileNotFoundError(prediction_path)
        frame, summary = summarize_one_model(
            label=label,
            prediction_path=prediction_path,
            nearest_csv=nearest_csv,
            out_root=out_root,
            min_slice_rows=int(args.min_slice_rows),
        )
        frames[label] = frame
        summaries.append(summary)

    comparison_df = pd.DataFrame([comparison_row(summary) for summary in summaries])
    comparison_df = comparison_df.sort_values("mae", ascending=True, kind="stable")
    comparison_df.to_csv(out_root / "comparison_summary.csv", index=False)

    paired_df = paired_deltas(
        frames,
        reference_label=str(args.reference_label),
        out_root=out_root,
    )
    bundle = {
        "prediction_specs": [
            {"label": label, "path": str(path)}
            for label, path in _parse_prediction_specs(args.prediction)
        ],
        "nearest_neighbors_csv": str(nearest_csv),
        "comparison_summary": comparison_df.to_dict(orient="records"),
        "paired_deltas": paired_df.to_dict(orient="records"),
    }
    (out_root / "summary.json").write_text(
        json.dumps(_json_safe(bundle), indent=2),
        encoding="utf-8",
    )
    (out_root / "SUMMARY.md").write_text(
        build_comparison_markdown(comparison_df, paired_df),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(bundle), indent=2))


if __name__ == "__main__":
    main()
