# TGNN-Solv: Physics-Informed Graph Neural Network for Solubility Prediction

**Thermodynamic Graph Neural Network for Solubility Prediction**

A physics-informed GNN that predicts solid-liquid equilibrium (SLE) solubility by learning physical parameters — not solubility directly. Gradients flow through hardcoded thermodynamic equations back to the GNN for end-to-end training.

## Key Features

- **Physics-informed**: SLE + NRTL with 0 learnable parameters in physics layer
- **Interpretable**: all intermediates (T_m, ΔH_fus, γ_2, Hansen params) are physically meaningful
- **Multi-task**: jointly learns crystal properties, activity coefficients, Hansen parameters
- **Uncertainty quantification**: MC-Dropout and Deep Ensemble support
- **Applicability domain**: Mahalanobis distance + Tanimoto similarity
- **Curriculum learning**: 3-phase training (pretrain → SLE → fine-tune)
- **Temperature-aware state block**: crystal-property heads stay temperature-invariant by default, while temperature enters the NRTL/state block explicitly
- **Parameter-space correction**: the correction path adjusts physical parameters and re-solves SLE instead of bypassing physics with a free direct head
- **Flexible interaction**: cross-attention (default) or bipartite message passing
- **Solvent-type MoE**: optional expert routing by solvent class

## Installation

```bash
git clone https://github.com/doctawho42/tgnn-solv.git
cd tgnn-solv

# Create environment
conda create -n tgnn-solv python=3.11
conda activate tgnn-solv

# Install PyTorch (adjust CUDA version as needed)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Install PyTorch Geometric
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html

# Install package
pip install -e ".[dev]"
```

## Documentation Map

- `docs/README.md`: entry point for the project documentation set
- `docs/architecture.md`: model architecture and design decisions
- `docs/data_preparation.md`: source datasets, CSV schema, and split modes
- `docs/training.md`: notebook and CLI training workflows
- `docs/evaluation.md`: evaluation scripts and worked examples
- `docs/baselines.md`: baseline overview and execution paths
- `docs/reproducing_paper.md`: end-to-end reproduction workflow
- `docs/script_reference.md`: script and notebook maturity map
- `docs/repository_audit.md`: detailed structural audit and open gaps
- `AGENTS.md`: condensed architecture and workflow notes for coding agents
- `BENCHMARKING_GUIDE.md`: benchmarking methodology and interpretation

## Quick Start

### 1. Prepare Data

```bash
jupyter notebook notebooks/01_prepare_data.ipynb
```

Downloads BigSolDBv2.1 (~120k solubility records) and auxiliary data (melting points, Hansen parameters, NIST values).

### 2. Train Model

```bash
jupyter notebook notebooks/02_train.ipynb
```

Trains TGNN-Solv with 3-phase curriculum learning (50 → 200 → 50 epochs).

### 3. Make Predictions

```python
from tgnn_solv.inference import load_model, predict_solubility, interpret_prediction

model, cfg = load_model("checkpoints/tgnn_solv_trained.pt")

result = predict_solubility(
    model,
    solute_smiles="CC(=O)Nc1ccc(O)cc1",  # paracetamol
    solvent_smiles="CCO",                 # ethanol
    T=298.15
)
print(interpret_prediction(result))
```

### 4. Evaluate Model Performance

**Option A: Full diagnostic evaluation**

```bash
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output benchmarks/evaluation.json
```

**Option B: Quick evaluation on subset**

```bash
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --n-samples 500 \
    --output benchmarks/quick_eval.json
```

**Option C: Compare with FastSolv baseline (pretrained)**

```bash
python scripts/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics checkpoints/fastsolv_compare.json
```

**Option D: Compare the default shared backbone against the `split_late`
encoder**

```bash
python scripts/run_seeds.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/multi_seed_results.json

python scripts/run_seeds.py \
    --config configs/paper_config_split_late.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/split_late_multi_seed_results.json
```

The dedicated `paper_config_split_late.yaml` file keeps the paper setup fixed
and switches only the encoder from `shared_residual` to `split_late`.

## Evaluation Scripts

There are two complementary evaluation entry points:

- `scripts/evaluate_complete.py`
  - lightweight checkpoint evaluation,
  - emits `true_ln_x2` / `pred_ln_x2` arrays for parity and residual plots,
  - best default for quick reports and figure generation.
- `scripts/benchmark_tgnn_solv.py`
  - richer `Evaluator`-backed benchmark,
  - best choice for detailed stratified benchmarking and model-to-model
    comparison.

Both scripts now emit a shared JSON report schema with:

- `metadata`
- `overall`
- `stratified.temperature`
- `stratified.solubility`
- `stratified.solvent_type`
- `stratified.solvent`
- `stratified.aux_data`
- optional `predictions.true_ln_x2` / `predictions.pred_ln_x2`

Legacy aliases such as `by_temperature`, `by_solubility_range`,
`by_solvent_type`, `true_ln_x2`, and `pred_ln_x2` are preserved for backward
compatibility.

## Optional Morgan Fingerprints

The maintained codebase now supports optional Morgan fingerprint augmentation
for both `TGNN-Solv` and `DirectGNN` through `TGNNSolvConfig`:

- `use_morgan_features`
- `morgan_radius`
- `morgan_n_bits`
- `morgan_hidden_dim`

This path injects fingerprints into the learned molecular representations
before the thermodynamic heads and pair block. It does not replace the
physics-informed solver path.

## Optional Descriptor Priors

The maintained codebase also supports an experimental descriptor-conditioned
`prior + residual` path for the `Hansen` and `V_m` heads:

- `use_descriptor_priors`
- `descriptor_prior_hidden_dim`
- `descriptor_prior_hansen_residual_max`
- `descriptor_prior_vm_residual_max`
- `descriptor_prior_reg_weight`

When enabled, fixed RDKit descriptors are converted into coarse priors and the
graph heads learn only bounded residuals around those priors. This path is
currently experimental, is not enabled in the paper configs by default, and is
mutually exclusive with `use_group_priors`.

## Optional Fixed Group Priors

The codebase also supports a stricter fixed fragment-count
group-contribution prior path for the same `Hansen` and `V_m` heads:

- `use_group_priors`
- `group_prior_hansen_residual_max`
- `group_prior_vm_residual_max`
- `group_prior_reg_weight`

When enabled, the prior is a deterministic function of fixed molecular
group counts and the graph branch learns only a bounded residual on top.
This is intended as a cleaner ablation than the learned descriptor-prior
adapter when you want to test whether explicit fixed priors help. This mode is
mutually exclusive with `use_descriptor_priors`.

### evaluate_complete.py

Comprehensive model evaluation with detailed metrics:

```bash
python scripts/evaluate_complete.py \
    --test-data FILE           # Path to test CSV (default: notebooks/data/processed/test.csv)
    --tgnn-checkpoint FILE     # Path to model checkpoint (default: checkpoints/tgnn_solv_trained.pt)
    --output FILE              # Output JSON path (default: benchmarks/complete_evaluation.json)
    --n-samples N              # Evaluate on N random samples (optional, default: all)
    --verbose                  # Verbose logging
```

**Output includes**:
- Overall metrics: MAE, RMSE, R², Pearson correlation, median error, max error, Q95 error
- Stratified by temperature: (<298K, 298-323K, 323-373K, >373K)
- Stratified by solubility: (very low, low, medium, high)
- JSON format for automated analysis

**Example output** (illustrative schema only; values depend on the checkpoint
and split you evaluate):
```json
{
  "overall": {
    "n_samples": 7500,
    "mae": 0.58,
    "rmse": 0.95,
    "r2": 0.87,
    "pearson_r": 0.93
  },
  "by_temperature": {
    "T_298_to_323K": {
      "n_samples": 3000,
      "mae": 0.51,
      "r2": 0.89
    }
  },
  "by_solubility": {
    "low_solubility": {
      "n_samples": 2500,
      "mae": 0.62,
      "r2": 0.85
    }
  }
}
```

### compare_fastsolv_tgnn.py

Comparison with FastSolv baseline:

```bash
python scripts/compare_fastsolv_tgnn.py \
    --test-data FILE            # Path to test CSV
    --tgnn-checkpoint FILE      # Path to TGNN model
    --fastsolv-checkpoint FILE  # Path to FastSolv ONNX (optional)
    --output FILE               # Output JSON path
    --n-samples N               # Number of samples (optional)
    --no-fastsolv               # Skip FastSolv (if unavailable)
```

**Note on FastSolv**: Uses only pretrained FastSolv for inference. Training FastSolv from scratch has unfixable NaN issues in descriptor computation (see FASTSOLV_NaN_ROOT_CAUSE.md). TGNN-Solv is recommended for custom training.

For the main FastSolv wrapper, see `scripts/run_fastsolv.py` and
`docs/baselines.md`.

## Data Format

Processed CSVs are written to `notebooks/data/processed/{train,val,test}.csv`.

**Required columns**:
- `solute_smiles`: canonical SMILES string
- `solvent_smiles`: canonical SMILES string
- `temperature`: temperature in Kelvin
- `ln_x2`: log mole fraction (target)
- `has_solubility`: boolean flag (true if solubility is available)

**Optional columns** (for auxiliary training):
- `T_m`: melting point (K)
- `has_T_m`: boolean flag
- `dH_fus`: fusion enthalpy (J/mol)
- `has_dH_fus`: boolean flag
- `hansen_d`, `hansen_p`, `hansen_h`: Hansen parameters
- `has_hansen`: boolean flag
- `ln_gamma_inf`: infinite dilution activity coefficient
- `has_gamma_inf`: boolean flag

**Split modes** (available in `scripts/prepare_data.py` and `notebooks/01_prepare_data.ipynb`):
- `solute_scaffold` (default): no test leakage via scaffold
- `solute`: random split by solute
- `solvent`: no solvent overlap between train/test

One `scripts/prepare_data.py` run now writes all three split families plus
`split_manifest.json`. The canonical filenames are:

- scaffold: `train.csv`, `val.csv`, `test.csv`
- solute: `train_solute.csv`, `val_solute.csv`, `test_solute.csv`
- solvent: `train_solvent.csv`, `val_solvent.csv`, `test_solvent.csv`

For fair baseline reporting against older work that did not use scaffold
holdout, use `scripts/run_split_comparisons.py` and report the `solute` split
alongside the stricter `solute_scaffold` split.

## Command Examples

### Example 1: Quick diagnostic (2 minutes)

```bash
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --n-samples 100 \
    --output bench_quick.json
```

### Example 2: Full evaluation for paper (15 minutes)

```bash
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output paper_results.json
```

Then parse results:

```python
import json
with open('paper_results.json') as f:
    data = json.load(f)
    
print(f"Overall MAE: {data['overall']['mae']:.4f}")
print(f"Overall R²:  {data['overall']['r2']:.4f}")
print(f"Test samples: {data['overall']['n_samples']}")

for temp_range, metrics in data['by_temperature'].items():
    if metrics['n_samples'] > 0:
        print(f"{temp_range}: MAE={metrics['mae']:.4f}, R²={metrics['r2']:.4f}")
```

### Example 3: Compare model versions

```bash
# Train two models
jupyter notebook notebooks/02_train.ipynb  # Save as best_v1.pt
# (modify hyperparams and retrain) → Save as best_v2.pt

# Evaluate both
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/best_v1.pt \
    --output eval_v1.json

python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/best_v2.pt \
    --output eval_v2.json
```

### Example 4: Evaluate on custom data

```bash
# Prepare your CSV with required columns
python scripts/evaluate_complete.py \
    --test-data your_custom_data.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output custom_results.json
```

### Example 5: Filter and evaluate on subset

```python
import pandas as pd

# Load and filter test set
df = pd.read_csv('notebooks/data/processed/test.csv')
ethanol_only = df[df['solvent_smiles'] == 'CCO'].copy()
ethanol_only.to_csv('test_ethanol.csv', index=False)

print(f"Created test set with {len(ethanol_only)} ethanol samples")
```

```bash
# Evaluate on filtered set
python scripts/evaluate_complete.py \
    --test-data test_ethanol.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output ethanol_eval.json
```

## Troubleshooting

### "ImportError: No module named 'tgnn_solv'"
```bash
pip install -e .
```

### "CUDA out of memory" 
Edit config in scripts or notebook:
```python
hidden_dim = 128       # reduce from 256
n_gnn_layers = 4      # reduce from 6
batch_size = 32       # reduce from 64
```

### "All predictions are NaN"
Usually caused by invalid SMILES. Verify:
```python
from rdkit import Chem
mol = Chem.MolFromSmiles(your_smiles)
assert mol is not None, f"Invalid SMILES: {your_smiles}"
```

### "Model not converging during training"
Check data quality and overfitting:
```bash
python scripts/diagnose_training.py overfit --sample-size 1000 --epochs 200
```

### "FastSolv predictions are NaN"
This usually reflects the known FastSolv descriptor-pipeline instability when
training from scratch. Preferred paths:
- use `python scripts/run_fastsolv.py predict ...` for pretrained FastSolv inference,
- use `python scripts/run_fastsolv.py compare ...` for TGNN-vs-FastSolv comparison,
- use TGNN-Solv or SolProp for custom training workflows instead of relying on
  FastSolv retraining.

See FASTSOLV_NaN_ROOT_CAUSE.md for technical details.

## Benchmarking Status

The repository does not currently ship a single blessed checkpoint or a
committed benchmark JSON that should be treated as the canonical scorecard.
Authoritative metrics depend on:

- the split protocol (`solute_scaffold`, `solute`, `solvent`),
- the exact checkpoint or seed sweep,
- optional baseline availability (for example FastSolv / SolProp),
- and the current training configuration.

Use one of the following to generate the numbers that matter for your setup:

- `python scripts/evaluate_complete.py ...` for lightweight checkpoint metrics,
- `python scripts/benchmark_tgnn_solv.py ...` for richer stratified reporting,
- `python scripts/run_split_comparisons.py ...` for fair split-wise comparison,
- `bash reproduce.sh` for the broader paper-style artifact set.

## Architecture Overview

**Forward pass**:
1. GNN Encoder: the default `shared_residual` path uses one shared 6-layer MPNN plus lightweight role adapters; an optional `split_late` variant keeps early layers shared and splits the last few layers by role
2. Auxiliary heads: crystal and Hansen properties, plus a lightweight `V_m` auxiliary prediction, are computed from temperature-invariant pre-interaction representations
3. Interaction: Cross-attention or bipartite message passing
4. Physics-aware readout: Concatenates attention + Set2Set pooling
5. Optional Morgan augmentation: Morgan fingerprints can be injected into the learned molecular representations before the thermodynamic heads and pair block
6. Optional molecular priors: descriptor-conditioned priors or fixed group-count priors can provide coarse `Hansen` / `V_m` estimates, and the graph path learns only bounded residuals around them; the two prior modes are mutually exclusive
7. Pair representation: Combines solute/solvent features
8. Solvent-type MoE: Optional expert routing
9. Prediction heads: Fusion (`T_m`, `ΔH_fus`, and by default a fixed `ΔCp_fus = 0` unless explicit `ΔCp_fus` prediction is enabled), NRTL, Hansen, auxiliary; the canonical configuration uses a compact `tau(T_ref)` + inverse-temperature-slope NRTL parameterization, and temperature is injected explicitly into the NRTL/state block
10. SLE Solver: Residual-controlled fixed-point iterations with implicit differentiation
11. Adaptive correction: Bounded parameter-space correction around the physics prediction, followed by a second SLE solve

**Three-phase curriculum training**:
- Phase 1 (50 epochs): Property pretraining (no solubility loss)
- Phase 2 (200 epochs): Full SLE training with solubility loss; maintained configs keep auxiliary losses light and unfreeze the correction path via `phase2_correction_unfreeze_epoch`
- Phase 3 (50 epochs): Fine-tuning with lower LR and moderate regularization

The canonical training CLI also uses pair-aware batching, so repeated
`(solute, solvent)` measurements at different temperatures are grouped into the
same training minibatches when possible. This makes the temperature ranking and
local van't Hoff regularizers active by construction rather than only by chance.

## Citation

If you use TGNN-Solv, please cite:

```bibtex
@article{tgnn-solv-2026,
  title={Physics-Informed Graph Neural Networks for Solubility Prediction},
  author={...},
  journal={...},
  year={2026}
}
```

## Related Documents

- `docs/README.md`: Navigation index for the full docs set
- `docs/script_reference.md`: Script and notebook inventory
- `docs/repository_audit.md`: Detailed audit of repository structure
- `AGENTS.md`: Full architecture details and design decisions
- `BENCHMARKING_GUIDE.md`: Comprehensive benchmarking methodology
- `FASTSOLV_NaN_ROOT_CAUSE.md`: Root cause analysis of FastSolv training failures
- `CODEBASE_PROMPT.md`: Detailed codebase reference

## Training details

Training uses a three‑phase curriculum (pretrain → SLE → fine‑tune). See
`src/tgnn_solv/trainer.py` and `TGNNSolvConfig` in `src/tgnn_solv/config.py`
for phase lengths, loss weights, pair-aware temperature batching controls, and
other hyperparameters. The notebooks save checkpoints under `checkpoints/`.

## Evaluation and comparison

Metrics are reported on `ln_x2` (MAE, RMSE, R²). The FastSolv wrapper converts
between `ln_x2` and `logS` internally when needed.

Compare FastSolv vs TGNN‑Solv on the same filtered rows:

```bash
python scripts/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics checkpoints/fastsolv_compare.json \
    --preds notebooks/data/processed/fastsolv_vs_tgnn.csv
```

## Hyperparameter tuning (Optuna)

```bash
pip install optuna
python scripts/run_optuna.py --models tgnn_solv,direct_gnn --n-trials 20
```

Or use the notebook:

```bash
jupyter notebook notebooks/08_optuna_tuning.ipynb
```

## Diagnostics

Quick dataset stats + overfit check:

```bash
python scripts/diagnose_training.py stats
python scripts/diagnose_training.py overfit --sample-size 1000 --epochs 200
```

## Baselines

**FastSolv (descriptor baseline)**  
Requires `fastsolv` (installed via `pip install fastsolv`).

```bash
# Predict with the pretrained FastSolv ensemble
python scripts/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output notebooks/data/processed/fastsolv_pred.csv

# Train FastSolv on your splits
python scripts/run_fastsolv.py train \
    --train notebooks/data/processed/train.csv \
    --val notebooks/data/processed/val.csv \
    --test notebooks/data/processed/test.csv \
    --outdir checkpoints/fastsolv_run \
    --metrics checkpoints/fastsolv_run/metrics.json

# Compare FastSolv vs TGNN-Solv metrics
python scripts/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics checkpoints/fastsolv_compare.json
```

FastSolv retraining remains available, but pretrained prediction / comparison is
the safer default because descriptor-path NaNs can still break custom
retraining on new splits.

**DirectGNN (no-physics ablation)**  
Standalone CLI:

```bash
python scripts/train_directgnn.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn.pt
```

For exploratory inspection and manual comparisons, `notebooks/05_baselines.ipynb`
remains useful.

**Split-wise comparison across scaffold / solute / solvent protocols**

```bash
python scripts/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

This runner writes per-split multi-seed artifacts under
`results/split_comparisons/` and an aggregate summary at
`results/split_comparisons.json`. The supplementary pipeline can turn this into
`Table S9`, and `generate_paper_figures.py` can render `Figure S2` when the
result file is available.

**Ablation study**

```bash
python scripts/run_ablation.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 3 \
    --output results/ablation.json
```

**SolProp (external baseline)**  
Requires separate `solprop` conda env.

```bash
conda activate solprop
python scripts/run_solprop.py \
    --input notebooks/data/processed/test.csv \
    --output notebooks/data/processed/solprop_predictions.csv \
    --temperature_dependent
```

Calibrate SolProp to your splits (linear correction on ln(x₂)) and evaluate:

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
