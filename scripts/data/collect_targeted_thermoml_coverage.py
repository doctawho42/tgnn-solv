#!/usr/bin/env python3
"""Collect exact SLE-pair ThermoML coverage for targeted auxiliary supervision."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import pandas as pd
from rdkit import RDLogger

SCRIPT_DATA_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SCRIPT_DATA_DIR.parent
REPO_ROOT = SCRIPTS_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _bootstrap  # noqa: E402,F401

RDLogger.DisableLog("rdApp.*")

from scripts.data.extract_idac_from_thermoml import (  # noqa: E402
    _fetch_or_load_record,
    _load_archive_page_dois,
    _load_current_nist_archive_pages,
    _load_dois,
    _load_journal_issue_index,
)
from tgnn_solv.data.thermoml_idac import load_thermoml_json  # noqa: E402
from tgnn_solv.data.thermoml_targeted import (  # noqa: E402
    ACTIVITY_SIGNAL_CANDIDATE_FAMILIES,
    aggregate_targeted_measurements,
    extract_targeted_measurement_rows,
    extract_targeted_pair_rows,
    measurement_rows_to_frame,
    measurements_to_frame,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan local or fetched ThermoML JSON records for exact overlap with "
            "maintained SLE pairs, then summarize coverage by property family, "
            "property label, DOI, and target role."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--processed-dir",
        default="notebooks/data/processed",
        help="Directory containing canonical train.csv / val.csv / test.csv.",
    )
    parser.add_argument(
        "--target-split",
        action="append",
        default=[],
        choices=("train", "val", "test"),
        help="Restrict the target SLE pairs to one or more splits. Defaults to all.",
    )
    parser.add_argument(
        "--json-dir",
        default="notebooks/data/raw/thermoml_json",
        help="Optional local ThermoML JSON cache to scan recursively.",
    )
    parser.add_argument(
        "--doi",
        action="append",
        default=[],
        help="One ThermoML DOI to fetch. Repeat for multiple records.",
    )
    parser.add_argument(
        "--doi-file",
        type=str,
        default=None,
        help="Text file with one DOI per line.",
    )
    parser.add_argument(
        "--archive-page",
        action="append",
        default=[],
        help="One NIST ThermoML journal/archive page to scan for DOI links.",
    )
    parser.add_argument(
        "--archive-page-file",
        type=str,
        default=None,
        help="Text file with one NIST ThermoML archive page URL per line.",
    )
    parser.add_argument(
        "--nist-current-archive-pages",
        action="store_true",
        help="Discover current NIST ThermoML journal issue pages from the official archive page.",
    )
    parser.add_argument(
        "--expand-journal-issues",
        action="store_true",
        help="Expand discovered NIST issue pages through the journal issue-index JSON.",
    )
    parser.add_argument(
        "--journal",
        action="append",
        default=[],
        choices=("jced", "jct", "fpe", "tca", "ijt"),
        help="Restrict expanded issue-page discovery to one or more journals.",
    )
    parser.add_argument(
        "--year-min",
        type=int,
        default=None,
        help="Minimum publication year for issue-index expansion.",
    )
    parser.add_argument(
        "--year-max",
        type=int,
        default=None,
        help="Maximum publication year for issue-index expansion.",
    )
    parser.add_argument(
        "--max-archive-pages",
        type=int,
        default=None,
        help="Optional cap on archive HTML pages scanned after issue-index expansion.",
    )
    parser.add_argument(
        "--save-json-dir",
        type=str,
        default=None,
        help="Optional directory where fetched ThermoML JSON records will be cached.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds for ThermoML JSON fetches.",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.0,
        help="Optional delay in seconds between remote fetches.",
    )
    parser.add_argument(
        "--max-dois",
        type=int,
        default=None,
        help="Optional cap on DOI JSON records fetched after discovery.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort on the first parse/fetch failure instead of recording it and continuing.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/thermoml_targeted_coverage",
        help="Output directory for coverage artifacts.",
    )
    parser.add_argument(
        "--doi-output",
        type=str,
        default=None,
        help="Optional text path for the final deduplicated DOI list used for fetching.",
    )
    return parser.parse_args()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _join_unique(values: pd.Series, limit: int = 25) -> str:
    clean = [str(value) for value in values.dropna().astype(str).unique() if str(value)]
    clean = sorted(clean)
    if len(clean) > limit:
        return "|".join(clean[:limit]) + f"|...(+{len(clean) - limit})"
    return "|".join(clean)


def _load_processed_pairs(processed_dir: Path, splits: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for split in splits:
        path = processed_dir / f"{split}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing processed split CSV: {path}")
        df = pd.read_csv(path, low_memory=False)
        df = df.loc[df["has_solubility"].fillna(False).astype(bool)].copy()
        if df.empty:
            continue
        df["split"] = split
        df["directed_pair_key"] = (
            df["solute_smiles"].astype(str).str.strip()
            + ">>"
            + df["solvent_smiles"].astype(str).str.strip()
        )
        df["pair_key_sorted"] = pd.DataFrame(
            {
                "a": df["solute_smiles"].astype(str).str.strip(),
                "b": df["solvent_smiles"].astype(str).str.strip(),
            }
        ).apply(lambda row: ">>".join(sorted((row["a"], row["b"]))), axis=1)
        df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
        frames.append(df)

    if not frames:
        return pd.DataFrame(
            columns=[
                "split",
                "solute_smiles",
                "solvent_smiles",
                "solute_name",
                "solvent_name",
                "directed_pair_key",
                "pair_key_sorted",
                "n_rows",
                "n_temperatures",
                "temp_min",
                "temp_max",
            ]
        )

    combined = pd.concat(frames, ignore_index=True)
    grouped = (
        combined.groupby(
            [
                "split",
                "solute_smiles",
                "solvent_smiles",
                "solute_name",
                "solvent_name",
                "directed_pair_key",
                "pair_key_sorted",
            ],
            dropna=False,
            sort=True,
        )
        .agg(
            n_rows=("ln_x2", "size"),
            n_temperatures=("temperature", lambda values: int(values.dropna().nunique())),
            temp_min=("temperature", "min"),
            temp_max=("temperature", "max"),
        )
        .reset_index()
    )
    return grouped


def _deduplicate_binary_matches(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    work = df.copy()
    work["record_key"] = work["doi"].fillna(work["source_label"])
    subset = [
        "record_key",
        "dataset_number",
        "pair_key_sorted",
        "property_label",
        "property_method",
        "property_phase",
        "property_standard_state",
        "property_target_smiles",
    ]
    work = work.drop_duplicates(subset=subset, keep="first").drop(columns=["record_key"])
    return work.reset_index(drop=True)


def _expand_to_sle_pairs(
    binary_matches: pd.DataFrame,
    pairs: pd.DataFrame,
) -> pd.DataFrame:
    if binary_matches.empty or pairs.empty:
        return pd.DataFrame()
    expanded = binary_matches.merge(pairs, on="pair_key_sorted", how="inner")
    target_smiles = expanded["property_target_smiles"].fillna("")
    expanded["property_target_role"] = "unspecified"
    expanded.loc[target_smiles.eq(expanded["solute_smiles"]), "property_target_role"] = "solute"
    expanded.loc[target_smiles.eq(expanded["solvent_smiles"]), "property_target_role"] = "solvent"
    expanded["property_target_matches_solute"] = expanded["property_target_role"].eq("solute")
    expanded["property_target_matches_solvent"] = expanded["property_target_role"].eq("solvent")
    return expanded


def _coverage_by_split(
    pairs: pd.DataFrame,
    expanded: pd.DataFrame,
    *,
    candidate_measurements: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for split in sorted(pairs["split"].dropna().unique().tolist()):
        pair_subset = pairs.loc[pairs["split"] == split].copy()
        match_subset = expanded.loc[expanded["split"] == split].copy() if not expanded.empty else pd.DataFrame()
        measurement_subset = (
            candidate_measurements.loc[candidate_measurements["split"] == split].copy()
            if candidate_measurements is not None and not candidate_measurements.empty
            else pd.DataFrame()
        )
        directed_pairs = set(pair_subset["directed_pair_key"])
        rows.append(
            {
                "split": split,
                "n_target_directed_pairs": int(len(directed_pairs)),
                "n_target_unordered_pairs": int(pair_subset["pair_key_sorted"].nunique()),
                "n_matched_directed_pairs": int(match_subset["directed_pair_key"].nunique()) if not match_subset.empty else 0,
                "n_matched_unordered_pairs": int(match_subset["pair_key_sorted"].nunique()) if not match_subset.empty else 0,
                "directed_pair_coverage_fraction": (
                    float(match_subset["directed_pair_key"].nunique() / len(directed_pairs))
                    if directed_pairs
                    else 0.0
                ),
                "n_property_rows": int(len(match_subset)),
                "n_dois": int(match_subset["doi"].dropna().nunique()) if not match_subset.empty else 0,
                "n_pairs_with_direct_activity": int(
                    match_subset.loc[
                        match_subset["property_family"] == "direct_activity",
                        "directed_pair_key",
                    ].nunique()
                )
                if not match_subset.empty
                else 0,
                "n_pairs_with_direct_activity_solute_target": int(
                    match_subset.loc[
                        (match_subset["property_family"] == "direct_activity")
                        & match_subset["property_target_role"].eq("solute"),
                        "directed_pair_key",
                    ].nunique()
                )
                if not match_subset.empty
                else 0,
                "n_pairs_with_direct_activity_solvent_target": int(
                    match_subset.loc[
                        (match_subset["property_family"] == "direct_activity")
                        & match_subset["property_target_role"].eq("solvent"),
                        "directed_pair_key",
                    ].nunique()
                )
                if not match_subset.empty
                else 0,
                "n_pairs_with_excess_thermo": int(
                    match_subset.loc[
                        match_subset["property_family"] == "excess_thermo",
                        "directed_pair_key",
                    ].nunique()
                )
                if not match_subset.empty
                else 0,
                "n_pairs_with_vle_like": int(
                    match_subset.loc[
                        match_subset["property_family"] == "vle_like",
                        "directed_pair_key",
                    ].nunique()
                )
                if not match_subset.empty
                else 0,
                "n_pairs_with_solution_thermo": int(
                    match_subset.loc[
                        match_subset["property_family"] == "solution_thermo",
                        "directed_pair_key",
                    ].nunique()
                )
                if not match_subset.empty
                else 0,
                "n_pairs_with_any_activity_signal_candidate": int(
                    match_subset.loc[
                        match_subset["property_family"].isin(ACTIVITY_SIGNAL_CANDIDATE_FAMILIES),
                        "directed_pair_key",
                    ].nunique()
                )
                if not match_subset.empty
                else 0,
                "n_pairs_with_candidate_measurements": int(
                    measurement_subset["directed_pair_key"].nunique()
                )
                if not measurement_subset.empty
                else 0,
            }
        )
    return pd.DataFrame(rows)


def _coverage_by_group(expanded: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if expanded.empty:
        return pd.DataFrame(columns=[*group_cols, "n_property_rows", "n_directed_pairs", "n_unordered_pairs", "n_dois"])
    grouped = (
        expanded.groupby(group_cols, dropna=False, sort=True)
        .agg(
            n_property_rows=("property_label", "size"),
            n_directed_pairs=("directed_pair_key", "nunique"),
            n_unordered_pairs=("pair_key_sorted", "nunique"),
            n_dois=("doi", lambda values: int(values.dropna().nunique())),
            n_solute_targeted_pairs=(
                "directed_pair_key",
                lambda values: int(
                    expanded.loc[values.index, :].loc[
                        expanded.loc[values.index, "property_target_role"].eq("solute"),
                        "directed_pair_key",
                    ].nunique()
                ),
            ),
            n_solvent_targeted_pairs=(
                "directed_pair_key",
                lambda values: int(
                    expanded.loc[values.index, :].loc[
                        expanded.loc[values.index, "property_target_role"].eq("solvent"),
                        "directed_pair_key",
                    ].nunique()
                ),
            ),
        )
        .reset_index()
    )
    return grouped


def _covered_pairs_summary(expanded: pd.DataFrame) -> pd.DataFrame:
    if expanded.empty:
        return pd.DataFrame()
    grouped = (
        expanded.groupby(
            [
                "split",
                "directed_pair_key",
                "solute_smiles",
                "solvent_smiles",
                "solute_name",
                "solvent_name",
                "pair_key_sorted",
                "n_rows",
                "n_temperatures",
                "temp_min",
                "temp_max",
            ],
            dropna=False,
            sort=True,
        )
        .agg(
            n_property_rows=("property_label", "size"),
            n_property_labels=("property_label", "nunique"),
            n_property_families=("property_family", "nunique"),
            n_dois=("doi", lambda values: int(values.dropna().nunique())),
            property_labels=("property_label", _join_unique),
            property_families=("property_family", _join_unique),
            target_roles=("property_target_role", _join_unique),
            dois=("doi", _join_unique),
        )
        .reset_index()
    )
    return grouped


def _missing_pairs_summary(pairs: pd.DataFrame, covered_pairs: pd.DataFrame) -> pd.DataFrame:
    if pairs.empty:
        return pd.DataFrame()
    covered = set(covered_pairs["directed_pair_key"]) if not covered_pairs.empty else set()
    missing = pairs.loc[~pairs["directed_pair_key"].isin(covered)].copy()
    return missing.sort_values(["split", "n_rows", "n_temperatures"], ascending=[True, False, False])


def _candidate_covered_pairs_summary(expanded: pd.DataFrame) -> pd.DataFrame:
    if expanded.empty:
        return pd.DataFrame()
    subset = expanded.loc[
        expanded["property_family"].isin(ACTIVITY_SIGNAL_CANDIDATE_FAMILIES)
    ].copy()
    if subset.empty:
        return pd.DataFrame()
    grouped = (
        subset.groupby(
            [
                "split",
                "directed_pair_key",
                "solute_smiles",
                "solvent_smiles",
                "solute_name",
                "solvent_name",
                "pair_key_sorted",
                "n_rows",
                "n_temperatures",
                "temp_min",
                "temp_max",
            ],
            dropna=False,
            sort=True,
        )
        .agg(
            n_property_rows=("property_label", "size"),
            n_property_labels=("property_label", "nunique"),
            n_property_families=("property_family", "nunique"),
            n_dois=("doi", lambda values: int(values.dropna().nunique())),
            property_labels=("property_label", _join_unique),
            property_families=("property_family", _join_unique),
            target_roles=("property_target_role", _join_unique),
            dois=("doi", _join_unique),
        )
        .reset_index()
    )
    return grouped


def _write_markdown_summary(
    summary: dict[str, object],
    *,
    coverage_by_split: pd.DataFrame,
    coverage_by_family: pd.DataFrame,
    path: Path,
) -> None:
    lines = [
        "# Targeted ThermoML Coverage Summary",
        "",
        f"- Target SLE directed pairs: `{summary.get('n_target_directed_pairs', 0)}`",
        f"- Target SLE unordered pairs: `{summary.get('n_target_unordered_pairs', 0)}`",
        f"- Binary ThermoML match rows: `{summary.get('n_binary_property_rows', 0)}`",
        f"- Binary ThermoML measurement rows: `{summary.get('n_binary_measurement_rows', 0)}`",
        f"- Directed SLE pair match rows: `{summary.get('n_directed_property_rows', 0)}`",
        f"- Directed SLE aggregated measurement rows: `{summary.get('n_directed_measurement_rows', 0)}`",
        f"- Directed SLE pairs with any activity-signal candidate family: `{summary.get('n_candidate_directed_pairs_matched', 0)}`",
        f"- Directed SLE pairs with candidate measurements: `{summary.get('n_candidate_directed_pairs_with_measurements', 0)}`",
        f"- Candidate-family directed aggregated measurement rows: `{summary.get('n_candidate_directed_measurement_rows', 0)}`",
        f"- Matched DOIs: `{summary.get('n_matched_dois', 0)}`",
        "",
        "## Coverage By Split",
        "",
        "| Split | Target directed pairs | Matched directed pairs | Coverage | Any activity-signal candidate pairs | Candidate pairs with measurements | Direct activity pairs | Solute-targeted direct activity pairs | Excess-thermo pairs | Solution-thermo pairs | VLE-like pairs |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in coverage_by_split.to_dict(orient="records"):
        lines.append(
            "| {split} | {n_target_directed_pairs} | {n_matched_directed_pairs} | {directed_pair_coverage_fraction:.4f} | {n_pairs_with_any_activity_signal_candidate} | {n_pairs_with_candidate_measurements} | {n_pairs_with_direct_activity} | {n_pairs_with_direct_activity_solute_target} | {n_pairs_with_excess_thermo} | {n_pairs_with_solution_thermo} | {n_pairs_with_vle_like} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Top Families",
            "",
            "| Split | Family | Directed pairs | Property rows | DOIs | Solute-targeted pairs |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    family_rows = coverage_by_family.sort_values(
        ["split", "n_directed_pairs", "n_property_rows"],
        ascending=[True, False, False],
    ).to_dict(orient="records")
    for row in family_rows[:20]:
        lines.append(
            "| {split} | {property_family} | {n_directed_pairs} | {n_property_rows} | {n_dois} | {n_solute_targeted_pairs} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    target_splits = args.target_split or ["train", "val", "test"]
    pairs = _load_processed_pairs(Path(args.processed_dir), target_splits)
    target_pair_set = set(pairs["pair_key_sorted"]) if not pairs.empty else set()

    doi_list = list(dict.fromkeys(args.doi))
    if args.doi_file is not None:
        doi_list.extend(_load_dois(Path(args.doi_file)))
        doi_list = list(dict.fromkeys(doi_list))

    archive_pages = list(dict.fromkeys(args.archive_page))
    if args.archive_page_file is not None:
        archive_pages.extend(_load_dois(Path(args.archive_page_file)))
        archive_pages = list(dict.fromkeys(archive_pages))
    if args.nist_current_archive_pages:
        discovered_pages = _load_current_nist_archive_pages(timeout=args.timeout)
        print(f"Discovered {len(discovered_pages)} current NIST archive page(s).", flush=True)
        archive_pages.extend(discovered_pages)
        archive_pages = list(dict.fromkeys(archive_pages))

    archive_page_stats: list[dict[str, object]] = []
    issue_index_stats: list[dict[str, object]] = []
    if args.expand_journal_issues and archive_pages:
        expanded_pages: list[str] = []
        keep_journals = set(args.journal)
        for seed_page in archive_pages:
            try:
                stats, pages = _load_journal_issue_index(
                    seed_page,
                    timeout=args.timeout,
                    year_min=args.year_min,
                    year_max=args.year_max,
                )
                issue_index_stats.append({"status": "ok", **stats})
                if keep_journals and stats["journal"] not in keep_journals:
                    continue
                print(
                    "Issue index pages: "
                    f"{stats['n_issue_pages']:4d} | {stats['journal']} | {stats['issue_index']}",
                    flush=True,
                )
                expanded_pages.extend(pages)
            except Exception as exc:
                issue_index_stats.append(
                    {
                        "status": "error",
                        "seed_page": seed_page,
                        "error": str(exc),
                    }
                )
                if args.fail_fast:
                    raise
                print(f"Issue-index expansion failed: {seed_page}: {exc}", flush=True)
        archive_pages = list(dict.fromkeys(expanded_pages))

    if args.max_archive_pages is not None:
        archive_pages = archive_pages[: args.max_archive_pages]

    for page_url in archive_pages:
        try:
            page_dois = _load_archive_page_dois(page_url, timeout=args.timeout)
            archive_page_stats.append(
                {
                    "archive_page": page_url,
                    "status": "ok",
                    "n_dois": len(page_dois),
                }
            )
            print(f"Archive page DOI links: {len(page_dois):4d} | {page_url}", flush=True)
            doi_list.extend(page_dois)
            doi_list = list(dict.fromkeys(doi_list))
        except Exception as exc:
            archive_page_stats.append(
                {
                    "archive_page": page_url,
                    "status": "error",
                    "error": str(exc),
                    "n_dois": 0,
                }
            )
            if args.fail_fast:
                raise
            print(f"Archive page failed: {page_url}: {exc}", flush=True)

    doi_list = list(dict.fromkeys(doi_list))
    if args.max_dois is not None:
        doi_list = doi_list[: args.max_dois]
    if args.doi_output is not None:
        Path(args.doi_output).write_text("\n".join(doi_list) + "\n", encoding="utf-8")

    save_json_dir = Path(args.save_json_dir) if args.save_json_dir else None
    if save_json_dir is not None:
        save_json_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    measurement_rows: list[dict[str, object]] = []
    parse_stats: list[dict[str, object]] = []

    if doi_list:
        print(f"Fetching {len(doi_list)} ThermoML JSON record(s) by DOI...", flush=True)
    for idx, doi in enumerate(doi_list, start=1):
        try:
            record, source_label, cache_hit = _fetch_or_load_record(
                doi,
                timeout=args.timeout,
                save_json_dir=save_json_dir,
            )
            extracted = extract_targeted_pair_rows(
                record,
                source_label=source_label,
                target_pairs=target_pair_set,
            )
            extracted_measurements = extract_targeted_measurement_rows(
                record,
                source_label=source_label,
                target_pairs=target_pair_set,
            )
            rows.extend(extracted)
            measurement_rows.extend(extracted_measurements)
            parse_stats.append(
                {
                    "source_type": "doi",
                    "source_id": doi,
                    "status": "ok",
                    "cache_hit": cache_hit,
                    "n_match_rows": len(extracted),
                    "n_measurement_rows": len(extracted_measurements),
                    "title": record.get("Citation", {}).get("sTitle"),
                }
            )
            if extracted or extracted_measurements:
                print(
                    f"[{idx:04d}/{len(doi_list):04d}] targeted rows={len(extracted):4d} | measurement rows={len(extracted_measurements):4d} | {doi}",
                    flush=True,
                )
        except Exception as exc:
            parse_stats.append(
                {
                    "source_type": "doi",
                    "source_id": doi,
                    "status": "error",
                    "cache_hit": False,
                    "n_match_rows": 0,
                    "n_measurement_rows": 0,
                    "error": str(exc),
                }
            )
            if args.fail_fast:
                raise
            print(f"[{idx:04d}/{len(doi_list):04d}] fetch failed | {doi}: {exc}", flush=True)
        if args.request_delay > 0 and idx < len(doi_list):
            time.sleep(args.request_delay)

    json_dir = Path(args.json_dir) if args.json_dir else None
    if json_dir is not None and json_dir.exists():
        json_paths = sorted(json_dir.rglob("*.json"))
        print(f"Parsing {len(json_paths)} local ThermoML JSON file(s)...", flush=True)
        for idx, json_path in enumerate(json_paths, start=1):
            try:
                record = load_thermoml_json(json_path)
                extracted = extract_targeted_pair_rows(
                    record,
                    source_label=str(json_path),
                    target_pairs=target_pair_set,
                )
                extracted_measurements = extract_targeted_measurement_rows(
                    record,
                    source_label=str(json_path),
                    target_pairs=target_pair_set,
                )
                rows.extend(extracted)
                measurement_rows.extend(extracted_measurements)
                parse_stats.append(
                    {
                        "source_type": "json",
                        "source_id": str(json_path),
                        "status": "ok",
                        "cache_hit": True,
                        "n_match_rows": len(extracted),
                        "n_measurement_rows": len(extracted_measurements),
                        "title": record.get("Citation", {}).get("sTitle"),
                    }
                )
                if extracted or extracted_measurements:
                    print(
                        f"[{idx:04d}/{len(json_paths):04d}] targeted rows={len(extracted):4d} | measurement rows={len(extracted_measurements):4d} | {json_path.name}",
                        flush=True,
                    )
            except Exception as exc:
                parse_stats.append(
                    {
                        "source_type": "json",
                        "source_id": str(json_path),
                        "status": "error",
                        "cache_hit": True,
                        "n_match_rows": 0,
                        "n_measurement_rows": 0,
                        "error": str(exc),
                    }
                )
                if args.fail_fast:
                    raise

    if not doi_list and (json_dir is None or not json_dir.exists()):
        raise SystemExit(
            "Provide at least one input source: --json-dir, --doi, --doi-file, "
            "--archive-page, --archive-page-file, or --nist-current-archive-pages."
        )

    binary_matches = _deduplicate_binary_matches(measurements_to_frame(rows))
    directed_matches = _expand_to_sle_pairs(binary_matches, pairs)
    binary_measurements = measurement_rows_to_frame(measurement_rows)
    binary_measurements_aggregated = aggregate_targeted_measurements(binary_measurements)
    directed_measurements = _expand_to_sle_pairs(binary_measurements_aggregated, pairs)
    candidate_directed_measurements = directed_measurements.loc[
        directed_measurements["property_family"].isin(ACTIVITY_SIGNAL_CANDIDATE_FAMILIES)
    ].copy()

    coverage_by_split = _coverage_by_split(
        pairs,
        directed_matches,
        candidate_measurements=candidate_directed_measurements,
    )
    coverage_by_family = _coverage_by_group(directed_matches, ["split", "property_family"])
    coverage_by_property = _coverage_by_group(
        directed_matches,
        ["split", "property_family", "property_label"],
    )
    covered_pairs = _covered_pairs_summary(directed_matches)
    missing_pairs = _missing_pairs_summary(pairs, covered_pairs)
    candidate_covered_pairs = _candidate_covered_pairs_summary(directed_matches)
    candidate_missing_pairs = _missing_pairs_summary(pairs, candidate_covered_pairs)
    candidate_measurement_pair_keys = (
        set(candidate_directed_measurements["directed_pair_key"])
        if not candidate_directed_measurements.empty
        else set()
    )
    candidate_measurement_covered_pairs = pairs.loc[
        pairs["directed_pair_key"].isin(candidate_measurement_pair_keys)
    ].copy()
    candidate_measurement_covered_pairs = candidate_measurement_covered_pairs.sort_values(
        ["split", "n_rows", "n_temperatures"],
        ascending=[True, False, False],
    )
    candidate_measurement_missing_pairs = _missing_pairs_summary(
        pairs,
        candidate_measurement_covered_pairs[["directed_pair_key"]],
    )

    parse_audit = pd.DataFrame(parse_stats)
    parse_audit.to_csv(out_dir / "parse_audit.csv", index=False)
    binary_matches.to_csv(out_dir / "thermoml_binary_pair_matches.csv", index=False)
    directed_matches.to_csv(out_dir / "sle_pair_matches.csv", index=False)
    binary_measurements.to_csv(out_dir / "thermoml_targeted_measurements.csv", index=False)
    binary_measurements_aggregated.to_csv(
        out_dir / "thermoml_targeted_measurements_aggregated.csv",
        index=False,
    )
    directed_measurements.to_csv(
        out_dir / "sle_targeted_measurements_aggregated.csv",
        index=False,
    )
    candidate_directed_measurements.to_csv(
        out_dir / "candidate_sle_targeted_measurements_aggregated.csv",
        index=False,
    )
    coverage_by_split.to_csv(out_dir / "coverage_by_split.csv", index=False)
    coverage_by_family.to_csv(out_dir / "coverage_by_family.csv", index=False)
    coverage_by_property.to_csv(out_dir / "coverage_by_property.csv", index=False)
    covered_pairs.to_csv(out_dir / "covered_sle_pairs.csv", index=False)
    missing_pairs.to_csv(out_dir / "missing_sle_pairs.csv", index=False)
    candidate_covered_pairs.to_csv(out_dir / "candidate_covered_sle_pairs.csv", index=False)
    candidate_missing_pairs.to_csv(out_dir / "candidate_missing_sle_pairs.csv", index=False)
    candidate_measurement_covered_pairs.to_csv(
        out_dir / "candidate_measurement_covered_sle_pairs.csv",
        index=False,
    )
    candidate_measurement_missing_pairs.to_csv(
        out_dir / "candidate_measurement_missing_sle_pairs.csv",
        index=False,
    )

    matched_dois = sorted(binary_matches["doi"].dropna().astype(str).unique()) if not binary_matches.empty else []
    (out_dir / "matched_dois.txt").write_text("\n".join(matched_dois) + ("\n" if matched_dois else ""), encoding="utf-8")

    summary = {
        "processed_dir": args.processed_dir,
        "target_splits": target_splits,
        "n_target_directed_pairs": int(pairs["directed_pair_key"].nunique()) if not pairs.empty else 0,
        "n_target_unordered_pairs": int(pairs["pair_key_sorted"].nunique()) if not pairs.empty else 0,
        "n_binary_property_rows": int(len(binary_matches)),
        "n_binary_pairs_matched": int(binary_matches["pair_key_sorted"].nunique()) if not binary_matches.empty else 0,
        "n_binary_measurement_rows": int(len(binary_measurements)),
        "n_binary_measurement_states": int(len(binary_measurements_aggregated)),
        "n_directed_property_rows": int(len(directed_matches)),
        "n_directed_pairs_matched": int(directed_matches["directed_pair_key"].nunique()) if not directed_matches.empty else 0,
        "n_directed_measurement_rows": int(len(directed_measurements)),
        "n_candidate_directed_measurement_rows": int(len(candidate_directed_measurements)),
        "n_candidate_directed_pairs_matched": int(candidate_covered_pairs["directed_pair_key"].nunique()) if not candidate_covered_pairs.empty else 0,
        "n_candidate_directed_pairs_with_measurements": int(len(candidate_measurement_pair_keys)),
        "n_matched_dois": int(len(matched_dois)),
        "coverage_by_split": coverage_by_split.to_dict(orient="records"),
        "top_property_rows": coverage_by_property.sort_values(
            ["n_directed_pairs", "n_property_rows"],
            ascending=[False, False],
        ).head(25).to_dict(orient="records"),
        "archive_page_stats": archive_page_stats,
        "issue_index_stats": issue_index_stats,
        "parse_audit": {
            "n_sources": int(len(parse_audit)),
            "n_sources_with_matches": int((parse_audit["n_match_rows"] > 0).sum()) if not parse_audit.empty else 0,
            "n_sources_with_measurements": int((parse_audit["n_measurement_rows"] > 0).sum()) if not parse_audit.empty else 0,
            "n_errors": int((parse_audit["status"] == "error").sum()) if not parse_audit.empty else 0,
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2) + "\n",
        encoding="utf-8",
    )
    _write_markdown_summary(
        summary,
        coverage_by_split=coverage_by_split,
        coverage_by_family=coverage_by_family,
        path=out_dir / "SUMMARY.md",
    )
    print(json.dumps(_json_safe(summary), indent=2))


if __name__ == "__main__":
    main()
