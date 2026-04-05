# TGNN-Solv Benchmarking Guide

## Overview

There are now four maintained benchmark layers in the repo:

- `scripts/evaluation/evaluate_complete.py`
  - quickest checkpoint report with plot-ready arrays
- `scripts/evaluation/benchmark_tgnn_solv.py`
  - richer `Evaluator`-backed benchmark JSON
- `scripts/experiments/run_full_budget_experiment.py`
  - full-budget TGNN-vs-DirectGNN diagnostic study
- `scripts/experiments/run_medium_budget_comparison.py`
  - full-scaffold medium-budget architecture comparison
- `scripts/evaluation/benchmark_adapter_model.py`
  - formal adapter API for arbitrary custom Python models

All maintained benchmark bundles now emit the same sidecars in addition to the
core `summary.csv / report.json / predictions.csv` contract:

- `run_manifest.json`
- `benchmark_card.json`

Those sidecars make the bundle machine-readable for:

- `Results & Plots -> Benchmark Studio`
- artifact lineage / diff views in the lab
- frozen benchmark release manifests
- downstream paper-table generation

These grouped paths are the preferred human-facing CLI layout. The old
top-level script paths remain available as compatibility wrappers.

Use the lightest tool that answers the question you actually have.

## Canonical Benchmark Bundle

A first-class comparable benchmark bundle now means:

- `summary.csv`
- `report.json`
- `predictions.csv`
- `run_manifest.json`
- `benchmark_card.json`

If one of those sidecars is missing, the output may still be useful, but it is
not as provenance-rich as the maintained bundle contract.

## Quick Checkpoint Benchmark

For the default quick report:

```bash
python scripts/evaluation/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output results/full_evaluation.json \
    --verbose
```

This gives you:

- overall MAE, RMSE, and `R²`
- stratified metrics by temperature, solubility range, solvent type, and data
  availability
- `true_ln_x2` / `pred_ln_x2` arrays for plotting

## Richer Benchmark JSON

If you want the `Evaluator`-backed path:

```bash
python scripts/evaluation/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/results.json
```

This is useful when you want a benchmark artifact that can be compared or
post-processed later.

## Physical Diagnostics

If top-line solubility metrics are not enough, inspect the TGNN intermediates:

```bash
python scripts/evaluation/validate_physics.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output results/physics_validation.json \
    --device cuda
```

Use this when you need:

- `T_m` / `dH_fus` parity
- NRTL parameter sanity checks
- Walden consistency diagnostics
- GC-prior crystal inspection

## Full-Budget Diagnostic Study

For the most detailed TGNN-vs-DirectGNN comparison:

```bash
python scripts/experiments/run_full_budget_experiment.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --seeds 42 \
    --output-dir results/full_budget_experiment \
    --device cuda
```

This study exports:

- TGNN metrics
- DirectGNN metrics
- oracle-evaluated TGNN metrics
- TGNN intermediate CSVs
- diagnostic JSON summaries

It also reuses resumable per-seed checkpoints.

## Medium-Budget Architecture Study

For the full-scaffold medium-budget comparison:

```bash
python scripts/experiments/run_medium_budget_comparison.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/medium_budget \
    --device cuda
```

This writes:

- `results/medium_budget/summary.json`
- `results/medium_budget/comparison_table.md`
- `results/medium_budget/per_model/<model>/...`

Use it when you need a single report covering tuned TGNN, GC-prior variants,
DirectGNN baselines, and RF on the same full scaffold split.

## Comparing Multiple Models

For lightweight checkpoint-to-checkpoint comparison, benchmark each model
separately and diff the resulting JSON:

```bash
python scripts/evaluation/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/model_a.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/model_a.json

python scripts/evaluation/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/model_b.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/model_b.json
```

## Benchmarking a Custom Python Model

For a repo-native adapter instead of a raw predictions CSV:

```bash
python scripts/evaluation/benchmark_adapter_model.py \
    --adapter your_package.your_adapter:YourAdapter \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --out-dir results/custom_benchmarks/your_adapter
```

The adapter contract lives in `src/tgnn_solv/benchmark_adapters.py` and expects:

- `describe()`
- `fit(...)`
- `predict_frame(...)`

This is the maintained path when a custom model should behave like a normal
in-repo benchmark participant rather than an ad hoc CSV dump.

## Thermodynamic Stress Suite

Once you already have a canonical `predictions.csv`, run the stress suite:

```bash
python scripts/evaluation/run_thermo_stress_suite.py \
    --predictions-csv results/custom_benchmarks/your_adapter/predictions.csv \
    --train-data notebooks/data/processed/train.csv \
    --output results/custom_benchmarks/your_adapter/stress_suite.json
```

This adds slice-level metrics for:

- temperature extremes
- very low vs moderate/high solubility
- missing `T_m` / `dH_fus` supervision
- water vs organic solvents
- extreme `γ∞`-like regimes when those columns are present
- seen vs unseen chemistry relative to the training split

## Frozen Benchmark Release

To freeze a benchmark release with checksums for processed splits and bundles:

```bash
python scripts/experiments/build_benchmark_release.py \
    --release-name article-benchmark \
    --version 0.1.0 \
    --processed-dir notebooks/data/processed \
    --bundle-root results/external_baselines/article_benchmark \
    --bundle-root results/custom_benchmarks \
    --out-dir results/releases/article_benchmark_v0_1_0
```

This writes `release_manifest.json` with hashes for:

- processed split CSVs
- `split_manifest.json`
- benchmark bundles and their sidecars
- optional checkpoints you choose to include

## Interpretation Guidance

Do not treat the repository as promising one immutable benchmark number.
Interpretation should focus on:

- matched split protocol
- matched training budget
- matched feature availability
- generated artifacts from your own run

Use:

- `evaluate_complete.py` for routine reports
- `benchmark_tgnn_solv.py` for richer checkpoint summaries
- `validate_physics.py` for TGNN-specific bottleneck diagnosis
- `run_full_budget_experiment.py` for deep TGNN-vs-DirectGNN analysis
- `run_medium_budget_comparison.py` for architecture screening
