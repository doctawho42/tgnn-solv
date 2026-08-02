#!/usr/bin/env python3
"""Convention audit of the broad IDAC (n=477) and corner (n=60) decompositions.

Everything here exists so that ONE combinatorial convention can be applied to both sets and
checked, rather than each set being reported under whichever convention flatters it.

  COMBINATORIAL CONVENTION.  One rule for both sets: headline the DEPLOYED residual-only
  convention, pairing MSE and the LOTV bound computed under that same convention.  Supplies
  the residual-only margin on the broad set with its three clustered bootstraps, and a
  per-cell bootstrap frequency for every cell of that set's bin-count x variance x convention
  grid.  Also evaluates the MIN-OVER-CONVENTIONS bound, which is admissible in population
  because B_insuff = E[Var(m | z*,T)] does not depend on the closure convention while the two
  LOTV bounds bin on two different functions of the same z*.  The same rule is then applied to
  the 2010 typed kernel on its OWN typed latent, on both sets, under both conventions (g10r is
  the residual-only arm), so the two are printed side by side rather than mixed.

  MATCH RULE.  How many of the 490/477 rows resolve into the UD compound list by an EXACT
  InChIKey and how many only through the 14-character first-block fallback, and the
  decomposition re-estimated on the strictly matched subset.

  THE TWO 1.783 VALUES and THE TWO 57s.  The chromatography-only 2002 MSE and the shared-57
  2002 MSE printed to six decimals, their overlap, and an explicit test of whether the
  dispersion-defined 57 (60 minus the Br/I pairs) is the same set as the
  corner-inside-broad-set 57.  They are not the same statistic and the coincidence is a
  rounding one, which is why both are printed at full precision here.

  THE PAIR-CONDITIONAL BOUND.  E[Var(m | pair)] on the subpopulation of rows that share a
  pair, against the LOTV binning bound computed on those same rows, plus the source
  homogeneity of those pairs (how many multi-row pairs come from one DOI).

  THE TYPED LATENT'S DIMENSION.  dim(z*,T) and dim/n, per row and per distinct pair, for the
  2010 kernel's own typed three-profile latent on both sets.

  DEPOSITED TABLES.  Writes the 477-row and 60-row row-level tables so the two sets can be
  inspected without running any code.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_convention_audit.py
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer, CosmoSac2010Layer  # noqa: E402

UD = Path.home() / "COSMOSAC" / "profiles" / "UD"
IDAC = ROOT / "notebooks" / "data" / "raw" / "idac_expanded.csv"
IDAC_RAW = ROOT / "notebooks" / "data" / "raw" / "idac_expanded_raw.csv"
IDAC_CURATED = ROOT / "notebooks" / "data" / "raw" / "idac.csv"
MATCHED = ROOT / "results" / "b_insuff" / "matched_pairs.csv"
OUT = ROOT / "results" / "b_insuff" / "convention_audit.json"
# Deposited row-level tables. `broad_idac_set_477.csv' was named
# `representative_set_477.csv' before 2026-07-28; the set is renamed throughout because
# "representative" names a coverage claim the manuscript retracts (see S4.2(i)).
TAB_REP = ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv"
TAB_COR = ROOT / "paper" / "si_tables" / "vt2005_matched_set_60.csv"

BIN_GRID = (3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32, 40, 48)


def corner_provenance(corner: pd.DataFrame, curated_csv: Path = IDAC_CURATED,
                      temperature: float = 298.0, tol: float = 0.5) -> pd.DataFrame:
    """Temperature, measurement method, source DOI and journal for each corner pair.

    `matched_pairs.csv' carries only the aggregated label, so the deposited corner table
    would otherwise lack the provenance fields the 477-row table carries and the
    Supporting-Information-Available statement promises.  The corner is the VT-2005-matchable
    298 K subset of the curated IDAC compilation, so the join is on canonical solute/solvent
    SMILES within `tol' of `temperature'; all 60 pairs resolve there and their aggregated
    ln(gamma_inf) reproduces `matched_pairs.csv' exactly.
    """
    raw = pd.read_csv(curated_csv, low_memory=False)
    raw["Tn"] = pd.to_numeric(raw["temperature"], errors="coerce")
    raw = raw[(raw["Tn"] - temperature).abs() <= tol].copy()

    def canon(smi):
        mol = Chem.MolFromSmiles(str(smi))
        return Chem.MolToSmiles(mol) if mol is not None else None

    raw["cu"] = [canon(s) for s in raw["solute_smiles"]]
    raw["cv"] = [canon(s) for s in raw["solvent_smiles"]]

    def joined(s):
        return "; ".join(sorted({str(x) for x in s.dropna()})) or "unreported"

    agg = raw.groupby(["cu", "cv"]).agg(T_K=("Tn", "mean"), method=("method", joined),
                                        source_doi=("doi", joined), journal=("journal", joined))
    out = corner.merge(agg, left_on=["solute_key", "solvent_key"], right_index=True, how="left")
    for col in ("method", "source_doi", "journal"):
        out[col] = out[col].fillna("unreported")
    return out


# --------------------------------------------------------------------------- helpers
def _resolver():
    """Resolve a SMILES into a UD compound key, recording which rule fired."""
    exact, by14 = {}, {}
    for ln in (UD / "complist.txt").read_text().splitlines()[1:]:
        t = ln.split()
        if len(t) < 5:
            continue
        ik = t[-1]
        exact[ik] = ik
        by14.setdefault(ik.split("-")[0], ik)

    def resolve(smi):
        mol = Chem.MolFromSmiles(str(smi))
        if mol is None:
            return None, None
        k = Chem.MolToInchiKey(mol)
        if k in exact:
            return exact[k], "exact"
        hit = by14.get(k.split("-")[0])
        return (hit, "first_block") if hit is not None else (None, None)
    return resolve


def _parse(path):
    meta, vals = {}, []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.startswith("# meta:"):
            meta = json.loads(line[len("# meta:"):].strip())
        elif line and not line.startswith("#"):
            vals.append(float(line.split()[1]))
    p = np.asarray(vals, float)
    return (p, float(p.sum()), float(meta.get("volume [A^3]") or 0.0),
            float(meta.get("disp. e/kB [K]") or 0.0))


def _profiles(su, sv):
    f = [UD / "sigma" / f"{su}.sigma", UD / "sigma" / f"{sv}.sigma",
         UD / "sigma3" / f"{su}.sigma", UD / "sigma3" / f"{sv}.sigma"]
    if not all(x.exists() for x in f):
        return None
    pu_s, Au_s, _, _ = _parse(f[0])
    pu_v, Au_v, _, _ = _parse(f[1])
    pt_s, At_s, V_s, eps_s = _parse(f[2])
    pt_v, At_v, V_v, eps_v = _parse(f[3])
    if pu_s.size != 51 or pu_v.size != 51 or pt_s.size != 153 or pt_v.size != 153:
        return None
    return dict(pu_s=pu_s, pu_v=pu_v, Au_s=Au_s, Au_v=Au_v, pt_s=pt_s, pt_v=pt_v,
                At_s=At_s, At_v=At_v, V_s=V_s, V_v=V_v, eps_s=eps_s, eps_v=eps_v)


def lotv(g, m, n_bins, ddof):
    q = np.quantile(g, np.linspace(0.0, 1.0, n_bins + 1))
    q[0] -= 1e-9
    q[-1] += 1e-9
    idx = np.digitize(g, q[1:-1])
    tot = 0.0
    for b in range(n_bins):
        mm = m[idx == b]
        if len(mm) > ddof:
            tot += (len(mm) / len(m)) * float(mm.var(ddof=ddof))
    return tot


def two_way_margin(g, m, su, sv, n_bins, ddof, n_boot=2000, seed=0):
    rng = np.random.default_rng(seed)
    U, V = np.unique(su), np.unique(sv)
    iu = {s: i for i, s in enumerate(U)}
    iv = {s: i for i, s in enumerate(V)}
    isu = np.array([iu[s] for s in su])
    isv = np.array([iv[s] for s in sv])
    out = []
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, len(U), len(U)), minlength=len(U))
        cv = np.bincount(rng.integers(0, len(V), len(V)), minlength=len(V))
        w = cs[isu] * cv[isv]
        if w.sum() < 30:
            continue
        idx = np.repeat(np.arange(len(m)), w)
        mm, gg = m[idx], g[idx]
        out.append(float(np.mean((mm - gg) ** 2)) - 2 * lotv(gg, mm, n_bins, ddof))
    out = np.array(out)
    return float(np.mean(out > 0)), [float(np.percentile(out, 5)), float(np.percentile(out, 95))]


def cluster_margin(g, m, clusters, n_bins, ddof, n_boot=2000, seed=0):
    rng = np.random.default_rng(seed)
    C = np.unique(clusters)
    idx_by_c = {c: np.where(clusters == c)[0] for c in C}
    out = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(C), len(C))
        idx = np.concatenate([idx_by_c[C[p]] for p in pick])
        if len(idx) < 30:
            continue
        mm, gg = m[idx], g[idx]
        out.append(float(np.mean((mm - gg) ** 2)) - 2 * lotv(gg, mm, n_bins, ddof))
    out = np.array(out)
    return float(np.mean(out > 0)), [float(np.percentile(out, 5)), float(np.percentile(out, 95))]


# --------------------------------------------------------------------------- main
def main() -> int:
    resolve = _resolver()
    idac = pd.read_csv(IDAC, low_memory=False)
    idac["Tn"] = pd.to_numeric(idac["temperature"], errors="coerce")
    idac = idac.dropna(subset=["ln_gamma_inf", "Tn"]).copy()
    res_u = [resolve(s) for s in idac["solute_smiles"]]
    res_v = [resolve(s) for s in idac["solvent_smiles"]]
    idac["su"] = [a for a, _ in res_u]
    idac["sv"] = [a for a, _ in res_v]
    idac["su_rule"] = [b for _, b in res_u]
    idac["sv_rule"] = [b for _, b in res_v]
    idac = idac.dropna(subset=["su", "sv"])
    print(f"[ladder] rows resolving into UD by InChIKey (either rule): {len(idac)}", flush=True)

    raw = pd.read_csv(IDAC_RAW, low_memory=False)
    raw["Tn"] = pd.to_numeric(raw["temperature"], errors="coerce")
    key = ["solute_smiles", "solvent_smiles", "Tn"]
    meth = (raw.dropna(subset=["Tn"]).groupby(key)["method"]
               .agg(lambda s: s.dropna().iloc[0] if s.notna().any() else "unreported"))
    jour = (raw.dropna(subset=["Tn"]).groupby(key)["journal"]
               .agg(lambda s: s.dropna().iloc[0] if s.notna().any() else "unreported"))
    idac["method"] = [meth.get((a, b, round(float(t), 10)), meth.get((a, b, t), "unreported"))
                      for a, b, t in zip(idac.solute_smiles, idac.solvent_smiles, idac.Tn)]
    idac["journal"] = [jour.get((a, b, round(float(t), 10)), jour.get((a, b, t), "unreported"))
                       for a, b, t in zip(idac.solute_smiles, idac.solvent_smiles, idac.Tn)]

    by_T = {}
    n_parse_ok = 0
    for _, r in idac.iterrows():
        pr = _profiles(r["su"], r["sv"])
        if pr is None:
            continue
        n_parse_ok += 1
        if pr["eps_s"] == 0 or pr["eps_v"] == 0:
            continue
        by_T.setdefault(round(float(r["Tn"]), 2), []).append(
            {**pr, "su": r["su"], "sv": r["sv"], "m": float(r["ln_gamma_inf"]),
             "T": float(r["Tn"]), "doi": str(r["idac_source_dois"]),
             "method": str(r["method"]), "journal": str(r["journal"]),
             "solute_smiles": str(r["solute_smiles"]), "solvent_smiles": str(r["solvent_smiles"]),
             "su_rule": str(r["su_rule"]), "sv_rule": str(r["sv_rule"])})
    print(f"[ladder] rows whose profile files parse: {n_parse_ok}", flush=True)

    l02 = CosmoSacLayer().double().eval(); l02.n_iter_eval = 300
    l10 = CosmoSac2010Layer().double().eval(); l10.n_iter_eval = 300
    st = lambda recs, k: torch.tensor(np.asarray([r[k] for r in recs]), dtype=torch.float64)

    flat, g02f, g02r, g10f, g10r = [], [], [], [], []
    for Tval, recs in by_T.items():
        T = torch.full((len(recs),), Tval, dtype=torch.float64)
        with torch.no_grad():
            a = l02.ln_gamma_inf(st(recs, "pu_s"), st(recs, "pu_v"), st(recs, "Au_s"),
                                 st(recs, "Au_v"), st(recs, "V_s"), st(recs, "V_v"), T).numpy()
            ar = l02.ln_gamma_inf(st(recs, "pu_s"), st(recs, "pu_v"), st(recs, "Au_s"),
                                  st(recs, "Au_v"), None, None, T).numpy()
            l10.use_dispersion = False
            b = l10.ln_gamma_inf(st(recs, "pt_s"), st(recs, "pt_v"), st(recs, "At_s"),
                                 st(recs, "At_v"), st(recs, "V_s"), st(recs, "V_v"), T).numpy()
            br = l10.ln_gamma_inf(st(recs, "pt_s"), st(recs, "pt_v"), st(recs, "At_s"),
                                  st(recs, "At_v"), None, None, T).numpy()
        g02f += list(a); g02r += list(ar); g10f += list(b); g10r += list(br); flat += recs
    print(f"[closure] evaluated {len(flat)} rows", flush=True)

    m = np.array([r["m"] for r in flat])
    su = np.array([r["su"] for r in flat]); sv = np.array([r["sv"] for r in flat])
    Ts = np.array([r["T"] for r in flat])
    doi = np.array([r["doi"] for r in flat])
    method = np.array([r["method"] for r in flat])
    g02f, g02r, g10f, g10r = map(np.array, (g02f, g02r, g10f, g10r))
    pair = np.array([f"{a}|{b}" for a, b in zip(su, sv)])
    strict = np.array([r["su_rule"] == "exact" and r["sv_rule"] == "exact" for r in flat])

    mse_f = float(np.mean((g02f - m) ** 2))
    mse_r = float(np.mean((g02r - m) ** 2))
    out = {"n": len(m), "mse_2002_full": round(mse_f, 6), "mse_2002_res": round(mse_r, 6),
           "var_m": round(float(m.var(ddof=0)), 4)}

    # ---------------------------------------------------- (R3-1) one convention rule
    conv = {"full": g02f, "res": g02r}
    headline = {}
    for cname, g in conv.items():
        mse = float(np.mean((g - m) ** 2))
        b = lotv(g, m, 8, 1)
        P2, ci2 = two_way_margin(g, m, su, sv, 8, 1)
        Pp, cip = cluster_margin(g, m, pair, 8, 1)
        Pd, cid = cluster_margin(g, m, doi, 8, 1)
        headline[cname] = {
            "mse": round(mse, 4), "b_insuff_up_8bins_Bessel": round(b, 4),
            "b_clos_lb": round(mse - b, 4), "margin": round(mse - 2 * b, 4),
            "P_two_way_solute_x_solvent": round(P2, 3), "ci90_two_way": [round(c, 3) for c in ci2],
            "P_clustered_on_pair": round(Pp, 3), "ci90_pair": [round(c, 3) for c in cip],
            "P_clustered_on_doi": round(Pd, 3), "ci90_doi": [round(c, 3) for c in cid],
        }
        print(f"[conv {cname}] margin {mse - 2*b:+.4f} P2={P2:.3f}", flush=True)
    out["representative_by_convention_8bins_Bessel"] = headline

    # min-over-conventions: B_insuff is convention-independent, so the tighter of the two
    # binning bounds is admissible in population.  Charged against the DEPLOYED (res) MSE.
    b_min = min(lotv(g02f, m, 8, 1), lotv(g02r, m, 8, 1))
    out["min_over_conventions"] = {
        "b_insuff_up": round(b_min, 4),
        "margin_against_deployed_res_mse": round(mse_r - 2 * b_min, 4),
        "margin_against_full_mse": round(mse_f - 2 * b_min, 4),
    }

    # ------------------- (R3-1b) the SAME convention rule applied to the 2010 typed kernel
    # Floor check (3) in the manuscript ("the modern kernel on its own typed latent") was
    # computed under the FULL combinatorial convention while the paper declares the DEPLOYED
    # residual-only convention on both sets.  Both are computed here so the switch is visible.
    conv10 = {"full": g10f, "res": g10r}
    head10 = {}
    for cname, g in conv10.items():
        mse = float(np.mean((g - m) ** 2))
        b = lotv(g, m, 8, 1)
        P2, ci2 = two_way_margin(g, m, su, sv, 8, 1)
        Pp, cip = cluster_margin(g, m, pair, 8, 1)
        Pd, cid = cluster_margin(g, m, doi, 8, 1)
        cells = {}
        for nb in BIN_GRID:
            for ddof, lab in ((0, "ML"), (1, "Bessel")):
                bb = lotv(g, m, nb, ddof)
                cells[f"{nb}bins_{lab}"] = {"b_insuff_up": round(bb, 4),
                                            "margin": round(mse - 2 * bb, 4)}
        head10[cname] = {
            "mse": round(mse, 4), "b_insuff_up_8bins_Bessel": round(b, 4),
            "b_clos_lb": round(mse - b, 4), "margin": round(mse - 2 * b, 4),
            "P_two_way_solute_x_solvent": round(P2, 3), "ci90_two_way": [round(c, 3) for c in ci2],
            "P_clustered_on_pair": round(Pp, 3), "ci90_pair": [round(c, 3) for c in cip],
            "P_clustered_on_doi": round(Pd, 3), "ci90_doi": [round(c, 3) for c in cid],
            "bin_grid": cells,
            "n_cells_margin_positive": int(sum(c["margin"] > 0 for c in cells.values())),
            "min_margin_over_bin_grid": min(c["margin"] for c in cells.values()),
        }
        print(f"[2010 conv {cname}] mse {mse:.4f} b {b:.4f} margin {mse - 2*b:+.4f} "
              f"P2={P2:.3f} Ppair={Pp:.3f} Pdoi={Pd:.3f}", flush=True)
    out["representative_2010_by_convention_8bins_Bessel"] = head10

    # per-cell grid with bootstrap frequency, representative set
    grid = []
    for cname, g in conv.items():
        mse = float(np.mean((g - m) ** 2))
        for nb in BIN_GRID:
            for ddof, lab in ((0, "ML"), (1, "Bessel")):
                b = lotv(g, m, nb, ddof)
                P, ci = two_way_margin(g, m, su, sv, nb, ddof, n_boot=600, seed=1)
                grid.append({"convention": cname, "bins": nb, "variance": lab,
                             "b_insuff_up": round(b, 4), "margin": round(mse - 2 * b, 4),
                             "P_positive": round(P, 3)})
        print(f"[grid] {cname} done", flush=True)
    out["representative_grid"] = grid
    out["representative_grid_summary"] = {
        "n_cells": len(grid),
        "n_cells_margin_positive": int(sum(c["margin"] > 0 for c in grid)),
        "min_margin": min(c["margin"] for c in grid),
        "max_margin": max(c["margin"] for c in grid),
        "min_margin_cell": min(grid, key=lambda c: c["margin"]),
        "min_P_positive": min(c["P_positive"] for c in grid),
        "res_only_min_margin": min(c["margin"] for c in grid if c["convention"] == "res"),
        "res_only_min_P": min(c["P_positive"] for c in grid if c["convention"] == "res"),
    }

    # ---------------------------------------------------- (R3-4) the match rule
    rules_u = Counter(r["su_rule"] for r in flat)
    rules_v = Counter(r["sv_rule"] for r in flat)
    mol_rule = {}
    for r in flat:
        mol_rule[r["su"]] = r["su_rule"]
        mol_rule[r["sv"]] = r["sv_rule"]
    match = {
        "rows_solute_exact": int(rules_u.get("exact", 0)),
        "rows_solute_first_block_only": int(rules_u.get("first_block", 0)),
        "rows_solvent_exact": int(rules_v.get("exact", 0)),
        "rows_solvent_first_block_only": int(rules_v.get("first_block", 0)),
        "rows_both_exact": int(strict.sum()),
        "rows_with_any_first_block": int((~strict).sum()),
        "distinct_molecules": len(mol_rule),
        "distinct_molecules_first_block_only": int(sum(v == "first_block" for v in mol_rule.values())),
        "first_block_molecules": sorted(k for k, v in mol_rule.items() if v == "first_block"),
    }
    if strict.sum() > 40:
        for cname, g in conv.items():
            gs, ms = g[strict], m[strict]
            mse_s = float(np.mean((gs - ms) ** 2))
            b_s = lotv(gs, ms, 8, 1)
            P_s, ci_s = two_way_margin(gs, ms, su[strict], sv[strict], 8, 1)
            match[f"strict_subset_{cname}"] = {
                "n": int(strict.sum()), "mse": round(mse_s, 4),
                "b_insuff_up_8bins_Bessel": round(b_s, 4),
                "margin": round(mse_s - 2 * b_s, 4),
                "P_two_way": round(P_s, 3), "ci90": [round(c, 3) for c in ci_s],
                "var_m": round(float(ms.var(ddof=0)), 4),
                "n_distinct_pairs": int(len(set(pair[strict]))),
            }
    out["match_rule"] = match
    print(f"[match] rows both exact: {strict.sum()} / {len(m)}", flush=True)

    # ---------------------------------------------------- (R3-5) the two 1.783s, the two 57s
    corner = pd.read_csv(MATCHED)
    cres = {}
    for a, b in zip(corner.solute_key, corner.solvent_key):
        ka, _ = resolve(a)
        kb, _ = resolve(b)
        cres[(a, b)] = (ka, kb)
    cset = {v for v in cres.values() if None not in v}
    shared = np.array([(a, b) in cset and abs(t - 298.15) <= 1.0
                       for a, b, t in zip(su, sv, Ts)])
    gc = np.array([str(x).startswith("Chromatography") for x in method])
    mse_gc = float(np.mean((g02f[gc] - m[gc]) ** 2))
    mse_sh = float(np.mean((g02f[shared] - m[shared]) ** 2))
    # which corner pairs are NOT represented
    present = {(a, b) for a, b, s in zip(su, sv, shared) if s}
    missing = [(sm, sv_, cres[(sm, sv_)]) for sm, sv_ in zip(corner.solute_key, corner.solvent_key)
               if cres[(sm, sv_)] not in present]
    names = {(r.solute_key, r.solvent_key): (r.solute_name, r.solvent_name)
             for r in corner.itertuples()}
    out["two_1783_values"] = {
        "gas_chromatography_only": {"n": int(gc.sum()), "mse_2002_full": round(mse_gc, 6)},
        "shared_57": {"n": int(shared.sum()), "mse_2002_full": round(mse_sh, 6)},
        "identical_to_4dp": bool(round(mse_gc, 3) == round(mse_sh, 3)),
        "rows_in_both_subsets": int((gc & shared).sum()),
        "coincidence_not_identity": bool(mse_gc != mse_sh),
    }
    out["the_two_57s"] = {
        "corner_pairs_absent_from_representative_set": [
            {"solute": s, "solvent": v, "solute_name": names[(s, v)][0],
             "solvent_name": names[(s, v)][1]} for s, v, _ in missing],
        "n_absent": len(missing),
        "corner_pairs_without_ccosmo_dispersion_BrI": [
            "bromobenzene / 1,2-ethanediol", "2-bromopropane / pyridine",
            "iodobenzene / 1,2-ethanediol"],
    }
    print(f"[1.783] gc={mse_gc:.6f}  shared57={mse_sh:.6f}  missing={len(missing)}", flush=True)

    # -------------- (R3-1c) the same convention switch on the 60-row corner, 2010 and 2002
    crecs, crows = [], []
    for i, r in corner.iterrows():
        ka, kb = cres[(r["solute_key"], r["solvent_key"])]
        if ka is None or kb is None:
            continue
        pr = _profiles(ka, kb)
        if pr is None:
            continue
        crecs.append({**pr, "su": ka, "sv": kb, "m": float(r["m"])})
        crows.append(i)
    Tc = torch.full((len(crecs),), 298.15, dtype=torch.float64)
    with torch.no_grad():
        c02f = l02.ln_gamma_inf(st(crecs, "pu_s"), st(crecs, "pu_v"), st(crecs, "Au_s"),
                                st(crecs, "Au_v"), st(crecs, "V_s"), st(crecs, "V_v"), Tc).numpy()
        c02r = l02.ln_gamma_inf(st(crecs, "pu_s"), st(crecs, "pu_v"), st(crecs, "Au_s"),
                                st(crecs, "Au_v"), None, None, Tc).numpy()
        l10.use_dispersion = False
        c10f = l10.ln_gamma_inf(st(crecs, "pt_s"), st(crecs, "pt_v"), st(crecs, "At_s"),
                                st(crecs, "At_v"), st(crecs, "V_s"), st(crecs, "V_v"), Tc).numpy()
        c10r = l10.ln_gamma_inf(st(crecs, "pt_s"), st(crecs, "pt_v"), st(crecs, "At_s"),
                                st(crecs, "At_v"), None, None, Tc).numpy()
    cm = np.array([r["m"] for r in crecs])
    csu = np.array([r["su"] for r in crecs]); csv_ = np.array([r["sv"] for r in crecs])
    corner_conv = {"n": int(len(cm)), "var_m": round(float(cm.var(ddof=0)), 4)}
    for kern, cg in (("2010", {"full": c10f, "res": c10r}),
                     ("2002", {"full": c02f, "res": c02r})):
        for cname, g in cg.items():
            mse = float(np.mean((g - cm) ** 2))
            b = lotv(g, cm, 8, 1)
            P2, ci2 = two_way_margin(g, cm, csu, csv_, 8, 1)
            cells = {}
            for nb in (6, 8, 10, 12, 16):
                for ddof, lab in ((0, "ML"), (1, "Bessel")):
                    bb = lotv(g, cm, nb, ddof)
                    cells[f"{nb}bins_{lab}"] = {"b_insuff_up": round(bb, 4),
                                                "margin": round(mse - 2 * bb, 4)}
            corner_conv[f"{kern}_{cname}"] = {
                "mse": round(mse, 4), "b_insuff_up_8bins_Bessel": round(b, 4),
                "b_clos_lb": round(mse - b, 4), "margin": round(mse - 2 * b, 4),
                "P_two_way_solute_x_solvent": round(P2, 3),
                "ci90_two_way": [round(c, 3) for c in ci2],
                "bin_grid": cells,
                "min_margin_over_bin_grid": min(c["margin"] for c in cells.values()),
                "max_margin_over_bin_grid": max(c["margin"] for c in cells.values()),
            }
            print(f"[corner {kern} {cname}] mse {mse:.4f} b {b:.4f} "
                  f"margin {mse - 2*b:+.4f} P2={P2:.3f}", flush=True)
    out["corner_by_convention_8bins_Bessel"] = corner_conv

    # ---------------------------------------------------- (R3-7) the pair-conditional bound
    multi = np.array([Counter(pair)[p] > 1 for p in pair])
    tot, mass = 0.0, 0
    for p in np.unique(pair[multi]):
        mm = m[pair == p]
        tot += len(mm) * float(mm.var(ddof=1))
        mass += len(mm)
    pair_bound = tot / mass
    b_lotv_multi = lotv(g02r[multi], m[multi], 8, 1)
    b_lotv_multi_full = lotv(g02f[multi], m[multi], 8, 1)
    # source homogeneity of the multi-row pairs
    doi_by_pair = defaultdict(set)
    for p, d in zip(pair, doi):
        doi_by_pair[p].add(d)
    multi_pairs = [p for p in np.unique(pair) if Counter(pair)[p] > 1]
    single_doi = sum(len(doi_by_pair[p]) == 1 for p in multi_pairs)
    out["pair_conditional_bound"] = {
        "n_rows_in_multirow_pairs": int(mass),
        "n_multirow_pairs": len(multi_pairs),
        "E_Var_m_given_pair_on_those_rows": round(pair_bound, 4),
        "lotv_8bins_Bessel_on_those_same_rows_res": round(b_lotv_multi, 4),
        "lotv_8bins_Bessel_on_those_same_rows_full": round(b_lotv_multi_full, 4),
        "ratio_lotv_over_pair_res": round(b_lotv_multi / pair_bound, 1),
        "n_multirow_pairs_from_a_single_doi": int(single_doi),
        "share_multirow_pairs_single_doi": round(single_doi / len(multi_pairs), 3),
        "mse_res_on_those_rows": round(float(np.mean((g02r[multi] - m[multi]) ** 2)), 4),
        "margin_res_on_those_rows_with_pair_bound": round(
            float(np.mean((g02r[multi] - m[multi]) ** 2)) - 2 * pair_bound, 4),
    }
    print(f"[pair] bound {pair_bound:.4f} vs lotv {b_lotv_multi:.4f}; "
          f"{single_doi}/{len(multi_pairs)} single-DOI", flush=True)

    # ---------------------------------------------------- (R3-8) typed-latent dimension
    n_corner_pairs = int(len(cset))
    out["typed_latent_dimension"] = {
        "bins_per_molecule_typed": 153,
        "dim_zstar_typed_pair": 306,
        "representative": {
            "dim_zstar_plus_T": 307, "n_rows": len(m),
            "dim_over_n_rows": round(307 / len(m), 2),
            "n_distinct_pairs": int(len(set(pair))),
            "dim_over_n_distinct_pairs": round(307 / len(set(pair)), 2),
        },
        "corner": {
            "dim_zstar": 306, "note": "all rows at 298 K, so T adds no dimension",
            "n_rows": 60, "dim_over_n_rows": round(306 / 60, 2),
            "n_distinct_pairs": 60, "dim_over_n_distinct_pairs": round(306 / 60, 2),
        },
        "untyped_2002_for_comparison": {
            "representative_dim_over_n_rows": round(103 / len(m), 2),
            "representative_dim_over_n_distinct_pairs": round(103 / len(set(pair)), 2),
            "corner_dim_over_n_rows": round(102 / 60, 2),
        },
    }

    # ---------------------------------------------------- (R1-24) deposited row tables
    TAB_REP.parent.mkdir(parents=True, exist_ok=True)
    pid = {p: i + 1 for i, p in enumerate(sorted(set(pair)))}
    rep_tab = pd.DataFrame({
        "pair_id": [pid[p] for p in pair],
        "solute_smiles": [r["solute_smiles"] for r in flat],
        "solvent_smiles": [r["solvent_smiles"] for r in flat],
        "solute_ud_key": su, "solvent_ud_key": sv,
        "match_rule_solute": [r["su_rule"] for r in flat],
        "match_rule_solvent": [r["sv_rule"] for r in flat],
        "T_K": Ts, "m_ln_gamma_inf": m,
        "g_2002_full": g02f, "g_2002_res": g02r,
        "g_2010_dsp_off_full": g10f, "g_2010_dsp_off_res": g10r,
        "method": method, "source_doi": doi,
        "journal": [r["journal"] for r in flat],
        "in_corner_57": shared,
    }).sort_values(["pair_id", "T_K"])
    rep_tab.to_csv(TAB_REP, index=False)
    cor_tab = corner_provenance(corner.copy())
    cor_tab["pair_id"] = range(1, len(cor_tab) + 1)
    cor_tab["in_broad_idac_set"] = [cres[(a, b)] in present
                                    for a, b in zip(cor_tab.solute_key, cor_tab.solvent_key)]
    for col, vals in (("g_2002_full_UD", c02f), ("g_2002_res_UD", c02r),
                      ("g_2010_dsp_off_full_UD", c10f), ("g_2010_dsp_off_res_UD", c10r)):
        s = pd.Series(np.nan, index=cor_tab.index, dtype=float)
        s.loc[crows] = vals
        cor_tab[col] = s.to_numpy()
    cor_tab.to_csv(TAB_COR, index=False)
    out["deposited_tables"] = {"broad_idac": str(TAB_REP.relative_to(ROOT)),
                              "corner": str(TAB_COR.relative_to(ROOT)),
                              "broad_idac_rows": len(rep_tab), "corner_rows": len(cor_tab)}

    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "representative_grid"}, indent=2))
    print(f"[saved] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
