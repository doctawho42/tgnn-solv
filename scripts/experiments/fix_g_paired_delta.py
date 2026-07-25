#!/usr/bin/env python
"""Paired Delta-rho between the two arms of a matched fork, plus its trajectory.

Why paired: both arms are scored on the SAME n=44 molecules, so each arm's marginal
drop-one spread badly overstates the uncertainty of their DIFFERENCE -- shared
per-molecule difficulty cancels in d_i = rho_i(free) - rho_i(fixg). Reporting the
marginal ranges instead makes a real contrast look like noise.

Why the epoch guard: the rolling checkpoint is rewritten only every --checkpoint-every
epochs, so several consecutive snapshots are byte-identical copies of an OLDER state.
Pairing arms by snapshot index therefore silently compares different epochs and
fabricates a trend. Each checkpoint's true (phase, epoch) is read from its resume_state
and mismatched pairs are refused.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/experiments/fix_g_paired_delta.py \
        --pair early=snap/fixg_5.pt,snap/free_5.pt \
        --pair late=snap/fixg_10.pt,snap/free_10.pt
"""
from __future__ import annotations

import argparse
import json
import sys
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd
import torch

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts" / "analysis"))

from run_compensation_surrogate import _canon, load_true_shapes, predict_sigma_hat  # noqa: E402

# Measured on the same n=44 set by scripts/experiments/rho_control_ladder.py.
WRONG_MOLECULE_BAND = 0.6505


def build_matched_set(sigma_csv: str, matched_csv: str):
    true = load_true_shapes(sigma_csv)
    md = pd.read_csv(matched_csv, low_memory=False)
    mols: set[str] = set()
    for col in ("solute_key", "solvent_key"):
        if col in md.columns:
            mols |= set(md[col].dropna().astype(str))
    keep = [(s, _canon(s)) for s in sorted(mols)]
    keep = [(s, c) for s, c in keep if c is not None and c in true]
    return [s for s, _ in keep], np.stack([true[c] for _, c in keep])


def checkpoint_epoch(path: str) -> tuple:
    """(phase, next_epoch_in_phase) the checkpoint actually holds -- not its filename."""
    ck = torch.load(path, map_location="cpu", weights_only=False)
    rs = ck.get("resume_state") or {}
    return rs.get("phase"), rs.get("next_epoch_in_phase")


def per_molecule_rho(path: str, smiles, sig_true, device) -> np.ndarray:
    from tgnn_solv.inference import load_model

    model, _ = load_model(path, device=device)
    sig_hat = predict_sigma_hat(model, smiles, device)
    return (np.linalg.norm(sig_hat - sig_true, axis=1)
            / (np.linalg.norm(sig_true, axis=1) + 1e-12))


def analyse(label, fixg_path, free_path, smiles, sig_true, device, n_boot):
    ef, er = checkpoint_epoch(fixg_path), checkpoint_epoch(free_path)
    if ef != er:
        print(f"[{label}] REFUSED: fixg at {ef}, free at {er} -- not a controlled contrast.")
        return None
    rf = per_molecule_rho(fixg_path, smiles, sig_true, device)
    rr = per_molecule_rho(free_path, smiles, sig_true, device)
    d = rr - rf                                   # positive => fixg is more physical
    n = len(d)
    rng = np.random.default_rng(0)
    boot = np.array([rng.choice(d, n, replace=True).mean() for _ in range(n_boot)])
    lo, hi = (float(x) for x in np.percentile(boot, [2.5, 97.5]))
    wins = int((d > 0).sum())
    p = sum(comb(n, i) for i in range(wins, n + 1)) / 2 ** n

    print(f"\n--- {label}  (phase {ef[0]}, epoch {ef[1]}) ---")
    print(f"  rho_fixg = {rf.mean():.4f}   rho_free = {rr.mean():.4f}")
    print(f"  paired delta = {d.mean():+.4f}   95% CI [{lo:+.4f}, {hi:+.4f}]"
          f"   {'excludes 0' if lo > 0 or hi < 0 else 'includes 0'}")
    print(f"  fixg more physical on {wins}/{n} molecules   sign-test p = {p:.2e}")
    return {"label": label, "epoch": ef[1], "phase": ef[0],
            "rho_fixg": float(rf.mean()), "rho_free": float(rr.mean()),
            "delta": float(d.mean()), "ci_low": lo, "ci_high": hi,
            "wins": wins, "n": n, "sign_p": float(p)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", action="append", required=True,
                    help="label=fixg.pt,free.pt (repeat for a trajectory)")
    ap.add_argument("--sigma-profiles", default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--target-delta", type=float, default=0.05, help="the GO bar")
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args()

    smiles, sig_true = build_matched_set(args.sigma_profiles, args.matched_csv)
    print(f"matched molecules with true VT-2005 profile: {len(smiles)}")
    device = torch.device(args.device)

    rows = []
    for spec in args.pair:
        label, paths = spec.split("=", 1)
        fixg_path, free_path = paths.split(",")
        r = analyse(label, fixg_path, free_path, smiles, sig_true, device, args.n_boot)
        if r:
            rows.append(r)

    if len(rows) >= 2:
        a, b = rows[0], rows[-1]
        span = b["epoch"] - a["epoch"]
        if span > 0:
            g = (b["delta"] - a["delta"]) / span
            fg = (b["rho_fixg"] - a["rho_fixg"]) / span
            print(f"\n=== trajectory over {span} epochs ===")
            print(f"  delta growth    : {g:+.5f}/epoch")
            print(f"  rho_fixg descent: {fg:+.5f}/epoch")
            if g > 0:
                need = (args.target_delta - b["delta"]) / g
                print(f"  epochs to reach delta={args.target_delta}: {need:.0f}")
            if fg < 0:
                need2 = (b["rho_fixg"] - WRONG_MOLECULE_BAND) / (-fg)
                print(f"  epochs for rho_fixg to cross the wrong-molecule band "
                      f"({WRONG_MOLECULE_BAND}): {need2:.0f}")
            print("  NB both conditions are required for GO; delta alone gives PARTIAL.")

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps({"pairs": rows}, indent=2))
        print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
