#!/usr/bin/env python3
r"""What the OUTER SLE iteration count is worth, measured on the scored rows.

WHY THIS EXISTS
---------------
Two counts decide the solubility number and neither was printed anywhere in the
submission: ``n_iter_train=5`` and ``n_iter_eval=20`` (``config.py``,
``configs/cosmo_sac.yaml``).  They are the SLE fixed point's counts -- the outer loop of
``solver.SLESolver`` -- and they are NOT the segment-loop counts
``cosmo_sac_gamma_iter_train/eval`` (16/30) that ``tests/test_cosmo_sac_iter_convergence.py``
guards and that the Supporting Information's COSMO-SAC-constants paragraph prints.  The
segment count is already known to be a lever worth ~1 ln-unit of MAE when swept alone
(CLAUDE.md); this script asks the same question of the outer count, which had no test and
no disclosure.

WHAT IT MEASURES, AND WHY IT NEEDS NO CHECKPOINT
------------------------------------------------
The NRTL SLE map closes in ``(Phi, tau_12, tau_21, G_12, G_21)`` alone.  Four of those
five are recoverable from the deposited per-row predictions:

    Phi, tau_12, tau_21, ln_gamma_inf     deposited columns
    ln_gamma_inf = tau_12 + tau_21 G_21   NRTLLayer.ln_gamma_inf, inverted for G_21
    alpha_12 = -ln(G_21)/tau_21           NRTLLayer.compute_tau_G_ref_invT, inverted
    G_12 = exp(-alpha_12 tau_12)

so the whole kernel is identified row by row and the repo's own ``_iterate_fixed_point``
can be re-run over it at any count.  No checkpoint, no GPU, no retraining.  The COSMO-SAC
arms cannot be done this way: their kernel is a sigma-profile pair and the profiles are
not deposited, so the measurement is on the NRTL closure only.

THE GATES
---------
identification  the recovered kernel must reproduce the deposited ``ln_gamma_2`` at the
                deposited ``x2``.  Rows that fail are dropped and counted (the inversion
                is ill-conditioned where ``tau_21`` is float32-zero).
reproduction    re-running at the evaluation setting (20 iterations, tol 1e-7) must
                reproduce the deposited ``ln_x2_physics``.  This is the instrument's proof
                that it is the same solver the run used.
null arm        the ideal closure (tau_12 = tau_21 = 0, G = 1) has no x2 dependence at
                all, so its 5-vs-20 difference must be exactly zero.  An instrument that
                returns a number on that is measuring its own arithmetic.

Note the measured quantity is the SOLVER's output ``ln_x2_physics``, before the bounded
adaptive correction, so the MAEs here are not the arm's published MAE.

USAGE
-----
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python \
        scripts/analysis/run_outer_sle_iteration_audit.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from tgnn_solv.layers import NRTLLayer
from tgnn_solv.solver import _iterate_fixed_point

# The pinned schedule (configs/cosmo_sac.yaml, configs/paper_config_nrtl_h64L3.yaml).
N_TRAIN, TOL_TRAIN = 5, 1.0e-5
N_EVAL, TOL_EVAL = 20, 1.0e-7
N_CONVERGED, TOL_CONVERGED = 200, 0.0
DAMPING, MIN_DAMPING = 0.7, 0.1
EPS = 1e-10                      # cfg.eps, used in ln_x2 = log(x2 + eps)
IDENT_TOL = 1e-3                 # ln gamma_2 agreement required to call a kernel identified

_LAYER = NRTLLayer()
_LAYER.eps = EPS


def _solve(Phi, t12, t21, G12, G21, n_iter, tol):
    x2, _ = _iterate_fixed_point(
        Phi, t12, t21, G12, G21, n_iter=n_iter, damping=DAMPING,
        min_damping=MIN_DAMPING, tol=tol, adaptive_damping=True, nrtl_layer=_LAYER,
    )
    return torch.log(x2 + EPS)


def _col(df, name):
    return torch.tensor(df[name].to_numpy(), dtype=torch.float64)


def audit_seed(path: Path) -> dict:
    df = pd.read_csv(path)
    df = df[df["has_solubility"].astype(bool)].reset_index(drop=True)
    Phi, t12, t21 = _col(df, "Phi"), _col(df, "tau_12"), _col(df, "tau_21")
    lgi, y = _col(df, "ln_gamma_inf"), _col(df, "ln_x2_true")
    dep, dep_g2 = _col(df, "ln_x2_physics"), _col(df, "ln_gamma_2")

    G21 = (lgi - t12) / t21
    alpha = -torch.log(G21.clamp_min(1e-300)) / t21
    alpha = torch.where(torch.isfinite(alpha), alpha, torch.zeros_like(alpha))
    G21, G12 = torch.exp(-alpha * t21), torch.exp(-alpha * t12)

    x2dep = torch.exp(dep)
    ident = (_LAYER.ln_gamma_2(1 - x2dep, x2dep, t12, t21, G12, G21) - dep_g2).abs()
    keep = ident < IDENT_TOL

    ln_t = _solve(Phi, t12, t21, G12, G21, N_TRAIN, TOL_TRAIN)[keep]
    ln_e = _solve(Phi, t12, t21, G12, G21, N_EVAL, TOL_EVAL)[keep]
    ln_c = _solve(Phi, t12, t21, G12, G21, N_CONVERGED, TOL_CONVERGED)[keep]
    yk, depk = y[keep], dep[keep]

    d = (ln_e - ln_t).abs().numpy()
    repro = (ln_e - depk).abs()
    return dict(
        file=str(path), n_rows=int(len(df)), n_identified=int(keep.sum()),
        gate_identification_max=float(ident[keep].max()),
        gate_reproduction_mean=float(repro.mean()),
        gate_reproduction_max=float(repro.max()),
        mae_train_count=float((ln_t - yk).abs().mean()),
        mae_eval_count=float((ln_e - yk).abs().mean()),
        mae_converged=float((ln_c - yk).abs().mean()),
        mae_deposited=float((depk - yk).abs().mean()),
        row_gap_mean=float(d.mean()), row_gap_p50=float(np.median(d)),
        row_gap_p95=float(np.percentile(d, 95)), row_gap_p99=float(np.percentile(d, 99)),
        row_gap_max=float(d.max()),
        frac_row_gap_gt_005=float(np.mean(d > 0.05)),
        frac_row_gap_gt_020=float(np.mean(d > 0.20)),
        _gap=d,
    )


def null_arm(path: Path) -> dict:
    """Ideal closure: no x2 dependence, so the count cannot move anything."""
    df = pd.read_csv(path)
    df = df[df["has_solubility"].astype(bool)]
    Phi = _col(df, "Phi")
    z, o = torch.zeros_like(Phi), torch.ones_like(Phi)
    d = (_solve(Phi, z, z, o, o, N_EVAL, TOL_EVAL)
         - _solve(Phi, z, z, o, o, N_TRAIN, TOL_TRAIN)).abs()
    return dict(max_abs_gap=float(d.max()), passes=bool(d.max() == 0.0))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="results/e5_sigma_grounding")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--arm", default="nrtl_predictions.csv")
    ap.add_argument("--out", default="results/solver_iteration_audit/outer_sle_counts.json")
    args = ap.parse_args()

    root = Path(args.root)
    per_seed, gaps = [], []
    for seed in args.seeds:
        r = audit_seed(root / f"seed_{seed}" / args.arm)
        gaps.append(r.pop("_gap"))
        r["seed"] = seed
        per_seed.append(r)

    pooled = np.concatenate(gaps)
    mt = np.array([r["mae_train_count"] for r in per_seed])
    me = np.array([r["mae_eval_count"] for r in per_seed])
    mc = np.array([r["mae_converged"] for r in per_seed])
    summary = dict(
        counts=dict(n_iter_train=N_TRAIN, n_iter_eval=N_EVAL,
                    solver_tol_train=TOL_TRAIN, solver_tol_eval=TOL_EVAL,
                    damping=DAMPING, converged_reference=N_CONVERGED),
        arm=args.arm, root=str(root), seeds=args.seeds,
        per_seed=per_seed,
        null_arm=null_arm(root / f"seed_{args.seeds[0]}" / args.arm),
        pooled_row_gap=dict(
            n=int(pooled.size), mean=float(pooled.mean()),
            p50=float(np.median(pooled)), p95=float(np.percentile(pooled, 95)),
            p99=float(np.percentile(pooled, 99)), max=float(pooled.max()),
            frac_gt_005=float(np.mean(pooled > 0.05)),
            frac_gt_020=float(np.mean(pooled > 0.20)),
        ),
        seed_mean_mae=dict(
            train_count=float(mt.mean()), eval_count=float(me.mean()),
            converged=float(mc.mean()),
            train_to_eval=float(me.mean() - mt.mean()),
            eval_to_converged=float(mc.mean() - me.mean()),
            train_to_converged=float(mc.mean() - mt.mean()),
        ),
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n")

    print(f"arm {args.arm}  seeds {args.seeds}")
    for r in per_seed:
        print(f"  seed {r['seed']}: identified {r['n_identified']}/{r['n_rows']}  "
              f"reproduction gate max {r['gate_reproduction_max']:.2e}  "
              f"MAE {r['mae_train_count']:.4f} (n={N_TRAIN}) -> "
              f"{r['mae_eval_count']:.4f} (n={N_EVAL}) -> {r['mae_converged']:.4f} (converged)")
    p = summary["pooled_row_gap"]
    print(f"  per-row |ln x2({N_EVAL}) - ln x2({N_TRAIN})| over {p['n']} rows: "
          f"mean {p['mean']:.4f}  p95 {p['p95']:.4f}  p99 {p['p99']:.4f}  max {p['max']:.4f}")
    print(f"  above 0.05: {p['frac_gt_005']*100:.1f}%    above 0.20: {p['frac_gt_020']*100:.1f}%")
    s = summary["seed_mean_mae"]
    print(f"  seed-mean MAE  train->eval {s['train_to_eval']:+.4f}   "
          f"eval->converged {s['eval_to_converged']:+.4f}")
    print(f"  null arm (ideal closure): max gap {summary['null_arm']['max_abs_gap']:.3e}  "
          f"{'PASS' if summary['null_arm']['passes'] else 'FAIL'}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
