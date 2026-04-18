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
- research diagnostics under:
  - `scripts/analysis/`
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
  - can discover DOI records from official NIST issue pages with
    `--nist-current-archive-pages`
  - can expand NIST journal issue indexes with `--expand-journal-issues`
  - writes optional DOI and audit sidecars for large IDAC crawls
- `attach_idac_aux_to_fixed_splits.py`
  - preserves existing supervised split CSVs and appends expanded IDAC rows to
    train only
  - preferred for fair `gamma_inf` ablations because adding aux-only rows before
    splitting changes scaffold validation/test composition
- `build_vant_hoff_anchor_split.py`
  - fits pairwise Van't Hoff curves on measured train-low rows
  - appends pseudo high-temperature rows with `has_vh_anchor=True`
  - used for temperature-extrapolation objective ablations without relabeling
    measured SLE rows

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
- `run_knn_modelability.py`
- `run_directgnn_error_structure_diagnostics.py`
- `run_prediction_error_slices.py`
- `plot_prediction_error_slices.py`
- `run_temperature_extrapolation_baselines.py`
- `run_temperature_interpolation_baselines.py`
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
- `run_phase1_diagnostic.py`
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
- `scripts/evaluation/run_knn_modelability.py`
  - KNN-style Morgan baseline plus nearest-neighbor `ln_x2` cliff/modelability diagnostics
- `scripts/evaluation/run_prediction_error_slices.py`
  - prediction-only pair, chemistry, solvent-type, and nearest-neighbor error slices for existing model CSVs
- `scripts/evaluation/plot_prediction_error_slices.py`
  - presentation-ready figures from `results/prediction_error_slices/`
- `scripts/evaluation/run_temperature_extrapolation_baselines.py`
  - CPU-first same-pair low-T to high-T extrapolation split plus pair-level
    Van't Hoff / linear / constant and RF(Morgan+T) baselines
- `scripts/evaluation/run_temperature_interpolation_baselines.py`
  - CPU-first same-pair interior-temperature interpolation split plus
    pair-level curve baselines and RF(Morgan+T)
- `scripts/evaluation/run_metric_diagnostics.py`
  - split-sensitivity bundle for `scaffold` / `solute` / `solvent` / pair-random / row-random RF comparisons,
    overlap summaries, and target-shift diagnostics
- `scripts/evaluation/run_thermo_stress_suite.py`
  - slice-based stress diagnostics for canonical `predictions.csv` bundles
- `scripts/experiments/build_benchmark_release.py`
  - frozen release manifest with checksums for processed splits and benchmark
- `scripts/analysis/audit_idac_expansion.py`
  - consolidates starter and NIST-extracted IDAC, aggregates duplicate
    pair-temperature measurements, and audits SLE-corpus coverage
- `scripts/analysis/audit_dcp_correction.py`
  - estimates the scale and failure modes of the maintained GC `dCp_fus`
    correction on processed splits
- `scripts/analysis/audit_fusion_supervision.py`
  - audits direct `T_m` / `dH_fus` coverage and derived `dS_fus` statistics
    for entropy-coupled crystal-branch ablations
- `scripts/analysis/summarize_physics_supervision_readiness.py`
  - combines IDAC, fixed-split aux attachment, dCp, unit-conversion, and error
    slice diagnostics into one operational report
- `scripts/analysis/scan_thermoml_property_inventory.py`
  - inventories cached ThermoML JSON property labels before implementing GE,
    VLE, heat-capacity, or other auxiliary tasks
- `scripts/analysis/audit_water_small_molecule_graphs.py`
  - audits water/simple-solvent coverage, current water error slices, and the
    graph-topology difference between legacy self-loop and opt-in explicit-H
    small-molecule featurization
- `scripts/analysis/run_structural_extrapolation_diagnosis.py`
  - consumes aligned scaffold prediction slices and writes DirectGNN-vs-TGNN
    deltas by novelty, target range, chemistry class, solvent type, and pair

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

### `scripts/analysis/`

- `diagnose_gradient_flow.py`
- `analyze_timp_channels.py`
- `audit_fusion_supervision.py`
- `run_source_uncertainty_audit.py`
- `run_structural_extrapolation_diagnosis.py`
- `sensitivity_analysis.py`
- `weight_analysis.py`
- `aggregate_proxy_results.py`
- `plot_probe_evolution.py`
- `visualize_attribution.py`
- `generate_presentation_figures.py`

These are research diagnostics and interpretation helpers rather than canonical
training/evaluation entry points. They are most useful after you already have
checkpoints, benchmark bundles, or `tgnn_intermediates.csv` exports.

`run_directgnn_error_structure_diagnostics.py` is the maintained DirectGNN
error-structure utility for the scaffold split:

- evaluates the maintained `DirectGNN` checkpoint on `train/val/test`
- reports actual `train -> test` generalization gaps
- summarizes pair-level error concentration and worst pairs
- slices test error by coarse solute chemistry buckets
- links DirectGNN test errors to nearest-train `pair Tanimoto` diagnostics when
  `results/knn_modelability_smoke/nearest_neighbors.csv` is available

`run_prediction_error_slices.py` is the maintained prediction-only companion
for cross-model scaffold error slicing:

- consumes existing prediction CSVs with `ln_x2_true` / `ln_x2_pred`
- defaults to the current `DirectGNN`, `TGNN_MPNN`, and `RF_hybrid` scaffold
  prediction artifacts from `results/tail_diagnostics_fast_v2/`
- writes aligned pair-level, coarse-chemistry, solvent-type,
  chemistry-by-solvent, halogenated-aromatic, paired-delta, and
  nearest-neighbor-linked summaries under `results/prediction_error_slices/`

`plot_prediction_error_slices.py` turns that bundle into PNG/PDF figures and
copies them into `presentation/figures/generated/` by default:

- model-level scaffold comparison
- pair-MAE CDF
- coarse chemistry class MAE
- halogenated-aromatic MAE by solvent type
- nearest-neighbor Tanimoto-bin MAE
- paired-delta summary versus DirectGNN

`run_temperature_extrapolation_baselines.py` is the quick protocol check for
the temperature-extrapolation argument:

- combines the maintained processed `train/val/test` rows
- selects same `(solute, solvent)` pairs with low-temperature observations and
  held-out high-temperature observations
- writes reusable neural-training CSVs under
  `results/temperature_extrapolation_baselines/splits/`
- evaluates cheap CPU baselines:
  - pair mean
  - last low-temperature value
  - pairwise linear-in-`T`
  - pairwise linear-in-`1/T` Van't Hoff
  - RF over Morgan fingerprints plus temperature
- generates presentation-ready figures under
  `presentation/figures/generated/temperature_extrapolation_*`

`build_vant_hoff_anchor_split.py` is the companion objective-ablation utility:

- reads a low-temperature train split such as
  `results/temperature_extrapolation_baselines/splits/train_low.csv`
- fits per-pair `ln(x2) = slope * (1/T) + intercept`
- appends pseudo high-temperature `vh_anchor` rows and writes fit diagnostics
- the training loss consumes these rows through the `vh_anchor` loss, not
  through normal measured-solubility supervision

`run_temperature_interpolation_baselines.py` is the quick protocol check for
the in-pair temperature-interpolation argument:

- combines the maintained processed `train/val/test` rows
- selects pairs with enough unique temperatures and temperature span
- keeps each pair's lowest and highest temperatures in train
- holds out only interior temperatures for val/test
- writes reusable neural-training CSVs under
  `results/temperature_interpolation_baselines/splits/`
- evaluates cheap CPU baselines:
  - pair mean
  - nearest train temperature
  - pairwise linear-in-`T`
  - pairwise linear-in-`1/T` Van't Hoff
  - piecewise linear interpolation
  - RF over Morgan fingerprints plus temperature
- generates presentation-ready figures under
  `presentation/figures/generated/temperature_interpolation_*`

`run_source_uncertainty_audit.py` is the maintained source-quality utility for
BigSolDB:

- preserves detailed raw `Source` identifiers through the maintained
  BigSolDB-to-`ln(x2)` conversion path
- computes source footprint diagnostics such as temperature-grid density and
  van't Hoff smoothness proxies
- exports heuristic source-level method/sigma priors plus a manual-review CSV
  for future weighted-loss experiments

The main TGNN training entrypoint now also covers the newer maintained model
surfaces:

- GPS encoder configs through `encoder_type="gps"`
- TIMP encoder configs through `encoder_type="timp"`
  - optional `use_gasteiger_charges`
  - optional `use_phys_edge_features`
  - optional `use_thermo_cross_attention`
- TGNN descriptor augmentation with stored descriptor normalization stats
- Stage 0 warm starts through `--pretrain` / `--pretrain-checkpoint`

## Usage Guidance

Preferred examples:

```bash
python scripts/training/train.py --help
python scripts/training/train_with_pretrain.py --help
python scripts/evaluation/evaluate_complete.py --help
python scripts/evaluation/benchmark_adapter_model.py --help
python scripts/experiments/run_phase1_diagnostic.py --help
python scripts/experiments/run_medium_budget_comparison.py --help
python scripts/experiments/build_benchmark_release.py --help
python scripts/external/run_fastsolv.py --help
python scripts/launch_lab.py
```

`run_phase1_diagnostic.py` is the maintained multi-seed wrapper when you want:

- matched TGNN-Solv vs DirectGNN runs across several seeds
- optional RF descriptor/morgan/hybrid baselines in the same output tree
- automatic TGNN oracle evaluation and `tgnn_intermediates.csv` export
- one aggregate JSON/markdown bundle with paired t-tests

Legacy top-level paths remain supported and unchanged.
