from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import torch

from tgnn_solv.applications.drug_properties import DrugPropertyPredictor, IonizationEstimate


class FakeScreener:
    MG_ML_ASSUMPTION = "screening assumption"

    def __init__(self) -> None:
        self.solvent_library = [
            {"name": "Water", "smiles": "O"},
            {"name": "Ethanol", "smiles": "CCO"},
            {"name": "DMSO", "smiles": "CS(C)=O"},
            {"name": "Acetone", "smiles": "CC(=O)C"},
        ]
        self._library_by_smiles = {
            "O": {"name": "Water", "smiles": "O", "density_g_mL": 0.997},
        }

    def _require_smiles(self, smiles: str, role: str) -> str:
        del role
        return smiles

    def _molecular_weight(self, smiles: str) -> float | None:
        mapping = {
            "CC(=O)Nc1ccc(O)cc1": 151.16,
            "O": 18.015,
            "CCO": 46.07,
            "CS(C)=O": 78.13,
            "CC(=O)C": 58.08,
        }
        return mapping.get(smiles, 100.0)

    def screen(self, solute_smiles: str, T: float, top_k: int, filters: dict | None, return_details: bool) -> pd.DataFrame:
        del solute_smiles, T, top_k, filters, return_details
        return pd.DataFrame(
            {
                "solvent_name": ["Water", "Ethanol", "DMSO", "Acetone"],
                "solubility_mg_mL": [2.5, 7.0, 15.0, 0.4],
                "x2": [0.01, 0.03, 0.08, 0.001],
                "ln_x2": [-4.6, -3.5, -2.5, -6.9],
            }
        )

    def _temperature_scan(self, solute_smiles: str, solvent_smiles: str, *, T_min: float, T_max: float, n_points: int) -> pd.DataFrame:
        del solute_smiles, solvent_smiles
        temps = torch.linspace(T_min, T_max, n_points).tolist()
        x2 = [0.01 + 0.0008 * (temp - T_min) for temp in temps]
        return pd.DataFrame(
            {
                "T": temps,
                "x2": x2,
                "ln_x2": [float(torch.log(torch.tensor(v)).item()) for v in x2],
            }
        )

    def _predict_one(self, solute_smiles: str, solvent_smiles: str, T: float) -> dict[str, float]:
        del solute_smiles, T
        mapping = {
            "O": {"x2": 0.01, "ln_x2": -4.605, "T_m": 420.0, "dH_fus": 32000.0, "hansen_sol": [18.0, 9.0, 14.0], "hansen_slv": [15.5, 16.0, 42.3]},
            "CCO": {"x2": 0.03, "ln_x2": -3.507, "T_m": 420.0, "dH_fus": 32000.0, "hansen_sol": [18.0, 9.0, 14.0], "hansen_slv": [15.8, 8.8, 19.4]},
            "CS(C)=O": {"x2": 0.08, "ln_x2": -2.526, "T_m": 420.0, "dH_fus": 32000.0, "hansen_sol": [18.0, 9.0, 14.0], "hansen_slv": [18.4, 16.4, 10.2]},
            "CC(=O)C": {"x2": 0.001, "ln_x2": -6.908, "T_m": 420.0, "dH_fus": 32000.0, "hansen_sol": [18.0, 9.0, 14.0], "hansen_slv": [15.5, 10.4, 7.0]},
        }
        return mapping.get(solvent_smiles, {"x2": 0.02, "ln_x2": -3.9, "T_m": 420.0, "dH_fus": 32000.0, "hansen_sol": [18.0, 9.0, 14.0], "hansen_slv": [16.0, 8.0, 10.0]})

    def _x2_to_mg_ml(self, x2: float, *, solute_mw: float | None, solvent_mw: float | None, solvent_density_g_ml: float | None) -> float:
        del x2, solute_mw, solvent_mw, solvent_density_g_ml
        return 2.5


class FakeDrugPredictor(DrugPropertyPredictor):
    def __init__(self) -> None:
        self.model = object()
        self.cfg = SimpleNamespace()
        self.device = torch.device("cpu")
        self.model_family = "tgnn_solv"
        self.screener = FakeScreener()
        self._water_meta = {"name": "Water", "smiles": "O", "density_g_mL": 0.997}

    def _predict_in_water(self, solute_smiles: str, *, T: float) -> dict[str, float]:
        del solute_smiles, T
        return {
            "solute": "CC(=O)Nc1ccc(O)cc1",
            "solvent": "O",
            "solvent_name": "Water",
            "T": 310.15,
            "x2": 0.01,
            "ln_x2": -4.605,
            "solubility_mg_mL": 2.5,
            "T_m": 420.0,
            "dH_fus": 32000.0,
            "hansen_sol": [18.0, 9.0, 14.0],
            "hansen_slv": [15.5, 16.0, 42.3],
        }

    def _descriptor_profile(self, smiles: str) -> dict[str, float]:
        del smiles
        return {
            "MolWt": 151.16,
            "MolLogP": 1.4,
            "TPSA": 76.0,
            "HBA": 2.0,
            "HBD": 2.0,
            "RotBonds": 1.0,
        }

    def _estimate_ionization(self, smiles: str) -> IonizationEstimate:
        del smiles
        return IonizationEstimate(None, None, "neutral_or_unknown", "none", "Neutral test surrogate.")

    def _combine_components(self, left_smiles: str, right_smiles: str) -> str | None:
        return f"{left_smiles}.{right_smiles}"

    def _morgan_fingerprint(self, smiles: str):
        del smiles
        return None


def test_bcs_classification_high_solubility_high_permeability() -> None:
    predictor = FakeDrugPredictor()
    payload = predictor.bcs_classify("CC(=O)Nc1ccc(O)cc1", dose_mg=100.0, volume_mL=250.0, T=310.15)
    assert payload["bcs_class"] == 1
    assert payload["high_solubility"] is True
    assert payload["high_permeability"] is True
    assert payload["dose_number"] is not None and payload["dose_number"] <= 1.0


def test_bcs_classification_flips_with_higher_dose() -> None:
    predictor = FakeDrugPredictor()
    payload = predictor.bcs_classify("CC(=O)Nc1ccc(O)cc1", dose_mg=2000.0, volume_mL=250.0, T=310.15)
    assert payload["bcs_class"] == 2
    assert payload["high_solubility"] is False
    assert payload["high_permeability"] is True


def test_developability_score_is_bounded_and_informative() -> None:
    predictor = FakeDrugPredictor()
    payload = predictor.developability_score("CC(=O)Nc1ccc(O)cc1", T=310.15)
    assert 0.0 <= payload["developability_score"] <= 1.0
    assert set(payload["component_scores"]) == {
        "solubility",
        "crystal_stability",
        "lipophilicity",
        "solvent_diversity",
        "temperature_sensitivity",
    }
    assert payload["traffic_light"] in {"green", "yellow", "red"}


def test_ph_correction_formula_matches_expected_trend() -> None:
    predictor = FakeDrugPredictor()
    estimate = IonizationEstimate(None, 9.0, "base", "test_heuristic", "Basic center")
    corrected = predictor._apply_ph_correction(1.0, 1.0, estimate)
    assert corrected is not None
    assert corrected > 1.0


def test_salt_cocrystal_screening_flags_approximation() -> None:
    predictor = FakeDrugPredictor()
    df = predictor.salt_cocrystal_impact(
        "CC(=O)Nc1ccc(O)cc1",
        ["O=C(O)C(O)C(O)CO", "not_a_smiles"],
        T=310.15,
    )
    assert not df.empty
    assert "caveats" in df.columns
    assert df["confidence"].notna().any()
