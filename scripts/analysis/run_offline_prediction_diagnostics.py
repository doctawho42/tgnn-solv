#!/usr/bin/env python3
"""Run CPU-only diagnostics on existing prediction artifacts.

This script intentionally does not load checkpoints or train models. It consumes
prediction CSVs that already contain true and predicted ``ln_x2`` values and
exports the diagnostics that are useful before spending GPU time:

- prediction compression: ``std(pred) / std(true)``;
- metrics by true ``ln_x2`` bins;
- pair-wise Van't Hoff slope and level errors for pairs with repeated
  temperatures;
- worst pairs and residual correlations with lightweight RDKit descriptors;
- optional summaries of TGNN-Solv intermediates such as ``tau_12``, ``Phi`` and
  ``ln_gamma2``.
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

import _bootstrap  # noqa: F401


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

DEFAULT_INTERMEDIATES = [
    (
        "TGNN_MPNN_proxy",
        "results/physics_bottleneck_diagnostics/tgnn_mpnn_proxy_intermediates/intermediates.csv",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--prediction",
        action="append",
        default=None,
        metavar="LABEL=CSV",
        help=(
            "Prediction CSV. Can be repeated. The CSV must contain a true "
            "column (`ln_x2_true` or `ln_x2`) and a predicted column "
            "(`ln_x2_pred` or `ln_x2_final`)."
        ),
    )
    parser.add_argument(
        "--intermediates",
        action="append",
        default=None,
        metavar="LABEL=CSV",
        help=(
            "Optional TGNN intermediate CSV. Can be repeated. If omitted, the "
            "maintained proxy intermediates are used when present."
        ),
    )
    parser.add_argument(
        "--out-dir",
        default="results/offline_prediction_diagnostics",
        help="Output directory for diagnostic artifacts.",
    )
    parser.add_argument(
        "--bin-edges",
        default="-25,-15,-12,-9,-6,-3,0",
        help="Comma-separated true ln_x2 bin edges.",
    )
    parser.add_argument(
        "--min-pair-points",
        type=int,
        default=3,
        help="Minimum rows per pair for pair-wise slope fitting.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=30,
        help="Number of worst rows/pairs to export per model.",
    )
    parser.add_argument(
        "--skip-rdkit",
        action="store_true",
        help="Skip RDKit descriptor correlations.",
    )
    parser.add_argument(
        "--unifac-coverage",
        default="results/unifac_coverage/current_priors/unifac_coverage_by_split.csv",
        help="Optional existing UNIFAC coverage summary CSV to copy into this diagnostic bundle.",
    )
    return parser.parse_args()


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _parse_specs(raw_specs: list[str] | None, defaults: list[tuple[str, str]]) -> list[tuple[str, Path]]:
    if not raw_specs:
        return [(label, Path(path)) for label, path in defaults if Path(path).exists()]
    specs: list[tuple[str, Path]] = []
    for raw in raw_specs:
        if "=" not in raw:
            raise ValueError(f"Invalid spec {raw!r}; expected LABEL=CSV")
        label, path = raw.split("=", 1)
        label = label.strip()
        if not label:
            raise ValueError(f"Invalid spec {raw!r}; empty label")
        specs.append((label, Path(path.strip())))
    return specs


def _detect_column(df: pd.DataFrame, candidates: tuple[str, ...], *, label: str, path: Path) -> str:
    for col in candidates:
        if col in df.columns:
            return col
    raise ValueError(
        f"{path} has no {label} column. Tried {candidates}; available: {list(df.columns)}"
    )


def _safe_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 2 or float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None
    value = float(np.corrcoef(x, y)[0, 1])
    return value if math.isfinite(value) else None


def _rank_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    x_rank = pd.Series(x).rank(method="average").to_numpy(dtype=float)
    y_rank = pd.Series(y).rank(method="average").to_numpy(dtype=float)
    return _safe_corr(x_rank, y_rank)


def _metrics(true: np.ndarray, pred: np.ndarray) -> dict[str, Any]:
    true = np.asarray(true, dtype=float)
    pred = np.asarray(pred, dtype=float)
    mask = np.isfinite(true) & np.isfinite(pred)
    true = true[mask]
    pred = pred[mask]
    if true.size == 0:
        return {
            "n": 0,
            "mae": None,
            "rmse": None,
            "r2": None,
            "bias": None,
            "median_abs_error": None,
            "p90_abs_error": None,
            "p95_abs_error": None,
            "true_std": None,
            "pred_std": None,
            "std_ratio_pred_over_true": None,
            "pearson_r": None,
            "spearman_r": None,
        }
    err = pred - true
    abs_err = np.abs(err)
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((true - np.mean(true)) ** 2))
    true_std = float(np.std(true, ddof=1)) if true.size > 1 else 0.0
    pred_std = float(np.std(pred, ddof=1)) if pred.size > 1 else 0.0
    return {
        "n": int(true.size),
        "mae": float(np.mean(abs_err)),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "r2": None if ss_tot == 0.0 else float(1.0 - ss_res / ss_tot),
        "bias": float(np.mean(err)),
        "median_abs_error": float(np.median(abs_err)),
        "p90_abs_error": float(np.quantile(abs_err, 0.90)),
        "p95_abs_error": float(np.quantile(abs_err, 0.95)),
        "true_std": true_std,
        "pred_std": pred_std,
        "std_ratio_pred_over_true": None if true_std == 0.0 else float(pred_std / true_std),
        "pearson_r": _safe_corr(true, pred),
        "spearman_r": _rank_corr(true, pred),
    }


def load_prediction_csv(label: str, path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False).copy()
    true_col = _detect_column(df, ("ln_x2_true", "ln_x2", "true_ln_x2"), label="true ln_x2", path=path)
    pred_col = _detect_column(df, ("ln_x2_pred", "ln_x2_final", "pred_ln_x2"), label="pred ln_x2", path=path)
    temp_col = None
    for candidate in ("temperature", "T", "T_K"):
        if candidate in df.columns:
            temp_col = candidate
            break

    out = df.copy()
    out["model"] = str(label)
    out["ln_x2_true"] = pd.to_numeric(out[true_col], errors="coerce")
    out["ln_x2_pred"] = pd.to_numeric(out[pred_col], errors="coerce")
    if temp_col is not None:
        out["temperature"] = pd.to_numeric(out[temp_col], errors="coerce")
    if "row_index" not in out.columns:
        out["row_index"] = np.arange(len(out), dtype=int)
    if "pair_key" not in out.columns and {"solute_smiles", "solvent_smiles"}.issubset(out.columns):
        out["pair_key"] = out["solute_smiles"].astype(str) + ">>" + out["solvent_smiles"].astype(str)
    out["signed_error"] = out["ln_x2_pred"] - out["ln_x2_true"]
    out["abs_error"] = out["signed_error"].abs()
    out["prediction_source"] = str(path)
    return out


def summarize_models(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model, group in predictions.groupby("model", sort=False):
        row = {"model": model}
        row.update(_metrics(group["ln_x2_true"].to_numpy(), group["ln_x2_pred"].to_numpy()))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("mae", na_position="last")


def summarize_bins(predictions: pd.DataFrame, edges: list[float]) -> pd.DataFrame:
    labels = [f"[{edges[i]},{edges[i + 1]})" for i in range(len(edges) - 1)]
    rows: list[dict[str, Any]] = []
    for model, group in predictions.groupby("model", sort=False):
        bins = pd.cut(group["ln_x2_true"], bins=edges, labels=labels, include_lowest=True, right=False)
        for bin_label, bin_group in group.groupby(bins, observed=False):
            if bin_group.empty:
                continue
            row = {"model": model, "ln_x2_bin": str(bin_label)}
            row.update(_metrics(bin_group["ln_x2_true"].to_numpy(), bin_group["ln_x2_pred"].to_numpy()))
            rows.append(row)
    return pd.DataFrame(rows)


def pair_slope_diagnostics(predictions: pd.DataFrame, *, min_points: int) -> pd.DataFrame:
    if "pair_key" not in predictions.columns or "temperature" not in predictions.columns:
        return pd.DataFrame()
    work = predictions.copy()
    work = work[
        np.isfinite(work["temperature"])
        & np.isfinite(work["ln_x2_true"])
        & np.isfinite(work["ln_x2_pred"])
        & (work["temperature"] > 0.0)
    ]
    rows: list[dict[str, Any]] = []
    for (model, pair_key), group in work.groupby(["model", "pair_key"], sort=False):
        if len(group) < min_points or group["temperature"].nunique(dropna=True) < min_points:
            continue
        group = group.sort_values("temperature")
        inv_t = 1.0 / group["temperature"].to_numpy(dtype=float)
        if float(np.std(inv_t)) == 0.0:
            continue
        y_true = group["ln_x2_true"].to_numpy(dtype=float)
        y_pred = group["ln_x2_pred"].to_numpy(dtype=float)
        true_slope, true_intercept = np.polyfit(inv_t, y_true, deg=1)
        pred_slope, pred_intercept = np.polyfit(inv_t, y_pred, deg=1)
        errors = y_pred - y_true
        rows.append(
            {
                "model": model,
                "pair_key": pair_key,
                "n_rows": int(len(group)),
                "n_temperatures": int(group["temperature"].nunique(dropna=True)),
                "temperature_min": float(group["temperature"].min()),
                "temperature_max": float(group["temperature"].max()),
                "temperature_span": float(group["temperature"].max() - group["temperature"].min()),
                "slope_true_K": float(true_slope),
                "slope_pred_K": float(pred_slope),
                "slope_error_K": float(pred_slope - true_slope),
                "abs_slope_error_K": float(abs(pred_slope - true_slope)),
                "level_true_at_mean_invT": float(true_slope * inv_t.mean() + true_intercept),
                "level_pred_at_mean_invT": float(pred_slope * inv_t.mean() + pred_intercept),
                "level_error_at_mean_invT": float((pred_slope - true_slope) * inv_t.mean() + pred_intercept - true_intercept),
                "pair_bias": float(np.mean(errors)),
                "pair_mae": float(np.mean(np.abs(errors))),
                "pair_rmse": float(np.sqrt(np.mean(errors**2))),
                "solute_smiles": str(group["solute_smiles"].iloc[0]) if "solute_smiles" in group.columns else None,
                "solvent_smiles": str(group["solvent_smiles"].iloc[0]) if "solvent_smiles" in group.columns else None,
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["model", "pair_mae", "abs_slope_error_K"], ascending=[True, False, False])
    return out


def summarize_pair_slopes(pair_slopes: pd.DataFrame) -> pd.DataFrame:
    if pair_slopes.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for model, group in pair_slopes.groupby("model", sort=False):
        row = {
            "model": model,
            "n_pairs": int(len(group)),
            "n_rows": int(group["n_rows"].sum()),
            "pair_mae_mean": float(group["pair_mae"].mean()),
            "pair_mae_median": float(group["pair_mae"].median()),
            "level_error_mae": float(group["level_error_at_mean_invT"].abs().mean()),
            "level_error_bias": float(group["level_error_at_mean_invT"].mean()),
            "slope_mae_K": float(group["abs_slope_error_K"].mean()),
            "slope_median_abs_error_K": float(group["abs_slope_error_K"].median()),
            "slope_bias_K": float(group["slope_error_K"].mean()),
            "slope_pearson_r": _safe_corr(
                group["slope_true_K"].to_numpy(dtype=float),
                group["slope_pred_K"].to_numpy(dtype=float),
            ),
            "pred_slope_std_K": float(group["slope_pred_K"].std(ddof=1)) if len(group) > 1 else 0.0,
            "true_slope_std_K": float(group["slope_true_K"].std(ddof=1)) if len(group) > 1 else 0.0,
        }
        rows.append(row)
    return pd.DataFrame(rows).sort_values("pair_mae_mean", na_position="last")


def _as_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    text = series.astype(str).str.strip().str.lower()
    return text.isin({"true", "1", "yes", "y"})


def source_error_summary(predictions: pd.DataFrame) -> pd.DataFrame:
    if "source" not in predictions.columns:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for (model, source), group in predictions.groupby(["model", "source"], dropna=False, sort=False):
        row = {"model": model, "source": source}
        row.update(_metrics(group["ln_x2_true"].to_numpy(), group["ln_x2_pred"].to_numpy()))
        if "solute_smiles" in group.columns:
            row["n_solutes"] = int(group["solute_smiles"].nunique(dropna=True))
        if "solvent_smiles" in group.columns:
            row["n_solvents"] = int(group["solvent_smiles"].nunique(dropna=True))
        if "pair_key" in group.columns:
            row["n_pairs"] = int(group["pair_key"].nunique(dropna=True))
        rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["model", "mae"], ascending=[True, False])
    return out


def crystal_mask_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    if "has_T_m" not in predictions.columns and "has_dH_fus" not in predictions.columns:
        return pd.DataFrame()
    work = predictions.copy()
    work["has_T_m_bool"] = _as_bool_series(work["has_T_m"]) if "has_T_m" in work.columns else False
    work["has_dH_fus_bool"] = (
        _as_bool_series(work["has_dH_fus"]) if "has_dH_fus" in work.columns else False
    )
    work["crystal_label_state"] = np.select(
        [
            work["has_T_m_bool"] & work["has_dH_fus_bool"],
            work["has_T_m_bool"] & ~work["has_dH_fus_bool"],
            ~work["has_T_m_bool"] & work["has_dH_fus_bool"],
        ],
        ["T_m_and_dH_fus", "T_m_only", "dH_fus_only"],
        default="no_crystal_labels",
    )
    rows: list[dict[str, Any]] = []
    for (model, state), group in work.groupby(["model", "crystal_label_state"], sort=False):
        row = {
            "model": model,
            "crystal_label_state": state,
            "has_T_m_fraction": float(group["has_T_m_bool"].mean()),
            "has_dH_fus_fraction": float(group["has_dH_fus_bool"].mean()),
        }
        row.update(_metrics(group["ln_x2_true"].to_numpy(), group["ln_x2_pred"].to_numpy()))
        rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["model", "crystal_label_state"])
    return out


def compute_rdkit_features(smiles_values: pd.Series) -> pd.DataFrame:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import Descriptors, rdMolDescriptors

    RDLogger.DisableLog("rdApp.*")
    rows: list[dict[str, Any]] = []
    for smiles in smiles_values.dropna().astype(str).drop_duplicates():
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            rows.append({"solute_smiles": smiles, "rdkit_valid": False})
            continue
        charges = [atom.GetFormalCharge() for atom in mol.GetAtoms()]
        rows.append(
            {
                "solute_smiles": smiles,
                "rdkit_valid": True,
                "mol_wt": float(Descriptors.MolWt(mol)),
                "heavy_atoms": int(mol.GetNumHeavyAtoms()),
                "hbd": int(rdMolDescriptors.CalcNumHBD(mol)),
                "hba": int(rdMolDescriptors.CalcNumHBA(mol)),
                "tpsa": float(rdMolDescriptors.CalcTPSA(mol)),
                "logp": float(Descriptors.MolLogP(mol)),
                "rings": int(rdMolDescriptors.CalcNumRings(mol)),
                "aromatic_rings": int(rdMolDescriptors.CalcNumAromaticRings(mol)),
                "rotatable_bonds": int(rdMolDescriptors.CalcNumRotatableBonds(mol)),
                "formal_charge": int(sum(charges)),
                "n_charged_atoms": int(sum(1 for charge in charges if charge != 0)),
                "n_fragments": int(len(Chem.GetMolFrags(mol))),
            }
        )
    return pd.DataFrame(rows)


def residual_feature_correlations(predictions: pd.DataFrame, *, skip_rdkit: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    if skip_rdkit or "solute_smiles" not in predictions.columns:
        return pd.DataFrame(), pd.DataFrame()
    try:
        feature_df = compute_rdkit_features(predictions["solute_smiles"])
    except Exception as exc:
        print(f"[warn] RDKit feature computation failed: {exc}", file=sys.stderr)
        return pd.DataFrame(), pd.DataFrame()

    merged = predictions.merge(feature_df, on="solute_smiles", how="left")
    feature_cols = [
        col
        for col in [
            "mol_wt",
            "heavy_atoms",
            "hbd",
            "hba",
            "tpsa",
            "logp",
            "rings",
            "aromatic_rings",
            "rotatable_bonds",
            "formal_charge",
            "n_charged_atoms",
            "n_fragments",
        ]
        if col in merged.columns
    ]
    rows: list[dict[str, Any]] = []
    for model, group in merged.groupby("model", sort=False):
        for col in feature_cols:
            x = pd.to_numeric(group[col], errors="coerce").to_numpy(dtype=float)
            signed = group["signed_error"].to_numpy(dtype=float)
            abs_err = group["abs_error"].to_numpy(dtype=float)
            rows.append(
                {
                    "model": model,
                    "feature": col,
                    "n": int(np.isfinite(x).sum()),
                    "pearson_signed_error": _safe_corr(x, signed),
                    "spearman_signed_error": _rank_corr(x, signed),
                    "pearson_abs_error": _safe_corr(x, abs_err),
                    "spearman_abs_error": _rank_corr(x, abs_err),
                }
            )
    corr = pd.DataFrame(rows)
    if not corr.empty:
        corr["_rank_key"] = corr["spearman_abs_error"].abs().fillna(0.0)
        corr = corr.sort_values(["model", "_rank_key"], ascending=[True, False]).drop(columns=["_rank_key"])
    return feature_df, corr


def intermediate_diagnostics(specs: list[tuple[str, Path]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, Any]] = []
    corr_rows: list[dict[str, Any]] = []
    interesting = [
        "T_m_pred",
        "dH_fus_pred",
        "T_m_solver",
        "dH_fus_solver",
        "tau_12_pred",
        "tau_21_pred",
        "alpha_pred",
        "ln_gamma2_pred",
        "Phi_pred",
        "ln_x2_physics",
        "ln_x2_final",
        "correction_magnitude",
        "gate_value",
    ]
    for label, path in specs:
        if not path.exists():
            continue
        df = pd.read_csv(path, low_memory=False)
        true_col = next((c for c in ("ln_x2_true", "ln_x2") if c in df.columns), None)
        error_col = next((c for c in ("error", "signed_error") if c in df.columns), None)
        if error_col is None and true_col and "ln_x2_final" in df.columns:
            df["signed_error"] = pd.to_numeric(df["ln_x2_final"], errors="coerce") - pd.to_numeric(df[true_col], errors="coerce")
            error_col = "signed_error"
        for col in interesting:
            if col not in df.columns:
                continue
            values = pd.to_numeric(df[col], errors="coerce")
            valid = values[np.isfinite(values)]
            if valid.empty:
                continue
            summary_rows.append(
                {
                    "label": label,
                    "column": col,
                    "n": int(valid.size),
                    "mean": float(valid.mean()),
                    "std": float(valid.std(ddof=1)) if valid.size > 1 else 0.0,
                    "min": float(valid.min()),
                    "p05": float(valid.quantile(0.05)),
                    "median": float(valid.median()),
                    "p95": float(valid.quantile(0.95)),
                    "max": float(valid.max()),
                }
            )
            if true_col is not None:
                corr_rows.append(
                    {
                        "label": label,
                        "column": col,
                        "target": true_col,
                        "pearson": _safe_corr(values.to_numpy(dtype=float), pd.to_numeric(df[true_col], errors="coerce").to_numpy(dtype=float)),
                        "spearman": _rank_corr(values.to_numpy(dtype=float), pd.to_numeric(df[true_col], errors="coerce").to_numpy(dtype=float)),
                    }
                )
            if error_col is not None:
                err = pd.to_numeric(df[error_col], errors="coerce").to_numpy(dtype=float)
                corr_rows.append(
                    {
                        "label": label,
                        "column": col,
                        "target": error_col,
                        "pearson": _safe_corr(values.to_numpy(dtype=float), err),
                        "spearman": _rank_corr(values.to_numpy(dtype=float), err),
                    }
                )
                corr_rows.append(
                    {
                        "label": label,
                        "column": col,
                        "target": f"abs_{error_col}",
                        "pearson": _safe_corr(values.to_numpy(dtype=float), np.abs(err)),
                        "spearman": _rank_corr(values.to_numpy(dtype=float), np.abs(err)),
                    }
                )
    return pd.DataFrame(summary_rows), pd.DataFrame(corr_rows)


def crystal_parameter_diagnostics(specs: list[tuple[str, Path]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, path in specs:
        if not path.exists():
            continue
        df = pd.read_csv(path, low_memory=False)
        work = df.copy()
        if "has_T_m" in work.columns:
            work["has_T_m_bool"] = _as_bool_series(work["has_T_m"])
        elif "T_m_true" in work.columns:
            work["has_T_m_bool"] = pd.to_numeric(work["T_m_true"], errors="coerce").notna()
        else:
            work["has_T_m_bool"] = False
        if "has_dH_fus" in work.columns:
            work["has_dH_fus_bool"] = _as_bool_series(work["has_dH_fus"])
        elif "dH_fus_true" in work.columns:
            work["has_dH_fus_bool"] = pd.to_numeric(work["dH_fus_true"], errors="coerce").notna()
        else:
            work["has_dH_fus_bool"] = False
        work["crystal_label_state"] = np.select(
            [
                work["has_T_m_bool"] & work["has_dH_fus_bool"],
                work["has_T_m_bool"] & ~work["has_dH_fus_bool"],
                ~work["has_T_m_bool"] & work["has_dH_fus_bool"],
            ],
            ["T_m_and_dH_fus", "T_m_only", "dH_fus_only"],
            default="no_crystal_labels",
        )
        for state, group in work.groupby("crystal_label_state", sort=False):
            row: dict[str, Any] = {
                "label": label,
                "crystal_label_state": state,
                "n": int(len(group)),
                "has_T_m_fraction": float(group["has_T_m_bool"].mean()),
                "has_dH_fus_fraction": float(group["has_dH_fus_bool"].mean()),
            }
            if "abs_error" in group.columns:
                row["ln_x2_mae"] = float(pd.to_numeric(group["abs_error"], errors="coerce").mean())
            elif {"ln_x2_final", "ln_x2_true"}.issubset(group.columns):
                err = pd.to_numeric(group["ln_x2_final"], errors="coerce") - pd.to_numeric(
                    group["ln_x2_true"], errors="coerce"
                )
                row["ln_x2_mae"] = float(err.abs().mean())
            for pred_col, true_col, prefix in [
                ("T_m_pred", "T_m_true", "T_m"),
                ("T_m_solver", "T_m_true", "T_m_solver"),
                ("dH_fus_pred", "dH_fus_true", "dH_fus"),
                ("dH_fus_solver", "dH_fus_true", "dH_fus_solver"),
            ]:
                if pred_col in group.columns:
                    pred = pd.to_numeric(group[pred_col], errors="coerce")
                    row[f"{prefix}_pred_mean"] = float(pred.mean())
                    row[f"{prefix}_pred_std"] = float(pred.std(ddof=1)) if pred.notna().sum() > 1 else 0.0
                if pred_col in group.columns and true_col in group.columns:
                    pred = pd.to_numeric(group[pred_col], errors="coerce")
                    true = pd.to_numeric(group[true_col], errors="coerce")
                    mask = pred.notna() & true.notna()
                    row[f"{prefix}_true_n"] = int(mask.sum())
                    if mask.any():
                        diff = pred[mask] - true[mask]
                        row[f"{prefix}_mae"] = float(diff.abs().mean())
                        row[f"{prefix}_bias"] = float(diff.mean())
            for col in ["Phi_pred", "ln_gamma2_pred", "ln_x2_physics", "ln_x2_final", "correction_magnitude"]:
                if col in group.columns:
                    values = pd.to_numeric(group[col], errors="coerce")
                    row[f"{col}_mean"] = float(values.mean())
                    row[f"{col}_std"] = float(values.std(ddof=1)) if values.notna().sum() > 1 else 0.0
            rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["label", "crystal_label_state"])
    return out


def load_unifac_coverage(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if "path" in df.columns:
        df = df.copy()
        df["split_name"] = df["path"].astype(str).map(lambda x: Path(x).stem)
    return df


def _format_markdown_value(value: Any, *, floatfmt: str = ".4g") -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return format(value, floatfmt)
    if isinstance(value, np.generic):
        return _format_markdown_value(value.item(), floatfmt=floatfmt)
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _to_markdown_table(df: pd.DataFrame, columns: list[str], *, floatfmt: str = ".4g") -> str:
    if df.empty:
        return ""
    available = [col for col in columns if col in df.columns]
    if not available:
        return ""
    rows = ["| " + " | ".join(available) + " |"]
    rows.append("| " + " | ".join("---" for _ in available) + " |")
    for _, row in df[available].iterrows():
        rows.append(
            "| "
            + " | ".join(_format_markdown_value(row[col], floatfmt=floatfmt) for col in available)
            + " |"
        )
    return "\n".join(rows)


def write_markdown(
    out_dir: Path,
    *,
    model_summary: pd.DataFrame,
    bin_metrics: pd.DataFrame,
    slope_summary: pd.DataFrame,
    source_summary: pd.DataFrame,
    crystal_metrics: pd.DataFrame,
    feature_corr: pd.DataFrame,
    interm_summary: pd.DataFrame,
    crystal_params: pd.DataFrame,
    unifac_coverage: pd.DataFrame,
) -> None:
    lines: list[str] = [
        "# Offline Prediction Diagnostics",
        "",
        "This bundle is computed from existing prediction artifacts only. No model was trained.",
        "",
        "## Model Summary",
        "",
    ]
    if model_summary.empty:
        lines.append("No model summaries were produced.")
    else:
        display_cols = [
            "model",
            "n",
            "mae",
            "r2",
            "bias",
            "true_std",
            "pred_std",
            "std_ratio_pred_over_true",
        ]
        lines.append(_to_markdown_table(model_summary, display_cols))

    lines += ["", "## ln(x2) Bin Metrics", ""]
    if bin_metrics.empty:
        lines.append("No bin metrics were produced.")
    else:
        cols = ["model", "ln_x2_bin", "n", "mae", "r2", "bias", "std_ratio_pred_over_true"]
        lines.append(_to_markdown_table(bin_metrics, cols))

    lines += ["", "## Pair Slope Summary", ""]
    if slope_summary.empty:
        lines.append("No pair slope diagnostics were produced; repeated-temperature pairs may be absent.")
    else:
        cols = [
            "model",
            "n_pairs",
            "pair_mae_mean",
            "level_error_mae",
            "slope_mae_K",
            "slope_pearson_r",
            "pred_slope_std_K",
            "true_slope_std_K",
        ]
        lines.append(_to_markdown_table(slope_summary, cols))

    lines += ["", "## Source Error Summary", ""]
    if source_summary.empty:
        lines.append("No source-level error summary was produced.")
    else:
        cols = ["model", "source", "n", "mae", "bias", "n_solutes", "n_solvents", "n_pairs"]
        lines.append(_to_markdown_table(source_summary.head(18), cols))
        if source_summary["source"].nunique(dropna=False) == 1:
            lines.append("")
            lines.append(
                "The current prediction artifacts expose only one collapsed source label; DOI-level error audit requires row-level DOI metadata."
            )

    lines += ["", "## Crystal Label Availability", ""]
    if crystal_metrics.empty:
        lines.append("No crystal-label mask metrics were produced.")
    else:
        cols = [
            "model",
            "crystal_label_state",
            "n",
            "mae",
            "bias",
            "has_T_m_fraction",
            "has_dH_fus_fraction",
        ]
        lines.append(_to_markdown_table(crystal_metrics, cols))

    lines += ["", "## Strongest Residual Feature Correlations", ""]
    if feature_corr.empty:
        lines.append("RDKit feature correlations were skipped or failed.")
    else:
        tmp = feature_corr.copy()
        tmp["_abs"] = tmp["spearman_abs_error"].abs().fillna(0.0)
        top = tmp.sort_values(["model", "_abs"], ascending=[True, False]).groupby("model").head(6)
        cols = ["model", "feature", "spearman_abs_error", "spearman_signed_error"]
        lines.append(_to_markdown_table(top, cols))

    lines += ["", "## TGNN Intermediate Summary", ""]
    if interm_summary.empty:
        lines.append("No intermediate summaries were produced.")
    else:
        keep = interm_summary[
            interm_summary["column"].isin(
                ["tau_12_pred", "tau_21_pred", "ln_gamma2_pred", "Phi_pred", "ln_x2_physics", "correction_magnitude"]
            )
        ]
        if keep.empty:
            keep = interm_summary.head(12)
        cols = ["label", "column", "n", "mean", "std", "p05", "median", "p95"]
        lines.append(_to_markdown_table(keep, cols))

    lines += ["", "## Crystal Parameter Diagnostics", ""]
    if crystal_params.empty:
        lines.append("No crystal-parameter diagnostics were produced.")
    else:
        cols = [
            "label",
            "crystal_label_state",
            "n",
            "ln_x2_mae",
            "T_m_true_n",
            "T_m_mae",
            "T_m_bias",
            "T_m_pred_mean",
            "dH_fus_true_n",
            "Phi_pred_mean",
            "Phi_pred_std",
        ]
        lines.append(_to_markdown_table(crystal_params, cols))

    lines += ["", "## UNIFAC Coverage", ""]
    if unifac_coverage.empty:
        lines.append("No UNIFAC coverage summary was found.")
    else:
        cols = [
            "split_name",
            "n_rows",
            "n_unifac_rows",
            "row_coverage",
            "n_unique_pairs",
            "n_unifac_unique_pairs",
            "unique_pair_coverage",
            "n_solvents",
        ]
        lines.append(_to_markdown_table(unifac_coverage, cols))

    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    edges = [float(x.strip()) for x in args.bin_edges.split(",") if x.strip()]
    if len(edges) < 2:
        raise ValueError("--bin-edges must contain at least two numeric values")

    prediction_specs = _parse_specs(args.prediction, DEFAULT_PREDICTIONS)
    if not prediction_specs:
        raise FileNotFoundError("No prediction CSVs found. Pass --prediction LABEL=CSV.")

    frames = [load_prediction_csv(label, path) for label, path in prediction_specs]
    predictions = pd.concat(frames, axis=0, ignore_index=True)
    predictions.to_csv(out_dir / "all_predictions_with_errors.csv", index=False)

    model_summary = summarize_models(predictions)
    model_summary.to_csv(out_dir / "model_summary.csv", index=False)

    bin_metrics = summarize_bins(predictions, edges)
    bin_metrics.to_csv(out_dir / "lnx2_bin_metrics.csv", index=False)

    source_summary = source_error_summary(predictions)
    source_summary.to_csv(out_dir / "source_error_summary.csv", index=False)

    crystal_metrics = crystal_mask_metrics(predictions)
    crystal_metrics.to_csv(out_dir / "crystal_label_metrics.csv", index=False)

    pair_slopes = pair_slope_diagnostics(predictions, min_points=int(args.min_pair_points))
    pair_slopes.to_csv(out_dir / "pair_slope_diagnostics.csv", index=False)
    slope_summary = summarize_pair_slopes(pair_slopes)
    slope_summary.to_csv(out_dir / "pair_slope_summary.csv", index=False)

    worst_rows = (
        predictions.sort_values(["model", "abs_error"], ascending=[True, False])
        .groupby("model", sort=False)
        .head(int(args.top_k))
    )
    worst_rows.to_csv(out_dir / "top_worst_rows.csv", index=False)

    if "pair_key" in predictions.columns:
        pair_errors = (
            predictions.groupby(["model", "pair_key"], dropna=False)
            .agg(
                n=("abs_error", "size"),
                mae=("abs_error", "mean"),
                rmse=("signed_error", lambda x: float(np.sqrt(np.mean(np.square(x))))),
                bias=("signed_error", "mean"),
                solute_smiles=("solute_smiles", "first") if "solute_smiles" in predictions.columns else ("abs_error", "size"),
                solvent_smiles=("solvent_smiles", "first") if "solvent_smiles" in predictions.columns else ("abs_error", "size"),
            )
            .reset_index()
            .sort_values(["model", "mae"], ascending=[True, False])
        )
        pair_errors.to_csv(out_dir / "pair_error_summary.csv", index=False)
        pair_errors.groupby("model", sort=False).head(int(args.top_k)).to_csv(
            out_dir / "top_worst_pairs.csv", index=False
        )

    feature_df, feature_corr = residual_feature_correlations(predictions, skip_rdkit=bool(args.skip_rdkit))
    feature_df.to_csv(out_dir / "solute_rdkit_features.csv", index=False)
    feature_corr.to_csv(out_dir / "residual_feature_correlations.csv", index=False)

    intermediate_specs = _parse_specs(args.intermediates, DEFAULT_INTERMEDIATES)
    interm_summary, interm_corr = intermediate_diagnostics(intermediate_specs)
    interm_summary.to_csv(out_dir / "intermediate_numeric_summary.csv", index=False)
    interm_corr.to_csv(out_dir / "intermediate_correlations.csv", index=False)

    crystal_params = crystal_parameter_diagnostics(intermediate_specs)
    crystal_params.to_csv(out_dir / "crystal_parameter_diagnostics.csv", index=False)

    unifac_coverage = load_unifac_coverage(Path(args.unifac_coverage))
    unifac_coverage.to_csv(out_dir / "unifac_coverage_summary.csv", index=False)

    summary = {
        "prediction_specs": [(label, str(path)) for label, path in prediction_specs],
        "intermediate_specs": [(label, str(path)) for label, path in intermediate_specs],
        "unifac_coverage": str(args.unifac_coverage) if Path(args.unifac_coverage).exists() else None,
        "model_summary": model_summary.to_dict(orient="records"),
        "n_models": int(model_summary.shape[0]),
        "n_prediction_rows": int(predictions.shape[0]),
        "n_pair_slope_rows": int(pair_slopes.shape[0]),
        "n_sources_in_prediction_artifacts": int(source_summary["source"].nunique(dropna=False))
        if not source_summary.empty
        else 0,
        "outputs": sorted(p.name for p in out_dir.iterdir() if p.is_file()),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_ready(summary), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(
        out_dir,
        model_summary=model_summary,
        bin_metrics=bin_metrics,
        slope_summary=slope_summary,
        source_summary=source_summary,
        crystal_metrics=crystal_metrics,
        feature_corr=feature_corr,
        interm_summary=interm_summary,
        crystal_params=crystal_params,
        unifac_coverage=unifac_coverage,
    )
    print(f"Wrote offline diagnostics to {out_dir}")


if __name__ == "__main__":
    main()
