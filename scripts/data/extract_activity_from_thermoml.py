#!/usr/bin/env python3
"""Extract finite-composition activity-side ThermoML data into a reusable artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd
from rdkit import RDLogger

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parents[0]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

RDLogger.DisableLog("rdApp.*")

from tgnn_solv.data.thermoml_activity import (
    aggregate_activity_measurements,
    extract_activity_measurements,
    measurements_to_frame,
)
from tgnn_solv.data.thermoml_idac import load_thermoml_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract finite-composition activity-side supervision from a local "
            "ThermoML JSON cache. Infinite-dilution activity-coefficient rows "
            "are intentionally excluded because they belong to the separate "
            "IDAC contour."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--json-dir",
        type=str,
        default="notebooks/data/raw/thermoml_json",
        help="Directory containing local ThermoML JSON files to parse recursively.",
    )
    parser.add_argument(
        "--processed-dir",
        type=str,
        default="notebooks/data/processed",
        help="Optional canonical processed SLE split directory for overlap audits.",
    )
    parser.add_argument(
        "--output-raw",
        type=str,
        default="results/thermoml_activity/thermoml_activity_measurements.csv",
        help="Output CSV for raw per-measurement rows.",
    )
    parser.add_argument(
        "--output-aggregated",
        type=str,
        default="results/thermoml_activity/thermoml_activity_aggregated.csv",
        help="Output CSV for exact-state aggregated rows.",
    )
    parser.add_argument(
        "--audit-output",
        type=str,
        default="results/thermoml_activity/summary.json",
        help="JSON path for extraction diagnostics.",
    )
    parser.add_argument(
        "--summary-md",
        type=str,
        default="results/thermoml_activity/SUMMARY.md",
        help="Markdown summary path.",
    )
    parser.add_argument(
        "--parse-audit-csv",
        type=str,
        default="results/thermoml_activity/parse_audit.csv",
        help="CSV path for per-file parse audit rows.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort on the first parse failure.",
    )
    return parser.parse_args()


def _load_processed_supervised(processed_dir: Path) -> pd.DataFrame | None:
    if not processed_dir.exists():
        return None
    parts = []
    for split in ("train", "val", "test"):
        path = processed_dir / f"{split}.csv"
        if not path.exists():
            return None
        df = pd.read_csv(path, low_memory=False)
        df = df.loc[df["has_solubility"].fillna(False).astype(bool)].copy()
        if df.empty:
            continue
        df["split"] = split
        solute = pd.to_numeric(df["solute_smiles"].notna(), errors="coerce")
        _ = solute  # silence lintless editor assumptions
        pair_a = df["solute_smiles"].astype(str)
        pair_b = df["solvent_smiles"].astype(str)
        df["pair_key_directed"] = pair_a + ">>" + pair_b
        df["pair_key_sorted"] = pd.DataFrame(
            {"a": pair_a, "b": pair_b}
        ).apply(lambda row: ">>".join(sorted((row["a"], row["b"]))), axis=1)
        parts.append(df)
    if not parts:
        return None
    return pd.concat(parts, ignore_index=True)


def _temperature_span_summary(df: pd.DataFrame) -> dict[str, object]:
    if df.empty:
        return {"all": {"n_groups": 0}}

    work = df.copy()
    work["temperature"] = pd.to_numeric(work["temperature"], errors="coerce")
    work = work.dropna(subset=["temperature"])
    if work.empty:
        return {"all": {"n_groups": 0}}

    result: dict[str, object] = {}
    for property_key in sorted(["all", *work["property_key"].dropna().unique().tolist()]):
        subset = work if property_key == "all" else work.loc[work["property_key"] == property_key].copy()
        if subset.empty:
            result[property_key] = {"n_groups": 0}
            continue
        group_key = subset["targeted_pair_key"].where(
            subset["targeted_pair_key"].notna(),
            subset["pair_key_sorted"],
        )
        grouped = subset.assign(_group_key=group_key).groupby("_group_key", sort=True)
        spans = grouped["temperature"].agg(["count", "min", "max"]).reset_index()
        spans["span_k"] = spans["max"] - spans["min"]
        result[property_key] = {
            "n_groups": int(len(spans)),
            "n_groups_ge_2_temperatures": int((spans["count"] >= 2).sum()),
            "n_groups_span_ge_5k": int((spans["span_k"] >= 5.0).sum()),
            "n_groups_span_ge_10k": int((spans["span_k"] >= 10.0).sum()),
            "n_groups_span_ge_20k": int((spans["span_k"] >= 20.0).sum()),
            "max_span_k": float(spans["span_k"].max()),
            "median_span_k": float(spans["span_k"].median()),
        }
    return result


def _overlap_summary(
    aggregated: pd.DataFrame,
    processed: pd.DataFrame | None,
) -> list[dict[str, object]]:
    if processed is None or aggregated.empty:
        return []

    rows: list[dict[str, object]] = []
    direct = aggregated.loc[aggregated["is_direct_activity"].fillna(False).astype(bool)].copy()
    for split in ("train", "val", "test", "all"):
        current = processed if split == "all" else processed.loc[processed["split"] == split].copy()
        if current.empty:
            rows.append({"split": split, "supervised_pairs": 0})
            continue

        pair_sorted = set(current["pair_key_sorted"])
        pair_directed = set(current["pair_key_directed"])

        rows.append(
            {
                "split": split,
                "supervised_pairs": int(len(pair_sorted)),
                "unordered_pair_overlap_rows": int(aggregated["pair_key_sorted"].isin(pair_sorted).sum()),
                "unordered_pair_overlap_pairs": int(aggregated.loc[
                    aggregated["pair_key_sorted"].isin(pair_sorted),
                    "pair_key_sorted",
                ].nunique()),
                "direct_target_as_solute_rows": int(
                    direct["targeted_pair_key"].isin(pair_directed).sum()
                ),
                "direct_target_as_solute_pairs": int(
                    direct.loc[
                        direct["targeted_pair_key"].isin(pair_directed),
                        "targeted_pair_key",
                    ].nunique()
                ),
                "direct_target_as_solvent_rows": int(
                    direct["reverse_targeted_pair_key"].isin(pair_directed).sum()
                ),
                "direct_target_as_solvent_pairs": int(
                    direct.loc[
                        direct["reverse_targeted_pair_key"].isin(pair_directed),
                        "reverse_targeted_pair_key",
                    ].nunique()
                ),
            }
        )
    return rows


def _property_overlap_summary(
    aggregated: pd.DataFrame,
    processed: pd.DataFrame | None,
) -> list[dict[str, object]]:
    if processed is None or aggregated.empty:
        return []

    rows: list[dict[str, object]] = []
    for property_key in sorted(aggregated["property_key"].dropna().unique().tolist()):
        subset = aggregated.loc[aggregated["property_key"] == property_key].copy()
        for overlap_row in _overlap_summary(subset, processed):
            rows.append(
                {
                    "property_key": property_key,
                    **overlap_row,
                }
            )
    return rows


def _summary_payload(
    raw_df: pd.DataFrame,
    agg_df: pd.DataFrame,
    *,
    json_dir: Path,
    processed: pd.DataFrame | None,
) -> dict[str, object]:
    direct = agg_df.loc[agg_df["is_direct_activity"].fillna(False).astype(bool)].copy()
    direct_mf = direct.loc[direct["composition_basis"] == "mole_fraction"].copy()

    composition_thresholds = {}
    for threshold in (0.05, 0.10, 0.20):
        subset = direct_mf.loc[pd.to_numeric(direct_mf["composition_value"], errors="coerce") >= threshold].copy()
        composition_thresholds[f"mole_fraction_ge_{threshold:.2f}"] = {
            "rows": int(len(subset)),
            "targeted_pairs": int(subset["targeted_pair_key"].dropna().nunique()),
        }

    property_counts = (
        agg_df["property_key"].value_counts().sort_index().to_dict()
        if not agg_df.empty
        else {}
    )
    basis_counts = (
        agg_df["composition_basis"].value_counts().sort_index().to_dict()
        if not agg_df.empty
        else {}
    )

    return {
        "json_dir": str(json_dir),
        "n_json_files": int(len(list(json_dir.rglob('*.json')))),
        "raw_rows": int(len(raw_df)),
        "aggregated_rows": int(len(agg_df)),
        "raw_unique_dois": int(raw_df["doi"].dropna().nunique()) if not raw_df.empty else 0,
        "aggregated_unique_pairs": int(agg_df["pair_key_sorted"].dropna().nunique()) if not agg_df.empty else 0,
        "aggregated_unique_targeted_pairs": int(agg_df["targeted_pair_key"].dropna().nunique()) if not agg_df.empty else 0,
        "property_counts": property_counts,
        "composition_basis_counts": basis_counts,
        "direct_activity": {
            "rows": int(len(direct)),
            "targeted_pairs": int(direct["targeted_pair_key"].dropna().nunique()),
            "target_components": int(direct["target_smiles"].dropna().nunique()),
            "properties": direct["property_key"].value_counts().sort_index().to_dict() if not direct.empty else {},
            "composition_thresholds": composition_thresholds,
        },
        "component_overlap": _component_overlap_summary(agg_df, processed),
        "temperature_span": _temperature_span_summary(agg_df),
        "sle_overlap_by_split": _overlap_summary(agg_df, processed),
        "sle_overlap_by_property": _property_overlap_summary(agg_df, processed),
        "scope_note": (
            "This contour intentionally excludes infinite-dilution activity-coefficient "
            "rows already covered by the separate ThermoML IDAC path."
        ),
    }


def _component_overlap_summary(
    aggregated: pd.DataFrame,
    processed: pd.DataFrame | None,
) -> dict[str, object]:
    if processed is None or aggregated.empty:
        return {}

    direct = aggregated.loc[aggregated["is_direct_activity"].fillna(False).astype(bool)].copy()
    if direct.empty:
        return {}

    solute_set = set(processed["solute_smiles"].dropna())
    solvent_set = set(processed["solvent_smiles"].dropna())
    target_unique = set(direct["target_smiles"].dropna())
    other_unique = set(direct["other_smiles"].dropna())
    return {
        "direct_target_components": int(len(target_unique)),
        "direct_target_components_in_sle_solutes": int(len(target_unique & solute_set)),
        "direct_target_components_in_sle_solvents": int(len(target_unique & solvent_set)),
        "direct_other_components_in_sle_solutes": int(len(other_unique & solute_set)),
        "direct_other_components_in_sle_solvents": int(len(other_unique & solvent_set)),
    }


def _write_markdown_summary(summary: dict[str, object], path: Path) -> None:
    overlap_rows = summary.get("sle_overlap_by_split", [])
    property_overlap_rows = summary.get("sle_overlap_by_property", [])
    direct = summary.get("direct_activity", {})
    component_overlap = summary.get("component_overlap", {})
    lines = [
        "# ThermoML Finite-Composition Activity Artifact",
        "",
        f"- Local ThermoML JSON files scanned: `{summary.get('n_json_files', 0)}`",
        f"- Raw extracted rows: `{summary.get('raw_rows', 0)}`",
        f"- Aggregated exact-state rows: `{summary.get('aggregated_rows', 0)}`",
        f"- Unique DOIs: `{summary.get('raw_unique_dois', 0)}`",
        f"- Unique unordered pairs: `{summary.get('aggregated_unique_pairs', 0)}`",
        f"- Unique targeted pairs: `{summary.get('aggregated_unique_targeted_pairs', 0)}`",
        "",
        "## Property Counts",
        "",
    ]
    for key, value in summary.get("property_counts", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Direct Activity Subset",
            "",
            f"- Direct finite-composition activity rows: `{direct.get('rows', 0)}`",
            f"- Direct targeted pairs: `{direct.get('targeted_pairs', 0)}`",
            f"- Direct target components: `{direct.get('target_components', 0)}`",
        ]
    )
    for key, value in direct.get("properties", {}).items():
        lines.append(f"- `{key}` rows: `{value}`")
    for threshold, stats in direct.get("composition_thresholds", {}).items():
        lines.append(
            f"- `{threshold}`: `{stats.get('rows', 0)}` rows / `{stats.get('targeted_pairs', 0)}` targeted pairs"
        )
    if component_overlap:
        lines.extend(
            [
                f"- Direct target components overlapping SLE solutes: `{component_overlap.get('direct_target_components_in_sle_solutes', 0)}`",
                f"- Direct target components overlapping SLE solvents: `{component_overlap.get('direct_target_components_in_sle_solvents', 0)}`",
                f"- Direct partner components overlapping SLE solutes: `{component_overlap.get('direct_other_components_in_sle_solutes', 0)}`",
                f"- Direct partner components overlapping SLE solvents: `{component_overlap.get('direct_other_components_in_sle_solvents', 0)}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Temperature Span",
            "",
            "| Property | Groups | >=2 temperatures | Span >=10 K | Span >=20 K | Max span, K |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for key, stats in summary.get("temperature_span", {}).items():
        lines.append(
            "| {key} | {n_groups} | {n_groups_ge_2_temperatures} | {n_groups_span_ge_10k} | {n_groups_span_ge_20k} | {max_span_k:.2f} |".format(
                key=key,
                n_groups=stats.get("n_groups", 0),
                n_groups_ge_2_temperatures=stats.get("n_groups_ge_2_temperatures", 0),
                n_groups_span_ge_10k=stats.get("n_groups_span_ge_10k", 0),
                n_groups_span_ge_20k=stats.get("n_groups_span_ge_20k", 0),
                max_span_k=float(stats.get("max_span_k", 0.0) or 0.0),
            )
        )
    lines.extend(
        [
            "",
            "## Property-Specific SLE Overlap",
            "",
            "| Property | Split | Unordered overlap pairs | Overlap rows | Direct target-as-solute pairs | Direct target-as-solvent pairs |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in property_overlap_rows:
        lines.append(
            "| {property_key} | {split} | {unordered_pair_overlap_pairs} | {unordered_pair_overlap_rows} | {direct_target_as_solute_pairs} | {direct_target_as_solvent_pairs} |".format(
                property_key=row.get("property_key", "n/a"),
                split=row.get("split", "n/a"),
                unordered_pair_overlap_pairs=row.get("unordered_pair_overlap_pairs", 0),
                unordered_pair_overlap_rows=row.get("unordered_pair_overlap_rows", 0),
                direct_target_as_solute_pairs=row.get("direct_target_as_solute_pairs", 0),
                direct_target_as_solvent_pairs=row.get("direct_target_as_solvent_pairs", 0),
            )
        )
    lines.extend(
        [
            "",
            "## SLE Overlap",
            "",
            "| Split | Unordered overlap pairs | Direct target-as-solute pairs | Direct target-as-solvent pairs |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in overlap_rows:
        lines.append(
            "| {split} | {unordered_pair_overlap_pairs} | {direct_target_as_solute_pairs} | {direct_target_as_solvent_pairs} |".format(
                split=row.get("split", "n/a"),
                unordered_pair_overlap_pairs=row.get("unordered_pair_overlap_pairs", 0),
                direct_target_as_solute_pairs=row.get("direct_target_as_solute_pairs", 0),
                direct_target_as_solvent_pairs=row.get("direct_target_as_solvent_pairs", 0),
            )
        )
    lines.extend(
        [
            "",
            "## Scope Note",
            "",
            f"- {summary.get('scope_note', '')}",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    json_dir = Path(args.json_dir)
    processed_dir = Path(args.processed_dir)
    output_raw = Path(args.output_raw)
    output_aggregated = Path(args.output_aggregated)
    audit_output = Path(args.audit_output)
    summary_md = Path(args.summary_md)
    parse_audit_csv = Path(args.parse_audit_csv)

    json_paths = sorted(json_dir.rglob("*.json"))
    if not json_paths:
        raise SystemExit(f"No ThermoML JSON files found under {json_dir}")

    rows: list[dict[str, object]] = []
    parse_stats: list[dict[str, object]] = []
    print(f"Parsing {len(json_paths)} local ThermoML JSON file(s)...", flush=True)
    for idx, json_path in enumerate(json_paths, start=1):
        try:
            record = load_thermoml_json(json_path)
            extracted = extract_activity_measurements(record, source_label=str(json_path))
            rows.extend(extracted)
            parse_stats.append(
                {
                    "path": str(json_path),
                    "status": "ok",
                    "n_activity_rows": len(extracted),
                    "title": record.get("Citation", {}).get("sTitle"),
                }
            )
            if extracted:
                print(
                    f"[{idx:04d}/{len(json_paths):04d}] activity rows={len(extracted):4d} | {json_path.name}",
                    flush=True,
                )
        except Exception as exc:
            parse_stats.append(
                {
                    "path": str(json_path),
                    "status": "error",
                    "error": str(exc),
                    "n_activity_rows": 0,
                }
            )
            if args.fail_fast:
                raise

    raw_df = measurements_to_frame(rows)
    agg_df = aggregate_activity_measurements(raw_df)
    processed = _load_processed_supervised(processed_dir)
    summary = _summary_payload(raw_df, agg_df, json_dir=json_dir, processed=processed)
    summary["parse_audit"] = {
        "csv": str(parse_audit_csv),
        "n_files": int(len(parse_stats)),
        "n_files_with_activity_rows": int(sum(item.get("n_activity_rows", 0) > 0 for item in parse_stats)),
        "n_parse_errors": int(sum(item.get("status") == "error" for item in parse_stats)),
    }

    output_raw.parent.mkdir(parents=True, exist_ok=True)
    output_aggregated.parent.mkdir(parents=True, exist_ok=True)
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    parse_audit_csv.parent.mkdir(parents=True, exist_ok=True)

    raw_df.to_csv(output_raw, index=False)
    agg_df.to_csv(output_aggregated, index=False)
    pd.DataFrame(parse_stats).to_csv(parse_audit_csv, index=False)
    audit_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_markdown_summary(summary, summary_md)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
