"""Step 0 (near-zero compute): does the L1-training / L2-metric mismatch actually bite?

The money-plot needs the frontier on an L2 axis (Lemma 2's B = B_closure + B_insuff has no L1
analog -- the cross-term only vanishes by the tower property in L2). The open question is whether
the *existing* L1-trained pKa frontier can be reused, or whether an L2 retrain is mandatory.

Controlled synthetic decides it. A head trained under L1 targets the conditional MEDIAN; B_closure
is defined via the conditional MEAN. They coincide iff residuals are symmetric. So sweep the 2x2:
    {training loss: L1, L2} x {noise: symmetric gauss, right-skewed}
and read S_norm at F=1 (closure exactly specified) under the MSE report metric:
    * S_norm_MSE(F=1) ~= 0 in every cell            -> mismatch is benign, reuse the L1 frontier.
    * S_norm_MSE(F=1) moves off 0 under L1 + skew    -> the median/mean gap bites -> L2 retrain needed.

The real pKa residuals are heavy-tailed/skewed (cf. the solubility headline: MAE +22% while R2
collapses +0.33->-0.03 -> second moment moves far more than first), so the L1+skew cell is the
one that mirrors the deployed setup.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_frontier_metric_diagnostic.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent


def _load_a1():
    spec = importlib.util.spec_from_file_location("a1_frontier", HERE / "run_physicality_frontier.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["a1_frontier"] = m   # needed so @dataclass introspection works
    spec.loader.exec_module(m)
    return m


def make_noise(kind, n, sd, gen):
    if kind == "gauss":
        return torch.randn(n, generator=gen, dtype=torch.float64) * sd
    # right-skewed, zero-mean: Exp(1)-1 (median ln2-1 ~ -0.31, mean 0) -> median != mean
    e = torch.empty(n, dtype=torch.float64)
    e.exponential_(1.0, generator=gen)
    return (e - 1.0) * sd


def train_eval(a1, family, shape_name, F, lam, loss_kind, noise_kind, z_tr, z_te, W, snr, steps, hid, seed):
    torch.manual_seed(seed)
    T, D = a1.teacher(family, W), a1.shape(shape_name, W)
    t_tr = T(z_tr); sig = float(t_tr.std())
    d_tr = D(z_tr); muD, sdD = float(d_tr.mean()), float(d_tr.std()) or 1.0
    alpha = 1.0 - F

    def g_F(z):
        return T(z) + alpha * sig * (D(z) - muD) / sdD

    noise_sd = sig / np.sqrt(snr) if sig > 0 else 1.0 / np.sqrt(snr)
    gen = torch.Generator().manual_seed(seed + 1)
    m_tr = (t_tr + make_noise(noise_kind, z_tr.shape[0], noise_sd, gen)).detach()
    m_te = (T(z_te) + make_noise(noise_kind, z_te.shape[0], noise_sd, gen)).detach()
    mae_ref, mse_ref = float(m_te.abs().mean()), float((m_te ** 2).mean())  # scale refs

    head = a1.Head(z_tr.shape[1], hid)
    opt = torch.optim.Adam(head.parameters(), lr=5e-3, weight_decay=1e-5)
    for _ in range(steps):
        opt.zero_grad()
        zh = head(z_tr)
        resid = m_tr - g_F(zh)
        fit = resid.abs().mean() if loss_kind == "l1" else (resid ** 2).mean()
        (fit + lam * ((zh - z_tr) ** 2).mean()).backward()
        opt.step()
    with torch.no_grad():
        zh = head(z_te)
        D_dev = float(torch.linalg.norm(zh - z_te, dim=1).mean() / (torch.linalg.norm(z_te, dim=1).mean() + 1e-12))
        r = m_te - g_F(zh)
        return D_dev, float(r.abs().mean()), float((r ** 2).mean())


def s_norm(D, metric):
    D, y = np.asarray(D, float), np.asarray(metric, float)
    Df, yf = D[0], y[0]
    if Df <= 0 or yf <= 0 or (D / Df).std() < 1e-9:
        return 0.0
    return float(-np.polyfit(D / Df, y / yf, 1)[0])


def main():
    a1 = _load_a1()
    d, n, snr, steps, hid, seed = 6, 2500, 8.0, 400, 32, 0
    fams = ["linear", "pde_field"]; shp = "quadratic"
    Fs = [1.0, 0.7, 0.4]; lams = [0.0, 0.1, 0.5, 2.0, 10.0]
    rng = np.random.default_rng(seed)
    W = a1.make_weights(rng, d)
    z = torch.tensor(rng.standard_normal((n, d)), dtype=torch.float64)
    z_tr, z_te = z[: int(0.8 * n)], z[int(0.8 * n):]

    print("Metric/loss diagnostic -- S_norm at each cell (MAE report vs MSE report)")
    print(f"  {'loss':>4} {'noise':>6} {'F':>5} {'S_norm(MAE)':>12} {'S_norm(MSE)':>12}")
    out = {"cells": []}
    for loss_kind in ("l2", "l1"):
        for noise_kind in ("gauss", "skew"):
            for F in Fs:
                Ds, maes, mses = [], [], []
                for fam in fams:
                    curve = [train_eval(a1, fam, shp, F, lam, loss_kind, noise_kind,
                                        z_tr, z_te, W, snr, steps, hid, seed) for lam in lams]
                    Ds.append([c[0] for c in curve]); maes.append([c[1] for c in curve]); mses.append([c[2] for c in curve])
                Sm = float(np.mean([s_norm(Ds[i], maes[i]) for i in range(len(fams))]))
                Ss = float(np.mean([s_norm(Ds[i], mses[i]) for i in range(len(fams))]))
                out["cells"].append({"loss": loss_kind, "noise": noise_kind, "F": F,
                                     "S_norm_mae": round(Sm, 3), "S_norm_mse": round(Ss, 3)})
                print(f"  {loss_kind:>4} {noise_kind:>6} {F:>5.2f} {Sm:>+12.3f} {Ss:>+12.3f}")

    # verdict: is S_norm_MSE(F=1) ~= 0 in the L1+skew cell (mirrors deployed pKa)?
    l1skew_f1 = next(c["S_norm_mse"] for c in out["cells"]
                     if c["loss"] == "l1" and c["noise"] == "skew" and c["F"] == 1.0)
    l2gauss_f1 = next(c["S_norm_mse"] for c in out["cells"]
                      if c["loss"] == "l2" and c["noise"] == "gauss" and c["F"] == 1.0)
    out["verdict"] = {"l1_skew_Snorm_mse_F1": l1skew_f1, "l2_gauss_Snorm_mse_F1": l2gauss_f1,
                      "retrain_needed": abs(l1skew_f1) > 0.1}
    Path("results/frontier/metric_diagnostic.json").write_text(json.dumps(out, indent=2))
    print(f"\n  L2/gauss S_norm_MSE(F=1) = {l2gauss_f1:+.3f}  (reference, should be ~0)")
    print(f"  L1/skew  S_norm_MSE(F=1) = {l1skew_f1:+.3f}  (mirrors deployed pKa)")
    print(f"  => L2 retrain needed: {abs(l1skew_f1) > 0.1}")


if __name__ == "__main__":
    main()
