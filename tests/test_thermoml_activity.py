import math

import pandas as pd

import sys
sys.path.insert(0, "src")

from scripts.data.extract_activity_from_thermoml import _property_overlap_summary
from tgnn_solv.data.thermoml_activity import (
    aggregate_activity_measurements,
    extract_activity_measurements,
)


def _base_record() -> dict:
    return {
        "Citation": {
            "sDOI": "10.0000/activity-example",
            "sTitle": "Example activity record",
            "sPubName": "J. Example Thermodynamics",
            "yrPubYr": "2024",
        },
        "Compound": [
            {
                "RegNum": {"nOrgNum": 1},
                "sCommonName": ["ethanol"],
                "sStandardInChI": "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
            },
            {
                "RegNum": {"nOrgNum": 2},
                "sCommonName": ["water"],
                "sStandardInChI": "InChI=1S/H2O/h1H2",
            },
        ],
    }


def _finite_activity_record() -> dict:
    record = _base_record()
    record["PureOrMixtureData"] = [
        {
            "nPureOrMixtureDataNumber": 1,
            "Component": [
                {"RegNum": {"nOrgNum": 1}},
                {"RegNum": {"nOrgNum": 2}},
            ],
            "Variable": [
                {
                    "nVarNumber": 1,
                    "VariableID": {"VariableType": {"eTemperature": "Temperature, K"}},
                },
                {
                    "nVarNumber": 2,
                    "VariableID": {
                        "RegNum": {"nOrgNum": 1},
                        "VariableType": {"eComponentComposition": "Mole fraction"},
                    },
                },
            ],
            "Constraint": [
                {
                    "ConstraintID": {"ConstraintType": {"ePressure": "Pressure, kPa"}},
                    "nConstraintValue": 101.325,
                }
            ],
            "Property": [
                {
                    "nPropNumber": 1,
                    "eStandardState": "Pure compound",
                    "PropPhaseID": {"ePropPhase": "Liquid"},
                    "Property-MethodID": {
                        "RegNum": {"nOrgNum": 1},
                        "PropertyGroup": {
                            "ActivityFugacityOsmoticProp": {
                                "ePropName": "Activity coefficient",
                                "eMethodName": "Static equilibrium",
                            }
                        },
                    },
                }
            ],
            "NumValues": [
                {
                    "VariableValue": [
                        {"nVarNumber": 1, "nVarValue": 298.15},
                        {"nVarNumber": 2, "nVarValue": 0.2},
                    ],
                    "PropertyValue": [
                        {"nPropNumber": 1, "nPropValue": 1.5},
                    ],
                }
            ],
        }
    ]
    return record


def _idac_like_record() -> dict:
    record = _base_record()
    record["PureOrMixtureData"] = [
        {
            "nPureOrMixtureDataNumber": 1,
            "Component": [
                {"RegNum": {"nOrgNum": 1}},
                {"RegNum": {"nOrgNum": 2}},
            ],
            "Variable": [
                {
                    "nVarNumber": 1,
                    "VariableID": {"VariableType": {"eTemperature": "Temperature, K"}},
                },
                {
                    "nVarNumber": 2,
                    "VariableID": {
                        "RegNum": {"nOrgNum": 1},
                        "VariableType": {"eComponentComposition": "Mole fraction"},
                    },
                },
            ],
            "Property": [
                {
                    "nPropNumber": 1,
                    "eStandardState": "Infinite dilution solute",
                    "PropPhaseID": {"ePropPhase": "Liquid"},
                    "Property-MethodID": {
                        "RegNum": {"nOrgNum": 1},
                        "PropertyGroup": {
                            "ActivityFugacityOsmoticProp": {
                                "ePropName": "Activity coefficient",
                                "eMethodName": "Chromatography",
                            }
                        },
                    },
                }
            ],
            "NumValues": [
                {
                    "VariableValue": [
                        {"nVarNumber": 1, "nVarValue": 298.15},
                        {"nVarNumber": 2, "nVarValue": 0.0},
                    ],
                    "PropertyValue": [
                        {"nPropNumber": 1, "nPropValue": 15.0},
                    ],
                }
            ],
        }
    ]
    return record


def _excess_enthalpy_record() -> dict:
    record = _base_record()
    record["PureOrMixtureData"] = [
        {
            "nPureOrMixtureDataNumber": 4,
            "Component": [
                {"RegNum": {"nOrgNum": 1}},
                {"RegNum": {"nOrgNum": 2}},
            ],
            "Variable": [
                {
                    "nVarNumber": 1,
                    "VariableID": {
                        "RegNum": {"nOrgNum": 1},
                        "VariableType": {"eComponentComposition": "Mole fraction"},
                    },
                }
            ],
            "Constraint": [
                {
                    "ConstraintID": {"ConstraintType": {"eTemperature": "Temperature, K"}},
                    "nConstraintValue": 298.15,
                }
            ],
            "Property": [
                {
                    "nPropNumber": 7,
                    "PropPhaseID": {"ePropPhase": "Liquid"},
                    "Property-MethodID": {
                        "PropertyGroup": {
                            "ExcessPartialApparentEnergyProp": {
                                "ePropName": "Excess molar enthalpy (molar enthalpy of mixing), kJ/mol",
                                "eMethodName": "Calorimetry",
                            }
                        }
                    },
                }
            ],
            "NumValues": [
                {
                    "VariableValue": [
                        {"nVarNumber": 1, "nVarValue": 0.3},
                    ],
                    "PropertyValue": [
                        {"nPropNumber": 7, "nPropValue": -1.2},
                    ],
                }
            ],
        }
    ]
    return record


def test_extract_activity_measurements_keeps_finite_activity_rows() -> None:
    rows = extract_activity_measurements(_finite_activity_record(), source_label="memory")

    assert len(rows) == 1
    row = rows[0]
    assert row["property_key"] == "activity_coefficient"
    assert row["measurement_kind"] == "direct_activity"
    assert row["target_smiles"] == "CCO"
    assert row["other_smiles"] == "O"
    assert row["targeted_pair_key"] == "CCO>>O"
    assert row["composition_basis"] == "mole_fraction"
    assert math.isclose(row["composition_value"], 0.2)
    assert math.isclose(row["temperature"], 298.15)
    assert math.isclose(row["pressure_kpa"], 101.325)
    assert math.isclose(row["value"], 1.5)
    assert math.isclose(row["ln_value"], math.log(1.5))


def test_extract_activity_measurements_excludes_idac_like_rows() -> None:
    rows = extract_activity_measurements(_idac_like_record(), source_label="memory")

    assert rows == []


def test_extract_activity_measurements_converts_excess_enthalpy_units() -> None:
    rows = extract_activity_measurements(_excess_enthalpy_record(), source_label="memory")

    assert len(rows) == 1
    row = rows[0]
    assert row["property_key"] == "excess_molar_enthalpy"
    assert row["measurement_kind"] == "excess_thermo"
    assert row["canonical_unit"] == "J/mol"
    assert math.isclose(row["value"], -1200.0)
    assert pd.isna(row["ln_value"])


def test_aggregate_activity_measurements_merges_duplicate_exact_states() -> None:
    frame = pd.DataFrame(
        [
            {
                "property_key": "activity_coefficient",
                "measurement_kind": "direct_activity",
                "pair_component_smiles_a": "CCO",
                "pair_component_smiles_b": "O",
                "pair_key_sorted": "CCO>>O",
                "target_smiles": "CCO",
                "target_name": "ethanol",
                "other_smiles": "O",
                "other_name": "water",
                "targeted_pair_key": "CCO>>O",
                "reverse_targeted_pair_key": "O>>CCO",
                "composition_basis": "mole_fraction",
                "composition_label": "Mole fraction",
                "composition_source": "variable",
                "composition_value": 0.2,
                "composition_smiles": "CCO",
                "composition_name": "ethanol",
                "temperature": 298.15,
                "pressure_kpa": 101.325,
                "phase": "Liquid",
                "standard_state": "Pure compound",
                "canonical_unit": "gamma",
                "method": "Static equilibrium",
                "value": 1.4,
                "ln_value": math.log(1.4),
                "uncertainty": 0.1,
                "doi": "10.0000/a",
                "is_direct_activity": True,
                "is_idac_like": False,
            },
            {
                "property_key": "activity_coefficient",
                "measurement_kind": "direct_activity",
                "pair_component_smiles_a": "CCO",
                "pair_component_smiles_b": "O",
                "pair_key_sorted": "CCO>>O",
                "target_smiles": "CCO",
                "target_name": "ethanol",
                "other_smiles": "O",
                "other_name": "water",
                "targeted_pair_key": "CCO>>O",
                "reverse_targeted_pair_key": "O>>CCO",
                "composition_basis": "mole_fraction",
                "composition_label": "Mole fraction",
                "composition_source": "variable",
                "composition_value": 0.2,
                "composition_smiles": "CCO",
                "composition_name": "ethanol",
                "temperature": 298.1500001,
                "pressure_kpa": 101.3250001,
                "phase": "Liquid",
                "standard_state": "Pure compound",
                "canonical_unit": "gamma",
                "method": "Static equilibrium",
                "value": 1.6,
                "ln_value": math.log(1.6),
                "uncertainty": 0.2,
                "doi": "10.0000/b",
                "is_direct_activity": True,
                "is_idac_like": False,
            },
        ]
    )

    aggregated = aggregate_activity_measurements(frame)

    assert len(aggregated) == 1
    row = aggregated.iloc[0]
    assert row["pair_key_sorted"] == "CCO>>O"
    assert math.isclose(row["composition_value"], 0.2)
    assert math.isclose(row["temperature"], 298.15)
    assert math.isclose(row["value"], 1.5)
    assert math.isclose(row["value_min"], 1.4)
    assert math.isclose(row["value_max"], 1.6)
    assert row["n_measurements"] == 2
    assert row["n_dois"] == 2


def test_property_overlap_summary_splits_overlap_by_property() -> None:
    aggregated = pd.DataFrame(
        [
            {
                "property_key": "relative_activity",
                "pair_key_sorted": "CCO>>O",
                "targeted_pair_key": "CCO>>O",
                "reverse_targeted_pair_key": "O>>CCO",
                "is_direct_activity": True,
            },
            {
                "property_key": "excess_molar_enthalpy",
                "pair_key_sorted": "CCN>>O",
                "targeted_pair_key": "CCN>>O",
                "reverse_targeted_pair_key": "O>>CCN",
                "is_direct_activity": False,
            },
        ]
    )
    processed = pd.DataFrame(
        [
            {
                "split": "train",
                "pair_key_sorted": "CCO>>O",
                "pair_key_directed": "CCO>>O",
                "solute_smiles": "CCO",
                "solvent_smiles": "O",
            },
            {
                "split": "val",
                "pair_key_sorted": "CCCl>>O",
                "pair_key_directed": "CCCl>>O",
                "solute_smiles": "CCCl",
                "solvent_smiles": "O",
            },
        ]
    )

    summary = _property_overlap_summary(aggregated, processed)
    by_key = {(row["property_key"], row["split"]): row for row in summary}

    rel_train = by_key[("relative_activity", "train")]
    assert rel_train["unordered_pair_overlap_pairs"] == 1
    assert rel_train["unordered_pair_overlap_rows"] == 1
    assert rel_train["direct_target_as_solute_pairs"] == 1
    assert rel_train["direct_target_as_solvent_pairs"] == 0

    excess_train = by_key[("excess_molar_enthalpy", "train")]
    assert excess_train["unordered_pair_overlap_pairs"] == 0
    assert excess_train["unordered_pair_overlap_rows"] == 0
    assert excess_train["direct_target_as_solute_pairs"] == 0
    assert excess_train["direct_target_as_solvent_pairs"] == 0
