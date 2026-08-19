#!/usr/bin/env python
"""Build the out-of-sample glycol-ether row set from ThermoML, and report ONLY its geometry.

WHAT THIS IS FOR
----------------
The glycol-ether separation is the one row set the admissibility rule leaves standing, and a
chemistry-blind relabelling of the same molecules reaches its margin in a tenth of draws.  The only
thing that settles a search's survivor is the same measurement on rows the search never saw.  The
pre-declared out-of-sample test returned NOT TESTABLE -- but `results/glycol_external_scope/scope.json`
(2026-08-11) established that this was a property of the two sets that were searched and not of the
literature: four external sources exist, two of them machine-readable through this repository's own
ThermoML fetcher.

THIS SCRIPT READS NO OUTCOME QUANTITY.  It fetches, extracts, filters on convention, canonicalises,
excludes pairs the broad set already carries, and prints the GEOMETRY: how many rows survive, over
which pairs, solutes, solvents, temperatures and source DOIs.  No MSE, no bound, no margin.  That
order is the precedent this project already set for the PGL test, whose pre-declaration records it:
"What HAD been established first is the geometry of the candidate row sets ... No outcome quantity
was read."  A test cannot be designed without knowing whether its data exist; it can be designed
without knowing what it will say.

THE THREE GUARDS, and each has a documented reason to be here
-------------------------------------------------------------
CONVENTION.  Only rows whose ThermoML eStandardState is a pure-liquid-solute basis are admitted,
which is what the three in-sample sources use.  The extractor does not enforce it.  The scoping
note calls this the single highest-risk step: a wrong-convention row is worse than no row, because
it enters the same column as the others and nothing downstream can tell.

PAIR OVERLAP.  Net-new pairs are counted on CANONICAL SMILES before anything else, because the
candidate sources are known to duplicate the in-sample ones -- diethylene glycol against the
alkanes of 10.1016/j.jct.2016.10.013, triethylene glycol against the aromatics of
10.1021/je020196d.  This is the guard the E2 crystal pool failed, where 97.76% of a 15,427-molecule
pool was already labelled in train and the null it produced was read as "grounding does not help".
An estimate of the overlap is not a measurement of it.

ADMISSIBILITY.  The surviving set must reach the same bar the map's own rule sets: n >= 40, at
least two surviving source DOIs, and a leave-one-source-out deletion that leaves at least 16 rows.
Reported, not enforced -- if it fails, that is the finding.

Usage
-----
    python scripts/analysis/build_glycol_oos_thermoml.py --out results/b_insuff/glycol_oos_thermoml
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tgnn_solv.data.thermoml_idac import (  # noqa: E402
    extract_idac_rows,
    fetch_thermoml_json,
    load_thermoml_json,
)

#: Ranks 1 and 2 of results/glycol_external_scope/scope.json -- the two candidates that carry a
#: ThermoML record.  Ranks 3 and 4 have none and would need hand transcription from PDF tables.
CANDIDATES = ["10.1016/j.jct.2013.05.011", "10.1021/je0102107"]
#: The pure-liquid-solute basis the three in-sample sources use.  Anything else is a different
#: quantity wearing the same column name.
ADMISSIBLE_STATES = {"Pure liquid solute", "Pure compound"}
#: The in-sample stratum, whose pairs must be excluded before a single row is counted as new.
BROAD = ROOT / "paper/si_tables/broad_idac_set_477.csv"
#: The four glycol ethers the stratum is defined on (canonical SMILES).
GLYCOLS = {"OCCO", "OCCOCCO", "OCCOCCOCCO", "OCCOCCOCCOCCO"}


#: A SECOND ADMISSION RULE, and it is declared here rather than applied quietly.
#:
#: 10.1021/je0102107 is titled "Infinite Dilution Activity Coefficients in Ethylene Glycol and
#: Ethylene Carbonate" and carries eleven two-component activity-coefficient datasets, and the
#: repository's extractor returns ZERO rows from it: the record never STATES infinite dilution.
#: It has no composition constraint and no solute mole-fraction variable -- only pressure and
#: temperature.  The extractor's gate is right to refuse it, because "the title says so" is not a
#: machine-checkable basis.
#:
#: What IS machine-checkable is the shape: a two-component dataset whose property is an activity
#: coefficient, with NO composition axis of any kind, measured by chromatography.  GLC retention
#: measures gamma^inf by construction, and a composition axis is exactly what such a dataset would
#: carry if it were not at infinite dilution.
#:
#: THIS RULE WAS WRITTEN AFTER SEEING THAT IT CHANGES ADMISSIBILITY -- one source cannot satisfy the
#: map's leave-one-source-out requirement and two can -- which is the post-hoc hazard this project
#: has been bitten by before.  The mitigation is that it is declared BEFORE any margin exists, and
#: that the geometry and the outcome are both reported under the strict rule AND under this one.
#: If the two disagree, that disagreement is the finding.
CHROMATOGRAPHIC_IDAC = "chromatography, two components, no composition axis"


def admit_chromatographic_idac(record: dict, doi: str) -> list[dict]:
    """Rows from a record the strict extractor refuses, under the rule declared above."""
    from tgnn_solv.data.thermoml_idac import (
        _as_list, _compound_lookup, _extract_org_num, _property_metadata,
    )
    compounds = _compound_lookup(record)
    out: list[dict] = []
    for dataset in _as_list(record.get("PureOrMixtureData")):
        ids = [n for c in _as_list(dataset.get("Component"))
               if (n := _extract_org_num(c)) is not None]
        if len(ids) != 2:
            continue
        # the whole of the rule: no composition axis on either side
        if any("Composition" in json.dumps(c) or "MoleFraction" in json.dumps(c)
               for c in _as_list(dataset.get("Constraint")) + _as_list(dataset.get("Variable"))):
            continue
        for prop in _as_list(dataset.get("Property")):
            md = _property_metadata(prop)
            if md is None or md.get("method") != "Chromatography":
                continue
            solute = md["solute_org_num"]
            solvent = next((i for i in ids if i != solute), None)
            if solvent is None:
                continue
            for point in _as_list(dataset.get("NumValues")):
                temps = [float(v["nVarValue"]) for v in _as_list(point.get("VariableValue"))
                         if "nVarValue" in v]
                vals = [float(v["nPropValue"]) for v in _as_list(point.get("PropertyValue"))
                        if "nPropValue" in v]
                if not temps or not vals or vals[0] <= 0:
                    continue
                out.append({
                    "doi": doi, "solute_org_num": solute,
                    "solute_smiles": compounds.get(solute, {}).get("smiles"),
                    "solvent_smiles": compounds.get(solvent, {}).get("smiles"),
                    "solute_name": compounds.get(solute, {}).get("name"),
                    "temperature": temps[0], "gamma_inf": vals[0],
                    "ln_gamma_inf": __import__("math").log(vals[0]),
                    "standard_state": md.get("standard_state"), "method": md.get("method"),
                    "idac_basis": CHROMATOGRAPHIC_IDAC,
                })
    return out


def canonical(smiles: object) -> str | None:
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
    mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
    return Chem.MolToSmiles(mol) if mol is not None else None


def record_for(doi: str, cache: Path) -> dict:
    """The ThermoML record, from the local corpus if it is there and the network otherwise."""
    local = cache / (doi.replace("/", "__") + ".json")
    if local.exists():
        print(f"  {doi}: local")
        return load_thermoml_json(local)
    print(f"  {doi}: fetching")
    blob = fetch_thermoml_json(doi)
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps(blob))
    return blob


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dois", nargs="+", default=CANDIDATES)
    ap.add_argument("--cache", type=Path, default=ROOT / "notebooks/data/raw/thermoml_json")
    ap.add_argument("--out", type=Path, default=ROOT / "results/b_insuff/glycol_oos_thermoml")
    ap.add_argument("--admit-chromatographic-idac", action="store_true",
                    help="also admit records the strict extractor refuses, under the declared "
                         "rule above. Reported separately, never merged silently.")
    a = ap.parse_args()

    print("== retrieving")
    rows: list[dict] = []
    for doi in a.dois:
        rec = record_for(doi, a.cache)
        got = extract_idac_rows(rec, source_label=doi)
        for r in got:
            r.setdefault("idac_basis", "declared in the record")
        print(f"     {len(got)} IDAC rows extracted (strict)")
        if not got and a.admit_chromatographic_idac:
            got = admit_chromatographic_idac(rec, doi)
            print(f"     {len(got)} admitted under the declared chromatographic rule")
        rows.extend(got)
    if not rows:
        raise SystemExit("no IDAC rows extracted from any candidate; nothing to report")

    d = pd.DataFrame(rows)
    print(f"\n== {len(d)} rows before any filter")
    print("   standard states present:", sorted(set(d.get("standard_state", pd.Series()).dropna())))

    # --- guard 1: convention -------------------------------------------------------------
    before = len(d)
    d = d[d["standard_state"].isin(ADMISSIBLE_STATES)].copy()
    print(f"\n== convention: {len(d)} of {before} rows on a pure-liquid-solute basis")
    if d.empty:
        raise SystemExit("no row survives the convention filter; the set is not usable")

    # --- restrict to the glycol ethers the stratum is defined on -------------------------
    d["solvent_can"] = [canonical(s) for s in d["solvent_smiles"]]
    d["solute_can"] = [canonical(s) for s in d["solute_smiles"]]
    d = d[d["solvent_can"].isin(GLYCOLS) & d["solute_can"].notna()].copy()
    print(f"== glycol-ether solvents: {len(d)} rows over "
          f"{d['solvent_can'].nunique()} of the stratum's 4 solvents")
    if d.empty:
        raise SystemExit("no glycol-ether row in these sources; the candidates do not deliver")

    # --- guard 2: pair overlap with the in-sample stratum --------------------------------
    broad = pd.read_csv(BROAD)
    broad["sol"] = [canonical(s) for s in broad["solute_smiles"]]
    broad["slv"] = [canonical(s) for s in broad["solvent_smiles"]]
    seen = set(zip(broad["sol"], broad["slv"]))
    d["pair"] = list(zip(d["solute_can"], d["solvent_can"]))
    d["net_new"] = [p not in seen for p in d["pair"]]
    n_pairs = d["pair"].nunique()
    new = d[d["net_new"]].copy()
    print("\n== overlap with the broad set")
    print(f"   {n_pairs} distinct pairs here; {new['pair'].nunique()} of them net-new")
    print(f"   {len(new)} of {len(d)} rows sit on a net-new pair "
          f"({100 * len(new) / len(d):.1f}%)")

    # --- guard 3: admissibility, reported not enforced -----------------------------------
    print("\n== geometry of the net-new set")
    if new.empty:
        print("   EMPTY. Every pair these sources carry is already in the broad set: the "
              "candidates duplicate the in-sample stratum and deliver no out-of-sample test.")
    else:
        per_doi = new.groupby("doi").size().to_dict()
        loso = {k: len(new) - v for k, v in per_doi.items()}
        print(f"   rows {len(new)}   pairs {new['pair'].nunique()}   "
              f"solutes {new['solute_can'].nunique()}   solvents {new['solvent_can'].nunique()}")
        print(f"   temperatures {sorted(round(float(t), 2) for t in new['temperature'].unique())}")
        print(f"   rows per source DOI: {per_doi}")
        print(f"   leave-one-source-out leaves: {loso}")
        print(f"\n   n >= 40                      {'PASS' if len(new) >= 40 else 'FAIL'} "
              f"({len(new)})")
        print(f"   >= 2 source DOIs             "
              f"{'PASS' if len(per_doi) >= 2 else 'FAIL'} ({len(per_doi)})")
        print(f"   LOSO leaves >= 16 rows       "
              f"{'PASS' if loso and min(loso.values()) >= 16 else 'FAIL'} "
              f"({min(loso.values()) if loso else 0})")

    a.out.mkdir(parents=True, exist_ok=True)
    d.to_csv(a.out / "candidate_rows.csv", index=False)
    new.to_csv(a.out / "net_new_rows.csv", index=False)
    geometry = {
        "what": "GEOMETRY ONLY -- no outcome quantity is computed here, by design",
        "dois": a.dois,
        "n_rows_extracted": int(before),
        "n_after_convention": int(len(d)),
        "n_glycol_rows": int(len(d)),
        "n_pairs": int(n_pairs),
        "n_net_new_rows": int(len(new)),
        "n_net_new_pairs": int(new["pair"].nunique()) if len(new) else 0,
        "n_solutes": int(new["solute_can"].nunique()) if len(new) else 0,
        "n_solvents": int(new["solvent_can"].nunique()) if len(new) else 0,
        "rows_per_source": new.groupby("doi").size().to_dict() if len(new) else {},
        "admissible": bool(len(new) >= 40
                           and new["doi"].nunique() >= 2
                           and (len(new) - new.groupby("doi").size().max()) >= 16)
        if len(new) else False,
    }
    (a.out / "geometry.json").write_text(json.dumps(geometry, indent=2, default=str) + "\n")
    print(f"\nwrote {a.out}/geometry.json  (and the two row files)")
    print("NEXT, and only in this order: write the pre-declaration for THIS row set, hash it, "
          "commit it, and only then compute a margin.")


if __name__ == "__main__":
    main()
