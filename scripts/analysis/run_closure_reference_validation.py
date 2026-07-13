#!/usr/bin/env python3
"""Validate tgnn_solv.CosmoSacLayer against the NIST reference COSMO-SAC-2002
(review gating issue #2, external-reference validation).

The reviewer noted that our differentiable COSMO-SAC layer was never checked
against a canonical implementation, so B_closure could in principle be an
implementation artifact. This script closes that: it compares our layer to the
NIST reference COSMO-SAC-2002 (Bell, Muller, Harvey et al., *J. Chem. Theory
Comput.* 2020; the pure-python reference in usnistgov/COSMOSAC), feeding BOTH
engines the SAME shipped VT-2005 sigma profiles -- so any discrepancy is purely
the layer's math (fixed point / damping / normalization / combinatorial), not the
profiles. The reference COSMO-SAC-2002 equations (Lin & Sandler 2002) are
reproduced inline below with the same constants our layer uses; the VT-2005
profile database is read from a local clone of the NIST repo.

Reproduce:
    git clone --recursive --depth 1 https://github.com/usnistgov/COSMOSAC.git
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_closure_reference_validation.py \
        --cosmosac-dir COSMOSAC

Result (2026-07-13, VT-2005, 298.15 K, 186 cross-class pairs): our layer matches
the reference to RESIDUAL RMSE 0.0035, MAE 0.0016, max 0.020 ln-gamma; strong
H-bond-donor solvents RMSE 0.0048, acceptor 0.0003, inert 0.0001. The layer is a
faithful COSMO-SAC-2002; B_closure vs experiment is genuine model misspecification,
not an implementation artifact.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import numpy as np
import pandas as pd
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402

T_REF = 298.15

# --- NIST reference COSMO-SAC-2002 (pure python), constants == our layer's ------
_q0, _r0, _z = 79.53, 66.69, 10
_c_hb, _sigma_hb = 85580.0, 0.0084
_R = 8.3144598 / 4184
_AEFF = 7.5
_EPS, _EO = 3.667, 2.395e-4
_alpha_prime = ((_EPS - 1.0) / (_EPS + 0.5)) * (0.3 * _AEFF ** 1.5) / _EO
_sig = np.linspace(-0.025, 0.025, 51)
_sm = np.tile(_sig, (51, 1))
_sn = np.tile(np.array(_sig, ndmin=2).T, (1, 51))
_sacc = np.tril(_sn) + np.triu(_sm, 1)
_sdon = np.tril(_sm) + np.triu(_sn, 1)
_DELTAW = (_alpha_prime / 2) * (_sm + _sn) ** 2 + _c_hb * np.maximum(0, _sacc - _sigma_hb) * np.minimum(0, _sdon + _sigma_hb)


def _ref_Gamma(T, psigma):
    Gamma = np.ones_like(psigma)
    AA = np.exp(-_DELTAW / (_R * T)) * psigma
    for _ in range(50):
        Gn = 1 / np.sum(AA * Gamma, axis=1)
        diff = np.abs((Gamma - Gn) / Gamma)
        Gamma = (Gn + Gamma) / 2
        if np.max(diff) < 1e-8:
            break
    return Gamma


def _load_vt2005(cosmosac_dir: Path):
    idx = pd.read_csv(cosmosac_dir / "profiles/VT2005/Sigma_Profile_Database_Index_v2.txt", sep="\t")

    def get(name):
        m = idx[idx["Compound Name"] == name]
        assert len(m) == 1, f"{name}: {len(m)} matches in VT-2005 index"
        i = int(m["Index No."].iloc[0])
        V = float(m["Vcosmo, A3"].iloc[0])
        f = cosmosac_dir / f"profiles/VT2005/Sigma_Profiles_v2/VT2005-{i:04d}-PROF.txt"
        dd = pd.read_csv(f, names=["sigma", "pA"], sep=r"\s+")
        pA = dd["pA"].to_numpy(float)
        return pA, float(pA.sum()), V                    # area-per-bin, area, V_cosmo
    return get


def _ref_inf(get, solute, solvent, T):
    """Reference (resid, comb, total) ln gamma_inf of solute in solvent."""
    pA_s, A_s, V_s = get(solute)
    pA_v, A_v, V_v = get(solvent)
    eps = 1e-12
    psig_mix = (eps * pA_s + (1 - eps) * pA_v) / (eps * A_s + (1 - eps) * A_v)
    lnG_mix = np.log(_ref_Gamma(T, psig_mix))
    p_s = pA_s / A_s
    lnG_s = np.log(_ref_Gamma(T, p_s))
    resid = A_s / _AEFF * np.sum(p_s * (lnG_mix - lnG_s))
    A = np.array([A_s, A_v]); V = np.array([V_s, V_v]); x = np.array([eps, 1 - eps])
    q = A / _q0; r = V / _r0
    th = x[0] * q[0] / np.dot(x, q); ph = x[0] * r[0] / np.dot(x, r)
    l = _z / 2 * (r - q) - (r - 1)
    comb = np.log(ph / x[0]) + _z / 2 * q[0] * np.log(th / ph) + l[0] - ph / x[0] * np.dot(x, l)
    return float(resid), float(comb), float(resid + comb)


# --- molecule set, grouped by H-bond behaviour ---------------------------------
STRONG_DONOR = ["WATER", "METHANOL", "ETHANOL", "1-HEXANOL", "N-HEXYLAMINE", "CYCLOHEXYLAMINE", "ANILINE"]
ACCEPTOR = ["PYRIDINE", "ACETONE", "ACETONITRILE", "NITROMETHANE"]
INERT = ["BENZENE", "CYCLOHEXANE", "TOLUENE", "CHLOROFORM"]
CLASS = {**{n: "strong_donor" for n in STRONG_DONOR}, **{n: "acceptor" for n in ACCEPTOR}, **{n: "inert" for n in INERT}}


def _our_inf(layer, get, solute, solvent, use_comb):
    pA_s, A_s, V_s = get(solute)
    pA_v, A_v, V_v = get(solvent)
    p2 = torch.tensor(pA_s, dtype=torch.float).unsqueeze(0)
    p1 = torch.tensor(pA_v, dtype=torch.float).unsqueeze(0)
    A2 = torch.tensor([A_s], dtype=torch.float); A1 = torch.tensor([A_v], dtype=torch.float)
    Tt = torch.tensor([T_REF], dtype=torch.float)
    V2 = torch.tensor([V_s], dtype=torch.float) if use_comb else None
    V1 = torch.tensor([V_v], dtype=torch.float) if use_comb else None
    with torch.no_grad():
        return float(layer.ln_gamma_inf(p2, p1, A2, A1, V2, V1, Tt)[0])


def _agg(d):
    d = np.asarray(d)
    return {"rmse": round(float(np.sqrt(np.mean(d ** 2))), 4),
            "mae": round(float(np.mean(np.abs(d))), 4),
            "max_abs": round(float(np.max(np.abs(d))), 4)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cosmosac-dir", type=Path, required=True, help="clone of usnistgov/COSMOSAC")
    ap.add_argument("--out-json", type=Path, default=REPO / "results/b_insuff/closure_reference_validation.json")
    args = ap.parse_args()

    get = _load_vt2005(args.cosmosac_dir)
    layer = CosmoSacLayer(cfg=None); layer.eval()
    mols = STRONG_DONOR + ACCEPTOR + INERT

    rows = []
    for a in mols:
        for b in mols:
            if a == b:
                continue
            ca, cb = CLASS[a], CLASS[b]
            if not (ca == "strong_donor" or cb == "strong_donor"
                    or (ca, cb) in {("acceptor", "inert"), ("inert", "acceptor")}):
                continue
            r_res, _, r_tot = _ref_inf(get, a, b, T_REF)
            o_res = _our_inf(layer, get, a, b, use_comb=False)
            o_full = _our_inf(layer, get, a, b, use_comb=True)
            rows.append({"solute": a, "solvent": b, "solvent_class": cb,
                         "ref_resid": round(r_res, 4), "our_res": round(o_res, 4), "d_res": round(o_res - r_res, 4),
                         "ref_total": round(r_tot, 4), "our_full": round(o_full, 4), "d_full": round(o_full - r_tot, 4)})

    by_class = {c: {"n": sum(r["solvent_class"] == c for r in rows),
                    "residual": _agg([r["d_res"] for r in rows if r["solvent_class"] == c]),
                    "total": _agg([r["d_full"] for r in rows if r["solvent_class"] == c])}
                for c in ("strong_donor", "acceptor", "inert") if any(r["solvent_class"] == c for r in rows)}
    out = {"reference": "NIST usnistgov/COSMOSAC COSMO-PurePython (Bell et al., JCTC 2020), COSMO-SAC-2002",
           "profiles": "identical VT-2005 profiles fed to both engines", "T_K": T_REF, "n_pairs": len(rows),
           "our_layer_iter_eval": layer.n_iter_eval, "our_layer_damping": layer.damping,
           "residual_agreement": _agg([r["d_res"] for r in rows]),
           "total_agreement": _agg([r["d_full"] for r in rows]),
           "by_solvent_class": by_class,
           "worst_pairs": sorted(rows, key=lambda r: -abs(r["d_res"]))[:6], "pairs": rows}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2))

    print(f"n={len(rows)} pairs, identical VT-2005 profiles, T={T_REF}K; our layer "
          f"{layer.n_iter_eval} iters/damping {layer.damping}")
    print(f"RESIDUAL vs reference: {out['residual_agreement']}")
    print(f"TOTAL    vs reference: {out['total_agreement']}")
    for c, v in by_class.items():
        print(f"  {c:14s} n={v['n']:2d}  resid RMSE={v['residual']['rmse']}  total RMSE={v['total']['rmse']}")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
