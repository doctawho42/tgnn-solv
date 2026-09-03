#!/usr/bin/env python
"""Upload the staged deposit to Zenodo as a NEW VERSION of the record the manuscript cites.

WHY A NEW VERSION AND NOT A NEW RECORD.  The manuscript prints the concept DOI
10.5281/zenodo.22263434, which always resolves to the latest version of that record.  Publishing a
new version therefore completes the citation without changing a character of the text.  A separate
record would mint a DOI the manuscript does not name, and the sentence would stay false.

WHY THIS EXISTS AT ALL.  The record as published holds the 18 MB source archive a GitHub release
produces.  The Data and Software Availability statement promises the model checkpoints, the
processed split and the full per-arm prediction files: 685 MB that cannot be in a git archive
because all of it is gitignored.  Referees follow that DOI during review, so the gap is a
review-window problem.  scripts/analysis/check_zenodo_record.py fails until this script has run.

THE TOKEN IS NEVER SEEN BY ANYTHING BUT ZENODO.  It is read from the ZENODO_TOKEN environment
variable and sent in an Authorization header.  It is deliberately NOT accepted as a command-line
argument -- argv is visible in `ps` and lands in shell history -- and never placed in a URL, where
it would be logged by every proxy on the path.

    export ZENODO_TOKEN=...                       # from zenodo.org/account/settings/applications
    python scripts/release/build_zenodo_bundle.py # stage it first, if not already staged
    python scripts/release/upload_zenodo_version.py --dry-run   # what would happen, no writes
    python scripts/release/upload_zenodo_version.py             # create the draft and upload
    python scripts/release/upload_zenodo_version.py --publish    # ... and publish it

PUBLISHING IS IRREVERSIBLE.  A published Zenodo version cannot be withdrawn, only superseded, so
--publish is opt-in and the default stops at a draft you can inspect in the browser first.

WHY THE FILES ARE PACKED.  The staged deposit is 385 files.  A Zenodo record listing 385 entries is
unusable in a browser and slow to download one by one, so they go up as a few archives grouped the
way a reader would want them, with MANIFEST.sha256 and README.md left loose at the top level.  The
manifest lists the sha256 of each ORIGINAL file, so a reader who unpacks the archives can still
verify every one of them.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGED = ROOT / "dist" / "zenodo"
PACKED = ROOT / "dist" / "zenodo_upload"
API = "https://zenodo.org/api"

#: The concept DOI the manuscript prints. The record id is its final component.
CONCEPT_RECORD = "22263434"

#: How the 385 staged files are grouped into archives. prefix -> archive name.
GROUPS = {
    "checkpoints": "checkpoints.tar.gz",
    "results": "results.tar.gz",
    "notebooks": "processed_split.tar.gz",
}
#: Left loose at the top level of the record, so a reader sees them without downloading anything.
LOOSE = ["MANIFEST.sha256", "README.md"]


def _req(method: str, url: str, token: str, data: bytes | None = None,
         content_type: str = "application/json") -> dict:
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")      # never in the URL
    if data is not None:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=300) as fh:
            body = fh.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf8", "replace")[:600]
        raise SystemExit(f"FAIL: {method} {url.split('?')[0]} -> HTTP {exc.code}\n  {detail}")


def _upload_file(bucket: str, path: Path, token: str) -> None:
    """PUT a file into the draft's bucket, streaming rather than reading it into memory."""
    size = path.stat().st_size
    req = urllib.request.Request(f"{bucket}/{path.name}", method="PUT")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/octet-stream")
    req.add_header("Content-Length", str(size))
    with path.open("rb") as fh:
        req.data = fh                                        # urllib streams a file object
        try:
            with urllib.request.urlopen(req, timeout=3600):
                pass
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf8", "replace")[:400]
            raise SystemExit(f"FAIL: uploading {path.name} -> HTTP {exc.code}\n  {detail}")


def pack() -> list[Path]:
    """Group the staged tree into archives. Returns everything to upload."""
    if not STAGED.is_dir():
        raise SystemExit(f"FAIL: nothing staged at {STAGED}. Run build_zenodo_bundle.py first.")
    PACKED.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for prefix, archive in GROUPS.items():
        src = STAGED / prefix
        if not src.is_dir():
            continue
        dst = PACKED / archive
        if not dst.exists():
            with tarfile.open(dst, "w:gz") as tar:
                tar.add(src, arcname=prefix)
        out.append(dst)
    for name in LOOSE:
        src = STAGED / name
        if src.exists():
            dst = PACKED / name
            dst.write_bytes(src.read_bytes())
            out.append(dst)
    return out


def metadata() -> dict:
    """The record metadata, fixing the eight fields that took Zenodo's defaults."""
    readme = STAGED / "README.md"
    description = ("<p>Code and data deposit for the manuscript. See the README in this record for "
                   "the full contents and how to reproduce a number.</p>")
    if readme.exists():
        first = readme.read_text(encoding="utf8").split("\n\n")[1:3]
        description = "<p>" + "</p><p>".join(p.replace("\n", " ") for p in first) + "</p>"
    return {
        "title": ("Ground Truth That Does Not Ground: Substituting Reference Solvent "
                  "σ-Profiles Degrades COSMO-SAC Solubility Prediction — code and data"),
        "upload_type": "dataset",
        "description": description,
        "version": "v1.0.0",
        "license": "mit",
        "creators": [
            {"name": "Polomoshnov, Nikita L.",
             "orcid": "0009-0001-4342-8539",
             "affiliation": ("Faculty of Bioengineering and Bioinformatics, Lomonosov Moscow "
                             "State University, Moscow, Russia")},
            {"name": "Rudik, Anastasiya V.",
             "affiliation": ("V. N. Orekhovich Institute of Biomedical Chemistry, Moscow, "
                             "Russia")},
        ],
        "keywords": ["solubility prediction", "physics-informed machine learning", "COSMO-SAC",
                     "infinite-dilution activity coefficients", "model misspecification"],
        "related_identifiers": [
            {"identifier": "https://github.com/doctawho42/tgnn-solv/tree/v1.0.0",
             "relation": "isDerivedFrom", "scheme": "url"},
            {"identifier": "10.5281/zenodo.15094979", "relation": "isDerivedFrom",
             "scheme": "doi", "resource_type": "dataset"},
        ],
        "notes": ("The processed train/validation/test split is derived from BigSolDB 2.0 "
                  "(doi:10.5281/zenodo.15094979), released under CC-BY-4.0, and is redistributed "
                  "here with attribution; everything else is MIT, matching LICENSE at the "
                  "repository root. The raw solubility corpus and the VT-2005 and UD sigma-profile "
                  "databases are NOT redistributed. Funding: Russian Science Foundation, project "
                  "No. 25-25-00148 (https://rscf.ru/project/25-25-00148/)."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show the plan, write nothing to Zenodo")
    ap.add_argument("--publish", action="store_true",
                    help="publish the new version. IRREVERSIBLE: a published version cannot be "
                         "withdrawn, only superseded.")
    ap.add_argument("--drop-inherited", action="store_true",
                    help="delete the files the new version inherits (the 18 MB GitHub release "
                         "archive). They are kept by default: the record is more useful with the "
                         "source beside the artifacts than without it.")
    args = ap.parse_args()

    files = pack()
    total = sum(f.stat().st_size for f in files)
    print(f"to upload, from {PACKED}:")
    for f in files:
        print(f"  {f.stat().st_size/1e6:9.1f} MB  {f.name}")
    print(f"  {total/1e6:9.1f} MB  total, {len(files)} file(s)")
    print(f"\ntarget: new version of Zenodo record {CONCEPT_RECORD} "
          f"(concept DOI 10.5281/zenodo.{CONCEPT_RECORD})")
    print("metadata to be set:")
    md = metadata()
    for k in ("title", "upload_type", "license", "version"):
        print(f"  {k}: {md[k]}")

    if args.dry_run:
        print("\ndry run: nothing was sent to Zenodo.")
        return 0

    token = os.environ.get("ZENODO_TOKEN", "").strip()
    if not token:
        print("\nFAIL: ZENODO_TOKEN is not set.\n"
              "  Create a personal access token at zenodo.org/account/settings/applications with\n"
              "  the deposit:write and deposit:actions scopes, then:\n"
              "      export ZENODO_TOKEN=...        (in your shell, not in a file in this repo)\n"
              "  The token is sent to Zenodo in an Authorization header and is never written to\n"
              "  disk, logged, or passed on the command line by this script.")
        return 1

    latest = _req("GET", f"{API}/records/{CONCEPT_RECORD}", token)
    dep_id = latest.get("id")
    print(f"\nlatest published version: {latest.get('doi')} (deposition {dep_id})")

    draft = _req("POST", f"{API}/deposit/depositions/{dep_id}/actions/newversion", token)
    draft_url = draft.get("links", {}).get("latest_draft")
    if not draft_url:
        raise SystemExit("FAIL: Zenodo did not return a draft link for the new version")
    draft = _req("GET", draft_url, token)
    draft_id, bucket = draft["id"], draft["links"]["bucket"]
    print(f"draft created: deposition {draft_id}")

    if args.drop_inherited:
        for f in draft.get("files", []):
            _req("DELETE", f"{API}/deposit/depositions/{draft_id}/files/{f['id']}", token)
            print(f"  removed inherited {f.get('filename', f.get('key'))}")

    for f in files:
        print(f"  uploading {f.name} ({f.stat().st_size/1e6:.0f} MB) ...", flush=True)
        _upload_file(bucket, f, token)

    _req("PUT", f"{API}/deposit/depositions/{draft_id}",
         token, json.dumps({"metadata": metadata()}).encode("utf8"))
    print("metadata set")

    if not args.publish:
        print(f"\nDRAFT READY, NOT PUBLISHED: https://zenodo.org/deposit/{draft_id}\n"
              "  Check it in the browser, then publish there, or re-run this with --publish.\n"
              "  Publishing is irreversible.")
        return 0

    published = _req("POST", f"{API}/deposit/depositions/{draft_id}/actions/publish", token)
    print(f"\npublished: {published.get('doi_url') or published.get('doi')}")
    print("now confirm the manuscript's promise is true:")
    print("    python scripts/analysis/check_zenodo_record.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
