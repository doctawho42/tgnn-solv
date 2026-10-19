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

# STAMP WHEN THE SESSION STARTED, because --hours is a budget against Kaggle's cap and the cap
# starts HERE, not at cell 6. Cells 2-5 install torch, stage the repo and hash the inputs; that is
# real session time the runner used to be blind to, so its deadline was optimistic by exactly the
# setup cost and an overrunning arm then walked into the hard kill. Written once and never
# overwritten: a session resumed from a saved output must keep the ORIGINAL stamp only if it is
# the same session, so the file lives in /kaggle/working (fresh per session) and not in the
# mounted output dataset.
_t0 = Path("/kaggle/working/.session_t0")
if not _t0.exists():
    _t0.write_text(str(time.time()))
print("session stamp:", _t0.read_text().strip(),
      "| age at this cell: %.2f min" % ((time.time() - float(_t0.read_text())) / 60))

import torch
print("torch", torch.__version__, "| cuda", torch.cuda.is_available(),
      "|", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO GPU")
assert torch.cuda.is_available(), (
    "No GPU. Set Accelerator to GPU in the notebook settings; these arms are ~2 h each on a T4 "
    "and are not worth starting on CPU.")
"""

INSTALL = """
# INSTALL ONLY WHAT IS MISSING, then probe the SUBPROCESS.
#
# Two things went wrong in the first version of this cell and both are worth the comment.
# (1) It checked for a replaced torch with importlib.reload(torch).  Reloading torch re-executes
#     its module body, which registers the C++ TORCH_LIBRARY namespace "triton" a second time --
#     torch forbids that, so the check crashed every time regardless of what pip had done.  A
#     loaded C extension cannot be re-executed; nothing can be learned by trying.
# (2) It checked the wrong process.  Training runs in a CHILD process, which imports whatever is
#     on disk at that moment.  This kernel's already-loaded torch says nothing about what the
#     child will get, and a child that silently falls back to CPU costs the whole session.
#
# So: install only the missing packages, then ask a subprocess what IT sees.
import importlib.util, subprocess

_torch_before = torch.__version__
_pkgs = " ".join(pkg for mod, pkg in (("torch_geometric", "torch-geometric"), ("rdkit", "rdkit"))
                 if importlib.util.find_spec(mod) is None)
if _pkgs:
    print("installing:", _pkgs)
    %pip install -q $_pkgs
else:
    print("torch_geometric and rdkit are already present; nothing installed")

_probe = subprocess.run(
    [sys.executable, "-c",
     "import json, torch, torch_geometric, rdkit;"
     "print(json.dumps({'torch': torch.__version__, 'cuda': torch.cuda.is_available(),"
     " 'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"
     " 'pyg': torch_geometric.__version__}))"],
    capture_output=True, text=True)
print(_probe.stdout.strip() or _probe.stderr.strip()[-2000:])
assert _probe.returncode == 0, "a fresh python cannot import the stack the training runs on"
_info = json.loads(_probe.stdout.strip().splitlines()[-1])
assert _info["cuda"], (
    f"A CHILD PROCESS SEES NO GPU (this kernel: cuda={torch.cuda.is_available()}). Training runs "
    f"in a child, so it would spend hours on CPU and look fine -- this project has lost runs to "
    f"exactly that. If this kernel DOES see a GPU, pip replaced torch with a build that has no "
    f"CUDA: factory-reset the session and re-run. If it does not, the Accelerator is not set.")
assert _info["torch"] == _torch_before, (
    f"pip changed torch on disk ({_torch_before} -> {_info['torch']}). Restart the session before "
    f"training: this kernel and its children now disagree about which torch they use.")
print("the training subprocess sees", _info["torch"], "on", _info["device"])
"""

STAGE = """
# Each cell imports what it uses, so a cell can be re-run on its own after a restart.
import os, sys, shutil
from pathlib import Path

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
import hashlib, json, os
from pathlib import Path

# THE ONE CHECK THAT MATTERS.  A run whose split files differ from the ones the published family
# trained on is not training against the same corpus, and its seeds may not be pooled with the
# five already reported.  This project has already lost a run family to a stream built against the
# wrong split files; the assertion is cheaper than the audit that finds it afterwards.
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
# КОД В ЯДРЕ -- ИЗ БАНДЛА, А НЕ ИЗ GIT, и 2026-10-19 это стоило запуска и трёх с половиной
# часов. Плечо grounded_a_detachencoder было в репозитории и запушено, но бандл был снимком от
# 2026-10-03: `case` в драйвере провалился МОЛЧА, обучение не шло (hours 0.0), и упал только
# агрегатор на отсутствующем CSV -- в двух шагах от причины. Теперь ожидаемый коммит передаётся
# при сборке ноутбука и сверяется ЗДЕСЬ, на первой минуте сессии.
_want = os.environ.get("TGNN_EXPECT_COMMIT", "").strip()
_prov = (man.get("code_provenance") or {})
_got = str(_prov.get("git_commit") or "")
print(f"\\nбандл собран из коммита {_got[:12] or '-'} "
      f"(ветка {_prov.get('git_branch') or '-'}, dirty={_prov.get('git_dirty')})")
if _want:
    assert _got.startswith(_want), (
        f"БАНДЛ НЕ ТОТ: ожидался коммит {_want}, в MANIFEST {_got[:12] or 'его нет вовсе'}. "
        f"Ядро копирует код ИЗ БАНДЛА, поэтому старая версия датасета означает старый драйвер и "
        f"старый src: плечи, добавленные после сборки, молча не запустятся. Пересобери "
        f"scripts/kaggle/build_kaggle_bundle.py и выложи новой версией датасета.")
    print(f"ожидаемый коммит {_want} подтверждён")
elif not _got:
    print("!! в MANIFEST нет code_provenance -- бандл собран до появления штампа; "
          "какой код здесь исполняется, проверить нечем")

print(f"\\nthe {len(SPLITS)} split files match the published runs exactly")
print("the sigma stream is the REBUILT one -- same pool, same split sizes, unverifiable assignment")
"""

RESTORE = """
import os, shutil
from pathlib import Path

# Carry a previous session's work forward, if its output dataset is attached.
#
# TWO LAYOUTS, AND THE SECOND ONE COST A SESSION.  `kaggle datasets create -p <dir> -r zip
# --dir-mode zip` zips each TOP-LEVEL directory and Kaggle extracts its CONTENTS at the
# dataset root -- so a staged tree of `out/checkpoints/...` arrives as `checkpoints/...`,
# with the `out/` wrapper GONE.  Verified 2026-10-04 with `kaggle datasets files`:
# tgnn-solv-e2-out lists `checkpoints/grounded_a_seed42.pt`, not `out/checkpoints/...`.
# The old glob looked only for `*/out`, found nothing, printed nothing alarming, and the
# arm restarted FROM SCRATCH -- the same silent-restart failure that had already burned
# 21.5 GPU-hours the day before.  Both layouts are accepted now.
# AND THE MOUNT POINT IS NOT WHERE THE SLUG SAYS EITHER.  Measured 2026-10-04 in the log of
# tgnn-solv-e2rb: the bundle mounted at `/kaggle/input/datasets/polomoshnov/tgnn-solv-e5`, i.e.
# `/kaggle/input/datasets/<owner>/<slug>/`, two levels BELOW `/kaggle/input`.  BUNDLE above
# survived that only because it searches recursively for a sentinel file; this cell walked one
# level, saw a directory called `datasets`, looked for `datasets/out` and `datasets/checkpoints`,
# found neither, and the guard fired.  So discovery is by CONTENT at any depth, never by position:
# Kaggle owns the mount path and has already changed it, while `checkpoints/` inside the dataset
# is ours.
OUT = Path("/kaggle/working/out")
OUT.mkdir(parents=True, exist_ok=True)
MARKERS = ("checkpoints", "results")
ROOT = Path("/kaggle/input")
bundle = globals().get("BUNDLE")
cands, seen = [], set()
for marker in MARKERS:
    for d in sorted(ROOT.rglob(marker)) if ROOT.is_dir() else []:
        if not d.is_dir():
            continue
        base = d.parent
        # The code/data bundle also carries a `results/` tree (the sigma-profile artifact).  It is
        # an INPUT, not a previous session's output, and copying it here would be a second source
        # of confusion in the same cell.
        if bundle is not None and (base == bundle or bundle in base.parents or base in bundle.parents):
            continue
        if base in seen:
            continue
        seen.add(base)
        cands.append(base)
for src in cands:
    print("restoring from", src)
    shutil.copytree(src, OUT, dirs_exist_ok=True)
if not cands:
    # Print the tree instead of only asserting, so the NEXT layout change is diagnosable from the
    # notebook itself rather than from a log round-trip.
    print("nothing found under", ROOT, "-- what is actually mounted:")
    for d in sorted(ROOT.rglob("*"))[:60] if ROOT.is_dir() else []:
        print("   ", d, "/" if d.is_dir() else "")

ckpts = sorted(OUT.glob("checkpoints/*.pt"))
done = sorted(OUT.glob("results/seed_*/*_predictions.csv"))
print(f"{len(ckpts)} checkpoints and {len(done)} prediction files carried forward")
for f in ckpts + done:
    print("  ", f.relative_to(OUT))

# A GUARD, because its absence is what made the failure silent.  A first session legitimately
# restores nothing; a RESUME session that restores nothing would quietly retrain from zero and
# spend the whole budget finding out.  Set TGNN_EXPECT_RESUME=1 in the notebook's env cell for
# any session that is meant to continue earlier work.
if os.environ.get("TGNN_EXPECT_RESUME", "").strip() not in ("", "0", "false", "False"):
    assert ckpts or done, (
        "TGNN_EXPECT_RESUME is set but nothing was restored. This cell searches /kaggle/input "
        "recursively for any directory containing `checkpoints/` or `results/`, so neither the "
        "mount depth nor a stripped `out/` wrapper can cause this -- the output dataset is not "
        "attached, or it holds neither of those directories. The mounted tree is printed above; "
        "cross-check it against `kaggle datasets files <slug>`."
    )
"""

RUN = """
import subprocess, sys

# NOT A SHELL MAGIC.  This was written as `!python ... \\` with backslash continuations, which
# IPython does not reliably join: the first line runs as a shell command and the rest are handed to
# the Python parser.  subprocess is unambiguous, and it hands back an exit code the cell can check.
# -u so the runner's progress streams into the notebook instead of arriving at the end of eleven
# hours, or not at all if the session is killed first.
_cmd = [sys.executable, "-u", "scripts/kaggle/run_arms.py",
        "--arms", {arms},
        "--seeds", {seeds},
        "--hours", "{hours}", "--device", "cuda", "--num-workers", "2",
        "--out-dir", "/kaggle/working/out/results",
        "--ckpt-dir", "/kaggle/working/out/checkpoints"] + {batch}
print(" ".join(_cmd), flush=True)
_rc = subprocess.run(_cmd).returncode
print("\\nrunner exit code:", _rc)
assert _rc == 0, "the runner failed; read the traceback above before saving a dataset version"
"""

SUMMARY = """
# What came out, and what still has to be queued.
import json
from pathlib import Path

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
    ap.add_argument("--hours", type=float, default=11.0,
                    help="the session budget, measured from the SESSION's start -- cell 1 stamps "
                         "it and the runner anchors to that, so setup time is charged against "
                         "this number rather than given away. Kaggle kills at twelve; the runner "
                         "stops itself before that and resumes next session. Set it to the quota "
                         "actually left, not to twelve.")
    ap.add_argument("--expect-resume", action="store_true",
                    help="сессия ПРОДОЛЖАЕТ прежнюю работу: ячейка восстановления падает, если "
                         "восстановить оказалось нечего. Без этого флага пустое восстановление "
                         "выглядит нормально, плечо тихо начинается с нуля и тратит весь бюджет "
                         "на то, чтобы это выяснить -- так 2026-10-04 было потеряно ядро, и так "
                         "же 2026-10-03 сгорели 21.5 часа.")
    ap.add_argument("--expect-commit", default=None,
                    help="префикс коммита, из которого ОБЯЗАН быть собран бандл. Ячейка проверки "
                         "сверяет его с MANIFEST.code_provenance и падает на первой минуте, если "
                         "приложена старая версия датасета. Без этого старый бандл означает "
                         "старый драйвер: плечо, добавленное после сборки, молча не запустится.")
    ap.add_argument("--batch-size", type=int, default=None,
                    help="override the config batch size for every arm. UNSET IS NOT NEUTRAL "
                         "HERE: at the config's 64 an arm costs about 20 h on a T4 (measured -- "
                         "two sessions each reached ~58%% of one arm in twelve), so a run left at "
                         "the default needs two sessions per arm. Setting it makes the arms "
                         "comparable with each other and NOT schedule-matched to the published "
                         "five-seed family; that is a claim about what the run is for.")
    a = ap.parse_args()

    cells = [
        md(INTRO),
        md("## 1 — environment"), code(ENV),
        md("## 2 — dependencies"), code(INSTALL),
        md("## 3 — stage code and data"), code(STAGE),
        md("## 4 — verify the inputs against the published digests"),
        code((f'import os\nos.environ["TGNN_EXPECT_COMMIT"] = "{a.expect_commit}"\n'
              if a.expect_commit else "") + VERIFY),
        md("## 5 — carry forward a previous session"),
        code(('import os\nos.environ["TGNN_EXPECT_RESUME"] = "1"\n'
              if a.expect_resume else "") + RESTORE),
        md(f"## 6 — run\n\n`{' '.join(a.arms)}` × seeds `{a.seeds}` "
           f"= **{len(a.arms) * len(a.seeds)} arms**.\n\n"
           + (f"Batch size **{a.batch_size}**, overriding the config's. These arms are comparable "
              f"with each other and are **not** schedule-matched to the published five-seed "
              f"family; anything read across the two families is reading across schedules."
              if a.batch_size else
              "Batch size from the config. **About 20 h an arm on a T4** — measured, not "
              "estimated: the 2026-08-19 and 2026-08-21 sessions each reached roughly 58% of one "
              "arm in twelve GPU-hours. Expect two sessions per arm.")),
        code(RUN.format(hours=a.hours, arms=", ".join(repr(x) for x in a.arms),
                        seeds=", ".join(repr(str(s)) for s in a.seeds),
                        batch=(f'["--batch-size", "{a.batch_size}"]' if a.batch_size else "[]"))),
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
