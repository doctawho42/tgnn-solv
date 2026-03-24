"""Unit tests for the TGNN-Solv loss helpers."""

import sys

import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.loss import TGNNSolvLoss


class TestPairTemperatureLosses:
    """Verify same-pair temperature consistency penalties."""

    def test_zero_for_monotonic_linear_vant_hoff_curve(self) -> None:
        """A perfectly linear same-pair van't Hoff curve should incur no penalty."""
        loss_fn = TGNNSolvLoss(TGNNSolvConfig())
        T = torch.tensor([300.0, 320.0, 340.0], dtype=torch.float32)
        inv_T = 1.0 / T
        pred = 10.0 - 2000.0 * inv_T
        pair_keys = ["pair_a", "pair_a", "pair_a"]

        losses = loss_fn._pair_temperature_losses(pred, T, pair_keys)

        assert torch.allclose(
            losses["pair_temp_rank"],
            torch.zeros_like(losses["pair_temp_rank"]),
            atol=1e-8,
        )
        assert torch.allclose(
            losses["vant_hoff_local"],
            torch.zeros_like(losses["vant_hoff_local"]),
            atol=1e-6,
        )

    def test_positive_for_nonmonotonic_nonlinear_curve(self) -> None:
        """A bad same-pair temperature trend should trigger both penalties."""
        loss_fn = TGNNSolvLoss(TGNNSolvConfig())
        T = torch.tensor([300.0, 320.0, 340.0], dtype=torch.float32)
        pred = torch.tensor([-4.0, -4.5, -3.8], dtype=torch.float32)
        pair_keys = ["pair_a", "pair_a", "pair_a"]

        losses = loss_fn._pair_temperature_losses(pred, T, pair_keys)

        assert losses["pair_temp_rank"].item() > 0.0
        assert losses["vant_hoff_local"].item() > 0.0


class TestEmptySupervisionBatches:
    """Regression tests for batches without active supervision targets."""

    def test_zero_loss_keeps_backward_valid(self) -> None:
        """A fully masked batch should still produce a backward-safe scalar loss."""
        loss_fn = TGNNSolvLoss(TGNNSolvConfig())
        output = {
            "ln_x2": torch.zeros(2),
            "fusion_params": {
                "T_m": torch.tensor([300.0, 310.0], requires_grad=True),
                "dH_fus": torch.tensor([10_000.0, 11_000.0], requires_grad=True),
            },
            "hansen_sol": torch.tensor(
                [[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]], requires_grad=True
            ),
            "hansen_slv": torch.tensor(
                [[1.2, 2.2, 3.2], [1.7, 2.7, 3.7]], requires_grad=True
            ),
            "physics": {
                "ln_gamma_inf": torch.tensor([0.1, 0.2], requires_grad=True),
                "tau_12": torch.tensor([0.0, 0.0], requires_grad=True),
                "tau_21": torch.tensor([0.0, 0.0], requires_grad=True),
            },
            "correction": torch.zeros(2),
            "gate": torch.tensor(0.0),
        }
        targets = {
            "ln_x2": torch.tensor([-5.0, -4.0]),
            "has_solubility": torch.zeros(2, dtype=torch.bool),
            "T_m": torch.tensor([300.0, 310.0]),
            "T_m_mask": torch.zeros(2, dtype=torch.bool),
            "dH_fus": torch.tensor([10_000.0, 11_000.0]),
            "dH_mask": torch.zeros(2, dtype=torch.bool),
            "hansen_sol": torch.tensor([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]]),
            "hansen_mask": torch.zeros(2, dtype=torch.bool),
            "ln_gamma_inf": torch.tensor([0.1, 0.2]),
            "gamma_mask": torch.zeros(2, dtype=torch.bool),
        }
        weights = {
            "sol": 0.0,
            "T_m": 1.0,
            "dH": 1.0,
            "hansen": 1.0,
            "gamma_inf": 1.0,
            "mono": 0.0,
            "res": 0.0,
            "bridge": 0.0,
            "tau_reg": 0.0,
            "phys_pref": 0.0,
            "direct_reg": 0.0,
            "direct_nll": 0.0,
            "pair_temp_rank": 0.0,
            "vant_hoff_local": 0.0,
            "moe_balance": 0.0,
        }

        loss, loss_dict = loss_fn(output, targets, weights=weights)

        assert loss.shape == torch.Size([])
        assert loss.requires_grad
        assert all(value == 0.0 for value in loss_dict.values())

        loss.backward()
        assert output["fusion_params"]["T_m"].grad is not None
