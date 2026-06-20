import math
import sys

import pandas as pd

sys.path.insert(0, "src")

from tgnn_solv.data.thermoml_targeted import (
    aggregate_targeted_measurements,
    classify_property_family,
    extract_targeted_measurement_rows,
    extract_targeted_pair_rows,
)


def _binary_record() -> dict:
    return {
        "Citation": {
            "sDOI": "10.0000/targeted-example",
            "sTitle": "Example targeted coverage record",
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
        "PureOrMixtureData": [
            {
                "nPureOrMixtureDataNumber": 7,
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
                    },
                    {
                        "nPropNumber": 2,
                        "PropPhaseID": {"ePropPhase": "Liquid"},
                        "Property-MethodID": {
                            "PropertyGroup": {
                                "ExcessPartialApparentEnergyProp": {
                                    "ePropName": "Excess molar enthalpy (molar enthalpy of mixing), kJ/mol",
                                    "eMethodName": "Calorimetry",
                                }
                            }
                        },
                    },
                ],
                "NumValues": [
                    {
                        "VariableValue": [
                            {"nVarNumber": 1, "nVarValue": 298.15},
                            {"nVarNumber": 2, "nVarValue": 0.2},
                        ],
                        "PropertyValue": [
                            {"nPropNumber": 1, "nPropValue": 1.5},
                            {"nPropNumber": 2, "nPropValue": -1.2},
                        ],
                    }
                ],
            }
        ],
    }


def test_classify_property_family_maps_target_labels() -> None:
    assert classify_property_family("Activity coefficient") == "direct_activity"
    assert (
        classify_property_family("Excess molar enthalpy (molar enthalpy of mixing), kJ/mol")
        == "excess_thermo"
    )
    assert classify_property_family("Vapor or sublimation pressure, kPa") == "vle_like"
    assert classify_property_family("Molar enthalpy of solution, kJ/mol") == "solution_thermo"
    assert classify_property_family("Binary diffusion coefficient, m2/s") == "other"


def test_extract_targeted_pair_rows_keeps_exact_binary_pair_matches() -> None:
    rows = extract_targeted_pair_rows(
        _binary_record(),
        source_label="memory",
        target_pairs={"CCO>>O"},
    )

    assert len(rows) == 2
    families = {row["property_label"]: row["property_family"] for row in rows}
    assert families["Activity coefficient"] == "direct_activity"
    assert (
        families["Excess molar enthalpy (molar enthalpy of mixing), kJ/mol"]
        == "excess_thermo"
    )
    for row in rows:
        assert row["pair_key_sorted"] == "CCO>>O"
        assert row["dataset_has_temperature"] is True
        assert row["dataset_has_pressure"] is True
        assert row["dataset_has_composition"] is True


def test_extract_targeted_pair_rows_respects_target_pair_filter() -> None:
    rows = extract_targeted_pair_rows(
        _binary_record(),
        source_label="memory",
        target_pairs={"CCN>>O"},
    )

    assert rows == []


def test_extract_targeted_measurement_rows_keeps_exact_binary_values() -> None:
    rows = extract_targeted_measurement_rows(
        _binary_record(),
        source_label="memory",
        target_pairs={"CCO>>O"},
    )

    assert len(rows) == 2
    by_label = {row["property_label"]: row for row in rows}
    activity = by_label["Activity coefficient"]
    assert activity["property_family"] == "direct_activity"
    assert activity["property_target_smiles"] == "CCO"
    assert activity["targeted_pair_key"] == "CCO>>O"
    assert activity["composition_basis"] == "mole_fraction"
    assert math.isclose(activity["composition_value"], 0.2)
    assert math.isclose(activity["temperature"], 298.15)
    assert math.isclose(activity["pressure_kpa"], 101.325)
    assert math.isclose(activity["value"], 1.5)
    assert math.isclose(activity["ln_value"], math.log(1.5))

    excess = by_label["Excess molar enthalpy (molar enthalpy of mixing), kJ/mol"]
    assert excess["property_family"] == "excess_thermo"
    assert excess["canonical_unit"] == "J/mol"
    assert math.isclose(excess["value"], -1200.0)


def test_aggregate_targeted_measurements_merges_duplicate_exact_states() -> None:
    frame = pd.DataFrame(
        [
            {
                "doi": "10.0000/a",
                "property_label": "Activity coefficient",
                "property_key": "activity_coefficient",
                "property_family": "direct_activity",
                "pair_component_smiles_a": "CCO",
                "pair_component_smiles_b": "O",
                "pair_component_name_a": "ethanol",
                "pair_component_name_b": "water",
                "pair_key_sorted": "CCO>>O",
                "property_target_smiles": "CCO",
                "property_target_name": "ethanol",
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
                "property_phase": "Liquid",
                "property_standard_state": "Pure compound",
                "reported_unit": "dimensionless",
                "canonical_unit": "gamma",
                "property_method": "Static equilibrium",
                "value": 1.5,
                "ln_value": math.log(1.5),
                "uncertainty": 0.1,
                "is_candidate_activity_signal": True,
                "is_idac_like": False,
            },
            {
                "doi": "10.0000/b",
                "property_label": "Activity coefficient",
                "property_key": "activity_coefficient",
                "property_family": "direct_activity",
                "pair_component_smiles_a": "CCO",
                "pair_component_smiles_b": "O",
                "pair_component_name_a": "ethanol",
                "pair_component_name_b": "water",
                "pair_key_sorted": "CCO>>O",
                "property_target_smiles": "CCO",
                "property_target_name": "ethanol",
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
                "property_phase": "Liquid",
                "property_standard_state": "Pure compound",
                "reported_unit": "dimensionless",
                "canonical_unit": "gamma",
                "property_method": "Static equilibrium",
                "value": 1.7,
                "ln_value": math.log(1.7),
                "uncertainty": 0.2,
                "is_candidate_activity_signal": True,
                "is_idac_like": False,
            },
        ]
    )

    aggregated = aggregate_targeted_measurements(frame)

    assert len(aggregated) == 1
    row = aggregated.iloc[0]
    assert row["n_measurements"] == 2
    assert row["n_dois"] == 2
    assert math.isclose(row["value"], 1.6)
    assert math.isclose(row["value_min"], 1.5)
    assert math.isclose(row["value_max"], 1.7)
