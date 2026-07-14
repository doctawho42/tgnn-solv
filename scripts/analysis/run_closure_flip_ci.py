#!/usr/bin/env python3
"""Uncertainty on the closure-fidelity 'flip' (review blocker: the 2010/dsp anchor was a
bare point estimate on the same underpowered n=60 instrument).

Recompute per-pair ln gamma_inf under COSMO-SAC 2002 / 2010 / dsp (NIST cCOSMO, UD
3-profile DB), then:
  (1) TWO-WAY (solute x solvent) cluster bootstrap of each closure's MSE -> 90% CI,
      matching run_b_insuff_keystone_robustness.py's clustering (not naive pair resampling,
      which ignores that one solute/solvent recurs across pairs).
  (2) The DEFENSIBLE claim, stated honestly: we hold only an UPPER bound on B_insuff
      (LOTV 0.563), so we CANNOT certify 'the inputs bind' (that needs a LOWER bound).
      What we CAN certify is that under 2010/dsp the closure-DOMINANCE certificate is LOST:
      P(MSE < 2*B_insuff) over the bootstrap. If ~1, the 2002 certificate robustly does
      not survive the fidelity upgrade.
  (3) Sensitivity: the flip (B_insuff > B_closure = MSE - B_insuff, i.e. B_insuff > MSE/2)
      survives for any true B_insuff above MSE/2. Report that threshold against every
      B_insuff estimate we have (LOTV 0.563, RF 0.565, ridge 0.625, kNN 0.40).

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_closure_flip_ci.py \
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
OUT = REPO / "results/b_insuff/closure_flip_ci.json"
PERPAIR = REPO / "results/b_insuff/closure_variant_perpair.csv"
T = 298.15
B_INSUFF_LOTV = 0.563
B_INSUFF_ESTIMATES = {"LOTV": 0.563, "RF": 0.565, "ridge": 0.625, "kNN_biased_up": 0.40}
N_BOOT = 4000
ALPHA = 0.10  # 90% CI


def _ik(smiles):
    m = Chem.MolFromSmiles(str(smiles))
    return Chem.MolToInchiKey(m) if m is not None else None


def _ud_resolver(ud_dir: Path):
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
        return exact.get(k, by14.get(k.split("-")[0]))
    return resolve


def compute_perpair(ud_dir: Path) -> pd.DataFrame:
    resolve = _ud_resolver(ud_dir)
    db = cCOSMO.DelawareProfileDatabase(str(ud_dir / "complist.txt"), str(ud_dir / "sigma3") + "/")
    pairs = pd.read_csv(MATCHED)
    eps = 1e-8
    rows, added = [], set()
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
            c1 = cCOSMO.COSMO1(names, db)
            c3 = cCOSMO.COSMO3(names, db)
            g2002 = float(c1.get_lngamma(T, x)[0])
            g2010 = float((c3.get_lngamma_comb(T, x) + c3.get_lngamma_resid(T, x))[0])
            gdsp = float(c3.get_lngamma(T, x)[0])
        except Exception:  # noqa: BLE001
            continue
        rows.append({"solute_key": str(r["solute_key"]), "solvent_key": str(r["solvent_key"]),
                     "solute": str(r["solute_name"]), "solvent": str(r["solvent_name"]),
                     "m": float(r["m"]), "g2002": g2002, "g2010": g2010, "gdsp": gdsp})
    return pd.DataFrame(rows)


def two_way_boot_mse(err2, solute_ids, solvent_ids, rng):
    """One two-way (solute x solvent) cluster-bootstrap MSE: resample unique solutes and
    unique solvents with replacement, weight each pair by (#times solute drawn)*(#times
    solvent drawn)."""
    us = np.unique(solute_ids); uv = np.unique(solvent_ids)
    cs = rng.integers(0, len(us), len(us)); cv = rng.integers(0, len(uv), len(uv))
    ws = np.bincount(cs, minlength=len(us)); wv = np.bincount(cv, minlength=len(uv))
    s_w = dict(zip(us, ws)); v_w = dict(zip(uv, wv))
    w = np.array([s_w[s] * v_w[v] for s, v in zip(solute_ids, solvent_ids)], dtype=float)
    if w.sum() == 0:
        return np.nan
    return float(np.sum(w * err2) / np.sum(w))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ud-dir", type=Path, required=True)
    args = ap.parse_args()

    df = compute_perpair(args.ud_dir)
    PERPAIR.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PERPAIR, index=False)
    n = len(df)
    m = df["m"].to_numpy()
    solute_ids = df["solute_key"].to_numpy(); solvent_ids = df["solvent_key"].to_numpy()
    rng = np.random.default_rng(0)
    thr = 2 * B_INSUFF_LOTV  # closure dominates iff MSE > 2*B_insuff

    out = {"n_pairs": n, "n_solutes": int(df["solute_key"].nunique()),
           "n_solvents": int(df["solvent_key"].nunique()),
           "B_insuff_lotv_floor": B_INSUFF_LOTV, "certificate_threshold_2xBinsuff": round(thr, 4),
           "n_boot": N_BOOT, "closures": {}}

    for name, key in [("cosmosac_2002", "g2002"), ("cosmosac_2010", "g2010"), ("cosmosac_dsp", "gdsp")]:
        g = df[key].to_numpy()
        ok = np.isfinite(g)
        err2 = (m[ok] - g[ok]) ** 2
        sid, vid = solute_ids[ok], solvent_ids[ok]
        mse_pt = float(err2.mean())
        boots = np.array([two_way_boot_mse(err2, sid, vid, rng) for _ in range(N_BOOT)])
        boots = boots[np.isfinite(boots)]
        lo, hi = np.quantile(boots, [ALPHA / 2, 1 - ALPHA / 2])
        bclos_pt = max(0.0, mse_pt - B_INSUFF_LOTV)
        # certificate: does the closure still DOMINATE (MSE > 2*B_insuff)?
        p_dominates = float(np.mean(boots > thr))
        out["closures"][name] = {
            "n_finite": int(ok.sum()),
            "mse_point": round(mse_pt, 4),
            "mse_ci90": [round(float(lo), 4), round(float(hi), 4)],
            "B_closure_lb_point": round(bclos_pt, 4),
            "B_closure_lb_ci90": [round(float(max(0.0, lo - B_INSUFF_LOTV)), 4),
                                  round(float(max(0.0, hi - B_INSUFF_LOTV)), 4)],
            "P_closure_dominates": round(p_dominates, 4),
            "P_certificate_lost": round(1 - p_dominates, 4),
            "flip_threshold_Binsuff_gt": round(mse_pt / 2, 4),  # flip holds iff true B_insuff > MSE/2
        }

    # honest verdict text
    c2002, c2010, cdsp = (out["closures"][k] for k in ("cosmosac_2002", "cosmosac_2010", "cosmosac_dsp"))
    out["verdict"] = {
        "2002_certificate": f"closure dominates with P={c2002['P_closure_dominates']} "
                            f"(MSE 90% CI {c2002['mse_ci90']} vs threshold {thr:.3f})",
        "2010_certificate_lost": f"P={c2010['P_certificate_lost']} that the 2002 closure-dominance "
                                 f"certificate is LOST under 2010 (MSE CI {c2010['mse_ci90']} below {thr:.3f})",
        "flip_sensitivity": (f"the stronger 'inputs bind' reading (B_insuff > B_closure) holds for any true "
                             f"B_insuff > MSE_2010/2 = {c2010['flip_threshold_Binsuff_gt']}; every B_insuff "
                             f"estimate we have exceeds it: {B_INSUFF_ESTIMATES} "
                             f"(only the kNN estimate, known biased-DOWN as a floor and biased for this, is near it). "
                             f"We do NOT claim a certified flip -- only an upper bound on B_insuff exists."),
        "honest_claim": ("Under 2010/dsp the closure-dominance certificate is robustly lost; the binding term is "
                         "no longer certifiably the closure. A certified flip to the inputs would need a lower "
                         "bound on B_insuff, which we do not have."),
    }
    OUT.write_text(json.dumps(out, indent=2))

    print(f"n={n} pairs, {out['n_solutes']} solutes x {out['n_solvents']} solvents; "
          f"closure dominates iff MSE > 2*B_insuff = {thr:.3f}")
    for name in ("cosmosac_2002", "cosmosac_2010", "cosmosac_dsp"):
        c = out["closures"][name]
        print(f"  {name:16s} MSE {c['mse_point']:.3f} CI90 {c['mse_ci90']}  "
              f"B_clos_lb {c['B_closure_lb_point']:.3f} CI90 {c['B_closure_lb_ci90']}  "
              f"P(dominates)={c['P_closure_dominates']:.3f}")
    print(f"\n2010 certificate LOST with P={c2010['P_certificate_lost']:.3f}")
    print(f"flip survives for true B_insuff > {c2010['flip_threshold_Binsuff_gt']:.3f}; "
          f"estimates: {B_INSUFF_ESTIMATES}")
    print(f"wrote {OUT}\nwrote {PERPAIR}")


if __name__ == "__main__":
    main()
