r"""Write the rows of Table S3 (``\label{tab:si-arms}``) from the per-row prediction CSVs.

Table S3 is the source of record for six of the derived numbers §2/§3 quote, and until now
nothing wrote it: ``results/e5_sigma_grounding/THREE_SEED_SUMMARY.md`` documents the recipe
("re-run ``run_e5_comparison.py`` per seed, then average ``per_arm``") but is itself
hand-written, and so is the printed table.  This script is that recipe, executed.

WHAT IT LOCKS ON.  The row set is not recomputed here.  ``run_e5_comparison.py`` is imported
by path and its ``intersection_keys`` / ``_metrics_on_keys`` are called unmodified, so the
key rounding (``T`` to 6 dp), the supervised-AND-finite conjunction and the cross-arm
intersection are the same code that wrote each seed's ``comparison.json`` -- not a second
implementation that can drift from it.  Read that file's ``_supervised_finite`` docstring
before changing anything here: the ``finite`` half of the conjunction is outcome-dependent
and is inert only as long as no arm predicts a non-finite ``ln_x2``.

THE ``\pm`` IS A POPULATION STANDARD DEVIATION over seeds (``ddof=0``), which is what the SI
and this table's caption state; a sample sd is larger by sqrt(k/(k-1)) (sqrt(3/2) at k=3).
Getting that backwards has already happened once in this project.

PARAMETERISED BY ROOT.  ``--root`` defaults to the published three-seed tree; point it at
``results/e5_sigma_grounding_leakfree`` when those per-row CSVs land and the same command
discharges the re-run.  Seeds are discovered from ``seed_*`` directories, so five seeds need
no flag.  An arm present at some seeds but not all is a hard error, because averaging it over
a different seed set than its neighbours would print a mean whose ``\pm`` spans a different
thing than the row above it.

TWO TREES, BECAUSE THE RE-RUN DOES NOT RETRAIN EVERY ROW.  The leak-free re-run produces the
ungrounded, grounded and sigma-oracle arms and nothing else; DirectGNN, NRTL and the
Staverman--Guggenheim arm are not retrained and the inventory's disposition is that they stand
as printed.  Pointed at the leak-free tree, the first version of this script simply dropped
them: it emitted a THREE-row Table S3, said nothing on stdout, wrote a header that did not
mention the loss, and its own row-reproduction test passed on the truncated table -- three rows
of the paper deleted by a generator whose whole purpose is that the table is no longer
hand-made.  Arms absent from ``--root`` are therefore taken from ``--published-root``, each row
carrying its source tree and its own seed list into the header and the JSON; an arm in neither
tree stops the script instead of vanishing from the table.

That splice is a measurement only if both trees score the same rows -- the ``+0.14`` of the
accuracy row is a difference between an arm in one tree and an arm in the other -- so the two
locks are compared key by key and a difference is fatal unless ``--allow-lock-mismatch`` says
otherwise, in which case it is stamped on the header and the table is no longer a like-for-like
comparison.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/make_si_arms_table.py
    ... --root results/e5_sigma_grounding_leakfree      # when the re-run lands
    ... --check                                          # compare, write nothing, exit 1 on drift
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
_E5_PATH = REPO / "scripts" / "analysis" / "run_e5_comparison.py"

# (arm key = <key>_predictions.csv, LaTeX label).  Rows are ordered by MAE at emit time;
# this order is only the fallback when two arms tie.
ARMS: tuple[tuple[str, str], ...] = (
    ("directgnn", "DirectGNN (no closure)"),
    ("nrtl", "NRTL closure"),
    ("grounded_a", r"COSMO-SAC, learned $\sigma$ (grounded)"),
    ("grounded_b", r"\quad $+$ Staverman--Guggenheim combinatorial"),
    ("ungrounded", r"COSMO-SAC, ungrounded $\sigma$"),
    ("oracle", r"COSMO-SAC, reference $\sigma$ ($\sigma$-oracle)"),
)

# The `+ Staverman--Guggenheim' row is typeset as a child of the learned-sigma row (\quad,
# and a label that reads as a continuation of it), so it is pinned directly beneath its
# parent even if the MAE order would separate them.  On the published tree the pin is inert
# -- grounded_a already sorts immediately before grounded_b -- and the JSON says so either way.
_CHILD_OF = {"grounded_b": "grounded_a"}

# Single-seed oracle-application controls.  They are NOT table rows: the SI values them in
# prose ("training-time injection (MAE 1.98) and the channel swap (MAE 2.08)").  They are
# scored on the lock the table arms define, never intersected into it -- adding an arm to the
# lock can only remove rows, and would move every row of the table to value two lines of text.
CONTROLS: tuple[tuple[str, str], ...] = (
    ("channel_swap", "channel swap"),
    ("grounded_a_truetrain", "training-time injection"),
)


def _load_e5():
    """Import run_e5_comparison.py by path (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("run_e5_comparison", _E5_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise SystemExit(f"cannot import {_E5_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path.resolve())


def discover_seeds(root: Path) -> list[int]:
    seeds = []
    for d in root.glob("seed_*"):
        if d.is_dir() and d.name[5:].isdigit():
            seeds.append(int(d.name[5:]))
    return sorted(seeds)


def _pop_sd(values) -> float:
    return float(np.std(np.asarray(values, dtype=float), ddof=0))


def _seeds_holding(root: Path, key: str, seeds: list[int]) -> list[int]:
    return [s for s in seeds if (root / f"seed_{s}" / f"{key}_predictions.csv").exists()]


def _no_partial(root: Path, present: dict[str, list[int]], seeds: list[int]) -> None:
    partial = {k: v for k, v in present.items() if v and len(v) != len(seeds)}
    if partial:
        raise SystemExit(
            f"make_si_arms_table: under {_rel(root)} these arms exist at some seeds and not "
            "others: " + "; ".join(f"{k} at {v} of {seeds}" for k, v in partial.items())
            + ".  A row averaged over a different seed set than the row above it prints a "
              "mean and a +/- that span different things.  Fetch the missing files, or drop "
              "the arm explicitly with --arms."
        )


def _lock_of_tree(e5, root: Path, seeds: list[int], arms) -> tuple[dict[int, list], list[str]]:
    """This tree's own cross-arm lock, over every table arm the tree holds at all its seeds."""
    lock_arms = [k for k, _ in arms if len(_seeds_holding(root, k, seeds)) == len(seeds)]
    locks: dict[int, list] = {}
    for seed in seeds:
        sd = root / f"seed_{seed}"
        frames = {k: pd.read_csv(sd / f"{k}_predictions.csv") for k in lock_arms}
        keys = e5.intersection_keys(frames)
        if not keys:
            raise SystemExit(
                f"make_si_arms_table: empty cross-arm intersection at seed {seed} of {_rel(root)}")
        locks[seed] = keys
    return locks, lock_arms


def collect(root: Path, seeds: list[int], arms=ARMS, controls=CONTROLS, *,
            published_root: Path | None = None, published_seeds: list[int] | None = None,
            allow_lock_mismatch: bool = False) -> dict:
    """Per-seed, per-arm metrics on each tree's own cross-arm lock.

    Arms the re-run does not produce are read from ``published_root`` at that tree's own seeds:
    see the module docstring on why dropping them instead is the defect this argument exists to
    close.  Pass ``published_root=None`` for the single-tree behaviour.
    """
    e5 = _load_e5()

    present = {key: _seeds_holding(root, key, seeds) for key, _ in arms}
    _no_partial(root, present, seeds)

    pub_root = published_root if published_root and published_root != root else None
    pub_seeds = list(published_seeds or (discover_seeds(pub_root) if pub_root else []))
    pub_present: dict[str, list[int]] = {}
    if pub_root:
        if not pub_seeds:
            raise SystemExit(f"make_si_arms_table: no seed_* directories under {_rel(pub_root)}")
        pub_present = {key: _seeds_holding(pub_root, key, pub_seeds)
                       for key, _ in arms if not present[key]}
        _no_partial(pub_root, pub_present, pub_seeds)

    # Arms the re-run PRODUCES may never be borrowed.  The re-run trains ungrounded and grounded
    # and re-evaluates the grounded checkpoints under the reference profile, so all three are its
    # own output; borrowing one from the published tree would print a published number in a row the
    # inventory says is regenerated, and the two would be indistinguishable on the page.  The
    # sigma-oracle is the live case: it lands after the two trained arms, so a table built in that
    # window silently carried the published value.  DirectGNN, NRTL and the +SG arm are not
    # retrained and their disposition is that they stand as published, so those may be borrowed.
    RERUN_ARMS = {"ungrounded", "grounded_a", "oracle"}
    source: dict[str, tuple[Path, list[int]]] = {}
    borrowed_rerun: list[str] = []
    for key, _ in arms:
        if present[key]:
            source[key] = (root, seeds)
        elif pub_present.get(key):
            if key in RERUN_ARMS and pub_root is not None:
                borrowed_rerun.append(key)
                continue
            source[key] = (pub_root, pub_seeds)
    if borrowed_rerun:
        raise SystemExit(
            f"make_si_arms_table: {borrowed_rerun} is an arm the re-run produces and it is not in "
            f"{_rel(root)}; it exists only in {_rel(pub_root)}.  Refusing to print a published "
            "value in a row the pre-commitment says is regenerated.  Run the arm, or build the "
            "table against the published tree alone."
        )
    missing = [k for k, _ in arms if k not in source]
    if missing:
        where = f"{_rel(root)}" + (f" or {_rel(pub_root)}" if pub_root else "")
        raise SystemExit(
            f"make_si_arms_table: no prediction CSVs for {missing} under {where}.  These are rows "
            "of Table S3 as printed; emitting the table without them would delete published rows "
            "silently, which is what this check exists to stop.  Point --published-root at the "
            "tree that holds them, or drop them deliberately with --arms."
        )
    table_arms = [(k, lab) for k, lab in arms if k in source]

    trees: list[tuple[Path, list[int]]] = [(root, seeds)]
    if any(t == pub_root for t, _ in source.values()):
        trees.append((pub_root, pub_seeds))
    locks: dict[Path, dict[int, list]] = {}
    lock_arms: dict[Path, list[str]] = {}
    for tree, tree_seeds in trees:
        locks[tree], lock_arms[tree] = _lock_of_tree(e5, tree, tree_seeds, arms)

    # The splice is a measurement only if both trees score the same rows.
    lock_check: dict[str, object] = {"trees": [_rel(t) for t in locks]}
    if len(locks) > 1:
        ref_tree = root
        ref = set(locks[ref_tree][seeds[0]])
        bad = []
        for tree, per_seed_keys in locks.items():
            for seed, keys in per_seed_keys.items():
                if set(keys) != ref:
                    bad.append(f"{_rel(tree)}/seed_{seed}: "
                               f"+{len(set(keys) - ref)}/-{len(ref - set(keys))} keys")
        lock_check["identical"] = not bad
        lock_check["differences"] = bad
        if bad and not allow_lock_mismatch:
            raise SystemExit(
                "make_si_arms_table: the two trees do not lock the same rows -- "
                + "; ".join(bad)
                + f".  Rows sourced from {_rel(pub_root)} would then be averaged over a different "
                  "row set than the rows above them, and the grounded-minus-DirectGNN difference "
                  "S3 quotes would not be a measurement.  Re-derive the lock, or pass "
                  "--allow-lock-mismatch to emit it with the discrepancy stamped on the header."
            )
    else:
        lock_check["identical"] = True
        lock_check["differences"] = []

    ctrl_source: dict[str, tuple[Path, list[int]]] = {}
    for key, _ in controls:
        for tree, tree_seeds in ((root, seeds), *(((pub_root, pub_seeds),) if pub_root else ())):
            hits = _seeds_holding(tree, key, tree_seeds)
            if hits:
                ctrl_source[key] = (tree, hits)
                break

    agg = {}
    for key, label in table_arms:
        tree, tree_seeds = source[key]
        met = {s: e5._metrics_on_keys(
            pd.read_csv(tree / f"seed_{s}" / f"{key}_predictions.csv"), locks[tree][s])
            for s in tree_seeds}
        mae = [met[s]["mae"] for s in tree_seeds]
        r2 = [met[s]["r2"] for s in tree_seeds]
        agg[key] = {
            "label": label,
            "source_root": _rel(tree),
            "seeds": list(tree_seeds),
            "mae_mean": float(np.mean(mae)), "mae_sd_population": _pop_sd(mae),
            "r2_mean": float(np.mean(r2)), "r2_sd_population": _pop_sd(r2),
            "mae_per_seed": {str(s): m for s, m in zip(tree_seeds, mae)},
            "r2_per_seed": {str(s): v for s, v in zip(tree_seeds, r2)},
            "n_per_seed": {str(s): met[s]["n"] for s in tree_seeds},
        }

    ctrl = {}
    for key, label in controls:
        if key not in ctrl_source:
            continue
        tree, hits = ctrl_source[key]
        met = {s: e5._metrics_on_keys(
            pd.read_csv(tree / f"seed_{s}" / f"{key}_predictions.csv"), locks[tree][s])
            for s in hits}
        ctrl[key] = {
            "label": label,
            "source_root": _rel(tree),
            "seeds": hits,
            "mae_per_seed": {str(s): met[s]["mae"] for s in hits},
            "r2_per_seed": {str(s): met[s]["r2"] for s in hits},
            "n_per_seed": {str(s): met[s]["n"] for s in hits},
            "scored_on": "the lock the table arms define; the control is not in the lock",
        }

    n_locked = {len(k) for per in locks.values() for k in per.values()}
    return {
        "root": _rel(root),
        "published_root": _rel(pub_root) if pub_root else None,
        "seeds": seeds,
        "published_seeds": pub_seeds if pub_root else [],
        "n_locked": sorted(n_locked),
        "lock_arms": [k for k, _ in arms if any(k in v for v in lock_arms.values())],
        "lock_arms_by_tree": {_rel(t): v for t, v in lock_arms.items()},
        "lock_check": lock_check,
        "arms_from_published_root": [k for k, (t, _) in source.items() if t != root],
        "sd_convention": "population standard deviation over seeds (ddof=0)",
        "lock_source": "scripts/analysis/run_e5_comparison.py intersection_keys "
                       "(supervised AND finite, T rounded to 6 dp), imported not reimplemented",
        "arms": agg,
        "controls": ctrl,
        "derived": derived(agg, ctrl, seeds),
    }


def derived(agg: dict, ctrl: dict, seeds: list[int]) -> dict:
    """The quantities §S3's prose reads off this table, unrounded, so a transcription can be checked."""
    out: dict[str, object] = {}
    mae = {k: v["mae_mean"] for k, v in agg.items()}
    if {"ungrounded", "grounded_a"} <= mae.keys():
        out["training_time_grounding_delta_mae"] = mae["grounded_a"] - mae["ungrounded"]
        out["per_seed_grounding_gain"] = {
            str(s): agg["ungrounded"]["mae_per_seed"][str(s)] - agg["grounded_a"]["mae_per_seed"][str(s)]
            for s in seeds
        }
    if {"grounded_a", "oracle"} <= mae.keys():
        out["evaluation_time_substitution_delta_mae"] = mae["oracle"] - mae["grounded_a"]
    if {"grounded_a", "directgnn"} <= mae.keys():
        out["grounded_minus_directgnn_mae"] = mae["grounded_a"] - mae["directgnn"]
    if "nrtl" in agg:
        triple = [round(v, 3) for v in agg["nrtl"]["mae_per_seed"].values()]
        out["nrtl_mean_of_printed_per_seed_triple"] = float(np.mean(triple))
        out["nrtl_mean_unrounded"] = mae["nrtl"]
    ref = seeds[0]
    s = str(ref)
    have = lambda k: k in agg and s in agg[k]["mae_per_seed"]  # noqa: E731
    if have("grounded_a"):
        base = agg["grounded_a"]["mae_per_seed"][s]
        spread = list(agg["grounded_a"]["mae_per_seed"].values())
        rng = max(spread) - min(spread)
        block: dict[str, object] = {
            "seed": ref,
            "learned_sigma_mae": base,
            # the yardstick S3 measures the two single-seed controls against: the learned arm's
            # FULL between-seed range, not its sd
            "learned_sigma_between_seed_range": rng,
            "learned_sigma_worst_seed_mae": max(spread),
        }
        if have("oracle"):
            block["evaluation_only_gap"] = agg["oracle"]["mae_per_seed"][s] - base
        inj = ctrl.get("grounded_a_truetrain", {}).get("mae_per_seed", {}).get(s)
        if inj is not None:
            block["training_time_injection_gap"] = inj - base
        swap = ctrl.get("channel_swap", {}).get("mae_per_seed", {}).get(s)
        if swap is not None:
            block["channel_swap_gap"] = swap - base
        if rng > 0:
            for name in ("training_time_injection_gap", "channel_swap_gap"):
                if name in block:
                    block[f"{name}_in_between_seed_ranges"] = float(block[name]) / rng
        if "evaluation_only_gap" in block and "training_time_injection_gap" in block:
            ev = float(block["evaluation_only_gap"])
            block["share_coadaptation_removes"] = (ev - float(block["training_time_injection_gap"])) / ev
            if rng > 0 and ev != 0:
                # S3's own sensitivity on the share: "a spread the size of the learned arm's
                # 0.118 would move the share by about +/-0.27".  The share is
                # (ev - inj_gap)/ev, so moving the unmeasured numerator by d moves it by d/ev.
                # This was recorded as not being a function of the artifacts and therefore
                # undischargeable by any generator; both of its operands are two lines above.
                block["share_shift_per_learned_arm_sized_spread"] = rng / ev
        if inj is not None and "oracle" in agg:
            # S3's latitude check on the share: hold the single-seed injected arm where it was
            # measured and read it against each OTHER seed's learned baseline and oracle.  The
            # injected arm has no between-seed spread of its own, so this is the only handle on
            # how far the share could move; it is a range, not an interval.
            other = {}
            for s2 in seeds:
                k2 = str(s2)
                if k2 == s or k2 not in agg["oracle"]["mae_per_seed"]:
                    continue
                ev = agg["oracle"]["mae_per_seed"][k2] - agg["grounded_a"]["mae_per_seed"][k2]
                if ev != 0:
                    other[k2] = (agg["oracle"]["mae_per_seed"][k2] - inj) / ev
            if other:
                block["share_holding_injection_against_other_seed_baselines"] = other
        if "evaluation_time_substitution_delta_mae" in out and inj is not None:
            three = float(out["evaluation_time_substitution_delta_mae"])
            block["share_vs_three_seed_gap"] = (three - (inj - base)) / three
        out["single_seed_controls"] = block
    return out


def _fmt_row(label: str, a: dict, pad: int) -> str:
    mae = f"${a['mae_mean']:.2f}\\pm{a['mae_sd_population']:.2f}$"
    r2 = f"${a['r2_mean']:+.2f}\\pm{a['r2_sd_population']:.2f}$"
    per = "/".join(f"{a['mae_per_seed'][str(s)]:.3f}" for s in a["seeds"])
    return f"{label.ljust(pad)}& {mae} & {r2} & ${per}$ \\\\"


def render_tex(summary: dict) -> str:
    seeds = summary["seeds"]
    arms = summary["arms"]
    for a in arms.values():                      # tolerate summaries built before per-row seeds
        a.setdefault("seeds", list(seeds))
    order = sorted(arms, key=lambda k: arms[k]["mae_mean"])
    pinned = []
    for key in list(order):
        parent = _CHILD_OF.get(key)
        if parent and parent in order:
            order.remove(key)
            order.insert(order.index(parent) + 1, key)
            pinned.append(key)
    pad = max(len(arms[k]["label"]) for k in order) + 1

    seed_lists = {tuple(arms[k]["seeds"]) for k in order}
    one_seed_list = len(seed_lists) == 1
    seedlist = "/".join(str(s) for s in seeds)
    n = summary["n_locked"]
    n_str = str(n[0]) if len(n) == 1 else "/".join(str(x) for x in n)
    head = [
        "% GENERATED by scripts/analysis/make_si_arms_table.py.  Do not edit; re-run the script:",
        "%   KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/make_si_arms_table.py \\",
        f"%       --root {summary['root']}",
        f"% ROOT: {summary['root']}",
        f"% SEEDS: {','.join(str(s) for s in seeds)}",
        f"% N-LOCKED: {n_str} rows, the cross-arm intersection (supervised AND finite) over "
        + (", ".join(summary["lock_arms"]) if len(summary.get("lock_arms_by_tree") or {}) < 2
           else "; ".join(f"{tree}: {', '.join(v)}"
                          for tree, v in summary["lock_arms_by_tree"].items()))
        + ",",
        "%   computed by run_e5_comparison.intersection_keys, which this script imports rather",
        "%   than reimplements.",
        "% The +/- is a POPULATION standard deviation over seeds (ddof=0), as the caption and the SI",
        "%   state; a sample sd would be larger by sqrt("
        + (f"{len(seeds)}/{len(seeds) - 1}" if len(seeds) > 1 else "k/(k-1)") + ").",
        "% Mean, +/- and per-seed column are each rounded ONCE from the unrounded values, the column",
        "%   independently of the mean beside it, so averaging the printed triple need not give the",
        "%   printed mean (the NRTL row is where the two roundings part).",
        "% Unrounded values, per-seed R^2, the single-seed controls and the derived quantities S3's",
        "%   prose reads off this table: paper/si_tables/si_arms_table.json",
    ]
    borrowed = summary.get("arms_from_published_root") or []
    if borrowed:
        head += [
            "% NOT EVERY ROW COMES FROM --root.  The re-run does not retrain these arms and the",
            f"%   inventory's disposition is that they stand as printed: {', '.join(borrowed)},",
            f"%   read from {summary.get('published_root')} at seeds "
            f"{','.join(str(s) for s in summary.get('published_seeds') or [])}.  Each row's source",
            "%   tree, seed list and per-seed n are in the JSON beside this file.",
            "% Row lock across the two trees: "
            + ("identical key set in every seed."
               if (summary.get("lock_check") or {}).get("identical", True)
               else "DIFFERS -- "
                    + "; ".join((summary.get("lock_check") or {}).get("differences", []))
                    + ".  The cross-tree differences this table is read for are NOT "
                      "like-for-like."),
        ]
    if pinned:
        head.append(
            "% Rows are ordered by MAE, except " + ", ".join(pinned)
            + " which is typeset as a child row and is pinned under its parent."
        )
    if one_seed_list:
        body = [f"Arm & MAE & $R^2$ & per-seed MAE (${seedlist}$) \\\\", "\\midrule"]
    else:
        head.append(
            "% The per-seed column carries a different seed list per row -- "
            + "; ".join(f"{k}: {'/'.join(str(s) for s in arms[k]['seeds'])}" for k in order)
            + " -- so the column header cannot name one, and the caption must say which rows are "
              "which."
        )
        body = ["Arm & MAE & $R^2$ & per-seed MAE \\\\", "\\midrule"]
    body += [_fmt_row(arms[k]["label"], arms[k], pad) for k in order]
    return "\n".join(head + body) + "\n"


_NUM_WS = re.compile(r"[ \t]+")


def parse_header(text: str) -> dict:
    """Read back the ROOT and SEEDS a rows file was generated from.

    The header carries its own provenance so a checker does not have to be told which tree
    to check against -- point `--check` (or the test) at the file and it re-derives the tree
    the file claims, which is what makes the gate follow the leak-free re-run automatically.
    """
    out: dict[str, object] = {}
    for line in text.splitlines():
        if line.startswith("% ROOT:"):
            out["root"] = line.split(":", 1)[1].strip()
        elif line.startswith("% SEEDS:"):
            out["seeds"] = [int(s) for s in line.split(":", 1)[1].strip().split(",") if s.strip()]
    return out


def _normalise(text: str) -> list[str]:
    """Content of a rows file with comments and alignment whitespace removed."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        out.append(_NUM_WS.sub(" ", line))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=REPO / "results" / "e5_sigma_grounding",
                    help="results tree holding seed_*/<arm>_predictions.csv "
                         "(default: the published three-seed tree)")
    ap.add_argument("--published-root", type=Path,
                    default=REPO / "results" / "e5_sigma_grounding",
                    help="tree the arms the re-run does NOT retrain are read from "
                         "(DirectGNN, NRTL, +SG); pass 'none' to require every arm under --root")
    ap.add_argument("--seeds", type=int, nargs="+", default=None,
                    help="default: every seed_* directory under --root")
    ap.add_argument("--published-seeds", type=int, nargs="+", default=None,
                    help="default: every seed_* directory under --published-root")
    ap.add_argument("--allow-lock-mismatch", action="store_true",
                    help="emit even when the two trees do not score the same rows, stamping the "
                         "discrepancy on the header (the table is then not like-for-like)")
    ap.add_argument("--arms", nargs="+", default=None,
                    help="subset of arm keys to table, in fallback order (default: all present)")
    ap.add_argument("--out-tex", type=Path,
                    default=REPO / "paper" / "si_tables" / "si_arms_rows.tex")
    ap.add_argument("--out-json", type=Path,
                    default=REPO / "paper" / "si_tables" / "si_arms_table.json")
    ap.add_argument("--check", action="store_true",
                    help="write nothing; exit 1 if --out-tex differs from what would be written")
    args = ap.parse_args()

    root = args.root if args.root.is_absolute() else (REPO / args.root)
    seeds = args.seeds or discover_seeds(root)
    if not seeds:
        raise SystemExit(f"make_si_arms_table: no seed_* directories under {root}")
    if args.arms is None:
        arms = ARMS
    else:
        known = dict(ARMS)
        unknown = [k for k in args.arms if k not in known]
        if unknown:
            raise SystemExit(
                f"make_si_arms_table: no LaTeX label for arm(s) {unknown}; "
                f"known arms are {list(known)}.  A new arm needs a row label added to ARMS."
            )
        arms = tuple((k, known[k]) for k in args.arms)

    pub = args.published_root
    if pub is not None and str(pub).lower() == "none":
        pub = None
    elif pub is not None and not pub.is_absolute():
        pub = REPO / pub

    summary = collect(root, seeds, arms=arms, published_root=pub,
                      published_seeds=args.published_seeds,
                      allow_lock_mismatch=args.allow_lock_mismatch)
    tex = render_tex(summary)
    if summary["arms_from_published_root"]:
        print(f"NOTE: {summary['arms_from_published_root']} are not in {_rel(root)}; read from "
              f"{summary['published_root']} at seeds {summary['published_seeds']} "
              f"(lock across trees: "
              f"{'identical' if summary['lock_check']['identical'] else 'DIFFERS'})")

    if args.check:
        if not args.out_tex.exists():
            print(f"CHECK FAIL: {_rel(args.out_tex)} does not exist")
            sys.exit(1)
        have = _normalise(args.out_tex.read_text())
        want = _normalise(tex)
        if have == want:
            print(f"CHECK OK: {_rel(args.out_tex)} reproduces from {summary['root']} "
                  f"(seeds {summary['seeds']}, n={summary['n_locked']})")
            return
        print(f"CHECK FAIL: {_rel(args.out_tex)} differs from {summary['root']}")
        for i in range(max(len(have), len(want))):
            h = have[i] if i < len(have) else "<missing>"
            w = want[i] if i < len(want) else "<missing>"
            if h != w:
                print(f"  file:      {h}")
                print(f"  generated: {w}")
        sys.exit(1)

    args.out_tex.parent.mkdir(parents=True, exist_ok=True)
    args.out_tex.write_text(tex)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2) + "\n")
    print(tex)
    print(f"wrote {_rel(args.out_tex)} and {_rel(args.out_json)}")


if __name__ == "__main__":
    main()
