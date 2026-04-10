# Training Guide

## Overview

The maintained training entry points are:

- `scripts/training/train.py`
  - TGNN-Solv with the three-phase curriculum
- `scripts/training/train_with_pretrain.py`
  - TGNN-Solv with Stage 0 enabled by default
- `scripts/training/train_directgnn.py`
  - DirectGNN with a flat solubility-training schedule
- `tgnn_solv.pretrain.Pretrainer`
  - Stage 0 encoder/readout pretraining API used by the CLI and notebooks

Canonical processed data lives under:

- `notebooks/data/processed/train.csv`
- `notebooks/data/processed/val.csv`
- `notebooks/data/processed/test.csv`

The grouped `scripts/training/` entry points are the preferred navigation
surface. Legacy top-level `scripts/train.py` and
`scripts/train_directgnn.py` remain supported as compatibility wrappers.

If you prefer a visual orchestration layer on top of the same training CLIs,
use [Experiment Lab](experiment_lab.md). Its `Training`, `Pipeline Studio`,
`Model Architect`, and `HPO Lab` workspaces all delegate to the maintained
training and experiment entry points described on this page.

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

## Optional Stage 0 Pretraining

This repository also implements an optional encoder/readout pretraining stage
that happens before the three-phase curriculum above.

Important distinction:

- `Phase 1` in `trainer.py`
  - supervised warmup on the solubility dataset’s auxiliary labels
- `Stage 0` in `pretrain.py`
  - separate self-supervised / weakly supervised molecular pretraining on a
    large SMILES collection

The maintained Stage 0 surfaces are now:

- `scripts/training/train.py --pretrain ...`
- `scripts/training/train.py --pretrain-checkpoint ...`
- `scripts/training/train_with_pretrain.py`
- the Python API in `tgnn_solv.pretrain` / `tgnn_solv.pretrain_pipeline`
- `notebooks/02_train.ipynb`

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
- RDKit property regression over the maintained 12-descriptor target vector
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
- the CLI can also save a dedicated Stage 0 checkpoint containing:
  - `gnn_state_dict`
  - `readout_state_dict`
  - `pretrain_history`
  - `pretrain_metadata`

Important implementation notes:

- Stage 0 is compatible with `encoder_type="mpnn"`, `encoder_type="gps"`,
  and `encoder_type="timp"`
- `Pretrainer` passes the PyG `batch` vector into the encoder, so GPS
  positional encodings and TIMP channel-aware readout wiring remain valid
  during Stage 0
- `tgnn_solv.pretrain_pipeline` is the maintained helper layer for loading
  SMILES sources, saving warm-start checkpoints, and restoring those weights
  later through `--pretrain-checkpoint`

### Stage 0 through the maintained CLI

Run Stage 0 and then the normal TGNN curriculum:

```bash
python scripts/training/train.py \
    --config configs/paper_config_tuned_pretrained.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_pretrained.pt \
    --pretrain \
    --pretrain-data zinc250k \
    --pretrain-epochs 30 \
    --device cuda
```

Or use the convenience wrapper:

```bash
python scripts/training/train_with_pretrain.py \
    --config configs/paper_config_tuned_pretrained.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_pretrained.pt \
    --pretrain-data zinc250k \
    --pretrain-epochs 30 \
    --device cuda
```

Reuse a previously saved Stage 0 checkpoint instead of rerunning ZINC:

```bash
python scripts/training/train.py \
    --config configs/paper_config_tuned_pretrained_descriptors.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_pretrained_descriptors.pt \
    --pretrain-checkpoint checkpoints/pretrained_encoder.pt \
    --run-descriptor-probe \
    --device cuda
```

This is the maintained warm-start path when you want one Stage 0 artifact to be
reused across several downstream TGNN variants such as:

- tuned TGNN
- GPS TGNN
- TGNN + descriptor augmentation
- TGNN + GC crystal priors

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

Additional TGNN-only switches worth knowing:

- `--pretrain`
- `--pretrain-checkpoint`
- `--pretrain-epochs`
- `--pretrain-batch-size`
- `--pretrain-lr`
- `--pretrain-data`
- `--pretrain-output`
- `--run-descriptor-probe`

## Interactive Training Surfaces

The repository also ships a maintained GUI for the same workflow:

- `Training`
  - launch tuned TGNN-Solv and DirectGNN runs
- `Pipeline Studio`
  - wire multi-step DAGs and save them as repo-local presets
- `Model Architect`
  - edit TGNN-Solv / DirectGNN configs and inspect active branches visually
- `HPO Lab`
  - launch Optuna and inspect study artifacts

Launch it with:

```bash
python scripts/launch_lab.py
```

## Checkpoint Contents

TGNN checkpoints saved by `scripts/training/train.py` include:

- model weights
- serialized config
- training history
- optional evaluation metrics
- resume state when checkpointing during training
- sidecars written next to the checkpoint:
  - `<checkpoint>.manifest.json`
  - `<checkpoint>.model_card.json`

When TGNN descriptor augmentation is enabled, the checkpoint also stores:

- `descriptor_mean`
- `descriptor_std`

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
- `configs/paper_config_tuned_tgnn_descriptors.yaml`
  - tuned TGNN with shared RDKit descriptor augmentation
- `configs/paper_config_tuned_regularized.yaml`
  - tuned TGNN with higher dropout, weight decay, stronger `tau_reg`, and early stopping
- `configs/paper_config_tuned_regularized_gc.yaml`
  - the same regularized schedule plus GC crystal priors
- `configs/paper_config_tuned_regularized_descriptors.yaml`
  - regularized tuned TGNN plus descriptor augmentation
- `configs/paper_config_tuned_gps.yaml`
  - tuned TGNN with the GPS encoder replacing the local-only MPNN
- `configs/paper_config_timp.yaml`
  - tuned TGNN with thermodynamics-informed message passing, Gasteiger
    charges, and physical edge features
- `configs/paper_config_timp_full.yaml`
  - TIMP plus thermo-biased cross-attention
- `configs/paper_config_tuned_pretrained.yaml`
  - tuned TGNN intended for Stage 0 + curriculum experiments
- `configs/paper_config_tuned_pretrained_descriptors.yaml`
  - Stage 0 + descriptor-augmented TGNN
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

- Stage 0 pretraining is optional but now supported directly by the main TGNN CLI.
- The main paper-style CLI still starts directly from the three-phase curriculum unless you pass `--pretrain` or `--pretrain-checkpoint`.
- Oracle injection is training-only unless a diagnostic script explicitly
  forces it during evaluation.
- Pair-temperature batching is important if you want temperature-consistency
  losses such as `pair_temp_rank` and `vant_hoff_local` to have enough same-pair
  temperature structure inside a batch.

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Config Cookbook](config_cookbook.md)
- [Experiments & Benchmarks](experiments.md)
- [Experiment Lab](experiment_lab.md)
- [Free GPU / Preemptible Training](free_gpu_training.md)
- [Troubleshooting](troubleshooting.md)

</div>
