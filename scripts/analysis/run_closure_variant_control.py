#!/usr/bin/env python3
"""Does a better-parameterized COSMO-SAC close B_closure? (harsh-review #1 control)

The keystone localizes B_closure to COSMO-SAC-2002's single-parameter H-bond kernel
(90% of error on strong H-bond-donor solvents). A domain reviewer's first question:
do the off-the-shelf better-parameterized variants the field built for exactly this
defect --- COSMO-SAC-2010 (donor/acceptor-typed HB) and -dsp (adds dispersion) ---
actually shrink B_closure on the same matched set?

We answer it with the NIST reference implementation (usnistgov/COSMOSAC, cCOSMO;
Bell et al. JCTC 2020) and its Delaware (UD) 3-sigma-profile database, computing
ln gamma_inf under 2002 / 2010 / dsp for the matched pairs and reporting each MSE
(hence B_closure = MSE - B_insuff) against the same B_insuff floor. Win either way:
if 2010/dsp closes B_closure, the actionable result is "re-parameterize the HB
kernel, don't enrich the inputs"; if not, the structural-ceiling reading hardens.

Requires: pip install <clone of usnistgov/COSMOSAC> (builds cCOSMO), and the UD
database dir from that clone.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_closure_variant_control.py \
        --ud-dir /path/to/COSMOSAC/profiles/UD
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger

import cCOSMO

RDLogger.DisableLog("rdApp.*")
REPO = Path(__file__).resolve().parents[2]
MATCHED = REPO / "results/b_insuff/matched_pairs.csv"
OUT = REPO / "results/b_insuff/closure_variant_control.json"
T = 298.15
B_INSUFF_LOTV = 0.563   # leakage-immune LOTV bound from run_b_insuff_keystone_robustness.py


def _ik(smiles):
    m = Chem.MolFromSmiles(str(smiles))
    return Chem.MolToInchiKey(m) if m is not None else None


def _ud_resolver(ud_dir: Path):
    """Map a molecule's InChIKey to a UD-database InChIKey (exact, else connectivity)."""
    exact, by14 = {}, {}
    for ln in (ud_dir / "complist.txt").read_text().splitlines()[1:]:
        t = ln.split()
        if len(t) < 5:
            continue
        ik = t[-1]
        exact[ik] = ik
        by14.setdefault(ik.split("-")[0], ik)

    def resolve(smiles):
        k = _ik(smiles)
        if k is None:
            return None
        if k in exact:
            return k
        return by14.get(k.split("-")[0])
    return resolve


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ud-dir", type=Path, required=True, help="COSMOSAC/profiles/UD directory")
    args = ap.parse_args()

    resolve = _ud_resolver(args.ud_dir)
    db = cCOSMO.DelawareProfileDatabase(str(args.ud_dir / "complist.txt"), str(args.ud_dir / "sigma3") + "/")

    pairs = pd.read_csv(MATCHED)
    eps = 1e-8
    rows = []
    added = set()
    for _, r in pairs.iterrows():
        su, sv = resolve(r["solute_key"]), resolve(r["solvent_key"])
        if su is None or sv is None:
            continue
        try:
            for iden in (su, sv):
                if iden not in added:
                    db.add_profile(db.normalize_identifier(iden))
                    added.add(iden)
            names = [su, sv]
            x = np.array([eps, 1 - eps])
            c1 = cCOSMO.COSMO1(names, db)          # COSMO-SAC-2002
            c3 = cCOSMO.COSMO3(names, db)          # COSMO-SAC-2010 / -dsp
            g2002 = float(c1.get_lngamma(T, x)[0])
            g2010 = float((c3.get_lngamma_comb(T, x) + c3.get_lngamma_resid(T, x))[0])
            gdsp = float(c3.get_lngamma(T, x)[0])   # 2010 + dispersion
        except Exception as e:  # noqa: BLE001
            continue
        rows.append({"solute": str(r["solute_name"]), "solvent": str(r["solvent_name"]),
                     "m": float(r["m"]), "g2002": round(g2002, 4), "g2010": round(g2010, 4),
                     "gdsp": round(gdsp, 4), "our_g_res_2002_vt2005": float(r["g_res"])})

    m = np.array([x["m"] for x in rows])

    def mse(key):
        g = np.array([x[key] for x in rows])
        ok = np.isfinite(g)
        return float(np.mean((m[ok] - g[ok]) ** 2)), int(ok.sum())

    thr = 2 * B_INSUFF_LOTV     # closure dominates iff MSE > 2*B_insuff (B_clos > B_insuff)
    per = {}
    for name, key in [("cosmosac_2002", "g2002"), ("cosmosac_2010", "g2010"), ("cosmosac_dsp", "gdsp")]:
        mval, n = mse(key)
        per[name] = {"mse": round(mval, 4), "n_finite": n,
                     "B_closure_lb": round(max(0.0, mval - B_INSUFF_LOTV), 4),
                     "closure_dominates": bool(mval > thr)}
    out = {
        "n_pairs": len(rows),
        "reference": "NIST cCOSMO (Bell et al. JCTC 2020), UD 3-profile database",
        "B_insuff_lotv_floor": B_INSUFF_LOTV,
        "verdict_threshold_mse (2*B_insuff)": round(thr, 4),
        "closures": per,
        "our_layer_res_2002_vt2005_mse": round(float(np.mean((m - np.array([x["our_g_res_2002_vt2005"] for x in rows])) ** 2)), 4),
        "worst_2002_pairs": sorted(rows, key=lambda x: -(x["m"] - x["g2002"]) ** 2)[:6],
    }
    OUT.write_text(json.dumps(out, indent=2))

    print(f"n={out['n_pairs']} pairs (UD 3-profiles), T={T}K;  closure dominates iff MSE > 2*B_insuff = {thr:.3f}")
    print("MSE to experiment (true 3-profile inputs, reference cCOSMO):")
    for k in ("cosmosac_2002", "cosmosac_2010", "cosmosac_dsp"):
        r = per[k]
        print(f"    {k:16s} MSE={r['mse']:.3f} (n={r['n_finite']})  B_clos_lb={r['B_closure_lb']:.3f}  "
              f"closure_dominates={r['closure_dominates']}")
    print(f"(our layer, res-only 2002 on VT-2005: MSE={out['our_layer_res_2002_vt2005_mse']:.3f})")
    m2002 = per["cosmosac_2002"]["mse"]
    d10 = m2002 - per["cosmosac_2010"]["mse"]
    print(f"=> 2010 shrinks MSE by {d10:+.3f} ({100*d10/m2002:+.0f}%); B_closure {per['cosmosac_2002']['B_closure_lb']:.2f}"
          f" -> {per['cosmosac_2010']['B_closure_lb']:.2f}; binding term flips closure->inputs under 2010="
          f"{not per['cosmosac_2010']['closure_dominates']}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
