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

All maintained external/custom benchmark surfaces now write the same canonical
artifact bundle:

- `summary.csv`
- `report.json`
- `predictions.csv`
- `run_manifest.json`
- `benchmark_card.json`

That is the contract consumed by:

- `Results & Plots -> Benchmark Studio` in the lab
- supplementary benchmark tables
- artifact registry and compare views

The grouped CLI layout under `scripts/training/`, `scripts/experiments/`, and
`scripts/external/` is now the preferred navigation surface. Legacy top-level
script paths remain available as wrappers.

## DirectGNN

`DirectGNN` is the main matched no-physics ablation:

- same graph backbone as TGNN-Solv
- same interaction stack
- no NRTL head
- no SLE solver
- direct prediction of `ln(x2)`

Train the maintained tuned baseline with:

```bash
python scripts/training/train_directgnn.py \
    --config configs/paper_config_directgnn_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn_tuned.pt \
    --device cuda
```

Multi-seed runs:

```bash
python scripts/experiments/run_seeds.py \
    --train-script scripts/training/train_directgnn.py \
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

The maintained uncertainty helpers now also support `DirectGNN`, so the same
family can participate in:

- MC-dropout review
- deep ensembles
- interval calibration

inside both the Python API and `Experiment Lab`.

## DirectGNN + Descriptor Augmentation

This baseline tests whether the remaining gap is mostly missing chemical side
information rather than the absence of the physics bottleneck.

Enabled config:

- `configs/paper_config_directgnn_descriptors.yaml`

Run:

```bash
python scripts/training/train_directgnn.py \
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
python scripts/external/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/fastsolv_predictions.csv

python scripts/external/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics results/fastsolv_compare.json
```

The maintained wrapper now also supports scratch training/evaluation on the
repo's own scaffold-aware splits, but the recommended article-comparison path
is to call it through the shared orchestrator:

```bash
python scripts/experiments/run_external_baseline_benchmark.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --out-dir results/external_baselines/article_benchmark \
    --split-mode solute_scaffold \
    --fastsolv-mode both \
    --solprop-mode native
```

## SolProp

SolProp is another optional external baseline that usually lives in its own
environment. In this repository the maintained entry point is the wrapper
`scripts/run_solprop.py` (the legacy `scripts/external/run_solprop.py` path
still forwards to it).

Recommended local extras for the maintained wrappers:

```bash
pip install -e ".[baselines]"
```

The wrapper now supports three distinct SolProp baselines on TGNN-Solv data:

- `predict`
  - zero-shot SolProp runtime, exported back into `ln(x2)` / `logS`
- `train`
  - zero-shot SolProp plus train-split calibration
- `train-native`
  - native retraining of the SolProp MPNN/FFN architecture directly on our
    `ln(x2)` targets, using solvent, solute, and temperature as model inputs

That native mode is the maintained article benchmark path when you want
SolProp trained directly on the same target rather than only evaluated
zero-shot or with a shallow calibration layer.

Maintained comparison mode:

- zero-shot SolProp is run at `298.15 K`
- the wrapper then evaluates those predictions directly on our split, or
  calibrates them on the train split with optional temperature input
- native retraining of the SolProp architecture is the maintained article
  comparison path when you want the competitor architecture trained directly on
  TGNN-Solv targets

Important runtime note:

- upstream SolProp's temperature-dependent branch is numerically brittle on a
  non-trivial fraction of our rows
- the wrapper still exposes `--temperature-dependent`, but treats it as an
  experimental mode and can fall back row-wise to room-temperature inference

Prediction:

```bash
python scripts/run_solprop.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/solprop_predictions.csv
```

Calibration on your own split:

```bash
python scripts/run_solprop.py train \
    --train notebooks/data/processed/train.csv \
    --val notebooks/data/processed/val.csv \
    --test notebooks/data/processed/test.csv \
    --outdir checkpoints/solprop_run \
    --include-temperature
```

Native retraining on TGNN-Solv `ln(x2)`:

```bash
python scripts/run_solprop.py train-native \
    --train notebooks/data/processed/train.csv \
    --val notebooks/data/processed/val.csv \
    --test notebooks/data/processed/test.csv \
    --outdir checkpoints/solprop_native \
    --device cpu \
    --epochs 40 \
    --patience 10 \
    --batch-size 256 \
    --num-models 5
```

Native checkpoint inference:

```bash
python scripts/run_solprop.py predict-native \
    --checkpoint-dir checkpoints/solprop_native \
    --input notebooks/data/processed/test.csv \
    --output results/solprop_native_predictions.csv \
    --metrics results/solprop_native_report.json \
    --split-mode solute_scaffold
```

If the selected Python environment does not carry a working SolProp runtime,
extract the maintained repo-local copy once:

```bash
python scripts/external/install_solprop_runtime.py
```

and then point the wrapper or benchmark runner at that extraction with
`SOLPROP_RUNTIME_DIR` or `--solprop-runtime-dir`.

For a fair external-baseline sweep on the canonical split family:

```bash
python scripts/experiments/run_external_baseline_benchmark.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --out-dir results/external_baselines \
    --split-mode solute_scaffold \
    --fastsolv-mode both \
    --solprop-mode native
```

The resulting bundle is directly visible in:

- `Results & Plots -> Benchmark Studio`
- `Results & Plots -> Experiment registry`
- supplementary `Table S10` when generated

## Comparison Runners

For fair comparison across split protocols:

```bash
python scripts/experiments/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline,rf_morgan,rf_hybrid" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

For the maintained full-scaffold medium-budget architecture comparison:

```bash
python scripts/experiments/run_medium_budget_comparison.py \
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

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Results](results.md)
- [Experiments & Benchmarks](experiments.md)
- [Config Cookbook](config_cookbook.md)
- [Architecture](architecture.md)

</div>
