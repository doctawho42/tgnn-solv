# Installation

## System Requirements

- Python ≥ 3.10 (tested with 3.11)
- CUDA 12.1 (optional, for GPU acceleration)
- 8GB+ RAM recommended

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/doctawho42/tgnn-solv.git
cd tgnn-solv
```

### 2. Create Conda Environment

```bash
conda create -n tgnn-solv python=3.11
conda activate tgnn-solv
```

### 3. Install PyTorch

Choose based on your system:

**With GPU (CUDA 12.1):**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

**CPU only:**
```bash
pip install torch
```

### 4. Install PyTorch Geometric

```bash
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
```

### 5. Install TGNN-Solv

```bash
pip install -e ".[dev]"
```

This installs:
- Core dependencies: `torch-geometric`, `rdkit`, `numpy`, `pandas`, `requests`, `tqdm`
- Development tools: `jupyter`, `matplotlib`, `scikit-learn`, `pytest`, `optuna`

### 6. (Optional) Install External Baselines

For FastSolv baseline:
```bash
pip install -e ".[baselines]"
```

## Verification

Verify installation:

```python
import torch
import torch_geometric
from tgnn_solv import __version__

print(f"PyTorch: {torch.__version__}")
print(f"PyG: {torch_geometric.__version__}")
print(f"TGNN-Solv: {__version__}")
```

## Docker Setup (Alternative)

If you prefer containerization:

```bash
docker build -t tgnn-solv .
docker run --gpus all -it tgnn-solv bash
```

## Troubleshooting

### CUDA/GPU Issues

```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall with specific CUDA version
pip install torch --force-reinstall --index-url https://download.pytorch.org/whl/cu121
```

### RDKit Import Errors

```bash
# RDKit sometimes needs conda installation
conda install -c conda-forge rdkit
```

### Out of Memory

Reduce batch size in config files or use CPU-only mode for testing.