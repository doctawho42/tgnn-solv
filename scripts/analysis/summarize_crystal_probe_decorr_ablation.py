#!/usr/bin/env python3
"""Summarize crystal-known probe decorrelation-loss ablations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
_THIS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import _bootstrap  # noqa: F401
from run_crystal_probe_compensation_diagnostics import (
    annotate_compensation,
    compensation_summary,
    regression_metrics,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        help=(
            "Run triple formatted as "
            "'label,standard_predictions.csv,forced_oracle_predictions.csv'. "
            "Repeat the flag for multiple runs."
        ),
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory for summary CSV/JSON/Markdown outputs.",
    )
    return parser.parse_args()


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    return value


def parse_run_spec(raw: str) -> tuple[str, Path, Path]:
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 3 or not all(parts):
        raise ValueError(
            "--run must be formatted as "
            "'label,standard_predictions.csv,forced_oracle_predictions.csv'"
        )
    label, standard_path, forced_path = parts
    return (
        label,
        _bootstrap.resolve_path(standard_path),
        _bootstrap.resolve_path(forced_path),
    )


def build_row(label: str, standard_path: Path, forced_path: Path) -> dict[str, Any]:
    standard = annotate_compensation(
        pd.read_csv(standard_path, low_memory=False).copy(),
        label=f"{label}_standard",
    )
    forced = annotate_compensation(
        pd.read_csv(forced_path, low_memory=False).copy(),
        label=f"{label}_forced_oracle",
    )

    standard_metrics = regression_metrics(standard["ln_x2_true"], standard["ln_x2_pred"])
    forced_metrics = regression_metrics(forced["ln_x2_true"], forced["ln_x2_pred"])
    standard_comp = compensation_summary(standard)
    forced_comp = compensation_summary(forced)

    return {
        "label": label,
        "standard_predictions": str(standard_path),
        "forced_oracle_predictions": str(forced_path),
        "standard_mae": standard_metrics["mae"],
        "standard_r2": standard_metrics["r2"],
        "standard_bias": standard_metrics["bias"],
        "standard_pred_std_ratio": standard_metrics["pred_std_ratio"],
        "standard_corr_delta_phi_delta_gamma": standard_comp["delta_phi_delta_gamma_corr"],
        "standard_mean_abs_compensation_sum": standard_comp["mean_abs_compensation_sum"],
        "standard_opposite_sign_fraction": standard_comp["opposite_sign_fraction"],
        "forced_oracle_mae": forced_metrics["mae"],
        "forced_oracle_r2": forced_metrics["r2"],
        "forced_oracle_bias": forced_metrics["bias"],
        "forced_oracle_pred_std_ratio": forced_metrics["pred_std_ratio"],
        "forced_oracle_corr_delta_phi_delta_gamma": forced_comp["delta_phi_delta_gamma_corr"],
        "forced_oracle_mean_abs_compensation_sum": forced_comp["mean_abs_compensation_sum"],
        "forced_oracle_opposite_sign_fraction": forced_comp["opposite_sign_fraction"],
        "forced_minus_standard_mae": (
            None
            if standard_metrics["mae"] is None or forced_metrics["mae"] is None
            else float(forced_metrics["mae"] - standard_metrics["mae"])
        ),
        "forced_minus_standard_compensation_sum": (
            None
            if standard_comp["mean_abs_compensation_sum"] is None
            or forced_comp["mean_abs_compensation_sum"] is None
            else float(
                forced_comp["mean_abs_compensation_sum"]
                - standard_comp["mean_abs_compensation_sum"]
            )
        ),
    }


def main() -> int:
    args = parse_args()
    out_dir = _bootstrap.resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        build_row(*parse_run_spec(raw_spec))
        for raw_spec in args.run
    ]
    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(out_dir / "decorr_ablation_summary.csv", index=False)

    payload = {
        "runs": rows,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_ready(payload), indent=2),
        encoding="utf-8",
    )

    summary_md = "\n".join(
        [
            "# Crystal-Known Probe Decorrelation-Loss Ablation",
            "",
            summary_df.to_csv(index=False),
            "",
        ]
    )
    (out_dir / "SUMMARY.md").write_text(summary_md, encoding="utf-8")
    print(json.dumps(_json_ready(payload), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
