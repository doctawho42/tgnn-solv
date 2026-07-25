#!/usr/bin/env python3
"""Figure 1: a schematic entry point to the paper, in two panels.

Deliberately carries no statistics and no evidence grading. An opening figure should let a
reader who does not yet know the topic see what is being done and what went wrong with it;
numbers belong to the results that report them, and the grading of claims by strength of
evidence belongs to the Discussion.

  (a) the pipeline and the paradox -- a learned encoder produces a charge-density profile that
      a fixed thermodynamic model turns into a solubility; substituting an external reference
      profile for the learned one makes the prediction worse.
  (b) where the error sits -- that error splits into a misspecified-model part and an
      insufficient-input part, and the model part is the larger.

    MPLBACKEND=Agg python scripts/analysis/make_overview_figure.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

# palette shared with make_concept_figures.py
SALMON = "#E8A98C"   # the fixed closure and the external reference input
TEAL = "#7FB5A6"     # the learned representation
INK = "#4D4D4D"
GRAY = "#9AA0A6"
HURT = "#B5654A"
PAPER = "#FBF9F7"
OUT = Path(__file__).resolve().parents[2] / "paper" / "figs" / "fig_overview"

plt.rcParams.update({
    "font.family": "serif", "text.usetex": False, "svg.fonttype": "none",
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "savefig.dpi": 300, "savefig.bbox": "tight", "figure.dpi": 150,
})


def box(ax, x, y, w, h, text, fc, ec=INK, fs=9.0, tc=INK, lw=1.1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.02",
                                fc=fc, ec=ec, lw=lw, mutation_aspect=0.55, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=4)


def arrow(ax, p0, p1, color=INK, lw=1.6, mut=12):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", color=color, lw=lw,
                                 mutation_scale=mut, zorder=2))


fig = plt.figure(figsize=(9.2, 3.05))
gs = fig.add_gridspec(1, 2, width_ratios=[1.32, 1.0], wspace=0.10,
                      left=0.015, right=0.985, top=0.86, bottom=0.03)
axa = fig.add_subplot(gs[0]); axa.set_xlim(0, 1.32); axa.set_ylim(0, 1.0); axa.axis("off")
axb = fig.add_subplot(gs[1]); axb.set_xlim(0, 1.0); axb.set_ylim(0, 1.0); axb.axis("off")

for ax, xmax, letter, title in ((axa, 1.32, "a", "The pipeline, and the paradox"),
                                (axb, 1.0, "b", "Where the error sits")):
    ax.add_patch(FancyBboxPatch((0.01, 0.02), xmax - 0.02, 0.94,
                                boxstyle="round,pad=0.006,rounding_size=0.02",
                                fc=PAPER, ec="#E4DED8", lw=1.0, zorder=0))
    ax.text(0.045, 0.87, letter, ha="left", va="center", fontsize=11.5,
            color=INK, fontweight="bold", zorder=1)
    ax.text(0.10, 0.87, title, ha="left", va="center", fontsize=10.5, color=INK, zorder=1)

# ---------------- (a) the pipeline and the swap ----------------
y = 0.56
box(axa, 0.06, y, 0.20, 0.15, "solute\n+ solvent", "white", fs=8.2)
box(axa, 0.30, y, 0.19, 0.15, "encoder", TEAL, fs=8.2, tc="white", lw=0)
box(axa, 0.53, y, 0.11, 0.15, r"$\hat\sigma$", TEAL, fs=12.0, tc="white", lw=0)
box(axa, 0.68, y, 0.30, 0.15, "thermodynamic\nmodel (fixed)", SALMON, fs=8.2, tc=INK, lw=0)
for p0, p1 in ((0.26, 0.30), (0.49, 0.53), (0.64, 0.68)):
    arrow(axa, (p0, y + 0.075), (p1, y + 0.075))
arrow(axa, (0.98, y + 0.075), (1.03, y + 0.075))
axa.text(1.055, y + 0.075, "solubility", ha="left", va="center", fontsize=8.8, color=INK)

# the substitution
box(axa, 0.53, 0.25, 0.11, 0.15, r"$\sigma^\star$", SALMON, fs=12.0, tc=INK, lw=0)
axa.text(0.50, 0.325, "external\nreference profile", ha="right", va="center",
         fontsize=8.2, color=INK)
arrow(axa, (0.585, 0.40), (0.585, 0.545), color=HURT, lw=1.8)
axa.text(0.66, 0.325, "substituting it makes\nthe prediction worse", ha="left", va="center",
         fontsize=8.8, color=HURT)
axa.text(0.06, 0.10, "Either the fixed model is wrong, or the learned profile\n"
                     "carries information the reference does not.",
         ha="left", va="center", fontsize=8.6, color=GRAY)

# ---------------- (b) the split ----------------
bx, by, bw, bh = 0.09, 0.46, 0.82, 0.14
frac = 0.72
axb.add_patch(FancyBboxPatch((bx, by), bw * frac, bh, boxstyle="square,pad=0",
                             fc=SALMON, ec=INK, lw=0.9, zorder=3))
axb.add_patch(FancyBboxPatch((bx + bw * frac, by), bw * (1 - frac), bh,
                             boxstyle="square,pad=0", fc="#DDE7E3", ec=INK, lw=0.9, zorder=3))
axb.text(bx + bw * frac / 2, by + bh / 2, "the model is\nmisspecified", ha="center",
         va="center", fontsize=8.4, color=INK, zorder=4)
axb.text(bx + bw * frac + bw * (1 - frac) / 2, by + bh / 2, "inputs\ninsufficient",
         ha="center", va="center", fontsize=7.2, color="#5F6B66", zorder=4)
axb.text(bx, by + bh + 0.06, "error when the reference profile is used",
         ha="left", va="bottom", fontsize=8.6, color=GRAY)
axb.text(0.50, 0.235, "The misspecification term is the larger.", ha="center", va="center",
         fontsize=9.2, color=HURT)
axb.text(0.50, 0.115, "An external reference for the profile is what\nmakes the two "
                      "terms separately measurable.", ha="center", va="center",
         fontsize=8.4, color=GRAY)

fig.suptitle("When do reference physical inputs help a learned solubility model?",
             fontsize=12.5, color=INK, y=0.985)
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT}.{ext}")
print(f"wrote {OUT}.pdf / .png")
