# Script Reference

This document maps every script and notebook to its intended role, maturity,
dependencies, and recommended usage.

## Maturity Legend

- **Production**: tested, documented, used in `reproduce.sh`
- **Research**: functional but may require manual intervention
- **Experimental**: may need adaptation to current APIs
- **Infrastructure**: internal utility, not user-facing

## Canonical CLI Workflow

| Entry point | Role | Status | Key dependencies | Notes |
|-------------|------|--------|------------------|-------|
| `scripts/prepare_data.py` | Download, merge, and split datasets | Canonical | pandas, RDKit, requests | CLI equivalent of `notebooks/01_prepare_data.ipynb` |
| `scripts/train.py` | Train one TGNN-Solv model | Canonical | PyTorch, PyG | Direct CLI mirror of the notebook training path |
| `scripts/run_seeds.py` | Run multiple training seeds and aggregate metrics | Canonical | Standard library, optional SciPy | Calls `scripts/train.py` repeatedly |
| `scripts/run_split_comparisons.py` | Compare multiple models across all canonical split protocols | Canonical | pandas, optional RDKit/scikit-learn, training CLIs | Produces split-wise comparison JSON and per-split artifacts |
| `scripts/evaluate_complete.py` | Lightweight checkpoint evaluation | Canonical | PyTorch, pandas, NumPy | Emits `true_ln_x2` and `pred_ln_x2` arrays for plotting |
| `scripts/generate_paper_figures.py` | Generate publication figures from result files | Canonical | matplotlib, NumPy, scikit-learn | Gracefully skips missing result artifacts |
| `reproduce.sh` | End-to-end reproduction driver | Canonical | Bash, Python, PyTorch, PyG | Orchestrates data, training, evaluation, optional baselines, and figures |

## Benchmarking and Analysis

| Entry point | Role | Status | Key dependencies | Notes |
|-------------|------|--------|------------------|-------|
| `scripts/benchmark_tgnn_solv.py` | Rich benchmark using `Evaluator` | Stable utility | PyTorch, PyG, pandas | Best choice for detailed stratified benchmarks |
| `scripts/analyze_benchmark.py` | Text summary of benchmark JSON | Stable utility | pandas, NumPy | Accepts both legacy and current benchmark key layouts |
| `scripts/compare_models.py` | Compare multiple TGNN-Solv checkpoints | Stable utility | Same as benchmark script | Wraps `benchmark_tgnn_solv.py` |

## Diagnostics and Tuning

| Entry point | Role | Status | Key dependencies | Notes |
|-------------|------|--------|------------------|-------|
| `scripts/diagnose_training.py` | Dataset statistics and overfit sanity check | Stable utility | PyTorch, PyG | Useful before expensive long training runs |
| `scripts/run_optuna.py` | Hyperparameter tuning for TGNN-Solv and baselines | Stable utility | Optuna, PyTorch, PyG | Uses the `OptunaTuner` API directly |

## Optional Baseline and Comparison Scripts

| Entry point | Role | Status | Key dependencies | Notes |
|-------------|------|--------|------------------|-------|
| `scripts/run_fastsolv.py` | Predict, train, or compare FastSolv | Optional | `fastsolv`, `fastprop`, Lightning | Main FastSolv wrapper |
| `scripts/run_solprop.py` | Predict or calibrate SolProp | Optional | `solprop_ml`, RDKit, scikit-learn | Supports a backward-compatible default `predict` mode |
| `scripts/compare_fastsolv_tgnn.py` | Lightweight TGNN-Solv vs FastSolv comparison | Legacy utility | Optional FastSolv/ONNX stack | Useful for quick comparisons, but `run_fastsolv.py compare` is the preferred baseline wrapper |

## Detailed Entries

### `scripts/_bootstrap.py`
**Status**: Infrastructure
**Purpose**: Shared path bootstrap for all scripts (import instead of inline `sys.path` hacks)
**Depends on**: nothing
**Produces**: nothing (side effect: adds `src/` to `sys.path`)

### `scripts/run_ablation.py`
**Status**: Research
**Purpose**: CLI for ablation study (reference model plus current comparison variants such as `fixed_group_priors`, `split_late_encoder`, `direct_gnn`, and small/large scaling sweeps)
**Depends on**: `configs/paper_config.yaml`, train/val/test CSVs, `src/tgnn_solv/ablation.py`
**Produces**: `results/ablation.json`

### `scripts/train_directgnn.py`
**Status**: Research
**Purpose**: CLI for training DirectGNN baseline (no physics)
**Depends on**: `configs/paper_config.yaml`, train/val CSVs, `src/tgnn_solv/baselines/`
**Produces**: `checkpoints/directgnn.pt`

### `scripts/statistical_tests.py`
**Status**: Production
**Purpose**: Paired statistical significance tests between model variants
**Depends on**: multi-seed result JSONs from `run_seeds.py`
**Produces**: `results/significance.json`

### `scripts/error_analysis.py`
**Status**: Research
**Purpose**: Detailed error analysis by solvent type, temperature, molecular descriptors
**Depends on**: `results/full_evaluation.json`, test CSV
**Produces**: `results/error_analysis.json`

### `scripts/learning_curves.py`
**Status**: Research
**Purpose**: Data efficiency experiment (performance vs training set size)
**Depends on**: `configs/`, train/val/test CSVs
**Produces**: `results/learning_curves.json`

### `scripts/temperature_extrapolation.py`
**Status**: Research
**Purpose**: Train on `T≤T_cut`, test on `T>T_cut` (physics extrapolation argument)
**Depends on**: `configs/`, full dataset CSV
**Produces**: `results/temperature_extrapolation.json`

### `scripts/validate_physics.py`
**Status**: Research (requires `return_intermediates` in model)
**Purpose**: Validate predicted physical parameters and van't Hoff consistency
**Depends on**: model checkpoint, test CSV
**Produces**: `results/physics_validation.json`

### `scripts/generate_supplementary.py`
**Status**: Production
**Purpose**: Generate LaTeX tables for Supplementary Information
**Depends on**: `results/*.json`
**Produces**: `tables/*.tex`, `tables/*.csv`

### `scripts/run_split_comparisons.py`
**Status**: Production
**Purpose**: Run fair split-wise comparisons across scaffold, solute, and solvent protocols
**Depends on**: processed split CSVs, `scripts/run_seeds.py`, `scripts/train_directgnn.py`, optional RDKit/scikit-learn for RF baseline
**Produces**: `results/split_comparisons.json`, `results/split_comparisons/*.json`

## Script Overlaps

Several scripts partially overlap on purpose:

- `scripts/evaluate_complete.py` vs `scripts/benchmark_tgnn_solv.py`
  - Use `evaluate_complete.py` for quick checkpoint metrics and figure-ready
    arrays.
  - Use `benchmark_tgnn_solv.py` for richer `Evaluator`-based stratification.
- `scripts/run_fastsolv.py compare` vs `scripts/compare_fastsolv_tgnn.py`
  - Prefer `run_fastsolv.py compare` when the FastSolv stack is installed.
  - Use `compare_fastsolv_tgnn.py` as a lightweight convenience wrapper.
- Notebook vs CLI workflows
  - Notebooks remain the best place for exploratory analysis and manual
    debugging.
  - The CLI workflow is the reproducible path for preparation, training,
    multi-seed runs, evaluation, ablations, paper-analysis experiments, figure
    generation, and supplementary tables.

## Notebook Reference

| Notebook | Role | Recommended usage |
|----------|------|-------------------|
| `notebooks/01_prepare_data.ipynb` | Data download, merge, split creation | Canonical notebook for data preparation |
| `notebooks/02_train.ipynb` | Training walkthrough | Canonical notebook for interactive training |
| `notebooks/03_inference.ipynb` | Interactive predictions | Examples and interpretation |
| `notebooks/04_evaluation.ipynb` | Rich evaluation workflow | Interactive inspection of trained models |
| `notebooks/05_baselines.ipynb` | DirectGNN baseline | Main manual baseline notebook |
| `notebooks/06_ablations.ipynb` | Ablation study | Main manual ablation workflow |
| `notebooks/07_temperature.ipynb` | Temperature analysis | Research notebook for temperature dependence |
| `notebooks/08_optuna_tuning.ipynb` | Optuna tuning | Notebook alternative to `scripts/run_optuna.py` |
