#!/usr/bin/env python
"""fix-g Gate 1 primary metric: rho = ||sigma_hat - sigma|| / ||sigma|| on the matched VT-2005 set.

Pre-registration: reports/PREREG_fix_g_2026-07-19.md.
rho is the physicality of the learned sigma-profile: 0 = perfectly physical, larger = more distorted.
Anchors (Paper 1): rho_free = 0.51 (free latent), rho_grounded = 0.36 (sigma-grounded latent).
Decision (per group of seeds): GO if mean rho <= 0.46 with solubility preserved;
NO-GO if rho >= 0.50; PARTIAL if 0.46 < rho < 0.50.

rho here is the same `rel_deviation` computed in run_compensation_surrogate.py, so it is on the
same footing as the committed anchors. Reported per checkpoint, then mean +/- sd over seeds, with a
drop-one (leave-one-molecule-out) leverage range because the matched set is small (~44 solutes).

Usage:
  python scripts/experiments/fix_g_rho_eval.py \
      --checkpoints fixg=ckpt/fixg_s0.pt fixg=ckpt/fixg_s1.pt fixg=ckpt/fixg_s2.pt \
                    free=ckpt/free_s0.pt free=ckpt/free_s1.pt free=ckpt/free_s2.pt \
      --out-json results/fix_g/gate1_rho.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

# make the src-layout package + the analysis helpers importable when run directly
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts" / "analysis"))
from run_compensation_surrogate import _canon, load_true_shapes, predict_sigma_hat  # noqa: E402


def rho_per_molecule(sig_hat: np.ndarray, sig_true: np.ndarray) -> np.ndarray:
    """Per-molecule relative deviation ||sigma_hat_i - sigma_i|| / ||sigma_i||."""
    num = np.linalg.norm(sig_hat - sig_true, axis=1)
    den = np.linalg.norm(sig_true, axis=1) + 1e-12
    return num / den


def rho_dataset(sig_hat: np.ndarray, sig_true: np.ndarray) -> float:
    """Dataset rho = mean||r|| / mean||ref|| -- the committed `rel_deviation` definition."""
    num = np.linalg.norm(sig_hat - sig_true, axis=1).mean()
    den = np.linalg.norm(sig_true, axis=1).mean() + 1e-12
    return float(num / den)


def dropone_range(sig_hat: np.ndarray, sig_true: np.ndarray) -> tuple[float, float]:
    """Leave-one-molecule-out range of the dataset rho (leverage on the small matched set)."""
    n = len(sig_hat)
    vals = []
    for i in range(n):
        keep = [j for j in range(n) if j != i]
        vals.append(rho_dataset(sig_hat[keep], sig_true[keep]))
    return float(min(vals)), float(max(vals))


def verdict(mean_rho: float) -> str:
    if mean_rho <= 0.46:
        return "GO (rho <= 0.46)"
    if mean_rho >= 0.50:
        return "NO-GO (rho >= 0.50; unmoved from free 0.51)"
    return "PARTIAL (0.46 < rho < 0.50)"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoints", nargs="+", required=True,
                    help="label=path entries, e.g. fixg=a.pt free=b.pt (labels group the seeds)")
    ap.add_argument("--sigma-profiles", default="results/sigma_profile_artifact/sigma_profiles.csv")
    ap.add_argument("--matched-csv", default="results/b_insuff/matched_pairs.csv")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out-json", type=Path, default=Path("results/fix_g/gate1_rho.json"))
    args = ap.parse_args()

    from tgnn_solv.inference import load_model
    device = torch.device(args.device)

    true = load_true_shapes(args.sigma_profiles)
    import pandas as pd
    md = pd.read_csv(args.matched_csv, low_memory=False)
    mols: set[str] = set()
    for col in ("solute_key", "solvent_key"):
        if col in md.columns:
            mols |= set(md[col].dropna().astype(str))
    keep = [(s, _canon(s)) for s in sorted(mols)]
    keep = [(s, c) for s, c in keep if c is not None and c in true]
    if len(keep) < 10:
        raise SystemExit(f"too few matched molecules with true profiles: {len(keep)}")
    smiles = [s for s, _ in keep]
    sig_true = np.stack([true[c] for _, c in keep])
    print(f"matched molecules with true VT-2005 profile: {len(keep)}")

    per_ckpt = []
    groups: dict[str, list[float]] = defaultdict(list)
    for entry in args.checkpoints:
        if "=" not in entry:
            raise SystemExit(f"checkpoint entry must be label=path, got {entry!r}")
        label, path = entry.split("=", 1)
        model, cfg = load_model(path, device=device)
        sig_hat = predict_sigma_hat(model, smiles, device)
        rho = rho_dataset(sig_hat, sig_true)
        lo, hi = dropone_range(sig_hat, sig_true)
        rank = int(getattr(cfg, "cosmo_sac_kernel_residual_rank", 0))
        rec = {"label": label, "checkpoint": path, "kernel_residual_rank": rank,
               "rho": rho, "dropone_min": lo, "dropone_max": hi, "n": len(keep)}
        per_ckpt.append(rec)
        groups[label].append(rho)
        print(f"  [{label}] {os.path.basename(path)}: rho={rho:.3f}  (drop-one {lo:.3f}-{hi:.3f}, rank={rank})")

    summary = {}
    for label, rhos in groups.items():
        arr = np.array(rhos)
        summary[label] = {"n_seeds": len(arr), "rho_mean": float(arr.mean()),
                          "rho_sd": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
                          "rho_seeds": [float(x) for x in arr]}
    out = {"prereg": "reports/PREREG_fix_g_2026-07-19.md",
           "anchors": {"rho_free": 0.51, "rho_grounded": 0.36, "GO_threshold": 0.46, "NOGO_threshold": 0.50},
           "per_checkpoint": per_ckpt, "summary": summary}
    if "fixg" in summary:
        out["gate1_verdict"] = verdict(summary["fixg"]["rho_mean"])
        print(f"\nGate 1 (fix-g mean rho = {summary['fixg']['rho_mean']:.3f}): {out['gate1_verdict']}")
        if "free" in summary:
            print(f"  free-baseline mean rho = {summary['free']['rho_mean']:.3f} "
                  f"(anchor 0.51); grounded anchor 0.36")
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2))
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
