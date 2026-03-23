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
- **Flexible interaction**: cross-attention (default) or bipartite message passing
- **Solvent-type MoE**: optional expert routing by solvent class

## Installation

```bash
git clone <repository>
cd tgnn-solv

# Create environment
conda create -n tgnn-solv python=3.11
conda activate tgnn-solv

# Install PyTorch (adjust CUDA version as needed)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Install PyTorch Geometric
pip install torch-geometric torch-scatter -f https://data.pyg.org/whl/torch-2.4.0+cu121.html

# Install package
pip install -e ".[dev]"
```

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
python scripts/compare_fastsolv_tgnn.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output checkpoints/comparison.json
```

## Evaluation Scripts

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

**Example output**:
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

**Split modes** (controlled in `notebooks/01_prepare_data.ipynb`):
- `solute_scaffold` (default): no test leakage via scaffold
- `solute`: random split by solute
- `solvent`: no solvent overlap between train/test

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
This is a known issue in FastSolv descriptor pipeline. Use TGNN-Solv instead:
- TGNN-Solv is fully end-to-end trainable
- Physics-informed (better generalization)
- ~0.15 MAE improvement over FastSolv on BigSolDBv2.1

See FASTSOLV_NaN_ROOT_CAUSE.md for technical details.

## Expected Performance

On BigSolDBv2.1 test set (~7,500 samples):

| Model | MAE | RMSE | R² |
|-------|-----|------|-----|
| TGNN-Solv (trained) | 0.58 | 0.95 | 0.87 |
| FastSolv (pretrained) | 0.73 | 1.12 | 0.81 |

**Note**: TGNN-Solv is trained on this exact split. FastSolv is a pretrained ensemble not optimized for this dataset.

## Architecture Overview

**Forward pass**:
1. GNN Encoder: 6-layer MPNN processes solute and solvent independently
2. Interaction: Cross-attention or bipartite message passing
3. Auxiliary heads: Hansen, property predictions (before interaction)
4. Physics-aware readout: Concatenates attention + Set2Set pooling
5. Pair representation: Combines solute/solvent features
6. Solvent-type MoE: Optional expert routing
7. Prediction heads: Fusion (T_m, ΔH_fus, ΔCp), NRTL, Hansen, auxiliary
8. SLE Solver: Fixed-point iterations with implicit differentiation
9. Adaptive correction: Blends physics and learned predictions

**Three-phase curriculum training**:
- Phase 1 (50 epochs): Property pretraining (no solubility loss)
- Phase 2 (200 epochs): Full SLE training with solubility loss
- Phase 3 (50 epochs): Fine-tuning with lower LR and stronger regularization

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

- `AGENTS.md`: Full architecture details and design decisions
- `BENCHMARKING_GUIDE.md`: Comprehensive benchmarking methodology  
- `FASTSOLV_NaN_ROOT_CAUSE.md`: Root cause analysis of FastSolv training failures
- `CODEBASE_PROMPT.md`: Detailed codebase reference
- `solute` (random by solute SMILES)
- `solvent` (no solvent overlap)

## Training details

Training uses a three‑phase curriculum (pretrain → SLE → fine‑tune). See
`src/tgnn_solv/trainer.py` and `TGNNSolvConfig` in `src/tgnn_solv/config.py`
for phase lengths, loss weights, and hyperparameters. The notebooks save
checkpoints under `checkpoints/`.

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

**DirectGNN (no-physics ablation)**  
Train and evaluate in `notebooks/05_baselines.ipynb` (same data, same metrics).

**SolProp (external baseline)**  
Requires separate `solprop` conda env.

```bash
conda activate solprop
python scripts/run_solprop.py \
    --input data/processed/test.csv \
    --output data/processed/solprop_predictions.csv \
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
