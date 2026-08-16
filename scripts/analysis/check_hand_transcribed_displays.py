#!/usr/bin/env python3
r"""Check the hand-transcribed displays of the sigma-grounding family against their artifacts.

WHY THIS EXISTS
---------------
``results/e5_sigma_grounding_leakfree/DISCHARGE_SHEET.md`` enrols thirty-six displays that the
five-seed leak-free re-run rewrites, and its Sec. 5 records what is wrong with that set: seven
enrolled items have no artifact and no generator behind them, twenty-one of the thirty-six rows are
prose no command recomputes, and the only mechanical gate anywhere in the set counts the abstract's
words.  Four of those items are hand-transcribed today and will still be hand-transcribed after the
re-run, because a generator is the wrong tool for a LaTeX table of prose:

  * the claims ledger    -- ``tab:claims`` / ``tab:claims-cont`` / ``tab:claims-cont2``
                            (three ``table*`` floats, nineteen rows, six block heads);
  * the run-family table -- the sigma-grounding row of ``tab:runs``, whose three cells must agree
                            with each other about the seed policy;
  * nine float captions  -- the seven the inventory's caption rule governs plus the two map
                            captions, which carry a differently-worded statement;
  * the table-of-contents graphic, whose caveat is a string literal in a script that reads no data;
  * THE ABSTRACT     -- added 2026-08-10.  When the author reversed the "no numerals" rule for it,
                        $2.043$, $1.846$ and $2.252$ became the only printed arm means in either
                        document that nothing verified, because this script finds a display by
                        ``\label`` and the achemso ``abstract`` environment has none.  It is
                        reached through the ``%<abstract-numerals>`` markers instead (see
                        ``find_abstract``), and all ten of its numerals are bound: three arm means
                        to the per-seed deposits the body's copies use, the margin sentence to
                        ``glycol_ether_ci_converged.json``, the search size to the map's own
                        stratum count.  Its two printed seed counts are told apart -- see
                        ``abstract_row``.

A generator cannot discharge those.  A CHECKER can: this script extracts every numeral from those
displays and verifies it against the artifact it is supposed to come from, failing loudly with the
display, the numeral, the artifact and both values when they disagree.

PARAMETERISED BY ROOT
---------------------
``--root`` is the results tree the re-run arms (ungrounded, grounded_a, oracle) are read from and
defaults to the published tree, so the same command discharges the leak-free tree when it lands::

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python \
        scripts/analysis/check_hand_transcribed_displays.py
    ... --root results/e5_sigma_grounding_leakfree

THE SEEDS ARE THE TREE'S, NOT A FLAG'S.  Five seeds need no argument, and that is not a
convenience: every printed seed count in these displays is checked against the seed set, so a
default of ``[42, 43, 44]`` made "3 seeds", "42,43,44", "Solid bars: three seeds", "seed 42 of
three" and both maps' "over 3 seeds" pass against a five-seed tree.  ``--seeds``, if given, must
equal what the tree holds; a disagreement stops the run.

Arms the re-run does not retrain -- DirectGNN, NRTL, ``grounded_b``, and the two seed-42 controls --
are always read from ``--published-root``, because the sheet's dispositions K and "outside" say their
published values stand.  When the two roots differ, the row lock of each is compared key by key: a
cross-root difference such as the ``+0.14`` of the accuracy row is only meaningful if both arms score
the identical rows, and that is checked rather than assumed.

WHAT "VERIFIED" MEANS HERE, AND WHAT IT DOES NOT
------------------------------------------------
Every numeral in the enrolled displays falls into exactly one of two sets, and the script prints
which:

  BOUND     -- recomputed from a deposited artifact and compared digit for digit at the decimal it
               is printed to.  A wrong digit is a MISMATCH and the run exits non-zero.
  DECLARED  -- a numeral belonging to another run family (the IDAC decomposition, the closure-
               fidelity kernels, the pKa second domain, the n=44 surrogate runs), registered here
               with its owner.  These are CHANGE-DETECTED, NOT VALUE-VERIFIED: the script knows what
               they read at the revision it was written against, so an edit to any of them fires
               UNREGISTERED (a numeral appeared) or STALE (a registered one is gone), but it makes no
               claim that the value is right.  Do not read a clean run as certifying them.

There is no third set.  A numeral that is neither bound nor declared is UNREGISTERED and fatal --
that is the property the whole script exists for, since the failure being guarded against is a wrong
digit entering a hand-transcribed cell during the five-seed substitution and passing every automatic
check the repository has.

THE CAPTION RULE
----------------
The inventory requires seven floats that carry re-run arms beside arms that were not re-run to say so
in their captions, and the two chemistry-map captions to say that only the physics side is five-seed.
The check is on the FORM OF WORDS, not on the existence of a caption: the seven must carry a
QUALIFIED phrase -- "leak-free re-run" or "<n>-seed re-run" -- and name at least one of their own
re-run arms; the two maps must name the physics side and the seed count in words.  The qualifier is
load-bearing: ``tab:baselines``' caption already reads "external models re-run here on an easier
by-solute split", so a rule keyed on the bare word "re-run" would pass a caption that says nothing
about this re-run at all.

The requirement activates when the root carries a re-run (``--rerun-landed``, default ``auto``: any
``--root`` other than the published tree that has per-row deposits in it).  Against the published
tree the rule is reported PENDING, which is what it is today: no arm in any of those floats came from
a re-run, so there is nothing yet to state.  What IS checked today is every caption's printed seed
count against the seeds actually in the root -- a five-seed tree under a caption reading "three
seeds" fails.

WHEN AN ARM IS NOT IN THE TREE YET
-----------------------------------
The leak-free tree lands in stages: the two trained arms first, the sigma-oracle only after a
separate inference pass (the sheet's precondition P0.3).  A cell quoting an arm that is not deposited
is reported MISSING and says in as many words that the numeral is UNCHECKED -- not verified, not
refuted.  It is never silently skipped, because a check that quietly does not run reads exactly like
one that passed.

EXIT STATUS
-----------
0 when no MISMATCH, UNREGISTERED, STALE or MISSING finding survives; 1 otherwise.  PENDING and OK are
not failures.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Callable, Sequence

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

#: The parity figure deposits the numbers it drew beside the PDF.  A numeral printed INSIDE a
#: figure cannot be read out of the .tex, so the caption's count of off-axis points is checked
#: against that sidecar rather than against a recomputation: the question here is whether the
#: caption agrees with the drawing, and the drawing is what the sidecar records.
_PARITY_JSON = REPO / "paper" / "figs" / "fig_parity_lnx2.numbers.json"


def _parity_sidecar() -> dict:
    if not _PARITY_JSON.exists():
        raise SystemExit(f"check: {_PARITY_JSON} is missing; regenerate the parity figure")
    return json.loads(_PARITY_JSON.read_text(encoding="utf-8"))
PUBLISHED_ROOT = REPO / "results" / "e5_sigma_grounding"

#: The two artifacts behind the abstract's IDAC sentence.  The abstract, the body and the deposit
#: have to agree about one interval, and this is the copy that decides.
GLYCOL_CI = REPO / "results" / "b_insuff" / "glycol_ether_ci_converged.json"
ADMISSIBILITY = REPO / "results" / "b_insuff" / "admissibility_table.csv"
#: The cross-fitted map, added 2026-08-11: the abstract now prints BOTH estimators' margin for the
#: glycol-ether row set, so the pre-declared estimator's value needs a binding of its own.
CROSSFIT_MAP = REPO / "results" / "b_insuff" / "crossfit_map_table.csv"


def crossfit_glycol_margin() -> float:
    """The pre-declared cross-fitted estimator's margin on the glycol-ether row set.

    Read at the SAME cell the binning-bound margin is read at -- broad_473, solvent_class axis,
    row unit, residual-only convention, pair-grouped folds, the declared regressor -- so the two
    numbers the abstract sets side by side differ in the estimator and in nothing else.
    """
    if not CROSSFIT_MAP.exists():
        raise SystemExit(f"check: {CROSSFIT_MAP} is missing; run "
                         "scripts/analysis/run_b_insuff_crossfit_scoring.py")
    df = pd.read_csv(CROSSFIT_MAP)
    cell = df[(df["set"] == "broad_473") & (df["axis"] == "solvent_class")
              & (df["stratum"] == "glycol_ether") & (df["unit"] == "row")
              & (df["convention"] == "res") & (df["fold_scheme"] == "pair")
              & (df["model"] == "rf")]
    if len(cell) != 1:
        raise SystemExit("check: the cross-fitted glycol-ether cell is no longer unique "
                         f"({len(cell)} rows matched); re-anchor crossfit_glycol_margin()")
    return float(cell["margin_cf"].iloc[0])


def glycol_deposit() -> dict:
    if not GLYCOL_CI.exists():
        raise SystemExit(f"check: {GLYCOL_CI} is missing; run "
                         "scripts/analysis/run_b_insuff_glycol_ether_ci.py")
    return json.loads(GLYCOL_CI.read_text(encoding="utf-8"))


def map_stratum_count() -> int:
    """The size of the search the glycol-ether row set is the survivor of.

    The map's headline cell -- broad IDAC, row unit, deployed residual-only convention -- and the
    count is of that cell's strata, which is what "$59$-fold search" names.
    """
    if not ADMISSIBILITY.exists():
        raise SystemExit(f"check: {ADMISSIBILITY} is missing; run "
                         "scripts/analysis/run_b_insuff_stratified_map.py")
    df = pd.read_csv(ADMISSIBILITY)
    cell = df[(df["set"] == "broad_477") & (df["unit"] == "row") & (df["convention"] == "res")]
    return int(cell.groupby(["axis", "stratum"]).ngroups)

# The five arms that intersect at every seed, plus the sigma-oracle re-evaluation.  The lock is
# taken over whichever of these the root actually holds; run_e5_comparison.py's own docstring
# records that the `finite` half of the conjunction is inert on these deposits, so the lock is the
# labelled row set and does not depend on which arms are present.
INTERSECTING_ARMS = ("nrtl", "directgnn", "ungrounded", "grounded_a", "grounded_b", "oracle")
RERUN_ARMS = ("ungrounded", "grounded_a", "oracle")
PUBLISHED_ONLY_ARMS = ("nrtl", "directgnn", "grounded_b")
SEED42_CONTROL_ARMS = ("grounded_a_truetrain", "channel_swap")

KEY = ["solute_smiles", "solvent_smiles", "T6"]
USECOLS = ["solute_smiles", "solvent_smiles", "T", "has_solubility", "ln_x2_true", "ln_x2_pred"]

def rel(path: Path) -> str:
    """Repo-relative when it can be, absolute otherwise -- a --root may live outside the repo."""
    try:
        return str(Path(path).relative_to(REPO))
    except ValueError:
        return str(path)


WORDS = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
         6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


# --------------------------------------------------------------------------- formatting
def fmt(x: float, nd: int, *, sign: bool = False) -> str:
    """Round half away from zero, the way a person transcribing a cell does.

    Python's round() is half-to-even, so round(1.845, 2) is 1.84 and the paper prints 1.85; every
    comparison here goes through this function so the checker and the transcriber round alike.
    """
    q = Decimal(1).scaleb(-nd)
    d = Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)
    if d == 0:
        d = abs(d)
    s = f"{d:+f}" if sign else f"{d:f}"
    # Decimal keeps the exact number of places asked for; nd=0 leaves a trailing '.'
    return s.rstrip(".") if nd == 0 else s


def word(n: int) -> str:
    return WORDS.get(n, str(n))


# --------------------------------------------------------------------------- findings
SEVERITY_FATAL = ("MISMATCH", "UNREGISTERED", "STALE", "MISSING")


@dataclass
class Finding:
    severity: str          # OK | MISMATCH | UNREGISTERED | STALE | MISSING | PENDING
    display: str           # the label or name of the display
    item: str              # what was checked
    printed: str = ""
    expected: str = ""
    artifact: str = ""
    note: str = ""

    @property
    def fatal(self) -> bool:
        return self.severity in SEVERITY_FATAL


# --------------------------------------------------------------------------- arm statistics
@dataclass
class ArmStat:
    arm: str
    root: Path
    seeds: tuple[int, ...]
    mae: dict[int, float]
    r2: dict[int, float]

    @property
    def mae_mean(self) -> float:
        return float(np.mean([self.mae[s] for s in self.seeds]))

    @property
    def mae_sd(self) -> float:
        return float(np.std([self.mae[s] for s in self.seeds]))

    @property
    def r2_mean(self) -> float:
        return float(np.mean([self.r2[s] for s in self.seeds]))

    @property
    def r2_sd(self) -> float:
        return float(np.std([self.r2[s] for s in self.seeds]))


def _pred_path(root: Path, seed: int, arm: str) -> Path:
    return root / f"seed_{seed}" / f"{arm}_predictions.csv"


def discover_seeds(root: Path) -> tuple[int, ...]:
    """The seeds a results tree actually holds: ``seed_<n>/`` with per-row deposits in it.

    Every printed seed count in these displays -- ``3 seeds``, ``42,43,44``, ``Solid bars: three
    seeds``, ``seed 42 of three``, ``over 3 seeds`` -- is checked against ``len(seeds)``, so where
    that number comes from decides whether the check can fail.  It used to come from a flag whose
    default was ``[42, 43, 44]``: pointed at the five-seed tree with no flag, the script compared
    the printed ``three`` against its own default and passed every one of them.  It comes from the
    tree now, and the flag (if given) is an assertion about the tree rather than a substitute for
    it.
    """
    seeds = []
    for d in sorted(root.glob("seed_*")):
        if d.is_dir() and d.name[5:].isdigit() and any(d.glob("*_predictions.csv")):
            seeds.append(int(d.name[5:]))
    return tuple(sorted(seeds))


def resolve_seeds(root: Path, requested: Sequence[object] | None, flag: str) -> tuple[int, ...]:
    found = discover_seeds(root)
    if not found:
        raise SystemExit(
            f"no seed_*/ directory with per-row prediction CSVs under {root}; the seed count the "
            "captions are checked against cannot be established, so nothing here is checkable"
        )
    if not requested:
        return found
    asked = tuple(int(s) for s in requested)
    if asked != found:
        raise SystemExit(
            f"{flag} says {list(asked)} but {rel(root)} holds {list(found)}.  These displays print "
            "their own seed count and this script checks it against the seed set it is given, so "
            "scoring a subset would certify a caption reading "
            f"'{word(len(asked))} seeds' against a {word(len(found))}-seed tree -- which is the "
            f"failure the check exists for.  Drop {flag} and let the tree decide."
        )
    return asked


def _load_arm(root: Path, seed: int, arm: str) -> pd.DataFrame:
    df = pd.read_csv(_pred_path(root, seed, arm), usecols=USECOLS, low_memory=False)
    df["T6"] = df["T"].round(6)
    return df


def _eligible(df: pd.DataFrame) -> pd.DataFrame:
    """Labelled AND finite-predicted rows, deduplicated on the key -- run_e5_comparison.py's lock."""
    d = df.drop_duplicates(KEY, keep="first")
    sup = d["has_solubility"].astype(str).str.strip().str.lower().isin({"true", "1", "1.0"})
    fin = np.isfinite(d["ln_x2_pred"].to_numpy(dtype=float))
    return d[sup & fin]


def _keys_of(df: pd.DataFrame) -> set[tuple]:
    return set(map(tuple, _eligible(df)[KEY].itertuples(index=False, name=None)))


def _metrics(df: pd.DataFrame, keys: Sequence[tuple]) -> tuple[float, float]:
    sub = df.drop_duplicates(KEY, keep="first").set_index(KEY).loc[list(keys)]
    t = sub["ln_x2_true"].to_numpy(dtype=float)
    p = sub["ln_x2_pred"].to_numpy(dtype=float)
    mae = float(np.mean(np.abs(t - p)))
    ss_res = float(np.sum((t - p) ** 2))
    ss_tot = float(np.sum((t - t.mean()) ** 2))
    return mae, float(1.0 - ss_res / (ss_tot + 1e-12))


@dataclass
class RootStats:
    """Every arm mean a display in this family can quote, from one results root."""
    root: Path
    seeds: tuple[int, ...]
    arms: dict[str, ArmStat]
    lock: dict[int, list[tuple]]
    n_total_rows: int
    facts: dict          # pairs / solutes / solvents / temperature span on the lock

    @property
    def n_lock(self) -> int:
        return len(self.lock[self.seeds[0]])


def collect_root(root: Path, seeds: Sequence[int]) -> RootStats:
    seeds = tuple(int(s) for s in seeds)
    present: list[str] = []
    for arm in INTERSECTING_ARMS:
        if all(_pred_path(root, s, arm).exists() for s in seeds):
            present.append(arm)
    if not present:
        raise SystemExit(
            f"no per-row prediction CSVs under {root} for seeds {list(seeds)} -- "
            "the leak-free tree carries only summary JSONs until the CSVs are fetched "
            "(DISCHARGE_SHEET.md precondition P0.1)"
        )
    lock: dict[int, list[tuple]] = {}
    arms: dict[str, ArmStat] = {a: ArmStat(a, root, seeds, {}, {}) for a in present}
    facts: dict = {}
    for seed in seeds:
        frames = {a: _load_arm(root, seed, a) for a in present}
        common: set[tuple] | None = None
        for df in frames.values():
            k = _keys_of(df)
            common = k if common is None else (common & k)
        keys = sorted(common or set())
        lock[seed] = keys
        for a, df in frames.items():
            mae, r2 = _metrics(df, keys)
            arms[a].mae[seed] = mae
            arms[a].r2[seed] = r2
        if seed == seeds[0]:
            ref = frames[present[0]]
            n_total = int(len(ref.drop_duplicates(KEY, keep="first")))
            sub = ref.drop_duplicates(KEY, keep="first").set_index(KEY).loc[keys].reset_index()
            facts = {
                "n_pairs": int(sub.groupby(["solute_smiles", "solvent_smiles"]).ngroups),
                "n_solutes": int(sub["solute_smiles"].nunique()),
                "n_solvents": int(sub["solvent_smiles"].nunique()),
                "t_min": float(sub["T"].min()),
                "t_max": float(sub["T"].max()),
                "n_total_rows": n_total,
            }
    return RootStats(root, seeds, arms, lock, facts["n_total_rows"], facts)


def seed42_controls(published_root: Path) -> dict[str, float]:
    """MAE of the two seed-42 control arms on the lock they share with grounded_a and oracle.

    Note (c) of the ledger asserts that lock is the same 5608 rows; taking the intersection over all
    four arms and reporting its size is how that assertion is checked rather than trusted.
    """
    arms = ("grounded_a", "oracle", *SEED42_CONTROL_ARMS)
    if not all(_pred_path(published_root, 42, a).exists() for a in arms):
        return {}
    frames = {a: _load_arm(published_root, 42, a) for a in arms}
    common: set[tuple] | None = None
    for df in frames.values():
        k = _keys_of(df)
        common = k if common is None else (common & k)
    keys = sorted(common or set())
    out = {a: _metrics(df, keys)[0] for a, df in frames.items()}
    out["n_lock"] = float(len(keys))
    return out


def both_increasing_groups(root: Path, published_root: Path, seeds: Sequence[int]) -> dict:
    """Groups in which BOTH arms' per-group affine recalibration is an increasing map.

    Reproduces the 652/633/650-by-seed and 589-at-all-three counts that the ledger's fifth row and
    Sec. S6.1 print.  ``results/e5_sigma_grounding/ranking/rank_final.json`` deposits every fitted
    slope's summary but not these counts, so they are recomputed here from the per-row deposits by
    the same construction ``rank_final.py`` uses: groups are (solute, T rounded to 1 K) with at least
    three solvents and a non-constant measurement, and the slope is the least-squares slope of the
    measurement on the prediction within the group.

    BOTH ARMS COME FROM ``--root`` OR THE COUNT IS NOT COMPUTED.  The quantity is within-checkpoint
    -- one set of weights, its own sigma-oracle re-evaluation, which is what lets the ledger say
    the row is free of the separate-tuning confound.  A per-arm fallback to ``--published-root``
    was worse than no fallback: with the leak-free tree in exactly the state the gate is in today
    (``grounded_a`` deposited, the sigma-oracle inference pass still pending, precondition P0.3) it
    took the grounded arm from the re-run and the oracle from the published tree and reported the
    count OK, in the same run in which every other oracle-quoting cell was correctly MISSING.  A
    count spliced across two trees is not the count the row claims, and reporting it as verified is
    the one outcome worse than reporting nothing.  ``published_root`` is kept in the signature and
    named in the diagnosis so the caller sees which tree was NOT consulted.
    """
    min_solvents, t_tol = 3, 1.0
    for seed in seeds:
        for arm in ("grounded_a", "oracle"):
            if not _pred_path(root, seed, arm).exists():
                other = (f" (it is in {rel(published_root)}, but splicing one arm from another "
                         "tree would not be this row's within-checkpoint contrast)"
                         if root != published_root
                         and _pred_path(published_root, seed, arm).exists() else "")
                return {"available": False,
                        "why": f"{arm} is not deposited at seed {seed} in {rel(root)}{other}"}
    sources = {(seed, arm): root for seed in seeds for arm in ("grounded_a", "oracle")}
    persistent: set[tuple] | None = None
    per_seed: dict[int, int] = {}
    n_groups_last = 0
    for seed in seeds:
        coll = {}
        for arm in ("grounded_a", "oracle"):
            df = _load_arm(sources[(seed, arm)], seed, arm)
            d = df.drop_duplicates(KEY, keep="first")
            sup = d["has_solubility"].astype(str).str.strip().str.lower().isin({"true", "1", "1.0"})
            d = d[sup].copy()
            d["Tr"] = (pd.to_numeric(d["T"], errors="coerce") / t_tol).round() * t_tol
            coll[arm] = (d.groupby(["solute_smiles", "Tr", "solvent_smiles"])
                          .agg(t=("ln_x2_true", "mean"), p=("ln_x2_pred", "mean")).sort_index())
        ref = coll["grounded_a"]
        inc: set[tuple] = set()
        n_groups = 0
        for (sol, tr), grp in ref.groupby(level=[0, 1]):
            solvents = sorted(grp.index.get_level_values(2).tolist())
            if len(solvents) < min_solvents:
                continue
            t = grp.droplevel([0, 1]).reindex(solvents)["t"].to_numpy(dtype=float)
            if np.std(t) == 0:
                continue
            n_groups += 1
            increasing = True
            for arm in ("grounded_a", "oracle"):
                p = coll[arm].loc[(sol, tr)].reindex(solvents)["p"].to_numpy(dtype=float)
                vp = float(np.var(p))
                slope = float(np.cov(p, t, bias=True)[0, 1] / vp) if vp > 0 else 0.0
                if not slope > 0.0:
                    increasing = False
            if increasing:
                inc.add((sol, float(tr)))
        per_seed[int(seed)] = len(inc)
        persistent = inc if persistent is None else (persistent & inc)
        n_groups_last = n_groups
    return {"available": True, "per_seed": per_seed,
            "all_seeds": len(persistent or set()), "n_groups": n_groups_last}


def need(block: dict, key: str, what: str) -> str:
    """Read a derived value, or raise the KeyError that turns into a MISSING finding."""
    if not block.get("available", True) or key not in block:
        raise KeyError(f"{what}: {block.get('why', 'not computed')}")
    return str(block[key])


# --------------------------------------------------------------------------- LaTeX extraction
_TEX_FILES = (
    "grounding_paradox.tex",
    "sections/SI.tex",
    "sections/supporting.tex",
    "sections/chemistry-map.tex",
    "sections/fig-parity-lnx2.tex",
)


def _balanced(text: str, i: int) -> int:
    """Index one past the '}' matching the '{' at text[i]."""
    assert text[i] == "{", text[i:i + 20]
    depth = 0
    while i < len(text):
        if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
            depth += 1
        elif text[i] == "}" and text[i - 1] != "\\":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced braces")


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def find_display(paper: Path, label: str) -> tuple[Path, str]:
    """The float (table*/table/figure*/figure) whose \\label is `label`, and the file it lives in."""
    for rel in _TEX_FILES:
        path = paper / rel
        if not path.exists():
            continue
        text = strip_comments(path.read_text())
        m = re.search(r"\\label\{" + re.escape(label) + r"\}", text)
        if not m:
            continue
        starts = [mm.start() for mm in re.finditer(r"\\begin\{(table\*?|figure\*?)\}", text)
                  if mm.start() < m.start()]
        if not starts:
            # a label outside a float (chemistry-map's \subsection) -- return the paragraph
            return path, text
        start = starts[-1]
        end_m = re.search(r"\\end\{(table\*?|figure\*?)\}", text[start:])
        end = start + end_m.end()
        return path, text[start:end]
    raise SystemExit(f"label {label!r} not found in any of {_TEX_FILES}")


#: The abstract's source markers.  See ``find_abstract``.
ABSTRACT_OPEN = "%<abstract-numerals>"
ABSTRACT_CLOSE = "%</abstract-numerals>"


def find_abstract(paper: Path) -> str:
    r"""The abstract's printed text, located by its source markers.

    EVERY OTHER DISPLAY HERE IS LOCATED BY ``\label``, and the achemso ``abstract`` environment
    carries none -- so when the author's 2026-08-10 ruling put the magnitudes back into the
    abstract, $2.043$, $1.846$ and $2.252$ became the only printed arm means in either document
    that no checker could reach.  They are also the three most exposed numerals in the
    submission: page 1, read without the deposit beside them, and rewritten by the five-seed
    re-run.

    A ``\label`` inside ``abstract`` would be a label on nothing (achemso does not number the
    block, and ``\ref`` to it prints the section it lands in), so the region is marked in the
    source instead.  The markers are LaTeX comments, they reach no reader, and BOTH ARE
    LOAD-BEARING: this function raises rather than returns when either is missing, when they do
    not bracket an ``abstract`` environment, or when the environment they bracket is not the
    document's own.  A checker that quietly stops covering a region reads exactly like one that
    passed, which is the failure this whole script exists to prevent.
    """
    path = paper / "grounding_paradox.tex"
    raw = path.read_text()
    # THE OPENING MARKER WAS NOT LOAD-BEARING AND THIS FUNCTION SAID IT WAS.  A plain
    # raw.find(ABSTRACT_OPEN) matches the first occurrence in the file, and the source comment
    # that documents these markers PRINTS THE LITERAL ITSELF ~140 lines earlier ("The block is now
    # delimited by the %<abstract-numerals> markers below").  So deleting the real marker left the
    # region running from that mention to the close, the identity check still passed, and the
    # script reported `pass' with coverage unchanged -- a checker that could not fail on the one
    # deletion it declared fatal.  Anchor on \begin{abstract} and take the LAST marker before it.
    anchor = raw.find("\\begin{abstract}")
    if anchor < 0:
        raise SystemExit("check_hand_transcribed_displays: no \\begin{abstract} in the article "
                         "source; the abstract's numerals cannot be located.")
    i, j = raw.rfind(ABSTRACT_OPEN, 0, anchor), raw.find(ABSTRACT_CLOSE, anchor)
    if i < 0 or j < 0:
        raise SystemExit(
            f"{rel(path)}: the abstract's source markers are gone ("
            f"{ABSTRACT_OPEN if i < 0 else ''}{' and ' if i < 0 and j < 0 else ''}"
            f"{ABSTRACT_CLOSE if j < 0 else ''} not found).  They are what gives this script a "
            "handle on the abstract; restore them around \\begin{abstract}...\\end{abstract}."
        )
    if j < i:
        raise SystemExit(f"{rel(path)}: the abstract's closing marker precedes its opening one")
    region = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", raw[i:j], re.S)
    whole = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", raw, re.S)
    if region is None or whole is None:
        raise SystemExit(f"{rel(path)}: the abstract markers no longer bracket an abstract "
                         "environment")
    if region.group(1) != whole.group(1):
        raise SystemExit(f"{rel(path)}: the marked region is not the document's abstract -- the "
                         "markers drifted, so they would certify the wrong text")
    return normalise_ws(strip_comments(region.group(1)))


def caption_of(block: str) -> str:
    # The optional argument is the SHORT caption, added to every Supporting Information float on
    # 2026-08-10 so that \listoftables prints one line per float instead of the whole caption.
    # It made six of the nine enrolled captions unreadable to this pattern -- tab:si-baselines-full,
    # tab:si-arms, tab:claims, tab:claims-cont2, tab:solvent-map, tab:solute-map -- and the script
    # reported each as MISSING, which is a checker that stopped checking rather than a display that
    # went wrong.  The group is non-capturing and the balanced scan still starts at the MANDATORY
    # brace, so the short caption is skipped rather than checked: it carries no numeral of its own.
    m = re.search(r"\\caption(?:\[[^\]]*\])?\{", block)
    if not m:
        return ""
    start = m.end() - 1
    end = _balanced(block, start)
    return normalise_ws(block[start + 1:end - 1])


def normalise_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tabnotes_of(block: str) -> str:
    """The \\tabnotes{...} block of a float, whitespace-normalised ('' when there is none).

    The ledger's notes a--h are inside the third float but outside its tabular, so a row-by-row
    pass over the table misses them -- and note (c) is where the ledger asserts that the two
    seed-42 control rows carry the same labelled set as the three-seed rows above them.  That is a
    checkable claim about a row lock, printed in a place nothing else looks at.
    """
    m = re.search(r"\\tabnotes\{", block)
    if not m:
        return ""
    start = m.end() - 1
    return normalise_ws(block[start + 1:_balanced(block, start) - 1])


def tabular_rows(block: str) -> list[str]:
    """The rows of the first tabular in `block`, whitespace-normalised, rules and heads dropped."""
    m = re.search(r"\\begin\{tabular\}\{", block)
    if not m:
        return []
    spec_end = _balanced(block, m.end() - 1)
    body_end = block.index(r"\end{tabular}", spec_end)
    body = block[spec_end:body_end]
    out = []
    for chunk in re.split(r"\\\\", body):
        c = normalise_ws(chunk)
        c = re.sub(r"\\(top|mid|bottom)rule", "", c)
        c = re.sub(r"\\addlinespace(\[[^\]]*\])?", "", c)
        c = normalise_ws(c)
        if c:
            out.append(c)
    return out


def pick_row_index(rows: Sequence[str], needle: str, display: str = "") -> int:
    hits = [i for i, r in enumerate(rows) if needle in r]
    if len(hits) != 1:
        where = f" of {display}" if display else ""
        raise SystemExit(f"row selector {needle!r}{where} matched {len(hits)} rows, expected 1")
    return hits[0]


# --------------------------------------------------------------------------- numeral extraction
# A leading sign counts only where a sign can stand: `$-0.197$` and `[-0.282,-0.117]` carry one,
# `VT-2005` and `top-1` do not, and reading the hyphen of a hyphenated name as a minus turned the
# first dump of this registry into a list of negative years.
_NUM_RE = re.compile(r"(?<![A-Za-z0-9])[-+]?\d+(?:\.\d+)?")

# Constructs whose digits are typesetting, not content.  Each is blanked to spaces of the same
# length so that every span computed on the masked text is a valid span in the raw text.
_MASK_PATTERNS = (
    r"\\label\{[^{}]*\}",
    r"\\(?:S\\)?ref\{[^{}]*\}",
    r"\\(?:eq|C|c)ref\{[^{}]*\}",
    r"\\cite[a-z]*\{[^{}]*\}",
    r"\\includegraphics(?:\[[^\]]*\])?\{[^{}]*\}",
    r"\\setlength\{[^{}]*\}\{[^{}]*\}",
    r"\\renewcommand\{[^{}]*\}\{[^{}]*\}",
    r"\\arraystretch",
    r"\\addlinespace(?:\[[^\]]*\])?",
    r"\\begin\{tabular\}",
    r"\\multicolumn\{\d+\}",
    r"\\dimexpr[^\\]*(?:\\[a-zA-Z]+)*\\relax",
    r"\\linewidth",
    r"\\tabcolsep",
    r"\\tnk\{[a-z,]*\}",
    r"\\hspace\{[^{}]*\}",
    r"\\vspace\{[^{}]*\}",
    r"L\{[^{}]*\}",
    r"\[[tbph!]+\]",
    # Digits that are part of a NAME, not of a measurement.  Each of these was found in the
    # displays this script checks; a digit inside a name cannot be verified against an artifact
    # and must not be reported as an unregistered measurement.
    r"R\^\{?2\}?",              # R^2
    r"top-\d+",                 # the top-1 metric
    r"nDCG@\d+",                # the nDCG@3 metric
    r"VT-\d{4}",                # the VT-2005 profile database
    r"\\log_\{?10\}?",          # log_10 S
    r"x_2",                     # ln x_2
    r"\\mathrm\s*pK_a",         # pKa
    r"pK_a",
    r"\\Delta\\Phi",
    r"\\Delta\\rho",
    # LAST, and it must be last: every remaining control sequence.  Without it the letters of
    # `\pm`, `\to` and `\times` sit directly against the digit that follows them, the sign
    # lookbehind above reads that letter as part of a word, and `$51\pm2\%$` loses its 2 while
    # `$1.78\to0.77$` reports a numeral `77`.  Control sequences carry no measurement.
    r"\\[a-zA-Z]+",
)


def mask_noncontent(text: str) -> str:
    masked = text
    for pat in _MASK_PATTERNS:
        masked = re.sub(pat, lambda m: " " * len(m.group(0)), masked)
    return masked


@dataclass(frozen=True)
class Numeral:
    token: str
    start: int
    end: int


def numerals(text: str) -> list[Numeral]:
    masked = mask_noncontent(text)
    return [Numeral(m.group(0), m.start(), m.end()) for m in _NUM_RE.finditer(masked)]


# --------------------------------------------------------------------------- bindings
@dataclass
class Bind:
    """One anchored assertion: a regex over the display, and what its groups must read."""
    what: str
    pattern: str
    expect: Callable[["Ctx"], tuple[str, ...]]
    artifact: Callable[["Ctx"], str]


@dataclass
class Claim:
    """A word-claim in a display that an artifact can settle (no numeral of its own)."""
    what: str
    holds: Callable[["Ctx"], bool]
    artifact: Callable[["Ctx"], str]
    quote: str = ""


@dataclass
class DisplayRow:
    key: str                       # substring selecting the row (or "" for a whole caption)
    binds: list[Bind] = field(default_factory=list)
    declared: list[str] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    owner: str = ""                # who owns the declared numerals


@dataclass
class Ctx:
    root: RootStats
    published: RootStats
    controls: dict[str, float]
    ranking: dict
    increasing: dict
    seeds: tuple[int, ...]
    rerun_landed: bool
    paper: Path

    # -- arm accessors: re-run arms from --root, everything else from --published-root
    def arm(self, name: str) -> ArmStat:
        src = self.published if name in PUBLISHED_ONLY_ARMS else self.root
        if name not in src.arms:
            raise KeyError(f"arm {name!r} absent from {src.root}")
        return src.arms[name]

    @property
    def gain(self) -> float:
        return self.arm("ungrounded").mae_mean - self.arm("grounded_a").mae_mean

    @property
    def penalty(self) -> float:
        return self.arm("oracle").mae_mean - self.arm("grounded_a").mae_mean

    @property
    def physics_penalty(self) -> float:
        return self.arm("grounded_a").mae_mean - self.arm("directgnn").mae_mean

    def per_seed_gain(self) -> list[float]:
        u, g = self.arm("ungrounded"), self.arm("grounded_a")
        return [u.mae[s] - g.mae[s] for s in self.seeds]

    @property
    def share(self) -> float:
        g42 = self.arm("grounded_a").mae[42]
        o42 = self.arm("oracle").mae[42]
        t42 = self.controls["grounded_a_truetrain"]
        return 1.0 - (t42 - g42) / (o42 - g42)


def A(ctx: Ctx, *arms: str) -> str:
    """A one-line description of where an arm mean came from."""
    parts = []
    for a in arms:
        src = ctx.published.root if a in PUBLISHED_ONLY_ARMS else ctx.root.root
        parts.append(f"{rel(src)}/seed_{{{','.join(str(s) for s in ctx.seeds)}}}"
                     f"/{a}_predictions.csv")
    return " and ".join(parts)


# --------------------------------------------------------------------------- the registry
def ledger_rows() -> list[DisplayRow]:
    """Block 1 of the claims ledger -- the five rows the sheet's row 5 enrols -- fully bound."""
    return [
        DisplayRow(
            key="Reference profiles hurt solubility at evaluation",
            binds=[
                Bind("the labelled row set",
                     r"labelled test rows \(\$(\d+)\$ of \$(\d+)\$\)",
                     lambda c: (str(c.root.n_lock), str(c.root.n_total_rows)),
                     lambda c: f"cross-arm lock over {A(c,'grounded_a')}"),
                Bind("the seed count",
                     r"\), (\d+) seeds",
                     lambda c: (str(len(c.seeds)),),
                     lambda c: f"seed directories under {rel(c.root.root)}"),
                Bind("grounded -> sigma-oracle MAE",
                     r"\$([\d.]+)\\to([\d.]+)\$; the per-seed values",
                     lambda c: (fmt(c.arm("grounded_a").mae_mean, 2),
                                fmt(c.arm("oracle").mae_mean, 2)),
                     lambda c: A(c, "grounded_a", "oracle")),
            ],
            claims=[
                Claim("the per-seed values do not overlap",
                      lambda c: max(c.arm("grounded_a").mae[s] for s in c.seeds)
                      < min(c.arm("oracle").mae[s] for s in c.seeds),
                      lambda c: A(c, "grounded_a", "oracle"),
                      quote="the per-seed values do not overlap"),
            ],
        ),
        DisplayRow(
            key="still hurt when injected at training",
            binds=[
                Bind("the control seed",
                     r"seed \$(\d+)\$",
                     lambda c: ("42",),
                     lambda c: f"{rel(PUBLISHED_ROOT)}/seed_42/ "
                               "(the co-adaptation control is a seed-42 arm)"),
                Bind("co-adapted injection against its own baseline",
                     r"\$([\d.]+)\\to([\d.]+)\$ \(own baseline \$([\d.]+)\\to([\d.]+)\$\)",
                     lambda c: (fmt(c.arm("grounded_a").mae[42], 2),
                                fmt(c.controls["grounded_a_truetrain"], 2),
                                fmt(c.arm("grounded_a").mae[42], 2),
                                fmt(c.arm("oracle").mae[42], 2)),
                     lambda c: f"{rel(PUBLISHED_ROOT)}/seed_42/"
                               "grounded_a_truetrain_predictions.csv against "
                               + A(c, "grounded_a", "oracle")),
            ],
        ),
        DisplayRow(
            key="so part of that gap is test-time distribution shift",
            binds=[
                Bind("the control seed",
                     r"seed \$(\d+)\$",
                     lambda c: ("42",),
                     lambda c: f"{rel(PUBLISHED_ROOT)}/seed_42/"),
                Bind("the share carried by the training-time injection",
                     r"share \$([\d.]+)\$ on one seed",
                     lambda c: (fmt(c.share, 2),),
                     lambda c: "1 - (truetrain-grounded)/(oracle-grounded) at seed 42, over "
                               + A(c, "grounded_a", "oracle")),
            ],
        ),
        DisplayRow(
            key=r"Training-time $\sigma$ supervision",
            binds=[
                Bind("the seed count",
                     r"labelled test rows, (\d+) seeds",
                     lambda c: (str(len(c.seeds)),),
                     lambda c: f"seed directories under {rel(c.root.root)}"),
                # RE-ANCHORED 2026-08-12. The supervision row was reworded when its claim lost its
                # sign, and both of these bindings anchored on wording that went with it: the arrow
                # was followed by "; the per-seed values" and the gains by "straddle". Neither
                # pattern matched, so seven numerals in the rewritten row were unregistered while
                # the two bindings reported MISSING -- a display can go dark without a mismatch.
                Bind("ungrounded -> grounded MAE",
                     r"\$([\d.]+)\\to([\d.]+)\$ in the seed mean",
                     lambda c: (fmt(c.arm("ungrounded").mae_mean, 2),
                                fmt(c.arm("grounded_a").mae_mean, 2)),
                     lambda c: A(c, "ungrounded", "grounded_a")),
                Bind("the per-seed supervision gains",
                     r"gains reverses: \$([-\d./]+)\$",
                     lambda c: ("/".join(fmt(g, 3) for g in c.per_seed_gain()),),
                     lambda c: A(c, "ungrounded", "grounded_a")),
                Bind("the co-adapted arm's cost",
                     r"straddle the co-adapted arm's \$([-+][\d.]+)\$",
                     lambda c: (fmt(c.controls["grounded_a_truetrain"]
                                    - c.arm("grounded_a").mae[42], 2, sign=True),),
                     lambda c: f"{rel(PUBLISHED_ROOT)}/seed_42/"
                               "grounded_a_truetrain_predictions.csv"),
            ],
            claims=[
                # INVERTED 2026-08-12, and the quote had to change with it. At three seeds the
                # supervision row asserted that the per-seed values do NOT overlap; at five they
                # do -- ungrounded reaches 1.940 and grounded reaches 2.056 -- so the row now
                # asserts the overlap instead. The quote is bound to the supervision row's own
                # wording because the substitution row still carries the old phrase verbatim and
                # is still right to: there grounded tops out at 2.056 against the oracle's 2.145.
                # A literal search for the old phrase found the wrong row and passed on it.
                Claim("the per-seed values overlap",
                      lambda c: min(c.arm("ungrounded").mae[s] for s in c.seeds)
                      <= max(c.arm("grounded_a").mae[s] for s in c.seeds),
                      lambda c: A(c, "ungrounded", "grounded_a"),
                      quote="the per-seed values overlap and one of the five gains reverses"),
                Claim("the per-seed gains straddle the co-adapted arm's cost",
                      lambda c: (min(c.per_seed_gain())
                                 < (c.controls["grounded_a_truetrain"]
                                    - c.arm("grounded_a").mae[42])
                                 < max(c.per_seed_gain())),
                      lambda c: A(c, "ungrounded", "grounded_a") + " against the seed-42 control",
                      quote="per-seed gains ... straddle the co-adapted arm's"),
            ],
        ),
        DisplayRow(
            key="degrades the",
            binds=[
                Bind("groups and solutes",
                     r"\(\$(\d+)\$ groups, \$(\d+)\$ solutes\), (\d+) seeds",
                     lambda c: (str(c.ranking["n_groups"]), str(c.ranking["n_solutes"]),
                                str(len(c.seeds))),
                     lambda c: c.ranking["path"]),
                Bind("pooled Spearman contrast",
                     r"Spearman \$([-+][\d.]+)\$ \$\[([-+][\d.]+),([-+][\d.]+)\]\$ pooled",
                     lambda c: (fmt(c.ranking["spearman"][0], 3, sign=True),
                                fmt(c.ranking["spearman"][1], 3, sign=True),
                                fmt(c.ranking["spearman"][2], 3, sign=True)),
                     lambda c: c.ranking["path"] + " :: pooled_over_seeds.spearman"),
                Bind("pooled nDCG@3 contrast",
                     r"nDCG@3 \$([-+][\d.]+)\$ \$\[([-+][\d.]+),([-+][\d.]+)\]\$",
                     lambda c: (fmt(c.ranking["ndcg"][0], 3, sign=True),
                                fmt(c.ranking["ndcg"][1], 3, sign=True),
                                fmt(c.ranking["ndcg"][2], 3, sign=True)),
                     lambda c: c.ranking["path"] + " :: pooled_over_seeds.ndcg"),
                Bind("pooled top-1 contrast",
                     r"top-1 \$([-+][\d.]+)\$ \$\[([-+][\d.]+),([-+][\d.]+)\]\$ pooled only",
                     lambda c: (fmt(c.ranking["top1"][0], 3, sign=True),
                                fmt(c.ranking["top1"][1], 3, sign=True),
                                fmt(c.ranking["top1"][2], 3, sign=True)),
                     lambda c: c.ranking["path"] + " :: pooled_over_seeds.top1"),
                Bind("the worst-seed crystal-term drift",
                     r"\\max\|\\Delta\\Phi\|=([\d.]+)\\times10\^\{-(\d+)\}",
                     lambda c: (fmt(c.ranking["phi_max"], 1), str(c.ranking["phi_exp"])),
                     lambda c: c.ranking["path"]
                               + " :: seed_*.integrity.phi_max_abs_diff_vs_grounded_a.oracle"),
                Bind("the share of the MAE gap an in-sample affine map removes",
                     r"removes \$(\d+)\\%\$ of the",
                     lambda c: (fmt(100.0 * (c.ranking["mae_gap"] - c.ranking["mae_affine_gap"])
                                    / c.ranking["mae_gap"], 0),),
                     lambda c: c.ranking["path"]
                               + " :: pooled_over_seeds.{mae,mae_affine}.diff"),
                Bind("groups whose fitted map increases in both arms at every seed",
                     r"in \$(\d+)\$ of the \$(\d+)\$ groups in both arms",
                     lambda c: (need(c.increasing, "all_seeds", "the both-increasing group count"),
                                need(c.increasing, "n_groups", "the group count")),
                     lambda c: "per-group least-squares slopes recomputed from "
                               + A(c, "grounded_a", "oracle")),
            ],
            claims=[
                Claim("all three per-seed Spearman intervals exclude zero",
                      lambda c: all(hi < 0 for _, _, hi in c.ranking["spearman_per_seed"]),
                      lambda c: c.ranking["path"]
                                + " :: seed_*.contrasts.oracle_minus_grounded_a.spearman.ci95",
                      quote="all three per-seed intervals excluding zero"),
                Claim("two of three per-seed top-1 intervals span zero",
                      lambda c: sum(lo <= 0 <= hi for _, lo, hi in c.ranking["top1_per_seed"])
                      == 2,
                      lambda c: c.ranking["path"]
                                + " :: seed_*.contrasts.oracle_minus_grounded_a.top1.ci95",
                      quote="two of three per-seed intervals spanning zero"),
            ],
        ),
    ]


def accuracy_row() -> DisplayRow:
    return DisplayRow(
        key="Physics arm vs",
        binds=[
            Bind("the labelled row set",
                 r"labelled test rows \(\$(\d+)\$ of \$(\d+)\$\)",
                 lambda c: (str(c.root.n_lock), str(c.root.n_total_rows)),
                 lambda c: f"cross-arm lock over {A(c,'grounded_a')}"),
            Bind("physics minus DirectGNN MAE",
                 r"\$([-+][\d.]+)\$ between separately tuned",
                 lambda c: (fmt(c.physics_penalty, 2, sign=True),),
                 lambda c: A(c, "grounded_a", "directgnn")),
        ],
    )


def abstract_row() -> DisplayRow:
    r"""Page 1, every numeral of it.

    THE THREE ARM MEANS ARE BOUND TO THE SAME ARTIFACT THE BODY'S COPIES USE -- the per-seed
    prediction deposits under the results root -- so the abstract cannot drift from
    \S\ref{sec:paradox} without one of the two failing.  The margin sentence is bound to the
    glycol-ether deposit, which is what makes "the abstract, the body and the deposit agree" a
    checked property rather than an intention: change the interval in the deposit and re-run, and
    this fires until the abstract is re-typed.

    TWO SEED COUNTS ARE PRINTED HERE AND THEY ARE NOT THE SAME COUNT.  "over three seeds" is the
    sigma-grounding arms and is BOUND to the seeds actually in ``--root``, so the five-seed re-run
    rewrites it and this check enforces that.  "on separate three-seed runs" is the n=44
    compensation-surrogate family at seeds 0, 1 and 2, which the re-run does not touch; it is
    change-DETECTED against the literal "three" and is not a fact about ``--root``.  An editor
    discharging "the abstract's seed count" who changes that one has changed the wrong number,
    and this is the check that says so.
    """
    dep = glycol_deposit()
    rows, conv = dep["row_set"], dep["converged_interval"]
    margin = dep["point_estimates"]["margin"]
    return DisplayRow(
        key="",
        binds=[
            Bind("the supervision arm means (ungrounded -> grounded)",
                 r"from \$([\d.]+)\$ to \$([\d.]+)\$ over",
                 lambda c: (fmt(c.arm("ungrounded").mae_mean, 3),
                            fmt(c.arm("grounded_a").mae_mean, 3)),
                 lambda c: A(c, "ungrounded", "grounded_a")),
            Bind("the abstract's OWN seed count (the sigma-grounding arms)",
                 r"over (\w+) seeds",
                 lambda c: (word(len(c.seeds)),),
                 lambda c: f"seed directories under {rel(c.root.root)}"),
            Bind("the sigma-oracle arm mean",
                 r"error to \$([\d.]+)\$ at inference",
                 lambda c: (fmt(c.arm("oracle").mae_mean, 3),),
                 lambda c: A(c, "oracle")),
            # RE-ANCHORED 2026-08-11.  The abstract's parenthetical used to carry rows and PAIRS;
            # it now carries rows and the two CLUSTER counts, and it prints both estimators'
            # margins.  Every numeral in the sentence is bound, the two cluster counts included.
            Bind("the glycol-ether margin, its row and cluster counts, its interval, and the "
                 "pre-declared estimator's margin",
                 # THE CLASS NAME IS THE BODY'S NOW, 2026-08-11 (round 7): "hydrocarbon and
                 # halobenzene" and not "nonpolar".  Two of the 19 are halobenzenes
                 # (Clc1ccccc1, Fc1ccccc1); "nonpolar" is right in this closure's own typing --
                 # a halobenzene is entirely non-hydrogen-bonding -- but in a solution-thermo
                 # abstract it reads as a claim about dipolarity, which chlorobenzene refutes.
                 # The body one page later already says "a hydrocarbon or a halobenzene".  This
                 # gate FAILS on the change rather than skipping, which is what it is for;
                 # re-point it here rather than loosening the class out of the pattern.
                 r"standing, \$(\d+)\$ rows over \$(\d+)\$ solvents and \$(\d+)\$ hydrocarbon and "
                 r"halobenzene "
                 r"solutes, its error exceeding its inputs' by \$([\d.]+)\$ \(\$(\d+)\\%\$ interval "
                 r"\$\[([-+][\d.]+),([-+][\d.]+)\]\$\), and \$([\d.]+)\$ under",
                 # Rounded HERE, half-up, from the deposit's own endpoints -- not read out of its
                 # ``printed_as`` field, so the deposit cannot pre-round its way past this check.
                 lambda c: (str(rows["n"]), str(rows["n_solvents"]), str(rows["n_solutes"]),
                            fmt(margin, 2), "90",
                            fmt(conv["ci90_lo"], 2, sign=True),
                            fmt(conv["ci90_hi"], 2, sign=True),
                            fmt(crossfit_glycol_margin(), 2)),
                 lambda c: f"{rel(GLYCOL_CI)} and {rel(CROSSFIT_MAP)} (the $90$ is the "
                           "estimator's declared coverage and is change-detected, not derived)"),
            Bind("the size of the search that row set is the survivor of",
                 r"is a \$(\d+)\$-fold search's survivor",
                 lambda c: (str(map_stratum_count()),),
                 lambda c: f"{rel(ADMISSIBILITY)}, broad_477 / row unit / residual-only "
                           "convention, distinct (axis, stratum)"),
            Bind("the SURROGATE family's seed count -- DECLARED, not this tree's",
                 r"on separate (\w+)-seed runs",
                 lambda c: ("three",),
                 lambda c: "the n=44 compensation-surrogate family at seeds 0, 1, 2, which the "
                           "sigma-grounding re-run does not touch"),
        ],
        claims=[
            # The abstract prints that interval to two decimals.  Whether it MAY is a property of
            # the deposit, not of the sentence: at 12 x 100000 draws the lower endpoint stood
            # 0.9 Monte-Carlo standard errors from a rounding boundary, so its printed second
            # decimal was a property of the seed set.  This is the check that says the draw count
            # is still high enough to have earned the digit.
            Claim("the printed endpoints are determined at two decimals",
                  lambda c: bool(conv.get("printing_is_determined")),
                  lambda c: f"{rel(GLYCOL_CI)}: boundary_margin_se "
                            f"{conv.get('boundary_margin_se')}, se "
                            f"({conv.get('se_lo')}, {conv.get('se_hi')}) over "
                            f"{conv.get('n_draws')} draws",
                  quote="$[+1.25,+2.87]$ printed to two decimals"),
        ],
    )


def runs_row() -> DisplayRow:
    return DisplayRow(
        key=r"$\sigma$-grounding arms, GPU, full corpus",
        binds=[
            Bind("the printed seed list",
                 r"\$((?:\d+,)*\d+)\$, mean\$\\pm\$sd",
                 lambda c: (",".join(str(s) for s in c.seeds),),
                 lambda c: f"seed directories under {rel(c.root.root)}"),
            Bind("the row count the mean is taken on",
                 r"n\{=\}(\d+)\$ labelled test rows",
                 lambda c: (str(c.root.n_lock),),
                 lambda c: f"cross-arm lock over {A(c,'grounded_a')}"),
            # The third cell indexes both headline numbers, and the sheet's row 7 requires all
            # three cells of this row to move together, so they are checked as one anchor.
            Bind("the substitution penalty and the supervision gain this row indexes",
                 r"the \$([-+][\d.]+)\$ and \$([-+][\d.]+)\$",
                 lambda c: (fmt(c.penalty, 2, sign=True), fmt(-c.gain, 2, sign=True)),
                 lambda c: A(c, "oracle", "grounded_a", "ungrounded")),
        ],
    )


def ledger_notes_row() -> DisplayRow:
    """Notes a--h at the foot of the ledger's third part.

    Note (c) is the one with a measurement in it: it asserts that the seed-42 control arms carry
    the identical labelled set, so that rows 2 and 3 of block 1 are on the same rows as row 1.
    It is checked by taking the intersection over all four arms and reporting its size, which is
    the assertion itself rather than a proxy for it.
    """
    return DisplayRow(
        key="",
        binds=[
            Bind("note (c): the seed-42 control arms carry the same labelled set",
                 r"The same \$(\d+)\$ rows: the seed-\$(\d+)\$ control arms",
                 lambda c: (str(int(c.controls["n_lock"])), "42"),
                 lambda c: f"intersection of {rel(PUBLISHED_ROOT)}/seed_42/"
                           "{grounded_a,oracle,grounded_a_truetrain,channel_swap}"
                           "_predictions.csv"),
        ],
    )


def controls_row() -> DisplayRow:
    """Table S25's second row: the two seed-42 controls, whose values are K-disposition.

    They are not retrained, so they are read from --published-root whatever --root is; that is
    exactly what makes them checkable today and still checkable after the substitution.
    """
    return DisplayRow(
        key="Co-adaptation and channel-swap oracle controls",
        binds=[
            Bind("the control seed",
                 r"\$(\d+)\$ only: a sign",
                 lambda c: ("42",),
                 lambda c: f"{rel(PUBLISHED_ROOT)}/seed_42/"),
            Bind("the co-adaptation and channel-swap costs this row indexes",
                 r"the \$([-+][\d.]+)\$ and \$([-+][\d.]+)\$ of",
                 lambda c: (fmt(c.controls["grounded_a_truetrain"]
                                - c.published.arms["grounded_a"].mae[42], 2, sign=True),
                            fmt(c.controls["channel_swap"]
                                - c.published.arms["grounded_a"].mae[42], 2, sign=True)),
                 lambda c: f"{rel(PUBLISHED_ROOT)}/seed_42/"
                           "{grounded_a_truetrain,channel_swap,grounded_a}_predictions.csv"),
        ],
    )


# --------------------------------------------------------------------------- caption rule
@dataclass
class CaptionSpec:
    label: str
    rerun_arms: tuple[str, ...]      # arm words at least one of which the statement must name
    kind: str                        # "float" (the seven) or "map" (the two)
    binds: list[Bind] = field(default_factory=list)
    declared: list[str] = field(default_factory=list)


def caption_specs() -> list[CaptionSpec]:
    return [
        CaptionSpec(
            "fig:paradox", ("ungrounded", "grounded", "oracle"), "float",
            binds=[
                Bind("the labelled row set",
                     r"on the \$(\d+)\$ labelled test rows",
                     lambda c: (str(c.root.n_lock),),
                     lambda c: f"cross-arm lock over {A(c,'grounded_a')}"),
                Bind("the seed count the solid bars carry",
                     r"Solid bars: (\w+)\s*seeds",
                     lambda c: (word(len(c.seeds)),),
                     lambda c: f"seed directories under {rel(c.root.root)}"),
                Bind("the seed of the hatched controls",
                     r"co-adaptation controls, seed \$(\d+)\$ only",
                     lambda c: ("42",),
                     lambda c: f"{rel(PUBLISHED_ROOT)}/seed_42/"),
            ],
        ),
        CaptionSpec(
            "fig:parity-lnx2", ("ungrounded", "grounded", "reference"), "float",
            binds=[
                # Re-anchored 2026-08-10: the caption was rewritten when Figure 3 was redrawn,
                # and the check caught it -- two numerals fell out of every binding and were
                # reported UNREGISTERED, which is the property this file exists for.
                Bind("the labelled row set",
                     r"on the \$(\d+)\$ labelled test rows",
                     lambda c: (str(c.root.n_lock),),
                     lambda c: f"cross-arm lock over {A(c,'grounded_a')}"),
                # The seed moved OUT of the caption and INTO the figure, where the redraw prints
                # it beside panel (a).  A numeral drawn inside a PDF is not reachable from here,
                # so the caption no longer claims it and this binding no longer looks for it;
                # the figure's own generator carries the seed in its .numbers.json sidecar.
                # RE-ANCHORED 2026-08-11 (round 7): the caption said the axes "span the measured
                # range" and called these the predictions that fall "below it", where the frame is
                # the measured range padded by 4% (make_parity_figure.py) and 69 is the count below
                # the PADDED frame -- 87 fall below the measured minimum itself.  The caption now
                # says frame; the count is unchanged and still comes from the sidecar.
                Bind("the predictions drawn below the axis",
                     r"its \$(\d+)\$ predictions that fall\s+below",
                     lambda c: (str(_parity_sidecar()["panels"]["oracle"]["n_below_axis"]),),
                     lambda c: rel(_PARITY_JSON)),
                Bind("the composition of the locked rows",
                     r"\$(\d+)\$ solute--solvent pairs over \$(\d+)\$ solutes and \$(\d+)\$ solvents",
                     lambda c: (str(c.root.facts["n_pairs"]), str(c.root.facts["n_solutes"]),
                                str(c.root.facts["n_solvents"])),
                     lambda c: f"cross-arm lock over {A(c,'grounded_a')}"),
                Bind("the temperature span of the locked rows",
                     r"between \$(\d+)\$ and \$(\d+)\$\\,K",
                     lambda c: (str(int(np.floor(c.root.facts["t_min"]))),
                                str(int(np.ceil(c.root.facts["t_max"])))),
                     lambda c: f"cross-arm lock over {A(c,'grounded_a')}"),
                # RETIRED 2026-08-10 with the clause it checked.  The caption used to reconcile the
                # panels' seed-42 statistics against Figure 2's three-seed bars in three sentences,
                # one of which bounded the departure "by at most 0.05 in MAE"; the redraw prints the
                # seed in the figure instead, so there is no such clause to check.  The binding is
                # removed rather than re-anchored: a binding kept alive against text that no longer
                # exists reports MISSING forever and trains a reader to ignore the report.
            ],
        ),
        CaptionSpec("tab:baselines", ("grounded", "oracle"), "float"),
        CaptionSpec("tab:si-baselines-full", ("grounded", "oracle"), "float"),
        CaptionSpec(
            "tab:si-arms", ("ungrounded", "grounded", "oracle"), "float",
            binds=[
                Bind("the seed count and the row set",
                     # RE-ANCHORED 2026-08-12. The caption no longer opens with one seed count,
                     # because the table's rows no longer share one: the three re-run arms carry
                     # five and the three published arms carry three, so the count moved into the
                     # sentence that says which rows are which and the row set stands alone.
                     r"the \$n\{=\}(\d+)\$ labelled test rows.*?carry (\d+) seeds",
                     lambda c: (str(c.root.n_lock), str(len(c.seeds))),
                     lambda c: f"cross-arm lock over {A(c,'grounded_a')}"),
                Bind("the seed count the sd is taken over",
                     r"over the (\w+)\s*seeds",
                     lambda c: (word(len(c.seeds)),),
                     lambda c: f"seed directories under {rel(c.root.root)}"),
            ],
        ),
        CaptionSpec("tab:claims", ("grounded", "ungrounded", "oracle"), "float"),
        CaptionSpec("tab:claims-cont2", ("grounded",), "float"),
        CaptionSpec(
            "tab:solvent-map", (), "map",
            binds=[
                Bind("the seed count the spread is over",
                     r"over (\d+) seeds",
                     lambda c: (str(len(c.seeds)),),
                     lambda c: f"seed directories under {rel(c.root.root)}"),
            ],
        ),
        CaptionSpec(
            "tab:solute-map", (), "map",
            binds=[
                Bind("the seed count the spread is over",
                     r"the (\d+)-seed spread",
                     lambda c: (str(len(c.seeds)),),
                     lambda c: f"seed directories under {rel(c.root.root)}"),
            ],
        ),
    ]


# The form of words each kind of caption must carry once the re-run has landed.  Checked as a form,
# not as the mere existence of a caption: the inventory's requirement is that the caption SAY which
# arms came from the re-run, and a caption can exist while saying nothing of the kind.
#
# The word "re-run" alone will not do, and that is not pedantry -- tab:baselines' caption already
# reads "external models re-run here on an easier by-solute split", which is a different re-run
# entirely.  The phrase must be QUALIFIED, by "leak-free" or by the seed count, so that the
# incumbent sentence cannot satisfy the rule by accident.
def rerun_phrase(n_seeds: int) -> re.Pattern:
    return re.compile(rf"(?:leak-free|{word(n_seeds)}-seed)[- ]?(?:leak-free[- ])?re-?run", re.I)


MAP_PHYSICS_WORD = re.compile(r"physics", re.I)


# --------------------------------------------------------------------------- checking engine
def _safe_artifact(b: Bind, ctx: Ctx) -> str:
    """The artifact description, or a placeholder when it too depends on the absent arm."""
    try:
        return b.artifact(ctx)
    except KeyError:
        return f"{rel(ctx.root.root)} (the arm is not deposited there)"


def check_row(display: str, text: str, row: DisplayRow, ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    claimed: list[tuple[int, int]] = []
    for b in row.binds:
        m = re.search(b.pattern, text)
        if m is None:
            out.append(Finding("MISSING", display, b.what,
                               printed="(pattern not found)", expected="/".join(b.expect(ctx)),
                               artifact=b.artifact(ctx),
                               note=f"the display no longer matches /{b.pattern}/ -- it was "
                                    "reworded, so this binding must be re-anchored before the "
                                    "numeral can be checked at all"))
            continue
        claimed.append(m.span(0))
        try:
            exp = b.expect(ctx)
        except KeyError as exc:
            # The arm this cell quotes is not in the tree yet.  That is the state the leak-free
            # tree will be in first -- precondition P0.3 of the discharge sheet: the sigma-oracle
            # is an inference pass that has not been run -- and it must be reported as "cannot be
            # checked", never silently skipped and never confused with agreement.
            out.append(Finding("MISSING", display, b.what,
                               printed=" | ".join(m.groups()),
                               expected=f"(cannot compute: {exc})",
                               artifact=_safe_artifact(b, ctx),
                               note="the arm this cell quotes is absent from the results root, so "
                                    "this numeral is UNCHECKED -- not verified, not refuted"))
            continue
        got = tuple(m.groups())
        if got != exp:
            out.append(Finding("MISMATCH", display, b.what,
                               printed=" | ".join(got), expected=" | ".join(exp),
                               artifact=b.artifact(ctx)))
        else:
            out.append(Finding("OK", display, b.what, printed=" | ".join(got),
                               expected=" | ".join(exp), artifact=b.artifact(ctx)))
    for cl in row.claims:
        try:
            ok = cl.holds(ctx)
        except KeyError as exc:
            out.append(Finding("MISSING", display, cl.what,
                               printed=cl.quote or "(word claim)",
                               expected=f"(cannot evaluate: {exc})",
                               artifact=rel(ctx.root.root),
                               note="the arm this claim is about is absent from the results root, "
                                    "so the claim is UNCHECKED -- not verified, not refuted"))
            continue
        out.append(Finding("OK" if ok else "MISMATCH", display, cl.what,
                           printed=cl.quote or "(word claim)",
                           expected="holds" if ok else "DOES NOT HOLD on this root",
                           artifact=cl.artifact(ctx)))
    # coverage: every numeral not inside a matched span must be declared
    leftover = [n for n in numerals(text)
                if not any(s <= n.start and n.end <= e for s, e in claimed)]
    declared = list(row.declared)
    for n in leftover:
        if n.token in declared:
            declared.remove(n.token)
        else:
            out.append(Finding("UNREGISTERED", display, f"numeral {n.token!r}",
                               printed=n.token, expected="(no binding, no declaration)",
                               artifact=row.owner or "unknown",
                               note="a numeral in a hand-transcribed display that nothing checks; "
                                    "bind it to an artifact or declare it with its owner. Context: "
                                    + _context(text, n)))
    for tok in declared:
        out.append(Finding("STALE", display, f"declared numeral {tok!r} is gone",
                           printed="(absent)", expected=tok, artifact=row.owner or "unknown",
                           note="the registry expected this numeral in this display; it was edited "
                                "away or moved, so the registry no longer describes the display"))
    return out


def _context(text: str, n: Numeral, width: int = 44) -> str:
    lo = max(0, n.start - width)
    hi = min(len(text), n.end + width)
    return "..." + text[lo:hi].strip() + "..."


def check_float(display: str, block: str, specs: Sequence[DisplayRow], ctx: Ctx) -> list[Finding]:
    """Every row of the float's tabular, whether or not the registry remembers it.

    COVERAGE IS A PROPERTY OF THE FLOAT, NOT OF THE ROWS SOMEONE SELECTED.  ``check_row`` accounts
    for every numeral inside the text it is handed, which makes a numeral unregisterable only if
    the row carrying it was handed over in the first place.  Before this function existed the rows
    were selected one by one from a registry, so a row NOBODY registered -- a row appended to the
    float during the five-seed substitution, carrying an ``n``, a seed count and a pair of MAEs
    that no artifact ever produced -- was never read, and the run printed ``UNREGISTERED 0`` and
    exited zero.  A verifier appended exactly such a row (``n=9999``, ``7 seeds``,
    ``3.14 -> 2.72``) and the script certified the float.

    So the registry is now checked for exhaustiveness in both directions: a row no selector
    matches is UNREGISTERED and fatal, and two selectors matching one row stop the script.  The
    coverage claim the module docstring makes -- that every numeral in the enrolled displays is
    bound or declared -- is only true if this holds.
    """
    rows = tabular_rows(block)
    if not rows:
        return [Finding("MISMATCH", display, "the float's tabular",
                        printed="(no rows parsed)", expected="a tabular with rows",
                        artifact=f"paper/ :: {display}",
                        note="the float was restructured, so nothing in it is being checked")]
    findings: list[Finding] = []
    claimed_by: dict[int, str] = {}
    for spec in specs:
        i = pick_row_index(rows, spec.key, display)
        if i in claimed_by:
            raise SystemExit(
                f"two registry selectors of {display} match the same row -- {claimed_by[i]!r} and "
                f"{spec.key!r}.  One row, one entry: overlapping selectors leave some OTHER row "
                "unclaimed while the count of claimed rows still looks right."
            )
        claimed_by[i] = spec.key
        findings += check_row(display, rows[i], spec, ctx)
    for i, text in enumerate(rows):
        if i in claimed_by:
            continue
        findings.append(Finding(
            "UNREGISTERED", display, f"row {i + 1} of {len(rows)} is in the float and in no "
                                     "registry entry",
            printed=normalise_ws(text)[:160],
            expected="a bound or declared DisplayRow selecting this row",
            artifact=f"paper/ :: {display}",
            note="every numeral this row carries is unchecked, and no count of OK findings says "
                 "so; bind it, or declare it with its owner (--dump-unclaimed prints the "
                 "skeleton)"))
    return findings


# --------------------------------------------------------------------------- TOC graphic
def toc_check(ctx: Ctx, root: Path) -> list[Finding]:
    """The graphic's own strings, derived, against the shipped PDF."""
    sys.path.insert(0, str(REPO / "scripts" / "analysis"))
    try:
        import make_toc_figure  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover - import failure is itself the finding
        return [Finding("MISSING", "tocentry", "make_toc_figure.py is not importable",
                        printed=str(exc), expected="a module exposing toc_lines()",
                        artifact="scripts/analysis/make_toc_figure.py")]
    if not hasattr(make_toc_figure, "toc_lines"):
        return [Finding("MISSING", "tocentry", "make_toc_figure.toc_lines is absent",
                        printed="(no such function)",
                        expected="toc_lines(root, certificate) -> list[str]",
                        artifact="scripts/analysis/make_toc_figure.py",
                        note="the caveat is still a string literal, so re-running the script "
                             "cannot discharge the row")]
    derived = make_toc_figure.toc_lines(root)
    pdf = ctx.paper / "figs" / "fig_toc.pdf"
    out: list[Finding] = []
    if shutil.which("pdftotext") is None or not pdf.exists():
        return [Finding("PENDING", "tocentry", "shipped graphic not read",
                        printed="", expected="\n".join(derived),
                        artifact=str(pdf),
                        note="pdftotext unavailable or figure absent; the derived lines are "
                             "reported and not compared")]
    txt = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    printed = [normalise_ws(ln) for ln in txt.splitlines() if normalise_ws(ln)]
    for line in derived:
        if normalise_ws(line) in printed:
            out.append(Finding("OK", "tocentry", "derived line is in the shipped graphic",
                               printed=line, expected=line, artifact=str(rel(pdf))))
        else:
            out.append(Finding("MISMATCH", "tocentry", "derived line is NOT in the shipped graphic",
                               printed="; ".join(p for p in printed if len(p) > 30) or "(none)",
                               expected=line, artifact=str(rel(pdf)),
                               note="re-run MPLBACKEND=Agg python scripts/analysis/"
                                    "make_toc_figure.py --e5-dir "
                                    f"{rel(root)}"))
    # the caveat must be gone once the root's own certificate certifies the re-run
    caveat = "not certified leak-free"
    still_printed = any(caveat in p for p in printed)
    should_print = any(caveat in ln for ln in derived)
    if still_printed != should_print:
        out.append(Finding("MISMATCH", "tocentry", "the leak-free caveat's presence",
                           printed="present" if still_printed else "absent",
                           expected="present" if should_print else "absent",
                           artifact=str(rel(root / "provenance_certificate.json")),
                           note="the caveat is derived from the certificate; the shipped graphic "
                                "disagrees with what the certificate says"))
    return out


# --------------------------------------------------------------------------- ranking artifact
def load_ranking(path: Path, seeds: Sequence[int]) -> dict:
    if not path.exists():
        raise SystemExit(
            f"ranking artifact {path} not found. Row 13 of the discharge sheet produces it with\n"
            f"    python results/e5_sigma_grounding/ranking/rank_final.py <outdir>\n"
            "(and that script hard-codes BASE and SEEDS at module scope -- see the sheet, Sec. 5.9)"
        )
    d = json.loads(path.read_text())
    pooled = d["pooled_over_seeds"]
    shown = rel(path)
    seed_keys = [f"seed_{s}" for s in seeds if f"seed_{s}" in d]
    phi = [d[k]["integrity"]["phi_max_abs_diff_vs_grounded_a"]["oracle"] for k in seed_keys]
    phi_max = max(phi)
    phi_exp = int(np.floor(np.log10(phi_max))) if phi_max > 0 else 0
    return {
        "path": shown,
        "n_groups": pooled["n_common_groups"],
        "n_solutes": pooled["spearman"]["n_solute_clusters"],
        "spearman": (pooled["spearman"]["diff"], *pooled["spearman"]["ci95"]),
        "ndcg": (pooled["ndcg"]["diff"], *pooled["ndcg"]["ci95"]),
        "top1": (pooled["top1"]["diff"], *pooled["top1"]["ci95"]),
        "mae_gap": pooled["mae"]["diff"],
        "mae_affine_gap": pooled["mae_affine"]["diff"],
        "phi_max": phi_max / 10 ** phi_exp,
        "phi_exp": -phi_exp,
        "spearman_per_seed": [
            (d[k]["contrasts"]["oracle_minus_grounded_a"]["spearman"]["diff"],
             *d[k]["contrasts"]["oracle_minus_grounded_a"]["spearman"]["ci95"])
            for k in seed_keys],
        "top1_per_seed": [
            (d[k]["contrasts"]["oracle_minus_grounded_a"]["top1"]["diff"],
             *d[k]["contrasts"]["oracle_minus_grounded_a"]["top1"]["ci95"])
            for k in seed_keys],
    }


# --------------------------------------------------------------------------- report
def report(findings: Sequence[Finding], *, verbose: bool) -> str:
    lines: list[str] = []
    by_sev: dict[str, list[Finding]] = {}
    for f in findings:
        by_sev.setdefault(f.severity, []).append(f)
    order = ["MISMATCH", "UNREGISTERED", "STALE", "MISSING", "PENDING", "OK"]
    lines.append("=" * 96)
    lines.append("hand-transcribed display check")
    lines.append("=" * 96)
    lines.append("  ".join(f"{s}: {len(by_sev.get(s, []))}" for s in order))
    lines.append("")
    for sev in order:
        items = by_sev.get(sev, [])
        if not items or (sev == "OK" and not verbose):
            continue
        lines.append(f"--- {sev} ({len(items)}) " + "-" * (76 - len(sev)))
        for f in items:
            lines.append(f"  [{f.display}] {f.item}")
            if sev == "OK":
                lines.append(f"      value     {f.printed}")
            else:
                lines.append(f"      printed   {f.printed}")
                lines.append(f"      artifact  {f.artifact}")
                lines.append(f"      expected  {f.expected}")
            if f.note:
                lines.append(f"      note      {f.note}")
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- main
def build_context(args: argparse.Namespace) -> Ctx:
    root = Path(args.root)
    published = Path(args.published_root)
    if not root.is_absolute():
        root = REPO / root
    if not published.is_absolute():
        published = REPO / published
    seeds = resolve_seeds(root, args.seeds, "--seeds")
    root_stats = collect_root(root, seeds)
    if published == root:
        pub_stats = root_stats
    else:
        pub_seeds = resolve_seeds(published, args.published_seeds, "--published-seeds")
        pub_stats = collect_root(published, pub_seeds)
    # Row 13 of the sheet puts the re-run's ranking artifact at <root>/ranking/rank_final.json.
    # Prefer it when it exists, fall back to the published one, and say which was used in the
    # report -- a ranking table read off the wrong tree is exactly the substitution defect the
    # sheet's ordering constraint H exists to prevent.
    if args.ranking_json:
        ranking_path = Path(args.ranking_json)
        if not ranking_path.is_absolute():
            ranking_path = REPO / ranking_path
    elif (root / "ranking" / "rank_final.json").exists():
        ranking_path = root / "ranking" / "rank_final.json"
    else:
        ranking_path = published / "ranking" / "rank_final.json"
    under_root = str(ranking_path).startswith(str(root))
    ranking = load_ranking(ranking_path, seeds if under_root else pub_stats.seeds)
    rerun = (args.rerun_landed == "yes") or (
        args.rerun_landed == "auto" and root != PUBLISHED_ROOT)
    return Ctx(
        root=root_stats,
        published=pub_stats,
        controls=seed42_controls(published),
        ranking=ranking,
        increasing=both_increasing_groups(root, published, seeds),
        seeds=seeds,
        rerun_landed=rerun,
        paper=Path(args.paper) if Path(args.paper).is_absolute() else REPO / args.paper,
    )


def cross_root_lock_check(ctx: Ctx) -> list[Finding]:
    """The +0.14 differences an arm in --root against an arm in --published-root.

    That subtraction is only a measurement if both arms score the identical rows.  When the two
    roots are the same tree it is true by construction; when they are not -- which is the whole
    five-seed substitution -- it is a fact about two separate runs and is checked here.
    """
    if ctx.root.root == ctx.published.root:
        return [Finding("OK", "cross-root", "the row lock is shared",
                        printed=f"one tree, n={ctx.root.n_lock}", expected="identical",
                        artifact=str(rel(ctx.root.root)))]
    ref = set(ctx.published.lock[ctx.published.seeds[0]])
    bad = []
    for seed in ctx.seeds:
        keys = set(ctx.root.lock[seed])
        if keys != ref:
            bad.append(f"seed {seed}: {len(keys - ref)} rows not in the published lock, "
                       f"{len(ref - keys)} missing")
    if bad:
        return [Finding("MISMATCH", "cross-root", "the row lock is shared across the two roots",
                        printed="; ".join(bad),
                        expected=f"the identical {len(ref)} keys in every seed of both roots",
                        artifact=f"{rel(ctx.root.root)} against "
                                 f"{rel(ctx.published.root)}",
                        note="a cross-root difference such as the +0.14 of the accuracy row is not "
                             "a measurement unless both arms score the same rows")]
    return [Finding("OK", "cross-root", "the row lock is shared across the two roots",
                    printed=f"n={len(ref)} in every seed of both roots", expected="identical",
                    artifact=f"{rel(ctx.root.root)} against "
                             f"{rel(ctx.published.root)}")]


def run_checks(ctx: Ctx) -> list[Finding]:
    findings: list[Finding] = cross_root_lock_check(ctx)
    paper = ctx.paper

    # ---- the claims ledger, three floats.  Each float is checked whole: the bound rows, the
    # rows declared to another run family, and -- the property that was missing -- the assertion
    # that between them they exhaust the float's tabular.
    _, claims_block = find_display(paper, "tab:claims")
    findings += check_float("tab:claims", claims_block,
                            [*ledger_rows(), *LEDGER_DECLARED_ROWS.get("tab:claims", [])], ctx)

    for label in ("tab:claims-cont", "tab:claims-cont2"):
        _, block = find_display(paper, label)
        specs = list(LEDGER_DECLARED_ROWS.get(label, []))
        if label == "tab:claims-cont2":
            specs.append(accuracy_row())
            findings += check_row(label + " (notes a-h)", tabnotes_of(block),
                                  ledger_notes_row(), ctx)
        findings += check_float(label, block, specs, ctx)

    # ---- the abstract, which carries three arm means and no label to reach them by
    findings += check_row("abstract (page 1)", find_abstract(paper), abstract_row(), ctx)

    # ---- the run-family table's sigma-grounding row
    _, runs_block = find_display(paper, "tab:runs")
    findings += check_float("tab:runs", runs_block,
                            [runs_row(), controls_row(),
                             *LEDGER_DECLARED_ROWS.get("tab:runs", [])], ctx)
    findings += deposit_note_check(ctx)

    # ---- the nine captions
    findings += caption_checks(ctx)

    # ---- the table-of-contents graphic
    findings += toc_check(ctx, ctx.root.root)
    return findings


def deposit_note_check(ctx: Ctx) -> list[Finding]:
    """Table S25's float-note claims every row of every arm at every seed is re-analysable.

    Two separate things are asserted and both are checked.  (a) The three arms the re-run produces
    must be deposited at every seed of --root -- an absent one is not "an arm that lives elsewhere",
    it is a hole in the claim.  (b) Every per-row file that IS deposited must be full length: the
    note exists because the seed-44 oracle file was once deposited truncated, and a short file
    re-analyses to a different number without saying so.
    """
    missing, short = [], []
    expect_rows = ctx.root.n_total_rows
    checked = 0
    for seed in ctx.seeds:
        for arm in INTERSECTING_ARMS:
            p = _pred_path(ctx.root.root, seed, arm)
            if not p.exists():
                if arm in RERUN_ARMS:
                    missing.append(f"seed_{seed}/{arm}")
                continue        # an arm the re-run does not produce legitimately lives elsewhere
            checked += 1
            n = sum(1 for _ in p.open()) - 1
            if n != expect_rows:
                short.append(f"seed_{seed}/{arm}={n}")
    if missing or short:
        return [Finding("MISMATCH", "tab:runs", "the float-note's deposit claim",
                        printed="every row of every arm at every seed is re-analysable "
                                "from the deposit",
                        expected=f"the {len(RERUN_ARMS)} re-run arms at each of "
                                 f"{len(ctx.seeds)} seeds, every file {expect_rows} rows",
                        artifact=str(rel(ctx.root.root)),
                        note=("absent: " + ", ".join(missing) if missing else "")
                             + ("; truncated: " + ", ".join(short) if short else ""))]
    return [Finding("OK", "tab:runs", "the float-note's deposit claim",
                    printed=f"{checked} files x {expect_rows} rows",
                    expected="all full length, re-run arms present at every seed",
                    artifact=str(rel(ctx.root.root)))]


def caption_checks(ctx: Ctx) -> list[Finding]:
    findings: list[Finding] = []
    for spec in caption_specs():
        _, block = find_display(ctx.paper, spec.label)
        cap = caption_of(block)
        if not cap:
            findings.append(Finding("MISSING", spec.label, "caption",
                                    printed="(none)", expected="a \\caption{...}",
                                    artifact="paper/"))
            continue
        row = DisplayRow(key="", binds=spec.binds, declared=list(spec.declared),
                         owner=f"caption of {spec.label}")
        findings += check_row(spec.label + " (caption)", cap, row, ctx)

        # the form-of-words rule
        if spec.kind == "float":
            says_rerun = bool(rerun_phrase(len(ctx.seeds)).search(cap))
            names_arm = any(a in cap.lower() for a in spec.rerun_arms)
            want = (f'a clause of the form "the {spec.rerun_arms[0] if spec.rerun_arms else "..."} '
                    f'... arms come from the {word(len(ctx.seeds))}-seed leak-free re-run": it must '
                    f'carry "leak-free re-run" or "{word(len(ctx.seeds))}-seed re-run" (the bare '
                    f'word "re-run" is not enough) and name at least one of '
                    f'{list(spec.rerun_arms)}')
            if ctx.rerun_landed:
                sev = "OK" if (says_rerun and names_arm) else "MISMATCH"
                findings.append(Finding(
                    sev, spec.label + " (caption)", "the caption rule: which arms came from the "
                                                    "re-run",
                    printed=("names the re-run" if says_rerun else "does NOT name a re-run")
                            + ("; names a re-run arm" if names_arm else "; names no re-run arm"),
                    expected=want,
                    artifact="results/e5_sigma_grounding_leakfree/DISCHARGE_SHEET.md row 34"))
            else:
                findings.append(Finding(
                    "PENDING", spec.label + " (caption)", "the caption rule",
                    printed="no re-run arm in this float yet",
                    expected=want,
                    artifact="results/e5_sigma_grounding_leakfree/DISCHARGE_SHEET.md row 34",
                    note="the rule activates when --root carries a re-run"))
        else:
            says_physics = bool(MAP_PHYSICS_WORD.search(cap))
            seed_word = word(len(ctx.seeds))
            says_seedword = (f"{seed_word}-seed" in cap.lower()
                             or f"{seed_word} seed" in cap.lower())
            want = (f"a clause saying only the physics side is {seed_word}-seed "
                    "(the control side stays published)")
            if ctx.rerun_landed:
                sev = "OK" if (says_physics and says_seedword) else "MISMATCH"
                findings.append(Finding(
                    sev, spec.label + " (caption)", "the map caption rule: only the physics side",
                    printed=("names the physics side" if says_physics
                             else "does NOT name the physics side")
                            + (f"; says {seed_word}-seed" if says_seedword
                               else f"; does NOT say {seed_word}-seed"),
                    expected=want,
                    artifact="results/e5_sigma_grounding_leakfree/DISCHARGE_SHEET.md row 34"))
            else:
                findings.append(Finding(
                    "PENDING", spec.label + " (caption)", "the map caption rule",
                    printed="both sides are published values",
                    expected=want,
                    artifact="results/e5_sigma_grounding_leakfree/DISCHARGE_SHEET.md row 34",
                    note="the rule activates when --root carries a re-run"))
    return findings


def dump_unclaimed(ctx: Ctx) -> str:
    """Print, per row of each enrolled float, the numerals no binding claims.

    Used to build ``LEDGER_DECLARED_ROWS`` in the first place, and to rebuild it when a display
    legitimately changes.  It is a authoring aid, not a check.
    """
    out: list[str] = []
    bound_keys = ({r.key for r in ledger_rows()}
                  | {accuracy_row().key, runs_row().key, controls_row().key})
    for label in ("tab:claims", "tab:claims-cont", "tab:claims-cont2", "tab:runs"):
        _, block = find_display(ctx.paper, label)
        out.append(f'    "{label}": [')
        for row_text in tabular_rows(block):
            if any(k in row_text for k in bound_keys):
                continue
            toks = [n.token for n in numerals(row_text)]
            key = normalise_ws(row_text)[:110].replace("\\", "\\\\").replace('"', r"\"")
            out.append(f'        DisplayRow(key="{key}",')
            out.append(f'                   declared={toks!r},')
            out.append('                   owner=""),')
        out.append("    ],")
    return "\n".join(out)


_HEADER = "the tabular's column header; carries no measurement"
_BLOCK = "a block head of the ledger; carries no measurement"
_IDAC = "decomposition, broad IDAC / VT-2005 (results/b_insuff/, run_b_insuff_*.py)"
_MAP = "the stratified map (results/b_insuff/stratified_map*, run_b_insuff_stratified_map.py)"
_FIDELITY = "closure-fidelity kernels and the kernel residual (run family 'Closure-fidelity kernels')"
_PKA = "the pKa second domain (results/pka_hammett/)"
_SURROGATE = "the n=44 surrogate runs, seeds {0,1,2} (run family 'Latent against its reference')"
_EXTERNAL = "external baselines (results/external_baseline_comparison/)"

# Numerals in the three ledger floats and the run-family table that belong to OTHER run families.
# They are registered here with their owner so that an edit to any of them is detected; the values
# themselves are NOT verified against an artifact by this script.  See the module docstring.
#
# Rebuild with --dump-unclaimed after a legitimate edit, and put the owner back.  A row whose key no
# longer selects exactly one row of its float stops the script: that is deliberate, because a
# silently-unmatched selector is how a display drifts out from under its own checker.
LEDGER_DECLARED_ROWS: dict[str, list[DisplayRow]] = {
    "tab:claims": [
        DisplayRow(key="Claim & Set ($n$)\\tnk{a} & Value, with its uncertainty and scope\\tnk{b}",
                   declared=[], owner=_HEADER),
        DisplayRow(key="\\multicolumn{3}{@{}L{\\dimexpr0.95\\linewidth+4\\tabcolsep\\relax}@{}}{\\emph{The two senses of grounding} (\\S\\ref{",
                   declared=[], owner=_BLOCK),
    ],
    "tab:claims-cont": [
        DisplayRow(key="Claim & Set ($n$)\\tnk{a} & Value, with its uncertainty and scope\\tnk{b}",
                   declared=[], owner=_HEADER),
        DisplayRow(key="\\multicolumn{3}{@{}L{\\dimexpr0.95\\linewidth+4\\tabcolsep\\relax}@{}}{\\emph{Closure against inputs on the activit",
                   declared=[], owner=_BLOCK),
        DisplayRow(key="$\\Bclos>\\Binsuf$ on \\emph{glycol-ether} solvents\\tnk{d,g} & broad IDAC, $182$, $3$ sources & the margin, a low",
                   # +1.25, not +1.26: the deposited interval was under-converged.  At the map's own 3000
                   # draws the endpoint has a Monte-Carlo sd of 0.0195 and ranges [1.209, 1.295]
                   # over forty seeds, so its second decimal was noise.  Converged at 1.2e8 draws
                   # it is 1.25432, which stands 7.2 Monte-Carlo standard errors clear of the
                   # 1.255 rounding boundary -- determined, under the deposit's own four-sigma rule.
                   # NOT '43': the pair count prints in the article's own sentence and in the map
                   # table, not in this ledger cell, whose set column reads "broad IDAC, 182,
                   # 3 sources".  Added here by mistake on 2026-08-10 and reported STALE at once.
                   declared=['182', '3', '+2.04', '+1.25', '+2.87', '+2.94', '0.95', '+1.60',
                             '59', '477', '58', '+1.76', '+1.02', '+2.49'],
                   owner=_IDAC),
        DisplayRow(key="\\ldots\\ on every other stratum of the map & broad IDAC, $59$ strata & \\S\\ref{sec:si-map}, Tables~\\ref{tab:map-",
                   declared=['59'], owner=_MAP),
        DisplayRow(key="\\ldots\\ for either set \\emph{as a whole} & broad IDAC ($477$); VT-2005-matched ($60$) & $+0.51$ (full $+0.95$)",
                   declared=['477', '60', '+0.51', '+0.95', '-0.38', '+0.01', '+0.18', '+0.05'],
                   owner=_IDAC),
        DisplayRow(key="$\\Binsuf^{\\mathrm{up}}$ near stratum-independent, $\\mathrm{MSE}$ not & broad IDAC, $3$ boundable classes; $6$ ",
                   declared=['3', '6', '2.0', '25', '6.8', '51', '0.02', '2000', '9'],
                   owner=_MAP),
        DisplayRow(key="$\\Bclos>\\Binsuf$, 2010 on its \\emph{own} typed latent\\tnk{f} & broad IDAC ($477$); VT-2005-matched ($60$) & $+",
                   declared=['2010', '477', '60', '+1.29', '0.95', '0.9', '0.9', '-0.77', '0.3'],
                   owner=_IDAC),
        DisplayRow(key="\\multicolumn{3}{@{}L{\\dimexpr0.95\\linewidth+4\\tabcolsep\\relax}@{}}{\\emph{Whether a better closure moves the ce",
                   declared=[], owner=_BLOCK),
        DisplayRow(key="The $2002\\to2010$ step lowers the error & broad IDAC ($477$) & $-0.99$ at $P\\approx0.2$: no improvement, and n",
                   declared=['2002', '2010', '477', '-0.99', '0.2', '-0.07', '0.6', '+0.06', '0.6'],
                   owner=_FIDELITY),
        DisplayRow(key="\\ldots but does on the VT-2005 set's chemistry & $57$ shared pairs, UD & $1.78\\to0.77$, $P>0.95$, at fixed pro",
                   declared=['57', '1.78', '0.77', '0.95', '57'], owner=_FIDELITY),
        DisplayRow(key="A fitted kernel residual transfers across solvents & VT-2005-matched ($60$), grouped folds & $-5\\pm16\\%$: span",
                   declared=['60', '-5', '16'], owner=_FIDELITY),
        DisplayRow(key="\\multicolumn{3}{@{}L{\\dimexpr0.95\\linewidth+4\\tabcolsep\\relax}@{}}{\\emph{The same split on a second closure} (",
                   declared=[], owner=_BLOCK),
        DisplayRow(key="A Hammett $\\mathrm pK_a$ closure reverses the substitution's sign between its two poles & OPERA $\\mathrm pK_a$",
                   # 0.083 / 27 / 0.303 entered 2026-08-11: the row used to end on "the clean
                   # pole is well specified only after the quality filter", which read a Jensen
                   # bound that had been squared twice.  It now carries the corrected bound and
                   # the MSE it is a share of.
                   declared=['158', '846', '20', '4', '-0.165', '-0.28', '-0.04', '19', '20',
                             '+0.79', '+0.57', '+0.95', '20', '20', '90', '0.31', '1', '16',
                             '0.083', '27', '0.303', '-0.2', '163', '+0.55'],
                   owner=_PKA),
    ],
    "tab:claims-cont2": [
        DisplayRow(key="Claim & Set ($n$)\\tnk{a} & Value, with its uncertainty and scope\\tnk{b}",
                   declared=[], owner=_HEADER),
        DisplayRow(key="\\multicolumn{3}{@{}L{\\dimexpr0.95\\linewidth+4\\tabcolsep\\relax}@{}}{\\emph{Mechanism} (\\S\\ref{sec:surrogate})}",
                   declared=[], owner=_BLOCK),
        DisplayRow(key="The latent departs from its reference along a shared direction & matched molecules ($44$), 3 seeds & $51\\pm2\\%",
                   declared=['44', '3', '51', '2'], owner=_SURROGATE),
        DisplayRow(key="\\ldots and that departure's top-two mode share exceeds a phase-randomised null & one grounded checkpoint, same",
                   declared=['44', '0.40', '0.22', '0.01'], owner=_SURROGATE),
        DisplayRow(key="\\ldots and that direction \\emph{transfers} to molecules outside the fit & matched molecules ($44$), 3 seeds & ",
                   declared=['44', '3', '4.1', '0.5'], owner=_SURROGATE),
        DisplayRow(key="That departure \\emph{cancels} closure error & not measured & the one direct check is under-powered and runs ag",
                   declared=[], owner=_SURROGATE),
        DisplayRow(key="\\multicolumn{3}{@{}L{\\dimexpr0.95\\linewidth+4\\tabcolsep\\relax}@{}}{\\emph{Accuracy} (\\S\\ref{sec:discussion})}",
                   declared=[], owner=_BLOCK),
    ],
    "tab:runs": [
        DisplayRow(key="Run family & Seeds & What it produced", declared=[], owner=_HEADER),
        DisplayRow(key="Decomposition, VT-2005-matched & none: the closure has no learnable parameters & \\S\\ref{sec:vt2005}; the estim",
                   declared=[], owner=_IDAC),
        DisplayRow(key="Decomposition, broad IDAC, with its design and provenance audit & none & \\S\\ref{sec:broad}: the $+0.51$, the $",
                   declared=['+0.51', '+0.95'], owner=_IDAC),
        DisplayRow(key="The stratified map & none & the $59$ strata, Tables~\\ref{tab:map-full}--\\ref{tab:map-detail}",
                   declared=['59'], owner=_MAP),
        DisplayRow(key="Closure-fidelity kernels & none & \\S\\ref{sec:fidelity}, Table~\\ref{tab:kernels}",
                   declared=[], owner=_FIDELITY),
        DisplayRow(key="Kernel residual & five fit seeds; $\\pm$ is their standard error & the $46\\pm5\\%$ and $-5\\pm16\\%$ of \\S\\ref{sec",
                   declared=['46', '5', '-5', '16'], owner=_FIDELITY),
        DisplayRow(key="Latent against its reference & $0,1,2$; mean$\\pm$sd & \\S\\ref{sec:surrogate}, Fig.~\\ref{fig:surrogate}",
                   declared=['0', '1', '2'], owner=_SURROGATE),
        DisplayRow(key="Closure validation & none & the \\emph{2002} NIST reproduction; Table~\\ref{tab:closure-anchor}. The 2010 reprod",
                   declared=['2002', '2010'], owner=_FIDELITY),
        DisplayRow(key="External baselines & one run each, on a \\emph{by-solute} split and, for two of the rows, a \\emph{random-pair} ",
                   declared=[], owner=_EXTERNAL),
        DisplayRow(key="pKa second domain: decomposition, Hammett probe and bootstrap & $K{=}20$ within-scaffold splits; $G{=}4$ serie",
                   declared=['20', '4'], owner=_PKA),
        DisplayRow(key="Noise floor and encoder probe & none & \\S\\ref{sec:data}, \\S\\ref{sec:gap}",
                   declared=[], owner="noise floor and encoder probe (results/noise_floor/, results/encoder_probe/)"),
    ],
}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(rel(PUBLISHED_ROOT)),
                    help="results tree the re-run arms are read from (default: the published tree)")
    ap.add_argument("--published-root", default=str(rel(PUBLISHED_ROOT)),
                    help="results tree the arms that are NOT retrained are read from")
    ap.add_argument("--seeds", nargs="+", default=None,
                    help="default, and the only accepted value: the seed_* directories under "
                         "--root.  Given explicitly it is an assertion about the tree, and a "
                         "disagreement is an error -- the captions' seed counts are checked "
                         "against this set, so a subset would certify them against a tree that "
                         "holds more")
    ap.add_argument("--published-seeds", nargs="+", default=None,
                    help="same rule, for --published-root")
    ap.add_argument("--ranking-json", default=None,
                    help="rank_final.json (default: <published-root>/ranking/rank_final.json)")
    ap.add_argument("--paper", default="paper", help="the paper source directory")
    ap.add_argument("--rerun-landed", choices=("auto", "yes", "no"), default="auto",
                    help="whether the caption rule's re-run statement is required")
    ap.add_argument("--json", default=None, help="write the findings as JSON here")
    ap.add_argument("--verbose", action="store_true", help="also print the OK findings")
    ap.add_argument("--dump-unclaimed", action="store_true",
                    help="authoring aid: print the unbound numerals of every enrolled row")
    args = ap.parse_args(argv)

    ctx = build_context(args)
    if args.dump_unclaimed:
        print(dump_unclaimed(ctx))
        return 0
    findings = run_checks(ctx)
    print(report(findings, verbose=args.verbose))
    if args.json:
        Path(args.json).write_text(json.dumps(
            [f.__dict__ | {"fatal": f.fatal} for f in findings], indent=2))
    fatal = [f for f in findings if f.fatal]
    declared = sum(len(r.declared) for rows in LEDGER_DECLARED_ROWS.values() for r in rows)
    print(f"root       {rel(ctx.root.root)}  seeds {list(ctx.seeds)}  "
          f"lock n={ctx.root.n_lock}")
    print(f"published  {rel(ctx.published.root)}  seeds {list(ctx.published.seeds)}")
    print(f"ranking    {ctx.ranking['path']}")
    print(f"coverage   {sum(1 for f in findings if f.severity == 'OK')} assertions verified "
          f"against artifacts; {declared} further numerals are registered to other run families "
          "and are change-detected only, NOT value-verified")
    print("RESULT: " + ("FAIL" if fatal else "pass")
          + f" ({len(fatal)} fatal finding{'s' if len(fatal) != 1 else ''})")
    return 1 if fatal else 0


if __name__ == "__main__":
    raise SystemExit(main())
