#!/usr/bin/env python3
"""Build a standalone ORCA/openCOSMO-RS finite-activity auxiliary stream."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
from rdkit import Chem
from tqdm import tqdm

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parents[0]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tgnn_solv.chemistry.cosmors import ensure_orca_cosmo_file
from tgnn_solv.chemistry.cosmors import OpenCosmoBinarySystem


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-csv",
        default="notebooks/data/processed/train.csv",
        help="Processed SLE CSV whose pair/temperature states should receive COSMO-RS pseudo labels.",
    )
    parser.add_argument(
        "--template-csv",
        default=None,
        help="Processed CSV whose columns should be mirrored. Defaults to --input-csv.",
    )
    parser.add_argument(
        "--output-csv",
        default="notebooks/data/processed_cosmors_finite_activity_aux_stream/gamma2_aux_train.csv",
        help="Output standalone finite-activity auxiliary stream.",
    )
    parser.add_argument(
        "--summary-json",
        default="notebooks/data/processed_cosmors_finite_activity_aux_stream/summary.json",
        help="Output summary JSON.",
    )
    parser.add_argument(
        "--molecule-status-csv",
        default=None,
        help="Optional per-molecule status export. Defaults to <output-dir>/molecule_status.csv.",
    )
    parser.add_argument(
        "--evaluation-failures-csv",
        default=None,
        help="Optional per-state evaluation-failure export. Defaults to <output-dir>/evaluation_failures.csv.",
    )
    parser.add_argument(
        "--source-label",
        default="aux_only_gamma2_cosmors24a",
    )
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
        "--cache-dir",
        default="notebooks/data/processed_cosmors_finite_activity_aux_stream/cache",
        help="Directory for cached per-molecule ORCA/COSMO artifacts.",
    )
    parser.add_argument("--orca-bin", default=None, help="Path to ORCA binary.")
    parser.add_argument(
        "--mpi-lib",
        default=None,
        help="Path to libmpi.40.dylib if ORCA needs a local runtime symlink.",
    )
    parser.add_argument("--orca-nprocs", type=int, default=2)
    parser.add_argument("--orca-maxcore-mb", type=int, default=1000)
    parser.add_argument(
        "--keep-orca-workdirs",
        action="store_true",
        help="Keep raw ORCA intermediate files instead of trimming cache directories.",
    )
    parser.add_argument(
        "--force-recompute-molecules",
        action="store_true",
        help="Ignore cached per-molecule .orcacosmo files and rerun ORCA generation.",
    )
    parser.add_argument("--max-input-rows", type=int, default=0)
    parser.add_argument("--max-states", type=int, default=0)
    parser.add_argument("--max-molecules", type=int, default=0)
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


def _canonical_pair_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    keys = (
        df[["solute_smiles", "solvent_smiles"]]
        .astype(str)
        .agg(">>".join, axis=1)
        .drop_duplicates()
    )
    return int(len(keys))


def _formal_charge(smiles: str) -> int | None:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    return int(Chem.GetFormalCharge(mol))


def main() -> None:
    args = parse_args()

    input_path = Path(args.input_csv)
    template_path = Path(args.template_csv) if args.template_csv else input_path
    output_path = Path(args.output_csv)
    summary_path = Path(args.summary_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    molecule_status_path = (
        Path(args.molecule_status_csv)
        if args.molecule_status_csv
        else output_path.parent / "molecule_status.csv"
    )
    evaluation_failures_path = (
        Path(args.evaluation_failures_csv)
        if args.evaluation_failures_csv
        else output_path.parent / "evaluation_failures.csv"
    )
    molecule_status_path.parent.mkdir(parents=True, exist_ok=True)
    evaluation_failures_path.parent.mkdir(parents=True, exist_ok=True)

    composition_grid = _parse_grid(
        args.composition_grid,
        decimals=args.composition_decimals,
    )
    states_df, state_mode = _load_states(
        input_path,
        temperature_decimals=args.temperature_decimals,
        composition_decimals=args.composition_decimals,
        composition_grid=composition_grid,
        max_input_rows=args.max_input_rows,
        max_states=args.max_states,
    )
    template_df = pd.read_csv(template_path, nrows=1, low_memory=False)
    template_columns = _ensure_aux_columns(list(template_df.columns))
    template = _template_row(template_columns)

    unique_smiles: list[str] = []
    seen_smiles: set[str] = set()
    for col in ("solute_smiles", "solvent_smiles"):
        for smiles in states_df[col].astype(str):
            if smiles not in seen_smiles:
                unique_smiles.append(smiles)
                seen_smiles.add(smiles)
    if args.max_molecules > 0:
        unique_smiles = unique_smiles[: int(args.max_molecules)]

    molecule_status_rows: list[dict[str, Any]] = []
    cosmo_cache: dict[str, Path] = {}
    enabled_smiles = set(unique_smiles)
    for smiles in tqdm(unique_smiles, desc="ORCA self-COSMO cache"):
        record = {
            "smiles": smiles,
            "formal_charge": _formal_charge(smiles),
            "status": "ok",
            "cosmo_path": None,
            "message": "",
        }
        try:
            artifact = ensure_orca_cosmo_file(
                smiles,
                cache_dir=args.cache_dir,
                orca_bin=args.orca_bin,
                mpi_lib=args.mpi_lib,
                nprocs=args.orca_nprocs,
                maxcore_mb=args.orca_maxcore_mb,
                keep_workdir=args.keep_orca_workdirs,
                force=args.force_recompute_molecules,
            )
            cosmo_cache[smiles] = artifact.cosmo_path
            record["cosmo_path"] = str(artifact.cosmo_path)
        except Exception as exc:
            record["status"] = "failed"
            record["message"] = f"{type(exc).__name__}: {exc}"
        molecule_status_rows.append(record)

    molecule_status_df = pd.DataFrame(molecule_status_rows)
    molecule_status_df.to_csv(molecule_status_path, index=False)

    active_states = states_df.loc[
        states_df["solute_smiles"].astype(str).isin(cosmo_cache)
        & states_df["solvent_smiles"].astype(str).isin(cosmo_cache)
    ].copy()

    systems_cache: dict[tuple[str, str], OpenCosmoBinarySystem] = {}
    aux_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    for record in tqdm(active_states.itertuples(index=False), desc="COSMO-RS finite-activity aux"):
        solute = str(record.solute_smiles)
        solvent = str(record.solvent_smiles)
        temperature = float(record.temperature)
        activity_x2 = float(record.activity_x2)
        pair_key = (solute, solvent)
        try:
            if pair_key not in systems_cache:
                systems_cache[pair_key] = OpenCosmoBinarySystem(
                    cosmo_cache[solute],
                    cosmo_cache[solvent],
                )
            ln_gamma_2 = systems_cache[pair_key].ln_gamma_2(activity_x2, temperature)
            aux_rows.append(
                _make_aux_row(
                    template,
                    solute_smiles=solute,
                    solvent_smiles=solvent,
                    temperature=temperature,
                    activity_x2=activity_x2,
                    ln_gamma_2=ln_gamma_2,
                    source=args.source_label,
                    gamma2_weight=args.gamma2_weight,
                    solute_name=getattr(record, "solute_name", ""),
                    solvent_name=getattr(record, "solvent_name", ""),
                )
            )
        except Exception as exc:
            failure_rows.append(
                {
                    "solute_smiles": solute,
                    "solvent_smiles": solvent,
                    "temperature": temperature,
                    "activity_x2": activity_x2,
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )

    aux_df = pd.DataFrame(aux_rows, columns=template_columns)
    aux_df.to_csv(output_path, index=False)

    failure_df = pd.DataFrame(failure_rows)
    failure_df.to_csv(evaluation_failures_path, index=False)

    covered_pairs = _canonical_pair_count(aux_df)
    target_pairs = _canonical_pair_count(states_df)
    summary = {
        "input_csv": str(input_path),
        "template_csv": str(template_path),
        "output_csv": str(output_path),
        "summary_json": str(summary_path),
        "cache_dir": str(Path(args.cache_dir)),
        "molecule_status_csv": str(molecule_status_path),
        "evaluation_failures_csv": str(evaluation_failures_path),
        "source_label": args.source_label,
        "state_mode": state_mode,
        "composition_grid": composition_grid,
        "gamma2_weight": float(args.gamma2_weight),
        "orca_bin": args.orca_bin,
        "mpi_lib": args.mpi_lib,
        "orca_nprocs": int(args.orca_nprocs),
        "orca_maxcore_mb": int(args.orca_maxcore_mb),
        "n_target_states": int(len(states_df)),
        "n_generated_states": int(len(aux_df)),
        "state_coverage_fraction": (
            None if len(states_df) == 0 else float(len(aux_df) / len(states_df))
        ),
        "n_target_pairs": int(target_pairs),
        "n_covered_pairs": int(covered_pairs),
        "pair_coverage_fraction": (
            None if target_pairs == 0 else float(covered_pairs / target_pairs)
        ),
        "n_unique_molecules_requested": int(len(unique_smiles)),
        "n_unique_molecules_cached": int(len(cosmo_cache)),
        "n_molecule_failures": int((molecule_status_df["status"] != "ok").sum())
        if not molecule_status_df.empty
        else 0,
        "n_eval_failures": int(len(failure_df)),
    }
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary), indent=2))


if __name__ == "__main__":
    main()
