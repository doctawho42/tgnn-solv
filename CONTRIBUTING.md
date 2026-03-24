# Contributing to TGNN-Solv

Thank you for contributing to TGNN-Solv. This document describes the expected
development workflow and project-specific constraints.

## Development Setup

1. Fork the repository and clone your fork locally.
2. Create and activate a development environment:
   ```bash
   conda create -n tgnn-solv-dev python=3.11
   conda activate tgnn-solv-dev
   ```
3. Install PyTorch with CUDA 12.1 support:
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   ```
4. Install PyTorch Geometric:
   ```bash
   pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
   ```
5. Install the package and development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
6. Run the test suite and make sure everything passes:
   ```bash
   pytest tests/ -v
   ```

## Code Style

- Use type hints for all public functions.
- Write docstrings in Google style.
- Keep the maximum line length at 100 characters.
- Run Ruff checks before submitting changes:
  ```bash
  ruff check src/ scripts/
  ```

## Pull Request Process

1. Create a feature branch from `main`.
2. Make sure `pytest tests/ -v` passes.
3. Add tests for any new functionality.
4. Update documentation when needed.
5. Open a pull request with a clear description of the changes.

## Architecture Notes

- The physics layers (`IdealSolubilityLayer`, `NRTLLayer`,
  `HansenDistanceLayer`) must not contain learnable parameters. Do not add
  `nn.Parameter` to them.
- The SLE solver uses implicit differentiation. Any change in `solver.py`
  must be validated against gradient correctness, especially with
  `tests/test_physics.py`.
- The three-phase training curriculum in `trainer.py` is sensitive. Modify it
  carefully and verify behavior with tests.

## Adding a New Baseline

1. Create a new file in `src/tgnn_solv/baselines/`.
2. Implement a class with `fit(train_df)` and
   `predict(test_df) -> np.ndarray`.
3. Expose the baseline through a documented entry point in `scripts/`,
   `notebooks/05_baselines.ipynb`, or `reproduce.sh` when appropriate.
4. Add tests under `tests/`.

## Reporting Issues

When opening an issue, include the following:

- Python version
- PyTorch version
- CUDA version
- Operating system
- Full traceback
