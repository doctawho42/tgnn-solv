#!/usr/bin/env python3
"""ANCHOR: does finite-difference d lngamma/d sigma match AUTOGRAD on the SAME
differentiable COSMO-SAC-2002 layer, same VT-2005 profiles, same area-per-bin
parameterization?

Adjudicates two things the cCOSMO-FD Fisher-rank (run_sigma_fisher_rank.py) left open:
  (1) Is finite differencing a valid instrument for the sigma-Fisher? -> autograd PR
      vs FD PR on the identical layer. If they match, FD is fine and the cCOSMO
      discrepancy is a 2002-implementation difference; if not, FD is the culprit.
  (2) Does the paper's PR~1.0 hold? -> autograd PR on VT-2005 (the paper's exact data
      and differentiable layer). ~1.0 confirms rank-1; ~2 means the headline is rank-2.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/anchor_sigma_fisher_autograd.py
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import numpy as np
import pandas as pd
import torch

from tgnn_solv.layers import CosmoSacLayer


def pr(I: np.ndarray) -> float:
    lam = np.clip(np.linalg.eigvalsh(I), 0.0, None)
    s = float(lam.sum())
    return float(s * s / (np.square(lam).sum() + 1e-300)) if s > 0 else 0.0


def area_preserving(I: np.ndarray) -> float:
    n = I.shape[0]
    u = np.ones(n) / np.sqrt(n)
    P = np.eye(n) - np.outer(u, u)
    return pr(P @ I @ P)


def main() -> None:
    df = pd.read_csv("results/sigma_profile_artifact/sigma_profiles.csv")
    cols = [f"sigma_p_{i}" for i in range(51)]
    P = torch.tensor(df[cols].to_numpy(), dtype=torch.float32)
    A = torch.tensor(df["sigma_area"].to_numpy(), dtype=torch.float32)
    N = len(df)
    rng = np.random.default_rng(0)
    idx = rng.permutation(N)
    n_sol, n_slv = 30, 15
    sol, slv = idx[:n_sol], idx[n_sol:n_sol + n_slv]
    pairs = [(int(s), int(v)) for s in sol for v in slv if s != v]

    layer = CosmoSacLayer(cfg=None).eval()
    n_iter = layer.n_iter_eval
    si = [s for s, _ in pairs]
    vi = [v for _, v in pairs]
    p2, A2 = P[si].clone(), A[si]
    p1, A1 = P[vi].clone(), A[vi]
    B = len(pairs)
    Tb = torch.full((B,), 298.15)
    x2b = torch.full((B,), 1e-8)

    # (1) exact autograd d lngamma2 / d p2  (per pair: lngamma2[i] depends only on p2[i])
    p2a = p2.clone().requires_grad_(True)
    lng = layer._residual_ln_gamma2(p2a, p1, A2, A1, x2b, Tb, n_iter=n_iter)
    g_ag = torch.autograd.grad(lng.sum(), p2a)[0].detach().numpy()

    # (2) central finite differences on the SAME layer, same 0.02 area step + clamp
    delta = 0.02
    g_fd = np.zeros((B, 51))
    with torch.no_grad():
        for j in range(51):
            pp = p2.clone(); pp[:, j] += delta
            pm = p2.clone(); pm[:, j] = torch.clamp(pm[:, j] - delta, min=0.0)
            lp = layer._residual_ln_gamma2(pp, p1, A2, A1, x2b, Tb, n_iter=n_iter).numpy()
            lm = layer._residual_ln_gamma2(pm, p1, A2, A1, x2b, Tb, n_iter=n_iter).numpy()
            g_fd[:, j] = (lp - lm) / (2.0 * delta)

    I_ag = g_ag.T @ g_ag
    I_fd = g_fd.T @ g_fd
    cos = np.sum(g_ag * g_fd, 1) / (np.linalg.norm(g_ag, axis=1) * np.linalg.norm(g_fd, axis=1) + 1e-12)

    print(f"VT-2005, {len(sol)} solutes x {len(slv)} solvents = {B} pairs, 51-bin single profile\n")
    print(f"  autograd   PR = {pr(I_ag):.3f}   (area-preserving {area_preserving(I_ag):.3f})")
    print(f"  finite-diff PR = {pr(I_fd):.3f}   (area-preserving {area_preserving(I_fd):.3f})")
    print(f"  median per-pair cos(autograd, FD) = {np.median(cos):.4f}")
    la = np.clip(np.linalg.eigvalsh(I_ag), 0, None)[::-1]
    print(f"  autograd top-5 eig / trace = {[round(float(v/la.sum()), 4) for v in la[:5]]}")


if __name__ == "__main__":
    main()
