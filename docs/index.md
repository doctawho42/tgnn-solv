<div class="tgnn-hero" markdown="1">

<div class="tgnn-hero__eyebrow">Physics-Informed Solubility Modeling</div>

# TGNN-Solv

Physics-informed graph learning for solid-liquid equilibrium solubility
prediction.

TGNN-Solv does not predict solubility directly by default. It predicts crystal
and interaction parameters, solves the SLE equation with a default NRTL
activity model, and only then applies a bounded correction. The central
question across this repository is whether that explicit thermodynamic
bottleneck helps
relative to the same graph backbone trained directly on `ln(x2)`.

<div class="tgnn-button-row" markdown="1">

[Install TGNN-Solv](getting_started/installation.md){ .md-button .md-button--primary }
[Run the quick start](getting_started/quick_start.md){ .md-button }
[Open Experiment Lab](experiment_lab.md){ .md-button }
[Browse the notebooks](notebooks.md){ .md-button }
[See benchmark workflows](experiments.md){ .md-button }

</div>

<div class="tgnn-chip-list">
  <span class="tgnn-chip">Default strict split: <code>solute_scaffold</code></span>
  <span class="tgnn-chip">Maintained TGNN baseline: <code>paper_config_tuned.yaml</code></span>
  <span class="tgnn-chip">Encoder options: <code>mpnn</code>, <code>gps</code>, or <code>timp</code></span>
  <span class="tgnn-chip">Optional TGNN descriptor augmentation available</span>
  <span class="tgnn-chip">TIMP and Hansen-contrastive variants available</span>
  <span class="tgnn-chip">Matched no-physics baseline: <code>DirectGNN</code></span>
  <span class="tgnn-chip">Structured reproduction: <code>core</code> / <code>article</code> / <code>full</code></span>
  <span class="tgnn-chip">Optional Stage 0 pretraining supported</span>
  <span class="tgnn-chip">Water supervision kept by default</span>
  <span class="tgnn-chip">Resume-safe training supported</span>
  <span class="tgnn-chip">Interactive Experiment Lab available</span>
</div>

</div>

## Site Overview

<div class="tgnn-grid tgnn-grid--3" markdown="1">

<div class="tgnn-card tgnn-card--accent" markdown="1">

### Core models

The maintained comparison is:

- `TGNN-Solv`
- `TGNN-Solv + descriptors`
- `TGNN-Solv + GPS encoder`
- `TGNN-Solv + TIMP encoder`
- `TGNN-Solv + TIMP + Hansen contrastive`
- `TGNN-Solv + Stage 0 pretraining`
- `DirectGNN`
- `DirectGNN + descriptors`
- descriptor and Morgan RF baselines

</div>

<div class="tgnn-card" markdown="1">

### Practical workflows

This site documents the maintained paths for:

- data preparation
- training and resume support
- Stage 0 encoder warm starts and GPS / TIMP / descriptor-augmented TGNN variants
- inference, uncertainty, and OOD checks
- benchmark and experiment runners
- gradient-flow, TIMP-channel, sensitivity, and weight diagnostics
- external FastSolv / SolProp comparison
- solvent/process/preformulation application workflows
- `Benchmark Studio`, benchmark cards/manifests, and structured reproduction profiles

</div>

<div class="tgnn-card" markdown="1">

### Interactive tutorials

The repository includes notebook walkthroughs for:

- data preparation
- training
- inference
- evaluation
- baselines, ablations, temperature analysis, and tuning

</div>

</div>

## Research Question

The repository is organized around one high-level question:

> Does an explicit thermodynamic bottleneck help out-of-split solubility
> prediction relative to a matched graph backbone trained directly on
> `ln(x2)`?

That is why the site consistently presents TGNN-Solv together with:

- the matched no-physics `DirectGNN` baseline
- the descriptor-augmented `DirectGNN` variant
- RF descriptor baselines
- optional external baselines such as FastSolv and SolProp

## Choose a Path

=== "First Run"

    Start here if you want a working environment and one end-to-end example.

    - [Installation](getting_started/installation.md)
      - environment setup, dependencies, sanity checks
    - [Quick Start Workflow](getting_started/quick_start.md)
      - prepare data, train one tuned TGNN model, evaluate a checkpoint
    - [Notebooks & Tutorials](notebooks.md)
      - interactive walkthroughs aligned with the maintained code paths
    - [Troubleshooting](troubleshooting.md)
      - the fastest way to debug setup, device, or resume issues

=== "Benchmarking"

    Start here if you want fair comparisons and reproducible result bundles.

    - [Config Cookbook](config_cookbook.md)
      - pick the right config for TGNN, DirectGNN, or ablation work
    - [Results](results.md)
      - understand canonical benchmark bundles, reproduction outputs, and provisional artifacts
    - [Experiments & Benchmarks](experiments.md)
      - medium-budget, full-budget, split-comparison, external-baseline, and reproduction workflows
    - [Reproducing the Paper](reproducing_paper.md)
      - choose between `core`, `article`, and `full` maintained profiles
    - [Model Zoo](model_zoo.md)
      - checkpoint conventions and current public-model status

=== "Deep Dive"

    Start here if you want to understand the architecture and its failure modes.

    - [Architecture](architecture.md)
      - the TGNN forward path, DirectGNN, GC priors, and Stage 0 pretraining
    - [Training](training.md)
      - curriculum phases, pair-aware batching, auxiliary/contrastive losses, oracle injection, resume
    - [Evaluation & Inference](evaluation.md)
      - prediction APIs, uncertainty, calibration, and applicability domain
    - [Applications](applications.md)
      - solvent screening, process optimization, BCS/developability, and PK-relevant formulation use cases
    - [Experiment Lab](experiment_lab.md)
      - visual orchestration, DAGs, model editing, planner, lineage, docs, and Benchmark Studio
    - [Baselines](baselines.md)
      - what each baseline tests and how to run it
    - [FAQ](faq.md)
      - common conceptual and practical questions

=== "Contributing"

    Start here if you want to change code, docs, or experiment scripts.

    - [Script Reference](script_reference.md)
      - maturity map for scripts and notebooks
    - [Contributing](contributing.md)
      - contributor workflow and doc/update policy
    - [Repository Audit](repository_audit.md)
      - current strengths, caveats, and structural risks
    - [Free GPU / Preemptible Training](free_gpu_training.md)
      - resume-safe execution in cloud notebook environments

## Documentation Hub

<div class="tgnn-grid tgnn-grid--2" markdown="1">

<div class="tgnn-card tgnn-card--accent" markdown="1">

### Start Here

Use these pages to get from clone to first result:

- [Installation](getting_started/installation.md)
- [Quick Start Workflow](getting_started/quick_start.md)
- [Notebooks & Tutorials](notebooks.md)

</div>

<div class="tgnn-card" markdown="1">

### Guides

Use these pages to understand the maintained implementation:

- [Architecture](architecture.md)
- [Data Preparation](data_preparation.md)
- [Training](training.md)
- [Evaluation & Inference](evaluation.md)
- [Applications](applications.md)
  - solvent screening, process optimization, BCS-style developability, and PK solubility profiling
- [Experiment Lab](experiment_lab.md)
- [Baselines](baselines.md)
- [Config Cookbook](config_cookbook.md)

</div>

<div class="tgnn-card" markdown="1">

### Workflows

Use these pages to run benchmark and reproduction paths:

- [Results](results.md)
- [Experiments & Benchmarks](experiments.md)
- [Model Zoo](model_zoo.md)
- [Reproducing the Paper](reproducing_paper.md)
- [Free GPU / Preemptible Training](free_gpu_training.md)

</div>

<div class="tgnn-card" markdown="1">

### Reference and Project Notes

Use these pages when you need targeted answers:

- [Script Reference](script_reference.md)
- [FAQ](faq.md)
- [Troubleshooting](troubleshooting.md)
- [Repository Audit](repository_audit.md)
- [Contributing](contributing.md)

</div>

</div>

## Model Families

<div class="tgnn-grid tgnn-grid--2" markdown="1">

<div class="tgnn-card" markdown="1">

### `TGNN-Solv`

- predicts `T_m`, `dH_fus`, `dCp_fus`, and NRTL state
- solves the SLE equation explicitly
- applies a bounded correction only after the solver
- supports GC crystal priors, descriptor augmentation, GPS and TIMP encoder
  variants, a train-only auxiliary direct-solubility rescue head, and Stage 0
  warm starts

</div>

<div class="tgnn-card" markdown="1">

### `DirectGNN`

- reuses the same backbone and interaction stack
- predicts `ln(x2)` directly
- acts as the matched no-physics control
- has a stronger descriptor-augmented variant for baseline pressure testing

</div>

<div class="tgnn-card" markdown="1">

### Descriptor-augmented baselines

- `DirectGNN + descriptors`
- RF on descriptors
- RF on Morgan fingerprints
- RF hybrid features

Use these to test whether hand-crafted chemistry closes the gap without the
TGNN physics bottleneck.

</div>

<div class="tgnn-card" markdown="1">

### External baselines

- FastSolv
- SolProp

These remain optional and environment-sensitive, so they are documented
honestly as external comparison surfaces rather than core repo dependencies.

</div>

</div>

## Recommended Reading Sequences

<div class="tgnn-grid tgnn-grid--3" markdown="1">

<div class="tgnn-card" markdown="1">

### Learn the project

1. [Quick Start Workflow](getting_started/quick_start.md)
2. [Architecture](architecture.md)
3. [Training](training.md)
4. [Evaluation & Inference](evaluation.md)

</div>

<div class="tgnn-card" markdown="1">

### Run serious comparisons

1. [Config Cookbook](config_cookbook.md)
2. [Results](results.md)
3. [Experiments & Benchmarks](experiments.md)
4. [Reproducing the Paper](reproducing_paper.md)

</div>

<div class="tgnn-card" markdown="1">

### Work interactively

1. [Notebooks & Tutorials](notebooks.md)
2. `01_prepare_data.ipynb`
3. `02_train.ipynb`
4. `03_inference.ipynb`
5. `04_evaluation.ipynb`

</div>

</div>

## Notebook-First Readers

If you prefer to learn the repository through interactive walkthroughs, start
with:

1. [01_prepare_data.ipynb](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/01_prepare_data.ipynb)
2. [02_train.ipynb](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/02_train.ipynb)
3. [03_inference.ipynb](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/03_inference.ipynb)
4. [04_evaluation.ipynb](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/04_evaluation.ipynb)

The site pages and notebooks are intentionally aligned, so the conceptual
documentation and the runnable examples describe the same maintained surfaces.

<div class="tgnn-page-nav" markdown="1">

## Continue With

- New to the repo:
  [Installation](getting_started/installation.md) →
  [Quick Start Workflow](getting_started/quick_start.md)
- Choosing configs or runs:
  [Config Cookbook](config_cookbook.md) →
  [Experiments & Benchmarks](experiments.md)
- Need metrics and artifacts:
  [Results](results.md) →
  [Model Zoo](model_zoo.md)

</div>
