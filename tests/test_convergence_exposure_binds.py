r"""Bind the convergence-exposure paragraph of the SI to ``results/segment_convergence/``.

WHY THIS EXISTS
---------------
Until 2026-10-25 this paragraph told the reader that the convergence exposure on the substitution
contrast was *unmeasured on these arms*, and that the tree retained no COSMO-SAC checkpoints.  Both
had stopped being true: the five grounded checkpoints landed two days after the sentence was
written, and ``results/segment_convergence/`` swept the evaluation count on them on 2026-09-30,
twenty-seven days after submission.  Nothing re-read the sentence, because a sentence is not an
enrolled display and the hand-transcribed-display checker finds a display by ``\label``.

A disclosure that overstates ignorance is still a wrong statement, and it is the kind that no
referee catches -- it reads as caution.  This test makes the paragraph's numerals fail loudly when
the deposit moves, in the same way a value gate does for the enrolled displays.

WHAT IS CHECKED, AND WHAT IS NOT
--------------------------------
Checked: the five seed-mean MAE values, the width of their interval, the step from the evaluation
count to the fixed point and its share of the reported contrast, the three per-row shift statistics
at the evaluation count, and the six segment-residual statistics for the two profile kinds -- each
against ``summary.json``, at the decimal the paragraph prints.  Also checked: the checkpoint
inventory the paragraph asserts, against the files on disk when they are present.

Not checked: that the sweep bounds what the paragraph says it bounds.  This is a transcription gate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SI = ROOT / "paper/sections/SI.tex"
DEPOSIT = ROOT / "results/segment_convergence/summary.json"
CKPTS = ROOT / "checkpoints/e5_leakfree"

CONTRAST = 0.41  # the +0.41 the paragraph measures its step against; printed in the same sentence


def _typeset() -> str:
    return "\n".join(re.split(r"(?<!\\)%", ln, maxsplit=1)[0] for ln in SI.read_text().splitlines())


@pytest.fixture(scope="module")
def prose() -> str:
    t = _typeset()
    i = t.find("Re-scoring the\nretained grounded weights at other counts")
    assert i > 0, "the re-scoring sentence is gone; rewrite this gate with the paragraph"
    return t[i : i + 2600]


@pytest.fixture(scope="module")
def dep() -> dict:
    if not DEPOSIT.exists():
        pytest.skip("segment_convergence deposit absent")
    return json.load(DEPOSIT.open())


def test_the_five_seed_means_are_the_deposit_s(prose: str, dep: dict) -> None:
    printed = re.search(
        r"MAE runs \$([\d.]+)\$,\s*\n\$([\d.]+)\$, \$([\d.]+)\$, \$([\d.]+)\$ and \$([\d.]+)\$", prose
    )
    assert printed is not None, "the five-value list no longer matches"
    want = [float(x) for x in printed.groups()]
    got = [round(dep["part_b"]["mae_mean"][c], 4) for c in ("8", "16", "30", "100", "300")]
    assert want == got, f"seed means: paragraph {want}, deposit {got}"


def test_the_interval_width_and_the_step_bind(prose: str, dep: dict) -> None:
    m = dep["part_b"]["mae_mean"]
    width = max(m.values()) - min(m.values())
    printed_width = float(re.search(r"an interval \$([\d.]+)\$ wide", prose).group(1))
    assert round(width, 3) == printed_width, f"width: paragraph {printed_width}, deposit {width:.4f}"

    step = dep["separation"]["mae_shift_30_to_converged_ln_x2"]
    printed_step = float(re.search(r"fixed point is \$\+([\d.]+)\$", prose).group(1))
    assert round(step, 3) == printed_step, f"step: paragraph {printed_step}, deposit {step:.5f}"

    printed_share = float(re.search(r"\$([\d.]+)\\%\$ of the \$\+0\.41\$", prose).group(1))
    assert round(100 * step / CONTRAST, 1) == printed_share, (
        f"share: paragraph {printed_share}%, deposit {100 * step / CONTRAST:.2f}%"
    )


def test_the_sign_of_convergence_is_still_against_the_arm(prose: str, dep: dict) -> None:
    """The paragraph says converging makes the arm WORSE. That is the surprising half."""
    m = dep["part_b"]["mae_mean"]
    assert m["300"] > m["30"] > m["8"], (
        "convergence no longer degrades the arm monotonically; the word 'worse' in the paragraph "
        f"is a claim about this ordering: {m}"
    )
    assert "worse" in prose


def test_the_per_row_shift_statistics_bind(prose: str, dep: dict) -> None:
    sh = dep["part_b"]["ln_x2_shift_vs_converged"]["30"]
    med = float(re.search(r"median row moves \$([\d.]+)\\times10\^\{-4\}", prose).group(1))
    assert round(sh["median"] * 1e4, 1) == med, f"median row shift: {med}e-4 vs {sh['median']:.6f}"
    p95 = float(re.search(r"ninety-fifth percentile\n\$([\d.]+)\$ and its worst row", prose).group(1))
    assert round(sh["p95"], 3) == p95, f"p95 row shift: {p95} vs {sh['p95']:.5f}"
    worst = float(re.search(r"worst row \$([\d.]+)\$ in", prose).group(1))
    assert round(sh["max"], 2) == worst, f"worst row: {worst} vs {sh['max']:.4f}"


def test_the_two_profiles_rate_statistics_bind(prose: str, dep: dict) -> None:
    by = dep["part_a"]["by_source"]
    ref, learned = by["reference_vt2005"]["counts"]["30"], by["learned_seed42"]["counts"]["30"]
    nums = re.search(
        r"median \$([\d.]+)\\times10\^\{-4\}\$, a ninety-fifth percentile of \$([\d.]+)\$ and a "
        r"worst case of \$([\d.]+)\$ in \\lngi\\?\s*\non the tabulation, against "
        r"\$([\d.]+)\\times10\^\{-3\}\$, \$([\d.]+)\$ and \$([\d.]+)\$ on the learned profile",
        prose,
    )
    assert nums is not None, "the two-profile sentence no longer matches"
    rm, rp, rx, lm, lp, lx = (float(x) for x in nums.groups())
    assert round(ref["median"] * 1e4, 1) == rm, f"tabulated median: {rm}e-4 vs {ref['median']:.2e}"
    assert round(ref["p95"], 3) == rp, f"tabulated p95: {rp} vs {ref['p95']:.5f}"
    assert round(ref["max"], 3) == rx, f"tabulated max: {rx} vs {ref['max']:.5f}"
    assert round(learned["median"] * 1e3, 1) == lm, f"learned median: {lm}e-3 vs {learned['median']:.2e}"
    assert round(learned["p95"], 3) == lp, f"learned p95: {lp} vs {learned['p95']:.5f}"
    assert round(learned["max"], 3) == lx, f"learned max: {lx} vs {learned['max']:.5f}"
    # The paragraph says the learned profile is the slower by roughly twofold where it is large.
    assert 1.5 < learned["p95"] / ref["p95"] < 3.0
    assert 1.5 < learned["max"] / ref["max"] < 3.0


def test_the_same_weights_as_the_deposited_arm(dep: dict) -> None:
    """Seed 42 at the evaluation count must reproduce the deposited arm, or it is other weights."""
    assert round(dep["part_b"]["mae_per_seed"]["42"]["30"], 5) == 1.88713, (
        "the sweep no longer reproduces the deposited grounded_a seed 42; the paragraph's claim "
        "that these are the retained weights of the arms of record rests on this identity"
    )


@pytest.mark.skipif(not CKPTS.exists(), reason="checkpoint tree absent")
def test_the_checkpoint_inventory_the_paragraph_asserts(prose: str) -> None:
    grounded = sorted(CKPTS.glob("grounded_a_seed*.pt"))
    ungrounded_w = sorted(CKPTS.glob("ungrounded_seed*.pt"))
    ungrounded_m = sorted(CKPTS.glob("ungrounded_seed*.manifest.json"))
    assert len(grounded) == 5, f"paragraph says five grounded weights; found {len(grounded)}"
    assert not ungrounded_w, (
        "the paragraph says the ungrounded arm has no weights, and that is why it reports the "
        f"supervision contrast as unsweepable; found {[p.name for p in ungrounded_w]}"
    )
    assert len(ungrounded_m) == 5, f"paragraph says five ungrounded manifests; found {len(ungrounded_m)}"
