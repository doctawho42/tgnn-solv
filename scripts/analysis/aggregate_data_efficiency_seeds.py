#!/usr/bin/env python
"""Aggregate per-seed data-efficiency summaries into mean +/- std per fraction.

Consumes the ``summary.json`` files emitted by ``run_data_efficiency_summary.py``
(one per seed, produced by the Modal ``data_efficiency`` function) and reports the
seed mean and standard deviation of the physics-minus-direct MAE gap at each training
fraction -- the error bars blind reviewer Major 3 asked for on the single-seed curve.

Usage:
  python scripts/analysis/aggregate_data_efficiency_seeds.py \
      results/data_efficiency_multiseed/data_efficiency_seed*/summary.json \
      --out-json results/data_efficiency_multiseed/aggregate.json
"""
from __future__ import annotations

import argparse
import glob
import json
import math
from collections import defaultdict
from pathlib import Path


def _mean_std(xs):
    n = len(xs)
    if n == 0:
        return float("nan"), float("nan")
    mu = sum(xs) / n
    if n == 1:
        return mu, 0.0
    var = sum((x - mu) ** 2 for x in xs) / (n - 1)  # sample std
    return mu, math.sqrt(var)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("summaries", nargs="+", help="per-seed summary.json paths (globs ok)")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    paths = []
    for pat in args.summaries:
        paths.extend(sorted(glob.glob(pat)) or [pat])
    paths = [p for p in paths if Path(p).exists()]
    if not paths:
        raise SystemExit("no summary.json files found")

    # frac -> metric -> list over seeds
    gap_mae = defaultdict(list)
    gap_spear = defaultdict(list)
    phys_mae = defaultdict(list)
    dir_mae = defaultdict(list)
    phys_r2 = defaultdict(list)
    dir_r2 = defaultdict(list)
    phys_top1 = defaultdict(list)
    dir_top1 = defaultdict(list)
    seeds = []

    for p in paths:
        d = json.loads(Path(p).read_text())
        # seed is encoded in the parent dir name data_efficiency_seed<N>
        parent = Path(p).parent.name
        seeds.append(parent)
        for row in d.get("physics_minus_direct", []):
            f = float(row["fraction"])
            gap_mae[f].append(row["mae_physics_minus_direct"])
            gap_spear[f].append(row.get("spearman_physics_minus_direct", float("nan")))
        curve = d.get("curve", {})
        for f_str, m in curve.get("physics", {}).items():
            f = float(f_str)
            phys_mae[f].append(m["mae"]); phys_r2[f].append(m["r2"])
            phys_top1[f].append(m.get("best_solvent_top1", float("nan")))
        for f_str, m in curve.get("direct", {}).items():
            f = float(f_str)
            dir_mae[f].append(m["mae"]); dir_r2[f].append(m["r2"])
            dir_top1[f].append(m.get("best_solvent_top1", float("nan")))

    fracs = sorted(gap_mae)
    rows = []
    for f in fracs:
        g_mu, g_sd = _mean_std(gap_mae[f])
        pm_mu, pm_sd = _mean_std(phys_mae[f])
        dm_mu, dm_sd = _mean_std(dir_mae[f])
        pr_mu, _ = _mean_std(phys_r2[f])
        dr_mu, _ = _mean_std(dir_r2[f])
        rows.append({
            "fraction": f,
            "n_seeds": len(gap_mae[f]),
            "gap_mae_mean": g_mu, "gap_mae_std": g_sd,
            "physics_mae_mean": pm_mu, "physics_mae_std": pm_sd,
            "direct_mae_mean": dm_mu, "direct_mae_std": dm_sd,
            "physics_r2_mean": pr_mu, "direct_r2_mean": dr_mu,
            "gap_excludes_zero": (g_mu - g_sd > 0) or (g_mu + g_sd < 0),
        })

    out = {"seeds": seeds, "n_files": len(paths), "per_fraction": rows}
    print(f"{'frac':>6} {'n':>2} {'gap_mae (mean+/-std)':>24} {'phys_mae':>16} {'dir_mae':>16}")
    for r in rows:
        print(f"{r['fraction']:>6} {r['n_seeds']:>2} "
              f"{r['gap_mae_mean']:>+10.3f} +/- {r['gap_mae_std']:<8.3f}  "
              f"{r['physics_mae_mean']:>7.3f}+/-{r['physics_mae_std']:<5.3f} "
              f"{r['direct_mae_mean']:>7.3f}+/-{r['direct_mae_std']:<5.3f}")

    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(out, indent=2))
        print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
