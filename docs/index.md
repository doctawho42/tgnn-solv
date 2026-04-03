# TGNN-Solv

Physics-informed graph learning for solid-liquid equilibrium solubility prediction.

[Install TGNN-Solv](getting_started/installation.md){ .md-button .md-button--primary }
[Run the quick start](getting_started/quick_start.md){ .md-button }
[Browse the notebooks](notebooks.md){ .md-button }

!!! abstract
    TGNN-Solv does not predict solubility directly by default. It predicts
    crystal and interaction parameters, solves the SLE equation with an NRTL
    activity model, and only then applies a bounded correction. The central
    comparison in this repository is whether that explicit physics bottleneck
    helps relative to the same backbone trained directly on `ln(x2)`.

## What This Site Covers

<div class="grid cards" markdown>

- :material-flask-outline: __Core models__

  ---

  The maintained comparison is:

  - `TGNN-Solv`
  - `DirectGNN`
  - `DirectGNN + descriptors`
  - descriptor and Morgan RF baselines

- :material-cog-outline: __Practical workflows__

  ---

  This site documents the maintained paths for:

  - data preparation
  - training and resume support
  - inference, uncertainty, and OOD checks
  - benchmark and experiment runners

- :material-notebook-outline: __Interactive tutorials__

  ---

  The repository includes notebook walkthroughs for:

  - data preparation
  - training
  - inference
  - evaluation
  - baselines, ablations, temperature analysis, and tuning

</div>

## Research Question

The project is organized around one high-level question:

> Does an explicit thermodynamic bottleneck help out-of-split solubility
> prediction relative to a matched graph backbone trained directly on
> `ln(x2)`?

That is why the site consistently presents TGNN-Solv together with:

- the matched no-physics `DirectGNN` baseline
- the descriptor-augmented `DirectGNN` variant
- RF descriptor baselines
- optional external baselines such as FastSolv and SolProp

## Start Here

<div class="grid cards" markdown>

- :material-download-outline: __Install__

  ---

  Set up the environment, PyTorch, and PyG.

  [Open installation guide](getting_started/installation.md)

- :material-rocket-launch-outline: __Quick start__

  ---

  Prepare the processed split, train one tuned TGNN model, run inference, and
  evaluate a checkpoint.

  [Open quick start](getting_started/quick_start.md)

- :material-graph-outline: __Understand the model__

  ---

  Read how TGNN-Solv factorizes crystal and interaction terms, how GC priors
  are injected, and where the solver sits in the forward pass.

  [Open architecture guide](architecture.md)

- :material-chart-box-outline: __Run experiments__

  ---

  Use the maintained experiment pages for medium-budget comparisons,
  full-budget diagnostics, split studies, and paper-style reproduction.

  [Open experiments guide](experiments.md)

</div>

## Model Families

| Model | What it predicts | Why it exists |
| --- | --- | --- |
| `TGNN-Solv` | `T_m`, `dH_fus`, `dCp_fus`, NRTL state, then `ln(x2)` through the solver | Main physics-informed model |
| `DirectGNN` | `ln(x2)` directly from the same graph backbone | Matched no-physics control |
| `DirectGNN + descriptors` | `ln(x2)` from graph features plus RDKit descriptors | Tests whether missing hand-crafted chemistry explains the gap |
| `RF` baselines | `ln(x2)` from descriptors, Morgan fingerprints, or both | Cheap descriptor-centric baselines |

## Documentation Map

- [Installation](getting_started/installation.md)
  - environment setup and dependency notes
- [Quick Start Workflow](getting_started/quick_start.md)
  - the shortest maintained path from raw repo to first trained model
- [Notebooks & Tutorials](notebooks.md)
  - interactive walkthroughs and how they map to the codebase
- [Architecture](architecture.md)
  - forward path, GC priors, Stage 0 pretraining, and DirectGNN
- [Training](training.md)
  - curriculum, resume support, pretraining, and training controls
- [Evaluation & Inference](evaluation.md)
  - prediction APIs, uncertainty, calibration, and applicability-domain checks
- [Experiments & Benchmarks](experiments.md)
  - maintained comparison runners and expected outputs
- [Script Reference](script_reference.md)
  - maturity map for scripts and notebooks

## Notebook-First Readers

If you prefer to learn the repository through interactive walkthroughs, start
with:

1. [01_prepare_data.ipynb](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/01_prepare_data.ipynb)
2. [02_train.ipynb](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/02_train.ipynb)
3. [03_inference.ipynb](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/03_inference.ipynb)
4. [04_evaluation.ipynb](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/04_evaluation.ipynb)

The site pages and notebooks are intentionally aligned, so the conceptual
documentation and the runnable examples describe the same maintained surfaces.
