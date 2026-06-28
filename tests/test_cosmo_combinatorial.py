import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader
import tgnn_solv.model as model_mod
from tgnn_solv.layers import make_temperature_features
from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer


def _readouts(trainer, loader):
    """Run the encoder on one batch to get solute/solvent readout vectors."""
    model = trainer.model
    sol_batch, slv_batch, targets = trainer._move_batch_to_device(next(iter(loader)))
    enc_t = model._encoder_temp_features(make_temperature_features(targets["T"]))
    _, gp_sol, _, _ = model._encode_and_readout(sol_batch, "solute", temp_feat=enc_t)
    _, gp_slv, _, _ = model._encode_and_readout(slv_batch, "solvent", temp_feat=enc_t)
    return gp_sol["value"], gp_slv["value"]


def test_conversion_constant_value():
    assert abs(model_mod._CM3_PER_MOL_TO_A3 - 1.660539) < 1e-3


def test_wire_volume_off_passes_none():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    trainer.cfg.cosmo_sac_wire_volume = False
    g_sol, g_slv = _readouts(trainer, loader)
    params = trainer.model._build_sigma_activity_params(g_sol, g_slv)
    assert params["V_solute"] is None and params["V_solvent"] is None


def test_wire_volume_on_passes_detached_angstrom3():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    trainer.cfg.cosmo_sac_wire_volume = True
    g_sol, g_slv = _readouts(trainer, loader)
    params = trainer.model._build_sigma_activity_params(g_sol, g_slv)
    V2, V1 = params["V_solute"], params["V_solvent"]
    assert V2 is not None and V1 is not None
    # detached: the size factor must not carry grad into the solubility loss
    assert not V2.requires_grad and not V1.requires_grad
    # Angstrom^3/molecule magnitude sanity (V_m head floored at 30 cm^3/mol -> ~50 A^3 min)
    assert float(V2.min()) > 40.0 and float(V2.max()) < 2000.0
    # equals head_aux V_m * conversion constant
    vm = trainer.model.head_aux(g_sol)["V_m"].detach() * model_mod._CM3_PER_MOL_TO_A3
    assert torch.allclose(V2, vm, atol=1e-4)


def _layer():
    return CosmoSacLayer(TGNNSolvConfig())


def test_combinatorial_zero_for_identical_components():
    layer = _layer()
    A = torch.tensor([100.0])
    V = torch.tensor([120.0])
    x2 = torch.tensor([0.3])
    # solute == solvent (same r, q) -> no size/shape mismatch -> SG term ~ 0
    lng_c = layer._combinatorial_ln_gamma2(A, A, V, V, x2)
    assert torch.allclose(lng_c, torch.zeros_like(lng_c), atol=1e-5)


def test_combinatorial_finite_and_nonzero_for_asymmetric_pair():
    layer = _layer()
    A2 = torch.tensor([60.0])
    A1 = torch.tensor([300.0])
    V2 = torch.tensor([50.0])
    V1 = torch.tensor([400.0])
    x2 = torch.tensor([1e-4])  # near infinite dilution
    lng_c = layer._combinatorial_ln_gamma2(A2, A1, V2, V1, x2)
    assert torch.isfinite(lng_c).all()
    assert float(lng_c.abs().max()) > 1e-3  # a genuine size effect


def test_ln_gamma2_changes_when_volume_wired():
    layer = _layer()  # use_combinatorial defaults True
    g = layer.sigma_grid
    p2 = torch.softmax(-((g - 0.005) ** 2) / 2e-5, dim=0).unsqueeze(0) * 60.0
    p1 = torch.softmax(-(g**2) / 2e-5, dim=0).unsqueeze(0) * 300.0
    A2 = p2.sum(-1)
    A1 = p1.sum(-1)
    V2 = torch.tensor([50.0])
    V1 = torch.tensor([400.0])
    x2 = torch.tensor([1e-3])
    x1 = 1.0 - x2
    T = torch.tensor([298.15])
    res_only = layer.ln_gamma_2(x1, x2, p2, p1, A2, A1, None, None, T)
    with_sg = layer.ln_gamma_2(x1, x2, p2, p1, A2, A1, V2, V1, T)
    assert not torch.allclose(res_only, with_sg)  # SG term contributes
