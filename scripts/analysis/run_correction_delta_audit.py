#!/usr/bin/env python3
"""Summarize what the bounded correction block changes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


DELTA_COLUMNS = [
    "delta_T_m",
    "delta_dH_fraction",
    "delta_tau_12",
    "delta_tau_21",
    "correction_gate",
    "correction_magnitude",
]


def _stats(series: pd.Series) -> dict[str, float]:
    arr = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {
            "n": 0,
            "mean": float("nan"),
            "std": float("nan"),
            "median_abs": float("nan"),
            "p90_abs": float("nan"),
            "max_abs": float("nan"),
        }
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "median_abs": float(np.median(np.abs(arr))),
        "p90_abs": float(np.quantile(np.abs(arr), 0.90)),
        "max_abs": float(np.max(np.abs(arr))),
    }


def _std_ratio(df: pd.DataFrame, delta_col: str, base_col: str) -> float:
    if delta_col not in df.columns or base_col not in df.columns:
        return float("nan")
    delta = pd.to_numeric(df[delta_col], errors="coerce").to_numpy(dtype=float)
    base = pd.to_numeric(df[base_col], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(delta) & np.isfinite(base)
    if mask.sum() == 0:
        return float("nan")
    base_std = float(np.std(base[mask]))
    if base_std <= 0:
        return float("inf") if float(np.std(delta[mask])) > 0 else float("nan")
    return float(np.std(delta[mask]) / base_std)


def _table_text(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return df.to_string(index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit correction-block deltas exported with predictions."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    df = pd.read_csv(args.input, low_memory=False)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    label = args.label or args.input.stem

    rows: list[dict[str, object]] = []
    for col in DELTA_COLUMNS:
        if col not in df.columns:
            continue
        rows.append({"quantity": col, **_stats(df[col])})

    ratios = {
        "std_delta_tau12_over_std_tau12": _std_ratio(df, "delta_tau_12", "tau_12"),
        "std_delta_tau21_over_std_tau21": _std_ratio(df, "delta_tau_21", "tau_21"),
        "std_delta_Tm_over_std_Tm_solver": _std_ratio(df, "delta_T_m", "T_m_solver"),
    }

    summary = {
        "label": label,
        "input": str(args.input),
        "rows": int(len(df)),
        "available_delta_columns": [col for col in DELTA_COLUMNS if col in df.columns],
        "stats": rows,
        "ratios": ratios,
    }
    pd.DataFrame(rows).to_csv(args.out_dir / "correction_delta_stats.csv", index=False)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )

    lines = [
        "# Correction-Block Delta Audit",
        "",
        f"Model: {label}",
        f"Rows: {len(df):,}",
        "",
        "## Delta Statistics",
        "",
        _table_text(pd.DataFrame(rows)) if rows else "No delta columns found.",
        "",
        "## Scale Ratios",
        "",
    ]
    for key, value in ratios.items():
        lines.append(f"- `{key}`: {value:.6g}")
    lines.append("")
    (args.out_dir / "SUMMARY.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
