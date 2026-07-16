"""Money-plot: S_norm(MSE) vs measured B_closure(L2) -- the cross-system test (not range containment).

Ingredients, all L2 now:
  * S_norm(MSE) = -d(MSE/MSE_free)/d(D/D_free)  from the MSE frontiers.
  * B_closure_norm = B_closure / Var(m)          from the Lemma-2 decomposition (identical def
    in synthetic and real).
Two guards the reviewer demanded:
  (b) matched infidelity -- the synthetic sweeps D/D_free down to ~0.05, pKa only to ~0.22, and the
      frontier is nonlinear, so the two-point/full slope is range-dependent. We recompute every
      slope over the COMMON D/D_free window and compare like with like.
  (c) meta/para excluded (variance-contaminated AND metric-unstable: its MSE-oracle > best trained).

Prints the synthetic S_norm-vs-B_closure curve and where the real ortho point lands, both naively
and at matched infidelity. Honest: if ortho does not land on the synthetic line, the law is not a
single curve under this construction and we say so.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_frontier_scatter.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
SNR = 8.0

# fetched-SDF decomposition (run_pka_real_decomposition) + Var(pKa) computed on the same SDF
PKA_BCLOS = {"ortho": 0.7539, "meta/para": 0.5499}
PKA_VAR = {"ortho": 9.612, "meta/para": 8.235}


def _load_diag():
    spec = importlib.util.spec_from_file_location("diag", HERE / "run_frontier_metric_diagnostic.py")
    m = importlib.util.module_from_spec(spec); sys.modules["diag"] = m
    spec.loader.exec_module(m)
    return m


def snorm(D, y, dmin=0.0):
    """-d(y/y_free)/d(D/D_free) over points with D/D_free >= dmin (matched-infidelity window)."""
    D, y = np.asarray(D, float), np.asarray(y, float)
    Df, yf = D[0], y[0]
    x = D / Df
    keep = x >= dmin
    if keep.sum() < 2 or x[keep].std() < 1e-9:
        return float("nan")
    return float(-np.polyfit(x[keep], (y / yf)[keep], 1)[0])


def main():
    diag = _load_diag(); a1 = diag._load_a1()
    # --- synthetic dense-F frontier in MSE (L2 train, gauss) ---
    d, n, steps, hid, seed = 6, 2500, 400, 32, 0
    fams, shp = ["linear", "monotone_nonlinear", "pde_field"], "quadratic"
    lams = [0.0, 0.05, 0.2, 0.8, 3.0, 12.0]
    Fgrid = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
    rng = np.random.default_rng(seed); W = a1.make_weights(rng, d)
    z = torch.tensor(rng.standard_normal((n, d)), dtype=torch.float64)
    z_tr, z_te = z[: int(0.8 * n)], z[int(0.8 * n):]

    # pKa ortho common infidelity floor (D/D_free range it actually reaches)
    pk = json.loads(Path("results/frontier/frontier_pka_curve_l2.json").read_text())
    o = pk["strata"]["ortho (misspecified)"]["curve"]
    oD = [c["P_mean"] for c in o]; oMSE = [c["mse_mean"] for c in o]
    dmin = min(d_ / oD[0] for d_ in oD)          # ortho only reaches this normalized infidelity
    print(f"matched-infidelity window: D/D_free in [{dmin:.2f}, 1.00]  (set by pKa ortho reach)\n")

    syn = []
    for F in Fgrid:
        Ss, Ssm = [], []
        for fam in fams:
            curve = [diag.train_eval(a1, fam, shp, F, lam, "l2", "gauss", z_tr, z_te, W, SNR, steps, hid, seed) for lam in lams]
            D = [c[0] for c in curve]; MSE = [c[2] for c in curve]
            Ss.append(snorm(D, MSE)); Ssm.append(snorm(D, MSE, dmin))
        Bc = (1 - F) ** 2 / (1 + 1 / SNR)
        syn.append({"F": F, "B_closure_norm": round(Bc, 3),
                    "S_norm_full": round(float(np.nanmean(Ss)), 3),
                    "S_norm_matched": round(float(np.nanmean(Ssm)), 3)})

    # fit synthetic law on the MATCHED slopes
    Bs = np.array([s["B_closure_norm"] for s in syn]); Sm = np.array([s["S_norm_matched"] for s in syn])
    b, a = np.polyfit(Bs, Sm, 1)

    # --- real ortho point ---
    o_Snorm_full = snorm(oD, oMSE); o_Snorm_matched = snorm(oD, oMSE, dmin)   # ortho already spans the window
    o_Bc = PKA_BCLOS["ortho"] / PKA_VAR["ortho"]
    pred = a + b * o_Bc

    print(f"{'F':>4} {'B_clos_norm':>12} {'S_norm(full)':>13} {'S_norm(matched)':>16}")
    for s in syn:
        print(f"{s['F']:>4.2f} {s['B_closure_norm']:>12.3f} {s['S_norm_full']:>13.3f} {s['S_norm_matched']:>16.3f}")
    print(f"\nsynthetic law (matched): S_norm = {a:+.3f} + {b:.2f} * B_closure_norm")
    print(f"\npKa ortho: B_closure_norm = {o_Bc:.3f} (B_clos_lb {PKA_BCLOS['ortho']}/Var {PKA_VAR['ortho']})")
    print(f"  S_norm(full)   = {o_Snorm_full:+.3f}")
    print(f"  S_norm(matched)= {o_Snorm_matched:+.3f}   vs synthetic-predicted {pred:+.3f}")
    lands = abs(o_Snorm_matched - pred) < 0.15
    print(f"  => ortho lands on the synthetic line: {lands}  (|resid|={abs(o_Snorm_matched-pred):.3f})")

    Path("results/frontier/frontier_scatter.json").write_text(json.dumps(
        {"snr": SNR, "matched_window_dmin": round(dmin, 3), "synthetic": syn,
         "synthetic_fit_matched": {"intercept": round(a, 3), "slope": round(b, 3)},
         "pka_ortho": {"B_closure_norm": round(o_Bc, 3), "S_norm_full": round(o_Snorm_full, 3),
                       "S_norm_matched": round(o_Snorm_matched, 3), "predicted": round(pred, 3),
                       "lands_on_line": bool(lands)}}, indent=2))
    print("\nwrote results/frontier/frontier_scatter.json")


if __name__ == "__main__":
    main()
