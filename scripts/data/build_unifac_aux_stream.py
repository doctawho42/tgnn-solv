#!/usr/bin/env python3
"""Build a standalone Modified-UNIFAC gamma_inf auxiliary stream.

The output has the same loose CSV contract as processed TGNN data and is meant
for `scripts/training/train.py --idac-train-data`. It does not append rows to
the supervised SLE split.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from tqdm import tqdm

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parents[0]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tgnn_solv.unifac import modified_unifac_lngamma_inf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a standalone Modified-UNIFAC pseudo-IDAC stream.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-csv",
        default="notebooks/data/processed/train.csv",
        help="Processed SLE CSV whose pair/temperature keys should receive UNIFAC pseudo-IDAC.",
    )
    parser.add_argument(
        "--template-csv",
        default=None,
        help="Processed CSV whose columns should be mirrored. Defaults to --input-csv.",
    )
    parser.add_argument(
        "--experimental-idac-csv",
        default="",
        help="Optional experimental IDAC CSV to prepend with higher gamma_weight.",
    )
    parser.add_argument(
        "--output-csv",
        default="notebooks/data/processed_unifac_aux_stream/gamma_aux_train.csv",
        help="Output standalone gamma_inf auxiliary stream.",
    )
    parser.add_argument(
        "--summary-json",
        default="notebooks/data/processed_unifac_aux_stream/summary.json",
        help="Output summary JSON.",
    )
    parser.add_argument("--source-label", default="aux_only_gamma_unifac_modified")
    parser.add_argument("--experimental-source-label", default="aux_only_gamma_experimental")
    parser.add_argument("--unifac-weight", type=float, default=0.15)
    parser.add_argument("--experimental-weight", type=float, default=1.0)
    parser.add_argument("--temperature-decimals", type=int, default=3)
    parser.add_argument("--max-input-rows", type=int, default=0)
    parser.add_argument("--max-pairs", type=int, default=0)
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
        "gamma_weight": 1.0,
        "has_solubility": False,
        "has_T_m": False,
        "has_dH_fus": False,
        "has_hansen": False,
        "has_gamma_inf": False,
        "fda_approved": "No",
    }
    for key, value in defaults.items():
        if key in row:
            row[key] = value
    return row


def _ensure_aux_columns(columns: list[str]) -> list[str]:
    out = list(columns)
    for col in ["gamma_weight"]:
        if col not in out:
            out.append(col)
    return out


def _make_aux_row(
    template: dict[str, Any],
    *,
    solute_smiles: str,
    solvent_smiles: str,
    temperature: float,
    ln_gamma_inf: float,
    source: str,
    gamma_weight: float,
) -> dict[str, Any]:
    row = dict(template)
    row["solute_smiles"] = str(solute_smiles)
    row["solvent_smiles"] = str(solvent_smiles)
    row["temperature"] = float(temperature)
    row["ln_gamma_inf"] = float(ln_gamma_inf)
    row["gamma_weight"] = float(gamma_weight)
    if "source" in row:
        row["source"] = source
    if "has_gamma_inf" in row:
        row["has_gamma_inf"] = True
    if "has_solubility" in row:
        row["has_solubility"] = False
    return row


def _read_experimental_idac(
    path: Path,
    *,
    temperature_decimals: int,
) -> pd.DataFrame:
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
    keep = df[["solute_smiles", "solvent_smiles", "temperature", "ln_gamma_inf"]].copy()
    keep["temperature"] = pd.to_numeric(keep["temperature"], errors="coerce").round(
        temperature_decimals
    )
    keep["ln_gamma_inf"] = pd.to_numeric(keep["ln_gamma_inf"], errors="coerce")
    keep = keep.dropna()
    finite = (
        np.isfinite(keep["temperature"].to_numpy(dtype=float))
        & np.isfinite(keep["ln_gamma_inf"].to_numpy(dtype=float))
    )
    keep = keep.loc[finite]
    return (
        keep.groupby(["solute_smiles", "solvent_smiles", "temperature"], as_index=False)
        .agg(ln_gamma_inf=("ln_gamma_inf", "mean"))
    )


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_csv)
    template_path = Path(args.template_csv or args.input_csv)
    output_path = Path(args.output_csv)
    summary_path = Path(args.summary_json)

    template_df = pd.read_csv(template_path, nrows=1, low_memory=False)
    columns = _ensure_aux_columns(list(template_df.columns))
    template = _template_row(columns)

    rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, float]] = set()

    n_experimental = 0
    if args.experimental_idac_csv:
        exp = _read_experimental_idac(
            Path(args.experimental_idac_csv),
            temperature_decimals=args.temperature_decimals,
        )
        for record in exp.itertuples(index=False):
            key = (
                str(record.solute_smiles),
                str(record.solvent_smiles),
                float(record.temperature),
            )
            seen_keys.add(key)
            rows.append(
                _make_aux_row(
                    template,
                    solute_smiles=key[0],
                    solvent_smiles=key[1],
                    temperature=key[2],
                    ln_gamma_inf=float(record.ln_gamma_inf),
                    source=args.experimental_source_label,
                    gamma_weight=float(args.experimental_weight),
                )
            )
        n_experimental = len(rows)

    sle = pd.read_csv(input_path, low_memory=False)
    if args.max_input_rows > 0:
        sle = sle.head(int(args.max_input_rows)).copy()
    if "has_solubility" in sle.columns:
        sle = sle.loc[_bool_series(sle["has_solubility"])].copy()
    keys = (
        sle[["solute_smiles", "solvent_smiles", "temperature"]]
        .dropna()
        .assign(
            temperature=lambda x: pd.to_numeric(
                x["temperature"], errors="coerce"
            ).round(int(args.temperature_decimals))
        )
        .dropna()
        .drop_duplicates()
    )
    if args.max_pairs > 0:
        keys = keys.head(int(args.max_pairs)).copy()

    n_attempted = 0
    n_missing = 0
    for record in tqdm(
        keys.itertuples(index=False),
        total=len(keys),
        desc="Modified UNIFAC pseudo-IDAC",
    ):
        key = (
            str(record.solute_smiles),
            str(record.solvent_smiles),
            float(record.temperature),
        )
        if key in seen_keys:
            continue
        n_attempted += 1
        lng = modified_unifac_lngamma_inf(
            key[0],
            key[1],
            key[2],
            temperature_decimals=int(args.temperature_decimals),
        )
        if lng is None:
            n_missing += 1
            continue
        seen_keys.add(key)
        rows.append(
            _make_aux_row(
                template,
                solute_smiles=key[0],
                solvent_smiles=key[1],
                temperature=key[2],
                ln_gamma_inf=float(lng),
                source=args.source_label,
                gamma_weight=float(args.unifac_weight),
            )
        )

    out = pd.DataFrame(rows, columns=columns)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)

    n_unifac = int((out["source"] == args.source_label).sum()) if "source" in out else len(out) - n_experimental
    summary = {
        "input_csv": input_path,
        "template_csv": template_path,
        "experimental_idac_csv": args.experimental_idac_csv or None,
        "output_csv": output_path,
        "appended_to_sle_splits": False,
        "n_rows": int(len(out)),
        "n_experimental_rows": int(n_experimental),
        "n_unifac_rows": n_unifac,
        "n_unifac_attempted": int(n_attempted),
        "n_unifac_missing": int(n_missing),
        "unifac_coverage": float(n_unifac / max(n_attempted, 1)),
        "unifac_weight": float(args.unifac_weight),
        "experimental_weight": float(args.experimental_weight),
        "n_pairs": int(out[["solute_smiles", "solvent_smiles"]].drop_duplicates().shape[0])
        if len(out)
        else 0,
    }
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
