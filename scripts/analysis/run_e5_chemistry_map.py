#!/usr/bin/env python3
"""Regenerate the chemistry-resolved maps of the asymptotic physics penalty.

This is the generator behind SI Sec. "Chemistry-resolved structure of the asymptotic
physics penalty" (`paper/sections/chemistry-map.tex`) and its two tables
(`tab:solvent-map`, `tab:solute-map`).  Before this script existed, all seventeen printed
values occurred nowhere in the repository except that .tex file: no CSV, no JSON, no
command.  `scripts/analysis/make_map_table_tex.py` is a different object -- the b_insuff
activity-axis map on the IDAC sets.

WHAT IS COMPUTED
----------------
For each seed s and each stratum S of the locked test rows,

    dMAE_s(S) = MAE(physics arm, S) - MAE(control arm, S)

and the table cell is `mean_s dMAE_s(S) +/- sd_s dMAE_s(S)`.  Positive means the closure
adds cost.  The default arms are the two the section names: control = `directgnn`,
physics = `grounded_a` (the grounded learned-sigma COSMO-SAC closure).

WHEN THE TWO SIDES HAVE DIFFERENT SEED COUNTS.  The leak-free re-run trains the physics arm at
five seeds and does not retrain the control at all; SI row 14's disposition is "regenerated on
the physics side only, the control side stays published".  There is then no seed-by-seed
pairing to make, and the way that was first written down -- `--control-seeds 42 43 44 42 43`,
padding three control seeds out to five by repeating two of them -- is not a pairing either: it
counts seeds 42 and 43 twice, which re-weights the control's own mean and moves the published
DirectGNN cell from `1.70 +/- 0.03` to `1.71 +/- 0.04` although DirectGNN is not retrained.  A
repeated seed is refused.  Unequal lists are handled by POOLING the control instead: the
control's stratum MAE is averaged over its own seeds and each physics seed is differenced
against that one number, so the spread in every cell is the physics side's alone -- which is
what the two captions are required to say -- and the control's printed mean and sd are over its
own seeds and cannot move.  `control_pairing` in the JSON records which rule was used.

TWO SPREAD CONVENTIONS ARE IN PLAY IN THE PUBLISHED TEXT, AND THEY DIFFER.
The section's two *arm means* (`1.70 +/- 0.03`, `1.85 +/- 0.05`) are population sd
(ddof=0), matching `results/e5_sigma_grounding/THREE_SEED_SUMMARY.md`.  Every *table cell*
is sample sd (ddof=1).  Both are emitted for every quantity; `sd` in the check is ddof=1
for cells and ddof=0 for the arm means, which is what reproduces the print.

ROW LOCK
--------
Rows supervised (`has_solubility`) and finite-predicted in every arm listed by
`--lock-arms` (default: the two compared arms).  On the published tree the `fin` half is
inert and the lock is 5608 rows for the two-arm and the six-arm intersection alike -- that
is checked, not assumed; see `scripts/analysis/run_e5_comparison.py::_supervised_finite`.

CLASS DEFINITIONS
-----------------
* Solvent class: `tgnn_solv.data.solvent_types.solvent_type_from_smiles` -- the nine
  printed classes are exactly `SOLVENT_TYPE_NAMES` minus `other`.  NOTE that `other` holds
  1240 of the 5608 locked rows (22.1%), so Table S21 does not partition the test set.
* Solute class: `_coarse_solute_class` imported live from
  `scripts/evaluation/run_prediction_error_slices.py`, so this script cannot drift from it.
  The four printed classes are four of its labels.
* Novelty stratum: maximum Morgan(r=2, 2048-bit) Tanimoto of the test solute against the
  set of unique train solutes in `--train-csv`; strata `<= 0.3` and `> 0.8`.
* Charged / salt: `multifrag_neutral` -- a solute deposited as a MULTI-FRAGMENT SMILES with no
  formal charge on any atom.  It reproduces the printed `-0.04 +/- 0.19` and is the default.
  This row was written off on 2026-08-10 as unrecoverable in principle, on the argument that the
  mask "excludes every solute carrying a formal charge, so it cannot be what a row named Charged /
  salt means".  THAT ARGUMENT IS WRONG, and the correction is in `salt_flags`: in this corpus a
  formal charge is mostly a nitro group on a neutral molecule, and the thirteen solutes the mask
  selects are drug hydrochlorides, tosylates, a phosphate, a malate and hydrates -- salts written
  un-ionised, which is what the row names.  Every candidate is still scored into
  `salt_candidate/*` whatever `--salt-def` says, and `--salt-def all` assigns none.

USAGE
-----
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_e5_chemistry_map.py \
        --root results/e5_sigma_grounding --check

    # the same command discharges the leak-free tree when its per-row CSVs land; --seeds is
    # discovered from the tree, and the control keeps its own three:
    ... --root results/e5_sigma_grounding_leakfree \
        --control-root results/e5_sigma_grounding --control-seeds 42 43 44
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _SCRIPTS_ROOT.parent
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import _bootstrap  # noqa: E402,F401

from rdkit import Chem, DataStructs, RDLogger  # noqa: E402
from rdkit.Chem import AllChem  # noqa: E402

from tgnn_solv.data.solvent_types import (  # noqa: E402
    SOLVENT_TYPE_NAMES,
    solvent_type_from_smiles,
)

RDLogger.DisableLog("rdApp.*")

_KEY = ["solute_smiles", "solvent_smiles", "T"]

#: Nine of the ten `SOLVENT_TYPE_NAMES`; `other` is not printed by Table S21.
PRINTED_SOLVENT_CLASSES = [n for n in SOLVENT_TYPE_NAMES if n != "other"]

#: The four `_coarse_solute_class` labels Table S22 prints.
PRINTED_SOLUTE_CLASSES = [
    "oxygenated",
    "polyaromatic",
    "heterocycle",
    "halogenated_aromatic",
]

#: Candidate readings of Table S22's "Charged / salt" row.  `explicit_salt` is the
#: repository's own predicate (`ionic_features._charge_summary`, `is_explicit_salt`);
#: `multifrag_neutral` is the only one that reproduces the printed `-0.04 +/- 0.19`, and it is
#: the row's definition (`DEFAULT_SALT_DEF`).
#:
#: WHY THE "IT EXCLUDES EVERY CHARGED SOLUTE" OBJECTION DOES NOT HOLD.  On the 5608 locked rows
#: `any_charge` selects 31 solutes / 735 rows, but 18 of those solutes (355 rows) have every
#: fragment net-neutral: the formal charges are the internal separation RDKit writes for a nitro
#: group, so they are neutral nitroaromatics and nitramines, not ions.  The 13 that do carry a
#: net-charged fragment (380 rows) are exactly `explicit_salt`, i.e. salts written WITH their
#: charges.  So `multifrag_neutral` does not exclude "every charged solute"; it excludes the
#: nitro compounds and the explicitly-ionised salts, and selects the salts written WITHOUT
#: charges -- 13 solutes, 416 rows: nine acid-addition salts (hydrochlorides, two tosylate
#: forms, a phosphate, a malate) and four hydrates.  That is a stated, reproducible definition,
#: and the cell is regenerable.  What it is NOT is the union of both spellings of a salt: the
#: 380 explicitly-ionised rows are outside the printed row, and `salt_candidate/multifrag`
#: (the union, `+0.07 +/- 0.34`) is deposited beside it so the exclusion is on the record.
SALT_DEFS = (
    "any_charge",
    "multifrag",
    "explicit_salt",
    "multifrag_neutral",
    "charged_or_salt",
)

#: The reading Table S22's row is assigned, and the default of `--salt-def`.
DEFAULT_SALT_DEF = "multifrag_neutral"

#: What `paper/sections/chemistry-map.tex` prints today, for `--check`.
#: `(mean, sd, approx)`; `approx=True` marks the one cell printed as `\approx0` rather than
#: a two-decimal value, which is satisfied by anything rounding to |x| <= 0.05.
PUBLISHED: dict[str, tuple[float, float | None, bool]] = {
    "arm/control_mae": (1.70, 0.03, False),
    "arm/physics_mae": (1.85, 0.05, False),
    "global/delta_mae": (0.14, None, False),
    "solvent/water": (0.52, 0.35, False),
    "solvent/carboxylic_acid": (0.39, 0.16, False),
    "solvent/sulfoxide": (0.26, 0.24, False),
    # Repaired 2026-08-10: the table printed +0.21 against a computed +0.2048.  See the note
    # under `check`; the .tex now prints +0.20 and this is the value it is held to.
    "solvent/nitrile": (0.20, 0.19, False),
    "solvent/alcohol": (0.15, 0.14, False),
    "solvent/aromatic": (0.03, 0.63, False),
    "solvent/hydrocarbon": (0.02, 0.50, False),
    "solvent/halogenated": (-0.29, 0.36, False),
    "solvent/amide": (-0.22, 0.11, False),
    "solute/oxygenated": (0.32, None, False),
    "solute/polyaromatic": (0.27, None, False),
    "solute/heterocycle": (0.17, None, False),
    "solute/halogenated_aromatic": (0.0, None, True),
    "solute/charged_salt": (-0.04, 0.19, False),
    "novelty/tanimoto_le_0.3": (-0.04, 0.18, False),
    "novelty/tanimoto_gt_0.8": (0.51, 0.09, False),
}


def _load_error_slices_module():
    """Import `_coarse_solute_class` from its one implementation rather than copying it."""
    path = _SCRIPTS_ROOT / "evaluation" / "run_prediction_error_slices.py"
    spec = importlib.util.spec_from_file_location("_e5_map_error_slices", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _supervised_mask(df: pd.DataFrame) -> np.ndarray:
    col = df["has_solubility"]
    if col.dtype == object:
        sup = col.map(lambda v: str(v).strip().lower() in ("true", "1")).to_numpy(bool)
    else:
        sup = col.fillna(False).astype(bool).to_numpy()
    fin = np.isfinite(df["ln_x2_pred"].to_numpy(dtype=float))
    return sup & fin


def load_arm(root: Path, seed: int, arm: str) -> pd.DataFrame:
    path = root / f"seed_{seed}" / f"{arm}_predictions.csv"
    if not path.is_file():
        raise SystemExit(f"missing per-row predictions: {path}")
    df = pd.read_csv(path, low_memory=False)
    df["T"] = df["T"].round(6)
    return df.drop_duplicates(_KEY, keep="first").reset_index(drop=True)


def locked_keys(frames: dict[tuple[int, str], pd.DataFrame]) -> list[tuple]:
    common: set | None = None
    for df in frames.values():
        elig = df[_supervised_mask(df)]
        keys = set(map(tuple, elig[_KEY].itertuples(index=False, name=None)))
        common = keys if common is None else (common & keys)
    return sorted(common or set())


def abs_errors(df: pd.DataFrame, keys: list[tuple]) -> np.ndarray:
    idx = df.set_index(_KEY)
    sub = idx.loc[keys]
    return np.abs(sub["ln_x2_true"].to_numpy(float) - sub["ln_x2_pred"].to_numpy(float))


def morgan_fp(smiles: str, radius: int, n_bits: int):
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)


def max_train_tanimoto(
    test_solutes: list[str], train_solutes: list[str], radius: int, n_bits: int
) -> dict[str, float]:
    train_fps = [fp for fp in (morgan_fp(s, radius, n_bits) for s in train_solutes) if fp is not None]
    if not train_fps:
        raise SystemExit("no valid train solute fingerprints")
    out: dict[str, float] = {}
    for smi in test_solutes:
        query = morgan_fp(smi, radius, n_bits)
        out[smi] = (
            float(max(DataStructs.BulkTanimotoSimilarity(query, train_fps)))
            if query is not None
            else 0.0
        )
    return out


def salt_flags(smiles: str) -> dict[str, bool]:
    """The five candidate readings, plus the one that separates a nitro group from an ion.

    `any_charge` is a formal-charge predicate, not an ionicity one: RDKit writes a nitro group
    as `[N+](=O)[O-]`, so a neutral nitroaromatic sets it.  `net_charged_fragment` asks the
    question `any_charge` is usually mistaken for -- does some fragment carry a NET charge --
    and it is what shows that excluding `any_charge` does not mean excluding ions.  It is
    reported in the summary, not offered as a row definition.
    """
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return {k: False for k in (*SALT_DEFS, "net_charged_fragment")}
    charges = [a.GetFormalCharge() for a in mol.GetAtoms()]
    frags = Chem.GetMolFrags(mol, asMols=True)
    n_frag = len(frags)
    any_charge = any(c != 0 for c in charges)
    multifrag = n_frag > 1
    return {
        "any_charge": any_charge,
        "multifrag": multifrag,
        "explicit_salt": multifrag and any_charge,
        "multifrag_neutral": multifrag and not any_charge,
        "charged_or_salt": multifrag or any_charge,
        "net_charged_fragment": any(
            sum(a.GetFormalCharge() for a in f.GetAtoms()) != 0 for f in frags),
    }


def cell(per_seed: list[float]) -> dict[str, Any]:
    arr = np.asarray(per_seed, float)
    return {
        "mean": float(arr.mean()),
        "sd": float(arr.std(ddof=1)) if arr.size > 1 else float("nan"),
        "sd_population": float(arr.std()),
        "per_seed": [float(x) for x in arr],
    }


def discover_seeds(root: Path) -> list[int]:
    """The seeds the tree holds.  A default seed list is how a five-seed tree gets read as three."""
    return sorted(int(d.name[5:]) for d in root.glob("seed_*")
                  if d.is_dir() and d.name[5:].isdigit() and any(d.glob("*_predictions.csv")))


def _distinct(seeds: list[int], flag: str) -> list[int]:
    dupes = sorted({s for s in seeds if seeds.count(s) > 1})
    if dupes:
        raise SystemExit(
            f"{flag} repeats {dupes}.  A seed counted twice is not a second measurement: it "
            "re-weights that arm's own mean and its sd.  Padding three control seeds out to five "
            "by repeating two of them moves the published DirectGNN cell from 1.70 +/- 0.03 to "
            "1.71 +/- 0.04 although DirectGNN is not retrained.  Give each seed once; unequal "
            "lists are pooled, not padded."
        )
    return seeds


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    control_root = Path(args.control_root) if args.control_root else root
    seeds = _distinct(list(args.seeds), "--seeds")
    control_seeds = _distinct(list(args.control_seeds) if args.control_seeds else list(seeds),
                              "--control-seeds")
    # Seed-by-seed only when the two sides carry the same seeds; otherwise the control is pooled
    # over its own, so its mean and sd are its published ones and every cell's spread is the
    # physics side's.  See the module docstring.
    paired = control_seeds == seeds
    slices = _load_error_slices_module()

    # (seed, arm) -> frame.  The control arm may come from a different results root and a
    # different seed list: SI row 14's disposition is "regenerated on the physics side only,
    # the control side stays published", so the leak-free tree (which trains no `directgnn`
    # arm) is differenced against the published control.
    frames: dict[tuple[int, str], pd.DataFrame] = {}
    for seed in seeds:
        frames[(seed, args.physics_arm)] = load_arm(root, seed, args.physics_arm)
    for seed in control_seeds:
        frames.setdefault((seed, args.control_arm), load_arm(control_root, seed, args.control_arm))
    for extra in args.lock_arms or []:
        for seed in seeds:
            frames.setdefault((seed, extra), load_arm(root, seed, extra))

    keys = locked_keys(frames)
    if not keys:
        raise SystemExit("empty cross-arm intersection; check --lock-arms and the roots")

    ae_phys = {s: abs_errors(frames[(s, args.physics_arm)], keys) for s in seeds}
    ae_ctrl = {c: abs_errors(frames[(c, args.control_arm)], keys) for c in control_seeds}
    solute = np.array([k[0] for k in keys], dtype=object)
    solvent = np.array([k[1] for k in keys], dtype=object)

    def delta(mask: np.ndarray) -> list[float] | None:
        mask = np.asarray(mask, bool)
        if mask.sum() == 0:
            return None
        if paired:
            return [float(ae_phys[s][mask].mean() - ae_ctrl[c][mask].mean())
                    for s, c in zip(seeds, control_seeds)]
        base = float(np.mean([ae_ctrl[c][mask].mean() for c in control_seeds]))
        return [float(ae_phys[s][mask].mean() - base) for s in seeds]

    out: dict[str, Any] = {
        "root": str(root),
        "control_root": str(control_root),
        "seeds": list(seeds),
        "control_seeds": control_seeds,
        "control_pairing": "seed-by-seed" if paired else "control pooled over its own seeds",
        "control_arm": args.control_arm,
        "physics_arm": args.physics_arm,
        "lock_arms": sorted({a for _, a in frames}),
        "n_locked": len(keys),
        "morgan": {"radius": args.morgan_radius, "n_bits": args.morgan_n_bits},
    }

    # --- the two arm means and the global delta ---------------------------------------
    # Each arm's mean and sd are over ITS OWN seeds, so the control's do not move with the
    # length of the physics list.
    out["arm/control_mae"] = cell([float(ae_ctrl[c].mean()) for c in control_seeds])
    out["arm/physics_mae"] = cell([float(ae_phys[s].mean()) for s in seeds])
    out["global/delta_mae"] = cell(delta(np.ones(len(keys), bool)))

    # --- solvent axis -------------------------------------------------------------------
    uniq_solvents = sorted(set(solvent.tolist()))
    solvent_class = np.array(
        [{s: solvent_type_from_smiles(s) for s in uniq_solvents}[s] for s in solvent], dtype=object
    )
    for name in PRINTED_SOLVENT_CLASSES + ["other"]:
        mask = solvent_class == name
        d = delta(mask)
        if d is None:
            continue
        entry = cell(d)
        entry["n_rows"] = int(mask.sum())
        entry["printed"] = name in PRINTED_SOLVENT_CLASSES
        out[f"solvent/{name}"] = entry

    # --- solute axis --------------------------------------------------------------------
    uniq_solutes = sorted(set(solute.tolist()))
    coarse = {s: slices.describe_solute(s)["coarse_class"] for s in uniq_solutes}
    solute_class = np.array([coarse[s] for s in solute], dtype=object)
    for name in sorted(set(solute_class.tolist())):
        mask = solute_class == name
        d = delta(mask)
        if d is None:
            continue
        entry = cell(d)
        entry["n_rows"] = int(mask.sum())
        entry["printed"] = name in PRINTED_SOLUTE_CLASSES
        out[f"solute/{name}"] = entry

    # --- the charged/salt row ------------------------------------------------------------
    # Every candidate is scored whatever --salt-def says; the flag only decides which one is
    # ASSIGNED to the printed row.  The audit block below is what refutes the "the mask excludes
    # every charged solute" objection this row was once written off under: it separates a formal
    # charge (a nitro group) from a net-charged fragment (an ion).
    flags = {s: salt_flags(s) for s in uniq_solutes}
    for defn in SALT_DEFS:
        mask = np.array([flags[s][defn] for s in solute], dtype=bool)
        d = delta(mask)
        if d is None:
            continue
        entry = cell(d)
        entry["n_rows"] = int(mask.sum())
        out[f"salt_candidate/{defn}"] = entry
    charged = [s for s in uniq_solutes if flags[s]["any_charge"]]
    ionic = [s for s in charged if flags[s]["net_charged_fragment"]]
    nitro = [s for s in charged if not flags[s]["net_charged_fragment"]]
    rows_of = lambda ss: int(sum(int((solute == s).sum()) for s in ss))  # noqa: E731
    out["salt_audit/formal_charge_is_not_ionicity"] = {
        "any_charge_solutes": len(charged), "any_charge_rows": rows_of(charged),
        "every_fragment_net_neutral_solutes": len(nitro),
        "every_fragment_net_neutral_rows": rows_of(nitro),
        "net_charged_fragment_solutes": len(ionic),
        "net_charged_fragment_rows": rows_of(ionic),
        "note": "a formal charge in this corpus is mostly the nitro group's internal "
                "separation on a neutral molecule; only the net-charged-fragment solutes are "
                "ions, and they are exactly the explicit_salt stratum",
    }
    if args.salt_def != "all":
        chosen = out.get(f"salt_candidate/{args.salt_def}")
        if chosen is not None:
            out["solute/charged_salt"] = dict(chosen, definition=args.salt_def)

    # --- novelty axis ---------------------------------------------------------------------
    train = pd.read_csv(args.train_csv, low_memory=False)
    train_solutes = sorted(set(train["solute_smiles"].astype(str)))
    sim = max_train_tanimoto(uniq_solutes, train_solutes, args.morgan_radius, args.morgan_n_bits)
    tani = np.array([sim[s] for s in solute], float)
    out["novelty/n_train_solutes"] = len(train_solutes)
    for label, mask, solute_pred in (
        (f"tanimoto_le_{args.novel_cut:g}", tani <= args.novel_cut,
         lambda s: sim[s] <= args.novel_cut),
        (f"tanimoto_gt_{args.familiar_cut:g}", tani > args.familiar_cut,
         lambda s: sim[s] > args.familiar_cut),
    ):
        d = delta(mask)
        if d is None:
            continue
        entry = cell(d)
        entry["n_rows"] = int(mask.sum())
        entry["n_solutes"] = int(sum(1 for s in uniq_solutes if solute_pred(s)))
        out[f"novelty/{label}"] = entry

    # --- conservation: each taxonomy partitions the locked rows, so the row-weighted
    #     recombination of its classes must return the global delta seed by seed. -------
    out["conservation"] = {
        axis: _recombine(out, axis, len(keys), out["global/delta_mae"]["per_seed"])
        for axis in ("solvent", "solute")
    }
    return out


def _recombine(out: dict[str, Any], axis: str, n_locked: int, global_per_seed: list[float]) -> dict:
    cells = {
        k: v
        for k, v in out.items()
        if k.startswith(f"{axis}/") and isinstance(v, dict) and "n_rows" in v
        and k != "solute/charged_salt"  # an overlapping stratum, not a class of the taxonomy
    }
    n_covered = sum(v["n_rows"] for v in cells.values())
    n_seeds = len(global_per_seed)
    recomposed = [
        sum(v["n_rows"] * v["per_seed"][i] for v in cells.values()) / max(n_covered, 1)
        for i in range(n_seeds)
    ]
    printed = {k: v for k, v in cells.items() if v.get("printed", True)}
    n_printed = sum(v["n_rows"] for v in printed.values())
    printed_recomposed = [
        sum(v["n_rows"] * v["per_seed"][i] for v in printed.values()) / max(n_printed, 1)
        for i in range(n_seeds)
    ]
    return {
        "n_classes": len(cells),
        "n_rows_covered": n_covered,
        "n_locked": n_locked,
        "n_rows_in_printed_classes": n_printed,
        "printed_classes_recomposed_per_seed": printed_recomposed,
        "printed_classes_recomposed_mean": float(np.mean(printed_recomposed)),
        "partitions_locked_rows": n_covered == n_locked,
        "recomposed_per_seed": recomposed,
        "max_abs_deviation_from_global": float(
            max(abs(a - b) for a, b in zip(recomposed, global_per_seed))
        ) if n_covered == n_locked else None,
        "n_rows_in_unprinted_classes": int(
            sum(v["n_rows"] for k, v in cells.items() if not v.get("printed", True))
        ),
    }


#: Which printed row of `chemistry-map.tex` each computed key is held to.  The row is matched by
#: its label in the first tabular column; the value is parsed out of the file at check time, so a
#: number edited in the manuscript and not here is a MISMATCH rather than an invisible drift.
TEX_ROW: dict[str, str] = {
    "solvent/water": "Water", "solvent/carboxylic_acid": "Carboxylic acid",
    "solvent/sulfoxide": "Sulfoxide", "solvent/nitrile": "Nitrile",
    "solvent/alcohol": "Alcohol", "solvent/aromatic": "Aromatic",
    "solvent/hydrocarbon": "Hydrocarbon", "solvent/halogenated": "Halogenated",
    "solvent/amide": "Amide", "solute/oxygenated": "Oxygenated",
    "solute/polyaromatic": "Polyaromatic", "solute/heterocycle": "Heterocycle",
    "solute/halogenated_aromatic": "Halogenated-aromatic",
    "solute/charged_salt": "Charged / salt",
    "novelty/tanimoto_le_0.3": r"Tanimoto $\leq0.3$",
    "novelty/tanimoto_gt_0.8": r"Tanimoto $>0.8$",
}

_CELL = re.compile(r"\$([+-]?[\d.]+)\s*(?:\\pm\s*([\d.]+))?\s*\$")


def parse_tex(path: Path) -> dict[str, tuple[float, float | None, bool]]:
    """Read the printed value of every mapped row out of the manuscript source.

    The frozen table this replaced was a second copy of the page, and a second copy is the
    thing `--check` exists to detect: editing the manuscript and not the constant, or the
    constant and not the manuscript, both passed.
    """
    text = path.read_text(encoding="utf-8")
    found: dict[str, tuple[float, float | None, bool]] = {}
    for key, label in TEX_ROW.items():
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith(label) or "&" not in stripped:
                continue
            cell = stripped.split("&", 1)[1]
            if r"\approx0" in cell:
                found[key] = (0.0, None, True)
            else:
                m = _CELL.search(cell)
                if m is None:
                    continue
                found[key] = (float(m.group(1)),
                              float(m.group(2)) if m.group(2) else None, False)
            break
    missing = [k for k in TEX_ROW if k not in found]
    if missing:
        raise SystemExit(f"check: these rows were not found in {path}: {missing}")
    return found


def check(out: dict[str, Any], tex: Path | None = None) -> list[str]:
    """Compare against what the .tex prints today, at the decimal it prints."""
    tex = tex or (_REPO_ROOT / "paper" / "sections" / "chemistry-map.tex")
    published = dict(PUBLISHED)
    published.update(parse_tex(tex))
    lines = ["", f"CHECK against {tex} (printed decimal, parsed at check time)", "-" * 78]
    failures = []
    for key, (want_mean, want_sd, approx) in published.items():
        got = out.get(key)
        if got is None:
            lines.append(f"{key:34s}  printed {want_mean:+.2f}  -- NOT COMPUTED (see notes)")
            failures.append(key)
            continue
        # arm means are printed with population sd; every table cell with sample sd.
        sd_got = got["sd_population"] if key.startswith("arm/") else got["sd"]
        ok_mean = abs(got["mean"]) <= 0.05 if approx else round(got["mean"], 2) == round(want_mean, 2)
        ok_sd = want_sd is None or round(sd_got, 2) == round(want_sd, 2)
        status = "OK" if (ok_mean and ok_sd) else "MISMATCH"
        if status == "MISMATCH":
            failures.append(key)
        sd_txt = f" +/- {sd_got:.4f}" if want_sd is not None else ""
        want_txt = f" +/- {want_sd:.2f}" if want_sd is not None else ""
        printed_txt = "~0" if approx else f"{want_mean:+.2f}"
        lines.append(
            f"{key:34s}  printed {printed_txt:>5s}{want_txt:11s}  computed {got['mean']:+.4f}{sd_txt:14s}  {status}"
        )
    lines.append("-" * 78)
    lines.append(f"{len(PUBLISHED) - len(failures)} of {len(PUBLISHED)} reproduce; failures: {failures or 'none'}")
    salt = out.get("solute/charged_salt")
    audit = out.get("salt_audit/formal_charge_is_not_ionicity")
    if salt and audit:
        lines.append("")
        lines.append(
            f"  solute/charged_salt is assigned by --salt-def={salt.get('definition')}: a solute "
            f"deposited as a multi-fragment SMILES with no formal charge, {salt['n_rows']} rows. "
            "This row was once written off as unrecoverable in principle, on the argument that "
            "that mask excludes every charged solute. It does not: of the "
            f"{audit['any_charge_solutes']} formally-charged solutes here "
            f"({audit['any_charge_rows']} rows), {audit['every_fragment_net_neutral_solutes']} "
            f"({audit['every_fragment_net_neutral_rows']} rows) have every fragment net-neutral -- "
            "nitro compounds, not ions. The mask excludes those and the "
            f"{audit['net_charged_fragment_rows']} rows of explicitly-ionised salt "
            "(salt_candidate/explicit_salt), and selects the salts written un-ionised. The "
            "exclusion of the explicit spelling is real and is why salt_candidate/multifrag, the "
            "union of both spellings, is deposited beside it."
        )
    if failures:
        lines.append("")
        lines.append("NOTES ON THE FAILURES")
        if "solvent/nitrile" in failures:
            nit = out.get("solvent/nitrile", {})
            lines.append(
                "  solvent/nitrile: the stratum is acetonitrile alone (n=252) and its 3-seed mean is "
                f"{nit.get('mean', float('nan')):+.4f}. Until 2026-08-10 the table printed +0.21 "
                "against a computed +0.2048, i.e. a last-digit slip that missed the 0.205 rounding "
                "boundary by 2e-4; the sd (0.19) was right throughout. (Averaging the per-seed values "
                "*after* rounding each to 2 dp does give +0.21, but that rule then breaks water "
                "(+0.51 vs +0.52) and amide (-0.21 vs -0.22), so it was not the table's rule.) The "
                "table now prints +0.20; a failure HERE means the cell has drifted again."
            )
        if "solute/charged_salt" in failures:
            lines.append(
                "  solute/charged_salt: the printed -0.04 +/- 0.19 is reproduced by `multifrag_neutral` "
                "and by no other candidate (any-charge +0.22, multi-fragment +0.07, explicit-salt "
                "+0.18, union +0.13). A failure here means either the tree moved the cell or "
                "--salt-def was pointed at a different candidate; it is NOT the old 'no definition "
                "reproduces this' finding, which was withdrawn 2026-08-10."
            )
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(_REPO_ROOT / "results/e5_sigma_grounding"),
                    help="results root holding seed_<N>/<arm>_predictions.csv")
    ap.add_argument("--seeds", type=int, nargs="+", default=None,
                    help="default: every seed_* directory under --root that holds per-row "
                         "predictions (a hard-coded default is how a five-seed tree gets read "
                         "as three)")
    ap.add_argument("--control-root", default=None,
                    help="root for the control arm when it is not regenerated (default: --root)")
    ap.add_argument("--control-seeds", type=int, nargs="+", default=None,
                    help="the control arm's OWN seeds (default: --seeds).  Need not match "
                         "--seeds in length: an unequal list pools the control over its own "
                         "seeds.  A repeated seed is an error, not padding")
    ap.add_argument("--control-arm", default="directgnn")
    ap.add_argument("--physics-arm", default="grounded_a")
    ap.add_argument("--lock-arms", nargs="+", default=None,
                    help="extra arms under --root whose supervised+finite rows also enter the lock "
                         "(the two compared arms always do)")
    ap.add_argument("--train-csv", default=str(_REPO_ROOT / "notebooks/data/processed/train.csv"))
    ap.add_argument("--morgan-radius", type=int, default=2)
    ap.add_argument("--morgan-n-bits", type=int, default=2048)
    ap.add_argument("--novel-cut", type=float, default=0.3)
    ap.add_argument("--familiar-cut", type=float, default=0.8)
    ap.add_argument("--salt-def", default=DEFAULT_SALT_DEF, choices=("all",) + SALT_DEFS,
                    help="which candidate is assigned to Table S22's 'Charged / salt' row "
                         f"(default: {DEFAULT_SALT_DEF}, the one that reproduces it).  Every "
                         "candidate is scored into salt_candidate/* regardless; 'all' assigns "
                         "none, which is what this row was reported as before 2026-08-10")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--check", action="store_true", help="print the comparison against the .tex")
    args = ap.parse_args()
    if not args.seeds:
        args.seeds = discover_seeds(Path(args.root))
        if not args.seeds:
            raise SystemExit(f"no seed_*/ directory with per-row predictions under {args.root}")

    out = build(args)
    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"root={out['root']}  seeds={out['seeds']}  n_locked={out['n_locked']}")
    print(f"arms: physics={out['physics_arm']} minus control={out['control_arm']} "
          f"(control seeds {out['control_seeds']} from {out['control_root']}; "
          f"{out['control_pairing']})")
    for key in sorted(k for k in out if isinstance(out[k], dict) and "mean" in out[k]):
        e = out[key]
        n = f" n={e['n_rows']:5d}" if "n_rows" in e else ""
        print(f"  {key:34s}{n}  {e['mean']:+.4f} +/- {e['sd']:.4f} (sd1) / {e['sd_population']:.4f} (sd0)"
              f"  per-seed={[round(x, 4) for x in e['per_seed']]}")
    for axis, c in out["conservation"].items():
        head = f"  conservation/{axis:9s} {c['n_classes']} classes cover {c['n_rows_covered']}/{c['n_locked']} rows"
        if c["partitions_locked_rows"]:
            head += f"; recombination deviates from the global delta by {c['max_abs_deviation_from_global']:.2e}"
        else:
            head += " -- DOES NOT PARTITION"
        print(head)
        print(f"      rows in classes the table does not print: {c['n_rows_in_unprinted_classes']}; "
              f"the printed classes alone ({c['n_rows_in_printed_classes']} rows) recombine to "
              f"{c['printed_classes_recomposed_mean']:+.4f}")
    if args.check:
        report = check(out)
        print("\n".join(report))
        # A check that cannot fail is not a check.  The verdict line names the failures; the
        # exit status has to carry it, or a caller in a pipeline reads success from a mismatch.
        if any("MISMATCH" in line or "NOT COMPUTED" in line for line in report):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
