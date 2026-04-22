#!/usr/bin/env python3
"""Consolidate temperature-extrapolation failure diagnostics.

This script is intentionally analysis-only: it does not train models.  It
collects the existing low-to-high temperature extrapolation artifacts, compares
Van't Hoff slopes, audits TGNN internal physical quantities, computes chemistry
slices, and writes a report-ready bundle.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - plotting is optional in headless envs
    plt = None

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors
except Exception:  # pragma: no cover
    Chem = None
    Descriptors = None
    rdMolDescriptors = None


ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--baseline-predictions",
        default="results/temperature_extrapolation_baselines/predictions.csv",
    )
    parser.add_argument(
        "--directgnn-predictions",
        default="results/temperature_extrapolation_slope_diagnostics/directgnn_proxy_predictions.csv",
    )
    parser.add_argument(
        "--tgnn-intermediates",
        default="results/temperature_extrapolation_slope_diagnostics/tgnn_proxy_intermediates/intermediates.csv",
    )
    parser.add_argument(
        "--oracle-tm-intermediates",
        default="results/temperature_extrapolation_slope_diagnostics/tgnn_proxy_intermediates/oracle_tm_intermediates.csv",
    )
    parser.add_argument(
        "--split-audit-summary",
        default="results/temperature_extrapolation_baselines/audit/split_audit_summary.json",
    )
    parser.add_argument(
        "--baseline-summary",
        default="results/temperature_extrapolation_baselines/summary.json",
    )
    parser.add_argument(
        "--neural-summary",
        default="results/temperature_extrapolation_neural_proxy/summary.json",
    )
    parser.add_argument(
        "--enhanced-summary",
        default="results/temperature_extrapolation_enhanced_proxy/summary.json",
    )
    parser.add_argument("--config", default="configs/paper_config_tuned.yaml")
    parser.add_argument(
        "--output-dir",
        default="results/temperature_extrapolation_failure_diagnostics",
    )
    parser.add_argument("--min-temps", type=int, default=3)
    return parser.parse_args()


def _path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def safe_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def detect_model_inputs(args: argparse.Namespace) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    baseline_path = _path(args.baseline_predictions)
    if baseline_path.exists():
        base = pd.read_csv(baseline_path, low_memory=False)
        if "eval_split" in base.columns:
            base = base[base["eval_split"].astype(str) == "test"].copy()
        keep_models = {
            "pair_vant_hoff",
            "pair_linear_T",
            "rf_morgan_T",
            "pair_last_low_T",
            "pair_mean",
        }
        base = base[base["model"].astype(str).isin(keep_models)].copy()
        frames.append(
            base[
                [
                    "pair_key",
                    "solute_smiles",
                    "solvent_smiles",
                    "temperature",
                    "ln_x2_true",
                    "ln_x2_pred",
                    "model",
                ]
            ]
        )

    direct_path = _path(args.directgnn_predictions)
    if direct_path.exists():
        direct = pd.read_csv(direct_path, low_memory=False)
        direct["model"] = direct.get("model", "directgnn_proxy_ep10")
        frames.append(
            direct[
                [
                    "pair_key",
                    "solute_smiles",
                    "solvent_smiles",
                    "temperature",
                    "ln_x2_true",
                    "ln_x2_pred",
                    "model",
                ]
            ]
        )

    tgnn_path = _path(args.tgnn_intermediates)
    if tgnn_path.exists():
        tgnn = pd.read_csv(tgnn_path, low_memory=False)
        final = tgnn.rename(columns={"ln_x2_final": "ln_x2_pred"}).copy()
        final["model"] = "tgnn_proxy_p1_8_1"
        frames.append(
            final[
                [
                    "pair_key",
                    "solute_smiles",
                    "solvent_smiles",
                    "temperature",
                    "ln_x2_true",
                    "ln_x2_pred",
                    "model",
                ]
            ]
        )
        if "ln_x2_physics" in tgnn.columns:
            phys = tgnn.rename(columns={"ln_x2_physics": "ln_x2_pred"}).copy()
            phys["model"] = "tgnn_physics_only_p1_8_1"
            frames.append(
                phys[
                    [
                        "pair_key",
                        "solute_smiles",
                        "solvent_smiles",
                        "temperature",
                        "ln_x2_true",
                        "ln_x2_pred",
                        "model",
                    ]
                ]
            )

    if not frames:
        raise FileNotFoundError("No prediction artifacts were found.")

    out = pd.concat(frames, ignore_index=True)
    out["temperature"] = safe_num(out["temperature"])
    out["ln_x2_true"] = safe_num(out["ln_x2_true"])
    out["ln_x2_pred"] = safe_num(out["ln_x2_pred"])
    out = out[np.isfinite(out["temperature"]) & np.isfinite(out["ln_x2_true"]) & np.isfinite(out["ln_x2_pred"])]
    out["signed_error"] = out["ln_x2_pred"] - out["ln_x2_true"]
    out["abs_error"] = out["signed_error"].abs()
    return out


def fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    slope, intercept = np.polyfit(x, y, deg=1)
    pred = slope * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / (ss_tot + 1e-12)
    return float(slope), float(intercept), float(r2)


def safe_corr(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> float | None:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2 or np.std(x) == 0.0 or np.std(y) == 0.0:
        return None
    value = float(np.corrcoef(x, y)[0, 1])
    return value if math.isfinite(value) else None


def build_pair_slopes(predictions: pd.DataFrame, min_temps: int) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for (model, pair_key), group in predictions.groupby(["model", "pair_key"], sort=False):
        group = group.sort_values("temperature")
        if group["temperature"].nunique() < min_temps:
            continue
        x = 1.0 / group["temperature"].to_numpy(dtype=float)
        if np.std(x) == 0.0:
            continue
        y_true = group["ln_x2_true"].to_numpy(dtype=float)
        y_pred = group["ln_x2_pred"].to_numpy(dtype=float)
        slope_true, intercept_true, r2_true = fit_line(x, y_true)
        slope_pred, intercept_pred, r2_pred = fit_line(x, y_pred)
        errors = y_pred - y_true
        records.append(
            {
                "model": model,
                "pair_key": pair_key,
                "solute_smiles": group["solute_smiles"].iloc[0],
                "solvent_smiles": group["solvent_smiles"].iloc[0],
                "n_rows": int(len(group)),
                "n_temps": int(group["temperature"].nunique()),
                "temperature_min": float(group["temperature"].min()),
                "temperature_max": float(group["temperature"].max()),
                "slope_true": slope_true,
                "slope_pred": slope_pred,
                "slope_error": slope_pred - slope_true,
                "abs_slope_error": abs(slope_pred - slope_true),
                "intercept_true": intercept_true,
                "intercept_pred": intercept_pred,
                "intercept_error": intercept_pred - intercept_true,
                "r2_true": r2_true,
                "r2_pred": r2_pred,
                "pair_mae": float(np.mean(np.abs(errors))),
                "pair_bias": float(np.mean(errors)),
                "true_delta_ln_x2": float(y_true[-1] - y_true[0]),
                "pred_delta_ln_x2": float(y_pred[-1] - y_pred[0]),
            }
        )
    return pd.DataFrame(records)


def summarize_slopes(pair_slopes: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model, group in pair_slopes.groupby("model", sort=False):
        slope_error = group["slope_error"].to_numpy(dtype=float)
        abs_slope_error = np.abs(slope_error)
        sign_mask = np.abs(group["slope_true"].to_numpy(dtype=float)) > 1e-9
        sign_acc = (
            float(
                np.mean(
                    np.sign(group.loc[sign_mask, "slope_pred"].to_numpy(dtype=float))
                    == np.sign(group.loc[sign_mask, "slope_true"].to_numpy(dtype=float))
                )
            )
            if sign_mask.any()
            else None
        )
        rows.append(
            {
                "model": model,
                "n_pairs": int(len(group)),
                "n_rows": int(group["n_rows"].sum()),
                "slope_mae_K": float(np.mean(abs_slope_error)),
                "slope_rmse_K": float(np.sqrt(np.mean(slope_error**2))),
                "slope_bias_K": float(np.mean(slope_error)),
                "slope_median_abs_error_K": float(np.median(abs_slope_error)),
                "slope_q90_abs_error_K": float(np.quantile(abs_slope_error, 0.90)),
                "slope_pearson_r": safe_corr(group["slope_true"], group["slope_pred"]),
                "slope_sign_accuracy": sign_acc,
                "mean_true_slope_K": float(group["slope_true"].mean()),
                "mean_pred_slope_K": float(group["slope_pred"].mean()),
                "pred_slope_std_K": float(group["slope_pred"].std(ddof=1)) if len(group) > 1 else 0.0,
                "pair_mae_mean": float(group["pair_mae"].mean()),
                "pair_mae_median": float(group["pair_mae"].median()),
                "pair_bias_mean": float(group["pair_bias"].mean()),
                "r2_true_mean": float(group["r2_true"].mean()),
                "r2_pred_mean": float(group["r2_pred"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(["pair_mae_mean", "slope_mae_K"])


def row_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, group in predictions.groupby("model", sort=False):
        err = group["signed_error"].to_numpy(dtype=float)
        true = group["ln_x2_true"].to_numpy(dtype=float)
        pred = group["ln_x2_pred"].to_numpy(dtype=float)
        ss_res = float(np.sum((pred - true) ** 2))
        ss_tot = float(np.sum((true - np.mean(true)) ** 2))
        rows.append(
            {
                "model": model,
                "n": int(len(group)),
                "mae": float(np.mean(np.abs(err))),
                "rmse": float(np.sqrt(np.mean(err**2))),
                "r2": float(1.0 - ss_res / (ss_tot + 1e-12)),
                "bias": float(np.mean(err)),
                "pred_std": float(np.std(pred, ddof=1)),
                "true_std": float(np.std(true, ddof=1)),
            }
        )
    return pd.DataFrame(rows).sort_values("mae")


_MOL_CACHE: dict[str, Any] = {}


def mol_from_smiles(smiles: str):
    if Chem is None:
        return None
    key = str(smiles)
    if key not in _MOL_CACHE:
        try:
            _MOL_CACHE[key] = Chem.MolFromSmiles(key)
        except Exception:
            _MOL_CACHE[key] = None
    return _MOL_CACHE[key]


def heavy_atoms(smiles: str) -> int | None:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return None
    return int(mol.GetNumHeavyAtoms())


def has_aromatic(smiles: str) -> bool:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return False
    return any(atom.GetIsAromatic() for atom in mol.GetAtoms())


def is_hydrocarbon(smiles: str) -> bool:
    mol = mol_from_smiles(smiles)
    if mol is None:
        return False
    return all(atom.GetAtomicNum() in {1, 6} for atom in mol.GetAtoms())


def has_smarts(smiles: str, smarts: str) -> bool:
    mol = mol_from_smiles(smiles)
    if mol is None or Chem is None:
        return False
    patt = Chem.MolFromSmarts(smarts)
    return bool(patt is not None and mol.HasSubstructMatch(patt))


def hbd_hba(smiles: str) -> tuple[int, int]:
    mol = mol_from_smiles(smiles)
    if mol is None or rdMolDescriptors is None:
        return 0, 0
    return int(rdMolDescriptors.CalcNumHBD(mol)), int(rdMolDescriptors.CalcNumHBA(mol))


def add_chemistry_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["is_water_solvent"] = out["solvent_smiles"].astype(str).isin({"O", "[H]O[H]"})
    out["solvent_heavy_atoms"] = out["solvent_smiles"].map(heavy_atoms)
    out["small_solvent_le3_heavy"] = out["solvent_heavy_atoms"].fillna(999).astype(float) <= 3
    out["alcohol_solvent"] = out["solvent_smiles"].map(lambda s: has_smarts(str(s), "[OX2H]"))
    out["aromatic_solvent"] = out["solvent_smiles"].map(lambda s: has_aromatic(str(s)))
    out["hydrocarbon_solvent"] = out["solvent_smiles"].map(lambda s: is_hydrocarbon(str(s)))
    out["aromatic_solute"] = out["solute_smiles"].map(lambda s: has_aromatic(str(s)))
    hbd_hba_values = out["solute_smiles"].map(lambda s: hbd_hba(str(s)))
    out["solute_hbd"] = [v[0] for v in hbd_hba_values]
    out["solute_hba"] = [v[1] for v in hbd_hba_values]
    out["hbonding_solute"] = (out["solute_hbd"] > 0) | (out["solute_hba"] > 0)
    out["low_solubility_true"] = out["ln_x2_true"] <= -8.0
    out["very_high_temperature"] = out["temperature"] >= 360.0
    return out


def chemistry_slices(predictions: pd.DataFrame) -> pd.DataFrame:
    enriched = add_chemistry_flags(predictions)
    slices = [
        ("water_solvent", "is_water_solvent"),
        ("small_solvent_le3_heavy", "small_solvent_le3_heavy"),
        ("alcohol_solvent", "alcohol_solvent"),
        ("aromatic_solvent", "aromatic_solvent"),
        ("hydrocarbon_solvent", "hydrocarbon_solvent"),
        ("aromatic_solute", "aromatic_solute"),
        ("hbonding_solute", "hbonding_solute"),
        ("low_solubility_true_lte_minus8", "low_solubility_true"),
        ("temperature_gte_360K", "very_high_temperature"),
    ]
    records: list[dict[str, Any]] = []
    for model, group in enriched.groupby("model", sort=False):
        total_mae = float(group["abs_error"].mean())
        for slice_name, col in slices:
            mask = group[col].fillna(False).astype(bool)
            if int(mask.sum()) == 0:
                continue
            comp = ~mask
            records.append(
                {
                    "model": model,
                    "slice": slice_name,
                    "n_slice": int(mask.sum()),
                    "fraction": float(mask.mean()),
                    "mae_slice": float(group.loc[mask, "abs_error"].mean()),
                    "mae_complement": float(group.loc[comp, "abs_error"].mean()) if comp.any() else None,
                    "delta_vs_model_overall": float(group.loc[mask, "abs_error"].mean() - total_mae),
                }
            )
    return pd.DataFrame(records)


def internal_summary(tgnn_path: Path, oracle_path: Path | None = None) -> dict[str, Any]:
    if not tgnn_path.exists():
        return {"available": False}
    df = pd.read_csv(tgnn_path, low_memory=False)
    pred_cols = [
        "ln_x2_true",
        "ln_x2_final",
        "ln_x2_physics",
        "T_m_solver",
        "dH_fus_solver",
        "tau_12_pred",
        "tau_21_pred",
        "alpha_pred",
        "ln_gamma2_pred",
        "Phi_pred",
        "correction_magnitude",
        "gate_value",
        "abs_error",
    ]
    stats = {}
    for col in pred_cols:
        if col not in df.columns:
            continue
        values = pd.to_numeric(df[col], errors="coerce")
        values = values[np.isfinite(values)]
        if values.empty:
            continue
        stats[col] = {
            "mean": float(values.mean()),
            "std": float(values.std(ddof=1)),
            "min": float(values.min()),
            "q05": float(values.quantile(0.05)),
            "median": float(values.median()),
            "q95": float(values.quantile(0.95)),
            "max": float(values.max()),
        }
    out: dict[str, Any] = {
        "available": True,
        "n_rows": int(len(df)),
        "stats": stats,
    }

    if {"T_m_true", "T_m_solver"}.issubset(df.columns):
        tm = df[["T_m_true", "T_m_solver"]].copy()
        tm["T_m_true"] = pd.to_numeric(tm["T_m_true"], errors="coerce")
        tm["T_m_solver"] = pd.to_numeric(tm["T_m_solver"], errors="coerce")
        tm = tm[np.isfinite(tm["T_m_true"]) & np.isfinite(tm["T_m_solver"])]
        if not tm.empty:
            err = tm["T_m_solver"] - tm["T_m_true"]
            out["tm_metrics"] = {
                "n": int(len(tm)),
                "mae_K": float(err.abs().mean()),
                "bias_K": float(err.mean()),
                "pred_std_K": float(tm["T_m_solver"].std(ddof=1)),
                "true_std_K": float(tm["T_m_true"].std(ddof=1)),
                "pearson_r": safe_corr(tm["T_m_true"], tm["T_m_solver"]),
            }

    if {"ln_x2_final", "ln_x2_physics"}.issubset(df.columns):
        corr = (pd.to_numeric(df["ln_x2_final"], errors="coerce") - pd.to_numeric(df["ln_x2_physics"], errors="coerce")).abs()
        out["physics_correction"] = {
            "mean_abs": float(corr.mean()),
            "median_abs": float(corr.median()),
            "p95_abs": float(corr.quantile(0.95)),
        }

    if oracle_path and oracle_path.exists():
        oracle = pd.read_csv(oracle_path, low_memory=False)
        if {"ln_x2_final", "ln_x2_true"}.issubset(oracle.columns):
            std_err = pd.to_numeric(df["ln_x2_final"], errors="coerce") - pd.to_numeric(df["ln_x2_true"], errors="coerce")
            oracle_err = pd.to_numeric(oracle["ln_x2_final"], errors="coerce") - pd.to_numeric(oracle["ln_x2_true"], errors="coerce")
            out["oracle_tm_only"] = {
                "mae_standard": float(std_err.abs().mean()),
                "mae_oracle_tm": float(oracle_err.abs().mean()),
                "delta_mae": float(oracle_err.abs().mean() - std_err.abs().mean()),
            }
    return out


def solver_budget_audit(args: argparse.Namespace) -> dict[str, Any]:
    config_path = _path(args.config)
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    keys = [
        "n_iter_train",
        "n_iter_eval",
        "damping",
        "solver_min_damping",
        "solver_adaptive_damping",
    ]
    settings: dict[str, Any] = {}
    for key in keys:
        m = re.search(rf"^\s*{re.escape(key)}\s*:\s*([^#\n]+)", text, flags=re.MULTILINE)
        if m:
            raw = m.group(1).strip()
            if raw.lower() in {"true", "false"}:
                settings[key] = raw.lower() == "true"
            else:
                try:
                    settings[key] = int(raw)
                except ValueError:
                    try:
                        settings[key] = float(raw)
                    except ValueError:
                        settings[key] = raw

    neural = read_json(_path(args.neural_summary))
    enhanced = read_json(_path(args.enhanced_summary))
    budget_rows = []
    for row in neural.get("neural_results", []):
        budget_rows.append(
            {
                "model": row.get("model"),
                "kind": row.get("kind"),
                "budget": row.get("budget"),
                "mae": row.get("mae"),
                "r2": row.get("r2"),
                "device": row.get("device"),
            }
        )
    for row in enhanced.get("completed_runs", []):
        budget_rows.append(
            {
                "model": row.get("model"),
                "kind": row.get("kind"),
                "budget": row.get("budget"),
                "mae": row.get("mae"),
                "r2": row.get("r2"),
                "device": row.get("device"),
            }
        )
    return {
        "config": str(config_path),
        "solver_settings": settings,
        "proxy_budget_results": budget_rows,
        "interpretation": (
            "Existing neural temperature-extrapolation numbers are local proxy runs. "
            "They are suitable for diagnostics but not for final claims about the full 50/200/50 curriculum."
        ),
    }


def write_plots(
    *,
    output_dir: Path,
    slope_metrics: pd.DataFrame,
    pair_slopes: pd.DataFrame,
    internal: dict[str, Any],
    slices: pd.DataFrame,
    budget: dict[str, Any],
) -> list[str]:
    if plt is None:
        return []

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "pdf.fonttype": 42,
            "figure.facecolor": "#FBFAF7",
            "axes.facecolor": "#FBFAF7",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    colors = {
        "pair_vant_hoff": "#5E967D",
        "pair_linear_T": "#7AA2B8",
        "directgnn_proxy_ep10": "#4F7F9B",
        "tgnn_proxy_p1_8_1": "#D79A83",
        "tgnn_physics_only_p1_8_1": "#B9A7D9",
        "rf_morgan_T": "#B9A7D9",
        "pair_last_low_T": "#9CA3AF",
        "pair_mean": "#C6CCD3",
    }
    artifacts: list[str] = []

    if not slope_metrics.empty:
        plot_df = slope_metrics.sort_values("pair_mae_mean")
        labels = plot_df["model"].tolist()
        fig, ax = plt.subplots(figsize=(8.8, 4.8))
        x = np.arange(len(plot_df))
        bars = ax.bar(
            x,
            plot_df["pair_mae_mean"],
            color=[colors.get(m, "#9CA3AF") for m in labels],
            edgecolor="#FFFFFF",
            linewidth=1,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=25, ha="right")
        ax.set_ylabel("Mean per-pair MAE")
        ax.set_title("Temperature extrapolation: value error")
        ax.grid(True, axis="y", color="#E7E3DA")
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.04, f"{h:.2f}", ha="center", fontsize=8)
        fig.tight_layout()
        path = output_dir / "temperature_value_error_comparison.pdf"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(str(path))

        fig, ax = plt.subplots(figsize=(8.8, 4.8))
        bars = ax.bar(
            x,
            plot_df["slope_median_abs_error_K"],
            color=[colors.get(m, "#9CA3AF") for m in labels],
            edgecolor="#FFFFFF",
            linewidth=1,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=25, ha="right")
        ax.set_ylabel("Median absolute slope error, K")
        ax.set_title("Temperature extrapolation: slope recovery")
        ax.grid(True, axis="y", color="#E7E3DA")
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 45, f"{h:.0f}", ha="center", fontsize=8)
        fig.tight_layout()
        path = output_dir / "temperature_slope_error_comparison.pdf"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(str(path))

    selected = pair_slopes[pair_slopes["model"].isin(["pair_vant_hoff", "directgnn_proxy_ep10", "tgnn_proxy_p1_8_1"])]
    if not selected.empty:
        fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2), sharex=True, sharey=True)
        for ax, (model, group) in zip(axes, selected.groupby("model", sort=False)):
            lo = np.quantile(np.concatenate([group["slope_true"], group["slope_pred"]]), 0.02)
            hi = np.quantile(np.concatenate([group["slope_true"], group["slope_pred"]]), 0.98)
            ax.scatter(group["slope_true"], group["slope_pred"], s=10, alpha=0.45, color=colors.get(model, "#9CA3AF"))
            ax.plot([lo, hi], [lo, hi], color="#6B7280", ls="--", lw=1)
            ax.axhline(0, color="#D7D2C7", lw=0.8)
            ax.axvline(0, color="#D7D2C7", lw=0.8)
            ax.set_title(model)
            ax.set_xlim(lo, hi)
            ax.set_ylim(lo, hi)
            ax.grid(True, color="#E7E3DA", lw=0.7)
        axes[0].set_ylabel("Predicted slope, K")
        for ax in axes:
            ax.set_xlabel("True slope, K")
        fig.suptitle("Van't Hoff slope recovery", y=1.02)
        fig.tight_layout()
        path = output_dir / "temperature_slope_scatter.pdf"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(str(path))

    if internal.get("available"):
        stats = internal.get("stats", {})
        names = ["ln_x2_true", "ln_x2_final", "Phi_pred", "ln_gamma2_pred", "tau_12_pred", "tau_21_pred"]
        stds = [stats.get(name, {}).get("std", np.nan) for name in names]
        fig, ax = plt.subplots(figsize=(8.8, 4.8))
        x = np.arange(len(names))
        bars = ax.bar(x, stds, color=["#5E967D", "#D79A83", "#E4C27D", "#8AB7A1", "#B9A7D9", "#B9A7D9"])
        ax.set_xticks(x)
        ax.set_xticklabels(["true ln x2", "TGNN ln x2", "Phi", "ln gamma2", "tau12", "tau21"], rotation=20, ha="right")
        ax.set_yscale("symlog", linthresh=1e-3)
        ax.set_ylabel("Standard deviation")
        ax.set_title("TGNN proxy internal variation")
        ax.grid(True, axis="y", color="#E7E3DA")
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h * 1.08 if h > 0 else 0.001, f"{h:.3g}", ha="center", fontsize=8)
        fig.tight_layout()
        path = output_dir / "tgnn_internal_variation.pdf"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        artifacts.append(str(path))

    if not slices.empty:
        focus_models = ["pair_vant_hoff", "directgnn_proxy_ep10", "tgnn_proxy_p1_8_1"]
        focus_slices = ["water_solvent", "small_solvent_le3_heavy", "alcohol_solvent", "aromatic_solvent", "low_solubility_true_lte_minus8", "temperature_gte_360K"]
        plot_df = slices[slices["model"].isin(focus_models) & slices["slice"].isin(focus_slices)].copy()
        if not plot_df.empty:
            pivot = plot_df.pivot(index="slice", columns="model", values="mae_slice").reindex(focus_slices)
            fig, ax = plt.subplots(figsize=(9.4, 5.2))
            pivot.plot(kind="bar", ax=ax, color=[colors.get(c, "#9CA3AF") for c in pivot.columns])
            ax.set_ylabel("MAE on slice")
            ax.set_xlabel("")
            ax.set_title("Temperature extrapolation chemistry slices")
            ax.grid(True, axis="y", color="#E7E3DA")
            ax.legend(title="")
            fig.tight_layout()
            path = output_dir / "temperature_chemistry_slices.pdf"
            fig.savefig(path, bbox_inches="tight")
            plt.close(fig)
            artifacts.append(str(path))

    budget_rows = pd.DataFrame(budget.get("proxy_budget_results", []))
    if not budget_rows.empty and "mae" in budget_rows.columns:
        plot_df = budget_rows.dropna(subset=["mae"]).copy()
        if not plot_df.empty:
            plot_df["label"] = plot_df["kind"].fillna(plot_df["model"]).astype(str).str.replace("_", "\n")
            fig, ax = plt.subplots(figsize=(9.5, 4.8))
            x = np.arange(len(plot_df))
            bars = ax.bar(x, plot_df["mae"], color="#D79A83", edgecolor="#FFFFFF")
            ax.set_xticks(x)
            ax.set_xticklabels(plot_df["label"], rotation=25, ha="right", fontsize=8)
            ax.set_ylabel("Test MAE")
            ax.set_title("Proxy budget results")
            ax.grid(True, axis="y", color="#E7E3DA")
            for bar in bars:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.03, f"{h:.2f}", ha="center", fontsize=8)
            fig.tight_layout()
            path = output_dir / "temperature_proxy_budget_results.pdf"
            fig.savefig(path, bbox_inches="tight")
            plt.close(fig)
            artifacts.append(str(path))
    return artifacts


def write_readme(output_dir: Path, summary: dict[str, Any]) -> None:
    row_metrics_table = pd.DataFrame(summary.get("row_metrics", []))
    slope_table = pd.DataFrame(summary.get("slope_metrics", []))

    def _plain_table(df: pd.DataFrame, cols: list[str]) -> str:
        if df.empty:
            return ""
        view = df[cols].copy()
        for col in view.columns:
            if pd.api.types.is_float_dtype(view[col]):
                view[col] = view[col].map(lambda x: "" if pd.isna(x) else f"{x:.4f}")
        return view.to_string(index=False)

    lines = [
        "# Temperature Extrapolation Failure Diagnostics",
        "",
        "This bundle consolidates same-pair low-to-high temperature diagnostics.",
        "",
        "## Row Metrics",
        "",
    ]
    if not row_metrics_table.empty:
        lines.append("```")
        lines.append(_plain_table(row_metrics_table, ["model", "n", "mae", "r2", "bias", "pred_std", "true_std"]))
        lines.append("```")
    lines.extend(["", "## Slope Metrics", ""])
    if not slope_table.empty:
        cols = [
            "model",
            "n_pairs",
            "pair_mae_mean",
            "slope_median_abs_error_K",
            "slope_mae_K",
            "slope_sign_accuracy",
            "pred_slope_std_K",
        ]
        lines.append("```")
        lines.append(_plain_table(slope_table, cols))
        lines.append("```")
    lines.extend(["", "## Main Interpretation", ""])
    for item in summary.get("main_findings", []):
        lines.append(f"- {item}")
    output_dir.joinpath("README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = _path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    predictions = detect_model_inputs(args)
    predictions.to_csv(output_dir / "combined_predictions.csv", index=False)

    rows = row_metrics(predictions)
    rows.to_csv(output_dir / "row_metrics.csv", index=False)

    slopes = build_pair_slopes(predictions, min_temps=args.min_temps)
    slopes.to_csv(output_dir / f"pair_slopes_min{args.min_temps}.csv", index=False)
    slope_metrics = summarize_slopes(slopes)
    slope_metrics.to_csv(output_dir / f"slope_metrics_min{args.min_temps}.csv", index=False)

    slices = chemistry_slices(predictions)
    slices.to_csv(output_dir / "chemistry_slices.csv", index=False)

    internal = internal_summary(_path(args.tgnn_intermediates), _path(args.oracle_tm_intermediates))
    (output_dir / "tgnn_internal_summary.json").write_text(json.dumps(_json_ready(internal), indent=2), encoding="utf-8")

    budget = solver_budget_audit(args)
    (output_dir / "solver_budget_audit.json").write_text(json.dumps(_json_ready(budget), indent=2), encoding="utf-8")

    split_audit = read_json(_path(args.split_audit_summary))
    baseline = read_json(_path(args.baseline_summary))

    findings: list[str] = []
    if not rows.empty:
        tgnn_row = rows[rows["model"] == "tgnn_proxy_p1_8_1"]
        if not tgnn_row.empty:
            findings.append(
                f"TGNN proxy final predictions have MAE={tgnn_row['mae'].iloc[0]:.3f} and prediction std={tgnn_row['pred_std'].iloc[0]:.3f}, "
                f"versus true std={tgnn_row['true_std'].iloc[0]:.3f}."
            )
    if internal.get("available"):
        tau_std = internal.get("stats", {}).get("tau_12_pred", {}).get("std")
        gamma_std = internal.get("stats", {}).get("ln_gamma2_pred", {}).get("std")
        corr_mean = internal.get("physics_correction", {}).get("mean_abs")
        tm_mae = internal.get("tm_metrics", {}).get("mae_K")
        oracle_delta = internal.get("oracle_tm_only", {}).get("delta_mae")
        if tau_std is not None and gamma_std is not None:
            findings.append(
                f"TGNN NRTL branch is nearly collapsed in this proxy: std(tau12)={tau_std:.2e}, std(ln gamma2)={gamma_std:.2e}."
            )
        if corr_mean is not None:
            findings.append(f"The bounded correction is inactive: mean |ln_x2_final-ln_x2_physics|={corr_mean:.2e}.")
        if tm_mae is not None and oracle_delta is not None:
            findings.append(
                f"On rows with Tm labels, Tm MAE is {tm_mae:.1f} K; substituting oracle Tm changes total MAE by {oracle_delta:.3f}."
            )
    if not slope_metrics.empty:
        tgnn_slope = slope_metrics[slope_metrics["model"] == "tgnn_proxy_p1_8_1"]
        direct_slope = slope_metrics[slope_metrics["model"] == "directgnn_proxy_ep10"]
        vh_slope = slope_metrics[slope_metrics["model"] == "pair_vant_hoff"]
        if not tgnn_slope.empty and not direct_slope.empty and not vh_slope.empty:
            findings.append(
                "For pairs with at least three high-temperature points, median slope error is "
                f"{vh_slope['slope_median_abs_error_K'].iloc[0]:.0f} K for pair Van't Hoff, "
                f"{tgnn_slope['slope_median_abs_error_K'].iloc[0]:.0f} K for TGNN proxy, and "
                f"{direct_slope['slope_median_abs_error_K'].iloc[0]:.0f} K for DirectGNN proxy."
            )
    findings.append(
        "No new full-budget training was run in this diagnostic pass; existing neural results remain proxy-budget evidence."
    )

    artifacts = write_plots(
        output_dir=output_dir,
        slope_metrics=slope_metrics,
        pair_slopes=slopes,
        internal=internal,
        slices=slices,
        budget=budget,
    )

    summary = {
        "created_at": "2026-04-19",
        "scope": "same-pair low-to-high temperature extrapolation failure diagnostics",
        "min_temps_for_slope_metrics": int(args.min_temps),
        "inputs": {
            "baseline_predictions": str(_path(args.baseline_predictions)),
            "directgnn_predictions": str(_path(args.directgnn_predictions)),
            "tgnn_intermediates": str(_path(args.tgnn_intermediates)),
            "split_audit_summary": str(_path(args.split_audit_summary)),
        },
        "row_metrics": rows.to_dict(orient="records"),
        "slope_metrics": slope_metrics.to_dict(orient="records"),
        "internal_summary": internal,
        "solver_budget_audit": budget,
        "split_audit_key": split_audit,
        "baseline_key": baseline.get("results", {}).get("trend", []),
        "main_findings": findings,
        "artifacts": {
            "combined_predictions": str(output_dir / "combined_predictions.csv"),
            "row_metrics": str(output_dir / "row_metrics.csv"),
            "pair_slopes": str(output_dir / f"pair_slopes_min{args.min_temps}.csv"),
            "slope_metrics": str(output_dir / f"slope_metrics_min{args.min_temps}.csv"),
            "chemistry_slices": str(output_dir / "chemistry_slices.csv"),
            "internal_summary": str(output_dir / "tgnn_internal_summary.json"),
            "solver_budget_audit": str(output_dir / "solver_budget_audit.json"),
            "plots": artifacts,
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(_json_ready(summary), indent=2), encoding="utf-8")
    write_readme(output_dir, summary)

    print(f"Wrote temperature failure diagnostics to {output_dir}")
    for finding in findings:
        print(f"- {finding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
