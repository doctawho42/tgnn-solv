#!/usr/bin/env python
"""Assemble the Zenodo deposit, and derive its contents from the document that defines them.

WHY IT IS DERIVED AND NOT LISTED.  ZENODO_DEPOSIT.md used to carry a hand-written table of what to
upload.  It was written on 2026-07-27 and by 2026-09-03 it named `results/e5_sigma_grounding/seed_4
{2,3,4}` -- the THREE-seed family -- while every headline number in the manuscript had moved to the
five-seed leak-free family in `results/e5_sigma_grounding_leakfree/`.  A deposit built from that
table would have archived artifacts the paper's numbers are not computed from, which is the same
defect as citing a figure drawn from the wrong run, and a referee downloading it would have found a
different arm behind the number.  So the analysis half of the deposit is read out of DEPOSITS.md,
the file that maps each printed claim to its artifact and is itself gated by check_doc_paths.py.
Add a claim there and the deposit follows it.

WHAT IS NOT DERIVED.  Model weights are not named in DEPOSITS.md (it maps numbers to the JSON and
CSV they were read from, not to the checkpoints those were produced by), so CHECKPOINTS below is
explicit, with the reason each one is in the archive.  Same for the processed split.

    python scripts/release/build_zenodo_bundle.py --dry-run     # the plan and the total size
    python scripts/release/build_zenodo_bundle.py               # stage it under dist/

The staged tree is what gets uploaded.  MANIFEST.sha256 goes up with it, so a reader can verify
every file they downloaded against the record rather than trusting the byte count.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: NEVER stage the results root itself.  DEPOSITS.md contains paths such as `results/.gitkeep`
#: whose parent directory is `results`, and staging that parent sweeps in 3.4 GB of local scratch
#: -- fourteen times the deposit -- most of it runs that no printed number depends on.
FORBIDDEN_ROOTS = {"results", "checkpoints", "notebooks", "notebooks/data", "."}

#: weights, which DEPOSITS.md does not name.  path -> why a reader needs it.
CHECKPOINTS = {
    "checkpoints/e5_leakfree":
        "the five leak-free seeds behind the headline substitution result (1.93 -> 2.34)",
    "checkpoints/cosmo_sac/tgnn_cosmo.pt":
        "the COSMO-SAC reference arm the closure contrasts are scored against",
    "results/closure_fix/ckpt":
        "the closure-fix arms",
    "checkpoints/e5_current_split":
        "the current-split arms the earlier three-seed family was scored on, kept so the "
        "retired values in the manuscript remain checkable",
}

#: everything else, explicitly.  path -> why.
EXTRA = {
    "notebooks/data/processed":
        "the processed train/val/test split every reported number is measured on; the "
        "solute-scaffold split is not reproducible across pipeline versions, so the files "
        "themselves are the only way to land on the same rows",
}

#: third-party material that must NOT go up.  Redistribution terms are theirs, not ours.
EXCLUDE_NAMES = {"BigSolDBv2.1.csv", "bradley_mp.csv"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _from_deposits() -> dict[str, str]:
    """Artifact paths named in DEPOSITS.md, as path -> the reason DEPOSITS.md gives by naming it."""
    text = (ROOT / "DEPOSITS.md").read_text(encoding="utf8")
    found: dict[str, str] = {}
    for raw in sorted(set(re.findall(r"`((?:results|notebooks)/[^`]+)`", text))):
        rel = raw.rstrip("/")
        p = ROOT / rel
        target = rel if p.is_dir() else str(Path(rel).parent)
        if target in FORBIDDEN_ROOTS:
            # a file sitting directly in results/ -- take the file, never its parent
            target = rel if p.is_file() else None
        if target:
            found.setdefault(target, "named in DEPOSITS.md as the artifact behind a printed claim")
    return found


def _walk(rel: str) -> list[Path]:
    p = ROOT / rel
    if p.is_file():
        return [p]
    return sorted(f for f in p.rglob("*") if f.is_file() and f.name not in EXCLUDE_NAMES)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "dist/zenodo")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    plan: dict[str, str] = {}
    plan.update(_from_deposits())
    plan.update(CHECKPOINTS)
    plan.update(EXTRA)

    missing = [rel for rel in plan if not (ROOT / rel).exists()]
    if missing:
        print("FAIL: the deposit names paths that are not on disk. Build them or fix the list:")
        for rel in missing:
            print(f"  {rel}")
        return 1

    total, files = 0, 0
    print(f"{'size':>10}  {'files':>6}  item")
    for rel in sorted(plan):
        fs = _walk(rel)
        size = sum(f.stat().st_size for f in fs)
        total += size
        files += len(fs)
        print(f"{size/1e6:9.1f}M  {len(fs):6d}  {rel}")
    print(f"{total/1e6:9.1f}M  {files:6d}  TOTAL"
          f"   (Zenodo's per-record limit is 50 GB)")

    if args.dry_run:
        return 0

    out = args.out
    if out.exists():
        shutil.rmtree(out)
    manifest: list[str] = []
    for rel in sorted(plan):
        for src in _walk(rel):
            dst = out / src.relative_to(ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            manifest.append(f"{_sha256(src)}  {src.relative_to(ROOT)}")
    (out / "MANIFEST.sha256").write_text("\n".join(manifest) + "\n", encoding="utf8")
    (out / "README.md").write_text(_archive_readme(plan, total, files), encoding="utf8")
    print(f"\nstaged at {out}")
    print("verify a download with:  shasum -c MANIFEST.sha256")
    return 0


def _archive_readme(plan: dict[str, str], total: int, files: int) -> str:
    lines = [
        "# Ground Truth That Does Not Ground -- code and data",
        "",
        "Artifacts too large to version, deposited alongside the manuscript. The analysis code is",
        "at <https://github.com/doctawho42/tgnn-solv> under the MIT licence; this archive holds the",
        "trained weights, the processed split and the per-arm predictions every reported number is",
        "computed from.",
        "",
        f"{files} files, {total/1e6:.0f} MB. `MANIFEST.sha256` lists a checksum for each; verify a",
        "download with `shasum -c MANIFEST.sha256`.",
        "",
        "## What is here, and why",
        "",
        "| path | why it is in the archive |",
        "|---|---|",
    ]
    lines += [f"| `{rel}` | {why} |" for rel, why in sorted(plan.items())]
    lines += [
        "",
        "## What is deliberately absent",
        "",
        "The raw solubility corpus (BigSolDB) and the VT-2005 and UD sigma-profile databases are",
        "third party and redistributable only on their own terms. The manuscript cites them and the",
        "repository documents how to fetch them.",
        "",
        "## Reproducing a number",
        "",
        "Clone the repository at the commit named in the manuscript's Data and Software",
        "Availability statement, unpack this archive over the working tree so that `results/` and",
        "`checkpoints/` sit where the scripts expect them, then run the script `DEPOSITS.md` names",
        "for the claim in question. `./verify.sh` re-runs every gate that binds a printed number to",
        "its artifact.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
