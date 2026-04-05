# Results

This page explains how to read the benchmark artifacts that currently live in
the repository, which bundles are canonical, and which ones should still be
treated as provisional diagnostics rather than final scientific claims.

## Read This First

The repo contains several different classes of results:

- structured reproduction summaries
- quick checkpoint evaluations
- canonical benchmark bundles
- proxy-budget diagnostic experiments
- split-comparison outputs
- medium-budget and full-budget benchmark runners
- targeted research probes, such as descriptor-recovery analyses

Do not compare numbers across different sections unless the following are
matched:

- split protocol
- training budget
- seed count
- feature path
- model family

For this project, the strict default split is `solute_scaffold`.

## Recommended Benchmark Hierarchy

When reporting results from TGNN-Solv, prefer this order of evidence:

1. full scaffold split over proxy subsets
2. matched training budgets across TGNN and DirectGNN
3. multi-seed aggregates over single-seed runs
4. metric bundles that include both top-line error and TGNN bottleneck
   diagnostics

That is why the maintained benchmark pages focus on:

- `scripts/experiments/reproduce_paper.py --profile article`
- `scripts/experiments/run_medium_budget_comparison.py`
- `scripts/experiments/run_full_budget_experiment.py`
- `scripts/experiments/run_split_comparisons.py`
- `scripts/experiments/run_external_baseline_benchmark.py`

## Canonical Artifact Contract

The project now relies on one shared benchmark artifact format for maintained
external baselines and custom models:

- `summary.csv`
- `report.json`
- `predictions.csv`
- `run_manifest.json`
- `benchmark_card.json`

This is what powers:

- `Results & Plots -> Benchmark Studio` in the lab
- artifact registry and diff views
- supplementary external-benchmark tables

If a benchmark bundle does not follow that contract, treat it as ad hoc output
rather than a first-class comparable result.

The sidecars matter because they carry:

- file-level provenance and checksums
- split / model-family metadata
- capability flags such as uncertainty availability
- machine-readable inputs for `Benchmark Studio`, lineage, and release freezing

## Reproduction Summaries

Structured paper-reproduction runs now write:

- `results/reproduction/core_summary.json`
- `results/reproduction/article_summary.json`
- `results/reproduction/full_summary.json`

These are orchestration summaries, not benchmark claims by themselves. Their
purpose is to record:

- which maintained profile was used
- which steps completed, failed, or were skipped
- where the resulting benchmark and figure artifacts landed

## Committed Diagnostic / Proxy Results

The checked-in result bundles under `results/` are mostly diagnostic or
research-stage outputs. They are useful for understanding failure modes, but
they should not be treated as the repository's final benchmark claims.

### Proxy diagnostic comparison

Source artifacts:

- `results/diagnostic_experiments/summary.json`
- `results/diagnostic_experiments/comparison_table.md`

Representative proxy numbers currently committed:

| Experiment | Test MAE | Notes |
| --- | ---: | --- |
| TGNN tuned proxy | `2.2275` | reference proxy checkpoint |
| TGNN tuned proxy with oracle `T_m` substitution | `2.2133` | only a small improvement on this proxy slice |
| DirectGNN + descriptors proxy | `2.0110` | strongest committed proxy result in this bundle |
| TGNN combined proxy | `5.9603` | clearly unstable / underperforming in this diagnostic run |

Important caveat:

- this bundle was run on a small proxy setup, not the maintained full-scaffold
  architecture-comparison budget

### Descriptor-prior medium scaffold diagnostic

Source artifact:

- `results/descriptor_prior_medium_scaffold.json`

Currently committed numbers:

| Model | MAE | RMSE | R² |
| --- | ---: | ---: | ---: |
| `tgnn_medium` | `2.2561` | `3.0619` | `-0.1660` |
| `tgnn_priors_medium` | `2.2614` | `3.0674` | `-0.1702` |
| `direct_gnn_medium` | `2.0692` | `2.8540` | `-0.0130` |

Interpretation:

- these are medium-sized diagnostic runs on a specific scaffold slice
- they are useful for trend inspection, not as the primary benchmark table for
  the project site

## Maintained Architecture Comparison Bundles

### Medium-budget architecture study

The main in-repo architecture-comparison target is the full-scaffold
medium-budget run under:

- `results/medium_budget/`

At the moment, the repository contains the in-progress TGNN artifact layout:

- `results/medium_budget/per_model/tgnn_tuned/checkpoint.pt`
- `results/medium_budget/per_model/tgnn_tuned/train.log`

The runner is designed to produce:

- `results/medium_budget/summary.json`
- `results/medium_budget/comparison_table.md`
- `results/medium_budget/per_model/<model>/...`

That is the benchmark bundle the site should treat as the main in-repo
architecture comparison once complete.

Recent follow-up lanes derived from the same scaffold split and budget include:

- regularized TGNN variants
- TGNN with descriptor augmentation
- TGNN with the GPS encoder
- Stage 0 pretrained TGNN variants

Those runs should be treated as queued / follow-up comparison tracks until
their own summaries land under `results/`.

### External article-comparison bundle

The maintained external competitor bundle now lives under:

- `results/external_baselines/article_benchmark/`

This is where FastSolv and native-retrained SolProp land when they are run
through the shared orchestrator. Once present, this bundle should be compared
against the in-repo model families through:

- `Results & Plots -> Benchmark Studio`
- supplementary `Table S10`
- checksum-based benchmark release manifests built from those bundles

### Custom benchmark bundles

Arbitrary user-provided model predictions should land under:

- `results/custom_benchmarks/<model_name>/`

They use the same canonical bundle contract and are therefore intentionally
comparable to maintained model families inside the GUI.

If the custom model is implemented through the adapter API instead of a raw
CSV, the bundle also captures that fact in its benchmark card.

## Frozen Release Manifests

When a benchmark snapshot should become paper-facing rather than just
locally inspectable, freeze it with:

```bash
python scripts/experiments/build_benchmark_release.py \
    --release-name article-benchmark \
    --version 0.1.0 \
    --processed-dir notebooks/data/processed \
    --bundle-root results/external_baselines/article_benchmark \
    --bundle-root results/custom_benchmarks \
    --out-dir results/releases/article_benchmark_v0_1_0
```

The produced `release_manifest.json` records checksums for:

- processed split CSVs
- `split_manifest.json`
- benchmark bundles and their sidecars
- optional checkpoints included in the release

## Experiment Lab Histories

The interactive `Experiment Lab` writes additional repo-local analysis history
under:

- `results/lab_runs/inference_history/`
- `results/lab_runs/uncertainty_history/`
- `results/lab_runs/calibration_history/`

These JSON artifacts are not benchmark claims by themselves. They are review
artifacts used for:

- saved single-system case studies
- ensemble vs MC-dropout uncertainty comparison
- batch calibration sessions
- lineage tracing back to checkpoints and datasets
- planner and pipeline follow-up intake inside the GUI

## Descriptor-Recovery Probe

One recent diagnostic probe asks whether the solute graph embedding already
linearly recovers standard RDKit descriptors.

Source artifact:

- `results/medium_budget/per_model/tgnn_tuned/descriptor_probe/summary.json`

Summary from the current probe:

- unique train solutes: `14997`
- unique test solutes: `2352`
- finite descriptor `R²`: `208 / 217`
- `R² >= 0.8`: `3 / 208`
- median descriptor `R²`: `0.505`

Representative descriptor recovery:

| Descriptor | Test R² |
| --- | ---: |
| `FractionCSP3` | `0.926` |
| `TPSA` | `0.650` |
| `NumHDonors` | `0.693` |
| `MolLogP` | `0.607` |
| `MolWt` | `0.450` |

Interpretation:

- the encoder clearly learns some chemically meaningful structure
- but it does not look "descriptor-complete" yet
- this supports treating encoder capacity as at least a partial bottleneck

## What To Report Publicly

For a paper, slide deck, or benchmark summary page, the safest reporting policy
is:

- use `solute_scaffold` as the primary split
- use matched budgets for TGNN and DirectGNN
- report seed aggregates when available
- include both:
  - solubility metrics such as MAE / RMSE / `R²`
  - TGNN bottleneck metrics such as `T_m` parity and oracle sensitivity

## Which Artifact Should I Trust?

| Question | Best artifact |
| --- | --- |
| "Does this one checkpoint work?" | `evaluate_complete.py` output |
| "How does TGNN compare with DirectGNN on a serious budget?" | `results/medium_budget/*` or `results/full_budget_experiment/*` |
| "How do FastSolv / SolProp compare on the same split?" | `results/external_baselines/article_benchmark/*` |
| "How does my custom model compare against maintained baselines?" | `results/custom_benchmarks/<name>/*` |
| "Are the physics intermediates sensible?" | `validate_physics.py` output or full-budget diagnostics |
| "Did the solute encoder learn chemistry or just fit the task?" | descriptor-recovery probe under `results/medium_budget/per_model/.../descriptor_probe/` |

## Related Pages

- [Experiments & Benchmarks](experiments.md)
- [Experiment Lab](experiment_lab.md)
- [Baselines](baselines.md)
- [Model Zoo](model_zoo.md)
- [Config Cookbook](config_cookbook.md)
