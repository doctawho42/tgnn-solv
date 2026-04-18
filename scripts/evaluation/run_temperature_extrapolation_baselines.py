#!/usr/bin/env python3
"""CPU-first temperature extrapolation diagnostics.

This script does not retrain TGNN-Solv or DirectGNN. It builds a strict
same-pair temperature extrapolation split and evaluates cheap baselines that
separate the question "is there exploitable high-temperature structure?" from
the expensive neural retraining question.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: E402,F401

try:
    from sklearn.ensemble import RandomForestRegressor  # noqa: E402
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # noqa: E402
except Exception as exc:  # pragma: no cover - optional dependency
    raise ImportError("scikit-learn is required for this diagnostic.") from exc

from rdkit import RDLogger  # noqa: E402

from tgnn_solv.features import smiles_to_morgan_fp  # noqa: E402


RDLogger.DisableLog("rdApp.warning")

MODEL_COLORS = {
    "pair_mean": "#737373",
    "pair_last_low_T": "#525252",
    "pair_linear_T": "#d97706",
    "pair_vant_hoff": "#2563eb",
    "rf_morgan_T": "#4d7c0f",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a same-pair low-temperature/high-temperature extrapolation "
            "split and evaluate cheap CPU baselines."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--processed-dir",
        default="notebooks/data/processed",
        help="Directory with train.csv / val.csv / test.csv to combine.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/temperature_extrapolation_baselines",
        help="Output bundle directory.",
    )
    parser.add_argument(
        "--train-max-k",
        type=float,
        default=310.0,
        help="Rows at or below this temperature are eligible for low-T train/val.",
    )
    parser.add_argument(
        "--test-min-k",
        type=float,
        default=330.0,
        help="Rows at or above this temperature are used as high-T extrapolation test.",
    )
    parser.add_argument(
        "--min-low-points",
        type=int,
        default=3,
        help=(
            "Minimum low-temperature points per pair before the highest low-T "
            "point is held out for validation."
        ),
    )
    parser.add_argument(
        "--min-high-points",
        type=int,
        default=1,
        help="Minimum high-temperature test points per pair.",
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=0,
        help="Optional cap on eligible pairs; 0 means use all.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed used only when --max-pairs samples pairs.",
    )
    parser.add_argument("--morgan-radius", type=int, default=2)
    parser.add_argument("--morgan-n-bits", type=int, default=1024)
    parser.add_argument("--rf-n-estimators", type=int, default=80)
    parser.add_argument("--rf-max-depth", type=int, default=24)
    parser.add_argument("--rf-n-jobs", type=int, default=-1)
    parser.add_argument("--skip-rf", action="store_true")
    parser.add_argument(
        "--presentation-dir",
        default="presentation/figures/generated",
        help="Directory that receives copies of generated PNG/PDF figures.",
    )
    parser.add_argument(
        "--no-presentation-copy",
        action="store_true",
        help="Do not copy figures into presentation/figures/generated.",
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
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _truthy_mask(series: pd.Series) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).to_numpy(dtype=bool)
    return (
        series.fillna(False)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y", "t"})
        .to_numpy(dtype=bool)
    )


def load_combined_processed(processed_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for split in ("train", "val", "test"):
        path = processed_dir / f"{split}.csv"
        frame = pd.read_csv(path, low_memory=False)
        frame["source_split"] = split
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    if "has_solubility" in df.columns:
        df = df.loc[_truthy_mask(df["has_solubility"])].copy()
    df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["ln_x2"] = pd.to_numeric(df["ln_x2"], errors="coerce")
    df = df.loc[
        np.isfinite(df["temperature"].to_numpy(dtype=float))
        & np.isfinite(df["ln_x2"].to_numpy(dtype=float))
    ].copy()
    df["pair_key"] = df["solute_smiles"].astype(str) + ">>" + df["solvent_smiles"].astype(str)
    df = df.sort_values(["pair_key", "temperature", "ln_x2"], kind="stable").reset_index(drop=True)
    df["combined_row_index"] = np.arange(len(df), dtype=int)
    return df


def build_temperature_split(
    df: pd.DataFrame,
    *,
    train_max_k: float,
    test_min_k: float,
    min_low_points: int,
    min_high_points: int,
    max_pairs: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    low = df.loc[df["temperature"] <= float(train_max_k)].copy()
    high = df.loc[df["temperature"] >= float(test_min_k)].copy()

    low_stats = low.groupby("pair_key", sort=False).agg(
        low_count=("ln_x2", "size"),
        low_min_T=("temperature", "min"),
        low_max_T=("temperature", "max"),
        low_mean_ln_x2=("ln_x2", "mean"),
    )
    high_stats = high.groupby("pair_key", sort=False).agg(
        high_count=("ln_x2", "size"),
        high_min_T=("temperature", "min"),
        high_max_T=("temperature", "max"),
        high_mean_ln_x2=("ln_x2", "mean"),
    )
    pair_stats = low_stats.join(high_stats, how="inner")
    pair_stats = pair_stats.loc[
        (pair_stats["low_count"] >= int(min_low_points))
        & (pair_stats["high_count"] >= int(min_high_points))
    ].copy()
    pair_stats["temperature_gap_K"] = pair_stats["high_min_T"] - pair_stats["low_max_T"]
    pair_stats["observed_high_shift"] = (
        pair_stats["high_mean_ln_x2"] - pair_stats["low_mean_ln_x2"]
    )
    pair_stats = pair_stats.sort_values(
        ["temperature_gap_K", "high_count", "low_count"],
        ascending=[False, False, False],
        kind="stable",
    )

    if max_pairs and len(pair_stats) > max_pairs:
        sampled_index = (
            pair_stats.sample(n=int(max_pairs), random_state=int(seed))
            .sort_values(["temperature_gap_K", "high_count", "low_count"], ascending=[False, False, False])
            .index
        )
        pair_stats = pair_stats.loc[sampled_index].copy()

    eligible_pairs = set(pair_stats.index.astype(str))
    selected_low = low.loc[low["pair_key"].isin(eligible_pairs)].copy()
    selected_high = high.loc[high["pair_key"].isin(eligible_pairs)].copy()

    val_indices: list[int] = []
    for _, group in selected_low.groupby("pair_key", sort=False):
        # Highest low-T row is the within-pair validation point; training still
        # sees lower temperatures for the same pair.
        val_indices.append(int(group.sort_values("temperature", kind="stable").index[-1]))
    val_df = selected_low.loc[val_indices].copy()
    train_df = selected_low.drop(index=val_indices).copy()
    test_df = selected_high.copy()

    return (
        train_df.sort_values(["pair_key", "temperature"], kind="stable").reset_index(drop=True),
        val_df.sort_values(["pair_key", "temperature"], kind="stable").reset_index(drop=True),
        test_df.sort_values(["pair_key", "temperature"], kind="stable").reset_index(drop=True),
        pair_stats.reset_index().rename(columns={"index": "pair_key"}),
    )


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[mask]
    y_pred = y_pred[mask]
    if y_true.size == 0:
        return {
            "n_samples": 0,
            "mae": None,
            "rmse": None,
            "r2": None,
            "bias": None,
            "median_abs_error": None,
            "p90_abs_error": None,
        }
    err = y_pred - y_true
    return {
        "n_samples": int(y_true.size),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)) if y_true.size > 1 else None,
        "bias": float(np.mean(err)),
        "median_abs_error": float(np.median(np.abs(err))),
        "p90_abs_error": float(np.quantile(np.abs(err), 0.90)),
    }


def _fit_poly(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    if x.size < 2 or float(np.std(x)) == 0.0:
        return 0.0, float(np.mean(y))
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def pair_baseline_predictions(
    train_df: pd.DataFrame,
    eval_df: pd.DataFrame,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    grouped_train = {pair: group.copy() for pair, group in train_df.groupby("pair_key", sort=False)}

    for pair_key, eval_group in eval_df.groupby("pair_key", sort=False):
        train_group = grouped_train.get(pair_key)
        if train_group is None or train_group.empty:
            continue
        train_group = train_group.sort_values("temperature", kind="stable")
        y_train = train_group["ln_x2"].to_numpy(dtype=float)
        t_train = train_group["temperature"].to_numpy(dtype=float)
        pair_mean = float(np.mean(y_train))
        last_low = float(train_group.iloc[-1]["ln_x2"])
        slope_t, intercept_t = _fit_poly(t_train, y_train)
        slope_inv_t, intercept_inv_t = _fit_poly(1.0 / t_train, y_train)

        for _, row in eval_group.iterrows():
            temp = float(row["temperature"])
            base = {
                "row_index": int(row["combined_row_index"]),
                "pair_key": pair_key,
                "solute_smiles": row["solute_smiles"],
                "solvent_smiles": row["solvent_smiles"],
                "temperature": temp,
                "ln_x2_true": float(row["ln_x2"]),
            }
            model_preds = {
                "pair_mean": pair_mean,
                "pair_last_low_T": last_low,
                "pair_linear_T": slope_t * temp + intercept_t,
                "pair_vant_hoff": slope_inv_t * (1.0 / temp) + intercept_inv_t,
            }
            for model, pred in model_preds.items():
                records.append({**base, "model": model, "ln_x2_pred": float(pred)})

    return pd.DataFrame(records)


def _morgan_cache(smiles_values: pd.Series, *, radius: int, n_bits: int) -> dict[str, np.ndarray | None]:
    cache: dict[str, np.ndarray | None] = {}
    for smiles in smiles_values.dropna().astype(str).drop_duplicates():
        cache[smiles] = smiles_to_morgan_fp(smiles, radius=radius, n_bits=n_bits)
    return cache


def _rf_feature_matrix(
    df: pd.DataFrame,
    solute_cache: dict[str, np.ndarray | None],
    solvent_cache: dict[str, np.ndarray | None],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows: list[np.ndarray] = []
    targets: list[float] = []
    row_indices: list[int] = []
    for row in df.itertuples(index=False):
        sol_fp = solute_cache.get(str(row.solute_smiles))
        slv_fp = solvent_cache.get(str(row.solvent_smiles))
        if sol_fp is None or slv_fp is None:
            continue
        temp = float(row.temperature)
        features = np.concatenate(
            [
                sol_fp.astype(np.float32, copy=False),
                slv_fp.astype(np.float32, copy=False),
                np.asarray([temp, 1.0 / temp, temp - 298.15], dtype=np.float32),
            ]
        )
        rows.append(features)
        targets.append(float(row.ln_x2))
        row_indices.append(int(row.combined_row_index))
    if not rows:
        return (
            np.empty((0, 0), dtype=np.float32),
            np.empty((0,), dtype=np.float32),
            np.empty((0,), dtype=int),
        )
    return (
        np.asarray(rows, dtype=np.float32),
        np.asarray(targets, dtype=np.float32),
        np.asarray(row_indices, dtype=int),
    )


def rf_predictions(
    train_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    *,
    radius: int,
    n_bits: int,
    n_estimators: int,
    max_depth: int,
    n_jobs: int,
    seed: int,
) -> pd.DataFrame:
    all_df = pd.concat([train_df, eval_df], ignore_index=True)
    solute_cache = _morgan_cache(all_df["solute_smiles"], radius=radius, n_bits=n_bits)
    solvent_cache = _morgan_cache(all_df["solvent_smiles"], radius=radius, n_bits=n_bits)
    X_train, y_train, _ = _rf_feature_matrix(train_df, solute_cache, solvent_cache)
    X_eval, _, eval_row_indices = _rf_feature_matrix(eval_df, solute_cache, solvent_cache)
    if X_train.size == 0 or X_eval.size == 0:
        return pd.DataFrame()

    model = RandomForestRegressor(
        n_estimators=int(n_estimators),
        max_depth=int(max_depth),
        n_jobs=int(n_jobs),
        random_state=int(seed),
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_eval)

    payload = eval_df.set_index("combined_row_index").loc[eval_row_indices].reset_index()
    out = payload[
        [
            "combined_row_index",
            "pair_key",
            "solute_smiles",
            "solvent_smiles",
            "temperature",
            "ln_x2",
        ]
    ].rename(columns={"combined_row_index": "row_index", "ln_x2": "ln_x2_true"})
    out["model"] = "rf_morgan_T"
    out["ln_x2_pred"] = preds.astype(float)
    return out


def add_error_columns(pred_df: pd.DataFrame, eval_split: str) -> pd.DataFrame:
    out = pred_df.copy()
    out["eval_split"] = eval_split
    out["signed_error"] = out["ln_x2_pred"].astype(float) - out["ln_x2_true"].astype(float)
    out["abs_error"] = out["signed_error"].abs()
    return out


def summarize_predictions(predictions: pd.DataFrame, train_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (eval_split, model), group in predictions.groupby(["eval_split", "model"], sort=False):
        row = {"eval_split": eval_split, "model": model}
        row.update(
            regression_metrics(
                group["ln_x2_true"].to_numpy(dtype=float),
                group["ln_x2_pred"].to_numpy(dtype=float),
            )
        )
        rows.append(row)
    metrics_df = pd.DataFrame(rows).sort_values(["eval_split", "mae"], kind="stable")

    anchor = (
        train_df.sort_values("temperature", kind="stable")
        .groupby("pair_key", sort=False)
        .tail(1)[["pair_key", "ln_x2"]]
        .rename(columns={"ln_x2": "anchor_ln_x2"})
    )
    trend_rows: list[dict[str, Any]] = []
    test_preds = predictions.loc[predictions["eval_split"] == "test"].copy()
    for model, model_group in test_preds.groupby("model", sort=False):
        pair_mean = (
            model_group.groupby("pair_key", sort=False)
            .agg(
                true_high_mean=("ln_x2_true", "mean"),
                pred_high_mean=("ln_x2_pred", "mean"),
                n_test=("ln_x2_true", "size"),
            )
            .reset_index()
            .merge(anchor, on="pair_key", how="inner")
        )
        if pair_mean.empty:
            continue
        true_delta = pair_mean["true_high_mean"] - pair_mean["anchor_ln_x2"]
        pred_delta = pair_mean["pred_high_mean"] - pair_mean["anchor_ln_x2"]
        nonzero = true_delta.abs() > 1.0e-8
        direction_accuracy = (
            float((np.sign(true_delta[nonzero]) == np.sign(pred_delta[nonzero])).mean())
            if nonzero.any()
            else None
        )
        trend_rows.append(
            {
                "model": model,
                "n_pairs": int(len(pair_mean)),
                "direction_accuracy": direction_accuracy,
                "mean_true_high_shift": float(true_delta.mean()),
                "mean_pred_high_shift": float(pred_delta.mean()),
                "pair_high_mean_mae": float(
                    np.mean(np.abs(pair_mean["pred_high_mean"] - pair_mean["true_high_mean"]))
                ),
                "fraction_predicted_increase": float((pred_delta > 0).mean()),
                "fraction_true_increase": float((true_delta > 0).mean()),
            }
        )
    trend_df = pd.DataFrame(trend_rows).sort_values("pair_high_mean_mae", kind="stable")

    summary = {
        "metrics": metrics_df.to_dict(orient="records"),
        "trend": trend_df.to_dict(orient="records"),
    }
    return metrics_df, trend_df, summary


def temperature_bin_metrics(predictions: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    test_df = predictions.loc[predictions["eval_split"] == "test"].copy()
    if test_df.empty:
        return pd.DataFrame()
    bins = [330.0, 340.0, 350.0, 365.0, 390.0, 500.0]
    labels = ["330-340", "340-350", "350-365", "365-390", "390+"]
    test_df["temperature_bin"] = pd.cut(
        test_df["temperature"],
        bins=bins,
        labels=labels,
        right=False,
        include_lowest=True,
    )
    rows: list[dict[str, Any]] = []
    for (model, temp_bin), group in test_df.groupby(["model", "temperature_bin"], observed=False):
        if group.empty:
            continue
        row = {"model": model, "temperature_bin": str(temp_bin)}
        row.update(
            regression_metrics(
                group["ln_x2_true"].to_numpy(dtype=float),
                group["ln_x2_pred"].to_numpy(dtype=float),
            )
        )
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(out_dir / "test_temperature_bin_metrics.csv", index=False)
    return out


def pair_error_table(predictions: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    test_df = predictions.loc[predictions["eval_split"] == "test"].copy()
    rows: list[dict[str, Any]] = []
    for (model, pair_key), group in test_df.groupby(["model", "pair_key"], sort=False):
        rows.append(
            {
                "model": model,
                "pair_key": pair_key,
                "solute_smiles": group["solute_smiles"].iloc[0],
                "solvent_smiles": group["solvent_smiles"].iloc[0],
                "n_test": int(len(group)),
                "temperature_min": float(group["temperature"].min()),
                "temperature_max": float(group["temperature"].max()),
                "mean_abs_error": float(group["abs_error"].mean()),
                "median_abs_error": float(group["abs_error"].median()),
                "mean_signed_error": float(group["signed_error"].mean()),
            }
        )
    out = pd.DataFrame(rows).sort_values(["model", "mean_abs_error"], ascending=[True, False], kind="stable")
    out.to_csv(out_dir / "test_pair_errors.csv", index=False)
    return out


def _style_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#d4d4d4", linewidth=0.8, alpha=0.65)
    ax.set_axisbelow(True)


def _save(fig: plt.Figure, out_dir: Path, stem: str, presentation_dir: Path | None, manifest: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        path = out_dir / f"{stem}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        manifest.append(str(path))
        if presentation_dir is not None:
            presentation_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, presentation_dir / path.name)
    plt.close(fig)


def plot_outputs(
    out_dir: Path,
    metrics_df: pd.DataFrame,
    trend_df: pd.DataFrame,
    bin_df: pd.DataFrame,
    predictions: pd.DataFrame,
    pair_stats: pd.DataFrame,
    presentation_dir: Path | None,
) -> dict[str, Any]:
    fig_dir = out_dir / "figures"
    manifest: list[str] = []
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
        }
    )

    test_metrics = metrics_df.loc[metrics_df["eval_split"] == "test"].copy()
    test_metrics = test_metrics.sort_values("mae", kind="stable")
    x = np.arange(len(test_metrics))
    colors = [MODEL_COLORS.get(model, "#525252") for model in test_metrics["model"]]
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2))
    axes[0].bar(x, test_metrics["mae"], color=colors, width=0.64)
    axes[0].set_xticks(x, test_metrics["model"], rotation=25, ha="right")
    axes[0].set_ylabel("High-T test MAE, ln x2")
    axes[0].set_title("Temperature extrapolation error")
    for idx, value in enumerate(test_metrics["mae"]):
        axes[0].text(idx, value + 0.025, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    _style_axes(axes[0])

    trend_plot = trend_df.set_index("model").reindex(test_metrics["model"])
    axes[1].bar(x, trend_plot["direction_accuracy"] * 100.0, color=colors, width=0.64)
    axes[1].set_xticks(x, test_metrics["model"], rotation=25, ha="right")
    axes[1].set_ylabel("High-T direction accuracy, %")
    axes[1].set_ylim(0, 100)
    axes[1].set_title("Correct sign of high-T shift")
    _style_axes(axes[1])
    fig.suptitle("Same-pair low-T to high-T extrapolation", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, fig_dir, "temperature_extrapolation_baseline_comparison", presentation_dir, manifest)

    if not bin_df.empty:
        fig, ax = plt.subplots(figsize=(7.2, 4.4))
        for model, group in bin_df.groupby("model", sort=False):
            ax.plot(
                group["temperature_bin"].astype(str),
                group["mae"],
                marker="o",
                linewidth=2.2,
                color=MODEL_COLORS.get(model, "#525252"),
                label=model,
            )
        ax.set_xlabel("High-T test bin, K")
        ax.set_ylabel("MAE, ln x2")
        ax.set_title("Error by extrapolation temperature")
        ax.tick_params(axis="x", rotation=20)
        ax.legend(frameon=False)
        _style_axes(ax)
        fig.tight_layout()
        _save(fig, fig_dir, "temperature_extrapolation_error_by_temperature", presentation_dir, manifest)

    # Example curves: choose pairs with many high-T observations and large span.
    example_pairs = (
        pair_stats.sort_values(["high_count", "temperature_gap_K"], ascending=[False, False], kind="stable")
        .head(4)["pair_key"]
        .tolist()
    )
    if example_pairs:
        pair_stats.loc[pair_stats["pair_key"].isin(example_pairs)].to_csv(
            out_dir / "example_pairs.csv",
            index=False,
        )
        fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.4), sharex=False, sharey=False)
        axes_flat = axes.ravel()
        for ax, pair_key in zip(axes_flat, example_pairs):
            pair_pred = predictions.loc[
                (predictions["eval_split"] == "test") & (predictions["pair_key"] == pair_key)
            ].copy()
            if pair_pred.empty:
                ax.axis("off")
                continue
            train_like = predictions.loc[
                (predictions["eval_split"] == "val") & (predictions["pair_key"] == pair_key)
            ].copy()
            true_points = pair_pred[["temperature", "ln_x2_true"]].drop_duplicates()
            ax.scatter(
                true_points["temperature"],
                true_points["ln_x2_true"],
                color="#111827",
                s=28,
                label="true high-T",
                zorder=4,
            )
            if not train_like.empty:
                val_true = train_like[["temperature", "ln_x2_true"]].drop_duplicates()
                ax.scatter(
                    val_true["temperature"],
                    val_true["ln_x2_true"],
                    color="#a3a3a3",
                    s=24,
                    label="held low-T",
                    zorder=3,
                )
            for model in ("pair_last_low_T", "pair_vant_hoff", "rf_morgan_T"):
                model_rows = pair_pred.loc[pair_pred["model"] == model].sort_values("temperature")
                if model_rows.empty:
                    continue
                ax.plot(
                    model_rows["temperature"],
                    model_rows["ln_x2_pred"],
                    linewidth=1.9,
                    marker="o",
                    markersize=3,
                    color=MODEL_COLORS.get(model, "#525252"),
                    label=model,
                )
            solute = str(pair_pred["solute_smiles"].iloc[0])
            solvent = str(pair_pred["solvent_smiles"].iloc[0])
            ax.set_title(f"{solute[:18]}... / {solvent[:12]}", fontsize=9)
            ax.set_xlabel("T, K")
            ax.set_ylabel("ln x2")
            _style_axes(ax)
        handles, labels = axes_flat[0].get_legend_handles_labels()
        if handles:
            fig.legend(handles, labels, loc="upper center", ncols=4, frameon=False)
        fig.suptitle("Representative high-temperature extrapolation curves", fontsize=13, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        _save(fig, fig_dir, "temperature_extrapolation_example_curves", presentation_dir, manifest)

    figure_manifest = {
        "figure_dir": str(fig_dir),
        "presentation_dir": None if presentation_dir is None else str(presentation_dir),
        "files": manifest,
    }
    (fig_dir / "figure_manifest.json").write_text(
        json.dumps(_json_safe(figure_manifest), indent=2),
        encoding="utf-8",
    )
    return figure_manifest


def build_markdown(
    *,
    args: argparse.Namespace,
    split_summary: dict[str, Any],
    metrics_df: pd.DataFrame,
    trend_df: pd.DataFrame,
    figure_manifest: dict[str, Any],
) -> str:
    test_metrics = metrics_df.loc[metrics_df["eval_split"] == "test"].sort_values("mae", kind="stable")
    trend_by_model = trend_df.set_index("model") if not trend_df.empty else pd.DataFrame()
    lines = [
        "# Temperature Extrapolation Baselines",
        "",
        "## Protocol",
        "",
        f"- Low-temperature train rows: `T <= {args.train_max_k:.2f} K`",
        f"- High-temperature test rows: `T >= {args.test_min_k:.2f} K`",
        "- Same `(solute, solvent)` pairs appear in low-T train and high-T test.",
        "- The highest low-T row per pair is held out as validation; lower low-T rows are used for fitting.",
        f"- Eligible pairs: `{split_summary['n_pairs']}`",
        f"- Train / val / test rows: `{split_summary['n_train']}` / `{split_summary['n_val']}` / `{split_summary['n_test']}`",
        "",
        "## High-T Test Metrics",
        "",
        "| Model | MAE | RMSE | R^2 | Bias | Direction accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in test_metrics.iterrows():
        trend = trend_by_model.loc[row["model"]] if row["model"] in trend_by_model.index else None
        direction = None if trend is None else trend.get("direction_accuracy")
        direction_text = "NA" if direction is None or pd.isna(direction) else f"{float(direction):.1%}"
        r2_text = "NA" if pd.isna(row["r2"]) else f"{float(row['r2']):.3f}"
        lines.append(
            f"| {row['model']} | {float(row['mae']):.3f} | "
            f"{float(row['rmse']):.3f} | {r2_text} | "
            f"{float(row['bias']):+.3f} | {direction_text} |"
        )
    lines += [
        "",
        "## Artifacts",
        "",
        "- `splits/train_low.csv`",
        "- `splits/val_low.csv`",
        "- `splits/test_high.csv`",
        "- `predictions.csv`",
        "- `metrics_by_model.csv`",
        "- `trend_summary.csv`",
        "- `test_temperature_bin_metrics.csv`",
        "- `test_pair_errors.csv`",
    ]
    if figure_manifest.get("files"):
        lines += [
            "",
            "## Figures",
            "",
        ]
        for path in figure_manifest["files"]:
            if str(path).endswith(".png"):
                lines.append(f"- `{Path(path).name}`")
    lines += [
        "",
        "## Neural Follow-Up",
        "",
        "Use the exported split CSVs for the actual TGNN-Solv vs DirectGNN test:",
        "",
        "```bash",
        "python scripts/training/train.py \\",
        "  --config configs/paper_config_tuned.yaml \\",
        "  --train-data results/temperature_extrapolation_baselines/splits/train_low.csv \\",
        "  --val-data results/temperature_extrapolation_baselines/splits/val_low.csv \\",
        "  --test-data results/temperature_extrapolation_baselines/splits/test_high.csv \\",
        "  --checkpoint checkpoints/temperature_extrapolation/tgnn_solv_lowT_highT.pt \\",
        "  --device cuda",
        "",
        "python scripts/training/train_directgnn.py \\",
        "  --config configs/paper_config_directgnn_tuned.yaml \\",
        "  --train-data results/temperature_extrapolation_baselines/splits/train_low.csv \\",
        "  --val-data results/temperature_extrapolation_baselines/splits/val_low.csv \\",
        "  --test-data results/temperature_extrapolation_baselines/splits/test_high.csv \\",
        "  --checkpoint checkpoints/temperature_extrapolation/directgnn_lowT_highT.pt \\",
        "  --device cuda",
        "```",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    processed_dir = Path(args.processed_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    split_dir = out_dir / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    presentation_dir = None if args.no_presentation_copy else Path(args.presentation_dir).expanduser().resolve()

    combined = load_combined_processed(processed_dir)
    train_df, val_df, test_df, pair_stats = build_temperature_split(
        combined,
        train_max_k=float(args.train_max_k),
        test_min_k=float(args.test_min_k),
        min_low_points=int(args.min_low_points),
        min_high_points=int(args.min_high_points),
        max_pairs=int(args.max_pairs),
        seed=int(args.seed),
    )
    train_df.to_csv(split_dir / "train_low.csv", index=False)
    val_df.to_csv(split_dir / "val_low.csv", index=False)
    test_df.to_csv(split_dir / "test_high.csv", index=False)
    pair_stats.to_csv(out_dir / "eligible_pair_stats.csv", index=False)

    predictions: list[pd.DataFrame] = []
    predictions.append(add_error_columns(pair_baseline_predictions(train_df, val_df), "val"))
    predictions.append(add_error_columns(pair_baseline_predictions(train_df, test_df), "test"))

    if not args.skip_rf:
        predictions.append(
            add_error_columns(
                rf_predictions(
                    train_df,
                    val_df,
                    radius=int(args.morgan_radius),
                    n_bits=int(args.morgan_n_bits),
                    n_estimators=int(args.rf_n_estimators),
                    max_depth=int(args.rf_max_depth),
                    n_jobs=int(args.rf_n_jobs),
                    seed=int(args.seed),
                ),
                "val",
            )
        )
        predictions.append(
            add_error_columns(
                rf_predictions(
                    train_df,
                    test_df,
                    radius=int(args.morgan_radius),
                    n_bits=int(args.morgan_n_bits),
                    n_estimators=int(args.rf_n_estimators),
                    max_depth=int(args.rf_max_depth),
                    n_jobs=int(args.rf_n_jobs),
                    seed=int(args.seed),
                ),
                "test",
            )
        )

    pred_df = pd.concat([frame for frame in predictions if not frame.empty], ignore_index=True)
    pred_df.to_csv(out_dir / "predictions.csv", index=False)

    metrics_df, trend_df, summary_payload = summarize_predictions(pred_df, train_df)
    metrics_df.to_csv(out_dir / "metrics_by_model.csv", index=False)
    trend_df.to_csv(out_dir / "trend_summary.csv", index=False)
    bin_df = temperature_bin_metrics(pred_df, out_dir)
    pair_error_table(pred_df, out_dir)

    split_summary = {
        "n_combined_supervised_rows": int(len(combined)),
        "n_pairs": int(pair_stats["pair_key"].nunique()),
        "n_train": int(len(train_df)),
        "n_val": int(len(val_df)),
        "n_test": int(len(test_df)),
        "train_temperature_range": [
            float(train_df["temperature"].min()),
            float(train_df["temperature"].max()),
        ],
        "val_temperature_range": [
            float(val_df["temperature"].min()),
            float(val_df["temperature"].max()),
        ],
        "test_temperature_range": [
            float(test_df["temperature"].min()),
            float(test_df["temperature"].max()),
        ],
        "mean_temperature_gap_K": float(pair_stats["temperature_gap_K"].mean()),
        "median_temperature_gap_K": float(pair_stats["temperature_gap_K"].median()),
    }

    figure_manifest = plot_outputs(
        out_dir,
        metrics_df,
        trend_df,
        bin_df,
        pred_df,
        pair_stats,
        presentation_dir,
    )

    payload = {
        "protocol": {
            "processed_dir": str(processed_dir),
            "train_max_k": float(args.train_max_k),
            "test_min_k": float(args.test_min_k),
            "min_low_points": int(args.min_low_points),
            "min_high_points": int(args.min_high_points),
            "max_pairs": int(args.max_pairs),
            "seed": int(args.seed),
            "rf_enabled": not bool(args.skip_rf),
            "rf_n_estimators": int(args.rf_n_estimators),
            "rf_max_depth": int(args.rf_max_depth),
            "morgan_n_bits": int(args.morgan_n_bits),
        },
        "split_summary": split_summary,
        "results": summary_payload,
        "figure_manifest": figure_manifest,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_safe(payload), indent=2),
        encoding="utf-8",
    )
    (out_dir / "SUMMARY.md").write_text(
        build_markdown(
            args=args,
            split_summary=split_summary,
            metrics_df=metrics_df,
            trend_df=trend_df,
            figure_manifest=figure_manifest,
        ),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(payload), indent=2))


if __name__ == "__main__":
    main()
