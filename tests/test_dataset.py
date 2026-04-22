"""Unit tests for dataset batching helpers."""

from __future__ import annotations

import sys
from collections import Counter

import pandas as pd
from pytest import MonkeyPatch
import torch
from torch_geometric.data import Data

sys.path.insert(0, "src")

from tgnn_solv.data import dataset as dataset_module
from tgnn_solv.data.dataset import PairTemperatureBatchSampler, make_loader
from tgnn_solv.ionic_features import IONIC_FEATURE_DIM


def _fake_graph() -> Data:
    """Create a minimal graph object for dataset tests."""
    return Data(
        x=torch.ones((2, 4), dtype=torch.float32),
        edge_index=torch.tensor([[0, 1], [1, 0]], dtype=torch.long),
        edge_attr=torch.ones((2, 2), dtype=torch.float32),
    )


def _toy_dataframe() -> pd.DataFrame:
    """Build a tiny split with repeated pairs across temperature."""
    rows = [
        ("CCO", "O", 290.0, -5.0),
        ("CCO", "O", 300.0, -4.8),
        ("CCO", "O", 310.0, -4.5),
        ("CCN", "O", 295.0, -6.0),
        ("CCN", "O", 315.0, -5.6),
        ("CCC", "CCO", 298.15, -3.9),
    ]
    return pd.DataFrame(
        {
            "solute_smiles": [row[0] for row in rows],
            "solvent_smiles": [row[1] for row in rows],
            "temperature": [row[2] for row in rows],
            "ln_x2": [row[3] for row in rows],
            "has_solubility": [True] * len(rows),
            "T_m": [350.0] * len(rows),
            "has_T_m": [True] * len(rows),
            "dH_fus": [18000.0] * len(rows),
            "has_dH_fus": [True] * len(rows),
            "hansen_d": [18.0] * len(rows),
            "hansen_p": [8.0] * len(rows),
            "hansen_h": [12.0] * len(rows),
            "has_hansen": [True] * len(rows),
            "ln_gamma_inf": [0.2] * len(rows),
            "has_gamma_inf": [True] * len(rows),
        }
    )


class TestPairTemperatureBatchSampler:
    """Verify same-pair batching for temperature consistency losses."""

    def test_sampler_covers_all_indices_once(self) -> None:
        """The sampler should partition the dataset without dropping samples."""
        pair_keys = ["pair_a", "pair_a", "pair_a", "pair_b", "pair_b", "pair_c"]
        sampler = PairTemperatureBatchSampler(
            pair_keys,
            batch_size=4,
            min_group_size=2,
            group_chunk_size=3,
            seed=7,
        )

        batches = list(iter(sampler))
        flat_indices = [idx for batch in batches for idx in batch]

        assert sorted(flat_indices) == list(range(len(pair_keys)))
        assert any(
            max(Counter(pair_keys[idx] for idx in batch).values()) >= 2
            for batch in batches
        )

    def test_make_loader_keeps_multi_temperature_pairs_together(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Pair-aware batching should surface repeated pair keys in a train batch."""
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_graph",
            lambda _smiles: _fake_graph(),
        )

        loader = make_loader(
            _toy_dataframe(),
            batch_size=4,
            shuffle=True,
            use_pair_temperature_batching=True,
            pair_temperature_min_group_size=2,
            pair_temperature_group_chunk_size=3,
            seed=11,
        )

        _, _, targets = next(iter(loader))
        pair_counts = Counter(targets["pair_key"])

        assert max(pair_counts.values()) >= 2

        grouped_temperatures: dict[str, list[float]] = {}
        for pair_key, temperature in zip(targets["pair_key"], targets["T"].tolist()):
            grouped_temperatures.setdefault(pair_key, []).append(temperature)

        assert any(
            len(temperatures) >= 2 and len(set(temperatures)) >= 2
            for temperatures in grouped_temperatures.values()
        )

    def test_make_loader_emits_morgan_features_when_enabled(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Morgan fingerprints should be present in the batch when requested."""
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_graph",
            lambda _smiles: _fake_graph(),
        )
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_morgan_fp",
            lambda _smiles, radius=2, n_bits=256: torch.ones(n_bits, dtype=torch.float32).numpy(),
        )

        loader = make_loader(
            _toy_dataframe(),
            batch_size=4,
            shuffle=False,
            use_morgan_features=True,
            morgan_n_bits=256,
        )

        _, _, targets = next(iter(loader))
        assert "solute_morgan_fp" in targets
        assert "solvent_morgan_fp" in targets
        assert tuple(targets["solute_morgan_fp"].shape) == (4, 256)
        assert tuple(targets["solvent_morgan_fp"].shape) == (4, 256)

    def test_make_loader_emits_ionic_features_when_enabled(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Ionic/contact-pair context should be available as pair-level targets."""
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_graph",
            lambda _smiles: _fake_graph(),
        )

        loader = make_loader(
            _toy_dataframe(),
            batch_size=4,
            shuffle=False,
            use_ionic_features=True,
        )

        _, _, targets = next(iter(loader))
        assert "ionic_features" in targets
        assert tuple(targets["ionic_features"].shape) == (4, IONIC_FEATURE_DIM)

    def test_curated_decomposition_solute_masks_invalid_fusion_labels(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Known no-melting solutes should not train the standard T_m/dH heads."""
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_graph",
            lambda _smiles: _fake_graph(),
        )
        delphinidin = "Oc1cc(O)c2cc(O)c(-c3cc(O)c(O)c(O)c3)[o+]c2c1.[Cl-]"
        df = _toy_dataframe().iloc[:1].copy()
        df["solute_smiles"] = [delphinidin]
        df["solvent_smiles"] = ["CC(C)=O"]
        df["has_T_m"] = [True]
        df["has_dH_fus"] = [True]
        df["T_m"] = [623.0]
        df["dH_fus"] = [40000.0]

        loader = make_loader(df, batch_size=1, shuffle=False)

        _, _, targets = next(iter(loader))
        assert targets["has_raw_T_m"].tolist() == [True]
        assert targets["has_valid_T_m"].tolist() == [False]
        assert targets["T_m_mask"].tolist() == [False]
        assert targets["has_decomposition_T"].tolist() == [True]
        assert targets["has_valid_dH_fus"].tolist() == [False]
        assert targets["crystal_handling"] == ["exclude_from_crystal_branch"]

    def test_make_loader_emits_vant_hoff_fit_targets(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Van't Hoff fit columns should be exposed as optional targets."""
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_graph",
            lambda _smiles: _fake_graph(),
        )
        df = _toy_dataframe()
        df["has_vh_fit"] = [True, True, True, False, False, False]
        df["vh_fit_slope"] = [-2500.0, -2500.0, -2500.0, 0.0, 0.0, 0.0]
        df["vh_fit_intercept"] = [3.0, 3.0, 3.0, 0.0, 0.0, 0.0]
        df["vh_fit_r2"] = [0.99, 0.99, 0.99, 0.0, 0.0, 0.0]
        df["vh_fit_rmse"] = [0.02, 0.02, 0.02, 0.0, 0.0, 0.0]
        df["vh_fit_weight"] = [0.8, 0.8, 0.8, 0.0, 0.0, 0.0]

        loader = make_loader(df, batch_size=4, shuffle=False)

        _, _, targets = next(iter(loader))
        assert "vh_fit_slope" in targets
        assert targets["vh_fit_mask"].dtype == torch.bool
        assert targets["vh_fit_mask"].tolist()[:3] == [True, True, True]
        assert torch.allclose(
            targets["vh_fit_slope"][:3],
            torch.full((3,), -2500.0),
        )
        assert torch.allclose(
            targets["vh_fit_weight"][:3],
            torch.full((3,), 0.8),
        )

    def test_make_loader_emits_descriptor_priors_when_enabled(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Descriptor prior features should be present in the batch when requested."""
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_graph",
            lambda _smiles: _fake_graph(),
        )
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_descriptor_prior_features",
            lambda _smiles: torch.arange(10, dtype=torch.float32).numpy(),
        )

        loader = make_loader(
            _toy_dataframe(),
            batch_size=4,
            shuffle=False,
            use_descriptor_priors=True,
        )

        _, _, targets = next(iter(loader))
        assert "solute_descriptor_prior_features" in targets
        assert "solvent_descriptor_prior_features" in targets
        assert tuple(targets["solute_descriptor_prior_features"].shape) == (4, 10)
        assert tuple(targets["solvent_descriptor_prior_features"].shape) == (4, 10)

    def test_make_loader_emits_full_descriptors_when_enabled(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Full RDKit descriptor vectors should be present for DirectGNN augmentation."""
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_graph",
            lambda _smiles: _fake_graph(),
        )
        monkeypatch.setattr(
            dataset_module,
            "compute_molecular_descriptors",
            lambda _smiles: torch.arange(12, dtype=torch.float32).numpy(),
        )

        loader = make_loader(
            _toy_dataframe(),
            batch_size=4,
            shuffle=False,
            use_descriptor_augmentation=True,
        )

        _, _, targets = next(iter(loader))
        assert "solute_descriptors" in targets
        assert "solvent_descriptors" in targets
        assert tuple(targets["solute_descriptors"].shape) == (4, 12)
        assert tuple(targets["solvent_descriptors"].shape) == (4, 12)

    def test_make_loader_emits_group_priors_when_enabled(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Fixed group prior features should be present in the batch when requested."""
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_graph",
            lambda _smiles: _fake_graph(),
        )
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_group_prior_features",
            lambda _smiles: torch.arange(20, dtype=torch.float32).numpy(),
        )

        loader = make_loader(
            _toy_dataframe(),
            batch_size=4,
            shuffle=False,
            use_group_priors=True,
        )

        _, _, targets = next(iter(loader))
        assert "solute_group_prior_features" in targets
        assert "solvent_group_prior_features" in targets
        assert tuple(targets["solute_group_prior_features"].shape) == (4, 20)
        assert tuple(targets["solvent_group_prior_features"].shape) == (4, 20)

    def test_make_loader_emits_crystal_gc_priors_when_enabled(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Fixed crystal GC priors should be present in the batch when requested."""
        monkeypatch.setattr(
            dataset_module,
            "smiles_to_graph",
            lambda _smiles: _fake_graph(),
        )
        monkeypatch.setattr(
            dataset_module,
            "compute_gc_priors",
            lambda _smiles: {
                "T_m_gc": 410.0,
                "dH_fus_gc": 21000.0,
                "dCp_fus_gc": 12.5,
            },
        )

        loader = make_loader(
            _toy_dataframe(),
            batch_size=4,
            shuffle=False,
            use_gc_priors_crystal=True,
        )

        _, _, targets = next(iter(loader))
        assert "T_m_gc" in targets
        assert "dH_fus_gc" in targets
        assert "dCp_fus_gc" in targets
        assert tuple(targets["T_m_gc"].shape) == (4,)
        assert tuple(targets["dH_fus_gc"].shape) == (4,)
        assert tuple(targets["dCp_fus_gc"].shape) == (4,)
