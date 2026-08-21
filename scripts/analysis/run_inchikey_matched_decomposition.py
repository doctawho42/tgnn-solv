#!/usr/bin/env python
"""Re-estimate the VT-2005-matched decomposition under the looser InChIKey match rule.

WHY.  The VT-2005-matched set is matched by RDKit canonical SMILES because that is the rule the
deployed sigma-oracle itself uses, and the Supporting Information records that InChIKey matching
would admit 85 pairs in place of 60 -- and then says the decomposition "was not re-estimated on
the InChIKey-matched set; whether the verdict moves on those 25 extra pairs is untested".

That sentence is the problem this script removes.  The re-estimate costs one CPU run over deposited
files, the set it would enlarge is the weakest one in the paper, and a cheap analysis left unrun at
the weakest point reads as a reluctance to look.  Run it and print it, whichever way it comes out.

WHAT IS AND IS NOT BEING ARGUED.  The stricter rule stays the reported one, for the reason already
given: the profile charged against each label should be the one the deployed pipeline would supply,
not one imported across a tautomer or protonation variant.  This is a robustness reading of a
choice already made, not a proposal to change it.

Usage
-----
    python scripts/analysis/run_inchikey_matched_decomposition.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from run_b_insuff_decomposition import (  # noqa: E402
    _inchikey, evaluate_closure, load_sigma_profiles, match_pairs,
)


def binsuff_upper(g, m, n_bins: int, ddof: int) -> float:
    """E[Var(m | bin(g))] with equal-count bins.

    NOT run_b_insuff_decomposition.lotv_binning, which fixes ddof=0. Sec. 2.5's cell is the
    UNBIASED within-bin variance, and reading this comparison off the maximum-likelihood cell
    would report a robustness check at a cell the paper does not report its margin at -- the
    first run of this script did exactly that and gave +0.236 where the headline is +0.05.
    """
    q = np.quantile(g, np.linspace(0.0, 1.0, n_bins + 1))
    q[0] -= 1e-9
    q[-1] += 1e-9
    idx = np.digitize(g, q[1:-1])
    return float(sum((np.sum(idx == b) / len(m)) * m[idx == b].var(ddof=ddof)
                     for b in range(n_bins) if np.sum(idx == b) > ddof))

T_REF, TOL, N_BINS, DDOF = 298.15, 1.0, 8, 1   # Sec. 2.5's cell: unbiased variance


def match_pairs_inchikey(idac_csv: str, table, temperature: float, tol: float) -> pd.DataFrame:
    """The same aggregation as match_pairs, keyed on InChIKey instead of canonical SMILES.

    The table stays keyed by canonical SMILES -- it is the sigma-profile artifact and the closure
    reads it that way -- so each matched InChIKey is mapped back to the canonical key of the
    profile it hit. That keeps evaluate_closure() and z_star() unchanged, which is the point: the
    only thing this function varies is which labels find a profile.
    """
    by_ik: dict = {}
    for key in table:
        ik = _inchikey(key)
        if ik is not None:
            by_ik.setdefault(ik, key)

    df = pd.read_csv(idac_csv, low_memory=False)
    df["T"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["m"] = pd.to_numeric(df["ln_gamma_inf"], errors="coerce")
    df = df[(df["T"] - temperature).abs() <= tol].dropna(subset=["m"]).copy()
    df["solute_key"] = df["solute_smiles"].map(lambda s: by_ik.get(_inchikey(str(s))))
    df["solvent_key"] = df["solvent_smiles"].map(lambda s: by_ik.get(_inchikey(str(s))))
    df = df.dropna(subset=["solute_key", "solvent_key"])
    return (df.groupby(["solute_key", "solvent_key"], as_index=False)
              .agg(m=("m", "mean"), n_records=("m", "size")))


def report(pairs: pd.DataFrame, table, label: str) -> dict:
    out = {"label": label, "n_pairs": int(len(pairs)),
           "n_solutes": int(pairs.solute_key.nunique()),
           "n_solvents": int(pairs.solvent_key.nunique())}
    m = pairs["m"].to_numpy(float)
    for conv in ("res", "full"):
        g = evaluate_closure(pairs, table, conv)
        mse = float(np.mean((m - g) ** 2))
        b = binsuff_upper(g, m, N_BINS, DDOF)                # the headline cell
        b_ml = binsuff_upper(g, m, N_BINS, 0)                # the other variance convention
        out[conv] = {"mse": round(mse, 4), "b_insuff_up": round(b, 4),
                     "margin": round(mse - 2 * b, 4),
                     "b_insuff_up_ml": round(b_ml, 4), "margin_ml": round(mse - 2 * b_ml, 4)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sigma-profiles",
                    default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--idac", default="notebooks/data/raw/idac.csv")
    ap.add_argument("--check-si", action="store_true",
                    help="bind the Supporting Information's sentence to this run")
    ap.add_argument("--out", type=Path,
                    default=ROOT / "results/b_insuff/inchikey_matched_decomposition.json")
    a = ap.parse_args()

    table = load_sigma_profiles(str(ROOT / a.sigma_profiles))
    canon = match_pairs(str(ROOT / a.idac), table, T_REF, TOL)
    ik = match_pairs_inchikey(str(ROOT / a.idac), table, T_REF, TOL)

    rows = [report(canon, table, "canonical SMILES (reported)"),
            report(ik, table, "InChIKey (looser)")]
    print(f"{'set':<28}{'pairs':>6}{'solutes':>9}{'solvents':>10}"
          f"{'res: MSE':>10}{'bound':>8}{'margin':>9}{'full: margin':>14}")
    for r in rows:
        print(f"{r['label']:<28}{r['n_pairs']:>6}{r['n_solutes']:>9}{r['n_solvents']:>10}"
              f"{r['res']['mse']:>10.3f}{r['res']['b_insuff_up']:>8.3f}"
              f"{r['res']['margin']:>+9.3f}{r['full']['margin']:>+14.3f}")

    d_res = rows[1]["res"]["margin"] - rows[0]["res"]["margin"]
    d_full = rows[1]["full"]["margin"] - rows[0]["full"]["margin"]
    same = (np.sign(rows[0]["res"]["margin"]) == np.sign(rows[1]["res"]["margin"])
            and np.sign(rows[0]["full"]["margin"]) == np.sign(rows[1]["full"]["margin"]))
    print(f"\n{rows[1]['n_pairs'] - rows[0]['n_pairs']} extra pairs move the margin by "
          f"{d_res:+.3f} (residual-only) and {d_full:+.3f} (full).")
    print(f"The sign is {'unchanged' if same else 'CHANGED'} under both conventions.")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({
        "what": "VT-2005-matched decomposition under the canonical-SMILES and InChIKey match rules",
        "cell": {"bins": N_BINS, "unit": "pair", "temperature_K": T_REF},
        "sets": rows, "delta_margin": {"res": round(d_res, 4), "full": round(d_full, 4)},
        "sign_unchanged": bool(same),
    }, indent=2) + "\n")
    print(f"\nwrote {a.out}")

    if a.check_si:
        import re
        si = re.sub(r"\s+", " ", (ROOT / "paper/sections/SI.tex").read_text())
        c, k = rows[0], rows[1]
        want = [("pairs, InChIKey", str(k["n_pairs"])),
                ("MSE, InChIKey", f"{k['res']['mse']:.3f}"),
                ("bound, InChIKey", f"{k['res']['b_insuff_up']:.3f}"),
                ("margin res, InChIKey", f"{k['res']['margin']:.3f}"),
                ("pairs, canonical", str(c["n_pairs"])),
                ("margin res, canonical", f"{c['res']['margin']:.3f}"),
                ("margin full, InChIKey", f"{k['full']['margin']:.2f}"),
                ("margin full, canonical", f"{c['full']['margin']:.2f}")]
        pat = (r"the \$(\d+)\$ pairs give \$\\mathrm\{MSE\}=([\d.]+)\$ against "
               r"\$\\Binsuf\\lesssim([\d.]+)\$, a margin of \$\+([\d.]+)\$ where the reported "
               r"\$(\d+)\$ give \$\+([\d.]+)\$, and \$\+([\d.]+)\$ against \$\+([\d.]+)\$")
        mm = re.search(pat, si)
        if mm is None:
            raise SystemExit("FAIL: the re-estimate sentence is not in the SI in the form this "
                             "gate reads; it was reworded or removed")
        bad = 0
        print("\nSI bind:")
        for (what, truth), got in zip(want, mm.groups()):
            ok = got == truth
            bad += not ok
            print(f"  {'ok  ' if ok else 'FAIL'}  {what:<24} paper {got:>8}   run {truth:>8}")
        if bad:
            raise SystemExit(f"{bad} numeral(s) disagree with this run")


if __name__ == "__main__":
    main()
