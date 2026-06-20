#!/usr/bin/env python3
"""Build an exact finite-activity auxiliary stream from jointly labeled SLE rows.

The output mirrors the loose processed-CSV contract accepted by
`scripts/train.py --idac-train-data`. Each auxiliary row carries an exact
`ln_gamma_2` target derived from measured `ln_x2`, `T_m`, and `dH_fus`:

    ln_gamma_2 = -ln_x2 - Phi_true
    Phi_true = (dH_fus / R) * (1 / T - 1 / T_m)

This path is intended for compensation-focused experiments where the goal is to
oversample rows with simultaneous solubility and crystal supervision instead of
relying on sparse batchwise coincidence inside the main train stream.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

R_GAS_J_MOL_K = 8.31446261815324


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-csv",
        default="notebooks/data/processed/train.csv",
        help="Processed SLE CSV to mine for jointly labeled rows.",
    )
    parser.add_argument(
        "--template-csv",
        default=None,
        help="Processed CSV whose columns should be mirrored. Defaults to --input-csv.",
    )
    parser.add_argument(
        "--output-csv",
        default="notebooks/data/processed_exact_joint_gamma2_aux_stream/gamma2_aux_train.csv",
        help="Output auxiliary CSV.",
    )
    parser.add_argument(
        "--summary-json",
        default="notebooks/data/processed_exact_joint_gamma2_aux_stream/summary.json",
        help="Output summary JSON.",
    )
    parser.add_argument(
        "--source-label",
        default="aux_only_gamma2_exact_joint",
        help="Source label written to output rows when a source column exists.",
    )
    parser.add_argument(
        "--gamma2-weight",
        type=float,
        default=1.0,
        help="Per-row finite-activity sample weight.",
    )
    parser.add_argument(
        "--temperature-decimals",
        type=int,
        default=3,
        help="Round temperatures before deduplication.",
    )
    parser.add_argument(
        "--composition-decimals",
        type=int,
        default=6,
        help="Round x2 before export.",
    )
    parser.add_argument(
        "--drop-duplicates",
        action="store_true",
        help="Drop duplicate (solute, solvent, temperature, x2) states after derivation.",
    )
    return parser.parse_args()


def _bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


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


def _ensure_aux_columns(columns: list[str]) -> list[str]:
    out = list(columns)
    for col in ("ln_gamma_2", "activity_x2", "has_gamma_2", "gamma2_weight"):
        if col not in out:
            out.append(col)
    return out


def _template_row(columns: list[str]) -> dict[str, Any]:
    row = {col: "" for col in columns}
    defaults: dict[str, Any] = {
        "temperature": 298.15,
        "ln_x2": 0.0,
        "T_m": 0.0,
        "dH_fus": 0.0,
        "hansen_d": 0.0,
        "hansen_p": 0.0,
        "hansen_h": 0.0,
        "ln_gamma_inf": 0.0,
        "ln_gamma_2": 0.0,
        "activity_x2": 0.0,
        "gamma_weight": 1.0,
        "gamma2_weight": 1.0,
        "has_solubility": False,
        "has_T_m": False,
        "has_dH_fus": False,
        "has_hansen": False,
        "has_gamma_inf": False,
        "has_gamma_2": False,
        "fda_approved": "No",
    }
    for key, value in defaults.items():
        if key in row:
            row[key] = value
    return row


def _load_joint_rows(path: Path, *, temperature_decimals: int) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False).copy()
    required = {
        "solute_smiles",
        "solvent_smiles",
        "temperature",
        "ln_x2",
        "T_m",
        "dH_fus",
        "has_solubility",
        "has_T_m",
        "has_dH_fus",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    mask = (
        _bool_series(df["has_solubility"])
        & _bool_series(df["has_T_m"])
        & _bool_series(df["has_dH_fus"])
    )
    df = df.loc[mask].copy()
    if df.empty:
        raise ValueError(f"{path} contains no jointly labeled solubility/crystal rows.")

    numeric_cols = ("temperature", "ln_x2", "T_m", "dH_fus")
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["solute_smiles", "solvent_smiles", *numeric_cols]).copy()
    df["temperature"] = df["temperature"].round(int(temperature_decimals))
    df = df.loc[
        np.isfinite(df["temperature"].to_numpy(dtype=float))
        & np.isfinite(df["ln_x2"].to_numpy(dtype=float))
        & np.isfinite(df["T_m"].to_numpy(dtype=float))
        & np.isfinite(df["dH_fus"].to_numpy(dtype=float))
        & (df["temperature"].to_numpy(dtype=float) > 0.0)
        & (df["T_m"].to_numpy(dtype=float) > 0.0)
    ].copy()
    return df.reset_index(drop=True)


def _make_aux_row(
    template: dict[str, Any],
    record: pd.Series,
    *,
    source_label: str,
    gamma2_weight: float,
    composition_decimals: int,
) -> dict[str, Any]:
    temperature = float(record["temperature"])
    ln_x2 = float(record["ln_x2"])
    T_m = float(record["T_m"])
    dH_fus = float(record["dH_fus"])
    activity_x2 = round(
        float(np.clip(math.exp(ln_x2), 1.0e-8, 1.0 - 1.0e-8)),
        int(composition_decimals),
    )
    phi_true = (dH_fus / R_GAS_J_MOL_K) * ((1.0 / temperature) - (1.0 / T_m))
    ln_gamma_2 = -ln_x2 - phi_true

    row = dict(template)
    for key in (
        "solute_smiles",
        "solvent_smiles",
        "solute_name",
        "solvent_name",
        "fda_approved",
    ):
        if key in record.index and key in row:
            row[key] = record[key]

    if "source" in row:
        row["source"] = source_label
    row["temperature"] = temperature
    row["ln_x2"] = 0.0
    row["T_m"] = 0.0
    row["dH_fus"] = 0.0
    row["has_solubility"] = False
    row["has_T_m"] = False
    row["has_dH_fus"] = False
    row["ln_gamma_inf"] = 0.0
    row["has_gamma_inf"] = False
    row["activity_x2"] = activity_x2
    row["ln_gamma_2"] = float(ln_gamma_2)
    row["has_gamma_2"] = True
    row["gamma2_weight"] = float(gamma2_weight)
    return row


def main() -> None:
    args = parse_args()

    input_path = Path(args.input_csv)
    template_path = Path(args.template_csv) if args.template_csv else input_path
    output_path = Path(args.output_csv)
    summary_path = Path(args.summary_json)

    joint_df = _load_joint_rows(
        input_path,
        temperature_decimals=int(args.temperature_decimals),
    )
    template_df = pd.read_csv(template_path, nrows=1, low_memory=False)
    columns = _ensure_aux_columns(template_df.columns.tolist())
    template = _template_row(columns)

    rows = [
        _make_aux_row(
            template,
            record=row,
            source_label=str(args.source_label),
            gamma2_weight=float(args.gamma2_weight),
            composition_decimals=int(args.composition_decimals),
        )
        for _, row in joint_df.iterrows()
    ]
    out_df = pd.DataFrame(rows, columns=columns)
    if args.drop_duplicates:
        out_df = out_df.drop_duplicates(
            subset=["solute_smiles", "solvent_smiles", "temperature", "activity_x2"]
        ).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(output_path, index=False)

    pair_df = joint_df[["solute_smiles", "solvent_smiles"]].drop_duplicates()
    summary = {
        "input_csv": str(input_path),
        "template_csv": str(template_path),
        "output_csv": str(output_path),
        "n_joint_rows_input": int(len(joint_df)),
        "n_joint_rows_output": int(len(out_df)),
        "n_unique_pairs": int(len(pair_df)),
        "n_unique_solutes": int(joint_df["solute_smiles"].nunique()),
        "n_unique_solvents": int(joint_df["solvent_smiles"].nunique()),
        "temperature_decimals": int(args.temperature_decimals),
        "composition_decimals": int(args.composition_decimals),
        "gamma2_weight": float(args.gamma2_weight),
        "drop_duplicates": bool(args.drop_duplicates),
        "source_label": str(args.source_label),
        "formula": {
            "phi_true": "(dH_fus / R) * (1/T - 1/T_m)",
            "ln_gamma_2": "-ln_x2 - phi_true",
            "R_gas_j_mol_k": R_GAS_J_MOL_K,
        },
    }
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
