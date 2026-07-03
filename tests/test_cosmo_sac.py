"""Tests for the differentiable COSMO-SAC activity layer and its solver wiring."""

from __future__ import annotations

import sys

import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer
from tgnn_solv.solver import SLESolver


def _gauss(grid: torch.Tensor, center: float, width: float, area: float) -> torch.Tensor:
    p = torch.exp(-0.5 * ((grid - center) / width) ** 2)
    return (p / p.sum() * area).unsqueeze(0)


def _profiles(layer: CosmoSacLayer):
    grid = layer.sigma_grid
    nonpolar = _gauss(grid, 0.0, 0.004, 300.0)
    polar = (
        _gauss(grid, 0.0, 0.004, 150.0)
        + _gauss(grid, 0.015, 0.003, 75.0)
        + _gauss(grid, -0.015, 0.003, 75.0)
    )
    return nonpolar, polar


def test_identical_components_give_zero_activity() -> None:
    layer = CosmoSacLayer(None).eval()
    nonpolar, _ = _profiles(layer)
    A = torch.tensor([300.0])
    V = torch.tensor([150.0])
    T = torch.tensor([298.15])
    lng = layer.ln_gamma_inf(nonpolar, nonpolar, A, A, V, V, T)
    assert abs(float(lng)) < 1e-4


def test_dissimilar_components_give_positive_activity() -> None:
    layer = CosmoSacLayer(None).eval()
    nonpolar, polar = _profiles(layer)
    A = torch.tensor([300.0])
    V = torch.tensor([150.0])
    T = torch.tensor([298.15])
    lng = float(layer.ln_gamma_inf(polar, nonpolar, A, A, V, V, T))
    assert lng > 0.0


def test_layer_is_differentiable_wrt_profile() -> None:
    layer = CosmoSacLayer(None)
    nonpolar, polar = _profiles(layer)
    A = torch.tensor([300.0])
    V = torch.tensor([150.0])
    T = torch.tensor([298.15])
    p = polar.clone().requires_grad_(True)
    layer.ln_gamma_inf(p, nonpolar, A, A, V, V, T).backward()
    assert p.grad is not None
    assert bool(torch.isfinite(p.grad).all())
    assert float(p.grad.abs().sum()) > 0.0


def test_combinatorial_size_effect_finite_and_small() -> None:
    layer = CosmoSacLayer(None).eval()
    nonpolar, _ = _profiles(layer)
    grid = layer.sigma_grid
    big = _gauss(grid, 0.0, 0.004, 600.0)  # same chemistry, bigger molecule
    T = torch.tensor([298.15])
    lng = float(
        layer.ln_gamma_inf(
            nonpolar, big, torch.tensor([300.0]), torch.tensor([600.0]),
            torch.tensor([150.0]), torch.tensor([300.0]), T,
        )
    )
    assert abs(lng) < 5.0  # pure size/combinatorial effect stays modest


def _tiny_loader(cfg):
    import pandas as pd
    from tgnn_solv.data.dataset import make_loader
    rows = [
        {"solute_smiles": "CC(=O)Nc1ccc(O)cc1", "solvent_smiles": "CCO",
         "temperature": 298.15, "ln_x2": -3.0, "source": "t", "has_solubility": True,
         "T_m": 442.0, "has_T_m": True, "dH_fus": 27000.0, "has_dH_fus": True,
         "hansen_d": 0.0, "hansen_p": 0.0, "hansen_h": 0.0, "has_hansen": False,
         "ln_gamma_inf": 0.0, "has_gamma_inf": False},
        {"solute_smiles": "c1ccccc1C(=O)O", "solvent_smiles": "CO",
         "temperature": 310.0, "ln_x2": -2.0, "source": "t", "has_solubility": True,
         "T_m": 395.0, "has_T_m": True, "dH_fus": 18000.0, "has_dH_fus": True,
         "hansen_d": 0.0, "hansen_p": 0.0, "hansen_h": 0.0, "has_hansen": False,
         "ln_gamma_inf": 0.0, "has_gamma_inf": False},
    ]
    return make_loader(pd.DataFrame(rows), batch_size=2, shuffle=False, num_workers=0,
                       cache=True, use_pair_temperature_batching=False)


def _cosmo_model_cfg() -> TGNNSolvConfig:
    return TGNNSolvConfig(
        activity_model="cosmo_sac", hidden_dim=32, n_gnn_layers=2,
        n_cross_attn_layers=1, n_attn_heads=4, pair_dim=64,
        solvent_moe_hidden=64, solvent_type_emb_dim=8,
        n_iter_train=2, n_iter_eval=2, set2set_steps=2,
        cosmo_sac_gamma_iter_train=4, cosmo_sac_gamma_iter_eval=4,
    )


def test_model_cosmo_sac_forward_train_and_eval() -> None:
    from tgnn_solv.model import TGNNSolv
    cfg = _cosmo_model_cfg()
    model = TGNNSolv(cfg=cfg)
    assert model.head_nrtl is None and model.head_sigma is not None
    sol, slv, targets = next(iter(_tiny_loader(cfg)))
    for training in (True, False):
        model.train(training)
        out = model(sol, slv, targets["T"], targets=targets)
        assert torch.isfinite(out["ln_x2"]).all()
        assert bool((out["x2"] > 0).all())
        # activity params carry sigma-profiles, not NRTL tau
        assert "p_solute" in out["nrtl_params"]


def test_model_cosmo_sac_backward() -> None:
    from tgnn_solv.model import TGNNSolv
    cfg = _cosmo_model_cfg()
    model = TGNNSolv(cfg=cfg).train()
    sol, slv, targets = next(iter(_tiny_loader(cfg)))
    out = model(sol, slv, targets["T"], targets=targets)
    loss = out["ln_x2"].pow(2).mean()
    loss.backward()
    grads = [p.grad for p in model.head_sigma.parameters() if p.grad is not None]
    assert grads and all(torch.isfinite(g).all() for g in grads)


def test_solver_cosmo_sac_path_returns_valid_solubility() -> None:
    cfg = TGNNSolvConfig(activity_model="cosmo_sac")
    solver = SLESolver(cfg).eval()
    layer = solver.cosmo_sac_layer
    assert layer is not None
    nonpolar, polar = _profiles(layer)
    B = 1
    T = torch.tensor([298.15])
    fusion = {
        "T_m": torch.tensor([400.0]),
        "dH_fus": torch.tensor([20000.0]),
        "dCp_fus": torch.tensor([0.0]),
    }
    activity = {
        "p_solute": polar, "p_solvent": nonpolar,
        "A_solute": torch.tensor([300.0]), "A_solvent": torch.tensor([300.0]),
        "V_solute": torch.tensor([150.0]), "V_solvent": torch.tensor([150.0]),
        "alpha_12": torch.tensor([0.3]),  # ignored, kept for compat
    }
    out = solver(T, fusion, activity)
    assert torch.isfinite(out["ln_x2"]).all()
    assert bool((out["x2"] > 0).all() and (out["x2"] <= 1).all())
    assert torch.isfinite(out["ln_gamma_inf"]).all()
