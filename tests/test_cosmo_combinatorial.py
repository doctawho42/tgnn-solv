import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader
import tgnn_solv.model as model_mod
from tgnn_solv.layers import make_temperature_features


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
