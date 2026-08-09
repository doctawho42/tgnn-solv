#!/usr/bin/env python3
"""fig_parity_lnx2 -- solubility parity, predicted against measured ln x2.

WHY THIS FILE EXISTS
--------------------
The submission had no ln x2 parity plot anywhere.  `paper/figs/fig_parity.pdf` is a
DIFFERENT figure -- activity-coefficient parity, ln gamma^inf, on the n=60 VT-2005-matched
pairs -- and it lives in the Supporting Information.  This one is the solubility target
itself, on the scaffold-split test rows, which is the plot a reader of a solubility paper
opens the paper to find.  Do not merge the two stems; a rerun of either must not overwrite
the other.

WHAT IT DRAWS
-------------
Four panels, one per arm, all on the SAME rows and the SAME square axes:

  (a) DirectGNN            the physics-free control -- the accuracy yardstick
  (b) ungrounded sigma     COSMO-SAC over an unsupervised sigma-profile
  (c) grounded sigma       the same closure with sigma-profile supervision (training-time)
  (d) ref. sigma (eval)    the same trained model with the reference VT-2005 sigma-profile
                           substituted at evaluation

(b) -> (c) is the paper's training-time sense of grounding; (c) -> (d) is its
evaluation-time sense.  (a) is what both are measured against.

ONE COLOUR PER ARM, AND WHICH FIGURE IT WAS TAKEN FROM
------------------------------------------------------
This figure is read by comparing panels, so no two arms may share a colour -- (a) and (c)
were both TEAL until 2026-08-10, which drew the paper's control-versus-closure comparison
in one hue.  The other figures of the two documents colour by ROLE, not by arm, and the
role palette deliberately collides these two:

  Fig. 1  overview       SALMON = fixed closure / external reference input; TEAL = learned rep.
  Fig. 2  paradox bars   GRAY NRTL | TEAL DirectGNN | BLUE ungrounded | TEAL grounded |
                         SALMON ref. sigma        <- TEAL is two different arms
  Fig. S1 architecture   GRAY DirectGNN | SALMON sigma-oracle
  Fig. S3 gamma parity   SALMON = reference-sigma closure
  Fig. S6 data-efficiency SALMON = physics-grounded arm | TEAL = DirectGNN

So no per-arm assignment can agree with Fig. 2 on both (a) and (c), and exactly one of them
has to move.  The one that moves is the one the two documents ALREADY disagree about: the
grounded arm is TEAL in Fig. 2 and SALMON in Fig. S6.  DirectGNN is TEAL in both Fig. 2 and
Fig. S6, and the reference-input arm is SALMON in Figs. 1, 2, S1 and S3, so those two keep
their colours and the grounded arm takes the house palette's fourth member, PURPLE.
GRAY is not available for (a): Fig. 2 spends it on NRTL, two pages earlier, on the same rows.
Figs. 2 and S6 were left alone (other agents hold that prose, and neither is this figure's
to recolour); the disagreement they carry is theirs, not one introduced here.

AXES ARE SET TO THE MEASUREMENT, NOT TO THE WORST PREDICTION
------------------------------------------------------------
Until 2026-08-10 the range was the union of measured AND predicted values over all four
arms, which is [-23.2, +0.9] -- and the only thing that reached -23 was 69 predictions of
one arm, so about 45% of every panel was blank paper and the identity ran through emptiness
for a third of its length.  The range is now the measured range (the axis the reader
calibrates against) plus a 4% margin; predictions falling outside it are drawn as capped
markers at the frame, at their own measured x, and counted in the panel.  Only (d) has any.

ROWS AND NUMBERS
----------------
The row set is the cross-arm intersection lock -- rows supervised and finite in EVERY one
of the six arms -- and it is computed by importing `intersection_keys` from
run_e5_comparison, the same function that produced results/e5_sigma_grounding/seed_*/
comparison.json.  MAE and R2 on each panel come from `_metrics_on_keys` in that same
module.  So the panel headers cannot drift from Fig. paradox / tab:si-arms: they are the
same estimator on the same rows, not a re-implementation.

ONE SEED, AND WHY.  The panels are seed 42.  Three-seed means are what the bar figure and
the SI table report, but they cannot be drawn here: results/e5_sigma_grounding/seed_44/
oracle_predictions.csv is a 295-row partial deposit (its own summary.json records the
8103-row, n_supervised=5608 run that comparison.json used), so seed 44's reference-sigma
arm has no per-row file to plot.  Drawing seeds 42+43 for one arm and 42+43+44 for the
others would put a different number of points in different panels of the same figure.
Seed 42 is deposited complete for all six arms plus both co-adaptation controls, and its
per-seed MAE for every arm is already printed in tab:si-arms.  `--seed` overrides.

THE SEED IS PRINTED IN THE FIGURE, not reconciled in the caption.  The panel headers are one
seed and the bars of Fig. paradox are three, and the caption used to spend three sentences
saying so.  The drawing states which seed it is; the difference from the three-seed means is
then a fact the reader can look up in tab:si-arms, not an argument the caption has to make.

USAGE
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/make_parity_figure.py \
        --e5-dir results/e5_sigma_grounding --seed 42 --out-dir paper/figs

    ... --dump-json paper/figs/fig_parity_lnx2.numbers.json   # every number the figure prints
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_e5_comparison import (  # noqa: E402
    _KEY,
    _metrics_on_keys,
    _round_key,
    intersection_keys,
)

# Palette shared with make_paradox_figures.py -- see its module docstring, and the
# "ONE COLOUR PER ARM" section above for which figure each assignment was taken from.
SALMON = "#E8A98C"   # (d) reference-input arm      -- as Figs. 1, 2, S1, S3
TEAL = "#7FB5A6"     # (a) DirectGNN, the control   -- as Figs. 2, S6
BLUE = "#8FB3DA"     # (b) ungrounded sigma         -- as Fig. 2
PURPLE = "#B7A5DC"   # (c) grounded sigma           -- the arm Figs. 2 and S6 disagree about
GRAY = "#9AA0A6"     # not an arm colour here: Fig. 2 spends GRAY on NRTL
INK = "#4D4D4D"

_DEFAULT_STYLE = Path.home() / ".claude/skills/repo-to-paper/assets/softpastel.mplstyle"

# The six arms whose intersection defines the lock.  All six are needed to reproduce
# n=5608 even though only four are drawn -- dropping the two undrawn arms would enlarge
# the row set and the panel headers would stop matching comparison.json.
LOCK_ARMS = ["nrtl", "directgnn", "ungrounded", "grounded_a", "grounded_b", "oracle"]

# (arm key, panel label, colour).  Order is the control first, then the grounding
# sequence the paper reads left to right.
PANELS = [
    ("directgnn", "DirectGNN", TEAL),
    ("ungrounded", "ungrounded $\\sigma$", BLUE),
    ("grounded_a", "grounded $\\sigma$", PURPLE),
    ("oracle", "ref. $\\sigma$ (eval)", SALMON),
]
LETTERS = "abcd"


def apply_style(style: str | None) -> None:
    path = Path(style) if style else _DEFAULT_STYLE
    if path.exists():
        plt.style.use(str(path))
        return
    plt.rcParams.update({
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "savefig.dpi": 300, "savefig.bbox": "tight", "figure.dpi": 200,
        "font.family": "sans-serif", "font.size": 11,
        "axes.edgecolor": INK, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True, "grid.color": "#D9D9D9",
        "grid.linewidth": 0.6, "grid.alpha": 0.7, "legend.frameon": False,
        "patch.linewidth": 0.0,
        "axes.prop_cycle": plt.cycler(color=[TEAL, SALMON, BLUE, PURPLE, GRAY]),
    })


def load_locked(e5_dir: Path, seed: int) -> tuple[list, dict, dict]:
    """(locked keys, per-arm (true,pred) arrays, per-arm metrics) for one seed."""
    d = e5_dir / f"seed_{seed}"
    frames = {a: pd.read_csv(d / f"{a}_predictions.csv") for a in LOCK_ARMS}
    for a, f in frames.items():
        n_sup = int(f["has_solubility"].astype(bool).sum()) if "has_solubility" in f else -1
        if n_sup < 1000:
            raise SystemExit(
                f"seed {seed} arm '{a}': only {n_sup} supervised rows in "
                f"{d / f'{a}_predictions.csv'} ({len(f)} rows total). That file is a partial "
                "deposit; the cross-arm lock computed from it would not be the paper's "
                "n=5608. Use a seed whose per-row deposit is complete, or restore the file."
            )
    keys = intersection_keys(frames)
    series, metrics = {}, {}
    for a, f in frames.items():
        sub = _round_key(f).drop_duplicates(_KEY, keep="first").set_index(_KEY).loc[keys]
        series[a] = (sub["ln_x2_true"].to_numpy(float), sub["ln_x2_pred"].to_numpy(float))
        metrics[a] = _metrics_on_keys(f, keys)
    return keys, series, metrics


def binned_median(x: np.ndarray, y: np.ndarray, n_bins: int = 12):
    """Median prediction in equal-COUNT bins of the measurement.

    Equal-count, not equal-width: the measurements are far denser near ln x2 = -5 than in
    the sparingly-soluble tail, and equal-width bins would put two or three points in the
    leftmost bin and draw a trace whose left end is noise.
    """
    edges = np.quantile(x, np.linspace(0.0, 1.0, n_bins + 1))
    xs, ys = [], []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (x >= lo) & (x <= hi) if i == n_bins - 1 else (x >= lo) & (x < hi)
        if m.sum() >= 20:
            xs.append(float(np.median(x[m])))
            ys.append(float(np.median(y[m])))
    return np.asarray(xs), np.asarray(ys)


def make_figure(series: dict, metrics: dict, out_dir: Path, stem: str,
                seed: int) -> tuple[list, dict]:
    drawn = [p for p in PANELS if p[0] in series]
    # Square panels on ONE shared range, so the 1:1 line is at 45 degrees in every panel
    # and the four panels are directly comparable by eye.
    #
    # THE RANGE IS THE MEASUREMENT'S, with a 4% margin.  Measured ln x2 runs -17.71 to
    # -0.06 on these rows, and three of the four arms predict entirely inside that; the
    # fourth sends 69 of its 5608 predictions (1.2%) as low as -22.3.  Taking the union
    # instead -- what this figure did until 2026-08-10 -- widened both axes by a quarter to
    # accommodate those 69 marks and left the rest of the panel, and a third of the identity
    # line, on blank paper.  Off-range predictions are drawn at the frame instead (below).
    tvals = series[drawn[0][0]][0]
    lo, hi = float(tvals.min()), float(tvals.max())
    pad = 0.04 * (hi - lo)
    lo, hi = lo - pad, hi + pad

    # TYPE SIZES ARE SET BY THE SUBSCRIPT, NOT BY THE BASE.  mathtext sets a subscript at
    # 0.7x its base, so the "2" of $\ln x_2$ and of $R^2$ is the smallest body type in the
    # figure.  The 6 pt floor applies to it: at the 1.039x this canvas is enlarged by when
    # set at \textwidth, a base below 8.3 pt puts that "2" under 6 pt on the page.  This is
    # the same trap fig_paradox documents at its ylabel.  Do not shrink BASE_MATH to buy
    # room; take the room out of the panel count or the label wording instead.
    BASE_MATH = 8.4   # anything containing a sub/superscript
    BASE_TICK = 7.4   # tick labels: no mathtext, so the floor applies to the base itself
    # Canvas = the width the figure is SET at (\textwidth = 504.47 pt = 6.98 in) before
    # the tight bbox crops it, so it prints at ~1:1 or slightly enlarged, never reduced.
    fig, axes = plt.subplots(1, len(drawn), figsize=(6.98, 2.62))
    axes = np.atleast_1d(axes)
    printed = {}
    for k, ((arm, label, colour), ax) in enumerate(zip(drawn, axes)):
        t, p = series[arm]
        m = metrics[arm]
        # rasterized: 5608 vector points x 4 panels is a multi-MB PDF that ACS production
        # renders slowly; the marks are a density field, not artwork.
        ax.scatter(t, p, s=2.0, color=colour, alpha=0.14, linewidths=0.0, zorder=2,
                   rasterized=True)
        # The identity now runs THROUGH the cloud for its whole length rather than beside
        # it, so it needs the same white-under-dark casing the median trace gets or the
        # dense core swallows it.  Both strokes carry the SAME dash spec, so the white
        # reads as a halo on each dash and not as a continuous stripe under a dashed line.
        _DASH = (0, (4.2, 2.8))
        for lw, col, z in ((2.5, "white", 3.1), (1.0, INK, 3.3)):
            ax.plot([lo, hi], [lo, hi], ls=_DASH, lw=lw, color=col, zorder=z,
                    solid_capstyle="butt")
        # The conditional trace is drawn white-under-dark so it stays legible where it
        # crosses the densest part of its own scatter.
        bx, by = binned_median(t, p)
        ax.plot(bx, by, color="white", lw=2.5, zorder=3.6, solid_capstyle="round")
        ax.plot(bx, by, color=INK, lw=1.2, zorder=3.8, solid_capstyle="round")
        # Predictions below the frame are SHOWN, not dropped: one open triangle per row at
        # its own measured x, pinned just inside the bottom spine, plus the count.  Any arm
        # can have them; on these rows only (d) does, and where they sit on the measurement
        # axis is the thing the old full-union range was spending half a panel to say.
        under = p < lo
        n_under = int(under.sum())
        if n_under:
            # Filled and translucent, not open: 69 outline triangles inside 10 ln units
            # overlap into a fence of trapezoids (the frame clips each tip) and read as one
            # solid bar. Filled at low alpha they stack into a density strip, which is the
            # honest reading -- a pile-up, whose position along the MEASUREMENT axis is the
            # part that carries information.  Seated a full marker-height above the spine.
            ax.scatter(t[under], np.full(n_under, lo + 0.045 * (hi - lo)), s=7.0,
                       marker="v", color=colour, alpha=0.40, linewidths=0.0,
                       clip_on=True, zorder=4.0)
            ax.text(0.5, 0.085, f"{n_under} below axis", transform=ax.transAxes,
                    ha="center", va="bottom", fontsize=6.6, color=INK)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xticks([-15, -10, -5, 0])
        ax.set_yticks([-15, -10, -5, 0])
        ax.set_xticks([-17.5, -12.5, -7.5, -2.5], minor=True)
        ax.set_yticks([-17.5, -12.5, -7.5, -2.5], minor=True)
        ax.tick_params(labelsize=BASE_TICK, length=2.4, pad=1.8)
        ax.tick_params(which="minor", length=1.4)
        ax.set_xlabel("measured $\\ln x_2$", fontsize=BASE_MATH, labelpad=2.0)
        if k == 0:
            ax.set_ylabel("predicted $\\ln x_2$", fontsize=BASE_MATH, labelpad=2.0)
        else:
            ax.set_yticklabels([])
        # THREE decimals, not two, and it is not a precision claim.  tab:si-arms prints the
        # per-seed MAE of every one of these arms to three decimals; at two the panel would
        # print 1.75 where the table prints 1.749 and 2.23 where it prints 2.232 -- four
        # values that exist nowhere else in the submission, sitting next to a three-seed
        # mean of 1.70 for the same arm.  At three decimals every MAE here is literally a
        # number the table already carries, and the three-decimal R2 reads as per-seed
        # rather than as a restatement of the +/- means in Fig. paradox.
        r2v = m["r2"]
        r2s = f"{r2v:+.3f}".replace("-", "−")   # U+2212, not a hyphen
        ax.set_title(f"({LETTERS[k]}) {label}\nMAE {m['mae']:.3f}   $R^2$ {r2s}",
                     fontsize=BASE_MATH, linespacing=1.40, pad=3.5)
        # The SHRINKAGE statistic.  The panel headers carry MAE and R^2; neither says how far
        # the cloud is tilted off the identity, which is the thing the eye actually reads off
        # a parity plot and the thing the article quotes.  It is the ordinary least-squares
        # slope of predicted on measured -- 1 would be an unshrunk predictor, and every arm
        # here is well below it.  Dumped, not drawn: a fitted line in the panel would compete
        # with the identity and the binned median for the same ink.
        slope = float(np.polyfit(t, p, 1)[0])
        printed[arm] = {"label": label, "mae": m["mae"], "r2": r2v, "n": m["n"],
                        "mae_printed": f"{m['mae']:.3f}", "r2_printed": f"{r2v:+.3f}",
                        "ols_slope_pred_on_meas": slope, "n_below_axis": n_under}
    # w_pad buys the horizontal gap that keeps one panel's "0" tick label clear of the
    # next panel's leftmost label; the two sit at the shared boundary and collide at the
    # default.
    fig.tight_layout(w_pad=1.9)
    # WHICH SEED, said by the drawing.  The panels are one seed and the bars of
    # Fig. paradox are three; three caption sentences used to reconcile the two.  A label
    # is the cheaper fix, and it is a description of what is shown.
    #
    # Anchored to panel (a)'s axes, not to the FIGURE.  The panels carry an equal aspect
    # with adjustable="box", so after tight_layout they shrink inside their allocation and
    # leave a band of slack below the x-labels that savefig's tight bbox would otherwise
    # crop away; a fig.text at y=0.01 pins that band open and prints the note a third of an
    # inch adrift of the plot.  In axes fractions it sits on the x-label's own baseline,
    # left of it (the label spans about 0.19..0.81, so this clears it) and under the
    # y-label, which is the conventional figure-note corner.
    axes[0].text(-0.30, -0.235, f"seed {seed}", transform=axes[0].transAxes,
                 ha="left", va="top", fontsize=6.8, color=GRAY)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("pdf", "png"):
        q = out_dir / f"{stem}.{ext}"
        fig.savefig(q, dpi=300 if ext == "pdf" else 150)
        written.append(str(q))
    plt.close(fig)
    return written, {"axis_range": [lo, hi], "panels": printed}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--e5-dir", default="results/e5_sigma_grounding", type=Path)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default="paper/figs", type=Path)
    ap.add_argument("--stem", default="fig_parity_lnx2")
    ap.add_argument("--style", default=None)
    ap.add_argument("--dump-json", default=None, type=Path)
    args = ap.parse_args()

    apply_style(args.style)
    keys, series, metrics = load_locked(args.e5_dir, args.seed)
    written, printed = make_figure(series, metrics, args.out_dir, args.stem, args.seed)
    printed["seed"] = args.seed
    printed["n_locked"] = len(keys)
    print(f"n_locked = {len(keys)} (seed {args.seed})")
    for arm, rec in printed["panels"].items():
        print(f"  {arm:12s} MAE {rec['mae']:.4f} -> printed {rec['mae_printed']}   "
              f"R2 {rec['r2']:+.4f} -> printed {rec['r2_printed']}   n {rec['n']}   "
              f"below axis {rec['n_below_axis']}")
    print("axis range", [round(v, 2) for v in printed["axis_range"]])
    for w in written:
        print("wrote", w)
    if args.dump_json:
        args.dump_json.write_text(json.dumps(printed, indent=2))
        print("wrote", args.dump_json)


if __name__ == "__main__":
    main()
