#!/usr/bin/env python3
r"""Stratified map of where the COSMO-SAC closure binds, replacing the aggregate verdict.

WHY THIS EXISTS.  The aggregate separation margin  MSE - 2 B_insuff^up  on the broad IDAC set
does not survive the manuscript's own two robustness operations applied together, and it is
carried by one publication.  The reason is structural, not a data defect:

    B_insuff^up is nearly stratum-independent -- it is bounded above by the within-stratum
    label variance and below by replicate/label noise, and sits in a narrow band -- while MSE
    varies by an order of magnitude across chemically distinct strata.  The aggregate margin is
    therefore a composition-weighted average dominated by whichever stratum the closure fails
    on hardest, and it will report "the map binds" for any set whose composition happens to
    contain one.  An aggregate is the wrong output of this instrument.

This script computes the replacement: the margin as a MAP over chemical strata.

----------------------------------------------------------------------------------------------
THE STRATIFICATION RULE.  Declared here, in full, before any margin is computed.  It is a pure
function of the SOLVENT SMILES (plus, on the second axis, of whether the solute is water).  It
never reads m, g, the squared error, the MSE, B_insuff, the margin, the source DOI or the
bootstrap.  `classify_solvent' below takes one argument, a SMILES string; that is the whole of
its input, and it is the mechanical guarantee that no stratum was chosen for its outcome.

AXIS 1 -- SOLVENT CLASS.  An ordered cascade over functional groups; the first class a solvent
matches is the class it takes.  The order is by hydrogen-bonding role first, because that is the
axis on which COSMO-SAC's hydrogen-bonding term acts, then by the dominant functional group.

  1. water                  -- H2O.  The only solvent whose entire molecular surface is
                               hydrogen-bond active, with sigma-profile mass at both extremes
                               and the smallest cavity of any liquid, so the Staverman-Guggenheim
                               combinatorial term is at its most extreme and the two
                               combinatorial conventions disagree most.
  2. glycol_ether           -- at least one O-H and at least two oxygens: the ethylene-glycol
                               oligomers.  Donor and acceptor sit on the same flexible chain, so
                               intramolecular hydrogen bonds form and the sigma-profile is
                               conformer-dependent.  COSMO-SAC scores one gas-phase conformer as
                               a bag of independent surface segments with no memory of
                               connectivity; this is its documented worst case.
  3. mono_alcohol           -- exactly one O-H, exactly one oxygen, no N and no halogen.
                               Single-donor self-associating liquids: the chemistry the 2002
                               hydrogen-bonding term was fitted on.
  4. nh_protic              -- an N-H donor (amides after tautomer normalisation, primary and
                               secondary amines, piperidine).  Nitrogen donors are weaker and
                               differently shaped than O-H, and the 2002 kernel lumps them under
                               one sigma_hb threshold shared with O-H; this class tests that
                               lumping.
  5. aryl_ether             -- no O-H/N-H, but an alkyl-aryl ether oxygen (anisole, phenetole).
                               The lone pairs are delocalised into the ring, so the acceptor
                               strength is far below a dialkyl ether and a single sigma_hb
                               cut-off is at its crudest.  Tested before the general acceptor
                               class precisely so that it is not swallowed by it.
  6. aprotic_acceptor       -- no O-H or N-H, but a carbonyl, a nitrile, a pyridine-type
                               aromatic nitrogen, an ether oxygen, a nitro group or a tertiary
                               amine nitrogen: esters, ketones, aldehydes, nitriles, azines,
                               ethers, nitroalkanes, trialkylamines.  Acceptor mass only, no
                               donor.  (Only esters, ketones, nitriles and azines occur among
                               the 36 solvents; the rest of the list is there because the same
                               cascade is applied to the solutes, where they do occur.)
  7. halogenated            -- any C-F/Cl/Br/I and no hydrogen-bond donor.  Large, soft,
                               polarisable halogen surfaces; 2002 carries no dispersion term and
                               one effective contact area, which is where that hurts most.
  8. aromatic_hydrocarbon   -- carbon and hydrogen only, with an aromatic ring.  Quadrupolar pi
                               face, sigma near zero over the ring.
  9. aliphatic_hydrocarbon  -- carbon and hydrogen only, no ring aromaticity.  Pure dispersion;
                               sigma is approximately zero everywhere, so the residual term
                               nearly vanishes and the prediction is almost entirely
                               combinatorial.

  A COARSE level is reported alongside, so that no level of granularity is itself a choice:
  hb_donor_acceptor_O (1+2+3), hb_donor_N (4), hb_acceptor_only (5+6), halogenated_nonHB (7),
  hydrocarbon_nonHB (8+9).  And a FINE level splits classes 4 and 5 into their functional-group
  families (amide / amine, ester / ketone / nitrile / azine) so the coarser classes cannot be
  said to be hiding a split.  Every class is reported at every level, including the ones with
  too few rows to bound, the ones where nothing separates, and the ones that favour the paper.

AXIS 2 -- SOLUTE ROLE.  water-as-solute against organic-solute, reported separately and crossed
with axis 1.  Water as the dilute solute is a different physical situation from water as the
solvent: an isolated H2O in an organic continuum has all four of its hydrogen-bond sites
unsatisfied by like molecules, a state the segment-activity expression is not fitted near, and
COSMO-SAC-2002's documented weakness is specific to it.  A SECONDARY solute-family axis (the
same functional-group cascade applied to the solute) is reported too, because a practitioner
deciding where to spend grounding effort needs both halves of the pair.

BOUNDABILITY.  One estimator cell is used everywhere: the manuscript's headline cell, 8
equal-count bins of g(z*) with the Bessel within-bin variance.  It is held fixed across every
stratum, both units and both conventions; no cell is selected anywhere in this script.  A
stratum is declared boundable at that cell when n >= 40, so that each of the 8 equal-count bins
holds at least 5 rows and the within-bin variance exists in every bin.  Smaller strata are still
reported -- with n, MSE, share of squared error and the estimate -- and additionally carry the
manuscript's own resample-adaptive rule max(3, n // 10), which is coarser and therefore more
conservative at small n and is defined at every n.  Nothing is dropped for being small.

UNITS AND CONVENTIONS.  Every stratum is reported at both units of analysis -- every row, and
one row per pair taken nearest 298.15 K -- and under both combinatorial conventions, `full' and
the deployed residual-only `res'.  Four numbers per stratum, all of them printed.

----------------------------------------------------------------------------------------------
ADMISSIBILITY.  One rule decides what may be STATED as a finding, applied to every stratum
alike -- the aggregate, the cells that favour the paper, and the cells that do not:

    a stratum may be stated as a finding only if it is (a) BOUNDABLE at the fixed headline
    cell, and (b) ROBUST TO LEAVE-ONE-SOURCE-OUT: its margin keeps its sign when any single
    source publication contributing to it is deleted.

Everything else is reported in the map and not stated.  Each stratum carries its n, its source
publications, its margin, its interval, its admissibility and the reason -- and a cell that
fails (b) is labelled with the publication that carries it.

Three things this rule needs pinned down, all of them decided here and not per stratum:

  * A stratum drawing on ONE publication fails (b) by non-testability, not by passing it
    vacuously.  There is no deletion to perform, so the sign was never put at risk.
  * A deletion that leaves fewer than 2 x n_bins rows leaves the fixed cell UNDEFINED, so the
    sign is not verifiable and the stratum fails (b).  A deletion that leaves the cell defined
    but the remainder below the boundable size is counted, reported, and additionally tracked
    by a STRICT variant of (b) in which every deletion must leave a still-boundable remainder.
    Both verdicts are deposited; the strict one is the more conservative and is the one to
    quote when a cell is close.
  * The rule tests whether a NUMBER is stable, not what it means.  The instrument is one-sided
    (Lemma `decomp': B_insuff is bounded above, B_clos below), so a positive margin certifies
    B_clos > 0 while a non-positive one is failure to separate and not a certified reversal --
    that would need a LOWER bound on B_insuff.  An admissible stratum with a non-positive
    margin therefore licenses nothing; `licenses' spells this out per stratum.

    Two directional cautions are deposited with the numbers rather than left to the reader.
    The Bessel within-bin variance inflates as the bins empty, so a deletion that leaves a
    small remainder biases B_insuff^up UP and the margin DOWN: for a positive-margin stratum
    that makes (b) conservative, and for a non-positive one it makes (b) ANTI-conservative --
    a robustly negative sign can be the estimator thinning rather than the chemistry.

OVERLAP.  The two axes are not independent -- a row with water as the dilute solute also has a
solvent, and a row in a solvent class also has a solute role -- so two admissible strata can be
the same rows twice.  Every pair of strata is therefore intersected, in rows and in pairs, and
the containment is named (identical / one inside the other / partial / disjoint).  For the
strata a reader might cite together the map additionally recomputes the margin on each SIDE of
the overlap, A \ B and B \ A, at the same fixed cell: that is the measurement of whether the two
cells carry independent evidence, in place of an assertion that they do.

ESTIMATORS.  lotv() and the two-way (solute x solvent) cluster bootstrap are imported from
scripts/analysis/run_b_insuff_estimator_grid.py.  There is no second implementation here.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_stratified_map.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from run_b_insuff_estimator_grid import lotv, two_way_margin_boot  # noqa: E402

BROAD = ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv"
CORNER = ROOT / "paper" / "si_tables" / "vt2005_matched_set_60.csv"
OUT = ROOT / "results" / "b_insuff" / "stratified_map.json"
OUT_CSV = ROOT / "results" / "b_insuff" / "stratified_map_table.csv"
ADM_JSON = ROOT / "results" / "b_insuff" / "admissibility.json"
ADM_CSV = ROOT / "results" / "b_insuff" / "admissibility_table.csv"
OVERLAP_CSV = ROOT / "results" / "b_insuff" / "stratum_overlap.csv"

N_BINS = 8          # the manuscript's headline estimator cell ...
DDOF = 1            # ... 8 equal-count bins, Bessel within-bin variance.
MIN_BOUNDABLE = 40  # 8 bins x >= 5 rows per bin
N_BOOT = 3000
T_REF = 298.15
N_NULL = 2000       # random-partition null for the "MSE varies, B_insuff does not" claim

# --------------------------------------------------------------------------------------------
# THE RULE.  A pure function of a SMILES string.  No outcome quantity is in scope.
# --------------------------------------------------------------------------------------------
_TAUT = rdMolStandardize.TautomerEnumerator()

_SMARTS = {
    "oh": "[OX2H]",
    "nh": "[NX3;H1,H2],[nX3;H1]",
    "carbonyl": "[CX3]=[OX1]",
    "nitrile": "[CX2]#[NX1]",
    "azine": "[n]",
    "aryl_alkyl_ether": "[c][OX2][CX4]",
    "halogen": "[F,Cl,Br,I]",
    "amide": "[CX3](=[OX1])[NX3]",
    "ester": "[CX3](=[OX1])[OX2][#6]",
    "ketone": "[#6][CX3](=[OX1])[#6]",
    "aldehyde": "[CX3H1](=[OX1])[#6]",
    "ether": "[#8X2]([#6])[#6]",
    "alkene": "[CX3]=[CX3]",
    "alkyne": "[CX2]#[CX2]",
    "nitro": "[NX3](=[OX1])[OX1]",
    "tertiary_amine": "[NX3;H0;!$([NX3]=*);!$([NX3][!#6])]",
}


def _q(name: str):
    pat = _SMARTS[name]
    if "," in pat and not pat.startswith("["):
        return [Chem.MolFromSmarts(p) for p in pat.split(",")]
    if name == "nh":
        return [Chem.MolFromSmarts("[NX3;H1,H2]"), Chem.MolFromSmarts("[nX3;H1]")]
    return [Chem.MolFromSmarts(pat)]


_Q = {k: _q(k) for k in _SMARTS}


def _has(mol, name: str) -> bool:
    return any(mol.HasSubstructMatch(q) for q in _Q[name])


def _prep(smiles: str):
    """Parse and normalise tautomers.

    The UD compound list stores formamide and N-methylformamide as their imidic-acid
    tautomers (`N=CO', `CN=CO'); the liquids are the amides, and the N-H donor is the whole
    point of their class.  RDKit's canonical tautomer restores it.  This is a chemistry fix
    applied to every molecule alike, not an exception carved for two of them.
    """
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        raise ValueError(f"unparseable SMILES: {smiles!r}")
    try:
        return _TAUT.Canonicalize(mol)
    except Exception:
        return mol


def classify_solvent(smiles: str) -> str:
    """AXIS 1.  Ordered cascade; the first match wins.  Input: a SMILES string, nothing else."""
    mol = _prep(smiles)
    syms = {a.GetSymbol() for a in mol.GetAtoms()}
    if Chem.MolToSmiles(mol) == "O":
        return "water"
    n_ox = sum(a.GetSymbol() == "O" for a in mol.GetAtoms())
    n_n = sum(a.GetSymbol() == "N" for a in mol.GetAtoms())
    has_hal = _has(mol, "halogen")
    if _has(mol, "oh") and n_ox >= 2:
        return "glycol_ether"
    if _has(mol, "oh") and n_ox == 1 and n_n == 0 and not has_hal:
        return "mono_alcohol"
    if _has(mol, "nh"):
        return "nh_protic"
    if _has(mol, "aryl_alkyl_ether"):
        return "aryl_ether"
    if any(_has(mol, k) for k in ("carbonyl", "nitrile", "azine", "ether", "nitro",
                                  "tertiary_amine")):
        return "aprotic_acceptor"
    if has_hal:
        return "halogenated"
    if syms <= {"C", "H"}:
        return ("aromatic_hydrocarbon" if any(a.GetIsAromatic() for a in mol.GetAtoms())
                else "aliphatic_hydrocarbon")
    return "unclassified"


COARSE = {
    "water": "hb_donor_acceptor_O",
    "glycol_ether": "hb_donor_acceptor_O",
    "mono_alcohol": "hb_donor_acceptor_O",
    "nh_protic": "hb_donor_N",
    "aprotic_acceptor": "hb_acceptor_only",
    "aryl_ether": "hb_acceptor_only",
    "halogenated": "halogenated_nonHB",
    "aromatic_hydrocarbon": "hydrocarbon_nonHB",
    "aliphatic_hydrocarbon": "hydrocarbon_nonHB",
}


def refine_family(smiles: str) -> str:
    """FINE level: split classes 4 and 5 into functional-group families.  Same pure input."""
    cls = classify_solvent(smiles)
    mol = _prep(smiles)
    if cls == "nh_protic":
        return "amide_NH" if _has(mol, "amide") else "amine_NH"
    if cls == "aprotic_acceptor":
        if _has(mol, "ester"):
            return "ester"
        if _has(mol, "nitrile"):
            return "nitrile"
        if _has(mol, "azine"):
            return "azine"
        if _has(mol, "ketone") or _has(mol, "aldehyde"):
            return "ketone_aldehyde"
        if _has(mol, "nitro"):
            return "nitro"
        if _has(mol, "tertiary_amine"):
            return "tertiary_amine"
        if _has(mol, "ether"):
            return "ether"
        return "aprotic_acceptor_other"
    if cls == "halogenated":
        return ("halogenated_aromatic" if any(a.GetIsAromatic() for a in mol.GetAtoms())
                else "halogenated_aliphatic")
    return cls


def classify_solute_family(smiles: str) -> str:
    """SECONDARY axis.  The same cascade, applied to the solute, with the hydrocarbons split
    by saturation because a solute's dispersion-only surface is the relevant distinction."""
    cls = classify_solvent(smiles)
    if cls == "water":
        return "water"
    mol = _prep(smiles)
    if cls == "aliphatic_hydrocarbon":
        if _has(mol, "alkyne"):
            return "alkyne"
        if _has(mol, "alkene"):
            return "alkene"
        return "alkane"
    if cls == "aprotic_acceptor":
        if _has(mol, "ester"):
            return "ester"
        if _has(mol, "nitrile"):
            return "nitrile"
        if _has(mol, "azine"):
            return "azine"
        if _has(mol, "aldehyde"):
            return "aldehyde"
        if _has(mol, "ketone"):
            return "ketone"
        if _has(mol, "nitro"):
            return "nitro"
        if _has(mol, "tertiary_amine"):
            return "tertiary_amine"
        if _has(mol, "ether"):
            return "ether"
        return "aprotic_acceptor_other"
    return refine_family(smiles)


# --------------------------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------------------------
def stable_seed(*parts: str) -> int:
    """A bootstrap seed that depends only on the strings it is given.

    Python's builtin hash() of a string is salted per interpreter process, so seeding from it
    would make the deposited bootstrap frequencies drift by a few thousandths between runs of
    the same script.  This does not.

    What is PASSED here matters more than what it does; see `row_set_key' below.
    """
    return int(hashlib.blake2b("\x1f".join(parts).encode(), digest_size=4).hexdigest(), 16) % (
        2 ** 31)


#: The order in which the manuscript reports the axes, and therefore the order in which a reader
#: meets a row set that has several names.  It is `make_map_table_tex.AXES'.
AXIS_ORDER = ["solvent_class", "solvent_class_coarse", "solvent_family_fine",
              "solute_role", "solute_family", "solvent_class_x_solute_role", "whole_set"]


def row_set_key(strata: list[tuple[str, str, "pd.Series"]]) -> dict[tuple[str, str], dict]:
    """One seed, one identity and one interval per ROW SET, not per stratum NAME.

    THE DEFECT THIS CLOSES, 2026-08-10.  Until now the bootstrap seed was `stable_seed(label,
    unit, convention, "<axis>::<stratum>")' -- the stratum's NAME.  Ten of this map's row sets
    carry more than one name (three select the same 182 glycol-ether rows, three the same 111
    water rows, and so on), so each of those drew an INDEPENDENT 3000-draw replicate of one
    quantity under each name, and the table printed them side by side as if they were separate
    measurements.  Two referees reported the consequence on the glycol ethers, where the same
    interval printed as [+1.27,+2.83], [+1.27,+2.87] and [+1.23,+2.90]; the spread is
    Monte-Carlo error, larger than the second decimal all three were printed to
    (`results/b_insuff/glycol_ether_ci_converged.json').

    The seed is now a function of the ROW SET.  A row set's seed string is its CANONICAL NAME:
    the first of its names in AXIS_ORDER above, ties broken alphabetically.  That is fixed by
    position -- the order a reader meets the row set in -- and never by the value of an endpoint,
    and it is the same rule `make_map_table_tex' uses to decide which name a pooled interval is
    quoted under.  Two names of one row set therefore hold the IDENTICAL interval, bit for bit,
    and each record carries `row_set_id' and `row_set_n_names' so the table says so rather than
    leaving a reader to intersect it themselves.

    Row sets with a single name keep the seed they had, because their canonical name is their
    only name; the change is confined to the printings that were the defect.

    Returns {(axis, stratum): {row_set_id, row_set_canonical, row_set_n_names}}.
    """
    groups: dict[tuple[int, ...], list[tuple[str, str]]] = {}
    for sname, lab, mask in strata:
        idx = tuple(int(i) for i in np.flatnonzero(np.asarray(mask)))
        if not idx:
            continue
        groups.setdefault(idx, []).append((sname, lab))
    out: dict[tuple[str, str], dict] = {}
    for idx, names in groups.items():
        names.sort(key=lambda nl: (AXIS_ORDER.index(nl[0]) if nl[0] in AXIS_ORDER
                                   else len(AXIS_ORDER), nl[1]))
        rid = hashlib.blake2b(",".join(map(str, idx)).encode(), digest_size=4).hexdigest()
        for nl in names:
            out[nl] = {"row_set_id": rid,
                       "row_set_canonical": f"{names[0][0]}::{names[0][1]}",
                       "row_set_n_names": len(names),
                       "row_set_names": [f"{a}::{s}" for a, s in names]}
    return out


def adaptive_bins(n: int) -> int:
    return max(3, n // 10)


def pair_conditional_variance(m, pair, T, same_T_only: bool = False):
    """E[Var(m | pair)] over pairs carrying more than one row -- a direct estimate of
    B_insuff = E[Var(m | z*,T)] on that subpopulation, since z* is a function of the pair.
    With `same_T_only' the rows must additionally agree in T to 0.01 K, which removes the
    temperature spread and leaves replicate/label disagreement alone."""
    key = ([f"{p}|{round(float(t), 2)}" for p, t in zip(pair, T)] if same_T_only
           else list(map(str, pair)))
    groups = defaultdict(list)
    for k, v in zip(key, m):
        groups[k].append(v)
    tot, mass, ngroups = 0.0, 0, 0
    for vals in groups.values():
        if len(vals) < 2:
            continue
        tot += len(vals) * float(np.var(vals, ddof=1))
        mass += len(vals)
        ngroups += 1
    if mass == 0:
        return None, 0, 0
    return tot / mass, mass, ngroups


def measure(g, m, solute, solvent, pair=None, T=None, source=None,
            boot: bool = True, seed: int = 0):
    """Every number the map prints for one stratum at one unit under one convention."""
    n = len(m)
    mse = float(np.mean((m - g) ** 2))
    rec = {
        "n": int(n),
        "n_solutes": int(len(set(solute))),
        "n_solvents": int(len(set(solvent))),
        "n_pairs": int(len({f"{a}|{b}" for a, b in zip(solute, solvent)})),
        "mse": round(mse, 4),
        "var_m": round(float(np.var(m, ddof=0)), 4),
        "boundable_at_headline_cell": bool(n >= MIN_BOUNDABLE),
    }
    if source is not None:
        se = (m - g) ** 2
        by = defaultdict(float)
        for s, e in zip(source, se):
            by[str(s)] += float(e)
        top = max(by.items(), key=lambda kv: kv[1])
        rec["n_sources"] = int(len(by))
        rec["top_source"] = top[0]
        rec["top_source_share_of_stratum_squared_error"] = round(top[1] / max(se.sum(), 1e-12), 4)
    if n >= 2 * N_BINS:
        b = lotv(g, m, N_BINS, DDOF)
        b_ml = lotv(g, m, N_BINS, 0)
        rec["b_insuff_up"] = round(b, 4)
        rec["b_insuff_up_ml"] = round(b_ml, 4)
        rec["b_closure_lb"] = round(mse - b, 4)
        rec["margin"] = round(mse - 2 * b, 4)
        rec["margin_ml"] = round(mse - 2 * b_ml, 4)
        # LOTV with ddof=0 is <= Var(m) by construction; the Bessel-corrected estimate can
        # exceed it once the bins get small, and when it does the stratum is under-powered
        # at this cell rather than genuinely noise-limited.
        rec["b_insuff_exceeds_var_m"] = bool(b > rec["var_m"])
    else:
        rec["b_insuff_up"] = rec["b_insuff_up_ml"] = rec["b_closure_lb"] = None
        rec["margin"] = rec["margin_ml"] = rec["b_insuff_exceeds_var_m"] = None
    nb = adaptive_bins(n)
    if n >= 2 * nb:
        ba = lotv(g, m, nb, DDOF)
        rec["adaptive_n_bins"] = int(nb)
        rec["b_insuff_up_adaptive"] = round(ba, 4)
        rec["margin_adaptive"] = round(mse - 2 * ba, 4)
    else:
        rec["adaptive_n_bins"] = int(nb)
        rec["b_insuff_up_adaptive"] = rec["margin_adaptive"] = None
    rec["P_boot"] = rec["margin_ci90"] = None
    # A stratum defined by a single solvent (water, the ester, ...) has no solvent-level
    # cluster left to resample, so the two-way bootstrap degenerates to a one-way bootstrap
    # over solute clusters.  That is the correct thing to do there, and it is flagged.
    rec["bootstrap_reduces_to_one_way"] = bool(rec["n_solutes"] < 2 or rec["n_solvents"] < 2)
    if boot and n >= 2 * N_BINS and max(rec["n_solutes"], rec["n_solvents"]) >= 2:
        try:
            P, lo, hi = two_way_margin_boot(g, m, np.asarray(solute), np.asarray(solvent),
                                            N_BINS, DDOF, n_boot=N_BOOT, seed=seed)
            if np.isfinite(P):
                rec["P_boot"] = round(float(P), 3)
                rec["margin_ci90"] = [round(float(lo), 3), round(float(hi), 3)]
        except Exception as exc:                                    # tiny/degenerate strata
            rec["boot_error"] = type(exc).__name__
    if pair is not None:
        pv, mass, ng = pair_conditional_variance(m, pair, T)
        if pv is not None:
            rec["pair_conditional_var"] = round(pv, 4)
            rec["pair_conditional_rows"] = int(mass)
            rec["pair_conditional_groups"] = int(ng)
        pv2, mass2, ng2 = pair_conditional_variance(m, pair, T, same_T_only=True)
        if pv2 is not None:
            rec["replicate_var_same_pair_same_T"] = round(pv2, 4)
            rec["replicate_rows"] = int(mass2)
            rec["replicate_groups"] = int(ng2)
    return rec


def pair_unit(df: pd.DataFrame) -> pd.DataFrame:
    """One row per pair, the row whose T is nearest T_REF; ties broken on T then row order."""
    d = df.copy()
    d["_dT"] = (d["T_K"] - T_REF).abs()
    d["_ord"] = np.arange(len(d))
    d = d.sort_values(["pair_key", "_dT", "T_K", "_ord"])
    return d.groupby("pair_key", sort=True).head(1).sort_values("_ord").drop(
        columns=["_dT", "_ord"])


def strata_of(df: pd.DataFrame) -> list[tuple[str, str, pd.Series]]:
    """Every stratum the map reports, as (axis, label, boolean mask)."""
    out: list[tuple[str, str, pd.Series]] = []
    all_mask = pd.Series(True, index=df.index)
    out.append(("whole_set", "all", all_mask))
    for lvl, col in (("solvent_class", "solvent_class"),
                     ("solvent_class_coarse", "solvent_coarse"),
                     ("solvent_family_fine", "solvent_family"),
                     ("solute_role", "solute_role"),
                     ("solute_family", "solute_family")):
        for lab in sorted(df[col].unique()):
            out.append((lvl, lab, df[col] == lab))
    for lab in sorted(df["solvent_class"].unique()):          # axis 1 x axis 2
        for role in ("water_solute", "organic_solute"):
            mask = (df["solvent_class"] == lab) & (df["solute_role"] == role)
            if mask.sum() > 0:
                out.append(("solvent_class_x_solute_role", f"{lab} | {role}", mask))
    return out


def build(df: pd.DataFrame, conv_cols: dict[str, str], label: str) -> dict:
    """The full table for one set: every stratum x {row, pair} x {full, res}."""
    units = {"row": df, "pair": pair_unit(df)}
    table = {}
    for uname, d in units.items():
        d = d.reset_index(drop=True)
        strata = strata_of(d)
        # One draw per ROW SET, not per stratum name.  See row_set_key.
        rsk = row_set_key(strata)
        for sname, lab, mask in strata:
            sub = d[mask.values if hasattr(mask, "values") else mask]
            if len(sub) == 0:
                continue
            key = f"{sname}::{lab}"
            slot = table.setdefault(key, {"axis": sname, "stratum": lab})
            ident = rsk[(sname, lab)]
            for cname, col in conv_cols.items():
                seedv = stable_seed(label, uname, cname, ident["row_set_canonical"])
                rec = measure(sub[col].to_numpy(float), sub["m"].to_numpy(float),
                              sub["solute_smiles"].to_numpy(), sub["solvent_smiles"].to_numpy(),
                              pair=(sub["pair_key"].to_numpy() if uname == "row" else None),
                              T=(sub["T_K"].to_numpy(float) if uname == "row" else None),
                              source=sub["source_doi"].to_numpy(), seed=seedv)
                # The seed is not the whole of the repair.  A reader holding the table has to be
                # able to see that two rows are one row set without intersecting them, so the
                # identity travels in the record and therefore in every deposited column.
                rec["row_set_id"] = ident["row_set_id"]
                rec["row_set_canonical"] = ident["row_set_canonical"]
                rec["row_set_n_names"] = ident["row_set_n_names"]
                rec["row_set_other_names"] = "|".join(
                    n for n in ident["row_set_names"] if n != f"{sname}::{lab}")
                rec["interval_is_a_restatement"] = bool(
                    ident["row_set_canonical"] != f"{sname}::{lab}")
                se = float(np.sum((sub["m"] - sub[col]) ** 2))
                se_tot = float(np.sum((d["m"] - d[col]) ** 2))
                rec["share_of_squared_error"] = round(se / se_tot, 4)
                rec["share_of_rows"] = round(len(sub) / len(d), 4)
                slot[f"{uname}::{cname}"] = rec
    return table


def loo_curves(d: pd.DataFrame, col: str, by: str) -> list[dict]:
    """Leave-one-<by>-out at the headline cell, as a curve sorted by resulting margin."""
    m = d["m"].to_numpy(float)
    g = d[col].to_numpy(float)
    su = d["solute_smiles"].to_numpy()
    sv = d["solvent_smiles"].to_numpy()
    keys = d[by].to_numpy()
    base_mse = float(np.mean((m - g) ** 2))
    base = base_mse - 2 * lotv(g, m, N_BINS, DDOF)
    rows = []
    for k in sorted(set(keys)):
        keep = keys != k
        if keep.sum() < 2 * N_BINS:
            continue
        mm, gg = m[keep], g[keep]
        mse = float(np.mean((mm - gg) ** 2))
        b = lotv(gg, mm, N_BINS, DDOF)
        drop = ~keep
        rows.append({
            "left_out": str(k), "n_removed": int(drop.sum()), "n_remaining": int(keep.sum()),
            "share_of_squared_error_removed": round(
                float(np.sum((m[drop] - g[drop]) ** 2)) / float(np.sum((m - g) ** 2)), 4),
            "mse": round(mse, 4), "b_insuff_up": round(b, 4),
            "margin": round(mse - 2 * b, 4),
            "delta_margin": round(mse - 2 * b - base, 4),
            "n_solutes_remaining": int(len(set(su[keep]))),
            "n_solvents_remaining": int(len(set(sv[keep]))),
        })
    return sorted(rows, key=lambda r: r["margin"])


# --------------------------------------------------------------------------------------------
# admissibility -- the one rule, applied to every stratum alike
# --------------------------------------------------------------------------------------------
ADMISSIBILITY_RULE = (
    "A stratum may be STATED AS A FINDING only if it is (a) BOUNDABLE at the fixed headline "
    f"cell (n >= {MIN_BOUNDABLE}, so each of the {N_BINS} equal-count bins holds at least five "
    "rows) and (b) ROBUST TO LEAVE-ONE-SOURCE-OUT: its margin keeps its sign when any single "
    "source publication contributing to it is deleted. A stratum drawing on one publication "
    "fails (b) by non-testability -- there is no deletion to perform, so the sign was never put "
    f"at risk. A deletion leaving fewer than {2 * N_BINS} rows leaves the fixed cell undefined, "
    "so the sign is unverifiable and the stratum fails (b) as well. Everything else is reported "
    "in the map, with its n, its sources, its margin, its interval and the reason, and is not "
    "stated as a finding."
)

ONE_SIDEDNESS = (
    "The rule tests whether a number is stable, not what it means. B_insuff is bounded ABOVE "
    "and B_clos BELOW, so a positive margin certifies B_clos > 0 while a non-positive margin is "
    "failure to separate and NOT a certified reversal -- that would need a lower bound on "
    "B_insuff. An admissible stratum with a non-positive margin therefore licenses nothing."
)

SMALL_N_BIAS = (
    "The Bessel within-bin variance inflates as the bins empty, so a deletion leaving a small "
    "remainder biases B_insuff^up up and the margin down. For a positive-margin stratum that "
    "makes leave-one-source-out conservative; for a non-positive one it makes it "
    "ANTI-conservative, and a robustly negative sign can be the estimator thinning rather than "
    "the chemistry. `loso_n_leaving_unboundable' counts the deletions where this applies and "
    "the strict variant of (b) refuses them."
)


def source_deletion_curve(sub: pd.DataFrame, col: str, base: float | None) -> list[dict]:
    """Leave-one-SOURCE-PUBLICATION-out for ONE stratum, at the fixed headline cell."""
    m = sub["m"].to_numpy(float)
    g = sub[col].to_numpy(float)
    src = sub["source_doi"].astype(str).to_numpy()
    se = (m - g) ** 2
    tot = float(se.sum())
    out = []
    for s in sorted(set(src)):
        drop = src == s
        keep = ~drop
        rec = {
            "left_out": s,
            "n_removed": int(drop.sum()),
            "n_remaining": int(keep.sum()),
            "share_of_stratum_squared_error_removed": round(
                float(se[drop].sum()) / max(tot, 1e-12), 4),
            "remainder_still_boundable": bool(keep.sum() >= MIN_BOUNDABLE),
        }
        if keep.sum() >= 2 * N_BINS:
            mm, gg = m[keep], g[keep]
            mse = float(np.mean((mm - gg) ** 2))
            b = lotv(gg, mm, N_BINS, DDOF)
            rec["mse"] = round(mse, 4)
            rec["b_insuff_up"] = round(b, 4)
            rec["margin"] = round(mse - 2 * b, 4)
            rec["delta_margin"] = None if base is None else round(rec["margin"] - base, 4)
        else:
            rec["mse"] = rec["b_insuff_up"] = rec["margin"] = rec["delta_margin"] = None
        out.append(rec)
    return out


def admissibility(df: pd.DataFrame, conv_cols: dict[str, str], table: dict,
                  setname: str) -> tuple[list[dict], dict]:
    """Both tests, for every stratum x {row, pair} x {full, res}, plus the rollup over cells."""
    units = {"row": df, "pair": pair_unit(df)}
    recs: list[dict] = []
    curves: dict[str, list[dict]] = {}
    for uname, d in units.items():
        d = d.reset_index(drop=True)
        for sname, lab, mask in strata_of(d):
            sub = d[mask.values if hasattr(mask, "values") else mask]
            if len(sub) == 0:
                continue
            key = f"{sname}::{lab}"
            for cname, col in conv_cols.items():
                rec = table[key][f"{uname}::{cname}"]
                base = rec["margin"]
                curve = source_deletion_curve(sub, col, base)
                curves[f"{setname}|{key}|{uname}|{cname}"] = curve
                n_src = len(curve)
                ev = [c for c in curve if c["margin"] is not None]
                bd = [c for c in ev if c["remainder_still_boundable"]]
                sgn = None if base is None else (1.0 if base > 0 else -1.0)
                if base is None:
                    ok_b = strict_b = False
                    why = f"the fixed cell is undefined at n={rec['n']}"
                elif n_src < 2:
                    ok_b = strict_b = False
                    why = (f"one source publication ({curve[0]['left_out']}): "
                           "leave-one-source-out cannot be run, so the sign was never tested")
                elif len(ev) < n_src:
                    ok_b = strict_b = False
                    bad = [c["left_out"] for c in curve if c["margin"] is None]
                    why = (f"{len(bad)} of {n_src} deletions leave fewer than {2 * N_BINS} rows "
                           f"and the fixed cell is then undefined ({', '.join(bad)}), so the "
                           "sign is not verifiable")
                else:
                    flips = [c for c in ev if c["margin"] * sgn <= 0]
                    ok_b = not flips
                    strict_b = ok_b and len(bd) == n_src
                    if flips:
                        why = "sign does not survive deletion of " + "; ".join(
                            f"{c['left_out']} ({base:+.3f} -> {c['margin']:+.3f})"
                            for c in flips)
                    elif not strict_b:
                        why = (f"sign holds, but {n_src - len(bd)} of {n_src} deletions leave "
                               f"n < {MIN_BOUNDABLE}: passes (b) and fails its strict variant")
                    else:
                        why = ""
                ok_a = bool(rec["boundable_at_headline_cell"])
                why_a = "" if ok_a else f"not boundable: n={rec['n']} < {MIN_BOUNDABLE}"
                worst = (min(ev, key=lambda c: c["margin"] * sgn) if (ev and sgn) else None)
                adm = bool(ok_a and ok_b)
                direction = ("no estimate" if base is None else
                             "positive" if base > 0 else "non-positive")
                if not adm:
                    lic = "nothing: reported in the map, not stated as a finding"
                elif direction == "positive":
                    lic = ("B_clos > 0 in this stratum: the closure's own error exceeds what "
                           "input insufficiency can account for")
                else:
                    lic = ("nothing: a non-positive margin is failure to separate, not a "
                           "certified reversal (that needs a LOWER bound on B_insuff)")
                reason = "; ".join(x for x in (why_a, why if not (ok_a and ok_b) else "") if x)
                recs.append({
                    "set": setname, "axis": sname, "stratum": lab, "unit": uname,
                    "convention": cname,
                    "row_set_id": rec.get("row_set_id"),
                    "row_set_canonical": rec.get("row_set_canonical"),
                    "row_set_n_names": rec.get("row_set_n_names"),
                    "interval_is_a_restatement": rec.get("interval_is_a_restatement"),
                    "n": rec["n"], "n_pairs": rec["n_pairs"], "n_solutes": rec["n_solutes"],
                    "n_solvents": rec["n_solvents"],
                    "n_sources": n_src,
                    "sources": "|".join(c["left_out"] for c in curve),
                    "top_source": rec.get("top_source"),
                    "top_source_share_of_stratum_squared_error": rec.get(
                        "top_source_share_of_stratum_squared_error"),
                    "share_of_squared_error": rec.get("share_of_squared_error"),
                    "mse": rec["mse"], "b_insuff_up": rec["b_insuff_up"], "margin": base,
                    "P_boot": rec["P_boot"],
                    "margin_ci90_lo": (rec["margin_ci90"] or [None, None])[0],
                    "margin_ci90_hi": (rec["margin_ci90"] or [None, None])[1],
                    "ci90_excludes_zero": (None if rec["margin_ci90"] is None else
                                           bool(rec["margin_ci90"][0] > 0
                                                or rec["margin_ci90"][1] < 0)),
                    "test_a_boundable": ok_a,
                    "loso_testable": bool(n_src >= 2),
                    "loso_n_deletions": n_src,
                    "loso_n_undefined": n_src - len(ev),
                    "loso_n_leaving_unboundable": n_src - len(bd),
                    "loso_margin_min": min((c["margin"] for c in ev), default=None),
                    "loso_margin_max": max((c["margin"] for c in ev), default=None),
                    "loso_worst_source": worst["left_out"] if worst else None,
                    "loso_worst_margin": worst["margin"] if worst else None,
                    "loso_worst_n_remaining": worst["n_remaining"] if worst else None,
                    "test_b_sign_survives_loso": ok_b,
                    "test_b_strict_remainder_boundable": strict_b,
                    "admissible_this_cell": adm,
                    "admissible_this_cell_strict": bool(ok_a and strict_b),
                    "direction": direction,
                    "licenses": lic,
                    "reason_not_admissible": reason,
                })
    roll: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in recs:
        roll[(r["axis"], r["stratum"])].append(r)
    for group in roll.values():
        n_cells = len(group)
        n_adm = sum(r["admissible_this_cell"] for r in group)
        n_str = sum(r["admissible_this_cell_strict"] for r in group)
        for r in group:
            r["cells_reported"] = n_cells
            r["cells_admissible"] = n_adm
            r["cells_admissible_strict"] = n_str
            r["admissible_in_every_cell"] = bool(n_adm == n_cells)
            r["admissible_in_every_cell_strict"] = bool(n_str == n_cells)
    return recs, curves


def overlap_table(df: pd.DataFrame) -> list[dict]:
    """Intersect every pair of strata, in rows and in pairs.  Both axes at every level."""
    d = df.reset_index(drop=True)
    sets: dict[tuple[str, str], tuple[set, set]] = {}
    for sname, lab, mask in strata_of(d):
        mm = mask.values if hasattr(mask, "values") else mask
        sets[(sname, lab)] = (set(np.flatnonzero(np.asarray(mm)).tolist()),
                              set(d.loc[mm, "pair_key"]))
    keys = list(sets)
    out = []
    for i, ka in enumerate(keys):
        ra, pa = sets[ka]
        for kb in keys[i + 1:]:
            rb, pb = sets[kb]
            sr, sp = ra & rb, pa & pb
            if not sr:
                rel = "disjoint"
            elif ra == rb:
                rel = "identical"
            elif ra < rb:
                rel = "a_inside_b"
            elif rb < ra:
                rel = "b_inside_a"
            else:
                rel = "partial"
            out.append({
                "axis_a": ka[0], "stratum_a": ka[1], "axis_b": kb[0], "stratum_b": kb[1],
                "same_axis": bool(ka[0] == kb[0]),
                "rows_a": len(ra), "rows_b": len(rb), "rows_shared": len(sr),
                "pairs_a": len(pa), "pairs_b": len(pb), "pairs_shared": len(sp),
                "shared_share_of_a": round(len(sr) / len(ra), 4),
                "shared_share_of_b": round(len(sr) / len(rb), 4),
                "relation": rel,
                "double_counts_if_cited_as_separate_evidence": bool(sr),
            })
    return out


def split_margins(df: pd.DataFrame, conv_cols: dict[str, str],
                  focus: list[tuple[str, str]]) -> list[dict]:
    """For overlapping strata a reader might cite together, the margin on EACH SIDE of the
    overlap at the same fixed cell: the measurement of whether they are independent evidence."""
    d = df.reset_index(drop=True)
    sets = {}
    for sname, lab, mask in strata_of(d):
        if (sname, lab) in focus:
            sets[(sname, lab)] = np.asarray(
                mask.values if hasattr(mask, "values") else mask, dtype=bool)
    keys = [k for k in focus if k in sets]

    def at(idx: np.ndarray, col: str):
        """The side of an overlap, carrying its own admissibility so it can be quoted."""
        sub = d.loc[idx]
        rec = {"n": int(idx.sum()), "n_pairs": int(sub["pair_key"].nunique()),
               "n_sources": int(sub["source_doi"].nunique()),
               "boundable": bool(idx.sum() >= MIN_BOUNDABLE),
               "mse": None, "b_insuff_up": None, "margin": None,
               "loso_margin_min": None, "loso_margin_max": None, "loso_worst_source": None,
               "admissible": False}
        if idx.sum() < 2 * N_BINS:
            return rec
        m = sub["m"].to_numpy(float)
        g = sub[col].to_numpy(float)
        mse = float(np.mean((m - g) ** 2))
        b = lotv(g, m, N_BINS, DDOF)
        rec["mse"] = round(mse, 4)
        rec["b_insuff_up"] = round(b, 4)
        rec["margin"] = round(mse - 2 * b, 4)
        curve = source_deletion_curve(sub, col, rec["margin"])
        ev = [c for c in curve if c["margin"] is not None]
        sgn = 1.0 if rec["margin"] > 0 else -1.0
        if ev:
            worst = min(ev, key=lambda c: c["margin"] * sgn)
            rec["loso_margin_min"] = min(c["margin"] for c in ev)
            rec["loso_margin_max"] = max(c["margin"] for c in ev)
            rec["loso_worst_source"] = worst["left_out"]
        rec["admissible"] = bool(rec["boundable"] and len(curve) >= 2 and len(ev) == len(curve)
                                 and all(c["margin"] * sgn > 0 for c in ev))
        return rec

    out = []
    for i, ka in enumerate(keys):
        for kb in keys[i + 1:]:
            a, b = sets[ka], sets[kb]
            if not (a & b).any():
                continue
            row = {"axis_a": ka[0], "stratum_a": ka[1], "axis_b": kb[0], "stratum_b": kb[1],
                   "rows_shared": int((a & b).sum()),
                   "pairs_shared": int(d.loc[a & b, "pair_key"].nunique())}
            for cname, col in conv_cols.items():
                row[f"A_{cname}"] = at(a, col)
                row[f"B_{cname}"] = at(b, col)
                row[f"A_minus_B_{cname}"] = at(a & ~b, col)
                row[f"B_minus_A_{cname}"] = at(b & ~a, col)
                row[f"A_and_B_{cname}"] = at(a & b, col)
            out.append(row)
    return out


def random_partition_null(d: pd.DataFrame, col: str, sizes: list[int], seed: int = 0) -> dict:
    """Is the structural claim -- MSE varies across strata, B_insuff does not -- a property of
    THIS partition, or would any partition of the same block sizes do it?  Random partitions of
    identical block sizes, same estimator cell, same boundability filter."""
    rng = np.random.default_rng(seed)
    m = d["m"].to_numpy(float)
    g = d[col].to_numpy(float)
    n = len(m)
    keep = [i for i, s in enumerate(sizes) if s >= MIN_BOUNDABLE]
    r_mse, r_b, ratio = [], [], []
    for _ in range(N_NULL):
        perm = rng.permutation(n)
        start, mses, bs = 0, [], []
        for i, s in enumerate(sizes):
            idx = perm[start:start + s]
            start += s
            if i not in keep:
                continue
            mses.append(float(np.mean((m[idx] - g[idx]) ** 2)))
            bs.append(lotv(g[idx], m[idx], N_BINS, DDOF))
        r_mse.append(max(mses) - min(mses))
        r_b.append(max(bs) - min(bs))
        ratio.append((max(mses) - min(mses)) / max(max(bs) - min(bs), 1e-9))
    return {"range_mse": r_mse, "range_b": r_b, "ratio": ratio}


def prepare(path: Path, kind: str) -> tuple[pd.DataFrame, dict[str, str]]:
    df = pd.read_csv(path)
    if kind == "broad":
        conv = {"full": "g_2002_full", "res": "g_2002_res"}
        df = df.rename(columns={"m_ln_gamma_inf": "m"})
    else:
        conv = {"full": "g_2002_full_UD", "res": "g_2002_res_UD"}
        df = df.rename(columns={"solute_key": "solute_smiles", "solvent_key": "solvent_smiles"})
    df["pair_key"] = df["solute_smiles"].astype(str) + "|" + df["solvent_smiles"].astype(str)
    smap = {s: classify_solvent(s) for s in df["solvent_smiles"].unique()}
    fmap = {s: refine_family(s) for s in df["solvent_smiles"].unique()}
    umap = {s: classify_solute_family(s) for s in df["solute_smiles"].unique()}
    df["solvent_class"] = df["solvent_smiles"].map(smap)
    df["solvent_coarse"] = df["solvent_class"].map(COARSE)
    df["solvent_family"] = df["solvent_smiles"].map(fmap)
    df["solute_family"] = df["solute_smiles"].map(umap)
    df["solute_role"] = np.where(df["solute_family"] == "water", "water_solute", "organic_solute")
    assert "unclassified" not in set(smap.values()), sorted(
        s for s, c in smap.items() if c == "unclassified")
    return df, conv


def flatten(table: dict, setname: str) -> list[dict]:
    rows = []
    for key, slot in table.items():
        for cell, rec in slot.items():
            if not isinstance(rec, dict):
                continue
            unit, conv = cell.split("::")
            rows.append({"set": setname, "axis": slot["axis"], "stratum": slot["stratum"],
                         "unit": unit, "convention": conv,
                         **{k: v for k, v in rec.items() if not isinstance(v, list)},
                         "margin_ci90_lo": (rec["margin_ci90"] or [None, None])[0],
                         "margin_ci90_hi": (rec["margin_ci90"] or [None, None])[1]})
    return rows


def main() -> int:
    out: dict = {
        "what_this_replaces": (
            "the aggregate separation margin on the broad IDAC set, reported as a single "
            "verdict; replaced by the margin as a map over chemical strata"),
        "estimator_cell_held_fixed": {"n_bins": N_BINS, "within_bin_variance": "Bessel (ddof=1)",
                                      "boundable_iff_n_at_least": MIN_BOUNDABLE,
                                      "adaptive_rule_also_reported": "max(3, n // 10)",
                                      "bootstrap": "two-way solute x solvent cluster, "
                                                   f"{N_BOOT} draws, 90% interval"},
        "rule": {
            "docstring": __doc__,
            "axis_1_input": "solvent SMILES only",
            "axis_2_input": "whether the solute is water",
            "classifier_is_pure_function_of_structure": True,
        },
    }

    broad, conv = prepare(BROAD, "broad")
    corner, cconv = prepare(CORNER, "corner")

    # ------------------------------------------------------------------ the rule, spelled out
    inv = []
    for s in sorted(broad["solvent_smiles"].unique()):
        sub = broad[broad["solvent_smiles"] == s]
        inv.append({"solvent_smiles": s, "class": classify_solvent(s), "family": refine_family(s),
                    "coarse": COARSE[classify_solvent(s)], "n_rows": int(len(sub)),
                    "n_pairs": int(sub["pair_key"].nunique())})
    out["solvent_inventory_broad"] = inv
    out["solvent_inventory_corner"] = [
        {"solvent_smiles": s, "class": classify_solvent(s), "family": refine_family(s),
         "n_rows": int((corner["solvent_smiles"] == s).sum())}
        for s in sorted(corner["solvent_smiles"].unique())]
    print("[rule] solvent classes on the broad set:")
    for k, v in sorted(Counter(broad["solvent_class"]).items(), key=lambda kv: -kv[1]):
        print(f"        {k:24s} {v:4d} rows")
    print(f"[rule] water-as-solute rows: {(broad.solute_role == 'water_solute').sum()}")

    # cross-tab, so the confound between axis 1 and axis 2 is on the record, not hidden
    ct = pd.crosstab(broad["solvent_class"], broad["solute_role"])
    out["crosstab_solvent_class_x_solute_role"] = json.loads(ct.to_json(orient="index"))

    # ------------------------------------------------- what the editor recomputed, reproduced
    def marg(d, col):
        m = d["m"].to_numpy(float)
        g = d[col].to_numpy(float)
        mse = float(np.mean((m - g) ** 2))
        return round(mse - 2 * lotv(g, m, N_BINS, DDOF), 4), int(len(m))

    bp = pair_unit(broad)
    repro = {}
    for uname, d in (("row", broad), ("pair", bp)):
        c1 = d["solvent_class"] != "glycol_ether"
        c2 = d["solute_role"] != "water_solute"
        for cname, col in conv.items():
            repro[f"{uname}/{cname}"] = {
                "full_set": marg(d, col),
                "minus_glycol_ethers": marg(d[c1], col),
                "minus_water_as_solute": marg(d[c2], col),
                "minus_both": marg(d[c1 & c2], col),
            }
    out["reproduction_of_the_compounded_cuts"] = repro
    print("[repro]", json.dumps(repro["row/res"]), json.dumps(repro["pair/res"]))

    # ------------------------------------------------------------------------------- the map
    print("[map] broad set ...", flush=True)
    broad_table = build(broad, conv, "broad")
    out["map_broad"] = broad_table
    print("[map] corner set ...", flush=True)
    corner_table = build(corner, cconv, "corner")
    out["map_corner"] = corner_table

    # ------------------------------------------------------------------------- admissibility
    print("[admissibility] applying the rule to every stratum ...", flush=True)
    adm_rows, adm_curves = [], {}
    for setname, dset, cmap, tbl in (("broad_477", broad, conv, broad_table),
                                     ("corner_60", corner, cconv, corner_table)):
        r, c = admissibility(dset, cmap, tbl, setname)
        adm_rows += r
        adm_curves.update(c)
        # the map itself marks each stratum admissible or not, with the reason
        for rec in r:
            cell = tbl[f"{rec['axis']}::{rec['stratum']}"][f"{rec['unit']}::{rec['convention']}"]
            for k in ("n_sources", "test_a_boundable", "loso_testable", "loso_n_deletions",
                      "loso_n_undefined", "loso_n_leaving_unboundable", "loso_margin_min",
                      "loso_margin_max", "loso_worst_source", "loso_worst_margin",
                      "test_b_sign_survives_loso", "test_b_strict_remainder_boundable",
                      "admissible_this_cell", "admissible_this_cell_strict",
                      "cells_admissible", "cells_reported", "admissible_in_every_cell",
                      "admissible_in_every_cell_strict", "ci90_excludes_zero", "direction",
                      "licenses", "reason_not_admissible"):
                cell[k] = rec[k]

    adm = pd.DataFrame(adm_rows)
    broad_adm = adm[adm["set"] == "broad_477"]
    passing = sorted({(r.axis, r.stratum) for r in broad_adm.itertuples()
                      if r.admissible_in_every_cell})
    passing_pos = sorted({(r.axis, r.stratum) for r in broad_adm.itertuples()
                          if r.admissible_in_every_cell and r.direction == "positive"})
    focus = sorted({(r.axis, r.stratum) for r in broad_adm.itertuples()
                    if r.cells_admissible > 0
                    or r.axis in ("solvent_class", "solute_role", "whole_set")})
    ovl = overlap_table(broad)
    spl = split_margins(broad, conv, focus)

    out["admissibility"] = {
        "rule": ADMISSIBILITY_RULE,
        "one_sidedness": ONE_SIDEDNESS,
        "small_n_bias_of_the_deletion_test": SMALL_N_BIAS,
        "cells_are_unit_x_convention": ["row::full", "row::res", "pair::full", "pair::res"],
        "verdict_requires": "both tests, in every reported unit x convention cell",
        "admissible_in_every_cell_broad": [f"{a}::{s}" for a, s in passing],
        "admissible_in_every_cell_and_positive_broad": [f"{a}::{s}" for a, s in passing_pos],
        "admissible_in_every_cell_corner": sorted(
            {f"{r.axis}::{r.stratum}" for r in adm[adm['set'] == 'corner_60'].itertuples()
             if r.admissible_in_every_cell}),
        "n_strata_broad": int(broad_adm.groupby(["axis", "stratum"]).ngroups),
        "n_strata_admissible_at_headline_cell_only": int(
            broad_adm[(broad_adm.unit == "row") & (broad_adm.convention == "res")]
            ["admissible_this_cell"].sum()),
        "per_stratum_marks": "every stratum record above carries admissible_this_cell, "
                             "admissible_in_every_cell and reason_not_admissible",
        "full_table": str(ADM_CSV.relative_to(ROOT)),
        "deletion_curves_and_overlap": str(ADM_JSON.relative_to(ROOT)),
    }
    out["stratum_overlap"] = {
        "why": "two strata can be the same rows twice; an axis is not an independent axis",
        "n_pairs_examined": len(ovl),
        "n_pairs_with_nonzero_overlap": sum(1 for r in ovl if r["rows_shared"] > 0),
        "table": str(OVERLAP_CSV.relative_to(ROOT)),
        "margins_on_each_side_of_the_overlap": str(ADM_JSON.relative_to(ROOT)),
    }

    # Identical rows under several names is a stronger statement than overlap, and it is the one
    # the bootstrap was getting wrong: see row_set_key.
    rs: dict[str, dict] = {}
    for slot in broad_table.values():
        r = slot.get("row::res")
        if r is None or "row_set_id" not in r:
            continue
        e = rs.setdefault(r["row_set_id"], {"row_set_id": r["row_set_id"], "n": r["n"],
                                            "canonical": r["row_set_canonical"], "names": []})
        e["names"].append(f"{slot['axis']}::{slot['stratum']}")
    multi = sorted((e for e in rs.values() if len(e["names"]) > 1), key=lambda e: -e["n"])
    out["row_sets_under_several_names"] = {
        "why": "the bootstrap seed was derived from the stratum NAME until 2026-08-10, so a row "
               "set carrying several names drew an independent replicate under each and the map "
               "printed them side by side as if they were separate measurements. The seed is now "
               "a function of the ROW SET (its canonical name, the first of its names in the "
               "manuscript's axis order), so every name of one row set holds the identical "
               "interval, and every record carries row_set_id, row_set_n_names and "
               "interval_is_a_restatement so the table says which rows are a restatement.",
        "n_row_sets_row_unit": len(rs),
        "n_row_sets_with_more_than_one_name": len(multi),
        "n_duplicate_names": sum(len(e["names"]) - 1 for e in multi),
        "row_sets": multi,
        "printing_precision_of_these_intervals": "results/b_insuff/map_ci_precision.json",
    }
    print(f"[row sets] {len(multi)} of {len(rs)} row sets carry more than one name "
          f"({sum(len(e['names']) - 1 for e in multi)} duplicate names); one interval each")
    adm_detail = {
        "per_stratum": adm_rows,
        "leave_one_source_out_curves": adm_curves,
        "pairs_with_nonzero_overlap": [r for r in ovl if r["rows_shared"] > 0],
        "margins_on_each_side_of_the_overlap": spl,
    }

    # ------------------------------------------------------------ diagnostics: B_insuff range
    diag = {}
    for uname in ("row", "pair"):
        for cname in conv:
            for scope, filt in (("boundable_only", lambda r: r["boundable_at_headline_cell"]),
                                ("every_class_with_an_estimate", lambda r: True)):
                vals = [(slot["stratum"], slot[f"{uname}::{cname}"]["b_insuff_up"],
                         slot[f"{uname}::{cname}"]["mse"], slot[f"{uname}::{cname}"]["n"],
                         slot[f"{uname}::{cname}"]["b_insuff_up_ml"])
                        for slot in broad_table.values()
                        if slot["axis"] == "solvent_class"
                        and f"{uname}::{cname}" in slot
                        and slot[f"{uname}::{cname}"]["b_insuff_up"] is not None
                        and filt(slot[f"{uname}::{cname}"])]
                if not vals:
                    continue
                bs = [v[1] for v in vals]
                ms = [v[2] for v in vals]
                diag[f"{uname}/{cname}/{scope}"] = {
                    "n_solvent_classes": len(vals),
                    "b_insuff_min": min(bs), "b_insuff_max": max(bs),
                    "b_insuff_ratio_max_over_min": round(max(bs) / max(min(bs), 1e-9), 2),
                    "mse_min": min(ms), "mse_max": max(ms),
                    "mse_ratio_max_over_min": round(max(ms) / max(min(ms), 1e-9), 2),
                    "per_class": [{"stratum": v[0], "n": v[3], "b_insuff_up": v[1],
                                   "b_insuff_up_ml": v[4], "mse": v[2]}
                                  for v in sorted(vals, key=lambda v: v[2])],
                }
    out["b_insuff_range_across_solvent_classes"] = diag

    # what bounds B_insuff above and below
    bnd = {}
    for cname, col in conv.items():
        rows = []
        for slot in broad_table.values():
            if slot["axis"] != "solvent_class":
                continue
            r = slot.get(f"row::{cname}")
            if r is None or r["b_insuff_up"] is None:
                continue
            rows.append({"stratum": slot["stratum"], "n": r["n"],
                         "upper_reference_var_m": r["var_m"],
                         "b_insuff_up": r["b_insuff_up"],
                         "b_insuff_up_ml": r["b_insuff_up_ml"],
                         "b_insuff_exceeds_var_m": r["b_insuff_exceeds_var_m"],
                         "lower_reference_pair_conditional_var": r.get("pair_conditional_var"),
                         "lower_reference_replicate_var_same_T": r.get(
                             "replicate_var_same_pair_same_T"),
                         "boundable": r["boundable_at_headline_cell"]})
        bnd[cname] = rows
    out["what_bounds_b_insuff"] = {
        "above": "the within-stratum label variance Var(m).  LOTV on one bin IS Var(m) and "
                 "refining the bins can only lower it, so with the maximum-likelihood "
                 "within-bin variance B_insuff^up <= Var(m) identically.  The Bessel-corrected "
                 "estimate the manuscript headlines can exceed Var(m) once the bins hold only "
                 "a few rows; `b_insuff_exceeds_var_m' flags exactly that, and it fires only "
                 "on strata already flagged as not boundable at this cell.",
        "below": "replicate/label disagreement.  z* is a deterministic function of the pair, so "
                 "E[Var(m | pair, T)] IS B_insuff on the rows that repeat.  No two rows of the "
                 "477 share a pair AND a temperature, so that quantity is not measurable here; "
                 "the coarser E[Var(m | pair)], which additionally absorbs the within-pair "
                 "temperature spread, is 0.0003-0.08 across strata -- one to two orders of "
                 "magnitude below the LOTV bound.  The level of B_insuff^up in this set is "
                 "therefore set by within-bin heterogeneity of the binning statistic, not by "
                 "label noise, which is why it is so nearly stratum-independent: every stratum "
                 "is binned into 8 quantile bins of a scalar and the residual spread of m "
                 "inside such a bin is a property of the estimator, not of the chemistry.",
        "per_class": bnd,
    }

    # ------------------------------------------------- diagnostics: squared-error concentration
    conc = {}
    for uname, d in (("row", broad), ("pair", bp)):
        for cname, col in conv.items():
            se = ((d["m"] - d[col]) ** 2).to_numpy(float)
            tot = float(se.sum())
            block = {}
            for axis in ("solvent_class", "solute_role", "source_doi", "solvent_family",
                         "solute_family"):
                shares = []
                for lab in sorted(d[axis].unique()):
                    msk = (d[axis] == lab).to_numpy()
                    shares.append({"stratum": str(lab), "n": int(msk.sum()),
                                   "share_of_rows": round(float(msk.sum()) / len(d), 4),
                                   "share_of_squared_error": round(float(se[msk].sum()) / tot, 4),
                                   "mse": round(float(se[msk].mean()), 4)})
                block[axis] = sorted(shares, key=lambda r: -r["share_of_squared_error"])
            conc[f"{uname}/{cname}"] = block
    out["squared_error_shares"] = conc

    # --------------------------------------------------------- diagnostics: leave-one-out curves
    head_col = conv["res"]
    out["leave_one_out_headline_cell"] = {
        "definition": "row unit, deployed residual-only convention, 8 bins, Bessel",
        "baseline_margin": marg(broad, head_col)[0],
        "leave_one_source_out": loo_curves(broad, head_col, "source_doi"),
        "leave_one_pair_out": loo_curves(broad, head_col, "pair_key"),
        "leave_one_solvent_class_out": loo_curves(broad, head_col, "solvent_class"),
    }
    out["leave_one_out_full_convention"] = {
        "baseline_margin": marg(broad, conv["full"])[0],
        "leave_one_source_out": loo_curves(broad, conv["full"], "source_doi"),
    }
    loso = out["leave_one_out_headline_cell"]["leave_one_source_out"]
    print(f"[loso] worst {loso[0]['left_out']} -> {loso[0]['margin']:+.3f}; "
          f"best {loso[-1]['left_out']} -> {loso[-1]['margin']:+.3f}")

    # per-stratum leave-one-source-out: which map cells are themselves carried by one paper
    per_strat = {}
    for cname, col in conv.items():
        block = {}
        for lab in sorted(broad["solvent_class"].unique()):
            sub = broad[broad["solvent_class"] == lab]
            if len(sub) < 2 * N_BINS or sub["source_doi"].nunique() < 2:
                continue
            block[lab] = loo_curves(sub.reset_index(drop=True), col, "source_doi")
        for role in ("water_solute", "organic_solute"):
            sub = broad[broad["solute_role"] == role]
            if len(sub) < 2 * N_BINS or sub["source_doi"].nunique() < 2:
                continue
            block[role] = loo_curves(sub.reset_index(drop=True), col, "source_doi")
        per_strat[cname] = block
    out["per_stratum_leave_one_source_out"] = per_strat

    # does the map's verdict for a stratum survive the unit and the convention?
    stab = []
    for slot in broad_table.values():
        if slot["axis"] not in ("solvent_class", "solute_role", "solvent_class_coarse"):
            continue
        cells = {c: slot[c] for c in ("row::full", "row::res", "pair::full", "pair::res")
                 if c in slot and slot[c]["margin"] is not None}
        if not cells:
            continue
        signs = {c: (r["margin"] > 0) for c, r in cells.items()}
        stab.append({
            "axis": slot["axis"], "stratum": slot["stratum"],
            "cells_available": len(cells),
            "margins": {c: r["margin"] for c, r in cells.items()},
            "P_boot": {c: r["P_boot"] for c, r in cells.items()},
            "n": {c: r["n"] for c, r in cells.items()},
            "boundable": {c: r["boundable_at_headline_cell"] for c, r in cells.items()},
            "sign_agrees_across_all_available_cells": len(set(signs.values())) == 1,
            "verdict": ("binds" if all(signs.values()) else
                        "does not bind" if not any(signs.values()) else "unstable"),
            "verdict_at_90pc_confidence": (
                "binds" if all((r["P_boot"] or 0) >= 0.9 for r in cells.values()) else
                "not established"),
        })
    out["verdict_stability"] = sorted(stab, key=lambda r: (r["axis"], r["stratum"]))

    # corner leave-one-out
    out["corner_leave_one_out"] = {
        cname: {"baseline_margin": marg(corner, col)[0],
                "leave_one_source_out": loo_curves(corner, col, "source_doi"),
                "leave_one_pair_out": loo_curves(corner, col, "pair_key"),
                "leave_one_solvent_class_out": loo_curves(corner, col, "solvent_class")}
        for cname, col in cconv.items()}

    # ------------------------------------------------------- diagnostics: random-partition null
    sizes = [int(v) for v in broad["solvent_class"].value_counts().sort_index().to_numpy()]
    null = {}
    for cname, col in conv.items():
        obs_vals = [(slot["stratum"], slot[f"row::{cname}"]["mse"],
                     slot[f"row::{cname}"]["b_insuff_up"])
                    for slot in broad_table.values()
                    if slot["axis"] == "solvent_class"
                    and slot[f"row::{cname}"]["boundable_at_headline_cell"]]
        obs_mse = max(v[1] for v in obs_vals) - min(v[1] for v in obs_vals)
        obs_b = max(v[2] for v in obs_vals) - min(v[2] for v in obs_vals)
        nl = random_partition_null(broad, col, sizes)
        null[cname] = {
            "observed_range_mse": round(obs_mse, 4),
            "observed_range_b_insuff": round(obs_b, 4),
            "observed_ratio": round(obs_mse / max(obs_b, 1e-9), 2),
            "null_median_range_mse": round(float(np.median(nl["range_mse"])), 4),
            "null_median_range_b_insuff": round(float(np.median(nl["range_b"])), 4),
            "null_median_ratio": round(float(np.median(nl["ratio"])), 2),
            "p_range_mse_at_least_observed": round(
                float(np.mean(np.asarray(nl["range_mse"]) >= obs_mse)), 4),
            "p_range_b_at_most_observed": round(
                float(np.mean(np.asarray(nl["range_b"]) <= obs_b)), 4),
            "p_ratio_at_least_observed": round(
                float(np.mean(np.asarray(nl["ratio"]) >= obs_mse / max(obs_b, 1e-9))), 4),
            "n_null_partitions": N_NULL,
            "block_sizes": sizes,
        }
    out["random_partition_null"] = null

    # ------------------------------------------------------------------------------- deposit
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    rows = flatten(broad_table, "broad_477") + flatten(corner_table, "corner_60")
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT_CSV, index=False)

    adm_cols = ["set", "axis", "stratum", "row_set_id", "row_set_canonical", "row_set_n_names",
                "interval_is_a_restatement", "unit", "convention", "n", "n_pairs", "n_solutes",
                "n_solvents", "n_sources", "sources", "top_source",
                "top_source_share_of_stratum_squared_error", "share_of_squared_error",
                "mse", "b_insuff_up", "margin", "P_boot", "margin_ci90_lo", "margin_ci90_hi",
                "ci90_excludes_zero", "test_a_boundable", "loso_testable", "loso_n_deletions",
                "loso_n_undefined", "loso_n_leaving_unboundable", "loso_margin_min",
                "loso_margin_max", "loso_worst_source", "loso_worst_margin",
                "loso_worst_n_remaining", "test_b_sign_survives_loso",
                "test_b_strict_remainder_boundable", "admissible_this_cell",
                "admissible_this_cell_strict", "cells_reported", "cells_admissible",
                "cells_admissible_strict", "admissible_in_every_cell",
                "admissible_in_every_cell_strict", "direction", "licenses",
                "reason_not_admissible"]
    adm[adm_cols].sort_values(
        ["set", "axis", "stratum", "unit", "convention"]).to_csv(ADM_CSV, index=False)
    ADM_JSON.write_text(json.dumps(
        {"rule": ADMISSIBILITY_RULE, "one_sidedness": ONE_SIDEDNESS,
         "small_n_bias_of_the_deletion_test": SMALL_N_BIAS,
         "estimator_cell_held_fixed": out["estimator_cell_held_fixed"],
         "verdict": out["admissibility"], **adm_detail}, indent=2))
    pd.DataFrame([r for r in ovl if r["rows_shared"] > 0]).sort_values(
        "rows_shared", ascending=False).to_csv(OVERLAP_CSV, index=False)

    print("\n===== admissibility, broad set (both tests, every unit x convention cell)")
    show = ["axis", "stratum", "unit", "convention", "n", "n_sources", "margin",
            "margin_ci90_lo", "margin_ci90_hi", "test_a_boundable",
            "test_b_sign_survives_loso", "loso_margin_min", "loso_margin_max",
            "loso_worst_source", "admissible_this_cell"]
    head = broad_adm[(broad_adm.unit == "row") & (broad_adm.convention == "res")]
    print(head[head.axis.isin(("whole_set", "solvent_class", "solute_role"))]
          .sort_values("margin", ascending=False)[show].to_string(index=False))
    print("\n[admissible in every cell] " + (", ".join(f"{a}::{s}" for a, s in passing)
                                             or "NONE"))
    print("[of those, positive-margin]  " + (", ".join(f"{a}::{s}" for a, s in passing_pos)
                                             or "NONE"))
    for r in sorted(ovl, key=lambda r: -r["rows_shared"])[:12]:
        if r["rows_shared"]:
            print(f"[overlap] {r['stratum_a']:24s} n {r['rows_shared']:3d} rows / "
                  f"{r['pairs_shared']:3d} pairs with {r['stratum_b']:24s} "
                  f"({r['relation']})")

    cols = ["stratum", "unit", "convention", "n", "n_solutes", "n_solvents", "mse",
            "b_insuff_up", "margin", "P_boot", "margin_ci90_lo", "margin_ci90_hi",
            "boundable_at_headline_cell", "share_of_squared_error", "n_sources",
            "top_source_share_of_stratum_squared_error"]
    for setname, axes in (("broad_477", ("whole_set", "solvent_class", "solute_role",
                                         "solvent_class_x_solute_role")),
                          ("corner_60", ("whole_set", "solvent_class"))):
        for ax in axes:
            s = tab[(tab["set"] == setname) & (tab["axis"] == ax)]
            if s.empty:
                continue
            print(f"\n===== {setname} / {ax}")
            print(s.sort_values(["stratum", "unit", "convention"])[cols].to_string(index=False))
    print(f"\n[saved] {OUT}")
    print(f"[saved] {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
