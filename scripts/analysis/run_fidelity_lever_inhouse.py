#!/usr/bin/env python3
"""In-house same-database reference-sigma fidelity lever: 2002 vs 2010/dsp closure on
UD typed profiles, PAIRED per pair. Replaces the cross-database n=57 with an in-house,
same-engine (our validated differentiable layers), same-database (UD) contrast.

Prediction pre-registered in reports/PREDICTION_fidelity_lever_2010_2026-07-18.md (commit
7b99a67) BEFORE this ran: MSE(ref->2010) < MSE(ref->2002) on the clean ln-gamma slice.

Slice A (clean, PRIMARY): ln gamma_inf on IDAC-cap-UD activity pairs (no crystal term).
2010 dispersion OFF is primary (validated 1.4e-4); dsp is a flagged secondary.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_fidelity_lever_inhouse.py
"""
from __future__ import annotations
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import json
from rdkit import Chem
from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from tgnn_solv.layers import CosmoSacLayer, CosmoSac2010Layer  # noqa: E402

H = Path.home() / "COSMOSAC/profiles/UD"


def ik1(smi):
    m = Chem.MolFromSmiles(str(smi))
    if m is None:
        return None
    k = Chem.MolToInchiKey(m)
    return k.split("-")[0] if k else None


def parse_ud(path):
    """Parse a UD .sigma file -> (psigmaA array [51 or 153], area, volume, eps/kB, disp_flag).
    Each closure uses its NATIVE averaging: sigma/ (Mullins, 2002), sigma3/ (Hsieh, 2010)."""
    meta, vals = {}, []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line.startswith("# meta:"):
            meta = json.loads(line[len("# meta:"):].strip())
        elif line and not line.startswith("#"):
            vals.append(float(line.split()[1]))
    p = np.asarray(vals, float)
    return (p, float(meta.get("area [A^2]", p[:51].sum())), float(meta.get("volume [A^3]", 0.0)),
            float(meta.get("disp. e/kB [K]", 0.0)), meta.get("disp. flag", ""))


def two_way_cluster_boot(d, solute, solvent, n_boot=3000, seed=0):
    """Two-way (solute x solvent) cluster bootstrap of mean(d); return P(mean>0) and CI90."""
    rng = np.random.default_rng(seed)
    su, sv = np.unique(solute), np.unique(solvent)
    row_su = {s: i for i, s in enumerate(su)}
    row_sv = {s: i for i, s in enumerate(sv)}
    isu = np.array([row_su[s] for s in solute])
    isv = np.array([row_sv[s] for s in solvent])
    means = []
    for _ in range(n_boot):
        cs = np.bincount(rng.integers(0, len(su), len(su)), minlength=len(su))
        cv = np.bincount(rng.integers(0, len(sv), len(sv)), minlength=len(sv))
        w = cs[isu] * cv[isv]
        if w.sum() == 0:
            continue
        means.append(float(np.sum(w * d) / np.sum(w)))
    means = np.array(means)
    return float(np.mean(means > 0)), (float(np.percentile(means, 5)), float(np.percentile(means, 95)))


def main():
    rows = [l.split("\t") if "\t" in l else l.split() for l in (H / "complist.txt").read_text().splitlines()[1:] if l.strip()]
    ud_fb2ik = {}   # first-block -> full InChIKey (= filename stem)
    for r in rows:
        if len(r) > 6 and "-" in r[6]:
            ud_fb2ik.setdefault(r[6].split("-")[0], r[6])

    idac = pd.read_csv(Path(__file__).resolve().parents[2] / "notebooks/data/raw/idac_expanded.csv")
    idac["T"] = pd.to_numeric(idac["temperature"], errors="coerce")
    idac = idac[(idac["T"] - 298.15).abs() <= 1.0].dropna(subset=["ln_gamma_inf"]).copy()
    idac["su1"] = idac["solute_smiles"].map(ik1)
    idac["sv1"] = idac["solvent_smiles"].map(ik1)
    idac = idac.dropna(subset=["su1", "sv1"])
    idac = idac[idac["su1"].isin(ud_fb2ik) & idac["sv1"].isin(ud_fb2ik)].drop_duplicates(["su1", "sv1"])

    # parse each closure's NATIVE UD profile: sigma/ (Mullins, 2002) and sigma3/ (Hsieh, 2010)
    prof = {}
    for fb in set(idac["su1"]) | set(idac["sv1"]):
        ik = ud_fb2ik[fb]
        fu, fs = H / "sigma" / f"{ik}.sigma", H / "sigma3" / f"{ik}.sigma"
        if not (fu.exists() and fs.exists()):
            continue
        try:
            pu, Au, Vu, _, _ = parse_ud(fu)          # untyped 51 (Mullins)
            pt, At, Vt, eps, flag = parse_ud(fs)     # typed 153 (Hsieh)
            if pu.shape[0] != 51 or pt.shape[0] != 153:
                continue
            prof[fb] = dict(pu=pu, pt=pt, Au=float(pu.sum()), At=float(pt.sum()), V=Vt, eps=eps, flag=flag)
        except Exception:
            continue
    idac = idac[idac["su1"].isin(prof) & idac["sv1"].isin(prof)]
    n = len(idac)
    su, sv = idac["su1"].to_numpy(), idac["sv1"].to_numpy()
    print(f"IDAC-cap-UD @298 pairs (native profiles): n={n}  solutes={idac['su1'].nunique()}  solvents={idac['sv1'].nunique()}")

    tb = lambda a: torch.tensor(np.asarray(a), dtype=torch.float64)
    PU2 = tb([prof[s]["pu"] for s in su]); PU1 = tb([prof[s]["pu"] for s in sv])   # 2002, Mullins untyped
    PT2 = tb([prof[s]["pt"] for s in su]); PT1 = tb([prof[s]["pt"] for s in sv])   # 2010, Hsieh typed
    Au2 = tb([prof[s]["Au"] for s in su]); Au1 = tb([prof[s]["Au"] for s in sv])
    At2 = tb([prof[s]["At"] for s in su]); At1 = tb([prof[s]["At"] for s in sv])
    V2 = tb([prof[s]["V"] for s in su]); V1 = tb([prof[s]["V"] for s in sv])
    eps2 = tb([prof[s]["eps"] for s in su]); eps1 = tb([prof[s]["eps"] for s in sv])
    m = idac["ln_gamma_inf"].to_numpy(float)
    T = torch.full((n,), 298.15, dtype=torch.float64)

    l2002 = CosmoSacLayer().double().eval(); l2002.n_iter_eval = 300
    l2010 = CosmoSac2010Layer().double().eval(); l2010.n_iter_eval = 300
    with torch.no_grad():
        g2002 = l2002.ln_gamma_inf(PU2, PU1, Au2, Au1, V2, V1, T).numpy()               # native Mullins
        l2010.use_dispersion = False
        g2010 = l2010.ln_gamma_inf(PT2, PT1, At2, At1, V2, V1, T).numpy()               # native Hsieh, dsp off
        l2010.use_dispersion = True
        g2010d = l2010.ln_gamma_inf(PT2, PT1, At2, At1, V2, V1, T, eps2=eps2, eps1=eps1).numpy()  # +dsp (secondary)

    def report(gname, g):
        e2002, e = g2002 - m, g - m
        mse0, mse = float(np.mean(e2002 ** 2)), float(np.mean(e ** 2))
        d = e2002 ** 2 - e ** 2
        P, ci = two_way_cluster_boot(d, su, sv)
        nb = int(np.sum(e ** 2 < e2002 ** 2))
        print(f"\n  --- 2002 vs {gname} ---")
        print(f"    MSE(2002)={mse0:.3f}  MSE({gname})={mse:.3f}  drop={100*(1-mse/mse0):+.0f}%  "
              f"paired mean(dSE)={float(np.mean(d)):+.3f}  2010 beats 2002 on {nb}/{n}")
        print(f"    two-way solute x solvent bootstrap: P({gname} better)={P:.3f}  margin CI90=[{ci[0]:+.3f},{ci[1]:+.3f}]")
        return mse0, mse, P, ci

    print("\n=== SLICE A: clean ln gamma_inf (IDAC-cap-UD, in-house, same-database, native profiles, PAIRED) ===")
    mse0, mse, P, ci = report("2010", g2010)          # PRIMARY (dsp off, validated 1.4e-4)
    report("2010/dsp", g2010d)                          # SECONDARY (dsp transcribed, not numerically validated)
    print(f"\n  PRIMARY VERDICT (2010 no-dsp): direction {'2010<2002 (as predicted)' if mse < mse0 else '2010>=2002 (FALSIFIES)'};"
          f" certified={'yes' if ci[0] > 0 else 'NO (CI spans 0)'}")


if __name__ == "__main__":
    main()
