#!/usr/bin/env python3
r"""GROUND-TRUTH VALIDATION of the cross-fitted B_insuff^up, before it touches the real strata.

This is the validation phase of the pre-declaration in
`scripts/analysis/run_b_insuff_crossfit_estimator.py' (sha256 d158989f...).  It changes nothing
in that file and scores no real margin.  It asks one question:

    is  B_insuff^cf = E[(m - rhat(z*))^2]  actually an UPPER bound on  B_insuff = E[Var(m | z*)],
    at the sample sizes, the dimension and the cluster structure of the real problem --
    and is it TIGHTER than the 8-bin coarsening it is meant to replace?

A bound that is not a bound is worse than a loose one, so the truth must be known in closed form.

==================================================================================================
THE SYNTHETIC POPULATION -- why B_insuff is known exactly
==================================================================================================

Rows are grouped into PAIRS (a solute x solvent chemistry) and pairs into SOURCES (publications),
exactly as in the real set.  For row i in pair p in source s:

    z*_i   = [ sigma_solute(51), A_solute, sigma_solvent(51), A_solvent, T_i ]         (105 dims)
    m_i    = mu(z*_i)  +  u_p  +  b_s  +  eps_i

  * the sigma-profile halves of z* are REAL rows of `results/sigma_profile_artifact/
    sigma_profiles.csv' (1432 profiles, numerical rank 46, first 10 PCs = 99.5% of variance), so
    the regressor faces the real geometry -- collinear, low effective rank, 105 nominal dims;
  * T_i is drawn from the real empirical temperature list, rows-per-pair from the real
    rows-per-pair distribution (185 pairs / 477 rows, max 15), sources from the real source-size
    profile (15 sources, 105 ... 1 rows);
  * mu(z*) = mu_scale * [ sqrt(f) * S_smooth(z*) + sqrt(1-f) * S_wiggly(z_p) ], both standardised.
    S_smooth is a low-order function of the leading PCs and T (learnable); S_wiggly is a fixed
    high-frequency random-Fourier function of the PAIR (in practice unlearnable from ~150 training
    pairs).  f = `smooth_frac' is the knob "how much LEARNABLE structure z* carries".  Both are
    functions of z*, so BOTH belong to E[m | z*] and NEITHER is part of B_insuff -- the wiggly part
    is pure approximation error for the regressor, which is the real problem's situation;
  * u_p ~ N(0, tau_u^2) drawn independently of z_p, shared by every row of the pair -- a pair-level
    shock that is NOT a function of the profile (a pair-specific systematic offset);
  * b_s ~ N(0, tau_b^2) drawn independently of chemistry, shared by every row of the source -- the
    shared-laboratory bias channel;
  * eps_i ~ N(0, sigma^2(z_p)), heteroscedastic in the pair's leading PC, normalised so that the
    row-average of sigma^2 is exactly the requested value.

Because u, b and eps are independent of z*, the conditional law of m given z* has

    Var(m | z*)  =  tau_u^2 + tau_b^2 + sigma^2(z_p),

so, conditional on the design (which is what every estimator sees),

    B_insuff  =  tau_u^2 + tau_b^2 + mean_i sigma^2(z_{p(i)})          EXACT, no Monte-Carlo error.

CAVEAT, stated up front.  Making u_p independent of z_p is what buys the closed form; in the real
set the pair's unmodelled chemistry IS a function of the profile and therefore sits in E[m|z*],
not in B_insuff.  tau_u here should be read as the part of a pair's systematic offset that is
genuinely independent of its profile.  The construction is deliberately HOSTILE in this respect:
a larger tau_u is a larger true B_insuff and therefore LESS slack for the bound, i.e. an easier
place to catch a violation.

The closure under test is  g(z*) = mu_scale*sqrt(f)*S_smooth(z*) + kappa*D(z*)  with D a fixed
quadratic misspecification -- so g is a scalar function of z*, the 8-bin coarsening bins on it
exactly as in the deposit, and MSE = E[(mu-g)^2] + B_insuff is of the real order.

==================================================================================================
WHAT IS MEASURED
==================================================================================================

E1  VALIDITY.  Across true B_insuff/Var(m) ratios and across three cluster-noise structures
    (row-iid / pair-shock / source-shock), and for three fold schemes (leaky row-level KFold,
    the declared pair-grouped GroupKFold, the declared source-grouped GroupKFold): the signed
    relative error (est - truth)/truth and the fraction of draws with est < truth.
E2  SAMPLE SIZE.  Fit size N from 40 (the map's MIN_BOUNDABLE) to 960, both fit scopes
    (global-then-restrict = the declared headline; within-subset = the declared sensitivity).
E3  TIGHTNESS vs STRUCTURE.  smooth_frac from 0 (nothing learnable) to 1 (fully learnable):
    where does the 8-bin histogram beat the forest?
E4  NULL.  mu identically constant: m independent of z*.  Both estimators must return Var(m).

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_crossfit_synthetic_validation.py --exp E2 E3 E4 E1
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold, KFold
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
SIGMA = ROOT / "results" / "sigma_profile_artifact" / "sigma_profiles.csv"
BROAD = ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv"
OUT = ROOT / "results" / "b_insuff" / ("crossfit_synthetic_validation" + ".json")

# --- pinned by the declaration (Sec. 1.2, 1.3, 1.4) --------------------------------------------
RF_KWARGS = {"n_estimators": 300, "min_samples_leaf": 5, "random_state": 0}
RIDGE_ALPHA = 1.0
N_SPLITS = 5
N_BINS = 8
DDOF = 1
MIN_BOUNDABLE = 40
# n_jobs only parallelises tree construction; it does not change the fitted forest.
RF_NJOBS = -1

# --- the real design, matched ------------------------------------------------------------------
REAL_N_ROWS = 477
REAL_N_PAIRS = 185
REAL_N_SOURCES = 15
VAR_M_TARGET = 4.8506          # deposited Var(m) on the broad set
KAPPA = 0.30                   # closure misspecification amplitude


# ================================================================================================
# the coarsening, copied verbatim from run_b_insuff_estimator_grid.lotv
# ================================================================================================
def lotv(g: np.ndarray, m: np.ndarray, n_bins: int = N_BINS, ddof: int = DDOF) -> float:
    q = np.quantile(g, np.linspace(0.0, 1.0, n_bins + 1))
    q[0] -= 1e-9
    q[-1] += 1e-9
    idx = np.digitize(g, q[1:-1])
    total = 0.0
    for b in range(n_bins):
        mm = m[idx == b]
        if len(mm) > ddof:
            total += (len(mm) / len(m)) * float(mm.var(ddof=ddof))
    return total


# ================================================================================================
# design
# ================================================================================================
@dataclass
class Design:
    zstar: np.ndarray          # (n, 105)
    pair_of_row: np.ndarray
    source_of_row: np.ndarray
    pc_pair: np.ndarray        # (n_pairs, k) leading PCs of the pair part
    pc_row: np.ndarray         # (n, k)
    t_std: np.ndarray          # (n,) standardised T


_CACHE: dict = {}
LAST_PARTS: dict = {}      # filled by draw_labels; see the note there


def _pools():
    if "prof" not in _CACHE:
        sp = pd.read_csv(SIGMA)
        cols = [f"sigma_p_{i}" for i in range(51)] + ["sigma_area"]
        _CACHE["prof"] = sp[cols].to_numpy(float)
        df = pd.read_csv(BROAD)
        _CACHE["T"] = df["T_K"].to_numpy(float)
        pair = (df.solute_smiles + "|" + df.solvent_smiles)
        _CACHE["rows_per_pair"] = pair.value_counts().to_numpy()
        _CACHE["source_sizes"] = df.source_doi.value_counts().to_numpy()
    return _CACHE


def build_design(rng: np.random.Generator, n_rows: int = REAL_N_ROWS,
                 n_pairs: int | None = None, n_sources: int = REAL_N_SOURCES,
                 n_pc: int = 8) -> Design:
    """Pairs carry real sigma profiles; rows-per-pair and source sizes follow the real shapes."""
    P = _pools()
    prof = P["prof"]
    if n_pairs is None:
        n_pairs = max(3, int(round(n_rows * REAL_N_PAIRS / REAL_N_ROWS)))
    # rows per pair: resample the real multiplicity distribution, then trim/pad to n_rows
    mult = rng.choice(P["rows_per_pair"], size=n_pairs, replace=True).astype(int)
    mult = np.maximum(mult, 1)
    while mult.sum() > n_rows:
        j = int(rng.integers(0, n_pairs))
        if mult[j] > 1:
            mult[j] -= 1
    while mult.sum() < n_rows:
        mult[int(rng.integers(0, n_pairs))] += 1
    pair_of_row = np.repeat(np.arange(n_pairs), mult)

    sol = prof[rng.integers(0, len(prof), n_pairs)]
    slv = prof[rng.integers(0, len(prof), n_pairs)]
    z_pair = np.hstack([sol, slv])                                   # (n_pairs, 104)
    T = rng.choice(P["T"], size=len(pair_of_row), replace=True)
    zstar = np.hstack([z_pair[pair_of_row], T.reshape(-1, 1)])       # (n, 105)

    # sources: assign PAIRS to sources with the real size profile, independent of chemistry
    ss = P["source_sizes"][:n_sources].astype(float)
    ss = ss / ss.sum()
    source_of_pair = rng.choice(n_sources, size=n_pairs, replace=True, p=ss)
    source_of_row = source_of_pair[pair_of_row]

    zc = z_pair - z_pair.mean(0)
    sd = zc.std(0)
    sd[sd == 0] = 1.0
    U, S, Vt = np.linalg.svd(zc / sd, full_matrices=False)
    pc_pair = U[:, :n_pc] * S[:n_pc]
    pc_pair = pc_pair / (pc_pair.std(0) + 1e-12)
    t_std = (T - T.mean()) / (T.std() + 1e-12)
    return Design(zstar=zstar, pair_of_row=pair_of_row, source_of_row=source_of_row,
                  pc_pair=pc_pair, pc_row=pc_pair[pair_of_row], t_std=t_std)


def _std(v: np.ndarray) -> np.ndarray:
    s = v.std()
    return (v - v.mean()) / s if s > 0 else v - v.mean()


def make_mean_and_closure(des: Design, rng: np.random.Generator, smooth_frac: float,
                          mu_scale: float, kappa: float = KAPPA):
    """mu(z*) = learnable smooth part + unlearnable wiggly part; g = smooth part + misspecification."""
    k = des.pc_pair.shape[1]
    a = rng.standard_normal(k) / np.sqrt(k)
    v = rng.standard_normal(k) / np.sqrt(k)
    s_smooth = _std(des.pc_row @ a
                    + 0.6 * np.tanh(1.5 * (des.pc_row @ v))
                    + 0.4 * des.pc_row[:, 0] * des.t_std
                    + 0.3 * des.t_std)
    # high-frequency random-Fourier function of the PAIR only -> constant within a pair
    n_feat = 24
    W = rng.standard_normal((k, n_feat)) * 2.2
    phi = rng.uniform(0, 2 * np.pi, n_feat)
    c = rng.standard_normal(n_feat)
    wig_pair = _std(np.cos(des.pc_pair @ W + phi) @ c)
    s_wig = wig_pair[des.pair_of_row]
    s_wig = _std(s_wig)

    mu = mu_scale * (np.sqrt(smooth_frac) * s_smooth + np.sqrt(max(0.0, 1 - smooth_frac)) * s_wig)
    u = rng.standard_normal(k) / np.sqrt(k)
    D = _std((des.pc_row @ u) ** 2 - 1.0)
    g = mu_scale * np.sqrt(smooth_frac) * s_smooth + kappa * D
    return mu, g


def draw_labels(des: Design, rng: np.random.Generator, mu: np.ndarray,
                b_insuff: float, f_u: float, f_b: float, f_e: float, hetero_gamma: float = 1.0):
    """m = mu + u_p + b_s + eps.

    Returns (m, truth, cond_var_row) where cond_var_row[i] = Var(m | z*_i) EXACTLY, so the truth
    of any label-blind subset of rows is the mean of cond_var_row over those rows."""
    tot = f_u + f_b + f_e
    f_u, f_b, f_e = f_u / tot, f_b / tot, f_e / tot
    tau_u2, tau_b2, sig2_bar = b_insuff * f_u, b_insuff * f_b, b_insuff * f_e
    n_pairs = des.pc_pair.shape[0]
    n_src = int(des.source_of_row.max()) + 1

    w = _std(des.pc_pair[:, 0])
    s2_row = np.exp(hetero_gamma * w)[des.pair_of_row]
    s2_row = s2_row * (sig2_bar / s2_row.mean()) if s2_row.mean() > 0 else s2_row * 0.0

    up = rng.standard_normal(n_pairs) * np.sqrt(tau_u2)
    bs = rng.standard_normal(n_src) * np.sqrt(tau_b2)
    eps = rng.standard_normal(len(mu)) * np.sqrt(s2_row)
    m = mu + up[des.pair_of_row] + bs[des.source_of_row] + eps
    cond_var_row = tau_u2 + tau_b2 + s2_row
    truth = float(cond_var_row.mean())                       # == b_insuff by construction
    # The REALISED analogue of the truth in this one dataset.  tau_u^2 and tau_b^2 are population
    # variance components; a dataset with only G clusters pins them down to O(sqrt(2/G)) relative
    # precision, so no estimator can track `truth' more closely than this quantity does.  Reported
    # so that a shortfall of an estimator can be split into estimator bias and cluster-count noise.
    shock = up[des.pair_of_row] + bs[des.source_of_row]
    LAST_PARTS.clear()
    LAST_PARTS.update(truth_realised=float(shock.var()) + float(s2_row.mean()),
                      tau_u2=tau_u2, tau_b2=tau_b2, sig2_bar=float(s2_row.mean()),
                      var_shock_realised=float(shock.var()))
    return m, truth, cond_var_row


# ================================================================================================
# estimators
# ================================================================================================
def _splits(scheme: str, n: int, groups_pair: np.ndarray, groups_src: np.ndarray):
    if scheme == "row":
        return list(KFold(n_splits=min(N_SPLITS, n), shuffle=True, random_state=0).split(np.arange(n)))
    g = groups_pair if scheme == "pair" else groups_src
    ng = len(np.unique(g))
    if ng < 3:
        return None
    return list(GroupKFold(n_splits=min(N_SPLITS, ng)).split(np.arange(n), groups=g))


def oof_sq_resid(z: np.ndarray, m: np.ndarray, scheme: str, groups_pair: np.ndarray,
                 groups_src: np.ndarray, model: str = "rf"):
    """Per-row out-of-fold squared residual; also returns fold-integrity flags (gate G1)."""
    sp = _splits(scheme, len(m), groups_pair, groups_src)
    if sp is None:
        return None, None
    oof = np.empty(len(m))
    leak_pair = leak_src = False
    for tr, te in sp:
        if set(groups_pair[tr]) & set(groups_pair[te]):
            leak_pair = True
        if set(groups_src[tr]) & set(groups_src[te]):
            leak_src = True
        if model == "rf":
            est = RandomForestRegressor(n_jobs=RF_NJOBS, **RF_KWARGS)
            est.fit(z[tr], m[tr])
            oof[te] = est.predict(z[te])
        else:
            sc = StandardScaler().fit(z[tr])
            est = Ridge(alpha=RIDGE_ALPHA).fit(sc.transform(z[tr]), m[tr])
            oof[te] = est.predict(sc.transform(z[te]))
    return (m - oof) ** 2, {"pair_across_folds": leak_pair, "source_across_folds": leak_src}


# ================================================================================================
# experiments
# ================================================================================================
def _rec(**kw):
    return {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in kw.items()}


def exp_validity(reps: int, ratios, structures, seed0: int = 1000):
    """E1 + E4: est vs exact truth, across truth ratios, cluster-noise structures, fold schemes."""
    out = []
    for r_idx, ratio in enumerate(ratios):
        for s_idx, (st_name, (f_u, f_b, f_e)) in enumerate(structures.items()):
            for rep in range(reps):
                rng = np.random.default_rng(seed0 + 977 * r_idx + 131 * s_idx + rep)
                des = build_design(rng, n_rows=REAL_N_ROWS)
                b_true = ratio * VAR_M_TARGET
                mu_scale = np.sqrt(max(0.0, (1 - ratio) * VAR_M_TARGET))
                mu, g = make_mean_and_closure(des, rng, smooth_frac=0.6, mu_scale=mu_scale)
                m, truth, _ = draw_labels(des, rng, mu, b_true, f_u, f_b, f_e)
                base = dict(exp="E1", ratio=ratio, structure=st_name, rep=rep,
                            n=len(m), truth=truth, var_m=float(m.var(ddof=1)),
                            mse=float(np.mean((m - g) ** 2)))
                out.append(_rec(estimator="bin8", scheme="-", value=lotv(g, m), **base))
                for scheme in ("row", "pair", "source"):
                    for model in ("rf", "ridge"):
                        sq, gate = oof_sq_resid(des.zstar, m, scheme, des.pair_of_row,
                                                des.source_of_row, model)
                        if sq is None:
                            continue
                        out.append(_rec(estimator=model, scheme=scheme, value=float(sq.mean()),
                                        oof_r2=float(1 - sq.mean() / m.var()),
                                        g1_pair_leak=gate["pair_across_folds"],
                                        g1_source_leak=gate["source_across_folds"], **base))
    return out


def exp_sample_size(reps: int, sizes, seed0: int = 2000):
    """E2: fit size N, both fit scopes.  Global scope additionally restricted to sub-strata."""
    out = []
    ratio, smooth_frac = 0.10, 0.6
    for si, N in enumerate(sizes):
        for rep in range(reps):
            rng = np.random.default_rng(seed0 + 613 * si + rep)
            nsrc = max(3, min(REAL_N_SOURCES, N // 30))
            des = build_design(rng, n_rows=N, n_sources=nsrc)
            b_true = ratio * VAR_M_TARGET
            mu_scale = np.sqrt((1 - ratio) * VAR_M_TARGET)
            mu, g = make_mean_and_closure(des, rng, smooth_frac, mu_scale)
            m, truth, _ = draw_labels(des, rng, mu, b_true, 0.3, 0.2, 0.5)
            base = dict(exp="E2", n=N, rep=rep, truth=truth, var_m=float(m.var(ddof=1)),
                        n_pairs=int(des.pc_pair.shape[0]), n_sources=int(nsrc))
            out.append(_rec(estimator="bin8", scheme="-", scope="within", value=lotv(g, m), **base))
            for scheme in ("pair", "source", "row"):
                sq, gate = oof_sq_resid(des.zstar, m, scheme, des.pair_of_row, des.source_of_row)
                if sq is None:
                    continue
                out.append(_rec(estimator="rf", scheme=scheme, scope="within",
                                value=float(sq.mean()),
                                oof_r2=float(1 - sq.mean() / m.var()),
                                g1_pair_leak=gate["pair_across_folds"],
                                g1_source_leak=gate["source_across_folds"], **base))
            sq, _ = oof_sq_resid(des.zstar, m, "pair", des.pair_of_row, des.source_of_row, "ridge")
            if sq is not None:
                out.append(_rec(estimator="ridge", scheme="pair", scope="within",
                                value=float(sq.mean()), **base))
    return out


def exp_global_then_restrict(reps: int, sub_sizes, seed0: int = 3000):
    """E2b: the DECLARED headline scope -- fit once on 473 rows, evaluate on chemical sub-strata.

    Sub-strata are unions of whole pairs (label-blind), as every stratum of the real map is."""
    out = []
    ratio, smooth_frac = 0.10, 0.6
    for rep in range(reps):
        rng = np.random.default_rng(seed0 + rep)
        des = build_design(rng, n_rows=REAL_N_ROWS)
        b_true = ratio * VAR_M_TARGET
        mu_scale = np.sqrt((1 - ratio) * VAR_M_TARGET)
        mu, g = make_mean_and_closure(des, rng, smooth_frac, mu_scale)
        m, _truth_global, cond_var_row = draw_labels(des, rng, mu, b_true, 0.3, 0.2, 0.5)
        sq_by_scheme = {}
        for scheme in ("pair", "source"):
            sq, _ = oof_sq_resid(des.zstar, m, scheme, des.pair_of_row, des.source_of_row)
            sq_by_scheme[scheme] = sq
        n_pairs = des.pc_pair.shape[0]
        for ns in sub_sizes:
            for k in range(3):
                sel_pairs = rng.permutation(n_pairs)
                rows = np.array([], int)
                for p in sel_pairs:
                    rows = np.concatenate([rows, np.where(des.pair_of_row == p)[0]])
                    if len(rows) >= ns:
                        break
                if len(rows) < ns:
                    continue
                rows = rows[:ns]
                t_sub = float(cond_var_row[rows].mean())
                base = dict(exp="E2b", n_sub=int(ns), rep=rep, draw=k, truth=t_sub,
                            var_m=float(m[rows].var(ddof=1)))
                out.append(_rec(estimator="bin8", scheme="-", scope="global",
                                value=lotv(g[rows], m[rows]), **base))
                for scheme, sq in sq_by_scheme.items():
                    if sq is None:
                        continue
                    out.append(_rec(estimator="rf", scheme=scheme, scope="global",
                                    value=float(sq[rows].mean()), **base))
    return out


def exp_dimension(reps: int, dims, seed0: int = 7000):
    """E6 (DIAGNOSTIC, not a proposal): the regressor's feature set coarsened to the leading k
    unsupervised PCs of z*.

    Why this is asked.  The pKa domain, where this estimator already headlines, regresses m on a
    ONE-dimensional z* within a scaffold; here z* is 105-dimensional over ~185 pairs.  Coarsening
    the features is a valid operation on the bound (tower property, declaration Sec. 1.1: a sigma-
    field smaller than sigma(z*) can only RAISE E[Var(m | .)]), so every point on this curve is a
    legitimate upper bound.  It is reported to locate the failure, NOT as a substitute estimator:
    Sec. 7 of the declaration forbids an alternative feature set, and adopting one would need a new
    declaration.  The PCs are fitted without labels."""
    out = []
    ratio, smooth_frac = 0.10, 0.6
    for di, k in enumerate(dims):
        for rep in range(reps):
            rng = np.random.default_rng(seed0 + 421 * di + rep)
            des = build_design(rng, n_rows=REAL_N_ROWS)
            b_true = ratio * VAR_M_TARGET
            mu_scale = np.sqrt((1 - ratio) * VAR_M_TARGET)
            mu, g = make_mean_and_closure(des, rng, smooth_frac, mu_scale)
            m, truth, _ = draw_labels(des, rng, mu, b_true, 0.3, 0.2, 0.5)
            if k is None:
                z = des.zstar
                lab = "raw105"
            else:
                zc = des.zstar - des.zstar.mean(0)
                sd = zc.std(0)
                sd[sd == 0] = 1.0
                U, S, _ = np.linalg.svd(zc / sd, full_matrices=False)
                z = U[:, :k] * S[:k]
                lab = f"pc{k}"
            base = dict(exp="E6", features=lab, rep=rep, n=len(m), truth=truth,
                        var_m=float(m.var(ddof=1)), mse=float(np.mean((m - g) ** 2)))
            out.append(_rec(estimator="bin8", scheme="-", value=lotv(g, m), **base))
            sq, _ = oof_sq_resid(z, m, "pair", des.pair_of_row, des.source_of_row)
            if sq is not None:
                out.append(_rec(estimator="rf", scheme="pair", value=float(sq.mean()),
                                oof_r2=float(1 - sq.mean() / m.var()), **base))
    return out


def exp_coherent_restrict(reps: int, sub_sizes, seed0: int = 6000):
    """E2c: as E2b but the sub-strata are CHEMICALLY COHERENT, as the real map's strata are.

    A stratum is grown from a seed pair by nearest-neighbour in the pair PC space, so its rows
    occupy one region of z*.  Validity is unaffected (the selection reads no label), but the
    regressor's approximation error is spatially structured, so a coherent stratum can sit
    systematically in a region where rhat is bad -- which a random pair set averages away."""
    out = []
    ratio, smooth_frac = 0.10, 0.6
    for rep in range(reps):
        rng = np.random.default_rng(seed0 + rep)
        des = build_design(rng, n_rows=REAL_N_ROWS)
        b_true = ratio * VAR_M_TARGET
        mu_scale = np.sqrt((1 - ratio) * VAR_M_TARGET)
        mu, g = make_mean_and_closure(des, rng, smooth_frac, mu_scale)
        m, _tg, cond_var_row = draw_labels(des, rng, mu, b_true, 0.3, 0.2, 0.5)
        sq_by_scheme = {}
        for scheme in ("pair", "source"):
            sq, _ = oof_sq_resid(des.zstar, m, scheme, des.pair_of_row, des.source_of_row)
            sq_by_scheme[scheme] = sq
        pc = des.pc_pair
        n_pairs = pc.shape[0]
        for ns in sub_sizes:
            for k in range(4):
                seed_p = int(rng.integers(0, n_pairs))
                order = np.argsort(((pc - pc[seed_p]) ** 2).sum(1))
                rows = np.array([], int)
                for p in order:
                    rows = np.concatenate([rows, np.where(des.pair_of_row == p)[0]])
                    if len(rows) >= ns:
                        break
                if len(rows) < ns:
                    continue
                rows = rows[:ns]
                base = dict(exp="E2c", n_sub=int(ns), rep=rep, draw=k,
                            truth=float(cond_var_row[rows].mean()),
                            var_m=float(m[rows].var(ddof=1)))
                out.append(_rec(estimator="bin8", scheme="-", scope="global",
                                value=lotv(g[rows], m[rows]), **base))
                for scheme, sq in sq_by_scheme.items():
                    if sq is None:
                        continue
                    out.append(_rec(estimator="rf", scheme=scheme, scope="global",
                                    value=float(sq[rows].mean()), **base))
    return out


def exp_closure_quality(reps: int, kappas, seed0: int = 5000):
    """E5: the coarsening bins on g, so its tightness is bought with the CLOSURE's own quality.

    kappa is the misspecification amplitude of g; large kappa = a poor binning statistic.  The
    cross-fitted forest never sees g, so this axis moves only one of the two estimators."""
    out = []
    ratio, smooth_frac = 0.10, 0.6
    for ki, kap in enumerate(kappas):
        for rep in range(reps):
            rng = np.random.default_rng(seed0 + 733 * ki + rep)
            des = build_design(rng, n_rows=REAL_N_ROWS)
            b_true = ratio * VAR_M_TARGET
            mu_scale = np.sqrt((1 - ratio) * VAR_M_TARGET)
            mu, g = make_mean_and_closure(des, rng, smooth_frac, mu_scale, kappa=kap)
            m, truth, _ = draw_labels(des, rng, mu, b_true, 0.3, 0.2, 0.5)
            base = dict(exp="E5", kappa=kap, rep=rep, n=len(m), truth=truth,
                        var_m=float(m.var(ddof=1)), mse=float(np.mean((m - g) ** 2)))
            out.append(_rec(estimator="bin8", scheme="-", value=lotv(g, m), **base))
            sq, _ = oof_sq_resid(des.zstar, m, "pair", des.pair_of_row, des.source_of_row)
            if sq is not None:
                out.append(_rec(estimator="rf", scheme="pair", value=float(sq.mean()),
                                oof_r2=float(1 - sq.mean() / m.var()), **base))
    return out


def exp_structure(reps: int, fracs, seed0: int = 4000):
    """E3: tightness against how much LEARNABLE structure z* carries."""
    out = []
    ratio = 0.10
    for fi, sf in enumerate(fracs):
        for rep in range(reps):
            rng = np.random.default_rng(seed0 + 811 * fi + rep)
            des = build_design(rng, n_rows=REAL_N_ROWS)
            b_true = ratio * VAR_M_TARGET
            mu_scale = np.sqrt((1 - ratio) * VAR_M_TARGET)
            mu, g = make_mean_and_closure(des, rng, sf, mu_scale)
            m, truth, _ = draw_labels(des, rng, mu, b_true, 0.3, 0.2, 0.5)
            base = dict(exp="E3", smooth_frac=sf, rep=rep, n=len(m), truth=truth,
                        var_m=float(m.var(ddof=1)), mse=float(np.mean((m - g) ** 2)))
            out.append(_rec(estimator="bin8", scheme="-", value=lotv(g, m), **base))
            for scheme in ("pair", "source"):
                sq, _ = oof_sq_resid(des.zstar, m, scheme, des.pair_of_row, des.source_of_row)
                if sq is not None:
                    out.append(_rec(estimator="rf", scheme=scheme, value=float(sq.mean()),
                                    oof_r2=float(1 - sq.mean() / m.var()), **base))
            sq, _ = oof_sq_resid(des.zstar, m, "pair", des.pair_of_row, des.source_of_row, "ridge")
            if sq is not None:
                out.append(_rec(estimator="ridge", scheme="pair", value=float(sq.mean()), **base))
    return out


# ================================================================================================
def summarise(recs):
    df = pd.DataFrame(recs)
    df["rel_err"] = (df["value"] - df["truth"]) / df["truth"]
    df["violation"] = df["value"] < df["truth"]
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", nargs="+", default=["E4", "E3", "E5", "E2", "E2b", "E2c", "E1"])
    ap.add_argument("--reps", type=int, default=16)
    ap.add_argument("--out-suffix", type=str, default="")
    args = ap.parse_args()

    global OUT
    if args.out_suffix:
        OUT = OUT.with_name(OUT.stem + args.out_suffix + OUT.suffix)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    all_recs: list[dict] = []
    done: list[str] = []
    t0 = time.time()

    def dump():
        OUT.write_text(json.dumps({"config": {"rf": RF_KWARGS, "n_splits": N_SPLITS,
                                              "n_bins": N_BINS, "ddof": DDOF,
                                              "reps": args.reps, "var_m_target": VAR_M_TARGET,
                                              "kappa": KAPPA},
                                   "experiments_done": done,
                                   "elapsed_s": round(time.time() - t0, 1),
                                   "records": all_recs}, indent=1))

    for e in args.exp:
        t = time.time()
        if e == "E4":
            recs = exp_validity(max(8, args.reps // 2), [1.0],
                                {"iid": (0, 0, 1), "pair_shock": (1, 0, 0), "source_shock": (0, 1, 0)})
            for r in recs:
                r["exp"] = "E4"
        elif e == "E3":
            recs = exp_structure(max(8, args.reps // 2), [0.0, 0.25, 0.5, 0.75, 1.0])
        elif e == "E5":
            recs = exp_closure_quality(max(8, args.reps // 2), [0.0, 0.3, 0.8, 1.5, 3.0])
        elif e == "E2":
            recs = exp_sample_size(max(8, args.reps // 2), [40, 57, 80, 120, 180, 260, 473, 960])
        elif e == "E2b":
            recs = exp_global_then_restrict(max(6, args.reps // 3), [40, 57, 70, 111, 182, 328, 473])
        elif e == "E2c":
            recs = exp_coherent_restrict(max(8, args.reps // 2), [40, 57, 70, 111, 182, 328])
        elif e == "E6":
            recs = exp_dimension(max(8, args.reps // 2), [1, 2, 4, 8, 16, None])
        elif e == "E1":
            recs = exp_validity(args.reps, [0.02, 0.10, 0.30, 0.60],
                                {"iid": (0, 0, 1), "pair_shock": (1, 0, 0),
                                 "source_shock": (0, 1, 0), "mixed": (0.3, 0.2, 0.5)})
        else:
            raise SystemExit(f"unknown experiment {e}")
        all_recs.extend(recs)
        done.append(e)
        dump()
        print(f"[{e}] {len(recs)} records in {time.time()-t:.0f}s (total {time.time()-t0:.0f}s)",
              flush=True)

    dump()
    print(f"[saved] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
