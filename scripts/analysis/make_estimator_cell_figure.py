#!/usr/bin/env python3
"""fig_estimator_cell -- the VT-2005 separation margin over every estimator cell, so that the
manuscript's own headline number can be seen sitting inside the spread its analyst choices produce.

WHY THIS FIGURE EXISTS
----------------------
Sec. 2.5 fixes four analyst choices in advance and Sec. 3.5.2 reports a margin of +0.045 with 4 of
60 single-pair deletions failing.  The reason those rules exist is that the margin is NOT robust to
the choices: over the same 60 rows, the same estimator and the same deposit, the aggregate runs from
-0.53 to +0.66 -- it changes SIGN -- as the bin count, the within-bin variance convention and the
combinatorial convention move across cells that are each individually defensible.

That is the manuscript's central methodological claim, and it was carried by a table of three
hand-picked rows.  Drawn over the whole grid it can be read at a glance, and it shows something the
three rows did not: the headline cell is among the LEAST favourable of the admissible ones.  A
reader who suspects the cell was chosen to flatter the result can see that it was not.

WHAT IS DRAWN
-------------
  (a)  aggregate margin against bin count, one line per convention x variance cell.  The zero line
       is the separation threshold: below it Lemma 1 does not separate the two terms at all.  The
       headline cell is ringed and labelled.
  (b)  how many of the 60 single-pair deletions send the margin below zero, same four lines.

Everything is recomputed from paper/si_tables/vt2005_matched_set_60.csv by the functions in
check_vt2005_leverage_counts.py, so the figure and that gate cannot disagree.

Usage
-----
    MPLBACKEND=Agg python scripts/analysis/make_estimator_cell_figure.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_vt2005_leverage_counts import (  # noqa: E402
    HEADLINE_BINS,
    HEADLINE_COLUMN,
    HEADLINE_DDOF,
    leave_one_pair_out,
    margin,
)

SALMON = "#E8A98C"
TEAL = "#7FB5A6"
BLUE = "#8FB3DA"
GOLD = "#E6C87A"
INK = "#4D4D4D"
HURT = "#B5654A"
_STYLE = Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"

#: (column, ddof) -> (colour, marker, label).  "residual-only" and "full" are the two combinatorial
#: conventions; ML and unbiased are the two within-bin variance conventions.
CELLS = {
    ("g_res", 1): (SALMON, "o", "residual-only, unbiased"),
    ("g_res", 0): (TEAL, "s", "residual-only, ML"),
    ("g_full", 1): (BLUE, "^", "full, unbiased"),
    ("g_full", 0): (GOLD, "D", "full, ML"),
}
BINS = range(3, 13)


def compute(deposit: Path) -> pd.DataFrame:
    d = pd.read_csv(deposit)
    m = d["m"].to_numpy(float)
    rows = []
    for (col, ddof) in CELLS:
        g = d[col].to_numpy(float)
        for n_bins in BINS:
            rows.append({"col": col, "ddof": ddof, "bins": n_bins,
                         "margin": margin(g, m, n_bins, ddof),
                         "n_failing": leave_one_pair_out(g, m, n_bins, ddof)["n_failing"]})
    return pd.DataFrame(rows)


def draw(t: pd.DataFrame, out_dir: Path, stem: str) -> list[str]:
    if _STYLE.exists():
        plt.style.use(str(_STYLE))
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(6.6, 4.6), sharex=True,
                                 gridspec_kw={"height_ratios": [1.35, 1.0]})

    ax.axhspan(t["margin"].min() * 1.15, 0.0, color="#F0E4E0", zorder=0)
    ax.axhline(0.0, color=INK, lw=0.9, zorder=2)
    for (col, ddof), (c, mk, lab) in CELLS.items():
        s = t[(t.col == col) & (t.ddof == ddof)]
        ax.plot(s["bins"], s["margin"], marker=mk, ms=3.6, lw=1.35, color=c, label=lab, zorder=3)
        bx.plot(s["bins"], s["n_failing"], marker=mk, ms=3.6, lw=1.35, color=c, zorder=3)

    h = t[(t.col == HEADLINE_COLUMN) & (t.ddof == HEADLINE_DDOF) & (t.bins == HEADLINE_BINS)]
    hm, hf = float(h["margin"].iloc[0]), int(h["n_failing"].iloc[0])
    for axis, val in ((ax, hm), (bx, hf)):
        axis.plot([HEADLINE_BINS], [val], marker="o", ms=10, mfc="none", mec=HURT, mew=1.5, zorder=4)
    ax.annotate(f"the reported cell\n{hm:+.3f}", xy=(HEADLINE_BINS, hm),
                xytext=(HEADLINE_BINS + 0.55, hm - 0.30), fontsize=7.0, color=HURT,
                arrowprops=dict(arrowstyle="-", color=HURT, lw=0.8))
    bx.annotate(f"{hf} of 60", xy=(HEADLINE_BINS, hf), xytext=(HEADLINE_BINS + 0.5, hf + 7),
                fontsize=7.0, color=HURT, arrowprops=dict(arrowstyle="-", color=HURT, lw=0.8))

    ax.text(0.012, 0.06, "below this line the two terms do not separate at all",
            transform=ax.transAxes, fontsize=6.8, color=HURT, style="italic")
    ax.set_ylabel("separation margin,\n" r"MSE $-\ 2\,B_{\mathrm{insuff}}^{\mathrm{up}}$",
                  fontsize=8.0)
    bx.set_ylabel("single-pair deletions\nthat cross zero", fontsize=8.0)
    bx.set_xlabel("number of equal-count bins of $g(z^\\star)$", fontsize=8.4)
    bx.set_xticks(list(BINS))
    for axis in (ax, bx):
        axis.tick_params(labelsize=7.2)
        for side in ("top", "right"):
            axis.spines[side].set_visible(False)
    ax.legend(fontsize=6.9, frameon=False, ncol=2, loc="upper left")
    ax.set_title("One deposit, one estimator, four defensible conventions: the margin changes sign",
                 fontsize=8.6, color=INK, pad=6)
    fig.tight_layout(h_pad=0.6)

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("pdf", "png"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p)
        written.append(str(p))
    plt.close(fig)
    return written


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--deposit", type=Path, default=Path("paper/si_tables/vt2005_matched_set_60.csv"))
    a.add_argument("--out-dir", type=Path, default=Path("paper/figs"))
    a.add_argument("--stem", default="fig_estimator_cell")
    args = a.parse_args()

    t = compute(args.deposit)
    print(f"margin over {len(t)} cells: {t['margin'].min():+.4f} to {t['margin'].max():+.4f}; "
          f"negative in {(t['margin'] <= 0).sum()} of them")
    h = t[(t.col == HEADLINE_COLUMN) & (t.ddof == HEADLINE_DDOF) & (t.bins == HEADLINE_BINS)]
    print(f"reported cell: margin {float(h['margin'].iloc[0]):+.4f}, "
          f"{int(h['n_failing'].iloc[0])} of 60 deletions cross zero")
    pos = t[t["margin"] > 0]
    print(f"of the {len(pos)} cells with a positive margin, the reported one ranks "
          f"{int((pos['margin'] < float(h['margin'].iloc[0])).sum()) + 1} from the bottom")
    for p in draw(t, args.out_dir, args.stem):
        print("wrote", p)


if __name__ == "__main__":
    main()
