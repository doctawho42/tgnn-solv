# TGNN-Solv Experiment Lab

Interactive Streamlit control panel for the maintained TGNN-Solv workflow.

## What it covers

- processed split inspection and label coverage
- TGNN-Solv and DirectGNN training launchers
- Stage 0 controls in the TGNN training surface, including fresh pretraining,
  warm-start checkpoint loading, and descriptor-probe export
- GPS-aware TGNN/DirectGNN config inspection with encoder-family visibility in
  the Training and Architect workspaces
- experiment runners for seeds, split comparisons, Optuna, and full-budget studies
- external baseline benchmarking for FastSolv and SolProp on the repo's own
  train/val/test splits
- native SolProp retraining on TGNN-Solv `ln(x2)` targets, with the trained
  checkpoints benchmarked through the same canonical artifact pipeline
- custom-model benchmarking from an existing predictions CSV or a command that
  generates one
- formal adapter-based custom benchmarking through
  `tgnn_solv.benchmark_adapters`
- `Pipeline Studio` for Airflow-style DAG planning, node editing, shell export, and one-click pipeline launch
- repo-local DAG preset saving so custom workflow plans can be versioned with the project
- `Pipeline Studio` and `Model Architect` now also expose drag/drop flow canvases with clickable nodes and editable connections
- `Model Architect` for visual TGNN-Solv / DirectGNN config editing, live forward-path diagrams, active-branch diff views, structure-derived graph previews, GPS encoder controls, TGNN descriptor-augmentation branches, and Stage 0 launch-time planning
- evaluation and physics-validation launchers
- artifact browser for JSON, CSV, and image outputs
- `Benchmark Studio` inside `Results & Plots` for leaderboard, parity/residual plots, stratified metrics, and comparison across FastSolv, SolProp, TGNN bundles, and custom-model benchmark outputs
- benchmark-card and run-manifest inspection for canonical benchmark bundles
- detailed single-system inference with temperature scans, persistent history, run-to-run comparison, and interpretation
- structure drawing and editing in `Inference` via an embedded Ketcher sketcher, with RDKit-sanitized structure/graph preview, sync-back into the SMILES inputs, and one-click apply+run
- `Run & inspect` now supports both `TGNN-Solv` and `DirectGNN` checkpoints
- `Uncertainty lab` with ensemble vs MC-dropout review and saved uncertainty sessions for both maintained model families
- `Calibration dashboard` with saved batch calibration runs and compare views for both maintained model families
- OOD / applicability-domain scoring through `tgnn_solv.domain`
- `Applications` for solvent screening, process optimization, drug
  developability, and PK-relevant solubility profiling
- lineage-aware results registry that connects checkpoints, configs, saved lab histories, and planner follow-ups
- `Planner` workspace with kanban board, experiment todo list, time-based schedule, and intake from saved lab histories
- `Documentation` workspace with local markdown rendering and embedded published docs
- structured paper reproduction controls with `core`, `article`, and `full` profiles
- persistent background job monitoring
- environment diagnostics for the selected Python interpreter

For SolProp specifically, the recommended article-comparison mode in the lab is
now `native`, which retrains the SolProp architecture directly on TGNN-Solv
targets. The room-temperature zero-shot and calibrated wrappers remain useful as
reference baselines, and the upstream temperature-dependent SolProp branch is
still exposed as an experimental option.

## Repo-backed state

The lab persists its own project-local state in the repository:

- DAG presets: `tools/experiment_lab/presets/pipelines/`
- planner board: `tools/experiment_lab/presets/planner/planner_state.json`
- inference history: `results/lab_runs/inference_history/`
- uncertainty history: `results/lab_runs/uncertainty_history/`
- calibration history: `results/lab_runs/calibration_history/`

These artifacts are then reused inside:

- `Results & Plots`
- `Pipeline Studio`
- `Planner`
- the lineage graph

## Install

```bash
pip install -e ".[gui,dev]"
```

## Launch

```bash
python scripts/launch_lab.py
```

The launcher auto-detects a project environment with the full GUI stack
(`streamlit`, flow editor, sortables, and Ketcher) and prefers that interpreter
over the current shell Python.

or

```bash
python scripts/gui/launch_lab.py
```

## Important runtime note

The Streamlit UI process and the training/inference process do not need to be
the same Python environment.

The sidebar exposes a `Python command` field. Use it when the GUI is running in
a lightweight environment but model code should execute elsewhere, for example:

```bash
conda run -n tgnn-solv python
```

This command is used for:

- training and experiment subprocesses
- evaluation runners
- checkpoint inspection
- detailed inference
- environment diagnostics

That makes the lab usable even when the GUI environment itself does not carry
the full PyTorch/PyG stack.

## Application Layer

The `Applications` page is intentionally conservative:

- solvent screening
  - ranks solvent libraries, antisolvents, green replacements, and
    crystallization windows
- process optimization
  - crystallization, extraction, and reaction-medium screens with
    constraint-driven ranking
- drug developability
  - BCS-style classification, developability scoring, and salt/cocrystal triage
- PK solubility profile
  - GI compartment, biorelevant media, IV, and topical vehicle workflows

It does **not** claim to be a full retrosynthesis planner, PBPK simulator, or
mechanistic PK/PD model. Instead it exposes the places where equilibrium
solubility is genuinely useful and clearly marks where additional models are
required.
