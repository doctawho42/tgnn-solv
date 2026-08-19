#!/usr/bin/env python
"""Is the rebuilt sigma stream the same stream the published five-seed family trained on?

THE PROBLEM THIS ANSWERS, and it is a deposit defect
-----------------------------------------------------
The certified leak-free re-run recorded the stream it consumed by digest:

    notebooks/data/processed_sigma_aux_stream_clean/sigma_train.csv  955a1862...
    notebooks/data/processed_sigma_aux_stream_clean/sigma_val.csv    daf72c20...

Neither file is on this machine.  The clean directory holds a DIFFERENT build (bbe02152, 1319
rows, no validation split) and sigma_val.csv is absent entirely; the stream the runs actually read
lived on the compute host, whose project is no longer reachable.  So a new training arm cannot be
put on the same bytes, and the honest question is how close it can be put.

WHAT THIS SCRIPT ESTABLISHES, AND WHAT IT CANNOT
-------------------------------------------------
Re-running the builder with the recorded parameters (--val-fraction 0.1 --split-seed 0, scaffolds
excluded from test and val) reproduces:

  * the POOL exactly -- same 1319 molecules, and their sigma-profiles are bit-equal;
  * the SPLIT SIZES exactly -- 1187 train and 132 val, the counts the checkpoint manifests record.

It cannot establish that the train/val ASSIGNMENT is the same 1187 and the same 132, because the
file that would say so was not retained.  sigma_val drives early stopping of the sigma warm-up, so
a different assignment moves where the warm-up stops -- a small difference, and a real one.

READ THIS BEFORE POOLING.  An arm trained on the rebuilt stream may be compared with the published
five, and the comparison must carry that sentence.  It is a fourth defect on the deposited record,
beside the three the Data Availability statement already discloses.

Usage
-----
    python scripts/kaggle/check_stream_equivalence.py
    python scripts/kaggle/check_stream_equivalence.py --json results/stream_equivalence.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REBUILT = ROOT / "notebooks/data/processed_sigma_aux_stream_rebuilt"
POOL_ON_DISK = ROOT / "notebooks/data/processed_sigma_aux_stream_clean/sigma_train.csv"
MANIFEST = ROOT / "checkpoints/e5_leakfree/grounded_a_seed42.manifest.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rebuilt", type=Path, default=REBUILT)
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()

    published = {}
    if MANIFEST.exists():
        for s in json.loads(MANIFEST.read_text())["metadata"]["grounding_streams"]:
            if s.get("present"):
                published[s["role"]] = {"sha256": s["sha256"], "n_rows": s.get("n_rows"),
                                        "n_solutes": s.get("n_distinct_solutes")}

    tr = pd.read_csv(a.rebuilt / "sigma_train.csv", low_memory=False)
    va = pd.read_csv(a.rebuilt / "sigma_val.csv", low_memory=False)
    pool = pd.read_csv(POOL_ON_DISK, low_memory=False)
    both = pd.concat([tr, va], ignore_index=True)

    pcols = [c for c in pool.columns if c.startswith("sigma_p_")]
    m = both.set_index("solute_smiles")[pcols].sort_index()
    o = pool.set_index("solute_smiles")[pcols].sort_index()
    common = m.index.intersection(o.index)
    max_diff = float(np.abs(m.loc[common].to_numpy(float)
                            - o.loc[common].to_numpy(float)).max()) if len(common) else float("nan")

    out = {
        "what": "how close the rebuilt sigma stream is to the one the published runs consumed",
        "published": published,
        "rebuilt": {
            "sigma_train": {"sha256": sha256(a.rebuilt / "sigma_train.csv"), "n_rows": len(tr)},
            "sigma_val": {"sha256": sha256(a.rebuilt / "sigma_val.csv"), "n_rows": len(va)},
        },
        "pool_identical": bool(set(both.solute_smiles) == set(pool.solute_smiles)),
        "n_pool_rebuilt": int(len(both)), "n_pool_on_disk": int(len(pool)),
        "columns_identical": list(tr.columns) == list(pool.columns),
        "profiles_max_abs_diff_on_shared_molecules": max_diff,
        "n_shared_molecules": int(len(common)),
        "split_sizes_match_published": (
            len(tr) == (published.get("sigma_train", {}) or {}).get("n_rows")
            and len(va) == (published.get("sigma_val", {}) or {}).get("n_rows")),
        "bytes_match_published": False,
        "WHAT_THIS_DOES_NOT_ESTABLISH": (
            "that the train/val ASSIGNMENT is the published one. The published files were not "
            "retained. sigma_val drives early stopping of the sigma warm-up, so a different "
            "assignment moves where the warm-up stops. Any arm trained on this stream and "
            "compared with the published five must carry that sentence."),
    }
    for role, blob in published.items():
        got = out["rebuilt"].get(role, {}).get("sha256")
        if got and got == blob["sha256"]:
            out["bytes_match_published"] = True

    print(f"pool identical                {out['pool_identical']} "
          f"({out['n_pool_rebuilt']} vs {out['n_pool_on_disk']} molecules)")
    print(f"columns identical             {out['columns_identical']}")
    print(f"profiles bit-equal            {max_diff == 0.0} (max|diff| = {max_diff:.3e})")
    print(f"split sizes match published   {out['split_sizes_match_published']} "
          f"({len(tr)}/{len(va)})")
    print(f"bytes match published         {out['bytes_match_published']}")
    print(f"\n{out['WHAT_THIS_DOES_NOT_ESTABLISH']}")

    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(out, indent=2) + "\n")
        print(f"\nwrote {a.json}")

    # The pool and the split sizes are what a new arm needs in order to be COMPARABLE at all.
    # If either fails, the rebuild is not a substitute and the run should not be queued.
    if not (out["pool_identical"] and out["split_sizes_match_published"] and max_diff == 0.0):
        raise SystemExit("the rebuilt stream is NOT equivalent to the published one; do not queue "
                         "arms against it without deciding what the difference costs")


if __name__ == "__main__":
    main()
