#!/usr/bin/env python3
"""Quantify crystal/activity compensation on the crystal-known probe."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from rdkit import Chem

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: F401

R_GAS = 8.31446261815324


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--standard-predictions",
        required=True,
        help="Standard TGNN crystal-known probe prediction CSV.",
    )
    parser.add_argument(
        "--direct-predictions",
        required=True,
        help="Matched DirectGNN crystal-known probe prediction CSV.",
    )
    parser.add_argument(
        "--oracle-train-predictions",
        required=True,
        help="TGNN prediction CSV for train-time oracle injection.",
    )
    parser.add_argument(
        "--forced-oracle-predictions",
        required=True,
        help="TGNN prediction CSV with forced oracle substitution at eval time.",
    )
    parser.add_argument(
        "--oracle-train-forced-predictions",
        required=True,
        help="TGNN prediction CSV with train-time oracle and forced eval oracle.",
    )
    parser.add_argument(
        "--idac-data",
        default=None,
        help="Optional IDAC auxiliary CSV used for overlap checks.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory for the exported CSV/JSON summaries.",
    )
    return parser.parse_args()


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_ready(v) for v in value]
    if isinstance(value, tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def canonical_smiles(smiles: object) -> str:
    if pd.isna(smiles):
        return ""
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return str(smiles)
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


def compute_phi(
    T: pd.Series | np.ndarray,
    Tm: pd.Series | np.ndarray,
    dH_fus: pd.Series | np.ndarray,
    dCp_fus: pd.Series | np.ndarray | None = None,
) -> np.ndarray:
    T_arr = pd.to_numeric(pd.Series(T), errors="coerce").to_numpy(dtype=float)
    Tm_arr = pd.to_numeric(pd.Series(Tm), errors="coerce").to_numpy(dtype=float)
    dH_arr = pd.to_numeric(pd.Series(dH_fus), errors="coerce").to_numpy(dtype=float)
    phi = (dH_arr / R_GAS) * (1.0 / T_arr - 1.0 / Tm_arr)
    if dCp_fus is not None:
        dCp_arr = pd.to_numeric(pd.Series(dCp_fus), errors="coerce").fillna(0.0).to_numpy(dtype=float)
        ratio = Tm_arr / T_arr
        phi = phi - (dCp_arr / R_GAS) * ((ratio - 1.0) - np.log(ratio + 1.0e-10))
    return phi


def regression_metrics(true: np.ndarray, pred: np.ndarray) -> dict[str, float | int | None]:
    true = np.asarray(true, dtype=float)
    pred = np.asarray(pred, dtype=float)
    mask = np.isfinite(true) & np.isfinite(pred)
    true = true[mask]
    pred = pred[mask]
    if true.size == 0:
        return {
            "n_rows": 0,
            "mae": None,
            "rmse": None,
            "r2": None,
            "bias": None,
            "target_std": None,
            "pred_std": None,
            "pred_std_ratio": None,
        }
    err = pred - true
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((true - true.mean()) ** 2))
    true_std = float(np.std(true, ddof=0))
    pred_std = float(np.std(pred, ddof=0))
    return {
        "n_rows": int(true.size),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "r2": None if ss_tot == 0.0 else float(1.0 - ss_res / ss_tot),
        "bias": float(np.mean(err)),
        "target_std": true_std,
        "pred_std": pred_std,
        "pred_std_ratio": None if true_std == 0.0 else float(pred_std / true_std),
    }


def annotate_compensation(df: pd.DataFrame, *, label: str) -> pd.DataFrame:
    work = df.copy()
    required_cols = [
        "ln_x2_true",
        "ln_x2_pred",
        "T",
        "T_m",
        "dH_fus",
        "Phi",
        "ln_gamma_2",
        "solute_smiles",
        "solvent_smiles",
    ]
    missing = [col for col in required_cols if col not in work.columns]
    if missing:
        raise ValueError(f"{label}: missing columns {missing}")

    work["solute_canonical"] = work["solute_smiles"].map(canonical_smiles)
    work["solvent_canonical"] = work["solvent_smiles"].map(canonical_smiles)
    work["pair_canonical"] = work["solute_canonical"] + ">>" + work["solvent_canonical"]
    work["Phi_true"] = compute_phi(work["T"], work["T_m"], work["dH_fus"])
    work["delta_phi"] = pd.to_numeric(work["Phi"], errors="coerce") - work["Phi_true"]
    work["ln_gamma_required"] = -pd.to_numeric(work["ln_x2_true"], errors="coerce") - work["Phi_true"]
    work["delta_gamma"] = pd.to_numeric(work["ln_gamma_2"], errors="coerce") - work["ln_gamma_required"]
    work["compensation_sum"] = work["delta_phi"] + work["delta_gamma"]
    work["compensation_opposite_sign"] = (
        np.sign(work["delta_phi"]).replace(0.0, np.nan)
        * np.sign(work["delta_gamma"]).replace(0.0, np.nan)
        < 0.0
    )
    work["physics_error_from_terms"] = -work["compensation_sum"]
    work["final_error"] = pd.to_numeric(work["ln_x2_pred"], errors="coerce") - pd.to_numeric(
        work["ln_x2_true"], errors="coerce"
    )
    work["abs_compensation_sum"] = work["compensation_sum"].abs()
    work["abs_magnitude_gap"] = (work["delta_phi"].abs() - work["delta_gamma"].abs()).abs()
    work["run_label"] = label
    return work


def safe_corr(x: pd.Series, y: pd.Series) -> float | None:
    x_arr = pd.to_numeric(x, errors="coerce").to_numpy(dtype=float)
    y_arr = pd.to_numeric(y, errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[mask]
    y_arr = y_arr[mask]
    if x_arr.size < 2 or float(np.std(x_arr)) == 0.0 or float(np.std(y_arr)) == 0.0:
        return None
    value = float(np.corrcoef(x_arr, y_arr)[0, 1])
    return value if math.isfinite(value) else None


def compensation_summary(df: pd.DataFrame) -> dict[str, float | int | None]:
    summary = regression_metrics(
        pd.to_numeric(df["ln_x2_true"], errors="coerce").to_numpy(dtype=float),
        pd.to_numeric(df["ln_x2_pred"], errors="coerce").to_numpy(dtype=float),
    )
    summary.update(
        {
            "delta_phi_mean": float(df["delta_phi"].mean()),
            "delta_phi_median": float(df["delta_phi"].median()),
            "delta_phi_std": float(df["delta_phi"].std(ddof=0)),
            "delta_gamma_mean": float(df["delta_gamma"].mean()),
            "delta_gamma_median": float(df["delta_gamma"].median()),
            "delta_gamma_std": float(df["delta_gamma"].std(ddof=0)),
            "delta_phi_delta_gamma_corr": safe_corr(df["delta_phi"], df["delta_gamma"]),
            "opposite_sign_fraction": float(df["compensation_opposite_sign"].mean()),
            "mean_abs_compensation_sum": float(df["abs_compensation_sum"].mean()),
            "median_abs_compensation_sum": float(df["abs_compensation_sum"].median()),
            "mean_abs_magnitude_gap": float(df["abs_magnitude_gap"].mean()),
            "mean_abs_final_minus_physics_error_gap": float(
                (df["final_error"].abs() - df["physics_error_from_terms"].abs()).abs().mean()
            ),
        }
    )
    return summary


def per_solute_summary(df: pd.DataFrame, *, label: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if "solute_name" in df.columns:
        group_cols = ["solute_name", "solute_canonical"]
    else:
        group_cols = ["solute_canonical"]
    for keys, group in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {
            "n_rows": int(len(group)),
            "delta_phi_mean": float(group["delta_phi"].mean()),
            "delta_gamma_mean": float(group["delta_gamma"].mean()),
            "mean_abs_compensation_sum": float(group["abs_compensation_sum"].mean()),
            "run_label": label,
        }
        for col, value in zip(group_cols, keys):
            row[col] = value
        rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["n_rows", "mean_abs_compensation_sum"], ascending=[False, False])
    return out


def overlap_summary(pred: pd.DataFrame, idac: pd.DataFrame | None) -> dict[str, Any]:
    if idac is None:
        return {"idac_available": False}
    test_pairs = set(pred["pair_canonical"])
    test_solutes = set(pred["solute_canonical"])
    test_solvents = set(pred["solvent_canonical"])
    idac_pairs = set(idac["pair_canonical"])
    idac_solutes = set(idac["solute_canonical"])
    idac_solvents = set(idac["solvent_canonical"])
    return {
        "idac_available": True,
        "n_test_rows": int(len(pred)),
        "n_test_pairs": int(len(test_pairs)),
        "n_idac_rows": int(len(idac)),
        "n_idac_pairs": int(len(idac_pairs)),
        "exact_pair_overlap_rows": int(pred["pair_canonical"].isin(idac_pairs).sum()),
        "exact_pair_overlap_pairs": int(len(test_pairs & idac_pairs)),
        "solute_overlap_rows": int(pred["solute_canonical"].isin(idac_solutes).sum()),
        "solvent_overlap_rows": int(pred["solvent_canonical"].isin(idac_solvents).sum()),
        "solute_overlap_unique": int(len(test_solutes & idac_solutes)),
        "solvent_overlap_unique": int(len(test_solvents & idac_solvents)),
    }


def read_prediction_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False).copy()


def main() -> int:
    args = parse_args()
    out_dir = _bootstrap.resolve_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    standard_path = _bootstrap.resolve_path(args.standard_predictions)
    direct_path = _bootstrap.resolve_path(args.direct_predictions)
    oracle_train_path = _bootstrap.resolve_path(args.oracle_train_predictions)
    forced_oracle_path = _bootstrap.resolve_path(args.forced_oracle_predictions)
    oracle_train_forced_path = _bootstrap.resolve_path(args.oracle_train_forced_predictions)
    idac_path = _bootstrap.resolve_path(args.idac_data) if args.idac_data else None

    standard = annotate_compensation(read_prediction_csv(standard_path), label="tgnn_standard")
    oracle_train = annotate_compensation(read_prediction_csv(oracle_train_path), label="tgnn_oracle_train")
    forced_oracle = annotate_compensation(read_prediction_csv(forced_oracle_path), label="tgnn_forced_oracle_eval")
    oracle_train_forced = annotate_compensation(
        read_prediction_csv(oracle_train_forced_path),
        label="tgnn_oracle_train_forced_oracle_eval",
    )
    direct = read_prediction_csv(direct_path)

    idac = None
    if idac_path is not None:
        idac = pd.read_csv(idac_path, low_memory=False).copy()
        idac["solute_canonical"] = idac["solute_smiles"].map(canonical_smiles)
        idac["solvent_canonical"] = idac["solvent_smiles"].map(canonical_smiles)
        idac["pair_canonical"] = idac["solute_canonical"] + ">>" + idac["solvent_canonical"]

    metric_rows = [
        {"run_label": "tgnn_standard", **regression_metrics(standard["ln_x2_true"], standard["ln_x2_pred"])},
        {"run_label": "directgnn", **regression_metrics(direct["ln_x2_true"], direct["ln_x2_pred"])},
        {"run_label": "tgnn_oracle_train", **regression_metrics(oracle_train["ln_x2_true"], oracle_train["ln_x2_pred"])},
        {
            "run_label": "tgnn_forced_oracle_eval",
            **regression_metrics(forced_oracle["ln_x2_true"], forced_oracle["ln_x2_pred"]),
        },
        {
            "run_label": "tgnn_oracle_train_forced_oracle_eval",
            **regression_metrics(oracle_train_forced["ln_x2_true"], oracle_train_forced["ln_x2_pred"]),
        },
    ]
    mode_metrics = pd.DataFrame(metric_rows)

    compensation_rows = [
        {"run_label": "tgnn_standard", **compensation_summary(standard)},
        {"run_label": "tgnn_oracle_train", **compensation_summary(oracle_train)},
        {"run_label": "tgnn_forced_oracle_eval", **compensation_summary(forced_oracle)},
        {
            "run_label": "tgnn_oracle_train_forced_oracle_eval",
            **compensation_summary(oracle_train_forced),
        },
    ]
    compensation_df = pd.DataFrame(compensation_rows)

    per_solute = pd.concat(
        [
            per_solute_summary(standard, label="tgnn_standard"),
            per_solute_summary(oracle_train, label="tgnn_oracle_train"),
        ],
        ignore_index=True,
    )
    if not per_solute.empty:
        per_solute = per_solute.sort_values(
            ["run_label", "n_rows", "mean_abs_compensation_sum"],
            ascending=[True, False, False],
        )

    standard_overlap = overlap_summary(standard, idac)

    standard.to_csv(out_dir / "standard_row_diagnostics.csv", index=False)
    oracle_train.to_csv(out_dir / "oracle_train_row_diagnostics.csv", index=False)
    forced_oracle.to_csv(out_dir / "forced_oracle_row_diagnostics.csv", index=False)
    oracle_train_forced.to_csv(out_dir / "oracle_train_forced_oracle_row_diagnostics.csv", index=False)
    mode_metrics.to_csv(out_dir / "mode_metrics.csv", index=False)
    compensation_df.to_csv(out_dir / "compensation_summary.csv", index=False)
    per_solute.to_csv(out_dir / "per_solute_summary.csv", index=False)

    payload = {
        "inputs": {
            "standard_predictions": standard_path,
            "direct_predictions": direct_path,
            "oracle_train_predictions": oracle_train_path,
            "forced_oracle_predictions": forced_oracle_path,
            "oracle_train_forced_predictions": oracle_train_forced_path,
            "idac_data": idac_path,
        },
        "mode_metrics": mode_metrics.to_dict(orient="records"),
        "compensation_summary": compensation_df.to_dict(orient="records"),
        "idac_overlap_standard": standard_overlap,
    }
    (out_dir / "summary.json").write_text(json.dumps(_json_ready(payload), indent=2), encoding="utf-8")

    summary_md = "\n".join(
        [
            "# Crystal-Known Probe Compensation Diagnostics",
            "",
            "## Mode Metrics",
            mode_metrics.to_csv(index=False),
            "",
            "## Compensation Summary",
            compensation_df.to_csv(index=False),
            "",
            "## IDAC Overlap",
            json.dumps(_json_ready(standard_overlap), indent=2),
            "",
        ]
    )
    (out_dir / "SUMMARY.md").write_text(summary_md + "\n", encoding="utf-8")
    print(json.dumps(_json_ready(payload), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
