#!/usr/bin/env python3
"""Deposit the INPUT-FIXED kernel control for the corner's 2002 -> 2010 fidelity step.

The two published kernels have no prescribed common input (sigma-profile averaging is part of
each model's definition: Mullins for 2002, Hsieh for 2010).  The control that removes the input
as an explanation reduces the typed Hsieh profile to a single 2002-shaped profile by its channel
sum p = p_nhb + p_OH + p_OT (Eq. 9 of Bell et al. 2020), which holds the profile DATABASE, the
CAVITY AREA, the VOLUME and the AVERAGING fixed and varies only the kernel.

Three arms on the same n=60 corner (results/b_insuff/matched_pairs.csv resolved to UD):

  A. 2002 kernel on the native Mullins profile (UD sigma/)      -> the paper's "fair 2002", 1.757
  B. 2002 kernel on the SUMMED Hsieh profile (UD sigma3/, channel sum, same area/volume)
  C. 2010 kernel (dispersion off) on the typed Hsieh profile     -> 0.765

  kernel step (input fixed):  B -> C
  averaging step alone:       A -> B      (same kernel, only the averaging changes)

Both contrasts are two-way (solute x solvent) cluster bootstraps of the paired squared-error
difference, sign convention: positive margin = the second arm is better.

VERIFICATION GATE (printed; the JSON records pass/fail): arms A and C must reproduce the
deposited results/b_insuff/fidelity_lever_fair2002.json corner values (1.7572, 0.7653).
Nothing is deposited unless they do.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_fidelity_lever_inputfixed.py
"""
from __future__ import annotations
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from rdkit import Chem
from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer, CosmoSac2010Layer  # noqa: E402

H = Path.home() / "COSMOSAC" / "profiles" / "UD"
MATCHED = ROOT / "results" / "b_insuff" / "matched_pairs.csv"
REF = ROOT / "results" / "b_insuff" / "fidelity_lever_fair2002.json"
OUT = ROOT / "results" / "b_insuff" / "fidelity_lever_inputfixed.json"


def ik_full(smi):
    m = Chem.MolFromSmiles(str(smi))
    return Chem.MolToInchiKey(m) if m else None


def build_resolver():
    exact, by14 = {}, {}
    for ln in (H / "complist.txt").read_text().splitlines()[1:]:
        t = ln.split()
        if len(t) < 5:
            continue
        ik = t[-1]
        exact[ik] = ik
        by14.setdefault(ik.split("-")[0], ik)

    def resolve(smi):
        k = ik_full(smi)
        if k is None:
            return None
        if k in exact:
            return k
        return by14.get(k.split("-")[0])
    return resolve


def parse_ud(path):
    meta, vals = {}, []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.startswith("# meta:"):
            meta = json.loads(line[len("# meta:"):].strip())
        elif line and not line.startswith("#"):
            vals.append(float(line.split()[1]))
    p = np.asarray(vals, float)
    vol = meta.get("volume [A^3]")
    return p, float(p.sum()), float(vol) if vol is not None else 0.0


def two_way_boot(d, su, sv, n_boot=4000, seed=0):
    """Two-way (solute x solvent) cluster bootstrap of mean(d); P(mean>0) and CI90."""
    rng = np.random.default_rng(seed)
    U, V = np.unique(su), np.unique(sv)
    iu = {s: i for i, s in enumerate(U)}
    iv = {s: i for i, s in enumerate(V)}
    isu = np.array([iu[s] for s in su])
    isv = np.array([iv[s] for s in sv])
    ms = []
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, len(U), len(U)), minlength=len(U))
        cv = np.bincount(rng.integers(0, len(V), len(V)), minlength=len(V))
        w = cs[isu] * cv[isv]
        if w.sum() == 0:
            continue
        ms.append(float(np.sum(w * d) / np.sum(w)))
    ms = np.array(ms)
    return float(np.mean(ms > 0)), (float(np.percentile(ms, 5)), float(np.percentile(ms, 95)))


def _profiles(su_ik, sv_ik):
    fu_s, fu_v = H / "sigma" / f"{su_ik}.sigma", H / "sigma" / f"{sv_ik}.sigma"
    f3_s, f3_v = H / "sigma3" / f"{su_ik}.sigma", H / "sigma3" / f"{sv_ik}.sigma"
    if not all(f.exists() for f in (fu_s, fu_v, f3_s, f3_v)):
        return None
    pu_s, Au_s, _ = parse_ud(fu_s)
    pu_v, Au_v, _ = parse_ud(fu_v)
    pt_s, At_s, V_s = parse_ud(f3_s)
    pt_v, At_v, V_v = parse_ud(f3_v)
    if pu_s.shape[0] != 51 or pu_v.shape[0] != 51 or pt_s.shape[0] != 153 or pt_v.shape[0] != 153:
        return None
    # Eq. 9 reduction: sum the three typed channels back to a single 51-bin profile.
    ps_s = pt_s.reshape(3, 51).sum(axis=0)
    ps_v = pt_v.reshape(3, 51).sum(axis=0)
    return dict(pu_s=pu_s, pu_v=pu_v, Au_s=Au_s, Au_v=Au_v,
                ps_s=ps_s, ps_v=ps_v,                       # summed Hsieh (area == At by construction)
                pt_s=pt_s, pt_v=pt_v, At_s=At_s, At_v=At_v,
                V_s=V_s, V_v=V_v)


def _stack(recs, key):
    return torch.tensor(np.asarray([r[key] for r in recs]), dtype=torch.float64)


def main():
    resolve = build_resolver()
    l2002 = CosmoSacLayer().double().eval(); l2002.n_iter_eval = 300
    l2010 = CosmoSac2010Layer().double().eval(); l2010.n_iter_eval = 300
    l2010.use_dispersion = False

    corner = []
    for _, r in pd.read_csv(MATCHED).iterrows():
        su_ik, sv_ik = resolve(r["solute_key"]), resolve(r["solvent_key"])
        if su_ik is None or sv_ik is None:
            continue
        pr = _profiles(su_ik, sv_ik)
        if pr is None:
            continue
        corner.append({**pr, "su": su_ik, "sv": sv_ik, "m": float(r["m"])})

    n = len(corner)
    T = torch.full((n,), 298.15, dtype=torch.float64)
    with torch.no_grad():
        g_A = l2002.ln_gamma_inf(_stack(corner, "pu_s"), _stack(corner, "pu_v"),
                                 _stack(corner, "Au_s"), _stack(corner, "Au_v"),
                                 _stack(corner, "V_s"), _stack(corner, "V_v"), T).numpy()
        g_B = l2002.ln_gamma_inf(_stack(corner, "ps_s"), _stack(corner, "ps_v"),
                                 _stack(corner, "At_s"), _stack(corner, "At_v"),
                                 _stack(corner, "V_s"), _stack(corner, "V_v"), T).numpy()
        g_C = l2010.ln_gamma_inf(_stack(corner, "pt_s"), _stack(corner, "pt_v"),
                                 _stack(corner, "At_s"), _stack(corner, "At_v"),
                                 _stack(corner, "V_s"), _stack(corner, "V_v"), T).numpy()

    m = np.array([r["m"] for r in corner])
    su = np.array([r["su"] for r in corner])
    sv = np.array([r["sv"] for r in corner])
    se = lambda g: (g - m) ** 2
    mse_A, mse_B, mse_C = float(se(g_A).mean()), float(se(g_B).mean()), float(se(g_C).mean())

    P_kernel, ci_kernel = two_way_boot(se(g_B) - se(g_C), su, sv)     # B -> C, input fixed
    P_avg, ci_avg = two_way_boot(se(g_A) - se(g_B), su, sv)           # A -> B, averaging alone

    print(f"CORNER n={n}  solutes={len(set(su))}  solvents={len(set(sv))}")
    print(f"  A  2002 kernel, native Mullins profile      MSE={mse_A:.4f}")
    print(f"  B  2002 kernel, summed Hsieh profile        MSE={mse_B:.4f}   (the input-fixed 2002 baseline)")
    print(f"  C  2010 kernel, typed Hsieh profile         MSE={mse_C:.4f}")
    print(f"  kernel step  B->C : margin {mse_B - mse_C:+.4f}  P={P_kernel:.3f}  "
          f"CI90=[{ci_kernel[0]:+.4f},{ci_kernel[1]:+.4f}]")
    print(f"  averaging    A->B : margin {mse_A - mse_B:+.4f}  P={P_avg:.3f}  "
          f"CI90=[{ci_avg[0]:+.4f},{ci_avg[1]:+.4f}]")

    ref = json.loads(REF.read_text())["corner"]
    checks = {
        "n_is_60": n == 60,
        "armA_reproduces_deposited_fair2002": abs(mse_A - ref["mse_2002_fair"]) < 1e-6,
        "armC_reproduces_deposited_2010": abs(mse_C - ref["mse_2010"]) < 1e-6,
    }
    passed = all(checks.values())
    print("\nVERIFICATION:", "PASS" if passed else "FAIL")
    for k, v in checks.items():
        print(f"  {'OK ' if v else 'XX '}{k}")

    result = {
        "provenance": "in-house CosmoSacLayer (2002 kernel) and CosmoSac2010Layer (2010 kernel, "
                      "dispersion off) on UD profiles; arm B applies Eq. 9 of Bell et al. 2020 "
                      "(p = p_nhb + p_OH + p_OT) to the Hsieh sigma3 profile so that database, "
                      "cavity area, volume and averaging are held fixed across the kernel step",
        "set": "corner (results/b_insuff/matched_pairs.csv resolved to UD), all rows at 298.15 K",
        "n": n, "n_solutes": int(len(set(su))), "n_solvents": int(len(set(sv))),
        "mse_2002_mullins_native": mse_A,
        "mse_2002_summed_hsieh": mse_B,
        "mse_2010_typed_hsieh": mse_C,
        "kernel_step_input_fixed": {
            "contrast": "2002 kernel on summed Hsieh -> 2010 kernel on typed Hsieh",
            "margin_mse": mse_B - mse_C, "P_2010_better": P_kernel, "ci90": list(ci_kernel)},
        "averaging_step_alone": {
            "contrast": "2002 kernel on native Mullins -> 2002 kernel on summed Hsieh",
            "margin_mse": mse_A - mse_B, "P_summed_better": P_avg, "ci90": list(ci_avg)},
        "bootstrap": "two-way solute x solvent cluster bootstrap, 4000 draws, seed 0, CI90 = 5th/95th pct",
        "verification": checks, "verified": passed,
    }
    if passed:
        OUT.write_text(json.dumps(result, indent=2))
        print(f"\n[saved] {OUT}")
    else:
        print("\n[NOT saved] verification failed; not depositing an unverified artifact.")
    return passed


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
