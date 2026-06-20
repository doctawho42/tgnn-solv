#!/usr/bin/env python3
"""Honest crystal/activity decomposition (non-identifiability) diagnostic.

The often-cited compensation correlation ``corr(delta_phi, delta_gamma) ~ -0.96``
against the GC (Joback) crystal reference is an *accounting/shared-reference
artifact*, NOT evidence of learned compensation:

  * ``delta_phi + delta_gamma`` equals the (small) physics-only prediction error,
    so the correlation is forced toward -1 whenever the model fits ln x2; and
  * both deltas embed the high-variance per-solute ``phi_gc`` with opposite sign.

This wrapper quantifies the artifact (a PERMUTATION NULL that destroys any learned
crystal/activity coupling still reproduces most of the correlation) and reports
the defensible signal -- the magnitude of ``delta_phi`` (the crystal term's
deviation from the physical prior) with an honest SOLUTE-CLUSTER bootstrap CI.

    python scripts/analysis/run_decomposition_identifiability.py \
        --predictions-csv results/e0_compensation/tgnn_mpnn_test_predictions.csv \
        --out-json results/e0_compensation/decomposition_identifiability.json
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

import _bootstrap  # noqa: F401,E402
from tgnn_solv.diagnostics.compensation import (  # noqa: E402
    decomposition_identifiability_summary,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--predictions-csv", required=True)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--n-perm", type=int, default=1000)
    parser.add_argument("--n-bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = pd.read_csv(args.predictions_csv, low_memory=False)
    summary = decomposition_identifiability_summary(
        df, n_perm=args.n_perm, n_bootstrap=args.n_bootstrap, seed=args.seed
    )
    if args.label is not None:
        summary["label"] = args.label
    summary["predictions_csv"] = str(Path(args.predictions_csv).resolve())

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
