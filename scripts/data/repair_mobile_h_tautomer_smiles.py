#!/usr/bin/env python3
"""Repair SMILES that a mobile-hydrogen InChI left on a minor tautomer.

THE DEFECT. A standard InChI whose ``/h`` layer carries a mobile-hydrogen group, such as
``(H2,2,3)``, declares the hydrogens shared between the listed atoms and so does NOT fix the
tautomer. ``Chem.MolFromInchi`` must still return one structure, and the form it picks is not the
chemically dominant one: formamide arrives as the imidic acid ``N=CO`` instead of ``NC=O``,
N-methylformamide as ``CN=CO``, and caprolactam as the lactim ``OC1=NCCCCC1``. Every table
downstream keys on canonical SMILES, so a record carrying the minor form silently fails to match a
reference profile deposited under the amide form. On this corpus that lost 27 infinite-dilution
records for formamide and N-methylformamide against molecules that ARE in VT-2005, and it is not
the tautomer ambiguity the article declines to cross: the records' own InChI identifies the amide,
so nothing is being carried across a variant -- a correctly identified substance was dropped
because of our own conversion. ``tgnn_solv.data.thermoml_idac._mol_from_inchi`` now resolves the
mobile-hydrogen case, which fixes every future extraction; this script repairs the tables already
on disk.

WHAT IS REPAIRED, AND WHAT IS DELIBERATELY NOT. The cached IDAC sources and the processed split.
Not ``results/``: those are deposited artifacts of runs that happened, and rewriting a molecule
inside one would falsify the record rather than correct it. (A substring search suggests
``results/`` is full of these strings; cell-exact matching finds none, because ``N=CO`` also occurs
inside longer SMILES.)

THE THREE GUARDS, all checked before anything is written, because editing a distributed split in
place is exactly the operation this project has been burned by:
  1. **No labelled row may be touched.** Every affected row must carry ``has_solubility`` false, so
     no reported solubility metric can move. If one is labelled the script refuses.
  2. **The scaffold invariant must survive.** Repairing a SOLUTE changes its Bemis--Murcko
     scaffold, and the split guarantees that no scaffold appears in two partitions. The repaired
     scaffold must therefore not already live in a partition other than the row's own.
  3. **The mapping is computed, not typed.** Each replacement is derived by re-parsing that
     record's own InChI through the repaired reader, so the script cannot encode a wrong guess
     about what a SMILES was meant to be.

The deposited checkpoints were fit before this repair, on 27 auxiliary rows carrying the minor
tautomer. No labelled row and therefore no reported number is affected, and the split is not
re-partitioned, so the arms stay comparable with their own data.

Usage:
    python scripts/data/repair_mobile_h_tautomer_smiles.py            # dry run, reports only
    python scripts/data/repair_mobile_h_tautomer_smiles.py --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from rdkit import Chem, RDLogger                                      # noqa: E402
from rdkit.Chem.Scaffolds import MurckoScaffold                       # noqa: E402

from tgnn_solv.data.thermoml_idac import _MOBILE_H, _mol_from_inchi   # noqa: E402

RDLogger.DisableLog("rdApp.*")

#: The cached sources, which feed every future build, and the split itself.
RAW = sorted((ROOT / "notebooks/data/raw").glob("idac*.csv"))
PROCESSED = sorted((ROOT / "notebooks/data/processed").glob("*.csv"))
SMILES_COLS = ("solute_smiles", "solvent_smiles")


def mapping_from_inchi() -> dict[str, str]:
    """Derive minor-form -> canonical-tautomer from the InChI columns of the cached sources."""
    out: dict[str, str] = {}
    for path in RAW:
        d = pd.read_csv(path, low_memory=False)
        for side in ("solute", "solvent"):
            ic, sc = f"{side}_inchi", f"{side}_smiles"
            if ic not in d or sc not in d:
                continue
            pairs = d[[ic, sc]].dropna().astype(str).drop_duplicates()
            for inchi, smiles in pairs.itertuples(index=False):
                if not _MOBILE_H.search(inchi):
                    continue
                mol = _mol_from_inchi(inchi)
                if mol is None:
                    continue
                fixed = Chem.MolToSmiles(mol, canonical=True)
                if fixed != smiles:
                    out[smiles] = fixed
    return out


def scaffold(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(mol))


def partition_scaffolds() -> dict[str, set[str]]:
    out = {}
    for name in ("train", "val", "test"):
        d = pd.read_csv(ROOT / f"notebooks/data/processed/{name}.csv", low_memory=False)
        out[name] = {s for s in d["solute_smiles"].dropna().astype(str).map(scaffold) if s}
    return out


def check_guards(fix: dict[str, str]) -> list[str]:
    """Guards 1 and 2. Returns the reasons to refuse, empty when the repair is safe."""
    problems: list[str] = []
    for name in ("train", "val", "test"):
        path = ROOT / f"notebooks/data/processed/{name}.csv"
        d = pd.read_csv(path, low_memory=False)
        hit = pd.Series(False, index=d.index)
        for col in SMILES_COLS:
            if col in d:
                hit |= d[col].astype(str).isin(fix)
        if "has_solubility" in d:
            labelled = int(d.loc[hit, "has_solubility"].astype(bool).sum())
            print(f"  {name}.csv: {int(hit.sum())} affected rows, labelled {labelled}")
            if labelled:
                problems.append(f"{name}.csv has {labelled} LABELLED affected rows; a reported "
                                "metric would move and the repair is not a representation change")
        if "solute_smiles" in d:
            moved = d.loc[d["solute_smiles"].astype(str).isin(fix), "solute_smiles"].astype(str)
            for smiles in sorted(set(moved)):
                new = scaffold(fix[smiles])
                elsewhere = [p for p, s in partition_scaffolds().items() if p != name and new in s]
                print(f"  {name}.csv solute {smiles} -> {fix[smiles]}: scaffold {new!r}, "
                      f"also in {elsewhere or 'no other partition'}")
                if elsewhere:
                    problems.append(f"repairing {smiles} in {name} gives scaffold {new!r}, which "
                                    f"already lives in {elsewhere}; the split guarantees no "
                                    "scaffold spans partitions")
    return problems


def repair(paths: list[Path], fix: dict[str, str], apply: bool) -> int:
    changed_cells = 0
    for path in paths:
        d = pd.read_csv(path, low_memory=False)
        per_file = 0
        for col in SMILES_COLS:
            if col not in d:
                continue
            m = d[col].astype(str).isin(fix)
            if m.any():
                per_file += int(m.sum())
                d.loc[m, col] = d.loc[m, col].astype(str).map(fix)
        if per_file:
            changed_cells += per_file
            print(f"  {'wrote' if apply else 'would write'} {per_file:>3} cells  "
                  f"{path.relative_to(ROOT)}")
            if apply:
                d.to_csv(path, index=False)
    return changed_cells


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the files; otherwise report only")
    a = ap.parse_args()

    fix = mapping_from_inchi()
    print(f"mapping derived from the InChI columns, {len(fix)} molecules:")
    for k, v in sorted(fix.items()):
        print(f"  {k:<28} -> {v}")
    if not fix:
        print("nothing to repair")
        return 0

    print("\nguards:")
    problems = check_guards(fix)
    if problems:
        print(f"\nREFUSING, {len(problems)} guard(s) failed:")
        for p in problems:
            print(f"  {p}")
        return 1
    print("  both guards pass")

    print("\ncached sources:")
    n_raw = repair(RAW, fix, a.apply)
    print("processed split:")
    n_proc = repair(PROCESSED, fix, a.apply)
    print(f"\n{n_raw + n_proc} cells in {len(RAW)} cached sources and the split"
          f"{'' if a.apply else ' (dry run; pass --apply)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
