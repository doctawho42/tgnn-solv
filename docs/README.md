# Documentation Index

Use this page as the entry point for the maintained project documentation.

## Core Guides

- `architecture.md`
  - TGNN-Solv forward path, DirectGNN baseline, Stage 0 pretraining, and key
    design choices
- `data_preparation.md`
  - raw sources, processed CSV layout, split modes, and dataset expectations
- `training.md`
  - canonical CLIs, standalone pretraining, tuned configs, resume support,
    ablations, and experiment runners
- `evaluation.md`
  - inference API, uncertainty, OOD/applicability-domain, checkpoint
    evaluation, physics diagnostics, and maintained experiment runners
- `baselines.md`
  - DirectGNN, DirectGNN+descriptors, RF, Ideal-SLE, FastSolv, and SolProp
- `reproducing_paper.md`
  - what `reproduce.sh` runs, what it skips, and how to validate outputs
- `script_reference.md`
  - maturity map for scripts and notebooks
- `repository_audit.md`
  - current strengths, known gaps, and structural caveats

## Top-Level Companion Docs

- `../README.md`
  - high-level project overview and quick-start commands
- `../AGENTS.md`
  - compact repo notes for coding agents and terminal-driven contributors
- `../CONTRIBUTING.md`
  - contribution workflow and validation checklist
- `../scripts/README.md`
  - grouped CLI layout and compatibility-wrapper policy
- `../src/tgnn_solv/README.md`
  - grouped internal package layout and preferred import surface

## Recommended Reading Order

For new contributors:

1. `architecture.md`
2. `data_preparation.md`
3. `training.md`
4. `evaluation.md`
5. `baselines.md`
6. `script_reference.md`
7. `free_gpu_training.md` if you need resumable cloud runs

## Project Conventions

- Canonical processed splits live under `notebooks/data/processed/`.
- `scripts/data/prepare_data.py` writes all supported split families in one run.
- Optional molecular features and priors are computed in `TGNNSolvDataset` at
  load time; they are not stored in the processed CSVs.
- Train-only calibration and normalization steps still happen later in the
  training scripts:
  - `T_m_gc` affine calibration for GC-prior crystal runs
  - RDKit descriptor mean/std normalization for DirectGNN augmentation
- Some maintained capabilities are library-first rather than CLI-first:
  - standalone encoder pretraining via `tgnn_solv.pretrain`
  - uncertainty via `tgnn_solv.uncertainty`
  - inference-time OOD screening via `tgnn_solv.domain`
- Generated metrics and experiment artifacts live under `results/`.
- Figures live under `figures/`, supplementary tables under `tables/`, and
  checkpoints under `checkpoints/`.
- For Python code navigation, prefer the grouped namespace surface documented in
  `src/tgnn_solv/README.md`; legacy flat imports remain valid for compatibility.
