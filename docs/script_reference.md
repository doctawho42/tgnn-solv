# Script Reference

This document maps scripts and notebooks to their intended role and current
stability.

## Maturity Legend

- `Canonical`
  - expected reproducible workflow entry point
- `Stable utility`
  - maintained and useful, but not necessarily part of the default article profile
- `Research`
  - useful experiment runner or analysis tool, but more likely to evolve
- `Optional`
  - depends on external stacks such as FastSolv or SolProp
- `Infrastructure`
  - internal helper, not a user-facing workflow

## Preferred CLI Layout

The preferred human-facing CLI surface is now grouped by purpose:

- `scripts/data/`
- `scripts/training/`
- `scripts/evaluation/`
- `scripts/experiments/`
- `scripts/external/`
- `scripts/applications/`

Legacy top-level `scripts/*.py` entry points remain available as compatibility
wrappers because tests, script-to-script imports, and compatibility entrypoints such as `reproduce.sh` still rely
on them.

## Canonical Workflow

| Entry point | Role | Status | Notes |
|-------------|------|--------|-------|
| `scripts/data/prepare_data.py` | Build processed splits from raw sources | Canonical | Writes all supported split families |
| `scripts/training/train.py` | Train one TGNN-Solv model | Canonical | Three-phase curriculum; supports `mpnn`, `gps`, and `timp` encoders |
| `scripts/experiments/run_seeds.py` | Multi-seed wrapper | Canonical | Can call other train scripts too |
| `scripts/evaluation/evaluate_complete.py` | Quick checkpoint evaluation | Canonical | Figure-ready arrays |
| `scripts/experiments/run_split_comparisons.py` | Fair split-wise comparison | Canonical | TGNN, DirectGNN, RF modes |
| `scripts/experiments/reproduce_paper.py` | Structured article-reproduction runner | Canonical | Supports `core`, `article`, and `full` profiles |
| `scripts/experiments/generate_paper_figures.py` | Figure generation | Canonical | Consumes result JSONs |
| `reproduce.sh` | Compatibility shell driver | Canonical | Delegates to `scripts/experiments/reproduce_paper.py --profile article` |

## Stable Utilities

| Entry point | Role | Status | Notes |
|-------------|------|--------|-------|
| `scripts/training/train_directgnn.py` | Train DirectGNN baseline | Stable utility | Supports descriptor augmentation and TIMP/GPS backbones |
| `scripts/training/train_with_pretrain.py` | Train TGNN-Solv with Stage 0 enabled by default | Stable utility | Thin wrapper over `train.py --pretrain --run-descriptor-probe`; useful for GPS and descriptor-augmented TGNN warm starts too |
| `scripts/training/run_resume_safe_train.sh` | Resume-safe TGNN wrapper for cloud sessions | Stable utility | Wraps `train.py --resume` |
| `scripts/evaluation/benchmark_tgnn_solv.py` | Rich benchmark via `Evaluator` | Stable utility | Use when you want more than quick eval |
| `scripts/evaluation/benchmark_adapter_model.py` | Benchmark a formal Python adapter | Stable utility | Preferred custom-model path when you want fit/predict/report in one contract |
| `scripts/evaluation/analyze_benchmark.py` | Text summary of benchmark JSON | Stable utility | Lightweight reporting helper |
| `scripts/evaluation/compare_models.py` | Compare multiple TGNN checkpoints | Stable utility | Wraps benchmark logic |
| `scripts/training/diagnose_training.py` | Dataset stats and overfit sanity check | Stable utility | Good pre-flight tool |
| `scripts/data/extract_idac_from_thermoml.py` | Build `idac.csv` from NIST ThermoML JSON records | Stable utility | Useful when enabling real `gamma_inf` supervision; works directly with `notebooks/data/raw/idac_seed_dois.txt` and can recreate the published Zenodo starter corpus |
| `scripts/evaluation/probe_gsol_descriptor_recovery.py` | Ridge linear probe from `g_sol` to RDKit descriptors | Stable utility | Useful for encoder-capacity diagnostics |
| `scripts/evaluation/run_thermo_stress_suite.py` | Stress slices on canonical prediction bundles | Stable utility | Reads `predictions.csv`, writes slice metrics JSON |
| `scripts/experiments/run_optuna.py` | Hyperparameter tuning | Stable utility | Supports TGNN, GPS TGNN, descriptor-augmented TGNN, and DirectGNN families |
| `scripts/launch_lab.py` | Launch the maintained Streamlit control surface | Stable utility | Preferred GUI entry point |
| `scripts/gui/launch_lab.py` | Namespaced launcher for the same lab | Stable utility | Same behavior, alternate path |

## Research Experiment Runners

| Entry point | Role | Status | Notes |
|-------------|------|--------|-------|
| `scripts/experiments/run_ablation.py` | Multi-seed ablation sweeps | Research | Includes `fixed_group_priors` and `direct_gnn` |
| `scripts/experiments/run_full_budget_experiment.py` | Full-budget TGNN-vs-DirectGNN diagnostic study | Research | Exports TGNN intermediates and oracle diagnostics |
| `scripts/experiments/run_phase1_diagnostic.py` | Multi-seed full-budget wrapper with oracle and RF aggregation | Research | Writes per-seed subdirs, aggregate JSON, markdown summary, and paired t-tests |
| `scripts/experiments/run_medium_budget_comparison.py` | Full-split medium-budget architecture comparison | Research | 4 TGNN variants, 2 DirectGNN variants, RF baseline |
| `scripts/evaluation/validate_physics.py` | Physics-parameter diagnostics | Research | Useful for TGNN checkpoint inspection |
| `scripts/evaluation/error_analysis.py` | Detailed residual analysis | Research | Consumes evaluation JSON |
| `scripts/experiments/learning_curves.py` | Data-efficiency study | Research | Multi-fraction, multi-seed |
| `scripts/experiments/temperature_extrapolation.py` | Temperature extrapolation study | Research | Uses a combined dataset CSV |
| `scripts/experiments/statistical_tests.py` | Paired significance testing | Research | Used by the `full` reproduction profile, but still analysis-oriented |
| `scripts/experiments/generate_supplementary.py` | Supplementary table generation | Research | Consumes produced result JSONs |
| `scripts/experiments/build_benchmark_release.py` | Freeze a checksum-based benchmark release manifest | Research | Best when preparing a paper-ready artifact snapshot |

## Optional External Baseline Wrappers

| Entry point | Role | Status | Notes |
|-------------|------|--------|-------|
| `scripts/external/run_fastsolv.py` | Predict, train, or compare FastSolv | Optional | Preferred FastSolv wrapper |
| `scripts/external/compare_fastsolv_tgnn.py` | Lightweight TGNN-vs-FastSolv comparison | Optional | Older convenience wrapper |
| `scripts/external/run_solprop.py` | Zero-shot, calibrated, or native-retrained SolProp | Optional | Usually run in a separate environment |

## Application CLIs

| Entry point | Role | Status | Notes |
|-------------|------|--------|-------|
| `scripts/applications/screen_solvents.py` | Solvent library screening, antisolvent search, and green replacement | Stable utility | Works with `TGNN-Solv` and `DirectGNN` checkpoints |
| `scripts/applications/optimize_process.py` | Crystallization, extraction, and reaction-medium optimization | Stable utility | Uses equilibrium heuristics, not kinetics |
| `scripts/applications/drug_developability.py` | BCS-style classification and developability scoring | Stable utility | pH correction and permeability remain heuristic |
| `scripts/applications/pk_profile.py` | GI/media/vehicle PK-facing solubility profile | Stable utility | Solubility-first PK support, not PBPK |

## Infrastructure

| Entry point | Role | Status | Notes |
|-------------|------|--------|-------|
| `scripts/_bootstrap.py` | Adds repo `src/` to `sys.path` for CLIs | Infrastructure | Imported by most scripts |

## Maintained Library Utilities

Some important maintained surfaces are not exposed as standalone CLIs today.
They are available through the Python API and are demonstrated in notebooks.

| Module / API | Role | Notes |
|--------------|------|-------|
| `tgnn_solv.pretrain.Pretrainer` | Stage 0 encoder/readout pretraining core | Used by `train.py --pretrain`, `train_with_pretrain.py`, and `notebooks/02_train.ipynb` |
| `tgnn_solv.pretrain_pipeline` | Stage 0 checkpoint save/load helpers | Used by the maintained TGNN training CLI |
| `tgnn_solv.pretrain.download_zinc250k` | Pretraining SMILES acquisition with fallback | Falls back to BigSolDB SMILES if needed |
| `tgnn_solv.inference.load_model` | Checkpoint loading | Reconstructs config and compatible weights |
| `tgnn_solv.inference.predict_solubility` | Single-system inference | Returns intermediates, not only final `ln(x2)` |
| `tgnn_solv.inference.temperature_scan` | Multi-temperature inference | Useful for van't Hoff style inspection |
| `tgnn_solv.inference.interpret_prediction` | Human-readable prediction report | Good for manual case review |
| `tgnn_solv.uncertainty.MCDropoutPredictor` | Single-checkpoint uncertainty | Covered in `notebooks/04_evaluation.ipynb` |
| `tgnn_solv.uncertainty.EnsemblePredictor` | Multi-checkpoint uncertainty | Now works for both `TGNN-Solv` and `DirectGNN` families |
| `tgnn_solv.uncertainty.calibration_report` | Interval calibration summary | Accepts MC-dropout or ensemble outputs |
| `tgnn_solv.domain.ApplicabilityDomain` | Inference-time OOD / AD scoring | Covered in `notebooks/03_inference.ipynb` and `notebooks/04_evaluation.ipynb` |
| `tgnn_solv.benchmark_adapters` | Formal custom-model adapter contract | Lets arbitrary models participate in canonical benchmark bundles |
| `tgnn_solv.artifacts` | Run manifests and benchmark/model cards | Supplies machine-readable provenance sidecars |
| `tgnn_solv.stress.build_stress_suite` | Thermodynamic stress slices for benchmark bundles | Used after `predictions.csv` already exists |
| `tgnn_solv.applications.solvent_screening.SolventScreener` | Solvent ranking and crystallization-window screening | Shared by CLI and `Experiment Lab` |
| `tgnn_solv.applications.process_optimization.ProcessOptimizer` | Process-facing solvent and temperature optimization | Shared by CLI and `Experiment Lab` |
| `tgnn_solv.applications.drug_properties.DrugPropertyPredictor` | BCS/developability workflow | Shared by CLI and `Experiment Lab` |
| `tgnn_solv.applications.pk_profiling.PKSolubilityProfiler` | GI/media/vehicle PK profile | Shared by CLI and `Experiment Lab` |

The same maintained surfaces are also exposed together through
`tools/experiment_lab/app.py`, but the GUI is an orchestration layer rather
than a separate model implementation.

## High-Signal Usage Notes

### `scripts/experiments/run_seeds.py`

- default train script is `scripts/training/train.py`
- can also launch `scripts/training/train_directgnn.py`
- aggregates `mae`, `rmse`, `r2`, and `pearson_r`

### `scripts/training/train_directgnn.py`

- computes descriptor normalization stats automatically when
  `use_descriptor_augmentation=True`
- saves `descriptor_mean` and `descriptor_std` into the checkpoint
- supports `--checkpoint-every` and `--resume`

### `scripts/training/train.py`

- supports `--checkpoint-every` and `--resume`
- optionally runs Stage 0 with `--pretrain`
- can warm-start from `--pretrain-checkpoint`
- can launch the existing descriptor-recovery probe with `--run-descriptor-probe`
- saves reusable Stage 0 encoder/readout checkpoints through
  `tgnn_solv.pretrain_pipeline`
- stores TGNN descriptor normalization stats in the checkpoint when
  `use_descriptor_augmentation=True`
- fits `gc_prior_tm_scale` / `gc_prior_tm_bias` on the training split when
  `use_gc_priors_crystal=True`
- preserves those calibrated GC settings inside the saved config

### `scripts/experiments/run_ablation.py`

- resolves canonical variant aliases
- automatically enables any optional dataset feature paths required by the
  selected variants

### `scripts/experiments/run_full_budget_experiment.py`

- trains TGNN-Solv and DirectGNN on matched budgets
- exports `metrics.json`, `diagnostics.json`, and `tgnn_intermediates.csv`
- passes `--checkpoint-every` through to the training CLIs
- resumes from existing per-seed checkpoints when available

### `scripts/experiments/run_phase1_diagnostic.py`

- wraps the maintained training CLIs across multiple seeds
- runs TGNN-Solv, DirectGNN, and optional RF descriptor/morgan/hybrid baselines
- saves `seed_<n>/tgnn`, `seed_<n>/tgnn_oracle`, `seed_<n>/directgnn`, and optional `seed_<n>/rf`
- writes `aggregate_metrics.json`, `statistical_tests.json`, and `summary.md`
- reuses the TGNN oracle-evaluation path by forcing oracle injection during post-hoc intermediate export
- auto-resumes from existing per-seed checkpoints when present

### `scripts/experiments/run_medium_budget_comparison.py`

- runs the medium-budget full-scaffold comparison under `results/medium_budget`
- derives a no-oracle training config from `paper_config_combined.yaml`
- writes `summary.json`, `comparison_table.md`, and per-model artifacts

## Notebook Reference

| Notebook | Role | Recommended usage |
|----------|------|-------------------|
| `notebooks/01_prepare_data.ipynb` | Data preparation | Canonical interactive equivalent of `prepare_data.py` |
| `notebooks/02_train.ipynb` | TGNN training walkthrough | Interactive training plus optional Stage 0 pretraining |
| `notebooks/03_inference.ipynb` | Inference examples | Manual inspection, temperature scans, and single-query AD checks |
| `notebooks/04_evaluation.ipynb` | Evaluation workflow | Stratified metrics, MC-dropout, calibration, and AD analysis |
| `notebooks/05_baselines.ipynb` | Baseline experiments | Exploratory DirectGNN, descriptor, RF, and external-baseline work |
| `notebooks/06_ablations.ipynb` | Ablation experiments | Exploratory ablations including maintained split-late comparison |
| `notebooks/07_temperature.ipynb` | Temperature analysis | Research notebook for van't Hoff and multi-temperature behavior |
| `notebooks/08_optuna_tuning.ipynb` | Optuna tuning | Interactive tuning |

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Experiments & Benchmarks](experiments.md)
- [Experiment Lab](experiment_lab.md)
- [Notebooks & Tutorials](notebooks.md)
- [Contributing](contributing.md)
- [Repository Audit](repository_audit.md)

</div>
