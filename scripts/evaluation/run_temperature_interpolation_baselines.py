#!/usr/bin/env python3
"""CPU-first in-pair temperature interpolation diagnostics.

The protocol keeps each selected `(solute, solvent)` pair in train/val/test,
holds out only interior temperature points, and always leaves the pair's low
and high temperature endpoints in train. This is the cleanest cheap benchmark
for whether a model captures within-pair temperature curve shape.
"""

from __future__ import annotations

import argparse
import hashlib
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
    "pair_nearest_T": "#525252",
    "pair_linear_T": "#d97706",
    "pair_vant_hoff": "#2563eb",
    "pair_piecewise_linear_T": "#0f766e",
    "rf_morgan_T": "#4d7c0f",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build an in-pair temperature interpolation split and evaluate "
            "cheap CPU baselines."
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
        default="results/temperature_interpolation_baselines",
        help="Output bundle directory.",
    )
    parser.add_argument(
        "--min-unique-temps",
        type=int,
        default=6,
        help="Minimum number of unique temperatures required per pair.",
    )
    parser.add_argument(
        "--min-temperature-span-k",
        type=float,
        default=20.0,
        help="Minimum within-pair temperature span.",
    )
    parser.add_argument(
        "--test-frac-interior",
        type=float,
        default=0.25,
        help="Fraction of interior temperatures assigned to test.",
    )
    parser.add_argument(
        "--val-frac-interior",
        type=float,
        default=0.15,
        help="Fraction of interior temperatures assigned to validation.",
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=1000,
        help="Cap selected pairs for a local tiny benchmark; 0 means use all.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--morgan-radius", type=int, default=2)
    parser.add_argument("--morgan-n-bits", type=int, default=1024)
    parser.add_argument("--rf-n-estimators", type=int, default=80)
    parser.add_argument("--rf-max-depth", type=int, default=24)
    parser.add_argument("--rf-n-jobs", type=int, default=-1)
    parser.add_argument("--skip-rf", action="store_true")
    parser.add_argument(
        "--presentation-dir",
        default="figures",
        help="Directory that receives copies of generated PNG/PDF figures.",
    )
    parser.add_argument(
        "--no-presentation-copy",
        action="store_true",
        help="Do not copy figures into figures/.",
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


def _stable_pair_seed(pair_key: str, seed: int) -> int:
    payload = f"{seed}|{pair_key}".encode("utf-8", errors="replace")
    digest = hashlib.sha256(payload).hexdigest()[:8]
    return int(digest, 16)


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


def eligible_pair_stats(
    df: pd.DataFrame,
    *,
    min_unique_temps: int,
    min_temperature_span_k: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for pair_key, group in df.groupby("pair_key", sort=False):
        temps = np.sort(group["temperature"].dropna().unique().astype(float))
        if temps.size < int(min_unique_temps):
            continue
        span = float(temps[-1] - temps[0])
        if span < float(min_temperature_span_k):
            continue
        rows.append(
            {
                "pair_key": pair_key,
                "solute_smiles": str(group["solute_smiles"].iloc[0]),
                "solvent_smiles": str(group["solvent_smiles"].iloc[0]),
                "n_rows": int(len(group)),
                "n_unique_temps": int(temps.size),
                "temperature_min": float(temps[0]),
                "temperature_max": float(temps[-1]),
                "temperature_span_K": span,
                "ln_x2_mean": float(group["ln_x2"].mean()),
                "ln_x2_std": float(group["ln_x2"].std(ddof=0)),
            }
        )
    stats = pd.DataFrame(rows)
    if stats.empty:
        return stats
    return stats.sort_values(
        ["n_unique_temps", "temperature_span_K", "n_rows"],
        ascending=[False, False, False],
        kind="stable",
    ).reset_index(drop=True)


def select_pairs(stats: pd.DataFrame, *, max_pairs: int, seed: int) -> pd.DataFrame:
    if not max_pairs or len(stats) <= int(max_pairs):
        return stats.copy()
    # Sample rather than taking only the densest sources, but keep output sorted
    # after sampling to make review deterministic and biased toward readable curves.
    sampled = stats.sample(n=int(max_pairs), random_state=int(seed))
    return sampled.sort_values(
        ["n_unique_temps", "temperature_span_K", "n_rows"],
        ascending=[False, False, False],
        kind="stable",
    ).reset_index(drop=True)


def _assign_temperature_ranks(
    temps: np.ndarray,
    *,
    pair_key: str,
    seed: int,
    test_frac_interior: float,
    val_frac_interior: float,
) -> dict[float, str]:
    temps = np.sort(np.asarray(temps, dtype=float))
    if temps.size < 4:
        raise ValueError("At least four temperatures are required for interpolation splitting.")
    assignment: dict[float, str] = {float(temps[0]): "train", float(temps[-1]): "train"}
    interior = temps[1:-1].copy()
    rng = np.random.RandomState(_stable_pair_seed(pair_key, seed))
    shuffled = interior.copy()
    rng.shuffle(shuffled)

    n_interior = len(interior)
    n_test = max(1, int(round(n_interior * float(test_frac_interior))))
    n_val = max(1, int(round(n_interior * float(val_frac_interior))))
    if n_test + n_val >= n_interior:
        # Preserve at least one interior temperature in train.
        overflow = n_test + n_val - (n_interior - 1)
        n_val = max(1, n_val - overflow)
        if n_test + n_val >= n_interior:
            n_test = max(1, n_interior - n_val - 1)

    test_temps = {float(t) for t in shuffled[:n_test]}
    val_temps = {float(t) for t in shuffled[n_test:n_test + n_val]}
    for temp in interior:
        key = float(temp)
        if key in test_temps:
            assignment[key] = "test"
        elif key in val_temps:
            assignment[key] = "val"
        else:
            assignment[key] = "train"
    return assignment


def build_interpolation_split(
    df: pd.DataFrame,
    pair_stats: pd.DataFrame,
    *,
    seed: int,
    test_frac_interior: float,
    val_frac_interior: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    selected_pairs = set(pair_stats["pair_key"].astype(str))
    selected = df.loc[df["pair_key"].isin(selected_pairs)].copy()
    split_frames: list[pd.DataFrame] = []
    assignment_rows: list[dict[str, Any]] = []

    for pair_key, group in selected.groupby("pair_key", sort=False):
        temps = np.sort(group["temperature"].dropna().unique().astype(float))
        assignment = _assign_temperature_ranks(
            temps,
            pair_key=str(pair_key),
            seed=int(seed),
            test_frac_interior=float(test_frac_interior),
            val_frac_interior=float(val_frac_interior),
        )
        tagged = group.copy()
        tagged["interpolation_split"] = tagged["temperature"].astype(float).map(assignment)
        split_frames.append(tagged)
        for temp, split in assignment.items():
            assignment_rows.append(
                {
                    "pair_key": pair_key,
                    "temperature": float(temp),
                    "interpolation_split": split,
                }
            )

    work = pd.concat(split_frames, ignore_index=True)
    assignments = pd.DataFrame(assignment_rows)
    train_df = work.loc[work["interpolation_split"] == "train"].copy()
    val_df = work.loc[work["interpolation_split"] == "val"].copy()
    test_df = work.loc[work["interpolation_split"] == "test"].copy()
    sort_cols = ["pair_key", "temperature", "ln_x2"]
    return (
        train_df.sort_values(sort_cols, kind="stable").reset_index(drop=True),
        val_df.sort_values(sort_cols, kind="stable").reset_index(drop=True),
        test_df.sort_values(sort_cols, kind="stable").reset_index(drop=True),
        assignments.sort_values(["pair_key", "temperature"], kind="stable").reset_index(drop=True),
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


def _nearest_prediction(train_t: np.ndarray, train_y: np.ndarray, temp: float) -> float:
    idx = int(np.argmin(np.abs(train_t - float(temp))))
    return float(train_y[idx])


def _piecewise_linear_prediction(train_t: np.ndarray, train_y: np.ndarray, temp: float) -> float:
    order = np.argsort(train_t)
    train_t = train_t[order]
    train_y = train_y[order]
    # np.interp gives linear interpolation inside endpoints and linear clipping
    # at endpoints; endpoints are always in train by construction.
    return float(np.interp(float(temp), train_t, train_y))


def pair_baseline_predictions(train_df: pd.DataFrame, eval_df: pd.DataFrame) -> pd.DataFrame:
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
                "pair_nearest_T": _nearest_prediction(t_train, y_train, temp),
                "pair_linear_T": slope_t * temp + intercept_t,
                "pair_vant_hoff": slope_inv_t * (1.0 / temp) + intercept_inv_t,
                "pair_piecewise_linear_T": _piecewise_linear_prediction(t_train, y_train, temp),
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
        rows.append(
            np.concatenate(
                [
                    sol_fp.astype(np.float32, copy=False),
                    slv_fp.astype(np.float32, copy=False),
                    np.asarray([temp, 1.0 / temp, temp - 298.15], dtype=np.float32),
                ]
            )
        )
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


def summarize_predictions(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    metric_rows: list[dict[str, Any]] = []
    for (eval_split, model), group in predictions.groupby(["eval_split", "model"], sort=False):
        row = {"eval_split": eval_split, "model": model}
        row.update(
            regression_metrics(
                group["ln_x2_true"].to_numpy(dtype=float),
                group["ln_x2_pred"].to_numpy(dtype=float),
            )
        )
        metric_rows.append(row)
    metrics_df = pd.DataFrame(metric_rows).sort_values(["eval_split", "mae"], kind="stable")

    shape_rows: list[dict[str, Any]] = []
    test_df = predictions.loc[predictions["eval_split"] == "test"].copy()
    for model, model_group in test_df.groupby("model", sort=False):
        pair_rows: list[dict[str, Any]] = []
        for pair_key, pair_group in model_group.groupby("pair_key", sort=False):
            pair_group = pair_group.sort_values("temperature", kind="stable")
            if len(pair_group) < 2:
                continue
            true = pair_group["ln_x2_true"].to_numpy(dtype=float)
            pred = pair_group["ln_x2_pred"].to_numpy(dtype=float)
            true_diff = np.diff(true)
            pred_diff = np.diff(pred)
            nonzero = np.abs(true_diff) > 1.0e-8
            if not nonzero.any():
                continue
            pair_rows.append(
                {
                    "pair_key": pair_key,
                    "n_test": int(len(pair_group)),
                    "slope_sign_accuracy": float(
                        (np.sign(true_diff[nonzero]) == np.sign(pred_diff[nonzero])).mean()
                    ),
                    "mean_slope_abs_error": float(np.mean(np.abs(pred_diff - true_diff))),
                }
            )
        if not pair_rows:
            continue
        pair_df = pd.DataFrame(pair_rows)
        shape_rows.append(
            {
                "model": model,
                "n_pairs_with_multiple_test_temps": int(len(pair_df)),
                "slope_sign_accuracy": float(pair_df["slope_sign_accuracy"].mean()),
                "mean_slope_abs_error": float(pair_df["mean_slope_abs_error"].mean()),
            }
        )
    shape_df = pd.DataFrame(shape_rows).sort_values("mean_slope_abs_error", kind="stable")
    summary = {
        "metrics": metrics_df.to_dict(orient="records"),
        "shape": shape_df.to_dict(orient="records"),
    }
    return metrics_df, shape_df, summary


def temperature_bin_metrics(predictions: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    test_df = predictions.loc[predictions["eval_split"] == "test"].copy()
    if test_df.empty:
        return pd.DataFrame()
    quantiles = np.unique(np.quantile(test_df["temperature"].to_numpy(dtype=float), [0, 0.2, 0.4, 0.6, 0.8, 1.0]))
    if len(quantiles) < 3:
        return pd.DataFrame()
    test_df["temperature_bin"] = pd.cut(
        test_df["temperature"],
        bins=quantiles,
        include_lowest=True,
        duplicates="drop",
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
    shape_df: pd.DataFrame,
    bin_df: pd.DataFrame,
    predictions: pd.DataFrame,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
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

    test_metrics = metrics_df.loc[metrics_df["eval_split"] == "test"].copy().sort_values("mae", kind="stable")
    x = np.arange(len(test_metrics))
    colors = [MODEL_COLORS.get(model, "#525252") for model in test_metrics["model"]]
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.2))
    axes[0].bar(x, test_metrics["mae"], color=colors, width=0.64)
    axes[0].set_xticks(x, test_metrics["model"], rotation=25, ha="right")
    axes[0].set_ylabel("Interior-T test MAE, ln x2")
    axes[0].set_title("In-pair temperature interpolation")
    for idx, value in enumerate(test_metrics["mae"]):
        axes[0].text(idx, value + 0.01, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    _style_axes(axes[0])

    shape_plot = shape_df.set_index("model").reindex(test_metrics["model"]) if not shape_df.empty else pd.DataFrame()
    if not shape_plot.empty and "slope_sign_accuracy" in shape_plot:
        axes[1].bar(x, shape_plot["slope_sign_accuracy"] * 100.0, color=colors, width=0.64)
        axes[1].set_ylabel("Slope sign accuracy, %")
        axes[1].set_ylim(0, 100)
    else:
        axes[1].bar(x, test_metrics["r2"], color=colors, width=0.64)
        axes[1].set_ylabel("R^2")
    axes[1].set_xticks(x, test_metrics["model"], rotation=25, ha="right")
    axes[1].set_title("Curve-shape fidelity")
    _style_axes(axes[1])
    fig.suptitle("Same-pair interior-temperature interpolation", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, fig_dir, "temperature_interpolation_baseline_comparison", presentation_dir, manifest)

    if not bin_df.empty:
        fig, ax = plt.subplots(figsize=(7.4, 4.4))
        for model, group in bin_df.groupby("model", sort=False):
            ax.plot(
                group["temperature_bin"].astype(str),
                group["mae"],
                marker="o",
                linewidth=2.0,
                color=MODEL_COLORS.get(model, "#525252"),
                label=model,
            )
        ax.set_xlabel("Held-out interior-T bin")
        ax.set_ylabel("MAE, ln x2")
        ax.set_title("Interpolation error by temperature bin")
        ax.tick_params(axis="x", rotation=20)
        ax.legend(frameon=False)
        _style_axes(ax)
        fig.tight_layout()
        _save(fig, fig_dir, "temperature_interpolation_error_by_temperature", presentation_dir, manifest)

    example_pairs = (
        pair_stats.sort_values(["n_unique_temps", "temperature_span_K"], ascending=[False, False], kind="stable")
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
            train_pair = train_df.loc[train_df["pair_key"] == pair_key].copy()
            test_pair = test_df.loc[test_df["pair_key"] == pair_key].copy()
            pair_pred = predictions.loc[
                (predictions["eval_split"] == "test") & (predictions["pair_key"] == pair_key)
            ].copy()
            if train_pair.empty or test_pair.empty or pair_pred.empty:
                ax.axis("off")
                continue
            ax.scatter(
                train_pair["temperature"],
                train_pair["ln_x2"],
                color="#a3a3a3",
                s=24,
                label="train true",
                zorder=3,
            )
            ax.scatter(
                test_pair["temperature"],
                test_pair["ln_x2"],
                color="#111827",
                s=30,
                label="held-out true",
                zorder=4,
            )
            for model in ("pair_piecewise_linear_T", "pair_vant_hoff", "rf_morgan_T"):
                rows = pair_pred.loc[pair_pred["model"] == model].sort_values("temperature")
                if rows.empty:
                    continue
                ax.plot(
                    rows["temperature"],
                    rows["ln_x2_pred"],
                    linewidth=1.9,
                    marker="o",
                    markersize=3,
                    color=MODEL_COLORS.get(model, "#525252"),
                    label=model,
                )
            solute = str(test_pair["solute_smiles"].iloc[0])
            solvent = str(test_pair["solvent_smiles"].iloc[0])
            ax.set_title(f"{solute[:18]}... / {solvent[:12]}", fontsize=9)
            ax.set_xlabel("T, K")
            ax.set_ylabel("ln x2")
            _style_axes(ax)
        handles, labels = axes_flat[0].get_legend_handles_labels()
        if handles:
            fig.legend(handles, labels, loc="upper center", ncols=5, frameon=False)
        fig.suptitle("Representative in-pair interpolation curves", fontsize=13, fontweight="bold")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        _save(fig, fig_dir, "temperature_interpolation_example_curves", presentation_dir, manifest)

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
    shape_df: pd.DataFrame,
    figure_manifest: dict[str, Any],
) -> str:
    test_metrics = metrics_df.loc[metrics_df["eval_split"] == "test"].sort_values("mae", kind="stable")
    shape_by_model = shape_df.set_index("model") if not shape_df.empty else pd.DataFrame()
    lines = [
        "# In-Pair Temperature Interpolation Baselines",
        "",
        "## Protocol",
        "",
        "- Same `(solute, solvent)` pairs appear in train, val, and test.",
        "- The lowest and highest temperatures of every pair are always kept in train.",
        "- Only interior temperature points are held out for val/test.",
        f"- Minimum unique temperatures per pair: `{args.min_unique_temps}`",
        f"- Minimum temperature span: `{args.min_temperature_span_k:.1f} K`",
        f"- Selected pairs: `{split_summary['n_pairs']}`",
        f"- Train / val / test rows: `{split_summary['n_train']}` / `{split_summary['n_val']}` / `{split_summary['n_test']}`",
        "",
        "## Interior-T Test Metrics",
        "",
        "| Model | MAE | RMSE | R^2 | Bias | Slope sign accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in test_metrics.iterrows():
        shape = shape_by_model.loc[row["model"]] if row["model"] in shape_by_model.index else None
        slope_acc = None if shape is None else shape.get("slope_sign_accuracy")
        slope_text = "NA" if slope_acc is None or pd.isna(slope_acc) else f"{float(slope_acc):.1%}"
        r2_text = "NA" if pd.isna(row["r2"]) else f"{float(row['r2']):.3f}"
        lines.append(
            f"| {row['model']} | {float(row['mae']):.3f} | "
            f"{float(row['rmse']):.3f} | {r2_text} | "
            f"{float(row['bias']):+.3f} | {slope_text} |"
        )
    lines += [
        "",
        "## Artifacts",
        "",
        "- `splits/train_inpair.csv`",
        "- `splits/val_inpair.csv`",
        "- `splits/test_inpair.csv`",
        "- `predictions.csv`",
        "- `metrics_by_model.csv`",
        "- `shape_summary.csv`",
        "- `test_temperature_bin_metrics.csv`",
        "- `test_pair_errors.csv`",
    ]
    if figure_manifest.get("files"):
        lines += ["", "## Figures", ""]
        for path in figure_manifest["files"]:
            if str(path).endswith(".png"):
                lines.append(f"- `{Path(path).name}`")
    lines += [
        "",
        "## Neural Follow-Up",
        "",
        "Use the exported split CSVs for a fair TGNN-Solv vs DirectGNN interpolation run:",
        "",
        "```bash",
        "python scripts/training/train.py \\",
        "  --config configs/paper_config_tuned.yaml \\",
        "  --train-data results/temperature_interpolation_baselines/splits/train_inpair.csv \\",
        "  --val-data results/temperature_interpolation_baselines/splits/val_inpair.csv \\",
        "  --test-data results/temperature_interpolation_baselines/splits/test_inpair.csv \\",
        "  --checkpoint checkpoints/temperature_interpolation/tgnn_solv_inpair.pt \\",
        "  --device cuda",
        "",
        "python scripts/training/train_directgnn.py \\",
        "  --config configs/paper_config_directgnn_tuned.yaml \\",
        "  --train-data results/temperature_interpolation_baselines/splits/train_inpair.csv \\",
        "  --val-data results/temperature_interpolation_baselines/splits/val_inpair.csv \\",
        "  --test-data results/temperature_interpolation_baselines/splits/test_inpair.csv \\",
        "  --checkpoint checkpoints/temperature_interpolation/directgnn_inpair.pt \\",
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
    all_pair_stats = eligible_pair_stats(
        combined,
        min_unique_temps=int(args.min_unique_temps),
        min_temperature_span_k=float(args.min_temperature_span_k),
    )
    selected_pair_stats = select_pairs(
        all_pair_stats,
        max_pairs=int(args.max_pairs),
        seed=int(args.seed),
    )
    if selected_pair_stats.empty:
        raise ValueError("No eligible pairs found for in-pair temperature interpolation.")

    train_df, val_df, test_df, assignments = build_interpolation_split(
        combined,
        selected_pair_stats,
        seed=int(args.seed),
        test_frac_interior=float(args.test_frac_interior),
        val_frac_interior=float(args.val_frac_interior),
    )
    train_df.to_csv(split_dir / "train_inpair.csv", index=False)
    val_df.to_csv(split_dir / "val_inpair.csv", index=False)
    test_df.to_csv(split_dir / "test_inpair.csv", index=False)
    assignments.to_csv(out_dir / "temperature_assignments.csv", index=False)
    all_pair_stats.to_csv(out_dir / "all_eligible_pair_stats.csv", index=False)
    selected_pair_stats.to_csv(out_dir / "selected_pair_stats.csv", index=False)

    predictions: list[pd.DataFrame] = [
        add_error_columns(pair_baseline_predictions(train_df, val_df), "val"),
        add_error_columns(pair_baseline_predictions(train_df, test_df), "test"),
    ]
    if not args.skip_rf:
        predictions += [
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
            ),
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
            ),
        ]

    pred_df = pd.concat([frame for frame in predictions if not frame.empty], ignore_index=True)
    pred_df.to_csv(out_dir / "predictions.csv", index=False)
    metrics_df, shape_df, summary_payload = summarize_predictions(pred_df)
    metrics_df.to_csv(out_dir / "metrics_by_model.csv", index=False)
    shape_df.to_csv(out_dir / "shape_summary.csv", index=False)
    bin_df = temperature_bin_metrics(pred_df, out_dir)
    pair_error_table(pred_df, out_dir)

    split_summary = {
        "n_combined_supervised_rows": int(len(combined)),
        "n_all_eligible_pairs": int(len(all_pair_stats)),
        "n_pairs": int(selected_pair_stats["pair_key"].nunique()),
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
        "mean_pair_temperature_span_K": float(selected_pair_stats["temperature_span_K"].mean()),
        "median_pair_temperature_span_K": float(selected_pair_stats["temperature_span_K"].median()),
        "mean_unique_temperatures_per_pair": float(selected_pair_stats["n_unique_temps"].mean()),
        "median_unique_temperatures_per_pair": float(selected_pair_stats["n_unique_temps"].median()),
    }

    figure_manifest = plot_outputs(
        out_dir,
        metrics_df,
        shape_df,
        bin_df,
        pred_df,
        train_df,
        test_df,
        selected_pair_stats,
        presentation_dir,
    )
    payload = {
        "protocol": {
            "processed_dir": str(processed_dir),
            "min_unique_temps": int(args.min_unique_temps),
            "min_temperature_span_k": float(args.min_temperature_span_k),
            "test_frac_interior": float(args.test_frac_interior),
            "val_frac_interior": float(args.val_frac_interior),
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
            shape_df=shape_df,
            figure_manifest=figure_manifest,
        ),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(payload), indent=2))


if __name__ == "__main__":
    main()
