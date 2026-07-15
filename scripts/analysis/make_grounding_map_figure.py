#!/usr/bin/env python3
"""The grounding map: whether feeding true physical inputs helps or hurts a learned
model is governed by two axes -- latent supervision (x) and closure fidelity (y).
Conceptual schematic with the three real anchors + the synthetic dial.

    MPLBACKEND=Agg python scripts/analysis/make_grounding_map_figure.py
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch

INK = "#2B2B2B"
SALMON = "#E3927B"   # grounding hurts
TEAL = "#7FB5A6"     # grounding helps
OUT = Path(__file__).resolve().parents[2] / "paper" / "figs" / "fig_grounding_map"

fig, ax = plt.subplots(figsize=(7.2, 5.0))

# helps if supervision + fidelity exceed a threshold; hurts in the low-low corner.
xx, yy = np.meshgrid(np.linspace(0, 1, 400), np.linspace(0, 1, 400))
helps = (xx + yy) > 0.85
ax.imshow(np.where(helps, 1.0, 0.0), extent=[0, 1, 0, 1], origin="lower",
          cmap=matplotlib.colors.ListedColormap([SALMON, TEAL]), alpha=0.20, aspect="auto")
# boundary (physics-tax T=0)
bx = np.linspace(0, 0.85, 100)
ax.plot(bx, 0.85 - bx, color=INK, lw=1.4, ls="--", alpha=0.7)
ax.text(0.50, 0.07, "grounding hurts", color="#B5654A", fontsize=13, ha="center", va="bottom", fontweight="bold")
ax.text(0.72, 0.94, "grounding helps", color="#4A806F", fontsize=13, ha="center", va="top", fontweight="bold")
ax.text(0.79, 0.13, r"physics-tax $\mathcal{T}=0$", color=INK, fontsize=8.5, rotation=-38, alpha=0.7)

def anchor(x, y, label, sub, dx=8, dy=8, ha="left", va="bottom"):
    ax.scatter([x], [y], s=95, color=INK, zorder=5, edgecolor="white", linewidth=1.1)
    ax.annotate(f"{label}\n{sub}", (x, y), xytext=(dx, dy), textcoords="offset points",
                fontsize=9, color=INK, ha=ha, va=va,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=INK, alpha=0.92, lw=0.6),
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.7, alpha=0.5,
                                shrinkA=2, shrinkB=3))

# ours: end-to-end sigma, low-fidelity 2002 closure -> hurts (the grounding paradox)
anchor(0.13, 0.17, "Ours (end-to-end $\\hat\\sigma$,", "COSMO-SAC-2002) $\\to$ hurts", dx=12, dy=6)
# closure-fidelity axis: 2010/dsp on true inputs -> crosses the boundary (verdict flips)
anchor(0.14, 0.80, "COSMO-SAC-2010/dsp", "(true inputs) $\\to$ flips to inputs", dx=12, dy=6)
arr = FancyArrowPatch((0.135, 0.24), (0.14, 0.73), arrowstyle="-|>", mutation_scale=14,
                      color="#4A806F", lw=1.8, zorder=4)
ax.add_patch(arr)
ax.text(0.155, 0.47, "raise closure\nfidelity", color="#4A806F", fontsize=8.5, va="center")
# latent-supervision axis: TeNNet supervised sigma -> helps (box sits just above its dot)
anchor(0.80, 0.35, "TeNNet-SAC", "(supervised $\\sigma$) $\\to$ helps", dx=0, dy=15, ha="center")
arr2 = FancyArrowPatch((0.45, 0.235), (0.75, 0.345), arrowstyle="-|>", mutation_scale=14,
                       color="#4A806F", lw=1.8, zorder=4)  # starts past the Ours box edge
ax.add_patch(arr2)
ax.text(0.60, 0.225, "supervise the latent", color="#4A806F", fontsize=8.5, ha="center", va="top")
# synthetic dial: swept closure fidelity
ax.plot([0.40, 0.40], [0.10, 0.90], color=INK, lw=1.0, ls=":", alpha=0.5)
ax.text(0.405, 0.985, "synthetic fidelity dial", color=INK, fontsize=8, va="top", ha="center", alpha=0.7)

ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_xlabel("latent supervision  (end-to-end $\\to$ supervised toward truth)", fontsize=11)
ax.set_ylabel("closure fidelity  (misspecified $\\to$ accurate)", fontsize=11)
ax.set_xticks([]); ax.set_yticks([])
ax.set_title("When do true physical inputs help a learned model? A two-axis map", fontsize=12)
for s in ax.spines.values():
    s.set_edgecolor(INK); s.set_linewidth(0.8)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT}.{ext}", dpi=200, bbox_inches="tight")
print(f"wrote {OUT}.pdf / .png")
