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

## Installation

```bash
conda create -n tgnn-solv python=3.11
conda activate tgnn-solv
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
pip install -e ".[dev]"
```

## Canonical Commands

### Reproducible workflow

1. `python scripts/prepare_data.py`
2. `python scripts/train.py`
3. `python scripts/run_seeds.py`
4. `python scripts/evaluate_complete.py`
5. `python scripts/run_split_comparisons.py`
6. `python scripts/generate_paper_figures.py`
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
python scripts/train.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --device cuda
```

For the maintained tuned TGNN baseline used in current architecture
comparisons, prefer `configs/paper_config_tuned.yaml`.

### Multi-seed TGNN-Solv

```bash
python scripts/run_seeds.py \
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
python scripts/train_directgnn.py \
    --config configs/paper_config_directgnn_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn.pt \
    --device cuda
```

### Train DirectGNN with descriptor augmentation

```bash
python scripts/train_directgnn.py \
    --config configs/paper_config_directgnn_descriptors.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn_desc.pt \
    --device cuda
```

### Full-budget diagnostic run

```bash
python scripts/run_full_budget_experiment.py \
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

### Medium-budget architecture comparison

```bash
python scripts/run_medium_budget_comparison.py \
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
python scripts/run_split_comparisons.py \
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
python scripts/run_optuna.py --models tgnn_solv,direct_gnn --n-trials 20
```

### Diagnostics

```bash
python scripts/diagnose_training.py stats
python scripts/diagnose_training.py overfit --sample-size 1000 --epochs 200
python scripts/validate_physics.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output results/physics_validation.json
```

## Optional External Baselines

### FastSolv

```bash
python scripts/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/fastsolv_predictions.csv

python scripts/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics results/fastsolv_compare.json
```

### SolProp

```bash
conda activate solprop
python scripts/run_solprop.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/solprop_predictions.csv \
    --temperature_dependent
```

## Architecture

### TGNN-Solv Forward Path

The maintained `TGNNSolv` forward pass in `src/tgnn_solv/model.py` is:

1. `GNNEncoder`
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
8. `FusionHead`
   - standard mode: predicts `T_m`, `dH_fus`, optional `dCp_fus`
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
- `tau_12`
- `tau_21`
- `ln_gamma_2`
- `Phi`
- `ln_x2_physics`
- `ln_x2_final`

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

With `use_gc_priors_crystal=True`, the GC crystal residual branches are
zero-initialized so the starting prediction equals the calibrated GC prior, and
they can be frozen for the first `gc_prior_residual_freeze_epochs` of Phase 1.

The canonical paper budget is `50 / 200 / 50`.

### Pair-aware batching

`scripts/train.py` uses pair-aware batching by default through
`make_loader(...)` so that:

- `pair_temp_rank`
- `vant_hoff_local`

can act on multiple temperatures from the same `(solute, solvent)` pair.

### Bridge, Walden, and Oracle

Current behavior:

- `bridge_loss_weight` defaults to `0.0`
- explicit phase-level bridge weights in YAML still override that default
- `use_walden_check` is optional and off by default
- `use_oracle_injection` is train-only unless a diagnostic script explicitly
  forces it in eval mode

The main maintained configs around these controls are:

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

## Configuration

All hyperparameters live in `src/tgnn_solv/config.py` in `TGNNSolvConfig`.

High-signal flags that are easy to miss:

- `encoder_role_mode`
- `nrtl_tau_mode`
- `use_morgan_features`
- `use_descriptor_augmentation`
- `use_descriptor_priors`
- `use_group_priors`
- `use_gc_priors_crystal`
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
- `configs/paper_config_directgnn_tuned.yaml`
- `configs/paper_config_directgnn_descriptors.yaml`
- `configs/small_debug.yaml`

## Documentation Map

- `docs/architecture.md`
- `docs/data_preparation.md`
- `docs/training.md`
- `docs/evaluation.md`
- `docs/baselines.md`
- `docs/reproducing_paper.md`
- `docs/script_reference.md`
- `docs/repository_audit.md`
- `docs/free_gpu_training.md`

## Current Caveats

- the full-budget experiment runner is present and maintained, but expensive
- the main single-run training CLIs support resume, but not every wrapper adds
  its own orchestration around partial-progress recovery
- FastSolv and SolProp remain optional external stacks
- not every research script is as hardened as the canonical train/eval path
