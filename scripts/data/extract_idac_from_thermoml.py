#!/usr/bin/env python3
"""Build an IDAC CSV from NIST ThermoML JSON records."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import unquote, urljoin
from urllib.request import Request, urlopen

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPT_DIR.parents[0]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from tgnn_solv.data.thermoml_idac import (
    DEFAULT_USER_AGENT,
    doi_to_json_url,
    extract_idac_rows,
    fetch_thermoml_json,
    load_thermoml_json,
)

NIST_THERMOML_ARCHIVE_PAGE = (
    "https://www.nist.gov/mml/acmd/trc/thermoml/thermoml-archive"
)
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.IGNORECASE)
JOURNAL_VAR_RE = re.compile(r"var\s+jstr\s*=\s*[\"']([^\"']+)[\"']")
ISSUE_INDEX_RE = re.compile(r"init_jquery_dropdowns\(\s*jstr\s*,\s*(\d+)")


class _LinkCollector(HTMLParser):
    """Small stdlib-only HTML link extractor for NIST archive pages."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        self._href = attrs_dict.get("href")
        self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        text = " ".join(part.strip() for part in self._text_parts if part.strip())
        self.links.append((text, self._href))
        self._href = None
        self._text_parts = []


def _fetch_text(url: str, timeout: float) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _extract_dois_from_text(text: str) -> list[str]:
    """Extract DOI-looking tokens and strip common URL/file suffixes."""
    dois: list[str] = []
    for match in DOI_RE.findall(text):
        doi = unquote(match)
        doi = re.sub(r"\.(?:json|xml|html)$", "", doi, flags=re.IGNORECASE)
        doi = doi.rstrip(".,);]")
        dois.append(doi)
    return list(dict.fromkeys(dois))


def _load_archive_page_dois(page_url: str, timeout: float) -> list[str]:
    """Fetch one NIST journal issue page and extract DOI identifiers."""
    html = _fetch_text(page_url, timeout=timeout)
    parser = _LinkCollector()
    parser.feed(html)

    found: list[str] = []
    found.extend(_extract_dois_from_text(html))
    for text, href in parser.links:
        absolute_href = urljoin(page_url, href)
        found.extend(_extract_dois_from_text(text))
        found.extend(_extract_dois_from_text(absolute_href))

    return list(dict.fromkeys(found))


def _load_current_nist_archive_pages(timeout: float) -> list[str]:
    """Return current journal issue pages linked from the official NIST page."""
    html = _fetch_text(NIST_THERMOML_ARCHIVE_PAGE, timeout=timeout)
    parser = _LinkCollector()
    parser.feed(html)
    pages = []
    for _, href in parser.links:
        absolute = urljoin(NIST_THERMOML_ARCHIVE_PAGE, href)
        if "trc.nist.gov/journals/" in absolute and absolute.endswith(".html"):
            pages.append(absolute)
    return list(dict.fromkeys(pages))


def _load_journal_issue_index(
    seed_page_url: str,
    *,
    timeout: float,
    year_min: int | None,
    year_max: int | None,
) -> tuple[dict[str, object], list[str]]:
    """
    Expand one NIST journal issue page into all issue pages from its JSON index.

    NIST issue pages load dropdown metadata through
    `/jsons/{journal}_issue.{dated}.json`; reproducing that JS path gives us
    all archive issue pages without relying on browser JavaScript.
    """
    html = _fetch_text(seed_page_url, timeout=timeout)
    journal_match = JOURNAL_VAR_RE.search(html)
    dated_match = ISSUE_INDEX_RE.search(html)
    if journal_match is None or dated_match is None:
        raise ValueError(f"Could not locate NIST issue index metadata in {seed_page_url}")

    journal = journal_match.group(1)
    dated = dated_match.group(1)
    index_url = f"https://trc.nist.gov/jsons/{journal}_issue.{dated}.json"
    index_text = _fetch_text(index_url, timeout=timeout)
    index = json.loads(index_text)

    pages: list[str] = []
    for year_str, volumes in index.items():
        try:
            year = int(year_str)
        except (TypeError, ValueError):
            continue
        if year_min is not None and year < year_min:
            continue
        if year_max is not None and year > year_max:
            continue
        if not isinstance(volumes, dict):
            continue
        for volume_str, issue_map in volumes.items():
            if isinstance(issue_map, dict):
                issues = issue_map.values()
            elif isinstance(issue_map, list):
                issues = issue_map
            else:
                continue
            for issue in issues:
                page = (
                    f"https://trc.nist.gov/journals/{journal}/{year}/"
                    f"{journal}{year}v{volume_str}i{issue}.html"
                )
                pages.append(page)

    stats = {
        "seed_page": seed_page_url,
        "journal": journal,
        "issue_index": index_url,
        "n_issue_pages": len(pages),
        "year_min": year_min,
        "year_max": year_max,
    }
    return stats, list(dict.fromkeys(pages))


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
        "--archive-page",
        action="append",
        default=[],
        help=(
            "NIST ThermoML journal issue/archive HTML page to scan for DOI/JSON "
            "links. Repeat the flag for multiple pages."
        ),
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
        help=(
            "Discover the current journal issue pages linked from the official "
            "NIST ThermoML Archive page and scan them for DOI/JSON links."
        ),
    )
    parser.add_argument(
        "--expand-journal-issues",
        action="store_true",
        help=(
            "For each NIST journal issue page, load its journal issue-index JSON "
            "and scan all issue pages from that index."
        ),
    )
    parser.add_argument(
        "--journal",
        action="append",
        default=[],
        choices=("jced", "jct", "fpe", "tca", "ijt"),
        help=(
            "When --expand-journal-issues is enabled, keep only these NIST "
            "journal codes. Repeat for multiple journals."
        ),
    )
    parser.add_argument(
        "--year-min",
        type=int,
        default=None,
        help="Optional minimum publication year when expanding NIST issue indexes.",
    )
    parser.add_argument(
        "--year-max",
        type=int,
        default=None,
        help="Optional maximum publication year when expanding NIST issue indexes.",
    )
    parser.add_argument(
        "--max-archive-pages",
        type=int,
        default=None,
        help="Optional cap on archive HTML pages scanned after issue-index expansion.",
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
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.0,
        help="Optional delay in seconds between remote ThermoML JSON fetches.",
    )
    parser.add_argument(
        "--max-dois",
        type=int,
        default=None,
        help="Optional cap on the number of DOI JSON records fetched after discovery.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Abort on the first remote fetch or parse failure instead of recording it and continuing.",
    )
    parser.add_argument(
        "--doi-output",
        type=str,
        default=None,
        help="Optional path to write the final deduplicated DOI list used for fetching.",
    )
    parser.add_argument(
        "--audit-output",
        type=str,
        default=None,
        help="Optional JSON path with discovery, fetch, extraction, and output diagnostics.",
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


def _fetch_or_load_record(
    doi: str,
    *,
    timeout: float,
    save_json_dir: Path | None,
) -> tuple[dict[str, object], str, bool]:
    """Load a cached ThermoML JSON record if present, otherwise fetch it."""
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


def main() -> None:
    args = parse_args()

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
        print(
            f"Discovered {len(discovered_pages)} current NIST archive page(s).",
            flush=True,
        )
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
        doi_output = Path(args.doi_output)
        doi_output.parent.mkdir(parents=True, exist_ok=True)
        doi_output.write_text("\n".join(doi_list) + "\n", encoding="utf-8")

    rows: list[dict[str, object]] = []
    fetch_stats: list[dict[str, object]] = []

    if args.save_json_dir is not None:
        save_json_dir = Path(args.save_json_dir)
        save_json_dir.mkdir(parents=True, exist_ok=True)
    else:
        save_json_dir = None

    if doi_list:
        print(f"Fetching {len(doi_list)} ThermoML JSON record(s) by DOI...")
    for idx, doi in enumerate(doi_list, start=1):
        try:
            record, source_label, cache_hit = _fetch_or_load_record(
                doi,
                timeout=args.timeout,
                save_json_dir=save_json_dir,
            )
            extracted = extract_idac_rows(record, source_label=source_label)
            rows.extend(extracted)
            fetch_stats.append(
                {
                    "doi": doi,
                    "status": "ok",
                    "cache_hit": cache_hit,
                    "n_idac_rows": len(extracted),
                    "title": record.get("Citation", {}).get("sTitle"),
                }
            )
            if extracted:
                print(
                    f"[{idx:04d}/{len(doi_list):04d}] IDAC rows={len(extracted):4d} | {doi}",
                    flush=True,
                )
        except Exception as exc:
            fetch_stats.append(
                {
                    "doi": doi,
                    "status": "error",
                    "error": str(exc),
                    "n_idac_rows": 0,
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
        print(f"Parsing {len(json_paths)} local ThermoML JSON file(s)...")
        for json_path in json_paths:
            try:
                record = load_thermoml_json(json_path)
                extracted = extract_idac_rows(record, source_label=str(json_path))
                rows.extend(extracted)
                fetch_stats.append(
                    {
                        "path": str(json_path),
                        "status": "ok",
                        "cache_hit": True,
                        "n_idac_rows": len(extracted),
                        "title": record.get("Citation", {}).get("sTitle"),
                    }
                )
            except Exception as exc:
                fetch_stats.append(
                    {
                        "path": str(json_path),
                        "status": "error",
                        "error": str(exc),
                        "n_idac_rows": 0,
                    }
                )
                if args.fail_fast:
                    raise

    if not doi_list and args.json_dir is None:
        if archive_page_stats or issue_index_stats:
            _write_json(
                args.audit_output,
                {
                    "status": "discovery_only",
                    "n_dois": 0,
                    "issue_indexes": issue_index_stats,
                    "archive_pages": archive_page_stats,
                    "fetch_stats": fetch_stats,
                },
            )
            print("No DOI records selected for fetching; discovery outputs were written.")
            return
        raise SystemExit(
            "Provide at least one input source: --doi, --doi-file, "
            "--archive-page, --archive-page-file, --nist-current-archive-pages, "
            "or --json-dir"
        )

    if not rows:
        _write_json(
            args.audit_output,
            {
                "status": "no_rows",
                "n_dois": len(doi_list),
                "issue_indexes": issue_index_stats,
                "archive_pages": archive_page_stats,
                "fetch_stats": fetch_stats,
            },
        )
        print("No IDAC rows were extracted.")
        return

    df = pd.DataFrame(rows)
    raw_row_count = len(df)
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
    print(f"Raw extracted rows before dedup: {raw_row_count:,}")

    _write_json(
        args.audit_output,
        {
            "status": "ok",
            "output": str(output_path),
            "n_rows_raw": raw_row_count,
            "n_rows": int(len(df)),
            "n_dois_requested": len(doi_list),
            "n_dois_with_rows": int(df["doi"].nunique()),
            "n_unique_pairs": int(
                df[["solute_smiles", "solvent_smiles"]]
                .drop_duplicates()
                .shape[0]
            ),
            "missing_solute_smiles": int(df["solute_smiles"].isna().sum()),
            "missing_solvent_smiles": int(df["solvent_smiles"].isna().sum()),
            "archive_pages": archive_page_stats,
            "issue_indexes": issue_index_stats,
            "fetch_stats": fetch_stats,
        },
    )


if __name__ == "__main__":
    main()
