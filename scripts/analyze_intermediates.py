#!/usr/bin/env python3
"""Export TGNN solver intermediates, oracle diagnostics, and compact summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from run_full_budget_experiment import (
    build_diagnostics,
    collect_tgnn_intermediates,
    regression_metrics,
)
from run_medium_budget_comparison import _collect_tgnn_tm_only_oracle_intermediates
from validate_physics import (
    load_model_from_checkpoint,
    make_test_loader,
)
from tgnn_solv.device import resolve_device
from tgnn_solv.post_analysis import safe_float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to the TGNN checkpoint.")
    parser.add_argument("--test-data", type=str, required=True, help="Path to the test CSV file.")
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory where CSV/JSON/MD analysis artifacts will be written.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Inference device for intermediate export.",
    )
    parser.add_argument(
        "--tau-sum-threshold",
        type=float,
        default=8.0,
        help="Threshold used in the NRTL diagnostic summary.",
    )
    return parser.parse_args()


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _metric_delta(oracle: dict[str, Any], standard: dict[str, Any]) -> dict[str, float | None]:
    delta: dict[str, float | None] = {}
    for metric_name in ("mae", "rmse", "r2", "bias", "pearson_r"):
        oracle_value = safe_float(oracle.get(metric_name))
        standard_value = safe_float(standard.get(metric_name))
        delta[metric_name] = (
            oracle_value - standard_value
            if oracle_value is not None and standard_value is not None
            else None
        )
    return delta


def build_summary_markdown(summary: dict[str, Any]) -> str:
    test_metrics = summary["test_metrics"]
    oracle_metrics = summary["oracle_tm_only"]["oracle"]
    tm_metrics = summary["tm_metrics"]
    nrtl = summary["nrtl_stats"]
    correction = summary["correction_analysis"]
    return "\n".join(
        [
            "# TGNN Intermediate Analysis",
            "",
            "## Core Metrics",
            f"- Test MAE: {test_metrics['mae']:.4f}" if test_metrics.get("mae") is not None else "- Test MAE: n/a",
            f"- Test RMSE: {test_metrics['rmse']:.4f}" if test_metrics.get("rmse") is not None else "- Test RMSE: n/a",
            f"- Test R²: {test_metrics['r2']:.4f}" if test_metrics.get("r2") is not None else "- Test R²: n/a",
            (
                f"- Oracle T_m-only MAE: {oracle_metrics['mae']:.4f}"
                if oracle_metrics.get("mae") is not None
                else "- Oracle T_m-only MAE: n/a"
            ),
            "",
            "## Physical Quantities",
            f"- T_m MAE: {tm_metrics['mae']:.3f} K" if tm_metrics.get("mae") is not None else "- T_m MAE: n/a",
            f"- T_m Pearson r: {tm_metrics['pearson_r']:.3f}" if tm_metrics.get("pearson_r") is not None else "- T_m Pearson r: n/a",
            (
                f"- Mean gate value: {correction['mean_gate_value']:.3f}"
                if correction.get("mean_gate_value") is not None
                else "- Mean gate value: n/a"
            ),
            (
                f"- Mean correction magnitude: {correction['mean_correction_magnitude']:.3f}"
                if correction.get("mean_correction_magnitude") is not None
                else "- Mean correction magnitude: n/a"
            ),
            "",
            "## NRTL Parameters",
            f"- τ12 mean/std: {nrtl['tau_12']['mean']:.3f} / {nrtl['tau_12']['std']:.3f}"
            if nrtl.get("tau_12", {}).get("mean") is not None
            else "- τ12 mean/std: n/a",
            f"- τ21 mean/std: {nrtl['tau_21']['mean']:.3f} / {nrtl['tau_21']['std']:.3f}"
            if nrtl.get("tau_21", {}).get("mean") is not None
            else "- τ21 mean/std: n/a",
            "",
            "## Artifacts",
            f"- Standard intermediates: `{summary['artifacts']['intermediates_csv']}`",
            f"- Oracle intermediates: `{summary['artifacts']['oracle_intermediates_csv']}`",
            f"- Diagnostics JSON: `{summary['artifacts']['diagnostics_json']}`",
        ]
    ) + "\n"


def main() -> int:
    args = parse_args()
    checkpoint_path = _bootstrap.resolve_path(args.checkpoint)
    test_data_path = _bootstrap.resolve_path(args.test_data)
    output_dir = _bootstrap.resolve_path(args.output_dir)
    device = resolve_device(args.device)
    output_dir.mkdir(parents=True, exist_ok=True)

    test_df = pd.read_csv(test_data_path, low_memory=False)
    model, cfg = load_model_from_checkpoint(checkpoint_path, device=device)
    _, loader = make_test_loader(test_df, cfg=cfg, batch_size=cfg.batch_size)

    print(f"Collecting standard intermediates on {device} ...")
    standard_df = collect_tgnn_intermediates(model, loader, device, force_oracle_injection=False)
    print(f"Collecting T_m-only oracle intermediates on {device} ...")
    oracle_df = _collect_tgnn_tm_only_oracle_intermediates(model=model, loader=loader, device=device)

    sol_mask = standard_df["has_solubility"].astype(bool).to_numpy()
    standard_metrics = regression_metrics(
        standard_df.loc[sol_mask, "ln_x2_final"].to_numpy(dtype=float),
        standard_df.loc[sol_mask, "ln_x2_true"].to_numpy(dtype=float),
    )
    oracle_metrics = regression_metrics(
        oracle_df.loc[sol_mask, "ln_x2_final"].to_numpy(dtype=float),
        oracle_df.loc[sol_mask, "ln_x2_true"].to_numpy(dtype=float),
    )

    tm_mask = standard_df["has_T_m"].astype(bool).to_numpy()
    tm_metrics = regression_metrics(
        standard_df.loc[tm_mask, "T_m_pred"].to_numpy(dtype=float),
        standard_df.loc[tm_mask, "T_m_true"].to_numpy(dtype=float),
    )

    oracle_summary = {
        "definition": "T_m_true substituted where available; dH_fus remains predicted.",
        "standard": standard_metrics,
        "oracle": oracle_metrics,
        "delta_vs_standard": _metric_delta(oracle_metrics, standard_metrics),
        "oracle_available_fraction_T_m": safe_float(oracle_df["oracle_used_T_m"].mean()),
        "oracle_available_fraction_dH_fus": safe_float(oracle_df["oracle_used_dH_fus"].mean()),
    }
    diagnostics = build_diagnostics(
        standard_df,
        tau_sum_threshold=float(args.tau_sum_threshold),
        oracle_metrics=oracle_summary,
    )

    standard_csv = output_dir / "intermediates.csv"
    oracle_csv = output_dir / "oracle_tm_intermediates.csv"
    diagnostics_json = output_dir / "diagnostics.json"
    summary_json = output_dir / "summary.json"
    summary_md = output_dir / "summary.md"

    standard_df.to_csv(standard_csv, index=False)
    oracle_df.to_csv(oracle_csv, index=False)
    diagnostics_json.write_text(
        json.dumps(_json_ready(diagnostics), indent=2),
        encoding="utf-8",
    )

    summary = {
        "checkpoint": str(checkpoint_path),
        "test_data": str(test_data_path),
        "device": str(device),
        "test_metrics": standard_metrics,
        "tm_metrics": tm_metrics,
        "oracle_tm_only": oracle_summary,
        "correction_analysis": diagnostics["correction_analysis"],
        "nrtl_stats": diagnostics["nrtl_parameter_analysis"],
        "artifacts": {
            "intermediates_csv": str(standard_csv),
            "oracle_intermediates_csv": str(oracle_csv),
            "diagnostics_json": str(diagnostics_json),
        },
    }
    summary_json.write_text(json.dumps(_json_ready(summary), indent=2), encoding="utf-8")
    summary_md.write_text(build_summary_markdown(summary), encoding="utf-8")

    print(f"Wrote intermediate analysis to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
