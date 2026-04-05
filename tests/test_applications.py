from tgnn_solv.applications import (
    aqueous_max_supported_dose_mg,
    dose_margin,
    mole_fraction_to_molarity_in_water,
    pharma_capability_matrix,
    solvent_swap_metrics,
    synthesis_window_metrics,
)


def test_aqueous_proxy_monotonicity() -> None:
    low = mole_fraction_to_molarity_in_water(1e-4)
    high = mole_fraction_to_molarity_in_water(1e-2)
    assert high > low > 0


def test_aqueous_dose_margin() -> None:
    max_dose = aqueous_max_supported_dose_mg(1e-3, 180.0)
    assert max_dose is not None
    margin = dose_margin(max_dose, 50.0)
    assert margin is not None
    assert margin > 0


def test_synthesis_window_prefers_hot_to_cold_drop() -> None:
    strong = synthesis_window_metrics(-1.5, -5.0)
    weak = synthesis_window_metrics(-4.5, -5.0)
    assert strong["route_score"] > weak["route_score"]
    assert strong["swing_ratio"] > weak["swing_ratio"]


def test_solvent_swap_prefers_poorer_target_medium() -> None:
    strong = solvent_swap_metrics(-1.0, -5.0)
    weak = solvent_swap_metrics(-1.0, -1.5)
    assert strong["transfer_score"] > weak["transfer_score"]
    assert strong["crash_ratio"] > weak["crash_ratio"]


def test_pharma_capability_matrix_marks_pd_as_unsupported() -> None:
    rows = pharma_capability_matrix(
        water_margin=0.4,
        has_water_prediction=True,
        best_cosolvent_uplift=12.0,
    )
    stage_map = {row["stage"]: row["support"] for row in rows}
    assert stage_map["Solvent ranking / crystallization"] == "strong"
    assert stage_map["PD / efficacy"] == "not supported"
