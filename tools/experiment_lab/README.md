# TGNN-Solv Experiment Lab

Interactive Streamlit control panel for the maintained TGNN-Solv workflow.

## What it covers

- processed split inspection and label coverage
- TGNN-Solv and DirectGNN training launchers
- experiment runners for seeds, split comparisons, Optuna, and full-budget studies
- `Pipeline Studio` for Airflow-style DAG planning, node editing, shell export, and one-click pipeline launch
- repo-local DAG preset saving so custom workflow plans can be versioned with the project
- `Pipeline Studio` and `Model Architect` now also expose drag/drop flow canvases with clickable nodes and editable connections
- `Model Architect` for visual TGNN-Solv / DirectGNN config editing, live forward-path diagrams, active-branch diff views, and structure-derived graph previews
- evaluation and physics-validation launchers
- artifact browser for JSON, CSV, and image outputs
- detailed single-system inference with temperature scans, persistent history, run-to-run comparison, and interpretation
- `Uncertainty lab` with ensemble vs MC-dropout review and saved uncertainty sessions
- `Calibration dashboard` with saved batch calibration runs and compare views
- OOD / applicability-domain scoring through `tgnn_solv.domain`
- lineage-aware results registry that connects checkpoints, configs, saved lab histories, and planner follow-ups
- `Planner` workspace with kanban board, experiment todo list, time-based schedule, and intake from saved lab histories
- `Documentation` workspace with local markdown rendering and embedded published docs
- full paper reproduction controls
- persistent background job monitoring
- environment diagnostics for the selected Python interpreter

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
