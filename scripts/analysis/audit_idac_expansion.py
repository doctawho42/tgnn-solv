#!/usr/bin/env python3
"""Audit and consolidate expanded IDAC data for TGNN-Solv.

The maintained training path reads a local IDAC CSV via `load_idac()`. This
script keeps the original starter file intact and writes two explicit expanded
artifacts:

- raw exact-deduplicated rows with provenance
- training-safe rows aggregated by `(solute_smiles, solvent_smiles, temperature)`

It also reports coverage against the current processed solubility splits.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: E402,F401


REQUIRED_BASE_COLUMNS = ("solute_smiles", "solvent_smiles", "temperature")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge starter and newly extracted NIST ThermoML IDAC CSV files, "
            "aggregate duplicate pair-temperature rows, and compute coverage "
            "against the processed TGNN-Solv corpus."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--starter-idac",
        default="notebooks/data/raw/idac.csv",
        help="Existing curated/starter IDAC CSV.",
    )
    parser.add_argument(
        "--extracted-idac",
        action="append",
        default=None,
        help=(
            "New extracted IDAC CSV. Can be repeated. Defaults to "
            "notebooks/data/raw/idac_nist_2015_2019.csv when present."
        ),
    )
    parser.add_argument(
        "--processed-dir",
        default="notebooks/data/processed",
        help="Directory with train.csv / val.csv / test.csv for coverage audit.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/idac_expansion_audit",
        help="Output directory for audit sidecars.",
    )
    parser.add_argument(
        "--raw-output",
        default="notebooks/data/raw/idac_expanded_raw.csv",
        help="Exact-deduplicated raw expanded IDAC output.",
    )
    parser.add_argument(
        "--training-output",
        default="notebooks/data/raw/idac_expanded.csv",
        help="Training-safe aggregated IDAC output.",
    )
    parser.add_argument(
        "--temperature-decimals",
        type=int,
        default=3,
        help="Temperature rounding used when grouping duplicate IDAC records.",
    )
    parser.add_argument(
        "--conflict-threshold-ln-gamma",
        type=float,
        default=0.5,
        help="Group std threshold for flagging conflicting ln(gamma_inf) rows.",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip PNG/PDF figure generation.",
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


def _default_extracted_paths() -> list[Path]:
    candidates = [
        Path("notebooks/data/raw/idac_nist_2015_2019.csv"),
        Path("results/idac_thermoml_smoke/idac_current_pages_max80.csv"),
    ]
    return [path for path in candidates if path.is_file()]


def _load_idac_csv(path: Path, label: str) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False).copy()
    missing = [col for col in REQUIRED_BASE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")

    if "ln_gamma_inf" not in df.columns:
        if "gamma_inf" not in df.columns:
            raise ValueError(f"{path} must contain either ln_gamma_inf or gamma_inf")
        gamma = pd.to_numeric(df["gamma_inf"], errors="coerce")
        df["ln_gamma_inf"] = np.log(gamma.where(gamma > 0))

    df["solute_smiles"] = df["solute_smiles"].astype(str).str.strip()
    df["solvent_smiles"] = df["solvent_smiles"].astype(str).str.strip()
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["ln_gamma_inf"] = pd.to_numeric(df["ln_gamma_inf"], errors="coerce")
    if "gamma_inf" in df.columns:
        df["gamma_inf"] = pd.to_numeric(df["gamma_inf"], errors="coerce")
    else:
        df["gamma_inf"] = np.exp(df["ln_gamma_inf"])

    df["idac_source_file"] = str(path)
    df["idac_source_label"] = label
    before = len(df)
    df = df.dropna(subset=[
        "solute_smiles",
        "solvent_smiles",
        "temperature",
        "ln_gamma_inf",
    ]).copy()
    finite = (
        np.isfinite(df["temperature"].to_numpy(dtype=float))
        & np.isfinite(df["ln_gamma_inf"].to_numpy(dtype=float))
    )
    df = df.loc[finite].copy()
    df = df.loc[
        df["solute_smiles"].astype(bool) & df["solvent_smiles"].astype(bool)
    ].copy()
    df["dropped_rows_from_file"] = before - len(df)
    return df.reset_index(drop=True)


def _read_all_inputs(starter: Path, extracted: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    starter_df = pd.DataFrame()
    if starter.is_file():
        starter_df = _load_idac_csv(starter, "starter")
        frames.append(starter_df)
    for path in extracted:
        if path.is_file():
            frames.append(_load_idac_csv(path, "nist_extracted"))
    if not frames:
        raise FileNotFoundError("No IDAC input files were found.")
    return pd.concat(frames, ignore_index=True), starter_df


def _exact_deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    subset = [
        col for col in (
            "doi",
            "dataset_number",
            "solute_smiles",
            "solvent_smiles",
            "temperature",
            "gamma_inf",
            "ln_gamma_inf",
        )
        if col in df.columns
    ]
    return df.drop_duplicates(subset=subset, keep="first").reset_index(drop=True)


def _join_values(values: pd.Series, limit: int = 20) -> str:
    clean = [str(v) for v in values.dropna().astype(str).unique() if str(v)]
    clean = sorted(clean)
    if len(clean) > limit:
        return "|".join(clean[:limit]) + f"|...(+{len(clean) - limit})"
    return "|".join(clean)


def _aggregate_for_training(
    df: pd.DataFrame,
    *,
    temperature_decimals: int,
    conflict_threshold: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = df.copy()
    work["temperature_group"] = work["temperature"].round(temperature_decimals)
    group_cols = ["solute_smiles", "solvent_smiles", "temperature_group"]

    grouped = work.groupby(group_cols, dropna=False, sort=False)
    training = grouped.agg(
        temperature=("temperature", "median"),
        ln_gamma_inf=("ln_gamma_inf", "median"),
        ln_gamma_inf_mean=("ln_gamma_inf", "mean"),
        idac_ln_gamma_std=("ln_gamma_inf", "std"),
        idac_ln_gamma_min=("ln_gamma_inf", "min"),
        idac_ln_gamma_max=("ln_gamma_inf", "max"),
        n_idac_records=("ln_gamma_inf", "size"),
        n_idac_dois=("doi", lambda x: int(x.dropna().astype(str).nunique()) if "doi" in work.columns else 0),
        idac_source_dois=("doi", _join_values if "doi" in work.columns else lambda x: ""),
        idac_source_files=("idac_source_file", _join_values),
        idac_source_labels=("idac_source_label", _join_values),
    ).reset_index()
    training = training.drop(columns=["temperature_group"])
    training["idac_ln_gamma_std"] = training["idac_ln_gamma_std"].fillna(0.0)
    training["gamma_inf"] = np.exp(training["ln_gamma_inf"])
    training["has_idac_conflict"] = (
        training["idac_ln_gamma_std"].to_numpy(dtype=float) >= conflict_threshold
    )
    training = training[
        [
            "solute_smiles",
            "solvent_smiles",
            "temperature",
            "gamma_inf",
            "ln_gamma_inf",
            "ln_gamma_inf_mean",
            "idac_ln_gamma_std",
            "idac_ln_gamma_min",
            "idac_ln_gamma_max",
            "n_idac_records",
            "n_idac_dois",
            "has_idac_conflict",
            "idac_source_dois",
            "idac_source_files",
            "idac_source_labels",
        ]
    ].sort_values(
        ["solute_smiles", "solvent_smiles", "temperature"],
        kind="stable",
    ).reset_index(drop=True)

    conflicts = training.loc[training["has_idac_conflict"]].sort_values(
        ["idac_ln_gamma_std", "n_idac_records"],
        ascending=[False, False],
        kind="stable",
    )
    return training, conflicts


def _basic_stats(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "n_rows": 0,
            "n_pairs": 0,
            "n_solutes": 0,
            "n_solvents": 0,
            "n_dois": 0,
        }
    stats = {
        "n_rows": int(len(df)),
        "n_pairs": int(df[["solute_smiles", "solvent_smiles"]].drop_duplicates().shape[0]),
        "n_solutes": int(df["solute_smiles"].nunique()),
        "n_solvents": int(df["solvent_smiles"].nunique()),
        "temperature_min": float(df["temperature"].min()),
        "temperature_max": float(df["temperature"].max()),
        "ln_gamma_inf_min": float(df["ln_gamma_inf"].min()),
        "ln_gamma_inf_max": float(df["ln_gamma_inf"].max()),
        "ln_gamma_inf_median": float(df["ln_gamma_inf"].median()),
    }
    if "doi" in df.columns:
        stats["n_dois"] = int(df["doi"].dropna().astype(str).nunique())
    else:
        stats["n_dois"] = 0
    for col in ["journal", "year", "method", "standard_state", "idac_source_label"]:
        if col in df.columns:
            stats[f"{col}_top"] = (
                df[col].dropna().astype(str).value_counts().head(10).to_dict()
            )
    return stats


def _load_processed_splits(processed_dir: Path) -> pd.DataFrame:
    frames = []
    for split in ["train", "val", "test"]:
        path = processed_dir / f"{split}.csv"
        if not path.is_file():
            continue
        df = pd.read_csv(path, low_memory=False)
        df["split"] = split
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    if "has_solubility" in out.columns:
        mask = out["has_solubility"].astype(str).str.lower().isin(["true", "1", "yes"])
        out = out.loc[mask].copy()
    out = out.dropna(subset=["solute_smiles", "solvent_smiles"]).copy()
    out["pair_key"] = out["solute_smiles"].astype(str) + ">>" + out["solvent_smiles"].astype(str)
    return out.reset_index(drop=True)


def _coverage_against_processed(idac: pd.DataFrame, processed: pd.DataFrame) -> dict[str, Any]:
    if processed.empty:
        return {"available": False}

    idac_pairs = set(
        zip(idac["solute_smiles"].astype(str), idac["solvent_smiles"].astype(str))
    )
    idac_solutes = set(idac["solute_smiles"].astype(str))
    idac_solvents = set(idac["solvent_smiles"].astype(str))

    rows: list[dict[str, Any]] = []
    for split, grp in processed.groupby("split", sort=False):
        pairs = set(zip(grp["solute_smiles"].astype(str), grp["solvent_smiles"].astype(str)))
        solutes = set(grp["solute_smiles"].astype(str))
        solvents = set(grp["solvent_smiles"].astype(str))
        exact_pair_mask = [
            (s, v) in idac_pairs
            for s, v in zip(grp["solute_smiles"].astype(str), grp["solvent_smiles"].astype(str))
        ]
        component_mask = [
            (s in idac_solutes) and (v in idac_solvents)
            for s, v in zip(grp["solute_smiles"].astype(str), grp["solvent_smiles"].astype(str))
        ]
        rows.append(
            {
                "split": split,
                "n_rows": int(len(grp)),
                "n_pairs": int(len(pairs)),
                "n_solutes": int(len(solutes)),
                "n_solvents": int(len(solvents)),
                "exact_pair_rows": int(np.sum(exact_pair_mask)),
                "exact_pair_row_fraction": float(np.mean(exact_pair_mask)) if len(grp) else 0.0,
                "component_seen_rows": int(np.sum(component_mask)),
                "component_seen_row_fraction": float(np.mean(component_mask)) if len(grp) else 0.0,
                "pair_overlap_fraction": len(pairs & idac_pairs) / len(pairs) if pairs else 0.0,
                "solute_overlap_fraction": len(solutes & idac_solutes) / len(solutes) if solutes else 0.0,
                "solvent_overlap_fraction": len(solvents & idac_solvents) / len(solvents) if solvents else 0.0,
            }
        )

    combined_pairs = set(
        zip(processed["solute_smiles"].astype(str), processed["solvent_smiles"].astype(str))
    )
    combined_solutes = set(processed["solute_smiles"].astype(str))
    combined_solvents = set(processed["solvent_smiles"].astype(str))
    return {
        "available": True,
        "by_split": rows,
        "overall": {
            "n_rows": int(len(processed)),
            "n_pairs": int(len(combined_pairs)),
            "n_solutes": int(len(combined_solutes)),
            "n_solvents": int(len(combined_solvents)),
            "idac_pair_overlap_fraction": (
                len(combined_pairs & idac_pairs) / len(combined_pairs)
                if combined_pairs else 0.0
            ),
            "idac_solute_overlap_fraction": (
                len(combined_solutes & idac_solutes) / len(combined_solutes)
                if combined_solutes else 0.0
            ),
            "idac_solvent_overlap_fraction": (
                len(combined_solvents & idac_solvents) / len(combined_solvents)
                if combined_solvents else 0.0
            ),
            "n_idac_pairs_not_in_sle": int(len(idac_pairs - combined_pairs)),
        },
    }


def _write_figures(raw_df: pd.DataFrame, training_df: pd.DataFrame, out_dir: Path) -> list[str]:
    figure_dir = out_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.hist(training_df["ln_gamma_inf"].to_numpy(dtype=float), bins=80, color="#2563eb", alpha=0.82)
    ax.set_xlabel("ln(gamma_inf)")
    ax.set_ylabel("pair-temperature rows")
    ax.set_title("Expanded IDAC distribution")
    ax.grid(axis="y", color="#d4d4d4", alpha=0.65)
    for suffix in ["png", "pdf"]:
        path = figure_dir / f"idac_ln_gamma_distribution.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        written.append(str(path))
    plt.close(fig)

    if "year" in raw_df.columns:
        counts = raw_df["year"].dropna().astype(str).value_counts().sort_index()
        if not counts.empty:
            fig, ax = plt.subplots(figsize=(7.0, 4.2))
            ax.bar(counts.index, counts.values, color="#4d7c0f")
            ax.set_xlabel("year")
            ax.set_ylabel("raw IDAC rows")
            ax.set_title("Expanded IDAC rows by publication year")
            ax.grid(axis="y", color="#d4d4d4", alpha=0.65)
            for suffix in ["png", "pdf"]:
                path = figure_dir / f"idac_rows_by_year.{suffix}"
                fig.savefig(path, dpi=220, bbox_inches="tight")
                written.append(str(path))
            plt.close(fig)

    if "method" in raw_df.columns:
        counts = raw_df["method"].fillna("unknown").astype(str).value_counts().head(12)
        fig, ax = plt.subplots(figsize=(8.5, 4.5))
        ax.barh(counts.index[::-1], counts.values[::-1], color="#d97706")
        ax.set_xlabel("raw IDAC rows")
        ax.set_title("Expanded IDAC rows by ThermoML method")
        ax.grid(axis="x", color="#d4d4d4", alpha=0.65)
        for suffix in ["png", "pdf"]:
            path = figure_dir / f"idac_rows_by_method.{suffix}"
            fig.savefig(path, dpi=220, bbox_inches="tight")
            written.append(str(path))
        plt.close(fig)

    return written


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_output = Path(args.raw_output)
    training_output = Path(args.training_output)
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    training_output.parent.mkdir(parents=True, exist_ok=True)

    extracted_paths = (
        [Path(p) for p in args.extracted_idac]
        if args.extracted_idac
        else _default_extracted_paths()
    )
    all_raw, starter_df = _read_all_inputs(Path(args.starter_idac), extracted_paths)
    exact_raw = _exact_deduplicate(all_raw)
    training_df, conflicts_df = _aggregate_for_training(
        exact_raw,
        temperature_decimals=args.temperature_decimals,
        conflict_threshold=args.conflict_threshold_ln_gamma,
    )

    exact_raw.to_csv(raw_output, index=False)
    training_df.to_csv(training_output, index=False)
    conflicts_df.to_csv(out_dir / "idac_conflicting_pair_temperatures.csv", index=False)

    processed = _load_processed_splits(Path(args.processed_dir))
    coverage = _coverage_against_processed(training_df, processed)
    if coverage.get("available"):
        pd.DataFrame(coverage["by_split"]).to_csv(out_dir / "coverage_by_split.csv", index=False)

    top_dois = (
        exact_raw["doi"].dropna().astype(str).value_counts().head(50)
        .rename_axis("doi").reset_index(name="n_rows")
        if "doi" in exact_raw.columns else pd.DataFrame()
    )
    top_dois.to_csv(out_dir / "top_idac_dois.csv", index=False)

    summary = {
        "inputs": {
            "starter_idac": str(Path(args.starter_idac)),
            "extracted_idac": [str(p) for p in extracted_paths],
        },
        "outputs": {
            "raw_output": str(raw_output),
            "training_output": str(training_output),
            "out_dir": str(out_dir),
        },
        "starter_stats": _basic_stats(starter_df),
        "raw_exact_deduplicated_stats": _basic_stats(exact_raw),
        "training_aggregated_stats": _basic_stats(training_df),
        "aggregation": {
            "temperature_decimals": int(args.temperature_decimals),
            "n_pair_temperature_groups": int(len(training_df)),
            "n_groups_with_multiple_records": int((training_df["n_idac_records"] > 1).sum()),
            "n_conflicting_groups": int(len(conflicts_df)),
            "conflict_threshold_ln_gamma": float(args.conflict_threshold_ln_gamma),
            "max_group_ln_gamma_std": float(training_df["idac_ln_gamma_std"].max())
            if len(training_df) else None,
            "median_group_records": float(training_df["n_idac_records"].median())
            if len(training_df) else None,
            "p95_group_records": float(training_df["n_idac_records"].quantile(0.95))
            if len(training_df) else None,
        },
        "coverage": coverage,
        "figures": [] if args.no_figures else _write_figures(exact_raw, training_df, out_dir),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )

    print(json.dumps(_json_safe(summary), indent=2))


if __name__ == "__main__":
    main()
