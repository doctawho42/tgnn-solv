#!/usr/bin/env python
"""Train, evaluate, and benchmark FastSolv on TGNN-Solv datasets."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Optional

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from rdkit import Chem

from tgnn_solv.data.split_registry import build_split_metadata
from tgnn_solv.external_benchmarking import (
    BenchmarkArtifacts,
    build_benchmark_artifacts,
    ln_x2_from_logS,
    logS_from_ln_x2,
    prepare_pair_dataframe,
    regression_metrics,
    write_benchmark_artifacts,
)

if TYPE_CHECKING:  # pragma: no cover
    import torch

ALL_2D = None
get_descriptors = None
fastprop_descriptors_module = None
fastpropDataLoader = None
standard_scale = None
Trainer = None
EarlyStopping = None
ModelCheckpoint = None
SolubilityDataset = None
FastsolvModel = None


def _load_fastsolv_runtime(descriptor_nproc: int | None = None) -> None:
    """Import optional FastSolv dependencies only when needed."""
    global ALL_2D
    global get_descriptors
    global fastprop_descriptors_module
    global fastpropDataLoader
    global standard_scale
    global Trainer
    global EarlyStopping
    global ModelCheckpoint
    global SolubilityDataset
    global FastsolvModel

    if FastsolvModel is not None:
        if descriptor_nproc is not None and fastprop_descriptors_module is not None:
            fastprop_descriptors_module._N_CPUS = max(1, int(descriptor_nproc))
        return

    try:
        import fastprop.descriptors as _fastprop_descriptors_module
        from fastprop.defaults import ALL_2D as _ALL_2D
        from fastprop.descriptors import get_descriptors as _get_descriptors
        from fastprop.data import (
            fastpropDataLoader as _fastpropDataLoader,
            standard_scale as _standard_scale,
        )
        from pytorch_lightning import Trainer as _Trainer
        from pytorch_lightning.callbacks import (
            EarlyStopping as _EarlyStopping,
            ModelCheckpoint as _ModelCheckpoint,
        )
        from fastsolv._classes import (
            SolubilityDataset as _SolubilityDataset,
            _fastsolv as _FastsolvModel,
        )
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "FastSolv runtime is not available. Install it with `pip install fastsolv`."
        ) from exc

    ALL_2D = _ALL_2D
    get_descriptors = _get_descriptors
    fastprop_descriptors_module = _fastprop_descriptors_module
    fastpropDataLoader = _fastpropDataLoader
    standard_scale = _standard_scale
    Trainer = _Trainer
    EarlyStopping = _EarlyStopping
    ModelCheckpoint = _ModelCheckpoint
    SolubilityDataset = _SolubilityDataset
    FastsolvModel = _FastsolvModel
    if descriptor_nproc is not None:
        fastprop_descriptors_module._N_CPUS = max(1, int(descriptor_nproc))


def _get_nan_tolerant_fastsolv_class() -> type[object]:
    """Wrap FastSolv's Lightning module so early NaNs don't kill the run."""
    _load_fastsolv_runtime()

    class NaNTolerantFastsolv(FastsolvModel):
        def validation_step(self, batch: object, batch_idx: int) -> object:
            try:
                return super().validation_step(batch, batch_idx)
            except ValueError as exc:
                if "Input contains NaN" in str(exc):
                    print(
                        "\n[Warning] FastSolv validation metric skipped due to NaN "
                        f"(epoch {self.trainer.current_epoch})."
                    )
                    import torch

                    return {"loss": torch.tensor(0.0)}
                raise

    return NaNTolerantFastsolv


def _clean_df(df: pd.DataFrame, *, require_targets: bool = False) -> pd.DataFrame:
    return prepare_pair_dataframe(df, require_targets=require_targets)


def _compute_descriptors(
    unique_smiles: Iterable[str],
    *,
    descriptor_nproc: int = 1,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    _load_fastsolv_runtime(descriptor_nproc=descriptor_nproc)
    smiles_array = np.asarray(list(unique_smiles), dtype=object)
    mols = [Chem.MolFromSmiles(str(s)) for s in smiles_array]
    descriptor_frame = get_descriptors(False, ALL_2D, mols).apply(pd.to_numeric, errors="coerce")
    descriptor_array = descriptor_frame.to_numpy(dtype=np.float32)
    finite_mask = np.isfinite(descriptor_array)
    nonfinite_before = int((~finite_mask).sum())
    rows_with_nonfinite_before = (
        int((~finite_mask).any(axis=1).sum()) if descriptor_array.ndim == 2 else 0
    )
    cols_with_nonfinite_before = (
        int((~finite_mask).any(axis=0).sum()) if descriptor_array.ndim == 2 else 0
    )

    # FastSolv's descriptor stack emits NaN/inf in a stable subset of columns for
    # this corpus. Replace them with train/predict-independent column statistics
    # so scaling and checkpoint buffers remain finite.
    if descriptor_array.ndim == 2 and descriptor_array.size:
        sanitized = descriptor_array.astype(np.float32, copy=True)
        with np.errstate(invalid="ignore"):
            column_fill = np.nanmean(np.where(finite_mask, sanitized, np.nan), axis=0)
        column_fill = np.where(np.isfinite(column_fill), column_fill, 0.0).astype(np.float32, copy=False)
        nonfinite_rows, nonfinite_cols = np.where(~finite_mask)
        if nonfinite_rows.size:
            sanitized[nonfinite_rows, nonfinite_cols] = column_fill[nonfinite_cols]
        descriptor_array = sanitized

    finite_mask_after = np.isfinite(descriptor_array)
    diagnostics = {
        "n_smiles": int(len(smiles_array)),
        "n_descriptor_columns": int(descriptor_array.shape[1]) if descriptor_array.ndim == 2 else 0,
        "nonfinite_cells_before_sanitize": nonfinite_before,
        "rows_with_nonfinite_before_sanitize": rows_with_nonfinite_before,
        "cols_with_nonfinite_before_sanitize": cols_with_nonfinite_before,
        "nonfinite_cells_after_sanitize": int((~finite_mask_after).sum()),
        "rows_with_nonfinite_after_sanitize": (
            int((~finite_mask_after).any(axis=1).sum()) if descriptor_array.ndim == 2 else 0
        ),
        "cols_with_nonfinite_after_sanitize": (
            int((~finite_mask_after).any(axis=0).sum()) if descriptor_array.ndim == 2 else 0
        ),
        "descriptor_nproc": int(descriptor_nproc),
    }
    return {
        smi: descriptor_array[idx]
        for idx, smi in enumerate(smiles_array)
    }, diagnostics


def _assemble_features(
    df: pd.DataFrame,
    desc_map: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sol = np.vstack([desc_map[str(s)] for s in df["solute_smiles"]]).astype(np.float32, copy=False)
    slv = np.vstack([desc_map[str(s)] for s in df["solvent_smiles"]]).astype(np.float32, copy=False)
    temp = df["temperature"].to_numpy(dtype=np.float32).reshape(-1, 1)
    return sol, slv, temp


def _scale_split(
    sol: np.ndarray,
    slv: np.ndarray,
    temp: np.ndarray,
    target: np.ndarray,
    stats: Optional[dict[str, "torch.Tensor"]] = None,
) -> tuple["torch.Tensor", "torch.Tensor", "torch.Tensor", "torch.Tensor", dict[str, "torch.Tensor"]]:
    import torch

    _load_fastsolv_runtime()
    sol_t = torch.tensor(sol, dtype=torch.float32)
    slv_t = torch.tensor(slv, dtype=torch.float32)
    temp_t = torch.tensor(temp, dtype=torch.float32)
    target_t = torch.tensor(target, dtype=torch.float32)

    if stats is None:
        sol_s, sol_m, sol_v = standard_scale(sol_t)
        slv_s, slv_m, slv_v = standard_scale(slv_t)
        temp_s, temp_m, temp_v = standard_scale(temp_t)
        target_s, target_m, target_v = standard_scale(target_t)
        stats = {
            "solute_means": sol_m,
            "solute_vars": sol_v,
            "solvent_means": slv_m,
            "solvent_vars": slv_v,
            "temperature_means": temp_m,
            "temperature_vars": temp_v,
            "target_means": target_m,
            "target_vars": target_v,
        }
    else:
        sol_s = standard_scale(sol_t, stats["solute_means"], stats["solute_vars"])
        slv_s = standard_scale(slv_t, stats["solvent_means"], stats["solvent_vars"])
        temp_s = standard_scale(temp_t, stats["temperature_means"], stats["temperature_vars"])
        target_s = standard_scale(target_t, stats["target_means"], stats["target_vars"])

    return sol_s, slv_s, temp_s, target_s, stats


def _scale_features_for_model(
    model: object,
    sol: np.ndarray,
    slv: np.ndarray,
    temp: np.ndarray,
) -> tuple["torch.Tensor", "torch.Tensor", "torch.Tensor"]:
    import torch

    _load_fastsolv_runtime()
    def _cpu_stat(name: str) -> "torch.Tensor | None":
        value = getattr(model, name, None)
        if value is None:
            return None
        return value.detach().cpu()

    sol_t = torch.tensor(sol, dtype=torch.float32)
    slv_t = torch.tensor(slv, dtype=torch.float32)
    temp_t = torch.tensor(temp, dtype=torch.float32)
    sol_s = standard_scale(sol_t, _cpu_stat("solute_means"), _cpu_stat("solute_vars"))
    slv_s = standard_scale(slv_t, _cpu_stat("solvent_means"), _cpu_stat("solvent_vars"))
    temp_s = standard_scale(temp_t, _cpu_stat("temperature_means"), _cpu_stat("temperature_vars"))
    return sol_s, slv_s, temp_s


def _compute_gradients(df: pd.DataFrame, logS_col: str = "logS") -> np.ndarray:
    gradients = np.full(len(df), np.nan, dtype=np.float32)
    for _, idx in df.groupby(["solute_smiles", "solvent_smiles"]).indices.items():
        if len(idx) < 2:
            continue
        temperatures = df.loc[idx, "temperature"].to_numpy(dtype=np.float32)
        logs = df.loc[idx, logS_col].to_numpy(dtype=np.float32)
        order = np.argsort(temperatures)
        grad_values = np.gradient(logs[order], temperatures[order])
        gradients[np.asarray(idx)[order]] = grad_values
    return gradients


def _summarize_logS_targets(df: pd.DataFrame) -> dict[str, Any]:
    values = pd.to_numeric(df["logS"], errors="coerce").to_numpy(dtype=float)
    finite_mask = np.isfinite(values)
    invalid_rows = df.loc[~finite_mask].copy()
    invalid_solvents = (
        invalid_rows["solvent_smiles"].astype(str).value_counts().head(20).to_dict()
        if not invalid_rows.empty
        else {}
    )
    ln_x2_nonnegative = 0
    if "ln_x2" in df.columns:
        ln_x2 = pd.to_numeric(df["ln_x2"], errors="coerce")
        ln_x2_nonnegative = int((ln_x2 >= 0.0).sum())
    return {
        "rows_before_filter": int(len(df)),
        "finite_rows": int(finite_mask.sum()),
        "nan_rows": int(np.isnan(values).sum()),
        "posinf_rows": int(np.isposinf(values).sum()),
        "neginf_rows": int(np.isneginf(values).sum()),
        "rows_with_ln_x2_ge_0": ln_x2_nonnegative,
        "top_invalid_solvents": invalid_solvents,
    }


def _filter_finite_logS_rows(
    df: pd.DataFrame,
    *,
    split_name: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    diagnostics = _summarize_logS_targets(df)
    finite_mask = np.isfinite(pd.to_numeric(df["logS"], errors="coerce").to_numpy(dtype=float))
    filtered = df.loc[finite_mask].reset_index(drop=True)
    diagnostics.update(
        {
            "split": split_name,
            "rows_after_filter": int(len(filtered)),
            "rows_dropped": int(len(df) - len(filtered)),
        }
    )
    return filtered, diagnostics


def _assert_finite_stats(stats: dict[str, "torch.Tensor"]) -> None:
    import torch

    bad: list[str] = []
    for name, tensor in stats.items():
        if tensor is None:
            bad.append(f"{name}=None")
            continue
        if not torch.isfinite(tensor).all():
            bad.append(name)
    if bad:
        raise ValueError(
            "Non-finite FastSolv scaling statistics detected: "
            + ", ".join(bad)
        )


def _predict_with_model(
    model: object,
    sol: np.ndarray,
    slv: np.ndarray,
    temp: np.ndarray,
    *,
    batch_size: int = 256,
) -> np.ndarray:
    import torch

    _load_fastsolv_runtime()
    sol_s, slv_s, temp_s = _scale_features_for_model(model, sol, slv, temp)
    dataset = SolubilityDataset(
        sol_s,
        slv_s,
        temp_s,
        torch.zeros(len(sol_s), dtype=torch.float32),
        torch.zeros(len(sol_s), dtype=torch.float32),
    )
    loader = fastpropDataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        persistent_workers=False,
    )
    trainer = Trainer(logger=False, enable_checkpointing=False)
    with torch.inference_mode():
        preds = trainer.predict(model, loader)
    return torch.vstack(preds).cpu().numpy().reshape(-1)


def _load_fastsolv_models_from_checkpoint(checkpoint: str) -> list[object]:
    _load_fastsolv_runtime()
    return [FastsolvModel.load_from_checkpoint(checkpoint)]


def _load_fastsolv_pretrained_ensemble() -> list[object]:
    _load_fastsolv_runtime()
    try:
        from fastsolv._module import _ALL_MODELS
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Unable to access the FastSolv pretrained ensemble.") from exc
    return list(_ALL_MODELS)


def _fastsolv_predict_ordered(
    df: pd.DataFrame,
    *,
    checkpoint: str | None = None,
    batch_size: int = 256,
    descriptor_nproc: int = 1,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    unique_smiles = np.unique(
        np.hstack([df["solute_smiles"].unique(), df["solvent_smiles"].unique()])
    )
    desc_map, diagnostics = _compute_descriptors(unique_smiles, descriptor_nproc=descriptor_nproc)
    sol, slv, temp = _assemble_features(df, desc_map)
    models = (
        _load_fastsolv_models_from_checkpoint(checkpoint)
        if checkpoint
        else _load_fastsolv_pretrained_ensemble()
    )
    all_predictions = [
        _predict_with_model(model, sol, slv, temp, batch_size=batch_size)
        for model in models
    ]
    stacked = np.stack(all_predictions, axis=1)
    diagnostics = {
        **diagnostics,
        "n_models": int(len(models)),
        "checkpoint": checkpoint or "pretrained_ensemble",
    }
    return stacked.mean(axis=1), stacked.std(axis=1), diagnostics


def _evaluate_prediction_bundle(
    *,
    model_name: str,
    split_name: str,
    split_df: pd.DataFrame,
    pred_logS: np.ndarray,
    uncertainty: np.ndarray | None = None,
    split_mode: str | None = None,
    test_data: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> BenchmarkArtifacts:
    eval_df = split_df.copy().reset_index(drop=True)
    eval_df["logS"] = logS_from_ln_x2(eval_df)
    eval_df["pred_logS"] = np.asarray(pred_logS, dtype=float)
    eval_df["pred_ln_x2"] = ln_x2_from_logS(
        pd.DataFrame(
            {
                "solvent_smiles": eval_df["solvent_smiles"],
                "logS": eval_df["pred_logS"],
            }
        ),
        logS_col="logS",
    )
    artifacts = build_benchmark_artifacts(
        model_name=model_name,
        eval_df=eval_df,
        pred_ln_x2=eval_df["pred_ln_x2"].to_numpy(dtype=float),
        pred_logS=eval_df["pred_logS"].to_numpy(dtype=float),
        uncertainty=uncertainty,
        metadata={
            **dict(metadata or {}),
            "model_family": "fastsolv",
            "evaluation_space": "ln_x2/logS",
            "split_name": split_name,
        },
        split_mode=split_mode or split_name,
        test_data=test_data,
    )
    artifacts.summary["split"] = split_name
    artifacts.summary["model"] = model_name
    return artifacts


def _save_descriptor_diagnostics(outdir: Path, diagnostics: dict[str, Any]) -> None:
    (outdir / "descriptor_diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2),
        encoding="utf-8",
    )


def run_predict(args: argparse.Namespace) -> int:
    df = _clean_df(pd.read_csv(args.input), require_targets="ln_x2" in pd.read_csv(args.input, nrows=0).columns)
    pred_logS, pred_std, diagnostics = _fastsolv_predict_ordered(
        df,
        checkpoint=args.checkpoint,
        batch_size=int(args.batch_size),
        descriptor_nproc=int(args.descriptor_nproc),
    )
    out_df = df.copy()
    out_df["fastsolv_logS"] = pred_logS
    out_df["fastsolv_logS_stdev"] = pred_std
    out_df["fastsolv_ln_x2"] = ln_x2_from_logS(
        pd.DataFrame(
            {
                "solvent_smiles": out_df["solvent_smiles"],
                "logS": out_df["fastsolv_logS"],
            }
        ),
        logS_col="logS",
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.output, index=False)
    print(f"Saved predictions to {args.output}")

    if args.metrics and "ln_x2" in df.columns:
        artifacts = _evaluate_prediction_bundle(
            model_name="fastsolv",
            split_name="predict",
            split_df=df,
            pred_logS=pred_logS,
            uncertainty=pred_std,
            split_mode=args.split_mode,
            test_data=args.input,
            metadata={"checkpoint": args.checkpoint or "pretrained_ensemble", "descriptor_diagnostics": diagnostics},
        )
        Path(args.metrics).parent.mkdir(parents=True, exist_ok=True)
        Path(args.metrics).write_text(json.dumps(artifacts.report, indent=2), encoding="utf-8")
        print(f"Saved benchmark report to {args.metrics}")
    return 0


def run_train(args: argparse.Namespace) -> int:
    import torch

    os.environ["FASTPROP_SKIP_MAPE"] = "1"
    _load_fastsolv_runtime(descriptor_nproc=int(args.descriptor_nproc))

    train_df = _clean_df(pd.read_csv(args.train), require_targets=True)
    val_df = _clean_df(pd.read_csv(args.val), require_targets=True)
    test_df = _clean_df(pd.read_csv(args.test), require_targets=True) if args.test else None

    for split_df in [train_df, val_df, test_df]:
        if split_df is None:
            continue
        split_df["logS"] = logS_from_ln_x2(split_df)

    train_df, train_target_diag = _filter_finite_logS_rows(train_df, split_name="train")
    val_df, val_target_diag = _filter_finite_logS_rows(val_df, split_name="val")
    test_target_diag = None
    if test_df is not None:
        test_df, test_target_diag = _filter_finite_logS_rows(test_df, split_name="test")

    if train_df.empty or val_df.empty:
        raise ValueError(
            "FastSolv training received no finite logS targets after filtering. "
            "Check solvent molarity coverage and ln_x2->logS conversion."
        )

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
    desc_map, diagnostics = _compute_descriptors(unique_smiles, descriptor_nproc=int(args.descriptor_nproc))

    train_sol, train_slv, train_temp = _assemble_features(train_df, desc_map)
    val_sol, val_slv, val_temp = _assemble_features(val_df, desc_map)
    train_target = train_df["logS"].to_numpy(dtype=np.float32).reshape(-1, 1)
    val_target = val_df["logS"].to_numpy(dtype=np.float32).reshape(-1, 1)

    train_sol_s, train_slv_s, train_temp_s, train_target_s, stats = _scale_split(
        train_sol,
        train_slv,
        train_temp,
        train_target,
    )
    _assert_finite_stats(stats)
    val_sol_s, val_slv_s, val_temp_s, val_target_s, _ = _scale_split(
        val_sol,
        val_slv,
        val_temp,
        val_target,
        stats=stats,
    )

    train_grad = torch.tensor(train_df["dlogS_dT"].to_numpy(dtype=np.float32).reshape(-1, 1))
    val_grad = torch.tensor(val_df["dlogS_dT"].to_numpy(dtype=np.float32).reshape(-1, 1))

    if args.disable_custom_loss or not args.compute_gradients:
        os.environ["DISABLE_CUSTOM_LOSS"] = "1"

    effective_lr = float(args.lr) * float(args.lr_scale)
    print("\n[FastSolv training]")
    print(f"  train rows: {len(train_df)}")
    print(f"  val rows:   {len(val_df)}")
    if test_df is not None:
        print(f"  test rows:  {len(test_df)}")
    print(f"  descriptor nproc: {int(args.descriptor_nproc)}")
    print(f"  effective lr: {effective_lr:.2e}")
    print(
        "  non-finite descriptor cells: "
        f"{diagnostics['nonfinite_cells_before_sanitize']} -> "
        f"{diagnostics['nonfinite_cells_after_sanitize']}"
    )
    print(
        "  non-finite logS rows filtered: "
        f"train {train_target_diag['rows_dropped']}, "
        f"val {val_target_diag['rows_dropped']}, "
        f"test {test_target_diag['rows_dropped'] if test_target_diag is not None else 0}"
    )

    NaNTolerantFastsolv = _get_nan_tolerant_fastsolv_class()
    model = NaNTolerantFastsolv(
        num_layers=int(args.num_layers),
        hidden_size=int(args.hidden_size),
        activation_fxn=args.activation,
        input_activation=args.input_activation,
        learning_rate=effective_lr,
        target_means=stats["target_means"],
        target_vars=stats["target_vars"],
        solute_means=stats["solute_means"],
        solute_vars=stats["solute_vars"],
        solvent_means=stats["solvent_means"],
        solvent_vars=stats["solvent_vars"],
        temperature_means=stats["temperature_means"],
        temperature_vars=stats["temperature_vars"],
    )

    train_ds = SolubilityDataset(train_sol_s, train_slv_s, train_temp_s, train_target_s, train_grad)
    val_ds = SolubilityDataset(val_sol_s, val_slv_s, val_temp_s, val_target_s, val_grad)
    train_loader = fastpropDataLoader(
        train_ds,
        batch_size=int(args.batch_size),
        shuffle=True,
        num_workers=0,
        persistent_workers=False,
    )
    val_loader = fastpropDataLoader(
        val_ds,
        batch_size=int(args.batch_size),
        shuffle=False,
        num_workers=0,
        persistent_workers=False,
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
        patience=int(args.patience),
    )
    trainer = Trainer(
        max_epochs=int(args.epochs),
        accelerator="auto",
        devices=1,
        callbacks=[ckpt_cb, es_cb],
        default_root_dir=str(outdir),
        log_every_n_steps=50,
        enable_progress_bar=True,
        num_sanity_val_steps=0,
        gradient_clip_val=float(args.gradient_clip_val),
        gradient_clip_algorithm="norm",
    )
    trainer.fit(model, train_loader, val_loader)

    best_checkpoint = ckpt_cb.best_model_path
    final_model = FastsolvModel.load_from_checkpoint(best_checkpoint) if best_checkpoint else model
    _save_descriptor_diagnostics(
        outdir,
        {
            **diagnostics,
            "best_checkpoint": best_checkpoint,
            "train_rows": int(len(train_df)),
            "val_rows": int(len(val_df)),
            "test_rows": int(len(test_df)) if test_df is not None else 0,
            "target_diagnostics": {
                "train": train_target_diag,
                "val": val_target_diag,
                "test": test_target_diag,
            },
        },
    )

    all_summaries: list[pd.DataFrame] = []
    split_payloads: dict[str, dict[str, Any]] = {}
    for split_name, split_df in [("val", val_df), ("test", test_df)]:
        if split_df is None or split_df.empty:
            continue
        split_sol, split_slv, split_temp = _assemble_features(split_df, desc_map)
        pred_logS = _predict_with_model(final_model, split_sol, split_slv, split_temp, batch_size=int(args.batch_size))
        artifacts = _evaluate_prediction_bundle(
            model_name="fastsolv",
            split_name=split_name,
            split_df=split_df,
            pred_logS=pred_logS,
            split_mode=split_name,
            test_data=str(getattr(args, split_name, "") or getattr(args, "test", "") or getattr(args, "val", "")),
            metadata={
                "checkpoint": best_checkpoint or "in_memory",
                "target_space": "logS",
                "descriptor_diagnostics": diagnostics,
            },
        )
        split_root = outdir / split_name
        report_path, predictions_path, summary_path = write_benchmark_artifacts(split_root, artifacts)
        all_summaries.append(artifacts.summary)
        split_payloads[split_name] = {
            "report": str(report_path),
            "predictions": str(predictions_path),
            "summary": str(summary_path),
            "overall": artifacts.report["overall"],
            "evaluation_subsets": artifacts.report.get("evaluation_subsets", {}),
            "logS_metrics": (
                ((artifacts.report.get("evaluation_subsets") or {}).get("logS_finite_subset"))
            ),
        }

    top_level = {
        "model": "fastsolv",
        "checkpoint": best_checkpoint,
        "split": build_split_metadata(split_mode=getattr(args, "split_mode", None), test_data=args.test or args.val),
        "headline_metric_space": "ln_x2",
        "logS_evaluation_policy": {
            "mode": "finite_only",
            "exclude_exact_ln_x2_eq_0": True,
            "notes": (
                "FastSolv is trained/predicted in logS, but headline bundle metrics are reported in ln_x2 "
                "on all supervised rows. logS metrics are auxiliary and restricted to rows with finite true "
                "and predicted logS."
            ),
        },
        "splits": split_payloads,
        "descriptor_diagnostics": diagnostics,
        "target_diagnostics": {
            "train": train_target_diag,
            "val": val_target_diag,
            "test": test_target_diag,
        },
    }
    (outdir / "metrics.json").write_text(json.dumps(top_level, indent=2), encoding="utf-8")
    if all_summaries:
        pd.concat(all_summaries, axis=0, ignore_index=True).to_csv(outdir / "summary.csv", index=False)
    if args.metrics:
        Path(args.metrics).parent.mkdir(parents=True, exist_ok=True)
        Path(args.metrics).write_text(json.dumps(top_level, indent=2), encoding="utf-8")
    return 0


def _tgnn_predict_ordered(
    dataset: object,
    checkpoint: str,
    batch_size: int,
    device: str | None,
) -> tuple[np.ndarray, np.ndarray]:
    import torch
    from torch.utils.data import DataLoader

    from tgnn_solv.data.dataset import collate_fn
    from tgnn_solv.inference import load_model

    dev = torch.device(device) if device else None
    model, cfg = load_model(checkpoint, device=dev)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=0,
        pin_memory=bool(dev is not None and dev.type == "cuda"),
    )
    model.eval()
    device_obj = next(model.parameters()).device
    predictions: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    with torch.no_grad():
        for sol_b, slv_b, tgt in loader:
            sol_b = sol_b.to(device_obj)
            slv_b = slv_b.to(device_obj)
            temp = tgt["T"].to(device_obj)
            output = model(
                sol_b,
                slv_b,
                temp,
                solvent_type=tgt.get("solvent_type"),
                solute_morgan_fp=tgt.get("solute_morgan_fp").to(device_obj) if hasattr(tgt.get("solute_morgan_fp"), "to") else None,
                solvent_morgan_fp=tgt.get("solvent_morgan_fp").to(device_obj) if hasattr(tgt.get("solvent_morgan_fp"), "to") else None,
                solute_descriptor_prior_features=tgt.get("solute_descriptor_prior_features").to(device_obj) if hasattr(tgt.get("solute_descriptor_prior_features"), "to") else None,
                solvent_descriptor_prior_features=tgt.get("solvent_descriptor_prior_features").to(device_obj) if hasattr(tgt.get("solvent_descriptor_prior_features"), "to") else None,
                solute_group_prior_features=tgt.get("solute_group_prior_features").to(device_obj) if hasattr(tgt.get("solute_group_prior_features"), "to") else None,
                solvent_group_prior_features=tgt.get("solvent_group_prior_features").to(device_obj) if hasattr(tgt.get("solvent_group_prior_features"), "to") else None,
                T_m_gc=tgt.get("T_m_gc").to(device_obj) if hasattr(tgt.get("T_m_gc"), "to") else None,
                dH_fus_gc=tgt.get("dH_fus_gc").to(device_obj) if hasattr(tgt.get("dH_fus_gc"), "to") else None,
                dCp_fus_gc=tgt.get("dCp_fus_gc").to(device_obj) if hasattr(tgt.get("dCp_fus_gc"), "to") else None,
            )
            predictions.append(output["ln_x2"].detach().cpu().numpy())
            masks.append(tgt["has_solubility"].cpu().numpy())
    return np.concatenate(predictions), np.concatenate(masks).astype(bool)


def run_compare(args: argparse.Namespace) -> int:
    from tgnn_solv.data.dataset import TGNNSolvDataset
    from tgnn_solv.inference import load_model

    base_df = _clean_df(pd.read_csv(args.input), require_targets=True)
    model, cfg = load_model(args.tgnn_checkpoint)
    dataset = TGNNSolvDataset(
        base_df,
        cache=True,
        use_morgan_features=cfg.use_morgan_features,
        morgan_radius=cfg.morgan_radius,
        morgan_n_bits=cfg.morgan_n_bits,
        use_descriptor_priors=cfg.use_descriptor_priors,
        use_group_priors=cfg.use_group_priors,
        use_gc_priors_crystal=cfg.use_gc_priors_crystal,
    )
    df = dataset.df.reset_index(drop=True)
    pred_tgnn, mask_tgnn = _tgnn_predict_ordered(
        dataset,
        args.tgnn_checkpoint,
        int(args.batch_size),
        args.device,
    )
    pred_fast_logS, pred_fast_std, diagnostics = _fastsolv_predict_ordered(
        df,
        checkpoint=args.fastsolv_checkpoint,
        batch_size=int(args.batch_size),
        descriptor_nproc=int(args.descriptor_nproc),
    )
    pred_fast_ln_x2 = ln_x2_from_logS(
        pd.DataFrame(
            {
                "solvent_smiles": df["solvent_smiles"],
                "logS": pred_fast_logS,
            }
        )
    ).to_numpy(dtype=float)

    has_sol = df["has_solubility"].fillna(False).astype(bool).to_numpy()
    true_ln_x2 = df["ln_x2"].to_numpy(dtype=float)
    tgnn_metrics = regression_metrics(true_ln_x2[has_sol & mask_tgnn], pred_tgnn[has_sol & mask_tgnn])
    fast_metrics = regression_metrics(true_ln_x2[has_sol], pred_fast_ln_x2[has_sol])
    result = {
        "split": build_split_metadata(split_mode=args.split_mode, test_data=args.input),
        "n_samples": int(has_sol.sum()),
        "tgnn_solv": {
            "checkpoint": args.tgnn_checkpoint,
            "ln_x2": tgnn_metrics,
        },
        "fastsolv": {
            "checkpoint": args.fastsolv_checkpoint or "pretrained_ensemble",
            "ln_x2": fast_metrics,
            "descriptor_diagnostics": diagnostics,
        },
    }
    if args.metrics:
        Path(args.metrics).parent.mkdir(parents=True, exist_ok=True)
        Path(args.metrics).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Saved metrics to {args.metrics}")
    if args.preds:
        out_df = df.copy()
        out_df["tgnn_ln_x2"] = pred_tgnn
        out_df["fastsolv_logS"] = pred_fast_logS
        out_df["fastsolv_logS_stdev"] = pred_fast_std
        out_df["fastsolv_ln_x2"] = pred_fast_ln_x2
        Path(args.preds).parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(args.preds, index=False)
        print(f"Saved predictions to {args.preds}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train or benchmark FastSolv on TGNN-Solv datasets.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    predict_p = sub.add_parser("predict", help="Run FastSolv predictions on a CSV.")
    predict_p.add_argument("--input", required=True)
    predict_p.add_argument("--output", required=True)
    predict_p.add_argument("--checkpoint", default=None, help="Optional custom FastSolv checkpoint. Defaults to the pretrained ensemble.")
    predict_p.add_argument("--metrics", default=None, help="Optional canonical report JSON path when targets are available.")
    predict_p.add_argument("--split-mode", default=None)
    predict_p.add_argument("--batch-size", type=int, default=256)
    predict_p.add_argument("--descriptor-nproc", type=int, default=1)

    train_p = sub.add_parser("train", help="Train FastSolv from scratch on repo splits.")
    train_p.add_argument("--train", required=True)
    train_p.add_argument("--val", required=True)
    train_p.add_argument("--test", default=None)
    train_p.add_argument("--outdir", required=True)
    train_p.add_argument("--epochs", type=int, default=200)
    train_p.add_argument("--batch-size", type=int, default=256)
    train_p.add_argument("--lr", type=float, default=1e-4)
    train_p.add_argument("--lr-scale", type=float, default=0.1)
    train_p.add_argument("--patience", type=int, default=20)
    train_p.add_argument("--num-layers", type=int, default=2)
    train_p.add_argument("--hidden-size", type=int, default=1800)
    train_p.add_argument("--activation", default="relu", choices=["relu", "leakyrelu"])
    train_p.add_argument("--input-activation", default="sigmoid", choices=["sigmoid", "clamp3"])
    train_p.add_argument("--compute-gradients", action="store_true")
    train_p.add_argument("--disable-custom-loss", action="store_true")
    train_p.add_argument("--gradient-clip-val", type=float, default=1.0)
    train_p.add_argument("--descriptor-nproc", type=int, default=1)
    train_p.add_argument("--metrics", default=None)
    train_p.add_argument("--split-mode", default=None)

    compare_p = sub.add_parser("compare", help="Compare TGNN-Solv against FastSolv on one test CSV.")
    compare_p.add_argument("--input", required=True)
    compare_p.add_argument("--tgnn-checkpoint", required=True)
    compare_p.add_argument("--fastsolv-checkpoint", default=None)
    compare_p.add_argument("--batch-size", type=int, default=128)
    compare_p.add_argument("--device", default=None)
    compare_p.add_argument("--split-mode", default=None)
    compare_p.add_argument("--descriptor-nproc", type=int, default=1)
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
