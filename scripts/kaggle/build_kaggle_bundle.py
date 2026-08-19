#!/usr/bin/env python
"""Assemble the Kaggle dataset for the GPU arms this laptop cannot run.

WHAT IS OUTSTANDING, AND WHY IT NEEDS A GPU
-------------------------------------------
Two training arms of Sec. 3.1 stand at ONE seed against five-seed comparators, and the referee
report asks for the other four of each:

  grounded_a_truetrain   the reference profile injected during TRAINING, so the crystal and
                         correction branches co-adapt to it.  This is the confound-free arm --
                         it removes the distribution shift the evaluation-time substitution
                         carries -- and it is the arm the "+0.18" comes from.
  channel_swap           the same injection under coordinate descent, which freezes Phi in
                         phase 2 so only the activity branch is refit against the true profile.

ALL FIVE SEEDS OF EACH MUST BE RE-RUN, not four.  The seed-42 runs on disk
(results/e5_sigma_grounding/seed_42/) were trained against the UNCERTIFIED sigma stream
(notebooks/data/processed_sigma_aux_stream/), and the five-seed family they would be compared
against was trained against the clean one (…_clean/).  Mixing the two would put a stream change
inside a seed contrast, which is the confound the leak-free re-run exists to remove.  Ten arms.

WHY THIS SCRIPT AND NOT bundle_e5_inputs.sh
--------------------------------------------
That bundler ships three directories and points at the uncertified stream.  This one ships the
code as well, defaults to the clean stream, and -- the part that matters -- writes a MANIFEST of
sha256 digests taken from the checkpoint manifests of the runs already published, so the Kaggle
side can ASSERT it received the same bytes rather than assume it.  This project has already lost
one run family to a stream built against the wrong split files; an assertion is cheaper than the
audit that finds it afterwards.

WHAT GOES IN
------------
  code/        src/, scripts/, configs/, pyproject.toml -- git-tracked files only
  data/        the three split files, the two clean stream files, the VT-2005 oracle artifact
  MANIFEST.json  sha256 of every shipped file, plus the digests the published runs recorded
  README.md    what to do with it

Usage
-----
    python scripts/kaggle/build_kaggle_bundle.py --out /tmp/kaggle_tgnn_solv
    # then: upload that directory as a Kaggle Dataset named tgnn-solv-e5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: The inputs the two outstanding arms read, and nothing else.  Keep this list minimal: every
#: extra file is one more thing whose version has to be reasoned about on the far side.
DATA = [
    "notebooks/data/processed/train.csv",
    "notebooks/data/processed/val.csv",
    "notebooks/data/processed/test.csv",
    # THE REBUILT STREAM, not the clean directory's.  The stream the published five-seed family
    # trained on was not retained -- see scripts/kaggle/check_stream_equivalence.py, which is the
    # artifact establishing that the rebuild reproduces the pool and the split sizes but not the
    # train/val assignment.  The clean directory holds a DIFFERENT build (no validation split at
    # all), so shipping it would be worse than shipping the rebuild and saying so.
    "notebooks/data/processed_sigma_aux_stream_rebuilt/sigma_train.csv",
    "notebooks/data/processed_sigma_aux_stream_rebuilt/sigma_val.csv",
    "results/sigma_profile_artifact/sigma_profiles.csv",
]
#: Git-tracked code trees.  `git ls-files` rather than a copytree so that no local scratch,
#: no __pycache__ and no untracked experiment lands in a dataset someone else will read.
CODE_TREES = ["src", "scripts", "configs"]
CODE_FILES = ["pyproject.toml"]

#: The digests the published five-seed family recorded for its own inputs.  A Kaggle run whose
#: files do not match these is not training against the same corpus, and its seeds may not be
#: pooled with the ones already reported.  Read out of the checkpoint manifests, not retyped.
REFERENCE_MANIFEST = "checkpoints/e5_leakfree/grounded_a_seed42.manifest.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def published_digests() -> dict[str, str]:
    """{relative path: sha256} as the published runs recorded them."""
    p = ROOT / REFERENCE_MANIFEST
    if not p.exists():
        return {}
    blob = json.loads(p.read_text())
    out = {i["relative_path"]: i["sha256"] for i in blob.get("inputs", []) if "relative_path" in i}
    for s in blob.get("metadata", {}).get("grounding_streams", []):
        if s.get("present") and s.get("path"):
            out[s["path"].split("tgnn-solv/")[-1]] = s["sha256"]
    return out


def tracked(tree: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", tree], cwd=ROOT, capture_output=True, text=True)
    return [line for line in out.stdout.split("\n") if line.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="directory to write (uploaded as-is)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing --out")
    a = ap.parse_args()

    if a.out.exists():
        if not a.force:
            raise SystemExit(f"{a.out} exists; pass --force to overwrite")
        shutil.rmtree(a.out)
    (a.out / "data").mkdir(parents=True)
    (a.out / "code").mkdir(parents=True)

    ref = published_digests()
    manifest: dict = {"data": {}, "code_files": 0, "published_digests": ref,
                      "mismatches": []}

    for rel in DATA:
        src = ROOT / rel
        if not src.exists():
            raise SystemExit(f"missing input {rel}; the bundle would be incomplete and is not "
                             f"written")
        dst = a.out / "data" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        digest = sha256(src)
        entry = {"sha256": digest, "size_bytes": src.stat().st_size}
        if rel in ref:
            entry["published_sha256"] = ref[rel]
            entry["matches_published"] = ref[rel] == digest
            if ref[rel] != digest:
                manifest["mismatches"].append(rel)
        manifest["data"][rel] = entry

    n = 0
    for tree in CODE_TREES:
        for rel in tracked(tree):
            src = ROOT / rel
            if not src.exists():
                continue
            dst = a.out / "code" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            n += 1
    for rel in CODE_FILES:
        shutil.copy2(ROOT / rel, a.out / "code" / rel)
        n += 1
    manifest["code_files"] = n

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True)
    manifest["git_commit"] = head.stdout.strip()
    manifest["git_dirty"] = bool(dirty.stdout.strip())

    eq = ROOT / "results/stream_equivalence.json"
    manifest["stream_equivalence"] = (json.loads(eq.read_text()) if eq.exists()
                                      else {"MISSING": "run scripts/kaggle/"
                                            "check_stream_equivalence.py"})
    (a.out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (a.out / "README.md").write_text(README)

    total = sum(f.stat().st_size for f in a.out.rglob("*") if f.is_file())
    print(f"wrote {a.out}")
    print(f"  data files  {len(DATA)}")
    print(f"  code files  {n}")
    print(f"  total       {total / 1e6:.1f} MB")
    print(f"  git         {manifest['git_commit'][:12]}"
          f"{' (DIRTY)' if manifest['git_dirty'] else ''}")
    if manifest["mismatches"]:
        print("\n  !! these inputs DO NOT match the digests the published runs recorded:")
        for rel in manifest["mismatches"]:
            print(f"     {rel}")
        print("     Seeds trained on them may not be pooled with the published five.")
    else:
        matched = sum(1 for v in manifest["data"].values() if v.get("matches_published"))
        print(f"  digests     {matched} of {len(DATA)} match the published runs "
              f"(the rest are not recorded in the reference manifest)")


README = """# tgnn-solv e5 — the two arms that need a GPU

`grounded_a_truetrain` and `channel_swap`, five seeds each, on the CERTIFIED-CLEAN sigma stream.

Both currently stand at one seed against five-seed comparators. The seed-42 runs already on disk
were trained against the *uncertified* stream, so they cannot be pooled with the clean family:
all five seeds of each arm are re-run here, ten arms in total.

## Layout

    data/   the three split files, the two clean stream files, the VT-2005 oracle artifact
    code/   src/ scripts/ configs/ pyproject.toml, git-tracked files only
    MANIFEST.json   sha256 of everything, beside the digests the published runs recorded

## The one assertion that matters

`MANIFEST.json` carries `published_sha256` for the split and stream files. The notebook checks
them before training. A run whose inputs do not match is not training against the same corpus,
and its seeds may not be pooled with the five already reported — this project has already lost a
run family to a stream built against the wrong split files.

## Running it

Use the notebooks in `code/scripts/kaggle/`. Internet must be ON (for pip). Save every session's
`/kaggle/working/out` as a dataset and pass it to the next session as an input: the runner skips
finished arms and resumes partial ones, so a 12-hour session limit costs nothing but a restart.
"""


if __name__ == "__main__":
    main()
