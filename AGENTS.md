# AGENTS.md

This file provides guidance to WARP and other coding agents working in this
repository.

## Project Overview

TGNN-Solv is a physics-informed graph neural network for solid-liquid
equilibrium (SLE) solubility prediction.

The key maintained comparison is:

- `TGNN-Solv`
  - predicts physical parameters, solves SLE, then applies a bounded
    parameter-space correction
- `DirectGNN`
  - matched backbone, direct `ln(x2)` prediction, no solver

The main research question is whether the explicit physics bottleneck helps
relative to the same graph backbone trained directly on solubility.

For a full conceptual and mathematical orientation before research-heavy work,
read:

- `PROJECT_DESCRIPTION.md`

It summarizes the problem, thermodynamic derivation, architecture, training
scheme, current empirical state, and roadmap. `PROJECT_MEMORY.md` remains the
source of truth for changing facts and recent incidents.

## Project Memory

Canonical cross-agent project memory lives in:

- `PROJECT_MEMORY.md`

All coding agents must treat it as a maintained operational source of truth.

Required workflow:

- before substantial work, read `PROJECT_MEMORY.md`
- when old narrative assets (`main.tex`, presentation text, older docs) disagree
  with fresh result bundles, prefer current reproducible artifacts and
  `PROJECT_MEMORY.md`
- after any significant incident, update `PROJECT_MEMORY.md` in the same turn
  if feasible

For this repository, an "incident" includes:

- new benchmark result
- failed or unstable run
- split/protocol change
- environment/runtime issue
- documentation drift discovery
- accepted hypothesis change
- artifact contract change

Memory updates should be factual, dated, concise, and point to concrete files
under `results/`, `logs/`, `docs/`, or source code.

## Installation

```bash
conda create -n tgnn-solv python=3.11
conda activate tgnn-solv
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
pip install -e ".[dev]"
```

Useful optional extras:

- `pip install -e ".[gui,dev]"`
  - Streamlit `Experiment Lab`, Ketcher, flow editor, planner UI
- `pip install -e ".[baselines]"`
  - external baseline wrappers such as FastSolv and SolProp helpers

Preferred CLI navigation is now grouped by purpose under:

- `scripts/data/`
- `scripts/training/`
- `scripts/evaluation/`
- `scripts/experiments/`
- `scripts/external/`
- `scripts/applications/`

Additional research diagnostics and interpretation helpers live under:

- `scripts/analysis/`

Legacy top-level `scripts/*.py` entry points are intentionally retained for
backward compatibility with imports, tests, and automation such as
`reproduce.sh`.

The internal package surface now also has grouped namespaces for navigation:

- `tgnn_solv.core`
- `tgnn_solv.chemistry`
- `tgnn_solv.data`
- `tgnn_solv.models`
- `tgnn_solv.physics`
- `tgnn_solv.training`
- `tgnn_solv.evaluation`
- `tgnn_solv.baselines`
- `tgnn_solv.research`
- `tgnn_solv.applications`

Legacy flat imports such as `tgnn_solv.model`, `tgnn_solv.trainer`, and
`tgnn_solv.inference` remain supported and are still the implementation source
of truth.

## Canonical Commands

### Reproducible workflow

1. `python scripts/data/prepare_data.py`
2. `python scripts/training/train.py`
3. `python scripts/experiments/run_seeds.py`
4. `python scripts/evaluation/evaluate_complete.py`
5. `python scripts/experiments/run_split_comparisons.py`
6. `python scripts/experiments/generate_paper_figures.py`
7. `bash reproduce.sh`

### Run all tests

```bash
pytest tests/ -v
```

### Specific tests

```bash
pytest tests/test_physics.py -v
pytest tests/test_integration.py -v
pytest tests/test_loss.py -v
pytest tests/test_dataset.py -v
```

### Train one TGNN-Solv model

```bash
python scripts/training/train.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --device cuda
```

Optional expanded-IDAC supervision is now passed as a separate auxiliary
stream, not by appending gamma-only rows to the main SLE CSV:

```bash
python scripts/training/train.py \
    --config configs/paper_config_tuned_entropy_interaction_rescue_explicit_h_small.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --idac-train-data results/temperature_extrapolation_enhanced_proxy/splits/idac_aux_train.csv \
    --idac-steps-per-epoch 4 \
    --idac-batch-size 64 \
    --checkpoint checkpoints/tgnn_with_idac_aux.pt \
    --device cuda
```

For same-pair temperature-extrapolation ablations, precomputed Van't Hoff
anchor rows can be added to the low-temperature train split without treating
them as measured solubility labels:

```bash
python scripts/data/build_vant_hoff_anchor_split.py \
    --train-data results/temperature_extrapolation_baselines/splits/train_low.csv \
    --output results/temperature_extrapolation_enhanced_proxy/splits/train_low_vh_anchor_350.csv \
    --summary results/temperature_extrapolation_enhanced_proxy/vh_anchor_350_summary.json \
    --temperatures 350.0 \
    --min-points 3 \
    --min-temp-span 5.0 \
    --weight 1.0
```

For the maintained tuned TGNN baseline used in current architecture
comparisons, prefer `configs/paper_config_tuned.yaml`.

Useful maintained follow-up configs:

- `configs/paper_config_tuned_tgnn_descriptors.yaml`
- `configs/paper_config_tuned_regularized.yaml`
- `configs/paper_config_tuned_regularized_gc.yaml`
- `configs/paper_config_tuned_regularized_descriptors.yaml`
- `configs/paper_config_tuned_source_weighted.yaml`
- `configs/paper_config_tuned_gps.yaml`
- `configs/paper_config_timp.yaml`
- `configs/paper_config_timp_full.yaml`
- `configs/paper_config_hansen_contrastive.yaml`
- `configs/paper_config_tuned_pretrained.yaml`
- `configs/paper_config_tuned_pretrained_descriptors.yaml`
- `configs/paper_config_tuned_interaction_rescue.yaml`
- `configs/paper_config_tuned_entropy_fusion.yaml`
- `configs/paper_config_tuned_entropy_interaction_rescue_explicit_h_small.yaml`
- `configs/paper_config_tuned_explicit_h_small.yaml`
- `configs/paper_config_tuned_tgnn_descriptors_explicit_h_small.yaml`
- `configs/paper_config_directgnn_tuned_explicit_h_small.yaml`
- `configs/paper_config_directgnn_descriptors_explicit_h_small.yaml`
- `configs/paper_config_uniquac.yaml`
- `configs/paper_config_wilson.yaml`

### Train TGNN-Solv with Stage 0 pretraining

```bash
python scripts/training/train_with_pretrain.py \
    --config configs/paper_config_tuned_pretrained.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_pretrained.pt \
    --pretrain-data zinc250k \
    --pretrain-epochs 30 \
    --device cuda
```

This is a thin wrapper over `scripts/training/train.py --pretrain` and also
enables the maintained post-train descriptor probe path by default.

### Multi-seed TGNN-Solv

```bash
python scripts/experiments/run_seeds.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/multi_seed_results.json \
    --checkpoint-dir checkpoints/seeds \
    --device cuda
```

### Train DirectGNN baseline

```bash
python scripts/training/train_directgnn.py \
    --config configs/paper_config_directgnn_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn.pt \
    --device cuda
```

### Train DirectGNN with descriptor augmentation

```bash
python scripts/training/train_directgnn.py \
    --config configs/paper_config_directgnn_descriptors.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn_desc.pt \
    --device cuda
```

### Full-budget diagnostic run

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

This exports:

- TGNN metrics
- DirectGNN metrics
- oracle-evaluated TGNN metrics
- `tgnn_intermediates.csv`
- detailed diagnostics JSON

The training CLIs now support resumable checkpoints via
`--checkpoint-every` and `--resume`, and the full-budget runner reuses those
per-seed checkpoints automatically.

### Multi-seed phase-1 diagnostic wrapper

```bash
python scripts/experiments/run_phase1_diagnostic.py \
    --seeds 42,123,456 \
    --budget 50,200,50 \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/phase1_diagnostic \
    --device cuda
```

This wrapper orchestrates:

- TGNN-Solv training/eval per seed
- DirectGNN training/eval per seed
- optional RF descriptor/morgan/hybrid baselines
- TGNN oracle evaluation via forced oracle injection
- aggregate JSON/markdown reporting and paired t-tests across seeds

### Medium-budget architecture comparison

```bash
python scripts/experiments/run_medium_budget_comparison.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/medium_budget \
    --device cuda
```

This trains tuned TGNN, GC-prior TGNN variants, tuned DirectGNN,
DirectGNN+descriptors, and RF(descriptors) on the full scaffold split.

### Split-wise comparison

```bash
python scripts/experiments/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline,rf_morgan,rf_hybrid" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

### Quick inference

```python
from tgnn_solv.inference import load_model, predict_solubility, interpret_prediction

model, cfg = load_model("checkpoints/tgnn_solv_trained.pt")
result = predict_solubility(
    model,
    solute_smiles="CC(=O)Nc1ccc(O)cc1",
    solvent_smiles="CCO",
    T=298.15,
)
print(interpret_prediction(result))
```

### Optuna

```bash
python scripts/experiments/run_optuna.py \
    --models tgnn_solv,tgnn_solv_gps,tgnn_solv_descriptors,direct_gnn,direct_gnn_descriptors \
    --n-trials 20
```

Current scope note:

- `Stage 0` pretraining is intentionally outside the default Optuna loop
  because rerunning ZINC-scale pretraining inside each trial would dominate
  the actual TGNN search cost

### Experiment Lab

```bash
python scripts/launch_lab.py
```

The maintained Streamlit surface now includes:

- `Training`
- `Experiments`
- `Pipeline Studio`
- `Model Architect`
- `Results & Plots`
  - including `Benchmark Studio`, lineage, artifact diff, registry
- `Inference`
  - TGNN-Solv and DirectGNN, uncertainty, calibration, AD/OOD, Ketcher editing
- `Applications`
  - solvent screening, process optimization, drug developability, PK solubility profile
- `Planner`
- `Documentation`
- `Reproduce`

### Application CLIs

```bash
python scripts/applications/screen_solvents.py --help
python scripts/applications/optimize_process.py --help
python scripts/applications/drug_developability.py --help
python scripts/applications/pk_profile.py --help
```

These are maintained thin wrappers over:

- `tgnn_solv.applications.solvent_screening`
- `tgnn_solv.applications.process_optimization`
- `tgnn_solv.applications.drug_properties`
- `tgnn_solv.applications.pk_profiling`

### Diagnostics

```bash
python scripts/training/diagnose_training.py stats
python scripts/training/diagnose_training.py overfit --sample-size 1000 --epochs 200
python scripts/evaluation/validate_physics.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output results/physics_validation.json
python scripts/evaluation/run_knn_modelability.py \
    --train-data notebooks/data/processed/train.csv \
    --test-data notebooks/data/processed/test.csv \
    --out-dir results/knn_modelability
python scripts/evaluation/run_metric_diagnostics.py \
    --protocols scaffold,solute,solvent,pair_random,row_random \
    --out-dir results/metric_diagnosis_bundle
python scripts/evaluation/run_directgnn_error_structure_diagnostics.py --help
python scripts/evaluation/run_prediction_error_slices.py --help
python scripts/evaluation/plot_prediction_error_slices.py --help
python scripts/evaluation/run_temperature_extrapolation_baselines.py --help
python scripts/evaluation/run_temperature_interpolation_baselines.py --help
python scripts/data/build_vant_hoff_anchor_split.py --help
python scripts/analysis/run_structural_extrapolation_diagnosis.py --help
python scripts/analysis/audit_water_small_molecule_graphs.py --help
python scripts/analysis/diagnose_gradient_flow.py --help
python scripts/analysis/analyze_timp_channels.py --help
python scripts/analysis/audit_fusion_supervision.py --help
python scripts/analysis/run_source_uncertainty_audit.py --help
python scripts/analysis/sensitivity_analysis.py --help
python scripts/analysis/weight_analysis.py --help
```

### Benchmark Infrastructure

```bash
python scripts/evaluation/benchmark_adapter_model.py --help
python scripts/evaluation/run_thermo_stress_suite.py --help
python scripts/experiments/build_benchmark_release.py --help
```

## Optional External Baselines

### FastSolv

```bash
python scripts/external/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/fastsolv_predictions.csv

python scripts/external/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics results/fastsolv_compare.json
```

### SolProp

```bash
conda activate solprop
python scripts/external/run_solprop.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/solprop_predictions.csv \
    --temperature_dependent
```

For current article-comparison benchmarking, the maintained SolProp mode is
native retraining on TGNN-Solv targets via `run_solprop.py train-native` /
`predict-native`.

## Architecture

### TGNN-Solv Forward Path

The maintained `TGNNSolv` forward pass in `src/tgnn_solv/model.py` is:

1. graph encoder
   - default `encoder_type="mpnn"` via `GNNEncoder`
   - optional `encoder_type="gps"` via `GPSEncoder`
   - optional `encoder_type="timp"` via `TIMPEncoder`
     - splits message passing into dispersive and polar channels
     - can consume folded heavy-atom Gasteiger charges and extra physical edge features
   - default `encoder_role_mode="shared_residual"`
   - optional `split_late`
2. pre-interaction auxiliary heads
   - `HansenHead`
   - `AuxPropsHead` for `V_m`
3. optional pre-head priors for `Hansen` / `V_m`
   - `use_descriptor_priors`
   - `use_group_priors`
4. solute-solvent interaction
   - default cross-attention
   - optional bipartite message passing
5. `PhysicsAwareReadout`
6. optional Morgan augmentation
7. pair representation and optional solvent-type MoE
   - optional shared RDKit descriptor augmentation enriches the pair state and
     projects it back to `pair_dim` before the physics heads
   - optional train-only auxiliary direct-solubility head can read the pair
     state for interaction-gradient rescue
8. `FusionHead`
   - standard mode: predicts `T_m`, `dH_fus`, optional `dCp_fus`
   - optional `fusion_output_mode="entropy_coupled"` standard-head mode:
     predicts `dH_fus` and `dS_fus`, then derives `T_m = dH_fus / dS_fus`
   - crystal GC mode: bounded residual around calibrated `T_m_gc`,
     `dH_fus_gc`, fixed `dCp_fus_gc`
9. `NRTLHead`
   - default `nrtl_tau_mode="ref_invT"`
10. solver-facing parameter substitution
    - optional oracle injection for supervised `T_m` / `dH_fus`
11. `SLESolver`
12. `AdaptivePhysicsCorrection`
    - bounded parameter deltas and gated residual blend

### Important Forward Outputs

`model.forward(...)` now exposes:

- `fusion_params`
  - raw head outputs used by auxiliary losses
- `solver_fusion_params`
  - actual values passed into the solver
- `oracle_injection_masks`
  - present when oracle injection is active
- `fusion_gc_priors`
  - present when crystal GC priors are enabled

With `return_intermediates=True`, the model also exposes solver-facing
diagnostic tensors such as:

- `T_m_solver`
- `dH_fus_solver`
- `dCp_fus_solver`
- `dS_fus`
- `tau_12`
- `tau_21`
- `ln_gamma_2`
- `Phi`
- `ln_x2_physics`
- `ln_x2_final`

When `encoder_type="timp"`, the intermediates also include channel-aware graph
embeddings such as:

- `g_sol_disp_pre`, `g_sol_polar_pre`
- `g_slv_disp_pre`, `g_slv_polar_pre`
- `g_sol_disp_post`, `g_sol_polar_post`
- `g_slv_disp_post`, `g_slv_polar_post`
- `timp_delta_d`, `timp_delta_p`, `timp_delta_h`

### DirectGNN

`DirectGNN` reuses:

- the same encoder
- the same interaction stack
- the same readout

It replaces the entire physics path with:

- thermometer temperature encoding
- direct MLP to `ln(x2)`

Optional DirectGNN feature paths:

- `use_morgan_features`
- `use_descriptor_augmentation`
- `encoder_type="gps"` for the GPS backbone option
- `encoder_type="timp"` for the TIMP backbone option

Descriptor augmentation computes full RDKit descriptors for both molecules,
sanitizes non-finite values, normalizes them using train-set statistics, and
augments the pair
representation with descriptor interactions.

## Training and Losses

### Curriculum

`src/tgnn_solv/trainer.py` implements a three-phase curriculum:

- Phase 1: property pretraining only
- Phase 2: full SLE training
- Phase 3: low-LR fine-tuning

`scripts/training/train.py` can also prepend optional Stage 0 encoder/readout
pretraining with:

- `--pretrain`
- `--pretrain-checkpoint`
- `--pretrain-epochs`
- `--pretrain-data`
- `--pretrain-output`

With `use_gc_priors_crystal=True`, the GC crystal residual branches are
zero-initialized so the starting prediction equals the calibrated GC prior, and
they can be frozen for the first `gc_prior_residual_freeze_epochs` of Phase 1.

The canonical paper budget is `50 / 200 / 50`.

When `encoder_type="timp"`, the trainer also enables channel-supervision
Hansen probes by default:

- Phase 1: `timp_disp_hansen=0.05`, `timp_polar_hansen=0.05`
- Phase 2/3: `timp_disp_hansen=0.02`, `timp_polar_hansen=0.02`

### Pair-aware batching

`scripts/training/train.py` uses pair-aware batching by default through
`make_loader(...)` so that:

- `pair_temp_rank`
- `vant_hoff_local`

can act on multiple temperatures from the same `(solute, solvent)` pair.

### Bridge, Walden, and Oracle

Current behavior:

- `bridge_loss_weight` defaults to `0.0`
- explicit phase-level bridge weights in YAML still override that default
- `use_hansen_contrastive` is optional and off by default
- `use_aux_direct_sol_loss` is optional and off by default
- `use_walden_check` is optional and off by default
- `use_oracle_injection` is train-only unless a diagnostic script explicitly
  forces it in eval mode

The main maintained configs around these controls are:

- `paper_config_hansen_contrastive.yaml`
- `paper_config_tuned_interaction_rescue.yaml`
- `paper_config_tuned_entropy_interaction_rescue_explicit_h_small.yaml`
- `paper_config_oracle.yaml`
- `paper_config_no_bridge.yaml`
- `paper_config_no_bridge_no_walden.yaml`

## Data Pipeline

### Processed splits

Canonical processed data lives under:

- `notebooks/data/processed/train.csv`
- `notebooks/data/processed/val.csv`
- `notebooks/data/processed/test.csv`

Additional split families:

- `*_solute.csv`
- `*_solvent.csv`

Canonical data preparation now keeps solvent-side water (`O`) in the
supervised `ln_x2` subset by default, even though water has only one atom and
would otherwise fail the generic `min_atoms=2` solvent gate. To reproduce the
legacy corpus without supervised aqueous rows, use either:

- `python scripts/data/prepare_data.py --no-include-water-solubility`
- `include_water_solubility: false` in the YAML config

### Dataset outputs

`TGNNSolvDataset` returns `(solute_graph, solvent_graph, targets_dict)` with
core keys:

- `T`
- `ln_x2`
- `has_solubility`
- `pair_key`
- `solvent_type`
- `T_m`, `T_m_mask`, `has_T_m`
- `dH_fus`, `dH_mask`, `has_dH_fus`
- `hansen_sol`, `hansen_mask`
- `ln_gamma_inf`, `gamma_mask`

Optional keys appear when enabled:

- `solute_morgan_fp`, `solvent_morgan_fp`
- `solute_descriptors`, `solvent_descriptors`
- `solute_descriptor_prior_features`, `solvent_descriptor_prior_features`
- `solute_group_prior_features`, `solvent_group_prior_features`
- `T_m_gc`, `dH_fus_gc`, `dCp_fus_gc`
- `hansen_sol_effective`, `hansen_slv_effective`
- `hansen_contrastive_mask`, `hansen_slv_contrastive_mask`
- `hansen_sol_contrastive_weight`, `hansen_slv_contrastive_weight`
- `pair_Ra`, `pair_hansen_mask`
- `source_sigma_ln_x2`, `source_solubility_weight`
- `source_method_guess`, `source_detail`

Graph featurization is now config-driven. The default corpus still uses the
historical `35/8` node/edge layout, while TIMP runs can opt into:

- `use_gasteiger_charges`
  - appends folded heavy-atom Gasteiger charge to each node feature vector
- `use_phys_edge_features`
  - appends `delta_chi`, `delta_rvdw`, `bond_polarity`, `hbond_cap` to each edge
- `explicit_h_small_molecules`
  - opt-in topology change for molecules with at most
    `explicit_h_max_heavy_atoms` heavy atoms; water changes from a one-node
    self-loop graph to an explicit O-H graph without changing feature
    dimensions

Application-layer modules build on top of the same inference surfaces and now
live under `src/tgnn_solv/applications/` rather than the old flat
`src/tgnn_solv/applications.py`.

## Configuration

All hyperparameters live in `src/tgnn_solv/config.py` in `TGNNSolvConfig`.

High-signal flags that are easy to miss:

- `activity_model`
- `encoder_role_mode`
- `nrtl_tau_mode`
- `use_morgan_features`
- `use_descriptor_augmentation`
- `use_descriptor_priors`
- `use_group_priors`
- `use_gc_priors_crystal`
- `fusion_output_mode`
- `fusion_entropy_min`
- `fusion_entropy_max`
- `fusion_entropy_init`
- `fusion_enthalpy_init`
- `encoder_type`
- `gps_num_heads`
- `gps_positional_encoding`
- `gps_pe_dim`
- `use_gasteiger_charges`
- `use_phys_edge_features`
- `explicit_h_small_molecules`
- `explicit_h_max_heavy_atoms`
- `use_thermo_cross_attention`
- `thermo_cross_attention_beta_init`
- `use_hansen_contrastive`
- `use_aux_direct_sol_loss`
- `include_water_solubility`
- `use_source_uncertainty_weights`
- `source_uncertainty_csv`
- `source_uncertainty_weight_mode`
- `idac_aux_steps_per_epoch`
- `idac_aux_phase1_weight`
- `idac_aux_phase2_weight`
- `idac_aux_phase3_weight`
- `vant_hoff_slope_scale`
- `vant_hoff_intercept_scale`
- `vh_anchor_default_weight`
- `use_oracle_injection`
- `bridge_loss_weight`
- `use_walden_check`
- `use_pair_temperature_batching`

Maintained config files:

- `configs/paper_config.yaml`
- `configs/paper_config_tuned.yaml`
- `configs/paper_config_split_late.yaml`
- `configs/paper_config_gc_priors.yaml`
- `configs/paper_config_oracle.yaml`
- `configs/paper_config_no_bridge.yaml`
- `configs/paper_config_no_bridge_no_walden.yaml`
- `configs/paper_config_combined.yaml`
- `configs/paper_config_tuned_tgnn_descriptors.yaml`
- `configs/paper_config_tuned_regularized.yaml`
- `configs/paper_config_tuned_regularized_gc.yaml`
- `configs/paper_config_tuned_regularized_descriptors.yaml`
- `configs/paper_config_tuned_gps.yaml`
- `configs/paper_config_timp.yaml`
- `configs/paper_config_timp_full.yaml`
- `configs/paper_config_hansen_contrastive.yaml`
- `configs/paper_config_tuned_pretrained.yaml`
- `configs/paper_config_tuned_pretrained_descriptors.yaml`
- `configs/paper_config_tuned_interaction_rescue.yaml`
- `configs/paper_config_tuned_entropy_fusion.yaml`
- `configs/paper_config_tuned_entropy_interaction_rescue_explicit_h_small.yaml`
- `configs/paper_config_tuned_explicit_h_small.yaml`
- `configs/paper_config_tuned_tgnn_descriptors_explicit_h_small.yaml`
- `configs/paper_config_directgnn_tuned.yaml`
- `configs/paper_config_directgnn_tuned_source_weighted.yaml`
- `configs/paper_config_directgnn_tuned_explicit_h_small.yaml`
- `configs/paper_config_directgnn_descriptors.yaml`
- `configs/paper_config_directgnn_descriptors_explicit_h_small.yaml`
- `configs/paper_config_uniquac.yaml`
- `configs/paper_config_wilson.yaml`
- `configs/small_debug.yaml`

## Documentation Map

- `docs/index.md`
- `docs/getting_started/installation.md`
- `docs/getting_started/quick_start.md`
- `docs/architecture.md`
- `docs/config_cookbook.md`
- `docs/data_preparation.md`
- `docs/training.md`
- `docs/evaluation.md`
- `docs/experiments.md`
- `docs/results.md`
- `docs/model_zoo.md`
- `docs/notebooks.md`
- `docs/applications.md`
- `docs/experiment_lab.md`
- `docs/baselines.md`
- `docs/reproducing_paper.md`
- `docs/script_reference.md`
- `docs/faq.md`
- `docs/troubleshooting.md`
- `docs/repository_audit.md`
- `docs/free_gpu_training.md`
- `docs/presentation.md`
- `BENCHMARKING_GUIDE.md`
- `scripts/README.md`
- `src/tgnn_solv/README.md`

## Current Caveats

- the full-budget experiment runner is present and maintained, but expensive
- the main single-run training CLIs support resume, but not every wrapper adds
  its own orchestration around partial-progress recovery
- FastSolv and SolProp remain optional external stacks
- not every research script is as hardened as the canonical train/eval path
- `DirectGNN` now supports the maintained uncertainty / calibration helpers,
  but the current OOD/applicability-domain path remains TGNN-specific
- benchmark bundles now include sidecars (`run_manifest.json`,
  `benchmark_card.json`), so changing that contract requires extra care
- application workflows are solubility-first decision tools, not full
  retrosynthesis, PBPK, or mechanistic PK/PD models
