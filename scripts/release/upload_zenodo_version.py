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

THE INVENIORDM API, NOT THE LEGACY DEPOSIT ONE.  The first version of this script used
/api/deposit/depositions/{id}/actions/newversion, which is what most tutorials still show.  Zenodo
now runs InvenioRDM and that compatibility layer rejected the call with a validation error on a
field the caller cannot set ("files.enabled: Please remove all files first").  The flow below is
the current one: POST {record}/versions for the draft, then declare / upload / commit each file
against the draft's own file links, then PUT the metadata, then publish.

METADATA IS READ-MODIFY-WRITE, NOT WRITTEN FROM SCRATCH.  InvenioRDM's metadata schema is not the
legacy one -- creators carry person_or_org, rights carry ids, relations carry relation_type ids --
and inventing that structure from documentation is how a submission gets silently mangled.  The
draft is fetched, the fields that are wrong are replaced in the structure Zenodo itself returned,
and the result is written back.

THE TOKEN IS NEVER SEEN BY ANYTHING BUT ZENODO.  It is read from the ZENODO_TOKEN environment
variable and sent in an Authorization header.  It is deliberately NOT accepted as a command-line
argument -- argv is visible in `ps` and lands in shell history -- and never placed in a URL, where
it would be logged by every proxy on the path.

    set -a; . ./.env; set +a                      # or export ZENODO_TOKEN=...
    python scripts/release/build_zenodo_bundle.py # stage it first, if not already staged
    python scripts/release/upload_zenodo_version.py --dry-run   # what would happen, no writes
    python scripts/release/upload_zenodo_version.py             # create the draft and upload
    python scripts/release/upload_zenodo_version.py --publish   # ... and publish it

PUBLISHING IS IRREVERSIBLE.  A published Zenodo version cannot be withdrawn, only superseded, so
--publish is opt-in and the default stops at a draft that can be inspected in the browser first.

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

#: The concept DOI the manuscript prints, for display only.
CONCEPT_RECORD = "22263434"

#: The published VERSION the API is anchored on.
#:
#: NOT THE CONCEPT ID.  GET /api/records/22263434 used to redirect to the latest version; after a
#: new-version draft existed it began answering 410 "The record has been deleted" instead, because
#: a concept id names a parent and not a retrievable record. The public citation path is unaffected
#: -- doi.org/10.5281/zenodo.22263434 still lands on the latest version, checked end to end -- but
#: anchoring API calls on the concept id makes the script fail for a reason that has nothing to do
#: with the deposit. It anchors on a published version and asks that for the latest one.
ANCHOR_RECORD = "22263435"

#: How the 385 staged files are grouped into archives. prefix -> archive name.
GROUPS = {
    "checkpoints": "checkpoints.tar.gz",
    "results": "results.tar.gz",
    "notebooks": "processed_split.tar.gz",
}
#: Left loose at the top level of the record, so a reader sees them without downloading anything.
LOOSE = ["MANIFEST.sha256", "README.md"]

#: Where the id of the new-version draft is remembered between runs.
#:
#: RETRIES MUST NOT CREATE A SECOND DRAFT.  The first attempt against this record hit an HTTP 500
#: from Zenodo -- and the draft was created anyway.  The next run therefore asked for another new
#: version, which 500'd again because one already existed, and the half-made draft could not even be
#: read back (GET returned 500, DELETE returned 504 and then succeeded silently).  Zenodo does not
#: list an unpublished new-version draft under {record}/versions, so there is nothing to discover it
#: from; the id is written here instead, and --draft overrides it.
DRAFT_STATE = PACKED / ".draft_id"


def _call(method: str, url: str, token: str, payload=None) -> dict:
    data = json.dumps(payload).encode("utf8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")          # never in the URL
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as fh:
            body = fh.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf8", "replace")[:800]
        raise SystemExit(f"FAIL: {method} {url} -> HTTP {exc.code}\n  {detail}")


def _put_content(url: str, path: Path, token: str) -> None:
    """Stream a file body into the draft, rather than reading 300 MB into memory.

    THE BODY MUST BE PASSED TO THE CONSTRUCTOR, NOT ASSIGNED AFTERWARDS.  The first version of
    this built the Request, added a Content-Length header, and then set `req.data = fh`.  CPython's
    `Request.data` setter REMOVES any Content-Length already on the request (bpo-16464), so the
    body went out with no length and Zenodo stored nothing: the upload returned success and the
    commit then failed with "Empty files are not accepted".  A silent zero-byte upload is exactly
    the failure that would have put an empty archive behind the DOI the manuscript cites.
    """
    size = path.stat().st_size
    with path.open("rb") as fh:
        req = urllib.request.Request(url, data=fh, method="PUT")   # data first...
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/octet-stream")
        req.add_header("Content-Length", str(size))                # ...then the length survives
        try:
            with urllib.request.urlopen(req, timeout=7200):
                pass
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf8", "replace")[:500]
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


def _description() -> str:
    readme = STAGED / "README.md"
    if not readme.exists():
        return ("<p>Code and data deposit for the manuscript: trained weights, the processed "
                "split and the per-arm predictions every reported number is computed from.</p>")
    paras = [p.replace("\n", " ").strip()
             for p in readme.read_text(encoding="utf8").split("\n\n")[1:4]]
    return "<p>" + "</p><p>".join(p for p in paras if p) + "</p>"


def patch_metadata(md: dict) -> dict:
    """Replace the fields that took Zenodo's defaults, inside the structure Zenodo returned."""
    md = json.loads(json.dumps(md))                              # do not mutate the caller's copy
    md["title"] = ("Ground Truth That Does Not Ground: Substituting Reference Solvent "
                   "σ-Profiles Degrades COSMO-SAC Solubility Prediction — code and data")
    md["description"] = _description()
    md["version"] = "v1.0.0"
    md["publisher"] = "Zenodo"
    md["resource_type"] = {"id": "dataset"}
    md["rights"] = [{"id": "mit"}]
    md["creators"] = [
        {"person_or_org": {"type": "personal", "family_name": "Polomoshnov",
                           "given_name": "Nikita L.",
                           "identifiers": [{"scheme": "orcid",
                                            "identifier": "0009-0001-4342-8539"}]},
         "affiliations": [{"name": "Faculty of Bioengineering and Bioinformatics, Lomonosov "
                                   "Moscow State University, Moscow, Russia"},
                          {"name": "V. N. Orekhovich Institute of Biomedical Chemistry, Moscow, "
                                   "Russia"}]},
        {"person_or_org": {"type": "personal", "family_name": "Rudik",
                           "given_name": "Anastasiya V."},
         "affiliations": [{"name": "V. N. Orekhovich Institute of Biomedical Chemistry, Moscow, "
                                   "Russia"}]},
    ]
    md["subjects"] = [{"subject": s} for s in
                      ["solubility prediction", "physics-informed machine learning", "COSMO-SAC",
                       "infinite-dilution activity coefficients", "model misspecification"]]
    md["related_identifiers"] = [
        {"identifier": "https://github.com/doctawho42/tgnn-solv/tree/v1.0.0",
         "scheme": "url", "relation_type": {"id": "isderivedfrom"}},
        {"identifier": "10.5281/zenodo.15094979", "scheme": "doi",
         "relation_type": {"id": "isderivedfrom"}, "resource_type": {"id": "dataset"}},
    ]
    md["notes"] = ("The processed train/validation/test split is derived from BigSolDB 2.0 "
                   "(doi:10.5281/zenodo.15094979), released under CC-BY-4.0, and is redistributed "
                   "here with attribution; everything else is MIT, matching LICENSE at the "
                   "repository root. The raw solubility corpus and the VT-2005 and UD "
                   "σ-profile databases are NOT redistributed; the manuscript cites them. "
                   "Funding: Russian Science Foundation, project No. 25-25-00148 "
                   "(https://rscf.ru/project/25-25-00148/).")
    return md


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="show the plan, write nothing to Zenodo")
    ap.add_argument("--publish", action="store_true",
                    help="publish the new version. IRREVERSIBLE: a published version cannot be "
                         "withdrawn, only superseded.")
    ap.add_argument("--draft", metavar="ID",
                    help="reuse this existing new-version draft instead of creating one. Defaults "
                         "to the id remembered from the last run.")
    args = ap.parse_args()

    files = pack()
    total = sum(f.stat().st_size for f in files)
    print(f"to upload, from {PACKED}:")
    for f in files:
        print(f"  {f.stat().st_size/1e6:9.1f} MB  {f.name}")
    print(f"  {total/1e6:9.1f} MB  total, {len(files)} file(s)")
    print(f"\ntarget: new version of Zenodo record {CONCEPT_RECORD} "
          f"(concept DOI 10.5281/zenodo.{CONCEPT_RECORD})")

    if args.dry_run:
        print("\ndry run: nothing was sent to Zenodo.")
        return 0

    token = os.environ.get("ZENODO_TOKEN", "").strip()
    if not token:
        print("\nFAIL: ZENODO_TOKEN is not set.\n"
              "  Create a personal access token at zenodo.org/account/settings/applications with\n"
              "  the deposit:write and deposit:actions scopes, then put it in the environment.\n"
              "  It is sent to Zenodo in an Authorization header and is never written to disk,\n"
              "  logged, or passed on the command line by this script.")
        return 1

    latest = _call("GET", f"{API}/records/{ANCHOR_RECORD}/versions/latest", token)
    rec_id = latest["id"]
    print(f"\nlatest published version: {latest.get('doi')} (record {rec_id})")

    remembered = args.draft or (DRAFT_STATE.read_text().strip()
                                if DRAFT_STATE.exists() else None)
    draft = None
    if remembered:
        try:
            draft = _call("GET", f"{API}/records/{remembered}/draft", token)
            print(f"reusing draft {remembered}")
        except SystemExit:
            print(f"draft {remembered} is not readable; creating a new version instead")
    if draft is None:
        draft = _call("POST", f"{API}/records/{rec_id}/versions", token)
        DRAFT_STATE.write_text(str(draft["id"]))
        print(f"draft created: {draft['id']}")
    links = draft["links"]
    print(f"  {links.get('self_html', links['self'])}")

    listing = _call("GET", links["files"], token).get("entries", [])
    entries = (listing if isinstance(listing, dict)
               else {f["key"]: f for f in listing})
    existing = {k for k, v in entries.items() if v.get("status") == "completed"}
    # A declared-but-not-committed entry blocks re-declaring the same key, so a retry after a
    # failed body upload has to clear it first. This is what the zero-length upload left behind.
    for key, meta in entries.items():
        if meta.get("status") != "completed":
            _call("DELETE", f"{links['files']}/{key}", token)
            print(f"  cleared incomplete entry {key}")
    to_send = [f for f in files if f.name not in existing]
    if existing:
        print(f"  draft already carries: {sorted(existing)}")

    if to_send:
        _call("POST", links["files"], token, [{"key": f.name} for f in to_send])
        for f in to_send:
            print(f"  uploading {f.name} ({f.stat().st_size/1e6:.0f} MB) ...", flush=True)
            _put_content(f"{links['files']}/{f.name}/content", f, token)
            _call("POST", f"{links['files']}/{f.name}/commit", token)

    updated = _call("PUT", links["self"], token,
                    {**draft, "metadata": patch_metadata(draft.get("metadata", {}))})
    print(f"metadata set: {updated.get('metadata', {}).get('title', '')[:60]}...")

    if not args.publish:
        print(f"\nDRAFT READY, NOT PUBLISHED\n  {links.get('self_html', links['self'])}\n"
              "  Inspect it, then publish in the browser or re-run with --publish.\n"
              "  Publishing is irreversible.")
        return 0

    published = _call("POST", links["publish"], token)
    print(f"\npublished: {published.get('links', {}).get('doi') or published.get('id')}")
    print("now confirm the manuscript's promise is true:")
    print("    python scripts/analysis/check_zenodo_record.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
