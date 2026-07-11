#!/usr/bin/env python3
"""Plot the data-efficiency curve (physics-grounded vs DirectGNN MAE across
train-by-solute fractions) from results/data_efficiency/summary.json → paper/figs.
Soft-pastel palette matching make_paradox_figures.py (physics=salmon, direct=teal)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[2]
SALMON, TEAL, INK = "#E8A98C", "#7FB5A6", "#4D4D4D"
_STYLE = Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"


def main() -> None:
    d = json.load(open(REPO / "results/data_efficiency/summary.json"))["curve"]
    try:
        plt.style.use(str(_STYLE))
    except Exception:
        plt.rcParams.update({
            "figure.facecolor": "white", "savefig.facecolor": "white", "savefig.dpi": 300,
            "savefig.bbox": "tight", "axes.grid": True, "axes.axisbelow": True,
            "grid.color": "#D9D9D9", "axes.edgecolor": INK, "font.size": 11,
        })

    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    for model, color, label, marker in (
        ("physics", SALMON, "physics-grounded", "o"),
        ("direct", TEAL, "DirectGNN (black box)", "s"),
    ):
        keys = sorted(d[model].keys(), key=float)
        fr = [float(k) for k in keys]
        mae = [d[model][k]["mae"] for k in keys]
        ax.plot(fr, mae, marker=marker, color=color, lw=2.0, ms=7, label=label)
    ax.set_xscale("log")
    ax.set_xticks([0.05, 0.1, 0.25, 0.5, 1.0])
    ax.set_xticklabels(["0.05", "0.1", "0.25", "0.5", "1.0"])
    ax.set_xlabel("training fraction (by solute)")
    ax.set_ylabel(r"scaffold-test MAE ($\ln x_2$)")
    ax.set_title("Physics grounding loses at every data budget", color=INK, fontsize=11)
    ax.legend(frameon=False, loc="upper left")
    out = REPO / "paper/figs"
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"fig_data_efficiency.{ext}")
    print("wrote", out / "fig_data_efficiency.pdf")


if __name__ == "__main__":
    main()
