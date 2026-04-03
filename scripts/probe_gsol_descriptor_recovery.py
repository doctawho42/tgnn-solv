#!/usr/bin/env python3
"""Probe how much solute graph embeddings linearly recover RDKit descriptors."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from torch_geometric.data import Batch

from tgnn_solv.features import (
    RDKIT_DESCRIPTOR_NAMES,
    compute_molecular_descriptors,
    smiles_to_graph,
    smiles_to_morgan_fp,
)
from tgnn_solv.inference import load_model
from tgnn_solv.layers import make_temperature_features
from tgnn_solv.reporting import json_safe


CORE_DESCRIPTOR_NAMES = (
    "MolWt",
    "MolLogP",
    "TPSA",
    "NumHDonors",
    "NumHAcceptors",
    "NumRotatableBonds",
    "RingCount",
    "HeavyAtomCount",
    "FractionCSP3",
    "MolMR",
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract unique-solute TGNN embeddings from a checkpoint and probe "
            "their linear recoverability of RDKit descriptors using Ridge regression."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="results/medium_budget/per_model/tgnn_tuned/checkpoint.pt",
    )
    parser.add_argument(
        "--train-data",
        type=str,
        default="notebooks/data/processed/train.csv",
    )
    parser.add_argument(
        "--test-data",
        type=str,
        default="notebooks/data/processed/test.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/medium_budget/per_model/tgnn_tuned/descriptor_probe",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Use cpu by default to avoid contending with a live training run.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=512,
    )
    parser.add_argument(
        "--ridge-alpha",
        type=float,
        default=1.0,
    )
    parser.add_argument(
        "--embedding-temperature",
        type=float,
        default=298.15,
        help="Temperature fed to the encoder if the checkpoint enables encoder temperature features.",
    )
    return parser.parse_args()


def resolve_device(device_str: str) -> torch.device:
    """Resolve a requested device with a safe fallback."""
    requested = device_str.strip().lower()
    if requested.startswith("cuda") and not torch.cuda.is_available():
        print("WARNING: CUDA requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    if requested == "mps" and not torch.backends.mps.is_available():
        print("WARNING: MPS requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    return torch.device(device_str)


def load_unique_solutes(path: Path) -> list[str]:
    """Load unique valid solute SMILES from a processed split CSV."""
    df = pd.read_csv(path, low_memory=False)
    if "solute_smiles" not in df.columns:
        raise ValueError(f"{path} does not contain a 'solute_smiles' column.")
    smiles = df["solute_smiles"].astype(str).drop_duplicates().tolist()
    return [s for s in smiles if s]


def iter_chunks(values: list[str], chunk_size: int) -> list[list[str]]:
    """Chunk a list into fixed-size batches."""
    return [values[i:i + chunk_size] for i in range(0, len(values), chunk_size)]


def extract_solute_embeddings(
    *,
    model: torch.nn.Module,
    smiles_list: list[str],
    device: torch.device,
    batch_size: int,
    temperature_K: float,
) -> tuple[list[str], np.ndarray]:
    """Extract one `g_sol_pre` embedding per unique solute."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    valid_smiles: list[str] = []
    rows: list[np.ndarray] = []
    model.eval()

    with torch.no_grad():
        for smiles_chunk in iter_chunks(smiles_list, batch_size):
            graphs = []
            kept_smiles = []
            for smiles in smiles_chunk:
                graph = smiles_to_graph(smiles)
                if graph is None:
                    continue
                graphs.append(graph)
                kept_smiles.append(smiles)
            if not graphs:
                continue

            sol_batch = Batch.from_data_list(graphs).to(device)
            temperatures = torch.full(
                (len(graphs),),
                float(temperature_K),
                dtype=torch.float,
                device=device,
            )
            temp_feat = make_temperature_features(temperatures)
            encoder_t_feat = model._encoder_temp_features(temp_feat)
            _, g_sol = model._encode_and_readout(
                sol_batch,
                role="solute",
                temp_feat=encoder_t_feat,
            )

            if model.cfg.use_morgan_features:
                fps: list[np.ndarray] = []
                filtered_smiles: list[str] = []
                filtered_rows: list[torch.Tensor] = []
                for smiles, g_row in zip(kept_smiles, g_sol, strict=True):
                    fp = smiles_to_morgan_fp(
                        smiles,
                        radius=model.cfg.morgan_radius,
                        n_bits=model.cfg.morgan_n_bits,
                    )
                    if fp is None:
                        continue
                    fps.append(fp)
                    filtered_smiles.append(smiles)
                    filtered_rows.append(g_row)
                if not filtered_smiles:
                    continue
                fp_tensor = torch.tensor(
                    np.stack(fps, axis=0),
                    dtype=g_sol.dtype,
                    device=device,
                )
                g_sol = torch.stack(filtered_rows, dim=0)
                g_sol = g_sol + model.fp_pre_scale * model.solute_fp_adapter(fp_tensor)
                kept_smiles = filtered_smiles

            valid_smiles.extend(kept_smiles)
            rows.append(g_sol.detach().cpu().numpy())

    if not rows:
        raise ValueError("No valid solute embeddings could be extracted.")
    return valid_smiles, np.concatenate(rows, axis=0)


def build_descriptor_matrix(smiles_list: list[str]) -> np.ndarray:
    """Compute the full RDKit descriptor matrix for a list of molecules."""
    descriptor_rows: list[np.ndarray] = []
    invalid: list[str] = []
    for smiles in smiles_list:
        descriptors = compute_molecular_descriptors(smiles)
        if descriptors is None:
            invalid.append(smiles)
            continue
        descriptor_rows.append(descriptors.astype(np.float32, copy=False))
    if invalid:
        sample = ", ".join(invalid[:5])
        raise ValueError(
            f"Descriptor computation failed for {len(invalid)} molecules. Sample: {sample}"
        )
    return np.stack(descriptor_rows, axis=0)


def summarize_thresholds(values: np.ndarray, threshold: float, *, op: str) -> dict[str, float | int]:
    """Count how many finite values satisfy a threshold relation."""
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"count": 0, "fraction": 0.0}
    if op == "ge":
        count = int(np.sum(finite >= threshold))
    elif op == "lt":
        count = int(np.sum(finite < threshold))
    else:
        raise ValueError(f"Unsupported op: {op}")
    return {"count": count, "fraction": float(count / finite.size)}


def bottleneck_interpretation(r2_values: np.ndarray) -> str:
    """Translate descriptor recoverability into the requested qualitative conclusion."""
    finite = r2_values[np.isfinite(r2_values)]
    if finite.size == 0:
        return "No finite descriptor R² values were available."
    frac_high = float(np.mean(finite > 0.8))
    frac_low = float(np.mean(finite < 0.5))
    if frac_high > 0.5:
        return "Most descriptors exceed R² > 0.8, so the encoder likely already learned descriptor-level information."
    if frac_low > 0.5:
        return "Most descriptors fall below R² < 0.5, which points to the encoder as a likely bottleneck."
    return "Descriptor recoverability is mixed: the encoder captures some descriptor structure, but not enough to call it fully bottleneck-free."


def fit_descriptor_probes(
    *,
    X_train: np.ndarray,
    X_test: np.ndarray,
    Y_train: np.ndarray,
    Y_test: np.ndarray,
    alpha: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fit one Ridge regression per descriptor and return tabular results."""
    rows: list[dict[str, Any]] = []
    r2_values: list[float] = []

    for idx, name in enumerate(RDKIT_DESCRIPTOR_NAMES):
        y_train = Y_train[:, idx]
        y_test = Y_test[:, idx]
        train_std = float(np.std(y_train))
        test_std = float(np.std(y_test))
        train_constant = train_std < 1e-12
        test_constant = test_std < 1e-12

        if train_constant or test_constant:
            row = {
                "descriptor": name,
                "r2_test": math.nan,
                "r2_train": math.nan,
                "status": "constant_train" if train_constant else "constant_test",
                "train_mean": float(np.mean(y_train)),
                "train_std": train_std,
                "test_mean": float(np.mean(y_test)),
                "test_std": test_std,
            }
            rows.append(row)
            continue

        regressor = make_pipeline(
            StandardScaler(),
            Ridge(alpha=alpha),
        )
        regressor.fit(X_train, y_train)
        train_pred = regressor.predict(X_train)
        test_pred = regressor.predict(X_test)
        r2_train = float(r2_score(y_train, train_pred))
        r2_test = float(r2_score(y_test, test_pred))
        r2_values.append(r2_test)

        rows.append(
            {
                "descriptor": name,
                "r2_test": r2_test,
                "r2_train": r2_train,
                "status": "ok",
                "train_mean": float(np.mean(y_train)),
                "train_std": train_std,
                "test_mean": float(np.mean(y_test)),
                "test_std": test_std,
            }
        )

    results_df = pd.DataFrame(rows).sort_values(
        by=["r2_test", "descriptor"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)

    finite_r2 = results_df["r2_test"].to_numpy(dtype=float)
    finite_r2 = finite_r2[np.isfinite(finite_r2)]
    summary = {
        "n_descriptors_total": int(len(results_df)),
        "n_descriptors_with_finite_r2": int(finite_r2.size),
        "mean_r2_test": float(np.mean(finite_r2)) if finite_r2.size else None,
        "median_r2_test": float(np.median(finite_r2)) if finite_r2.size else None,
        "r2_ge_0_8": summarize_thresholds(finite_r2, 0.8, op="ge"),
        "r2_lt_0_5": summarize_thresholds(finite_r2, 0.5, op="lt"),
        "interpretation": bottleneck_interpretation(finite_r2),
    }
    return results_df, summary


def build_markdown_report(
    *,
    summary: dict[str, Any],
    results_df: pd.DataFrame,
    core_df: pd.DataFrame,
    checkpoint_path: Path,
    device: str,
    train_count: int,
    test_count: int,
) -> str:
    """Build a concise markdown report for the descriptor probe."""
    lines = [
        "# `g_sol` Descriptor Recovery Probe",
        "",
        f"- Checkpoint: `{checkpoint_path}`",
        f"- Device: `{device}`",
        f"- Unique train solutes: `{train_count}`",
        f"- Unique test solutes: `{test_count}`",
        f"- Finite descriptor R² count: `{summary['n_descriptors_with_finite_r2']}` / `{summary['n_descriptors_total']}`",
        f"- Mean test R²: `{summary['mean_r2_test']:.3f}`" if summary["mean_r2_test"] is not None else "- Mean test R²: `NA`",
        f"- Median test R²: `{summary['median_r2_test']:.3f}`" if summary["median_r2_test"] is not None else "- Median test R²: `NA`",
        f"- R² ≥ 0.8: `{summary['r2_ge_0_8']['count']}` / `{summary['n_descriptors_with_finite_r2']}` ({summary['r2_ge_0_8']['fraction']:.1%})",
        f"- R² < 0.5: `{summary['r2_lt_0_5']['count']}` / `{summary['n_descriptors_with_finite_r2']}` ({summary['r2_lt_0_5']['fraction']:.1%})",
        "",
        f"**Interpretation:** {summary['interpretation']}",
        "",
        "## Core descriptors",
        "",
        "| Descriptor | Test R² | Train R² | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in core_df.itertuples(index=False):
        test_r2 = "NA" if not math.isfinite(float(row.r2_test)) else f"{float(row.r2_test):.3f}"
        train_r2 = "NA" if not math.isfinite(float(row.r2_train)) else f"{float(row.r2_train):.3f}"
        lines.append(
            f"| {row.descriptor} | {test_r2} | {train_r2} | {row.status} |"
        )

    lines.extend(
        [
            "",
            "## Top 20 descriptors by test R²",
            "",
            "| Descriptor | Test R² |",
            "| --- | ---: |",
        ]
    )
    top_df = results_df.loc[results_df["status"] == "ok", ["descriptor", "r2_test"]].head(20)
    for row in top_df.itertuples(index=False):
        lines.append(f"| {row.descriptor} | {float(row.r2_test):.3f} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    """Run the descriptor-recovery probe end to end."""
    args = parse_args()
    checkpoint_path = Path(args.checkpoint).resolve()
    train_path = Path(args.train_data).resolve()
    test_path = Path(args.test_data).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    device = resolve_device(args.device)
    model, cfg = load_model(str(checkpoint_path), device=device)
    model.eval()

    train_solutes = load_unique_solutes(train_path)
    test_solutes = load_unique_solutes(test_path)
    overlap = sorted(set(train_solutes) & set(test_solutes))

    train_smiles, X_train = extract_solute_embeddings(
        model=model,
        smiles_list=train_solutes,
        device=device,
        batch_size=args.batch_size,
        temperature_K=args.embedding_temperature,
    )
    test_smiles, X_test = extract_solute_embeddings(
        model=model,
        smiles_list=test_solutes,
        device=device,
        batch_size=args.batch_size,
        temperature_K=args.embedding_temperature,
    )
    Y_train = build_descriptor_matrix(train_smiles)
    Y_test = build_descriptor_matrix(test_smiles)

    results_df, probe_summary = fit_descriptor_probes(
        X_train=X_train,
        X_test=X_test,
        Y_train=Y_train,
        Y_test=Y_test,
        alpha=args.ridge_alpha,
    )

    core_df = (
        results_df[results_df["descriptor"].isin(CORE_DESCRIPTOR_NAMES)]
        .set_index("descriptor")
        .reindex(CORE_DESCRIPTOR_NAMES)
        .reset_index()
    )

    np.savez_compressed(
        output_dir / "train_solute_embeddings.npz",
        smiles=np.asarray(train_smiles, dtype=object),
        embeddings=X_train.astype(np.float32, copy=False),
    )
    np.savez_compressed(
        output_dir / "test_solute_embeddings.npz",
        smiles=np.asarray(test_smiles, dtype=object),
        embeddings=X_test.astype(np.float32, copy=False),
    )
    results_df.to_csv(output_dir / "descriptor_r2.csv", index=False)

    summary_payload = {
        "checkpoint": str(checkpoint_path),
        "checkpoint_mtime_utc": pd.Timestamp(
            checkpoint_path.stat().st_mtime,
            unit="s",
            tz="UTC",
        ).isoformat(),
        "config": {
            "hidden_dim": int(cfg.hidden_dim),
            "use_temperature_in_encoder": bool(cfg.use_temperature_in_encoder),
            "use_morgan_features": bool(cfg.use_morgan_features),
            "encoder_role_mode": str(cfg.encoder_role_mode),
        },
        "probe": {
            "embedding_name": "g_sol_pre",
            "embedding_temperature_K": float(args.embedding_temperature),
            "ridge_alpha": float(args.ridge_alpha),
            "device": str(device),
        },
        "dataset": {
            "train_data": str(train_path),
            "test_data": str(test_path),
            "n_train_unique_solutes": int(len(train_smiles)),
            "n_test_unique_solutes": int(len(test_smiles)),
            "n_split_overlap_solutes": int(len(overlap)),
            "split_overlap_examples": overlap[:10],
        },
        "summary": probe_summary,
        "core_descriptors": {
            row["descriptor"]: {
                "r2_test": (
                    None if not math.isfinite(float(row["r2_test"])) else float(row["r2_test"])
                ),
                "r2_train": (
                    None if not math.isfinite(float(row["r2_train"])) else float(row["r2_train"])
                ),
                "status": str(row["status"]),
            }
            for _, row in core_df.iterrows()
        },
    }

    (output_dir / "summary.json").write_text(
        json.dumps(json_safe(summary_payload), indent=2),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        build_markdown_report(
            summary=probe_summary,
            results_df=results_df,
            core_df=core_df,
            checkpoint_path=checkpoint_path,
            device=str(device),
            train_count=len(train_smiles),
            test_count=len(test_smiles),
        ),
        encoding="utf-8",
    )

    print(f"Wrote descriptor probe outputs to {output_dir}")
    print(probe_summary["interpretation"])


if __name__ == "__main__":
    main()
