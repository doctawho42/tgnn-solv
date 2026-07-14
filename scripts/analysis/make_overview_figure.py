#!/usr/bin/env python3
"""One unifying overview / graphical-abstract figure carrying the whole story in a
single view, so the formal theory can be stated (not walked through) in the main text
and its proofs moved to the ESI. Three acts, left to right:

  1. The paradox   -- molecule -> encoder -> sigma -> fixed COSMO-SAC closure -> ln x2;
                       swapping the learned sigma-hat for the TRUE sigma makes it WORSE.
  2. The measurement-- the external oracle splits the true-input error into B_closure
                       (closure wrong even given truth) + B_insuff (inputs insufficient);
                       here the closure binds.
  3. The map        -- two levers move the ceiling: raise closure fidelity (2010/dsp) or
                       supervise the latent (TeNNet) -> grounding flips from hurt to help.

    MPLBACKEND=Agg python scripts/analysis/make_overview_figure.py
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# palette shared with make_concept_figures.py
SALMON = "#E8A98C"   # fixed closure / true (oracle) inputs
TEAL = "#7FB5A6"     # learned representation / encoder
INK = "#4D4D4D"
GRAY = "#9AA0A6"
HURT = "#C8674F"     # grounding hurts
HELP = "#4A806F"     # grounding helps
PAPER = "#FBF9F7"
OUT = Path(__file__).resolve().parents[2] / "paper" / "figs" / "fig_overview"

plt.rcParams.update({
    "font.family": "serif", "text.usetex": False, "svg.fonttype": "none",
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "savefig.dpi": 300, "savefig.bbox": "tight", "figure.dpi": 150,
})


def box(ax, x, y, w, h, text, fc, ec=INK, fs=9.0, tc=INK, lw=1.1, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.02",
                                fc=fc, ec=ec, lw=lw, mutation_aspect=0.6, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=4, fontweight=("bold" if bold else "normal"))


def arrow(ax, p0, p1, color=INK, lw=1.6, style="-|>", ls="-", mut=12, rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, color=color, lw=lw,
                                 linestyle=ls, mutation_scale=mut, zorder=2,
                                 connectionstyle=f"arc3,rad={rad}"))


fig, ax = plt.subplots(figsize=(11.4, 4.2))
ax.set_xlim(0, 3.0); ax.set_ylim(0, 1.0); ax.axis("off")

# ---- act panels (soft backing cards) ----
for i, (x0, title) in enumerate([(0.02, "1. The paradox"),
                                  (1.03, "2. The measurement"),
                                  (2.04, "3. The map")]):
    ax.add_patch(FancyBboxPatch((x0, 0.03), 0.94, 0.94, boxstyle="round,pad=0.006,rounding_size=0.02",
                                fc=PAPER, ec="#E4DED8", lw=1.0, zorder=0))
    ax.text(x0 + 0.03, 0.90, title, ha="left", va="center", fontsize=10.5,
            color=INK, fontweight="bold", zorder=1)

# ===================== ACT 1: the paradox =====================
# pipeline: molecule -> encoder -> sigma -> closure -> ln x2
box(ax, 0.06, 0.55, 0.16, 0.12, "solute\n+ solvent", "white", fs=8.0)
box(ax, 0.29, 0.55, 0.16, 0.12, "encoder\n$h$", TEAL, fs=8.6, tc="white", lw=0)
box(ax, 0.52, 0.55, 0.14, 0.12, r"$\hat\sigma$", TEAL, fs=10.5, tc="white", lw=0)
box(ax, 0.72, 0.55, 0.20, 0.12, "COSMO-SAC\nclosure $g$", SALMON, fs=8.2, tc=INK, lw=0)
arrow(ax, (0.22, 0.61), (0.29, 0.61)); arrow(ax, (0.45, 0.61), (0.52, 0.61))
arrow(ax, (0.66, 0.61), (0.72, 0.61))
ax.text(0.965, 0.61, r"$\ln x_2$", ha="left", va="center", fontsize=9.5, color=INK)
arrow(ax, (0.92, 0.61), (0.955, 0.61))
ax.text(0.49, 0.72, "fixed, no fitted parameters", ha="center", va="bottom", fontsize=7.4,
        color="#C67A54", style="italic")

# the swap: true sigma -> worse
box(ax, 0.52, 0.30, 0.14, 0.12, r"$\sigma^\star$", SALMON, fs=10.5, tc=INK, lw=0)
ax.text(0.44, 0.36, "swap in\nTRUE $\\sigma$", ha="right", va="center", fontsize=7.6, color=INK)
arrow(ax, (0.51, 0.36), (0.52, 0.36), color=INK)
arrow(ax, (0.59, 0.42), (0.59, 0.54), color=HURT, lw=1.4, style="-|>")
ax.text(0.075, 0.205, "Premise: truer physical inputs $\\rightarrow$ better.", ha="left",
        va="center", fontsize=8.6, color=GRAY, zorder=2)
ax.text(0.075, 0.115, "Here, the opposite. So which is wrong —", ha="left", va="center",
        fontsize=8.8, color=HURT, fontweight="bold", zorder=2)
ax.text(0.075, 0.055, "the closure, or the inputs?", ha="left", va="center",
        fontsize=8.8, color=HURT, fontweight="bold", zorder=2)

# chevron 1 -> 2
arrow(ax, (0.955, 0.5), (1.03, 0.5), color=INK, lw=2.2, mut=18)

# ===================== ACT 2: the measurement =====================
cx = 1.03
ax.text(cx + 0.47, 0.80, "the true input has an external oracle (VT-2005),", ha="center",
        va="center", fontsize=7.8, color=GRAY, style="italic")
ax.text(cx + 0.47, 0.735, "so the true-input error splits exactly:", ha="center",
        va="center", fontsize=7.8, color=GRAY, style="italic")
# B = B_closure + B_insuff bar
ax.text(cx + 0.47, 0.62, r"$B \;=\; B_{\mathrm{closure}} \;+\; B_{\mathrm{insuff}}$",
        ha="center", va="center", fontsize=12.5, color=INK)
# stacked bar: closure large, insuff small
bx, by, bw = cx + 0.14, 0.40, 0.68
frac = 0.72
ax.add_patch(FancyBboxPatch((bx, by), bw * frac, 0.10, boxstyle="square,pad=0",
                            fc=SALMON, ec=INK, lw=0.8, zorder=3))
ax.add_patch(FancyBboxPatch((bx + bw * frac, by), bw * (1 - frac), 0.10, boxstyle="square,pad=0",
                            fc="#DDE7E3", ec=INK, lw=0.8, zorder=3))
ax.text(bx + bw * frac / 2, by + 0.05, "closure is wrong", ha="center", va="center",
        fontsize=7.8, color=INK, zorder=4)
ax.text(bx + bw * frac + bw * (1 - frac) / 2, by + 0.16, "inputs\ninsufficient", ha="center",
        va="center", fontsize=6.8, color=GRAY, zorder=4)
arrow(ax, (bx + bw * frac + 0.06, by + 0.14), (bx + bw * frac + 0.02, by + 0.10),
      color=GRAY, lw=0.9, mut=8)
ax.text(cx + 0.47, 0.30, r"$B_{\mathrm{closure}} > B_{\mathrm{insuff}}$   ($P\approx0.78$)",
        ha="center", va="center", fontsize=9.2, color=INK, fontweight="bold")
ax.text(cx + 0.47, 0.135, "The ceiling is the CLOSURE,\nnot the inputs.", ha="center",
        va="center", fontsize=9.0, color=SALMON if False else "#B5654A", fontweight="bold")

# chevron 2 -> 3
arrow(ax, (1.965, 0.5), (2.04, 0.5), color=INK, lw=2.2, mut=18)

# ===================== ACT 3: the map =====================
mx, my, mw, mh = 2.16, 0.20, 0.70, 0.52
# quadrant background: hurts (low-low) vs helps (rest)
ax.add_patch(FancyBboxPatch((mx, my), mw, mh, boxstyle="square,pad=0",
                            fc="#F3E7E2", ec=INK, lw=1.0, zorder=1))
ax.add_patch(FancyBboxPatch((mx, my), mw * 0.5, mh * 0.5, boxstyle="square,pad=0",
                            fc="#EAD6CE", ec="none", zorder=1.2))
ax.text(mx + mw * 0.25, my + mh * 0.25, "grounding\nHURTS", ha="center", va="center",
        fontsize=7.6, color=HURT, fontweight="bold", zorder=2)
ax.text(mx + mw * 0.72, my + mh * 0.74, "grounding\nHELPS", ha="center", va="center",
        fontsize=7.6, color=HELP, fontweight="bold", zorder=2)
# axes labels
ax.text(mx + mw / 2, my - 0.055, "latent supervision  $\\rightarrow$", ha="center", va="center",
        fontsize=7.6, color=INK)
ax.text(mx - 0.03, my + mh / 2, "closure fidelity  $\\rightarrow$", ha="center", va="center",
        fontsize=7.6, color=INK, rotation=90)
# our anchor (low-low) + two levers
ax.scatter([mx + mw * 0.16], [my + mh * 0.18], s=45, color=INK, zorder=4, edgecolor="white", lw=1.0)
ax.text(mx + mw * 0.16, my + mh * 0.05, "ours\n(2002)", ha="center", va="top", fontsize=6.4,
        color=INK, zorder=4)
arrow(ax, (mx + mw * 0.16, my + mh * 0.26), (mx + mw * 0.16, my + mh * 0.82), color=HELP,
      lw=1.5, mut=10)
ax.text(mx + mw * 0.02, my + mh * 0.55, "2010/\ndsp", ha="left", va="center", fontsize=6.2, color=HELP)
arrow(ax, (mx + mw * 0.24, my + mh * 0.16), (mx + mw * 0.80, my + mh * 0.16), color=HELP,
      lw=1.5, mut=10)
ax.text(mx + mw * 0.52, my + mh * 0.05, "TeNNet", ha="center", va="center", fontsize=6.2, color=HELP)
ax.text(mx + mw / 2, my + mh + 0.10,
        "Two levers flip the sign:\nraise closure fidelity, or supervise the latent.",
        ha="center", va="center", fontsize=8.0, color=INK)

fig.suptitle("When do true physical inputs help a learned solubility model?",
             fontsize=12.5, color=INK, y=1.03)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT}.{ext}")
print(f"wrote {OUT}.pdf / .png")
