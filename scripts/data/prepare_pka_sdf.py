"""Prepare the OPERA pKa SDF for the pKa/Hammett rigs (adds pKa_a / pKa_b fields).

Source (open access, public domain -- NIEHS/EPA): Mansouri et al., "Open-source QSAR models
for pKa prediction using multiple machine learning approaches", J. Cheminform. 11:60 (2019),
DOI 10.1186/s13321-019-0384-1. Additional file 1 ("Original and curated pKa data used for
modeling"):
  https://static-content.springer.com/esm/art%3A10.1186%2Fs13321-019-0384-1/MediaObjects/13321_2019_384_MOESM1_ESM.zip
The zip's `pka_QR.sdf` (QSAR-ready, 7904 records) stores a single `pKa` field plus a
`basicOrAcidic` discriminator ("acidic"/"basic"), whereas the rigs
(run_pka_real_decomposition.py, run_pka_trained_comparison.py) read separate `pKa_a` (acid) and
`pKa_b` (base) fields. This reconstructs that split, keeping every other field
(Original_SMILES / Canonical_QSARr etc.) intact.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/data/prepare_pka_sdf.py \
        --in <path>/pka_QR.sdf --out notebooks/data/raw/pKa_QR.sdf
"""
from __future__ import annotations

import argparse
from pathlib import Path

from rdkit import Chem


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", type=Path, required=True, help="OPERA pka_QR.sdf")
    ap.add_argument("--out", type=Path, default=Path("notebooks/data/raw/pKa_QR.sdf"))
    args = ap.parse_args()

    supp = Chem.SDMolSupplier(str(args.inp))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    w = Chem.SDWriter(str(args.out))
    n_in = n_out = n_a = n_b = n_skip = 0
    for mol in supp:
        n_in += 1
        if mol is None:
            n_skip += 1
            continue
        props = mol.GetPropsAsDict()
        pka = props.get("pKa")
        kind = str(props.get("basicOrAcidic", "")).strip().lower()
        if pka is None or kind not in ("acidic", "basic"):
            n_skip += 1
            continue
        if kind == "acidic":
            mol.SetProp("pKa_a", str(pka))
            n_a += 1
        else:
            mol.SetProp("pKa_b", str(pka))
            n_b += 1
        w.write(mol)
        n_out += 1
    w.close()
    print(f"read {n_in} records -> wrote {n_out}  (pKa_a={n_a}, pKa_b={n_b}, skipped={n_skip})")
    print(f"  {args.out}")


if __name__ == "__main__":
    main()
