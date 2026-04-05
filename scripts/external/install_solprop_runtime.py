#!/usr/bin/env python3
"""Download and extract the SolProp runtime package with pretrained model files."""

from __future__ import annotations

import argparse
import json
import tarfile
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = REPO_ROOT / "benchmarks" / "external_runtimes" / "solprop_ml"
PACKAGE_URLS = {
    "solprop_ml": "https://conda.anaconda.org/fhvermei/noarch/solprop_ml-1.2-py_1.tar.bz2",
    "chemprop_solvation": "https://conda.anaconda.org/fhvermei/noarch/chemprop_solvation-0.0.3-py_0.tar.bz2",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install the SolProp runtime package locally without mutating the active conda environment."
    )
    parser.add_argument("--target-dir", default=str(DEFAULT_TARGET))
    parser.add_argument("--force-download", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    target_dir = Path(args.target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    archives: dict[str, str] = {}
    for package_name, url in PACKAGE_URLS.items():
        archive_path = target_dir / Path(url).name
        if args.force_download or not archive_path.exists():
            print(f"Downloading {url} -> {archive_path}")
            urllib.request.urlretrieve(url, archive_path)
        print(f"Extracting {archive_path} -> {target_dir}")
        with tarfile.open(archive_path, "r:bz2") as tf:
            tf.extractall(target_dir)
        archives[package_name] = str(archive_path)

    egg_candidates = sorted(target_dir.glob("site-packages/*.egg"))
    manifest = {
        "archives": archives,
        "target_dir": str(target_dir),
        "egg_path": str(egg_candidates[0]) if egg_candidates else None,
        "site_packages": str(target_dir / "site-packages"),
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
