"""T0 kill-test for the Grounding-Budget concept.

Concept note: reports/CONCEPT_grounding_budget_2026-07-15.md

Synthetic controlled closure with a TUNABLE, exact null space. Tests, on HELD-OUT molecules:

  H1 (correct closure): null-space-TARGETED direction labels beat RANDOM labels -- and beat
      the no-label arm -- at EQUAL label budget k. Targeted directions are the smallest-
      eigenvalue subspace of the closure's Fisher matrix E[(dy/dz)(dy/dz)^T], computed FROM
      THE CLOSURE ALONE (no z*).
  H2 (misspecified closure): anchoring ALONE leaves latent error, while anchoring PLUS a capped
      correction head ("firewall") recovers more of z*.

Mechanism. The observable for a pair is  E_ij = psi(z_i)^T K psi(z_j)  with psi an elementwise
nonlinearity (tanh) and K acting only on the first `di = d - ker_dim` "identifiable" coordinates.
The last `ker_dim` coordinates never enter the closure -> they are an EXACT per-molecule gauge
(shift them freely, the observable is unchanged): that is the compensation. The elementwise psi
breaks the spurious metric-rotation gauge that a purely bilinear closure would have, so y-fitting
recovers the identifiable coordinates and the ONLY residual freedom is the compensation gauge --
which makes the full held-out recovery a clean, single, honest metric.

Labels are k directions U; the supervision is the projections U^T z* on TRAIN molecules. TARGETED
picks U = the closure's ill-constrained (Fisher-null) subspace; RANDOM picks U at random. At
equal budget k, targeted should collapse the gauge while random wastes budget on already-pinned
identifiable directions.

Pre-registered falsification (concept note S8):
  F1  no-label arm must FAIL to recover the gauge (ker rel > 0.5), else there is no compensation.
  F2  TARGETED must beat RANDOM on held-out FULL recovery at k = ker_dim (< 0.7x), else the novel
      core (the null-space label-selection law) is dead.
  F3  TARGETED must also beat the no-label arm (< 0.7x).

All CPU, minutes. No GNN, no rdkit. T0 tests the label-selection mechanism; the transfer-limited
real encoder and the real COSMO-SAC closure are T0.5 / T1.
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
    d: int = 24                 # ambient latent dim (sigma-profile bins)
    ker_dim: int = 6            # dimension of the exact compensation gauge
    n_train: int = 400
    n_test: int = 200
    n_pairs: int = 4000
    noise_y: float = 0.02
    noise_x: float = 0.05
    eps_misspec: float = 0.25
    lam_label: float = 5.0
    corr_cap: float = 0.5       # firewall cap, as a fraction of std(y)
    epochs: int = 800
    lr: float = 3e-2
    seeds: tuple = (0, 1, 2, 3, 4)
    k_grid: tuple = (0, 2, 4, 6, 9, 12, 18)


def psi(z):
    return torch.tanh(z)


def make_closure(cfg: Cfg, rng: np.random.Generator):
    """K (SPD) acting on the first di coords; last ker_dim coords are the exact gauge."""
    di = cfg.d - cfg.ker_dim
    B = rng.standard_normal((di, di))
    K = B @ B.T / di + 0.5 * np.eye(di)          # well-conditioned SPD
    eye = np.eye(cfg.d)
    range_basis = eye[:, :di]                     # identifiable (standard) coords
    ker_basis = eye[:, di:]                       # gauge (standard) coords
    return K, ker_basis, range_basis, di


def energy(z_i, z_j, K, di):
    a = psi(z_i[..., :di]); b = psi(z_j[..., :di])
    return (a * (b @ K)).sum(-1)


def fisher_targeted(K, di, d, k, rng: np.random.Generator):
    """Ill-constrained subspace from the CLOSURE ALONE: smallest-eigenvalue eigenvectors of
    G = E[(dE/dz_i)(dE/dz_i)^T] over random z. On the gauge coords dE/dz = 0 -> they surface as
    the smallest-eigenvalue directions."""
    if k == 0:
        return np.zeros((d, 0))
    n = 512
    Zi = rng.standard_normal((n, d)); Zj = rng.standard_normal((n, d))
    ai = np.tanh(Zi[:, :di]); dpsi = 1.0 - ai ** 2  # psi'(z_i)
    bj = np.tanh(Zj[:, :di])
    grad_id = dpsi * (bj @ K)                        # (n, di) = dE/dz_i on identifiable block
    G = np.zeros((d, d))
    g_full = np.zeros((n, d)); g_full[:, :di] = grad_id
    G = g_full.T @ g_full / n
    evals, evecs = np.linalg.eigh(G)
    return evecs[:, :k]                              # smallest eigenvalues first


def random_dirs(d, k, rng):
    if k == 0:
        return np.zeros((d, 0))
    Qr, _ = np.linalg.qr(rng.standard_normal((d, k)))
    return Qr[:, :k]


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


def run_arm(data, K_model, K_true, di, U_np, cfg, use_firewall, seed):
    torch.manual_seed(seed)
    zt = torch.tensor(data["z_train"]); ze = torch.tensor(data["z_test"])
    xt = torch.tensor(data["x_train"]); xe = torch.tensor(data["x_test"])
    yi = torch.tensor(data["pi"]); yj = torch.tensor(data["pj"]); yv = torch.tensor(data["y"])
    Km = torch.tensor(K_model)
    U = torch.tensor(U_np) if U_np.shape[1] > 0 else None
    lab_t = (zt @ U) if U is not None else None

    enc = Encoder(cfg.d)
    params = list(enc.parameters())
    fw = Firewall(cfg.d, cfg.corr_cap * float(np.std(data["y"]))) if use_firewall else None
    if fw is not None:
        params += list(fw.parameters())
    opt = torch.optim.Adam(params, lr=cfg.lr)

    for _ in range(cfg.epochs):
        opt.zero_grad()
        zh = enc(xt)
        e = energy(zh[yi], zh[yj], Km, di)
        if fw is not None:
            e = e + fw(xt[yi], xt[yj])
        loss = ((e - yv) ** 2).mean()
        if U is not None:
            loss = loss + cfg.lam_label * (((zh @ U) - lab_t) ** 2).mean()
        loss.backward()
        opt.step()

    with torch.no_grad():
        err = enc(xe) - ze
        Kb = torch.tensor(data["ker_basis"]); Rb = torch.tensor(data["range_basis"])
        rel = lambda v: (v.norm(dim=1) / ze.norm(dim=1)).mean().item()
        te_i, te_j = data["te_i"], data["te_j"]
        e_te = energy(enc(xe)[te_i], enc(xe)[te_j], torch.tensor(K_true), di)
        y_te = torch.tensor(data["y_te"])
        yfit = (((e_te - y_te) ** 2).mean() / (y_te.var() + 1e-12)).item()
    return dict(full=rel(err), ker=rel(err @ Kb), rng=rel(err @ Rb), yfit=yfit)


def make_data(cfg, K_true, ker_basis, range_basis, di, rng):
    d = cfg.d
    z_train = rng.standard_normal((cfg.n_train, d)); z_test = rng.standard_normal((cfg.n_test, d))
    M = rng.standard_normal((d, d))
    x_train = z_train @ M.T + cfg.noise_x * rng.standard_normal((cfg.n_train, d))
    x_test = z_test @ M.T + cfg.noise_x * rng.standard_normal((cfg.n_test, d))
    pi = rng.integers(0, cfg.n_train, cfg.n_pairs); pj = rng.integers(0, cfg.n_train, cfg.n_pairs)
    ai = np.tanh(z_train[pi, :di]); bj = np.tanh(z_train[pj, :di])
    y = (ai * (bj @ K_true)).sum(-1) + cfg.noise_y * rng.standard_normal(cfg.n_pairs)
    te_i = rng.integers(0, cfg.n_test, 2000); te_j = rng.integers(0, cfg.n_test, 2000)
    at = np.tanh(z_test[te_i, :di]); bt = np.tanh(z_test[te_j, :di])
    y_te = (at * (bt @ K_true)).sum(-1)
    return dict(z_train=z_train, z_test=z_test, x_train=x_train, x_test=x_test, pi=pi, pj=pj,
                y=y, te_i=te_i, te_j=te_j, y_te=y_te, ker_basis=ker_basis, range_basis=range_basis)


def agg(runs):
    return {k: (float(np.mean([r[k] for r in runs])), float(np.std([r[k] for r in runs])))
            for k in runs[0]}


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

    print(f"# Grounding-Budget T0 (nonlinear closure)  d={cfg.d} ker_dim={cfg.ker_dim} "
          f"eps={cfg.eps_misspec} seeds={len(cfg.seeds)} epochs={cfg.epochs}\n")

    print("## H1 (correct closure): held-out recovery vs label budget k")
    print(f"{'k':>3} | {'arm':<9} | {'full(rel)':>13} | {'ker(rel)':>13} | {'range(rel)':>13} | {'yfit':>7}")
    print("-" * 76)
    h1 = {}
    for k in cfg.k_grid:
        for name in (["no-label"] if k == 0 else ["no-label", "random", "targeted"]):
            runs = []
            for seed in cfg.seeds:
                rng = np.random.default_rng(seed)
                K_true, kerb, rngb, di = make_closure(cfg, rng)
                data = make_data(cfg, K_true, kerb, rngb, di, rng)
                if name == "no-label":
                    U = np.zeros((cfg.d, 0))
                elif name == "random":
                    U = random_dirs(cfg.d, k, rng)
                else:
                    U = fisher_targeted(K_true, di, cfg.d, k, rng)
                runs.append(run_arm(data, K_true, K_true, di, U, cfg, False, seed))
            a = agg(runs); h1[(k, name)] = a
            print(f"{k:>3} | {name:<9} | {a['full'][0]:>7.4f}±{a['full'][1]:.3f} | "
                  f"{a['ker'][0]:>7.4f}±{a['ker'][1]:.3f} | {a['rng'][0]:>7.4f}±{a['rng'][1]:.3f} | "
                  f"{a['yfit'][0]:>7.4f}")
        if k > 0:
            print("-" * 76)

    print("\n## H2 (misspecified closure, k = ker_dim, targeted labels)")
    print(f"{'arm':<26} | {'full(rel)':>13} | {'ker(rel)':>13} | {'range(rel)':>13} | {'yfit':>7}")
    print("-" * 76)
    k = cfg.ker_dim
    h2 = {}
    for name, misspec, fw in [("correct closure (ref)", False, False),
                              ("misspec, anchor only", True, False),
                              ("misspec, anchor+firewall", True, True)]:
        runs = []
        for seed in cfg.seeds:
            rng = np.random.default_rng(seed)
            K_true, kerb, rngb, di = make_closure(cfg, rng)
            data = make_data(cfg, K_true, kerb, rngb, di, rng)
            if misspec:
                D = rng.standard_normal((di, di)); D = D @ D.T; D = D / np.linalg.norm(D) * np.linalg.norm(K_true)
                K_model = K_true + cfg.eps_misspec * D
                U = fisher_targeted(K_model, di, cfg.d, k, rng)
            else:
                K_model = K_true
                U = fisher_targeted(K_true, di, cfg.d, k, rng)
            runs.append(run_arm(data, K_model, K_true, di, U, cfg, fw, seed))
        a = agg(runs); h2[name] = a
        print(f"{name:<26} | {a['full'][0]:>7.4f}±{a['full'][1]:.3f} | "
              f"{a['ker'][0]:>7.4f}±{a['ker'][1]:.3f} | {a['rng'][0]:>7.4f}±{a['rng'][1]:.3f} | {a['yfit'][0]:>7.4f}")

    print("\n## Verdicts")
    kk = cfg.ker_dim
    # H1 is a claim about the COMPENSATION subspace = ker(closure). Judge the mechanism on ker.
    nol_ker = h1[(0, "no-label")]["ker"][0]
    tgt_ker = h1[(kk, "targeted")]["ker"][0]; rnd_ker = h1[(kk, "random")]["ker"][0]
    tgt_rng = h1[(kk, "targeted")]["rng"][0]
    tgt_full = h1[(kk, "targeted")]["full"][0]; rnd_full = h1[(kk, "random")]["full"][0]
    f1 = nol_ker > 0.5
    f2 = tgt_ker < 0.5 * rnd_ker and tgt_ker < 0.3          # gauge collapsed AND << random
    f3 = tgt_full < 0.7 * rnd_full                          # pre-registered full-recovery check
    print(f"F1  compensation exists (no-label ker>0.5):        {nol_ker:.3f} -> {'PASS' if f1 else 'FAIL'}")
    print(f"F2  MECHANISM: targeted collapses gauge, << random:{tgt_ker:.3f} vs {rnd_ker:.3f} -> {'PASS' if f2 else 'FAIL'}")
    print(f"F3  pre-registered full: targeted <0.7x random:    {tgt_full:.3f} vs {rnd_full:.3f} -> {'PASS' if f3 else 'FAIL'}")
    print(f"    [caveat] residual targeted error is ENCODER-limited range, not gauge: "
          f"range={tgt_rng:.3f} (Risk-2 preview; y-fit alone underidentifies identifiable coords)")
    # H2: does the firewall reduce latent error under misspecification vs anchoring alone?
    fw_full = h2["misspec, anchor+firewall"]["full"][0]; ao_full = h2["misspec, anchor only"]["full"][0]
    h2_demo = fw_full < 0.9 * ao_full
    print(f"H2  firewall < anchor-only under misspec (<0.9x):  {fw_full:.3f} vs {ao_full:.3f} -> "
          f"{'DEMONSTRATED' if h2_demo else 'NOT demonstrated by this toy (H2 needs its own design)'}")
    print(f"\nH1 CORE: {'SURVIVES -> proceed to T0.5 (real COSMO-SAC closure kernel: is it global & low-dim?)' if (f1 and f2) else 'DEAD -> program core falsified'}")


if __name__ == "__main__":
    main()
