#!/usr/bin/env python3
"""Run split-sensitivity and dataset diagnostics for ln(x2) prediction."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
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
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
except Exception as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "scikit-learn is required for run_metric_diagnostics.py. "
        "Install it with `pip install scikit-learn`."
    ) from exc

from tgnn_solv.features import compute_molecular_descriptors, smiles_to_morgan_fp  # noqa: E402
from tgnn_solv.data.utils import get_scaffold  # noqa: E402


TRUE_VALUES = {"true", "1", "yes", "y", "t"}
DEFAULT_PROTOCOLS = ("scaffold", "scaffold_random", "solute", "pair_random", "row_random")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose why ln(x2) metrics differ across split protocols by running "
            "the same RF baseline on scaffold-family, solute, pair-random, and "
            "row-random splits while also exporting overlap and target-distribution "
            "summaries."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--processed-dir",
        default="notebooks/data/processed",
        help="Directory with canonical processed split CSVs.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/metric_diagnosis",
        help="Directory for generated diagnostics and derived split CSVs.",
    )
    parser.add_argument(
        "--protocols",
        default=",".join(DEFAULT_PROTOCOLS),
        help="Comma-separated protocols to evaluate.",
    )
    parser.add_argument(
        "--rf-feature-mode",
        choices=["descriptors", "morgan", "hybrid"],
        default="hybrid",
    )
    parser.add_argument("--rf-n-estimators", type=int, default=100)
    parser.add_argument("--rf-max-depth", type=int, default=30)
    parser.add_argument("--morgan-radius", type=int, default=2)
    parser.add_argument("--morgan-n-bits", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return value


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _supervised_view(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "has_solubility" in out.columns:
        series = out["has_solubility"]
        if pd.api.types.is_bool_dtype(series):
            mask = series.fillna(False).to_numpy(dtype=bool)
        else:
            mask = (
                series.fillna(False)
                .astype(str)
                .str.strip()
                .str.lower()
                .isin(TRUE_VALUES)
                .to_numpy(dtype=bool)
            )
        out = out.loc[mask].copy()
    out["ln_x2"] = pd.to_numeric(out["ln_x2"], errors="coerce")
    out["temperature"] = pd.to_numeric(out["temperature"], errors="coerce")
    out = out.loc[np.isfinite(out["ln_x2"].to_numpy(dtype=float))].reset_index(drop=True)
    return out


def _target_stats(series: pd.Series) -> dict[str, float | int]:
    arr = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    arr = arr[np.isfinite(arr)]
    return {
        "n": int(arr.size),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "median": float(np.median(arr)),
        "p01": float(np.percentile(arr, 1)),
        "p05": float(np.percentile(arr, 5)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "frac_below_-15": float((arr < -15).mean()),
        "frac_below_-20": float((arr < -20).mean()),
    }


def _pair_series(df: pd.DataFrame) -> pd.Series:
    return df["solute_smiles"].astype(str) + "||" + df["solvent_smiles"].astype(str)


def _scaffold_series(df: pd.DataFrame) -> pd.Series:
    solutes = df["solute_smiles"].astype(str)
    scaffold_map = {
        smiles: get_scaffold(smiles) or ""
        for smiles in solutes.drop_duplicates().tolist()
    }
    return solutes.map(scaffold_map)


def _overlap_summary(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame) -> dict[str, float | int]:
    train_pairs = set(_pair_series(train_df))
    val_pairs = set(_pair_series(val_df))
    test_pairs = set(_pair_series(test_df))
    train_solutes = set(train_df["solute_smiles"].astype(str))
    val_solutes = set(val_df["solute_smiles"].astype(str))
    test_solutes = set(test_df["solute_smiles"].astype(str))
    train_scaffolds = {value for value in _scaffold_series(train_df) if value}
    val_scaffolds = {value for value in _scaffold_series(val_df) if value}
    test_scaffolds = {value for value in _scaffold_series(test_df) if value}
    train_triplets = set(zip(_pair_series(train_df), train_df["temperature"].astype(float)))
    test_triplets = set(zip(_pair_series(test_df), test_df["temperature"].astype(float)))
    return {
        "train_val_pair_overlap": int(len(train_pairs & val_pairs)),
        "train_test_pair_overlap": int(len(train_pairs & test_pairs)),
        "val_test_pair_overlap": int(len(val_pairs & test_pairs)),
        "train_test_pair_overlap_fraction_of_test": float(len(train_pairs & test_pairs) / max(len(test_pairs), 1)),
        "train_val_solute_overlap": int(len(train_solutes & val_solutes)),
        "train_test_solute_overlap": int(len(train_solutes & test_solutes)),
        "val_test_solute_overlap": int(len(val_solutes & test_solutes)),
        "train_test_solute_overlap_fraction_of_test": float(len(train_solutes & test_solutes) / max(len(test_solutes), 1)),
        "train_val_scaffold_overlap": int(len(train_scaffolds & val_scaffolds)),
        "train_test_scaffold_overlap": int(len(train_scaffolds & test_scaffolds)),
        "val_test_scaffold_overlap": int(len(val_scaffolds & test_scaffolds)),
        "train_test_scaffold_overlap_fraction_of_test": float(len(train_scaffolds & test_scaffolds) / max(len(test_scaffolds), 1)),
        "train_test_exact_pair_temperature_overlap": int(len(train_triplets & test_triplets)),
        "n_train_pairs": int(len(train_pairs)),
        "n_val_pairs": int(len(val_pairs)),
        "n_test_pairs": int(len(test_pairs)),
        "n_train_solutes": int(len(train_solutes)),
        "n_val_solutes": int(len(val_solutes)),
        "n_test_solutes": int(len(test_solutes)),
        "n_train_scaffolds": int(len(train_scaffolds)),
        "n_val_scaffolds": int(len(val_scaffolds)),
        "n_test_scaffolds": int(len(test_scaffolds)),
    }


def _pair_count_summary(df: pd.DataFrame) -> dict[str, float | int]:
    counts = df.groupby(["solute_smiles", "solvent_smiles"], dropna=False).size()
    return {
        "unique_pairs": int(len(counts)),
        "mean_points_per_pair": float(counts.mean()),
        "median_points_per_pair": float(counts.median()),
        "p90_points_per_pair": float(counts.quantile(0.90)),
        "p99_points_per_pair": float(counts.quantile(0.99)),
        "max_points_per_pair": int(counts.max()),
    }


def _load_existing_protocol(processed_dir: Path, protocol: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    suffix = {
        "scaffold": "",
        "solute": "_solute",
        "solvent": "_solvent",
    }[protocol]
    train_df = _supervised_view(_read_csv(processed_dir / f"train{suffix}.csv"))
    val_df = _supervised_view(_read_csv(processed_dir / f"val{suffix}.csv"))
    test_df = _supervised_view(_read_csv(processed_dir / f"test{suffix}.csv"))
    return train_df, val_df, test_df


def _build_row_random_split(
    full_df: pd.DataFrame,
    *,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    idx = np.arange(len(full_df))
    train_idx, temp_idx = train_test_split(idx, test_size=0.2, random_state=seed, shuffle=True)
    val_idx, test_idx = train_test_split(temp_idx, test_size=0.5, random_state=seed, shuffle=True)
    return (
        full_df.iloc[train_idx].reset_index(drop=True),
        full_df.iloc[val_idx].reset_index(drop=True),
        full_df.iloc[test_idx].reset_index(drop=True),
    )


def _build_pair_random_split(
    full_df: pd.DataFrame,
    *,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pair_df = full_df[["solute_smiles", "solvent_smiles"]].astype(str).drop_duplicates().reset_index(drop=True)
    pair_df["pair_key"] = pair_df["solute_smiles"] + "||" + pair_df["solvent_smiles"]
    pair_keys = pair_df["pair_key"].tolist()
    train_pairs, temp_pairs = train_test_split(pair_keys, test_size=0.2, random_state=seed, shuffle=True)
    val_pairs, test_pairs = train_test_split(temp_pairs, test_size=0.5, random_state=seed, shuffle=True)
    pair_key_series = _pair_series(full_df)
    return (
        full_df.loc[pair_key_series.isin(set(train_pairs))].reset_index(drop=True),
        full_df.loc[pair_key_series.isin(set(val_pairs))].reset_index(drop=True),
        full_df.loc[pair_key_series.isin(set(test_pairs))].reset_index(drop=True),
    )


def _build_scaffold_random_split(
    full_df: pd.DataFrame,
    *,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    work_df = full_df.copy()
    work_df["_scaffold_key"] = _scaffold_series(work_df)
    groups = np.asarray(
        work_df.loc[work_df["_scaffold_key"].astype(bool), "_scaffold_key"]
        .drop_duplicates()
        .astype(str)
        .tolist()
    )
    if groups.size == 0:
        raise ValueError("scaffold_random split received no valid scaffold groups.")
    train_groups, temp_groups = train_test_split(groups, test_size=0.2, random_state=seed, shuffle=True)
    val_groups, test_groups = train_test_split(temp_groups, test_size=0.5, random_state=seed, shuffle=True)
    assigned: dict[str, str] = {str(key): "train" for key in train_groups}
    assigned.update({str(key): "val" for key in val_groups})
    assigned.update({str(key): "test" for key in test_groups})

    mask = work_df["_scaffold_key"].map(assigned).fillna("train")
    return (
        work_df.loc[mask == "train"].drop(columns="_scaffold_key").reset_index(drop=True),
        work_df.loc[mask == "val"].drop(columns="_scaffold_key").reset_index(drop=True),
        work_df.loc[mask == "test"].drop(columns="_scaffold_key").reset_index(drop=True),
    )


def _safe_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    if x.size < 2 or y.size < 2:
        return None
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        mask = np.isfinite(x) & np.isfinite(y)
        x = x[mask]
        y = y[mask]
    if x.size < 2 or y.size < 2 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _heavy_atom_map(smiles_values: list[str]) -> dict[str, int | None]:
    from rdkit import Chem

    heavy_atoms: dict[str, int | None] = {}
    for smiles in smiles_values:
        mol = Chem.MolFromSmiles(smiles)
        heavy_atoms[smiles] = int(mol.GetNumHeavyAtoms()) if mol is not None else None
    return heavy_atoms


def _scaffold_bias_summary(
    full_df: pd.DataFrame,
    *,
    scaffold_protocols: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]],
    heavy_atom_map: dict[str, int | None],
) -> dict[str, Any]:
    work_df = full_df.copy()
    work_df["scaffold"] = _scaffold_series(work_df)
    work_df["solute_heavy_atoms"] = work_df["solute_smiles"].astype(str).map(heavy_atom_map)
    group_frame = (
        work_df.loc[work_df["scaffold"].astype(bool)]
        .groupby("scaffold", dropna=False)
        .agg(
            n_rows=("ln_x2", "size"),
            n_solutes=("solute_smiles", "nunique"),
            mean_ln_x2=("ln_x2", "mean"),
            median_ln_x2=("ln_x2", "median"),
            mean_temp=("temperature", "mean"),
            mean_heavy_atoms=("solute_heavy_atoms", "mean"),
        )
        .reset_index()
    )

    all_rows = group_frame["n_rows"].to_numpy(dtype=float)
    all_solutes = group_frame["n_solutes"].to_numpy(dtype=float)
    all_mean_ln_x2 = group_frame["mean_ln_x2"].to_numpy(dtype=float)
    all_heavy_atoms = group_frame["mean_heavy_atoms"].to_numpy(dtype=float)

    protocol_payload: dict[str, Any] = {}
    for protocol, (_, _, test_df) in scaffold_protocols.items():
        test_scaffolds = {value for value in _scaffold_series(test_df) if value}
        subset = group_frame.loc[group_frame["scaffold"].isin(test_scaffolds)].copy()
        protocol_payload[protocol] = {
            "n_test_scaffolds": int(len(subset)),
            "test_group_rows_mean": float(subset["n_rows"].mean()) if len(subset) else None,
            "test_group_rows_median": float(subset["n_rows"].median()) if len(subset) else None,
            "test_group_rows_p90": float(subset["n_rows"].quantile(0.90)) if len(subset) else None,
            "test_group_solutes_mean": float(subset["n_solutes"].mean()) if len(subset) else None,
            "test_group_heavy_atoms_mean": float(subset["mean_heavy_atoms"].mean()) if len(subset) else None,
            "test_group_ln_x2_mean": float(subset["mean_ln_x2"].mean()) if len(subset) else None,
            "test_group_ln_x2_median": float(subset["mean_ln_x2"].median()) if len(subset) else None,
        }

    return {
        "global": {
            "n_scaffolds": int(len(group_frame)),
            "corr_rows_vs_mean_ln_x2": _safe_corr(all_rows, all_mean_ln_x2),
            "corr_unique_solutes_vs_mean_ln_x2": _safe_corr(all_solutes, all_mean_ln_x2),
            "corr_rows_vs_mean_heavy_atoms": _safe_corr(all_rows, all_heavy_atoms),
            "corr_heavy_atoms_vs_mean_ln_x2": _safe_corr(all_heavy_atoms, all_mean_ln_x2),
        },
        "protocols": protocol_payload,
    }


def _descriptor_map(smiles_values: list[str]) -> dict[str, np.ndarray | None]:
    return {smiles: compute_molecular_descriptors(smiles) for smiles in smiles_values}


def _morgan_map(
    smiles_values: list[str],
    *,
    radius: int,
    n_bits: int,
) -> dict[str, np.ndarray | None]:
    return {
        smiles: smiles_to_morgan_fp(smiles, radius=radius, n_bits=n_bits)
        for smiles in smiles_values
    }


def _feature_matrix(
    df: pd.DataFrame,
    *,
    feature_mode: str,
    descriptor_cache: dict[str, np.ndarray | None],
    morgan_cache: dict[str, np.ndarray | None],
) -> tuple[np.ndarray, np.ndarray]:
    rows: list[np.ndarray] = []
    targets: list[float] = []
    for row in df.itertuples(index=False):
        solute = str(row.solute_smiles)
        solvent = str(row.solvent_smiles)
        temp = float(row.temperature)
        inv_temp = 1.0 / temp

        desc_features = None
        morgan_features = None

        if feature_mode in {"descriptors", "hybrid"}:
            sol_desc = descriptor_cache.get(solute)
            slv_desc = descriptor_cache.get(solvent)
            if sol_desc is not None and slv_desc is not None:
                desc_features = np.concatenate(
                    [
                        sol_desc.astype(float, copy=False),
                        slv_desc.astype(float, copy=False),
                        [temp, inv_temp],
                    ]
                )
        if feature_mode in {"morgan", "hybrid"}:
            sol_fp = morgan_cache.get(solute)
            slv_fp = morgan_cache.get(solvent)
            if sol_fp is not None and slv_fp is not None:
                morgan_features = np.concatenate(
                    [
                        sol_fp.astype(float, copy=False),
                        slv_fp.astype(float, copy=False),
                        [temp, inv_temp],
                    ]
                )

        if feature_mode == "descriptors":
            features = desc_features
        elif feature_mode == "morgan":
            features = morgan_features
        else:
            if desc_features is None or morgan_features is None:
                features = None
            else:
                features = np.concatenate([desc_features, morgan_features]).astype(np.float32, copy=False)

        if features is None:
            continue

        target = float(row.ln_x2)
        if not np.isfinite(target):
            continue
        rows.append(features)
        targets.append(target)

    if not rows:
        return np.empty((0, 0), dtype=np.float32), np.empty((0,), dtype=np.float32)
    return np.asarray(rows, dtype=np.float32), np.asarray(targets, dtype=np.float32)


def _rf_metrics(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    feature_mode: str,
    descriptor_cache: dict[str, np.ndarray | None],
    morgan_cache: dict[str, np.ndarray | None],
    n_estimators: int,
    max_depth: int,
    seed: int,
) -> dict[str, float | int]:
    X_train, y_train = _feature_matrix(
        train_df,
        feature_mode=feature_mode,
        descriptor_cache=descriptor_cache,
        morgan_cache=morgan_cache,
    )
    X_test, y_test = _feature_matrix(
        test_df,
        feature_mode=feature_mode,
        descriptor_cache=descriptor_cache,
        morgan_cache=morgan_cache,
    )
    if len(X_train) == 0 or len(X_test) == 0:
        raise ValueError("RF diagnostics received an empty feature matrix.")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        n_jobs=-1,
        random_state=seed,
    )
    model.fit(X_train_scaled, y_train)
    preds = model.predict(X_test_scaled)
    pearson_r = float(np.corrcoef(y_test, preds)[0, 1]) if np.std(y_test) > 0 and np.std(preds) > 0 else float("nan")
    return {
        "mae": float(mean_absolute_error(y_test, preds)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, preds))),
        "r2": float(r2_score(y_test, preds)),
        "pearson_r": pearson_r,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }


def _directgnn_gap_summary(log_path: Path) -> dict[str, float | int | None]:
    if not log_path.exists():
        return {}
    pattern = re.compile(
        r"Epoch\s+(?P<epoch>\d+)/(?P<epochs>\d+): train=(?P<train>[0-9.]+), val_MAE=(?P<val_mae>[0-9.]+), val_R²=(?P<val_r2>[-0-9.]+)"
    )
    matches = [pattern.search(line) for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines()]
    records = [m.groupdict() for m in matches if m]
    if not records:
        return {}
    last = records[-1]
    train_value = float(last["train"])
    val_mae = float(last["val_mae"])
    return {
        "epoch": int(last["epoch"]),
        "epochs": int(last["epochs"]),
        "train_objective": train_value,
        "val_mae": val_mae,
        "val_r2": float(last["val_r2"]),
        "val_minus_train": float(val_mae - train_value),
        "log_path": str(log_path),
    }


def _runtime_availability() -> dict[str, bool]:
    return {
        "fastsolv": importlib.util.find_spec("fastsolv") is not None,
        "solprop": importlib.util.find_spec("solprop") is not None,
        "rdkit": importlib.util.find_spec("rdkit") is not None,
        "sklearn": importlib.util.find_spec("sklearn") is not None,
    }


def _write_split_csvs(
    out_dir: Path,
    protocol: str,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> None:
    train_df.to_csv(out_dir / f"train_{protocol}.csv", index=False)
    val_df.to_csv(out_dir / f"val_{protocol}.csv", index=False)
    test_df.to_csv(out_dir / f"test_{protocol}.csv", index=False)


def _protocol_summary(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict[str, Any]:
    full_df = pd.concat([train_df, val_df, test_df], ignore_index=True)
    return {
        "row_counts": {
            "train": int(len(train_df)),
            "val": int(len(val_df)),
            "test": int(len(test_df)),
            "total": int(len(full_df)),
        },
        "target": {
            "train": _target_stats(train_df["ln_x2"]),
            "val": _target_stats(val_df["ln_x2"]),
            "test": _target_stats(test_df["ln_x2"]),
            "all": _target_stats(full_df["ln_x2"]),
        },
        "pair_counts": _pair_count_summary(full_df),
        "scaffold_counts": {
            "train": int(len({value for value in _scaffold_series(train_df) if value})),
            "val": int(len({value for value in _scaffold_series(val_df) if value})),
            "test": int(len({value for value in _scaffold_series(test_df) if value})),
            "all": int(len({value for value in _scaffold_series(full_df) if value})),
        },
        "overlap": _overlap_summary(train_df, val_df, test_df),
    }


def main() -> None:
    args = parse_args()
    processed_dir = Path(args.processed_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    protocol_order = [item.strip() for item in args.protocols.split(",") if item.strip()]
    supported = {"scaffold", "scaffold_random", "solute", "solvent", "pair_random", "row_random"}
    unsupported = sorted(set(protocol_order) - supported)
    if unsupported:
        raise ValueError(f"Unsupported protocols: {unsupported}")

    scaffold_train, scaffold_val, scaffold_test = _load_existing_protocol(processed_dir, "scaffold")
    full_df = pd.concat([scaffold_train, scaffold_val, scaffold_test], ignore_index=True).reset_index(drop=True)
    unique_smiles = sorted(
        set(full_df["solute_smiles"].astype(str)).union(set(full_df["solvent_smiles"].astype(str)))
    )
    heavy_atom_map = _heavy_atom_map(sorted(set(full_df["solute_smiles"].astype(str))))

    descriptor_cache = _descriptor_map(unique_smiles) if args.rf_feature_mode in {"descriptors", "hybrid"} else {}
    morgan_cache = (
        _morgan_map(unique_smiles, radius=args.morgan_radius, n_bits=args.morgan_n_bits)
        if args.rf_feature_mode in {"morgan", "hybrid"}
        else {}
    )

    payload: dict[str, Any] = {
        "config": {
            "processed_dir": str(processed_dir),
            "out_dir": str(out_dir),
            "protocols": protocol_order,
            "seed": int(args.seed),
            "rf_feature_mode": args.rf_feature_mode,
            "rf_n_estimators": int(args.rf_n_estimators),
            "rf_max_depth": int(args.rf_max_depth),
            "morgan_radius": int(args.morgan_radius),
            "morgan_n_bits": int(args.morgan_n_bits),
        },
        "runtime_availability": _runtime_availability(),
        "dataset_summary": {
            "overall_target": _target_stats(full_df["ln_x2"]),
            "overall_pair_counts": _pair_count_summary(full_df),
            "unique_solutes": int(full_df["solute_smiles"].nunique(dropna=True)),
            "unique_solvents": int(full_df["solvent_smiles"].nunique(dropna=True)),
            "unique_scaffolds": int(len({value for value in _scaffold_series(full_df) if value})),
        },
        "protocol_summaries": {},
        "rf_results": {},
        "directgnn_proxy_gap": _directgnn_gap_summary(
            Path("results/proxy_comparison/log_directgnn_tuned_train.txt").resolve()
        ),
    }

    split_frames: dict[str, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = {}
    for protocol in protocol_order:
        if protocol in {"scaffold", "solute", "solvent"}:
            train_df, val_df, test_df = _load_existing_protocol(processed_dir, protocol)
        elif protocol == "scaffold_random":
            train_df, val_df, test_df = _build_scaffold_random_split(full_df, seed=args.seed)
            _write_split_csvs(out_dir, protocol, train_df, val_df, test_df)
        elif protocol == "row_random":
            train_df, val_df, test_df = _build_row_random_split(full_df, seed=args.seed)
            _write_split_csvs(out_dir, protocol, train_df, val_df, test_df)
        else:  # pair_random
            train_df, val_df, test_df = _build_pair_random_split(full_df, seed=args.seed)
            _write_split_csvs(out_dir, protocol, train_df, val_df, test_df)

        split_frames[protocol] = (train_df, val_df, test_df)
        payload["protocol_summaries"][protocol] = _protocol_summary(train_df, val_df, test_df)

        print(f"[metric-diagnostics] fitting RF on {protocol}...", flush=True)
        payload["rf_results"][protocol] = _rf_metrics(
            train_df,
            test_df,
            feature_mode=args.rf_feature_mode,
            descriptor_cache=descriptor_cache,
            morgan_cache=morgan_cache,
            n_estimators=args.rf_n_estimators,
            max_depth=args.rf_max_depth,
            seed=args.seed,
        )
        print(
            "[metric-diagnostics] "
            f"{protocol}: MAE={payload['rf_results'][protocol]['mae']:.3f}, "
            f"R2={payload['rf_results'][protocol]['r2']:.3f}",
            flush=True,
        )

    scaffold_protocols = {
        protocol: frames
        for protocol, frames in split_frames.items()
        if protocol in {"scaffold", "scaffold_random"}
    }
    if scaffold_protocols:
        payload["scaffold_bias_diagnostics"] = _scaffold_bias_summary(
            full_df,
            scaffold_protocols=scaffold_protocols,
            heavy_atom_map=heavy_atom_map,
        )

    comparison_lines = [
        "# Metric Diagnosis Summary",
        "",
        "## RF by protocol",
        "",
    ]
    for protocol in protocol_order:
        metrics = payload["rf_results"][protocol]
        overlap = payload["protocol_summaries"][protocol]["overlap"]
        comparison_lines.append(
            f"- `{protocol}`: MAE `{metrics['mae']:.3f}`, R² `{metrics['r2']:.3f}`, "
            f"train-test pair overlap `{100 * overlap['train_test_pair_overlap_fraction_of_test']:.1f}%`, "
            f"train-test solute overlap `{100 * overlap['train_test_solute_overlap_fraction_of_test']:.1f}%`"
        )

    comparison_lines.extend(
        [
            "",
            "## Dataset shape",
            "",
            f"- Supervised rows: `{payload['dataset_summary']['overall_target']['n']}`",
            f"- Unique solutes: `{payload['dataset_summary']['unique_solutes']}`",
            f"- Unique solvents: `{payload['dataset_summary']['unique_solvents']}`",
            f"- Unique scaffolds: `{payload['dataset_summary']['unique_scaffolds']}`",
            f"- Unique pairs: `{payload['dataset_summary']['overall_pair_counts']['unique_pairs']}`",
            f"- Median points per pair: `{payload['dataset_summary']['overall_pair_counts']['median_points_per_pair']:.1f}`",
            "",
            "## Scaffold bias diagnostics",
            "",
        ]
    )
    scaffold_bias = payload.get("scaffold_bias_diagnostics", {})
    if scaffold_bias:
        global_bias = scaffold_bias.get("global", {})
        comparison_lines.extend(
            [
                f"- corr(rows per scaffold, mean ln_x2): `{global_bias.get('corr_rows_vs_mean_ln_x2')}`",
                f"- corr(rows per scaffold, mean heavy atoms): `{global_bias.get('corr_rows_vs_mean_heavy_atoms')}`",
                f"- corr(mean heavy atoms, mean ln_x2): `{global_bias.get('corr_heavy_atoms_vs_mean_ln_x2')}`",
            ]
        )
        for protocol, stats in scaffold_bias.get("protocols", {}).items():
            comparison_lines.append(
                f"- `{protocol}` test scaffolds: mean rows/group `{stats['test_group_rows_mean']:.2f}`, "
                f"mean heavy atoms `{stats['test_group_heavy_atoms_mean']:.2f}`, "
                f"mean scaffold-mean ln_x2 `{stats['test_group_ln_x2_mean']:.3f}`"
            )

    comparison_lines.extend(
        [
            "",
            "## External baseline runtime availability",
            "",
            f"- `fastsolv`: `{payload['runtime_availability']['fastsolv']}`",
            f"- `solprop`: `{payload['runtime_availability']['solprop']}`",
        ]
    )

    (out_dir / "summary.json").write_text(json.dumps(_json_ready(payload), indent=2), encoding="utf-8")
    (out_dir / "comparison_table.md").write_text("\n".join(comparison_lines) + "\n", encoding="utf-8")
    print(f"[metric-diagnostics] wrote {out_dir / 'summary.json'}")
    print(f"[metric-diagnostics] wrote {out_dir / 'comparison_table.md'}")


if __name__ == "__main__":
    main()
