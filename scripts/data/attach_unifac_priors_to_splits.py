#!/usr/bin/env python3
"""Attach precomputed Modified-UNIFAC gamma_inf priors to processed splits."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
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


DEFAULT_SPLIT_FILES = [
    "train.csv",
    "val.csv",
    "test.csv",
    "train_solute.csv",
    "val_solute.csv",
    "test_solute.csv",
    "train_solvent.csv",
    "val_solvent.csv",
    "test_solvent.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy processed split CSVs and add unifac_ln_gamma_inf / "
            "has_unifac_gamma_inf columns for the optional NRTL UNIFAC prior."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--processed-dir", default="notebooks/data/processed")
    parser.add_argument(
        "--output-dir",
        default="notebooks/data/processed_unifac_priors",
    )
    parser.add_argument(
        "--split-files",
        default=",".join(DEFAULT_SPLIT_FILES),
        help="Comma-separated split files to process.",
    )
    parser.add_argument("--temperature-decimals", type=int, default=3)
    parser.add_argument(
        "--max-rows-per-file",
        type=int,
        default=0,
        help="Debug cap. Rows beyond the cap are copied with has_unifac_gamma_inf=False.",
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


def _key_frame(df: pd.DataFrame, *, temperature_decimals: int) -> pd.DataFrame:
    return (
        df[["solute_smiles", "solvent_smiles", "temperature"]]
        .copy()
        .assign(
            solute_smiles=lambda x: x["solute_smiles"].astype(str),
            solvent_smiles=lambda x: x["solvent_smiles"].astype(str),
            temperature=lambda x: pd.to_numeric(
                x["temperature"], errors="coerce"
            ).round(int(temperature_decimals)),
        )
    )


def main() -> None:
    args = parse_args()
    processed_dir = Path(args.processed_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    split_files = [name.strip() for name in args.split_files.split(",") if name.strip()]

    cache: dict[tuple[str, str, float], float | None] = {}
    summary: dict[str, Any] = {
        "processed_dir": processed_dir,
        "output_dir": output_dir,
        "temperature_decimals": int(args.temperature_decimals),
        "split_files": {},
    }

    manifest = processed_dir / "split_manifest.json"
    if manifest.is_file():
        shutil.copy2(manifest, output_dir / "split_manifest.json")

    for name in split_files:
        in_path = processed_dir / name
        if not in_path.is_file():
            continue
        out_path = output_dir / name
        df = pd.read_csv(in_path, low_memory=False).copy()
        df["unifac_ln_gamma_inf"] = 0.0
        df["has_unifac_gamma_inf"] = False

        work_idx = df.index
        if args.max_rows_per_file > 0:
            work_idx = df.index[: int(args.max_rows_per_file)]

        keys = _key_frame(
            df.loc[work_idx],
            temperature_decimals=int(args.temperature_decimals),
        )
        unique_keys = keys.dropna().drop_duplicates()

        for record in tqdm(
            unique_keys.itertuples(index=False),
            total=len(unique_keys),
            desc=f"UNIFAC priors {name}",
        ):
            key = (
                str(record.solute_smiles),
                str(record.solvent_smiles),
                float(record.temperature),
            )
            if key not in cache:
                cache[key] = modified_unifac_lngamma_inf(
                    key[0],
                    key[1],
                    key[2],
                    temperature_decimals=int(args.temperature_decimals),
                )

        row_keys = _key_frame(
            df.loc[work_idx],
            temperature_decimals=int(args.temperature_decimals),
        )
        values = []
        masks = []
        for record in row_keys.itertuples(index=False):
            key = (
                str(record.solute_smiles),
                str(record.solvent_smiles),
                float(record.temperature),
            )
            value = cache.get(key)
            values.append(float(value) if value is not None else 0.0)
            masks.append(value is not None)
        df.loc[work_idx, "unifac_ln_gamma_inf"] = values
        df.loc[work_idx, "has_unifac_gamma_inf"] = masks
        df.to_csv(out_path, index=False)

        summary["split_files"][name] = {
            "input": in_path,
            "output": out_path,
            "n_rows": int(len(df)),
            "n_rows_considered": int(len(work_idx)),
            "n_unique_keys_considered": int(len(unique_keys)),
            "n_unifac_rows": int(df["has_unifac_gamma_inf"].sum()),
            "coverage_considered": float(
                df.loc[work_idx, "has_unifac_gamma_inf"].mean()
            )
            if len(work_idx)
            else 0.0,
        }

    summary["n_cached_unifac_keys"] = int(len(cache))
    summary["n_cached_success"] = int(sum(v is not None for v in cache.values()))
    (output_dir / "unifac_prior_summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
