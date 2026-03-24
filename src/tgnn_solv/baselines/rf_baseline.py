"""Random Forest baseline on RDKit descriptors for TGNN-Solv comparisons."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.preprocessing import StandardScaler
except Exception as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "scikit-learn is required for rf_baseline.py. "
        "Install it with `pip install scikit-learn`."
    ) from exc

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    from rdkit.ML.Descriptors import MoleculeDescriptors
except Exception as exc:  # pragma: no cover - optional dependency
    raise ImportError(
        "RDKit is required for rf_baseline.py. "
        "Install it with `conda install -c conda-forge rdkit` or an equivalent package."
    ) from exc


SUPPORTED_TREE_REGRESSORS = {
    "random_forest": RandomForestRegressor,
    "gradient_boosting": GradientBoostingRegressor,
}

REQUIRED_COLUMNS = {"solute_smiles", "solvent_smiles", "temperature", "ln_x2"}


def compute_pair_descriptors(
    solute_smiles: str,
    solvent_smiles: str,
    temperature: float,
) -> np.ndarray | None:
    """Compute concatenated RDKit descriptors for a solute-solvent pair.

    Args:
        solute_smiles: Solute SMILES string.
        solvent_smiles: Solvent SMILES string.
        temperature: Temperature in Kelvin.

    Returns:
        Concatenated descriptor vector, or None if either molecule is invalid.
    """
    mol_sol = Chem.MolFromSmiles(solute_smiles)
    mol_slv = Chem.MolFromSmiles(solvent_smiles)
    if mol_sol is None or mol_slv is None:
        return None

    calc = MoleculeDescriptors.MolecularDescriptorCalculator(
        [name for name, _ in Descriptors.descList]
    )
    desc_sol = np.array(calc.CalcDescriptors(mol_sol), dtype=float)
    desc_slv = np.array(calc.CalcDescriptors(mol_slv), dtype=float)

    desc_sol = np.nan_to_num(desc_sol, nan=0.0, posinf=1e6, neginf=-1e6)
    desc_slv = np.nan_to_num(desc_slv, nan=0.0, posinf=1e6, neginf=-1e6)

    inv_temperature = 1.0 / float(temperature)
    return np.concatenate([desc_sol, desc_slv, [float(temperature), inv_temperature]])


class RFBaseline:
    """Random Forest baseline trained on RDKit pair descriptors."""

    def __init__(
        self,
        n_estimators: int = 500,
        max_depth: int = 30,
        n_jobs: int = -1,
        random_state: int = 42,
    ) -> None:
        """Initialize the baseline model and feature scaler.

        Args:
            n_estimators: Number of trees in the forest.
            max_depth: Maximum tree depth.
            n_jobs: Number of parallel jobs for fitting and inference.
            random_state: Random seed for reproducibility.
        """
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            n_jobs=n_jobs,
            random_state=random_state,
        )
        self.scaler = StandardScaler()
        self.fitted = False

    @staticmethod
    def _validate_columns(df: pd.DataFrame) -> None:
        """Validate that a dataframe contains the required columns.

        Args:
            df: Input dataframe.

        Raises:
            ValueError: If any required column is missing.
        """
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

    def fit(self, train_df: pd.DataFrame) -> RFBaseline:
        """Fit the baseline model on a training dataframe.

        Args:
            train_df: Training dataframe with pair identifiers and targets.

        Returns:
            The fitted baseline instance.
        """
        self._validate_columns(train_df)

        valid_descriptors: list[np.ndarray] = []
        targets: list[float] = []

        for row in train_df.itertuples(index=False):
            descriptor = compute_pair_descriptors(
                row.solute_smiles,
                row.solvent_smiles,
                row.temperature,
            )
            if descriptor is None:
                continue

            target = float(row.ln_x2)
            if not np.isfinite(target):
                continue

            valid_descriptors.append(descriptor)
            targets.append(target)

        if not valid_descriptors:
            raise ValueError("No valid training samples were found for RFBaseline.")

        X = np.array(valid_descriptors, dtype=float)
        y = np.array(targets, dtype=float)

        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.model.fit(X_scaled, y)
        self.fitted = True

        print(
            f"RFBaseline fitted on {len(X)} samples "
            f"({len(train_df) - len(X)} skipped)"
        )
        return self

    def predict(self, test_df: pd.DataFrame) -> tuple[np.ndarray, list[int]]:
        """Predict solubility values for valid rows in a dataframe.

        Args:
            test_df: Test dataframe with pair identifiers.

        Returns:
            Tuple of predictions and valid dataframe indices.
        """
        assert self.fitted, "RFBaseline must be fitted before calling predict()."
        self._validate_columns(test_df)

        valid_descriptors: list[np.ndarray] = []
        valid_indices: list[int] = []

        for idx, row in enumerate(test_df.itertuples(index=False)):
            descriptor = compute_pair_descriptors(
                row.solute_smiles,
                row.solvent_smiles,
                row.temperature,
            )
            if descriptor is None:
                continue

            valid_descriptors.append(descriptor)
            valid_indices.append(idx)

        if not valid_descriptors:
            return np.array([], dtype=float), []

        X = np.array(valid_descriptors, dtype=float)
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        return np.asarray(predictions, dtype=float), valid_indices

    def evaluate(self, test_df: pd.DataFrame) -> dict[str, float | int]:
        """Evaluate the baseline on a test dataframe.

        Args:
            test_df: Test dataframe with targets.

        Returns:
            Dictionary with regression metrics and sample counts.
        """
        predictions, valid_idx = self.predict(test_df)
        if len(valid_idx) == 0:
            return {
                "mae": float("nan"),
                "rmse": float("nan"),
                "r2": float("nan"),
                "pearson_r": float("nan"),
                "n_samples": 0,
                "n_skipped": len(test_df),
            }

        true = test_df.iloc[valid_idx]["ln_x2"].values.astype(float)

        mae = float(mean_absolute_error(true, predictions))
        rmse = float(np.sqrt(mean_squared_error(true, predictions)))
        r2 = float(r2_score(true, predictions))

        if len(true) > 1 and np.std(true) > 0 and np.std(predictions) > 0:
            pearson_r = float(np.corrcoef(true, predictions)[0, 1])
        else:
            pearson_r = float("nan")

        return {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "pearson_r": pearson_r,
            "n_samples": int(len(valid_idx)),
            "n_skipped": int(len(test_df) - len(valid_idx)),
        }


def _json_ready(metrics: dict[str, float | int]) -> dict[str, float | int | None]:
    """Convert non-finite metric values to JSON-safe values.

    Args:
        metrics: Metrics dictionary.

    Returns:
        JSON-safe metrics dictionary.
    """
    output: dict[str, float | int | None] = {}
    for key, value in metrics.items():
        if isinstance(value, (float, np.floating)):
            output[key] = float(value) if np.isfinite(value) else None
        elif isinstance(value, (int, np.integer)):
            output[key] = int(value)
        else:
            output[key] = value
    return output


def main() -> None:
    """Train and evaluate the Random Forest baseline from CSV files."""
    parser = argparse.ArgumentParser(
        description="Train and evaluate a Random Forest baseline on RDKit descriptors."
    )
    parser.add_argument("--train", type=str, required=True, help="Path to the train CSV file.")
    parser.add_argument("--test", type=str, required=True, help="Path to the test CSV file.")
    parser.add_argument(
        "--output",
        type=str,
        default="results/rf_baseline.json",
        help="Path to save evaluation metrics as JSON.",
    )
    args = parser.parse_args()

    train_df = pd.read_csv(args.train)
    test_df = pd.read_csv(args.test)

    baseline = RFBaseline()
    baseline.fit(train_df)
    metrics = baseline.evaluate(test_df)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(_json_ready(metrics), handle, indent=2)

    print("Random Forest baseline results:")
    for key in ("mae", "rmse", "r2", "pearson_r", "n_samples", "n_skipped"):
        print(f"  {key}: {metrics[key]}")
    print(f"Saved metrics to {output_path}")


if __name__ == "__main__":
    main()
