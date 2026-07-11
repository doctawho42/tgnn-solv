#!/usr/bin/env python3
"""Extract the Hammett-amenable aromatic subset from a pKa dataset + assign oracle sigma.

Phase-3 (pKa second domain) DATA pipeline. Given an experimental pKa table
(SMILES, pKa) -- recommended source: the DataWarrior/OPERA curated *experimental*
set (Mansouri et al. 2019, J. Cheminform.; public domain) -- this keeps only
monoprotic aromatics whose ionizing group is unambiguous and whose ring
substituents all have tabulated Hammett sigma constants, and emits, per molecule:

    scaffold, pKa0, rho, sigma_total (meta/para additive), positions, has_ortho,
    all_substituents_known, fidelity_bin ("high_F" = meta/para only | "low_F" = ortho/unknown)

sigma_total is the ORACLE physical intermediate z* for the grounding test; the fixed
Hammett closure is g(z*) = pKa0 - rho * sigma_total. The high_F / low_F split IS the
fidelity sweep (Phase-3 scope): the LFER is near-exact on meta/para (small B_clos) and
breaks on ortho/proximal (large B_clos + B_insuff).

CRITICAL: use EXPERIMENTAL pKa only. ChEMBL/Epik *calculated* pKa would make a study of
model/closure behavior circular. Do NOT train the closure study on predicted labels.

Requires rdkit. Run the parser self-test WITHOUT any dataset:
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/data/build_pka_hammett_subset.py --self-test
Build the subset once a dataset CSV is in hand:
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/data/build_pka_hammett_subset.py \
        --input notebooks/data/raw/pka_experimental.csv --smiles-col SMILES --pka-col pKa \
        --out results/pka_hammett/hammett_subset.csv
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from rdkit import Chem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

# --------------------------------------------------------------------------- #
# Ionizing scaffolds. ipso_smarts matches the aromatic carbon (match[0]) bearing
# the ionizing group; group_smarts marks the group atoms to EXCLUDE from substituents.
# rho / pKa0 are the classic reaction-series constants (Hansch-Leo-Taft).
# --------------------------------------------------------------------------- #
SCAFFOLDS = [
    # name          ipso (aromatic C + group)         group atoms         pKa0   rho
    ("benzoic_acid", "[c;R1]C(=O)[OX2H1]",             "C(=O)[OX2H1]",     4.20,  1.00),
    ("phenol",       "[c;R1][OX2H1]",                  "[OX2H1]",          9.99,  2.23),
    ("anilinium",    "[c;R1][NX3;H2]",                 "[NX3;H2]",         4.60,  2.77),
    ("pyridinium",   "[n;R1]",                         "",                 5.25,  5.90),
]

# --------------------------------------------------------------------------- #
# Substituent patterns rooted at the ring atom (match[0] = ring carbon).
# Ordered specific -> generic (first match wins). (sigma_meta, sigma_para).
# --------------------------------------------------------------------------- #
SUBSTITUENTS = [
    ("NO2",    "[c]-[NX3+](=O)[O-]",   (0.71, 0.78)),
    ("CF3",    "[c]-[CX4](F)(F)F",     (0.43, 0.54)),
    ("CN",     "[c]-[CX2]#[NX1]",      (0.56, 0.66)),
    ("COOH",   "[c]-C(=O)[OX2H1]",     (0.37, 0.45)),
    ("COOCH3", "[c]-C(=O)O[CH3]",      (0.37, 0.45)),
    ("COCH3",  "[c]-C(=O)[CH3]",       (0.38, 0.50)),
    ("CHO",    "[c]-[CX3H1]=O",        (0.35, 0.42)),
    ("OCH3",   "[c]-[OX2][CH3]",       (0.12, -0.27)),
    ("OH",     "[c]-[OX2H1]",          (0.12, -0.37)),
    ("NMe2",   "[c]-[NX3]([CH3])[CH3]",(-0.16, -0.83)),
    ("NHAc",   "[c]-[NX3H1]C(=O)C",    (0.21, 0.00)),
    ("NH2",    "[c]-[NX3H2]",          (-0.16, -0.66)),
    ("F",      "[c]-[F]",              (0.34, 0.06)),
    ("Cl",     "[c]-[Cl]",             (0.37, 0.23)),
    ("Br",     "[c]-[Br]",             (0.39, 0.23)),
    ("I",      "[c]-[I]",              (0.35, 0.18)),
    ("tBu",    "[c]-[CX4]([CH3])([CH3])[CH3]", (-0.10, -0.20)),
    ("C2H5",   "[c]-[CH2][CH3]",       (-0.07, -0.15)),
    ("CH3",    "[c]-[CH3]",            (-0.07, -0.17)),
]
_SUB_COMPILED = [(name, Chem.MolFromSmarts(sm), sig) for name, sm, sig in SUBSTITUENTS]


def _ring_distance(mol, ring, a, b):
    """Shortest number of ring bonds between atoms a,b within the given ring atom set."""
    ringset = set(ring)
    from collections import deque
    seen = {a: 0}
    q = deque([a])
    while q:
        cur = q.popleft()
        if cur == b:
            return seen[cur]
        for nb in mol.GetAtomWithIdx(cur).GetNeighbors():
            j = nb.GetIdx()
            if j in ringset and j not in seen:
                seen[j] = seen[cur] + 1
                q.append(j)
    return seen.get(b, -1)


def assign_hammett_sigma(smiles: str):
    """Return a Hammett record for a monoprotic aromatic, or None if not amenable."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    ri = mol.GetRingInfo()

    for name, ipso_sm, group_sm, pka0, rho in SCAFFOLDS:
        ipso_pat = Chem.MolFromSmarts(ipso_sm)
        matches = mol.GetSubstructMatches(ipso_pat)
        if len(matches) != 1:               # require a UNIQUE ionizing site (monoprotic, unambiguous)
            continue
        ipso = matches[0][0]
        # the aromatic ring containing ipso
        ring = next((r for r in ri.AtomRings() if ipso in r and
                     all(mol.GetAtomWithIdx(i).GetIsAromatic() for i in r)), None)
        if ring is None or len(ring) != 6:
            continue
        group_atoms = set()
        if group_sm:
            gp = Chem.MolFromSmarts(group_sm)
            for m in mol.GetSubstructMatches(gp):
                group_atoms.update(m)

        subs = []           # (position, name, sigma_at_position)
        ok = True
        for ci in ring:
            if ci == ipso:
                continue
            atom = mol.GetAtomWithIdx(ci)
            # exocyclic heavy neighbors not part of the ionizing group
            exo = [nb.GetIdx() for nb in atom.GetNeighbors()
                   if nb.GetIdx() not in ring and nb.GetAtomicNum() > 1
                   and nb.GetIdx() not in group_atoms]
            if not exo:
                continue                     # unsubstituted position (H)
            dist = _ring_distance(mol, ring, ipso, ci)
            pos = {1: "ortho", 2: "meta", 3: "para"}.get(dist)
            # identify the substituent by a pattern rooted at this ring carbon
            found = None
            for sname, patt, sig in _SUB_COMPILED:
                if patt is None:
                    continue
                for mm in mol.GetSubstructMatches(patt):
                    if mm[0] == ci:
                        found = (sname, sig)
                        break
                if found:
                    break
            if found is None:
                ok = False                   # an unrecognized substituent -> not fully known
                subs.append((pos, "UNKNOWN", None))
                continue
            sname, (sm_meta, sm_para) = found
            sigma = sm_meta if pos == "meta" else (sm_para if pos == "para" else None)  # ortho: no clean sigma
            subs.append((pos, sname, sigma))

        if not subs:
            # unsubstituted parent (e.g. benzoic acid itself) -> sigma_total 0, valid high_F point
            return dict(smiles=smiles, scaffold=name, pka0=pka0, rho=rho, sigma_total=0.0,
                        n_sub=0, has_ortho=False, all_known=True, fidelity_bin="high_F",
                        substituents=[])
        has_ortho = any(p == "ortho" for p, _, _ in subs)
        all_known = ok
        # sigma_total from meta/para only (ortho has no clean tabulated sigma)
        clean = [s for p, _, s in subs if p in ("meta", "para") and s is not None]
        sigma_total = float(sum(clean)) if clean else 0.0
        bin_ = "high_F" if (all_known and not has_ortho) else "low_F"
        return dict(smiles=smiles, scaffold=name, pka0=pka0, rho=rho, sigma_total=sigma_total,
                    n_sub=len(subs), has_ortho=has_ortho, all_known=all_known,
                    fidelity_bin=bin_, substituents=subs)
    return None


# --------------------------------------------------------------------------- #
def self_test():
    cases = [
        # smiles, expected scaffold, expected sigma_total (meta/para), expected bin
        ("OC(=O)c1ccccc1",                 "benzoic_acid", 0.00, "high_F"),   # benzoic acid
        ("OC(=O)c1ccc([N+](=O)[O-])cc1",   "benzoic_acid", 0.78, "high_F"),   # p-nitro
        ("OC(=O)c1cccc(Cl)c1",             "benzoic_acid", 0.37, "high_F"),   # m-chloro
        ("OC(=O)c1ccc(OC)cc1",             "benzoic_acid", -0.27, "high_F"),  # p-methoxy
        ("OC(=O)c1ccccc1Cl",               "benzoic_acid", 0.00, "low_F"),    # o-chloro -> ortho bin
        ("Oc1ccc([N+](=O)[O-])cc1",        "phenol",       0.78, "high_F"),   # p-nitrophenol
        ("Nc1ccc([N+](=O)[O-])cc1",        "anilinium",    0.78, "high_F"),   # p-nitroaniline
    ]
    print("[self-test] assign_hammett_sigma:")
    npass = 0
    for smi, exp_scaf, exp_sig, exp_bin in cases:
        rec = assign_hammett_sigma(smi)
        if rec is None:
            print(f"  FAIL  {smi:32s} -> None (expected {exp_scaf})")
            continue
        pred_pka = rec["pka0"] - rec["rho"] * rec["sigma_total"]
        ok = (rec["scaffold"] == exp_scaf and abs(rec["sigma_total"] - exp_sig) < 1e-6
              and rec["fidelity_bin"] == exp_bin)
        npass += ok
        flag = "ok  " if ok else "FAIL"
        print(f"  {flag}  {smi:32s} {rec['scaffold']:12s} sigma={rec['sigma_total']:+.2f} "
              f"bin={rec['fidelity_bin']:6s} g(z*)=pKa {pred_pka:5.2f}")
    print(f"[self-test] {npass}/{len(cases)} passed")
    return npass == len(cases)


def build_subset(inp: Path, smiles_col: str, pka_col: str, out: Path):
    import csv
    rows_in = list(csv.DictReader(inp.open()))
    kept = []
    for r in rows_in:
        smi = r.get(smiles_col)
        if not smi:
            continue
        rec = assign_hammett_sigma(smi)
        if rec is None:
            continue
        try:
            rec["pka_exp"] = float(r.get(pka_col, "nan"))
        except (TypeError, ValueError):
            continue
        rec["substituents"] = ";".join(f"{p}:{n}" for p, n, _ in rec["substituents"])
        kept.append(rec)
    out.parent.mkdir(parents=True, exist_ok=True)
    if kept:
        cols = ["smiles", "scaffold", "pka0", "rho", "sigma_total", "pka_exp", "n_sub",
                "has_ortho", "all_known", "fidelity_bin", "substituents"]
        with out.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for rec in kept:
                w.writerow({k: rec[k] for k in cols})
    hi = sum(1 for r in kept if r["fidelity_bin"] == "high_F")
    print(f"[build] {len(rows_in)} in -> {len(kept)} Hammett-amenable "
          f"({hi} high_F, {len(kept)-hi} low_F). wrote {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--input", type=Path)
    ap.add_argument("--smiles-col", default="SMILES")
    ap.add_argument("--pka-col", default="pKa")
    ap.add_argument("--out", type=Path, default=Path("results/pka_hammett/hammett_subset.csv"))
    args = ap.parse_args()
    if args.self_test or not args.input:
        self_test()
        if not args.input:
            return
    build_subset(args.input, args.smiles_col, args.pka_col, args.out)


if __name__ == "__main__":
    main()
