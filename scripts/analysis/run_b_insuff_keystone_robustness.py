#!/usr/bin/env python3
"""Keystone identification robustness (review gating issue #4).

The load-bearing verdict B_closure > B_insuff on the n=60 IDAC set holds iff the
B_insuff upper bound is below MSE/2. A referee argued B_insuff = E[Var(m|z*)] is
UNIDENTIFIED at n=60 in 102-D over a CROSSED 41-solute x 17-solvent design: any
two pairs sharing a solute (or a solvent) share 51/102 z* coordinates exactly, so
every conditional-variance estimator can borrow strength from a near-duplicate
neighbour and bias B_insuff DOWNWARD -- anti-conservative, in exactly the direction
that manufactures the separation. The published robustness guards only
leave-one-SOLVENT-out and a single-axis 17-solvent bootstrap. This script adds the
missing guards the review requires before "likely the closure" stays in the
abstract/contributions:

  (1) DISTINCT-PAIR estimators -- kNN and blocked-OOF (RF/ridge) restricted so a
      neighbour / training row shares NEITHER the solute NOR the solvent of the
      target, removing the 51/102-shared-coordinate leakage so B_insuff cannot be
      deflated by a near-twin; plus a diagnostic of how often the raw 1-NN IS such
      a near-twin (this reconciles the paper's "biased up" vs "most optimistic"
      kNN descriptions: asymptotically biased up, finite-sample optimistic here
      because the nearest neighbour is usually a shared-solute/solvent duplicate).
  (2) leave-one-SOLUTE-out, and a JOINT drop of the top-leverage solute + solvent.
  (3) a TWO-WAY (solute x solvent) cluster bootstrap on the certification margin
      (pigeonhole multiplicity, Cameron-Gelbach-Miller), vs the solvent-only
      bootstrap the paper reports.

Reuses the estimators + matched-pair table from run_b_insuff_decomposition.py; no
COSMO-SAC re-run (g_res is already in matched_pairs.csv). CPU, deterministic.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_b_insuff_keystone_robustness.py
"""

from __future__ import annotations

import importlib.util
import json
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
MATCHED = HERE.parents[1] / "results/b_insuff/matched_pairs.csv"
SIGMA = HERE.parents[1] / "results/sigma_profile_artifact/sigma_profiles.csv"
OUT = HERE.parents[1] / "results/b_insuff/keystone_robustness.json"
SEED = 0


def _load_decomp_module():
    spec = importlib.util.spec_from_file_location(
        "b_insuff_decomp", HERE / "run_b_insuff_decomposition.py")
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules["b_insuff_decomp"] = mod          # dataclass/pickle safety
    spec.loader.exec_module(mod)
    return mod


def _rf():
    return RandomForestRegressor(n_estimators=500, min_samples_leaf=3, random_state=SEED)


# --------------------------------------------------------------------------- #
# Distinct-pair estimators (the core new guard)
# --------------------------------------------------------------------------- #
def knn_var_distinct(Z, m, solute, solvent, k=1, forbid="either"):
    """kNN-in-z* difference estimator restricted to neighbours that do NOT share
    the target's solute/solvent. forbid='either' (share neither solute nor solvent
    -- the strict guard), 'solute', or 'solvent'. Returns 0.5*mean_i mean_j (m_i-m_j)^2."""
    Zs = StandardScaler().fit_transform(Z)
    D = pairwise_distances(Zs)
    n = len(m)
    diffs = []
    for i in range(n):
        if forbid == "either":
            ok = (solute != solute[i]) & (solvent != solvent[i])
        elif forbid == "solute":
            ok = solute != solute[i]
        else:
            ok = solvent != solvent[i]
        ok[i] = False
        cand = np.where(ok)[0]
        order = cand[np.argsort(D[i, cand])[:k]]
        diffs.append(np.mean([(m[i] - m[j]) ** 2 for j in order]))
    return 0.5 * float(np.mean(diffs))


def raw_knn_neighbour_sharing(Z, solute, solvent, k=1):
    """Diagnostic: fraction of points whose raw kNN (in standardized z*) shares the
    target's solute or solvent -- i.e. is a 51/102-shared-coordinate near-twin."""
    Zs = StandardScaler().fit_transform(Z)
    D = pairwise_distances(Zs)
    n = len(solute)
    shares = 0
    for i in range(n):
        d = D[i].copy(); d[i] = np.inf
        nbrs = np.argsort(d)[:k]
        if any(solute[j] == solute[i] or solvent[j] == solvent[i] for j in nbrs):
            shares += 1
    return shares / n


def blocked_oof_var(make_reg, Z, m, solute, solvent, scale=False):
    """Leave-one-(solute AND solvent)-out OOF residual MSE: predict m_i from a
    regressor trained ONLY on rows sharing neither solute_i nor solvent_i, so no
    training row is a 51/102-shared-coordinate near-twin. Upper estimate of
    E[Var(m|z*)] with the near-duplicate leakage removed."""
    n = len(m)
    pred = np.zeros(n)
    for i in range(n):
        mask = (solute != solute[i]) & (solvent != solvent[i])
        if mask.sum() < 5:
            pred[i] = m[mask].mean() if mask.sum() else m.mean()
            continue
        Ztr, Zte = Z[mask], Z[i:i + 1]
        if scale:
            sc = StandardScaler().fit(Ztr)
            Ztr, Zte = sc.transform(Ztr), sc.transform(Zte)
        reg = make_reg()
        reg.fit(Ztr, m[mask])
        pred[i] = reg.predict(Zte)[0]
    return float(np.mean((m - pred) ** 2))


# --------------------------------------------------------------------------- #
# Two-way cluster bootstrap
# --------------------------------------------------------------------------- #
def two_way_cluster_bootstrap(mod, m, g, solute, solvent, n_boot=3000, seed=0):
    """Pigeonhole two-way (solute x solvent) cluster bootstrap on the margin.
    Resample solute IDs and solvent IDs independently with replacement; each row's
    multiplicity = (#times its solute drawn) * (#times its solvent drawn). Recompute
    the deployed-convention B_closure lower bound (MSE - B_insuff^LOTV) and the
    certification margin (lb - B_insuff^LOTV) on the multiplicity-expanded sample."""
    rng = np.random.default_rng(seed)
    su = np.array(sorted(set(solute)))
    sv = np.array(sorted(set(solvent)))
    row_su = np.array([np.where(su == s)[0][0] for s in solute])
    row_sv = np.array([np.where(sv == s)[0][0] for s in solvent])
    lbs, margins = [], []
    for _ in range(n_boot):
        cs = Counter(rng.integers(0, len(su), size=len(su)))
        cv = Counter(rng.integers(0, len(sv), size=len(sv)))
        mult = np.array([cs.get(row_su[r], 0) * cv.get(row_sv[r], 0) for r in range(len(m))])
        if mult.sum() < 12:
            continue
        idx = np.repeat(np.arange(len(m)), mult)
        mm, gg = m[idx], g[idx]
        mse = float(np.mean((mm - gg) ** 2))
        b = mod.lotv_binning(gg, mm, n_bins=max(3, len(mm) // 10))
        lb = mse - b
        lbs.append(lb); margins.append(lb - b)
    lbs, margins = np.array(lbs), np.array(margins)
    return {
        "scheme": "two-way (solute x solvent) pigeonhole, LOTV/binning",
        "n_boot": int(len(lbs)),
        "bclosure_lb_median": round(float(np.median(lbs)), 3),
        "bclosure_lb_ci90": [round(float(np.percentile(lbs, 5)), 3),
                             round(float(np.percentile(lbs, 95)), 3)],
        "margin_median": round(float(np.median(margins)), 3),
        "margin_ci90": [round(float(np.percentile(margins, 5)), 3),
                        round(float(np.percentile(margins, 95)), 3)],
        "P_verdict_holds": round(float(np.mean(margins > 0)), 3),
    }


def solvent_only_bootstrap(mod, m, g, solvent, n_boot=3000, seed=0):
    """The paper's single-axis 17-solvent cluster bootstrap, recomputed here for a
    like-for-like comparison against the two-way scheme."""
    rng = np.random.default_rng(seed)
    sv = np.array(sorted(set(solvent)))
    margins = []
    for _ in range(n_boot):
        drawn = rng.choice(sv, size=len(sv), replace=True)
        idx = np.concatenate([np.where(solvent == s)[0] for s in drawn])
        mm, gg = m[idx], g[idx]
        if len(mm) < 12:
            continue
        mse = float(np.mean((mm - gg) ** 2))
        b = mod.lotv_binning(gg, mm, n_bins=max(3, len(mm) // 10))
        margins.append((mse - b) - b)
    margins = np.array(margins)
    return {"scheme": "solvent-only (paper)", "n_boot": int(len(margins)),
            "margin_median": round(float(np.median(margins)), 3),
            "margin_ci90": [round(float(np.percentile(margins, 5)), 3),
                            round(float(np.percentile(margins, 95)), 3)],
            "P_verdict_holds": round(float(np.mean(margins > 0)), 3)}


# --------------------------------------------------------------------------- #
def _verdict_row(name, binsuff, mse):
    return {"binsuff_up": round(float(binsuff), 4),
            "bclosure_lb": round(float(mse - binsuff), 4),
            "verdict_holds": bool(binsuff < mse / 2)}


def leave_one_group_out(mod, Z, m, g, group, min_keep=20):
    """Drop each level of `group` (solute or solvent); recompute verdict via RF-OOF
    and LOTV/binning. Returns holding counts + per-fold rows."""
    folds = []
    for lvl in sorted(set(group)):
        keep = group != lvl
        if keep.sum() < min_keep:
            continue
        mse_s = float(np.mean((m[keep] - g[keep]) ** 2))
        b_rf = mod.oof_var(_rf, Z[keep], m[keep])
        b_bin = mod.lotv_binning(g[keep], m[keep], n_bins=6)
        folds.append({"dropped": str(lvl), "n": int(keep.sum()), "mse": round(mse_s, 3),
                      "binsuff_rf": round(b_rf, 3), "binsuff_bin": round(b_bin, 3),
                      "holds_rf": bool(b_rf < mse_s / 2), "holds_bin": bool(b_bin < mse_s / 2)})
    return {"n_folds": len(folds),
            "n_holding_rf": sum(r["holds_rf"] for r in folds),
            "n_holding_binning": sum(r["holds_bin"] for r in folds),
            "folds": folds}


def main():
    mod = _load_decomp_module()
    pairs = pd.read_csv(MATCHED)
    table = mod.load_sigma_profiles(str(SIGMA))
    Z = mod.z_star(pairs, table)
    m = pairs["m"].to_numpy(float)
    g = pairs["g_res"].to_numpy(float)            # deployed residual-only convention
    solute = pairs["solute_key"].to_numpy()
    solvent = pairs["solvent_key"].to_numpy()
    mse = float(np.mean((m - g) ** 2))
    thr = mse / 2

    su_counts = pd.Series(solute).value_counts()
    sv_counts = pd.Series(solvent).value_counts()

    out = {"n": len(pairs), "n_solutes": int(su_counts.size), "n_solvents": int(sv_counts.size),
           "convention": "res (deployed)", "mse_true_input": round(mse, 4),
           "verdict_threshold_mse_over_2": round(thr, 4),
           "max_solute_leverage": {"solute": str(su_counts.index[0]), "n_pairs": int(su_counts.iloc[0])},
           "max_solvent_leverage": {"solvent": str(sv_counts.index[0]), "n_pairs": int(sv_counts.iloc[0])}}

    # (1) distinct-pair estimators ------------------------------------------------
    Zs = StandardScaler().fit_transform(Z)
    est = {
        "knn_raw":            _verdict_row("knn_raw", mod.knn_var(Z, m, 1), mse),
        "knn_distinct_pair":  _verdict_row("knn_distinct", knn_var_distinct(Z, m, solute, solvent, 1, "either"), mse),
        "knn_distinct_solute":_verdict_row("knn_distinct_solute", knn_var_distinct(Z, m, solute, solvent, 1, "solute"), mse),
        "knn_distinct_solvent":_verdict_row("knn_distinct_solvent", knn_var_distinct(Z, m, solute, solvent, 1, "solvent"), mse),
        "rf_oof_random5fold": _verdict_row("rf_oof", mod.oof_var(_rf, Z, m), mse),
        "rf_oof_blocked":     _verdict_row("rf_blocked", blocked_oof_var(_rf, Z, m, solute, solvent), mse),
        "ridge_oof_random5fold": _verdict_row("ridge_oof", mod.oof_var(lambda: Ridge(alpha=1.0), Zs, m), mse),
        "ridge_oof_blocked":  _verdict_row("ridge_blocked", blocked_oof_var(lambda: Ridge(alpha=1.0), Z, m, solute, solvent, scale=True), mse),
        "lotv_binning6":      _verdict_row("binning6", mod.lotv_binning(g, m, 6), mse),
    }
    out["distinct_pair_estimators"] = est
    out["raw_knn_neighbour_shares_solute_or_solvent"] = round(
        raw_knn_neighbour_sharing(Z, solute, solvent, 1), 3)

    # (2) leave-one-solute-out, leave-one-solvent-out, joint drop -----------------
    out["leave_one_solute_out"] = leave_one_group_out(mod, Z, m, g, solute, min_keep=20)
    out["leave_one_solvent_out"] = leave_one_group_out(mod, Z, m, g, solvent, min_keep=20)
    top_su, top_sv = su_counts.index[0], sv_counts.index[0]
    keep = (solute != top_su) & (solvent != top_sv)
    mse_j = float(np.mean((m[keep] - g[keep]) ** 2))
    out["joint_drop_top_solute_and_solvent"] = {
        "dropped_solute": str(top_su), "dropped_solvent": str(top_sv),
        "n_remaining": int(keep.sum()), "mse": round(mse_j, 3),
        **{k: v for k, v in {
            "binsuff_rf": round(mod.oof_var(_rf, Z[keep], m[keep]), 3),
            "binsuff_bin": round(mod.lotv_binning(g[keep], m[keep], 6), 3),
        }.items()},
    }
    jr = out["joint_drop_top_solute_and_solvent"]
    jr["holds_rf"] = bool(jr["binsuff_rf"] < mse_j / 2)
    jr["holds_bin"] = bool(jr["binsuff_bin"] < mse_j / 2)

    # (3) two-way vs solvent-only bootstrap --------------------------------------
    out["bootstrap_two_way"] = two_way_cluster_bootstrap(mod, m, g, solute, solvent)
    out["bootstrap_solvent_only"] = solvent_only_bootstrap(mod, m, g, solvent)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    # ---- console summary ----
    print(f"n={out['n']} ({out['n_solutes']} solutes x {out['n_solvents']} solvents), "
          f"MSE_res={mse:.3f}, verdict needs B_insuff < MSE/2 = {thr:.3f}")
    print(f"top-leverage solute={out['max_solute_leverage']['n_pairs']}/60, "
          f"solvent={out['max_solvent_leverage']['n_pairs']}/60; "
          f"raw 1-NN shares solute/solvent in {out['raw_knn_neighbour_shares_solute_or_solvent']*100:.0f}% of points")
    print("(1) B_insuff estimators (verdict holds iff < %.3f):" % thr)
    for k, r in est.items():
        print(f"    {k:24s} B_insuff^up={r['binsuff_up']:.3f}  holds={r['verdict_holds']}")
    ls, lv = out["leave_one_solute_out"], out["leave_one_solvent_out"]
    print(f"(2) leave-one-SOLUTE-out:  RF holds {ls['n_holding_rf']}/{ls['n_folds']}, "
          f"binning {ls['n_holding_binning']}/{ls['n_folds']}")
    print(f"    leave-one-SOLVENT-out: RF holds {lv['n_holding_rf']}/{lv['n_folds']}, "
          f"binning {lv['n_holding_binning']}/{lv['n_folds']}")
    print(f"    joint drop (top solute+solvent -> n={jr['n_remaining']}): "
          f"RF holds={jr['holds_rf']} (B_insuff={jr['binsuff_rf']}), bin holds={jr['holds_bin']}")
    b2, b1 = out["bootstrap_two_way"], out["bootstrap_solvent_only"]
    print(f"(3) two-way bootstrap:  margin={b2['margin_median']} CI90={b2['margin_ci90']}, "
          f"P(holds)={b2['P_verdict_holds']}")
    print(f"    solvent-only (paper): margin={b1['margin_median']} CI90={b1['margin_ci90']}, "
          f"P(holds)={b1['P_verdict_holds']}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
