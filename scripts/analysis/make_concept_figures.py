#!/usr/bin/env python3
"""Generate the four conceptual schematics for grounding_paradox.tex.

These are *explanatory* figures (not data plots) that carry the general
composed-predictor thesis, which the readability audit found was delivered
entirely as equations:

  fig_composed.pdf        the general pipeline x -> h -> z -> g -> y with the
                          matched free-predictor control, callouts for where
                          B_closure / B_insuff / the oracle live, and a 3-row
                          instance table (solubility / pKa / synthetic).
  fig_decomp_concept.pdf  what B = B_insuff + B_closure MEANS: conditional cloud
                          (B_insuff) vs the gap between E[m|z*] and the fixed
                          closure g(z*) (B_closure).
  fig_ident.pdf           geometry of non-identifiability: near-collinear crystal
                          and activity directions (a band of equivalent splits),
                          collapsed by an off-axis external label.
  fig_phase.pdf           the physics-tax phase picture: asymptotic closure bias
                          Delta_inf vs variance saving; the T=0 boundary splits
                          "physics helps" from "physics hurts"; solubility / pKa /
                          synthetic-dial placed on it.

Pure matplotlib + numpy (no torch/rdkit). Schematic geometry is illustrative;
only the annotated numbers (CRLB drop, dial fidelities) come from the paper.

    python scripts/analysis/make_concept_figures.py --out-dir paper/figs
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

# THE JOURNAL'S GRAPHICS SPECIFICATION, applied before any figure is created. Without it matplotlib
# emits DejaVu Sans in Type 3, and both are violations; see acs_figure_style for what and why.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from acs_figure_style import apply as _acs_apply  # noqa: E402
_acs_apply()

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch  # noqa: E402

# soft-pastel palette (mirrors make_paradox_figures.py)
SALMON = "#E8A98C"   # closure / oracle / true-input
TEAL = "#7FB5A6"     # learned representation / encoder
BLUE = "#8FB3DA"
PURPLE = "#B7A5DC"
GOLD = "#E6C87A"
GRAY = "#9AA0A6"
INK = "#4D4D4D"

_DEFAULT_STYLE = Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"


def apply_style() -> None:
    if _DEFAULT_STYLE.exists():
        plt.style.use(str(_DEFAULT_STYLE))
        # AFTER style.use, NOT BEFORE: the shared style file resets rcParams wholesale, so a
        # typeface set earlier is silently discarded. The specification has to be applied last.
        _acs_apply()
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "savefig.dpi": 300, "savefig.bbox": "tight", "figure.dpi": 150,
    # "font.family" REMOVED 2026-08-29: the figures were set in serif to match the body
    # type, and the journal asks for Helvetica or Arial in artwork. acs_figure_style now
    # owns the typeface; setting it here silently overrode that.
"font.size": 10.5,
        "axes.edgecolor": INK, "patch.linewidth": 0.0,
    })


def _box(ax, xy, w, h, text, fc, ec=INK, fs=10.5, tc=INK, lw=1.1, style="round,pad=0.02"):
    x, y = xy
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style,
                                linewidth=lw, edgecolor=ec, facecolor=fc, alpha=0.95))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc)


def _arrow(ax, p0, p1, color=INK, lw=1.6, style="-|>", ls="-", rad=0.0, mut=14, cs=None):
    conn = cs if cs is not None else f"arc3,rad={rad}"
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=mut,
                                 linewidth=lw, color=color, linestyle=ls,
                                 connectionstyle=conn, zorder=1))


def _save(fig, out_dir: Path, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"{name}.{ext}")
    plt.close(fig)


# --------------------------------------------------------------------------- #
def fig_composed(out_dir: Path) -> None:
    fig = plt.figure(figsize=(8.2, 4.64))
    gs = fig.add_gridspec(2, 1, height_ratios=[2.15, 1.0], hspace=0.28)
    ax = fig.add_subplot(gs[0]); ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")

    yb = 3.1                      # main pipeline row
    bw, bh = 1.55, 0.95
    xs = [0.15, 2.15, 4.15, 6.15, 8.15]
    _box(ax, (xs[0], yb), bw, bh, "input $x$\n(molecular\ngraphs)", "white", fs=9.5)
    _box(ax, (xs[1], yb), bw, bh, "encoder $h$\n(learned)", TEAL, fs=10)
    _box(ax, (xs[2], yb), bw, bh, "intermediate\n$z=h(x)$", BLUE, fs=10)
    _box(ax, (xs[3], yb), bw, bh, "fixed closure\n$g$", SALMON, fs=10)
    _box(ax, (xs[4], yb), bw, bh, r"$\hat y=g(h(x))$", "white", fs=10)
    for i in range(4):
        _arrow(ax, (xs[i] + bw, yb + bh / 2), (xs[i + 1], yb + bh / 2))

    # callouts
    ax.annotate("oracle $z^\\star$ available\n(external ground truth)",
                xy=(xs[2] + bw / 2, yb + bh), xytext=(xs[2] + bw / 2, yb + bh + 0.9),
                ha="center", va="bottom", fontsize=8.6, color=BLUE,
                arrowprops=dict(arrowstyle="-", color=BLUE, lw=1.0))
    ax.text(xs[2] + bw / 2, yb - 0.28, "$B_{\\mathrm{insuff}}$ lives here\n(inputs can't resolve)",
            ha="center", va="top", fontsize=8.4, color=BLUE)
    ax.text(xs[3] + bw / 2, yb - 0.28, "$B_{\\mathrm{closure}}$ lives here\n(fixed map is wrong)",
            ha="center", va="top", fontsize=8.4, color="#C67A54")

    # matched control branch
    yd = 1.0
    _box(ax, (xs[4], yd), bw, bh, "$\\hat y_{\\mathrm{direct}}$\n(no closure)", "white",
         ec=GRAY, tc=GRAY, fs=9.5, lw=1.1)
    _arrow(ax, (xs[1] + bw / 2, yb), (xs[4], yd + bh / 2), color=GRAY, ls=(0, (4, 3)),
           cs="angle,angleA=-90,angleB=180,rad=12")
    ax.text(4.15, 1.05, "matched control: shares $h$, drops $g$", ha="center", va="center",
            fontsize=8.6, color=GRAY, style="italic")
    ax.text(xs[4] + bw / 2, yd - 0.28,
            "physics tax $=R_{\\mathrm{phys}}-R_{\\mathrm{direct}}$",
            ha="center", va="top", fontsize=8.6, color=INK)

    # instance table
    axt = fig.add_subplot(gs[1]); axt.axis("off")
    cols = ["", "input $x$", "encoder $h$", "intermediate $z$", "fixed closure $g$", "target $y$"]
    rows = [
        ["solubility", "solute+solvent\ngraphs", "MPNN", "$\\sigma$-profile",
         "COSMO-SAC", "$\\ln x_2$"],
        ["pKa", "molecular\ngraph", "MPNN", "Hammett $\\sigma$",
         "LFER $pK_{a0}\\!-\\!\\rho\\sigma$", "$pK_a$"],
        ["synthetic", "features", "MLP", "latent $z$",
         "deformed teacher", "$m$"],
    ]
    tbl = axt.table(cellText=rows, colLabels=cols, cellLoc="center", loc="center",
                    bbox=[0.0, 0.0, 1.0, 1.0])
    tbl.auto_set_font_size(False); tbl.set_fontsize(8.6)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#D9D9D9")
        if r == 0:
            cell.set_text_props(color=INK, fontweight="bold"); cell.set_facecolor("#F2F2F2")
        if c == 0 and r > 0:
            cell.set_text_props(color=INK, fontweight="bold")
        if c == 3 and r > 0:
            cell.set_facecolor("#EAF1F9")
        if c == 4 and r > 0:
            cell.set_facecolor("#FBEDE4")
    axt.set_title("the same abstraction, three instances", fontsize=9.5, color=INK, pad=2)
    _save(fig, out_dir, "fig_composed")


# --------------------------------------------------------------------------- #
def fig_decomp_concept(out_dir: Path) -> None:
    rng = np.random.default_rng(0)
    z = np.linspace(0.2, 4.8, 220)
    Emz = 1.35 * np.sin(0.55 * z) + 0.32 * z          # E[m|z*], best any map reaches
    scatter_z = rng.uniform(0.2, 4.8, 150)
    cond_mean = 1.35 * np.sin(0.55 * scatter_z) + 0.32 * scatter_z
    m = cond_mean + rng.normal(0, 0.42, scatter_z.size)  # irreducible spread = B_insuff
    g = Emz - (0.55 + 0.16 * z)                        # fixed closure, systematically off

    fig, ax = plt.subplots(figsize=(6.4, 4.5))
    ax.fill_between(z, Emz - 0.42, Emz + 0.42, color=BLUE, alpha=0.20, lw=0,
                    label=r"$B_{\mathrm{insuff}}=\mathbb{E}\,\mathrm{Var}(m\,|\,z^\star)$")
    ax.scatter(scatter_z, m, s=12, color=BLUE, alpha=0.55, edgecolor="none", zorder=2)
    ax.plot(z, Emz, color=INK, lw=2.2, zorder=4, label=r"$\mathbb{E}[m\,|\,z^\star]$ (best any map reaches)")
    ax.plot(z, g, color=SALMON, lw=2.4, zorder=4, label=r"fixed closure $g(z^\star)$")
    # B_closure gap shading at a representative z
    zc = 3.5
    yb_top = np.interp(zc, z, Emz); yb_bot = np.interp(zc, z, g)
    ax.annotate("", xy=(zc, yb_top), xytext=(zc, yb_bot),
                arrowprops=dict(arrowstyle="<->", color="#C67A54", lw=1.8))
    ax.text(zc + 0.12, (yb_top + yb_bot) / 2,
            r"$B_{\mathrm{closure}}$" "\n(map is off the\nconditional mean)",
            ha="left", va="center", fontsize=9, color="#C67A54")
    ax.annotate("feed true $z^\\star$ through $g$\n$\\rightarrow$ lands here, not on $\\mathbb{E}[m|z^\\star]$",
                xy=(1.15, np.interp(1.15, z, g)), xytext=(2.25, -0.32),
                ha="left", va="center", fontsize=8.6, color="#C67A54",
                arrowprops=dict(arrowstyle="-|>", color="#C67A54", lw=1.2))
    ax.set_xlabel(r"physical intermediate $z^\star$ (1-D summary)")
    ax.set_ylabel(r"activity target $m$")
    ax.set_title("What the closure/insufficiency split means", fontsize=12)
    ax.legend(loc="upper left", fontsize=8.4, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, out_dir, "fig_decomp_concept")


# --------------------------------------------------------------------------- #
def fig_ident(out_dir: Path) -> None:
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.0, 4.3))
    for ax in (a1, a2):
        ax.set_xlim(-0.2, 3.2); ax.set_ylim(-0.2, 3.2); ax.set_aspect("equal"); ax.axis("off")

    # (a) near-collinear crystal & activity directions + band of equivalent splits
    cry = np.array([2.7, 1.9]); act = np.array([2.9, 2.35])
    a1.add_patch(FancyArrowPatch((0, 0), tuple(cry), arrowstyle="-|>", mutation_scale=16,
                                 lw=2.4, color=SALMON))
    a1.add_patch(FancyArrowPatch((0, 0), tuple(act), arrowstyle="-|>", mutation_scale=16,
                                 lw=2.4, color=TEAL))
    a1.text(2.75, 2.52, r"activity $\ln\gamma^\infty\propto 1/T$", fontsize=9, color=TEAL, ha="right")
    a1.text(2.5, 0.98, r"crystal $\Phi\propto(1/T-1/T_m)$", fontsize=9, color=SALMON, ha="center")
    thetas = np.linspace(np.arctan2(cry[1], cry[0]), np.arctan2(act[1], act[0]), 30)
    for t in thetas:
        a1.plot([0, 3.05 * np.cos(t)], [0, 3.05 * np.sin(t)], color=GRAY, lw=0.6, alpha=0.30, zorder=0)
    a1.text(2.42, 0.42, "family of equivalent splits\n(profiled Fisher info, $\\Delta H_{\\mathrm{fus}}$ free)",
            fontsize=8.2, color=GRAY, ha="center")
    a1.set_title("(a) solubility alone: split unrecoverable", fontsize=10.5)

    # (b) external label collapses the band
    ext = np.array([0.4, 2.8])
    a2.add_patch(FancyArrowPatch((0, 0), tuple(cry), arrowstyle="-|>", mutation_scale=16,
                                 lw=2.4, color=SALMON))
    a2.add_patch(FancyArrowPatch((0, 0), tuple(act), arrowstyle="-|>", mutation_scale=16,
                                 lw=2.4, color=TEAL))
    a2.add_patch(FancyArrowPatch((0, 0), tuple(ext), arrowstyle="-|>", mutation_scale=16,
                                 lw=2.6, color=PURPLE))
    a2.text(ext[0] - 0.05, ext[1] + 0.12, "external\nsingle-component\nlabel (off-axis)",
            fontsize=8.6, color=PURPLE, ha="center")
    a2.scatter([cry[0]], [cry[1]], s=60, color=INK, zorder=5)
    a2.annotate("split pinned", xy=(cry[0], cry[1]), xytext=(2.7, 1.24),
                ha="center", va="top", fontsize=8.6, color=INK,
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0, shrinkA=3, shrinkB=5))
    a2.text(1.55, 0.35, r"CRLB sd($\Delta H_{\mathrm{fus}}$):" "\n"
            r"$19{,}895\rightarrow1{,}689$ J/mol",
            fontsize=8.6, color=INK, ha="center")
    a2.set_title("(b) an off-axis label collapses the band", fontsize=10.5)
    fig.suptitle("Why the crystal/activity split is non-identifiable", fontsize=12, y=1.0)
    _save(fig, out_dir, "fig_ident")


# --------------------------------------------------------------------------- #
def fig_phase(out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    lim = 1.0
    # T = Delta_inf - variance_saving ; boundary Delta_inf = variance_saving
    ax.fill_between([0, lim], [0, lim], [lim, lim], color=SALMON, alpha=0.16, lw=0)   # hurts (upper-left)
    ax.fill_between([0, lim], [0, 0], [0, lim], color=TEAL, alpha=0.16, lw=0)         # helps (lower-right)
    ax.plot([0, lim], [0, lim], color=INK, lw=1.6, ls="--")
    ax.text(0.24, 0.80, "physics HURTS\n$(\\Delta_\\infty>$ variance saved$)$", color="#C67A54",
            fontsize=10, ha="center", fontweight="bold")
    ax.text(0.74, 0.20, "physics HELPS\n$(\\Delta_\\infty<$ variance saved$)$", color="#3F7A6B",
            fontsize=10, ha="center", fontweight="bold")
    ax.text(0.62, 0.66, "$T=0$", color=INK, fontsize=9.5, rotation=39)

    # solubility / COSMO-SAC: high bias, and n grows -> variance saving shrinks (moves left)
    ax.scatter([0.30], [0.72], s=90, color=SALMON, edgecolor=INK, zorder=5)
    ax.annotate("solubility\n(COSMO-SAC)", xy=(0.30, 0.72), xytext=(0.10, 0.55),
                fontsize=9, color=INK, ha="center",
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0))
    ax.annotate("", xy=(0.12, 0.72), xytext=(0.30, 0.72),
                arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.4))
    ax.text(0.20, 0.755, "$n$ grows", fontsize=7.8, color=GRAY, ha="center")

    # pKa: trained comparison lands in "helps" (physics 1.47 < DirectGNN 1.88)
    ax.scatter([0.60], [0.09], s=80, color=BLUE, edgecolor=INK, zorder=5)
    ax.annotate("pKa (Hammett,\ntrained): helps", xy=(0.60, 0.09), xytext=(0.46, 0.19),
                fontsize=8.6, color=INK, ha="center",
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.0))

    # synthetic dial ticks climbing Delta_inf as fidelity F drops
    for F, yv in [(1.00, 0.03), (0.76, 0.30), (0.38, 0.60)]:
        ax.scatter([0.42], [yv], s=42, color=GOLD, edgecolor=INK, zorder=5)
        ax.text(0.455, yv, f"$F={F:.2f}$", fontsize=7.6, color=INK, va="center")
    ax.annotate("synthetic dial\n(fidelity $F\\downarrow$)", xy=(0.42, 0.30), xytext=(0.60, 0.44),
                fontsize=8.4, color="#9A8425", ha="left", va="center",
                arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=1.0, shrinkA=3, shrinkB=4))

    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.set_xlabel("estimation-variance saving  $V_{\\mathrm{direct}}-V_{\\mathrm{phys}}$  (grows at small $n$)")
    ax.set_ylabel("asymptotic closure bias  $\\Delta_\\infty=B_{\\mathrm{closure}}-\\Gamma$")
    ax.set_title("When a physics prior helps vs. hurts", fontsize=12)
    ax.set_xticks([]); ax.set_yticks([])
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, out_dir, "fig_phase")


def fig_arch(out_dir: Path) -> None:
    # WHAT SETS THE PRINTED TYPE SIZE HERE.  The figure is set at \textwidth (504.5 pt) and
    # savefig trims to the drawn content, so on the page
    #     printed box  = (box in data units) x 504.5 / (content extent in data units)
    #     printed type = (point size below)  x 504.5 / (72 x canvas width in inches)
    # The first does not involve the canvas and the second does not involve the geometry, so
    # shrinking the canvas -- or raising a point size -- grows the TYPE relative to the BOXES
    # and nothing else.  Check the boxes, not only the type sizes, if either moves.  The
    # cheapest way to buy printed type size is to stop some label overhanging the right edge:
    # the content extent is in the denominator above, and the boxes end at x = 12.15.
    fig, ax = plt.subplots(figsize=(8.85, 4.35))
    ax.set_xlim(0, 12.4); ax.set_ylim(0, 6.2); ax.axis("off")

    # 9.8 pt is the smallest base at which a mathtext sub/superscript (0.7x) clears 6 pt on
    # the page at this figure's scale, so every label carrying one is set at 9.8.
    FS_SUB = 9.8

    # inputs
    _box(ax, (0.15, 4.35), 1.5, 0.7, "solute\ngraph", "white", fs=9)
    _box(ax, (0.15, 3.05), 1.5, 0.7, "solvent\ngraph", "white", fs=9)
    # shared encoder
    _box(ax, (2.05, 3.05), 1.5, 2.0, "shared\nencoder $h$", TEAL, fs=10)
    _arrow(ax, (1.65, 4.7), (2.05, 4.5)); _arrow(ax, (1.65, 3.4), (2.05, 3.6))
    # heads
    _box(ax, (3.95, 4.55), 1.55, 0.85, "crystal\nhead", BLUE, fs=9)
    _box(ax, (3.95, 3.05), 1.55, 0.85, "$\\sigma$-profile\nhead", BLUE, fs=9)
    _arrow(ax, (3.55, 4.55), (3.95, 4.75)); _arrow(ax, (3.55, 3.55), (3.95, 3.45))
    # closure
    _box(ax, (6.35, 3.05), 1.7, 0.85, "COSMO-SAC\nclosure $g$", SALMON, fs=9.5)
    _arrow(ax, (5.5, 3.47), (6.35, 3.47))
    ax.text(5.9, 3.70, "$\\hat z$", fontsize=9, color=INK, ha="center")
    ax.text(5.9, 3.22, "$B_{\\mathrm{insuff}}$", fontsize=FS_SUB, color=BLUE,
            ha="center", va="top")
    ax.text(7.0, 2.96, "$B_{\\mathrm{closure}}$", fontsize=FS_SUB, color="#C67A54",
            ha="center", va="top")
    # sigma-oracle injection
    # The box is sized to its longest run, "(reference VT-2005)": at 1.7 units and 8.4 pt that
    # run left the box on both sides.  Its floor sits at 1.60, not 1.35, because the grey
    # matched-control arc passes under it at y = 1.36 and used to cut its lower-right corner.
    # Two text objects, not one two-line label: the first line carries the superscript star,
    # which mathtext sets at 0.7x and which therefore needs a 9.8 pt base, while the second
    # line at 9.8 pt would be wider than the box.  Neither line has a sub/superscript the
    # other needs.
    _box(ax, (6.05, 1.60), 2.3, 0.75, "", "#F3D4C4", ec=SALMON)
    ax.text(7.20, 2.16, "$\\sigma$-oracle $z^\\star$", ha="center", va="center",
            fontsize=FS_SUB, color=INK)
    ax.text(7.20, 1.80, "(reference VT-2005)", ha="center", va="center",
            fontsize=8.6, color=INK)
    _arrow(ax, (7.6, 2.35), (7.6, 3.05), color=SALMON, ls=(0, (3, 2)))
    ax.text(7.72, 2.60, "replaces $\\hat z$", fontsize=8.2, color="#C67A54", ha="left")
    # SLE solver
    _box(ax, (8.75, 3.5), 1.5, 1.25, "SLE\nsolver", PURPLE, fs=9.5)
    _arrow(ax, (5.5, 4.95), (8.75, 4.55), rad=-0.12)     # Phi(T) from crystal head
    ax.text(7.0, 5.02, "$\\Phi(T)$", fontsize=8.8, color=INK, ha="center")
    _arrow(ax, (8.05, 3.47), (8.75, 3.9))                 # ln gamma from closure
    # Under this arrow, not on it: the shaft crosses y = 3.70 at x = 8.40, and a label whose
    # baseline sat at 3.50 had the shaft running through its own glyphs.
    ax.text(8.42, 3.36, "$\\ln\\gamma_2$", fontsize=FS_SUB, color=INK, ha="center", va="top")
    # output
    _box(ax, (10.55, 3.75), 1.6, 0.8, "$\\ln x_2$", "white", fs=10)
    _arrow(ax, (10.25, 4.12), (10.55, 4.15))
    # DirectGNN control branch (solid)
    _box(ax, (8.75, 1.15), 1.5, 0.8, "DirectGNN\n(no closure)", "white", ec=GRAY, tc=GRAY, fs=8.6)
    _arrow(ax, (2.75, 2.9), (8.75, 1.55), color=GRAY, lw=1.8, rad=0.42)  # dips below the closure/oracle boxes
    ax.text(5.3, 0.5, "matched control: shares $h$, drops $g$", fontsize=8.2, color=GRAY,
            style="italic", ha="center")
    _box(ax, (10.55, 1.15), 1.6, 0.8, "$\\ln x_2$\n(direct)", "white", ec=GRAY, tc=GRAY,
         fs=FS_SUB)
    _arrow(ax, (10.25, 1.55), (10.55, 1.55), color=GRAY)
    ax.annotate("", xy=(11.35, 3.75), xytext=(11.35, 1.95),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=1.2))
    # Left of the arrow, not right of it: to the right this label overhung the boxes by
    # 0.7 data units, and that overhang is what the whole graphic was scaled down to fit.
    ax.text(11.20, 2.85, "physics tax\n$R_{\\mathrm{phys}}-R_{\\mathrm{direct}}$",
            fontsize=FS_SUB, color=INK, ha="right", va="center", multialignment="right")
    _save(fig, out_dir, "fig_architecture")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="paper/figs")
    args = ap.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    apply_style()
    fig_composed(out)
    fig_decomp_concept(out)
    fig_ident(out)
    fig_phase(out)
    fig_arch(out)
    print(f"wrote fig_composed/fig_decomp_concept/fig_ident/fig_phase/fig_architecture (.pdf/.png) to {out}")


if __name__ == "__main__":
    main()
