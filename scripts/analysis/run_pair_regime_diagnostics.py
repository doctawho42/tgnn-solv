#!/usr/bin/env python3
"""Diagnose prediction quality for known-pair and new-pair regimes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def _pair_key(df: pd.DataFrame) -> pd.Series:
    if "pair_key" in df.columns:
        key = df["pair_key"].astype(str)
        missing = key.eq("") | key.eq("nan")
        if not missing.any():
            return key
    if {"solute_smiles", "solvent_smiles"}.issubset(df.columns):
        return df["solute_smiles"].astype(str) + ">>" + df["solvent_smiles"].astype(str)
    raise ValueError("Input must contain pair_key or solute_smiles/solvent_smiles")


def _first_existing(df: pd.DataFrame, candidates: list[str]) -> str:
    for col in candidates:
        if col in df.columns:
            return col
    raise ValueError(f"None of the expected columns is present: {candidates}")


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[mask]
    y_pred = y_pred[mask]
    if len(y_true) == 0:
        return {
            "n": 0,
            "mae": float("nan"),
            "rmse": float("nan"),
            "bias": float("nan"),
            "r2": float("nan"),
            "std_true": float("nan"),
            "std_pred": float("nan"),
        }
    err = y_pred - y_true
    ss_res = float(np.square(err).sum())
    ss_tot = float(np.square(y_true - y_true.mean()).sum())
    return {
        "n": int(len(y_true)),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(np.square(err)))),
        "bias": float(np.mean(err)),
        "r2": float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "std_true": float(np.std(y_true)),
        "std_pred": float(np.std(y_pred)),
    }


def _parse_prediction_spec(raw: str) -> tuple[str, Path]:
    if "=" in raw:
        label, path = raw.split("=", 1)
        return label.strip(), Path(path)
    path = Path(raw)
    return path.stem, path


def _table_text(df: pd.DataFrame) -> str:
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return df.to_string(index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare prediction metrics for pairs seen and unseen in train."
    )
    parser.add_argument("--train-data", required=True, type=Path)
    parser.add_argument("--test-data", required=True, type=Path)
    parser.add_argument("--prediction", action="append", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    train = pd.read_csv(args.train_data, low_memory=False)
    test = pd.read_csv(args.test_data, low_memory=False)
    train_pairs = set(_pair_key(train))
    train_solutes = set(train["solute_smiles"].astype(str)) if "solute_smiles" in train else set()
    train_solvents = set(train["solvent_smiles"].astype(str)) if "solvent_smiles" in train else set()

    test_pairs = _pair_key(test)
    test_pair_regime = np.where(test_pairs.isin(train_pairs), "known_pair", "new_pair")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    coverage: list[dict[str, object]] = []

    for raw_spec in args.prediction:
        label, path = _parse_prediction_spec(raw_spec)
        pred_df = pd.read_csv(path, low_memory=False)
        y_col = _first_existing(pred_df, ["ln_x2_true", "ln_x2"])
        pred_col = _first_existing(pred_df, ["ln_x2_pred", "ln_x2_final", "prediction"])
        pair = _pair_key(pred_df)

        if len(pred_df) == len(test):
            regime = test_pair_regime
        else:
            regime = np.where(pair.isin(train_pairs), "known_pair", "new_pair")

        if "solute_smiles" in pred_df:
            solute_regime = np.where(
                pred_df["solute_smiles"].astype(str).isin(train_solutes),
                "known_solute",
                "new_solute",
            )
        else:
            solute_regime = np.array(["unknown_solute"] * len(pred_df))
        if "solvent_smiles" in pred_df:
            solvent_regime = np.where(
                pred_df["solvent_smiles"].astype(str).isin(train_solvents),
                "known_solvent",
                "new_solvent",
            )
        else:
            solvent_regime = np.array(["unknown_solvent"] * len(pred_df))

        y_true = pred_df[y_col].to_numpy(dtype=float)
        y_pred = pred_df[pred_col].to_numpy(dtype=float)
        for split_name, values in {
            "all": np.array(["all"] * len(pred_df)),
            "pair_regime": regime,
            "solute_regime": solute_regime,
            "solvent_regime": solvent_regime,
        }.items():
            for value in sorted(set(values.tolist())):
                mask = values == value
                m = _metrics(y_true[mask], y_pred[mask])
                rows.append({"model": label, "slice": split_name, "value": value, **m})

        coverage.append(
            {
                "model": label,
                "rows": int(len(pred_df)),
                "known_pair_fraction": float(np.mean(regime == "known_pair")),
                "known_solute_fraction": float(np.mean(solute_regime == "known_solute")),
                "known_solvent_fraction": float(np.mean(solvent_regime == "known_solvent")),
            }
        )

    metrics = pd.DataFrame(rows)
    coverage_df = pd.DataFrame(coverage)
    metrics.to_csv(args.out_dir / "regime_metrics.csv", index=False)
    coverage_df.to_csv(args.out_dir / "regime_coverage.csv", index=False)

    summary = {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_pairs": int(len(train_pairs)),
        "test_known_pair_fraction": float(np.mean(test_pair_regime == "known_pair")),
        "metrics": rows,
        "coverage": coverage,
    }
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )

    lines = [
        "# Pair-Regime Diagnostics",
        "",
        f"Train rows: {len(train):,}",
        f"Test rows: {len(test):,}",
        f"Train pairs: {len(train_pairs):,}",
        f"Known-pair fraction in test: {summary['test_known_pair_fraction']:.3f}",
        "",
        "## Metrics",
        "",
        _table_text(metrics),
        "",
        "## Coverage",
        "",
        _table_text(coverage_df),
        "",
    ]
    (args.out_dir / "SUMMARY.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
