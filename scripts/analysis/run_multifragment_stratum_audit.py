#!/usr/bin/env python3
r"""The part of the scored set that the ideal-solubility term is not written for.

WHY THIS EXISTS
---------------
``Phi = (dH_fus/R)(1/T - 1/T_m)`` is the ideal-solubility term of a PURE, one-component
crystalline solute: the solid in equilibrium with the saturated solution is that solute's
own crystal.  A hydrochloride salt, a sodium carboxylate, a hexafluorophosphate ionic
liquid and a hydrate are none of those things -- the equilibrium solid is a different
phase, dissociation or hydration is part of the process, and a single ``T_m``/``dH_fus``
pair does not stand for it.  A multi-component solute is visible in the SMILES: it
contains a ``.``.

This script counts that stratum inside the scored row set and reports the arms' error on
it, so the paper can disclose it with a size rather than filter it away.  IT DOES NOT
FILTER ANYTHING.  The scored set is the intersection-locked n=5608 and is quoted
throughout both documents; changing it here would orphan every number keyed to it.

USAGE
-----
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python \
        scripts/analysis/run_multifragment_stratum_audit.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ARMS = {
    "directgnn": "directgnn_predictions.csv",
    "nrtl": "nrtl_predictions.csv",
    "grounded_a": "grounded_a_predictions.csv",
    "ungrounded": "ungrounded_predictions.csv",
}


def _cluster_ci(d: pd.DataFrame, multi_mask, n_boot: int, seed: int) -> dict:
    """95% interval on (MAE on the stratum - MAE off it), resampling SOLUTES.

    The effective sample size is the number of solutes -- 26 on one side, 121 on the
    other -- not the number of rows, so the bootstrap resamples solutes within each side
    with replacement and re-pools the rows they carry.
    """
    rng = np.random.default_rng(seed)
    err = d["abs_error"].to_numpy()
    keys = d["solute_smiles"].to_numpy()
    groups = {"multi": {}, "rest": {}}
    for k, side in zip(keys, np.where(multi_mask.to_numpy(), "multi", "rest")):
        groups[side].setdefault(k, [])
    for e, k, side in zip(err, keys, np.where(multi_mask.to_numpy(), "multi", "rest")):
        groups[side][k].append(e)
    a = [np.asarray(v) for v in groups["multi"].values()]
    b = [np.asarray(v) for v in groups["rest"].values()]
    draws = np.empty(n_boot)
    for i in range(n_boot):
        ia = rng.integers(0, len(a), len(a))
        ib = rng.integers(0, len(b), len(b))
        draws[i] = (np.concatenate([a[j] for j in ia]).mean()
                    - np.concatenate([b[j] for j in ib]).mean())
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return dict(n_clusters_multi=len(a), n_clusters_rest=len(b),
                point=float(np.concatenate(a).mean() - np.concatenate(b).mean()),
                ci95=[float(lo), float(hi)],
                crosses_zero=bool(lo < 0.0 < hi))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-boot", type=int, default=4000)
    ap.add_argument("--root", default="results/e5_sigma_grounding")
    ap.add_argument("--split", default="notebooks/data/processed/test.csv")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--out", default="results/multifragment_stratum/summary.json")
    args = ap.parse_args()

    test = pd.read_csv(args.split)
    lab = test[test["has_solubility"].astype(bool)].copy()
    lab["multi"] = lab["solute_smiles"].str.contains(".", regex=False)
    by_solute = lab.groupby("solute_smiles").agg(
        rows=("ln_x2", "size"), multi=("multi", "first"), has_T_m=("has_T_m", "max"))
    multi = by_solute[by_solute["multi"]]

    comp = dict(
        n_labelled_rows=int(len(lab)),
        n_labelled_solutes=int(lab["solute_smiles"].nunique()),
        n_multifragment_rows=int(lab["multi"].sum()),
        frac_multifragment_rows=float(lab["multi"].mean()),
        n_multifragment_solutes=int(len(multi)),
        n_multifragment_solutes_with_measured_T_m=int((multi["has_T_m"] > 0).sum()),
        n_singlefragment_solutes_with_measured_T_m=int(
            (by_solute[~by_solute["multi"]]["has_T_m"] > 0).sum()),
        solutes=[{"smiles": s, "rows": int(multi.loc[s, "rows"]),
                  "has_T_m": bool(multi.loc[s, "has_T_m"] > 0)} for s in multi.index],
    )

    rows, boot = [], {}
    for seed in args.seeds:
        for arm, fname in ARMS.items():
            d = pd.read_csv(Path(args.root) / f"seed_{seed}" / fname)
            d = d[d["has_solubility"].astype(bool)]
            m = d["solute_smiles"].str.contains(".", regex=False)
            rows.append(dict(seed=seed, arm=arm, n_multi=int(m.sum()),
                             mae_multi=float(d.loc[m, "abs_error"].mean()),
                             mae_rest=float(d.loc[~m, "abs_error"].mean()),
                             mae_all=float(d["abs_error"].mean())))
            boot[(seed, arm)] = _cluster_ci(d, m, args.n_boot, seed)
    r = pd.DataFrame(rows)
    per_arm = {}
    for arm, sub in r.groupby("arm"):
        per_arm[arm] = dict(
            mae_all=float(sub["mae_all"].mean()),
            mae_multi=float(sub["mae_multi"].mean()),
            mae_rest=float(sub["mae_rest"].mean()),
            multi_minus_rest_per_seed=[float(v) for v in
                                       (sub["mae_multi"] - sub["mae_rest"]).to_numpy()],
            multi_minus_rest_mean=float((sub["mae_multi"] - sub["mae_rest"]).mean()),
            all_minus_rest=float(sub["mae_all"].mean() - sub["mae_rest"].mean()),
            solute_clustered_ci_per_seed=[boot[(s, arm)] for s in args.seeds],
            n_seeds_ci_excludes_zero=int(sum(
                not boot[(s, arm)]["crosses_zero"] for s in args.seeds)),
        )
    per_arm["_gaps_vs_directgnn"] = {
        arm: dict(on_all_rows=per_arm[arm]["mae_all"] - per_arm["directgnn"]["mae_all"],
                  on_single_fragment_only=(per_arm[arm]["mae_rest"]
                                           - per_arm["directgnn"]["mae_rest"]))
        for arm in ("nrtl", "grounded_a", "ungrounded")
    }

    summary = dict(root=args.root, seeds=args.seeds, composition=comp,
                   per_seed=rows, per_arm=per_arm)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n")

    print(f"labelled test rows {comp['n_labelled_rows']} over "
          f"{comp['n_labelled_solutes']} solutes")
    print(f"multi-fragment: {comp['n_multifragment_rows']} rows "
          f"({comp['frac_multifragment_rows']*100:.2f}%) over "
          f"{comp['n_multifragment_solutes']} solutes; "
          f"{comp['n_multifragment_solutes_with_measured_T_m']} of them carry a measured T_m "
          f"(single-fragment: {comp['n_singlefragment_solutes_with_measured_T_m']} of "
          f"{comp['n_labelled_solutes'] - comp['n_multifragment_solutes']})")
    for arm in ARMS:
        a = per_arm[arm]
        print(f"  {arm:<11} all {a['mae_all']:.4f}  multi {a['mae_multi']:.4f}  "
              f"rest {a['mae_rest']:.4f}   multi-rest per seed "
              + " ".join(f"{v:+.3f}" for v in a["multi_minus_rest_per_seed"])
              + f"   removing the stratum moves the mean {a['all_minus_rest']:+.4f}")
        for s, c in zip(args.seeds, a["solute_clustered_ci_per_seed"]):
            print(f"      seed {s} solute-clustered ({c['n_clusters_multi']} vs "
                  f"{c['n_clusters_rest']} clusters): {c['point']:+.3f} "
                  f"[{c['ci95'][0]:+.3f},{c['ci95'][1]:+.3f}]"
                  + ("  crosses zero" if c["crosses_zero"] else "  excludes zero"))
    g = per_arm["_gaps_vs_directgnn"]
    for arm in ("nrtl", "grounded_a"):
        print(f"  {arm} minus DirectGNN: {g[arm]['on_all_rows']:+.4f} on all rows, "
              f"{g[arm]['on_single_fragment_only']:+.4f} on single-fragment rows only")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
