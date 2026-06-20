#!/usr/bin/env python3
"""Extract pure-component T_m and dH_fus data from ThermoML JSON records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import pandas as pd
from rdkit import RDLogger

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parents[0]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

RDLogger.DisableLog("rdApp.*")

from tgnn_solv.data.thermoml_crystal import (
    aggregate_crystal_measurements,
    extract_crystal_measurements,
    measurements_to_frame,
)
from tgnn_solv.data.thermoml_idac import (
    doi_to_json_url,
    fetch_thermoml_json,
    load_thermoml_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract pure-component crystal properties from ThermoML JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        "--json-dir",
        type=str,
        default=None,
        help="Directory containing local ThermoML JSON files to parse recursively.",
    )
    parser.add_argument(
        "--save-json-dir",
        type=str,
        default=None,
        help="Optional directory where fetched ThermoML JSON records will be cached.",
    )
    parser.add_argument(
        "--output-raw",
        type=str,
        default="results/thermoml_crystal/thermoml_crystal_measurements.csv",
        help="Output CSV for raw per-measurement rows.",
    )
    parser.add_argument(
        "--output-aggregated",
        type=str,
        default="results/thermoml_crystal/thermoml_crystal_aggregated.csv",
        help="Output CSV for aggregated solute-level crystal rows.",
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
        help="Optional cap on fetched DOI records.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort on the first fetch or parse failure.",
    )
    parser.add_argument(
        "--audit-output",
        type=str,
        default="results/thermoml_crystal/summary.json",
        help="Optional JSON path with extraction diagnostics.",
    )
    return parser.parse_args()


def _load_lines(path: Path) -> list[str]:
    items: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        items.append(stripped)
    return items


def _safe_json_name(doi: str) -> str:
    return doi.replace("/", "__").replace(":", "_")


def _fetch_or_load_record(
    doi: str,
    *,
    timeout: float,
    save_json_dir: Path | None,
) -> tuple[dict[str, object], str, bool]:
    if save_json_dir is not None:
        out_path = save_json_dir / f"{_safe_json_name(doi)}.json"
        if out_path.exists():
            return load_thermoml_json(out_path), str(out_path), True
    record = fetch_thermoml_json(doi, timeout=timeout)
    if save_json_dir is not None:
        out_path = save_json_dir / f"{_safe_json_name(doi)}.json"
        out_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record, str(out_path), False
    return record, doi_to_json_url(doi), False


def _write_json(path: str | None, payload: dict[str, object]) -> None:
    if path is None:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _frame_stats(raw_df: pd.DataFrame, agg_df: pd.DataFrame) -> dict[str, object]:
    return {
        "raw_rows": int(len(raw_df)),
        "raw_solutes": int(raw_df["solute_smiles"].nunique()) if not raw_df.empty else 0,
        "raw_dois": int(raw_df["doi"].nunique()) if not raw_df.empty else 0,
        "raw_tm_rows": int((raw_df["property_key"] == "T_m").sum()) if not raw_df.empty else 0,
        "raw_dh_rows": int((raw_df["property_key"] == "dH_fus").sum()) if not raw_df.empty else 0,
        "aggregated_solutes": int(len(agg_df)),
        "aggregated_tm_solutes": int(agg_df["T_m"].notna().sum()) if "T_m" in agg_df else 0,
        "aggregated_dh_solutes": int(agg_df["dH_fus"].notna().sum()) if "dH_fus" in agg_df else 0,
        "aggregated_joint_solutes": int(
            (agg_df["T_m"].notna() & agg_df["dH_fus"].notna()).sum()
        )
        if {"T_m", "dH_fus"}.issubset(agg_df.columns)
        else 0,
    }


def main() -> None:
    args = parse_args()

    doi_list = list(dict.fromkeys(args.doi))
    if args.doi_file is not None:
        doi_list.extend(_load_lines(Path(args.doi_file)))
        doi_list = list(dict.fromkeys(doi_list))
    if args.max_dois is not None:
        doi_list = doi_list[: args.max_dois]

    if args.save_json_dir is not None:
        save_json_dir = Path(args.save_json_dir)
        save_json_dir.mkdir(parents=True, exist_ok=True)
    else:
        save_json_dir = None

    rows: list[dict[str, object]] = []
    fetch_stats: list[dict[str, object]] = []

    if doi_list:
        print(f"Fetching {len(doi_list)} ThermoML JSON record(s) by DOI...", flush=True)
    for idx, doi in enumerate(doi_list, start=1):
        try:
            record, source_label, cache_hit = _fetch_or_load_record(
                doi,
                timeout=args.timeout,
                save_json_dir=save_json_dir,
            )
            extracted = extract_crystal_measurements(record, source_label=source_label)
            rows.extend(extracted)
            fetch_stats.append(
                {
                    "doi": doi,
                    "status": "ok",
                    "cache_hit": cache_hit,
                    "n_crystal_rows": len(extracted),
                    "title": record.get("Citation", {}).get("sTitle"),
                }
            )
            if extracted:
                print(
                    f"[{idx:04d}/{len(doi_list):04d}] crystal rows={len(extracted):4d} | {doi}",
                    flush=True,
                )
        except Exception as exc:
            fetch_stats.append(
                {
                    "doi": doi,
                    "status": "error",
                    "error": str(exc),
                    "n_crystal_rows": 0,
                }
            )
            if args.fail_fast:
                raise
            print(f"[{idx:04d}/{len(doi_list):04d}] fetch failed | {doi}: {exc}", flush=True)
        if args.request_delay > 0 and idx < len(doi_list):
            time.sleep(args.request_delay)

    if args.json_dir is not None:
        json_dir = Path(args.json_dir)
        json_paths = sorted(json_dir.rglob("*.json"))
        print(f"Parsing {len(json_paths)} local ThermoML JSON file(s)...", flush=True)
        for json_path in json_paths:
            try:
                record = load_thermoml_json(json_path)
                extracted = extract_crystal_measurements(record, source_label=str(json_path))
                rows.extend(extracted)
                fetch_stats.append(
                    {
                        "path": str(json_path),
                        "status": "ok",
                        "cache_hit": True,
                        "n_crystal_rows": len(extracted),
                        "title": record.get("Citation", {}).get("sTitle"),
                    }
                )
            except Exception as exc:
                fetch_stats.append(
                    {
                        "path": str(json_path),
                        "status": "error",
                        "error": str(exc),
                        "n_crystal_rows": 0,
                    }
                )
                if args.fail_fast:
                    raise

    if not doi_list and args.json_dir is None:
        raise SystemExit("Provide at least one input source: --doi, --doi-file, or --json-dir")

    raw_df = measurements_to_frame(rows)
    if raw_df.empty:
        _write_json(
            args.audit_output,
            {
                "status": "no_rows",
                "n_dois_requested": len(doi_list),
                "fetch_stats": fetch_stats,
            },
        )
        print("No crystal rows were extracted.")
        return

    raw_df = raw_df.drop_duplicates(
        subset=["doi", "dataset_number", "prop_number", "solute_smiles", "property_key", "value"],
        keep="first",
    ).sort_values(["doi", "solute_smiles", "property_key", "value"])
    agg_df = aggregate_crystal_measurements(raw_df)

    raw_output_path = Path(args.output_raw)
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_df.to_csv(raw_output_path, index=False)

    agg_output_path = Path(args.output_aggregated)
    agg_output_path.parent.mkdir(parents=True, exist_ok=True)
    agg_df.to_csv(agg_output_path, index=False)

    stats = _frame_stats(raw_df, agg_df)
    print(f"Saved raw measurements: {raw_output_path}")
    print(f"Saved aggregated crystal artifact: {agg_output_path}")
    print(
        "Raw rows={raw_rows:,} | solutes={raw_solutes:,} | DOIs={raw_dois:,}".format(
            **stats
        )
    )
    print(
        "Aggregated solutes={aggregated_solutes:,} | T_m={aggregated_tm_solutes:,} | "
        "dH_fus={aggregated_dh_solutes:,} | both={aggregated_joint_solutes:,}".format(
            **stats
        )
    )

    _write_json(
        args.audit_output,
        {
            "status": "ok",
            "inputs": {
                "doi_count": len(doi_list),
                "json_dir": args.json_dir,
            },
            "outputs": {
                "raw_csv": str(raw_output_path),
                "aggregated_csv": str(agg_output_path),
            },
            "stats": stats,
            "fetch_stats": fetch_stats,
        },
    )


if __name__ == "__main__":
    main()
