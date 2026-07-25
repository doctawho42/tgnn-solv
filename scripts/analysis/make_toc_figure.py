#!/usr/bin/env python3
"""Table-of-contents graphic for the ACS submission.

ACS asks for one image that conveys the paper at a glance, printed small. It therefore
carries the single claim and nothing else: a learned profile drives a fixed thermodynamic
model, and substituting the external reference profile makes the prediction worse. Same
palette as Figure 1.

ACS specifies the TOC graphic fits a 3.25 in x 1.75 in slot.

    MPLBACKEND=Agg python scripts/analysis/make_toc_figure.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

SALMON = "#E8A98C"
TEAL = "#7FB5A6"
INK = "#4D4D4D"
HURT = "#B5654A"
OUT = Path(__file__).resolve().parents[2] / "paper" / "figs" / "fig_toc"

plt.rcParams.update({
    "font.family": "serif", "text.usetex": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "savefig.dpi": 600, "savefig.bbox": "tight", "figure.dpi": 150,
})


def box(ax, x, y, w, h, text, fc, ec=INK, fs=7.0, tc=INK, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.005,rounding_size=0.02",
                                fc=fc, ec=ec, lw=lw, mutation_aspect=0.5, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=4)


fig = plt.figure(figsize=(3.25, 1.75))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

y = 0.60
box(ax, 0.03, y, 0.19, 0.17, "solute\n+ solvent", "white", fs=6.2)
box(ax, 0.26, y, 0.17, 0.17, "encoder", TEAL, fs=6.6, tc="white", lw=0)
box(ax, 0.47, y, 0.10, 0.17, r"$\hat\sigma$", TEAL, fs=9.0, tc="white", lw=0)
box(ax, 0.61, y, 0.26, 0.17, "fixed\nthermodynamics", SALMON, fs=6.2, tc=INK, lw=0)
for p0, p1 in ((0.22, 0.26), (0.43, 0.47), (0.57, 0.61)):
    ax.add_patch(FancyArrowPatch((p0, y + 0.085), (p1, y + 0.085), arrowstyle="-|>",
                                 color=INK, lw=1.1, mutation_scale=8, zorder=2))
ax.add_patch(FancyArrowPatch((0.87, y + 0.085), (0.91, y + 0.085), arrowstyle="-|>",
                             color=INK, lw=1.1, mutation_scale=8, zorder=2))
ax.text(0.925, y + 0.085, "$\\ln x_2$", ha="left", va="center", fontsize=7.5, color=INK)

box(ax, 0.47, 0.20, 0.10, 0.17, r"$\sigma^\star$", SALMON, fs=9.0, tc=INK, lw=0)
ax.text(0.44, 0.285, "reference\nprofile", ha="right", va="center", fontsize=6.2, color=INK)
ax.add_patch(FancyArrowPatch((0.52, 0.37), (0.52, 0.585), arrowstyle="-|>",
                             color=HURT, lw=1.4, mutation_scale=9, zorder=2))
ax.text(0.60, 0.285, "prediction gets worse", ha="left", va="center",
        fontsize=7.2, color=HURT)
ax.text(0.5, 0.055, "The fixed model, not the input, sets the ceiling.",
        ha="center", va="center", fontsize=7.0, color=INK)

for ext in ("pdf", "png"):
    fig.savefig(f"{OUT}.{ext}")
print(f"wrote {OUT}.pdf / .png")
