#!/usr/bin/env python
"""The Zenodo record the manuscript prints must hold what the manuscript says it holds.

WHY THIS EXISTS.  On 2026-09-03 the DOI came back and the record behind it held two files,
18 MB: the source archive that a GitHub release produces.  The sentence that cites it promises
"the model checkpoints, the processed split, the full per-arm prediction files and the larger
analysis artifacts" -- 685 MB in 385 files, none of which is in a git tree, because all of it is
gitignored.  The DOI resolved, the manuscript compiled, every other gate stayed green, and a
referee following the citation would have found the code and not one checkpoint.

ZENODO_DEPOSIT.md warned about exactly this in prose.  Prose does not fail a build.

WHAT IS CHECKED.  The DOI printed in the Data and Software Availability statement is read out of
the manuscript, resolved through Zenodo's public API, and the record's file list is compared
against the deposit that scripts/release/build_zenodo_bundle.py stages.  A record whose payload is
only the GitHub source archive fails.

NETWORK.  This gate needs the internet and is therefore NOT in verify.sh, which must pass offline.
Run it before submission, and after any new version is published:

    python scripts/analysis/check_zenodo_record.py

Exit 0 means the citation is honest.  Exit 2 means the check could not run (no network); that is
not a pass, and it says so.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "paper/grounding_paradox.tex"

#: What the manuscript's sentence promises the archive contains, as regexes over the paths of the
#: ORIGINAL files -- read from the record's own MANIFEST.sha256, not from the names of the files
#: attached to it.
#:
#: WHY THE MANIFEST AND NOT THE FILE NAMES.  The first version of this gate matched substrings
#: against the attached file names, which worked while the deposit was going up as 385 loose files.
#: The deposit is uploaded packed -- three archives -- and the same gate then reported the record
#: as missing the per-arm predictions, which were sitting inside results.tar.gz all along. It was
#: measuring the wrong surface: a false alarm on a complete record is as bad as silence on an
#: incomplete one, because the next person learns to ignore it. The manifest lists every original
#: path and travels with the deposit, so it answers the question the sentence actually asks.
EXPECTED_KINDS = {
    "model checkpoints": r"checkpoints/.*\.pt$",
    "processed split": r"processed/(train|val|test)\.csv$",
    "per-arm predictions": r"seed_4\d/.*predictions\.csv$",
}
#: The GitHub release archive, which is what an auto-archived record holds and by itself is not
#: the deposit. Named so the failure message can say precisely what went wrong.
RELEASE_ARCHIVE = re.compile(r"tgnn-solv-[\d.]+\.(?:tar\.gz|zip)$")


def _doi_from_manuscript() -> str:
    text = "\n".join(l for l in ARTICLE.read_text(encoding="utf8").split("\n")
                     if not l.lstrip().startswith("%"))
    m = re.search(r"10\.5281/zenodo\.(\d+)", text)
    if not m:
        print("FAIL: the manuscript prints no Zenodo DOI at all")
        sys.exit(1)
    return m.group(0)


def _record(doi: str) -> dict:
    rec_id = doi.rsplit(".", 1)[1]
    url = f"https://zenodo.org/api/records/{rec_id}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as fh:      # follows the concept -> version hop
        return json.load(fh)


def main() -> int:
    doi = _doi_from_manuscript()
    print(f"manuscript cites {doi}")
    try:
        rec = _record(doi)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"COULD NOT CHECK: {exc}. This is not a pass -- run it again with a network.")
        return 2

    entries = rec.get("files", [])
    files = [f.get("key", "") for f in entries]
    total = sum(f.get("size", 0) for f in entries)
    print(f"resolves to {rec.get('doi')} -- {len(files)} file(s), {total/1e6:.0f} MB")

    only_release = files and all(RELEASE_ARCHIVE.search(f) for f in files)

    # The manifest indexes the original files, whether they went up loose or packed.
    paths, source = files, "the attached file names"
    manifest = next((f for f in entries if f.get("key") == "MANIFEST.sha256"), None)
    if manifest:
        try:
            with urllib.request.urlopen(manifest["links"]["self"], timeout=120) as fh:
                paths = [line.split("  ", 1)[1]
                         for line in fh.read().decode("utf8").strip().split("\n") if "  " in line]
            source = f"MANIFEST.sha256 on the record ({len(paths)} original files)"
        except (urllib.error.URLError, OSError, KeyError, IndexError) as exc:
            print(f"  could not read the manifest ({exc}); falling back to file names")
    print(f"checked against {source}")

    missing = [kind for kind, pattern in EXPECTED_KINDS.items()
               if not any(re.search(pattern, p) for p in paths)]

    if only_release:
        print("\nFAIL: the record holds only the GitHub release archive.\n")
        print("  The statement in the manuscript promises the checkpoints, the processed split and")
        print("  the per-arm predictions. Those are gitignored, so no release archive can contain")
        print("  them. Stage the deposit and upload it as a NEW VERSION of this record:\n")
        print("      python scripts/release/build_zenodo_bundle.py")
        print("\n  A new version keeps the concept DOI the manuscript prints, so nothing in the")
        print("  text has to change once it is published. See ZENODO_DEPOSIT.md.")
        return 1
    if missing:
        print(f"\nFAIL: the record does not appear to carry: {', '.join(missing)}")
        for f in paths[:20]:
            print(f"    {f}")
        return 1
    for kind, pattern in EXPECTED_KINDS.items():
        n = sum(1 for p in paths if re.search(pattern, p))
        print(f"  {kind:22s} {n:3d} file(s)")
    print("ok: the record carries the artifacts the manuscript's statement promises")
    return 0


if __name__ == "__main__":
    sys.exit(main())
