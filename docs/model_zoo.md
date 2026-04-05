# Model Zoo

This page documents the checkpoint conventions used by TGNN-Solv and the
current status of publicly documented models.

## Current Status

The repository does not yet publish a versioned "official checkpoint bundle"
for download through the documentation site.

What is available today:

- checkpoints produced locally by the training scripts
- per-seed and per-model checkpoints produced by experiment runners
- consistent loading through `tgnn_solv.inference.load_model`
- checkpoint sidecars emitted by the maintained training CLIs:
  - `<checkpoint>.manifest.json`
  - `<checkpoint>.model_card.json`

That means the model zoo is currently a schema and workflow page rather than a
download catalog.

It is also useful to separate three artifact classes:

- trainable checkpoints
- benchmark bundles (`summary.csv`, `report.json`, `predictions.csv`,
  `run_manifest.json`, `benchmark_card.json`)
- lab-history JSON artifacts under `results/lab_runs/`

Only the first class belongs to the model zoo in the strict sense.

## Where Checkpoints Come From

Common checkpoint locations:

- `checkpoints/*.pt`
  - manual single-run training outputs
- `checkpoints/seeds/*.pt`
  - multi-seed outputs
- `results/full_budget_experiment/.../*.pt`
  - full-budget study outputs
- `results/medium_budget/per_model/<model>/checkpoint.pt`
  - medium-budget architecture-comparison outputs

## Loading a Checkpoint

Use the maintained inference API:

```python
from tgnn_solv.inference import load_model

model, cfg = load_model("checkpoints/tgnn_solv_tuned.pt")
```

This reconstructs:

- the model config
- node and edge feature dimensions
- compatible weights from the checkpoint payload

## Checkpoint Compatibility

TGNN checkpoints written by the maintained training path include:

- model weights
- serialized config
- feature dimensions
- optional resume state
- optional training history / metadata depending on the save point

DirectGNN checkpoints additionally store descriptor normalization statistics
when descriptor augmentation is enabled:

- `descriptor_mean`
- `descriptor_std`

Current tooling scope:

- `TGNN-Solv` checkpoints support the full physics-facing inference workbench
- `DirectGNN` checkpoints support `Run & inspect`, `Uncertainty lab`, and
  `Calibration dashboard`
- checkpoint model cards now capture capability flags such as descriptor
  augmentation, GC priors, and uncertainty support

## Recommended Local Naming

If you are creating your own checkpoint library, use names that encode:

- model family
- split
- budget
- seed
- special feature path

Example:

```text
tgnn_tuned_scaffold_50_200_50_seed42.pt
directgnn_desc_scaffold_200_seed42.pt
```

## Suggested Metadata To Record

For any checkpoint you intend to reuse or share, keep or publish:

- the checkpoint itself
- the emitted `*.manifest.json`
- the emitted `*.model_card.json`

Those sidecars should contain at least:

- training command
- config path
- split protocol
- seed
- device
- test metrics
- for TGNN:
  - `T_m` MAE / Pearson `r`
  - oracle sensitivity
  - any GC-prior metrics if relevant

## Example Local Model Registry

If you want to maintain your own model zoo inside a lab or fork, a practical
layout is:

```text
checkpoints/
  registry.json
  tgnn_tuned_scaffold_seed42.pt
  directgnn_tuned_scaffold_seed42.pt
  directgnn_desc_scaffold_seed42.pt
```

Where `registry.json` contains:

- checkpoint path
- config file
- metrics
- notes
- commit hash

The maintained checkpoint sidecars already cover most of that schema, so a
local registry can now be mostly an indexing layer rather than a place where
you hand-write provenance from scratch.

## Current Site-Documented Artifacts

Two local artifact families are already important enough to mention here:

### Medium-budget architecture comparison

Expected path:

- `results/medium_budget/per_model/<model>/checkpoint.pt`

Purpose:

- full-scaffold single-seed architecture comparison

### Full-budget diagnostic experiment

Expected path:

- `results/full_budget_experiment/<seed>/...`

Purpose:

- matched-budget TGNN-vs-DirectGNN diagnostics with intermediate exports

### External competitor benchmark outputs

Expected path:

- `results/external_baselines/article_benchmark/`

Purpose:

- benchmark bundles for FastSolv and native-retrained SolProp
- directly comparable in `Benchmark Studio`, but not model-zoo checkpoints in
  the same sense as TGNN/DirectGNN training outputs

## If You Want a Public Download Section Later

Once stable checkpoints are published, this page should grow into a table like:

| Name | Model | Split | Budget | Seed(s) | Metrics | Download |
| --- | --- | --- | --- | --- | --- | --- |

Until then, treat the model zoo as a checkpoint compatibility guide.

## Related Pages

- [Results](results.md)
- [Experiments & Benchmarks](experiments.md)
- [Evaluation & Inference](evaluation.md)
