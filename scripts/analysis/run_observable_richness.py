#!/usr/bin/env python3
"""Law vs experiment-design: does a RICHER observable resolve more sigma-directions?

The paper's activity Fisher (rank ~1) observes ln gamma2 at ONE condition: infinite
dilution, ~298 K. This asks whether that rank-1 is intrinsic to the observable, or an
artifact of how little we measure. We keep the SAME solute-solvent pairs fixed (so we
isolate observable-richness from sample size) and enrich the CONDITIONS each pair is
observed at: finite mole fractions x2, and multiple temperatures T. All gradients are
exact autograd on the differentiable COSMO-SAC-2002 layer (the method that reproduced
PR=1.002), so there is no finite-difference floor.

  PR stays ~1 as conditions richen  -> deep law: activity carries one sigma-dimension.
  PR climbs with conditions         -> actionable: measuring more makes sigma readable.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_observable_richness.py
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import json

import numpy as np
import pandas as pd
import torch

from tgnn_solv.layers import CosmoSacLayer


def pr(I: np.ndarray) -> float:
    lam = np.clip(np.linalg.eigvalsh(I), 0.0, None)
    s = float(lam.sum())
    return float(s * s / (np.square(lam).sum() + 1e-300)) if s > 0 else 0.0


def main() -> None:
    df = pd.read_csv("results/sigma_profile_artifact/sigma_profiles.csv")
    cols = [f"sigma_p_{i}" for i in range(51)]
    P = torch.tensor(df[cols].to_numpy(), dtype=torch.float32)
    A = torch.tensor(df["sigma_area"].to_numpy(), dtype=torch.float32)
    rng = np.random.default_rng(0)
    idx = rng.permutation(len(df))
    n_sol, n_slv = 30, 15
    pairs = [(int(s), int(v)) for s in idx[:n_sol] for v in idx[n_sol:n_sol + n_slv] if s != v]
    si = [s for s, _ in pairs]; vi = [v for _, v in pairs]
    p2, A2 = P[si].clone(), A[si]
    p1, A1 = P[vi].clone(), A[vi]
    B = len(pairs)
    layer = CosmoSacLayer(cfg=None).eval()
    n_iter = layer.n_iter_eval

    def grad_at(x2: float, T: float) -> np.ndarray:
        """Exact autograd d ln gamma2_res / d p2 for every pair at (x2, T). Shape (B,51)."""
        p2a = p2.clone().requires_grad_(True)
        lng = layer._residual_ln_gamma2(
            p2a, p1, A2, A1, torch.full((B,), x2), torch.full((B,), T), n_iter=n_iter)
        return torch.autograd.grad(lng.sum(), p2a)[0].detach().numpy()

    # cache gradients on a condition grid, then aggregate different subsets
    X2 = [1e-8, 0.05, 0.1, 0.2, 0.4]
    TT = [278.15, 298.15, 323.15, 348.15]
    G = {(x, T): grad_at(x, T) for x in X2 for T in TT}

    def fisher_pr(x2s, Ts) -> dict:
        I = np.zeros((51, 51))
        for x in x2s:
            for T in Ts:
                g = G[(x, T)]
                I += g.T @ g
        lam = np.clip(np.linalg.eigvalsh(I), 0, None)[::-1]
        evr = (lam / lam.sum())
        return {"PR": pr(I), "top1": float(evr[0]), "top2": float(evr[:2].sum()),
                "top3": float(evr[:3].sum()), "n_cond": len(x2s) * len(Ts)}

    settings = [
        ("inf-dil, 1 T           ", [1e-8], [298.15]),
        ("inf-dil, 4 T           ", [1e-8], TT),
        ("5 x2,    1 T           ", X2, [298.15]),
        ("5 x2,    4 T           ", X2, TT),
    ]
    out = []
    print(f"VT-2005, {n_sol} solutes x {n_slv} solvents = {B} pairs (fixed); autograd on the 2002 layer\n")
    print(f"{'observable':<24}{'#cond':>6}{'PR':>8}{'top1':>8}{'top2':>8}{'top3':>8}")
    print("-" * 62)
    for name, xs, ts in settings:
        r = fisher_pr(xs, ts)
        out.append({"setting": name.strip(), **r})
        print(f"{name}{r['n_cond']:>6}{r['PR']:>8.3f}{r['top1']:>8.3f}{r['top2']:>8.3f}{r['top3']:>8.3f}")
    Path = __import__("pathlib").Path
    op = Path("results/compensation/observable_richness.json")
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {op}")


if __name__ == "__main__":
    main()
