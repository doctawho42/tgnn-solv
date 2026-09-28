#!/usr/bin/env python
"""Bind Sec. 3.3's donor-window numerals -- caption and running prose -- to the deposits they claim.

WHY THIS EXISTS.  check_hand_transcribed_displays.py binds the floats and the abstract of the
re-run family, and it is the reason six values in this manuscript were caught stale.  It cannot
reach these: the donor-window numbers sit in running prose with no producer between them and the
artifact, which is exactly the position the six stale values sat in.

WHAT CHANGED 2026-09-28, AND WHY THE GATE IS WIDER NOW.  This gate used to read
results/closure_ladder/placebo_profile_diagnosis.csv, a RETIRED run whose sigma-supervision stream
ran for zero steps.  It bound the prose to that deposit faithfully -- and that was the whole
problem.  Every numeral agreed with its artifact while the paragraph's topic sentence was a claim
about the arms of Fig. 2, which were never measured.  When they were, the quantity moved by a factor
of twenty (31.0% of surface to 1.5%) and the rank correlation with the reference went from -0.055 to
+0.65.  A gate can only bind prose to the deposit it is pointed at; pointing it at the right one is
not something it can check for itself.  So the deposit is now the rescore, and the enrichment
statistics that carry the surviving claim are bound too, rather than left in prose.

WHAT IS BOUND

  results/donor_window_rescore/per_solvent.csv   (grounded_a, seeds 42-46)
    the four molecule-matched learned areas    cyclohexane, acetone, toluene, tetrahydrofuran
    their reference areas being exactly zero   the claim is "exactly zero", not "small"
    the fraction range over those same four
    the median where the reference is empty
    acetonitrile's reference area              the 6.71 that stands above ethanol's 6.20
    the figure's counts                        sixteen drawn, twelve empty, sixteen occupied
    both rank correlations                     the arms of record's +0.65 and the retired -0.055
    the retired head's median surface share    the 31.0% the separation argument rests on

  results/sigma_profile_residual/per_molecule.csv   (same arms, 126 molecules, five seeds)
    the residual's donor-window enrichment     median, IQR, the share exceeding one
    the two molecule counts                    126 measured, 48 with a non-empty reference

OUT OF SCOPE, DELIBERATELY.  Water's 15.75 and the 264-of-1003 donor-free count come from the
reference tabulation, not from either deposit; the retired head's MAE 2.61 / R^2 -0.31 come from its
own scoring; the 0.212-against-0.189 null arm comes from the retired deposit's untrained row.  A
gate that pretended to check those would be worse than no gate.

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
from scipy.stats import spearmanr

DEPOSIT = Path("results/donor_window_rescore/per_solvent.csv")
RESIDUAL = Path("results/sigma_profile_residual/per_molecule.csv")
SECTION = Path("paper/sections/compensation-surrogate.tex")
#: The count the figure draws, which must equal --top in make_donor_window_figure.py.
TOP = 16
NAMED = {"cyclohexane": "C1CCCCC1", "acetone": "CC(C)=O",
         "toluene": "Cc1ccccc1", "tetrahydrofuran": "C1CCOC1"}
WORDS = {12: "twelve", 16: "sixteen", 25: "twenty-five", 31: "thirty-one"}


def _find(tex: str, pattern: str, what: str) -> tuple[str, ...]:
    m = re.search(pattern, tex)
    if m is None:
        raise SystemExit(f"NOT FOUND in {SECTION}: {what}\n  pattern {pattern}")
    return m.groups()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--deposit", type=Path, default=DEPOSIT)
    p.add_argument("--residual", type=Path, default=RESIDUAL)
    p.add_argument("--section", type=Path, default=SECTION)
    a = p.parse_args()

    d = pd.read_csv(a.deposit)
    r = pd.read_csv(a.residual)
    di = d.set_index("solvent_smiles")
    drawn = d.sort_values("n_rows", ascending=False).head(TOP)
    # WHITESPACE-NORMALISED BEFORE MATCHING.  Three of this gate's patterns carried a literal "\n"
    # at whatever column the source happened to wrap at, so the 2026-08-19 readability pass broke
    # them one after another without a single bound value having changed. A gate that fails on a
    # reflow teaches its reader to ignore it.  Values are bound; line breaks are not.
    tex = re.sub(r"\s+", " ", a.section.read_text())

    checks: list[tuple[str, str, str]] = []   # what, claimed, artifact

    got = _find(tex, r"profile carries \$([\d.]+)\$, \$([\d.]+)\$, \$([\d.]+)\$ and \$([\d.]+)\$",
                "the four molecule-matched learned areas")
    for (name, smi), claimed in zip(NAMED.items(), got):
        checks.append((f"learned donor-window area, {name}", claimed,
                       f"{di.loc[smi, 'learned_donor_window_area']:.2f}"))
        checks.append((f"reference donor-window area, {name}", "0.000",
                       f"{di.loc[smi, 'reference_donor_window_area']:.3f}"))

    lo, hi = _find(tex, r"between \$([\d.]+)\\%\$ and \$([\d.]+)\\%\$ of each molecule's total "
                        r"surface", "the fraction range over the four named molecules")
    frac = [di.loc[s, "learned_donor_fraction"] for s in NAMED.values()]
    checks.append(("fraction range, low", lo, f"{100 * min(frac):.1f}"))
    checks.append(("fraction range, high", hi, f"{100 * max(frac):.1f}"))

    n_word, med_empty = _find(
        tex, r"median over the ([\w-]+) solvents whose reference is exactly zero is \$([\d.]+)\$",
        "the median area where the reference is empty")
    empty = d[d["reference_donor_window_area"] <= 1e-9]
    checks.append(("solvents with empty reference", n_word, WORDS.get(len(empty), str(len(empty)))))
    checks.append(("median learned area where reference empty", med_empty,
                   f"{empty['learned_donor_window_area'].median():.1f}"))

    (acn,) = _find(tex, r"acetonitrile's \$([\d.]+)\$\\,\\AA\$\^2\$",
                   "acetonitrile's reference donor-window area")
    checks.append(("reference area, acetonitrile", acn,
                   f"{di.loc['CC#N', 'reference_donor_window_area']:.2f}"))

    (n_drawn,) = _find(tex, r"Figure~\\ref\{fig:donor-window\} draws that comparison over the "
                            r"([\w-]+) solvents carrying the most scored rows",
                       "the number of solvents the figure draws")
    (n_zero,) = _find(tex, r"the reference is exactly zero in ([\w-]+) of them", "the empty count")
    (n_occ,) = _find(tex, r"the learned profile is occupied in all ([\w-]+)", "the occupied count")
    n_empty_drawn = int((drawn["reference_donor_window_area"] == 0).sum())
    n_occupied = int((drawn["learned_donor_window_area"] > 0).sum())
    checks.append(("solvents drawn", n_drawn, WORDS.get(len(drawn), str(len(drawn)))))
    checks.append(("reference exactly zero, drawn", n_zero,
                   WORDS.get(n_empty_drawn, str(n_empty_drawn))))
    checks.append(("learned occupied, drawn", n_occ, WORDS.get(n_occupied, str(n_occupied))))

    # THE TWO RANK CORRELATIONS, which are what the separation argument turns on: the retired head
    # had no relationship to the reference at all, and these arms do.
    n_scored, rho = _find(tex, r"across the ([\w-]+) scored solvents the learned donor-window area "
                               r"ranks with the reference at \$\\rho=\+([\d.]+)\$",
                          "the rank correlation on the arms of record")
    checks.append(("scored solvents", n_scored, WORDS.get(len(d), str(len(d)))))
    checks.append(("Spearman rho, arms of record", rho,
                   f"{spearmanr(d.learned_donor_window_area, d.reference_donor_window_area).statistic:+.2f}".lstrip("+")))

    ret_pct, ret_rho = _find(
        tex, r"puts \$([\d.]+)\\%\$ of surface in the same window and does not rank with the "
             r"reference at all \(\$\\rho=-([\d.]+)\$",
        "the retired head's surface share and rank correlation")
    checks.append(("retired median surface share", ret_pct,
                   f"{100 * d['retired_learned_donor_fraction'].median():.1f}"))
    checks.append(("Spearman rho, retired", f"-{ret_rho}",
                   f"{spearmanr(d.retired_learned_donor_window_area, d.reference_donor_window_area).statistic:.3f}"))

    (survives,) = _find(tex, r"What the supervised arms leave is \$([\d.]+)\$",
                        "the surviving mass fraction on the arms of record")
    checks.append(("surviving donor-window share", survives,
                   f"{d['learned_donor_fraction'].median():.3f}"))

    # THE ENRICHMENT, quoted on the molecules whose reference tabulation is NOT empty, so that the
    # baseline the residual is compared against is not a column of zeros.
    enr, iqr_lo, iqr_hi = _find(
        tex, r"over-represented there by a factor of \$([\d.]+)\$ \(IQR \$([\d.]+)\$ to \$([\d.]+)\$",
        "the donor-window enrichment and its IQR")
    (share,) = _find(tex, r"exceeding one for \$(\d+)\\%\$ of molecules", "the share exceeding one")
    n_mol, n_ref = _find(tex, r"over \$(\d+)\$ molecules and five seeds; the figure is quoted on "
                              r"the \$(\d+)\$ whose reference tabulation carries donor area",
                         "the two molecule counts")
    has_ref = r[r.donor_area_reference > 1e-9]
    e = has_ref["resid_frac_donor_solvent"] / has_ref["area_frac_donor_solvent"]
    checks.append(("donor enrichment, median", enr, f"{e.median():.1f}"))
    checks.append(("donor enrichment, IQR low", iqr_lo, f"{e.quantile(.25):.1f}"))
    checks.append(("donor enrichment, IQR high", iqr_hi, f"{e.quantile(.75):.1f}"))
    checks.append(("share exceeding one", share, f"{100 * (e > 1).mean():.0f}"))
    checks.append(("molecules measured", n_mol, str(r.smiles.nunique())))
    checks.append(("molecules with non-empty reference", n_ref, str(has_ref.smiles.nunique())))

    bad = 0
    for what, claimed, artifact in checks:
        ok = claimed == artifact
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {what:44s} paper {claimed:>10s}   deposit {artifact:>10s}")
    print(f"\n{len(checks)} numerals bound to {a.deposit.name} + {a.residual.name}, {bad} mismatched")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
