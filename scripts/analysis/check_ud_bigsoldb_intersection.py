#!/usr/bin/env python
"""The UD-intersect-BigSolDB matched set: does it exist, and how big is it?

WHY THIS EXISTS.  Sec. 3.4 said the solubility half of the 2010/dsp question "additionally needs a
UD-intersect-BigSolDB matched set, which this corpus lacks".  That is an absolute claim a referee
can refute in about a second, and it is wrong: the set exists.  It is thin -- 437 of the 5608
labelled test rows, over 11 solutes -- and thinness is the constraint that actually bites, so the
article now says that instead.  This script is what the corrected sentence's numbers come from, and
it is a gate: --check-article fails if the article and the deposit drift apart.

WHY IT MATTERS BEYOND ONE SENTENCE.  Limitation (x) names this set as the experiment that would
close the regime gap between the phenomenon (solubility at finite composition) and the mechanism
(infinite-dilution activity).  Whether it can be built at all is therefore load-bearing for the
Conclusions, which now say building it is the experiment this work leaves.  It can.  What cannot be
built without a GPU is its LEARNED-profile arm: the deployed sigma head emits an untyped 51-bin
profile and the 2010 kernel reads a typed 153-grid, so the paradox comparison under that closure
needs a new head, not just this intersection.

THE MATCH IS ON InChIKey, and that is the looser of the two rules this project uses -- the broad
IDAC set matches that way and the VT-2005-matched set does not (Sec. S3.4 quantifies the
asymmetry).  Reported here because it is the rule that governs the UD deposit's own keys.

Usage
-----
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/check_ud_bigsoldb_intersection.py
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/check_ud_bigsoldb_intersection.py --check-article
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
#: NOT IN THE REPOSITORY.  The UD profile deposit lives outside the tree, so this script reports
#: "unavailable" rather than failing when it is absent -- a checkout without it must still run.
UD = Path.home() / "COSMOSAC/profiles/UD"
SPLIT = ROOT / "notebooks/data/processed/test.csv"
ARTICLE = ROOT / "paper/grounding_paradox.tex"


def ud_keys(path: Path) -> set[str]:
    text = (path / "complist.txt").read_text(errors="ignore")
    return set(re.findall(r"[A-Z]{14}-[A-Z]{10}-[A-Z]", text))


def inchikeys(smiles: pd.Series) -> pd.Series:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import inchi
    RDLogger.DisableLog("rdApp.*")
    cache: dict[str, str | None] = {}

    def one(s: object) -> str | None:
        if not isinstance(s, str):
            return None
        if s not in cache:
            mol = Chem.MolFromSmiles(s)
            try:
                cache[s] = inchi.MolToInchiKey(mol) if mol is not None else None
            except Exception:
                cache[s] = None
        return cache[s]

    return smiles.map(one)


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--ud", type=Path, default=UD)
    a.add_argument("--split", type=Path, default=SPLIT)
    a.add_argument("--check-article", action="store_true")
    a.add_argument("--out", type=Path, default=None)
    args = a.parse_args()

    if not (args.ud / "complist.txt").exists():
        raise SystemExit(f"{args.ud} is not on this machine; the intersection cannot be computed "
                         f"here and nothing is reported.  It is not in the repository by design.")

    keys = ud_keys(args.ud)
    d = pd.read_csv(args.split, low_memory=False)
    lab = d[d["has_solubility"].astype(bool)] if "has_solubility" in d else d
    both = inchikeys(lab["solute_smiles"]).isin(keys) & inchikeys(lab["solvent_smiles"]).isin(keys)
    sub = lab[both]

    result = {
        "ud_compounds": len(keys),
        "n_labelled_test_rows": int(len(lab)),
        "n_matched_rows": int(both.sum()),
        "n_solutes": int(sub["solute_smiles"].nunique()),
        "n_solvents": int(sub["solvent_smiles"].nunique()),
        "n_pairs": int(sub.groupby(["solute_smiles", "solvent_smiles"]).ngroups),
    }
    for k, v in result.items():
        print(f"{k:24s} {v}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")

    if args.check_article:
        tex = ARTICLE.read_text()
        m = re.search(r"That set exists but is thin: \$(\d+)\$ of the \$(\d+)\$ labelled test\s+"
                      r"rows carry a UD profile on both sides, over \$(\d+)\$ solutes and \$(\d+)\$ "
                      r"pairs", tex)
        if m is None:
            raise SystemExit("the sentence this gate binds is not in the article in the form it "
                             "reads; it was reworded or removed")
        want = (str(result["n_matched_rows"]), str(result["n_labelled_test_rows"]),
                str(result["n_solutes"]), str(result["n_pairs"]))
        bad = sum(g != w for g, w in zip(m.groups(), want))
        print("\narticle bind:")
        for label, got, w in zip(("matched rows", "labelled test rows", "solutes", "pairs"),
                                 m.groups(), want):
            print(f"  {'ok  ' if got == w else 'FAIL'}  {label:20s} paper {got:>6s}   "
                  f"deposit {w:>6s}")
        if bad:
            raise SystemExit(f"{bad} of the sentence's numerals disagree with the deposit")


if __name__ == "__main__":
    main()
