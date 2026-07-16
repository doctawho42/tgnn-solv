"""Experiment A2b (spine) -- the DATA-BUDGET axis on pKa: disentangle bias from variance.

The lambda-sweep (run_pka_lambda_frontier.py) traced the fidelity axis but the meta/para slope
(S=-5.34) is confounded by sample size: meta/para n=163 vs ortho n=1198 (7.3x). Prop. 1,
  T(n) ~= Delta_inf + [V_phys(n) - V_direct(n)],
makes the sign of the tax n-dependent: at small n the estimation-variance saving can dominate
the bias, at large n only Delta_inf remains. The synthetic dial held n fixed and swept only F,
so A1 measured only the bias term (S in [0, 0.17]); a value like -5.34 is the variance term,
outside A1's range. (App G already says it in words: on clean meta/para the fixed LFER on the
reference sigma is excellent yet the small-n trained arm is not -- variance, not fidelity.)

This sweeps n on ORTHO (subsample + refit), holding the closure fixed, and measures the
reference-input penalty and the physics tax as functions of n:
    D_free = mean|sigma_hat - sigma_true|  (latent INFIDELITY, not physicality)   [lambda=0]
    reference-input penalty  Pen(n) = MAE_oracle - MAE_free      (>0: pinning to true sigma HURTS)
    two-point slope          S(n)   = -(dMAE/dD) = (MAE_oracle - MAE_free) / D_free
    physics tax (Prop 1)     Tax(n) = MAE_free_physics - MAE_direct   (>0: bottleneck loses to black box)

Two wins:
  * confound removed: if S(n=163) on ortho is still > 0 while meta/para (also n~=163) is < 0, the
    sign flip is FIDELITY (closure quality), not n.
  * n*: Prop 1 predicts S(n)/Pen(n) rises with n and crosses zero -- the critical data budget,
    currently a theory corollary with no measurement.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/experiments/run_pka_n_sweep.py \
        --sdf notebooks/data/raw/pKa_QR.sdf --out-json results/frontier/frontier_pka_nsweep.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import torch
import torch.nn as nn
from torch_geometric.loader import DataLoader

HERE = Path(__file__).resolve().parent


def _load_cmp():
    spec = importlib.util.spec_from_file_location("pka_cmp", HERE / "run_pka_trained_comparison.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _train(model, tr, epochs, lr, device, physics):
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    l1 = nn.L1Loss()
    loader = DataLoader(tr, batch_size=128, shuffle=True)
    model.train()
    for _ in range(epochs):
        for batch in loader:
            batch = batch.to(device)
            opt.zero_grad()
            if physics:
                z = model.enc(batch.x, batch.edge_index, batch.batch)
                sh = model.head(z).squeeze(-1)
                pred = batch.pka0.squeeze(-1) - batch.rho.squeeze(-1) * sh
            else:
                pred = model(batch)
            l1(pred, batch.pka.squeeze(-1)).backward()
            opt.step()


def _eval_physics(model, te, device):
    model.eval()
    devs, errs = [], []
    with torch.no_grad():
        for batch in DataLoader(te, batch_size=256):
            batch = batch.to(device)
            z = model.enc(batch.x, batch.edge_index, batch.batch)
            sh = model.head(z).squeeze(-1)
            pred = batch.pka0.squeeze(-1) - batch.rho.squeeze(-1) * sh
            devs.append((sh - batch.sigma.squeeze(-1)).abs().cpu())
            errs.append((pred - batch.pka.squeeze(-1)).abs().cpu())
    return float(torch.cat(devs).mean()), float(torch.cat(errs).mean())


def _eval_direct(model, te, device):
    model.eval()
    errs = []
    with torch.no_grad():
        for batch in DataLoader(te, batch_size=256):
            batch = batch.to(device)
            errs.append((model(batch) - batch.pka.squeeze(-1)).abs().cpu())
    return float(torch.cat(errs).mean())


def zero_crossing(ns, ys):
    """linear-interpolated n where y(n) crosses 0 (first sign change), else None."""
    for i in range(1, len(ns)):
        if ys[i - 1] == 0:
            return ns[i - 1]
        if ys[i - 1] * ys[i] < 0:
            t = ys[i - 1] / (ys[i - 1] - ys[i])
            return round(ns[i - 1] + t * (ns[i] - ns[i - 1]))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdf", default="notebooks/data/raw/pKa_QR.sdf")
    ap.add_argument("--out-json", type=Path, default=Path("results/frontier/frontier_pka_nsweep.json"))
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--n-grid", type=int, nargs="+", default=[163, 300, 500, 800, 1198])
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        args.epochs, args.seeds, args.n_grid = 3, [42], [163, 400]

    device = torch.device("cpu")
    cmp = _load_cmp()
    data = cmp.build_dataset(cmp._load_real_decomp(), args.sdf)
    ortho = [g for g in data if g.fidelity == "low_F"]
    in_dim = ortho[0].x.shape[1]
    grid = [n for n in args.n_grid if n <= len(ortho)]
    print(f"ortho n={len(ortho)}; sweeping n in {grid}; seeds={args.seeds} epochs={args.epochs}")

    rows = []
    for n in grid:
        Ds, Mf, Md, Mo = [], [], [], []
        for seed in args.seeds:
            rng = np.random.default_rng(seed)
            idx = rng.choice(len(ortho), size=n, replace=False)
            sub = [ortho[i] for i in idx]
            tr_idx, te_idx = cmp.scaffold_split(sub, seed)
            tr = [sub[i] for i in tr_idx]; te = [sub[i] for i in te_idx]
            torch.manual_seed(seed)
            phys = cmp.PhysicsGNN(in_dim, args.hidden, args.layers).to(device)
            _train(phys, tr, args.epochs, args.lr, device, physics=True)
            D, mf = _eval_physics(phys, te, device)
            torch.manual_seed(seed)
            direct = cmp.DirectGNN(in_dim, args.hidden, args.layers).to(device)
            _train(direct, tr, args.epochs, args.lr, device, physics=False)
            md = _eval_direct(direct, te, device)
            orc = np.array([float(sub[i].g_oracle) for i in te_idx])
            tru = np.array([float(sub[i].pka) for i in te_idx])
            mo = float(np.mean(np.abs(orc - tru)))
            Ds.append(D); Mf.append(mf); Md.append(md); Mo.append(mo)
        D, mf, md, mo = map(lambda a: float(np.mean(a)), (Ds, Mf, Md, Mo))
        pen = mo - mf                       # reference-input penalty (>0: pinning to true sigma HURTS)
        S2 = pen / D if D > 1e-9 else 0.0   # two-point slope -(dMAE/dD)
        tax = mf - md                       # physics-vs-direct (Prop 1; >0: bottleneck loses)
        rows.append({"n": n, "D_free": round(D, 3), "mae_free": round(mf, 3),
                     "mae_direct": round(md, 3), "mae_oracle": round(mo, 3),
                     "ref_input_penalty": round(pen, 3), "S_twopoint": round(S2, 3),
                     "physics_tax_vs_direct": round(tax, 3),
                     "mae_free_sd": round(float(np.std(Mf)), 3)})
        print(f"  n={n:5d}: D={D:.3f} free={mf:.3f} direct={md:.3f} oracle={mo:.3f} | "
              f"penalty(oracle-free)={pen:+.3f} S={S2:+.3f} tax(phys-direct)={tax:+.3f}")

    ns = [r["n"] for r in rows]
    out = {"config": {"epochs": args.epochs, "seeds": args.seeds, "n_grid": grid},
           "axis_note": "D_free = mean|sigma_hat - sigma_true| is latent INFIDELITY (0 = physical). "
                        "S = -(dMAE/dD): >0 = misspecified (pinning to truth hurts).",
           "rows": rows,
           "n_star_ref_input_penalty": zero_crossing(ns, [r["ref_input_penalty"] for r in rows]),
           "n_star_physics_tax": zero_crossing(ns, [r["physics_tax_vs_direct"] for r in rows])}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2))
    print(f"  n* (reference-input penalty crosses 0): {out['n_star_ref_input_penalty']}")
    print(f"  n* (physics tax vs direct crosses 0):   {out['n_star_physics_tax']}")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
