#!/usr/bin/env python3
"""Constant-offset control for the transfer ratio of the compensating-surrogate probe.

The transfer arm of `run_compensation_surrogate.py` compares a ridge-fitted distortion
operator D against the ZERO-DRIFT (identity) null out of sample.  That null is weak: a
single molecule-INDEPENDENT constant offset, fitted on the same training half, already
explains whatever part of the drift is a common shift of every profile.  The quantity
that bounds the transfer claim is therefore

    offset ratio      = MSE(identity) / MSE(mean-offset)      <- what a constant buys
    D-over-offset     = MSE(mean-offset) / MSE(D)             <- what D buys BEYOND it

and `improvement_ratio` = offset ratio x D-over-offset exactly.

This script recomputes the deposited two-model companion run of
`results/compensation/isolation.json` -- the only compensating-surrogate run whose BOTH
checkpoints are still on disk -- with that control added, and gates the deposit on
reproducing the deposited arms of that file to 1e-6.  The three-seed run behind the
headline 4.1x (results/sur/surrogate_seeds/surrogate_seeds.json) and the GPU companion
run (results/compensation/isolation_gpu.json) point at checkpoints that were not
retained, so the control cannot be computed for either; the deposit records that.

Run:

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python \
        scripts/analysis/run_surrogate_offset_control.py

Writes results/compensation/offset_control.json.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "results" / "compensation" / "offset_control.json"
REFERENCE = ROOT / "results" / "compensation" / "isolation.json"
SLE_CKPT = ROOT / "checkpoints" / "cosmo_sac" / "tgnn_cosmo.pt"
BASE_CKPT = ROOT / "results" / "closure_fix" / "ckpt" / "arm_base.pt"
SIGMA_CSV = ROOT / "results" / "sigma_profile_artifact" / "sigma_profiles.csv"
MATCHED_CSV = ROOT / "results" / "b_insuff" / "matched_pairs.csv"

LAM = 1e-3  # the deposited run's --lam default


def arms(target: np.ndarray, ref: np.ndarray) -> dict:
    """Identity / constant-offset / ridge-D out-of-sample MSEs on the deposited split.

    The permutation, the half split and the ridge design (ref plus an intercept column)
    are exactly those of run_compensation_surrogate.a1a2, so `oos_mse_distortion_D` and
    `oos_mse_identity` here must reproduce the deposited ones bit for bit.
    """
    from run_compensation_surrogate import ridge_fit

    n = len(target)
    rng = np.random.default_rng(0)
    idx = rng.permutation(n)
    half = n // 2
    tr, te = idx[:half], idx[half:]

    d_mat = ridge_fit(np.column_stack([ref[tr], np.ones(len(tr))]), target[tr], LAM)
    mse_d = float(np.mean((np.column_stack([ref[te], np.ones(len(te))]) @ d_mat - target[te]) ** 2))
    mse_id = float(np.mean((ref[te] - target[te]) ** 2))

    # the control: one molecule-independent shift of the whole profile, fitted on the
    # training half only, applied unchanged to every held-out molecule
    offset = (target[tr] - ref[tr]).mean(axis=0, keepdims=True)
    mse_off = float(np.mean((ref[te] + offset - target[te]) ** 2))

    return {
        "n": n,
        "n_train": int(len(tr)),
        "n_heldout": int(len(te)),
        "oos_mse_identity": mse_id,
        "oos_mse_constant_offset": mse_off,
        "oos_mse_distortion_D": mse_d,
        "improvement_ratio_D_over_identity": float(mse_id / mse_d),
        "offset_ratio_over_identity": float(mse_id / mse_off),
        "D_ratio_over_offset": float(mse_off / mse_d),
    }


def main() -> None:
    from run_compensation_surrogate import _canon, load_true_shapes, predict_sigma_hat

    import pandas as pd
    from tgnn_solv.inference import load_model

    for p in (SLE_CKPT, BASE_CKPT, SIGMA_CSV, MATCHED_CSV, REFERENCE):
        if not p.exists():
            raise SystemExit(f"missing input: {p}")

    device = torch.device("cpu")
    true = load_true_shapes(str(SIGMA_CSV))
    md = pd.read_csv(MATCHED_CSV, low_memory=False)
    mols: set[str] = set()
    for col in ("solute_key", "solvent_key"):
        if col in md.columns:
            mols |= set(md[col].dropna().astype(str))
    keep = []
    for s in sorted(mols):
        c = _canon(s)
        if c is not None and c in true:
            keep.append((s, c))
    smiles = [s for s, _ in keep]
    sig_true = np.stack([true[c] for _, c in keep])

    sle_model, _ = load_model(str(SLE_CKPT), device=device)
    sig_hat = predict_sigma_hat(sle_model, smiles, device)
    base_model, _ = load_model(str(BASE_CKPT), device=device)
    sig_grounded = predict_sigma_hat(base_model, smiles, device)

    res = {
        "vs_true": arms(sig_hat, sig_true),
        "isolation": arms(sig_hat, sig_grounded),
    }

    dep = json.loads(REFERENCE.read_text())
    checks = {}
    for tag, key in (("vs_true", "vs_true"), ("isolation", "isolation")):
        a2 = dep[key]["A2"]
        checks[f"{tag}_reproduces_oos_mse_identity"] = bool(
            abs(res[tag]["oos_mse_identity"] - a2["oos_mse_identity"]) < 1e-9
        )
        checks[f"{tag}_reproduces_oos_mse_distortion_D"] = bool(
            abs(res[tag]["oos_mse_distortion_D"] - a2["oos_mse_distortion_D"]) < 1e-9
        )
        checks[f"{tag}_reproduces_improvement_ratio"] = bool(
            abs(res[tag]["improvement_ratio_D_over_identity"] - a2["improvement_ratio"]) < 1e-4
        )
    checks["n_is_44"] = bool(res["vs_true"]["n"] == 44)
    checks["factorisation_exact"] = all(
        abs(res[t]["offset_ratio_over_identity"] * res[t]["D_ratio_over_offset"]
            - res[t]["improvement_ratio_D_over_identity"]) < 1e-6
        for t in ("vs_true", "isolation")
    )

    out = {
        "provenance": (
            "constant-offset control on the two-model companion run deposited as "
            "results/compensation/isolation.json, via "
            "scripts/analysis/run_surrogate_offset_control.py; both checkpoints on disk"
        ),
        "sle_checkpoint": str(SLE_CKPT.relative_to(ROOT)),
        "grounded_checkpoint": str(BASE_CKPT.relative_to(ROOT)),
        "set": "44 VT-2005-matched molecules, sigma shape on 51 bins",
        "split": "seed-0 permutation, 22 train / 22 held out (the deposited run's split)",
        "control": (
            "one molecule-independent constant shift of the profile, fitted on the "
            "training half, applied unchanged to every held-out molecule"
        ),
        "arms": res,
        "not_computable": {
            "three_seed_headline": (
                "results/sur/surrogate_seeds/surrogate_seeds.json (transfer 4.1+-0.5x): the "
                "three seed checkpoints were not retained, so no offset control exists for it"
            ),
            "gpu_companion_run": (
                "results/compensation/isolation_gpu.json (transfer 3.3x): its checkpoint "
                "fields point at an ephemeral scratch path that no longer exists"
            ),
        },
        "scope": (
            "This run is the uncontrolled two-model comparison, which over-states both the "
            "departure and the transfer relative to the three-seed within-model contrast; "
            "the control bounds the transfer ratio ON THIS RUN and is not a measurement of "
            "the three-seed 4.1x."
        ),
        "verification": checks,
        "verified": all(checks.values()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    for tag in ("vs_true", "isolation"):
        a = res[tag]
        print(f"[{tag}] identity {a['oos_mse_identity']:.6e}  offset {a['oos_mse_constant_offset']:.6e}  "
              f"D {a['oos_mse_distortion_D']:.6e}")
        print(f"    D/identity x{a['improvement_ratio_D_over_identity']:.3f} = "
              f"offset/identity x{a['offset_ratio_over_identity']:.3f} * "
              f"D/offset x{a['D_ratio_over_offset']:.3f}")
    print("verification:", json.dumps(checks))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
