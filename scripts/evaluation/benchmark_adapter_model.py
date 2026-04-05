#!/usr/bin/env python3
"""Benchmark a Python adapter implementation against repo splits."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401

from tgnn_solv.benchmark_adapters import _parse_json_arg, run_adapter_benchmark


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark a custom Python adapter that implements the repo adapter contract."
    )
    parser.add_argument("--adapter", required=True, help="Adapter reference in `module:ClassOrFactory` form.")
    parser.add_argument("--test-data", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--train-data", default=None)
    parser.add_argument("--val-data", default=None)
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--pred-lnx2-col", default="ln_x2_pred")
    parser.add_argument("--pred-logs-col", default=None)
    parser.add_argument("--uncertainty-col", default=None)
    parser.add_argument("--init-kwargs-json", default=None)
    parser.add_argument("--fit-kwargs-json", default=None)
    parser.add_argument("--predict-kwargs-json", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    artifacts = run_adapter_benchmark(
        adapter_ref=args.adapter,
        test_data=args.test_data,
        out_dir=args.out_dir,
        train_data=args.train_data,
        val_data=args.val_data,
        init_kwargs=_parse_json_arg(args.init_kwargs_json),
        fit_kwargs=_parse_json_arg(args.fit_kwargs_json),
        predict_kwargs=_parse_json_arg(args.predict_kwargs_json),
        model_name=args.model_name,
        pred_lnx2_col=args.pred_lnx2_col or None,
        pred_logs_col=args.pred_logs_col or None,
        uncertainty_col=args.uncertainty_col or None,
    )
    print(json.dumps(artifacts.report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
