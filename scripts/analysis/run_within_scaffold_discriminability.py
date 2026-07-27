#!/usr/bin/env python
"""Within-scaffold discriminability of the DirectGNN pair representation.

Study 4 reports eta^2(scaffold)/eta^2(solute) ~ 1 on the test split, which is close to
mechanically forced: only 34 of the 147 test solutes share a Bemis-Murcko scaffold with
another solute (11 multi-member scaffolds, 8.8% of rows), so the two partitions coincide
on 91% of the data whatever the representation does.  That ratio therefore bounds what the
representation buys beyond scaffold; it does not measure whether molecules sharing a
scaffold are resolved.

This script measures it directly, restricted to the 34 shared-scaffold solutes.  For every
pair of distinct solutes measured in a COMMON solvent (so solvent identity cannot carry the
comparison) it takes the Euclidean distance between their mean pair representations, and
reports

    ratio = mean over same-scaffold pairs / mean over different-scaffold pairs

with a 90% cluster bootstrap over the multi-member scaffolds.  ratio -> 0 would mean
same-scaffold molecules are unresolved; ratio -> 1 would mean scaffold membership does not
compress the representation at all.  The median-of-distances ratio is reported alongside as
a heavy-tail check, and the mean percentile of a same-scaffold distance within its own
solvent's between-scaffold distance distribution as a location check.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python \
        scripts/analysis/run_within_scaffold_discriminability.py \
        --checkpoints checkpoints/e5_current_split/directgnn_seed4{2,3,4}.pt \
        --out-json results/blackbox/within_scaffold_discriminability.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))
sys.path.insert(0, str(_REPO / "scripts" / "experiments"))

from blackbox_study1a import extract_hbb  # noqa: E402


def murcko(smiles) -> np.ndarray:
    from rdkit import Chem
    from rdkit.Chem.Scaffolds import MurckoScaffold
    out = []
    for s in smiles:
        m = Chem.MolFromSmiles(s)
        out.append(MurckoScaffold.MurckoScaffoldSmiles(mol=m) if m else "?")
    return np.asarray(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoints", nargs="+", required=True)
    ap.add_argument("--data-dir", default="notebooks/data/processed")
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    dd = _REPO / args.data_dir
    rows = pd.read_csv(dd / "test.csv", low_memory=False)
    if "has_solubility" in rows.columns:
        rows = rows[rows["has_solubility"].astype(bool)].reset_index(drop=True)
    rows = rows.assign(_scaf=murcko(list(rows.solute_smiles)))
    sc_of = dict(zip(rows.solute_smiles, rows._scaf))

    n_by_scaf = rows.groupby("_scaf").solute_smiles.nunique()
    multi = set(n_by_scaf[n_by_scaf > 1].index)
    shared = sorted({s for s in rows.solute_smiles.unique() if sc_of[s] in multi})
    shared_rows = int(rows.solute_smiles.isin(shared).sum())

    design = {
        "n_rows": int(len(rows)),
        "n_solutes": int(rows.solute_smiles.nunique()),
        "n_scaffolds": int(rows._scaf.nunique()),
        "n_multi_member_scaffolds": len(multi),
        "n_solutes_sharing_a_scaffold": len(shared),
        "rows_from_shared_scaffold_solutes": shared_rows,
        "share_of_rows": shared_rows / len(rows),
    }
    print(json.dumps(design, indent=1))

    out = {"design": design, "seeds": {}}
    for ck in args.checkpoints:
        ck = Path(ck)
        if not ck.is_absolute():
            ck = _REPO / ck
        print(f"\n=== {ck.name} ===")
        H = extract_hbb(ck, rows, torch.device(args.device)).astype(np.float64)
        H = H - H.mean(0)

        cells = collections.defaultdict(list)
        for i, k in enumerate(zip(rows.solute_smiles, rows.solvent_smiles)):
            cells[k].append(i)
        mu = {k: H[v].mean(0) for k, v in cells.items()}

        by_solvent = collections.defaultdict(list)
        for (sol, slv) in mu:
            by_solvent[slv].append(sol)

        within, between = [], []
        within_by_scaf = collections.defaultdict(list)
        percentiles = []
        for slv, sols in by_solvent.items():
            if len(sols) < 2:
                continue
            loc_w, loc_b = [], []
            for a in range(len(sols)):
                for b in range(a + 1, len(sols)):
                    A, B = sols[a], sols[b]
                    d = float(np.linalg.norm(mu[(A, slv)] - mu[(B, slv)]))
                    if sc_of[A] == sc_of[B]:
                        loc_w.append(d)
                        within_by_scaf[sc_of[A]].append(d)
                    else:
                        loc_b.append(d)
            within += loc_w
            between += loc_b
            if loc_b:
                percentiles += [float((np.asarray(loc_b) < d).mean()) for d in loc_w]

        w = np.asarray(within)
        b = np.asarray(between)
        scafs = sorted(within_by_scaf)
        rng = np.random.default_rng(0)
        boot = np.empty(args.n_boot)
        for i in range(args.n_boot):
            pick = rng.choice(len(scafs), len(scafs), replace=True)
            boot[i] = np.concatenate([within_by_scaf[scafs[j]] for j in pick]).mean() / b.mean()

        rec = {
            "n_within_pairs": int(w.size),
            "n_between_pairs": int(b.size),
            "n_scaffolds_contributing": len(scafs),
            "mean_within": float(w.mean()),
            "mean_between": float(b.mean()),
            "ratio_of_means": float(w.mean() / b.mean()),
            "ratio_of_medians": float(np.median(w) / np.median(b)),
            "mean_percentile_within_same_solvent_between_scaffold": float(np.mean(percentiles)),
            "ratio_ci90_scaffold_cluster_bootstrap": [float(np.quantile(boot, 0.05)),
                                                      float(np.quantile(boot, 0.95))],
        }
        out["seeds"][ck.name] = rec
        print(json.dumps(rec, indent=1))

    if args.out_json:
        p = args.out_json if args.out_json.is_absolute() else _REPO / args.out_json
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=1))
        print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
