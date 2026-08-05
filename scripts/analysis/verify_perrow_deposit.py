#!/usr/bin/env python3
r"""Audit the deposited per-row prediction files of the sigma-grounding run family.

WHY THIS EXISTS
---------------
The article states two things about results/e5_sigma_grounding/seed_*/ that a
referee should be able to check without a GPU and without trusting us:

  (a) every per-row prediction file is complete -- all 8103 test rows, of which
      exactly 5608 carry a solubility label, in the same order in every arm, with
      no non-finite ln x2 prediction anywhere.  The row lock of Sec. 2.2 is
      therefore fixed by which rows carry a label and not by which rows an arm
      handled;

  (b) each file is the file its run scored -- i.e. the metrics in the run's own
      *_predictions.summary.json recompute from the CSV beside it, exactly.

One file used to fail (a): seed_44/oracle_predictions.csv was deposited at 295 of
its 8103 rows, because the transfer off the compute volume stopped mid-record.
It was repaired on 2026-08-05 from the volume copy, and (b) is what establishes
that the recovered file is the one the run scored rather than a re-run: every
field of the deposited summary reproduces from it at zero absolute difference.
This script is that check, kept so the claim stays checkable.

It reads only committed/deposited artifacts.  It trains nothing, loads no model
and needs no GPU.

REPRODUCE
---------
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python \
        scripts/analysis/verify_perrow_deposit.py

Exit status is 0 when every file passes and 1 otherwise, so it can gate a
deposit.  --json writes the full per-file report.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
E5 = REPO / "results/e5_sigma_grounding"

# What the run family is supposed to have written.  These are the article's numbers
# (Sec. 2.2), hard-coded on purpose: a check that reads its expectations out of the
# files it is checking checks nothing.
N_TEST_ROWS = 8103
N_LABELLED = 5608

# Fields of a *_predictions.summary.json that are recomputable from the CSV, with the
# function that recomputes each from the labelled subset.  `bias` is the signed mean
# error; `r2` uses the same 1 - SS_res/(SS_tot + 1e-10) the exporter used.
_ATOL = 1e-12


def _recompute(df: pd.DataFrame) -> dict:
    sup = df[df["has_solubility"].astype(bool)]
    err = sup["error"].to_numpy(float)
    y = sup["ln_x2_true"].to_numpy(float)
    pred = sup["ln_x2_pred"].to_numpy(float)
    out = {
        "n_rows": int(len(df)),
        "n_supervised": int(len(sup)),
    }
    if len(err):
        ss_res = float(np.square(err).sum())
        ss_tot = float(np.square(y - y.mean()).sum())
        out.update(
            mae=float(np.abs(err).mean()),
            rmse=float(np.sqrt(np.square(err).mean())),
            r2=float(1.0 - ss_res / (ss_tot + 1e-10)),
            bias=float(err.mean()),
            target_std=float(y.std(ddof=0)),
            pred_std=float(pred.std(ddof=0)),
            pred_std_ratio=float(pred.std(ddof=0) / (y.std(ddof=0) + 1e-12)),
        )
    if "sigma_oracle_applied" in df.columns:
        osub = df[df["sigma_oracle_applied"].astype(bool) & df["has_solubility"].astype(bool)]
        oerr = osub["error"].to_numpy(float)
        if len(oerr):
            out["sigma_oracle"] = {
                "n_oracle": int(len(oerr)),
                "mae": float(np.abs(oerr).mean()),
                "rmse": float(np.sqrt(np.square(oerr).mean())),
                "bias": float(oerr.mean()),
            }
    return out


def _compare(deposited: dict, recomputed: dict) -> list[str]:
    """Fields the summary printed that the CSV does not reproduce."""
    bad = []
    for k, want in deposited.items():
        if k not in recomputed or want is None:
            continue
        got = recomputed[k]
        if isinstance(want, dict) and isinstance(got, dict):
            for kk, ww in want.items():
                if ww is None or kk not in got:
                    continue
                if abs(float(ww) - float(got[kk])) > _ATOL:
                    bad.append(f"{k}.{kk}: summary {ww!r} vs csv {got[kk]!r}")
            continue
        if isinstance(want, (int, float)) and abs(float(want) - float(got)) > _ATOL:
            bad.append(f"{k}: summary {want!r} vs csv {got!r}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(E5))
    ap.add_argument("--json", default=None, help="write the full report here")
    args = ap.parse_args()
    root = Path(args.root)

    files = sorted(root.glob("seed_*/*_predictions.csv"))
    if not files:
        print(f"no per-row prediction files under {root}", file=sys.stderr)
        return 1

    report: list[dict] = []
    frames: dict[tuple[str, str], pd.DataFrame] = {}
    failures = 0
    print(f"{'file':<58} {'rows':>6} {'lab':>6} {'lastline':>9} "
          f"{'nonfinite':>10} {'vs summary':>11}")
    for f in files:
        seed = f.parent.name
        arm = f.name.replace("_predictions.csv", "")
        raw = f.read_bytes()
        df = pd.read_csv(f, low_memory=False)
        complete_last_line = raw.endswith(b"\n")
        nonfinite = int((~np.isfinite(df["ln_x2_pred"].to_numpy(float))).sum())
        lab = int(df["has_solubility"].astype(bool).sum())

        sp = f.with_suffix("").with_suffix(".summary.json")
        sp = f.parent / f"{arm}_predictions.summary.json"
        mismatches: list[str] = []
        if sp.exists():
            mismatches = _compare(json.loads(sp.read_text()), _recompute(df))
            summary_state = "OK" if not mismatches else f"{len(mismatches)} BAD"
        else:
            summary_state = "(none)"

        ok = (len(df) == N_TEST_ROWS and lab == N_LABELLED
              and complete_last_line and nonfinite == 0 and not mismatches)
        failures += (not ok)
        print(f"{str(f.relative_to(REPO)):<58} {len(df):>6} {lab:>6} "
              f"{'ok' if complete_last_line else 'TRUNC':>9} {nonfinite:>10} "
              f"{summary_state:>11}")
        for m in mismatches:
            print(f"    ! {m}")
        report.append({"file": str(f.relative_to(REPO)), "seed": seed, "arm": arm,
                       "n_rows": int(len(df)), "n_labelled": lab,
                       "last_line_complete": complete_last_line,
                       "n_nonfinite_ln_x2_pred": nonfinite,
                       "summary_mismatches": mismatches, "pass": bool(ok)})
        if len(df) == N_TEST_ROWS:
            frames[(seed, arm)] = df[["solute_smiles", "solvent_smiles", "T",
                                      "has_solubility"]]

    # Row order and labelling must agree across arms within a seed, or the locked
    # 5608 is not the same 5608 for every arm.
    print()
    order_failures = 0
    for seed in sorted({s for s, _ in frames}):
        arms = sorted(a for s, a in frames if s == seed)
        ref_arm = arms[0]
        ref = frames[(seed, ref_arm)]
        ref_key = list(zip(ref.solute_smiles, ref.solvent_smiles, ref["T"].round(6)))
        ref_lab = ref["has_solubility"].astype(bool).to_numpy()
        bad = []
        for a in arms[1:]:
            d = frames[(seed, a)]
            same_order = list(zip(d.solute_smiles, d.solvent_smiles,
                                  d["T"].round(6))) == ref_key
            same_lab = bool((d["has_solubility"].astype(bool).to_numpy() == ref_lab).all())
            if not (same_order and same_lab):
                bad.append(a)
        order_failures += len(bad)
        print(f"{seed}: {len(arms)} full-length arms, row order and labelling "
              f"{'identical' if not bad else 'DIFFER for ' + ', '.join(bad)} "
              f"(reference {ref_arm})")

    failures += order_failures
    print(f"\n{len(files)} files checked, {len(files) - failures} passing"
          if failures else f"\nall {len(files)} files pass")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
