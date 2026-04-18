"""Unit tests for the TGNN-Solv loss helpers."""

import sys

import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.loss import TGNNSolvLoss
from tgnn_solv.model import TGNNSolv
from tgnn_solv.trainer import TGNNSolvTrainer


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

    def test_close_temperature_pairs_stay_finite_and_capped(self) -> None:
        """Very small ΔT should not explode the local van't Hoff penalty."""
        loss_fn = TGNNSolvLoss(TGNNSolvConfig())
        T = torch.tensor([298.0, 303.0, 308.0], dtype=torch.float32)
        pred = torch.tensor([-12.0, 5.0, -14.0], dtype=torch.float32)
        pair_keys = ["pair_a", "pair_a", "pair_a"]

        losses = loss_fn._pair_temperature_losses(pred, T, pair_keys)

        assert torch.isfinite(losses["vant_hoff_local"])
        assert losses["vant_hoff_local"].item() <= 100.0 + 1e-6


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


class TestBridgeAndWaldenControls:
    """Regression tests for new bridge and Walden loss controls."""

    def _base_output(self) -> dict[str, object]:
        return {
            "ln_x2": torch.zeros(2),
            "fusion_params": {
                "T_m": torch.tensor([100.0, 200.0], requires_grad=True),
                "dH_fus": torch.tensor([50_000.0, 30_000.0], requires_grad=True),
            },
            "hansen_sol": torch.tensor(
                [[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]], requires_grad=True
            ),
            "hansen_slv": torch.tensor(
                [[1.2, 2.2, 3.2], [1.7, 2.7, 3.7]], requires_grad=True
            ),
            "aux_sol": {"V_m": torch.tensor([100.0, 100.0], requires_grad=True)},
            "physics": {
                "ln_gamma_inf": torch.tensor([0.1, 0.2], requires_grad=True),
                "tau_12": torch.tensor([0.0, 0.0], requires_grad=True),
                "tau_21": torch.tensor([0.0, 0.0], requires_grad=True),
            },
            "correction": torch.zeros(2),
            "gate": torch.tensor(0.0),
        }

    def _base_targets(self) -> dict[str, object]:
        return {
            "ln_x2": torch.tensor([-5.0, -4.0]),
            "has_solubility": torch.zeros(2, dtype=torch.bool),
            "T_m": torch.tensor([300.0, 310.0]),
            "T_m_mask": torch.tensor([True, False], dtype=torch.bool),
            "dH_fus": torch.tensor([10_000.0, 11_000.0]),
            "dH_mask": torch.tensor([True, False], dtype=torch.bool),
            "hansen_sol": torch.tensor([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]]),
            "hansen_mask": torch.zeros(2, dtype=torch.bool),
            "ln_gamma_inf": torch.tensor([0.1, 0.2]),
            "gamma_mask": torch.zeros(2, dtype=torch.bool),
        }

    def test_bridge_loss_is_not_computed_when_weight_is_zero(self) -> None:
        """Bridge path should be skipped entirely when its effective weight is zero."""
        loss_fn = TGNNSolvLoss(TGNNSolvConfig())
        loss_fn._bridge_loss = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("bridge loss should not be evaluated")
        )

        weights = {key: 0.0 for key in loss_fn.default_weights}
        weights["bridge"] = 0.0
        loss, loss_dict = loss_fn(
            self._base_output(),
            self._base_targets(),
            weights=weights,
            T=torch.tensor([298.15, 298.15]),
        )

        assert "bridge" not in loss_dict
        assert loss.item() == 0.0

    def test_walden_penalty_only_hits_unsupervised_samples(self) -> None:
        """Walden loss should ignore samples already supervised on both crystal targets."""
        cfg = TGNNSolvConfig(
            use_walden_check=True,
            walden_target=56.5,
            walden_tolerance=30.0,
            walden_weight=0.1,
        )
        loss_fn = TGNNSolvLoss(cfg)
        weights = {key: 0.0 for key in loss_fn.default_weights}

        loss, loss_dict = loss_fn(
            self._base_output(),
            self._base_targets(),
            weights=weights,
        )

        expected_raw = (abs(30_000.0 / 200.0 - 56.5) - 30.0) ** 2
        assert torch.isclose(
            torch.tensor(loss_dict["walden"]),
            torch.tensor(expected_raw),
        )
        assert torch.isclose(
            loss.detach(),
            torch.tensor(cfg.walden_weight * expected_raw),
        )

    def test_walden_uses_explicit_entropy_when_available(self) -> None:
        """Walden loss should prefer FusionHead-provided dS_fus diagnostics."""
        cfg = TGNNSolvConfig(
            use_walden_check=True,
            walden_target=56.5,
            walden_tolerance=30.0,
            walden_weight=0.1,
        )
        loss_fn = TGNNSolvLoss(cfg)
        output = self._base_output()
        output["fusion_params"]["dS_fus"] = torch.tensor(
            [56.5, 150.0],
            dtype=torch.float32,
            requires_grad=True,
        )
        weights = {key: 0.0 for key in loss_fn.default_weights}

        loss, loss_dict = loss_fn(
            output,
            self._base_targets(),
            weights=weights,
        )

        expected_raw = (150.0 - 56.5 - 30.0) ** 2
        assert torch.isclose(
            torch.tensor(loss_dict["walden"]),
            torch.tensor(expected_raw),
        )
        assert torch.isclose(
            loss.detach(),
            torch.tensor(cfg.walden_weight * expected_raw),
        )

    def test_trainer_uses_global_bridge_weight_unless_phase_override_exists(
        self,
    ) -> None:
        """Global bridge weight should be the default, with old per-phase overrides preserved."""
        cfg = TGNNSolvConfig(
            hidden_dim=32,
            n_gnn_layers=2,
            n_cross_attn_layers=1,
            n_attn_heads=4,
            pair_dim=64,
            solvent_moe_hidden=64,
            solvent_type_emb_dim=8,
            n_iter_train=2,
            n_iter_eval=2,
            set2set_steps=2,
            bridge_loss_weight=0.07,
            phase2_loss_weights={"bridge": 0.02},
        )
        trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)

        assert trainer.phase_weights[1]["bridge"] == 0.07
        assert trainer.phase_weights[2]["bridge"] == 0.02
        assert trainer.phase_weights[3]["bridge"] == 0.07

    def test_aux_direct_solubility_weight_schedule(self) -> None:
        """Auxiliary direct solubility loss is phase-gated by the trainer."""
        cfg = TGNNSolvConfig(
            hidden_dim=32,
            n_gnn_layers=2,
            n_cross_attn_layers=1,
            n_attn_heads=4,
            pair_dim=64,
            solvent_moe_hidden=64,
            solvent_type_emb_dim=8,
            n_iter_train=2,
            n_iter_eval=2,
            set2set_steps=2,
            use_aux_direct_sol_loss=True,
            aux_direct_sol_loss_weight=0.1,
            aux_direct_sol_loss_phase3_weight=0.01,
        )
        trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)

        assert trainer.phase_weights[1]["aux_direct_sol"] == 0.0
        assert trainer.phase_weights[2]["aux_direct_sol"] == 0.1
        assert trainer.phase_weights[3]["aux_direct_sol"] == 0.01

    def test_oracle_injection_probability_anneals_over_phase2(self) -> None:
        """Phase 2 should ramp oracle injection down over the last 50 epochs."""
        cfg = TGNNSolvConfig(
            hidden_dim=32,
            n_gnn_layers=2,
            n_cross_attn_layers=1,
            n_attn_heads=4,
            pair_dim=64,
            solvent_moe_hidden=64,
            solvent_type_emb_dim=8,
            n_iter_train=2,
            n_iter_eval=2,
            set2set_steps=2,
            use_oracle_injection=True,
            oracle_injection_prob=1.0,
        )
        model = TGNNSolv(cfg=cfg)
        trainer = TGNNSolvTrainer(model, cfg)

        trainer._set_oracle_injection_prob(2, epoch=0, n_epochs=200)
        assert trainer.cfg.oracle_injection_prob == 1.0

        trainer._set_oracle_injection_prob(2, epoch=149, n_epochs=200)
        assert trainer.cfg.oracle_injection_prob == 1.0

        trainer._set_oracle_injection_prob(2, epoch=150, n_epochs=200)
        assert abs(trainer.cfg.oracle_injection_prob - 0.98) < 1e-8

        trainer._set_oracle_injection_prob(2, epoch=199, n_epochs=200)
        assert trainer.cfg.oracle_injection_prob == 0.0


class TestHansenDeltaLoss:
    """Regression tests for explicit pairwise Hansen-delta supervision."""

    def test_hansen_delta_loss_uses_pair_effective_targets(self) -> None:
        """The loss should supervise predicted solute-solvent Hansen deltas."""
        cfg = TGNNSolvConfig()
        loss_fn = TGNNSolvLoss(cfg)
        weights = {key: 0.0 for key in loss_fn.default_weights}
        weights["hansen_delta"] = 1.0

        output = {
            "ln_x2": torch.zeros(2),
            "hansen_sol": torch.tensor(
                [[10.0, 5.0, 3.0], [20.0, 10.0, 4.0]],
                requires_grad=True,
            ),
            "hansen_slv": torch.tensor(
                [[8.0, 4.0, 1.0], [15.0, 6.0, 1.0]],
                requires_grad=True,
            ),
            "physics": {},
        }
        targets = {
            "ln_x2": torch.zeros(2),
            "has_solubility": torch.zeros(2, dtype=torch.bool),
            "hansen_sol_effective": torch.tensor(
                [[11.0, 5.0, 3.0], [20.0, 10.0, 4.0]]
            ),
            "hansen_slv_effective": torch.tensor(
                [[8.0, 4.0, 1.0], [16.0, 7.0, 2.0]]
            ),
            "pair_hansen_mask": torch.tensor([True, True]),
            "pair_hansen_weight": torch.tensor([1.0, 0.5]),
        }

        loss, loss_dict = loss_fn(output, targets, weights=weights)

        pred_delta = output["hansen_sol"] - output["hansen_slv"]
        true_delta = (
            targets["hansen_sol_effective"]
            - targets["hansen_slv_effective"]
        )
        per_sample = ((pred_delta - true_delta) / loss_fn.S_hansen).pow(2).mean(dim=-1)
        expected = (
            per_sample * targets["pair_hansen_weight"]
        ).sum() / targets["pair_hansen_weight"].sum()

        assert torch.allclose(torch.tensor(loss_dict["hansen_delta"]), expected.detach())
        assert torch.allclose(loss, expected)
        loss.backward()
        assert output["hansen_sol"].grad is not None
        assert output["hansen_slv"].grad is not None

    def test_trainer_can_schedule_hansen_delta_loss(self) -> None:
        """Config-driven Hansen-delta weights should populate phase weights."""
        cfg = TGNNSolvConfig(
            hidden_dim=32,
            n_gnn_layers=2,
            n_cross_attn_layers=1,
            n_attn_heads=4,
            pair_dim=64,
            solvent_moe_hidden=64,
            solvent_type_emb_dim=8,
            n_iter_train=2,
            n_iter_eval=2,
            set2set_steps=2,
            use_hansen_delta_loss=True,
            hansen_delta_loss_phase1_weight=0.05,
            hansen_delta_loss_phase2_weight=0.02,
            hansen_delta_loss_phase3_weight=0.01,
        )
        trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)

        assert trainer.phase_weights[1]["hansen_delta"] == 0.05
        assert trainer.phase_weights[2]["hansen_delta"] == 0.02
        assert trainer.phase_weights[3]["hansen_delta"] == 0.01
