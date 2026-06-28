from tgnn_solv.config import TGNNSolvConfig


def test_cosmo_sac_config_pins_grounded_recipe():
    c = TGNNSolvConfig.from_yaml("configs/cosmo_sac.yaml")
    assert c.activity_model == "cosmo_sac"
    assert c.hidden_dim == 64 and c.n_gnn_layers == 3
    assert c.cosmo_sac_gamma_iter_train == 16 and c.cosmo_sac_gamma_iter_eval == 30
    assert c.cosmo_sac_wire_volume is False          # arm A residual-only by default
    assert c.sigma_aux_symmetrize is True
    assert c.freeze_sigma_head_during_sle is True
    assert c.sigma_warmup_epochs > 0
    assert c.sigma_aux_steps_per_epoch > 0
    # matched budget 30/70/10 = 110 (same total as DirectGNN-h64); NOT the tuned 50/200/50
    assert (c.epochs_phase1, c.epochs_phase2, c.epochs_phase3) == (30, 70, 10)


def test_nrtl_h64_config_matches_capacity_and_budget():
    # NRTL milestone arm must run at the SAME h64/3L capacity + 30/70/10 budget as the
    # cosmo/DirectGNN arms (the tuned config is h256/6L @ 50/200/50 — not comparable).
    c = TGNNSolvConfig.from_yaml("configs/paper_config_nrtl_h64L3.yaml")
    assert c.activity_model == "nrtl"
    assert c.hidden_dim == 64 and c.n_gnn_layers == 3
    assert (c.epochs_phase1, c.epochs_phase2, c.epochs_phase3) == (30, 70, 10)


def test_directgnn_h64_config_matches_capacity():
    c = TGNNSolvConfig.from_yaml("configs/paper_config_directgnn_h64L3.yaml")
    assert c.hidden_dim == 64 and c.n_gnn_layers == 3
    assert c.epochs_phase2 == 110          # = TGNN total budget 30+70+10
    assert c.use_morgan_features is False
    assert c.use_descriptor_augmentation is False
