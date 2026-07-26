#!/usr/bin/env python
"""Is the sigma-drift low-rank BEYOND what smoothness alone produces?

The compensating-surrogate section reads the top-2 explained-variance ratio (EVR) of the
mean-centred sigma-deviation against an ISOTROPIC null. That null is too weak: any smooth
function on the 51-bin sigma grid has a concentrated spectrum whether or not it carries
information. Smoothing iid noise reproduces the effect on its own (top-2 EVR 0.25 at kernel
sd 1 bin, 0.58 at 4, 0.83 at 8).

The right reference keeps each deviation's own smoothness and destroys only the alignment
BETWEEN molecules, which is what "low-rank, transferable" asserts. Two such nulls:

  phase-randomised : per row, randomise the Fourier phases and keep the amplitude spectrum.
                     Each row's roughness is preserved exactly; any shared direction is gone.
  wrong-molecule   : assign each molecule another molecule's true profile and form the same
                     deviation. Carries the real profile manifold and no compensation.

The statistic is credited only with the excess over these, never over the isotropic null.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_evr_structured_null.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts" / "analysis"))

from run_compensation_surrogate import _canon, load_true_shapes, predict_sigma_hat  # noqa: E402


def top2_evr(M: np.ndarray) -> float:
    X = M - M.mean(0)
    v = np.linalg.svd(X, compute_uv=False) ** 2
    return float(v[:2].sum() / v.sum())


def phase_randomise(row: np.ndarray, rng) -> np.ndarray:
    """Keep the amplitude spectrum, randomise the phases: same roughness, no shared direction."""
    F = np.fft.rfft(row)
    ph = rng.uniform(0, 2 * np.pi, len(F))
    ph[0] = 0.0                       # keep the mean real
    if len(row) % 2 == 0:
        ph[-1] = 0.0                  # Nyquist term stays real
    return np.fft.irfft(np.abs(F) * np.exp(1j * ph), n=len(row))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", default="checkpoints/cosmo_sac/tgnn_cosmo.pt")
    ap.add_argument("--baseline-checkpoint", default=None,
                    help="if given, the deviation is checkpoint minus baseline (isolation "
                         "drift); otherwise it is checkpoint minus the VT-2005 reference")
    ap.add_argument("--sigma-profiles", default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    ap.add_argument("--n-null", type=int, default=2000)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out-json", type=Path,
                    default=Path("results/compensation/evr_structured_null.json"))
    args = ap.parse_args()

    from tgnn_solv.inference import load_model
    device = torch.device(args.device)

    true = load_true_shapes(str(_REPO / args.sigma_profiles))
    md = pd.read_csv(_REPO / args.matched_csv, low_memory=False)
    mols: set[str] = set()
    for col in ("solute_key", "solvent_key"):
        if col in md.columns:
            mols |= set(md[col].dropna().astype(str))
    keep = [(s, _canon(s)) for s in sorted(mols)]
    keep = [(s, c) for s, c in keep if c is not None and c in true]
    smiles = [s for s, _ in keep]
    S = np.stack([true[c] for _, c in keep])
    n, p = S.shape
    print(f"matched set: n={n}, bins={p}")

    model, _ = load_model(str(_REPO / args.checkpoint), device=device)
    hat = predict_sigma_hat(model, smiles, device)
    if args.baseline_checkpoint:
        base, _ = load_model(str(_REPO / args.baseline_checkpoint), device=device)
        drift = hat - predict_sigma_hat(base, smiles, device)
        what = "isolation drift (checkpoint - baseline)"
    else:
        drift = hat - S
        what = "deviation from the VT-2005 reference"
    print(f"deviation: {what}\n")

    # A degenerate deviation makes the EVR 0/0, and NaN compares false against every null,
    # which would silently print the favourable verdict. Refuse instead.
    scale = float(np.abs(drift).max())
    if not np.isfinite(scale) or scale < 1e-12:
        raise SystemExit(
            f"the deviation is identically zero (max |drift| = {scale:.3e}); these two "
            "checkpoints share a sigma head, so there is no drift to characterise")

    obs = top2_evr(drift)
    if not np.isfinite(obs):
        raise SystemExit("top-2 EVR is not finite; refusing to report a verdict")
    rng = np.random.default_rng(0)

    iso = np.array([top2_evr(rng.standard_normal((n, p))) for _ in range(args.n_null)])
    phase = np.array([top2_evr(np.stack([phase_randomise(r, np.random.default_rng(1000 * k + i))
                                         for i, r in enumerate(drift)]))
                      for k in range(min(args.n_null, 400))])
    wrong = []
    for k in range(200):
        r = np.random.default_rng(k)
        idx = r.permutation(n)
        while np.any(idx == np.arange(n)):
            idx = r.permutation(n)
        wrong.append(top2_evr(S[idx] - S))
    wrong = np.array(wrong)

    print(f"observed top-2 EVR                    : {obs:.4f}")
    print(f"  isotropic null (what the paper used): {iso.mean():.4f} +/- {iso.std():.4f}"
          f"   ratio {obs/iso.mean():.2f}x")
    print(f"  PHASE-RANDOMISED null               : {phase.mean():.4f} +/- {phase.std():.4f}"
          f"   p = {(phase >= obs).mean():.4f}")
    print(f"  WRONG-MOLECULE null                 : {wrong.mean():.4f} +/- {wrong.std():.4f}"
          f"   p = {(wrong >= obs).mean():.4f}")

    survives = (phase >= obs).mean() < 0.05 and (wrong >= obs).mean() < 0.05
    print()
    print("VERDICT: the drift is low-rank beyond its own smoothness."
          if survives else
          "VERDICT: the statistic does NOT exceed a structure-matched null. The top-2 EVR\n"
          "         is a property of smooth 51-bin functions, not evidence of a shared\n"
          "         compensating direction; 'low-rank' is not supported by it.")

    out = {"deviation": what, "n": n, "bins": p, "observed_top2_evr": obs,
           "isotropic_null_mean": float(iso.mean()),
           "phase_randomised_null_mean": float(phase.mean()),
           "phase_randomised_p": float((phase >= obs).mean()),
           "wrong_molecule_null_mean": float(wrong.mean()),
           "wrong_molecule_p": float((wrong >= obs).mean()),
           "exceeds_structured_null": bool(survives)}
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    (_REPO / args.out_json).write_text(json.dumps(out, indent=2))
    print(f"\nwrote {args.out_json}")


if __name__ == "__main__":
    main()
