# Evaluation Guide

## Overview

Different evaluation scripts answer different questions:

- `scripts/evaluate_complete.py`
  - quick checkpoint evaluation with figure-ready arrays
- `scripts/benchmark_tgnn_solv.py`
  - richer `Evaluator`-backed benchmark report
- `scripts/validate_physics.py`
  - TGNN physical-parameter diagnostics
- `scripts/run_split_comparisons.py`
  - fair comparison across scaffold, solute, and solvent splits
- `scripts/run_full_budget_experiment.py`
  - full-budget TGNN-vs-DirectGNN diagnostic export
- `scripts/run_medium_budget_comparison.py`
  - full-split medium-budget architecture comparison

## `scripts/evaluate_complete.py`

Use this for lightweight checkpoint evaluation:

```bash
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output results/full_evaluation.json \
    --verbose
```

Outputs include:

- overall regression metrics
- temperature-stratified metrics
- solubility-range metrics
- solvent-type metrics
- auxiliary-label-availability metrics
- `true_ln_x2` / `pred_ln_x2` arrays for plotting

Use this as the default quick report.

## `scripts/benchmark_tgnn_solv.py`

Use this when you want the richer `Evaluator` path:

```bash
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/results.json
```

It shares the same broad report schema as `evaluate_complete.py`, but is more
convenient for deeper benchmark summaries.

## `scripts/validate_physics.py`

Use this when you care about TGNN intermediates rather than only final
solubility error:

```bash
python scripts/validate_physics.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output results/physics_validation.json \
    --device cuda
```

This script understands the current optional feature paths, including:

- Morgan augmentation
- descriptor priors
- fixed group priors
- crystal GC priors

## `scripts/run_split_comparisons.py`

Use this for fair comparison across split protocols:

```bash
python scripts/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline,rf_morgan,rf_hybrid" \
    --config configs/paper_config.yaml \
    --n-seeds 3 \
    --output results/split_comparisons.json
```

It:

- resolves canonical train/val/test triplets for each split family
- runs the requested models on matched data
- stores per-split artifacts under `results/split_comparisons/`
- aggregates metrics across seeds

## `scripts/run_full_budget_experiment.py`

This is the most detailed single diagnostic runner in the repo:

```bash
python scripts/run_full_budget_experiment.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --seeds 42 \
    --output-dir results/full_budget_experiment \
    --device cuda
```

It does all of the following in one command:

- trains TGNN-Solv on the full paper budget
- trains DirectGNN on an equivalent total epoch budget
- evaluates both on the same test split
- exports TGNN intermediate physical parameters for every test sample
- reruns TGNN inference in forced-oracle mode
- writes an interpretation guide alongside the metrics

Per-seed and aggregate artifacts include:

- `metrics.json`
- `diagnostics.json`
- `tgnn_intermediates.csv`
- `README.md`

The intermediate CSV includes, when available:

- `T_m_pred`, `dH_fus_pred`, `dCp_fus_pred`
- `T_m_solver`, `dH_fus_solver`, `dCp_fus_solver`
- `T_m_gc` for GC-prior crystal runs
- `tau_12_pred`, `tau_21_pred`, `alpha_pred`
- `ln_gamma2_pred`
- `Phi_pred`
- `ln_x2_physics`
- `ln_x2_final`
- correction magnitude and gate outputs
- true `T_m` / `dH_fus`
- oracle usage masks

The runner reuses resumable per-seed checkpoints created by the main training
CLIs.

## `scripts/run_medium_budget_comparison.py`

Use this for the full-scaffold medium-budget architecture comparison:

```bash
python scripts/run_medium_budget_comparison.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/medium_budget \
    --device cuda
```

It trains and evaluates:

- `tgnn_tuned`
- `tgnn_gc_priors`
- `tgnn_no_bridge`
- `tgnn_combined_no_oracle`
- `directgnn_tuned`
- `directgnn_descriptors`
- `rf_descriptors`

Top-level outputs:

- `results/medium_budget/summary.json`
- `results/medium_budget/comparison_table.md`
- `results/medium_budget/per_model/<model>/...`

For TGNN models, per-model outputs include:

- `metrics.json`
- `standard_intermediates.csv`
- `oracle_intermediates.csv`
- `config.yaml`
- `resolved_config.json`
- training logs and checkpoints

The combined TGNN comparison derives a no-oracle training config from
`paper_config_combined.yaml` and still evaluates oracle mode afterward.

## FastSolv and Other External Comparisons

Preferred FastSolv wrapper:

```bash
python scripts/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics results/fastsolv_compare.json
```

SolProp remains an optional separate-environment workflow.

## Practical Guidance

Use:

- `evaluate_complete.py`
  - for quick checkpoint reports
- `benchmark_tgnn_solv.py`
  - for richer benchmark summaries
- `validate_physics.py`
  - for TGNN-only physical diagnostics
- `run_split_comparisons.py`
  - for fair split-protocol comparisons
- `run_full_budget_experiment.py`
  - for full-budget TGNN-vs-DirectGNN diagnosis
- `run_medium_budget_comparison.py`
  - for the full-split medium-budget architecture study
