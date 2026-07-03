"""Tests for the external sigma-profile auxiliary supervision pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import make_loader
from tgnn_solv.loss import sigma_profile_emd_loss
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer

REPO = Path(__file__).resolve().parents[1]
N_BINS = 51
_SOLUTES = ["CC(=O)Nc1ccc(O)cc1", "c1ccc2ccccc2c1", "CCO", "CC(=O)Oc1ccccc1C(=O)O"]


def _profile(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.linspace(-0.025, 0.025, N_BINS)
    p = np.exp(-0.5 * ((x - rng.uniform(-0.01, 0.01)) / 0.004) ** 2)
    p += 0.3 * np.exp(-0.5 * ((x - rng.uniform(-0.02, 0.02)) / 0.003) ** 2)
    return p / p.sum()


def _sigma_stream_frame() -> pd.DataFrame:
    rows = []
    for i, smi in enumerate(_SOLUTES):
        prof = _profile(i)
        row = {
            "solute_smiles": smi, "solvent_smiles": smi, "temperature": 298.15,
            "ln_x2": 0.0, "source": "t", "has_solubility": False,
            "T_m": 0.0, "has_T_m": False, "dH_fus": 0.0, "has_dH_fus": False,
            "hansen_d": 0.0, "hansen_p": 0.0, "hansen_h": 0.0, "has_hansen": False,
            "ln_gamma_inf": 0.0, "has_gamma_inf": False,
            "has_sigma_profile": True, "sigma_area": 250.0 + 10.0 * i,
        }
        for b in range(N_BINS):
            row[f"sigma_p_{b}"] = float(prof[b])
        rows.append(row)
    return pd.DataFrame(rows)


def _cosmo_cfg() -> TGNNSolvConfig:
    return TGNNSolvConfig(
        activity_model="cosmo_sac", hidden_dim=32, n_gnn_layers=2,
        n_cross_attn_layers=1, n_attn_heads=4, pair_dim=64,
        solvent_moe_hidden=64, solvent_type_emb_dim=8,
        n_iter_train=2, n_iter_eval=2, set2set_steps=2,
        cosmo_sac_gamma_iter_train=4, cosmo_sac_gamma_iter_eval=4,
        sigma_aux_steps_per_epoch=2,
    )


def test_emd_loss_zero_for_identical_and_positive_for_shifted() -> None:
    p = torch.tensor([_profile(0)], dtype=torch.float)
    q = torch.tensor([_profile(5)], dtype=torch.float)
    area = torch.tensor([250.0])
    mask = torch.tensor([True])
    same = sigma_profile_emd_loss(p, p, area, area, mask)
    diff = sigma_profile_emd_loss(p, q, area, area, mask)
    assert float(same) < 1e-6
    assert float(diff) > 0.0


def test_sigma_stream_loads_with_mask_and_target() -> None:
    cfg = _cosmo_cfg()
    loader = make_loader(_sigma_stream_frame(), batch_size=4, shuffle=False,
                         num_workers=0, cache=True, use_pair_temperature_batching=False)
    _, _, targets = next(iter(loader))
    assert bool(targets["sigma_profile_mask"].all())
    assert targets["sigma_profile_target"].shape == (4, N_BINS)
    assert not bool(targets["has_solubility"].any())


def test_sigma_aux_batch_trains_head_and_skips_when_disabled() -> None:
    cfg = _cosmo_cfg()
    model = TGNNSolv(cfg=cfg)
    trainer = TGNNSolvTrainer(model, cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    batch = next(iter(make_loader(_sigma_stream_frame(), batch_size=4, shuffle=False,
                                  num_workers=0, cache=True,
                                  use_pair_temperature_batching=False)))
    loss, d = trainer._train_sigma_aux_batch(batch, opt, phase=1)
    assert loss is not None and np.isfinite(loss)
    grads = [p.grad for p in model.head_sigma.parameters() if p.grad is not None]
    assert grads and all(torch.isfinite(g).all() for g in grads)

    # An NRTL model has no sigma head -> the aux step is a no-op.
    nrtl_model = TGNNSolv(cfg=TGNNSolvConfig(hidden_dim=32, n_gnn_layers=2,
                                             n_cross_attn_layers=1, n_attn_heads=4,
                                             pair_dim=64, solvent_moe_hidden=64,
                                             solvent_type_emb_dim=8, set2set_steps=2))
    nrtl_trainer = TGNNSolvTrainer(nrtl_model, TGNNSolvConfig())
    loss2, _ = nrtl_trainer._train_sigma_aux_batch(batch, opt, phase=1)
    assert loss2 is None


def test_builder_runs_and_guards_scaffolds(tmp_path: Path) -> None:
    # Synthetic artifact incl. a molecule whose scaffold is in the test split.
    art = tmp_path / "sigma_profiles.csv"
    rows = []
    for i, smi in enumerate(_SOLUTES):
        prof = _profile(i)
        r = {"smiles": smi, "sigma_area": 250.0}
        r.update({f"sigma_p_{b}": float(prof[b]) for b in range(N_BINS)})
        rows.append(r)
    pd.DataFrame(rows).to_csv(art, index=False)

    excl = tmp_path / "test.csv"
    pd.DataFrame({"solute_smiles": ["CC(=O)Nc1ccc(O)cc1"]}).to_csv(excl, index=False)
    out = tmp_path / "sigma_train.csv"
    summ = tmp_path / "summary.json"
    res = subprocess.run(
        [sys.executable, "scripts/data/build_sigma_profile_aux_stream.py",
         "--sigma-csv", str(art),
         "--template-csv", "notebooks/data/processed/train.csv",
         "--output-csv", str(out), "--summary-json", str(summ),
         "--exclude-scaffolds-from", str(excl)],
        cwd=REPO, capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stderr
    built = pd.read_csv(out)
    smis = set(built["solute_smiles"])
    assert "CC(=O)Nc1ccc(O)cc1" not in smis          # leaked scaffold excluded
    assert (built["solvent_smiles"] == built["solute_smiles"]).all()  # self-solvent
    assert built["has_sigma_profile"].all()
    assert all(f"sigma_p_{b}" in built.columns for b in range(N_BINS))
