"""De-risk test for the 'closure-geometry governs learned-latent trustworthiness' program
(ideation top-pick: observable_design / physical_locus). The T0.5 measurement showed the real
COSMO-SAC closure is a DEGENERATE rank-1 bottleneck -- adding solvent/temperature channels did NOT
raise the rank. The whole new program hinges on whether that is universal or whether a NON-degenerate
closure exists where adding observables raises the closure Jacobian rank (so observable-design can
make a learned latent identifiable). This script builds a controllable non-COSMO closure and tests it.

Closure: 1-D steady diffusion  -d/dx(D(x) du/dx) = f0,  Dirichlet u(0)=u(1)=0.
Latent: the diffusion-coefficient field D(x) = softplus(z), z in R^{n_edge} (positive, differentiable).
Forward: assemble stiffness A(D), solve u = A^{-1} f0, observe y = u[sensors] (K sensors).
The closure z -> y is NONLINEAR (D enters the operator) and its Jacobian dy/dz is INPUT-DEPENDENT
(the per-input null bundle the synthesis flagged as the genuine object vs a single global active subspace).

Panels (staged; cheapest-decisive first):
  Panel 1 (FREE, no training): rank / spectrum of the closure Jacobian vs K (# sensors). Does the
          constrained rank TRACK K (non-degenerate -> observable-design can work) or SATURATE like
          COSMO-SAC's rank-1? This is the make-or-break generalization de-risk.
  Panel 2 (training): does the DATA-AGNOSTIC closure spectrum predict per-direction recovery of the
          true field by a trained latent-through-closure model?
  Panel 3 (causal intervention): add a sensor predicted (from the closure alone) to span a currently-
          null field direction -> recovery collapses there, while a cost-matched already-observed
          sensor does not. The differential intervention is the non-tautological move.

All CPU, minutes. No rdkit.
"""
from __future__ import annotations

import argparse
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import torch

torch.set_default_dtype(torch.float64)


def stiffness(D_edge, h):
    """Tridiagonal FE/FV stiffness for -d/dx(D du/dx) on n interior nodes.
    D_edge: (..., n+1) diffusivity at the n+1 edges between nodes/boundaries."""
    n = D_edge.shape[-1] - 1
    dl = D_edge[..., :-1]     # left edges  (n,)
    dr = D_edge[..., 1:]      # right edges (n,)
    main = (dl + dr) / h ** 2
    off = -dr[..., :-1] / h ** 2
    A = torch.diag_embed(main) + torch.diag_embed(off, offset=1) + torch.diag_embed(off, offset=-1)
    return A


def solve_u(z, f0, h):
    """z: (..., n+1) log-diffusivity -> u: (..., n) at interior nodes."""
    D = torch.nn.functional.softplus(z) + 1e-3
    A = stiffness(D, h)
    u = torch.linalg.solve(A, f0.expand(*z.shape[:-1], f0.shape[-1]).unsqueeze(-1)).squeeze(-1)
    return u


def closure_y(z, sensors, f0, h):
    return solve_u(z, f0, h)[..., sensors]


def jac(z, sensors, f0, h):
    """Closure Jacobian dy/dz at a single z (K x (n+1)), via autograd."""
    zc = z.clone().detach().requires_grad_(True)
    y = closure_y(zc, sensors, f0, h)                 # (K,)
    J = torch.zeros(y.shape[0], z.shape[-1])
    for k in range(y.shape[0]):
        g, = torch.autograd.grad(y[k], zc, retain_graph=True)
        J[k] = g
    return J


def eff_rank(sv):
    """Participation ratio of singular values^2 (a smooth effective rank)."""
    s2 = sv ** 2
    return float((s2.sum() ** 2) / (s2 ** 2).sum())


def place_sensors(n, K):
    """K sensors placed as evenly as possible among n interior nodes."""
    return np.linspace(0, n - 1, K).round().astype(int)


def ref_fields(n_edge, n_fields, rng):
    """Smooth positive log-diffusivity fields (the 'molecules' of this testbed)."""
    xs = np.linspace(0, 1, n_edge)
    Z = []
    for _ in range(n_fields):
        z = np.zeros(n_edge)
        for kf in range(1, 5):
            z += rng.normal() / kf * np.sin(np.pi * kf * xs + rng.uniform(0, np.pi))
        Z.append(z)
    return torch.tensor(np.array(Z))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", type=int, default=1)
    args = ap.parse_args()

    n = 31                       # interior nodes
    n_edge = n + 1               # diffusivity dofs (the latent dim)
    h = 1.0 / (n + 1)
    f0 = torch.ones(n)           # unit source
    rng = np.random.default_rng(0)
    K_grid = [1, 2, 4, 8, 16, 24]

    print(f"# Closure-geometry PDE de-risk  n_edge(latent)={n_edge}  (1-D diffusion, K-sensor knob)\n")

    # ---------- Panel 1: rank vs K (free) ----------
    print("## Panel 1: closure-Jacobian rank vs #sensors K  (does rank TRACK K, unlike COSMO rank-1?)")
    print(f"{'K':>3} | {'eff.rank(J)':>12} | {'top singular values (norm)':>34}")
    print("-" * 56)
    fields = ref_fields(n_edge, 12, rng)
    for K in K_grid:
        sensors = place_sensors(n, K)
        ranks, spec = [], None
        for z in fields:
            J = jac(z, sensors, f0, h)
            sv = torch.linalg.svdvals(J)
            ranks.append(eff_rank(sv))
            if spec is None:
                spec = (sv / sv[0]).detach().numpy()
        er = float(np.mean(ranks))
        show = np.round(spec[:min(6, len(spec))], 3)
        print(f"{K:>3} | {er:>12.2f} | {str(show):>34}")
    print("\n  Contrast: real COSMO-SAC stayed eff.rank ~1.0 even aggregating 96 solvent/T channels.")
    print("  If PDE eff.rank tracks K here, observable-design generalizes past COSMO's degenerate rank-1.")


if __name__ == "__main__":
    main()
