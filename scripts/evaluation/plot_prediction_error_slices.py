#!/usr/bin/env python3
"""Generate presentation-ready figures for prediction error slice bundles."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


MODEL_ORDER = ["DirectGNN", "RF_hybrid", "TGNN_MPNN"]
MODEL_COLORS = {
    "DirectGNN": "#2563eb",
    "RF_hybrid": "#4d7c0f",
    "TGNN_MPNN": "#d97706",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot figures from results/prediction_error_slices.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--bundle-dir",
        default="results/prediction_error_slices",
        help="Input bundle produced by run_prediction_error_slices.py.",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Figure output directory. Defaults to <bundle-dir>/figures.",
    )
    parser.add_argument(
        "--presentation-dir",
        default="figures",
        help="Optional directory that receives copies of generated figures.",
    )
    parser.add_argument(
        "--no-presentation-copy",
        action="store_true",
        help="Do not copy generated figures into figures.",
    )
    return parser.parse_args()


def _model_dirs(bundle_dir: Path) -> list[str]:
    labels = [p.name for p in bundle_dir.iterdir() if p.is_dir() and (p / "summary.json").is_file()]
    return [label for label in MODEL_ORDER if label in labels] + [
        label for label in labels if label not in MODEL_ORDER
    ]


def _ordered_summary(bundle_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(bundle_dir / "comparison_summary.csv")
    order = {label: idx for idx, label in enumerate(MODEL_ORDER)}
    df["_order"] = df["label"].map(lambda x: order.get(x, 999))
    return df.sort_values(["_order", "label"], kind="stable").drop(columns=["_order"])


def _save(fig: plt.Figure, out_dir: Path, stem: str, copied: list[Path], presentation_dir: Path | None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"{stem}.png", out_dir / f"{stem}.pdf"]
    for path in paths:
        fig.savefig(path, dpi=220, bbox_inches="tight")
        copied.append(path)
        if presentation_dir is not None:
            presentation_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, presentation_dir / path.name)
    plt.close(fig)


def _style_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#d4d4d4", linewidth=0.8, alpha=0.65)
    ax.set_axisbelow(True)


def plot_model_comparison(bundle_dir: Path, out_dir: Path, copied: list[Path], presentation_dir: Path | None) -> None:
    df = _ordered_summary(bundle_dir)
    labels = df["label"].tolist()
    colors = [MODEL_COLORS.get(label, "#525252") for label in labels]
    x = np.arange(len(labels))

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    axes[0].bar(x, df["mae"], color=colors, width=0.62)
    axes[0].set_xticks(x, labels, rotation=20, ha="right")
    axes[0].set_ylabel("MAE, ln x2")
    axes[0].set_title("Scaffold test error")
    axes[0].set_ylim(0, max(df["mae"]) * 1.22)
    for idx, value in enumerate(df["mae"]):
        axes[0].text(idx, value + 0.025, f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    _style_axes(axes[0])

    axes[1].bar(x, df["r2"], color=colors, width=0.62)
    axes[1].set_xticks(x, labels, rotation=20, ha="right")
    axes[1].set_ylabel("R^2")
    axes[1].set_title("Explained variance")
    axes[1].set_ylim(0, max(df["r2"]) * 1.28)
    for idx, value in enumerate(df["r2"]):
        axes[1].text(idx, value + 0.01, f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    _style_axes(axes[1])

    fig.suptitle("Aligned prediction-only scaffold comparison", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, out_dir, "prediction_slice_model_comparison", copied, presentation_dir)


def plot_pair_cdf(bundle_dir: Path, labels: Iterable[str], out_dir: Path, copied: list[Path], presentation_dir: Path | None) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    for label in labels:
        path = bundle_dir / label / "pair_errors.csv"
        if not path.is_file():
            continue
        values = pd.read_csv(path)["mean_abs_error"].dropna().to_numpy(dtype=float)
        values = np.sort(values)
        y = np.arange(1, values.size + 1) / values.size
        ax.plot(values, y, label=label, color=MODEL_COLORS.get(label, "#525252"), linewidth=2.2)
    ax.axvline(1.0, color="#737373", linestyle="--", linewidth=1.0)
    ax.axvline(3.0, color="#737373", linestyle=":", linewidth=1.2)
    ax.set_xlabel("Pair-level MAE, ln x2")
    ax.set_ylabel("Fraction of test pairs")
    ax.set_title("Pair error concentration")
    ax.set_xlim(left=0)
    ax.legend(frameon=False)
    _style_axes(ax)
    fig.tight_layout()
    _save(fig, out_dir, "prediction_slice_pair_mae_cdf", copied, presentation_dir)


def _load_group_metric(bundle_dir: Path, labels: Iterable[str], filename: str, group_col: str) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for label in labels:
        path = bundle_dir / label / filename
        if not path.is_file():
            continue
        df = pd.read_csv(path)
        df["label"] = label
        rows.append(df[[group_col, "label", "mae", "n_rows"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def plot_chemistry_classes(bundle_dir: Path, labels: list[str], out_dir: Path, copied: list[Path], presentation_dir: Path | None) -> None:
    df = _load_group_metric(bundle_dir, labels, "chemistry_coarse_class_metrics.csv", "coarse_class")
    if df.empty:
        return
    direct = df[df["label"] == "DirectGNN"].sort_values("n_rows", ascending=False)
    categories = direct["coarse_class"].tolist()
    if not categories:
        categories = sorted(df["coarse_class"].unique())
    categories = categories[:8]
    x = np.arange(len(categories))
    width = 0.78 / max(len(labels), 1)

    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    for idx, label in enumerate(labels):
        sub = df[df["label"] == label].set_index("coarse_class").reindex(categories)
        offset = (idx - (len(labels) - 1) / 2) * width
        ax.bar(
            x + offset,
            sub["mae"],
            width=width,
            label=label,
            color=MODEL_COLORS.get(label, "#525252"),
        )
    ax.set_xticks(x, categories, rotation=28, ha="right")
    ax.set_ylabel("MAE, ln x2")
    ax.set_title("Error by solute chemistry class")
    ax.legend(frameon=False, ncols=len(labels))
    _style_axes(ax)
    fig.tight_layout()
    _save(fig, out_dir, "prediction_slice_chemistry_class_mae", copied, presentation_dir)


def plot_halogenated_solvent(bundle_dir: Path, labels: list[str], out_dir: Path, copied: list[Path], presentation_dir: Path | None) -> None:
    df = _load_group_metric(
        bundle_dir,
        labels,
        "halogenated_aromatic_by_solvent_type.csv",
        "solvent_type_name",
    )
    if df.empty:
        return
    direct = df[df["label"] == "DirectGNN"].sort_values("n_rows", ascending=False)
    categories = direct["solvent_type_name"].tolist()[:8]
    x = np.arange(len(categories))
    width = 0.78 / max(len(labels), 1)

    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    for idx, label in enumerate(labels):
        sub = df[df["label"] == label].set_index("solvent_type_name").reindex(categories)
        offset = (idx - (len(labels) - 1) / 2) * width
        ax.bar(
            x + offset,
            sub["mae"],
            width=width,
            label=label,
            color=MODEL_COLORS.get(label, "#525252"),
        )
    ax.set_xticks(x, categories, rotation=25, ha="right")
    ax.set_ylabel("MAE, ln x2")
    ax.set_title("Halogenated aromatic solutes by solvent type")
    ax.legend(frameon=False, ncols=len(labels))
    _style_axes(ax)
    fig.tight_layout()
    _save(fig, out_dir, "prediction_slice_halogenated_aromatic_solvent", copied, presentation_dir)


def plot_neighbor_bins(bundle_dir: Path, labels: list[str], out_dir: Path, copied: list[Path], presentation_dir: Path | None) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    for label in labels:
        path = bundle_dir / label / "nearest_neighbor_error_bins.csv"
        if not path.is_file():
            continue
        df = pd.read_csv(path)
        ax.plot(
            df["pair_tanimoto_bin"].astype(str),
            df["mae"],
            marker="o",
            linewidth=2.2,
            label=label,
            color=MODEL_COLORS.get(label, "#525252"),
        )
    ax.set_xlabel("Nearest train pair Tanimoto bin")
    ax.set_ylabel("MAE, ln x2")
    ax.set_title("Coverage vs error")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(frameon=False)
    _style_axes(ax)
    fig.tight_layout()
    _save(fig, out_dir, "prediction_slice_nearest_neighbor_bins", copied, presentation_dir)


def plot_paired_deltas(bundle_dir: Path, out_dir: Path, copied: list[Path], presentation_dir: Path | None) -> None:
    path = bundle_dir / "paired_deltas_vs_DirectGNN.csv"
    if not path.is_file():
        return
    df = pd.read_csv(path)
    if df.empty:
        return
    labels = df["label"].tolist()
    colors = [MODEL_COLORS.get(label, "#525252") for label in labels]
    x = np.arange(len(labels))

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.0))
    axes[0].bar(x, df["mean_abs_error_delta_vs_reference"], color=colors, width=0.62)
    axes[0].axhline(0, color="#262626", linewidth=1.0)
    axes[0].set_xticks(x, labels, rotation=20, ha="right")
    axes[0].set_ylabel("Delta MAE vs DirectGNN")
    axes[0].set_title("Global paired delta")
    _style_axes(axes[0])

    axes[1].bar(x, df["fraction_rows_model_better_than_reference"] * 100.0, color=colors, width=0.62)
    axes[1].axhline(50, color="#262626", linewidth=1.0, linestyle="--")
    axes[1].set_xticks(x, labels, rotation=20, ha="right")
    axes[1].set_ylabel("Rows better than DirectGNN, %")
    axes[1].set_title("Row-wise wins")
    axes[1].set_ylim(0, 100)
    _style_axes(axes[1])

    fig.suptitle("Paired model comparison on the same scaffold rows", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, out_dir, "prediction_slice_paired_deltas", copied, presentation_dir)


def main() -> None:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else bundle_dir / "figures"
    presentation_dir = None if args.no_presentation_copy else Path(args.presentation_dir).expanduser().resolve()

    labels = _model_dirs(bundle_dir)
    copied: list[Path] = []

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
        }
    )

    plot_model_comparison(bundle_dir, out_dir, copied, presentation_dir)
    plot_pair_cdf(bundle_dir, labels, out_dir, copied, presentation_dir)
    plot_chemistry_classes(bundle_dir, labels, out_dir, copied, presentation_dir)
    plot_halogenated_solvent(bundle_dir, labels, out_dir, copied, presentation_dir)
    plot_neighbor_bins(bundle_dir, labels, out_dir, copied, presentation_dir)
    plot_paired_deltas(bundle_dir, out_dir, copied, presentation_dir)

    manifest = {
        "bundle_dir": str(bundle_dir),
        "figure_dir": str(out_dir),
        "presentation_dir": None if presentation_dir is None else str(presentation_dir),
        "files": [str(path) for path in copied],
    }
    (out_dir / "figure_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
