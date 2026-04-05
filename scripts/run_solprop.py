#!/usr/bin/env python
"""Predict and calibrate SolProp on TGNN-Solv datasets."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from rdkit import RDLogger

from tgnn_solv.external_benchmarking import (
    BenchmarkArtifacts,
    build_benchmark_artifacts,
    ln_x2_from_logS,
    logS_from_ln_x2,
    merge_prediction_frame,
    prepare_pair_dataframe,
    regression_metrics,
    write_benchmark_artifacts,
)


RDLogger.DisableLog("rdApp.warning")
warnings.filterwarnings(
    "ignore",
    message="Creating a tensor from a list of numpy.ndarrays is extremely slow.*",
)


calculate_solubility = None
SolubilityModels = None
_MODELS_CACHE: dict[tuple[bool, bool], object] = {}
_TRAIN_RUNTIME_CACHE: dict[str, Any] = {}
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOLPROP_RUNTIME_DIR = REPO_ROOT / "benchmarks" / "external_runtimes" / "solprop_ml"


T_DEP_LOGS_COLUMNS = (
    "logS_T_from_aq_with_T_dep_Hdiss [log10(mol/L)]",
    "logS_T_from_ref_with_T_dep_Hdiss [log10(mol/L)]",
    "logS_T_from_aq_with_constant_Hdiss [log10(mol/L)]",
    "logS_T_from_ref_with_constant_Hdiss [log10(mol/L)]",
    "logS_298_from_aq [log10(mol/L)]",
    "logS_298_from_ref [log10(mol/L)]",
)
ROOM_TEMP_LOGS_COLUMNS = (
    "logS_298_from_aq [log10(mol/L)]",
    "logS_298_from_ref [log10(mol/L)]",
    "logS_T_from_aq_with_constant_Hdiss [log10(mol/L)]",
    "logS_T_from_ref_with_constant_Hdiss [log10(mol/L)]",
    "logS_T_from_aq_with_T_dep_Hdiss [log10(mol/L)]",
    "logS_T_from_ref_with_T_dep_Hdiss [log10(mol/L)]",
)
LOGS_STD_COLUMNS = {
    "logS_298_from_aq [log10(mol/L)]": "stdev_logS_298_from_aq [log10(mol/L)]",
    "logS_298_from_ref [log10(mol/L)]": "stdev_logS_298_from_ref [log10(mol/L)]",
    "logS_aq_298 [log10(mol/L)]": "stdev_logS_aq_298 [log10(mol/L)]",
}
ROOM_TEMPERATURE_K = 298.15


def _load_solprop_runtime() -> None:
    global calculate_solubility
    global SolubilityModels

    if calculate_solubility is not None and SolubilityModels is not None:
        return

    _ensure_solprop_sys_path()
    _patch_torch_load_for_solprop()

    try:
        from solvation_predictor.calculate_solubility import calculate_solubility as _calculate_solubility
        from solvation_predictor.solubility.solubility_models import SolubilityModels as _SolubilityModels
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "SolProp runtime is not available. Install the maintained stack first. "
            "The most reliable path is the upstream conda package (`conda install -c fhvermei "
            "-c conda-forge solprop_ml`) or a local extracted runtime from "
            "`python scripts/external/install_solprop_runtime.py`."
        ) from exc

    calculate_solubility = _calculate_solubility
    SolubilityModels = _SolubilityModels


def _ensure_solprop_sys_path() -> None:
    candidate_roots: list[Path] = []
    egg_env = os.environ.get("SOLPROP_EGG_PATH", "").strip()
    runtime_env = os.environ.get("SOLPROP_RUNTIME_DIR", "").strip()
    chemprop_env = os.environ.get("CHEMPROP_SOLVATION_DIR", "").strip()
    if egg_env:
        candidate_roots.append(Path(egg_env))
    if runtime_env:
        candidate_roots.append(Path(runtime_env))
    if chemprop_env:
        candidate_roots.append(Path(chemprop_env))
    candidate_roots.append(DEFAULT_SOLPROP_RUNTIME_DIR)
    candidate_roots.extend(_discover_conda_package_cache_roots())

    candidate_paths: list[Path] = []
    for root in candidate_roots:
        if not root:
            continue
        if root.is_file() and root.suffix == ".egg":
            candidate_paths.append(root)
            continue
        if not root.exists():
            continue
        site_packages = root / "site-packages"
        if site_packages.exists():
            if (site_packages / "chemprop_solvation").exists():
                candidate_paths.append(site_packages)
            if (site_packages / "solvation_predictor").exists():
                candidate_paths.append(site_packages)
        candidate_paths.extend(sorted(root.glob("site-packages/*.egg")))
        candidate_paths.extend(sorted(root.glob("*.egg")))
        if (root / "solvation_predictor").exists():
            candidate_paths.append(root)
        if (root / "chemprop_solvation").exists():
            candidate_paths.append(root)

    for path in candidate_paths:
        path_str = str(path)
        if path.exists() and path_str not in sys.path:
            sys.path.insert(0, path_str)


def _discover_conda_package_cache_roots() -> list[Path]:
    executable = Path(sys.executable).resolve()
    pkgs_dir: Path | None = None
    for parent in executable.parents:
        candidate = parent / "pkgs"
        if candidate.exists():
            pkgs_dir = candidate
            break
    if pkgs_dir is None:
        return []

    roots: list[Path] = []
    roots.extend(sorted(pkgs_dir.glob("solprop_ml-*"), reverse=True))
    roots.extend(sorted(pkgs_dir.glob("chemprop_solvation-*"), reverse=True))
    return roots


def _patch_torch_load_for_solprop() -> None:
    import torch

    if getattr(torch.load, "_tgnn_solprop_patched", False):
        return

    original_torch_load = torch.load

    def _patched_torch_load(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("weights_only", False)
        return original_torch_load(*args, **kwargs)

    _patched_torch_load._tgnn_solprop_patched = True  # type: ignore[attr-defined]
    torch.load = _patched_torch_load


def _load_solprop_models(*, reduced_number: bool, temperature_dependent: bool) -> object:
    key = (bool(reduced_number), bool(temperature_dependent))
    if key in _MODELS_CACHE:
        return _MODELS_CACHE[key]

    _load_solprop_runtime()
    try:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with (
            contextlib.redirect_stdout(stdout_buffer),
            contextlib.redirect_stderr(stderr_buffer),
        ):
            models = SolubilityModels(
                reduced_number=bool(reduced_number),
                load_g=True,
                load_h=bool(temperature_dependent),
                load_saq=True,
                load_solute=bool(temperature_dependent),
                verbose=False,
            )
    except FileNotFoundError as exc:  # pragma: no cover - depends on external package layout
        raise RuntimeError(
            "SolProp code is installed, but its pretrained model files are missing. "
            "Install the upstream conda package (`solprop_ml`) or populate the package "
            "with the required runtime assets before running this script. "
            "The maintained repo-local path is `python scripts/external/install_solprop_runtime.py`, "
            "then point the script at that extraction via `SOLPROP_RUNTIME_DIR` if needed."
        ) from exc

    _MODELS_CACHE[key] = models
    return models


def _load_solprop_train_runtime() -> dict[str, Any]:
    if _TRAIN_RUNTIME_CACHE:
        return _TRAIN_RUNTIME_CACHE

    _ensure_solprop_sys_path()
    _patch_torch_load_for_solprop()
    try:
        from solvation_predictor.data.data import DatapointList, read_data_from_df
        from solvation_predictor.data.scaler import Scaler
        from solvation_predictor.inp import InputArguments
        from solvation_predictor.models.model import Model
        from solvation_predictor.train.evaluate import evaluate as solprop_evaluate
        from solvation_predictor.train.evaluate import predict as solprop_predict
        from solvation_predictor.train.train import build_lr_scheduler
        from solvation_predictor.train.train import build_optimizer
        from solvation_predictor.train.train import get_loss_func
        from solvation_predictor.train.train import initialize_weights
        from solvation_predictor.train.train import load_checkpoint as load_native_checkpoint
        from solvation_predictor.train.train import load_input as load_native_input
        from solvation_predictor.train.train import load_scaler as load_native_scaler
        from solvation_predictor.train.train import save_checkpoint as save_native_checkpoint
        from solvation_predictor.train.train import train as solprop_train_epoch
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ImportError(
            "SolProp native training runtime is not available. Install the SolProp "
            "runtime together with the maintained baseline extras "
            "(`pip install -e \".[baselines]\"`)."
        ) from exc

    _TRAIN_RUNTIME_CACHE.update(
        {
            "DatapointList": DatapointList,
            "InputArguments": InputArguments,
            "Model": Model,
            "Scaler": Scaler,
            "build_lr_scheduler": build_lr_scheduler,
            "build_optimizer": build_optimizer,
            "evaluate": solprop_evaluate,
            "get_loss_func": get_loss_func,
            "initialize_weights": initialize_weights,
            "load_checkpoint": load_native_checkpoint,
            "load_input": load_native_input,
            "load_scaler": load_native_scaler,
            "predict": solprop_predict,
            "read_data_from_df": read_data_from_df,
            "save_checkpoint": save_native_checkpoint,
            "train_epoch": solprop_train_epoch,
        }
    )
    return _TRAIN_RUNTIME_CACHE


def _choose_logS_column(df: pd.DataFrame, *, temperature_dependent: bool) -> str | None:
    preferred = T_DEP_LOGS_COLUMNS if temperature_dependent else ROOM_TEMP_LOGS_COLUMNS
    for column in preferred:
        if column not in df.columns:
            continue
        values = pd.to_numeric(df[column], errors="coerce")
        if np.isfinite(values.to_numpy(dtype=float)).any():
            return column
    return None


def _prepare_solprop_input(
    df: pd.DataFrame,
    *,
    runtime_temperature_k: float | None = None,
) -> pd.DataFrame:
    canonical_df = prepare_pair_dataframe(df, require_targets="ln_x2" in df.columns)
    payload = canonical_df[["row_index", "solute_smiles", "solvent_smiles", "temperature"]].copy()
    payload = payload.rename(
        columns={
            "solute_smiles": "solute",
            "solvent_smiles": "solvent",
        }
    )
    if runtime_temperature_k is not None:
        payload["temperature"] = float(runtime_temperature_k)
    return payload


def _solprop_error_message(exc: Exception) -> str:
    message = " ".join(f"{exc.__class__.__name__}: {exc}".split())
    if len(message) > 320:
        return message[:317] + "..."
    return message


def _run_solprop_runtime(
    payload: pd.DataFrame,
    *,
    temperature_dependent: bool,
    reduced_number: bool,
) -> pd.DataFrame:
    models = _load_solprop_models(
        reduced_number=bool(reduced_number),
        temperature_dependent=bool(temperature_dependent),
    )
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as handle:
        export_path = Path(handle.name)
    try:
        with (
            contextlib.redirect_stdout(stdout_buffer),
            contextlib.redirect_stderr(stderr_buffer),
        ):
            calculate_solubility(
                df=payload,
                models=models,
                calculate_aqueous=True,
                calculate_Hdiss_T_dep=bool(temperature_dependent),
                reduced_number=bool(reduced_number),
                export_csv=str(export_path),
                export_detailed_csv=True,
                validate_data_list=[],
            )
        return pd.read_csv(export_path)
    except Exception as exc:
        captured = "\n".join(
            line
            for line in (stdout_buffer.getvalue() + "\n" + stderr_buffer.getvalue()).splitlines()
            if line.strip()
        )
        tail = "\n".join(captured.splitlines()[-12:])
        detail = _solprop_error_message(exc)
        if tail:
            detail = f"{detail} | log tail: {tail}"
        raise RuntimeError(detail) from exc
    finally:
        export_path.unlink(missing_ok=True)


def _build_prediction_chunk(
    chunk: pd.DataFrame,
    detailed: pd.DataFrame,
    *,
    runtime_mode: str,
    runtime_error: str | None = None,
) -> pd.DataFrame:
    if "row_index" not in detailed.columns and len(detailed) == len(chunk):
        detailed["row_index"] = chunk["row_index"].to_numpy()
    detailed["solute_smiles"] = detailed["solute"].astype(str)
    detailed["solvent_smiles"] = detailed["solvent"].astype(str)
    detailed["temperature"] = pd.to_numeric(detailed["temperature"], errors="coerce")
    selected_col = _choose_logS_column(detailed, temperature_dependent=runtime_mode == "temperature_dependent")
    detailed["solprop_logS"] = (
        pd.to_numeric(detailed[selected_col], errors="coerce")
        if selected_col is not None
        else np.nan
    )
    std_col = LOGS_STD_COLUMNS.get(selected_col or "")
    detailed["solprop_logS_stdev"] = (
        pd.to_numeric(detailed[std_col], errors="coerce")
        if std_col and std_col in detailed.columns
        else np.nan
    )
    detailed["solprop_source_column"] = selected_col or "none"
    detailed["solprop_ln_x2"] = _safe_logS_to_ln_x2(
        detailed["solvent_smiles"],
        detailed["solprop_logS"],
    )
    detailed["solprop_runtime_mode"] = runtime_mode
    detailed["solprop_runtime_error"] = runtime_error or ""
    return detailed


def _failed_prediction_chunk(
    chunk: pd.DataFrame,
    *,
    runtime_mode: str,
    runtime_error: str,
) -> pd.DataFrame:
    failed = chunk[["row_index", "solute_smiles", "solvent_smiles", "temperature"]].copy()
    failed["solprop_logS"] = np.nan
    failed["solprop_logS_stdev"] = np.nan
    failed["solprop_source_column"] = "none"
    failed["solprop_ln_x2"] = np.nan
    failed["solprop_runtime_mode"] = runtime_mode
    failed["solprop_runtime_error"] = runtime_error
    return failed


def _predict_chunk_rowwise(
    chunk: pd.DataFrame,
    *,
    temperature_dependent: bool,
    reduced_number: bool,
) -> tuple[pd.DataFrame, dict[str, int]]:
    outputs: list[pd.DataFrame] = []
    stats = {
        "rowwise_rows": 0,
        "room_temp_fallback_rows": 0,
        "failed_rows": 0,
    }
    for _, row in chunk.iterrows():
        row_df = row.to_frame().T.copy()
        stats["rowwise_rows"] += 1
        try:
            mode = "temperature_dependent" if temperature_dependent else "room_temperature_override"
            runtime_temperature = None if temperature_dependent else ROOM_TEMPERATURE_K
            detailed = _run_solprop_runtime(
                _prepare_solprop_input(row_df, runtime_temperature_k=runtime_temperature),
                temperature_dependent=bool(temperature_dependent),
                reduced_number=bool(reduced_number),
            )
            outputs.append(_build_prediction_chunk(row_df, detailed, runtime_mode=mode))
            continue
        except Exception as exc:
            primary_error = _solprop_error_message(exc)

        if temperature_dependent:
            try:
                detailed = _run_solprop_runtime(
                    _prepare_solprop_input(row_df, runtime_temperature_k=ROOM_TEMPERATURE_K),
                    temperature_dependent=False,
                    reduced_number=bool(reduced_number),
                )
                outputs.append(
                    _build_prediction_chunk(
                        row_df,
                        detailed,
                        runtime_mode="room_temperature_fallback",
                        runtime_error=primary_error,
                    )
                )
                stats["room_temp_fallback_rows"] += 1
                continue
            except Exception as fallback_exc:
                combined_error = (
                    f"temperature-dependent failed: {primary_error}; "
                    f"room-temperature fallback failed: {_solprop_error_message(fallback_exc)}"
                )
        else:
            combined_error = primary_error

        outputs.append(
            _failed_prediction_chunk(
                row_df,
                runtime_mode="failed",
                runtime_error=combined_error,
            )
        )
        stats["failed_rows"] += 1
    return pd.concat(outputs, axis=0, ignore_index=True), stats


def _safe_logS_to_ln_x2(solvent_smiles: pd.Series, logS: pd.Series) -> pd.Series:
    return ln_x2_from_logS(
        pd.DataFrame({"solvent_smiles": solvent_smiles, "logS": logS}),
        logS_col="logS",
    )


def _safe_ln_x2_to_logS(solvent_smiles: pd.Series, pred_ln_x2: np.ndarray) -> pd.Series:
    clipped = np.minimum(np.asarray(pred_ln_x2, dtype=float), np.log(0.999999))
    return logS_from_ln_x2(
        pd.DataFrame({"solvent_smiles": solvent_smiles, "ln_x2": clipped}),
        ln_x2_col="ln_x2",
    )


def _normalize_native_device(device: str) -> str:
    import torch

    requested = (device or "auto").strip().lower()
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        return "cpu"
    if requested == "mps":
        # Upstream SolProp training code only understands CPU/CUDA.
        return "cpu"
    return requested


def _build_native_solprop_frame(
    df: pd.DataFrame,
    *,
    require_targets: bool,
    include_temperature_feature: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    canonical_df = prepare_pair_dataframe(df, require_targets=require_targets).reset_index(drop=True)
    native_df = pd.DataFrame(
        {
            "mol_solvent": canonical_df["solvent_smiles"].astype(str),
            "mol_solute": canonical_df["solute_smiles"].astype(str),
        }
    )
    if include_temperature_feature:
        native_df["feature_temperature"] = pd.to_numeric(
            canonical_df["temperature"],
            errors="coerce",
        ).astype(float)
    native_df["target_ln_x2"] = (
        pd.to_numeric(canonical_df["ln_x2"], errors="coerce").astype(float)
        if require_targets
        else np.nan
    )
    return canonical_df, native_df


def _make_native_input_args(
    *,
    outdir: Path,
    num_features: int,
    epochs: int,
    batch_size: int,
    num_models: int,
    device: str,
    lr_init: float,
    lr_final: float,
    lr_max: float,
    warm_up_epochs: float,
    depth: int,
    mpn_hidden: int,
    mpn_dropout: float,
    ffn_hidden: int,
    ffn_layers: int,
    ffn_dropout: float,
):
    runtime = _load_solprop_train_runtime()
    import torch

    InputArguments = runtime["InputArguments"]
    inp = InputArguments()
    inp.output_dir = str(outdir)
    inp.property = "solvation"
    inp.num_mols = 2
    inp.num_targets = 1
    inp.num_features = int(num_features)
    inp.scale = "standard"
    inp.scale_features = bool(num_features)
    inp.use_same_scaler_for_features = True
    inp.add_hydrogens_to_solvent = False
    inp.mix = False
    inp.save_memory = False
    inp.make_plots = False
    inp.optimization = False
    inp.num_folds = 1
    inp.num_models = int(num_models)
    inp.epochs = int(epochs)
    inp.batch_size = int(batch_size)
    inp.loss_metric = "rmse"
    inp.minimize_score = True
    inp.learning_rates = (float(lr_init), float(lr_final), float(lr_max))
    inp.warm_up_epochs = min(float(warm_up_epochs), max(0.0, float(epochs) - 0.5))
    inp.lr_scheduler = "Noam"
    inp.shared = False
    inp.depth = int(depth)
    inp.mpn_hidden = int(mpn_hidden)
    inp.mpn_dropout = float(mpn_dropout)
    inp.ffn_hidden = int(ffn_hidden)
    inp.ffn_num_layers = int(ffn_layers)
    inp.ffn_dropout = float(ffn_dropout)
    inp.cuda = _normalize_native_device(device) == "cuda" and torch.cuda.is_available()
    inp.gpu = 0
    return inp


def _discover_native_checkpoint_paths(path_like: str | Path) -> list[Path]:
    root = Path(path_like)
    if root.is_file():
        return [root]
    candidates = sorted(root.rglob("model.pt"))
    if candidates:
        return candidates
    fallback = sorted(root.rglob("*.pt"))
    return fallback


def _prepare_native_dataset(
    df: pd.DataFrame,
    *,
    require_targets: bool,
    inp: Any,
    scale_with: Any | None = None,
) -> tuple[pd.DataFrame, Any]:
    runtime = _load_solprop_train_runtime()
    DatapointList = runtime["DatapointList"]
    read_data_from_df = runtime["read_data_from_df"]

    canonical_df, native_df = _build_native_solprop_frame(
        df,
        require_targets=require_targets,
        include_temperature_feature=bool(inp.num_features),
    )
    _, data_list = read_data_from_df(inp, df=native_df)
    if len(data_list) != len(canonical_df):
        raise ValueError(
            "SolProp native data preparation dropped one or more rows. "
            "Check SMILES validity and feature values before training."
        )
    dataset = DatapointList(data_list)
    if scale_with is not None:
        scale_with.transform_standard(dataset)
    return canonical_df, dataset


def _native_predict_with_checkpoints(
    checkpoint_paths: list[Path],
    df: pd.DataFrame,
    *,
    device: str,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray | None]:
    runtime = _load_solprop_train_runtime()
    load_checkpoint = runtime["load_checkpoint"]
    load_input = runtime["load_input"]
    load_scaler = runtime["load_scaler"]
    predict = runtime["predict"]

    if not checkpoint_paths:
        raise ValueError("No native SolProp checkpoints were found for prediction.")

    all_predictions: list[np.ndarray] = []
    eval_df: pd.DataFrame | None = None
    normalized_device = _normalize_native_device(device)
    for checkpoint_path in checkpoint_paths:
        inp = load_input(str(checkpoint_path))
        inp.cuda = normalized_device == "cuda"
        scaler = load_scaler(str(checkpoint_path))
        eval_df_current, dataset = _prepare_native_dataset(
            df,
            require_targets="ln_x2" in df.columns,
            inp=inp,
            scale_with=scaler,
        )
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            model = load_checkpoint(str(checkpoint_path), current_inp=inp)
        preds = np.asarray(predict(model=model, data=dataset, scaler=scaler), dtype=float).reshape(-1)
        all_predictions.append(preds)
        if eval_df is None:
            eval_df = eval_df_current

    prediction_matrix = np.vstack(all_predictions)
    mean_pred = prediction_matrix.mean(axis=0)
    std_pred = prediction_matrix.std(axis=0, ddof=0) if prediction_matrix.shape[0] > 1 else None
    assert eval_df is not None
    return eval_df, mean_pred, std_pred


def run_solprop_predictions(
    df: pd.DataFrame,
    *,
    temperature_dependent: bool,
    batch_size: int,
    reduced_number: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    base_df = prepare_pair_dataframe(df, require_targets="ln_x2" in df.columns)
    if base_df.empty:
        return base_df, {
            "rows": 0,
            "n_success": 0,
            "n_chunks": 0,
            "temperature_dependent": bool(temperature_dependent),
            "reduced_number": bool(reduced_number),
            "source_columns": {},
        }

    chunk_outputs: list[pd.DataFrame] = []
    source_columns: dict[str, int] = {}
    effective_batch = max(1, int(batch_size))
    rowwise_rows = 0
    room_temp_fallback_rows = 0
    failed_rows = 0

    for start in range(0, len(base_df), effective_batch):
        chunk = base_df.iloc[start : start + effective_batch].copy()
        try:
            runtime_mode = "temperature_dependent" if temperature_dependent else "room_temperature_override"
            runtime_temperature = None if temperature_dependent else ROOM_TEMPERATURE_K
            detailed = _run_solprop_runtime(
                _prepare_solprop_input(chunk, runtime_temperature_k=runtime_temperature),
                temperature_dependent=bool(temperature_dependent),
                reduced_number=bool(reduced_number),
            )
            chunk_outputs.append(
                _build_prediction_chunk(
                    chunk,
                    detailed,
                    runtime_mode=runtime_mode,
                )
            )
        except Exception:
            rowwise_output, rowwise_stats = _predict_chunk_rowwise(
                chunk,
                temperature_dependent=bool(temperature_dependent),
                reduced_number=bool(reduced_number),
            )
            rowwise_rows += int(rowwise_stats["rowwise_rows"])
            room_temp_fallback_rows += int(rowwise_stats["room_temp_fallback_rows"])
            failed_rows += int(rowwise_stats["failed_rows"])
            chunk_outputs.append(rowwise_output)

    prediction_frame = pd.concat(chunk_outputs, axis=0, ignore_index=True)
    for source_name, count in (
        prediction_frame["solprop_source_column"]
        .fillna("none")
        .astype(str)
        .value_counts()
        .to_dict()
        .items()
    ):
        source_columns[str(source_name)] = int(count)

    merged = merge_prediction_frame(
        base_df,
        prediction_frame,
        required_prediction_cols=["solprop_logS", "solprop_ln_x2"],
    )
    runtime_mode_counts = (
        merged.get("solprop_runtime_mode", pd.Series(dtype=str))
        .fillna("unknown")
        .astype(str)
        .value_counts()
        .to_dict()
    )
    unique_errors = [
        str(value)
        for value in merged.get("solprop_runtime_error", pd.Series(dtype=str))
        .fillna("")
        .astype(str)
        .unique()
        if str(value).strip()
    ]
    diagnostics = {
        "rows": int(len(base_df)),
        "n_success": int(np.isfinite(merged["solprop_ln_x2"].to_numpy(dtype=float)).sum()),
        "n_chunks": int(len(chunk_outputs)),
        "temperature_dependent": bool(temperature_dependent),
        "reduced_number": bool(reduced_number),
        "source_columns": source_columns,
        "runtime_modes": {str(key): int(value) for key, value in runtime_mode_counts.items()},
        "rowwise_rows": int(rowwise_rows),
        "room_temp_fallback_rows": int(room_temp_fallback_rows),
        "failed_rows": int(failed_rows),
        "errors": unique_errors[:10],
        "room_temperature_override_k": ROOM_TEMPERATURE_K if not temperature_dependent else None,
    }
    return merged, diagnostics


def _fit_calibrator(
    pred_ln_x2: np.ndarray,
    true_ln_x2: np.ndarray,
    temperatures: np.ndarray,
    *,
    include_temperature: bool,
) -> dict[str, Any]:
    from sklearn.linear_model import LinearRegression

    mask = np.isfinite(pred_ln_x2) & np.isfinite(true_ln_x2) & np.isfinite(temperatures)
    if mask.sum() < 2:
        raise ValueError("Not enough finite SolProp predictions to fit a calibrator.")
    if include_temperature:
        design = np.column_stack([pred_ln_x2[mask], temperatures[mask]])
    else:
        design = pred_ln_x2[mask].reshape(-1, 1)
    target = true_ln_x2[mask]
    model = LinearRegression().fit(design, target)
    return {
        "intercept": float(model.intercept_),
        "coef": [float(x) for x in np.atleast_1d(model.coef_)],
        "include_temperature": bool(include_temperature),
        "n_train_samples": int(mask.sum()),
    }


def _apply_calibrator(
    pred_ln_x2: np.ndarray,
    temperatures: np.ndarray,
    calibrator: dict[str, Any],
) -> np.ndarray:
    pred_ln_x2 = np.asarray(pred_ln_x2, dtype=float)
    temperatures = np.asarray(temperatures, dtype=float)
    if calibrator.get("include_temperature"):
        return (
            float(calibrator["intercept"])
            + float(calibrator["coef"][0]) * pred_ln_x2
            + float(calibrator["coef"][1]) * temperatures
        )
    return float(calibrator["intercept"]) + float(calibrator["coef"][0]) * pred_ln_x2


def _evaluate_prediction_bundle(
    *,
    model_name: str,
    split_name: str,
    split_df: pd.DataFrame,
    pred_ln_x2: np.ndarray,
    pred_logS: np.ndarray | None = None,
    uncertainty: np.ndarray | None = None,
    split_mode: str | None = None,
    test_data: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> BenchmarkArtifacts:
    eval_df = split_df.copy().reset_index(drop=True)
    if pred_logS is None:
        pred_logS = _safe_ln_x2_to_logS(eval_df["solvent_smiles"], pred_ln_x2)
    artifacts = build_benchmark_artifacts(
        model_name=model_name,
        eval_df=eval_df,
        pred_ln_x2=np.asarray(pred_ln_x2, dtype=float),
        pred_logS=np.asarray(pred_logS, dtype=float),
        uncertainty=np.asarray(uncertainty, dtype=float) if uncertainty is not None else None,
        metadata={
            **dict(metadata or {}),
            "model_family": "solprop",
            "evaluation_space": "ln_x2/logS",
            "split_name": split_name,
        },
        split_mode=split_mode or split_name,
        test_data=test_data,
    )
    artifacts.summary["split"] = split_name
    artifacts.summary["model"] = model_name
    return artifacts


def run_predict(args: argparse.Namespace) -> int:
    raw_df = pd.read_csv(args.input)
    if int(args.max_records or 0) > 0:
        raw_df = raw_df.head(int(args.max_records)).copy()
    require_targets = "ln_x2" in raw_df.columns
    df = prepare_pair_dataframe(raw_df, require_targets=require_targets)
    predictions_df, diagnostics = run_solprop_predictions(
        df,
        temperature_dependent=bool(args.temperature_dependent),
        batch_size=int(args.batch_size),
        reduced_number=bool(args.reduced_number),
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(output_path, index=False)
    print(f"Saved predictions to {output_path}")

    if args.metrics and "ln_x2" in predictions_df.columns:
        artifacts = _evaluate_prediction_bundle(
            model_name="solprop_zero_shot",
            split_name=args.split_mode or "predict",
            split_df=predictions_df,
            pred_ln_x2=predictions_df["solprop_ln_x2"].to_numpy(dtype=float),
            pred_logS=predictions_df["solprop_logS"].to_numpy(dtype=float),
            uncertainty=predictions_df["solprop_logS_stdev"].to_numpy(dtype=float),
            split_mode=args.split_mode,
            test_data=args.input,
            metadata={"diagnostics": diagnostics, "calibrated": False},
        )
        metrics_path = Path(args.metrics)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(artifacts.report, indent=2), encoding="utf-8")
        print(f"Saved report to {metrics_path}")
    return 0


def run_train(args: argparse.Namespace) -> int:
    train_df = prepare_pair_dataframe(pd.read_csv(args.train), require_targets=True)
    val_df = prepare_pair_dataframe(pd.read_csv(args.val), require_targets=True)
    test_df = prepare_pair_dataframe(pd.read_csv(args.test), require_targets=True) if args.test else None

    train_pred, train_diag = run_solprop_predictions(
        train_df,
        temperature_dependent=bool(args.temperature_dependent),
        batch_size=int(args.batch_size),
        reduced_number=bool(args.reduced_number),
    )
    val_pred, val_diag = run_solprop_predictions(
        val_df,
        temperature_dependent=bool(args.temperature_dependent),
        batch_size=int(args.batch_size),
        reduced_number=bool(args.reduced_number),
    )
    test_pred, test_diag = (
        run_solprop_predictions(
            test_df,
            temperature_dependent=bool(args.temperature_dependent),
            batch_size=int(args.batch_size),
            reduced_number=bool(args.reduced_number),
        )
        if test_df is not None
        else (None, {})
    )

    calibrator = _fit_calibrator(
        train_pred["solprop_ln_x2"].to_numpy(dtype=float),
        train_pred["ln_x2"].to_numpy(dtype=float),
        train_pred["temperature"].to_numpy(dtype=float),
        include_temperature=bool(args.include_temperature),
    )
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "calibrator.json").write_text(json.dumps(calibrator, indent=2), encoding="utf-8")

    train_cal = _apply_calibrator(
        train_pred["solprop_ln_x2"].to_numpy(dtype=float),
        train_pred["temperature"].to_numpy(dtype=float),
        calibrator,
    )
    metrics_payload: dict[str, Any] = {
        "model_family": "solprop",
        "temperature_dependent": bool(args.temperature_dependent),
        "include_temperature": bool(args.include_temperature),
        "reduced_number": bool(args.reduced_number),
        "calibrator": calibrator,
        "diagnostics": {
            "train": train_diag,
            "val": val_diag,
            "test": test_diag,
        },
        "train": {
            "raw": regression_metrics(
                train_pred["ln_x2"].to_numpy(dtype=float),
                train_pred["solprop_ln_x2"].to_numpy(dtype=float),
            ),
            "calibrated": regression_metrics(
                train_pred["ln_x2"].to_numpy(dtype=float),
                train_cal,
            ),
        },
        "splits": {},
    }

    all_summaries: list[pd.DataFrame] = []
    for split_name, split_df, split_path in (
        ("val", val_pred, args.val),
        ("test", test_pred, args.test),
    ):
        if split_df is None or split_df.empty:
            continue

        raw_artifacts = _evaluate_prediction_bundle(
            model_name="solprop_zero_shot",
            split_name=split_name,
            split_df=split_df,
            pred_ln_x2=split_df["solprop_ln_x2"].to_numpy(dtype=float),
            pred_logS=split_df["solprop_logS"].to_numpy(dtype=float),
            uncertainty=split_df["solprop_logS_stdev"].to_numpy(dtype=float),
            split_mode=split_name,
            test_data=split_path,
            metadata={"calibrated": False, "diagnostics": {"train": train_diag, split_name: metrics_payload["diagnostics"].get(split_name)}},
        )
        raw_root = outdir / split_name / "raw"
        raw_report_path, raw_predictions_path, raw_summary_path = write_benchmark_artifacts(raw_root, raw_artifacts)
        all_summaries.append(raw_artifacts.summary)

        calibrated_ln_x2 = _apply_calibrator(
            split_df["solprop_ln_x2"].to_numpy(dtype=float),
            split_df["temperature"].to_numpy(dtype=float),
            calibrator,
        )
        calibrated_logS = _safe_ln_x2_to_logS(split_df["solvent_smiles"], calibrated_ln_x2)
        calibrated_artifacts = _evaluate_prediction_bundle(
            model_name="solprop_calibrated",
            split_name=split_name,
            split_df=split_df,
            pred_ln_x2=calibrated_ln_x2,
            pred_logS=calibrated_logS.to_numpy(dtype=float),
            split_mode=split_name,
            test_data=split_path,
            metadata={"calibrated": True, "calibrator": calibrator},
        )
        cal_root = outdir / split_name / "calibrated"
        cal_report_path, cal_predictions_path, cal_summary_path = write_benchmark_artifacts(cal_root, calibrated_artifacts)
        all_summaries.append(calibrated_artifacts.summary)

        export_df = split_df.copy()
        export_df["solprop_calibrated_ln_x2"] = calibrated_ln_x2
        export_df["solprop_calibrated_logS"] = calibrated_logS.to_numpy(dtype=float)
        export_df.to_csv(outdir / f"solprop_{split_name}_predictions.csv", index=False)

        metrics_payload["splits"][split_name] = {
            "raw": {
                "overall": raw_artifacts.report["overall"],
                "report": str(raw_report_path),
                "predictions": str(raw_predictions_path),
                "summary": str(raw_summary_path),
            },
            "calibrated": {
                "overall": calibrated_artifacts.report["overall"],
                "report": str(cal_report_path),
                "predictions": str(cal_predictions_path),
                "summary": str(cal_summary_path),
            },
        }

    if all_summaries:
        pd.concat(all_summaries, axis=0, ignore_index=True).to_csv(outdir / "summary.csv", index=False)
    metrics_path = outdir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    if args.metrics:
        explicit_metrics = Path(args.metrics)
        explicit_metrics.parent.mkdir(parents=True, exist_ok=True)
        explicit_metrics.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    print(f"Saved calibrated SolProp benchmark bundle to {outdir}")
    return 0


def run_native_predict(args: argparse.Namespace) -> int:
    raw_df = pd.read_csv(args.input)
    if int(args.max_records or 0) > 0:
        raw_df = raw_df.head(int(args.max_records)).copy()
    checkpoint_paths = _discover_native_checkpoint_paths(args.checkpoint_dir)
    eval_df, pred_ln_x2, pred_std = _native_predict_with_checkpoints(
        checkpoint_paths,
        raw_df,
        device=args.device,
    )
    predictions_df = eval_df.copy()
    predictions_df["solprop_native_ln_x2"] = pred_ln_x2
    predictions_df["solprop_native_logS"] = _safe_ln_x2_to_logS(
        predictions_df["solvent_smiles"],
        pred_ln_x2,
    ).to_numpy(dtype=float)
    if pred_std is not None:
        predictions_df["solprop_native_std"] = pred_std
    predictions_df["solprop_native_n_models"] = len(checkpoint_paths)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(output_path, index=False)
    print(f"Saved native SolProp predictions to {output_path}")

    if args.metrics and "ln_x2" in predictions_df.columns:
        artifacts = _evaluate_prediction_bundle(
            model_name="solprop_native",
            split_name=args.split_mode or "predict_native",
            split_df=predictions_df,
            pred_ln_x2=pred_ln_x2,
            pred_logS=predictions_df["solprop_native_logS"].to_numpy(dtype=float),
            uncertainty=pred_std,
            split_mode=args.split_mode,
            test_data=args.input,
            metadata={
                "native_retrain": True,
                "n_models": len(checkpoint_paths),
                "checkpoint_dir": str(Path(args.checkpoint_dir)),
                "temperature_feature": True,
                "target_space": "ln_x2",
            },
        )
        metrics_path = Path(args.metrics)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(artifacts.report, indent=2), encoding="utf-8")
        print(f"Saved native SolProp report to {metrics_path}")
    return 0


def run_native_train(args: argparse.Namespace) -> int:
    runtime = _load_solprop_train_runtime()
    import torch
    from torch.optim.lr_scheduler import ExponentialLR, StepLR

    build_lr_scheduler = runtime["build_lr_scheduler"]
    build_optimizer = runtime["build_optimizer"]
    evaluate = runtime["evaluate"]
    get_loss_func = runtime["get_loss_func"]
    initialize_weights = runtime["initialize_weights"]
    load_checkpoint = runtime["load_checkpoint"]
    save_checkpoint = runtime["save_checkpoint"]
    train_epoch = runtime["train_epoch"]

    train_df = prepare_pair_dataframe(pd.read_csv(args.train), require_targets=True)
    val_df = prepare_pair_dataframe(pd.read_csv(args.val), require_targets=True)
    test_df = prepare_pair_dataframe(pd.read_csv(args.test), require_targets=True) if args.test else None

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    inp = _make_native_input_args(
        outdir=outdir,
        num_features=1,
        epochs=int(args.epochs),
        batch_size=int(args.batch_size),
        num_models=int(args.num_models),
        device=args.device,
        lr_init=float(args.lr_init),
        lr_final=float(args.lr_final),
        lr_max=float(args.lr_max),
        warm_up_epochs=float(args.warm_up_epochs),
        depth=int(args.depth),
        mpn_hidden=int(args.mpn_hidden),
        mpn_dropout=float(args.mpn_dropout),
        ffn_hidden=int(args.ffn_hidden),
        ffn_layers=int(args.ffn_layers),
        ffn_dropout=float(args.ffn_dropout),
    )

    _, train_dataset = _prepare_native_dataset(train_df, require_targets=True, inp=inp)
    _, val_dataset = _prepare_native_dataset(val_df, require_targets=True, inp=inp)
    _, test_dataset = (
        _prepare_native_dataset(test_df, require_targets=True, inp=inp)
        if test_df is not None
        else (None, None)
    )

    train_size = len(train_dataset.get_data())
    if train_size <= 0:
        raise ValueError("Native SolProp training received an empty training split.")
    inp.batch_size = max(1, min(int(inp.batch_size), int(train_size)))
    inp.warm_up_epochs = min(float(inp.warm_up_epochs), max(0.0, float(inp.epochs) - 0.5))

    Scaler = runtime["Scaler"]
    scaler = Scaler(data=train_dataset, scale_features=inp.scale_features)
    scaler.transform_standard(train_dataset)
    scaler.transform_standard(val_dataset)
    if test_dataset is not None:
        scaler.transform_standard(test_dataset)

    loss_func = get_loss_func(inp.loss_metric)
    histories: list[dict[str, Any]] = []
    checkpoint_paths: list[Path] = []

    for model_i in range(int(args.num_models)):
        model_dir = outdir / "fold_0" / f"model{model_i}"
        model_dir.mkdir(parents=True, exist_ok=True)
        with (
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            model = runtime["Model"](inp)
        initialize_weights(model, seed=int(args.seed) + model_i)
        if inp.cuda:
            model = model.cuda()
        optimizer = build_optimizer(model, inp.learning_rates[0])
        scheduler = build_lr_scheduler(optimizer, inp, len(train_dataset.get_data()))

        checkpoint_path = model_dir / "model.pt"
        save_checkpoint(str(checkpoint_path), model, inp, scaler)

        best_score = float("inf")
        best_epoch = -1
        epochs_without_improve = 0
        model_history: list[dict[str, float]] = []
        for epoch in range(int(args.epochs)):
            _, train_loss = train_epoch(
                model=model,
                data=train_dataset,
                loss_func=loss_func,
                optimizer=optimizer,
                scheduler=scheduler,
                inp=inp,
            )
            if isinstance(scheduler, (ExponentialLR, StepLR)):
                scheduler.step(epoch=epoch)

            val_scores = evaluate(model=model, data=val_dataset, metric_func=inp.loss_metric, scaler=scaler)
            val_score = float(np.nanmean(val_scores))
            learning_rate = float(optimizer.param_groups[0]["lr"])
            model_history.append(
                {
                    "epoch": float(epoch),
                    "train_loss_raw": float(train_loss),
                    "val_rmse": float(val_score),
                    "lr": learning_rate,
                }
            )
            if np.isfinite(val_score) and val_score < best_score:
                best_score = float(val_score)
                best_epoch = int(epoch)
                save_checkpoint(str(checkpoint_path), model, inp, scaler)
                epochs_without_improve = 0
            else:
                epochs_without_improve += 1
                if int(args.patience) > 0 and epochs_without_improve >= int(args.patience):
                    break

        histories.append(
            {
                "model_index": model_i,
                "checkpoint": str(checkpoint_path),
                "best_epoch": best_epoch,
                "best_val_rmse": best_score,
                "history": model_history,
            }
        )
        checkpoint_paths.append(checkpoint_path)

    train_pred_df, train_pred_ln_x2, train_pred_std = _native_predict_with_checkpoints(
        checkpoint_paths,
        train_df,
        device=args.device,
    )
    val_pred_df, val_pred_ln_x2, val_pred_std = _native_predict_with_checkpoints(
        checkpoint_paths,
        val_df,
        device=args.device,
    )
    test_bundle = (
        _native_predict_with_checkpoints(checkpoint_paths, test_df, device=args.device)
        if test_df is not None
        else None
    )

    metrics_payload: dict[str, Any] = {
        "model_family": "solprop",
        "native_retrain": True,
        "target_space": "ln_x2",
        "temperature_feature": True,
        "n_models": len(checkpoint_paths),
        "device": _normalize_native_device(args.device),
        "checkpoint_paths": [str(path) for path in checkpoint_paths],
        "config": {
            "epochs": int(args.epochs),
            "patience": int(args.patience),
            "batch_size": int(args.batch_size),
            "learning_rates": [float(args.lr_init), float(args.lr_final), float(args.lr_max)],
            "warm_up_epochs": float(args.warm_up_epochs),
            "depth": int(args.depth),
            "mpn_hidden": int(args.mpn_hidden),
            "mpn_dropout": float(args.mpn_dropout),
            "ffn_hidden": int(args.ffn_hidden),
            "ffn_layers": int(args.ffn_layers),
            "ffn_dropout": float(args.ffn_dropout),
            "seed": int(args.seed),
        },
        "training_history": histories,
        "train_metrics": regression_metrics(
            train_pred_df["ln_x2"].to_numpy(dtype=float),
            train_pred_ln_x2,
        ),
        "splits": {},
    }

    all_summaries: list[pd.DataFrame] = []
    split_payloads: list[tuple[str, pd.DataFrame, np.ndarray, np.ndarray | None, str | None]] = [
        ("val", val_pred_df, val_pred_ln_x2, val_pred_std, args.val),
    ]
    if test_bundle is not None:
        split_payloads.append(("test", test_bundle[0], test_bundle[1], test_bundle[2], args.test))

    for split_name, split_df, pred_ln_x2, pred_std, split_path in split_payloads:
        artifacts = _evaluate_prediction_bundle(
            model_name="solprop_native",
            split_name=split_name,
            split_df=split_df,
            pred_ln_x2=pred_ln_x2,
            pred_logS=_safe_ln_x2_to_logS(split_df["solvent_smiles"], pred_ln_x2).to_numpy(dtype=float),
            uncertainty=pred_std,
            split_mode=split_name,
            test_data=split_path,
            metadata={
                "native_retrain": True,
                "n_models": len(checkpoint_paths),
                "target_space": "ln_x2",
                "temperature_feature": True,
            },
        )
        split_root = outdir / split_name
        report_path, predictions_path, summary_path = write_benchmark_artifacts(split_root, artifacts)
        all_summaries.append(artifacts.summary)
        metrics_payload["splits"][split_name] = {
            "overall": artifacts.report["overall"],
            "report": str(report_path),
            "predictions": str(predictions_path),
            "summary": str(summary_path),
        }

    if all_summaries:
        pd.concat(all_summaries, axis=0, ignore_index=True).to_csv(outdir / "summary.csv", index=False)
    metrics_path = outdir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    if args.metrics:
        explicit_metrics = Path(args.metrics)
        explicit_metrics.parent.mkdir(parents=True, exist_ok=True)
        explicit_metrics.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    print(f"Saved native SolProp training bundle to {outdir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SolProp zero-shot, calibrated, or native-retrained baselines on TGNN-Solv datasets."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    pred = sub.add_parser("predict", help="Run zero-shot SolProp predictions on a CSV.")
    pred.add_argument("--input", required=True)
    pred.add_argument("--output", required=True)
    pred.add_argument("--metrics", default=None, help="Optional canonical report JSON when targets are present.")
    pred.add_argument("--split-mode", default=None)
    pred.add_argument(
        "--temperature-dependent",
        action="store_true",
        help=(
            "Attempt SolProp's upstream temperature-dependent runtime. "
            "Without this flag the wrapper uses room-temperature inference at 298.15 K, "
            "which is the maintained stable comparison mode on TGNN-Solv splits."
        ),
    )
    pred.add_argument("--batch-size", type=int, default=256)
    pred.add_argument("--max-records", type=int, default=0)
    pred.add_argument("--reduced-number", action="store_true", help="Use the reduced-number SolProp ensemble.")

    train = sub.add_parser("train", help="Fit a train-set calibration on top of SolProp predictions.")
    train.add_argument("--train", required=True)
    train.add_argument("--val", required=True)
    train.add_argument("--test", default=None)
    train.add_argument("--outdir", required=True)
    train.add_argument("--metrics", default=None)
    train.add_argument(
        "--temperature-dependent",
        action="store_true",
        help=(
            "Attempt SolProp's upstream temperature-dependent runtime before calibration. "
            "Without this flag the wrapper calibrates room-temperature SolProp predictions "
            "against the split's actual temperatures."
        ),
    )
    train.add_argument("--include-temperature", action="store_true", help="Include temperature as a calibrator feature.")
    train.add_argument("--batch-size", type=int, default=256)
    train.add_argument("--reduced-number", action="store_true", help="Use the reduced-number SolProp ensemble.")

    native_pred = sub.add_parser("predict-native", help="Run native-retrained SolProp checkpoints on a CSV.")
    native_pred.add_argument("--checkpoint-dir", required=True, help="Directory containing `model.pt` checkpoints or a single checkpoint path.")
    native_pred.add_argument("--input", required=True)
    native_pred.add_argument("--output", required=True)
    native_pred.add_argument("--metrics", default=None)
    native_pred.add_argument("--split-mode", default=None)
    native_pred.add_argument("--device", default="auto", help="`auto`, `cpu`, or `cuda`. MPS falls back to CPU because upstream SolProp training code is CUDA-only.")
    native_pred.add_argument("--max-records", type=int, default=0)

    native_train = sub.add_parser("train-native", help="Train the native SolProp architecture directly on TGNN-Solv `ln(x2)` targets.")
    native_train.add_argument("--train", required=True)
    native_train.add_argument("--val", required=True)
    native_train.add_argument("--test", default=None)
    native_train.add_argument("--outdir", required=True)
    native_train.add_argument("--metrics", default=None)
    native_train.add_argument("--device", default="auto", help="`auto`, `cpu`, or `cuda`. Native SolProp training only supports CPU/CUDA.")
    native_train.add_argument("--epochs", type=int, default=40)
    native_train.add_argument("--patience", type=int, default=10)
    native_train.add_argument("--batch-size", type=int, default=32)
    native_train.add_argument("--num-models", type=int, default=5)
    native_train.add_argument("--seed", type=int, default=42)
    native_train.add_argument("--lr-init", type=float, default=1e-3)
    native_train.add_argument("--lr-final", type=float, default=1e-4)
    native_train.add_argument("--lr-max", type=float, default=1e-3)
    native_train.add_argument("--warm-up-epochs", type=float, default=2.0)
    native_train.add_argument("--depth", type=int, default=4)
    native_train.add_argument("--mpn-hidden", type=int, default=200)
    native_train.add_argument("--mpn-dropout", type=float, default=0.0)
    native_train.add_argument("--ffn-hidden", type=int, default=500)
    native_train.add_argument("--ffn-layers", type=int, default=4)
    native_train.add_argument("--ffn-dropout", type=float, default=0.0)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.cmd == "predict":
        return run_predict(args)
    if args.cmd == "train":
        return run_train(args)
    if args.cmd == "predict-native":
        return run_native_predict(args)
    if args.cmd == "train-native":
        return run_native_train(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
