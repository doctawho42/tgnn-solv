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
  - by default the repository falls back to a tiny built-in curated table
  - for real supervision, use the published Zenodo starter files or place a
    local `idac.csv` under `notebooks/data/raw/`
  - you can also set `TGNN_SOLV_IDAC_PATH=/abs/path/to/idac.csv`

The merged dataframe is built by `DataBuilder` and then split with the helpers
in `split.py` and `split_registry.py`.

## Canonical CLI

```bash
python scripts/data/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42
```

Useful flags:

```bash
python scripts/data/prepare_data.py \
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

Water-solubility supervision is now enabled by default for the canonical
corpus. The SLE filter still enforces `min_atoms=2` for general solvents, but
it keeps solvent-side water (`O`) so that measured aqueous `ln_x2` rows remain
in the supervised subset. To reproduce the legacy corpus without supervised
water rows, use either:

```bash
python scripts/data/prepare_data.py --no-include-water-solubility
```

or set the YAML config field:

```yaml
include_water_solubility: false
```

## What the Script Does

`scripts/data/prepare_data.py` performs the same high-level workflow as
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

When those processed splits are later frozen for an article-facing benchmark
release, the release builder also records checksums and provenance metadata so
that external comparisons can prove they used the same data bundle.

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

## Adding Real IDAC Data

`load_idac()` first looks for a local file before falling back to the built-in
demo table. Supported file locations:

- `notebooks/data/raw/idac.csv`
- `notebooks/data/raw/idac.tsv`
- `notebooks/data/raw/idac_gamma_inf.csv`
- `notebooks/data/raw/gamma_inf.csv`
- `TGNN_SOLV_IDAC_PATH=/abs/path/to/file`

The repository now also ships a small maintained starter corpus:

- `notebooks/data/raw/idac.csv`
- `notebooks/data/raw/idac_seed_dois.txt`

Canonical public copies of the same starter release are published on Zenodo:

- [`idac.csv`](https://zenodo.org/records/19484205/files/idac.csv)
- [`idac_seed_dois.txt`](https://zenodo.org/records/19484205/files/idac_seed_dois.txt)
- record page: [`Zenodo 19484205`](https://zenodo.org/records/19484205)

Current starter-corpus stats:

- `404` rows
- `138` unique `(solute, solvent)` pairs
- `9` ThermoML DOI sources
- temperature range `298.0 .. 438.0 K`
- `ln_gamma_inf` range `-1.386 .. 7.185`

This file is intentionally external to the main solubility corpus. It should be
read as a bootstrap `IDAC` source, not as evidence that `BigSolDB` itself
already contains matched `gamma_inf` supervision.

If you want to refresh the local copies from the published release, use:

```bash
curl -L https://zenodo.org/records/19484205/files/idac.csv \
    -o notebooks/data/raw/idac.csv
curl -L https://zenodo.org/records/19484205/files/idac_seed_dois.txt \
    -o notebooks/data/raw/idac_seed_dois.txt
```

Required logical columns:

- solute SMILES
  - aliases such as `solute_smiles`, `smiles_solute`, `solute`
- solvent SMILES
  - aliases such as `solvent_smiles`, `smiles_solvent`, `solvent`
- `ln_gamma_inf`
  - aliases such as `ln_gamma_inf`, `gamma_inf`, `log_gamma_inf`
  - values must already be in log-space; the loader does not apply `log()`

Optional:

- temperature
  - aliases such as `temperature`, `temperature_k`, `temp`, `t`
  - if omitted, `298.15 K` is assumed

After placing the file, rebuild processed splits:

```bash
python scripts/data/prepare_data.py --output-dir notebooks/data/processed
```

The CLI already prints `gamma_inf` counts for the unified dataframe and for
each split. A non-zero count there means `has_gamma_inf` is now active.

`gamma_inf` rows do not need an exact overlap with the solubility corpus
anymore. During dataset build they can also appear as `aux_only_gamma`
records, which enables standalone supervision of the `ln_gamma_inf` head in
Phase 1 / auxiliary training.

The practical implication is important: a dedicated external `IDAC` corpus is
now useful even when its `(solute, solvent, T)` tuples do not coincide with
existing `ln(x2)` rows. The previous matched-pair-only bottleneck no longer
applies.

If you need to build `idac.csv` yourself from NIST ThermoML JSON pages, use:

```bash
python scripts/data/extract_idac_from_thermoml.py \
    --doi-file notebooks/data/raw/idac_seed_dois.txt \
    --output notebooks/data/raw/idac.csv
```

This helper:

- fetches ThermoML `JSON` from `trc.nist.gov`
- extracts only binary `Activity coefficient` measurements at infinite dilution
- converts `gamma_inf` to `ln_gamma_inf`
- derives SMILES from the standard InChI using RDKit
- can be used to recreate or extend the published Zenodo starter release

You can also pass `--doi-file path/to/dois.txt` or parse a local directory of
ThermoML JSON files with `--json-dir path/to/json_archive`.

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
  - `scripts/training/train.py` fits `gc_prior_tm_scale` and `gc_prior_tm_bias` on the
    training split only when `use_gc_priors_crystal=True`
- DirectGNN descriptor normalization
  - `scripts/training/train_directgnn.py` computes descriptor mean/std on the training
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

The maintained article benchmark uses:

- `solute_scaffold`
  - strict molecular generalization
  - the default split mode for benchmark-release manifests

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
- use `scripts/experiments/run_split_comparisons.py` to avoid accidental split drift
- use `scripts/experiments/build_benchmark_release.py` when freezing a
  benchmark bundle for paper, external baselines, or adapter-based custom
  models

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

## Reproducibility Notes

The project now treats processed splits as first-class artifacts rather than
just intermediate CSVs. In practice this means:

- the training and evaluation stack expects the canonical processed contract
  under `notebooks/data/processed/`
- benchmark bundles can record the exact split files and hashes they used
- custom-model adapters are expected to benchmark against the same CSV schema
  instead of inventing a parallel input format

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Quick Start Workflow](getting_started/quick_start.md)
- [Training](training.md)
- [Evaluation & Inference](evaluation.md)
- [Experiments & Benchmarks](experiments.md)

</div>
