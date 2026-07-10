import numpy as np
import torch

from sigma_fixtures import make_tiny_cosmo_trainer_and_loader
from tgnn_solv.layers import make_temperature_features
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
    assert B >= 2  # fixture yields batch_size 2; need a mixed mask
    n = model.cfg.cosmo_sac_n_bins
    # craft a distinctive oracle profile, MIXED mask: only row 0 matched
    oracle_p = torch.zeros(B, n)
    oracle_p[:, 0] = 100.0  # mass entirely in bin 0
    oracle_A = torch.full((B,), 100.0)
    mask = torch.tensor([True] + [False] * (B - 1))
    targets["sigma_oracle_p_solute"] = oracle_p
    targets["sigma_oracle_area_solute"] = oracle_A
    targets["sigma_oracle_mask_solute"] = mask
    # encode to get readouts, then build params with oracle on vs off
    enc_t = model._encoder_temp_features(make_temperature_features(targets["T"]))
    _, gp_s, _, _ = model._encode_and_readout(sol_b, "solute", temp_feat=enc_t)
    _, gp_v, _, _ = model._encode_and_readout(slv_b, "solvent", temp_feat=enc_t)
    p_off = model._build_sigma_activity_params(gp_s["value"], gp_v["value"])["p_solute"]
    p_on = model._build_sigma_activity_params(
        gp_s["value"], gp_v["value"], targets=targets, force_sigma_oracle=True)["p_solute"]
    assert not torch.allclose(p_off, p_on)                       # oracle changed the profile
    assert torch.allclose(p_on[0], oracle_p[0].to(p_on))         # matched row uses the oracle exactly
    assert torch.allclose(p_on[1:], p_off[1:])                   # unmatched rows keep predicted profile


def test_train_time_oracle_injection_gated_by_flag():
    """Eval-only contract holds by default; train-time injection fires only when
    cfg.train_sigma_oracle is set (the model.py:538 guard relaxation). Robust to
    train-mode dropout: compare against the distinctive oracle profile (a bin-0
    spike), not a second stochastic forward — the swap is a deterministic overwrite."""
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    model = trainer.model
    model.train()  # TRAIN mode — where the old guard blocked oracle injection
    sol_b, slv_b, targets = trainer._move_batch_to_device(next(iter(loader)))
    B = len(targets["solute_smiles"])
    n = model.cfg.cosmo_sac_n_bins
    oracle_p = torch.zeros(B, n)
    oracle_p[:, 0] = 100.0  # distinctive spike; a head prediction is never shaped like this
    targets["sigma_oracle_p_solute"] = oracle_p
    targets["sigma_oracle_area_solute"] = torch.full((B,), 100.0)
    targets["sigma_oracle_mask_solute"] = torch.tensor([True] + [False] * (B - 1))
    enc_t = model._encoder_temp_features(make_temperature_features(targets["T"]))
    _, gp_s, _, _ = model._encode_and_readout(sol_b, "solute", temp_feat=enc_t)
    _, gp_v, _, _ = model._encode_and_readout(slv_b, "solvent", temp_feat=enc_t)

    prev = getattr(model.cfg, "train_sigma_oracle", False)
    try:
        model.cfg.train_sigma_oracle = False  # default: guard blocks train-time swap
        p_off = model._build_sigma_activity_params(
            gp_s["value"], gp_v["value"], targets=targets, force_sigma_oracle=True)["p_solute"]
        assert not torch.allclose(p_off[0], oracle_p[0].to(p_off))  # matched row NOT swapped

        model.cfg.train_sigma_oracle = True  # flag on: swap fires on matched rows in train mode
        p_on = model._build_sigma_activity_params(
            gp_s["value"], gp_v["value"], targets=targets, force_sigma_oracle=True)["p_solute"]
        assert torch.allclose(p_on[0], oracle_p[0].to(p_on))       # matched row == oracle exactly
        assert not torch.allclose(p_on[1], oracle_p[1].to(p_on))   # unmatched row keeps prediction
    finally:
        model.cfg.train_sigma_oracle = prev


def test_trainer_inject_sigma_oracle_populates_targets(tmp_path):
    """_inject_sigma_oracle builds the six oracle target keys, sets the force flag, and
    caches per-SMILES results so canonicalization is not repeated."""
    import pandas as pd
    trainer, loader = make_tiny_cosmo_trainer_and_loader()
    n = trainer.model.cfg.cosmo_sac_n_bins
    _, _, t0 = next(iter(loader))
    solute_smi = t0["solute_smiles"][0]
    row = {"smiles": solute_smi, "sigma_area": 50.0}
    for i in range(n):
        row[f"sigma_p_{i}"] = 50.0 / n
    csv = tmp_path / "sig.csv"
    pd.DataFrame([row]).to_csv(csv, index=False)
    trainer._sigma_oracle_table = load_sigma_profiles(str(csv), n_bins=n)
    trainer._oracle_row_cache = {}
    trainer.cfg.train_sigma_oracle = True
    trainer.cfg.sigma_oracle_side = "both"

    _, _, targets = trainer._move_batch_to_device(next(iter(loader)))
    for k in ("sigma_oracle_p_solute", "sigma_oracle_area_solute", "sigma_oracle_mask_solute",
              "sigma_oracle_p_solvent", "sigma_oracle_area_solvent", "sigma_oracle_mask_solvent"):
        assert k in targets, k
    assert targets.get("__force_sigma_oracle__") is True
    assert targets["sigma_oracle_p_solute"].shape[-1] == n
    assert len(trainer._oracle_row_cache) > 0  # per-SMILES memoization populated
