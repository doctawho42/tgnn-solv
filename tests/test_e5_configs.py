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
    # Phase 3 is off: it never improved val on any of the ten finished sigma_arms runs and
    # its result was restored away before saving. The declared ceiling is therefore 100
    # against the 110 of the NRTL and DirectGNN arms below, and that mismatch is real but
    # not binding: phase 2 early-stops at 31-66 epochs across arms, so actual spend varies
    # by 35 epochs between arms already -- three times the 10 removed here. Matching the
    # ceiling never matched the spend. NOT the tuned 50/200/50.
    assert (c.epochs_phase1, c.epochs_phase2, c.epochs_phase3) == (30, 70, 0)


def test_nrtl_h64_config_matches_capacity_and_budget():
    # NRTL milestone arm runs at the SAME h64/3L capacity as the cosmo/DirectGNN arms, and
    # still at the 30/70/10 ceiling; cosmo_sac dropped to 30/70/0 above, so the ceilings no
    # longer agree (the tuned config is h256/6L @ 50/200/50 — not comparable either way).
    c = TGNNSolvConfig.from_yaml("configs/paper_config_nrtl_h64L3.yaml")
    assert c.activity_model == "nrtl"
    assert c.hidden_dim == 64 and c.n_gnn_layers == 3
    assert (c.epochs_phase1, c.epochs_phase2, c.epochs_phase3) == (30, 70, 10)


def test_directgnn_h64_config_matches_capacity():
    c = TGNNSolvConfig.from_yaml("configs/paper_config_directgnn_h64L3.yaml")
    assert c.hidden_dim == 64 and c.n_gnn_layers == 3
    assert c.epochs_phase2 == 110          # = the TGNN ceiling as declared when this was
    # written, 30+70+10; cosmo_sac is now 30/70/0, see the note there
    assert c.use_morgan_features is False
    assert c.use_descriptor_augmentation is False
