#!/usr/bin/env python3
"""Separate the two axes confounded in the two published 2002-full cells of the n=60
VT-2005-matched set: profile DATABASE (VT-2005 against UD/Mullins) x segment-iteration
COUNT (30 against 300) x dtype.

WHY THIS EXISTS.  Table 5's note (b) printed "that database difference is the whole
difference between its VT-2005/full 1.80 and the 1.757 here".  It is not: the two cells
differ on the count as well, the two artifacts do not share it, and the count carries a
third of the gap.  The note now prints the crossed decomposition, and the numbers it
prints have to come from somewhere a reader can re-run -- which is this file.  They were
hand-transcribed from a scratch script for one draft, which is the defect this repair
was written against.
"""
from __future__ import annotations
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402
from tgnn_solv.data.utils import canonicalize  # noqa: E402

H = Path.home() / "COSMOSAC" / "profiles" / "UD"
N_BINS = 51
T_REF = 298.15

# ---------------- VT-2005 table (exactly run_b_insuff_decomposition.load_sigma_profiles)
def load_vt(csv_path):
    df = pd.read_csv(csv_path)
    cols = [f"sigma_p_{i}" for i in range(N_BINS)]
    table = {}
    for rec in df.itertuples(index=False):
        d = rec._asdict()
        key = canonicalize(str(d.get("smiles", "")))
        if key is None or key in table:
            continue
        p = np.array([float(d[c]) for c in cols], dtype=float)
        try:
            v = float(d.get("v_cosmo", float("nan")))
        except (TypeError, ValueError):
            v = float("nan")
        table[key] = (p, float(d.get("sigma_area", p.sum())), v)
    return table


# ---------------- UD table (exactly run_fidelity_lever_fair2002)
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


def mse_cell(pairs, table, dtype, n_iter):
    """Full-convention 2002 MSE with the given profile table, dtype and iteration count."""
    layer = CosmoSacLayer(cfg=None)
    if dtype is torch.float64:
        layer = layer.double()
    layer.eval()
    layer.n_iter_eval = n_iter
    p2 = torch.tensor(np.stack([table[k][0] for k in pairs["solute_key"]]), dtype=dtype)
    A2 = torch.tensor([table[k][1] for k in pairs["solute_key"]], dtype=dtype)
    p1 = torch.tensor(np.stack([table[k][0] for k in pairs["solvent_key"]]), dtype=dtype)
    A1 = torch.tensor([table[k][1] for k in pairs["solvent_key"]], dtype=dtype)
    V2 = torch.tensor([table[k][2] for k in pairs["solute_key"]], dtype=dtype)
    V1 = torch.tensor([table[k][2] for k in pairs["solvent_key"]], dtype=dtype)
    T = torch.full((len(pairs),), T_REF, dtype=dtype)
    with torch.no_grad():
        g = layer.ln_gamma_inf(p2, p1, A2, A1, V2, V1, T).numpy().astype(float)
    m = pairs["m"].to_numpy(float)
    return float(np.mean((g - m) ** 2)), g


def main():
    pairs = pd.read_csv(ROOT / "results/b_insuff/matched_pairs.csv")
    vt = load_vt(ROOT / "results/sigma_profile_artifact/sigma_profiles.csv")

    # UD table keyed by the SAME canonical-SMILES keys, so the pair list is untouched
    resolve = build_resolver()
    ud = {}
    keys = sorted(set(pairs["solute_key"]) | set(pairs["solvent_key"]))
    missing = []
    for k in keys:
        ik = resolve(k)
        f_m = H / "sigma" / f"{ik}.sigma" if ik else None
        f_t = H / "sigma3" / f"{ik}.sigma" if ik else None
        if ik is None or not f_m.exists() or not f_t.exists():
            missing.append(k)
            continue
        p, A, _ = parse_ud(f_m)
        _, _, V = parse_ud(f_t)          # volume lives in the typed meta, as in fair2002
        if p.shape[0] != 51:
            missing.append(k)
            continue
        ud[k] = (p, A, V)
    print(f"molecules in the 60-pair set: {len(keys)}  resolved in UD: {len(ud)}  missing: {missing}")

    print("\n--- 2002 full-convention MSE on the same 60 rows ---")
    cells = {}
    for dbname, table in (("VT-2005", vt), ("UD", ud)):
        for n_iter in (30, 300):
            for dt, dtname in ((torch.float32, "f32"), (torch.float64, "f64")):
                mse, _ = mse_cell(pairs, table, dt, n_iter)
                cells[(dbname, n_iter, dtname)] = mse
                print(f"  {dbname:8s} n_iter={n_iter:3d} {dtname}  MSE = {mse:.6f}")

    print("\n--- decomposition of the published 0.0432 gap (VT/30/f32 -> UD/300/f64) ---")
    vt30 = cells[("VT-2005", 30, "f32")]
    ud300 = cells[("UD", 300, "f64")]
    print(f"  published gap                   = {vt30 - ud300:+.4f}")
    for n_iter in (30, 300):
        for dtname in ("f32", "f64"):
            d = cells[("VT-2005", n_iter, dtname)] - cells[("UD", n_iter, dtname)]
            print(f"  database alone at n_iter={n_iter:3d} {dtname} = {d:+.4f}")
    for db in ("VT-2005", "UD"):
        for dtname in ("f32", "f64"):
            d = cells[(db, 30, dtname)] - cells[(db, 300, dtname)]
            print(f"  count alone on {db:8s} {dtname}    = {d:+.4f}")
    for db in ("VT-2005", "UD"):
        for n_iter in (30, 300):
            d = cells[(db, n_iter, "f32")] - cells[(db, n_iter, "f64")]
            print(f"  dtype alone on {db:8s} n={n_iter:3d}   = {d:+.6g}")

    # ---------------- profile-by-profile comparison of the two tabulations
    print("\n--- raw 51-bin profiles, VT-2005 vs UD (Mullins), molecule by molecule ---")
    same, diff = [], []
    for k in keys:
        if k not in ud or k not in vt:
            continue
        a = np.asarray(vt[k][0], float)
        b = np.asarray(ud[k][0], float)
        if a.shape != b.shape:
            diff.append((k, float("nan")))
            continue
        md = float(np.max(np.abs(a - b)))
        (same if md <= 1e-6 else diff).append((k, md))
    allmd = sorted([m for _, m in same] + [m for _, m in diff], reverse=True)
    ntot = len(allmd)
    print(f"  identical to 1e-6 A^2: {len(same)} of {ntot}")
    # THE COUNT DEPENDS ENTIRELY ON THE TOLERANCE, so print the sweep rather than one number.
    for tol in (1e-6, 1e-4, 1e-3, 5e-3, 1e-2):
        print(f"    within {tol:g} A^2: {sum(1 for m in allmd if m <= tol)} of {ntot}")
    for k, md in sorted(diff, key=lambda t: -t[1]):
        print(f"    DIFFERS  {k:40s} max|dp| = {md:.4g}")

    # broad set -- keyed on canonical SMILES, which is what `vt` and `resolve` speak;
    # an earlier revision fed resolve() the UD keys and silently matched nothing (0 of 0).
    broad = pd.read_csv(ROOT / "paper/si_tables/broad_idac_set_477.csv")
    bkeys = sorted(set(broad["solute_smiles"].dropna()) | set(broad["solvent_smiles"].dropna()))
    bs, bd = 0, []
    nb = 0
    for k in bkeys:
        ik = resolve(k)
        f_m = H / "sigma" / f"{ik}.sigma" if ik else None
        if k not in vt or ik is None or not f_m.exists():
            continue
        p_ud, _, _ = parse_ud(f_m)
        if p_ud.shape[0] != 51:
            continue
        nb += 1
        md = float(np.max(np.abs(np.asarray(vt[k][0], float) - p_ud)))
        if md <= 1e-6:
            bs += 1
        else:
            bd.append((k, md))
    print(f"  broad set: {bs} of {nb} molecules present in both tabulations are identical")
    for k, md in sorted(bd, key=lambda t: -t[1]):
        print(f"    DIFFERS  {k:40s} max|dp| = {md:.4g}")


    # ---- DEPOSIT.  The two numbers Table 5's note (b) prints must be generated, not
    # transcribed; that they were not is the defect this file was written against.
    out = ROOT / "results" / "profile_db_vs_iteration"
    out.mkdir(parents=True, exist_ok=True)
    rec = {
        "what": "2002 full-convention MSE on the 60 VT-2005-matched rows, crossed over "
                "profile database x segment-iteration count x dtype",
        "generated_by": "scripts/analysis/run_profile_database_vs_iteration_cross.py",
        "cells": {f"{db}|n_iter={n}|{dt}": v for (db, n, dt), v in cells.items()},
        "published_gap_vt30_minus_ud300": vt30 - ud300,
        "database_alone_at_common_count": {
            f"n_iter={n}|{dt}": cells[("VT-2005", n, dt)] - cells[("UD", n, dt)]
            for (db, n, dt) in cells if db == "UD"},
        "count_alone": {
            f"{db}|{dt}": cells[(db, 30, dt)] - cells[(db, 300, dt)]
            for (db, n, dt) in cells if n == 30},
        "printed_in_note_b": {
            "database_at_common_count": round(cells[("VT-2005", 30, "f32")]
                                              - cells[("UD", 30, "f32")], 3),
        "count_at_common_database": round(cells[("VT-2005", 30, "f32")]
                                          - cells[("VT-2005", 300, "f32")], 3),
            # THE NOTE MAY NOT SAY "IDENTICAL".  At 1e-3 A^2 per bin, ZERO of the 44 agree; the
        # honest statement is the one below -- two molecules are a different calculation and
        # the other 42 agree to within the third-largest deviation.
        "worst_two": [k for k, _ in sorted(diff, key=lambda t: -t[1])[:2]],
        "worst_two_max_abs_dp": [round(m, 3) for _, m in sorted(diff, key=lambda t: -t[1])[:2]],
        "remaining_42_agree_within_A2": round(sorted(allmd, reverse=True)[2], 4),
        "n_within_tolerance": {f"{t:g}": sum(1 for m in allmd if m <= t)
                               for t in (1e-6, 1e-4, 1e-3, 5e-3, 1e-2)},
        },
        "molecules_identical_between_tabulations": {
            "matched_60_set": f"{len(same)} of {len(same) + len(diff)}",
            "broad_set": f"{bs} of {nb}",
            "differ": [k for k, _ in diff],
        },
    }
    (out / "cross.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"\nwrote {out / 'cross.json'}")


if __name__ == "__main__":
    main()
