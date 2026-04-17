#!/usr/bin/env python3
"""Run a Morgan KNN baseline and nearest-neighbor modelability diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: E402,F401

try:
    from sklearn.metrics import mean_absolute_error
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except Exception as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "scikit-learn is required for run_knn_modelability.py. "
        "Install it with `pip install scikit-learn`."
    ) from exc

from tgnn_solv.external_benchmarking import (  # noqa: E402
    build_benchmark_artifacts,
    prepare_pair_dataframe,
    write_benchmark_artifacts,
)
from tgnn_solv.features import (  # noqa: E402
    smiles_to_morgan_fp,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a KNN baseline on pair Morgan fingerprints and measure how "
            "nearest-neighbor ln(x2) gaps behave as a function of pair "
            "Tanimoto similarity."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--train-data", required=True)
    parser.add_argument("--test-data", required=True)
    parser.add_argument("--val-data", default=None)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--knn-mode",
        choices=["pair_tanimoto_1nn", "sklearn_euclidean"],
        default="pair_tanimoto_1nn",
        help=(
            "Prediction mode. `pair_tanimoto_1nn` is the fast chemistry-native "
            "baseline; `sklearn_euclidean` fits a scaled KNN on pair Morgan "
            "bits plus temperature."
        ),
    )
    parser.add_argument("--n-neighbors", type=int, default=5)
    parser.add_argument("--weights", choices=["uniform", "distance"], default="distance")
    parser.add_argument("--metric", default="euclidean")
    parser.add_argument("--morgan-radius", type=int, default=2)
    parser.add_argument("--morgan-n-bits", type=int, default=2048)
    parser.add_argument(
        "--cliff-threshold",
        type=float,
        default=2.0,
        help="Absolute ln(x2) gap used to flag a solubility cliff.",
    )
    parser.add_argument("--max-train-samples", type=int, default=0)
    parser.add_argument("--max-test-samples", type=int, default=0)
    return parser.parse_args()


def _supervised_view(df: pd.DataFrame) -> pd.DataFrame:
    out = prepare_pair_dataframe(df, require_targets=True).copy()
    out["ln_x2"] = pd.to_numeric(out["ln_x2"], errors="coerce")
    out["temperature"] = pd.to_numeric(out["temperature"], errors="coerce")
    out = out.loc[out["has_solubility"].fillna(False).astype(bool)].copy()
    out["pair_key"] = (
        out["solute_smiles"].astype(str) + "||" + out["solvent_smiles"].astype(str)
    )
    out = out.loc[np.isfinite(out["ln_x2"].to_numpy(dtype=float))].reset_index(drop=True)
    return out


def _maybe_subsample(
    df: pd.DataFrame,
    max_samples: int,
    *,
    seed: int = 42,
) -> pd.DataFrame:
    if max_samples <= 0 or len(df) <= max_samples:
        return df.reset_index(drop=True)
    return df.sample(n=max_samples, random_state=seed).reset_index(drop=True)


def _pair_feature_matrix(
    df: pd.DataFrame,
    *,
    radius: int,
    n_bits: int,
) -> tuple[np.ndarray, np.ndarray]:
    cache: dict[str, np.ndarray | None] = {}
    rows: list[np.ndarray] = []
    kept: list[int] = []
    for idx, row in enumerate(df.itertuples(index=False)):
        solute = str(row.solute_smiles)
        solvent = str(row.solvent_smiles)
        if solute not in cache:
            cache[solute] = smiles_to_morgan_fp(solute, radius=radius, n_bits=n_bits)
        if solvent not in cache:
            cache[solvent] = smiles_to_morgan_fp(solvent, radius=radius, n_bits=n_bits)
        sol_fp = cache[solute]
        slv_fp = cache[solvent]
        if sol_fp is None or slv_fp is None:
            continue
        temp = float(row.temperature)
        feats = np.concatenate(
            [
                sol_fp,
                slv_fp,
                np.asarray([temp, 1.0 / temp], dtype=np.float32),
            ]
        )
        rows.append(feats.astype(np.float32, copy=False))
        kept.append(idx)
    if not rows:
        return np.empty((0, 2 * n_bits + 2), dtype=np.float32), np.empty((0,), dtype=int)
    return np.stack(rows).astype(np.float32, copy=False), np.asarray(kept, dtype=int)


def _pair_bit_matrix(
    df: pd.DataFrame,
    *,
    radius: int,
    n_bits: int,
) -> tuple[np.ndarray, np.ndarray]:
    cache: dict[str, np.ndarray | None] = {}
    rows: list[np.ndarray] = []
    kept: list[int] = []
    for idx, row in enumerate(df.itertuples(index=False)):
        solute = str(row.solute_smiles)
        solvent = str(row.solvent_smiles)
        if solute not in cache:
            cache[solute] = smiles_to_morgan_fp(solute, radius=radius, n_bits=n_bits)
        if solvent not in cache:
            cache[solvent] = smiles_to_morgan_fp(solvent, radius=radius, n_bits=n_bits)
        sol_fp = cache[solute]
        slv_fp = cache[solvent]
        if sol_fp is None or slv_fp is None:
            continue
        rows.append(
            np.concatenate([sol_fp, slv_fp]).astype(np.uint8, copy=False)
        )
        kept.append(idx)
    if not rows:
        return np.empty((0, 2 * n_bits), dtype=np.uint8), np.empty((0,), dtype=int)
    return np.stack(rows).astype(np.uint8, copy=False), np.asarray(kept, dtype=int)


def _unique_pair_view(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[["pair_key", "solute_smiles", "solvent_smiles"]]
        .drop_duplicates("pair_key", keep="first")
        .reset_index(drop=True)
    )


def _fit_knn(
    X_train: np.ndarray,
    y_train: np.ndarray,
    *,
    n_neighbors: int,
    weights: str,
    metric: str,
) -> Pipeline:
    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "knn",
                KNeighborsRegressor(
                    n_neighbors=n_neighbors,
                    weights=weights,
                    metric=metric,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)
    return model


def _tanimoto_vs_train(
    query_bits: np.ndarray,
    train_bits: np.ndarray,
    train_counts: np.ndarray,
) -> np.ndarray:
    query = query_bits.astype(np.uint8, copy=False)
    query_count = int(query.sum())
    intersections = train_bits @ query.astype(np.int16, copy=False)
    unions = train_counts + query_count - intersections
    sims = np.divide(
        intersections,
        unions,
        out=np.zeros_like(intersections, dtype=np.float32),
        where=unions > 0,
    )
    return sims.astype(np.float32, copy=False)


def _nearest_neighbor_frame(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    train_pair_df: pd.DataFrame,
    test_pair_df: pd.DataFrame,
    train_pair_bits: np.ndarray,
    test_pair_bits: np.ndarray,
    *,
    cliff_threshold: float,
    n_bits: int,
) -> pd.DataFrame:
    train_counts = train_pair_bits.sum(axis=1).astype(np.int32, copy=False)
    pair_neighbors: dict[str, dict[str, float | str]] = {}

    train_by_pair: dict[str, pd.DataFrame] = {
        str(pair_key): grp.reset_index(drop=True)
        for pair_key, grp in train_df.groupby("pair_key", sort=False)
    }

    for idx, query in enumerate(test_pair_bits):
        sims = _tanimoto_vs_train(query, train_pair_bits, train_counts)
        nn_idx = int(np.argmax(sims))
        solute_query = query[:n_bits]
        solvent_query = query[n_bits:]
        solute_ref = train_pair_bits[nn_idx, :n_bits]
        solvent_ref = train_pair_bits[nn_idx, n_bits:]

        solute_inter = int(solute_query @ solute_ref.astype(np.int16, copy=False))
        solvent_inter = int(solvent_query @ solvent_ref.astype(np.int16, copy=False))
        solute_union = int(solute_query.sum() + solute_ref.sum() - solute_inter)
        solvent_union = int(solvent_query.sum() + solvent_ref.sum() - solvent_inter)
        solute_tani = float(solute_inter / solute_union) if solute_union > 0 else 0.0
        solvent_tani = float(solvent_inter / solvent_union) if solvent_union > 0 else 0.0

        pair_neighbors[str(test_pair_df.iloc[idx]["pair_key"])] = {
            "nearest_train_pair_key": str(train_pair_df.iloc[nn_idx]["pair_key"]),
            "nearest_train_solute_smiles": str(train_pair_df.iloc[nn_idx]["solute_smiles"]),
            "nearest_train_solvent_smiles": str(train_pair_df.iloc[nn_idx]["solvent_smiles"]),
            "pair_tanimoto": float(sims[nn_idx]),
            "solute_tanimoto": solute_tani,
            "solvent_tanimoto": solvent_tani,
        }

    rows: list[dict[str, Any]] = []
    for _, test_row in test_df.iterrows():
        pair_info = pair_neighbors[str(test_row["pair_key"])]
        train_pair_rows = train_by_pair[str(pair_info["nearest_train_pair_key"])]
        temp_deltas = np.abs(
            train_pair_rows["temperature"].to_numpy(dtype=float)
            - float(test_row["temperature"])
        )
        local_idx = int(np.argmin(temp_deltas))
        matched_train = train_pair_rows.iloc[local_idx]
        true_value = float(test_row["ln_x2"])
        nn_value = float(matched_train["ln_x2"])
        abs_delta = abs(true_value - nn_value)
        rows.append(
            {
                "row_index": int(test_row["row_index"]),
                "solute_smiles": str(test_row["solute_smiles"]),
                "solvent_smiles": str(test_row["solvent_smiles"]),
                "temperature": float(test_row["temperature"]),
                "ln_x2": true_value,
                "nearest_train_row_index": int(matched_train["row_index"]),
                "nearest_train_pair_key": str(pair_info["nearest_train_pair_key"]),
                "nearest_train_solute_smiles": str(pair_info["nearest_train_solute_smiles"]),
                "nearest_train_solvent_smiles": str(pair_info["nearest_train_solvent_smiles"]),
                "nearest_train_temperature": float(matched_train["temperature"]),
                "nearest_train_ln_x2": nn_value,
                "pair_tanimoto": float(pair_info["pair_tanimoto"]),
                "solute_tanimoto": float(pair_info["solute_tanimoto"]),
                "solvent_tanimoto": float(pair_info["solvent_tanimoto"]),
                "temperature_delta": abs(
                    float(test_row["temperature"]) - float(matched_train["temperature"])
                ),
                "abs_delta_ln_x2": abs_delta,
                "is_cliff": bool(abs_delta >= cliff_threshold),
            }
        )
    return pd.DataFrame(rows)


def _bin_summary(neighbor_df: pd.DataFrame) -> pd.DataFrame:
    bins = [0.0, 0.3, 0.5, 0.7, 0.85, 1.01]
    labels = ["0.00-0.30", "0.30-0.50", "0.50-0.70", "0.70-0.85", "0.85-1.00"]
    out = neighbor_df.copy()
    out["pair_tanimoto_bin"] = pd.cut(
        out["pair_tanimoto"],
        bins=bins,
        labels=labels,
        include_lowest=True,
        right=False,
    )
    grouped = (
        out.groupby("pair_tanimoto_bin", observed=False)
        .agg(
            n=("pair_tanimoto", "size"),
            mean_pair_tanimoto=("pair_tanimoto", "mean"),
            mean_abs_delta_ln_x2=("abs_delta_ln_x2", "mean"),
            median_abs_delta_ln_x2=("abs_delta_ln_x2", "median"),
            p90_abs_delta_ln_x2=("abs_delta_ln_x2", lambda s: float(np.quantile(s, 0.9)) if len(s) else np.nan),
            cliff_rate=("is_cliff", "mean"),
        )
        .reset_index()
    )
    grouped["cliff_rate"] = grouped["cliff_rate"].astype(float)
    return grouped


def _threshold_summary(neighbor_df: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
    out: dict[str, dict[str, float | int]] = {}
    for thr in thresholds:
        mask = neighbor_df["pair_tanimoto"].to_numpy(dtype=float) >= thr
        subset = neighbor_df.loc[mask]
        key = f"pair_tanimoto_gte_{thr:.1f}"
        if subset.empty:
            out[key] = {"n": 0, "mean_abs_delta_ln_x2": float("nan"), "median_abs_delta_ln_x2": float("nan"), "cliff_rate": float("nan")}
            continue
        out[key] = {
            "n": int(len(subset)),
            "mean_abs_delta_ln_x2": float(subset["abs_delta_ln_x2"].mean()),
            "median_abs_delta_ln_x2": float(subset["abs_delta_ln_x2"].median()),
            "cliff_rate": float(subset["is_cliff"].mean()),
        }
    return out


def main() -> int:
    args = parse_args()
    train_path = _bootstrap.resolve_path(args.train_data)
    test_path = _bootstrap.resolve_path(args.test_data)
    val_path = _bootstrap.resolve_path(args.val_data) if args.val_data else None
    out_dir = _bootstrap.resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_df = _maybe_subsample(
        _supervised_view(pd.read_csv(train_path, low_memory=False)),
        int(args.max_train_samples),
    )
    test_df = _maybe_subsample(
        _supervised_view(pd.read_csv(test_path, low_memory=False)),
        int(args.max_test_samples),
    )

    train_eval = train_df.reset_index(drop=True)
    test_eval = test_df.reset_index(drop=True)

    train_pair_df = _unique_pair_view(train_eval)
    test_pair_df = _unique_pair_view(test_eval)
    train_pair_bits, train_bit_keep = _pair_bit_matrix(
        train_pair_df,
        radius=args.morgan_radius,
        n_bits=args.morgan_n_bits,
    )
    test_pair_bits, test_bit_keep = _pair_bit_matrix(
        test_pair_df,
        radius=args.morgan_radius,
        n_bits=args.morgan_n_bits,
    )
    if len(train_bit_keep) != len(train_pair_df):
        raise ValueError("Unique-pair train bit-matrix dropped rows unexpectedly.")
    if len(test_bit_keep) != len(test_pair_df):
        raise ValueError("Unique-pair test bit-matrix dropped rows unexpectedly.")
    train_pair_df = train_pair_df.iloc[train_bit_keep].reset_index(drop=True)
    test_pair_df = test_pair_df.iloc[test_bit_keep].reset_index(drop=True)

    neighbor_df = _nearest_neighbor_frame(
        train_eval,
        test_eval,
        train_pair_df,
        test_pair_df,
        train_pair_bits,
        test_pair_bits,
        cliff_threshold=float(args.cliff_threshold),
        n_bits=args.morgan_n_bits,
    )

    if args.knn_mode == "sklearn_euclidean":
        X_train, train_keep = _pair_feature_matrix(
            train_df,
            radius=args.morgan_radius,
            n_bits=args.morgan_n_bits,
        )
        X_test, test_keep = _pair_feature_matrix(
            test_df,
            radius=args.morgan_radius,
            n_bits=args.morgan_n_bits,
        )
        if len(train_keep) == 0 or len(test_keep) == 0:
            raise ValueError("No valid Morgan pair features could be computed.")
        train_eval = train_df.iloc[train_keep].reset_index(drop=True)
        test_eval = test_df.iloc[test_keep].reset_index(drop=True)
        y_train = train_eval["ln_x2"].to_numpy(dtype=float)
        model = _fit_knn(
            X_train,
            y_train,
            n_neighbors=args.n_neighbors,
            weights=args.weights,
            metric=args.metric,
        )
        pred_ln_x2 = model.predict(X_test).astype(float, copy=False)
        if len(test_keep) != len(test_df):
            neighbor_df = neighbor_df.iloc[test_keep].reset_index(drop=True)
        model_name = "knn_morgan"
    else:
        pred_ln_x2 = neighbor_df["nearest_train_ln_x2"].to_numpy(dtype=float)
        model_name = "knn_pair_tanimoto_1nn"

    artifacts = build_benchmark_artifacts(
        model_name=model_name,
        eval_df=test_eval,
        pred_ln_x2=pred_ln_x2,
        metadata={
            "model_family": "knn_baseline",
            "knn_mode": args.knn_mode,
            "feature_mode": "pair_morgan",
            "n_neighbors": int(args.n_neighbors),
            "weights": args.weights,
            "metric": args.metric,
            "morgan_radius": int(args.morgan_radius),
            "morgan_n_bits": int(args.morgan_n_bits),
            "train_data": str(train_path),
            "val_data": str(val_path) if val_path is not None else None,
            "test_data": str(test_path),
        },
        split_mode="custom",
        test_data=str(test_path),
    )
    write_benchmark_artifacts(
        out_dir,
        artifacts,
        input_paths={
            "train_data": train_path,
            "val_data": val_path,
            "test_data": test_path,
        },
        command=[
            "python",
            "scripts/evaluation/run_knn_modelability.py",
            "--train-data",
            str(train_path),
            "--test-data",
            str(test_path),
            "--out-dir",
            str(out_dir),
            "--knn-mode",
            args.knn_mode,
        ],
    )

    neighbor_df["knn_pred_ln_x2"] = pred_ln_x2
    neighbor_df["knn_abs_error"] = np.abs(
        pred_ln_x2 - test_eval["ln_x2"].to_numpy(dtype=float)
    )
    neighbor_df.to_csv(out_dir / "nearest_neighbors.csv", index=False)

    bin_summary = _bin_summary(neighbor_df)
    bin_summary.to_csv(out_dir / "modelability_bins.csv", index=False)

    overall_nn_mae = float(
        mean_absolute_error(
            test_eval["ln_x2"].to_numpy(dtype=float),
            neighbor_df["nearest_train_ln_x2"].to_numpy(dtype=float),
        )
    )
    summary = {
        "train_samples": int(len(train_eval)),
        "test_samples": int(len(test_eval)),
        "knn": {
            "mae": float(artifacts.report["overall"].get("mae", float("nan"))),
            "rmse": float(artifacts.report["overall"].get("rmse", float("nan"))),
            "r2": float(artifacts.report["overall"].get("r2", float("nan"))),
            "pearson_r": float(artifacts.report["overall"].get("pearson_r", float("nan"))),
            "mode": args.knn_mode,
            "n_neighbors": int(args.n_neighbors),
            "weights": args.weights,
            "metric": args.metric,
        },
        "nearest_neighbor": {
            "mae": overall_nn_mae,
            "mean_pair_tanimoto": float(neighbor_df["pair_tanimoto"].mean()),
            "median_pair_tanimoto": float(neighbor_df["pair_tanimoto"].median()),
            "mean_abs_delta_ln_x2": float(neighbor_df["abs_delta_ln_x2"].mean()),
            "median_abs_delta_ln_x2": float(neighbor_df["abs_delta_ln_x2"].median()),
            "cliff_threshold": float(args.cliff_threshold),
            "cliff_rate": float(neighbor_df["is_cliff"].mean()),
            "thresholds": _threshold_summary(neighbor_df),
        },
    }
    (out_dir / "modelability_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
