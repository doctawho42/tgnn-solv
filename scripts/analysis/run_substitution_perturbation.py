#!/usr/bin/env python3
"""How far the sigma-oracle substitution moves the crystal parameters and Phi.

Discharges the Section S1 coupling sentence, which no command computed before this script:

    "Over the three seeds, on the rows where the substitution applied, it moves T_m by at most
     0.025 K against a median of 450 K, dH_fus by at most 4.6 J/mol against a median of 3.5e4,
     and Phi -- the quantity that actually enters the SLE -- by at most 7e-4 against a median
     magnitude of 4.5.  On the rows where the substitution did not apply the same quantities still
     move, by 1.2e-4 K, 0.045 J/mol and 6e-6, which is the residue of forwarding one checkpoint
     twice on a GPU and sets the floor these figures should be read against."

Everything it needs is already in the per-row export: `T_m_corrected`, `dH_fus_corrected` and `Phi`
(the corrected crystal parameters the solver receives, and the ideal term it forms), plus
`sigma_oracle_applied` on the oracle side.  The maxima are elementwise |oracle - grounded| over the
aligned rows of the two files; the medians are a scale reference read off the grounded arm.

TWO THINGS TO KNOW BEFORE QUOTING A NUMBER FROM THIS SCRIPT.

1. The printed figures are over EVERY exported row (8103 per seed on the published tree), not the
   5608 labelled ones.  Restricted to labelled rows the T_m maximum falls to 0.008 K, so
   `--rows labelled` does not reproduce the sentence.  Default is `all`.
2. THE MEDIANS ARE POOLED OVER THE SEEDS, and were not always: the sentence opens "over the three
   seeds", but until 2026-08-10 it printed 3.7e4 and 4.7, which are seed 42's medians alone
   (pooled: 3.479e4 and 4.534; only T_m survived, because 449.65 and 449.04 both print 450 at two
   significant figures).  Those two digits were repaired against this script, which is what it is
   for.  `--expect-published` now checks the medians on the POOLED basis and refuses the first-seed
   one; the per-seed medians, the mean of them and the first seed's are all still printed and
   deposited, so a future basis change is visible rather than silent.
3. The medians are reported on the rows the sentence names -- the ones the substitution applied to
   -- and also over every row.  On the published tree the two agree to well under the printed
   precision (449.12 vs 449.04 K, an identical 3.479e4, 4.537 vs 4.534), because 8066 of the 8103
   rows are applied rows; `median_reference` (all rows) and `median_reference_applied` are both in
   the JSON so that the agreement is a fact on the record and not an assumption.

The results root is a flag; default is the published tree.  Point `--root` at
results/e5_sigma_grounding_leakfree to discharge the leak-free re-run with the same command.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "results" / "e5_sigma_grounding"

# label -> (column, unit, how the median is taken)
QUANTITIES = {
    "T_m": ("T_m_corrected", "K", "median"),
    "dH_fus": ("dH_fus_corrected", "J/mol", "median"),
    "Phi": ("Phi", "-", "median_magnitude"),
}
ALT_CRYSTAL = {"T_m": "T_m_solver", "dH_fus": "dH_fus_solver"}

# What Section S1 prints today, off the published tree at seeds 42/43/44, over all exported rows.
# `median` is the POOLED median over the seeds; see note 2 in the module docstring for why the
# first-seed basis is not accepted here even though it is still computed and deposited.
PUBLISHED = {
    "max_applied": {"T_m": 0.025, "dH_fus": 4.6, "Phi": 7e-4},
    "max_unapplied": {"T_m": 1.2e-4, "dH_fus": 0.045, "Phi": 6e-6},
    "median": {"T_m": 450.0, "dH_fus": 3.5e4, "Phi": 4.5},
    "median_sigfigs": {"T_m": 2, "dH_fus": 2, "Phi": 2},
}


def discover_seeds(root: Path, grounded: str, oracle: str) -> list[int]:
    seeds = []
    for d in sorted(root.glob("seed_*")):
        m = re.fullmatch(r"seed_(\d+)", d.name)
        if m and (d / grounded).exists() and (d / oracle).exists():
            seeds.append(int(m.group(1)))
    return sorted(seeds)


def signif(x: float, n: int) -> float:
    if x == 0 or not np.isfinite(x):
        return float(x)
    return float(round(x, -int(np.floor(np.log10(abs(x)))) + (n - 1)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                    help=f"results root holding seed_*/ (default: {DEFAULT_ROOT.relative_to(REPO)})")
    ap.add_argument("--seeds", type=int, nargs="+", default=None,
                    help="seeds to use; default is every seed_* under --root carrying both CSVs")
    ap.add_argument("--grounded-name", default="grounded_a_predictions.csv")
    ap.add_argument("--oracle-name", default="oracle_predictions.csv")
    ap.add_argument("--rows", choices=("all", "labelled"), default="all",
                    help="row set; the printed sentence is over 'all' (default)")
    ap.add_argument("--out", type=Path, default=None, help="write the full result as JSON here")
    ap.add_argument("--expect-published", action="store_true",
                    help="assert the values Section S1 prints today; non-zero exit on mismatch")
    args = ap.parse_args()

    root = args.root if args.root.is_absolute() else (REPO / args.root)
    if not root.is_dir():
        ap.error(f"--root does not exist: {root}")
    seeds = args.seeds if args.seeds else discover_seeds(root, args.grounded_name, args.oracle_name)
    if not seeds:
        ap.error(f"no seed_* directory under {root} carries both "
                 f"{args.grounded_name} and {args.oracle_name}")

    print(f"root  : {root}")
    print(f"seeds : {' '.join(str(s) for s in seeds)}")
    print(f"rows  : {args.rows}")

    per_seed = []
    pooled_vals: dict[str, list[np.ndarray]] = {q: [] for q in QUANTITIES}
    pooled_applied: dict[str, list[np.ndarray]] = {q: [] for q in QUANTITIES}
    for seed in seeds:
        d = root / f"seed_{seed}"
        g = pd.read_csv(d / args.grounded_name)
        o = pd.read_csv(d / args.oracle_name)
        need = {c for c, _, _ in QUANTITIES.values()} | {"sigma_oracle_applied", "has_solubility"}
        missing = sorted((need - set(o.columns)) | ({c for c, _, _ in QUANTITIES.values()} - set(g.columns)))
        if missing:
            raise SystemExit(
                f"seed {seed}: the export does not carry {missing}. These are physics intermediates "
                f"written by scripts/analysis/export_checkpoint_predictions.py from the model's "
                f"forward dict; re-export both arms with that script (the oracle arm with "
                f"--sigma-oracle, so sigma_oracle_applied is written) rather than reconstructing "
                f"them -- nothing else in the deposit records the crystal parameters per row.")
        if args.rows == "labelled":
            g = g[g["has_solubility"].astype(bool)]
            o = o[o["has_solubility"].astype(bool)]
        g = g.reset_index(drop=True)
        o = o.reset_index(drop=True)
        if len(g) != len(o):
            raise SystemExit(f"seed {seed}: {len(g)} grounded rows vs {len(o)} oracle rows")
        for col in ("solute_smiles", "solvent_smiles"):
            if not (g[col].values == o[col].values).all():
                raise SystemExit(f"seed {seed}: {col} row order differs between the two arms")

        applied = o["sigma_oracle_applied"].astype(bool).to_numpy()
        rec = {"seed": seed, "n_rows": int(len(g)), "n_applied": int(applied.sum()),
               "n_unapplied": int((~applied).sum()), "quantities": {}}
        for q, (col, unit, how) in QUANTITIES.items():
            gv = g[col].to_numpy(dtype=float)
            delta = np.abs(o[col].to_numpy(dtype=float) - gv)
            med_src = np.abs(gv) if how == "median_magnitude" else gv
            pooled_vals[q].append(med_src)
            pooled_applied[q].append(med_src[applied])
            entry = {
                "column": col,
                "unit": unit,
                "max_abs_delta_applied": float(np.nanmax(delta[applied])) if applied.any() else None,
                "max_abs_delta_unapplied": float(np.nanmax(delta[~applied])) if (~applied).any() else None,
                "median_reference": float(np.nanmedian(med_src)),
                # the sentence's own row set; on the published tree it agrees with the line above
                # to well under the printed precision, and that is checked rather than assumed
                "median_reference_applied": (
                    float(np.nanmedian(med_src[applied])) if applied.any() else None),
            }
            if q in ALT_CRYSTAL and ALT_CRYSTAL[q] in g.columns and ALT_CRYSTAL[q] in o.columns:
                dalt = np.abs(o[ALT_CRYSTAL[q]].to_numpy(dtype=float) - g[ALT_CRYSTAL[q]].to_numpy(dtype=float))
                entry["max_abs_delta_applied_presolver"] = float(np.nanmax(dalt[applied])) if applied.any() else None
            rec["quantities"][q] = entry
        per_seed.append(rec)

        print(f"\nseed {seed}   rows {rec['n_rows']}  applied {rec['n_applied']}  "
              f"not applied {rec['n_unapplied']}")
        for q, (col, unit, _) in QUANTITIES.items():
            e = rec["quantities"][q]
            print(f"  {q:7s} ({col:16s}) max|delta| applied {e['max_abs_delta_applied']:.3g} {unit},"
                  f"  not applied {e['max_abs_delta_unapplied']:.3g} {unit},"
                  f"  median {e['median_reference']:.4g}")

    summary = {}
    for q, (col, unit, how) in QUANTITIES.items():
        a = [r["quantities"][q]["max_abs_delta_applied"] for r in per_seed
             if r["quantities"][q]["max_abs_delta_applied"] is not None]
        u = [r["quantities"][q]["max_abs_delta_unapplied"] for r in per_seed
             if r["quantities"][q]["max_abs_delta_unapplied"] is not None]
        meds = [r["quantities"][q]["median_reference"] for r in per_seed]
        summary[q] = {
            "column": col,
            "unit": unit,
            "median_kind": how,
            "max_abs_delta_applied_over_seeds": float(max(a)) if a else None,
            "max_abs_delta_applied_argseed": seeds[int(np.argmax(a))] if a else None,
            "max_abs_delta_unapplied_over_seeds": float(max(u)) if u else None,
            "max_abs_delta_unapplied_argseed": seeds[int(np.argmax(u))] if u else None,
            "median_first_seed": meds[0],
            "median_pooled": float(np.nanmedian(np.concatenate(pooled_vals[q]))),
            "median_pooled_applied": float(np.nanmedian(np.concatenate(pooled_applied[q]))),
            "median_mean_of_per_seed": float(np.mean(meds)),
            "median_per_seed": {str(s): m for s, m in zip(seeds, meds)},
        }

    print(f"\n=== over the {len(seeds)} seeds, {args.rows} rows ===")
    for q, e in summary.items():
        print(f"  {q:7s} applied:  at most {e['max_abs_delta_applied_over_seeds']:.3g} "
              f"{e['unit']} (seed {e['max_abs_delta_applied_argseed']})")
        print(f"  {'':7s} not applied: {e['max_abs_delta_unapplied_over_seeds']:.3g} "
              f"{e['unit']} (seed {e['max_abs_delta_unapplied_argseed']})")
        print(f"  {'':7s} {e['median_kind']} reference:  POOLED {e['median_pooled']:.4g}"
              f"   (pooled over applied rows only {e['median_pooled_applied']:.4g})"
              f"   first seed {e['median_first_seed']:.4g}"
              f"   mean of per-seed {e['median_mean_of_per_seed']:.4g}")

    out = {
        "root": str(root),
        "seeds": seeds,
        "rows": args.rows,
        "grounded_name": args.grounded_name,
        "oracle_name": args.oracle_name,
        "per_seed": per_seed,
        "summary": summary,
    }
    if args.out:
        outp = args.out if args.out.is_absolute() else (REPO / args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(out, indent=2) + "\n")
        print(f"\nwrote {outp}")

    if args.expect_published:
        bad, notes = [], []
        for q, e in summary.items():
            sf = 2 if q != "Phi" else 1
            got = signif(e["max_abs_delta_applied_over_seeds"], sf)
            want = signif(PUBLISHED["max_applied"][q], sf)
            if got != want:
                bad.append(f"max|delta| {q} on applied rows: {got:g} != {want:g}")
            gotu = signif(e["max_abs_delta_unapplied_over_seeds"], 2 if q != "Phi" else 1)
            wantu = signif(PUBLISHED["max_unapplied"][q], 2 if q != "Phi" else 1)
            if gotu != wantu:
                bad.append(f"max|delta| {q} on unapplied rows: {gotu:g} != {wantu:g}")
            nsf = PUBLISHED["median_sigfigs"][q]
            want_med = PUBLISHED["median"][q]
            # The sentence says "over the three seeds", so the median it quotes must be the POOLED
            # one.  A first-seed median that happens to agree is not a pass on the right basis.
            if signif(e["median_pooled"], nsf) != signif(want_med, nsf):
                bad.append(f"median {q}: pooled over {len(seeds)} seeds "
                           f"{e['median_pooled']:.4g} != {want_med:g}")
            if signif(e["median_pooled_applied"], nsf) != signif(e["median_pooled"], nsf):
                bad.append(f"median {q}: the sentence's own row set (substitution applied) gives "
                           f"{e['median_pooled_applied']:.4g}, which does not agree with the "
                           f"all-rows pooled {e['median_pooled']:.4g} at {nsf} s.f.")
            if signif(e["median_first_seed"], nsf) != signif(want_med, nsf):
                notes.append(f"median {q}: the pooled median is {e['median_pooled']:.4g} and the "
                             f"FIRST-SEED one is {e['median_first_seed']:.4g}; the printed "
                             f"{want_med:g} is the pooled one, which is what the sentence claims. "
                             "This line is the record that the two bases differ here.")
        if notes:
            print("\nBASIS NOTE (the printed value is the pooled one; the first seed differs):")
            for n in notes:
                print(f"  {n}")
        if bad:
            print("\nEXPECT-PUBLISHED FAILED:")
            for b in bad:
                print(f"  {b}")
            return 1
        print("\nexpect-published: every maximum AND every median Section S1 prints is reproduced "
              f"over all {len(seeds)} seeds -- the maxima as three-seed maxima, the medians pooled "
              "over the seeds, on the row set the sentence names.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
