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

Useful repo-integration smoke checks:

```bash
python scripts/experiments/reproduce_paper.py --profile core --list-steps
python scripts/experiments/reproduce_paper.py --profile core --step prepare_data --dry-run
mkdocs build
```

## Contribution Expectations

1. Add or update tests for any behavior change.
2. Update documentation when you change:
   - CLI arguments
   - config fields or config defaults
   - checkpoint contents
   - dataset payload keys
   - evaluation outputs or JSON schemas
   - artifact sidecars such as `run_manifest.json`, `benchmark_card.json`, or
     checkpoint `*.model_card.json`
   - experiment runners or result directory layouts
3. Preserve backward compatibility where practical for:
   - YAML configs
   - saved checkpoints
   - downstream JSON report consumers
   - canonical benchmark bundle sidecars
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
- If you change the canonical benchmark contract, also update:
  - `BENCHMARKING_GUIDE.md`
  - `docs/results.md`
  - `docs/baselines.md`
  - `docs/experiment_lab.md`
- For new internal imports, prefer the grouped namespace surface where it keeps
  call sites clearer:
  - `tgnn_solv.core.*`
  - `tgnn_solv.chemistry.*`
  - `tgnn_solv.models.*`
  - `tgnn_solv.physics.*`
  - `tgnn_solv.training.*`
  - `tgnn_solv.evaluation.*`
  - `tgnn_solv.research.*`
- Keep the legacy flat modules in place unless you are explicitly removing a
  compatibility layer and have audited downstream imports.
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
2. If you are adding a new non-baseline library module, place the real
   implementation where it fits best and expose it through the grouped
   namespace surface in `src/tgnn_solv/`.
3. Add the human-facing CLI entry point under the grouped `scripts/`
   layout:
   - `scripts/data/`
   - `scripts/training/`
   - `scripts/evaluation/`
   - `scripts/experiments/`
   - `scripts/external/`
4. Only keep or add a top-level `scripts/*.py` wrapper when you need backward
   compatibility with existing imports, tests, or automation.
5. Document whether it is:
   - canonical
   - stable utility
   - research / experimental
6. Update `docs/script_reference.md`, `scripts/README.md`, `src/tgnn_solv/README.md`, and any affected
   guide in `docs/`.
7. If the new CLI emits first-class artifacts, prefer machine-readable sidecars
   rather than only prose notes.

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
