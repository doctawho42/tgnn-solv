# Scripts Layout

The repository now exposes two parallel CLI layouts:

- legacy top-level entry points under `scripts/*.py`
- categorized wrappers under:
  - `scripts/data/`
  - `scripts/training/`
  - `scripts/evaluation/`
  - `scripts/experiments/`
  - `scripts/external/`
  - `scripts/applications/`
- GUI launchers under:
  - `scripts/launch_lab.py`
  - `scripts/gui/launch_lab.py`

## Why Both Exist

The top-level scripts remain the compatibility surface for:

- existing docs and copy-paste commands
- tests that import script modules directly
- runners that import other scripts by filename
- external automation and compatibility entrypoints such as `reproduce.sh`

The categorized paths are the preferred navigation surface for humans.
They delegate to the legacy entry points, so behavior stays identical.

## Category Map

### `scripts/data/`

- `prepare_data.py`
- `extract_idac_from_thermoml.py`
  - can recreate or extend the published Zenodo starter files
    `idac.csv` / `idac_seed_dois.txt` from NIST ThermoML JSON

### `scripts/training/`

- `train.py`
- `train_with_pretrain.py`
- `train_directgnn.py`
- `diagnose_training.py`
- `run_resume_safe_train.sh`

### `scripts/evaluation/`

- `evaluate_complete.py`
- `benchmark_tgnn_solv.py`
- `benchmark_adapter_model.py`
- `validate_physics.py`
- `analyze_benchmark.py`
- `compare_models.py`
- `error_analysis.py`
- `run_thermo_stress_suite.py`

### `scripts/experiments/`

- `run_seeds.py`
- `run_ablation.py`
- `run_split_comparisons.py`
- `run_full_budget_experiment.py`
- `run_medium_budget_comparison.py`
- `run_optuna.py`
- `reproduce_paper.py`
- `learning_curves.py`
- `temperature_extrapolation.py`
- `statistical_tests.py`
- `generate_paper_figures.py`
- `generate_supplementary.py`
- `build_benchmark_release.py`

### `scripts/external/`

- `run_fastsolv.py`
- `compare_fastsolv_tgnn.py`
- `run_solprop.py`

`run_solprop.py` now covers:

- zero-shot SolProp prediction
- train-split calibration
- native SolProp retraining on TGNN-Solv `ln(x2)` targets

The newer infrastructure scripts worth knowing about are:

- `scripts/evaluation/benchmark_adapter_model.py`
  - formal adapter API for arbitrary Python models
- `scripts/evaluation/run_thermo_stress_suite.py`
  - slice-based stress diagnostics for canonical `predictions.csv` bundles
- `scripts/experiments/build_benchmark_release.py`
  - frozen release manifest with checksums for processed splits and benchmark
    bundles

### `scripts/applications/`

- `screen_solvents.py`
- `optimize_process.py`
- `drug_developability.py`
- `pk_profile.py`

These application CLIs are maintained thin wrappers around:

- `tgnn_solv.applications.solvent_screening`
- `tgnn_solv.applications.process_optimization`
- `tgnn_solv.applications.drug_properties`
- `tgnn_solv.applications.pk_profiling`

They are intended for explicit solvent/process/formulation triage, not as
general retrosynthesis or mechanistic PK/PD simulators.

The main TGNN training entrypoint now also covers the newer maintained model
surfaces:

- GPS encoder configs through `encoder_type="gps"`
- TGNN descriptor augmentation with stored descriptor normalization stats
- Stage 0 warm starts through `--pretrain` / `--pretrain-checkpoint`

## Usage Guidance

Preferred examples:

```bash
python scripts/training/train.py --help
python scripts/training/train_with_pretrain.py --help
python scripts/evaluation/evaluate_complete.py --help
python scripts/evaluation/benchmark_adapter_model.py --help
python scripts/experiments/run_medium_budget_comparison.py --help
python scripts/experiments/build_benchmark_release.py --help
python scripts/external/run_fastsolv.py --help
python scripts/launch_lab.py
```

Legacy top-level paths remain supported and unchanged.
