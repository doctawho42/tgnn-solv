# Baselines

## Overview

The repository contains or wraps five main baseline families:

- `DirectGNN`
- `DirectGNN + descriptors`
- `RandomForest` on RDKit descriptors / Morgan / hybrid features
- `Ideal SLE`
- optional external baselines: FastSolv and SolProp

These baselines answer different failure-mode questions. They should not be
treated as interchangeable.

## DirectGNN

`DirectGNN` is the main matched no-physics ablation:

- same graph backbone as TGNN-Solv
- same interaction stack
- no NRTL head
- no SLE solver
- direct prediction of `ln(x2)`

Train the maintained tuned baseline with:

```bash
python scripts/train_directgnn.py \
    --config configs/paper_config_directgnn_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn_tuned.pt \
    --device cuda
```

Multi-seed runs:

```bash
python scripts/run_seeds.py \
    --train-script scripts/train_directgnn.py \
    --config configs/paper_config_directgnn_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/directgnn_multi_seed_results.json \
    --checkpoint-dir checkpoints/directgnn_seeds \
    --device cuda
```

`train_directgnn.py` also supports resumable checkpoints through
`--checkpoint-every` and `--resume`.

## DirectGNN + Descriptor Augmentation

This baseline tests whether the remaining gap is mostly missing chemical side
information rather than the absence of the physics bottleneck.

Enabled config:

- `configs/paper_config_directgnn_descriptors.yaml`

Run:

```bash
python scripts/train_directgnn.py \
    --config configs/paper_config_directgnn_descriptors.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn_desc.pt \
    --device cuda
```

Maintained descriptor-path behavior:

- uses the standard RDKit descriptor set from `Descriptors.descList`
- computes descriptors for both solute and solvent
- sanitizes NaN/Inf descriptor values to zero before normalization
- normalizes with train-set mean/std only
- stores `descriptor_mean` and `descriptor_std` in the checkpoint
- reuses one descriptor MLP for both molecular roles

## RandomForest Baselines

`src/tgnn_solv/baselines/rf_baseline.py` supports three feature modes:

- `descriptors`
- `morgan`
- `hybrid`

Run directly:

```bash
python -m tgnn_solv.baselines.rf_baseline \
    --train notebooks/data/processed/train.csv \
    --test notebooks/data/processed/test.csv \
    --feature-mode descriptors \
    --output results/rf_descriptors.json
```

Morgan example:

```bash
python -m tgnn_solv.baselines.rf_baseline \
    --train notebooks/data/processed/train.csv \
    --test notebooks/data/processed/test.csv \
    --feature-mode morgan \
    --morgan-n-bits 2048 \
    --output results/rf_morgan.json
```

The descriptor RF baseline uses the same shared RDKit descriptor helper as the
descriptor-augmented DirectGNN path, so descriptor comparisons are aligned on
the same feature family.

## Ideal SLE

`Ideal SLE` is the physics-only baseline with no learned interaction term.

Run:

```bash
python -m tgnn_solv.baselines.ideal_sle \
    --train notebooks/data/processed/train.csv \
    --test notebooks/data/processed/test.csv \
    --output results/ideal_sle_baseline.json
```

Behavior:

- assumes `gamma = 1`
- uses `T_m` and `dH_fus` when available
- can include the `dCp_fus` term when present
- falls back to simpler assumptions when fusion data are missing

This is the floor for "physics alone without learned nonideality".

## FastSolv

FastSolv is an optional external descriptor baseline.

Preferred usage is inference or comparison with pretrained weights:

```bash
python scripts/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/fastsolv_predictions.csv

python scripts/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics results/fastsolv_compare.json
```

Training FastSolv from scratch on TGNN-Solv data remains environment-sensitive
and is not the recommended default workflow.

## SolProp

SolProp is another optional external baseline that usually lives in its own
environment.

Prediction:

```bash
conda activate solprop
python scripts/run_solprop.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/solprop_predictions.csv \
    --temperature_dependent
```

Calibration on your own split:

```bash
conda activate solprop
python scripts/run_solprop.py train \
    --train notebooks/data/processed/train.csv \
    --val notebooks/data/processed/val.csv \
    --test notebooks/data/processed/test.csv \
    --outdir checkpoints/solprop_run \
    --temperature_dependent \
    --include_temperature \
    --export_preds
```

## Comparison Runners

For fair comparison across split protocols:

```bash
python scripts/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline,rf_morgan,rf_hybrid" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

For the maintained full-scaffold medium-budget architecture comparison:

```bash
python scripts/run_medium_budget_comparison.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/medium_budget \
    --device cuda
```

That runner evaluates:

- tuned TGNN
- TGNN + GC priors
- TGNN + no bridge
- TGNN + GC priors + no bridge, trained without oracle injection
- tuned DirectGNN
- DirectGNN + descriptors
- RF on descriptors

## Suggested Reading Order

If you want the most informative progression:

1. `Ideal SLE`
2. `RF(descriptors)`
3. `DirectGNN`
4. `DirectGNN + descriptors`
5. `TGNN-Solv`
6. external pretrained baselines such as FastSolv or SolProp

That ordering isolates:

- pure thermodynamic structure
- descriptor information
- graph-learning capacity without physics
- whether descriptor side information closes the GNN gap
- whether the full physics bottleneck adds value
