# Documentation Index

For the published documentation site, start from `docs/index.md`.

This file is the repo-internal map of the same maintained documentation set.

## Site Pages

- `docs/index.md`
  - public site landing page, project overview, and reading paths
- `docs/getting_started/installation.md`
  - environment setup and dependency notes
- `docs/getting_started/quick_start.md`
  - shortest maintained end-to-end workflow
- `docs/notebooks.md`
  - notebook inventory and mapping to the docs
- `docs/architecture.md`
  - TGNN-Solv forward path, DirectGNN baseline, Stage 0 pretraining, and key
    design choices
- `docs/data_preparation.md`
  - raw sources, processed CSV layout, split modes, and dataset expectations
- `docs/training.md`
  - canonical CLIs, standalone pretraining, tuned configs, resume support,
    ablations, and experiment runners
- `docs/evaluation.md`
  - inference API, uncertainty, OOD/applicability-domain, checkpoint
  evaluation, physics diagnostics, and maintained experiment runners
- `docs/baselines.md`
  - DirectGNN, DirectGNN+descriptors, RF, Ideal-SLE, FastSolv, and SolProp
- `docs/config_cookbook.md`
  - recommended config selection by use case
- `docs/results.md`
  - benchmark hierarchy and interpretation of committed result bundles
- `docs/experiments.md`
  - maintained benchmark and comparison runners, output layouts, and runner
    selection guidance
- `docs/model_zoo.md`
  - checkpoint conventions and local artifact layouts
- `docs/reproducing_paper.md`
  - what `reproduce.sh` runs, what it skips, and how to validate outputs
- `docs/script_reference.md`
  - maturity map for scripts and notebooks
- `docs/faq.md`
  - short answers to recurring questions
- `docs/troubleshooting.md`
  - common environment and training failures
- `docs/repository_audit.md`
  - current strengths, known gaps, and structural caveats
- `docs/contributing.md`
  - public-site contributor summary with a link to the full root guide

## Top-Level Companion Docs

- `README.md`
  - high-level project overview and quick-start commands
- `AGENTS.md`
  - compact repo notes for coding agents and terminal-driven contributors
- `CONTRIBUTING.md`
  - contribution workflow and validation checklist
- `scripts/README.md`
  - grouped CLI layout and compatibility-wrapper policy
- `src/tgnn_solv/README.md`
  - grouped internal package layout and preferred import surface

## Recommended Reading Order

For site readers:

1. `docs/index.md`
2. `docs/getting_started/installation.md`
3. `docs/getting_started/quick_start.md`
4. `docs/architecture.md`
5. `docs/training.md`
6. `docs/evaluation.md`
7. `docs/experiments.md`

For contributors after that:

1. `docs/script_reference.md`
2. `docs/free_gpu_training.md` if you need resumable cloud runs
3. `docs/repository_audit.md`
4. `CONTRIBUTING.md`

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
