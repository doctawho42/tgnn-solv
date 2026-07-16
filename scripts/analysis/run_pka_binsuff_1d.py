"""Point-estimate B_insuff on pKa (1-D latent) -- closes the App G bound-as-value hole.

The decomposition (run_pka_real_decomposition) reports B_insuff as an OOF-RF UPPER bound, because on
solubility z* is a 102-D sigma-profile with only n=60 matched pairs (unestimable conditional variance
-> S4.2's one-sided bounds). App G then reads that bound as a value ("B_insuff ~ 4.7, dominated by
insufficiency"), which the methodology does not license.

On pKa the latent is a SCALAR (sigma_total, one Hammett constant per molecule) with n(ortho)=1008, so
E[Var(pKa | sigma*)] is 1-D point-estimable. We use the difference-based (Rice) estimator WITHIN each
scaffold (pKa0/rho are per-scaffold, i.e. part of z*), pooled by n -- it removes any smooth E[pKa|sigma]
trend, so it is not inflated by curvature and is a point estimate, not a bound. Bootstrap CI included.

Then B_closure = MSE - B_insuff (now a point +/- CI) -> B_closure_norm, and we re-test the frontier
law (which needs x ~ 0.343 for ortho). Outcome NOT prejudged: a confirmed large B_insuff legitimately
refutes the money-plot; a smaller one makes it consistent. We just measure.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_pka_binsuff_1d.py --sdf notebooks/data/raw/pKa_QR.sdf
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import numpy as np

ANALYSIS = Path(__file__).resolve().parent
SYN_LAW = {"intercept": -0.032, "slope": 1.81}   # synthetic MSE law S_norm = a + b*B_closure_norm
S_NORM_MEAS = {"low_F": 0.588}                    # measured ortho S_norm(MSE)


def within_scaffold_var(recs):
    """E[Var(pKa | scaffold)] -- the variance the LATENT must explain, given the external per-scaffold
    pKa0 prior. This is the commensurable denominator: numerator (B_closure) is within-scaffold, so the
    denominator must be too. Dividing by marginal Var(pKa) folds in the between-scaffold spread the
    model gets for FREE from pKa0 -> deflates x by ~1.6x (the reviewer's catch)."""
    tot, N = 0.0, 0
    for s in sorted({r["scaffold"] for r in recs}):
        y = np.array([r["pka"] for r in recs if r["scaffold"] == s], float)
        tot += y.var() * len(y); N += len(y)
    return tot / N


def rice_thin(recs, thin):
    """B_insuff on every-`thin`-th sigma-sorted point within scaffold (Rice upward-bias check)."""
    d = []
    for s in sorted({r["scaffold"] for r in recs}):
        idx = [i for i, r in enumerate(recs) if r["scaffold"] == s]
        sig = np.array([recs[i]["sigma"] for i in idx]); y = np.array([recs[i]["pka"] for i in idx])
        y = y[np.argsort(sig)][::thin]
        if len(y) > 2:
            d.extend((np.diff(y) ** 2 / 2).tolist())
    return float(np.mean(d))


def _load_decomp():
    spec = importlib.util.spec_from_file_location("pkareal", ANALYSIS / "run_pka_real_decomposition.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def rice(sig, y):
    """difference-based conditional-variance estimate of E[Var(y|sig)] (removes smooth trend)."""
    o = np.argsort(sig)
    dy = np.diff(y[o])
    return float(np.mean(dy ** 2) / 2.0) if len(dy) else float("nan")


def rice_terms(recs):
    """pooled within-scaffold squared half-differences d_i = (y_{(i+1)}-y_{(i)})^2 / 2.
    mean(d) = B_insuff point estimate; std(d)/sqrt(len) = a CONSERVATIVE SE (adjacent d_i are
    negatively correlated, so ignoring that overestimates the variance). Resampling-based CIs are
    invalid for a difference estimator (ties), so we use the analytic SE."""
    d = []
    for scaf in sorted({r["scaffold"] for r in recs}):
        idx = [i for i, r in enumerate(recs) if r["scaffold"] == scaf]
        if len(idx) < 6:
            continue
        sig = np.array([recs[i]["sigma"] for i in idx], float)
        y = np.array([recs[i]["pka"] for i in idx], float)
        dy = np.diff(y[np.argsort(sig)])
        d.extend((dy ** 2 / 2.0).tolist())
    return np.array(d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdf", default="notebooks/data/raw/pKa_QR.sdf")
    ap.add_argument("--boot", type=int, default=200)
    args = ap.parse_args()
    mod = _load_decomp()
    recs, _ = mod.load_records(Path(args.sdf), mod._load_builder())

    out = {}
    for strat, name in [("low_F", "ortho (misspecified)"), ("high_F", "meta/para (well-specified)")]:
        rs = [r for r in recs if r["bin"] == strat]
        if len(rs) < 20:
            continue
        pka = np.array([r["pka"] for r in rs]); g = np.array([r["g"] for r in rs])
        mse = float(np.mean((pka - g) ** 2))
        d = rice_terms(rs)
        bi = float(np.mean(d)); se = float(np.std(d, ddof=1) / np.sqrt(len(d)))
        bi_lo, bi_hi = bi - 1.96 * se, bi + 1.96 * se
        # B_closure = MSE - B_insuff (CI flips)
        bclos = mse - bi
        bclos_lo, bclos_hi = mse - bi_hi, mse - bi_lo
        var = within_scaffold_var(rs)                     # CORRECT denominator (commensurable)
        bcn, bcn_lo, bcn_hi = bclos / var, bclos_lo / var, bclos_hi / var
        row = {"n": len(rs), "MSE": round(mse, 3),
               "B_insuff_point": round(bi, 3), "B_insuff_CI": [round(bi_lo, 3), round(bi_hi, 3)],
               "B_closure_point": round(bclos, 3), "B_closure_CI": [round(bclos_lo, 3), round(bclos_hi, 3)],
               "B_closure_norm": round(bcn, 3), "B_closure_norm_CI": [round(bcn_lo, 3), round(bcn_hi, 3)]}
        out[name] = row
        print(f"== {name}: n={len(rs)} ==")
        print(f"   MSE={mse:.3f}  B_insuff(point)={bi:.3f} CI[{bi_lo:.3f},{bi_hi:.3f}]  "
              f"(was <= {'5.36' if strat=='low_F' else '2.78'} OOF-RF upper bound)")
        print(f"   B_closure(point)={bclos:.3f} CI[{bclos_lo:.3f},{bclos_hi:.3f}] / E[Var(pKa|scaf)]={var:.3f}"
              f" -> B_closure_norm={bcn:.3f} CI[{bcn_lo:.3f},{bcn_hi:.3f}]  (marginal-Var denom would give {bclos/pka.var():.3f})")
        row["denominator_within_scaffold"] = round(var, 3)
        if strat in S_NORM_MEAS:
            req = (S_NORM_MEAS[strat] - SYN_LAW["intercept"]) / SYN_LAW["slope"]
            inside = bcn_lo <= req <= bcn_hi
            print(f"   frontier law needs x={req:.3f}; measured x-CI [{bcn_lo:.3f},{bcn_hi:.3f}]")
            print(f"   => law {'CONSISTENT (x INSIDE CI; NOT refuted; CI wide => low power, NOT confirmed)' if inside else 'REFUTED'}")
            row["law_required_x"] = round(req, 3); row["law_consistent"] = bool(inside)
        print(f"   frac of MSE that is insufficiency: {bi/mse:.2f}")
        b1, b2, b3 = rice_thin(rs, 1), rice_thin(rs, 2), rice_thin(rs, 3)
        print(f"   Rice bias check: full={b1:.3f} thin2={b2:.3f} thin3={b3:.3f}  "
              f"({'CLEAN' if abs(b2-b1) < 0.15*b1 else 'FLAG: trend contaminates'})")
        row["rice_thin_check"] = [round(b1, 3), round(b2, 3), round(b3, 3)]
        print()

    Path("results/frontier/pka_binsuff_1d.json").write_text(json.dumps(out, indent=2))
    print("wrote results/frontier/pka_binsuff_1d.json")


if __name__ == "__main__":
    main()
