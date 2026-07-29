"""T0-H2: a focused, robust kill-test for the CO-DESIGN claim (H2) of the Grounding-Budget concept.

Concept note: reports/CONCEPT_grounding_budget_2026-07-15.md
H1 (the null-space label-selection law) already passed in run_grounding_budget_t0_synthetic.py.
There, H2 was only directionally suggestive and high-variance. This script tests H2 cleanly.

H2 claim. With the gauge already anchored (k = ker_dim targeted labels in EVERY arm), under a
MISSPECIFIED closure the model still distorts the physical latent to fit y through the wrong closure.
A bounded ("capped") correction head absorbs the systematic O(eps) closure error so the latent stays
physical -- BUT the correction CAP must be co-sized with eps:
    cap too small  -> cannot absorb the closure error -> latent distorts (= anchor-only)
    cap ~ eps      -> absorbs exactly the systematic error -> latent recovers
    cap too large  -> correction also eats signal -> latent under-constrained -> drifts again
So the co-design signature is a U-SHAPE in latent-recovery error vs cap, with the optimum tracking eps.

Two decisive panels (robust: MEDIAN +/- IQR over many seeds; gradient clipping applied EQUALLY to all
arms so the test measures the mechanism, not optimizer blow-up):
  Panel A  eps-sweep, arms {anchor-only, anchor+firewall(fixed cap)}: firewall's advantage must GROW
           with eps (Delta-vs-baseline separates), else the firewall does nothing under misspecification.
  Panel B  cap-sweep at fixed eps: latent recovery must be U-shaped with a min at an intermediate cap
           (co-design), else "which cap" is irrelevant and H2's novel part is dead.

Pre-registered falsification:
  H2a  firewall Delta(eps) must be << anchor-only Delta(eps) at the largest eps (< 0.6x), else no effect.
  H2b  the best cap must beat BOTH cap=0 (anchor-only) AND the largest cap (< 0.8x each), i.e. a real
       interior optimum, else there is no co-design.

All CPU, minutes. No GNN, no rdkit.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import torch

torch.set_default_dtype(torch.float64)


@dataclass
class Cfg:
    d: int = 24
    ker_dim: int = 6
    n_train: int = 400
    n_test: int = 200
    n_pairs: int = 8000
    noise_y: float = 0.02
    noise_x: float = 0.05
    lam_label: float = 5.0
    epochs: int = 1000
    lr: float = 2e-2
    clip: float = 5.0
    seeds: tuple = tuple(range(8))
    eps_grid: tuple = (0.0, 0.05, 0.1, 0.2, 0.4)
    cap_grid: tuple = (0.0, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0)  # fractions of std(y); 0.0 = anchor-only
    eps_for_capsweep: float = 0.2
    mix_features: bool = False  # False => x = z* + noise (clean encoder baseline, isolates the O(eps) misspec effect)


def psi(z):
    return torch.tanh(z)


def make_closure(cfg, rng):
    di = cfg.d - cfg.ker_dim
    B = rng.standard_normal((di, di))
    K = B @ B.T / di + 0.5 * np.eye(di)
    eye = np.eye(cfg.d)
    return K, eye[:, di:], eye[:, :di], di          # K, ker_basis, range_basis, di


def energy(z_i, z_j, K, di):
    return (psi(z_i[..., :di]) * (psi(z_j[..., :di]) @ K)).sum(-1)


def fisher_targeted(K, di, d, k, rng):
    if k == 0:
        return np.zeros((d, 0))
    n = 512
    Zi = rng.standard_normal((n, d)); Zj = rng.standard_normal((n, d))
    dpsi = 1.0 - np.tanh(Zi[:, :di]) ** 2
    grad_id = dpsi * (np.tanh(Zj[:, :di]) @ K)
    g = np.zeros((n, d)); g[:, :di] = grad_id
    _, evecs = np.linalg.eigh(g.T @ g / n)
    return evecs[:, :k]


class Encoder(torch.nn.Module):
    def __init__(self, d):
        super().__init__()
        self.lin = torch.nn.Linear(d, d)

    def forward(self, x):
        return self.lin(x)


class Firewall(torch.nn.Module):
    def __init__(self, d, cap):
        super().__init__()
        self.cap = cap
        self.net = torch.nn.Sequential(
            torch.nn.Linear(2 * d, 32), torch.nn.Tanh(), torch.nn.Linear(32, 1))

    def forward(self, xi, xj):
        return self.cap * torch.tanh(self.net(torch.cat([xi, xj], -1)).squeeze(-1))


def make_data(cfg, K_true, ker_basis, range_basis, di, rng):
    d = cfg.d
    z_train = rng.standard_normal((cfg.n_train, d)); z_test = rng.standard_normal((cfg.n_test, d))
    M = rng.standard_normal((d, d)) if cfg.mix_features else np.eye(d)
    x_train = z_train @ M.T + cfg.noise_x * rng.standard_normal((cfg.n_train, d))
    x_test = z_test @ M.T + cfg.noise_x * rng.standard_normal((cfg.n_test, d))
    pi = rng.integers(0, cfg.n_train, cfg.n_pairs); pj = rng.integers(0, cfg.n_train, cfg.n_pairs)
    ai = np.tanh(z_train[pi, :di]); bj = np.tanh(z_train[pj, :di])
    y = (ai * (bj @ K_true)).sum(-1) + cfg.noise_y * rng.standard_normal(cfg.n_pairs)
    return dict(z_train=z_train, z_test=z_test, x_train=x_train, x_test=x_test, pi=pi, pj=pj, y=y,
                ker_basis=ker_basis, range_basis=range_basis)


def train_eval(data, K_model, K_true, di, U_np, cap_frac, cfg, seed):
    torch.manual_seed(seed)
    zt = torch.tensor(data["z_train"]); ze = torch.tensor(data["z_test"])
    xt = torch.tensor(data["x_train"]); xe = torch.tensor(data["x_test"])
    yi = torch.tensor(data["pi"]); yj = torch.tensor(data["pj"]); yv = torch.tensor(data["y"])
    Km = torch.tensor(K_model)
    U = torch.tensor(U_np); lab_t = zt @ U
    enc = Encoder(cfg.d)
    params = list(enc.parameters())
    fw = None
    if cap_frac > 0:
        fw = Firewall(cfg.d, cap_frac * float(np.std(data["y"])))
        params += list(fw.parameters())
    opt = torch.optim.Adam(params, lr=cfg.lr)
    for _ in range(cfg.epochs):
        opt.zero_grad()
        zh = enc(xt)
        e = energy(zh[yi], zh[yj], Km, di)
        if fw is not None:
            e = e + fw(xt[yi], xt[yj])
        loss = ((e - yv) ** 2).mean() + cfg.lam_label * (((zh @ U) - lab_t) ** 2).mean()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, cfg.clip)
        opt.step()
    with torch.no_grad():
        err = enc(xe) - ze
        Rb = torch.tensor(data["range_basis"])
        rel = lambda v: (v.norm(dim=1) / ze.norm(dim=1)).mean().item()
        return dict(full=rel(err), rng=rel(err @ Rb))


def med_iqr(vals):
    v = np.array(vals)
    return float(np.median(v)), float(np.percentile(v, 25)), float(np.percentile(v, 75))


def run_cell(cfg, eps, cap_frac):
    """One (eps, cap) cell: k=ker_dim targeted labels always; return per-seed full-recovery list."""
    out = []
    k = cfg.ker_dim
    for seed in cfg.seeds:
        rng = np.random.default_rng(seed)
        K_true, kerb, rngb, di = make_closure(cfg, rng)
        data = make_data(cfg, K_true, kerb, rngb, di, rng)
        if eps > 0:
            D = rng.standard_normal((di, di)); D = D @ D.T
            D = D / np.linalg.norm(D) * np.linalg.norm(K_true)
            K_model = K_true + eps * D
        else:
            K_model = K_true
        U = fisher_targeted(K_model, di, cfg.d, k, rng)
        out.append(train_eval(data, K_model, K_true, di, U, cap_frac, cfg, seed)["full"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--seeds", type=int, default=None)
    args = ap.parse_args()
    cfg = Cfg()
    if args.epochs:
        cfg.epochs = args.epochs
    if args.seeds:
        cfg.seeds = tuple(range(args.seeds))

    print(f"# T0-H2 co-design  d={cfg.d} ker_dim={cfg.ker_dim} seeds={len(cfg.seeds)} "
          f"epochs={cfg.epochs} clip={cfg.clip}  (median +/- IQR)\n")

    # ---------- Panel A: eps-sweep, anchor-only vs firewall ----------
    print("## Panel A: full recovery vs eps (k=ker_dim anchored). cap=0 anchor-only; cap=0.5 firewall")
    print(f"{'eps':>5} | {'anchor-only med[IQR]':>26} | {'firewall med[IQR]':>26}")
    print("-" * 64)
    base_ao = base_fw = None
    A = {}
    for eps in cfg.eps_grid:
        ao = run_cell(cfg, eps, 0.0)
        fwv = run_cell(cfg, eps, 0.5)
        A[eps] = (ao, fwv)
        m_ao, l_ao, h_ao = med_iqr(ao); m_fw, l_fw, h_fw = med_iqr(fwv)
        if eps == 0.0:
            base_ao, base_fw = m_ao, m_fw
        print(f"{eps:>5.2f} | {m_ao:>8.3f} [{l_ao:.2f},{h_ao:.2f}]      | {m_fw:>8.3f} [{l_fw:.2f},{h_fw:.2f}]")
    eps_max = cfg.eps_grid[-1]
    d_ao = med_iqr(A[eps_max][0])[0] - base_ao
    d_fw = med_iqr(A[eps_max][1])[0] - base_fw
    print(f"\n  Delta vs eps=0 baseline at eps={eps_max}:  anchor-only +{d_ao:.3f}   firewall +{d_fw:.3f}")

    # ---------- Panel B: cap-sweep at fixed eps (co-design U-shape) ----------
    print(f"\n## Panel B: full recovery vs correction cap at eps={cfg.eps_for_capsweep} (U-shape = co-design)")
    print(f"{'cap':>6} | {'full recovery med[IQR]':>28}")
    print("-" * 40)
    B = {}
    for cap in cfg.cap_grid:
        vals = run_cell(cfg, cfg.eps_for_capsweep, cap)
        B[cap] = med_iqr(vals)[0]
        m, lo, hi = med_iqr(vals)
        tag = " (anchor-only)" if cap == 0 else ""
        print(f"{cap:>6.2f} | {m:>8.3f} [{lo:.2f},{hi:.2f}]{tag}")
    best_cap = min(B, key=B.get)
    print(f"\n  best cap = {best_cap}  (min recovery error {B[best_cap]:.3f})")

    # ---------- verdicts ----------
    print("\n## Pre-registered verdicts")
    h2a = d_fw < 0.6 * d_ao if d_ao > 1e-6 else False
    print(f"H2a firewall degrades << anchor-only as eps grows (Delta_fw < 0.6x Delta_ao): "
          f"+{d_fw:.3f} vs +{d_ao:.3f} -> {'PASS' if h2a else 'FAIL'}")
    interior = 0 < list(cfg.cap_grid).index(best_cap) < len(cfg.cap_grid) - 1
    h2b = interior and B[best_cap] < 0.8 * B[cfg.cap_grid[0]] and B[best_cap] < 0.8 * B[cfg.cap_grid[-1]]
    print(f"H2b co-design U-shape: interior optimum beats cap=0 and max cap (<0.8x each): "
          f"best={best_cap}({B[best_cap]:.3f}) vs anchor-only({B[cfg.cap_grid[0]]:.3f}) vs "
          f"maxcap({B[cfg.cap_grid[-1]]:.3f}) -> {'PASS' if h2b else 'FAIL'}")
    print(f"\nH2: {'CO-DESIGN DEMONSTRATED' if (h2a and h2b) else 'NOT cleanly demonstrated -- H2 stays a risk, not a headline'}")


if __name__ == "__main__":
    main()
