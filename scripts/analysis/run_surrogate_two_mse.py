#!/usr/bin/env python3
"""The direct cancellation check for the compensating-surrogate reading (paper sec:surrogate).

The claim that the end-to-end drift CANCELS part of B_closure predicts
MSE(m, g(sigma_hat)) < MSE(m, g(z*)) on the matched activity corner. That comparison was
previously only inferred. It is run here on the checkpoints retained locally:

  * the SLE-trained (end-to-end) COSMO-SAC checkpoint, and
  * a grounded warm-up checkpoint (phase-1 only, sigma supervision on the grounding pool),

with the cavity area held at its VT-2005 reference value in every arm, so that only the
PROFILE SHAPE -- the drift quantity of sec:surrogate -- varies between arms.

Caveats recorded in the output and in the paper: neither checkpoint is one of the three
surrogate seeds (those were not retained); the 44 probe molecules all lie inside the
sigma-grounding pool, so the warm-up arm's profiles are an in-sample fit to z*.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_surrogate_two_mse.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402

N_BINS = 51
OUT = ROOT / "results" / "compensation" / "two_mse_check.json"
ARMS = (("sle_trained_end_to_end", ROOT / "checkpoints/cosmo_sac/tgnn_cosmo.pt"),
        ("grounded_warmup_phase1_only", ROOT / "results/closure_fix/ckpt/arm_base.pt"))


def canon(s):
    mol = Chem.MolFromSmiles(str(s))
    return Chem.MolToSmiles(mol) if mol is not None else None


def ref_table(path):
    df = pd.read_csv(path)
    cols = [f"sigma_p_{i}" for i in range(N_BINS)]
    smi = "smiles" if "smiles" in df.columns else df.columns[0]
    t = {}
    for _, d in df.iterrows():
        k = canon(d[smi])
        if k is None or k in t:
            continue
        p = np.array([float(d[c]) for c in cols])
        if p.sum() > 0:
            t[k] = (p, float(d.get("sigma_area", p.sum())))
    return t


def predict_shapes(model, smiles):
    from torch_geometric.data import Batch
    from tgnn_solv.inference import _smiles_to_graph_for_model
    graphs = [_smiles_to_graph_for_model(s, model) for s in smiles]
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(graphs), 64):
            b = Batch.from_data_list(graphs[i:i + 64])
            _, payload, _, _ = model._encode_and_readout(b, "solute", temp_feat=None)
            out.append(model.head_sigma(payload["value"])["p_shape"].cpu().numpy())
    return np.concatenate(out, 0)


def main() -> int:
    tab = ref_table(ROOT / "results/sigma_profile_artifact/sigma_profiles.csv")
    md = pd.read_csv(ROOT / "results/b_insuff/matched_pairs.csv")
    mols = [s for s in sorted(set(md.solute_key) | set(md.solvent_key)) if canon(s) in tab]
    m = md["m"].to_numpy(float)
    layer = CosmoSacLayer(cfg=None).eval()

    def mse(shapes):
        def prof(k):
            p_ref, A = tab[canon(k)]
            return shapes[canon(k)] * A, A
        P2, A2 = zip(*[prof(k) for k in md.solute_key])
        P1, A1 = zip(*[prof(k) for k in md.solvent_key])
        tt = lambda x: torch.tensor(np.asarray(x), dtype=torch.float)
        with torch.no_grad():
            g = layer.ln_gamma_inf(tt(P2), tt(P1), tt(A2), tt(A1), None, None,
                                   torch.full((len(md),), 298.15)).numpy()
        return float(np.mean((m - g) ** 2))

    ref = {canon(s): tab[canon(s)][0] / tab[canon(s)][0].sum() for s in mols}
    out = {"n_pairs": int(len(md)), "n_molecules": len(mols), "convention": "residual-only",
           "note": "cavity area held at the VT-2005 reference value in every arm; only the "
                   "profile shape varies. Probe molecules all lie inside the sigma-grounding pool.",
           "mse_reference_zstar": round(mse(ref), 4), "arms": {}}
    for tag, ck in ARMS:
        if not Path(ck).exists():
            out["arms"][tag] = {"status": "checkpoint not present"}
            continue
        from tgnn_solv.inference import load_model
        model, _ = load_model(str(ck), device=torch.device("cpu"))
        S = predict_shapes(model, mols)
        hat = {canon(s): S[i] / max(S[i].sum(), 1e-12) for i, s in enumerate(mols)}
        dev = float(np.mean([np.linalg.norm(hat[canon(s)] - ref[canon(s)]) /
                             np.linalg.norm(ref[canon(s)]) for s in mols]))
        out["arms"][tag] = {"checkpoint": str(ck), "mse_learned_sigma_hat": round(mse(hat), 4),
                            "relative_shape_deviation_from_reference": round(dev, 4)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"[saved] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
