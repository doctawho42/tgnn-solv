#!/usr/bin/env python3
"""Figure 1: a schematic entry point to the paper, in two panels.

Deliberately carries no statistics and no evidence grading. An opening figure should let a
reader who does not yet know the topic see what is being done and what went wrong with it;
numbers belong to the results that report them, and the grading of claims by strength of
evidence belongs to the Discussion.

  (a) the pipeline and the paradox -- a learned encoder produces a charge-density profile that
      a fixed thermodynamic model turns into a solubility; substituting an external reference
      profile for the learned one makes the prediction worse.
  (b) where the error sits -- one-sided bounds on the misspecified-model and
      insufficient-input parts in the deployed residual-only convention. Bounds, never a
      point split: the conditional variance is unestimable, so B_insuff is only ever an
      upper bound and B_closure only lower-bounded.

2026-07-28 declutter. Panel (b) used to carry a three-line statistical sentence (separation
margin, the pair-clustered and two-way bootstrap intervals, the n=60 comparison) and two grey
footnote lines. Prose set inside axes is unreadable at the printed column width, so all of it
moved OUT of the figure and into the caption; nothing was weakened and nothing was dropped.
What replaces it is a shape the eye can take in: because the bar's full width IS the total
error, the separation threshold MSE/2 is exactly the bar's midpoint, so the reader sees the
input block ending left of centre instead of reading a number. The caption must still state
the margin +0.51, both bootstrap intervals, the +0.05 on the n=60 corner, and that the two
blocks are contiguous shares of one total rather than intervals on an axis.

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


# Canvas width.  The figure is set at \linewidth (504.5 pt) across the two columns.  At the old
# 9.2 in (662 pt) everything shrank by 0.76 on the page, which put the smallest label at ~5.7 pt.
# 8.0 in (576 pt) prints at 0.88, so nothing here falls below 7 pt.  The height moves with it so
# the aspect, and therefore every box and arrow position, is unchanged.
fig = plt.figure(figsize=(8.0, 2.65))
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
bx, by, bw, bh = 0.09, 0.47, 0.82, 0.17
# Representative set (n=477 IDAC-cap-UD activity measurements over 185 molecule pairs) under the
# DEPLOYED residual-only combinatorial convention -- one convention rule across both sets, adopted
# in round 3: MSE 1.902, B_insuff <= 0.697 (LOTV, 8 equal-count bins, UNBIASED within-bin
# variance), so B_closure >= 1.205 and the separation margin MSE - 2*B_insuff = +0.51.  Drawn as
# two contiguous SHARES of one total -- never as intervals, and never as a gap on an axis.
MSE, BINS = 1.902, 0.697
lo = BINS / MSE
hi = 1.0 - lo
axb.add_patch(FancyBboxPatch((bx, by), bw * lo, bh, boxstyle="square,pad=0",
                             fc="#DDE7E3", ec=INK, lw=0.9, zorder=3))
axb.add_patch(FancyBboxPatch((bx + bw * lo, by), bw * hi, bh, boxstyle="square,pad=0",
                             fc=SALMON, ec=INK, lw=0.9, zorder=3))
# One type size for both halves.  They are contiguous shares of ONE quantity, so a size
# difference between them reads as an emphasis the panel does not mean to place.
axb.text(bx + bw * lo / 2, by + bh / 2, "inputs\ninsufficient", ha="center",
         va="center", fontsize=8.6, color="#5F6B66", zorder=4)
axb.text(bx + bw * lo + bw * hi / 2, by + bh / 2, "the model is\nmisspecified", ha="center",
         va="center", fontsize=8.6, color=INK, zorder=4)
# the design (477 measurements over 185 molecule pairs) is the caption's business; the panel
# needs only enough to say which quantity is being cut.
# This header is the widest single run in panel (b) and it is left-aligned on the bar, so it
# has only (0.99 - bx) = 0.90 axis units -- about 206 pt -- before it leaves the rounded box on
# the right.  At 8.2 pt it did leave it, by about a point, once the canvas came down to 8.0 in.
# 7.8 pt and a single space buy back roughly ten points of that run.  Measure the run, not the
# eye, if this string is ever lengthened.
axb.text(bx, by + bh + 0.10, "error when the reference profile is used ($n{=}477$)",
         ha="left", va="bottom", fontsize=7.8, color=GRAY)
axb.text(bx + bw * lo, by + bh + 0.035, r"$\leq 0.70$", ha="right", va="bottom",
         fontsize=8.4, color="#5F6B66")
axb.text(bx + bw * lo, by + bh + 0.035, r"  $\geq 1.21$", ha="left", va="bottom",
         fontsize=8.4, color=HURT)
# The bar's full width IS the total error, so the separation threshold MSE/2 is its midpoint:
# the input block ending left of centre IS the ordering, drawn rather than asserted. The margin
# itself, its two bootstrap intervals and the n=60 comparison are the caption's business.
axb.plot([bx + bw / 2] * 2, [by - 0.10, by + bh + 0.015], ls=(0, (3.2, 2.2)), lw=1.2,
         color=HURT, zorder=5, solid_capstyle="butt")
axb.text(bx + bw / 2, by - 0.135, "half the total error", ha="center", va="top",
         fontsize=8.4, color=HURT)

fig.suptitle("When do reference physical inputs help a learned solubility model?",
             fontsize=12.5, color=INK, y=0.985)
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT}.{ext}")
print(f"wrote {OUT}.pdf / .png")
