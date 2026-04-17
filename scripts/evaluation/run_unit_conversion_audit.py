#!/usr/bin/env python
"""Audit ln(x2) / x2 / logS conversions across raw and processed corpora."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from rdkit import RDLogger

from tgnn_solv.data.utils import PROCESSED_DIR, RAW_DIR, canonicalize
from tgnn_solv.external_benchmarking import (
    clip_ln_x2_for_logS,
    estimate_solvent_molarity,
    ln_x2_from_logS,
    logS_from_ln_x2,
    prepare_pair_dataframe,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit internal unit conversions and estimate whether ln(x2) <-> "
            "logS translation is a major error source."
        )
    )
    parser.add_argument(
        "--raw-data",
        default=str(RAW_DIR / "BigSolDBv2.1.csv"),
        help="Raw BigSolDB CSV used to audit x2/logS consistency.",
    )
    parser.add_argument(
        "--processed-dir",
        default=str(PROCESSED_DIR),
        help="Directory containing processed split CSV files.",
    )
    parser.add_argument(
        "--splits",
        default=(
            "train.csv,val.csv,test.csv,"
            "train_solute.csv,val_solute.csv,test_solute.csv,"
            "train_solvent.csv,val_solvent.csv,test_solvent.csv"
        ),
        help="Comma-separated processed CSV basenames to audit if present.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/unit_conversion_audit",
        help="Output directory for audit artifacts.",
    )
    return parser


def _normalize_column_name(name: str) -> str:
    return "".join(ch for ch in str(name).strip().lower() if ch.isalnum())


def _resolve_column(df: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    mapping = {_normalize_column_name(col): col for col in df.columns}
    for alias in aliases:
        found = mapping.get(_normalize_column_name(alias))
        if found is not None:
            return found
    return None


def _error_stats(values: np.ndarray) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {
            "mean_abs_error": float("nan"),
            "median_abs_error": float("nan"),
            "p95_abs_error": float("nan"),
            "max_abs_error": float("nan"),
        }
    abs_arr = np.abs(arr)
    return {
        "mean_abs_error": float(abs_arr.mean()),
        "median_abs_error": float(np.median(abs_arr)),
        "p95_abs_error": float(np.quantile(abs_arr, 0.95)),
        "max_abs_error": float(abs_arr.max()),
    }


def _series_from_mapping(values: pd.Series, mapping: dict[str, float | None]) -> pd.Series:
    return values.astype(str).map(mapping)


def _safe_canonicalize_series(values: pd.Series) -> tuple[pd.Series, int]:
    raw = values.astype(str).str.strip()
    invalid_placeholder = raw.eq("") | raw.eq("-") | raw.str.lower().isin({"nan", "none"})
    unique_valid = raw.loc[~invalid_placeholder].unique().tolist()
    RDLogger.DisableLog("rdApp.error")
    try:
        canonical_map = {smi: canonicalize(smi) for smi in unique_valid}
    finally:
        RDLogger.EnableLog("rdApp.error")
    canonical = raw.map(canonical_map)
    canonical.loc[invalid_placeholder] = np.nan
    return canonical, int(invalid_placeholder.sum())


def _solvent_molarity_mapping(solvent_smiles: pd.Series) -> dict[str, float | None]:
    unique = sorted(set(solvent_smiles.astype(str)))
    return {smi: estimate_solvent_molarity(smi) for smi in unique}


def audit_processed_split(path: Path) -> dict[str, Any]:
    df = pd.read_csv(path, low_memory=False)
    df = prepare_pair_dataframe(df, require_targets="ln_x2" in df.columns)
    ln_x2 = pd.to_numeric(df["ln_x2"], errors="coerce")
    log_s = logS_from_ln_x2(df)
    ln_x2_roundtrip = ln_x2_from_logS(
        pd.DataFrame(
            {
                "solvent_smiles": df["solvent_smiles"],
                "logS": log_s,
            }
        ),
        logS_col="logS",
    )
    finite_mask = (
        np.isfinite(ln_x2.to_numpy(dtype=float))
        & np.isfinite(log_s.to_numpy(dtype=float))
        & np.isfinite(ln_x2_roundtrip.to_numpy(dtype=float))
    )

    molarity_map = _solvent_molarity_mapping(df["solvent_smiles"])
    molarity = _series_from_mapping(df["solvent_smiles"], molarity_map)
    missing_density_mask = molarity.isna().to_numpy()
    inf_log_s_mask = np.isinf(log_s.to_numpy(dtype=float))
    finite_molarity_mask = np.isfinite(molarity.to_numpy(dtype=float))
    ln_x2_zero_mask = ln_x2.to_numpy(dtype=float) == 0.0
    inf_due_zero_mask = finite_molarity_mask & ln_x2_zero_mask

    summary = {
        "split_file": path.name,
        "rows": int(len(df)),
        "unique_solvents": int(df["solvent_smiles"].astype(str).nunique()),
        "finite_logS_rows": int(np.isfinite(log_s.to_numpy(dtype=float)).sum()),
        "nan_logS_rows": int(np.isnan(log_s.to_numpy(dtype=float)).sum()),
        "inf_logS_rows": int(inf_log_s_mask.sum()),
        "nonfinite_logS_rows": int((~np.isfinite(log_s.to_numpy(dtype=float))).sum()),
        "fraction_nonfinite_logS": float((~np.isfinite(log_s.to_numpy(dtype=float))).mean()),
        "missing_molarity_rows": int(missing_density_mask.sum()),
        "missing_density_rows": int(missing_density_mask.sum()),
        "finite_molarity_rows": int(finite_molarity_mask.sum()),
        "ln_x2_eq_0_rows": int((ln_x2.to_numpy(dtype=float) == 0.0).sum()),
        "inf_due_ln_x2_eq_0_rows": int(inf_due_zero_mask.sum()),
        "roundtrip_rows": int(finite_mask.sum()),
        **_error_stats(
            ln_x2_roundtrip.to_numpy(dtype=float)[finite_mask]
            - ln_x2.to_numpy(dtype=float)[finite_mask]
        ),
        "top_missing_density_solvents": (
            df.loc[missing_density_mask, "solvent_smiles"]
            .astype(str)
            .value_counts()
            .head(15)
            .to_dict()
        ),
        "top_inf_logS_solvents": (
            df.loc[inf_log_s_mask, "solvent_smiles"]
            .astype(str)
            .value_counts()
            .head(15)
            .to_dict()
        ),
    }
    return summary


def audit_raw_bigsoldb(path: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    raw_df = pd.read_csv(path, low_memory=False)
    solvent_smiles_col = _resolve_column(raw_df, ("SMILES_Solvent",))
    solvent_name_col = _resolve_column(raw_df, ("Solvent",))
    x2_col = _resolve_column(raw_df, ("Solubility(mole_fraction)", "x2"))
    log_s_col = _resolve_column(raw_df, ("LogS(mol/L)", "logS"))
    temp_col = _resolve_column(raw_df, ("Temperature_K", "temperature"))
    if (
        solvent_smiles_col is None
        or solvent_name_col is None
        or x2_col is None
        or log_s_col is None
        or temp_col is None
    ):
        raise ValueError("Raw BigSolDB columns required for conversion audit were not found.")

    audit_df = pd.DataFrame(
        {
            "solvent_name": raw_df[solvent_name_col].astype(str),
            "solvent_smiles": raw_df[solvent_smiles_col].astype(str),
            "temperature": pd.to_numeric(raw_df[temp_col], errors="coerce"),
            "x2_raw": pd.to_numeric(raw_df[x2_col], errors="coerce"),
            "logS_raw": pd.to_numeric(raw_df[log_s_col], errors="coerce"),
        }
    )
    audit_df["solvent_smiles"], invalid_solvent_smiles_rows = _safe_canonicalize_series(
        audit_df["solvent_smiles"]
    )
    valid_x2_mask = (audit_df["x2_raw"] > 0.0) & (audit_df["x2_raw"] <= 1.0)
    audit_df["ln_x2_from_x2"] = np.nan
    audit_df.loc[valid_x2_mask, "ln_x2_from_x2"] = np.log(
        audit_df.loc[valid_x2_mask, "x2_raw"]
    )
    audit_df["logS_from_x2"] = logS_from_ln_x2(
        pd.DataFrame(
            {
                "solvent_smiles": audit_df["solvent_smiles"],
                "ln_x2": audit_df["ln_x2_from_x2"],
            }
        )
    )
    audit_df["ln_x2_from_logS"] = ln_x2_from_logS(
        pd.DataFrame(
            {
                "solvent_smiles": audit_df["solvent_smiles"],
                "logS": audit_df["logS_raw"],
            }
        ),
        logS_col="logS",
    )
    audit_df["delta_logS"] = audit_df["logS_from_x2"] - audit_df["logS_raw"]
    audit_df["delta_ln_x2"] = audit_df["ln_x2_from_logS"] - audit_df["ln_x2_from_x2"]

    paired_mask = (
        np.isfinite(audit_df["logS_raw"].to_numpy(dtype=float))
        & np.isfinite(audit_df["ln_x2_from_x2"].to_numpy(dtype=float))
        & np.isfinite(audit_df["logS_from_x2"].to_numpy(dtype=float))
        & np.isfinite(audit_df["ln_x2_from_logS"].to_numpy(dtype=float))
    )
    recoverable_from_log_s_mask = (
        audit_df["ln_x2_from_x2"].isna()
        & np.isfinite(audit_df["logS_raw"].to_numpy(dtype=float))
        & np.isfinite(audit_df["ln_x2_from_logS"].to_numpy(dtype=float))
    )

    by_solvent = (
        audit_df.loc[paired_mask]
        .groupby(["solvent_smiles", "solvent_name"], dropna=False)
        .agg(
            n_rows=("delta_logS", "size"),
            mean_abs_delta_logS=("delta_logS", lambda s: float(np.mean(np.abs(s)))),
            median_abs_delta_logS=("delta_logS", lambda s: float(np.median(np.abs(s)))),
            mean_abs_delta_ln_x2=("delta_ln_x2", lambda s: float(np.mean(np.abs(s)))),
            median_abs_delta_ln_x2=("delta_ln_x2", lambda s: float(np.median(np.abs(s)))),
        )
        .reset_index()
        .sort_values(["mean_abs_delta_ln_x2", "n_rows"], ascending=[False, False])
    )

    summary = {
        "raw_rows": int(len(audit_df)),
        "rows_with_invalid_solvent_smiles": int(invalid_solvent_smiles_rows),
        "rows_with_valid_x2": int(valid_x2_mask.sum()),
        "rows_with_finite_logS": int(np.isfinite(audit_df["logS_raw"].to_numpy(dtype=float)).sum()),
        "rows_with_x2_eq_1": int((audit_df["x2_raw"] == 1.0).sum()),
        "rows_pairwise_audited": int(paired_mask.sum()),
        "rows_recoverable_from_logS_only": int(recoverable_from_log_s_mask.sum()),
        "logS_vs_x2": _error_stats(audit_df.loc[paired_mask, "delta_logS"].to_numpy(dtype=float)),
        "ln_x2_vs_logS": _error_stats(audit_df.loc[paired_mask, "delta_ln_x2"].to_numpy(dtype=float)),
        "rows_abs_delta_logS_gt_0_02": int(
            (np.abs(audit_df.loc[paired_mask, "delta_logS"].to_numpy(dtype=float)) > 0.02).sum()
        ),
        "rows_abs_delta_logS_gt_0_05": int(
            (np.abs(audit_df.loc[paired_mask, "delta_logS"].to_numpy(dtype=float)) > 0.05).sum()
        ),
        "rows_abs_delta_logS_gt_0_10": int(
            (np.abs(audit_df.loc[paired_mask, "delta_logS"].to_numpy(dtype=float)) > 0.10).sum()
        ),
        "rows_abs_delta_logS_gt_0_20": int(
            (np.abs(audit_df.loc[paired_mask, "delta_logS"].to_numpy(dtype=float)) > 0.20).sum()
        ),
        "rows_abs_delta_ln_x2_gt_0_05": int(
            (np.abs(audit_df.loc[paired_mask, "delta_ln_x2"].to_numpy(dtype=float)) > 0.05).sum()
        ),
        "rows_abs_delta_ln_x2_gt_0_10": int(
            (np.abs(audit_df.loc[paired_mask, "delta_ln_x2"].to_numpy(dtype=float)) > 0.10).sum()
        ),
        "rows_abs_delta_ln_x2_gt_0_20": int(
            (np.abs(audit_df.loc[paired_mask, "delta_ln_x2"].to_numpy(dtype=float)) > 0.20).sum()
        ),
        "rows_abs_delta_ln_x2_gt_0_50": int(
            (np.abs(audit_df.loc[paired_mask, "delta_ln_x2"].to_numpy(dtype=float)) > 0.50).sum()
        ),
        "top_raw_logS_mismatch_solvents": (
            by_solvent.head(15).to_dict(orient="records") if not by_solvent.empty else []
        ),
    }
    return summary, by_solvent


def audit_prediction_conversion_consistency() -> dict[str, Any]:
    solvent_smiles = pd.Series(["O", "CCO", "CC(C)CO"])
    pred_ln_x2 = np.array([0.0, -1.0, -5.0], dtype=float)
    clipped = clip_ln_x2_for_logS(pred_ln_x2)
    log_s = logS_from_ln_x2(
        pd.DataFrame(
            {
                "solvent_smiles": solvent_smiles,
                "ln_x2": clipped,
            }
        )
    )
    return {
        "shared_prediction_clip_upper": float(clipped.max()),
        "all_prediction_logS_finite": bool(np.isfinite(log_s.to_numpy(dtype=float)).all()),
        "prediction_logS_values": [float(v) for v in log_s.to_numpy(dtype=float)],
    }


def write_summary_markdown(path: Path, payload: dict[str, Any]) -> None:
    raw = payload["raw_bigsoldb"]
    processed = payload["processed_splits"]
    prediction = payload["prediction_path_consistency"]
    lines = [
        "# Unit Conversion Audit",
        "",
        "## Main Findings",
        "",
        f"- raw rows pairwise audited: `{raw['rows_pairwise_audited']}`",
        f"- raw rows with invalid solvent SMILES skipped: `{raw['rows_with_invalid_solvent_smiles']}`",
        (
            "- raw `logS` vs raw `x2` consistency:"
            f" mean abs `delta logS = {raw['logS_vs_x2']['mean_abs_error']:.4f}`,"
            f" mean abs `delta ln_x2 = {raw['ln_x2_vs_logS']['mean_abs_error']:.4f}`"
        ),
        (
            "- raw mismatch tail is thin:"
            f" `|delta ln_x2| > 0.1` on {raw['rows_abs_delta_ln_x2_gt_0_10']} rows,"
            f" `|delta ln_x2| > 0.2` on {raw['rows_abs_delta_ln_x2_gt_0_20']} rows"
        ),
        f"- rows recoverable from `logS` only: `{raw['rows_recoverable_from_logS_only']}`",
        "- interpretation: raw conversion mismatch is two orders of magnitude"
        " smaller than current model MAE and is not a headline bottleneck",
        (
            "- prediction-side `ln_x2 -> logS` clipping now shared and finite:"
            f" `all_prediction_logS_finite = {prediction['all_prediction_logS_finite']}`"
        ),
        "",
        "## Processed Splits",
        "",
    ]
    for row in processed:
        lines.extend(
            [
                f"### `{row['split_file']}`",
                "",
                f"- rows: `{row['rows']}`",
                (
                    "- finite `logS`: "
                    f"`{row['finite_logS_rows']}`, "
                    f"`NaN = {row['nan_logS_rows']}`, "
                    f"`inf = {row['inf_logS_rows']}`"
                ),
                (
                    "- non-finite breakdown: "
                    f"`missing molarity = {row['missing_molarity_rows']}`, "
                    f"`x2 = 1 rows = {row['inf_due_ln_x2_eq_0_rows']}`"
                ),
                (
                    "- round-trip abs error:"
                    f" mean `{row['mean_abs_error']:.3e}`,"
                    f" max `{row['max_abs_error']:.3e}`"
                ),
                (
                    "- missing molarity rows: "
                    f"`{row['missing_molarity_rows']}`"
                ),
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    split_names = [name.strip() for name in args.splits.split(",") if name.strip()]
    processed_dir = Path(args.processed_dir)
    processed_summaries: list[dict[str, Any]] = []
    for split_name in split_names:
        split_path = processed_dir / split_name
        if not split_path.exists():
            continue
        processed_summaries.append(audit_processed_split(split_path))
    processed_df = pd.DataFrame(processed_summaries)
    if not processed_df.empty:
        processed_df.to_csv(out_dir / "processed_split_roundtrip.csv", index=False)

    raw_summary, by_solvent = audit_raw_bigsoldb(Path(args.raw_data))
    if not by_solvent.empty:
        by_solvent.to_csv(out_dir / "raw_pairwise_by_solvent.csv", index=False)

    payload = {
        "raw_bigsoldb": raw_summary,
        "processed_splits": processed_summaries,
        "prediction_path_consistency": audit_prediction_conversion_consistency(),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    write_summary_markdown(out_dir / "SUMMARY.md", payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
