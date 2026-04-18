#!/usr/bin/env python3
"""Build a standalone IDAC auxiliary stream in processed-dataset format.

Unlike `attach_idac_aux_to_fixed_splits.py`, this script does not append IDAC
rows to any supervised SLE split. The output is a separate CSV intended for:

    python scripts/training/train.py ... --idac-train-data <output.csv>

The trainer consumes it through the gamma-only objective.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a standalone gamma_inf auxiliary CSV for TGNN training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--idac-csv",
        default="notebooks/data/raw/idac_expanded.csv",
        help="Aggregated IDAC CSV with solute_smiles, solvent_smiles, temperature, ln_gamma_inf or gamma_inf.",
    )
    parser.add_argument(
        "--template-csv",
        default="notebooks/data/processed/train.csv",
        help="Processed SLE CSV whose column contract should be mirrored.",
    )
    parser.add_argument(
        "--output-csv",
        default="notebooks/data/processed_idac_aux_stream/idac_train.csv",
        help="Standalone aux-only IDAC stream CSV to write.",
    )
    parser.add_argument(
        "--summary-json",
        default="notebooks/data/processed_idac_aux_stream/summary.json",
        help="Summary JSON path.",
    )
    parser.add_argument(
        "--source-label",
        default="aux_only_gamma_expanded_stream",
        help="Source label assigned to generated IDAC rows.",
    )
    parser.add_argument(
        "--temperature-decimals",
        type=int,
        default=3,
        help="Temperature rounding used when aggregating duplicate IDAC keys.",
    )
    return parser.parse_args()


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


def _load_idac(path: Path, *, temperature_decimals: int) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False).copy()
    required = {"solute_smiles", "solvent_smiles", "temperature"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")
    if "ln_gamma_inf" not in df.columns:
        if "gamma_inf" not in df.columns:
            raise ValueError(f"{path} must contain ln_gamma_inf or gamma_inf")
        gamma = pd.to_numeric(df["gamma_inf"], errors="coerce")
        df["ln_gamma_inf"] = np.log(gamma.where(gamma > 0))

    out = df[["solute_smiles", "solvent_smiles", "temperature", "ln_gamma_inf"]].copy()
    out["solute_smiles"] = out["solute_smiles"].astype(str)
    out["solvent_smiles"] = out["solvent_smiles"].astype(str)
    out["temperature"] = pd.to_numeric(out["temperature"], errors="coerce")
    out["ln_gamma_inf"] = pd.to_numeric(out["ln_gamma_inf"], errors="coerce")
    out = out.dropna(
        subset=["solute_smiles", "solvent_smiles", "temperature", "ln_gamma_inf"]
    )
    finite = (
        np.isfinite(out["temperature"].to_numpy(dtype=float))
        & np.isfinite(out["ln_gamma_inf"].to_numpy(dtype=float))
    )
    out = out.loc[finite].copy()
    out["temperature"] = out["temperature"].round(int(temperature_decimals))
    out = (
        out.groupby(["solute_smiles", "solvent_smiles", "temperature"], as_index=False)
        .agg(
            ln_gamma_inf=("ln_gamma_inf", "mean"),
            n_idac_records=("ln_gamma_inf", "count"),
        )
    )
    return out


def _empty_row_template(columns: list[str]) -> dict[str, Any]:
    row = {col: "" for col in columns}
    numeric_defaults = {
        "temperature": 298.15,
        "ln_x2": 0.0,
        "T_m": 0.0,
        "dH_fus": 0.0,
        "hansen_d": 0.0,
        "hansen_p": 0.0,
        "hansen_h": 0.0,
        "ln_gamma_inf": 0.0,
        "gamma_weight": 1.0,
    }
    bool_defaults = {
        "has_solubility": False,
        "has_T_m": False,
        "has_dH_fus": False,
        "has_hansen": False,
        "has_gamma_inf": False,
        "fda_approved": "No",
    }
    for key, value in numeric_defaults.items():
        if key in row:
            row[key] = value
    for key, value in bool_defaults.items():
        if key in row:
            row[key] = value
    return row


def _ensure_aux_columns(columns: list[str]) -> list[str]:
    out = list(columns)
    if "gamma_weight" not in out:
        out.append("gamma_weight")
    return out


def build_aux_stream(
    idac: pd.DataFrame,
    *,
    template_columns: list[str],
    source_label: str,
) -> pd.DataFrame:
    template = _empty_row_template(template_columns)
    rows: list[dict[str, Any]] = []
    for record in idac.itertuples(index=False):
        row = dict(template)
        row["solute_smiles"] = str(record.solute_smiles)
        row["solvent_smiles"] = str(record.solvent_smiles)
        row["temperature"] = float(record.temperature)
        row["ln_gamma_inf"] = float(record.ln_gamma_inf)
        row["gamma_weight"] = 1.0
        if "source" in row:
            row["source"] = source_label
        if "has_gamma_inf" in row:
            row["has_gamma_inf"] = True
        if "has_solubility" in row:
            row["has_solubility"] = False
        rows.append(row)
    return pd.DataFrame(rows, columns=template_columns)


def main() -> None:
    args = parse_args()
    idac_path = Path(args.idac_csv)
    template_path = Path(args.template_csv)
    output_path = Path(args.output_csv)
    summary_path = Path(args.summary_json)

    template = pd.read_csv(template_path, nrows=1, low_memory=False)
    idac = _load_idac(idac_path, temperature_decimals=args.temperature_decimals)
    aux = build_aux_stream(
        idac,
        template_columns=_ensure_aux_columns(list(template.columns)),
        source_label=args.source_label,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    aux.to_csv(output_path, index=False)

    summary = {
        "idac_csv": idac_path,
        "template_csv": template_path,
        "output_csv": output_path,
        "source_label": args.source_label,
        "temperature_decimals": int(args.temperature_decimals),
        "n_rows": int(len(aux)),
        "n_pairs": int(aux[["solute_smiles", "solvent_smiles"]].drop_duplicates().shape[0]),
        "n_solutes": int(aux["solute_smiles"].nunique()),
        "n_solvents": int(aux["solvent_smiles"].nunique()),
        "ln_gamma_inf_mean": float(aux["ln_gamma_inf"].mean()),
        "ln_gamma_inf_std": float(aux["ln_gamma_inf"].std()),
        "appended_to_sle_splits": False,
    }
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
