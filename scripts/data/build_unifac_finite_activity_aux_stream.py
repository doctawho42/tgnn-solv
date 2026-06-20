#!/usr/bin/env python3
"""Build a standalone Modified-UNIFAC finite-activity auxiliary stream.

The output mirrors the loose CSV contract used by processed TGNN data so it can
be passed to `scripts/training/train.py --idac-train-data`. Unlike the existing
IDAC auxiliary stream, these rows supervise finite-composition `ln(gamma_2)` at
explicit activity states via `activity_x2`.
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

from tgnn_solv.unifac import modified_unifac_lngamma_binary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a standalone Modified-UNIFAC finite-activity auxiliary CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-csv",
        default="notebooks/data/processed/train.csv",
        help="Processed SLE CSV whose pair/temperature states should receive UNIFAC finite-activity pseudo labels.",
    )
    parser.add_argument(
        "--template-csv",
        default=None,
        help="Processed CSV whose columns should be mirrored. Defaults to --input-csv.",
    )
    parser.add_argument(
        "--output-csv",
        default="notebooks/data/processed_unifac_finite_activity_aux_stream/gamma2_aux_train.csv",
        help="Output standalone finite-activity auxiliary stream.",
    )
    parser.add_argument(
        "--summary-json",
        default="notebooks/data/processed_unifac_finite_activity_aux_stream/summary.json",
        help="Output summary JSON.",
    )
    parser.add_argument("--source-label", default="aux_only_gamma2_unifac_modified")
    parser.add_argument("--gamma2-weight", type=float, default=0.15)
    parser.add_argument("--temperature-decimals", type=int, default=3)
    parser.add_argument("--composition-decimals", type=int, default=6)
    parser.add_argument(
        "--composition-grid",
        default="",
        help=(
            "Optional comma-separated x2 grid. When omitted, use the observed "
            "solubility row composition x2=exp(ln_x2) for each supervised row."
        ),
    )
    parser.add_argument(
        "--allow-approximate-fallback",
        action="store_true",
        help=(
            "Allow low-cost SMILES standardization fallbacks when exact DDBST "
            "group lookup fails: no stereo, largest fragment, neutralized form."
        ),
    )
    parser.add_argument("--max-input-rows", type=int, default=0)
    parser.add_argument("--max-states", type=int, default=0)
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


def _parse_grid(spec: str, *, decimals: int) -> list[float]:
    values: list[float] = []
    for chunk in str(spec).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        value = round(float(chunk), int(decimals))
        if not math.isfinite(value) or value <= 0.0 or value >= 1.0:
            raise ValueError(f"Invalid composition value {chunk!r}; expected 0 < x < 1.")
        values.append(value)
    return sorted(dict.fromkeys(values))


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


def _ensure_aux_columns(columns: list[str]) -> list[str]:
    out = list(columns)
    for col in ("ln_gamma_2", "activity_x2", "has_gamma_2", "gamma2_weight"):
        if col not in out:
            out.append(col)
    return out


def _load_states(
    path: Path,
    *,
    temperature_decimals: int,
    composition_decimals: int,
    composition_grid: list[float],
    max_input_rows: int,
    max_states: int,
) -> tuple[pd.DataFrame, str]:
    df = pd.read_csv(path, low_memory=False).copy()
    if max_input_rows > 0:
        df = df.head(int(max_input_rows)).copy()
    if "has_solubility" in df.columns:
        df = df.loc[_bool_series(df["has_solubility"])].copy()
    required = {"solute_smiles", "solvent_smiles", "temperature"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce").round(
        int(temperature_decimals)
    )
    df = df.dropna(subset=["solute_smiles", "solvent_smiles", "temperature"]).copy()
    for optional_col in ("solute_name", "solvent_name"):
        if optional_col not in df.columns:
            df[optional_col] = ""

    if composition_grid:
        states = df[
            ["solute_smiles", "solvent_smiles", "temperature", "solute_name", "solvent_name"]
        ].copy()
        states = states.drop_duplicates().reset_index(drop=True)
        rows: list[dict[str, Any]] = []
        for record in states.itertuples(index=False):
            for x2 in composition_grid:
                rows.append(
                    {
                        "solute_smiles": record.solute_smiles,
                        "solvent_smiles": record.solvent_smiles,
                        "temperature": float(record.temperature),
                        "activity_x2": round(float(x2), int(composition_decimals)),
                        "solute_name": getattr(record, "solute_name", ""),
                        "solvent_name": getattr(record, "solvent_name", ""),
                    }
                )
        state_df = pd.DataFrame(rows)
        state_mode = "grid"
    else:
        if "ln_x2" not in df.columns:
            raise ValueError(
                f"{path} must contain ln_x2 when --composition-grid is not provided"
            )
        df["ln_x2"] = pd.to_numeric(df["ln_x2"], errors="coerce")
        df = df.loc[np.isfinite(df["ln_x2"].to_numpy(dtype=float))].copy()
        df["activity_x2"] = np.exp(df["ln_x2"].to_numpy(dtype=float))
        df["activity_x2"] = df["activity_x2"].clip(1.0e-8, 1.0 - 1.0e-8)
        df["activity_x2"] = df["activity_x2"].round(int(composition_decimals))
        state_df = df[
            [
                "solute_smiles",
                "solvent_smiles",
                "temperature",
                "activity_x2",
                "solute_name",
                "solvent_name",
            ]
        ].copy()
        state_mode = "observed_x2"

    state_df = state_df.dropna(
        subset=["solute_smiles", "solvent_smiles", "temperature", "activity_x2"]
    ).copy()
    state_df = state_df.loc[
        (state_df["activity_x2"].astype(float) > 0.0)
        & (state_df["activity_x2"].astype(float) < 1.0)
    ].copy()
    state_df = state_df.drop_duplicates().reset_index(drop=True)
    if max_states > 0:
        state_df = state_df.head(int(max_states)).copy()
    return state_df, state_mode


def _make_aux_row(
    template: dict[str, Any],
    *,
    solute_smiles: str,
    solvent_smiles: str,
    temperature: float,
    activity_x2: float,
    ln_gamma_2: float,
    source: str,
    gamma2_weight: float,
    solute_name: str = "",
    solvent_name: str = "",
) -> dict[str, Any]:
    row = dict(template)
    row["solute_smiles"] = str(solute_smiles)
    row["solvent_smiles"] = str(solvent_smiles)
    row["temperature"] = float(temperature)
    row["activity_x2"] = float(activity_x2)
    row["ln_gamma_2"] = float(ln_gamma_2)
    row["gamma2_weight"] = float(gamma2_weight)
    if "source" in row:
        row["source"] = source
    if "solute_name" in row and solute_name:
        row["solute_name"] = str(solute_name)
    if "solvent_name" in row and solvent_name:
        row["solvent_name"] = str(solvent_name)
    if "has_gamma_2" in row:
        row["has_gamma_2"] = True
    if "has_solubility" in row:
        row["has_solubility"] = False
    return row


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_csv)
    template_path = Path(args.template_csv or args.input_csv)
    output_path = Path(args.output_csv)
    summary_path = Path(args.summary_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    composition_grid = _parse_grid(
        args.composition_grid,
        decimals=int(args.composition_decimals),
    )
    states, state_mode = _load_states(
        input_path,
        temperature_decimals=int(args.temperature_decimals),
        composition_decimals=int(args.composition_decimals),
        composition_grid=composition_grid,
        max_input_rows=int(args.max_input_rows),
        max_states=int(args.max_states),
    )

    template_df = pd.read_csv(template_path, nrows=1, low_memory=False)
    columns = _ensure_aux_columns(list(template_df.columns))
    template = _template_row(columns)

    rows: list[dict[str, Any]] = []
    n_eval_failures = 0
    for record in tqdm(
        states.itertuples(index=False),
        total=len(states),
        desc="Modified UNIFAC finite-activity aux",
    ):
        lng = modified_unifac_lngamma_binary(
            str(record.solute_smiles),
            str(record.solvent_smiles),
            float(record.temperature),
            float(record.activity_x2),
            temperature_decimals=int(args.temperature_decimals),
            composition_decimals=int(args.composition_decimals),
            allow_approximate_fallback=bool(args.allow_approximate_fallback),
        )
        if lng is None:
            n_eval_failures += 1
            continue
        rows.append(
            _make_aux_row(
                template,
                solute_smiles=str(record.solute_smiles),
                solvent_smiles=str(record.solvent_smiles),
                temperature=float(record.temperature),
                activity_x2=float(record.activity_x2),
                ln_gamma_2=float(lng),
                source=str(args.source_label),
                gamma2_weight=float(args.gamma2_weight),
                solute_name=str(getattr(record, "solute_name", "") or ""),
                solvent_name=str(getattr(record, "solvent_name", "") or ""),
            )
        )

    aux = pd.DataFrame(rows, columns=columns)
    aux.to_csv(output_path, index=False)

    n_target_states = int(len(states))
    n_generated_states = int(len(aux))
    n_covered_pairs = (
        int(aux[["solute_smiles", "solvent_smiles"]].drop_duplicates().shape[0])
        if not aux.empty
        else 0
    )
    n_target_pairs = (
        int(states[["solute_smiles", "solvent_smiles"]].drop_duplicates().shape[0])
        if not states.empty
        else 0
    )
    summary = {
        "input_csv": str(input_path),
        "template_csv": str(template_path),
        "output_csv": str(output_path),
        "state_mode": state_mode,
        "allow_approximate_fallback": bool(args.allow_approximate_fallback),
        "gamma2_weight": float(args.gamma2_weight),
        "composition_grid": composition_grid,
        "n_target_pairs": n_target_pairs,
        "n_target_states": n_target_states,
        "n_generated_states": n_generated_states,
        "n_covered_pairs": n_covered_pairs,
        "state_coverage_fraction": float(n_generated_states / max(n_target_states, 1)),
        "pair_coverage_fraction": float(n_covered_pairs / max(n_target_pairs, 1)),
        "n_eval_failures": int(n_eval_failures),
    }
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
