#!/usr/bin/env python3
"""Tier-1 closure-fix crossover (constructive complement to the grounding paradox).

The paper's negatives say a physics prior does not help and that a downstream output
residual (Gate B) does not recover accuracy. The constructive claim this script tests:
spend a *matched* budget where the closure/insufficiency split points and it DOES help,
and the winning locus *flips* with the split -- so the diagnostic is prescriptive, not
just descriptive.

Controlled synthetic with KNOWN channels (reuses the teacher/misspecification engine of
run_fidelity_dial.py). One world carries both error channels at once, each on its own knob:

  intermediate z* = captured coords (what the closure sees)
  discarded coords x_dis = target-relevant info the intermediate lacks   -> B_insuff knob (beta)
  fixed misspecified closure g_F(z*) = T(z*) + (1-F)*D(z*)                -> B_clos  knob (F)
  target m = T(z*) + beta * dis(x_dis) + noise

  B_clos   = E[(E[m|z*] - g_F(z*))^2] = (1-F)^2               (map wrong on info it HAS)
  B_insuff = Var(beta * dis)          = beta^2                (info the intermediate LACKS)

Three matched-budget arms each add K random-Fourier features + ridge, fit to the physics
residual m - g_F(z*), differing only in WHICH input (=information) they may use:

  C (closure-fix) : features of z* only        -> can remove B_clos, structurally not B_insuff
  I (input-fix)   : features of x_dis          -> can remove B_insuff, structurally not B_clos
  O (agnostic)    : features of the full raw x -> the downstream-residual baseline (both, spread thin)

Budget = K learnable ridge weights, identical across arms (the RFF projection is random,
not learned). Two views:
  * matched-headroom SWEEP -- hold B_clos+B_insuff=R fixed, sweep the split theta -> a clean
    X-crossover (gain_C rises, gain_I falls, cross at theta=0.5 i.e. log-ratio 0);
  * full (F,beta) GRID -- robustness: the fraction of grid cells whose winner matches
    sign(B_clos - B_insuff).

numpy + scikit-learn/matplotlib only (no torch/rdkit -> no libomp conflict).

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_closure_fix_dial.py \
        --out-json results/closure_fix_dial/summary.json --fig-dir paper/figs --seeds 0 1 2 3 4
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np

# --- reuse the EXACT teacher/misspecification engine from the fidelity dial ---
_dial_path = Path(__file__).with_name("run_fidelity_dial.py")
_spec = importlib.util.spec_from_file_location("run_fidelity_dial", _dial_path)
_dial = importlib.util.module_from_spec(_spec)
sys.modules["run_fidelity_dial"] = _dial  # so @dataclass can resolve cls.__module__
_spec.loader.exec_module(_dial)
make_teachers, make_shapes, standardize = _dial.make_teachers, _dial.make_shapes, _dial.standardize


# --------------------------------------------------------------------------- #
# matched-budget learner: K random-Fourier features + closed-form ridge.
# The random projection is NOT learned; the K ridge weights ARE -> budget = K.
# --------------------------------------------------------------------------- #
def _rff(X: np.ndarray, W: np.ndarray, b: np.ndarray) -> np.ndarray:
    K = W.shape[1]
    return np.sqrt(2.0 / K) * np.cos(X @ W + b)


def _ridge_residual_fit(feat_tr, resid_tr, feat_te, K, lengthscale, lam, rng) -> np.ndarray:
    din = feat_tr.shape[1]
    W = rng.standard_normal((din, K)) / lengthscale
    b = rng.uniform(0.0, 2.0 * np.pi, size=K)
    Phi_tr, Phi_te = _rff(feat_tr, W, b), _rff(feat_te, W, b)
    A = Phi_tr.T @ Phi_tr + lam * np.eye(K)
    w = np.linalg.solve(A, Phi_tr.T @ resid_tr)
    return Phi_te @ w


def _mse(a, b) -> float:
    return float(np.mean((a - b) ** 2))


def _eval_cell(z_all, xdis_all, t_all, dis_all, Dunit_all, one_minus_F, beta,
               snr, tr, te, K, rng_base):
    """One (fidelity, insufficiency) world: build the target, run all three matched arms.
    Returns (gains dict C/I/O, b_clos, b_insuff, base_mse)."""
    gF_all = t_all + one_minus_F * Dunit_all
    signal_all = t_all + beta * dis_all
    noise_sd = signal_all.std() / np.sqrt(snr)
    # deterministic noise from rng_base so the cell is reproducible
    m_all = signal_all + rng_base.standard_normal(len(t_all)) * noise_sd
    base_te = _mse(m_all[te], gF_all[te])
    b_clos = _mse(t_all[te], gF_all[te])
    b_insuff = float(np.mean((beta * dis_all[te]) ** 2))
    resid_tr = m_all[tr] - gF_all[tr]
    feats = {
        "C": (z_all[tr], z_all[te], float(np.sqrt(z_all.shape[1]))),
        "I": (xdis_all[tr], xdis_all[te], float(np.sqrt(xdis_all.shape[1]))),
        "O": (np.column_stack([z_all[tr], xdis_all[tr]]),
              np.column_stack([z_all[te], xdis_all[te]]),
              float(np.sqrt(z_all.shape[1] + xdis_all.shape[1]))),
    }
    gains = {}
    for arm, (ftr, fte, ls) in feats.items():
        # each arm draws its own random-feature projection from the cell rng (deterministic,
        # independent per arm, varies by seed/cell); ridge weights are the matched budget K.
        corr = _ridge_residual_fit(ftr, resid_tr, fte, K, ls, lam=1e-1, rng=rng_base)
        gains[arm] = base_te - _mse(m_all[te], gF_all[te] + corr)
    return gains, b_clos, b_insuff, base_te


# --------------------------------------------------------------------------- #
# full (F, beta) grid  -> robustness statistic (winner matches split sign)
# --------------------------------------------------------------------------- #
@dataclass
class CrossRecord:
    family: str
    shape: str
    fidelity: float
    beta: float
    seed: int
    b_clos: float
    b_insuff: float
    base_mse: float
    gain_C: float
    gain_I: float
    gain_O: float
    log_ratio: float


def _world(rng, T, D, wdis, n, d, kdis):
    z_all = rng.standard_normal((2 * n, d))
    xdis_all = rng.standard_normal((2 * n, kdis))
    t_all = standardize(np.asarray(T(z_all), dtype=float))
    dis_all = standardize(np.asarray(xdis_all @ wdis, dtype=float))
    Dunit_all = standardize(np.asarray(D(z_all), dtype=float))
    return z_all, xdis_all, t_all, dis_all, Dunit_all


def run_grid(seeds, n, d, kdis, snr, K, fidelities, betas, shapes_subset):
    records = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        teachers = make_teachers(rng, d)
        shapes = make_shapes(rng, d)
        if shapes_subset:
            shapes = {k: v for k, v in shapes.items() if k in shapes_subset}
        wdis = rng.standard_normal(kdis) / np.sqrt(kdis)
        for fam_idx, (fam, T) in enumerate(teachers.items()):
            for sh_idx, (sh, D) in enumerate(shapes.items()):
                z_all, xdis_all, t_all, dis_all, Dunit_all = _world(rng, T, D, wdis, n, d, kdis)
                tr, te = slice(0, n), slice(n, 2 * n)
                for F in fidelities:
                    for beta in betas:
                        rng_cell = np.random.default_rng(np.random.SeedSequence(
                            [seed, fam_idx, sh_idx, int((1 - F) * 1e6), int(beta * 1e6)]))
                        gains, bc, bi, base = _eval_cell(
                            z_all, xdis_all, t_all, dis_all, Dunit_all,
                            1.0 - F, beta, snr, tr, te, K, rng_cell)
                        records.append(CrossRecord(
                            family=fam, shape=sh, fidelity=float(F), beta=float(beta), seed=seed,
                            b_clos=bc, b_insuff=bi, base_mse=base,
                            gain_C=gains["C"], gain_I=gains["I"], gain_O=gains["O"],
                            log_ratio=float(np.log(max(bc, 1e-9) / max(bi, 1e-9)))))
    return records


# --------------------------------------------------------------------------- #
# matched-headroom sweep  -> clean X-crossover (hold B_clos+B_insuff=R, sweep split)
# --------------------------------------------------------------------------- #
def run_matched_sweep(seeds, n, d, kdis, snr, K, R, thetas, shapes_subset):
    acc = {float(th): defaultdict(list) for th in thetas}
    for seed in seeds:
        rng = np.random.default_rng(1000 + seed)
        teachers = make_teachers(rng, d)
        shapes = make_shapes(rng, d)
        if shapes_subset:
            shapes = {k: v for k, v in shapes.items() if k in shapes_subset}
        wdis = rng.standard_normal(kdis) / np.sqrt(kdis)
        for fam_idx, (fam, T) in enumerate(teachers.items()):
            for sh_idx, (sh, D) in enumerate(shapes.items()):
                z_all, xdis_all, t_all, dis_all, Dunit_all = _world(rng, T, D, wdis, n, d, kdis)
                tr, te = slice(0, n), slice(n, 2 * n)
                for th in thetas:
                    one_minus_F = float(np.sqrt(R * th))       # B_clos target = R*theta
                    beta = float(np.sqrt(R * (1.0 - th)))      # B_insuff target = R*(1-theta)
                    rng_cell = np.random.default_rng(np.random.SeedSequence(
                        [seed, fam_idx, sh_idx, int(th * 1e6), 7]))
                    gains, bc, bi, base = _eval_cell(
                        z_all, xdis_all, t_all, dis_all, Dunit_all,
                        one_minus_F, beta, snr, tr, te, K, rng_cell)
                    a = acc[float(th)]
                    a["C"].append(gains["C"]); a["I"].append(gains["I"]); a["O"].append(gains["O"])
                    a["bc"].append(bc); a["bi"].append(bi)
    sweep = []
    for th in thetas:
        a = acc[float(th)]
        sweep.append({
            "theta": float(th),
            "log_ratio": float(np.log(max(np.mean(a["bc"]), 1e-9) / max(np.mean(a["bi"]), 1e-9))),
            "b_clos": float(np.mean(a["bc"])), "b_insuff": float(np.mean(a["bi"])),
            "gain_C": float(np.mean(a["C"])), "gain_C_sd": float(np.std(a["C"])),
            "gain_I": float(np.mean(a["I"])), "gain_I_sd": float(np.std(a["I"])),
            "gain_O": float(np.mean(a["O"])), "gain_O_sd": float(np.std(a["O"])),
        })
    return sweep


def _grid_stats(recs):
    x = np.array([r.log_ratio for r in recs])
    dCI = np.array([r.gain_C - r.gain_I for r in recs])
    agree = float(np.mean(np.sign(dCI) == np.sign(x)))
    # fraction C-wins per log-ratio bin (for the sigmoid panel)
    edges = np.quantile(x, np.linspace(0, 1, 11))
    bins = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (x >= lo) & (x <= hi)
        if mask.sum():
            bins.append({"log_ratio_mid": float((lo + hi) / 2),
                         "frac_C_wins": float(np.mean(dCI[mask] > 0)),
                         "n": int(mask.sum())})
    return {"frac_winner_matches_split_sign": agree, "bins": bins}


def make_figure(sweep, grid_stats, fig_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir.mkdir(parents=True, exist_ok=True)
    lr = np.array([s["log_ratio"] for s in sweep])
    gC = np.array([s["gain_C"] for s in sweep]); sC = np.array([s["gain_C_sd"] for s in sweep])
    gI = np.array([s["gain_I"] for s in sweep]); sI = np.array([s["gain_I_sd"] for s in sweep])
    gO = np.array([s["gain_O"] for s in sweep]); sO = np.array([s["gain_O_sd"] for s in sweep])

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
    # Panel A: matched-headroom X-crossover
    for g, s, lab, col in [(gC, sC, "closure-fix (C)", "#c1443c"),
                           (gI, sI, "input-fix (I)", "#2f6f8f"),
                           (gO, sO, "agnostic downstream (O)", "#8a8a8a")]:
        axes[0].plot(lr, g, marker="o", ms=4, lw=2, color=col, label=lab)
        axes[0].fill_between(lr, g - s, g + s, color=col, alpha=0.15)
    axes[0].axvline(0, color="0.6", lw=0.8, ls=":")
    axes[0].set_xlabel(r"measured split  $\log(B_{\rm clos}/B_{\rm insuff})$")
    axes[0].set_ylabel("error removed at matched budget (MSE)")
    axes[0].set_title("Matched headroom ($B_{\\rm clos}{+}B_{\\rm insuff}$ fixed):\n"
                      "the winning locus follows the split")
    axes[0].legend(fontsize=8)

    # Panel B: fraction of grid cells where closure-fix wins (robustness sigmoid)
    mids = np.array([b["log_ratio_mid"] for b in grid_stats["bins"]])
    frac = np.array([b["frac_C_wins"] for b in grid_stats["bins"]])
    axes[1].axhline(0.5, color="0.6", lw=0.8, ls="--")
    axes[1].axvline(0, color="0.6", lw=0.8, ls=":")
    axes[1].plot(mids, frac, marker="s", ms=5, lw=2, color="#5a3a86")
    axes[1].set_ylim(-0.03, 1.03)
    axes[1].set_xlabel(r"measured split  $\log(B_{\rm clos}/B_{\rm insuff})$")
    axes[1].set_ylabel("fraction of cells where closure-fix wins")
    axes[1].set_title(f"Full ($F,\\beta$) grid, {int(100*grid_stats['frac_winner_matches_split_sign'])}%"
                      " winner$=$split sign\n(the crossover is at 0)")
    fig.tight_layout()
    written = []
    for ext in ("pdf", "png"):
        p = fig_dir / f"fig_closure_fix_crossover.{ext}"
        fig.savefig(p, dpi=150); written.append(str(p))
    plt.close(fig)
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--d", type=int, default=6)
    ap.add_argument("--kdis", type=int, default=4)
    ap.add_argument("--snr", type=float, default=12.0)
    ap.add_argument("--K", type=int, default=64)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--R", type=float, default=0.4, help="fixed total headroom B_clos+B_insuff for the sweep")
    ap.add_argument("--thetas", type=float, nargs="+",
                    default=[0.05, 0.15, 0.3, 0.45, 0.55, 0.7, 0.85, 0.95])
    ap.add_argument("--fidelities", type=float, nargs="+", default=[1.0, 0.85, 0.7, 0.55, 0.4, 0.25])
    ap.add_argument("--betas", type=float, nargs="+", default=[0.05, 0.2, 0.4, 0.6, 0.85, 1.2])
    ap.add_argument("--shapes", type=str, nargs="*", default=None)
    ap.add_argument("--out-json", type=Path, default=Path("results/closure_fix_dial/summary.json"))
    ap.add_argument("--fig-dir", type=Path, default=Path("paper/figs"))
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()

    grid = run_grid(args.seeds, args.n, args.d, args.kdis, args.snr, args.K,
                    args.fidelities, args.betas, args.shapes)
    gstats = _grid_stats(grid)
    sweep = run_matched_sweep(args.seeds, args.n, args.d, args.kdis, args.snr, args.K,
                              args.R, args.thetas, args.shapes)
    figs = [] if args.no_figures else make_figure(sweep, gstats, args.fig_dir)

    def regime(pred):
        sub = [r for r in grid if pred(r)]
        if not sub:
            return None
        return {"n": len(sub),
                "gain_C": float(np.mean([r.gain_C for r in sub])),
                "gain_I": float(np.mean([r.gain_I for r in sub])),
                "gain_O": float(np.mean([r.gain_O for r in sub])),
                "b_clos": float(np.mean([r.b_clos for r in sub])),
                "b_insuff": float(np.mean([r.b_insuff for r in sub]))}

    out = {
        "config": {"n": args.n, "d": args.d, "kdis": args.kdis, "snr": args.snr, "K": args.K,
                   "seeds": args.seeds, "R": args.R, "thetas": args.thetas},
        "grid_stats": gstats,
        "matched_sweep": sweep,
        "closure_dominated_regime_mean": regime(lambda r: r.log_ratio > 1.0),
        "insufficiency_dominated_regime_mean": regime(lambda r: r.log_ratio < -1.0),
        "grid_records": [asdict(r) for r in grid],
        "figures": figs,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2))

    print(f"[closure-fix] wrote {args.out_json}  (grid {len(grid)} cells, sweep {len(sweep)} points)")
    print(f"[closure-fix] winner matches split sign in "
          f"{100*gstats['frac_winner_matches_split_sign']:.1f}% of grid cells")
    print("\n  matched-headroom sweep (B_clos+B_insuff=%.2f fixed):" % args.R)
    print(f"  {'theta':>6}{'logratio':>10}{'gain_C':>9}{'gain_I':>9}{'gain_O':>9}")
    for s in sweep:
        print(f"  {s['theta']:>6.2f}{s['log_ratio']:>10.2f}{s['gain_C']:>+9.3f}"
              f"{s['gain_I']:>+9.3f}{s['gain_O']:>+9.3f}")
    if figs:
        print("\n[closure-fix] figures:", ", ".join(figs))


if __name__ == "__main__":
    main()
