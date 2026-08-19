#!/usr/bin/env python
"""Does the regime-bridge set exist in any data this project holds?  It does not.

WHAT THE BRIDGE WOULD BE
-------------------------
The paradox is measured on solubility at finite composition; the mechanism -- B_closure against
B_insuff -- on infinite-dilution activity coefficients.  Limitation (i) calls the transfer between
them "a conjecture and the principal open question here", and limitation (x) names the set that
would close it.  Closing it needs rows carrying BOTH quantities for the SAME molecule pair: a
measured solubility and a measured ln gamma^inf.

THE ANSWER, and it is not a matter of degree
---------------------------------------------
Across the whole labelled corpus (108,287 rows, 12,129 pairs, 1,525 solutes, 212 solvents) and
every infinite-dilution pull this repository holds -- the broad IDAC set, the curated idac.csv, the
14,900-row expanded pull, the NIST 2015-2019 pull -- the number of shared PAIRS is **zero**.

It is not a canonicalisation artifact.  There are 22 shared solvents and 9 shared solutes, all of
them small hydrocarbons and aromatics; on exactly those molecules the IDAC side carries 17 pairs
and the solubility side 12, and they do not overlap either.  Relaxing the key to the first block of
the InChIKey -- blind to tautomer, salt and stereochemistry -- leaves it at zero.

The two literatures avoid each other's pairs even where their molecules coincide, which is what one
should expect: gamma^inf is measured by gas chromatography on volatile solutes in industrial
solvents, and solubility on drug-like solids in the solvents a formulator uses.

WHAT THIS CHANGES
-----------------
The bridge is not a data-assembly task and cannot be reached by a wider pull.  It requires
gamma^inf to be MEASURED on pairs that already carry a solubility, which is a laboratory programme.
The Conclusions said "the set that would carry both is named in limitation (x), and building it is
the experiment this work leaves", which implied an intersection waiting to be taken; that sentence
is corrected to say what the experiment actually is.

Usage
-----
    python scripts/analysis/check_regime_bridge_exists.py --json results/regime_bridge.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ["notebooks/data/processed/train.csv", "notebooks/data/processed/val.csv",
          "notebooks/data/processed/test.csv"]
ACTIVITY = {
    "broad_idac_477": "paper/si_tables/broad_idac_set_477.csv",
    "idac_curated": "notebooks/data/raw/idac.csv",
    "idac_expanded": "notebooks/data/raw/idac_expanded.csv",
    "idac_nist_2015_2019": "notebooks/data/raw/idac_nist_2015_2019.csv",
}


def keyer():
    from rdkit import Chem, RDLogger
    from rdkit.Chem import inchi
    RDLogger.DisableLog("rdApp.*")
    canon: dict = {}
    block: dict = {}

    def c(s):
        if s not in canon:
            m = Chem.MolFromSmiles(s) if isinstance(s, str) else None
            canon[s] = Chem.MolToSmiles(m) if m is not None else None
        return canon[s]

    def b(s):
        if s not in block:
            m = Chem.MolFromSmiles(s) if isinstance(s, str) else None
            try:
                block[s] = inchi.MolToInchiKey(m).split("-")[0] if m is not None else None
            except Exception:
                block[s] = None
        return block[s]

    return c, b


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args()
    c, b = keyer()

    sol = pd.concat([pd.read_csv(ROOT / f, low_memory=False) for f in SPLITS], ignore_index=True)
    sol = sol[sol["has_solubility"].astype(bool)]
    sol_pairs = {(c(x), c(y)) for x, y in zip(sol.solute_smiles, sol.solvent_smiles)}
    sol_block = {(b(x), b(y)) for x, y in zip(sol.solute_smiles, sol.solvent_smiles)}
    sol_su = {c(x) for x in sol.solute_smiles}
    sol_sv = {c(y) for y in sol.solvent_smiles}
    print(f"labelled corpus: {len(sol)} rows, {len(sol_pairs)} pairs, "
          f"{len(sol_su)} solutes, {len(sol_sv)} solvents\n")

    out = {"solubility": {"n_rows": int(len(sol)), "n_pairs": len(sol_pairs),
                          "n_solutes": len(sol_su), "n_solvents": len(sol_sv)}, "activity": {}}
    for name, rel in ACTIVITY.items():
        path = ROOT / rel
        if not path.exists():
            print(f"{name:22s} absent")
            continue
        d = pd.read_csv(path, low_memory=False)
        sc = next((x for x in d.columns if "solute" in x and "smiles" in x), None)
        vc = next((x for x in d.columns if "solvent" in x and "smiles" in x), None)
        if sc is None or vc is None:
            print(f"{name:22s} no SMILES columns, skipped")
            continue
        pairs = {(c(x), c(y)) for x, y in zip(d[sc], d[vc])}
        blocks = {(b(x), b(y)) for x, y in zip(d[sc], d[vc])}
        su, sv = {c(x) for x in d[sc]}, {c(y) for y in d[vc]}
        shared_su, shared_sv = su & sol_su, sv & sol_sv
        # the sharp form: even restricted to molecules BOTH sides carry, do the pairs meet?
        on_shared_i = {p for p in pairs if p[0] in shared_su and p[1] in shared_sv}
        on_shared_s = {p for p in sol_pairs if p[0] in shared_su and p[1] in shared_sv}
        rec = {"n_rows": int(len(d)), "n_pairs": len(pairs),
               "shared_pairs": len(pairs & sol_pairs),
               "shared_pairs_first_block": len(blocks & sol_block),
               "shared_solutes": len(shared_su), "shared_solvents": len(shared_sv),
               "pairs_on_shared_molecules_activity": len(on_shared_i),
               "pairs_on_shared_molecules_solubility": len(on_shared_s),
               "their_overlap": len(on_shared_i & on_shared_s)}
        out["activity"][name] = rec
        print(f"{name:22s} {rec['n_rows']:>6} rows {rec['n_pairs']:>5} pairs | "
              f"shared pairs {rec['shared_pairs']:>3} "
              f"(first-block {rec['shared_pairs_first_block']:>3}) | "
              f"shared molecules {rec['shared_solutes']}x{rec['shared_solvents']} -> "
              f"{rec['pairs_on_shared_molecules_activity']} vs "
              f"{rec['pairs_on_shared_molecules_solubility']} pairs, "
              f"overlap {rec['their_overlap']}")

    total = sum(r["shared_pairs"] for r in out["activity"].values())
    out["bridge_exists"] = total > 0
    print(f"\nshared pairs across every pull: {total}")
    print("The bridge is not a data-assembly task. It requires gamma^inf to be MEASURED on pairs "
          "that already carry a solubility." if total == 0 else
          "A bridge set exists; build it.")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(out, indent=2) + "\n")
        print(f"wrote {a.json}")


if __name__ == "__main__":
    main()
