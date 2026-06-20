#!/usr/bin/env python3
"""Summarize crystal/activity compensation from a prediction CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
from tgnn_solv.diagnostics.compensation import annotate_compensation_frame
from tgnn_solv.diagnostics.compensation import compensation_row_mask
from tgnn_solv.diagnostics.compensation import compensation_summary
from tgnn_solv.diagnostics.compensation import grouped_compensation_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--predictions-csv",
        required=True,
        help="Prediction CSV exported by export_checkpoint_predictions.py.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory for summary artifacts.",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Optional run label. Defaults to the prediction filename stem.",
    )
    parser.add_argument(
        "--include-unsupervised",
        action="store_true",
        help="Keep rows without measured ln_x2_true instead of filtering to supervised rows.",
    )
    return parser.parse_args()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def main() -> None:
    args = parse_args()
    predictions_path = Path(args.predictions_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    label = args.label or predictions_path.stem

    df = pd.read_csv(predictions_path, low_memory=False)
    if not args.include_unsupervised and "has_solubility" in df.columns:
        mask = df["has_solubility"].astype(str).str.lower().isin({"true", "1", "yes"})
        df = df.loc[mask].copy()
    eligibility_mask = compensation_row_mask(df)
    df = df.loc[eligibility_mask].copy()

    annotated = annotate_compensation_frame(df, label=label)
    summary = compensation_summary(annotated)
    summary["label"] = label
    summary["predictions_csv"] = str(predictions_path.resolve())
    summary["n_eligible_rows_before_annotation"] = int(eligibility_mask.sum())

    per_pair = grouped_compensation_summary(
        annotated,
        group_cols=["pair_canonical"],
        label=label,
    )
    if not per_pair.empty:
        per_pair = per_pair.sort_values(["n_rows", "mae"], ascending=[False, False])
    group_cols = ["solute_canonical"]
    if "solute_name" in annotated.columns:
        group_cols = ["solute_name", "solute_canonical"]
    per_solute = grouped_compensation_summary(
        annotated,
        group_cols=group_cols,
        label=label,
    )
    if not per_solute.empty:
        per_solute = per_solute.sort_values(["n_rows", "mae"], ascending=[False, False])

    annotated_path = out_dir / "row_diagnostics.csv"
    summary_path = out_dir / "summary.json"
    pair_path = out_dir / "per_pair_summary.csv"
    solute_path = out_dir / "per_solute_summary.csv"
    summary_md_path = out_dir / "SUMMARY.md"

    annotated.to_csv(annotated_path, index=False)
    per_pair.to_csv(pair_path, index=False)
    per_solute.to_csv(solute_path, index=False)
    summary_path.write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )

    lines = [
        f"# Compensation Diagnostics: {label}",
        "",
        f"- Rows: `{summary['n_rows']}`",
        f"- MAE: `{summary['mae']:.6f}`" if summary["mae"] is not None else "- MAE: `NA`",
        f"- RMSE: `{summary['rmse']:.6f}`" if summary["rmse"] is not None else "- RMSE: `NA`",
        f"- R2: `{summary['r2']:.6f}`" if summary["r2"] is not None else "- R2: `NA`",
        (
            f"- corr(delta_phi, delta_gamma): "
            f"`{summary['delta_phi_delta_gamma_corr']:.6f}`"
            if summary["delta_phi_delta_gamma_corr"] is not None
            else "- corr(delta_phi, delta_gamma): `NA`"
        ),
        (
            f"- mean |delta_phi + delta_gamma|: "
            f"`{summary['mean_abs_compensation_sum']:.6f}`"
            if summary["mean_abs_compensation_sum"] is not None
            else "- mean |delta_phi + delta_gamma|: `NA`"
        ),
        (
            f"- opposite-sign fraction: `{summary['opposite_sign_fraction']:.6f}`"
            if summary["opposite_sign_fraction"] is not None
            else "- opposite-sign fraction: `NA`"
        ),
        "",
        "Artifacts:",
        f"- `row_diagnostics.csv`",
        f"- `per_pair_summary.csv`",
        f"- `per_solute_summary.csv`",
        f"- `summary.json`",
    ]
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(_json_safe(summary), indent=2))


if __name__ == "__main__":
    main()
