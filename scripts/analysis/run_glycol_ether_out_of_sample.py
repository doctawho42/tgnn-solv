#!/usr/bin/env python3
r"""Out-of-sample test of the glycol-ether separation, pre-declared before it was run.

WHY THIS EXISTS
---------------
`run_b_insuff_stratified_map.py' searches fifty-nine strata and states one of them: the
glycol-ether solvents of the broad IDAC set, 182 rows over 43 pairs from three publications,
margin +2.04 [+1.27, +2.83] at the headline cell.  `run_b_insuff_map_multiplicity_null.py'
then asks what that search returns when the chemistry is relabelled at random with the
containment lattice, the stratum sizes and every row's m, g, source and pair held fixed, and
answers: at least one certified row set in 58% of 2000 draws, two admissible positive row sets
in 29%, and a certified margin of +2.04 or more in 10.1% of all draws (17% of the draws that
certify anything).  The observed margin sits near the ninetieth percentile of a chemistry-blind
null.  A number a blind search returns that often is not, on the strength of that search alone,
a located fact about glycol ethers.

The only thing that settles it is the same measurement on rows the search never saw.  This
script is that measurement.  Everything from here to the line marked END OF PRE-DECLARATION was
written and committed to before any margin, MSE or B_insuff was computed on the out-of-sample
rows.  What HAD been established first is the geometry of the candidate row sets -- how many
rows exist, which solvents and solutes they carry, which files they come from -- because a test
cannot be designed without knowing whether its data exist.  No outcome quantity was read.

==============================================================================================
                                  PRE-DECLARATION
==============================================================================================

1.  THE INVENTORY.  What is held that the fifty-nine-stratum search did not see.

  (a)  results/published_idac_check/scored_records.csv -- the PGL 6th-edition IDAC database
       (Lazzaroni 2023 + Jaubert/TDE), 7889 of 8138 usable records over 2279 distinct pairs,
       each at its own temperature, scored by this repository's deployed
       ``tgnn_solv.layers.CosmoSacLayer'' on VT-2005 sigma-profiles matched by exact InChIKey.
       Another group's compilation, 16x the rows of the broad set, and a different profile
       database from the broad set's UD.  This is the out-of-sample set.

  (b)  notebooks/data/raw/idac_expanded.csv -- the 14900-row pool the broad set was drawn
       from.  Of its glycol-ether-solvent rows, 184 carry a neutral glycol ether and 182 of
       those are already in the broad set; the remaining 1369 are hydroxy-functionalised ionic
       liquids, which the cascade calls glycol ethers, which have no VT-2005 profile, and which
       the deployed closure cannot score.  Two out-of-sample rows is not a test.  NOT USED.

  (c)  paper/si_tables/vt2005_matched_set_60.csv -- inside the search (reported as corner_60).
       NOT OUT OF SAMPLE.

  So (a) is the whole of the out-of-sample evidence, and the test is run there.

2.  THE ROW SET.  The glycol-ether solvent stratum of (a): every scored PGL record whose
    SOLVENT SMILES returns "glycol_ether" from the unmodified ``classify_solvent'' cascade
    imported from run_b_insuff_stratified_map.py.  No re-tuning of the cascade, no exclusion of
    any solvent it happens to catch, and no addition of any it happens to miss.  Pairs shared
    with the broad IDAC set are excluded before anything is computed.

    Row-set geometry, established before this declaration was written:
      52 rows, 7 solvent molecules (glycerol, 1,4-butanediol, 1,2-ethanediol, 1,2-propanediol,
      2-methoxyethanol, 2-ethoxyethanol, and acetic acid, which the cascade admits because it
      carries an O-H and two oxygens), 1 solute -- water -- and 7 pairs, all from
      IdacRecJaubert+TdeWinOrg.txt, T from 312.87 to 404.15 K.  Source labels within that file:
      50 rows J (Jaubert/Moine compilation), 2 rows T (NIST TDE).
      The exact analogue of the in-sample cell, glycol-ether solvent with an ORGANIC solute,
      has ZERO rows in (a): the non-aqueous Lazzaroni file carries 88 solvents and not one
      glycol ether.

    Two mismatches against the in-sample cell are therefore known in advance and are stated
    here rather than after the result: the solute is water rather than the nineteen organic
    solutes of the in-sample cell, which the paper's own axis 2 holds to be a different
    physical situation; and the oligomers that carry 141 of the in-sample cell's 182 rows
    (di-, tri- and tetraethylene glycol) are absent, leaving 1,2-ethanediol as the only solvent
    molecule in common.

3.  THE ESTIMATOR CELL.  The manuscript's headline cell, unchanged and not swept:
      unit         row
      convention   res (residual-only, the deployed one)
      binning      8 equal-count bins of g(z*)
      variance     Bessel-corrected within-bin variance (ddof=1)
      margin       MSE - 2 * B_insuff^up
      interval     two-way (solute x solvent) cluster bootstrap, 3000 draws, 90% interval,
                   seed from the same ``stable_seed'' used by the map.
    The other three cells (row/full, pair/res, pair/full) are computed and deposited so that
    nothing is hidden, but the PRIMARY is row/res and the verdict is read off it alone.

4.  THE ADMISSIBILITY RULE.  The manuscript's, applied without amendment:
      (a) BOUNDABLE: n >= 40, so each of the eight bins holds at least five rows.
      (b) ROBUST TO LEAVE-ONE-SOURCE-OUT: the margin keeps its sign when any single source
          contributing to it is deleted.  A stratum drawing on one source fails (b) by
          non-testability.  A deletion leaving fewer than 16 rows leaves the fixed cell
          undefined and the stratum fails (b).
    The broad set's source axis is the source DOI.  The PGL files carry no DOI, so the source
    axis here is declared to be the finest provenance the set actually has: the record file,
    and within the Jaubert/TDE files the compilation label (J / T / Y).  This is a coarser
    axis than the in-sample one and therefore a WEAKER test, which is stated now and not
    discovered later.

5.  WHAT COUNTS AS CONFIRMATION.  Declared before running, three outcomes and nothing else:

    CONFIRMED  -- the row set is admissible under rule 4 at the primary cell AND its margin is
                  positive AND the 90% cluster-bootstrap interval lies wholly above zero.
                  Then the separation reproduces on another group's compilation with a
                  different profile database, the multiplicity objection is answered by
                  replication rather than by argument, and the title's second clause keeps its
                  chemical localisation.

    NOT CONFIRMED -- the row set is admissible and its margin is non-positive, or the interval
                  covers zero.  Then the chemical localisation is not out-of-sample evidence
                  and the title's second clause loses it.

    NOT TESTABLE -- the row set is inadmissible under rule 4: too small to bound, or its sign
                  never put at risk because the provenance axis carries no deletion that leaves
                  the fixed cell defined.  This counts AS NOT CONFIRMED for the purpose of the
                  title.  A test the paper's own rule would not let it state in sample is not a
                  test it may state out of sample.

    No fourth outcome is available, and in particular there is no outcome in which a positive
    margin on an inadmissible row set is reported as support.  The one-sidedness of the
    instrument is unchanged: a positive margin certifies B_clos > 0, a non-positive one is
    failure to separate and certifies nothing in the other direction.

6.  ONE TEST.  There is no cascade here, no second stratum, no alternative cell and no
    alternative rule.  Item 7 below is DESCRIPTIVE and is not a test: it is the same map over
    the PGL set's other solvent classes, reported because a reader is entitled to see whether
    the instrument behaves out of sample the way Sec. 3.2 says it behaves in sample (B_insuff
    nearly stratum-independent while MSE varies by an order of magnitude).  Nothing in item 7
    may be stated as a finding, and no glycol-ether verdict is read from it.

7.  DESCRIPTIVE COMPANION.  Solvent class x {row} x {res, full} over the whole PGL set, with n,
    MSE, B_insuff^up, margin and admissibility for each class, plus the ratio of the MSE range
    to the B_insuff range across classes.

==============================================================================================
                              END OF PRE-DECLARATION
==============================================================================================

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_glycol_ether_out_of_sample.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from run_b_insuff_estimator_grid import lotv, two_way_margin_boot  # noqa: E402
from run_b_insuff_stratified_map import (  # noqa: E402
    DDOF,
    MIN_BOUNDABLE,
    N_BINS,
    N_BOOT,
    T_REF,
    classify_solute_family,
    classify_solvent,
    stable_seed,
)

# POST-RUN CORRECTION, recorded rather than folded in silently.  The first execution keyed the
# shared-pair exclusion and the shared-solvent report on RAW SMILES strings, and the two sets
# spell the same molecule differently (`C(CO)O' in the PGL component map, `OCCO' in the broad
# set), so the report read "no solvent molecule in common" when ethylene glycol is in fact in
# both.  Canonicalising fixes a false sentence and can only REMOVE rows from the test, never
# add them.  It touches neither the row-set rule, the estimator cell, the admissibility rule
# nor the verdict, all of which are as declared; the verdict was NOT TESTABLE before the fix
# and is NOT TESTABLE after it.
def canon(smiles: str) -> str:
    mol = Chem.MolFromSmiles(str(smiles))
    return Chem.MolToSmiles(mol) if mol is not None else str(smiles)


PGL = ROOT / "results" / "published_idac_check" / "scored_records.csv"
PGL_SRC = ROOT / "results" / "published_idac_check" / "pgl6ed_source"
BROAD = ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv"
OUT = ROOT / "results" / "b_insuff" / "glycol_ether_out_of_sample.json"
OUT_CSV = ROOT / "results" / "b_insuff" / "glycol_ether_out_of_sample_rows.csv"

TARGET = "glycol_ether"
PRIMARY_UNIT = "row"
PRIMARY_CONV = "res"


# ------------------------------------------------------------------------------------------
def load_pgl() -> pd.DataFrame:
    """The out-of-sample rows, with the declared provenance axis attached."""
    d = pd.read_csv(PGL)
    d["solute_canon"] = d["solute_smiles"].map(canon)
    d["solvent_canon"] = d["solvent_smiles"].map(canon)
    d["pair_key"] = d["solute_canon"] + "|" + d["solvent_canon"]

    # Declared source axis: record file, refined by the compilation label inside the two
    # Jaubert/TDE files (the Lazzaroni file carries no label and stays one source).
    lab: dict[str, str] = {}
    for fname, tag in (("IdacRecJaubert+TdeWinOrg.txt", "WinOrg"),
                       ("IdacRecJaubert+TdeOrginW.txt", "OrgInW")):
        raw = pd.read_csv(PGL_SRC / fname, sep=r"\s+", skiprows=1,
                          names=["solute_id", "solvent_id", "T_K", "gamma", "Source"])
        for r in raw.itertuples(index=False):
            key = f"{tag}|{r.solute_id}|{r.solvent_id}|{round(float(r.T_K), 2)}|{r.gamma}"
            lab[key] = str(r.Source)

    def src_of(row) -> str:
        tag = {"IdacRecJaubert+TdeWinOrg.txt": "WinOrg",
               "IdacRecJaubert+TdeOrginW.txt": "OrgInW"}.get(row.record_file)
        if tag is None:
            return str(row.record_set)
        key = (f"{tag}|{row.solute_id}|{row.solvent_id}|"
               f"{round(float(row.T_K), 2)}|{row.gamma_inf_exp}")
        return f"{row.record_set}:{lab.get(key, 'unlabelled')}"

    d["source_doi"] = [src_of(r) for r in d.itertuples(index=False)]
    smap = {s: classify_solvent(s) for s in d["solvent_smiles"].unique()}
    umap = {s: classify_solute_family(s) for s in d["solute_smiles"].unique()}
    d["solvent_class"] = d["solvent_smiles"].map(smap)
    d["solute_family"] = d["solute_smiles"].map(umap)
    d["solute_role"] = np.where(d["solute_family"] == "water", "water_solute", "organic_solute")
    return d


def pair_unit(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["_dT"] = (d["T_K"] - T_REF).abs()
    d["_ord"] = np.arange(len(d))
    d = d.sort_values(["pair_key", "_dT", "T_K", "_ord"])
    return d.groupby("pair_key", sort=True).head(1).sort_values("_ord").drop(
        columns=["_dT", "_ord"])


def cell(sub: pd.DataFrame, col: str, seed: int) -> dict:
    """The headline cell, computed exactly as the map computes it."""
    m = sub["m"].to_numpy(float)
    g = sub[col].to_numpy(float)
    n = len(m)
    rec = {
        "n": int(n),
        "n_solutes": int(sub["solute_smiles"].nunique()),
        "n_solvents": int(sub["solvent_smiles"].nunique()),
        "n_pairs": int(sub["pair_key"].nunique()),
        "n_sources": int(sub["source_doi"].nunique()),
        "mse": round(float(np.mean((m - g) ** 2)), 4),
        "var_m": round(float(np.var(m, ddof=0)), 4),
        "boundable_at_headline_cell": bool(n >= MIN_BOUNDABLE),
        "b_insuff_up": None, "b_closure_lb": None, "margin": None,
        "P_boot": None, "margin_ci90": None,
    }
    if n >= 2 * N_BINS:
        b = lotv(g, m, N_BINS, DDOF)
        rec["b_insuff_up"] = round(b, 4)
        rec["b_closure_lb"] = round(rec["mse"] - b, 4)
        rec["margin"] = round(rec["mse"] - 2 * b, 4)
        rec["b_insuff_exceeds_var_m"] = bool(b > rec["var_m"])
    if rec["margin"] is not None and max(rec["n_solutes"], rec["n_solvents"]) >= 2:
        try:
            P, lo, hi = two_way_margin_boot(g, m, sub["solute_smiles"].to_numpy(),
                                            sub["solvent_smiles"].to_numpy(),
                                            N_BINS, DDOF, n_boot=N_BOOT, seed=seed)
            if np.isfinite(P):
                rec["P_boot"] = round(float(P), 3)
                rec["margin_ci90"] = [round(float(lo), 3), round(float(hi), 3)]
        except Exception as exc:
            rec["boot_error"] = type(exc).__name__
    rec["bootstrap_reduces_to_one_way"] = bool(rec["n_solutes"] < 2 or rec["n_solvents"] < 2)
    return rec


def loso(sub: pd.DataFrame, col: str, base: float | None) -> tuple[list[dict], bool, str]:
    """Rule 4(b) on the declared provenance axis."""
    m = sub["m"].to_numpy(float)
    g = sub[col].to_numpy(float)
    src = sub["source_doi"].astype(str).to_numpy()
    curve = []
    for s in sorted(set(src)):
        keep = src != s
        rec = {"left_out": s, "n_removed": int((~keep).sum()), "n_remaining": int(keep.sum()),
               "remainder_still_boundable": bool(keep.sum() >= MIN_BOUNDABLE),
               "margin": None}
        if keep.sum() >= 2 * N_BINS:
            mm, gg = m[keep], g[keep]
            b = lotv(gg, mm, N_BINS, DDOF)
            rec["margin"] = round(float(np.mean((mm - gg) ** 2)) - 2 * b, 4)
        curve.append(rec)
    if base is None:
        return curve, False, f"the fixed cell is undefined at n={len(m)}"
    if len(curve) < 2:
        return curve, False, (f"one source ({curve[0]['left_out']}): leave-one-source-out "
                              "cannot be run, so the sign was never put at risk")
    ev = [c for c in curve if c["margin"] is not None]
    if len(ev) < len(curve):
        bad = [c["left_out"] for c in curve if c["margin"] is None]
        return curve, False, (f"{len(bad)} of {len(curve)} deletions leave fewer than "
                              f"{2 * N_BINS} rows and the fixed cell is then undefined "
                              f"({', '.join(bad)}), so the sign is not verifiable")
    sgn = 1.0 if base > 0 else -1.0
    flips = [c for c in ev if c["margin"] * sgn <= 0]
    if flips:
        return curve, False, "sign does not survive deletion of " + "; ".join(
            f"{c['left_out']} ({base:+.3f} -> {c['margin']:+.3f})" for c in flips)
    return curve, True, ""


def verdict(rec: dict, ok_b: bool, why_b: str) -> tuple[str, str]:
    ok_a = bool(rec["boundable_at_headline_cell"])
    if not ok_a:
        return "NOT TESTABLE", f"not boundable: n={rec['n']} < {MIN_BOUNDABLE}"
    if not ok_b:
        return "NOT TESTABLE", why_b
    if rec["margin"] is None or rec["margin"] <= 0:
        return "NOT CONFIRMED", "admissible, and the margin does not separate"
    ci = rec["margin_ci90"]
    if ci is None:
        return "NOT CONFIRMED", "admissible and positive, but no cluster interval exists"
    if ci[0] <= 0:
        return "NOT CONFIRMED", (f"admissible and positive, but the 90% interval "
                                 f"[{ci[0]:+.3f}, {ci[1]:+.3f}] covers zero")
    return "CONFIRMED", (f"admissible, margin {rec['margin']:+.3f}, "
                         f"90% interval [{ci[0]:+.3f}, {ci[1]:+.3f}]")


# ------------------------------------------------------------------------------------------
def main() -> int:
    d = load_pgl()
    broad = pd.read_csv(BROAD)
    broad["solute_canon"] = broad["solute_smiles"].map(canon)
    broad["solvent_canon"] = broad["solvent_smiles"].map(canon)
    broad_pairs = set(broad["solute_canon"] + "|" + broad["solvent_canon"])
    broad_glycol_solvents = set(
        broad.loc[[classify_solvent(s) == TARGET for s in broad["solvent_smiles"]],
                  "solvent_canon"])

    out: dict = {
        "what": ("pre-declared out-of-sample test of the glycol-ether separation, on the PGL "
                 "6th-edition IDAC database scored by the deployed CosmoSacLayer on VT-2005 "
                 "profiles"),
        # The whole docstring, not a slice of it.  An earlier version sliced on the string
        # "PRE-DECLARATION", which also occurs inside "END OF PRE-DECLARATION" and in the prose
        # above the banner, so it deposited 508 characters of the wrong text.  Depositing the
        # docstring entire cannot mis-slice and cannot silently drop a clause of the hypothesis.
        "pre_declaration": __doc__,
        "pre_declaration_sha256": hashlib.sha256(__doc__.encode()).hexdigest(),
        "out_of_sample_set": {
            "file": str(PGL.relative_to(ROOT)),
            "n_rows": int(len(d)),
            "n_pairs": int(d["pair_key"].nunique()),
            "profile_database": "VT-2005",
            "broad_set_profile_database": "UD",
            "record_sets": d["record_set"].value_counts().to_dict(),
        },
    }

    # ---- the declared row set --------------------------------------------------------------
    g = d[d["solvent_class"] == TARGET].copy()
    shared = sorted(set(g["pair_key"]) & broad_pairs)
    g = g[~g["pair_key"].isin(broad_pairs)]
    analogue = g[g["solute_role"] == "organic_solute"]

    out["row_set"] = {
        "definition": ("classify_solvent(solvent_smiles) == 'glycol_ether', minus any pair "
                       "shared with the broad IDAC set"),
        "n_rows": int(len(g)),
        "n_pairs": int(g["pair_key"].nunique()),
        "n_solutes": int(g["solute_smiles"].nunique()),
        "n_solvents": int(g["solvent_smiles"].nunique()),
        "solvents": sorted(set(g["solvent_name"].astype(str))),
        "solutes": sorted(set(g["solute_name"].astype(str))),
        "pairs_shared_with_broad_set_excluded": shared,
        "sources": g["source_doi"].value_counts().to_dict(),
        "T_K_range": [float(g["T_K"].min()), float(g["T_K"].max())] if len(g) else None,
        "solvent_molecules_shared_with_in_sample_cell": sorted(
            set(g["solvent_canon"]) & broad_glycol_solvents),
        "in_sample_cell_solvent_molecules": sorted(broad_glycol_solvents),
        "exact_analogue_cell_glycol_ether_x_organic_solute_n_rows": int(len(analogue)),
    }

    # ---- the primary test ------------------------------------------------------------------
    units = {"row": g, "pair": pair_unit(g) if len(g) else g}
    conv = {"res": "g_res", "full": "g_full"}
    cells = {}
    for uname, dd in units.items():
        for cname, col in conv.items():
            if len(dd) == 0:
                cells[f"{uname}::{cname}"] = {"n": 0}
                continue
            seed = stable_seed("pgl6ed_out_of_sample", uname, cname,
                               f"solvent_class::{TARGET}")
            rec = cell(dd, col, seed)
            curve, ok_b, why_b = loso(dd, col, rec["margin"])
            v, reason = verdict(rec, ok_b, why_b)
            rec["loso_curve"] = curve
            rec["test_a_boundable"] = bool(rec["boundable_at_headline_cell"])
            rec["test_b_sign_survives_loso"] = bool(ok_b)
            rec["admissible"] = bool(rec["boundable_at_headline_cell"] and ok_b)
            rec["verdict"] = v
            rec["verdict_reason"] = reason
            cells[f"{uname}::{cname}"] = rec
    out["cells"] = cells
    primary = cells[f"{PRIMARY_UNIT}::{PRIMARY_CONV}"]
    out["primary"] = {
        "cell": f"{PRIMARY_UNIT}/{PRIMARY_CONV}, {N_BINS} equal-count bins, ddof={DDOF}",
        "verdict": primary.get("verdict"),
        "reason": primary.get("verdict_reason"),
        "margin": primary.get("margin"),
        "margin_ci90": primary.get("margin_ci90"),
        "in_sample_comparator": {"margin": 2.0364, "ci90": [1.268, 2.833], "n": 182,
                                 "n_pairs": 43, "n_sources": 3},
    }

    # ---- descriptive companion (item 7; not a test) ----------------------------------------
    desc = []
    for lab in sorted(d["solvent_class"].unique()):
        sub = d[d["solvent_class"] == lab]
        rec = cell(sub, "g_res", stable_seed("pgl6ed_desc", "row", "res", str(lab)))
        curve, ok_b, why_b = loso(sub, "g_res", rec["margin"])
        rec["stratum"] = lab
        rec["admissible"] = bool(rec["boundable_at_headline_cell"] and ok_b)
        rec["reason_not_admissible"] = "" if rec["admissible"] else why_b
        rec.pop("loso_curve", None)
        desc.append(rec)
    bnd = [r for r in desc if r["margin"] is not None and r["boundable_at_headline_cell"]]
    out["descriptive_solvent_class_map"] = {
        "note": ("DESCRIPTIVE, declared as not a test (item 7). No verdict is read from this "
                 "block and no stratum in it is stated as a finding."),
        "strata": desc,
        "range_mse_over_boundable": (round(max(r["mse"] for r in bnd)
                                           - min(r["mse"] for r in bnd), 4) if bnd else None),
        "range_b_insuff_over_boundable": (round(max(r["b_insuff_up"] for r in bnd)
                                                - min(r["b_insuff_up"] for r in bnd), 4)
                                          if bnd else None),
    }

    # ---- donor-class shares on the same out-of-sample set --------------------------------
    # Not part of the test.  Sec. 3.2.4 claims the VT-2005-matched set's hydrogen-bond
    # localisation ("90% of the squared error on strong donors, near-exact on acceptor-only")
    # is "the same localisation" the published evaluation shows at 130x the rows.  That set is
    # this one, so the claim is checkable here rather than assertable, and these are the
    # numbers it is checked against.
    se = (d["m"] - d["g_res"]) ** 2
    tot = float(se.sum())
    donor = []
    for lab, idx in d.groupby("solvent_donor_class").groups.items():
        s = se.loc[idx]
        donor.append({"donor_class": str(lab), "n": int(len(s)),
                      "share_of_squared_error": round(float(s.sum()) / tot, 4),
                      "mse": round(float(s.mean()), 4)})
    out["donor_class_shares_res"] = sorted(donor, key=lambda r: -r["share_of_squared_error"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    if len(g):
        g.to_csv(OUT_CSV, index=False)

    print(json.dumps({"row_set": out["row_set"], "primary": out["primary"]}, indent=2))
    print("\nDESCRIPTIVE solvent-class map (PGL, row/res) -- not a test:")
    print(pd.DataFrame(desc)[["stratum", "n", "n_sources", "mse", "b_insuff_up", "margin",
                              "P_boot", "admissible"]].to_string(index=False))
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
