import math

import sys
sys.path.insert(0, "src")

from tgnn_solv.data.thermoml_idac import extract_idac_rows


def _sample_record(constraint_value: float = 0.0) -> dict:
    return {
        "Citation": {
            "sDOI": "10.0000/example",
            "sTitle": "Example IDAC record",
            "sPubName": "J. Example Data",
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
        "PureOrMixtureData": [
            {
                "nPureOrMixtureDataNumber": 1,
                "Component": [
                    {"RegNum": {"nOrgNum": 1}},
                    {"RegNum": {"nOrgNum": 2}},
                ],
                "Constraint": [
                    {
                        "ConstraintID": {
                            "ConstraintType": {"eComponentComposition": "Mole fraction"},
                            "RegNum": {"nOrgNum": 1},
                        },
                        "nConstraintValue": constraint_value,
                    }
                ],
                "Variable": [
                    {
                        "nVarNumber": 1,
                        "VariableID": {
                            "VariableType": {"eTemperature": "Temperature, K"},
                        },
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
                        ],
                        "PropertyValue": [
                            {"nPropNumber": 1, "nPropValue": 1.5},
                        ],
                    }
                ],
            }
        ],
    }


def _sample_variable_record(mole_fraction: float = 0.0) -> dict:
    return {
        "Citation": {
            "sDOI": "10.0000/example-variable",
            "sTitle": "Example Variable IDAC record",
            "sPubName": "J. Example Data",
            "yrPubYr": "2024",
        },
        "Compound": [
            {
                "RegNum": {"nOrgNum": 1},
                "sCommonName": ["naphthalene"],
                "sStandardInChI": "InChI=1S/C10H8/c1-2-6-10-8-4-3-7-9(10)5-1/h1-8H",
            },
            {
                "RegNum": {"nOrgNum": 2},
                "sCommonName": ["formamide"],
                "sStandardInChI": "InChI=1S/CH3NO/c2-1-3/h1H,(H2,2,3)",
            },
        ],
        "PureOrMixtureData": [
            {
                "nPureOrMixtureDataNumber": 5,
                "Component": [
                    {"RegNum": {"nOrgNum": 1}},
                    {"RegNum": {"nOrgNum": 2}},
                ],
                "Variable": [
                    {
                        "nVarNumber": 1,
                        "VariableID": {
                            "VariableType": {"eTemperature": "Temperature, K"},
                        },
                    },
                    {
                        "nVarNumber": 3,
                        "VariableID": {
                            "RegNum": {"nOrgNum": 1},
                            "VariableType": {"eComponentComposition": "Mole fraction"},
                        },
                    },
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
                                    "eMethodName": "Chromatography",
                                }
                            },
                        },
                    }
                ],
                "NumValues": [
                    {
                        "VariableValue": [
                            {"nVarNumber": 1, "nVarValue": 298.0},
                            {"nVarNumber": 3, "nVarValue": mole_fraction},
                        ],
                        "PropertyValue": [
                            {"nPropNumber": "1", "nPropValue": 53.0},
                        ],
                    }
                ],
            }
        ],
    }


def test_extract_idac_rows_builds_binary_row() -> None:
    rows = extract_idac_rows(_sample_record(), source_label="memory")

    assert len(rows) == 1
    row = rows[0]
    assert row["solute_smiles"] == "CCO"
    assert row["solvent_smiles"] == "O"
    assert row["solute_name"] == "ethanol"
    assert row["solvent_name"] == "water"
    assert row["temperature"] == 298.15
    assert row["gamma_inf"] == 1.5
    assert math.isclose(row["ln_gamma_inf"], math.log(1.5))


def test_extract_idac_rows_requires_zero_mole_fraction_constraint() -> None:
    rows = extract_idac_rows(_sample_record(constraint_value=0.2), source_label="memory")

    assert rows == []


def test_extract_idac_rows_supports_variable_based_zero_mole_fraction() -> None:
    rows = extract_idac_rows(_sample_variable_record(), source_label="memory")

    assert len(rows) == 1
    row = rows[0]
    assert row["solute_name"] == "naphthalene"
    assert row["solvent_name"] == "formamide"
    assert row["temperature"] == 298.0
    assert row["gamma_inf"] == 53.0


def test_extract_idac_rows_rejects_nonzero_variable_mole_fraction() -> None:
    rows = extract_idac_rows(
        _sample_variable_record(mole_fraction=0.05),
        source_label="memory",
    )

    assert rows == []
