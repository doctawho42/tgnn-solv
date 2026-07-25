#!/usr/bin/env python
"""Calibrate rho against molecule-blind controls on the n=44 matched VT-2005 set.

A decision threshold on rho only means something if trivial predictors score WORSE
than it. This computes the reference ladder: a leave-one-out corpus-mean profile
(zero molecular information), the true profile of a randomly permuted molecule, and
a uniform profile -- using the committed metric and the committed n=44 selection
path from fix_g_rho_eval.py.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/experiments/rho_control_ladder.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts" / "analysis"))

from run_compensation_surrogate import _canon, load_true_shapes  # noqa: E402


def rho_dataset(sig_hat: np.ndarray, sig_true: np.ndarray) -> float:
    """The committed `rel_deviation`: mean||r|| / mean||ref||."""
    num = np.linalg.norm(sig_hat - sig_true, axis=1).mean()
    den = np.linalg.norm(sig_true, axis=1).mean() + 1e-12
    return float(num / den)


def load_matched_true(sigma_csv: str, matched_csv: str) -> np.ndarray:
    """Rebuild the exact n=44 true-profile matrix used by fix_g_rho_eval.py."""
    true = load_true_shapes(sigma_csv)
    md = pd.read_csv(matched_csv, low_memory=False)
    mols: set[str] = set()
    for col in ("solute_key", "solvent_key"):
        if col in md.columns:
            mols |= set(md[col].dropna().astype(str))
    keep = [(s, _canon(s)) for s in sorted(mols)]
    keep = [(s, c) for s, c in keep if c is not None and c in true]
    return np.stack([true[c] for _, c in keep])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sigma-profiles", default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    ap.add_argument("--perm-seeds", type=int, default=5)
    args = ap.parse_args()

    sig_true = load_matched_true(args.sigma_profiles, args.matched_csv)
    n, nbins = sig_true.shape
    print(f"n = {n}, bins = {nbins}, rowsum = "
          f"{sig_true.sum(1).min():.12f} .. {sig_true.sum(1).max():.12f}\n")

    loo = np.stack([np.delete(sig_true, i, axis=0).mean(0) for i in range(n)])
    rho_loo = rho_dataset(loo, sig_true)

    perm = []
    for seed in range(args.perm_seeds):
        rng = np.random.default_rng(seed)
        idx = rng.permutation(n)
        while np.any(idx == np.arange(n)):  # derangement
            idx = rng.permutation(n)
        perm.append(rho_dataset(sig_true[idx], sig_true))

    flat = np.full_like(sig_true, 1.0 / nbins)

    print("CONTROL LADDER (rho)")
    print(f"  leave-one-out corpus mean (molecule-blind) : {rho_loo:.4f}")
    print(f"  true profile of the WRONG molecule         : {min(perm):.4f} .. {max(perm):.4f}")
    print(f"  uniform flat profile                       : {rho_dataset(flat, sig_true):.4f}")
    print()
    print(f"pre-registered decision band [0.46, 0.50] contains the molecule-blind "
          f"constant ({rho_loo:.4f})? -> {0.46 <= rho_loo <= 0.50}")


if __name__ == "__main__":
    main()
