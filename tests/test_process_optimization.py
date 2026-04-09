from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import torch

from tgnn_solv.applications.process_optimization import ProcessOptimizer
from tgnn_solv.applications.solvent_screening import SolventScreener


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
        "smiles": "CCOC(C)=O",
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
        species_bias = {
            "CC(=O)Nc1ccc(O)cc1": {"CCO": 0.09, "O": 0.002, "CCOC(C)=O": 0.07, "ClCCl": 0.08},
            "CCO": {"CCO": 0.25, "O": 0.45, "CCOC(C)=O": 0.18, "ClCCl": 0.05},
            "CCN": {"CCO": 0.22, "O": 0.40, "CCOC(C)=O": 0.12, "ClCCl": 0.04},
            "CC(=O)O": {"CCO": 0.06, "O": 0.12, "CCOC(C)=O": 0.02, "ClCCl": 0.01},
        }
        base = species_bias.get(solute_smiles, species_bias["CC(=O)Nc1ccc(O)cc1"])[solvent_smiles]
        temperature_factor = max(0.2, (T - 240.0) / 90.0)
        x2 = min(0.9, base * temperature_factor)
        return {
            "x2": x2,
            "ln_x2": float(torch.log(torch.tensor(x2)).item()),
            "gamma_2": 1.15,
            "Phi": 2.0,
            "T_m": 440.0,
            "dH_fus": 22500.0,
            "tau_12": 0.7,
            "tau_21": 0.5,
            "Ra": 5.0 if solvent_smiles in {"CCO", "CCOC(C)=O"} else 11.0,
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
        del solvent_smiles
        temperatures = torch.linspace(T_min, T_max, n_points).tolist()
        base = 0.001 if solute_smiles == "CC(=O)Nc1ccc(O)cc1" else 0.01
        slope = 0.00045 if solute_smiles == "CC(=O)Nc1ccc(O)cc1" else 0.0002
        x2 = [base + slope * (temp - T_min) for temp in temperatures]
        return pd.DataFrame(
            {
                "T": temperatures,
                "x2": x2,
                "ln_x2": [float(torch.log(torch.tensor(value)).item()) for value in x2],
                "gamma_2": [1.15 for _ in temperatures],
            }
        )


class FakeProcessOptimizer(ProcessOptimizer):
    def __init__(self) -> None:
        self.model = object()
        self.cfg = SimpleNamespace()
        self.device = torch.device("cpu")
        self.screener = FakeScreener()
        self.model_family = self.screener.model_family


def test_optimize_crystallization_returns_ranked_solutions() -> None:
    optimizer = FakeProcessOptimizer()
    rows = optimizer.optimize_crystallization(
        "CC(=O)Nc1ccc(O)cc1",
        target_yield=0.5,
        T_range=(278.0, 340.0),
        constraints={"min_green_score": 5},
    )
    assert rows
    assert rows[0]["T_hot"] > rows[0]["T_cold"]
    assert "temperature_scan" in rows[0]


def test_optimize_extraction_ranks_by_partition_and_miscibility() -> None:
    optimizer = FakeProcessOptimizer()
    df = optimizer.optimize_extraction(
        "CC(=O)Nc1ccc(O)cc1",
        "O",
        T=298.15,
        constraints={"min_partition_coefficient": 2.0},
    )
    assert not df.empty
    assert "partition_coefficient" in df.columns
    assert df.iloc[0]["rank"] == 1


def test_optimize_reaction_medium_reports_species_columns() -> None:
    optimizer = FakeProcessOptimizer()
    df = optimizer.optimize_reaction_medium(
        ["CCO", "CCN"],
        "CC(=O)O",
        T_reaction=298.15,
        constraints={"min_reactant_solubility_mg_mL": 0.1},
    )
    assert not df.empty
    assert "reactant_1_solubility_mg_mL" in df.columns
    assert "product_solubility_mg_mL" in df.columns
    assert "reactant_product_selectivity" in df.columns


def test_design_solvent_system_returns_binary_candidates() -> None:
    optimizer = FakeProcessOptimizer()
    df = optimizer.design_solvent_system(
        "CC(=O)Nc1ccc(O)cc1",
        (1.0, 30.0),
        T=298.15,
    )
    assert not df.empty
    assert {"solvent_a", "solvent_b", "phi_a", "estimated_solubility_mg_mL"} <= set(df.columns)
