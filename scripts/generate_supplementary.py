#!/usr/bin/env python3
"""Generate LaTeX and CSV supplementary tables from experiment results."""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Callable

import _bootstrap  # noqa: F401
import pandas as pd

from tgnn_solv.reporting import normalize_report_payload


MODEL_LABELS = {
    "tgnn_solv": "TGNN-Solv",
    "direct_gnn": "DirectGNN",
    "rf_baseline": "RF Baseline",
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate supplementary LaTeX tables from results/ outputs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default="results/",
        help="Directory containing experiment result JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="tables/",
        help="Directory where .tex and .csv tables will be written.",
    )
    return parser.parse_args()


def warn(message: str) -> None:
    """Print a warning message."""
    print(f"WARNING: {message}")


def load_json(path: Path, warn_missing: bool = True) -> dict[str, object] | None:
    """Load a JSON file if it exists, otherwise return None."""
    if not path.is_file():
        if warn_missing:
            warn(f"Missing source file: {path}")
        return None
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        warn(f"Expected a JSON object in {path}")
        return None
    return payload


def fmt_mean_std(mean: object, std: object) -> str:
    """Format a mean ± std cell."""
    if mean is None or std is None:
        return "n/a"
    return f"{float(mean):.3f} ± {float(std):.3f}"


def fmt_float(value: object, digits: int = 3) -> str:
    """Format a float-like value or return n/a."""
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


def fmt_pct(value: object, digits: int = 1) -> str:
    """Format a ratio as a percent string."""
    if value is None:
        return "n/a"
    try:
        return f"{100.0 * float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "n/a"


def first_non_none(*values: object) -> object | None:
    """Return the first value that is not None."""
    for value in values:
        if value is not None:
            return value
    return None


def save_table(
    df: pd.DataFrame,
    output_dir: Path,
    stem: str,
    caption: str,
) -> tuple[Path, Path]:
    """Save a table as both LaTeX and CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    tex_path = output_dir / f"{stem}.tex"
    csv_path = output_dir / f"{stem}.csv"

    column_format = "l" + "c" * max(len(df.columns) - 1, 0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        tabular = df.to_latex(
            index=False,
            escape=False,
            float_format=lambda x: f"{x:.3f}",
            column_format=column_format,
        )
    latex = "\n".join(
        [
            r"\begin{table}",
            rf"\caption{{{caption}}}",
            r"\centering",
            tabular.strip(),
            r"\end{table}",
            "",
        ]
    )

    tex_path.write_text(latex, encoding="utf-8")
    df.to_csv(csv_path, index=False)
    return tex_path, csv_path


def build_table_s1(results_dir: Path) -> pd.DataFrame | None:
    """Build Table S1 from multi_seed_results.json."""
    payload = load_json(results_dir / "multi_seed_results.json")
    if payload is None:
        return None

    rows: list[dict[str, object]] = []
    for record in payload.get("per_seed", []):
        if not isinstance(record, dict):
            continue
        rows.append(
            {
                "Seed": record.get("seed"),
                "MAE": record.get("mae"),
                "RMSE": record.get("rmse"),
                "R²": record.get("r2"),
                "Pearson": record.get("pearson_r"),
            }
        )

    aggregated = payload.get("aggregated", {})
    if isinstance(aggregated, dict):
        rows.append(
            {
                "Seed": "Mean ± Std",
                "MAE": fmt_mean_std(aggregated.get("mae", {}).get("mean"), aggregated.get("mae", {}).get("std")),
                "RMSE": fmt_mean_std(aggregated.get("rmse", {}).get("mean"), aggregated.get("rmse", {}).get("std")),
                "R²": fmt_mean_std(aggregated.get("r2", {}).get("mean"), aggregated.get("r2", {}).get("std")),
                "Pearson": fmt_mean_std(
                    aggregated.get("pearson_r", {}).get("mean"),
                    aggregated.get("pearson_r", {}).get("std"),
                ),
            }
        )

    return pd.DataFrame(rows, columns=["Seed", "MAE", "RMSE", "R²", "Pearson"])


def build_table_s2(results_dir: Path) -> pd.DataFrame | None:
    """Build Table S2 from ablation.json."""
    payload = load_json(results_dir / "ablation.json")
    if payload is None:
        return None

    variants = payload.get("variants", {})
    order = payload.get("variant_order", list(variants.keys()))
    delta_vs_full = payload.get("delta_vs_full", {})
    if not isinstance(variants, dict) or not variants:
        warn("Ablation payload does not contain any variants.")
        return None

    rows: list[dict[str, object]] = []
    for name in order:
        data = variants.get(name)
        if not isinstance(data, dict):
            continue
        delta = delta_vs_full.get(name, {}) if isinstance(delta_vs_full, dict) else {}
        rows.append(
            {
                "Variant": data.get("display_name", name),
                "MAE (mean±std)": fmt_mean_std(data.get("mae_mean"), data.get("mae_std")),
                "ΔMAE": "—" if name == "full" else fmt_float(delta.get("delta_mae")),
                "R²": fmt_mean_std(data.get("r2_mean"), data.get("r2_std")),
                "p-value": "—" if name == "full" else fmt_float(delta.get("significance_p")),
            }
        )

    return pd.DataFrame(rows, columns=["Variant", "MAE (mean±std)", "ΔMAE", "R²", "p-value"])


def build_table_s3(results_dir: Path) -> pd.DataFrame | None:
    """Build Table S3 from solvent-type metrics or error analysis."""
    full_eval = load_json(results_dir / "full_evaluation.json", warn_missing=False)
    if full_eval is not None:
        full_eval = normalize_report_payload(full_eval)
        by_solvent_type = full_eval.get("by_solvent_type")
        if isinstance(by_solvent_type, dict) and by_solvent_type:
            rows = []
            for label, metrics in by_solvent_type.items():
                if not isinstance(metrics, dict):
                    continue
                rows.append(
                    {
                        "Solvent Type": label,
                        "N samples": metrics.get("n_samples"),
                        "MAE": metrics.get("mae"),
                        "RMSE": metrics.get("rmse"),
                        "R²": metrics.get("r2"),
                        "Pearson": metrics.get("pearson_r"),
                    }
                )
            if rows:
                return pd.DataFrame(rows)

        by_solvent = full_eval.get("by_solvent")
        if isinstance(by_solvent, dict) and by_solvent:
            rows = []
            for label, metrics in by_solvent.items():
                if not isinstance(metrics, dict):
                    continue
                rows.append(
                    {
                        "Solvent Group": label,
                        "N samples": metrics.get("n_samples", metrics.get("n")),
                        "MAE": metrics.get("mae"),
                        "RMSE": metrics.get("rmse"),
                        "R²": metrics.get("r2"),
                        "Pearson": metrics.get("pearson", metrics.get("pearson_r")),
                    }
                )
            if rows:
                return pd.DataFrame(rows)

    error_analysis = load_json(results_dir / "error_analysis.json")
    if error_analysis is None:
        return None

    solvent_rows = error_analysis.get("solvent_analysis", [])
    if not isinstance(solvent_rows, list) or not solvent_rows:
        warn("error_analysis.json does not contain solvent_analysis rows.")
        return None

    rows = []
    for row in solvent_rows:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "Solvent": row.get("solvent_label", row.get("solvent_smiles")),
                "SMILES": row.get("solvent_smiles"),
                "N samples": row.get("n_samples"),
                "MAE": row.get("mae"),
                "Mean signed error": row.get("mean_signed_error"),
            }
        )
    return pd.DataFrame(rows)


def build_table_s4(results_dir: Path) -> pd.DataFrame | None:
    """Build Table S4 from temperature-stratified evaluation results."""
    payload = load_json(results_dir / "full_evaluation.json")
    if payload is None:
        return None
    payload = normalize_report_payload(payload)

    by_temperature = payload.get("by_temperature")
    if not isinstance(by_temperature, dict) or not by_temperature:
        warn("full_evaluation.json does not contain by_temperature.")
        return None

    rows = []
    for label, metrics in by_temperature.items():
        if not isinstance(metrics, dict):
            continue
        rows.append(
            {
                "Temperature bin": label,
                "N samples": metrics.get("n_samples"),
                "MAE": metrics.get("mae"),
                "RMSE": metrics.get("rmse"),
                "R²": metrics.get("r2"),
                "Pearson": metrics.get("pearson_r"),
            }
        )
    return pd.DataFrame(rows)


def build_table_s5(results_dir: Path) -> pd.DataFrame | None:
    """Build Table S5 from physics_validation.json."""
    payload = load_json(results_dir / "physics_validation.json")
    if payload is None:
        return None

    properties = payload.get("property_validation")
    if not isinstance(properties, dict) or not properties:
        warn("physics_validation.json does not contain property_validation.")
        return None

    rows = []
    for name, metrics in properties.items():
        if not isinstance(metrics, dict):
            continue
        rows.append(
            {
                "Property": name,
                "MAE": metrics.get("mae"),
                "R²": metrics.get("r2"),
                "Pearson": metrics.get("pearson"),
                "N samples": metrics.get("n_samples"),
                "% in physical range": fmt_pct(metrics.get("frac_in_range")) if metrics.get("frac_in_range") is not None else "n/a",
            }
        )
    return pd.DataFrame(rows, columns=["Property", "MAE", "R²", "Pearson", "N samples", "% in physical range"])


def build_table_s6(results_dir: Path) -> pd.DataFrame | None:
    """Build Table S6 from learning_curves.json."""
    payload = load_json(results_dir / "learning_curves.json")
    if payload is None:
        return None

    results = payload.get("results")
    if not isinstance(results, dict) or not results:
        warn("learning_curves.json does not contain results.")
        return None

    models = payload.get("models", [])
    if not isinstance(models, list):
        models = []

    rows = []
    for fraction_label, entry in results.items():
        if not isinstance(entry, dict):
            continue
        row: dict[str, object] = {
            "Fraction": fraction_label,
            "N_train": entry.get("n_samples"),
        }
        effective_models = models or [key for key in entry.keys() if key in MODEL_LABELS]
        for model_name in effective_models:
            model_data = entry.get(model_name)
            if not isinstance(model_data, dict):
                continue
            label = MODEL_LABELS.get(model_name, model_name)
            row[f"{label} MAE"] = fmt_mean_std(model_data.get("mae_mean"), model_data.get("mae_std"))
            row[f"{label} R²"] = fmt_mean_std(model_data.get("r2_mean"), model_data.get("r2_std"))
        rows.append(row)

    return pd.DataFrame(rows)


def build_table_s7(results_dir: Path) -> pd.DataFrame | None:
    """Build Table S7 from temperature_extrapolation.json."""
    payload = load_json(results_dir / "temperature_extrapolation.json")
    if payload is None:
        return None

    t_cuts = payload.get("t_cuts")
    if not isinstance(t_cuts, dict) or not t_cuts:
        warn("temperature_extrapolation.json does not contain t_cuts.")
        return None

    rows = []
    for label, entry in t_cuts.items():
        if not isinstance(entry, dict):
            continue
        rows.append(
            {
                "T_cut (K)": label,
                "N_train": entry.get("n_train"),
                "N_test": entry.get("n_test"),
                "N_pairs": entry.get("n_pairs"),
                "Test T range": (
                    f"[{entry['test_T_range'][0]:.2f}, {entry['test_T_range'][1]:.2f}]"
                    if isinstance(entry.get("test_T_range"), list) and len(entry["test_T_range"]) == 2
                    else "n/a"
                ),
                "TGNN-Solv MAE": fmt_mean_std(
                    entry.get("tgnn_solv", {}).get("mae_mean"),
                    entry.get("tgnn_solv", {}).get("mae_std"),
                ),
                "DirectGNN MAE": fmt_mean_std(
                    entry.get("direct_gnn", {}).get("mae_mean"),
                    entry.get("direct_gnn", {}).get("mae_std"),
                ),
                "Improvement (%)": fmt_float(entry.get("improvement_pct"), digits=1),
            }
        )
    return pd.DataFrame(rows)


def build_table_s8(results_dir: Path) -> pd.DataFrame | None:
    """Build Table S8 from shared-vs-split-late backbone comparison results."""
    shared_payload = load_json(results_dir / "multi_seed_results.json", warn_missing=False)
    split_payload = load_json(results_dir / "split_late_multi_seed_results.json", warn_missing=False)
    if shared_payload is None or split_payload is None:
        warn("Backbone comparison requires both multi_seed_results.json and split_late_multi_seed_results.json.")
        return None

    significance_payload = load_json(results_dir / "significance.json", warn_missing=False)
    significance_lookup: dict[tuple[str, str], dict[str, object]] = {}
    if isinstance(significance_payload, dict):
        comparisons = significance_payload.get("comparisons", [])
        if isinstance(comparisons, list):
            for comparison in comparisons:
                if not isinstance(comparison, dict):
                    continue
                model_a = comparison.get("model_a")
                model_b = comparison.get("model_b")
                if isinstance(model_a, str) and isinstance(model_b, str):
                    significance_lookup[(model_a, model_b)] = comparison

    rows: list[dict[str, object]] = []
    payload_specs = [
        ("TGNN-Solv", "shared_residual", shared_payload),
        ("TGNN-Solv", "split_late", split_payload),
    ]
    for model_name, encoder_mode, payload in payload_specs:
        aggregated = payload.get("aggregated", {}) if isinstance(payload, dict) else {}
        if not isinstance(aggregated, dict):
            continue
        rows.append(
            {
                "Model": model_name,
                "Encoder": encoder_mode,
                "MAE (mean±std)": fmt_mean_std(
                    aggregated.get("mae", {}).get("mean"),
                    aggregated.get("mae", {}).get("std"),
                ),
                "RMSE (mean±std)": fmt_mean_std(
                    aggregated.get("rmse", {}).get("mean"),
                    aggregated.get("rmse", {}).get("std"),
                ),
                "R² (mean±std)": fmt_mean_std(
                    aggregated.get("r2", {}).get("mean"),
                    aggregated.get("r2", {}).get("std"),
                ),
                "Pearson (mean±std)": fmt_mean_std(
                    aggregated.get("pearson_r", {}).get("mean"),
                    aggregated.get("pearson_r", {}).get("std"),
                ),
            }
        )

    if not rows:
        return None

    for row in rows:
        row["Shared vs SplitLate p-value"] = "—"

    significance = significance_lookup.get(("TGNN-Solv", "SplitLate")) or significance_lookup.get(
        ("SplitLate", "TGNN-Solv")
    )
    if significance is not None and len(rows) >= 2:
        rows[1]["Shared vs SplitLate p-value"] = fmt_float(
            first_non_none(significance.get("bonferroni_p"), significance.get("ttest_p"))
        )
    elif len(rows) >= 2:
        rows[1]["Shared vs SplitLate p-value"] = "n/a"

    return pd.DataFrame(rows)


def build_table_s9(results_dir: Path) -> pd.DataFrame | None:
    """Build Table S9 from split_comparisons.json."""
    payload = load_json(results_dir / "split_comparisons.json")
    if payload is None:
        return None

    split_order = payload.get("split_order")
    splits = payload.get("splits")
    model_order = payload.get("model_order")
    if not isinstance(split_order, list) or not isinstance(splits, dict):
        warn("split_comparisons.json does not contain split_order/splits.")
        return None
    if not isinstance(model_order, list):
        model_order = []

    rows: list[dict[str, object]] = []
    for split_mode in split_order:
        split_payload = splits.get(split_mode)
        if not isinstance(split_payload, dict):
            continue

        split_meta = split_payload.get("split", {})
        models = split_payload.get("models", {})
        if not isinstance(split_meta, dict) or not isinstance(models, dict):
            continue

        row: dict[str, object] = {
            "Split": split_meta.get("display_name", split_mode),
            "Mode": split_meta.get("mode", split_mode),
        }

        best_model = None
        best_mae = None
        for model_name in model_order:
            model_payload = models.get(model_name)
            if not isinstance(model_payload, dict):
                continue
            aggregated = model_payload.get("aggregated", {})
            if not isinstance(aggregated, dict):
                continue
            mae_stats = aggregated.get("mae", {})
            r2_stats = aggregated.get("r2", {})
            if isinstance(mae_stats, dict):
                row[f"{MODEL_LABELS.get(model_name, model_name)} MAE"] = fmt_mean_std(
                    mae_stats.get("mean"),
                    mae_stats.get("std"),
                )
                mae_mean = mae_stats.get("mean")
                if mae_mean is not None:
                    mae_value = float(mae_mean)
                    if best_mae is None or mae_value < best_mae:
                        best_mae = mae_value
                        best_model = MODEL_LABELS.get(model_name, model_name)
            if isinstance(r2_stats, dict):
                row[f"{MODEL_LABELS.get(model_name, model_name)} R²"] = fmt_mean_std(
                    r2_stats.get("mean"),
                    r2_stats.get("std"),
                )

        significance = split_payload.get("significance", {})
        if isinstance(significance, dict):
            comparisons = significance.get("comparisons", [])
            if isinstance(comparisons, list):
                for comparison in comparisons:
                    if not isinstance(comparison, dict):
                        continue
                    model_a = comparison.get("model_a")
                    model_b = comparison.get("model_b")
                    if not isinstance(model_a, str) or not isinstance(model_b, str):
                        continue
                    key = f"{model_a} vs {model_b} p-value"
                    row[key] = fmt_float(
                        first_non_none(comparison.get("bonferroni_p"), comparison.get("ttest_p"))
                    )

        row["Best model"] = best_model or "n/a"
        rows.append(row)

    return pd.DataFrame(rows)


def main() -> int:
    """Generate all available supplementary tables."""
    args = parse_args()

    results_dir = _bootstrap.resolve_path(args.results_dir)
    output_dir = _bootstrap.resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    table_builders: list[tuple[str, str, Callable[[Path], pd.DataFrame | None], str]] = [
        ("table_s1_multi_seed", "Full multi-seed evaluation results", build_table_s1, "Table S1"),
        ("table_s2_ablation", "Ablation study results", build_table_s2, "Table S2"),
        ("table_s3_solvent_metrics", "Per-solvent or solvent-type metrics", build_table_s3, "Table S3"),
        ("table_s4_temperature_stratified", "Temperature-stratified evaluation results", build_table_s4, "Table S4"),
        ("table_s5_physics_validation", "Physical parameter validation", build_table_s5, "Table S5"),
        ("table_s6_learning_curves", "Learning-curve results", build_table_s6, "Table S6"),
        ("table_s7_temperature_extrapolation", "Temperature extrapolation results", build_table_s7, "Table S7"),
        ("table_s8_backbone_comparison", "Shared-versus-split-late backbone comparison", build_table_s8, "Table S8"),
        ("table_s9_split_protocols", "Model performance across split protocols", build_table_s9, "Table S9"),
    ]

    generated: list[Path] = []
    for stem, caption, builder, table_name in table_builders:
        df = builder(results_dir)
        if df is None or df.empty:
            warn(f"{table_name} was skipped because no usable data was found.")
            continue
        tex_path, csv_path = save_table(df, output_dir=output_dir, stem=stem, caption=caption)
        generated.append(tex_path)
        print(f"Generated {table_name}: {tex_path.name} and {csv_path.name}")

    print()
    print(f"Generated {len(generated)} tables in {output_dir}:")
    for path in generated:
        print(f"  {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
