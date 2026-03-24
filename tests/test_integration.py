"""Integration tests for full TGNN-Solv forward and backward passes."""

import sys

import numpy as np
import pytest
import torch

sys.path.insert(0, "src")

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.features import smiles_to_graph
from tgnn_solv.model import TGNNSolv


def make_small_config() -> TGNNSolvConfig:
    """Create a reduced configuration that still exercises the full model path."""
    return TGNNSolvConfig(
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


def make_split_late_config() -> TGNNSolvConfig:
    """Create a reduced config that exercises the asymmetric late encoder path."""
    return TGNNSolvConfig(
        hidden_dim=32,
        n_gnn_layers=2,
        encoder_role_mode="split_late",
        encoder_role_specific_layers=1,
        n_cross_attn_layers=1,
        n_attn_heads=4,
        pair_dim=64,
        solvent_moe_hidden=64,
        solvent_type_emb_dim=8,
        n_iter_train=2,
        n_iter_eval=2,
        set2set_steps=2,
    )


def make_test_batch(
    pairs: list[tuple[str, str, float]],
) -> tuple[object, object, torch.Tensor, torch.Tensor]:
    """Build model inputs from `(solute_smiles, solvent_smiles, temperature)` tuples.

    The real dataset returns `(solute_graph, solvent_graph, targets_dict)` and
    `collate_fn()` turns those into `(solute_batch, solvent_batch, targets)`.
    `TGNNSolv.forward()` only consumes the batched solute graph, batched solvent
    graph, the temperature tensor, and the optional solvent type tensor, so this
    helper mirrors the real collation path and returns exactly those arguments.
    """
    from tgnn_solv.data.dataset import collate_fn
    from tgnn_solv.data.solvent_types import solvent_type_id_from_smiles

    samples = []
    for solute_smiles, solvent_smiles, temperature in pairs:
        solute_graph = smiles_to_graph(solute_smiles)
        solvent_graph = smiles_to_graph(solvent_smiles)
        if solute_graph is None or solvent_graph is None:
            raise ValueError(
                f"Invalid SMILES pair: solute={solute_smiles!r}, solvent={solvent_smiles!r}"
            )

        targets = {
            "T": torch.tensor(float(temperature), dtype=torch.float32),
            "solvent_type": torch.tensor(
                solvent_type_id_from_smiles(solvent_smiles),
                dtype=torch.long,
            ),
        }
        samples.append((solute_graph, solvent_graph, targets))

    solute_batch, solvent_batch, targets = collate_fn(samples)
    return solute_batch, solvent_batch, targets["T"], targets["solvent_type"]


def run_model(
    model: TGNNSolv,
    batch: tuple[object, object, torch.Tensor, torch.Tensor],
) -> dict[str, torch.Tensor]:
    """Run the model on a test batch using the real forward signature."""
    solute_batch, solvent_batch, temperature, solvent_type = batch
    return model(
        solute_batch,
        solvent_batch,
        temperature,
        solvent_type=solvent_type,
    )


@pytest.fixture
def small_model() -> TGNNSolv:
    """Create a compact model instance for integration tests."""
    model = TGNNSolv(cfg=make_small_config())
    model.eval()
    return model


class TestForwardPass:
    """Forward-pass integration checks."""

    def test_model_creates(self) -> None:
        """Model construction succeeds and creates trainable parameters."""
        model = TGNNSolv(cfg=make_small_config())
        n_params = sum(p.numel() for p in model.parameters())
        assert n_params > 0

    def test_output_keys(self, small_model: TGNNSolv) -> None:
        """Forward pass returns the expected output dictionary."""
        batch = make_test_batch([("CCO", "O", 298.15)])
        out = run_model(small_model, batch)

        expected_keys = {
            "ln_x2",
            "x2",
            "physics",
            "proposal_physics",
            "fusion_params",
            "corrected_fusion_params",
            "nrtl_params",
            "corrected_nrtl_state",
            "correction",
        }
        assert isinstance(out, dict)
        assert expected_keys.issubset(out.keys()), f"Unexpected output keys: {sorted(out.keys())}"
        assert "tau_ref_12" in out["nrtl_params"]
        assert "tau_ref_21" in out["nrtl_params"]

    def test_no_nan_output(self, small_model: TGNNSolv) -> None:
        """Valid molecular pairs do not produce NaN or Inf outputs."""
        pairs = [
            ("CCO", "O", 298.15),
            ("c1ccccc1", "CCCCCC", 310.0),
            ("CC(=O)O", "CCO", 273.15),
        ]
        batch = make_test_batch(pairs)
        out = run_model(small_model, batch)
        ln_x2 = out["ln_x2"]

        assert ln_x2.shape[0] == len(pairs)
        assert torch.isfinite(ln_x2).all(), f"Non-finite values in output: {ln_x2}"

    def test_fusion_head_is_temperature_invariant(
        self,
        small_model: TGNNSolv,
    ) -> None:
        """Crystal-property heads should not change with temperature for one solute."""
        batch = make_test_batch([
            ("CCO", "O", 298.15),
            ("CCO", "O", 350.00),
        ])
        out = run_model(small_model, batch)
        fusion = out["fusion_params"]

        for key in ("T_m", "dH_fus", "dCp_fus"):
            assert torch.allclose(
                fusion[key][0],
                fusion[key][1],
                atol=1e-6,
                rtol=0.0,
            ), f"{key} changed with temperature: {fusion[key]}"

    def test_correction_is_bounded(self, small_model: TGNNSolv) -> None:
        """The residual proposal must stay within the configured trust region."""
        batch = make_test_batch([
            ("CCO", "O", 298.15),
            ("c1ccccc1", "CCCCCC", 310.0),
        ])
        out = run_model(small_model, batch)
        residual = out["ln_x2_direct"] - out["physics"]["ln_x2"]
        limit = small_model.cfg.correction_max_abs + 1e-6
        assert residual.abs().max().item() <= limit

    def test_correction_starts_as_identity(self, small_model: TGNNSolv) -> None:
        """Fresh correction weights should not perturb the physics solution."""
        batch = make_test_batch([
            ("CCO", "O", 298.15),
            ("c1ccccc1", "CCCCCC", 310.0),
        ])
        out = run_model(small_model, batch)

        proposal_residual = out["ln_x2_direct"] - out["physics"]["ln_x2"]
        final_residual = out["ln_x2"] - out["physics"]["ln_x2"]
        assert torch.allclose(
            proposal_residual,
            torch.zeros_like(proposal_residual),
            atol=1e-6,
            rtol=0.0,
        ), f"Initial proposal residual is not zero: {proposal_residual}"
        assert torch.allclose(
            final_residual,
            torch.zeros_like(final_residual),
            atol=1e-6,
            rtol=0.0,
        ), f"Initial final residual is not zero: {final_residual}"

    def test_corrected_parameter_outputs_are_finite(
        self,
        small_model: TGNNSolv,
    ) -> None:
        """Parameter-space correction outputs should remain finite."""
        batch = make_test_batch([("CCO", "O", 298.15)])
        out = run_model(small_model, batch)

        for payload_key in ("corrected_fusion_params", "corrected_nrtl_state"):
            for value in out[payload_key].values():
                assert torch.isfinite(value).all(), (
                    f"Non-finite corrected parameter in {payload_key}: {value}"
                )

    def test_split_late_encoder_forward(self) -> None:
        """The alternative asymmetric late encoder should run end-to-end."""
        model = TGNNSolv(cfg=make_split_late_config())
        model.eval()
        batch = make_test_batch([
            ("CCO", "O", 298.15),
            ("CCN", "O", 315.0),
        ])

        with torch.no_grad():
            out = run_model(model, batch)

        assert torch.isfinite(out["ln_x2"]).all()
        assert out["ln_x2"].shape[0] == 2

    def test_auxiliary_outputs_are_minimal_and_finite(
        self,
        small_model: TGNNSolv,
    ) -> None:
        """The maintained auxiliary head should only expose supervised physics support."""
        batch = make_test_batch([("CCO", "O", 298.15)])
        out = run_model(small_model, batch)

        assert set(out["aux_sol"].keys()) == {"V_m"}
        assert set(out["aux_slv"].keys()) == {"V_m"}
        assert torch.isfinite(out["aux_sol"]["V_m"]).all()
        assert torch.isfinite(out["aux_slv"]["V_m"]).all()


class TestGradientFlow:
    """Backward-pass integration checks."""

    def test_gradients_exist(self) -> None:
        """At least some parameters receive non-zero gradients."""
        model = TGNNSolv(cfg=make_small_config())
        model.train()

        batch = make_test_batch([("CCO", "O", 298.15)])
        out = run_model(model, batch)
        loss = out["ln_x2"].sum()
        loss.backward()

        params_with_grad = [
            name
            for name, parameter in model.named_parameters()
            if parameter.grad is not None and parameter.grad.abs().sum() > 0
        ]
        assert len(params_with_grad) > 0, "No parameters received gradients"

    def test_no_nan_gradients(self) -> None:
        """Computed gradients stay finite."""
        model = TGNNSolv(cfg=make_small_config())
        model.train()

        batch = make_test_batch([("CCO", "O", 298.15)])
        out = run_model(model, batch)
        loss = out["ln_x2"].sum()
        loss.backward()

        for name, parameter in model.named_parameters():
            if parameter.grad is not None:
                assert torch.isfinite(parameter.grad).all(), f"Non-finite gradient in {name}"


class TestReproducibility:
    """Reproducibility checks for seeded model creation."""

    def test_deterministic_with_seed(self) -> None:
        """Two runs with the same seed produce the same prediction."""
        results = []
        batch = make_test_batch([("CCO", "O", 298.15)])

        for _ in range(2):
            np.random.seed(42)
            torch.manual_seed(42)
            model = TGNNSolv(cfg=make_small_config())
            model.eval()
            with torch.no_grad():
                out = run_model(model, batch)
            results.append(out["ln_x2"].item())

        assert np.isclose(results[0], results[1], atol=1e-6), (
            f"Results differ across runs: {results[0]} vs {results[1]}"
        )


class TestParameterCount:
    """Sanity checks for parameter counts."""

    def test_small_config(self) -> None:
        """The reduced integration-test config stays within a small size budget."""
        model = TGNNSolv(cfg=make_small_config())
        n_params = sum(p.numel() for p in model.parameters())
        assert n_params < 1_000_000, f"Small model too large: {n_params:,} params"
        assert n_params > 1_000, f"Small model too small: {n_params:,} params"

    def test_default_config(self) -> None:
        """The default model size remains within a reasonable expected range."""
        model = TGNNSolv(cfg=TGNNSolvConfig())
        n_params = sum(p.numel() for p in model.parameters())
        assert 500_000 < n_params < 50_000_000, f"Unexpected param count: {n_params:,}"

    def test_split_late_encoder_has_more_parameters_than_shared(self) -> None:
        """Split-late mode should add role-specific capacity over the shared baseline."""
        shared_model = TGNNSolv(cfg=make_small_config())
        split_model = TGNNSolv(cfg=make_split_late_config())
        shared_params = sum(p.numel() for p in shared_model.parameters())
        split_params = sum(p.numel() for p in split_model.parameters())
        assert split_params > shared_params
