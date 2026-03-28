# Contributing to TGNN-Solv

This document describes the expected development workflow and the project
constraints that matter most when changing model code, scripts, or docs.

## Development Setup

```bash
git clone <your-fork-or-repo-url>
cd tgnn-solv

conda create -n tgnn-solv-dev python=3.11
conda activate tgnn-solv-dev

pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
pip install -e ".[dev]"
```

Run the test suite before opening a PR:

```bash
pytest tests/ -v
```

Useful targeted checks:

```bash
pytest tests/test_physics.py -v
pytest tests/test_integration.py -v
pytest tests/test_dataset.py -v
```

## Contribution Expectations

1. Add or update tests for any behavior change.
2. Update documentation when you change:
   - CLI arguments
   - config fields or config defaults
   - checkpoint contents
   - dataset payload keys
   - evaluation outputs or JSON schemas
   - experiment runners or result directory layouts
3. Preserve backward compatibility where practical for:
   - YAML configs
   - saved checkpoints
   - downstream JSON report consumers
4. Keep optional dependency paths optional. Scripts using FastSolv or SolProp
   must still allow `--help` and unrelated commands without those packages.

## Code Style

- Use type hints on public functions and classes.
- Keep docstrings concise and accurate.
- Prefer small, explicit helpers over hidden side effects.
- Run linting if you are touching a broad surface area:

```bash
ruff check src/ scripts/
```

## Model and Physics Constraints

- `solver.py`, `IdealSolubilityLayer`, `NRTLLayer`, and
  `HansenDistanceLayer` must remain free of learnable parameters.
- If you change the solver or implicit-diff path, validate against
  `tests/test_physics.py` and `tests/test_integration.py`.
- If you add new model inputs, make sure they are wired consistently through:
  - `dataset.py`
  - training and evaluation loaders
  - `model.py`
  - inference utilities
  - relevant scripts
- If you add new config flags, document them in:
  - `README.md`
  - `AGENTS.md`
  - the relevant file in `docs/`
- If you change resume behavior, also update:
  - `docs/training.md`
  - `docs/free_gpu_training.md`
  - `docs/script_reference.md`

## Experimental Features

The repository contains several research modes that are easy to break by
changing only one layer of the stack:

- Morgan augmentation
- descriptor augmentation for DirectGNN
- descriptor and fixed-group priors for `Hansen` / `V_m`
- crystal GC priors for `T_m` / `dH_fus` / `dCp_fus`
- GC prior calibration and residual freezing
- oracle injection
- Walden consistency penalty
- full-budget diagnostic export
- medium-budget architecture comparison

When touching one of these, check the corresponding tests:

- `tests/test_features.py`
- `tests/test_direct_gnn.py`
- `tests/test_group_contribution.py`
- `tests/test_config.py`
- `tests/test_loss.py`
- `tests/test_dataset.py`
- `tests/test_integration.py`

## Baselines and Scripts

If you add a new baseline or experiment runner:

1. Put the core implementation in `src/tgnn_solv/baselines/` or the relevant
   package module.
2. Add a CLI entry point under `scripts/` if the workflow is meant to be
   reproducible.
3. Document whether it is:
   - canonical
   - stable utility
   - research / experimental
4. Update `docs/script_reference.md` and any affected guide in `docs/`.

## Pull Requests

A good PR should include:

- the problem being solved
- the files or subsystems changed
- whether config, checkpoint, or report formats changed
- what tests or smoke checks were run
- any remaining caveats or migration notes

## Reporting Issues

Please include:

- Python version
- PyTorch version
- CUDA version if relevant
- operating system
- command used
- config file used
- full traceback or failing log excerpt
