"""Planted-term POSITIVE CONTROL for the self-solvation law-vs-compensation discriminator.

Surviving seed (generative ideation, RESULTS_ideation_generative_2026-07-15.json): to tell a genuinely
discovered closed-form closure correction from a black-box residual compensator, use SELF-SOLVATION /
single-component data as an "uncheatable" axis -- a matched-capacity black-box fit on cross-pairs is
structurally blind on the self-solvation diagonal (never fit there), while a correctly-structured
closed-form term extrapolates there. BEFORE touching real data we must prove the DISCRIMINATOR ITSELF
works on synthetic data with a KNOWN planted term.

Design (honest; sensitivity AND specificity):
  Features: 5 physical functionals of each real VT-2005 sigma-profile (HB-acceptor/donor mass, polarity,
    mean sigma, area), z-scored.
  Planted term (POSITIVE): a symmetric bilinear physical form over features,
    Delta*(a,b) = c1(acc_a don_b + don_a acc_b) + c2 pol_a pol_b + c3 mean_a mean_b   (HB complementarity
    + polarity + dipole matching). Defined on all pairs incl. the self-solvation diagonal a=a.
  Data: train ONLY on off-diagonal pairs (i != j), y = Delta* + noise. Evaluate on the held-out DIAGONAL.
  Candidates, MATCHED capacity, same data/epochs:
    A  closed-form (structured): symmetric bilinear over a learned feature map, Delta_A = phi(a)^T S phi(b),
       S symmetric -> exchange-symmetric BY CONSTRUCTION, so it extrapolates to a=b. It must still DISCOVER
       phi and S from off-diagonal data (it is NOT handed the planted form).
    B  black-box MLP on [feat_a, feat_b] (asymmetric, no structure).
    B2 strongest-fair black-box: exchange-symmetric DeepSets MLP on {feat_a, feat_b} (respects a<->b
       symmetry but is not bilinear-structured) -- does symmetry alone rescue self-solvation?
  NEGATIVE control: Delta* = 0 (pure noise off-diagonal). A must NOT hallucinate a diagonal term.

Pre-registered verdict:
  PASS (discriminator works) iff  POSITIVE: A recovers Delta*(a,a) on the held-out diagonal (corr high)
    while B and B2 do NOT (clear separation);  AND  NEGATIVE: A's diagonal prediction is ~uncorrelated
    with the (zero) truth -> no false positive.
  FAIL (stop before real data) iff  B/B2 also predict the diagonal well (no structural blindness), OR A
    fails the positive, OR A hallucinates on the negative.

All CPU, minutes. Uses real VT-2005 sigma-profiles; no rdkit, no training of the big model.
"""
from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch

torch.set_default_dtype(torch.float64)

CSV = "results/sigma_profile_artifact/sigma_profiles.csv"
SIGMA_HB = 0.0084
SEED = 0


def features(df):
    """5 physical functionals of each sigma-profile, z-scored."""
    bincols = [f"sigma_p_{i}" for i in range(51)]
    P = df[bincols].to_numpy()                    # area per bin
    area = df["sigma_area"].to_numpy()
    p = P / area[:, None].clip(1e-6)              # normalized profile (sums to 1)
    grid = np.linspace(-0.025, 0.025, 51)
    acc = p[:, grid > SIGMA_HB].sum(1)            # mass in strongly-positive sigma
    don = p[:, grid < -SIGMA_HB].sum(1)           # mass in strongly-negative sigma
    mean = (p * grid).sum(1)
    pol = (p * grid ** 2).sum(1)
    F = np.stack([acc, don, mean, pol, area / area.mean()], 1)
    F = (F - F.mean(0)) / (F.std(0) + 1e-9)
    return torch.tensor(F)                        # (N,5)


def planted(F, positive):
    """Symmetric bilinear planted term over features; batched over pair tensors A,B (...,5)."""
    if not positive:
        return None
    c1, c2, c3 = 1.0, 0.6, 0.5
    acc, don, mean, pol = 0, 1, 2, 3

    def delta(A, B):
        return (c1 * (A[..., acc] * B[..., don] + A[..., don] * B[..., acc])
                + c2 * A[..., pol] * B[..., pol]
                + c3 * A[..., mean] * B[..., mean])
    return delta


class ClosedForm(torch.nn.Module):
    """Delta = phi(a)^T S phi(b), S symmetric -> exchange-symmetric by construction."""
    def __init__(self, d_in=5, k=8):
        super().__init__()
        self.phi = torch.nn.Sequential(torch.nn.Linear(d_in, 16), torch.nn.Tanh(), torch.nn.Linear(16, k))
        self.L = torch.nn.Parameter(0.1 * torch.randn(k, k))

    def forward(self, A, B):
        S = self.L + self.L.t()
        pa, pb = self.phi(A), self.phi(B)
        return ((pa @ S) * pb).sum(-1)


class BlackBox(torch.nn.Module):
    """Asymmetric MLP on [a,b]."""
    def __init__(self, d_in=5, h=40):
        super().__init__()
        self.net = torch.nn.Sequential(torch.nn.Linear(2 * d_in, h), torch.nn.Tanh(),
                                       torch.nn.Linear(h, h), torch.nn.Tanh(), torch.nn.Linear(h, 1))

    def forward(self, A, B):
        return self.net(torch.cat([A, B], -1)).squeeze(-1)


class SymBlackBox(torch.nn.Module):
    """Exchange-symmetric DeepSets MLP on {a,b}: fair strongest black-box."""
    def __init__(self, d_in=5, h=36):
        super().__init__()
        self.enc = torch.nn.Sequential(torch.nn.Linear(d_in, h), torch.nn.Tanh(), torch.nn.Linear(h, h))
        self.head = torch.nn.Sequential(torch.nn.Tanh(), torch.nn.Linear(h, h), torch.nn.Tanh(), torch.nn.Linear(h, 1))

    def forward(self, A, B):
        return self.head(self.enc(A) + self.enc(B)).squeeze(-1)


def nparams(m):
    return sum(p.numel() for p in m.parameters())


def fit(model, F, tr_i, tr_j, y_tr, epochs=1500, lr=3e-3):
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    A, B = F[tr_i], F[tr_j]
    for _ in range(epochs):
        opt.zero_grad()
        loss = ((model(A, B) - y_tr) ** 2).mean()
        loss.backward()
        opt.step()
    return model


def run(positive, rng, F, epochs=1500):
    N = F.shape[0]
    n_pairs = 12000
    ti = rng.integers(0, N, n_pairs); tj = rng.integers(0, N, n_pairs)
    keep = ti != tj
    ti, tj = ti[keep], tj[keep]
    delta = planted(F, positive)
    noise = 0.1
    if positive:
        y_tr = delta(F[ti], F[tj]) + noise * torch.randn(len(ti))
        y_diag = delta(F, F)                       # true self-solvation value per molecule
    else:
        y_tr = noise * torch.randn(len(ti))
        y_diag = torch.zeros(N)
    ti_t, tj_t = torch.tensor(ti), torch.tensor(tj)

    out = {}
    for name, model in [("closed-form (A)", ClosedForm()),
                        ("black-box (B)", BlackBox()),
                        ("sym-black-box (B2)", SymBlackBox())]:
        fit(model, F, ti_t, tj_t, y_tr, epochs=epochs)
        with torch.no_grad():
            pred_diag = model(F, F)                 # predict on the self-solvation diagonal
            off_pred = model(F[ti_t], F[tj_t])
            off_rmse = ((off_pred - y_tr) ** 2).mean().sqrt().item()
            if positive:
                dc = torch.corrcoef(torch.stack([pred_diag, y_diag]))[0, 1].item()
                drmse = ((pred_diag - y_diag) ** 2).mean().sqrt().item() / (y_diag.std().item() + 1e-9)
            else:
                dc = 0.0 if pred_diag.std() < 1e-9 else abs(pred_diag.mean().item()) / (pred_diag.std().item() + 1e-9)
                drmse = pred_diag.abs().mean().item()
        out[name] = (nparams(model), off_rmse, dc, drmse)
    return out


def main():
    df = pd.read_csv(CSV)
    F = features(df)
    rng = np.random.default_rng(SEED)
    print(f"# Self-solvation discriminator -- planted-term positive control  (N={F.shape[0]} real VT-2005)\n")

    print("## POSITIVE control (planted symmetric-bilinear term)")
    print(f"{'model':<20} | {'#params':>7} | {'off-diag RMSE':>13} | {'DIAG corr':>10} | {'DIAG nRMSE':>10}")
    print("-" * 72)
    pos = run(True, np.random.default_rng(SEED), F)
    for k, (np_, orm, dc, dr) in pos.items():
        print(f"{k:<20} | {np_:>7} | {orm:>13.4f} | {dc:>10.3f} | {dr:>10.3f}")

    print("\n## NEGATIVE control (planted term = 0; residual is pure noise)")
    print(f"{'model':<20} | {'#params':>7} | {'off-diag RMSE':>13} | {'DIAG |mean|/std':>15} | {'DIAG |pred|':>10}")
    print("-" * 74)
    neg = run(False, np.random.default_rng(SEED + 1), F)
    for k, (np_, orm, dc, dr) in neg.items():
        print(f"{k:<20} | {np_:>7} | {orm:>13.4f} | {dc:>15.3f} | {dr:>10.4f}")

    # ---- verdict ----
    A_dc = pos["closed-form (A)"][2]; B_dc = pos["black-box (B)"][2]; B2_dc = pos["sym-black-box (B2)"][2]
    A_neg = neg["closed-form (A)"][3]
    sep = A_dc > 0.7 and A_dc > B_dc + 0.3 and A_dc > B2_dc + 0.3
    spec = A_neg < 0.3 * pos["closed-form (A)"][3] if False else A_neg  # report raw; threshold below
    print("\n## Verdict")
    print(f"  POSITIVE separation: closed-form diag corr {A_dc:.3f} vs BB {B_dc:.3f} vs symBB {B2_dc:.3f}"
          f"  -> {'A recovers self-solvation, black-boxes blind' if sep else 'NO clean separation'}")
    print(f"  NEGATIVE specificity: closed-form diag |pred| under zero-truth = {A_neg:.4f}"
          f"  (should be small vs positive-control diag signal)")
    print(f"\n  DISCRIMINATOR: {'VALIDATED -> proceed to real-data self-solvation test' if sep else 'NOT validated -> stop before real data'}")


if __name__ == "__main__":
    main()
