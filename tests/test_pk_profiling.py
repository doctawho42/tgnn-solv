from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import torch

from tgnn_solv.applications.drug_properties import IonizationEstimate
from tgnn_solv.applications.pk_profiling import PKSolubilityProfiler


class FakePKProfiler(PKSolubilityProfiler):
    def __init__(self) -> None:
        self.model = object()
        self.cfg = SimpleNamespace()
        self.device = torch.device("cpu")
        self.model_family = "tgnn_solv"
        self.drug = SimpleNamespace()
        self.screener = SimpleNamespace()
        self.screener._require_smiles = lambda smiles, role: smiles
        self.screener._predict_one = self._fake_predict_one
        self.screener._molecular_weight = lambda smiles: {
            "CC(=O)Nc1ccc(O)cc1": 151.16,
            "O": 18.015,
            "CCO": 46.07,
            "CC(O)CO": 76.09,
            "CS(C)=O": 78.13,
            "OCCOCCOCCOCCO": 194.0,
            "CCCCCCCCCCCCCCCC": 226.45,
        }.get(smiles, 100.0)
        self.screener._x2_to_mg_ml = self._fake_x2_to_mg_ml

        self.drug._predict_in_water = self._fake_predict_in_water
        self.drug._descriptor_profile = lambda smiles: {
            "MolWt": 151.16,
            "MolLogP": 2.0,
            "TPSA": 78.0,
            "HBA": 2.0,
            "HBD": 2.0,
        }
        self.drug._estimate_ionization = lambda smiles: IonizationEstimate(None, 8.5, "base", "test", "basic surrogate")
        self.drug._apply_ph_correction = lambda intrinsic, pH, estimate: float(intrinsic) * (1.0 + 10.0 ** min(6.0, max(-6.0, float(estimate.basic_pka or 0.0) - float(pH)))) if estimate.basic_pka is not None else float(intrinsic)
        self.drug._dose_number = lambda dose_mg, volume_mL, solubility_mg_mL: float(dose_mg) / max(float(volume_mL) * float(solubility_mg_mL), 1e-9)
        self.drug._high_permeability = lambda descriptors: True
        self.drug.bcs_classify = lambda smiles, dose_mg, volume_mL, T: {
            "bcs_class": 2,
            "high_permeability": True,
            "high_solubility": False,
        }

    def _fake_predict_in_water(self, solute_smiles: str, *, T: float) -> dict[str, float]:
        del solute_smiles
        return {
            "solute": "CC(=O)Nc1ccc(O)cc1",
            "solvent": "O",
            "solvent_name": "Water",
            "T": float(T),
            "x2": 0.002 + 0.00005 * max(float(T) - 298.15, 0.0),
            "ln_x2": -6.0,
            "solubility_mg_mL": 1.2 + 0.02 * max(float(T) - 298.15, 0.0),
            "gamma_2": 1.5,
            "T_m": 420.0,
            "dH_fus": 32000.0,
        }

    def _fake_predict_one(self, solute_smiles: str, solvent_smiles: str, T: float) -> dict[str, float]:
        del solute_smiles, T
        base = {
            "O": (0.0025, 1.6),
            "CCO": (0.025, 1.2),
            "CC(O)CO": (0.06, 1.1),
            "CS(C)=O": (0.12, 1.0),
            "OCCOCCOCCOCCO": (0.08, 1.1),
            "CCCCCCCCCCCCCCCC": (0.0002, 4.0),
        }.get(solvent_smiles, (0.01, 1.2))
        return {
            "x2": base[0],
            "ln_x2": -4.0,
            "gamma_2": base[1],
        }

    def _fake_x2_to_mg_ml(self, x2: float, *, solute_mw: float | None, solvent_mw: float | None, solvent_density_g_ml: float | None) -> float:
        del solute_mw, solvent_mw, solvent_density_g_ml
        return float(x2) * 800.0


def test_gi_tract_profile_returns_compartments_and_absorption_proxy() -> None:
    profiler = FakePKProfiler()
    payload = profiler.gi_tract_profile("CC(=O)Nc1ccc(O)cc1", dose_mg=500.0)
    assert len(payload["compartments"]) >= 5
    assert 0.0 <= payload["f_abs_estimate"] <= 1.0
    assert payload["max_absorbable_dose"] > 0
    assert payload["rate_limiting_step"]


def test_biorelevant_media_screen_reports_food_effect() -> None:
    profiler = FakePKProfiler()
    payload = profiler.biorelevant_media_screen("CC(=O)Nc1ccc(O)cc1")
    assert len(payload["media"]) == 4
    assert payload["food_effect_prediction"] in {"positive food effect", "negative food effect", "minimal food effect", "undetermined"}
    assert "administration_recommendation" in payload


def test_iv_and_topical_screening_return_ranked_tables() -> None:
    profiler = FakePKProfiler()
    iv_df = profiler.iv_formulation_screening("CC(=O)Nc1ccc(O)cc1")
    topical_df = profiler.topical_vehicle_screening("CC(=O)Nc1ccc(O)cc1")
    assert not iv_df.empty
    assert not topical_df.empty
    assert {"vehicle_name", "iv_estimated_concentration_37C_mg_mL", "recommended"} <= set(iv_df.columns)
    assert {"vehicle_name", "thermodynamic_activity", "permeation_potential"} <= set(topical_df.columns)
