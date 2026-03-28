# Data Preparation

## Overview

The data pipeline merges a primary solubility dataset with several auxiliary
property sources, then creates group-aware train/validation/test splits.

Main sources used by `src/tgnn_solv/data/sources.py`:

- `BigSolDBv2.1`
  - primary solubility records with temperature and `ln_x2`
- Bradley melting points
  - broad `T_m` coverage
- curated NIST-like overrides and fusion-property sources
  - used for `T_m` and `dH_fus` enrichment
- Hansen parameters
  - `hansen_d`, `hansen_p`, `hansen_h`
- IDAC / infinite-dilution activity coefficients
  - `ln_gamma_inf`

The merged dataframe is built by `DataBuilder` and then split with the helpers
in `split.py` and `split_registry.py`.

## Canonical CLI

```bash
python scripts/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42
```

Useful flags:

```bash
python scripts/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42 \
    --train-ratio 0.8 \
    --val-ratio 0.1 \
    --test-ratio 0.1 \
    --skip-download
```

`--skip-download` expects the raw files to already exist under the sibling
`raw/` directory.

## What the Script Does

`scripts/prepare_data.py` performs the same high-level workflow as
`notebooks/01_prepare_data.ipynb`:

1. load the primary solubility source
2. filter for SLE-compatible records
3. load auxiliary property sources
4. merge everything with `DataBuilder`
5. create all canonical split families
6. write split metadata to `split_manifest.json`
7. print split sizes and auxiliary-label coverage

## Output Files

One run writes all supported split families:

- `train.csv`, `val.csv`, `test.csv`
- `train_solute.csv`, `val_solute.csv`, `test_solute.csv`
- `train_solvent.csv`, `val_solvent.csv`, `test_solvent.csv`
- `split_manifest.json`

The canonical training path uses:

- `train.csv`
- `val.csv`
- `test.csv`

The `_solute` and `_solvent` variants are comparison splits used by
split-protocol analyses.

## Processed CSV Schema

Required columns for model training or evaluation:

- `solute_smiles`
- `solvent_smiles`
- `temperature`
- `ln_x2`

Common mask and auxiliary columns:

- `has_solubility`
- `T_m`
- `has_T_m`
- `dH_fus`
- `has_dH_fus`
- `hansen_d`
- `hansen_p`
- `hansen_h`
- `has_hansen`
- `ln_gamma_inf`
- `has_gamma_inf`
- `source`

The dataset layer will derive additional non-CSV fields at load time, such as:

- solvent type ids
- pair keys for same-pair temperature batching
- Morgan fingerprints
- RDKit descriptors
- descriptor prior features
- fixed group prior features
- crystal GC priors

Two important transformations do not happen in the CSV layer:

- GC-prior `T_m_gc` calibration
  - `scripts/train.py` fits `gc_prior_tm_scale` and `gc_prior_tm_bias` on the
    training split only when `use_gc_priors_crystal=True`
- DirectGNN descriptor normalization
  - `scripts/train_directgnn.py` computes descriptor mean/std on the training
    split only and stores them in the checkpoint

## Split Modes

The split logic lives in `src/tgnn_solv/data/split.py`.

Supported modes:

- `solute_scaffold`
  - default and strictest molecular generalization split
- `solute`
  - grouped by exact solute SMILES
- `solvent`
  - prevents solvent overlap between splits

All modes use group-preserving assignment rather than naive row-wise random
splits.

## Auxiliary-Only Rows

The builder can append auxiliary-only rows for pretraining, for example
compounds with fusion-property labels but no solubility measurement. This is
part of why the processed CSVs may contain rows where:

- `has_solubility=False`
- `ln_x2` is present only as a placeholder target value

The training loss masks these cases correctly.

## Fair-Comparison Guidance

When comparing against older literature or simpler baselines:

- report `solute_scaffold` as the strict result
- report `solute` only when matching a less strict protocol
- use `scripts/run_split_comparisons.py` to avoid accidental split drift

## Data-Loader Feature Paths

`TGNNSolvDataset` computes optional side information lazily and caches it:

- Morgan fingerprints
- full RDKit descriptor vectors for DirectGNN augmentation
- compact descriptor-prior features for `Hansen` / `V_m`
- fixed group-count prior features for `Hansen` / `V_m`
- crystal GC priors for `T_m`, `dH_fus`, `dCp_fus`

These are dataset-time features, not precomputed CSV columns.

Notes on the two higher-variance feature paths:

- RDKit descriptor vectors are computed through the shared feature helper and
  sanitized to finite values before model normalization.
- GC crystal priors are raw per-molecule estimates. The training script may
  later calibrate `T_m_gc`, but the dataset intentionally exposes the raw
  prior values.
