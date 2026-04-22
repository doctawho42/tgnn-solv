#!/usr/bin/env python3
"""Replace the crystal term in TGNN row-level outputs with external Tm/dHfus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem

R = 8.31446261815324


def canonical_smiles(smiles: object) -> str:
    if pd.isna(smiles):
        return ""
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return str(smiles)
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


def bool_series(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.fillna(False)
    return s.astype(str).str.lower().isin({"true", "1", "yes", "y", "t"})


def compute_phi(T: pd.Series, Tm: pd.Series, dH: pd.Series, dCp: pd.Series | None) -> pd.Series:
    T_arr = pd.to_numeric(T, errors="coerce").astype(float)
    Tm_arr = pd.to_numeric(Tm, errors="coerce").astype(float)
    dH_arr = pd.to_numeric(dH, errors="coerce").astype(float)
    phi = (dH_arr / R) * (1.0 / T_arr - 1.0 / Tm_arr)
    if dCp is not None:
        dCp_arr = pd.to_numeric(dCp, errors="coerce").fillna(0.0).astype(float)
        ratio = Tm_arr / T_arr
        psi = (ratio - 1.0) - np.log(ratio + 1.0e-10)
        phi = phi - (dCp_arr / R) * psi
    return phi


def metric_block(df: pd.DataFrame, pred_col: str, true_col: str) -> dict[str, float | int | None]:
    mask = np.isfinite(df[pred_col].to_numpy(float)) & np.isfinite(df[true_col].to_numpy(float))
    if not mask.any():
        return {"n": 0, "mae": None, "rmse": None, "r2": None, "bias": None, "pred_std": None}
    y = df.loc[mask, true_col].to_numpy(float)
    p = df.loc[mask, pred_col].to_numpy(float)
    e = p - y
    ss_res = float(np.square(e).sum())
    ss_tot = float(np.square(y - y.mean()).sum())
    return {
        "n": int(mask.sum()),
        "mae": float(np.abs(e).mean()),
        "rmse": float(np.sqrt(np.square(e).mean())),
        "r2": float(1.0 - ss_res / (ss_tot + 1.0e-10)),
        "bias": float(e.mean()),
        "pred_std": float(p.std(ddof=0)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", required=True, help="CSV with TGNN intermediates/predictions.")
    parser.add_argument("--overrides", required=True, help="CSV with external T_m/dH_fus values.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--true-col", default="ln_x2_true")
    parser.add_argument("--temperature-col", default="temperature")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pred = pd.read_csv(args.predictions, low_memory=False)
    overrides = pd.read_csv(args.overrides)
    pred["solute_canonical"] = pred["solute_smiles"].map(canonical_smiles)
    overrides["solute_canonical"] = overrides["solute_smiles"].map(canonical_smiles)
    over_cols = [
        "solute_canonical", "solute_name", "T_m_K", "dH_fus_J_mol",
        "dCp_fus_J_molK", "source_url", "source_note", "confidence",
    ]
    merged = pred.merge(
        overrides[over_cols],
        on="solute_canonical",
        how="left",
        suffixes=("", "_external"),
    )
    matched = merged["T_m_K"].notna() & merged["dH_fus_J_mol"].notna()
    supervised = bool_series(merged.get("has_solubility", pd.Series(True, index=merged.index)))
    true_col = args.true_col if args.true_col in merged.columns else "ln_x2"
    if true_col not in merged.columns:
        raise ValueError("No true ln_x2 column found.")
    temp_col = args.temperature_col if args.temperature_col in merged.columns else "T"
    if temp_col not in merged.columns:
        raise ValueError("No temperature column found.")

    gamma_col = None
    for candidate in ("ln_gamma2_pred", "ln_gamma_2", "ln_gamma_2_corrected", "ln_gamma_inf"):
        if candidate in merged.columns:
            gamma_col = candidate
            break
    if gamma_col is None:
        merged["ln_gamma_for_substitution"] = 0.0
        gamma_col = "ln_gamma_for_substitution"

    original_col = None
    for candidate in ("ln_x2_final", "ln_x2_pred", "ln_x2_physics"):
        if candidate in merged.columns:
            original_col = candidate
            break
    if original_col is None:
        raise ValueError("No original prediction column found.")

    merged["Phi_external"] = np.nan
    merged.loc[matched, "Phi_external"] = compute_phi(
        merged.loc[matched, temp_col],
        merged.loc[matched, "T_m_K"],
        merged.loc[matched, "dH_fus_J_mol"],
        merged.loc[matched, "dCp_fus_J_molK"] if "dCp_fus_J_molK" in merged.columns else None,
    )
    merged["ln_x2_external_ideal"] = -merged["Phi_external"]
    merged["ln_x2_external_crystal_keep_gamma"] = -merged["Phi_external"] - pd.to_numeric(
        merged[gamma_col], errors="coerce"
    )
    if "correction_magnitude" in merged.columns:
        merged["ln_x2_external_crystal_keep_gamma_correction"] = (
            merged["ln_x2_external_crystal_keep_gamma"]
            + pd.to_numeric(merged["correction_magnitude"], errors="coerce").fillna(0.0)
        )
    else:
        merged["ln_x2_external_crystal_keep_gamma_correction"] = merged[
            "ln_x2_external_crystal_keep_gamma"
        ]
    merged["external_delta_vs_original"] = (
        merged["ln_x2_external_crystal_keep_gamma_correction"]
        - pd.to_numeric(merged[original_col], errors="coerce")
    )
    eval_df = merged.loc[matched & supervised].copy()

    summary_rows = []
    for label, col in [
        ("original", original_col),
        ("external_ideal", "ln_x2_external_ideal"),
        ("external_crystal_keep_gamma", "ln_x2_external_crystal_keep_gamma"),
        ("external_crystal_keep_gamma_correction", "ln_x2_external_crystal_keep_gamma_correction"),
    ]:
        block = metric_block(eval_df, col, true_col)
        block["variant"] = label
        block["prediction_col"] = col
        summary_rows.append(block)
    summary = pd.DataFrame(summary_rows)

    by_solute = []
    for solute, g in eval_df.groupby("solute_name_external", dropna=False):
        row = {"solute_name_external": solute, "rows": int(len(g))}
        for label, col in [
            ("original", original_col),
            ("external_keep_gamma_corr", "ln_x2_external_crystal_keep_gamma_correction"),
        ]:
            block = metric_block(g, col, true_col)
            row[f"{label}_mae"] = block["mae"]
            row[f"{label}_bias"] = block["bias"]
            row[f"{label}_r2"] = block["r2"]
        row["T_m_K"] = float(g["T_m_K"].iloc[0])
        row["dH_fus_J_mol"] = float(g["dH_fus_J_mol"].iloc[0])
        row["confidence"] = str(g["confidence"].iloc[0])
        by_solute.append(row)
    by_solute_df = pd.DataFrame(by_solute)
    if "rows" in by_solute_df.columns:
        by_solute_df = by_solute_df.sort_values("rows", ascending=False)

    row_path = out_dir / "external_crystal_substitution_rows.csv"
    summary_path = out_dir / "external_crystal_substitution_summary.csv"
    solute_path = out_dir / "external_crystal_substitution_by_solute.csv"
    json_path = out_dir / "summary.json"
    merged.to_csv(row_path, index=False)
    summary.to_csv(summary_path, index=False)
    by_solute_df.to_csv(solute_path, index=False)
    payload = {
        "predictions": str(Path(args.predictions).resolve()),
        "overrides": str(Path(args.overrides).resolve()),
        "gamma_col": gamma_col,
        "original_col": original_col,
        "true_col": true_col,
        "temperature_col": temp_col,
        "n_rows": int(len(merged)),
        "n_matched_rows": int(matched.sum()),
        "n_eval_rows": int(len(eval_df)),
        "summary": summary.to_dict(orient="records"),
        "by_solute": by_solute_df.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
