#!/usr/bin/env python3
"""Run the thermodynamic stress suite on a benchmark predictions bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
import pandas as pd

from tgnn_solv.stress import build_stress_suite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate thermodynamic stress slices for a benchmark predictions bundle."
    )
    parser.add_argument("--predictions-csv", required=True, help="Canonical predictions.csv path.")
    parser.add_argument("--train-data", default=None, help="Optional training CSV for seen/unseen slice analysis.")
    parser.add_argument("--pred-col", default="ln_x2_pred")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    predictions_df = pd.read_csv(args.predictions_csv)
    train_df = pd.read_csv(args.train_data) if args.train_data else None
    payload = build_stress_suite(
        predictions_df,
        pred_col=args.pred_col,
        train_df=train_df,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
