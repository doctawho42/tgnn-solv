#!/usr/bin/env python3
"""One unifying overview / graphical-abstract figure carrying the whole story in a
single view, so the formal theory can be stated (not walked through) in the main text
and its proofs moved to the ESI.

Top row -- three acts, left to right:
  1. The paradox     -- molecule -> encoder -> sigma -> fixed COSMO-SAC closure -> ln x2;
                         swapping the learned sigma-hat for the reference sigma makes it WORSE.
  2. The measurement -- the external oracle splits the reference-input error into
                         B_closure (closure wrong even given truth) + B_insuff (inputs
                         insufficient); here the closure binds.
  3. The lever       -- ONE axis: closure fidelity. Raise it (2002 -> 2010/dsp) and
                         grounding flips from hurt to help. Latent supervision is a
                         second lever, left to future work.

Bottom row -- the claims ledger, graded by strength of evidence (folds in the old Table 2):
  Certified / Likely / Exploratory, colour-coded green -> amber -> gray.

    MPLBACKEND=Agg python scripts/analysis/make_overview_figure.py
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# palette shared with make_concept_figures.py
SALMON = "#E8A98C"   # fixed closure / reference (oracle) inputs
TEAL = "#7FB5A6"     # learned representation / encoder
INK = "#4D4D4D"
GRAY = "#9AA0A6"
HURT = "#C8674F"     # grounding hurts
HELP = "#4A806F"     # grounding helps
AMBER = "#C08A2E"    # likely (sub-threshold) claims
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


fig = plt.figure(figsize=(11.4, 6.5))
gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.46], hspace=0.06,
                      left=0.012, right=0.988, top=0.92, bottom=0.02)
ax = fig.add_subplot(gs[0]); ax.set_xlim(0, 3.0); ax.set_ylim(0, 1.0); ax.axis("off")
axl = fig.add_subplot(gs[1]); axl.set_xlim(0, 3.0); axl.set_ylim(0, 1.0); axl.axis("off")

# ---- act panels (soft backing cards) ----
for i, (x0, title) in enumerate([(0.02, "1. The paradox"),
                                  (1.03, "2. The measurement"),
                                  (2.04, "3. No lever found")]):
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

# the swap: reference sigma -> worse
box(ax, 0.52, 0.30, 0.14, 0.12, r"$\sigma^\star$", SALMON, fs=10.5, tc=INK, lw=0)
ax.text(0.44, 0.36, "swap in\nreference $\\sigma$", ha="right", va="center", fontsize=7.6, color=INK)
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
ax.text(cx + 0.47, 0.80, "the reference input has an external oracle (VT-2005),", ha="center",
        va="center", fontsize=7.8, color=GRAY, style="italic")
ax.text(cx + 0.47, 0.735, "so the reference-input error splits exactly:", ha="center",
        va="center", fontsize=7.8, color=GRAY, style="italic")
# B = B_closure + B_insuff bar
ax.text(cx + 0.47, 0.62, r"$B \;=\; B_{\mathrm{closure}} \;+\; B_{\mathrm{insuff}}$",
        ha="center", va="center", fontsize=12.5, color=INK)
# stacked bar: closure large, insuff small
bx, by, bw = cx + 0.14, 0.42, 0.68
frac = 0.72
ax.add_patch(FancyBboxPatch((bx, by), bw * frac, 0.10, boxstyle="square,pad=0",
                            fc=SALMON, ec=INK, lw=0.8, zorder=3))
ax.add_patch(FancyBboxPatch((bx + bw * frac, by), bw * (1 - frac), 0.10, boxstyle="square,pad=0",
                            fc="#DDE7E3", ec=INK, lw=0.8, zorder=3))
ax.text(bx + bw * frac / 2, by + 0.05, "closure is wrong", ha="center", va="center",
        fontsize=7.8, color=INK, zorder=4)
ax.text(bx + bw * frac + bw * (1 - frac) / 2, by + 0.05, "inputs\ninsuff.", ha="center",
        va="center", fontsize=6.0, color="#5F6B66", zorder=4)
ax.text(cx + 0.47, 0.29, r"$B_{\mathrm{closure}} > B_{\mathrm{insuff}}$"
        "   ($P_{\\mathrm{boot}}\\approx0.78$)",
        ha="center", va="center", fontsize=9.2, color=INK, fontweight="bold")
ax.text(cx + 0.47, 0.135, "The ceiling is the CLOSURE,\nnot the inputs.", ha="center",
        va="center", fontsize=9.0, color="#B5654A", fontweight="bold")

# chevron 2 -> 3
arrow(ax, (1.965, 0.5), (2.04, 0.5), color=INK, lw=2.2, mut=18)

# ===================== ACT 3: no lever found (2002 vs 2010/dsp, two sets) =====================
mx0 = 2.10
ax.text(mx0 + 0.43, 0.80, "The obvious fix---a better closure---\ndoes not hold up on representative data.",
        ha="center", va="center", fontsize=8.0, color=INK)
# two paired-bar groups: MSE(2002) vs MSE(2010/dsp) on the curated corner and the representative set
base_y, bw, scale = 0.34, 0.052, 0.165
groups = [(mx0 + 0.10, "curated\n$n{=}60$", 1.757, 0.765, "$+56\\%$,\ngrazes 0", "2010\n(no dsp)"),
          (mx0 + 0.52, "represent.\n$n{=}477$", 1.911, 1.855, "$+3\\%$,\nnot sig.", "2010/\ndsp")]
for gx, glab, m02, m10, note, mlab in groups:
    for dx, val, col, lab in [(-0.035, m02, SALMON, "2002"), (0.035, m10, TEAL, mlab)]:
        ax.add_patch(FancyBboxPatch((gx + dx - bw / 2, base_y), bw, val * scale,
                                    boxstyle="square,pad=0", fc=col, ec=INK, lw=0.7, zorder=3))
        ax.text(gx + dx, base_y + val * scale + 0.016, f"{val:.2f}", ha="center", va="bottom",
                fontsize=5.6, color=INK)
        ax.text(gx + dx, base_y - 0.032, lab, ha="center", va="top", fontsize=5.5, color=col)
    ax.text(gx, base_y - 0.115, glab, ha="center", va="top", fontsize=6.6, color=INK, fontweight="bold")
    ax.text(gx, 0.705, note, ha="center", va="bottom", fontsize=5.8, color=GRAY, style="italic")
ax.text(mx0 + 0.43, 0.115, "No closure-fidelity lever established.", ha="center", va="center",
        fontsize=8.0, color="#B5654A", fontweight="bold")

# ===================== BOTTOM ROW: the claims ledger =====================
ledger = [
    (0.02, "CERTIFIED", HELP, "#EAF1EE", [
        r"Symptom: reference $\sigma$ makes solubility worse (3 seeds, $n{=}5608$)",
        r"Exact split $B=B_{\mathrm{closure}}+B_{\mathrm{insuff}}$ (Lemma 2)",
        r"pKa oracle-swap flip: meta/para helped, ortho hurt ($20/20$, $P{=}1.00$)",
    ]),
    (1.03, "LIKELY", AMBER, "#F6EEDD", [
        r"Mechanism: latent $=$ low-rank, transferable surrogate ($n{=}44$)",
        r"Closure is the larger term, low-$\gamma$ set: $P_{\mathrm{boot}}{\approx}0.78$",
        r"Attribution on the matched $n{=}60$ corner (no transfer)",
    ]),
    (2.04, "OPEN", GRAY, "#F0F0F0", [
        r"No fidelity lever: $2002{\to}2010$/dsp $+3\%$ ($n{=}477$, $P{=}0.62$)",
        r"Transfer of the attribution to finite composition",
        r"Whether the drift is the closure's signed inverse $J^{+}(m{-}g)$",
    ]),
]
axl.text(0.02, 0.955, "What the paper establishes, graded by evidence",
         ha="left", va="center", fontsize=8.6, color=INK, fontweight="bold")
for x0, head, col, band, items in ledger:
    axl.add_patch(FancyBboxPatch((x0, 0.06), 0.94, 0.80,
                                 boxstyle="round,pad=0.006,rounding_size=0.02",
                                 fc="white", ec=col, lw=1.2, zorder=1))
    # header band
    axl.add_patch(FancyBboxPatch((x0, 0.66), 0.94, 0.20,
                                 boxstyle="round,pad=0.006,rounding_size=0.02",
                                 fc=band, ec="none", zorder=1.5))
    axl.text(x0 + 0.03, 0.76, head, ha="left", va="center", fontsize=8.6,
             color=col, fontweight="bold", zorder=3)
    for j, it in enumerate(items):
        yy = 0.52 - j * 0.165
        axl.scatter([x0 + 0.045], [yy], s=18, color=col, zorder=3, edgecolor="none")
        axl.text(x0 + 0.075, yy, it, ha="left", va="center", fontsize=6.9,
                 color=INK, zorder=3)

fig.suptitle("When do reference physical inputs help a learned solubility model?",
             fontsize=12.5, color=INK, y=0.975)
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT}.{ext}")
print(f"wrote {OUT}.pdf / .png")
