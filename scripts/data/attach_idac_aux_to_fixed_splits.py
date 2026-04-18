#!/usr/bin/env python3
"""Attach expanded IDAC auxiliary rows to fixed processed splits.

This script preserves the supervised train/val/test split exactly and appends
new `gamma_inf` auxiliary-only rows to train splits only. Use it when evaluating
expanded IDAC supervision without changing the benchmark protocol.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SPLIT_TRIPLETS = {
    "solute_scaffold": ("train.csv", "val.csv", "test.csv"),
    "solute": ("train_solute.csv", "val_solute.csv", "test_solute.csv"),
    "solvent": ("train_solvent.csv", "val_solvent.csv", "test_solvent.csv"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy existing processed splits and append expanded IDAC rows to "
            "train only, preserving validation/test supervised protocols."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--processed-dir",
        default="notebooks/data/processed",
        help="Existing processed split directory to preserve.",
    )
    parser.add_argument(
        "--idac-csv",
        default="notebooks/data/raw/idac_expanded.csv",
        help="Aggregated expanded IDAC CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="notebooks/data/processed_idac_expanded_train_aux",
        help="Output directory for fixed splits plus train-only IDAC aux rows.",
    )
    parser.add_argument(
        "--source-label",
        default="aux_only_gamma_expanded",
        help="Source value used for appended IDAC rows.",
    )
    parser.add_argument(
        "--temperature-decimals",
        type=int,
        default=3,
        help="Temperature rounding for duplicate-key matching.",
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


def _bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _gamma_key_frame(df: pd.DataFrame, *, temperature_decimals: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "solute_smiles": df["solute_smiles"].astype(str),
            "solvent_smiles": df["solvent_smiles"].astype(str),
            "temperature_key": pd.to_numeric(df["temperature"], errors="coerce").round(
                temperature_decimals
            ),
        }
    )


def _key_set(df: pd.DataFrame, *, temperature_decimals: int) -> set[tuple[str, str, float]]:
    keys = _gamma_key_frame(df, temperature_decimals=temperature_decimals).dropna()
    return set(keys.itertuples(index=False, name=None))


def _load_idac(path: Path) -> pd.DataFrame:
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
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["ln_gamma_inf"] = pd.to_numeric(df["ln_gamma_inf"], errors="coerce")
    df = df.dropna(
        subset=["solute_smiles", "solvent_smiles", "temperature", "ln_gamma_inf"]
    ).copy()
    finite = (
        np.isfinite(df["temperature"].to_numpy(dtype=float))
        & np.isfinite(df["ln_gamma_inf"].to_numpy(dtype=float))
    )
    return df.loc[finite].reset_index(drop=True)


def _empty_row_template(columns: list[str]) -> dict[str, Any]:
    row = {col: "" for col in columns}
    numeric_defaults = {
        "ln_x2": 0.0,
        "T_m": 0.0,
        "dH_fus": 0.0,
        "hansen_d": 0.0,
        "hansen_p": 0.0,
        "hansen_h": 0.0,
        "ln_gamma_inf": 0.0,
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


def _build_aux_rows(idac: pd.DataFrame, columns: list[str], source_label: str) -> pd.DataFrame:
    template = _empty_row_template(columns)
    rows: list[dict[str, Any]] = []
    for record in idac.itertuples(index=False):
        row = dict(template)
        row["solute_smiles"] = str(record.solute_smiles)
        row["solvent_smiles"] = str(record.solvent_smiles)
        row["temperature"] = float(record.temperature)
        row["ln_gamma_inf"] = float(record.ln_gamma_inf)
        if "source" in row:
            row["source"] = source_label
        if "has_gamma_inf" in row:
            row["has_gamma_inf"] = True
        if "has_solubility" in row:
            row["has_solubility"] = False
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def _split_summary(path: Path) -> dict[str, Any]:
    df = pd.read_csv(path, low_memory=False)
    supervised = (
        _bool_series(df["has_solubility"])
        if "has_solubility" in df.columns
        else pd.Series(True, index=df.index)
    )
    gamma = (
        _bool_series(df["has_gamma_inf"])
        if "has_gamma_inf" in df.columns
        else pd.Series(False, index=df.index)
    )
    return {
        "path": str(path),
        "n_rows": int(len(df)),
        "n_supervised_rows": int(supervised.sum()),
        "n_gamma_rows": int(gamma.sum()),
        "n_aux_only_gamma_rows": int((gamma & ~supervised).sum()),
        "n_solutes": int(df["solute_smiles"].nunique()) if "solute_smiles" in df.columns else 0,
        "n_solvents": int(df["solvent_smiles"].nunique()) if "solvent_smiles" in df.columns else 0,
    }


def main() -> None:
    args = parse_args()
    processed_dir = Path(args.processed_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    idac = _load_idac(Path(args.idac_csv))
    idac_key_df = _gamma_key_frame(idac, temperature_decimals=args.temperature_decimals)
    idac = idac.loc[idac_key_df.dropna().index].copy().reset_index(drop=True)

    summary: dict[str, Any] = {
        "processed_dir": str(processed_dir),
        "idac_csv": str(Path(args.idac_csv)),
        "output_dir": str(output_dir),
        "idac_input_rows": int(len(idac)),
        "split_results": {},
    }

    manifest_path = processed_dir / "split_manifest.json"
    if manifest_path.is_file():
        (output_dir / "split_manifest.json").write_text(
            manifest_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    for split_name, (train_name, val_name, test_name) in SPLIT_TRIPLETS.items():
        train_path = processed_dir / train_name
        val_path = processed_dir / val_name
        test_path = processed_dir / test_name
        if not train_path.is_file() or not val_path.is_file() or not test_path.is_file():
            continue

        train = pd.read_csv(train_path, low_memory=False)
        val = pd.read_csv(val_path, low_memory=False)
        test = pd.read_csv(test_path, low_memory=False)
        columns = list(train.columns)

        existing_gamma = pd.concat([train, val, test], ignore_index=True)
        if "has_gamma_inf" in existing_gamma.columns:
            existing_gamma = existing_gamma.loc[_bool_series(existing_gamma["has_gamma_inf"])].copy()
        else:
            existing_gamma = existing_gamma.iloc[0:0].copy()
        existing_keys = _key_set(
            existing_gamma,
            temperature_decimals=args.temperature_decimals,
        )

        idac_keys = _gamma_key_frame(idac, temperature_decimals=args.temperature_decimals)
        is_new = [
            key not in existing_keys
            for key in idac_keys.itertuples(index=False, name=None)
        ]
        aux_input = idac.loc[is_new].copy().reset_index(drop=True)
        aux_rows = _build_aux_rows(aux_input, columns, args.source_label)
        train_out = pd.concat([train, aux_rows], ignore_index=True)

        train_out.to_csv(output_dir / train_name, index=False)
        val.to_csv(output_dir / val_name, index=False)
        test.to_csv(output_dir / test_name, index=False)

        summary["split_results"][split_name] = {
            "input": {
                "train": _split_summary(train_path),
                "val": _split_summary(val_path),
                "test": _split_summary(test_path),
            },
            "output": {
                "train": _split_summary(output_dir / train_name),
                "val": _split_summary(output_dir / val_name),
                "test": _split_summary(output_dir / test_name),
            },
            "n_existing_gamma_keys": int(len(existing_keys)),
            "n_new_idac_aux_rows_added_to_train": int(len(aux_rows)),
            "n_idac_rows_skipped_as_existing_gamma": int(len(idac) - len(aux_rows)),
        }

    (output_dir / "idac_aux_attachment_summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary), indent=2))


if __name__ == "__main__":
    main()
