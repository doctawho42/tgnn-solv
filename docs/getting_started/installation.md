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

If you want the maintained Streamlit GUI as well:

```bash
pip install -e ".[gui,dev]"
```

This adds the dependencies used by:

- `scripts/launch_lab.py`
- `scripts/gui/launch_lab.py`
- `tools/experiment_lab/app.py`

### 6. (Optional) Install External Baselines

For the maintained FastSolv / SolProp wrappers and benchmark helpers:
```bash
pip install -e ".[baselines]"
```

This adds the dependencies used by:

- `scripts/external/run_fastsolv.py`
- `scripts/external/run_solprop.py`
- `scripts/experiments/run_external_baseline_benchmark.py`
- `scripts/evaluation/benchmark_custom_model.py`

If you want both the GUI and the external-baseline stack:

```bash
pip install -e ".[gui,baselines,dev]"
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

The repository also ships a maintained compose layout for the current GUI and
docs surfaces:

```bash
docker compose up lab
docker compose up docs
```

Available services include:

- `lab`
  - Streamlit Experiment Lab on `http://localhost:8501`
- `docs`
  - MkDocs site on `http://localhost:8000`
- `train`
  - one tuned TGNN-Solv training run on the canonical split
- `evaluate`
  - checkpoint evaluation
- `external-benchmarks`
  - optional FastSolv / native SolProp benchmark runner

The Docker image now installs the grouped CLI layout, GUI extras, and docs
toolchain by default. Optional external baselines stay behind a separate build
switch because they are heavier and more environment-sensitive.

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

<div class="tgnn-page-nav" markdown="1">

## Next Step

- [Quick Start Workflow](quick_start.md)
- [Experiment Lab](../experiment_lab.md)
- [Troubleshooting](../troubleshooting.md)
- [Notebooks & Tutorials](../notebooks.md)

</div>
