import numpy as np
import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader
from tgnn_solv.sigma_oracle import load_sigma_profiles, build_oracle_tensors


def test_load_and_build_oracle_tensors(tmp_path):
    import pandas as pd
    n = 51
    row = {"smiles": "CCO", "sigma_area": 88.0}
    shape = np.full(n, 88.0 / n)
    for i in range(n):
        row[f"sigma_p_{i}"] = float(shape[i])
    csv = tmp_path / "sig.csv"
    pd.DataFrame([row]).to_csv(csv, index=False)
    table = load_sigma_profiles(str(csv), n_bins=n)
    assert len(table) == 1
    p, A, mask = build_oracle_tensors(["CCO", "c1ccccc1"], table, n_bins=n)
    assert p.shape == (2, n) and A.shape == (2,) and mask.dtype == torch.bool
    assert bool(mask[0]) is True and bool(mask[1]) is False   # CCO matched, benzene not
    assert abs(float(A[0]) - 88.0) < 1e-4
    assert torch.all(p[1] == 0) and float(A[1]) == 0.0          # unmatched -> zeros (masked out)


def test_forward_uses_oracle_profile_for_matched_rows():
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    model = trainer.model
    model.eval()
    sol_b, slv_b, targets = trainer._move_batch_to_device(next(iter(loader)))
    B = len(targets["solute_smiles"])
    n = model.cfg.cosmo_sac_n_bins
    # craft a distinctive oracle profile for ALL rows, mask all True
    oracle_p = torch.zeros(B, n); oracle_p[:, 0] = 100.0  # mass entirely in bin 0
    oracle_A = torch.full((B,), 100.0)
    mask = torch.ones(B, dtype=torch.bool)
    targets["sigma_oracle_p_solute"] = oracle_p
    targets["sigma_oracle_area_solute"] = oracle_A
    targets["sigma_oracle_mask_solute"] = mask
    # encode to get readouts, then build params with oracle on vs off
    enc_t = model._encoder_temp_features(
        __import__("tgnn_solv.layers", fromlist=["make_temperature_features"]).make_temperature_features(targets["T"]))
    _, gp_s, _, _ = model._encode_and_readout(sol_b, "solute", temp_feat=enc_t)
    _, gp_v, _, _ = model._encode_and_readout(slv_b, "solvent", temp_feat=enc_t)
    p_off = model._build_sigma_activity_params(gp_s["value"], gp_v["value"])["p_solute"]
    p_on = model._build_sigma_activity_params(
        gp_s["value"], gp_v["value"], targets=targets, force_sigma_oracle=True)["p_solute"]
    assert not torch.allclose(p_off, p_on)            # oracle changed the profile
    assert torch.allclose(p_on, oracle_p.to(p_on))    # matched rows use the oracle exactly
