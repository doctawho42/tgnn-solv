#!/usr/bin/env python
"""Bind Sec. 3.3's donor-window numerals -- caption and running prose -- to the deposit they claim.

WHY THIS EXISTS.  check_hand_transcribed_displays.py binds the floats and the abstract of the
re-run family, and it is the reason six values in this manuscript were caught stale.  It cannot
reach these: the donor-window numbers come off results/closure_ladder/placebo_profile_diagnosis.csv,
a retired run outside every tree that checker knows, so they sit in exactly the position the six
stale values sat in -- a numeral in running prose with no producer between it and the artifact.
Figure~\\ref{fig:donor-window} put more of them on the page, so they get a gate.

WHAT IS BOUND.  Every numeral in Sec. 3.3 that this deposit determines:

  the four molecule-matched areas       cyclohexane, acetone, toluene, tetrahydrofuran
  their reference areas being zero      the claim is "exactly zero", not "small"
  the fraction range the prose quotes   min and max over those same four
  acetonitrile's reference area         the 6.71 that stands above ethanol's 6.20
  the figure's solvent count            sixteen drawn
  the figure's empty-reference count    twelve of the sixteen

Anything the deposit does NOT determine is out of scope and stays out: water's 15.75 and the
264-of-1003 donor-free count come from the reference tabulation, not from here, and the head's MAE
2.61 / R^2 -0.31 come from the retired run's own scoring.  A gate that pretended to check those
would be worse than no gate.

Usage
-----
    python scripts/analysis/check_donor_window_caption.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

DEPOSIT = Path("results/closure_ladder/placebo_profile_diagnosis.csv")
SECTION = Path("paper/sections/compensation-surrogate.tex")
#: The count the figure draws, which must equal --top in make_donor_window_figure.py.
TOP = 16
NAMED = {"cyclohexane": "C1CCCCC1", "acetone": "CC(C)=O",
         "toluene": "Cc1ccccc1", "tetrahydrofuran": "C1CCOC1"}


def _find(tex: str, pattern: str, what: str) -> tuple[str, ...]:
    m = re.search(pattern, tex)
    if m is None:
        raise SystemExit(f"NOT FOUND in {SECTION}: {what}\n  pattern {pattern}")
    return m.groups()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--deposit", type=Path, default=DEPOSIT)
    p.add_argument("--section", type=Path, default=SECTION)
    a = p.parse_args()

    d = pd.read_csv(a.deposit).set_index("solvent_smiles")
    drawn = d.sort_values("n_rows", ascending=False).head(TOP)
    tex = a.section.read_text()

    checks: list[tuple[str, str, str]] = []   # what, claimed, artifact

    got = _find(tex, r"profile carries \$([\d.]+)\$, \$([\d.]+)\$, \$([\d.]+)\$ and \$([\d.]+)\$",
                "the four molecule-matched learned areas")
    for (name, smi), claimed in zip(NAMED.items(), got):
        checks.append((f"learned donor-window area, {name}", claimed,
                       f"{d.loc[smi, 'learned_donor_window_area']:.1f}"))
        checks.append((f"reference donor-window area, {name}", "0.000",
                       f"{d.loc[smi, 'reference_donor_window_area']:.3f}"))

    lo, hi = _find(tex, r"between \$(\d+)\\%\$ and\n\$(\d+)\\%\$ of each molecule's total surface",
                   "the fraction range over the four named molecules")
    frac = [d.loc[s, "learned_donor_fraction"] for s in NAMED.values()]
    checks.append(("fraction range, low", lo, f"{100 * min(frac):.0f}"))
    checks.append(("fraction range, high", hi, f"{100 * max(frac):.0f}"))

    (acn,) = _find(tex, r"acetonitrile's \$([\d.]+)\$\\,\\AA\$\^2\$",
                   "acetonitrile's reference donor-window area")
    checks.append(("reference area, acetonitrile", acn,
                   f"{d.loc['CC#N', 'reference_donor_window_area']:.2f}"))

    (n_drawn,) = _find(tex, r"Figure~\\ref\{fig:donor-window\} draws that comparison over the\n"
                            r"(\w+) solvents carrying the most scored rows",
                       "the number of solvents the figure draws")
    (n_zero,) = _find(tex, r"the reference is exactly zero in (\w+) of them", "the empty count")
    words = {12: "twelve", 16: "sixteen"}
    checks.append(("solvents drawn", n_drawn, words.get(len(drawn), str(len(drawn)))))
    n_empty = int((drawn["reference_donor_window_area"] == 0).sum())
    checks.append(("reference exactly zero", n_zero, words.get(n_empty, str(n_empty))))

    bad = 0
    for what, claimed, artifact in checks:
        ok = claimed == artifact
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {what:44s} paper {claimed:>10s}   deposit {artifact:>10s}")
    print(f"\n{len(checks)} numerals bound to {a.deposit}, {bad} mismatched")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
