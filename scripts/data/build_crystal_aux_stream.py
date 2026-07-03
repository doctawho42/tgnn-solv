#!/usr/bin/env python3
"""Build a standalone external crystal (T_m / dH_fus) auxiliary stream.

This grounds the crystal branch of the physics-informed model on a much larger
pool of *single-component* melting-point / fusion-enthalpy labels than the
solubility pairs themselves (the ``open_crystal_artifact``: ~19k T_m, ~495
dH_fus). It mirrors ``build_idac_aux_stream.py``: the output is a separate CSV
in processed-dataset format, consumed via

    python scripts/train.py ... \
        --crystal-train-data <output.csv> --crystal-steps-per-epoch 8

Each emitted row is a single-component crystal-label row: the solute is paired
with *itself* as the "solvent" so a valid solvent graph exists, but
``has_solubility=False`` and all activity masks are off, so only the T_m / dH_fus
losses fire (the trainer's ``_train_crystal_aux_batch`` enforces this too).

CRITICAL CORRECTNESS GUARD: to keep the scaffold-extrapolation evaluation honest,
pool solutes whose Bemis-Murcko scaffold appears in a held-out split (e.g. the
solubility TEST set) must be excluded via ``--exclude-scaffolds-from``.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tgnn_solv.data.utils import get_scaffold


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a standalone external crystal (T_m/dH_fus) auxiliary CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--crystal-csv",
        default="results/open_crystal_artifact/open_crystal_solute.csv",
        help="Per-solute crystal artifact with solute_smiles, T_m, dH_fus columns.",
    )
    parser.add_argument(
        "--template-csv",
        default="notebooks/data/processed/train.csv",
        help="Processed SLE CSV whose column contract should be mirrored.",
    )
    parser.add_argument(
        "--output-csv",
        default="notebooks/data/processed_crystal_aux_stream/crystal_train.csv",
        help="Standalone aux-only crystal stream CSV to write.",
    )
    parser.add_argument(
        "--summary-json",
        default="notebooks/data/processed_crystal_aux_stream/summary.json",
    )
    parser.add_argument(
        "--exclude-scaffolds-from",
        nargs="*",
        default=["notebooks/data/processed/test.csv", "notebooks/data/processed/val.csv"],
        help="Split CSV(s) whose solute Murcko scaffolds must be excluded from the pool "
        "(prevents scaffold leakage into the headline evaluation).",
    )
    parser.add_argument(
        "--source-label",
        default="aux_only_open_crystal_stream",
        help="Source label assigned to generated crystal rows.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=298.15,
        help="Nominal temperature for the rows (T_m/dH losses are T-independent).",
    )
    parser.add_argument(
        "--require-dH",
        action="store_true",
        help="If set, keep only solutes that also have a fusion enthalpy.",
    )
    parser.add_argument(
        "--allow-no-scaffold-exclusion",
        action="store_true",
        help="Override the fail-closed scaffold-leak guard. Only for pools that are "
        "intentionally NOT used in a scaffold-split evaluation; otherwise a missing "
        "or empty split CSV silently leaks held-out scaffolds into the pool.",
    )
    return parser.parse_args()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _excluded_scaffolds(paths: list[str], *, allow_missing: bool = False) -> set[str]:
    """Collect Murcko scaffolds to exclude. Fails CLOSED by default.

    A missing or empty/header-only split CSV would silently yield zero exclusions
    and emit the entire (non-split-aware) crystal pool, leaking held-out scaffolds
    into the headline scaffold-extrapolation evaluation. So unless ``allow_missing``
    is set, a requested path that does not exist or yields zero scaffolds raises.
    """
    scaffolds: set[str] = set()
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            if allow_missing:
                continue
            raise FileNotFoundError(
                f"--exclude-scaffolds-from path does not exist: {path}. Refusing to "
                "build the aux stream without the mandatory scaffold-leak guard "
                "(pass --allow-no-scaffold-exclusion to override deliberately)."
            )
        df = pd.read_csv(path, usecols=lambda c: c == "solute_smiles", low_memory=False)
        path_scaffolds = {
            scaf
            for smi in df["solute_smiles"].dropna().astype(str).unique()
            if (scaf := get_scaffold(smi))
        }
        if not path_scaffolds and not allow_missing:
            raise ValueError(
                f"{path} yielded zero usable solute scaffolds; refusing to proceed "
                "(an empty/header-only split would silently leak the full pool into "
                "the evaluation). Pass --allow-no-scaffold-exclusion to override."
            )
        scaffolds |= path_scaffolds
    return scaffolds


def _empty_row_template(columns: list[str], temperature: float) -> dict[str, Any]:
    row = {col: "" for col in columns}
    numeric_defaults = {
        "temperature": temperature,
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


def _load_crystal_pool(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if "solute_smiles" not in df.columns or "T_m" not in df.columns:
        raise ValueError(f"{path} must contain solute_smiles and T_m columns.")
    out = pd.DataFrame()
    out["solute_smiles"] = df["solute_smiles"].astype(str)
    out["T_m"] = pd.to_numeric(df["T_m"], errors="coerce")
    out["dH_fus"] = (
        pd.to_numeric(df["dH_fus"], errors="coerce")
        if "dH_fus" in df.columns
        else np.nan
    )
    out = out.dropna(subset=["solute_smiles", "T_m"])
    out = out[np.isfinite(out["T_m"].to_numpy(dtype=float))]
    out = out[out["solute_smiles"].str.len() > 0]
    out = out.drop_duplicates(subset=["solute_smiles"])
    return out


def build_stream(
    pool: pd.DataFrame,
    *,
    template_columns: list[str],
    source_label: str,
    temperature: float,
) -> pd.DataFrame:
    template = _empty_row_template(template_columns, temperature)
    rows: list[dict[str, Any]] = []
    for record in pool.itertuples(index=False):
        row = dict(template)
        smi = str(record.solute_smiles)
        row["solute_smiles"] = smi
        row["solvent_smiles"] = smi  # self-solvent: valid graph, no pair signal
        row["temperature"] = float(temperature)
        row["T_m"] = float(record.T_m)
        row["has_T_m"] = True
        dH = float(record.dH_fus) if record.dH_fus == record.dH_fus else float("nan")
        if math.isfinite(dH):
            row["dH_fus"] = dH
            row["has_dH_fus"] = True
        else:
            row["dH_fus"] = 0.0
            row["has_dH_fus"] = False
        if "source" in row:
            row["source"] = source_label
        if "has_solubility" in row:
            row["has_solubility"] = False
        rows.append(row)
    return pd.DataFrame(rows, columns=template_columns)


def main() -> None:
    args = parse_args()
    crystal_path = Path(args.crystal_csv)
    template_path = Path(args.template_csv)
    output_path = Path(args.output_csv)
    summary_path = Path(args.summary_json)

    template = pd.read_csv(template_path, nrows=1, low_memory=False)
    pool = _load_crystal_pool(crystal_path)
    n_raw = len(pool)

    requested_excludes = list(args.exclude_scaffolds_from or [])
    excluded_scaffolds = _excluded_scaffolds(
        requested_excludes, allow_missing=args.allow_no_scaffold_exclusion
    )
    if requested_excludes and not excluded_scaffolds and not args.allow_no_scaffold_exclusion:
        raise SystemExit(
            "Scaffold exclusion produced an empty set; aborting to prevent leakage "
            "of held-out scaffolds into the crystal aux pool."
        )
    if excluded_scaffolds:
        keep_mask = ~pool["solute_smiles"].map(
            lambda s: get_scaffold(s) in excluded_scaffolds
        )
        pool = pool[keep_mask].copy()
    n_after_scaffold = len(pool)

    if args.require_dH:
        pool = pool[np.isfinite(pool["dH_fus"].to_numpy(dtype=float))].copy()

    stream = build_stream(
        pool,
        template_columns=list(template.columns),
        source_label=args.source_label,
        temperature=args.temperature,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    stream.to_csv(output_path, index=False)

    n_dH = int(stream["has_dH_fus"].astype(bool).sum()) if "has_dH_fus" in stream else 0
    summary = {
        "crystal_csv": crystal_path,
        "template_csv": template_path,
        "output_csv": output_path,
        "source_label": args.source_label,
        "n_pool_raw": int(n_raw),
        "n_after_scaffold_exclusion": int(n_after_scaffold),
        "n_excluded_scaffolds": int(len(excluded_scaffolds)),
        "n_rows": int(len(stream)),
        "n_rows_with_dH_fus": n_dH,
        "exclude_scaffolds_from": list(args.exclude_scaffolds_from or []),
        "appended_to_sle_splits": False,
    }
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
