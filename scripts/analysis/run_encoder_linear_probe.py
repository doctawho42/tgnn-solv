#!/usr/bin/env python3
"""Linear-probe diagnostic: is the encoder limited by EXPRESSIVITY or TRANSFER?

We freeze the trained encoder, take its per-molecule readout for TRAIN-split and
TEST-split solutes, and linearly regress (ridge) the embedding onto interpretable
RDKit descriptors. We fit on train solutes and measure R^2 on train (in-sample)
and on held-out test solutes.

  * train R^2 LOW                  -> the channels do not even encode the
                                      descriptors: an EXPRESSIVITY problem
                                      (a new/bigger encoder could help).
  * train R^2 HIGH but test R^2 LOW -> the encoder encodes chemistry on the
                                      training distribution but it does NOT
                                      TRANSFER to new scaffolds: a distribution-
                                      shift problem (a new encoder won't fix it;
                                      pretraining / better inputs / coverage will).

This settles the "should we design a new graph encoder?" question with numbers.

    python scripts/analysis/run_encoder_linear_probe.py \
        --checkpoint checkpoints/proxy/tgnn_mpnn.pt --model-type tgnn \
        --train-data notebooks/data/processed/train.csv \
        --test-data  notebooks/data/processed/test.csv \
        --out-json results/encoder_probe/tgnn_mpnn.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))
import _bootstrap  # noqa: F401

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, rdMolDescriptors
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from tgnn_solv.data.dataset import make_loader
from tgnn_solv.inference import load_directgnn_model, load_model

# Curated interpretable descriptors (the probe targets).
_DESCRIPTORS: dict[str, Any] = {
    "MolWt": Descriptors.MolWt,
    "MolLogP": Crippen.MolLogP,
    "TPSA": rdMolDescriptors.CalcTPSA,
    "NumHDonors": rdMolDescriptors.CalcNumHBD,
    "NumHAcceptors": rdMolDescriptors.CalcNumHBA,
    "NumRotatableBonds": rdMolDescriptors.CalcNumRotatableBonds,
    "FractionCSP3": rdMolDescriptors.CalcFractionCSP3,
    "NumAromaticRings": rdMolDescriptors.CalcNumAromaticRings,
    "NumRings": rdMolDescriptors.CalcNumRings,
    "NumHeteroatoms": rdMolDescriptors.CalcNumHeteroatoms,
    "LabuteASA": rdMolDescriptors.CalcLabuteASA,
    "NumAliphaticRings": rdMolDescriptors.CalcNumAliphaticRings,
    "NHOHCount": Descriptors.NHOHCount,
    "NOCount": Descriptors.NOCount,
    "HeavyAtomCount": Descriptors.HeavyAtomCount,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--model-type", choices=["tgnn", "direct"], default="tgnn")
    p.add_argument("--train-data", default="notebooks/data/processed/train.csv")
    p.add_argument("--test-data", default="notebooks/data/processed/test.csv")
    p.add_argument("--device", default="cpu")
    p.add_argument("--max-solutes", type=int, default=800, help="Cap per split.")
    p.add_argument("--ridge-alpha", type=float, default=10.0)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--out-json", required=True)
    return p.parse_args()


def _unique_solutes(csv: str, cap: int) -> list[str]:
    s = pd.read_csv(csv, usecols=lambda c: c == "solute_smiles", low_memory=False)
    uniq = list(dict.fromkeys(s["solute_smiles"].dropna().astype(str)))
    return uniq[:cap]


@torch.no_grad()
def _embeddings(model, cfg, smiles: list[str], device: str, batch_size: int) -> tuple[np.ndarray, list[str]]:
    """Per-molecule encoder readout for each SMILES (self-solvent rows)."""
    df = pd.DataFrame({
        "solute_smiles": smiles, "solvent_smiles": smiles, "temperature": 298.15,
        "ln_x2": 0.0, "source": "probe", "has_solubility": False,
        "T_m": 0.0, "has_T_m": False, "dH_fus": 0.0, "has_dH_fus": False,
        "hansen_d": 0.0, "hansen_p": 0.0, "hansen_h": 0.0, "has_hansen": False,
        "ln_gamma_inf": 0.0, "has_gamma_inf": False,
    })
    loader = make_loader(
        df, batch_size=batch_size, shuffle=False, num_workers=0, cache=True,
        drop_last=False, use_pair_temperature_batching=False,
        use_morgan_features=cfg.use_morgan_features,
        morgan_radius=cfg.morgan_radius, morgan_n_bits=cfg.morgan_n_bits,
        use_descriptor_augmentation=cfg.use_descriptor_augmentation,
        use_ionic_features=cfg.use_ionic_features,
        use_descriptor_priors=cfg.use_descriptor_priors,
        use_group_priors=cfg.requires_group_prior_features,
        use_gc_priors_crystal=cfg.use_gc_priors_crystal,
        use_gasteiger_charges=cfg.use_gasteiger_charges,
        use_phys_edge_features=cfg.use_phys_edge_features,
        explicit_h_small_molecules=cfg.explicit_h_small_molecules,
        explicit_h_max_heavy_atoms=cfg.explicit_h_max_heavy_atoms,
    )
    embs, smis = [], []
    for sol_b, _slv_b, targets in loader:
        sol_b = sol_b.to(device)
        _, payload, _, _ = model._encode_and_readout(sol_b, "solute")
        embs.append(payload["value"].detach().cpu().numpy())
        smis.extend(targets.get("solute_smiles", [""] * payload["value"].shape[0]))
    return np.concatenate(embs, axis=0), smis


def _descriptor_matrix(smiles: list[str]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    names = list(_DESCRIPTORS)
    rows, keep = [], []
    for i, smi in enumerate(smiles):
        mol = Chem.MolFromSmiles(str(smi))
        if mol is None:
            continue
        try:
            rows.append([float(_DESCRIPTORS[n](mol)) for n in names])
            keep.append(i)
        except Exception:
            continue
    return np.asarray(rows, dtype=float), np.asarray(keep, dtype=int), names


def main() -> None:
    args = parse_args()
    loader_fn = load_directgnn_model if args.model_type == "direct" else load_model
    model, cfg = loader_fn(args.checkpoint, device=args.device)
    model.eval()

    tr_smis = _unique_solutes(args.train_data, args.max_solutes)
    te_smis = _unique_solutes(args.test_data, args.max_solutes)

    Xtr, tr_smis = _embeddings(model, cfg, tr_smis, args.device, args.batch_size)
    Xte, te_smis = _embeddings(model, cfg, te_smis, args.device, args.batch_size)
    Dtr, ktr, names = _descriptor_matrix(tr_smis)
    Dte, kte, _ = _descriptor_matrix(te_smis)
    Xtr, Xte = Xtr[ktr], Xte[kte]

    xs = StandardScaler().fit(Xtr)
    Xtr_s, Xte_s = xs.transform(Xtr), xs.transform(Xte)
    ds = StandardScaler().fit(Dtr)
    Dtr_s, Dte_s = ds.transform(Dtr), ds.transform(Dte)

    per_desc = {}
    train_r2, test_r2 = [], []
    for j, name in enumerate(names):
        reg = Ridge(alpha=args.ridge_alpha).fit(Xtr_s, Dtr_s[:, j])
        r2_tr = float(r2_score(Dtr_s[:, j], reg.predict(Xtr_s)))
        r2_te = float(r2_score(Dte_s[:, j], reg.predict(Xte_s)))
        per_desc[name] = {"train_r2": r2_tr, "test_r2": r2_te}
        train_r2.append(r2_tr)
        test_r2.append(r2_te)

    med_tr, med_te = float(np.median(train_r2)), float(np.median(test_r2))
    if med_tr < 0.5:
        verdict = "EXPRESSIVITY-limited: descriptors are poorly encoded even on train."
    elif med_tr - med_te > 0.25:
        verdict = "TRANSFER-limited: encodes chemistry on train but it does not generalize to test scaffolds."
    else:
        verdict = "Encoder reads descriptors comparably on train and test (neither obviously limiting)."

    out = {
        "checkpoint": str(Path(args.checkpoint).resolve()),
        "model_type": args.model_type,
        "n_train_solutes": int(Xtr.shape[0]), "n_test_solutes": int(Xte.shape[0]),
        "embedding_dim": int(Xtr.shape[1]),
        "median_train_r2": med_tr, "median_test_r2": med_te,
        "median_gap_train_minus_test": med_tr - med_te,
        "verdict": verdict,
        "per_descriptor": per_desc,
    }
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_descriptor"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
