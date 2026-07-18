#!/usr/bin/env python3
"""Pre-committed analysis of the 2x2 sigma-substitution test (review item #1).

Consumes the four condition CSVs written by do_paradox_2x2 (via export_checkpoint_predictions.py):
    cond_both_learned.csv    (a) learned sigma both channels          (--sigma-oracle-side none)
    cond_both_reference.csv  (b) reference sigma both channels        (--sigma-oracle-side both)
    cond_ref_solvent.csv     (c) reference solvent + LEARNED solute   (--sigma-oracle-side solvent)
    cond_ref_solute.csv      (d) reference solute  + LEARNED solvent  (--sigma-oracle-side solute)

Decision rule is FIXED in reports/PREDICTION_paradox_2x2_channel_2026-07-18.md and is NOT recomputed
here -- this script only evaluates the pre-registered statistic. On the both-reference subset (solute
AND solvent in VT-2005 -- the only rows where all four conditions are defined):

    MISMATCH = mean[MAE(c), MAE(d)] - mean[MAE(a), MAE(b)]

    >= +0.20  -> H_mixing (co-adaptation): the paradox is learned/reference INCONSISTENCY -> the
                 solubility headline is wrong and must be rewritten.
    <  +0.10  -> H_chemistry: mixing is NOT the cause; the +0.42 solvent-only effect is solute
                 chemistry (drug-like = high-B_closure), both-reference~0 = low-B_closure regime;
                 paradox real, headline survives with a scope caveat.
    [0.10,0.20) -> intermediate: partial mixing, report both channels jointly.

Design discipline (the thread's rule): SAME molecules across all four conditions (kills the
design-vs-chemistry hiding place). The four CSVs are the identical test set in the identical loader
order, so they are aligned BY POSITION after the has_solubility filter -- NOT merged on pair_key
(a pair_key merge exploded 5571->32129 on duplicate keys in an earlier run). Alignment is asserted
on solute/solvent SMILES; a mismatch is a hard error, never a silent reindex.

Usage:
    python scripts/analysis/run_paradox_2x2_analysis.py --dir results/paradox_2x2
    python scripts/analysis/run_paradox_2x2_analysis.py --selftest   # known-answer fixture, no data
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

COND_FILES = {
    "a_both_learned": "cond_both_learned.csv",
    "b_both_reference": "cond_both_reference.csv",
    "c_ref_solvent": "cond_ref_solvent.csv",
    "d_ref_solute": "cond_ref_solute.csv",
}
# Pre-registered thresholds (do not edit without re-registering).
T_MIXING = 0.20
T_CHEMISTRY = 0.10


def _as_bool(s: pd.Series) -> np.ndarray:
    """Robustly coerce a column to bool. pandas to_csv writes Python bools as the STRINGS
    'True'/'False'; read_csv usually infers bool dtype, but if a column comes back as object,
    ``.astype(bool)`` maps the non-empty string 'False' to True -- a silent corruption. Map
    explicitly instead."""
    if s.dtype == bool:
        return s.to_numpy()
    if s.dtype == object:
        m = {"True": True, "False": False, "true": True, "false": False, "1": True, "0": False,
             True: True, False: False}
        out = s.map(m)
        if out.isna().any():
            bad = sorted(set(s[out.isna()].astype(str)))[:5]
            raise SystemExit(f"un-coercible boolean values {bad} in a mask/flag column")
        return out.to_numpy(dtype=bool)
    arr = s.to_numpy(dtype=float)  # numeric 0/1
    if not np.isfinite(arr).all():
        raise SystemExit("NaN/inf in a numeric mask/flag column (np.nan.astype(bool) is silently True)")
    return arr.astype(bool)


def _load_supervised(path: Path) -> pd.DataFrame:
    """Load one condition CSV, keep supervised rows, reset to positional index."""
    df = pd.read_csv(path)
    for col in ("has_solubility", "sigma_oracle_mask_solute", "sigma_oracle_mask_solvent"):
        if col in df.columns:
            df[col] = _as_bool(df[col])
    df = df[df["has_solubility"]].reset_index(drop=True)
    return df


def _assert_aligned(frames: dict[str, pd.DataFrame]) -> None:
    """All four conditions must be the same molecules in the same order (position alignment)."""
    ref_name, ref = next(iter(frames.items()))
    n = len(ref)
    for name, df in frames.items():
        if len(df) != n:
            raise SystemExit(
                f"row-count mismatch: {name} has {len(df)} supervised rows, {ref_name} has {n}. "
                "The four conditions must be the identical test set; do NOT proceed."
            )
    for name, df in frames.items():
        if name == ref_name:
            continue
        for col in ("solute_smiles", "solvent_smiles"):
            if not (df[col].values == ref[col].values).all():
                bad = int((df[col].values != ref[col].values).sum())
                raise SystemExit(
                    f"position misalignment: {name}.{col} differs from {ref_name}.{col} in {bad}/{n} "
                    "rows. The conditions are not row-aligned; refusing to compute MISMATCH."
                )


def _both_reference_mask(b: pd.DataFrame) -> np.ndarray:
    """Rows where the reference substitution actually hit BOTH channels (solute AND solvent matched
    to VT-2005). Taken from the both_reference CSV's own matcher masks -- the faithful definition of
    'all four conditions defined', with no rdkit re-canonicalization that could disagree with the
    model's own SMILES matching."""
    if "sigma_oracle_mask_solute" not in b or "sigma_oracle_mask_solvent" not in b:
        raise SystemExit("both_reference CSV lacks sigma_oracle_mask_* columns; wrong --sigma-oracle-side?")
    ms = b["sigma_oracle_mask_solute"].astype(bool).to_numpy()
    mv = b["sigma_oracle_mask_solvent"].astype(bool).to_numpy()
    return ms & mv


def _mae(df: pd.DataFrame, mask: np.ndarray) -> float:
    return float(df.loc[mask, "abs_error"].to_numpy(dtype=float).mean())


def _cluster_bootstrap_mismatch(frames: dict[str, pd.DataFrame], mask: np.ndarray,
                                cluster_key: pd.Series, n_boot: int = 2000, seed: int = 0) -> dict:
    """Bootstrap MISMATCH by resampling SOLUTE clusters (scaffold-correlated errors -> cluster, not
    per-row). Deterministic (fixed seed)."""
    a = frames["a_both_learned"].loc[mask, "abs_error"].to_numpy(float)
    b = frames["b_both_reference"].loc[mask, "abs_error"].to_numpy(float)
    c = frames["c_ref_solvent"].loc[mask, "abs_error"].to_numpy(float)
    d = frames["d_ref_solute"].loc[mask, "abs_error"].to_numpy(float)
    clusters = cluster_key[mask].to_numpy()
    uniq = np.unique(clusters)
    idx_by_cluster = {u: np.where(clusters == u)[0] for u in uniq}
    rng = np.random.default_rng(seed)
    stats = np.empty(n_boot)
    for k in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        rows = np.concatenate([idx_by_cluster[u] for u in pick])
        stats[k] = 0.5 * (c[rows].mean() + d[rows].mean()) - 0.5 * (a[rows].mean() + b[rows].mean())
    lo, hi = np.percentile(stats, [5, 95])
    return {"mismatch_boot_mean": float(stats.mean()), "ci90": [float(lo), float(hi)],
            "p_ge_0.2": float((stats >= T_MIXING).mean()), "p_le_0.1": float((stats <= T_CHEMISTRY).mean()),
            "n_clusters": int(len(uniq))}


TINY_N = 30  # pre-registration expects ~198/seed; below this the verdict is fragile


def _verdict(mismatch: float, underpowered: bool, n_bothref: int, n_nonfinite_dropped: int) -> str:
    """Gate the categorical verdict. A non-finite MISMATCH or an underpowered checkpoint must NOT
    route to H_mixing/H_chemistry -- those are confident-wrong reads of a divergent or dead run."""
    if not np.isfinite(mismatch):
        return ("INCONCLUSIVE: non-finite MISMATCH (divergent checkpoint / NaN or inf abs_error even "
                "after dropping non-finite rows) -- do not interpret")
    if underpowered:
        return ("INCONCLUSIVE: underpowered -- this checkpoint does not reproduce the paradox "
                "(overall oracle-minus-learned < 0.15); a null MISMATCH here is NOT H_chemistry")
    if mismatch >= T_MIXING:
        base = "H_mixing (co-adaptation): headline must be rewritten"
    elif mismatch < T_CHEMISTRY:
        base = "H_chemistry: paradox real, headline survives with scope caveat"
    else:
        base = "intermediate: partial mixing, report both channels jointly"
    flags = []
    if n_bothref < TINY_N:
        flags.append(f"FRAGILE: n_bothref={n_bothref} << pre-registered ~198")
    if n_nonfinite_dropped > 0:
        flags.append(f"{n_nonfinite_dropped} non-finite rows dropped")
    return base + (f"  [{'; '.join(flags)}]" if flags else "")


def analyse(frames: dict[str, pd.DataFrame]) -> dict:
    _assert_aligned(frames)
    b = frames["b_both_reference"]
    mask_bothref = _both_reference_mask(b)
    if int(mask_bothref.sum()) == 0:
        raise SystemExit("both-reference subset is EMPTY (no row had both channels matched to VT-2005). "
                         "Check the sigma artifact path and the oracle side; refusing to report a verdict.")

    # Finiteness: a non-converged SLE row (NaN/inf ln_x2 -> abs_error) must not silently poison the
    # MAE. NaN routes _verdict to 'intermediate'; +inf routes it to 'H_mixing' -- both confident-wrong.
    # Require a row finite in ALL FOUR conditions to be comparable (same-molecule discipline).
    finite_all = np.ones(len(b), dtype=bool)
    for v in frames.values():
        finite_all &= np.isfinite(v["abs_error"].to_numpy(dtype=float))
    n_nonfinite_dropped = int((mask_bothref & ~finite_all).sum())
    mask_bothref = mask_bothref & finite_all
    n_bothref = int(mask_bothref.sum())
    if n_bothref == 0:
        raise SystemExit("both-reference subset is EMPTY after dropping non-finite rows -- the checkpoint "
                         "diverged on every comparable molecule. Refusing to report a verdict.")

    mae = {k: _mae(v, mask_bothref) for k, v in frames.items()}
    mismatch = 0.5 * (mae["c_ref_solvent"] + mae["d_ref_solute"]) - 0.5 * (mae["a_both_learned"] + mae["b_both_reference"])
    # Sanity: the both-reference paradox itself (oracle - learned), expected ~+0.017 from the channel split.
    bothref_paradox = mae["b_both_reference"] - mae["a_both_learned"]

    # Secondary read: condition (c) on this EASY subset vs the solvent-only subset (learned solute +
    # reference solvent on DRUG-LIKE solutes = the +0.42 regime). If (c)~0 here but +0.42 there, the
    # difference is solute hardness (chemistry), isolating (ii) from (i).
    ms = b["sigma_oracle_mask_solute"].astype(bool).to_numpy()
    mv = b["sigma_oracle_mask_solvent"].astype(bool).to_numpy()
    mask_solvent_only = mv & (~ms) & finite_all
    sec = {}
    if mask_solvent_only.sum() > 0:
        # on solvent-only rows the reference substitution lands only on the solvent -> that is exactly
        # what cond_ref_solvent computed there; the paradox vs both_learned:
        sec = {
            "solvent_only_n": int(mask_solvent_only.sum()),
            "solvent_only_paradox_ref_solvent_minus_learned": float(
                _mae(frames["c_ref_solvent"], mask_solvent_only) - _mae(frames["a_both_learned"], mask_solvent_only)),
            "bothref_c_paradox_ref_solvent_minus_learned": float(
                mae["c_ref_solvent"] - mae["a_both_learned"]),
        }

    # Power check: does THIS checkpoint even reproduce the paradox? The 2x2 endtoend was trained for
    # only 15 SLE epochs (vs the converged e5 run, overall paradox ~+0.39). If the overall
    # oracle-minus-learned paradox is small, a null MISMATCH is UNDERPOWERED, not evidence for
    # H_chemistry -- surface that so a dead checkpoint is never read as a resolved verdict.
    full_learned = frames["a_both_learned"]["abs_error"].to_numpy(float)[finite_all].mean()
    full_oracle = frames["b_both_reference"]["abs_error"].to_numpy(float)[finite_all].mean()
    overall_paradox = float(full_oracle - full_learned)
    underpowered = overall_paradox < 0.15
    solvent_only_paradox = sec.get("solvent_only_paradox_ref_solvent_minus_learned")

    boot = _cluster_bootstrap_mismatch(frames, mask_bothref, b["solute_smiles"])
    return {
        "n_supervised_total": int(len(b)),
        "n_both_reference": n_bothref,
        "n_nonfinite_dropped": n_nonfinite_dropped,
        "n_unique_solutes_bothref": int(b.loc[mask_bothref, "solute_smiles"].nunique()),
        "mae_by_condition": mae,
        "MISMATCH": float(mismatch),
        "bothref_paradox_oracle_minus_learned": float(bothref_paradox),
        "verdict": _verdict(mismatch, underpowered, n_bothref, n_nonfinite_dropped),
        "power_check": {
            "overall_paradox_oracle_minus_learned": overall_paradox,
            "solvent_only_paradox": solvent_only_paradox,
            "underpowered": bool(underpowered),
            "note": ("overall paradox < 0.15 -> this 15-epoch checkpoint does not reproduce the e5 "
                     "paradox (~+0.39); a null MISMATCH here is UNDERPOWERED, not H_chemistry. "
                     "Retrain longer before trusting a null.") if underpowered else
                    "checkpoint reproduces a non-trivial paradox; the MISMATCH split is interpretable.",
        },
        "bootstrap": boot,
        "secondary": sec,
        "thresholds": {"mixing_ge": T_MIXING, "chemistry_lt": T_CHEMISTRY},
        "caveat": "single-seed run (seed 42); the pre-registration envisioned seeds 42+43. The 2x2 "
                  "endtoend checkpoint is trained for 15 SLE epochs (not converged), so absolute MAEs "
                  "and the both-reference paradox may be attenuated vs e5; the MISMATCH is same-molecule "
                  "and relative, hence more robust. Uncertainty is carried by the solute-cluster "
                  "bootstrap CI, not by seed variance. Read the verdict jointly with power_check.",
    }


# ---------------------------------------------------------------------------- #
def _selftest() -> None:
    """Known-answer fixtures. 5 rows: both-reference subset = rows 0,1,2 (solute&solvent matched);
    row 3 solvent-only; row 4 neither. Non-subset rows 3,4 make mean(b)>mean(a) so overall_paradox
    exceeds the 0.15 power floor (else the fixtures would trip the underpowered gate).
        a=[1,1,1] b=[1,1,1] c=[2,2,2] d=[2,2,2] on the subset -> MISMATCH=0.5(2+2)-0.5(1+1)=+1.0.
    Covers: exact MISMATCH, alignment scramble, empty subset, solvent-only read, H_chemistry routing,
    the underpowered gate, NaN/inf dropping, and the verdict-level finiteness guard.
    """
    def frame(errs, ms, mv, sol=None, slv=None):
        n = len(errs)
        return pd.DataFrame({
            "solute_smiles": sol or [f"S{i}" for i in range(n)],
            "solvent_smiles": slv or [f"V{i}" for i in range(n)],
            "has_solubility": [True] * n,
            "abs_error": errs,
            "sigma_oracle_mask_solute": ms,
            "sigma_oracle_mask_solvent": mv,
        })
    MS = [True, True, True, False, False]
    MV = [True, True, True, True, False]
    # rows 3,4: b>a so overall_paradox=(4.0-3.4)=+0.6 -> powered.
    frames = {
        "a_both_learned":  frame([1, 1, 1, 5, 9], [False]*5, [False]*5),
        "b_both_reference": frame([1, 1, 1, 6, 11], MS, MV),
        "c_ref_solvent":   frame([2, 2, 2, 6, 9], [False]*5, MV),
        "d_ref_solute":    frame([2, 2, 2, 5, 9], MS, [False]*5),
    }
    res = analyse(frames)
    assert res["n_both_reference"] == 3, res["n_both_reference"]
    assert abs(res["MISMATCH"] - 1.0) < 1e-9, res["MISMATCH"]
    assert res["verdict"].startswith("H_mixing"), res["verdict"]
    assert "FRAGILE" in res["verdict"], res["verdict"]           # n=3 << 198
    assert res["power_check"]["underpowered"] is False, res["power_check"]
    assert abs(res["bothref_paradox_oracle_minus_learned"] - 0.0) < 1e-9
    assert res["secondary"]["solvent_only_n"] == 1
    assert abs(res["secondary"]["solvent_only_paradox_ref_solvent_minus_learned"] - 1.0) < 1e-9

    # alignment guard must fire on a scrambled SMILES order
    bad = {k: v.copy() for k, v in frames.items()}
    bad["c_ref_solvent"]["solute_smiles"] = ["X", "S1", "S2", "S3", "S4"]
    try:
        analyse(bad); raise AssertionError("alignment guard did NOT fire")
    except SystemExit:
        pass

    # empty subset must error
    empty = {k: v.copy() for k, v in frames.items()}
    empty["b_both_reference"]["sigma_oracle_mask_solute"] = [False]*5
    try:
        analyse(empty); raise AssertionError("empty-subset guard did NOT fire")
    except SystemExit:
        pass

    # H_chemistry branch (powered): c,d ~ a,b on the subset
    chem = {
        "a_both_learned":  frame([1, 1, 1, 5, 9], [False]*5, [False]*5),
        "b_both_reference": frame([1, 1, 1, 6, 11], MS, MV),
        "c_ref_solvent":   frame([1.02, 1.0, 1.03, 6, 9], [False]*5, MV),
        "d_ref_solute":    frame([1.0, 1.01, 1.0, 5, 9], MS, [False]*5),
    }
    rc = analyse(chem)
    assert rc["MISMATCH"] < T_CHEMISTRY and rc["verdict"].startswith("H_chemistry"), rc["verdict"]

    # underpowered gate: overall_paradox=0 -> INCONCLUSIVE even though MISMATCH is a clean 0
    flat = {
        "a_both_learned":  frame([1, 1, 1, 5, 9], [False]*5, [False]*5),
        "b_both_reference": frame([1, 1, 1, 5, 9], MS, MV),
        "c_ref_solvent":   frame([1, 1, 1, 5, 9], [False]*5, MV),
        "d_ref_solute":    frame([1, 1, 1, 5, 9], MS, [False]*5),
    }
    ru = analyse(flat)
    assert ru["power_check"]["underpowered"] is True
    assert ru["verdict"].startswith("INCONCLUSIVE: underpowered"), ru["verdict"]

    # finiteness: inf in c row0 and NaN in d row1 -> those rows dropped, MISMATCH stays finite
    nf = {
        "a_both_learned":  frame([1, 1, 1, 5, 9], [False]*5, [False]*5),
        "b_both_reference": frame([1, 1, 1, 6, 11], MS, MV),
        "c_ref_solvent":   frame([float("inf"), 2, 2, 6, 9], [False]*5, MV),
        "d_ref_solute":    frame([2, float("nan"), 2, 5, 9], MS, [False]*5),
    }
    rn = analyse(nf)
    assert rn["n_nonfinite_dropped"] == 2, rn["n_nonfinite_dropped"]
    assert rn["n_both_reference"] == 1 and abs(rn["MISMATCH"] - 1.0) < 1e-9, rn
    assert np.isfinite(rn["MISMATCH"]) and "non-finite" in rn["verdict"], rn["verdict"]

    # all-subset-nonfinite -> empty-after-drop error
    dead = {k: v.copy() for k, v in nf.items()}
    dead["c_ref_solvent"]["abs_error"] = [float("inf")] * 5
    try:
        analyse(dead); raise AssertionError("empty-after-drop guard did NOT fire")
    except SystemExit:
        pass

    # verdict-level finiteness guard: inf/NaN MISMATCH must NOT route to H_mixing/intermediate
    assert _verdict(float("inf"), False, 100, 0).startswith("INCONCLUSIVE: non-finite")
    assert _verdict(float("nan"), False, 100, 0).startswith("INCONCLUSIVE: non-finite")

    # string/numeric-bool coercion: the CSV-round-trip trap
    assert list(_as_bool(pd.Series(["True", "False", "True"]))) == [True, False, True]
    assert list(_as_bool(pd.Series([True, False], dtype=bool))) == [True, False]
    assert list(_as_bool(pd.Series([1, 0, 1]))) == [True, False, True]
    for badvals in (pd.Series(["yes", "no"]), pd.Series([1.0, float("nan")])):
        try:
            _as_bool(badvals); raise AssertionError(f"_as_bool accepted {list(badvals)}")
        except SystemExit:
            pass
    print("SELFTEST PASS: MISMATCH exact; alignment/empty/underpowered/finiteness/bool guards all fire; "
          "H_mixing/H_chemistry/INCONCLUSIVE branches route correctly.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, help="directory holding the four cond_*.csv files")
    ap.add_argument("--out", type=Path, default=None, help="write the result JSON here")
    ap.add_argument("--selftest", action="store_true", help="run the known-answer fixture and exit")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return
    if not args.dir:
        ap.error("--dir is required unless --selftest")

    frames = {}
    for key, fname in COND_FILES.items():
        p = args.dir / fname
        if not p.exists():
            raise SystemExit(f"missing condition file: {p}")
        frames[key] = _load_supervised(p)

    res = analyse(frames)
    print(json.dumps(res, indent=2))
    print("\n" + "=" * 72)
    print(f"MISMATCH = {res['MISMATCH']:+.3f}   (mixing>=+{T_MIXING}, chemistry<+{T_CHEMISTRY})")
    print(f"  bootstrap 90% CI: {res['bootstrap']['ci90']}   n_bothref={res['n_both_reference']}")
    print(f"VERDICT: {res['verdict']}")
    print("=" * 72)
    out = args.out or (args.dir / "paradox_2x2_analysis.json")
    out.write_text(json.dumps(res, indent=2))
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
