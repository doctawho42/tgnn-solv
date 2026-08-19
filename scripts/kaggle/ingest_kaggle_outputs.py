#!/usr/bin/env python
"""Bring a Kaggle run's outputs home, and refuse the ones that are not what they claim.

WHAT COMES BACK
---------------
    out/results/seed_*/…_predictions.csv    per-row predictions, one file per arm
    out/results/seed_*/comparison.json      the aggregator's per-seed output
    out/results/kaggle_progress.json        one entry per arm attempt, with its wall time
    out/checkpoints/…{.pt,.manifest.json}   the trained weights and their provenance

WHAT THIS CHECKS BEFORE COPYING ANYTHING
-----------------------------------------
1.  Every predictions file is COMPLETE.  A killed session can leave a short file, and the runner's
    own guard only fires on the machine that wrote it.  This project has shipped one truncated
    per-row file already.
2.  Every checkpoint manifest names the SAME split digests the published family used.  An arm
    trained on different splits cannot be pooled with them, and the point of the run is pooling.
3.  The sigma stream digest is reported, NOT asserted.  It will not match: the published stream
    was not retained and these arms train on the rebuild (see check_stream_equivalence.py).  The
    mismatch is expected and must travel with the numbers rather than be silently absorbed.

Nothing is copied unless (1) and (2) pass for every arm, because a half-ingested family is worse
than none: the next reader cannot tell which rows came from where.

Usage
-----
    python scripts/kaggle/ingest_kaggle_outputs.py --from ~/Downloads/out \\
        --results-root results/e5_kaggle --ckpt-root checkpoints/e5_kaggle
    python scripts/kaggle/ingest_kaggle_outputs.py --from ~/Downloads/out --dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "checkpoints/e5_leakfree/grounded_a_seed42.manifest.json"
#: the labelled+unlabelled test rows; a shorter export did not finish
EXPECTED_ROWS_MIN = 8000
SPLIT_ROLES = ("train_data", "val_data", "test_data")


def rows(p: Path) -> int:
    with p.open("rb") as fh:
        return sum(1 for _ in fh) - 1


def published_splits() -> dict[str, str]:
    if not REFERENCE.exists():
        return {}
    blob = json.loads(REFERENCE.read_text())
    return {i["role"]: i["sha256"] for i in blob.get("inputs", []) if i.get("role") in SPLIT_ROLES}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", type=Path, required=True,
                    help="the downloaded 'out' directory")
    ap.add_argument("--results-root", type=Path, default=ROOT / "results/e5_kaggle")
    ap.add_argument("--ckpt-root", type=Path, default=ROOT / "checkpoints/e5_kaggle")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    src_results = a.src / "results"
    src_ckpt = a.src / "checkpoints"
    if not src_results.is_dir():
        raise SystemExit(f"{src_results} is not a directory; point --from at the 'out' directory")

    preds = sorted(src_results.glob("seed_*/*_predictions.csv"))
    if not preds:
        raise SystemExit(f"no predictions under {src_results}; nothing to ingest")

    problems: list[str] = []
    print(f"{len(preds)} prediction files\n")
    for p in preds:
        n = rows(p)
        ok = n >= EXPECTED_ROWS_MIN
        print(f"  {'ok ' if ok else 'SHORT'}  {n:>6} rows  {p.relative_to(src_results)}")
        if not ok:
            problems.append(f"{p.relative_to(src_results)} has {n} rows (< {EXPECTED_ROWS_MIN})")

    want = published_splits()
    mans = sorted(src_ckpt.glob("*.manifest.json")) if src_ckpt.is_dir() else []
    print(f"\n{len(mans)} checkpoint manifests"
          f"{'' if want else '  (no reference manifest here; split check skipped)'}")
    streams: set[str] = set()
    for m in mans:
        blob = json.loads(m.read_text())
        got = {i["role"]: i["sha256"] for i in blob.get("inputs", []) if i.get("role") in want}
        bad = [r for r in want if got.get(r) != want[r]]
        print(f"  {'ok ' if not bad else 'BAD'}  {m.name}"
              f"{'' if not bad else '  splits differ: ' + ','.join(bad)}")
        if bad:
            problems.append(f"{m.name} trained on different {', '.join(bad)}")
        for s in blob.get("metadata", {}).get("grounding_streams", []):
            if s.get("present") and s.get("sha256"):
                streams.add(f"{s['role']}={s['sha256'][:16]}")

    if streams:
        print("\nsigma streams these arms consumed (reported, not asserted):")
        for s in sorted(streams):
            print(f"  {s}")
        print("  The published family's stream was not retained, so this will not match it.\n"
              "  Any pooled comparison must say so.")

    if problems:
        print(f"\n{len(problems)} problem(s); NOTHING was copied:")
        for x in problems:
            print(f"  - {x}")
        raise SystemExit(1)

    if a.dry_run:
        print("\ndry run: everything passes, nothing copied")
        return

    for sub, dst in ((src_results, a.results_root), (src_ckpt, a.ckpt_root)):
        if not sub.is_dir():
            continue
        for f in sub.rglob("*"):
            if not f.is_file():
                continue
            target = dst / f.relative_to(sub)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
    print(f"\ningested -> {a.results_root} and {a.ckpt_root}")
    print("NEXT: aggregate with scripts/analysis/run_e5_comparison.py, then decide whether these "
          "arms may be pooled with the published five given the stream note above.")


if __name__ == "__main__":
    main()
