#!/usr/bin/env python3
"""Evaluate a no-ML ideal-SLE baseline on a processed TGNN-Solv split.

The baseline uses the Hildebrand crystal term and assumes ideal mixing:

    ln x2 = -Phi = -dH_fus/R * (1/T - 1/T_m)

Where supervised crystal labels are missing, train-free Joback-style GC priors
are used as a deterministic fallback.
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
from tgnn_solv.group_contribution import GC_FALLBACK_PRIORS, compute_gc_priors  # noqa: E402
from tgnn_solv.reporting import json_safe  # noqa: E402

R_GAS = 8.314462618


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ideal-SLE baseline on a processed test CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--test-data", type=str, required=True)
    parser.add_argument("--output-dir", type=str, required=True)
    return parser.parse_args()


def bool_mask(series: pd.Series, default: bool = False) -> np.ndarray:
    if series is None:
        return np.full(0, default, dtype=bool)
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(default).to_numpy(dtype=bool)
    normalized = series.fillna(default).astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "yes", "y", "t"}).to_numpy(dtype=bool)


def supervised_mask(df: pd.DataFrame) -> np.ndarray:
    if "has_solubility" not in df.columns:
        return np.ones(len(df), dtype=bool)
    return bool_mask(df["has_solubility"])


def safe_float(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def regression_metrics(pred: np.ndarray, true: np.ndarray) -> dict[str, Any]:
    pred = np.asarray(pred, dtype=float)
    true = np.asarray(true, dtype=float)
    mask = np.isfinite(pred) & np.isfinite(true)
    pred = pred[mask]
    true = true[mask]
    if pred.size < 2:
        return {"n": int(pred.size), "mae": None, "rmse": None, "r2": None}
    err = pred - true
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((true - np.mean(true)) ** 2))
    return {
        "n": int(pred.size),
        "n_samples": int(pred.size),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "r2": float(1.0 - ss_res / (ss_tot + 1e-10)),
        "bias": float(np.mean(err)),
        "test_mae": float(np.mean(np.abs(err))),
        "test_rmse": float(np.sqrt(np.mean(err**2))),
        "test_r2": float(1.0 - ss_res / (ss_tot + 1e-10)),
    }


def crystal_params(row: pd.Series) -> tuple[float, float, str]:
    """Return `(T_m, dH_fus, source)` with GC fallback when needed."""
    def row_bool(name: str) -> bool:
        value = row.get(name, False)
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y", "t"}
        return bool(value)

    has_tm = row_bool("has_T_m")
    has_dh = row_bool("has_dH_fus")
    tm = safe_float(row.get("T_m")) if has_tm else None
    dh = safe_float(row.get("dH_fus")) if has_dh else None

    gc = None
    if tm is None or dh is None:
        try:
            gc = compute_gc_priors(str(row.get("solute_smiles", "")))
        except Exception:
            gc = GC_FALLBACK_PRIORS
        if gc is None:
            gc = GC_FALLBACK_PRIORS
    if tm is None:
        tm = safe_float(gc.get("T_m_gc")) if gc else None
    if dh is None:
        dh = safe_float(gc.get("dH_fus_gc")) if gc else None
    tm = tm if tm is not None else float(GC_FALLBACK_PRIORS["T_m_gc"])
    dh = dh if dh is not None else float(GC_FALLBACK_PRIORS["dH_fus_gc"])
    source = (
        "labels"
        if has_tm and has_dh
        else ("mixed_label_gc" if has_tm or has_dh else "gc_fallback")
    )
    return float(tm), float(dh), source


def ideal_ln_x2(row: pd.Series) -> tuple[float, float, float, str]:
    temperature = safe_float(row.get("temperature"))
    if temperature is None:
        temperature = 298.15
    tm, dh, source = crystal_params(row)
    tm = max(float(tm), 1.0)
    temperature = max(float(temperature), 1.0)
    phi = float(dh) / R_GAS * (1.0 / temperature - 1.0 / tm)
    ln_x2 = float(np.clip(-phi, -30.0, 0.0))
    return ln_x2, phi, tm, source


def main() -> None:
    args = parse_args()
    test_path = _bootstrap.resolve_path(args.test_data)
    output_dir = _bootstrap.resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(test_path, low_memory=False).reset_index().rename(columns={"index": "row_index"})
    df = df.loc[supervised_mask(df)].reset_index(drop=True)

    predictions: list[float] = []
    phis: list[float] = []
    tm_values: list[float] = []
    sources: list[str] = []
    for _, row in df.iterrows():
        ln_x2, phi, tm, source = ideal_ln_x2(row)
        predictions.append(ln_x2)
        phis.append(phi)
        tm_values.append(tm)
        sources.append(source)

    y_true = df["ln_x2"].to_numpy(dtype=float)
    y_pred = np.asarray(predictions, dtype=float)
    metrics = regression_metrics(y_pred, y_true)
    payload = {
        "model": "ideal_sle",
        "baseline_definition": "ln_x2 = -dH_fus/R * (1/T - 1/T_m), gamma_2=1",
        "test_data": str(test_path),
        "overall": metrics,
        "mae": metrics.get("mae"),
        "rmse": metrics.get("rmse"),
        "r2": metrics.get("r2"),
        "source_counts": pd.Series(sources).value_counts().to_dict(),
    }
    (output_dir / "metrics.json").write_text(
        json.dumps(json_safe(payload), indent=2),
        encoding="utf-8",
    )

    pred_df = df[["row_index", "solute_smiles", "solvent_smiles", "temperature", "ln_x2"]].copy()
    pred_df["ln_x2_pred"] = y_pred
    pred_df["Phi"] = phis
    pred_df["T_m_used"] = tm_values
    pred_df["crystal_param_source"] = sources
    pred_df.to_csv(output_dir / "predictions.csv", index=False)

    print(json.dumps(json_safe(payload), indent=2))


if __name__ == "__main__":
    main()
