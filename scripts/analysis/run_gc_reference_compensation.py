#!/usr/bin/env python3
"""Robust crystal/activity compensation against a GC (Joback) reference.

The strict compensation diagnostic needs measured T_m AND dH_fus per row, but the
standard solubility test split has no fusion-enthalpy labels (so the published
``corr=-0.876`` came from an n=8 hand-built probe). This wrapper computes the
robust full-test variant using per-solute Joback group-contribution priors as the
crystal reference -- computable for any SMILES.

    python scripts/analysis/run_gc_reference_compensation.py \
        --predictions-csv results/e0_compensation/tgnn_mpnn_test_predictions.csv \
        --out-json results/e0_compensation/gc_reference_summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
from tgnn_solv.diagnostics.compensation import gc_reference_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--predictions-csv", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_csv(args.predictions_csv, low_memory=False)
    summary = gc_reference_summary(df, n_bootstrap=args.n_bootstrap, seed=args.seed)
    if args.label is not None:
        summary["label"] = args.label
    summary["predictions_csv"] = str(Path(args.predictions_csv).resolve())

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
