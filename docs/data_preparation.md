# Data Preparation

## Overview

The data pipeline combines a primary solubility dataset with auxiliary physical
property sources and then creates group-aware train/validation/test splits.

Main sources:

- **BigSolDBv2.1** — primary solubility dataset with temperature-dependent
  measurements and `ln_x2` targets.
- **Bradley melting points** — broad melting-point coverage used to populate
  `T_m`.
- **Curated NIST values** — manually curated physical-property overrides and
  reference values used for melting point and fusion-property enrichment.
- **Hansen parameters** — solute Hansen descriptors (`hansen_d`,
  `hansen_p`, `hansen_h`).
- **IDAC** — infinite-dilution activity coefficient data (`ln_gamma_inf`).

The merged dataset is built with `DataBuilder` and then split with
`scaffold_split()`.

## CLI Usage

The notebook-equivalent CLI is:

```bash
python scripts/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42
```

All arguments:

```bash
python scripts/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42 \
    --train-ratio 0.8 \
    --val-ratio 0.1 \
    --test-ratio 0.1
```

If the raw files are already present and you want to disable download attempts:

```bash
python scripts/prepare_data.py \
    --output-dir notebooks/data/processed \
    --skip-download
```

`--skip-download` expects the raw directory to live next to the processed
directory, for example:

- processed: `notebooks/data/processed`
- raw: `notebooks/data/raw`

## What the Script Does

`scripts/prepare_data.py` reproduces the same sequence as
`notebooks/01_prepare_data.ipynb`:

1. Load BigSolDBv2.1.
2. Filter records for SLE compatibility with `filter_for_sle(x2_max=0.98)`.
3. Load auxiliary sources: melting points, fusion enthalpies, Hansen data,
   and IDAC.
4. Merge everything with `DataBuilder`.
5. Split the unified dataframe with `scaffold_split`.
6. Save all canonical split families:
   - `train.csv`, `val.csv`, `test.csv`
   - `train_solute.csv`, `val_solute.csv`, `test_solute.csv`
   - `train_solvent.csv`, `val_solvent.csv`, `test_solvent.csv`
7. Save `split_manifest.json` with metadata for all generated split variants.
8. Print final statistics for split sizes, unique solutes and solvents, and
   auxiliary-label coverage.

## CSV Format

Processed CSV files are written to:

- `notebooks/data/processed/train.csv`
- `notebooks/data/processed/val.csv`
- `notebooks/data/processed/test.csv`

The same run also saves:

- `notebooks/data/processed/train_solute.csv`
- `notebooks/data/processed/val_solute.csv`
- `notebooks/data/processed/test_solute.csv`
- `notebooks/data/processed/train_solvent.csv`
- `notebooks/data/processed/val_solvent.csv`
- `notebooks/data/processed/test_solvent.csv`
- `notebooks/data/processed/split_manifest.json`

Required columns:

- `solute_smiles`
- `solvent_smiles`
- `temperature`
- `ln_x2`

Common optional columns used by TGNN-Solv:

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

## Split Modes

The split logic is implemented in `src/tgnn_solv/data/split.py`.

Available modes:

- `solute_scaffold`
  - Default mode.
  - Groups rows by the Murcko scaffold of the solute.
  - Best choice for scaffold generalization experiments.
- `solute`
  - Groups rows by exact solute SMILES.
  - Useful for comparison against prior work that used random-by-solute splits.
- `solvent`
  - Groups rows by solvent SMILES.
  - Prevents solvent overlap between splits.

All modes use greedy bin-packing to keep split sizes close to the target
ratios while preserving group integrity.

## Fair Comparison Guidance

When comparing TGNN-Solv against baselines or prior papers:

- report `solute_scaffold` as the strict generalization result;
- report `solute` when the comparison target did not use scaffold holdout;
- use `scripts/run_split_comparisons.py` for a consistent multi-seed comparison
  across all split protocols.
