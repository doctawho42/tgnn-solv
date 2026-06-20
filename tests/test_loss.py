"""Unit tests for the TGNN-Solv loss helpers."""

import sys

import pytest
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

    def test_explicit_vant_hoff_fit_targets_work_for_anchor_only_rows(self) -> None:
        """Fit-table slope targets should not require has_solubility=True rows."""
        loss_fn = TGNNSolvLoss(TGNNSolvConfig(vant_hoff_fit_r2_min=0.95))
        T = torch.tensor([325.0, 355.0, 385.0], dtype=torch.float32)
        slope = torch.tensor(-2600.0)
        intercept = torch.tensor(4.0)
        pred = slope * (1.0 / T) + intercept
        pair_keys = ["pair_a", "pair_a", "pair_a"]
        target_slope = torch.full((3,), float(slope))
        target_intercept = torch.full((3,), float(intercept))
        target_mask = torch.ones(3, dtype=torch.bool)
        sol_mask = torch.zeros(3, dtype=torch.bool)

        losses = loss_fn._pair_temperature_losses(
            pred,
            T,
            pair_keys,
            sol_mask=sol_mask,
            target_slope=target_slope,
            target_intercept=target_intercept,
            target_mask=target_mask,
            target_weight=torch.full((3,), 0.8),
            target_r2=torch.full((3,), 0.99),
        )

        assert torch.allclose(
            losses["vant_hoff_slope"],
            torch.zeros_like(losses["vant_hoff_slope"]),
            atol=1e-8,
        )
        assert torch.allclose(
            losses["vant_hoff_intercept"],
            torch.zeros_like(losses["vant_hoff_intercept"]),
            atol=1e-8,
        )

        bad_losses = loss_fn._pair_temperature_losses(
            pred + torch.tensor([0.0, 1.0, 0.0]),
            T,
            pair_keys,
            sol_mask=sol_mask,
            target_slope=target_slope,
            target_intercept=target_intercept,
            target_mask=target_mask,
            target_weight=torch.full((3,), 0.8),
            target_r2=torch.full((3,), 0.99),
        )

        assert bad_losses["vant_hoff_slope"].item() > 0.0
        assert bad_losses["vant_hoff_intercept"].item() > 0.0


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

    def test_finite_activity_gamma2_loss_respects_mask(self) -> None:
        """Finite-composition ln(gamma_2) supervision should use its own mask."""
        loss_fn = TGNNSolvLoss(TGNNSolvConfig())
        output = {
            "ln_x2": torch.zeros(2),
            "fusion_params": {
                "T_m": torch.tensor([300.0, 310.0], requires_grad=True),
                "dH_fus": torch.tensor([10_000.0, 11_000.0], requires_grad=True),
            },
            "physics": {
                "ln_gamma_inf": torch.tensor([0.0, 0.0], requires_grad=True),
                "ln_gamma_2": torch.tensor([1.5, -0.5], requires_grad=True),
                "tau_12": torch.tensor([0.0, 0.0], requires_grad=True),
                "tau_21": torch.tensor([0.0, 0.0], requires_grad=True),
            },
            "correction": torch.zeros(2),
            "gate": torch.tensor(0.0),
        }
        targets = {
            "ln_x2": torch.tensor([-5.0, -4.0]),
            "has_solubility": torch.zeros(2, dtype=torch.bool),
            "ln_gamma_2_target": torch.tensor([1.0, 99.0]),
            "gamma2_mask": torch.tensor([True, False], dtype=torch.bool),
            "gamma2_weight": torch.tensor([1.0, 1.0]),
        }
        weights = {key: 0.0 for key in loss_fn.default_weights}
        weights["gamma_2"] = 1.0

        loss, loss_dict = loss_fn(output, targets, weights=weights)

        assert loss_dict["gamma_2"] == pytest.approx(0.25)
        assert loss.item() == pytest.approx(0.25)


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

    def test_idac_aux_component_scale_preserves_constant_csv_weights(self) -> None:
        """Constant aux CSV weights should scale aux-only activity batches."""
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
        )
        trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)

        mask = torch.tensor([True, True, False])
        weight = torch.tensor([0.25, 0.25, 0.25], dtype=torch.float32)

        scale = trainer._idac_aux_component_scale(mask, weight)

        assert scale == pytest.approx(0.25)

    def test_idac_aux_component_scale_defaults_to_one_without_weights(self) -> None:
        """Missing aux CSV weights should preserve the historical behavior."""
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
        )
        trainer = TGNNSolvTrainer(TGNNSolv(cfg=cfg), cfg)

        mask = torch.tensor([True, False, True])

        scale = trainer._idac_aux_component_scale(mask, None)

        assert scale == pytest.approx(1.0)

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


class TestCrystalActivityDecorrelationLoss:
    """Regression tests for the crystal/activity decorrelation penalty."""

    def _joint_targets(self, n_rows: int) -> dict[str, torch.Tensor]:
        return {
            "ln_x2": torch.zeros(n_rows),
            "has_solubility": torch.ones(n_rows, dtype=torch.bool),
            "T_m": torch.full((n_rows,), 350.0),
            "T_m_mask": torch.ones(n_rows, dtype=torch.bool),
            "dH_fus": torch.full((n_rows,), 10_000.0),
            "dH_mask": torch.ones(n_rows, dtype=torch.bool),
        }

    def test_decorr_penalty_hits_perfect_anticorrelation(self) -> None:
        """Perfectly compensating branch errors should produce corr^2 ~= 1."""
        cfg = TGNNSolvConfig(decorr_min_samples=3)
        loss_fn = TGNNSolvLoss(cfg)
        weights = {key: 0.0 for key in loss_fn.default_weights}
        weights["decorr"] = 1.0

        T = torch.tensor([300.0, 310.0, 320.0, 330.0], dtype=torch.float32)
        targets = self._joint_targets(n_rows=4)
        phi_true = (targets["dH_fus"] / cfg.R) * (1.0 / T - 1.0 / targets["T_m"])
        delta_phi = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float32)
        gamma_required = -targets["ln_x2"] - phi_true

        output = {
            "ln_x2": torch.zeros(4),
            "physics": {
                "Phi": (phi_true + delta_phi).clone().detach().requires_grad_(True),
                "ln_gamma_2": (
                    gamma_required - delta_phi
                ).clone().detach().requires_grad_(True),
            },
        }

        loss, loss_dict = loss_fn(
            output,
            targets,
            weights=weights,
            T=T,
        )

        assert torch.isclose(loss.detach(), torch.tensor(1.0), atol=1e-6)
        assert loss_dict["decorr"] == pytest.approx(1.0, abs=1e-6)
        assert loss_dict["decorr_corr"] == pytest.approx(-1.0, abs=1e-6)
        assert loss_dict["decorr_joint_rows"] == pytest.approx(4.0)

        loss.backward()
        assert output["physics"]["Phi"].grad is not None
        assert output["physics"]["ln_gamma_2"].grad is not None

    def test_decorr_penalty_skips_small_joint_batches(self) -> None:
        """The penalty should stay inactive when too few joint labels are present."""
        cfg = TGNNSolvConfig(decorr_min_samples=3)
        loss_fn = TGNNSolvLoss(cfg)
        weights = {key: 0.0 for key in loss_fn.default_weights}
        weights["decorr"] = 1.0

        T = torch.tensor([300.0, 310.0], dtype=torch.float32)
        targets = self._joint_targets(n_rows=2)
        phi_true = (targets["dH_fus"] / cfg.R) * (1.0 / T - 1.0 / targets["T_m"])

        output = {
            "ln_x2": torch.zeros(2),
            "physics": {
                "Phi": (phi_true + 1.0).clone().detach().requires_grad_(True),
                "ln_gamma_2": (-phi_true - 1.0).clone().detach().requires_grad_(True),
            },
        }

        loss, loss_dict = loss_fn(
            output,
            targets,
            weights=weights,
            T=T,
        )

        assert torch.isclose(loss.detach(), torch.tensor(0.0), atol=1e-8)
        assert loss_dict["decorr"] == 0.0
        assert loss_dict["decorr_corr"] == 0.0
        assert loss_dict["decorr_joint_rows"] == pytest.approx(2.0)

    def test_decorr_penalty_skips_zero_variance_errors(self) -> None:
        """Constant branch errors should not create unstable correlation penalties."""
        cfg = TGNNSolvConfig(decorr_min_samples=3)
        loss_fn = TGNNSolvLoss(cfg)
        weights = {key: 0.0 for key in loss_fn.default_weights}
        weights["decorr"] = 1.0

        T = torch.tensor([300.0, 310.0, 320.0, 330.0], dtype=torch.float32)
        targets = self._joint_targets(n_rows=4)
        phi_true = (targets["dH_fus"] / cfg.R) * (1.0 / T - 1.0 / targets["T_m"])
        gamma_required = -targets["ln_x2"] - phi_true

        output = {
            "ln_x2": torch.zeros(4),
            "physics": {
                "Phi": (phi_true + 2.0).clone().detach().requires_grad_(True),
                "ln_gamma_2": (
                    gamma_required - 1.0
                ).clone().detach().requires_grad_(True),
            },
        }

        loss, loss_dict = loss_fn(
            output,
            targets,
            weights=weights,
            T=T,
        )

        assert torch.isclose(loss.detach(), torch.tensor(0.0), atol=1e-8)
        assert loss_dict["decorr"] == 0.0
        assert loss_dict["decorr_corr"] == 0.0
        assert loss_dict["decorr_joint_rows"] == pytest.approx(4.0)
