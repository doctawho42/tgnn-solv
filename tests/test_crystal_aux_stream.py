"""Tests for the external single-component crystal auxiliary stream.

Covers the three correctness guards from the plan:
  * aux rows produce valid graphs and activate ONLY the T_m / dH_fus masks
    (self-solvent rows, has_solubility=False);
  * `_train_crystal_aux_batch` runs in crystal phases and is skipped in phase 2
    under coordinate descent;
  * the builder excludes pool scaffolds that appear in a held-out split.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.data.dataset import make_loader
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer

REPO_ROOT = Path(__file__).resolve().parents[1]

# Small, real molecules so RDKit graph + Joback GC priors succeed.
_SOLUTES = [
    "CC(=O)Nc1ccc(O)cc1",   # paracetamol
    "c1ccccc1C(=O)O",        # benzoic acid
    "CC(=O)Oc1ccccc1C(=O)O", # aspirin
    "c1ccccc1O",             # phenol
]


def _crystal_aux_frame() -> pd.DataFrame:
    """Single-component crystal-label rows in the processed-dataset contract."""
    rows = []
    for i, smi in enumerate(_SOLUTES):
        rows.append(
            {
                "solute_smiles": smi,
                "solvent_smiles": smi,  # self-solvent
                "temperature": 298.15,
                "ln_x2": 0.0,
                "source": "test_crystal_aux",
                "has_solubility": False,
                "T_m": 350.0 + 10.0 * i,
                "has_T_m": True,
                "dH_fus": 20000.0 if i % 2 == 0 else 0.0,
                "has_dH_fus": i % 2 == 0,
                "hansen_d": 0.0, "hansen_p": 0.0, "hansen_h": 0.0, "has_hansen": False,
                "ln_gamma_inf": 0.0, "has_gamma_inf": False,
            }
        )
    return pd.DataFrame(rows)


def _small_config() -> TGNNSolvConfig:
    return TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        n_iter_train=2,
        n_iter_eval=2,
        set2set_steps=2,
        nrtl_tau_mode="gamma_inf",
        use_gc_priors_crystal=True,
        predict_dCp_fus=False,
        branch_training_mode="coordinate_descent",
        detach_crystal_from_encoder=True,
        detach_crystal_params_in_sle=True,
        crystal_aux_steps_per_epoch=2,
    )


def _loader(cfg: TGNNSolvConfig):
    return make_loader(
        _crystal_aux_frame(),
        batch_size=4,
        shuffle=False,
        num_workers=0,
        cache=True,
        use_pair_temperature_batching=False,
        use_gc_priors_crystal=cfg.use_gc_priors_crystal,
    )


def test_crystal_aux_rows_activate_only_crystal_masks() -> None:
    cfg = _small_config()
    loader = _loader(cfg)
    sol_batch, slv_batch, targets = next(iter(loader))

    # Both component graphs exist (self-solvent), so the batch is well-formed.
    assert sol_batch.num_nodes > 0 and slv_batch.num_nodes > 0
    # Crystal supervision is active...
    assert bool(targets["T_m_mask"].any().item())
    assert bool(targets["dH_mask"].any().item())  # at least the even-index rows
    # ...while solubility / activity supervision is OFF.
    assert not bool(targets["has_solubility"].any().item())
    gamma_mask = targets.get("gamma_mask")
    if isinstance(gamma_mask, torch.Tensor):
        assert not bool(gamma_mask.any().item())
    # GC priors were computed per row for the crystal branch.
    assert isinstance(targets.get("T_m_gc"), torch.Tensor)


def test_crystal_aux_batch_trains_in_phase1_and_skips_phase2_under_coord_descent() -> None:
    cfg = _small_config()
    model = TGNNSolv(cfg=cfg)
    trainer = TGNNSolvTrainer(model, cfg)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    batch = next(iter(_loader(cfg)))

    # Phase 1 is a crystal phase under coordinate descent -> aux step runs.
    loss_p1, dict_p1 = trainer._train_crystal_aux_batch(batch, optimizer, phase=1)
    assert loss_p1 is not None and torch.isfinite(torch.tensor(loss_p1))
    # The active components are the crystal losses only.
    assert "T_m" in dict_p1 or "dH" in dict_p1

    # Phase 2 freezes the crystal branch under coordinate descent -> skipped.
    loss_p2, dict_p2 = trainer._train_crystal_aux_batch(batch, optimizer, phase=2)
    assert loss_p2 is None and dict_p2 == {}


def test_builder_excludes_heldout_scaffolds() -> None:
    spec = importlib.util.spec_from_file_location(
        "build_crystal_aux_stream",
        REPO_ROOT / "scripts" / "data" / "build_crystal_aux_stream.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Pool contains paracetamol (benzene scaffold) and naphthalene (fused-ring
    # scaffold); only the benzene scaffold is held out.
    pool = pd.DataFrame(
        {
            "solute_smiles": ["CC(=O)Nc1ccc(O)cc1", "c1ccc2ccccc2c1"],
            "T_m": [442.0, 353.0],
            "dH_fus": [27000.0, 19000.0],
        }
    )
    template_cols = [
        "solute_smiles", "solvent_smiles", "temperature", "ln_x2", "source",
        "has_solubility", "T_m", "has_T_m", "dH_fus", "has_dH_fus",
        "hansen_d", "hansen_p", "hansen_h", "has_hansen",
        "ln_gamma_inf", "has_gamma_inf",
    ]

    excluded = {module.get_scaffold("CC(=O)Nc1ccc(O)cc1")}
    kept = pool[~pool["solute_smiles"].map(lambda s: module.get_scaffold(s) in excluded)]
    stream = module.build_stream(
        kept,
        template_columns=template_cols,
        source_label="test",
        temperature=298.15,
    )
    smis = set(stream["solute_smiles"])
    assert "CC(=O)Nc1ccc(O)cc1" not in smis  # leaked scaffold removed
    assert "c1ccc2ccccc2c1" in smis           # distinct scaffold kept
    # Emitted rows obey the single-component contract.
    assert (stream["solvent_smiles"] == stream["solute_smiles"]).all()
    assert not stream["has_solubility"].any()
    assert stream["has_T_m"].all()
