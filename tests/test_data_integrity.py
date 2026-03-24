"""Data integrity tests for processed TGNN-Solv splits."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


DATA_DIR = Path("notebooks/data/processed")
TRAIN_PATH = DATA_DIR / "train.csv"
VAL_PATH = DATA_DIR / "val.csv"
TEST_PATH = DATA_DIR / "test.csv"

data_exists = pytest.mark.skipif(
    not all(path.exists() for path in [TRAIN_PATH, VAL_PATH, TEST_PATH]),
    reason="Processed data not found. Run notebooks/01_prepare_data.ipynb first.",
)


@data_exists
class TestDataLeakage:
    """Checks for split leakage across processed datasets."""

    @pytest.fixture(autouse=True)
    def load_data(self) -> None:
        """Load train, validation, and test splits for each test."""
        self.train = pd.read_csv(TRAIN_PATH)
        self.val = pd.read_csv(VAL_PATH)
        self.test = pd.read_csv(TEST_PATH)

    def test_no_exact_row_overlap(self) -> None:
        """No exact `(solute, solvent, temperature)` rows appear in multiple splits."""
        for name_a, df_a, name_b, df_b in [
            ("train", self.train, "val", self.val),
            ("train", self.train, "test", self.test),
            ("val", self.val, "test", self.test),
        ]:
            keys_a = set(
                zip(
                    df_a["solute_smiles"],
                    df_a["solvent_smiles"],
                    df_a["temperature"],
                )
            )
            keys_b = set(
                zip(
                    df_b["solute_smiles"],
                    df_b["solvent_smiles"],
                    df_b["temperature"],
                )
            )
            overlap = keys_a & keys_b
            assert len(overlap) == 0, f"{name_a}/{name_b} have {len(overlap)} overlapping rows"

    def test_no_solute_leakage_scaffold_split(self) -> None:
        """Test solute scaffolds should not substantially overlap with training scaffolds."""
        try:
            from rdkit.Chem.Scaffolds.MurckoScaffold import MurckoScaffoldSmiles
        except ImportError:
            pytest.skip("RDKit not available")

        def get_scaffolds(smiles_series: pd.Series) -> set[str]:
            scaffolds: set[str] = set()
            for smi in smiles_series.unique():
                try:
                    scaffolds.add(MurckoScaffoldSmiles(smi))
                except Exception:
                    pass
            return scaffolds

        train_scaffolds = get_scaffolds(self.train["solute_smiles"])
        test_scaffolds = get_scaffolds(self.test["solute_smiles"])
        overlap = train_scaffolds & test_scaffolds

        overlap_frac = len(overlap) / max(len(test_scaffolds), 1)
        assert overlap_frac < 0.1, (
            f"Scaffold overlap: {len(overlap)}/{len(test_scaffolds)} ({overlap_frac:.1%})"
        )


@data_exists
class TestDataQuality:
    """Sanity checks for processed data quality."""

    @pytest.fixture(autouse=True)
    def load_data(self) -> None:
        """Load train, validation, and test splits for each test."""
        self.train = pd.read_csv(TRAIN_PATH)
        self.val = pd.read_csv(VAL_PATH)
        self.test = pd.read_csv(TEST_PATH)
        self.all_data = pd.concat([self.train, self.val, self.test], ignore_index=True)

    def test_required_columns_exist(self) -> None:
        """All required columns must be present in every split."""
        required = ["solute_smiles", "solvent_smiles", "temperature", "ln_x2"]
        for df_name, df in [("train", self.train), ("val", self.val), ("test", self.test)]:
            for col in required:
                assert col in df.columns, f"Missing column '{col}' in {df_name}"

    def test_no_nan_in_targets(self) -> None:
        """Rows with solubility labels must not contain NaN targets."""
        for df_name, df in [("train", self.train), ("val", self.val), ("test", self.test)]:
            if "has_solubility" in df.columns:
                sol_mask = df["has_solubility"].astype(bool)
                nan_count = df.loc[sol_mask, "ln_x2"].isna().sum()
            else:
                nan_count = df["ln_x2"].isna().sum()
            assert nan_count == 0, f"{nan_count} NaN values in ln_x2 in {df_name}"

    def test_temperature_range(self) -> None:
        """Temperatures must stay within a physically reasonable range."""
        temperatures = self.all_data["temperature"]
        assert temperatures.min() > 100, f"Min temperature too low: {temperatures.min()}"
        assert temperatures.max() < 1000, f"Max temperature too high: {temperatures.max()}"

    def test_ln_x2_range(self) -> None:
        """`ln(x2)` values must stay within a reasonable physical range."""
        mask = self.all_data["ln_x2"].notna()
        ln_x2 = self.all_data.loc[mask, "ln_x2"]
        assert ln_x2.max() <= 0.1, f"ln_x2 max too high: {ln_x2.max()} (x2 > 1?)"
        assert ln_x2.min() > -35, f"ln_x2 min too low: {ln_x2.min()}"

    def test_valid_smiles(self) -> None:
        """A representative sample of SMILES strings must parse with RDKit."""
        try:
            from rdkit import Chem
        except ImportError:
            pytest.skip("RDKit not available")

        sample_size = int(np.minimum(500, len(self.all_data)))
        sample = self.all_data.sample(sample_size, random_state=42)
        invalid = []
        for _, row in sample.iterrows():
            for col in ["solute_smiles", "solvent_smiles"]:
                mol = Chem.MolFromSmiles(row[col])
                if mol is None:
                    invalid.append((col, row[col]))

        assert len(invalid) == 0, f"Invalid SMILES found: {invalid[:5]}"

    def test_split_proportions(self) -> None:
        """Split proportions should remain close to 80/10/10."""
        total = len(self.train) + len(self.val) + len(self.test)
        train_frac = len(self.train) / total
        val_frac = len(self.val) / total
        test_frac = len(self.test) / total

        assert 0.7 < train_frac < 0.9, f"Train fraction: {train_frac:.2%}"
        assert 0.05 < val_frac < 0.2, f"Val fraction: {val_frac:.2%}"
        assert 0.05 < test_frac < 0.2, f"Test fraction: {test_frac:.2%}"
