#!/usr/bin/env python3
"""Closure-implementation validity checks (review gating issue #2).

A referee argued that B_closure (~1.47 res MSE on the n=60 IDAC set) is not
distinguished from an implementation / HB-kernel artifact, because the deployed
differentiable COSMO-SAC layer is (a) residual-only (Staverman-Guggenheim term
off) and (b) never validated against a reference. We cannot ship a full external
reference validation locally (no published VT-2005 IDAC table is committed), so we
do the internal validity checks that bound the artifact hypotheses:

  (1) SELF-SOLVATION: ln gamma_inf(i in i) must be 0 by construction. A non-zero
      value would signal a global bug (grid / damping / normalization). Ruling this
      out removes the "global implementation artifact" hypothesis.
  (2) ERROR LOCALIZATION: partition the residual (m - g_res) by solvent H-bond
      DONOR class. If the error concentrates in strong donors (water/acid/alcohol/
      glycol/amine) and vanishes on inert/acceptor solvents (alkane/aromatic/
      pyridine), the ceiling is COSMO-SAC's documented single-parameter HB-kernel
      weakness on associating systems -- a known limitation, not a global bug.
  (3) SG RECONCILIATION: is the "more-physics-worse" effect (res -> full adds the
      SG combinatorial term and raises MSE) concentrated on SIZE-ASYMMETRIC pairs?
      That is the documented miscalibration of the unmodified SG term (motivating
      modified-SG / Kikic / free-volume corrections), which would make it a
      combinatorial-calibration issue rather than a general grounding paradox.
  (4) HB-KERNEL SENSITIVITY: turn the single HB parameter c_hb off / up and show the
      strong-donor error moves while the inert error does not -- localizing the
      B_closure signal to the crude HB term specifically.

Reuses the matched-pair table (g_res/g_full already committed) + the CosmoSacLayer.
CPU, deterministic.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_closure_validation.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))
MATCHED = REPO / "results/b_insuff/matched_pairs.csv"
SIGMA = REPO / "results/sigma_profile_artifact/sigma_profiles.csv"
OUT = REPO / "results/b_insuff/closure_validation.json"

from tgnn_solv.layers import CosmoSacLayer  # noqa: E402

T_REF = 298.15


def _load_decomp_module():
    spec = importlib.util.spec_from_file_location(
        "b_insuff_decomp", HERE / "run_b_insuff_decomposition.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["b_insuff_decomp"] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
# H-bond donor classification of solvents
# --------------------------------------------------------------------------- #
_SMARTS = {
    "water": "[OX2H2]",
    "carboxylic_acid": "[CX3](=O)[OX2H1]",
    "hydroxyl": "[#6][OX2H]",             # alcohol / glycol / phenol OH
    "amine_NH": "[NX3;!$(NC=O);!$(N=*);H1,H2]",
    "aromatic_N": "[n]",
    "carbonyl": "[CX3]=[OX1]",
    "nitrile": "[NX1]#[CX2]",
    "sulfoxide": "[SX3]=[OX1]",
}
_PAT = {k: Chem.MolFromSmarts(v) for k, v in _SMARTS.items()}


def donor_class(smiles: str) -> str:
    """Strong-donor / acceptor-only / inert bucket by H-bond donor capacity."""
    m = Chem.MolFromSmiles(str(smiles))
    if m is None:
        return "unknown"
    has = {k: m.HasSubstructMatch(p) for k, p in _PAT.items()}
    if has["water"]:
        return "strong_donor"          # water
    if has["carboxylic_acid"] or has["hydroxyl"] or has["amine_NH"]:
        return "strong_donor"          # acid / alcohol / glycol / amine
    if has["aromatic_N"] or has["carbonyl"] or has["nitrile"] or has["sulfoxide"]:
        return "acceptor_only"         # pyridine / amide / ketone / nitrile / DMSO
    return "inert"                     # hydrocarbon / halogenated / aromatic


# --------------------------------------------------------------------------- #
# COSMO-SAC evaluation with an overridable c_hb
# --------------------------------------------------------------------------- #
def eval_closure(table, solute_keys, solvent_keys, convention: str, c_hb=None):
    cfg = None if c_hb is None else SimpleNamespace(cosmo_sac_c_hb=float(c_hb))
    layer = CosmoSacLayer(cfg=cfg)
    layer.eval()
    p2 = torch.tensor(np.stack([table[k][0] for k in solute_keys]), dtype=torch.float)
    A2 = torch.tensor([table[k][1] for k in solute_keys], dtype=torch.float)
    p1 = torch.tensor(np.stack([table[k][0] for k in solvent_keys]), dtype=torch.float)
    A1 = torch.tensor([table[k][1] for k in solvent_keys], dtype=torch.float)
    T = torch.full((len(solute_keys),), T_REF)
    if convention == "full":
        vol = lambda k: (table[k][2] if len(table[k]) > 2 and table[k][2] == table[k][2] and table[k][2] > 0 else float("nan"))
        V2 = torch.tensor([vol(k) for k in solute_keys], dtype=torch.float)
        V1 = torch.tensor([vol(k) for k in solvent_keys], dtype=torch.float)
    else:
        V2 = V1 = None
    with torch.no_grad():
        return layer.ln_gamma_inf(p2, p1, A2, A1, V2, V1, T).numpy()


def _cav_vol(table, key):
    e = table.get(key)
    v = e[2] if e is not None and len(e) > 2 else float("nan")
    return float(v) if v == v and v > 0 else float("nan")


# --------------------------------------------------------------------------- #
def main():
    mod = _load_decomp_module()
    pairs = pd.read_csv(MATCHED)
    table = mod.load_sigma_profiles(str(SIGMA))
    m = pairs["m"].to_numpy(float)
    g_res = pairs["g_res"].to_numpy(float)
    g_full = pairs["g_full"].to_numpy(float)
    solute = pairs["solute_key"].to_numpy()
    solvent = pairs["solvent_key"].to_numpy()
    out = {"n": len(pairs), "mse_res": round(float(np.mean((m - g_res) ** 2)), 4),
           "mse_full": round(float(np.mean((m - g_full) ** 2)), 4)}

    # (1) self-solvation -----------------------------------------------------
    mols = sorted(set(solute) | set(solvent))
    self_lng = eval_closure(table, mols, mols, "res")
    out["self_solvation"] = {
        "n_molecules": len(mols),
        "max_abs_ln_gamma_inf": round(float(np.max(np.abs(self_lng))), 6),
        "mean_abs": round(float(np.mean(np.abs(self_lng))), 6),
        "interpretation": "should be ~0; nonzero => global grid/damping/normalization bug",
    }

    # (2) error localization by donor class ----------------------------------
    cls = np.array([donor_class(k) for k in solvent])
    err2 = (m - g_res) ** 2
    loc = {}
    for c in ["strong_donor", "acceptor_only", "inert", "unknown"]:
        sel = cls == c
        if sel.sum() == 0:
            continue
        loc[c] = {"n_pairs": int(sel.sum()),
                  "mean_sq_error": round(float(err2[sel].mean()), 3),
                  "share_of_total_SSE": round(float(err2[sel].sum() / err2.sum()), 3)}
    out["error_localization_by_donor"] = loc

    # (3) SG reconciliation: more-physics-worse vs size asymmetry -------------
    Vs = np.array([_cav_vol(table, k) for k in solute])
    Vv = np.array([_cav_vol(table, k) for k in solvent])
    ok = np.isfinite(Vs) & np.isfinite(Vv) & (Vs > 0) & (Vv > 0)
    asym = np.full(len(m), np.nan)
    asym[ok] = np.abs(np.log(Vs[ok] / Vv[ok]))            # |ln(V_solute/V_solvent)|
    d_err = (m - g_full) ** 2 - (m - g_res) ** 2          # >0 => SG made it worse
    good = ok & np.isfinite(d_err)
    r = float(np.corrcoef(asym[good], d_err[good])[0, 1])
    med = np.nanmedian(asym[good])
    hi, lo = good & (asym > med), good & (asym <= med)
    out["sg_more_physics_worse"] = {
        "delta_mse_full_minus_res": round(float(d_err[good].mean()), 3),
        "corr(size_asymmetry, delta_sq_error)": round(r, 3),
        "n_used": int(good.sum()),
        "mean_delta_high_asymmetry": round(float(d_err[hi].mean()), 3),
        "mean_delta_low_asymmetry": round(float(d_err[lo].mean()), 3),
        "interpretation": "positive corr / larger delta on size-asymmetric pairs => "
                          "the SG (combinatorial) miscalibration, not a general grounding paradox",
    }

    # (4) HB-kernel (c_hb) sensitivity ---------------------------------------
    base_chb = 85580.0
    sens = {}
    for fac in (0.0, 1.0, 2.0):
        g = eval_closure(table, solute, solvent, "res", c_hb=fac * base_chb)
        e2 = (m - g) ** 2
        sens[f"c_hb_x{fac:.1f}"] = {
            c: round(float(e2[cls == c].mean()), 3)
            for c in ["strong_donor", "acceptor_only", "inert"] if (cls == c).sum()
        }
    out["c_hb_sensitivity_mean_sq_error_by_class"] = sens
    out["c_hb_sensitivity_note"] = ("strong_donor error should move strongly with c_hb while inert "
                                    "stays flat => B_closure signal is localized to the HB kernel")

    OUT.write_text(json.dumps(out, indent=2))

    # ---- console ----
    print(f"n={out['n']}  MSE_res={out['mse_res']}  MSE_full={out['mse_full']}")
    ss = out["self_solvation"]
    print(f"(1) self-solvation ln_gamma_inf(i,i): max|.|={ss['max_abs_ln_gamma_inf']} "
          f"(should be ~0)  -> {'OK, no global bug' if ss['max_abs_ln_gamma_inf'] < 0.05 else 'NONZERO: investigate'}")
    print("(2) error localization by solvent H-bond donor class (res convention):")
    for c, r_ in loc.items():
        print(f"    {c:14s} n={r_['n_pairs']:2d}  mean_sq_err={r_['mean_sq_error']:.3f}  "
              f"share_SSE={r_['share_of_total_SSE']:.2f}")
    sg = out["sg_more_physics_worse"]
    print(f"(3) SG more-physics-worse: delta_MSE(full-res)={sg['delta_mse_full_minus_res']}, "
          f"corr(asym, delta)={sg['corr(size_asymmetry, delta_sq_error)']}, "
          f"hi-asym delta={sg['mean_delta_high_asymmetry']} vs lo-asym={sg['mean_delta_low_asymmetry']}")
    print("(4) c_hb sensitivity (mean sq error by class):")
    for k, v in sens.items():
        print(f"    {k:10s} " + "  ".join(f"{c}={v[c]}" for c in v))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
