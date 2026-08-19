# Project Memory

Last updated: 2026-04-26

## Purpose

This file is the canonical long-term memory for AI agents working in this
repository.

Use it to keep the current project state stable across separate chats, IDE
restarts, and agent handoffs.

When `main.tex`, presentation assets, docs, and fresh result bundles disagree,
prefer:

1. current reproducible artifacts under `results/`
2. current maintained configs and scripts
3. this file
4. older narrative documents (`main.tex`, presentation scripts, older docs)

## Project Identity

- Project: `TGNN-Solv`
- Main maintained question:
  - does an explicit physics bottleneck help relative to the same graph
    backbone trained directly on `ln(x2)`?
- Main controlled comparison:
  - `TGNN-Solv`
  - `DirectGNN`
- Target:
  - equilibrium solubility as `ln(x2)`
- Current corpus framing:
  - BigSolDB-derived, water-inclusive supervised subset is now the maintained
    default

## Canonical Data And Split Facts

- Full merged frame:
  - `120,197` rows
  - `19,878` unique solute
  - `212` solvent
  - `29,826` unique pairs
- Solubility-supervised subset:
  - `108,287` rows
  - `212` solvent
  - `12,129` unique `(solute, solvent)` pairs
  - median temperatures per pair: `9`
- Maintained canonical split in reports and training docs:
  - `solute_scaffold`
- Additional maintained split families:
  - `solute`
  - `solvent`
  - research diagnostics also used:
    - `pair_random`
    - `row_random`
    - `scaffold_random`

## Current Accepted Findings

### 1. Current baseline ordering on the maintained scaffold split

Accepted current numbers from the presentation/diagnostic pipeline:

- `DirectGNN`: `MAE 1.652`, `R^2 0.478`
- `RF hybrid`: `MAE 1.722`, `R^2 0.449`
- `TGNN MPNN`: `MAE 1.741`, `R^2 0.438`

Interpretation:

- `DirectGNN` currently beats the best maintained RF baseline.
- The current direct-vs-physics gap is small:
  - physics path costs about `+0.09 MAE` relative to DirectGNN.
- Older text in `main.tex` and older narrative pages may still reflect a
  pre-fix regime where RF was stronger. Treat those sections as stale unless
  they are explicitly revalidated by current artifacts.

Primary artifacts:

- `presentation/seminar_talk.tex`
- `results/proxy_comparison/`
- `results/medium_budget/`

### 2. KNN/modelability critique is not supported by current data

Nearest-neighbor diagnostics on the maintained split:

- `1-NN pair Tanimoto` full split:
  - `MAE 2.530`
  - `R^2 -0.192`
- controlled subset `5k/1k`:
  - `1-NN pair Tanimoto`: `MAE 2.716`
  - `sklearn KNN k=5 Euclidean`: `MAE 2.844`

Interpretation:

- simple neighbor lookup is much weaker than RF and DirectGNN
- this is not a literal MODI calculation
- it is an empirical counterexample to the claim
  `bad KNN => unusable dataset`

Primary artifacts:

- `results/knn_modelability_smoke/`
- `results/knn_subset_compare/`
- `presentation/figures/generated/knn_*`

### 3. Split difficulty is the main global driver of headline metrics

RF protocol comparison:

- `scaffold`: `MAE 1.703`, `R^2 0.462`
- `solute`: `MAE 1.642`, `R^2 0.420`
- `solvent`: `MAE 0.732`, `R^2 0.735`
- `pair_random`: `MAE 0.783`, `R^2 0.806`
- `row_random`: `MAE 0.166`, `R^2 0.987`

Interpretation:

- `solute` is nearly as hard as `scaffold`
- `solvent` is much easier
- `pair_random` is much easier than `solute`
- `row_random` is heavily leakage-friendly and is not a serious headline
  protocol for this pair-temperature corpus
- the dominant problem is generalization to unseen solutes

Primary artifacts:

- `results/metric_diagnosis_bundle/comparison_table.md`
- `results/metric_diagnosis_bundle/summary.json`

### 4. Current scaffold split is biased toward the left tail

Current maintained `scaffold` test is materially left-shifted relative to a
random scaffold-group split.

- current `scaffold` test:
  - mean `ln_x2 = -6.068`
  - std `3.118`
  - `frac(ln_x2 < -15) = 1.03%`
- `scaffold_random` test:
  - mean `ln_x2 = -5.230`
  - std `2.590`
  - `frac(ln_x2 < -15) = 0.13%`

Scaffold-group composition also shifts:

- current test groups:
  - `46.24` rows/group
  - mean heavy atoms `27.88`
- random scaffold test groups:
  - `136.13` rows/group
  - mean heavy atoms `22.86`

Interpretation:

- the current balanced scaffold packing pushes rarer, heavier, less soluble
  scaffold groups into test
- current scaffold metrics are therefore affected by both structural novelty
  and target-shift bias

Primary artifacts:

- `results/metric_diagnosis_scaffold_bias/scaffold_bias_summary.json`
- `results/metric_diagnosis_scaffold_bias/SUMMARY.md`
- `results/metric_diagnosis_scaffold_random_rf/quick_rf_metrics.json`

### 5. External baselines reproduce the same split story

`SolProp native quick`:

- `solute`:
  - `MAE 1.624`
  - `R^2 0.388`
- `pair_random`:
  - `MAE 0.638`
  - `R^2 0.876`

Interpretation:

- external baseline behavior matches RF diagnostics
- `pair_random` is much easier than `solute`
- the main difficulty is not "new pair" in general; it is new-solute
  generalization

Primary artifacts:

- `results/external_baselines/solute/solprop_native_quick/metrics.json`
- `results/external_baselines/pair_random/solprop_native_quick_recovered/test_metrics.json`
- recovered contract-v2 bundles:
  - `results/external_baselines/solute/solprop_native_contract_v2/metrics.json`
  - `results/external_baselines/pair_random/solprop_native_contract_v2/metrics.json`

### 6. FastSolv status

Current status as of `2026-04-16`:

- descriptor NaNs were real and were sanitized in `scripts/run_fastsolv.py`
- all-NaN predictions were traced further downstream:
  - `logS_from_ln_x2(...)` produces many non-finite training targets
  - `NaN` targets come from solvents with no molarity estimate
  - `inf` targets come mostly from water rows with exact `ln_x2 = 0`
  - old FastSolv training path dropped `NaN`, but not `inf`
  - this corrupted scaler stats:
    - checkpoint `target_means = 3.4e38`
    - checkpoint `target_vars = NaN`
  - the model then predicted only `NaN`

Current fix status:

- `scripts/run_fastsolv.py` now filters non-finite converted `logS` rows before
  scaling/training and writes `target_diagnostics`
- `src/tgnn_solv/data/sources.py` now augments `_density_map()` with the
  authors' `BigSolDBv2.1_densities.csv`, joined to canonical
  `SMILES_Solvent` through the main BigSolDB table
- full-split target stats are now finite after filtering
- density coverage improvement on `solute` split:
  - train `NaN logS`: `22,211 -> 2,590`
  - val `NaN logS`: `2,733 -> 300`
  - test `NaN logS`: `2,701 -> 356`
- remaining `+inf` targets are still dominated by water rows with exact
  `ln_x2 = 0`
- tiny-subset smoke retrain was successful:
  - checkpoint `target_means/target_vars` are finite
  - `val n_predictions = 172`
  - `test n_predictions = 169`
  - prediction columns are finite end-to-end

Accepted conclusion:

- the old FastSolv failure mode is explained and patched
- a maintained `solute` rerun after the patch has completed with finite
  end-to-end predictions:
  - `val`: `MAE 1.909`, `R^2 0.238`
  - `test`: `MAE 1.941`, `R^2 0.226`
- this confirms that the wrapper now works, but also that current
  `FastSolv -> logS -> ln_x2` benchmarking remains materially weaker than
  `SolProp native` and RF on the hard `solute` protocol
- a second controlled low-priority full rerun on `pair_random` was started
  later on `2026-04-16` with:
  - `epochs=30`
  - `patience=5`
  - `batch_size=256`
  - `descriptor_nproc=1`
  - single-threaded BLAS env caps
  - `nice -n 15`
- that `pair_random` rerun has now completed and remained very weak:
  - `val`: `MAE 2.834`, `R^2 -0.414`
  - `test`: `MAE 2.910`, `R^2 -0.594`
- accepted interpretation:
  - the original NaN/corrupted-scaler failure is fixed
  - but the current FastSolv wrapper path is still not a competitive external
    baseline on either `solute` or `pair_random`

Primary artifacts:

- `results/external_baselines/solute/fastsolv_sanitized_train_quick/metrics.json`
- `results/external_baselines/solute/fastsolv_sanitized_train_quick/descriptor_diagnostics.json`
- `results/external_baselines/solute/fastsolv_sanitized_train_quick/checkpoints/epoch=22-step=7153.ckpt`
- `results/external_baselines/solute/fastsolv_finite_targets_tiny_smoke/metrics.json`
- `results/external_baselines/solute/fastsolv_finite_targets_tiny_smoke/descriptor_diagnostics.json`
- completed maintained `solute` rerun:
  - `results/external_baselines/solute/fastsolv_contract_v2/metrics.json`
  - `results/external_baselines/solute/fastsolv_contract_v2/descriptor_diagnostics.json`
- completed `pair_random` rerun:
  - `results/external_baselines/pair_random/fastsolv_contract_v2/`

### 7. Unit conversion accuracy is not the main bottleneck

Completed unit-conversion audit across raw BigSolDB, processed splits, and
prediction-side baseline adapters.

Accepted current results:

- raw BigSolDB pairwise consistency on rows with both `x2` and `logS`:
  - audited rows: `109,278`
  - mean abs `delta logS = 0.0063`
  - mean abs `delta ln_x2 = 0.0137`
  - `p95 abs delta ln_x2 = 0.0338`
- processed split round-trip `ln_x2 -> logS -> ln_x2`:
  - mean abs error across splits: about `3e-17`
  - max abs error across splits: about `3.6e-15`
- prediction-side conversion:
  - `clip_ln_x2_for_logS(...)` is now shared across baseline adapters and
    keeps predicted `logS` finite near `x2 -> 1`

Interpretation:

- conversion math itself is not a headline source of the current `MAE ~ 1.6`
  regime
- raw `x2`/`logS` disagreement exists, but it is two orders of magnitude
  smaller than model error on average
- the important conversion issue is not numeric precision but coverage/boundary
  behavior in external `logS` baselines:
  - missing solvent molarity still causes some `NaN logS` rows
  - exact `ln_x2 = 0` rows imply `x2 = 1` and therefore infinite `logS`
- this coverage/boundary issue matters for `FastSolv` / `SolProp` benchmarking
  but does not explain the poor headline metrics of repo-native models trained
  directly on `ln_x2`

Concrete split facts:

- maintained scaffold `test.csv`:
  - `missing molarity rows = 80 / 8,027` (`1.0%`)
  - `inf logS from ln_x2 = 0 rows = 2,185 / 8,027` (`27.2%`)
- maintained solute `test_solute.csv`:
  - `missing molarity rows = 356 / 12,584` (`2.8%`)
  - `inf logS from ln_x2 = 0 rows = 1,941 / 12,584` (`15.4%`)

Important caveat:

- the largest raw mismatches are isolated source-data inconsistencies between
  raw `x2` and raw `logS`, not a failure of repo conversion formulas

Primary artifacts:

- `results/unit_conversion_audit/summary.json`
- `results/unit_conversion_audit/SUMMARY.md`
- `results/unit_conversion_audit/processed_split_roundtrip.csv`
- `results/unit_conversion_audit/raw_pairwise_by_solvent.csv`
- `scripts/evaluation/run_unit_conversion_audit.py`
- `tests/test_unit_conversions.py`

### 8. Benchmark bundles now separate `ln_x2` headline metrics from finite-only `logS` metrics

As of `2026-04-16`, canonical benchmark reports now expose explicit evaluation
subsets so external-baseline interpretation is less ambiguous.

Current contract:

- `report["overall"]`
  - maintained headline metric block
  - `ln_x2` on all supervised rows
- `report["evaluation_subsets"]["ln_x2_all_supervised"]`
  - explicit copy of the headline subset
- `report["evaluation_subsets"]["ln_x2_finite_logS_subset"]`
  - `ln_x2` metrics restricted to rows where both true and predicted `logS`
    are finite
- `report["evaluation_subsets"]["logS_finite_subset"]`
  - `logS` metrics on that same finite-only subset
- `report["evaluation_subsets"]["policy"]`
  - includes counts and the maintained rule that exact `ln_x2 = 0` rows stay
    in headline `ln_x2` metrics but are excluded from `logS` metrics

Maintained policy:

- `FastSolv` and zero-shot/calibrated `SolProp`
  - headline interpretation remains `ln_x2` on all supervised rows
  - `logS` metrics are auxiliary and finite-only
- native-retrained `SolProp`
  - primary comparison is `ln_x2` on all supervised rows
  - derived `logS` metrics remain auxiliary finite-only diagnostics

Primary source changes:

- `src/tgnn_solv/reporting.py`
- `src/tgnn_solv/external_benchmarking.py`
- `scripts/run_fastsolv.py`
- `scripts/run_solprop.py`
- `tests/test_unit_conversions.py`

### 9. `SolProp native` bundles have been recovered under the new contract

As of `2026-04-16`, the existing `SolProp native quick` checkpoints were
re-evaluated with the new evaluation-subset contract instead of retraining from
scratch.

Recovered bundles:

- `solute`
  - `results/external_baselines/solute/solprop_native_contract_v2/metrics.json`
  - `results/external_baselines/solute/solprop_native_contract_v2/summary.csv`
- `pair_random`
  - `results/external_baselines/pair_random/solprop_native_contract_v2/metrics.json`
  - `results/external_baselines/pair_random/solprop_native_contract_v2/summary.csv`

Accepted current numbers under the maintained headline interpretation
(`ln_x2` on all supervised rows):

- `solute`
  - `val`: `MAE 1.349`, `R^2 0.553`
  - `test`: `MAE 1.624`, `R^2 0.388`
- `pair_random`
  - `val`: `MAE 0.676`, `R^2 0.853`
  - `test`: `MAE 0.638`, `R^2 0.876`

Important caveat:

- `solute` recovery reused the old top-level training metadata from
  `solprop_native_quick/metrics.json`
- `pair_random` only had checkpoint-level artifacts, so the recovered bundle
  explicitly marks:
  - `train = null`
  - `train_metrics = null`
  - `training_history = []`
  - `config.patience = null`

### 10. `SolProp calibrated` contract-v2 status

As of the latest `2026-04-16` update:

- completed `pair_random` rerun:
  - raw test: `MAE 2.357`, `R^2 -0.644`
  - calibrated test: `MAE 1.912`, `R^2 0.172`
- completed `solute` rerun:
  - raw test: `MAE 2.361`, `R^2 -0.465`
  - calibrated test: `MAE 2.340`, `R^2 -0.176`
- these reruns are expensive because `run_solprop.py train` first computes
  upstream predictions on full `train/val/test`, not only on `val/test`
- current machine state during those runs:
  - `8` CPU cores
  - load average about `16 / 14 / 10`

Interpretation:

- the `pair_random` calibrated path is not competitive with native retraining
  and should be treated as an auxiliary adapter diagnostic, not a maintained
  external headline baseline
- the `solute` calibrated path is also not competitive with native retraining
  and remains weak even after temperature-aware linear calibration
- aggressive CPU-side external reruns should still be staged carefully on this
  machine

Primary artifacts:

- completed `pair_random` bundle:
  - `results/external_baselines/pair_random/solprop_calibrated_contract_v2/metrics.json`
- completed `solute` bundle:
  - `results/external_baselines/solute/solprop_calibrated_contract_v2/`

### 11. Source-uncertainty audit is now in place

As of `2026-04-17`, the repository now has a maintained first-pass pipeline for
source-level method/sigma priors derived from raw BigSolDB `Source`
identifiers:

- script:
  - `scripts/analysis/run_source_uncertainty_audit.py`
- helper module:
  - `src/tgnn_solv/data/source_uncertainty.py`
- tracked manual override table:
  - `notebooks/data/metadata/bigsoldb_source_method_overrides.csv`

Accepted current audit results from the maintained supervised corpus:

- supervised rows after the maintained BigSolDB conversion path: `108,287`
- unique detailed sources: `1,656`
- source fragmentation is much stronger than initially assumed:
  - top `50` sources cover only `9.52%` of maintained rows
  - top `200` sources cover `28.33%`
  - top `500` sources cover `57.32%`
  - top `1000` sources cover `86.72%`

Important interpretation:

- manual review of only the top `30-50` sources is not enough for this corpus
- pattern-only heuristics should not be over-interpreted as literal
  experimental methods
- the current source-level sigma map is a training prior, not a pointwise
  uncertainty label

Current first-pass row-weighted prior mix without DOI metadata enrichment:

- `multi_temperature_primary`: `96,908` rows (`89.49%`)
- `unknown`: `10,824` rows (`10.00%`)
- `single_temperature_primary`: `318` rows (`0.29%`)
- `unknown_primary`: `237` rows (`0.22%`)

Accepted conclusion:

- the repository now has the infrastructure needed to attach source-level
  uncertainty priors to maintained BigSolDB rows
- but meaningful method-specific classes like `hplc`, `uv`, or
  `polythermal_visual` require either manual overrides or DOI metadata/text
  enrichment; source-pattern heuristics alone are not enough

Primary artifacts:

- `results/source_uncertainty_audit/SUMMARY.md`
- `results/source_uncertainty_audit/summary.json`
- `results/source_uncertainty_audit/source_summary.csv`
- `results/source_uncertainty_audit/source_method_candidates.csv`
- `results/source_uncertainty_audit/top_sources_manual_review.csv`
- `results/source_uncertainty_audit/supervised_rows_with_source_uncertainty.csv`

### 12. Cross-model prediction-only error slices are aligned

As of `2026-04-17`, scaffold test prediction CSVs from
`results/tail_diagnostics_fast_v2/` have been re-sliced with a common
prediction-only diagnostic script:

- script:
  - `scripts/evaluation/run_prediction_error_slices.py`
- plotting script:
  - `scripts/evaluation/plot_prediction_error_slices.py`
- bundle:
  - `results/prediction_error_slices/`

Current aligned scaffold comparison:

- `DirectGNN`:
  - `MAE 1.652`
  - `R^2 0.478`
  - median pair MAE `1.261`
  - P90 pair MAE `3.752`
  - halogenated-aromatic MAE `1.945`
- `RF_hybrid`:
  - `MAE 1.712`
  - `R^2 0.450`
  - median pair MAE `1.394`
  - P90 pair MAE `3.719`
  - halogenated-aromatic MAE `2.020`
- `TGNN_MPNN`:
  - `MAE 1.741`
  - `R^2 0.438`
  - median pair MAE `1.443`
  - P90 pair MAE `3.576`
  - halogenated-aromatic MAE `1.972`

Paired row-wise deltas versus `DirectGNN` on the same `5,826` scaffold rows:

- `TGNN_MPNN`:
  - mean abs-error delta `+0.089`
  - better than DirectGNN on `46.4%` of rows
  - abs-error correlation with DirectGNN `0.798`
- `RF_hybrid`:
  - mean abs-error delta `+0.060`
  - better than DirectGNN on `48.2%` of rows
  - abs-error correlation with DirectGNN `0.667`

Accepted interpretation:

- the scaffold ranking from previous diagnostics is stable under aligned
  prediction-only slicing: `DirectGNN < RF_hybrid < TGNN_MPNN` by MAE
- errors are not identical across models; RF and TGNN still beat DirectGNN on a
  large minority of individual rows
- `halogenated_aromatic x hydrocarbon` is a consistently difficult slice for
  DirectGNN and RF; TGNN's worst highlighted slice is `other x other`
- nearest-neighbor coverage helps most clearly for DirectGNN:
  Spearman(`pair_tanimoto`, `abs_error`) is `-0.159` for DirectGNN but only
  `-0.056` for TGNN and `-0.076` for RF in this bundle

Primary artifacts:

- `results/prediction_error_slices/SUMMARY.md`
- `results/prediction_error_slices/comparison_summary.csv`
- `results/prediction_error_slices/paired_deltas_vs_DirectGNN.csv`
- `results/prediction_error_slices/figures/`
- copied presentation figures:
  - `presentation/figures/generated/prediction_slice_model_comparison.png`
  - `presentation/figures/generated/prediction_slice_pair_mae_cdf.png`
  - `presentation/figures/generated/prediction_slice_chemistry_class_mae.png`
  - `presentation/figures/generated/prediction_slice_halogenated_aromatic_solvent.png`
  - `presentation/figures/generated/prediction_slice_nearest_neighbor_bins.png`
  - `presentation/figures/generated/prediction_slice_paired_deltas.png`
- `results/prediction_error_slices/DirectGNN/`
- `results/prediction_error_slices/TGNN_MPNN/`
- `results/prediction_error_slices/RF_hybrid/`

### 13. Same-pair temperature extrapolation has a strong physical baseline

As of `2026-04-17`, a CPU-first same-pair low-temperature to
high-temperature extrapolation diagnostic has been added and run:

- script:
  - `scripts/evaluation/run_temperature_extrapolation_baselines.py`
- bundle:
  - `results/temperature_extrapolation_baselines/`

Protocol:

- combine maintained processed `train/val/test` supervised rows
- select same `(solute, solvent)` pairs with:
  - at least `3` low-temperature points at `T <= 310 K`
  - at least `1` high-temperature point at `T >= 330 K`
- hold out the highest low-temperature row per pair as validation
- fit baselines on lower-temperature rows and evaluate on held-out high-T rows
- selected set:
  - `1,751` pairs
  - train / val / test rows: `7,120 / 1,751 / 3,343`
  - high-T test range: `330.0 .. 425.77 K`
  - median train-test temperature gap: `25 K`

High-T test results:

- `pair_vant_hoff`:
  - `MAE 0.368`
  - `R^2 0.887`
  - high-T shift direction accuracy `99.0%`
- `pair_linear_T`:
  - `MAE 0.414`
  - `R^2 0.850`
  - high-T shift direction accuracy `99.0%`
- `pair_last_low_T`:
  - `MAE 1.202`
  - `R^2 0.694`
  - high-T shift direction accuracy `1.0%`
- `RF(Morgan+T)`:
  - `MAE 1.290`
  - `R^2 0.658`
  - high-T shift direction accuracy `40.4%`
- `pair_mean`:
  - `MAE 1.456`
  - `R^2 0.561`
  - high-T shift direction accuracy `1.1%`

Accepted interpretation:

- the initial bundle was baseline-only; a neural single-seed local-MPS proxy
  follow-up was completed later on `2026-04-17`
- it does show that the corpus contains a strong, exploitable thermodynamic
  temperature signal under same-pair high-T extrapolation
- a physically parameterized `1/T` Van't Hoff trend beats the non-extrapolating
  RF(Morgan+T) baseline by about `0.92 MAE`
- the result supports moving the main physics-vs-direct argument away from
  same-distribution scaffold MAE alone and toward explicit temperature
  extrapolation
- the generated split CSVs are the canonical input for fair TGNN/DirectGNN
  neural retraining:
  - `results/temperature_extrapolation_baselines/splits/train_low.csv`
  - `results/temperature_extrapolation_baselines/splits/val_low.csv`
  - `results/temperature_extrapolation_baselines/splits/test_high.csv`

Neural proxy follow-up on the same split:

- bundle:
  - `results/temperature_extrapolation_neural_proxy/`
- caveat:
  - single-seed local-MPS proxy, not full-budget CUDA or multi-seed
- `DirectGNN`:
  - config: `configs/paper_config_directgnn_tuned.yaml`
  - budget: `10` epochs
  - batch size: `256`
  - seed: `42`
  - high-T test: `MAE 1.619`, `R^2 0.283`, `RMSE 2.167`
  - checkpoint:
    - `checkpoints/temperature_extrapolation/directgnn_lowT_highT_proxy_seed42_ep10.pt`
  - logs:
    - `logs/temperature_extrapolation/directgnn_lowT_highT_proxy_seed42_ep10/`
- `TGNN-Solv`:
  - config: `configs/paper_config_tuned.yaml`
  - budget: `1/8/1` phases
  - batch size: `256`
  - seed: `42`
  - high-T test: `MAE 1.945`, `R^2 0.060`, `RMSE 2.481`
  - checkpoint:
    - `checkpoints/temperature_extrapolation/tgnn_solv_lowT_highT_proxy_seed42_p1-8-1.pt`
  - logs:
    - `logs/temperature_extrapolation/tgnn_solv_lowT_highT_proxy_seed42_p1-8-1/`
- accepted immediate interpretation:
  - under this short local proxy budget, `DirectGNN` beats `TGNN-Solv` by
    `0.326 MAE` on high-T extrapolation
  - both neural models remain far worse than the per-pair Van't Hoff baseline
    (`MAE 0.368`) and worse than RF(Morgan+T) (`MAE 1.290`)
  - this is evidence that the current neural training setup does not yet
    exploit the available same-pair temperature trend, not evidence against
    the split or the presence of thermodynamic signal

Primary artifacts:

- `results/temperature_extrapolation_baselines/SUMMARY.md`
- `results/temperature_extrapolation_baselines/summary.json`
- `results/temperature_extrapolation_baselines/metrics_by_model.csv`
- `results/temperature_extrapolation_baselines/trend_summary.csv`
- `results/temperature_extrapolation_baselines/test_temperature_bin_metrics.csv`
- `results/temperature_extrapolation_baselines/predictions.csv`
- `results/temperature_extrapolation_neural_proxy/SUMMARY.md`
- `results/temperature_extrapolation_neural_proxy/summary.json`
- `results/temperature_extrapolation_neural_proxy/comparison.csv`
- copied presentation figures:
  - `presentation/figures/generated/temperature_extrapolation_baseline_comparison.png`
  - `presentation/figures/generated/temperature_extrapolation_error_by_temperature.png`
  - `presentation/figures/generated/temperature_extrapolation_example_curves.png`

### 14. In-pair temperature interpolation is an intentionally easy protocol with a strong floor

As of `2026-04-17`, a CPU-first same-pair interior-temperature interpolation
diagnostic has been added and run:

- script:
  - `scripts/evaluation/run_temperature_interpolation_baselines.py`
- bundle:
  - `results/temperature_interpolation_baselines/`

Protocol:

- combine maintained processed `train/val/test` supervised rows
- select pairs with at least `6` unique temperatures and at least `20 K` span
- sample `1,000` pairs for the local tiny benchmark from `10,263` eligible
  pairs
- keep each pair's lowest and highest temperatures in train
- hold out only interior temperatures for val/test
- selected set:
  - train / val / test rows: `6,780 / 1,174 / 2,089`
  - mean unique temperatures per pair: `10.043`
  - median unique temperatures per pair: `9`
  - median pair temperature span: `40 K`

Interior-temperature test results:

- `pair_piecewise_linear_T`:
  - `MAE 0.038`
  - `R^2 0.993`
  - slope sign accuracy `99.4%`
- `pair_vant_hoff`:
  - `MAE 0.043`
  - `R^2 0.997`
  - slope sign accuracy `99.3%`
- `pair_linear_T`:
  - `MAE 0.045`
  - `R^2 0.997`
  - slope sign accuracy `99.3%`
- `pair_nearest_T`:
  - `MAE 0.195`
  - `R^2 0.986`
  - slope sign accuracy `88.8%`
- `RF(Morgan+T)`:
  - `MAE 0.667`
  - `R^2 0.876`
  - slope sign accuracy `95.9%`
- `pair_mean`:
  - `MAE 0.383`
  - `R^2 0.965`
  - slope sign accuracy `0.0%`

Accepted interpretation:

- this is not yet a neural `TGNN-Solv` vs `DirectGNN` retraining result
- it proves that same-pair interior-temperature interpolation is very easy
  when pair-specific curve information is available
- future neural results on this split must be compared against the strong
  per-pair interpolation floor, not only against each other
- a meaningful TGNN/DirectGNN win condition here is curve-shape fidelity and
  approach to the Van't Hoff / piecewise-linear floor, not merely beating
  RF(Morgan+T)
- generated split CSVs for neural follow-up:
  - `results/temperature_interpolation_baselines/splits/train_inpair.csv`
  - `results/temperature_interpolation_baselines/splits/val_inpair.csv`
  - `results/temperature_interpolation_baselines/splits/test_inpair.csv`

Primary artifacts:

- `results/temperature_interpolation_baselines/SUMMARY.md`
- `results/temperature_interpolation_baselines/summary.json`
- `results/temperature_interpolation_baselines/metrics_by_model.csv`
- `results/temperature_interpolation_baselines/shape_summary.csv`
- `results/temperature_interpolation_baselines/test_temperature_bin_metrics.csv`
- `results/temperature_interpolation_baselines/predictions.csv`
- copied presentation figures:
  - `presentation/figures/generated/temperature_interpolation_baseline_comparison.png`
  - `presentation/figures/generated/temperature_interpolation_error_by_temperature.png`
  - `presentation/figures/generated/temperature_interpolation_example_curves.png`

### 15. Enhanced TGNN temperature-extrapolation plumbing works, but the objective is not solved

As of `2026-04-18`, the enhanced local-MPS temperature-extrapolation path has
three completed proxy runs on the same low-T/high-T split:

- enhanced TGNN baseline:
  - `MAE 2.016`
  - `R^2 0.012`
- enhanced TGNN + separate IDAC stream + local Van't Hoff curve losses:
  - `MAE 2.029`
  - `R^2 0.0069`
- enhanced TGNN + separate IDAC stream + local curve losses + precomputed
  350 K Van't Hoff anchor rows:
  - `MAE 1.986`
  - `R^2 0.025`

Current maintained comparison on this protocol:

- pair Van't Hoff closed-form fit:
  - `MAE 0.368`
  - `R^2 0.887`
- `DirectGNN` proxy:
  - `MAE 1.619`
  - `R^2 0.283`
- old `TGNN-Solv` proxy:
  - `MAE 1.945`
  - `R^2 0.060`

Accepted interpretation:

- expanded IDAC plumbing is now correct for local proxy work:
  - IDAC is passed through a separate gamma-only auxiliary loader, not appended
    to the main SLE train CSV
- pair-curve losses are implemented and runnable:
  - `pair_temp_delta`
  - `vant_hoff_slope`
  - `vant_hoff_intercept`
  - `vh_anchor`
- precomputed Van't Hoff anchor distillation is directionally positive
  (`2.029 -> 1.986` MAE), but still not enough to beat the old TGNN proxy
  (`1.945`) or DirectGNN (`1.619`)
- this is a negative/partial result for the current objective, not a reason to
  discard the infrastructure
- do not spend full `50/200/50` CUDA budget on this temperature protocol until
  a short proxy beats `MAE 1.945`

Primary artifacts:

- `scripts/data/build_vant_hoff_anchor_split.py`
- `results/temperature_extrapolation_enhanced_proxy/SUMMARY.md`
- `results/temperature_extrapolation_enhanced_proxy/summary.json`
- `results/temperature_extrapolation_enhanced_proxy/vh_anchor_350_summary.json`
- `results/temperature_extrapolation_enhanced_proxy/splits/train_low_vh_anchor_350.csv`
- `checkpoints/temperature_extrapolation_enhanced/tgnn_entropy_rescue_idacstream_vhanchor350_seed42_p1-4-0.pt`
- `logs/temperature_extrapolation_enhanced/tgnn_entropy_rescue_idacstream_vhanchor350_seed42_p1-4-0/`

### 16. Structural extrapolation error is heterogeneous, not a uniform TGNN failure

As of `2026-04-18`, a prediction-only structural-extrapolation diagnosis has
been added on top of the aligned scaffold prediction slices:

- script:
  - `scripts/analysis/run_structural_extrapolation_diagnosis.py`
- bundle:
  - `results/structural_extrapolation_diagnosis/`
- inputs:
  - `results/prediction_error_slices_latest/DirectGNN/`
  - `results/prediction_error_slices_latest/TGNN_MPNN/`
  - `results/prediction_error_slices_latest/RF_hybrid/`

Current aligned scaffold result:

- row count: `5,826`
- pair count: `823`
- `DirectGNN`:
  - `MAE 1.652`
  - median absolute error `1.245`
  - P90 absolute error `3.631`
- `TGNN_MPNN`:
  - `MAE 1.741`
  - median absolute error `1.440`
  - P90 absolute error `3.468`
- `RF_hybrid`:
  - `MAE 1.712`
  - median absolute error `1.350`
  - P90 absolute error `3.609`

TGNN-vs-DirectGNN deltas:

- mean abs-error delta: `+0.089`
- median abs-error delta: `+0.081`
- TGNN better on `46.4%` of rows
- TGNN better on `46.9%` of pairs
- catastrophic pair fraction (`pair MAE > 3`):
  - DirectGNN: `17.1%`
  - TGNN_MPNN: `15.4%`

Important slices:

- novelty bins:
  - TGNN is worse in the `pair_tanimoto 0.6-0.8` bin:
    `+0.428 MAE` relative to DirectGNN
  - TGNN is slightly better in the lowest novelty bin `<=0.3`:
    `-0.072 MAE`
  - TGNN is also better in the small high-similarity `>0.8` bin:
    `-0.210 MAE`, but this bin has only `57` rows
- target-value bins:
  - TGNN is worse in the extreme low-solubility tail `ln_x2 <= -15`:
    `+0.440 MAE`
  - TGNN is approximately tied for `ln_x2 > -3`:
    `-0.004 MAE`
- chemistry classes:
  - largest TGNN regressions:
    - `polyaromatic`: `+1.125 MAE`, but only `52` rows
    - `other`: `+1.022 MAE`, `130` rows
    - `oxygenated`: `+0.304 MAE`, `444` rows
  - TGNN improves `sulfur_or_phosphorus`:
    `-0.053 MAE`
- solvent types:
  - TGNN is worse in aromatic solvents:
    `+0.740 MAE`, `130` rows
  - TGNN is essentially tied on water:
    `+0.004 MAE`, with TGNN better on `51.5%` of water rows
  - TGNN improves hydrocarbon solvents:
    `-0.232 MAE`
  - TGNN improves carboxylic-acid solvents:
    `-0.277 MAE`, but only `35` rows

Accepted interpretation:

- structural extrapolation remains a shared failure mode across DirectGNN,
  RF, and TGNN
- TGNN's global physics tax is small on average, but not uniform
- the physics path reduces some catastrophic pair errors while losing median
  accuracy in several slices
- water is not currently the main explanation for the TGNN-vs-DirectGNN gap on
  scaffold; both models are similarly weak on water rows
- immediate structural work should prioritize:
  - polyaromatic / "other" coarse classes
  - aromatic-solvent slices
  - understanding why TGNN loses in the `0.6-0.8` pair-Tanimoto bin
  - using TGNN/DirectGNN complementarity for ensembling or routing diagnostics

Primary artifacts:

- `results/structural_extrapolation_diagnosis/SUMMARY.md`
- `results/structural_extrapolation_diagnosis/summary.json`
- `results/structural_extrapolation_diagnosis/novelty_bins_pair_tanimoto.csv`
- `results/structural_extrapolation_diagnosis/target_value_bins.csv`
- `results/structural_extrapolation_diagnosis/chemistry_class_deltas.csv`
- `results/structural_extrapolation_diagnosis/solvent_type_deltas.csv`
- `results/structural_extrapolation_diagnosis/pair_level_deltas.csv`
- `results/structural_extrapolation_diagnosis/top_target_rescues.csv`
- `results/structural_extrapolation_diagnosis/top_target_regressions.csv`

## Current Engineering Constraints

- Full `DirectGNN` split diagnostics on local MPS are runtime-limited.
- Short `solute` proxy attempts showed:
  - `bs=2048`: MPS OOM
  - `bs=1024`: no useful artifact
  - `bs=768`: about `19-21 s/batch`, around `46 min/epoch`
- Fair `DirectGNN` retraining on harder splits should be moved to CUDA or
  preceded by graph/data-path optimization.

Primary artifact:

- `logs/directgnn_split_diag/directgnn_solute_proxy6_bs768.stdout.log`

## Open Questions

- Replace or revise the maintained scaffold protocol:
  - seed-averaged random scaffold-group split?
  - target-drift-constrained group split?
- Close full-budget `50/200/50` comparisons on stronger hardware.
- Revalidate FastSolv after finite-target filtering.
- Determine whether TIMP gains in probe metrics can be converted into better
  final MAE once the next bottleneck is addressed.
- Finish aligned external benchmarking against FastSolv/SolProp on the same
  maintained protocols.

## Artifact Map

- Main long-form narrative:
  - `main.tex`
- Main presentation:
  - `presentation/seminar_talk.tex`
  - `presentation/talk_text.md`
  - `presentation/talk_text_verbatim.md`
- Split diagnostics:
  - `results/metric_diagnosis_bundle/`
  - `results/metric_diagnosis_scaffold_bias/`
  - `results/extended_split_diagnostics/`
- Prediction error slices:
  - `results/directgnn_error_structure/`
  - `results/prediction_error_slices/`
  - `results/prediction_error_slices_latest/`
  - `results/structural_extrapolation_diagnosis/`
- Temperature extrapolation diagnostics:
  - `results/temperature_extrapolation_baselines/`
  - `results/temperature_extrapolation_neural_proxy/`
  - `results/temperature_extrapolation_enhanced_proxy/`
- Temperature interpolation diagnostics:
  - `results/temperature_interpolation_baselines/`
- KNN/modelability diagnostics:
  - `results/knn_modelability_smoke/`
  - `results/knn_subset_compare/`
- External baselines:
  - `results/external_baselines/solute/`
  - `results/external_baselines/pair_random/`

## Incident Log

### 2026-04-16

- Created project memory as the canonical cross-agent state file.
- Confirmed that current `scaffold` test is left-tail biased relative to
  `scaffold_random`.
- Confirmed that `solute` remains almost as hard as `scaffold`, while
  `pair_random` is much easier.
- Confirmed `SolProp native quick` reproduces the same split ordering.
- Confirmed `FastSolv` all-NaN predictions are caused by non-finite converted
  `logS` targets corrupting scaling buffers, not just by descriptor NaNs.
- Patched `scripts/run_fastsolv.py` to filter non-finite converted `logS`
  targets before scaling and validated the fix on a tiny smoke retrain with
  finite checkpoints and finite predictions.
- Integrated the authors' solvent density table into `_density_map()`, which
  removed most `NaN` `logS` conversions caused by missing solvent molarity.
- Completed a full unit-conversion audit and accepted that conversion accuracy
  is not the main project bottleneck; the remaining issue is boundary/coverage
  behavior for external `logS` baselines on exact `ln_x2 = 0` rows and
  unsupported solvent molarity cases.
- Updated canonical benchmark bundle contracts so all maintained external
  baseline reports explicitly separate headline `ln_x2` metrics from finite-only
  `logS` subset metrics, and fixed the documented policy for exact `ln_x2 = 0`
  rows.
- Recovered `SolProp native` contract-v2 bundles from existing quick
  checkpoints for both `solute` and `pair_random`, including explicit
  `evaluation_subsets` and finite-only `logS` metrics.
- Started full `SolProp calibrated` contract-v2 reruns on `solute` and
  `pair_random`; as of the latest update they are still actively computing
  upstream predictions on full `train/val/test`.
- Completed maintained `FastSolv` contract-v2 rerun on `solute` with finite
  predictions but weak hard-split metrics:
  - `val`: `MAE 1.909`, `R^2 0.238`
  - `test`: `MAE 1.941`, `R^2 0.226`
- Completed `SolProp calibrated` contract-v2 rerun on `pair_random`; the
  calibrated adapter improved over raw upstream predictions but remained much
  weaker than native retraining:
  - raw test: `MAE 2.357`, `R^2 -0.644`
  - calibrated test: `MAE 1.912`, `R^2 0.172`
- Completed `SolProp calibrated` contract-v2 rerun on `solute`; the
  temperature-aware calibrated adapter again remained much weaker than native
  retraining:
  - raw test: `MAE 2.361`, `R^2 -0.465`
  - calibrated test: `MAE 2.340`, `R^2 -0.176`
- Started a controlled low-priority `FastSolv` full rerun on `pair_random`
  under single-threaded BLAS caps to limit CPU contention while the remaining
  `SolProp` calibrated `solute` rerun is still active.
- Completed that `FastSolv` `pair_random` rerun; the wrapper now runs
  end-to-end but the metrics are very poor:
  - `val`: `MAE 2.834`, `R^2 -0.414`
  - `test`: `MAE 2.910`, `R^2 -0.594`
- Started tail-aware scaffold diagnostics in
  `results/tail_diagnostics/` to quantify per-bin error and trimmed metrics for
  `DirectGNN`, `TGNN MPNN`, RF hybrid, and external baselines; the first
  interactive run was interrupted when the IDE session hung, and a rerun was
  started on `2026-04-17`.

### 2026-04-17

- Added a maintained source-uncertainty audit pipeline:
  - `scripts/analysis/run_source_uncertainty_audit.py`
  - `src/tgnn_solv/data/source_uncertainty.py`
- Extended `load_bigsoldb(...)` with `preserve_source_detail=True` so raw
  detailed `Source` identifiers can be preserved through the maintained BigSolDB
  conversion path without changing the default loader contract.
- Added `notebooks/data/metadata/bigsoldb_source_method_overrides.csv` as the
  tracked manual override surface for future source-level method/sigma curation.
- Confirmed that BigSolDB source identifiers are highly fragmented:
  top `50` sources cover only `9.52%` of maintained supervised rows.
- Exported the first reproducible source-prior bundle under
  `results/source_uncertainty_audit/`.
- Confirmed that pattern-only heuristics are enough for coarse priors such as
  `multi_temperature_primary` vs `single_temperature_primary`, but not enough
  for defensible fine-grained experimental method labels without metadata/text
  enrichment.
- Switched the source-uncertainty metadata path to an official-API-first
  workflow:
  - `Semantic Scholar` first
  - then `OpenAlex`
  - then `Crossref`
  - optional `Unpaywall` only when a real email is provided
- Added `--metadata-csv` reuse support to
  `scripts/analysis/run_source_uncertainty_audit.py` so reviewed bundles can be
  rebuilt from cached metadata without re-hitting the network.
- Fixed two bugs in the reviewed source-audit path:
  - override-column rename bug in `_build_classification_table(...)`
  - false manual overrides caused by `NaN` override fields being treated as the
    string `"nan"` in `classify_source_method(...)`
- Rebuilt the reviewed source-prior bundle under
  `results/source_uncertainty_audit_reviewed/` using cached metadata from
  `results/source_uncertainty_audit_metadata/source_metadata.csv`.
- Added the first text-confirmed manual overrides to
  `notebooks/data/metadata/bigsoldb_source_method_overrides.csv`, including:
  - `gravimetric_equilibrium` for:
    - `10.1016/j.molliq.2018.12.081`
    - `10.1021/acs.jced.8b00811`
    - `10.1021/acs.jced.8b00430`
  - `polythermal_visual` for:
    - `10.1016/j.cjche.2020.07.022`
- Current reviewed source-prior row mix is:
  - `multi_temperature_primary`: `92,556`
  - `unknown`: `9,530`
  - `gravimetric_equilibrium`: `2,492`
  - `computed_or_modeled`: `2,249`
  - `polythermal_visual`: `471`
  - `single_temperature_primary`: `318`
  - `compilation_or_secondary`: `281`
  - `unknown_primary`: `237`
  - `dsc`: `153`
- Restarted tail-aware scaffold diagnostics with explicit progress logging and a
  smaller RF budget in `results/tail_diagnostics_fast_v2/`:
  - `rf_n_estimators=50`
  - `rf_max_depth=20`
  - `rf_n_jobs=1`
  - completed successfully with `7` bundles:
    - `DirectGNN`, `TGNN_MPNN`, `RF_hybrid_refit` on `scaffold`
    - `SolProp_native`, `FastSolv` on `solute`
    - `SolProp_native`, `SolProp_calibrated` on `pair_random`
  - key scaffold trimmed-vs-all result:
    - `DirectGNN`: `MAE 1.652 -> 1.588`, `R^2 0.478 -> 0.489`
    - `TGNN_MPNN`: `MAE 1.741 -> 1.674`, `R^2 0.438 -> 0.456`
    - `RF_hybrid_refit`: `MAE 1.712 -> 1.645`, `R^2 0.450 -> 0.458`
  - accepted interpretation:
    - the extreme left tail `ln_x2 <= -15` is genuinely hard
    - but it is only `60` scaffold rows and removing it improves headline
      scaffold `R^2` by only about `0.01–0.02`
    - therefore the left tail is a real contributor, but not the main sole
      explanation for the low scaffold `R^2`
- Strengthened source-method heuristics:
  - explicit measurement-method keywords now outrank generic
    `modeling/simulation` phrases
  - author-name tokens such as `Acree` and `Yalkowsky` were removed from
    compilation heuristics because they produced false positives on primary
    experimental papers
- Expanded manual text-confirmed source overrides to `27` rows in
  `notebooks/data/metadata/bigsoldb_source_method_overrides.csv`
- Rebuilt `results/source_uncertainty_audit_reviewed/` after those fixes.
  Current row-weighted source-prior mix:
  - `multi_temperature_primary`: `92,693`
  - `unknown`: `9,530`
  - `gravimetric_equilibrium`: `2,949`
  - `computed_or_modeled`: `2,089`
  - `polythermal_visual`: `471`
  - `single_temperature_primary`: `318`
  - `unknown_primary`: `237`
- Current accepted interpretation for source priors:
  - official metadata plus text-confirmed overrides already recover a useful
    pocket of trustworthy `gravimetric` and `laser-monitoring` sources
  - but the corpus still remains dominated by `multi_temperature_primary`
    coarse priors rather than exact method labels, so weighted-loss work should
    treat current sigmas as source priors, not literal pointwise error bars
- Added an optional maintained weighted-solubility-loss prototype driven by the
  reviewed source-prior bundle:
  - config surface added in `src/tgnn_solv/config.py`:
    - `use_source_uncertainty_weights`
    - `source_uncertainty_csv`
    - `source_uncertainty_weight_mode`
    - sigma / min-max weight controls
  - dataframe merge helper added in
    `src/tgnn_solv/data/source_uncertainty.py`
  - `TGNNSolvDataset` / `make_loader(...)` now attach:
    - `source_sigma_ln_x2`
    - `source_solubility_weight`
    - optional `source_method_guess`
    - optional `source_detail`
  - `TGNNSolvLoss` now uses weighted Huber / weighted direct-NLL for the
    solubility terms when the config flag is enabled
  - `DirectGNNTrainer` now uses the same per-row weights for its primary Huber
    loss when the flag is enabled
- Maintained training entry points and major training-oriented wrappers now pass
  the source-uncertainty loader kwargs through:
  - `scripts/train.py`
  - `scripts/train_directgnn.py`
  - `scripts/run_full_budget_experiment.py`
  - `src/tgnn_solv/optuna_tuner.py`
  - `scripts/run_ablation.py`
- Verified merge safety on maintained processed splits:
  - reviewed uncertainty bundle has `0` duplicate merge keys on
    `(solute_smiles, solvent_smiles, temperature, ln_x2)`
  - all unmatched rows in `train/val/test` are `has_solubility=False`
  - all supervised rows match successfully
- Validation status for the weighted-loss prototype:
  - `pytest tests/test_source_uncertainty.py -v` now passes `9` tests
  - real loader smoke on `notebooks/data/processed/train.csv` succeeds and
    emits finite `source_sigma_ln_x2` / `source_solubility_weight` targets
  - simple loss smoke confirms the weighted solubility loss path is active
- `2026-04-17`: added maintained source-weighted config variants:
  - `configs/paper_config_tuned_source_weighted.yaml`
  - `configs/paper_config_directgnn_tuned_source_weighted.yaml`
- `2026-04-17`: attempted full maintained scaffold weighted proxy on local MPS
  and aborted it as a runtime incident:
  - `DirectGNN` with full processed `train/val/test`, `6` epochs, `batch_size=64`
    showed about `1.7–2.3 s/batch` over `1,734` train batches/epoch and was
    interrupted after `54` batches
  - retrying `DirectGNN` with `batch_size=256` still showed about
    `5–6 s/batch` over `433` train batches/epoch and was interrupted after
    `12` batches
  - accepted interpretation:
    - local full-split weighted ablation on current MPS path is too slow to be
      a practical diagnostic protocol
    - matched subset ablations are the right local path until a faster device
      or faster graph/data path is available
- `2026-04-17`: completed a matched scaffold-subset source-weighted ablation on
  a sampled `1000 / 200 / 400` subset from maintained `solute_scaffold`
  `train/val/test` with seed `42`:
  - subset data:
    - `results/source_weighted_proxy_subset/data/train_scaffold1000_200_400_seed42.csv`
    - `results/source_weighted_proxy_subset/data/val_scaffold1000_200_400_seed42.csv`
    - `results/source_weighted_proxy_subset/data/test_scaffold1000_200_400_seed42.csv`
  - compact artifact bundle:
    - `results/source_weighted_proxy_subset/summary.json`
    - `results/source_weighted_proxy_subset/comparison.csv`
    - `results/source_weighted_proxy_subset/comparison.md`
  - `DirectGNN`, matched `6`-epoch subset run:
    - unweighted:
      - `MAE 2.120`
      - `RMSE 2.862`
      - `R^2 0.210`
      - log dir:
        `logs/source_weighted_proxy_subset/directgnn_unweighted_subset_seed42`
    - source-weighted:
      - `MAE 2.331`
      - `RMSE 3.005`
      - `R^2 0.129`
      - delta vs unweighted:
        - `+0.211 MAE`
        - `-0.081 R^2`
      - log dir:
        `logs/source_weighted_proxy_subset/directgnn_weighted_subset_seed42`
  - `TGNN-Solv`, matched `1/4/1` subset run:
    - unweighted:
      - `MAE 2.393`
      - `RMSE 3.424`
      - `R^2 -0.131`
      - log dir:
        `logs/source_weighted_proxy_subset/tgnn_unweighted_subset_seed42`
    - source-weighted:
      - `MAE 2.412`
      - `RMSE 3.464`
      - `R^2 -0.157`
      - delta vs unweighted:
        - `+0.019 MAE`
        - `-0.027 R^2`
      - log dir:
        `logs/source_weighted_proxy_subset/tgnn_weighted_subset_seed42`
  - accepted interpretation:
    - on this matched scaffold-subset ablation, the current heuristic
      source-prior weighting does not improve either `DirectGNN` or
      `TGNN-Solv`
    - it is currently a negative result, not a maintained training win
    - any future weighting work should probably improve the prior quality first
      rather than pushing the current heuristic directly into headline runs
- `2026-04-17`: completed maintained `DirectGNN` scaffold error-structure
  diagnostics under:
  - `results/directgnn_error_structure/summary.json`
  - `results/directgnn_error_structure/SUMMARY.md`
  - `results/directgnn_error_structure/train_val_test_metrics.json`
  - `results/directgnn_error_structure/pair_errors.csv`
  - `results/directgnn_error_structure/chemistry_coarse_class_metrics.csv`
  - `results/directgnn_error_structure/chemistry_flag_metrics.csv`
  - `results/directgnn_error_structure/nearest_neighbor_error_summary.json`
- accepted numbers from that bundle:
  - actual checkpoint metrics:
    - train:
      - `MAE 1.062`
      - `R^2 0.703`
    - val:
      - `MAE 1.854`
      - `R^2 0.350`
    - test:
      - `MAE 1.652`
      - `R^2 0.478`
  - actual generalization gap:
    - `test - train MAE = +0.590`
    - interpretation:
      - the maintained `DirectGNN` checkpoint is not just mildly underfit
      - there is a real train-to-test generalization gap on the scaffold split
  - pair-level error concentration on scaffold test:
    - `823` unique `(solute, solvent)` pairs
    - median pair MAE: `1.261`
    - `P90 = 3.752`
    - `P95 = 4.507`
    - pairs with `MAE < 1.0`: `41.7%`
    - pairs with `MAE > 3.0`: `17.1%`
    - accepted interpretation:
      - test error is concentrated in a minority of difficult pairs rather than
        spread uniformly
  - chemistry slices:
    - largest coarse class:
      - `heterocycle`
      - `n_rows = 3,138`
      - `MAE 1.521`
      - `R^2 0.521`
    - worst coarse class by MAE:
      - `halogenated_aromatic`
      - `n_rows = 1,784`
      - `MAE 1.945`
      - `R^2 0.380`
    - useful flag slices:
      - `has_halogen`: `MAE 1.916`
      - `has_heterocycle`: `MAE 1.664`
      - `has_nh`: `MAE 1.465`
    - accepted interpretation:
      - halogenated aromatic solutes are a real weakness of the maintained
        scaffold `DirectGNN` checkpoint
      - nitrogen-containing solutes are not uniformly hard; the model performs
        materially better on `has_nh` slices than on halogenated ones
  - nearest-train-neighbor linkage using the existing pair-Tanimoto bundle:
    - matched rows: `5,826 / 5,826`
    - Pearson(`pair_tanimoto`, `abs_error`) = `-0.161`
    - Spearman(`pair_tanimoto`, `abs_error`) = `-0.159`
    - at `pair_tanimoto >= 0.5`:
      - `n = 1,983`
      - `MAE 1.426`
    - at `pair_tanimoto >= 0.8`:
      - `n = 57`
      - `MAE 1.188`
    - accepted interpretation:
      - DirectGNN error does improve for test rows with closer train neighbors
      - but the effect is moderate rather than dominant, so coverage explains
        part of the scaffold difficulty, not all of it
- `2026-04-17`: added and ran a maintained prediction-only cross-model error
  slicing utility:
  - script:
    - `scripts/evaluation/run_prediction_error_slices.py`
  - plotting script:
    - `scripts/evaluation/plot_prediction_error_slices.py`
  - bundle:
    - `results/prediction_error_slices/`
  - inputs:
    - `results/tail_diagnostics_fast_v2/directgnn_scaffold_predictions.csv`
    - `results/tail_diagnostics_fast_v2/tgnn_mpnn_scaffold_predictions.csv`
    - `results/tail_diagnostics_fast_v2/rf_hybrid_scaffold_predictions.csv`
  - key aligned test metrics:
    - `DirectGNN`: `MAE 1.652`, `R^2 0.478`
    - `RF_hybrid`: `MAE 1.712`, `R^2 0.450`
    - `TGNN_MPNN`: `MAE 1.741`, `R^2 0.438`
  - paired deltas versus `DirectGNN`:
    - `TGNN_MPNN`: `+0.089` mean abs-error delta, better on `46.4%` rows
    - `RF_hybrid`: `+0.060` mean abs-error delta, better on `48.2%` rows
  - accepted interpretation:
    - DirectGNN remains the best current scaffold model by global MAE/R^2
    - TGNN and RF still win on a large minority of rows, so model errors are
      correlated but not interchangeable
    - halogenated-aromatic chemistry, especially with hydrocarbon solvents, is
      a high-error slice worth targeting in the next analysis
  - presentation-ready PNG/PDF figures were generated under:
    - `results/prediction_error_slices/figures/`
    - `presentation/figures/generated/prediction_slice_*.{png,pdf}`
- `2026-04-17`: added and ran a CPU-first same-pair temperature-extrapolation
  baseline diagnostic:
  - script:
    - `scripts/evaluation/run_temperature_extrapolation_baselines.py`
  - bundle:
    - `results/temperature_extrapolation_baselines/`
  - protocol:
    - low-T fitting rows: `T <= 310 K`
    - high-T test rows: `T >= 330 K`
    - `1,751` same `(solute, solvent)` pairs
    - train / val / test rows: `7,120 / 1,751 / 3,343`
  - key high-T test results:
    - `pair_vant_hoff`: `MAE 0.368`, `R^2 0.887`, direction accuracy `99.0%`
    - `pair_linear_T`: `MAE 0.414`, `R^2 0.850`, direction accuracy `99.0%`
    - `RF(Morgan+T)`: `MAE 1.290`, `R^2 0.658`, direction accuracy `40.4%`
    - `pair_last_low_T`: `MAE 1.202`, `R^2 0.694`, direction accuracy `1.0%`
    - `pair_mean`: `MAE 1.456`, `R^2 0.561`, direction accuracy `1.1%`
  - accepted interpretation:
    - this baseline bundle was not yet a neural TGNN-vs-DirectGNN result
      at creation time; the follow-up neural proxy is recorded below
    - it is strong evidence that explicit thermodynamic temperature structure
      is present and exploitable in the corpus
    - the generated split CSVs under
      `results/temperature_extrapolation_baselines/splits/` are the next input
      for fair CUDA TGNN/DirectGNN retraining
  - presentation-ready figures were generated under:
    - `results/temperature_extrapolation_baselines/figures/`
    - `presentation/figures/generated/temperature_extrapolation_*.{png,pdf}`
- `2026-04-17`: completed the missing neural proxy numbers for temperature
  extrapolation finding 13 on the existing low-T/high-T split:
  - split:
    - `results/temperature_extrapolation_baselines/splits/train_low.csv`
    - `results/temperature_extrapolation_baselines/splits/val_low.csv`
    - `results/temperature_extrapolation_baselines/splits/test_high.csv`
  - bundle:
    - `results/temperature_extrapolation_neural_proxy/`
  - `DirectGNN`:
    - config: `configs/paper_config_directgnn_tuned.yaml`
    - budget: `10` epochs, batch size `256`, seed `42`, local `mps`
    - high-T test: `MAE 1.619`, `R^2 0.283`, `RMSE 2.167`
    - runtime: `1089 s`
    - log dir:
      - `logs/temperature_extrapolation/directgnn_lowT_highT_proxy_seed42_ep10/`
  - `TGNN-Solv`:
    - config: `configs/paper_config_tuned.yaml`
    - budget: `1/8/1` phases, batch size `256`, seed `42`, local `mps`
    - high-T test: `MAE 1.945`, `R^2 0.060`, `RMSE 2.481`
    - runtime: `1433 s`
    - log dir:
      - `logs/temperature_extrapolation/tgnn_solv_lowT_highT_proxy_seed42_p1-8-1/`
  - accepted interpretation:
    - on this short local proxy, `DirectGNN` beats `TGNN-Solv` by `0.326 MAE`
    - both neural models are much weaker than the per-pair Van't Hoff baseline
      (`MAE 0.368`) and RF(Morgan+T) (`MAE 1.290`) from the same finding
    - this result should be treated as a training/objective diagnostic and not
      as a full-budget final physics-vs-direct conclusion
- `2026-04-17`: added and ran a CPU-first same-pair
  interior-temperature interpolation diagnostic:
  - script:
    - `scripts/evaluation/run_temperature_interpolation_baselines.py`
  - bundle:
    - `results/temperature_interpolation_baselines/`
  - protocol:
    - endpoints of each selected pair's temperature range stay in train
    - only interior temperatures are held out for val/test
    - `1,000` pairs sampled from `10,263` eligible pairs
    - train / val / test rows: `6,780 / 1,174 / 2,089`
  - key interior-T test results:
    - `pair_piecewise_linear_T`: `MAE 0.038`, `R^2 0.993`, slope sign accuracy `99.4%`
    - `pair_vant_hoff`: `MAE 0.043`, `R^2 0.997`, slope sign accuracy `99.3%`
    - `pair_linear_T`: `MAE 0.045`, `R^2 0.997`, slope sign accuracy `99.3%`
    - `RF(Morgan+T)`: `MAE 0.667`, `R^2 0.876`, slope sign accuracy `95.9%`
  - accepted interpretation:
    - this is not yet a neural TGNN-vs-DirectGNN result
    - in-pair interior-temperature interpolation has a very strong per-pair
      baseline floor, so future neural results must be judged against
      Van't Hoff / piecewise interpolation, not only RF or each other
    - the generated split CSVs under
      `results/temperature_interpolation_baselines/splits/` are the next input
      for fair CUDA TGNN/DirectGNN interpolation retraining
  - presentation-ready figures were generated under:
    - `results/temperature_interpolation_baselines/figures/`
    - `presentation/figures/generated/temperature_interpolation_*.{png,pdf}`
- `2026-04-17`: expanded the existing IDAC/ThermoML path instead of adding a
  separate standalone IDAC project:
  - source code:
    - `scripts/data/extract_idac_from_thermoml.py`
    - `src/tgnn_solv/data/thermoml_idac.py`
    - `src/tgnn_solv/data/sources.py`
  - accepted implementation decision:
    - TGNN-Solv already has `gamma_inf` auxiliary supervision through
      `DataBuilder.add_gamma()`, `load_idac()`, trainer Phase 1, and
      `TGNNSolvLoss`
    - the right near-term path is to expand the maintained IDAC CSV source,
      not to create a parallel toy PINN repository
  - extractor changes:
    - added official NIST ThermoML Archive page discovery via
      `--nist-current-archive-pages`
    - added issue-index expansion via `--expand-journal-issues`
    - added journal/year/page/DOI filters, JSON cache support, DOI output,
      and audit JSON output
  - smoke artifacts:
    - `results/idac_thermoml_smoke/idac_current_pages_max80.csv`
    - `results/idac_thermoml_smoke/discovered_dois_max80.txt`
    - `results/idac_thermoml_smoke/audit_max80.json`
    - `results/idac_thermoml_smoke/discovery_jced_2017_first2_audit.json`
    - `tmp/thermoml_json_smoke/`
  - smoke result:
    - current NIST pages exposed `65` DOI links
    - `65` ThermoML JSON records were fetched
    - `49` usable IDAC rows were extracted from `1` DOI
    - extracted rows covered `8` unique pairs with no missing solute/solvent
      SMILES
    - combined with the starter `notebooks/data/raw/idac.csv`, this would
      increase the local IDAC pool from `404` rows / `138` pairs / `9` DOI to
      `453` rows / `146` pairs / `10` DOI before broader crawling
  - validation:
    - `python -m py_compile scripts/data/extract_idac_from_thermoml.py`
    - `python -m pytest tests/test_thermoml_idac.py tests/test_sources.py -q`
      passed (`6 passed`)
  - caveat:
    - `thermo`, `chemicals`, and `lxml` were not installed in the active
      `tgnn-solv` environment, so UNIFAC pseudo-IDAC was not implemented in
      this pass
- `2026-04-17`: consolidated the broad NIST ThermoML IDAC crawl and built
  fair fixed-split auxiliary-supervision artifacts:
  - input from completed crawl:
    - `notebooks/data/raw/idac_nist_2015_2019.csv`
    - `results/idac_thermoml/nist_2015_2019_audit.json`
    - `results/idac_thermoml/nist_2015_2019_dois.txt`
  - new tooling:
    - `scripts/analysis/audit_idac_expansion.py`
    - `scripts/data/attach_idac_aux_to_fixed_splits.py`
    - `scripts/analysis/audit_dcp_correction.py`
    - `scripts/analysis/scan_thermoml_property_inventory.py`
    - `scripts/analysis/summarize_physics_supervision_readiness.py`
  - consolidated IDAC outputs:
    - `notebooks/data/raw/idac_expanded_raw.csv`
    - `notebooks/data/raw/idac_expanded.csv`
    - `results/idac_expansion_audit/summary.json`
  - IDAC expansion result:
    - exact-deduplicated raw rows: `14,910`
    - aggregated training rows: `14,900`
    - unique IDAC pairs: `3,145`
    - unique DOI count: `63`
    - conflicting pair-temperature groups at std threshold `0.5`: `0`
    - exact overlap with current SLE `(solute, solvent)` pairs: `0%`
  - important protocol caveat:
    - preparing all data with expanded IDAC before splitting created
      `notebooks/data/processed_idac_expanded/`
    - this changed the supervised scaffold composition to
      `100,432 / 3,933 / 3,922` solubility rows in train/val/test
    - therefore this bundle is diagnostic only, not a fair benchmark input
  - fair fixed-split aux bundle:
    - `notebooks/data/processed_idac_expanded_train_aux/`
    - canonical supervised scaffold rows are preserved:
      `96,798 / 5,663 / 5,826`
    - new expanded IDAC aux-only rows added to scaffold train: `14,496`
    - starter gamma rows skipped as already present: `404`
  - refreshed prediction-slice bundle:
    - `results/prediction_error_slices_latest/`
    - DirectGNN: `MAE 1.652`, `R^2 0.478`, median pair MAE `1.261`
    - TGNN_MPNN: `MAE 1.741`, `R^2 0.438`, median pair MAE `1.443`
    - RF_hybrid: `MAE 1.712`, `R^2 0.450`, median pair MAE `1.394`
    - TGNN_MPNN has fewer catastrophic pair errors above `3.0` MAE
      (`15.4%`) than DirectGNN/RF (`17.1%`), despite worse mean MAE
  - train/test gap retained from DirectGNN structure diagnostics:
    - train MAE `1.062`, test MAE `1.652`
    - test-minus-train MAE gap `0.590`
  - dCp audit:
    - `results/dcp_correction_audit/summary.json`
    - current Joback/GC `dCp_fus_gc` prior produces very large uncalibrated
      corrections; even the plausible single-component subset within `250 K`
      below `T_m` has median absolute correction `1.482` ln units
    - accepted interpretation: `dCp` has potential signal but must be clipped
      or calibrated before being used as a free SLE correction
  - ThermoML multitask inventory:
    - `results/thermoml_property_inventory/summary.json`
    - scanned `3,721` cached JSON files
    - GE-like labels include `213` excess molar enthalpy records
    - VLE-like labels include `2,074` vapor/sublimation pressure records and
      `850` boiling-temperature-at-pressure records
    - accepted interpretation: there is enough cached ThermoML signal to
      prototype GE/VLE auxiliary extractors after the IDAC ablation
  - combined operational report:
    - `results/physics_supervision_audit/summary.json`
    - `results/physics_supervision_audit/summary.md`
  - validation:
    - py_compile passed for all new scripts
    - `pytest tests/test_thermoml_idac.py tests/test_sources.py
      tests/test_unit_conversions.py tests/test_group_contribution.py -q`
      passed (`13 passed`)
- `2026-04-17`: added opt-in explicit-hydrogen graph support for water and
  other small molecules:
  - motivation:
    - canonical supervised water rows are retained, but the legacy graph for
      water is a one-node self-loop after H suppression
    - this is numerically valid but gives MPNN/TIMP no real O-H edges
  - implementation:
    - `src/tgnn_solv/features.py`:
      - `smiles_to_graph(..., explicit_h_small_molecules=True,
        explicit_h_max_heavy_atoms=3)`
      - default remains legacy H-suppressed behavior for checkpoint
        compatibility
      - when enabled, water becomes `3` nodes and `4` directed O-H edges with
        unchanged feature dimensions
    - `src/tgnn_solv/config.py`:
      - added `explicit_h_small_molecules`
      - added `explicit_h_max_heavy_atoms`
    - propagated the flags through datasets, loaders, training scripts,
      inference/domain/uncertainty/attribution helpers, Optuna, pretraining,
      and benchmark wrappers
    - added matched ablation configs:
      - `configs/paper_config_tuned_explicit_h_small.yaml`
      - `configs/paper_config_directgnn_tuned_explicit_h_small.yaml`
      - `configs/paper_config_tuned_tgnn_descriptors_explicit_h_small.yaml`
      - `configs/paper_config_directgnn_descriptors_explicit_h_small.yaml`
  - water/small-molecule audit:
    - `scripts/analysis/audit_water_small_molecule_graphs.py`
    - output bundle: `results/water_small_molecule_audit/`
    - canonical scaffold test:
      - water-solvent rows: `476 / 5,826` (`8.17%`)
      - small-solvent rows with `<=3` heavy atoms: `2,104 / 5,826`
        (`36.11%`)
      - mean water `ln_x2`: `-10.671`
      - mean non-water `ln_x2`: `-5.659`
    - current prediction-slice MAE on scaffold test water rows:
      - DirectGNN: `2.199`
      - TGNN_MPNN: `2.203`
      - RF_hybrid: `2.305`
    - graph topology check:
      - legacy water graph: `1` node, `1` self-loop edge, physical-edge
        nonzero fraction `0.0`
      - explicit-H water graph: `3` nodes, `4` directed O-H edges,
        physical-edge nonzero fraction `1.0`
  - docs updated:
    - `docs/data_preparation.md`
    - `docs/architecture.md`
    - `docs/config_cookbook.md`
    - `docs/script_reference.md`
    - `scripts/README.md`
    - `AGENTS.md`
  - validation:
    - py_compile passed for modified source/scripts
    - `pytest tests/test_water_graph.py tests/test_config.py
      tests/test_dataset.py tests/test_timp.py -q` passed (`38 passed`)
- `2026-04-17`: added opt-in entropy-coupled crystal fusion mode:
  - motivation:
    - current `FusionHead` predicted `T_m` and `dH_fus` independently
    - the proposed physics path is to predict fusion enthalpy and entropy and
      derive `T_m = dH_fus / dS_fus`
  - implementation:
    - `src/tgnn_solv/config.py`:
      - `fusion_output_mode`
      - `fusion_entropy_min`
      - `fusion_entropy_max`
      - `fusion_entropy_init`
      - `fusion_enthalpy_init`
    - `src/tgnn_solv/heads.py`:
      - `fusion_output_mode="entropy_coupled"` predicts `dH_fus` and
        `dS_fus`, derives `T_m`, and exposes `dS_fus`,
        `T_m_unclamped`, `dH_fus_raw`
      - default remains `fusion_output_mode="direct"` for checkpoint
        compatibility
    - `src/tgnn_solv/model.py`:
      - keeps `dS_fus` consistent on `fusion_params`,
        `solver_fusion_params`, and `corrected_fusion_params`
      - `return_intermediates=True` now includes `dS_fus`,
        `dS_fus_solver`, and `dS_fus_corrected`
    - `src/tgnn_solv/loss.py`:
      - Walden loss now uses explicit `dS_fus` when available
    - added config:
      - `configs/paper_config_tuned_entropy_fusion.yaml`
  - fusion-supervision audit:
    - `scripts/analysis/audit_fusion_supervision.py`
    - output bundle: `results/fusion_supervision_audit/`
    - canonical scaffold split:
      - train `T_m` rows: `66,558`, unique solutes: `14,443`
      - train `dH_fus` rows paired with `T_m`: `1,279`, unique solutes: `31`
      - validation/test direct `dH_fus` rows: `0`
      - train row-weighted median `dS_fus`: `53.93` J/(mol*K)
      - train Walden `[20,150]` outside fraction: `3.36%`
      - canonical train/val/test unique entropy records: `31`
    - accepted interpretation:
      - entropy coupling is a useful structural regularizer
      - it does not replace the need to expand direct `dH_fus` supervision
  - docs updated:
    - `docs/architecture.md`
    - `docs/config_cookbook.md`
    - `docs/script_reference.md`
    - `scripts/README.md`
    - `AGENTS.md`
  - validation:
    - py_compile passed for modified source/scripts
    - `pytest tests/test_integration.py tests/test_loss.py tests/test_config.py -q`
      passed (`56 passed`)
- `2026-04-18`: ran an enhanced same-pair temperature-extrapolation TGNN
  proxy:
  - protocol:
    - train: low-temperature same-pair rows from
      `results/temperature_extrapolation_baselines/splits/train_low.csv`
    - validation: `results/temperature_extrapolation_baselines/splits/val_low.csv`
    - test: high-temperature same-pair rows from
      `results/temperature_extrapolation_baselines/splits/test_high.csv`
  - config:
    - `configs/paper_config_tuned_entropy_interaction_rescue_explicit_h_small.yaml`
    - combines entropy-coupled fusion, explicit-H small molecules,
      auxiliary direct solubility loss, crystal-detach, and Walden check
  - completed local-MPS proxy:
    - budget: `1/4/0`
    - checkpoint:
      `checkpoints/temperature_extrapolation_enhanced/tgnn_entropy_explicit_h_rescue_seed42_p1-4-0.pt`
    - metrics:
      - `MAE 2.016`
      - `RMSE 2.544`
      - `R^2 0.012`
    - artifact bundle:
      - `results/temperature_extrapolation_enhanced_proxy/summary.json`
      - `results/temperature_extrapolation_enhanced_proxy/SUMMARY.md`
      - `logs/temperature_extrapolation_enhanced/tgnn_entropy_explicit_h_rescue_seed42_p1-4-0/`
  - comparison to existing proxy artifacts:
    - old TGNN proxy (`1/8/1`): `MAE 1.945`, `R^2 0.060`
    - DirectGNN proxy (`10 epochs`): `MAE 1.619`, `R^2 0.283`
    - pair Van't Hoff baseline: `MAE 0.368`, `R^2 0.887`
  - interpretation:
    - the ready-made enhanced flags do not fix high-temperature extrapolation
      in this local proxy setting
    - `aux_direct_sol_loss` and `detach_crystal_from_encoder` are already
      implemented and active in the enhanced config, so they are not missing
      code items
    - likely next bottleneck is the training objective: pair-level
      temperature-curve supervision is too weak relative to the closed-form
      Van't Hoff signal
  - runtime incidents:
    - expanded-IDAC append attempt used
      `results/temperature_extrapolation_enhanced_proxy/splits/train_low_idac_aux.csv`
      (`21,996` rows; `14,876` gamma-only aux rows) and was stopped manually
      during phase 2 because full-loader/solver training was too slow on MPS
    - `1/4/1` no-IDAC attempt was stopped manually during phase 3 because
      phase-3 batches became minutes-long on MPS
  - accepted follow-up:
    - IDAC should be integrated through a separate auxiliary batch stream or
      gamma-only fast path, not by appending gamma rows to the main SLE CSV for
      local proxy runs
    - add stronger same-pair temperature-curve supervision before spending
      full `50/200/50` CUDA budget on this protocol
- `2026-04-18`: implemented separate IDAC auxiliary training and supervised
  pair-temperature curve losses:
  - source changes:
    - `scripts/train.py`:
      - added `--idac-train-data`
      - added `--idac-steps-per-epoch`
      - added `--idac-batch-size`
    - `src/tgnn_solv/model.py`:
      - added `TGNNSolv.forward(..., gamma_only=True)`
      - gamma-only path runs encoder + interaction + NRTL `ln_gamma_inf`
        without SLE solver/correction
    - `src/tgnn_solv/trainer.py`:
      - added separate gamma-only auxiliary IDAC optimizer steps
      - auxiliary stream uses phase-specific IDAC weights and does not append
        rows to the main SLE loader
    - `src/tgnn_solv/loss.py`:
      - added `pair_temp_delta`
      - added `vant_hoff_slope`
      - added `vant_hoff_intercept`
    - `src/tgnn_solv/config.py`:
      - added IDAC auxiliary step/weight controls
      - added Van't Hoff slope/intercept scale controls
    - `configs/paper_config_tuned_entropy_interaction_rescue_explicit_h_small.yaml`
      now enables the new curve losses and defaults to
      `idac_aux_steps_per_epoch=4`
  - IDAC-only local auxiliary split:
    - `results/temperature_extrapolation_enhanced_proxy/splits/idac_aux_train.csv`
    - rows: `14,876`
    - unique pairs: `3,140`
    - unique solutes: `134`
    - unique solvents: `111`
    - summary:
      `results/temperature_extrapolation_enhanced_proxy/idac_aux_summary.json`
  - validation:
    - py_compile passed for modified files
    - `pytest tests/test_loss.py tests/test_config.py -q` passed
      (`27 passed`)
    - `pytest tests/test_water_graph.py -q` passed (`5 passed`)
    - gamma-only forward smoke-test passed on an IDAC batch
    - new pair-temperature losses were checked for autograd flow
  - runtime finding:
    - IDAC auxiliary stream must use a smaller separate batch on MPS
    - inheriting the main SLE batch size `512` made gamma-only cross-attention
      too slow
    - `--idac-batch-size 64` is the current practical local-MPS setting
  - completed local-MPS proxy with separate IDAC stream and supervised curve
    losses:
    - budget: `1/4/0`
    - IDAC stream: `4` aux batches/epoch, IDAC batch size `64`
    - checkpoint:
      `checkpoints/temperature_extrapolation_enhanced/tgnn_entropy_rescue_idacstream_vh_seed42_p1-4-0_idacbs64.pt`
    - metrics:
      - `MAE 2.029`
      - `RMSE 2.551`
      - `R^2 0.0069`
    - logs:
      `logs/temperature_extrapolation_enhanced/tgnn_entropy_rescue_idacstream_vh_seed42_p1-4-0_idacbs64/`
    - summary:
      `results/temperature_extrapolation_enhanced_proxy/SUMMARY.md`
      and `summary.json`
  - accepted interpretation:
    - the plumbing is now correct: expanded IDAC no longer requires appending
      gamma-only rows to SLE train CSVs
    - the short proxy result is still negative relative to:
      - previous enhanced proxy `MAE 2.016`
      - older TGNN proxy `MAE 1.945`
      - DirectGNN proxy `MAE 1.619`
      - pair Van't Hoff `MAE 0.368`
    - next temperature-extrapolation improvement should use explicit pair-curve
      anchor/distillation from precomputed train-low Van't Hoff fits rather
      than only generic local curve regularization
- `2026-04-18`: implemented and tested precomputed Van't Hoff anchor
  distillation for same-pair temperature extrapolation:
  - source changes:
    - `scripts/data/build_vant_hoff_anchor_split.py`:
      - fits pairwise `ln(x2) = slope * (1/T) + intercept` on train-low rows
      - appends pseudo high-temperature rows with `has_vh_anchor=True`
      - writes fit diagnostics and a summary JSON
    - `src/tgnn_solv/data/dataset.py`:
      - emits `vh_anchor_ln_x2`, `vh_anchor_mask`, and `vh_anchor_weight`
    - `src/tgnn_solv/loss.py`:
      - adds `vh_anchor` weighted Huber supervision
    - `src/tgnn_solv/config.py`:
      - adds `vh_anchor_default_weight`
    - `src/tgnn_solv/trainer.py`:
      - includes `vh_anchor` in phase-level loss-weight defaults
    - `configs/paper_config_tuned_entropy_interaction_rescue_explicit_h_small.yaml`:
      - enables `vh_anchor` in phase 2 and phase 3
  - generated anchor split:
    - base train rows: `7,120`
    - anchor rows: `1,424`
    - output rows: `8,544`
    - anchor temperature: `350 K`
    - median fit `R^2`: `0.997`
    - median fit `RMSE`: `0.0091`
    - artifacts:
      - `results/temperature_extrapolation_enhanced_proxy/splits/train_low_vh_anchor_350.csv`
      - `results/temperature_extrapolation_enhanced_proxy/splits/train_low_vh_anchor_350.csv.fits.csv`
      - `results/temperature_extrapolation_enhanced_proxy/vh_anchor_350_summary.json`
  - validation:
    - py_compile passed for modified source and the new script
    - `pytest tests/test_loss.py tests/test_config.py tests/test_dataset.py -q`
      passed (`34 passed`)
    - smoke batch confirmed `vh_anchor` loss is active on anchor rows only
  - completed local-MPS proxy:
    - budget: `1/4/0`
    - IDAC stream: `4` aux batches/epoch, IDAC batch size `64`
    - train:
      `results/temperature_extrapolation_enhanced_proxy/splits/train_low_vh_anchor_350.csv`
    - IDAC aux:
      `results/temperature_extrapolation_enhanced_proxy/splits/idac_aux_train.csv`
    - checkpoint:
      `checkpoints/temperature_extrapolation_enhanced/tgnn_entropy_rescue_idacstream_vhanchor350_seed42_p1-4-0.pt`
    - metrics:
      - `MAE 1.986`
      - `RMSE 2.527`
      - `R^2 0.025`
    - logs:
      `logs/temperature_extrapolation_enhanced/tgnn_entropy_rescue_idacstream_vhanchor350_seed42_p1-4-0/`
    - summary:
      `results/temperature_extrapolation_enhanced_proxy/SUMMARY.md`
      and `summary.json`
  - accepted interpretation:
    - VH-anchor distillation is the first enhanced variant with a positive
      movement (`2.029 -> 1.986` MAE)
    - the improvement is still insufficient: it remains worse than old TGNN
      proxy `MAE 1.945`, DirectGNN proxy `MAE 1.619`, and pair Van't Hoff
      `MAE 0.368`
    - temperature extrapolation remains an unresolved objective/training
      problem under the current short local proxy
    - no training, FastSolv, SolProp, or Python worker processes remained
      active after the run
- `2026-04-18`: added and ran structural-extrapolation diagnosis on the latest
  aligned scaffold prediction slices:
  - script:
    - `scripts/analysis/run_structural_extrapolation_diagnosis.py`
  - output bundle:
    - `results/structural_extrapolation_diagnosis/`
  - validation:
    - `python -m json.tool results/structural_extrapolation_diagnosis/summary.json`
      passed
    - `python -m py_compile scripts/analysis/run_structural_extrapolation_diagnosis.py`
      passed
  - key result:
    - TGNN_MPNN is worse than DirectGNN globally by `+0.089 MAE`
    - TGNN_MPNN is still better on `46.4%` of scaffold rows
    - TGNN_MPNN is better on `46.9%` of scaffold pairs
    - catastrophic pair fraction (`pair MAE > 3`) is lower for TGNN_MPNN:
      `15.4%` vs DirectGNN `17.1%`
  - important slices:
    - TGNN is worse for polyaromatic rows (`+1.125 MAE`, `52` rows)
    - TGNN is worse for aromatic solvents (`+0.740 MAE`, `130` rows)
    - TGNN is tied on water rows (`+0.004 MAE`)
    - TGNN improves hydrocarbon solvents (`-0.232 MAE`)
    - TGNN improves the lowest `pair_tanimoto <= 0.3` bin (`-0.072 MAE`)
  - accepted interpretation:
    - structural extrapolation is heterogeneous
    - the next architectural work should target slice-specific failure modes
      and model complementarity, not only global scaffold MAE
- `2026-04-18`: implemented the first structural-rescue plumbing pass for the
  TGNN physics path:
  - source changes:
    - `src/tgnn_solv/config.py`:
      - added `use_nrtl_group_prior`, `nrtl_group_prior_tau_scale`,
        `nrtl_group_prior_tau_clamp`, `nrtl_group_prior_ra_scale`
      - added `requires_group_prior_features`
    - `src/tgnn_solv/heads.py`:
      - added an opt-in deterministic Hansen/group-contribution prior on
        `tau_ref_12` and `tau_ref_21` in `NRTLHead`
      - this is a weak in-repo surrogate, not a true UNIFAC implementation
    - `src/tgnn_solv/model.py` and `src/tgnn_solv/trainer.py`:
      - pass group-count features into `NRTLHead` in both full forward and
        Phase 1 shortcut forward
    - loaders in `scripts/train.py`, `scripts/training/train.py` wrapper path,
      `scripts/run_full_budget_experiment.py`, `scripts/train_directgnn.py`,
      `src/tgnn_solv/optuna_tuner.py`, and related diagnostics now request
      group features whenever `requires_group_prior_features` is true
    - inference/uncertainty/attribution/physics-validation helpers now also
      compute group features when `use_nrtl_group_prior=true`
    - `scripts/data/build_idac_aux_stream.py`:
      - builds standalone IDAC auxiliary CSVs for `--idac-train-data`
      - does not append IDAC rows to SLE train/val/test splits
    - `configs/paper_config_tuned_structural_rescue.yaml`:
      - enables `split_late`, entropy-coupled fusion, explicit-H small
        molecules, `use_aux_direct_sol_loss`, phase-2 crystal detach, IDAC
        aux-stream weights, and the NRTL group prior
  - generated aux-stream artifact:
    - `notebooks/data/processed_idac_aux_stream/idac_train.csv`
    - `notebooks/data/processed_idac_aux_stream/summary.json`
    - rows: `14,900`
    - pairs: `3,145`
    - `appended_to_sle_splits: false`
  - validation:
    - `pytest tests/test_config.py tests/test_dataset.py tests/test_integration.py tests/test_loss.py -q`
      passed (`64 passed`)
    - py_compile passed for modified source and `scripts/data/build_idac_aux_stream.py`
    - smoke inference with
      `checkpoints/structural_rescue_proxy_smoke_v2.pt` completed with
      `use_nrtl_group_prior=true`
  - smoke/proxy training:
    - first run found a real Phase 1 bug: direct `head_nrtl(...)` call in
      `trainer._forward_phase1` lacked group features when
      `use_nrtl_group_prior=true`
    - fixed in the same pass
    - completed CPU smoke on `tmp/structural_rescue_proxy/` with:
      - SLE rows: `96/24/24`
      - standalone IDAC aux rows: `64`
      - budget: `1/1/1`
      - checkpoint:
        `checkpoints/structural_rescue_proxy_smoke_v2.pt`
      - logs:
        `logs/structural_rescue_proxy_smoke/structural_rescue_proxy_smoke_v2/`
      - smoke test metric: `MAE 1.992`, `R^2 -0.686`
    - this smoke metric is not a benchmark result; it only validates that the
      new objectives and feature plumbing execute end-to-end
- `2026-04-18`: installed real UNIFAC dependencies and added precomputed
  Modified-UNIFAC support:
  - environment:
    - installed in `~/anaconda3/envs/tgnn-solv`:
      - `thermo 0.6.0`
      - `chemicals 1.5.1`
      - `lxml 6.1.0`
    - `pyproject.toml` now exposes optional extra `thermo`
    - `requirements.txt` includes the same packages
  - source changes:
    - `src/tgnn_solv/unifac.py`:
      - RDKit SMILES -> InChIKey -> DDBST Modified-UNIFAC groups
      - computes `ln(gamma_inf)` with `thermo.unifac.UNIFAC` and
        `DOUFIP2016`
    - `src/tgnn_solv/config.py`:
      - added `use_unifac_gamma_prior`,
        `unifac_gamma_prior_tau_scale`, and
        `unifac_gamma_prior_tau_clamp`
    - `src/tgnn_solv/data/dataset.py`:
      - emits `gamma_weight`, `unifac_ln_gamma_inf`,
        `unifac_gamma_mask`
    - `src/tgnn_solv/loss.py`:
      - `gamma_inf` objective now supports row-level `gamma_weight`
    - `src/tgnn_solv/heads.py`, `model.py`, `trainer.py`:
      - precomputed UNIFAC `ln(gamma_inf)` can be converted to a weak
        tau offset in the NRTL head
    - inference, uncertainty, attribution, and physics-validation helpers
      compute/pass UNIFAC priors when the config requires them
    - new scripts:
      - `scripts/data/build_unifac_aux_stream.py`
      - `scripts/data/attach_unifac_priors_to_splits.py`
    - `configs/paper_config_tuned_structural_rescue.yaml` now enables the
      UNIFAC gamma prior in addition to the group-prior fallback
  - generated artifacts:
    - standalone combined gamma aux stream:
      - `notebooks/data/processed_unifac_aux_stream/gamma_aux_train.csv`
      - `notebooks/data/processed_unifac_aux_stream/summary.json`
      - rows: `39,459`
      - experimental IDAC rows: `14,900`
      - Modified-UNIFAC pseudo rows: `24,559`
      - UNIFAC pseudo row weight: `0.15`
      - experimental row weight: `1.0`
      - `appended_to_sle_splits: false`
    - processed split copies with UNIFAC prior columns:
      - `notebooks/data/processed_unifac_priors/`
      - `notebooks/data/processed_unifac_priors/unifac_prior_summary.json`
      - canonical scaffold coverage:
        - train: `29,840 / 111,035` rows (`26.87%`)
        - val: `624 / 8,026` rows (`7.77%`)
        - test: `690 / 8,027` rows (`8.60%`)
      - all split families were processed
  - validation:
    - `pytest tests/test_config.py tests/test_dataset.py tests/test_integration.py tests/test_loss.py -q`
      passed (`65 passed`)
    - py_compile passed for modified source and UNIFAC scripts
    - inference smoke with
      `checkpoints/structural_rescue_unifac_proxy_smoke.pt` completed with
      `use_unifac_gamma_prior=true`
  - smoke/proxy training:
    - completed CPU smoke on `tmp/structural_rescue_unifac_proxy/`
    - SLE rows: `96/24/24`
    - gamma aux rows: `64`
    - budget: `1/1/1`
    - checkpoint:
      `checkpoints/structural_rescue_unifac_proxy_smoke.pt`
    - logs:
      `logs/structural_rescue_unifac_proxy_smoke/structural_rescue_unifac_proxy_smoke/`
    - smoke metric: `MAE 2.062`, `R^2 -0.786`
    - this remains only a plumbing smoke, not a benchmark

## 2026-04-18 - Structural Extrapolation Pretraining Diagnostics

- Added prediction-only CPU diagnostics for structural extrapolation:
  - `scripts/analysis/test_compositional_generalization.py`
    - BRICS fragment compositionality split for existing prediction CSVs
  - `scripts/analysis/scaffold_distance_error_analysis.py`
    - nearest train Murcko-scaffold distance vs prediction error
  - `scripts/analysis/analyze_embedding_geometry.py`
    - PCA/MMD/domain-AUC and PCA/t-SNE plots for saved descriptor-probe
      embeddings
    - includes a temporary NumPy pickle compatibility shim for older
      `numpy._core` object-array NPZ artifacts
- Generated summary artifacts:
  - `results/structural_extrapolation_diagnostics/summary.json`
  - `results/structural_extrapolation_diagnostics/SUMMARY.md`
  - detailed BRICS outputs:
    - `results/compositional_generalization/directgnn_latest/`
    - `results/compositional_generalization/tgnn_mpnn_latest/`
  - detailed scaffold-distance outputs:
    - `results/scaffold_distance_analysis/directgnn_latest/`
    - `results/scaffold_distance_analysis/tgnn_mpnn_latest/`
  - embedding-geometry outputs:
    - `results/embedding_geometry/tgnn_mpnn_proxy/`
    - `results/embedding_geometry/tgnn_tuned_medium/`
- Key BRICS compositional result on current scaffold predictions:
  - composed-from-train-BRICS rows: `1,358 / 5,826` (`23.31%`)
  - DirectGNN:
    - composed row MAE `1.438`
    - novel-fragment row MAE `1.717`
    - gap `+0.279` MAE
  - TGNN_MPNN:
    - composed row MAE `1.385`
    - novel-fragment row MAE `1.849`
    - gap `+0.464` MAE
  - interpretation: BRICS fragment novelty is materially associated with
    scaffold error, especially for TGNN.
- Key nearest-scaffold-distance result:
  - median nearest train-scaffold distance: `0.481` row-level,
    `0.487` unique-solute-level
  - DirectGNN:
    - row Pearson/Spearman `0.050 / 0.064`
    - unique-solute Pearson/Spearman `0.102 / 0.122`
  - TGNN_MPNN:
    - row Pearson/Spearman `-0.056 / -0.035`
    - unique-solute Pearson/Spearman `0.009 / 0.041`
  - interpretation: scalar nearest Murcko distance alone is too weak to
    explain errors; structural difficulty is not a simple monotonic function
    of nearest-scaffold Tanimoto.
- Embedding geometry from saved descriptor-probe embeddings:
  - `results/proxy_comparison/tgnn_mpnn_descriptor_probe/`:
    - split-domain classifier AUC `0.857`
    - RBF MMD^2 `0.0272`
    - train/test are strongly separable in frozen `g_sol` space
  - `results/medium_budget/per_model/tgnn_tuned/descriptor_probe/`:
    - split-domain classifier AUC `0.839`
    - RBF MMD^2 `0.0331`
    - train/test remain moderately separable in frozen `g_sol` space
- Existing linear descriptor probes remain relevant:
  - TGNN_MPNN proxy median test descriptor R^2 `0.565`
  - tuned medium TGNN median test descriptor R^2 `0.505`
  - both are "mixed" descriptor recoverability, not enough to declare the
    encoder bottleneck-free.
- Accepted interpretation:
  - single-molecule representation pretraining can help but is insufficient
    for structural extrapolation because the target is pair compatibility
  - next high-rigor direction is pair/fragment-level pretraining or stronger
    functional-group/UNIFAC-style priors, not only masked-subgraph or
    descriptor recovery on isolated molecules
- Validation:
  - `python -m py_compile scripts/analysis/test_compositional_generalization.py scripts/analysis/scaffold_distance_error_analysis.py`
    passed
  - `python -m py_compile scripts/analysis/analyze_embedding_geometry.py`
    passed

## 2026-04-18 - Research Idea Backlog From Current Discussion

This section is an actionable idea registry, not a result table. Treat items
marked "hypothesis" or "idea" as not yet validated unless an artifact is cited
elsewhere in this memory.

### Evaluation protocols to keep separate

- Maintain three distinct evaluation regimes:
  - scaffold / solute structural extrapolation:
    - new solute or new scaffold
    - DirectGNN can remain stronger here; TGNN target is minimal physics tax
      plus interpretability/temperature robustness
  - same-pair temperature interpolation:
    - train and test points from the same solute-solvent pair, with held-out
      temperatures inside the observed range
    - physics should be competitive or better because the temperature curve is
      constrained by SLE/Van't Hoff structure
  - same-pair low-to-high temperature extrapolation:
    - train on low-temperature points and test on high-temperature points
    - this is the "killer feature" regime for physics
- Current accepted temperature-extrapolation diagnostic:
  - same-pair low-to-high `T`
  - `pair Van't Hoff`: `MAE 0.368`, `R^2 0.887`, shift-direction accuracy
    `99.0%`
  - `pair linear T`: `MAE 0.414`, `R^2 0.850`, shift-direction accuracy
    `99.0%`
  - `RF(Morgan+T)`: `MAE 1.290`, `R^2 0.658`, shift-direction accuracy
    `40.4%`
  - `DirectGNN proxy`: `MAE 1.619`, `R^2 0.283`
  - `TGNN proxy`: `MAE 1.945`, `R^2 0.060`
  - interpretation:
    - physics works in this regime
    - current neural models are not extracting the temperature-curve benefit
      yet
- Add/maintain a same-pair temperature-interpolation benchmark:
  - pairs with at least `6` temperature points
  - options:
    - leave-one-temperature-out
    - 70/30 temperature split within pair
    - middle-point holdout
  - compare DirectGNN, TGNN, pair Van't Hoff, pair linear T
- Pair-random parity remains a useful intermediate engineering target:
  - target: TGNN within about `±0.03 MAE` of DirectGNN
  - if TGNN remains substantially worse here, the bottleneck or pair branch is
    still too costly
- Add curve-quality diagnostics beyond pointwise MAE:
  - slope error in `ln(x2)` vs `1/T`
  - pairwise rank accuracy across temperature
  - monotonicity violations
  - pair-level curve shape fidelity
  - pair-level error distribution and worst-pair tables
  - train-vs-test MAE extraction from logs for overfit/underfit diagnosis

### Immediate TGNN training and architecture rescue ideas

- Keep using interaction-gradient rescue:
  - train-only auxiliary direct-solubility head on the pair representation
  - purpose: supervise `g_pair` and cross-attention, not to bypass physics as
    the final deployed prediction
  - suggested phase weights:
    - Phase 1: `0`
    - Phase 2: around `0.1`
    - Phase 3: around `0.01`
- Detach crystal branch during Phase 2 SLE training:
  - purpose: prevent `T_m` / crystal supervision from dominating the shared
    encoder while the interaction/NRTL path is trying to learn pair chemistry
  - if implemented, log gradient norms for crystal vs interaction branches
- Split crystal and interaction representations:
  - physics rationale:
    - `T_m`, `dH_fus`, `dS_fus` are pure-solid/crystal properties
    - `tau_12`, `tau_21`, `alpha`, `gamma_inf` are liquid pair-interaction
      properties
    - one shared encoder can impose the wrong inductive bias
  - implementation options:
    - full `crystal_encoder` and `interaction_encoder`
    - shared low-level backbone plus branch-specific adapters
    - `split_late` or residual role-specific adapters as lower-cost variants
  - key constraint:
    - `T_m` / fusion losses should not backpropagate into the interaction-only
      adapter unless this is an explicit ablation
- NRTL-head capacity/flexibility ideas:
  - richer temperature dependence:
    - current/ref mode plus optional `a + b/T + c*ln(T)`
    - or weak linear/log correction with regularization
  - constrain or route `alpha`:
    - fixed alpha by system class
    - narrow range prediction
    - solvent-class routing
  - prefer corrections in parameter space:
    - residuals on `T_m`, `dH_fus`, `dCp_fus`, `tau_12`, `tau_21`, `alpha`
      followed by solving SLE
    - avoid an unconstrained final `ln(x2)` bypass unless it is explicitly an
      ensemble/baseline ablation
- Optional direct/physics ensemble idea:
  - `ln_x2_final = w_phys * ln_x2_SLE + (1 - w_phys) * ln_x2_direct`
  - useful as an ablation or calibrated fallback
  - risk: can collapse back to DirectGNN with a decorative solver
- Alternative activity models and mixtures of experts:
  - keep Wilson/UNIQUAC configs as physical-model alternatives
  - consider eNRTL or electrostatic additions for electrolyte/ionic systems
  - solvent-type MoE can route systems to different physical heads/models

### NRTL and pair-interaction supervision ideas

- Expanded IDAC should be treated as a separate auxiliary supervision stream,
  not appended as solubility rows:
  - current expanded ThermoML 2015-2019 IDAC:
    - `14,900` rows
    - `3,145` pairs
    - `63` DOI
    - `0%` overlap with SLE pairs
  - old IDAC:
    - `404` rows
    - `138` pairs
    - `9` DOI
  - no current conflicting pair issue was found in the extracted expanded set
    (`std > 0.5`: `0` pairs)
- Keep row-level gamma weights:
  - experimental IDAC weight near `1.0`
  - UNIFAC pseudo-IDAC weight around `0.15`
  - do not silently give pseudo-data equal authority
- Future ThermoML auxiliary objectives:
  - extract `G^E` / excess Gibbs energy and supervise NRTL directly through:
    - `G^E / RT`
  - extract VLE data and supervise activity coefficients through:
    - `y_i P = x_i gamma_i P_i^sat`
  - these are different tasks but constrain the same NRTL pair parameters
- Potential data sources for pair-interaction supervision:
  - NIST ThermoML
  - DECHEMA where legally accessible
  - OpenThermo
  - literature scraping from JCED, Fluid Phase Equilibria,
    J. Chem. Thermodynamics
  - DOI -> Semantic Scholar abstract -> method-label classification for source
    metadata
- UNIFAC / group-contribution prior directions:
  - current repository has a weak UNIFAC `ln(gamma_inf)` prior path and a group
    prior fallback
  - future stronger version:
    - true group-interaction prior for NRTL-like tau values
    - neural residual around UNIFAC/functional-group estimates:
      - `tau_pred = tau_prior + delta_tau_NN`
    - curriculum annealing from deterministic UNIFAC to neural prediction
  - use this especially for scaffold extrapolation because functional groups
    transfer better than whole-scaffold embeddings

### Fusion-property and SLE-physics ideas

- Entropy-coupled fusion is the preferred physical parameterization:
  - predict `dH_fus` and `dS_fus`
  - derive `T_m = dH_fus / dS_fus`
  - do not independently predict an unconstrained `T_m` when testing the
    strict physical bottleneck
- Add/maintain Walden-style entropy constraints:
  - typical organic `dS_fus` around `50-60 J/(mol*K)`
  - useful soft range: roughly `20-150 J/(mol*K)`
  - account for exceptions:
    - spherical/symmetric molecules can have low entropy of fusion
    - flexible molecules can have high entropy of fusion
- Explicit entropy terms to consider:
  - conformational entropy:
    - term proportional to `R * ln(N_rot + 1)` or a learned scalar multiple
  - rotational symmetry correction:
    - approximate `-R * ln(sigma)` if symmetry number can be computed
- Add `dCp_fus` rather than assuming `Delta Cp = 0` forever:
  - `Delta Cp = 0` Hildebrand approximation can create systematic errors of
    order `0.5-0.8` in `ln(x2)` for complex molecules
  - use a regularized group-contribution or SPARC/Bondi-like prior when direct
    labels are unavailable
- Thermodynamic cycle supervision:
  - `dH_fus = dH_sub - dH_vap`
  - use as a loss term when `dH_sub` and `dH_vap` are available
  - consider multitask heads for `dH_fus`, `dH_sub`, `dH_vap`
- Candidate fusion-property data sources:
  - `T_m`:
    - Bradley Open
    - Bradley Double Plus Good
    - NIST WebBook
    - CRC Handbook
    - Kaggle melting-point datasets
    - PubChem experimental properties
    - ChEMBL
  - `dH_fus`:
    - Acree & Chickos / JPCRD compilations
    - CRC Handbook
    - NIST WebBook
  - pseudo/auxiliary:
    - SPARC or group-contribution estimates
    - inverse extraction from multi-temperature SLE curves when gamma can be
      estimated

### Water and small-molecule representation ideas

- Accepted issue:
  - water as heavy-atom graph is nearly degenerate:
    - legacy graph: one oxygen node, self-loop, no physical heavy-atom edges
    - this weakens MPNN and TIMP channels
  - water is important:
    - current scaffold-test water-solvent rows: about `476 / 5,826`
    - small solvents with <=3 heavy atoms: about `2,104 / 5,826`
- Current implemented low-cost fix:
  - `explicit_h_small_molecules`
  - water changes to explicit O-H graph:
    - `3` nodes
    - directed O-H edges
  - applies to molecules with at most `explicit_h_max_heavy_atoms`
- Additional water/small-molecule ideas to preserve:
  - append small-molecule global descriptors:
    - `MolLogP`, `TPSA`, HBD/HBA, dipole proxies, polar surface descriptors
  - virtual node for one-atom graphs with global molecular features
  - learned special-solvent embeddings for water/methanol/ethanol/etc.
  - 3D conformers or small-molecule geometric encoder for water-like edge
    cases
- Required diagnostics after any water/small-molecule change:
  - water-only MAE
  - small-solvent MAE
  - TIMP dispersive vs polar channel activity on water pairs
  - attribution over explicit H/O nodes

### Structural extrapolation and representation ideas

- Accepted mechanism hypotheses:
  - structural extrapolation is hard for all models because scaffold split is
    chemical extrapolation, not simple interpolation
  - TGNN has an additional handicap because errors propagate through:
    - fusion properties
    - activity parameters
    - solver
    - correction branch
  - NRTL parameter identifiability is weak from SLE-only supervision
  - crystal supervision can impose a "solid-property" bias on an encoder that
    also needs to represent liquid pair compatibility
- Functional-group tokenization:
  - build fragment/group graphs using BRICS, rings, and functional-group
    matches
  - represent groups such as `OH`, `COOH`, `amide`, `phenyl`, `thiophene`,
    etc.
  - motivation:
    - new scaffolds can still be new combinations of known groups
    - UNIFAC/COSMO-style methods are group/fragment-oriented
- Hierarchical encoding:
  - atom-level MPNN
  - fragment-level graph/attention
  - molecule-level pooling
  - use molecule-level features for crystal/fusion properties
  - use fragment/pair features for `tau` and compatibility
- Meta-learning / few-shot adaptation:
  - if one or more experimental points exist for a new pair, initialize NRTL
    parameters from the network/prior and adapt `tau_12`, `tau_21`, `alpha`
    by a few gradient steps
  - useful industrially because a first measured point is often available
- Applicability-domain framing:
  - nearest Murcko distance alone is weak
  - BRICS novelty and embedding-domain separability are more informative
  - combine multiple AD signals:
    - BRICS novelty
    - pair Tanimoto
    - scaffold distance
    - embedding-domain classifier score
    - solvent class and water/small-solvent flags

### Pretraining ideas for structural extrapolation

- Current single-molecule Stage 0 tasks are useful but insufficient:
  - masked subgraph
  - bond type
  - RDKit descriptor recovery
  - molecule-level contrastive learning
  - limitation: they do not teach solute-solvent compatibility
- Pairwise compatibility pretraining:
  - pretrain encoder + interaction head to predict BigSolDB pair solubility or
    pair-ranking signals
  - can be done with lower budget than full physics training
  - should include cross-scaffold positives/negatives where possible
- IDAC/GE/VLE pair pretraining:
  - pretrain pair representation on `gamma_inf`, `G^E`, or VLE-derived
    activity coefficients
  - this directly targets the NRTL/interaction branch
- Cross-scaffold compatibility transfer:
  - molecules with similar UNIFAC/IDAC compatibility profiles should have
    compatible pair embeddings even when scaffolds differ
  - possible contrastive labels:
    - similar solvent compatibility vector
    - similar UNIFAC gamma profile
    - similar experimental IDAC profile
- Fragment-level/additivity pretraining:
  - predict fragment contributions to descriptors or interaction proxies
  - enforce additive reconstruction of molecular properties from fragment
    embeddings
  - directly targets compositional generalization
- Broader pretraining coverage:
  - ZINC250k and ChEMBL are higher-value than BigSolDB-only pretraining when
    the goal is new-scaffold coverage
  - but broad coverage alone does not solve pair compatibility without pair or
    fragment objectives

### GPU experiment queue

- Full same-pair temperature extrapolation retraining:
  - TGNN structural-rescue config with:
    - entropy-coupled fusion
    - explicit-H small molecules
    - expanded IDAC aux stream
    - UNIFAC/gamma prior
    - aux direct pair head
    - phase-2 crystal detach
  - DirectGNN explicit-H control
  - target:
    - TGNN high-T MAE should drop substantially below current proxy `1.945`
    - practical first target `< 1.0`
    - aspirational target near Van't Hoff `< 0.5`
- Pair-random parity full run:
  - same rescue features
  - target: TGNN within `±0.03 MAE` of DirectGNN
- Same-pair temperature interpolation benchmark:
  - implement and run DirectGNN/TGNN/Van't Hoff/linear baselines
- Multi-seed confirmation:
  - especially for temperature extrapolation and pair-random parity
  - at least `3` seeds before strong claims
- Ablations to run when GPU is available:
  - expanded IDAC only
  - UNIFAC prior only
  - explicit-H only
  - entropy-coupled fusion only
  - aux direct head only
  - phase-2 detach only
  - split encoder/adapters
  - pairwise/fragment pretraining
  - GE/VLE auxiliary supervision

### Source uncertainty and metadata ideas

- Current source weighting result is negative on the tested subset, but the
  idea is not rejected globally.
- Better source-uncertainty path:
  - DOI -> Semantic Scholar metadata/abstract
  - LLM or rules-based method classification:
    - shake-flask
    - HPLC
    - gravimetric
    - synthetic/estimated
    - unspecified
  - method labels can drive:
    - row uncertainty
    - source-grouped evaluation
    - robust losses
    - heteroskedastic heads
- Do not prioritize this over core diagnostics and temperature-extrapolation
  rescue unless source labels become cheap to obtain.

### Communication / narrative framing to preserve

- The project narrative should not claim that TGNN must beat DirectGNN on every
  scaffold MAE table.
- More defensible narrative:
  - DirectGNN is currently the best scaffold MAE model
  - TGNN has a small physics tax on scaffold MAE
  - same-pair temperature extrapolation is where physics should provide a
    clear advantage
  - current Van't Hoff baseline proves the physics signal exists
  - current TGNN implementation still needs better pair supervision and
    interaction-gradient flow to use that signal
- Any future manuscript/presentation should explicitly separate:
  - structural extrapolation
  - temperature interpolation
  - temperature extrapolation
  - row-random leakage-friendly interpolation

## 2026-04-18 - Cause 2 CPU Checks And Pair-Pretraining Plan

- Added CPU diagnostic scripts for the "cause 2" structural-extrapolation
  plan:
  - `scripts/analysis/analyze_fragment_coverage.py`
  - `scripts/analysis/analyze_solubility_cliffs.py`
  - `scripts/analysis/summarize_unifac_coverage.py`
- Generated artifacts:
  - `results/fragment_coverage/scaffold_test/`
  - `results/solubility_cliffs/train_sampled/`
  - `results/unifac_coverage/current_priors/`
  - combined report:
    - `results/structural_extrapolation_cause2_cpu_checks/summary.json`
    - `results/structural_extrapolation_cause2_cpu_checks/SUMMARY.md`
- Fragment coverage result on canonical `train.csv -> test.csv`:
  - train unique solutes: `15,080`
  - test unique solutes: `2,340`
  - train unique BRICS fragments: `9,662`
  - mean / median test fragment coverage: `0.566 / 0.667`
  - fully covered test solutes: `597 / 2,340` (`25.5%`)
  - partially covered with >50% fragments seen: `690 / 2,340` (`29.5%`)
  - mostly novel with <=50% fragments seen: `1,053 / 2,340` (`45.0%`)
  - interpretation:
    - scaffold test is not mostly a simple recombination of train BRICS
      fragments
    - fragment-level methods are still relevant, but broad coverage or
      better priors are needed because many test solutes contain mostly novel
      BRICS fragments
- Solubility cliff result on sampled train pairs:
  - data: `notebooks/data/processed/train.csv`
  - mean `ln(x2)` over temperatures per `(solvent, solute)` pair
  - sampling:
    - max `200` solutes per solvent
    - max `20,000` pairs per solvent
    - seed `42`
  - solvents analyzed: `147`
  - pairs analyzed: `424,822`
  - similar pairs with Tanimoto >= `0.4`: `3,360`
  - hard cliffs with Tanimoto >= `0.6` and `|Delta ln(x2)| > 2.0`:
    `170`
  - cliff rate:
    - all sampled pairs: `0.040%`
    - similar pairs: `5.06%`
  - easy positives with Tanimoto >= `0.6` and `|Delta ln(x2)| < 0.5`:
    `262`
  - hard-negative / easy-positive ratio: `0.649`
  - interpretation:
    - hard negatives are available and should be used for contrastive
      pretraining
    - but cliffs are not frequent enough under these thresholds to explain all
      structural error by themselves
- UNIFAC prior coverage result from existing precomputed prior splits:
  - train row coverage: `26.9%`
  - train unique-pair coverage: `32.0%`
  - canonical scaffold test row coverage: `8.6%`
  - canonical scaffold test unique-pair coverage: `10.9%`
  - interpretation:
    - current precomputed Modified-UNIFAC prior is useful where available
    - coverage is far below the `>60%` level that would make UNIFAC prior a
      standalone structural-extrapolation solution
    - pair/fragment pretraining and additional ThermoML/UNIFAC coverage remain
      necessary
- Accepted priority hierarchy for cause 2:
  - high priority:
    - pairwise solubility contrastive pretraining
    - explicit Hansen delta prediction / Hansen compatibility objective
    - stronger UNIFAC or functional-group prior for the NRTL head
  - medium priority:
    - solvent-conditioned contrastive pretraining
    - cross-solvent transfer prediction
  - lower priority / larger rewrite:
    - fragment-equivariant MPNN
    - explicit functional-group graph encoder
- Pairwise solubility contrastive pretraining idea:
  - add a fifth Stage 0 task using `(solute_A, solute_B, solvent)` triples
  - positives:
    - same solvent
    - similar solubility, e.g. `|Delta ln(x2)| < 0.5`
  - hard negatives:
    - high structural similarity, e.g. Tanimoto > `0.6`
    - large solubility gap, e.g. `|Delta ln(x2)| > 2.0`
  - easy negatives:
    - structurally dissimilar and large solubility gap
  - purpose:
    - teach pair compatibility and solubility cliffs, not just isolated
      molecular structure
  - implementation note:
    - use solvent-grouped sampling and cache Morgan fingerprints
    - avoid making random negatives dominate the task because they are too
      easy
- Solvent-conditioned contrastive pretraining idea:
  - represent `h_solute | solvent`, not only isolated `h_solute`
  - positives/negatives can be formed from the same solute across different
    solvents:
    - similar solubility across similar solvents -> positive
    - large solubility change across dissimilar solvents -> negative
  - must guard against train/test leakage when evaluating structural
    extrapolation
- Hansen delta objective:
  - current Hansen supervision should be extended from individual molecule
    parameter prediction to explicit pairwise delta prediction:
    - predict `hansen_solute`
    - predict `hansen_solvent`
    - predict `hansen_solute - hansen_solvent` or pair distance directly
  - compatibility/delta loss should have higher weight than pure individual
    recovery when the goal is pair compatibility
- UNIFAC-guided pretraining idea:
  - use deterministic UNIFAC outputs as pseudo-labels for pair compatibility
  - train pair/fragment heads to reproduce UNIFAC-like interaction profiles
  - do not confuse this with the current weak `ln(gamma_inf)` prior path:
    - current path is a limited prior with low coverage
    - future path should target group-interaction / compatibility structure
- Cross-solvent transfer task:
  - input:
    - solute
    - solvent A
    - observed or encoded `ln_x2(solute, A)`
    - solvent B
  - target:
    - `ln_x2(solute, B)`
  - purpose:
    - learn transfer in solvent space and few-shot behavior across solvents
  - risk:
    - leakage if the same solute/pair appears across train/test splits without
      careful protocol design
- Fragment-equivariant / functional-group architecture idea:
  - build a two-level encoder:
    - atom-level MPNN
    - fragment or functional-group MPNN
  - aggregate atom embeddings to fragments and combine molecule-level and
    fragment-level representations
  - use fragment/pair representation for NRTL and compatibility heads
  - large rewrite; only pursue after lower-cost pair-pretraining and prior
    routes are tested
- Practical conclusion after CPU checks:
  - ZINC250k single-molecule pretraining is not enough because the missing
    signal is pair compatibility
  - hard negatives exist and can supervise pairwise contrastive learning
  - BRICS coverage is too low to assume fragment recombination alone solves
    scaffold split
  - current UNIFAC prior coverage is too low to be the only fix
  - next implementation should start with pairwise contrastive sampling and
    Hansen delta objective, then test with GPU-backed Stage 0 / fine-tuning

## 2026-04-18 - Pairwise Contrastive Artifact And Hansen Delta Objective

Status: implemented / Stage 0 hook available, not yet GPU-benchmarked.

- Implemented pairwise solubility contrastive data-artifact builder:
  - `scripts/data/build_pairwise_contrastive_pretrain.py`
  - input:
    - `notebooks/data/processed/train.csv`
  - outputs:
    - `notebooks/data/processed_pairwise_contrastive/pairwise_contrastive_train.csv`
    - `notebooks/data/processed_pairwise_contrastive/summary.json`
    - `notebooks/data/processed_pairwise_contrastive/solvent_sampling_summary.csv`
  - artifact contract:
    - one row is `(solute_A, solute_B, solvent)` under a shared solvent
    - includes mean/median `ln_x2`, temperature coverage metadata, Tanimoto,
      `delta_ln_x2`, `pair_type`, binary `contrastive_label`, and
      `sample_weight`
    - `easy_positive`: Tanimoto >= `0.6` and `|Delta ln_x2| < 0.5`
    - `hard_negative`: Tanimoto >= `0.6` and `|Delta ln_x2| > 2.0`
    - `easy_negative`: Tanimoto <= `0.3` and `|Delta ln_x2| > 2.0`
- Generated the first train artifact:
  - `n_pair_mean_rows`: `10560`
  - `n_solvents_considered`: `205`
  - `n_output_rows`: `2356`
  - pair types:
    - `easy_negative`: `1906`
    - `easy_positive`: `246`
    - `hard_negative`: `204`
  - labels:
    - negative `0`: `2110`
    - positive `1`: `246`
- Implemented explicit Hansen delta compatibility objective:
  - `src/tgnn_solv/loss.py`
  - new loss key:
    - `hansen_delta`
  - target:
    - `(hansen_sol_effective - hansen_slv_effective)`
    - falls back to direct `hansen_sol` / `hansen_slv` if effective pseudo
      fields are absent
  - mask/weights:
    - uses `pair_hansen_mask`
    - uses `pair_hansen_weight` when present
  - scale:
    - normalizes by `S_hansen`
- Added config/schedule plumbing:
  - `src/tgnn_solv/config.py`
    - `use_hansen_delta_loss`
    - `hansen_delta_loss_phase1_weight`
    - `hansen_delta_loss_phase2_weight`
    - `hansen_delta_loss_phase3_weight`
  - `src/tgnn_solv/trainer.py`
    - phase-specific default scheduling for `hansen_delta`
  - `scripts/train.py`
    - pseudo-Hansen targets are enabled when either
      `use_hansen_contrastive` or `use_hansen_delta_loss` is active
  - synchronized the same pseudo-Hansen condition in:
    - `scripts/run_full_budget_experiment.py`
    - `scripts/train_directgnn.py`
    - `src/tgnn_solv/optuna_tuner.py`
    - `scripts/analysis/analyze_timp_channels.py`
    - `scripts/analysis/diagnose_gradient_flow.py`
- Connected the pairwise contrastive artifact to optional Stage 0 pretraining:
  - `src/tgnn_solv/pretrain.py`
    - `PairwiseContrastiveDataset`
    - `PairwiseCompatibilityProjectionHead`
    - optional `pairwise_contrastive_csv`
    - optional `pairwise_contrastive_weight`
    - optional `pairwise_contrastive_batch_size`
  - objective:
    - encode `(solute_A, solvent)` and `(solute_B, solvent)`
    - project pair states built from `[g_solute, g_solvent, |diff|, product]`
    - use weighted BCE on cosine-similarity logits
    - positive label means similar solubility under the same solvent
    - negative label means hard/easy negative from the generated artifact
  - `src/tgnn_solv/pretrain_pipeline.py`
    - passes optional pairwise pretraining args through Stage 0 and checkpoint
      metadata
  - `scripts/train.py`
    - new optional flags:
      - `--pretrain-pairwise-contrastive-data`
      - `--pretrain-pairwise-contrastive-weight`
      - `--pretrain-pairwise-contrastive-batch-size`
  - example:
    - `python scripts/training/train.py --pretrain --pretrain-data zinc250k --pretrain-pairwise-contrastive-data notebooks/data/processed_pairwise_contrastive/pairwise_contrastive_train.csv --pretrain-pairwise-contrastive-weight 0.1 ...`
- Updated structural rescue config:
  - `configs/paper_config_tuned_structural_rescue.yaml`
  - enables `use_hansen_delta_loss: true`
  - enables pseudo-Hansen targets
  - phase weights:
    - Phase 1: `0.05`
    - Phase 2: `0.02`
    - Phase 3: `0.01`
- Added regression tests:
  - `tests/test_loss.py`
  - verifies:
    - Hansen delta loss value and gradients
    - trainer phase scheduling
- Validation:
  - `python -m py_compile` passed for modified modules in the
    `tgnn-solv` conda environment
  - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_loss.py tests/test_config.py -q`
    passed: `29 passed`
  - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_pretrain_pipeline.py -q`
    passed: `4 passed`
  - combined validation:
    - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_loss.py tests/test_config.py tests/test_pretrain_pipeline.py -q`
    - passed: `33 passed`
  - default shell `pytest` can resolve to Homebrew Python without project
    dependencies; use the conda env interpreter for reproducible validation

## 2026-04-18 - Trainer Resume Test Compatibility After IDAC Aux Hook

Status: fixed / full test suite passed.

- Incident:
  - full test suite initially failed in:
    - `tests/test_trainer_resume.py::test_phase1_gc_residual_freeze_schedule_unfreezes_after_configured_epochs`
    - `tests/test_trainer_resume.py::test_phase2_early_stopping_restores_best_state`
  - root cause:
    - `src/tgnn_solv/trainer.py::train_phase` always passed
      `idac_loader=` into `train_epoch`
    - existing resume tests monkeypatch `train_epoch` with the historical
      positional-only test double signature
- Fix:
  - `train_phase` now calls `train_epoch(..., idac_loader=...)` only when
    `idac_train_loader is not None`
  - default non-IDAC training and tests keep the old call shape
  - IDAC auxiliary stream behavior remains available when an IDAC loader is
    explicitly provided
- Validation:
  - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_trainer_resume.py -q`
    passed: `4 passed`
  - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/ -q`
    passed: `227 passed`

## 2026-04-18 - Full Project Description For Agent Onboarding

Status: documentation added.

- Added `PROJECT_DESCRIPTION.md` as a root-level conceptual orientation file
  for future coding and research agents.
- Sources used:
  - `main.tex`
  - `presentation/seminar_talk.tex`
  - `presentation/talk_text.md`
  - `presentation/talk_text_full_verbatim.md`
  - current `PROJECT_MEMORY.md`
- Scope of the new file:
  - project motivation and target definition
  - data model, auxiliary labels, water handling, and split families
  - SLE thermodynamic derivation
  - NRTL activity model and fixed-point solver
  - implicit differentiation formula
  - TGNN-Solv architecture and DirectGNN control baseline
  - Stage 0 and three-phase training
  - loss components, IDAC auxiliary stream, Hansen delta, and pairwise
    contrastive pretraining
  - current empirical state and accepted bottlenecks
  - structural and temperature extrapolation narrative
  - repository concept map and agent reasoning rules
- Updated `AGENTS.md` to point agents to `PROJECT_DESCRIPTION.md` for full
  conceptual/mathematical orientation while keeping `PROJECT_MEMORY.md` as the
  source of truth for changing facts and recent incidents.

## 2026-04-18 - Physics Bottleneck CPU Diagnostics

Status: implemented / run on current processed splits and available TGNN
checkpoints.

- Accepted near-term diagnostic plan:
  - first diagnose compensatory degeneracy before adding more losses
  - inspect ideal-SLE contribution on rows with direct `T_m` and `dH_fus`
  - check same-pair Van't Hoff consistency in train/test data
  - inspect TGNN intermediates for:
    - `tau_12`, `tau_21`, `alpha`
    - `Phi` versus `-ln_gamma_2`
    - `ln_x2_physics` versus `ln_x2_final`
    - `T_m_pred` versus `T_m_true`
  - treat same-pair temperature extrapolation as the main physics-win target,
    not only scaffold MAE
- Added script:
  - `scripts/analysis/run_physics_bottleneck_diagnostics.py`
  - pure CPU, no training required
  - outputs per-split diagnostics plus optional intermediates diagnostics
  - writes JSON, CSV, Markdown, and plots under a chosen results directory
- Command used for the main diagnostic bundle:
  - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python scripts/analysis/run_physics_bottleneck_diagnostics.py --train-data notebooks/data/processed/train.csv --test-data notebooks/data/processed/test.csv --intermediates-csv results/physics_bottleneck_diagnostics/tgnn_medium_budget_intermediates/intermediates.csv --output-dir results/physics_bottleneck_diagnostics_medium --min-vh-points 3 --min-vh-temp-span 5.0`
- Intermediates export commands were run through:
  - `scripts/evaluation/analyze_intermediates.py`
  - root checkpoint:
    - `checkpoints/tgnn_solv_trained.pt`
    - outputs under `results/physics_bottleneck_diagnostics/tgnn_checkpoint_intermediates/`
  - medium-budget checkpoint:
    - `results/medium_budget/per_model/tgnn_tuned/checkpoint.pt`
    - outputs under `results/physics_bottleneck_diagnostics/tgnn_medium_budget_intermediates/`
- Main data-diagnostic results:
  - train supervised rows: `96,798`
  - test supervised rows: `5,826`
  - direct train rows with both `T_m` and `dH_fus`: `1,080`
  - direct test rows with both `T_m` and `dH_fus`: `0`
  - ideal-SLE MAE on direct train crystal-label subset: `0.897`
  - fraction of train crystal-label rows with `|ln_x2_ideal - ln_x2| > 2`:
    `0.124`
  - train same-pair Van't Hoff regressions:
    - pairs: `10,211`
    - median `R^2`: `0.9973`
    - fraction with `R^2 < 0.5`: `0.0062`
    - negative slope fraction: `0.9980`
  - test same-pair Van't Hoff regressions:
    - pairs: `763`
    - median `R^2`: `0.9970`
    - fraction with `R^2 < 0.5`: `0.0105`
    - negative slope fraction: `0.9921`
  - sign convention note:
    - regression is `ln_x2` versus `1/T`
    - endothermic dissolution usually gives a negative slope because
      `ln_x2` rises with temperature
- Medium-budget TGNN intermediates diagnostic:
  - checkpoint:
    - `results/medium_budget/per_model/tgnn_tuned/checkpoint.pt`
  - standard test MAE from intermediates export: `1.816`
  - physics-path MAE from diagnostic bundle: `1.814`
  - final MAE from diagnostic bundle: `1.816`
  - `T_m` MAE on rows with `has_T_m`: `36.1 K`
  - `tau_12` median: `-0.090`
  - `tau_21` median: `0.061`
  - `tau_12` fraction with `|tau| > 8`: `0.0015`
  - `tau_21` fraction with `|tau| > 8`: `0.0`
  - median absolute final correction `|ln_x2_final - ln_x2_physics|`: `0.0`
  - fraction with correction magnitude `> 0.5`: `0.0017`
- Interpretation:
  - the corpus strongly supports the Van't Hoff temperature form for same-pair
    multi-temperature subsets
  - direct `dH_fus` labels are too sparse for test-set ideal-SLE diagnostics
    without GC fallback or model intermediates
  - for the medium-budget checkpoint, the final adaptive correction is almost
    inactive, so the reported error is essentially the physics-path error
  - NRTL parameters are not generally exploding; the larger bottleneck appears
    to be limited physical-path accuracy / identifiability rather than
    out-of-range `tau`
  - root-level `checkpoints/tgnn_solv_trained.pt` is not representative of the
    current reported TGNN scaffold result:
    - intermediates test MAE: `5.73`
    - `T_m` MAE: `287 K`
    - treat it as stale/debug unless its provenance is re-established
- Main artifact roots:
  - `results/physics_bottleneck_diagnostics_medium/`
  - `results/physics_bottleneck_diagnostics/`
  - `results/physics_bottleneck_diagnostics/tgnn_medium_budget_intermediates/`
  - `results/physics_bottleneck_diagnostics/tgnn_checkpoint_intermediates/`

## 2026-04-18 - Exact TGNN_MPNN Proxy Bottleneck Diagnostics

Status: benchmark-aligned diagnostics / oracle-mask export fixed.

- Provenance for the canonical `TGNN_MPNN` scaffold result:
  - checkpoint:
    - `checkpoints/proxy/tgnn_mpnn.pt`
  - evaluation report:
    - `results/proxy_comparison/tgnn_mpnn.json`
  - prediction slices:
    - `results/prediction_error_slices/TGNN_MPNN/`
    - `results/prediction_error_slices_latest/TGNN_MPNN/`
  - log:
    - `logs/20260413_031254/test_metrics.json`
  - metric:
    - `MAE 1.7413106`
    - `RMSE 2.3384303`
    - `R^2 0.437688`
- Exported exact proxy intermediates:
  - command:
    - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python scripts/evaluation/analyze_intermediates.py --checkpoint checkpoints/proxy/tgnn_mpnn.pt --test-data notebooks/data/processed/test.csv --output-dir results/physics_bottleneck_diagnostics/tgnn_mpnn_proxy_intermediates --device cpu`
  - artifact root:
    - `results/physics_bottleneck_diagnostics/tgnn_mpnn_proxy_intermediates/`
- Ran the unified bottleneck diagnostic bundle with GC fallback enabled:
  - command:
    - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python scripts/analysis/run_physics_bottleneck_diagnostics.py --train-data notebooks/data/processed/train.csv --test-data notebooks/data/processed/test.csv --intermediates-csv results/physics_bottleneck_diagnostics/tgnn_mpnn_proxy_intermediates/intermediates.csv --output-dir results/physics_bottleneck_diagnostics_proxy --min-vh-points 3 --min-vh-temp-span 5.0 --ideal-use-gc-fallback`
  - artifact root:
    - `results/physics_bottleneck_diagnostics_proxy/`
- Exact proxy intermediates results:
  - final test MAE: `1.7413106`
  - physics-path MAE: `1.7413106`
  - final correction:
    - median absolute correction: `0.0`
    - fraction `|correction| > 0.5`: `0.0`
  - `T_m` MAE on rows with `has_T_m`: `47.5 K`
  - `tau_12`:
    - median: `1.317`
    - fraction `|tau| > 5`: `0.144`
    - fraction `|tau| > 8`: `0.0`
  - `tau_21`:
    - median: `0.907`
    - fraction `|tau| > 5`: `0.0045`
    - fraction `|tau| > 8`: `0.0`
  - `alpha` distribution is exported in the diagnostics bundle plots/JSON.
- T_m-only oracle result for the exact proxy checkpoint:
  - standard MAE: `1.7413106`
  - T_m-only oracle MAE: `1.7456180`
  - oracle T_m availability fraction: `0.443`
  - dH_fus oracle availability was intentionally disabled in this diagnostic:
    `0.0`
  - interpretation:
    - replacing available `T_m` alone does not improve the checkpoint
    - current bottleneck is not solved by T_m substitution only
    - focus should stay on NRTL/interaction identifiability, direct IDAC stream,
      pair-branch gradient rescue, and temperature-curve objectives
- GC-fallback ideal-SLE diagnostic:
  - script option added:
    - `--ideal-use-gc-fallback`
  - uses direct labels where available and Joback-style GC priors otherwise
  - train:
    - rows: `96,798`
    - source counts:
      - `labels`: `1,080`
      - `mixed_label_gc`: `51,242`
      - `gc_fallback`: `44,476`
    - ideal-SLE MAE: `3.971`
    - fraction `|ideal error| > 2`: `0.630`
  - test:
    - rows: `5,826`
    - source counts:
      - `mixed_label_gc`: `1,357`
      - `gc_fallback`: `4,469`
    - ideal-SLE MAE: `7.001`
    - fraction `|ideal error| > 2`: `0.742`
  - interpretation:
    - raw GC-prior ideal SLE is not competitive by itself
    - learned physical path dramatically improves over raw GC ideal SLE, but
      still trails DirectGNN on scaffold MAE
- Diagnostics code changes:
  - `scripts/analysis/run_physics_bottleneck_diagnostics.py`
    - added GC fallback for ideal-SLE diagnostics
    - improved Markdown labels for direct-label versus labels/GC runs
  - `src/tgnn_solv/model.py`
    - now exports `oracle_injection_masks` when
      `force_oracle_injection=True`, even if normal training config has
      `use_oracle_injection=False`
    - this fixes diagnostic summaries that previously showed
      `oracle_available_fraction_T_m=0.0` despite forced oracle evaluation
- Validation:
  - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m py_compile scripts/analysis/run_physics_bottleneck_diagnostics.py src/tgnn_solv/model.py`
    passed
  - first attempted direct pytest node ids for oracle tests were wrong and
    pytest returned `not found`; then reran correctly with:
    - `/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_integration.py -k oracle_injection -q`
    - passed: `2 passed, 29 deselected`

## 2026-04-18 - Structural Rescue CPU Smoke Ablation

Status: benchmarked smoke / not a paper result.

- Attempted a full-data CPU proxy run:
  - config: `configs/paper_config_tuned.yaml`
  - requested budget: `1/4/0`
  - log:
    - `results/ablation_proxy/train_tgnn_tuned_p1-4-0.log`
  - outcome:
    - stopped before checkpoint
    - Phase 1 took about `6` minutes
    - Phase 2 was approximately `16` minutes per epoch on CPU
    - two variants at `1/4/0` would have taken more than an hour
  - interpretation:
    - full-data CPU proxy is too slow for rapid architecture ablations
    - use deterministic smoke splits on CPU and reserve full budgets for GPU
- Created deterministic smoke artifacts:
  - `results/ablation_proxy/splits/train_smoke_4096.csv`
  - `results/ablation_proxy/splits/val_smoke_1024.csv`
  - `results/ablation_proxy/splits/idac_smoke_2048.csv`
  - split summary:
    - `results/ablation_proxy/splits/smoke_split_summary.json`
    - `results/ablation_proxy/splits/SMOKE_SPLIT.md`
  - full canonical test remained:
    - `notebooks/data/processed/test.csv`
  - raw test rows: `8,027`
  - supervised test rows used in metrics: `5,826`
- Ran matched CPU smoke trainings with budget `1/1/0`:
  - baseline:
    - config: `configs/paper_config_tuned.yaml`
    - checkpoint:
      - `checkpoints/ablation_proxy/tgnn_tuned_smoke_p1-1-0.pt`
    - log:
      - `results/ablation_proxy/train_tgnn_tuned_smoke_p1-1-0.log`
    - metrics:
      - MAE: `2.171`
      - RMSE: `2.871`
      - R2: `0.153`
      - duration: `97.0 s`
  - structural rescue:
    - config: `configs/paper_config_tuned_structural_rescue.yaml`
    - separate IDAC auxiliary stream, not appended to SLE rows:
      - `results/ablation_proxy/splits/idac_smoke_2048.csv`
      - `--idac-steps-per-epoch 2`
      - `--idac-batch-size 64`
    - checkpoint:
      - `checkpoints/ablation_proxy/tgnn_structural_rescue_smoke_p1-1-0.pt`
    - log:
      - `results/ablation_proxy/train_tgnn_structural_rescue_smoke_p1-1-0.log`
    - metrics:
      - MAE: `2.368`
      - RMSE: `3.171`
      - R2: `-0.034`
      - duration: `97.6 s`
  - delta rescue - baseline:
    - MAE: `+0.197`
    - R2: `-0.187`
- Exported intermediate and bottleneck diagnostics:
  - baseline:
    - `results/ablation_proxy/tgnn_tuned_smoke_p1-1-0_intermediates/`
    - `results/ablation_proxy/tgnn_tuned_smoke_p1-1-0_diagnostics/`
  - structural rescue:
    - `results/ablation_proxy/tgnn_structural_rescue_smoke_p1-1-0_intermediates/`
    - `results/ablation_proxy/tgnn_structural_rescue_smoke_p1-1-0_diagnostics/`
  - aggregate summary:
    - `results/ablation_proxy/summary.json`
    - `results/ablation_proxy/SUMMARY.md`
- Key diagnostic differences:
  - baseline:
    - `T_m` MAE: `48.89 K`
    - median `tau_12`: `1.011`
    - median `tau_21`: `0.986`
    - median `|Phi| / |-ln_gamma|`: `2.59`
    - correction magnitude: `0.0`
  - structural rescue:
    - `T_m` MAE: `50.12 K`
    - median `tau_12`: `0.489`
    - median `tau_21`: `0.309`
    - median `|Phi| / |-ln_gamma|`: `6.30`
    - correction magnitude: `0.0`
- Interpretation:
  - structural-rescue plumbing is runnable on CPU and IDAC aux is active as a
    separate stream
  - this very short `1/1/0` smoke worsens scaffold full-test MAE
  - the result is not evidence against the full rescue idea because:
    - budget is far below the maintained `50/200/50` curriculum
    - rescue restored the Phase-2 start checkpoint after one epoch
    - many rescue losses are enabled immediately without warmup/ramping
  - useful signal:
    - rescue compresses NRTL tau values strongly in this smoke
    - activity contribution becomes too small relative to the crystal term
    - future GPU run should test a real Phase-2 budget and consider ramping
      IDAC / aux-direct / prior weights instead of switching all rescue
      objectives on at once

## 2026-04-18 - Temperature Extrapolation Slope Diagnostics

Status: implemented / diagnosed on existing proxy checkpoints.

- Added reusable slope diagnostic:
  - `scripts/analysis/check_vant_hoff_slopes.py`
  - fits `ln_x2 = slope * (1/T) + intercept` per `(model, pair_key)`
  - accepts baseline multi-model prediction CSVs and single-model neural
    prediction/intermediate CSVs
  - exports `pair_slopes.csv`, `metrics_by_model.csv`, `worst_pairs.csv`,
    `summary.json`, `SUMMARY.md`, and diagnostic plots
- Exported and analyzed TGNN proxy temperature-extrapolation intermediates:
  - checkpoint:
    - `checkpoints/temperature_extrapolation/tgnn_solv_lowT_highT_proxy_seed42_p1-8-1.pt`
  - test split:
    - `results/temperature_extrapolation_baselines/splits/test_high.csv`
  - artifacts:
    - `results/temperature_extrapolation_slope_diagnostics/tgnn_proxy_intermediates/`
    - `results/temperature_extrapolation_slope_diagnostics/tgnn_proxy_slopes/`
    - `results/temperature_extrapolation_slope_diagnostics/tgnn_proxy_slopes_min3/`
  - metrics on full `test_high`:
    - MAE: `1.9449`
    - RMSE: `2.4811`
    - R2: `0.0602`
    - `T_m` MAE on available labels: `59.04 K`
  - important intermediate diagnostics:
    - mean correction magnitude: `1.09e-5`
    - mean correction gate: `0.935`
    - `tau_12` mean/std: `-0.00351 / 0.000048`
    - `tau_21` mean/std: `-0.00350 / 0.000048`
  - interpretation:
    - proxy TGNN activity correction is effectively inactive
    - NRTL tau collapses near zero on this run
    - temperature extrapolation is carried almost entirely by the crystal SLE
      term, not by pair-specific activity temperature dependence
- Exported DirectGNN proxy predictions from:
  - `checkpoints/temperature_extrapolation/directgnn_lowT_highT_proxy_seed42_ep10.pt`
  - prediction artifact:
    - `results/temperature_extrapolation_slope_diagnostics/directgnn_proxy_predictions.csv`
  - slope artifacts:
    - `results/temperature_extrapolation_slope_diagnostics/directgnn_proxy_slopes/`
    - `results/temperature_extrapolation_slope_diagnostics/directgnn_proxy_slopes_min3/`
- Ran baseline slope diagnostics on:
  - `results/temperature_extrapolation_baselines/predictions.csv`
  - artifacts:
    - `results/temperature_extrapolation_slope_diagnostics/baselines_test/`
    - `results/temperature_extrapolation_slope_diagnostics/baselines_test_min3/`
- Eligible high-temperature test pairs:
  - `588` pairs have at least `2` distinct high-temperature points
  - `389` pairs have at least `3` distinct high-temperature points
- Combined slope summary:
  - `results/temperature_extrapolation_slope_diagnostics/combined_slope_metrics.csv`
  - `results/temperature_extrapolation_slope_diagnostics/summary.json`
  - `results/temperature_extrapolation_slope_diagnostics/SUMMARY.md`
- Key `min_temps=3` slope metrics:
  - pair Van't Hoff:
    - `n_pairs`: `389`
    - slope MAE: `1614 K`
    - median absolute slope error: `763 K`
    - slope sign accuracy: `0.990`
    - pair MAE mean: `0.425`
  - TGNN proxy:
    - `n_pairs`: `389`
    - slope MAE: `1663 K`
    - median absolute slope error: `1158 K`
    - slope sign accuracy: `0.997`
    - predicted slope std: `327 K`
    - pair MAE mean: `1.894`
  - DirectGNN proxy:
    - `n_pairs`: `389`
    - slope MAE: `2078 K`
    - median absolute slope error: `1630 K`
    - slope sign accuracy: `0.995`
    - predicted slope std: `1848 K`
    - pair MAE mean: `1.608`
- Interpretation:
  - both neural proxies mostly get the direction of the temperature trend
    correct on multi-temperature high-T pairs
  - TGNN slope magnitude is overly compressed, with very low predicted slope
    variance
  - DirectGNN has more slope variance but weak pairwise slope correlation and
    lower value MAE than TGNN
  - the failure mode is not primarily slope sign; it is pair-specific slope
    magnitude and intercept/value calibration
- Prepared multi-temperature Van't Hoff anchor split:
  - output:
    - `results/temperature_extrapolation_slope_diagnostics/splits/train_low_vh_anchor_325_340_355_370_385.csv`
  - fit table:
    - `results/temperature_extrapolation_slope_diagnostics/splits/train_low_vh_anchor_325_340_355_370_385.csv.fits.csv`
  - summary:
    - `results/temperature_extrapolation_slope_diagnostics/vh_anchor_325_340_355_370_385_summary.json`
  - input rows: `7120`
  - output rows: `13675`
  - anchor rows: `6555`
  - fit pairs: `1311`
  - anchor temperatures: `325`, `340`, `355`, `370`, `385 K`
  - anchor weight: `0.8`
  - median low-T fit R2: `0.997269`
  - median low-T fit RMSE: `0.009509 ln(x2)`
- Next GPU experiment candidate:
  - train TGNN on the multi-temperature VH-anchor split instead of the
    single-350 K anchor
  - keep expanded IDAC as a separate auxiliary stream, not appended to SLE
    rows
  - compare against the existing `1/8/1` TGNN proxy and DirectGNN proxy on
    both value MAE and slope diagnostics

## 2026-04-18 - Temperature Rescue Objective Plumbing

Status: implemented / smoke-tested, not benchmarked.

- Added fit-table slope/intercept supervision plumbing for temperature
  extrapolation rescue:
  - `src/tgnn_solv/loss.py`
  - `src/tgnn_solv/data/dataset.py`
  - `src/tgnn_solv/config.py`
  - `src/tgnn_solv/trainer.py`
- `scripts/data/build_vant_hoff_anchor_split.py` now annotates fitted pairs
  with explicit `vh_fit_*` metadata on real low-temperature rows and generated
  Van't Hoff anchor rows:
  - `has_vh_fit`
  - `vh_fit_slope`
  - `vh_fit_intercept`
  - `vh_fit_r2`
  - `vh_fit_rmse`
  - `vh_fit_weight`
- Regenerated the maintained multi-temperature VH-anchor split:
  - `results/temperature_extrapolation_slope_diagnostics/splits/train_low_vh_anchor_325_340_355_370_385.csv`
  - summary:
    - `results/temperature_extrapolation_slope_diagnostics/vh_anchor_325_340_355_370_385_summary.json`
  - input rows: `7120`
  - output rows: `13675`
  - anchor rows: `6555`
  - rows with `vh_fit_*` metadata: `12663`
  - real fitted rows with `vh_fit_*` metadata: `6108`
  - fit pairs: `1311`
  - anchor temperatures: `325`, `340`, `355`, `370`, `385 K`
  - median low-T fit R2: `0.997269`
  - median low-T fit RMSE: `0.009509 ln(x2)`
- `TGNNSolvDataset` now emits optional VH fit targets:
  - `vh_fit_slope`
  - `vh_fit_intercept`
  - `vh_fit_r2`
  - `vh_fit_rmse`
  - `vh_fit_weight`
  - `vh_fit_mask`
  - legacy `vh_anchor_slope` / `vh_anchor_intercept` columns remain supported
    as fallback input
- `TGNNSolvLoss._pair_temperature_losses(...)` now supports explicit
  Van't Hoff fit targets:
  - same loss keys are reused:
    - `vant_hoff_slope`
    - `vant_hoff_intercept`
  - explicit targets work even when `has_solubility=False`, enabling
    anchor-only rows to supervise curve slope/intercept
  - explicit fit targets are filtered by `cfg.vant_hoff_fit_r2_min`
    - default: `0.95`
- Added Phase-2 ramp support:
  - config field: `temperature_rescue_ramp_epochs`
  - default: `0` (disabled)
  - when enabled, Phase-2 ramps:
    - `aux_direct_sol`
    - `pair_temp_delta`
    - `vant_hoff_slope`
    - `vant_hoff_intercept`
    - `vh_anchor`
- Added candidate temperature-rescue config:
  - `configs/paper_config_tuned_temperature_rescue.yaml`
  - key settings:
    - `explicit_h_small_molecules: true`
    - `fusion_output_mode: entropy_coupled`
    - `use_aux_direct_sol_loss: true`
    - `detach_crystal_from_encoder: true`
    - `temperature_rescue_ramp_epochs: 25`
    - `pair_temperature_group_chunk_size: 6`
    - `bridge: 0.0` in Phase 2/3
    - Phase-2 `vh_anchor: 0.8`
    - Phase-2 `vant_hoff_slope: 0.10`
    - Phase-2 `vant_hoff_intercept: 0.02`
- Smoke artifacts:
  - `results/temperature_rescue_plumbing_smoke/summary.json`
  - `results/temperature_rescue_plumbing_smoke/summary_with_anchors.json`
  - `results/temperature_rescue_plumbing_smoke/SUMMARY.md`
  - anchor-containing smoke batch:
    - rows: `11`
    - VH-anchor rows: `5`
    - VH-fit rows: `11`
    - minimum fit R2: `0.9963`
    - active raw losses:
      - `sol`
      - `vh_anchor`
      - `vant_hoff_slope`
      - `vant_hoff_intercept`
      - `walden`
- Tests and checks:
  - `py_compile` passed for changed Python modules
  - targeted pytest passed:
    - `tests/test_loss.py`
    - `tests/test_dataset.py`
    - `tests/test_trainer_resume.py`
  - JSON validation passed for smoke summaries and VH-anchor summary
  - `git diff --check` passed for changed files
- Next benchmark:
  - run `configs/paper_config_tuned_temperature_rescue.yaml` on the
    multi-temperature VH-anchor split with expanded IDAC passed as
    `--idac-train-data`
  - evaluate both value metrics and `check_vant_hoff_slopes.py` slope metrics

## Update Rules

Update this file after any significant incident, including:

- new benchmark result
- failed or unstable training run
- split/protocol change
- important documentation drift discovery
- environment/runtime issue affecting reproducibility
- new accepted hypothesis or rejection of an old one
- artifact contract change
- accepted research direction, experiment idea, or architecture idea that is
  likely to guide future implementation, even before it has benchmark results

Each update should be:

- dated
- factual
- concise
- linked to concrete files under `results/`, `logs/`, `docs/`, or source code
- clear about status:
  - implemented
  - plumbing-only
  - benchmarked
  - hypothesis
  - idea / not yet validated

## 2026-04-18 - Supervisor-Facing Report Rewrite

Status: documentation drafted for external scientific review and compute-resource request.

- Added supervisor-facing report files under `reports/`:
  - `reports/supervisor_report_short.md`
    - concise sending version in Russian
    - focuses on completed work, current results, and compute-resource need
  - `reports/supervisor_report_full.md`
    - fuller article-like report in Russian with appendices and tables
    - consolidates data, thermodynamics, architecture, training/evaluation,
      scaffold results, temperature diagnostics, IDAC/UNIFAC expansion,
      water handling, structural-extrapolation diagnostics, negative results,
      reproducibility pointers, and GPU resource justification
  - `reports/supervisor_request_letter.md`
    - short draft cover letter for requesting scientific supervision and GPU
      resources
- Writing decisions:
  - reduced diary-like narrative and future-idea sprawl from older report style
  - avoided a standalone glossary and explained key terms near first use
  - kept English model names only where they are project identifiers
  - treated the report as completed-work documentation with a bounded compute
    request, not as user documentation or an open-ended roadmap
- Current word counts from `wc -w`:
  - short report: `2059`
  - full report: `6355`
  - cover letter: `266`
- These reports should be preferred over old `main.tex` for initial supervisor
  outreach, while `PROJECT_DESCRIPTION.md` and `PROJECT_MEMORY.md` remain the
  internal agent-oriented technical references.

## 2026-04-19 - Supervisor Report Converted To TeX/PDF

Status: completed / compiled with XeLaTeX.

- Reworked the supervisor-facing reports into TeX as the primary deliverables,
  following the formatting style of the original `main.tex` report:
  - `reports/supervisor_report_short.tex`
  - `reports/supervisor_report_full.tex`
  - `reports/supervisor_request_letter.tex`
- Compiled PDFs were generated successfully:
  - `reports/supervisor_report_short.pdf` (`5` pages)
  - `reports/supervisor_report_full.pdf` (`28` pages)
  - `reports/supervisor_request_letter.pdf` (`1` page)
- Formatting choices:
  - XeLaTeX + `fontspec` / `polyglossia`
  - Times New Roman was used because the local TeX install does not expose the
    original `CMU Serif` font used in `main.tex`
  - tables use `booktabs`, `tabularx`, and the same article-style structure as
    the original report
- Full report additions relative to the first Markdown draft:
  - all formulas are native TeX math, not code blocks
  - added mathematical appendices for:
    - SLE derivation from chemical potentials
    - fusion free-energy expression including `Delta C_p`
    - NRTL and IDAC infinite-dilution formula
    - fixed-point formulation and implicit differentiation
    - sensitivity estimates for `T_m`, `Delta H_fus`, and `Delta C_p`
    - Van't Hoff slope interpretation and conditioning estimates
    - identifiability / compensatory degeneracy
    - error propagation through the physics bottleneck
    - water one-atom graph degeneracy and explicit-H justification
    - statistical interpretation of the `+0.089 MAE` TGNN-vs-DirectGNN gap
    - structural-vs-temperature extrapolation distinction
    - Hansen delta compatibility objective
    - compute-resource estimate
- Older Markdown report drafts were moved to:
  - `reports/drafts_markdown/`
  - they are retained only as drafts; TeX/PDF files in `reports/` are the
    current supervisor-facing artifacts.
- Validation:
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error supervisor_report_short.tex supervisor_report_full.tex supervisor_request_letter.tex`
    completed successfully from `reports/`
  - only layout warnings remained (`Underfull/Overfull hbox`), no TeX errors.

## 2026-04-19 - Supervisor Reports Illustrated

Status: completed / compiled with figures.

- Added visual material to the supervisor-facing TeX reports:
  - `reports/supervisor_report_short.tex`
  - `reports/supervisor_report_full.tex`
- Regenerated PDFs successfully:
  - `reports/supervisor_report_short.pdf` (`7` pages)
  - `reports/supervisor_report_full.pdf` (`36` pages)
  - `reports/supervisor_request_letter.pdf` (`1` page, unchanged except rebuilt)
- Figure assets live under `reports/figures/`.
  - Reused presentation/result figures copied from `presentation/figures/generated/`, including corpus distributions, SLE/NRTL examples, prediction-slice comparisons, temperature extrapolation/interpolation baselines, gradient-flow diagrams, sensitivity and error-decomposition figures.
  - Added new report-specific schematic figures via `reports/figures/build_report_figures.py`:
    - `architecture_schematic.pdf`
    - `sle_decomposition_schematic.pdf`
    - `evaluation_regimes_schematic.pdf`
    - `water_graph_schematic.pdf`
    - `idac_expansion_bars.pdf`
    - `compute_plan_schematic.pdf`
- The short report now contains the core architecture schematic, scaffold-model comparison, water graph correction, SLE decomposition, temperature-extrapolation comparison, and compute-plan schematic.
- The full report now additionally contains corpus distribution figures, ideal-SLE and NRTL illustrations, pair-error diagnostics, chemistry-slice diagnostics, IDAC expansion, sensitivity heatmap, error-propagation waterfall, and gradient-flow/fix diagrams.
- Validation command:
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error supervisor_report_short.tex supervisor_report_full.tex supervisor_request_letter.tex`
- Validation result:
  - successful XeLaTeX build from `reports/`
  - only layout warnings remained (`Underfull/Overfull hbox`), no TeX errors
  - temporary LaTeX build files were cleaned with `latexmk -c` after PDF generation.

## 2026-04-19 - Supervisor Reports Design Cleanup

Status: completed / compiled after visual and editorial cleanup.

- Reworked `reports/figures/build_report_figures.py` to regenerate the full inserted figure set in a single minimalist style:
  - soft low-saturation palette
  - rounded Figma-style schematic boxes
  - cleaner arrow routing
  - English-only text inside figure PDFs
  - no mixed presentation palettes in the report figures
- Regenerated all report figure PDFs under `reports/figures/`, including corpus distributions, SLE/NRTL illustrations, model-comparison charts, temperature baseline plots, gradient-flow diagrams, sensitivity heatmap, error-decomposition waterfall, IDAC expansion, and architecture/evaluation/water schematics.
- Removed from the reports:
  - standalone resource-request section from `reports/supervisor_report_full.tex`
  - standalone compute-resource section from `reports/supervisor_report_short.tex`
  - compute-plan figure from both reports
  - artifact-map appendix from `reports/supervisor_report_full.tex`
  - internal `PROJECT_DESCRIPTION.md` artifact pointer from the supervisor-facing full report
- Edited wording in the reports to reduce slang-like phrasing such as "physics tax", "bottleneck", and explicit resource-request language; the cover letter remains the place where compute resources are requested.
- Rebuilt PDFs successfully:
  - `reports/supervisor_report_short.pdf` (`7` pages)
  - `reports/supervisor_report_full.pdf` (`34` pages)
  - `reports/supervisor_request_letter.pdf` (`1` page)
- Validation:
  - XeLaTeX build completed successfully from `reports/`
  - only layout warnings remained (`Underfull/Overfull hbox`), no TeX errors
  - `pdftotext` check found no removed resource/artifact section headings in the short/full report PDFs
  - `pdftotext` check over `reports/figures/*.pdf` found zero Cyrillic labels inside figure files
  - temporary LaTeX build files were cleaned with `latexmk -c` after PDF generation.

## 2026-04-19 - Supervisor Reports Editorial Revision After Feedback

Status: completed / compiled after substantive proofreading and structure pass.

- Edited the supervisor-facing TeX reports in response to feedback that the old report was too diary-like, jargon-heavy, and missing context for a new scientific supervisor:
  - `reports/supervisor_report_short.tex`
  - `reports/supervisor_report_full.tex`
- Added early terminology sections:
  - full report: `Ключевые термины и обозначения`
  - short report: compact `Ключевые термины`
  - terms now define `SLE`, `GNN`, `NRTL`, `IDAC`, `UNIFAC`, molecular scaffold, DirectGNN/TGNN-Solv, group-contribution priors, oracle diagnostics, and full training budget in Russian explanatory language.
- Rewrote the problem statement to explain:
  - why solubility matters experimentally and industrially
  - why structure, crystal packing, solvent compatibility, polarity, hydrogen bonding, and temperature make the task difficult
  - what physical interpretability gives a researcher beyond a single scalar prediction
- Updated the data section from current processed CSV facts rather than old narrative numbers:
  - processed `train/val/test` rows: `127,088`
  - supervised solubility rows: `108,287`
  - unique supervised solutes: `1,525`
  - unique supervised solvents: `212`
  - supervised solute-solvent pairs: `12,129`
  - temperature range: `243.15`-`425.77 K`
  - mean / median rows per pair: `8.93` / `9`
  - exact duplicate `(solute, solvent, T)` triples with conflicting `ln_x2`: `0`
- Added a full-report section `Обзор существующих подходов и внешних ориентиров` with a compact literature/method table covering:
  - empirical/QSPR/RF descriptors
  - UNIFAC / Modified UNIFAC
  - NRTL / Wilson / UNIQUAC
  - graph neural networks
  - external SolProp and FastSolv baselines
- Added bibliography entries in the full report for BigSolDB, NRTL, Wilson, UNIQUAC, UNIFAC, Modified UNIFAC, MPNN/GAT/Chemprop-style graph models, SolProp, and FastSolv-related external work.
- Reduced mixed Russian-English phrasing in the report body:
  - replaced `supervised` wording with Russian equivalents
  - replaced visible `scaffold` prose with `разбиение по новым каркасам` / `молекулярный каркас`
  - kept English only where it is a model name, data/tool name, acronym defined in the glossary, or figure-internal label
- Validation:
  - rebuilt from `reports/` with `latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error supervisor_report_full.tex supervisor_report_short.tex supervisor_request_letter.tex`
  - cleaned LaTeX temporaries with `latexmk -c`
  - current PDFs:
    - `reports/supervisor_report_short.pdf` (`9` pages, `195,801` bytes)
    - `reports/supervisor_report_full.pdf` (`38` pages, `631,819` bytes)
    - `reports/supervisor_request_letter.pdf` (`1` page, `36,996` bytes)
  - `pdftotext` check found no standalone resource-request/artifact-map headings and no `supervised`, `full-budget`, `GC priors`, or `solubility-модели` residue in the PDFs.
  - `pdftotext` over `reports/figures/*.pdf` found zero Cyrillic labels inside figure files; graph labels remain English as requested.

## 2026-04-19 - Supervisor Reports References and Figure Readability Pass

Status: completed / compiled.

- Updated the supervisor-facing report sources:
  - `reports/supervisor_report_full.tex`
  - `reports/supervisor_report_short.tex`
- Ensured the previously paired/two-column report figures are represented as readable single-column figures; validation found no remaining `minipage`/`subfigure` blocks and no narrow `includegraphics` widths below `0.6\textwidth` in the short/full report TeX files.
- Expanded citation coverage:
  - full report now has `33` `\cite{...}` calls and `38` bibliography entries
  - short report now has `10` `\cite{...}` calls and a compact `15`-entry bibliography
  - added citations around BigSolDB, SLE thermodynamics, NRTL, UNIFAC/Modified UNIFAC, Hansen parameters, ThermoML/IDAC, RDKit/GNNs, SolProp/FastSolv, entropy/fusion data, and training/loss methodology
- Added a compact bibliography to `reports/supervisor_report_short.tex` so the short version is also citable as a standalone scientific summary.
- Rebuilt PDFs successfully from `reports/`:
  - `reports/supervisor_report_full.pdf` (`43` pages, `652,825` bytes)
  - `reports/supervisor_report_short.pdf` (`10` pages, `238,533` bytes)
  - `reports/supervisor_request_letter.pdf` (`1` page, `36,995` bytes)
- Validation:
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error supervisor_report_full.tex supervisor_report_short.tex supervisor_request_letter.tex`
  - no unresolved citation/reference warnings remained in final logs
  - `pdftotext` checks found no `??`, undefined-reference text, standalone resource-request headings, artifact-map headings, or removed jargon residues
  - temporary LaTeX build files were cleaned with `latexmk -c` after PDF generation.

## 2026-04-19 - Supervisor Report Formula Numbering and Corpus Plot Fix

Status: completed / compiled.

- Updated the supervisor report TeX sources so only equations referenced from the text remain numbered:
  - `reports/supervisor_report_full.tex`: only `eq:phi-dcp`, `eq:nrtl`, `eq:idac`, and `eq:error-propagation` remain in numbered `equation` environments
  - `reports/supervisor_report_short.tex`: only `eq:sle-short` remains numbered
  - all other display equations/alignments were converted to starred environments
- Investigated the apparent zero peak in the first report figures:
  - processed `train/val/test` contain `127,088` rows total
  - `18,801` auxiliary non-solubility rows have `has_solubility=False` and placeholder `ln_x2=0`
  - the actual SLE subset has `108,287` rows, zero exact `ln_x2=0` values, and maximum `ln_x2=-0.0465676358163347`
  - therefore the zero peak was a report-figure bug, not a BigSolDB/SLE dataset issue
- Fixed `reports/figures/build_report_figures.py`:
  - added `solubility_rows(...)`
  - `corpus_lnx2_histogram()` and `corpus_points_per_pair()` now filter `has_solubility=True`
  - regenerated report figures under `reports/figures/`
- Rebuilt PDFs successfully:
  - `reports/supervisor_report_full.pdf` (`43` pages, `650,998` bytes)
  - `reports/supervisor_report_short.pdf` (`10` pages, `238,418` bytes)
  - `reports/supervisor_request_letter.pdf` (`1` page, `37,001` bytes)
- Validation:
  - final `latexmk -xelatex` build had no unresolved citation/reference warnings in the final logs
  - `pdftotext` checks found no `??`, undefined-reference text, standalone resource-request headings, artifact-map headings, or removed jargon residues
  - temporary LaTeX build files were cleaned with `latexmk -c`.

## 2026-04-19 - Supervisor Report Restored Training/Loss/Pretraining Content

Status: completed / compiled.

- Reworked the supervisor report as a strengthened revision of the original `main.tex` narrative rather than a second standalone summary.
- Updated `reports/supervisor_report_full.tex`:
  - added a dedicated section `Обучение, функция ошибки и протокол оценки`
  - restored/condensed the original-report content on Stage 0 encoder pretraining, the three-phase 50/200/50 training schedule, Huber solubility loss, masked auxiliary property losses, IDAC auxiliary stream, Hansen pair losses, temperature regularizers, regularization, oracle substitution, and GC-prior residual warm start
  - added `Актуальные рабочие гипотезы` with explicit hypotheses on crystal-branch capture, NRTL underidentifiability, temperature-slope failure, pair/fragment structural extrapolation, and systematic physics errors (`Delta Cp`, water graphs, bridge loss)
  - added appendix `Формальная запись предобучения и функции ошибки` with mathematical objectives for masked atom/bond prediction, RDKit descriptor prediction, contrastive InfoNCE-style pretraining, masked property losses, and pair slope matching
  - removed visible awkward wording such as `солют`; replaced it with `вещество` / `растворяемое вещество`
- Updated `reports/supervisor_report_short.tex` with a compact section explaining how the model is trained and how the loss is composed, while keeping the short PDF at 10 pages.
- Updated `reports/figures/build_report_figures.py` and regenerated figures:
  - `rdkit_molecular_graph_examples.pdf` using RDKit 2D coordinates for paracetamol, ethanol, and explicit-H water
  - `pretraining_tasks_schematic.pdf`
  - `training_curriculum_schematic.pdf`
  - `loss_components_schematic.pdf`
  - `hypothesis_map_schematic.pdf`
- Rebuilt PDFs successfully:
  - `reports/supervisor_report_full.pdf`: 50 pages, 766,224 bytes
  - `reports/supervisor_report_short.pdf`: 10 pages, 241,227 bytes
- Validation:
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
  - final logs have no unresolved citation/reference warnings
  - equation numbering remains limited to formulas referenced by `\eqref`: full report has `eq:phi-dcp`, `eq:nrtl`, `eq:idac`, `eq:error-propagation`; short report has `eq:sle-short`
  - `pdftotext` checks found no visible Russian `солют` or `лосс` residue in report text; remaining English `head/loss/pretraining/curriculum` terms are inside English-labeled figures or bibliography/model names.

## 2026-04-19 - Supervisor Report Worked Example and Identifiability Pass

Status: completed / compiled.

- Updated `reports/supervisor_report_full.tex` as an editorial/scientific strengthening pass:
  - added an opening graphical abstract figure for the TGNN-Solv logic
  - added main-text sensitivity estimates showing how errors in `T_m`, `dH_fus`, and omitted `dCp_fus` propagate into `ln x2`
  - added an identifiability schematic explaining why SLE-only training cannot uniquely determine crystal and NRTL contributions
  - added a worked paracetamol-in-ethanol example tracing the model path from molecular graphs to `Phi(T)`, `ln gamma2`, and `ln x2`
  - strengthened the DirectGNN section so it is explicitly framed as a controlled ablation of the physics bottleneck rather than just another baseline
  - clarified the Van't Hoff slope interpretation for temperature extrapolation
  - replaced the readiness/resource-style section with `Подготовленные проверки и оставшаяся неопределённость`
  - rewrote the conclusion to emphasize the current scientific state: scaffold MAE still favors DirectGNN, while same-pair Van't Hoff results show that the physical temperature signal is strong but not yet learned reliably by TGNN-Solv
- Updated `reports/figures/build_report_figures.py` and regenerated `29` report figures, including:
  - `reports/figures/graphical_abstract_schematic.pdf`
  - `reports/figures/worked_example_trace.pdf`
  - `reports/figures/identifiability_constraints_schematic.pdf`
  - RDKit-coordinate molecular graph examples reused by report figures
- Performed an additional terminology cleanup in visible Russian report text:
  - replaced `супервизия` / `супервизирован` wording with `обучающий сигнал`, `прямые метки`, or `IDAC-данные`
  - validation found no remaining visible `супервиз`, `лосс`, `GC priors`, or `full-budget` residues in the report TeX sources
- Rebuilt PDFs successfully:
  - `reports/supervisor_report_full.pdf`: `55` pages, `856,948` bytes
  - `reports/supervisor_report_short.pdf`: `10` pages, `241,212` bytes
- Validation:
  - `python reports/figures/build_report_figures.py`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
  - final logs have no unresolved citation/reference warnings
  - equation numbering remains limited to formulas referenced by `\eqref`: full report has `eq:phi-dcp`, `eq:nrtl`, `eq:idac`, `eq:error-propagation`; short report has `eq:sle-short`

## 2026-04-19 - Temperature Extrapolation Split Audit

Status: completed / diagnostic artifacts written.

- Added reproducible audit script:
  - `scripts/analysis/audit_temperature_extrapolation_split.py`
- Ran it on the maintained low-to-high temperature split and wrote:
  - `results/temperature_extrapolation_baselines/audit/README.md`
  - `results/temperature_extrapolation_baselines/audit/split_audit_summary.json`
  - `results/temperature_extrapolation_baselines/audit/pair_low_high_trends.csv`
  - `results/temperature_extrapolation_baselines/audit/train_low_vant_hoff_fits.csv`
- Main findings:
  - `train_low`, `val_low`, and `test_high` all contain exactly `1,751` unique pairs.
  - Pair overlap `train_low ∩ test_high` is `1,751 / 1,751 = 100%`, so the protocol is confirmed as same-pair temperature extrapolation, not new-pair or scaffold extrapolation.
  - The split is built from the combined processed corpus: `train_low` includes `297` rows whose original `source_split` was `test`, and `test_high` includes `120` such rows. This is acceptable for a standalone same-pair temperature protocol but must not be mixed with scaffold-split leakage claims.
  - `test_high` water fraction is `408 / 3,343 = 12.2%` rows and `145 / 1,751 = 8.3%` pairs; water is not dominant and cannot explain the full neural temperature-extrapolation gap by itself.
  - `test_high` small-solvent fraction (`<=3` heavy atoms) is `29.6%` rows and `29.8%` pairs.
  - Observed high-minus-low solubility shift is positive for `99.6%` of pairs; the data are not dominated by reversed/exothermic temperature trends.
  - Low-temperature pair Van't Hoff fits have median `R2=0.999`, positive `d ln(x2)/dT` in `99.1%` of pairs, and high-T mean/median MAE `0.315 / 0.140` by pair-level recomputation.
  - Water pairs are harder for pair Van't Hoff too: water high-T MAE mean `0.657` vs nonwater `0.284`.
- Existing baseline artifacts remain consistent:
  - pair Van't Hoff test MAE `0.368`, direction accuracy `99.0%`.
  - RF(Morgan+T) test MAE `1.290`, direction accuracy `40.4%`, mean predicted high shift `-0.054` despite true mean high shift `+1.110`; this is best interpreted as RF temperature-feature extrapolation failure, not as a data trend reversal.
- Solver settings in `configs/paper_config_tuned.yaml`:
  - `n_iter_train=5`, `n_iter_eval=20`, `damping=0.7`, `solver_min_damping=0.1`, `solver_adaptive_damping=true`.
  - No immediate solver configuration bug was found, but `n_iter_train=5` remains a plausible training-stability bottleneck for hard high-temperature extrapolation.
- Log inspection for `logs/temperature_extrapolation/tgnn_solv_lowT_highT_proxy_seed42_p1-8-1.stdout.log`:
  - no catastrophic Phase 2 loss explosion was observed; validation MAE improves from initial Phase 2 `2.431` to about `2.124` by Phase 3 validation.
  - proxy budget remains a major caveat: the run used `1/8/1`, far below canonical `50/200/50`.

## 2026-04-19 - Supervisor Reports Include Temperature Audit Results

Status: completed / compiled.

- Integrated the reproducible temperature-extrapolation split audit into both supervisor-facing reports:
  - `reports/supervisor_report_full.tex`
  - `reports/supervisor_report_short.tex`
- Added a new report figure generated from the audit JSON:
  - `reports/figures/temperature_protocol_audit.pdf`
  - source: `reports/figures/build_report_figures.py`
- Full report now explicitly states that the low-to-high temperature split is a same-pair protocol:
  - `train_low`, `val_low`, and `test_high` each contain `1,751` unique pairs.
  - `train_low ∩ test_high = 1,751 / 1,751 = 100.0%`.
  - This is a known-pair temperature extrapolation test, not a scaffold/new-pair structural extrapolation test.
- Added the audit table to the full report with the current key numbers:
  - row counts: `7,120 / 1,751 / 3,343` for `train_low / val_low / test_high`.
  - test water fraction: `12.2%` rows.
  - test small-solvent fraction (`<=3` heavy atoms): `29.6%` rows.
  - observed positive high-minus-low shift: `99.6%` of pairs.
  - median low-temperature Van't Hoff fit `R2=0.999`.
  - low-temperature fit high-temperature mean/median MAE: `0.315 / 0.140`.
- Reframed the Van't Hoff result in the report:
  - it remains the physical reference for how much information is present in the temperature series;
  - it is pair-fitted and should not be described as a fair direct competitor for de novo/new-pair neural prediction.
- Rebuilt report PDFs successfully:
  - `reports/supervisor_report_full.pdf`: `56` pages, `885,113` bytes.
  - `reports/supervisor_report_short.pdf`: `10` pages, `242,068` bytes.
- Validation:
  - `python reports/figures/build_report_figures.py`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
  - final LaTeX logs have no unresolved citation/reference warnings.
  - numbered equations remain limited to formulas referenced by `\eqref`: full report has `eq:phi-dcp`, `eq:nrtl`, `eq:idac`, `eq:error-propagation`; short report has `eq:sle-short`.
  - visible PDF text check found no remaining `супервиз`, `лосс`, `GC priors`, `full-budget`, `de novo`, or `known-pair` residues.

## 2026-04-19 - Temperature Extrapolation Failure Diagnostics Integrated

Status: completed / report-updated.

- Added and ran consolidated analysis script:
  - `scripts/analysis/run_temperature_failure_diagnostics.py`
- Wrote diagnostic bundle:
  - `results/temperature_extrapolation_failure_diagnostics/summary.json`
  - `results/temperature_extrapolation_failure_diagnostics/row_metrics.csv`
  - `results/temperature_extrapolation_failure_diagnostics/slope_metrics_min3.csv`
  - `results/temperature_extrapolation_failure_diagnostics/pair_slopes_min3.csv`
  - `results/temperature_extrapolation_failure_diagnostics/chemistry_slices.csv`
  - `results/temperature_extrapolation_failure_diagnostics/tgnn_internal_summary.json`
  - `results/temperature_extrapolation_failure_diagnostics/solver_budget_audit.json`
- Main same-pair high-temperature row metrics remain:
  - pair Van't Hoff: MAE `0.368`, R2 `0.887`.
  - DirectGNN proxy (`10` epochs): MAE `1.619`, R2 `0.283`.
  - TGNN-Solv proxy (`1/8/1`): MAE `1.945`, R2 `0.060`.
  - TGNN physics-only output is effectively identical to final output: MAE `1.945`; bounded correction is inactive.
- Slope diagnostics on pairs with at least `3` high-temperature points (`389` pairs):
  - pair Van't Hoff: per-pair MAE `0.425`, median slope error `763 K`, sign accuracy `99.0%`.
  - DirectGNN proxy: per-pair MAE `1.608`, median slope error `1630 K`, sign accuracy `99.5%`.
  - TGNN-Solv proxy: per-pair MAE `1.894`, median slope error `1158 K`, sign accuracy `99.7%`.
  - RF(Morgan+T): per-pair MAE `1.280`, median slope error `3386 K`, sign accuracy `56.0%`.
- TGNN proxy internal diagnosis:
  - true `ln_x2` std in `test_high`: `2.560`.
  - TGNN final prediction std: `0.582`, so predictions are strongly compressed.
  - `std(tau_12)=4.83e-05`, `std(tau_21)=4.81e-05`, `std(ln_gamma2)=2.86e-04`; NRTL branch is nearly collapsed / pair-insensitive in the proxy run.
  - mean `|ln_x2_final - ln_x2_physics| = 1.09e-05`; adaptive correction path is effectively inactive.
  - on rows with `T_m` labels, `T_m` MAE is `59.0 K`; substituting oracle `T_m` only changes overall MAE from `1.945` to `1.903` (`-0.042`), so the proxy failure is not explained by the crystal head alone.
- Chemistry slices in `test_high`:
  - water solvent: Van't Hoff `0.604`, DirectGNN `2.092`, TGNN `2.455` MAE.
  - small solvents (`<=3` heavy atoms): Van't Hoff `0.444`, DirectGNN `1.833`, TGNN `2.143` MAE.
  - aromatic solvents: Van't Hoff `0.216`, DirectGNN `1.661`, TGNN `2.018` MAE.
  - low-solubility rows (`ln_x2 <= -8`): Van't Hoff `0.579`, DirectGNN `4.119`, TGNN `5.218` MAE.
  - rows with `T >= 360 K`: Van't Hoff `1.121`, DirectGNN `1.549`, TGNN `1.662` MAE.
- Solver/budget audit:
  - tuned config uses `n_iter_train=5`, `n_iter_eval=20`, `damping=0.7`, `solver_min_damping=0.1`, `solver_adaptive_damping=true`.
  - no immediate solver configuration bug was found, but all neural temperature-extrapolation numbers remain proxy-budget evidence, not final full-curriculum results.
- Updated report figures via `reports/figures/build_report_figures.py`:
  - `reports/figures/temperature_slope_recovery_diagnostics.pdf`
  - `reports/figures/temperature_tgnn_internal_diagnostics.pdf`
  - `reports/figures/temperature_chemistry_slice_diagnostics.pdf`
- Updated both supervisor reports:
  - `reports/supervisor_report_full.tex` / `.pdf`
  - `reports/supervisor_report_short.tex` / `.pdf`
- Rebuilt PDFs:
  - `reports/supervisor_report_full.pdf`: `59` pages, `953,628` bytes.
  - `reports/supervisor_report_short.pdf`: `11` pages, `264,858` bytes.
- Validation:
  - `python scripts/analysis/run_temperature_failure_diagnostics.py`
  - `python reports/figures/build_report_figures.py`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
  - final logs have no unresolved citation/reference warnings and no overfull boxes.
  - `python -m py_compile scripts/analysis/run_temperature_failure_diagnostics.py scripts/analysis/audit_temperature_extrapolation_split.py reports/figures/build_report_figures.py`
- Current interpretation:
  - The weak TGNN proxy result is now localized: the NRTL/activity branch is nearly constant, the final correction is inactive, and the model compresses the high-temperature solubility distribution.
  - Water and small solvents are harder but do not fully explain the failure; the low-solubility tail is the most severe slice.
  - Next GPU/full-budget test must report not only MAE/R2 but also prediction std, NRTL parameter variance, `ln_gamma2` variance, correction magnitude, and Van't Hoff slope recovery.

## 2026-04-19 - Supervisor Report Architecture and Training Coverage Pass

Status: completed / report-updated.

- Expanded `reports/supervisor_report_full.tex` and `reports/supervisor_report_short.tex` to cover architecture and training details that were missing from the previous rewrite:
  - atom/bond feature rationale and why atomic number alone is insufficient;
  - latent molecular and pair vector sizes and why high-dimensional representations are used;
  - MPNN message passing, GPS/global attention, TIMP dispersive/polar channel decomposition;
  - Hansen-contrastive and TIMP channel diagnostics from the seminar material;
  - solute-solvent cross-attention, interaction-gradient starvation, and implemented rescue mechanisms;
  - solvent-type MoE in the pair/physics path;
  - physical temperature encoding versus DirectGNN thermometer encoding;
  - adaptive parameter-space correction with a second SLE solve;
  - Stage 0 pretraining tasks: masked atom/subgraph recovery, bond prediction, RDKit-property regression, and molecular contrastive learning;
  - pair-aware batching, Van't Hoff local/rank losses, vH-loss scale failure, and bridge-loss caveat;
  - uncertainty, calibration, applicability-domain diagnostics, application workflows, and modelability/KNN evidence.
- Reworked `reports/figures/build_report_figures.py`:
  - removed RDKit molecular graph examples and the worked-example trace from the report figure set;
  - added `graph_mechanisms_schematic.pdf`, `interaction_rescue_schematic.pdf`, `correction_loop_schematic.pdf`, `temperature_encoding_schematic.pdf`, `timp_hansen_diagnostics.pdf`, and `uncertainty_ad_schematic.pdf`;
  - expanded/relaid out `architecture_schematic.pdf`, `identifiability_constraints_schematic.pdf`, and `temperature_protocol_audit.pdf` to reduce cramped labels and arrow/block overlap.
- Rebuilt figures and reports:
  - `reports/supervisor_report_full.pdf`: `66` pages, `1,068,818` bytes.
  - `reports/supervisor_report_short.pdf`: `11` pages, `270,413` bytes.
- Validation:
  - `python -m py_compile reports/figures/build_report_figures.py`
  - `python reports/figures/build_report_figures.py`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
  - final LaTeX logs have no unresolved citation/reference warnings and no overfull boxes; only non-fatal underfull-box warnings remain.

## 2026-04-19 - Supervisor Report Data Collection and IDAC Corpus Pass

Status: completed / report-updated.

- Expanded the data section in `reports/supervisor_report_full.tex` and `reports/supervisor_report_short.tex` so data collection is described as a substantive part of the work, not just a row-count table.
- Added main-corpus preparation details:
  - BigSolDB v2.1 as the primary SLE source;
  - canonical SMILES, Kelvin temperatures, `ln_x2` target contract;
  - explicit mask columns for sparse auxiliary labels;
  - source/provenance tracking and duplicate/conflict audits.
- Added full IDAC corpus construction narrative:
  - starter IDAC corpus: `404` rows, `138` pairs, `9` DOI (`notebooks/data/raw/idac.csv` / Zenodo starter release);
  - NIST ThermoML extraction via DOI/archive discovery, cached JSON, binary infinite-dilution activity-coefficient filtering, InChI-to-SMILES standardization through RDKit, `gamma_inf -> ln_gamma_inf`, exact deduplication and pair-temperature aggregation;
  - expanded IDAC corpus: `14,900` rows, `3,145` pairs, `136` solutes, `112` solvents, `63` DOI, temperature range `273.17-438.0 K`, `ln_gamma_inf` range `-3.817..8.178`, `0` conflict groups at std threshold `0.5`;
  - exact overlap with SLE pairs and SLE triples is `0%`, so expanded IDAC is not solubility leakage;
  - maintained training protocol consumes IDAC as a separate auxiliary stream / train-only aux rows, not as appended SLE solubility rows.
- Added report figures in `reports/figures/build_report_figures.py`:
  - `data_collection_pipeline_schematic.pdf`
  - `idac_collection_pipeline_schematic.pdf`
- Rebuilt figures and reports:
  - `python -m py_compile reports/figures/build_report_figures.py`
  - `python reports/figures/build_report_figures.py` (`39` report figures generated)
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
- Final PDF sizes:
  - `reports/supervisor_report_full.pdf`: `68` pages, `1,129,234` bytes.
  - `reports/supervisor_report_short.pdf`: `11` pages, `272,367` bytes.
- Final log audit found no unresolved citations/references, no duplicate labels, and no overfull boxes; only non-fatal underfull-box warnings remain.

## 2026-04-19 - Supervisor Report Figure Simplification and Starter IDAC Clarification

Status: completed / report-updated.

- Addressed visual critique of overloaded report schemes:
  - `reports/figures/graph_mechanisms_schematic.pdf` no longer uses decorative molecular graph doodles or curved arrows; it is now a three-card comparison of MPNN, GPS, and TIMP mechanisms.
  - `reports/figures/interaction_rescue_schematic.pdf` was rebuilt as a diagnosis-vs-fixes panel with one connector arrow and no text between overlapping blocks.
  - `reports/figures/architecture_schematic.pdf` was rebuilt as two clean lanes: shared representation, TGNN-Solv physics path, and DirectGNN direct path, with minimal straight connectors.
  - Removed the accidental double shadow rendering in the figure helper to keep the visual style lighter.
- Clarified how the starter IDAC corpus was collected in both reports:
  - the `404`-row starter corpus is not from BigSolDB and not synthetic;
  - it is a separate ThermoML bootstrap corpus built from `9` manually selected DOI records listed in `notebooks/data/raw/idac_seed_dois.txt`;
  - for each DOI, official NIST ThermoML JSON was fetched, binary liquid-phase IDAC measurements were extracted, InChI identifiers were standardized to SMILES through RDKit, and DOI/method/phase/standard-state provenance was preserved in `notebooks/data/raw/idac.csv`;
  - the later broad ThermoML crawl uses the same extraction logic but expands DOI/archive coverage.
- Rebuilt figures and reports:
  - `python -m py_compile reports/figures/build_report_figures.py`
  - `python reports/figures/build_report_figures.py` (`39` report figures generated)
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
- Final PDF sizes:
  - `reports/supervisor_report_full.pdf`: `68` pages, `1,129,900` bytes.
  - `reports/supervisor_report_short.pdf`: `11` pages, `272,741` bytes.
- Final log audit found no unresolved citations/references, no duplicate labels, and no overfull boxes; only non-fatal underfull-box warnings remain.

## 2026-04-19 - Supervisor Report Mathematical Appendix Expansion

Status: completed / report-updated.

- Expanded the mathematical appendix in `reports/supervisor_report_full.tex` substantially, keeping the short report unchanged except for rebuild artifacts.
- Added or deepened appendix coverage for:
  - SLE fixed-point formulation, existence/uniqueness conditions, basin argument from ideal-solubility initialization, adaptive damping, implicit differentiation, denominator safeguard, and numerical precision estimates;
  - TIMP physics: dispersive/polar message decomposition, physical edge features, Hansen-channel alignment, orthogonality penalty, and relation to NRTL contact-energy parameters;
  - NRTL model choice relative to Wilson/UNIQUAC/UNIFAC and Gibbs-Duhem thermodynamic consistency;
  - group/descriptor/UNIFAC priors, zero-initialized bounded residuals, stochastic oracle injection / teacher forcing, annealing schedule, and bounded parameter-space correction with a second SLE solve;
  - Van't Hoff local-loss explosion mechanism, three-level stabilization, denominator clamp, per-pair cap, scaled slope/intercept losses, and `sol_fraction` as the main loss-dominance safeguard;
  - pair-aware temperature batching, AdamW/gradient clipping/early stopping, regularizer domination diagnostics, Optuna/TPE/pruning mathematics and the role of tuned configs;
  - linear-probe rationale, uncertainty calibration, MC-dropout / ensemble formulas, OOD detection via Mahalanobis distance plus Morgan Tanimoto, application utility framing, and applicability limits.
- Added bibliography entries and citations for Optuna/TPE/pruning (`akiba2019`, `bergstra2011`, `li2018`) plus cross-references to existing thermodynamics, uncertainty, and graph-learning sources.
- Added new report figures in `reports/figures/build_report_figures.py`:
  - `solver_convergence_schematic.pdf`
  - `vh_stability_safeguards.pdf`
  - `optuna_tpe_schematic.pdf`
- Rebuilt figures and reports:
  - `python -m py_compile reports/figures/build_report_figures.py`
  - `python reports/figures/build_report_figures.py` (`42` report figures generated)
  - `latexmk -xelatex -interaction=nonstopmode supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode supervisor_report_short.tex`
- Final PDF sizes:
  - `reports/supervisor_report_full.pdf`: `79` pages, `1,301,900` bytes.
  - `reports/supervisor_report_short.pdf`: `11` pages, `272,741` bytes.
- Final log audit found no LaTeX errors, no unresolved citations/references, and no overfull boxes; only non-fatal underfull-box warnings remain in long paragraphs/bibliography entries.

## 2026-04-20 - Supervisor Report Coverage Audit and Figure Additions

Status: completed / report-updated.

- Audited `reports/supervisor_report_full.tex` against the old report narrative, seminar/presentation materials, and generated diagnostics to identify missing high-value content rather than adding more future-planning text.
- Expanded the full report with additional concise sections/paragraphs on:
  - corpus temperature and solvent-frequency distributions;
  - source/provenance coverage and why simple source weighting is not yet a validated improvement;
  - practical modelability via nearest-neighbor/Tanimoto diagnostics and solubility cliffs;
  - comparison of activity-coefficient model families, including why NRTL remains the main differentiable SLE layer and why UNIFAC/COSMO-RS are treated differently;
  - atom-contribution/attribution maps as sanity checks for MPNN/TIMP behavior;
  - descriptor augmentation as a controlled hybrid path rather than a replacement for graph/physics modeling;
  - reproducible artifact contracts for runs, benchmark cards, manifests, predictions, configs, and checkpoints.
- Added/connected new report figures in `reports/figures/build_report_figures.py` and `reports/supervisor_report_full.tex`:
  - `corpus_temperature_histogram.pdf`
  - `corpus_solvent_barplot.pdf`
  - `source_uncertainty_coverage.pdf`
  - `knn_modelability_diagnostics.pdf`
  - `source_weighting_ablation.pdf`
  - `attribution_examples.pdf`
  - `weight_group_stats.pdf`
  - `descriptor_probe_bars.pdf`
- Added a COSMO-RS reference entry (`klamt1995`) for the expanded activity-model comparison table.
- Kept `reports/supervisor_report_short.tex` intentionally unchanged in substance to avoid turning the 11-page first-contact version into another full report.
- Rebuilt artifacts:
  - `python -m py_compile reports/figures/build_report_figures.py`
  - `python reports/figures/build_report_figures.py` (`50` report figures generated)
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
- Final PDF sizes:
  - `reports/supervisor_report_full.pdf`: `87` pages, `1,494,418` bytes.
  - `reports/supervisor_report_short.pdf`: `11` pages, `272,742` bytes.
- Final log audit found no LaTeX errors, no unresolved citations/references, and no overfull boxes; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report Architecture Details and Figure Readability Pass

Status: completed / report-updated.

- Addressed report review items about missing architecture/training details in `reports/supervisor_report_full.tex`:
  - added a dedicated readout subsection explaining attention pooling, Set2Set pooling, output dimension `3d`, and TIMP channel-aware readouts;
  - expanded solvent-type MoE description with gating equations, residual scaling, zero-safe initialization, and expert-balance regularization;
  - expanded pair-aware temperature batching explanation in the main training section with the batch-grouping formula and explicit relation to `pair_temp_rank`, `vant_hoff_local`, slope/intercept losses, and Van't Hoff anchors.
- Addressed figure readability/design issues in `reports/figures/build_report_figures.py`:
  - bundled and registered local `reports/fonts/Montserrat.ttf` for generated report figures;
  - darkened text colors and reduced most box text weight from bold/semibold to medium/normal;
  - redesigned `architecture_schematic.pdf` (figure 19) as a cleaner shared-lane + TGNN/Direct lanes diagram with fewer arrows and explicit readout/MoE blocks;
  - redesigned `temperature_protocol_audit.pdf` (figure 29) with larger card spacing and safer label/value layout;
  - redesigned `solver_convergence_schematic.pdf` (figure 41) with shorter step labels, larger blocks, and no overflowing block text;
  - reduced early corpus figure insert sizes and changed figures 2-5 from strict `[H]` placement to `[htbp]` so they no longer occupy one page each unnecessarily.
- Rebuilt artifacts:
  - `python -m py_compile reports/figures/build_report_figures.py`
  - `python reports/figures/build_report_figures.py` (`50` report figures generated)
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
- Final PDF sizes:
  - `reports/supervisor_report_full.pdf`: `86` pages, `1,501,893` bytes.
  - `reports/supervisor_report_short.pdf`: `11` pages, `273,922` bytes.
- Final log audit found no LaTeX errors, no unresolved citations/references, and no overfull boxes; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report High-Contrast Figure Typography Pass

Status: completed / report-updated.

- Responded to readability feedback that generated report figures were too small, thin, gray, and pale after the previous design pass.
- Updated `reports/figures/build_report_figures.py` so generated figure text is high-contrast and survives TeX scaling:
  - kept the bundled Montserrat asset available, but used the system Verdana renderer for generated figures because matplotlib rendered the variable Montserrat file too thin;
  - darkened text, grid, and line colors and forced generated text to a bold high-contrast style;
  - raised global source font floors for figure text, ticks, legends, labels, and bar annotations;
  - thickened rounded-card borders and arrows.
- Reworked wide diagrams whose text became cramped after the font increase:
  - `architecture_schematic.pdf`: wider encoder block, larger lane labels, larger source text, compact solvent-type MoE card, and no extra branch-arrow clutter;
  - `temperature_protocol_audit.pdf`: larger cards, shorter subtitles, larger interpretation block, and no text escaping from cards;
  - `solver_convergence_schematic.pdf`: larger step cards, simplified equations, fewer arrows, and larger safeguard text;
  - `interaction_rescue_schematic.pdf`: simplified fix labels so large text no longer overlaps inside cards.
- Adjusted early corpus figure insert sizes in `reports/supervisor_report_full.tex` so figures 2-5 now share pages more compactly while staying readable:
  - target distribution / points-per-pair / temperature distribution at `0.66\textwidth`;
  - solvent-frequency plot at `0.72\textwidth`.
- Rebuilt artifacts:
  - `python reports/figures/build_report_figures.py` (`50` report figures generated);
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`.
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `86` pages, `1,302,290` bytes;
  - `reports/supervisor_report_short.pdf`: `11` pages, `249,039` bytes.
- Final log audit found no LaTeX errors, no unresolved citations/references, and no overfull boxes; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report Balanced Typography Correction

Status: completed / report-updated.

- Corrected the previous high-contrast figure pass because it overcorrected typography: too many labels were forced to be large and bold, and several block diagrams became visually heavy or cramped.
- Updated `reports/figures/build_report_figures.py`:
  - removed global forced-bold behavior from `_force_readable_text`;
  - lowered the global font-size floor to a safety minimum only;
  - restored normal/medium text for ordinary block content and kept semibold only for headings or key labels;
  - kept high-contrast text color so figures remain readable without making all text visually dominant.
- Replaced `architecture_schematic.pdf` (report figure 19) with a new two-panel comparison:
  - top strip shows the shared molecular representation path;
  - bottom panels separately show the TGNN-Solv physical map and the DirectGNN direct map;
  - optional solvent-type MoE is shown as a compact note on the shared pair vector rather than as another arrow path;
  - removed the previous long horizontal chain that made the figure visually cluttered.
- Visually previewed regenerated key figures/pages, including the architecture figure inside the short/full PDFs and the main protocol/solver/graph-mechanism diagrams.
- Rebuilt artifacts:
  - `python -m py_compile reports/figures/build_report_figures.py`;
  - `python reports/figures/build_report_figures.py` (`50` report figures generated);
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`.
- Final PDF sizes after this correction:
  - `reports/supervisor_report_full.pdf`: `86` pages, `1,720,369` bytes;
  - `reports/supervisor_report_short.pdf`: `11` pages, `299,704` bytes.
- Final log audit found no LaTeX errors, no unresolved citations/references, and no overfull boxes; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report Targeted Figure Layout Cleanup

Status: completed / report-updated.

- Addressed follow-up design feedback on generated report figures where some block text was still too small and several arrows/cards remained visually awkward.
- Updated `reports/figures/build_report_figures.py` with targeted changes rather than another global bold pass:
  - raised only the safety-level minimum figure text size and default card font slightly;
  - kept ordinary block text normal/medium weight to avoid the previous over-bold look;
  - kept Verdana as the generated-figure font because the bundled Montserrat variable font remained too thin in matplotlib PDF output.
- Reworked the specific reported figures:
  - Figure 8 / `idac_collection_pipeline_schematic.pdf`: removed the long crossing route, expanded the three-column card layout, shortened labels, and kept IDAC as a separate activity-only auxiliary stream rather than an appended solubility label.
  - Figure 18 / `interaction_rescue_schematic.pdf`: replaced the previous multi-arrow fan with a clean evidence -> bottleneck -> rescue-signals layout; no arrows now pass through content blocks.
  - Figure 19 / `architecture_schematic.pdf`: kept the two-panel TGNN-Solv vs DirectGNN comparison but increased block readability and moved the TGNN solver/correction/output chain fully inside its card.
- Rebuilt artifacts:
  - `python reports/figures/build_report_figures.py` (`50` report figures generated);
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`.
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `86` pages, `1,718,859` bytes;
  - `reports/supervisor_report_short.pdf`: `11` pages, `299,410` bytes.
- Final log audit found no LaTeX errors, no unresolved citations/references, and no overfull boxes; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report Global Design and Typography Pass

Status: completed / report-updated.

- Performed a broader typography and design pass on the supervisor reports after feedback that several generated figures still looked visually inconsistent, pale, over-bold in places, or too small after TeX scaling.
- Updated `reports/figures/build_report_figures.py`:
  - switched generated report figures to a stable TrueType `Arial` renderer after testing system alternatives; this avoids the noisy TTC subsetting warnings seen with `Helvetica Neue` while staying more compact than Verdana;
  - softened the figure palette and reduced visual heaviness of grids, borders, and arrows;
  - kept high-contrast text but removed the previous global heavy/bold look; headings use medium/semibold selectively, ordinary block text uses normal/medium weight;
  - adjusted global label, tick, legend, bar-label, caption-card, and rounded-box styling so text remains readable without becoming visually aggressive;
  - reduced oversized schematic canvases so TeX no longer downscales text excessively.
- Reworked remaining problematic generated figures:
  - `training_curriculum_schematic.pdf`: bottom explanations are now separate cards, eliminating text collision between Phase 2 and Phase 3 notes;
  - `solver_convergence_schematic.pdf`: the proposed-solution formula is split across lines so arrows do not visually collide with equations;
  - appendix solver / Van't Hoff-stability / Optuna figures are inserted at `0.96\textwidth` in `reports/supervisor_report_full.tex` for better readability.
- Updated TeX styling in `reports/supervisor_report_full.tex` and `reports/supervisor_report_short.tex`:
  - added subdued link coloring via `ReportBlue` instead of default bright blue;
  - added consistent small figure captions with compact spacing;
  - kept table caption styling only in the full report, where tables require it.
- Rebuilt artifacts:
  - `python -m py_compile reports/figures/build_report_figures.py`;
  - `python reports/figures/build_report_figures.py` (`50` report figures generated);
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`.
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `87` pages, `1,973,266` bytes;
  - `reports/supervisor_report_short.pdf`: `12` pages, `335,855` bytes.
- Final log audit found no LaTeX errors, no unresolved citations/references, no overfull boxes, and no caption-package warnings; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report Block Text Fitting Pass

Status: completed / report-updated.

- Addressed follow-up feedback that some generated block diagrams still had text too close to borders, text escaping cards, or line collisions after TeX scaling.
- Updated `reports/figures/build_report_figures.py`:
  - added measured text fitting for the shared `box(...)` helper using the matplotlib renderer;
  - wrapped plain prose lines only when measured text width exceeds the available card interior;
  - locally reduced font size only for cards that still overflow after wrapping;
  - preserved math/TeX lines and avoided global font shrinking or global bold styling;
  - allowed intentionally fitted small text to bypass the later global minimum-size reset.
- Manual cleanup after automated fitting:
  - shortened `graphical_abstract_schematic.pdf` final solver label from `SLE / NRTL` to `SLE/NRTL` and widened that card slightly;
  - shortened `hypothesis_map_schematic.pdf` labels to avoid vertical word-by-word wrapping;
  - renamed the solver figure title/subtitle to avoid awkward `fixed-point` rendering in the graphic itself.
- Rebuilt artifacts:
  - `python -m py_compile reports/figures/build_report_figures.py`;
  - `python reports/figures/build_report_figures.py` (`50` report figures generated);
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`.
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `87` pages, `1,975,425` bytes;
  - `reports/supervisor_report_short.pdf`: `12` pages, `335,937` bytes.
- Final log audit found no LaTeX errors, no unresolved citations/references, no overfull boxes, and no caption-package warnings; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report Russian Terminology Cleanup

Status: completed / report-updated.

- Cleaned remaining anglicisms and ML slang in `reports/supervisor_report_full.tex` and `reports/supervisor_report_short.tex` while preserving proper model names, file/code identifiers, mathematical symbols, figure-internal English labels, and bibliography titles.
- Replaced Russian-English hybrids and colloquial technical terms in prose, including:
  - `loss`, `batching`, `checkpoint`, `proxy`, `inference`, `dropout`, `latent/embedding`, `bridge-компонент`, `correction-блок`, `teacher forcing`, `GC prior`, `readout`, `head`, `seed`, and `validation/test`;
  - normalized them to Russian scientific wording such as `функция потерь`, `мини-пакет`, `сохранённое состояние модели`, `сокращённый запуск`, `применение модели`, `случайное выключение нейронов`, `векторное представление`, `мостовой компонент`, `поправочный блок`, `принудительная подстановка`, `априорная оценка`, `агрегация атомных состояний`, `выходной блок`, `случайная инициализация`, and `валидационная и тестовая части`.
- Fixed a table overfull issue in the temperature-protocol audit by converting the long two-column table to `tabularx` and rewriting row labels in Russian.
- Fixed a short-report overfull line by splitting the long application/uncertainty sentence into two readable sentences.
- Rebuilt artifacts:
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`.
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `87` pages, `1,975,160` bytes;
  - `reports/supervisor_report_short.pdf`: `12` pages, `336,086` bytes.
- Final log audit found no LaTeX errors, no undefined references/citations, no overfull boxes, and no caption-package warnings; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report Figure 18/19/29 Layout Fix

Status: completed / report-updated.

- Addressed follow-up layout feedback for three generated report figures:
  - Figure 18 (`interaction_rescue_schematic.pdf`): widened the canvas/cards, simplified the left diagnostic labels, increased column spacing, and lengthened the arrows so card text no longer sits on borders;
  - Figure 19 (`architecture_schematic.pdf`): rebuilt the TGNN-Solv vs DirectGNN architecture schematic with larger separated panels, longer non-overlapping arrows, and more vertical clearance around shared-backbone labels;
  - Figure 29 (`temperature_protocol_audit.pdf`): expanded the protocol cards, increased inter-card spacing, reduced card text density, and enlarged the interpretation block to prevent line collisions and block overlap.
- Updated `reports/figures/build_report_figures.py` and regenerated report figure PDFs with `python reports/figures/build_report_figures.py` (`50` report figures generated; only non-fatal pandas dtype/version warnings were printed).
- Rebuilt artifacts:
  - `latexmk -g -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`.
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `87` pages, `1,975,011` bytes;
  - `reports/supervisor_report_short.pdf`: `12` pages, `335,930` bytes.
- Final log audit found no LaTeX errors, no undefined references/citations, no overfull boxes, and no caption-package warnings; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report Evidence/Diagnostics Expansion

Status: completed / report-updated.

- Strengthened `reports/supervisor_report_full.tex` with compact evidence-focused additions rather than broad prose expansion:
  - added an evidence-status map separating confirmed facts, diagnostics, hypotheses, and GPU-dependent validation;
  - added a supervision/observability matrix showing which observations constrain hidden TGNN-Solv quantities;
  - added a medium-budget physical-path audit figure showing that the correction path does not materially improve the physics-only solution in that run, while NRTL parameters mostly stay within physical bounds;
  - added a structural-generalization diagnostic figure combining BRICS novelty, weak nearest-scaffold-distance explanation, and embedding-domain-shift evidence;
  - added a full-budget validation contract table with required checks for the next GPU stage.
- Updated `reports/supervisor_report_short.tex` with a concise status table so the short version also separates confirmed results from diagnostics and GPU-dependent claims.
- Updated `reports/figures/build_report_figures.py` with four new generated figures:
  - `evidence_status_matrix.pdf`;
  - `supervision_matrix.pdf`;
  - `physics_bottleneck_audit.pdf`;
  - `structural_generalization_diagnostics.pdf`.
- Rebuilt artifacts:
  - `python -m py_compile reports/figures/build_report_figures.py`;
  - `python reports/figures/build_report_figures.py` (`54` report figures generated; only non-fatal pandas dtype/version warnings were printed);
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`.
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `91` pages, `2,101,843` bytes;
  - `reports/supervisor_report_short.pdf`: `12` pages, `336,625` bytes.
- Final log audit found no LaTeX errors, no undefined references/citations, no overfull boxes, and no caption-package warnings; only non-fatal underfull-box warnings remain.

## 2026-04-20 - Supervisor Report Interpretability Projection and Float Layout Pass

Status: completed / report-updated.

- Addressed follow-up report feedback about Figure 27 and large whitespace around generated figures.
- Updated `reports/figures/build_report_figures.py`:
  - rebuilt `evidence_status_matrix.pdf` with narrower columns, larger inter-column gaps, smaller row cards, and no block overlap;
  - added `chemical_space_projection.pdf`, a dataset-level PCA projection of unique supervised solute structures from Morgan fingerprints;
  - added `embedding_geometry_diagnostics.pdf`, a fresh PCA projection of saved TGNN-Solv 768-dimensional solute representations with split and MolLogP views;
  - retained optional UMAP support in the projection artifact script without adding a hard dependency.
- Added reusable CPU diagnostic script:
  - `scripts/analysis/run_chemical_space_projection.py`
  - output artifacts under `results/chemical_space_projection/`:
    - `chemical_space_projection.csv`
    - `summary.json`
  - current summary: `1,525` valid unique supervised solutes, `1,222` train, `149` val, `154` test; PCA-2 variance `~2.0%`; UMAP package unavailable in the current environment.
- Updated `reports/supervisor_report_full.tex`:
  - added subsection on chemical-space and representation-space geometry;
  - inserted the two new interpretability figures;
  - tightened float spacing and adjusted nearby figure placement/widths to remove a large blank after Figure 27.
- Updated `reports/supervisor_report_short.tex` with the same compact float spacing defaults.
- Rebuilt artifacts:
  - `python -m py_compile reports/figures/build_report_figures.py scripts/analysis/run_chemical_space_projection.py`
  - `python scripts/analysis/run_chemical_space_projection.py --output-dir results/chemical_space_projection --max-train-solutes 2500`
  - `python reports/figures/build_report_figures.py` (`56` report figures generated)
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `92` pages, `2,448,274` bytes.
  - `reports/supervisor_report_short.pdf`: `12` pages, `336,627` bytes.
- Final log audit found no LaTeX errors, no undefined references/citations, no overfull boxes, and no caption-package warnings; only non-fatal underfull-box warnings remain.

## 2026-04-20 - UMAP, Cluster Interpretability, and NRTL Failure-Mode Report Update

Status: completed / report-updated.

- Added `umap-learn` to `pyproject.toml` dev extras so the chemical-space UMAP diagnostics are reproducible in fresh dev installs.
- Installed `umap-learn` in the active environment:
  - `umap-learn 0.5.12`;
  - `pynndescent 0.6.0`;
  - `numba 0.65.0`;
  - `llvmlite 0.47.0`;
  - `scikit-learn` was upgraded to `1.7.2`.
- Extended chemical-space interpretation in `scripts/analysis/run_chemical_space_projection.py`:
  - Morgan-fingerprint UMAP is now used when available;
  - added an 8-cluster chemical grouping with functional-group summaries;
  - joined cluster assignments to model prediction-error artifacts for DirectGNN, TGNN-Solv MPNN, and RF hybrid.
- Current chemical-space artifacts under `results/chemical_space_projection/`:
  - `chemical_space_projection.csv`;
  - `cluster_profiles.csv`;
  - `cluster_model_errors.csv`;
  - `summary.json`.
- Current cluster-level model interpretation:
  - TGNN-Solv is better than DirectGNN in clusters `C5` (`delta MAE = -0.642`), `C2` (`-0.432`), and `C4` (`-0.119`);
  - TGNN-Solv is worse in clusters `C3` (`+0.445`), `C7` (`+0.282`), and `C1` (`+0.097`);
  - this confirms that the physics path is not uniformly worse, but helps and hurts in different chemical regimes.
- Added hidden-representation interpretation script:
  - `scripts/analysis/run_embedding_interpretability.py`.
- Current hidden-representation artifacts under `results/embedding_interpretability/tgnn_tuned_medium/`:
  - `embedding_projection.csv`;
  - `embedding_cluster_profiles.csv`;
  - `summary.json`.
- Important runtime caveat:
  - UMAP on Morgan fingerprints is stable in the current environment;
  - UMAP on saved 768-dimensional TGNN-Solv embedding artifacts caused a low-level crash in the current CPU environment, so `run_embedding_interpretability.py` defaults to a stable PCA projection unless `--use-umap` is explicitly requested.
- Updated `reports/figures/build_report_figures.py`:
  - `chemical_space_projection.pdf` now uses UMAP coordinates when available;
  - `embedding_geometry_diagnostics.pdf` now reads the saved representation-interpretability artifact instead of recomputing from NPZ inside the figure builder;
  - added `cluster_error_interpretability.pdf`;
  - added `nrtl_collapse_mechanism.pdf` comparing the short temperature run with the medium-budget scaffold run.
- Updated `reports/supervisor_report_full.tex`:
  - added a compact explanation of the two NRTL failure regimes;
  - updated the chemical/representation geometry section to UMAP + clustering;
  - added cluster-level model interpretation and report text tying cluster errors to chemical regimes.
- Rebuilt artifacts:
  - `python -m py_compile reports/figures/build_report_figures.py scripts/analysis/run_chemical_space_projection.py scripts/analysis/run_embedding_interpretability.py`;
  - `python reports/figures/build_report_figures.py` (`58` report figures generated; only non-fatal pandas dtype/version warnings were printed);
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error supervisor_report_short.tex`.
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `94` pages, `2,529,993` bytes;
  - `reports/supervisor_report_short.pdf`: `12` pages, `336,624` bytes.
- Final log audit found no LaTeX errors, no undefined references/citations, no overfull boxes, and no caption-package warnings; only non-fatal underfull-box warnings remain.

2026-04-20 - Temperature interpretability bundle integrated into supervisor report

- Added `scripts/analysis/run_temperature_interpretability_bundle.py` to build reproducible temperature-interpretability artifacts under `results/temperature_interpretability_bundle/`:
  - `wide_predictions.csv`;
  - `pair_metrics.csv`;
  - `required_activity_summary.csv`;
  - `slope_level_pairs.csv`;
  - `selected_pairs.csv`;
  - `pair_profiles.csv`;
  - `degeneracy_scan.csv`;
  - `summary.json`.
- The bundle now anchors report examples to readable real pairs:
  - `TGNN beats DirectGNN`: `N-tert-butylacrylamide / formamide`;
  - `TGNN fails on a known pair`: `2,4-dinitro-L-phenylalanine / water`;
  - `large activity correction needed`: `Delphinidin / acetone`;
  - `very low-solubility tail`: `Delphinidin / ethanol`.
- Added new report figures in `reports/figures/build_report_figures.py`:
  - `temperature_prediction_distribution_diagnostics.pdf`;
  - `temperature_pair_profile_panels.pdf`;
  - `temperature_slope_level_problem.pdf`;
  - `degeneracy_visualization.pdf`.
- Updated `reports/supervisor_report_full.tex`:
  - inserted distribution-level temperature diagnostics after the high-temperature baseline comparison;
  - inserted concrete pair-profile panels with text clarifying that TGNN-Solv helps on some known pairs but fails on others;
  - inserted a dedicated ``correct shape, wrong level'' figure in the temperature-slope section;
  - inserted a local compensatory-degeneracy figure in the identifiability section.
- Important execution note:
  - an initial parallel run allowed `build_report_figures.py` to read stale `temperature_interpretability_bundle` CSVs before the bundle refresh finished;
  - rerunning the figure builder after the bundle completed fixed the mismatch.
- Visual QA was done on standalone figure PDFs and on report pages `25`, `45`, `46`, and `49` rendered to PNG:
  - new figures are readable at page scale;
  - no new layout collisions or large vertical gaps were observed on the inspected report pages.
- Rebuilt artifacts after the temperature-interpretability pass:
  - `python -m py_compile scripts/analysis/run_temperature_interpretability_bundle.py reports/figures/build_report_figures.py`;
  - `python scripts/analysis/run_temperature_interpretability_bundle.py --output-dir results/temperature_interpretability_bundle`;
  - `python reports/figures/build_report_figures.py` (`62` figures generated; only non-fatal pandas dtype/version warnings were printed);
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error reports/supervisor_report_full.tex`;
  - `latexmk -xelatex -interaction=nonstopmode -halt-on-error reports/supervisor_report_short.tex`.
- Final PDF sizes after this pass:
  - `reports/supervisor_report_full.pdf`: `96` pages, `2,933,196` bytes;
  - `reports/supervisor_report_short.pdf`: `12` pages, `336,612` bytes.

2026-04-21 - Supervisor report critique-response pass

- Updated `reports/supervisor_report_full.tex` and `reports/supervisor_report_short.tex` in response to the publication-readiness critique:
  - reframed the work as a current-stage research report rather than a completed proof of TGNN-Solv superiority;
  - made the main scaffold table explicitly single-run/no-confidence-interval and added the interpretation that `R2 = 0.478` explains less than half of held-out scaffold variance;
  - labelled SolProp as retrained/native on TGNN-Solv targets, not an external zero-shot reference;
  - clarified that the temperature Van't Hoff result is a same-pair fitted reference/oracle, not a new-system competitor;
  - made the NRTL-collapse conclusion explicit: with nearly constant `tau` and `ln_gamma_2 approx 0`, TGNN-Solv degenerates toward ideal-solubility/crystal-only prediction;
  - added caveats on IDAC transfer to SLE pairs, UNIFAC pseudo-label coverage, missing PICP calibration numbers, missing inference-time benchmark, and missing full-budget component ablations;
  - softened Hansen-bridge and TIMP-Hansen language so they are described as metric/auxiliary constraints, not proof of physically pure channels;
  - replaced misleading "full budget" wording with planned/baseline budget wording and reduced "пока"-style provisional phrasing.
- Added `reports/figures/prediction_slice_lnx2_bin_mae.pdf` via `reports/figures/build_report_figures.py`:
  - plots MAE by true `ln_x2` bins for DirectGNN, TGNN-Solv MPNN, and RF hybrid;
  - uses `results/prediction_error_slices_latest/*/predictions_with_errors.csv`.
- Added report tables summarizing:
  - split-wise current evidence, including RF metrics from `results/metric_diagnosis_bundle/comparison_table.md`;
  - ablation/evidence status for TIMP, Hansen contrastive, IDAC auxiliary stream, UNIFAC pseudo-labels, explicit water hydrogens, entropy-coupled fusion, and solvent-type MoE.
- Fixed/qualified mathematical appendices:
  - Cramer-Rao scalar estimate is now explicitly one-effective-parameter only; one IDAC point gives a rank-1 Fisher matrix for the full NRTL parameter vector;
  - SLE smoothness is stated as a local implicit-function result with numerical safeguards, not a global analytic proof;
  - convergence-gradient amplification is marked as a possible mechanism whose corpus prevalence still requires logging;
  - heat-capacity correction threshold is parameterized by `dCp_fus` and no longer presented as universal;
  - joint SLE+IDAC rank is described as an upper bound that may be lower under collinearity.
- Rebuilt/checked artifacts:
  - `python -m py_compile reports/figures/build_report_figures.py` succeeded;
  - `reports/supervisor_report_full.pdf` rebuilt successfully (`104` pages);
  - `reports/supervisor_report_short.pdf` rebuilt successfully (`12` pages);
  - no undefined-reference or undefined-citation warnings were found in the checked LaTeX logs;
  - no overfull-box warnings were found after enabling tolerant paragraph breaking for the reports; remaining warnings are underfull boxes caused by the local XeLaTeX setup missing Russian hyphenation patterns.

2026-04-21 - Difficult ionic/formulation system audit added

- Added `scripts/analysis/audit_difficult_ionic_systems.py` to classify supervised rows by:
  - formal charge;
  - fragment count / explicit salt status;
  - zwitterion status;
  - coarse solvent dielectric regime from a curated high-coverage lookup table;
  - anthocyanidin-like names;
  - extreme low-solubility and formulation-audit candidates.
- Generated `results/difficult_systems_audit/`:
  - `row_audit.csv`;
  - `class_summary.csv`;
  - `model_error_by_class.csv`;
  - `delphinidin_summary.csv`;
  - `required_gamma_anomalies_top500.csv`;
  - `summary.json`.
- Key audit results on the canonical scaffold test:
  - `6.6%` of rows have formal charge;
  - `3.6%` are explicit salts;
  - `3.5%` are zwitterions;
  - `3.0%` are charged low-dielectric contact-pair candidates;
  - `0.9%` are charged high-dielectric dissociation candidates;
  - `0.45%` (`26` rows) are extreme low-solubility charged/anthocyanidin-like formulation-audit candidates;
  - dielectric coverage is `82.6%` of test rows.
- Error slices from current prediction artifacts:
  - DirectGNN MAE neutral/charged: `1.604` / `2.337`;
  - TGNN-Solv MPNN MAE neutral/charged: `1.701` / `2.309`;
  - explicit salts in low-dielectric solvents are hard for all models (`DirectGNN 3.749`, `TGNN-Solv 3.894`);
  - formulation-audit candidates are catastrophic (`DirectGNN 11.19`, `TGNN-Solv 11.90`).
- Required activity analysis is limited by available crystal data:
  - only `1080` supervised rows have both `T_m` and `dH_fus`, all in train;
  - median `|ln_gamma_req| = 0.47`;
  - `2.9%` of those rows have `|ln_gamma_req| > 4`.
- Delphinidin chloride audit:
  - `40` scaffold-test rows in acetone, ethanol, methanol, and water;
  - no processed `T_m` or `dH_fus`, so `ln_gamma_req` cannot be computed from oracle crystal data;
  - source lookup identifies Kumoro et al. 2010, J. Chem. Eng. Data, DOI `10.1021/je900851k`, with measurements in water/methanol/ethanol/acetone; the acidified-solvent hypothesis is not supported for this specific source.
- Added `difficult_systems_audit_summary.pdf` to `reports/figures/build_report_figures.py` and integrated it into `reports/supervisor_report_full.tex`.
- Updated `reports/supervisor_report_short.tex` with a compact difficult-system audit paragraph.
- Rebuilt reports:
  - `reports/supervisor_report_full.pdf`: `105` pages;
  - `reports/supervisor_report_short.pdf`: `13` pages;
  - checked logs contain no overfull boxes and no undefined references/citations.

2026-04-21 - Delphinidin chloride case study added to difficult-system audit

- Extended `scripts/analysis/audit_difficult_ionic_systems.py` with delphinidin-specific outputs:
  - `results/difficult_systems_audit/delphinidin_model_errors.csv`;
  - `results/difficult_systems_audit/delphinidin_slope_summary.csv`.
- Updated `results/difficult_systems_audit/summary.json` with:
  - `delphinidin_rows_test = 40`;
  - `delphinidin_formulation_audit_rows_test = 20`;
  - `formulation_audit_rows_test = 26`.
- Delphinidin chloride scaffold-test details:
  - solvents are acetone, ethanol, methanol, and water, `10` rows each;
  - acetone/ethanol account for `20` of the `26` extreme formulation-audit candidates;
  - acetone MAE is `17.68` for DirectGNN, `16.72` for RF hybrid, and `18.47` for TGNN-Solv MPNN;
  - ethanol MAE is `9.48` for DirectGNN, `9.53` for RF hybrid, and `10.77` for TGNN-Solv MPNN;
  - methanol and water remain difficult but are less extreme than acetone/ethanol.
- Van't Hoff diagnostics for delphinidin are internally consistent:
  - all four solvent curves are monotone with `R2 > 0.991`;
  - effective solution enthalpies from slopes are approximately `18.9--20.6 kJ/mol`.
- Interpretation update:
  - the source remains Kumoro et al. 2010 (`10.1021/je900851k`) / NIST ThermoML (`https://trc.nist.gov/ThermoML/10.1021/je900851k.html`), and the acidified-solvent hypothesis is not supported for these rows;
  - the rows have no processed `T_m` or `dH_fus`, so `ln_gamma_req` cannot be computed from oracle crystal data;
  - current evidence points to a crystal-parameter/formulation-audit and contact-ion-pair representation issue, not a simple temperature/unit/sign error and not standalone proof that eNRTL is required.
- Added `reports/figures/delphinidin_case_study.pdf` and integrated it into `reports/supervisor_report_full.tex`; the short report now states the same conclusion compactly.
- Rebuilt and checked reports:
  - `reports/supervisor_report_full.pdf`: `106` pages, `2,946,126` bytes;
  - `reports/supervisor_report_short.pdf`: `13` pages, `338,505` bytes;
  - logs contain no overfull-box warnings and no undefined reference/citation warnings.

2026-04-21 - Delphinidin/no-melting architecture hooks implemented

- Added `src/tgnn_solv/ionic_features.py` with curated ionic/contact-pair helpers:
  - coarse solvent dielectric and protic-solvent lookup;
  - formal-charge, explicit-salt, and zwitterion summaries;
  - applicability-domain flags;
  - curated delphinidin chloride no-melting handling as `exclude_from_crystal_branch`.
- Dataset changes in `src/tgnn_solv/data/dataset.py`:
  - optional `ionic_features` target vector;
  - `has_raw_T_m`, `has_valid_T_m`, `has_decomposition_T`, `has_raw_dH_fus`, and `has_valid_dH_fus` masks;
  - decomposition/no-melting rows no longer supervise the standard fusion-property heads.
- Model/training changes:
  - `TGNNSolvConfig` now has `use_ionic_features` and `use_direct_phi_branch` controls;
  - `FusionHead` can emit an effective `Phi(T)=a+b/T` branch;
  - `SLESolver` accepts `Phi_override` for no-melting/missing-`T_m` rows;
  - TGNN-Solv, DirectGNN, trainers, inference, and evaluation loaders now pass ionic features end to end;
  - `configs/paper_config_tuned_temperature_rescue.yaml` enables ionic features and direct-Phi handling.
- Evaluation changes:
  - `scripts/evaluate_complete.py` now reports system-class slices such as `without_valid_T_m`, `decomposition_or_no_melt`, `explicit_salt_low_eps`, `possible_dissociation_high_eps`, `zwitterion`, `charged_any`, and `neutral_standard`;
  - `scripts/run_full_budget_experiment.py` exports valid-crystal masks and direct-Phi diagnostics in TGNN intermediate CSVs.
- Existing Van't Hoff slope/intercept losses were already implemented in `src/tgnn_solv/loss.py`; no duplicate slope-loss was added. The temperature-rescue config continues to use those maintained losses.
- Verification:
  - `PYTHONPATH=src python -m py_compile ...` for modified source/scripts succeeded;
  - `PYTHONPATH=src python -m pytest tests/test_ionic_features.py tests/test_dataset.py -q` passed (`13` tests);
  - `PYTHONPATH=src python -m pytest tests/test_direct_gnn.py tests/test_loss.py -q` passed (`18` tests);
  - `PYTHONPATH=src python -m pytest tests/test_integration.py::TestForwardPass::test_direct_phi_branch_overrides_missing_tm_rows -q` passed;
  - `PYTHONPATH=src python -m pytest tests/test_evaluate_complete.py tests/test_full_budget_experiment.py -q` passed (`4` tests).

2026-04-21 - Temperature-rescue hooks full smoke verification

- Full test suite passed with the project Python environment:
  - command: `PYTHONPATH=src python -m pytest tests/ -q`;
  - result: `235 passed, 12 warnings in 12.47s`;
  - note: bare `pytest` resolves to a Homebrew Python without `numpy`, so use `python -m pytest` from the active Anaconda environment.
- Runtime inference smoke with `configs/paper_config_tuned_temperature_rescue.yaml` succeeded for delphinidin chloride in acetone:
  - `direct_phi_mask = True`;
  - applicability flags include `decomposes_before_melting` and `ion_pair_regime`;
  - `interpret_prediction(...)` reports the effective direct-Phi branch.
- Evaluation smoke on existing checkpoints succeeded:
  - TGNN checkpoint `checkpoints/tgnn_solv_trained.pt` on a 64-row sample wrote `tmp/eval_tgnn_smoke.json` and `tmp/eval_tgnn_smoke_intermediates.csv`;
  - DirectGNN checkpoint `checkpoints/proxy/directgnn_tuned.pt` on the same sample wrote `tmp/eval_direct_smoke.json`;
  - system-class metrics are emitted, including valid/missing crystal-data and ionic/contact-pair slices.
- Short CPU training smoke succeeded on `tmp/temperature_rescue_smoke/`:
  - subset sizes: train `100`, val `34`, test `34` rows, with delphinidin rows included only to exercise no-melting/contact-pair paths;
  - TGNN-Solv 1/1/1 phase smoke wrote `tmp/temperature_rescue_smoke/tgnn_smoke.pt`, `eval.json`, and `intermediates.csv`;
  - DirectGNN 1-epoch smoke wrote `tmp/temperature_rescue_smoke/direct_smoke.pt` and `direct_eval.json`;
  - these are runtime/backprop checks only, not scientific benchmark results.
- TGNN smoke intermediates confirm branch activation:
  - `34` intermediate rows;
  - `16` rows with `direct_phi_mask = True`;
  - delphinidin ethanol rows have `has_valid_T_m = False`, `has_decomposition_T = True`, and `direct_phi_mask = True`.
- Difficult-system audit smoke succeeded:
  - command: `PYTHONPATH=src python scripts/analysis/audit_difficult_ionic_systems.py --processed-dir notebooks/data/processed --out-dir tmp/difficult_systems_audit_smoke`;
  - wrote `summary.json`, `class_summary.csv`, `model_error_by_class.csv`, `delphinidin_summary.csv`, `delphinidin_slope_summary.csv`, `delphinidin_model_errors.csv`, `required_gamma_anomalies_top500.csv`, and `row_audit.csv`.
- Audit-smoke key facts match the maintained interpretation:
  - supervised rows: `108287`; scaffold-test rows: `5826`;
  - charged fraction in test: `6.56%`;
  - explicit salts in low dielectric test solvents: `3.00%`;
  - formulation-audit candidates: `26` rows (`0.45%` test);
  - delphinidin chloride: `40` test rows, `20` formulation-audit rows, solvents acetone/ethanol/methanol/water, no processed `T_m`/`dH_fus`;
  - delphinidin Van't Hoff slopes remain monotone with `R2 > 0.991` and effective solution enthalpies about `18.9--20.6 kJ/mol`.

2026-04-21 - Example-system chemistry casebook added to report

- Added `scripts/analysis/build_example_system_casebook.py` to make example systems chemically interpretable:
  - consolidates selected temperature-profile pairs, slope-level examples, baseline temperature examples, and the delphinidin solvent series;
  - writes `results/example_system_casebook/example_system_casebook.csv` and `.md`;
  - exports RDKit molecule depictions under `results/example_system_casebook/molecules/`.
- Current casebook contains `16` unique example systems, including:
  - `N-tert-butylacrylamide / formamide` where TGNN-Solv wins by restraining an overly optimistic DirectGNN level;
  - `2,4-dinitro-L-phenylalanine / water` where TGNN-Solv overpredicts because the weak/collapsed activity path cannot supply the required positive activity penalty;
  - delphinidin chloride in acetone/ethanol/methanol/water, interpreted as missing crystal-parameter plus ion-pair/specific-solvation cases rather than proof that eNRTL is immediately required;
  - polyol/apolar, acid/amide, acid/alcohol, quinone/aromatic, terpene/aromatic, and same-pair Van't Hoff examples.
- Added report figures in `reports/figures/build_report_figures.py`:
  - `example_system_molecule_gallery.pdf` shows all casebook molecular pairs used as examples;
  - `example_system_interpretation_cards.pdf` links structures, interactions, metrics, and failure interpretation for key cases.
- Integrated both figures into `reports/supervisor_report_full.tex` after the temperature pair-profile figure.
- Verification:
  - `PYTHONPATH=src python scripts/analysis/build_example_system_casebook.py --output-dir results/example_system_casebook` succeeded;
  - `PYTHONPATH=src python -m py_compile scripts/analysis/build_example_system_casebook.py reports/figures/build_report_figures.py` succeeded;
  - `cd reports && latexmk -xelatex -interaction=nonstopmode supervisor_report_full.tex` succeeded and rebuilt `reports/supervisor_report_full.pdf` (`108` pages, about `3.0 MB`);
  - log check found no undefined references/citations and no overfull warnings;
  - `PYTHONPATH=src python -m pytest tests/test_ionic_features.py -q` passed (`3` tests).

2026-04-21 - Example-system report format corrected and readability audit added

- Supersedes the earlier dense example-system gallery/card layout: the user review found the combined card/gallery figures too small and unreadable.
- Removed the dense `example_system_molecule_gallery.pdf` and `example_system_interpretation_cards.pdf` references from `reports/supervisor_report_full.tex` and removed their generators from `reports/figures/build_report_figures.py`.
- Extended `scripts/analysis/build_example_system_casebook.py` so the maintained casebook now also writes one report-ready structure PDF per key system under `reports/figures/` plus `results/example_system_casebook/report_structure_figures.csv`.
- Added a readable report subsection, `Химический разбор примерных температурных систем`, with one paragraph and one separate molecule-structure figure for each representative system instead of a packed overview figure.
- Added `reports/readability_audit.md` with the current readability assessment:
  - full report builds and is technically consistent;
  - current PDF is `110` pages with `77` figures and `22` tables;
  - it should be treated as a full technical archive, not as the final short external narrative;
  - recommended final report target is `15--25` pages with most diagnostics moved to supplement/artifact references.
- Verification:
  - `PYTHONPATH=src python scripts/analysis/build_example_system_casebook.py --output-dir results/example_system_casebook --report-figures-dir reports/figures` succeeded;
  - `PYTHONPATH=src python -m py_compile scripts/analysis/build_example_system_casebook.py reports/figures/build_report_figures.py` succeeded;
  - `cd reports && latexmk -xelatex -interaction=nonstopmode supervisor_report_full.tex` succeeded and rebuilt `reports/supervisor_report_full.pdf` (`110` pages, about `3.0 MB`);
  - log check found no undefined references/citations, no overfull warnings, and no references to the removed dense example-system figures.

2026-04-21 - Superseded readable report with embedded full-PDF appendix

- Historical note: this implementation was replaced later the same day by a native single-document readable report. Do not restore the embedded-PDF design.
- Earlier structure of the readable report:
  - compact main narrative based on the existing short report;
  - four representative chemical examples in the main text, each with a separate structure figure;
  - appendix A with the full ten-system detailed chemical case section;
  - appendix B embedded `reports/supervisor_report_full.pdf` in full via `pdfpages`, preserving the complete technical report as a maximally detailed appendix.
- Updated `reports/readability_audit.md` to point readers to the new readable report and clarify that `supervisor_report_full.pdf` is a technical archive/supplement rather than the preferred first-read narrative.
- Earlier verification for the now-superseded artifact:
  - `cd reports && latexmk -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - `reports/supervisor_report_readable.pdf` has `129` pages and size about `3.6 MB`;
  - log check found no undefined references/citations, no overfull warnings, and no fatal LaTeX errors;
  - `PYTHONPATH=src python -m py_compile scripts/analysis/build_example_system_casebook.py reports/figures/build_report_figures.py` succeeded.

2026-04-21 - Readable report rebuilt as one native LaTeX document

- Supersedes the earlier `supervisor_report_readable.tex` implementation that appended `supervisor_report_full.pdf` via `pdfpages` / `\includepdf`.
- Reworked `reports/supervisor_report_readable.tex` into a single coherent native LaTeX document:
  - compact main narrative for first reading;
  - four representative chemical examples in the main text, each with a separate structure figure;
  - detailed ten-system chemistry case appendix as native LaTeX;
  - full mathematical/technical appendices imported natively from the full report;
  - one table of contents and one bibliography.
- `reports/supervisor_report_readable.tex` no longer contains `pdfpages`, `\includepdf`, or an embedded `supervisor_report_full.pdf` appendix.
- Updated `reports/readability_audit.md` to describe the new readable report state and remove the stale embedded-PDF wording.
- Verification:
  - `cd reports && latexmk -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - `reports/supervisor_report_readable.pdf` has `53` pages and size about `1.0 MB`;
  - log check found no undefined references/citations and no fatal LaTeX errors;
  - `PYTHONPATH=src python -m py_compile scripts/analysis/build_example_system_casebook.py reports/figures/build_report_figures.py` succeeded.

2026-04-21 - Readable report expanded with coherent experimental appendix and language cleanup

- Reworked `reports/supervisor_report_readable.tex` again after review that the previous 53-page native version lost too much information from the full report's main body.
- Added a new native appendix, `Расширенный экспериментальный и методический контекст`, rather than copying the old main text wholesale.
- The new appendix restores the lost experimental narrative in connected form:
  - corpus composition, source audit, data preparation, IDAC/UNIFAC coverage;
  - evaluation regimes and why the scaffold split is the hard headline protocol;
  - method comparison context and external baseline status;
  - architecture/training context that was too compressed in the short narrative;
  - scaffold-test error structure, charged-system audit, delphinidin case study;
  - temperature protocol audit, distribution compression, slope-vs-level issue, NRTL collapse;
  - structural extrapolation, chemistry slices, BRICS/embedding diagnostics;
  - working hypotheses, negative results, ablation status, next validation contract;
  - interpretation, uncertainty, and applicability-domain context.
- Cleaned obvious English/slang wording in `reports/supervisor_report_readable.tex` and `reports/readability_audit.md`:
  - replaced terms such as `scaffold-test`, `train/test`, `representative`, `standalone`, and informal Russian phrases like `ломается`, `попадает лучше`, `недодаёт`, `провал` where they were not appropriate for report prose;
  - kept established model names, chemical names, acronyms, filenames, and bibliographic titles unchanged.
- Updated `reports/readability_audit.md` for the new state: `supervisor_report_readable.pdf` is now `83` pages, about `2.7 MB`, with a short main narrative plus detailed experimental and technical appendices.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - `reports/supervisor_report_readable.pdf` has `83` pages and size about `2.7 MB`;
  - log check found no undefined references/citations, no overfull warnings, and no fatal LaTeX errors;
  - label check found `107` labels and no duplicate labels;
  - figure check found `69` includegraphics entries and no missing figure files;
  - `PYTHONPATH=src python -m py_compile scripts/analysis/build_example_system_casebook.py reports/figures/build_report_figures.py` succeeded.

## 2026-04-21 - Standalone supervisor report cleanup after editorial review

- Re-edited `reports/supervisor_report_readable.tex` so the report reads as a standalone first-facing document, not as a derivative of another internal version.
- Removed report-text references to previous/full/readable versions, mechanical merging, transferred/lost material, and other editorial process language.
- Rewrote the title, abstract, appendix transition, extended experimental-context appendix opening, and several section headings:
  - `Architecture and training` is now a normal method section;
  - temperature appendix is now framed around experiments and curve level;
  - ablation section is framed as checked vs unchecked components;
  - validation section is framed as required checks.
- Rewrote `reports/readability_audit.md` to describe the current standalone report rather than comparing internal report versions.
- Rebuilt `reports/supervisor_report_readable.pdf` with XeLaTeX:
  - `83` pages;
  - `69` figures, `0` missing;
  - `107` LaTeX labels, `0` duplicates;
  - no critical LaTeX errors, undefined references, or undefined citations in the final log.

## 2026-04-22 - Supervisor report revised after scientific/readability critique

- Reworked `reports/supervisor_report_readable.tex` after a line-by-line scientific critique focused on readability, statistical caution, and overclaiming.
- Structural changes:
  - replaced the long front `Краткое содержание` with a short `Резюме для руководителя`;
  - moved the glossary from the beginning to appendix `Обозначения и термины`;
  - changed `Итог` from an unnumbered section to a numbered section;
  - removed duplicated chemical-structure figures from the main narrative and kept detailed system-by-system structures in the appendix.
- Scientific wording changes:
  - all headline model comparisons are explicitly marked as one-run results without confidence intervals;
  - every mention of Van't Hoff `MAE = 0.368` is tied to the known-pair regime, not new-system transfer;
  - SolProp native retraining is described as another architecture under the same target contract, not independent external validation;
  - FastSolv notes now specify the `ln_x2 -> logS` finite-target filtering issue;
  - NRTL discussion now states that low-solubility SLE mainly constrains an effective `ln_gamma_inf` and temperature dependence, not unique NRTL parameters;
  - delphinidin chloride discussion now states that missing `T_m` / `dH_fus` means the solver uses crystal-branch predictions rather than experimental crystal values.
- Added explicit next diagnostic requirement: log NRTL-head gradient norms and implicit-derivative denominator statistics in full-budget runs.
- Updated `reports/readability_audit.md` for the new report state.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - a second `latexmk -xelatex` pass reported all targets up to date;
  - `reports/supervisor_report_readable.pdf` has `84` pages and size about `2.7 MB`;
  - log check found no fatal LaTeX errors, undefined references, undefined citations, or overfull warnings;
  - label check found `108` labels and no duplicates;
  - figure check found `63` includegraphics entries and no missing figure files.

## 2026-04-22 - Supervisor report appendix critique incorporated

- Revised the second half of `reports/supervisor_report_readable.tex` after a detailed critique of the appendices.
- Main appendix changes:
  - added an explicit status note separating empirical diagnostics from theoretical estimates and planned checks;
  - clarified that Van't Hoff slope anchors must be precomputed from training/anchor rows and are not evidence of transfer to new pairs;
  - softened UNIFAC-prior, gradient-conflict, identifiability, convergence, smoothness, and Cramer-Rao sections from overstrong claims to conditional/local estimates;
  - changed the multi-seed recommendation from `3` runs as practical minimum to `5-7` runs for the observed `0.089` MAE gap;
  - added Optuna validation-bias caveat and noted the limited proxy-search budget;
  - documented artifact storage formats for CSV/YAML/PT/JSON/prediction outputs;
  - added a soft applicability-domain penalty alternative to the hard OOD indicator;
  - clarified that expanded IDAC data has zero exact SLE-pair overlap and supports transferable activity representation rather than direct test-pair parameter identification.
- Bibliography cleanup:
  - removed unused `bradley2014` and `vermeire2021` entries;
  - clarified BigSolDB 2.1 as the Zenodo data snapshot used in this work;
  - clarified the IDAC Zenodo entry as a project deposit;
  - cited the delphinidin solubility source in the case discussion.
- Updated `reports/readability_audit.md` for the new 84-page state.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - `cd reports && latexmk -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - `reports/supervisor_report_readable.pdf` has `84` pages, `63` figures, `108` LaTeX labels, and size about `2.7 MB`;
  - log check found no fatal LaTeX errors, undefined references, undefined citations, or overfull warnings;
  - citation-key check found no missing or unused bibliography entries (`46` cited keys and `46` bibliography entries).

## 2026-04-22 - Supervisor report seminar-gradient diagnostic incorporated

- Audited seminar presentation materials and talk notes for report-relevant content that was missing from `reports/supervisor_report_readable.tex`.
- Added the cross-attention gradient-starvation diagnosis to the report:
  - pair cross-attention gradient in TGNN-Solv diagnostic run: about `7e-4` versus `2.3e-2` in DirectGNN, roughly `33x` weaker;
  - encoder gradients were present, but mainly through the crystal branch rather than the solute-solvent interaction path;
  - the train-time auxiliary pair head restored the pair-attention gradient scale in a 50-step check (`0.0377` versus `0.0381` in DirectGNN), but this is documented as a gradient-flow check, not an MAE result.
- Updated the implemented-component status table to include the auxiliary pair-signal branch as partially verified.
- Removed duplicated `gradient_flow.pdf` / `gradient_flow_fix.pdf` figure blocks and inserted a `\FloatBarrier` after the gradient-flow subsection so those figures do not drift into the next subsection.
- Added/kept layout protections in the readable report:
  - `\usepackage[section]{placeins}`;
  - `\raggedbottom`;
  - local `\enlargethispage{2\baselineskip}` before the appendix transition to remove a nearly blank page caused by one orphan line before `\clearpage`.
- Updated `reports/readability_audit.md` for the new report state.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - `reports/supervisor_report_readable.pdf` has `86` pages, `63` includegraphics entries, `109` LaTeX labels, and size about `2.7 MB`;
  - log check found no fatal LaTeX errors, undefined references, undefined citations, overfull warnings, float-placement warnings, or vbox overfull/underfull warnings matching the audit pattern;
  - citation-key check found no missing or unused bibliography entries (`46` cited keys and `46` bibliography entries);
  - label check found no duplicate labels;
  - PDF text-density check found no nearly blank content pages beyond the title page and the trailing form-feed separator.

## 2026-04-22 - CPU-only offline prediction diagnostics added to readable report

- Added `scripts/analysis/run_offline_prediction_diagnostics.py`, a CPU-only diagnostic script that consumes existing prediction/intermediate CSV artifacts and does not load checkpoints or train models.
- Default inputs:
  - `results/tail_diagnostics_fast_v2/directgnn_scaffold_predictions.csv`;
  - `results/tail_diagnostics_fast_v2/tgnn_mpnn_scaffold_predictions.csv`;
  - `results/tail_diagnostics_fast_v2/rf_hybrid_scaffold_predictions.csv`;
  - `results/physics_bottleneck_diagnostics/tgnn_mpnn_proxy_intermediates/intermediates.csv` when present.
- Generated `results/offline_prediction_diagnostics/` with summary/model metrics, `ln_x2`-bin metrics, pair-wise Van't Hoff slope diagnostics, worst rows/pairs, lightweight RDKit residual correlations, and TGNN intermediate summaries.
- Key diagnostic findings from the saved scaffold predictions:
  - all three maintained models compress the prediction range: `std(pred) / std(true)` is `0.700` for DirectGNN, `0.672` for RF hybrid, and `0.692` for TGNN-Solv;
  - the left tail `ln_x2 < -15` remains badly underfit: MAE is `7.78` for DirectGNN, `8.14` for RF hybrid, and `8.22` for TGNN-Solv on `60` rows;
  - pair-wise temperature slopes are weakly recovered: slope correlation is `0.129` for DirectGNN, `0.223` for RF hybrid, and `-0.015` for TGNN-Solv across `763` repeated-temperature pairs;
  - strongest simple RDKit residual correlations are modest and dominated by size proxies such as molecular weight/heavy atoms.
- Incorporated the offline diagnostic conclusion into `reports/supervisor_report_readable.tex`: future runs must be judged not only by MAE, but also by prediction dispersion, tail-bin errors, and pair-wise temperature-slope recovery.
- Updated `reports/readability_audit.md` for the new report state.
- Verification:
  - `python -m py_compile scripts/analysis/run_offline_prediction_diagnostics.py` succeeded;
  - `python scripts/analysis/run_offline_prediction_diagnostics.py --out-dir results/offline_prediction_diagnostics` completed successfully;
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - `reports/supervisor_report_readable.pdf` has `87` pages, `63` includegraphics entries, and size about `2.8 MB`;
  - log check found no fatal LaTeX errors, undefined references, undefined citations, overfull warnings, float-placement warnings, or vbox overfull/underfull warnings matching the audit pattern;
  - citation-key check found no missing or unused bibliography entries (`46` cited keys and `46` bibliography entries);
  - label check found no duplicate labels (`109` labels);
  - all `63` figure files resolve through `reports/figures/` / explicit report-relative paths;
  - PDF text-density check found no nearly blank content pages.

## 2026-04-22 - Offline prediction diagnostics extended with source, crystal, and UNIFAC checks

- Extended `scripts/analysis/run_offline_prediction_diagnostics.py` beyond the initial prediction-compression diagnostics.
- New outputs in `results/offline_prediction_diagnostics/`:
  - `source_error_summary.csv`;
  - `crystal_label_metrics.csv`;
  - `crystal_parameter_diagnostics.csv`;
  - `unifac_coverage_summary.csv`.
- Findings:
  - current scaffold prediction artifacts expose only one collapsed source label, `BigSolDBv2.1`; DOI-level source-error audit requires preserving row-level DOI/source metadata in future prediction CSVs;
  - scaffold predictions contain `1,357 / 5,826` rows with `T_m` labels and no rows with `dH_fus` labels;
  - rows without crystal labels have higher MAE than rows with `T_m` labels: TGNN-Solv `1.812` vs `1.510`, DirectGNN `1.714` vs `1.447`, RF hybrid `1.759` vs `1.558`;
  - TGNN proxy intermediate diagnostics on rows with known `T_m` give `T_m` MAE about `47.5 K` and bias about `-19.6 K`; no `dH_fus` truth exists in that artifact;
  - maintained UNIFAC-prior coverage is low on the main scaffold test: `8.6%` row coverage and `10.9%` unique-pair coverage.
- Added these conclusions to `reports/supervisor_report_readable.tex` and `reports/readability_audit.md`.
- Verification:
  - `python -m py_compile scripts/analysis/run_offline_prediction_diagnostics.py` succeeded;
  - `python scripts/analysis/run_offline_prediction_diagnostics.py --out-dir results/offline_prediction_diagnostics` completed successfully and produced the new CSV outputs.

## 2026-04-22 - CPU/MPS checklist for no-GPU work completed

- Added `results/offline_prediction_diagnostics/cpu_work_checklist.md` to explicitly map the no-GPU work plan to completed artifacts.
- Completed all diagnostics that can be run from already saved prediction/intermediate artifacts without training:
  - prediction compression;
  - `ln_x2` bin metrics;
  - repeated-temperature pair slope diagnostics;
  - pair-level and row-level worst-case summaries;
  - TGNN intermediate summaries;
  - RDKit residual correlations;
  - available source-field summary;
  - crystal-label availability and predicted crystal-parameter diagnostics;
  - existing UNIFAC coverage summary.
- Explicitly marked non-completed items that require new external data or training rather than offline diagnostics:
  - DOI-level error audit is blocked by collapsed `source=BigSolDBv2.1` in current prediction CSVs;
  - new LogP/IDAC/crystal data collection requires external/manual data work;
  - Van't Hoff reparameterization, alternative losses, and 500--3000 row MPS training checks require separate training protocols.
- Rebuilt `reports/supervisor_report_readable.pdf` after inserting source/crystal/UNIFAC diagnostic conclusions.
- Verification after rebuild:
  - `reports/supervisor_report_readable.pdf` has `87` pages and size about `2.8 MB`;
  - no fatal LaTeX errors, undefined references, undefined citations, overfull warnings, float warnings, or vbox warnings matching the audit pattern;
  - `63` figure includes, `0` missing figures;
  - `109` labels, `0` duplicate labels;
  - `46` cited bibliography keys and `46` bibitems, with no missing or unused entries;
  - PDF text-density check found `0` nearly blank content pages.

## 2026-04-22 - MPS rescue training, alternative losses, gradient diagnostics, and external crystal substitution

- Implemented configurable solubility losses in `src/tgnn_solv/config.py`, `src/tgnn_solv/loss.py`, and `src/tgnn_solv/baselines/direct_gnn.py`:
  - `huber`, `mae`, `weighted_huber`, `weighted_mae`;
  - inverse-frequency `ln_x2` bin weighting;
  - optional prediction-variance preservation penalty.
- Verified the existing direct-`Phi(T)` branch and enabled it in the diagnostic rescue config rather than introducing a separate incompatible parameterization.
- Added diagnostic configs:
  - `configs/small_debug_direct_huber.yaml`;
  - `configs/small_debug_direct_weighted.yaml`;
  - `configs/small_debug_vh_weighted.yaml`.
- Built the balanced MPS diagnostic split under `results/mps_small_rescue/splits/`.
- Ran three small MPS training checks on the diagnostic split:
  - DirectGNN Huber: checkpoint `checkpoints/mps_small_rescue/direct_huber.pt`, test MAE `3.134`, R2 `0.174`, bias `-1.008`;
  - DirectGNN weighted MAE: checkpoint `checkpoints/mps_small_rescue/direct_weighted.pt`, test MAE `3.053`, R2 `0.207`, bias `0.011`;
  - TGNN-Solv with direct Phi, Van't Hoff slope/intercept losses, ionic features, and weighted loss: checkpoint `checkpoints/mps_small_rescue/tgnn_vh_weighted.pt`, test MAE `3.416`, R2 `0.111`, bias `-1.628`.
- Added `scripts/analysis/export_checkpoint_predictions.py` and exported row-level prediction CSVs for all three checkpoints under `results/mps_small_rescue/`.
- Ran full offline diagnostics with RDKit correlations under `results/mps_small_rescue/offline_diagnostics_rdkit/`:
  - all three diagnostic models still compress prediction range, with `std(pred)/std(true)` about `0.73--0.75`;
  - weighted DirectGNN improves average MAE and removes global bias, but worsens some low-solubility bins;
  - TGNN direct-Phi/VH configuration improves the extreme left-tail bin relative to both DirectGNN variants but remains worse on average in this short diagnostic run;
  - repeated-temperature slope recovery remains weak: TGNN slope MAE about `1471 K`, Direct weighted about `1947 K`, true slope std about `2070 K`.
- Updated `scripts/analysis/diagnose_gradient_flow.py` for current ionic-feature contracts and ran a 20-step / 500-row gradient diagnostic under `results/mps_small_rescue/gradient_flow/run_20steps/`:
  - TGNN interaction gradient is only `0.041x` the DirectGNN interaction gradient in this configuration;
  - TGNN NRTL head receives nonzero gradient (`mean_norm ~= 0.073`), so the failure mode is not complete NRTL starvation, but the cross-attention/interaction block is strongly under-driven relative to DirectGNN.
- Added `scripts/analysis/run_external_crystal_substitution.py` and `results/external_crystal_substitution/fusion_overrides.csv` with external fusion overrides for borneol, isoborneol, xylitol, glutaric acid, vitamin K3/menadione, benzoic acid, phthalic acid, and salicylic acid.
- Ran external crystal substitution on the temperature-extrapolation TGNN proxy artifact:
  - artifact: `results/external_crystal_substitution/temperature_extrapolation_proxy/`;
  - matched rows: `128`;
  - original TGNN proxy MAE: `2.786`;
  - external-crystal keep-gamma MAE: `1.155`;
  - large improvements for glutaric acid, borneol, isoborneol, benzoic acid, and vitamin K3/menadione;
  - xylitol and salicylic acid worsen under ideal/external crystal substitution, indicating unresolved activity or data/phase-form effects.
- Ran external substitution against the scaffold TGNN MPNN proxy artifact, but the current override set has `0` matched rows there; broader external crystal matching is still required for scaffold-level conclusions.
- Verification:
  - `python -m py_compile` succeeded for the modified loss/config/model/diagnostic scripts;
  - `pytest tests/test_loss.py -q` passed with `13 passed`.

## 2026-04-22 - Readable report updated with MPS rescue and external crystal substitution

- Updated `reports/supervisor_report_readable.tex` with the new MPS diagnostic training results, alternative-loss interpretation, direct-`Phi` diagnostic status, gradient-flow findings, and external crystal substitution table.
- Added bibliography entries for NIST Chemistry WebBook and Cheméo because the external fusion overrides now appear in the report narrative.
- Updated `reports/readability_audit.md` with the additional editorial and technical check.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - resulting PDF has `89` pages, `63` figure includes, and size about `2.76 MB`;
  - log grep found no fatal LaTeX errors, undefined citations/references, overfull warnings, or float-placement errors.

## 2026-04-22 - Report readability audit, rasterized scatter figures, and UMAP cluster interpretation

- Re-audited `reports/supervisor_report_readable.tex` as the standalone current report rather than as a merged revision history artifact.
- Cleaned remaining report prose around CPU/MPS diagnostics and Optuna search:
  - replaced `bias` with Russian `смещение` in visible table/prose;
  - replaced `proxy-поиск`, `scaffold-протокол`, `GPU-запуск`, and `Huber-потеря` with Russian equivalents where they were not file names or method names.
- Added `scripts/analysis/interpret_umap_clusters.py` and generated:
  - `results/chemical_space_projection/cluster_class_interpretation.csv`;
  - `results/chemical_space_projection/cluster_class_interpretation.md`.
- Added a report table explicitly interpreting the eight UMAP/Morgan clusters as coarse chemical classes:
  - aromatic sulfones/amines;
  - N-containing heteroaromatics and aromatic carbonyls;
  - hydrophobic long-alkyl aromatic amines;
  - hydroxy-carbonyl acids/alcohols/flexible aliphatic fragments;
  - nitroaromatic amines;
  - small test-heavy hydrophobic long-chain aromatic amines;
  - aromatic carbonyl/phenol/ether compounds;
  - large flexible hydroxy/ether long-chain molecules.
- Rasterized scatter-heavy figures at 300 dpi and switched report includes to the raster versions while retaining original PDFs:
  - `temperature_slope_recovery_diagnostics_raster.png`;
  - `prediction_slice_paired_deltas_raster.png`;
  - `knn_modelability_diagnostics_raster.png`;
  - `temperature_prediction_distribution_diagnostics_raster.png`;
  - `structural_generalization_diagnostics_raster.png`;
  - `chemical_space_projection_raster.png`;
  - `cluster_error_interpretability_raster.png`;
  - `embedding_geometry_diagnostics_raster.png`.
- Changed all `figure` and `table` environments in `supervisor_report_readable.tex` to `[H]` placement so figures/tables stay near first mention rather than floating far through the document.
- Rebuilt `reports/supervisor_report_readable.pdf`:
  - `90` pages;
  - `63` `includegraphics` entries, `0` missing;
  - all `63` figures and `12` tables use `[H]`;
  - final PDF size about `5.1 MB`.
- Verification:
  - `cd reports && latexmk -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - log grep found no fatal LaTeX errors, undefined citations/references, overfull warnings, float-placement warnings, or vbox overfull/underfull warnings matching the audit pattern;
  - PDF text-density check found no blank content pages beyond title/trailing extraction artifact and one intentionally figure-dominated page;
  - `python -m py_compile` succeeded for the new UMAP interpretation script and the relevant diagnostic scripts.
- Additional verification after the report rebuild:
  - `pytest tests/test_loss.py -q` passed with `13 passed`.

## 2026-04-22 - Readable report narrative rewrite

- Reworked `reports/supervisor_report_readable.tex` as a coherent standalone narrative rather than a chronological accumulation of fixes.
- Main text now follows a linear order:
  - task definition;
  - data and evaluation protocol;
  - thermodynamic model;
  - models and training;
  - main results;
  - diagnosed reasons TGNN-Solv currently loses;
  - chemical examples;
  - completed pre-full-budget checks;
  - final conclusion.
- Removed low-level implementation and hardware details from the main text:
  - small diagnostic training table moved to the appendix subsection `Предварительные проверки без полноразмерного обучения`;
  - water explicit-hydrogen figure moved from the main data section to the appendix section on water graph topology;
  - main text no longer mentions the specific local machine/accelerator used for small checks.
- Strengthened definition order in the main narrative:
  - `ln x2`, SLE, `Phi(T)`, `gamma2`, NRTL, IDAC, scaffold split, and known-pair Van't Hoff mode are introduced before being used for interpretation.
- Updated `reports/readability_audit.md` with the narrative rewrite status and current technical counts.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `86` pages, `63` figures, `13` tables, `112` labels, and size about `5.0 MB`;
  - all figures/tables use `[H]`, no missing figures, no duplicate labels;
  - log grep found no fatal LaTeX errors, undefined citations/references, overfull warnings, float-placement warnings, or vbox overfull/underfull warnings matching the audit pattern;
  - PDF text-density check found no blank content pages beyond title/trailing extraction artifact and one intentionally figure-dominated page.

## 2026-04-23 - Readable report prose pass after full critique

- Edited `reports/supervisor_report_readable.tex` after a full readability critique:
  - shortened overloaded sentences in the main text and appendices;
  - reduced defensive phrasing (`поэтому`, `не является`, `Это не`, `не доказывает`);
  - clarified the temperature-check table where the direction metric was not saved for small-budget neural runs;
  - added explicit numeric usefulness criteria to the full-budget validation plan;
  - shortened the glossary entry for oracle substitution;
  - added Russian common names in chemical examples while preserving dataset/figure labels.
- Updated `reports/readability_audit.md` with the prose-pass checklist and current technical counts.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `86` pages and size about `5.0 MB`;
  - `63` figures, `13` tables, `63` `includegraphics`, `112` labels;
  - all figures/tables use `[H]`, no missing figures, no duplicate labels;
  - log grep found no fatal LaTeX errors, undefined citations/references, overfull warnings, or float-placement errors;
  - PDF text-density check found no blank content pages beyond title, one intentionally figure-dominated page, and the trailing `pdftotext` artifact.

## 2026-04-23 - Additional report style, hypothesis-status, and layout pass

- Applied an additional editorial pass to `reports/supervisor_report_readable.tex` after targeted style feedback:
  - removed remaining colloquial phrases such as `списать как шум`, `из воздуха`, and `перестал быть голодным`;
  - kept `градиентное голодание` only as the technical term for gradient starvation;
  - reduced remaining overuse of `конкретно` / `принципиально` where it was stylistic rather than necessary.
- Added explicit definitions of `поддерживаемый запуск` and `диагностический прогон` in both the main text and glossary.
- Added a short computational-context statement in the main data/protocol section: current maintained and diagnostic runs were local Apple M1 Pro runs without a dedicated CUDA GPU, explaining the single maintained run and small diagnostic budgets.
- Added a main-text hypothesis status table covering:
  - crystal contribution as an error source;
  - weak pair discrimination / NRTL branch degeneracy;
  - Van't Hoff temperature structure;
  - auxiliary interaction-gradient branch;
  - current lack of evidence that eNRTL is the next necessary step.
- Split the appendices visually with explicit unnumbered headings:
  - `Вычислительные результаты и диагностика`;
  - `Теоретическое обоснование архитектурных решений`.
- Combined the temperature protocol audit and prediction-distribution panels into one compound figure to remove a low-density figure-only page.
- Updated `reports/readability_audit.md` with this pass and verification results.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `86` pages, `62` figure environments, `14` table environments, `63` `includegraphics`, and size about `5.0 MB`;
  - all figures/tables use `[H]`, no missing figures, no duplicate labels;
  - log grep found no fatal LaTeX errors, undefined citations/references, overfull warnings, float-placement errors, or vbox overflow warnings;
  - PDF text-density check found only the title page below the low-text threshold, with no blank content pages.

## 2026-04-23 - Report narrative audit follow-up

- Applied another narrative and structure pass to `reports/supervisor_report_readable.tex` based on external critique.
- Changed the executive summary to lead with the main result:
  - TGNN-Solv `MAE=1.741`, DirectGNN `MAE=1.652`, RF hybrid `MAE=1.722` on new scaffolds;
  - the summary now frames the work as a diagnosed negative result rather than introducing the setup first.
- Moved key crystal-sensitivity estimates from the appendix into the main diagnosis section:
  - `30 K` error in `T_m` gives about `0.53` in `ln x2`;
  - `5 kJ/mol` error in `dH_fus` gives about `0.68` in `ln x2`.
- Rewrote the main failure-mechanism section to reduce monotonic `first/second/third diagnosis` phrasing and directly interpret the NRTL branch as failing to discriminate pairs.
- Added explicit text that random-row `MAE=0.166` is a near-interpolation protocol with repeated chemistry, not performance on new systems.
- Added a main-text definition of contact ion pair in the chemical examples section.
- Added a main-text table with the minimal next validation package:
  - multiple random seeds;
  - full temperature extrapolation;
  - crystal-parameter substitution;
  - NRTL and pair-gradient logging.
- Added a short note explaining that figure axes/internal labels remain in English because figures are direct experiment artifacts and Russian captions translate their meaning.
- Updated `reports/readability_audit.md` with the follow-up pass and verification results.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `86` pages, `62` figure environments, `15` table environments, `63` `includegraphics`, and size about `5.0 MB`;
  - no missing figures, no duplicate labels, all figures/tables use `[H]`;
  - log grep found no fatal LaTeX errors, undefined citations/references, overfull warnings, float-placement errors, or vbox overflow warnings;
  - PDF text-density check found only the title page below the low-text threshold.

## 2026-04-23 - Report appendix structure and reader-map pass

- Applied a further critique-driven structure pass to `reports/supervisor_report_readable.tex`.
- Added a post-summary `Карта отчёта` page explaining how to read the main report and appendix groups.
- Moved short explanations of evaluation regimes, controlled TGNN-vs-Direct comparison, and charged-system handling into the main text so Appendix C is no longer required to understand the headline tables.
- Split appendices into three explicit unnumbered groups:
  - `Вычислительные результаты` for A--C;
  - `Математическое обоснование` for D--M;
  - `Планируемые доработки` for N--AI.
- Reduced defensive repetition by keeping the formal single-run/no-CI caveat in the main results section and shortening duplicate wording in the statistical appendix.
- Replaced the glossary term `Оракульная подстановка` with `Контрольная подстановка`, keeping `оракульный расчёт` only as an explanatory synonym.
- Added `Что это говорит о модели` interpretation sentences to the main chemical-example table and detailed chemical examples.
- Strengthened the final conclusion: a diagnostic physical model with localized failure modes is framed as a substantive result even if it remains weaker than DirectGNN as a mean-error predictor.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `90` pages, `62` figure environments, `15` table environments, `63` `includegraphics`, and size about `5.0 MB`;
  - no missing figures or duplicate labels;
  - log grep found no fatal LaTeX errors, undefined citations/references, overfull warnings, float-placement errors, or vbox overflow warnings;
  - PDF text-density check found only the title page below the low-text threshold.

## 2026-04-23 - Report internal-path cleanup and float-layout pass

- Edited `reports/supervisor_report_readable.tex` to remove documentation-like references to concrete internal files, folders, config names, and result paths from the report prose.
- Rewrote the UMAP-cluster paragraph to keep chemical interpretation and remove the internal table path.
- Rewrote the Optuna and reproducibility sections without concrete config names, result directories, file extensions, or storage paths.
- Renamed the appendix section from `Контракт воспроизводимых артефактов` to `Воспроизводимость экспериментов` and made it describe reproducibility content rather than repository layout.
- Removed explicit file names from the IDAC Zenodo bibliography item.
- Changed figure/table placement strategy to reduce graph-induced gaps:
  - ordinary figures now use `[!htbp]`;
  - molecule structure figures in detailed chemical examples remain `[H]` to stay with the corresponding system text;
  - tables now use `[!htbp]`;
  - added `flafter` so floats cannot appear before their source location;
  - kept `placeins` section barriers so floats do not drift beyond sections.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `88` pages, down from `90`, with `62` figure environments, `15` table environments, and `63` `includegraphics`;
  - no missing figures or duplicate labels;
  - log grep found no fatal LaTeX errors, undefined citations/references, overfull warnings, float-placement errors, or vbox overflow warnings;
  - visible internal-path search returned no matches outside normal bibliography URLs;
  - PDF text-density check found only the title page and two figure-heavy diagnostic pages below the low-text threshold, with no blank content pages.

## 2026-04-23 - Report conceptual critique integration

- Integrated a substantive critique pass into `reports/supervisor_report_readable.tex`.
- Main narrative now explicitly separates two regimes:
  - same-pair temperature extrapolation;
  - transfer to new solute chemistry.
- Added main-text limitations and risks:
  - Murcko scaffold split tests new cores but not all new substituent/functionality patterns;
  - NRTL in low-solubility SLE rows is mostly constrained through effective `ln_gamma_inf(T)`, not independently identifiable `tau_12`, `tau_21`, and `alpha`;
  - crystal and activity branches have asymmetric supervision, making interaction-gradient starvation a symptom of information imbalance;
  - residual physical correction may compensate crystal errors through activity parameters unless parameter deltas are logged;
  - TIMP negative results need train/test linear-probe interpretation to distinguish channel expressivity from transfer failure;
  - delphinidin chloride may involve form equilibria, so binary one-species SLE is only an effective approximation for such salts;
  - learned `dCp_fus` without direct labels needs a separate ablation because it can add noise as well as remove systematic bias.
- Expanded the hypothesis-status and next-validation tables with:
  - NRTL identifiability status;
  - correction-block audit;
  - IDAC/UNIFAC coverage-masked ablations;
  - direct `ln_gamma_inf(T)` comparison;
  - `dCp_fus` ablation.
- Verification:
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has 90 pages, 62 figure environments, 15 table environments, and 63 includegraphics entries;
  - missing figures: 0; duplicate labels: 0;
  - log grep found no fatal LaTeX errors, undefined references/citations, overfull warnings, float-placement warnings, or vbox overflow warnings;
  - visible internal-path search returned no matches outside normal bibliography URLs;
  - PDF text-density check found only the title page and two figure-heavy diagnostic pages below threshold, with no blank content pages.

## 2026-04-23 - Direct activity parameterization and small MPS verification

- Implemented a direct activity mode for TGNN-Solv where the activity branch predicts the observable dilute-limit activity level and temperature coefficient, `ln_gamma_inf(T)`, instead of requiring three independently interpretable NRTL parameters in low-solubility SLE rows.
- Added solver support for the simplified finite-concentration form `ln_gamma_2(x,T)=ln_gamma_inf(T)(1-x)^2`, while preserving the existing NRTL path.
- Added optional training/diagnostic controls:
  - smooth phase-2 loss scheduling;
  - direct bounded residual correction to `ln_x2` as an alternative correction mode;
  - export of corrected parameters and correction deltas;
  - pair-regime diagnostics for known/new pairs, solutes, and solvents;
  - correction-delta audit summaries.
- Added small diagnostic configs for the direct-activity mode, stop-gradient variant, smooth schedule, and direct residual-correction variant.
- Small MPS training on the existing diagnostic split produced:
  - DirectGNN weighted MAE `3.053`, R2 `0.207`;
  - small TGNN-NRTL MAE `3.416`, R2 `0.111`;
  - small TGNN direct-activity MAE `3.236`, R2 `0.194`.
- Interpretation: direct `ln_gamma_inf(T)` improves the small TGNN run over the three-parameter NRTL path, but does not beat the direct model and remains biased/compressed.
- Gradient diagnostics on the direct-activity stop-gradient setup found interaction-gradient starvation still present:
  - TGNN interaction / DirectGNN interaction ratio `0.069` without auxiliary pair loss;
  - ratio `0.268` with auxiliary pair loss weight `0.2`.
- Correction audit for the direct-activity small run found the correction block was not doing the main work:
  - mean final correction magnitude about `0.001` in `ln_x2`;
  - `std(delta_tau12) / std(tau12)` about `0.0013`.
- Pair-regime diagnostics confirmed the main scaffold prediction table is entirely new-pair/new-solute for saved predictions and known-solvent only, so the headline test is transfer to new solute chemistry under a known solvent set.
- Refreshed pairwise contrastive pretraining data:
  - `6,602` total pair examples;
  - `208` hard negatives with Tanimoto >= `0.6` and `|delta ln_x2| > 2`;
  - `239` easy positives and `6,155` easy negatives.
- Updated `reports/supervisor_report_readable.tex` with these implementation and diagnostic results, without adding internal path references to the prose.
- Verification:
  - `python -m pytest tests/test_physics.py -q` passed: `18 passed`;
  - `python -m pytest tests/test_loss.py tests/test_dataset.py -q` passed: `23 passed`;
  - `python -m pytest tests/test_integration.py -q` passed: `32 passed`;
  - Python compile checks passed for modified model, solver, trainer, heads, layers, config, export, and diagnostic scripts;
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `91` pages and size about `5.1 MB`;
  - log grep found no fatal LaTeX errors, undefined references/citations, overfull warnings, float-placement errors, or vbox overflow warnings;
  - visible internal-path search in the report returned no concrete repository path references;
  - PDF text-density check found no blank content pages.

## 2026-04-23 - Auxiliary pair-loss gradient sweep and SLE crystal-detach diagnostic

- Added diagnostic config flag `detach_crystal_params_in_sle` to test whether SLE-loss gradients routed through crystal parameters are responsible for weak pair-block gradients.
- In this mode crystal heads can still learn from auxiliary crystal labels, but the SLE path receives detached crystal parameters.
- Ran short MPS gradient-flow diagnostics for direct-activity TGNN with stop-gradient crystal input:
  - no auxiliary pair loss: TGNN interaction / DirectGNN interaction ratio `0.069`;
  - auxiliary pair loss weight `0.2`: ratio `0.268`;
  - auxiliary pair loss weight `0.2` plus detached SLE crystal parameters: ratio `0.268`;
  - auxiliary pair loss weight `0.5` plus detached SLE crystal parameters: ratio `0.667`;
  - auxiliary pair loss weight `1.0` plus detached SLE crystal parameters: ratio `1.33`.
- Interpretation: detaching crystal parameters from the SLE path does not materially change the gradient ratio at weight `0.2`; the dominant lever is the auxiliary pair-loss weight.
- Added a compact sweep summary under `results/mps_gamma_inf_activity/gradient_flow/aux_weight_sweep_summary.csv`.
- Updated `reports/supervisor_report_readable.tex` to reflect:
  - the auxiliary pair-loss weight sweep;
  - the fact that close R2 between DirectGNN and direct-activity TGNN comes with very different bias/calibration;
  - level/slope diagnostics for the small runs.
- Verification:
  - `python -m pytest tests/test_physics.py tests/test_integration.py -q` passed: `50 passed`;
  - Python compile check passed for modified model/config and related modules;
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `92` pages and size about `5.1 MB`;
  - log grep found no fatal LaTeX errors, undefined references/citations, overfull warnings, float-placement errors, or vbox overflow warnings;
  - PDF text-density check found no blank content pages.

## 2026-04-23 - Activity global-bias diagnostic and report recalibration update

- Added optional trainable global activity offset for direct `ln_gamma_inf(T)` runs:
  - config flags `use_activity_global_bias` and `activity_global_bias_init`;
  - the bias is applied inside the direct-activity `NRTLHead` before the finite-concentration activity approximation.
- Added `scripts/analysis/run_gamma_inf_bias_diagnostics.py` to summarize train/val/test bias, bin-wise residuals, distribution shifts in internal quantities, validation-set post-hoc calibration shifts, and crystal-parameter replacement when rows with valid `T_m` and `dH_fus` exist.
- Ran a small MPS diagnostic with direct activity, trainable global activity bias, auxiliary pair-loss weight `0.5`, crystal-input detachment, and detached SLE crystal parameters.
- Test metrics for the new small run:
  - MAE `3.225`, R2 `0.225`, bias `-1.431`, prediction-std ratio `0.703`;
  - previous direct-activity small run: MAE `3.236`, R2 `0.194`, bias `-1.396`;
  - small full-NRTL run: MAE `3.416`, R2 `0.111`, bias `-1.628`;
  - small DirectGNN reference: MAE `3.053`, R2 `0.207`, bias `+0.011`.
- Pair-level temperature diagnostics:
  - DirectGNN slope MAE `1947 K`;
  - full-NRTL TGNN slope MAE `1471 K`;
  - direct-activity TGNN slope MAE `1471 K`;
  - direct-activity plus global-bias/aux0.5 slope MAE `1506 K`.
- Interpretation:
  - the physical path recovers temperature slopes better than DirectGNN in the small diagnostic, but loses the absolute level;
  - the global activity bias plus stronger auxiliary pair loss improves R2 and only slightly improves MAE, but does not remove the negative level bias;
  - validation-median post-hoc calibration improves test MAE from `3.225` to `2.856` and R2 from `0.225` to `0.315`, so level calibration is a real bottleneck, but this is diagnostic rather than a fair test result;
  - no valid test rows with both `T_m` and `dH_fus` were available in the small split, so the crystal-vs-activity decomposition could not be completed there;
  - bin-wise residuals are not a uniform constant shift: the model overpredicts the extreme low-solubility tail and underpredicts more soluble rows.
- Updated `reports/supervisor_report_readable.tex` with:
  - the slope-versus-level interpretation;
  - the global-bias/aux0.5 result;
  - the post-hoc calibration diagnostic;
  - the conclusion that the next check must separate crystal-level and activity-level errors rather than add another global shift.
- Adjusted report float placement to reduce figure-induced whitespace and rebuilt the report.
- Verification:
  - `python -m pytest tests/test_physics.py tests/test_integration.py -q` passed: `50 passed`;
  - `python -m pytest tests/test_loss.py tests/test_dataset.py -q` passed: `23 passed`;
  - Python compile check passed for modified config/head/report diagnostic script before training;
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `90` pages and size about `5.1 MB`;
  - all `63` includegraphics targets exist;
  - log grep found no fatal LaTeX errors, undefined references/citations, overfull warnings, float-placement errors, or vbox overflow warnings;
  - PDF text-density and sampled page screenshots found no blank content pages after the float-placement adjustment.

## 2026-04-23 - Fixed tail-weighted loss and calibration diagnostics for direct activity

- Extended solubility bin weighting in `src/tgnn_solv/loss.py` and `TGNNSolvConfig`:
  - existing `inverse_frequency` mode is preserved;
  - new `fixed` mode uses configured per-bin weights and normalizes them by the batch mean;
  - added `sol_bin_weights` to make tail weighting reproducible from YAML.
- Added validation-prediction-bin calibration to `scripts/analysis/run_gamma_inf_bias_diagnostics.py`:
  - writes prediction-bin calibration tables;
  - compares validation-fitted prediction-bin shifts with global validation mean/median shifts and test-only oracle shifts.
- Calibration result for the existing direct-activity + global-bias + aux0.5 small run:
  - no post-hoc shift: MAE `3.225`, R2 `0.225`, bias `-1.431`;
  - validation median shift: MAE `2.856`, R2 `0.315`, bias `-0.355`;
  - test oracle median shift: MAE `2.768`, R2 `0.316`, bias `+0.328`;
  - validation prediction-bin median shift with 5 bins: MAE `3.027`, R2 `0.234`, bias `-0.387`.
- Additional calibration sweep found no prediction-bin, linear, Huber-linear, or isotonic post-hoc calibration that beat the global validation median shift by MAE in this small protocol.
- Added `configs/small_debug_gamma_inf_tail_weighted_aux05.yaml` and trained the small MPS fixed-tail-weight run with direct `ln_gamma_inf(T)`, trainable activity bias, aux pair-loss weight `0.5`, and fixed solubility-bin weights.
- Tail-weighted small-run metrics:
  - train: MAE `3.005`, R2 `0.409`, bias `+0.390`, prediction-std ratio `0.589`;
  - validation: MAE `3.054`, R2 `0.256`, bias `+0.141`, prediction-std ratio `0.557`;
  - test: MAE `2.862`, RMSE `3.806`, R2 `0.318`, bias `-0.430`, prediction-std ratio `0.592`.
- Offline comparison on the same small diagnostic split:
  - DirectGNN weighted reference: MAE `3.053`, R2 `0.207`, bias `+0.011`, prediction-std ratio `0.727`;
  - direct-activity TGNN before tail weighting: MAE `3.225`, R2 `0.225`, bias `-1.431`, prediction-std ratio `0.703`;
  - tail-weighted direct-activity TGNN: MAE `2.862`, R2 `0.318`, bias `-0.430`, prediction-std ratio `0.592`.
- Pair-level slope diagnostics:
  - DirectGNN weighted reference slope MAE `1947 K`;
  - direct-activity TGNN before tail weighting slope MAE `1506 K`;
  - tail-weighted direct-activity TGNN slope MAE `1491 K`.
- Interpretation:
  - fixed tail weighting is the first small-protocol TGNN variant in this sequence that beats the small DirectGNN reference without post-hoc calibration;
  - the gain mostly reduces level bias and improves ranking/MAE;
  - it does not solve prediction-range compression, because the prediction-std ratio drops to `0.592`;
  - true-bin residuals remain sign-changing: extreme low-solubility rows are overpredicted, while more soluble rows are underpredicted.
- Updated `reports/supervisor_report_readable.tex` and rebuilt `reports/supervisor_report_readable.pdf`:
  - added the tail-weighted run to the main small-diagnostic table and appendix table;
  - added the negative result for prediction-bin calibration;
  - updated the hypothesis-status table and component-status table;
  - kept prose free of concrete repository path references.
- Verification:
  - `python -m py_compile src/tgnn_solv/config.py src/tgnn_solv/loss.py scripts/analysis/run_gamma_inf_bias_diagnostics.py` passed;
  - `python -m pytest tests/test_loss.py -q` passed: `13 passed`;
  - `python -m pytest tests/test_physics.py tests/test_dataset.py tests/test_integration.py -q` passed: `60 passed`;
  - `cd reports && latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex` succeeded;
  - rebuilt PDF has `91` pages and size about `5.1 MB`;
  - log grep found no fatal LaTeX errors, undefined references/citations, overfull warnings, float-too-large warnings, float-placement errors, or vbox overflow warnings;
  - internal-path search in the report returned no concrete repository path references.

## 2026-04-23 - UNIFAC prior path revalidated on the small diagnostic split

- Confirmed that direct-activity TGNN already supports the form
  `ln_gamma_inf = ln_gamma_inf_UNIFAC + Delta_NN` when
  `nrtl_tau_mode='gamma_inf'` and `use_unifac_gamma_prior=True`.
- Installed optional Modified-UNIFAC runtime dependencies in the environment:
  - `thermo`
  - `chemicals`
  - `lxml`
- Attached UNIFAC priors to the small diagnostic split with
  `scripts/data/attach_unifac_priors_to_splits.py`.
- Coverage on the small split with attached UNIFAC priors:
  - train: `663 / 2629` rows, `25.2%`
  - validation: `31 / 704` rows, `4.4%`
  - test: `61 / 1002` rows, `6.1%`
- Added `configs/small_debug_gamma_inf_tail_weighted_aux05_unifac.yaml` to enable the prior on top of the best tail-weighted direct-activity small configuration.
- Started a small MPS training run with the UNIFAC prior enabled.
- Early result:
  - initial Phase-2 validation after Phase 1: `MAE 3.605`, `R2 -0.023`.
- Practical interpretation:
  - the direct `UNIFAC + Delta_NN` path is implemented and now executable in this environment;
  - on the small transfer split the coverage is too low to make it the main next lever;
  - early validation did not look promising relative to the non-UNIFAC tail-weighted run, while runtime increased sharply;
  - therefore the report treats UNIFAC as a weak prior, not as a central resolved fix.
- Updated `reports/supervisor_report_readable.tex` to mention the low-coverage UNIFAC prior check in the small-run summary and component-status table.

## 2026-04-23 - Crystal-known probe clarifies that crystal error is only part of the level problem

- Added `scripts/analysis/build_crystal_known_probe_split.py` to construct a tiny internal split restricted to rows with both experimental `T_m` and `dH_fus`.
- Built `results/crystal_known_probe/splits/` from the small diagnostic train split:
  - selected rows with both crystal targets: `50`;
  - split sizes: train `35`, validation `7`, test `8`;
  - test set contains only two crystal regimes, so this is strictly a diagnostic probe and not a standalone benchmark.
- Added `configs/small_debug_gamma_inf_tail_weighted_aux05_crystal_probe.yaml` and trained a tail-weighted direct-activity TGNN on this probe:
  - test MAE `0.601`;
  - test RMSE `0.813`;
  - test R2 `0.633`;
  - test bias `+0.087`;
  - prediction-std ratio `0.518`.
- Extended `scripts/analysis/export_checkpoint_predictions.py` with `--oracle` so TGNN checkpoints can be reevaluated with forced crystal-target substitution at inference time.
- Forced-oracle reevaluation of that same TGNN checkpoint on the crystal-known probe test set worsened the result:
  - MAE `1.244`;
  - R2 `-0.113`;
  - bias `+0.118`;
  - prediction-std ratio `0.074`.
- This is strong evidence that the already trained pair/activity branch is co-adapted to the model's own crystal predictions; naive post-hoc replacement with true crystal parameters breaks that balance instead of fixing it.
- `DirectGNN` baseline code in `src/tgnn_solv/baselines/direct_gnn.py` was extended to support `sol_bin_weight_mode='fixed'`, matching the TGNN tail-weight contract.
- Added `configs/small_debug_direct_tail_fixed_crystal_probe.yaml` and trained the comparable tiny DirectGNN:
  - test MAE `0.818`;
  - test RMSE `0.882`;
  - test R2 `0.569`;
  - test bias `-0.370`;
  - prediction-std ratio `0.463`.
- Added `configs/small_debug_gamma_inf_tail_weighted_aux05_crystal_probe_oracle.yaml` and trained the same TGNN architecture with train-time oracle crystal substitution enabled:
  - test MAE `0.567`;
  - test RMSE `0.937`;
  - test R2 `0.512`;
  - test bias `+0.393`;
  - prediction-std ratio `0.472`.
- Forced-oracle reevaluation of the oracle-trained checkpoint still remained poor:
  - MAE `1.251`;
  - R2 `-0.234`;
  - bias `+0.450`;
  - prediction-std ratio `0.076`.
- Interpretation:
  - cleaner crystal supervision helps, but only modestly in this probe (`0.601 -> 0.567` MAE);
  - crystal uncertainty is therefore a real contributor, but not the sole or dominant remaining bottleneck;
  - the coupled compensation between `Phi(T)` and `ln_gamma_2` remains critical;
  - improvements in crystal handling alone are unlikely to resolve the level problem without better pair/activity discrimination.
- Key artifacts:
  - `results/crystal_known_probe/model_comparison_summary.csv`
  - `results/crystal_known_probe/tgnn_test_predictions.csv`
  - `results/crystal_known_probe/tgnn_test_predictions_oracle.csv`
  - `results/crystal_known_probe/direct_test_predictions.csv`
  - `results/crystal_known_probe/tgnn_oracle_train_test_predictions.csv`
  - `results/crystal_known_probe/tgnn_oracle_train_test_predictions_forced_oracle.csv`
- Updated `reports/supervisor_report_readable.tex` to include this probe as a diagnostic result in the main discussion and appendix status table.

## 2026-04-24 - Crystal-known compensation diagnostics and readable-report final pass

- Added `scripts/analysis/run_crystal_probe_compensation_diagnostics.py` to
  quantify crystal/activity compensation directly from saved crystal-known probe
  prediction CSVs.
- Ran the maintained compensation diagnostic on:
  - `results/crystal_known_probe/tgnn_test_predictions.csv`
  - `results/crystal_known_probe/direct_test_predictions.csv`
  - `results/crystal_known_probe/tgnn_oracle_train_test_predictions.csv`
  - `results/crystal_known_probe/tgnn_test_predictions_oracle.csv`
  - `results/crystal_known_probe/tgnn_oracle_train_test_predictions_forced_oracle.csv`
  - with auxiliary overlap check against
    `results/temperature_extrapolation_enhanced_proxy/splits/idac_aux_train.csv`
- Standard TGNN compensation result on the `8` test rows:
  - `corr(delta_phi, delta_gamma) = -0.876`
  - opposite-sign fraction `= 1.0`
  - mean `|delta_phi + delta_gamma| = 0.590`
  - mean `|ln_x2_final - ln_x2_physics| = 0.024`
- Forced-oracle reevaluation destroys that balance instead of fixing it:
  - mean `delta_phi = 1.74e-4` (effectively zero crystal error)
  - mean `|delta_phi + delta_gamma| = 1.242`
  - `MAE = 1.244`
- Oracle-train probe remains only a partial improvement:
  - test `MAE 0.567`
  - test `R^2 0.512`
  - bias `+0.393`
  - oracle-train plus forced-oracle eval still gives `MAE 1.251`
- Per-solute diagnostics show the same compensation pattern in both crystal
  regimes present in this probe:
  - aspirin rows have negative `delta_phi` and positive `delta_gamma`
  - anthracene rows have positive `delta_phi` and negative `delta_gamma`
- Exact IDAC-overlap check on this probe is currently impossible:
  - exact pair overlap rows `0`
  - exact pair overlap unique pairs `0`
  - exact solute overlap `0`
  - exact solvent overlap `0`
  - therefore the intended "IDAC breaks compensation" comparison cannot yet be
    evaluated on the current crystal-known split
- Accepted interpretation:
  - the local TGNN win over DirectGNN on the crystal-known probe is real, but it
    does not indicate clean physical factorization
  - the current model achieves that win through a tightly coupled decomposition
    between `Phi(T)` and `ln_gamma_2`
  - a dedicated overlap-aware SLE/IDAC protocol is now required for the next
    decisive activity-branch test
- New artifacts:
  - `results/crystal_known_probe/compensation_diagnostics/summary.json`
  - `results/crystal_known_probe/compensation_diagnostics/compensation_summary.csv`
  - `results/crystal_known_probe/compensation_diagnostics/per_solute_summary.csv`
  - `results/crystal_known_probe/compensation_diagnostics/mode_metrics.csv`
  - `results/crystal_known_probe/compensation_diagnostics/standard_row_diagnostics.csv`
  - `results/crystal_known_probe/compensation_diagnostics/SUMMARY.md`
- Updated `reports/supervisor_report_readable.tex` again to:
  - fold the explicit compensation numbers into the supervisor summary, results,
    diagnosis, hypothesis-status, and appendix-summary sections
  - record the current zero-overlap limitation for IDAC on this probe
  - add small `needspace` guards and a local prose bridge to avoid section
    headings dangling at the bottom of a page in the edited region
- Performed a full visual audit of the readable supervisor PDF after those
  report edits and then applied a second readability pass:
  - checked every page of `reports/supervisor_report_readable.pdf`
  - found two real layout defects in the appendix (`AC` and `AE` section
    headings stretched with huge inter-word gaps) and fixed them via manual
    line breaks in the section titles
  - converted the two early summary tables ("Статус рабочих гипотез" and
    "Химические примеры") from float tables to `longtable` so they can start on
    the section page and continue naturally instead of leaving half-page blanks
- Current readable-report artifact after the full audit:
  - `reports/supervisor_report_readable.pdf`
  - rebuilt successfully with XeLaTeX on `2026-04-24`
  - current length `95` pages (down from `96` after the longtable compaction)
  - targeted recheck confirmed cleaner pages `17`--`20` and fixed appendix
    headings on pages `87` and `89`
- Audited the full canonical scaffold corpus for rows with simultaneous
  supervised solubility, `T_m`, and `dH_fus`:
  - full `train/val/test` union contains `1080` such rows out of `127088`
    total rows and `108287` supervised-solubility rows
  - all `1080` joint-label rows are in `train`; `val` and `test` contain `0`
  - effective support is much smaller than the row count suggests:
    `146` unique pairs, only `11` unique solutes, `77` solvents, and all such
    rows come from `BigSolDBv2.1`
  - therefore a naive batchwise decorrelation penalty
    `corr(delta_phi, delta_gamma)^2` would be very sparse in standard mixed
    training batches; with batch size `64`, the expected number of joint-label
    rows is only `0.62`, `P(batch has >=2)` is about `12.9%`, and
    `P(batch has >=3)` is about `2.5%`
  - accepted implementation implication: if a crystal/activity decorrelation
    loss is tried, it should use a dedicated or oversampled auxiliary loader
    rather than an ordinary per-batch term on the main scaffold train stream

## 2026-04-24 - Open ThermoML crystal-data pipeline and overlap audit

- Added a reproducible open crystal-data path rather than keeping ThermoML
  crystal extraction as an untracked helper:
  - `scripts/data/extract_crystal_from_thermoml.py`
  - `scripts/data/build_open_crystal_artifact.py`
  - `tests/test_thermoml_crystal.py`
- Refactored crystal-source loading in `src/tgnn_solv/data/sources.py` to make
  source-specific open inputs explicit without changing the canonical
  `load_melting_points()` / `load_fusion_enthalpies()` behavior:
  - `load_bradley_melting_points()`
  - `load_curated_melting_points()`
  - `load_curated_fusion_enthalpies()`
  - curated crystal constants are now top-level mappings instead of being
    buried only inside the merged loaders
- Ran the new ThermoML crystal extractor on the maintained local cache under
  `notebooks/data/raw/thermoml_json`:
  - input cache size: `3721` JSON records
  - raw extracted crystal measurements:
    `results/thermoml_crystal/thermoml_crystal_measurements.csv`
    with `1679` rows, `846` solutes, `473` DOI sources
  - aggregated ThermoML crystal artifact:
    `results/thermoml_crystal/thermoml_crystal_aggregated.csv`
    with `701` solutes carrying `T_m`, `473` carrying `dH_fus`, and `473`
    carrying both
  - extraction summary:
    `results/thermoml_crystal/summary.json`
- Built the first explicit open crystal artifact with source-level priority and
  processed-split overlap audit:
  - main artifact:
    `results/open_crystal_artifact/open_crystal_solute.csv`
  - coverage audit:
    `results/open_crystal_artifact/coverage_by_split.csv`
  - pairwise source agreement audit:
    `results/open_crystal_artifact/pairwise_source_agreement.csv`
  - human/machine summaries:
    `results/open_crystal_artifact/summary.md`
    and `results/open_crystal_artifact/summary.json`
- Current accepted source-priority policy in that artifact:
  - `T_m`: `curated_nist_webbook > thermoml > bradley`
  - `dH_fus`: `curated_nist_webbook > thermoml`
- Resulting open artifact coverage:
  - `19,436` solutes with final `T_m`
  - `495` solutes with final `dH_fus`
  - `495` solutes with final joint `T_m + dH_fus`
  - selected `T_m` sources:
    `32` curated, `688` ThermoML, `18,716` Bradley
  - selected `dH_fus` sources:
    `31` curated, `464` ThermoML
- Gain versus the current canonical supervised corpus if this open artifact is
  attached solute-wise:
  - joint-label rows (`has_solubility & T_m & dH_fus`) become:
    - train: `1080 -> 14401`
    - val: `0 -> 288`
    - test: `0 -> 221`
    - full union: `1080 -> 14910`
  - unique supervised `(solute, solvent)` pairs with both labels become:
    `146 -> 1497`
  - the key protocol consequence is that joint-label supervision is no longer
    train-only if this sidecar is adopted
- Source-agreement findings that justify the chosen priority:
  - curated `T_m` vs ThermoML `T_m`:
    `13` overlaps, median absolute delta `0.275 K`
  - ThermoML `T_m` vs Bradley `T_m`:
    `307` overlaps, median absolute delta `273.45 K`
  - curated `dH_fus` vs ThermoML `dH_fus`:
    `9` overlaps, median absolute delta `930 J/mol`
  - accepted interpretation:
    - curated crystal values are consistent enough to remain highest priority
    - ThermoML is a strong open expansion path, especially for `dH_fus`
    - Bradley remains useful for broad `T_m` coverage but should stay
      lowest-priority where ThermoML exists
- Documentation/report updates:
  - `docs/data_preparation.md` now documents the full open crystal path,
    commands, priority order, and current overlap numbers
  - `docs/script_reference.md` and `scripts/README.md` now list the new
    crystal-data CLIs
  - `reports/supervisor_report_readable.tex` now records the new open
    crystal-data contour, current coverage numbers, and the Bradley-vs-ThermoML
    conflict signal
- Important scope note:
  - this open crystal artifact is intentionally still a sidecar resource, not a
    silent replacement for the canonical `notebooks/data/processed/*.csv`
  - adopting it into the maintained benchmark contract would require an
    explicit protocol decision because it changes where direct crystal
    supervision is available, especially in `val` and `test`

## 2026-04-24 - Crystal/activity decorrelation loss hook

- Added an opt-in decorrelation penalty to `src/tgnn_solv/loss.py`:
  - loss key: `decorr`
  - formula on jointly supervised rows:
    `corr(delta_phi, delta_gamma)^2`
  - the decomposition matches
    `scripts/analysis/run_crystal_probe_compensation_diagnostics.py`:
    `delta_phi = Phi_pred - Phi_true`
    and
    `delta_gamma = ln_gamma_2_pred - (-ln_x2_true - Phi_true)`
- Activation contract:
  - only rows with simultaneous `ln_x2`, `T_m`, and `dH_fus` supervision
    contribute
  - new config hooks in `src/tgnn_solv/config.py`:
    `decorr_min_samples` and `decorr_eps`
  - safe skip behavior for too-small batches, non-finite rows, and zero-variance
    branch errors
- Trainer defaults now expose `decorr: 0.0` in all three phases via
  `src/tgnn_solv/trainer.py`, so any experiment must enable it explicitly
  through `phase{1,2,3}_loss_weights`.
- Added regression tests in `tests/test_loss.py` for:
  - perfect anti-correlation (`loss ~= 1`)
  - skip on too-small joint batches
  - skip on zero-variance branch errors
- Verification run:
  - `KMP_DUPLICATE_LIB_OK=TRUE conda run -n tgnn-solv python -m py_compile src/tgnn_solv/config.py src/tgnn_solv/trainer.py src/tgnn_solv/loss.py tests/test_loss.py`
  - `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src conda run -n tgnn-solv python -m pytest tests/test_loss.py tests/test_config.py -q`
  - result: `33 passed`
- Important scope note:
  - this is plumbing only; no maintained training run uses a nonzero `decorr`
    weight yet
  - the earlier corpus audit still applies:
    on the current canonical scaffold split, ordinary mixed batches are too
    sparse for this term to fire often without an auxiliary or oversampled
    joint-label stream

## 2026-04-24 - Crystal-known probe decorrelation ablation

- Ran a small reproducible `L_decorr` sweep on the maintained
  `crystal-known probe` split (`35/7/8` train/val/test) where every row has
  joint `ln_x2`, `T_m`, and `dH_fus` labels.
- Added dedicated configs:
  - `configs/small_debug_gamma_inf_tail_weighted_aux05_crystal_probe_decorr_005.yaml`
  - `configs/small_debug_gamma_inf_tail_weighted_aux05_crystal_probe_decorr_020.yaml`
  - `configs/small_debug_gamma_inf_tail_weighted_aux05_crystal_probe_decorr_050.yaml`
- Added aggregation helper:
  - `scripts/analysis/summarize_crystal_probe_decorr_ablation.py`
- Produced new checkpoints and prediction exports under:
  - `checkpoints/crystal_known_probe/`
  - `results/crystal_known_probe/decorr_ablation/`
- Main summary artifact:
  - `results/crystal_known_probe/decorr_ablation/decorr_ablation_summary.csv`
  - `results/crystal_known_probe/decorr_ablation/SUMMARY.md`
- Quantitative outcome of the sweep:
  - baseline (`decorr=0.0`):
    `MAE=0.6014`, `R^2=0.6332`,
    `pred_std_ratio=0.5177`,
    `corr(delta_phi,delta_gamma)=-0.8765`,
    `mean_abs(delta_phi+delta_gamma)=0.5900`,
    `forced_oracle_MAE=1.2436`
  - `decorr=0.05`:
    `MAE=0.6011`, `R^2=0.6337`,
    `pred_std_ratio=0.5185`,
    `corr=-0.8764`,
    `mean_abs_sum=0.5897`,
    `forced_oracle_MAE=1.2435`
  - `decorr=0.20`:
    `MAE=0.5992`, `R^2=0.6353`,
    `pred_std_ratio=0.5209`,
    `corr=-0.8763`,
    `mean_abs_sum=0.5878`,
    `forced_oracle_MAE=1.2431`
  - `decorr=0.50`:
    `MAE=0.5969`, `R^2=0.6383`,
    `pred_std_ratio=0.5253`,
    `corr=-0.8762`,
    `mean_abs_sum=0.5855`,
    `forced_oracle_MAE=1.2425`
- Accepted interpretation:
  - on this probe, direct decorrelation loss behaves as weak regularization,
    not as a mechanism that breaks the coupled decomposition
  - standard-eval quality improves only marginally (`MAE 0.601 -> 0.597`)
  - the compensation structure remains essentially unchanged
    (`corr(delta_phi,delta_gamma)` stays near `-0.876`)
  - forced-oracle failure is not rescued
    (`forced_minus_standard_MAE` slightly increases from `0.642` to `0.646`)
- Report synchronization:
  - `reports/supervisor_report_readable.tex` now includes
    - the explicit definition of `L_decorr` in the training section
    - the negative-result ablation table in the `crystal-known probe` section
    - the updated summary and hypotheses text reflecting that
      decorrelation loss alone does not resolve identifiability
- Verification:
  - `latexmk -g -xelatex -interaction=nonstopmode supervisor_report_readable.tex`
    succeeded in `reports/`

## 2026-04-24 - Open ThermoML finite-composition activity-data contour

- Added a reproducible ThermoML activity-side extractor for the next missing
  supervision signal:
  - `src/tgnn_solv/data/thermoml_activity.py`
  - `scripts/data/extract_activity_from_thermoml.py`
  - `tests/test_thermoml_activity.py`
- Scope of the new contour:
  - finite-composition `Activity coefficient`
  - finite-composition `(Relative) activity`
  - `Excess molar enthalpy (molar enthalpy of mixing)`
  - intentionally excludes infinite-dilution activity-coefficient rows already
    covered by the dedicated ThermoML `IDAC` path
- Verification:
  - `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src conda run -n tgnn-solv python -m py_compile src/tgnn_solv/data/thermoml_activity.py scripts/data/extract_activity_from_thermoml.py tests/test_thermoml_activity.py`
  - `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src conda run -n tgnn-solv python -m pytest tests/test_thermoml_activity.py tests/test_thermoml_idac.py tests/test_thermoml_crystal.py -q`
  - result: `10 passed`
- Ran the extractor on the maintained local ThermoML cache:
  - command:
    `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src conda run -n tgnn-solv python scripts/data/extract_activity_from_thermoml.py --json-dir notebooks/data/raw/thermoml_json --processed-dir notebooks/data/processed --output-raw results/thermoml_activity/thermoml_activity_measurements.csv --output-aggregated results/thermoml_activity/thermoml_activity_aggregated.csv --audit-output results/thermoml_activity/summary.json --summary-md results/thermoml_activity/SUMMARY.md --parse-audit-csv results/thermoml_activity/parse_audit.csv`
  - outputs:
    - `results/thermoml_activity/thermoml_activity_measurements.csv`
    - `results/thermoml_activity/thermoml_activity_aggregated.csv`
    - `results/thermoml_activity/summary.json`
    - `results/thermoml_activity/SUMMARY.md`
    - `results/thermoml_activity/parse_audit.csv`
- Current artifact counts on the local cache (`3721` JSON files):
  - raw rows: `8,821`
  - aggregated exact-state rows: `8,683`
  - DOI sources: `102`
  - unordered binary pairs: `295`
  - targeted direct-activity pairs: `109`
  - property breakdown:
    - `activity_coefficient`: `345`
    - `relative_activity`: `3,146`
    - `excess_molar_enthalpy`: `5,192`
  - direct finite-composition activity subset:
    - total rows: `3,491`
    - target components: `7`
    - mole-fraction `>= 0.10`: `1,161` rows / `27` targeted pairs
    - mole-fraction `>= 0.20`: `1,087` rows / `25` targeted pairs
- Temperature-span signal is real:
  - direct `Activity coefficient` groups:
    `11` total, `4` with span `>= 20 K`, max span `60 K`
  - direct `(Relative) activity` groups:
    `98` total, `35` with span `>= 20 K`, max span `273.3 K`
  - excess-enthalpy groups:
    `196` total, `63` with span `>= 20 K`, max span `380 K`
- Overlap against the current maintained scaffold SLE benchmark is the key
  limitation:
  - unordered exact pair overlap:
    - train: `6`
    - val: `0`
    - test: `0`
  - direct target-as-solute overlap:
    - train: `0`
    - val: `0`
    - test: `0`
  - direct target-as-solvent overlap:
    - train: `6`
    - val: `0`
    - test: `0`
  - direct target components appearing in current SLE solutes:
    `0`
  - direct target components appearing in current SLE solvents:
    `4`
- Accepted interpretation:
  - open finite-composition ThermoML activity data now exists as a reproducible
    sidecar and is large enough to justify dedicated future auxiliary
    objectives
  - but on the maintained scaffold protocol it does not yet break the crystal /
    activity identifiability bottleneck because the exact overlap is tiny and
    the current exact overlaps supervise the solvent side rather than the
    dissolved-solute side of the decomposition
  - this sharpens the next data-collection requirement:
    grow *intersecting* pair-level activity coverage, not just generic ThermoML
    activity volume
- Report/docs synchronization:
  - `docs/data_preparation.md` now documents the full finite-composition
    ThermoML activity path, current counts, and overlap limits
  - `docs/script_reference.md` and `scripts/README.md` now list the new
    extractor
  - `reports/supervisor_report_readable.tex` now states explicitly that
    decorrelation loss is blocked by information insufficiency and records the
    new ThermoML activity contour as the concrete next data-collection route

## 2026-04-25 - ThermoML activity contour property-level overlap audit

- Extended the finite-composition ThermoML summary path so overlap is reported
  by property, not only in aggregate:
  - `scripts/data/extract_activity_from_thermoml.py`
  - `tests/test_thermoml_activity.py`
- Verification:
  - `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python -m py_compile scripts/data/extract_activity_from_thermoml.py tests/test_thermoml_activity.py`
  - `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python -m pytest tests/test_thermoml_activity.py -q`
  - result: `5 passed`
- Regenerated the maintained ThermoML activity-side artifacts:
  - command:
    `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python scripts/data/extract_activity_from_thermoml.py --json-dir notebooks/data/raw/thermoml_json --processed-dir notebooks/data/processed --output-raw results/thermoml_activity/thermoml_activity_measurements.csv --output-aggregated results/thermoml_activity/thermoml_activity_aggregated.csv --audit-output results/thermoml_activity/summary.json --summary-md results/thermoml_activity/SUMMARY.md --parse-audit-csv results/thermoml_activity/parse_audit.csv`
  - updated outputs:
    - `results/thermoml_activity/summary.json`
    - `results/thermoml_activity/SUMMARY.md`
    - `results/thermoml_activity/thermoml_activity_aggregated.csv`
    - `results/thermoml_activity/thermoml_activity_measurements.csv`
- New property-specific overlap facts on the maintained scaffold SLE protocol:
  - `relative_activity`:
    - train overlap `148` rows / `6` exact unordered pairs
    - val overlap `0`
    - test overlap `0`
    - direct target-as-solute overlap `0`
    - direct target-as-solvent overlap `148` rows / `6` pairs
  - `activity_coefficient`:
    - exact pair overlap `0` on train/val/test
  - `excess_molar_enthalpy`:
    - exact pair overlap `0` on train/val/test
- Accepted interpretation:
  - there is no hidden `H^E` reserve in the current open ThermoML contour for
    the maintained scaffold benchmark; all current exact overlap comes only
    from solvent-targeted `relative_activity`
  - the bottleneck is therefore sharper than "too little activity data":
    the current SLE corpus and finite-composition ThermoML corpus are mostly
    covering different molecule pairs
  - the next decisive data step should be targeted coverage expansion over the
    `12,129` maintained SLE pairs, not just generic ThermoML volume growth
- Report synchronization:
  - `reports/supervisor_report_readable.tex` now states explicitly that the
    overlap bottleneck is property-specific and structural, not just a weak
    aggregate-count effect

## 2026-04-25 - Targeted ThermoML exact-pair coverage artifact

- Added a new exact-pair ThermoML coverage collector aimed at the real
  activity-branch bottleneck rather than generic ThermoML volume:
  - `src/tgnn_solv/data/thermoml_targeted.py`
  - `scripts/data/collect_targeted_thermoml_coverage.py`
  - `tests/test_thermoml_targeted.py`
- Purpose of the new artifact:
  - scan all binary ThermoML property labels against the maintained SLE pair
    list
  - expand unordered ThermoML binary matches to directed SLE
    `solute -> solvent` pairs
  - separate generic pair overlap from activity-signal candidate overlap
  - write actionable gap lists:
    - `candidate_covered_sle_pairs.csv`
    - `candidate_missing_sle_pairs.csv`
- Verification:
  - `python -m py_compile src/tgnn_solv/data/thermoml_targeted.py scripts/data/collect_targeted_thermoml_coverage.py tests/test_thermoml_targeted.py`
  - `PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python -m pytest tests/test_thermoml_targeted.py -q`
  - result: `3 passed`
- Built the new coverage artifact on the maintained local ThermoML cache:
  - command:
    `PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python scripts/data/collect_targeted_thermoml_coverage.py --processed-dir notebooks/data/processed --json-dir notebooks/data/raw/thermoml_json --out-dir results/thermoml_targeted_coverage`
  - outputs:
    - `results/thermoml_targeted_coverage/summary.json`
    - `results/thermoml_targeted_coverage/SUMMARY.md`
    - `results/thermoml_targeted_coverage/thermoml_binary_pair_matches.csv`
    - `results/thermoml_targeted_coverage/sle_pair_matches.csv`
    - `results/thermoml_targeted_coverage/coverage_by_split.csv`
    - `results/thermoml_targeted_coverage/coverage_by_family.csv`
    - `results/thermoml_targeted_coverage/coverage_by_property.csv`
    - `results/thermoml_targeted_coverage/covered_sle_pairs.csv`
    - `results/thermoml_targeted_coverage/missing_sle_pairs.csv`
    - `results/thermoml_targeted_coverage/candidate_covered_sle_pairs.csv`
    - `results/thermoml_targeted_coverage/candidate_missing_sle_pairs.csv`
- Key findings on the maintained scaffold benchmark:
  - generic exact binary ThermoML overlap is not tiny:
    - `2353 / 12129` directed SLE pairs matched at least one binary ThermoML
      property label
    - split coverage:
      - train `2029 / 10560` (`19.21%`)
      - val `151 / 746` (`20.24%`)
      - test `173 / 823` (`21.02%`)
    - matched DOI count: `454`
  - but almost all of that overlap is the wrong supervision family:
    - composition-like labels dominate:
      - train `1925` pairs
      - val `151` pairs
      - test `171` pairs
    - candidate activity-signal families
      (`direct_activity`, `solution_thermo`, `excess_thermo`, `vle_like`)
      cover only `16` directed SLE pairs total:
      - train `14`
      - val `0`
      - test `2`
  - candidate-family breakdown:
    - `direct_activity`: train `7`, val `0`, test `0`
      - direct target-as-solute still `0`
      - direct target-as-solvent `7`
    - `solution_thermo`: train `11`, val `0`, test `2`
      - mostly `Molar enthalpy of dilution`, `Molar enthalpy of solution`,
        `Osmotic coefficient`
    - `vle_like`: train `1`, val `0`, test `0`
      - `Boiling temperature at pressure P, K`
    - `excess_thermo`: exact overlap still `0`
- Accepted interpretation:
  - the structural bottleneck is now sharper than "ThermoML and SLE barely
    overlap by pair"
  - generic exact pair overlap exists, but almost all matched labels are
    composition-like or generic physical properties that do not independently
    identify the activity branch
  - the next data-collection step should therefore target the
    `candidate_missing_sle_pairs.csv` gap list and seek exactly the missing
    supervision families, not just more ThermoML volume
- Report/docs synchronization:
  - `reports/supervisor_report_readable.tex` now records the stronger result:
    generic ThermoML exact-pair overlap exists, but candidate activity-signal
    overlap remains tiny
  - `scripts/README.md`, `docs/script_reference.md`, and
    `docs/data_preparation.md` now document the new targeted coverage collector

## 2026-04-25 - Targeted ThermoML measurement-level harvest for exact SLE pairs

- Extended the exact-pair ThermoML collector from property-label overlap to
  measurement-level harvesting:
  - `src/tgnn_solv/data/thermoml_targeted.py`
  - `scripts/data/collect_targeted_thermoml_coverage.py`
  - `tests/test_thermoml_targeted.py`
- Added measurement-level outputs under
  `results/thermoml_targeted_coverage/`:
  - `thermoml_targeted_measurements.csv`
  - `thermoml_targeted_measurements_aggregated.csv`
  - `sle_targeted_measurements_aggregated.csv`
  - `candidate_sle_targeted_measurements_aggregated.csv`
  - `candidate_measurement_covered_sle_pairs.csv`
  - `candidate_measurement_missing_sle_pairs.csv`
- The collector now:
  - extracts numeric ThermoML rows for exact matched binary pairs
  - preserves DOI, phase, method, standard state, temperature, pressure, and
    composition metadata
  - aggregates to exact thermodynamic states
  - separates label-level candidate overlap from measurement-backed candidate
    overlap
- Verification:
  - `python -m py_compile src/tgnn_solv/data/thermoml_targeted.py scripts/data/collect_targeted_thermoml_coverage.py tests/test_thermoml_targeted.py`
  - `PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python -m pytest tests/test_thermoml_targeted.py -q`
  - result: `5 passed`
- Regenerated the maintained local-cache artifact with:
  - `PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python scripts/data/collect_targeted_thermoml_coverage.py --processed-dir notebooks/data/processed --json-dir notebooks/data/raw/thermoml_json --out-dir results/thermoml_targeted_coverage`
- Measurement-level result on the maintained local cache (`3721` JSON):
  - raw exact-pair measurement rows: `30,903`
  - exact-state aggregates: `30,336`
  - directed candidate-family exact-state aggregates: `698`
  - property-level candidate pairs: `16`
  - measurement-backed candidate pairs: `15`
    - train `13`
    - val `0`
    - test `2`
  - candidate-family state breakdown:
    - `Molar enthalpy of dilution`: `472` states across `7` train pairs
    - `(Relative) activity`: `148` states across `6` train pairs
    - `Osmotic coefficient`: `31` states across `3` train pairs
    - `Molar enthalpy of solution`: `8` states across `4` pairs (`2` train,
      `2` test)
    - `Boiling temperature at pressure P`: `39` states across `1` train pair
- Important correction:
  - one train pair (`Cc1ccccc1>>O`, DOI `10.1021/acs.jced.7b00114`) appears as
    a candidate at the property-label level because the record exposes
    `Activity coefficient`, but the usable numeric row is IDAC-like and is
    therefore filtered from the measurement-backed artifact
- Accepted interpretation:
  - the repo now has a concrete exact-pair ThermoML measurement harvest rather
    than only an overlap audit
  - the practical bottleneck is sharper than before: after removing the
    IDAC-like false positive, only `15` exact SLE pairs have any usable
    candidate-family measurement in the maintained open cache
  - targeted collection should therefore use
    `candidate_measurement_missing_sle_pairs.csv` as the operative gap list,
    not the looser property-label-only candidate view

## 2026-04-25 - Finite-composition Modified-UNIFAC pseudo coverage on exact SLE gaps

- Added a synthetic exact-pair coverage-expansion path for the current
  measurement-backed ThermoML gap:
  - `src/tgnn_solv/unifac.py`
    - new `modified_unifac_lngamma_binary(...)` helper for finite-composition
      solute-side `ln(gamma)` in binary mixtures
  - `scripts/data/build_unifac_finite_activity_coverage.py`
  - `tests/test_unifac_finite.py`
- Purpose:
  - evaluate finite-composition Modified-UNIFAC pseudo activity on the same
    directed SLE pairs that currently lack usable open ThermoML activity-side
    measurements
  - report pair-level and source-state-level coverage before committing to a
    larger exact-row pseudo-label build
  - separate missing-group bottlenecks from numerical UNIFAC failures
- Verification:
  - `python -m py_compile src/tgnn_solv/unifac.py scripts/data/build_unifac_finite_activity_coverage.py tests/test_unifac_finite.py`
  - `PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python -m pytest tests/test_unifac_finite.py -q`
  - result: `3 passed`
- Built the maintained synthetic-coverage artifact with:
  - `PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python scripts/data/build_unifac_finite_activity_coverage.py --processed-dir notebooks/data/processed --out-dir results/unifac_finite_activity_coverage`
- Outputs:
  - `results/unifac_finite_activity_coverage/unifac_finite_activity_pseudo.csv`
  - `results/unifac_finite_activity_coverage/pair_status.csv`
  - `results/unifac_finite_activity_coverage/missing_pairs.csv`
  - `results/unifac_finite_activity_coverage/evaluation_failures.csv`
  - `results/unifac_finite_activity_coverage/coverage_by_split.csv`
  - `results/unifac_finite_activity_coverage/summary.json`
  - `results/unifac_finite_activity_coverage/SUMMARY.md`
- Current run configuration:
  - target set: `candidate_measurement_missing_sle_pairs.csv`
  - temperature mode: `pair_median`
  - composition grid: `0.01, 0.02, 0.05, 0.10, 0.20`
- Synthetic coverage result on the exact missing-pair set:
  - target missing directed pairs: `12,114`
  - missing-pair set source pair-temperature states: `108,148`
  - ready UNIFAC pairs: `2,756`
  - pair coverage on the missing set: `22.75%`
  - source-state coverage on the missing set: `23.28%`
  - split-wise pair coverage:
    - train: `2648 / 10547` (`25.11%`)
    - val: `50 / 746` (`6.70%`)
    - test: `58 / 821` (`7.06%`)
  - source-state coverage by split:
    - train: `24,467 / 96,679`
    - val: `302 / 5,663`
    - test: `411 / 5,806`
  - generated pseudo rows in this median-temperature grid run: `13,780`
  - evaluation failures with groups present: `0`
- Remaining bottleneck for the synthetic path:
  - `9,297` pairs are missing solute UNIFAC groups
  - `14` pairs are missing solvent UNIFAC groups
  - `47` pairs are missing both
- Accepted interpretation:
  - this is the first concrete path that materially increases exact-pair
    activity-side coverage without waiting for new experimental DOI discovery
  - the gain is meaningful but still partial: roughly one quarter of the
    current measurement-backed gap can be closed with existing Modified-UNIFAC
    group coverage
  - the dominant remaining blocker is not UNIFAC numerical instability but
    missing solute-group assignments, so the next synthetic expansion should
    focus on broader fragment/group coverage or a COSMO-style fallback rather
    than on retrying the same UNIFAC stack

## 2026-04-25 - Approximate-fallback UNIFAC coverage expansion and finite gamma2 aux smoke

- Extended the finite-composition UNIFAC route so it can be used as an
  activity-only auxiliary stream rather than only as a coverage audit:
  - `src/tgnn_solv/unifac.py`
    - added opt-in approximate lookup fallback for Modified-UNIFAC group
      assignment via stereochemistry stripping, largest-fragment extraction,
      neutralization, and neutralized-largest-fragment retry
    - exact behavior remains unchanged unless
      `allow_approximate_fallback=True`
  - `scripts/data/build_unifac_finite_activity_coverage.py`
    - added `--allow-approximate-fallback`
  - `scripts/data/build_unifac_finite_activity_aux_stream.py`
    - new builder for standalone finite-composition `ln(gamma_2)` auxiliary CSVs
      compatible with `scripts/train.py --idac-train-data`
  - `src/tgnn_solv/data/dataset.py`
    - added finite-activity targets `ln_gamma_2_target`, `gamma2_mask`,
      `gamma2_weight`, `activity_x2`
  - `src/tgnn_solv/model.py`
    - extended `gamma_only=True` fast path so NRTL can evaluate finite
      `ln(gamma_2)` at supplied `x2`
  - `src/tgnn_solv/loss.py`
    - added `gamma_2` loss component
  - `src/tgnn_solv/trainer.py`
    - auxiliary activity loader now accepts either `gamma_inf` or finite
      `gamma_2`
  - `scripts/train.py`
    - help text broadened from IDAC-only wording to generic activity auxiliary
      wording
- Verification:
  - `python -m py_compile src/tgnn_solv/unifac.py scripts/data/build_unifac_finite_activity_coverage.py scripts/data/build_unifac_finite_activity_aux_stream.py src/tgnn_solv/data/dataset.py src/tgnn_solv/loss.py src/tgnn_solv/model.py src/tgnn_solv/trainer.py scripts/train.py tests/test_loss.py tests/test_integration.py tests/test_unifac_finite.py`
  - `PYTHONPATH=src KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python -m pytest tests/test_loss.py tests/test_integration.py tests/test_unifac_finite.py -q`
  - result: `53 passed`
- Rebuilt exact-gap finite-composition coverage with approximate fallback:
  - command:
    - `PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python scripts/data/build_unifac_finite_activity_coverage.py --processed-dir notebooks/data/processed --out-dir results/unifac_finite_activity_coverage_fallback --allow-approximate-fallback`
  - outputs:
    - `results/unifac_finite_activity_coverage_fallback/summary.json`
    - `results/unifac_finite_activity_coverage_fallback/SUMMARY.md`
    - `results/unifac_finite_activity_coverage_fallback/pair_status.csv`
    - `results/unifac_finite_activity_coverage_fallback/missing_pairs.csv`
  - coverage gain versus the maintained exact-only finite-composition run:
    - ready missing-gap directed pairs: `2756 -> 3076`
    - pair coverage: `22.75% -> 25.39%`
    - generated pseudo rows: `13,780 -> 15,380`
    - source-state coverage: `23.28% -> 25.82%`
    - split-wise pair coverage:
      - train: `25.11% -> 27.72%` (`2648 -> 2924`)
      - val: `6.70% -> 8.45%` (`50 -> 63`)
      - test: `7.06% -> 10.84%` (`58 -> 89`)
- Built a finite-activity auxiliary stream for the current small MPS rescue
  split:
  - command:
    - `PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/bin/conda run -p /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv python scripts/data/build_unifac_finite_activity_aux_stream.py --input-csv results/mps_small_rescue/splits/train.csv --template-csv results/mps_small_rescue/splits/train.csv --output-csv results/mps_small_rescue/unifac_finite_activity_aux/gamma2_aux_train.csv --summary-json results/mps_small_rescue/unifac_finite_activity_aux/summary.json --allow-approximate-fallback`
  - result:
    - `177 / 566` train pairs covered (`31.27%`)
    - `680 / 2319` train states covered (`29.32%`)
    - artifact:
      - `results/mps_small_rescue/unifac_finite_activity_aux/gamma2_aux_train.csv`
- Ran a faster tiny smoke ablation before committing to a full small-split
  retrain:
  - tiny split built from pair subsamples of
    `results/mps_small_rescue/splits/{train,val,test}.csv`
    under `results/unifac_gamma2_tiny/splits/`
    - sizes: train `545` rows / `128` pairs, val `155` / `32`, test `271` / `48`
  - tiny train auxiliary stream:
    - `results/unifac_gamma2_tiny/unifac_finite_activity_aux/gamma2_aux_train.csv`
    - coverage: `36 / 123` train pairs (`29.27%`),
      `176 / 517` train states (`34.04%`)
  - matched tiny baseline run:
    - checkpoint: `checkpoints/unifac_gamma2_tiny_baseline.pt`
    - logs: `logs/unifac_gamma2_tiny_baseline/`
    - exported summaries:
      - `results/unifac_gamma2_tiny/baseline_val_summary.json`
      - `results/unifac_gamma2_tiny/baseline_test_summary.json`
    - metrics:
      - val: MAE `2.8563`, RMSE `3.7192`, R2 `-0.3002`,
        `pred_std_ratio=0.5030`
      - test: MAE `4.0827`, RMSE `5.0914`, R2 `0.0025`,
        `pred_std_ratio=0.3421`
  - matched tiny finite-activity aux run:
    - checkpoint: `checkpoints/unifac_gamma2_tiny_aux.pt`
    - logs: `logs/unifac_gamma2_tiny_aux/`
    - exported summaries:
      - `results/unifac_gamma2_tiny/aux_val_summary.json`
      - `results/unifac_gamma2_tiny/aux_test_summary.json`
    - metrics:
      - val: MAE `2.8061`, RMSE `3.6669`, R2 `-0.2638`,
        `pred_std_ratio=0.4717`
      - test: MAE `4.0915`, RMSE `5.0828`, R2 `0.0059`,
        `pred_std_ratio=0.3232`
- Additional tiny-split coverage readout:
  - observed-state UNIFAC coverage on the tiny val/test splits is still sparse
    even with approximate fallback:
    - val: `4 / 29` pairs (`13.79%`), `4 / 152` states (`2.63%`)
    - test: `4 / 46` pairs (`8.70%`), `34 / 256` states (`13.28%`)
- Accepted interpretation:
  - approximate fallback materially improves finite-composition exact-gap
    coverage and raises scaffold-test missing-gap coverage from `7.06%` to
    `10.84%`, so it is worth keeping as the maintained low-cost synthetic path
  - the first matched tiny ablation does not show a clear global test gain from
    finite `gamma_2` auxiliary supervision after a `1/1/0` budget
  - on this tiny budget the effect looks more like weak regularization on val
    than a demonstrated compensation break on test, and the tiny val/test
    covered subsets are too small to treat as decisive evidence
  - next decision point:
    - either run the same finite-activity aux on the full
      `results/mps_small_rescue/splits/` budget for a more realistic small test
    - or move to a stronger synthetic fallback such as ORCA-driven COSMO if the
      larger small-split run still shows no measurable test benefit

## 2026-04-25 - ORCA/openCOSMO-RS pilot path is executable locally; tiny crystal-probe pilot does not yet break compensation

- Added an ORCA/openCOSMO-RS finite-activity synthetic path and a generic
  compensation diagnostic path:
  - `src/tgnn_solv/chemistry/cosmors.py`
  - `scripts/data/build_cosmors_finite_activity_aux_stream.py`
  - `src/tgnn_solv/diagnostics/compensation.py`
  - `scripts/analysis/run_prediction_compensation_diagnostics.py`
  - `tests/test_cosmors_helpers.py`
  - `tests/test_compensation_diagnostics.py`
- Verification:
  - `python -m py_compile src/tgnn_solv/chemistry/cosmors.py src/tgnn_solv/diagnostics/compensation.py scripts/data/build_cosmors_finite_activity_aux_stream.py scripts/analysis/run_prediction_compensation_diagnostics.py tests/test_compensation_diagnostics.py tests/test_cosmors_helpers.py`
  - `PYTHONPATH=src KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_compensation_diagnostics.py tests/test_cosmors_helpers.py -q`
  - result: `4 passed`
- Environment/runtime facts established on this machine:
  - installed `openCOSMO-RS_py` into the maintained `tgnn-solv` conda env
  - local ORCA works for the COSMO self-pair route when
    `libmpi.40.dylib` is symlinked into the ORCA workdir
  - local ORCA does not ship a working `openCOSMORS` executable, but still
    writes usable `.solute.orcacosmo` artifacts before the final
    openCOSMO-RS handoff fails
  - the repo helper now treats that as an expected partial-success mode and
    continues from the produced `.orcacosmo`
- Smoke artifacts confirming the local path:
  - `results/cosmors_builder_smoke/`
  - `results/compensation_diagnostics_smoke/`
- Built a targeted crystal-known probe COSMO pilot subset:
  - source split: `results/crystal_known_probe/splits/train.csv`
  - subset manifest:
    - `results/crystal_known_probe/cosmors_pilot_subset/train_subset.csv`
    - `results/crystal_known_probe/cosmors_pilot_subset/subset_summary.json`
  - selected `9` observed states spanning `8` directed pairs and `9` unique
    molecules across the aspirin, hexane, and anthracene regimes
- Ran ORCA/openCOSMO-RS finite-activity generation on that subset:
  - outputs:
    - `results/crystal_known_probe/cosmors_pilot_subset/gamma2_aux_train.csv`
    - `results/crystal_known_probe/cosmors_pilot_subset/summary.json`
    - `results/crystal_known_probe/cosmors_pilot_subset/molecule_status.csv`
    - `results/crystal_known_probe/cosmors_pilot_subset/evaluation_failures.csv`
  - result:
    - state coverage `9 / 9`
    - pair coverage `8 / 8`
    - molecule failures `0`
    - evaluation failures `0`
  - observed runtime on the cached-subset pilot:
    - ORCA self-COSMO cache stage finished in about `4m44s`
- Trained a matched tiny TGNN pilot on the maintained crystal-known probe with
  the COSMO finite-activity aux stream:
  - config:
    - `configs/small_debug_gamma_inf_tail_weighted_aux05_crystal_probe.yaml`
  - checkpoint:
    - `checkpoints/crystal_known_probe/tgnn_gamma_inf_tail_weighted_aux05_crystal_probe_cosmors_pilot.pt`
  - logs:
    - `logs/crystal_known_probe_cosmors_pilot/tgnn_gamma_inf_tail_weighted_aux05_crystal_probe_cosmors_pilot/`
  - prediction artifacts:
    - `results/crystal_known_probe/cosmors_pilot/tgnn_test_predictions.csv`
    - `results/crystal_known_probe/cosmors_pilot/tgnn_test_summary.json`
    - `results/crystal_known_probe/cosmors_pilot/tgnn_test_predictions_oracle.csv`
    - `results/crystal_known_probe/cosmors_pilot/tgnn_test_summary_oracle.json`
    - `results/crystal_known_probe/cosmors_pilot/compensation_standard/summary.json`
    - `results/crystal_known_probe/cosmors_pilot/compensation_oracle/summary.json`
    - `results/crystal_known_probe/cosmors_pilot/comparison_vs_baseline.json`
- Tiny crystal-probe COSMO pilot results versus the maintained crystal-probe
  baseline:
  - standard test metrics:
    - MAE `0.601 -> 0.646`
    - RMSE `0.813 -> 0.733`
    - R2 `0.633 -> 0.702`
    - pred-std ratio `0.518 -> 0.697`
  - compensation markers:
    - `corr(delta_phi, delta_gamma): -0.876 -> -0.873`
    - mean `|delta_phi + delta_gamma|: 0.590 -> 0.637`
    - opposite-sign fraction: `1.000 -> 0.875`
  - forced-oracle reevaluation:
    - MAE `1.244 -> 1.219`
    - `corr(delta_phi, delta_gamma): 0.881 -> 0.879`
    - mean `|delta_phi + delta_gamma|: 1.242 -> 1.213`
- Accepted interpretation:
  - the ORCA/openCOSMO-RS fallback is now a real executable path in this
    environment, not just a speculative next step
  - even a very small exact-observed COSMO finite-activity stream can shift
    the model's test spread and RMSE/R2 on the crystal-known probe
  - however, this first pilot does not materially weaken the central
    compensation pattern:
    - `corr(delta_phi, delta_gamma)` barely moved
    - the compensation-sum metric became slightly worse in standard mode
    - forced-oracle collapse remains essentially intact
  - practical next step:
    - scale the COSMO aux stream to a larger exact-observed subset before
      drawing any stronger claim about compensation breaking

## 2026-04-25 - Full crystal-known train COSMO aux stream improves test fit and partially weakens compensation

- Scaled the ORCA/openCOSMO-RS path from the targeted pilot subset to the full
  maintained crystal-known probe train split:
  - command:
    - `PYTHONPATH=src KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python scripts/data/build_cosmors_finite_activity_aux_stream.py --input-csv results/crystal_known_probe/splits/train.csv --template-csv results/crystal_known_probe/splits/train.csv --output-csv results/crystal_known_probe/cosmors_full_train/gamma2_aux_train.csv --summary-json results/crystal_known_probe/cosmors_full_train/summary.json --molecule-status-csv results/crystal_known_probe/cosmors_full_train/molecule_status.csv --evaluation-failures-csv results/crystal_known_probe/cosmors_full_train/evaluation_failures.csv --cache-dir results/crystal_known_probe/cosmors_finite_activity_aux/cache --orca-bin /Users/nikitapolomosnov/Library/orca_6_1_1/orca --mpi-lib /opt/homebrew/lib/libmpi.40.dylib --orca-nprocs 2 --orca-maxcore-mb 1000`
  - outputs:
    - `results/crystal_known_probe/cosmors_full_train/gamma2_aux_train.csv`
    - `results/crystal_known_probe/cosmors_full_train/summary.json`
    - `results/crystal_known_probe/cosmors_full_train/molecule_status.csv`
    - `results/crystal_known_probe/cosmors_full_train/evaluation_failures.csv`
  - result:
    - state coverage `35 / 35`
    - pair coverage `34 / 34`
    - molecule coverage `34 / 34`
    - molecule failures `0`
    - evaluation failures `0`
  - observed runtime:
    - ORCA self-COSMO cache stage finished in about `21m18s`
- Trained a matched full crystal-known probe COSMO-sidecar run:
  - checkpoint:
    - `checkpoints/crystal_known_probe/tgnn_gamma_inf_tail_weighted_aux05_crystal_probe_cosmors_full.pt`
  - logs:
    - `logs/crystal_known_probe_cosmors_full/tgnn_gamma_inf_tail_weighted_aux05_crystal_probe_cosmors_full/`
  - activity-side loader settings:
    - `--idac-steps-per-epoch 5`
    - `--idac-batch-size 8`
- Exported prediction and compensation artifacts for the full COSMO run:
  - `results/crystal_known_probe/cosmors_full_train/tgnn_test_predictions.csv`
  - `results/crystal_known_probe/cosmors_full_train/tgnn_test_summary.json`
  - `results/crystal_known_probe/cosmors_full_train/tgnn_test_predictions_oracle.csv`
  - `results/crystal_known_probe/cosmors_full_train/tgnn_test_summary_oracle.json`
  - `results/crystal_known_probe/cosmors_full_train/compensation_standard/summary.json`
  - `results/crystal_known_probe/cosmors_full_train/compensation_oracle/summary.json`
  - `results/crystal_known_probe/cosmors_full_train/comparison_vs_baseline_and_pilot.json`
- Full-train COSMO run versus the maintained crystal-known baseline:
  - standard test metrics:
    - MAE `0.601 -> 0.592`
    - RMSE `0.813 -> 0.696`
    - R2 `0.633 -> 0.731`
    - pred-std ratio `0.518 -> 0.782`
  - standard compensation markers:
    - `corr(delta_phi, delta_gamma): -0.876 -> -0.833`
    - mean `|delta_phi + delta_gamma|: 0.590 -> 0.585`
    - opposite-sign fraction: `1.000 -> 0.750`
  - forced-oracle reevaluation:
    - MAE `1.244 -> 1.056`
    - RMSE `1.416 -> 1.200`
    - R2 `-0.113 -> 0.201`
    - pred-std ratio `0.074 -> 0.175`
    - `corr(delta_phi, delta_gamma): 0.881 -> 0.841`
    - mean `|delta_phi + delta_gamma|: 1.242 -> 1.048`
- Comparison against the earlier `9`-state COSMO pilot:
  - the pilot-subset run improved RMSE/R2 but did not materially change the
    compensation geometry
  - the full-train run is the first COSMO-side result that simultaneously:
    - improves standard test fit over the baseline
    - makes `corr(delta_phi, delta_gamma)` less negative by a visible margin
    - reduces the forced-oracle damage substantially instead of leaving it
      almost unchanged
- Accepted interpretation:
  - a fully exact-observed COSMO finite-activity sidecar on the tiny
    crystal-known probe does not eliminate compensation, but it now shows the
    first credible sign of weakening it
  - the effect is still partial:
    - standard `corr(delta_phi, delta_gamma)` remains strongly negative
    - the model is still not close to clean factorization
  - however, the forced-oracle improvement from `R2 < 0` to `R2 > 0` is a real
    qualitative change relative to both the baseline and the tiny pilot subset
  - practical next step:
    - repeat the same COSMO-side experiment on a larger small-split subset or a
      more realistic rescue split before treating this as robust evidence

## 2026-04-25 - More realistic mps_small_rescue heldout experiment gives mixed but informative COSMO-side signal

- Built a more realistic rescue-style split that keeps almost all of
  `results/mps_small_rescue/splits/train.csv` for supervised training while
  holding out the `8` crystal-known probe test pairs as a separate diagnostic
  set:
  - split files under `results/mps_small_rescue_crystal_holdout/splits/`
  - split summary artifact:
    - `results/mps_small_rescue_crystal_holdout/split_summary.json`
  - split summary:
    - `train_rows_original: 2629`
    - `train_rows_kept: 2621`
    - `train_rows_removed: 8`
    - `train_pairs_kept: 594`
    - `crystal_diagnostic_test_rows: 8`
  - key files:
    - `train.csv`
    - `val.csv`
    - `test.csv`
    - `crystal_diagnostic_test.csv`
    - `train_rows_removed_for_crystal_test.csv`
    - `cosmors_aux_source_train.csv`
    - `split_summary.json`
- Built a heldout-rescue COSMO finite-activity auxiliary stream from the
  remaining crystal-known train rows (`crystal_known_probe/train + val`,
  excluding the held-out test pairs):
  - command:
    - `PYTHONPATH=src KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python scripts/data/build_cosmors_finite_activity_aux_stream.py --input-csv results/mps_small_rescue_crystal_holdout/splits/cosmors_aux_source_train.csv --template-csv results/mps_small_rescue_crystal_holdout/splits/train.csv --output-csv results/mps_small_rescue_crystal_holdout/cosmors_aux/gamma2_aux_train.csv --summary-json results/mps_small_rescue_crystal_holdout/cosmors_aux/summary.json --molecule-status-csv results/mps_small_rescue_crystal_holdout/cosmors_aux/molecule_status.csv --evaluation-failures-csv results/mps_small_rescue_crystal_holdout/cosmors_aux/evaluation_failures.csv --cache-dir results/crystal_known_probe/cosmors_finite_activity_aux/cache --orca-bin /Users/nikitapolomosnov/Library/orca_6_1_1/orca --mpi-lib /opt/homebrew/lib/libmpi.40.dylib --orca-nprocs 2 --orca-maxcore-mb 1000`
  - result:
    - state coverage `42 / 42`
    - pair coverage `41 / 41`
    - molecule coverage `38 / 38`
    - molecule failures `0`
    - evaluation failures `0`
  - new artifacts:
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux/gamma2_aux_train.csv`
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux/summary.json`
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux/molecule_status.csv`
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux/evaluation_failures.csv`
- Trained matched heldout-rescue baselines with and without the COSMO sidecar:
  - baseline checkpoint:
    - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_baseline.pt`
  - COSMO-side checkpoint:
    - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_cosmors42.pt`
  - logs:
    - `logs/mps_small_rescue_crystal_holdout_baseline/tgnn_gamma_inf_tail_weighted_aux05_baseline/`
    - `logs/mps_small_rescue_crystal_holdout_cosmors42/tgnn_gamma_inf_tail_weighted_aux05_cosmors42/`
- Exported comparable prediction bundles for both runs on:
  - the main rescue test:
    - `baseline_main_test_summary.json`
    - `cosmors42_main_test_summary.json`
  - the held-out crystal diagnostic test:
    - `baseline_crystal_test_summary.json`
    - `baseline_crystal_test_summary_oracle.json`
    - `cosmors42_crystal_test_summary.json`
    - `cosmors42_crystal_test_summary_oracle.json`
  - compensation summaries:
    - `compensation_baseline_standard/summary.json`
    - `compensation_baseline_oracle/summary.json`
    - `compensation_cosmors42_standard/summary.json`
    - `compensation_cosmors42_oracle/summary.json`
  - combined comparison:
    - `results/mps_small_rescue_crystal_holdout/comparison_baseline_vs_cosmors42.json`
- Main rescue-test result:
  - COSMO sidecar made the main `mps_small_rescue` test slightly worse than the
    matched heldout baseline:
    - MAE `3.253 -> 3.323`
    - RMSE `4.090 -> 4.239`
    - R2 `0.213 -> 0.154`
- Held-out crystal-diagnostic result:
  - standard mode improved with the COSMO sidecar:
    - MAE `2.038 -> 1.656`
    - RMSE `2.289 -> 1.685`
    - R2 `-1.909 -> -0.576`
    - bias `-1.156 -> -0.534`
  - compensation summary on the held-out crystal test also improved in
    standard mode:
    - `corr(delta_phi, delta_gamma): 0.768 -> 0.533`
    - mean `|delta_phi + delta_gamma|: 2.039 -> 1.658`
    - opposite-sign fraction `0.875 -> 1.000`
- Forced-oracle behavior on the held-out crystal test did **not** improve in
  the same clean way:
  - baseline forced-oracle was better than baseline standard:
    - MAE `2.038 -> 1.378`
    - R2 `-1.909 -> -1.005`
  - COSMO-side forced-oracle was roughly flat/slightly worse versus its own
    standard mode:
    - MAE `1.656 -> 1.651`
    - R2 `-0.576 -> -1.339`
  - compensation under forced-oracle also remained poor:
    - `corr(delta_phi, delta_gamma): 0.775 -> 0.590` for baseline vs COSMO
      forced-oracle mode
    - mean `|delta_phi + delta_gamma|: 1.369 -> 1.634`
- Accepted interpretation:
  - in this more realistic rescue-style setup, COSMO-side supervision helps the
    held-out crystal-diagnostic standard predictions, but that gain does not
    transfer to the main rescue test
  - unlike the tiny full crystal-known run, the heldout-rescue COSMO result
    does **not** produce a cleaner forced-oracle story
  - the likely picture is:
    - COSMO-side supervision is improving some pair/activity structure on the
      held-out crystal rows
    - but that improvement is not yet aligned with the broader rescue target
      distribution, and crystal/activity factorization is still not robust
- practical next step:
  - do **not** expand the ORCA/COSMO route further yet
  - first weaken the sidecar on this same heldout-rescue protocol:
    - reduce `idac_steps_per_epoch`
    - reduce `gamma2_weight`
  - target criterion:
    - keep the crystal-holdout standard-mode gain while removing or shrinking
      the main-test degradation
- documentation sync:
  - updated `reports/supervisor_report_readable.tex` to include this mixed
    heldout-rescue COSMO result and the weaker-sidecar next step
  - rebuilt `reports/supervisor_report_readable.pdf` successfully on
    `2026-04-25`

## 2026-04-25 - Heldout-rescue COSMO weakening ablation: lower `gamma2_weight` works better than lower aux frequency

- Built a lighter heldout-rescue COSMO finite-activity auxiliary stream by
  reusing the existing ORCA cache but lowering the row weight:
  - command:
    - `KMP_DUPLICATE_LIB_OK=TRUE /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python scripts/data/build_cosmors_finite_activity_aux_stream.py --input-csv results/mps_small_rescue_crystal_holdout/splits/cosmors_aux_source_train.csv --template-csv results/mps_small_rescue_crystal_holdout/splits/train.csv --output-csv results/mps_small_rescue_crystal_holdout/cosmors_aux_w005/gamma2_aux_train.csv --summary-json results/mps_small_rescue_crystal_holdout/cosmors_aux_w005/summary.json --molecule-status-csv results/mps_small_rescue_crystal_holdout/cosmors_aux_w005/molecule_status.csv --evaluation-failures-csv results/mps_small_rescue_crystal_holdout/cosmors_aux_w005/evaluation_failures.csv --cache-dir results/crystal_known_probe/cosmors_finite_activity_aux/cache --orca-bin /Users/nikitapolomosnov/Library/orca_6_1_1/orca --mpi-lib /opt/homebrew/lib/libmpi.40.dylib --orca-nprocs 2 --orca-maxcore-mb 1000 --gamma2-weight 0.05`
  - result:
    - state coverage `42 / 42`
    - pair coverage `41 / 41`
    - molecule coverage `38 / 38`
    - molecule failures `0`
    - evaluation failures `0`
  - new artifacts:
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux_w005/gamma2_aux_train.csv`
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux_w005/summary.json`
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux_w005/molecule_status.csv`
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux_w005/evaluation_failures.csv`
- Ran two weakening ablations on the same heldout-rescue protocol:
  - lower aux frequency only:
    - checkpoint:
      - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_cosmors42_steps2.pt`
    - logs:
      - `logs/mps_small_rescue_crystal_holdout_cosmors42_steps2/tgnn_gamma_inf_tail_weighted_aux05_cosmors42_steps2/`
    - exported artifacts:
      - `results/mps_small_rescue_crystal_holdout/cosmors42_steps2_main_test_summary.json`
      - `results/mps_small_rescue_crystal_holdout/cosmors42_steps2_crystal_test_summary.json`
      - `results/mps_small_rescue_crystal_holdout/cosmors42_steps2_crystal_test_summary_oracle.json`
      - `results/mps_small_rescue_crystal_holdout/compensation_cosmors42_steps2_standard/summary.json`
      - `results/mps_small_rescue_crystal_holdout/compensation_cosmors42_steps2_oracle/summary.json`
  - lower pseudo-label strength only:
    - checkpoint:
      - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_cosmors42_w005.pt`
    - logs:
      - `logs/mps_small_rescue_crystal_holdout_cosmors42_w005/tgnn_gamma_inf_tail_weighted_aux05_cosmors42_w005/`
    - exported artifacts:
      - `results/mps_small_rescue_crystal_holdout/cosmors42_w005_main_test_summary.json`
      - `results/mps_small_rescue_crystal_holdout/cosmors42_w005_crystal_test_summary.json`
      - `results/mps_small_rescue_crystal_holdout/cosmors42_w005_crystal_test_summary_oracle.json`
      - `results/mps_small_rescue_crystal_holdout/compensation_cosmors42_w005_standard/summary.json`
      - `results/mps_small_rescue_crystal_holdout/compensation_cosmors42_w005_oracle/summary.json`
  - combined comparison:
    - `results/mps_small_rescue_crystal_holdout/comparison_baseline_vs_cosmors42_vs_steps2_vs_w005.json`
- Result for lowering `idac_steps_per_epoch` only (`steps=2`) was negative:
  - main rescue test got worse than both baseline and the original `cosmors42`
    sidecar:
    - MAE `3.253 -> 3.411`
    - RMSE `4.090 -> 4.350`
    - R2 `0.213 -> 0.109`
  - crystal holdout standard improved further:
    - MAE `2.038 -> 1.537`
    - RMSE `2.289 -> 1.733`
    - R2 `-1.909 -> -0.667`
  - but forced-oracle collapsed badly:
    - MAE `1.378 -> 2.113`
    - RMSE `1.901 -> 2.562`
    - R2 `-1.005 -> -2.643`
  - compensation also stayed in the over-compensated regime:
    - standard `corr(delta_phi, delta_gamma)=0.526`,
      mean `|delta_phi + delta_gamma|=1.537`
    - oracle `corr(delta_phi, delta_gamma)=0.601`,
      mean `|delta_phi + delta_gamma|=2.112`
- Result for lowering `gamma2_weight` to `0.05` while keeping
  `idac_steps_per_epoch=5` was materially better:
  - main rescue test improved over the matched heldout baseline and over all
    previously tried COSMO variants on this protocol:
    - MAE `3.253 -> 3.190`
    - RMSE `4.090 -> 4.057`
    - R2 `0.213 -> 0.225`
  - crystal holdout standard kept a real gain over baseline, although smaller
    than the original stronger sidecar:
    - MAE `2.038 -> 1.817`
    - RMSE `2.289 -> 2.004`
    - R2 `-1.909 -> -1.229`
  - forced-oracle behavior moved back close to the baseline-oracle regime
    instead of staying degraded like `cosmors42` / `steps=2`:
    - MAE `1.378 -> 1.410`
    - RMSE `1.901 -> 1.927`
    - R2 `-1.005 -> -1.062`
  - compensation also became much closer to the baseline pattern:
    - standard `corr(delta_phi, delta_gamma)=0.790`,
      mean `|delta_phi + delta_gamma|=1.814`,
      opposite-sign fraction `0.875`
    - oracle `corr(delta_phi, delta_gamma)=0.797`,
      mean `|delta_phi + delta_gamma|=1.409`,
      opposite-sign fraction `0.875`
- Accepted interpretation:
  - on this heldout-rescue setup, lowering COSMO pseudo-label strength is a
    better weakening lever than lowering the sidecar update frequency
  - `gamma2_weight=0.05` is the first COSMO-side variant here that keeps some
    crystal-holdout standard gain while also removing the main-test regression
    and avoiding the strong forced-oracle degradation seen in the heavier
    sidecar runs
  - the trade-off is clear:
    - stronger COSMO sidecar gives a larger crystal-standard gain but hurts
      transfer and oracle cleanliness
    - lighter COSMO sidecar gives a smaller crystal-standard gain but restores
      main-test behavior and a cleaner oracle picture
- Practical next step:
  - keep ORCA coverage fixed for now
  - sweep locally around the promising weaker-sidecar regime first:
    - `gamma2_weight` near `0.05 - 0.10`
    - optionally a mild `idac_steps_per_epoch` reduction such as `3 - 4`, but
      avoid `2` as the default next candidate

## 2026-04-25 - Heldout-rescue COSMO `gamma2_weight=0.10` restores more crystal gain, but loses the `w005` main/oracle stability

- Ran the midpoint heldout-rescue COSMO sidecar ablation with
  `gamma2_weight=0.10` and unchanged `idac_steps_per_epoch=5`:
  - auxiliary stream:
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux_w010/gamma2_aux_train.csv`
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux_w010/summary.json`
  - checkpoint:
    - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_cosmors42_w010.pt`
  - logs:
    - `logs/mps_small_rescue_crystal_holdout_cosmors42_w010/tgnn_gamma_inf_tail_weighted_aux05_cosmors42_w010/`
  - exported artifacts:
    - `results/mps_small_rescue_crystal_holdout/cosmors42_w010_main_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/cosmors42_w010_crystal_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/cosmors42_w010_crystal_test_summary_oracle.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_cosmors42_w010_standard/summary.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_cosmors42_w010_oracle/summary.json`
  - refreshed comparison bundle:
    - `results/mps_small_rescue_crystal_holdout/comparison_baseline_vs_cosmors42_vs_steps2_vs_w005_vs_w010.json`
- Main rescue-test result:
  - `w010` is worse than baseline and worse than `w005`:
    - MAE `3.253 -> 3.329` vs baseline
    - RMSE `4.090 -> 4.257`
    - R2 `0.213 -> 0.147`
  - relative to `w005`, this is a clear regression:
    - MAE `3.190 -> 3.329`
    - RMSE `4.057 -> 4.257`
    - R2 `0.225 -> 0.147`
- Held-out crystal-diagnostic result:
  - standard mode did improve over baseline and also improved over `w005`:
    - baseline `MAE 2.038`, `RMSE 2.289`, `R2 -1.909`
    - `w005` `MAE 1.817`, `RMSE 2.004`, `R2 -1.229`
    - `w010` `MAE 1.713`, `RMSE 1.819`, `R2 -0.838`
  - forced-oracle moved back into the undesirable regime:
    - baseline oracle: `MAE 1.378`, `RMSE 1.901`, `R2 -1.005`
    - `w005` oracle: `MAE 1.410`, `RMSE 1.927`, `R2 -1.062`
    - `w010` oracle: `MAE 1.711`, `RMSE 1.936`, `R2 -1.080`
- Compensation result:
  - standard compensation became much less clean than both baseline and `w005`:
    - baseline `corr(delta_phi, delta_gamma)=0.768`
    - `w005` `corr=0.790`
    - `w010` `corr=0.226`
    - mean `|delta_phi + delta_gamma|` still improved vs baseline
      (`2.039 -> 1.715`), but the decorrelation signal is now poor
  - oracle compensation also degraded:
    - baseline oracle `corr=0.775`, mean `|delta_phi + delta_gamma|=1.369`
    - `w005` oracle `corr=0.797`, mean `1.409`
    - `w010` oracle `corr=0.329`, mean `1.703`
- Accepted interpretation:
  - increasing the COSMO pseudo-label weight from `0.05` to `0.10` buys more
    crystal-standard gain, but it already loses the main-test and oracle
    stability that made `w005` the first usable weakening regime
  - among tested heldout-rescue COSMO weights, `w005` remains the best overall
    compromise
  - if another local interpolation is worth trying, it should be closer to
    `0.05` than to `0.10` (for example `0.075`), not heavier than `0.10`

## 2026-04-26 - Heldout-rescue exact joint-label `ln_gamma_2` auxiliary stream gives the right structural signal, but `w100` is too strong

- Added a reproducible builder for exact joint crystal/activity supervision
  rather than relying only on synthetic UNIFAC/COSMO pseudo-labels:
  - `scripts/data/build_exact_joint_gamma2_aux_stream.py`
  - formula used per jointly labeled row:
    - `Phi_true = (dH_fus / R) * (1/T - 1/T_m)`
    - `ln_gamma_2 = -ln_x2 - Phi_true`
  - output rows are aux-only and match the existing
    `scripts/train.py --idac-train-data` contract
- Built the first heldout-rescue exact-joint auxiliary stream from the current
  crystal-known train rows:
  - `results/mps_small_rescue_crystal_holdout/exact_joint_aux_w100/gamma2_aux_train.csv`
  - `results/mps_small_rescue_crystal_holdout/exact_joint_aux_w100/summary.json`
  - coverage matches the rescue crystal-known train support exactly:
    - `42` rows
    - `41` unique pairs
    - `3` solutes
    - `36` solvents
- Trained the first oversampled exact-joint rescue run with unchanged aux
  schedule and strong per-row weight:
  - checkpoint:
    - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_w100.pt`
  - logs:
    - `logs/mps_small_rescue_crystal_holdout_exactjoint42_w100/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_w100/`
  - exported artifacts:
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_w100_main_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_w100_crystal_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_w100_crystal_test_summary_oracle.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_w100_standard/summary.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_w100_oracle/summary.json`
  - compact comparison bundle:
    - `results/mps_small_rescue_crystal_holdout/comparison_baseline_vs_w005_vs_exactjoint42_w100.json`
- Main rescue-test result:
  - the exact-joint run stayed near the matched baseline on the main test:
    - baseline `MAE 3.253`, `RMSE 4.090`, `R2 0.213`
    - exact-joint `MAE 3.249`, `RMSE 4.107`, `R2 0.206`
  - relative to heavy COSMO regimes, this avoids the clear main-test regression
  - relative to `cosmors42_w005`, it is still slightly worse on the main test:
    - `w005` `MAE 3.190`, `RMSE 4.057`, `R2 0.225`
- Held-out crystal-diagnostic result:
  - standard mode is not yet a win:
    - baseline `MAE 2.038`, `RMSE 2.289`, `R2 -1.909`
    - exact-joint `MAE 2.161`, `RMSE 2.312`, `R2 -1.968`
  - but forced-oracle improved materially relative to its own standard mode:
    - standard `MAE 2.161`, `RMSE 2.312`, `R2 -1.968`
    - oracle `MAE 1.510`, `RMSE 2.084`, `R2 -1.411`
  - this is still worse than baseline-oracle / `w005` oracle, but unlike the
    failed naive decorrelation runs it restores a clear "oracle helps" signal
- Compensation result:
  - standard compensation stayed reasonably clean:
    - `corr(delta_phi, delta_gamma)=0.661`
    - mean `|delta_phi + delta_gamma|=2.167`
    - opposite-sign fraction `1.000`
  - oracle compensation also stayed coherent and improved in magnitude:
    - `corr(delta_phi, delta_gamma)=0.677`
    - mean `|delta_phi + delta_gamma|=1.490`
    - opposite-sign fraction `1.000`
  - compared with `w010`, this is much cleaner; compared with baseline / `w005`,
    the correlation is somewhat worse but still in the same qualitative regime
- Accepted interpretation:
  - dedicated exact joint-label activity supervision is a more meaningful
    compensation lever than naive batchwise `decorr`, because it gives the
    activity branch an exact target on the rows where the decomposition is
    actually identifiable
  - the first strong setting here (`gamma2_weight=1.0` in the aux stream) is
    too aggressive: it keeps the main test under control and revives the oracle
    gap, but it over-regularizes crystal-standard predictions
  - therefore the next compensation-focused sweep should move to weaker
    exact-joint weights, not stronger COSMO weights:
    - first candidates: `gamma2_weight` around `0.10 - 0.50`
    - keep the dedicated aux stream / oversampling structure
    - optionally compare pure exact-joint against `exact-joint + cosmors42_w005`
  - the larger structural path is now clearer:
    - keep `modified-UNIFAC` as a cheap weak prior only
    - keep weak COSMO (`w005`-like) as an optional synthetic regularizer
    - treat exact joint-label `ln_gamma_2` supervision as the main route to
      reducing compensation
    - if this route works at lower weight, expand it using the open crystal
      sidecar rather than more ORCA coverage, because that sidecar can raise
      full-corpus joint-label support from `1080` to `14401` rows and
      `146` to `1497` unique supervised pairs

## 2026-04-26 - Constant aux `gamma2_weight` was a no-op under normalized weighted means; corrected exact-joint `w025` becomes the first valid compensation-weight reference

- Found a trainer/loss contract bug in the finite-activity auxiliary path:
  - `loss.py` computes `gamma_2` via normalized `weighted_mean(...)`
  - aux builders (`COSMO`, `UNIFAC`, exact-joint) were writing a single
    constant `gamma2_weight` across the whole aux CSV
  - therefore a constant `gamma2_weight=c` canceled out exactly and did **not**
    scale the aux loss magnitude at all
  - implication:
    - earlier heldout-rescue `gamma2_weight` sweeps should not be interpreted as
      valid weight-controlled evidence until rerun under the corrected trainer
- Applied a targeted trainer-side fix instead of changing global loss semantics:
  - `src/tgnn_solv/trainer.py`
    - new helper `_idac_aux_component_scale(...)`
    - aux-only `gamma_weight` / `gamma2_weight` are now folded into the
      component loss weights inside `_train_idac_aux_batch(...)`
    - relative per-row weighting inside a batch is still handled by the
      normalized weighted mean, but constant aux CSV weights now change the
      total sidecar strength as originally intended
  - regression coverage:
    - `tests/test_loss.py` gained checks for
      `_idac_aux_component_scale(...)`
  - environment note:
    - `py_compile` passed
    - direct import sanity checks passed in the `tgnn-solv` env
    - `pytest` under that env aborted during import before reaching the new
      tests, so full test execution remains pending
- Ran the first corrected exact-joint heldout-rescue reference at
  `gamma2_weight=0.25`:
  - checkpoint:
    - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_w025_fixscale.pt`
  - logs:
    - `logs/mps_small_rescue_crystal_holdout_exactjoint42_w025_fixscale/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_w025_fixscale/`
  - exported artifacts:
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_w025_fixscale_main_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_w025_fixscale_crystal_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_w025_fixscale_crystal_test_summary_oracle.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_w025_fixscale_standard/summary.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_w025_fixscale_oracle/summary.json`
  - compact comparison bundle:
    - `results/mps_small_rescue_crystal_holdout/comparison_baseline_vs_w005_vs_exactjoint42_w025_fixscale.json`
- Corrected exact-joint `w025` result:
  - main rescue test is now clearly competitive:
    - baseline `MAE 3.253`, `RMSE 4.090`, `R2 0.213`
    - exact-joint `w025` `MAE 3.221`, `RMSE 4.072`, `R2 0.219`
    - `cosmors42_w005` still remains slightly better on the main test
      (`MAE 3.190`, `RMSE 4.057`, `R2 0.225`)
  - crystal standard is still poor:
    - baseline `MAE 2.038`, `RMSE 2.289`, `R2 -1.909`
    - exact-joint `w025` `MAE 2.223`, `RMSE 2.403`, `R2 -2.206`
  - but forced-oracle becomes the cleanest exact-joint result so far:
    - exact-joint `w025` oracle `MAE 1.340`, `RMSE 1.938`, `R2 -1.085`
    - this beats the earlier corrected-free exact-joint `w100` oracle
      (`1.510`, `2.084`, `-1.411`)
    - it is also slightly better than the baseline oracle on MAE
      (`1.378 -> 1.340`) and materially cleaner than `cosmors42_w005` on
      compensation magnitude
- Compensation result for corrected exact-joint `w025`:
  - standard:
    - `corr(delta_phi, delta_gamma)=0.636`
    - mean `|delta_phi + delta_gamma|=2.232`
    - opposite-sign fraction `0.750`
  - oracle:
    - `corr(delta_phi, delta_gamma)=0.645`
    - mean `|delta_phi + delta_gamma|=1.325`
    - opposite-sign fraction `0.750`
  - interpretation:
    - exact-joint `w025` is now the strongest evidence so far that the
      compensation problem is better attacked by exact joint-label activity
      supervision than by stronger synthetic sidecars
    - its current failure mode is not main-test transfer or oracle collapse;
      it is specifically degraded crystal-standard prediction quality
- Accepted next step:
  - keep the corrected trainer
  - continue the exact-joint sweep downward, with `gamma2_weight=0.10` as the
    next candidate
  - do **not** rely on the older `w005/w010/w100` sidecar weight conclusions as
    clean weight evidence until those runs are rerun under the corrected
    aux-weight scaling semantics

## 2026-04-26 - Corrected exact-joint `w010` failed; mixed exact-joint + weak COSMO kept the oracle signal but did not repair crystal-standard predictions

- Ran the corrected heldout-rescue exact-joint reference at `gamma2_weight=0.10`:
  - checkpoint:
    - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_w010_fixscale.pt`
  - logs:
    - `logs/mps_small_rescue_crystal_holdout_exactjoint42_w010_fixscale/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_w010_fixscale/`
  - exported artifacts:
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_w010_fixscale_main_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_w010_fixscale_crystal_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_w010_fixscale_crystal_test_summary_oracle.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_w010_fixscale_standard/summary.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_w010_fixscale_oracle/summary.json`
- Corrected exact-joint `w010` result:
  - the weaker exact-joint run is not a useful compromise:
    - main rescue test regressed below baseline:
      - baseline `MAE 3.253`, `RMSE 4.090`, `R2 0.213`
      - exact-joint `w010` `MAE 3.394`, `RMSE 4.281`, `R2 0.138`
    - crystal standard remained poor:
      - exact-joint `w010` `MAE 2.117`, `RMSE 2.172`, `R2 -1.619`
    - forced-oracle became actively unhealthy relative to its own standard mode:
      - standard `MAE 2.117`, `RMSE 2.172`, `R2 -1.619`
      - oracle `MAE 1.949`, `RMSE 2.408`, `R2 -2.218`
  - compensation also degraded in both modes:
    - standard `corr(delta_phi, delta_gamma)=0.434`,
      mean `|delta_phi + delta_gamma|=2.128`
    - oracle `corr(delta_phi, delta_gamma)=0.498`,
      mean `|delta_phi + delta_gamma|=1.927`
  - accepted interpretation:
    - simply sweeping the corrected exact-joint weight downward does **not**
      repair the crystal-standard failure mode
    - the useful exact-joint region is therefore not "as weak as possible";
      `w010` is already too weak to preserve the compensation benefit

- Built a mixed exact-joint + weak COSMO auxiliary stream on the exact same
  `42` crystal-known states / `41` pairs:
  - input streams:
    - `results/mps_small_rescue_crystal_holdout/exact_joint_aux_w025/gamma2_aux_train.csv`
    - `results/mps_small_rescue_crystal_holdout/cosmors_aux_w005/gamma2_aux_train.csv`
  - merged aux bundle:
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_plus_cosmors42_w005_fixscale_aux/gamma2_aux_train.csv`
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_plus_cosmors42_w005_fixscale_aux/summary.json`
  - summary:
    - `84` aux rows total
    - still only `42` unique states because the two sidecars overlap exactly
    - each supervised state now carries one exact-joint target (`0.25`) and one
      weak COSMO target (`0.05`)
- Ran the mixed heldout-rescue experiment:
  - checkpoint:
    - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_plus_cosmors42_w005_fixscale.pt`
  - logs:
    - `logs/mps_small_rescue_crystal_holdout_exactjoint42_plus_cosmors42_w005_fixscale/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_plus_cosmors42_w005_fixscale/`
  - exported artifacts:
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_plus_cosmors42_w005_fixscale_main_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_plus_cosmors42_w005_fixscale_crystal_test_summary.json`
    - `results/mps_small_rescue_crystal_holdout/exactjoint42_plus_cosmors42_w005_fixscale_crystal_test_summary_oracle.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_plus_cosmors42_w005_fixscale_standard/summary.json`
    - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_plus_cosmors42_w005_fixscale_oracle/summary.json`
  - compact comparison bundle:
    - `results/mps_small_rescue_crystal_holdout/comparison_baseline_vs_w005_vs_exactjoint42_w025_fixscale_vs_w010_fixscale_vs_exactjoint42_plus_cosmors42_w005_fixscale.json`
- Mixed exact-joint + weak COSMO result:
  - main rescue test landed between baseline and the failed `w010`, but did not
    beat the best references:
    - exact-joint + COSMO `MAE 3.311`, `RMSE 4.141`, `R2 0.193`
    - worse than baseline (`3.253`, `4.090`, `0.213`)
    - worse than exact-joint `w025` (`3.221`, `4.072`, `0.219`)
    - worse than `cosmors42_w005` (`3.190`, `4.057`, `0.225`)
  - crystal standard also stayed poor:
    - `MAE 2.275`, `RMSE 2.490`, `R2 -2.442`
  - but oracle remained the strongest seen so far on MAE and compensation
    magnitude:
    - oracle `MAE 1.322`, `RMSE 1.930`, `R2 -1.069`
    - oracle compensation `corr(delta_phi, delta_gamma)=0.661`,
      mean `|delta_phi + delta_gamma|=1.311`
    - this slightly improves over exact-joint `w025` on oracle MAE
      (`1.340 -> 1.322`) and oracle compensation magnitude (`1.325 -> 1.311`)
  - accepted interpretation:
    - adding a weak COSMO prior on top of exact-joint does **not** solve the
      crystal-standard problem in the current tiny `42`-state regime
    - however it preserves, and slightly strengthens, the compensation-focused
      oracle story, so the exact-joint route still looks structurally correct

- Updated compensation-direction conclusion:
  - the current main lever against compensation is still exact joint-label
    `ln_gamma_2` supervision, not stronger synthetic sidecars
  - local scalar weight sweep is largely exhausted:
    - `w010` is too weak
    - `w025` is the best pure exact-joint compromise so far
    - `w025 + weak COSMO` improves oracle diagnostics slightly but still fails
      on crystal-standard transfer
  - therefore the next *meaningful* correction should change supervision
    structure rather than keep nudging local weights:
    - expand exact joint-label coverage via the open-crystal sidecar
    - optionally keep weak COSMO only as a background prior on top
    - stop spending cycles on lower corrected exact-joint weights unless a new
      scheduling idea is introduced

## 2026-04-26 - Exact-joint interpretation tightened; next priority is two-stage crystal/activity training rather than more local weight nudging

- Clarified metric scope for the current heldout-rescue discussion:
  - do **not** mix the following bundles in narrative comparisons:
    - small rescue weighted DirectGNN reference:
      - `results/mps_small_rescue/direct_weighted_predictions.summary.json`
      - `MAE 3.053`
    - older crystal-known oracle probe:
      - `results/crystal_known_probe_compensation/` and related report text
      - forced-oracle `MAE` around `1.242`
    - current exact-joint heldout-rescue bundle:
      - `results/mps_small_rescue_crystal_holdout/comparison_baseline_vs_w005_vs_exactjoint42_w100.json`
      - `results/mps_small_rescue_crystal_holdout/comparison_baseline_vs_w005_vs_exactjoint42_w025_fixscale_vs_w010_fixscale_vs_exactjoint42_plus_cosmors42_w005_fixscale.json`
      - baseline for this bundle is:
        - main `MAE 3.253`
        - crystal-standard `MAE 2.038`
        - crystal-oracle `MAE 1.378`
- Synthesis from the current heldout-rescue exact-joint bundle:
  - exact-joint remains the only tested supervision that consistently improves
    the oracle-side compensation story without collapsing the main rescue test:
    - `w100`:
      - main `MAE 3.249`
      - crystal-standard `MAE 2.161`
      - crystal-oracle `MAE 1.510`
      - oracle mean `|delta_phi + delta_gamma| = 1.490`
    - corrected `w025`:
      - main `MAE 3.221`
      - crystal-standard `MAE 2.223`
      - crystal-oracle `MAE 1.340`
      - oracle mean `|delta_phi + delta_gamma| = 1.325`
    - corrected `w025 + weak COSMO`:
      - main `MAE 3.311`
      - crystal-standard `MAE 2.275`
      - crystal-oracle `MAE 1.322`
      - oracle mean `|delta_phi + delta_gamma| = 1.311`
  - across all of these runs, crystal-standard remains worse than the heldout
    baseline (`2.038`), even when oracle diagnostics improve
- Accepted interpretation update:
  - this is now treated primarily as a target-consistency problem, not a simple
    scalar-weight-tuning problem
  - exact-joint builds the activity target from experimental crystal
    parameters, while the standard SLE path still uses the model's predicted
    crystal branch
  - when predicted `Phi(T)` is wrong, the optimizer cannot simultaneously make
    `ln(x2)`, `ln(gamma_2)`, and crystal-standard predictions correct, so the
    improved oracle decomposition is paid for by degraded crystal-standard
    performance
- Updated next-step priority:
  - the next meaningful experiment should change training structure, not just
    nudge `gamma2_weight`
  - preferred sequence:
    - pretrain / fit the crystal branch on rows with known `T_m` and
      `dH_fus`
    - freeze the crystal branch
    - train the activity branch with exact-joint supervision against the frozen
      predicted `Phi(T)`
    - optionally run `1-2` short coordinate-descent unfreeze/refit passes
  - a narrow control around `w050` can remain optional, but it is now a
    secondary sanity check rather than the main compensation experiment

## 2026-04-26 - Added branch-aware `coordinate_descent` training mode for crystal/activity decoupling

- Implemented a new config / CLI control for branch-aware training:
  - `src/tgnn_solv/config.py`
    - new `branch_training_mode` field
  - `scripts/train.py`
    - new `--branch-training-mode` override
- The supported non-default mode is currently `coordinate_descent`, which
  repurposes the maintained 3-phase trainer as one explicit
  `crystal -> activity -> crystal` cycle:
  - Phase 1:
    - freezes interaction / activity modules
    - keeps only crystal / pre-interaction property losses active
  - Phase 2:
    - freezes the crystal / shared pre-interaction stack
    - forces `detach_crystal_from_encoder=true`
    - forces `detach_crystal_params_in_sle=true`
    - keeps only activity / solubility-side losses active
  - Phase 3:
    - freezes interaction / activity modules again
    - keeps `sol + crystal/property` losses active so the crystal branch can
      refit against a fixed activity side
- Implementation details are in:
  - `src/tgnn_solv/trainer.py`
    - phase-aware branch freezing helpers
    - branch-mode loss allowlists
    - correction-freeze scheduling that no longer unfreezes correction inside
      crystal phases of the coordinate-descent regime
- Regression coverage added:
  - `tests/test_config.py`
  - `tests/test_trainer_resume.py`
- Verified on `2026-04-26` with:
  - `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_config.py tests/test_trainer_resume.py -q`
  - `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src /Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/test_loss.py -q`
- Current caveat:
  - this is one coordinate-descent cycle inside the existing curriculum, not
    yet a multi-cycle outer-loop experiment runner

## 2026-04-26 - First end-to-end `coordinate_descent` smoke run completed on exact-joint crystal-holdout split

- Completed a full smoke run with the new branch-aware training mode:
  - command shape:
    - `scripts/train.py`
    - `configs/small_debug_gamma_inf_stopgrad.yaml`
    - `results/mps_small_rescue_crystal_holdout/splits/{train,val,test}.csv`
    - `results/mps_small_rescue_crystal_holdout/exact_joint_aux_w025/gamma2_aux_train.csv`
    - `--branch-training-mode coordinate_descent`
    - overridden to `epochs 1/1/1`, `batch_size 64`, `device mps`
  - artifacts:
    - `checkpoints/coord_descent_smoke_111.pt`
    - `logs/coord_descent_smoke_exactjoint_w025_111/summary.json`
    - `logs/coord_descent_smoke_exactjoint_w025_111/test_metrics.json`
- Smoke-run result:
  - finished successfully end-to-end in about `210 s`
  - test metrics:
    - `MAE 3.679`
    - `RMSE 4.611`
    - `R^2 -0.001`
- Structural verification from the live run:
  - Phase 1 active losses were crystal-only:
    - `T_m`, `dH`, `hansen`
  - Phase 2 active losses switched to activity / solubility:
    - `sol`, `gamma_inf`, `gamma_2`, pair-temperature terms, residual /
      direct / preference regularizers
  - Phase 3 active losses switched back to crystal refit:
    - `sol`, `T_m`, `dH`, `hansen`
  - this confirms the new mode is not just a config alias; the trainer really
    remaps objectives by phase during an actual run
- Practical runtime note:
  - an earlier `1/4/1` smoke on the same split was manually interrupted after
    confirming the Phase 2 transition because MPS throughput at `batch_size 16`
    was too slow for a quick validation pass
  - for laptop smoke tests, `batch_size 64` and tiny `1/1/1` budgets are a
    much better sanity-check regime
- Interpretation:
  - this run proves the new training path is operational and stable on the
    exact-joint sidecar setup
  - the metric value itself should **not** be over-interpreted because the
    budget is intentionally tiny and the config is a smoke/debug config rather
    than the maintained tuned rescue setting

## 2026-04-26 - Fixed final test-evaluation phase bug in `scripts/train.py`

- Runtime issue discovered during the first `coordinate_descent` smoke run:
  - the final test evaluation path in `scripts/train.py` was hardcoded to
    `trainer.validate(..., phase=2)`
  - this is wrong once the restored best model comes from Phase 3, because the
    reported `val_loss` then uses Phase 2 loss weights instead of the phase
    that actually produced the checkpoint
- Fix:
  - `scripts/train.py` now resolves the evaluation phase from
    `trainer.best_phase`, falling back to Phase 3 when Phase 3 exists and to
    Phase 2 otherwise
  - the script also prints the chosen evaluation phase before test validation
- Verification:
  - reran the completed checkpoint path via:
    - `--resume checkpoints/coord_descent_smoke_111.pt`
  - new artifacts:
    - `checkpoints/coord_descent_smoke_111_retest.pt`
    - `logs/coord_descent_smoke_exactjoint_w025_111_retest/test_metrics.json`
  - the script now logs `Using validation phase weights from Phase 3`
  - on the same restored checkpoint:
    - `MAE/RMSE/R^2` stayed the same
    - reported `val_loss` changed from about `4.286` to `3.899`, which confirms
      the bug was in the evaluation weighting, not in the predictions

## 2026-04-26 - Ran the analogous heldout-rescue `1/4/1` `coordinate_descent` reference for exact-joint `w025`

- Reused the same small heldout-rescue protocol family as the corrected
  `exactjoint42_w025_fixscale` reference:
  - config:
    - `configs/small_debug_gamma_inf_tail_weighted_aux05.yaml`
  - data:
    - `results/mps_small_rescue_crystal_holdout/splits/{train,val,test}.csv`
    - `results/mps_small_rescue_crystal_holdout/splits/crystal_diagnostic_test.csv`
    - exact-joint aux stream:
      - `results/mps_small_rescue_crystal_holdout/exact_joint_aux_w025/gamma2_aux_train.csv`
  - run controls:
    - `epochs 1/4/1`
    - `idac_steps_per_epoch=5`
    - `batch_size=16`
    - `--branch-training-mode coordinate_descent`
    - `device mps`
- Training artifacts:
  - checkpoint:
    - `checkpoints/mps_small_rescue_crystal_holdout/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_w025_fixscale_coordinate_descent.pt`
  - logs:
    - `logs/mps_small_rescue_crystal_holdout_exactjoint42_w025_fixscale_coordinate_descent/tgnn_gamma_inf_tail_weighted_aux05_exactjoint42_w025_fixscale_coordinate_descent/`
  - runtime:
    - completed successfully in about `775.4 s`
- Exported evaluation artifacts:
  - `results/mps_small_rescue_crystal_holdout/exactjoint42_w025_fixscale_coordinate_descent_main_test_summary.json`
  - `results/mps_small_rescue_crystal_holdout/exactjoint42_w025_fixscale_coordinate_descent_crystal_test_summary.json`
  - `results/mps_small_rescue_crystal_holdout/exactjoint42_w025_fixscale_coordinate_descent_crystal_test_summary_oracle.json`
  - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_w025_fixscale_coordinate_descent_standard/summary.json`
  - `results/mps_small_rescue_crystal_holdout/compensation_exactjoint42_w025_fixscale_coordinate_descent_oracle/summary.json`
  - compact comparison bundle:
    - `results/mps_small_rescue_crystal_holdout/comparison_baseline_vs_w005_vs_exactjoint42_w025_fixscale_vs_exactjoint42_w025_fixscale_coordinate_descent.json`
- Result relative to the current heldout-rescue references:
  - main test regressed:
    - baseline:
      - `MAE 3.253`, `RMSE 4.090`, `R2 0.213`
    - corrected exact-joint `w025`:
      - `MAE 3.221`, `RMSE 4.072`, `R2 0.219`
    - `coordinate_descent` exact-joint `w025`:
      - `MAE 3.340`, `RMSE 4.175`, `R2 0.180`
  - crystal-standard improved only slightly relative to plain exact-joint and
    still stayed worse than baseline:
    - baseline:
      - `MAE 2.038`
    - corrected exact-joint `w025`:
      - `MAE 2.223`
    - `coordinate_descent` exact-joint `w025`:
      - `MAE 2.157`
  - forced-oracle crystal evaluation became the best result in this small
    heldout-rescue line:
    - baseline oracle:
      - `MAE 1.378`, `RMSE 1.901`, `R2 -1.005`
    - corrected exact-joint `w025` oracle:
      - `MAE 1.340`, `RMSE 1.938`, `R2 -1.085`
    - `coordinate_descent` exact-joint `w025` oracle:
      - `MAE 1.151`, `RMSE 1.695`, `R2 -0.596`
- Compensation diagnostics:
  - standard:
    - baseline:
      - `corr(delta_phi, delta_gamma)=0.768`
      - `mean |delta_phi + delta_gamma|=2.039`
    - corrected exact-joint `w025`:
      - `corr(delta_phi, delta_gamma)=0.636`
      - `mean |delta_phi + delta_gamma|=2.232`
    - `coordinate_descent` exact-joint `w025`:
      - `corr(delta_phi, delta_gamma)=0.755`
      - `mean |delta_phi + delta_gamma|=2.160`
  - oracle:
    - baseline:
      - `corr(delta_phi, delta_gamma)=0.775`
      - `mean |delta_phi + delta_gamma|=1.369`
    - corrected exact-joint `w025`:
      - `corr(delta_phi, delta_gamma)=0.645`
      - `mean |delta_phi + delta_gamma|=1.325`
    - `coordinate_descent` exact-joint `w025`:
      - `corr(delta_phi, delta_gamma)=0.762`
      - `mean |delta_phi + delta_gamma|=1.144`
- Interpretation:
  - the branch-aware training change did **not** solve the crystal-standard
    conflict on this small protocol
  - it also did **not** preserve the cleaner low-correlation compensation
    pattern seen in plain exact-joint `w025`; the correlation metric moved back
    toward the baseline regime
  - however, it materially improved the oracle regime:
    - best oracle MAE so far in this heldout-rescue line
    - lowest oracle `mean |delta_phi + delta_gamma|` so far in this line
  - working hypothesis after this run:
    - `coordinate_descent` helps the oracle decomposition mostly by improving
      the magnitude balance between crystal and activity terms
    - but the frozen/refit schedule in its current single-cycle form is not yet
      enough to recover baseline-quality crystal predictions or a consistently
      cleaner compensation structure in standard evaluation
