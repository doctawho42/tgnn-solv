#!/usr/bin/env python3
"""Structured article-reproduction runner."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401

from tgnn_solv.reproduction import (
    PROFILE_CHOICES,
    ReproductionSettings,
    actual_command_for_step,
    build_reproduction_steps,
    quote_command,
    reproduction_profiles,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the maintained TGNN-Solv article-reproduction workflow.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--profile", choices=PROFILE_CHOICES, default="article")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--python-command", default=sys.executable)
    parser.add_argument("--processed-dir", default="notebooks/data/processed")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--checkpoints-dir", default="checkpoints")
    parser.add_argument("--figures-dir", default="figures")
    parser.add_argument("--tables-dir", default="tables")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-seeds", type=int, default=5)
    parser.add_argument("--split-mode", default="solute_scaffold")
    parser.add_argument("--fastsolv-mode", choices=["both", "pretrained", "scratch", "skip"], default="both")
    parser.add_argument(
        "--solprop-mode",
        choices=["native", "both", "all", "zero_shot", "calibrated", "skip"],
        default="native",
    )
    parser.add_argument("--fastsolv-python", default=None)
    parser.add_argument("--solprop-python", default=None)
    parser.add_argument("--solprop-runtime-dir", default=None)
    parser.add_argument("--solprop-native-device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--no-external-continue-on-error", action="store_true")
    parser.add_argument("--step", action="append", default=[], help="Run only the selected step id. Can be passed multiple times.")
    parser.add_argument("--skip-step", action="append", default=[], help="Skip the selected step id. Can be passed multiple times.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-steps", action="store_true")
    parser.add_argument("--list-format", choices=["text", "json"], default="text")
    parser.add_argument(
        "--summary-json",
        default=None,
        help="Where to write the structured run summary. Defaults to results/reproduction/<profile>_summary.json.",
    )
    return parser


def make_settings(args: argparse.Namespace) -> ReproductionSettings:
    return ReproductionSettings(
        profile=args.profile,
        python_command=args.python_command,
        device=args.device,
        processed_dir=args.processed_dir,
        results_dir=args.results_dir,
        checkpoints_dir=args.checkpoints_dir,
        figures_dir=args.figures_dir,
        tables_dir=args.tables_dir,
        seed=int(args.seed),
        n_seeds=int(args.n_seeds),
        split_mode=args.split_mode,
        fastsolv_mode=args.fastsolv_mode,
        solprop_mode=args.solprop_mode,
        fastsolv_python=args.fastsolv_python,
        solprop_python=args.solprop_python,
        solprop_runtime_dir=args.solprop_runtime_dir,
        solprop_native_device=args.solprop_native_device,
        external_continue_on_error=not bool(args.no_external_continue_on_error),
    )


def filter_steps(
    steps: list[Any],
    only_steps: list[str],
    skip_steps: list[str],
) -> list[Any]:
    only_set = {item.strip() for item in only_steps if item.strip()}
    skip_set = {item.strip() for item in skip_steps if item.strip()}
    filtered = [step for step in steps if (not only_set or step.step_id in only_set) and step.step_id not in skip_set]
    return filtered


def validate_runtime(settings: ReproductionSettings) -> None:
    check_command = shlex.split(settings.python_command) + [
        "-c",
        "import torch, torch_geometric, tgnn_solv; print('runtime_ok')",
    ]
    subprocess.run(check_command, check=True, cwd=_bootstrap.REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def step_summary_path(settings: ReproductionSettings, explicit: str | None) -> Path:
    if explicit:
        return _bootstrap.resolve_path(explicit)
    return _bootstrap.resolve_path(
        str(Path(settings.results_dir) / "reproduction" / f"{settings.profile}_summary.json")
    )


def print_step_listing(steps: list[Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps([asdict(step) for step in steps], indent=2))
        return
    for index, step in enumerate(steps, start=1):
        print(f"{index:02d}. {step.step_id} :: {step.name}")
        print(f"    {step.description}")
        print(f"    command: {quote_command(step.command_preview)}")
        if step.expected_outputs:
            print(f"    outputs: {', '.join(step.expected_outputs)}")


def main() -> int:
    args = build_parser().parse_args()
    settings = make_settings(args)
    steps = filter_steps(
        build_reproduction_steps(settings),
        only_steps=args.step,
        skip_steps=args.skip_step,
    )
    if not steps:
        raise ValueError("No reproduction steps remain after applying step filters.")

    if args.list_steps:
        print_step_listing(steps, as_json=args.list_format == "json")
        return 0

    summary_path = step_summary_path(settings, args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    validate_runtime(settings)

    profile_docs = reproduction_profiles()
    state: dict[str, Any] = {}
    run_summary: dict[str, Any] = {
        "profile": settings.profile,
        "profile_description": profile_docs.get(settings.profile),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "settings": asdict(settings),
        "dry_run": bool(args.dry_run),
        "steps": [],
    }

    for index, step in enumerate(steps, start=1):
        command = actual_command_for_step(step, settings, state)
        print(f"[{index}/{len(steps)}] {step.name}")
        print(f"  step_id : {step.step_id}")
        print(f"  command : {quote_command(command)}")
        started = time.time()
        step_record: dict[str, Any] = {
            "index": index,
            "step_id": step.step_id,
            "name": step.name,
            "description": step.description,
            "category": step.category,
            "command": command,
            "expected_outputs": list(step.expected_outputs),
            "optional": bool(step.optional),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if args.dry_run:
            step_record["status"] = "dry_run"
            step_record["runtime_s"] = 0.0
            run_summary["steps"].append(step_record)
            continue
        try:
            subprocess.run(command, check=True, cwd=_bootstrap.REPO_ROOT)
            step_record["status"] = "completed"
        except subprocess.CalledProcessError as exc:
            step_record["status"] = "failed"
            step_record["returncode"] = int(exc.returncode)
            run_summary["steps"].append(step_record)
            step_record["runtime_s"] = round(time.time() - started, 3)
            summary_path.write_text(json.dumps(run_summary, indent=2), encoding="utf-8")
            if args.continue_on_error or step.optional:
                print(f"  warning : step failed with exit code {exc.returncode}, continuing")
                continue
            raise
        step_record["runtime_s"] = round(time.time() - started, 3)
        run_summary["steps"].append(step_record)
        summary_path.write_text(json.dumps(run_summary, indent=2), encoding="utf-8")

    run_summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    run_summary["status"] = "completed"
    summary_path.write_text(json.dumps(run_summary, indent=2), encoding="utf-8")
    print(f"\nReproduction summary written to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
