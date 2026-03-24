# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

TGNN-Solv is a **physics-informed Graph Neural Network** for predicting solid-liquid equilibrium (SLE) solubility. The GNN predicts *physical parameters* (melting point T_m, fusion enthalpy ΔH_fus, NRTL interaction energies), not solubility directly. Thermodynamic equations are hardcoded and differentiable — gradients flow through physics back to the GNN.

## Installation

```bash
conda create -n tgnn-solv python=3.11
conda activate tgnn-solv
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
pip install -e ".[dev]"
```

## Commands

### Canonical Reproducible Path

The main reproducible workflow is:

1. `python scripts/prepare_data.py`
2. `python scripts/train.py`
3. `python scripts/run_seeds.py`
4. `python scripts/evaluate_complete.py`
5. `python scripts/run_split_comparisons.py`
6. `python scripts/generate_paper_figures.py`
7. `bash reproduce.sh`

Use the notebooks for exploratory analysis, ablations, baseline research, and
temperature studies. See `docs/script_reference.md` for the current maturity
map.

**Run all tests:**
```bash
pytest tests/ -v
```

**Run a specific test module:**
```bash
pytest tests/test_physics.py -v
```

**Run a single test:**
```bash
pytest tests/test_physics.py::TestNRTL::test_dilute_limit -v
```

**Run the SolProp baseline comparison** (requires separate `solprop` conda env):
```bash
conda activate solprop
python scripts/run_solprop.py \
    --input notebooks/data/processed/test.csv \
    --output notebooks/data/processed/solprop_predictions.csv \
    --temperature_dependent
```

**Calibrate SolProp on your splits (linear correction) and evaluate:**
```bash
conda activate solprop
python scripts/run_solprop.py train \
    --train notebooks/data/processed/train.csv \
    --val notebooks/data/processed/val.csv \
    --test notebooks/data/processed/test.csv \
    --outdir checkpoints/solprop_run \
    --temperature_dependent \
    --include_temperature \
    --export_preds
```

**Run FastSolv baseline + comparison** (requires `fastsolv`):
```bash
# Predict with pretrained FastSolv ensemble
python scripts/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output notebooks/data/processed/fastsolv_pred.csv

# Compare FastSolv vs TGNN-Solv metrics
python scripts/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics checkpoints/fastsolv_compare.json
```

⚠️ **NOTE on FastSolv Training**: Training FastSolv from scratch with custom data may fail with NaN predictions due to:
- Descriptor computation producing NaN for certain molecule classes
- Model architecture incompatibility with new data distributions
- Use **pretrained FastSolv ensemble prediction** instead, or **use TGNN-Solv for custom training** (fully differentiable physics-based architecture)

**Prepare data, train, and evaluate** (via Jupyter notebooks):
```bash
jupyter notebook notebooks/01_prepare_data.ipynb   # Downloads BigSolDBv2.1 (~120k records)
jupyter notebook notebooks/02_train.ipynb
jupyter notebook notebooks/04_evaluation.ipynb
```

**Reproduce the main paper workflow**:
```bash
bash reproduce.sh
```

**Run the shared-vs-split-late backbone comparison**:
```bash
python scripts/run_seeds.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output results/multi_seed_results.json

python scripts/run_seeds.py \
    --config configs/paper_config_split_late.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output results/split_late_multi_seed_results.json
```

**Run the canonical split-protocol comparison**:
```bash
python scripts/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

**Benchmark trained model:**
```bash
# Single model benchmark
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/results.json

# Compare multiple models
python scripts/compare_models.py \
    --models checkpoints/v1.pt checkpoints/v2.pt checkpoints/v3.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/comparison.json
```

See [BENCHMARKING_GUIDE.md](BENCHMARKING_GUIDE.md) for detailed benchmarking instructions.

**Script roles and maturity notes:**

- `scripts/evaluate_complete.py` is the lightweight evaluation entry point and
  now emits prediction arrays used by the plotting pipeline.
- `scripts/benchmark_tgnn_solv.py` is the richer `Evaluator`-backed benchmark
  entry point.
- `scripts/run_fastsolv.py compare` is the preferred FastSolv comparison
  wrapper; `scripts/compare_fastsolv_tgnn.py` is a lighter convenience script.
- `scripts/train_directgnn.py` is the CLI entry point for the DirectGNN
  no-physics baseline.
- `scripts/run_ablation.py` is the CLI entry point for multi-seed ablation
  sweeps.
- `scripts/run_split_comparisons.py` is the CLI entry point for fair
  split-wise comparisons across scaffold, solute, and solvent protocols.
- `scripts/error_analysis.py`, `scripts/learning_curves.py`,
  `scripts/temperature_extrapolation.py`, `scripts/validate_physics.py`,
  `scripts/statistical_tests.py`, and `scripts/generate_supplementary.py`
  provide the paper-analysis steps consumed by `reproduce.sh`.
- `notebooks/05_baselines.ipynb` and `notebooks/06_ablations.ipynb` remain
  useful for exploratory inspection and manual debugging, but they are no
  longer the only automation path for DirectGNN and ablations.

**Quick inference:**
```python
from tgnn_solv.inference import load_model, predict_solubility, interpret_prediction
model, cfg = load_model("checkpoints/tgnn_solv_trained.pt")
result = predict_solubility(model, solute_smiles="CC(=O)Nc1ccc(O)cc1", solvent_smiles="CCO", T=298.15)
print(interpret_prediction(result))
```

**Optuna hyperparameter tuning:**
```bash
python scripts/run_optuna.py --models tgnn_solv,direct_gnn --n-trials 20
```

**Optuna notebook:**
```bash
jupyter notebook notebooks/08_optuna_tuning.ipynb
```

**Diagnostics (dataset stats + overfit check):**
```bash
python scripts/diagnose_training.py stats
python scripts/diagnose_training.py overfit --sample-size 1000 --epochs 200
```

## Architecture

### Forward Pass Pipeline (`model.py`)

The `TGNNSolv` forward pass runs in this sequence:

1. **GNNEncoder** (`layers.py`) — the default `shared_residual` backbone uses a shared 6-layer MPNN for both solute and solvent, then applies lightweight role-specific adapters at the end. An alternative `split_late` mode keeps early layers shared but gives the last few message-passing layers separate solute/solvent weights for direct shared-vs-asymmetric comparison. In the v2 architecture, encoder outputs used by crystal-property heads are temperature-invariant by default.
2. **Auxiliary heads** (`heads.py`) — `HansenHead` and the lightweight `AuxPropsHead` run *before* interaction on the pre-interaction representations. In the maintained architecture `AuxPropsHead` predicts only molar volume `V_m`, because that is the only auxiliary quantity currently used by the loss.
3. **Interaction** (`layers.py`) — default `SoluteSolventCrossAttention` (stacked Transformer cross-attention with global tokens), optional `BipartiteMessagePassing` (complete bipartite message passing between solute/solvent atoms). The default paper config keeps temperature out of the encoder and interaction stack to avoid leakage into crystal-property heads. Requires padding via `pad_atom_features()`.
4. **PhysicsAwareReadout** (`layers.py`) — concatenates attention pooling + Set2Set pooling → 3× hidden_dim vector per molecule.
5. **PairRepresentation** (`heads.py`) — combines `[g_sol, g_slv, g_sol * g_slv, |g_sol - g_slv|]` into a single pair vector.
6. **SolventTypeMoE** (`heads.py`) — optional mixture‑of‑experts routing based on solvent type, applied to the pair vector.
7. **Prediction heads** — `FusionHead` (T_m, ΔH_fus, ΔCp_fus from solute only), `NRTLHead` (default compact `ref_invT` form with `tau(T_ref)` + inverse-temperature slopes; legacy `dg/a_T` and `abc` remain supported) receives explicit temperature features, `HansenHead`, and a `V_m`-only `AuxPropsHead`.
8. **SLESolver** (`solver.py`) — iterative fixed-point solver (SLE + NRTL) with **zero learnable parameters**. Uses `SLESolverFunction` (custom `torch.autograd.Function`) with implicit differentiation via the implicit function theorem for stable training gradients. The v2 solver adds residual-based stopping, adaptive damping, and a temperature gradient term in the implicit backward.
9. **AdaptivePhysicsCorrection** (`heads.py`) — per-sample gating between the physics prediction and a bounded parameter-space proposal. The module predicts bounded deltas for `T_m`, `ΔH_fus`, `tau_12(T)`, and `tau_21(T)`, re-runs the corrected parameters through the SLE solver, then blends the resulting residual: `ln(x₂)_proposal = SLE(theta + delta_theta)`, `ln(x₂) = ln(x₂)_physics + (1 - σ(w)) · clip(ln(x₂)_proposal - ln(x₂)_physics)`.

### Training: Three-Phase Curriculum (`trainer.py`)

- **Phase 1** (50 epochs): Property pretraining only — no solubility loss. Trains heads on T_m, ΔH_fus, Hansen, γ∞. Correction gate is frozen.
- **Phase 2** (200 epochs): Full SLE training with solubility loss. Correction gate unfreezes at epoch 20. Early stopping on val MAE.
- **Phase 3** (50 epochs): Fine-tuning — lower LR, stronger monotonicity and correction penalties. Restores best model at end.

Loss components (weights vary by phase, see `trainer.py::phase_weights`): `sol` (Huber on ln x₂), `T_m`, `dH`, `hansen`, `gamma_inf`, `mono` (dx₂/dT ≥ 0 penalty), `res` (correction magnitude), `bridge` (Hansen–NRTL consistency), `tau_reg`, `phys_pref`, `direct_reg` (keep the residual proposal local), `direct_nll` (uncertainty on the residual proposal), `pair_temp_rank` (same-pair temperature monotonicity), `vant_hoff_local` (local linearity in `ln x₂` vs `1/T`), `moe_balance`.

The canonical `scripts/train.py` path now uses pair-aware train batching by
default, so the same-pair temperature losses are exercised whenever the split
contains repeated `(solute, solvent)` pairs at different temperatures.

### Data Pipeline (`data/`)

- `sources.py` — downloads/parses BigSolDBv2.1 (primary ~121k solubility records), Bradley melting points, curated NIST values, Hansen parameters, and IDAC (γ∞) data. LogS→x₂ uses density/3D‑volume estimates when x₂ is missing.
- `builder.py` — `DataBuilder` merges all sources via left join on canonical SMILES. Also appends "auxiliary-only" records (compounds with T_m but no solubility) for Phase 1 pretraining.
- `split.py` — Group-based train/val/test split using greedy bin-packing. Modes: `solute_scaffold` (default), `solute` (random by solute SMILES), `solvent` (no solvent overlap).
- `split_registry.py` — canonical naming and metadata for split-aware CSVs and
  experiment outputs.
- `dataset.py` — `TGNNSolvDataset` returns `(solute_graph, solvent_graph, targets_dict)` triples. All auxiliary targets have boolean mask columns (`has_T_m`, `has_dH_fus`, etc.) since most records are missing some auxiliary labels. The same module also provides `PairTemperatureBatchSampler` and `make_loader()`, which are used by the canonical training script to keep repeated pair measurements together across temperature.
- `solvent_types.py` — solvent type classification used for MoE routing.

### Key Design Decisions

- **Implicit differentiation**: During training, `SLESolverFunction` runs successive substitution *without* gradient tracking in the forward pass, then computes exact gradients through the converged fixed point using the implicit function theorem. The solver also propagates the NRTL contribution to `d ln(x₂) / dT`, so monotonicity regularization no longer depends on a separate explicit-only path by default. Controlled by `TGNNSolvConfig.use_implicit_diff`.
- **Temperature enters the state block explicitly**: The default v2 setup keeps `T` out of the crystal-property encoder path and injects it directly into the NRTL head and correction summary instead. This reduces temperature leakage into `T_m`, `ΔH_fus`, and other temperature-invariant predictions.
- **Switchable encoder asymmetry**: The maintained default is still the current shared backbone (`encoder_role_mode="shared_residual"`). The codebase also supports `encoder_role_mode="split_late"` for direct shared-vs-asymmetric comparisons without changing the rest of the architecture.
- **Compact NRTL parameterization**: The default configuration uses the more identifiable `ref_invT` mode, where the network predicts `tau(T_ref)` and a single inverse-temperature slope per direction. This is converted internally to the ABC solver form, while `legacy` and `abc` remain loadable for older checkpoints and experiments.
- **Physics layers have zero learnable parameters**: `IdealSolubilityLayer`, `NRTLLayer`, and `HansenDistanceLayer` are fully hardcoded thermodynamic equations.
- **Constrained activations**: All physical outputs are range-constrained (T_m via sigmoid in [100, 700] K; α via sigmoid in [0.1, 0.6]; ΔH_fus via softplus > 0).
- **Bounded correction**: The correction head cannot replace the physics solution with an arbitrary direct predictor. It can only propose a bounded additive correction within `±correction_max_abs`.
- **Parameter-space correction**: The correction module operates on `T_m`, `ΔH_fus`, and current-temperature `tau` values, then pushes those corrected parameters back through the SLE solver. This keeps the correction path physically structured.
- **Same-pair temperature regularization**: The canonical train loader uses pair-aware batching so minibatches systematically contain multiple temperatures for the same `(solute, solvent)` pair when the data allows it, and the loss adds ranking and local van't Hoff consistency penalties.
- **SLE runs in float32**: The SLE solver casts to float32 for numerical stability even when training in mixed precision.
- **Scatter without torch_scatter**: `scatter_add` and `scatter_mean` are implemented natively in `layers.py` to avoid the `torch_scatter` dependency.

### Other Modules

- `progress.py` — Lightweight progress-bar helpers (`progress()`, `trange()`) with graceful fallback to plain iterables when tqdm is unavailable. Used throughout training/inference loops.
- `eval_temperature.py` — Temperature-dependent evaluation: stratified metrics (T=298K vs other), extrapolation analysis (train on T≤T_cut, test on T>T_cut), van't Hoff consistency checks, per-pair temperature curves.
- `evaluate.py` — `Evaluator` class with stratified metrics by solvent type, solubility range, temperature, and auxiliary data availability.
- `uncertainty.py` — `MCDropoutPredictor` (N forward passes with dropout active) and `EnsemblePredictor` (K trained models).
- `domain.py` — `ApplicabilityDomain`: Mahalanobis distance in pair-representation space + Tanimoto similarity to training set. Call `ad.fit(train_loader)` once, then `ad.score(smi_solute, smi_solvent, T)`.
- `pretrain.py` — Optional Stage 0 GNN pretraining on ZINC250k: masked subgraph + bond prediction + contrastive + RDKit property prediction.
- `ablation.py` — Full ablation study framework (10 variants: split-late encoder, no cross-attn, no NRTL, no curriculum, no aux losses, no correction, no implicit diff, small/large model).
- `baselines/` — `DirectGNN`: same GNN+cross-attn backbone but with direct MLP → ln(x₂) prediction (no physics). Used as the key ablation to validate physics adds value. `ThermometerEncoder`: ordinal temperature encoding with fractional bin filling for smooth gradients.

### Configuration (`config.py`)

All hyperparameters live in `TGNNSolvConfig` (a `dataclass`). Key fields:
- `hidden_dim=256`, `n_gnn_layers=6`, `n_cross_attn_layers=3`, `pair_dim=512`
- `encoder_role_mode="shared_residual"` (default) or `"split_late"`
- `encoder_role_specific_layers` — number of late role-specific GNN layers in `split_late` mode
- `n_iter_train=5`, `n_iter_eval=20` — SLE fixed-point iterations
- `solver_tol_train`, `solver_tol_eval`, `solver_adaptive_damping` — residual-based convergence control for the solver
- `use_implicit_diff=True` — use implicit differentiation in backward pass
- `interaction_mode="cross_attn"` (default) or `"bipartite"`
- `set2set_steps=3`
- `nrtl_tau_mode="ref_invT"` (default), `"legacy"`, or `"abc"`
- `use_solvent_moe=True`, `solvent_moe_experts`, `solvent_moe_hidden`, `solvent_type_emb_dim`
- `use_temperature_in_encoder=False`, `use_temperature_in_interaction=False`, `use_temperature_in_nrtl_head=True` — default v2 temperature routing
- `correction_max_abs=2.0` — trust-region width for bounded residual correction
- `correction_Tm_max_delta`, `correction_dH_fraction`, `correction_tau_max_delta` — bounds for parameter-space correction
- Scale factors (`S_H`, `S_g`, `S_delta`, etc.) normalize head outputs into physically stable ranges.

### Molecular Featurization (`features.py`)

`smiles_to_graph(smiles)` → PyG `Data`. Atom features (35-dim): atomic number (one-hot over 12 elements), hybridization, formal charge, H count, aromaticity, ring membership, electronegativity, vdW radius, polarizability. Bond features (8-dim): bond type (single/double/triple/aromatic), conjugated, in ring, stereo E/Z.

## Data Layout

```
notebooks/data/
  raw/          # Downloaded source files (BigSolDBv2.1.csv, bradley_mp.csv, etc.)
  processed/    # Canonical merged/split CSVs (train.csv, val.csv, test.csv)
checkpoints/    # Saved model checkpoints (.pt files)
notebooks/      # Jupyter notebooks for data prep, training, evaluation
docs/           # Task-oriented documentation mirrors for contributors and agents
results/        # Evaluation JSONs and aggregate metrics
figures/        # Generated paper figures
```

## Testing

Tests include:
- `tests/test_physics.py` (physics layers + solver)
- `tests/test_pretrain.py` (masked atom pretrain targets)
- `tests/test_split.py` (solvent split leakage)
- `tests/test_builder.py` (gamma merge + SLE filter)
- `tests/test_integration.py` (forward/backward integration)
- `tests/test_data_integrity.py` (processed split integrity; skips if data is absent)

## Documentation Map

- `docs/architecture.md` — expanded architecture notes
- `docs/data_preparation.md` — source datasets, CSV schema, and split modes
- `docs/training.md` — canonical training paths
- `docs/evaluation.md` — evaluation scripts and comparison entry points
- `docs/baselines.md` — baseline scripts and notebooks
- `docs/reproducing_paper.md` — paper reproduction workflow
- `docs/script_reference.md` — script and notebook inventory
- `docs/repository_audit.md` — current redundancy and insufficiency audit
