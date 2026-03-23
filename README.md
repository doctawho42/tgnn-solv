# TGNN-Solv

**Thermodynamic Graph Neural Network for Solubility Prediction**

A physics-informed GNN that predicts solid-liquid equilibrium (SLE)
solubility by learning physical parameters — not solubility directly.

## Architecture

**Key principle**: The GNN predicts *physical parameters*
(melting point, fusion enthalpy, NRTL interaction energies).
Thermodynamic equations are hardcoded and differentiable —
gradients flow through physics back to the GNN.

Forward pass: solute/solvent GNN encoders -> interaction (cross-attn or
bipartite MP) -> physics heads -> SLE solver -> adaptive correction blend.

## Features

- **Physics-informed**: SLE + NRTL with 0 learnable parameters in the physics layer
- **Interpretable**: every intermediate ($T_m$, $\Delta H_{fus}$, $\gamma_2$, Hansen params) is physically meaningful
- **Multi-task**: jointly learns crystal properties, activity coefficients, Hansen parameters
- **Uncertainty**: MC-Dropout and Deep Ensemble support
- **Applicability domain**: Mahalanobis distance + Tanimoto similarity
- **Curriculum learning**: 3-phase training (pretrain → SLE → fine-tune)
- **Solvent-type MoE**: optional expert routing by solvent class
- **Interaction modes**: default cross-attention, optional bipartite message passing

## Installation

```bash
git clone https://github.com/doctawho42/tgnn-solv.git
cd tgnn-solv

# Create environment
conda create -n tgnn-solv python=3.11
conda activate tgnn-solv

# PyTorch (adjust CUDA version)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# PyG
pip install torch-geometric torch-scatter \
    -f https://data.pyg.org/whl/torch-2.4.0+cu121.html

# Install package
pip install -e ".[dev]"
```

## Quick start

### 1. Prepare data

```bash
jupyter notebook notebooks/01_prepare_data.ipynb
```
Downloads BigSolDBv2.1 (~120k records) and auxiliary data.

### 2. Train

```bash
jupyter notebook notebooks/02_train.ipynb
```

### 3. Predict

```python
from tgnn_solv.inference import load_model, predict_solubility, interpret_prediction

model, cfg = load_model("checkpoints/tgnn_solv_trained.pt")

result = predict_solubility(
    model,
    solute_smiles="CC(=O)Nc1ccc(O)cc1",   # paracetamol
    solvent_smiles="CCO",                   # ethanol
    T=298.15,
)
print(interpret_prediction(result))
```

### 4. Evaluate

```bash
jupyter notebook notebooks/04_evaluation.ipynb
```

## Data and splits

Processed CSVs are written to `notebooks/data/processed/{train,val,test}.csv`.
Minimum required columns for training/evaluation scripts:

- `solute_smiles`, `solvent_smiles` (canonical SMILES)
- `temperature` (Kelvin)
- `ln_x2` (log mole fraction)
- `has_solubility` (boolean)

Split mode is controlled in `notebooks/01_prepare_data.ipynb` via `scaffold_split(...)`.
Supported modes:

- `solute_scaffold` (default, no scaffold leakage)
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
