"""Experiment A1 (spine) -- the physicality-accuracy frontier; slope = misspecification.

The fidelity dial (run_fidelity_dial.py) compares an ORACLE closure on z* against a
FREE head; it has no learned latent and no supervision knob. This script adds exactly
that: a shared learned encoder z_hat = h_theta(z*) trained THROUGH a fixed misspecified
closure g_F, with a latent-supervision weight lambda pinning z_hat toward the physical
reference z*:

    L(theta) = mean( m - g_F(z_hat) )^2  +  lambda * mean|| z_hat - z* ||^2 .

Sweeping lambda traces a curve in ( physicality ||z_hat - z*||/||z*|| , error MAE/std(m) ).
Its slope  S := -d(MAE_rel)/d(physicality)  (the accuracy paid per unit of un-physicality,
i.e. the head's compensation rate) is the claim:

    well-specified closure (F=1)  -> S ~ 0   (physicality is free; no trade-off)
    misspecified closure (F<1)    -> S  > 0   growing as F falls.

The closure g_F(z) = T(z) + (1-F)*sig*(D(z)-muD)/sdD reuses the dial's teacher families
and misspecification shapes (same functional forms, same weight-draw order), reimplemented
in torch so g_F(z_hat) is differentiable. Constants sig, muD, sdD are fixed from the z*
reference draw so g_F is a genuinely FIXED map applied to the learned z_hat.

CPU, deterministic. Run:
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_physicality_frontier.py \
        --out-json results/frontier/frontier_synth.json
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn


# --------------------------------------------------------------------------- #
# torch teacher families / misspecification shapes (same forms as the dial)
# --------------------------------------------------------------------------- #
def make_weights(rng: np.random.Generator, d: int) -> dict:
    to_t = lambda a: torch.tensor(a, dtype=torch.float64)
    return {
        "w": to_t(rng.standard_normal(d) / np.sqrt(d)),
        "w1": to_t(rng.standard_normal(d) / np.sqrt(d)),
        "w2": to_t(rng.standard_normal(d) / np.sqrt(d)),
        "u": to_t(rng.standard_normal(d) / np.sqrt(d)),
    }


def teacher(name: str, W: dict):
    w, w1, w2 = W["w"], W["w1"], W["w2"]
    return {
        "linear": lambda z: z @ w,
        "monotone_nonlinear": lambda z: torch.tanh(1.5 * (z @ w)),
        "kinetics_exp": lambda z: torch.exp(0.4 * (z @ w)),
        "pde_field": lambda z: torch.sin(z @ w1) + 0.5 * torch.cos(1.3 * (z @ w2)),
    }[name]


def shape(name: str, W: dict):
    u = W["u"]
    return {
        "linear_bias": lambda z: z @ u,
        "quadratic": lambda z: (z @ u) ** 2 - 1.0,
        "cubic": lambda z: (z @ u) ** 3 - 3.0 * (z @ u),
        "abs": lambda z: torch.abs(z @ u) - np.sqrt(2.0 / np.pi),
        "sinusoidal": lambda z: torch.sin(2.0 * (z @ u)),
        "cross_term": lambda z: z[:, 0] * z[:, 1],
    }[name]


class Head(nn.Module):
    """Shared low-capacity encoder z* -> z_hat (cannot compensate per-sample)."""

    def __init__(self, d: int, hid: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, hid), nn.Tanh(), nn.Linear(hid, d)
        ).double()

    def forward(self, z):
        return self.net(z)


@dataclass
class FrontierPoint:
    family: str
    shape: str
    fidelity: float
    lam: float
    physicality: float   # ||z_hat - z*|| / ||z*||   (rel, row-mean)
    mae_rel: float       # MAE(m, g_F(z_hat)) / std(m)


def train_one(
    family: str, shape_name: str, F: float, lam: float,
    z_tr, z_te, W: dict, snr: float, steps: int, hid: int, seed: int,
) -> FrontierPoint:
    torch.manual_seed(seed)
    T = teacher(family, W)
    D = shape(shape_name, W)

    # fixed closure constants from the reference (train) draw of z*
    t_tr = T(z_tr)
    sig = float(t_tr.std())
    d_tr = D(z_tr)
    muD, sdD = float(d_tr.mean()), float(d_tr.std()) or 1.0
    alpha = 1.0 - F

    def g_F(z):
        return T(z) + alpha * sig * (D(z) - muD) / sdD

    # target m = T(z*) + noise (fixed); noise on train only, test uses clean scale for MAE ref
    noise_sd = sig / np.sqrt(snr) if sig > 0 else 1.0 / np.sqrt(snr)
    g = torch.Generator().manual_seed(seed + 1)
    m_tr = (t_tr + torch.randn(t_tr.shape, generator=g, dtype=torch.float64) * noise_sd).detach()
    m_te = (T(z_te) + torch.randn(z_te.shape[0], generator=g, dtype=torch.float64) * noise_sd).detach()
    m_std = float(m_te.std()) or 1.0

    head = Head(z_tr.shape[1], hid)
    opt = torch.optim.Adam(head.parameters(), lr=5e-3, weight_decay=1e-5)
    for _ in range(steps):
        opt.zero_grad()
        zh = head(z_tr)
        fit = ((m_tr - g_F(zh)) ** 2).mean()
        sup = ((zh - z_tr) ** 2).mean()
        (fit + lam * sup).backward()
        opt.step()

    with torch.no_grad():
        zh = head(z_te)
        num = torch.linalg.norm(zh - z_te, dim=1).mean()
        den = torch.linalg.norm(z_te, dim=1).mean() + 1e-12
        phys = float(num / den)
        mae = float((m_te - g_F(zh)).abs().mean())
    return FrontierPoint(family, shape_name, float(F), float(lam), phys, mae / m_std)


def slope(points: list[FrontierPoint]) -> float:
    """S = -d(mae_rel)/d(physicality) across the lambda sweep (>=0 = misspecification)."""
    x = np.array([p.physicality for p in points])
    y = np.array([p.mae_rel for p in points])
    if x.std() < 1e-9:
        return 0.0
    b = float(np.polyfit(x, y, 1)[0])   # d(mae)/d(phys), <= 0 when compensating
    return max(0.0, -b)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=Path("results/frontier/frontier_synth.json"))
    ap.add_argument("--n", type=int, default=2500)
    ap.add_argument("--d", type=int, default=6)
    ap.add_argument("--steps", type=int, default=400)
    ap.add_argument("--hidden", type=int, default=32)
    ap.add_argument("--snr", type=float, default=8.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fidelities", type=float, nargs="+", default=[1.0, 0.6, 0.35])
    ap.add_argument("--lambdas", type=float, nargs="+", default=[0.0, 0.05, 0.2, 0.8, 3.0, 12.0])
    ap.add_argument("--families", nargs="+",
                    default=["linear", "monotone_nonlinear", "kinetics_exp", "pde_field"])
    ap.add_argument("--shapes", nargs="+",
                    default=["linear_bias", "quadratic", "sinusoidal"])
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        args.n, args.steps, args.families, args.shapes = 800, 150, ["linear", "pde_field"], ["quadratic"]

    torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))
    rng = np.random.default_rng(args.seed)
    W = make_weights(rng, args.d)
    z = torch.tensor(rng.standard_normal((args.n, args.d)), dtype=torch.float64)
    n_tr = int(0.8 * args.n)
    z_tr, z_te = z[:n_tr], z[n_tr:]

    pts: list[FrontierPoint] = []
    for fam in args.families:
        for sh in args.shapes:
            for F in args.fidelities:
                for lam in args.lambdas:
                    pts.append(train_one(fam, sh, F, lam, z_tr, z_te, W,
                                         args.snr, args.steps, args.hidden, args.seed))

    # aggregate: slope S per fidelity, averaged over family x shape
    by_F: dict[float, list[float]] = {}
    for F in args.fidelities:
        slopes = []
        for fam in args.families:
            for sh in args.shapes:
                sub = [p for p in pts if p.family == fam and p.shape == sh and p.fidelity == F]
                sub = sorted(sub, key=lambda p: p.lam)
                slopes.append(slope(sub))
        by_F[F] = slopes

    summary = {
        "config": {k: getattr(args, k) for k in
                   ("n", "d", "steps", "hidden", "snr", "seed", "fidelities", "lambdas",
                    "families", "shapes")},
        "slope_by_fidelity": {
            f"{F:.2f}": {"S_mean": round(float(np.mean(by_F[F])), 4),
                         "S_sd": round(float(np.std(by_F[F])), 4)}
            for F in args.fidelities},
        "endpoints_by_fidelity": {
            f"{F:.2f}": {
                "phys_free_lam0": round(float(np.mean(
                    [p.physicality for p in pts if p.fidelity == F and p.lam == min(args.lambdas)])), 4),
                "phys_pinned_lammax": round(float(np.mean(
                    [p.physicality for p in pts if p.fidelity == F and p.lam == max(args.lambdas)])), 4),
                "mae_free_lam0": round(float(np.mean(
                    [p.mae_rel for p in pts if p.fidelity == F and p.lam == min(args.lambdas)])), 4),
                "mae_pinned_lammax": round(float(np.mean(
                    [p.mae_rel for p in pts if p.fidelity == F and p.lam == max(args.lambdas)])), 4),
            } for F in args.fidelities},
        "points": [asdict(p) for p in pts],
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, indent=2))

    print("Physicality-accuracy frontier (spine A1)")
    print(f"  n={args.n} d={args.d} steps={args.steps} snr={args.snr} "
          f"families={len(args.families)} shapes={len(args.shapes)}")
    print("  Slope S = -d(MAE_rel)/d(physicality)  [0 = closure well specified]")
    print(f"  {'fidelity F':>12} {'S_mean':>9} {'S_sd':>7}   "
          f"{'phys free->pinned':>20}  {'MAE free->pinned':>18}")
    for F in args.fidelities:
        e = summary["endpoints_by_fidelity"][f"{F:.2f}"]
        s = summary["slope_by_fidelity"][f"{F:.2f}"]
        print(f"  {F:>12.2f} {s['S_mean']:>9.4f} {s['S_sd']:>7.4f}   "
              f"{e['phys_free_lam0']:>8.3f} -> {e['phys_pinned_lammax']:<7.3f}  "
              f"{e['mae_free_lam0']:>7.3f} -> {e['mae_pinned_lammax']:<7.3f}")
    print(f"\n  wrote {args.out_json}")


if __name__ == "__main__":
    main()
