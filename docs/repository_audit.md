# Repository Audit

This audit summarizes the current state of the repository structure, with
special attention to documentation, scripts, notebooks, and duplication across
entry points.

## Executive Summary

The repository is now structurally coherent around a single canonical data
layout and a clear core workflow:

1. `scripts/prepare_data.py`
2. `scripts/train.py`
3. `scripts/run_seeds.py`
4. `scripts/evaluate_complete.py`
5. `scripts/generate_paper_figures.py`
6. `reproduce.sh`

The biggest historical issues were inconsistent path conventions, CLI scripts
that only worked after `pip install -e .`, and documentation that described a
slightly more complete automation story than the code actually provided.

The follow-up hardening passes closed several of those gaps:

- `scripts/_bootstrap.py` now centralizes repo-root and `src/` path setup.
- DirectGNN and ablation workflows now have dedicated CLI entry points.
- `reproduce.sh` now orchestrates additional paper-analysis steps, including
  error analysis, learning curves, temperature extrapolation, statistical
  tests, and supplementary tables.

## Strengths

- The architecture is conceptually clean and well separated into model,
  physics, data, evaluation, and baseline modules.
- The notebook suite covers the major research workflows.
- The data pipeline has a clear primary split (`solute_scaffold`) and explicit
  optional comparison splits (`*_solute.csv`).
- The solver, physics tests, and integration tests make the high-risk numerical
  parts of the project more trustworthy than the average research repository.

## Issues Found During Audit

### 1. Script Bootstrap Inconsistency

Before this audit pass, several scripts assumed the package had already been
installed, while others added `src/` to `sys.path` manually. This meant that
some commands failed when run directly from a clean checkout.

High-signal examples:

- `scripts/train.py`
- `scripts/diagnose_training.py`
- `scripts/run_optuna.py`
- `scripts/compare_models.py`

Status:

- Fixed by standardizing direct-from-checkout `src/` bootstrap in the affected
  scripts.

### 2. Optional Dependency Handling Was Too Eager

Some baseline scripts imported optional packages at module import time. That
made even `--help` unusable when those dependencies were not installed.

High-signal examples:

- `scripts/run_fastsolv.py`
- `scripts/run_solprop.py`

Status:

- Fixed by deferring runtime imports until the relevant command executes.

### 3. Benchmark Script Drifted from the Core APIs

`scripts/benchmark_tgnn_solv.py` had drifted from the current data and
evaluation APIs:

- it referenced a non-existent `DataBuilder.build_dataset_dict(...)`,
- it expected outdated `Evaluator` output keys,
- it duplicated benchmark logic that no longer matched the live code.

Status:

- Fixed to use `TGNNSolvDataset`, `collate_fn`, and the current `Evaluator`
  output schema.

### 4. Evaluation Artifacts Were Not Figure-Friendly

`scripts/generate_paper_figures.py` was designed to consume prediction arrays,
but `scripts/evaluate_complete.py` did not export them.

Status:

- Fixed by exporting `true_ln_x2` and `pred_ln_x2` arrays from
  `scripts/evaluate_complete.py`.

### 5. Documentation Had Real but Recoverable Drift

The docs previously mixed:

- `data/...` and `notebooks/data/...`,
- canonical and auxiliary split conventions,
- existing and hypothetical scripts,
- lightweight utilities and full automation claims.

Status:

- Canonical paths are now aligned on `notebooks/data/...`.
- Missing script references were removed or rewritten as optional/manual
  workflows.
- Documentation now distinguishes between canonical, optional, and legacy
  scripts.

## Redundancy Analysis

### Intentional Overlap

Some overlap is justified and useful:

- `evaluate_complete.py` and `benchmark_tgnn_solv.py`
  - one is lightweight and plot-oriented,
  - the other is `Evaluator`-based and benchmark-oriented.
- notebook workflows and CLI workflows
  - notebooks support exploration,
  - CLI scripts support reproducibility.

### Accidental or Costly Overlap

The following overlaps remain and should be considered for future
consolidation:

- `scripts/run_fastsolv.py compare` vs `scripts/compare_fastsolv_tgnn.py`
  - both compare TGNN-Solv and FastSolv,
  - they differ more in implementation style than in user-facing purpose.
- repeated metric/report formatting across evaluation and benchmark scripts
  - the outputs are related but not fully unified.

## Insufficiency Analysis

The repository still has a few structural gaps that are important to document
honestly:

- Some scripts remain more research-oriented than production-hardened, even
  though they are useful.
- Optional dependency stacks such as FastSolv and SolProp still introduce
  environment-dependent behavior.
- Multiple JSON-producing scripts still implement their own metric/table
  formatting instead of sharing a common reporting layer.

## Recommended Canonical Usage

### Reproducible End-to-End Path

Use:

1. `scripts/prepare_data.py`
2. `scripts/train.py`
3. `scripts/run_seeds.py`
4. `scripts/evaluate_complete.py`
5. `scripts/generate_paper_figures.py`
6. `reproduce.sh` for orchestration

### Rich Interactive Analysis

Use:

1. `notebooks/01_prepare_data.ipynb`
2. `notebooks/02_train.ipynb`
3. `notebooks/04_evaluation.ipynb`
4. `notebooks/05_baselines.ipynb`
5. `notebooks/06_ablations.ipynb`
6. `notebooks/07_temperature.ipynb`

## Remaining Recommendations

These changes were intentionally not forced in this audit pass because they are
architectural decisions rather than obvious bug fixes:

1. Consolidate TGNN-Solv vs FastSolv comparison into one canonical script.
2. Decide whether `evaluate_complete.py` or `benchmark_tgnn_solv.py` should be
   the single primary evaluation entry point.
3. Consider a shared reporting helper for metrics tables and JSON schema
   normalization across evaluation, figure generation, and supplementary-table
   scripts.
4. Decide whether research scripts such as learning curves, temperature
   extrapolation, and physics validation should be promoted from research-grade
   utilities to fully regression-tested production workflows.
