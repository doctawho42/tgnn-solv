#!/usr/bin/env python3
"""Build pseudo high-temperature Van't Hoff anchor rows for a train split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fit ln(x2) = slope * (1/T) + intercept for each solute-solvent "
            "pair and append pseudo anchor rows at selected temperatures."
        )
    )
    parser.add_argument("--train-data", required=True, help="Input train CSV.")
    parser.add_argument("--output", required=True, help="Output augmented CSV.")
    parser.add_argument(
        "--summary",
        default=None,
        help="Optional JSON summary path. Defaults to <output>.summary.json.",
    )
    parser.add_argument(
        "--temperatures",
        default="350.0",
        help="Comma-separated pseudo-anchor temperatures in K.",
    )
    parser.add_argument(
        "--min-points",
        type=int,
        default=3,
        help="Minimum real low-temperature points required to fit a pair.",
    )
    parser.add_argument(
        "--min-temp-span",
        type=float,
        default=5.0,
        help="Minimum temperature span in K required to fit a pair.",
    )
    parser.add_argument(
        "--weight",
        type=float,
        default=1.0,
        help="vh_anchor_weight assigned to generated pseudo rows.",
    )
    parser.add_argument(
        "--max-anchors-per-pair",
        type=int,
        default=None,
        help="Optional cap after parsing --temperatures.",
    )
    return parser.parse_args()


def _parse_temperatures(raw: str, max_count: int | None) -> list[float]:
    temps = [float(item.strip()) for item in str(raw).split(",") if item.strip()]
    if not temps:
        raise ValueError("--temperatures must contain at least one value")
    if max_count is not None:
        temps = temps[: max(max_count, 0)]
    return temps


def _fit_pair(group: pd.DataFrame) -> dict[str, float] | None:
    x = 1.0 / group["temperature"].to_numpy(dtype=float)
    y = group["ln_x2"].to_numpy(dtype=float)
    if len(group) < 2:
        return None
    slope, intercept = np.polyfit(x, y, deg=1)
    y_hat = slope * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r2": float(r2),
        "rmse": float(np.sqrt(np.mean((y - y_hat) ** 2))),
    }


def _pair_key_frame(df: pd.DataFrame) -> pd.Series:
    return df["solute_smiles"].astype(str) + ">>" + df["solvent_smiles"].astype(str)


def main() -> None:
    args = parse_args()
    train_path = Path(args.train_data)
    out_path = Path(args.output)
    summary_path = (
        Path(args.summary)
        if args.summary is not None
        else out_path.with_suffix(out_path.suffix + ".summary.json")
    )
    temperatures = _parse_temperatures(args.temperatures, args.max_anchors_per_pair)

    df = pd.read_csv(train_path, low_memory=False)
    required = {"solute_smiles", "solvent_smiles", "temperature", "ln_x2", "has_solubility"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    df = df.copy()
    if "has_vh_anchor" not in df.columns:
        df["has_vh_anchor"] = False
    if "vh_anchor_ln_x2" not in df.columns:
        df["vh_anchor_ln_x2"] = np.nan
    if "vh_anchor_weight" not in df.columns:
        df["vh_anchor_weight"] = 0.0
    for col in (
        "has_vh_fit",
        "vh_fit_slope",
        "vh_fit_intercept",
        "vh_fit_r2",
        "vh_fit_rmse",
        "vh_fit_weight",
    ):
        if col in df.columns:
            df = df.drop(columns=[col])

    supervised = df[df["has_solubility"].astype(bool)].copy()
    anchor_rows: list[dict] = []
    fit_records: list[dict] = []

    for (solute, solvent), group in supervised.groupby(["solute_smiles", "solvent_smiles"]):
        group = group.sort_values("temperature")
        if len(group) < int(args.min_points):
            continue
        temp_span = float(group["temperature"].max() - group["temperature"].min())
        if temp_span < float(args.min_temp_span):
            continue
        fit = _fit_pair(group)
        if fit is None:
            continue
        base = group.iloc[-1].copy()
        fit_records.append({
            "solute_smiles": solute,
            "solvent_smiles": solvent,
            "pair_key": f"{solute}>>{solvent}",
            "n_points": int(len(group)),
            "T_min": float(group["temperature"].min()),
            "T_max": float(group["temperature"].max()),
            "T_span": temp_span,
            **fit,
        })
        for T_anchor in temperatures:
            row = base.copy()
            row["temperature"] = float(T_anchor)
            row["ln_x2"] = float(fit["slope"] * (1.0 / float(T_anchor)) + fit["intercept"])
            row["source"] = "VanHoffAnchor"
            row["has_solubility"] = False
            row["has_T_m"] = False
            row["has_dH_fus"] = False
            row["has_hansen"] = False
            row["has_gamma_inf"] = False
            row["T_m"] = 0.0
            row["dH_fus"] = 0.0
            row["hansen_d"] = 0.0
            row["hansen_p"] = 0.0
            row["hansen_h"] = 0.0
            row["ln_gamma_inf"] = 0.0
            row["has_vh_anchor"] = True
            row["vh_anchor_ln_x2"] = float(row["ln_x2"])
            row["vh_anchor_weight"] = float(args.weight)
            row["vh_anchor_slope"] = float(fit["slope"])
            row["vh_anchor_intercept"] = float(fit["intercept"])
            row["vh_anchor_fit_r2"] = float(fit["r2"])
            row["vh_anchor_fit_rmse"] = float(fit["rmse"])
            row["has_vh_fit"] = True
            row["vh_fit_slope"] = float(fit["slope"])
            row["vh_fit_intercept"] = float(fit["intercept"])
            row["vh_fit_r2"] = float(fit["r2"])
            row["vh_fit_rmse"] = float(fit["rmse"])
            row["vh_fit_weight"] = float(args.weight)
            anchor_rows.append(row.to_dict())

    fits = pd.DataFrame(fit_records)
    df["__pair_key"] = _pair_key_frame(df)
    df["has_vh_fit"] = False
    df["vh_fit_slope"] = np.nan
    df["vh_fit_intercept"] = np.nan
    df["vh_fit_r2"] = np.nan
    df["vh_fit_rmse"] = np.nan
    df["vh_fit_weight"] = 0.0
    if not fits.empty:
        fit_lookup = fits.set_index("pair_key")
        matched = df["__pair_key"].isin(fit_lookup.index)
        df.loc[matched, "has_vh_fit"] = True
        df.loc[matched, "vh_fit_slope"] = df.loc[matched, "__pair_key"].map(fit_lookup["slope"])
        df.loc[matched, "vh_fit_intercept"] = df.loc[matched, "__pair_key"].map(fit_lookup["intercept"])
        df.loc[matched, "vh_fit_r2"] = df.loc[matched, "__pair_key"].map(fit_lookup["r2"])
        df.loc[matched, "vh_fit_rmse"] = df.loc[matched, "__pair_key"].map(fit_lookup["rmse"])
        df.loc[matched, "vh_fit_weight"] = float(args.weight)
    df = df.drop(columns=["__pair_key"])

    anchors = pd.DataFrame(anchor_rows)
    out = pd.concat([df, anchors], ignore_index=True, sort=False) if anchor_rows else df
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    if not fits.empty:
        fits_path = out_path.with_suffix(out_path.suffix + ".fits.csv")
        fits.to_csv(fits_path, index=False)
    else:
        fits_path = None

    summary = {
        "input": str(train_path),
        "output": str(out_path),
        "fit_table": str(fits_path) if fits_path is not None else None,
        "input_rows": int(len(df)),
        "output_rows": int(len(out)),
        "anchor_rows": int(len(anchor_rows)),
        "fit_pairs": int(len(fits)),
        "temperatures": temperatures,
        "min_points": int(args.min_points),
        "min_temp_span": float(args.min_temp_span),
        "weight": float(args.weight),
        "fit_r2_median": float(fits["r2"].median()) if not fits.empty else None,
        "fit_rmse_median": float(fits["rmse"].median()) if not fits.empty else None,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
