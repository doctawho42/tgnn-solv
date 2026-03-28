# Training Guide

## Overview

The maintained training entry points are:

- `scripts/train.py`
  - TGNN-Solv with the three-phase curriculum
- `scripts/train_directgnn.py`
  - DirectGNN with a flat solubility-training schedule

Canonical processed data lives under:

- `notebooks/data/processed/train.csv`
- `notebooks/data/processed/val.csv`
- `notebooks/data/processed/test.csv`

## TGNN-Solv Training

Paper-style training command:

```bash
python scripts/train.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --device cuda
```

Maintained tuned baseline for architecture comparison:

```bash
python scripts/train.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_tuned.pt \
    --device cuda
```

Common CLI overrides:

- `--hidden-dim`
- `--n-gnn-layers`
- `--batch-size`
- `--lr` for `lr_phase2`
- `--checkpoint-every`
- `--resume`

## Curriculum

`TGNN-Solv` uses three phases.

### Phase 1

- property pretraining only
- no `ln(x2)` loss
- correction frozen
- if `use_gc_priors_crystal=True`, the GC residual branches can be frozen for
  the first `gc_prior_residual_freeze_epochs`

### Phase 2

- full SLE training
- `ln(x2)` is active
- correction unfreezes at `phase2_correction_unfreeze_epoch`
- oracle injection, if enabled, anneals toward zero near the end of the phase

### Phase 3

- low-learning-rate fine-tuning
- stronger correction and consistency regularization
- oracle injection forced off

The canonical paper budget is `50 / 200 / 50`.

## GC-Prior Crystal Runs

When `use_gc_priors_crystal=True`, `scripts/train.py` performs two extra steps:

1. it computes raw per-solute GC priors through the dataset path
2. it fits a train-only affine calibration for `T_m_gc`

The learned calibration is stored back into the config as:

- `gc_prior_tm_scale`
- `gc_prior_tm_bias`

The residual crystal branches are also zero-initialized so that the starting
prediction matches the calibrated GC prior exactly.

## Resume Support

Both main training CLIs support resumable checkpoints:

```bash
python scripts/train.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_resume.pt \
    --checkpoint-every 5 \
    --device cuda
```

Resume the same run later with:

```bash
python scripts/train.py \
    --resume checkpoints/tgnn_resume.pt \
    --checkpoint checkpoints/tgnn_resume.pt \
    --device cuda
```

DirectGNN supports the same pattern through `scripts/train_directgnn.py`.

For cloud or preemptible sessions, `scripts/run_resume_safe_train.sh` wraps the
TGNN CLI and reuses the checkpoint automatically.

## Multi-Seed Runs

Use `scripts/run_seeds.py` for maintained multi-seed wrappers:

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

You can also point it at `scripts/train_directgnn.py`.

## DirectGNN Training

Maintained tuned baseline:

```bash
python scripts/train_directgnn.py \
    --config configs/paper_config_directgnn_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn_tuned.pt \
    --device cuda
```

DirectGNN uses:

- the same graph backbone
- the same pair-aware batching controls
- a single flat budget controlled by `epochs_phase2`

### DirectGNN with descriptor augmentation

```bash
python scripts/train_directgnn.py \
    --config configs/paper_config_directgnn_descriptors.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn_desc.pt \
    --device cuda
```

This path:

- computes the full RDKit descriptor vector for solute and solvent
- sanitizes NaN/Inf descriptor values to zero
- computes descriptor mean/std on the training split only
- stores `descriptor_mean` and `descriptor_std` in the checkpoint
- reuses one descriptor MLP for both molecular roles

## Important Config Variants

Maintained TGNN configs:

- `configs/paper_config.yaml`
  - canonical paper-style training config
- `configs/paper_config_tuned.yaml`
  - maintained tuned TGNN baseline
- `configs/paper_config_split_late.yaml`
  - late role-specific encoder blocks
- `configs/paper_config_gc_priors.yaml`
  - crystal GC priors with residual warm-start and freeze control
- `configs/paper_config_oracle.yaml`
  - training-time oracle injection
- `configs/paper_config_no_bridge.yaml`
  - bridge disabled, Walden enabled
- `configs/paper_config_no_bridge_no_walden.yaml`
  - bridge and Walden both disabled
- `configs/paper_config_combined.yaml`
  - GC priors + no bridge + Walden + oracle injection

Maintained DirectGNN configs:

- `configs/paper_config_directgnn_tuned.yaml`
  - tuned no-physics baseline
- `configs/paper_config_directgnn_descriptors.yaml`
  - descriptor-augmented DirectGNN baseline

## Experiment Runners

### Ablations

```bash
python scripts/run_ablation.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --variants full,fixed_group_priors,split_late_encoder,direct_gnn \
    --n-seeds 3 \
    --output results/ablation.json \
    --device cuda
```

### Full-budget diagnostic study

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

This runner:

- trains TGNN-Solv and DirectGNN on matched budgets
- exports TGNN intermediates
- runs forced-oracle evaluation
- reuses resumable per-seed checkpoints

### Medium-budget architecture comparison

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
injection is disabled during training for that specific comparison.

## Pair-Aware Temperature Batching

The canonical loader path uses:

- `use_pair_temperature_batching=True`
- `pair_temperature_min_group_size`
- `pair_temperature_group_chunk_size`

This matters because losses such as `pair_temp_rank` and `vant_hoff_local`
depend on seeing multiple temperatures from the same pair together.

## Bridge, Walden, and Oracle Controls

Current semantics:

- `bridge_loss_weight` defaults to `0.0`
- explicit per-phase `bridge` loss weights in YAML still override that default
- `configs/paper_config.yaml` therefore still trains with bridge loss through
  the phase-loss tables
- `use_walden_check=True` adds an unsupervised consistency penalty
- `use_oracle_injection=True` affects solver inputs during training, not normal
  inference

## Checkpoint Contents

TGNN checkpoints saved by `scripts/train.py` include:

- model weights
- serialized config
- training history
- optional evaluation metrics
- resume state when checkpointing during training

DirectGNN checkpoints include the same core items and additionally store
descriptor normalization stats when descriptor augmentation is enabled:

- `descriptor_mean`
- `descriptor_std`
