#!/usr/bin/env python
"""Per-row mechanistic diagnostics for the run_e5 arms (one seed).

Reproduces the seed-44 verification (2026-07-05): why external sigma-supervision
does not beat DirectGNN and why the perfect-sigma oracle is a floor. Deterministic,
so it can be re-run per seed for the paper.

For each TGNN arm (nrtl, ungrounded, grounded_a, grounded_b, oracle) on the supervised
finite subset it reports ln x2 accuracy, the activity/crystal channel spreads, the
crystal<->activity compensation corr(Phi, ln_gamma2), and a covariance attribution of
Var(error) onto the additive channels A=-ln_gamma2, C=-Phi, K=clamp residual, T=-target
(these sum to the error, so the fractions sum to 1). Then the oracle control: on the
oracle-applied rows (identical crystal channel), oracle vs grounded_a with raw /
bias-corrected / affine-recalibrated R2 -- separating eval-time miscalibration from a
genuine recalibration-proof degradation.

Usage:
  python scripts/analysis/run_e5_perrow_diagnostics.py --seed-dir results/e5_sigma_grounding/seed_44
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

ARMS = ["nrtl", "directgnn", "ungrounded", "grounded_a", "grounded_b", "oracle"]
TGNN_ARMS = ["nrtl", "ungrounded", "grounded_a", "grounded_b", "oracle"]


def _col(df, *cands):
    for c in cands:
        if c in df.columns:
            return c
    return None


def _load(seed_dir, arm):
    p = os.path.join(seed_dir, f"{arm}_predictions.csv")
    return pd.read_csv(p) if os.path.exists(p) else None


def _supervised(df, ycol, pcol):
    m = df.copy()
    if "has_solubility" in m.columns:
        m = m[m["has_solubility"].astype(str).str.lower().isin({"true", "1", "1.0"})]
    m = m[np.isfinite(m[ycol]) & np.isfinite(m[pcol])]
    return m


def _r2(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    sst = np.sum((y - y.mean()) ** 2)
    return float("nan") if sst == 0 else 1.0 - np.sum((p - y) ** 2) / sst


def arm_stats(df):
    y = _col(df, "ln_x2_true"); pc = _col(df, "ln_x2_pred", "ln_x2_final")
    phi = _col(df, "Phi", "phi"); g = _col(df, "ln_gamma2_pred", "ln_gamma_2")
    d = _supervised(df, y, pc)
    out = {"n": int(len(d)),
           "mae": float(np.mean(np.abs(d[pc] - d[y]))),
           "rmse": float(np.sqrt(np.mean((d[pc] - d[y]) ** 2))),
           "r2": _r2(d[y], d[pc])}
    if phi and g and phi in d and g in d:
        dd = d[np.isfinite(d[phi]) & np.isfinite(d[g])]
        A, C = -dd[g].values, -dd[phi].values
        K = dd[pc].values - (A + C)
        T = -dd[y].values
        err = dd[pc].values - dd[y].values
        ve = np.var(err)
        frac = {k: float(np.cov(err, x)[0, 1] / ve) if ve > 0 else float("nan")
                for k, x in [("fA", A), ("fC", C), ("fK", K), ("fT", T)]}
        out.update({
            "std_activity": float(dd[g].std()), "mean_activity": float(dd[g].mean()),
            "std_crystal": float(dd[phi].std()),
            "compensation_corr_phi_gamma": float(np.corrcoef(dd[phi], dd[g])[0, 1]),
            "err_var_fractions": frac,
            "r_err_activity": float(np.corrcoef(err, A)[0, 1]),
            "r_err_crystal": float(np.corrcoef(err, C)[0, 1]),
        })
    return out


def oracle_control(dfs):
    """oracle vs grounded_a on the oracle-applied rows, aligned on (pair_key, T)."""
    o, g = dfs.get("oracle"), dfs.get("grounded_a")
    if o is None or g is None:
        return {"error": "missing oracle or grounded_a"}
    y = _col(o, "ln_x2_true"); pc = _col(o, "ln_x2_pred", "ln_x2_final")
    key = [k for k in ("pair_key", "T") if k in o.columns and k in g.columns]
    if "sigma_oracle_applied" in o.columns:
        o = o[o["sigma_oracle_applied"].astype(str).str.lower().isin({"true", "1", "1.0"})]
    o = _supervised(o, y, pc).drop_duplicates(subset=key)
    g = _supervised(g, y, pc).drop_duplicates(subset=key)
    m = o.merge(g, on=key, suffixes=("_o", "_g"))
    yv = m[f"{y}_o"].values

    def rr(p):
        err = p - yv; sst = np.sum((yv - yv.mean()) ** 2)
        r2 = 1 - np.sum(err ** 2) / sst
        r2d = 1 - np.sum((err - err.mean()) ** 2) / sst           # remove constant offset
        r2a = float(np.corrcoef(p, yv)[0, 1] ** 2)                # best affine recalibration
        return {"bias": float(err.mean()), "std_err": float(err.std()),
                "r2_raw": float(r2), "r2_debiased": float(r2d), "r2_affine": r2a}
    return {"n_matched": int(len(m)),
            "oracle": rr(m[f"{pc}_o"].values),
            "grounded_a": rr(m[f"{pc}_g"].values)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-dir", required=True)
    ap.add_argument("--out-json", default=None)
    a = ap.parse_args()

    dfs = {arm: _load(a.seed_dir, arm) for arm in ARMS}
    report = {"seed_dir": a.seed_dir, "per_arm": {}, "oracle_control": None}
    for arm in ARMS:
        if dfs[arm] is None:
            continue
        report["per_arm"][arm] = arm_stats(dfs[arm])
    report["oracle_control"] = oracle_control(dfs)

    print(f"== per-row diagnostics: {a.seed_dir} ==")
    hdr = f"{'arm':<11}{'n':>6}{'MAE':>8}{'R2':>8}{'std_g':>8}{'comp':>8}{'fT':>7}{'r_err_C':>9}{'r_err_A':>9}"
    print(hdr)
    for arm in ARMS:
        s = report["per_arm"].get(arm)
        if not s:
            continue
        comp = s.get("compensation_corr_phi_gamma", float("nan"))
        fT = s.get("err_var_fractions", {}).get("fT", float("nan"))
        rc = s.get("r_err_crystal", float("nan")); ra = s.get("r_err_activity", float("nan"))
        stdg = s.get("std_activity", float("nan"))
        print(f"{arm:<11}{s['n']:>6}{s['mae']:>8.3f}{s['r2']:>8.3f}{stdg:>8.3f}{comp:>8.3f}{fT:>7.2f}{rc:>9.3f}{ra:>9.3f}")
    oc = report["oracle_control"]
    if oc and "oracle" in oc:
        print(f"\n-- oracle control (n_matched={oc['n_matched']}, identical crystal channel) --")
        for k in ("oracle", "grounded_a"):
            r = oc[k]
            print(f"  {k:<11} bias={r['bias']:+.3f} R2_raw={r['r2_raw']:+.3f} "
                  f"R2_debiased={r['r2_debiased']:+.3f} R2_affine={r['r2_affine']:+.3f}")

    out = a.out_json or os.path.join(a.seed_dir, "perrow_diagnostics.json")
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
