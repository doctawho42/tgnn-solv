r"""Bind the over-representation sentence of the donor-window paragraph to its artifact.

WHY THIS EXISTS
---------------
``scripts/analysis/check_hand_transcribed_displays.py`` guards the enrolled displays, and it finds a
display by ``\label``.  The paragraph this test guards -- the donor-window paragraph of
``paper/sections/compensation-surrogate.tex`` -- carries no label, so every numeral in its closing
sentence sat outside every mechanical check the repository has.  It stayed wrong for four weeks: the
printed interquartile range of ``[1.6, 3.0]`` reproduced neither aggregation of the deposit it was
read from, and the factor and the pool were measured over a molecule set built with
``ln_x2.notna()``, which admits 2495 auxiliary rows whose ``ln_x2`` is exactly ``0.0``
(``results/row_filter_audit/RESULTS.md``).  Fifty-five of the deposit's 126 molecules appear in no
labelled test row.

The deposit itself was never regenerated and still publishes the unfiltered ``4.381``, so a reader
who follows the citation lands on a superseded number.  That is recorded in
``results/sigma_profile_residual/SUPERSEDED.md``; what this test adds is that the SENTENCE cannot
drift from the CSV again without a red test.

WHAT IS CHECKED, AND WHAT IS NOT
--------------------------------
Checked: the factor, both ends of the interval, the size of the restricted pool, the size of the
unfiltered pool, and the count of sub-unity exceptions -- each recomputed from
``per_molecule.csv`` and the labelled rows of ``notebooks/data/processed/test.csv``, and compared at
the decimal the sentence prints.

Not checked: that the quantity means what the sentence says it means.  This is a transcription gate.
It binds prose to artifact and never artifact to claim.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SECTION = ROOT / "paper/sections/compensation-surrogate.tex"
PER_MOLECULE = ROOT / "results/sigma_profile_residual/per_molecule.csv"
TEST_ROWS = ROOT / "notebooks/data/processed/test.csv"

# The sentence, with its six numerals captured.  Written as one pattern on purpose: a sentence
# rewritten into a different shape should fail LOUDLY here rather than quietly stop being checked.
SENTENCE = re.compile(
    r"over-represented there by a factor of \$(?P<factor>[\d.]+)\$ \(IQR \$(?P<lo>[\d.]+)\$ to\s*\n"
    r"\$(?P<hi>[\d.]+)\$\).*?"
    r"quoted on the\s*\n\$(?P<pool>\d+)\$ that both carry donor area.*?"
    r"(?P<exceptions>Three) of the thirty-three fall below one.*?"
    r"unfiltered pool of \$(?P<unfiltered>\d+)\$",
    re.DOTALL,
)

WORD_COUNT = {"Three": 3}


def _typeset() -> str:
    """The section with its LaTeX comments removed.

    The comment block above the paragraph discusses the superseded 4.38 on purpose, so a check on
    what the section PRINTS has to read past the commentary -- the same flattening the author does
    by hand when verifying that an edit landed.
    """
    out = []
    for line in SECTION.read_text().splitlines():
        kept = re.split(r"(?<!\\)%", line, maxsplit=1)[0]
        out.append(kept)
    return "\n".join(out)


def _printed() -> dict[str, str]:
    m = SENTENCE.search(_typeset())
    assert m is not None, (
        "the over-representation sentence no longer matches the pattern this test binds; "
        "if it was rewritten, rewrite the pattern with it rather than deleting the test"
    )
    return m.groupdict()


def _measured() -> dict[str, float | int]:
    from tgnn_solv.data.utils import canonicalize

    rows = pd.read_csv(TEST_ROWS, low_memory=False)
    labelled = rows[rows["has_solubility"].astype(bool)]
    seen = set(labelled["solute_smiles"].astype(str)) | set(labelled["solvent_smiles"].astype(str))
    reached = {c for s in seen if (c := canonicalize(str(s))) is not None}

    d = pd.read_csv(PER_MOLECULE)
    d = d[d["donor_area_reference"] > 0]
    unfiltered = d["smiles"].nunique()
    d = d[[canonicalize(str(s)) in reached for s in d["smiles"]]]

    # The molecule is the unit: median over seeds first, then quantiles over molecules.
    per_mol = d.groupby("smiles")["enrichment_donor_solute"].median().dropna()
    lo, mid, hi = np.percentile(per_mol, [25, 50, 75])
    return {
        "factor": mid,
        "lo": lo,
        "hi": hi,
        "pool": len(per_mol),
        "unfiltered": unfiltered,
        "exceptions": int((per_mol <= 1).sum()),
    }


needs_data = pytest.mark.skipif(
    not (PER_MOLECULE.exists() and TEST_ROWS.exists()),
    reason="deposit or processed split absent",
)


@needs_data
def test_factor_and_interval_bind_to_the_deposit() -> None:
    printed, measured = _printed(), _measured()
    for key in ("factor", "lo", "hi"):
        want = float(printed[key])
        got = round(float(measured[key]), len(printed[key].split(".")[-1]))
        assert got == want, (
            f"{key}: the sentence prints {want} and the deposit gives {got} "
            f"(restricted to the labelled-row pool, molecule as the unit)"
        )


@needs_data
def test_both_pool_sizes_bind() -> None:
    printed, measured = _printed(), _measured()
    assert int(printed["pool"]) == measured["pool"], (
        f"restricted pool: sentence {printed['pool']}, measured {measured['pool']}"
    )
    assert int(printed["unfiltered"]) == measured["unfiltered"], (
        f"unfiltered pool: sentence {printed['unfiltered']}, measured {measured['unfiltered']}"
    )


@needs_data
def test_the_exception_count_is_the_stable_statement() -> None:
    """The share moved 94% -> 91% because the pool halved; the COUNT is what holds."""
    printed, measured = _printed(), _measured()
    assert WORD_COUNT[printed["exceptions"]] == measured["exceptions"], (
        f"sub-unity exceptions: sentence says {printed['exceptions']}, measured "
        f"{measured['exceptions']}"
    )


@needs_data
def test_the_named_exceptions_are_the_measured_ones() -> None:
    from tgnn_solv.data.utils import canonicalize

    rows = pd.read_csv(TEST_ROWS, low_memory=False)
    labelled = rows[rows["has_solubility"].astype(bool)]
    seen = set(labelled["solute_smiles"].astype(str)) | set(labelled["solvent_smiles"].astype(str))
    reached = {c for s in seen if (c := canonicalize(str(s))) is not None}
    d = pd.read_csv(PER_MOLECULE)
    d = d[d["donor_area_reference"] > 0]
    d = d[[canonicalize(str(s)) in reached for s in d["smiles"]]]
    per_mol = d.groupby("smiles")["enrichment_donor_solute"].median()
    below = set(per_mol[per_mol <= 1].index)
    assert below == {"NC=O", "O", "CC#N"}, (
        f"the sentence names formamide, water and acetonitrile; measured {sorted(below)}"
    )


@needs_data
def test_the_superseded_deposit_value_is_not_what_the_paper_prints() -> None:
    """Guard the confusion this correction came out of: 4.38 and 2.1 are different quantities."""
    d = pd.read_csv(PER_MOLECULE)
    unfiltered_all = d["enrichment_donor_solute"].median()
    assert round(float(unfiltered_all), 2) == 4.38, (
        "the deposit's own headline moved; check results/sigma_profile_residual/SUPERSEDED.md "
        "and results/row_filter_audit/RESULTS.md before touching the paper"
    )
    assert "4.38" not in _typeset(), (
        "the unfiltered 4.38 is not a value this section may TYPESET: it is measured over 126 "
        "molecules, 55 of which appear in no labelled test row.  The comment block may discuss it"
    )
