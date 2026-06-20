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
- open crystal sidecar artifact
  - reproducible `ThermoML + curated + Bradley` consolidation with explicit
    source priority under `results/open_crystal_artifact/`
- open finite-composition activity sidecar artifact
  - reproducible ThermoML extraction of finite-composition direct-activity and
    excess-mixing signals under `results/thermoml_activity/`
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

Keeping water in the supervised corpus does not by itself change the graph
representation. The default graph builder remains backward-compatible:
single-heavy-atom molecules such as water are represented as one node with a
self-loop. For water/small-solvent representation ablations, use the opt-in
featurizer flags:

```yaml
explicit_h_small_molecules: true
explicit_h_max_heavy_atoms: 3
```

With these flags, water (`O`) becomes a 3-node graph with directed O-H edges.
This is especially relevant for TIMP runs, because the polar/physical edge
channels otherwise receive no real O-H edge on water. The current CPU audit is:

```bash
python scripts/analysis/audit_water_small_molecule_graphs.py \
    --processed-dir notebooks/data/processed \
    --prediction-dir results/prediction_error_slices_latest \
    --out-dir results/water_small_molecule_audit
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

You can also pass `--doi-file path/to/dois.txt`, parse a local directory of
ThermoML JSON files with `--json-dir path/to/json_archive`, or discover DOI
records directly from official NIST ThermoML archive pages:

```bash
python scripts/data/extract_idac_from_thermoml.py \
    --nist-current-archive-pages \
    --save-json-dir notebooks/data/raw/thermoml_json \
    --output notebooks/data/raw/idac_from_current_nist_pages.csv \
    --audit-output results/idac_thermoml/audit_current_pages.json
```

For broader crawls, the helper can reproduce the NIST issue-dropdown logic and
expand a journal page into all indexed issue pages:

```bash
python scripts/data/extract_idac_from_thermoml.py \
    --nist-current-archive-pages \
    --expand-journal-issues \
    --journal jced \
    --year-min 2015 \
    --year-max 2019 \
    --save-json-dir notebooks/data/raw/thermoml_json \
    --output notebooks/data/raw/idac_jced_2015_2019.csv \
    --doi-output results/idac_thermoml/jced_2015_2019_dois.txt \
    --audit-output results/idac_thermoml/jced_2015_2019_audit.json
```

Use `--max-archive-pages` or `--max-dois` for smoke tests before a full crawl.
The script records per-DOI extraction counts and failures in the audit JSON so
large jobs are restartable and debuggable.

After a broad crawl, keep the original starter `idac.csv` intact and create an
explicit expanded artifact:

```bash
python scripts/analysis/audit_idac_expansion.py \
    --starter-idac notebooks/data/raw/idac.csv \
    --extracted-idac notebooks/data/raw/idac_nist_2015_2019.csv \
    --raw-output notebooks/data/raw/idac_expanded_raw.csv \
    --training-output notebooks/data/raw/idac_expanded.csv \
    --out-dir results/idac_expansion_audit
```

For fair model comparisons, do not add the expanded aux-only IDAC rows before
running the scaffold split. That changes the supervised validation/test
composition. Instead, attach new `gamma_inf` rows to the training split only
while preserving the existing supervised rows:

```bash
python scripts/data/attach_idac_aux_to_fixed_splits.py \
    --processed-dir notebooks/data/processed \
    --idac-csv notebooks/data/raw/idac_expanded.csv \
    --output-dir notebooks/data/processed_idac_expanded_train_aux
```

Use `notebooks/data/processed_idac_expanded_train_aux` for controlled IDAC
ablation runs. A separately prepared `processed_idac_expanded` bundle is only a
protocol-shift diagnostic unless its supervised split composition is explicitly
accepted.

## Open Crystal Data Path

The repository now also keeps the open pure-component crystal-data path as a
separate reproducible contour rather than silently folding it into the
canonical `prepare_data.py` output.

Step 1: extract pure-component `T_m` / `dH_fus` from local or fetched ThermoML
JSON:

```bash
python scripts/data/extract_crystal_from_thermoml.py \
    --json-dir notebooks/data/raw/thermoml_json \
    --output-raw results/thermoml_crystal/thermoml_crystal_measurements.csv \
    --output-aggregated results/thermoml_crystal/thermoml_crystal_aggregated.csv \
    --audit-output results/thermoml_crystal/summary.json
```

This writes:

- per-measurement ThermoML rows with DOI/method/phase provenance
- an aggregated solute-level ThermoML artifact
- a summary JSON with row, DOI, and solute counts

On the current maintained local ThermoML cache (`3721` JSON files), this path
produces:

- `1679` raw crystal measurements
- `701` aggregated solutes with `T_m`
- `473` aggregated solutes with `dH_fus`
- `473` aggregated solutes with both `T_m` and `dH_fus`

Step 2: merge ThermoML with the existing open crystal sources and record
explicit source priority:

```bash
python scripts/data/build_open_crystal_artifact.py \
    --thermoml-aggregated results/thermoml_crystal/thermoml_crystal_aggregated.csv \
    --processed-dir notebooks/data/processed \
    --out-dir results/open_crystal_artifact
```

The current priority order is:

- `T_m`: `curated_nist_webbook > thermoml > bradley`
- `dH_fus`: `curated_nist_webbook > thermoml`

This builder writes:

- `results/open_crystal_artifact/open_crystal_solute.csv`
  - one solute-level artifact with source-level columns and selected values
- `results/open_crystal_artifact/coverage_by_split.csv`
  - overlap and gain versus the canonical processed splits
- `results/open_crystal_artifact/pairwise_source_agreement.csv`
  - source-overlap delta audit
- `results/open_crystal_artifact/summary.json`
- `results/open_crystal_artifact/summary.md`

Current artifact stats:

- final `T_m` coverage: `19,436` solutes
- final `dH_fus` coverage: `495` solutes
- final joint `T_m + dH_fus` coverage: `495` solutes

Current gain relative to the canonical supervised scaffold split contract:

- train joint-label rows: `1080 -> 14401`
- val joint-label rows: `0 -> 288`
- test joint-label rows: `0 -> 221`
- full supervised joint-label rows: `1080 -> 14910`
- full supervised unique `(solute, solvent)` pairs with both labels:
  `146 -> 1497`

The conflict audit matters. Current overlaps show:

- curated `T_m` vs ThermoML `T_m`
  - `13` overlaps, median absolute delta `0.275 K`
- ThermoML `T_m` vs Bradley `T_m`
  - `307` overlaps, median absolute delta `273.45 K`
- curated `dH_fus` vs ThermoML `dH_fus`
  - `9` overlaps, median absolute delta `930 J/mol`

Interpretation:

- curated values are close enough to stay highest priority
- ThermoML is useful and broadly expands `dH_fus`
- Bradley remains valuable for broad `T_m` coverage, but should stay
  lowest-priority because its overlaps with ThermoML are often large

This open crystal contour is intentionally a sidecar today. It is not wired
into the canonical `prepare_data.py` output by default yet, because the
expanded crystal path still needs explicit downstream protocol decisions
(for example whether to regenerate the maintained processed splits or keep the
open artifact as a separate diagnostic resource first).

## Open Finite-Composition Activity Path

The repository now also keeps the next missing activity-side data contour as a
separate reproducible artifact rather than mixing it silently into the
canonical SLE corpus.

This path intentionally excludes infinite-dilution `Activity coefficient`
rows, because those already belong to the maintained ThermoML `IDAC` route.
Its purpose is different: collect finite-composition pair-level signals that do
not pass through the crystal term.

Build the ThermoML activity artifact from the local JSON cache:

```bash
python scripts/data/extract_activity_from_thermoml.py \
    --json-dir notebooks/data/raw/thermoml_json \
    --processed-dir notebooks/data/processed \
    --output-raw results/thermoml_activity/thermoml_activity_measurements.csv \
    --output-aggregated results/thermoml_activity/thermoml_activity_aggregated.csv \
    --audit-output results/thermoml_activity/summary.json \
    --summary-md results/thermoml_activity/SUMMARY.md \
    --parse-audit-csv results/thermoml_activity/parse_audit.csv
```

This writes:

- `thermoml_activity_measurements.csv`
  - raw per-measurement rows with DOI/method/phase/standard-state provenance
- `thermoml_activity_aggregated.csv`
  - exact-state aggregated rows keyed by pair, targeted component,
    composition, temperature, and pressure
- `summary.json` / `SUMMARY.md`
  - property counts, composition-basis counts, temperature-span summaries, and
    overlap against the canonical scaffold SLE splits
- `parse_audit.csv`
  - one parse row per cached ThermoML JSON file

On the current maintained ThermoML cache (`3721` JSON files), this activity
path produces:

- `8821` raw rows
- `8683` aggregated exact-state rows
- `102` DOI sources
- `295` unordered binary pairs
- `109` targeted direct-activity pairs

Current property breakdown:

- `3491` direct finite-composition activity rows
  - `345` `Activity coefficient`
  - `3146` `(Relative) activity`
- `5192` excess-mixing rows
  - `Excess molar enthalpy (molar enthalpy of mixing)`

Current composition basis breakdown:

- `6376` `mole_fraction`
- `2249` `molality_mol_per_kg`
- `58` `mass_fraction`

Current wide-composition direct-activity subset:

- mole-fraction `>= 0.10`: `1161` rows across `27` targeted pairs
- mole-fraction `>= 0.20`: `1087` rows across `25` targeted pairs

Current temperature-span summary:

- direct `Activity coefficient`
  - `11` targeted groups, `4` with span `>= 20 K`, max span `60 K`
- direct `(Relative) activity`
  - `98` targeted groups, `35` with span `>= 20 K`, max span `273.3 K`
- excess enthalpy
  - `196` pair groups, `63` with span `>= 20 K`, max span `380 K`

The overlap audit is the key scientific limitation:

- unordered overlap with the canonical supervised scaffold corpus:
  - only `6` train pairs, `0` val pairs, `0` test pairs
- direct target-as-solute overlap:
  - `0` train, `0` val, `0` test
- direct target-as-solvent overlap:
  - `6` train pairs, `0` val, `0` test
- direct target components in the extracted ThermoML contour:
  - only `7` unique components total
  - `0` of them appear as SLE solutes
  - `4` of them appear as SLE solvents

Interpretation:

- ThermoML already contains a real open finite-composition activity contour
- that contour is large enough to justify dedicated extractors and future
  auxiliary objectives
- but on the current maintained scaffold benchmark it does not yet break the
  compensation bottleneck on the same pairs, because its exact overlap is tiny
  and all current exact overlaps supervise the solvent side rather than the
  dissolved solute

This activity contour is therefore a sidecar today, like the open crystal
artifact. It is a data asset and protocol input for the next supervision path,
not a silent change to `prepare_data.py` or to the maintained benchmark split
contract.

For targeted data collection, use the exact-pair coverage collector:

```bash
python scripts/data/collect_targeted_thermoml_coverage.py \
    --processed-dir notebooks/data/processed \
    --json-dir notebooks/data/raw/thermoml_json \
    --out-dir results/thermoml_targeted_coverage
```

This writes:

- `thermoml_binary_pair_matches.csv`
  - raw exact unordered binary ThermoML matches against canonical SLE pairs
- `sle_pair_matches.csv`
  - the same matches expanded to directed `solute -> solvent` SLE pairs with
    `property_target_role`
- `thermoml_targeted_measurements.csv`
  - raw measurement-level harvest for exact-matched binary pairs with
    DOI/method/phase/standard-state/state-variable provenance
- `thermoml_targeted_measurements_aggregated.csv`
  - exact-state aggregation of the same measurement rows
- `sle_targeted_measurements_aggregated.csv`
  - exact-state aggregates expanded to directed SLE pairs
- `candidate_sle_targeted_measurements_aggregated.csv`
  - measurement-backed candidate-family exact states only
- `coverage_by_split.csv`, `coverage_by_family.csv`, `coverage_by_property.csv`
  - exact-pair coverage summaries by split and ThermoML property family
- `candidate_covered_sle_pairs.csv`
  - directed SLE pairs with at least one activity-signal candidate family
    (`direct_activity`, `solution_thermo`, `excess_thermo`, `vle_like`)
- `candidate_missing_sle_pairs.csv`
  - the complementary gap list for targeted ThermoML expansion
- `candidate_measurement_covered_sle_pairs.csv`
  - directed SLE pairs with at least one usable candidate-family measurement
- `candidate_measurement_missing_sle_pairs.csv`
  - the stricter measurement-backed gap list for targeted collection

On the current maintained local cache (`3721` JSON files), the key result is
more specific than the earlier direct-activity audit:

- generic exact binary ThermoML overlap exists for `2353 / 12129` maintained
  SLE pairs (`2029` train, `151` val, `173` test)
- the exact-pair harvest now contains the actual numeric data:
  - `30,903` raw measurement rows
  - `30,336` exact-state aggregates
- but activity-signal candidate coverage remains tiny:
  - property-level candidate overlap: `14` train, `0` val, `2` test
  - measurement-backed candidate overlap: `13` train, `0` val, `2` test
  - candidate-family exact-state aggregates: `698`
- direct finite-composition activity remains solvent-targeted only:
  - `7` train pairs
  - `0` direct target-as-solute pairs
- exact `H^E` overlap remains `0`
- one apparent extra train `Activity coefficient` pair is IDAC-like and is
  filtered out of the measurement-backed artifact, so the measurement-backed
  gap list is intentionally stricter than the property-label view

This is the maintained artifact for the next collection step because it turns
the problem from “find more ThermoML” into “close the candidate-family gap on
these exact missing SLE pairs.”

As a synthetic exact-pair expansion path, the repository now also supports
finite-composition Modified-UNIFAC pseudo coverage on the same SLE pairs:

```bash
python scripts/data/build_unifac_finite_activity_coverage.py \
    --processed-dir notebooks/data/processed \
    --out-dir results/unifac_finite_activity_coverage
```

By default this targets
`results/thermoml_targeted_coverage/candidate_measurement_missing_sle_pairs.csv`
and evaluates a dilute composition grid (`0.01,0.02,0.05,0.10,0.20`) at one
representative median temperature per missing directed pair.

This writes:

- `unifac_finite_activity_pseudo.csv`
  - finite-composition pseudo activity rows with `ln(gamma)` on the selected
    composition grid
- `pair_status.csv`
  - one row per directed pair with group-availability status
- `missing_pairs.csv`
  - the remaining uncovered pairs after the UNIFAC check
- `evaluation_failures.csv`
  - any states where group assignments existed but UNIFAC still failed
- `coverage_by_split.csv`, `summary.json`, `SUMMARY.md`
  - pair/state coverage summaries for the synthetic path

On the current maintained gap set, this synthetic path covers:

- `2756 / 12114` missing directed pairs (`22.75%`)
- `25180 / 108148` observed pair-temperature states on those missing pairs
  (`23.28%`) when expanded back to the full source temperatures
- split-wise pair coverage:
  - train: `2648 / 10547` (`25.11%`)
  - val: `50 / 746` (`6.70%`)
  - test: `58 / 821` (`7.06%`)

The main remaining blocker is not numerical failure inside UNIFAC but missing
group assignments:

- `9297` pairs are missing solute groups
- `14` pairs are missing solvent groups
- `47` pairs are missing both
- `0` ready pairs failed during finite-composition evaluation

This makes the next synthetic-data question concrete: whether it is worth
adding broader fragment/group coverage or a COSMO-style fallback for the
remaining `~77%` of measurement-backed exact-pair gaps.

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
