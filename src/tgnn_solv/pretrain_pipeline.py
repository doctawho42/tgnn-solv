"""Utilities for optional Stage 0 pretraining before TGNN task training."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import tempfile
from typing import Any

import pandas as pd
import torch

from .config import TGNNSolvConfig
from .model import TGNNSolv
from .pretrain import Pretrainer, download_zinc250k


def atomic_torch_save(payload: dict[str, Any], path: Path) -> None:
    """Atomically save a checkpoint to avoid partial files on interruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.tmp.",
        suffix=".pt",
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        torch.save(payload, tmp_path)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def load_pretraining_smiles(
    source: str,
    *,
    max_molecules: int | None = None,
) -> list[str]:
    """Load a SMILES corpus for Stage 0 pretraining."""
    normalized = str(source).strip()
    if not normalized:
        raise ValueError("Pretraining source must be a non-empty string.")

    if normalized.lower() == "zinc250k":
        return download_zinc250k(
            max_molecules=max_molecules if max_molecules is not None else 250000
        )

    path = Path(normalized).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Pretraining source does not exist: {path}")

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, low_memory=False)
        smiles_col = next(
            (column for column in df.columns if "smi" in column.lower()),
            None,
        )
        if smiles_col is None:
            smiles_col = df.columns[0]
        smiles = df[smiles_col].astype(str).tolist()
    else:
        smiles = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    if max_molecules is not None:
        smiles = smiles[:max_molecules]
    return smiles


def derive_pretrain_checkpoint_path(final_checkpoint_path: str | Path) -> Path:
    """Derive a default Stage 0 checkpoint path from the final model checkpoint."""
    checkpoint_path = Path(final_checkpoint_path).expanduser().resolve()
    return checkpoint_path.with_name(f"{checkpoint_path.stem}_pretrained_encoder.pt")


def build_pretrain_checkpoint_payload(
    *,
    model: TGNNSolv,
    config: TGNNSolvConfig,
    pretrain_history: dict[str, list[float]],
    pretrain_source: str,
    pretrain_epochs: int,
    pretrain_batch_size: int,
    pretrain_lr: float,
    smiles_count: int,
) -> dict[str, Any]:
    """Serialize the Stage 0 artifacts needed to warm-start a new model."""
    return {
        "format": "tgnn_solv_stage0_pretrain",
        "config": asdict(config),
        "gnn_state_dict": model.gnn.state_dict(),
        "readout_state_dict": model.readout.state_dict(),
        "pretrain_history": pretrain_history,
        "pretrain_metadata": {
            "source": pretrain_source,
            "epochs": int(pretrain_epochs),
            "batch_size": int(pretrain_batch_size),
            "lr": float(pretrain_lr),
            "smiles_count": int(smiles_count),
        },
    }


def save_pretrained_encoder_checkpoint(
    *,
    model: TGNNSolv,
    config: TGNNSolvConfig,
    output_path: str | Path,
    pretrain_history: dict[str, list[float]],
    pretrain_source: str,
    pretrain_epochs: int,
    pretrain_batch_size: int,
    pretrain_lr: float,
    smiles_count: int,
) -> Path:
    """Save the Stage 0-pretrained encoder/readout weights."""
    path = Path(output_path).expanduser().resolve()
    payload = build_pretrain_checkpoint_payload(
        model=model,
        config=config,
        pretrain_history=pretrain_history,
        pretrain_source=pretrain_source,
        pretrain_epochs=pretrain_epochs,
        pretrain_batch_size=pretrain_batch_size,
        pretrain_lr=pretrain_lr,
        smiles_count=smiles_count,
    )
    atomic_torch_save(payload, path)
    return path


def load_pretrained_encoder_checkpoint(
    path: str | Path,
    *,
    map_location: str | torch.device = "cpu",
) -> dict[str, Any]:
    """Load a saved Stage 0 checkpoint."""
    resolved = Path(path).expanduser().resolve()
    checkpoint = torch.load(resolved, map_location=map_location)
    required = {"gnn_state_dict", "readout_state_dict"}
    missing = required - set(checkpoint)
    if missing:
        raise ValueError(
            f"Pretrain checkpoint {resolved} is missing keys: {sorted(missing)}"
        )
    return checkpoint


def apply_pretrained_encoder_checkpoint(
    model: TGNNSolv,
    checkpoint: dict[str, Any],
    *,
    strict: bool = True,
) -> dict[str, Any]:
    """Load Stage 0 weights into `model.gnn` and `model.readout`."""
    gnn_load = model.gnn.load_state_dict(
        checkpoint["gnn_state_dict"],
        strict=strict,
    )
    readout_load = model.readout.load_state_dict(
        checkpoint["readout_state_dict"],
        strict=strict,
    )
    metadata = dict(checkpoint.get("pretrain_metadata") or {})
    metadata["gnn_missing_keys"] = list(gnn_load.missing_keys)
    metadata["gnn_unexpected_keys"] = list(gnn_load.unexpected_keys)
    metadata["readout_missing_keys"] = list(readout_load.missing_keys)
    metadata["readout_unexpected_keys"] = list(readout_load.unexpected_keys)
    metadata["history"] = checkpoint.get("pretrain_history")
    return metadata


def run_stage0_pretraining(
    model: TGNNSolv,
    config: TGNNSolvConfig,
    *,
    device: torch.device,
    pretrain_source: str = "zinc250k",
    pretrain_epochs: int = 30,
    pretrain_batch_size: int = 128,
    pretrain_lr: float = 3.0e-4,
    pretrain_max_molecules: int | None = None,
    save_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run Stage 0 pretraining and optionally save the encoder checkpoint."""
    smiles_list = load_pretraining_smiles(
        pretrain_source,
        max_molecules=pretrain_max_molecules,
    )
    pretrainer = Pretrainer(
        model.gnn,
        model.readout,
        config,
        device=device,
    )
    history = pretrainer.pretrain(
        smiles_list,
        n_epochs=pretrain_epochs,
        batch_size=pretrain_batch_size,
        lr=pretrain_lr,
    )
    metadata: dict[str, Any] = {
        "source": pretrain_source,
        "epochs": int(pretrain_epochs),
        "batch_size": int(pretrain_batch_size),
        "lr": float(pretrain_lr),
        "smiles_count": int(len(smiles_list)),
        "history": history,
        "checkpoint_path": None,
    }
    if save_path is not None:
        checkpoint_path = save_pretrained_encoder_checkpoint(
            model=model,
            config=config,
            output_path=save_path,
            pretrain_history=history,
            pretrain_source=pretrain_source,
            pretrain_epochs=pretrain_epochs,
            pretrain_batch_size=pretrain_batch_size,
            pretrain_lr=pretrain_lr,
            smiles_count=len(smiles_list),
        )
        metadata["checkpoint_path"] = str(checkpoint_path)
    return metadata
