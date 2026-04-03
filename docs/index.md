# TGNN-Solv

Physics-informed Graph Neural Network for solid-liquid equilibrium (SLE) solubility prediction.

## Overview

TGNN-Solv is a framework that:

- **Predicts crystal and interaction parameters** using graph neural networks
- **Passes them through a differentiable thermodynamic solver**
- **Trains end-to-end** through the physics bottleneck

The repository also contains key baselines for comparison:

- **TGNN-Solv**: physics-first GNN with SLE + NRTL
- **DirectGNN**: matched GNN backbone with direct `ln(x2)` prediction
- **DirectGNN + descriptors**: DirectGNN plus shared RDKit descriptor side-channel
- **RF baselines**: Random Forest on RDKit descriptors, Morgan fingerprints, or both

## Quick Links

- 📖 [Read the full documentation](architecture.md)
- 🚀 [Installation & Setup](getting_started/installation.md)
- ⚡ [Quick Start Workflow](getting_started/quick_start.md)
- 🏗️ [Architecture Details](architecture.md)
- 📊 [Evaluation & Inference](evaluation.md)

## Getting Started

### Installation

```bash
git clone https://github.com/doctawho42/tgnn-solv.git
cd tgnn-solv

conda create -n tgnn-solv python=3.11
conda activate tgnn-solv

pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
pip install -e ".[dev]"
```

### Basic Workflow

```bash
# Prepare data
python scripts/data/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42

# Train model
python scripts/training/train.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --device cuda
```

## Key Features

✨ **Physics-Informed**: Differentiable SLE + NRTL thermodynamic solver  
🧠 **Advanced Architecture**: Cross-attention, dual-graph encoders, parameter correction heads  
📈 **Comprehensive Baselines**: DirectGNN, Random Forest, FastSolv, SolProp  
🔧 **Production Ready**: Inference API, uncertainty estimation, OOD detection  
🎓 **Research Focused**: Multiple config variants, ablations, reproducibility tools  

## Citation

If you use TGNN-Solv in your research, please cite the corresponding paper.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
