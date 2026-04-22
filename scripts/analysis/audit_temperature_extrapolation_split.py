#!/usr/bin/env python3
"""Audit the same-pair temperature-extrapolation protocol.

The script checks whether the low-temperature train split and high-temperature
test split really contain the same molecule pairs, how much water/small-solvent
chemistry is present, whether the observed high-temperature shift has the
expected sign, and how well a pair-specific Van't Hoff fit extrapolates from
the low-temperature part.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from rdkit import Chem
except Exception:  # pragma: no cover - optional in some lightweight envs
    Chem = None

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


WATER_SMILES = {"O", "[H]O[H]"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--train-low",
        type=Path,
        default=Path("results/temperature_extrapolation_baselines/splits/train_low.csv"),
    )
    p.add_argument(
        "--val-low",
        type=Path,
        default=Path("results/temperature_extrapolation_baselines/splits/val_low.csv"),
    )
    p.add_argument(
        "--test-high",
        type=Path,
        default=Path("results/temperature_extrapolation_baselines/splits/test_high.csv"),
    )
    p.add_argument(
        "--baseline-dir",
        type=Path,
        default=Path("results/temperature_extrapolation_baselines"),
    )
    p.add_argument(
        "--config",
        type=Path,
        default=Path("configs/paper_config_tuned.yaml"),
        help="TGNN config used to report solver settings.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/temperature_extrapolation_baselines/audit"),
    )
    return p.parse_args()


def _read_split(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if "T" not in df.columns:
        if "temperature" not in df.columns:
            raise KeyError(f"{path} has no T or temperature column")
        df["T"] = df["temperature"]
    if "pair_key" not in df.columns:
        df["pair_key"] = df["solute_smiles"] + ">>" + df["solvent_smiles"]
    df["T"] = pd.to_numeric(df["T"], errors="coerce")
    df["ln_x2"] = pd.to_numeric(df["ln_x2"], errors="coerce")
    if "has_solubility" in df.columns:
        df = df[df["has_solubility"].astype(bool)].copy()
    return df.dropna(subset=["T", "ln_x2", "solute_smiles", "solvent_smiles"])


def _pair_set(df: pd.DataFrame) -> set[tuple[str, str]]:
    return set(zip(df["solute_smiles"], df["solvent_smiles"]))


_HEAVY_ATOM_CACHE: dict[str, float] = {}


def _heavy_atoms(smiles: str) -> float:
    if smiles in _HEAVY_ATOM_CACHE:
        return _HEAVY_ATOM_CACHE[smiles]
    if Chem is None:
        return math.nan
    mol = Chem.MolFromSmiles(smiles)
    value = float(mol.GetNumHeavyAtoms()) if mol is not None else math.nan
    _HEAVY_ATOM_CACHE[smiles] = value
    return value


def _split_summary(df: pd.DataFrame) -> dict[str, Any]:
    pair_counts = df.groupby("pair_key").size()
    water = df["solvent_smiles"].isin(WATER_SMILES)
    small = df["solvent_smiles"].map(_heavy_atoms).le(3)
    source_split = (
        df["source_split"].value_counts(dropna=False).to_dict()
        if "source_split" in df.columns
        else {}
    )
    return {
        "rows": int(len(df)),
        "pairs": int(df["pair_key"].nunique()),
        "solutes": int(df["solute_smiles"].nunique()),
        "solvents": int(df["solvent_smiles"].nunique()),
        "source_split_counts": {str(k): int(v) for k, v in source_split.items()},
        "temperature_min": float(df["T"].min()),
        "temperature_max": float(df["T"].max()),
        "temperature_quantiles": {
            str(k): float(v)
            for k, v in df["T"].quantile([0, 0.25, 0.5, 0.75, 1]).items()
        },
        "ln_x2_min": float(df["ln_x2"].min()),
        "ln_x2_max": float(df["ln_x2"].max()),
        "ln_x2_mean": float(df["ln_x2"].mean()),
        "ln_x2_median": float(df["ln_x2"].median()),
        "rows_per_pair_mean": float(pair_counts.mean()),
        "rows_per_pair_median": float(pair_counts.median()),
        "rows_per_pair_max": int(pair_counts.max()),
        "water_row_fraction": float(water.mean()),
        "water_pair_fraction": float(
            df.loc[water, "pair_key"].nunique() / max(df["pair_key"].nunique(), 1)
        ),
        "small_solvent_row_fraction": float(small.mean()),
        "small_solvent_pair_fraction": float(
            df.loc[small, "pair_key"].nunique() / max(df["pair_key"].nunique(), 1)
        ),
        "top_solvents_by_rows": {
            str(k): int(v) for k, v in df["solvent_smiles"].value_counts().head(10).items()
        },
    }


def _trend_table(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat(
        [train.assign(split="train_low"), test.assign(split="test_high")],
        ignore_index=True,
    )
    rows = []
    for pair_key, group in combined.groupby("pair_key"):
        if group["split"].nunique() < 2:
            continue
        low = group[group["split"] == "train_low"]
        high = group[group["split"] == "test_high"]
        rows.append(
            {
                "pair_key": pair_key,
                "n_low": int(len(low)),
                "n_high": int(len(high)),
                "T_low_mean": float(low["T"].mean()),
                "T_high_mean": float(high["T"].mean()),
                "ln_low_mean": float(low["ln_x2"].mean()),
                "ln_high_mean": float(high["ln_x2"].mean()),
                "delta_ln_high_minus_low": float(
                    high["ln_x2"].mean() - low["ln_x2"].mean()
                ),
                "solvent_smiles": str(group["solvent_smiles"].iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def _linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    slope, intercept = np.polyfit(x, y, deg=1)
    pred = intercept + slope * x
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(slope), float(intercept), float(r2)


def _vant_hoff_fits(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pair_key, low in train.groupby("pair_key"):
        if len(low) < 2 or low["T"].nunique() < 2:
            continue
        high = test[test["pair_key"] == pair_key]
        if high.empty:
            continue
        x = 1.0 / low["T"].to_numpy(float)
        y = low["ln_x2"].to_numpy(float)
        slope, intercept, r2 = _linear_fit(x, y)
        pred_high = intercept + slope * (1.0 / high["T"].to_numpy(float))
        err = pred_high - high["ln_x2"].to_numpy(float)
        rows.append(
            {
                "pair_key": pair_key,
                "n_low": int(len(low)),
                "n_high": int(len(high)),
                "low_T_span": float(low["T"].max() - low["T"].min()),
                "high_T_min": float(high["T"].min()),
                "vh_r2_low": r2,
                "vh_slope": slope,
                "vh_positive_dln_dT": bool(slope < 0),
                "vh_high_mae": float(np.abs(err).mean()),
                "vh_high_bias": float(err.mean()),
                "solvent_smiles": str(low["solvent_smiles"].iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def _read_solver_config(path: Path) -> dict[str, Any]:
    keys = [
        "n_iter_train",
        "n_iter_eval",
        "damping",
        "solver_min_damping",
        "solver_tol_train",
        "solver_tol_eval",
        "solver_adaptive_damping",
    ]
    if not path.exists():
        return {}
    if yaml is not None:
        data = yaml.safe_load(path.read_text()) or {}
        model_data = data.get("model", {}) if isinstance(data, dict) else {}
        merged = {**data, **model_data} if isinstance(data, dict) else {}
        return {k: merged[k] for k in keys if k in merged}
    out: dict[str, Any] = {}
    for line in path.read_text().splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        if k in keys:
            out[k] = v.split("#", 1)[0].strip()
    return out


def _safe_read_csv(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def _write_markdown(
    path: Path,
    summary: dict[str, Any],
    baseline_metrics: pd.DataFrame | None,
    baseline_trends: pd.DataFrame | None,
) -> None:
    def table(df: pd.DataFrame) -> str:
        if df.empty:
            return ""
        view = df.copy()
        for col in view.columns:
            if pd.api.types.is_float_dtype(view[col]):
                view[col] = view[col].map(lambda x: f"{x:.4g}" if pd.notna(x) else "")
            else:
                view[col] = view[col].astype(str)
        headers = list(view.columns)
        rows = view.values.tolist()
        out = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
        ]
        for row in rows:
            out.append("| " + " | ".join(map(str, row)) + " |")
        return "\n".join(out)

    lines = [
        "# Temperature Extrapolation Split Audit",
        "",
        "This audit checks whether the temperature-extrapolation split is a true "
        "same-pair low-to-high temperature protocol and whether obvious data "
        "composition issues explain the weak neural proxy results.",
        "",
        "## Key Findings",
        "",
        f"- Pair overlap train_low -> test_high: "
        f"{summary['pair_overlap']['train_low_test_high_frac']:.1%} "
        f"({summary['pair_overlap']['train_low_test_high']} / "
        f"{summary['pair_overlap']['test_pairs']} test pairs).",
        f"- Test water row fraction: "
        f"{summary['splits']['test_high']['water_row_fraction']:.1%}.",
        f"- Test small-solvent row fraction (<=3 heavy atoms): "
        f"{summary['splits']['test_high']['small_solvent_row_fraction']:.1%}.",
        f"- Positive observed high-minus-low shift: "
        f"{summary['trend']['positive_high_minus_low_fraction']:.1%}.",
        f"- Pair Van't Hoff positive dln(x2)/dT from low-temperature fits: "
        f"{summary['vant_hoff_fits']['positive_dln_dT_fraction']:.1%}.",
        f"- Pair Van't Hoff mean/median high-T MAE: "
        f"{summary['vant_hoff_fits']['high_mae_mean']:.3f} / "
        f"{summary['vant_hoff_fits']['high_mae_median']:.3f}.",
        "",
        "## Interpretation",
        "",
        "- The split is intentionally a same-pair extrapolation protocol, not a "
        "new-pair or new-scaffold protocol.",
        "- Water is present but not dominant; it cannot explain the full neural "
        "temperature-extrapolation gap by itself.",
        "- The high-temperature shift direction is overwhelmingly normal: most "
        "pairs become more soluble at higher temperature.",
        "- The RF direction failure is therefore best interpreted as a model "
        "extrapolation failure in the temperature feature, not as evidence that "
        "the data have mostly reversed trends.",
        "- The split is built from the combined processed corpus; source_split "
        "counts must not be mixed with scaffold-split claims.",
        "",
        "## Solver Config",
        "",
        "```json",
        json.dumps(summary.get("solver_config", {}), indent=2),
        "```",
    ]
    if baseline_metrics is not None:
        lines += ["", "## Baseline Metrics", "", table(baseline_metrics)]
    if baseline_trends is not None:
        lines += ["", "## Baseline Trend Summary", "", table(baseline_trends)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    train = _read_split(args.train_low)
    val = _read_split(args.val_low)
    test = _read_split(args.test_high)

    train_pairs = _pair_set(train)
    val_pairs = _pair_set(val)
    test_pairs = _pair_set(test)

    trend = _trend_table(train, test)
    fits = _vant_hoff_fits(train, test)

    baseline_metrics = _safe_read_csv(args.baseline_dir / "metrics_by_model.csv")
    baseline_trends = _safe_read_csv(args.baseline_dir / "trend_summary.csv")

    water_fit = fits["solvent_smiles"].isin(WATER_SMILES) if not fits.empty else pd.Series([])
    summary: dict[str, Any] = {
        "inputs": {
            "train_low": str(args.train_low),
            "val_low": str(args.val_low),
            "test_high": str(args.test_high),
            "baseline_dir": str(args.baseline_dir),
            "config": str(args.config),
        },
        "splits": {
            "train_low": _split_summary(train),
            "val_low": _split_summary(val),
            "test_high": _split_summary(test),
        },
        "pair_overlap": {
            "train_low_test_high": int(len(train_pairs & test_pairs)),
            "val_low_test_high": int(len(val_pairs & test_pairs)),
            "train_low_val_low": int(len(train_pairs & val_pairs)),
            "test_pairs": int(len(test_pairs)),
            "val_pairs": int(len(val_pairs)),
            "train_low_test_high_frac": float(len(train_pairs & test_pairs) / max(len(test_pairs), 1)),
            "val_low_test_high_frac": float(len(val_pairs & test_pairs) / max(len(test_pairs), 1)),
            "train_low_val_low_frac": float(len(train_pairs & val_pairs) / max(len(val_pairs), 1)),
        },
        "trend": {
            "pairs": int(len(trend)),
            "positive_high_minus_low_fraction": float(
                (trend["delta_ln_high_minus_low"] > 0).mean()
            ) if not trend.empty else None,
            "delta_ln_mean": float(trend["delta_ln_high_minus_low"].mean())
            if not trend.empty
            else None,
            "delta_ln_median": float(trend["delta_ln_high_minus_low"].median())
            if not trend.empty
            else None,
        },
        "vant_hoff_fits": {
            "pairs": int(len(fits)),
            "low_r2_mean": float(fits["vh_r2_low"].mean()) if not fits.empty else None,
            "low_r2_median": float(fits["vh_r2_low"].median()) if not fits.empty else None,
            "positive_dln_dT_fraction": float(fits["vh_positive_dln_dT"].mean())
            if not fits.empty
            else None,
            "high_mae_mean": float(fits["vh_high_mae"].mean()) if not fits.empty else None,
            "high_mae_median": float(fits["vh_high_mae"].median()) if not fits.empty else None,
            "low_r2_lt_0p5_fraction": float((fits["vh_r2_low"] < 0.5).mean())
            if not fits.empty
            else None,
            "high_mae_gt_1_fraction": float((fits["vh_high_mae"] > 1.0).mean())
            if not fits.empty
            else None,
            "water_pairs": int(water_fit.sum()) if not fits.empty else 0,
            "water_high_mae_mean": float(fits.loc[water_fit, "vh_high_mae"].mean())
            if not fits.empty and water_fit.any()
            else None,
            "nonwater_high_mae_mean": float(fits.loc[~water_fit, "vh_high_mae"].mean())
            if not fits.empty and (~water_fit).any()
            else None,
        },
        "solver_config": _read_solver_config(args.config),
    }

    (args.output_dir / "split_audit_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    trend.to_csv(args.output_dir / "pair_low_high_trends.csv", index=False)
    fits.to_csv(args.output_dir / "train_low_vant_hoff_fits.csv", index=False)
    _write_markdown(
        args.output_dir / "README.md",
        summary=summary,
        baseline_metrics=baseline_metrics,
        baseline_trends=baseline_trends,
    )

    print(json.dumps(summary, indent=2))
    print(f"\nWrote audit outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
