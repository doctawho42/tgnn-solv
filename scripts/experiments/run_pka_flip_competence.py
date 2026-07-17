#!/usr/bin/env python3
"""Resolve the pKa flip's split-dependence into ONE crossover law.

The stratified certification shows ortho HURTS (learned sigma_hat beats the oracle) but the
scaffold-extrapolation control shows ortho HELPS (learned sigma_hat degrades and loses). Both are
the same statement: grounding HELPS on a pole iff the fidelity-determined oracle error is BELOW what
the learned arm can achieve. Fidelity sets the oracle threshold (meta/para 0.32, ortho 1.62);
competence (training budget / interpolation vs extrapolation) sets the learned arm's error; the sign
of the grounding effect is the crossover between them.

This maps the crossover directly: sweep the learned arm's competence (train-data fraction, stratified)
and, as the low-competence extreme, the scaffold-extrapolation regime; report learned MAE vs the fixed
oracle threshold per pole. Prediction: ortho crosses the threshold (sign flips) as competence drops;
meta/para never crosses (oracle too good), so it always helps.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/experiments/run_pka_flip_competence.py \
        --sdf notebooks/data/raw/pKa_QR.sdf --seeds 6 --epochs 300 \
        --out-json results/pka_hammett/flip_competence.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np

HERE = Path(__file__).resolve().parent


def _load(p):
    spec = importlib.util.spec_from_file_location("m", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


fc = _load(HERE / "run_pka_flip_certify.py")   # build, net_charged, stratified_split, train_permol, tc


def subsample_stratified(subset, tr_idx, frac, rng):
    """Keep a `frac` fraction of the train indices, stratified by scaffold (>=1 per scaffold)."""
    if frac >= 1.0:
        return tr_idx
    from collections import defaultdict
    by = defaultdict(list)
    for i in tr_idx:
        by[subset[i].scaffold].append(i)
    keep = []
    for _, idx in by.items():
        idx = list(idx)
        rng.shuffle(idx)
        k = max(1, int(round(frac * len(idx))))
        keep += idx[:k]
    return keep


def regime(subset, in_dim, device, epochs, lr, hidden, layers, seeds, split, frac):
    """Return (learned_mae mean, sd, per-split gaps, oracle_mae) for a competence regime."""
    split_fn = fc.stratified_split if split == "stratified" else fc.tc.scaffold_split
    learned_maes, oracle_maes, gaps = [], [], []
    for s in seeds:
        rng = np.random.default_rng(1000 + s)
        tr_idx, te_idx = split_fn(subset, s)
        if split == "stratified":
            tr_idx = subsample_stratified(subset, tr_idx, frac, rng)
        tr = [subset[i] for i in tr_idx]
        te = [subset[i] for i in te_idx]
        le = fc.train_permol(fc.tc.PhysicsGNN, tr, te, in_dim, hidden, layers, device, epochs, lr, s)
        oe = np.array([abs(float(subset[i].g_oracle) - float(subset[i].pka)) for i in te_idx])
        learned_maes.append(float(le.mean()))
        oracle_maes.append(float(oe.mean()))
        gaps.append(float((oe - le).mean()))       # >0 = oracle worse = HURTS
    return (round(float(np.mean(learned_maes)), 3), round(float(np.std(learned_maes)), 3),
            round(float(np.mean(oracle_maes)), 3), round(float(np.mean(gaps)), 3),
            round(float(np.mean(np.array(gaps) > 0)), 2), [round(g, 3) for g in gaps])


def main():
    import torch
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdf", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--out-json", type=Path, default=Path("results/pka_hammett/flip_competence.json"))
    a = ap.parse_args()

    device = torch.device("cpu")
    data, n_raw, n_kept = fc.build(a.sdf)
    in_dim = data[0].x.shape[1]
    seeds = list(range(42, 42 + a.seeds))
    print(f"QC {n_raw}->{n_kept}; graphs={len(data)}; seeds={seeds}")

    poles = {"high_F (meta/para)": [g for g in data if g.fidelity == "high_F"],
             "low_F (ortho/hetero)": [g for g in data if g.fidelity == "low_F"]}
    # competence ladder: stratified at decreasing data fraction, then scaffold-extrapolation
    ladder = [("stratified", 1.0), ("stratified", 0.5), ("stratified", 0.25),
              ("stratified", 0.12), ("scaffold", 1.0)]
    out = {"n_raw": n_raw, "n_kept": n_kept, "seeds": a.seeds, "poles": {}}
    for pname, subset in poles.items():
        print(f"\n===== {pname}  n={len(subset)} =====")
        rows = []
        for split, frac in ladder:
            lm, lsd, om, gap, frac_hurt, gaps = regime(
                subset, in_dim, device, a.epochs, a.lr, a.hidden, a.layers, seeds, split, frac)
            tag = f"{split[:5]}/f={frac}" if split == "stratified" else "scaffold-EXTRAP"
            sign = "HURTS" if gap > 0 else "HELPS"
            crossed = "learned < oracle (HURTS)" if lm < om else "learned > oracle (HELPS)"
            rows.append({"regime": tag, "learned_mae": lm, "learned_sd": lsd, "oracle_mae": om,
                         "gap": gap, "sign": sign, "frac_splits_hurt": frac_hurt, "per_seed_gap": gaps})
            print(f"  {tag:16s}  learned={lm:.3f}+-{lsd:.3f}  oracle(threshold)={om:.3f}  "
                  f"gap={gap:+.3f}  {sign}  [{crossed}]  hurt {frac_hurt*100:.0f}%")
        out["poles"][pname] = {"n": len(subset), "oracle_threshold": rows[0]["oracle_mae"], "ladder": rows}

    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {a.out_json}")
    print("Crossover law: grounding HELPS iff learned_mae > oracle_threshold (fidelity-set).")


if __name__ == "__main__":
    main()
