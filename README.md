# TGNN-Solv

**Thermodynamic Graph Neural Network for Solubility Prediction**

A physics-informed GNN that predicts solid-liquid equilibrium (SLE)
solubility by learning physical parameters — not solubility directly.

## Architecture

**Key principle**: The GNN predicts *physical parameters*
(melting point, fusion enthalpy, NRTL interaction energies).
Thermodynamic equations are hardcoded and differentiable —
gradients flow through physics back to the GNN.

Forward pass: solute/solvent GNN encoders -> cross-attention -> physics heads
-> SLE solver -> adaptive correction blend.
For full details, see `AGENTS.md` and `CODEBASE_PROMPT.md`.

## Features

- **Physics-informed**: SLE + NRTL with 0 learnable parameters in the physics layer
- **Interpretable**: every intermediate ($T_m$, $\Delta H_{fus}$, $\gamma_2$, Hansen params) is physically meaningful
- **Multi-task**: jointly learns crystal properties, activity coefficients, Hansen parameters
- **Uncertainty**: MC-Dropout and Deep Ensemble support
- **Applicability domain**: Mahalanobis distance + Tanimoto similarity
- **Curriculum learning**: 3-phase training (pretrain → SLE → fine-tune)

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

## Hyperparameter tuning (Optuna)

```bash
pip install optuna
python scripts/run_optuna.py --models tgnn_solv,direct_gnn --n-trials 20
```

Or use the notebook:

```bash
jupyter notebook notebooks/08_optuna_tuning.ipynb
```

## Codebase prompt

`CODEBASE_PROMPT.md` contains the full project structure and contents of all
non-ignored text files (notebooks are included as code cells only, no outputs).
