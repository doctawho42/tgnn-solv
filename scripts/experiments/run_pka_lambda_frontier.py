"""Experiment A2 (spine, real data) -- the physicality-accuracy frontier on pKa, full lambda-curve.

The two-point version (run_pka_frontier_twopoint.py) used only the endpoints already in
trained_by_stratum.json (lambda=0 free sigma_hat, lambda=inf oracle) and got the SIGN of the
slope per fidelity stratum. This traces the whole curve: it adds a supervision term
lambda * MSE(sigma_hat, sigma_true) to the physics arm and sweeps lambda, measuring the pair

    ( physicality  P = mean|sigma_hat - sigma_true| ,  pKa test MAE )

stratified into meta/para (Hammett LFER well specified) vs ortho (misspecified). The slope
S = -d(MAE)/dP is the misspecification measure (A1's synthetic law on real data):

    meta/para (well specified) -> S <= 0  (pinning sigma_hat toward the true Hammett sigma HELPS)
    ortho     (misspecified)   -> S  > 0  (pinning HURTS; the free sigma_hat compensates)

lambda=inf is the fixed-LFER oracle on the true sigma (P=0), already the sigma_oracle arm.

Reuses build_dataset / Encoder / PhysicsGNN / scaffold_split from run_pka_trained_comparison
(no fork of the validated rig; supervision is added in this script's own loop via model.enc/head).

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/experiments/run_pka_lambda_frontier.py \
        --sdf notebooks/data/raw/pKa_QR.sdf --out-json results/frontier/frontier_pka_curve.json
    # wiring smoke: add --smoke
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


def train_eval(cmp, subset, lam, seed, in_dim, hid, layers, epochs, lr, device):
    """train physics arm with L1(pKa) + lam*MSE(sigma_hat, sigma_true); return (P, MAE) on test.

    P = mean|sigma_hat - sigma_true| on the held-out scaffold split; MAE = pKa test MAE.
    Also returns the oracle MAE on the same test split (the lambda=inf, P=0 anchor)."""
    torch.manual_seed(seed)
    tr_idx, te_idx = cmp.scaffold_split(subset, seed)
    tr = [subset[i] for i in tr_idx]
    te = [subset[i] for i in te_idx]
    model = cmp.PhysicsGNN(in_dim, hid, layers).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    l1, mse = nn.L1Loss(), nn.MSELoss()
    loader = DataLoader(tr, batch_size=128, shuffle=True)

    model.train()
    for _ in range(epochs):
        for batch in loader:
            batch = batch.to(device)
            opt.zero_grad()
            z = model.enc(batch.x, batch.edge_index, batch.batch)
            sigma_hat = model.head(z).squeeze(-1)
            pred = batch.pka0.squeeze(-1) - batch.rho.squeeze(-1) * sigma_hat
            loss = l1(pred, batch.pka.squeeze(-1)) + lam * mse(sigma_hat, batch.sigma.squeeze(-1))
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        devs, errs = [], []
        for batch in DataLoader(te, batch_size=256):
            batch = batch.to(device)
            z = model.enc(batch.x, batch.edge_index, batch.batch)
            sigma_hat = model.head(z).squeeze(-1)
            pred = batch.pka0.squeeze(-1) - batch.rho.squeeze(-1) * sigma_hat
            devs.append((sigma_hat - batch.sigma.squeeze(-1)).abs().cpu())
            errs.append((pred - batch.pka.squeeze(-1)).cpu())     # signed residual
        P = float(torch.cat(devs).mean())
        r = torch.cat(errs)
        mae, mse = float(r.abs().mean()), float((r ** 2).mean())   # L2 axis for the law + MAE for continuity
    orc = np.array([float(subset[i].g_oracle) for i in te_idx])
    tru = np.array([float(subset[i].pka) for i in te_idx])
    ro = orc - tru
    mae_oracle, mse_oracle = float(np.mean(np.abs(ro))), float(np.mean(ro ** 2))
    return P, mae, mse, mae_oracle, mse_oracle


def slope(P, mae):
    """S = -d(MAE)/dP across the lambda sweep (>0 = misspecification: physicality costs accuracy)."""
    P, mae = np.asarray(P), np.asarray(mae)
    if P.std() < 1e-9:
        return 0.0
    return float(-np.polyfit(P, mae, 1)[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdf", default="notebooks/data/raw/pKa_QR.sdf")
    ap.add_argument("--out-json", type=Path, default=Path("results/frontier/frontier_pka_curve.json"))
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--lambdas", type=float, nargs="+", default=[0.0, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0])
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    if args.smoke:
        args.epochs, args.seeds, args.lambdas = 3, [42], [0.0, 1.0, 30.0]

    device = torch.device(args.device if (args.device != "cuda" or torch.cuda.is_available()) else "cpu")
    cmp = _load_cmp()
    mod = cmp._load_real_decomp()
    data = cmp.build_dataset(mod, args.sdf)
    in_dim = data[0].x.shape[1]
    strata = {
        "meta/para (well-specified)": [g for g in data if g.fidelity == "high_F"],
        "ortho (misspecified)": [g for g in data if g.fidelity == "low_F"],
    }
    print(f"dataset {len(data)} graphs, in_dim={in_dim}, device={device}; "
          f"lambdas={args.lambdas} seeds={args.seeds} epochs={args.epochs}")

    out = {"config": {"epochs": args.epochs, "seeds": args.seeds, "lambdas": args.lambdas,
                      "hidden": args.hidden, "layers": args.layers}, "strata": {}}
    for label, subset in strata.items():
        if len(subset) < 40:
            continue
        print(f"\n== {label}: n={len(subset)} ==")
        curve, oracle_maes, oracle_mses = [], [], []
        for lam in args.lambdas:
            Ps, maes, mses = [], [], []
            for seed in args.seeds:
                P, mae, mse, mae_orc, mse_orc = train_eval(cmp, subset, lam, seed, in_dim, args.hidden,
                                                           args.layers, args.epochs, args.lr, device)
                Ps.append(P); maes.append(mae); mses.append(mse)
                oracle_maes.append(mae_orc); oracle_mses.append(mse_orc)
            pt = {"lambda": lam, "P_mean": round(float(np.mean(Ps)), 4),
                  "mae_mean": round(float(np.mean(maes)), 4), "mae_sd": round(float(np.std(maes)), 4),
                  "mse_mean": round(float(np.mean(mses)), 4)}
            curve.append(pt)
            print(f"   lambda={lam:>5}: P={pt['P_mean']:.3f}  pKa MAE={pt['mae_mean']:.3f}  MSE={pt['mse_mean']:.3f}")
        mae_oracle = round(float(np.mean(oracle_maes)), 4)
        mse_oracle = round(float(np.mean(oracle_mses)), 4)
        S = slope([p["P_mean"] for p in curve], [p["mae_mean"] for p in curve])           # MAE (continuity)
        S_mse = slope([p["P_mean"] for p in curve], [p["mse_mean"] for p in curve])        # MSE (the law axis)
        out["strata"][label] = {"n": len(subset), "curve": curve,
                                "mae_oracle_laminf_P0": mae_oracle, "mse_oracle_laminf_P0": mse_oracle,
                                "slope_S_mae": round(S, 4), "slope_S_mse": round(S_mse, 4)}
        verdict = "HURTS (misspecified)" if S_mse > 0 else "HELPS (well specified)"
        print(f"   oracle (P=0): MAE={mae_oracle:.3f} MSE={mse_oracle:.3f}")
        print(f"   slope S(MAE)={S:+.4f}  S(MSE)={S_mse:+.4f}  ({verdict})")

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
