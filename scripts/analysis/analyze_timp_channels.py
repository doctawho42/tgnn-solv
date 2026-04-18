#!/usr/bin/env python
"""Analyze what TIMP dispersive and polar channels encode."""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
for candidate in (SCRIPTS, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import _bootstrap  # noqa: F401,E402
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from tgnn_solv.data.dataset import make_loader
from tgnn_solv.features import RDKIT_DESCRIPTOR_NAMES, compute_molecular_descriptors
from tgnn_solv.hansen_contrastive import pseudo_hansen_from_smiles
from tgnn_solv.inference import load_model


DESCRIPTOR_TARGETS = ("MolLogP", "TPSA", "NumHDonors", "MolWt")
MIN_LABELLED_TRAIN = 12
MIN_LABELLED_TEST = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run channel-specific probes and norm diagnostics for a TIMP checkpoint.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--test-data", required=True)
    parser.add_argument("--train-data", default=None, help="Optional train CSV. If omitted, test solutes are split internally.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _resolve_device(raw: str) -> torch.device:
    if raw == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    if raw == "mps" and not torch.backends.mps.is_available():
        print("[timp-channels] MPS unavailable, falling back to CPU.")
        return torch.device("cpu")
    return torch.device(raw)


def _loader(df: pd.DataFrame, cfg, batch_size: int, seed: int):
    local_cfg = cfg
    old_batch_size = int(local_cfg.batch_size)
    local_cfg.batch_size = int(batch_size)
    try:
        return make_loader(
            df,
            batch_size=batch_size,
            shuffle=False,
            num_workers=0,
            cache=True,
            drop_last=False,
            use_pair_temperature_batching=False,
            use_morgan_features=cfg.use_morgan_features,
            morgan_radius=cfg.morgan_radius,
            morgan_n_bits=cfg.morgan_n_bits,
            use_descriptor_augmentation=cfg.use_descriptor_augmentation,
            use_descriptor_priors=cfg.use_descriptor_priors,
            use_group_priors=cfg.requires_group_prior_features,
            use_gc_priors_crystal=cfg.use_gc_priors_crystal,
            use_gasteiger_charges=cfg.use_gasteiger_charges,
            use_phys_edge_features=cfg.use_phys_edge_features,
            explicit_h_small_molecules=cfg.explicit_h_small_molecules,
            explicit_h_max_heavy_atoms=cfg.explicit_h_max_heavy_atoms,
            use_pseudo_hansen=(cfg.use_hansen_contrastive or cfg.use_hansen_delta_loss) and cfg.use_pseudo_hansen,
            pseudo_hansen_weight_discount=cfg.pseudo_hansen_weight_discount,
            seed=seed,
        )
    finally:
        local_cfg.batch_size = old_batch_size


def _move_targets(targets: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {
        key: value.to(device) if isinstance(value, torch.Tensor) else value
        for key, value in targets.items()
    }


def _optional(targets: dict[str, Any], key: str):
    value = targets.get(key)
    return value if isinstance(value, torch.Tensor) else None


def _unique_solute_df(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if "solute_smiles" not in df.columns:
        raise ValueError(f"{path} lacks solute_smiles.")
    return df.drop_duplicates("solute_smiles", keep="first").reset_index(drop=True)


def _infer_train_csv(test_path: str | Path) -> Path | None:
    test_path = Path(test_path).expanduser().resolve()
    candidate = test_path.with_name("train.csv")
    if candidate.exists() and candidate != test_path:
        return candidate
    return None


@lru_cache(maxsize=50000)
def _descriptor_row(smiles: str) -> dict[str, float] | None:
    values = compute_molecular_descriptors(smiles)
    if values is None:
        return None
    return {
        name: float(values[idx])
        for idx, name in enumerate(RDKIT_DESCRIPTOR_NAMES)
        if name in DESCRIPTOR_TARGETS
    }


def _collect(model, cfg, csv_path: str | Path, device: torch.device, batch_size: int, seed: int) -> pd.DataFrame:
    df = _unique_solute_df(csv_path)
    loader = _loader(df, cfg, batch_size, seed)
    rows: list[dict[str, Any]] = []
    model.eval()
    with torch.no_grad():
        for sol_batch, slv_batch, targets in loader:
            sol_batch = sol_batch.to(device)
            slv_batch = slv_batch.to(device)
            targets_dev = _move_targets(targets, device)
            output = model(
                sol_batch,
                slv_batch,
                targets_dev["T"],
                solvent_type=_optional(targets_dev, "solvent_type"),
                solute_morgan_fp=_optional(targets_dev, "solute_morgan_fp"),
                solvent_morgan_fp=_optional(targets_dev, "solvent_morgan_fp"),
                solute_descriptors=_optional(targets_dev, "solute_descriptors"),
                solvent_descriptors=_optional(targets_dev, "solvent_descriptors"),
                solute_descriptor_prior_features=_optional(targets_dev, "solute_descriptor_prior_features"),
                solvent_descriptor_prior_features=_optional(targets_dev, "solvent_descriptor_prior_features"),
                solute_group_prior_features=_optional(targets_dev, "solute_group_prior_features"),
                solvent_group_prior_features=_optional(targets_dev, "solvent_group_prior_features"),
                T_m_gc=_optional(targets_dev, "T_m_gc"),
                dH_fus_gc=_optional(targets_dev, "dH_fus_gc"),
                dCp_fus_gc=_optional(targets_dev, "dCp_fus_gc"),
                targets=targets_dev,
                return_intermediates=True,
            )
            if not isinstance(output, tuple):
                raise ValueError("Expected TIMP model to return intermediates.")
            _, intermediates = output
            if "g_sol_disp_pre" not in intermediates or "g_sol_polar_pre" not in intermediates:
                raise ValueError("Checkpoint did not expose TIMP channel embeddings.")
            g_disp = intermediates["g_sol_disp_pre"].detach().cpu().numpy()
            g_polar = intermediates["g_sol_polar_pre"].detach().cpu().numpy()
            hansen = targets["hansen_sol"].detach().cpu().numpy()
            hansen_mask = targets["hansen_mask"].detach().cpu().numpy().astype(bool)
            smiles_values = targets["solute_smiles"]
            for i, smiles in enumerate(smiles_values):
                smiles_str = str(smiles)
                desc = _descriptor_row(smiles_str)
                if desc is None:
                    continue
                pseudo = pseudo_hansen_from_smiles(smiles_str)
                if pseudo is None:
                    pseudo = (np.nan, np.nan, np.nan)
                rows.append(
                    {
                        "solute_smiles": smiles_str,
                        "g_disp": g_disp[i].astype(np.float32),
                        "g_polar": g_polar[i].astype(np.float32),
                        "has_hansen": bool(hansen_mask[i]),
                        "delta_d": float(hansen[i, 0]) if hansen_mask[i] else np.nan,
                        "delta_p": float(hansen[i, 1]) if hansen_mask[i] else np.nan,
                        "delta_h": float(hansen[i, 2]) if hansen_mask[i] else np.nan,
                        "pseudo_delta_d": float(pseudo[0]),
                        "pseudo_delta_p": float(pseudo[1]),
                        "pseudo_delta_h": float(pseudo[2]),
                        **desc,
                    }
                )
    if not rows:
        raise ValueError(f"No TIMP channel rows collected from {csv_path}.")
    return pd.DataFrame(rows)


def _stack(df: pd.DataFrame, column: str) -> np.ndarray:
    return np.stack(df[column].to_list()).astype(np.float32, copy=False)


def _probe_r2(X_train: np.ndarray, X_test: np.ndarray, y_train: np.ndarray, y_test: np.ndarray) -> float:
    mask_train = np.isfinite(y_train)
    mask_test = np.isfinite(y_test)
    if int(mask_train.sum()) < 5 or int(mask_test.sum()) < 3:
        return float("nan")
    if float(np.std(y_train[mask_train])) < 1.0e-12 or float(np.std(y_test[mask_test])) < 1.0e-12:
        return float("nan")
    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    model.fit(X_train[mask_train], y_train[mask_train])
    pred = model.predict(X_test[mask_test])
    return float(r2_score(y_test[mask_test], pred))


def _select_target(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    actual_col: str,
    pseudo_col: str,
    display_name: str,
) -> tuple[str, str, str, int, int]:
    actual_train = int(pd.to_numeric(train_df[actual_col], errors="coerce").notna().sum())
    actual_test = int(pd.to_numeric(test_df[actual_col], errors="coerce").notna().sum())
    if actual_train >= MIN_LABELLED_TRAIN and actual_test >= MIN_LABELLED_TEST:
        return actual_col, display_name, "experimental", actual_train, actual_test
    return pseudo_col, f"псевдо-{display_name}", "pseudo", actual_train, actual_test


def _build_probe_matrix(train_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.DataFrame:
    Xd_train = _stack(train_df, "g_disp")
    Xd_test = _stack(test_df, "g_disp")
    Xp_train = _stack(train_df, "g_polar")
    Xp_test = _stack(test_df, "g_polar")
    targets = [
        ("delta_d", "pseudo_delta_d", r"$\delta_d$"),
        ("delta_p", "pseudo_delta_p", r"$\delta_p$"),
        ("delta_h", "pseudo_delta_h", r"$\delta_h$"),
    ]
    rows: list[dict[str, Any]] = []
    for actual_col, pseudo_col, display_name in targets:
        target, label, source, actual_train, actual_test = _select_target(
            train_df,
            test_df,
            actual_col,
            pseudo_col,
            display_name,
        )
        y_train = pd.to_numeric(train_df[target], errors="coerce").to_numpy(dtype=float)
        y_test = pd.to_numeric(test_df[target], errors="coerce").to_numpy(dtype=float)
        rows.append(
            {
                "target": label,
                "disp_R2": _probe_r2(Xd_train, Xd_test, y_train, y_test),
                "polar_R2": _probe_r2(Xp_train, Xp_test, y_train, y_test),
                "source": source,
                "actual_train_count": actual_train,
                "actual_test_count": actual_test,
            }
        )
    for target in DESCRIPTOR_TARGETS:
        y_train = pd.to_numeric(train_df[target], errors="coerce").to_numpy(dtype=float)
        y_test = pd.to_numeric(test_df[target], errors="coerce").to_numpy(dtype=float)
        rows.append(
            {
                "target": target,
                "disp_R2": _probe_r2(Xd_train, Xd_test, y_train, y_test),
                "polar_R2": _probe_r2(Xp_train, Xp_test, y_train, y_test),
                "source": "descriptor",
                "actual_train_count": int(np.isfinite(y_train).sum()),
                "actual_test_count": int(np.isfinite(y_test).sum()),
            }
        )
    return pd.DataFrame(rows)


def _plot_probe_matrix(matrix: pd.DataFrame, output_dir: Path) -> None:
    values = matrix[["disp_R2", "polar_R2"]].to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(6.7, 4.9))
    im = ax.imshow(values, cmap="RdYlBu", vmin=-0.2, vmax=1.0, aspect="auto")
    ax.set_xticks([0, 1], ["дисперсия", "полярность"])
    ax.set_yticks(np.arange(len(matrix)), matrix["target"].tolist())
    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            label = "NA" if not np.isfinite(values[i, j]) else f"{values[i, j]:.2f}"
            color = "white" if np.isfinite(values[i, j]) and values[i, j] > 0.52 else "#24333E"
            ax.text(j, i, label, ha="center", va="center", fontsize=9, color=color)
    ax.set_title("Что линейно читается из TIMP-каналов")
    fig.colorbar(im, ax=ax, label="$R^2$")
    fig.text(
        0.02,
        0.02,
        "Если в тесте недостаточно экспериментальных Hansen-меток,\nиспользуется явно помеченный псевдо-Hansen-прокси.",
        fontsize=8.5,
        color="#4C5A67",
    )
    fig.savefig(output_dir / "timp_channel_probe_matrix.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "timp_channel_probe_matrix.png", dpi=220, bbox_inches="tight")


def _plot_ratio(test_df: pd.DataFrame, output_dir: Path) -> float:
    disp_norm = np.linalg.norm(_stack(test_df, "g_disp"), axis=1)
    polar_norm = np.linalg.norm(_stack(test_df, "g_polar"), axis=1)
    ratio = disp_norm / np.clip(disp_norm + polar_norm, 1.0e-12, None)
    logp = pd.to_numeric(test_df["MolLogP"], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(ratio) & np.isfinite(logp)
    corr = float(np.corrcoef(ratio[mask], logp[mask])[0, 1]) if mask.sum() > 2 else float("nan")
    spearman = float(pd.Series(ratio[mask]).corr(pd.Series(logp[mask]), method="spearman")) if mask.sum() > 2 else float("nan")
    fig, ax = plt.subplots(figsize=(6.6, 4.8))
    ax.scatter(logp[mask], ratio[mask], s=14, alpha=0.28, color="#4C78A8", label="молекулы")
    if mask.sum() >= 3:
        slope, intercept = np.polyfit(logp[mask], ratio[mask], deg=1)
        x_line = np.linspace(float(np.min(logp[mask])), float(np.max(logp[mask])), 200)
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, color="#E45756", lw=2.0, label="линейная регрессия")
        bins = np.quantile(logp[mask], np.linspace(0.0, 1.0, 8))
        bins = np.unique(bins)
        if bins.size >= 3:
            bin_ids = np.digitize(logp[mask], bins[1:-1], right=False)
            centers = []
            medians = []
            for idx in range(len(bins) - 1):
                in_bin = bin_ids == idx
                if np.any(in_bin):
                    centers.append(float(np.median(logp[mask][in_bin])))
                    medians.append(float(np.median(ratio[mask][in_bin])))
            if centers:
                ax.plot(
                    centers,
                    medians,
                    color="#54A24B",
                    lw=1.8,
                    marker="o",
                    ms=4,
                    label="медиана по корзинам",
                )
    ax.set_xlabel("MolLogP")
    ax.set_ylabel(r"$\|g_{disp}\| / (\|g_{disp}\| + \|g_{polar}\|)$")
    ax.set_title("Доля дисперсионного канала и липофильность")
    ax.grid(True, alpha=0.25)
    if np.isfinite(corr):
        ax.text(
            0.03,
            0.96,
            f"Pearson = {corr:.2f}\nSpearman = {spearman:.2f}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9.5,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#B8C2CC"},
        )
    ax.legend(loc="lower right", frameon=True, fontsize=8.5)
    fig.savefig(output_dir / "timp_channel_ratio_vs_logp.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "timp_channel_ratio_vs_logp.png", dpi=220, bbox_inches="tight")
    return corr


def _plot_embedding(test_df: pd.DataFrame, output_dir: Path, channel: str, color_by: str) -> None:
    X = _stack(test_df, f"g_{channel}")
    y = pd.to_numeric(test_df[color_by], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(y)
    X2 = PCA(n_components=2, random_state=42).fit_transform(X[mask])
    fig, ax = plt.subplots(figsize=(5.8, 5.1))
    sc = ax.scatter(X2[:, 0], X2[:, 1], c=y[mask], s=12, cmap="viridis", alpha=0.75)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"{channel}: цвет = {color_by}")
    fig.colorbar(sc, ax=ax, label=color_by)
    fig.savefig(output_dir / f"timp_{channel}_embedding_{color_by}.pdf", bbox_inches="tight")
    fig.savefig(output_dir / f"timp_{channel}_embedding_{color_by}.png", dpi=220, bbox_inches="tight")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    device = _resolve_device(args.device)
    model, cfg = load_model(str(Path(args.checkpoint).expanduser().resolve()), device=device)
    if str(getattr(cfg, "encoder_type", "")) != "timp":
        raise ValueError(f"Expected encoder_type='timp', got {cfg.encoder_type!r}.")

    test_df = _collect(model, cfg, args.test_data, device, args.batch_size, args.seed)
    train_path = Path(args.train_data).expanduser().resolve() if args.train_data else _infer_train_csv(args.test_data)
    if train_path is not None:
        print(f"[timp-channels] Using train split: {train_path}")
        train_df = _collect(model, cfg, train_path, device, args.batch_size, args.seed)
    else:
        print("[timp-channels] Train split not found; falling back to internal solute split of the test set.")
        train_df, test_df = train_test_split(
            test_df,
            test_size=0.35,
            random_state=args.seed,
        )
        train_df = train_df.reset_index(drop=True)
        test_df = test_df.reset_index(drop=True)

    matrix = _build_probe_matrix(train_df, test_df)
    matrix.to_csv(output_dir / "channel_probe_r2.csv", index=False)
    test_df.drop(columns=["g_disp", "g_polar"]).to_csv(output_dir / "channel_metadata.csv", index=False)
    np.savez_compressed(
        output_dir / "channel_embeddings_test.npz",
        smiles=test_df["solute_smiles"].to_numpy(dtype=object),
        g_disp=_stack(test_df, "g_disp"),
        g_polar=_stack(test_df, "g_polar"),
    )

    _plot_probe_matrix(matrix, output_dir)
    corr = _plot_ratio(test_df, output_dir)
    _plot_embedding(test_df, output_dir, "disp", "MolLogP")
    _plot_embedding(test_df, output_dir, "polar", "TPSA")

    summary = {
        "n_train_solutes": int(len(train_df)),
        "n_test_solutes": int(len(test_df)),
        "ratio_vs_mollogp_corr": None if not np.isfinite(corr) else corr,
        "experimental_hansen_train_unique": int(pd.to_numeric(train_df["delta_d"], errors="coerce").notna().sum()),
        "experimental_hansen_test_unique": int(pd.to_numeric(test_df["delta_d"], errors="coerce").notna().sum()),
        "probe": matrix.to_dict(orient="records"),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote TIMP channel analysis to {output_dir}")


if __name__ == "__main__":
    main()
