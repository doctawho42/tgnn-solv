#!/usr/bin/env python3
"""Build an IDAC CSV from NIST ThermoML JSON records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parents[0]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tgnn_solv.data.thermoml_idac import (
    doi_to_json_url,
    extract_idac_rows,
    fetch_thermoml_json,
    load_thermoml_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract ln(gamma_inf) rows from NIST ThermoML JSON into a CSV.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--doi",
        action="append",
        default=[],
        help="One ThermoML DOI to fetch. Repeat the flag for multiple DOIs.",
    )
    parser.add_argument(
        "--doi-file",
        type=str,
        default=None,
        help="Text file with one DOI per line. Blank lines and lines starting with # are ignored.",
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
        "--output",
        type=str,
        default="notebooks/data/raw/idac.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds for ThermoML JSON fetches.",
    )
    return parser.parse_args()


def _load_dois(path: Path) -> list[str]:
    """Load DOI strings from a text file."""
    dois: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        dois.append(stripped)
    return dois


def _safe_json_name(doi: str) -> str:
    """Map a DOI to a filesystem-safe JSON filename."""
    return doi.replace("/", "__").replace(":", "_")


def main() -> None:
    args = parse_args()

    doi_list = list(dict.fromkeys(args.doi))
    if args.doi_file is not None:
        doi_list.extend(_load_dois(Path(args.doi_file)))
        doi_list = list(dict.fromkeys(doi_list))

    rows: list[dict[str, object]] = []

    if args.save_json_dir is not None:
        save_json_dir = Path(args.save_json_dir)
        save_json_dir.mkdir(parents=True, exist_ok=True)
    else:
        save_json_dir = None

    if doi_list:
        print(f"Fetching {len(doi_list)} ThermoML JSON record(s) by DOI...")
    for doi in doi_list:
        record = fetch_thermoml_json(doi, timeout=args.timeout)
        source_label = doi_to_json_url(doi)
        rows.extend(extract_idac_rows(record, source_label=source_label))
        if save_json_dir is not None:
            out_path = save_json_dir / f"{_safe_json_name(doi)}.json"
            out_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    if args.json_dir is not None:
        json_dir = Path(args.json_dir)
        json_paths = sorted(json_dir.rglob("*.json"))
        print(f"Parsing {len(json_paths)} local ThermoML JSON file(s)...")
        for json_path in json_paths:
            record = load_thermoml_json(json_path)
            rows.extend(extract_idac_rows(record, source_label=str(json_path)))

    if not doi_list and args.json_dir is None:
        raise SystemExit("Provide at least one input source: --doi, --doi-file, or --json-dir")

    if not rows:
        print("No IDAC rows were extracted.")
        return

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(
        subset=["doi", "solute_smiles", "solvent_smiles", "temperature", "gamma_inf"],
        keep="first",
    ).sort_values(["doi", "solvent_smiles", "solute_smiles", "temperature"])

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"Saved: {output_path}")
    print(f"Rows: {len(df):,}")
    print(f"DOIs: {df['doi'].nunique():,}")
    print(f"Unique pairs: {df[['solute_smiles', 'solvent_smiles']].drop_duplicates().shape[0]:,}")
    print(f"Missing solute SMILES: {int(df['solute_smiles'].isna().sum()):,}")
    print(f"Missing solvent SMILES: {int(df['solvent_smiles'].isna().sum()):,}")


if __name__ == "__main__":
    main()
