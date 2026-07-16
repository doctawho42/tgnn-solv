"""Experiment B (salvage) -- did NOT survive its own controls. Fig 9 stays an honest negative.

Hypothesis tested: Fig 9's null (median cosine ~=0 between the drift delta_X = z_hat_X - z*_X
and the first-order compensation J^+(m-g)) is a DISTRIBUTION-MISMATCH artifact -- the drift was
shaped on the training partner distribution D_train while Fig 9 probed one pair from a different
D_match. If so, the same object on D_train (many pairs) should align and on D_match should not,
with sample size held fixed.

Object matched to the paper: scalar closure g, latent z_X in R^d, J = grad_{z_X} g,
J^+(m-g) = (m-g) J / ||J||^2. Closure with a genuine compromise (the true z_S-quadratic coupling
beta*(z_X.p)*(z_S.q)^2 is OMITTED by g_F, so no fixed delta fixes all partners -> the per-molecule
compensation is a real compromise over the partner distribution):
    T(z_X,z_S)   = z_X^T A z_S + 0.5 kappa (z_X.z_X)(z_S.v) + beta (z_X.p)(z_S.q)^2   (true)
    g_F(z_X,z_S) = z_X^T (A+(1-F)E) z_S + 0.5 kappa (z_X.z_X)(z_S.v)                    (misspecified)
The head learns ONE free z_hat_X per molecule over its D_train partners (lambda=0, sharpest drift),
init at z*_X;  delta_X = z_hat_X - z*_X.

VERDICT (F=0.5, beta=0.8, seed 0): the salvage does NOT cleanly hold.
  - Fig 9 reproduced: cos(delta, J^+ on one D_match pair) = 0.055 ~ 0.  (OK)
  - The drift IS essentially the Gauss-Newton first-order compensation: cos(delta, GN_train)=0.98.
  - BUT Fig 9's OWN estimator (naive per-pair J^+ average) is uniformly weak even on D_train
    (0.20), so its ~0 is dominated by being a poor estimator of the GN compensation, NOT by the
    partner distribution. The distribution gap under the proper (GN) estimator is modest
    (train 0.98 vs match 0.79) and the shift sweep is confounded by Jacobian conditioning
    (||z_S|| grows with the mean shift). => distribution mismatch is a minor, confounded rider,
    not the cause. In the real setting the activity Fisher is near rank-1 (participation ratio
    ~1.4/51), which makes GN itself ill-posed -- another reason the clean story does not transfer.
Kept as a documented negative control. Fig 9 remains reported as an honest negative; do NOT put
a distribution-mismatch explanation in the paper. See reports/SPEC_frontier_experiments_2026-07-16.md.

CPU, deterministic.  KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_drift_distribution_mismatch.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch


def cosines(delta: np.ndarray, c: np.ndarray) -> np.ndarray:
    """row-wise cosine between two (M,d) arrays; nan rows (zero c) dropped by caller."""
    dn = np.linalg.norm(delta, axis=1)
    cn = np.linalg.norm(c, axis=1)
    dot = (delta * c).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return dot / (dn * cn)


def med(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    return float(np.median(x)) if x.size else float("nan")


class Closure:
    """analytic teacher / misspecified closure and its first-order compensation."""

    def __init__(self, rng, d, F, kappa, beta):
        self.d, self.F, self.kappa, self.beta = d, F, kappa, beta
        self.A = rng.standard_normal((d, d)) / np.sqrt(d)
        self.E = rng.standard_normal((d, d)) / np.sqrt(d)   # wrong-coupling direction
        self.v = rng.standard_normal(d) / np.sqrt(d)
        self.p = rng.standard_normal(d) / np.sqrt(d)        # true z_S-quadratic coupling
        self.q = rng.standard_normal(d) / np.sqrt(d)
        self.CF = self.A + (1.0 - F) * self.E

    def m_true(self, zx, zs, noise_sd, rng):
        lin = np.einsum("id,de,je->ij", zx, self.A, zs)          # (M,K) z_X^T A z_S
        quad = 0.5 * self.kappa * (zx * zx).sum(1)[:, None] * (zs @ self.v)[None, :]
        # z_S-quadratic true coupling the closure OMITS: not fixable by any fixed delta,
        # so the best per-molecule compensation is a compromise over the partner distribution.
        zsq = self.beta * (zx @ self.p)[:, None] * ((zs @ self.q) ** 2)[None, :]
        return lin + quad + zsq + rng.standard_normal((zx.shape[0], zs.shape[0])) * noise_sd

    def g_np(self, zx, zs):
        lin = np.einsum("id,de,je->ij", zx, self.CF, zs)
        quad = 0.5 * self.kappa * (zx * zx).sum(1)[:, None] * (zs @ self.v)[None, :]
        return lin + quad

    def jac(self, zx, zs):
        """J(z*_X,z_S) for every (X,S) pair -> (M,K,d)."""
        base = np.einsum("de,je->jd", self.CF, zs)               # (K,d) = CF z_S
        J = base[None, :, :] + self.kappa * zx[:, None, :] * (zs @ self.v)[None, :, None]
        return J

    def first_order_unit(self, zx, zs, noise_sd, rng):
        """per-pair J^+(m-g) = (m-g) J / ||J||^2  -> (M,K,d). Also returns (r, J)."""
        m = self.m_true(zx, zs, noise_sd, rng)
        r = m - self.g_np(zx, zs)                                # (M,K)
        J = self.jac(zx, zs)                                     # (M,K,d)
        Jn2 = (J * J).sum(2) + 1e-9
        return r[:, :, None] * J / Jn2[:, :, None], r, J         # (M,K,d),(M,K),(M,K,d)

    # torch closure for the drift fit (differentiable in z_hat)
    def g_torch(self, zh, zs_t):
        CF = torch.tensor(self.CF)
        v = torch.tensor(self.v)
        lin = (zh @ CF) @ zs_t.T
        quad = 0.5 * self.kappa * (zh * zh).sum(1)[:, None] * (zs_t @ v)[None, :]
        return lin + quad


def gauss_newton(r, J, eps=1e-3):
    """per-molecule GN step (Sum_S J J^T + eps I)^-1 Sum_S J r  -> (M,d).

    This is the actual first-order minimiser of Sum_S (r_S - J_S.delta)^2, which the drift
    converges to -- distinct from the naive average of per-pair J^+ r that Fig 9's formula
    estimates."""
    d = J.shape[2]
    H = np.einsum("mkd,mke->mde", J, J) + eps * np.eye(d)[None]  # (M,d,d)
    b = np.einsum("mkd,mk->md", J, r)                            # (M,d)
    return np.linalg.solve(H, b)


def fit_drift(clo, zx, zs_train, m_train, steps, lr):
    zstar = torch.tensor(zx)
    zh = torch.tensor(zx.copy(), requires_grad=True)   # init at z*_X
    zs_t = torch.tensor(zs_train)
    m_t = torch.tensor(m_train)
    opt = torch.optim.Adam([zh], lr=lr)
    for _ in range(steps):
        opt.zero_grad()
        loss = ((m_t - clo.g_torch(zh, zs_t)) ** 2).mean()
        loss.backward()
        opt.step()
    return (zh.detach().numpy() - zstar.numpy())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=Path("results/frontier/drift_distribution_mismatch.json"))
    ap.add_argument("--d", type=int, default=4)
    ap.add_argument("--M", type=int, default=150)
    ap.add_argument("--K-train", type=int, default=30)
    ap.add_argument("--K-match", type=int, default=30)
    ap.add_argument("--fidelity", type=float, default=0.5)
    ap.add_argument("--kappa", type=float, default=0.15)
    ap.add_argument("--beta", type=float, default=0.8)
    ap.add_argument("--mu-shift", type=float, default=2.0)
    ap.add_argument("--sigma-match", type=float, default=0.5)
    ap.add_argument("--snr", type=float, default=20.0)
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--lr", type=float, default=2e-2)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    d, M = args.d, args.M
    clo = Closure(rng, d, args.fidelity, args.kappa, args.beta)

    zx = rng.standard_normal((M, d))                                    # molecule latents
    zs_train = rng.standard_normal((args.K_train, d))                  # D_train ~ N(0, I)
    mu = args.mu_shift * np.ones(d)
    zs_match = mu + args.sigma_match * rng.standard_normal((args.K_match, d))  # D_match (shifted)

    # residual scale for noise: from the misspecification magnitude on D_train
    r_scale = (clo.m_true(zx, zs_train, 0.0, rng) - clo.g_np(zx, zs_train)).std()
    noise_sd = r_scale / np.sqrt(args.snr)

    # --- 1. the actual drift (trained free z_hat over D_train) ---
    m_train = clo.m_true(zx, zs_train, noise_sd, rng)
    delta = fit_drift(clo, zx, zs_train, m_train, args.steps, args.lr)

    # --- 2. first-order compensation directions (analytic J at z*_X) ---
    ng = np.random.default_rng(args.seed + 7)
    u_train, r_train, J_train = clo.first_order_unit(zx, zs_train, noise_sd, ng)  # (M,K_train,d)
    u_match, r_match, J_match = clo.first_order_unit(zx, zs_match, noise_sd, ng)  # (M,K_match,d)

    c_train_many = u_train.mean(1)                 # naive avg of per-pair J^+ r (Fig 9's object)
    c_match_many = u_match.mean(1)
    c_train_1 = u_train[:, 0, :]
    c_match_1 = u_match[:, 0, :]   # = Fig 9 (one pair, wrong distribution)
    gn_train = gauss_newton(r_train, J_train)      # exact first-order minimiser on D_train
    gn_match = gauss_newton(r_match, J_match)

    cell = {
        "train_many_naive": med(cosines(delta, c_train_many)),
        "train_1_naive": med(cosines(delta, c_train_1)),
        "match_many_naive": med(cosines(delta, c_match_many)),
        "match_1_FIG9": med(cosines(delta, c_match_1)),
        "train_GaussNewton": med(cosines(delta, gn_train)),
        "match_GaussNewton": med(cosines(delta, gn_match)),
    }

    # --- 3. distribution-shift sweep: sample size fixed at "many", move D_match ---
    shift_sweep = []
    for mu_s in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]:
        zs_m = mu_s * np.ones(d) + args.sigma_match * rng.standard_normal((args.K_match, d))
        u_m, r_m, J_m = clo.first_order_unit(zx, zs_m, noise_sd, np.random.default_rng(args.seed + 11))
        shift_sweep.append({
            "mu_shift": mu_s,
            "cos_match_many_naive": round(med(cosines(delta, u_m.mean(1))), 3),
            "cos_match_GaussNewton": round(med(cosines(delta, gauss_newton(r_m, J_m))), 3),
        })

    # The salvage is about the DISTRIBUTION, a relative claim at equal sample size:
    fig9_reproduced = cell["match_1_FIG9"] < 0.2
    power_excluded = cell["match_many_naive"] < cell["match_1_FIG9"] + 0.1   # many wrong-dist samples don't help
    distribution_effect = cell["train_GaussNewton"] - cell["match_GaussNewton"] > 0.3
    first_order_ok = cell["train_GaussNewton"] > 0.5                          # drift is first-order under GN
    salvage = fig9_reproduced and power_excluded and distribution_effect and first_order_ok

    summary = {
        "config": {k: getattr(args, k) for k in
                   ("d", "M", "K_train", "K_match", "fidelity", "kappa", "beta", "mu_shift",
                    "sigma_match", "snr", "steps", "seed")},
        "cos_median": {k: round(v, 3) for k, v in cell.items()},
        "shift_sweep": shift_sweep,
        "drift_norm_median": round(float(np.median(np.linalg.norm(delta, axis=1))), 3),
        "checks": {"fig9_reproduced": bool(fig9_reproduced), "power_excluded": bool(power_excluded),
                   "distribution_effect": bool(distribution_effect), "first_order_ok": bool(first_order_ok)},
        "salvage_supported": bool(salvage),
        "reading": ("drift aligns with the D_train first-order compensation (best under Gauss-Newton) "
                    "but NOT with D_match; Fig 9 = match_1. Many D_match samples also fail => "
                    "distribution mismatch, not power. Naive per-pair-J^+ average (Fig 9's own "
                    "estimator) is a lossy predictor even on D_train; Gauss-Newton is the clean one."),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2))

    print("Drift distribution-mismatch (Experiment B, salvage)")
    print(f"  d={d} M={M} K_train={args.K_train} K_match={args.K_match} "
          f"F={args.fidelity} kappa={args.kappa} mu_shift={args.mu_shift} snr={args.snr}")
    print("  median cos(delta_X, first-order compensation):")
    print(f"                       {'1 sample':>10} {'many (naive)':>13} {'many (Gauss-Newton)':>21}")
    print(f"    D_train (right)    {cell['train_1_naive']:>10.3f} {cell['train_many_naive']:>13.3f} "
          f"{cell['train_GaussNewton']:>21.3f}")
    print(f"    D_match (wrong)    {cell['match_1_FIG9']:>10.3f} {cell['match_many_naive']:>13.3f} "
          f"{cell['match_GaussNewton']:>21.3f}   <- match_1 = Fig 9")
    print("  distribution-shift sweep (sample size fixed = many):")
    for s in shift_sweep:
        print(f"    mu_shift={s['mu_shift']:>4} : naive {s['cos_match_many_naive']:+.3f}  "
              f"GaussNewton {s['cos_match_GaussNewton']:+.3f}")
    print(f"\n  checks: fig9_reproduced={fig9_reproduced} power_excluded={power_excluded} "
          f"distribution_effect={distribution_effect} first_order_ok={first_order_ok}")
    print(f"  salvage_supported = {salvage}")
    print(f"  wrote {args.out_json}")


if __name__ == "__main__":
    main()
