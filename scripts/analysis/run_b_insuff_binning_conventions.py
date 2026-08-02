#!/usr/bin/env python3
"""Binning-rule sensitivity of the LOTV upper bound on B_insuff, plus the Jensen
lower bound on B_clos on BOTH deposited sets.

Findings (3) and (4) of the round-4 audit:

  (3) "Eight equal-count bins" is under-specified.  n is not divisible by k on either
      set (60/8 = 7.5, 477/8 = 59.6), so several standard implementations of
      "equal-count" disagree on where the boundaries go.  This script enumerates the
      implementations, reports B_insuff^up and the margin MSE - 2*B_insuff^up under
      each, on the corner (n=60) and on the representative set (n=477), sweeping the
      bin count, and identifies which implementation the paper's own committed code
      (scripts/analysis/run_b_insuff_convention_audit.py:lotv, and the identical copies in
      run_b_insuff_{decomposition,estimator_grid,representative_audit}.py) uses.

  (4) Section 3.2 promises the Jensen constant-offset lower bound numbers in the SI
      tables appendix but only corner values appear there.  This computes E[m], E[g]
      and B_clos >= (E[m]-E[g])^2 on the 477-row keystone under both conventions and
      compares it against the LOTV upper bound on B_insuff.

Reads only the deposited row-level tables, so every number here is reproducible from
paper/si_tables/ without re-running any COSMO-SAC evaluation.

    PYTHONPATH=src ~/anaconda3/envs/tgnn-solv/bin/python \
        scripts/analysis/run_b_insuff_binning_conventions.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv"
COR = ROOT / "paper" / "si_tables" / "vt2005_matched_set_60.csv"
OUTDIR = ROOT / "results" / "b_insuff"
OUT = OUTDIR / "binning_conventions.json"
OUT_CSV = OUTDIR / "binning_conventions_sweep.csv"

BIN_GRID = (3, 4, 5, 6, 7, 8, 10, 12, 16, 20)


# --------------------------------------------------------------------------- #
# Binning implementations.  Each returns an integer label array of length n.
# --------------------------------------------------------------------------- #
def bins_paper_digitize(g: np.ndarray, k: int) -> np.ndarray:
    """A. THE PAPER'S OWN CODE, verbatim from run_b_insuff_convention_audit.py:lotv.

    Interpolated (numpy default 'linear') quantile edges on g, then np.digitize with
    right=False, so a value sitting exactly on an interior edge falls in the UPPER bin.
    Bin counts are only approximately equal.
    """
    q = np.quantile(g, np.linspace(0.0, 1.0, k + 1))
    q = q.copy()
    q[0] -= 1e-9
    q[-1] += 1e-9
    return np.digitize(g, q[1:-1])


def bins_quantile_ties_lower(g: np.ndarray, k: int) -> np.ndarray:
    """B. Same interpolated quantile edges, but ties assigned to the LOWER bin.

    i.e. half-open intervals closed on the right, (edge_{i}, edge_{i+1}] --- the
    convention pandas.cut/qcut use.  Identical to A whenever no observation lands
    exactly on an interior edge.
    """
    q = np.quantile(g, np.linspace(0.0, 1.0, k + 1))
    edges = q[1:-1]
    return np.searchsorted(edges, g, side="left")


def bins_qcut(g: np.ndarray, k: int) -> np.ndarray:
    """C. pandas.qcut(g, k, duplicates='drop') --- the off-the-shelf 'equal-count' call.

    Uses the same interpolated quantile edges but right-closed intervals with
    include_lowest, and silently collapses duplicate edges (fewer than k bins).
    """
    lab = pd.qcut(pd.Series(g), k, labels=False, duplicates="drop")
    return np.asarray(lab, dtype=int)


def bins_array_split(g: np.ndarray, k: int) -> np.ndarray:
    """D. np.array_split of the sorted order --- exactly equal counts, remainder spread
    over the LOW bins (sizes ceil(n/k) then floor(n/k)).  This is a rank rule, not a
    value rule: with ties in g it can split equal g values across two bins.
    """
    n = len(g)
    order = np.argsort(g, kind="stable")
    lab = np.empty(n, dtype=int)
    for b, chunk in enumerate(np.array_split(order, k)):
        lab[chunk] = b
    return lab


def bins_floor_remainder_last(g: np.ndarray, k: int) -> np.ndarray:
    """E. floor(n/k) per bin with the whole remainder dumped in the LAST bin.

    The naive hand-rolled 'equal-count' loop; on the corner this makes the top bin
    11 rows against 7 everywhere else.
    """
    n = len(g)
    order = np.argsort(g, kind="stable")
    w = n // k
    lab = np.empty(n, dtype=int)
    for b in range(k):
        lo = b * w
        hi = n if b == k - 1 else (b + 1) * w
        lab[order[lo:hi]] = b
    return lab


def bins_rank_floor(g: np.ndarray, k: int) -> np.ndarray:
    """F. floor(k * rank / n) --- equal counts with the remainder INTERLEAVED
    (sizes alternate ceil/floor rather than being front-loaded as in D).
    """
    n = len(g)
    order = np.argsort(g, kind="stable")
    lab = np.empty(n, dtype=int)
    lab[order] = (np.arange(n) * k) // n
    return lab


def bins_quantile_inverted_cdf(g: np.ndarray, k: int) -> np.ndarray:
    """G. Order-statistic ('inverted_cdf') quantile edges instead of interpolated ones,
    ties to the upper bin.  Edges are then observed values of g.
    """
    q = np.quantile(g, np.linspace(0.0, 1.0, k + 1), method="inverted_cdf")
    return np.searchsorted(q[1:-1], g, side="right")


IMPLS = {
    "A_paper_quantile_digitize_ties_upper": bins_paper_digitize,
    "B_quantile_edges_ties_lower": bins_quantile_ties_lower,
    "C_pandas_qcut_duplicates_drop": bins_qcut,
    "D_numpy_array_split_sorted": bins_array_split,
    "E_floor_nk_remainder_to_last": bins_floor_remainder_last,
    "F_rank_floor_k_rank_over_n": bins_rank_floor,
    "G_quantile_inverted_cdf": bins_quantile_inverted_cdf,
}


def lotv_from_labels(lab: np.ndarray, m: np.ndarray, ddof: int) -> float:
    """E[Var(m | bin)] with the paper's mass convention: a bin with <= ddof members
    contributes zero to the numerator while its rows stay in the denominator n."""
    tot = 0.0
    n = len(m)
    for b in np.unique(lab):
        mm = m[lab == b]
        if len(mm) > ddof:
            tot += (len(mm) / n) * float(mm.var(ddof=ddof))
    return tot


def bin_sizes(lab: np.ndarray) -> list[int]:
    return [int((lab == b).sum()) for b in np.unique(lab)]


def envelope(ms: np.ndarray, k: int, ddof: int = 1,
             size_lo: int = 1, size_hi: int | None = None) -> tuple[float, float]:
    """Exact min and max of E[Var(m | bin)] over EVERY contiguous partition of the
    g-sorted targets `ms` into exactly k parts whose sizes lie in [size_lo, size_hi]
    (exact DP, not a search).  Any binning implementation is one such partition, so a
    claimed value outside this interval cannot be produced by any rule at that k.
    """
    n = len(ms)
    size_hi = size_hi or n
    cs = np.concatenate([[0.0], np.cumsum(ms)])
    cs2 = np.concatenate([[0.0], np.cumsum(ms ** 2)])

    def cost(i: int, j: int) -> float:
        L = j - i
        if L <= ddof:
            return 0.0
        ss = (cs2[j] - cs2[i]) - (cs[j] - cs[i]) ** 2 / L
        return ss * L / (L - ddof)

    INF = float("inf")
    lo_dp = np.full((k + 1, n + 1), INF)
    hi_dp = np.full((k + 1, n + 1), -INF)
    lo_dp[0, 0] = hi_dp[0, 0] = 0.0
    for b in range(1, k + 1):
        for j in range(1, n + 1):
            for i in range(max(0, j - size_hi), j - size_lo + 1):
                if lo_dp[b - 1, i] == INF:
                    continue
                c = cost(i, j)
                lo_dp[b, j] = min(lo_dp[b, j], lo_dp[b - 1, i] + c)
                hi_dp[b, j] = max(hi_dp[b, j], hi_dp[b - 1, i] + c)
    return float(lo_dp[k, n] / n), float(hi_dp[k, n] / n)


# --------------------------------------------------------------------------- #
def main() -> int:
    rep = pd.read_csv(REP)
    cor = pd.read_csv(COR)

    sets = {
        "representative_477": {
            "m": rep["m_ln_gamma_inf"].to_numpy(float),
            "res": rep["g_2002_res"].to_numpy(float),
            "full": rep["g_2002_full"].to_numpy(float),
        },
        "corner_60": {
            "m": cor["m"].to_numpy(float),
            "res": cor["g_res"].to_numpy(float),
            "full": cor["g_full"].to_numpy(float),
        },
    }

    out: dict = {
        "paper_implementation": "A_paper_quantile_digitize_ties_upper",
        "paper_implementation_source": [
            "scripts/analysis/run_b_insuff_convention_audit.py:lotv",
            "scripts/analysis/run_b_insuff_estimator_grid.py:lotv",
            "scripts/analysis/run_b_insuff_representative_audit.py:lotv",
            "scripts/analysis/run_b_insuff_decomposition.py:lotv_binning (ddof=0 only)",
        ],
        "sets": {},
    }

    rows = []
    for sname, d in sets.items():
        m = d["m"]
        n = len(m)
        blk: dict = {"n": n, "var_m_ML": round(float(m.var(ddof=0)), 6),
                     "var_m_Bessel": round(float(m.var(ddof=1)), 6),
                     "conventions": {}}
        for conv in ("res", "full"):
            g = d[conv]
            mse = float(np.mean((m - g) ** 2))
            n_dup = int(n - len(np.unique(g)))
            cblk: dict = {
                "mse": round(mse, 6),
                "n_exact_ties_in_g": n_dup,
                "E_m": round(float(m.mean()), 6),
                "E_g": round(float(g.mean()), 6),
                "jensen_lb_B_clos": round(float((m.mean() - g.mean()) ** 2), 6),
                "by_bins": {},
            }
            for k in BIN_GRID:
                cell = {}
                for iname, fn in IMPLS.items():
                    lab = fn(g, k)
                    sizes = bin_sizes(lab)
                    e = {}
                    for ddof, dlab in ((1, "Bessel"), (0, "ML")):
                        b = lotv_from_labels(lab, m, ddof)
                        e[dlab] = {"b_insuff_up": round(b, 6),
                                   "margin": round(mse - 2 * b, 6)}
                        rows.append({
                            "set": sname, "convention": conv, "bins": k,
                            "impl": iname, "variance": dlab,
                            "n_bins_realised": len(sizes),
                            "min_bin": min(sizes), "max_bin": max(sizes),
                            "b_insuff_up": round(b, 6),
                            "mse": round(mse, 6),
                            "margin": round(mse - 2 * b, 6),
                        })
                    e["n_bins_realised"] = len(sizes)
                    e["bin_sizes"] = sizes
                    cell[iname] = e
                bvals = [cell[i]["Bessel"]["b_insuff_up"] for i in IMPLS]
                cell["_spread_Bessel"] = {
                    "min": round(min(bvals), 6), "max": round(max(bvals), 6),
                    "spread": round(max(bvals) - min(bvals), 6),
                    "paper_is_max": bool(
                        cell["A_paper_quantile_digitize_ties_upper"]["Bessel"]["b_insuff_up"]
                        == max(bvals)),
                    "n_distinct_values": len({round(v, 9) for v in bvals}),
                }
                # exact envelope over every contiguous k-partition, and over the
                # strictly equal-count ones (all bin sizes in {floor(n/k), ceil(n/k)})
                ms = m[np.argsort(g, kind="stable")]
                a_lo, a_hi = envelope(ms, k)
                s_lo, s_hi = n // k, -(-n // k)
                e_lo, e_hi = envelope(ms, k, size_lo=s_lo, size_hi=s_hi)
                cell["_envelope_Bessel"] = {
                    "any_contiguous_partition": {
                        "b_min": round(a_lo, 6), "b_max": round(a_hi, 6),
                        "margin_min": round(mse - 2 * a_hi, 6),
                        "margin_max": round(mse - 2 * a_lo, 6)},
                    "strictly_equal_count": {
                        "allowed_bin_sizes": [s_lo, s_hi],
                        "b_min": round(e_lo, 6), "b_max": round(e_hi, 6),
                        "margin_min": round(mse - 2 * e_hi, 6),
                        "margin_max": round(mse - 2 * e_lo, 6),
                        "paper_value": cell["A_paper_quantile_digitize_ties_upper"]["Bessel"]["b_insuff_up"],
                        "paper_is_the_max_ie_least_favourable": bool(
                            abs(cell["A_paper_quantile_digitize_ties_upper"]["Bessel"]["b_insuff_up"]
                                - e_hi) < 1e-9),
                        "margin_sign_determined_by_equal_count_rule": bool(
                            (mse - 2 * e_hi) * (mse - 2 * e_lo) > 0)},
                }
                cblk["by_bins"][k] = cell
            blk["conventions"][conv] = cblk
        out["sets"][sname] = blk

    # ------------------------------------------------------------------ Jensen (4)
    jen = {}
    for sname, d in sets.items():
        m = d["m"]
        e = {"E_m": round(float(m.mean()), 6), "n": len(m)}
        b_min_conv = min(lotv_from_labels(bins_paper_digitize(d[c], 8), m, 1)
                         for c in ("res", "full"))
        for conv in ("res", "full"):
            g = d[conv]
            lb = float((m.mean() - g.mean()) ** 2)
            b8 = lotv_from_labels(bins_paper_digitize(g, 8), m, 1)
            mse = float(np.mean((m - g) ** 2))
            e[conv] = {
                "E_g": round(float(g.mean()), 6),
                "mean_gap_E_m_minus_E_g": round(float(m.mean() - g.mean()), 6),
                "jensen_lb_B_clos": round(lb, 6),
                "mse": round(mse, 6),
                "lotv_ub_B_insuff_8bins_Bessel_paper_impl": round(b8, 6),
                # does the assumption-free lower bound clear the LOTV upper bound?
                "jensen_separates_same_convention": bool(lb > b8),
                "jensen_separates_vs_min_over_conventions_bound": bool(lb > b_min_conv),
                # the bound the paper actually headlines, for contrast
                "lotv_implied_lb_B_clos_mse_minus_binsuf": round(mse - b8, 6),
                "jensen_is_dominated_by_lotv_implied_lb": bool(lb < mse - b8),
            }
        e["min_over_conventions_lotv_ub"] = round(b_min_conv, 6)
        jen[sname] = e
    out["jensen"] = jen

    OUTDIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    OUT.write_text(json.dumps(out, indent=2))

    # ------------------------------------------------------------------ console
    print("=" * 78)
    print("(3) BINNING-RULE SWEEP -- residual-only convention, Bessel variance")
    print("=" * 78)
    for sname in sets:
        for k in (7, 8):
            cell = out["sets"][sname]["conventions"]["res"]["by_bins"][k]
            mse = out["sets"][sname]["conventions"]["res"]["mse"]
            print(f"\n{sname}, k={k}, MSE_res={mse:.4f}")
            for iname in IMPLS:
                e = cell[iname]
                print(f"   {iname:42s} B={e['Bessel']['b_insuff_up']:.4f} "
                      f"margin={e['Bessel']['margin']:+.4f} "
                      f"bins={e['n_bins_realised']} sizes={e['bin_sizes']}")
            print(f"   spread(Bessel) over the 7 named impls = {cell['_spread_Bessel']}")
            print(f"   exact envelope = {json.dumps(cell['_envelope_Bessel'])}")

    print("\n" + "=" * 78)
    print("(4) JENSEN")
    print("=" * 78)
    print(json.dumps(jen, indent=2))
    print(f"\n[saved] {OUT}\n[saved] {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
