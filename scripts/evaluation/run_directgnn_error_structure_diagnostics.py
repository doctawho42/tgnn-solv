#!/usr/bin/env python3
"""Diagnose where the maintained DirectGNN scaffold model makes errors."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: E402,F401

from rdkit import Chem  # noqa: E402
from rdkit.Chem import Descriptors, rdMolDescriptors  # noqa: E402

from run_full_budget_experiment import (  # noqa: E402
    build_loader,
    load_direct_checkpoint,
    pearson_corr,
    regression_metrics,
    resolve_device,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run structural error diagnostics for the maintained DirectGNN "
            "checkpoint on the scaffold split."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--checkpoint",
        default="checkpoints/proxy/directgnn_tuned.pt",
    )
    parser.add_argument(
        "--train-data",
        default="notebooks/data/processed/train.csv",
    )
    parser.add_argument(
        "--val-data",
        default="notebooks/data/processed/val.csv",
    )
    parser.add_argument(
        "--test-data",
        default="notebooks/data/processed/test.csv",
    )
    parser.add_argument(
        "--test-predictions",
        default="results/tail_diagnostics_fast_v2/directgnn_scaffold_predictions.csv",
        help="Optional existing test-prediction CSV to reuse instead of recomputing test predictions.",
    )
    parser.add_argument(
        "--nearest-neighbors-csv",
        default="results/knn_modelability_smoke/nearest_neighbors.csv",
        help="Optional nearest-neighbor diagnostics CSV from run_knn_modelability.py.",
    )
    parser.add_argument(
        "--out-dir",
        default="results/directgnn_error_structure",
    )
    parser.add_argument(
        "--device",
        default="mps",
    )
    parser.add_argument(
        "--eval-batch-size",
        type=int,
        default=512,
        help="Batch size used for fresh checkpoint evaluation on train/val/test.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    return parser.parse_args()


def _safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


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


def _rank_corr(x: np.ndarray, y: np.ndarray) -> float | None:
    if x.size < 2 or y.size < 2:
        return None
    x_rank = pd.Series(x).rank(method="average").to_numpy(dtype=float)
    y_rank = pd.Series(y).rank(method="average").to_numpy(dtype=float)
    return pearson_corr(x_rank, y_rank)


@torch.no_grad()
def collect_direct_predictions(
    model: torch.nn.Module,
    loader: torch.utils.data.DataLoader,
    device: torch.device,
) -> pd.DataFrame:
    """Collect DirectGNN predictions in dataset order."""
    model.eval()
    dataset_df = loader.dataset.df.reset_index(drop=True).copy()
    rows: list[pd.DataFrame] = []
    cursor = 0

    for sol_b, slv_b, tgt in loader:
        sol_b = sol_b.to(device)
        slv_b = slv_b.to(device)
        T = tgt["T"].to(device)
        solvent_type = tgt.get("solvent_type")
        solute_morgan_fp = tgt.get("solute_morgan_fp")
        solvent_morgan_fp = tgt.get("solvent_morgan_fp")
        solute_descriptors = tgt.get("solute_descriptors")
        solvent_descriptors = tgt.get("solvent_descriptors")
        mask = tgt["has_solubility"]

        batch_size = int(T.shape[0])
        batch_df = dataset_df.iloc[cursor:cursor + batch_size].copy().reset_index(drop=True)
        batch_df["row_index"] = np.arange(cursor, cursor + batch_size, dtype=int)
        cursor += batch_size

        if not mask.any():
            continue

        out = model(
            sol_b,
            slv_b,
            T,
            solvent_type=solvent_type,
            solute_morgan_fp=(
                solute_morgan_fp.to(device)
                if isinstance(solute_morgan_fp, torch.Tensor)
                else None
            ),
            solvent_morgan_fp=(
                solvent_morgan_fp.to(device)
                if isinstance(solvent_morgan_fp, torch.Tensor)
                else None
            ),
            solute_descriptors=(
                solute_descriptors.to(device)
                if isinstance(solute_descriptors, torch.Tensor)
                else None
            ),
            solvent_descriptors=(
                solvent_descriptors.to(device)
                if isinstance(solvent_descriptors, torch.Tensor)
                else None
            ),
        )
        mask_np = mask.cpu().numpy().astype(bool, copy=False)
        batch_df = batch_df.loc[mask_np].copy().reset_index(drop=True)
        batch_df["ln_x2_true"] = batch_df["ln_x2"].astype(float)
        batch_df["ln_x2_pred"] = out["ln_x2"].detach().cpu().numpy()[mask_np]
        rows.append(batch_df)

    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out["abs_error"] = np.abs(
        out["ln_x2_pred"].to_numpy(dtype=float)
        - out["ln_x2_true"].to_numpy(dtype=float)
    )
    out["signed_error"] = (
        out["ln_x2_pred"].to_numpy(dtype=float)
        - out["ln_x2_true"].to_numpy(dtype=float)
    )
    return out


def _coarse_solute_class(features: dict[str, Any]) -> str:
    if features["invalid"]:
        return "invalid"
    if features["has_halogen"] and features["n_aromatic"] >= 1:
        return "halogenated_aromatic"
    if features["has_heterocycle"]:
        return "heterocycle"
    if features["has_sp"]:
        return "sulfur_or_phosphorus"
    if features["has_oh"]:
        return "oxygenated"
    if features["has_nh"]:
        return "nitrogenated"
    if features["n_aromatic"] >= 2:
        return "polyaromatic"
    if features["n_hetero"] == 0 and features["n_rings"] == 0:
        return "hydrocarbon_like"
    return "other"


def describe_solute(smiles: str) -> dict[str, Any]:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return {
            "solute_smiles": str(smiles),
            "invalid": True,
            "has_oh": False,
            "has_nh": False,
            "has_halogen": False,
            "has_sp": False,
            "has_heterocycle": False,
            "n_rings": 0,
            "n_aromatic": 0,
            "n_hetero": 0,
            "mw": math.nan,
            "tpsa": math.nan,
            "hbd": math.nan,
            "hba": math.nan,
            "coarse_class": "invalid",
        }

    ring_info = mol.GetRingInfo()
    has_heterocycle = False
    for ring in ring_info.AtomRings():
        if any(mol.GetAtomWithIdx(idx).GetAtomicNum() not in {6, 1} for idx in ring):
            has_heterocycle = True
            break

    features = {
        "solute_smiles": str(smiles),
        "invalid": False,
        "has_oh": mol.HasSubstructMatch(Chem.MolFromSmarts("[OX2H]")),
        "has_nh": mol.HasSubstructMatch(Chem.MolFromSmarts("[NX3;H1,H2]")),
        "has_halogen": mol.HasSubstructMatch(Chem.MolFromSmarts("[F,Cl,Br,I]")),
        "has_sp": mol.HasSubstructMatch(Chem.MolFromSmarts("[S,P]")),
        "has_heterocycle": has_heterocycle,
        "n_rings": int(rdMolDescriptors.CalcNumRings(mol)),
        "n_aromatic": int(rdMolDescriptors.CalcNumAromaticRings(mol)),
        "n_hetero": int(rdMolDescriptors.CalcNumHeteroatoms(mol)),
        "mw": float(Descriptors.MolWt(mol)),
        "tpsa": float(rdMolDescriptors.CalcTPSA(mol)),
        "hbd": int(rdMolDescriptors.CalcNumHBD(mol)),
        "hba": int(rdMolDescriptors.CalcNumHBA(mol)),
    }
    features["coarse_class"] = _coarse_solute_class(features)
    return features


def summarize_metrics(df: pd.DataFrame) -> dict[str, Any]:
    return regression_metrics(
        df["ln_x2_pred"].to_numpy(dtype=float),
        df["ln_x2_true"].to_numpy(dtype=float),
    )


def pair_error_analysis(test_df: pd.DataFrame, out_dir: Path) -> dict[str, Any]:
    pair_df = (
        test_df.groupby(
            ["pair_key", "solute_smiles", "solvent_smiles"],
            as_index=False,
            sort=False,
        )
        .agg(
            n_points=("abs_error", "size"),
            mean_abs_error=("abs_error", "mean"),
            median_abs_error=("abs_error", "median"),
            max_abs_error=("abs_error", "max"),
            mean_signed_error=("signed_error", "mean"),
            temperature_min=("temperature", "min"),
            temperature_max=("temperature", "max"),
            ln_x2_true_mean=("ln_x2_true", "mean"),
            ln_x2_pred_mean=("ln_x2_pred", "mean"),
        )
        .sort_values("mean_abs_error", ascending=False, kind="stable")
        .reset_index(drop=True)
    )
    pair_df.to_csv(out_dir / "pair_errors.csv", index=False)
    pair_df.head(50).to_csv(out_dir / "top_worst_pairs.csv", index=False)

    mae_values = pair_df["mean_abs_error"].to_numpy(dtype=float)
    summary = {
        "n_pairs": int(len(pair_df)),
        "median_pair_mae": float(np.median(mae_values)),
        "p90_pair_mae": float(np.quantile(mae_values, 0.90)),
        "p95_pair_mae": float(np.quantile(mae_values, 0.95)),
        "fraction_pair_mae_lt_0_5": float(np.mean(mae_values < 0.5)),
        "fraction_pair_mae_lt_1_0": float(np.mean(mae_values < 1.0)),
        "fraction_pair_mae_gt_3_0": float(np.mean(mae_values > 3.0)),
        "fraction_pair_mae_gt_5_0": float(np.mean(mae_values > 5.0)),
    }
    (out_dir / "pair_error_summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    return summary


def chemistry_analysis(test_df: pd.DataFrame, out_dir: Path) -> dict[str, Any]:
    solute_features = pd.DataFrame(
        [describe_solute(smiles) for smiles in test_df["solute_smiles"].drop_duplicates()]
    )
    solute_features.to_csv(out_dir / "solute_features.csv", index=False)
    merged = test_df.merge(solute_features, on="solute_smiles", how="left")

    coarse_rows: list[dict[str, Any]] = []
    for coarse_class, grp in merged.groupby("coarse_class", sort=False):
        metrics = summarize_metrics(grp)
        coarse_rows.append(
            {
                "coarse_class": str(coarse_class),
                "n_rows": int(len(grp)),
                "n_solutes": int(grp["solute_smiles"].nunique()),
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
                "r2": metrics["r2"],
                "bias": metrics["bias"],
                "mean_abs_error": float(grp["abs_error"].mean()),
            }
        )
    coarse_df = pd.DataFrame(coarse_rows).sort_values(
        ["n_rows", "mae"],
        ascending=[False, True],
        na_position="last",
    )
    coarse_df.to_csv(out_dir / "chemistry_coarse_class_metrics.csv", index=False)

    flag_cols = [
        "has_oh",
        "has_nh",
        "has_halogen",
        "has_sp",
        "has_heterocycle",
    ]
    flag_rows: list[dict[str, Any]] = []
    for flag in flag_cols:
        grp = merged.loc[merged[flag].fillna(False).astype(bool)].copy()
        if grp.empty:
            continue
        metrics = summarize_metrics(grp)
        flag_rows.append(
            {
                "flag": flag,
                "n_rows": int(len(grp)),
                "n_solutes": int(grp["solute_smiles"].nunique()),
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
                "r2": metrics["r2"],
                "bias": metrics["bias"],
                "mean_abs_error": float(grp["abs_error"].mean()),
            }
        )
    flag_df = pd.DataFrame(flag_rows).sort_values(
        ["n_rows", "mae"],
        ascending=[False, True],
        na_position="last",
    )
    flag_df.to_csv(out_dir / "chemistry_flag_metrics.csv", index=False)

    summary = {
        "n_test_rows": int(len(test_df)),
        "n_unique_solutes": int(test_df["solute_smiles"].nunique()),
        "largest_coarse_class_by_rows": (
            None if coarse_df.empty else coarse_df.iloc[0].to_dict()
        ),
        "worst_coarse_class_by_mae": (
            None
            if coarse_df.empty
            else coarse_df.sort_values("mae", ascending=False, na_position="last").iloc[0].to_dict()
        ),
        "flag_count": int(len(flag_df)),
    }
    (out_dir / "chemistry_summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    return summary


def neighbor_error_analysis(
    test_df: pd.DataFrame,
    nearest_csv: Path,
    out_dir: Path,
) -> dict[str, Any] | None:
    if not nearest_csv.is_file():
        return None

    nn_df = pd.read_csv(nearest_csv, low_memory=False).copy()
    nn_df = nn_df.rename(columns={"ln_x2": "ln_x2_true"})
    payload_cols = [
        "nearest_train_pair_key",
        "pair_tanimoto",
        "solute_tanimoto",
        "solvent_tanimoto",
        "temperature_delta",
        "abs_delta_ln_x2",
        "is_cliff",
    ]
    if (
        "row_index" in test_df.columns
        and "row_index" in nn_df.columns
        and not test_df["row_index"].duplicated().any()
        and not nn_df["row_index"].duplicated().any()
    ):
        merged = test_df.merge(
            nn_df[["row_index"] + payload_cols],
            on=["row_index"],
            how="left",
        )
    else:
        merge_keys = ["solute_smiles", "solvent_smiles", "temperature", "ln_x2_true"]
        merged = test_df.merge(
            nn_df[merge_keys + payload_cols],
            on=merge_keys,
            how="left",
        )
    merged = merged.rename(columns={"abs_delta_ln_x2": "abs_neighbor_gap"})
    merged.to_csv(out_dir / "nearest_neighbor_error_rows.csv", index=False)

    match_count = int(merged["pair_tanimoto"].notna().sum())
    if match_count == 0:
        return {
            "matched_rows": 0,
            "n_test_rows": int(len(test_df)),
        }

    good = merged.loc[merged["pair_tanimoto"].notna()].copy()
    pair_tani = good["pair_tanimoto"].to_numpy(dtype=float)
    abs_error = good["abs_error"].to_numpy(dtype=float)
    bins = pd.cut(
        good["pair_tanimoto"],
        bins=[0.0, 0.3, 0.5, 0.7, 0.8, 1.01],
        right=False,
        include_lowest=True,
        labels=["0.00-0.30", "0.30-0.50", "0.50-0.70", "0.70-0.80", "0.80-1.00"],
    )
    bin_df = (
        good.assign(pair_tanimoto_bin=bins)
        .groupby("pair_tanimoto_bin", observed=False)
        .agg(
            n=("pair_tanimoto", "size"),
            mean_pair_tanimoto=("pair_tanimoto", "mean"),
            mae=("abs_error", "mean"),
            median_abs_error=("abs_error", "median"),
            p90_abs_error=("abs_error", lambda s: float(np.quantile(s, 0.90))),
        )
        .reset_index()
    )
    bin_df.to_csv(out_dir / "nearest_neighbor_error_bins.csv", index=False)

    thresholds: dict[str, Any] = {}
    for thr in (0.5, 0.6, 0.7, 0.8):
        mask = pair_tani >= thr
        key = f"pair_tanimoto_gte_{thr:.1f}"
        if not mask.any():
            thresholds[key] = {"n": 0, "mae": None, "median_abs_error": None}
            continue
        subset_err = abs_error[mask]
        thresholds[key] = {
            "n": int(mask.sum()),
            "mae": float(np.mean(subset_err)),
            "median_abs_error": float(np.median(subset_err)),
        }

    summary = {
        "n_test_rows": int(len(test_df)),
        "matched_rows": match_count,
        "pearson_pair_tanimoto_vs_abs_error": pearson_corr(pair_tani, abs_error),
        "spearman_pair_tanimoto_vs_abs_error": _rank_corr(pair_tani, abs_error),
        "mean_abs_error": float(np.mean(abs_error)),
        "median_abs_error": float(np.median(abs_error)),
        "thresholds": thresholds,
    }
    (out_dir / "nearest_neighbor_error_summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2),
        encoding="utf-8",
    )
    return summary


def train_gap_analysis(
    model: torch.nn.Module,
    cfg: Any,
    device: torch.device,
    *,
    train_path: Path,
    val_path: Path,
    test_path: Path,
    seed: int,
    eval_batch_size: int,
    reuse_test_predictions: pd.DataFrame | None,
    out_dir: Path,
) -> dict[str, Any]:
    cfg = cfg if isinstance(cfg, object) else cfg
    cfg.batch_size = int(eval_batch_size)

    split_payloads: dict[str, pd.DataFrame] = {}
    for split_name, split_path in (
        ("train", train_path),
        ("val", val_path),
    ):
        df = pd.read_csv(split_path, low_memory=False)
        loader = build_loader(df, cfg, seed=seed)
        pred_df = collect_direct_predictions(model, loader, device)
        pred_df.to_csv(out_dir / f"{split_name}_predictions.csv", index=False)
        split_payloads[split_name] = pred_df

    if reuse_test_predictions is not None:
        test_df = reuse_test_predictions.copy()
    else:
        df = pd.read_csv(test_path, low_memory=False)
        loader = build_loader(df, cfg, seed=seed)
        test_df = collect_direct_predictions(model, loader, device)
    test_df.to_csv(out_dir / "test_predictions.csv", index=False)
    split_payloads["test"] = test_df

    metrics = {
        split: summarize_metrics(pred_df)
        for split, pred_df in split_payloads.items()
    }
    metrics["gaps"] = {
        "test_minus_train_mae": float(metrics["test"]["mae"] - metrics["train"]["mae"]),
        "test_minus_val_mae": float(metrics["test"]["mae"] - metrics["val"]["mae"]),
        "test_minus_train_r2": float(metrics["test"]["r2"] - metrics["train"]["r2"]),
        "test_minus_val_r2": float(metrics["test"]["r2"] - metrics["val"]["r2"]),
    }
    (out_dir / "train_val_test_metrics.json").write_text(
        json.dumps(_json_safe(metrics), indent=2),
        encoding="utf-8",
    )
    return metrics


def build_markdown(
    *,
    gap_metrics: dict[str, Any],
    pair_summary: dict[str, Any],
    chemistry_summary: dict[str, Any],
    neighbor_summary: dict[str, Any] | None,
) -> str:
    lines = [
        "# DirectGNN Error Structure Diagnostics",
        "",
        "## Train / Val / Test",
        "",
        f"- Train: `MAE {gap_metrics['train']['mae']:.3f}`, `R^2 {gap_metrics['train']['r2']:.3f}`",
        f"- Val: `MAE {gap_metrics['val']['mae']:.3f}`, `R^2 {gap_metrics['val']['r2']:.3f}`",
        f"- Test: `MAE {gap_metrics['test']['mae']:.3f}`, `R^2 {gap_metrics['test']['r2']:.3f}`",
        f"- Test - Train MAE gap: `{gap_metrics['gaps']['test_minus_train_mae']:+.3f}`",
        "",
        "## Pair-Level Error",
        "",
        f"- Median pair MAE: `{pair_summary['median_pair_mae']:.3f}`",
        f"- P90 pair MAE: `{pair_summary['p90_pair_mae']:.3f}`",
        f"- P95 pair MAE: `{pair_summary['p95_pair_mae']:.3f}`",
        f"- Pairs with MAE < 1.0: `{pair_summary['fraction_pair_mae_lt_1_0']:.1%}`",
        f"- Pairs with MAE > 3.0: `{pair_summary['fraction_pair_mae_gt_3_0']:.1%}`",
        "",
        "## Chemistry",
        "",
        f"- Unique test solutes: `{chemistry_summary['n_unique_solutes']}`",
    ]
    worst_class = chemistry_summary.get("worst_coarse_class_by_mae")
    if isinstance(worst_class, dict):
        lines.append(
            "- Worst coarse class by MAE: "
            f"`{worst_class['coarse_class']}` "
            f"(n=`{int(worst_class['n_rows'])}`, MAE=`{float(worst_class['mae']):.3f}`)"
        )
    if neighbor_summary is not None:
        lines += [
            "",
            "## Nearest-Train-Neighbor",
            "",
            f"- Matched rows: `{neighbor_summary['matched_rows']}` / `{neighbor_summary['n_test_rows']}`",
            (
                "- Pearson(pair Tanimoto, abs error): "
                f"`{neighbor_summary['pearson_pair_tanimoto_vs_abs_error']:.3f}`"
                if neighbor_summary.get("pearson_pair_tanimoto_vs_abs_error") is not None
                else "- Pearson(pair Tanimoto, abs error): `NA`"
            ),
            (
                "- Spearman(pair Tanimoto, abs error): "
                f"`{neighbor_summary['spearman_pair_tanimoto_vs_abs_error']:.3f}`"
                if neighbor_summary.get("spearman_pair_tanimoto_vs_abs_error") is not None
                else "- Spearman(pair Tanimoto, abs error): `NA`"
            ),
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = Path(args.checkpoint).expanduser().resolve()
    train_path = Path(args.train_data).expanduser().resolve()
    val_path = Path(args.val_data).expanduser().resolve()
    test_path = Path(args.test_data).expanduser().resolve()
    test_predictions_path = Path(args.test_predictions).expanduser().resolve()
    nearest_path = Path(args.nearest_neighbors_csv).expanduser().resolve()

    device = resolve_device(args.device)
    model, cfg = load_direct_checkpoint(checkpoint_path, device)

    reused_test_df = None
    if test_predictions_path.is_file():
        reused_test_df = pd.read_csv(test_predictions_path, low_memory=False)
        reused_test_df["abs_error"] = np.abs(
            reused_test_df["ln_x2_pred"].to_numpy(dtype=float)
            - reused_test_df["ln_x2_true"].to_numpy(dtype=float)
        )
        reused_test_df["signed_error"] = (
            reused_test_df["ln_x2_pred"].to_numpy(dtype=float)
            - reused_test_df["ln_x2_true"].to_numpy(dtype=float)
        )

    gap_metrics = train_gap_analysis(
        model,
        cfg,
        device,
        train_path=train_path,
        val_path=val_path,
        test_path=test_path,
        seed=int(args.seed),
        eval_batch_size=int(args.eval_batch_size),
        reuse_test_predictions=reused_test_df,
        out_dir=out_dir,
    )
    test_df = pd.read_csv(out_dir / "test_predictions.csv", low_memory=False)

    pair_summary = pair_error_analysis(test_df, out_dir)
    chemistry_summary = chemistry_analysis(test_df, out_dir)
    neighbor_summary = neighbor_error_analysis(test_df, nearest_path, out_dir)

    top_level = {
        "checkpoint": str(checkpoint_path),
        "train_data": str(train_path),
        "val_data": str(val_path),
        "test_data": str(test_path),
        "test_predictions_reused": bool(reused_test_df is not None),
        "nearest_neighbors_used": bool(neighbor_summary is not None),
        "train_val_test_metrics": gap_metrics,
        "pair_error_summary": pair_summary,
        "chemistry_summary": chemistry_summary,
        "nearest_neighbor_summary": neighbor_summary,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(_json_safe(top_level), indent=2),
        encoding="utf-8",
    )
    (out_dir / "SUMMARY.md").write_text(
        build_markdown(
            gap_metrics=gap_metrics,
            pair_summary=pair_summary,
            chemistry_summary=chemistry_summary,
            neighbor_summary=neighbor_summary,
        ),
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(top_level), indent=2))


if __name__ == "__main__":
    main()
