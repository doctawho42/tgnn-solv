#!/usr/bin/env python
"""
Train and run FastSolv on TGNN-Solv datasets.

Examples:
  # Predict with pretrained FastSolv ensemble
  python scripts/run_fastsolv.py predict \
      --input notebooks/data/processed/test.csv \
      --output notebooks/data/processed/fastsolv_pred.csv

  # Train a FastSolv model on your splits
  python scripts/run_fastsolv.py train \
      --train notebooks/data/processed/train.csv \
      --val notebooks/data/processed/val.csv \
      --test notebooks/data/processed/test.csv \
      --outdir checkpoints/fastsolv_run

  # Compare FastSolv vs TGNN-Solv on a dataset
  python scripts/run_fastsolv.py compare \
      --input notebooks/data/processed/test.csv \
      --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
      --metrics checkpoints/fastsolv_compare.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors

try:
    from fastprop.defaults import ALL_2D
    from fastprop.descriptors import get_descriptors
    from fastprop.data import fastpropDataLoader, standard_scale
except Exception as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "fastprop is required. Install with `pip install fastsolv`."
    ) from exc

try:
    from pytorch_lightning import Trainer
    from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint
except Exception as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "pytorch-lightning is required (installed via fastsolv dependencies)."
    ) from exc

try:
    from fastsolv._classes import SolubilityDataset, _fastsolv
    from fastsolv._module import fastsolv as fastsolv_predict
except Exception as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "fastsolv is required. Install with `pip install fastsolv`."
    ) from exc

from tgnn_solv.data.utils import canonicalize
from tgnn_solv.data.sources import _density_map

if TYPE_CHECKING:  # pragma: no cover
    import torch


REQUIRED_COLUMNS = {"solute_smiles", "solvent_smiles", "temperature"}


def _estimate_c_solvent_molarity(smiles: str) -> Optional[float]:
    """Estimate solvent molarity (mol/L) from SMILES."""
    if not smiles:
        return None
    can = canonicalize(smiles) or smiles
    mol = Chem.MolFromSmiles(can)
    if mol is None:
        return None

    density_map = _density_map()
    rho = density_map.get(can)
    if rho is not None:
        mw = Descriptors.MolWt(mol)
        if mw > 0:
            return 1000.0 * rho / mw

    try:
        mol_h = Chem.AddHs(mol)
        params = AllChem.ETKDGv3()
        params.randomSeed = 0xF00D
        if AllChem.EmbedMolecule(mol_h, params) != 0:
            return None
        try:
            AllChem.UFFOptimizeMolecule(mol_h, maxIters=200)
        except Exception:
            pass
        vol_a3 = rdMolDescriptors.CalcMolVolume(mol_h)
        if not np.isfinite(vol_a3) or vol_a3 <= 0:
            return None
        v_m_cm3 = vol_a3 * 0.602214076
        if v_m_cm3 <= 0 or not np.isfinite(v_m_cm3):
            return None
        return 1000.0 / v_m_cm3
    except Exception:
        return None


def _build_c_solvent(
    solvent_smiles: Iterable[str],
) -> Dict[str, Optional[float]]:
    cache: Dict[str, Optional[float]] = {}
    for smi in solvent_smiles:
        if smi in cache:
            continue
        cache[smi] = _estimate_c_solvent_molarity(smi)
    return cache


def logS_from_ln_x2(df: pd.DataFrame) -> pd.Series:
    """Convert ln(x2) to logS (mol/L) with solvent molarity."""
    if "ln_x2" not in df.columns:
        raise ValueError("ln_x2 column missing for conversion.")
    x2 = np.exp(pd.to_numeric(df["ln_x2"], errors="coerce"))
    c_map = _build_c_solvent(df["solvent_smiles"].fillna(""))
    C = df["solvent_smiles"].map(c_map).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        S = x2 * C / (1.0 - x2)
        logS = np.log10(S)
    return pd.Series(logS, index=df.index)


def ln_x2_from_logS(df: pd.DataFrame) -> pd.Series:
    """Convert logS (mol/L) to ln(x2) with solvent molarity."""
    if "logS" not in df.columns:
        raise ValueError("logS column missing for conversion.")
    logS = pd.to_numeric(df["logS"], errors="coerce")
    S = np.power(10.0, logS)
    c_map = _build_c_solvent(df["solvent_smiles"].fillna(""))
    C = df["solvent_smiles"].map(c_map).astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        x2 = S / (S + C)
        ln_x2 = np.log(x2)
    return pd.Series(ln_x2, index=df.index)


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    df = df.copy()
    df["solute_smiles"] = df["solute_smiles"].apply(canonicalize)
    df["solvent_smiles"] = df["solvent_smiles"].apply(canonicalize)
    df = df.dropna(subset=["solute_smiles", "solvent_smiles", "temperature"])
    return df


def _compute_descriptors(
    unique_smiles: np.ndarray,
) -> Dict[str, np.ndarray]:
    mols = [Chem.MolFromSmiles(s) for s in unique_smiles]
    descs = get_descriptors(False, ALL_2D, mols).to_numpy(dtype=np.float32)
    return {smi: desc for smi, desc in zip(unique_smiles, descs)}


def _assemble_features(
    df: pd.DataFrame,
    desc_map: Dict[str, np.ndarray],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    sol = np.vstack([desc_map[s] for s in df["solute_smiles"]])
    slv = np.vstack([desc_map[s] for s in df["solvent_smiles"]])
    T = df["temperature"].to_numpy(dtype=np.float32).reshape(-1, 1)
    return sol, slv, T


def _scale_split(
    sol: np.ndarray,
    slv: np.ndarray,
    T: np.ndarray,
    y: np.ndarray,
    stats: Optional[Dict[str, "torch.Tensor"]] = None,
) -> Tuple["torch.Tensor", "torch.Tensor", "torch.Tensor", "torch.Tensor", Dict[str, "torch.Tensor"]]:
    import torch

    sol_t = torch.tensor(sol, dtype=torch.float32)
    slv_t = torch.tensor(slv, dtype=torch.float32)
    T_t = torch.tensor(T, dtype=torch.float32)
    y_t = torch.tensor(y, dtype=torch.float32)

    if stats is None:
        sol_s, sol_m, sol_v = standard_scale(sol_t)
        slv_s, slv_m, slv_v = standard_scale(slv_t)
        T_s, T_m, T_v = standard_scale(T_t)
        y_s, y_m, y_v = standard_scale(y_t)
        stats = {
            "solute_means": sol_m,
            "solute_vars": sol_v,
            "solvent_means": slv_m,
            "solvent_vars": slv_v,
            "temperature_means": T_m,
            "temperature_vars": T_v,
            "target_means": y_m,
            "target_vars": y_v,
        }
    else:
        sol_s = standard_scale(sol_t, stats["solute_means"], stats["solute_vars"])
        slv_s = standard_scale(slv_t, stats["solvent_means"], stats["solvent_vars"])
        T_s = standard_scale(T_t, stats["temperature_means"], stats["temperature_vars"])
        y_s = standard_scale(y_t, stats["target_means"], stats["target_vars"])

    return sol_s, slv_s, T_s, y_s, stats


def _compute_gradients(df: pd.DataFrame, logS_col: str = "logS") -> np.ndarray:
    grad = np.full(len(df), np.nan, dtype=np.float32)
    groups = df.groupby(["solute_smiles", "solvent_smiles"])
    for _, idx in groups.indices.items():
        if len(idx) < 2:
            continue
        temps = df.loc[idx, "temperature"].to_numpy(dtype=np.float32)
        logs = df.loc[idx, logS_col].to_numpy(dtype=np.float32)
        order = np.argsort(temps)
        temps = temps[order]
        logs = logs[order]
        grad_vals = np.gradient(logs, temps)
        grad_idx = np.array(idx)[order]
        grad[grad_idx] = grad_vals
    return grad


def _metrics(true: np.ndarray, pred: np.ndarray) -> Dict[str, float]:
    err = pred - true
    mae = float(np.abs(err).mean())
    rmse = float(np.sqrt((err ** 2).mean()))
    ss_res = float((err ** 2).sum())
    ss_tot = float(((true - true.mean()) ** 2).sum())
    r2 = float(1.0 - ss_res / (ss_tot + 1e-10))
    bias = float(err.mean())
    return {"mae": mae, "rmse": rmse, "r2": r2, "bias": bias}


def _masked_metrics(
    true: np.ndarray, pred: np.ndarray, mask: np.ndarray
) -> Tuple[Dict[str, float], int]:
    mask = mask.astype(bool)
    mask = mask & np.isfinite(true) & np.isfinite(pred)
    if not mask.any():
        return {"mae": float("nan"), "rmse": float("nan"),
                "r2": float("nan"), "bias": float("nan")}, 0
    return _metrics(true[mask], pred[mask]), int(mask.sum())


def _predict_with_model(
    model: _fastsolv,
    sol: np.ndarray,
    slv: np.ndarray,
    T: np.ndarray,
) -> np.ndarray:
    import torch

    ds = SolubilityDataset(
        torch.tensor(sol, dtype=torch.float32),
        torch.tensor(slv, dtype=torch.float32),
        torch.tensor(T, dtype=torch.float32),
        torch.zeros(len(sol), dtype=torch.float32),
        torch.zeros(len(sol), dtype=torch.float32),
    )
    loader = fastpropDataLoader(ds, num_workers=0, persistent_workers=False)
    trainer = Trainer(logger=False, enable_checkpointing=False)
    with torch.inference_mode():
        preds = trainer.predict(model, loader)
    return torch.vstack(preds).cpu().numpy().reshape(-1)


def _fastsolv_predict_ordered(
    df: pd.DataFrame,
    checkpoint: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    unique_smiles = np.unique(
        np.hstack([df["solute_smiles"].unique(), df["solvent_smiles"].unique()])
    )
    desc_map = _compute_descriptors(unique_smiles)
    sol, slv, T = _assemble_features(df, desc_map)

    if checkpoint:
        model = _fastsolv.load_from_checkpoint(checkpoint)
        pred = _predict_with_model(model, sol, slv, T)
        return pred, np.full_like(pred, np.nan)

    try:
        from fastsolv._module import _ALL_MODELS
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Unable to access FastSolv pretrained ensemble."
        ) from exc

    all_preds = []
    for model in _ALL_MODELS:
        all_preds.append(_predict_with_model(model, sol, slv, T))
    stacked = np.stack(all_preds, axis=1)
    return stacked.mean(axis=1), stacked.std(axis=1)


def _tgnn_predict_ordered(
    dataset,
    checkpoint: str,
    batch_size: int,
    device: Optional[str],
) -> Tuple[np.ndarray, np.ndarray]:
    import torch
    from torch.utils.data import DataLoader

    from tgnn_solv.data.dataset import collate_fn
    from tgnn_solv.inference import load_model

    dev = torch.device(device) if device else None
    model, _cfg = load_model(checkpoint, device=dev)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0,
        pin_memory=(dev is not None and dev.type == "cuda"),
    )

    model.eval()
    device = next(model.parameters()).device
    preds = []
    masks = []
    with torch.no_grad():
        for sol_b, slv_b, tgt in loader:
            sol_b = sol_b.to(device)
            slv_b = slv_b.to(device)
            T = tgt["T"].to(device)
            solvent_type = tgt.get("solvent_type")
            out = model(sol_b, slv_b, T, solvent_type=solvent_type)
            preds.append(out["ln_x2"].detach().cpu().numpy())
            masks.append(tgt["has_solubility"].cpu().numpy())

    return np.concatenate(preds), np.concatenate(masks).astype(bool)


def run_predict(args: argparse.Namespace) -> int:
    df = _clean_df(pd.read_csv(args.input))

    if args.checkpoint:
        model = _fastsolv.load_from_checkpoint(args.checkpoint)
        unique_smiles = np.unique(
            np.hstack([df["solute_smiles"].unique(), df["solvent_smiles"].unique()])
        )
        desc_map = _compute_descriptors(unique_smiles)
        sol, slv, T = _assemble_features(df, desc_map)
        pred_logS = _predict_with_model(model, sol, slv, T)
        df_out = df.copy()
        df_out["predicted_logS"] = pred_logS
        df_out["predicted_logS_stdev"] = np.nan
    else:
        df_out = fastsolv_predict(df).reset_index()

    metrics = {}
    if "ln_x2" in df.columns:
        df_out["logS"] = logS_from_ln_x2(df)
        df_out["predicted_ln_x2"] = ln_x2_from_logS(
            df_out.rename(columns={"predicted_logS": "logS"})
        )
        try:
            metrics["logS"] = _metrics(
                df_out["logS"].to_numpy(dtype=float),
                df_out["predicted_logS"].to_numpy(dtype=float),
            )
            metrics["ln_x2"] = _metrics(
                df["ln_x2"].to_numpy(dtype=float),
                df_out["predicted_ln_x2"].to_numpy(dtype=float),
            )
        except Exception:
            pass

    df_out.to_csv(args.output, index=False)
    print(f"Saved predictions to {args.output}")
    if args.metrics and metrics:
        with open(args.metrics, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        print(f"Saved metrics to {args.metrics}")
    return 0


def run_train(args: argparse.Namespace) -> int:
    import torch

    train_df = _clean_df(pd.read_csv(args.train))
    val_df = _clean_df(pd.read_csv(args.val))
    test_df = _clean_df(pd.read_csv(args.test)) if args.test else None

    if args.target == "logS":
        if "logS" not in train_df.columns:
            train_df["logS"] = logS_from_ln_x2(train_df)
            val_df["logS"] = logS_from_ln_x2(val_df)
            if test_df is not None:
                test_df["logS"] = logS_from_ln_x2(test_df)
        else:
            train_df["logS"] = pd.to_numeric(train_df["logS"], errors="coerce")
            val_df["logS"] = pd.to_numeric(val_df["logS"], errors="coerce")
            if test_df is not None:
                test_df["logS"] = pd.to_numeric(test_df["logS"], errors="coerce")
    else:
        train_df["logS"] = logS_from_ln_x2(train_df)
        val_df["logS"] = logS_from_ln_x2(val_df)
        if test_df is not None:
            test_df["logS"] = logS_from_ln_x2(test_df)

    train_df = train_df.dropna(subset=["logS"])
    val_df = val_df.dropna(subset=["logS"])
    if test_df is not None:
        test_df = test_df.dropna(subset=["logS"])

    if args.compute_gradients:
        train_df["dlogS_dT"] = _compute_gradients(train_df)
        val_df["dlogS_dT"] = _compute_gradients(val_df)
        if test_df is not None:
            test_df["dlogS_dT"] = _compute_gradients(test_df)
    else:
        train_df["dlogS_dT"] = 0.0
        val_df["dlogS_dT"] = 0.0
        if test_df is not None:
            test_df["dlogS_dT"] = 0.0

    unique_smiles = np.unique(
        np.hstack(
            [
                train_df["solute_smiles"].unique(),
                train_df["solvent_smiles"].unique(),
                val_df["solute_smiles"].unique(),
                val_df["solvent_smiles"].unique(),
                [] if test_df is None else test_df["solute_smiles"].unique(),
                [] if test_df is None else test_df["solvent_smiles"].unique(),
            ]
        )
    )
    desc_map = _compute_descriptors(unique_smiles)

    train_sol, train_slv, train_T = _assemble_features(train_df, desc_map)
    val_sol, val_slv, val_T = _assemble_features(val_df, desc_map)
    train_y = train_df["logS"].to_numpy(dtype=np.float32).reshape(-1, 1)
    val_y = val_df["logS"].to_numpy(dtype=np.float32).reshape(-1, 1)

    train_sol_s, train_slv_s, train_T_s, train_y_s, stats = _scale_split(
        train_sol, train_slv, train_T, train_y
    )
    val_sol_s, val_slv_s, val_T_s, val_y_s, _ = _scale_split(
        val_sol, val_slv, val_T, val_y, stats=stats
    )

    train_grad = torch.tensor(
        train_df["dlogS_dT"].to_numpy(dtype=np.float32).reshape(-1, 1)
    )
    val_grad = torch.tensor(
        val_df["dlogS_dT"].to_numpy(dtype=np.float32).reshape(-1, 1)
    )

    disable_custom = args.disable_custom_loss or not args.compute_gradients
    if disable_custom:
        os.environ["DISABLE_CUSTOM_LOSS"] = "1"

    model = _fastsolv(
        num_layers=args.num_layers,
        hidden_size=args.hidden_size,
        activation_fxn=args.activation,
        input_activation=args.input_activation,
        learning_rate=args.lr,
        target_means=stats["target_means"],
        target_vars=stats["target_vars"],
        solute_means=stats["solute_means"],
        solute_vars=stats["solute_vars"],
        solvent_means=stats["solvent_means"],
        solvent_vars=stats["solvent_vars"],
        temperature_means=stats["temperature_means"],
        temperature_vars=stats["temperature_vars"],
    )

    train_ds = SolubilityDataset(
        train_sol_s, train_slv_s, train_T_s, train_y_s, train_grad
    )
    val_ds = SolubilityDataset(
        val_sol_s, val_slv_s, val_T_s, val_y_s, val_grad
    )

    train_loader = fastpropDataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0, persistent_workers=False
    )
    val_loader = fastpropDataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0, persistent_workers=False
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ckpt_cb = ModelCheckpoint(
        dirpath=outdir / "checkpoints",
        monitor="validation_mse_scaled_loss",
        mode="min",
        save_top_k=1,
    )
    es_cb = EarlyStopping(
        monitor="validation_mse_scaled_loss",
        mode="min",
        patience=args.patience,
    )

    trainer = Trainer(
        max_epochs=args.epochs,
        accelerator="auto",
        devices=1,
        callbacks=[ckpt_cb, es_cb],
        default_root_dir=str(outdir),
        log_every_n_steps=50,
        enable_progress_bar=True,
    )
    trainer.fit(model, train_loader, val_loader)

    best_ckpt = ckpt_cb.best_model_path
    if best_ckpt:
        print(f"Best checkpoint: {best_ckpt}")

    # Evaluate
    metrics = {}
    model = _fastsolv.load_from_checkpoint(best_ckpt) if best_ckpt else model
    pred_val = _predict_with_model(model, val_sol, val_slv, val_T)
    metrics["val_logS"] = _metrics(val_y.squeeze(), pred_val)

    if test_df is not None:
        test_sol, test_slv, test_T = _assemble_features(test_df, desc_map)
        test_y = test_df["logS"].to_numpy(dtype=np.float32).reshape(-1)
        pred_test = _predict_with_model(model, test_sol, test_slv, test_T)
        metrics["test_logS"] = _metrics(test_y, pred_test)

    if args.metrics:
        with open(args.metrics, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        print(f"Saved metrics to {args.metrics}")

    return 0


def run_compare(args: argparse.Namespace) -> int:
    base_df = _clean_df(pd.read_csv(args.input))

    # Use TGNN dataset filtering to ensure comparable rows
    from tgnn_solv.data.dataset import TGNNSolvDataset
    dataset = TGNNSolvDataset(base_df, cache=True)
    df = dataset.df.reset_index(drop=True)

    pred_tgnn, mask_tgnn = _tgnn_predict_ordered(
        dataset, args.tgnn_checkpoint, args.batch_size, args.device
    )

    pred_fast_logS, pred_fast_std = _fastsolv_predict_ordered(
        df, checkpoint=args.fastsolv_checkpoint
    )
    pred_fast_ln_x2 = ln_x2_from_logS(
        pd.DataFrame(
            {"solvent_smiles": df["solvent_smiles"], "logS": pred_fast_logS}
        )
    ).to_numpy(dtype=float)

    has_sol = (
        df["has_solubility"].to_numpy(dtype=bool)
        if "has_solubility" in df.columns
        else np.ones(len(df), dtype=bool)
    )
    true_ln_x2 = df["ln_x2"].to_numpy(dtype=float)

    tgnn_metrics, tgnn_n = _masked_metrics(
        true_ln_x2, pred_tgnn, has_sol & mask_tgnn
    )
    fast_metrics, fast_n = _masked_metrics(
        true_ln_x2, pred_fast_ln_x2, has_sol
    )

    true_logS = logS_from_ln_x2(df).to_numpy(dtype=float)
    fast_logS_metrics, _ = _masked_metrics(
        true_logS, pred_fast_logS, has_sol
    )

    result = {
        "n_samples": int(has_sol.sum()),
        "tgnn_solv": {
            "n": tgnn_n,
            "ln_x2": tgnn_metrics,
            "checkpoint": args.tgnn_checkpoint,
        },
        "fastsolv": {
            "n": fast_n,
            "ln_x2": fast_metrics,
            "logS": fast_logS_metrics,
            "checkpoint": args.fastsolv_checkpoint or "pretrained_ensemble",
        },
    }

    print("\nComparison (ln_x2):")
    print(f"  TGNN-Solv: MAE={tgnn_metrics['mae']:.3f} "
          f"RMSE={tgnn_metrics['rmse']:.3f} R²={tgnn_metrics['r2']:.3f}")
    print(f"  FastSolv:  MAE={fast_metrics['mae']:.3f} "
          f"RMSE={fast_metrics['rmse']:.3f} R²={fast_metrics['r2']:.3f}")

    if args.metrics:
        with open(args.metrics, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Saved metrics to {args.metrics}")

    if args.preds:
        out_df = df.copy()
        out_df["tgnn_ln_x2"] = pred_tgnn
        out_df["fastsolv_logS"] = pred_fast_logS
        out_df["fastsolv_logS_stdev"] = pred_fast_std
        out_df["fastsolv_ln_x2"] = pred_fast_ln_x2
        out_df.to_csv(args.preds, index=False)
        print(f"Saved predictions to {args.preds}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train or run FastSolv on TGNN-Solv datasets."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    predict_p = sub.add_parser("predict", help="Run predictions")
    predict_p.add_argument("--input", required=True)
    predict_p.add_argument("--output", required=True)
    predict_p.add_argument("--checkpoint", default=None)
    predict_p.add_argument("--metrics", default=None)

    train_p = sub.add_parser("train", help="Train FastSolv")
    train_p.add_argument("--train", required=True)
    train_p.add_argument("--val", required=True)
    train_p.add_argument("--test", default=None)
    train_p.add_argument("--outdir", required=True)
    train_p.add_argument("--epochs", type=int, default=200)
    train_p.add_argument("--batch-size", type=int, default=256)
    train_p.add_argument("--lr", type=float, default=1e-4)
    train_p.add_argument("--patience", type=int, default=20)
    train_p.add_argument("--num-layers", type=int, default=2)
    train_p.add_argument("--hidden-size", type=int, default=1800)
    train_p.add_argument("--activation", default="relu", choices=["relu", "leakyrelu"])
    train_p.add_argument("--input-activation", default="sigmoid", choices=["sigmoid", "clamp3"])
    train_p.add_argument("--target", default="ln_x2", choices=["ln_x2", "logS"])
    train_p.add_argument("--compute-gradients", action="store_true")
    train_p.add_argument("--disable-custom-loss", action="store_true")
    train_p.add_argument("--metrics", default=None)

    compare_p = sub.add_parser(
        "compare", help="Compare FastSolv vs TGNN-Solv"
    )
    compare_p.add_argument("--input", required=True)
    compare_p.add_argument("--tgnn-checkpoint", required=True)
    compare_p.add_argument("--fastsolv-checkpoint", default=None)
    compare_p.add_argument("--batch-size", type=int, default=128)
    compare_p.add_argument("--device", default=None)
    compare_p.add_argument("--metrics", default=None)
    compare_p.add_argument("--preds", default=None)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.cmd == "predict":
        return run_predict(args)
    if args.cmd == "train":
        return run_train(args)
    if args.cmd == "compare":
        return run_compare(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
