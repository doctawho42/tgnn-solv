#!/usr/bin/env python
"""CPU diagnostics for TGNN-Solv physical bottlenecks.

This script bundles the low-cost checks used to decide whether TGNN-Solv is
limited by crystal-property prediction, NRTL/solver identifiability, data
quality, or the final correction path. It does not train a model.

Inputs can be only processed SLE CSVs. If a TGNN intermediates CSV is also
provided, the script adds NRTL/correction diagnostics.
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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

R_GAS = 8.31446261815324

TEMPERATURE_COLUMNS = ("temperature", "T", "T_K", "temp_K")
TM_COLUMNS = ("T_m", "T_m_K", "Tm", "melting_point", "melting_point_K")
DH_COLUMNS = ("dH_fus", "dH_fus_J_mol", "dHfus", "delta_H_fus", "DeltaH_fus")
LN_X_COLUMNS = ("ln_x2", "ln_x2_true", "target", "y_true")
SOLUTE_COLUMNS = ("solute_smiles", "solute", "smiles_solute")
SOLVENT_COLUMNS = ("solvent_smiles", "solvent", "smiles_solvent")


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    if isinstance(value, np.ndarray):
        return json_ready(value.tolist())
    if isinstance(value, np.generic):
        return json_ready(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(json_ready(payload), indent=2), encoding="utf-8")


def as_bool_mask(series: pd.Series, default: bool = False) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(default).to_numpy(dtype=bool)
    normalized = series.fillna(default).astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "yes", "y", "t"}).to_numpy(dtype=bool)


def pick_column(df: pd.DataFrame, candidates: tuple[str, ...], *, required: bool = False) -> str | None:
    for name in candidates:
        if name in df.columns:
            return name
    if required:
        raise ValueError(f"Missing any of columns: {candidates}")
    return None


def numeric(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce")


def finite_array(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def finite_stats(values: Any) -> dict[str, Any]:
    arr = finite_array(values)
    if arr.size == 0:
        return {"n": 0}
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "p01": float(np.quantile(arr, 0.01)),
        "p05": float(np.quantile(arr, 0.05)),
        "median": float(np.median(arr)),
        "p95": float(np.quantile(arr, 0.95)),
        "p99": float(np.quantile(arr, 0.99)),
        "max": float(np.max(arr)),
    }


def regression_metrics(pred: Any, true: Any) -> dict[str, Any]:
    pred_arr = np.asarray(pred, dtype=float)
    true_arr = np.asarray(true, dtype=float)
    mask = np.isfinite(pred_arr) & np.isfinite(true_arr)
    pred_arr = pred_arr[mask]
    true_arr = true_arr[mask]
    if pred_arr.size == 0:
        return {"n": 0, "mae": None, "rmse": None, "r2": None, "bias": None}
    err = pred_arr - true_arr
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((true_arr - np.mean(true_arr)) ** 2))
    return {
        "n": int(pred_arr.size),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "r2": float(1.0 - ss_res / (ss_tot + 1e-12)) if pred_arr.size >= 2 else None,
        "bias": float(np.mean(err)),
    }


def load_supervised_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False).reset_index().rename(columns={"index": "row_index"})
    if "has_solubility" in df.columns:
        df = df.loc[as_bool_mask(df["has_solubility"], default=True)].copy()
    return df.reset_index(drop=True)


def compute_gc_prior(smiles: str, cache: dict[str, dict[str, float | None]]) -> dict[str, float | None]:
    """Compute cached crystal GC priors while keeping default diagnostics lightweight."""
    key = str(smiles)
    if key in cache:
        return cache[key]

    scripts_root = Path(__file__).resolve().parents[1]
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))
    try:
        import _bootstrap  # noqa: F401
        from tgnn_solv.group_contribution import GC_FALLBACK_PRIORS, compute_gc_priors

        priors = compute_gc_priors(key) or dict(GC_FALLBACK_PRIORS)
    except Exception:
        priors = {"T_m_gc": 400.0, "dH_fus_gc": 20000.0, "dCp_fus_gc": 0.0}

    cache[key] = priors
    return priors


def infer_dh_unit_and_values(dh: pd.Series) -> tuple[str, pd.Series]:
    finite = pd.to_numeric(dh, errors="coerce")
    finite_pos = finite[np.isfinite(finite) & (finite > 0)]
    if finite_pos.empty:
        return "unknown", finite
    median_abs = float(np.median(np.abs(finite_pos)))
    if median_abs < 500.0:
        return "kJ/mol_inferred_converted_to_J/mol", finite * 1000.0
    return "J/mol_inferred", finite


def prepare_pair_key(df: pd.DataFrame) -> pd.Series:
    if "pair_key" in df.columns:
        return df["pair_key"].astype(str)
    sol_col = pick_column(df, SOLUTE_COLUMNS, required=True)
    slv_col = pick_column(df, SOLVENT_COLUMNS, required=True)
    return df[sol_col].astype(str) + "||" + df[slv_col].astype(str)


def save_hist(values: Any, path: Path, title: str, xlabel: str, bins: int = 80) -> None:
    arr = finite_array(values)
    if arr.size == 0:
        return
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.hist(arr, bins=bins, alpha=0.8, color="#2563eb", edgecolor="white")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_scatter(x: Any, y: Any, path: Path, title: str, xlabel: str, ylabel: str) -> None:
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[mask]
    y_arr = y_arr[mask]
    if x_arr.size == 0:
        return
    if x_arr.size > 10000:
        rng = np.random.default_rng(42)
        idx = rng.choice(x_arr.size, size=10000, replace=False)
        x_arr = x_arr[idx]
        y_arr = y_arr[idx]
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    ax.scatter(x_arr, y_arr, s=7, alpha=0.25, color="#0f766e", edgecolors="none")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def ideal_solubility_analysis(
    df: pd.DataFrame,
    output_dir: Path,
    top_n: int,
    use_gc_fallback: bool,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    t_col = pick_column(df, TEMPERATURE_COLUMNS, required=True)
    tm_col = pick_column(df, TM_COLUMNS)
    dh_col = pick_column(df, DH_COLUMNS)
    ln_col = pick_column(df, LN_X_COLUMNS, required=True)
    slv_col = pick_column(df, SOLVENT_COLUMNS)

    if tm_col is None or dh_col is None:
        summary = {
            "status": "skipped",
            "reason": "missing T_m or dH_fus column",
            "temperature_column": t_col,
            "ln_x_column": ln_col,
            "use_gc_fallback": bool(use_gc_fallback),
        }
        write_json(output_dir / "ideal_solubility_summary.json", summary)
        return summary

    has_tm = as_bool_mask(df["has_T_m"], default=False) if "has_T_m" in df.columns else np.ones(len(df), dtype=bool)
    has_dh = as_bool_mask(df["has_dH_fus"], default=False) if "has_dH_fus" in df.columns else np.ones(len(df), dtype=bool)

    t = numeric(df, t_col)
    tm = numeric(df, tm_col)
    dh_unit, dh_j = infer_dh_unit_and_values(numeric(df, dh_col))
    ln_x = numeric(df, ln_col)
    base_mask = np.isfinite(t) & np.isfinite(ln_x) & (t > 0)
    tm_values = tm.copy()
    dh_values = dh_j.copy()
    param_source = np.full(len(df), "labels", dtype=object)
    direct_ok = (
        has_tm
        & has_dh
        & np.isfinite(tm_values)
        & np.isfinite(dh_values)
        & (tm_values > 0)
        & (dh_values > 0)
    )

    if use_gc_fallback:
        sol_col = pick_column(df, SOLUTE_COLUMNS, required=True)
        cache: dict[str, dict[str, float | None]] = {}
        needs_gc = base_mask & ~direct_ok
        for idx, row in df.loc[needs_gc].iterrows():
            priors = compute_gc_prior(str(row[sol_col]), cache)
            gc_tm = priors.get("T_m_gc")
            gc_dh = priors.get("dH_fus_gc")
            row_has_tm = bool(has_tm[idx] and np.isfinite(tm_values.loc[idx]) and tm_values.loc[idx] > 0)
            row_has_dh = bool(has_dh[idx] and np.isfinite(dh_values.loc[idx]) and dh_values.loc[idx] > 0)
            if not row_has_tm and gc_tm is not None and math.isfinite(float(gc_tm)) and float(gc_tm) > 0:
                tm_values.loc[idx] = float(gc_tm)
            if not row_has_dh and gc_dh is not None and math.isfinite(float(gc_dh)) and float(gc_dh) > 0:
                dh_values.loc[idx] = float(gc_dh)
            param_source[idx] = "mixed_label_gc" if (row_has_tm or row_has_dh) else "gc_fallback"
        mask = base_mask & np.isfinite(tm_values) & np.isfinite(dh_values) & (tm_values > 0) & (dh_values > 0)
    else:
        mask = base_mask & direct_ok

    rows = df.loc[mask].copy()
    if rows.empty:
        summary = {
            "status": "no_rows",
            "n_supervised_rows": int(len(df)),
            "n_rows_with_Tm_and_dH": 0,
            "dH_unit_inferred": dh_unit,
            "use_gc_fallback": bool(use_gc_fallback),
        }
        write_json(output_dir / "ideal_solubility_summary.json", summary)
        return summary

    t_v = t.loc[mask].to_numpy(dtype=float)
    tm_v = tm_values.loc[mask].to_numpy(dtype=float)
    dh_v = dh_values.loc[mask].to_numpy(dtype=float)
    y_true = ln_x.loc[mask].to_numpy(dtype=float)

    phi_raw = dh_v / R_GAS * (1.0 / t_v - 1.0 / tm_v)
    phi_clipped = np.clip(phi_raw, 0.0, 50.0)
    y_ideal = -phi_clipped
    ideal_error = y_ideal - y_true
    ln_gamma_implied = ideal_error

    out = rows[[c for c in ["row_index", "solute_smiles", "solvent_smiles", t_col, ln_col, tm_col, dh_col] if c in rows.columns]].copy()
    out = out.rename(columns={t_col: "temperature", ln_col: "ln_x2_true", tm_col: "T_m", dh_col: "dH_fus_input"})
    out["dH_fus_J_mol"] = dh_v
    out["crystal_param_source"] = param_source[mask]
    out["Phi_raw"] = phi_raw
    out["Phi_clipped"] = phi_clipped
    out["ln_x2_ideal"] = y_ideal
    out["ideal_error"] = ideal_error
    out["ln_gamma_implied"] = ln_gamma_implied
    out.to_csv(output_dir / "ideal_solubility_rows.csv", index=False)

    by_solvent_summary: list[dict[str, Any]] = []
    if slv_col is not None:
        group_source = out.copy()
        group_source["solvent_smiles"] = rows[slv_col].astype(str).to_numpy()
        grouped = group_source.groupby("solvent_smiles", sort=False)
        for solvent, group in grouped:
            if len(group) < 5:
                continue
            err = group["ideal_error"].to_numpy(dtype=float)
            gamma = group["ln_gamma_implied"].to_numpy(dtype=float)
            by_solvent_summary.append(
                {
                    "solvent_smiles": solvent,
                    "n": int(len(group)),
                    "mae_ideal": float(np.mean(np.abs(err))),
                    "bias_ideal": float(np.mean(err)),
                    "median_abs_ideal_error": float(np.median(np.abs(err))),
                    "mean_ln_gamma_implied": float(np.mean(gamma)),
                    "median_ln_gamma_implied": float(np.median(gamma)),
                    "std_ln_gamma_implied": float(np.std(gamma)),
                }
            )
    by_solvent = pd.DataFrame(by_solvent_summary)
    if not by_solvent.empty:
        by_solvent["abs_mean_ln_gamma_implied"] = by_solvent["mean_ln_gamma_implied"].abs()
        by_solvent = by_solvent.sort_values(["abs_mean_ln_gamma_implied", "n"], ascending=[False, False])
        by_solvent.to_csv(output_dir / "ideal_activity_by_solvent.csv", index=False)

    metrics = regression_metrics(y_ideal, y_true)
    summary = {
        "status": "ok",
        "n_supervised_rows": int(len(df)),
        "n_rows_with_Tm_and_dH": int(len(out)),
        "fraction_supervised_with_Tm_and_dH": float(len(out) / max(len(df), 1)),
        "temperature_column": t_col,
        "T_m_column": tm_col,
        "dH_column": dh_col,
        "dH_unit_inferred": dh_unit,
        "use_gc_fallback": bool(use_gc_fallback),
        "crystal_param_source_counts": out["crystal_param_source"].value_counts().to_dict(),
        "definition": "ln_x2_ideal = -clip(dH_fus/R * (1/T - 1/T_m), 0, 50), gamma_2=1",
        "metrics_ideal_vs_true": metrics,
        "ideal_error_stats": finite_stats(ideal_error),
        "abs_ideal_error_stats": finite_stats(np.abs(ideal_error)),
        "ln_gamma_implied_stats": finite_stats(ln_gamma_implied),
        "frac_abs_ideal_error_gt_1": float(np.mean(np.abs(ideal_error) > 1.0)),
        "frac_abs_ideal_error_gt_2": float(np.mean(np.abs(ideal_error) > 2.0)),
        "top_solvents_by_abs_mean_ln_gamma": by_solvent.head(top_n).to_dict(orient="records") if not by_solvent.empty else [],
    }
    write_json(output_dir / "ideal_solubility_summary.json", summary)
    save_hist(ideal_error, output_dir / "ideal_error_hist.png", "Ideal SLE error", "ln_x2_ideal - ln_x2_true")
    save_hist(ln_gamma_implied, output_dir / "ln_gamma_implied_hist.png", "Implied ln(gamma2)", "ln_x2_ideal - ln_x2_true")
    save_scatter(y_true, y_ideal, output_dir / "ideal_parity.png", "Ideal SLE parity", "ln_x2 true", "ln_x2 ideal")
    return summary


def vant_hoff_consistency(df: pd.DataFrame, output_dir: Path, min_points: int, min_temp_span: float) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    t_col = pick_column(df, TEMPERATURE_COLUMNS, required=True)
    ln_col = pick_column(df, LN_X_COLUMNS, required=True)
    pair_key = prepare_pair_key(df)
    work = df.copy()
    work["_pair_key"] = pair_key
    work["_temperature"] = numeric(work, t_col)
    work["_ln_x2"] = numeric(work, ln_col)
    work = work[np.isfinite(work["_temperature"]) & np.isfinite(work["_ln_x2"]) & (work["_temperature"] > 0)].copy()

    rows: list[dict[str, Any]] = []
    for key, group in work.groupby("_pair_key", sort=False):
        if len(group) < min_points:
            continue
        temp = group["_temperature"].to_numpy(dtype=float)
        y = group["_ln_x2"].to_numpy(dtype=float)
        temp_span = float(np.max(temp) - np.min(temp))
        if temp_span < min_temp_span:
            continue
        x = 1.0 / temp
        if np.std(x) <= 0 or np.std(y) <= 0:
            continue
        slope, intercept = np.polyfit(x, y, deg=1)
        pred = slope * x + intercept
        ss_res = float(np.sum((y - pred) ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = float(1.0 - ss_res / (ss_tot + 1e-12))
        rmse = float(np.sqrt(np.mean((y - pred) ** 2)))
        rows.append(
            {
                "pair_key": key,
                "n_points": int(len(group)),
                "n_unique_temperatures": int(pd.Series(temp).nunique()),
                "temperature_min": float(np.min(temp)),
                "temperature_max": float(np.max(temp)),
                "temperature_span": temp_span,
                "vant_hoff_slope_vs_invT": float(slope),
                "vant_hoff_intercept": float(intercept),
                "vant_hoff_r2": r2,
                "vant_hoff_rmse": rmse,
                "slope_negative_expected_for_endothermic": bool(slope < 0.0),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        summary = {
            "status": "no_pairs",
            "n_supervised_rows": int(len(df)),
            "min_points": int(min_points),
            "min_temp_span": float(min_temp_span),
            "note": "No same-pair groups had enough temperatures for Van't Hoff regression.",
        }
        write_json(output_dir / "vant_hoff_summary.json", summary)
        return summary

    out = out.sort_values(["vant_hoff_r2", "n_points"], ascending=[True, False])
    out.to_csv(output_dir / "vant_hoff_pair_consistency.csv", index=False)
    out.loc[out["vant_hoff_r2"] < 0.5].to_csv(output_dir / "vant_hoff_bad_pairs_r2_lt_0p5.csv", index=False)

    r2 = out["vant_hoff_r2"].to_numpy(dtype=float)
    summary = {
        "status": "ok",
        "n_pairs": int(len(out)),
        "n_pairs_r2_lt_0p5": int(np.sum(r2 < 0.5)),
        "fraction_pairs_r2_lt_0p5": float(np.mean(r2 < 0.5)),
        "n_pairs_n_points_ge_4_r2_lt_0p5": int(((out["n_points"] >= 4) & (out["vant_hoff_r2"] < 0.5)).sum()),
        "r2_stats": finite_stats(r2),
        "rmse_stats": finite_stats(out["vant_hoff_rmse"].to_numpy(dtype=float)),
        "slope_stats": finite_stats(out["vant_hoff_slope_vs_invT"].to_numpy(dtype=float)),
        "fraction_negative_slope": float(out["slope_negative_expected_for_endothermic"].mean()),
        "slope_sign_note": "Regression is ln_x2 versus 1/T; endothermic dissolution usually gives a negative slope because ln_x2 rises with T.",
        "min_points": int(min_points),
        "min_temp_span": float(min_temp_span),
    }
    write_json(output_dir / "vant_hoff_summary.json", summary)
    save_hist(r2, output_dir / "vant_hoff_r2_hist.png", "Same-pair Van't Hoff R2", "R2")
    save_hist(out["vant_hoff_slope_vs_invT"], output_dir / "vant_hoff_slope_hist.png", "Van't Hoff slope vs 1/T", "slope")
    save_scatter(out["n_points"], out["vant_hoff_r2"], output_dir / "vant_hoff_r2_vs_n_points.png", "Van't Hoff R2 vs points", "n points", "R2")
    return summary


def source_audit(df: pd.DataFrame, output_dir: Path, top_n: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ln_col = pick_column(df, LN_X_COLUMNS, required=True)
    source_cols = [c for c in ("source_detail", "source", "source_method_guess") if c in df.columns]
    summary: dict[str, Any] = {"status": "ok", "source_columns": source_cols}
    if "source_sigma_ln_x2" in df.columns:
        summary["source_sigma_ln_x2_stats"] = finite_stats(numeric(df, "source_sigma_ln_x2"))
    if not source_cols:
        summary["status"] = "skipped"
        summary["reason"] = "no source columns"
        write_json(output_dir / "source_audit_summary.json", summary)
        return summary

    for col in source_cols:
        rows: list[dict[str, Any]] = []
        for source, group in df.groupby(col, dropna=False, sort=False):
            y = numeric(group, ln_col).to_numpy(dtype=float)
            finite = y[np.isfinite(y)]
            if finite.size == 0:
                continue
            rows.append(
                {
                    col: str(source),
                    "n": int(finite.size),
                    "mean_ln_x2": float(np.mean(finite)),
                    "std_ln_x2": float(np.std(finite)),
                    "median_ln_x2": float(np.median(finite)),
                    "min_ln_x2": float(np.min(finite)),
                    "max_ln_x2": float(np.max(finite)),
                    "n_solutes": int(group[pick_column(group, SOLUTE_COLUMNS)].nunique()) if pick_column(group, SOLUTE_COLUMNS) else None,
                    "n_solvents": int(group[pick_column(group, SOLVENT_COLUMNS)].nunique()) if pick_column(group, SOLVENT_COLUMNS) else None,
                }
            )
        out = pd.DataFrame(rows).sort_values("n", ascending=False) if rows else pd.DataFrame()
        out.to_csv(output_dir / f"source_audit_by_{col}.csv", index=False)
        summary[f"by_{col}"] = {
            "n_sources": int(len(out)),
            "top_by_count": out.head(top_n).to_dict(orient="records") if not out.empty else [],
            "top_by_std_min_n_20": out.loc[out["n"] >= 20].sort_values("std_ln_x2", ascending=False).head(top_n).to_dict(orient="records") if not out.empty else [],
        }

    write_json(output_dir / "source_audit_summary.json", summary)
    return summary


def column_or_none(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    return pick_column(df, candidates)


def intermediates_diagnostics(path: Path | None, output_dir: Path, top_n: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if path is None:
        summary = {"status": "skipped", "reason": "no intermediates CSV provided"}
        write_json(output_dir / "intermediates_summary.json", summary)
        return summary
    if not path.exists():
        summary = {"status": "skipped", "reason": f"intermediates CSV not found: {path}"}
        write_json(output_dir / "intermediates_summary.json", summary)
        return summary

    df = pd.read_csv(path, low_memory=False)
    tau12_col = column_or_none(df, ("tau_12", "tau_12_pred", "tau12"))
    tau21_col = column_or_none(df, ("tau_21", "tau_21_pred", "tau21"))
    alpha_col = column_or_none(df, ("alpha_12", "alpha_pred", "alpha"))
    phys_col = column_or_none(df, ("ln_x2_physics", "ln_x2_phys"))
    final_col = column_or_none(df, ("ln_x2_final", "ln_x2_pred", "prediction", "y_pred"))
    true_col = column_or_none(df, ("ln_x2_true", "ln_x2", "target", "y_true"))
    phi_col = column_or_none(df, ("Phi", "Phi_pred", "phi"))
    lng_col = column_or_none(df, ("ln_gamma_2", "ln_gamma2_pred", "ln_gamma2", "ln_gamma_2_pred"))
    tm_pred_col = column_or_none(df, ("T_m_pred", "T_m_solver", "T_m"))
    tm_true_col = column_or_none(df, ("T_m_true", "T_m_target"))

    numeric_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "status": "ok",
        "intermediates_csv": str(path),
        "n_rows": int(len(df)),
        "n_solubility_rows": int(as_bool_mask(df["has_solubility"], default=True).sum())
        if "has_solubility" in df.columns
        else int(len(df)),
        "columns_used": {
            "tau_12": tau12_col,
            "tau_21": tau21_col,
            "alpha": alpha_col,
            "ln_x2_physics": phys_col,
            "ln_x2_final": final_col,
            "ln_x2_true": true_col,
            "Phi": phi_col,
            "ln_gamma_2": lng_col,
            "T_m_pred": tm_pred_col,
            "T_m_true": tm_true_col,
        },
    }

    for label, col in (("tau_12", tau12_col), ("tau_21", tau21_col), ("alpha", alpha_col)):
        if col is None:
            continue
        values = numeric(df, col).to_numpy(dtype=float)
        stats = finite_stats(values)
        if label.startswith("tau"):
            finite = finite_array(values)
            stats.update(
                {
                    "frac_abs_gt_5": float(np.mean(np.abs(finite) > 5.0)) if finite.size else None,
                    "frac_abs_gt_8": float(np.mean(np.abs(finite) > 8.0)) if finite.size else None,
                    "frac_abs_gt_10": float(np.mean(np.abs(finite) > 10.0)) if finite.size else None,
                }
            )
        summary[label] = stats
        numeric_rows.append({"quantity": label, **stats})
        save_hist(values, output_dir / f"{label}_hist.png", f"{label} distribution", label)

    if tau12_col is not None and tau21_col is not None:
        tau_sum = numeric(df, tau12_col).to_numpy(dtype=float) + numeric(df, tau21_col).to_numpy(dtype=float)
        summary["tau_sum"] = finite_stats(tau_sum)
        save_hist(tau_sum, output_dir / "tau_sum_hist.png", "tau_12 + tau_21", "tau sum")

    if phys_col is not None and final_col is not None:
        phys = numeric(df, phys_col).to_numpy(dtype=float)
        final = numeric(df, final_col).to_numpy(dtype=float)
        correction = final - phys
        finite_corr = finite_array(correction)
        corr_summary = {
            "stats": finite_stats(correction),
            "abs_stats": finite_stats(np.abs(correction)),
            "frac_abs_gt_0p5": float(np.mean(np.abs(finite_corr) > 0.5)) if finite_corr.size else None,
            "frac_abs_gt_1": float(np.mean(np.abs(finite_corr) > 1.0)) if finite_corr.size else None,
            "frac_abs_gt_2": float(np.mean(np.abs(finite_corr) > 2.0)) if finite_corr.size else None,
        }
        if true_col is not None:
            true = numeric(df, true_col).to_numpy(dtype=float)
            sol_mask = (
                as_bool_mask(df["has_solubility"], default=True)
                if "has_solubility" in df.columns
                else np.ones(len(df), dtype=bool)
            )
            corr_summary["metrics_filter"] = "has_solubility == True"
            corr_summary["physics_metrics_vs_true"] = regression_metrics(phys[sol_mask], true[sol_mask])
            corr_summary["final_metrics_vs_true"] = regression_metrics(final[sol_mask], true[sol_mask])
        summary["correction"] = corr_summary
        save_hist(correction, output_dir / "correction_hist.png", "Final correction", "ln_x2_final - ln_x2_physics")
        save_scatter(phys, final, output_dir / "physics_vs_final.png", "Physics path vs final", "ln_x2 physics", "ln_x2 final")

    if phi_col is not None and lng_col is not None:
        phi = numeric(df, phi_col).to_numpy(dtype=float)
        minus_lng = -numeric(df, lng_col).to_numpy(dtype=float)
        finite_mask = np.isfinite(phi) & np.isfinite(minus_lng)
        if finite_mask.any():
            abs_phi = np.abs(phi[finite_mask])
            abs_lng = np.abs(minus_lng[finite_mask])
            summary["crystal_vs_activity_contribution"] = {
                "n": int(finite_mask.sum()),
                "frac_abs_Phi_gt_abs_minus_ln_gamma": float(np.mean(abs_phi > abs_lng)),
                "median_abs_Phi": float(np.median(abs_phi)),
                "median_abs_minus_ln_gamma": float(np.median(abs_lng)),
                "median_abs_ratio_Phi_to_activity": float(np.median(abs_phi / np.maximum(abs_lng, 1e-8))),
            }
        save_scatter(phi, minus_lng, output_dir / "phi_vs_minus_ln_gamma.png", "Crystal vs activity contribution", "Phi", "-ln_gamma_2")

    if tm_pred_col is not None and tm_true_col is not None:
        tm_mask = (
            as_bool_mask(df["has_T_m"], default=False)
            if "has_T_m" in df.columns
            else np.ones(len(df), dtype=bool)
        )
        tm_metrics = regression_metrics(
            numeric(df, tm_pred_col).to_numpy(dtype=float)[tm_mask],
            numeric(df, tm_true_col).to_numpy(dtype=float)[tm_mask],
        )
        tm_metrics["metrics_filter"] = "has_T_m == True"
        summary["T_m_metrics"] = tm_metrics
        save_scatter(numeric(df, tm_true_col), numeric(df, tm_pred_col), output_dir / "tm_parity.png", "T_m parity", "T_m true", "T_m pred")

    if numeric_rows:
        pd.DataFrame(numeric_rows).to_csv(output_dir / "intermediates_numeric_summary.csv", index=False)
    write_json(output_dir / "intermediates_summary.json", summary)
    return summary


def write_top_level_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = ["# Physics Bottleneck Diagnostics", ""]
    lines.append("## Inputs")
    for key in ("train_data", "test_data", "intermediates_csv"):
        value = summary.get(key)
        if value:
            lines.append(f"- {key}: `{value}`")
    lines.append("")
    for split_name, split_summary in summary.get("splits", {}).items():
        lines.append(f"## {split_name}")
        ideal = split_summary.get("ideal_solubility", {})
        if ideal.get("status") == "ok":
            metrics = ideal.get("metrics_ideal_vs_true", {})
            row_label = (
                "ideal-SLE rows with labels/GC"
                if ideal.get("use_gc_fallback")
                else "ideal-SLE rows with direct labels"
            )
            lines.append(f"- {row_label}: `{ideal.get('n_rows_with_Tm_and_dH')}`")
            if ideal.get("use_gc_fallback"):
                lines.append(f"- crystal parameter sources: `{ideal.get('crystal_param_source_counts')}`")
            lines.append(f"- ideal-SLE MAE: `{metrics.get('mae'):.4f}`" if metrics.get("mae") is not None else "- ideal-SLE MAE: `n/a`")
            lines.append(f"- |ideal error| > 2: `{ideal.get('frac_abs_ideal_error_gt_2'):.3f}`")
        else:
            lines.append(f"- ideal-SLE: `{ideal.get('status')}`")
        vh = split_summary.get("vant_hoff", {})
        if vh.get("status") == "ok":
            r2_stats = vh.get("r2_stats", {})
            lines.append(f"- Van't Hoff pairs: `{vh.get('n_pairs')}`")
            lines.append(f"- Van't Hoff median R2: `{r2_stats.get('median'):.4f}`" if r2_stats.get("median") is not None else "- Van't Hoff median R2: `n/a`")
            lines.append(f"- Van't Hoff bad-pair fraction R2<0.5: `{vh.get('fraction_pairs_r2_lt_0p5'):.3f}`")
        else:
            lines.append(f"- Van't Hoff: `{vh.get('status')}`")
        lines.append("")
    inter = summary.get("intermediates", {})
    lines.append("## Intermediates")
    if inter.get("status") == "ok":
        correction = inter.get("correction", {})
        final_metrics = correction.get("final_metrics_vs_true", {})
        phys_metrics = correction.get("physics_metrics_vs_true", {})
        if phys_metrics:
            lines.append(f"- physics-path MAE: `{phys_metrics.get('mae'):.4f}`")
        if final_metrics:
            lines.append(f"- final MAE: `{final_metrics.get('mae'):.4f}`")
        if correction.get("abs_stats", {}).get("median") is not None:
            lines.append(f"- median |final-physics correction|: `{correction['abs_stats']['median']:.4f}`")
        for tau_key in ("tau_12", "tau_21"):
            tau = inter.get(tau_key, {})
            if tau.get("n"):
                lines.append(f"- {tau_key} median: `{tau.get('median'):.4f}`, frac |tau|>8: `{tau.get('frac_abs_gt_8'):.3f}`")
    else:
        lines.append(f"- status: `{inter.get('status')}` ({inter.get('reason')})")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_for_split(name: str, path: Path, output_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    split_dir = output_dir / name
    split_dir.mkdir(parents=True, exist_ok=True)
    df = load_supervised_csv(path)
    return {
        "data": str(path),
        "n_supervised_rows": int(len(df)),
        "ideal_solubility": ideal_solubility_analysis(
            df,
            split_dir / "ideal_solubility",
            args.top_n,
            args.ideal_use_gc_fallback,
        ),
        "vant_hoff": vant_hoff_consistency(df, split_dir / "vant_hoff", args.min_vh_points, args.min_vh_temp_span),
        "source_audit": source_audit(df, split_dir / "source_audit", args.top_n),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--train-data", type=Path, default=Path("notebooks/data/processed/train.csv"))
    parser.add_argument("--test-data", type=Path, default=Path("notebooks/data/processed/test.csv"))
    parser.add_argument("--intermediates-csv", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--min-vh-points", type=int, default=3)
    parser.add_argument("--min-vh-temp-span", type=float, default=5.0)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--ideal-use-gc-fallback",
        action="store_true",
        help="Fill missing T_m/dH_fus with Joback-style crystal GC priors for ideal-SLE diagnostics.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "train_data": str(args.train_data) if args.train_data else None,
        "test_data": str(args.test_data) if args.test_data else None,
        "intermediates_csv": str(args.intermediates_csv) if args.intermediates_csv else None,
        "ideal_use_gc_fallback": bool(args.ideal_use_gc_fallback),
        "splits": {},
    }

    if args.train_data and args.train_data.exists():
        summary["splits"]["train"] = run_for_split("train", args.train_data, output_dir, args)
    if args.test_data and args.test_data.exists():
        summary["splits"]["test"] = run_for_split("test", args.test_data, output_dir, args)

    summary["intermediates"] = intermediates_diagnostics(args.intermediates_csv, output_dir / "intermediates", args.top_n)
    write_json(output_dir / "summary.json", summary)
    write_top_level_markdown(summary, output_dir / "SUMMARY.md")
    print(json.dumps(json_ready(summary), indent=2))


if __name__ == "__main__":
    main()
