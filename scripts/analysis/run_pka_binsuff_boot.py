#!/usr/bin/env python3
"""Bootstrap CIs for the QC'd pKa closure/insufficiency point split.

The point split (run_pka_real_decomposition, net-charge QC): per stratum,
  MSE       = mean_i (pKa_i - g_oracle_i)^2                     [reference-input error]
  B_insuff  = weighted within-scaffold out-of-fold RF MSE       [E[Var(pKa|scaffold,sigma)]]
  B_closure = MSE - B_insuff.
Re-fitting the RF inside every bootstrap resample is too slow, and the within-scaffold RF is
stable on the large ortho scaffolds (n=150-450), so we take the standard fast route: compute each
molecule's OOF residual ONCE, then resample molecules WITHIN each scaffold (stratified, preserving
scaffold sizes) over the precomputed per-molecule contributions. This is a molecule bootstrap of the
fitted within-scaffold estimator; it holds the point estimate fixed and reports its sampling CI.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_pka_binsuff_boot.py
"""
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import importlib.util
from pathlib import Path
import numpy as np
from rdkit import Chem
from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

ROOT = Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv")
spec = importlib.util.spec_from_file_location("m", ROOT / "scripts/analysis/run_pka_real_decomposition.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def net_charged(smi):
    mol = Chem.MolFromSmiles(str(smi))
    return mol is None or Chem.GetFormalCharge(mol) != 0


def oof_pred(sig, y, seed=0):
    """Per-sample out-of-fold RF prediction (same config as _oof_mse); var-fallback if tiny."""
    if len(y) < 20:
        return np.full_like(y, y.mean())
    oof = np.zeros_like(y)
    for tr, te in KFold(n_splits=5, shuffle=True, random_state=seed).split(sig):
        rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=seed)
        rf.fit(sig[tr], y[tr])
        oof[te] = rf.predict(sig[te])
    return oof


def per_molecule(recs):
    """Return arrays (insuff_contrib, closure_contrib, scaffold) over molecules in scaffolds n>=8."""
    ins, clo, scaf = [], [], []
    for s in sorted({r["scaffold"] for r in recs}):
        idx = [i for i, r in enumerate(recs) if r["scaffold"] == s]
        if len(idx) < 8:
            continue
        sig = np.array([recs[i]["sigma"] for i in idx], float).reshape(-1, 1)
        y = np.array([recs[i]["pka"] for i in idx], float)
        g = np.array([recs[i]["g"] for i in idx], float)
        pred = oof_pred(sig, y)
        ins += list((y - pred) ** 2)
        clo += list((y - g) ** 2)
        scaf += [s] * len(idx)
    return np.array(ins), np.array(clo), np.array(scaf)


def strat_boot(ins, clo, scaf, B=4000, seed=0):
    rng = np.random.default_rng(seed)
    uniq = np.unique(scaf)
    idx_by = {s: np.where(scaf == s)[0] for s in uniq}
    bi, bc = [], []
    for _ in range(B):
        rows = np.concatenate([idx_by[s][rng.integers(0, len(idx_by[s]), len(idx_by[s]))] for s in uniq])
        bi.append(ins[rows].mean())
        bc.append(clo[rows].mean() - ins[rows].mean())
    return np.array(bi), np.array(bc)


recs, _ = m.load_records(ROOT / "notebooks/data/raw/pKa_QR.sdf", m._load_builder())
kept = [r for r in recs if not net_charged(r["smiles"])]
print(f"records {len(recs)} -> kept {len(kept)}")

for binname, label in [("low_F", "ortho/hetero"), ("high_F", "meta/para (clean)")]:
    sub = [r for r in kept if r.get("bin") == binname]
    ins, clo, scaf = per_molecule(sub)
    B_insuff, MSE = float(ins.mean()), float(clo.mean())
    B_closure = MSE - B_insuff
    bi, bc = strat_boot(ins, clo, scaf)
    print(f"\n=== {label}: n={len(sub)} (in-scaffold {len(ins)}) ===")
    print(f"  MSE={MSE:.3f}  B_insuff={B_insuff:.3f}  B_closure={B_closure:.3f}  ({100*B_insuff/MSE:.0f}% insuff)")
    print(f"  B_insuff  95% CI [{np.percentile(bi,2.5):.2f}, {np.percentile(bi,97.5):.2f}]")
    print(f"  B_closure 95% CI [{np.percentile(bc,2.5):.2f}, {np.percentile(bc,97.5):.2f}]  "
          f"P(B_closure>0)={float((bc>0).mean()):.3f}")
