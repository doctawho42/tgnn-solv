import math

import pandas as pd

import sys
sys.path.insert(0, "src")

from tgnn_solv.data.thermoml_crystal import (
    aggregate_crystal_measurements,
    extract_crystal_measurements,
)


def _sample_record() -> dict:
    return {
        "Citation": {
            "sDOI": "10.0000/crystal-example",
            "sTitle": "Example crystal record",
            "sPubName": "J. Example Thermodynamics",
            "yrPubYr": "2024",
        },
        "Compound": [
            {
                "RegNum": {"nOrgNum": 1},
                "sCommonName": ["naphthalene"],
                "sStandardInChI": "InChI=1S/C10H8/c1-2-6-10-8-4-3-7-9(10)5-1/h1-8H",
            }
        ],
        "PureOrMixtureData": [
            {
                "nPureOrMixtureDataNumber": 7,
                "Component": [{"RegNum": {"nOrgNum": 1}}],
                "Property": [
                    {
                        "nPropNumber": 1,
                        "PropPhaseID": {"ePropPhase": "Crystal"},
                        "Property-MethodID": {
                            "PropertyGroup": {
                                "ePropName": "Normal melting temperature, K",
                                "eMethodName": "DSC",
                            }
                        },
                    },
                    {
                        "nPropNumber": 2,
                        "PropPhaseID": {"ePropPhase": "Crystal"},
                        "Property-MethodID": {
                            "PropertyGroup": {
                                "ePropName": (
                                    "Molar enthalpy of transition or fusion, kJ/mol"
                                ),
                                "eMethodName": "DSC",
                            }
                        },
                    },
                ],
                "NumValues": [
                    {
                        "PropertyValue": [
                            {"nPropNumber": 1, "nPropValue": 353.4},
                            {"nPropNumber": 2, "nPropValue": 19.06},
                        ]
                    }
                ],
            }
        ],
    }


def test_extract_crystal_measurements_builds_tm_and_dh_rows() -> None:
    rows = extract_crystal_measurements(_sample_record(), source_label="memory")

    assert len(rows) == 2
    tm_row = next(row for row in rows if row["property_key"] == "T_m")
    dh_row = next(row for row in rows if row["property_key"] == "dH_fus")

    assert tm_row["solute_smiles"] == "c1ccc2ccccc2c1"
    assert tm_row["property_name"] == "Normal melting temperature, K"
    assert tm_row["canonical_unit"] == "K"
    assert math.isclose(tm_row["T_m"], 353.4)
    assert tm_row["dH_fus"] is None

    assert dh_row["canonical_unit"] == "J/mol"
    assert dh_row["phase"] == "Crystal"
    assert math.isclose(dh_row["dH_fus"], 19060.0)
    assert dh_row["T_m"] is None


def test_aggregate_crystal_measurements_keeps_dh_only_from_tm_paired_dois() -> None:
    frame = pd.DataFrame(
        [
            {
                "source_label": "memory",
                "doi": "10.0000/paired",
                "solute_smiles": "CCO",
                "solute_name": "ethanol",
                "formula": "C2H6O",
                "property_key": "T_m",
                "T_m": 159.0,
                "dH_fus": None,
            },
            {
                "source_label": "memory",
                "doi": "10.0000/paired",
                "solute_smiles": "CCO",
                "solute_name": "ethanol",
                "formula": "C2H6O",
                "property_key": "dH_fus",
                "T_m": None,
                "dH_fus": 5000.0,
            },
            {
                "source_label": "memory",
                "doi": "10.0000/unpaired-dh",
                "solute_smiles": "CCO",
                "solute_name": "ethanol",
                "formula": "C2H6O",
                "property_key": "dH_fus",
                "T_m": None,
                "dH_fus": 25000.0,
            },
            {
                "source_label": "memory",
                "doi": "10.0000/extra-tm",
                "solute_smiles": "CCO",
                "solute_name": "ethanol",
                "formula": "C2H6O",
                "property_key": "T_m",
                "T_m": 161.0,
                "dH_fus": None,
            },
        ]
    )

    aggregated = aggregate_crystal_measurements(frame)

    assert len(aggregated) == 1
    row = aggregated.iloc[0]
    assert row["solute_smiles"] == "CCO"
    assert math.isclose(row["T_m"], 160.0)
    assert math.isclose(row["dH_fus"], 5000.0)
    assert row["T_m_n_measurements"] == 2
    assert row["dH_fus_n_measurements"] == 1
    assert row["thermoml_pair_doi_count"] == 1
