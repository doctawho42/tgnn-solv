# Training Guide

## Overview

The maintained training entry points are:

- `scripts/training/train.py`
  - TGNN-Solv with the three-phase curriculum
- `scripts/training/train_directgnn.py`
  - DirectGNN with a flat solubility-training schedule
- `tgnn_solv.pretrain.Pretrainer`
  - optional standalone Stage 0 encoder/readout pretraining API

Canonical processed data lives under:

- `notebooks/data/processed/train.csv`
- `notebooks/data/processed/val.csv`
- `notebooks/data/processed/test.csv`

The grouped `scripts/training/` entry points are the preferred navigation
surface. Legacy top-level `scripts/train.py` and
`scripts/train_directgnn.py` remain supported as compatibility wrappers.

## TGNN-Solv Training

Paper-style training command:

```bash
python scripts/training/train.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --device cuda
```

Maintained tuned baseline for architecture comparison:

```bash
python scripts/training/train.py \
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

`TGNN-Solv` uses three training phases after model construction.

### Phase 1

- supervised property-only warmup on the processed training split
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

## Optional Standalone Stage 0 Pretraining

This repository also implements an optional encoder/readout pretraining stage
that happens before the three-phase curriculum above.

Important distinction:

- `Phase 1` in `trainer.py`
  - supervised warmup on the solubility dataset’s auxiliary labels
- `Stage 0` in `pretrain.py`
  - separate self-supervised / weakly supervised molecular pretraining on a
    large SMILES collection

`scripts/training/train.py` does not run Stage 0 automatically. The maintained
surface for Stage 0 today is the Python API and the interactive
`notebooks/02_train.ipynb` walkthrough.

### What `Pretrainer` does

`src/tgnn_solv/pretrain.py` provides:

- `download_zinc250k(max_molecules=250000)`
  - downloads ZINC250k when available
  - falls back to unique BigSolDB SMILES if the download is unavailable
- `Pretrainer(model.gnn, model.readout, cfg, device)`
  - updates the encoder and readout in place
  - attaches temporary pretraining heads that are discarded afterward

The pretraining tasks are:

- masked 2-hop subgraph atom-feature reconstruction
- masked bond-type prediction
- RDKit property prediction
- graph contrastive learning on augmented molecular views

### Minimal Stage 0 example

```python
from tgnn_solv.pretrain import Pretrainer, download_zinc250k

smiles_list = download_zinc250k()
pretrainer = Pretrainer(model.gnn, model.readout, cfg, device=device)
history = pretrainer.pretrain(
    smiles_list,
    n_epochs=30,
    batch_size=128,
    lr=3e-4,
)
```

Practical behavior:

- `model.gnn` and `model.readout` are modified in place
- temporary atom/property/bond/contrastive heads are deleted after pretraining
- you continue with normal TGNN training using the same model instance
- there is no dedicated checkpoint schema just for Stage 0 today

## GC-Prior Crystal Runs

When `use_gc_priors_crystal=True`, `scripts/training/train.py` performs two
extra steps:

1. it computes raw per-solute GC priors through the dataset path
2. it fits a train-only affine calibration for `T_m_gc`

The learned calibration is stored back into the config as:

- `gc_prior_tm_scale`
- `gc_prior_tm_bias`

The residual crystal branches are also zero-initialized so that the starting
prediction matches the calibrated GC prior exactly.

If `gc_prior_residual_freeze_epochs > 0`, those residual branches stay frozen
for the early part of Phase 1. This is the maintained way to let a GC-prior
model start from the pure calibrated prior before learning residual
corrections.

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

## Resume Support

Both main training CLIs support resumable checkpoints:

```bash
python scripts/training/train.py \
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
python scripts/training/train.py \
    --resume checkpoints/tgnn_resume.pt \
    --checkpoint checkpoints/tgnn_resume.pt \
    --device cuda
```

DirectGNN supports the same pattern through
`scripts/training/train_directgnn.py`.

For cloud or preemptible sessions, `scripts/training/run_resume_safe_train.sh`
wraps the TGNN CLI and reuses the checkpoint automatically.

## Checkpoint Contents

TGNN checkpoints saved by `scripts/training/train.py` include:

- model weights
- serialized config
- training history
- optional evaluation metrics
- resume state when checkpointing during training

DirectGNN checkpoints include the same core items and additionally store
descriptor normalization stats when descriptor augmentation is enabled:

- `descriptor_mean`
- `descriptor_std`

## Multi-Seed Runs

Use `scripts/experiments/run_seeds.py` for maintained multi-seed wrappers:

```bash
python scripts/experiments/run_seeds.py \
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

You can also point it at `scripts/training/train_directgnn.py`.

## DirectGNN Training

Maintained tuned baseline:

```bash
python scripts/training/train_directgnn.py \
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
python scripts/training/train_directgnn.py \
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
python scripts/experiments/run_ablation.py \
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
python scripts/experiments/run_full_budget_experiment.py \
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
python scripts/experiments/run_medium_budget_comparison.py \
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

## Practical Distinctions

- Stage 0 pretraining is optional and library-driven today.
- The main paper-style CLI starts directly from the three-phase curriculum.
- Oracle injection is training-only unless a diagnostic script explicitly
  forces it during evaluation.
- Pair-temperature batching is important if you want temperature-consistency
  losses such as `pair_temp_rank` and `vant_hoff_local` to have enough same-pair
  temperature structure inside a batch.
