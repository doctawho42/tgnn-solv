from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import torch

from tgnn_solv.applications import BUILTIN_SOLVENT_LIBRARY, SolventScreener


CUSTOM_LIBRARY = [
    {
        "name": "Ethanol",
        "smiles": "CCO",
        "solvent_class": "alcohol",
        "boiling_point_K": 351.5,
        "density_g_mL": 0.789,
        "ild_class": "ICH Class 3",
        "green_score": 8,
        "cost_relative": "low",
        "h_bond_donor": True,
        "h_bond_acceptor": True,
        "protic": True,
        "miscible_with_water": True,
        "hansen_d": 15.8,
        "hansen_p": 8.8,
        "hansen_h": 19.4,
    },
    {
        "name": "Water",
        "smiles": "O",
        "solvent_class": "water",
        "boiling_point_K": 373.15,
        "density_g_mL": 0.997,
        "ild_class": "ICH Class 3",
        "green_score": 10,
        "cost_relative": "low",
        "h_bond_donor": True,
        "h_bond_acceptor": True,
        "protic": True,
        "miscible_with_water": True,
        "hansen_d": 15.5,
        "hansen_p": 16.0,
        "hansen_h": 42.3,
    },
    {
        "name": "Ethyl acetate",
        "smiles": "CCOC(=O)C",
        "solvent_class": "ester",
        "boiling_point_K": 350.25,
        "density_g_mL": 0.897,
        "ild_class": "ICH Class 3",
        "green_score": 8,
        "cost_relative": "low",
        "h_bond_donor": False,
        "h_bond_acceptor": True,
        "protic": False,
        "miscible_with_water": False,
        "hansen_d": 15.8,
        "hansen_p": 5.3,
        "hansen_h": 7.2,
    },
    {
        "name": "DCM",
        "smiles": "ClCCl",
        "solvent_class": "chlorinated",
        "boiling_point_K": 312.95,
        "density_g_mL": 1.326,
        "ild_class": "ICH Class 2",
        "green_score": 2,
        "cost_relative": "low",
        "h_bond_donor": False,
        "h_bond_acceptor": False,
        "protic": False,
        "miscible_with_water": False,
        "hansen_d": 18.2,
        "hansen_p": 6.3,
        "hansen_h": 6.1,
    },
]


class FakeScreener(SolventScreener):
    def __init__(self) -> None:
        super().__init__(
            model=object(),
            cfg=SimpleNamespace(),
            device=torch.device("cpu"),
            solvent_library=CUSTOM_LIBRARY,
        )

    def _predict_one(self, solute_smiles: str, solvent_smiles: str, T: float) -> dict[str, float]:
        del solute_smiles
        base = {
            "CCO": 0.10,
            "O": 0.003,
            "CCOC(C)=O": 0.08,
            "ClCCl": 0.09,
        }[solvent_smiles]
        temperature_factor = max(0.2, (T - 240.0) / 100.0)
        x2 = base * temperature_factor
        return {
            "x2": x2,
            "ln_x2": float(torch.log(torch.tensor(x2)).item()),
            "gamma_2": 1.2,
            "Phi": 2.1,
            "T_m": 440.0,
            "dH_fus": 23000.0,
            "tau_12": 0.7,
            "tau_21": 0.5,
            "Ra": 6.0 if solvent_smiles in {"CCO", "CCOC(=O)C"} else 10.0,
            "hansen_sol": [18.0, 10.0, 14.0],
            "hansen_slv": [16.0, 8.0, 10.0],
        }

    def _temperature_scan(
        self,
        solute_smiles: str,
        solvent_smiles: str,
        *,
        T_min: float,
        T_max: float,
        n_points: int,
    ) -> pd.DataFrame:
        del solute_smiles, solvent_smiles
        temperatures = torch.linspace(T_min, T_max, n_points).tolist()
        x2 = [0.002 + 0.0006 * (temp - T_min) for temp in temperatures]
        return pd.DataFrame(
            {
                "T": temperatures,
                "x2": x2,
                "ln_x2": [float(torch.log(torch.tensor(value)).item()) for value in x2],
                "gamma_2": [1.2 for _ in temperatures],
            }
        )


def test_builtin_solvent_library_contains_required_examples() -> None:
    names = {entry["name"] for entry in BUILTIN_SOLVENT_LIBRARY}
    required = {"Water", "Ethanol", "Acetone", "Ethyl acetate", "DMF", "DMSO", "Supercritical CO2"}
    assert required.issubset(names)


def test_screen_sorts_and_filters_solvents() -> None:
    screener = FakeScreener()
    df = screener.screen(
        "CC(=O)Nc1ccc(O)cc1",
        T=298.15,
        top_k=3,
        filters={"min_green_score": 5, "exclude_classes": ["chlorinated"]},
    )
    assert not df.empty
    assert "solubility_mg_mL" in df.columns
    assert "confidence" in df.columns
    assert "DCM" not in set(df["solvent_name"])
    assert df.iloc[0]["solvent_name"] == "Ethanol"


def test_crystallization_window_reports_positive_yield() -> None:
    screener = FakeScreener()
    payload = screener.crystallization_window("CC(=O)Nc1ccc(O)cc1", "CCO", T_hot=350.0, T_cold=280.0, n_points=8)
    assert payload["x2_hot"] > payload["x2_cold"]
    assert payload["theoretical_yield"] > 0
    assert payload["supersaturation_ratio"] > 1
    assert payload["temperature_scan"].shape[0] == 8


def test_antisolvent_and_green_replacement_workflows() -> None:
    screener = FakeScreener()
    anti_df = screener.antisolvent_screening("CC(=O)Nc1ccc(O)cc1", "CCO", T=298.15)
    assert not anti_df.empty
    assert anti_df.iloc[0]["recommended"] in {True, False}
    assert "Water" in set(anti_df["antisolvent_name"])

    green_df = screener.green_solvent_replacement("CC(=O)Nc1ccc(O)cc1", "ClCCl", T=298.15, min_solubility_fraction=0.5)
    assert not green_df.empty
    assert "solubility_retention" in green_df.columns
    assert green_df["green_improvement"].max() > 0


def test_solvent_swap_path_returns_steps() -> None:
    screener = FakeScreener()
    path = screener.solvent_swap_path("CC(=O)Nc1ccc(O)cc1", "ClCCl", "CCOC(C)=O", T=298.15, max_steps=2)
    assert path
    assert {"from_solvent", "to_solvent", "miscibility", "x2_in_from", "x2_in_to", "volume_ratio_estimate"} <= set(path[0])
