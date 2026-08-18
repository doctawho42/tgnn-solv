"""The hand-transcribed displays of the sigma-grounding family must agree with their artifacts.

``results/e5_sigma_grounding_leakfree/DISCHARGE_SHEET.md`` Sec. 5 records that four enrolled items
are hand-transcribed LaTeX with no generator behind them -- the claims ledger, the run-family
table's sigma-grounding row, the nine captions the caption rule governs, and the table-of-contents
graphic -- and that the only mechanical gate anywhere in that set counts the abstract's words.  This
module is the gate that was missing: it runs
``scripts/analysis/check_hand_transcribed_displays.py`` against the published tree, so a wrong digit
entering any of those displays fails the suite instead of passing every automatic check the
repository has.

The heavy test reads twenty per-row prediction files (~130 MB) and takes about half a minute.  It is
skipped when the deposits are absent, so a checkout without ``results/`` still runs the suite; it is
NOT skipped when they are present, because a check that only runs on the author's machine is the
check that was not there.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analysis" / "check_hand_transcribed_displays.py"
PUBLISHED = REPO / "results" / "e5_sigma_grounding"
TOC = REPO / "scripts" / "analysis" / "make_toc_figure.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _deposits_present() -> bool:
    return all((PUBLISHED / f"seed_{s}" / f"{a}_predictions.csv").exists()
               for s in (42, 43, 44)
               for a in ("ungrounded", "grounded_a", "oracle", "directgnn"))


needs_deposits = pytest.mark.skipif(
    not _deposits_present(),
    reason="per-row e5 deposits absent; the display check needs results/e5_sigma_grounding/",
)


# --------------------------------------------------------------------------- unit-level checks
def test_fmt_rounds_half_away_from_zero():
    """The paper prints 1.85 for a mean of 1.8457; Python's round() would print 1.84."""
    mod = _load(SCRIPT, "check_displays_fmt")
    assert mod.fmt(1.845, 2) == "1.85"
    assert mod.fmt(0.1435, 2, sign=True) == "+0.14"
    assert mod.fmt(-0.1977, 2, sign=True) == "-0.20"
    assert mod.fmt(0.2366, 3) == "0.237"


def test_numeral_extraction_reads_measurements_and_not_names():
    """A digit inside a name is not a measurement, and a macro must not eat the digit after it."""
    mod = _load(SCRIPT, "check_displays_num")
    toks = [n.token for n in mod.numerals(r"top-1 $-0.107$ on VT-2005, $51\pm2\%$, $R^2$, "
                                          r"$1.78\to0.77$")]
    assert toks == ["-0.107", "51", "2", "1.78", "0.77"]


def test_toc_lines_are_derived_from_the_run_tree():
    """Row 26 of the discharge sheet: re-running the script must not leave a stale claim standing."""
    toc = _load(TOC, "make_toc_figure_under_test")
    assert hasattr(toc, "toc_lines"), "the caveat is still a string literal"
    lines = toc.toc_lines(PUBLISHED)
    assert lines[0] == "Grounding is two operations on one database, with opposite signs"
    assert lines[1] == ("(solubility MAE on held-out scaffolds, three seeds; "
                        "magnitudes in the text).")
    assert lines[2] == "Training on it is not certified leak-free; a re-run is pre-committed."


def test_toc_caveat_and_seed_count_move_with_the_tree(tmp_path):
    """Both moving parts move: the caveat on line three AND the seed count on line two."""
    toc = _load(TOC, "make_toc_figure_under_test2")
    root = tmp_path / "leakfree"
    for seed in (42, 43, 44, 45, 46):
        d = root / f"seed_{seed}"
        d.mkdir(parents=True)
        (d / "grounded_a_predictions.summary.json").write_text("{}")
    assert "five seeds" in toc.toc_lines(root)[1]
    assert len(toc.toc_lines(root)) == 3, "an absent certificate must keep the caveat"

    (root / "provenance_certificate.json").write_text('{"certified": true, "problems": []}')
    certified = toc.toc_lines(root)
    assert len(certified) == 2, "a passing certificate must drop the caveat"
    assert not any("leak-free" in line for line in certified)

    (root / "provenance_certificate.json").write_text('{"certified": false, "problems": ["x"]}')
    assert len(toc.toc_lines(root)) == 3, "a failing certificate must keep the caveat"


def test_a_row_no_selector_matches_is_fatal():
    r"""Coverage is a property of the FLOAT, not of the rows someone remembered to select.

    The numeral accounting runs inside the text it is handed, so a row nobody registered was
    never read at all: a verifier appended a wholly invented row to ``tab:claims`` -- new label,
    ``n=9999``, ``7 seeds``, ``3.14 -> 2.72`` -- and the run printed ``MISMATCH 0, UNREGISTERED
    0, OK 48`` and exited zero.
    """
    mod = _load(SCRIPT, "check_displays_float")
    block = "\n".join([
        r"\begin{table*}", r"\begin{tabular}{ll}", r"\toprule",
        r"Claim & Value \\", r"\midrule",
        r"A registered claim & $1.5$ \\",
        r"An entirely invented claim & labelled rows ($9999$), 7 seeds \\",
        r"\bottomrule", r"\end{tabular}", r"\end{table*}"])
    specs = [mod.DisplayRow(key="Claim & Value", owner="header"),
             mod.DisplayRow(key="A registered claim", declared=["1.5"], owner="somewhere")]
    findings = mod.check_float("tab:demo", block, specs, None)
    unregistered = [f for f in findings if f.severity == "UNREGISTERED"]
    assert len(unregistered) == 1, [f.item for f in findings]
    assert "An entirely invented claim" in unregistered[0].printed
    assert unregistered[0].fatal

    # and the registry may not double-claim one row while leaving another unread
    with pytest.raises(SystemExit, match="match the same row"):
        mod.check_float("tab:demo", block, [*specs, mod.DisplayRow(key="registered claim")], None)


def test_seeds_come_from_the_tree_and_a_flag_may_not_undercount_it(tmp_path):
    """Every printed seed count is checked against this set, so a default of [42,43,44] made
    'three seeds', '42,43,44' and 'seed 42 of three' pass against a five-seed tree."""
    mod = _load(SCRIPT, "check_displays_seeds")
    for seed in (42, 43, 44, 45, 46):
        d = tmp_path / f"seed_{seed}"
        d.mkdir()
        (d / "grounded_a_predictions.csv").write_text("solute_smiles\n")
    (tmp_path / "seed_47").mkdir()          # no deposits: not a seed of this tree
    assert mod.discover_seeds(tmp_path) == (42, 43, 44, 45, 46)
    assert mod.resolve_seeds(tmp_path, None, "--seeds") == (42, 43, 44, 45, 46)
    assert mod.resolve_seeds(tmp_path, [42, 43, 44, 45, 46], "--seeds") == (42, 43, 44, 45, 46)
    with pytest.raises(SystemExit, match="holds"):
        mod.resolve_seeds(tmp_path, [42, 43, 44], "--seeds")
    with pytest.raises(SystemExit, match="cannot be established"):
        mod.resolve_seeds(tmp_path / "nothing-here", None, "--seeds")


def test_the_both_increasing_count_is_never_spliced_across_two_trees(tmp_path):
    """One checkpoint and its own oracle re-evaluation, or the count is not computed.

    With the leak-free tree in exactly the state the gate is in today -- grounded arm deposited,
    the sigma-oracle inference pass still pending -- a per-arm fallback took the grounded arm
    from the re-run and the oracle from the published tree and reported the count OK, in a run
    where every other oracle-quoting cell was correctly MISSING.
    """
    mod = _load(SCRIPT, "check_displays_splice")
    root, published = tmp_path / "leakfree", tmp_path / "published"
    for seed in (42, 43):
        (root / f"seed_{seed}").mkdir(parents=True)
        (root / f"seed_{seed}" / "grounded_a_predictions.csv").write_text("x\n")
        (published / f"seed_{seed}").mkdir(parents=True)
        for arm in ("grounded_a", "oracle"):
            (published / f"seed_{seed}" / f"{arm}_predictions.csv").write_text("x\n")
    got = mod.both_increasing_groups(root, published, (42, 43))
    assert got["available"] is False
    assert "oracle" in got["why"] and "splicing" in got["why"]
    # and the caller turns that into a MISSING finding rather than a number
    with pytest.raises(KeyError):
        mod.need(got, "all_seeds", "the both-increasing group count")


# --------------------------------------------------------------------------- the check itself
@needs_deposits
def test_hand_transcribed_displays_agree_with_their_artifacts():
    """Every bound numeral in the ledger, the run-family row and the nine captions.

    A failure here prints the display, the numeral, the artifact and both values.  Read the output
    before touching either side: the printed number may be right and the generator wrong.
    """
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO, capture_output=True, text=True,
        env={**os.environ, "KMP_DUPLICATE_LIB_OK": "TRUE"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@needs_deposits
def test_every_numeral_in_those_displays_is_accounted_for():
    """No numeral in the enrolled displays is unregistered -- bound or declared, never neither."""
    # AGAINST THE RUN OF RECORD, 2026-08-18.  This pointed at PUBLISHED_ROOT, and once the paper's
    # displays moved to the five-seed re-run that made it a coverage test on a tree the paper does
    # not report: the numerals stayed registered, so the two assertions that matter still held, but
    # the OK floor fell to 29 and the test went red for the one reason it was not written to catch.
    mod = _load(SCRIPT, "check_displays_cover")
    args = mod.argparse.Namespace(
        root=str(mod.RERUN_ROOT), published_root=str(mod.PUBLISHED_ROOT),
        seeds=None, published_seeds=None, ranking_json=None, paper="paper",
        rerun_landed="no", json=None, verbose=False, dump_unclaimed=False)
    ctx = mod.build_context(args)
    findings = mod.run_checks(ctx)
    unregistered = [f for f in findings if f.severity == "UNREGISTERED"]
    stale = [f for f in findings if f.severity == "STALE"]
    assert not unregistered, "\n".join(f"{f.display}: {f.item} -- {f.note}" for f in unregistered)
    assert not stale, "\n".join(f"{f.display}: {f.item}" for f in stale)
    assert sum(1 for f in findings if f.severity == "OK") > 40


@needs_deposits
def test_the_caption_rule_activates_when_a_re_run_lands():
    """Told no re-run landed the rule is PENDING; told one did, every caption is decided by it.

    REWRITTEN 2026-08-18, when the thing it asserted stopped being true.  It used to require all
    nine to MISMATCH under ``--rerun-landed yes``, which was right while no caption named the
    re-run and became a test that the discharge had NOT happened the moment it did.  What the rule
    is for is that no caption stays advisory once the seeds are in, so that is what is asserted:
    nine findings, none of them PENDING, and against the run of record all nine pass.
    """
    mod = _load(SCRIPT, "check_displays_caps")
    base = dict(root=str(mod.RERUN_ROOT), published_root=str(mod.PUBLISHED_ROOT),
                seeds=None, published_seeds=None, ranking_json=None, paper="paper",
                json=None, verbose=False, dump_unclaimed=False)

    pending = mod.caption_checks(mod.build_context(
        mod.argparse.Namespace(**base, rerun_landed="no")))
    rule = [f for f in pending if "rule" in f.item]
    assert len(rule) == 9, "the rule governs seven floats plus the two map captions"
    assert all(f.severity == "PENDING" for f in rule)

    required = mod.caption_checks(mod.build_context(
        mod.argparse.Namespace(**base, rerun_landed="yes")))
    rule = [f for f in required if "rule" in f.item]
    assert len(rule) == 9
    assert not [f for f in rule if f.severity == "PENDING"], (
        "with a re-run landed the rule is not advisory: every one of the nine must be decided"
    )
    assert all(f.severity == "OK" for f in rule), "\n".join(
        f"{f.display}: {f.printed}" for f in rule if f.severity != "OK")
