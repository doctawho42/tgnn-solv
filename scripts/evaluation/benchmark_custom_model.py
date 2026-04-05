#!/usr/bin/env python3
"""Evaluate arbitrary external model predictions on TGNN-Solv datasets."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from tgnn_solv.external_benchmarking import (
    build_benchmark_artifacts,
    ln_x2_from_logS,
    logS_from_ln_x2,
    merge_prediction_frame,
    prepare_pair_dataframe,
    write_benchmark_artifacts,
)


def _safe_pred_logS(solvent_smiles: pd.Series, pred_ln_x2: np.ndarray) -> pd.Series:
    clipped = np.minimum(np.asarray(pred_ln_x2, dtype=float), np.log(0.999999))
    return logS_from_ln_x2(
        pd.DataFrame({"solvent_smiles": solvent_smiles, "ln_x2": clipped}),
        ln_x2_col="ln_x2",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark a custom model from an existing predictions CSV or a command that generates one."
    )
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--test-data", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--predictions-csv", default=None)
    parser.add_argument("--command", default=None, help="Optional shell command with {test_data} and {predictions_output} placeholders.")
    parser.add_argument("--generated-predictions", default=None, help="Where the custom command should write predictions.")
    parser.add_argument("--pred-lnx2-col", default=None)
    parser.add_argument("--pred-logs-col", default=None)
    parser.add_argument("--uncertainty-col", default=None)
    parser.add_argument("--merge-on", choices=["auto", "row_index", "pair"], default="auto")
    parser.add_argument("--metadata-json", default=None, help="Optional JSON file with extra metadata.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.predictions_csv and not args.command:
        raise ValueError("Provide either --predictions-csv or --command.")
    if not args.pred_lnx2_col and not args.pred_logs_col:
        raise ValueError("Provide at least one of --pred-lnx2-col or --pred-logs-col.")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = Path(args.predictions_csv) if args.predictions_csv else Path(args.generated_predictions or out_dir / "custom_predictions.csv")

    if args.command:
        command = args.command.format(test_data=args.test_data, predictions_output=str(predictions_path))
        subprocess.run(["bash", "-lc", command], check=True, cwd=Path(__file__).resolve().parents[2])

    if not predictions_path.exists():
        raise FileNotFoundError(f"Predictions CSV not found: {predictions_path}")

    base_df = prepare_pair_dataframe(pd.read_csv(args.test_data), require_targets=True)
    raw_predictions = pd.read_csv(predictions_path)
    merged = merge_prediction_frame(
        base_df,
        raw_predictions,
        prefer_row_index=args.merge_on != "pair",
    )

    pred_ln_x2: np.ndarray | None = None
    pred_logS: np.ndarray | None = None
    if args.pred_lnx2_col:
        pred_ln_x2 = pd.to_numeric(merged[args.pred_lnx2_col], errors="coerce").to_numpy(dtype=float)
    if args.pred_logs_col:
        pred_logS = pd.to_numeric(merged[args.pred_logs_col], errors="coerce").to_numpy(dtype=float)

    if pred_ln_x2 is None and pred_logS is not None:
        pred_ln_x2 = ln_x2_from_logS(
            pd.DataFrame({"solvent_smiles": merged["solvent_smiles"], "logS": pred_logS}),
            logS_col="logS",
        ).to_numpy(dtype=float)
    if pred_logS is None and pred_ln_x2 is not None:
        pred_logS = _safe_pred_logS(merged["solvent_smiles"], pred_ln_x2).to_numpy(dtype=float)

    metadata: dict[str, Any] = {
        "model_family": "custom",
        "predictions_csv": str(predictions_path),
        "merge_on": args.merge_on,
    }
    if args.metadata_json:
        metadata.update(json.loads(Path(args.metadata_json).read_text(encoding="utf-8")))

    uncertainty = None
    if args.uncertainty_col and args.uncertainty_col in merged.columns:
        uncertainty = pd.to_numeric(merged[args.uncertainty_col], errors="coerce").to_numpy(dtype=float)

    artifacts = build_benchmark_artifacts(
        model_name=args.model_name,
        eval_df=merged,
        pred_ln_x2=np.asarray(pred_ln_x2, dtype=float),
        pred_logS=np.asarray(pred_logS, dtype=float),
        uncertainty=uncertainty,
        metadata=metadata,
        split_mode="custom",
        test_data=args.test_data,
    )
    write_benchmark_artifacts(out_dir, artifacts)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
