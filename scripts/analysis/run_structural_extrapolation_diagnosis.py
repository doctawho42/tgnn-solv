#!/usr/bin/env python3
"""Diagnose structural-extrapolation failure modes from aligned predictions.

This script consumes the prediction-error-slice bundle produced by
``scripts/evaluation/run_prediction_error_slices.py`` and writes a compact
structural-extrapolation diagnosis:

- global model ordering
- row-level and pair-level deltas versus a reference model
- nearest-train-neighbor novelty bins
- target-range bins
- chemistry and solvent-type slices
- top target-model rescues and regressions

It does not retrain models and is intended as a cheap CPU diagnostic before
larger scaffold/solute architecture ablations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--bundle-dir",
        type=Path,
        default=Path("results/prediction_error_slices_latest"),
        help="Prediction-error-slice bundle directory.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/structural_extrapolation_diagnosis"),
        help="Output directory.",
    )
    p.add_argument(
        "--reference-label",
        default="DirectGNN",
        help="Reference model label.",
    )
    p.add_argument(
        "--target-label",
        default="TGNN_MPNN",
        help="Target model label compared against reference.",
    )
    p.add_argument(
        "--other-labels",
        default="RF_hybrid",
        help="Comma-separated optional extra model labels.",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=30,
        help="Number of top rescue/regression rows to write.",
    )
    return p.parse_args()


def _read_model_rows(bundle_dir: Path, label: str) -> pd.DataFrame:
    model_dir = bundle_dir / label
    nn_path = model_dir / "nearest_neighbor_error_rows.csv"
    pred_path = model_dir / "predictions_with_errors.csv"
    path = nn_path if nn_path.exists() else pred_path
    if not path.exists():
        raise FileNotFoundError(f"No predictions found for {label}: {path}")
    df = pd.read_csv(path)
    if "row_index" not in df.columns:
        df = df.reset_index().rename(columns={"index": "row_index"})
    return df


def _mae(x: pd.Series | np.ndarray) -> float:
    arr = np.asarray(x, dtype=float)
    return float(np.nanmean(np.abs(arr))) if arr.size else float("nan")


def _rmse(x: pd.Series | np.ndarray) -> float:
    arr = np.asarray(x, dtype=float)
    return float(np.sqrt(np.nanmean(arr * arr))) if arr.size else float("nan")


def _slice_metrics(
    df: pd.DataFrame,
    group_col: str,
    ref_col: str,
    target_col: str,
    min_n: int = 10,
) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(group_col, dropna=False):
        if len(g) < min_n:
            continue
        rows.append(
            {
                group_col: key,
                "n": int(len(g)),
                "ref_mae": _mae(g[ref_col]),
                "target_mae": _mae(g[target_col]),
                "delta_target_minus_ref": float(
                    np.nanmean(g[target_col] - g[ref_col])
                ),
                "target_better_fraction": float(
                    np.nanmean(g[target_col] < g[ref_col])
                ),
                "ref_p90": float(np.nanquantile(g[ref_col], 0.9)),
                "target_p90": float(np.nanquantile(g[target_col], 0.9)),
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(
            ["delta_target_minus_ref", "n"], ascending=[False, False]
        )
    return out


def _bin_metrics(
    df: pd.DataFrame,
    value_col: str,
    bins: Iterable[float],
    labels: list[str],
    ref_col: str,
    target_col: str,
) -> pd.DataFrame:
    if value_col not in df.columns:
        return pd.DataFrame()
    tmp = df.copy()
    tmp[f"{value_col}_bin"] = pd.cut(
        tmp[value_col], bins=list(bins), labels=labels, include_lowest=True
    )
    return _slice_metrics(
        tmp,
        f"{value_col}_bin",
        ref_col=ref_col,
        target_col=target_col,
        min_n=1,
    )


def _load_solute_features(bundle_dir: Path, label: str) -> pd.DataFrame | None:
    path = bundle_dir / label / "solute_features.csv"
    if not path.exists():
        return None
    cols = [
        "solute_smiles",
        "coarse_class",
        "has_halogen",
        "has_heterocycle",
        "has_nh",
        "has_oh",
        "has_sp",
        "mw",
        "tpsa",
        "n_rings",
        "n_hetero",
    ]
    df = pd.read_csv(path)
    keep = [c for c in cols if c in df.columns]
    return df[keep].drop_duplicates("solute_smiles")


def _aligned_rows(
    bundle_dir: Path,
    reference_label: str,
    target_label: str,
    other_labels: list[str],
) -> pd.DataFrame:
    ref = _read_model_rows(bundle_dir, reference_label)
    target = _read_model_rows(bundle_dir, target_label)

    base_cols = [
        "row_index",
        "solute_smiles",
        "solvent_smiles",
        "temperature",
        "ln_x2_true",
        "pair_key",
        "solvent_type_name",
        "pair_tanimoto",
        "solute_tanimoto",
        "solvent_tanimoto",
        "temperature_delta",
        "abs_neighbor_gap",
        "is_cliff",
    ]
    base_cols = [c for c in base_cols if c in ref.columns]
    aligned = ref[base_cols + ["ln_x2_pred", "signed_error", "abs_error"]].rename(
        columns={
            "ln_x2_pred": f"{reference_label}_pred",
            "signed_error": f"{reference_label}_signed_error",
            "abs_error": f"{reference_label}_abs_error",
        }
    )
    target_keep = ["row_index", "ln_x2_pred", "signed_error", "abs_error"]
    aligned = aligned.merge(
        target[target_keep].rename(
            columns={
                "ln_x2_pred": f"{target_label}_pred",
                "signed_error": f"{target_label}_signed_error",
                "abs_error": f"{target_label}_abs_error",
            }
        ),
        on="row_index",
        how="inner",
    )

    for label in other_labels:
        if not label:
            continue
        other = _read_model_rows(bundle_dir, label)
        aligned = aligned.merge(
            other[target_keep].rename(
                columns={
                    "ln_x2_pred": f"{label}_pred",
                    "signed_error": f"{label}_signed_error",
                    "abs_error": f"{label}_abs_error",
                }
            ),
            on="row_index",
            how="left",
        )

    features = _load_solute_features(bundle_dir, reference_label)
    if features is not None:
        aligned = aligned.merge(features, on="solute_smiles", how="left")

    aligned["target_minus_ref_abs_error"] = (
        aligned[f"{target_label}_abs_error"]
        - aligned[f"{reference_label}_abs_error"]
    )
    aligned["target_better_than_ref"] = (
        aligned[f"{target_label}_abs_error"]
        < aligned[f"{reference_label}_abs_error"]
    )
    return aligned


def _global_summary(
    aligned: pd.DataFrame,
    reference_label: str,
    target_label: str,
    other_labels: list[str],
) -> dict:
    labels = [reference_label, target_label] + [l for l in other_labels if l]
    models = {}
    for label in labels:
        col = f"{label}_abs_error"
        if col not in aligned:
            continue
        signed = f"{label}_signed_error"
        models[label] = {
            "mae": _mae(aligned[col]),
            "rmse_abs_error": _rmse(aligned[col]),
            "median_abs_error": float(np.nanmedian(aligned[col])),
            "p90_abs_error": float(np.nanquantile(aligned[col], 0.9)),
            "bias": float(np.nanmean(aligned[signed])) if signed in aligned else None,
            "overprediction_fraction": (
                float(np.nanmean(aligned[signed] > 0)) if signed in aligned else None
            ),
        }
    ref_col = f"{reference_label}_abs_error"
    target_col = f"{target_label}_abs_error"
    return {
        "n_rows": int(len(aligned)),
        "models": models,
        "target_vs_reference": {
            "reference": reference_label,
            "target": target_label,
            "mean_abs_error_delta": float(np.nanmean(aligned[target_col] - aligned[ref_col])),
            "median_abs_error_delta": float(np.nanmedian(aligned[target_col] - aligned[ref_col])),
            "target_better_fraction": float(np.nanmean(aligned[target_col] < aligned[ref_col])),
            "target_worse_fraction": float(np.nanmean(aligned[target_col] > aligned[ref_col])),
            "both_bad_abs_error_gt_3_fraction": float(
                np.nanmean((aligned[target_col] > 3.0) & (aligned[ref_col] > 3.0))
            ),
            "target_rescue_fraction_ref_gt_3_target_lt_1": float(
                np.nanmean((aligned[ref_col] > 3.0) & (aligned[target_col] < 1.0))
            ),
            "target_regression_fraction_ref_lt_1_target_gt_3": float(
                np.nanmean((aligned[ref_col] < 1.0) & (aligned[target_col] > 3.0))
            ),
        },
    }


def _write_markdown(
    out: Path,
    summary: dict,
    tables: dict[str, pd.DataFrame],
    reference_label: str,
    target_label: str,
) -> None:
    tvs = summary["target_vs_reference"]
    models = summary["models"]

    def table_head(df: pd.DataFrame, n: int = 8) -> str:
        if df.empty:
            return "_No rows._\n"
        return df.head(n).to_markdown(index=False)

    lines = [
        "# Structural Extrapolation Diagnosis",
        "",
        "Date: 2026-04-18",
        "",
        f"Reference: `{reference_label}`. Target: `{target_label}`.",
        "",
        "This is a prediction-only scaffold diagnostic. It uses aligned existing",
        "prediction CSVs and does not retrain any model.",
        "",
        "## Global Metrics",
        "",
        "| Model | MAE | Median AE | P90 AE | Bias | Overprediction fraction |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label, m in models.items():
        bias = m["bias"]
        over = m["overprediction_fraction"]
        lines.append(
            f"| {label} | {m['mae']:.3f} | {m['median_abs_error']:.3f} | "
            f"{m['p90_abs_error']:.3f} | {bias:.3f} | {over:.3f} |"
        )

    lines += [
        "",
        "## Target vs Reference",
        "",
        f"- Mean abs-error delta (`{target_label}` - `{reference_label}`): "
        f"`{tvs['mean_abs_error_delta']:.3f}`",
        f"- Median abs-error delta: `{tvs['median_abs_error_delta']:.3f}`",
        f"- `{target_label}` better row fraction: `{tvs['target_better_fraction']:.3f}`",
        f"- Both bad (`AE > 3` for both) row fraction: "
        f"`{tvs['both_bad_abs_error_gt_3_fraction']:.3f}`",
        f"- `{target_label}` rescue fraction (`{reference_label} AE > 3`, "
        f"`{target_label} AE < 1`): `{tvs['target_rescue_fraction_ref_gt_3_target_lt_1']:.3f}`",
        f"- `{target_label}` regression fraction (`{reference_label} AE < 1`, "
        f"`{target_label} AE > 3`): `{tvs['target_regression_fraction_ref_lt_1_target_gt_3']:.3f}`",
        "",
        "## Novelty Bins",
        "",
        table_head(tables["pair_tanimoto_bins"]),
        "",
        "## Target-Value Bins",
        "",
        table_head(tables["ln_x2_bins"]),
        "",
        "## Chemistry Classes",
        "",
        table_head(tables["coarse_class"]),
        "",
        "## Solvent Types",
        "",
        table_head(tables["solvent_type_name"]),
        "",
        "## Interpretation",
        "",
        "- Structural extrapolation remains a shared failure mode, not a TGNN-only failure.",
        "- The target model wins on a large minority of rows, so errors are correlated but not identical.",
        "- Slices with positive `delta_target_minus_ref` are where the physics path currently adds cost.",
        "- Slices with negative `delta_target_minus_ref` are candidates for physics-aware ensembling or targeted architecture work.",
        "",
        "## Output Files",
        "",
        "- `aligned_row_deltas.csv`",
        "- `pair_level_deltas.csv`",
        "- `novelty_bins_pair_tanimoto.csv`",
        "- `target_value_bins.csv`",
        "- `chemistry_class_deltas.csv`",
        "- `solvent_type_deltas.csv`",
        "- `top_target_rescues.csv`",
        "- `top_target_regressions.csv`",
        "- `summary.json`",
    ]
    out.write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    other_labels = [x.strip() for x in args.other_labels.split(",") if x.strip()]
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    aligned = _aligned_rows(
        args.bundle_dir,
        args.reference_label,
        args.target_label,
        other_labels,
    )
    ref_col = f"{args.reference_label}_abs_error"
    target_col = f"{args.target_label}_abs_error"

    aligned.to_csv(out_dir / "aligned_row_deltas.csv", index=False)

    pair_rows = []
    for pair_key, g in aligned.groupby("pair_key"):
        pair_rows.append(
            {
                "pair_key": pair_key,
                "n": int(len(g)),
                "solute_smiles": g["solute_smiles"].iloc[0],
                "solvent_smiles": g["solvent_smiles"].iloc[0],
                "solvent_type_name": g.get("solvent_type_name", pd.Series([""])).iloc[0],
                "coarse_class": g.get("coarse_class", pd.Series([""])).iloc[0],
                "pair_tanimoto_mean": float(np.nanmean(g.get("pair_tanimoto", np.nan))),
                "ref_pair_mae": _mae(g[ref_col]),
                "target_pair_mae": _mae(g[target_col]),
                "delta_target_minus_ref": float(np.nanmean(g[target_col] - g[ref_col])),
                "target_better_fraction": float(np.nanmean(g[target_col] < g[ref_col])),
            }
        )
    pair_df = pd.DataFrame(pair_rows).sort_values(
        "delta_target_minus_ref", ascending=False
    )
    pair_df.to_csv(out_dir / "pair_level_deltas.csv", index=False)

    tables = {
        "pair_tanimoto_bins": _bin_metrics(
            aligned,
            "pair_tanimoto",
            bins=[-0.001, 0.3, 0.4, 0.5, 0.6, 0.8, 1.001],
            labels=["<=0.3", "0.3-0.4", "0.4-0.5", "0.5-0.6", "0.6-0.8", ">0.8"],
            ref_col=ref_col,
            target_col=target_col,
        ),
        "ln_x2_bins": _bin_metrics(
            aligned,
            "ln_x2_true",
            bins=[-np.inf, -15, -10, -7, -5, -3, 0.001],
            labels=["<=-15", "-15..-10", "-10..-7", "-7..-5", "-5..-3", ">-3"],
            ref_col=ref_col,
            target_col=target_col,
        ),
        "coarse_class": _slice_metrics(
            aligned, "coarse_class", ref_col=ref_col, target_col=target_col
        )
        if "coarse_class" in aligned
        else pd.DataFrame(),
        "solvent_type_name": _slice_metrics(
            aligned, "solvent_type_name", ref_col=ref_col, target_col=target_col
        )
        if "solvent_type_name" in aligned
        else pd.DataFrame(),
    }

    tables["pair_tanimoto_bins"].to_csv(
        out_dir / "novelty_bins_pair_tanimoto.csv", index=False
    )
    tables["ln_x2_bins"].to_csv(out_dir / "target_value_bins.csv", index=False)
    tables["coarse_class"].to_csv(out_dir / "chemistry_class_deltas.csv", index=False)
    tables["solvent_type_name"].to_csv(out_dir / "solvent_type_deltas.csv", index=False)

    rescues = aligned.sort_values("target_minus_ref_abs_error", ascending=True).head(
        args.top_k
    )
    regressions = aligned.sort_values("target_minus_ref_abs_error", ascending=False).head(
        args.top_k
    )
    rescues.to_csv(out_dir / "top_target_rescues.csv", index=False)
    regressions.to_csv(out_dir / "top_target_regressions.csv", index=False)

    summary = _global_summary(
        aligned, args.reference_label, args.target_label, other_labels
    )
    summary.update(
        {
            "bundle_dir": str(args.bundle_dir),
            "output_dir": str(out_dir),
            "n_pairs": int(pair_df["pair_key"].nunique()),
            "pair_level": {
                "target_better_pair_fraction": float(
                    np.nanmean(pair_df["target_pair_mae"] < pair_df["ref_pair_mae"])
                ),
                "mean_pair_mae_delta": float(
                    np.nanmean(pair_df["target_pair_mae"] - pair_df["ref_pair_mae"])
                ),
                "catastrophic_pair_fraction_ref_gt_3": float(
                    np.nanmean(pair_df["ref_pair_mae"] > 3.0)
                ),
                "catastrophic_pair_fraction_target_gt_3": float(
                    np.nanmean(pair_df["target_pair_mae"] > 3.0)
                ),
            },
        }
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    _write_markdown(
        out_dir / "SUMMARY.md",
        summary,
        tables,
        reference_label=args.reference_label,
        target_label=args.target_label,
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
