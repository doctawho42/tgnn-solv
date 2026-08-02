#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Draw the stratified closure map -- the figure that REPLACES the aggregate decomposition bar.

WHY THIS SCRIPT EXISTS
----------------------
`make_paradox_figures.fig_decomposition` drew ONE bar for the whole broad IDAC set, cut at
the headline B_insuff^up, plus a swarm of the other reported bounds.  That aggregate does
not survive the manuscript's own two robustness operations applied together (chemistry cut
+ pair unit takes +0.50 to -0.38), and it is carried by one publication (deleting
10.1021/acs.jced.7b00114 takes +0.509 to +0.184 while the other fourteen deletions leave it
in [+0.42, +0.87]).  So the aggregate is retired and the same instrument is reported as a
MAP of where the closure binds.

The structural reason the map is the right output, and the thing this figure has to make
visible at a glance:

  B_insuff^up is nearly stratum-independent -- every stratum is binned the same way (8
  equal-count bins of one scalar), so every stratum gets nearly the same bound.  Row unit,
  deployed convention, across the six solvent classes where the estimate exists at all,
  B_insuff^up spans 0.108-0.733 (x6.8) while MSE spans 0.089-4.569 (x51).  The aggregate
  margin is therefore a composition-weighted average of a quantity that varies by ~50x
  offset against one that is essentially constant, and it will report "the map binds" for
  any set whose composition happens to include a stratum the closure fails on.

WHAT IS DRAWN, panel by panel (all three share the stratum rows; row order is the headline
margin, descending, so the map reads top-down as "where to spend grounding effort"):

  (a) the decomposition, per stratum, at the headline cell: a teal bar 0 -> B_insuff^up
      and a salmon bar B_insuff^up -> MSE, exactly the two blocks the retired aggregate bar
      had, now one row per stratum.  The teal blocks line up in a sliver; the salmon blocks
      do not.  Where the bound exceeds the total error (aprotic acceptors) the teal block
      runs past MSE and is drawn pale, with the total marked by its own tick.
      Two brackets in the header strip carry the spans as ratios.
  (b) the margin MSE - 2 B_insuff^up with its 90% two-way cluster-bootstrap interval, on an
      axis zoomed to the region where the verdicts actually differ.  The other three
      unit x convention cells are drawn as grey ticks on the same row, so a sign flip
      between conventions or units is visible without a second panel.  Marker shape and
      colour are the verdict; a hollow marker is a stratum below the boundable size.
  (c) the composition: each stratum's share of the set's squared error, with the share
      carried by its single largest source publication drawn dark inside it, and a tick at
      the stratum's share of ROWS.  Bar past tick = the stratum carries more of the error
      than its size; the aggregate row is the whole set, which is what an aggregate averages.

Everything is read from the committed artifact
`results/b_insuff/stratified_map_table.csv` (produced by
`scripts/analysis/run_b_insuff_stratified_map.py`, which owns the stratification rule, the
estimator and the bootstrap).  Nothing is hard-coded, including the verdicts: the verdict
rule is applied here to the deposited cells so the figure cannot drift from the table.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/make_stratified_map_figure.py

Writes paper/figs/fig_decomposition.{pdf,png} -- the SAME stem the retired aggregate figure
used, because this figure replaces it in place.  Edits no .tex.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

# Palette and its meanings are shared with make_paradox_figures.py and
# make_overview_figure.py.  TEAL = the input-insufficiency term, SALMON = the
# model-misspecification term.  Do not invert one without the others.
SALMON = "#E8A98C"
TEAL = "#7FB5A6"
GRAY = "#9AA0A6"
INK = "#4D4D4D"
HURT = "#B5654A"
PALE = "#D9D9D9"

_DEFAULT_STYLE = Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"

# The headline cell.  Held fixed for every stratum: 8 equal-count bins of g(z*), Bessel
# within-bin variance, row unit, deployed (residual-only) combinatorial convention.
UNIT, CONV = "row", "res"
BOUNDABLE_N = 40          # 8 bins x >= 5 rows; the artifact carries the same flag
P_GATE = 0.90             # the verdict rule's bootstrap-frequency gate

XMAX_A = 5.0              # panel (a): two rows run past this and are drawn with a cap
XLO_B, XHI_B = -0.85, 7.0  # panel (b)

DISPLAY = {
    "water": "water",
    "glycol_ether": "glycol ether",
    "mono_alcohol": "mono-alcohol",
    "nh_protic": "N–H protic",
    "aryl_ether": "aryl ether",
    "aprotic_acceptor": "aprotic acceptor",
    "halogenated": "halogenated",
    "aromatic_hydrocarbon": "aromatic hydrocarbon",
    "aliphatic_hydrocarbon": "aliphatic hydrocarbon",
    "water_solute": "water as solute",
    "organic_solute": "organic solute",
    "all": "whole set",
}

BINDS, NOBIND, UNSET, NOMEAS = "binds", "does not bind", "not established", "not measurable"
VERDICT_STYLE = {
    BINDS: dict(marker="o", color=SALMON, size=30),
    NOBIND: dict(marker="s", color=TEAL, size=27),
    UNSET: dict(marker="D", color=GRAY, size=22),
}


def apply_style(style: str | None) -> None:
    path = Path(style) if style else _DEFAULT_STYLE
    if path.exists():
        plt.style.use(str(path))
        return
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.05,
        "figure.dpi": 200, "font.family": "sans-serif", "font.size": 11,
        "axes.edgecolor": INK, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "patch.linewidth": 0.0,
    })


# --------------------------------------------------------------------------- #
def verdict(cells: pd.DataFrame) -> str:
    """The manuscript's verdict rule, applied to the cells the artifact actually carries.

    BINDS            every available unit x convention cell has a positive margin AND
                     P_boot >= 0.90 in all of them.
    DOES NOT BIND    every available cell has a negative margin.  (Sign only: the negative
                     verdict is not confidence-gated, and the legend says so.)
    NOT ESTABLISHED  the sign or the confidence fails somewhere.
    NOT MEASURABLE   the estimator supports no cell at all at this n.
    """
    ok = cells[np.isfinite(cells["margin"])]
    if ok.empty:
        return NOMEAS
    if (ok["margin"] > 0).all() and (ok["P_boot"] >= P_GATE).all():
        return BINDS
    if (ok["margin"] < 0).all():
        return NOBIND
    return UNSET


def build_rows(csv: Path) -> tuple[list[dict], pd.DataFrame]:
    d = pd.read_csv(csv)
    d = d[d["set"] == "broad_477"]

    blocks = [("solvent class", "solvent_class"),
              ("solute role", "solute_role"),
              (None, "whole_set")]
    rows: list[dict] = []
    slot = 0
    for title, axis in blocks:
        sub = d[d["axis"] == axis]
        if title is not None:
            rows.append(dict(kind="header", label=title, y=slot))
            slot += 1
        head = sub[(sub["unit"] == UNIT) & (sub["convention"] == CONV)].copy()
        # map order: headline margin descending; strata the estimator cannot reach at all
        # fall to the bottom of their block, ordered by total error.
        head["_k1"] = np.where(np.isfinite(head["margin"]), 0, 1)
        head = head.sort_values(["_k1", "margin", "mse"], ascending=[True, False, False])
        for _, h in head.iterrows():
            cells = sub[sub["stratum"] == h["stratum"]]
            other = cells[~((cells["unit"] == UNIT) & (cells["convention"] == CONV))]
            rows.append(dict(
                kind="stratum", y=slot, stratum=h["stratum"], axis=axis,
                label=DISPLAY.get(h["stratum"], h["stratum"]),
                n=int(h["n"]), mse=float(h["mse"]),
                b=float(h["b_insuff_up"]), margin=float(h["margin"]),
                p=float(h["P_boot"]),
                ci=(float(h["margin_ci90_lo"]), float(h["margin_ci90_hi"])),
                se_share=float(h["share_of_squared_error"]),
                row_share=float(h["share_of_rows"]),
                top_src=float(h["top_source_share_of_stratum_squared_error"]),
                n_sources=int(h["n_sources"]),
                boundable=bool(h["boundable_at_headline_cell"]),
                verdict=verdict(cells),
                other_margins=[float(v) for v in other["margin"] if np.isfinite(v)],
                is_aggregate=(axis == "whole_set"),
            ))
            slot += 1
        slot += 1                                   # blank between blocks
    return rows, d


def spans(rows: list[dict]) -> dict:
    """The two ranges the header brackets carry: solvent classes with a bound, headline cell."""
    cls = [r for r in rows
           if r["kind"] == "stratum" and r["axis"] == "solvent_class"
           and np.isfinite(r["b"])]
    b = np.array([r["b"] for r in cls])
    m = np.array([r["mse"] for r in cls])
    return dict(b=(b.min(), b.max()), mse=(m.min(), m.max()),
                b_ratio=b.max() / b.min(), mse_ratio=m.max() / m.min(), k=len(cls))


# --------------------------------------------------------------------------- #
def _bracket(ax, x0, x1, y, label, color, fs):
    """A range bracket with end caps, labelled ABOVE it and anchored at its left cap.

    The B bracket is a sliver -- that is the point of it -- so a label centred on the span,
    or set outside either cap, would leave the axes on the left or collide with the MSE
    bracket on the right.  Both are therefore set the same way, above and left-anchored.
    """
    ax.plot([x0, x1], [y, y], lw=0.9, color=color, solid_capstyle="butt", zorder=4)
    for x in (x0, x1):
        ax.plot([x, x], [y - 0.19, y + 0.19], lw=0.9, color=color, zorder=4)
    ax.annotate(label, (x0, y), xytext=(-0.5, 3.5), textcoords="offset points",
                ha="left", va="bottom", fontsize=fs, color=color, zorder=4)


def _frac(ax, y: float) -> float:
    """Data y -> axes fraction, for an axis whose y limits are inverted."""
    lo, hi = ax.get_ylim()
    return (y - lo) / (hi - lo)


def draw(rows: list[dict], out_dir: Path, stem: str) -> list[str]:
    S = spans(rows)
    n_slot = max(r["y"] for r in rows) + 1
    head_h = 2.55                                    # header strip, in slot units
    fs_row, fs_tick, fs_title, fs_lab, fs_key = 7.2, 7.0, 8.2, 7.6, 6.9

    # Absolute inches below the rows (x label + the three keys) and above them (titles), so
    # the key does not creep into the plotting area when the number of strata changes.
    below, above = 0.94, 0.30
    H = 0.205 * (n_slot + head_h) + below + above
    fig = plt.figure(figsize=(7.1, H))
    gs = fig.add_gridspec(1, 3, width_ratios=[2.05, 2.05, 1.00], wspace=0.10,
                          left=0.185, right=0.985,
                          top=1 - above / H, bottom=below / H)
    axA, axB, axC = (fig.add_subplot(gs[0, i]) for i in range(3))

    for ax in (axA, axB, axC):
        ax.set_ylim(n_slot - 0.45, -head_h)
        ax.grid(False)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis="x", labelsize=fs_tick, length=2.5, pad=1.5)
        ax.set_yticks([])

    # ---------------- row labels and block separators ---------------------- #
    ticks, labels, colors = [], [], []
    for r in rows:
        if r["kind"] == "header":
            ticks.append(r["y"])
            labels.append(r["label"].upper())
            colors.append(GRAY)
            continue
        ticks.append(r["y"])
        labels.append(f"{r['label']}  ({r['n']})")
        colors.append(INK if r["verdict"] != NOMEAS else GRAY)
    axA.set_yticks(ticks)
    axA.set_yticklabels(labels, fontsize=fs_row)
    for t, c, r in zip(axA.get_yticklabels(), colors, rows):
        t.set_color(c)
        if r["kind"] == "header":
            t.set_fontsize(fs_row - 0.6)
            t.set_fontweight("bold")
    axA.tick_params(axis="y", length=0, pad=2.5)

    agg_y = [r["y"] for r in rows if r["kind"] == "stratum" and r["is_aggregate"]][0]
    strata = [r for r in rows if r["kind"] == "stratum"]
    for ax in (axA, axB, axC):
        ax.axhline(agg_y - 0.62, color=PALE, lw=0.8, zorder=1)
        for i, r in enumerate(strata):               # zebra, so a row tracks across panels
            if i % 2:
                ax.axhspan(r["y"] - 0.5, r["y"] + 0.5, color=INK, alpha=0.038, lw=0,
                           zorder=0)

    # ---------------- panel (a): the decomposition, per stratum ------------ #
    # The band is the span of the teal blocks over the solvent classes, drawn only across
    # the rows it is computed from, so it cannot be read as covering the solute-role rows.
    cls_y = [r["y"] for r in rows if r["kind"] == "stratum"
             and r["axis"] == "solvent_class" and np.isfinite(r["b"])]
    axA.axvspan(S["b"][0], S["b"][1], ymin=_frac(axA, max(cls_y) + 0.5),
                ymax=_frac(axA, min(cls_y) - 0.5), color=TEAL, alpha=0.11, lw=0, zorder=1)

    h = 0.52
    for r in rows:
        if r["kind"] != "stratum":
            continue
        y, mse, b = r["y"], r["mse"], r["b"]
        capped = mse > XMAX_A
        end = min(mse, XMAX_A)
        if not np.isfinite(b):
            axA.barh(y, end, height=h, color="white", edgecolor=GRAY, linewidth=0.7,
                     linestyle=(0, (2.2, 1.4)), zorder=3)
        else:
            axA.barh(y, min(b, end), height=h, color=TEAL, edgecolor="none", zorder=3)
            if b < mse:
                axA.barh(y, end - b, height=h, left=b, color=SALMON, edgecolor="none",
                         zorder=3)
            else:                                    # the bound covers the whole error
                axA.barh(y, b - mse, height=h, left=mse, color=TEAL, alpha=0.45,
                         edgecolor=TEAL, linewidth=0.6, hatch="////", zorder=3)
        if capped:                                   # the total is off the axis: say so
            axA.plot(XMAX_A * 1.004, y, marker=">", ms=4.2, color=INK, clip_on=False,
                     zorder=6)
            # the knockout patch takes the colour of the block it sits on, so the label
            # reads as inside the bar instead of punching a hole in it
            axA.annotate(f"{mse:.2f}", (XMAX_A * 0.985, y), ha="right", va="center",
                         fontsize=fs_key - 0.3, color=INK, zorder=7,
                         bbox=dict(facecolor=("white" if not np.isfinite(b) else SALMON),
                                   edgecolor="none", pad=0.7))
        else:
            axA.plot([mse] * 2, [y - h / 2 - 0.07, y + h / 2 + 0.07],
                     lw=1.1, color=INK, zorder=5)

    _bracket(axA, *S["b"], -0.95,
             f"$B^{{\\mathrm{{up}}}}_{{\\mathrm{{insuff}}}}$   $\\times{S['b_ratio']:.1f}$",
             TEAL, fs_key)
    _bracket(axA, *S["mse"], -2.05, f"MSE   $\\times{S['mse_ratio']:.0f}$", INK, fs_key)

    axA.set_xlim(0, XMAX_A)
    axA.set_xticks([0, 1, 2, 3, 4, 5])
    axA.set_xlabel("error  ($\\ln\\gamma$ units$^2$)", fontsize=fs_lab, labelpad=2)
    axA.set_title("(a)  input bound and total error", fontsize=fs_title, pad=4)

    # ---------------- panel (b): the margin, with its interval ------------- #
    axB.axvline(0.0, color=INK, lw=1.0, zorder=2)
    for r in rows:
        if r["kind"] != "stratum" or r["verdict"] == NOMEAS:
            continue
        y = r["y"]
        lo, hi = r["ci"]
        hi_cap = hi > XHI_B
        axB.plot([max(lo, XLO_B), min(hi, XHI_B)], [y, y], lw=1.0, color=INK, alpha=0.55,
                 zorder=3, solid_capstyle="butt")
        for x, on in ((lo, lo >= XLO_B), (hi, not hi_cap)):
            if on:
                axB.plot([x, x], [y - 0.17, y + 0.17], lw=1.0, color=INK, alpha=0.55,
                         zorder=3)
        if hi_cap:
            axB.plot(XHI_B * 0.998, y, marker=">", ms=3.6, color=INK, alpha=0.55,
                     zorder=3, clip_on=False)
        for v in r["other_margins"]:
            axB.plot(v, y, marker="|", ms=6.5, mew=1.0, color=GRAY, zorder=4)
        st = VERDICT_STYLE[r["verdict"]]
        axB.scatter(r["margin"], y, s=st["size"], marker=st["marker"],
                    facecolor=(st["color"] if r["boundable"] else "white"),
                    edgecolor=st["color"] if r["boundable"] else st["color"],
                    linewidth=1.0, zorder=6)

    axB.set_xlim(XLO_B, XHI_B)
    axB.set_xticks([0, 1, 2, 3, 4, 5, 6, 7])
    # The margin is MSE - 2 B^up (the manuscript's definition, Table 2 note b): B_closure
    # exceeds B_insuff exactly when MSE - B^up > B^up.  Panel (a)'s two blocks are B^up and
    # B_closure's lower bound MSE - B^up, which is NOT this quantity -- do not relabel either
    # one to match the other.
    axB.set_xlabel("margin  $=\\ \\mathrm{MSE}-2B^{\\mathrm{up}}_{\\mathrm{insuff}}$",
                   fontsize=fs_lab, labelpad=2)
    axB.set_title("(b)  margin on $B_{\\mathrm{closure}}$, 90% interval",
                  fontsize=fs_title, pad=4)

    # ---------------- panel (c): composition and its source concentration -- #
    hc = 0.44
    for r in rows:
        if r["kind"] != "stratum":
            continue
        y, se = r["y"], r["se_share"]
        axC.barh(y, se, height=hc, color=GRAY, alpha=0.45, edgecolor="none", zorder=3)
        axC.barh(y, se * r["top_src"], height=hc, color=INK, edgecolor="none", zorder=4)
        axC.plot([r["row_share"]] * 2, [y - hc / 2 - 0.15, y + hc / 2 + 0.15],
                 lw=1.3, color=HURT, zorder=5)

    axC.set_xlim(0, 1.03)
    axC.set_xticks([0, 0.5, 1.0])
    axC.set_xticklabels(["0", "0.5", "1"])
    axC.set_xlabel("share of the set", fontsize=fs_lab, labelpad=2)
    axC.set_title("(c)  composition", fontsize=fs_title, pad=4)

    # ---------------- keys, one under each panel it explains --------------- #
    kA = [Patch(facecolor=TEAL, label="$B^{\\mathrm{up}}_{\\mathrm{insuff}}$"),
          Patch(facecolor=SALMON,
                label="$B^{\\mathrm{lb}}_{\\mathrm{closure}}$"),
          Line2D([], [], color=INK, lw=1.1, label="MSE"),
          Patch(facecolor=TEAL, alpha=0.45, hatch="////", edgecolor=TEAL,
                label="bound past MSE"),
          # the dashed bar in (a) and the blank row in (b) are the same fact
          Patch(facecolor="white", edgecolor=GRAY, linewidth=0.7,
                linestyle=(0, (2.2, 1.4)), label="no bound at this $n$")]
    kB = [Line2D([], [], ls="", marker="o", ms=4.4, mfc=SALMON, mec=SALMON,
                 label="binds: all cells $+$, $P\\geq0.90$"),
          Line2D([], [], ls="", marker="s", ms=4.2, mfc=TEAL, mec=TEAL,
                 label="does not bind: all cells $-$"),
          Line2D([], [], ls="", marker="D", ms=3.8, mfc="white", mec=GRAY,
                 label="not established"),
          Line2D([], [], ls="", marker="o", ms=4.4, mfc="white", mec=SALMON,
                 label="hollow: $n<40$, not boundable"),
          Line2D([], [], ls="", marker="|", ms=6.0, mew=1.0, color=GRAY,
                 label="other unit $\\times$ convention cells")]
    kC = [Patch(facecolor=GRAY, alpha=0.45, label="share of squared error"),
          Patch(facecolor=INK, label="its largest source"),
          Line2D([], [], color=HURT, lw=1.3, label="share of rows")]

    for handles, x, ncol in ((kA, 0.145, 2), (kB, 0.555, 2), (kC, 0.885, 1)):
        lg = fig.legend(handles=handles, loc="upper center",
                        bbox_to_anchor=(x, (below - 0.42) / H),
                        ncol=ncol, fontsize=fs_key, frameon=False, handlelength=1.3,
                        handletextpad=0.45, columnspacing=0.9, labelspacing=0.35,
                        borderpad=0.0)
        for t in lg.get_texts():
            t.set_color(INK)

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("pdf", "png"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p)
        written.append(str(p))
    return fig, written


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", default="results/b_insuff/stratified_map_table.csv")
    ap.add_argument("--out-dir", default="paper/figs")
    ap.add_argument("--stem", default="fig_decomposition")
    ap.add_argument("--style", default=None)
    ap.add_argument("--proof-png", default=None,
                    help="also render a PNG at the size the figure prints at, 150 dpi")
    args = ap.parse_args()

    apply_style(args.style)
    rows, _ = build_rows(Path(args.table))
    fig, written = draw(rows, Path(args.out_dir), args.stem)

    S = spans(rows)
    print(f"{S['k']} solvent classes carry a bound at the headline cell "
          f"({UNIT}/{CONV}): B in [{S['b'][0]:.3f}, {S['b'][1]:.3f}] (x{S['b_ratio']:.1f}), "
          f"MSE in [{S['mse'][0]:.3f}, {S['mse'][1]:.3f}] (x{S['mse_ratio']:.1f})")
    for r in rows:
        if r["kind"] != "stratum":
            continue
        m = "--" if not np.isfinite(r["margin"]) else f"{r['margin']:+.3f}"
        print(f"  {r['label']:<24s} n={r['n']:>3d}  MSE={r['mse']:6.3f}  "
              f"margin={m:>7s}  {r['verdict']:<16s} "
              f"boundable={r['boundable']!s:<5s} sources={r['n_sources']}")
    for p in written:
        print("wrote", p)

    if args.proof_png:
        # 150 dpi at the width the figure is SET at in the manuscript, so what is checked
        # by eye is what the reader sees, not an enlargement.
        w_in = fig.get_size_inches()[0]
        fig.savefig(args.proof_png, dpi=150 * (6.5 / w_in))
        print("wrote", args.proof_png)
    plt.close(fig)


if __name__ == "__main__":
    main()
