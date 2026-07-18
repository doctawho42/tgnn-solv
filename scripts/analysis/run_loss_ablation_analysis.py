#!/usr/bin/env python3
"""Pre-committed analysis of the minimal-loss ablation (does the paradox need the ~30-term objective?).

Compares the compensating-surrogate paradox between the FULL-loss run (do_paradox_2x2's cond_both_learned
/ cond_both_reference) and the MINIMAL-loss run (do_loss_ablation's same two conditions). Decision rule is
FIXED in reports/PREDICTION_loss_ablation_2026-07-18.md and only evaluated here.

    PARADOX = MAE(both_reference) - MAE(both_learned)   on all supervised finite rows
              (POSITIVE = learned sigma beats the true reference => paradox present; the `both` oracle
               substitutes the solvent for ~99% of rows and the solute for ~5%, so this is the
               solvent-dominated overall paradox where the effect lives, per the channel split).

    H_intrinsic     : PARADOX_min > 0 and within 0.10 MAE of PARADOX_full and > 0.5*PARADOX_full
                      -> surrogate is intrinsic to closure+latent, loss zoo is convenience.
    H_loss_dependent: PARADOX_min < 0.5*PARADOX_full or flips negative
                      -> a dropped term was load-bearing; qualify the mechanism claim.

Reuses the adversarially-verified helpers from run_paradox_2x2_analysis (bool coercion, supervised load,
both-reference mask). Run locally after pulling both result dirs off the VM.

Usage:
    python scripts/analysis/run_loss_ablation_analysis.py --full-dir results/paradox_2x2 \
        --min-dir results/loss_ablation --min-base-val 1.95
    python scripts/analysis/run_loss_ablation_analysis.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_paradox_2x2_analysis import _load_supervised, _both_reference_mask  # noqa: E402

LEARNED = "cond_both_learned.csv"
REFERENCE = "cond_both_reference.csv"


def _paradox(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    """MAE(reference b) - MAE(learned a) on all supervised rows finite in BOTH conditions, plus the
    both-reference-subset paradox (secondary). a,b are position-aligned (same test set, same order)."""
    if len(a) != len(b):
        raise SystemExit(f"learned/reference row-count mismatch ({len(a)} vs {len(b)}): not the same test set")
    if not (a["solute_smiles"].values == b["solute_smiles"].values).all():
        raise SystemExit("learned/reference SMILES misaligned; refusing to compute a paradox")
    ea = a["abs_error"].to_numpy(float)
    eb = b["abs_error"].to_numpy(float)
    finite = np.isfinite(ea) & np.isfinite(eb)
    n_drop = int((~finite).sum())
    overall = float(eb[finite].mean() - ea[finite].mean())
    # both-reference subset (should be ~0 -- consistency check)
    mask_br = _both_reference_mask(b) & finite
    subset = float(eb[mask_br].mean() - ea[mask_br].mean()) if mask_br.sum() > 0 else None
    return {"paradox_overall": overall, "paradox_both_reference_subset": subset,
            "n_supervised_finite": int(finite.sum()), "n_nonfinite_dropped": n_drop,
            "mae_learned": float(ea[finite].mean()), "mae_reference": float(eb[finite].mean()),
            "n_both_reference_subset": int(mask_br.sum())}


def _cluster_bootstrap_paradox(a: pd.DataFrame, b: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> dict:
    ea = a["abs_error"].to_numpy(float)
    eb = b["abs_error"].to_numpy(float)
    finite = np.isfinite(ea) & np.isfinite(eb)
    ea, eb = ea[finite], eb[finite]
    clusters = a["solute_smiles"].to_numpy()[finite]
    uniq = np.unique(clusters)
    idx = {u: np.where(clusters == u)[0] for u in uniq}
    rng = np.random.default_rng(seed)
    stats = np.empty(n_boot)
    for k in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        rows = np.concatenate([idx[u] for u in pick])
        stats[k] = eb[rows].mean() - ea[rows].mean()
    lo, hi = np.percentile(stats, [5, 95])
    return {"ci90": [float(lo), float(hi)], "p_gt_0": float((stats > 0).mean())}


def _verdict(p_full: float, p_min: float) -> str:
    if not (np.isfinite(p_full) and np.isfinite(p_min)):
        return "INCONCLUSIVE: non-finite paradox"
    if p_full <= 0.05:
        return ("INCONCLUSIVE: the FULL-loss run does not itself show a clear paradox "
                f"(PARADOX_full={p_full:+.3f}); the ablation has no baseline to preserve")
    if p_min < 0.5 * p_full or p_min <= 0:
        return (f"H_loss_dependent: PARADOX collapsed {p_full:+.3f} -> {p_min:+.3f} (< half) -- a dropped "
                "loss term was load-bearing; qualify the mechanism claim, run a drop-one follow-up")
    within = abs(p_min - p_full) <= 0.10
    return (f"H_intrinsic: PARADOX robust {p_full:+.3f} -> {p_min:+.3f}"
            + ("" if within else " (>0.5x but shifted >0.10; note the attenuation)")
            + " -- surrogate is intrinsic to closure+latent, the loss zoo is engineering convenience")


def analyse(full_dir: Path, min_dir: Path, min_base_val: float | None = None) -> dict:
    def load(d):
        return (_load_supervised(d / LEARNED), _load_supervised(d / REFERENCE))
    a_f, b_f = load(full_dir)
    a_m, b_m = load(min_dir)
    full = _paradox(a_f, b_f)
    minl = _paradox(a_m, b_m)
    boot_full = _cluster_bootstrap_paradox(a_f, b_f)
    boot_min = _cluster_bootstrap_paradox(a_m, b_m)
    p_full, p_min = full["paradox_overall"], minl["paradox_overall"]
    res = {
        "PARADOX_full": p_full, "PARADOX_min": p_min, "delta": float(p_min - p_full),
        "full": {**full, "bootstrap": boot_full},
        "min": {**minl, "bootstrap": boot_min},
        "verdict": _verdict(p_full, p_min),
        "min_base_val": min_base_val,
        "guardrail": ("min-base val not supplied; cannot confirm the minimal model trained"
                      if min_base_val is None else
                      ("minimal base likely degenerate (val >> full-loss ~1.95); ablation uninformative"
                       if min_base_val > 2.3 else "minimal base val in range; ablation informative")),
    }
    return res


# ---------------------------------------------------------------------------- #
def _selftest() -> None:
    def frame(errs, ms, mv):
        n = len(errs)
        return pd.DataFrame({
            "solute_smiles": [f"S{i}" for i in range(n)], "solvent_smiles": [f"V{i}" for i in range(n)],
            "has_solubility": [True] * n, "abs_error": errs,
            "sigma_oracle_mask_solute": ms, "sigma_oracle_mask_solvent": mv})
    MS = [True, True, False, False]
    MV = [True, True, True, False]
    # full-loss: reference clearly worse than learned (paradox +1.0 overall)
    a_f = frame([1, 1, 1, 1], [False]*4, [False]*4)
    b_f = frame([2, 2, 2, 2], MS, MV)
    # minimal-loss H_intrinsic: paradox preserved (+0.95)
    a_m = frame([1, 1, 1, 1], [False]*4, [False]*4)
    b_m = frame([1.95, 1.95, 1.95, 1.95], MS, MV)
    r = _paradox(a_f, b_f)
    assert abs(r["paradox_overall"] - 1.0) < 1e-9, r
    rm = _paradox(a_m, b_m)
    assert abs(rm["paradox_overall"] - 0.95) < 1e-9, rm
    v = _verdict(r["paradox_overall"], rm["paradox_overall"])
    assert v.startswith("H_intrinsic"), v
    # collapse -> loss-dependent
    assert _verdict(1.0, 0.2).startswith("H_loss_dependent")
    assert _verdict(1.0, -0.3).startswith("H_loss_dependent")
    # full-loss null -> inconclusive
    assert _verdict(0.02, 0.5).startswith("INCONCLUSIVE")
    # SMILES misalignment guard
    bad = b_f.copy(); bad["solute_smiles"] = ["X", "S1", "S2", "S3"]
    try:
        _paradox(a_f, bad); raise AssertionError("alignment guard did NOT fire")
    except SystemExit:
        pass
    print("SELFTEST PASS: paradox exact; H_intrinsic/H_loss_dependent/INCONCLUSIVE route; alignment guard fires.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full-dir", type=Path, help="do_paradox_2x2 output (full-loss cond CSVs)")
    ap.add_argument("--min-dir", type=Path, help="do_loss_ablation output (minimal-loss cond CSVs)")
    ap.add_argument("--min-base-val", type=float, default=None, help="minimal-loss base val ln_x2 (guardrail)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _selftest(); return
    if not (args.full_dir and args.min_dir):
        ap.error("--full-dir and --min-dir are required unless --selftest")
    res = analyse(args.full_dir, args.min_dir, args.min_base_val)
    print(json.dumps(res, indent=2))
    print("\n" + "=" * 72)
    print(f"PARADOX_full={res['PARADOX_full']:+.3f}  PARADOX_min={res['PARADOX_min']:+.3f}  "
          f"delta={res['delta']:+.3f}")
    print(f"VERDICT: {res['verdict']}")
    print("=" * 72)
    out = args.out or (args.min_dir / "loss_ablation_analysis.json")
    out.write_text(json.dumps(res, indent=2))
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
