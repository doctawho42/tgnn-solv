#!/usr/bin/env python3
"""Trained encoder->closure vs DirectGNN comparison on pKa (referee M3).

The pKa second domain (sections/pka-domain.tex) established that the *decomposition* transfers;
the trained-model paradox and physics tax were left to future work. This is that comparison,
mirroring the solubility setup with a matched control:

  physics arm : shared graph encoder -> predicted Hammett sigma_hat -> FIXED LFER closure
                g(sigma) = pKa0 - rho * sigma_hat   (pKa0, rho are the per-scaffold constants)
  direct arm  : the same encoder -> a free pKa head (no closure) -- the matched control
  sigma-oracle: the fixed LFER on the TRUE tabulated sigma (deterministic, no training)

On a Bemis-Murcko scaffold split of the OPERA Hammett-amenable subset. Outputs test MAE per
arm and the grounding gap (oracle vs learned physics), i.e. the trained-model operating point
for the phase diagram. Reuses the validated Hammett assignment (assign_hammett_sigma) and the
SDF loader from run_pka_real_decomposition.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/experiments/run_pka_trained_comparison.py \
        --sdf <path>/pKa_QR.sdf --device cuda --out-json results/pka_hammett/trained_comparison.json
    # CPU smoke (wiring only): add  --smoke
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import torch
import torch.nn as nn
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GINConv, global_mean_pool

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent / "analysis"

ATOMS = [6, 7, 8, 9, 15, 16, 17, 35, 53]   # C N O F P S Cl Br I; else "other"


def _load_real_decomp():
    spec = importlib.util.spec_from_file_location(
        "pka_real", ANALYSIS / "run_pka_real_decomposition.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _atom_feats(atom):
    z = atom.GetAtomicNum()
    onehot = [int(z == a) for a in ATOMS] + [int(z not in ATOMS)]
    return onehot + [
        atom.GetTotalDegree() / 4.0,
        atom.GetFormalCharge(),
        int(atom.GetIsAromatic()),
        int(atom.IsInRing()),
        atom.GetTotalNumHs() / 4.0,
    ]


def _to_graph(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or mol.GetNumAtoms() == 0:
        return None
    x = torch.tensor([_atom_feats(a) for a in mol.GetAtoms()], dtype=torch.float)
    src, dst = [], []
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        src += [i, j]; dst += [j, i]
    edge_index = torch.tensor([src, dst], dtype=torch.long) if src else torch.zeros((2, 0), dtype=torch.long)
    return Data(x=x, edge_index=edge_index)


def build_dataset(mod, sdf):
    recs, _ = mod.load_records(Path(sdf), mod._load_builder())
    data = []
    for r in recs:
        g = _to_graph(r["smiles"])
        if g is None:
            continue
        g.pka = torch.tensor([r["pka"]], dtype=torch.float)
        g.pka0 = torch.tensor([r["pka0"]], dtype=torch.float)
        g.rho = torch.tensor([r["rho"]], dtype=torch.float)
        g.sigma = torch.tensor([r["sigma"]], dtype=torch.float)
        g.g_oracle = torch.tensor([r["g"]], dtype=torch.float)   # fixed LFER on TRUE sigma
        g.fidelity = r["bin"]                                    # high_F (clean meta/para) | low_F (ortho)
        g.scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=Chem.MolFromSmiles(r["smiles"])) or "none"
        data.append(g)
    return data


class Encoder(nn.Module):
    def __init__(self, in_dim, hid, layers):
        super().__init__()
        self.convs = nn.ModuleList()
        d = in_dim
        for _ in range(layers):
            self.convs.append(GINConv(nn.Sequential(
                nn.Linear(d, hid), nn.ReLU(), nn.Linear(hid, hid))))
            d = hid
        self.hid = hid

    def forward(self, x, edge_index, batch):
        for conv in self.convs:
            x = torch.relu(conv(x, edge_index))
        return global_mean_pool(x, batch)


class PhysicsGNN(nn.Module):
    """encoder -> sigma_hat -> pKa = g_oracle_intercept... uses fixed LFER via (pka0,rho)."""
    def __init__(self, in_dim, hid, layers):
        super().__init__()
        self.enc = Encoder(in_dim, hid, layers)
        self.head = nn.Sequential(nn.Linear(hid, hid), nn.ReLU(), nn.Linear(hid, 1))

    def forward(self, d, pka0, rho):
        z = self.enc(d.x, d.edge_index, d.batch)
        sigma_hat = self.head(z).squeeze(-1)
        return pka0 - rho * sigma_hat            # fixed LFER closure


class DirectGNN(nn.Module):
    def __init__(self, in_dim, hid, layers):
        super().__init__()
        self.enc = Encoder(in_dim, hid, layers)
        self.head = nn.Sequential(nn.Linear(hid, hid), nn.ReLU(), nn.Linear(hid, 1))

    def forward(self, d, *_):
        z = self.enc(d.x, d.edge_index, d.batch)
        return self.head(z).squeeze(-1)


def scaffold_split(data, seed, test_frac=0.2):
    from collections import defaultdict
    groups = defaultdict(list)
    for i, g in enumerate(data):
        groups[g.scaffold].append(i)
    scaffs = sorted(groups, key=lambda s: (-len(groups[s]), s))
    rng = np.random.default_rng(seed)
    rng.shuffle(scaffs)
    n_test = int(test_frac * len(data))
    test, train = [], []
    for s in scaffs:
        (test if len(test) < n_test else train).extend(groups[s])
    return train, test


def run_arm(model, train_loader, test_data, pka0_t, rho_t, device, epochs, lr):
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    lossf = nn.L1Loss()
    model.train()
    for _ in range(epochs):
        for batch in train_loader:
            batch = batch.to(device)
            opt.zero_grad()
            pred = model(batch, batch.pka0.squeeze(-1), batch.rho.squeeze(-1))
            loss = lossf(pred, batch.pka.squeeze(-1))
            loss.backward(); opt.step()
    model.eval()
    with torch.no_grad():
        loader = DataLoader(test_data, batch_size=256)
        errs = []
        for batch in loader:
            batch = batch.to(device)
            pred = model(batch, batch.pka0.squeeze(-1), batch.rho.squeeze(-1))
            errs.append((pred - batch.pka.squeeze(-1)).abs().cpu())
        return float(torch.cat(errs).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sdf", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out-json", type=Path, default=Path("results/pka_hammett/trained_comparison.json"))
    args = ap.parse_args()
    if args.smoke:
        args.epochs, args.seeds = 2, [42]

    device = torch.device(args.device if torch.cuda.is_available() or args.device != "cuda" else "cpu")
    mod = _load_real_decomp()
    data = build_dataset(mod, args.sdf)
    in_dim = data[0].x.shape[1]
    print(f"dataset: {len(data)} graphs, in_dim={in_dim}, device={device}")

    def run_comparison(subset):
        arms = {}
        for name, Cls in (("physics_learned_sigma", PhysicsGNN), ("direct", DirectGNN)):
            maes = []
            for seed in args.seeds:
                torch.manual_seed(seed)
                tr_idx, te_idx = scaffold_split(subset, seed)
                tr = [subset[i] for i in tr_idx]; te = [subset[i] for i in te_idx]
                loader = DataLoader(tr, batch_size=128, shuffle=True)
                model = Cls(in_dim, args.hidden, args.layers).to(device)
                maes.append(run_arm(model, loader, te, None, None, device, args.epochs, args.lr))
            arms[name] = {"mae_mean": round(float(np.mean(maes)), 3),
                          "mae_sd": round(float(np.std(maes)), 3),
                          "per_seed": [round(x, 3) for x in maes]}
        _, te_idx = scaffold_split(subset, args.seeds[0])
        orc = np.array([float(subset[i].g_oracle) for i in te_idx])
        tru = np.array([float(subset[i].pka) for i in te_idx])
        arms["sigma_oracle_fixed_LFER"] = {"mae": round(float(np.mean(np.abs(orc - tru))), 3)}
        arms["physics_minus_direct"] = round(
            arms["physics_learned_sigma"]["mae_mean"] - arms["direct"]["mae_mean"], 3)
        return arms

    strata = {"all": data,
              "high_F (clean meta/para)": [g for g in data if g.fidelity == "high_F"],
              "low_F (ortho/hetero)": [g for g in data if g.fidelity == "low_F"]}
    res = {"epochs": args.epochs, "seeds": args.seeds, "strata": {}}
    for label, subset in strata.items():
        if len(subset) < 40:
            continue
        print(f"== stratum {label}: n={len(subset)} ==")
        res["strata"][label] = {"n": len(subset), "arms": run_comparison(subset)}

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(res, indent=2))
    for label, s in res["strata"].items():
        a = s["arms"]
        print(f"  {label:26s} n={s['n']:4d}  physics={a['physics_learned_sigma']['mae_mean']}  "
              f"direct={a['direct']['mae_mean']}  Delta={a['physics_minus_direct']:+.2f}  "
              f"oracle={a['sigma_oracle_fixed_LFER']['mae']}")
    print(f"wrote {args.out_json}")


if __name__ == "__main__":
    main()
