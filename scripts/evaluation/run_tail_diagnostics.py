#!/usr/bin/env python
"""Compute tail-aware diagnostics for maintained benchmark models."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from rdkit import RDLogger
from torch import Tensor

import sys

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: E402,F401

from run_full_budget_experiment import build_loader
from tgnn_solv.baselines.direct_gnn import DirectGNN, DirectGNNTrainer
from tgnn_solv.baselines.rf_baseline import RFBaseline
from tgnn_solv.inference import load_directgnn_model


@dataclass
class PredictionBundle:
    model_name: str
    split_name: str
    frame: pd.DataFrame
    overall: dict[str, float | int | None]


def _log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run tail-aware diagnostics on maintained benchmark artifacts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--out-dir",
        default="results/tail_diagnostics",
        help="Output directory for diagnostics artifacts.",
    )
    parser.add_argument(
        "--train-data",
        default="notebooks/data/processed/train.csv",
        help="Maintained scaffold train CSV for RF refit.",
    )
    parser.add_argument(
        "--test-data",
        default="notebooks/data/processed/test.csv",
        help="Maintained scaffold test CSV for diagnostics.",
    )
    parser.add_argument(
        "--directgnn-checkpoint",
        default="checkpoints/proxy/directgnn_tuned.pt",
        help="DirectGNN checkpoint used for maintained scaffold headline numbers.",
    )
    parser.add_argument(
        "--tgnn-report",
        default="results/proxy_comparison/tgnn_mpnn.json",
        help="TGNN evaluation report containing `predictions.true_ln_x2/pred_ln_x2`.",
    )
    parser.add_argument(
        "--rf-feature-mode",
        default="hybrid",
        choices=["descriptors", "morgan", "hybrid"],
        help="RF feature mode for scaffold refit.",
    )
    parser.add_argument(
        "--rf-n-estimators",
        type=int,
        default=500,
        help="RF number of trees for scaffold refit.",
    )
    parser.add_argument(
        "--rf-max-depth",
        type=int,
        default=30,
        help="RF max depth for scaffold refit.",
    )
    parser.add_argument(
        "--rf-n-jobs",
        type=int,
        default=1,
        help="RF internal parallelism.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Loader/build seed for DirectGNN evaluation.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Device for DirectGNN evaluation.",
    )
    parser.add_argument(
        "--trim-threshold",
        type=float,
        default=-15.0,
        help="Rows with ln_x2 <= threshold are excluded from the trimmed view.",
    )
    parser.add_argument(
        "--bin-edges",
        default="-25,-15,-12,-9,-6,-3,0",
        help="Comma-separated ln_x2 bin edges.",
    )
    return parser.parse_args()


def _regression_metrics(true: np.ndarray, pred: np.ndarray) -> dict[str, float | int | None]:
    true = np.asarray(true, dtype=float)
    pred = np.asarray(pred, dtype=float)
    mask = np.isfinite(true) & np.isfinite(pred)
    true = true[mask]
    pred = pred[mask]
    if true.size == 0:
        return {
            "n_samples": 0,
            "mae": None,
            "rmse": None,
            "r2": None,
            "bias": None,
            "pearson_r": None,
        }

    errors = pred - true
    ss_res = float(np.sum(errors ** 2))
    ss_tot = float(np.sum((true - np.mean(true)) ** 2))
    pearson_r = None
    if true.size > 1 and np.std(true) > 0 and np.std(pred) > 0:
        pearson_r = float(np.corrcoef(true, pred)[0, 1])
    return {
        "n_samples": int(true.size),
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
        "r2": float(1.0 - ss_res / (ss_tot + 1e-10)),
        "bias": float(np.mean(errors)),
        "pearson_r": pearson_r,
    }


def _collect_direct_predictions(
    model: DirectGNN,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
) -> pd.DataFrame:
    trainer = DirectGNNTrainer(model, device=device)
    trainer.model.eval()
    dataset_df = loader.dataset.df.reset_index(drop=True)
    rows: list[pd.DataFrame] = []
    cursor = 0

    with torch.no_grad():
        for sol_b, slv_b, tgt in loader:
            sol_b = sol_b.to(device)
            slv_b = slv_b.to(device)
            T = tgt["T"].to(device)
            solvent_type = tgt.get("solvent_type")
            solute_morgan_fp = tgt.get("solute_morgan_fp")
            solvent_morgan_fp = tgt.get("solvent_morgan_fp")
            solute_descriptors = tgt.get("solute_descriptors")
            solvent_descriptors = tgt.get("solvent_descriptors")
            mask = tgt["has_solubility"].to(dtype=torch.bool)

            batch_size = int(T.shape[0])
            batch_df = dataset_df.iloc[cursor:cursor + batch_size].copy().reset_index(drop=True)
            cursor += batch_size

            if not mask.any():
                continue

            out = trainer.model(
                sol_b,
                slv_b,
                T,
                solvent_type=solvent_type,
                solute_morgan_fp=(
                    solute_morgan_fp.to(device)
                    if isinstance(solute_morgan_fp, Tensor)
                    else None
                ),
                solvent_morgan_fp=(
                    solvent_morgan_fp.to(device)
                    if isinstance(solvent_morgan_fp, Tensor)
                    else None
                ),
                solute_descriptors=(
                    solute_descriptors.to(device)
                    if isinstance(solute_descriptors, Tensor)
                    else None
                ),
                solvent_descriptors=(
                    solvent_descriptors.to(device)
                    if isinstance(solvent_descriptors, Tensor)
                    else None
                ),
            )
            keep = mask.cpu().numpy().astype(bool)
            kept = batch_df.loc[keep].copy().reset_index(drop=True)
            kept["ln_x2_true"] = tgt["ln_x2"][mask].cpu().numpy()
            kept["ln_x2_pred"] = out["ln_x2"].detach().cpu()[mask].numpy()
            rows.append(kept)

    if not rows:
        raise ValueError("DirectGNN evaluation produced no supervised predictions.")
    return pd.concat(rows, axis=0, ignore_index=True)


def _load_tgnn_predictions(report_path: Path, test_df: pd.DataFrame) -> pd.DataFrame:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    preds = report.get("predictions") or {}
    row_indices = np.asarray(preds.get("row_indices") or [], dtype=int)
    true = np.asarray(preds.get("true_ln_x2") or [], dtype=float)
    pred = np.asarray(preds.get("pred_ln_x2") or [], dtype=float)
    if row_indices.size == 0 or true.size == 0 or pred.size == 0:
        raise ValueError(f"TGNN report does not contain serialized prediction arrays: {report_path}")
    if not (len(row_indices) == len(true) == len(pred)):
        raise ValueError("TGNN serialized prediction arrays have mismatched lengths.")

    base = test_df.copy()
    if "row_index" not in base.columns:
        base = base.reset_index().rename(columns={"index": "row_index"})
    merged = base.iloc[row_indices].copy().reset_index(drop=True)
    merged["ln_x2_true"] = true
    merged["ln_x2_pred"] = pred
    return merged


def _fit_rf_predictions(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    feature_mode: str,
    n_estimators: int,
    max_depth: int,
    n_jobs: int,
    random_state: int,
) -> pd.DataFrame:
    rf = RFBaseline(
        n_estimators=n_estimators,
        max_depth=max_depth,
        n_jobs=n_jobs,
        random_state=random_state,
        feature_mode=feature_mode,
    )
    RDLogger.DisableLog("rdApp.warning")
    RDLogger.DisableLog("rdApp.error")
    try:
        rf.fit(train_df)
        eval_df = rf._supervised_view(test_df).reset_index(drop=True)
        pred, valid_idx = rf.predict(eval_df)
    finally:
        RDLogger.EnableLog("rdApp.warning")
        RDLogger.EnableLog("rdApp.error")
    out = eval_df.iloc[valid_idx].copy().reset_index(drop=True)
    out["ln_x2_true"] = out["ln_x2"].astype(float)
    out["ln_x2_pred"] = pred
    return out


def _bin_table(bundle: PredictionBundle, edges: list[float]) -> pd.DataFrame:
    frame = bundle.frame.copy()
    cats = pd.cut(
        frame["ln_x2_true"].astype(float),
        bins=edges,
        right=True,
        include_lowest=True,
    )
    rows: list[dict[str, Any]] = []
    for cat in cats.cat.categories:
        mask = cats == cat
        subset = frame.loc[mask]
        metrics = _regression_metrics(subset["ln_x2_true"].to_numpy(), subset["ln_x2_pred"].to_numpy())
        rows.append(
            {
                "model": bundle.model_name,
                "split": bundle.split_name,
                "bin": str(cat),
                "n_samples": int(mask.sum()),
                "true_mean": float(subset["ln_x2_true"].mean()) if len(subset) else None,
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def _trimmed_rows(bundle: PredictionBundle, threshold: float) -> list[dict[str, Any]]:
    frame = bundle.frame.copy()
    full = _regression_metrics(frame["ln_x2_true"].to_numpy(), frame["ln_x2_pred"].to_numpy())
    trimmed = frame.loc[frame["ln_x2_true"].astype(float) > float(threshold)].copy()
    trimmed_metrics = _regression_metrics(
        trimmed["ln_x2_true"].to_numpy(),
        trimmed["ln_x2_pred"].to_numpy(),
    )
    tail = frame.loc[frame["ln_x2_true"].astype(float) <= float(threshold)].copy()
    tail_metrics = _regression_metrics(
        tail["ln_x2_true"].to_numpy(),
        tail["ln_x2_pred"].to_numpy(),
    )
    return [
        {
            "model": bundle.model_name,
            "split": bundle.split_name,
            "slice": "all_supervised",
            "threshold": threshold,
            **full,
        },
        {
            "model": bundle.model_name,
            "split": bundle.split_name,
            "slice": f"trimmed_gt_{threshold:g}",
            "threshold": threshold,
            **trimmed_metrics,
        },
        {
            "model": bundle.model_name,
            "split": bundle.split_name,
            "slice": f"tail_le_{threshold:g}",
            "threshold": threshold,
            **tail_metrics,
        },
    ]


def _load_external_predictions(predictions_csv: Path, *, model_name: str, split_name: str) -> PredictionBundle:
    df = pd.read_csv(predictions_csv)
    pred_candidates = [
        "ln_x2_pred",
        "pred_ln_x2",
        "solprop_native_ln_x2",
        "solprop_ln_x2",
        "fastsolv_ln_x2",
    ]
    pred_col = next((col for col in pred_candidates if col in df.columns), None)
    if pred_col is not None and pred_col != "ln_x2_pred":
        df["ln_x2_pred"] = pd.to_numeric(df[pred_col], errors="coerce")
    if "ln_x2_true" not in df.columns and "ln_x2" in df.columns:
        df["ln_x2_true"] = pd.to_numeric(df["ln_x2"], errors="coerce")
    if "ln_x2_true" not in df.columns or "ln_x2_pred" not in df.columns:
        raise ValueError(f"Predictions CSV missing required columns: {predictions_csv}")
    overall = _regression_metrics(df["ln_x2_true"].to_numpy(), df["ln_x2_pred"].to_numpy())
    return PredictionBundle(model_name=model_name, split_name=split_name, frame=df, overall=overall)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    progress_path = out_dir / "progress.json"

    def write_progress(step: str, **extra: Any) -> None:
        payload = {"step": step, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        payload.update(extra)
        progress_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    bin_edges = [float(v) for v in str(args.bin_edges).split(",") if str(v).strip()]
    if len(bin_edges) < 2:
        raise ValueError("Provide at least two bin edges.")
    if sorted(bin_edges) != bin_edges:
        raise ValueError("Bin edges must be sorted ascending.")

    _log("Loading maintained scaffold train/test CSVs")
    write_progress("loading_data")
    train_df = pd.read_csv(args.train_data).reset_index(drop=True)
    test_df = pd.read_csv(args.test_data).reset_index().rename(columns={"index": "row_index"})

    bundles: list[PredictionBundle] = []

    # DirectGNN scaffold predictions from checkpoint inference.
    _log(f"Evaluating DirectGNN from {args.directgnn_checkpoint}")
    write_progress("directgnn_eval")
    direct_checkpoint = Path(args.directgnn_checkpoint)
    direct_model, direct_cfg = load_directgnn_model(str(direct_checkpoint), device=torch.device(args.device))
    direct_loader = build_loader(test_df, direct_cfg, seed=int(args.seed))
    direct_frame = _collect_direct_predictions(direct_model, direct_loader, torch.device(args.device))
    direct_overall = _regression_metrics(direct_frame["ln_x2_true"].to_numpy(), direct_frame["ln_x2_pred"].to_numpy())
    bundles.append(PredictionBundle("DirectGNN", "scaffold", direct_frame, direct_overall))
    direct_frame.to_csv(out_dir / "directgnn_scaffold_predictions.csv", index=False)
    _log(
        "DirectGNN done: "
        f"n={direct_overall['n_samples']} mae={direct_overall['mae']:.3f} r2={direct_overall['r2']:.3f}"
    )

    # TGNN scaffold predictions from serialized report arrays.
    _log(f"Loading TGNN serialized predictions from {args.tgnn_report}")
    write_progress("tgnn_eval")
    tgnn_frame = _load_tgnn_predictions(Path(args.tgnn_report), test_df)
    tgnn_overall = _regression_metrics(tgnn_frame["ln_x2_true"].to_numpy(), tgnn_frame["ln_x2_pred"].to_numpy())
    bundles.append(PredictionBundle("TGNN_MPNN", "scaffold", tgnn_frame, tgnn_overall))
    tgnn_frame.to_csv(out_dir / "tgnn_mpnn_scaffold_predictions.csv", index=False)
    _log(
        "TGNN done: "
        f"n={tgnn_overall['n_samples']} mae={tgnn_overall['mae']:.3f} r2={tgnn_overall['r2']:.3f}"
    )

    # RF scaffold predictions via reproducible refit.
    _log(
        "Fitting RF refit: "
        f"feature_mode={args.rf_feature_mode} n_estimators={args.rf_n_estimators} "
        f"max_depth={args.rf_max_depth} n_jobs={args.rf_n_jobs}"
    )
    write_progress(
        "rf_refit",
        rf_feature_mode=str(args.rf_feature_mode),
        rf_n_estimators=int(args.rf_n_estimators),
        rf_max_depth=int(args.rf_max_depth),
        rf_n_jobs=int(args.rf_n_jobs),
    )
    rf_frame = _fit_rf_predictions(
        train_df,
        test_df,
        feature_mode=str(args.rf_feature_mode),
        n_estimators=int(args.rf_n_estimators),
        max_depth=int(args.rf_max_depth),
        n_jobs=int(args.rf_n_jobs),
        random_state=int(args.seed),
    )
    rf_overall = _regression_metrics(rf_frame["ln_x2_true"].to_numpy(), rf_frame["ln_x2_pred"].to_numpy())
    bundles.append(PredictionBundle("RF_hybrid_refit", "scaffold", rf_frame, rf_overall))
    rf_frame.to_csv(out_dir / "rf_hybrid_scaffold_predictions.csv", index=False)
    _log(
        "RF done: "
        f"n={rf_overall['n_samples']} mae={rf_overall['mae']:.3f} r2={rf_overall['r2']:.3f}"
    )

    # Optional already-computed external solute bundles, if present.
    _log("Loading optional external prediction bundles if present")
    write_progress("external_bundle_load")
    optional_sources = [
        (
            Path("results/external_baselines/solute/solprop_native_contract_v2/test/predictions.csv"),
            "SolProp_native",
            "solute",
        ),
        (
            Path("results/external_baselines/solute/fastsolv_contract_v2/test/predictions.csv"),
            "FastSolv",
            "solute",
        ),
        (
            Path("results/external_baselines/pair_random/solprop_native_contract_v2/test/predictions.csv"),
            "SolProp_native",
            "pair_random",
        ),
        (
            Path("results/external_baselines/pair_random/solprop_calibrated_contract_v2/test/calibrated/predictions.csv"),
            "SolProp_calibrated",
            "pair_random",
        ),
    ]
    for predictions_csv, model_name, split_name in optional_sources:
        path = Path(predictions_csv)
        if path.exists():
            bundles.append(_load_external_predictions(path, model_name=model_name, split_name=split_name))
            _log(f"Loaded external bundle: model={model_name} split={split_name}")

    _log("Computing tail-bin and trimmed metrics")
    write_progress("aggregating_metrics", n_bundles=len(bundles))
    all_bins = pd.concat([_bin_table(bundle, bin_edges) for bundle in bundles], axis=0, ignore_index=True)
    all_trimmed = pd.DataFrame(
        [row for bundle in bundles for row in _trimmed_rows(bundle, float(args.trim_threshold))]
    )

    summary = {
        "trim_threshold": float(args.trim_threshold),
        "bin_edges": bin_edges,
        "bundles": [
            {
                "model": bundle.model_name,
                "split": bundle.split_name,
                "overall": bundle.overall,
                "n_rows": int(len(bundle.frame)),
            }
            for bundle in bundles
        ],
    }

    write_progress("writing_outputs", n_bundles=len(bundles))
    all_bins.to_csv(out_dir / "bin_metrics.csv", index=False)
    all_trimmed.to_csv(out_dir / "trimmed_metrics.csv", index=False)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_progress("completed", n_bundles=len(bundles))
    _log(f"Saved tail diagnostics to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
