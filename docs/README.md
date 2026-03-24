# Documentation Index

Use this page as the entry point for the project documentation.

## Core Guides

- `architecture.md` — model internals, forward-pass stages, and design choices
- `data_preparation.md` — source datasets, CSV schema, and split workflow
- `training.md` — CLI and notebook training paths
- `evaluation.md` — evaluation scripts and worked examples
- `baselines.md` — baseline overview and execution commands
- `reproducing_paper.md` — full paper-reproduction workflow
- `script_reference.md` — maturity map for scripts and notebooks
- `repository_audit.md` — detailed audit of structure, redundancy, and gaps

## Project Conventions

- Canonical processed data paths live under `notebooks/data/processed/`.
- `scripts/prepare_data.py` now writes all canonical split families in one run:
  `train.csv` / `val.csv` / `test.csv`,
  `train_solute.csv` / `val_solute.csv` / `test_solute.csv`,
  `train_solvent.csv` / `val_solvent.csv` / `test_solvent.csv`.
- `split_manifest.json` records the generated split variants and the selected
  primary split.
- `results/` stores generated metrics and JSON reports.
- `figures/` stores generated publication figures.
- `tables/` stores generated supplementary `.tex` and `.csv` tables.

## Recommended Reading Order

For new contributors:

1. `architecture.md`
2. `data_preparation.md`
3. `training.md`
4. `evaluation.md`
5. `script_reference.md`
6. `repository_audit.md`
