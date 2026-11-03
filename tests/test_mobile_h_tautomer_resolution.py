"""A mobile-hydrogen InChI must not leave a SMILES on a minor tautomer.

A standard InChI whose ``/h`` layer carries a mobile-hydrogen group does not fix the tautomer, and
``Chem.MolFromInchi`` resolves it to a form that is not the dominant one: formamide arrived as the
imidic acid, caprolactam as the lactim. Since every table downstream keys on canonical SMILES, such
a record silently fails to match a reference profile deposited under the amide form. That cost 27
infinite-dilution records and made the two matching rules of the Supporting Information differ by
25 pairs where they should have agreed.

These tests pin both halves of the repair: the reader resolves the ambiguous case and leaves the
determined one alone, and no table on disk still disagrees with its own InChI.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from rdkit import Chem

from tgnn_solv.data.thermoml_idac import _MOBILE_H, _mol_from_inchi

ROOT = Path(__file__).resolve().parents[1]

#: The three molecules this corpus actually lost, with the form the InChI means.
KNOWN = [
    ("InChI=1S/CH3NO/c2-1-3/h1H,(H2,2,3)", "NC=O", "formamide"),
    ("InChI=1S/C2H5NO/c1-3-2-4/h2H,1H3,(H,3,4)", "CNC=O", "N-methylformamide"),
    # read out of notebooks/data/raw/idac.csv, where the record names it 1-aza-2-cycloheptanone
    ("InChI=1S/C6H11NO/c8-6-4-2-1-3-5-7-6/h1-5H2,(H,7,8)", "O=C1CCCCCN1", "caprolactam"),
]


@pytest.mark.parametrize("inchi,expected,name", KNOWN)
def test_mobile_hydrogen_resolves_to_the_dominant_tautomer(inchi, expected, name):
    assert _MOBILE_H.search(inchi), f"{name}: this InChI has no mobile-hydrogen layer to resolve"
    mol = _mol_from_inchi(inchi)
    assert mol is not None, f"{name}: the InChI did not parse"
    assert Chem.MolToSmiles(mol, canonical=True) == expected


@pytest.mark.parametrize("inchi", [
    "InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H",                 # benzene
    "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",                  # ethanol
    "InChI=1S/C3H6O/c1-3(2)4/h1-2H3",                     # acetone
])
def test_a_determined_inchi_is_left_exactly_as_rdkit_parses_it(inchi):
    """Where the /h layer fixes the hydrogens the structure is settled.

    Canonicalising those too would rewrite molecules the repair has no licence to touch, so the
    reader must be a no-op on them.
    """
    assert not _MOBILE_H.search(inchi)
    plain = Chem.MolToSmiles(Chem.MolFromInchi(inchi), canonical=True)
    assert Chem.MolToSmiles(_mol_from_inchi(inchi), canonical=True) == plain


@pytest.mark.parametrize("rel", [
    "notebooks/data/raw/idac.csv",
    "notebooks/data/raw/idac_expanded.csv",
    "notebooks/data/raw/idac_expanded_raw.csv",
])
def test_no_cached_table_disagrees_with_its_own_inchi(rel):
    """The invariant, stated over the data rather than over the three known molecules.

    Any future re-extraction that reintroduces a minor tautomer fails here, whichever molecule it
    happens to be, because the row's own InChI is the reference.
    """
    path = ROOT / rel
    if not path.exists():
        pytest.skip(f"{rel} is not in this checkout")
    d = pd.read_csv(path, low_memory=False)
    disagreements = []
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
            want = Chem.MolToSmiles(mol, canonical=True)
            if want != smiles:
                disagreements.append(f"{side}: {smiles!r} should be {want!r} per {inchi}")
    assert not disagreements, (
        f"{len(disagreements)} SMILES disagree with their own InChI in {rel}; run "
        f"scripts/data/repair_mobile_h_tautomer_smiles.py --apply\n  "
        + "\n  ".join(disagreements[:6])
    )
