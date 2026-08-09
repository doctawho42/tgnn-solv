"""The chemistry maps get a mechanical gate on every cell they print.

SI Sec. "Chemistry-resolved structure of the asymptotic physics penalty" prints seventeen
values across Tables S21 and S22. Until `scripts/analysis/run_e5_chemistry_map.py` existed
every one of them occurred nowhere in the repository except `paper/sections/chemistry-map.tex`
-- no CSV, no JSON, no command -- so a wrong digit in any of them passed every automatic
check the repository had.

These tests pin the generator against the published per-row tree at the decimal the paper
prints. TWO OF THE SEVENTEEN WERE ASSERTED AS INEQUALITIES WHEN THIS FILE WAS FIRST WRITTEN,
because they did not reproduce. Both have since been settled, on 2026-08-10, and the
inequalities are gone:

  * the nitrile cell printed +0.21 where the data give +0.2048. That was a last-digit slip in
    the table and the table was repaired to +0.20; this file now asserts the equality, so a
    drift back to +0.21 fails here.
  * the "Charged / salt" cell was written off as having no recoverable class definition, on the
    argument that the one mask reproducing it excludes every formally charged solute. The
    argument was wrong -- see `test_charged_salt_is_recoverable_and_the_write_off_was_wrong` --
    and the cell is now assigned, checked and regenerable like its neighbours.

Banking a negative needs the discipline of banking a positive: an inequality asserted as a
finding must be re-examined when the thing it rests on moves, not left to harden. If the
leak-free re-run lands and these are re-derived, update the expectations here in the same
commit as the .tex, so the two can never disagree unnoticed.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "analysis" / "run_e5_chemistry_map.py"
_ROOT = _REPO / "results" / "e5_sigma_grounding"
_TRAIN = _REPO / "notebooks" / "data" / "processed" / "train.csv"

_REQUIRED = [
    _ROOT / f"seed_{seed}" / f"{arm}_predictions.csv"
    for seed in (42, 43, 44)
    for arm in ("directgnn", "grounded_a")
] + [_TRAIN]

pytestmark = pytest.mark.skipif(
    not all(p.is_file() for p in _REQUIRED),
    reason="published e5 per-row predictions / processed train split not present",
)


@pytest.fixture(scope="module")
def mapped():
    spec = importlib.util.spec_from_file_location("_e5_chem_map", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = argparse.Namespace(
        root=str(_ROOT),
        control_root=None,
        control_seeds=None,
        seeds=[42, 43, 44],
        control_arm="directgnn",
        physics_arm="grounded_a",
        lock_arms=None,
        train_csv=str(_TRAIN),
        morgan_radius=2,
        morgan_n_bits=2048,
        novel_cut=0.3,
        familiar_cut=0.8,
        salt_def=module.DEFAULT_SALT_DEF,
    )
    return module, module.build(args)


def _mean2(out, key):
    return round(out[key]["mean"], 2)


def test_row_lock_is_the_published_5608(mapped):
    _, out = mapped
    assert out["n_locked"] == 5608


def test_arm_means_and_global_delta(mapped):
    """The section's own header numbers: 1.70 +/- 0.03, 1.85 +/- 0.05, +0.14, span 0.05-0.25."""
    _, out = mapped
    control, physics = out["arm/control_mae"], out["arm/physics_mae"]
    # the two arm means print population sd; every table cell prints sample sd.
    assert (round(control["mean"], 2), round(control["sd_population"], 2)) == (1.70, 0.03)
    assert (round(physics["mean"], 2), round(physics["sd_population"], 2)) == (1.85, 0.05)
    assert _mean2(out, "global/delta_mae") == 0.14
    per_seed = sorted(round(x, 2) for x in out["global/delta_mae"]["per_seed"])
    assert (per_seed[0], per_seed[-1]) == (0.05, 0.25)
    # the footnote's point: the rounded pair differs by 0.15, the unrounded one by 0.14.
    assert round(round(physics["mean"], 2) - round(control["mean"], 2), 2) == 0.15


@pytest.mark.parametrize(
    "cls,mean,sd",
    [
        ("water", 0.52, 0.35),
        ("carboxylic_acid", 0.39, 0.16),
        ("sulfoxide", 0.26, 0.24),
        ("alcohol", 0.15, 0.14),
        ("aromatic", 0.03, 0.63),
        ("hydrocarbon", 0.02, 0.50),
        ("halogenated", -0.29, 0.36),
        ("amide", -0.22, 0.11),
    ],
)
def test_solvent_map_cells(mapped, cls, mean, sd):
    _, out = mapped
    cell = out[f"solvent/{cls}"]
    assert (round(cell["mean"], 2), round(cell["sd"], 2)) == (mean, sd)


def test_nitrile_cell_reproduces_the_repaired_value(mapped):
    """Table S21 printed +0.21 +/- 0.19 until 2026-08-10; the data give +0.2048, i.e. +0.20.

    The sd was always right and the stratum is acetonitrile alone, so this was a last-digit slip
    and not a class-definition question: the value misses the 0.205 rounding boundary by 2e-4.
    The table now prints +0.20 and this asserts it, so a drift back fails here.
    """
    _, out = mapped
    cell = out["solvent/nitrile"]
    assert (round(cell["mean"], 2), round(cell["sd"], 2)) == (0.20, 0.19)
    assert cell["n_rows"] == 252  # acetonitrile alone
    # the rule that WOULD have given +0.21 -- rounding each seed before averaging -- is not the
    # table's rule, and this is the check that says so rather than the prose claiming it.
    rounded_first = round(sum(round(v, 2) for v in cell["per_seed"]) / len(cell["per_seed"]), 2)
    assert rounded_first == 0.21
    for other, printed in (("water", 0.52), ("amide", -0.22)):
        c = out[f"solvent/{other}"]
        assert round(sum(round(v, 2) for v in c["per_seed"]) / len(c["per_seed"]), 2) != printed


@pytest.mark.parametrize(
    "cls,mean",
    [("oxygenated", 0.32), ("polyaromatic", 0.27), ("heterocycle", 0.17)],
)
def test_solute_map_point_estimates(mapped, cls, mean):
    _, out = mapped
    assert _mean2(out, f"solute/{cls}") == mean


def test_halogenated_aromatic_is_the_approximately_zero_cell(mapped):
    _, out = mapped
    assert abs(out["solute/halogenated_aromatic"]["mean"]) <= 0.05


@pytest.mark.parametrize(
    "stratum,mean,sd",
    [("tanimoto_le_0.3", -0.04, 0.18), ("tanimoto_gt_0.8", 0.51, 0.09)],
)
def test_novelty_strata(mapped, stratum, mean, sd):
    """Morgan r=2, 2048 bits, max similarity to the train solutes -- the definition that fits."""
    _, out = mapped
    cell = out[f"novelty/{stratum}"]
    assert (round(cell["mean"], 2), round(cell["sd"], 2)) == (mean, sd)


def test_charged_salt_is_recoverable_and_the_write_off_was_wrong(mapped):
    r"""Table S22's -0.04 +/- 0.19 IS recoverable: `multifrag_neutral`, and nothing else.

    This cell was recorded on 2026-08-10 as unregenerable *in principle*, on the argument that
    the one mask reproducing it "excludes every solute carrying a formal charge, so it cannot be
    what a row named Charged / salt means". That argument does not survive enumerating the
    solutes it is about. In this corpus a formal charge is mostly the internal separation RDKit
    writes for a nitro group on a neutral molecule: of the 31 formally-charged solutes on the
    locked rows, 18 have every fragment net-neutral. The 13 that carry a net-charged fragment are
    exactly `explicit_salt` -- salts written WITH their charges -- and the mask selects the same
    chemistry written WITHOUT them: hydrochlorides, tosylates, a phosphate, a malate, hydrates.

    What the mask does exclude is the explicit spelling, so the printed row is the un-ionised
    salts and not the union of both spellings; that is asserted here too, because a recovered
    definition that quietly over-reaches is the next version of the same defect.
    """
    module, out = mapped
    assert module.DEFAULT_SALT_DEF == "multifrag_neutral"
    cell = out["solute/charged_salt"]
    assert cell["definition"] == "multifrag_neutral"
    assert (round(cell["mean"], 2), round(cell["sd"], 2)) == (-0.04, 0.19)
    assert cell["n_rows"] == 416
    # it is the ONLY candidate that reproduces the printed pair -- that is what makes the
    # assignment a recovery and not a choice among several fits.
    for defn in ("any_charge", "multifrag", "explicit_salt", "charged_or_salt"):
        other = out[f"salt_candidate/{defn}"]
        assert (round(other["mean"], 2), round(other["sd"], 2)) != (-0.04, 0.19), defn

    # the refutation itself: formal charge is not ionicity here.
    audit = out["salt_audit/formal_charge_is_not_ionicity"]
    assert audit["any_charge_solutes"] == 31
    assert audit["every_fragment_net_neutral_solutes"] == 18
    assert audit["net_charged_fragment_solutes"] == 13
    assert audit["every_fragment_net_neutral_rows"] > 0
    # the ions are precisely the explicitly-written salts, which is why excluding formal charge
    # does not exclude "every charged solute" -- it excludes nitro compounds and one spelling.
    assert audit["net_charged_fragment_rows"] == out["salt_candidate/explicit_salt"]["n_rows"]
    assert set(module.SALT_DEFS) >= {"explicit_salt", "multifrag_neutral"}


def test_the_charged_salt_row_is_not_the_union_of_both_salt_spellings(mapped):
    """The recovered definition is stated, so what it leaves out is stated with it."""
    _, out = mapped
    union = out["salt_candidate/multifrag"]
    assert union["n_rows"] == (out["solute/charged_salt"]["n_rows"]
                               + out["salt_candidate/explicit_salt"]["n_rows"])
    assert round(union["mean"], 2) != round(out["solute/charged_salt"]["mean"], 2)


def test_salt_def_all_still_assigns_nothing(mapped):
    """The pre-2026-08-10 behaviour is kept reachable, and is no longer the default."""
    import argparse as _argparse
    module, _ = mapped
    args = _argparse.Namespace(
        root=str(_ROOT), control_root=None, control_seeds=None, seeds=[42, 43, 44],
        control_arm="directgnn", physics_arm="grounded_a", lock_arms=None,
        train_csv=str(_TRAIN), morgan_radius=2, morgan_n_bits=2048,
        novel_cut=0.3, familiar_cut=0.8, salt_def="all")
    out = module.build(args)
    assert "solute/charged_salt" not in out
    assert out["salt_candidate/multifrag_neutral"]["n_rows"] == 416


def test_both_taxonomies_partition_the_locked_rows(mapped):
    """A map that resolves +0.14 must recombine to it; and the printed cells are not the whole set."""
    _, out = mapped
    for axis, unprinted in (("solvent", 1240), ("solute", 501)):
        cons = out["conservation"][axis]
        assert cons["partitions_locked_rows"]
        assert cons["max_abs_deviation_from_global"] < 1e-12
        assert cons["n_rows_in_unprinted_classes"] == unprinted


# ------------------------------------------------- the seed lists of the two sides


def test_seeds_are_discovered_from_the_tree(mapped, tmp_path):
    """A hard-coded default is how a five-seed tree gets read as three and nothing says so."""
    module, _ = mapped
    for seed in (42, 43, 44, 45, 46):
        d = tmp_path / f"seed_{seed}"
        d.mkdir()
        (d / "grounded_a_predictions.csv").write_text("solute_smiles\n")
    assert module.discover_seeds(tmp_path) == [42, 43, 44, 45, 46]
    (tmp_path / "seed_47").mkdir()  # a directory with no deposits is not a seed
    assert module.discover_seeds(tmp_path) == [42, 43, 44, 45, 46]


def test_a_repeated_control_seed_is_refused(mapped):
    """`--control-seeds 42 43 44 42 43` padded three control runs out to five by counting two
    of them twice, and moved the published DirectGNN cell from 1.70 +/- 0.03 to 1.71 +/- 0.04
    -- a cell whose disposition is that it does not move.  It is an error now, not padding."""
    module, _ = mapped
    with pytest.raises(SystemExit) as exc:
        module._distinct([42, 43, 44, 42, 43], "--control-seeds")
    assert "repeats [42, 43]" in str(exc.value)
    assert module._distinct([42, 43, 44], "--control-seeds") == [42, 43, 44]


def test_pooling_the_control_leaves_its_published_mean_and_sd_where_they_were(mapped):
    """Five physics seeds against three control seeds: the control is pooled, not padded.

    The control's printed mean and sd must be over its own three seeds -- exactly the published
    1.7022 / 0.0330 -- and every cell's spread must be the physics side's alone, which is what
    the two map captions are required to say once the re-run lands.
    """
    module, three = mapped
    args = argparse.Namespace(
        root=str(_ROOT), control_root=str(_ROOT), control_seeds=[42, 43, 44],
        seeds=[42, 43, 44, 42, 43], control_arm="directgnn", physics_arm="grounded_a",
        lock_arms=None, train_csv=str(_TRAIN), morgan_radius=2, morgan_n_bits=2048,
        novel_cut=0.3, familiar_cut=0.8, salt_def="all")
    with pytest.raises(SystemExit):
        module.build(args)          # a repeat on the physics side is refused just the same

    args.seeds = [42, 43, 44]
    args.control_seeds = [43, 42, 44]   # same set, different order -> pooled, not paired
    out = module.build(args)
    assert out["control_pairing"] == "control pooled over its own seeds"
    assert out["arm/control_mae"]["mean"] == pytest.approx(
        three["arm/control_mae"]["mean"], abs=1e-12)
    assert out["arm/control_mae"]["sd_population"] == pytest.approx(
        three["arm/control_mae"]["sd_population"], abs=1e-12)
    # pooled: the physics spread alone, so the global delta's sd is the physics arm's sd
    assert out["global/delta_mae"]["sd_population"] == pytest.approx(
        out["arm/physics_mae"]["sd_population"], abs=1e-12)
    # and the point estimate is untouched by the pairing rule
    assert out["global/delta_mae"]["mean"] == pytest.approx(
        three["global/delta_mae"]["mean"], abs=1e-12)
