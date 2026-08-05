#!/usr/bin/env python3
"""What the pKa insufficiency bound conditions on, and what it costs to get that wrong.

Lemma `decomp' requires z* to be the closure's ENTIRE argument.  The Hammett closure
g = pKa0(s) - rho(s) * sigma_H reads two things: the reaction series s (which selects the
literature constant pair) and the substituent constant sigma_H.  So z* = (s, sigma_H), and
B_insuff = E[Var(pKa | s, sigma_H)].  That is what run_pka_real_decomposition.py estimates --
`_binsuff_within_scaffold' fits the regressor WITHIN each series and pools by n -- and the
regressor is therefore sigma(s, sigma_H)-measurable, which is what makes the decomposition
exact for it.

This script prints that estimate beside the one a reader might assume from the phrase "the
latent is a scalar": the same out-of-fold random forest with the series POOLED, conditioning
on sigma_H alone.  Two things follow from the contrast, and both are stated in the manuscript:

  * conditioning on s is not a free choice -- with s pooled, g is not measurable with respect
    to the conditioning variable and Lemma `decomp' does not license the split at all; and
  * it is not the conservative choice either -- pooled, the bound exceeds the pole's own MSE
    and the closure floor it leaves is vacuous.

Numbers printed here appear in section 3.5 of the article and in the pKa SI section.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_pka_binsuff_conditioning_check.py
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
from rdkit import Chem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

ROOT = Path(__file__).resolve().parents[2]
SDF = ROOT / "notebooks" / "data" / "raw" / "pKa_QR.sdf"


def _load_decomposition():
    path = ROOT / "scripts" / "analysis" / "run_pka_real_decomposition.py"
    spec = importlib.util.spec_from_file_location("pka_decomp", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _net_charged(smiles: str) -> bool:
    mol = Chem.MolFromSmiles(str(smiles))
    return mol is None or Chem.GetFormalCharge(mol) != 0


def main() -> None:
    dec = _load_decomposition()
    recs, n_read = dec.load_records(SDF, dec._load_builder())
    kept = [r for r in recs if not _net_charged(r["smiles"])]   # the uniform net-neutral QC
    print(f"read {n_read} -> Hammett-amenable {len(recs)} -> after net-charge QC {len(kept)}")

    poles = (("clean  (meta/para, all substituents tabulated)", "high_F"),
             ("degraded (an ortho or untabulated position)   ", "low_F"))
    for label, key in poles:
        rs = [r for r in kept if r["bin"] == key]
        m = np.array([r["pka"] for r in rs], float)
        g = np.array([r["g"] for r in rs], float)
        mse = float(np.mean((m - g) ** 2))

        # z* = (s, sigma_H): the closure's entire argument -- the manuscript's estimator.
        within = dec._binsuff_within_scaffold(rs)
        # sigma_H alone: series pooled.  g is not measurable w.r.t. this, so the split is
        # unlicensed; printed only to show what the omission would cost.
        sig = np.array([r["sigma"] for r in rs], float).reshape(-1, 1)
        pooled = dec._oof_mse(sig, m)

        print(f"\n=== {label}  n={len(rs)} ===")
        print(f"  MSE = {mse:.3f}   (RMSE {mse ** 0.5:.3f})")
        print(f"  B_insuff^up | (s, sigma_H)  = {within:.3f}   -> B_clos floor {mse - within:+.3f}")
        print(f"  B_insuff^up | sigma_H alone = {pooled:.3f}   -> B_clos floor {mse - pooled:+.3f}"
              f"{'   [vacuous]' if pooled >= mse else ''}")


if __name__ == "__main__":
    main()
