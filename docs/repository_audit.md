# Repository Audit

This audit summarizes the current repo shape, with emphasis on whether the
documented workflows actually match the code.

## Executive Summary

The repository is now coherent around a reproducible CLI path:

1. `scripts/prepare_data.py`
2. `scripts/train.py`
3. `scripts/run_seeds.py`
4. `scripts/evaluate_complete.py`
5. `scripts/run_split_comparisons.py`
6. `scripts/generate_paper_figures.py`
7. `reproduce.sh`

The main improvements relative to earlier states are:

- docs now describe the real maintained scripts instead of hypothetical ones
- DirectGNN has a documented standalone CLI and descriptor-augmentation mode
- crystal GC priors, Walden/oracle modes, and the full-budget experiment runner
  are documented as explicit research features
- the main training CLIs now support resumable checkpoints
- the medium-budget full-split architecture runner is documented alongside the
  full-budget diagnostic path
- split-wise comparison and baseline workflows are described consistently with
  the live code

## Current Strengths

- clear separation between model, solver, data, and reporting code
- strong numerical test coverage around the physics core
- canonical split registry for scaffold, solute, and solvent protocols
- one maintained no-physics baseline (`DirectGNN`) and multiple descriptor
  baselines for fair comparison
- full-budget diagnostic runner that exports solver intermediates rather than
  only top-line error metrics

## Known Gaps

### 1. Resume Support Is Better, But Not Universal

The main TGNN and DirectGNN training CLIs now support resumable checkpoints,
and the two heavy experiment runners reuse those checkpoints automatically.

Implication:

- single-run training is preemption-safe
- some lighter wrappers still do not add their own orchestration around
  partial-progress recovery

### 2. Optional Dependency Stacks Remain Environment-Sensitive

FastSolv and SolProp are still external ecosystems with their own dependency
requirements.

Status:

- wrappers are documented honestly as optional
- unrelated script help paths no longer depend on those imports

### 3. Research Scripts Are Unevenly Hardened

Useful research scripts exist for:

- ablations
- learning curves
- temperature extrapolation
- physics validation
- full-budget diagnostics
- medium-budget architecture comparison

They are valuable, but they are not all at the same regression-hardening level
as the canonical train/eval path.

### 4. No Fixed Repo-Wide Metric Target

The repository intentionally does not claim one immutable benchmark number that
every environment must match exactly.

Implication:

- reproduction should be validated via generated artifacts and consistent
  schemas, not by a single hardcoded MAE target in the docs

## Intentional Overlap

Some overlap is useful and should remain:

- `evaluate_complete.py` vs `benchmark_tgnn_solv.py`
  - quick plot-ready eval vs richer benchmark path
- notebook vs CLI workflows
  - exploration vs reproducibility
- `run_split_comparisons.py` vs `run_full_budget_experiment.py`
  - split-protocol fairness vs one deep budget-matched diagnostic study

## Recommended Usage Today

### Reproducible default path

Use:

1. `scripts/prepare_data.py`
2. `scripts/train.py`
3. `scripts/run_seeds.py`
4. `scripts/evaluate_complete.py`
5. `scripts/run_split_comparisons.py`
6. `reproduce.sh`

### Best baseline-comparison path

Use:

1. `scripts/train_directgnn.py`
2. `configs/paper_config_directgnn_descriptors.yaml`
3. `python -m tgnn_solv.baselines.rf_baseline`
4. `scripts/run_split_comparisons.py`

### Best bottleneck-diagnosis path

Use:

1. `scripts/run_full_budget_experiment.py`
2. `scripts/validate_physics.py`

## Open Follow-Up Opportunities

These are still good future hardening targets:

1. expand resume-aware orchestration to more multi-run wrappers
2. consolidate overlapping benchmark/report formatting helpers
3. expand regression coverage for the research-heavy experiment scripts
4. decide whether any current experimental config variants should be promoted to
   canonical status
