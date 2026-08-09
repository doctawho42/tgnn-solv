r"""Gate on Table S3 (``\label{tab:si-arms}``), the source of record for six of the derived
numbers the manuscript quotes.

Two of these tests need the per-row prediction CSVs, which are ~5 MB each and gitignored, so
they skip on a fresh clone.  The rest -- the standard-deviation convention and the child-row
pin -- run everywhere, because the ``\pm`` convention is the one that has been got backwards
before and it should not be guarded only where 100 MB of artifacts happen to be present.

The artifact-gated tests take the tree to check from the generated file's own ``% ROOT:``
header, so when the leak-free CSVs land and the table is regenerated with ``--root
results/e5_sigma_grounding_leakfree`` this gate follows it without being edited.

NO GATE HERE SKIPS BECAUSE THE TREE CHANGED.  Both of the tests below used to open with
``if summary["root"] != PUBLISHED_ROOT: pytest.skip(...)``, which stood the gates down at
precisely the moment they were needed: the four-decimal mean list, the NRTL rounding note, the
``0.177``/``0.428``/``0.59`` sentence and the ``0.83``/``0.61`` pair are hand-transcribed, and
the one edit that will ever rewrite them is the five-seed substitution -- the same edit that
repoints ``% ROOT:`` away from the published tree.  So the assertions are now split by what they
are actually about.  Everything the prose reads OFF THE TABLE is checked against the regenerated
summary whatever tree it names.  The published constants below are asserted only for the arms
the re-run does not retrain, which stand as printed by disposition and must therefore keep their
values on every tree, plus the whole table when the tree is the published one.  Where a sentence
genuinely cannot survive a five-seed rewrite unchanged, the test fails asking to be re-pointed;
it never passes by not running.
"""
from __future__ import annotations

import importlib
import math
from pathlib import Path

import pytest

m = importlib.import_module("scripts.analysis.make_si_arms_table")

REPO = Path(__file__).resolve().parents[1]
ROWS_TEX = REPO / "paper" / "si_tables" / "si_arms_rows.tex"
PUBLISHED_ROOT = "results/e5_sigma_grounding"
PUBLISHED_ROOT_PATH = REPO / PUBLISHED_ROOT

# The three arms the leak-free re-run does not retrain.  The inventory's disposition is that
# they stand as printed, so their values must hold whatever tree the rows file names -- and a
# table that has lost them is the defect `make_si_arms_table` now refuses to emit.
NOT_RETRAINED = ("directgnn", "nrtl", "grounded_b")

# The values printed today, at the precision they are printed at.  MAE mean, population sd.
PUBLISHED_MAE = {
    "directgnn": (1.7022, 0.0330),
    "nrtl": (1.7950, 0.0705),
    "grounded_a": (1.8457, 0.0535),
    "grounded_b": (1.8788, 0.0910),
    "ungrounded": (2.0434, 0.0397),
    "oracle": (2.2517, 0.0214),
}
# Single-seed oracle-application controls, valued in S3's prose as 1.98 and 2.08.
PUBLISHED_CONTROLS_SEED42 = {"grounded_a_truetrain": 1.9806, "channel_swap": 2.0780}


def _fake_arm(label, mae_per_seed, r2_per_seed, seeds):
    import numpy as np
    return {
        "label": label,
        "mae_mean": float(np.mean(mae_per_seed)), "mae_sd_population": m._pop_sd(mae_per_seed),
        "r2_mean": float(np.mean(r2_per_seed)), "r2_sd_population": m._pop_sd(r2_per_seed),
        "mae_per_seed": {str(s): v for s, v in zip(seeds, mae_per_seed)},
        "r2_per_seed": {str(s): v for s, v in zip(seeds, r2_per_seed)},
        "n_per_seed": {str(s): 10 for s in seeds},
    }


def test_pm_is_a_population_sd_not_a_sample_one():
    # [1,2,3]: population sd = sqrt(2/3) = 0.8165, sample sd = 1.0.  A sample sd is larger by
    # sqrt(k/(k-1)); printing one where the caption promises the other is the mistake this
    # project has already made once.
    assert m._pop_sd([1.0, 2.0, 3.0]) == pytest.approx(math.sqrt(2.0 / 3.0), abs=1e-12)
    assert m._pop_sd([1.0, 2.0, 3.0]) != pytest.approx(1.0, abs=1e-6)


def test_rows_round_once_from_the_unrounded_values():
    seeds = [42, 43, 44]
    summary = {
        "root": PUBLISHED_ROOT, "seeds": seeds, "n_locked": [5608], "lock_arms": ["nrtl"],
        # NRTL is the row where the two roundings part: the printed triple averages to 1.7953
        # (-> 1.80) while the arm's own mean is 1.794975 (-> 1.79).  The mean must come from
        # the unrounded values, never from the column beside it.
        "arms": {"nrtl": _fake_arm("NRTL closure", [1.733532, 1.757623, 1.893770],
                                   [0.38213, 0.346154, 0.298154], seeds)},
    }
    row = [ln for ln in m.render_tex(summary).splitlines()
           if ln.startswith("NRTL closure")][0]
    assert r"$1.79\pm0.07$" in row
    assert r"$1.80\pm" not in row
    assert "$1.734/1.758/1.894$" in row


def test_child_row_is_pinned_under_its_parent_and_the_header_says_so():
    seeds = [42, 43]
    summary = {
        "root": PUBLISHED_ROOT, "seeds": seeds, "n_locked": [10],
        "lock_arms": ["grounded_a", "grounded_b", "oracle"],
        "arms": {
            # grounded_b sorts BEFORE grounded_a here, so the pin has to move it.
            "grounded_a": _fake_arm("learned", [2.0, 2.0], [0.3, 0.3], seeds),
            "grounded_b": _fake_arm(r"\quad $+$ comb", [1.0, 1.0], [0.4, 0.4], seeds),
            "oracle": _fake_arm("oracle", [3.0, 3.0], [0.0, 0.0], seeds),
        },
    }
    tex = m.render_tex(summary)
    body = [ln for ln in tex.splitlines() if not ln.startswith("%") and "&" in ln]
    labels = [ln.split("&")[0].strip() for ln in body[1:]]  # drop the column header
    assert labels == ["learned", r"\quad $+$ comb", "oracle"]
    assert "pinned under its parent" in tex


def test_header_round_trips_root_and_seeds():
    text = "% ROOT: results/x\n% SEEDS: 42,43,44,45,46\nArm & MAE \\\\\n"
    assert m.parse_header(text) == {"root": "results/x", "seeds": [42, 43, 44, 45, 46]}


def test_an_arm_in_neither_tree_stops_the_script(tmp_path):
    """A printed row of Table S3 may not leave the table because a tree does not hold it.

    Pointed at the leak-free tree -- which trains the ungrounded, grounded and sigma-oracle arms
    and nothing else -- the generator used to emit a THREE-row table, deleting DirectGNN, NRTL
    and the +SG row with no warning on stdout and none in the generated header.
    """
    (tmp_path / "seed_42").mkdir()
    (tmp_path / "seed_42" / "ungrounded_predictions.csv").write_text("x\n")
    with pytest.raises(SystemExit) as exc:
        m.collect(tmp_path, [42], published_root=None)
    for arm in ("directgnn", "nrtl", "grounded_b"):
        assert arm in str(exc.value)
    assert "silently" in str(exc.value)


def test_rows_carry_their_own_seed_list_into_the_per_seed_column():
    """Two trees, two seed lists: the column header can no longer name one, and says so."""
    seeds = [42, 43, 44, 45, 46]
    summary = {
        "root": "results/leakfree", "published_root": PUBLISHED_ROOT, "seeds": seeds,
        "published_seeds": [42, 43, 44], "n_locked": [5608], "lock_arms": ["grounded_a"],
        "lock_arms_by_tree": {"results/leakfree": ["grounded_a"], PUBLISHED_ROOT: ["directgnn"]},
        "lock_check": {"identical": True, "differences": []},
        "arms_from_published_root": ["directgnn"],
        "arms": {
            "grounded_a": _fake_arm("grounded", [1.8] * 5, [0.3] * 5, seeds),
            "directgnn": _fake_arm("DirectGNN", [1.7] * 3, [0.4] * 3, [42, 43, 44]),
        },
    }
    summary["arms"]["grounded_a"]["seeds"] = seeds
    summary["arms"]["directgnn"]["seeds"] = [42, 43, 44]
    tex = m.render_tex(summary)
    assert "per-seed MAE \\\\" in tex, "a single seed list must not be claimed for both rows"
    assert "different seed list per row" in tex
    assert "stand as printed: directgnn" in tex
    assert "identical key set in every seed" in tex
    directgnn = [ln for ln in tex.splitlines() if ln.startswith("DirectGNN")][0]
    assert "$1.700/1.700/1.700$" in directgnn


# ---------------------------------------------------------------- artifact-gated


def _root_from_committed_file():
    if not ROWS_TEX.exists():
        pytest.skip(f"{ROWS_TEX} not generated")
    head = m.parse_header(ROWS_TEX.read_text())
    root = REPO / str(head["root"])
    seeds = list(head["seeds"])
    missing = [f"{root}/seed_{s}" for s in seeds
               if not (root / f"seed_{s}" / "grounded_a_predictions.csv").exists()]
    if root != PUBLISHED_ROOT_PATH:
        # the not-retrained rows come from the published tree, so it is needed too
        missing += [f"{PUBLISHED_ROOT_PATH}/seed_{s}"
                    for s in m.discover_seeds(PUBLISHED_ROOT_PATH)
                    if not (PUBLISHED_ROOT_PATH / f"seed_{s}"
                            / "directgnn_predictions.csv").exists()]
        if not m.discover_seeds(PUBLISHED_ROOT_PATH):
            missing.append(str(PUBLISHED_ROOT_PATH))
    if missing:
        pytest.skip(f"per-row prediction CSVs absent: {missing} (gitignored, ~5 MB each)")
    return root, seeds


@pytest.fixture(scope="module")
def regenerated():
    root, seeds = _root_from_committed_file()
    return root, seeds, m.collect(root, seeds, published_root=PUBLISHED_ROOT_PATH)


def test_committed_rows_reproduce_from_the_tree_they_name(regenerated):
    _, _, summary = regenerated
    assert m._normalise(m.render_tex(summary)) == m._normalise(ROWS_TEX.read_text())


def test_the_rows_the_re_run_does_not_retrain_keep_their_published_values(regenerated):
    """DirectGNN, NRTL, +SG and the two seed-42 controls, on any tree the rows file names.

    Their disposition is that they stand as printed, so a tree change must not move them and
    must not lose them.  This is the assertion that used to be skipped away the moment ``%
    ROOT:`` stopped saying ``results/e5_sigma_grounding`` -- which is also the moment a
    generator that silently drops the rows would have gone unnoticed.
    """
    _, _, summary = regenerated
    for key in NOT_RETRAINED:
        assert key in summary["arms"], (
            f"{key} is a printed row of Table S3 and is not in the generated table; a re-run "
            "tree does not retrain it, so it must be sourced from --published-root")
        arm = summary["arms"][key]
        mae, sd = PUBLISHED_MAE[key]
        assert arm["mae_mean"] == pytest.approx(mae, abs=5e-5), key
        assert arm["mae_sd_population"] == pytest.approx(sd, abs=5e-5), key
        assert arm["seeds"] == [42, 43, 44], f"{key} is a three-seed published row"
    for key, mae in PUBLISHED_CONTROLS_SEED42.items():
        ctrl = summary["controls"][key]
        assert ctrl["seeds"] == [42], f"{key} is a single-seed control"
        assert ctrl["mae_per_seed"]["42"] == pytest.approx(mae, abs=5e-5), key
    # A row from one tree minus a row from another is a measurement only on a shared lock.
    assert summary["lock_check"]["identical"], summary["lock_check"]["differences"]
    assert summary["n_locked"] == [5608]


def test_published_values_are_the_ones_printed(regenerated):
    """The whole table, but only while the rows file still tracks the published tree.

    Unlike the test above this one IS tree-specific -- the re-run arms are expected to move --
    so on another tree it asserts what must hold there instead: the re-run rows are present,
    they carry that tree's seeds, and the three derived deltas §S3 quotes are computable.  It
    does not skip, because "the constants no longer apply" is not the same as "nothing applies".
    """
    root, seeds, summary = regenerated
    rerun = ("ungrounded", "grounded_a", "oracle")
    if summary["root"] != PUBLISHED_ROOT:
        for key in rerun:
            assert summary["arms"][key]["seeds"] == seeds, key
            assert summary["arms"][key]["source_root"] == summary["root"], key
        for key in ("training_time_grounding_delta_mae",
                    "evaluation_time_substitution_delta_mae", "grounded_minus_directgnn_mae"):
            assert isinstance(summary["derived"][key], float), key
        assert set(summary["arms_from_published_root"]) == set(NOT_RETRAINED)
        return
    assert seeds == [42, 43, 44]
    for key, (mae, sd) in PUBLISHED_MAE.items():
        arm = summary["arms"][key]
        assert arm["mae_mean"] == pytest.approx(mae, abs=5e-5), key
        assert arm["mae_sd_population"] == pytest.approx(sd, abs=5e-5), key
    # the two senses of grounding, as S3 states them
    assert summary["derived"]["training_time_grounding_delta_mae"] == pytest.approx(-0.1977, abs=5e-5)
    assert summary["derived"]["evaluation_time_substitution_delta_mae"] == pytest.approx(0.4059, abs=5e-5)
    assert summary["derived"]["grounded_minus_directgnn_mae"] == pytest.approx(0.1435, abs=5e-5)


def test_the_prose_that_reads_off_the_table_carries_the_same_digits(regenerated):
    r"""§S3 restates the table to four decimals in running prose, and prose is where a wrong
    digit survives: the table is now generated, the sentence below it is still transcribed by
    hand.  This is the gate on that transcription.  If the sentence is rewritten, this test
    fails rather than skips -- a gate that quietly stops applying is worse than none.

    EVERY NUMBER IN THE PATTERNS BELOW IS A CAPTURE GROUP CHECKED AGAINST THE REGENERATED
    SUMMARY, none is baked into the regex.  Three of them used to be (``1.981-1.803``,
    ``2.232-1.803``), which meant the sentence could only be gated for the tree those digits
    came from -- and the test then skipped on every other tree, so re-transcribing the sentence
    for five seeds would have moved it out of reach of the only check that reads it.  The one
    thing still keyed to the published tree is the SHAPE of the sentences; when the shape
    changes the test fails and says which sentence to re-point.
    """
    import re
    _, seeds, summary = regenerated
    text = " ".join((REPO / "paper" / "sections" / "SI.tex").read_text().split())
    arms = summary["arms"]
    order = sorted(arms, key=lambda k: arms[k]["mae_mean"])

    num = r"\$(-?\d+\.\d+)\$"
    bare = r"(-?\d+\.\d+)"
    k = len(order)
    sent = re.search(
        r"To four decimals the means are " + r", ".join([num] * (k - 1)) + r" and " + num
        + r", with population standard deviations " + r", ".join([num] * (k - 1)) + r" and " + num,
        text)
    assert sent is not None, "the four-decimal sentence of S3 changed shape; re-point this gate"
    means, sds = [float(x) for x in sent.groups()[:k]], [float(x) for x in sent.groups()[k:]]
    assert means == [round(arms[a]["mae_mean"], 4) for a in order]
    assert sds == [round(arms[a]["mae_sd_population"], 3) for a in order]

    # the NRTL two-roundings note, and the two senses of grounding
    d = summary["derived"]
    note = re.search(r"averaging its printed per-seed triple gives " + num
                     + r", whose two-decimal form is " + num
                     + r", but the arm's mean is " + num, text)
    assert note is not None, "the NRTL rounding note of S3 changed shape; re-point this gate"
    assert float(note.group(1)) == round(d["nrtl_mean_of_printed_per_seed_triple"], 4)
    assert float(note.group(2)) == round(d["nrtl_mean_of_printed_per_seed_triple"], 2)
    assert float(note.group(3)) == round(d["nrtl_mean_unrounded"], 6)

    # the oracle-control block: the share at the matched seed, both subtractions spelled out
    c = d["single_seed_controls"]
    ref = str(c["seed"])
    ctrl = re.search(r"at seed \$(\d+)\$ the injection costs \$" + bare + r"-" + bare + r"="
                     + bare + r"\$ where the evaluation-only substitution costs \$" + bare
                     + r"-" + bare + r"=" + bare + r"\$, a share of " + num, text)
    assert ctrl is not None, "the seed-42 share sentence of S3 changed shape; re-point this gate"
    g = ctrl.groups()
    inj = summary["controls"]["grounded_a_truetrain"]["mae_per_seed"][ref]
    assert g[0] == ref, "the share is quoted at a seed the controls were not run at"
    assert float(g[1]) == round(inj, 3)
    assert float(g[2]) == float(g[5]) == round(c["learned_sigma_mae"], 3)
    assert float(g[3]) == round(c["training_time_injection_gap"], 3)
    assert float(g[4]) == round(arms["oracle"]["mae_per_seed"][ref], 3)
    assert float(g[6]) == round(c["evaluation_only_gap"], 3)
    assert float(g[7]) == round(c["share_coadaptation_removes"], 2)

    # ... the sensitivity S3 quotes on the share, whose two operands are both in this JSON.
    # It was written off as "not a function of the artifacts" and therefore not dischargeable by
    # any generator; it is the learned arm's between-seed range over the evaluation-only gap, and
    # binding it is what stops it standing at 0.118 / +/-0.27 after the five seeds land.
    sens = re.search(r"spread the size of the learned arm's " + num
                     + r" would move the share by about \$\\pm(\d+\.\d+)\$", text)
    assert sens is not None, "the share-sensitivity sentence of S3 changed shape; re-point this gate"
    assert float(sens.group(1)) == round(c["learned_sigma_between_seed_range"], 3)
    assert float(sens.group(2)) == round(c["share_shift_per_learned_arm_sized_spread"], 2)

    # ... and the latitude on it: the injected arm held fixed, read against the other seeds
    other = c["share_holding_injection_against_other_seed_baselines"]
    others = re.search(r"holding the injected arm at " + num + r" and reading it against the "
                       r"seed-\$\d+\$ (?:and|,) [^.]*?learned baselines instead gives "
                       r"((?:\$-?\d+\.\d+\$(?:,? and | *, *)?)+)", text)
    assert others is not None, "the other-seed baseline sentence of S3 changed shape"
    assert float(others.group(1)) == round(inj, 3)
    quoted = [float(x) for x in re.findall(r"\$(-?\d+\.\d+)\$", others.group(2))]
    assert quoted == [round(v, 2) for v in other.values()], (
        f"the sentence quotes {quoted} against {len(seeds) - 1} other seeds in the tree")

    senses = re.search(r"training-time supervision moves the arm from " + num + r" to " + num
                       + r" \(helps, " + num + r"\), evaluation-time substitution from " + num
                       + r" to " + num + r" \(hurts, \$\+(\d+\.\d+)\$\)", text)
    assert senses is not None, "the two-senses sentence of S3 changed shape; re-point this gate"
    got = [float(x) for x in senses.groups()]
    assert got[0] == round(arms["ungrounded"]["mae_mean"], 4)
    assert got[1] == got[3] == round(arms["grounded_a"]["mae_mean"], 4)
    assert got[4] == round(arms["oracle"]["mae_mean"], 4)
    assert got[2] == round(d["training_time_grounding_delta_mae"], 2)
    assert got[5] == round(d["evaluation_time_substitution_delta_mae"], 2)


def test_arms_absent_from_root_are_sourced_from_the_published_tree(tmp_path):
    """A stand-in re-run tree holding only the physics arm still emits the DirectGNN row.

    The tree is built by symlink from the published deposits, so this asserts the plumbing --
    which tree each row is read from, and that the two locks agree -- and not the values.
    """
    root, seeds = _root_from_committed_file()
    if root != PUBLISHED_ROOT_PATH:
        pytest.skip("the committed rows file already tracks a re-run tree")
    rerun = tmp_path / "rerun"
    for seed in seeds:
        (rerun / f"seed_{seed}").mkdir(parents=True)
        (rerun / f"seed_{seed}" / "grounded_a_predictions.csv").symlink_to(
            root / f"seed_{seed}" / "grounded_a_predictions.csv")
    two = (("directgnn", "DirectGNN (no closure)"), ("grounded_a", "grounded"))
    summary = m.collect(rerun, seeds, arms=two, controls=(), published_root=root)
    assert set(summary["arms"]) == {"directgnn", "grounded_a"}
    assert summary["arms_from_published_root"] == ["directgnn"]
    assert summary["arms"]["directgnn"]["source_root"] == PUBLISHED_ROOT
    assert summary["arms"]["grounded_a"]["source_root"] == m._rel(rerun)
    assert summary["lock_check"]["identical"], summary["lock_check"]["differences"]
    assert summary["arms"]["directgnn"]["mae_mean"] == pytest.approx(
        PUBLISHED_MAE["directgnn"][0], abs=5e-5)


def test_controls_are_scored_on_the_lock_and_never_join_it(regenerated):
    _, _, summary = regenerated
    # A control in the lock could only remove rows, moving every row of the table to value
    # two lines of prose.  The lock arms are the table's arms and nothing else.
    assert set(summary["lock_arms"]).isdisjoint(summary["controls"])
    n = set(summary["n_locked"])
    for ctrl in summary["controls"].values():
        assert set(ctrl["n_per_seed"].values()) <= n
