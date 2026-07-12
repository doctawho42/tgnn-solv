#!/usr/bin/env python3
"""Analyze the Tier-3 closure-fix crossover (constructive complement to the paradox).

Two parts, both from artifacts the Modal ``closure_fix`` run leaves on the volume:

  (1) CROSSOVER STATISTIC from closure_fix_summary.json. Per-arm test ln x2 MAE,
      mean +/- sd over seeds, and the seed-paired gap
          gap_seed = gain_C - gain_I = MAE_I(seed) - MAE_C(seed)
      (base is shared, so it cancels). gap>0 => the same matched budget K buys more
      accuracy on the CLOSURE (Arm C) than on the intermediate (Arm I) => B_clos
      dominates at matched K -- the constructive proof of the paper's thesis in its
      own system. Arm O (unmatched output residual) is the Gate-B reference.

  (2) REALIZED CLOSURE DEFORMATION from an Arm-C checkpoint. Reconstruct the learned
      exchange-kernel residual  Delta = B diag(a) B^T  on the fixed 51-bin sigma-grid,
      report ||Delta||_F, and plot Delta(sigma_m, sigma_n) -- shows WHERE the fix
      concentrates (expect the H-bond / high-|sigma| region the single c_hb/sigma_hb
      cutoff cannot express), i.e. that a genuine closure correction was learned, not
      a diffuse black-box.

Usage:
  python scripts/analysis/analyze_closure_fix.py \
      --summary results/closure_fix/closure_fix_summary.json \
      --armC-ckpt results/closure_fix/ckpt/arm_C_closure_seed0.pt \
      --out-json results/closure_fix/crossover_analysis.json --fig-dir paper/figs
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np

ARM_KEYS = {"C_closure": "closure-fix (C)", "I_input": "input-fix (I)", "O_output": "output-residual (O)"}


def _mean_sd(xs):
    n = len(xs)
    if n == 0:
        return float("nan"), float("nan")
    mu = sum(xs) / n
    if n == 1:
        return mu, 0.0
    return mu, math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))


def crossover_stats(summary_path: Path) -> dict:
    d = json.loads(summary_path.read_text())
    base = d.get("base_mae")
    arms = d.get("arms", {})
    # group by (arm_base -> {seed -> mae})
    by_arm = defaultdict(dict)
    for k, v in arms.items():
        m = re.match(r"(.+)_seed(\d+)$", k)
        if not m:
            continue
        by_arm[m.group(1)][int(m.group(2))] = float(v) if isinstance(v, (int, float)) else float("nan")

    per_arm = {}
    for arm, seedmap in by_arm.items():
        maes = list(seedmap.values())
        mu, sd = _mean_sd(maes)
        gmu, gsd = _mean_sd([base - x for x in maes]) if base is not None else (float("nan"), float("nan"))
        per_arm[arm] = {"label": ARM_KEYS.get(arm, arm), "seeds": seedmap,
                        "mae_mean": mu, "mae_sd": sd, "gain_mean": gmu, "gain_sd": gsd}

    # seed-paired crossover gap: gap_seed = MAE_I - MAE_C  (>0 => closure-fix wins)
    out = {"base_mae": base, "per_arm": per_arm}
    if "C_closure" in by_arm and "I_input" in by_arm:
        shared = sorted(set(by_arm["C_closure"]) & set(by_arm["I_input"]))
        gaps = [by_arm["I_input"][s] - by_arm["C_closure"][s] for s in shared]
        gmu, gsd = _mean_sd(gaps)
        se = gsd / math.sqrt(len(gaps)) if len(gaps) > 1 else float("nan")
        out["crossover"] = {
            "seeds": shared,
            "gap_per_seed_MAE_I_minus_C": {s: g for s, g in zip(shared, gaps)},
            "gap_mean": gmu, "gap_sd": gsd, "gap_se": se,
            "ci95": [gmu - 1.96 * se, gmu + 1.96 * se] if se == se else None,
            "closure_fix_wins": gmu > 0,
            "verdict": ("closure-fix beats input-fix at matched K => B_clos dominates"
                        if gmu > 0 else "input-fix >= closure-fix (no closure-dominance at this budget)"),
        }
    return out


def deformation(ckpt_path: Path, fig_dir: Path) -> dict:
    import torch
    sd = torch.load(ckpt_path, map_location="cpu")
    state = sd.get("model_state_dict", sd.get("state_dict", sd))
    kB = ka = None
    for k, v in state.items():
        if k.endswith("cosmo_sac_layer.kernel_B"):
            kB = v.detach().cpu().numpy()
        elif k.endswith("cosmo_sac_layer.kernel_a"):
            ka = v.detach().cpu().numpy()
    if kB is None or ka is None:
        return {"error": "kernel_B/kernel_a not found in checkpoint (arm may not be Arm C, or R=0)"}
    delta = (kB * ka[None, :]) @ kB.T          # (51,51) symmetric residual, kcal/mol
    n_bins = delta.shape[0]
    sigma_grid = np.linspace(-0.025, 0.025, n_bins)
    fro = float(np.sqrt((delta ** 2).sum()))
    res = {"rank_R": int(kB.shape[1]), "frobenius_norm": fro,
           "max_abs": float(np.abs(delta).max()),
           "diag_mean": float(np.diag(delta).mean()),
           # concentration: fraction of |Delta| mass in the high-|sigma| (>0.01) band
           "high_sigma_mass_frac": float(
               np.abs(delta)[np.ix_(np.abs(sigma_grid) > 0.01, np.abs(sigma_grid) > 0.01)].sum()
               / (np.abs(delta).sum() + 1e-12))}

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5.2, 4.4))
        vmax = np.abs(delta).max() or 1.0
        im = ax.imshow(delta, origin="lower", cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                       extent=[sigma_grid[0], sigma_grid[-1], sigma_grid[0], sigma_grid[-1]])
        ax.set_xlabel(r"$\sigma_n$ (e/\AA$^2$)"); ax.set_ylabel(r"$\sigma_m$ (e/\AA$^2$)")
        ax.set_title(r"Learned closure correction $\Delta(\sigma_m,\sigma_n)$"
                     "\n(Arm C, rank %d, $\\|\\Delta\\|_F=%.1f$ kcal/mol)" % (res["rank_R"], fro))
        fig.colorbar(im, ax=ax, label="kcal/mol")
        fig.tight_layout()
        fig_dir.mkdir(parents=True, exist_ok=True)
        for ext in ("pdf", "png"):
            p = fig_dir / f"fig_closure_fix_deformation.{ext}"
            fig.savefig(p, dpi=150)
        res["figure"] = str(fig_dir / "fig_closure_fix_deformation.pdf")
        plt.close(fig)
    except Exception as e:  # noqa: BLE001
        res["figure_error"] = str(e)
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--armC-ckpt", type=Path, default=None, help="Arm-C checkpoint for the deformation plot")
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--fig-dir", type=Path, default=Path("paper/figs"))
    args = ap.parse_args()

    out = crossover_stats(args.summary)
    if args.armC_ckpt and args.armC_ckpt.exists():
        out["deformation"] = deformation(args.armC_ckpt, args.fig_dir)

    print(f"base MAE = {out['base_mae']}")
    print(f"{'arm':<22}{'MAE (mean+/-sd)':>22}{'gain vs base':>18}")
    for arm, s in out["per_arm"].items():
        print(f"  {s['label']:<20}{s['mae_mean']:>10.4f} +/-{s['mae_sd']:<7.4f}"
              f"{s['gain_mean']:>+10.4f}+/-{s['gain_sd']:.4f}")
    if "crossover" in out:
        c = out["crossover"]
        print(f"\nCROSSOVER  gap = MAE_I - MAE_C = {c['gap_mean']:+.4f} +/- {c['gap_sd']:.4f}  "
              f"(seed-paired, n={len(c['seeds'])})")
        if c.get("ci95"):
            print(f"  95% CI [{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}]  -> {c['verdict']}")
    if "deformation" in out and "frobenius_norm" in out["deformation"]:
        de = out["deformation"]
        print(f"\nDEFORMATION  ||Delta||_F = {de['frobenius_norm']:.2f} kcal/mol, "
              f"high-|sigma| mass frac = {de.get('high_sigma_mass_frac', float('nan')):.2f}")

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(out, indent=2))
        print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
