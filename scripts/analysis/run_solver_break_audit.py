#!/usr/bin/env python
"""Does the SLE outer loop's early exit ever fire -- and what does its sync cost?

WHY THIS EXISTS. ``_iterate_cosmo_sac_fixed_point`` ends each outer iteration with

    if residual.max().item() < tol: break

On CUDA, ``.item()`` is a BLOCKING host synchronisation: the CPU stops until the whole
queued GPU work drains. That happens ``n_iter`` times per forward (5 at train, 20 at eval),
and each flush destroys the one thing that hides Python dispatch cost -- the CPU running
ahead to queue the next iteration's kernels while the GPU chews the current ones. A
COSMO-SAC forward issues on the order of a thousand tiny kernels, so the pipeline is exactly
what it cannot afford to lose. Measured on a Kaggle T4 (2026-10-02): 331 ms/step at batch
64 with the GPU 25% busy (p90 34%), while the data loader was delivering 648-714 rows/s
against a 193 rows/s compute ceiling -- not data-starved, latency-bound inside the step.

Removing the break is NOT free in principle: it changes the operator on any row where the
exit used to fire, and this project has already been bitten once by treating a solver
iteration count as a free hyperparameter when it is a property of the trained weights (see
the segment-count warning in CLAUDE.md). So the question is empirical, and it is asked on
REAL learned profiles rather than synthetic ones, because synthetic stimuli have already
shown 0.0000 in this solver where real ones show 0.0734.

The audit reports, per (tol, Phi) cell, the first outer iteration at which the batch-max
residual falls below tol -- i.e. the iteration the break would fire on -- or ``never``.

IT COVERS BOTH PATHS ON PURPOSE. The first version audited only COSMO-SAC, found "never
fires", and the flag was then turned off in all three iterators -- which
``test_physics_verification.py::test_damping_convergence`` immediately caught: on the NRTL
path with a near-ideal pair the exit fires at iteration 16 of 30, and disabling it moves x2
by 2.3e-09. Negligible as physics, but it is the difference between an audited no-op and an
undeclared operator change, so the NRTL arm is measured here rather than inferred from the
COSMO-SAC one. The two closures differ exactly where it matters: a near-ideal NRTL pair
reaches its fixed point in a handful of iterations, while a COSMO-SAC residual carries a
whole segment solve per outer step and does not.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer, NRTLLayer
from tgnn_solv.solver import _SLE_EXP_ARG_MAX, _SLE_EXP_ARG_MIN, _iterate_fixed_point

PROFILES = Path("results/closure_conditioning/learned_profiles.npz")


def trace_residual(
    Phi: torch.Tensor, layer: CosmoSacLayer, p2, p1, A2, A1, V2, V1, T,
    *, n_iter: int, damping: float, min_damping: float, adaptive: bool,
) -> list[float]:
    """Batch-max outer residual after each iteration -- the quantity the break tests.

    Mirrors ``solver._iterate_cosmo_sac_fixed_point`` exactly, minus the break itself.
    """
    x2 = torch.exp((-Phi).clamp(_SLE_EXP_ARG_MIN, _SLE_EXP_ARG_MAX)).clamp(1e-10, 1 - 1e-10)
    damp = torch.full_like(x2, damping)
    prev = torch.full_like(x2, float("inf"))
    trace = []
    for _ in range(n_iter):
        lng2 = layer.ln_gamma_2(1.0 - x2, x2, p2, p1, A2, A1, V2, V1, T)
        cand = torch.exp((-Phi - lng2).clamp(_SLE_EXP_ARG_MIN, _SLE_EXP_ARG_MAX)).clamp(
            1e-10, 1 - 1e-10
        )
        residual = (torch.log(cand) - torch.log(x2)).abs()
        if adaptive:
            damp = torch.where(residual > prev, (damp * 0.5).clamp(min=min_damping),
                               (damp * 1.05).clamp(max=1.0))
        x2 = damp * cand + (1.0 - damp) * x2
        prev = residual
        trace.append(float(residual.max()))
    return trace


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profiles", type=Path, default=PROFILES)
    ap.add_argument("--batch", type=int, default=64, help="rows per batch (break tests the max)")
    ap.add_argument("--n-batches", type=int, default=24)
    ap.add_argument("--out", type=Path, default=Path("results/solver_break_audit"))
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    cfg = TGNNSolvConfig(activity_model="cosmo_sac")
    d = np.load(a.profiles)
    p_sol, p_slv = d["p_solute"], d["p_solvent"]
    rng = np.random.default_rng(a.seed)
    layer = CosmoSacLayer(cfg)

    rows = []
    for mode, n_iter, tol in (("train", cfg.n_iter_train, cfg.solver_tol_train),
                              ("eval", cfg.n_iter_eval, cfg.solver_tol_eval)):
        layer.train(mode == "train")
        for phi in (0.0, 2.0, 4.0, 8.0):
            fired, first, last = 0, [], float("nan")
            for _ in range(a.n_batches):
                idx = rng.choice(len(p_sol), a.batch, replace=False)
                p2 = torch.from_numpy(p_sol[idx]).float()
                p1 = torch.from_numpy(p_slv[idx]).float()
                A2, A1 = p2.sum(-1), p1.sum(-1)
                # SG volumes are not deposited; r0*q-consistent spheres keep the
                # combinatorial term in its physical range without inventing data.
                V2, V1 = A2 * 1.2, A1 * 1.2
                T = torch.from_numpy(rng.uniform(273.0, 323.0, a.batch)).float()
                Phi = torch.full((a.batch,), phi)
                with torch.no_grad():
                    tr = trace_residual(Phi, layer, p2, p1, A2, A1, V2, V1, T,
                                        n_iter=n_iter, damping=cfg.damping,
                                        min_damping=cfg.solver_min_damping,
                                        adaptive=cfg.solver_adaptive_damping)
                hit = next((i + 1 for i, r in enumerate(tr) if r < tol), None)
                if hit is not None:
                    fired += 1
                    first.append(hit)
                last = tr[-1]
            rows.append({
                "closure": "cosmo_sac", "mode": mode, "n_iter": n_iter, "tol": tol,
                "Phi": phi, "batches": a.n_batches, "break_fired": fired,
                "first_iter_median": (float(np.median(first)) if first else None),
                "residual_after_last_iter": last,
                "margin_to_tol": last / tol,
            })
            print(f"cosmo_sac {mode:<5} Phi={phi:<4} n_iter={n_iter:<3} tol={tol:g}: "
                  f"break fired in {fired}/{a.n_batches} batches; "
                  f"final residual {last:.3e} = {last / tol:.2g}x tol")

    # --- NRTL arm: same question, the other closure -----------------------------------
    # tau is swept from near-ideal to strongly non-ideal, because that is the axis the exit
    # is sensitive to: an ideal closure has no x2 dependence and converges at once.
    nrtl = NRTLLayer()
    for mode, n_iter, tol in (("train", cfg.n_iter_train, cfg.solver_tol_train),
                              ("eval", cfg.n_iter_eval, cfg.solver_tol_eval)):
        for tau, label in ((0.5, "near-ideal"), (3.0, "moderate"), (9.0, "stiff")):
            Phi = torch.from_numpy(rng.uniform(0.5, 8.0, a.batch)).float()
            t12 = torch.full((a.batch,), tau)
            t21 = torch.full((a.batch,), tau / 6.0)
            alpha = torch.full((a.batch,), 0.3)
            trace = []
            with torch.no_grad():
                for n in range(1, n_iter + 1):
                    x2, _ = _iterate_fixed_point(
                        Phi, t12, t21, torch.exp(-alpha * t12), torch.exp(-alpha * t21),
                        n_iter=n, damping=cfg.damping, min_damping=cfg.solver_min_damping,
                        tol=0.0, adaptive_damping=cfg.solver_adaptive_damping,
                        nrtl_layer=nrtl)
                    trace.append(x2)
            # residual as the loop measures it: |log x2(n) - log x2(n-1)|, batch max
            res_tr = [float((torch.log(trace[i]) - torch.log(trace[i - 1])).abs().max())
                      for i in range(1, len(trace))]
            hit = next((i + 2 for i, r in enumerate(res_tr) if r < tol), None)
            rows.append({
                "closure": "nrtl", "mode": mode, "n_iter": n_iter, "tol": tol,
                "tau_12": tau, "regime": label, "break_fired": int(hit is not None),
                "first_iter_median": (float(hit) if hit else None),
                "residual_after_last_iter": (res_tr[-1] if res_tr else None),
                "margin_to_tol": (res_tr[-1] / tol if res_tr else None),
            })
            print(f"nrtl      {mode:<5} tau={tau:<4} ({label:<10}) n_iter={n_iter:<3} "
                  f"tol={tol:g}: break at iter {hit if hit else 'never':<5}; "
                  f"final residual {res_tr[-1]:.3e} = {res_tr[-1] / tol:.2g}x tol")

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(
        {"profiles": str(a.profiles), "n_profiles": int(len(p_sol)),
         "batch": a.batch, "seed": a.seed, "cells": rows}, indent=2))
    for cl in ("cosmo_sac", "nrtl"):
        sub = [r for r in rows if r["closure"] == cl]
        print(f"\n{cl}: break fired in {sum(r['break_fired'] for r in sub)} of "
              f"{sum(r.get('batches', 1) for r in sub)} cells")
    print(f"-> {a.out / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
