#!/usr/bin/env python3
"""Plot the data-efficiency curve (physics-grounded vs DirectGNN MAE across
train-by-solute fractions) from results/data_efficiency/summary.json → paper/figs.
Soft-pastel palette matching make_paradox_figures.py (physics=salmon, direct=teal)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# THE JOURNAL'S GRAPHICS SPECIFICATION, applied before any figure is created. Without it matplotlib
# emits DejaVu Sans in Type 3, and both are violations; see acs_figure_style for what and why.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from acs_figure_style import apply as _acs_apply  # noqa: E402
_acs_apply()

REPO = Path(__file__).resolve().parents[2]
SALMON, TEAL, INK = "#E8A98C", "#7FB5A6", "#4D4D4D"
_STYLE = Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"


def main() -> None:
    d = json.load(open(REPO / "results/data_efficiency/summary.json"))["curve"]
    try:
        plt.style.use(str(_STYLE))
        # AFTER style.use, NOT BEFORE: the shared style file resets rcParams wholesale, so a
        # typeface set earlier is silently discarded. The specification has to be applied last.
        _acs_apply()
    except Exception:
        plt.rcParams.update({
            "figure.facecolor": "white", "savefig.facecolor": "white", "savefig.dpi": 300,
            "savefig.bbox": "tight", "axes.grid": True, "axes.axisbelow": True,
            "grid.color": "#D9D9D9", "axes.edgecolor": INK, "font.size": 11,
        })

    # Canvas = \columnwidth (240.7 pt = 3.34 in), the width the section sets it at, so the
    # PDF prints at 1:1 instead of the 0.50x reduction that put its ticks at 5.0 pt.
    fig, ax = plt.subplots(figsize=(3.52, 2.57))
    for model, color, label, marker in (
        ("physics", SALMON, "physics-grounded", "o"),
        ("direct", TEAL, "DirectGNN (black box)", "s"),
    ):
        keys = sorted(d[model].keys(), key=float)
        fr = [float(k) for k in keys]
        mae = [d[model][k]["mae"] for k in keys]
        ax.plot(fr, mae, marker=marker, color=color, lw=1.6, ms=5, label=label)
    ax.set_xscale("log")
    ax.set_xticks([0.05, 0.1, 0.25, 0.5, 1.0])
    ax.set_xticklabels(["0.05", "0.1", "0.25", "0.5", "1.0"])
    # The y-label's "2" is a mathtext subscript, which matplotlib sets at 0.7x the base, so
    # the base has to clear 6/0.7 pt on the page for the subscript to clear 6 pt.  The canvas
    # prints at 0.89x (270.5 pt native into the 240.7 pt column), so the base must clear
    # 6/0.7/0.89 = 9.6 pt; 10.2 leaves the subscript at 6.3 pt on the page.
    ax.set_xlabel("training fraction (by solute)", fontsize=10.2)
    ax.set_ylabel(r"scaffold-test MAE ($\ln x_2$)", fontsize=10.2)
    # Factual enumeration only. The paper makes no accuracy claim in either direction
    # (Sec. 5; Table 2 grades the physics-vs-DirectGNN row "no claim"), so this title must
    # not assert one -- it names the axes, the seed count and the arms, and nothing else.
    # Set on two lines: at 6.6 pt it fitted on one, but 6.6 x 0.89 = 5.9 pt on the page is
    # below the 6 pt floor, and 7.6 pt on one line would widen the canvas and undo the gain.
    ax.set_title("Scaffold-test MAE by training fraction,\n"
                 "two separately tuned arms, one seed",
                 color=INK, fontsize=7.6)
    ax.tick_params(labelsize=7.6)
    ax.legend(frameon=False, loc="upper left", fontsize=7.6)
    out = REPO / "paper/figs"
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"fig_data_efficiency.{ext}")
    print("wrote", out / "fig_data_efficiency.pdf")


if __name__ == "__main__":
    main()
