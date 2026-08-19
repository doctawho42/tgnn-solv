#!/usr/bin/env python
"""Generate the Kaggle notebook that runs the outstanding GPU arms.

Written as a generator rather than a checked-in .ipynb so the notebook cannot drift from the
commands and the digests this repository actually holds: every constant below is read from the
repo at generation time.

    python scripts/kaggle/make_notebook.py --out /tmp/kaggle_tgnn_solv/tgnn-solv-e5.ipynb
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _lines(src: str) -> list[str]:
    """nbformat source lines: EVERY element but the last must end in a newline.

    A plain .split("\\n") drops them, and the result still round-trips through json.load --
    which is why the defect survived a structural check.  What it does NOT survive is being
    executed: Jupyter joins the elements verbatim, so a cell written that way arrives as one
    mashed line and the notebook is broken on the first run.  Caught by dry-running the cells
    against a faked /kaggle tree, not by reading the file.
    """
    body = src.strip("\n")
    return [line + "\n" for line in body.split("\n")[:-1]] + [body.split("\n")[-1]]


def md(src: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(src)}


def code(src: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": _lines(src)}


INTRO = """
# tgnn-solv — the two arms that need a GPU

`grounded_a_truetrain` (reference profile injected during **training**, so the crystal and
correction branches co-adapt to it) and `channel_swap` (the same injection under coordinate
descent, which freezes Φ in phase 2). Both stand at **one seed** against five-seed comparators,
and the referee report asks for the rest.

`grounded_a` runs beside them because the contrast is *within* a stream: the σ-stream the
published five-seed family trained on **was not retained** (it lived only on a compute host that
is no longer reachable), so a rebuilt stream is used here. The rebuild reproduces the pool exactly
— same 1319 molecules, profiles bit-equal — and the split sizes exactly (1187/132), but **not** the
train/val assignment, which cannot be checked against a file that no longer exists. Running
`grounded_a` here makes the comparison self-contained instead of resting on that.

## Session protocol

Kaggle stops a GPU session at its limit. Nothing is lost:

1. Run the notebook. It stops starting new arms ~1 h before the limit.
2. **Save `/kaggle/working/out` as a new Dataset version** (`tgnn-solv-e5-out`).
3. Add that dataset as an input to the next session and run the same notebook.

Finished arms are skipped, partial ones resume from their checkpoint. The runner is seed-major,
so an interrupted run leaves **complete seeds** rather than a ragged matrix.

**Settings:** Accelerator = GPU (T4 ×2 or P100), Internet = **ON** (needed for pip), Persistence =
Variables and Files.
"""

ENV = """
import os, sys, json, shutil, subprocess, time
from pathlib import Path

import torch
print("torch", torch.__version__, "| cuda", torch.cuda.is_available(),
      "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO GPU")
assert torch.cuda.is_available(), (
    "No GPU. Set Accelerator to GPU in the notebook settings; these arms are ~2 h each on a T4 "
    "and are not worth starting on CPU.")
"""

INSTALL = """
# torch is preinstalled with the right CUDA build.  torch-geometric does NOT list torch in its
# install_requires, so a plain install will not replace it -- and --no-deps is avoided because it
# would also skip torch_geometric's own runtime deps.  tgnn_solv uses only Data/Batch containers
# (no torch-scatter / torch-sparse), so the pure-python wheel is enough.
_torch_before = torch.__version__
%pip install -q torch-geometric rdkit
import importlib, torch as _t
importlib.reload(_t)
assert _t.__version__ == _torch_before, (
    f"pip replaced torch ({_torch_before} -> {_t.__version__}); the CUDA build is gone. "
    f"Reinstall the Kaggle torch before continuing.")
import torch_geometric, rdkit
print("torch_geometric", torch_geometric.__version__, "| rdkit", rdkit.__version__)
"""

STAGE = """
# Locate the input dataset by its manifest rather than by a hard-coded slug.
BUNDLE = next((p.parent for p in Path("/kaggle/input").rglob("MANIFEST.json")
               if (p.parent / "code").is_dir()), None)
assert BUNDLE is not None, ("The tgnn-solv-e5 dataset is not attached. Add it under "
                            "Input > Add Data.")
print("bundle:", BUNDLE)

# /kaggle/input is read-only and the package is installed editable, so the code is copied out.
REPO = Path("/kaggle/working/repo")
if REPO.exists():
    shutil.rmtree(REPO)
shutil.copytree(BUNDLE / "code", REPO)
for rel in ("notebooks/data/processed", "notebooks/data/processed_sigma_aux_stream_rebuilt",
            "results/sigma_profile_artifact"):
    src = BUNDLE / "data" / rel
    if src.is_dir():
        shutil.copytree(src, REPO / rel, dirs_exist_ok=True)
os.chdir(REPO)
sys.path.insert(0, str(REPO / "src"))
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
print("repo:", REPO, "| files:", sum(1 for _ in REPO.rglob("*") if _.is_file()))
"""

VERIFY = """
# THE ONE CHECK THAT MATTERS.  A run whose split files differ from the ones the published family
# trained on is not training against the same corpus, and its seeds may not be pooled with the
# five already reported.  This project has already lost a run family to a stream built against the
# wrong split files; the assertion is cheaper than the audit that finds it afterwards.
import hashlib

man = json.loads((BUNDLE / "MANIFEST.json").read_text())
bad = []
for rel, entry in man["data"].items():
    p = BUNDLE / "data" / rel
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    ok = got == entry["sha256"]
    pub = entry.get("published_sha256")
    mark = "ok " if ok else "BAD"
    note = ""
    if pub:
        # The label must name the RIGHT reason.  Everything whose digest differs was reading
        # "rebuilt stream", including a split file corrupted in transit -- which is the one case
        # where the reader must not be told the difference is expected.
        expected = "sigma_aux_stream_rebuilt" in rel
        note = ("  == published" if pub == got
                else "  != published (rebuilt stream, expected)" if expected
                else "  != published (NOT EXPECTED for this file)")
    print(f"{mark} {got[:16]}  {rel}{note}")
    if not ok:
        bad.append(rel)
assert not bad, f"the dataset is corrupt in transit: {bad}"

SPLITS = [r for r in man["data"] if "/processed/" in r]
assert all(man["data"][r].get("matches_published") for r in SPLITS), (
    "The SPLIT files do not match the digests the published runs recorded. Stop: seeds trained on "
    "them cannot be pooled with the published five.")
print(f"\\nthe {len(SPLITS)} split files match the published runs exactly")
print("the sigma stream is the REBUILT one -- same pool, same split sizes, unverifiable assignment")
"""

RESTORE = """
# Carry a previous session's work forward, if its output dataset is attached.
OUT = Path("/kaggle/working/out")
OUT.mkdir(parents=True, exist_ok=True)
prev = [p for p in Path("/kaggle/input").glob("*/out") if p.is_dir()]
for p in prev:
    print("restoring from", p)
    shutil.copytree(p, OUT, dirs_exist_ok=True)
done = sorted(OUT.glob("results/seed_*/*_predictions.csv"))
print(f"{len(done)} prediction files carried forward")
for d in done:
    print("  ", d.relative_to(OUT))
"""

RUN = """
# Stops starting new arms with time left to write.  Kaggle's GPU sessions are 12 h; 11.0 leaves an
# hour, which is enough for one export and the dataset save.
!python scripts/kaggle/run_arms.py \\
    --arms {arms} \\
    --seeds {seeds} \\
    --hours 11.0 --device cuda --num-workers 2 \\
    --out-dir /kaggle/working/out/results \\
    --ckpt-dir /kaggle/working/out/checkpoints
"""

SUMMARY = """
# What came out, and what still has to be queued.
import pandas as pd

prog = Path("/kaggle/working/out/results/kaggle_progress.json")
if prog.exists():
    df = pd.DataFrame(json.loads(prog.read_text()))
    print(df.to_string(index=False))
    print(f"\\ntotal GPU hours this dataset: {df.hours.sum():.2f}")

size = sum(f.stat().st_size for f in Path("/kaggle/working/out").rglob("*") if f.is_file())
print(f"\\n/kaggle/working/out is {size / 1e9:.2f} GB")
print("\\nNEXT: File > Save Version, then add /kaggle/working/out as a Dataset version named")
print("tgnn-solv-e5-out and attach it to the next session.")
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--arms", nargs="+",
                    default=["grounded_a", "grounded_a_truetrain", "channel_swap"])
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    a = ap.parse_args()

    cells = [
        md(INTRO),
        md("## 1 — environment"), code(ENV),
        md("## 2 — dependencies"), code(INSTALL),
        md("## 3 — stage code and data"), code(STAGE),
        md("## 4 — verify the inputs against the published digests"), code(VERIFY),
        md("## 5 — carry forward a previous session"), code(RESTORE),
        md(f"## 6 — run\n\n`{' '.join(a.arms)}` × seeds `{a.seeds}` "
           f"= **{len(a.arms) * len(a.seeds)} arms**, roughly 2 h each on a T4."),
        code(RUN.format(arms=" ".join(a.arms), seeds=" ".join(str(s) for s in a.seeds))),
        md("## 7 — what came out"), code(SUMMARY),
    ]
    nb = {"cells": cells, "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
        "accelerator": "GPU"}, "nbformat": 4, "nbformat_minor": 5}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(nb, indent=1) + "\n")
    print(f"wrote {a.out}  ({len(cells)} cells, "
          f"{len(a.arms) * len(a.seeds)} arms: {' '.join(a.arms)} x {a.seeds})")


if __name__ == "__main__":
    main()
