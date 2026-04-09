"""Regression tests for the optional TIMP encoder path."""

from __future__ import annotations

import sys

import pytest
import torch
import torch.nn.functional as F
from torch_geometric.data import Batch

sys.path.insert(0, "src")

from tgnn_solv.baselines.direct_gnn import DirectGNN  # noqa: E402
from tgnn_solv.config import TGNNSolvConfig  # noqa: E402
from tgnn_solv.features import (  # noqa: E402
    graph_feature_spec_from_config,
    smiles_to_graph,
)
from tgnn_solv.layers import (  # noqa: E402
    GNNEncoder,
    SoluteSolventCrossAttention,
    TIMPEncoder,
)
from tgnn_solv.model import TGNNSolv  # noqa: E402


def make_timp_config(**overrides: object) -> TGNNSolvConfig:
    """Build a compact TIMP config for tests."""
    base = dict(
        hidden_dim=32,
        n_gnn_layers=2,
        encoder_type="timp",
        encoder_role_mode="shared_residual",
        encoder_role_specific_layers=1,
        use_gasteiger_charges=True,
        use_phys_edge_features=True,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        set2set_steps=2,
        dropout=0.0,
        use_solvent_moe=False,
        n_iter_train=2,
        n_iter_eval=2,
    )
    base.update(overrides)
    return TGNNSolvConfig(**base)


def make_graph(smiles: str, cfg: TGNNSolvConfig):
    """Build one graph using the config-driven TIMP feature flags."""
    graph = smiles_to_graph(
        smiles,
        use_gasteiger_charges=cfg.use_gasteiger_charges,
        use_phys_edge_features=cfg.use_phys_edge_features,
    )
    assert graph is not None
    return graph


def make_pair_batches(
    pairs: list[tuple[str, str, float]],
    cfg: TGNNSolvConfig,
) -> tuple[Batch, Batch, torch.Tensor]:
    """Create batched graph inputs for a list of `(solute, solvent, T)` pairs."""
    solute_graphs = [make_graph(solute, cfg) for solute, _, _ in pairs]
    solvent_graphs = [make_graph(solvent, cfg) for _, solvent, _ in pairs]
    temperatures = torch.tensor(
        [float(temperature) for _, _, temperature in pairs],
        dtype=torch.float32,
    )
    return (
        Batch.from_data_list(solute_graphs),
        Batch.from_data_list(solvent_graphs),
        temperatures,
    )


def test_gasteiger_charges() -> None:
    """Neutral molecules should expose finite folded heavy-atom Gasteiger charges."""
    cfg = make_timp_config()
    spec = graph_feature_spec_from_config(cfg)

    for smiles in ("CCO", "c1ccccc1", "O", "CC(=O)Nc1ccc(O)cc1"):
        graph = make_graph(smiles, cfg)
        charges = graph.x[:, spec.gasteiger_charge_idx]
        assert torch.isfinite(charges).all()
        assert abs(float(charges.sum())) < 1.0e-5


def test_phys_edge_features() -> None:
    """Physical edge features should highlight polar / H-bond-active ethanol bonds."""
    cfg = make_timp_config()
    ethanol = make_graph("CCO", cfg)
    benzene = make_graph("c1ccccc1", cfg)

    ethanol_phys = ethanol.edge_attr[:, -4:]
    benzene_phys = benzene.edge_attr[:, -4:]

    assert float(ethanol_phys[:, 0].max()) > 0.5  # delta_chi
    assert float(ethanol_phys[:, 3].max()) == pytest.approx(1.0)  # hbond_cap
    assert float(benzene_phys[:, 0].max()) == pytest.approx(0.0, abs=1.0e-8)
    assert float(benzene_phys[:, 3].max()) == pytest.approx(0.0, abs=1.0e-8)


def test_timp_forward() -> None:
    """A TIMP-backed TGNN model should run one full forward pass on a small batch."""
    torch.manual_seed(0)
    cfg = make_timp_config()
    model = TGNNSolv(cfg=cfg)
    solute_batch, solvent_batch, temperature = make_pair_batches(
        [("CCO", "O", 298.15), ("CCCCCC", "CCO", 310.0)],
        cfg,
    )

    output, intermediates = model(
        solute_batch,
        solvent_batch,
        temperature,
        return_intermediates=True,
    )

    assert output["ln_x2"].shape == (2,)
    assert torch.isfinite(output["ln_x2"]).all()
    assert torch.isfinite(intermediates["g_sol_disp_pre"]).all()
    assert torch.isfinite(intermediates["g_sol_polar_pre"]).all()


def test_timp_backward() -> None:
    """TIMP parameters should support a clean backward pass with finite gradients."""
    torch.manual_seed(0)
    cfg = make_timp_config()
    model = TGNNSolv(cfg=cfg)
    solute_batch, solvent_batch, temperature = make_pair_batches(
        [("CCO", "O", 298.15), ("CCN", "CCO", 315.0)],
        cfg,
    )

    output = model(solute_batch, solvent_batch, temperature)
    loss = output["ln_x2"].sum() + output["physics"]["ln_gamma_inf"].sum()
    loss.backward()

    grads = [
        parameter.grad
        for parameter in model.parameters()
        if parameter.grad is not None
    ]
    assert grads
    assert all(torch.isfinite(grad).all() for grad in grads)


def test_timp_channels_differ() -> None:
    """Dispersive and polar pooled channels should not collapse onto each other."""
    torch.manual_seed(0)
    cfg = make_timp_config()
    model = TGNNSolv(cfg=cfg)
    solute_batch, solvent_batch, temperature = make_pair_batches(
        [("CCO", "O", 298.15), ("CCCCCC", "O", 298.15)],
        cfg,
    )

    _, intermediates = model(
        solute_batch,
        solvent_batch,
        temperature,
        return_intermediates=True,
    )
    ethanol_cos = F.cosine_similarity(
        intermediates["g_sol_disp_pre"][0:1],
        intermediates["g_sol_polar_pre"][0:1],
    ).item()
    hexane_cos = F.cosine_similarity(
        intermediates["g_sol_disp_pre"][1:2],
        intermediates["g_sol_polar_pre"][1:2],
    ).item()

    assert ethanol_cos < 0.9
    assert hexane_cos < 0.9


def test_timp_reduces_to_mpnn() -> None:
    """With aligned random initialization, TIMP outputs should stay on the MPNN scale."""
    graphs = [smiles_to_graph("CCO"), smiles_to_graph("c1ccccc1")]
    assert all(graph is not None for graph in graphs)
    batch = Batch.from_data_list([graph for graph in graphs if graph is not None])

    torch.manual_seed(0)
    mpnn = GNNEncoder(35, 8, hidden_dim=32, n_layers=2)
    torch.manual_seed(0)
    cfg = make_timp_config(
        use_gasteiger_charges=False,
        use_phys_edge_features=False,
    )
    spec = graph_feature_spec_from_config(cfg)
    timp = TIMPEncoder(
        35,
        8,
        hidden_dim=32,
        n_layers=2,
        alpha_idx=spec.polarizability_idx,
        charge_idx=spec.gasteiger_charge_idx,
        dropout=0.0,
    )
    for layer in [*timp.shared_layers, *timp.solute_layers, *timp.solvent_layers]:
        with torch.no_grad():
            layer.w_disp.fill_(1.0)
            layer.b_disp.zero_()
            layer.phi_polar.load_state_dict(layer.phi_disp.state_dict())

    out_mpnn = mpnn(
        batch.x,
        batch.edge_index,
        batch.edge_attr,
        batch=batch.batch,
    )
    out_timp, _, _ = timp(
        batch.x,
        batch.edge_index,
        batch.edge_attr,
        batch=batch.batch,
    )
    norm_ratio = float(
        (out_timp.norm() / out_mpnn.norm().clamp_min(1.0e-8)).detach()
    )

    assert torch.isfinite(out_timp).all()
    assert 0.25 < norm_ratio < 4.0


def test_thermo_cross_attention() -> None:
    """Thermo-biased attention should match the standard path at beta=0 and differ otherwise."""
    torch.manual_seed(0)
    standard = SoluteSolventCrossAttention(
        16,
        4,
        use_thermo_cross_attention=False,
    )
    thermo = SoluteSolventCrossAttention(
        16,
        4,
        use_thermo_cross_attention=True,
    )
    shared_state = thermo.state_dict()
    for key, value in standard.state_dict().items():
        if key in shared_state and shared_state[key].shape == value.shape:
            shared_state[key] = value.clone()
    thermo.load_state_dict(shared_state, strict=False)
    standard.eval()
    thermo.eval()

    h_solute = torch.randn(2, 3, 16)
    h_solvent = torch.randn(2, 4, 16)
    solute_mask = torch.ones(2, 3, dtype=torch.bool)
    solvent_mask = torch.ones(2, 4, dtype=torch.bool)

    with torch.no_grad():
        thermo.beta.zero_()
        out_standard, weights_standard = standard(
            h_solute, h_solvent, solute_mask, solvent_mask
        )
        out_beta_zero, weights_beta_zero = thermo(
            h_solute, h_solvent, solute_mask, solvent_mask
        )
        thermo.beta.fill_(0.1)
        out_beta, weights_beta = thermo(
            h_solute, h_solvent, solute_mask, solvent_mask
        )

    assert torch.allclose(out_standard, out_beta_zero, atol=1.0e-6)
    assert torch.allclose(weights_standard, weights_beta_zero, atol=1.0e-6)
    assert not torch.allclose(out_standard, out_beta, atol=1.0e-6)
    assert not torch.allclose(weights_standard, weights_beta, atol=1.0e-6)


def test_gasteiger_edge_cases() -> None:
    """Charged / radical / single-atom molecules should stay finite under TIMP featurization."""
    cfg = make_timp_config()
    spec = graph_feature_spec_from_config(cfg)

    for smiles in ("[Na+]", "[Cl-]", "[CH3]", "O"):
        graph = make_graph(smiles, cfg)
        charges = graph.x[:, spec.gasteiger_charge_idx]
        assert graph.num_nodes >= 1
        assert torch.isfinite(graph.x).all()
        assert torch.isfinite(charges).all()


def test_timp_with_directgnn() -> None:
    """DirectGNN should accept the TIMP encoder as a drop-in backbone."""
    torch.manual_seed(0)
    cfg = make_timp_config()
    model = DirectGNN(cfg=cfg)
    solute_batch, solvent_batch, temperature = make_pair_batches(
        [("CCO", "O", 298.15), ("CCN", "CCO", 305.0)],
        cfg,
    )

    output = model(solute_batch, solvent_batch, temperature)

    assert output["ln_x2"].shape == (2,)
    assert torch.isfinite(output["ln_x2"]).all()
