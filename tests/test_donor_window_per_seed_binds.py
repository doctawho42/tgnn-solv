r"""Bind the PER-SEED numerals of the donor-window paragraph to the per-seed deposits.

WHY THIS EXISTS
---------------
Every printed quantity in that paragraph used to be read off the SEED-AVERAGED profile, and the
per-seed spreads are wide enough that three of them were wrong or misleading (2026-10-29):

  * rho printed +0.65, which EXCEEDS all five per-seed values (+0.451/+0.284/+0.436/+0.545/+0.555) --
    averaging five profiles suppresses area noise and inflates a rank correlation;
  * the four named donor-window areas were printed to two decimals (0.22/1.96/1.33/2.40) where the
    arms span 0.07..0.34 on cyclohexane and 0.40..2.28 on toluene;
  * "between 0.1% and 1.5% of each molecule's total surface" was simply WRONG per seed: the four run
    0.04% to 2.04%, so the printed interval EXCLUDED observed values at both ends. A range is the one
    statistic that cannot be averaged and still mean what it says.

The paragraph now carries per-seed medians and spreads, with the averaged figures attached to the
figure they actually draw. This test recomputes each of those from the per-seed deposits so they
cannot drift back.

WHAT IS NOT CHECKED
-------------------
``0.015``, the profile mass the supervised arms leave in the extreme bins, is NOT bound here. It
carries a four-order margin against the ``1e-6`` a softmax reaches at a logit gap of ten, so no
plausible seed spread reaches it; chasing it would be theatre. ``0.212`` and ``0.189`` are
single-checkpoint quantities (an untrained net and the retired head), so no seed average enters them
-- ``check_donor_window_caption.py`` already declares them out of scope for the same reason.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
SECTION = ROOT / "paper/sections/compensation-surrogate.tex"
PER_SEED = ROOT / "results/class2_transfer/per_seed_donor"
DEPOSITED = [42, 43, 44, 45, 46]
NAMED = ["C1CCCCC1", "CC(C)=O", "Cc1ccccc1", "C1CCOC1"]   # cyclohexane, acetone, toluene, THF

needs = pytest.mark.skipif(not PER_SEED.exists(), reason="per-seed donor deposits absent")


def _typeset() -> str:
    return "\n".join(re.split(r"(?<!\\)%", ln, maxsplit=1)[0]
                     for ln in SECTION.read_text().splitlines())


def _frames(prefix: str, seeds: list[int]) -> dict[int, pd.DataFrame]:
    return {s: pd.read_csv(PER_SEED / f"{prefix}_seed{s}.csv") for s in seeds}


@needs
def test_the_five_per_seed_rho_values_bind() -> None:
    printed = re.search(
        r"\(\$\+([\d.]+)\$, \$\+([\d.]+)\$, \$\+([\d.]+)\$, \$\+([\d.]+)\$, \$\+([\d.]+)\$;", _typeset()
    )
    assert printed is not None, "the five per-seed rho values no longer match the pattern"
    want = [float(x) for x in printed.groups()]
    got = []
    for s in DEPOSITED:
        d = _frames("deposited", [s])[s]
        got.append(round(float(spearmanr(d.learned_donor_window_area,
                                         d.reference_donor_window_area).statistic), 3))
    assert want == got, f"per-seed rho: paragraph {want}, deposits {got}"


@needs
def test_the_median_seed_rho_binds() -> None:
    printed = float(re.search(r"ranks with the reference at\s*\n?\$\\rho=\+([\d.]+)\$ in the median seed",
                              _typeset()).group(1))
    rhos = [float(spearmanr(_frames("deposited", [s])[s].learned_donor_window_area,
                            _frames("deposited", [s])[s].reference_donor_window_area).statistic)
            for s in DEPOSITED]
    assert round(float(np.median(rhos)), 2) == printed, (
        f"median-seed rho: paragraph {printed}, deposits {np.median(rhos):.4f}"
    )


@needs
def test_the_averaged_rho_still_exceeds_every_arm() -> None:
    """The sentence's whole point. If this stops holding, the sentence is wrong, not stale."""
    avg = pd.read_csv(ROOT / "results/donor_window_rescore/per_solvent.csv")
    rho_avg = float(spearmanr(avg.learned_donor_window_area, avg.reference_donor_window_area).statistic)
    rhos = [float(spearmanr(_frames("deposited", [s])[s].learned_donor_window_area,
                            _frames("deposited", [s])[s].reference_donor_window_area).statistic)
            for s in DEPOSITED]
    assert rho_avg > max(rhos), (
        f"the seed-averaged rho {rho_avg:.4f} no longer exceeds every per-seed value {rhos}"
    )
    assert "exceeds every per-seed value" in _typeset()


@needs
def test_the_four_per_seed_median_areas_bind() -> None:
    printed = re.search(
        r"per-seed medians of \$([\d.]+)\$, \$([\d.]+)\$, \$([\d.]+)\$ and\s*\n?\$([\d.]+)\$", _typeset()
    )
    assert printed is not None, "the four per-seed median areas no longer match"
    want = [float(x) for x in printed.groups()]
    f = _frames("deposited", DEPOSITED)
    got = []
    for smi in NAMED:
        vals = [float(f[s].loc[f[s].solvent_smiles == smi, "learned_donor_window_area"].iloc[0])
                for s in DEPOSITED]
        got.append(round(float(np.median(vals)), 2))
    assert want == got, f"per-seed median areas: paragraph {want}, deposits {got}"


@needs
def test_the_surface_share_range_covers_every_observation() -> None:
    """The defect this replaced: a printed range that excluded observed values."""
    m = re.search(r"from \$([\d.]+)\\%\$ to \$([\d.]+)\\%\$ across solvents and\s*\nseeds", _typeset())
    assert m is not None, "the surface-share range no longer matches"
    lo_p, hi_p = (float(x) for x in m.groups())
    f = _frames("deposited", DEPOSITED)
    vals = [100 * float(f[s].loc[f[s].solvent_smiles == smi, "learned_donor_fraction"].iloc[0])
            for smi in NAMED for s in DEPOSITED]
    # Bounds must round OUTWARD: the first correction rounded to nearest and excluded both
    # extremes (0.038336 and 2.041615) exactly as the original range had.
    assert math.floor(min(vals) * 100) / 100 == lo_p and math.ceil(max(vals) * 100) / 100 == hi_p, (
        f"printed range [{lo_p}, {hi_p}]%, outward-rounded observed "
        f"[{math.floor(min(vals)*100)/100}, {math.ceil(max(vals)*100)/100}]%"
    )
    assert min(vals) >= lo_p and max(vals) <= hi_p, (
        "the printed range must CONTAIN every per-seed observation -- that was the original defect, "
        "and rounding to nearest reintroduces it"
    )


@needs
def test_the_zero_reference_median_and_its_spread_bind() -> None:
    t = _typeset()
    med_p = float(re.search(r"per-seed median area is\s*\n?\$([\d.]+)\$", t).group(1))
    lo_p, hi_p = (float(x) for x in
                  re.search(r"spanning \$([\d.]+)\$ to \$([\d.]+)\$ between seeds", t).groups())
    f = _frames("deposited", DEPOSITED)
    meds = []
    for s in DEPOSITED:
        d = f[s]
        meds.append(float(d[d.reference_donor_window_area == 0.0].learned_donor_window_area.median()))
    assert round(float(np.median(meds)), 1) == med_p, f"median of medians: {med_p} vs {np.median(meds):.4f}"
    assert round(min(meds), 2) == lo_p and round(max(meds), 2) == hi_p, (
        f"printed spread [{lo_p}, {hi_p}], observed [{min(meds):.2f}, {max(meds):.2f}]"
    )


@needs
def test_current_code_per_seed_rho_sits_inside_the_deposited_spread() -> None:
    """This is what settled the transfer question: the drop was the averaging base, not the code."""
    dep = [float(spearmanr(_frames("deposited", [s])[s].learned_donor_window_area,
                           _frames("deposited", [s])[s].reference_donor_window_area).statistic)
           for s in DEPOSITED]
    cur = [float(spearmanr(_frames("current", [s])[s].learned_donor_window_area,
                           _frames("current", [s])[s].reference_donor_window_area).statistic)
           for s in (42, 43)]
    assert all(min(dep) <= c <= max(dep) for c in cur), (
        f"current-code per-seed rho {cur} left the deposited spread [{min(dep):.3f}, {max(dep):.3f}]; "
        "the class-2 transfer conclusion rests on them being inside it"
    )
