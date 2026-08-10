#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit the map's table bodies from the deposited admissibility table.

The map is the instrument's declared output, so it prints in the article and
every one of its cells has to come out of the artifact rather than out of a
typist.  This script writes four ``tabular`` bodies (see WHERE EACH TABLE GOES),
one row per stratum of the broad IDAC set at the headline estimator cell (eight
equal-count bins of g(z*), Bessel within-bin variance, row unit, deployed
residual-only convention), into ``paper/si_tables/`` for the manuscript to
``\\input``.  Nothing here is hard-coded: n, pair counts,
source counts, margins, intervals, the full-convention margin, how many of the
four unit x convention cells the stratum is admissible in, and the reason it is
not admissible all come from
``results/b_insuff/admissibility_table.csv``, written by
``scripts/analysis/run_b_insuff_stratified_map.py``.

The one editorial act is compression: the artifact's reason strings are written
for a reader with the whole table in front of them, and the table column is
narrow, so each is rewritten into the same statement in fewer words and each DOI
is replaced by its key P1..P15 in the manuscript's own source list.  The
substitutions are exhaustive and the script raises if a reason string arrives in
a form it does not recognise, so a new failure mode cannot be silently dropped.

WHERE EACH TABLE GOES
---------------------
The map is the instrument's declared output and the abstract names it as what
replaces the retired aggregate verdict, so it may not live only in the
Supporting Information.  Three bodies are written:

    stratified_map_rows_article.tex   ARTICLE.  The fifteen strata the fixed
                                      estimator can bound (n >= 40), on both
                                      axes and at every granularity, with their
                                      sources, margins, intervals and what each
                                      shows.  These are the only strata that can
                                      separate anything, so a reader of the
                                      article alone sees which chemistry
                                      separates and which does not.
    stratified_map_rows.tex           SI, solvent axis, all strata.
    stratified_map_rows_solute.tex    SI, solute axis, cross-tab, whole set.
    stratified_map_rows_detail.tex    SI, error/bound/share/deletion columns.

The SI bodies are the FULL 59 strata, including the 44 the estimator cannot
bound and the 15 of those that carry no estimate at all; nothing is dropped from
either place.

NO VERDICT VOCABULARY: THE CELL STATES THE CONDITION
----------------------------------------------------
Until 2026-08-02 the last column printed a three-value taxonomy --
``established`` / ``admissible, not established`` / a reason -- which is a
coined scheme a reader has to look up, exactly what the Grade column of the
claim ledger was retired for.  The column now states, in ordinary language, the
condition each row is in: what the numbers show, or which test the row fails and
how.  The computed distinctions below still decide WHICH sentence is printed;
what changed is that the sentence says the thing rather than naming it.

NO BOLD ON THE PASSING ROW, 2026-08-05 (round 3, referee 1, must-fix).  That
cell used to print its condition in \textbf, which reads as "this is the
finding" in a table whose other rows carry no null either.  The bold is retired:
the row set the rule leaves standing is the survivor of a 59-fold search that
the map's own chemistry-blind null does not separate from chance, and the null
is now stated in note (d) of the first map table, whose notes the other map
tables adopt.  Do not restore the bold here or the phrase "the one established
finding" in the article.

    positive, robust and not a restatement   "the closure's own error exceeds
      of a larger row set                     the bound on its inputs; the sign
                                              holds when any one publication is
                                              deleted"
    positive and robust, but most of its     "N% of these rows are the X's and
      rows belong to a larger such set        the M outside give <margin>, so
      and its margin does not stand           this margin does not stand outside
      outside it                              the X's: demoted to them by
                                              clause (c)"
    robust but the margin is not positive    "the margin is not positive, so the
                                              two terms are not separated here;
                                              a bound from above cannot show the
                                              inputs are at fault"
    otherwise                                the test it fails, with the number

RESTATEMENT is computed, not asserted.  A positive robust cell A restates B when
B is also positive and robust, B holds more rows, more than half of A's rows are
B's, and A-minus-B does not itself pass -- i.e. A's margin does not stand
outside B.  That is exactly the manuscript's argument for demoting the alkane
solutes, and both inputs come from the artifact: ``stratum_overlap.csv`` for the
shared-row counts and ``admissibility.json``'s
``margins_on_each_side_of_the_overlap`` for the complement.  Nothing about which
stratum wins is written into this file.

Every passing row additionally carries an OVERLAP FLAG naming the other passing
row sets it shares rows with and by how much, so a reader of the map alone
cannot count one row set twice across the two axes.

ONE ROW SET, ONE INTERVAL, 2026-08-07 (two referees, independently).
--------------------------------------------------------------------
The map's bootstrap seed is derived from the STRATUM NAME
(``run_b_insuff_stratified_map.stable_seed``), so the strata that select the
SAME rows under different names each got an INDEPENDENT 3000-draw replicate of
the same interval, and this script printed all of them.  The glycol-ether row
set -- the one finding in the paper -- has three such names and therefore
printed three intervals: ``[+1.27,+2.83]`` (solvent class), ``[+1.27,+2.87]``
(fine family) and ``[+1.23,+2.90]`` (class x role), with the manuscript quoting
the first in its abstract.  Twenty-two pairs of strata in this map are
row-identical, so the same thing happened to water, the mono-alcohols, the
N--H protics and the aprotic acceptors.

Those are not different quantities and they are not different roundings.  A
3000-draw replicate of this interval carries a Monte-Carlo standard deviation of
0.020 on EACH endpoint (forty seeds, deposited in
``glycol_ether_ci_converged.json``), which is twice the second decimal they were
printed to; the four values in the manuscript sat within +-1.8 sd of one mean.

So: row-identical strata now print ONE interval.  Which one is fixed by
position, not by value -- the first name the row set gets in the manuscript's
own axis order (``AXES``/``AXIS_RANK`` below), which is the order a reader meets
it in and was not chosen by reading endpoints.  The map itself now draws one
bootstrap per row set rather than per name (``run_b_insuff_stratified_map.
row_set_key``), so the two agree by construction instead of by this file
suppressing the duplicates.

AND THE SAME QUESTION, ASKED OF EVERY CELL, 2026-08-10
------------------------------------------------------
Converging the glycol ethers repaired the interval that had been NOTICED.  The
apparatus behind it is the same for all of them: this generator prints 35 cells
over 24 row sets and 48 endpoints, every one a 3000-draw replicate rounded to
two decimals, and at that draw count two decimals are not determined.  Measured
over 200 seeds per row set (``results/b_insuff/map_ci_precision.json``), 42 of
the 46 endpoints that come off that apparatus stood inside four Monte-Carlo
standard errors of a rounding boundary; the spread per endpoint runs 0.0009 to
0.223, so the +-0.02 the glycol cell taught us was the RIGHT figure for a cell
whose interval is 1.5 wide and 11x too small for the widest.

Each row set therefore prints at ITS OWN precision, and this generator quotes
``printed_as`` from that deposit with no rounding of its own:

    converged   two decimals, bought with draws.  The glycol ethers keep the
                1.2e8-draw deposit (``glycol_ether_ci_converged.json``), which
                the abstract quotes.
    coarsened   one decimal, which the draw count does determine.
    stated      two decimals with the Monte-Carlo standard deviation printed as
                a superscript on the interval, because neither precision was
                affordable and the honest thing is to show the reader the digit
                is not a datum.
    degenerate  unmoved by any seed, because the two-way resample has about ten
                distinct compositions.  Reproducible, not converged, and said so.

Quoting ``printed_as`` also ends a second defect: the earlier generator read the
3-decimal deposit and rounded it again to two, and on three cells the exact
endpoint and the twice-rounded one printed DIFFERENT second decimals
(``water`` lo, ``aromatic_hydrocarbon`` hi, ``aprotic_acceptor`` lo).

READ ``printing_is_determined`` / ``boundary_margin_se`` OUT OF A DEPOSIT BEFORE
TRUSTING ITS LAST DIGIT.  A small standard error is not on its own a licence: it
is the standard error MEASURED AGAINST THE DISTANCE FROM THE ENDPOINT TO THE
NEAREST ROUNDING BOUNDARY that decides.  At the glycol deposit's first setting
(12 x 100000 draws) the lower endpoint sat 0.0008 above a boundary with a
standard error of 0.00091, so which second decimal a number IN THE ABSTRACT
printed was a property of the seed set.

    python scripts/analysis/make_map_table_tex.py
"""
from __future__ import annotations

import csv
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "results" / "b_insuff" / "admissibility_table.csv"
OVERLAP = ROOT / "results" / "b_insuff" / "stratum_overlap.csv"
SIDES = ROOT / "results" / "b_insuff" / "admissibility.json"
CONVERGED = ROOT / "results" / "b_insuff" / "glycol_ether_ci_converged.json"
PRECISION = ROOT / "results" / "b_insuff" / "map_ci_precision.json"
#: The seed count behind every per-cell precision verdict; it is asserted against the deposit
#: rather than trusted, so this note cannot drift from the run that produced the numbers.
MC_SEEDS_NOTE = 200
#: The map's own draw count, asserted against the deposit below for the same reason.
MC_DRAWS_NOTE = 3000
CI_NOTE = ROOT / "paper" / "si_tables" / "map_ci_note.tex"
CI_BODY = ROOT / "paper" / "si_tables" / "map_ci_body.tex"
OUT = ROOT / "paper" / "si_tables" / "stratified_map_rows.tex"
OUT_SOLUTE = ROOT / "paper" / "si_tables" / "stratified_map_rows_solute.tex"
OUT_ARTICLE = ROOT / "paper" / "si_tables" / "stratified_map_rows_article.tex"
OUT_ARTICLE_B = ROOT / "paper" / "si_tables" / "stratified_map_rows_article_solute.tex"
KEY = ROOT / "paper" / "si_tables" / "map_source_key.tex"
DETAIL = ROOT / "paper" / "si_tables" / "stratified_map_rows_detail.tex"

SET = "broad_477"
UNIT = "row"
CONV = "res"

# The axes, in the order the manuscript reports them, with their printed headings.
# The map prints in the main text and is split over two floats, one per axis, because at 59 rows
# plus notes it does not fit on one page and a half-page float per axis does.
SOLVENT_AXES = [
    ("solvent_class", "Solvent class"),
    ("solvent_class_coarse", "Solvent class, coarse"),
    ("solvent_family_fine", "Solvent family, fine"),
]
SOLUTE_AXES = [
    ("solute_role", "Solute role"),
    ("solute_family", "Solute family"),
    ("solvent_class_x_solute_role", "Solvent class $\\times$ solute role"),
    ("whole_set", "The set as a whole"),
]
AXES = SOLVENT_AXES + SOLUTE_AXES

# Which name a row set's interval is quoted under when several names select the same rows:
# the first in the manuscript's own axis order, which is AXES above and is the order in which
# a reader meets the row set.  Fixed by position, never by looking at the endpoints.
AXIS_RANK = {a: i for i, (a, _) in enumerate(AXES)}

# The SI carries all 59 strata, which is four floats and not two.  At 28 and 31 rows the two
# earlier floats ran 266 pt and 214 pt past the text block, so their last rows printed over the
# folio and off the page -- silently, since LaTeX calls that a warning.  The split below is at
# an axis boundary, never inside one, so no stratum is separated from its neighbours by it.
SI_GROUPS = [
    (SOLVENT_AXES[:2], "stratified_map_rows.tex"),
    (SOLVENT_AXES[2:], "stratified_map_rows_fine.tex"),
    (SOLUTE_AXES[:2], "stratified_map_rows_solute.tex"),
    (SOLUTE_AXES[2:], "stratified_map_rows_xtab.tex"),
]

PRETTY = {
    "glycol_ether": "glycol ether",
    "water": "water",
    "aprotic_acceptor": "aprotic acceptor",
    "mono_alcohol": "mono-alcohol",
    "nh_protic": "N--H protic",
    "halogenated": "halogenated",
    "aromatic_hydrocarbon": "aromatic hydrocarbon",
    "aryl_ether": "aryl ether",
    "aliphatic_hydrocarbon": "aliphatic hydrocarbon",
    "hb_donor_acceptor_O": "H-bond donor and acceptor (O)",
    "hb_acceptor_only": "H-bond acceptor only",
    "hb_donor_N": "H-bond donor (N)",
    "halogenated_nonHB": "halogenated, non-H-bonding",
    "hydrocarbon_nonHB": "hydrocarbon, non-H-bonding",
    "halogenated_aliphatic": "halogenated aliphatic",
    "halogenated_aromatic": "halogenated aromatic",
    "amide_NH": "amide N--H",
    "amine_NH": "amine N--H",
    "ketone_aldehyde": "ketone/aldehyde",
    "azine": "azine",
    "nitrile": "nitrile",
    "ester": "ester",
    "ether": "ether",
    "ketone": "ketone",
    "aldehyde": "aldehyde",
    "alkane": "alkane",
    "alkene": "alkene",
    "alkyne": "alkyne",
    "nitro": "nitro",
    "tertiary_amine": "tertiary amine",
    "organic_solute": "organic solute",
    "water_solute": "water as solute",
    "all": "whole set",
}


def pretty(stratum: str) -> str:
    if "|" in stratum:
        a, b = (s.strip() for s in stratum.split("|"))
        return f"{PRETTY.get(a, a)} $\\vert$ {PRETTY.get(b, b)}"
    return PRETTY.get(stratum, stratum.replace("_", " "))


def head_label(stratum: str) -> str:
    """The row set's chemistry, without the granularity it is named at.

    ``glycol_ether``, ``glycol_ether | organic_solute`` and the fine-level
    ``glycol_ether`` are one row set under three names; the overlap flags group
    them by this label so the flag reads as chemistry rather than as bookkeeping.
    """
    base = stratum.split("|")[0].strip()
    return PRETTY.get(base, base.replace("_", " "))


def hyphen(label: str) -> str:
    """``glycol ether`` -> ``glycol-ether``: the attributive form, for ``... cells``."""
    return label.replace(" ", "-")


def _round(x: float, nd: int) -> str:
    """Half away from zero, which is how this manuscript has always rounded.

    Python's default is half-to-even and its binary floats break ties the other
    way as often as not, so ``-0.435`` printed as ``-0.43`` where every earlier
    draft printed ``-0.44``.  Decimal fixes both.
    """
    q = Decimal(1).scaleb(-nd)
    return str(Decimal(repr(abs(x))).quantize(q, rounding=ROUND_HALF_UP))


def in_last_digit(x: float, decimals: int) -> str:
    """A Monte-Carlo spread expressed in units of the last digit printed.

    The superscript on a stated interval has to fit in a table column that had under a point of
    slack, and 0.0066 set as a superscript is 16.6pt wide -- which is how the first version of
    this pass pushed three of the four map tabulars past the text block.  In units of the last
    printed digit the same number is `0.7', two characters, and it says the thing more directly:
    the second decimal of that endpoint moves by 0.7 of itself between seeds, and 22 of itself in
    the worst cell.  Rounded to two DECIMALS instead it would print 0.01, overstating it by half
    again -- the same class of error as the digit it qualifies.
    """
    u = x / (10.0 ** -decimals)
    return f"{u:.0f}" if u >= 10 else f"{u:.1f}"


def fmt_signed(x: str, nd: int = 2) -> str:
    if x in ("", None):
        return "---"
    v = float(x)
    return ("$+" if v >= 0 else "$-") + _round(v, nd) + "$"


def band(p: str) -> str:
    """The manuscript's own rounding rule for bootstrap frequencies (\\S4)."""
    if p in ("", None):
        return "---"
    v = float(p)
    if v > 0.95:
        return "$>0.95$"
    if v < 0.2:
        return "$<0.2$"
    return f"${{\\approx}}{v:.1f}$"


def fmt_ci(lo: str, hi: str) -> str:
    if lo in ("", None) or hi in ("", None):
        return "---"
    return "$[" + fmt_signed(lo).strip("$") + "," + fmt_signed(hi).strip("$") + "]$"


def main() -> None:
    rows = list(csv.DictReader(SRC.open()))
    broad = [r for r in rows if r["set"] == SET]

    whole = [r for r in broad if r["axis"] == "whole_set" and r["unit"] == UNIT
             and r["convention"] == "res"][0]
    doi_key = {doi: f"P{i}" for i, doi in enumerate(whole["sources"].split("|"), 1)}

    # ----------------------------------------------------------------- #
    # The counting vocabulary, computed off the artifact.
    #   admissible      admissible_in_every_cell, i.e. both tests in all four
    #                   unit x convention cells.
    #   positive        margin > 0 there.
    #   self-contained  not a restatement of a larger positive admissible cell.
    # ----------------------------------------------------------------- #
    head_cells = [r for r in broad if r["unit"] == UNIT and r["convention"] == CONV]
    key = {(r["axis"], r["stratum"]): r for r in head_cells}
    admissible = {k for k, r in key.items() if r["admissible_in_every_cell"] == "True"}
    positive = {k for k in admissible if key[k]["direction"] == "positive"}

    overlaps: dict[tuple[str, str], list[dict]] = {}
    for o in csv.DictReader(OVERLAP.open()):
        a = (o["axis_a"], o["stratum_a"])
        b = (o["axis_b"], o["stratum_b"])
        if int(o["rows_shared"]) <= 0:
            continue
        overlaps.setdefault(a, []).append({"other": b, "rec": o, "flip": False})
        overlaps.setdefault(b, []).append({"other": a, "rec": o, "flip": True})

    # ----------------------------------------------------------------- #
    # ONE ROW SET, ONE INTERVAL.  See the module docstring.  Row-identical
    # strata are pooled; the pool quotes the interval of its coarsest name.
    # ----------------------------------------------------------------- #
    parent: dict[tuple[str, str], tuple[str, str]] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for entries in overlaps.values():
        for e in entries:
            if e["rec"]["relation"] != "identical":
                continue
            a = (e["rec"]["axis_a"], e["rec"]["stratum_a"])
            b = (e["rec"]["axis_b"], e["rec"]["stratum_b"])
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

    def rank(k: tuple[str, str]) -> tuple[int, str]:
        return (AXIS_RANK.get(k[0], len(AXIS_RANK)), k[1])

    pools: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for k in list(parent):
        pools.setdefault(find(k), []).append(k)
    canonical = {k: min(members, key=rank)
                 for members in pools.values() for k in members}

    # ----------------------------------------------------------------- #
    # ONE ROW SET, ONE INTERVAL, AT ONE PRECISION -- AND THE PRECISION IS
    # THE ONE THAT ROW SET'S DRAW COUNT SUPPORTS.
    # `map_ci_precision.json' carries, per row set, the interval, how many
    # decimals it may be printed to, and (where the answer is "neither two
    # nor one") the Monte-Carlo standard deviation to print beside it.  This
    # generator does no rounding of its own: it quotes `printed_as', which
    # the deposit computed from the exact endpoint.  That is also what ends
    # the double rounding the earlier generator did, reading a 3-decimal CSV
    # and rounding it again to two -- which moved the second decimal of three
    # cells away from what the exact value prints.
    # ----------------------------------------------------------------- #
    prec = json.loads(PRECISION.read_text()) if PRECISION.exists() else None
    prec_by_name: dict[tuple[str, str], dict] = {}
    if prec is not None:
        for cell in prec["cells"]:
            for nm in cell["names"]:
                prec_by_name[(nm["axis"], nm["stratum"])] = cell

    def ci_cell(k: tuple[str, str]) -> str:
        """The 90% margin interval this row prints, already formatted.

        Row-identical strata share one interval, because the map drew an
        independent bootstrap per stratum NAME and the spread between those
        draws is Monte-Carlo error, not chemistry.  Which name it is quoted
        under is fixed by position (``AXIS_RANK``), never by the endpoints.
        """
        r = key.get(canonical.get(k, k)) or key[k]
        if r["margin_ci90_lo"] in ("", None):
            return "---"
        cell = prec_by_name.get(k)
        if cell is None:
            raise SystemExit(f"{k} prints an interval that {PRECISION.name} does not cover; "
                             "re-run scripts/analysis/run_b_insuff_map_ci_precision.py")
        iv = cell["interval"]
        lo, hi = iv["printed_as"]
        nd = iv["printed_decimals"]
        out = "$[" + fmt_signed(str(lo), nd).strip("$") + "," + \
              fmt_signed(str(hi), nd).strip("$") + "]"
        if iv["printed_monte_carlo_sd"]:
            out += "^{" + in_last_digit(iv["printed_monte_carlo_sd"], nd) + "}"
        return out + "$"

    def share_of(entry: dict) -> float:
        o = entry["rec"]
        return float(o["shared_share_of_b"] if entry["flip"] else o["shared_share_of_a"])

    def rows_of(entry: dict, other: bool) -> int:
        o = entry["rec"]
        which = ("rows_a" if other else "rows_b") if entry["flip"] else \
                ("rows_b" if other else "rows_a")
        return int(o[which])

    sides = json.loads(SIDES.read_text())["margins_on_each_side_of_the_overlap"]
    complement = {}
    for e in sides:
        a, b = (e["axis_a"], e["stratum_a"]), (e["axis_b"], e["stratum_b"])
        complement[(a, b)] = (e[f"A_minus_B_{CONV}"], e[f"B_minus_A_{CONV}"])
        complement[(b, a)] = (e[f"B_minus_A_{CONV}"], e[f"A_minus_B_{CONV}"])

    def restatement_of(k: tuple[str, str]) -> tuple[str, str] | None:
        """The larger positive admissible cell this one restates, if any.

        A is a restatement of B when B is also positive and admissible, B holds
        more rows, most of A's rows are B's, and A minus B is not admissible --
        so A's positive margin does not stand outside B.
        """
        for entry in overlaps.get(k, []):
            b = entry["other"]
            if b not in positive or b == k:
                continue
            if rows_of(entry, other=True) <= rows_of(entry, other=False):
                continue
            if share_of(entry) <= 0.5:
                continue
            outside = complement.get((k, b), ({}, {}))[0]
            if outside and outside.get("admissible"):
                continue
            return b
        return None

    established = {k for k in positive if restatement_of(k) is None}

    def overlap_flag(k: tuple[str, str], skip: str | None = None) -> str:
        """Which other admissible row sets this row shares rows with, and by how much.

        ``skip`` drops a label the verdict text has already named with its share,
        so the flag never repeats the sentence beside it.
        """
        alias, partial = [], {}
        for entry in overlaps.get(k, []):
            b = entry["other"]
            if b not in admissible or b == k:
                continue
            label = head_label(b[1])
            if label == skip:
                continue
            if entry["rec"]["relation"] == "identical":
                alias.append(label)
            else:
                partial[label] = max(partial.get(label, 0.0), share_of(entry))
        count = {1: "the other", 2: "the two other", 3: "the three other"}
        bits = []
        if alias:
            noun = "cell" if len(alias) == 1 else "cells"
            bits.append(f"the same rows as {count.get(len(alias), len(alias))} "
                        f"{hyphen(alias[0])} {noun}"
                        if len(set(alias)) == 1 else
                        "the same rows as " + ", ".join(sorted(set(alias))))
        for label in sorted(partial, key=lambda s: -partial[s]):
            bits.append(f"${100 * partial[label]:.0f}\\%$ shared with the {label}s")
        return ", ".join(bits)

    def keyed(text: str) -> str:
        for doi, k in sorted(doi_key.items(), key=lambda kv: -len(kv[0])):
            text = text.replace(doi, k)
        return text

    def shorten(r: dict) -> str:
        """What the row is in a position to show, or the test it fails, in words.

        No label: the cell prints the condition itself, so a reader gets the
        reason without a key.  Which of the four sentences is printed is decided
        by the artifact (``admissible_in_every_cell``, ``direction``, and the
        overlap arithmetic above); the wording is the only editorial act.
        """
        k = (r["axis"], r["stratum"])
        if k in admissible:
            skip = None
            if k in established:
                body = ("the closure's own error exceeds the bound on its inputs, and the "
                        "sign holds when any one publication is deleted")
            elif k in positive:
                b = restatement_of(k)
                skip = head_label(b[1])
                shared = max(share_of(e) for e in overlaps[k] if e["other"] == b)
                outside = complement[(k, b)][0]
                body = (f"the sign holds under every deletion, but ${100 * shared:.0f}\\%$ "
                        f"of these rows are the {skip}s' and the ${outside['n']}$ outside "
                        f"give {fmt_signed(str(outside['margin']))}, so this margin does not "
                        f"stand outside the {skip}s: demoted to them by clause~(c)")
            else:
                body = ("the sign holds under every deletion, but the margin is not "
                        "positive, so the two terms are not separated here---a bound from "
                        "above cannot show the inputs are at fault")
            flag = overlap_flag(k, skip)
            return body + ("; " + flag if flag else "")
        reason = keyed(r["reason_not_admissible"])
        parts: list[str] = []
        m = re.search(r"not boundable: n=(\d+) < 40", reason)
        if m:
            parts.append("$n<40$: too few rows for eight bins of five")
            reason = reason[m.end():].lstrip("; ")
        m = re.fullmatch(r"the fixed cell is undefined at n=(\d+)", reason)
        if m:
            parts.append("no estimate at this $n$")
            reason = ""
        m = re.fullmatch(
            r"one source publication \((P\d+)\): leave-one-source-out cannot be run, "
            r"so the sign was never tested", reason)
        if m:
            parts.append(f"one source ({m.group(1)}), so there is no deletion to run "
                         "and the sign was never put at risk")
            reason = ""
        m = re.fullmatch(
            r"(\d+) of (\d+) deletions? leave fewer than 16 rows and the fixed cell is then "
            r"undefined \(([^)]*)\), so the sign is not verifiable", reason)
        if m:
            plural = "" if m.group(2) == "1" else "s"
            parts.append(f"too few rows remain after deleting {m.group(3)} "
                         f"({m.group(1)} of {m.group(2)} deletion{plural}), so the sign "
                         "is untested there")
            reason = ""
        m = re.fullmatch(r"sign does not survive deletion of (.*)", reason)
        if m:
            def _arrow(g: "re.Match[str]") -> str:
                a, b = float(g.group(1)), float(g.group(2))
                return f"takes $ {a:+.3f} \\to {b:+.3f} $"
            body = re.sub(r"\(([-+0-9.]+) -> ([-+0-9.]+)\)", _arrow, m.group(1))
            parts.append("the margin changes sign when one publication is deleted: "
                         + body)
            reason = ""
        m = re.fullmatch(
            r"sign holds, but (\d+) of (\d+) deletions leave n < 40: passes \(b\) and fails "
            r"its strict variant", reason)
        if m:
            parts.append(f"the sign holds, but all {m.group(1)} deletions leave $n<40$")
            reason = ""
        if reason.strip():
            raise SystemExit(f"unrecognised reason for {r['axis']}::{r['stratum']}: {reason!r}")
        if not parts:
            # Passes at the printed cell and not in one of the other three, so the
            # reason has to be fetched from the cell that fails.
            others = [q for q in broad if q["axis"] == r["axis"] and q["stratum"] == r["stratum"]
                      and q["admissible_this_cell"] != "True"]
            if others:
                q = others[0]
                # THE CONVENTION HAS ONE NAME AND IT IS NOT "deployed".  The 2026-08-10
                # one-name-per-thing pass renamed the pair to `residual-only' against `full'
                # and grounding_paradox.tex:84 forbids the old word in printed text.  That
                # rename had been applied BY HAND to this script's generated output, so the
                # first regeneration silently put "deployed convention" back into the SI.
                # A prohibition that lives in the output of a generator is not enforced.
                parts.append(f"passes here and fails at the {q['unit']} unit "
                             f"({'residual-only' if q['convention'] == 'res' else 'full'} "
                             "convention), " + shorten_cell(q))
            else:
                parts.append("passes here, not in all four cells")
        return "; ".join(parts)

    def shorten_cell(q: dict) -> str:
        reason = keyed(q["reason_not_admissible"])
        m = re.fullmatch(r"sign does not survive deletion of (\S+) \(([-+0-9.]+) -> ([-+0-9.]+)\)",
                         reason)
        if m:
            return (f"where deleting {m.group(1)} takes "
                    f"$ {float(m.group(2)):+.3f} \\to {float(m.group(3)):+.3f} $")
        return reason

    # The WHOLE tabular is generated, not just its rows: TeX cannot start an alignment cell with
    # \input, so a body-only file breaks with "Misplaced \omit" on the first \multicolumn.
    def write_map(path: Path, axes: list[tuple[str, str]],
                  only_boundable: bool = False) -> None:
        lines: list[str] = []
        lines.append("% GENERATED by scripts/analysis/make_map_table_tex.py from")
        lines.append("% results/b_insuff/admissibility_table.csv. Do not edit; re-run the script.")
        # 0.14 + 0.355 (was 0.15 + 0.38): at the wider pair the tabular ran 13.2 pt past
        # \textwidth in a table*, which prints as an overhang into the margin.
        # The stated intervals carry a superscript, and three of the four map tabulars then ran
        # 8.7-16.6pt past the text block.  The width was bought back from \tabcolsep in the
        # floats (3pt -> 2pt, 18 gaps) and not from these two columns, because narrowing the
        # reason column wraps its prose and the float that carries it is already at the page
        # height: at 0.335 the tabular fitted and the float was 25.6pt too tall.
        lines.append(r"\begin{tabular}{@{}L{0.14\linewidth}rrlrlrcL{0.355\linewidth}@{}}")
        lines.append(r"\toprule")
        lines.append(r"Stratum & $n$ & pairs & sources\tnk{a} & margin & $90\%$ margin\tnk{b} "
                     r"& full & cells\tnk{c} & what it shows, or the test it fails\tnk{d} \\")
        lines.append(r"\midrule")
        n_printed = 0
        for axis, heading in axes:
            sel = [r for r in broad if r["axis"] == axis and r["unit"] == UNIT
                   and r["convention"] == "res"]
            if only_boundable:
                sel = [r for r in sel if r["test_a_boundable"] == "True"]
            if not sel:
                continue
            sel.sort(key=lambda r: -int(r["n"]))
            if not lines[-1].startswith(r"\midrule"):
                lines.append("\\addlinespace[1.5pt]")
            lines.append(f"\\multicolumn{{9}}{{@{{}}l@{{}}}}{{\\emph{{{heading}}}}}\\\\")
            for r in sel:
                full = [q for q in broad if q["axis"] == axis and q["stratum"] == r["stratum"]
                        and q["unit"] == UNIT and q["convention"] == "full"][0]
                share = r["top_source_share_of_stratum_squared_error"]
                src = (f"{r['n_sources']} ({doi_key[r['top_source']]}, "
                       f"{float(share):.2f})") if r["n_sources"] != "0" else "---"
                lines.append(
                    f"{pretty(r['stratum'])} & ${r['n']}$ & ${r['n_pairs']}$ & {src} & "
                    f"{fmt_signed(r['margin'])} & "
                    f"{ci_cell((axis, r['stratum']))} & "
                    f"{fmt_signed(full['margin'])} & ${r['cells_admissible']}$ & "
                    f"{shorten(r)} \\\\")
                n_printed += 1
        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        path.write_text("\n".join(lines) + "\n")
        print(f"wrote {path} ({len(lines)} lines, {n_printed} strata)")

    # The article's map: every stratum the fixed estimator can bound, on both axes and at
    # every granularity.  A stratum below n=40 has no margin the rule can act on, so the
    # article loses no separation by carrying these fifteen and no others; the 44 it does
    # not carry are in the two SI halves, each with the test it fails.
    # SPLIT BY AXIS, as the SI's halves are, and for the same reason: at fifteen rows plus the
    # source key one float is ~70 pt too tall for the page and silently runs into the folio,
    # while two half-page floats place.  The split is the axis boundary, not a selection.
    write_map(OUT_ARTICLE, SOLVENT_AXES, only_boundable=True)
    write_map(OUT_ARTICLE_B, SOLUTE_AXES, only_boundable=True)
    for axes, name in SI_GROUPS:
        write_map(ROOT / "paper" / "si_tables" / name, axes)

    # The P1..P15 key, written once and \input by the article's table note.  The SI's halves
    # point at that note rather than repeating fifteen DOIs in a second document.
    KEY.write_text(
        "% GENERATED by scripts/analysis/make_map_table_tex.py. Do not edit; re-run the script.\n"
        + ",\n".join(f"{k}~\\texttt{{{doi}}}" for doi, k in
                     sorted(doi_key.items(), key=lambda kv: int(kv[1][1:])))
        + ".\n")
    print(f"wrote {KEY} ({len(doi_key)} sources)")

    # ------------------------------------------------------------------------------------- #
    # The interval note, GENERATED.  It states what each interval's precision is and why, and
    # every number in it is read out of the precision deposit -- including the counts, which is
    # the point: the sentence it replaces ("each endpoint carries +-0.02 of Monte-Carlo spread")
    # was one cell's number generalised by hand to eleven, and 22 of the 48 endpoints exceed it.
    # ------------------------------------------------------------------------------------- #
    if prec is not None:
        v = {k: 0 for k in ("converged", "coarsened", "stated", "degenerate")}
        for c in prec["cells"]:
            v[c["verdict"]] += 1
        cnt = prec["counts"]
        gly = next(c for c in prec["cells"] if c["canonical_stratum"] == "glycol_ether")
        atoms = max(c["monte_carlo_at_the_maps_own_draws"]["distinct_resampled_margins_median"]
                    for c in prec["cells"] if c["verdict"] == "degenerate")
        got_seeds = {c["monte_carlo_at_the_maps_own_draws"]["n_seeds"] for c in prec["cells"]}
        if got_seeds != {MC_SEEDS_NOTE}:
            raise SystemExit(f"the note says {MC_SEEDS_NOTE} seeds; the deposit has {got_seeds}")
        if prec["estimator_cell"]["map_draw_count"] != MC_DRAWS_NOTE:
            raise SystemExit(f"the note says {MC_DRAWS_NOTE} draws; the deposit has "
                             f"{prec['estimator_cell']['map_draw_count']}")
        # The map's own row-set arithmetic, over ALL its strata and not only the ones that draw
        # an interval, read out of the columns run_b_insuff_stratified_map now deposits.
        seen: dict[str, int] = {}
        for r in head_cells:
            if r.get("row_set_id"):
                seen[r["row_set_id"]] = int(r["row_set_n_names"])
        n_multi = sum(1 for x in seen.values() if x > 1)
        n_dup = sum(x - 1 for x in seen.values() if x > 1)
        # Per ENDPOINT, not per cell: the smallest spread in the map is one endpoint of the
        # ester cell, and taking the larger of a cell's two would hide it.
        sds = [c["monte_carlo_at_the_maps_own_draws"][k]
               for c in prec["cells"] if c["verdict"] != "degenerate"
               for k in ("lo_sd", "hi_sd")]
        # pretty(), not head_label(): the second degenerate cell is the halogenated solvents
        # WITH WATER AS SOLUTE, and the map also carries a halogenated cell that is not
        # degenerate, so the short label would name the wrong rows.
        degen = "; ".join(pretty(c["canonical_stratum"])
                          for c in prec["cells"] if c["verdict"] == "degenerate")
        # THE FOUR-STANDARD-ERROR PROPERTY BELONGS TO 11 OF THE 24 CELLS AND TO NO OTHERS, and
        # the first version of this note asserted it of all of them.  It read "Each prints at the
        # precision its own draw count determines---both endpoints four Monte-Carlo standard
        # errors clear of the nearest rounding boundary", which is false for the 11 `stated' cells
        # (their margins run 0.03 to 11.44 se) and undefined for the 2 degenerate ones.  It was
        # written to abolish a blanket precision claim generalised from one cell and it made a
        # blanket precision claim of its own; worse, the ARTICLE's version of the same sentence
        # carried the exception list, so the paper was honest in one document and blanket in the
        # other.  The `stated' cells are the ones where NO precision this table can print is
        # determined, and their superscript is a warning rather than a refinement.  Say that.
        converged = [c for c in prec["cells"] if c["verdict"] == "converged"]
        conv_names = "; ".join(pretty(c["canonical_stratum"]) for c in converged)
        note = (
            "Two-way solute\\,$\\times$\\,solvent cluster bootstrap, $5$th and $95$th "
            "percentiles. Row-identical strata are one row set: drawn once and printed once, "
            "under the row set's first name above and restated under the rest "
            f"({n_multi} of {len(seen)} row sets, {n_dup} rows). Each prints at the precision its "
            f"own draw count supports, decided cell by cell over ${MC_SEEDS_NOTE}$ seeds and "
            f"verified on the run that bought it. {v['converged']} carry two decimals "
            f"({conv_names}, the latter at ${gly['n_draws'] / 1e8:.1f}\\times10^{{8}}$ draws) and "
            f"{v['coarsened']} carry one, both endpoints of each standing four Monte-Carlo "
            f"standard errors clear of the nearest rounding boundary at that precision. For "
            f"{v['stated']} no precision this table can print is determined: those carry two "
            "decimals with a superscript giving their endpoints' Monte-Carlo standard deviation "
            "in units of that last digit, and the superscript is the warning rather than a "
            f"refinement. A further {v['degenerate']} ({degen}) no seed moves at all---each has "
            "one cluster on one of its two axes, so the resample is one-way over three clusters "
            f"and about {atoms} distinct compositions exist: a bootstrap with nothing left to "
            # NO FILESYSTEM PATH IN PRINTED TEXT.  This note carried
            # \texttt{results/b_insuff/map_ci_precision.json} for one draft and was the only
            # printed path in either document; every other deposit in the paper is named in
            # prose ("the deposited per-cell record", "Data Set S1").  The path belongs in this
            # generator's header comment, which is where a reader who wants the file will be.
            "resample, not a converged one. The per-cell verdict, its draw count and its cost at "
            "either precision are on the deposited record (\\S\\ref{sec:si-map}).")
        CI_NOTE.write_text(
            "% GENERATED by scripts/analysis/make_map_table_tex.py from\n"
            "% results/b_insuff/map_ci_precision.json. Do not edit; re-run the script.\n"
            + note + "\n")
        print(f"wrote {CI_NOTE} ({v})")

        # The class statement, in the section body rather than in a table note, because it is
        # about the apparatus and not about one float.  Generated for the same reason: the
        # sentence it replaces generalised one cell's spread to eleven by hand.
        redraws = [c.get("n_draws") or c["interval"]["n_draws"] for c in prec["cells"]]
        redraw_lo, redraw_hi = min(redraws) / 1e5, max(redraws) / 1e8
        body = (
            # THE PRINTED COLUMN IS NO LONGER THE 3000-DRAW OUTPUT and this sentence used to open
            # "The bootstrap draws 3000 resamples per row set", present tense, three lines above a
            # table whose 11 `stated' cells now print second decimals the 3000-draw run did not
            # give (mono-alcohol solvent [+0.18,+3.24] -> [+0.28,+3.32] and nine more).  A reader
            # was told the count that was AUDITED and shown the intervals of a different run.
            f"The map's own bootstrap draws {MC_DRAWS_NOTE} resamples per row set, which does not determine "
            # `sds' excludes the degenerate cells, whose endpoints no seed moves; quoting a
            # floor of 0 would read as convergence where it is a resample with nothing left in
            # it, so the sentence has to say which endpoints the range is over.
            f"a second decimal: over ${MC_SEEDS_NOTE}$ seeds the Monte-Carlo spread of an endpoint "
            f"any seed moves runs ${min(sds):.4f}$ to ${max(sds):.3f}$, and "
            f"{cnt['of_those_unsupported_at_two_decimals']} of the "
            f"{cnt['endpoints_off_the_3000_draw_apparatus']} endpoints drawn at that count stand "
            "inside four Monte-Carlo standard errors of the rounding boundary their second decimal "
            f"turns on---the closest reaching {cnt['largest_clearance_of_any_movable_endpoint_in_sd']}"
            f" and the median {cnt['median_clearance_of_a_movable_endpoint_in_sd']} of the four "
            f"required. The interval column of Tables~\\ref{{tab:map-full}} to~\\ref{{tab:map-xtab}} "
            "is therefore not that output: every row set was re-drawn at a count chosen from its "
            f"own Monte-Carlo error---${redraw_lo:.1f}\\times10^{{5}}$ to "
            f"${redraw_hi:.1f}\\times10^{{8}}$ draws---and prints at the precision that count "
            "supports, cell by cell. Note~\\emph{b} of Table~\\ref{tab:map-full} gives the rule "
            "and the count at each precision.")
        CI_BODY.write_text(
            "% GENERATED by scripts/analysis/make_map_table_tex.py from\n"
            "% results/b_insuff/map_ci_precision.json. Do not edit; re-run the script.\n"
            + body + "\n")
        print(f"wrote {CI_BODY}")

    # The companion body: the columns the main text's map does not carry, for the same 59 strata.
    det: list[str] = []
    det.append("% GENERATED by scripts/analysis/make_map_table_tex.py from")
    det.append("% results/b_insuff/admissibility_table.csv. Do not edit by hand; re-run the script.")
    det.append(r"\begin{tabular}{@{}lrrrlrl@{}}")
    det.append(r"\toprule")
    det.append(r"Stratum & $n$ & $\mathrm{MSE}$ & $\Binsuf^{\mathrm{up}}$\tnk{a} & $P$\tnk{b} & "
               r"share\tnk{c} & leave-one-source-out\tnk{d} \\")
    det.append(r"\midrule")
    for axis, heading in AXES:
        sel = [r for r in broad if r["axis"] == axis and r["unit"] == UNIT
               and r["convention"] == "res"]
        if not sel:
            continue
        sel.sort(key=lambda r: -int(r["n"]))
        if not det[-1].startswith("%"):
            det.append("\\addlinespace[1.5pt]")
        det.append(f"\\multicolumn{{7}}{{@{{}}l@{{}}}}{{\\emph{{{heading}}}}}\\\\")
        for r in sel:
            def num(key: str, nd: int = 3) -> str:
                return "---" if r[key] in ("", None) else "$" + _round(float(r[key]), nd) + "$"
            runnable = int(r["loso_n_deletions"]) - int(r["loso_n_undefined"])
            if runnable <= 0 or r["loso_margin_min"] == "":
                loso = "none possible"
            elif runnable == 1:
                loso = fmt_signed(r["loso_margin_min"]) + " (one deletion)"
            else:
                loso = (fmt_ci(r["loso_margin_min"], r["loso_margin_max"])
                        + f" ({runnable})")
            det.append(
                f"{pretty(r['stratum'])} & ${r['n']}$ & {num('mse')} & {num('b_insuff_up')} & "
                f"{band(r['P_boot'])} & "
                f"${100 * float(r['share_of_squared_error']):.1f}\\%$ & {loso} \\\\")
    det.append(r"\bottomrule")
    det.append(r"\end{tabular}")
    DETAIL.write_text("\n".join(det) + "\n")
    print(f"wrote {DETAIL} ({len(det)} lines)")


if __name__ == "__main__":
    main()
