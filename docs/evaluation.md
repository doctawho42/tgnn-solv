# Evaluation Guide

## Overview

Different maintained evaluation surfaces answer different questions:

- library inference helpers in `src/tgnn_solv/inference.py`
  - single-point prediction, temperature scans, checkpoint I/O, human-readable
    reports
- library uncertainty helpers in `src/tgnn_solv/uncertainty.py`
  - MC-dropout, deep ensembles, calibration summaries
- library applicability-domain helper in `src/tgnn_solv/domain.py`
  - inference-time OOD screening against the training distribution
- `scripts/evaluation/evaluate_complete.py`
  - quick checkpoint evaluation with figure-ready arrays
- `scripts/evaluation/benchmark_tgnn_solv.py`
  - richer `Evaluator`-backed benchmark report
- `scripts/evaluation/validate_physics.py`
  - TGNN physical-parameter diagnostics
- `scripts/experiments/run_split_comparisons.py`
  - fair comparison across scaffold, solute, and solvent splits
- `scripts/experiments/run_full_budget_experiment.py`
  - full-budget TGNN-vs-DirectGNN diagnostic export
- `scripts/experiments/run_medium_budget_comparison.py`
  - full-split medium-budget architecture comparison

The grouped `scripts/evaluation/` and `scripts/experiments/` paths are the
preferred navigation surface. Legacy top-level script paths still work for
backward compatibility.

The same maintained inference, uncertainty, calibration, and OOD surfaces are
also exposed interactively in [Experiment Lab](experiment_lab.md).

## External and Custom Benchmarks

The repository now maintains the competitor and custom-model benchmark surfaces
in the same canonical artifact format used elsewhere in the project.

Main entry points:

- `scripts/run_fastsolv.py`
  - FastSolv pretrained inference and scratch training/evaluation on repo splits
- `scripts/run_solprop.py`
  - SolProp zero-shot prediction and train-split calibration on repo splits
- `scripts/experiments/run_external_baseline_benchmark.py`
  - orchestrates FastSolv and SolProp together and writes one comparison bundle
- `scripts/evaluation/benchmark_custom_model.py`
  - benchmarks an arbitrary prediction CSV or a custom command-generated CSV
    against the canonical split

Artifact contract:

- `report.json`
- `predictions.csv`
- `summary.csv`

That shared contract is what lets `Results & Plots`, the artifact registry, and
the lab compare maintained baselines and custom models without special-case UI.

Current SolProp benchmark policy:

- the maintained stable mode is room-temperature SolProp inference at `298.15 K`
- `train` mode then fits a lightweight calibrator on the repo train split, with
  optional true-temperature input
- `train-native` retrains the native SolProp architecture directly on TGNN-Solv
  `ln(x2)` targets and is the maintained architecture-level comparison mode
- `--temperature-dependent` remains available, but upstream SolProp is unstable
  on part of our chemistry, so the wrapper may fall back row-wise

## Inference API

The core inference helpers live in `src/tgnn_solv/inference.py`.

### `load_model(...)`

```python
from tgnn_solv.inference import load_model

model, cfg = load_model("checkpoints/tgnn_solv_trained.pt")
```

Behavior:

- reconstructs `TGNNSolvConfig` from the checkpoint payload
- restores compatible weights even if the checkpoint contains extra keys
- preserves saved metadata when present

### `predict_solubility(...)`

```python
from tgnn_solv.inference import predict_solubility

result = predict_solubility(
    model,
    solute_smiles="CC(=O)Nc1ccc(O)cc1",
    solvent_smiles="CCO",
    T=298.15,
)
```

`predict_solubility` returns more than only `ln(x2)`:

- final `x2` and `ln_x2`
- ideal-solubility and activity-coefficient decomposition
- crystal properties `T_m`, `dH_fus`, `dCp_fus`
- NRTL outputs such as `tau_12`, `tau_21`, `alpha_12`
- Hansen predictions and `Ra`
- correction magnitude and gate value
- optional GC crystal priors when the checkpoint uses them
- optional direct-path sigma outputs when the model emits them

Inference-time feature handling is config-aware:

- if `use_morgan_features=True`, Morgan fingerprints are generated on the fly
- if `use_descriptor_priors=True`, descriptor-prior features are generated on
  the fly
- if `use_group_priors=True`, fixed group-prior features are generated on the
  fly
- if `use_gc_priors_crystal=True`, crystal GC priors are recomputed on the fly
  with fallback priors when needed

Normal inference never injects oracle `T_m` or `dH_fus`. Oracle substitution is
reserved for diagnostics unless explicitly forced by an evaluation script.

### `temperature_scan(...)`

Use this for a solubility curve across temperature:

```python
from tgnn_solv.inference import temperature_scan

scan_df = temperature_scan(
    model,
    solute_smiles="CC(=O)Nc1ccc(O)cc1",
    solvent_smiles="CCO",
    T_min=270.0,
    T_max=340.0,
    n_points=15,
)
```

The returned DataFrame includes:

- `T`
- `x2`
- `ln_x2`
- `x_ideal`
- `gamma_2`
- `correction`

### `interpret_prediction(...)`

`interpret_prediction(result)` turns a prediction dict into a readable report
with:

- solubility magnitude
- decomposition into crystal and non-ideal terms
- crystal-property sanity cues
- NRTL parameters
- Hansen-distance interpretation
- direct-path sigma when available

## Uncertainty Estimation

The uncertainty helpers live in `src/tgnn_solv/uncertainty.py`.

### `MCDropoutPredictor`

This is the low-friction post-hoc option when you have one checkpoint:

```python
from tgnn_solv.uncertainty import MCDropoutPredictor

mc = MCDropoutPredictor(model, n_samples=30)
pred = mc.predict("CC(=O)Nc1ccc(O)cc1", "CCO", T=298.15)
```

It returns mean, std, and 5th/95th percentiles for:

- `ln_x2`
- `x2`
- `gamma_2`
- `T_m`
- `dH_fus`
- `Phi`
- `ln_gamma_2`
- correction magnitude

### `EnsemblePredictor`

This is the higher-fidelity option when you have multiple trained checkpoints:

```python
from tgnn_solv.uncertainty import EnsemblePredictor

ens = EnsemblePredictor([model1, model2, model3])
pred = ens.predict("CC(=O)Nc1ccc(O)cc1", "CCO", T=298.15)
```

The notebook examples focus on MC-dropout because it only needs one model, but
the ensemble API is maintained and available for multi-seed work.

### `calibration_report(...)`

`calibration_report(predictions, true_ln_x2)` summarizes whether the predicted
intervals are sensible. The current report fields are:

- `n_samples`
- `PICP_90`
- `MPIW`
- `MAE`
- `RMSE`
- `sharpness`

## Applicability Domain and OOD Detection

The inference-time OOD helper is `ApplicabilityDomain` in
`src/tgnn_solv/domain.py`.

### What is currently implemented

The current AD score combines two signals:

- Mahalanobis distance in the learned pair-representation space
- nearest-neighbor Morgan Tanimoto similarity for solute and solvent

It also reports:

- whether the exact solute was seen in training
- whether the exact solvent was seen in training
- a combined `confidence` score

Important implementation note:

- older high-level descriptions may mention leverage
- the maintained implementation currently does not use leverage in the
  decision path or output payload

### Minimal AD workflow

```python
import pandas as pd

from tgnn_solv.data import PROCESSED_DIR, make_loaders
from tgnn_solv.domain import ApplicabilityDomain

train_df = pd.read_csv(PROCESSED_DIR / "train.csv")
val_df = pd.read_csv(PROCESSED_DIR / "val.csv")
test_df = pd.read_csv(PROCESSED_DIR / "test.csv")
train_loader, _, _ = make_loaders(train_df, val_df, test_df, batch_size=cfg.batch_size)

ad = ApplicabilityDomain(model, train_loader)
score = ad.score("CC(=O)Nc1ccc(O)cc1", "CCO", T=298.15)
print(score["in_domain"], score["confidence"])
print(ad.report("CC(=O)Nc1ccc(O)cc1", "CCO", T=298.15))
```

Current scoring behavior:

- `mahalanobis <= mahalanobis_cutoff`
  - latent-space criterion passes
- both `tanimoto_solute` and `tanimoto_solvent >= tanimoto_threshold`
  - fingerprint criterion passes
- `in_domain`
  - true only if both criteria pass
- `confidence`
  - average of a Mahalanobis-derived confidence term and the smaller of the
    two Tanimoto similarities

This is not wired automatically into `predict_solubility`. If you want OOD
screening at inference time, call `ApplicabilityDomain` alongside prediction.

## Experiment Lab Evaluation Workbench

`Experiment Lab` exposes the maintained evaluation stack through four
interactive inference modes:

- `Run & inspect`
  - single-system prediction, RDKit structure view, and temperature scan for both `TGNN-Solv` and `DirectGNN`
- `History & compare`
  - persistent saved runs under `results/lab_runs/inference_history/`
- `Uncertainty lab`
  - ensemble vs MC-dropout review with saved comparison sessions
- `Calibration dashboard`
  - batch `PICP_90`, `MPIW`, `MAE`, `RMSE`, and parity analysis with saved history

These GUI views still delegate to the same underlying APIs:

- `predict_solubility`
- `predict_direct_solubility`
- `temperature_scan`
- `temperature_scan_direct`
- `MCDropoutPredictor`
- `EnsemblePredictor`
- `calibration_report`
- `ApplicabilityDomain`

## `scripts/evaluation/evaluate_complete.py`

Use this for lightweight checkpoint evaluation:

```bash
python scripts/evaluation/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output results/full_evaluation.json \
    --verbose
```

Outputs include:

- overall regression metrics
- temperature-stratified metrics
- solubility-range metrics
- solvent-type metrics
- auxiliary-label-availability metrics
- `true_ln_x2` / `pred_ln_x2` arrays for plotting

Use this as the default quick report.

## `scripts/evaluation/benchmark_tgnn_solv.py`

Use this when you want the richer `Evaluator` path:

```bash
python scripts/evaluation/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/results.json
```

It shares the same broad report schema as `evaluate_complete.py`, but is more
convenient for deeper benchmark summaries.

## `scripts/evaluation/validate_physics.py`

Use this when you care about TGNN intermediates rather than only final
solubility error:

```bash
python scripts/evaluation/validate_physics.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output results/physics_validation.json \
    --device cuda
```

This script understands the current optional feature paths, including:

- Morgan augmentation
- descriptor priors
- fixed group priors
- crystal GC priors

## `scripts/experiments/run_split_comparisons.py`

Use this for fair comparison across split protocols:

```bash
python scripts/experiments/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline,rf_morgan,rf_hybrid" \
    --config configs/paper_config.yaml \
    --n-seeds 3 \
    --output results/split_comparisons.json
```

It:

- resolves canonical train/val/test triplets for each split family
- runs the requested models on matched data
- stores per-split artifacts under `results/split_comparisons/`
- aggregates metrics across seeds

## `scripts/experiments/run_full_budget_experiment.py`

This is the most detailed single diagnostic runner in the repo:

```bash
python scripts/experiments/run_full_budget_experiment.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --seeds 42 \
    --output-dir results/full_budget_experiment \
    --device cuda
```

It does all of the following in one command:

- trains TGNN-Solv on the full paper budget
- trains DirectGNN on an equivalent total epoch budget
- evaluates both on the same test split
- exports TGNN intermediate physical parameters for every test sample
- reruns TGNN inference in forced-oracle mode
- writes an interpretation guide alongside the metrics

Per-seed and aggregate artifacts include:

- `metrics.json`
- `diagnostics.json`
- `tgnn_intermediates.csv`
- `README.md`

The intermediate CSV includes, when available:

- `T_m_pred`, `dH_fus_pred`, `dCp_fus_pred`
- `T_m_solver`, `dH_fus_solver`, `dCp_fus_solver`
- `T_m_gc` for GC-prior crystal runs
- `tau_12_pred`, `tau_21_pred`, `alpha_pred`
- `ln_gamma2_pred`
- `Phi_pred`
- `ln_x2_physics`
- `ln_x2_final`
- correction magnitude and gate outputs
- true `T_m` / `dH_fus`
- oracle usage masks

The runner reuses resumable per-seed checkpoints created by the main training
CLIs.

## `scripts/experiments/run_medium_budget_comparison.py`

Use this for the full-scaffold medium-budget architecture comparison:

```bash
python scripts/experiments/run_medium_budget_comparison.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/medium_budget \
    --device cuda
```

It trains and evaluates:

- `tgnn_tuned`
- `tgnn_gc_priors`
- `tgnn_no_bridge`
- `tgnn_combined_no_oracle`
- `directgnn_tuned`
- `directgnn_descriptors`
- `rf_descriptors`

Top-level outputs:

- `results/medium_budget/summary.json`
- `results/medium_budget/comparison_table.md`
- `results/medium_budget/per_model/<model>/...`

For TGNN models, per-model outputs include:

- `metrics.json`
- `standard_intermediates.csv`
- `oracle_tm_intermediates.csv`
- `config.yaml`
- `resolved_config.json`
- training logs and checkpoints

The combined TGNN comparison derives a no-oracle training config from
`paper_config_combined.yaml` and still evaluates oracle mode afterward.

## FastSolv and Other External Comparisons

Preferred FastSolv wrapper:

```bash
python scripts/external/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics results/fastsolv_compare.json
```

SolProp remains an optional separate-environment workflow.

## Practical Guidance

Use:

- `evaluate_complete.py`
  - for quick checkpoint reports
- `benchmark_tgnn_solv.py`
  - for richer benchmark summaries
- `validate_physics.py`
  - for TGNN-only physical diagnostics
- `ApplicabilityDomain`
  - for inference-time OOD screening against the training split
- `MCDropoutPredictor`
  - for single-checkpoint uncertainty
- `EnsemblePredictor`
  - for multi-checkpoint uncertainty
- `run_split_comparisons.py`
  - for fair split-protocol comparisons
- `run_full_budget_experiment.py`
  - for full-budget TGNN-vs-DirectGNN diagnosis
- `run_medium_budget_comparison.py`
  - for the full-split medium-budget architecture study

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Results](results.md)
- [Experiment Lab](experiment_lab.md)
- [Model Zoo](model_zoo.md)
- [FAQ](faq.md)
- [Troubleshooting](troubleshooting.md)

</div>
