#!/usr/bin/env python3
"""Validate tgnn_solv.layers.CosmoSac2010Layer against the NIST reference COSMO-SAC-2010
(``cCOSMO.COSMO3``; usnistgov/COSMOSAC, Bell et al. JCTC 2020), exactly as
run_closure_reference_validation.py does for the 2002 layer.

Both engines are fed the SAME Delaware (UD) typed 3-profiles, so any discrepancy is
a pure implementation difference in our differentiable layer, not a profile mismatch.
We compare the residual and combinatorial ln gamma at infinite dilution over many
binary pairs at 298.15 K. A small RMSE (~1e-3) certifies the layer, making the
predicted-null of the learned-sigma -> 2010 experiment readable (a null then means
insensitivity to fidelity, not a broken layer).

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/validate_cosmo2010_layer.py \
        --ud-dir ~/COSMOSAC/profiles/UD --n-compounds 80 --n-pairs 400
"""
from __future__ import annotations
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import argparse
from pathlib import Path
import numpy as np
import cCOSMO
import torch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from tgnn_solv.layers import CosmoSac2010Layer  # noqa: E402

T_REF = 298.15


def load_working_compounds(db, cas_list, n_want, ref="7732-18-5"):
    """Return CAS that both add to the DB and build a COSMO3 model (profile file present)."""
    work = []
    for c in cas_list:
        if len(work) >= n_want:
            break
        try:
            db.add_profile(db.normalize_identifier(c))
            cCOSMO.COSMO3([c, ref], db)   # forces the profile file to load
            work.append(c)
        except Exception:
            continue
    return work


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ud-dir", type=Path, default=Path.home() / "COSMOSAC/profiles/UD")
    ap.add_argument("--n-compounds", type=int, default=80)
    ap.add_argument("--n-pairs", type=int, default=400)
    ap.add_argument("--n-iter", type=int, default=200)
    args = ap.parse_args()

    db = cCOSMO.DelawareProfileDatabase(str(args.ud_dir / "complist.txt"), str(args.ud_dir / "sigma3/"))
    rows = [l.split() for l in (args.ud_dir / "complist.txt").read_text().splitlines()[1:] if l.strip()]
    cas = [r[2] for r in rows if len(r) >= 3]
    # water first so the ref compound is present
    work = load_working_compounds(db, ["7732-18-5"] + cas, args.n_compounds)
    print(f"working compounds: {len(work)}")

    # cache typed 153-profile + area + volume for each working compound.
    # cCOSMO keys profiles by InChIKey (normalize_identifier); psigmaA is an attribute.
    prof, area, vol = {}, {}, {}
    good = []
    for c in work:
        try:
            fp = db.get_profile(db.normalize_identifier(c))
            p = np.concatenate([np.asarray(getattr(fp.profiles, t).psigmaA, float) for t in ("nhb", "oh", "ot")])
            prof[c], area[c], vol[c] = p, float(fp.A_COSMO_A2), float(fp.V_COSMO_A3)
            good.append(c)
        except Exception:
            continue
    work = good
    print(f"profiles cached: {len(work)}")

    rng = np.random.default_rng(0)
    pairs = []
    seen = set()
    while len(pairs) < args.n_pairs and len(seen) < len(work) ** 2:
        s, v = work[rng.integers(len(work))], work[rng.integers(len(work))]
        if s == v or (s, v) in seen:
            continue
        seen.add((s, v))
        pairs.append((s, v))

    # reference (cCOSMO) resid + comb at infinite dilution
    x = np.array([1e-8, 1.0 - 1e-8])
    ref_res, ref_comb, P2, P1, A2, A1, V2, V1, keep = [], [], [], [], [], [], [], [], []
    for s, v in pairs:
        try:
            mp = cCOSMO.COSMO3([s, v], db)
            r = float(mp.get_lngamma_resid(T_REF, x)[0])
            cb = float(mp.get_lngamma_comb(T_REF, x)[0])
        except Exception:
            continue
        ref_res.append(r); ref_comb.append(cb)
        P2.append(prof[s]); P1.append(prof[v]); A2.append(area[s]); A1.append(area[v]); V2.append(vol[s]); V1.append(vol[v])
        keep.append((s, v))
    n = len(keep)
    print(f"validated pairs: {n}")

    # our differentiable layer (residual-only, then +combinatorial) on identical profiles
    layer = CosmoSac2010Layer().eval()
    layer.n_iter_eval = args.n_iter
    tb = lambda a: torch.tensor(np.asarray(a), dtype=torch.float64)
    P2, P1 = tb(P2), tb(P1)
    A2, A1, V2, V1 = tb(A2), tb(A1), tb(V2), tb(V1)
    T = torch.full((n,), T_REF, dtype=torch.float64)
    layer.double()   # float64 buffers for a faithful numeric comparison
    with torch.no_grad():
        my_res = layer.ln_gamma_inf(P2, P1, A2, A1, None, None, T).numpy()
        layer.use_combinatorial = True
        my_tot = layer.ln_gamma_inf(P2, P1, A2, A1, V2, V1, T).numpy()
    my_comb = my_tot - my_res

    ref_res, ref_comb = np.array(ref_res), np.array(ref_comb)
    ref_tot = ref_res + ref_comb

    def stats(name, a, b):
        d = a - b
        print(f"  {name:14s} RMSE={np.sqrt(np.mean(d**2)):.5f}  MAE={np.mean(np.abs(d)):.5f}  max|Δ|={np.max(np.abs(d)):.5f}  (range {b.min():.2f}..{b.max():.2f})")
        return np.sqrt(np.mean(d**2))

    print(f"\n=== CosmoSac2010Layer vs cCOSMO.COSMO3, {n} pairs @ {T_REF} K (float64, {args.n_iter} iters) ===")
    stats("residual", my_res, ref_res)
    stats("combinatorial", my_comb, ref_comb)
    r_tot = stats("total(res+comb)", my_tot, ref_tot)
    # worst residual pairs
    dr = np.abs(my_res - ref_res)
    order = np.argsort(dr)[::-1][:5]
    print("  worst residual pairs (ours vs ref):")
    for i in order:
        print(f"    {keep[i][0]}/{keep[i][1]}: ours={my_res[i]:+.3f} ref={ref_res[i]:+.3f} Δ={dr[i]:.3f}")
    print("\nVERDICT:", "PASS (RMSE < 0.01)" if r_tot < 0.01 else "CHECK (RMSE >= 0.01)")


if __name__ == "__main__":
    main()
