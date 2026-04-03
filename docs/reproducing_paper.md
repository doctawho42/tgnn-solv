# Reproducing the Main Workflow

## Entry Point

The repository-level reproduction driver is:

- `reproduce.sh`

Run it from the repo root:

```bash
bash reproduce.sh
```

## What `reproduce.sh` Actually Runs

As of the current codebase, `reproduce.sh` performs this sequence:

1. validate Python, PyTorch, PyG, and package importability
2. prepare data with `scripts/prepare_data.py` if processed CSVs are missing
3. run 5-seed TGNN-Solv training with `scripts/run_seeds.py`
4. run a matched 5-seed `split_late` backbone comparison
5. evaluate the best TGNN checkpoint with `scripts/evaluate_complete.py`
6. run `scripts/error_analysis.py`
7. run `scripts/run_ablation.py`
8. run baseline and analysis steps:
   - DirectGNN multi-seed baseline
   - FastSolv prediction if available
   - learning curves
   - temperature extrapolation
   - physics validation
   - split-wise comparison
   - statistical tests
   - supplementary tables
   - figure generation

## Canonical Commands Behind the Script

### Data preparation

```bash
python scripts/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42
```

### 5-seed TGNN-Solv run

```bash
python scripts/run_seeds.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/multi_seed_results.json \
    --checkpoint-dir checkpoints/seeds \
    --device cuda
```

### 5-seed split-late comparison

```bash
python scripts/run_seeds.py \
    --config configs/paper_config_split_late.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/split_late_multi_seed_results.json \
    --checkpoint-dir checkpoints/split_late_seeds \
    --device cuda
```

### Best-checkpoint evaluation

```bash
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/seeds/seed_<best>.pt \
    --output results/full_evaluation.json \
    --verbose
```

## Important Scope Boundary

`reproduce.sh` is the paper-style automation path, but it does not cover every
research mode now present in the codebase.

Note on script layout:

- the repo now exposes grouped human-facing entry points under `scripts/data/`,
  `scripts/training/`, `scripts/evaluation/`, `scripts/experiments/`, and
  `scripts/external/`
- `reproduce.sh` intentionally keeps using the legacy top-level
  `scripts/*.py` paths because those wrappers remain the compatibility surface

The following maintained configs and experiment paths are available but are not
part of the default reproduction script:

- `paper_config_tuned.yaml`
- `paper_config_gc_priors.yaml`
- `paper_config_oracle.yaml`
- `paper_config_no_bridge.yaml`
- `paper_config_no_bridge_no_walden.yaml`
- `paper_config_combined.yaml`
- `paper_config_directgnn_tuned.yaml`
- `paper_config_directgnn_descriptors.yaml`
- `scripts/run_full_budget_experiment.py`
- `scripts/run_medium_budget_comparison.py`

Those are research or diagnostic extensions, not default reproduction targets.

## Expected Artifacts

After a successful run, the most important outputs are:

- `results/multi_seed_results.json`
- `results/split_late_multi_seed_results.json`
- `results/directgnn_multi_seed_results.json`
- `results/full_evaluation.json`
- `results/error_analysis.json`
- `results/ablation.json`
- `results/learning_curves.json`
- `results/temperature_extrapolation.json`
- `results/physics_validation.json`
- `results/split_comparisons.json`
- `results/significance.json`
- `figures/`
- `tables/`

Optional artifacts appear when optional dependency stacks are installed, for
example FastSolv outputs.

## Validating a Reproduction Run

The repo does not ship one fixed benchmark JSON that should be treated as the
only acceptable numeric outcome. Exact metrics depend on:

- hardware
- optional dependency availability
- the chosen split files
- random seeds
- checkpoint reuse vs retraining

Treat your generated artifacts as the authoritative outputs of your run.

A successful reproduction means:

- all expected JSON and CSV artifacts are created
- the best-seed checkpoint resolves cleanly into `full_evaluation.json`
- the plotting and supplementary scripts can consume the generated files
- optional steps are either completed or skipped with clear warnings

## Separate Full-Budget Diagnostic Study

If you want the stricter TGNN-vs-DirectGNN budget-matched diagnostic run with
intermediate physical export, use:

```bash
python scripts/run_full_budget_experiment.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --seeds 42 \
    --output-dir results/full_budget_experiment \
    --device cuda
```

That experiment is intentionally separate from `reproduce.sh` because it is
slower and diagnostic-heavy.

## Separate Medium-Budget Architecture Study

For the full-split medium-budget comparison used for architecture triage, run:

```bash
python scripts/run_medium_budget_comparison.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/medium_budget \
    --device cuda
```

This runner trains:

- `tgnn_tuned`
- `tgnn_gc_priors`
- `tgnn_no_bridge`
- `tgnn_combined_no_oracle`
- `directgnn_tuned`
- `directgnn_descriptors`
- `rf_descriptors`

The combined TGNN run is derived from `paper_config_combined.yaml`, but oracle
injection is disabled during training in that specific comparison so the study
isolates GC priors and no-bridge behavior.

## Expected Runtime

Wall-clock time varies significantly. On a single modern GPU, rough guidance:

| Stage | Expected Time |
|------|---------------|
| Data preparation | 5-20 minutes |
| 5-seed TGNN-Solv training | several hours to half a day |
| Best-checkpoint evaluation | 10-20 minutes |
| Ablations and learning curves | many additional hours |
| Full end-to-end workflow | half a day to more than a day |

## Practical Caveats

- `reproduce.sh` can skip optional steps when dependencies such as FastSolv are
  not installed.
- `scripts/train.py` and `scripts/train_directgnn.py` support
  `--checkpoint-every` and `--resume`.
- `run_full_budget_experiment.py` and `run_medium_budget_comparison.py` reuse
  those resumable checkpoints automatically.
- Notebooks remain useful for exploratory inspection, but CLI paths are the
  reproducible default.
