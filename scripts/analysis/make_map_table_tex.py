#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit the main text's map table body from the deposited admissibility table.

The map is the instrument's declared output, so it prints in the main text and
every one of its cells has to come out of the artifact rather than out of a
typist.  This script writes the ``tabular`` body of Table~\\ref{tab:map} --- one
row per stratum of the broad IDAC set, at the headline estimator cell (eight
equal-count bins of g(z*), Bessel within-bin variance, row unit, deployed
residual-only convention) --- into

    paper/si_tables/stratified_map_rows.tex

which the manuscript ``\\input``s.  Nothing here is hard-coded: n, pair counts,
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

THE VERDICT COLUMN HAS THREE VALUES, NOT TWO
--------------------------------------------
Until 2026-08-02 this script printed ``established`` for every row that was
admissible in all four cells with a positive margin, which is FOUR rows -- the
glycol ethers at three granularities and the alkane solutes -- while every prose
statement in the manuscript says one stratum is established.  Both counts were
true of different things and the one word carried them both.  The vocabulary is
now fixed and the column prints three values:

    established              admissible in all four cells, margin positive, and
                             SELF-CONTAINED (below).  One row set: the glycol
                             ethers, at each of the three granularities it
                             appears at.
    admissible, not          admissible in all four cells, but either the margin
    established              is not positive (a one-sided bound certifies
                             nothing) or the row set is a restatement of a
                             larger admissible one.
    (a reason)               not admissible: the reason it fails (a) or (b).

SELF-CONTAINED is computed, not asserted.  A positive admissible cell A is a
restatement when some other positive admissible cell B holds more rows than A,
more than half of A's rows are B's, and A-minus-B is not itself admissible --
i.e. A's margin does not stand outside B.  That is exactly the manuscript's
argument for demoting the alkane solutes, and both inputs come from the
artifact: ``stratum_overlap.csv`` for the shared-row counts and
``admissibility.json``'s ``margins_on_each_side_of_the_overlap`` for the
complement.  Nothing about which stratum wins is written into this file.

Every admissible row additionally carries an OVERLAP FLAG naming the other
admissible row sets it shares rows with and by how much, so a reader of the map
alone cannot count one row set twice across the two axes.

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
OUT = ROOT / "paper" / "si_tables" / "stratified_map_rows.tex"
OUT_SOLUTE = ROOT / "paper" / "si_tables" / "stratified_map_rows_solute.tex"
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
        """The artifact's reason, in the same content and fewer words."""
        k = (r["axis"], r["stratum"])
        if k in admissible:
            skip = None
            if k in established:
                body = "\\textbf{established}"
            elif k in positive:
                b = restatement_of(k)
                skip = head_label(b[1])
                shared = max(share_of(e) for e in overlaps[k] if e["other"] == b)
                outside = complement[(k, b)][0]
                body = (f"admissible, not established: ${100 * shared:.0f}\\%$ of these "
                        f"rows are the {skip}s' and the ${outside['n']}$ outside give "
                        f"{fmt_signed(str(outside['margin']))}, so this is that finding "
                        "restated")
            else:
                body = ("admissible, not established: margin not positive, so "
                        "nothing is certified")
            flag = overlap_flag(k, skip)
            return body + ("; " + flag if flag else "")
        reason = keyed(r["reason_not_admissible"])
        parts: list[str] = []
        m = re.search(r"not boundable: n=(\d+) < 40", reason)
        if m:
            parts.append("$n<40$")
            reason = reason[m.end():].lstrip("; ")
        m = re.fullmatch(r"the fixed cell is undefined at n=(\d+)", reason)
        if m:
            parts.append("no estimate at this $n$")
            reason = ""
        m = re.fullmatch(
            r"one source publication \((P\d+)\): leave-one-source-out cannot be run, "
            r"so the sign was never tested", reason)
        if m:
            parts.append(f"one source ({m.group(1)}), so no deletion to run")
            reason = ""
        m = re.fullmatch(
            r"(\d+) of (\d+) deletions? leave fewer than 16 rows and the fixed cell is then "
            r"undefined \(([^)]*)\), so the sign is not verifiable", reason)
        if m:
            parts.append(f"{m.group(1)} of {m.group(2)} deletions undefined "
                         f"({m.group(3).replace(', ', ', ')})")
            reason = ""
        m = re.fullmatch(r"sign does not survive deletion of (.*)", reason)
        if m:
            def _arrow(g: "re.Match[str]") -> str:
                a, b = float(g.group(1)), float(g.group(2))
                return f"($ {a:+.3f} \\to {b:+.3f} $)"
            body = re.sub(r"\(([-+0-9.]+) -> ([-+0-9.]+)\)", _arrow, m.group(1))
            parts.append("sign flips on deleting " + body)
            reason = ""
        m = re.fullmatch(
            r"sign holds, but (\d+) of (\d+) deletions leave n < 40: passes \(b\) and fails "
            r"its strict variant", reason)
        if m:
            parts.append(f"sign holds, but all {m.group(1)} deletions leave $n<40$")
            reason = ""
        if reason.strip():
            raise SystemExit(f"unrecognised reason for {r['axis']}::{r['stratum']}: {reason!r}")
        if not parts:
            # Admissible at the printed cell and not in one of the other three, so the
            # reason has to be fetched from the cell that fails.
            others = [q for q in broad if q["axis"] == r["axis"] and q["stratum"] == r["stratum"]
                      and q["admissible_this_cell"] != "True"]
            if others:
                q = others[0]
                parts.append(f"admissible here; fails at the {q['unit']} unit "
                             f"({'deployed' if q['convention'] == 'res' else 'full'} convention), "
                             + shorten_cell(q))
            else:
                parts.append("admissible here, not in every cell")
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
    def write_map(path: Path, axes: list[tuple[str, str]]) -> None:
        lines: list[str] = []
        lines.append("% GENERATED by scripts/analysis/make_map_table_tex.py from")
        lines.append("% results/b_insuff/admissibility_table.csv. Do not edit; re-run the script.")
        lines.append(r"\begin{tabular}{@{}L{0.15\linewidth}rrlrlrcL{0.38\linewidth}@{}}")
        lines.append(r"\toprule")
        lines.append(r"Stratum & $n$ & pairs & sources\tnk{a} & margin & $90\%$ margin\tnk{b} "
                     r"& full & cells\tnk{c} & verdict\tnk{d} \\")
        lines.append(r"\midrule")
        for axis, heading in axes:
            sel = [r for r in broad if r["axis"] == axis and r["unit"] == UNIT
                   and r["convention"] == "res"]
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
                    f"{fmt_ci(r['margin_ci90_lo'], r['margin_ci90_hi'])} & "
                    f"{fmt_signed(full['margin'])} & ${r['cells_admissible']}$ & "
                    f"{shorten(r)} \\\\")
        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        path.write_text("\n".join(lines) + "\n")
        print(f"wrote {path} ({len(lines)} lines)")

    write_map(OUT, SOLVENT_AXES)
    write_map(OUT_SOLUTE, SOLUTE_AXES)

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
