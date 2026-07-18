#!/usr/bin/env python3
"""Deposit the FAIR full-2002 vs 2010/dsp closure-fidelity contrast that the paper headlines
(1.757 -> 0.765 on the n=60 corner), reproducibly, via our in-house NIST-validated layers on each
closure's NATIVE UD averaging: sigma/ (Mullins) for 2002, sigma3/ (Hsieh, typed) for 2010/dsp.

The committed flip artifact (results/b_insuff/closure_flip_ci.json) carries only the crippled
single-channel cCOSMO 2002 (COSMO1 read a Hsieh sigma3 base -> nhb-only = 1.263). This script
computes the FAIR 2002 (our CosmoSacLayer on the full Mullins profile = 1.757) on the same corner,
with cCOSMO cross-checks, and writes results/b_insuff/fidelity_lever_fair2002.json.

VERIFICATION GATE (printed; the JSON records pass/fail): must reproduce the paper's corner
    fair-2002 MSE ~1.757, 2010 MSE ~0.765, and the cross-checks (cCOSMO crippled-2002 ~1.263,
    our 2010 ~ cCOSMO 2010). Nothing here is trusted unless these hold.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_fidelity_lever_fair2002.py
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
import cCOSMO  # noqa: E402

H = Path.home() / "COSMOSAC" / "profiles" / "UD"
MATCHED = ROOT / "results" / "b_insuff" / "matched_pairs.csv"
IDAC = ROOT / "notebooks" / "data" / "raw" / "idac_expanded.csv"
OUT = ROOT / "results" / "b_insuff" / "fidelity_lever_fair2002.json"


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
    eps = meta.get("disp. e/kB [K]")
    return (p, float(p.sum()),   # cavity area = full profile sum (51 for Mullins, 153 for Hsieh typed)
            float(vol) if vol is not None else 0.0,
            float(eps) if eps is not None else 0.0)


def two_way_boot(d, su, sv, n_boot=4000, seed=0):
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
    pu_s, Au_s, _, _ = parse_ud(fu_s)
    pu_v, Au_v, _, _ = parse_ud(fu_v)
    pt_s, At_s, V_s, eps_s = parse_ud(f3_s)
    pt_v, At_v, V_v, eps_v = parse_ud(f3_v)
    if pu_s.shape[0] != 51 or pu_v.shape[0] != 51 or pt_s.shape[0] != 153 or pt_v.shape[0] != 153:
        return None
    return dict(pu_s=pu_s, pu_v=pu_v, Au_s=Au_s, Au_v=Au_v, pt_s=pt_s, pt_v=pt_v,
                At_s=At_s, At_v=At_v, V_s=V_s, V_v=V_v, eps_s=eps_s, eps_v=eps_v)


def _stack(recs, key):
    return torch.tensor(np.asarray([r[key] for r in recs]), dtype=torch.float64)


def evaluate(recs, l2002, l2010, T_val=298.15, with_ccosmo=False):
    n = len(recs)
    T = torch.full((n,), T_val, dtype=torch.float64)
    with torch.no_grad():
        g2002 = l2002.ln_gamma_inf(_stack(recs, "pu_s"), _stack(recs, "pu_v"),
                                   _stack(recs, "Au_s"), _stack(recs, "Au_v"),
                                   _stack(recs, "V_s"), _stack(recs, "V_v"), T).numpy()
        l2010.use_dispersion = False
        g2010 = l2010.ln_gamma_inf(_stack(recs, "pt_s"), _stack(recs, "pt_v"),
                                   _stack(recs, "At_s"), _stack(recs, "At_v"),
                                   _stack(recs, "V_s"), _stack(recs, "V_v"), T).numpy()
        l2010.use_dispersion = True
        gdsp = l2010.ln_gamma_inf(_stack(recs, "pt_s"), _stack(recs, "pt_v"),
                                  _stack(recs, "At_s"), _stack(recs, "At_v"),
                                  _stack(recs, "V_s"), _stack(recs, "V_v"), T,
                                  eps2=_stack(recs, "eps_s"), eps1=_stack(recs, "eps_v")).numpy()
    m = np.array([r["m"] for r in recs])
    su = np.array([r["su"] for r in recs])
    sv = np.array([r["sv"] for r in recs])
    mse = lambda g: float(np.mean((g - m) ** 2))
    out = {"n": n, "n_solutes": int(len(set(su))), "n_solvents": int(len(set(sv))),
           "mse_2002_fair": mse(g2002), "mse_2010": mse(g2010), "mse_2010dsp": mse(gdsp)}
    for tag, g in [("2010", g2010), ("2010dsp", gdsp)]:
        d = (g2002 - m) ** 2 - (g - m) ** 2  # positive => the modern kernel is better
        P, ci = two_way_boot(d, su, sv)
        out[f"P_{tag}_better"] = P
        out[f"ci90_{tag}"] = list(ci)
    if with_ccosmo:
        out["ccosmo_2002_crippled"] = float(np.nanmean((np.array([r["g2002_crip"] for r in recs]) - m) ** 2))
        out["ccosmo_2010"] = float(np.nanmean((np.array([r["g2010_cc"] for r in recs]) - m) ** 2))
    return out


def main():
    resolve = build_resolver()
    l2002 = CosmoSacLayer().double().eval(); l2002.n_iter_eval = 300
    l2010 = CosmoSac2010Layer().double().eval(); l2010.n_iter_eval = 300

    # --- CORNER (n=60): the matched_pairs corner resolved to UD, with cCOSMO cross-checks ---
    db3 = cCOSMO.DelawareProfileDatabase(str(H / "complist.txt"), str(H / "sigma3") + "/")
    added = set()
    corner = []
    for _, r in pd.read_csv(MATCHED).iterrows():
        su_ik, sv_ik = resolve(r["solute_key"]), resolve(r["solvent_key"])
        if su_ik is None or sv_ik is None:
            continue
        pr = _profiles(su_ik, sv_ik)
        if pr is None:
            continue
        try:
            for iden in (su_ik, sv_ik):
                if iden not in added:
                    db3.add_profile(db3.normalize_identifier(iden)); added.add(iden)
            x = np.array([1e-8, 1 - 1e-8])
            c1 = cCOSMO.COSMO1([su_ik, sv_ik], db3)
            c3 = cCOSMO.COSMO3([su_ik, sv_ik], db3)
            g2002_crip = float(c1.get_lngamma(298.15, x)[0])
            g2010_cc = float((c3.get_lngamma_comb(298.15, x) + c3.get_lngamma_resid(298.15, x))[0])
        except Exception:  # noqa: BLE001
            g2002_crip = g2010_cc = float("nan")
        corner.append({**pr, "su": su_ik, "sv": sv_ik, "m": float(r["m"]),
                       "g2002_crip": g2002_crip, "g2010_cc": g2010_cc})
    corner_res = evaluate(corner, l2002, l2010, with_ccosmo=True)
    print(f"CORNER n={corner_res['n']}  fair-2002 MSE={corner_res['mse_2002_fair']:.3f}  "
          f"2010 MSE={corner_res['mse_2010']:.3f}  P(2010 better)={corner_res['P_2010_better']:.3f} "
          f"CI90={corner_res['ci90_2010']}")
    print(f"  cross-check: cCOSMO crippled-2002={corner_res['ccosmo_2002_crippled']:.3f} (~1.263)  "
          f"cCOSMO-2010={corner_res['ccosmo_2010']:.3f}  our-2010={corner_res['mse_2010']:.3f}")

    # --- REPRESENTATIVE (IDAC-cap-UD, all T): the n~477 set for the no-lever null ---
    # 2002 (Mullins) and 2010-no-dsp (Hsieh) from our validated layers; the DSP arm from cCOSMO's
    # reference get_lngamma (our transcribed dsp term is validated on benign pairs but diverges from
    # the reference on the high-eps tail, so we defer the dsp arm to the reference implementation).
    idac = pd.read_csv(IDAC)
    idac["Tn"] = pd.to_numeric(idac["temperature"], errors="coerce")
    idac = idac.dropna(subset=["ln_gamma_inf", "Tn"]).copy()
    idac["su"] = idac["solute_smiles"].map(resolve)
    idac["sv"] = idac["solvent_smiles"].map(resolve)
    idac = idac.dropna(subset=["su", "sv"])
    dbR = cCOSMO.DelawareProfileDatabase(str(H / "complist.txt"), str(H / "sigma3") + "/")
    addedR = set()
    rep_by_T = {}
    for _, r in idac.iterrows():
        pr = _profiles(r["su"], r["sv"])
        if pr is None or pr["eps_s"] == 0 or pr["eps_v"] == 0:   # dispersion undefined -> valid-eps set
            continue
        try:
            for iden in (r["su"], r["sv"]):
                if iden not in addedR:
                    dbR.add_profile(dbR.normalize_identifier(iden)); addedR.add(iden)
            c3 = cCOSMO.COSMO3([r["su"], r["sv"]], dbR)
            gdsp_cc = float(c3.get_lngamma(float(r["Tn"]), np.array([1e-8, 1 - 1e-8]))[0])  # comb+resid+DISP
        except Exception:  # noqa: BLE001
            continue
        rep_by_T.setdefault(round(float(r["Tn"]), 2), []).append(
            {**pr, "su": r["su"], "sv": r["sv"], "m": float(r["ln_gamma_inf"]), "gdsp_cc": gdsp_cc})
    # evaluate per temperature (the layers take one T), then pool the per-pair squared errors
    rep_flat, se2002, se2010, sedsp = [], [], [], []
    for Tval, recs in rep_by_T.items():
        n = len(recs)
        T = torch.full((n,), Tval, dtype=torch.float64)
        with torch.no_grad():
            g2 = l2002.ln_gamma_inf(_stack(recs, "pu_s"), _stack(recs, "pu_v"), _stack(recs, "Au_s"),
                                    _stack(recs, "Au_v"), _stack(recs, "V_s"), _stack(recs, "V_v"), T).numpy()
            l2010.use_dispersion = False
            g10 = l2010.ln_gamma_inf(_stack(recs, "pt_s"), _stack(recs, "pt_v"), _stack(recs, "At_s"),
                                     _stack(recs, "At_v"), _stack(recs, "V_s"), _stack(recs, "V_v"), T).numpy()
        m = np.array([r["m"] for r in recs])
        gdsp_cc = np.array([r["gdsp_cc"] for r in recs])
        se2002 += list((g2 - m) ** 2); se2010 += list((g10 - m) ** 2); sedsp += list((gdsp_cc - m) ** 2)
        rep_flat += recs
    su = np.array([r["su"] for r in rep_flat]); sv = np.array([r["sv"] for r in rep_flat])
    se2002, se2010, sedsp = map(np.array, (se2002, se2010, sedsp))
    Pd, cid = two_way_boot(se2002 - sedsp, su, sv)
    rep_res = {"n": len(rep_flat), "n_solutes": int(len(set(su))), "n_solvents": int(len(set(sv))),
               "mse_2002_fair": float(se2002.mean()), "mse_2010": float(se2010.mean()),
               "mse_2010dsp": float(sedsp.mean()), "P_2010dsp_better": Pd, "ci90_2010dsp": list(cid)}
    print(f"REPRESENTATIVE n={rep_res['n']}  fair-2002 MSE={rep_res['mse_2002_fair']:.3f}  "
          f"2010/dsp MSE={rep_res['mse_2010dsp']:.3f}  P(dsp better)={rep_res['P_2010dsp_better']:.3f}")

    # --- verification gate ---
    checks = {
        "corner_fair2002_~1.757": abs(corner_res["mse_2002_fair"] - 1.757) < 0.06,
        "corner_2010_~0.765": abs(corner_res["mse_2010"] - 0.765) < 0.06,
        "ccosmo_crippled_~1.263": abs(corner_res["ccosmo_2002_crippled"] - 1.263) < 0.08,
        "our2010_matches_ccosmo2010": abs(corner_res["mse_2010"] - corner_res["ccosmo_2010"]) < 0.05,
        "representative_fair2002_~1.911": abs(rep_res["mse_2002_fair"] - 1.911) < 0.08,
        "representative_2010dsp_~1.855": abs(rep_res["mse_2010dsp"] - 1.855) < 0.20,
        "representative_n_~477": 455 <= rep_res["n"] <= 495,
    }
    passed = all(checks.values())
    print("\nVERIFICATION:", "PASS" if passed else "FAIL")
    for k, v in checks.items():
        print(f"  {'OK ' if v else 'XX '}{k}")
    result = {"provenance": "2002=in-house CosmoSacLayer on Mullins sigma/; 2010-no-dsp=in-house "
                            "CosmoSac2010Layer on Hsieh sigma3/; dsp arm=cCOSMO COSMO3 reference; UD native profiles",
              "corner": corner_res, "representative": rep_res, "verification": checks, "verified": passed}
    if passed:
        OUT.write_text(json.dumps(result, indent=2))
        print(f"\n[saved] {OUT}")
    else:
        print("\n[NOT saved] verification failed; not depositing an unverified artifact.")
    return passed


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
