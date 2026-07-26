#!/usr/bin/env python3
"""Local (no-GPU) closure correction on the keystone matched set -- the constructive
Tier-3 claim recovered without training the large model, plus the A3 convergence.

Using the TRUE VT-2005 sigma-profiles (n=60 matched IDAC pairs), fit a small
structure-preserving low-rank residual  Delta = B diag(a) B^T  on the fixed COSMO-SAC
exchange-energy kernel so the closure g_Delta(sigma_true) better matches the experimental
ln gamma^inf. Cross-validated. Two questions:

  (1) Is the closure defect low-rank and correctable? -- fit R in {1,2,3}, report the
      held-out MSE reduction vs the fixed closure (R=0). A held-out drop => B_clos is a
      genuine, low-dimensional closure defect a few parameters remove (the Arm-C thesis,
      on TRUE sigma, so no learned-intermediate confound).
  (2) A3 convergence: does Delta concentrate on the same sigma-grid region where the
      learned sigma_hat compensates (the nonpolar->polar shift of sec:surrogate)?
      -- correlate |Delta|'s sigma-marginal with the mean |sigma_hat - sigma_true|.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_local_closure_fix.py \
        --out-json results/compensation/local_closure_fix.json --fig-dir paper/figs
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer

N_BINS = 51
SIGMA_GRID = np.linspace(-0.025, 0.025, N_BINS)
T_REF = 298.15


def _load_binsuff():
    p = Path(__file__).with_name("run_b_insuff_decomposition.py")
    spec = importlib.util.spec_from_file_location("b_insuff", p)
    m = importlib.util.module_from_spec(spec)
    sys.modules["b_insuff"] = m
    spec.loader.exec_module(m)
    return m


def build_tensors(pairs, table):
    p2 = torch.tensor(np.stack([table[k][0] for k in pairs["solute_key"]]), dtype=torch.float)
    A2 = torch.tensor([table[k][1] for k in pairs["solute_key"]], dtype=torch.float)
    p1 = torch.tensor(np.stack([table[k][0] for k in pairs["solvent_key"]]), dtype=torch.float)
    A1 = torch.tensor([table[k][1] for k in pairs["solvent_key"]], dtype=torch.float)
    T = torch.full((len(pairs),), T_REF)
    m = torch.tensor(pairs["m"].to_numpy(), dtype=torch.float)
    return p2, A2, p1, A1, T, m


def fit_kernel(R, tr, p2, A2, p1, A1, T, m, steps=400, lr=5e-2, wd=1e-2, seed=0):
    """Fit the rank-R residual on the train rows; return the layer + train/all MSE fn."""
    cfg = TGNNSolvConfig(activity_model="cosmo_sac", cosmo_sac_kernel_residual_rank=R)
    layer = CosmoSacLayer(cfg=cfg)
    layer.train()
    # The residual init must be seeded: without it the reported held-out MSE is one
    # unreproducible draw and the rank ordering is not stable across draws.
    torch.manual_seed(seed)
    if R > 0:
        with torch.no_grad():
            layer.kernel_B.normal_(0, 1e-2)
        opt = torch.optim.Adam([layer.kernel_B, layer.kernel_a], lr=lr, weight_decay=wd)
        for _ in range(steps):
            opt.zero_grad()
            g = layer.ln_gamma_inf(p2[tr], p1[tr], A2[tr], A1[tr], None, None, T[tr])
            loss = torch.mean((g - m[tr]) ** 2)
            loss.backward()
            opt.step()
    layer.eval()

    def mse(idx):
        with torch.no_grad():
            g = layer.ln_gamma_inf(p2[idx], p1[idx], A2[idx], A1[idx], None, None, T[idx])
            return float(torch.mean((g - m[idx]) ** 2))
    return layer, mse


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    ap.add_argument("--sigma-profiles", default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--ranks", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2],
                    help="fit seeds; the spread over these is reported, not hidden")
    ap.add_argument("--group-by", choices=["none", "solvent"], default="none",
                    help="none = random pair folds; solvent = no solvent shared "
                         "between train and test, which is the leakage-free design")
    ap.add_argument("--sigma-checkpoint", default="checkpoints/cosmo_sac/tgnn_cosmo.pt",
                    help="for the A3 convergence: where sigma_hat deviates from sigma_true")
    ap.add_argument("--out-json", type=Path, default=Path("results/compensation/local_closure_fix.json"))
    ap.add_argument("--fig-dir", type=Path, default=Path("paper/figs"))
    args = ap.parse_args()

    bmod = _load_binsuff()
    table = bmod.load_sigma_profiles(args.sigma_profiles)
    pairs = pd.read_csv(args.matched_csv, low_memory=False)
    pairs = pairs[pairs["solute_key"].isin(table) & pairs["solvent_key"].isin(table)].reset_index(drop=True)
    n = len(pairs)
    print(f"matched pairs with true profiles: {n}")
    p2, A2, p1, A1, T, m = build_tensors(pairs, table)

    # baseline (fixed closure) MSE
    base_layer, base_mse = fit_kernel(0, np.arange(n), p2, A2, p1, A1, T, m)
    base = base_mse(np.arange(n))
    print(f"baseline B_clos (fixed closure, true sigma): MSE = {base:.3f}")

    # ---- fold design -------------------------------------------------------------
    # Random pair folds put the same solvent on both sides of the split. Since the closure
    # error is predominantly a between-solvent systematic, that is leakage, and the 60 matched
    # pairs form a single connected component under shared solute/solvent identity, so no
    # molecule-disjoint holdout exists at all. --group-by solvent is the leakage-free design.
    rng = np.random.default_rng(0)
    if args.group_by == "solvent":
        solv = np.array([str(x) for x in pairs["solvent_key"]]) if "solvent_key" in pairs \
            else np.array([str(x) for x in pairs.iloc[:, 1]])
        uniq, counts = np.unique(solv, return_counts=True)
        order = uniq[np.argsort(-counts)]
        buckets = [[] for _ in range(args.folds)]
        for u in order:                       # greedy balance by size
            buckets[int(np.argmin([sum(len(np.where(solv == v)[0]) for v in b) for b in buckets]))].append(u)
        folds = [np.concatenate([np.where(solv == v)[0] for v in b]) if b else np.array([], int)
                 for b in buckets]
        print(f"fold design: solvent-grouped, sizes {[len(f) for f in folds]}")
    else:
        folds = np.array_split(rng.permutation(n), args.folds)
        print(f"fold design: random pair folds, sizes {[len(f) for f in folds]}")

    results = {"n": n, "baseline_mse": base, "fold_design": args.group_by,
               "seeds": list(args.seeds), "ranks": {}}
    for R in args.ranks:
        per_seed_oos, per_seed_ins, fold_spread = [], [], []
        for sd in args.seeds:
            oos, ins = [], []
            for f in range(args.folds):
                te = folds[f]
                tr = np.concatenate([folds[j] for j in range(args.folds) if j != f])
                if len(te) == 0 or len(tr) == 0:
                    continue
                _, mse = fit_kernel(R, tr, p2, A2, p1, A1, T, m, seed=sd)
                oos.append(mse(te)); ins.append(mse(tr))
            per_seed_oos.append(float(np.mean(oos))); per_seed_ins.append(float(np.mean(ins)))
            fold_spread.append(float(np.std(oos)))
        oos_mse = float(np.mean(per_seed_oos)); ins_mse = float(np.mean(per_seed_ins))
        sd_seed = float(np.std(per_seed_oos))
        results["ranks"][R] = {
            "K": 52 * R, "heldout_mse": oos_mse, "train_mse": ins_mse,
            "heldout_mse_per_seed": per_seed_oos,
            "heldout_sd_over_seeds": sd_seed,
            "heldout_sd_over_folds": float(np.mean(fold_spread)),
            "heldout_reduction_vs_fixed": float(base - oos_mse),
            "heldout_reduction_pct": float(100 * (base - oos_mse) / base),
            "reduction_pct_per_seed": [float(100 * (base - v) / base) for v in per_seed_oos],
        }
        print(f"  R={R} (K={52*R}): held-out MSE {oos_mse:.3f} "
              f"+/- {sd_seed:.3f} over seeds (+/- {np.mean(fold_spread):.3f} over folds)"
              f"  => reduction {100*(base-oos_mse)/base:+.1f}% "
              f"[per seed: {', '.join(f'{100*(base-v)/base:+.0f}%' for v in per_seed_oos)}]")

    # fit the best small rank on ALL data for the deformation map + A3
    bestR = args.ranks[0]
    full_layer, _ = fit_kernel(bestR, np.arange(n), p2, A2, p1, A1, T, m)
    with torch.no_grad():
        Ba = full_layer.kernel_B * full_layer.kernel_a.unsqueeze(0)
        Delta = (Ba @ full_layer.kernel_B.t()).numpy()
    delta_marg = np.abs(Delta).sum(1)                       # sigma-marginal of |Delta|
    delta_marg /= delta_marg.sum() + 1e-12

    # ---- A3: where sigma_hat deviates from true sigma ----
    a3 = {}
    try:
        cs = Path(__file__).with_name("run_compensation_surrogate.py")
        spec = importlib.util.spec_from_file_location("comp", cs)
        cm = importlib.util.module_from_spec(spec); sys.modules["comp"] = cm
        spec.loader.exec_module(cm)
        from tgnn_solv.inference import load_model
        model, _ = load_model(args.sigma_checkpoint, device=torch.device("cpu"))
        true_shapes = cm.load_true_shapes(args.sigma_profiles)
        keep = [(s, cm._canon(s)) for s in sorted(set(pairs["solute_key"]) | set(pairs["solvent_key"]))]
        keep = [(s, c) for s, c in keep if c in true_shapes]
        sig_hat = cm.predict_sigma_hat(model, [s for s, _ in keep], torch.device("cpu"))
        sig_true = np.stack([true_shapes[c] for _, c in keep])
        dev_marg = np.abs(sig_hat - sig_true).mean(0)       # mean |deviation| per sigma-bin
        dev_marg /= dev_marg.sum() + 1e-12
        corr = float(np.corrcoef(delta_marg, dev_marg)[0, 1])
        a3 = {"corr_delta_vs_sigmahat_deviation": corr,
              "verdict": ("CONVERGENT: the closure correction concentrates where the learned "
                          "sigma_hat compensates" if corr > 0.3 else "weak/no convergence")}
        print(f"\nA3 convergence: corr(|Delta| marginal, |sigma_hat-sigma| marginal) = {corr:+.2f}")
    except Exception as e:  # noqa: BLE001
        a3 = {"error": str(e)}
        dev_marg = None
        print(f"\nA3 skipped: {e}")

    results["best_rank_for_map"] = bestR
    results["delta_frobenius"] = float(np.sqrt((Delta ** 2).sum()))
    results["A3"] = a3

    # ---- figure ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(10.0, 4.0))
        vmax = np.abs(Delta).max() or 1.0
        im = ax[0].imshow(Delta, origin="lower", cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                          extent=[SIGMA_GRID[0], SIGMA_GRID[-1], SIGMA_GRID[0], SIGMA_GRID[-1]])
        ax[0].set_xlabel(r"$\sigma_n$"); ax[0].set_ylabel(r"$\sigma_m$")
        ax[0].set_title(f"Fitted closure correction $\\Delta$ (R={bestR})")
        fig.colorbar(im, ax=ax[0], label="kcal/mol")
        ax[1].plot(SIGMA_GRID, delta_marg, color="#c1443c", lw=2, label=r"$|\Delta|$ $\sigma$-marginal (map fix)")
        if dev_marg is not None:
            ax[1].plot(SIGMA_GRID, dev_marg, color="#2f6f8f", lw=2, ls="--",
                       label=r"$|\hat\sigma-\sigma|$ (input compensation)")
        ax[1].set_xlabel(r"$\sigma$"); ax[1].set_ylabel("normalized concentration")
        ax[1].set_title("A3: two routes, one closure defect"); ax[1].legend(fontsize=8)
        fig.tight_layout()
        args.fig_dir.mkdir(parents=True, exist_ok=True)
        for ext in ("pdf", "png"):
            fig.savefig(args.fig_dir / f"fig_local_closure_fix.{ext}", dpi=150)
        results["figure"] = str(args.fig_dir / "fig_local_closure_fix.pdf")
        plt.close(fig)
    except Exception as e:  # noqa: BLE001
        results["figure_error"] = str(e)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(results, indent=2))
    print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
