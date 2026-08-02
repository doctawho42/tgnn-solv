#!/usr/bin/env python3
"""Table-of-contents graphic for the ACS submission.

ACS asks for one image that conveys the paper at a glance, printed small, and it is
the one image the journal places beside the article.  It therefore has to carry a
claim the paper still makes.

WHAT IT USED TO SAY, AND WHY THAT IS GONE
-----------------------------------------
Until 2026-08-02 the bottom line read "On 477 activity measurements over 185 molecule
pairs, the fixed model and not the input is the likelier ceiling (margin +0.51)".
That is the aggregate verdict, and the aggregate is retired: an aggregate margin is a
composition-weighted average of a term that moves 25-fold across chemistries against a
bound that barely moves, so it reports the composition of the set and not a property of
the closure (Sec. 3.2.1).  The graphic may not restate it.

WHAT IT SAYS NOW
----------------
The finding that survives and is stated in the title: "grounding" names two opposite
operations on one reference database, and they carry opposite signs.  Supervising the
learned profile against the database during training improves solubility MAE by 0.20
over three seeds; substituting the same database's profile for the learned one at
prediction time degrades it by 0.41.  Both numbers are the three-seed test-split values
of Sec. 3.1, and the scope (solubility MAE, three seeds) prints in the image.

The stratified map is the paper's other deliverable and does not go here: at 3.25 x 1.75
in nothing legible can carry fifteen strata with their margins and intervals, and a
drawn map reduced to one bar per class would be an aggregate again.  The map is a table
in the article (Table 3).

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
HELP = "#4E8C7A"
OUT = Path(__file__).resolve().parents[2] / "paper" / "figs" / "fig_toc"

# savefig pad_inches: the default 0.1 in adds 14.4 pt of white to a 234 pt-wide canvas, so
# \includegraphics[width=\linewidth] then scales the whole graphic by 0.946 and every point
# size set below prints 5.4% smaller than it reads here.  0.02 in keeps the margin without
# the reduction: at pad 0.1 the 6.0 pt sentence printed at 5.67 pt.
plt.rcParams.update({
    "font.family": "serif", "text.usetex": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "savefig.dpi": 600, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "figure.dpi": 150,
})


def box(ax, x, y, w, h, text, fc, ec=INK, fs=7.0, tc=INK, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.005,rounding_size=0.02",
                                fc=fc, ec=ec, lw=lw, mutation_aspect=0.5, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=4)


fig = plt.figure(figsize=(3.25, 1.75))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

# Point sizes here are printed point sizes (the canvas is the 3.25 in ACS slot and the
# tocentry measure is 3.26 in).  Nothing below 6.0 pt, and a mathtext sub/superscript is
# 0.7x its base, so a label carrying one needs a base of at least 8.6 pt.
y = 0.755
box(ax, 0.02, y, 0.18, 0.16, "solute\n+ solvent", "white", fs=6.4)
box(ax, 0.245, y, 0.155, 0.16, "encoder", TEAL, fs=6.5, tc="white", lw=0)
box(ax, 0.445, y, 0.095, 0.16, r"$\hat\sigma$", TEAL, fs=9.0, tc="white", lw=0)
box(ax, 0.585, y, 0.245, 0.16, "fixed\nthermodynamics", SALMON, fs=6.4, tc=INK, lw=0)
for p0, p1 in ((0.20, 0.245), (0.40, 0.445), (0.54, 0.585)):
    ax.add_patch(FancyArrowPatch((p0, y + 0.08), (p1, y + 0.08), arrowstyle="-|>",
                                 color=INK, lw=1.1, mutation_scale=8, zorder=2))
ax.add_patch(FancyArrowPatch((0.83, y + 0.08), (0.858, y + 0.08), arrowstyle="-|>",
                             color=INK, lw=1.1, mutation_scale=8, zorder=2))
ax.text(0.868, y + 0.08, "$\\ln x_2$", ha="left", va="center", fontsize=9.0, color=INK)

# The reference database, and the two operations on it.  The left arrow is training-time
# supervision and the right one is the evaluation-time substitution; they end on different
# boxes because they are different interventions, which is the whole point of the image.
box(ax, 0.325, 0.375, 0.095, 0.16, r"$\sigma^\star$", SALMON, fs=9.0, tc=INK, lw=0)
ax.text(0.3725, 0.305, "reference profile", ha="center", va="center", fontsize=6.4, color=INK)

ax.add_patch(FancyArrowPatch((0.348, 0.545), (0.322, 0.745), arrowstyle="-|>",
                             color=HELP, lw=1.4, mutation_scale=9, zorder=2))
ax.add_patch(FancyArrowPatch((0.408, 0.545), (0.487, 0.745), arrowstyle="-|>",
                             color=HURT, lw=1.4, mutation_scale=9, zorder=2))

ax.text(0.245, 0.665, "train on it", ha="right", va="center", fontsize=6.8, color=HELP)
ax.text(0.245, 0.575, "MAE $-0.20$", ha="right", va="center", fontsize=6.8, color=HELP)
ax.text(0.505, 0.665, "feed it in instead", ha="left", va="center", fontsize=6.8, color=HURT)
ax.text(0.505, 0.575, "MAE $+0.41$", ha="left", va="center", fontsize=6.8, color=HURT)

# One line, and it states the sign structure rather than a set-level verdict.
ax.text(0.5, 0.115, "Grounding is two operations on one database, with opposite signs\n"
        "(solubility MAE on held-out scaffolds, three seeds).",
        ha="center", va="center", fontsize=6.2, color=INK)

for ext in ("pdf", "png"):
    fig.savefig(f"{OUT}.{ext}")
print(f"wrote {OUT}.pdf / .png")
