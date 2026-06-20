#!/usr/bin/env python3
"""Build an open crystal-property artifact with explicit source priority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterable

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parents[0]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tgnn_solv.data.sources import (
    load_bradley_melting_points,
    load_curated_fusion_enthalpies,
    load_curated_melting_points,
)

TM_PRIORITY = (
    ("curated_nist_webbook", "T_m_curated"),
    ("thermoml", "T_m_thermoml"),
    ("bradley", "T_m_bradley"),
)
DH_PRIORITY = (
    ("curated_nist_webbook", "dH_fus_curated"),
    ("thermoml", "dH_fus_thermoml"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an open crystal-property artifact with provenance.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--thermoml-aggregated",
        type=str,
        default="results/thermoml_crystal/thermoml_crystal_aggregated.csv",
        help="Aggregated ThermoML crystal CSV from extract_crystal_from_thermoml.py.",
    )
    parser.add_argument(
        "--processed-dir",
        type=str,
        default="notebooks/data/processed",
        help="Directory containing canonical train/val/test processed CSVs.",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="results/open_crystal_artifact",
        help="Output directory.",
    )
    return parser.parse_args()


def _select_from_priority(
    row: pd.Series,
    *,
    specs: Iterable[tuple[str, str]],
    value_name: str,
) -> pd.Series:
    available: list[tuple[int, str, float]] = []
    for rank, (source, column) in enumerate(specs, start=1):
        value = row.get(column)
        if pd.notna(value):
            available.append((rank, source, float(value)))

    prefix = value_name
    if not available:
        return pd.Series(
            {
                prefix: pd.NA,
                f"{prefix}_source": pd.NA,
                f"{prefix}_source_rank": pd.NA,
                f"{prefix}_n_sources": 0,
                f"{prefix}_available_sources": "",
                f"{prefix}_min_source_value": pd.NA,
                f"{prefix}_max_source_value": pd.NA,
                f"{prefix}_max_pairwise_delta": pd.NA,
            }
        )

    rank, source, value = available[0]
    all_values = [item[2] for item in available]
    return pd.Series(
        {
            prefix: value,
            f"{prefix}_source": source,
            f"{prefix}_source_rank": rank,
            f"{prefix}_n_sources": len(available),
            f"{prefix}_available_sources": ";".join(item[1] for item in available),
            f"{prefix}_min_source_value": min(all_values),
            f"{prefix}_max_source_value": max(all_values),
            f"{prefix}_max_pairwise_delta": max(all_values) - min(all_values),
        }
    )


def _pairwise_overlap_summary(
    frame: pd.DataFrame,
    *,
    left_name: str,
    left_column: str,
    right_name: str,
    right_column: str,
) -> dict[str, object]:
    overlap = frame.loc[frame[left_column].notna() & frame[right_column].notna()].copy()
    if overlap.empty:
        return {
            "left": left_name,
            "right": right_name,
            "n_overlap": 0,
        }
    delta = (overlap[left_column] - overlap[right_column]).abs()
    return {
        "left": left_name,
        "right": right_name,
        "n_overlap": int(len(overlap)),
        "median_abs_delta": float(delta.median()),
        "p90_abs_delta": float(delta.quantile(0.9)),
        "max_abs_delta": float(delta.max()),
    }


def _load_processed_supervised(processed_dir: Path) -> pd.DataFrame:
    parts = []
    for split in ("train", "val", "test"):
        path = processed_dir / f"{split}.csv"
        df = pd.read_csv(path, low_memory=False)
        df = df.loc[df["has_solubility"].fillna(False).astype(bool)].copy()
        df["split"] = split
        parts.append(df)
    return pd.concat(parts, ignore_index=True)


def _coverage_rows(processed: pd.DataFrame, artifact: pd.DataFrame) -> list[dict[str, object]]:
    selected = artifact[["solute_smiles", "T_m", "dH_fus"]].copy()
    merged = processed.merge(selected, on="solute_smiles", how="left", suffixes=("_current", "_open"))

    rows: list[dict[str, object]] = []
    for split in ("train", "val", "test", "all"):
        current = merged if split == "all" else merged.loc[merged["split"] == split].copy()
        current_tm = current["has_T_m"].fillna(False).astype(bool)
        current_dh = current["has_dH_fus"].fillna(False).astype(bool)
        open_tm = current["T_m_open"].notna()
        open_dh = current["dH_fus_open"].notna()
        union_both = (current_tm | open_tm) & (current_dh | open_dh)
        union_frame = current.loc[union_both].copy()
        rows.append(
            {
                "split": split,
                "supervised_rows": int(len(current)),
                "current_T_m_rows": int(current_tm.sum()),
                "current_dH_fus_rows": int(current_dh.sum()),
                "current_joint_rows": int((current_tm & current_dh).sum()),
                "open_T_m_rows": int(open_tm.sum()),
                "open_dH_fus_rows": int(open_dh.sum()),
                "open_joint_rows": int((open_tm & open_dh).sum()),
                "gain_T_m_rows_vs_current": int((~current_tm & open_tm).sum()),
                "gain_dH_fus_rows_vs_current": int((~current_dh & open_dh).sum()),
                "gain_joint_rows_vs_current": int(union_both.sum() - (current_tm & current_dh).sum()),
                "union_joint_rows": int(union_both.sum()),
                "union_joint_unique_solutes": int(union_frame["solute_smiles"].nunique()),
                "union_joint_unique_solvents": int(union_frame["solvent_smiles"].nunique()),
                "union_joint_unique_pairs": int(
                    union_frame[["solute_smiles", "solvent_smiles"]].drop_duplicates().shape[0]
                ),
            }
        )
    return rows


def _write_summary_markdown(summary: dict[str, object], path: Path) -> None:
    coverage = summary["coverage_by_split"]
    pairwise = summary["pairwise_source_agreement"]
    lines = [
        "# Open Crystal Artifact",
        "",
        "## Priority Order",
        "",
        f"- `T_m`: `{summary['priority']['T_m']}`",
        f"- `dH_fus`: `{summary['priority']['dH_fus']}`",
        "",
        "## Source Counts",
        "",
        f"- Curated `T_m`: `{summary['source_counts']['curated_T_m_solutes']}` solutes",
        f"- Bradley `T_m`: `{summary['source_counts']['bradley_T_m_solutes']}` solutes",
        f"- ThermoML `T_m`: `{summary['source_counts']['thermoml_T_m_solutes']}` solutes",
        f"- Curated `dH_fus`: `{summary['source_counts']['curated_dH_fus_solutes']}` solutes",
        f"- ThermoML `dH_fus`: `{summary['source_counts']['thermoml_dH_fus_solutes']}` solutes",
        "",
        "## Selected Artifact",
        "",
        f"- Solutes in artifact: `{summary['artifact_counts']['solutes']}`",
        f"- Final `T_m` coverage: `{summary['artifact_counts']['with_T_m']}`",
        f"- Final `dH_fus` coverage: `{summary['artifact_counts']['with_dH_fus']}`",
        f"- Final joint `T_m + dH_fus` coverage: `{summary['artifact_counts']['with_both']}`",
        "",
        "## Processed-Split Gain",
        "",
        "| Split | Current joint rows | Union joint rows | Gain | Unique pairs after union |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in coverage:
        lines.append(
            "| {split} | {current_joint_rows} | {union_joint_rows} | {gain_joint_rows_vs_current} | {union_joint_unique_pairs} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Pairwise Source Agreement",
            "",
            "| Left | Right | Overlap | Median abs delta | P90 abs delta | Max abs delta |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in pairwise:
        lines.append(
            "| {left} | {right} | {n_overlap} | {median_abs_delta} | {p90_abs_delta} | {max_abs_delta} |".format(
                left=row["left"],
                right=row["right"],
                n_overlap=row["n_overlap"],
                median_abs_delta=f"{row.get('median_abs_delta', float('nan')):.3f}" if row["n_overlap"] else "n/a",
                p90_abs_delta=f"{row.get('p90_abs_delta', float('nan')):.3f}" if row["n_overlap"] else "n/a",
                max_abs_delta=f"{row.get('max_abs_delta', float('nan')):.3f}" if row["n_overlap"] else "n/a",
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    thermoml_path = Path(args.thermoml_aggregated)
    processed_dir = Path(args.processed_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    thermoml = pd.read_csv(thermoml_path)
    rename_map = {
        "T_m": "T_m_thermoml",
        "T_m_source": "T_m_thermoml_source_name",
        "T_m_protocol": "T_m_thermoml_protocol",
        "dH_fus": "dH_fus_thermoml",
        "dH_fus_source": "dH_fus_thermoml_source_name",
        "dH_fus_protocol": "dH_fus_thermoml_protocol",
        "T_m_n_measurements": "T_m_thermoml_n_measurements",
        "T_m_n_dois": "T_m_thermoml_n_dois",
        "T_m_example_doi": "T_m_thermoml_example_doi",
        "T_m_std": "T_m_thermoml_std",
        "T_m_min": "T_m_thermoml_min",
        "T_m_max": "T_m_thermoml_max",
        "dH_fus_n_measurements": "dH_fus_thermoml_n_measurements",
        "dH_fus_n_dois": "dH_fus_thermoml_n_dois",
        "dH_fus_example_doi": "dH_fus_thermoml_example_doi",
        "dH_fus_std": "dH_fus_thermoml_std",
        "dH_fus_min": "dH_fus_thermoml_min",
        "dH_fus_max": "dH_fus_thermoml_max",
        "thermoml_pair_doi_count": "thermoml_pair_doi_count",
    }
    thermoml = thermoml.rename(
        columns={key: value for key, value in rename_map.items() if key in thermoml.columns}
    )

    curated_tm = load_curated_melting_points().rename(columns={"T_m": "T_m_curated"})
    curated_dh = load_curated_fusion_enthalpies().rename(columns={"dH_fus": "dH_fus_curated"})
    bradley_tm = load_bradley_melting_points().rename(columns={"T_m": "T_m_bradley"})

    artifact = pd.DataFrame(
        {
            "solute_smiles": sorted(
                set(curated_tm["solute_smiles"].tolist())
                | set(curated_dh["solute_smiles"].tolist())
                | set(bradley_tm["solute_smiles"].tolist())
                | set(thermoml["solute_smiles"].dropna().tolist())
            )
        }
    )
    artifact = artifact.merge(curated_tm, on="solute_smiles", how="left")
    artifact = artifact.merge(curated_dh, on="solute_smiles", how="left")
    artifact = artifact.merge(bradley_tm, on="solute_smiles", how="left")
    artifact = artifact.merge(thermoml, on="solute_smiles", how="left")

    tm_selected = artifact.apply(
        lambda row: _select_from_priority(row, specs=TM_PRIORITY, value_name="T_m"),
        axis=1,
    )
    dh_selected = artifact.apply(
        lambda row: _select_from_priority(row, specs=DH_PRIORITY, value_name="dH_fus"),
        axis=1,
    )
    artifact = pd.concat([artifact, tm_selected, dh_selected], axis=1)
    artifact["has_open_crystal_both"] = artifact["T_m"].notna() & artifact["dH_fus"].notna()

    artifact_path = out_dir / "open_crystal_solute.csv"
    artifact.to_csv(artifact_path, index=False)

    processed = _load_processed_supervised(processed_dir)
    coverage_rows = _coverage_rows(processed, artifact)
    coverage_df = pd.DataFrame(coverage_rows)
    coverage_path = out_dir / "coverage_by_split.csv"
    coverage_df.to_csv(coverage_path, index=False)

    pairwise_rows = [
        _pairwise_overlap_summary(
            artifact,
            left_name="T_m curated",
            left_column="T_m_curated",
            right_name="T_m ThermoML",
            right_column="T_m_thermoml",
        ),
        _pairwise_overlap_summary(
            artifact,
            left_name="T_m ThermoML",
            left_column="T_m_thermoml",
            right_name="T_m Bradley",
            right_column="T_m_bradley",
        ),
        _pairwise_overlap_summary(
            artifact,
            left_name="dH_fus curated",
            left_column="dH_fus_curated",
            right_name="dH_fus ThermoML",
            right_column="dH_fus_thermoml",
        ),
    ]
    pairwise_df = pd.DataFrame(pairwise_rows)
    pairwise_path = out_dir / "pairwise_source_agreement.csv"
    pairwise_df.to_csv(pairwise_path, index=False)

    summary = {
        "inputs": {
            "thermoml_aggregated": str(thermoml_path),
            "processed_dir": str(processed_dir),
        },
        "priority": {
            "T_m": "curated_nist_webbook > thermoml > bradley",
            "dH_fus": "curated_nist_webbook > thermoml",
        },
        "source_counts": {
            "curated_T_m_solutes": int(curated_tm["T_m_curated"].notna().sum()),
            "bradley_T_m_solutes": int(bradley_tm["T_m_bradley"].notna().sum()),
            "thermoml_T_m_solutes": int(thermoml["T_m_thermoml"].notna().sum()),
            "curated_dH_fus_solutes": int(curated_dh["dH_fus_curated"].notna().sum()),
            "thermoml_dH_fus_solutes": int(thermoml["dH_fus_thermoml"].notna().sum()),
        },
        "artifact_counts": {
            "solutes": int(len(artifact)),
            "with_T_m": int(artifact["T_m"].notna().sum()),
            "with_dH_fus": int(artifact["dH_fus"].notna().sum()),
            "with_both": int(artifact["has_open_crystal_both"].sum()),
            "selected_T_m_sources": artifact["T_m_source"].fillna("<missing>").value_counts().to_dict(),
            "selected_dH_fus_sources": artifact["dH_fus_source"].fillna("<missing>").value_counts().to_dict(),
        },
        "coverage_by_split": coverage_rows,
        "pairwise_source_agreement": pairwise_rows,
        "outputs": {
            "artifact_csv": str(artifact_path),
            "coverage_csv": str(coverage_path),
            "pairwise_csv": str(pairwise_path),
        },
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_summary_markdown(summary, out_dir / "summary.md")

    print(f"Saved open crystal artifact: {artifact_path}")
    print(
        "Solutes={solutes:,} | T_m={with_T_m:,} | dH_fus={with_dH_fus:,} | both={with_both:,}".format(
            **summary["artifact_counts"]
        )
    )
    for row in coverage_rows:
        print(
            f"{row['split']}: current joint={row['current_joint_rows']:,} | "
            f"union joint={row['union_joint_rows']:,} | "
            f"gain={row['gain_joint_rows_vs_current']:,}"
        )


if __name__ == "__main__":
    main()
