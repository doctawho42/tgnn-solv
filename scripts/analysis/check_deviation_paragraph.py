#!/usr/bin/env python
"""Bind the numerals of Sec. 3.2.1's `Deviation from the declaration` to their deposits.

WHY THIS PARAGRAPH GETS ITS OWN GATE.  It is the manuscript's most contested block -- a documented
departure from a hashed pre-declaration -- and it is the one a referee will read hardest.  It is
also running prose, which is where all eight of this manuscript's stale or crossed values were
found, and restructuring it already turned up a ninth: an R^2 attributed to "the matched set" that
belongs to the glycol-ether stratum itself.

WHAT IS BOUND, and to what
--------------------------
  results/b_insuff/crossfit_map.json
      B_insuff^cf and MSE on the glycol stratum, its out-of-fold R^2 and its cross-fitted margin;
      the range of the violation across every source-folded cell, forest and ridge separately
  the SI's own cross-fit subsection
      the two null frequencies and the two certifying-draw percentages, which moved into the
      article so that "the null moves the wrong way" stops being a phrase and becomes a number

NOT BOUND: the +1.76 [+1.02,+2.49] glycol margin under the cross-fit, which
run_glycol_oos_margin.py's sibling gate already covers where it is printed elsewhere.  This file
asserts only what it names.

Usage
-----
    python scripts/analysis/check_deviation_paragraph.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "paper/grounding_paradox.tex"
CROSSFIT = ROOT / "results/b_insuff/crossfit_map.json"
BROAD = ROOT / "paper/si_tables/broad_idac_set_477.csv"
#: the glycol stratum's shape, which is how its cells are identified in the map
GLYCOL = {"n": 182, "n_solutes": 19, "n_solvents": 4}


def glycol_cells(blob: dict) -> list[dict]:
    out: list[dict] = []

    def walk(node):
        if isinstance(node, dict):
            if all(node.get(k) == v for k, v in GLYCOL.items()) and "b_insuff_cf" in node:
                out.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(blob.get("cells", {}))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--article", type=Path, default=ARTICLE)
    a = ap.parse_args()

    blob = json.loads(CROSSFIT.read_text())
    cells = glycol_cells(blob)
    if not cells:
        raise SystemExit("no glycol-ether cell found in the crossfit map; the deposit moved")
    # THE CELL MUST BE NAMED, NOT GUESSED.  The first version picked "the cell whose binning margin
    # is the published +2.036", which selects a PAIR-folded cell (valid, +1.76) where the paragraph
    # is talking about the SOURCE-folded one (invalid, -7.58).  Both are glycol.  This gate exists
    # because that is the defect class, so it may not commit it: the cell is source-folded, random
    # forest, row unit, residual-only -- the paper's own convention on the declaration's own folds.
    named = [c for c in cells if c.get("fold_scheme") == "source" and c.get("model") == "rf"
             and c.get("unit") == "row" and c.get("convention") == "res"]
    if not named:
        raise SystemExit("no source-folded rf/row/res glycol cell in the deposit")
    head = named[0]

    d = pd.read_csv(BROAD)
    mse_set = float(np.mean((d.m_ln_gamma_inf - d.g_2002_res) ** 2))
    src = {k: v for k, v in blob["oof_summary"].items() if "source" in k}
    rf = [v["b_insuff_cf"] / mse_set for k, v in src.items() if k.endswith("rf")]
    ridge = [np.log10(v["b_insuff_cf"] / mse_set) for k, v in src.items() if k.endswith("ridge")]

    want = {
        "B_insuff^cf on the stratum": f"{head['b_insuff_cf']:.2f}",
        "the stratum's own MSE": f"{head['mse']:.2f}",
        "its out-of-fold R^2": f"{head['oof_r2']:.2f}",
        "violation range, low": f"{min(rf):.1f}",
        "violation range, high": f"{max(rf):.1f}",
        "the cross-fitted margin there": f"{head['margin_cf']:.2f}",
    }

    tex = a.article.read_text()
    m = re.search(
        r"the estimator returns \$\\Binsuf=([\d.]+)\$ against that stratum's own \$\\mathrm\{MSE\}\$ "
        r"of \$([\d.]+)\$,\s+twice what the decomposition allows, at \$R\^2=(-[\d.]+)\$ out of fold\. "
        r"Across the source-folded cells the\s+same violation runs from \$([\d.]+)\$ to \$([\d.]+)\$ "
        r"times \$\\mathrm\{MSE\}\$.*?so the \$(-[\d.]+)\$ it prints here", tex, re.S)
    if m is None:
        raise SystemExit("the deviation paragraph is not in the article in the form this gate "
                         "reads; it was reworded or removed")

    bad = 0
    print("deviation paragraph, bound to results/b_insuff/crossfit_map.json:")
    for (label, truth), got in zip(want.items(), m.groups()):
        ok = got == truth
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:32s} paper {got:>8s}   deposit {truth:>8s}")

    # the ridge order of magnitude is stated in words, so it is checked as a floor
    floor = int(min(ridge))
    print(f"  {'ok  ' if floor == 27 else 'FAIL'}  {'ridge, orders of magnitude':32s} "
          f"paper twenty-seven   deposit {floor}")
    bad += floor != 27

    # and the two null frequencies the article now carries
    # Split into two periods by the 2026-08-19 readability pass; the gate reported it reworded,
    # which is what it is for.  The four numerals and their order are unchanged.
    n = re.search(r"moves from \$([\d.]+)\$ to \$([\d.]+)\$\. Conditioned on drawing a map that "
                  r"certifies anything at all, a\s+relabelling reaches the observed maximum in "
                  r"\$(\d+)\\%\$ of draws against \$(\d+)\\%\$", tex)
    si = (ROOT / "paper/sections/crossfit-negative.tex").read_text()
    s = re.search(r"moves the wrong way, \$([\d.]+)\\to([\d.]+)\$;.*?in \$(\d+)\\%\$ of draws\s+"
                  r"against \$(\d+)\\%\$", si, re.S)
    if n and s:
        for label, got, truth in zip(("null p, binning", "null p, cross-fit",
                                      "certifying draws, cross-fit", "certifying draws, binning"),
                                     n.groups(), s.groups()):
            ok = got == truth
            bad += not ok
            print(f"  {'ok  ' if ok else 'FAIL'}  {label:32s} paper {got:>8s}   SI {truth:>8s}")
    else:
        print("  FAIL  the null sentence does not match between the article and the SI")
        bad += 1

    print(f"\n{len(want) + 5} numerals bound, {bad} mismatched")
    if bad:
        raise SystemExit("the deviation paragraph and its deposits disagree")


if __name__ == "__main__":
    main()
