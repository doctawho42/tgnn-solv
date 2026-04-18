#!/usr/bin/env python3
"""Summarize CPU-side readiness for improving TGNN physics supervision."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


def _load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(numeric):
        return "n/a"
    return f"{numeric:.{digits}f}"


def _write_markdown(summary: dict[str, Any], path: Path) -> None:
    idac = summary.get("idac_expansion", {})
    train_aux = summary.get("train_aux_attachment", {}).get("solute_scaffold", {})
    naive = summary.get("naive_expanded_prepare_data", {})
    errors = summary.get("prediction_error_slices", [])
    direct_gap = summary.get("directgnn_generalization_gap", {})
    dcp = summary.get("dcp_correction", {})
    conversion = summary.get("unit_conversion", {})
    thermoml = summary.get("thermoml_inventory", {})

    lines = [
        "# Physics Supervision Readiness Audit",
        "",
        "## Main Conclusions",
        "",
        "- Expanded ThermoML IDAC is usable as auxiliary `gamma_inf` supervision, not as direct SLE-pair coverage.",
        "- Do not use `notebooks/data/processed_idac_expanded` for benchmark comparisons: adding aux-only rows before scaffold splitting changes the supervised validation/test protocol.",
        "- Use `notebooks/data/processed_idac_expanded_train_aux` for fair short ablations: canonical supervised splits are preserved and new IDAC rows are attached to train only.",
        "- Current Joback/GC `dCp_fus_gc` is too uncalibrated for direct use as a free SLE correction; it needs clipping/calibration before training.",
        "- Existing error slices show TGNN's physics tax is concentrated, not universal: TGNN beats DirectGNN on a large minority of rows but loses on mean MAE.",
        "",
        "## IDAC Expansion",
        "",
        f"- Raw exact-deduplicated rows: `{idac.get('raw_rows', 'n/a')}`",
        f"- Aggregated train-safe rows: `{idac.get('training_rows', 'n/a')}`",
        f"- Unique IDAC pairs: `{idac.get('training_pairs', 'n/a')}`",
        f"- Unique DOI count: `{idac.get('raw_dois', 'n/a')}`",
        f"- Conflicting pair-temperature groups: `{idac.get('n_conflicting_groups', 'n/a')}`",
        f"- Exact SLE pair overlap fraction: `{_fmt(idac.get('sle_pair_overlap_fraction'))}`",
        "",
        "## Fixed-Split Train-Aux Bundle",
        "",
        f"- Output: `{summary.get('train_aux_attachment', {}).get('output_dir', 'n/a')}`",
        f"- New IDAC aux rows added to scaffold train: `{train_aux.get('n_new_idac_aux_rows_added_to_train', 'n/a')}`",
        f"- Existing starter gamma rows skipped: `{train_aux.get('n_idac_rows_skipped_as_existing_gamma', 'n/a')}`",
        f"- Scaffold train supervised rows preserved: `{train_aux.get('input_train_supervised', 'n/a')} -> {train_aux.get('output_train_supervised', 'n/a')}`",
        f"- Scaffold val/test supervised rows preserved: `{train_aux.get('input_val_supervised', 'n/a')}/{train_aux.get('input_test_supervised', 'n/a')} -> {train_aux.get('output_val_supervised', 'n/a')}/{train_aux.get('output_test_supervised', 'n/a')}`",
        "",
        "## Naive Expanded Prepare-Data Bundle",
        "",
        f"- Output: `{naive.get('output_dir', 'n/a')}`",
        f"- Supervised scaffold train/val/test became: `{naive.get('train_supervised', 'n/a')}` / `{naive.get('val_supervised', 'n/a')}` / `{naive.get('test_supervised', 'n/a')}`",
        "- Interpretation: this is a protocol-shift diagnostic artifact, not a fair benchmark input.",
        "",
        "## Existing Error Structure",
        "",
        "| Model | MAE | R2 | Median pair MAE | P90 pair MAE | Pair MAE > 3 | Worst class |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in errors:
        lines.append(
            "| {label} | {mae} | {r2} | {pair_med} | {pair_p90} | {pair_gt3} | {worst} |".format(
                label=row.get("label", "n/a"),
                mae=_fmt(row.get("mae")),
                r2=_fmt(row.get("r2")),
                pair_med=_fmt(row.get("median_pair_mae")),
                pair_p90=_fmt(row.get("p90_pair_mae")),
                pair_gt3=_fmt(row.get("fraction_pair_mae_gt_3")),
                worst=row.get("worst_coarse_class", "n/a"),
            )
        )
    lines.extend(
        [
            "",
            "## Train-Test Gap",
            "",
            f"- DirectGNN train MAE: `{_fmt(direct_gap.get('train_mae'))}`",
            f"- DirectGNN test MAE: `{_fmt(direct_gap.get('test_mae'))}`",
            f"- Test minus train MAE: `{_fmt(direct_gap.get('test_minus_train_mae'))}`",
            f"- DirectGNN train R2: `{_fmt(direct_gap.get('train_r2'))}`",
            f"- DirectGNN test R2: `{_fmt(direct_gap.get('test_r2'))}`",
            "",
            "## dCp Correction Audit",
            "",
            f"- Overall median |dCp correction|: `{_fmt(dcp.get('overall_median_abs'))}` ln units",
            f"- Plausible single-component, within 250 K below Tm median |correction|: `{_fmt(dcp.get('plausible_close_median_abs'))}` ln units",
            f"- Plausible close subset fraction |correction| > 0.8: `{_fmt(dcp.get('plausible_close_frac_abs_gt_0_8'))}`",
            "- Interpretation: current GC dCp prior has signal but is not safe without clipping/calibration.",
            "",
            "## Unit Conversion",
            "",
            f"- Raw BigSolDB mean abs ln_x2 reconstruction delta: `{_fmt(conversion.get('raw_mean_abs_ln_x2_delta'), 4)}`",
            f"- Raw BigSolDB p95 abs ln_x2 reconstruction delta: `{_fmt(conversion.get('raw_p95_abs_ln_x2_delta'), 4)}`",
            "- Interpretation: unit conversion remains too small to explain MAE ~1.6.",
            "",
            "## ThermoML Multi-Task Inventory",
            "",
            f"- Cached JSON files scanned: `{thermoml.get('n_json_files', 'n/a')}`",
            f"- GE-like properties: `{thermoml.get('ge_like_properties', {})}`",
            f"- VLE-like properties: `{thermoml.get('vle_like_properties', {})}`",
            f"- Crystal-like properties: `{thermoml.get('crystal_like_properties', {})}`",
            "- Interpretation: there is enough ThermoML signal to prototype GE/excess-enthalpy and VLE auxiliary extractors after IDAC ablation.",
            "",
            "## Optional Dependencies",
            "",
            f"- `thermo`: `{summary.get('optional_dependencies', {}).get('thermo')}`",
            f"- `chemicals`: `{summary.get('optional_dependencies', {}).get('chemicals')}`",
            "- UNIFAC pseudo-IDAC should stay optional until these are explicitly added to the environment.",
            "",
            "## Next Short Run",
            "",
            "Use the fixed train-aux bundle for a controlled IDAC ablation:",
            "",
            "```bash",
            "python scripts/training/train.py \\",
            "  --config configs/paper_config_tuned_interaction_rescue.yaml \\",
            "  --train-data notebooks/data/processed_idac_expanded_train_aux/train.csv \\",
            "  --val-data notebooks/data/processed_idac_expanded_train_aux/val.csv \\",
            "  --test-data notebooks/data/processed_idac_expanded_train_aux/test.csv \\",
            "  --checkpoint checkpoints/idac_expanded_train_aux_tgnn.pt \\",
            "  --device cuda",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    out_dir = Path("results/physics_supervision_audit")
    out_dir.mkdir(parents=True, exist_ok=True)

    idac = _load_json("results/idac_expansion_audit/summary.json")
    train_aux = _load_json(
        "notebooks/data/processed_idac_expanded_train_aux/idac_aux_attachment_summary.json"
    )
    pred = _load_json("results/prediction_error_slices_latest/summary.json")
    direct_gap = _load_json("results/directgnn_error_structure/train_val_test_metrics.json")
    dcp = _load_json("results/dcp_correction_audit/summary.json")
    unit = _load_json("results/unit_conversion_audit/summary.json")
    thermoml_inventory = _load_json("results/thermoml_property_inventory/summary.json")

    scaffold_aux = train_aux.get("split_results", {}).get("solute_scaffold", {})
    scaffold_in = scaffold_aux.get("input", {})
    scaffold_out = scaffold_aux.get("output", {})
    dcp_close = (
        dcp.get("subsets", {})
        .get("plausible_single_component_gc_within_250K_below_Tm", {})
    )
    unit_raw = unit.get("raw_bigsoldb", {}).get("ln_x2_vs_logS", {})

    summary = {
        "idac_expansion": {
            "raw_rows": idac.get("raw_exact_deduplicated_stats", {}).get("n_rows"),
            "raw_dois": idac.get("raw_exact_deduplicated_stats", {}).get("n_dois"),
            "training_rows": idac.get("training_aggregated_stats", {}).get("n_rows"),
            "training_pairs": idac.get("training_aggregated_stats", {}).get("n_pairs"),
            "n_conflicting_groups": idac.get("aggregation", {}).get("n_conflicting_groups"),
            "sle_pair_overlap_fraction": (
                idac.get("coverage", {})
                .get("overall", {})
                .get("idac_pair_overlap_fraction")
            ),
        },
        "train_aux_attachment": {
            "output_dir": train_aux.get("output_dir"),
            "solute_scaffold": {
                "n_new_idac_aux_rows_added_to_train": scaffold_aux.get(
                    "n_new_idac_aux_rows_added_to_train"
                ),
                "n_idac_rows_skipped_as_existing_gamma": scaffold_aux.get(
                    "n_idac_rows_skipped_as_existing_gamma"
                ),
                "input_train_supervised": scaffold_in.get("train", {}).get("n_supervised_rows"),
                "output_train_supervised": scaffold_out.get("train", {}).get("n_supervised_rows"),
                "input_val_supervised": scaffold_in.get("val", {}).get("n_supervised_rows"),
                "output_val_supervised": scaffold_out.get("val", {}).get("n_supervised_rows"),
                "input_test_supervised": scaffold_in.get("test", {}).get("n_supervised_rows"),
                "output_test_supervised": scaffold_out.get("test", {}).get("n_supervised_rows"),
            },
        },
        "naive_expanded_prepare_data": {
            "output_dir": "notebooks/data/processed_idac_expanded",
            "train_supervised": 100432,
            "val_supervised": 3933,
            "test_supervised": 3922,
        },
        "prediction_error_slices": pred.get("comparison_summary", []),
        "directgnn_generalization_gap": {
            "train_mae": direct_gap.get("train", {}).get("mae"),
            "test_mae": direct_gap.get("test", {}).get("mae"),
            "test_minus_train_mae": direct_gap.get("gaps", {}).get("test_minus_train_mae"),
            "train_r2": direct_gap.get("train", {}).get("r2"),
            "test_r2": direct_gap.get("test", {}).get("r2"),
        },
        "dcp_correction": {
            "overall_median_abs": dcp.get("overall", {}).get("median_abs"),
            "overall_p95_abs": dcp.get("overall", {}).get("p95_abs"),
            "plausible_close_median_abs": dcp_close.get("median_abs"),
            "plausible_close_p95_abs": dcp_close.get("p95_abs"),
            "plausible_close_frac_abs_gt_0_8": dcp_close.get("frac_abs_gt_0_8"),
        },
        "unit_conversion": {
            "raw_mean_abs_ln_x2_delta": unit_raw.get("mean_abs_error"),
            "raw_p95_abs_ln_x2_delta": unit_raw.get("p95_abs_error"),
        },
        "thermoml_inventory": {
            "n_json_files": thermoml_inventory.get("n_json_files"),
            "ge_like_properties": thermoml_inventory.get("ge_like_properties", {}),
            "vle_like_properties": thermoml_inventory.get("vle_like_properties", {}),
            "crystal_like_properties": thermoml_inventory.get("crystal_like_properties", {}),
        },
        "optional_dependencies": {
            "thermo": _has_module("thermo"),
            "chemicals": _has_module("chemicals"),
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    _write_markdown(summary, out_dir / "summary.md")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
