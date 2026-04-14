#!/usr/bin/env python
"""Plot descriptor linear-probe evolution over training epochs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
for candidate in (SCRIPTS, SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import _bootstrap  # noqa: F401,E402
import matplotlib.pyplot as plt
import pandas as pd


TRACKED_COLUMNS = (
    "MolLogP_R2",
    "TPSA_R2",
    "NumHDonors_R2",
    "NumHAcceptors_R2",
    "FractionCSP3_R2",
    "MolWt_R2",
    "median_R2",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot R² of descriptor Ridge probes collected during training.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--probe-csv", required=True, help="CSV produced by --probe-every.")
    parser.add_argument("--output", required=True, help="Output PDF/PNG path.")
    return parser.parse_args()


def _save(fig: plt.Figure, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    if output.suffix.lower() != ".png":
        fig.savefig(output.with_suffix(".png"), dpi=220, bbox_inches="tight")


def main() -> None:
    args = parse_args()
    csv_path = Path(args.probe_csv).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    df = pd.read_csv(csv_path)
    if "global_epoch" not in df.columns:
        raise ValueError(f"{csv_path} must contain a global_epoch column.")
    if df.empty:
        raise ValueError(f"{csv_path} is empty.")

    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    colors = {
        "MolLogP_R2": "#4C78A8",
        "TPSA_R2": "#F58518",
        "NumHDonors_R2": "#54A24B",
        "NumHAcceptors_R2": "#B279A2",
        "FractionCSP3_R2": "#72B7B2",
        "MolWt_R2": "#E45756",
        "median_R2": "#333333",
    }
    labels = {
        "MolLogP_R2": "MolLogP",
        "TPSA_R2": "TPSA",
        "NumHDonors_R2": "доноры H",
        "NumHAcceptors_R2": "акцепторы H",
        "FractionCSP3_R2": "FractionCSP3",
        "MolWt_R2": "масса",
        "median_R2": "медиана",
    }
    x = df["global_epoch"].to_numpy()
    for col in TRACKED_COLUMNS:
        if col not in df.columns:
            continue
        y = pd.to_numeric(df[col], errors="coerce")
        if y.notna().sum() == 0:
            continue
        style = {
            "linewidth": 2.8 if col == "median_R2" else 1.8,
            "linestyle": "-" if col == "median_R2" else "--",
            "marker": "o",
            "markersize": 4.5,
        }
        ax.plot(x, y, color=colors.get(col), label=labels.get(col, col), **style)

    if "phase" in df.columns:
        for phase in sorted(df["phase"].dropna().unique()):
            phase_df = df[df["phase"] == phase]
            start = float(phase_df["global_epoch"].min())
            ax.axvline(start, color="#B8C2CC", linewidth=0.9, alpha=0.7)
            ax.text(
                start,
                0.02,
                f"Фаза {int(phase)}",
                rotation=90,
                va="bottom",
                ha="right",
                fontsize=9,
                color="#5B6770",
            )

    ax.set_xlabel("Эпоха")
    ax.set_ylabel("$R^2$ линейной пробы")
    ax.set_ylim(-0.05, 1.03)
    ax.grid(True, alpha=0.22)
    ax.legend(loc="lower right", fontsize=9, ncol=2, frameon=False)
    ax.set_title("Когда энкодер начинает кодировать химические дескрипторы")
    _save(fig, output)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
