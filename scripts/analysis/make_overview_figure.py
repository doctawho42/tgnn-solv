#!/usr/bin/env python3
"""Figure 1: a schematic entry point to the paper, in two panels.

Deliberately carries no evidence grading. An opening figure should let a reader who does not
yet know the topic see what is being done and what went wrong with it; the grading of claims
by strength of evidence belongs to the Discussion.

  (a) the pipeline and the substitution -- a learned encoder produces a charge-density profile
      that a fixed thermodynamic model turns into a solubility, and an external reference
      profile can be put in its place at prediction time.  A MECHANISM, NOT AN OUTCOME: see
      the 2026-08-10 note.
  (b) where the error sits -- one-sided bounds on the misspecified-model and
      insufficient-input parts in the deployed residual-only convention, drawn PER SOLVENT
      CLASS, under a strip that draws the WHOLE search the three are taken from. Bounds,
      never a point split: the conditional variance is unestimable, so B_insuff is only ever
      an upper bound and B_closure only lower-bounded.

2026-08-10 PANEL (a) DRAWS THE MECHANISM AND STOPS THERE, and every drawn term is now defined
where it prints.  Panel (a) had never been revised -- it was carried through the 2026-08-09
rebuild by an explicit "(a) is unchanged" clause -- and it was the half breaking the two rules
the display pass is run against.  Four things went, and one thing arrived:

  * THE INFERENCE WENT.  "Either the fixed model is wrong, or the learned profile carries
    information the reference does not" is the paper's disjunction, and it was printed on
    page 4, in a schematic, before either alternative exists for the reader.  A schematic may
    say what is drawn; it may not pre-announce the reading.  Seventeen drawn words.
  * THE RESULT WENT.  "substituting it makes the prediction worse" is a finding -- it is the
    first clause of the paper's title -- set inside a figure whose brief is to show what is
    done, not what came of it.  Replaced by the mechanism the arrow actually draws,
    "substituted at prediction time", which is the Introduction's own phrase ("at the moment
    of prediction").  The arrow is recoloured from HURT to SALMON_D for the same reason: HURT
    is the palette's harm colour, so it was an outcome asserted in ink.  SALMON_D ties the
    arrow to the salmon sigma-star it carries, i.e. the colour now names the object.
  * THE TITLE WENT WITH THEM.  "The pipeline, and the paradox" names a paradox that page 4 has
    not shown; "The pipeline, and the substitution" names the two things drawn.
  * THREE UNDEFINED TERMS WENT.  "UD", "boundable" and "aprotic acceptors" printed on page 4
    and were first defined on pages 7, 7 and nowhere -- against this file's own instruction,
    four lines below the caption budget: "every term in it must be defined by then: keep it in
    plain English".  UD is now glossed where it prints ("Delaware (UD)"); "boundable" is now
    "with a bound", which also makes the strip's two labels a matched pair against "with no
    bound"; and "aprotic acceptors" carries its defining condition, "(no O-H or N-H)" -- the
    class rule at run_b_insuff_stratified_map.py:52 -- so the stratum keeps the name Table 2
    and Fig. 6 give it while a reader on page 4 can still tell what it is.  Do not strip these
    glosses: the class name is a term of art and "UD" is an institution's initials, and neither
    is met before this page.  Note what was NOT done: "aprotic acceptors" was not renamed to
    a plain paraphrase, because the drawn name has to match the tables that carry the numbers.
  * WHAT ARRIVED IS AIR.  (a) drops from 39 drawn words to 20 and gains no element.  The panel
    is re-laid in printed points from its own box (the idiom (b) has used since 2026-08-09)
    instead of the OLD_PAGE_SCALE remap, so the schematic is centred in the box it now has
    rather than sitting where a two-line paragraph used to leave it, and (a)'s type floor rises
    from 7.09 pt to 7.6 pt -- (b)'s FS_NAME -- inside the room the deleted prose frees.

  The float's HEIGHT AND WIDTH ARE UNCHANGED, deliberately: a shorter float reflows the body
  from page 4 onward, and the page counts are fixed at 33 / 84.  The space bought is spent
  inside panel (a), not given back to the text.

2026-08-09 THE PANEL (b) REBUILD, and what it did NOT change. Every referee-forced item below
is still here -- the strip with its three counts, three distinct marks with three distinct
reasons, one-sided blocks with no interval cap, "UD reference profiles", n = 477, the three
classes and their six numbers. What changed is the size, contrast and coordinate system each
of them is drawn at, because the old drawing could be read confidently and read WRONG:

  * TWO UNLABELLED COORDINATE SYSTEMS, 18.5 pt apart and flush right. The strip's x was
    ordinal rank over 59 categories; the bars' x was magnitude in (ln gamma)^2; both ran to
    the same right-hand x with no scale on either, which is the canonical way to assert a
    shared axis. The bars now carry a drawn, zeroed, numbered rule (below), and the strip
    stops 14 pt short of it.
  * THE THIRD BAR ENCODED A DIFFERENT QUANTITY. Where the bound exceeds the total error the
    old drawing made the BOUND the bar's length and hid the error in a 0.95 pt interior
    hairline, so comparing lengths -- what bar charts train a reader to do -- read 0.140 for
    the acceptor-only aprotics, 58% too large, and the panel's own "25-fold" came out as 16.
    Now the filled bar ends at the total error in ALL THREE rows and the bound is the same
    object in all three: an ink rule overhanging the bar. In the third row that rule simply
    stands past the bar's end, which is the disclosure drawn instead of asserted.
  * ONE SYMBOL, FOUR PLACEMENTS, THREE SIZES, one of them floating into the line above. The
    asterisk now appears exactly twice, both inline: on the standing class's name, and inside
    "1 stands" beneath the tick it marks.
  * "FIFTEEN BOUNDABLE (FILLED)" DID NOT COUNT TO FIFTEEN. The fifteenth changed colour AND
    height at once, so "filled" read as the fourteen-long grey run; and the forty-four were
    themselves filled rectangles, separated from the fifteen by a 1.89:1 tint step. Now
    boundable/unboundable is fill-versus-outline, one categorical attribute, every tick the
    same height, and "stands" is a separate channel -- the mark below the strip.
  * THE CONTRAST THE PANEL EXISTS TO DRAW WAS BELOW ITS OWN THRESHOLD OF VISIBILITY. The
    three teal blocks were 5.10, 10.18 and 6.65 pt wide, a 5.08 pt spread -- and water's
    bound is exactly twice the glycol ethers', which the old drawing showed doubling 26 pt
    above a red line saying the bound "hardly moves". The three bound rules now span ~8.6 pt
    against ~175 pt of spread in the bar ends, on one numbered rule, and the red line says
    what that is: 2-fold against 25-fold.

WHY (b) COULD NOT SIMPLY BE ENLARGED. The binding constraint is the acceptor-only aprotics'
overshoot, B_insuff^up - MSE = 0.1404 - 0.0891 = 0.0513 (ln gamma)^2, on an axis that must
also reach 2.25. Getting that overshoot to ~7.5 pt needs >= 147 pt per unit, i.e. >= 360 pt of
bar span and >= 466 pt of panel -- the full measure of the page and therefore a second row,
which is a 2.4x taller float. At this panel's width the overshoot is ~4 pt and is carried by
an annotation on its own row as well as by size. Two dodges were considered and rejected: a
broken axis destroys the 25-fold length reading, and plotting sqrt(MSE) breaks additivity, so
"at most" + "at least" would no longer sum to the total and the legend would stop meaning
anything. Linear, contiguous, one scale.

2026-08-07 THE STRIP, and why three bars alone were a misdrawing. Two referees, independently:
three solvent classes summing to 350 rows are drawn out of the fifty-nine strata the search
covers, and a reader with only the bars in front of them reads the map as three classes wide.
The panel is the paper's one overview display of the finding's SHAPE, and the shape is that most
of the map supports no statement at all -- which is what the abstract says ("most strata
unboundable") and what the bars, alone, deny. The strip draws all fifty-nine: outlined where no
bound exists (forty-four), filled where one does (fifteen), and the one row set the
admissibility rule leaves standing marked beneath the strip by the same asterisk its bar wears.
The bars are then labelled for what they are, the three of those fifteen that are solvent
classes. Do not delete the strip to buy space for the bars: without it the three bars are a
claim about the map's width, and the claim is false.

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
the design can bound at this cell (n >= 40); their values are READ AT BUILD TIME from
results/b_insuff/stratified_map_table.csv (set=broad_477, axis=solvent_class, unit=row,
convention=res) and are the same cells the map figure and Table 2 carry. Do not put the
aggregate bar back, and do not add a fourth class without checking that it clears n = 40.

    MPLBACKEND=Agg python scripts/analysis/make_overview_figure.py
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "figs" / "fig_overview"
MAP_TABLE = ROOT / "results" / "b_insuff" / "stratified_map_table.csv"

# palette shared with make_concept_figures.py
SALMON = "#E8A98C"   # the fixed closure and the external reference input
TEAL = "#7FB5A6"     # the learned representation
INK = "#4D4D4D"
# GRAY (#9AA0A6, 2.51:1 on the panel fill) is GONE as of 2026-08-10.  It survived the 2026-08-09
# contrast pass -- which replaced it everywhere in (b) -- only because panel (a) still set one
# two-line sentence in it, and that sentence has now gone too.  Leaving the constant behind would
# leave a below-floor colour in reach that _check_contrast() does not police, because nothing
# would be using it to police.
HURT = "#B5654A"
PAPER = "#FBF9F7"

# (b)'s own text and fill colours.  EVERY DISCLOSURE A REFEREE FORCED INTO THIS PANEL USED TO BE
# SET IN #9AA0A6, which is 2.51:1 on the panel fill -- 44% under the 4.5:1 body-text floor -- and
# the forty-four unboundable ticks were #DFD9D3 at 1.33:1, i.e. drawn below the threshold at which
# the strip can be counted.  These are their replacements; _check_contrast() below is the guard.
SUBINK = "#6E6E6E"    # secondary text: 4.85:1              (was #9AA0A6, 2.51:1)
STRIPO = "#6E6E6E"    # unboundable tick, OUTLINE only      (was #DFD9D3 filled, 1.33:1)
TEAL_D = "#3E6E62"    # the input-bound block: 5.66:1 on paper, 3.01:1 against SALMON, so the two
                      # blocks survive greyscale printing without relying on an outline (the old
                      # pale #DDE7E3 was 1.20:1 on paper and 1.58:1 against SALMON).
TEAL_W = "#35705E"    # the teal-side legend word
SALMON_D = "#A2543A"  # the salmon-side legend word: 5.17:1

FIG_W_IN = 502.58 / 72.0   # \linewidth of the two-column float, exactly (see SCALE DISCIPLINE)
FIG_H_IN = 2.515 - 22.0 / 72.0   # 2026-08-24: the strip's height, given back to the page

# ---- SCALE DISCIPLINE.  A coded point must be a printed point. -------------------------------
# The comment that stood here until 2026-08-09 said "8.0 in prints at 0.88, so nothing here falls
# below 7 pt".  It was false twice over.  savefig.bbox was "tight" (rcParams, below), so a coded
# 576 pt canvas was emitted as a 581.52 pt box and \includegraphics[width=\linewidth] scaled it by
# 0.86427, not 0.88 -- and at 0.86427 the smallest coded size in (b), 6.3, printed at 5.44 pt.
# The fix is not a bigger font list, it is to stop guessing: the figure is now saved with
# bbox_inches=None at exactly \linewidth, so the emitted media box IS the printed box, the
# \includegraphics scale is 1.000, and every fontsize= and lw= in this file is a printed point.
# If you change FIG_W_IN, you break that identity; if you change savefig.bbox back to "tight", you
# break it silently.  _check_media_box() re-derives it from the emitted PDF at the end of the run.
plt.rcParams.update({
    "font.family": "serif", "text.usetex": False, "svg.fonttype": "none",
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "savefig.dpi": 300, "savefig.bbox": None, "figure.dpi": 150,
})

# OLD_PAGE_SCALE survives only for the two SHARED type sizes -- the panel letter, the panel title
# and the suptitle -- which are (b)'s as much as (a)'s and are not this pass's to move.  Panel (a)'s
# own geometry no longer goes through it: as of 2026-08-10 (a) is laid out in printed points from
# its own panel box, like (b), so the "multiply back by the old page scale and remap every y" path
# that carried the unrevised (a) through the 2026-08-09 rebuild is gone.
OLD_PAGE_SCALE = 0.86427


def _a(fs):
    """A SHARED font size (panel letter, panel title, suptitle), in the accepted figure's units."""
    return fs * OLD_PAGE_SCALE


# ---- colour audit ---------------------------------------------------------------------------
def _lum(h):
    def c(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _check_contrast():
    for name, col, floor in (("SUBINK", SUBINK, 4.5), ("INK", INK, 4.5), ("TEAL_W", TEAL_W, 4.5),
                             ("SALMON_D", SALMON_D, 4.5), ("STRIPO", STRIPO, 3.0),
                             ("TEAL_D", TEAL_D, 4.5)):
        r = _ratio(col, PAPER)
        assert r >= floor, f"{name} {col} is {r:.2f}:1 on the panel fill, floor {floor}"
    # HURT now carries exactly one object in the whole figure -- (b)'s display line.  It left
    # panel (a) on 2026-08-10 with the outcome it was colouring; see the note at the top.
    assert _ratio(HURT, PAPER) >= 4.0
    # the two blocks must be separable without hue, i.e. in a greyscale print
    assert _ratio(TEAL_D, SALMON) >= 2.5, f"teal/salmon {_ratio(TEAL_D, SALMON):.2f}:1"


# ---- the three classes, read from the artifact rather than retyped ---------------------------
# 2026-08-09.  These six numbers used to be a literal in this file while the comment above named
# the CSV they come from; a number that moves in the artifact then moves in Table 2 and the map
# figure and silently does not move here.  They are now read, and the marks are DERIVED from the
# same two columns the admissibility rule of Sec. 4.2(i) is defined on, so a class cannot be drawn
# wearing a mark the table does not give it.
#
# THE IDENTITY THE PANEL RESTS ON, verified below on all fifteen boundable strata:
#     b_closure_lb = MSE - B_insuff^up        and        margin = MSE - 2 B_insuff^up
# so "margin > 0" is exactly "the salmon block is longer than the teal one".  The admissibility
# test is therefore already legible off any row, which is why this panel draws no threshold line
# at MSE/2 -- the 2026-08-02 note that retired it stands, and this is the reason it stands.
# 2026-08-10 THE CLASS NAME CARRIES ITS DEFINING CONDITION.  "aprotic acceptors" printed on page 4
# and was defined nowhere in the article -- the SI's class rule (run_b_insuff_stratified_map.py:52)
# is "no O-H or N-H, but a carbonyl, a nitrile, a pyridine-type" acceptor, and the negative half of
# that rule is the whole of what a reader needs here.  The NAME is unchanged, because Table 2 and
# Fig. 6 carry the numbers under it; only the gloss is new.  "glycol ethers" and "water" need none.
DISPLAY = {"glycol_ether": "glycol ethers", "water": "water",
           "aprotic_acceptor": "aprotic acceptors"}
# The gloss is a SEPARATE object at the secondary size and colour, so the row still reads
# name / mark / verdict at one size and the definition sits under the eye without joining them.
# "/" is "or"; the full "no O-H or N-H" is 8.5 pt too wide for the line and the type does not come
# down to buy it -- 7.0 pt is (b)'s floor and this file's standing commitment.
GLOSS = {"aprotic_acceptor": "(no O–H/N–H)"}


def load_map():
    rows = []
    with MAP_TABLE.open() as fh:
        for r in csv.DictReader(fh):
            if r["set"] == "broad_477" and r["unit"] == "row" and r["convention"] == "res":
                rows.append(r)
    assert len(rows) == 59, f"{len(rows)} strata at the headline cell, expected 59"
    boundable = [r for r in rows if r["boundable_at_headline_cell"] == "True"]
    assert len(boundable) == 15, f"{len(boundable)} boundable, expected 15"
    for r in boundable:              # the identity the drawing encodes
        mse, b = float(r["mse"]), float(r["b_insuff_up"])
        assert abs(float(r["margin"]) - (mse - 2 * b)) < 1e-3
        assert abs(float(r["b_closure_lb"]) - (mse - b)) < 1e-3
    classes = [r for r in boundable if r["axis"] == "solvent_class"]
    assert len(classes) == 3, f"{len(classes)} boundable solvent classes, expected 3"
    out = []
    for r in sorted(classes, key=lambda r: -float(r["margin"])):   # the map's own order
        stable = r["test_b_sign_survives_loso"] == "True"
        positive = float(r["margin"]) > 0
        # THE MARKS ARE NOT DECORATION and one mark cannot carry two reasons.  Until 2026-08 both
        # unestablished classes wore a dagger glossed "the ordering here does not survive removing
        # one contributing laboratory", which is true of water and FALSE of the acceptor-only
        # aprotics: that cell is admissible in all four unit x convention cells and survives every
        # one of its four deletions.  It is not established because its margin is not positive and
        # the instrument is one-sided.  The three marks are derived here so they cannot drift:
        #   *  bounded, sign-stable under deletion, margin positive  -- it stands
        #   +  the sign does not survive deleting a contributing laboratory
        #   ++ the sign survives, but the margin is not positive
        mark = "\\ast" if (stable and positive) else ("\\dagger" if not stable else "\\ddagger")
        out.append(dict(name=DISPLAY[r["stratum"]], gloss=GLOSS.get(r["stratum"], ""),
                        mark=mark, n=int(r["n"]),
                        b=float(r["b_insuff_up"]), mse=float(r["mse"])))
    assert [c["mark"] for c in out] == ["\\ast", "\\dagger", "\\ddagger"]
    return out


CLASSES = load_map()
_check_contrast()

# ---- the figure frame ------------------------------------------------------------------------
fig = plt.figure(figsize=(FIG_W_IN, FIG_H_IN))
gs = fig.add_gridspec(1, 2, width_ratios=[1.32, 1.0], wspace=0.10,
                      left=0.015, right=0.985, top=0.902, bottom=0.012)
axa = fig.add_subplot(gs[0]); axa.set_xlim(0, 1.32); axa.set_ylim(0, 1.0); axa.axis("off")
axb = fig.add_subplot(gs[1]); axb.set_xlim(0, 1.0); axb.set_ylim(0, 1.0); axb.axis("off")

PANEL_BOX = {}
for ax, xmax, letter in ((axa, 1.32, "a"), (axb, 1.0, "b")):
    PANEL_BOX[letter] = FancyBboxPatch((0.01, 0.02), xmax - 0.02, 0.94,
                                       boxstyle="round,pad=0.006,rounding_size=0.02",
                                       fc=PAPER, ec="#E4DED8", lw=1.0, zorder=0)
    ax.add_patch(PANEL_BOX[letter])

# Everything below is specified in PRINTED POINTS measured from a panel box's own top-left corner,
# and converted through the box the renderer actually drew.  Nothing is a hand-tuned axis fraction,
# so a change of figure size moves the drawing rigidly instead of silently rescaling one element
# against another -- which is how the old panel came to have five distinct left edges, one of them
# 3.70 pt OUTSIDE its own text margin and another 7.31 pt outside the border.
fig.canvas.draw()
_R = fig.canvas.get_renderer()
_PX = fig.dpi / 72.0


def _geom(ax, letter):
    b = PANEL_BOX[letter].get_window_extent(renderer=_R)
    a = ax.get_window_extent(renderer=_R)
    return dict(bx=b.x0, by=b.y1, bw=b.width / _PX, bh=b.height / _PX,
                ax0=a.x0, ay0=a.y0, aw=a.width, ah=a.height)


GA, GB = _geom(axa, "a"), _geom(axb, "b")


def bx(dx, g=None):
    """x, in axes coords, dx printed points right of the panel box's left edge."""
    g = g or GB
    return (g["bx"] + dx * _PX - g["ax0"]) / g["aw"] * (1.32 if g is GA else 1.0)


def by(dy, g=None):
    """y, in axes coords, dy printed points below the panel box's top edge."""
    g = g or GB
    return (g["by"] - dy * _PX - g["ay0"]) / g["ah"]


BOX_W = GB["bw"]
BOX_H = GB["bh"]
MARGIN = 6.0                     # ONE text margin, left and right, for every object in (b)
L, R = MARGIN, BOX_W - MARGIN
IW = R - L

# ---- type ------------------------------------------------------------------------------------
# Ten distinct sizes, eight of them printing below 7 pt, is what "overloaded" and "unreadable"
# were made of.  Five remain in (b) and the smallest is 7.0 pt: below the article's \footnotesize
# tables (8 pt) and its 10 pt body, which a figure may be -- a caption-adjacent label read at
# arm's length is not a table entry read in sequence -- but far above the 5.44 pt at 2.51:1 that
# carried this panel's disclosures until now, and above the 7.09 pt floor of panel (a).
FS_LETTER, FS_TITLE = _a(11.5), _a(10.5)     # 9.94 / 9.07, shared with (a) and unchanged
FS_SAY = 7.5                                 # the one display line, set apart by colour not size
FS_NAME = 7.5                                # the three class names
FS_TXT = 7.0                                 # everything else that is words or numerals

TITLE_Y = 12.0                               # both panels' title line, printed pt below box top


def say(dx, dy, s, fs=FS_TXT, color=SUBINK, ha="left", va="center", g=None, ax=None, **kw):
    ax = ax or axb
    return ax.text(bx(dx, g), by(dy, g), s, ha=ha, va=va, fontsize=fs, color=color,
                   zorder=6, **kw)


def wpt(artist):
    return artist.get_window_extent(renderer=_R).width / _PX


for ax, letter, title, g in ((axa, "a", "The pipeline, and the substitution", GA),
                             (axb, "b", "Where the error sits", GB)):
    ax.text(bx(9.0, g), by(TITLE_Y, g), letter, ha="left", va="center", fontsize=FS_LETTER,
            color=INK, fontweight="bold", zorder=1)
    ax.text(bx(21.0, g), by(TITLE_Y, g), title, ha="left", va="center", fontsize=FS_TITLE,
            color=INK, zorder=1)

# ---------------- (a) the pipeline and the substitution ----------------
# 2026-08-10.  Printed points from (a)'s own panel box, the idiom (b) uses; nothing here is a
# hand-tuned axes fraction and no size goes through OLD_PAGE_SCALE any more.  WHAT IS DRAWN AND
# WHY NOTHING ELSE IS: four boxes and four arrows are the composed predictor of Eq. (1) -- inputs,
# encoder, the learned intermediate, the fixed map -- and the fifth arrow is the one operation the
# paper performs on it, putting the tabulated profile in the learned one's place.  There is no
# outcome, no colour standing for an outcome, and no sentence: what the substitution does to the
# prediction is a result, it is measured in Sec. 3, and page 4 is three sections early for it.
FS_A_BOX = 7.6          # box labels; the panel's type floor, equal to (b)'s FS_NAME
FS_A_LAB = 7.6          # the labels outside the boxes
FS_A_SYM = 10.4         # the two profile symbols
A_PAD_X, A_PAD_Y = 4.8, 4.2          # printed pt of air inside a box, around its label
# A_PAD_X and GAP are set by ONE constraint and are not free: four boxes, four arrows and the
# word "solubility" have to reach the right margin and stop, and the assertion below is where
# that is enforced.  If a label in (a) ever gets longer, these come down, not the type.

A_BW = GA["bw"]
AL, AR = 8.0, A_BW - 8.0             # (a)'s text margin, its own, wider box notwithstanding


def bxa(dx):
    return bx(dx, GA)


def bya(dy):
    return by(dy, GA)


def tw(s, fs, ax=None):
    """Printed width of a string, measured rather than estimated."""
    t = (ax or axa).text(0, 0, s, fontsize=fs)
    w = t.get_window_extent(renderer=_R).width / _PX
    t.remove()
    return w


def abox(x0, x1, ytop, ybot, text, fc, ec=INK, fs=FS_A_BOX, tc=INK, lw=1.1):
    """A rounded box on (a), cornered in printed pt, labelled on its centre."""
    axa.add_patch(FancyBboxPatch((bxa(x0), bya(ybot)), bxa(x1) - bxa(x0), bya(ytop) - bya(ybot),
                                 boxstyle="round,pad=0.004,rounding_size=0.018",
                                 fc=fc, ec=ec, lw=lw, mutation_aspect=0.55, zorder=3))
    axa.text(bxa((x0 + x1) / 2), bya((ytop + ybot) / 2), text, ha="center", va="center",
             fontsize=fs, color=tc, zorder=4)


def arrow(p0, p1, color=INK, lw=1.6, mut=11):
    axa.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", color=color, lw=lw,
                                  mutation_scale=mut, zorder=2))


# widths from the type, so a box can never be narrower than the words in it
W_IN = max(tw("solute", FS_A_BOX), tw("+ solvent", FS_A_BOX)) + 2 * A_PAD_X
W_ENC = tw("encoder", FS_A_BOX) + 2 * A_PAD_X
W_SIG = tw(r"$\hat\sigma$", FS_A_SYM) + 2 * A_PAD_X
W_MOD = max(tw("thermodynamic", FS_A_BOX), tw("model (fixed)", FS_A_BOX)) + 2 * A_PAD_X
GAP = 7.5

# ROWS.  The pipeline and the substitution are one block, centred between the title line and the
# foot of the box -- so the schematic sits in the panel it has rather than where a deleted
# paragraph used to hold it down.
ROW_H = 2 * FS_A_BOX + 2 * A_PAD_Y                    # a two-line box
# SIGMA-STAR IS DRAWN THE SIZE OF THE SLOT IT GOES INTO, not the size of its own glyph: the whole
# content of (a)'s lower half is that one object can stand where the other does, and two boxes of
# different heights deny it in the only channel a schematic has.
SYM_H = ROW_H
STACK = 26.0                                          # pipeline foot to sigma-star head
BLOCK = ROW_H + STACK + SYM_H
A_TOP, A_BOT = TITLE_Y + 12.0, BOX_H - 6.0
P_TOP = A_TOP + (A_BOT - A_TOP - BLOCK) / 2.0
P_BOT = P_TOP + ROW_H
S_TOP = P_BOT + STACK
S_BOT = S_TOP + SYM_H
P_MID = (P_TOP + P_BOT) / 2.0
S_MID = (S_TOP + S_BOT) / 2.0

x = AL
abox(x, x + W_IN, P_TOP, P_BOT, "solute\n+ solvent", "white")
x += W_IN
arrow((bxa(x), bya(P_MID)), (bxa(x + GAP), bya(P_MID)))
x += GAP
abox(x, x + W_ENC, P_TOP, P_BOT, "encoder", TEAL, tc="white", lw=0)
x += W_ENC
arrow((bxa(x), bya(P_MID)), (bxa(x + GAP), bya(P_MID)))
x += GAP
SIG_L, SIG_R = x, x + W_SIG
abox(SIG_L, SIG_R, P_TOP, P_BOT, r"$\hat\sigma$", TEAL, fs=FS_A_SYM, tc="white", lw=0)
x += W_SIG
arrow((bxa(x), bya(P_MID)), (bxa(x + GAP), bya(P_MID)))
x += GAP
abox(x, x + W_MOD, P_TOP, P_BOT, "thermodynamic\nmodel (fixed)", SALMON, tc=INK, lw=0)
x += W_MOD
arrow((bxa(x), bya(P_MID)), (bxa(x + GAP), bya(P_MID)))
axa.text(bxa(x + GAP + 3.0), bya(P_MID), "solubility", ha="left", va="center",
         fontsize=FS_A_LAB, color=INK, zorder=4)
assert x + GAP + 3.0 + tw("solubility", FS_A_LAB) <= AR, "(a)'s pipeline runs past its margin"

# THE SUBSTITUTION, and only the substitution.  sigma-star sits under the slot it replaces, the
# arrow points into that slot, and the two labels say where the value comes from and when it is
# put in.  SALMON_D, not HURT: the colour names the object the arrow carries, not a verdict on it.
SIG_C = (SIG_L + SIG_R) / 2.0
abox(SIG_L, SIG_R, S_TOP, S_BOT, r"$\sigma^\star$", SALMON, fs=FS_A_SYM, tc=INK, lw=0)
arrow((bxa(SIG_C), bya(S_TOP - 1.5)), (bxa(SIG_C), bya(P_BOT + 2.0)), color=SALMON_D, lw=1.8)
axa.text(bxa(SIG_L - 6.0), bya(S_MID), "external reference\nprofile (VT-2005)", ha="right",
         va="center", fontsize=FS_A_LAB, color=INK, zorder=4)
axa.text(bxa(SIG_R + 6.0), bya(S_MID), "substituted at\nprediction time", ha="left",
         va="center", fontsize=FS_A_LAB, color=SALMON_D, zorder=4)

# ---------------- (b) the split, per solvent class ----------------
#   name                      n     B_insuff^up   MSE     verdict
#   glycol ethers            182       0.108     2.252    established
#   water                    111       0.215     0.477    not admissible -- the sign flips under two
#                                                         of its three leave-one-source-out deletions
#   acceptor-only aprotics    57       0.140     0.089    admissible, not established -- the bound
#                                                         exceeds the total error, and a non-positive
#                                                         margin is failure to separate, not a
#                                                         certified reversal
# Only the first clears the admissibility rule of Sec. 4.2(i), and a front-matter panel that draws
# three positive-looking bars with no mark says three things the Results forbid.  The marks and
# their reasons stay until the rule changes; do not drop them to buy space, and do not add a class
# without checking both n >= 40 and its admissibility column in results/b_insuff/admissibility_table.csv.
#
# 2026-08-07 THE STANDING CLASS CARRIES A MARK OF ITS OWN, and the caption no longer says
# "unmarked".  A referee: with the other two marked, an unmarked block reads as a CATEGORY, and a
# reader cannot tell whether it means "passed the rule" or "not yet put to it" -- absence of a
# disqualification is not a mark.  The asterisk is that mark, and it is glossed by the rule it
# clears rather than by the absence of the other two reasons.  Three marks, three reasons; do not
# go back to two.

# the dateline carries the two things the caption is not allowed to have to buy back in words --
# the database this half of the figure is measured on, and n -- plus the unit the bars are in.
# 2026-08-10: THE DATABASE IS NAMED IN A WORD AND NOT IN INITIALS.  "UD reference profiles" put
# initials on page 4 whose expansion is on page 7, in the abbreviation table; "Delaware (UD)" is
# the same name, glossed at first mention, and it binds UD for every later use.  The name itself
# is not droppable -- (a) and (b) are measured on DIFFERENT tabulated databases and the 2026-08-07
# note above is what stops the two halves being read as one table.
say(L, 23.5, "$59$ strata, Delaware (UD) profiles ($n{=}477$), $(\\ln\\gamma)^2$", fs=FS_NAME)

# ---- the whole search: REMOVED FROM THE PANEL 2026-08-24, MOVED INTO THE CAPTION ------------
# A strip of fifty-nine ticks used to run above the bars, outlined where no bound exists and
# filled where one does, so that three bars could not be read as the whole search.  The reason
# was right and the object was wrong: the reader this panel is for reported it as the thing that
# made the panel unreadable, and a second horizontal object with its own grammar, its own two
# labels and no scale is a lot to charge for one guard.  The guard now runs in the caption, in
# words -- 'three of the fifteen strata, of fifty-nine searched, that carry a bound' -- which
# costs the reader one clause and the panel nothing.  Do not restore the strip without first
# checking that the caption has stopped saying it.
N_STRATA, N_BOUNDABLE = 59, 15          # kept: the caption's counts are asserted against these

# ---- legend, set as a header over the zone each colour occupies rather than as a lookup -------
# The teal entry sits at the left margin, where every teal block starts; the salmon entry is
# right-aligned, where the salmon runs.  Position assigns the colour and the swatch is the backup.
# The teal swatch carries the bound rule on its right edge, which is how the rule in each row is
# taught without a third legend entry.
# 2026-08-24: LEG_Y was 60.0 and ROW0 73.5, both set below a strip that no longer
# exists.  STRIP_RECLAIM is the height it and its label line occupied; subtracting it
# in one place keeps every offset below in its original relative position.
STRIP_RECLAIM = 22.0
LEG_Y, SW_W, SW_H = 60.0 - STRIP_RECLAIM, 11.0, 5.6


def swatch(dx, dy, fc, ec):
    axb.add_patch(Rectangle((bx(dx), by(dy + SW_H / 2)), bx(dx + SW_W) - bx(dx),
                            by(dy - SW_H / 2) - by(dy + SW_H / 2), fc=fc, ec=ec, lw=0.6, zorder=3))


swatch(L, LEG_Y, TEAL_D, TEAL_D)
axb.plot([bx(L + SW_W)] * 2, [by(LEG_Y - SW_H / 2 - 1.2), by(LEG_Y + SW_H / 2 + 1.2)],
         lw=1.2, color=INK, zorder=5, solid_capstyle="butt")
# "the model" BECAME "the map as deployed", 2026-08-11 (round 7, referee CHEM item 9).  The block
# is B_closure, which is the error of the composite of the FIXED KERNEL and the one-conformer
# gas-phase calculation that produced z*, and the profile-calculation share of it is left unbounded
# in the text.  A reader who meets "the model" against "the inputs" concludes the kernel is the
# culprit and the profiles are exonerated, which is the one split this design cannot make.  The
# caption carries the unbounded share.  Do not shorten this back to a word for the kernel alone.
# THE MEASURE SETS THE WORDING.  "the map as deployed, at least" runs 104 pt and leaves the salmon
# swatch overlapping the teal label's last word; the room between the two legend entries is about
# 96 pt at this type size.  CORRECTED 2026-08-11: "the map" is NOT the paper's term for the
# composite.  The paper defines the composite as "the fixed map together with the calculation that
# produced z*", so "the map" names the kernel side ALONE and this rationale had it backwards.  The
# short entry is kept because the caption says in full which of the two the bound is on, and the
# legend cannot carry that in the 96 pt available; it is the caption and not the legend that
# disambiguates.
say(L + SW_W + 4.0, LEG_Y, "the inputs, at most", color=TEAL_W)
_rl = say(R, LEG_Y, "the fixed map, at least", color=SALMON_D, ha="right")
swatch(R - wpt(_rl) - 4.0 - SW_W, LEG_Y, SALMON, SALMON_D)

# ---- the three rows ---------------------------------------------------------------------------
# ONE ENCODING, THREE ROWS, NO SPECIAL CASE.  The filled bar always ends at the TOTAL ERROR and the
# bound is always the same object: a 1.2 pt ink rule at B_insuff^up, overhanging the bar so that
# the three bounds can be compared to each other across the rows.  Teal is [0, min(B, MSE)], the
# at-most region; salmon is [B, MSE], the at-least region; where the bound runs past the total
# error there is no salmon block at all and the bound's unused headroom is drawn OPEN, because
# nothing is claimed there.  Nothing in the panel has two caps: a non-positive margin is failure
# to separate, not a certified reversal, and no reversed or negative block is drawn.
SCALE = 2.30                     # (ln gamma)^2 across IW
PPU = IW / SCALE
BAR_H, ROW0, ROW_PITCH, NAME_TO_BAR = 6.4, 73.5 - STRIP_RECLAIM, 18.0, 4.8
# THE ONE DISTANCE THE WHOLE PANEL TURNS ON.  If a future width or scale edit shrinks it, the
# third row silently goes back to being a 2 mm striped dot with its quantity hidden inside it.
_over = (CLASSES[2]["b"] - CLASSES[2]["mse"]) * PPU
assert _over >= 3.5, f"the aprotic overshoot is {_over:.2f} pt; it must stay legible"

REASONS = {"\\ast": "stands: bounded, stable, positive",
           "\\dagger": "not established",
           "\\ddagger": "not established"}
# The two failing rows' reasons are set beside their own bars, in the space their short bars leave,
# so each reason is adjacent to the drawn fact it names -- water's sign fragility beside the bar
# whose sign it is, and the aprotics' overshoot beside the rule that overshoots.  The standing row
# has no such space (its bar fills the axis), so its reason follows its name.  All three verdicts
# ride on the name line: "not established" is the phrase that separates measured-and-failed from
# never-put-to-the-rule, which is the distinction the third round of review forced.
ASIDES = {"\\dagger": "dropping a laboratory flips the sign",
          "\\ddagger": "the bound runs past the total error"}


def bar_x(v):
    return L + v * PPU


for k, c in enumerate(CLASSES):
    ny = ROW0 + k * ROW_PITCH
    yt, yb = ny + NAME_TO_BAR, ny + NAME_TO_BAR + BAR_H
    nm = say(L, ny, c["name"], fs=FS_NAME, color=INK)
    _x = L + wpt(nm) + 2.0
    if c["gloss"]:
        _gl = say(_x, ny, c["gloss"])
        _x += wpt(_gl) + 2.0
    # THE SYMBOLS ARE GONE, THE VERDICTS ARE NOT.  Each row used to carry *, dagger or ddagger
    # next to its name and the reason beside it -- a footnote apparatus for three rows, on a panel
    # whose reader has to look somewhere else to decode it.  The mark is dropped and the reason it
    # pointed at is simply set where it stood, so the verdict is read rather than resolved.
    _rx = _x + 1.0
    _rs = say(_rx, ny, "\u2014 " + REASONS[c["mark"]], color=INK)
    # the name line now carries a gloss on one row, which makes it the panel's tightest line
    assert _rx + wpt(_rs) <= R, f"{c['name']!r}: its name line runs past the margin"
    b, mse = c["b"], c["mse"]
    axb.add_patch(Rectangle((bx(L), by(yb)), bx(bar_x(min(b, mse))) - bx(L), by(yt) - by(yb),
                            fc=TEAL_D, ec="none", lw=0, zorder=3))
    if mse > b:
        axb.add_patch(Rectangle((bx(bar_x(b)), by(yb)), bx(bar_x(mse)) - bx(bar_x(b)),
                                by(yt) - by(yb), fc=SALMON, ec="none", lw=0, zorder=3))
    else:                       # the bound's unused headroom: drawn, and drawn empty
        axb.add_patch(Rectangle((bx(bar_x(mse)), by(yb)), bx(bar_x(b)) - bx(bar_x(mse)),
                                by(yt) - by(yb), fc="none", ec=TEAL_D, lw=0.6,
                                zorder=3))
    axb.plot([bx(bar_x(b))] * 2, [by(yb + 1.6), by(yt - 1.6)], lw=1.2, color=INK, zorder=5,
             solid_capstyle="butt")
    if c["mark"] in ASIDES:
        say(max(bar_x(mse), bar_x(b)) + 8.0, yt + BAR_H / 2, ASIDES[c["mark"]])

# ---- the rule the bars stand on ---------------------------------------------------------------
# 2026-08-09 REVERSES one half of the 2026-08-02 note that stood here: "no threshold line, no
# numbers".  The threshold line stays out, and for the reason recorded at load_map() -- margin =
# MSE - 2 B identically, so the admissibility test is which of the two blocks is longer and needs
# no line.  The NUMBERS come back, because the trade that note made is what left the panel with
# two unlabelled coordinate systems and a headline no reader could check: the strip and the bars
# were two flush-right horizontal objects with no scale on either.  With a zeroed, numbered rule
# under the bars and none under the strip, 2.2518/0.0891 = 25 is recoverable off the page with a
# ruler, and the strip is visibly not on it.
AXIS_Y = ROW0 + 2 * ROW_PITCH + NAME_TO_BAR + BAR_H + 5.8
axb.plot([bx(L), bx(R)], [by(AXIS_Y)] * 2, lw=0.7, color=INK, zorder=4)
for v, lab in ((0.0, "0"), (0.5, "0.5"), (1.0, "1.0"), (1.5, "1.5"), (2.0, "2.0")):
    axb.plot([bx(bar_x(v))] * 2, [by(AXIS_Y), by(AXIS_Y + 2.4)], lw=0.7, color=INK, zorder=4)
    say(bar_x(v), AXIS_Y + 7.6, lab, color=INK, ha="center")   # "0", not "0.0": centred on the
    #  axis origin, which is the text margin, a three-glyph numeral would sit outside the panel

# THE CONTRAST IS THE PANEL, and this is the line that says what it is.  It used to read "The
# input bound hardly moves; the error moves 25-fold", 26 pt below a drawing in which water's bound
# is exactly TWICE the glycol ethers' -- the sentence was contradicted by its own panel, and read
# off the bar ends the 25 came out as 16 because the third bar's length was the bound and not the
# error.  Both numbers are now true of exactly the three classes drawn, and both are checkable
# against the rule above: 0.2150/0.1077 = 2.00 and 2.2518/0.0891 = 25.3.
SAY_Y = AXIS_Y + 18.5
say(L, SAY_Y, "The input bound moves 2-fold; the error, 25-fold.", fs=FS_SAY, color=HURT)

fig.suptitle("When do reference physical inputs help a learned solubility model?",
             fontsize=_a(12.5), color=INK, y=0.985)


# ---- the guards ------------------------------------------------------------------------------
def _check_layout():
    """No ink outside the panel, and no type below the floor."""
    bb = PANEL_BOX["b"].get_window_extent(renderer=_R)
    worst, who = -99.0, ""
    for t in axb.texts:
        e = t.get_window_extent(renderer=_R)
        out = max(bb.x0 - e.x0, e.x1 - bb.x1, bb.y0 - e.y0, e.y1 - bb.y1) / _PX
        if out > worst:
            worst, who = out, t.get_text()
        assert t.get_fontsize() >= 6.5, f"{t.get_text()!r} at {t.get_fontsize()} pt"
    for p in axb.patches:
        if p is PANEL_BOX["b"]:
            continue
        e = p.get_window_extent(renderer=_R)
        out = max(bb.x0 - e.x0, e.x1 - bb.x1, bb.y0 - e.y0, e.y1 - bb.y1) / _PX
        if out > worst:
            worst, who = out, f"a {type(p).__name__}"
    assert worst <= -1.0, f"panel (b): {who!r} comes within {worst + 0.0:.2f} pt of its own border"
    # 2026-08-10: (a) gets the same guard.  It never had one, which is part of how it went eleven
    # months without a layout audit while (b) was rebuilt twice.
    ba = PANEL_BOX["a"].get_window_extent(renderer=_R)
    worst, who = -99.0, ""
    for t in axa.texts:
        assert t.get_fontsize() >= 7.0, f"{t.get_text()!r} at {t.get_fontsize()} pt"
        e = t.get_window_extent(renderer=_R)
        out = max(ba.x0 - e.x0, e.x1 - ba.x1, ba.y0 - e.y0, e.y1 - ba.y1) / _PX
        if out > worst:
            worst, who = out, t.get_text()
    for p in axa.patches:
        if p is PANEL_BOX["a"]:
            continue
        e = p.get_window_extent(renderer=_R)
        out = max(ba.x0 - e.x0, e.x1 - ba.x1, ba.y0 - e.y0, e.y1 - ba.y1) / _PX
        if out > worst:
            worst, who = out, f"a {type(p).__name__}"
    assert worst <= -1.0, f"panel (a): {who!r} comes within {worst:.2f} pt of its own border"


def _check_media_box(path):
    """The emitted box must be \\linewidth, or every printed size above is a guess."""
    head = path.read_bytes()[:4000].decode("latin-1", "replace")
    i = head.find("/MediaBox")
    w = float(head[i:i + 80].split("[")[1].split()[2])
    assert abs(w - 502.58) < 0.5, f"media box {w} pt is not \\linewidth; the scale is not 1.000"


_check_layout()
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT}.{ext}", bbox_inches=None)
_check_media_box(Path(f"{OUT}.pdf"))
print(f"wrote {OUT}.pdf / .png   panel (b) {BOX_W:.2f} x {BOX_H:.2f} pt, "
      f"{PPU:.1f} pt per (ln gamma)^2, aprotic overshoot {_over:.2f} pt")
