#!/usr/bin/env python3
"""Certify the pKa grounding-FLIP: the reference-sigma oracle HELPS on the clean meta/para
pole and HURTS on the ortho pole -- the same intervention, opposite signs, predicted by
closure specification. Upgrades the single-split ortho pole of sections/pka-domain.tex
(Exploratory) to a K-split, paired, bootstrapped measurement.

Two fixes over run_pka_trained_comparison.py:
  1. DATA QC (uniform, closure-INDEPENDENT): drop net-charged (pre-ionized) input
     structures. The re-fetched canonical full OPERA (7904) ships a handful of pre-protonated
     microstates (aminopyridinium [NH+] at pKa -7.78, a pyrylium [O+], ...) that wreck the
     clean pole (pyridinium RMSE 0.63->3.83). Net formal charge != 0 removes exactly these
     while KEEPING net-neutral substituents (nitro [N+]([O-])=O), restoring the clean pole to
     RMSE ~0.63. Filtering by residual-to-the-closure would be circular; this is not.
  2. STATS: the oracle is evaluated on EVERY split (not just seed[0]); the flip statistic is
     the paired per-molecule gap d = |err_oracle| - |err_learned| (>0 = oracle worse = HURTS),
     aggregated over K stratified splits with sign consistency + a scaffold-cluster bootstrap.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/experiments/run_pka_flip_certify.py \
        --sdf notebooks/data/raw/pKa_QR.sdf --device cpu --n-splits 20 --epochs 300 \
        --split stratified --out-json results/pka_hammett/flip_certify_stratified.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import torch
import torch.nn as nn
from rdkit import Chem
from rdkit import RDLogger
from torch_geometric.loader import DataLoader

RDLogger.DisableLog("rdApp.*")
HERE = Path(__file__).resolve().parent


def _load(modpath):
    spec = importlib.util.spec_from_file_location("m", modpath)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tc = _load(HERE / "run_pka_trained_comparison.py")


def net_charged(smi):
    """Non-circular structural QC flag: net formal charge != 0 (a pre-ionized microstate).
    KEEPS net-neutral charge-separated groups such as nitro [N+]([O-])=O."""
    mol = Chem.MolFromSmiles(str(smi))
    return mol is None or Chem.GetFormalCharge(mol) != 0


def build(sdf):
    mod = tc._load_real_decomp()
    recs, _ = mod.load_records(Path(sdf), mod._load_builder())
    kept = [r for r in recs if not net_charged(r["smiles"])]
    data = []
    for r in kept:
        g = tc._to_graph(r["smiles"])
        if g is None:
            continue
        g.pka = torch.tensor([r["pka"]], dtype=torch.float)
        g.pka0 = torch.tensor([r["pka0"]], dtype=torch.float)
        g.rho = torch.tensor([r["rho"]], dtype=torch.float)
        g.g_oracle = torch.tensor([r["g"]], dtype=torch.float)
        g.fidelity = r["bin"]
        g.scaffold = r["scaffold"]
        data.append(g)
    return data, len(recs), len(kept)


def stratified_split(subset, seed, test_frac=0.2):
    """80/20 within each chemical scaffold: keeps every scaffold in train AND test, so the
    test of 'learned sigma_hat quality vs the oracle' is not confounded with scaffold
    extrapolation (unlike a 2-ring-system Murcko split on the meta/para pole)."""
    groups = defaultdict(list)
    for i, g in enumerate(subset):
        groups[g.scaffold].append(i)
    rng = np.random.default_rng(seed)
    tr, te = [], []
    for _, idx in groups.items():
        idx = list(idx)
        rng.shuffle(idx)
        k = max(1, int(round(test_frac * len(idx))))
        te += idx[:k]
        tr += idx[k:]
    return tr, te


def train_permol(Cls, tr, te, in_dim, hid, layers, device, epochs, lr, seed):
    torch.manual_seed(seed)
    model = Cls(in_dim, hid, layers).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    lossf = nn.L1Loss()
    model.train()
    for _ in range(epochs):
        for b in DataLoader(tr, batch_size=128, shuffle=True):
            b = b.to(device)
            opt.zero_grad()
            pred = model(b, b.pka0.squeeze(-1), b.rho.squeeze(-1))
            loss = lossf(pred, b.pka.squeeze(-1))
            loss.backward()
            opt.step()
    model.eval()
    errs = []
    with torch.no_grad():
        for b in DataLoader(te, batch_size=256, shuffle=False):
            b = b.to(device)
            pred = model(b, b.pka0.squeeze(-1), b.rho.squeeze(-1))
            errs.append((pred - b.pka.squeeze(-1)).abs().cpu().numpy())
    return np.concatenate(errs) if errs else np.array([])


def cluster_boot(d, scaff, seed=0, B=4000):
    """Cluster bootstrap over scaffold labels (the correlated unit). Returns P(mean d>0)
    and the 90% CI of mean d. NOTE: few chemical scaffolds => read as a coarse check;
    the K-split sign consistency is the stronger statistic."""
    rng = np.random.default_rng(seed)
    scaff = np.asarray(scaff)
    uniq = np.unique(scaff)
    idx_by = {s: np.where(scaff == s)[0] for s in uniq}
    means = []
    for _ in range(B):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        rows = np.concatenate([idx_by[s] for s in pick])
        means.append(float(d[rows].mean()))
    means = np.array(means)
    return float((means > 0).mean()), (float(np.percentile(means, 5)), float(np.percentile(means, 95)))


def split_boot(per_split, seed=0, B=4000):
    """Bootstrap over the K independent splits (each a fresh stratified split)."""
    rng = np.random.default_rng(seed)
    ps = np.asarray(per_split)
    means = np.array([float(ps[rng.integers(0, len(ps), len(ps))].mean()) for _ in range(B)])
    return float((means > 0).mean()), (float(np.percentile(means, 5)), float(np.percentile(means, 95)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdf", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--n-splits", type=int, default=20)
    ap.add_argument("--split", choices=["scaffold", "stratified"], default="stratified")
    ap.add_argument("--out-json", type=Path, default=Path("results/pka_hammett/flip_certify.json"))
    a = ap.parse_args()

    device = torch.device(a.device if (a.device != "cuda" or torch.cuda.is_available()) else "cpu")
    data, n_raw, n_kept = build(a.sdf)
    in_dim = data[0].x.shape[1]
    print(f"QC net_charge!=0: {n_raw} records -> {n_kept} kept; graphs={len(data)}; device={device}; split={a.split}")
    seeds = list(range(42, 42 + a.n_splits))
    split_fn = stratified_split if a.split == "stratified" else tc.scaffold_split
    strata = {"high_F (meta/para)": [g for g in data if g.fidelity == "high_F"],
              "low_F (ortho/hetero)": [g for g in data if g.fidelity == "low_F"]}
    out = {"qc": "net_formal_charge!=0 dropped (uniform)", "split": a.split,
           "epochs": a.epochs, "n_splits": a.n_splits, "n_raw": n_raw, "n_kept": n_kept, "strata": {}}

    for label, subset in strata.items():
        print(f"\n== {label}: n={len(subset)} ==")
        all_d, all_scaff, per_split, learned_maes, oracle_maes = [], [], [], [], []
        for seed in seeds:
            tr_idx, te_idx = split_fn(subset, seed)
            tr = [subset[i] for i in tr_idx]
            te = [subset[i] for i in te_idx]
            le = train_permol(tc.PhysicsGNN, tr, te, in_dim, a.hidden, a.layers, device, a.epochs, a.lr, seed)
            oe = np.array([abs(float(subset[i].g_oracle) - float(subset[i].pka)) for i in te_idx])
            d = oe - le                      # >0 = oracle worse = grounding HURTS
            all_d.append(d)
            all_scaff += [subset[i].scaffold for i in te_idx]
            per_split.append(float(d.mean()))
            learned_maes.append(float(le.mean()))
            oracle_maes.append(float(oe.mean()))
        all_d = np.concatenate(all_d)
        ps = np.array(per_split)
        cb_p, cb_ci = cluster_boot(all_d, all_scaff)
        sb_p, sb_ci = split_boot(per_split)
        rec = {
            "n": len(subset),
            "learned_mae": [round(float(np.mean(learned_maes)), 3), round(float(np.std(learned_maes)), 3)],
            "oracle_mae": [round(float(np.mean(oracle_maes)), 3), round(float(np.std(oracle_maes)), 3)],
            "gap_oracle_minus_learned": [round(float(ps.mean()), 3), round(float(ps.std()), 3)],
            "per_split_gap": [round(x, 3) for x in per_split],
            "frac_splits_oracle_worse": round(float((ps > 0).mean()), 3),
            "cluster_boot_P_oracle_worse": round(cb_p, 3), "cluster_boot_CI90": [round(cb_ci[0], 3), round(cb_ci[1], 3)],
            "split_boot_P_oracle_worse": round(sb_p, 3), "split_boot_CI90": [round(sb_ci[0], 3), round(sb_ci[1], 3)],
        }
        out["strata"][label] = rec
        direction = "HURTS (oracle worse)" if ps.mean() > 0 else "HELPS (oracle better)"
        print(f"  learned={rec['learned_mae'][0]}+-{rec['learned_mae'][1]}  "
              f"oracle={rec['oracle_mae'][0]}+-{rec['oracle_mae'][1]}  gap={ps.mean():+.3f}  {direction}")
        print(f"  oracle worse in {(ps > 0).mean() * 100:.0f}% of {a.n_splits} splits;  "
              f"cluster-boot P={cb_p:.3f} CI90[{cb_ci[0]:+.2f},{cb_ci[1]:+.2f}];  split-boot P={sb_p:.3f} CI90[{sb_ci[0]:+.2f},{sb_ci[1]:+.2f}]")

    hp = out["strata"]["high_F (meta/para)"]
    lp = out["strata"]["low_F (ortho/hetero)"]
    help_ok = hp["gap_oracle_minus_learned"][0] < 0 and hp["split_boot_P_oracle_worse"] < 0.1
    hurt_ok = lp["gap_oracle_minus_learned"][0] > 0 and lp["split_boot_P_oracle_worse"] > 0.9
    out["verdict"] = {"metapara_HELPS_certified": help_ok, "ortho_HURTS_certified": hurt_ok,
                      "flip_certified": help_ok and hurt_ok}
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(out, indent=2))
    print(f"\nFLIP  meta/para HELPS certified={help_ok}   ortho HURTS certified={hurt_ok}")
    print(f"wrote {a.out_json}")


if __name__ == "__main__":
    main()
