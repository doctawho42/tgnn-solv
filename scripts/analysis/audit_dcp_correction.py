#!/usr/bin/env python3
"""Estimate the scale of the omitted SLE dCp correction on processed data."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rdkit import Chem  # noqa: E402
from tgnn_solv.group_contribution import compute_gc_priors  # noqa: E402


R = 8.31446261815324


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate how large the SLE heat-capacity correction would be if "
            "using the maintained Joback/GC dCp_fus prior."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--processed-dir",
        default="notebooks/data/processed",
        help="Directory with train.csv / val.csv / test.csv.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/dcp_correction_audit",
        help="Output directory.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Optional row cap for smoke tests; 0 means all supervised rows.",
    )
    parser.add_argument("--seed", type=int, default=42)
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


def _bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _load_processed(processed_dir: Path) -> pd.DataFrame:
    frames = []
    for split in ["train", "val", "test"]:
        path = processed_dir / f"{split}.csv"
        if not path.is_file():
            continue
        df = pd.read_csv(path, low_memory=False)
        df["split"] = split
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No train/val/test CSVs found in {processed_dir}")
    df = pd.concat(frames, ignore_index=True)
    if "has_solubility" in df.columns:
        df = df.loc[_bool_series(df["has_solubility"])].copy()
    return df.reset_index(drop=True)


def _gc_table(smiles_values: pd.Series) -> pd.DataFrame:
    rows = []
    for smiles in sorted(smiles_values.dropna().astype(str).unique()):
        priors = compute_gc_priors(smiles)
        mol = Chem.MolFromSmiles(smiles)
        n_fragments = 0
        formal_charge = None
        if mol is not None:
            fragments = Chem.GetMolFrags(mol)
            n_fragments = len(fragments)
            formal_charge = int(sum(atom.GetFormalCharge() for atom in mol.GetAtoms()))
        rows.append(
            {
                "solute_smiles": smiles,
                "T_m_gc": priors.get("T_m_gc"),
                "dH_fus_gc": priors.get("dH_fus_gc"),
                "dCp_fus_gc": priors.get("dCp_fus_gc"),
                "gc_has_nonzero_dcp": bool(abs(float(priors.get("dCp_fus_gc") or 0.0)) > 1e-12),
                "gc_n_fragments": n_fragments,
                "gc_formal_charge": formal_charge,
            }
        )
    return pd.DataFrame(rows)


def _summarize(values: pd.Series) -> dict[str, Any]:
    arr = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if arr.size == 0:
        return {"n": 0}
    abs_arr = np.abs(arr)
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "mean_abs": float(np.mean(abs_arr)),
        "median_abs": float(np.median(abs_arr)),
        "p90_abs": float(np.quantile(abs_arr, 0.90)),
        "p95_abs": float(np.quantile(abs_arr, 0.95)),
        "p99_abs": float(np.quantile(abs_arr, 0.99)),
        "max_abs": float(np.max(abs_arr)),
        "frac_abs_gt_0_1": float(np.mean(abs_arr > 0.1)),
        "frac_abs_gt_0_3": float(np.mean(abs_arr > 0.3)),
        "frac_abs_gt_0_5": float(np.mean(abs_arr > 0.5)),
        "frac_abs_gt_0_8": float(np.mean(abs_arr > 0.8)),
    }


def _subset_summaries(work: pd.DataFrame) -> dict[str, Any]:
    has_true_tm = (
        work["T_m_true"].notna()
        & np.isfinite(work["T_m_true"].to_numpy(dtype=float))
        & (work["T_m_true"].to_numpy(dtype=float) > 0)
    )
    single_neutral = (
        (work["gc_n_fragments"].fillna(0).astype(int) == 1)
        & (work["gc_formal_charge"].fillna(999).astype(int) == 0)
    )
    plausible_gc = (
        single_neutral
        & work["T_m_used"].between(250.0, 900.0)
        & work["dCp_used"].between(-50.0, 300.0)
    )
    close_to_melt = plausible_gc & (work["temp_gap_to_tm"] >= 0.0) & (work["temp_gap_to_tm"] <= 250.0)
    return {
        "has_true_Tm": {
            "n_rows": int(has_true_tm.sum()),
            **_summarize(work.loc[has_true_tm, "dcp_phi_correction"]),
        },
        "single_component_neutral": {
            "n_rows": int(single_neutral.sum()),
            **_summarize(work.loc[single_neutral, "dcp_phi_correction"]),
        },
        "plausible_single_component_gc": {
            "n_rows": int(plausible_gc.sum()),
            **_summarize(work.loc[plausible_gc, "dcp_phi_correction"]),
        },
        "plausible_single_component_gc_within_250K_below_Tm": {
            "n_rows": int(close_to_melt.sum()),
            **_summarize(work.loc[close_to_melt, "dcp_phi_correction"]),
        },
    }


def _write_figures(df: pd.DataFrame, out_dir: Path) -> list[str]:
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.hist(np.abs(df["dcp_phi_correction"].to_numpy(dtype=float)), bins=80, color="#0f766e")
    ax.set_xlabel("|Delta Phi from dCp|, ln x2 units")
    ax.set_ylabel("supervised rows")
    ax.set_title("Estimated omitted dCp correction")
    ax.grid(axis="y", color="#d4d4d4", alpha=0.65)
    for suffix in ["png", "pdf"]:
        path = fig_dir / f"dcp_correction_abs_distribution.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        written.append(str(path))
    plt.close(fig)

    if "temp_gap_to_tm" in df.columns:
        fig, ax = plt.subplots(figsize=(6.5, 4.4))
        ax.scatter(
            df["temp_gap_to_tm"],
            np.abs(df["dcp_phi_correction"]),
            s=5,
            alpha=0.20,
            color="#2563eb",
            edgecolors="none",
        )
        ax.set_xlabel("T_m_used - T, K")
        ax.set_ylabel("|Delta Phi from dCp|")
        ax.set_title("dCp correction grows with temperature gap")
        ax.grid(color="#d4d4d4", alpha=0.55)
        for suffix in ["png", "pdf"]:
            path = fig_dir / f"dcp_correction_vs_temp_gap.{suffix}"
            fig.savefig(path, dpi=220, bbox_inches="tight")
            written.append(str(path))
        plt.close(fig)

    return written


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = _load_processed(Path(args.processed_dir))
    if args.max_rows > 0 and len(df) > args.max_rows:
        df = df.sample(n=args.max_rows, random_state=args.seed).reset_index(drop=True)

    gc = _gc_table(df["solute_smiles"])
    work = df.merge(gc, on="solute_smiles", how="left")
    work["T"] = pd.to_numeric(work["temperature"], errors="coerce")
    has_tm = _bool_series(work["has_T_m"]) if "has_T_m" in work.columns else pd.Series(False, index=work.index)
    work["T_m_true"] = pd.to_numeric(work.get("T_m", np.nan), errors="coerce")
    work["T_m_used"] = np.where(
        has_tm & np.isfinite(work["T_m_true"]) & (work["T_m_true"] > 0),
        work["T_m_true"],
        work["T_m_gc"],
    )
    work["dCp_used"] = pd.to_numeric(work["dCp_fus_gc"], errors="coerce").fillna(0.0)
    ratio = work["T_m_used"].to_numpy(dtype=float) / work["T"].to_numpy(dtype=float)
    psi = (ratio - 1.0) - np.log(np.clip(ratio, 1e-12, None))
    work["dcp_phi_correction"] = -(work["dCp_used"].to_numpy(dtype=float) / R) * psi
    work["abs_dcp_phi_correction"] = work["dcp_phi_correction"].abs()
    work["temp_gap_to_tm"] = work["T_m_used"] - work["T"]
    finite_mask = (
        np.isfinite(work["T"].to_numpy(dtype=float))
        & np.isfinite(work["T_m_used"].to_numpy(dtype=float))
        & np.isfinite(work["dcp_phi_correction"].to_numpy(dtype=float))
    )
    work = work.loc[finite_mask].copy()

    by_split = []
    for split, grp in work.groupby("split", sort=False):
        row = {"split": split}
        row.update(_summarize(grp["dcp_phi_correction"]))
        by_split.append(row)
    by_split_df = pd.DataFrame(by_split)
    by_split_df.to_csv(out_dir / "dcp_correction_by_split.csv", index=False)

    bins = [-np.inf, 0, 25, 50, 75, 100, 150, 250, np.inf]
    labels = ["T_above_Tm", "0-25", "25-50", "50-75", "75-100", "100-150", "150-250", "250+"]
    work["temp_gap_bin"] = pd.cut(work["temp_gap_to_tm"], bins=bins, labels=labels)
    bin_rows = []
    for bin_name, grp in work.groupby("temp_gap_bin", observed=False):
        if grp.empty:
            continue
        row = {"temp_gap_bin": str(bin_name)}
        row.update(_summarize(grp["dcp_phi_correction"]))
        bin_rows.append(row)
    pd.DataFrame(bin_rows).to_csv(out_dir / "dcp_correction_by_temp_gap.csv", index=False)

    top_cols = [
        "split",
        "solute_smiles",
        "solvent_smiles",
        "temperature",
        "ln_x2",
        "T_m_true",
        "T_m_gc",
        "T_m_used",
        "dCp_used",
        "dcp_phi_correction",
        "abs_dcp_phi_correction",
        "temp_gap_to_tm",
    ]
    work.sort_values("abs_dcp_phi_correction", ascending=False).head(200)[top_cols].to_csv(
        out_dir / "top_dcp_correction_rows.csv",
        index=False,
    )
    gc.to_csv(out_dir / "solute_gc_dcp_priors.csv", index=False)
    plausible_mask = (
        (work["gc_n_fragments"].fillna(0).astype(int) == 1)
        & (work["gc_formal_charge"].fillna(999).astype(int) == 0)
        & work["T_m_used"].between(250.0, 900.0)
        & work["dCp_used"].between(-50.0, 300.0)
    )
    work.loc[plausible_mask].sort_values(
        "abs_dcp_phi_correction",
        ascending=False,
    ).head(200)[top_cols].to_csv(
        out_dir / "top_dcp_correction_rows_plausible_single_component.csv",
        index=False,
    )

    summary = {
        "processed_dir": str(Path(args.processed_dir)),
        "out_dir": str(out_dir),
        "n_supervised_rows": int(len(work)),
        "n_unique_solutes": int(work["solute_smiles"].nunique()),
        "n_solutes_with_nonzero_gc_dcp": int(gc["gc_has_nonzero_dcp"].sum()),
        "overall": _summarize(work["dcp_phi_correction"]),
        "subsets": _subset_summaries(work),
        "by_split": by_split,
        "figures": _write_figures(work, out_dir),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary), indent=2))


if __name__ == "__main__":
    main()
