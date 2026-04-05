#!/usr/bin/env python3
"""Freeze a benchmark release manifest with checksums for splits and artifact bundles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401

from tgnn_solv.artifacts import describe_file, runtime_snapshot, write_json


def _discover_bundle_files(root: Path) -> list[dict[str, object]]:
    bundles: list[dict[str, object]] = []
    for summary_path in sorted(root.rglob("summary.csv")):
        bundle_dir = summary_path.parent
        report_path = bundle_dir / "report.json"
        predictions_path = bundle_dir / "predictions.csv"
        if not report_path.exists() and not predictions_path.exists():
            continue
        bundle = {
            "bundle_dir": str(bundle_dir),
            "summary": describe_file(summary_path, role="summary"),
            "report": describe_file(report_path, role="report") if report_path.exists() else None,
            "predictions": describe_file(predictions_path, role="predictions") if predictions_path.exists() else None,
            "run_manifest": describe_file(bundle_dir / "run_manifest.json", role="run_manifest")
            if (bundle_dir / "run_manifest.json").exists()
            else None,
            "benchmark_card": describe_file(bundle_dir / "benchmark_card.json", role="benchmark_card")
            if (bundle_dir / "benchmark_card.json").exists()
            else None,
        }
        bundles.append(bundle)
    return bundles


def _discover_processed_files(processed_dir: Path) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for path in sorted(processed_dir.glob("*.csv")):
        files.append(describe_file(path, role="processed_split"))
    manifest_path = processed_dir / "split_manifest.json"
    if manifest_path.exists():
        files.append(describe_file(manifest_path, role="split_manifest"))
    return files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a frozen benchmark release manifest with checksums."
    )
    parser.add_argument("--release-name", default="tgnn-benchmark")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--processed-dir", default="notebooks/data/processed")
    parser.add_argument("--bundle-root", action="append", default=[])
    parser.add_argument("--checkpoint", action="append", default=[])
    parser.add_argument("--out-dir", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    processed_dir = Path(args.processed_dir).expanduser().resolve()
    bundle_roots = [Path(item).expanduser().resolve() for item in args.bundle_root if item]
    if not bundle_roots:
        bundle_roots = [
            (Path("results") / "external_baselines").resolve(),
            (Path("results") / "custom_benchmarks").resolve(),
            (Path("results") / "medium_budget").resolve(),
        ]
    checkpoints = [Path(item).expanduser().resolve() for item in args.checkpoint if item]

    payload = {
        "schema_version": "1.0",
        "release_name": args.release_name,
        "version": args.version,
        "runtime": runtime_snapshot(),
        "processed_data": _discover_processed_files(processed_dir) if processed_dir.exists() else [],
        "benchmark_bundles": [
            {
                "root": str(root),
                "bundles": _discover_bundle_files(root),
            }
            for root in bundle_roots
            if root.exists()
        ],
        "checkpoints": [describe_file(path, role="checkpoint") for path in checkpoints if path.exists()],
    }
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "release_manifest.json", payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
