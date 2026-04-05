#!/usr/bin/env python3
"""Wait for the medium-budget TGNN baseline to finish, then export full analysis."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import torch
import yaml

from tgnn_solv.post_analysis import (
    build_selected_checkpoint_payload,
    parse_training_log,
    safe_float,
    wait_for_checkpoint_completion,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source-checkpoint",
        type=str,
        default="results/medium_budget/per_model/tgnn_tuned/checkpoint.pt",
        help="Checkpoint written by the live baseline run.",
    )
    parser.add_argument(
        "--export-checkpoint",
        type=str,
        default="checkpoints/tgnn_tuned_medium.pt",
        help="Canonical best-checkpoint path for downstream evaluation.",
    )
    parser.add_argument(
        "--train-log",
        type=str,
        default="results/medium_budget/per_model/tgnn_tuned/train.log",
        help="train.log produced by the medium-budget baseline run.",
    )
    parser.add_argument(
        "--config-yaml",
        type=str,
        default="results/medium_budget/per_model/tgnn_tuned/config.yaml",
        help="Resolved config file used by the baseline run.",
    )
    parser.add_argument(
        "--config-label",
        type=str,
        default="paper_config_tuned.yaml",
        help="Human-readable config label for the final markdown summary.",
    )
    parser.add_argument(
        "--test-data",
        type=str,
        default="notebooks/data/processed/test.csv",
        help="Test split used for evaluation.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/baseline_medium",
        help="Directory where post-analysis artifacts will be written.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device to use for batch-style evaluation scripts.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for the live checkpoint to mark training as completed before running analysis.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=600.0,
        help="Polling interval while waiting for training completion.",
    )
    parser.add_argument(
        "--timeout-hours",
        type=float,
        default=18.0,
        help="Maximum wait time when --wait is enabled.",
    )
    parser.add_argument(
        "--python-executable",
        type=str,
        default=sys.executable,
        help="Python interpreter used for child evaluation scripts.",
    )
    return parser.parse_args()


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"[{timestamp}] {message}", flush=True)


def atomic_torch_save(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        torch.save(payload, tmp_path)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_step(command: list[str], *, cwd: Path) -> None:
    log("Running: " + " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def load_run_config(config_yaml_path: Path) -> dict[str, Any]:
    if not config_yaml_path.exists():
        return {}
    return yaml.safe_load(config_yaml_path.read_text(encoding="utf-8")) or {}


def pick_observations(
    *,
    best_entry: dict[str, Any] | None,
    final_entry: dict[str, Any] | None,
    oracle_delta_mae: float | None,
    tm_pearson_r: float | None,
    gate_mean: float | None,
) -> list[str]:
    observations: list[str] = []
    if best_entry is not None and final_entry is not None:
        best_mae = safe_float(best_entry.get("val_mae"))
        final_mae = safe_float(final_entry.get("val_mae"))
        if best_mae is not None and final_mae is not None and final_mae > best_mae + 0.02:
            observations.append(
                f"Validation MAE degraded from {best_mae:.3f} at the best Phase 2 epoch "
                f"to {final_mae:.3f} at the final logged epoch, consistent with overfitting."
            )
    if oracle_delta_mae is not None:
        if oracle_delta_mae < -0.05:
            observations.append(
                f"T_m-only oracle substitution improved test MAE by {-oracle_delta_mae:.3f}, "
                "so melting-point error is a material part of the residual gap."
            )
        elif oracle_delta_mae > -0.01:
            observations.append(
                "T_m-only oracle substitution changed MAE only marginally, so the residual gap is not primarily a T_m issue."
            )
    if tm_pearson_r is not None and tm_pearson_r < 0.5:
        observations.append(
            f"T_m correlation remains weak (Pearson r={tm_pearson_r:.3f}), which limits solver fidelity."
        )
    if gate_mean is not None:
        observations.append(
            f"The correction gate averaged {gate_mean:.3f} on the test set, quantifying how much the learned residual path was used."
        )
    return observations


def build_summary_markdown(summary: dict[str, Any]) -> str:
    cfg = summary["configuration"]
    results = summary["results"]
    overfit = summary["overfitting_analysis"]
    observations = summary["key_observations"]
    lines = [
        "# TGNN Baseline Medium-Budget Results",
        "",
        "## Configuration",
        f"- Config: {cfg['config_label']}",
        f"- Budget: {cfg['budget']}",
        f"- Dropout: {cfg['dropout']}",
        f"- Early stopping: {cfg['early_stopping']}",
        "",
        "## Results",
        (
            f"- Best val MAE: {results['best_val_mae']:.3f} "
            f"(epoch {results['best_epoch']} Phase {results['best_phase']})"
            if results.get("best_val_mae") is not None
            else "- Best val MAE: n/a"
        ),
        f"- Final test MAE: {results['test_mae']:.3f}" if results.get("test_mae") is not None else "- Final test MAE: n/a",
        f"- RMSE: {results['test_rmse']:.3f}" if results.get("test_rmse") is not None else "- RMSE: n/a",
        f"- R²: {results['test_r2']:.3f}" if results.get("test_r2") is not None else "- R²: n/a",
        f"- T_m MAE: {results['tm_mae_K']:.3f} K" if results.get("tm_mae_K") is not None else "- T_m MAE: n/a",
        f"- T_m Pearson r: {results['tm_pearson_r']:.3f}" if results.get("tm_pearson_r") is not None else "- T_m Pearson r: n/a",
        (
            f"- Oracle T_m-only MAE: {results['oracle_tm_test_mae']:.3f}"
            if results.get("oracle_tm_test_mae") is not None
            else "- Oracle T_m-only MAE: n/a"
        ),
        (
            f"- Gate mean: {results['gate_mean']:.3f}"
            if results.get("gate_mean") is not None
            else "- Gate mean: n/a"
        ),
        (
            f"- Correction mean magnitude: {results['correction_mean_magnitude']:.3f}"
            if results.get("correction_mean_magnitude") is not None
            else "- Correction mean magnitude: n/a"
        ),
        "",
        "## Overfitting Analysis",
        (
            f"- Train sol_raw / val MAE at best epoch: {overfit['best_epoch_train_sol_over_val_mae']:.4f}"
            if overfit.get("best_epoch_train_sol_over_val_mae") is not None
            else "- Train sol_raw / val MAE at best epoch: n/a"
        ),
        (
            f"- Train sol_raw / val MAE at final epoch: {overfit['final_epoch_train_sol_over_val_mae']:.4f}"
            if overfit.get("final_epoch_train_sol_over_val_mae") is not None
            else "- Train sol_raw / val MAE at final epoch: n/a"
        ),
        (
            f"- tau_reg raw at best epoch: {overfit['best_epoch_tau_reg_raw']:.4f}"
            if overfit.get("best_epoch_tau_reg_raw") is not None
            else "- tau_reg raw at best epoch: n/a"
        ),
        (
            f"- tau_reg raw at final epoch: {overfit['final_epoch_tau_reg_raw']:.4f}"
            if overfit.get("final_epoch_tau_reg_raw") is not None
            else "- tau_reg raw at final epoch: n/a"
        ),
        "",
        "## Checkpoint Selection",
        f"- Source checkpoint: `{summary['checkpoint_selection']['source_checkpoint']}`",
        f"- Exported checkpoint: `{summary['checkpoint_selection']['export_checkpoint']}`",
        f"- Selected state source: `{summary['checkpoint_selection']['selected_state_source']}`",
        (
            f"- `model_state` already matched tracked best: {summary['checkpoint_selection']['model_state_matches_best_state']}"
        ),
        "",
        "## Key Observations",
    ]
    if observations:
        lines.extend(f"- {item}" for item in observations)
    else:
        lines.append("- No automatic observations were generated.")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    source_checkpoint = _bootstrap.resolve_path(args.source_checkpoint)
    export_checkpoint = _bootstrap.resolve_path(args.export_checkpoint)
    train_log = _bootstrap.resolve_path(args.train_log)
    config_yaml = _bootstrap.resolve_path(args.config_yaml)
    test_data = _bootstrap.resolve_path(args.test_data)
    output_dir = _bootstrap.resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.wait:
        log("Waiting for the live medium-budget baseline checkpoint to complete.")
        wait_for_checkpoint_completion(
            source_checkpoint,
            poll_interval_s=float(args.poll_interval_seconds),
            timeout_s=float(args.timeout_hours) * 3600.0,
            log=log,
        )
        log("Checkpoint marked as completed. Starting post-analysis.")

    payload = torch.load(source_checkpoint, map_location="cpu", weights_only=False)
    selected_payload, selection_meta = build_selected_checkpoint_payload(payload)
    atomic_torch_save(selected_payload, export_checkpoint)

    checkpoint_selection = {
        "source_checkpoint": str(source_checkpoint),
        "export_checkpoint": str(export_checkpoint),
        **selection_meta,
    }
    (output_dir / "checkpoint_selection.json").write_text(
        json.dumps(checkpoint_selection, indent=2),
        encoding="utf-8",
    )
    log(f"Exported best checkpoint to {export_checkpoint}")

    evaluation_json = output_dir / "evaluation.json"
    physics_json = output_dir / "physics_validation.json"
    physics_analysis_dir = output_dir / "physics_analysis"
    learning_curves_json = output_dir / "learning_curves.json"
    summary_json = output_dir / "summary.json"
    summary_md = output_dir / "summary.md"

    run_step(
        [
            args.python_executable,
            "scripts/evaluate_complete.py",
            "--test-data",
            str(test_data),
            "--tgnn-checkpoint",
            str(export_checkpoint),
            "--output",
            str(evaluation_json),
            "--verbose",
        ],
        cwd=repo_root,
    )
    run_step(
        [
            args.python_executable,
            "scripts/validate_physics.py",
            "--checkpoint",
            str(export_checkpoint),
            "--test-data",
            str(test_data),
            "--output",
            str(physics_json),
            "--device",
            args.device,
        ],
        cwd=repo_root,
    )
    run_step(
        [
            args.python_executable,
            "scripts/analyze_intermediates.py",
            "--checkpoint",
            str(export_checkpoint),
            "--test-data",
            str(test_data),
            "--output-dir",
            str(physics_analysis_dir),
            "--device",
            args.device,
        ],
        cwd=repo_root,
    )

    learning_curves = parse_training_log(train_log)
    learning_curves_json.write_text(
        json.dumps(learning_curves, indent=2),
        encoding="utf-8",
    )

    evaluation = load_json(evaluation_json)
    physics = load_json(physics_json)
    physics_analysis = load_json(physics_analysis_dir / "summary.json")
    run_config = load_run_config(config_yaml)

    best_entry = learning_curves.get("best_phase2_by_val_mae")
    final_entry = learning_curves.get("final_entry")
    best_tau_reg = safe_float(
        ((best_entry or {}).get("loss_components", {}).get("tau_reg", {}) or {}).get("raw")
    )
    final_tau_reg = safe_float(
        ((final_entry or {}).get("loss_components", {}).get("tau_reg", {}) or {}).get("raw")
    )

    oracle_delta_mae = safe_float(
        (((physics_analysis.get("oracle_tm_only") or {}).get("delta_vs_standard") or {}).get("mae"))
    )
    tm_pearson_r = safe_float((physics_analysis.get("tm_metrics") or {}).get("pearson_r"))
    gate_mean = safe_float((physics_analysis.get("correction_analysis") or {}).get("mean_gate_value"))

    config_dict = payload.get("config") or {}
    checkpoint_cfg_dropout = (
        run_config.get("dropout")
        if isinstance(run_config, dict) and "dropout" in run_config
        else config_dict.get("dropout")
    )
    early_stopping_patience = (
        run_config.get("early_stopping_patience")
        if isinstance(run_config, dict)
        else config_dict.get("early_stopping_patience")
    )
    if early_stopping_patience is None or int(early_stopping_patience) >= 999:
        early_stopping_label = "disabled"
    else:
        early_stopping_label = f"patience={int(early_stopping_patience)}"

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "config_label": args.config_label,
            "budget": (
                f"{config_dict.get('epochs_phase1', 'NA')}/"
                f"{config_dict.get('epochs_phase2', 'NA')}/"
                f"{config_dict.get('epochs_phase3', 'NA')}"
            ),
            "dropout": checkpoint_cfg_dropout,
            "early_stopping": early_stopping_label,
        },
        "checkpoint_selection": checkpoint_selection,
        "results": {
            "best_val_mae": safe_float((best_entry or {}).get("val_mae")),
            "best_epoch": (best_entry or {}).get("epoch"),
            "best_phase": (best_entry or {}).get("phase"),
            "test_mae": safe_float((evaluation.get("overall") or {}).get("mae")),
            "test_rmse": safe_float((evaluation.get("overall") or {}).get("rmse")),
            "test_r2": safe_float((evaluation.get("overall") or {}).get("r2")),
            "tm_mae_K": safe_float((physics_analysis.get("tm_metrics") or {}).get("mae")),
            "tm_pearson_r": safe_float((physics_analysis.get("tm_metrics") or {}).get("pearson_r")),
            "oracle_tm_test_mae": safe_float(
                (((physics_analysis.get("oracle_tm_only") or {}).get("oracle") or {}).get("mae"))
            ),
            "oracle_tm_delta_mae_vs_standard": oracle_delta_mae,
            "gate_mean": gate_mean,
            "correction_mean_magnitude": safe_float(
                (physics_analysis.get("correction_analysis") or {}).get("mean_correction_magnitude")
            ),
        },
        "overfitting_analysis": {
            "best_epoch_train_sol_over_val_mae": safe_float(
                (best_entry or {}).get("train_sol_raw_over_val_mae")
            ),
            "final_epoch_train_sol_over_val_mae": safe_float(
                (final_entry or {}).get("train_sol_raw_over_val_mae")
            ),
            "best_epoch_tau_reg_raw": best_tau_reg,
            "final_epoch_tau_reg_raw": final_tau_reg,
        },
        "artifacts": {
            "evaluation_json": str(evaluation_json),
            "physics_validation_json": str(physics_json),
            "physics_analysis_dir": str(physics_analysis_dir),
            "learning_curves_json": str(learning_curves_json),
        },
        "learning_curves": {
            "best_phase2_by_val_mae": best_entry,
            "final_entry": final_entry,
            "n_entries": learning_curves.get("n_entries"),
        },
        "key_observations": pick_observations(
            best_entry=best_entry,
            final_entry=final_entry,
            oracle_delta_mae=oracle_delta_mae,
            tm_pearson_r=tm_pearson_r,
            gate_mean=gate_mean,
        ),
        "physics_validation": {
            "property_validation": physics.get("property_validation"),
            "correction_gate": physics.get("correction_gate"),
            "vant_hoff": physics.get("vant_hoff"),
        },
    }

    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(build_summary_markdown(summary), encoding="utf-8")
    log(f"Wrote summary artifacts to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
