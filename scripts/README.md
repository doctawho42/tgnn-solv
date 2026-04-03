# Scripts Layout

The repository now exposes two parallel CLI layouts:

- legacy top-level entry points under `scripts/*.py`
- categorized wrappers under:
  - `scripts/data/`
  - `scripts/training/`
  - `scripts/evaluation/`
  - `scripts/experiments/`
  - `scripts/external/`

## Why Both Exist

The top-level scripts remain the compatibility surface for:

- existing docs and copy-paste commands
- tests that import script modules directly
- runners that import other scripts by filename
- external automation such as `reproduce.sh`

The categorized paths are the preferred navigation surface for humans.
They delegate to the legacy entry points, so behavior stays identical.

## Category Map

### `scripts/data/`

- `prepare_data.py`

### `scripts/training/`

- `train.py`
- `train_directgnn.py`
- `diagnose_training.py`
- `run_resume_safe_train.sh`

### `scripts/evaluation/`

- `evaluate_complete.py`
- `benchmark_tgnn_solv.py`
- `validate_physics.py`
- `analyze_benchmark.py`
- `compare_models.py`
- `error_analysis.py`

### `scripts/experiments/`

- `run_seeds.py`
- `run_ablation.py`
- `run_split_comparisons.py`
- `run_full_budget_experiment.py`
- `run_medium_budget_comparison.py`
- `run_optuna.py`
- `learning_curves.py`
- `temperature_extrapolation.py`
- `statistical_tests.py`
- `generate_paper_figures.py`
- `generate_supplementary.py`

### `scripts/external/`

- `run_fastsolv.py`
- `compare_fastsolv_tgnn.py`
- `run_solprop.py`

## Usage Guidance

Preferred examples:

```bash
python scripts/training/train.py --help
python scripts/evaluation/evaluate_complete.py --help
python scripts/experiments/run_medium_budget_comparison.py --help
python scripts/external/run_fastsolv.py --help
```

Legacy top-level paths remain supported and unchanged.
