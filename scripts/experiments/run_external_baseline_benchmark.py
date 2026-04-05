#!/usr/bin/env python3
"""Run external baseline benchmark workflows on TGNN-Solv splits."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
import pandas as pd

from tgnn_solv.reporting import json_safe


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_command(command: list[str], *, env_overrides: dict[str, str] | None = None) -> None:
    print("\n[Command]")
    print(" ".join(command))
    env = os.environ.copy()
    if env_overrides:
        env.update({k: v for k, v in env_overrides.items() if v})
    subprocess.run(command, cwd=REPO_ROOT, check=True, env=env)


def _summary_from_report(report_path: Path) -> pd.DataFrame:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    overall = payload.get("overall", {})
    model_name = payload.get("model") or (payload.get("metadata") or {}).get("model") or report_path.parent.name
    split_meta = payload.get("split") or (payload.get("metadata") or {}).get("split") or {}
    return pd.DataFrame(
        [
            {
                "model": model_name,
                "mae": overall.get("mae"),
                "rmse": overall.get("rmse"),
                "r2": overall.get("r2"),
                "bias": overall.get("bias"),
                "n_samples": overall.get("n_samples", overall.get("n")),
                "n_predictions": overall.get("n_predictions"),
                "split": (
                    split_meta.get("split_mode") or split_meta.get("mode")
                    if isinstance(split_meta, dict)
                    else None
                ),
                "artifact": str(report_path),
            }
        ]
    )


def _collect_summary_rows(root: Path) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    summary_dirs: set[Path] = set()
    summary_paths = sorted(root.rglob("summary.csv"), key=lambda path: (len(path.relative_to(root).parts), str(path)))
    for summary_path in summary_paths:
        if summary_path.resolve() == (root / "summary.csv").resolve():
            continue
        resolved_parent = summary_path.parent.resolve()
        if any(parent in summary_dirs for parent in resolved_parent.parents):
            continue
        try:
            frame = pd.read_csv(summary_path)
        except Exception:
            continue
        if frame.empty:
            continue
        frame = frame.copy()
        frame["artifact"] = str(summary_path)
        rows.append(frame)
        summary_dirs.add(resolved_parent)

    reports: list[pd.DataFrame] = []
    for report_path in sorted(root.rglob("report.json")):
        resolved_parent = report_path.parent.resolve()
        if resolved_parent in summary_dirs or any(parent in summary_dirs for parent in resolved_parent.parents):
            continue
        try:
            reports.append(_summary_from_report(report_path))
        except Exception:
            continue
    if rows and reports:
        return pd.concat([*rows, *reports], axis=0, ignore_index=True)
    if rows:
        return pd.concat(rows, axis=0, ignore_index=True)
    if reports:
        return pd.concat(reports, axis=0, ignore_index=True)
    return pd.DataFrame()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run FastSolv and SolProp benchmark workflows on TGNN-Solv splits."
    )
    parser.add_argument("--train-data", required=True)
    parser.add_argument("--val-data", required=True)
    parser.add_argument("--test-data", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--python", default=sys.executable, help="Python executable or launcher.")
    parser.add_argument("--fastsolv-python", default=None, help="Optional dedicated Python for FastSolv commands.")
    parser.add_argument("--solprop-python", default=None, help="Optional dedicated Python for SolProp commands.")
    parser.add_argument("--solprop-runtime-dir", default=None, help="Optional local runtime dir created by `scripts/external/install_solprop_runtime.py`.")
    parser.add_argument("--split-mode", default="solute_scaffold")
    parser.add_argument("--continue-on-error", action="store_true")

    parser.add_argument("--fastsolv-mode", choices=["skip", "pretrained", "scratch", "both"], default="both")
    parser.add_argument("--fastsolv-batch-size", type=int, default=256)
    parser.add_argument("--fastsolv-descriptor-nproc", type=int, default=1)
    parser.add_argument("--fastsolv-epochs", type=int, default=40)
    parser.add_argument("--fastsolv-patience", type=int, default=10)
    parser.add_argument("--fastsolv-lr", type=float, default=1e-4)
    parser.add_argument("--fastsolv-lr-scale", type=float, default=0.1)

    parser.add_argument(
        "--solprop-mode",
        choices=["skip", "zero_shot", "calibrated", "native", "both", "all"],
        default="native",
    )
    parser.add_argument("--solprop-batch-size", type=int, default=256)
    parser.add_argument("--solprop-temperature-dependent", action="store_true")
    parser.add_argument("--solprop-include-temperature", action="store_true")
    parser.add_argument("--solprop-reduced-number", action="store_true")
    parser.add_argument("--solprop-native-device", default="auto")
    parser.add_argument("--solprop-native-epochs", type=int, default=40)
    parser.add_argument("--solprop-native-patience", type=int, default=10)
    parser.add_argument("--solprop-native-num-models", type=int, default=5)
    parser.add_argument("--solprop-native-seed", type=int, default=42)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def execute(name: str, command: list[str], output_root: Path, *, env_overrides: dict[str, str] | None = None) -> None:
        try:
            _run_command(command, env_overrides=env_overrides)
            runs.append({"name": name, "output_root": str(output_root), "command": command})
        except subprocess.CalledProcessError as exc:
            failure = {"name": name, "output_root": str(output_root), "command": command, "returncode": exc.returncode}
            failures.append(failure)
            if not args.continue_on_error:
                raise

    python = args.python
    fastsolv_python = args.fastsolv_python or python
    solprop_python = args.solprop_python or python
    solprop_env = {"SOLPROP_RUNTIME_DIR": args.solprop_runtime_dir} if args.solprop_runtime_dir else None

    if args.fastsolv_mode in {"pretrained", "both"}:
        root = out_dir / "fastsolv_pretrained"
        execute(
            "fastsolv_pretrained",
            [
                fastsolv_python,
                "scripts/run_fastsolv.py",
                "predict",
                "--input",
                args.test_data,
                "--output",
                str(root / "predictions.csv"),
                "--metrics",
                str(root / "report.json"),
                "--split-mode",
                args.split_mode,
                "--batch-size",
                str(int(args.fastsolv_batch_size)),
                "--descriptor-nproc",
                str(int(args.fastsolv_descriptor_nproc)),
            ],
            root,
        )

    if args.fastsolv_mode in {"scratch", "both"}:
        root = out_dir / "fastsolv_scratch"
        execute(
            "fastsolv_scratch",
            [
                fastsolv_python,
                "scripts/run_fastsolv.py",
                "train",
                "--train",
                args.train_data,
                "--val",
                args.val_data,
                "--test",
                args.test_data,
                "--outdir",
                str(root),
                "--epochs",
                str(int(args.fastsolv_epochs)),
                "--patience",
                str(int(args.fastsolv_patience)),
                "--batch-size",
                str(int(args.fastsolv_batch_size)),
                "--lr",
                str(float(args.fastsolv_lr)),
                "--lr-scale",
                str(float(args.fastsolv_lr_scale)),
                "--descriptor-nproc",
                str(int(args.fastsolv_descriptor_nproc)),
                "--split-mode",
                args.split_mode,
                "--disable-custom-loss",
            ],
            root,
        )

    if args.solprop_mode in {"zero_shot", "both", "all"}:
        root = out_dir / "solprop_zero_shot"
        command = [
            solprop_python,
            "scripts/run_solprop.py",
            "predict",
            "--input",
            args.test_data,
            "--output",
            str(root / "predictions.csv"),
            "--metrics",
            str(root / "report.json"),
            "--split-mode",
            args.split_mode,
            "--batch-size",
            str(int(args.solprop_batch_size)),
        ]
        if args.solprop_temperature_dependent:
            command.append("--temperature-dependent")
        if args.solprop_reduced_number:
            command.append("--reduced-number")
        execute("solprop_zero_shot", command, root, env_overrides=solprop_env)

    if args.solprop_mode in {"calibrated", "both", "all"}:
        root = out_dir / "solprop_calibrated"
        command = [
            solprop_python,
            "scripts/run_solprop.py",
            "train",
            "--train",
            args.train_data,
            "--val",
            args.val_data,
            "--test",
            args.test_data,
            "--outdir",
            str(root),
            "--batch-size",
            str(int(args.solprop_batch_size)),
        ]
        if args.solprop_temperature_dependent:
            command.append("--temperature-dependent")
        if args.solprop_include_temperature:
            command.append("--include-temperature")
        if args.solprop_reduced_number:
            command.append("--reduced-number")
        execute("solprop_calibrated", command, root, env_overrides=solprop_env)

    if args.solprop_mode in {"native", "all"}:
        root = out_dir / "solprop_native"
        command = [
            solprop_python,
            "scripts/run_solprop.py",
            "train-native",
            "--train",
            args.train_data,
            "--val",
            args.val_data,
            "--test",
            args.test_data,
            "--outdir",
            str(root),
            "--device",
            args.solprop_native_device,
            "--epochs",
            str(int(args.solprop_native_epochs)),
            "--patience",
            str(int(args.solprop_native_patience)),
            "--batch-size",
            str(int(args.solprop_batch_size)),
            "--num-models",
            str(int(args.solprop_native_num_models)),
            "--seed",
            str(int(args.solprop_native_seed)),
        ]
        execute("solprop_native", command, root, env_overrides=solprop_env)

    summary = _collect_summary_rows(out_dir)
    if not summary.empty:
        summary.to_csv(out_dir / "summary.csv", index=False)

    comparison = {
        "report_type": "external_baseline_benchmark",
        "out_dir": str(out_dir),
        "train_data": args.train_data,
        "val_data": args.val_data,
        "test_data": args.test_data,
        "split_mode": args.split_mode,
        "runs": runs,
        "failures": failures,
        "summary_rows": json_safe(summary.to_dict(orient="records")) if not summary.empty else [],
    }
    if not summary.empty and "mae" in summary.columns:
        ranked = summary.dropna(subset=["mae"]).copy()
        if "split" in ranked.columns:
            split_series = ranked["split"].fillna("").astype(str)
            preferred_mask = split_series.isin({str(args.split_mode), "test"})
            if preferred_mask.any():
                ranked = ranked.loc[preferred_mask].copy()
        ranked = ranked.sort_values("mae", ascending=True)
        if not ranked.empty:
            comparison["best_model"] = json_safe(ranked.iloc[0].to_dict())
    (out_dir / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
