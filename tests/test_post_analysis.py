from __future__ import annotations

import torch

from tgnn_solv.post_analysis import (
    build_selected_checkpoint_payload,
    parse_training_log_text,
)


def test_parse_training_log_text_keeps_latest_duplicate_epoch() -> None:
    text = """
Phase 2 epochs:  50%|█████     | 20/40 [00:00<00:00,  1.00it/s]  Epoch  19/40: train=0.1047, val=1.0639, MAE=1.852, R²=0.277, gate=0.736
    loss/sol_raw=0.0980 loss/sol_weighted=0.0980 weight=1
    loss/tau_reg_raw=1.2300 loss/tau_reg_weighted=0.0025 weight=0.002
    loss/total=0.1200 loss/sol_fraction=0.820 loss/sol_fraction_min=0.220 loss/max_regularizer_ratio=8.40 loss/regularizer_domination_count=14
Phase 2 epochs:  52%|█████▎    | 21/40 [00:00<00:00,  1.00it/s]  Epoch  20/40: train=0.0753, val=1.3254, MAE=1.845, R²=0.294, gate=0.758
    loss/sol_raw=0.0700 loss/sol_weighted=0.0700 weight=1
    loss/tau_reg_raw=1.8400 loss/tau_reg_weighted=0.0037 weight=0.002
    loss/total=0.0753 loss/sol_fraction=0.930 loss/sol_fraction_min=0.330 loss/max_regularizer_ratio=3.90 loss/regularizer_domination_count=9
Phase 2 epochs:  52%|█████▎    | 21/40 [00:00<00:00,  1.00it/s]  Epoch  20/40: train=0.0730, val=1.3100, MAE=1.840, R²=0.296, gate=0.759
    loss/sol_raw=0.0680 loss/sol_weighted=0.0680 weight=1
    loss/tau_reg_raw=1.8500 loss/tau_reg_weighted=0.0037 weight=0.002
    loss/total=0.0730 loss/sol_fraction=0.940 loss/sol_fraction_min=0.340 loss/max_regularizer_ratio=3.70 loss/regularizer_domination_count=7
Phase 3 epochs:  10%|█         | 1/10 [00:00<00:00,  1.00it/s]  Epoch   0/10: train=0.0500, val=1.9000, MAE=1.860, R²=0.280, gate=0.760
    loss/sol_raw=0.0450 loss/sol_weighted=0.0450 weight=1
    loss/tau_reg_raw=1.5000 loss/tau_reg_weighted=0.0030 weight=0.002
    loss/total=0.0500 loss/sol_fraction=0.900 loss/sol_fraction_min=0.500 loss/max_regularizer_ratio=3.20 loss/regularizer_domination_count=4
"""
    parsed = parse_training_log_text(text)
    assert parsed["n_entries"] == 3
    best = parsed["best_phase2_by_val_mae"]
    assert best is not None
    assert best["epoch"] == 20
    assert best["val_mae"] == 1.84
    assert best["loss_components"]["tau_reg"]["raw"] == 1.85
    assert best["regularizer_domination_count"] == 7
    assert parsed["final_entry"]["phase"] == 3


def test_build_selected_checkpoint_payload_prefers_trainer_best_state() -> None:
    current = {"weight": torch.tensor([1.0])}
    best = {"weight": torch.tensor([2.0])}
    payload = {
        "model_state": current,
        "model_state_dict": current,
        "trainer_state_dict": {
            "best_state": best,
            "best_val_loss": 1.23,
            "best_epoch": 19,
            "best_phase": 2,
        },
        "resume_state": {"status": "completed"},
    }

    selected_payload, meta = build_selected_checkpoint_payload(payload)

    assert meta["selected_state_source"] == "trainer_state_dict.best_state"
    assert meta["model_state_matches_best_state"] is False
    assert torch.equal(selected_payload["model_state"]["weight"], torch.tensor([2.0]))
    assert torch.equal(selected_payload["model_state_dict"]["weight"], torch.tensor([2.0]))
