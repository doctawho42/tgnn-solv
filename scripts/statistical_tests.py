#!/usr/bin/env python3
"""Run statistical tests for multi-seed model comparison results."""

from __future__ import annotations

import argparse
import json
import math
from itertools import combinations
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401
import numpy as np
from tgnn_solv.data.split_registry import build_split_metadata

try:
    from scipy.stats import t as student_t
    from scipy.stats import ttest_ind, ttest_rel, wilcoxon
except Exception:  # pragma: no cover - optional dependency
    student_t = None
    ttest_ind = None
    ttest_rel = None
    wilcoxon = None


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run statistical tests on multi-seed experiment results.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--results",
        type=str,
        nargs="+",
        required=True,
        help="Paths to JSON files produced by scripts/run_seeds.py.",
    )
    parser.add_argument(
        "--labels",
        type=str,
        nargs="+",
        default=None,
        help="Optional model labels in the same order as --results.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/significance.json",
        help="Path to save the significance analysis JSON.",
    )
    parser.add_argument(
        "--allow-mixed-splits",
        action="store_true",
        help="Allow significance comparisons across different split modes.",
    )
    return parser.parse_args()


def to_float(value: object) -> float | None:
    """Convert a value to a finite float if possible."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def infer_labels(paths: list[Path]) -> list[str]:
    """Infer model labels from result filenames."""
    return [path.stem for path in paths]


def load_json(path: Path) -> dict[str, Any]:
    """Load one result JSON file."""
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def extract_split_metadata(payload: dict[str, Any]) -> dict[str, str | None]:
    """Extract split metadata from a result payload."""
    split = payload.get("split")
    if isinstance(split, dict):
        mode = split.get("mode")
        if isinstance(mode, str) and mode:
            return {
                "mode": mode,
                "display_name": split.get("display_name"),
                "train_data": split.get("train_data"),
                "val_data": split.get("val_data"),
                "test_data": split.get("test_data"),
            }

    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        metadata_split = metadata.get("split")
        if isinstance(metadata_split, dict):
            mode = metadata_split.get("mode")
            if isinstance(mode, str) and mode:
                return {
                    "mode": mode,
                    "display_name": metadata_split.get("display_name"),
                    "train_data": metadata_split.get("train_data"),
                    "val_data": metadata_split.get("val_data"),
                    "test_data": metadata_split.get("test_data"),
                }

    return build_split_metadata(
        split_mode=payload.get("split_mode"),
        train_data=payload.get("train_data"),
        val_data=payload.get("val_data"),
        test_data=payload.get("test_data"),
    )


def extract_mae_by_seed(payload: dict[str, Any]) -> dict[int, float]:
    """Extract MAE values keyed by seed from a run_seeds-style payload."""
    seed_to_mae: dict[int, float] = {}

    per_seed = payload.get("per_seed")
    if isinstance(per_seed, list):
        for idx, record in enumerate(per_seed):
            if not isinstance(record, dict):
                continue
            mae = to_float(record.get("mae"))
            if mae is None:
                continue
            raw_seed = record.get("seed", idx)
            try:
                seed = int(raw_seed)
            except (TypeError, ValueError):
                seed = idx
            seed_to_mae[seed] = mae
        if seed_to_mae:
            return seed_to_mae

    aggregated = payload.get("aggregated", {})
    if isinstance(aggregated, dict):
        mae_info = aggregated.get("mae", {})
        if isinstance(mae_info, dict):
            values = mae_info.get("values", [])
            seeds = payload.get("seeds", [])
            if isinstance(values, list):
                for idx, value in enumerate(values):
                    mae = to_float(value)
                    if mae is None:
                        continue
                    seed = idx
                    if isinstance(seeds, list) and idx < len(seeds):
                        try:
                            seed = int(seeds[idx])
                        except (TypeError, ValueError):
                            seed = idx
                    seed_to_mae[seed] = mae

    return seed_to_mae


def sample_std(values: np.ndarray) -> float:
    """Compute sample standard deviation with ddof=1."""
    if values.size < 2:
        return 0.0
    return float(values.std(ddof=1))


def cohens_d(values_a: np.ndarray, values_b: np.ndarray) -> float | None:
    """Compute Cohen's d using pooled sample standard deviation."""
    n_a = values_a.size
    n_b = values_b.size
    if n_a == 0 or n_b == 0:
        return None

    mean_diff = float(values_a.mean() - values_b.mean())
    if n_a + n_b < 3:
        return 0.0 if mean_diff == 0.0 else None

    std_a = sample_std(values_a)
    std_b = sample_std(values_b)
    denom = n_a + n_b - 2
    if denom <= 0:
        return 0.0 if mean_diff == 0.0 else None

    pooled_var = ((n_a - 1) * (std_a ** 2) + (n_b - 1) * (std_b ** 2)) / denom
    pooled_std = math.sqrt(max(pooled_var, 0.0))
    if pooled_std == 0.0:
        return 0.0 if mean_diff == 0.0 else None
    return mean_diff / pooled_std


def compute_ci_of_difference(
    values_a: np.ndarray,
    values_b: np.ndarray,
    paired: bool,
) -> tuple[float | None, float | None]:
    """Compute a 95% confidence interval for the mean difference."""
    if values_a.size == 0 or values_b.size == 0:
        return None, None

    if paired:
        diffs = values_a - values_b
        mean_diff = float(diffs.mean())
        if diffs.size < 2:
            return mean_diff, mean_diff
        std_diff = sample_std(diffs)
        sem = std_diff / math.sqrt(diffs.size)
        if sem == 0.0:
            return mean_diff, mean_diff
        if student_t is not None:
            critical = float(student_t.ppf(0.975, df=diffs.size - 1))
        else:
            critical = 1.96
        margin = critical * sem
        return mean_diff - margin, mean_diff + margin

    mean_diff = float(values_a.mean() - values_b.mean())
    std_a = sample_std(values_a)
    std_b = sample_std(values_b)
    sem = math.sqrt((std_a ** 2) / max(values_a.size, 1) + (std_b ** 2) / max(values_b.size, 1))
    if sem == 0.0:
        return mean_diff, mean_diff

    if student_t is not None:
        var_a = (std_a ** 2) / max(values_a.size, 1)
        var_b = (std_b ** 2) / max(values_b.size, 1)
        numerator = (var_a + var_b) ** 2
        denominator = 0.0
        if values_a.size > 1:
            denominator += (var_a ** 2) / (values_a.size - 1)
        if values_b.size > 1:
            denominator += (var_b ** 2) / (values_b.size - 1)
        df = (numerator / denominator) if denominator > 0 else max(values_a.size + values_b.size - 2, 1)
        critical = float(student_t.ppf(0.975, df=df))
    else:
        critical = 1.96

    margin = critical * sem
    return mean_diff - margin, mean_diff + margin


def paired_wilcoxon_p(values_a: np.ndarray, values_b: np.ndarray) -> float | None:
    """Compute a paired Wilcoxon p-value when possible."""
    if wilcoxon is None or values_a.size != values_b.size or values_a.size < 2:
        return None

    diffs = values_a - values_b
    if np.allclose(diffs, 0.0):
        return 1.0

    try:
        return float(wilcoxon(values_a, values_b).pvalue)
    except Exception:
        return None


def significance_marker(p_value: float | None) -> str:
    """Format significance markers from a p-value."""
    if p_value is None:
        return "n/a"
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return "ns"


def format_float(value: float | None, precision: int = 3) -> str:
    """Format a float for console output."""
    if value is None:
        return "n/a"
    return f"{value:.{precision}f}"


def compare_models(
    label_a: str,
    mae_by_seed_a: dict[int, float],
    label_b: str,
    mae_by_seed_b: dict[int, float],
    scipy_available: bool,
) -> dict[str, Any]:
    """Compare two models statistically on MAE."""
    seeds_a = sorted(mae_by_seed_a)
    seeds_b = sorted(mae_by_seed_b)
    paired = seeds_a == seeds_b and len(seeds_a) > 0

    if paired:
        ordered_seeds = seeds_a
        values_a = np.asarray([mae_by_seed_a[seed] for seed in ordered_seeds], dtype=float)
        values_b = np.asarray([mae_by_seed_b[seed] for seed in ordered_seeds], dtype=float)
    else:
        ordered_seeds = []
        values_a = np.asarray([mae_by_seed_a[seed] for seed in seeds_a], dtype=float)
        values_b = np.asarray([mae_by_seed_b[seed] for seed in seeds_b], dtype=float)

    mean_a = float(values_a.mean()) if values_a.size else None
    mean_b = float(values_b.mean()) if values_b.size else None
    difference = (mean_a - mean_b) if mean_a is not None and mean_b is not None else None
    ci_low, ci_high = compute_ci_of_difference(values_a, values_b, paired=paired)

    ttest_p = None
    wilcoxon_p = None
    if scipy_available:
        try:
            if paired and ttest_rel is not None and values_a.size >= 2:
                ttest_p = float(ttest_rel(values_a, values_b).pvalue)
            elif not paired and ttest_ind is not None and values_a.size >= 2 and values_b.size >= 2:
                ttest_p = float(ttest_ind(values_a, values_b, equal_var=False).pvalue)
        except Exception:
            ttest_p = None
        wilcoxon_p = paired_wilcoxon_p(values_a, values_b) if paired else None

    return {
        "model_a": label_a,
        "model_b": label_b,
        "metric": "mae",
        "mean_a": mean_a,
        "mean_b": mean_b,
        "difference": difference,
        "ci_95": [ci_low, ci_high],
        "ttest_p": ttest_p,
        "wilcoxon_p": wilcoxon_p,
        "cohens_d": cohens_d(values_a, values_b),
        "paired": paired,
        "paired_seeds": ordered_seeds,
        "n_a": int(values_a.size),
        "n_b": int(values_b.size),
    }


def build_summary_table(
    comparisons: list[dict[str, Any]],
    use_bonferroni: bool,
) -> str:
    """Build a formatted summary table string."""
    lines = [
        (
            f"{'Comparison':<28} | {'ΔMAE':>8} | {'95% CI':>20} | "
            f"{'p (t-test)':>10} | {'p (Wilcoxon)':>12} | {'Cohens d':>9} | {'Sig?':>4}"
        ),
        "-" * 109,
    ]

    for item in comparisons:
        ci_low, ci_high = item["ci_95"]
        ci_text = (
            f"[{format_float(ci_low, 3)}, {format_float(ci_high, 3)}]"
            if ci_low is not None and ci_high is not None
            else "n/a"
        )
        comparison_p = item.get("bonferroni_p") if use_bonferroni else item.get("ttest_p")
        if comparison_p is None:
            comparison_p = item.get("wilcoxon_p")
        sig_text = significance_marker(comparison_p)
        comparison_label = f"{item['model_a']} vs {item['model_b']}"
        lines.append(
            f"{comparison_label:<28} | "
            f"{format_float(item['difference'], 3):>8} | "
            f"{ci_text:>20} | "
            f"{format_float(item['ttest_p'], 3):>10} | "
            f"{format_float(item['wilcoxon_p'], 3):>12} | "
            f"{format_float(item['cohens_d'], 3):>9} | "
            f"{sig_text:>4}"
        )

    lines.append("")
    lines.append("Significance: *** p<0.001, ** p<0.01, * p<0.05, ns p>=0.05")
    if use_bonferroni:
        lines.append("Significance markers use Bonferroni-corrected t-test p-values.")
    return "\n".join(lines)


def main() -> int:
    """Run model comparison statistics and save the report."""
    args = parse_args()

    result_paths = [_bootstrap.resolve_path(path_str) for path_str in args.results]
    if len(result_paths) < 2:
        raise ValueError("At least two result files are required for statistical comparison.")
    output_path = _bootstrap.resolve_path(args.output)

    labels = args.labels
    if labels is None:
        labels = infer_labels(result_paths)
    elif len(labels) != len(result_paths):
        raise ValueError("--labels must match the number of --results files.")

    scipy_available = all(obj is not None for obj in (ttest_ind, ttest_rel))
    if not scipy_available:
        print("WARNING: SciPy is not available; p-values will be omitted.")

    model_results: list[dict[str, Any]] = []
    for label, path in zip(labels, result_paths):
        payload = load_json(path)
        mae_by_seed = extract_mae_by_seed(payload)
        if not mae_by_seed:
            raise ValueError(f"No valid per-seed MAE values found in {path}")
        split = extract_split_metadata(payload)
        model_results.append(
            {
                "label": label,
                "path": str(path),
                "mae_by_seed": mae_by_seed,
                "split": split,
            }
        )

    split_modes = {
        str(model_result["split"].get("mode", "unknown"))
        for model_result in model_results
    }
    if len(split_modes) > 1 and not args.allow_mixed_splits:
        split_summary = ", ".join(
            f"{result['label']}={result['split'].get('mode', 'unknown')}"
            for result in model_results
        )
        raise ValueError(
            "Mixed split modes detected in --results. "
            "Use --allow-mixed-splits only if this is intentional. "
            f"Received: {split_summary}"
        )

    comparisons: list[dict[str, Any]] = []
    for model_a, model_b in combinations(model_results, 2):
        comparison = compare_models(
            label_a=model_a["label"],
            mae_by_seed_a=model_a["mae_by_seed"],
            label_b=model_b["label"],
            mae_by_seed_b=model_b["mae_by_seed"],
            scipy_available=scipy_available,
        )
        comparison["split_a"] = model_a["split"]
        comparison["split_b"] = model_b["split"]
        comparisons.append(comparison)

    use_bonferroni = len(model_results) > 2
    n_comparisons = len(comparisons)
    for item in comparisons:
        if item["ttest_p"] is None:
            item["bonferroni_p"] = None
        elif use_bonferroni:
            item["bonferroni_p"] = min(float(item["ttest_p"]) * n_comparisons, 1.0)
        else:
            item["bonferroni_p"] = float(item["ttest_p"])

        significance_p = item["bonferroni_p"] if use_bonferroni else item["ttest_p"]
        if significance_p is None:
            significance_p = item["wilcoxon_p"]
        item["significant_at_005"] = bool(significance_p is not None and significance_p < 0.05)

    summary_table = build_summary_table(comparisons, use_bonferroni=use_bonferroni)
    print(summary_table)

    payload = {
        "split": (
            model_results[0]["split"]
            if len(split_modes) == 1 and model_results
            else {
                "mode": "mixed",
                "members": [
                    {
                        "label": result["label"],
                        "mode": result["split"].get("mode"),
                        "display_name": result["split"].get("display_name"),
                    }
                    for result in model_results
                ],
            }
        ),
        "comparisons": comparisons,
        "summary_table": summary_table,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print()
    print(f"Saved significance results to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
