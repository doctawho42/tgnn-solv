#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit the out-of-sample descriptive map as a table body for the SI.

WHY THIS EXISTS
---------------
The pre-declared out-of-sample test (``run_glycol_ether_out_of_sample.py``)
returned NOT TESTABLE, and its declaration item 7 also asked for a DESCRIPTIVE
companion: the same estimator cell over every solvent class of the PGL
6th-edition set.  That companion was deposited in the artifact but reported in
prose only in part -- the article named the three largest positive classes and
not the negative ones, and neither document said which of the classes the
manuscript's own admissibility rule admits.  A ranking quoted in part is a
different statement from the ranking, so the whole of it now prints, in the same
format as the in-sample map tables (Tables S9-S13).

Round 3, referee 3, must-fix: "Deposit the full nine-class descriptive table
(class, n, margin, interval, boundable, deletions runnable, verdict) in the SI
beside the pre-declaration, in the same format as Tables S9-S13, so the
out-of-sample map is inspectable on the same terms as the in-sample one."

WHERE EACH NUMBER COMES FROM
----------------------------
n, pairs, sources, margin, interval, boundability and admissibility are read
from ``results/b_insuff/glycol_ether_out_of_sample.json``, which is the
deposited artifact of the pre-declared run and is not recomputed here.

The one column the artifact does not carry is how many of each stratum's
leave-one-source-out deletions can be RUN -- the run pops the curve before
writing the JSON and keeps only the verdict sentence.  That column is
recomputed here from the same scored records through the same ``load_pgl`` and
the same ``loso`` the run used, so the labels and the 16-row cutoff are the
run's own rather than a re-derivation.  The recomputed reason string is checked
against the artifact's for every stratum and the script raises on any
disagreement, so this file cannot drift from the deposit.

    python scripts/analysis/make_oos_map_table_tex.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from run_glycol_ether_out_of_sample import load_pgl, loso  # noqa: E402

SRC = ROOT / "results" / "b_insuff" / "glycol_ether_out_of_sample.json"
OUT = ROOT / "paper" / "si_tables" / "oos_descriptive_rows.tex"

PRETTY = {
    "aliphatic_hydrocarbon": "aliphatic hydrocarbon",
    "aprotic_acceptor": "aprotic acceptor",
    "aromatic_hydrocarbon": "aromatic hydrocarbon",
    "aryl_ether": "aryl ether",
    "glycol_ether": "glycol ether",
    "halogenated": "halogenated",
    "mono_alcohol": "mono-alcohol",
    "nh_protic": "N--H protic",
    "unclassified": "unclassified",
    "water": "water",
}

# The source labels the declared provenance axis produces, shortened for a narrow column.
# The axis is the record file, refined by the compilation label inside the two Jaubert/TDE
# files; the Lazzaroni file carries no label and stays one source.
SHORT = {
    "Jaubert_TDE_water_in_organic:J": "WinOrg:J",
    "Jaubert_TDE_water_in_organic:T": "WinOrg:T",
    "Jaubert_TDE_water_in_organic:Y": "WinOrg:Y",
    "Jaubert_TDE_organic_in_water:J": "OrgInW:J",
    "Jaubert_TDE_organic_in_water:T": "OrgInW:T",
    "Jaubert_TDE_organic_in_water:Y": "OrgInW:Y",
    "LazzaroniDb2023": "Lazzaroni",
}


def shorten(label: str) -> str:
    return SHORT.get(label, label.replace("_", " "))


def fmt(x: float | None, places: int = 2) -> str:
    if x is None:
        return "---"
    return f"${x:+.{places}f}$"


def interval(ci: list[float] | None) -> str:
    if ci is None:
        return "---"
    return f"$[{ci[0]:+.2f},{ci[1]:+.2f}]$"


def reason_sentence(rec: dict, curve: list[dict]) -> str:
    """The condition the row is in, in the table's own words, from the artifact's reason."""
    why = rec["reason_not_admissible"]
    if rec["admissible"]:
        head = "boundable, and the sign holds when any one source is deleted, so the rule admits it"
        if rec["margin"] is not None and rec["margin"] > 0:
            if rec["margin_ci90"] is not None and rec["margin_ci90"][0] > 0:
                return f"{head}; the closure's own error exceeds the bound on its inputs here"
            return (f"{head}; the margin is positive but its interval covers zero, so nothing is "
                    "separated at this cell")
        return (f"{head}; the margin is not positive, so the two terms are not separated here---a "
                "bound from above cannot show the inputs are at fault")
    if why.startswith("the fixed cell is undefined"):
        return f"the fixed cell is undefined at $n={rec['n']}$: no estimate"
    if why.startswith("not boundable"):
        return f"$n={rec['n']}<40$: too few rows for eight bins of five"
    if "deletions leave fewer than" in why:
        bad = [shorten(c["left_out"]) for c in curve if c["margin"] is None]
        return (f"{len(bad)} of {len(curve)} deletions leave fewer than $16$ rows and the fixed "
                f"cell is then undefined ({', '.join(bad)}), so the sign is not verifiable")
    if why.startswith("sign does not survive"):
        base = rec["margin"]
        sgn = 1.0 if base > 0 else -1.0
        flips = [c for c in curve if c["margin"] is not None and c["margin"] * sgn <= 0]
        parts = "; ".join(f"{shorten(c['left_out'])} takes ${base:+.3f} \\to {c['margin']:+.3f}$"
                          for c in flips)
        return f"the margin changes sign when one source is deleted: {parts}"
    raise SystemExit(f"unrecognised reason string, refusing to guess: {why!r}")


def main() -> None:
    art = json.loads(SRC.read_text())
    strata = art["descriptive_solvent_class_map"]["strata"]

    d = load_pgl()
    rows = []
    for rec in sorted(strata, key=lambda r: -(r["margin"] if r["margin"] is not None else -1e9)):
        lab = rec["stratum"]
        sub = d[d["solvent_class"] == lab]
        curve, ok_b, why_b = loso(sub, "g_res", rec["margin"])
        # The deposit is the authority; this file may not disagree with it.
        if bool(rec["admissible"]) != bool(rec["boundable_at_headline_cell"] and ok_b):
            raise SystemExit(f"{lab}: admissibility disagrees with the deposited artifact")
        if not rec["admissible"] and why_b != rec["reason_not_admissible"]:
            raise SystemExit(f"{lab}: reason disagrees with the deposited artifact\n"
                             f"  artifact:   {rec['reason_not_admissible']}\n"
                             f"  recomputed: {why_b}")
        if int(len(curve)) != int(rec["n_sources"]):
            raise SystemExit(f"{lab}: source count disagrees with the deposited artifact")
        runnable = sum(1 for c in curve if c["margin"] is not None)
        rows.append(
            f"{PRETTY.get(lab, lab)} & ${rec['n']}$ & ${rec['n_pairs']}$ & ${rec['n_sources']}$ & "
            f"{fmt(rec['margin'])} & {interval(rec['margin_ci90'])} & "
            f"{'yes' if rec['boundable_at_headline_cell'] else 'no'} & "
            f"${runnable}/{len(curve)}$ & "
            f"{'yes' if rec['admissible'] else 'no'} & {reason_sentence(rec, curve)} \\\\"
        )

    lines = [
        "% GENERATED by scripts/analysis/make_oos_map_table_tex.py from",
        "% results/b_insuff/glycol_ether_out_of_sample.json. Do not edit; re-run the script.",
        r"\begin{tabular}{@{}L{0.11\linewidth}rrrrlccc"
        r"L{0.263\linewidth}@{}}",
        r"\toprule",
        r"Solvent class & $n$ & pairs & sources\tnk{a} & margin & $90\%$ margin\tnk{b} & "
        r"bound\-able\tnk{c} & dele\-tions\tnk{d} & admis\-sible & "
        r"what it shows, or the test it fails \\",
        r"\midrule",
        *rows,
        r"\bottomrule",
        r"\end{tabular}",
    ]
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} ({len(rows)} strata)")


if __name__ == "__main__":
    main()
