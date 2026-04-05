# Experiment Lab

`Experiment Lab` is the maintained interactive control surface for TGNN-Solv.
It uses the same scripts, checkpoints, processed CSVs, and Python APIs
documented elsewhere on this site, but exposes them as one visual workspace.

Use it when you want:

- one place to launch training, evaluation, experiments, and reproduction jobs
- interactive single-system inference with RDKit structures and atom graphs
- post-hoc uncertainty inspection, calibration review, and OOD checks
- artifact browsing, lineage tracing, and side-by-side result comparison
- visual DAG planning and model-architecture editing
- a repo-backed kanban board and experiment schedule
- access to the documentation site from inside the app itself

## Install

Install the GUI-enabled extras:

```bash
pip install -e ".[gui,dev]"
```

The core model runtime still follows the same PyTorch / PyG installation path
described in [Installation](getting_started/installation.md).

## Launch

Preferred launchers:

```bash
python scripts/launch_lab.py
```

or:

```bash
python scripts/gui/launch_lab.py
```

## Runtime Model

The Streamlit UI process and the model-execution process do not need to use
the same interpreter.

The sidebar exposes a `Python command` field. That command is used for:

- training and evaluation subprocesses
- checkpoint inspection
- detailed inference
- uncertainty and calibration helpers
- environment diagnostics

This is useful when the GUI runs in a lighter environment but model code
should execute in the real `tgnn-solv` environment.

## Main Workspaces

### Data

- processed split coverage
- representative rows and temperature / solubility scatter
- split-family navigation for scaffold, solute, and solvent holdout CSVs

### Training

- tuned TGNN-Solv and DirectGNN launchers
- curriculum-aware training setup
- the same grouped training entry points documented in [Training](training.md)

### Experiments

- multi-seed, split-comparison, medium-budget, full-budget, and Optuna launchers
- external baseline benchmark launcher for FastSolv and SolProp, including
  native SolProp retraining on TGNN-Solv targets
- custom-model benchmark launcher for arbitrary prediction CSVs or
  command-generated outputs
- canonical benchmark bundles that drop straight into the same results registry
  and compare views as maintained models

### Pipeline Studio

- Airflow-style DAG editor with drag, connect, and inline block editing
- repo-backed preset saving under `tools/experiment_lab/presets/pipelines/`
- shell / JSON export
- import of saved inference, uncertainty, or calibration artifacts as DAG nodes

### Model Architect

- TGNN-Solv and DirectGNN config editing
- visual branch diff for the maintained architecture comparison
- real RDKit structure and graph previews derived from the current SMILES

### Results & Plots

- artifact registry across `results/`, `checkpoints/`, `figures/`, and `tables/`
- `Benchmark Studio` for canonical benchmark bundles with leaderboard,
  parity/residual plots, temperature/error views, and stratified metrics
  across FastSolv, SolProp, TGNN-family, and custom-model outputs
- lineage graph linking configs, jobs, checkpoints, lab histories, and planner
  follow-ups
- artifact diff for checkpoints, JSON reports, and CSV tables

### Inference

- single-system prediction with decomposition and temperature scan
- explicit `DirectGNN` run-and-inspect path for the matched no-physics baseline
- persistent history for saved inference runs
- `Uncertainty lab` for ensemble and MC-dropout review
- `Calibration dashboard` for `PICP_90`, `MPIW`, `MAE`, `RMSE`, and parity
  plots
- OOD / applicability-domain scoring through `tgnn_solv.domain`

Current scope note:

- `Run & inspect` supports both `TGNN-Solv` and `DirectGNN`
- `Uncertainty lab` and `Calibration dashboard` currently remain
  `TGNN-Solv`-only because they rely on the maintained physics-facing
  inference stack

### Planner

- repo-backed kanban board
- experiment todo list with scheduling
- intake from saved inference / uncertainty / calibration history
- launch of selected follow-up tasks directly from the board

### Documentation

- local Markdown rendering from `docs/`
- embedded published documentation site

### Reproduce

- structured article-reproduction launcher with `core`, `article`, and `full`
  profiles
- step-graph view sourced from the same maintained reproduction module used by
  `reproduce.sh` and `scripts/experiments/reproduce_paper.py`
- targeted launch of selected reproduction steps when you do not want the whole
  profile

## History and Lineage

The lab persists its own analysis sessions under:

- `results/lab_runs/inference_history/`
- `results/lab_runs/uncertainty_history/`
- `results/lab_runs/calibration_history/`

These saved JSON artifacts are reused throughout the app:

- they appear in the results registry
- they can be compared and downloaded from the inference workbench
- they can be imported into `Pipeline Studio`
- they can be turned into follow-up tasks in `Planner`
- they appear in the lineage graph together with checkpoints and configs

## When To Use the Lab vs the CLI

Use the lab when you need:

- visual monitoring
- ad hoc single-system analysis
- artifact comparison
- external baseline or custom-model benchmarking without hand-writing wrapper
  commands
- planning, scheduling, and manual review loops

Use the CLI when you need:

- unattended execution on a server
- scripted reproducibility
- simple copy-paste commands for training or evaluation
- integration into external automation

Both surfaces are maintained and point to the same underlying project assets.

## Related Pages

- [Installation](getting_started/installation.md)
- [Quick Start Workflow](getting_started/quick_start.md)
- [Training](training.md)
- [Evaluation & Inference](evaluation.md)
- [Experiments & Benchmarks](experiments.md)
- [Results](results.md)
