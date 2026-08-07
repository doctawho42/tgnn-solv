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
      insufficient-input parts in the deployed residual-only convention, drawn PER SOLVENT
      CLASS, under a strip that draws the WHOLE search the three are taken from. Bounds,
      never a point split: the conditional variance is unestimable, so B_insuff is only ever
      an upper bound and B_closure only lower-bounded.

2026-08-07 THE STRIP, and why three bars alone were a misdrawing. Two referees, independently:
three solvent classes summing to 350 rows are drawn out of the fifty-nine strata the search
covers, and a reader with only the bars in front of them reads the map as three classes wide.
The panel is the paper's one overview display of the finding's SHAPE, and the shape is that most
of the map supports no statement at all -- which is what the abstract says ("most strata
unboundable") and what the bars, alone, deny. The strip draws all fifty-nine: pale where no
bound exists (forty-four), filled where one does (fifteen), and the one row set the
admissibility rule leaves standing carried out to full height under its own mark. The bars are
then labelled for what they are, the three of those fifteen that are solvent classes. Do not
delete the strip to buy space for the bars: without it the three bars are a claim about the
map's width, and the claim is false.

2026-07-28 declutter. Panel (b) used to carry a three-line statistical sentence (separation
margin, the pair-clustered and two-way bootstrap intervals, the n=60 comparison) and two grey
footnote lines. Prose set inside axes is unreadable at the printed column width, so all of it
moved OUT of the figure and into the caption; nothing was weakened and nothing was dropped.

2026-08-07 THE TWO PANELS NAME THEIR DATABASES, and the names are the point. Panel (a) said
"external reference profile" and panel (b) "error when the reference profile is used", so the
figure asserted that one table runs through both measurements. It does not: the evaluation-time
substitution is the VT-2005 database, while the decomposition and its glycol-ether margin are
computed on the UD profiles the broad IDAC set is matched to -- which is also why Sec. 3.5.3's
database-to-database bracket exists at all. Two referees read the abstract's matching "the same
reference" as an error rather than a looseness; the abstract now says "another such database"
and these labels carry the same correction. What the two axes share is that a tabulated
reference for the intermediate exists on each, not that it is the same table. Do not drop
"(VT-2005)" or "UD" to buy width, and do not let one panel name its database while the other
does not.

2026-08-02 restratification -- WHY THIS PANEL IS NO LONGER ONE BAR. It drew the whole set's
split as a single bar cut at B_insuff^up, with the threshold MSE/2 at its midpoint, so the
reader saw the input block end left of centre and read the aggregate ordering off the shape.
That aggregate is retired: it does not survive the chemistry cut and the pair unit applied
together (+0.51 -> -0.38), and it is carried by one publication (leave-one-source-out takes
it to +0.18 while the other fourteen deletions leave it in [+0.42, +0.87]). The reason is
structural and is what the panel now draws: B_insuff^up is nearly stratum-independent -- every
stratum is binned the same way, into eight equal-count bins of one scalar -- while MSE varies
across strata by a factor of 25, so a single bar is a composition-weighted average of a
quantity that moves against one that does not. The three classes drawn are exactly the three
the design can bound at this cell (n >= 40); their values come from
results/b_insuff/stratified_map_table.csv (set=broad_477, axis=solvent_class, unit=row,
convention=res) and are the same cells the map figure and Table 2 carry. Do not put the
aggregate bar back, and do not add a fourth class without checking that it clears n = 40.

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
axa.text(0.50, 0.325, "external reference\nprofile (VT-2005)", ha="right", va="center",
         fontsize=8.2, color=INK)
arrow(axa, (0.585, 0.40), (0.585, 0.545), color=HURT, lw=1.8)
axa.text(0.66, 0.325, "substituting it makes\nthe prediction worse", ha="left", va="center",
         fontsize=8.8, color=HURT)
axa.text(0.06, 0.10, "Either the fixed model is wrong, or the learned profile\n"
                     "carries information the reference does not.",
         ha="left", va="center", fontsize=8.6, color=GRAY)

# ---------------- (b) the split, per solvent class ----------------
# Row unit, deployed residual-only convention, one estimator cell for all three (LOTV, eight
# equal-count bins, UNBIASED within-bin variance).  The three classes that clear n = 40 on the
# broad IDAC set, in the map's own order (headline margin descending):
#   name                      n     B_insuff^up   MSE     verdict
#   glycol ethers            182       0.108     2.252    established
#   water                    111       0.215     0.477    not admissible -- the sign flips under two
#                                                         of its three leave-one-source-out deletions
#   acceptor-only aprotics    57       0.140     0.089    admissible, not established -- the bound
#                                                         exceeds the total error, and a non-positive
#                                                         margin is failure to separate, not a
#                                                         certified reversal
#
# 2026-08-02.  THE MARKS ARE NOT DECORATION.  Only the first of the three clears the admissibility
# rule of Sec. 4.2(i) (boundable AND sign-stable under deletion of every contributing publication,
# in all four unit x convention cells), and a front-matter panel that draws three positive-looking
# bars with no mark says three things the Results forbid.  The marks and their gloss stay
# until the rule changes; do not drop them to buy space, and do not add a class without checking
# both n >= 40 and its admissibility column in results/b_insuff/admissibility_table.csv.
#
# THE TWO MARKS ARE DIFFERENT REASONS AND ONE MARK CANNOT CARRY BOTH.  Until this revision both
# unestablished classes wore a dagger glossed "the ordering here does not survive removing one
# contributing laboratory", which is true of water and FALSE of the acceptor-only aprotics: that
# cell is admissible in all four cells and survives every one of its four deletions.  It is not
# established because its margin is not positive and the instrument is one-sided.  Keep the marks
# distinct.
#
# 2026-08-07 THE STANDING CLASS NOW CARRIES A MARK OF ITS OWN, and the caption no longer says
# "unmarked".  A referee: with the other two marked, an unmarked block reads as a CATEGORY, and a
# reader cannot tell whether it means "passed the rule" or "not yet put to it" -- absence of a
# disqualification is not a mark.  The asterisk is that mark, and it is glossed by the rule it
# clears (bounded, sign-stable under deletion, margin positive) rather than by the absence of the
# other two reasons.  Three marks, three glosses; do not go back to two.
CLASSES = [("glycol ethers", 0.1077, 2.2518, " $\\ast$"),
           ("water", 0.2150, 0.4765, " $\\dagger$"),
           ("aprotic acceptors", 0.1404, 0.0891, " $\\ddagger$")]
LX, BX0, BX1 = 0.365, 0.380, 0.965      # label right edge; bar span
SCALE = 2.45                             # ln-gamma units^2 across (BX1 - BX0)
BH = 0.078


def _x(v):
    return BX0 + (BX1 - BX0) * v / SCALE


axb.text(0.045, 0.808, "error on the UD reference profiles ($n{=}477$)",
         ha="left", va="center", fontsize=7.6, color=GRAY)

# ---- the whole search, one tick per stratum ----------------------------------------------
# results/b_insuff/stratified_map_table.csv, set=broad_477, unit=row, convention=res: 59 strata
# over seven axes (whole set, solute family, solvent family, solvent class, coarse class, solute
# role, class x role), of which boundable_at_headline_cell holds on 15.  Six of those are
# admissible in every unit x convention cell; clause (c) of Sec. 4.2 collapses the six to three
# distinct ROW SETS, and one of the three is also positive and undemoted -- the glycol ethers.
# Those are the counts Table 3's note (h) prints, and the two must move together.
# The ticks are SORTED by status, not by name: the strata carry no natural order, and sorting is
# what lets the eye read 44-against-15 off the strip.  The standing one is drawn last, taller,
# in ink, under the same asterisk the bar below it wears.
N_STRATA, N_BOUNDABLE = 59, 15
SX0, SX1, SY, SH = 0.045, 0.965, 0.712, 0.038
_pitch = (SX1 - SX0) / N_STRATA
for i in range(N_STRATA):
    stands = i == N_STRATA - 1
    boundable = i >= N_STRATA - N_BOUNDABLE
    axb.add_patch(FancyBboxPatch((SX0 + i * _pitch, SY), _pitch * 0.68,
                                 SH * (1.5 if stands else 1.0),
                                 boxstyle="square,pad=0", lw=0, zorder=3,
                                 fc=INK if stands else ("#9AA0A6" if boundable else "#DFD9D3")))
axb.text(SX0 + (N_STRATA - 0.66) * _pitch, SY + SH * 1.5 - 0.008, "$\\ast$",
         ha="center", va="bottom", fontsize=6.5, color=INK)
axb.text(0.045, 0.678, "fifty-nine strata; fifteen boundable (filled), one stands ($\\ast$)",
         ha="left", va="center", fontsize=6.5, color=GRAY)
axb.text(0.045, 0.616, "the three boundable solvent classes", ha="left", va="center",
         fontsize=7.4, color=INK)

for k, (name, b, mse, mark) in enumerate(CLASSES):
    yk = 0.495 - k * 0.098
    axb.text(LX, yk + BH / 2, name + mark,
             ha="right", va="center", fontsize=8.0,
             color=INK if "ast" in mark else GRAY)
    if mse > b:                          # the ordinary case: two contiguous blocks
        axb.add_patch(FancyBboxPatch((_x(0), yk), _x(b) - _x(0), BH,
                                     boxstyle="square,pad=0", fc="#DDE7E3", ec=INK,
                                     lw=0.8, zorder=3))
        axb.add_patch(FancyBboxPatch((_x(b), yk), _x(mse) - _x(b), BH,
                                     boxstyle="square,pad=0", fc=SALMON, ec=INK,
                                     lw=0.8, zorder=3))
    else:                                # the bound runs past the total error: no model block
        axb.add_patch(FancyBboxPatch((_x(0), yk), _x(b) - _x(0), BH,
                                     boxstyle="square,pad=0", fc="#DDE7E3", ec=INK,
                                     lw=0.8, ls=(0, (2.0, 1.3)), zorder=3))
        axb.plot([_x(mse)] * 2, [yk, yk + BH], lw=1.1, color=INK, zorder=5)
# The teal blocks line up because every stratum is binned the same way; the salmon ones do not.
# That contrast IS the panel, so it is drawn and not asserted -- no threshold line, no numbers.
KY, KH, KW = 0.232, 0.046, 0.036         # legend swatch row: y, height, width
axb.add_patch(FancyBboxPatch((0.085, KY), KW, KH, boxstyle="square,pad=0",
                             fc="#DDE7E3", ec=INK, lw=0.7, zorder=3))
axb.text(0.085 + KW + 0.020, KY + KH / 2, "the inputs, at most", ha="left", va="center",
         fontsize=7.4, color="#5F6B66")
axb.add_patch(FancyBboxPatch((0.545, KY), KW, KH, boxstyle="square,pad=0",
                             fc=SALMON, ec=INK, lw=0.7, zorder=3))
axb.text(0.545 + KW + 0.020, KY + KH / 2, "the model, at least", ha="left", va="center",
         fontsize=7.4, color=INK)
# 25-fold is the MSE ratio across exactly these three classes (0.0891 -> 2.2518 = 25.3), not
# across all nine: the sentence must describe the rows the panel actually draws.
axb.text(0.045, 0.190, "The input bound hardly moves; the error moves 25-fold.",
         ha="left", va="center", fontsize=8.0, color=HURT)
# One line per mark, and each line names the rule its class meets or fails.  The asterisk's gloss
# is the admissibility rule itself, so "stands" cannot be read as "not yet tested".
axb.text(0.045, 0.150, "$\\ast$ stands: bounded, sign-stable under deletion, margin positive.\n"
                       "$\\dagger$ measured, not established: dropping a laboratory flips the sign.\n"
                       "$\\ddagger$ measured, not established: margin not positive, bound one-sided.",
         ha="left", va="top", multialignment="left", fontsize=6.3, color=GRAY,
         linespacing=1.14)

fig.suptitle("When do reference physical inputs help a learned solubility model?",
             fontsize=12.5, color=INK, y=0.985)
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT}.{ext}")
print(f"wrote {OUT}.pdf / .png")
