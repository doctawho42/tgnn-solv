#!/usr/bin/env python
"""No scored row puts one molecule in both roles, which is what bounds the substitution's
role-dependence change at zero.

WHY THIS IS A GATE AND NOT A REMARK.  Sec. 2.4 used to say the substitution changes two things at
once -- the profile values and the role-dependence -- and leaves them unseparated.  It separates
them, and the separation is a row count rather than an argument, so it can go stale the moment a
split is regenerated.  The data-preparation rule of this project says the seeded solute_scaffold
split is NOT stable across pipeline versions; a regeneration that introduced one self-pair would
silently falsify a claim in Computational methods.

THE MECHANISM THE COUNT STANDS ON.  CosmoSacLayer._residual_ln_gamma2 builds the solute's
pure-component reference as p2_pure = p2 / A2 -- from the SOLUTE-ROLE profile -- and at infinite
dilution the mixture profile is p1 / A1, the solvent-role one.  On a pair of distinct molecules
each is therefore read in exactly one role and no role discrepancy can enter the bracket.  Only a
self-pair puts one molecule in both positions, and there the two roles' profiles disagree, which is
the identity violation Sec. S1 prices.

WHAT IS CHECKED: every set any reported number is scored on, matched on canonical SMILES.

Usage
-----
    python scripts/analysis/check_no_scored_self_pairs.py
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[2]
#: (path, solute column, solvent column, label, row filter) for every scored set.
SETS = [
    ("notebooks/data/processed/test.csv", "solute_smiles", "solvent_smiles",
     "test split, all rows", None),
    ("notebooks/data/processed/test.csv", "solute_smiles", "solvent_smiles",
     "test split, labelled rows", "labelled"),
    ("notebooks/data/processed/val.csv", "solute_smiles", "solvent_smiles",
     "validation split", None),
    ("paper/si_tables/broad_idac_set_477.csv", "solute_smiles", "solvent_smiles",
     "broad IDAC set", None),
]
#: The VT-2005-matched deposit carries keys and names rather than SMILES.
KEYED = ("paper/si_tables/vt2005_matched_set_60.csv", "solute_key", "solvent_key",
         "VT-2005-matched set")


def canoniser():
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
    cache: dict = {}

    def can(s):
        if s not in cache:
            m = Chem.MolFromSmiles(s) if isinstance(s, str) else None
            cache[s] = Chem.MolToSmiles(m) if m is not None else None
        return cache[s]
    return can


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    can = canoniser()
    bad = 0

    print("self-pairs on every set a reported number is scored on:")
    for rel, su, sv, label, filt in SETS:
        rows = list(csv.DictReader((ROOT / rel).open()))
        if filt == "labelled":
            rows = [r for r in rows if str(r.get("has_solubility", "")).lower() in ("true", "1")]
        unparsed = [r for r in rows if not can(r[su]) or not can(r[sv])]
        hits = [r for r in rows if can(r[su]) and can(r[su]) == can(r[sv])]
        # AN UNPARSEABLE ROW IS A FAILURE, NOT A PASS.  A molecule RDKit cannot read is a molecule
        # this check cannot clear, and reporting zero over rows it could not compare would be the
        # gate failing open.
        ok = not hits and not unparsed
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {label:<28} rows {len(rows):>6}   "
              f"self-pairs {len(hits)}   unparseable {len(unparsed)}")

    rel, su, sv, label = KEYED
    rows = list(csv.DictReader((ROOT / rel).open()))
    hits = [r for r in rows if r[su].strip() == r[sv].strip()]
    bad += bool(hits)
    print(f"  {'ok  ' if not hits else 'FAIL'}  {label:<28} rows {len(rows):>6}   "
          f"self-pairs {len(hits)}   (matched on deposited key, no SMILES column)")

    if bad:
        raise SystemExit(f"\n{bad} set(s) contain a scored self-pair, or a row this check could "
                         f"not compare. Sec. 2.4 bounds the substitution's role-dependence change "
                         f"at zero on the strength of there being none.")
    print("\nNo scored row puts one molecule in both roles, so the substitution changes the "
          "profile values alone on every row reported.")


if __name__ == "__main__":
    main()
