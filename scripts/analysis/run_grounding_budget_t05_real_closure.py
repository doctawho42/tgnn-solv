"""T0.5 kill-test on the REAL COSMO-SAC closure.

Concept note: reports/CONCEPT_grounding_budget_2026-07-15.md. T0 (synthetic) confirmed the H1
label-selection mechanism *in principle*. T0.5 asks the make-or-break real-data question:

  Does the real COSMO-SAC closure (CosmoSacLayer, exact, zero learnable params) have an
  approximately (1) LOW-DIMENSIONAL and (2) GLOBAL (molecule-independent) ill-constrained
  subspace of the sigma-profile -> ln gamma map?

If yes: a small, universal anchor basis pins the compensation for every molecule -> the program's
"grounding budget" is cheap and the law is real on real data. If the ill-constrained subspace is
high-dimensional OR strongly molecule-dependent: anchoring degenerates to "label everything" and
the program is falsified on the real closure.

Method (no checkpoint needed -- the closure is parameter-free). For real VT-2005 sigma-profiles
(results/sigma_profile_artifact/sigma_profiles.csv, 1432 molecules), evaluate the Jacobian
g = d ln gamma_inf / d p2 (solute profile, area held fixed) via autograd, across many solvent
contexts x temperatures. Two panels:

  Panel 1  GLOBAL Fisher  G = mean_k g_k g_k^T  over all contexts. Its eigenspectrum: the LARGE
           eigenvalues are well-constrained profile directions; the SMALL-eigenvalue tail is the
           ill-constrained (compensation-prone) subspace. Report its effective size.
  Panel 2  PER-SOLUTE ill-constrained subspace (bottom-m eigenvectors of the per-solute Fisher over
           that solute's contexts) and the cross-solute ALIGNMENT (mean subspace overlap), vs a
           random-subspace null. High alignment = global basis exists.

Pre-registered reading:
  - "low-dim": the ill-constrained subspace carrying the compensation should be a modest fraction of
    the 51 bins (say <= ~15) rather than most of them.
  - "global": mean cross-solute overlap of the bottom-m subspaces must clearly exceed the random
    null (m/51) -- otherwise no cheap universal basis.

All CPU, minutes.
"""
from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch

from tgnn_solv.layers import CosmoSacLayer

CSV = "results/sigma_profile_artifact/sigma_profiles.csv"
N_SOLUTE = 100
N_SOLV = 48
TS = (298.15, 330.0)
SEED = 0


def load_profiles():
    df = pd.read_csv(CSV)
    bincols = [f"sigma_p_{i}" for i in range(51)]
    P = torch.tensor(df[bincols].to_numpy(), dtype=torch.float32)
    A = torch.tensor(df["sigma_area"].to_numpy(), dtype=torch.float32)
    V = torch.tensor(df["v_cosmo"].to_numpy(), dtype=torch.float32)
    return P, A, V, df["smiles"].tolist()


def solute_gradients(clo, P, A, V, si, solv_idx, T):
    """Rows = d ln gamma_inf(solute si in each solvent) / d p2, area held fixed."""
    n = len(solv_idx)
    p2 = P[si].repeat(n, 1).clone().detach().requires_grad_(True)
    A2 = A[si].repeat(n)
    V2 = V[si].repeat(n)
    p1, A1, V1 = P[solv_idx], A[solv_idx], V[solv_idx]
    Tt = torch.full((n,), float(T))
    lng = clo.ln_gamma_inf(p2, p1, A2, A1, V2, V1, Tt)
    mask = lng.detach().abs() < 49.0            # drop clamp-saturated contexts
    lng.sum().backward()
    g = p2.grad.detach()
    return g[mask]


def subspace_overlap(U, W):
    """Mean captured energy of one m-dim orthobasis by another: ||U^T W||_F^2 / m in [0,1]."""
    m = U.shape[1]
    return float((U.t() @ W).pow(2).sum() / m)


def bottom_m(Gs, m):
    evals, evecs = torch.linalg.eigh(Gs)          # ascending
    return evecs[:, :m]                           # smallest-eigenvalue subspace


def main():
    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)
    P, A, V, smiles = load_profiles()
    Nmol = P.shape[0]
    clo = CosmoSacLayer()
    clo.eval()
    print(f"# T0.5 real COSMO-SAC closure  n_mol={Nmol} probes={N_SOLUTE} solv/ctx={N_SOLV} "
          f"T={TS}  (51 sigma bins)\n")

    solute_idx = rng.choice(Nmol, N_SOLUTE, replace=False)
    per_solute_G = []
    all_g = []
    for si in solute_idx:
        gs = []
        solv_idx = rng.choice(Nmol, N_SOLV, replace=False)
        for T in TS:
            g = solute_gradients(clo, P, A, V, int(si), solv_idx, T)
            if g.shape[0] > 0:
                gs.append(g)
        if not gs:
            continue
        gs = torch.cat(gs, 0)
        per_solute_G.append(gs.t() @ gs / gs.shape[0])
        all_g.append(gs)
    allg = torch.cat(all_g, 0)
    G = allg.t() @ allg / allg.shape[0]

    # ---------- Panel 1: global spectrum ----------
    evals = torch.linalg.eigvalsh(G).flip(0)      # descending
    ev = evals.clamp_min(0).numpy()
    tot = ev.sum()
    cum = np.cumsum(ev) / tot
    part_ratio = float((ev.sum() ** 2) / (ev ** 2).sum())   # participation ratio
    n_above_1pct = int((ev > 0.01 * ev[0]).sum())
    n_for_99 = int(np.searchsorted(cum, 0.99) + 1)
    n_for_999 = int(np.searchsorted(cum, 0.999) + 1)
    print("## Panel 1: global Fisher spectrum (of 51 profile directions)")
    print(f"  top-8 eigenvalues (norm): {np.round(ev[:8] / ev[0], 4)}")
    print(f"  participation ratio (eff. # well-constrained dirs): {part_ratio:.1f}")
    print(f"  # dirs > 1% of max:            {n_above_1pct}")
    print(f"  # dirs for 99% sensitivity:    {n_for_99}")
    print(f"  # dirs for 99.9% sensitivity:  {n_for_999}")
    ill = 51 - n_for_999
    print(f"  => ill-constrained tail (compensation-prone): ~{ill} / 51 directions "
          f"(anchor budget proxy)")

    # ---------- Panel 2: global-vs-local alignment ----------
    print("\n## Panel 2: per-solute ill-constrained subspace alignment (global?)")
    print(f"{'m':>3} | {'mean overlap':>13} | {'random null m/51':>17} | {'ratio vs null':>13}")
    print("-" * 56)
    for m in (3, 6, 10):
        subs = [bottom_m(Gs, m) for Gs in per_solute_G]
        # mean pairwise overlap over a random sample of pairs
        idx = list(range(len(subs)))
        pairs = [(rng.integers(len(subs)), rng.integers(len(subs))) for _ in range(600)]
        ov = [subspace_overlap(subs[i], subs[j]) for i, j in pairs if i != j]
        mo = float(np.mean(ov)); null = m / 51.0
        print(f"{m:>3} | {mo:>13.3f} | {null:>17.3f} | {mo / null:>12.2f}x")

    # also: alignment of each solute's bottom-m to the GLOBAL bottom-m
    print("\n  per-solute bottom-6 vs GLOBAL bottom-6 subspace:")
    _, gevec = torch.linalg.eigh(G)
    gbot = gevec[:, :6]
    ov_global = [subspace_overlap(bottom_m(Gs, 6), gbot) for Gs in per_solute_G]
    print(f"    mean overlap with global basis: {np.mean(ov_global):.3f} "
          f"(random null {6/51:.3f}) -> {np.mean(ov_global)/(6/51):.2f}x")

    print("\n## Read")
    print(f"  low-dim?  ill-constrained tail ~{ill}/51.  "
          f"{'YES (cheap budget)' if ill <= 15 else 'NO -- high-dim (expensive)'}")


if __name__ == "__main__":
    main()
