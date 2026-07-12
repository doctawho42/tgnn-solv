#!/usr/bin/env python3
"""Closure/insufficiency decomposition on REAL experimental pKa (OPERA/Mansouri 2019).

Phase-3 second-domain measurement. Upgrades the paper's pKa point from an illustrative
overshoot (two molecules) + semi-synthetic validation to a decomposition measured on a
real experimental dataset, exactly mirroring the solubility keystone (Lemma 3):

    E[(m - g(z*))^2]  =  B_insuff  +  B_closure
    m       = experimental pKa (pKa_a for acid scaffolds, pKa_b for base scaffolds)
    z*      = the Hammett substituent constant sigma_total (meta/para additive)
    g(z*)   = the FIXED Hammett LFER  pKa0 - rho * sigma_total  (Hansch-Leo-Taft constants)

We reuse assign_hammett_sigma() from the data builder so the Hammett assignment is identical
to the one the paper's parser self-test (7/7) validates. Reported per fidelity bin:
  high_F (meta/para only, all substituents known) -- the near-exact LFER regime
  low_F  (ortho / unknown substituent)            -- ortho field effects the sigma cannot carry

Bounds, not a point split (a fitted E[m|z*] makes the cross term non-zero, exactly as in
the solubility case). We report:
  * MSE_closure = E[(m - g(z*))^2]                      (true-input path error)
  * B_insuff  <= out-of-fold RF/kNN MSE of m ~ sigma    (input insufficiency upper bound)
  * B_closure >= MSE_closure - B_insuff^up              (convention-independent lower bound)
  * B_closure >= (E[m] - E[g])^2 per scaffold           (Jensen; systematic offset)

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_pka_real_decomposition.py \
        --sdf <path>/pKa_QR.sdf --out-json results/pka_hammett/real_decomposition.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
from rdkit import Chem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

ACID_SCAFFOLDS = {"benzoic_acid", "phenol"}
BASE_SCAFFOLDS = {"anilinium", "pyridinium"}


def _load_builder():
    """Import assign_hammett_sigma from the data builder without a package install."""
    here = Path(__file__).resolve().parents[1]
    path = here / "data" / "build_pka_hammett_subset.py"
    spec = importlib.util.spec_from_file_location("pka_builder", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.assign_hammett_sigma


def _fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


_AROM_N = Chem.MolFromSmarts("[n]")
_N_OXIDE = Chem.MolFromSmarts("[n]-[O]")


def _ring_clean(smiles: str, scaffold: str) -> bool:
    """Reject heteroaromatic mismatches: the parser can label an aminopyridine as 'anilinium'
    or a pyridinecarboxylic acid as 'benzoic_acid'. Require a genuine benzene ring for the
    carbon-ring scaffolds, and a clean (non-N-oxide, single-N) pyridine for pyridinium."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    if scaffold in ("benzoic_acid", "phenol", "anilinium"):
        return not mol.HasSubstructMatch(_AROM_N)          # must be benzene, not heteroaromatic
    if scaffold == "pyridinium":
        return (len(mol.GetSubstructMatches(_AROM_N)) == 1
                and not mol.HasSubstructMatch(_N_OXIDE))
    return True


def load_records(sdf_path: Path, assign):
    supp = Chem.SDMolSupplier(str(sdf_path))
    recs = []
    n_read = 0
    for mol in supp:
        if mol is None:
            continue
        n_read += 1
        props = mol.GetPropsAsDict()
        # neutral form for the Hammett parser; QSAR-ready SMILES carry explicit charges/N-oxides
        smi = props.get("Original_SMILES") or props.get("Canonical_QSARr")
        if not smi:
            smi = Chem.MolToSmiles(mol)
        smi = max(smi.split("."), key=len)                  # largest fragment (desalt)
        rec = assign(smi)
        if rec is None:
            continue
        if not _ring_clean(smi, rec["scaffold"]):
            continue
        if rec["scaffold"] in ACID_SCAFFOLDS:
            pka = _fnum(props.get("pKa_a"))
        elif rec["scaffold"] in BASE_SCAFFOLDS:
            pka = _fnum(props.get("pKa_b"))
        else:
            continue
        if pka is None:
            continue
        g = rec["pka0"] - rec["rho"] * rec["sigma_total"]
        recs.append(dict(smiles=smi, scaffold=rec["scaffold"], sigma=rec["sigma_total"],
                         pka0=rec["pka0"], rho=rec["rho"],
                         g=g, pka=pka, bin=rec["fidelity_bin"], has_ortho=rec["has_ortho"],
                         n_sub=rec["n_sub"]))
    return recs, n_read


def _oof_mse(X: np.ndarray, m: np.ndarray, seed: int = 0):
    """Out-of-fold RF MSE (an upper bound on E[Var(m | X))])."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import KFold
    if len(m) < 20:
        return float(np.var(m))
    oof = np.zeros_like(m)
    kf = KFold(n_splits=5, shuffle=True, random_state=seed)
    for tr, te in kf.split(X):
        rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=seed)
        rf.fit(X[tr], m[tr])
        oof[te] = rf.predict(X[te])
    return float(np.mean((m - oof) ** 2))


def _binsuff_within_scaffold(recs, seed: int = 0):
    """E[Var(pKa | scaffold, sigma)] upper bound: regress pKa~sigma WITHIN each scaffold and
    pool weighted by n. Pooling across scaffolds would fold the different pKa0's into the
    'unresolved' variance and inflate B_insuff, which is wrong -- pKa0 is part of z*."""
    tot, n = 0.0, 0
    for scaf in sorted({r["scaffold"] for r in recs}):
        idx = [i for i, r in enumerate(recs) if r["scaffold"] == scaf]
        if len(idx) < 8:
            continue
        sig = np.array([recs[i]["sigma"] for i in idx], float).reshape(-1, 1)
        m = np.array([recs[i]["pka"] for i in idx], float)
        tot += _oof_mse(sig, m, seed) * len(idx)
        n += len(idx)
    return (tot / n) if n else None


def decompose(recs, label: str):
    if not recs:
        return {"label": label, "n": 0}
    m = np.array([r["pka"] for r in recs], float)
    g = np.array([r["g"] for r in recs], float)
    resid = g - m
    mse = float(np.mean(resid ** 2))
    binsuff = _binsuff_within_scaffold(recs)
    bclos_lb = (mse - binsuff) if binsuff is not None else None
    per_scaffold = {}
    jensen = {}
    for scaf in sorted({r["scaffold"] for r in recs}):
        idx = [i for i, r in enumerate(recs) if r["scaffold"] == scaf]
        if len(idx) >= 5:
            rr = resid[idx]
            per_scaffold[scaf] = {"n": len(idx), "rmse": round(float(np.sqrt(np.mean(rr ** 2))), 3),
                                  "mean_resid": round(float(np.mean(rr)), 3)}
            jensen[scaf] = round(float(np.mean(rr) ** 2), 4)
    return {
        "label": label, "n": len(recs),
        "mse_true_input": round(mse, 4),
        "rmse_true_input": round(math.sqrt(mse), 3),
        "binsuff_within_scaffold_up": None if binsuff is None else round(binsuff, 4),
        "bclosure_lb_conv_indep": None if bclos_lb is None else round(bclos_lb, 4),
        "bclosure_jensen_by_scaffold": jensen,
        "per_scaffold": per_scaffold,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdf", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=Path("results/pka_hammett/real_decomposition.json"))
    args = ap.parse_args()

    assign = _load_builder()
    recs, n_read = load_records(args.sdf, assign)
    hi = [r for r in recs if r["bin"] == "high_F"]
    lo = [r for r in recs if r["bin"] == "low_F"]
    hi_mono = [r for r in hi if r["n_sub"] == 1]   # canonical mono-substituted Hammett series

    out = {
        "source": "OPERA / Mansouri 2019 pKa_QR.sdf (experimental pKa_a/pKa_b)",
        "n_molecules_read": n_read,
        "n_hammett_amenable": len(recs),
        "high_F_mono": decompose(hi_mono, "high_F mono-substituted (canonical LFER)"),
        "high_F": decompose(hi, "high_F (meta/para, incl. poly-sub)"),
        "low_F": decompose(lo, "low_F (ortho / unknown)"),
        "all": decompose(recs, "all"),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2))

    def _fmt(d):
        return (f"n={d['n']:4d}  MSE={d.get('mse_true_input')}  RMSE={d.get('rmse_true_input')}  "
                f"B_insuff^up={d.get('binsuff_within_scaffold_up')}  "
                f"B_clos_lb={d.get('bclosure_lb_conv_indep')}")
    print(f"read {n_read} molecules -> {len(recs)} Hammett-amenable "
          f"({len(hi)} high_F [{len(hi_mono)} mono], {len(lo)} low_F)")
    for d in (out["high_F_mono"], out["high_F"], out["low_F"], out["all"]):
        print(f"  {d['label'][:38]:38s} {_fmt(d)}")
    print(f"  per-scaffold (high_F mono): {out['high_F_mono'].get('per_scaffold')}")
    # diagnostic: worst |residual| in the mono series (to catch bad pKa / additivity outliers)
    hi_mono_sorted = sorted(hi_mono, key=lambda r: abs(r["g"] - r["pka"]), reverse=True)
    print("  worst mono-series residuals (g - pKa):")
    for r in hi_mono_sorted[:8]:
        print(f"    {r['scaffold']:12s} sig={r['sigma']:+.2f} g={r['g']:5.2f} "
              f"pKa={r['pka']:5.2f} resid={r['g']-r['pka']:+.2f}  {r['smiles'][:44]}")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
