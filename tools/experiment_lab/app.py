from __future__ import annotations

import copy
import json
import math
import os
import re
import shlex
import signal
import subprocess
import sys
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

try:
    import yaml
except Exception:  # pragma: no cover - optional in GUI env
    yaml = None

try:
    from streamlit_flow import streamlit_flow
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode
    from streamlit_flow.layouts import ManualLayout
    from streamlit_flow.state import StreamlitFlowState

    FLOW_ERROR = None
except Exception as exc:  # pragma: no cover - optional in GUI env
    streamlit_flow = None
    StreamlitFlowEdge = None
    StreamlitFlowNode = None
    ManualLayout = None
    StreamlitFlowState = None
    FLOW_ERROR = f"{type(exc).__name__}: {exc}"

try:
    from streamlit_sortables import sort_items

    SORTABLES_ERROR = None
except Exception as exc:  # pragma: no cover - optional in GUI env
    sort_items = None
    SORTABLES_ERROR = f"{type(exc).__name__}: {exc}"

try:
    from streamlit_ketcher import st_ketcher

    KETCHER_ERROR = None
except Exception as exc:  # pragma: no cover - optional in GUI env
    st_ketcher = None
    KETCHER_ERROR = f"{type(exc).__name__}: {exc}"

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors
    from rdkit.Chem.Draw import rdMolDraw2D

    RDKIT_ERROR = None
except Exception as exc:  # pragma: no cover - optional in GUI env
    Chem = None
    DataStructs = None
    AllChem = None
    Descriptors = None
    rdMolDescriptors = None
    rdMolDraw2D = None
    RDKIT_ERROR = f"{type(exc).__name__}: {exc}"


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
RUNS_DIR = REPO_ROOT / "results" / "lab_runs"
RUNNER_PATH = Path(__file__).with_name("job_runner.py")
PROCESSED_DIR = REPO_ROOT / "notebooks" / "data" / "processed"
CONFIG_DIR = REPO_ROOT / "configs"
RESULTS_DIR = REPO_ROOT / "results"
CHECKPOINTS_DIR = REPO_ROOT / "checkpoints"
FIGURES_DIR = REPO_ROOT / "figures"
TABLES_DIR = REPO_ROOT / "tables"
DOCS_DIR = REPO_ROOT / "docs"
TMP_DIR = REPO_ROOT / "tmp"
PIPELINE_PRESETS_DIR = REPO_ROOT / "tools" / "experiment_lab" / "presets" / "pipelines"
PLANNER_DIR = REPO_ROOT / "tools" / "experiment_lab" / "presets" / "planner"
PLANNER_STATE_PATH = PLANNER_DIR / "planner_state.json"
INFERENCE_HISTORY_DIR = RUNS_DIR / "inference_history"
UNCERTAINTY_HISTORY_DIR = RUNS_DIR / "uncertainty_history"
CALIBRATION_HISTORY_DIR = RUNS_DIR / "calibration_history"
OPTUNA_DIR = RESULTS_DIR / "optuna"
APP_TITLE = "TGNN-Solv Experiment Lab"
DEFAULT_PYTHON_COMMAND = sys.executable
PROBE_CACHE_VERSION = 2
PUBLISHED_DOCS_URL = "https://doctawho42.github.io/tgnn-solv/"
RUNTIME_SOURCE_FILES = (
    Path(__file__).resolve(),
    SRC_ROOT / "tgnn_solv" / "inference.py",
    SRC_ROOT / "tgnn_solv" / "uncertainty.py",
    SRC_ROOT / "tgnn_solv" / "model.py",
)

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from tgnn_solv.applications import (
        BUILTIN_SOLVENT_LIBRARY,
        PHARMA_MEDIA_LIBRARY,
        SYNTHESIS_SOLVENT_LIBRARY,
    )
except Exception:  # pragma: no cover - fallback only
    BUILTIN_SOLVENT_LIBRARY = []
    SYNTHESIS_SOLVENT_LIBRARY = {
        "Water": "O",
        "Methanol": "CO",
        "Ethanol": "CCO",
        "Isopropanol": "CC(C)O",
        "Acetone": "CC(=O)C",
        "Acetonitrile": "CC#N",
        "Ethyl acetate": "CCOC(=O)C",
        "THF": "C1CCOC1",
        "2-MeTHF": "CC1CCCO1",
        "Toluene": "Cc1ccccc1",
        "DMSO": "CS(C)=O",
        "DMF": "CN(C)C=O",
    }
    PHARMA_MEDIA_LIBRARY = {
        "Water": "O",
        "Ethanol": "CCO",
        "Propylene glycol": "CC(O)CO",
        "Glycerol": "C(C(CO)O)O",
        "PEG surrogate": "OCCOCCOCCO",
        "DMSO": "CS(C)=O",
    }

APPLICATION_ROUTE_TEMPLATE: list[dict[str, Any]] = [
    {
        "step_id": "S1",
        "compound_smiles": "CC(=O)Nc1ccc(O)cc1",
        "reaction_temp_k": 338.15,
        "isolation_temp_k": 278.15,
        "candidate_solvents": "Ethanol, Isopropanol, Acetonitrile, Ethyl acetate, Water",
        "goal": "temperature-swing crystallization",
    },
    {
        "step_id": "S2",
        "compound_smiles": "O=C(Nc1ncccn1)c1ccccc1",
        "reaction_temp_k": 323.15,
        "isolation_temp_k": 283.15,
        "candidate_solvents": "THF, 2-MeTHF, Toluene, Ethyl acetate, Water",
        "goal": "workup and isolation",
    },
]

WORKSPACE_GROUPS: list[list[dict[str, str]]] = [
    [
        {"name": "Overview", "button": "Overview", "kicker": "Start", "desc": "Status and quick launches"},
        {"name": "Data", "button": "Data", "kicker": "Data", "desc": "Splits and label coverage"},
        {"name": "Training", "button": "Training", "kicker": "Train", "desc": "Runs and curriculum setup"},
        {"name": "Pipeline Studio", "button": "Pipeline", "kicker": "Flow", "desc": "Interactive DAG editor"},
        {"name": "Experiments", "button": "Experiments", "kicker": "Batch", "desc": "Scripts and experiment launchers"},
        {"name": "HPO Lab", "button": "HPO", "kicker": "Tune", "desc": "Optuna launch and study dashboard"},
        {"name": "Model Architect", "button": "Architect", "kicker": "Model", "desc": "Interactive model graph editor"},
    ],
    [
        {"name": "Results & Plots", "button": "Results", "kicker": "Results", "desc": "Artifacts and dashboards"},
        {"name": "Inference", "button": "Inference", "kicker": "Infer", "desc": "Detailed single-system workbench"},
        {"name": "Applications", "button": "Applications", "kicker": "Apply", "desc": "Synthesis and developability"},
        {"name": "Planner", "button": "Planner", "kicker": "Plan", "desc": "Kanban, todos, and schedule"},
        {"name": "Documentation", "button": "Docs", "kicker": "Docs", "desc": "Local docs and published site"},
        {"name": "Reproduce", "button": "Reproduce", "kicker": "Paper", "desc": "Article reproduction workflow"},
        {"name": "Job Center", "button": "Jobs", "kicker": "Jobs", "desc": "Live processes and logs"},
        {"name": "Environment", "button": "Runtime", "kicker": "Runtime", "desc": "Interpreter health"},
    ],
]


def runtime_code_token() -> tuple[int, ...]:
    token: list[int] = []
    for path in RUNTIME_SOURCE_FILES:
        try:
            token.append(path.stat().st_mtime_ns)
        except FileNotFoundError:
            token.append(0)
    return tuple(token)


def ensure_runtime_cache_consistency() -> None:
    current_token = runtime_code_token()
    cached_token = st.session_state.get("_lab_runtime_code_token")
    if cached_token != current_token:
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state["_lab_runtime_code_token"] = current_token

ARCHITECTURE_VISUAL_NODES: dict[str, list[dict[str, Any]]] = {
    "TGNN-Solv": [
        {"id": "solute_graph", "label": "Solute graph", "track": "input", "kind": "core", "x": 20, "y": 40, "note": "Parsed RDKit solute graph"},
        {"id": "solvent_graph", "label": "Solvent graph", "track": "input", "kind": "core", "x": 20, "y": 220, "note": "Parsed RDKit solvent graph"},
        {"id": "stage0_warmstart", "label": "Stage 0 warm start", "track": "shared", "kind": "toggle", "x": 250, "y": 20, "note": "Optional pretraining of `model.gnn` and `model.readout` before the main curriculum"},
        {"id": "shared_encoder", "label": "Shared MPNN / GPS encoder", "track": "shared", "kind": "core", "x": 250, "y": 130, "note": "Shared residual or split-late encoder selected by `encoder_type`"},
        {"id": "gps_pe", "label": "GPS positional encoding", "track": "shared", "kind": "toggle", "x": 250, "y": 360, "note": "Laplacian or RWSE node positional features when `encoder_type=gps`"},
        {"id": "pre_head_priors", "label": "Pre-head priors", "track": "tgnn", "kind": "toggle", "flag": "use_descriptor_priors", "x": 500, "y": 30, "note": "Descriptor/group/GC prior lane"},
        {"id": "interaction", "label": "Interaction stack", "track": "shared", "kind": "core", "x": 500, "y": 170, "note": "Cross-attention or bipartite interaction"},
        {"id": "readout_pair", "label": "Readout + pair", "track": "shared", "kind": "core", "x": 500, "y": 320, "note": "Set2Set plus pair construction"},
        {"id": "morgan_adapter", "label": "Morgan adapter", "track": "shared", "kind": "toggle", "flag": "use_morgan_features", "x": 260, "y": 370, "note": "Optional fingerprint side path"},
        {"id": "descriptor_aug", "label": "Descriptor augmentation", "track": "shared", "kind": "toggle", "flag": "use_descriptor_augmentation", "x": 500, "y": 420, "note": "Normalized RDKit descriptors fused back into the TGNN pair representation"},
        {"id": "solvent_moe", "label": "Solvent-type MoE", "track": "tgnn", "kind": "toggle", "flag": "use_solvent_moe", "x": 500, "y": 470, "note": "Optional mixture-of-experts routing"},
        {"id": "fusion_head", "label": "FusionHead", "track": "tgnn", "kind": "core", "x": 760, "y": 30, "note": "Predicts Tm / dHfus / dCpfus"},
        {"id": "nrtl_head", "label": "NRTLHead", "track": "tgnn", "kind": "core", "x": 760, "y": 170, "note": "Predicts solver interaction parameters"},
        {"id": "correction", "label": "Adaptive correction", "track": "tgnn", "kind": "core", "x": 760, "y": 320, "note": "Bounded solver-space correction"},
        {"id": "solver", "label": "SLE solver", "track": "tgnn", "kind": "core", "x": 1010, "y": 155, "note": "0-parameter thermodynamic bottleneck"},
        {"id": "oracle_injection", "label": "Oracle injection", "track": "tgnn", "kind": "toggle", "flag": "use_oracle_injection", "x": 1010, "y": 30, "note": "Train-time supervised substitution"},
        {"id": "implicit_diff", "label": "Implicit differentiation", "track": "tgnn", "kind": "toggle", "flag": "use_implicit_diff", "x": 1010, "y": 360, "note": "One-step backward through fixed point"},
    ],
    "DirectGNN": [
        {"id": "solute_graph", "label": "Solute graph", "track": "input", "kind": "core", "x": 20, "y": 70, "note": "Parsed RDKit solute graph"},
        {"id": "solvent_graph", "label": "Solvent graph", "track": "input", "kind": "core", "x": 20, "y": 260, "note": "Parsed RDKit solvent graph"},
        {"id": "shared_encoder", "label": "Shared MPNN / GPS encoder", "track": "shared", "kind": "core", "x": 250, "y": 155, "note": "Same maintained encoder stack as TGNN-Solv"},
        {"id": "gps_pe", "label": "GPS positional encoding", "track": "shared", "kind": "toggle", "x": 250, "y": 360, "note": "Optional Laplacian or RWSE node positional features"},
        {"id": "interaction_readout", "label": "Interaction + readout", "track": "shared", "kind": "core", "x": 520, "y": 155, "note": "Shared interaction and readout stack"},
        {"id": "temperature", "label": "Thermometer encoder", "track": "direct", "kind": "core", "x": 800, "y": 35, "note": "Direct temperature encoding"},
        {"id": "descriptor_aug", "label": "Descriptor augmentation", "track": "direct", "kind": "toggle", "flag": "use_descriptor_augmentation", "x": 800, "y": 175, "note": "Full RDKit descriptor path"},
        {"id": "morgan_path", "label": "Morgan path", "track": "direct", "kind": "toggle", "flag": "use_morgan_features", "x": 800, "y": 315, "note": "Optional fingerprint path"},
        {"id": "mlp_head", "label": "Direct ln(x2) head", "track": "direct", "kind": "core", "x": 1060, "y": 155, "note": "Direct regression head"},
    ],
}

ARCHITECTURE_VISUAL_EDGES: dict[str, list[tuple[str, str, str]]] = {
    "TGNN-Solv": [
        ("e_solute_encoder", "solute_graph", "shared_encoder"),
        ("e_solvent_encoder", "solvent_graph", "shared_encoder"),
        ("e_stage0_encoder", "stage0_warmstart", "shared_encoder"),
        ("e_gps_encoder", "gps_pe", "shared_encoder"),
        ("e_encoder_priors", "shared_encoder", "pre_head_priors"),
        ("e_encoder_interaction", "shared_encoder", "interaction"),
        ("e_interaction_readout", "interaction", "readout_pair"),
        ("e_readout_fusion", "readout_pair", "fusion_head"),
        ("e_readout_nrtl", "readout_pair", "nrtl_head"),
        ("e_readout_correction", "readout_pair", "correction"),
        ("e_readout_descriptor", "readout_pair", "descriptor_aug"),
        ("e_fusion_solver", "fusion_head", "solver"),
        ("e_nrtl_solver", "nrtl_head", "solver"),
        ("e_solver_correction", "solver", "correction"),
        ("e_morgan_readout", "morgan_adapter", "readout_pair"),
        ("e_descriptor_fusion", "descriptor_aug", "fusion_head"),
        ("e_oracle_solver", "oracle_injection", "solver"),
        ("e_correction_implicit", "correction", "implicit_diff"),
        ("e_encoder_morgan", "shared_encoder", "morgan_adapter"),
        ("e_readout_moe", "readout_pair", "solvent_moe"),
        ("e_moe_fusion", "solvent_moe", "fusion_head"),
    ],
    "DirectGNN": [
        ("e_solute_encoder", "solute_graph", "shared_encoder"),
        ("e_solvent_encoder", "solvent_graph", "shared_encoder"),
        ("e_gps_encoder", "gps_pe", "shared_encoder"),
        ("e_encoder_readout", "shared_encoder", "interaction_readout"),
        ("e_temperature_head", "temperature", "mlp_head"),
        ("e_descriptor_head", "descriptor_aug", "mlp_head"),
        ("e_morgan_head", "morgan_path", "mlp_head"),
        ("e_readout_head", "interaction_readout", "mlp_head"),
    ],
}


WORKFLOW_STEPS = [
    (
        "Core article reproduction",
        "Run the maintained core profile: canonical data, tuned TGNN seeds, evaluation, split comparison, tables, and figures.",
        ["python", "scripts/experiments/reproduce_paper.py", "--profile", "core"],
    ),
    (
        "Article comparison bundle",
        "Run the current article profile, including medium-budget comparisons and external baseline benchmarking.",
        ["python", "scripts/experiments/reproduce_paper.py", "--profile", "article"],
    ),
    (
        "Full diagnostic reproduction",
        "Run the expanded profile with split-late, DirectGNN multi-seed, ablations, temperature extrapolation, significance, and full-budget diagnostics.",
        ["python", "scripts/experiments/reproduce_paper.py", "--profile", "full"],
    ),
    (
        "External baseline benchmark",
        "Run FastSolv and native SolProp against the repo's canonical split.",
        ["python", "scripts/experiments/run_external_baseline_benchmark.py"],
    ),
    (
        "Generate supplementary tables",
        "Collect paper-facing CSV/LaTeX tables from the currently available results.",
        ["python", "scripts/experiments/generate_supplementary.py"],
    ),
    (
        "Generate paper figures",
        "Create publication-ready plots from result artifacts.",
        ["python", "scripts/experiments/generate_paper_figures.py"],
    ),
    (
        "Legacy shell entrypoint",
        "Compatibility wrapper that now delegates to the structured article profile runner.",
        ["bash", "reproduce.sh"],
    ),
]

PIPELINE_PRESETS: dict[str, dict[str, Any]] = {
    "Canonical TGNN workflow": {
        "description": (
            "The maintained end-to-end path: scaffold-aware data, one tuned TGNN run, "
            "multi-seed sweep, full evaluation, split comparison, and paper figures."
        ),
        "nodes": [
            {
                "id": "prepare_data",
                "label": "Prepare scaffold-aware data",
                "category": "data",
                "command": "python scripts/data/prepare_data.py --output-dir notebooks/data/processed --split-mode solute_scaffold --seed 42 --skip-download",
                "depends_on": [],
                "expected_outputs": [
                    "notebooks/data/processed/train.csv",
                    "notebooks/data/processed/val.csv",
                    "notebooks/data/processed/test.csv",
                ],
                "notes": "Merge raw sources, canonicalize SMILES, left-join auxiliary labels, and write the canonical scaffold-aware split.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "train_tgnn",
                "label": "Train tuned TGNN-Solv",
                "category": "training",
                "command": "python scripts/training/train.py --config configs/paper_config_tuned.yaml --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --checkpoint checkpoints/tgnn_solv_trained.pt --device cuda --checkpoint-every 10",
                "depends_on": ["prepare_data"],
                "expected_outputs": ["checkpoints/tgnn_solv_trained.pt"],
                "notes": "Single maintained TGNN run with the tuned paper-style configuration and resumable checkpoints.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "run_seeds",
                "label": "Run TGNN multi-seed sweep",
                "category": "experiments",
                "command": "python scripts/experiments/run_seeds.py --config configs/paper_config_tuned.yaml --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --n-seeds 5 --base-seed 42 --output results/multi_seed_results.json --checkpoint-dir checkpoints/seeds --device cuda",
                "depends_on": ["prepare_data"],
                "expected_outputs": ["results/multi_seed_results.json", "checkpoints/seeds"],
                "notes": "Seed variance estimate on the canonical split. This is the main stability readout for the maintained TGNN pipeline.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "evaluate_complete",
                "label": "Evaluate best TGNN checkpoint",
                "category": "evaluation",
                "command": "python scripts/evaluation/evaluate_complete.py --test-data notebooks/data/processed/test.csv --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt --output results/full_evaluation.json --verbose",
                "depends_on": ["train_tgnn"],
                "expected_outputs": ["results/full_evaluation.json"],
                "notes": "Parity metrics, prediction arrays, and report JSON for the tuned TGNN checkpoint.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "split_compare",
                "label": "Run split-wise comparison",
                "category": "experiments",
                "command": "python scripts/experiments/run_split_comparisons.py --processed-dir notebooks/data/processed --splits solute_scaffold,solute,solvent --models tgnn_solv,direct_gnn,rf_baseline,rf_morgan,rf_hybrid --config configs/paper_config_tuned.yaml --output results/split_comparisons.json",
                "depends_on": ["prepare_data"],
                "expected_outputs": ["results/split_comparisons.json"],
                "notes": "Checks where generalization fails: scaffold holdout, solute holdout, and solvent holdout.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "paper_figures",
                "label": "Generate paper figures",
                "category": "analysis",
                "command": "python scripts/experiments/generate_paper_figures.py",
                "depends_on": ["evaluate_complete", "split_compare", "run_seeds"],
                "expected_outputs": ["figures"],
                "notes": "Consumes evaluation and experiment artifacts to regenerate the paper-facing plots.",
                "launchable": True,
                "active": True,
            },
        ],
    },
    "Paper reproduction map": {
        "description": (
            "An expanded DAG view of the maintained article-reproduction path: tuned TGNN core, medium-budget matched baselines, external FastSolv/SolProp benchmarking, diagnostics, and final figure/table generation."
        ),
        "nodes": [
            {
                "id": "repro_prepare_data",
                "label": "Prepare data if missing",
                "category": "data",
                "command": "python scripts/data/prepare_data.py --output-dir notebooks/data/processed --split-mode solute_scaffold --seed 42 --skip-download",
                "depends_on": [],
                "expected_outputs": ["notebooks/data/processed/train.csv", "notebooks/data/processed/test.csv"],
                "notes": "Maintained grouped data-preparation entrypoint used by the structured reproduction runner.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_run_seeds",
                "label": "TGNN 5-seed run",
                "category": "experiments",
                "command": "python scripts/experiments/run_seeds.py --config configs/paper_config_tuned.yaml --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --n-seeds 5 --base-seed 42 --output results/multi_seed_results.json --checkpoint-dir checkpoints/seeds --device cuda",
                "depends_on": ["repro_prepare_data"],
                "expected_outputs": ["results/multi_seed_results.json", "checkpoints/seeds"],
                "notes": "Maintained tuned TGNN multi-seed run used as the core article anchor.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_medium_budget",
                "label": "Medium-budget architecture sweep",
                "category": "experiments",
                "command": "python scripts/experiments/run_medium_budget_comparison.py --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --output-dir results/medium_budget --device cuda",
                "depends_on": ["repro_prepare_data"],
                "expected_outputs": ["results/medium_budget"],
                "notes": "Current in-repo article comparison across tuned TGNN, GC-prior variants, DirectGNN baselines, and RF.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_external",
                "label": "External FastSolv / SolProp benchmark",
                "category": "baseline",
                "command": "python scripts/experiments/run_external_baseline_benchmark.py --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --out-dir results/external_baselines/article_benchmark --split-mode solute_scaffold --fastsolv-mode both --solprop-mode native --continue-on-error",
                "depends_on": ["repro_prepare_data"],
                "expected_outputs": ["results/external_baselines/article_benchmark/summary.csv"],
                "notes": "Article-facing external benchmark path with FastSolv and native-retrained SolProp.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_split_late",
                "label": "Split-late matched backbone",
                "category": "experiments",
                "command": "python scripts/experiments/run_seeds.py --config configs/paper_config_split_late.yaml --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --n-seeds 5 --base-seed 42 --output results/split_late_multi_seed_results.json --checkpoint-dir checkpoints/split_late_seeds --device cuda",
                "depends_on": ["repro_prepare_data"],
                "expected_outputs": ["results/split_late_multi_seed_results.json", "checkpoints/split_late_seeds"],
                "notes": "Keeps the budget fixed while toggling the late role-specific encoder variant.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_eval",
                "label": "Best-checkpoint evaluation",
                "category": "evaluation",
                "command": "python scripts/experiments/reproduce_paper.py --profile article --step evaluate_best",
                "depends_on": ["repro_run_seeds"],
                "expected_outputs": ["results/full_evaluation.json"],
                "notes": "Structured reproduction runner resolves the best TGNN seed dynamically from results/multi_seed_results.json.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_error",
                "label": "Error analysis",
                "category": "analysis",
                "command": "python scripts/evaluation/error_analysis.py --predictions results/full_evaluation.json --test-data notebooks/data/processed/test.csv --output results/error_analysis.json",
                "depends_on": ["repro_eval"],
                "expected_outputs": ["results/error_analysis.json"],
                "notes": "Breaks the error down by chemistry and operating regimes.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_ablation",
                "label": "Ablation suite",
                "category": "analysis",
                "command": "python scripts/experiments/run_ablation.py --config configs/paper_config_tuned.yaml --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --n-seeds 3 --output results/ablation.json --device cuda",
                "depends_on": ["repro_prepare_data"],
                "expected_outputs": ["results/ablation.json"],
                "notes": "Bridge / Walden / oracle / architecture controls.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_direct",
                "label": "DirectGNN baseline",
                "category": "baseline",
                "command": "python scripts/experiments/run_seeds.py --train-script scripts/training/train_directgnn.py --config configs/paper_config_directgnn_tuned.yaml --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --n-seeds 5 --base-seed 42 --output results/directgnn_multi_seed_results.json --checkpoint-dir checkpoints/directgnn_seeds --device cuda",
                "depends_on": ["repro_prepare_data"],
                "expected_outputs": ["results/directgnn_multi_seed_results.json", "checkpoints/directgnn_seeds"],
                "notes": "Matched backbone, no solver bottleneck, now tracked as a proper multi-seed comparison bundle.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_temp",
                "label": "Temperature extrapolation study",
                "category": "analysis",
                "command": "python scripts/experiments/temperature_extrapolation.py",
                "depends_on": ["repro_eval", "repro_direct"],
                "expected_outputs": ["results/temperature_extrapolation.json"],
                "notes": "Checks whether the hardcoded solver path helps outside the observed temperature window.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_physics",
                "label": "Physics validation",
                "category": "evaluation",
                "command": "python scripts/evaluation/validate_physics.py --checkpoint checkpoints/tgnn_solv_trained.pt --test-data notebooks/data/processed/test.csv --output results/physics_validation.json",
                "depends_on": ["repro_eval"],
                "expected_outputs": ["results/physics_validation.json"],
                "notes": "Exports physics-facing diagnostics and solver sanity checks.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_stats",
                "label": "Statistical tests",
                "category": "analysis",
                "command": "python scripts/experiments/statistical_tests.py --results results/multi_seed_results.json results/directgnn_multi_seed_results.json results/split_late_multi_seed_results.json --labels TGNN-Solv DirectGNN SplitLate --output results/significance.json",
                "depends_on": ["repro_run_seeds", "repro_direct"],
                "expected_outputs": ["results/significance.json"],
                "notes": "Paper-level significance checks across model families.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_supplementary",
                "label": "Supplementary tables",
                "category": "analysis",
                "command": "python scripts/experiments/generate_supplementary.py",
                "depends_on": ["repro_eval", "repro_physics", "repro_stats"],
                "expected_outputs": ["tables"],
                "notes": "Collects supplementary tables and appendix-facing exports.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_figures",
                "label": "Paper figures",
                "category": "analysis",
                "command": "python scripts/experiments/generate_paper_figures.py",
                "depends_on": ["repro_eval", "repro_error", "repro_ablation", "repro_temp", "repro_stats"],
                "expected_outputs": ["figures"],
                "notes": "Final figure build after evaluation, diagnostics, and statistical testing.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "repro_shell",
                "label": "Structured article profile",
                "category": "paper",
                "command": "python scripts/experiments/reproduce_paper.py --profile article",
                "depends_on": [],
                "expected_outputs": ["results/reproduction/article_summary.json", "results", "figures", "tables"],
                "notes": "Single maintained entry point for the article profile. Use this when you want orchestration and dynamic best-checkpoint resolution handled automatically.",
                "launchable": True,
                "active": False,
            },
        ],
    },
    "Medium-budget architecture study": {
        "description": (
            "Architecture-triage DAG used to compare tuned TGNN, GC-prior variants, DirectGNN, DirectGNN+descriptors, and RF baselines on the full scaffold split."
        ),
        "nodes": [
            {
                "id": "medium_prepare",
                "label": "Prepare canonical split",
                "category": "data",
                "command": "python scripts/data/prepare_data.py --output-dir notebooks/data/processed --split-mode solute_scaffold --seed 42 --skip-download",
                "depends_on": [],
                "expected_outputs": ["notebooks/data/processed/train.csv", "notebooks/data/processed/test.csv"],
                "notes": "Rebuild canonical processed CSVs before the architecture sweep.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "medium_budget",
                "label": "Run medium-budget comparison",
                "category": "experiments",
                "command": "python scripts/experiments/run_medium_budget_comparison.py --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --output-dir results/medium_budget --device cuda",
                "depends_on": ["medium_prepare"],
                "expected_outputs": ["results/medium_budget"],
                "notes": "Shared-budget comparison across TGNN, DirectGNN, descriptor-augmented baselines, and RF.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "medium_plots",
                "label": "Plot architecture leaderboard",
                "category": "analysis",
                "command": "python scripts/experiments/generate_paper_figures.py",
                "depends_on": ["medium_budget"],
                "expected_outputs": ["figures"],
                "notes": "Reuses the figure generator once medium-budget artifacts land.",
                "launchable": True,
                "active": True,
            },
        ],
    },
    "Full-budget diagnostic study": {
        "description": (
            "The heavier diagnostic branch that exports solver intermediates, oracle-evaluated TGNN metrics, matched DirectGNN baselines, and detailed JSON diagnostics."
        ),
        "nodes": [
            {
                "id": "full_prepare",
                "label": "Prepare canonical split",
                "category": "data",
                "command": "python scripts/data/prepare_data.py --output-dir notebooks/data/processed --split-mode solute_scaffold --seed 42 --skip-download",
                "depends_on": [],
                "expected_outputs": ["notebooks/data/processed/train.csv", "notebooks/data/processed/test.csv"],
                "notes": "Canonical scaffold-aware processed data.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "full_budget",
                "label": "Run full-budget experiment",
                "category": "experiments",
                "command": "python scripts/experiments/run_full_budget_experiment.py --config configs/paper_config_tuned.yaml --train-data notebooks/data/processed/train.csv --val-data notebooks/data/processed/val.csv --test-data notebooks/data/processed/test.csv --seeds 42 --output-dir results/full_budget_experiment --device cuda",
                "depends_on": ["full_prepare"],
                "expected_outputs": ["results/full_budget_experiment"],
                "notes": "Budget-matched TGNN vs DirectGNN run with solver-facing diagnostic exports.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "full_validate",
                "label": "Validate physics on exported checkpoint",
                "category": "evaluation",
                "command": "python scripts/evaluation/validate_physics.py --checkpoint checkpoints/tgnn_solv_trained.pt --test-data notebooks/data/processed/test.csv --output results/physics_validation.json",
                "depends_on": ["full_budget"],
                "expected_outputs": ["results/physics_validation.json"],
                "notes": "Checks solver stability and parameter reasonableness after the heavy run.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "full_figures",
                "label": "Refresh figures and tables",
                "category": "analysis",
                "command": "bash reproduce.sh",
                "depends_on": ["full_budget", "full_validate"],
                "expected_outputs": ["figures", "tables"],
                "notes": "Optional coarse-grained downstream step when you want the rest of the paper automation after the diagnostic export.",
                "launchable": True,
                "active": False,
            },
        ],
    },
    "Inference QA and uncertainty review": {
        "description": (
            "A review-oriented DAG that connects checkpoint evaluation, physics validation, and the interactive "
            "lab history streams for single-case inference, uncertainty sweeps, and calibration studies."
        ),
        "nodes": [
            {
                "id": "qa_checkpoint",
                "label": "Evaluate tuned checkpoint",
                "category": "evaluation",
                "command": "python scripts/evaluation/evaluate_complete.py --test-data notebooks/data/processed/test.csv --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt --output results/full_evaluation.json --verbose",
                "depends_on": [],
                "expected_outputs": ["results/full_evaluation.json"],
                "notes": "Baseline evaluation before manual case inspection.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "qa_physics",
                "label": "Run physics validation",
                "category": "evaluation",
                "command": "python scripts/evaluation/validate_physics.py --checkpoint checkpoints/tgnn_solv_trained.pt --test-data notebooks/data/processed/test.csv --output results/physics_validation.json",
                "depends_on": ["qa_checkpoint"],
                "expected_outputs": ["results/physics_validation.json"],
                "notes": "Check whether solver-facing parameters remain physically reasonable before deep case review.",
                "launchable": True,
                "active": True,
            },
            {
                "id": "qa_inference_history",
                "label": "Curate saved inference runs",
                "category": "analysis",
                "command": "",
                "depends_on": ["qa_checkpoint"],
                "expected_outputs": ["results/lab_runs/inference_history"],
                "notes": "Human-in-the-loop node: populate the lab's saved single-system inference history and compare decomposition / OOD decisions.",
                "launchable": False,
                "active": True,
            },
            {
                "id": "qa_uncertainty_history",
                "label": "Review saved uncertainty runs",
                "category": "evaluation",
                "command": "",
                "depends_on": ["qa_checkpoint"],
                "expected_outputs": ["results/lab_runs/uncertainty_history"],
                "notes": "Human-in-the-loop node: inspect ensemble vs MC-dropout spread on the saved uncertainty history.",
                "launchable": False,
                "active": True,
            },
            {
                "id": "qa_calibration_history",
                "label": "Review calibration dashboard history",
                "category": "evaluation",
                "command": "",
                "depends_on": ["qa_uncertainty_history"],
                "expected_outputs": ["results/lab_runs/calibration_history"],
                "notes": "Human-in-the-loop node: verify coverage, sharpness, and interval efficiency on saved calibration sessions.",
                "launchable": False,
                "active": True,
            },
            {
                "id": "qa_figures",
                "label": "Refresh figure deck",
                "category": "analysis",
                "command": "python scripts/experiments/generate_paper_figures.py",
                "depends_on": ["qa_physics", "qa_calibration_history"],
                "expected_outputs": ["figures"],
                "notes": "Optional downstream refresh once inference QA and uncertainty review are complete.",
                "launchable": True,
                "active": False,
            },
        ],
    },
}

ARCHITECTURE_DEFAULTS = {
    "TGNN-Solv": CONFIG_DIR / "paper_config_tuned.yaml",
    "DirectGNN": CONFIG_DIR / "paper_config_directgnn_tuned.yaml",
}

DEFAULT_SOLUTE_SMILES = "CC(=O)Nc1ccc(O)cc1"
DEFAULT_SOLVENT_SMILES = "CCO"


def theme_palette() -> dict[str, str]:
    dark = st.get_option("theme.base") == "dark"
    if dark:
        return {
            "surface": "#111827",
            "surface_alt": "#0f172a",
            "card": "#172033",
            "text": "#F8FAFC",
            "muted": "#CBD5E1",
            "border": "#334155",
            "blue": "#60A5FA",
            "green": "#34D399",
            "orange": "#FBBF24",
            "purple": "#A78BFA",
            "red": "#F87171",
            "slate": "#94A3B8",
        }
    return {
        "surface": "#FFFFFF",
        "surface_alt": "#F8FAFC",
        "card": "#F8FAFC",
        "text": "#0F172A",
        "muted": "#475569",
        "border": "#CBD5E1",
        "blue": "#2563EB",
        "green": "#059669",
        "orange": "#D97706",
        "purple": "#7C3AED",
        "red": "#DC2626",
        "slate": "#64748B",
    }


def hex_to_rgba(color: str, alpha: float) -> str:
    value = color.strip().lstrip("#")
    if len(value) != 6:
        return color
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


def contrast_text_color(color: str) -> str:
    value = color.strip().lstrip("#")
    if len(value) != 6:
        return "#FFFFFF"
    r = int(value[0:2], 16) / 255.0
    g = int(value[2:4], 16) / 255.0
    b = int(value[4:6], 16) / 255.0

    def channel_luminance(channel: float) -> float:
        if channel <= 0.03928:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    luminance = (
        0.2126 * channel_luminance(r)
        + 0.7152 * channel_luminance(g)
        + 0.0722 * channel_luminance(b)
    )
    return "#0F172A" if luminance > 0.46 else "#F8FAFC"


def accent_scale(color: str) -> list[list[float | str]]:
    return [
        [0.0, hex_to_rgba(color, 0.18)],
        [0.55, hex_to_rgba(color, 0.55)],
        [1.0, color],
    ]


def accent_pill_style(color: str) -> str:
    text_color = color
    return (
        f"background:{hex_to_rgba(color, 0.16)};"
        f"border-color:{hex_to_rgba(color, 0.32)};"
        f"color:{text_color};"
    )


def category_color(category: str) -> str:
    palette = theme_palette()
    mapping = {
        "data": palette["blue"],
        "training": palette["green"],
        "experiments": palette["purple"],
        "evaluation": palette["orange"],
        "analysis": palette["slate"],
        "baseline": palette["red"],
        "paper": palette["orange"],
    }
    return mapping.get(category, palette["slate"])


def slugify_label(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "custom_node"


def resolve_repo_path(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else (REPO_ROOT / path)


def json_safe_copy(payload: Any) -> Any:
    return json.loads(json.dumps(payload))


def normalize_config_document(data: dict[str, Any] | None) -> dict[str, Any]:
    doc = copy.deepcopy(data or {})
    for section in ("model", "training", "loss_weights", "stage0"):
        value = doc.get(section)
        if not isinstance(value, dict):
            doc[section] = {}
    return doc


def flatten_nested_dict(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    items: dict[str, str] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            items.update(flatten_nested_dict(value, full_key))
        elif isinstance(value, list):
            items[full_key] = ", ".join(str(item) for item in value)
        else:
            items[full_key] = "—" if value is None else str(value)
    return items


def config_diff_frame(base_doc: dict[str, Any], current_doc: dict[str, Any]) -> pd.DataFrame:
    base_flat = flatten_nested_dict(base_doc)
    current_flat = flatten_nested_dict(current_doc)
    keys = sorted(set(base_flat) | set(current_flat))
    rows = []
    for key in keys:
        base_value = base_flat.get(key, "—")
        current_value = current_flat.get(key, "—")
        if base_value != current_value:
            rows.append({"field": key, "base": base_value, "current": current_value})
    return pd.DataFrame(rows)


def load_architecture_doc(family: str, config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    base = cached_yaml(str(path)) if path.exists() else {}
    doc = normalize_config_document(base if isinstance(base, dict) else {})
    model = doc.setdefault("model", {})
    training = doc.setdefault("training", {})
    if family == "TGNN-Solv":
        model.setdefault("encoder_type", "mpnn")
        model.setdefault("gps_num_heads", 4)
        model.setdefault("gps_use_edge_attr", True)
        model.setdefault("gps_positional_encoding", "laplacian")
        model.setdefault("gps_pe_dim", 8)
        model.setdefault("hidden_dim", 256)
        model.setdefault("pair_dim", 512)
        model.setdefault("n_gnn_layers", 6)
        model.setdefault("encoder_role_mode", "shared_residual")
        model.setdefault("interaction_mode", "cross_attn")
        model.setdefault("n_cross_attn_layers", 3)
        model.setdefault("n_attn_heads", 8)
        model.setdefault("dropout", 0.1)
        model.setdefault("set2set_steps", 3)
        model.setdefault("use_solvent_moe", True)
        model.setdefault("use_morgan_features", False)
        model.setdefault("use_descriptor_augmentation", False)
        model.setdefault("use_descriptor_priors", False)
        model.setdefault("use_group_priors", False)
        model.setdefault("use_gc_priors_crystal", False)
        model.setdefault("use_oracle_injection", False)
        model.setdefault("nrtl_tau_mode", "ref_invT")
        model.setdefault("use_implicit_diff", True)
        model.setdefault("use_temperature_in_nrtl_head", True)
    else:
        model.setdefault("encoder_type", "mpnn")
        model.setdefault("gps_num_heads", 4)
        model.setdefault("gps_use_edge_attr", True)
        model.setdefault("gps_positional_encoding", "laplacian")
        model.setdefault("gps_pe_dim", 8)
        model.setdefault("hidden_dim", 256)
        model.setdefault("pair_dim", 512)
        model.setdefault("n_gnn_layers", 6)
        model.setdefault("encoder_role_mode", "shared_residual")
        model.setdefault("interaction_mode", "cross_attn")
        model.setdefault("n_cross_attn_layers", 3)
        model.setdefault("n_attn_heads", 8)
        model.setdefault("dropout", 0.1)
        model.setdefault("set2set_steps", 3)
        model.setdefault("use_morgan_features", False)
        model.setdefault("use_descriptor_augmentation", False)
        model.setdefault("descriptor_hidden_dim", 128)
    training.setdefault("batch_size", 64)
    training.setdefault("epochs_phase1", 50)
    training.setdefault("epochs_phase2", 200)
    training.setdefault("epochs_phase3", 50)
    training.setdefault("use_pair_temperature_batching", True)
    stage0 = doc.setdefault("stage0", {})
    stage0.setdefault("enabled", False)
    stage0.setdefault("mode", "fresh")
    stage0.setdefault("pretrain_data", "zinc250k")
    stage0.setdefault("pretrain_epochs", 30)
    stage0.setdefault("pretrain_batch_size", 128)
    stage0.setdefault("pretrain_lr", 3.0e-4)
    stage0.setdefault("pretrain_max_molecules", None)
    stage0.setdefault("pretrain_checkpoint", "")
    stage0.setdefault("pretrain_output", "")
    stage0.setdefault("run_descriptor_probe", True)
    stage0.setdefault("descriptor_probe_output_dir", "")
    stage0.setdefault("descriptor_probe_device", "cpu")
    return doc


def yaml_dump_text(data: dict[str, Any]) -> str:
    if yaml is not None:
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
    return json.dumps(data, indent=2, ensure_ascii=True)


def model_cardinality_stats(smiles: str) -> dict[str, Any] | None:
    if Chem is None:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    ring_info = mol.GetRingInfo()
    hetero = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() not in {1, 6})
    aromatic = sum(1 for atom in mol.GetAtoms() if atom.GetIsAromatic())
    return {
        "atoms": mol.GetNumAtoms(),
        "bonds": mol.GetNumBonds(),
        "rings": ring_info.NumRings(),
        "heteroatoms": hetero,
        "aromatic_atoms": aromatic,
    }


def molecule_graph_figure(smiles: str, title: str | None = None, *, height: int = 520) -> go.Figure | None:
    if Chem is None or AllChem is None:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.Mol(mol)
    try:
        AllChem.Compute2DCoords(mol)
    except Exception:
        return None

    conf = mol.GetConformer()
    xs: list[float] = []
    ys: list[float] = []
    elements: list[str] = []
    hover: list[str] = []
    for atom in mol.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        xs.append(float(pos.x))
        ys.append(float(-pos.y))
        elements.append(atom.GetSymbol())
        hover.append(
            f"{atom.GetSymbol()} · idx {atom.GetIdx()}<br>"
            f"degree {atom.GetDegree()} · aromatic {atom.GetIsAromatic()} · ring {atom.IsInRing()}"
        )

    palette = theme_palette()
    element_colors = {
        "C": palette["slate"],
        "N": palette["blue"],
        "O": palette["red"],
        "S": palette["orange"],
        "Cl": palette["green"],
        "F": palette["green"],
        "Br": palette["orange"],
    }
    bond_x: list[float] = []
    bond_y: list[float] = []
    for bond in mol.GetBonds():
        begin_pos = conf.GetAtomPosition(bond.GetBeginAtomIdx())
        end_pos = conf.GetAtomPosition(bond.GetEndAtomIdx())
        bond_x.extend([float(begin_pos.x), float(end_pos.x), None])
        bond_y.extend([float(-begin_pos.y), float(-end_pos.y), None])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=bond_x,
            y=bond_y,
            mode="lines",
            line={"color": palette["border"], "width": 2.1},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            text=elements,
            textposition="middle center",
            hovertext=hover,
            hovertemplate="%{hovertext}<extra></extra>",
            marker={
                "size": 34,
                "color": [element_colors.get(element, palette["muted"]) for element in elements],
                "line": {"color": palette["surface"], "width": 1.5},
            },
            textfont={"size": 14, "color": palette["surface"] if st.get_option("theme.base") != "dark" else palette["surface_alt"]},
            showlegend=False,
        )
    )
    layout_kwargs: dict[str, Any] = {
        "template": plotly_template(),
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": dict(l=8, r=8, t=28 if not title else 46, b=8),
        "height": height,
        "xaxis": {"visible": False},
        "yaxis": {"visible": False, "scaleanchor": "x", "scaleratio": 1},
    }
    layout_kwargs["title"] = {"text": title or ""}
    fig.update_layout(**layout_kwargs)
    return fig


def render_stat_tiles(entries: list[tuple[str, str, str]]) -> None:
    if not entries:
        return
    for start in range(0, len(entries), 4):
        row = entries[start:start + 4]
        cols = st.columns(4, gap="small")
        for index, col in enumerate(cols):
            if index >= len(row):
                continue
            label, value, note = row[index]
            with col:
                st.metric(label, value)
                if note:
                    st.caption(note)


def render_molecule_showcase(
    smiles: str,
    *,
    title: str,
    subtitle: str,
    svg_size: tuple[int, int] = (620, 420),
    graph_height: int = 580,
    compact: bool = False,
) -> None:
    st.markdown(f"### {title}")
    st.caption(subtitle)

    if compact:
        render_molecule_panel(
            smiles,
            "2D structure",
            "Canonical RDKit depiction from the exact current SMILES.",
            width=svg_size[0],
            height=svg_size[1],
        )
        st.markdown("**Atom graph**")
        st.caption("Node colors follow element types and the connectivity is derived from the same parsed structure.")
        graph_fig = molecule_graph_figure(smiles, None, height=graph_height)
        if graph_fig is not None:
            st.plotly_chart(style_plot(graph_fig), use_container_width=True)
        else:
            st.warning("RDKit could not build an atom graph from this SMILES string.")
    else:
        media_left, media_right = st.columns([0.9, 1.1], gap="large")
        with media_left:
            render_molecule_panel(
                smiles,
                "2D structure",
                "Canonical RDKit depiction from the exact current SMILES.",
                width=svg_size[0],
                height=svg_size[1],
            )
        with media_right:
            st.markdown("**Atom graph**")
            st.caption("Node colors follow element types and the connectivity is derived from the same parsed structure.")
            graph_fig = molecule_graph_figure(smiles, None, height=graph_height)
            if graph_fig is not None:
                st.plotly_chart(style_plot(graph_fig), use_container_width=True)
            else:
                st.warning("RDKit could not build an atom graph from this SMILES string.")

    stats = model_cardinality_stats(smiles) or {}
    desc = descriptor_summary(smiles) or {}
    stat_entries = [
        ("Atoms", str(stats.get("atoms", "—")), "graph nodes"),
        ("Bonds", str(stats.get("bonds", "—")), "graph edges"),
        ("Rings", str(stats.get("rings", "—")), "ring systems"),
        ("Hetero", str(stats.get("heteroatoms", "—")), "non-carbon atoms"),
        ("Aromatic", str(stats.get("aromatic_atoms", "—")), "aromatic atoms"),
        ("MolWt", f"{float(desc.get('MolWt', 0.0)):.1f}" if desc else "—", "g/mol"),
        ("LogP", f"{float(desc.get('MolLogP', 0.0)):.2f}" if desc else "—", "RDKit"),
        ("TPSA", f"{float(desc.get('TPSA', 0.0)):.1f}" if desc else "—", "A^2"),
    ]
    render_stat_tiles(stat_entries)


def render_structure_editor_preview(
    role: str,
    canonical_smiles: str | None,
    *,
    raw_smiles: str | None = None,
    error: str | None = None,
) -> None:
    with st.container(border=True):
        st.markdown(f"#### {role} sanitized preview")
        st.caption(
            "Normalized RDKit structure and atom graph derived from the current drawing. This is what will be sent to the model after sync."
        )
        if error:
            st.warning(error)
            return
        if not canonical_smiles:
            st.info("Draw a valid structure to populate this preview.")
            return

        summary = normalized_structure_summary(canonical_smiles, raw_smiles) or {}
        normalized_smiles = str(summary.get("canonical_smiles", canonical_smiles))
        status_labels = [
            ("RDKit", "parsed"),
            ("Sanitize", "ok"),
            ("Canonical", str(summary.get("normalization", "same"))),
            ("Formula", str(summary.get("formula", "—"))),
        ]
        chips = "".join(
            f'<span class="lab-chip"><strong>{escape(label)}</strong><span>{escape(value)}</span></span>'
            for label, value in status_labels
        )
        st.markdown(f'<div class="lab-chip-row">{chips}</div>', unsafe_allow_html=True)
        if raw_smiles and str(raw_smiles).strip() and str(raw_smiles).strip() != normalized_smiles:
            st.caption("The editor export was canonicalized before preview, so the normalized SMILES differs from the raw drawing output.")
        st.code(normalized_smiles, language="text")

        render_molecule_panel(
            normalized_smiles,
            "2D structure",
            "Sanitized RDKit depiction from the editor payload.",
            width=460,
            height=300,
        )
        st.markdown("**Atom graph**")
        st.caption("Connectivity preview from the same parsed molecule.")
        graph_fig = molecule_graph_figure(normalized_smiles, None, height=340)
        if graph_fig is not None:
            st.plotly_chart(style_plot(graph_fig), use_container_width=True)
        else:
            st.warning("RDKit could not build an atom graph from this structure.")

        stats = summary.get("stats") or {}
        desc = summary.get("descriptors") or {}
        render_stat_tiles(
            [
                ("Atoms", str(stats.get("atoms", "—")), "graph nodes"),
                ("Bonds", str(stats.get("bonds", "—")), "graph edges"),
                ("Heavy", str(summary.get("heavy_atoms", "—")), "non-hydrogen atoms"),
                ("Fragments", str(summary.get("fragments", "—")), "connected components"),
                ("Charge", str(summary.get("formal_charge", "—")), "formal charge"),
                ("Stereo", str(summary.get("stereocenters", "—")), "assigned or unassigned centers"),
                ("LogP", f"{float(desc.get('MolLogP', 0.0)):.2f}" if desc else "—", "RDKit"),
                ("TPSA", f"{float(desc.get('TPSA', 0.0)):.1f}" if desc else "—", "A^2"),
            ]
        )



def repo_pipeline_presets() -> dict[str, dict[str, Any]]:
    presets: dict[str, dict[str, Any]] = {}
    for path in sorted(PIPELINE_PRESETS_DIR.glob("*.json")):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        nodes = payload.get("nodes")
        if not isinstance(nodes, list):
            continue
        name = str(payload.get("name") or path.stem.replace("_", " "))
        payload["_path"] = str(path)
        presets[name] = payload
    return presets


def pipeline_preset_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for name, payload in PIPELINE_PRESETS.items():
        catalog[f"Built-in · {name}"] = {
            "name": name,
            "description": payload.get("description", ""),
            "nodes": json_safe_copy(payload.get("nodes", [])),
            "kind": "builtin",
        }
    for name, payload in repo_pipeline_presets().items():
        catalog[f"Repo · {name}"] = {
            "name": name,
            "description": payload.get("description", ""),
            "nodes": json_safe_copy(payload.get("nodes", [])),
            "kind": "repo",
            "path": payload.get("_path"),
            "saved_at": payload.get("saved_at"),
        }
    return catalog


def save_repo_pipeline_preset(
    *,
    name: str,
    description: str,
    nodes: list[dict[str, Any]],
    source_label: str,
) -> Path:
    target = PIPELINE_PRESETS_DIR / f"{slugify_label(name)}.json"
    payload = {
        "name": name,
        "description": description,
        "nodes": nodes,
        "source_label": source_label,
        "saved_at": utc_now(),
    }
    write_json(target, payload)
    return target


def delete_repo_pipeline_preset_by_name(name: str) -> bool:
    path = PIPELINE_PRESETS_DIR / f"{slugify_label(name)}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def short_smiles_label(smiles: str, limit: int = 20) -> str:
    value = str(smiles)
    return value if len(value) <= limit else value[: limit - 1] + "…"


def inference_history_label(record: dict[str, Any]) -> str:
    checkpoint = Path(str(record.get("checkpoint", ""))).stem or "checkpoint"
    family = str(record.get("model_family", "tgnn_solv"))
    family_tag = "Direct" if family == "direct_gnn" else "TGNN"
    return (
        f"{format_timestamp(record.get('created_at'))} · "
        f"{short_smiles_label(str(record.get('solute_smiles', '')))} in "
        f"{short_smiles_label(str(record.get('solvent_smiles', '')), 14)} · "
        f"{float(record.get('temperature', 0.0)):.1f} K · {family_tag} · {checkpoint}"
    )


def save_inference_record(
    *,
    checkpoint_path: str,
    model_family: str,
    solute: str,
    solvent: str,
    temperature: float,
    scan_tmin: float,
    scan_tmax: float,
    scan_points: int,
    mc_samples: int,
    run_mc: bool,
    reference_csv: str,
    domain_csv: str,
    run_domain: bool,
    payload: dict[str, Any],
) -> Path:
    result = payload.get("prediction", {})
    record = {
        "id": f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "created_at": utc_now(),
        "checkpoint": checkpoint_path,
        "model_family": model_family,
        "solute_smiles": solute,
        "solvent_smiles": solvent,
        "temperature": float(temperature),
        "scan_tmin": float(scan_tmin),
        "scan_tmax": float(scan_tmax),
        "scan_points": int(scan_points),
        "mc_samples": int(mc_samples),
        "run_mc": bool(run_mc),
        "reference_csv": reference_csv,
        "domain_csv": domain_csv,
        "run_domain": bool(run_domain),
        "prediction": result,
        "scan": payload.get("scan", []),
        "interpretation": payload.get("interpretation", ""),
        "config": payload.get("config", {}),
        "mc_dropout": payload.get("mc_dropout"),
        "domain": payload.get("domain"),
        "domain_report": payload.get("domain_report"),
    }
    target = INFERENCE_HISTORY_DIR / f"{record['id']}.json"
    write_json(target, record)
    return target


def load_inference_history() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(INFERENCE_HISTORY_DIR.glob("*.json"), reverse=True):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict) or "prediction" not in payload:
            continue
        payload["_path"] = str(path)
        records.append(payload)
    records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return records


def delete_inference_records(record_ids: list[str]) -> int:
    deleted = 0
    wanted = set(record_ids)
    for path in INFERENCE_HISTORY_DIR.glob("*.json"):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if str(payload.get("id")) in wanted:
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted


def inference_history_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        prediction = record.get("prediction", {})
        rows.append(
            {
                "id": record.get("id"),
                "created_at": format_timestamp(record.get("created_at")),
                "pair": f"{short_smiles_label(str(record.get('solute_smiles', '')), 18)} in {short_smiles_label(str(record.get('solvent_smiles', '')), 14)}",
                "family": str(record.get("model_family", "tgnn_solv")),
                "T": round(float(record.get("temperature", 0.0)), 2),
                "ln_x2": round(float(prediction.get("ln_x2", float("nan"))), 4),
                "gamma_2": round(float(prediction.get("gamma_2", float("nan"))), 4),
                "Phi": round(float(prediction.get("Phi", float("nan"))), 4),
                "ood_conf": round(float((record.get("domain") or {}).get("confidence", float("nan"))), 4),
                "in_domain": bool((record.get("domain") or {}).get("in_domain")) if record.get("domain") else None,
                "checkpoint": Path(str(record.get("checkpoint", ""))).name,
            }
        )
    return pd.DataFrame(rows)


def uncertainty_history_label(record: dict[str, Any]) -> str:
    checkpoints = record.get("checkpoints", [])
    count = len(checkpoints) if isinstance(checkpoints, list) else 0
    return (
        f"{format_timestamp(record.get('created_at'))} · "
        f"{short_smiles_label(str(record.get('solute_smiles', '')))} in "
        f"{short_smiles_label(str(record.get('solvent_smiles', '')), 14)} · "
        f"{float(record.get('temperature', 0.0)):.1f} K · {count} ckpt"
    )


def save_uncertainty_record(
    *,
    solute: str,
    solvent: str,
    temperature: float,
    scan_tmin: float,
    scan_tmax: float,
    scan_points: int,
    mc_samples: int,
    checkpoints: tuple[str, ...],
    include_mc: bool,
    model_family: str,
    payload: dict[str, Any],
) -> Path:
    record = {
        "id": f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "created_at": utc_now(),
        "solute_smiles": solute,
        "solvent_smiles": solvent,
        "temperature": float(temperature),
        "scan_tmin": float(scan_tmin),
        "scan_tmax": float(scan_tmax),
        "scan_points": int(scan_points),
        "mc_samples": int(mc_samples),
        "checkpoints": list(checkpoints),
        "include_mc": bool(include_mc),
        "model_family": str(model_family),
        "n_models": int(payload.get("n_models", len(checkpoints))),
        "ensemble": payload.get("ensemble"),
        "mc_dropout": payload.get("mc_dropout"),
        "member_predictions": payload.get("member_predictions", []),
        "ensemble_scan": payload.get("ensemble_scan", []),
        "mc_scan": payload.get("mc_scan", []),
        "payload": payload,
    }
    target = UNCERTAINTY_HISTORY_DIR / f"{record['id']}.json"
    write_json(target, record)
    return target


def load_uncertainty_history() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(UNCERTAINTY_HISTORY_DIR.glob("*.json"), reverse=True):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        payload["_path"] = str(path)
        records.append(payload)
    records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return records


def delete_uncertainty_records(record_ids: list[str]) -> int:
    deleted = 0
    wanted = set(record_ids)
    for path in UNCERTAINTY_HISTORY_DIR.glob("*.json"):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if str(payload.get("id")) in wanted:
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted


def uncertainty_history_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        ensemble = record.get("ensemble") or {}
        mc = record.get("mc_dropout") or {}
        rows.append(
            {
                "id": record.get("id"),
                "created_at": format_timestamp(record.get("created_at")),
                "pair": f"{short_smiles_label(str(record.get('solute_smiles', '')), 18)} in {short_smiles_label(str(record.get('solvent_smiles', '')), 14)}",
                "family": str(record.get("model_family", "tgnn_solv")),
                "T": round(float(record.get("temperature", 0.0)), 2),
                "n_models": int(record.get("n_models", 0) or 0),
                "ensemble_std": round(float(ensemble.get("ln_x2_std", float("nan"))), 4) if ensemble else np.nan,
                "mc_std": round(float(mc.get("ln_x2_std", float("nan"))), 4) if mc else np.nan,
                "checkpoints": ", ".join(Path(str(path)).name for path in record.get("checkpoints", [])[:3]),
            }
        )
    return pd.DataFrame(rows)


def calibration_history_label(record: dict[str, Any]) -> str:
    dataset = Path(str(record.get("dataset_csv", ""))).name or "dataset"
    methods = ",".join(sorted((record.get("reports") or {}).keys()))
    return (
        f"{format_timestamp(record.get('created_at'))} · "
        f"{dataset} · {int(record.get('n_rows', 0) or 0)} rows · {methods or 'methods'}"
    )


def save_calibration_record(
    *,
    dataset_csv: str,
    sample_rows: int,
    mc_samples: int,
    checkpoints: tuple[str, ...],
    include_mc: bool,
    include_ensemble: bool,
    model_family: str,
    payload: dict[str, Any],
) -> Path:
    record = {
        "id": f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "created_at": utc_now(),
        "dataset_csv": dataset_csv,
        "sample_rows": int(sample_rows),
        "mc_samples": int(mc_samples),
        "checkpoints": list(checkpoints),
        "include_mc": bool(include_mc),
        "include_ensemble": bool(include_ensemble),
        "model_family": str(model_family),
        "n_rows": int(payload.get("n_rows", 0) or 0),
        "reports": payload.get("reports", {}),
        "samples": payload.get("samples", {}),
        "payload": payload,
    }
    target = CALIBRATION_HISTORY_DIR / f"{record['id']}.json"
    write_json(target, record)
    return target


def load_calibration_history() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(CALIBRATION_HISTORY_DIR.glob("*.json"), reverse=True):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        payload["_path"] = str(path)
        records.append(payload)
    records.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return records


def delete_calibration_records(record_ids: list[str]) -> int:
    deleted = 0
    wanted = set(record_ids)
    for path in CALIBRATION_HISTORY_DIR.glob("*.json"):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if str(payload.get("id")) in wanted:
            path.unlink(missing_ok=True)
            deleted += 1
    return deleted


def calibration_history_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        reports = record.get("reports") or {}
        ensemble = reports.get("ensemble") or {}
        mc = reports.get("mc_dropout") or {}
        rows.append(
            {
                "id": record.get("id"),
                "created_at": format_timestamp(record.get("created_at")),
                "dataset": Path(str(record.get("dataset_csv", ""))).name,
                "family": str(record.get("model_family", "tgnn_solv")),
                "rows": int(record.get("n_rows", 0) or 0),
                "n_checkpoints": len(record.get("checkpoints", [])),
                "ensemble_PICP": round(float(ensemble.get("PICP_90", float("nan"))), 4) if ensemble else np.nan,
                "mc_PICP": round(float(mc.get("PICP_90", float("nan"))), 4) if mc else np.nan,
                "methods": ", ".join(sorted(reports.keys())),
            }
        )
    return pd.DataFrame(rows)


def history_record_entries(limit: int = 24) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for kind, records in [
        ("inference", load_inference_history()),
        ("uncertainty", load_uncertainty_history()),
        ("calibration", load_calibration_history()),
    ]:
        for record in records[:limit]:
            path_value = str(record.get("_path", ""))
            if not path_value:
                continue
            path = Path(path_value)
            created_at = str(record.get("created_at", ""))
            checkpoints: list[str] = []
            dataset_csv = ""
            title = ""
            subtitle = ""
            notes = ""
            suggested_command = "python scripts/launch_lab.py"
            if kind == "inference":
                checkpoint = str(record.get("checkpoint", ""))
                checkpoints = [checkpoint] if checkpoint else []
                model_family = str(record.get("model_family", "tgnn_solv"))
                title = f"Inference review · {short_smiles_label(str(record.get('solute_smiles', '')), 18)} in {short_smiles_label(str(record.get('solvent_smiles', '')), 14)}"
                subtitle = f"{float(record.get('temperature', 0.0)):.1f} K · ln x₂ {float((record.get('prediction') or {}).get('ln_x2', float('nan'))):.3f}"
                notes = (
                    f"Saved inference run at {relative_label(path)}.\n"
                    f"Pair: {record.get('solute_smiles', '')} in {record.get('solvent_smiles', '')} @ {float(record.get('temperature', 0.0)):.2f} K.\n"
                    f"Checkpoint: {checkpoint or '—'}.\n"
                    + (
                        "Use this task to inspect decomposition, OOD status, and temperature scan drift."
                        if model_family == "tgnn_solv"
                        else "Use this task to inspect direct prediction behavior, temperature trends, and feature-side baseline context."
                    )
                )
                if checkpoint:
                    if model_family == "tgnn_solv":
                        suggested_command = (
                            f"python scripts/evaluation/evaluate_complete.py --test-data notebooks/data/processed/test.csv "
                            f"--tgnn-checkpoint {shlex.quote(checkpoint)} --output results/followup_inference_eval.json --verbose"
                        )
            elif kind == "uncertainty":
                checkpoints = [str(item) for item in record.get("checkpoints", []) if item]
                ensemble = record.get("ensemble") or {}
                title = f"Uncertainty run · {short_smiles_label(str(record.get('solute_smiles', '')), 18)} in {short_smiles_label(str(record.get('solvent_smiles', '')), 14)}"
                subtitle = (
                    f"{len(checkpoints)} ckpt · ensemble std "
                    f"{float(ensemble.get('ln_x2_std', float('nan'))):.3f}" if ensemble else f"{len(checkpoints)} ckpt · MC-only"
                )
                notes = (
                    f"Saved uncertainty run at {relative_label(path)}.\n"
                    f"Pair: {record.get('solute_smiles', '')} in {record.get('solvent_smiles', '')} @ {float(record.get('temperature', 0.0)):.2f} K.\n"
                    f"Checkpoints: {', '.join(relative_label(Path(item)) for item in checkpoints) or '—'}.\n"
                    f"Use this task to compare ensemble vs MC-dropout spread and decide whether more seeds or calibration are needed."
                )
            else:
                dataset_csv = str(record.get("dataset_csv", ""))
                checkpoints = [str(item) for item in record.get("checkpoints", []) if item]
                methods = ", ".join(sorted((record.get("reports") or {}).keys())) or "methods"
                title = f"Calibration run · {Path(dataset_csv).name or 'dataset'}"
                subtitle = f"{int(record.get('n_rows', 0) or 0)} rows · {methods}"
                notes = (
                    f"Saved calibration run at {relative_label(path)}.\n"
                    f"Dataset: {dataset_csv or '—'} with {int(record.get('n_rows', 0) or 0)} sampled rows.\n"
                    f"Checkpoints: {', '.join(relative_label(Path(item)) for item in checkpoints) or '—'}.\n"
                    f"Use this task to review PICP, interval width, and whether the uncertainty story is publication-ready."
                )

            entries.append(
                {
                    "kind": kind,
                    "created_at": created_at,
                    "path": str(path),
                    "label": f"{format_timestamp(created_at)} · {title}",
                    "title": title,
                    "subtitle": subtitle,
                    "notes": notes,
                    "checkpoints": checkpoints,
                    "dataset_csv": dataset_csv,
                    "suggested_command": suggested_command,
                }
            )
    entries.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return entries[:limit]


def unique_planner_task_id(tasks: list[dict[str, Any]], base: str) -> str:
    existing = {str(task.get("id")) for task in tasks if isinstance(task, dict)}
    candidate = slugify_label(base)[:32] or "task"
    suffix = 1
    while candidate in existing:
        candidate = slugify_label(f"{base}_{suffix}")[:32] or f"task_{suffix}"
        suffix += 1
    return candidate


def add_planner_task_from_history(payload: dict[str, Any], entry: dict[str, Any]) -> tuple[str, bool]:
    tasks = payload.setdefault("tasks", [])
    for task in tasks:
        if str(task.get("artifact_path", "")) == str(entry.get("path", "")):
            return str(task.get("id", "")), False
    task_id = unique_planner_task_id(tasks, f"{entry.get('kind', 'history')}_{Path(str(entry.get('path', ''))).stem}")
    task = {
        "id": task_id,
        "title": str(entry.get("title", "History follow-up")),
        "status": "Ready",
        "priority": "P2",
        "owner": "analysis",
        "start": datetime.now().date().isoformat(),
        "end": datetime.now().date().isoformat(),
        "estimate_hours": 2.0,
        "notes": str(entry.get("notes", "")),
        "command": str(entry.get("suggested_command", "")),
        "artifact_path": str(entry.get("path", "")),
        "history_kind": str(entry.get("kind", "")),
        "related_checkpoints": list(entry.get("checkpoints", [])),
        "related_dataset": str(entry.get("dataset_csv", "")),
    }
    tasks.append(task)
    payload.setdefault("board", {}).setdefault("Ready", []).append(task_id)
    return task_id, True


def pipeline_node_from_history_entry(entry: dict[str, Any], existing_ids: set[str]) -> dict[str, Any]:
    base_id = slugify_label(f"{entry.get('kind', 'history')}_{Path(str(entry.get('path', ''))).stem}")[:40] or "history_artifact"
    node_id = base_id
    suffix = 1
    while node_id in existing_ids:
        node_id = slugify_label(f"{base_id}_{suffix}")[:40] or f"history_artifact_{suffix}"
        suffix += 1
    category = "evaluation" if entry.get("kind") in {"uncertainty", "calibration"} else "analysis"
    artifact_path = str(entry.get("path", ""))
    notes = str(entry.get("notes", ""))
    if artifact_path:
        notes = f"{notes}\n\nArtifact: {artifact_path}"
    return {
        "id": node_id,
        "label": str(entry.get("title", "History artifact")),
        "category": category,
        "command": "",
        "depends_on": [],
        "expected_outputs": [artifact_path] if artifact_path else [],
        "notes": notes,
        "launchable": False,
        "active": True,
        "artifact_path": artifact_path,
        "history_kind": str(entry.get("kind", "")),
    }


def planner_task_references_artifact(task: dict[str, Any], artifact_path: Path) -> bool:
    targets = [str(task.get("artifact_path", "")), str(task.get("related_dataset", ""))]
    targets.extend(str(item) for item in task.get("related_checkpoints", []) if item)
    artifact_abs = str(artifact_path.resolve())
    artifact_rel = relative_label(artifact_path)
    for target in targets:
        if not target:
            continue
        try:
            target_abs = str(Path(target).resolve())
        except Exception:
            target_abs = target
        if target == artifact_abs or target_abs == artifact_abs:
            return True
        if artifact_rel == target or artifact_rel in target:
            return True
        try:
            if relative_label(Path(target)) == artifact_rel:
                return True
        except Exception:
            continue
    return False


def history_lineage_context(path: Path) -> dict[str, Any]:
    kind = artifact_kind(path)
    if kind not in {"inference_history", "uncertainty_history", "calibration_history"}:
        return {}
    payload = cached_json(str(path))
    if not isinstance(payload, dict):
        return {}
    if kind == "inference_history":
        return {
            "pair_label": (
                f"{short_smiles_label(str(payload.get('solute_smiles', '')), 18)} in "
                f"{short_smiles_label(str(payload.get('solvent_smiles', '')), 14)} @ {float(payload.get('temperature', 0.0)):.1f} K"
            ),
            "checkpoints": [str(payload.get("checkpoint", ""))] if payload.get("checkpoint") else [],
            "datasets": [str(payload.get("reference_csv", "")), str(payload.get("domain_csv", ""))],
            "methods": ["predict_solubility", "temperature_scan"],
        }
    if kind == "uncertainty_history":
        methods = ["ensemble"]
        if payload.get("mc_dropout"):
            methods.append("mc_dropout")
        return {
            "pair_label": (
                f"{short_smiles_label(str(payload.get('solute_smiles', '')), 18)} in "
                f"{short_smiles_label(str(payload.get('solvent_smiles', '')), 14)} @ {float(payload.get('temperature', 0.0)):.1f} K"
            ),
            "checkpoints": [str(item) for item in payload.get("checkpoints", []) if item],
            "datasets": [],
            "methods": methods,
        }
    return {
        "dataset_label": Path(str(payload.get("dataset_csv", ""))).name or "dataset",
        "checkpoints": [str(item) for item in payload.get("checkpoints", []) if item],
        "datasets": [str(payload.get("dataset_csv", ""))],
        "methods": sorted((payload.get("reports") or {}).keys()),
    }


def branch_state_label(state: str) -> str:
    labels = {
        "core": "core",
        "active": "active",
        "off": "off",
        "removed": "removed",
    }
    return labels.get(state, state)


def architecture_branch_rows(tgnn_doc: dict[str, Any], direct_doc: dict[str, Any]) -> pd.DataFrame:
    tgnn_model = tgnn_doc.get("model", {})
    direct_model = direct_doc.get("model", {})
    rows = [
        {
            "module": "Encoder family",
            "track": "shared backbone",
            "tgnn": "active" if tgnn_model.get("encoder_type", "mpnn") == "gps" else "core",
            "direct": "active" if direct_model.get("encoder_type", "mpnn") == "gps" else "core",
            "explanation": "Both model families can keep the same downstream contract while swapping the local MPNN encoder for GPSEncoder.",
        },
        {
            "module": "Positional encoding",
            "track": "shared backbone",
            "tgnn": "active" if tgnn_model.get("encoder_type", "mpnn") == "gps" else "off",
            "direct": "active" if direct_model.get("encoder_type", "mpnn") == "gps" else "off",
            "explanation": "GPS mode appends Laplacian or RWSE structural positional features before graph-global attention.",
        },
        {
            "module": "Shared GNN encoder",
            "track": "shared backbone",
            "tgnn": "core",
            "direct": "core",
            "explanation": "Dual-graph encoder with role-specific adapters if enabled.",
        },
        {
            "module": "Interaction stack",
            "track": "shared backbone",
            "tgnn": "core",
            "direct": "core",
            "explanation": "Cross-attention or bipartite message passing across solute and solvent atoms.",
        },
        {
            "module": "Physics-aware readout",
            "track": "shared backbone",
            "tgnn": "core",
            "direct": "core",
            "explanation": "Set2Set-style graph readout before the heads diverge.",
        },
        {
            "module": "Morgan adapter",
            "track": "optional shared branch",
            "tgnn": "active" if tgnn_model.get("use_morgan_features") else "off",
            "direct": "active" if direct_model.get("use_morgan_features") else "off",
            "explanation": "Fingerprint side-channel projected into the learned graph representation.",
        },
        {
            "module": "Descriptor augmentation",
            "track": "optional shared branch",
            "tgnn": "active" if tgnn_model.get("use_descriptor_augmentation") else "off",
            "direct": "active" if direct_model.get("use_descriptor_augmentation") else "off",
            "explanation": "Normalized RDKit descriptors are fused into the pair state after graph interaction and readout.",
        },
        {
            "module": "Solvent-type MoE",
            "track": "tgnn-only",
            "tgnn": "active" if tgnn_model.get("use_solvent_moe") else "off",
            "direct": "removed",
            "explanation": "Solvent-aware routing after pair construction.",
        },
        {
            "module": "Descriptor priors",
            "track": "tgnn-only",
            "tgnn": "active" if tgnn_model.get("use_descriptor_priors") else "off",
            "direct": "removed",
            "explanation": "Bounded residuals around compact chemistry priors.",
        },
        {
            "module": "Group priors",
            "track": "tgnn-only",
            "tgnn": "active" if tgnn_model.get("use_group_priors") else "off",
            "direct": "removed",
            "explanation": "Fixed fragment-count priors before the physics path.",
        },
        {
            "module": "GC crystal priors",
            "track": "tgnn-only",
            "tgnn": "active" if tgnn_model.get("use_gc_priors_crystal") else "off",
            "direct": "removed",
            "explanation": "Joback-style crystal priors with bounded residual learning.",
        },
        {
            "module": "FusionHead",
            "track": "tgnn-only",
            "tgnn": "core",
            "direct": "removed",
            "explanation": "Predicts T_m, dH_fus, and optional dCp_fus.",
        },
        {
            "module": "NRTLHead",
            "track": "tgnn-only",
            "tgnn": "core",
            "direct": "removed",
            "explanation": "Predicts interaction parameters before the solver.",
        },
        {
            "module": "SLE solver",
            "track": "tgnn-only",
            "tgnn": "core",
            "direct": "removed",
            "explanation": "Zero-parameter thermodynamic bottleneck for ln(x₂).",
        },
        {
            "module": "Adaptive correction",
            "track": "tgnn-only",
            "tgnn": "core",
            "direct": "removed",
            "explanation": "Bounded parameter-space deltas after the physics solve.",
        },
        {
            "module": "Oracle injection",
            "track": "tgnn-only",
            "tgnn": "active" if tgnn_model.get("use_oracle_injection") else "off",
            "direct": "removed",
            "explanation": "Train-time substitution of supervised crystal values into the solver path.",
        },
        {
            "module": "Implicit differentiation",
            "track": "tgnn-only",
            "tgnn": "active" if tgnn_model.get("use_implicit_diff", True) else "off",
            "direct": "removed",
            "explanation": "One-step backward pass through the fixed-point solution.",
        },
        {
            "module": "Thermometer encoder",
            "track": "direct-only",
            "tgnn": "removed",
            "direct": "core",
            "explanation": "Temperature enters DirectGNN as learned bins before the prediction MLP.",
        },
        {
            "module": "Direct ln(x₂) head",
            "track": "direct-only",
            "tgnn": "removed",
            "direct": "core",
            "explanation": "MLP bypasses all explicit thermodynamic parameterization.",
        },
    ]
    return pd.DataFrame(rows)


def branch_state_value(state: str) -> int:
    return {"removed": 0, "off": 1, "active": 2, "core": 3}.get(state, 1)


def architecture_branch_heatmap(tgnn_doc: dict[str, Any], direct_doc: dict[str, Any]) -> go.Figure:
    palette = theme_palette()
    rows = architecture_branch_rows(tgnn_doc, direct_doc)
    z = [
        [branch_state_value(value) for value in rows["tgnn"].tolist()],
        [branch_state_value(value) for value in rows["direct"].tolist()],
    ]
    text = [
        [branch_state_label(value) for value in rows["tgnn"].tolist()],
        [branch_state_label(value) for value in rows["direct"].tolist()],
    ]
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=rows["module"].tolist(),
            y=["TGNN-Solv", "DirectGNN"],
            text=text,
            texttemplate="%{text}",
            textfont={"size": 11},
            colorscale=[
                [0.0, hex_to_rgba(palette["slate"], 0.28)],
                [0.33, palette["slate"]],
                [0.66, palette["green"]],
                [1.0, palette["blue"]],
            ],
            zmin=0,
            zmax=3,
            hovertemplate="family %{y}<br>module %{x}<br>state %{text}<extra></extra>",
            showscale=False,
        )
    )
    fig.update_layout(
        title="Active-branch matrix",
        height=420,
        margin=dict(l=20, r=20, t=56, b=20),
        xaxis={"tickangle": 35},
        yaxis={"title": ""},
    )
    return fig


def architecture_track_balance_figure(branch_df: pd.DataFrame) -> go.Figure:
    palette = theme_palette()
    rows: list[dict[str, Any]] = []
    for family_name, column in [("TGNN-Solv", "tgnn"), ("DirectGNN", "direct")]:
        for track, track_df in branch_df.groupby("track"):
            core_active = int(track_df[column].isin(["core", "active"]).sum())
            optional_off = int((track_df[column] == "off").sum())
            removed = int((track_df[column] == "removed").sum())
            rows.extend(
                [
                    {"family": family_name, "track": track, "bucket": "core/active", "count": core_active},
                    {"family": family_name, "track": track, "bucket": "off", "count": optional_off},
                    {"family": family_name, "track": track, "bucket": "removed", "count": removed},
                ]
            )
    fig = px.bar(
        pd.DataFrame(rows),
        x="track",
        y="count",
        color="bucket",
        facet_row="family",
        barmode="stack",
        height=460,
        title="Branch activity by track",
        color_discrete_map={
            "core/active": palette["blue"],
            "off": palette["slate"],
            "removed": palette["red"],
        },
    )
    fig.update_layout(margin=dict(l=16, r=16, t=56, b=16), legend={"orientation": "h", "y": 1.1})
    fig.for_each_annotation(lambda ann: ann.update(text=ann.text.split("=")[-1]))
    return fig


def shared_backbone_compare_frame(tgnn_doc: dict[str, Any], direct_doc: dict[str, Any]) -> pd.DataFrame:
    tgnn_model = tgnn_doc.get("model", {})
    direct_model = direct_doc.get("model", {})
    rows = []
    keys = [
        ("hidden_dim", "hidden_dim"),
        ("n_gnn_layers", "n_gnn_layers"),
        ("encoder_role_mode", "encoder_role_mode"),
        ("interaction_mode", "interaction_mode"),
        ("n_cross_attn_layers", "n_cross_attn_layers"),
        ("n_attn_heads", "n_attn_heads"),
        ("pair_dim", "pair_dim"),
        ("dropout", "dropout"),
        ("set2set_steps", "set2set_steps"),
        ("use_morgan_features", "use_morgan_features"),
    ]
    for label, key in keys:
        left = tgnn_model.get(key)
        right = direct_model.get(key)
        rows.append({"setting": label, "TGNN-Solv": left, "DirectGNN": right, "match": left == right})
    return pd.DataFrame(rows)


def branch_strip_html(title: str, items: list[tuple[str, str]]) -> str:
    pills = "".join(
        f'<span class="lab-branch-pill" data-state="{escape(state)}">{escape(label)}</span>'
        for label, state in items
    )
    return (
        f'<div class="lab-workspace-panel"><h4>{escape(title)}</h4>'
        f'<div class="lab-branch-strip">{pills}</div></div>'
    )

def pipeline_nodes_for_preset(name: str) -> list[dict[str, Any]]:
    preset = PIPELINE_PRESETS.get(name) or next(iter(PIPELINE_PRESETS.values()))
    return json_safe_copy(preset["nodes"])


def resolve_pipeline_command(command_text: str, python_command: str) -> list[str]:
    tokens = shlex.split(command_text)
    if not tokens:
        return []
    if tokens[0] == "python":
        return [*python_command_tokens(python_command), *tokens[1:]]
    return tokens


def pipeline_output_exists(paths: list[str]) -> bool:
    if not paths:
        return False
    return all(resolve_repo_path(path).exists() for path in paths)


def pipeline_topology(nodes: list[dict[str, Any]]) -> tuple[list[str], dict[str, int], list[str]]:
    node_map = {node["id"]: node for node in nodes}
    indegree: dict[str, int] = {node["id"]: 0 for node in nodes if node.get("active", True)}
    adjacency: dict[str, list[str]] = defaultdict(list)
    errors: list[str] = []
    for node in nodes:
        if not node.get("active", True):
            continue
        for dep in node.get("depends_on", []):
            if dep not in node_map:
                errors.append(f"`{node['label']}` depends on missing node `{dep}`.")
                continue
            if not node_map[dep].get("active", True):
                errors.append(f"`{node['label']}` depends on inactive node `{dep}`.")
                continue
            adjacency[dep].append(node["id"])
            indegree[node["id"]] += 1

    queue = deque(sorted([node_id for node_id, degree in indegree.items() if degree == 0]))
    order: list[str] = []
    levels: dict[str, int] = {node_id: 0 for node_id in queue}

    while queue:
        current = queue.popleft()
        order.append(current)
        for nxt in adjacency.get(current, []):
            levels[nxt] = max(levels.get(nxt, 0), levels.get(current, 0) + 1)
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    active_count = sum(node.get("active", True) for node in nodes)
    if len(order) != active_count:
        errors.append("Cycle detected in active pipeline nodes. Remove the loop before exporting or launching the pipeline.")

    for node in nodes:
        if not node.get("active", True):
            levels[node["id"]] = levels.get(node["id"], 0)
    return order, levels, errors


def pipeline_status_map(nodes: list[dict[str, Any]]) -> dict[str, str]:
    node_map = {node["id"]: node for node in nodes}
    statuses: dict[str, str] = {}
    progress = True
    while progress:
        progress = False
        for node in nodes:
            node_id = node["id"]
            if node_id in statuses:
                continue
            if not node.get("active", True):
                statuses[node_id] = "inactive"
                progress = True
                continue
            deps = node.get("depends_on", [])
            if any(dep not in node_map or not node_map[dep].get("active", True) for dep in deps):
                statuses[node_id] = "blocked"
                progress = True
                continue
            if pipeline_output_exists(node.get("expected_outputs", [])):
                statuses[node_id] = "materialized"
                progress = True
                continue
            dep_statuses = [statuses.get(dep) for dep in deps]
            if not deps or all(status == "materialized" for status in dep_statuses):
                statuses[node_id] = "ready"
                progress = True
            elif all(status is not None for status in dep_statuses):
                statuses[node_id] = "planned"
                progress = True
    for node in nodes:
        statuses.setdefault(node["id"], "planned" if node.get("active", True) else "inactive")
    return statuses


def pipeline_summary_frame(nodes: list[dict[str, Any]]) -> pd.DataFrame:
    statuses = pipeline_status_map(nodes)
    rows = []
    for node in nodes:
        rows.append(
            {
                "id": node["id"],
                "label": node["label"],
                "category": node["category"],
                "status": statuses.get(node["id"], "planned"),
                "depends_on": ", ".join(node.get("depends_on", [])) or "—",
                "outputs": ", ".join(node.get("expected_outputs", [])) or "—",
                "launchable": node.get("launchable", True),
            }
        )
    return pd.DataFrame(rows)


def pipeline_dag_figure(nodes: list[dict[str, Any]], selected_id: str | None = None) -> go.Figure:
    palette = theme_palette()
    order, levels, _ = pipeline_topology(nodes)
    statuses = pipeline_status_map(nodes)
    groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    node_map = {node["id"]: node for node in nodes}

    ordered_nodes = [node_map[node_id] for node_id in order if node_id in node_map]
    remaining = [node for node in nodes if node["id"] not in order]
    for node in ordered_nodes + remaining:
        groups[levels.get(node["id"], 0)].append(node)

    positions: dict[str, tuple[float, float]] = {}
    max_y = 0.0
    for level, group in sorted(groups.items()):
        sorted_group = sorted(group, key=lambda item: item["label"])
        for index, node in enumerate(sorted_group):
            y = -index * 2.1
            positions[node["id"]] = (level * 4.4, y)
            max_y = min(max_y, y)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[coord[0] for coord in positions.values()] or [0],
            y=[coord[1] for coord in positions.values()] or [0],
            mode="markers",
            marker={"opacity": 0},
            hoverinfo="skip",
            showlegend=False,
        )
    )

    status_colors = {
        "materialized": palette["green"],
        "ready": palette["blue"],
        "planned": palette["orange"],
        "blocked": palette["red"],
        "inactive": palette["slate"],
    }

    for node in nodes:
        x, y = positions.get(node["id"], (0.0, 0.0))
        for dep in node.get("depends_on", []):
            if dep not in positions:
                continue
            dep_x, dep_y = positions[dep]
            fig.add_annotation(
                x=x - 0.62,
                y=y,
                ax=dep_x + 0.62,
                ay=dep_y,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1,
                arrowwidth=1.6,
                arrowcolor=palette["border"],
                opacity=0.95,
            )

    for node in nodes:
        x, y = positions.get(node["id"], (0.0, 0.0))
        status = statuses.get(node["id"], "planned")
        fill = status_colors.get(status, palette["slate"])
        border = palette["text"] if node["id"] == selected_id else fill
        node_text = contrast_text_color(fill)
        fig.add_annotation(
            x=x,
            y=y,
            showarrow=False,
            align="left",
            xanchor="center",
            yanchor="middle",
            bordercolor=border,
            borderwidth=2 if node["id"] == selected_id else 1.2,
            borderpad=13,
            bgcolor=fill,
            opacity=0.95 if node.get("active", True) else 0.5,
            font={"size": 13, "color": node_text},
            text=(
                f"<b>{escape(node['label'])}</b><br>"
                f"<span style='font-size:11px'>{escape(node['category'].upper())} · {escape(status)}</span>"
            ),
        )

    fig.update_layout(
        template=plotly_template(),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=12, r=12, t=20, b=12),
        height=max(620, 240 + int(abs(max_y) * 94)),
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def pipeline_shell_script(nodes: list[dict[str, Any]], python_command: str) -> str:
    order, _, _ = pipeline_topology(nodes)
    node_map = {node["id"]: node for node in nodes}
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"cd {shlex.quote(str(REPO_ROOT))}",
        "export PYTHONUNBUFFERED=1",
        "",
    ]
    for node_id in order:
        node = node_map[node_id]
        if not node.get("active", True) or not node.get("launchable", True):
            continue
        command = resolve_pipeline_command(node["command"], python_command)
        if not command:
            continue
        lines.append(f'echo "== {node["label"]} =="')
        lines.append(quote_command(command))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def architecture_summary(family: str, doc: dict[str, Any]) -> dict[str, Any]:
    model = doc.get("model", {})
    training = doc.get("training", {})
    stage0 = doc.get("stage0", {})
    active_modules = 4
    if model.get("encoder_type", "mpnn") == "gps":
        active_modules += 1
    if model.get("use_morgan_features"):
        active_modules += 1
    if model.get("use_descriptor_augmentation"):
        active_modules += 1
    if model.get("use_solvent_moe"):
        active_modules += 1
    if family == "TGNN-Solv":
        for flag in ("use_descriptor_priors", "use_group_priors", "use_gc_priors_crystal", "use_oracle_injection"):
            if model.get(flag):
                active_modules += 1
    readout_dim = int(model.get("hidden_dim", 256)) * 3
    pair_dim = int(model.get("pair_dim", 512))
    total_epochs = int(training.get("epochs_phase1", 0) or 0) + int(training.get("epochs_phase2", 0) or 0) + int(training.get("epochs_phase3", 0) or 0)
    encoder_type = str(model.get("encoder_type", "mpnn"))
    encoder_label = (
        f"GPS · {model.get('gps_positional_encoding', 'laplacian')}"
        if encoder_type == "gps"
        else "MPNN"
    )
    return {
        "encoder": encoder_label,
        "hidden_dim": int(model.get("hidden_dim", 256)),
        "layers": int(model.get("n_gnn_layers", 6)),
        "readout_dim": readout_dim,
        "pair_dim": pair_dim,
        "total_epochs": total_epochs,
        "active_modules": active_modules,
        "stage0": "warm start" if bool(stage0.get("enabled")) and family == "TGNN-Solv" else "off",
        "physics": "solver bottleneck" if family == "TGNN-Solv" else "direct ln(x₂) head",
    }


def svg_text_block(x: float, y: float, lines: list[str], *, fill: str, size: int = 14, weight: int = 600, anchor: str = "middle") -> str:
    spans = []
    for index, line in enumerate(lines):
        dy = "0" if index == 0 else "1.22em"
        spans.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{fill}" '
        f'font-size="{size}" font-weight="{weight}" font-family="Inter, ui-sans-serif, system-ui;">'
        + "".join(spans)
        + "</text>"
    )


def architecture_svg(family: str, doc: dict[str, Any]) -> str:
    palette = theme_palette()
    model = doc.get("model", {})
    summary = architecture_summary(family, doc)
    width = 1240
    height = 620 if family == "TGNN-Solv" else 560
    blocks: list[str] = []
    texts: list[str] = []
    arrows: list[str] = []
    accents: list[str] = []

    def box(x: float, y: float, w: float, h: float, title: str, subtitle: str, fill: str, stroke: str, dashed: bool = False) -> None:
        dash = ' stroke-dasharray="7 6"' if dashed else ""
        blocks.append(
            f'<rect x="{x}" y="{y}" rx="24" ry="24" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash} />'
        )
        texts.append(svg_text_block(x + w / 2, y + 32, [title], fill=palette["text"], size=18, weight=800))
        texts.append(svg_text_block(x + w / 2, y + 60, [subtitle], fill=palette["muted"], size=12, weight=500))

    def arrow(x1: float, y1: float, x2: float, y2: float, color: str, dashed: bool = False) -> None:
        dash = ' stroke-dasharray="8 7"' if dashed else ""
        arrows.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="3"{dash} marker-end="url(#arrow)" />'
        )

    if family == "TGNN-Solv":
        box(30, 92, 170, 116, "Solute graph", "real RDKit graph input", palette["card"], palette["border"])
        box(30, 280, 170, 116, "Solvent graph", "real RDKit graph input", palette["card"], palette["border"])
        box(248, 140, 210, 202, "Shared encoder", f"{summary['encoder']} · {summary['layers']} layers · {summary['hidden_dim']}d", "rgba(37,99,235,0.12)", palette["blue"])
        texts.append(svg_text_block(353, 220, ["role adapters", model.get("encoder_role_mode", "shared_residual")], fill=palette["blue"], size=13, weight=700))
        if model.get("encoder_type", "mpnn") == "gps":
            texts.append(
                svg_text_block(
                    353,
                    270,
                    [
                        f"PE: {model.get('gps_positional_encoding', 'laplacian')}",
                        f"{model.get('gps_num_heads', 4)} heads · {model.get('gps_pe_dim', 8)}-d",
                    ],
                    fill=palette["blue"],
                    size=12,
                    weight=700,
                )
            )
        else:
            texts.append(svg_text_block(353, 270, ["local message passing", "no GPS positional branch"], fill=palette["muted"], size=12, weight=600))
        box(502, 72, 200, 104, "Pre-head priors", "descriptor / group / GC bounds", "rgba(124,58,237,0.12)", palette["purple"], dashed=not any(model.get(flag) for flag in ("use_descriptor_priors", "use_group_priors", "use_gc_priors_crystal")))
        box(502, 214, 200, 104, "Interaction", f"{model.get('interaction_mode', 'cross_attn')} × {model.get('n_cross_attn_layers', 3)}", "rgba(5,150,105,0.12)", palette["green"])
        box(502, 356, 200, 104, "Readout + pair", f"Set2Set {model.get('set2set_steps', 3)} · pair {summary['pair_dim']}d", "rgba(148,163,184,0.16)", palette["slate"])
        box(748, 72, 190, 104, "Fusion head", "Tₘ · ΔHfus · optional ΔCp", "rgba(245,158,11,0.14)", palette["orange"])
        box(748, 214, 190, 104, "NRTL head", model.get("nrtl_tau_mode", "ref_invT"), "rgba(245,158,11,0.10)", palette["orange"])
        box(748, 356, 190, 104, "Correction", "bounded solver-space deltas", "rgba(239,68,68,0.12)", palette["red"])
        box(982, 164, 184, 216, "SLE solver", "0 learnable params · implicit diff", "rgba(251,191,36,0.12)", palette["orange"])
        texts.append(svg_text_block(1074, 268, ["ln x₂ = SLE(θ, T)", "final = physics + gate·Δ"], fill=palette["text"], size=14, weight=700))

        arrow(200, 150, 248, 188, palette["border"])
        arrow(200, 338, 248, 290, palette["border"])
        arrow(458, 242, 502, 266, palette["border"])
        arrow(702, 266, 748, 266, palette["border"])
        arrow(938, 266, 982, 266, palette["border"])
        arrow(843, 176, 843, 214, palette["orange"], dashed=True)
        arrow(843, 318, 843, 356, palette["orange"], dashed=True)
        arrow(702, 124, 748, 124, palette["purple"], dashed=True)
        arrow(938, 404, 982, 320, palette["red"])

        if model.get("use_morgan_features"):
            box(228, 464, 210, 74, "Morgan adapter", "pre/post graph augmentation", "rgba(37,99,235,0.08)", palette["blue"], dashed=False)
            arrow(438, 500, 502, 392, palette["blue"], dashed=True)
        else:
            box(228, 464, 210, 74, "Morgan adapter", "disabled", "rgba(148,163,184,0.10)", palette["slate"], dashed=True)

        if model.get("use_descriptor_augmentation"):
            box(20, 486, 190, 74, "Descriptor aug", "normalized RDKit fusion into pair state", "rgba(124,58,237,0.08)", palette["purple"], dashed=False)
            arrow(210, 522, 748, 124, palette["purple"], dashed=True)
        else:
            box(20, 486, 190, 74, "Descriptor aug", "disabled", "rgba(148,163,184,0.10)", palette["slate"], dashed=True)

        if model.get("use_solvent_moe"):
            box(502, 498, 200, 42, "Solvent-type MoE", "routing active", "rgba(16,185,129,0.08)", palette["green"], dashed=False)
        else:
            box(502, 498, 200, 42, "Solvent-type MoE", "disabled", "rgba(148,163,184,0.10)", palette["slate"], dashed=True)

        if bool(doc.get("stage0", {}).get("enabled")):
            box(248, 24, 210, 78, "Stage 0 warm start", "pretrain.py / pretrain_pipeline.py", "rgba(16,185,129,0.08)", palette["green"], dashed=False)
            arrow(353, 102, 353, 140, palette["green"], dashed=True)
        else:
            box(248, 24, 210, 78, "Stage 0 warm start", "off", "rgba(148,163,184,0.10)", palette["slate"], dashed=True)

    else:
        box(38, 122, 180, 116, "Solute graph", "real RDKit graph input", palette["card"], palette["border"])
        box(38, 286, 180, 116, "Solvent graph", "real RDKit graph input", palette["card"], palette["border"])
        box(268, 158, 212, 196, "Shared encoder", f"{summary['encoder']} · {summary['layers']} layers · {summary['hidden_dim']}d", "rgba(37,99,235,0.12)", palette["blue"])
        box(532, 158, 208, 196, "Interaction + readout", f"{model.get('interaction_mode', 'cross_attn')} · Set2Set {model.get('set2set_steps', 3)}", "rgba(16,185,129,0.12)", palette["green"])
        box(792, 80, 160, 102, "Temperature", "thermometer encoder", "rgba(251,191,36,0.12)", palette["orange"])
        box(792, 206, 160, 102, "Descriptor aug", "RDKit descriptors", "rgba(124,58,237,0.12)", palette["purple"], dashed=not bool(model.get("use_descriptor_augmentation")))
        box(792, 332, 160, 102, "Morgan path", "fingerprint adapter", "rgba(37,99,235,0.10)", palette["blue"], dashed=not bool(model.get("use_morgan_features")))
        box(1004, 158, 172, 196, "MLP head", "direct ln(x₂) prediction", "rgba(239,68,68,0.12)", palette["red"])
        texts.append(svg_text_block(1090, 272, ["[g_sol ∥ g_slv ∥", "g⊙g ∥ |Δg| ∥ T]"], fill=palette["text"], size=14, weight=700))

        arrow(218, 176, 268, 204, palette["border"])
        arrow(218, 340, 268, 308, palette["border"])
        arrow(480, 256, 532, 256, palette["border"])
        arrow(740, 256, 1004, 256, palette["border"])
        arrow(952, 130, 1004, 190, palette["orange"], dashed=True)
        arrow(952, 258, 1004, 256, palette["purple"], dashed=True)
        arrow(952, 382, 1004, 322, palette["blue"], dashed=True)

    blocks_html = "".join(blocks)
    arrows_html = "".join(arrows)
    texts_html = "".join(texts)
    return f"""
    <div class="lab-svg-panel">
      <svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{escape(family)} architecture diagram">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="{palette['border']}"></path>
          </marker>
        </defs>
        <rect x="0" y="0" width="{width}" height="{height}" rx="28" fill="{palette['surface_alt']}" />
        {blocks_html}
        {arrows_html}
        {texts_html}
      </svg>
    </div>
    """


def architecture_input_frame(solute: str, solvent: str) -> pd.DataFrame:
    rows = []
    for role, smiles in [("solute", solute), ("solvent", solvent)]:
        stats = model_cardinality_stats(smiles)
        if stats is None:
            rows.append({"role": role, "smiles": smiles, "atoms": "—", "bonds": "—", "rings": "—", "heteroatoms": "—"})
            continue
        rows.append({"role": role, "smiles": smiles, **stats})
    return pd.DataFrame(rows)


def generated_config_path(family: str, slug: str) -> Path:
    suffix = "directgnn" if family == "DirectGNN" else "tgnn"
    return CONFIG_DIR / "gui_generated" / f"{slug}_{suffix}.yaml"


def build_architecture_training_command(
    family: str,
    config_path: str,
    python_command: str,
    *,
    doc: dict[str, Any],
    train_data: str,
    val_data: str,
    test_data: str,
    checkpoint: str,
    device: str,
) -> list[str]:
    stage0 = doc.get("stage0", {})
    if family == "DirectGNN":
        return build_python_command(
            "scripts/training/train_directgnn.py",
            "--config",
            config_path,
            "--train-data",
            train_data,
            "--val-data",
            val_data,
            "--test-data",
            test_data,
            "--checkpoint",
            checkpoint,
            "--device",
            device,
            python_command_text=python_command,
        )
    command = build_python_command(
        "scripts/training/train.py",
        "--config",
        config_path,
        "--train-data",
        train_data,
        "--val-data",
        val_data,
        "--test-data",
        test_data,
        "--checkpoint",
        checkpoint,
        "--device",
        device,
        python_command_text=python_command,
    )
    if bool(stage0.get("enabled")):
        mode = str(stage0.get("mode", "fresh"))
        if mode == "checkpoint" and str(stage0.get("pretrain_checkpoint", "")).strip():
            command.extend(
                [
                    "--pretrain-checkpoint",
                    str(stage0.get("pretrain_checkpoint", "")).strip(),
                ]
            )
        else:
            command.append("--pretrain")
            command.extend(["--pretrain-data", str(stage0.get("pretrain_data", "zinc250k"))])
            command.extend(["--pretrain-epochs", str(int(stage0.get("pretrain_epochs", 30) or 30))])
            command.extend(
                [
                    "--pretrain-batch-size",
                    str(int(stage0.get("pretrain_batch_size", 128) or 128)),
                ]
            )
            command.extend(["--pretrain-lr", str(float(stage0.get("pretrain_lr", 3.0e-4) or 3.0e-4))])
            if stage0.get("pretrain_max_molecules") not in {None, "", 0}:
                command.extend(["--pretrain-max-molecules", str(int(stage0.get("pretrain_max_molecules")))])
        if str(stage0.get("pretrain_output", "")).strip():
            command.extend(["--pretrain-output", str(stage0.get("pretrain_output", "")).strip()])
        if bool(stage0.get("run_descriptor_probe")):
            command.append("--run-descriptor-probe")
            if str(stage0.get("descriptor_probe_output_dir", "")).strip():
                command.extend(
                    [
                        "--descriptor-probe-output-dir",
                        str(stage0.get("descriptor_probe_output_dir", "")).strip(),
                    ]
                )
            command.extend(["--descriptor-probe-device", str(stage0.get("descriptor_probe_device", "cpu"))])
    return command


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def plotly_template() -> str:
    return "plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"


def style_plot(fig: go.Figure) -> go.Figure:
    palette = theme_palette()
    margin = fig.layout.margin.to_plotly_json() if fig.layout.margin else {}
    fig.update_layout(
        template=plotly_template(),
        paper_bgcolor=hex_to_rgba(palette["surface_alt"], 0.96),
        plot_bgcolor=hex_to_rgba(palette["surface"], 0.98),
        colorway=[
            palette["blue"],
            palette["green"],
            palette["orange"],
            palette["purple"],
            palette["red"],
            palette["slate"],
        ],
        font={"color": palette["text"]},
        title={"font": {"color": palette["text"]}},
        legend={
            **(fig.layout.legend.to_plotly_json() if fig.layout.legend else {}),
            "font": {"color": palette["text"]},
            "title": {"font": {"color": palette["text"]}},
        },
        polar={
            "bgcolor": "rgba(0,0,0,0)",
            "angularaxis": {
                "gridcolor": hex_to_rgba(palette["border"], 0.26),
                "linecolor": hex_to_rgba(palette["border"], 0.36),
                "tickfont": {"color": palette["muted"]},
            },
            "radialaxis": {
                "gridcolor": hex_to_rgba(palette["border"], 0.26),
                "linecolor": hex_to_rgba(palette["border"], 0.36),
                "tickfont": {"color": palette["muted"]},
            },
        },
        hoverlabel={
            "bgcolor": palette["surface_alt"],
            "bordercolor": palette["border"],
            "font": {"color": palette["text"]},
        },
        margin={
            "l": margin.get("l", 20),
            "r": margin.get("r", 20),
            "t": margin.get("t", 52),
            "b": margin.get("b", 20),
        },
    )
    fig.update_xaxes(
        gridcolor=hex_to_rgba(palette["border"], 0.28),
        linecolor=hex_to_rgba(palette["border"], 0.5),
        tickfont={"color": palette["muted"]},
        title_font={"color": palette["text"]},
        zerolinecolor=hex_to_rgba(palette["border"], 0.32),
    )
    fig.update_yaxes(
        gridcolor=hex_to_rgba(palette["border"], 0.28),
        linecolor=hex_to_rgba(palette["border"], 0.5),
        tickfont={"color": palette["muted"]},
        title_font={"color": palette["text"]},
        zerolinecolor=hex_to_rgba(palette["border"], 0.32),
    )
    return fig


def quote_command(command: list[str]) -> str:
    return shlex.join(command)


def extract_last_json_block(stdout: str) -> Any:
    in_string = False
    escape = False
    depth = 0
    block_start = None
    last_object = None

    for index, char in enumerate(stdout):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            if depth == 0:
                block_start = index
            depth += 1
            continue

        if char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and block_start is not None:
                candidate = stdout[block_start:index + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                last_object = parsed

    if last_object is None:
        raise ValueError("Could not find a JSON object in subprocess output.")
    return last_object


def parse_extra_args(text: str) -> list[str]:
    return shlex.split(text.strip()) if text.strip() else []


def suggested_python_command() -> str:
    candidates = [
        REPO_ROOT / ".venv" / "bin" / "python",
        Path.home() / "anaconda3" / "envs" / "tgnn-solv" / "bin" / "python",
        Path.home() / "miniforge3" / "envs" / "tgnn-solv" / "bin" / "python",
        Path.home() / "mambaforge" / "envs" / "tgnn-solv" / "bin" / "python",
        Path(DEFAULT_PYTHON_COMMAND),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return DEFAULT_PYTHON_COMMAND


def python_command_tokens(command_text: str | None = None) -> list[str]:
    raw = (command_text or DEFAULT_PYTHON_COMMAND).strip()
    tokens = shlex.split(raw)
    return tokens or [DEFAULT_PYTHON_COMMAND]


def build_python_command(
    script_path: str,
    *args: str,
    python_command_text: str | None = None,
) -> list[str]:
    return [*python_command_tokens(python_command_text), script_path, *args]


def filesystem_summary() -> dict[str, int]:
    return {
        "processed_splits": sum(1 for _ in PROCESSED_DIR.glob("*.csv")) if PROCESSED_DIR.exists() else 0,
        "checkpoints": len(available_checkpoints()),
        "artifacts": len(available_artifacts()),
        "images": len(available_images()),
        "jobs": len(load_jobs()),
    }


def relative_label(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def compact_path_label(path_value: str | Path, keep_segments: int = 3) -> str:
    rel = relative_label(Path(str(path_value)))
    parts = Path(rel).parts
    if len(parts) <= keep_segments:
        return rel
    return "…/" + "/".join(parts[-keep_segments:])


def list_files(root: Path, patterns: tuple[str, ...], limit: int = 600) -> list[Path]:
    results: list[Path] = []
    for pattern in patterns:
        results.extend(root.rglob(pattern))
    unique = sorted({path.resolve() for path in results if path.is_file()})
    return unique[:limit]


def available_configs() -> list[Path]:
    return sorted(CONFIG_DIR.glob("*.yaml"))


def available_checkpoints() -> list[Path]:
    return list_files(CHECKPOINTS_DIR, ("*.pt", "*.pth", "*.ckpt"), limit=300)


def checkpoint_family_from_payload(payload: dict[str, Any]) -> str:
    if payload.get("error"):
        return "unsupported"
    if not payload.get("has_config"):
        return "unsupported"
    model_class = str(payload.get("model_class", "") or "").lower()
    model_type = str(payload.get("model_type", "") or "").lower()
    top_keys = set(str(key) for key in payload.get("top_level_keys", []))
    if "directgnn" in model_class or "direct" in model_type:
        if {"model_state", "model_state_dict"} & top_keys:
            return "direct_gnn"
        return "unsupported"
    if {"model_state", "model_state_dict"} & top_keys:
        return "tgnn_solv"
    return "unsupported"


def inference_workbench_reason(payload: dict[str, Any]) -> str | None:
    if payload.get("error"):
        return str(payload["error"])
    if not payload.get("has_config"):
        return "missing `config` payload"
    family = checkpoint_family_from_payload(payload)
    if family in {"tgnn_solv", "direct_gnn"}:
        return None
    top_keys = set(str(key) for key in payload.get("top_level_keys", []))
    if not ({"model_state", "model_state_dict"} & top_keys):
        return "missing compatible model weights"
    return "unsupported checkpoint family for the inference workbench"


def tgnn_inference_reason(payload: dict[str, Any]) -> str | None:
    family = checkpoint_family_from_payload(payload)
    if family in {"tgnn_solv", "direct_gnn"}:
        return None
    if payload.get("error"):
        return str(payload["error"])
    if not payload.get("has_config"):
        return "missing `config` payload"
    return None


def workbench_compatible_checkpoints(
    python_command: str,
    checkpoints: list[Path],
) -> tuple[list[Path], list[tuple[Path, str]]]:
    supported: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    for path in checkpoints:
        try:
            payload = inspect_checkpoint(
                python_command,
                str(path),
                path.stat().st_mtime,
            )
        except Exception as exc:
            rejected.append((path, f"{type(exc).__name__}: {exc}"))
            continue
        reason = inference_workbench_reason(payload)
        if reason is None:
            supported.append(path)
        else:
            rejected.append((path, reason))
    return supported, rejected


def tgnn_inference_checkpoints(
    python_command: str,
    checkpoints: list[Path],
) -> tuple[list[Path], list[tuple[Path, str]]]:
    supported: list[Path] = []
    rejected: list[tuple[Path, str]] = []
    for path in checkpoints:
        try:
            payload = inspect_checkpoint(
                python_command,
                str(path),
                path.stat().st_mtime,
            )
        except Exception as exc:
            rejected.append((path, f"{type(exc).__name__}: {exc}"))
            continue
        reason = tgnn_inference_reason(payload)
        if reason is None:
            supported.append(path)
        else:
            rejected.append((path, reason))
    return supported, rejected


def available_images() -> list[Path]:
    roots = [CHECKPOINTS_DIR, FIGURES_DIR, RESULTS_DIR]
    found: list[Path] = []
    for root in roots:
        if root.exists():
            found.extend(list_files(root, ("*.png", "*.jpg", "*.jpeg", "*.svg"), limit=400))
    return sorted({path.resolve() for path in found})


def available_artifacts() -> list[Path]:
    roots = [RESULTS_DIR, CHECKPOINTS_DIR, FIGURES_DIR, TABLES_DIR]
    found: list[Path] = []
    for root in roots:
        if root.exists():
            found.extend(list_files(root, ("*.json", "*.csv", "*.png", "*.jpg", "*.jpeg", "*.svg"), limit=800))
    return sorted({path.resolve() for path in found})


def artifact_kind(path: Path) -> str:
    parent = path.parent.name
    suffix = path.suffix.lower()
    if suffix in {".pt", ".pth", ".ckpt"}:
        return "checkpoint"
    if suffix == ".json":
        if parent == "inference_history":
            return "inference_history"
        if parent == "uncertainty_history":
            return "uncertainty_history"
        if parent == "calibration_history":
            return "calibration_history"
        return "json"
    if suffix == ".csv":
        return "csv"
    if suffix in {".png", ".jpg", ".jpeg", ".svg"}:
        return "image"
    return "other"


def artifact_model_guess(path: Path) -> str:
    kind = artifact_kind(path)
    if kind in {"inference_history", "uncertainty_history", "calibration_history"}:
        try:
            payload = cached_json(str(path))
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            checkpoints = []
            if payload.get("checkpoint"):
                checkpoints.append(str(payload.get("checkpoint")))
            checkpoints.extend(str(item) for item in payload.get("checkpoints", []) if item)
            joined = " ".join(Path(item).name.lower() for item in checkpoints)
            if "direct" in joined:
                return "direct_gnn"
            if checkpoints:
                return "tgnn_solv"
            if kind == "calibration_history":
                return "uncertainty_eval"
    label = relative_label(path).lower()
    if "direct" in label:
        return "direct_gnn"
    if "tgnn" in label:
        return "tgnn_solv"
    if "rf" in label:
        return "rf_baseline"
    if "fastsolv" in label:
        return "fastsolv"
    if "solprop" in label:
        return "solprop"
    if "custom" in label:
        return "custom"
    if "optuna" in label:
        return "optuna"
    if "seed" in label:
        return "seed_sweep"
    return "generic"


@st.cache_data(show_spinner=False)
def artifact_registry_frame() -> pd.DataFrame:
    paths = sorted({*available_artifacts(), *available_checkpoints()})
    rows: list[dict[str, Any]] = []
    for path in paths:
        try:
            stat = path.stat()
        except Exception:
            continue
        rows.append(
            {
                "path": relative_label(path),
                "kind": artifact_kind(path),
                "model_guess": artifact_model_guess(path),
                "name": path.name,
                "parent": relative_label(path.parent),
                "suffix": path.suffix.lower(),
                "size_mb": round(stat.st_size / (1024 * 1024), 3),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                "abs_path": str(path),
            }
        )
    return pd.DataFrame(rows).sort_values(["modified_at", "path"], ascending=[False, True]) if rows else pd.DataFrame()


def related_artifact_frame(registry_df: pd.DataFrame, selected_path: Path, *, limit: int = 12) -> pd.DataFrame:
    if registry_df.empty:
        return pd.DataFrame()
    stem = selected_path.stem.lower()
    parent = relative_label(selected_path.parent)
    model = artifact_model_guess(selected_path)
    related = registry_df[
        (registry_df["parent"] == parent)
        | (registry_df["model_guess"] == model)
        | (registry_df["name"].astype(str).str.lower().str.contains(stem[: max(3, min(8, len(stem)))], regex=False))
    ].copy()
    related = related[related["path"] != relative_label(selected_path)]
    return related.head(limit)


def flatten_numeric_payload(data: Any, prefix: str = "") -> dict[str, float]:
    items: dict[str, float] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else str(key)
            items.update(flatten_numeric_payload(value, full_key))
    elif isinstance(data, list):
        return items
    elif isinstance(data, (int, float)) and not isinstance(data, bool):
        items[prefix] = float(data)
    return items


def compare_numeric_frames(left_payload: dict[str, float], right_payload: dict[str, float]) -> pd.DataFrame:
    keys = sorted(set(left_payload) | set(right_payload))
    rows = []
    for key in keys:
        left = left_payload.get(key)
        right = right_payload.get(key)
        if left is None and right is None:
            continue
        delta = None if left is None or right is None else float(right) - float(left)
        rows.append({"metric": key, "left": left, "right": right, "delta": delta})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def nearest_config_for_doc(config_doc: dict[str, Any]) -> tuple[str | None, int]:
    target = normalize_config_document(config_doc if isinstance(config_doc, dict) else {})
    best_path: str | None = None
    best_diff = 10**9
    for path in available_configs():
        try:
            base = normalize_config_document(cached_yaml(str(path)))
        except Exception:
            continue
        diff_count = len(config_diff_frame(base, target))
        if diff_count < best_diff:
            best_diff = diff_count
            best_path = str(path)
    return best_path, int(best_diff if best_diff != 10**9 else 0)


def _job_path_tokens(job: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for item in job.get("command", []):
        if not isinstance(item, str):
            continue
        tokens.append(item)
    for item in job.get("expected_outputs", []):
        if isinstance(item, str):
            tokens.append(item)
    return tokens


def job_references_artifact(job: dict[str, Any], artifact_path: Path) -> bool:
    artifact_label = relative_label(artifact_path)
    stem = artifact_path.stem.lower()
    parent = relative_label(artifact_path.parent).lower()
    for token in _job_path_tokens(job):
        token_norm = str(token).lower()
        if artifact_label.lower() in token_norm:
            return True
        if parent and parent in token_norm:
            return True
        if stem and stem in token_norm:
            return True
    return False


def lineage_graph_figure(nodes: list[dict[str, Any]], edges: list[tuple[str, str]]) -> go.Figure:
    palette = theme_palette()
    color_map = {
        "config": palette["purple"],
        "job": palette["blue"],
        "checkpoint": palette["green"],
        "artifact": palette["orange"],
        "focal": palette["red"],
    }
    fig = go.Figure()
    for source, target in edges:
        src = next((node for node in nodes if node["id"] == source), None)
        dst = next((node for node in nodes if node["id"] == target), None)
        if src is None or dst is None:
            continue
        fig.add_annotation(
            x=dst["x"],
            y=dst["y"],
            ax=src["x"],
            ay=src["y"],
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1,
            arrowwidth=1.8,
            arrowcolor=palette["border"],
            opacity=0.9,
        )
    for node in nodes:
        fill = color_map.get(node["kind"], palette["slate"])
        node_text = contrast_text_color(fill)
        fig.add_annotation(
            x=node["x"],
            y=node["y"],
            showarrow=False,
            align="left",
            borderpad=12,
            borderwidth=2,
            bordercolor=fill,
            bgcolor=fill,
            font={"color": node_text, "size": 13},
            text=f"<b>{escape(node['label'])}</b><br><span style='font-size:11px'>{escape(node.get('subtitle', ''))}</span>",
        )
    fig.update_layout(
        template=plotly_template(),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=max(460, 180 + 88 * max(1, len(nodes))),
        margin=dict(l=24, r=24, t=24, b=24),
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def ensure_layout() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / "logs").mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / "states").mkdir(parents=True, exist_ok=True)
    INFERENCE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    UNCERTAINTY_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    CALIBRATION_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    PIPELINE_PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    PLANNER_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def default_planner_state() -> dict[str, Any]:
    tasks = [
        {
            "id": "exp-pretrain-ablation",
            "title": "Pretraining ablation",
            "status": "Backlog",
            "priority": "P1",
            "owner": "research",
            "start": datetime.now().date().isoformat(),
            "end": (datetime.now().date()).isoformat(),
            "estimate_hours": 6,
            "notes": "Run the pretraining-enabled architecture against the tuned TGNN baseline.",
            "command": "python scripts/experiments/run_medium_budget_comparison.py --output-dir results/medium_budget_pretrain",
        },
        {
            "id": "exp-solver-diagnostics",
            "title": "Solver diagnostics refresh",
            "status": "Ready",
            "priority": "P1",
            "owner": "analysis",
            "start": datetime.now().date().isoformat(),
            "end": datetime.now().date().isoformat(),
            "estimate_hours": 4,
            "notes": "Re-export solver-facing intermediates and article diagnostics.",
            "command": "python scripts/evaluation/evaluate_complete.py --checkpoint checkpoints/tgnn_solv_trained.pt",
        },
        {
            "id": "exp-directgnn-desc",
            "title": "DirectGNN + descriptors benchmark",
            "status": "Running",
            "priority": "P2",
            "owner": "baseline",
            "start": datetime.now().date().isoformat(),
            "end": datetime.now().date().isoformat(),
            "estimate_hours": 8,
            "notes": "Matched descriptor-augmented DirectGNN run for architecture comparison.",
            "command": "python scripts/training/train_directgnn.py --config configs/paper_config_directgnn_descriptors.yaml",
        },
    ]
    board = {column: [] for column in ["Backlog", "Ready", "Running", "Blocked", "Done"]}
    for task in tasks:
        board.setdefault(task["status"], []).append(task["id"])
    return {"board": board, "tasks": tasks, "saved_at": utc_now()}


def load_planner_state() -> dict[str, Any]:
    ensure_layout()
    if not PLANNER_STATE_PATH.exists():
        state = default_planner_state()
        write_json(PLANNER_STATE_PATH, state)
        return state
    try:
        payload = read_json(PLANNER_STATE_PATH)
    except Exception:
        payload = default_planner_state()
    if not isinstance(payload, dict):
        payload = default_planner_state()
    payload.setdefault("board", default_planner_state()["board"])
    payload.setdefault("tasks", default_planner_state()["tasks"])
    return payload


def save_planner_state(payload: dict[str, Any]) -> None:
    payload["saved_at"] = utc_now()
    write_json(PLANNER_STATE_PATH, payload)


def planner_task_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(task["id"]): task for task in payload.get("tasks", []) if isinstance(task, dict) and task.get("id")}


def planner_board_labels(payload: dict[str, Any]) -> list[dict[str, Any]]:
    task_map = planner_task_map(payload)
    board = payload.get("board", {})
    containers: list[dict[str, Any]] = []
    for column in ["Backlog", "Ready", "Running", "Blocked", "Done"]:
        labels: list[str] = []
        for task_id in board.get(column, []):
            task = task_map.get(str(task_id))
            if not task:
                continue
            labels.append(f"{task['id']} | {task.get('priority', 'P2')} | {task['title']}")
        containers.append({"header": column, "items": labels})
    return containers


def sync_planner_board_from_labels(payload: dict[str, Any], board_labels: list[dict[str, Any]]) -> dict[str, Any]:
    task_map = planner_task_map(payload)
    seen: set[str] = set()
    board: dict[str, list[str]] = {}
    for container in board_labels:
        column = str(container.get("header", "Backlog"))
        labels = container.get("items", [])
        board[column] = []
        for label in labels:
            task_id = str(label).split(" | ", 1)[0]
            if task_id not in task_map:
                continue
            seen.add(task_id)
            task_map[task_id]["status"] = column
            board[column].append(task_id)
    for task_id, task in task_map.items():
        if task_id not in seen:
            board.setdefault(task.get("status", "Backlog"), []).append(task_id)
    payload["board"] = board
    payload["tasks"] = list(task_map.values())
    return payload


def planner_timeline_frame(payload: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for task in payload.get("tasks", []):
        start = str(task.get("start") or datetime.now().date().isoformat())
        end = str(task.get("end") or start)
        rows.append(
            {
                "Task": task.get("title", task.get("id")),
                "Status": task.get("status", "Backlog"),
                "Owner": task.get("owner", "research"),
                "Priority": task.get("priority", "P2"),
                "Start": start,
                "Finish": end,
                "Hours": float(task.get("estimate_hours", 0.0) or 0.0),
                "id": task.get("id"),
            }
        )
    return pd.DataFrame(rows)


def planner_sortable_style() -> str:
    palette = theme_palette()
    dark = st.get_option("theme.base") == "dark"
    container_fill = "rgba(15, 23, 42, 0.94)" if dark else "rgba(241, 245, 249, 0.92)"
    body_fill = "rgba(30, 41, 59, 0.74)" if dark else "rgba(226, 232, 240, 0.68)"
    item_fill = "rgba(15, 23, 42, 0.98)" if dark else "rgba(255, 255, 255, 0.98)"
    item_text = "#F8FAFC" if dark else "#0F172A"
    header_text = "#F8FAFC" if dark else "#0F172A"
    border = "rgba(96, 165, 250, 0.28)" if dark else "rgba(37, 99, 235, 0.12)"
    shadow = "0 20px 42px rgba(2, 6, 23, 0.36)" if dark else "0 12px 28px rgba(15, 23, 42, 0.06)"
    accent = palette["blue"]
    return f"""
    .sortable-component {{
      display: flex;
      gap: 16px;
      overflow-x: auto;
      padding: 12px 0 14px;
      align-items: flex-start;
    }}
    .sortable-container {{
      min-width: 270px;
      background: {container_fill};
      border: 1px solid {border};
      border-radius: 20px;
      min-height: 360px;
      padding: 0;
      box-shadow: {shadow};
      overflow: hidden;
    }}
    .sortable-container-header,
    .sortable-container-header * {{
      font-weight: 900;
      color: {header_text} !important;
      background: {container_fill} !important;
    }}
    .sortable-container-header {{
      padding: 14px 16px 10px;
      margin: 0;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      font-size: 0.84rem;
      line-height: 1.2;
      border-bottom: 1px solid {border};
      min-height: 48px;
      display: flex;
      align-items: center;
    }}
    .sortable-container-body {{
      background: {body_fill} !important;
      border-radius: 0 0 20px 20px;
      margin: 0;
      min-height: 308px;
      padding: 8px 8px 10px;
    }}
    .sortable-item {{
      background: {item_fill};
      color: {item_text} !important;
      border: 1px solid {border};
      border-left: 4px solid {accent};
      border-radius: 16px;
      padding: 12px 13px 12px;
      margin: 8px;
      box-shadow: {shadow};
      font-weight: 700;
      line-height: 1.4;
      white-space: normal;
      display: block;
      min-height: 56px;
    }}
    .sortable-item:hover,
    .sortable-item:focus {{
      color: {item_text} !important;
      transform: translateY(-1px);
      box-shadow: 0 22px 44px rgba(2, 6, 23, 0.22);
    }}
    .sortable-item * {{
      color: {item_text} !important;
    }}
    """


def task_priority_color(priority: str) -> str:
    palette = theme_palette()
    mapping = {
        "P1": palette["red"],
        "P2": palette["orange"],
        "P3": palette["green"],
    }
    return mapping.get(str(priority), palette["slate"])


def auto_layout_pipeline_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order, levels, _ = pipeline_topology(nodes)
    ordered_ids = order + [node["id"] for node in nodes if node["id"] not in order]
    rows_by_level: dict[int, int] = defaultdict(int)
    by_id = {node["id"]: node for node in nodes}
    for node_id in ordered_ids:
        level = levels.get(node_id, 0)
        row = rows_by_level[level]
        rows_by_level[level] += 1
        by_id[node_id]["ui_pos"] = {"x": 70 + 300 * level, "y": 50 + 160 * row}
    return list(by_id.values())


def discover_optuna_artifacts() -> tuple[list[Path], list[Path]]:
    trial_paths: list[Path] = []
    best_paths: list[Path] = []
    if OPTUNA_DIR.exists():
        trial_paths.extend(sorted(OPTUNA_DIR.rglob("*_trials.csv")))
        best_paths.extend(sorted(OPTUNA_DIR.rglob("*_best.json")))
    return trial_paths, best_paths


def optuna_best_frame(best_paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in best_paths:
        try:
            payload = read_json(path)
        except Exception:
            continue
        params = payload.get("best_params", {}) if isinstance(payload, dict) else {}
        rows.append(
            {
                "model": payload.get("model", path.stem.replace("_best", "")),
                "best_value": payload.get("best_value"),
                "n_params": len(params) if isinstance(params, dict) else 0,
                "path": relative_label(path),
                "top_params": ", ".join(f"{k}={v}" for k, v in list((params or {}).items())[:4]),
            }
        )
    return pd.DataFrame(rows).sort_values("best_value", ascending=True, na_position="last") if rows else pd.DataFrame()


def optuna_parameter_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in df.columns if str(column).startswith("params_")]


def available_doc_pages() -> list[Path]:
    if not DOCS_DIR.exists():
        return []
    return sorted(path for path in DOCS_DIR.rglob("*.md") if path.is_file())


@st.cache_data(show_spinner=False)
def cached_text(path_str: str) -> str:
    return Path(path_str).read_text(encoding="utf-8")


def module_flag_state(family: str, doc: dict[str, Any], node_id: str, flag: str | None) -> bool:
    model = doc.get("model", {})
    stage0 = doc.get("stage0", {})
    if family == "TGNN-Solv" and node_id == "pre_head_priors":
        return any(bool(model.get(key)) for key in ("use_descriptor_priors", "use_group_priors", "use_gc_priors_crystal"))
    if node_id == "gps_pe":
        return str(model.get("encoder_type", "mpnn")) == "gps"
    if family == "TGNN-Solv" and node_id == "stage0_warmstart":
        return bool(stage0.get("enabled"))
    if flag is None:
        return True
    return bool(model.get(flag))


def flow_node_style(track: str, active: bool, *, selected: bool = False) -> dict[str, Any]:
    palette = theme_palette()
    track_colors = {
        "input": palette["slate"],
        "shared": palette["blue"],
        "tgnn": palette["orange"],
        "direct": palette["purple"],
    }
    fill = track_colors.get(track, palette["blue"]) if active else palette["muted"]
    text_color = contrast_text_color(fill)
    return {
        "background": fill,
        "color": text_color,
        "border": f"3px solid {palette['text'] if selected else hex_to_rgba(fill, 0.72)}",
        "borderRadius": "18px",
        "padding": "14px 16px",
        "width": 190,
        "fontSize": "14px",
        "fontWeight": 700,
        "boxShadow": (
            "0 18px 34px rgba(2, 6, 23, 0.26)"
            if st.get_option("theme.base") == "dark"
            else "0 14px 30px rgba(15, 23, 42, 0.14)"
        ),
    }


def pipeline_flow_signature(nodes: list[dict[str, Any]], selected_id: str | None) -> str:
    payload = [
        {
            "id": node["id"],
            "label": node.get("label"),
            "category": node.get("category"),
            "active": bool(node.get("active", True)),
            "depends_on": sorted(node.get("depends_on", [])),
            "ui_pos": node.get("ui_pos"),
        }
        for node in nodes
    ]
    return json.dumps({"nodes": payload, "selected_id": selected_id or ""}, sort_keys=True, ensure_ascii=True)


def flow_state_signature(state: StreamlitFlowState | None) -> str:
    if state is None:
        return ""
    payload = {
        "nodes": [
            {
                "id": node.id,
                "x": float(node.position["x"]),
                "y": float(node.position["y"]),
                "content": node.data.get("content"),
            }
            for node in state.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
            }
            for edge in state.edges
        ],
        "selected_id": state.selected_id or "",
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def pipeline_flow_state(nodes: list[dict[str, Any]], selected_id: str | None = None) -> StreamlitFlowState | None:
    if StreamlitFlowState is None or StreamlitFlowNode is None or StreamlitFlowEdge is None:
        return None
    order, levels, _ = pipeline_topology(nodes)
    ordered_ids = order + [node["id"] for node in nodes if node["id"] not in order]
    rows_by_level: dict[int, int] = defaultdict(int)
    flow_nodes: list[StreamlitFlowNode] = []
    flow_edges: list[StreamlitFlowEdge] = []
    statuses = pipeline_status_map(nodes)
    node_map = {node["id"]: node for node in nodes}
    for node_id in ordered_ids:
        node = node_map[node_id]
        level = levels.get(node_id, 0)
        row = rows_by_level[level]
        rows_by_level[level] += 1
        pos = node.get("ui_pos") or {"x": 60 + 280 * level, "y": 50 + 150 * row}
        flow_nodes.append(
            StreamlitFlowNode(
                id=node_id,
                pos=(float(pos["x"]), float(pos["y"])),
                data={"content": f"{node['label']}\n{node['category'].upper()} · {statuses.get(node_id, 'planned')}"},
                selectable=True,
                connectable=True,
                draggable=True,
                deletable=True,
                selected=node_id == selected_id,
                style=flow_node_style(node.get("category", "shared"), node.get("active", True), selected=node_id == selected_id),
            )
        )
    for node in nodes:
        for dep in node.get("depends_on", []):
            flow_edges.append(
                StreamlitFlowEdge(
                    id=f"{dep}->{node['id']}",
                    source=dep,
                    target=node["id"],
                    animated=statuses.get(node["id"]) == "ready",
                    deletable=True,
                    focusable=True,
                    edge_type="smoothstep",
                    style={"strokeWidth": 3},
                )
            )
    return StreamlitFlowState(nodes=flow_nodes, edges=flow_edges, selected_id=selected_id)


def sync_pipeline_from_flow(nodes: list[dict[str, Any]], flow_state: StreamlitFlowState) -> list[dict[str, Any]]:
    valid_ids = {node["id"] for node in nodes}
    edge_targets: dict[str, list[str]] = defaultdict(list)
    for edge in flow_state.edges:
        if edge.source != edge.target and edge.source in valid_ids and edge.target in valid_ids:
            edge_targets[str(edge.target)].append(str(edge.source))
    for node in nodes:
        flow_node = next((item for item in flow_state.nodes if item.id == node["id"]), None)
        if flow_node is not None:
            node["ui_pos"] = {"x": float(flow_node.position["x"]), "y": float(flow_node.position["y"])}
        node["depends_on"] = sorted(set(edge_targets.get(node["id"], [])))
    return nodes


def pipeline_canvas_state(nodes: list[dict[str, Any]], selected_id: str | None) -> StreamlitFlowState | None:
    state_key = "pipeline_studio_flow_state"
    signature_key = "pipeline_studio_flow_signature"
    signature = pipeline_flow_signature(nodes, selected_id)
    cached_state = st.session_state.get(state_key)
    if cached_state is None or st.session_state.get(signature_key) != signature:
        cached_state = pipeline_flow_state(nodes, selected_id)
        st.session_state[state_key] = cached_state
        st.session_state[signature_key] = signature
    return cached_state


def architecture_visual_state(family: str, doc: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    state_key = f"architect_visual_{family}"
    saved = st.session_state.get(state_key, {})
    saved_nodes = {item["id"]: item for item in saved.get("nodes", []) if isinstance(item, dict) and item.get("id")}
    saved_edges = saved.get("edges", [])
    selected_id = saved.get("selected_id")
    base_nodes = copy.deepcopy(ARCHITECTURE_VISUAL_NODES[family])
    for node in base_nodes:
        if node["id"] in saved_nodes:
            node["x"] = float(saved_nodes[node["id"]].get("x", node["x"]))
            node["y"] = float(saved_nodes[node["id"]].get("y", node["y"]))
            node["note"] = str(saved_nodes[node["id"]].get("note", node["note"]))
        node["active"] = module_flag_state(family, doc, node["id"], node.get("flag"))
    base_edge_ids = {edge_id for edge_id, _, _ in ARCHITECTURE_VISUAL_EDGES[family]}
    edges = [{"id": edge_id, "source": source, "target": target} for edge_id, source, target in ARCHITECTURE_VISUAL_EDGES[family]]
    for edge in saved_edges:
        if isinstance(edge, dict) and edge.get("id") not in base_edge_ids:
            edges.append(edge)
    if not selected_id and base_nodes:
        selected_id = base_nodes[0]["id"]
    st.session_state[state_key] = {"nodes": base_nodes, "edges": edges, "selected_id": selected_id}
    return base_nodes, edges


def architecture_visual_signature(family: str, doc: dict[str, Any]) -> str:
    nodes, edges = architecture_visual_state(family, doc)
    model = doc.get("model", {})
    flags = {
        key: model.get(key)
        for key in sorted(model.keys())
        if key.startswith("use_")
        or key
        in {
            "hidden_dim",
            "n_gnn_layers",
            "pair_dim",
            "interaction_mode",
            "n_cross_attn_layers",
            "n_attn_heads",
            "set2set_steps",
            "encoder_type",
            "gps_num_heads",
            "gps_use_edge_attr",
            "gps_positional_encoding",
            "gps_pe_dim",
        }
    }
    payload = {
        "family": family,
        "nodes": [
            {
                "id": node["id"],
                "x": node["x"],
                "y": node["y"],
                "active": bool(node.get("active", True)),
                "note": node.get("note", ""),
            }
            for node in nodes
        ],
        "edges": edges,
        "flags": flags,
        "stage0": doc.get("stage0", {}),
        "selected_id": st.session_state.get(f"architect_visual_{family}", {}).get("selected_id"),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def architecture_flow_state(family: str, doc: dict[str, Any]) -> StreamlitFlowState | None:
    if StreamlitFlowState is None or StreamlitFlowNode is None or StreamlitFlowEdge is None:
        return None
    nodes, edges = architecture_visual_state(family, doc)
    selected_id = st.session_state.get(f"architect_visual_{family}", {}).get("selected_id")
    flow_nodes: list[StreamlitFlowNode] = []
    for node in nodes:
        is_selected = node["id"] == selected_id
        flow_nodes.append(
            StreamlitFlowNode(
                id=node["id"],
                pos=(float(node["x"]), float(node["y"])),
                data={"content": f"{node['label']}\n{node['track']}"},
                selectable=True,
                connectable=True,
                draggable=True,
                deletable=node.get("kind") != "core",
                selected=is_selected,
                style=flow_node_style(node.get("track", "shared"), bool(node.get("active", True)), selected=is_selected),
            )
        )
    flow_edges = [
        StreamlitFlowEdge(
            id=str(edge["id"]),
            source=str(edge["source"]),
            target=str(edge["target"]),
            animated=False,
            deletable=True,
            focusable=True,
            edge_type="smoothstep",
            style={"strokeWidth": 3},
        )
        for edge in edges
    ]
    return StreamlitFlowState(nodes=flow_nodes, edges=flow_edges, selected_id=selected_id)


def sync_architecture_from_flow(family: str, flow_state: StreamlitFlowState) -> None:
    state_key = f"architect_visual_{family}"
    payload = st.session_state.get(state_key, {"nodes": [], "edges": []})
    nodes = {item["id"]: item for item in payload.get("nodes", []) if item.get("id")}
    valid_ids = set(nodes)
    for flow_node in flow_state.nodes:
        node = nodes.get(flow_node.id)
        if node is None:
            continue
        node["x"] = float(flow_node.position["x"])
        node["y"] = float(flow_node.position["y"])
    payload["nodes"] = list(nodes.values())
    payload["edges"] = [
        {"id": edge.id, "source": edge.source, "target": edge.target}
        for edge in flow_state.edges
        if edge.source != edge.target and edge.source in valid_ids and edge.target in valid_ids
    ]
    payload["selected_id"] = flow_state.selected_id
    st.session_state[state_key] = payload


def architecture_canvas_state(family: str, doc: dict[str, Any]) -> StreamlitFlowState | None:
    state_key = f"architect_flow_state_{family}"
    signature_key = f"architect_flow_signature_{family}"
    signature = architecture_visual_signature(family, doc)
    cached_state = st.session_state.get(state_key)
    if cached_state is None or st.session_state.get(signature_key) != signature:
        cached_state = architecture_flow_state(family, doc)
        st.session_state[state_key] = cached_state
        st.session_state[signature_key] = signature
    return cached_state


def workspace_button_panel(current_page: str) -> str:
    chosen_page = current_page
    st.markdown("### Workspace")
    for row_index, group in enumerate(WORKSPACE_GROUPS):
        cols = st.columns(len(group), gap="small")
        for col, item in zip(cols, group):
            active = item["name"] == current_page
            with col:
                with st.container(border=True):
                    st.caption(item["kicker"])
                    if st.button(
                        item.get("button", item["name"]),
                        key=f"workspace_nav_{row_index}_{item['name']}",
                        use_container_width=True,
                        type="primary" if active else "secondary",
                    ):
                        chosen_page = item["name"]
                    st.caption(item["desc"])
    return chosen_page


def status_badge_html(status: str) -> str:
    safe = status.lower()
    return f'<span class="lab-status-pill" data-state="{safe}">{safe}</span>'


def launch_job(
    name: str,
    category: str,
    command: list[str],
    cwd: Path,
    expected_outputs: list[str] | None = None,
) -> None:
    ensure_layout()
    job_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    state_path = RUNS_DIR / "states" / f"{job_id}.json"
    log_path = RUNS_DIR / "logs" / f"{job_id}.log"
    state = {
        "id": job_id,
        "name": name,
        "category": category,
        "status": "queued",
        "command": command,
        "cwd": str(cwd),
        "log_path": str(log_path),
        "created_at": utc_now(),
        "expected_outputs": expected_outputs or [],
    }
    write_json(state_path, state)
    subprocess.Popen(
        [sys.executable, str(RUNNER_PATH), str(state_path)],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def load_jobs() -> list[dict[str, Any]]:
    ensure_layout()
    jobs = []
    for path in sorted((RUNS_DIR / "states").glob("*.json"), reverse=True):
        try:
            state = read_json(path)
            state["_state_path"] = str(path)
            jobs.append(state)
        except Exception:
            continue
    jobs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return jobs


def stop_job(job: dict[str, Any]) -> bool:
    target_pid = job.get("target_pid")
    state_path = Path(str(job["_state_path"]))
    if not target_pid:
        return False
    try:
        os.killpg(int(target_pid), signal.SIGTERM)
    except Exception:
        try:
            os.kill(int(target_pid), signal.SIGTERM)
        except Exception:
            return False
    state = read_json(state_path)
    state["status"] = "stopping"
    write_json(state_path, state)
    return True


def tail_log(path: Path, max_lines: int = 200) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(lines[-max_lines:])


def format_timestamp(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return value


def format_duration(started_at: str | None, finished_at: str | None) -> str:
    if not started_at:
        return "—"
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(finished_at.replace("Z", "+00:00")) if finished_at else datetime.now(timezone.utc)
        seconds = max((end - start).total_seconds(), 0.0)
    except Exception:
        return "—"
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.2f}h"


def metric_card(title: str, value: str, caption: str = "") -> None:
    st.markdown(
        f"""
        <div class="lab-card">
          <div class="lab-eyebrow">{title}</div>
          <h3>{value}</h3>
          <p>{caption}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="lab-card">
          <h3>{title}</h3>
          <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(
    title: str,
    subtitle: str,
    *,
    eyebrow: str = "Workspace",
    chips: list[tuple[str, str]] | None = None,
) -> None:
    chips_html = ""
    if chips:
        rendered = []
        for label, value in chips:
            rendered.append(
                f'<span class="lab-chip"><strong>{label}</strong><span>{value}</span></span>'
            )
        chips_html = f'<div class="lab-chip-row">{"".join(rendered)}</div>'
    st.markdown(
        f"""
        <div class="lab-page-header">
          <div class="lab-eyebrow">{eyebrow}</div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
          {chips_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def segmented_choice(
    label: str,
    options: list[str],
    *,
    key: str,
    default: str | None = None,
    help_text: str | None = None,
) -> str:
    if not options:
        raise ValueError("segmented_choice requires at least one option.")
    choice_default = default if default in options else options[0]
    if hasattr(st, "segmented_control"):
        choice = st.segmented_control(
            label,
            options,
            default=choice_default,
            selection_mode="single",
            help=help_text,
            key=key,
        )
        return choice or choice_default
    return st.radio(
        label,
        options,
        index=options.index(choice_default),
        horizontal=True,
        help=help_text,
        key=key,
    )


def frame_for_display(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.copy()
    for column in clean.columns:
        series = clean[column]
        if series.dtype == object:
            clean[column] = series.map(lambda value: "" if pd.isna(value) else str(value))
    return clean


def render_dataframe(df: pd.DataFrame, **kwargs: Any) -> None:
    st.dataframe(frame_for_display(df), **kwargs)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root { color-scheme: light dark; }
        section[data-testid="stSidebar"] {
          width: 19.5rem !important;
        }
        section[data-testid="stSidebar"] > div {
          width: 19.5rem !important;
        }
        .block-container {
          max-width: min(96vw, 1720px);
          padding-top: 2.85rem;
          padding-bottom: 3rem;
        }
        .lab-hero, .lab-card, .lab-shell-card, .lab-panel, .lab-page-header {
          border-radius: 1.4rem;
          border: 1px solid color-mix(in srgb, var(--text-color) 12%, transparent);
          background: color-mix(in srgb, var(--secondary-background-color) 90%, transparent);
          box-shadow: 0 18px 42px rgba(15, 23, 42, 0.07);
          color: var(--text-color);
        }
        .lab-hero {
          padding: 1.4rem 1.5rem;
          margin-bottom: 1.1rem;
          background:
            radial-gradient(circle at top right, rgba(37,99,235,0.20), transparent 30%),
            radial-gradient(circle at bottom left, rgba(16,185,129,0.15), transparent 24%),
            linear-gradient(180deg, color-mix(in srgb, var(--background-color) 98%, transparent), color-mix(in srgb, var(--secondary-background-color) 96%, transparent));
        }
        .lab-page-header {
          padding: 1.2rem 1.35rem 1.08rem;
          margin: 0.2rem 0 1.15rem;
          background:
            linear-gradient(135deg, rgba(37,99,235,0.12), transparent 42%),
            linear-gradient(325deg, rgba(16,185,129,0.09), transparent 38%),
            linear-gradient(180deg, color-mix(in srgb, var(--background-color) 99%, transparent), color-mix(in srgb, var(--secondary-background-color) 95%, transparent));
        }
        .lab-page-header h1 {
          margin: 0.55rem 0 0.18rem;
          font-size: 2.05rem;
          line-height: 1.06;
          color: var(--text-color);
        }
        .lab-page-header p {
          margin: 0.25rem 0 0;
          max-width: 75rem;
          color: color-mix(in srgb, var(--text-color) 74%, transparent);
          line-height: 1.5;
        }
        .lab-chip-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.55rem;
          margin-top: 0.82rem;
        }
        .lab-chip {
          display: inline-flex;
          align-items: center;
          gap: 0.38rem;
          padding: 0.34rem 0.72rem;
          border-radius: 999px;
          border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
          background: color-mix(in srgb, var(--background-color) 92%, transparent);
          font-size: 0.83rem;
          color: color-mix(in srgb, var(--text-color) 82%, transparent);
        }
        .lab-chip strong {
          font-weight: 800;
          color: var(--text-color);
        }
        .lab-eyebrow {
          display: inline-flex;
          width: fit-content;
          padding: 0.28rem 0.62rem;
          border-radius: 999px;
          background: color-mix(in srgb, var(--primary-color) 14%, transparent);
          color: var(--primary-color);
          font-size: 0.74rem;
          font-weight: 800;
          letter-spacing: 0.08em;
          text-transform: uppercase;
        }
        .lab-hero h1 {
          margin: 0.58rem 0 0.2rem;
          font-size: 2.3rem;
          line-height: 1.04;
          color: var(--text-color);
        }
        .lab-hero p,
        .lab-card p,
        .lab-caption {
          color: color-mix(in srgb, var(--text-color) 74%, transparent);
          line-height: 1.52;
        }
        .lab-card {
          padding: 1rem 1.05rem;
          height: 100%;
        }
        .lab-card h3 {
          margin: 0.1rem 0 0.3rem;
          font-size: 1.04rem;
          color: var(--text-color);
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
          border-radius: 1.25rem !important;
          border-color: color-mix(in srgb, var(--text-color) 10%, transparent) !important;
          background:
            linear-gradient(180deg, color-mix(in srgb, var(--background-color) 99%, transparent), color-mix(in srgb, var(--secondary-background-color) 95%, transparent));
          box-shadow: 0 14px 34px rgba(15, 23, 42, 0.04);
        }
        div[data-testid="stMetric"] {
          border-radius: 1.05rem;
          border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
          background: color-mix(in srgb, var(--background-color) 97%, transparent);
          padding: 0.9rem 1rem;
          min-height: 6.15rem;
        }
        div[data-testid="stMetricLabel"] {
          font-weight: 700;
        }
        div[data-testid="stMetricValue"] {
          font-size: 1.85rem;
        }
        div[data-testid="stDataFrame"] {
          border-radius: 1.05rem;
          overflow: hidden;
          border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
        }
        .stButton > button,
        .stDownloadButton > button {
          border-radius: 999px;
          border: 1px solid color-mix(in srgb, var(--primary-color) 28%, transparent);
          min-height: 2.8rem;
          font-weight: 700;
          box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
        }
        .stButton > button[kind="primary"],
        .stForm button[kind="primary"] {
          background: linear-gradient(135deg, color-mix(in srgb, var(--primary-color) 92%, white), color-mix(in srgb, var(--primary-color) 68%, black));
          color: white;
          border: none;
        }
        .lab-shell-card, .lab-panel {
          padding: 1.05rem 1.1rem;
        }
        .lab-section-title {
          margin-top: 0.2rem;
        }
        .lab-status-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.25rem 0.62rem;
          border-radius: 999px;
          font-size: 0.74rem;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .lab-status-pill[data-state="running"] {
          background: rgba(37, 99, 235, 0.12);
          color: #2563eb;
        }
        .lab-status-pill[data-state="completed"] {
          background: rgba(16, 185, 129, 0.12);
          color: #059669;
        }
        .lab-status-pill[data-state="failed"] {
          background: rgba(239, 68, 68, 0.12);
          color: #dc2626;
        }
        .lab-status-pill[data-state="queued"],
        .lab-status-pill[data-state="stopping"] {
          background: rgba(245, 158, 11, 0.12);
          color: #d97706;
        }
        .lab-svg-panel {
          padding: 1rem 1.05rem;
          border-radius: 1.2rem;
          border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
          background:
            linear-gradient(180deg, color-mix(in srgb, var(--background-color) 98%, transparent), color-mix(in srgb, var(--secondary-background-color) 96%, transparent));
          min-height: 320px;
        }
        .lab-svg-panel svg {
          width: 100%;
          height: auto;
          display: block;
        }
        .lab-workspace-panel {
          padding: 1.1rem 1.15rem;
          border-radius: 1.35rem;
          border: 1px solid color-mix(in srgb, var(--text-color) 11%, transparent);
          background:
            linear-gradient(180deg, color-mix(in srgb, var(--background-color) 99%, transparent), color-mix(in srgb, var(--secondary-background-color) 95%, transparent));
          box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
          margin-bottom: 1rem;
        }
        .lab-workspace-panel h3,
        .lab-workspace-panel h4 {
          margin-top: 0;
          color: var(--text-color);
        }
        .lab-workspace-panel p {
          color: color-mix(in srgb, var(--text-color) 74%, transparent);
          line-height: 1.55;
        }
        .lab-kicker-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.6rem;
          margin-bottom: 0.9rem;
        }
        .lab-kicker {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.42rem 0.82rem;
          border-radius: 999px;
          background: color-mix(in srgb, var(--primary-color) 10%, transparent);
          border: 1px solid color-mix(in srgb, var(--primary-color) 20%, transparent);
          font-size: 0.84rem;
          font-weight: 700;
          color: color-mix(in srgb, var(--text-color) 90%, transparent);
        }
        .lab-branch-strip {
          display: flex;
          flex-wrap: wrap;
          gap: 0.55rem;
          margin: 0.75rem 0 0.2rem;
        }
        .lab-branch-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.38rem;
          padding: 0.44rem 0.76rem;
          border-radius: 999px;
          border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
          font-size: 0.82rem;
          font-weight: 700;
          background: color-mix(in srgb, var(--background-color) 94%, transparent);
        }
        .lab-branch-pill[data-state="core"] {
          color: #2563eb;
          background: rgba(37, 99, 235, 0.11);
        }
        .lab-branch-pill[data-state="active"] {
          color: #059669;
          background: rgba(16, 185, 129, 0.12);
        }
        .lab-branch-pill[data-state="off"] {
          color: #64748b;
          background: rgba(148, 163, 184, 0.16);
        }
        .lab-branch-pill[data-state="removed"] {
          color: #dc2626;
          background: rgba(239, 68, 68, 0.11);
        }
        .lab-code-note {
          font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, monospace;
          font-size: 0.86rem;
          white-space: pre-wrap;
          word-break: break-word;
        }
        .lab-grid-2 {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 0.85rem;
        }
        .lab-small {
          font-size: 0.88rem;
        }
        .lab-sidebar-note {
          color: color-mix(in srgb, var(--text-color) 72%, transparent);
          font-size: 0.86rem;
          line-height: 1.45;
        }
        div[data-baseweb="tab-list"] {
          gap: 0.55rem;
          margin-bottom: 0.75rem;
        }
        .stTabs [data-baseweb="tab"] {
          padding: 0.58rem 0.9rem;
          border-radius: 999px;
          border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
          background: color-mix(in srgb, var(--secondary-background-color) 84%, transparent);
          font-weight: 700;
        }
        .stTabs [aria-selected="true"] {
          background: color-mix(in srgb, var(--primary-color) 14%, transparent);
          color: var(--primary-color);
          border-color: color-mix(in srgb, var(--primary-color) 28%, transparent);
        }
        .stSegmentedControl [data-baseweb="button-group"] button {
          border-radius: 999px !important;
          font-weight: 700;
          min-height: 2.4rem;
        }
        .lab-muted {
          color: color-mix(in srgb, var(--text-color) 70%, transparent);
        }
        .lab-divider {
          height: 1px;
          margin: 1rem 0 1.15rem;
          background: color-mix(in srgb, var(--text-color) 10%, transparent);
        }
        .lab-callout {
          padding: 0.9rem 1rem;
          border-radius: 1rem;
          border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
          background: color-mix(in srgb, var(--background-color) 96%, transparent);
          line-height: 1.55;
        }
        .lab-stat-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 0.78rem;
          margin-top: 0.95rem;
        }
        .lab-stat-tile {
          padding: 0.88rem 0.95rem;
          border-radius: 1rem;
          border: 1px solid color-mix(in srgb, var(--text-color) 9%, transparent);
          background: color-mix(in srgb, var(--background-color) 97%, transparent);
          min-height: 5.9rem;
        }
        .lab-stat-tile span {
          display: block;
          font-size: 0.8rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: color-mix(in srgb, var(--text-color) 64%, transparent);
        }
        .lab-stat-tile strong {
          display: block;
          margin-top: 0.28rem;
          font-size: 1.18rem;
          line-height: 1.15;
          color: var(--text-color);
        }
        .lab-stat-tile small {
          display: block;
          margin-top: 0.26rem;
          line-height: 1.35;
          color: color-mix(in srgb, var(--text-color) 70%, transparent);
        }
        @media (max-width: 1150px) {
          .lab-stat-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    palette = theme_palette()
    st.markdown(
        f"""
        <style>
        .js-plotly-plot .plotly .gtitle,
        .js-plotly-plot .plotly .xtitle,
        .js-plotly-plot .plotly .ytitle,
        .js-plotly-plot .plotly .annotation-text,
        .js-plotly-plot .plotly .legend text,
        .js-plotly-plot .plotly .legendtitletext,
        .js-plotly-plot .plotly .xtick text,
        .js-plotly-plot .plotly .ytick text,
        .js-plotly-plot .plotly .colorbar text,
        .js-plotly-plot .plotly .angularaxistick text,
        .js-plotly-plot .plotly .radialaxistick text {{
          fill: {palette["text"]} !important;
        }}
        .js-plotly-plot .plotly .gridlayer path,
        .js-plotly-plot .plotly .zerolinelayer path {{
          stroke: {hex_to_rgba(palette["border"], 0.34)} !important;
        }}
        .js-plotly-plot .plotly .xlines-above,
        .js-plotly-plot .plotly .ylines-above,
        .js-plotly-plot .plotly .xaxislayer-above path,
        .js-plotly-plot .plotly .yaxislayer-above path {{
          stroke: {hex_to_rgba(palette["border"], 0.5)} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_path_select(label: str, options: list[Path], default: Path | None = None, key: str = "") -> str:
    labels = [relative_label(path) for path in options]
    default_index = 0
    if default is not None:
        try:
            default_index = options.index(default)
        except ValueError:
            default_index = 0
    if options:
        choice = st.selectbox(label, labels, index=default_index, key=f"{key}_select")
        choice_path = options[labels.index(choice)]
    else:
        choice_path = default or REPO_ROOT
        st.text_input(label, value=str(choice_path), key=f"{key}_fallback", disabled=True)
    custom = st.text_input("Custom path override", value=str(choice_path), key=f"{key}_custom")
    return custom.strip()


def coerce_bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    series = df[column]
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    normalized = series.fillna(False).astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "yes", "y", "t"})


def canonicalize_smiles(smiles: str) -> tuple[str | None, str | None]:
    raw = str(smiles or "").strip()
    if not raw:
        return None, "The editor is empty."
    if Chem is None:
        return raw, None
    mol = Chem.MolFromSmiles(raw)
    if mol is None:
        return None, "The drawn structure could not be converted to a valid SMILES string."
    return Chem.MolToSmiles(mol, canonical=True), None


def parse_smiles_tokens(raw_text: str, library: dict[str, str] | None = None) -> list[tuple[str, str]]:
    if not raw_text:
        return []
    library = library or {}
    resolved: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for token in re.split(r"[,\n;]+", str(raw_text)):
        label = token.strip()
        if not label:
            continue
        smiles = library.get(label, label)
        canonical, error = canonicalize_smiles(smiles)
        if canonical is None or error:
            continue
        pair = (label, canonical)
        if pair in seen:
            continue
        seen.add(pair)
        resolved.append(pair)
    return resolved


def default_route_editor_frame() -> pd.DataFrame:
    return pd.DataFrame(APPLICATION_ROUTE_TEMPLATE)


def normalized_structure_summary(smiles: str, raw_smiles: str | None = None) -> dict[str, Any] | None:
    if Chem is None:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    raw = str(raw_smiles or "").strip()
    descriptor_info = descriptor_summary(smiles) or {}
    stats = model_cardinality_stats(smiles) or {}
    return {
        "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
        "normalization": "changed" if raw and raw != smiles else "same",
        "fragments": len(Chem.GetMolFrags(mol)),
        "formal_charge": int(Chem.GetFormalCharge(mol)),
        "heavy_atoms": int(mol.GetNumHeavyAtoms()),
        "stereocenters": len(Chem.FindMolChiralCenters(mol, includeUnassigned=True)),
        "formula": rdMolDescriptors.CalcMolFormula(mol) if rdMolDescriptors is not None else "—",
        "stats": stats,
        "descriptors": descriptor_info,
    }


def molecule_svg(smiles: str, width: int = 460, height: int = 320) -> str | None:
    if Chem is None or rdMolDraw2D is None:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
    options = drawer.drawOptions()
    options.padding = 0.06
    options.bondLineWidth = 1.8
    if st.get_option("theme.base") == "dark" and hasattr(rdMolDraw2D, "SetDarkMode"):
        try:
            rdMolDraw2D.SetDarkMode(options)
        except Exception:
            pass
    rdMolDraw2D.PrepareAndDrawMolecule(drawer, mol)
    drawer.FinishDrawing()
    return drawer.GetDrawingText().replace("svg:", "")


def render_molecule_panel(
    smiles: str,
    title: str,
    subtitle: str,
    *,
    width: int = 460,
    height: int = 320,
) -> None:
    st.markdown(f"**{title}**")
    st.caption(subtitle)
    if Chem is None:
        st.warning(f"RDKit is unavailable in the app environment: {RDKIT_ERROR}")
        return
    svg = molecule_svg(smiles, width=width, height=height)
    if svg:
        st.markdown(f'<div class="lab-svg-panel">{svg}</div>', unsafe_allow_html=True)
    else:
        st.error("RDKit could not parse this SMILES string.")


def descriptor_summary(smiles: str) -> dict[str, float] | None:
    if Chem is None or Descriptors is None:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return {
        "MolWt": round(float(Descriptors.MolWt(mol)), 3),
        "MolLogP": round(float(Descriptors.MolLogP(mol)), 3),
        "TPSA": round(float(Descriptors.TPSA(mol)), 3),
        "HBA": float(Descriptors.NumHAcceptors(mol)),
        "HBD": float(Descriptors.NumHDonors(mol)),
        "RotBonds": float(Descriptors.NumRotatableBonds(mol)),
    }


@st.cache_data(show_spinner=False)
def cached_dataframe(path_str: str) -> pd.DataFrame:
    return pd.read_csv(path_str, low_memory=False)


@st.cache_data(show_spinner=False)
def cached_yaml(path_str: str) -> dict[str, Any]:
    if yaml is None:
        return {}
    with Path(path_str).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@st.cache_data(show_spinner=False)
def cached_json(path_str: str) -> Any:
    return read_json(Path(path_str))


@st.cache_data(show_spinner=False)
def cached_fp_index(csv_path: str) -> dict[str, Any]:
    if Chem is None or AllChem is None:
        return {"solute_smiles": [], "solute_fps": [], "solvent_smiles": [], "solvent_fps": []}

    df = pd.read_csv(csv_path)
    solutes = sorted(set(df.get("solute_smiles", pd.Series(dtype=str)).dropna().astype(str)))
    solvents = sorted(set(df.get("solvent_smiles", pd.Series(dtype=str)).dropna().astype(str)))

    def to_fps(smiles_list: list[str]) -> tuple[list[str], list[Any]]:
        valid_smiles: list[str] = []
        fps: list[Any] = []
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                continue
            valid_smiles.append(smi)
            fps.append(AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048))
        return valid_smiles, fps

    solute_smiles, solute_fps = to_fps(solutes)
    solvent_smiles, solvent_fps = to_fps(solvents)
    return {
        "solute_smiles": solute_smiles,
        "solute_fps": solute_fps,
        "solvent_smiles": solvent_smiles,
        "solvent_fps": solvent_fps,
    }


def nearest_similarity(smiles: str, fp_bank: list[Any], smiles_bank: list[str]) -> tuple[float, str | None]:
    if Chem is None or AllChem is None or DataStructs is None:
        return 0.0, None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or not fp_bank:
        return 0.0, None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    similarities = DataStructs.BulkTanimotoSimilarity(fp, fp_bank)
    best_idx = int(np.argmax(similarities))
    return float(similarities[best_idx]), smiles_bank[best_idx]


@st.cache_data(show_spinner=False)
def probe_selected_python(python_command: str) -> dict[str, Any]:
    script = f"""
import importlib
import json
import platform
import sys
from pathlib import Path

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

modules = {{}}
for name in [
    "yaml",
    "numpy",
    "pandas",
    "rdkit",
    "torch",
    "torch_geometric",
    "scipy",
    "tgnn_solv",
    "tgnn_solv.inference",
]:
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", None)
        modules[name] = {{"ok": True, "version": version}}
    except Exception as exc:
        modules[name] = {{"ok": False, "error": f"{{type(exc).__name__}}: {{exc}}"}}

cuda_available = False
mps_available = False
if modules.get("torch", {{}}).get("ok"):
    import torch
    try:
        cuda_available = bool(torch.cuda.is_available())
    except Exception:
        cuda_available = False
    try:
        mps_available = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    except Exception:
        mps_available = False

payload = {{
    "ok": True,
    "python": sys.executable,
    "version": sys.version,
    "platform": platform.platform(),
    "cwd": str(Path.cwd()),
    "cuda_available": cuda_available,
    "mps_available": mps_available,
    "modules": modules,
}}
print(json.dumps(payload))
"""
    try:
        proc = subprocess.run(
            [*python_command_tokens(python_command), "-c", script],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=45,
        )
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    if proc.returncode != 0:
        return {
            "ok": False,
            "error": proc.stderr.strip() or proc.stdout.strip() or f"Process failed with code {proc.returncode}",
        }

    try:
        return extract_last_json_block(proc.stdout)
    except Exception:
        return {"ok": False, "error": proc.stdout.strip() or "Probe completed without valid JSON."}


def device_options_from_probe(probe: dict[str, Any]) -> list[str]:
    options = ["cpu"]
    if probe.get("cuda_available"):
        options.insert(0, "cuda")
    if probe.get("mps_available"):
        options.append("mps")
    return options


def module_ok(probe: dict[str, Any], name: str) -> bool:
    return bool(probe.get("modules", {}).get(name, {}).get("ok"))


def run_selected_python_json(
    python_command: str,
    script: str,
    args: list[str],
    timeout: int = 240,
) -> tuple[Any | None, str | None]:
    try:
        proc = subprocess.run(
            [*python_command_tokens(python_command), "-c", script, *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

    if proc.returncode != 0:
        details = proc.stderr.strip() or proc.stdout.strip() or f"Subprocess failed with code {proc.returncode}"
        return None, details

    try:
        return extract_last_json_block(proc.stdout), None
    except Exception:
        payload = proc.stdout.strip() or "Subprocess did not emit a JSON payload."
        return None, payload


@st.cache_data(show_spinner=False)
@st.cache_data(show_spinner=False)
def inspect_checkpoint(python_command: str, checkpoint_path: str, mtime: float) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

import torch

def safe_value(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {{str(k): safe_value(v) for k, v in value.items()}}
    if isinstance(value, (list, tuple)):
        return [safe_value(v) for v in value]
    return str(value)

path = Path(sys.argv[1])
checkpoint = torch.load(path, map_location="cpu", weights_only=False)
payload = {{
    "path": str(path),
    "top_level_keys": sorted(str(key) for key in checkpoint.keys()),
    "node_feat_dim": checkpoint.get("node_feat_dim"),
    "edge_feat_dim": checkpoint.get("edge_feat_dim"),
    "metadata": safe_value(checkpoint.get("metadata", {{}})),
    "config": safe_value(checkpoint.get("config", {{}})),
    "model_class": safe_value(checkpoint.get("model_class")),
    "model_type": safe_value(checkpoint.get("model_type")),
    "has_config": isinstance(checkpoint.get("config"), dict) and bool(checkpoint.get("config")),
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(python_command, script, [checkpoint_path], timeout=120)
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_model_inference(
    python_command: str,
    checkpoint_path: str,
    solute: str,
    solvent: str,
    temperature: float,
    scan_tmin: float,
    scan_tmax: float,
    scan_points: int,
    run_mc: bool,
    mc_samples: int,
    run_domain: bool,
    domain_csv: str,
    domain_fit_rows: int,
    domain_mahal_pct: float,
    domain_tani_threshold: float,
) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.inference import interpret_prediction, load_model, predict_solubility, temperature_scan
from tgnn_solv.uncertainty import MCDropoutPredictor

checkpoint_path = sys.argv[1]
solute = sys.argv[2]
solvent = sys.argv[3]
temperature = float(sys.argv[4])
scan_tmin = float(sys.argv[5])
scan_tmax = float(sys.argv[6])
scan_points = int(sys.argv[7])
run_mc = sys.argv[8] == "1"
mc_samples = int(sys.argv[9])
run_domain = sys.argv[10] == "1"
domain_csv = sys.argv[11]
domain_fit_rows = int(sys.argv[12])
domain_mahal_pct = float(sys.argv[13])
domain_tani_threshold = float(sys.argv[14])

model, cfg = load_model(checkpoint_path)
result = predict_solubility(model, solute, solvent, T=temperature)
scan_df = temperature_scan(
    model,
    solute,
    solvent,
    T_min=scan_tmin,
    T_max=scan_tmax,
    n_points=scan_points,
)
payload = {{
    "model_family": "tgnn_solv",
    "prediction": result,
    "scan": scan_df.to_dict(orient="records"),
    "interpretation": interpret_prediction(result),
    "config": cfg.__dict__,
}}
if run_mc:
    payload["mc_dropout"] = MCDropoutPredictor(model, n_samples=mc_samples).predict(solute, solvent, T=temperature)
if run_domain:
    try:
        import pandas as pd
        from tgnn_solv.data.dataset import make_loader
        from tgnn_solv.domain import ApplicabilityDomain

        train_df = pd.read_csv(domain_csv)
        original_rows = len(train_df)
        if domain_fit_rows > 0 and len(train_df) > domain_fit_rows:
            train_df = train_df.sample(n=domain_fit_rows, random_state=42).sort_index()
        train_loader = make_loader(
            train_df,
            batch_size=max(16, min(int(getattr(cfg, "batch_size", 64)), 128)),
            shuffle=False,
            num_workers=0,
            cache=True,
            use_pair_temperature_batching=False,
            use_morgan_features=bool(getattr(cfg, "use_morgan_features", False)),
            use_descriptor_augmentation=bool(getattr(cfg, "use_descriptor_augmentation", False)),
            use_descriptor_priors=bool(getattr(cfg, "use_descriptor_priors", False)),
            use_group_priors=bool(getattr(cfg, "use_group_priors", False)),
            use_gc_priors_crystal=bool(getattr(cfg, "use_gc_priors_crystal", False)),
            use_gasteiger_charges=bool(getattr(cfg, "use_gasteiger_charges", False)),
            use_phys_edge_features=bool(getattr(cfg, "use_phys_edge_features", False)),
        )
        ad = ApplicabilityDomain(
            model,
            train_loader=train_loader,
            mahalanobis_threshold=domain_mahal_pct,
            tanimoto_threshold=domain_tani_threshold,
        )
        payload["domain"] = ad.score(solute, solvent, T=temperature)
        payload["domain"]["fit_rows"] = int(len(train_df))
        payload["domain"]["sampled"] = bool(len(train_df) < original_rows)
        payload["domain"]["train_csv"] = domain_csv
        payload["domain"]["mahal_pct"] = domain_mahal_pct
        payload["domain"]["tani_threshold"] = domain_tani_threshold
        payload["domain_report"] = ad.report(solute, solvent, T=temperature)
    except Exception as exc:
        payload["domain_error"] = f"{{type(exc).__name__}}: {{exc}}"
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute,
            solvent,
            str(float(temperature)),
            str(float(scan_tmin)),
            str(float(scan_tmax)),
            str(int(scan_points)),
            "1" if run_mc else "0",
            str(int(mc_samples)),
            "1" if run_domain else "0",
            domain_csv,
            str(int(domain_fit_rows)),
            str(float(domain_mahal_pct)),
            str(float(domain_tani_threshold)),
        ],
        timeout=1500 if (run_mc or run_domain) else 480,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_direct_model_inference(
    python_command: str,
    checkpoint_path: str,
    solute: str,
    solvent: str,
    temperature: float,
    scan_tmin: float,
    scan_tmax: float,
    scan_points: int,
) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.inference import (
    interpret_direct_prediction,
    load_directgnn_model,
    predict_direct_solubility,
    temperature_scan_direct,
)

checkpoint_path = sys.argv[1]
solute = sys.argv[2]
solvent = sys.argv[3]
temperature = float(sys.argv[4])
scan_tmin = float(sys.argv[5])
scan_tmax = float(sys.argv[6])
scan_points = int(sys.argv[7])

model, cfg = load_directgnn_model(checkpoint_path)
result = predict_direct_solubility(model, solute, solvent, T=temperature)
scan_df = temperature_scan_direct(
    model,
    solute,
    solvent,
    T_min=scan_tmin,
    T_max=scan_tmax,
    n_points=scan_points,
)
payload = {{
    "model_family": "direct_gnn",
    "prediction": result,
    "scan": scan_df.to_dict(orient="records"),
    "interpretation": interpret_direct_prediction(result),
    "config": cfg.__dict__,
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute,
            solvent,
            str(float(temperature)),
            str(float(scan_tmin)),
            str(float(scan_tmax)),
            str(int(scan_points)),
        ],
        timeout=900,
    )
    if error:
        return {"error": error}
    return payload or {}


def run_uncertainty_inference(
    python_command: str,
    checkpoint_paths: tuple[str, ...],
    solute: str,
    solvent: str,
    temperature: float,
    scan_tmin: float,
    scan_tmax: float,
    scan_points: int,
    mc_samples: int,
    include_mc: bool,
) -> dict[str, Any]:
    script = f"""
import json
import numpy as np
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.inference import (
    load_directgnn_model,
    load_model,
    predict_direct_solubility,
    predict_solubility,
)
from tgnn_solv.uncertainty import EnsemblePredictor, MCDropoutPredictor

paths = [item for item in sys.argv[1].split("::") if item]
solute = sys.argv[2]
solvent = sys.argv[3]
temperature = float(sys.argv[4])
scan_tmin = float(sys.argv[5])
scan_tmax = float(sys.argv[6])
scan_points = int(sys.argv[7])
mc_samples = int(sys.argv[8])
include_mc = sys.argv[9] == "1"

models = []
configs = []
families = []
for path in paths:
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    model_class = str(checkpoint.get("model_class", "")).lower()
    model_type = str(checkpoint.get("model_type", "")).lower()
    top_keys = set(str(key) for key in checkpoint.keys())
    if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
        family = "direct_gnn"
        model, cfg = load_directgnn_model(path)
    else:
        family = "tgnn_solv"
        model, cfg = load_model(path)
    families.append(family)
    models.append(model)
    configs.append(getattr(cfg, "__dict__", {{}}))

if len(set(families)) != 1:
    raise ValueError("Selected uncertainty checkpoints must all belong to the same model family.")

family = families[0]
predict_one = predict_solubility if family == "tgnn_solv" else predict_direct_solubility

temps = np.linspace(scan_tmin, scan_tmax, scan_points).tolist()
payload = {{
    "checkpoints": paths,
    "n_models": len(models),
    "model_family": family,
    "member_predictions": [],
    "temperatures": temps,
    "configs": configs,
}}

for path, model in zip(paths, models):
    pred = predict_one(model, solute, solvent, T=temperature)
    member = {{
        "checkpoint": path,
        "ln_x2": pred["ln_x2"],
        "x2": pred["x2"],
    }}
    for key in ("gamma_2", "Phi", "T_m", "dH_fus", "correction", "gate"):
        if key in pred:
            member[key] = pred[key]
    payload["member_predictions"].append(member)

if len(models) >= 2:
    ensemble = EnsemblePredictor(models)
    payload["ensemble"] = ensemble.predict(solute, solvent, T=temperature)
    ensemble_scan = []
    for temp in temps:
        result = ensemble.predict(solute, solvent, T=float(temp))
        result["T"] = float(temp)
        ensemble_scan.append(result)
    payload["ensemble_scan"] = ensemble_scan

if include_mc and models:
    mc = MCDropoutPredictor(models[0], n_samples=mc_samples)
    payload["mc_dropout"] = mc.predict(solute, solvent, T=temperature)
    mc_scan = []
    for temp in temps:
        result = mc.predict(solute, solvent, T=float(temp))
        result["T"] = float(temp)
        mc_scan.append(result)
    payload["mc_scan"] = mc_scan

print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            "::".join(checkpoint_paths),
            solute,
            solvent,
            str(float(temperature)),
            str(float(scan_tmin)),
            str(float(scan_tmax)),
            str(int(scan_points)),
            str(int(mc_samples)),
            "1" if include_mc else "0",
        ],
        timeout=1800,
    )
    if error:
        return {"error": error}
    return payload or {}


def run_uncertainty_calibration(
    python_command: str,
    checkpoint_paths: tuple[str, ...],
    dataset_csv: str,
    sample_size: int,
    mc_samples: int,
    include_mc: bool,
    include_ensemble: bool,
) -> dict[str, Any]:
    script = f"""
import json
import pandas as pd
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.inference import load_directgnn_model, load_model
from tgnn_solv.uncertainty import EnsemblePredictor, MCDropoutPredictor, calibration_report

paths = [item for item in sys.argv[1].split("::") if item]
dataset_csv = sys.argv[2]
sample_size = int(sys.argv[3])
mc_samples = int(sys.argv[4])
include_mc = sys.argv[5] == "1"
include_ensemble = sys.argv[6] == "1"

df = pd.read_csv(dataset_csv)
if "has_solubility" in df.columns:
    df = df[df["has_solubility"].astype(bool)]
df = df.dropna(subset=["solute_smiles", "solvent_smiles", "temperature", "ln_x2"]).copy()
if sample_size > 0 and len(df) > sample_size:
    df = df.sample(n=sample_size, random_state=42).sort_index()

models = []
families = []
for path in paths:
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    model_class = str(checkpoint.get("model_class", "")).lower()
    model_type = str(checkpoint.get("model_type", "")).lower()
    top_keys = set(str(key) for key in checkpoint.keys())
    if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
        family = "direct_gnn"
        model, _ = load_directgnn_model(path)
    else:
        family = "tgnn_solv"
        model, _ = load_model(path)
    families.append(family)
    models.append(model)

if len(set(families)) != 1:
    raise ValueError("Selected calibration checkpoints must all belong to the same model family.")

payload = {{
    "dataset_csv": dataset_csv,
    "n_rows": int(len(df)),
    "checkpoints": paths,
    "model_family": families[0] if families else "unknown",
    "reports": {{}},
    "samples": {{}},
}}

def rows_from_predictions(method_name, predictions, true_values, systems):
    rows = []
    for pred, true_val, system in zip(predictions, true_values, systems):
        q05 = float(pred["ln_x2_q05"])
        q95 = float(pred["ln_x2_q95"])
        mean = float(pred["ln_x2_mean"])
        rows.append({{
            "method": method_name,
            "solute_smiles": system["solute_smiles"],
            "solvent_smiles": system["solvent_smiles"],
            "temperature": float(system["temperature"]),
            "true_ln_x2": float(true_val),
            "pred_ln_x2_mean": mean,
            "q05": q05,
            "q95": q95,
            "interval_width": q95 - q05,
            "covered": bool(q05 <= float(true_val) <= q95),
            "abs_error": abs(mean - float(true_val)),
        }})
    return rows

systems = df[["solute_smiles", "solvent_smiles", "temperature", "ln_x2"]].to_dict(orient="records")
true_ln_x2 = [float(row["ln_x2"]) for row in systems]

if include_ensemble and len(models) >= 2:
    ens = EnsemblePredictor(models)
    preds = [ens.predict(row["solute_smiles"], row["solvent_smiles"], T=float(row["temperature"])) for row in systems]
    payload["reports"]["ensemble"] = calibration_report(preds, true_ln_x2)
    payload["samples"]["ensemble"] = rows_from_predictions("ensemble", preds, true_ln_x2, systems)

if include_mc and models:
    mc = MCDropoutPredictor(models[0], n_samples=mc_samples)
    preds = [mc.predict(row["solute_smiles"], row["solvent_smiles"], T=float(row["temperature"])) for row in systems]
    payload["reports"]["mc_dropout"] = calibration_report(preds, true_ln_x2)
    payload["samples"]["mc_dropout"] = rows_from_predictions("mc_dropout", preds, true_ln_x2, systems)

print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            "::".join(checkpoint_paths),
            dataset_csv,
            str(int(sample_size)),
            str(int(mc_samples)),
            "1" if include_mc else "0",
            "1" if include_ensemble else "0",
        ],
        timeout=2400,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_synthesis_route_screen(
    python_command: str,
    checkpoint_path: str,
    route_payload_json: str,
    scan_points: int,
) -> dict[str, Any]:
    script = f"""
import json
import numpy as np
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import synthesis_window_metrics
from tgnn_solv.inference import (
    load_directgnn_model,
    load_model,
    predict_direct_solubility,
    predict_solubility,
)

checkpoint_path = sys.argv[1]
route_payload = json.loads(sys.argv[2])
scan_points = int(sys.argv[3])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, _ = load_directgnn_model(checkpoint_path)
    predict_one = predict_direct_solubility
else:
    family = "tgnn_solv"
    model, _ = load_model(checkpoint_path)
    predict_one = predict_solubility

rows = []
steps = []
for step in route_payload.get("steps", []):
    step_id = str(step.get("step_id", "step"))
    compound = str(step.get("compound_smiles", ""))
    reaction_temp = float(step.get("reaction_temp_k", 333.15))
    isolation_temp = float(step.get("isolation_temp_k", 278.15))
    goal = str(step.get("goal", "temperature-swing crystallization"))
    candidates = step.get("candidates", [])
    ranked = []
    scan_rows = []
    for candidate in candidates:
        solvent_label = str(candidate.get("label", candidate.get("smiles", "solvent")))
        solvent_smiles = str(candidate.get("smiles", ""))
        hot_pred = predict_one(model, compound, solvent_smiles, T=reaction_temp)
        cold_pred = predict_one(model, compound, solvent_smiles, T=isolation_temp)
        metrics = synthesis_window_metrics(hot_pred["ln_x2"], cold_pred["ln_x2"])
        row = {{
            "step_id": step_id,
            "goal": goal,
            "compound_smiles": compound,
            "reaction_temp_k": reaction_temp,
            "isolation_temp_k": isolation_temp,
            "solvent_label": solvent_label,
            "solvent_smiles": solvent_smiles,
            "hot_ln_x2": hot_pred["ln_x2"],
            "cold_ln_x2": cold_pred["ln_x2"],
            "delta_ln_x2": metrics["delta_ln_x2"],
            "swing_ratio": metrics["swing_ratio"],
            "route_score": metrics["route_score"],
            "regime": metrics["regime"],
        }}
        ranked.append(row)
        temps = np.linspace(min(reaction_temp, isolation_temp), max(reaction_temp, isolation_temp), max(scan_points, 4))
        for temp in temps:
            pred = predict_one(model, compound, solvent_smiles, T=float(temp))
            scan_rows.append({{
                "step_id": step_id,
                "solvent_label": solvent_label,
                "solvent_smiles": solvent_smiles,
                "T": float(temp),
                "ln_x2": float(pred["ln_x2"]),
            }})
    ranked.sort(key=lambda item: float(item["route_score"]), reverse=True)
    rows.extend(ranked)
    steps.append({{
        "step_id": step_id,
        "goal": goal,
        "compound_smiles": compound,
        "reaction_temp_k": reaction_temp,
        "isolation_temp_k": isolation_temp,
        "top_solvent": ranked[0]["solvent_label"] if ranked else None,
        "top_score": ranked[0]["route_score"] if ranked else None,
        "ranked": ranked,
        "scan": scan_rows,
    }})

top_choice_counts = {{}}
for step in steps:
    top_name = step.get("top_solvent")
    if top_name:
        top_choice_counts[top_name] = top_choice_counts.get(top_name, 0) + 1

payload = {{
    "model_family": family,
    "steps": steps,
    "rows": rows,
    "summary": {{
        "n_steps": len(steps),
        "n_candidates": len(rows),
        "top_choice_counts": top_choice_counts,
        "mean_top_score": float(np.mean([step["top_score"] for step in steps if step.get("top_score") is not None])) if steps else None,
    }},
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [checkpoint_path, route_payload_json, str(int(scan_points))],
        timeout=2400,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_developability_screen(
    python_command: str,
    checkpoint_path: str,
    solute_smiles: str,
    temperature: float,
    dose_mg: float,
    media_payload_json: str,
) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from rdkit import Chem
from rdkit.Chem import Descriptors

from tgnn_solv.applications import (
    aqueous_max_supported_dose_mg,
    dose_margin,
    mole_fraction_to_molarity_in_water,
    pharma_capability_matrix,
)
from tgnn_solv.inference import (
    load_directgnn_model,
    load_model,
    predict_direct_solubility,
    predict_solubility,
)

checkpoint_path = sys.argv[1]
solute_smiles = sys.argv[2]
temperature = float(sys.argv[3])
dose_mg = float(sys.argv[4])
media_payload = json.loads(sys.argv[5])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, _ = load_directgnn_model(checkpoint_path)
    predict_one = predict_direct_solubility
else:
    family = "tgnn_solv"
    model, _ = load_model(checkpoint_path)
    predict_one = predict_solubility

mol = Chem.MolFromSmiles(solute_smiles)
mol_weight = float(Descriptors.MolWt(mol)) if mol is not None else None
rows = []
water_x2 = None
for medium in media_payload:
    label = str(medium.get("label", "medium"))
    smiles = str(medium.get("smiles", ""))
    pred = predict_one(model, solute_smiles, smiles, T=temperature)
    row = {{
        "medium": label,
        "smiles": smiles,
        "ln_x2": float(pred["ln_x2"]),
        "x2": float(pred["x2"]),
    }}
    rows.append(row)
    if label.lower() == "water" or smiles == "O":
        water_x2 = float(pred["x2"])

rows.sort(key=lambda item: float(item["ln_x2"]), reverse=True)
for row in rows:
    row["fold_vs_water"] = (float(row["x2"]) / water_x2) if (water_x2 is not None and water_x2 > 0) else None
    if row["medium"].lower() == "water" or row["smiles"] == "O":
        row["molarity_proxy_mol_l"] = mole_fraction_to_molarity_in_water(float(row["x2"]))
        row["max_supported_dose_mg_250ml"] = aqueous_max_supported_dose_mg(float(row["x2"]), mol_weight)
        row["dose_margin"] = dose_margin(row["max_supported_dose_mg_250ml"], dose_mg if dose_mg > 0 else None)
    else:
        row["molarity_proxy_mol_l"] = None
        row["max_supported_dose_mg_250ml"] = None
        row["dose_margin"] = None

best_cosolvent_uplift = None
for row in rows:
    if row["medium"].lower() == "water" or row["smiles"] == "O":
        continue
    fold = row.get("fold_vs_water")
    if fold is None:
        continue
    if best_cosolvent_uplift is None or float(fold) > float(best_cosolvent_uplift):
        best_cosolvent_uplift = float(fold)

water_row = next((row for row in rows if row["medium"].lower() == "water" or row["smiles"] == "O"), None)
payload = {{
    "model_family": family,
    "solute_smiles": solute_smiles,
    "temperature": temperature,
    "dose_mg": dose_mg,
    "mol_weight": mol_weight,
    "rows": rows,
    "water_row": water_row,
    "best_cosolvent_uplift": best_cosolvent_uplift,
    "capability_matrix": pharma_capability_matrix(
        water_margin=water_row.get("dose_margin") if water_row else None,
        has_water_prediction=bool(water_row),
        best_cosolvent_uplift=best_cosolvent_uplift,
    ),
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute_smiles,
            str(float(temperature)),
            str(float(dose_mg)),
            media_payload_json,
        ],
        timeout=1800,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_drug_developability_analysis(
    python_command: str,
    checkpoint_path: str,
    solute_smiles: str,
    temperature: float,
    dose_mg: float,
    volume_ml: float,
    counterions_json: str,
) -> dict[str, Any]:
    script = f"""
import json
import math
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import DrugPropertyPredictor
from tgnn_solv.inference import load_directgnn_model, load_model

checkpoint_path = sys.argv[1]
solute_smiles = sys.argv[2]
temperature = float(sys.argv[3])
dose_mg = float(sys.argv[4])
volume_ml = float(sys.argv[5])
counterions = json.loads(sys.argv[6])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, cfg = load_directgnn_model(checkpoint_path)
else:
    family = "tgnn_solv"
    model, cfg = load_model(checkpoint_path)

predictor = DrugPropertyPredictor(model, cfg, next(model.parameters()).device)

def to_jsonable(value):
    if isinstance(value, dict):
        return {{str(key): to_jsonable(val) for key, val in value.items()}}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "to_dict") and value.__class__.__name__ == "DataFrame":
        return value.where(value.notna(), None).to_dict(orient="records")
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        try:
            scalar = value.item()
            if isinstance(scalar, float):
                return scalar if math.isfinite(scalar) else None
            return scalar
        except Exception:
            return value
    return value

bcs = predictor.bcs_classify(solute_smiles, dose_mg=dose_mg, volume_mL=volume_ml, T=temperature)
developability = predictor.developability_score(solute_smiles, T=temperature)
media_profile = predictor.pharma_media_profile(solute_smiles, T=temperature)
reference_comparison = predictor.compare_with_reference_drugs(solute_smiles, top_k=5)
salt_screen = predictor.salt_cocrystal_impact(solute_smiles, counterions, T=temperature)

payload = {{
    "model_family": family,
    "checkpoint_path": checkpoint_path,
    "solute_smiles": solute_smiles,
    "temperature": temperature,
    "dose_mg": dose_mg,
    "volume_ml": volume_ml,
    "bcs": to_jsonable(bcs),
    "developability": to_jsonable(developability),
    "media_profile": to_jsonable(media_profile),
    "reference_comparison": to_jsonable(reference_comparison),
    "salt_cocrystal_screen": to_jsonable(salt_screen),
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute_smiles,
            str(float(temperature)),
            str(float(dose_mg)),
            str(float(volume_ml)),
            counterions_json,
        ],
        timeout=3600,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_pk_profile_analysis(
    python_command: str,
    checkpoint_path: str,
    solute_smiles: str,
    dose_mg: float,
) -> dict[str, Any]:
    script = f"""
import json
import math
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import PKSolubilityProfiler
from tgnn_solv.inference import load_directgnn_model, load_model

checkpoint_path = sys.argv[1]
solute_smiles = sys.argv[2]
dose_mg = float(sys.argv[3])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, cfg = load_directgnn_model(checkpoint_path)
else:
    family = "tgnn_solv"
    model, cfg = load_model(checkpoint_path)

profiler = PKSolubilityProfiler(model, cfg, next(model.parameters()).device)

def to_jsonable(value):
    if isinstance(value, dict):
        return {{str(key): to_jsonable(val) for key, val in value.items()}}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "to_dict") and value.__class__.__name__ == "DataFrame":
        return value.where(value.notna(), None).to_dict(orient="records")
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        try:
            scalar = value.item()
            if isinstance(scalar, float):
                return scalar if math.isfinite(scalar) else None
            return scalar
        except Exception:
            return value
    return value

payload = {{
    "model_family": family,
    "checkpoint_path": checkpoint_path,
    "solute_smiles": solute_smiles,
    "dose_mg": dose_mg,
    "gi_profile": to_jsonable(profiler.gi_tract_profile(solute_smiles, dose_mg=dose_mg)),
    "biorelevant_media": to_jsonable(profiler.biorelevant_media_screen(solute_smiles)),
    "iv_screen": to_jsonable(profiler.iv_formulation_screening(solute_smiles)),
    "topical_screen": to_jsonable(profiler.topical_vehicle_screening(solute_smiles)),
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute_smiles,
            str(float(dose_mg)),
        ],
        timeout=3600,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_solvent_swap_screen(
    python_command: str,
    checkpoint_path: str,
    solute_smiles: str,
    donor_smiles: str,
    donor_label: str,
    acceptor_payload_json: str,
    transfer_temp: float,
    isolation_temp: float,
    scan_points: int,
) -> dict[str, Any]:
    script = f"""
import json
import numpy as np
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import solvent_swap_metrics, synthesis_window_metrics
from tgnn_solv.inference import (
    load_directgnn_model,
    load_model,
    predict_direct_solubility,
    predict_solubility,
)

checkpoint_path = sys.argv[1]
solute_smiles = sys.argv[2]
donor_smiles = sys.argv[3]
donor_label = sys.argv[4]
acceptor_payload = json.loads(sys.argv[5])
transfer_temp = float(sys.argv[6])
isolation_temp = float(sys.argv[7])
scan_points = int(sys.argv[8])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, _ = load_directgnn_model(checkpoint_path)
    predict_one = predict_direct_solubility
else:
    family = "tgnn_solv"
    model, _ = load_model(checkpoint_path)
    predict_one = predict_solubility

donor_hot = predict_one(model, solute_smiles, donor_smiles, T=transfer_temp)
rows = []
scan = []
for acceptor in acceptor_payload:
    label = str(acceptor.get("label", "acceptor"))
    smiles = str(acceptor.get("smiles", ""))
    target_hot = predict_one(model, solute_smiles, smiles, T=transfer_temp)
    target_cold = predict_one(model, solute_smiles, smiles, T=isolation_temp)
    swap = solvent_swap_metrics(donor_hot["ln_x2"], target_hot["ln_x2"])
    cold_window = synthesis_window_metrics(target_hot["ln_x2"], target_cold["ln_x2"])
    rows.append({{
        "acceptor_label": label,
        "acceptor_smiles": smiles,
        "donor_label": donor_label,
        "donor_smiles": donor_smiles,
        "transfer_temp_k": transfer_temp,
        "isolation_temp_k": isolation_temp,
        "donor_hot_ln_x2": float(donor_hot["ln_x2"]),
        "acceptor_hot_ln_x2": float(target_hot["ln_x2"]),
        "acceptor_cold_ln_x2": float(target_cold["ln_x2"]),
        "delta_ln_x2": float(swap["delta_ln_x2"]),
        "crash_ratio": float(swap["crash_ratio"]),
        "transfer_score": float(swap["transfer_score"]),
        "regime": str(swap["regime"]),
        "cold_capture_score": float(cold_window["route_score"]),
    }})
    temps = np.linspace(min(transfer_temp, isolation_temp), max(transfer_temp, isolation_temp), max(scan_points, 4))
    for temp in temps:
        pred = predict_one(model, solute_smiles, smiles, T=float(temp))
        scan.append({{
            "acceptor_label": label,
            "T": float(temp),
            "ln_x2": float(pred["ln_x2"]),
        }})

rows.sort(key=lambda item: float(item["transfer_score"]), reverse=True)
payload = {{
    "model_family": family,
    "solute_smiles": solute_smiles,
    "donor_label": donor_label,
    "donor_smiles": donor_smiles,
    "rows": rows,
    "scan": scan,
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute_smiles,
            donor_smiles,
            donor_label,
            acceptor_payload_json,
            str(float(transfer_temp)),
            str(float(isolation_temp)),
            str(int(scan_points)),
        ],
        timeout=1800,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_solvent_screening(
    python_command: str,
    checkpoint_path: str,
    solute_smiles: str,
    temperature: float,
    top_k: int,
    filters_json: str,
) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import SolventScreener
from tgnn_solv.inference import load_directgnn_model, load_model

checkpoint_path = sys.argv[1]
solute_smiles = sys.argv[2]
temperature = float(sys.argv[3])
top_k = int(sys.argv[4])
filters = json.loads(sys.argv[5])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, cfg = load_directgnn_model(checkpoint_path)
else:
    family = "tgnn_solv"
    model, cfg = load_model(checkpoint_path)

screener = SolventScreener(model, cfg, next(model.parameters()).device)
screen_df = screener.screen(solute_smiles, T=temperature, top_k=top_k, filters=filters, return_details=True)
records = screen_df.where(screen_df.notna(), None).to_dict(orient="records")
payload = {{
    "model_family": family,
    "checkpoint_path": checkpoint_path,
    "solute_smiles": solute_smiles,
    "temperature": temperature,
    "screening_rows": records,
    "assumptions": screen_df.attrs.get("assumptions", {{}}),
    "library_size": len(screener.solvent_library),
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute_smiles,
            str(float(temperature)),
            str(int(top_k)),
            filters_json,
        ],
        timeout=3600,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_crystallization_window_analysis(
    python_command: str,
    checkpoint_path: str,
    solute_smiles: str,
    solvent_smiles: str,
    temperature_hot: float | None,
    temperature_cold: float | None,
    n_points: int,
) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import SolventScreener
from tgnn_solv.inference import load_directgnn_model, load_model

checkpoint_path = sys.argv[1]
solute_smiles = sys.argv[2]
solvent_smiles = sys.argv[3]
temperature_hot = None if sys.argv[4] == "none" else float(sys.argv[4])
temperature_cold = None if sys.argv[5] == "none" else float(sys.argv[5])
n_points = int(sys.argv[6])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, cfg = load_directgnn_model(checkpoint_path)
else:
    family = "tgnn_solv"
    model, cfg = load_model(checkpoint_path)

screener = SolventScreener(model, cfg, next(model.parameters()).device)
payload = screener.crystallization_window(
    solute_smiles,
    solvent_smiles,
    T_hot=temperature_hot,
    T_cold=temperature_cold,
    n_points=n_points,
)
scan = payload["temperature_scan"].where(payload["temperature_scan"].notna(), None).to_dict(orient="records")
payload["temperature_scan"] = scan
payload["model_family"] = family
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute_smiles,
            solvent_smiles,
            "none" if temperature_hot is None else str(float(temperature_hot)),
            "none" if temperature_cold is None else str(float(temperature_cold)),
            str(int(n_points)),
        ],
        timeout=2400,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_antisolvent_screening_analysis(
    python_command: str,
    checkpoint_path: str,
    solute_smiles: str,
    good_solvent_smiles: str,
    temperature: float,
) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import SolventScreener
from tgnn_solv.inference import load_directgnn_model, load_model

checkpoint_path = sys.argv[1]
solute_smiles = sys.argv[2]
good_solvent_smiles = sys.argv[3]
temperature = float(sys.argv[4])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, cfg = load_directgnn_model(checkpoint_path)
else:
    family = "tgnn_solv"
    model, cfg = load_model(checkpoint_path)

screener = SolventScreener(model, cfg, next(model.parameters()).device)
df = screener.antisolvent_screening(solute_smiles, good_solvent_smiles, T=temperature)
payload = {{
    "model_family": family,
    "rows": df.where(df.notna(), None).to_dict(orient="records"),
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [checkpoint_path, solute_smiles, good_solvent_smiles, str(float(temperature))],
        timeout=2400,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_green_replacement_analysis(
    python_command: str,
    checkpoint_path: str,
    solute_smiles: str,
    current_solvent_smiles: str,
    temperature: float,
    min_solubility_fraction: float,
) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import SolventScreener
from tgnn_solv.inference import load_directgnn_model, load_model

checkpoint_path = sys.argv[1]
solute_smiles = sys.argv[2]
current_solvent_smiles = sys.argv[3]
temperature = float(sys.argv[4])
min_solubility_fraction = float(sys.argv[5])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, cfg = load_directgnn_model(checkpoint_path)
else:
    family = "tgnn_solv"
    model, cfg = load_model(checkpoint_path)

screener = SolventScreener(model, cfg, next(model.parameters()).device)
df = screener.green_solvent_replacement(
    solute_smiles,
    current_solvent_smiles,
    T=temperature,
    min_solubility_fraction=min_solubility_fraction,
)
payload = {{
    "model_family": family,
    "rows": df.where(df.notna(), None).to_dict(orient="records"),
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute_smiles,
            current_solvent_smiles,
            str(float(temperature)),
            str(float(min_solubility_fraction)),
        ],
        timeout=2400,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_process_optimization_analysis(
    python_command: str,
    checkpoint_path: str,
    mode: str,
    payload_json: str,
) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path
import pandas as pd
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import ProcessOptimizer
from tgnn_solv.inference import load_directgnn_model, load_model

checkpoint_path = sys.argv[1]
mode = sys.argv[2]
payload = json.loads(sys.argv[3])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, cfg = load_directgnn_model(checkpoint_path)
else:
    family = "tgnn_solv"
    model, cfg = load_model(checkpoint_path)

optimizer = ProcessOptimizer(model, cfg, next(model.parameters()).device)
if mode == "crystallization":
    result = optimizer.optimize_crystallization(
        payload["solute_smiles"],
        target_yield=float(payload.get("target_yield", 0.8)),
        T_range=(float(payload.get("T_min", 273.0)), float(payload.get("T_max", 373.0))),
        constraints=payload.get("constraints"),
    )
elif mode == "extraction":
    result = optimizer.optimize_extraction(
        payload["solute_smiles"],
        payload["source_solvent"],
        T=float(payload.get("temperature", 298.15)),
        constraints=payload.get("constraints"),
    )
elif mode == "reaction_medium":
    result = optimizer.optimize_reaction_medium(
        payload["reactants"],
        payload["product_smiles"],
        T_reaction=float(payload.get("temperature", 298.15)),
        constraints=payload.get("constraints"),
    )
else:
    result = optimizer.design_solvent_system(
        payload["solute_smiles"],
        tuple(payload["target_solubility_range"]),
        T=float(payload.get("temperature", 298.15)),
    )

if isinstance(result, pd.DataFrame):
    result_payload = result.where(result.notna(), None).to_dict(orient="records")
    assumptions = getattr(result, "attrs", {{}}).get("assumptions", {{}})
else:
    result_payload = result
    assumptions = {{}}

payload = {{
    "model_family": family,
    "mode": mode,
    "checkpoint_path": checkpoint_path,
    "result": result_payload,
    "assumptions": assumptions,
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [checkpoint_path, mode, payload_json],
        timeout=3600,
    )
    if error:
        return {"error": error}
    return payload or {}


@st.cache_data(show_spinner=False)
def run_process_candidate_scan(
    python_command: str,
    checkpoint_path: str,
    solute_smiles: str,
    solvent_smiles: str,
    T_min: float,
    T_max: float,
    n_points: int,
) -> dict[str, Any]:
    script = f"""
import json
import sys
from pathlib import Path
import torch

repo_root = Path({str(REPO_ROOT)!r})
src_root = repo_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from tgnn_solv.applications import SolventScreener
from tgnn_solv.inference import load_directgnn_model, load_model

checkpoint_path = sys.argv[1]
solute_smiles = sys.argv[2]
solvent_smiles = sys.argv[3]
T_min = float(sys.argv[4])
T_max = float(sys.argv[5])
n_points = int(sys.argv[6])

checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
model_class = str(checkpoint.get("model_class", "")).lower()
model_type = str(checkpoint.get("model_type", "")).lower()
top_keys = set(str(key) for key in checkpoint.keys())
if ("directgnn" in model_class or "direct" in model_type) and ({{"model_state", "model_state_dict"}} & top_keys):
    family = "direct_gnn"
    model, cfg = load_directgnn_model(checkpoint_path)
else:
    family = "tgnn_solv"
    model, cfg = load_model(checkpoint_path)

screener = SolventScreener(model, cfg, next(model.parameters()).device)
scan = screener._augment_scan(
    screener._temperature_scan(solute_smiles, solvent_smiles, T_min=T_min, T_max=T_max, n_points=n_points),
    solute_smiles,
    solvent_smiles,
)
payload = {{
    "model_family": family,
    "scan": scan.where(scan.notna(), None).to_dict(orient="records"),
}}
print(json.dumps(payload))
"""
    payload, error = run_selected_python_json(
        python_command,
        script,
        [
            checkpoint_path,
            solute_smiles,
            solvent_smiles,
            str(float(T_min)),
            str(float(T_max)),
            str(int(n_points)),
        ],
        timeout=2400,
    )
    if error:
        return {"error": error}
    return payload or {}


def split_family_options() -> dict[str, dict[str, Path]]:
    families: dict[str, dict[str, Path]] = {}
    candidates = {
        "Scaffold-aware canonical split": {
            "train": PROCESSED_DIR / "train.csv",
            "val": PROCESSED_DIR / "val.csv",
            "test": PROCESSED_DIR / "test.csv",
        },
        "Solute holdout split": {
            "train": PROCESSED_DIR / "train_solute.csv",
            "val": PROCESSED_DIR / "val_solute.csv",
            "test": PROCESSED_DIR / "test_solute.csv",
        },
        "Solvent holdout split": {
            "train": PROCESSED_DIR / "train_solvent.csv",
            "val": PROCESSED_DIR / "val_solvent.csv",
            "test": PROCESSED_DIR / "test_solvent.csv",
        },
    }
    for name, mapping in candidates.items():
        if all(path.exists() for path in mapping.values()):
            families[name] = mapping
    return families


def split_summary_frame(family_mapping: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for split_name, path in family_mapping.items():
        df = cached_dataframe(str(path))
        rows.append(
            {
                "split": split_name,
                "rows": int(len(df)),
                "solutes": int(df["solute_smiles"].nunique()) if "solute_smiles" in df.columns else 0,
                "solvents": int(df["solvent_smiles"].nunique()) if "solvent_smiles" in df.columns else 0,
                "pairs": int(df[["solute_smiles", "solvent_smiles"]].drop_duplicates().shape[0])
                if {"solute_smiles", "solvent_smiles"} <= set(df.columns)
                else 0,
                "supervised": int(coerce_bool_series(df, "has_solubility").sum()),
                "T_m": int(coerce_bool_series(df, "has_T_m").sum()),
                "dH_fus": int(coerce_bool_series(df, "has_dH_fus").sum()),
                "Hansen": int(coerce_bool_series(df, "has_hansen").sum()),
                "gamma_inf": int(coerce_bool_series(df, "has_gamma_inf").sum()),
            }
        )
    return pd.DataFrame(rows)


def coverage_frame(family_mapping: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for split_name, path in family_mapping.items():
        df = cached_dataframe(str(path))
        denom = max(len(df), 1)
        for label, column in [
            ("solubility", "has_solubility"),
            ("T_m", "has_T_m"),
            ("dH_fus", "has_dH_fus"),
            ("Hansen", "has_hansen"),
            ("gamma_inf", "has_gamma_inf"),
        ]:
            rows.append(
                {
                    "split": split_name,
                    "label": label,
                    "fraction": float(coerce_bool_series(df, column).sum()) / denom,
                }
            )
    return pd.DataFrame(rows)


def representative_system_frame(df: pd.DataFrame, limit: int = 120) -> pd.DataFrame:
    view = df.copy()
    supervised_mask = coerce_bool_series(view, "has_solubility")
    if supervised_mask.any():
        view = view.loc[supervised_mask].copy()
    view = view.head(limit).reset_index(drop=True)
    if view.empty:
        return view
    solute_name = view["solute_name"] if "solute_name" in view.columns else pd.Series("", index=view.index)
    solvent_name = view["solvent_name"] if "solvent_name" in view.columns else pd.Series("", index=view.index)
    view["preview_label"] = (
        solute_name.fillna("").astype(str).replace("", pd.NA).fillna(view["solute_smiles"].astype(str).str.slice(0, 24))
        + " in "
        + solvent_name.fillna("").astype(str).replace("", pd.NA).fillna(view["solvent_smiles"].astype(str).str.slice(0, 20))
        + " @ "
        + view["temperature"].astype(float).round(1).astype(str)
        + " K"
    )
    return view


def config_feature_rows(config_path: str) -> pd.DataFrame:
    cfg = cached_yaml(config_path)
    if not isinstance(cfg, dict):
        return pd.DataFrame(columns=["feature", "value"])
    model = cfg.get("model", {})
    training = cfg.get("training", {})
    rows = [
        {"feature": "Encoder type", "value": model.get("encoder_type", "mpnn")},
        {
            "feature": "GPS PE",
            "value": model.get("gps_positional_encoding", "—")
            if model.get("encoder_type", "mpnn") == "gps"
            else "off",
        },
        {
            "feature": "GPS heads / PE dim",
            "value": (
                f"{model.get('gps_num_heads', '—')} / {model.get('gps_pe_dim', '—')}"
                if model.get("encoder_type", "mpnn") == "gps"
                else "—"
            ),
        },
        {"feature": "Shared encoder", "value": model.get("encoder_role_mode", "—")},
        {"feature": "Cross-attention layers", "value": model.get("n_cross_attn_layers", "—")},
        {"feature": "Descriptor augmentation", "value": model.get("use_descriptor_augmentation", "—")},
        {"feature": "Morgan features", "value": model.get("use_morgan_features", "—")},
        {"feature": "Descriptor priors", "value": model.get("use_descriptor_priors", "—")},
        {"feature": "Group priors", "value": model.get("use_group_priors", "—")},
        {"feature": "GC crystal priors", "value": model.get("use_gc_priors_crystal", "—")},
        {"feature": "Implicit differentiation", "value": model.get("use_implicit_diff", "—")},
        {"feature": "Solvent MoE", "value": model.get("use_solvent_moe", "—")},
        {"feature": "Pair-temp batching", "value": training.get("use_pair_temperature_batching", "—")},
        {"feature": "Batch size", "value": training.get("batch_size", "—")},
    ]
    return pd.DataFrame(rows)


def job_status_counts(jobs: list[dict[str, Any]]) -> pd.DataFrame:
    statuses = ["queued", "running", "stopping", "completed", "failed"]
    rows = []
    for status in statuses:
        rows.append({"status": status, "count": sum(job.get("status") == status for job in jobs)})
    return pd.DataFrame(rows)


def top_counts_frame(df: pd.DataFrame, column: str, top_n: int = 12, label: str = "value") -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=[label, "count"])
    counts = df[column].astype(str).value_counts().head(top_n)
    return pd.DataFrame({label: counts.index.tolist(), "count": counts.values.tolist()})


@st.cache_data(show_spinner=False)
def discover_metric_csvs() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(RESULTS_DIR.rglob("*.csv")):
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if not {"model", "mae"} <= set(df.columns):
            continue
        for _, row in df.iterrows():
            entry = {"artifact": relative_label(path), "model": row.get("model")}
            for metric in ("mae", "rmse", "r2", "bias", "runtime_s", "val_loss"):
                if metric in df.columns:
                    entry[metric] = row.get(metric)
            if "split" in df.columns:
                entry["split"] = row.get("split")
            rows.append(entry)
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def discover_evaluation_jsons() -> list[str]:
    candidates = []
    for path in RESULTS_DIR.rglob("*.json"):
        try:
            payload = read_json(path)
        except Exception:
            continue
        if isinstance(payload, dict) and ("overall" in payload or payload.get("report_type") == "evaluation"):
            candidates.append(str(path))
    return sorted(candidates)


def benchmark_root_candidates() -> list[Path]:
    candidates = [
        RESULTS_DIR / "external_baselines",
        RESULTS_DIR / "custom_benchmarks",
        RESULTS_DIR,
        TMP_DIR,
    ]
    existing = [path for path in candidates if path.exists()]
    return existing or [RESULTS_DIR]


def _safe_read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data(show_spinner=False)
def discover_benchmark_runs(search_roots: tuple[str, ...]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    seen_summaries: set[str] = set()
    for root_str in search_roots:
        if not root_str:
            continue
        root = Path(root_str).expanduser()
        if not root.exists():
            continue
        for summary_path in sorted(root.rglob("summary.csv")):
            summary_key = str(summary_path.resolve())
            if summary_key in seen_summaries:
                continue
            seen_summaries.add(summary_key)
            bundle_dir = summary_path.parent
            report_path = bundle_dir / "report.json"
            predictions_path = bundle_dir / "predictions.csv"
            metadata_path = bundle_dir / "metadata.json"
            benchmark_card_path = bundle_dir / "benchmark_card.json"
            run_manifest_path = bundle_dir / "run_manifest.json"
            if not report_path.exists() and not predictions_path.exists():
                continue
            try:
                summary_df = pd.read_csv(summary_path)
            except Exception:
                continue
            if summary_df.empty or "model" not in summary_df.columns:
                continue
            report_payload = _safe_read_json(report_path) if report_path.exists() else {}
            report_metadata = report_payload.get("metadata", {}) if isinstance(report_payload, dict) else {}
            metadata_payload = _safe_read_json(metadata_path) if metadata_path.exists() else {}
            metadata: dict[str, Any] = {}
            if isinstance(report_metadata, dict):
                metadata.update(report_metadata)
            if isinstance(metadata_payload, dict):
                metadata.update(metadata_payload)
            benchmark_card = _safe_read_json(benchmark_card_path) if benchmark_card_path.exists() else {}
            card_capabilities = benchmark_card.get("capabilities", {}) if isinstance(benchmark_card, dict) else {}
            stat = summary_path.stat()
            split_info = metadata.get("split", {}) if isinstance(metadata.get("split"), dict) else {}
            root_label = relative_label(root) if root.exists() else str(root)
            for index, record in summary_df.iterrows():
                model_name = str(record.get("model") or bundle_dir.name)
                split_name = (
                    record.get("split")
                    or split_info.get("split_mode")
                    or split_info.get("mode")
                    or split_info.get("display_name")
                    or "unknown"
                )
                overall = report_payload.get("overall", {}) if isinstance(report_payload, dict) else {}
                model_family = (
                    metadata.get("model_family")
                    or artifact_model_guess(bundle_dir)
                    or artifact_model_guess(summary_path)
                )
                n_samples_value = pd.to_numeric(record.get("n_samples", overall.get("n_samples")), errors="coerce")
                n_predictions_value = pd.to_numeric(record.get("n_predictions", overall.get("n_predictions")), errors="coerce")
                rows.append(
                    {
                        "run_id": f"{relative_label(bundle_dir)}::{index}::{model_name}",
                        "bundle_dir": str(bundle_dir),
                        "bundle_label": relative_label(bundle_dir),
                        "root_label": root_label,
                        "summary_path": str(summary_path),
                        "report_path": str(report_path) if report_path.exists() else "",
                        "predictions_path": str(predictions_path) if predictions_path.exists() else "",
                        "metadata_path": str(metadata_path) if metadata_path.exists() else "",
                        "benchmark_card_path": str(benchmark_card_path) if benchmark_card_path.exists() else "",
                        "run_manifest_path": str(run_manifest_path) if run_manifest_path.exists() else "",
                        "model": model_name,
                        "model_family": str(model_family),
                        "split": str(split_name),
                        "mae": pd.to_numeric(record.get("mae"), errors="coerce"),
                        "rmse": pd.to_numeric(record.get("rmse"), errors="coerce"),
                        "r2": pd.to_numeric(record.get("r2"), errors="coerce"),
                        "bias": pd.to_numeric(record.get("bias"), errors="coerce"),
                        "n_samples": int(n_samples_value) if pd.notna(n_samples_value) else 0,
                        "n_predictions": int(n_predictions_value) if pd.notna(n_predictions_value) else 0,
                        "has_report": report_path.exists(),
                        "has_predictions": predictions_path.exists(),
                        "predictions_source": str(metadata.get("predictions_csv") or ""),
                        "merge_on": str(metadata.get("merge_on") or ""),
                        "has_uncertainty": bool(card_capabilities.get("uncertainty")),
                        "has_physics": bool(card_capabilities.get("physics_decomposition")),
                        "has_ood": bool(card_capabilities.get("ood_screening")),
                        "native_training": bool(card_capabilities.get("native_training")),
                        "custom_adapter": bool(card_capabilities.get("custom_adapter")),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                        "modified_ts": stat.st_mtime,
                    }
                )
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    frame = frame.sort_values(["mae", "modified_ts"], ascending=[True, False], na_position="last").reset_index(drop=True)
    return frame


def benchmark_stratified_frame(report_payload: Any) -> pd.DataFrame:
    if not isinstance(report_payload, dict):
        return pd.DataFrame()
    stratified = report_payload.get("stratified", {})
    if not isinstance(stratified, dict):
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for group_name, group_payload in stratified.items():
        if not isinstance(group_payload, dict):
            continue
        for bucket_name, bucket_metrics in group_payload.items():
            if not isinstance(bucket_metrics, dict):
                continue
            rows.append(
                {
                    "group": str(group_name),
                    "bucket": str(bucket_name),
                    "mae": pd.to_numeric(bucket_metrics.get("mae"), errors="coerce"),
                    "rmse": pd.to_numeric(bucket_metrics.get("rmse"), errors="coerce"),
                    "r2": pd.to_numeric(bucket_metrics.get("r2"), errors="coerce"),
                    "bias": pd.to_numeric(bucket_metrics.get("bias"), errors="coerce"),
                    "n_samples": int(pd.to_numeric(bucket_metrics.get("n_samples", bucket_metrics.get("n")), errors="coerce") or 0),
                }
            )
    return pd.DataFrame(rows)


def benchmark_predictions_frame(path_str: str) -> pd.DataFrame:
    if not path_str:
        return pd.DataFrame()
    try:
        return cached_dataframe(path_str)
    except Exception:
        return pd.DataFrame()


def benchmark_metric_summary_rows(run_row: pd.Series) -> list[tuple[str, str]]:
    return [
        ("Model", str(run_row.get("model", "—"))),
        ("Family", str(run_row.get("model_family", "—"))),
        ("Split", str(run_row.get("split", "—"))),
        ("MAE", f"{float(run_row.get('mae')):.4f}" if pd.notna(run_row.get("mae")) else "—"),
        ("RMSE", f"{float(run_row.get('rmse')):.4f}" if pd.notna(run_row.get("rmse")) else "—"),
        ("R²", f"{float(run_row.get('r2')):.4f}" if pd.notna(run_row.get("r2")) else "—"),
        ("Rows", str(int(run_row.get("n_samples", 0) or 0))),
        ("Predictions", str(int(run_row.get("n_predictions", 0) or 0))),
    ]


def render_benchmark_studio() -> None:
    palette = theme_palette()
    default_roots = [str(path) for path in benchmark_root_candidates()]
    root_cols = st.columns([1.25, 1.0], gap="large")
    with root_cols[0]:
        selected_roots = st.multiselect(
            "Benchmark search roots",
            default_roots,
            default=[str(path) for path in benchmark_root_candidates()[:2]],
            help="Canonical benchmark bundles are discovered from directories containing `summary.csv`, `report.json`, and `predictions.csv`.",
        )
    with root_cols[1]:
        extra_root = st.text_input(
            "Additional root (optional)",
            value="",
            help="Use this for ad-hoc benchmark outputs outside `results/`, e.g. `tmp/external_benchmark_native_smoke2`.",
        ).strip()
    active_roots = tuple(dict.fromkeys([*selected_roots, extra_root] if extra_root else selected_roots))
    run_df = discover_benchmark_runs(active_roots)
    if run_df.empty:
        st.info("No canonical benchmark bundles were found under the selected roots.")
        return

    summary_cols = st.columns(4)
    with summary_cols[0]:
        st.metric("Benchmark runs", str(len(run_df)))
    with summary_cols[1]:
        st.metric("Families", str(run_df["model_family"].nunique()))
    with summary_cols[2]:
        st.metric("Custom runs", str(int((run_df["model_family"] == "custom").sum())))
    with summary_cols[3]:
        st.metric("Roots", str(len(active_roots)))

    filter_cols = st.columns([0.95, 0.95, 0.9, 1.2], gap="small")
    with filter_cols[0]:
        family_options = sorted(run_df["model_family"].dropna().astype(str).unique().tolist())
        family_filter = st.multiselect("Model family", family_options, default=family_options)
    with filter_cols[1]:
        split_options = sorted(run_df["split"].dropna().astype(str).unique().tolist())
        split_filter = st.multiselect("Split", split_options, default=split_options)
    with filter_cols[2]:
        metric_name = st.selectbox("Ranking metric", ["mae", "rmse", "r2", "bias"], index=0, key="benchmark_metric_name")
    with filter_cols[3]:
        query = st.text_input("Search", value="", help="Filter by model name, bundle path, or source predictions file.")

    filtered = run_df.copy()
    if family_filter:
        filtered = filtered[filtered["model_family"].isin(family_filter)]
    if split_filter:
        filtered = filtered[filtered["split"].isin(split_filter)]
    if query.strip():
        q = query.strip().lower()
        filtered = filtered[
            filtered["model"].astype(str).str.lower().str.contains(q, regex=False)
            | filtered["bundle_label"].astype(str).str.lower().str.contains(q, regex=False)
            | filtered["predictions_source"].astype(str).str.lower().str.contains(q, regex=False)
        ]
    if filtered.empty:
        st.info("No benchmark runs match the current filters.")
        return

    ascending = metric_name != "r2"
    filtered = filtered.sort_values(metric_name, ascending=ascending, na_position="last").reset_index(drop=True)
    leaderboard = filtered[
        [
            "model",
            "model_family",
            "split",
            "mae",
            "rmse",
            "r2",
            "bias",
            "n_samples",
            "bundle_label",
        ]
    ].copy()
    leaderboard["bundle_label"] = leaderboard["bundle_label"].map(lambda value: compact_path_label(value, keep_segments=4))
    st.markdown("### Benchmark leaderboard")
    render_dataframe(leaderboard.head(120), use_container_width=True, hide_index=True)

    chart_df = filtered.dropna(subset=[metric_name]).copy().head(24)
    if not chart_df.empty:
        title = f"{metric_name.upper()} across benchmark bundles"
        fig = px.bar(
            chart_df,
            x="model",
            y=metric_name,
            color="model_family",
            hover_data=["split", "bundle_label"],
            text_auto=".3f" if metric_name != "r2" else ".2f",
            title=title,
            height=430,
        )
        fig.update_xaxes(tickangle=28)
        st.plotly_chart(style_plot(fig), use_container_width=True)

    labels = filtered["run_id"].tolist()
    label_to_row = {str(row["run_id"]): row for _, row in filtered.iterrows()}
    focused_run_id = st.selectbox(
        "Focused benchmark run",
        labels,
        format_func=lambda value: f"{label_to_row[value]['model']} · {label_to_row[value]['split']} · {compact_path_label(label_to_row[value]['bundle_label'], keep_segments=4)}",
        key="focused_benchmark_run",
    )
    focused_row = filtered.loc[filtered["run_id"] == focused_run_id].iloc[0]
    compare_default = labels[: min(4, len(labels))]
    compare_run_ids = st.multiselect(
        "Compare runs",
        labels,
        default=[focused_run_id, *[item for item in compare_default if item != focused_run_id][:2]],
        format_func=lambda value: f"{label_to_row[value]['model']} · {compact_path_label(label_to_row[value]['bundle_label'], keep_segments=3)}",
        key="benchmark_compare_runs",
    )
    compare_df = filtered[filtered["run_id"].isin(compare_run_ids)].copy()

    info_left, info_right = st.columns([0.95, 1.05], gap="large")
    with info_left:
        st.markdown("### Focused run")
        stat_grid = "".join(
            f'<div class="lab-stat-tile"><span>{escape(key)}</span><strong>{escape(value)}</strong></div>'
            for key, value in benchmark_metric_summary_rows(focused_row)
        )
        st.markdown(f'<div class="lab-stat-grid">{stat_grid}</div>', unsafe_allow_html=True)
        meta_rows = [
            {"field": "bundle", "value": focused_row["bundle_label"]},
            {"field": "report", "value": compact_path_label(focused_row["report_path"], keep_segments=4) if focused_row["report_path"] else "—"},
            {"field": "predictions", "value": compact_path_label(focused_row["predictions_path"], keep_segments=4) if focused_row["predictions_path"] else "—"},
            {"field": "benchmark card", "value": compact_path_label(focused_row["benchmark_card_path"], keep_segments=4) if focused_row["benchmark_card_path"] else "—"},
            {"field": "run manifest", "value": compact_path_label(focused_row["run_manifest_path"], keep_segments=4) if focused_row["run_manifest_path"] else "—"},
            {"field": "predictions source", "value": focused_row["predictions_source"] or "—"},
            {"field": "merge mode", "value": focused_row["merge_on"] or "—"},
            {"field": "uncertainty", "value": "yes" if focused_row.get("has_uncertainty") else "no"},
            {"field": "physics", "value": "yes" if focused_row.get("has_physics") else "no"},
            {"field": "OOD", "value": "yes" if focused_row.get("has_ood") else "no"},
            {"field": "modified", "value": focused_row["modified_at"]},
        ]
        render_dataframe(pd.DataFrame(meta_rows), use_container_width=True, hide_index=True)
        if compare_df.shape[0] > 1:
            compare_table = compare_df[["model", "model_family", "split", "mae", "rmse", "r2", "bias"]].copy()
            compare_table = compare_table.sort_values(metric_name, ascending=ascending, na_position="last")
            with st.expander("Selected-run metric table", expanded=True):
                render_dataframe(compare_table, use_container_width=True, hide_index=True)
    with info_right:
        compare_plot_df = compare_df.melt(
            id_vars=["model", "model_family", "split"],
            value_vars=["mae", "rmse", "r2"],
            var_name="metric",
            value_name="value",
        ).dropna(subset=["value"])
        if not compare_plot_df.empty:
            fig = px.bar(
                compare_plot_df,
                x="metric",
                y="value",
                color="model",
                barmode="group",
                hover_data=["model_family", "split"],
                title="Selected-run metric comparison",
                height=360,
            )
            st.plotly_chart(style_plot(fig), use_container_width=True)

    report_payload = cached_json(str(focused_row["report_path"])) if focused_row["report_path"] else {}
    benchmark_card_payload = cached_json(str(focused_row["benchmark_card_path"])) if focused_row["benchmark_card_path"] else {}
    run_manifest_payload = cached_json(str(focused_row["run_manifest_path"])) if focused_row["run_manifest_path"] else {}
    predictions_df = benchmark_predictions_frame(str(focused_row["predictions_path"]))
    detail_left, detail_right = st.columns([1.15, 0.85], gap="large")
    with detail_left:
        st.markdown("### Prediction diagnostics")
        if {"ln_x2", "ln_x2_pred"} <= set(predictions_df.columns):
            plot_df = predictions_df.dropna(subset=["ln_x2", "ln_x2_pred"]).copy()
            if not plot_df.empty:
                lo = float(np.nanmin([plot_df["ln_x2"].min(), plot_df["ln_x2_pred"].min()]))
                hi = float(np.nanmax([plot_df["ln_x2"].max(), plot_df["ln_x2_pred"].max()]))
                parity = px.scatter(
                    plot_df,
                    x="ln_x2",
                    y="ln_x2_pred",
                    color="temperature" if "temperature" in plot_df.columns else None,
                    hover_data=["solute_smiles", "solvent_smiles"] if {"solute_smiles", "solvent_smiles"} <= set(plot_df.columns) else None,
                    title="Parity: predicted vs true ln(x2)",
                    height=420,
                )
                parity.add_trace(
                    go.Scatter(
                        x=[lo, hi],
                        y=[lo, hi],
                        mode="lines",
                        name="ideal",
                        line={"color": palette["border"], "dash": "dash"},
                    )
                )
                st.plotly_chart(style_plot(parity), use_container_width=True)

                diag_cols = st.columns(2, gap="large")
                with diag_cols[0]:
                    resid = go.Figure()
                    resid.add_trace(
                        go.Histogram(
                            x=plot_df["error"] if "error" in plot_df.columns else (plot_df["ln_x2_pred"] - plot_df["ln_x2"]),
                            marker_color=palette["blue"],
                            opacity=0.9,
                            nbinsx=32,
                            name="residual",
                        )
                    )
                    resid.update_layout(title="Residual distribution", height=330, xaxis_title="prediction error", yaxis_title="count")
                    st.plotly_chart(style_plot(resid), use_container_width=True)
                with diag_cols[1]:
                    if "temperature" in plot_df.columns:
                        temp_df = plot_df.copy()
                        temp_df["abs_error_plot"] = (
                            temp_df["abs_error"] if "abs_error" in temp_df.columns else (temp_df["ln_x2_pred"] - temp_df["ln_x2"]).abs()
                        )
                        temp_fig = px.scatter(
                            temp_df,
                            x="temperature",
                            y="abs_error_plot",
                            color="solvent_smiles" if "solvent_smiles" in temp_df.columns else None,
                            title="Absolute error vs temperature",
                            height=330,
                        )
                        st.plotly_chart(style_plot(temp_fig), use_container_width=True)
                    else:
                        st.info("No temperature column available for temperature diagnostics.")
                if "prediction_std" in plot_df.columns:
                    unc_fig = px.scatter(
                        plot_df.assign(
                            abs_error_plot=plot_df["abs_error"] if "abs_error" in plot_df.columns else (plot_df["ln_x2_pred"] - plot_df["ln_x2"]).abs()
                        ),
                        x="prediction_std",
                        y="abs_error_plot",
                        color="temperature" if "temperature" in plot_df.columns else None,
                        title="Uncertainty proxy vs absolute error",
                        height=320,
                    )
                    st.plotly_chart(style_plot(unc_fig), use_container_width=True)
            else:
                st.info("Predictions file exists, but it does not contain finite `ln_x2` / `ln_x2_pred` pairs.")
        else:
            st.info("No canonical predictions file is available for the focused bundle.")
    with detail_right:
        if benchmark_card_payload:
            with st.expander("Benchmark card", expanded=False):
                st.json(benchmark_card_payload)
        if run_manifest_payload:
            with st.expander("Run manifest", expanded=False):
                st.json(run_manifest_payload)
        st.markdown("### Stratified metrics")
        stratified_df = benchmark_stratified_frame(report_payload)
        if stratified_df.empty:
            st.info("No stratified metrics were found in the report.")
        else:
            render_dataframe(stratified_df, use_container_width=True, hide_index=True)
            strat_metric = st.selectbox("Stratified metric", ["mae", "rmse", "r2", "bias"], key="stratified_metric")
            strat_fig = px.bar(
                stratified_df.dropna(subset=[strat_metric]),
                x="bucket",
                y=strat_metric,
                color="group",
                hover_data=["n_samples"],
                title=f"{strat_metric.upper()} by stratified bucket",
                height=360,
            )
            strat_fig.update_xaxes(tickangle=28)
            st.plotly_chart(style_plot(strat_fig), use_container_width=True)

    with st.expander("Predictions preview", expanded=False):
        if predictions_df.empty:
            st.info("No predictions preview is available.")
        else:
            preview_cols = [
                column
                for column in [
                    "row_index",
                    "solute_smiles",
                    "solvent_smiles",
                    "temperature",
                    "ln_x2",
                    "ln_x2_pred",
                    "prediction_std",
                    "error",
                    "abs_error",
                    "model",
                ]
                if column in predictions_df.columns
            ]
            render_dataframe(predictions_df[preview_cols].head(200), use_container_width=True, hide_index=True)


def config_training_snapshot(config_path: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    cfg = cached_yaml(config_path)
    training = cfg.get("training", {}) if isinstance(cfg, dict) else {}
    model = cfg.get("model", {}) if isinstance(cfg, dict) else {}
    losses = cfg.get("loss_weights", {}) if isinstance(cfg, dict) else {}
    phase_df = pd.DataFrame(
        [
            {
                "phase": "Phase 1",
                "epochs": training.get("epochs_phase1", 0),
                "lr": training.get("lr_phase1"),
            },
            {
                "phase": "Phase 2",
                "epochs": training.get("epochs_phase2", 0),
                "lr": training.get("lr_phase2"),
            },
            {
                "phase": "Phase 3",
                "epochs": training.get("epochs_phase3", 0),
                "lr": training.get("lr_phase3"),
            },
        ]
    )
    phase2 = losses.get("phase2", {}) if isinstance(losses, dict) else {}
    loss_df = pd.DataFrame(
        [{"loss": name, "weight": value} for name, value in phase2.items() if isinstance(value, (int, float))]
    ).sort_values("weight", ascending=False)
    meta = {
        "batch_size": training.get("batch_size"),
        "warmup_epochs": training.get("warmup_epochs"),
        "pair_temp_batching": training.get("use_pair_temperature_batching"),
        "hidden_dim": model.get("hidden_dim"),
        "layers": model.get("n_gnn_layers"),
        "encoder_type": model.get("encoder_type", "mpnn"),
        "gps_positional_encoding": model.get("gps_positional_encoding"),
        "gps_num_heads": model.get("gps_num_heads"),
        "gps_pe_dim": model.get("gps_pe_dim"),
        "cross_attn_layers": model.get("n_cross_attn_layers"),
        "dropout": model.get("dropout"),
        "encoder_role_mode": model.get("encoder_role_mode"),
        "use_descriptor_augmentation": model.get("use_descriptor_augmentation", False),
        "nrtl_tau_mode": model.get("nrtl_tau_mode"),
    }
    return phase_df, loss_df, meta


def json_summary_view(data: Any) -> None:
    if isinstance(data, dict) and data.get("report_type") == "evaluation":
        evaluation_report_view(data)
        with st.expander("Raw JSON", expanded=False):
            st.json(data)
        return

    if isinstance(data, dict) and "overall" in data and isinstance(data["overall"], dict):
        evaluation_report_view(data)
        with st.expander("Raw JSON", expanded=False):
            st.json(data)
        return

    if isinstance(data, dict) and "per_seed" in data and isinstance(data["per_seed"], list):
        per_seed = pd.DataFrame(data["per_seed"])
        render_dataframe(per_seed, use_container_width=True)
        numeric_cols = [col for col in per_seed.columns if pd.api.types.is_numeric_dtype(per_seed[col])]
        if "seed" in per_seed.columns and numeric_cols:
            metric = st.selectbox("Metric", numeric_cols, index=0, key="seed_metric")
            fig = px.line(per_seed, x="seed", y=metric, markers=True, title=f"{metric} by seed", height=420)
            st.plotly_chart(style_plot(fig), use_container_width=True)
        with st.expander("Raw JSON", expanded=False):
            st.json(data)
        return

    if isinstance(data, dict):
        summary_rows = []
        for key, value in data.items():
            if isinstance(value, (int, float, str, bool)):
                summary_rows.append({"key": key, "value": value})
        if summary_rows:
            render_dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
        st.json(data)
        return

    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            render_dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.write(data)


def evaluation_report_view(data: dict[str, Any]) -> None:
    overall = data.get("overall", {})
    cols = st.columns(5)
    metrics = [
        ("MAE", overall.get("mae", "—")),
        ("RMSE", overall.get("rmse", "—")),
        ("R²", overall.get("r2", "—")),
        ("Pearson", overall.get("pearson_r", overall.get("pearson", "—"))),
        ("Samples", overall.get("n_samples", overall.get("n", "—"))),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            if isinstance(value, (float, int)):
                st.metric(label, f"{float(value):.3f}" if label != "Samples" else str(int(value)))
            else:
                st.metric(label, str(value))

    preds = data.get("predictions", {})
    if isinstance(preds, dict) and {"true_ln_x2", "pred_ln_x2"} <= set(preds.keys()):
        df = pd.DataFrame(
            {
                "true_ln_x2": preds["true_ln_x2"],
                "pred_ln_x2": preds["pred_ln_x2"],
            }
        )
        df["abs_error"] = (df["pred_ln_x2"] - df["true_ln_x2"]).abs()
        left, right = st.columns(2, gap="large")
        with left:
            fig = px.scatter(
                df,
                x="true_ln_x2",
                y="pred_ln_x2",
                color="abs_error",
                color_continuous_scale="Turbo",
                title="Parity scatter",
                height=440,
            )
            min_v = float(df[["true_ln_x2", "pred_ln_x2"]].min().min())
            max_v = float(df[["true_ln_x2", "pred_ln_x2"]].max().max())
            fig.add_shape(type="line", x0=min_v, y0=min_v, x1=max_v, y1=max_v, line={"dash": "dash"})
            st.plotly_chart(style_plot(fig), use_container_width=True)
        with right:
            hist = px.histogram(df, x="abs_error", nbins=35, title="Absolute error distribution", height=440)
            st.plotly_chart(style_plot(hist), use_container_width=True)

    by_temp = data.get("by_temperature", {})
    if isinstance(by_temp, dict) and by_temp:
        rows = []
        for bucket, metrics in by_temp.items():
            if isinstance(metrics, dict):
                rows.append({"bucket": bucket, **metrics})
        if rows:
            bucket_df = pd.DataFrame(rows)
            if "mae" in bucket_df.columns:
                fig = px.bar(bucket_df, x="bucket", y="mae", title="MAE by temperature bucket", color="mae", height=380)
                st.plotly_chart(style_plot(fig), use_container_width=True)


def dataframe_plot_builder(df: pd.DataFrame, key_prefix: str) -> None:
    if df.empty:
        st.info("Selected CSV is empty.")
        return
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    categorical_cols = [col for col in df.columns if col not in numeric_cols]
    plot_type = st.selectbox("Chart type", ["Scatter", "Line", "Bar", "Histogram", "Box"], key=f"{key_prefix}_type")
    x_col = st.selectbox("X axis", df.columns.tolist(), key=f"{key_prefix}_x")
    y_candidates = numeric_cols or df.columns.tolist()
    y_col = st.selectbox("Y axis", y_candidates, key=f"{key_prefix}_y")
    color_col = st.selectbox("Color", ["(none)"] + categorical_cols, key=f"{key_prefix}_color")
    color_value = None if color_col == "(none)" else color_col

    if plot_type == "Scatter":
        fig = px.scatter(df, x=x_col, y=y_col, color=color_value, height=520)
    elif plot_type == "Line":
        fig = px.line(df, x=x_col, y=y_col, color=color_value, markers=True, height=520)
    elif plot_type == "Bar":
        fig = px.bar(df, x=x_col, y=y_col, color=color_value, height=520)
    elif plot_type == "Histogram":
        fig = px.histogram(df, x=x_col, color=color_value, height=520)
    else:
        fig = px.box(df, x=x_col, y=y_col, color=color_value, height=520)
    st.plotly_chart(style_plot(fig), use_container_width=True)


def render_overview(python_command: str, probe: dict[str, Any]) -> None:
    summary = filesystem_summary()
    jobs = load_jobs()
    running = sum(job.get("status") == "running" for job in jobs)
    st.markdown(
        f"""
        <div class="lab-hero">
          <div class="lab-eyebrow">Interactive lab</div>
          <h1>{APP_TITLE}</h1>
          <p>
            One control surface for data preparation, TGNN-Solv and DirectGNN training, experiment orchestration,
            artifact inspection, paper reproduction, and detailed single-system inference. The UI surfaces the
            repository’s real scripts and outputs instead of introducing a second workflow.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(5)
    with cols[0]:
        metric_card("Processed CSVs", str(summary["processed_splits"]), "Detected under notebooks/data/processed")
    with cols[1]:
        metric_card("Checkpoints", str(summary["checkpoints"]), "Available for evaluation and inference")
    with cols[2]:
        metric_card("Artifacts", str(summary["artifacts"]), "JSON, CSV, image, and figure outputs")
    with cols[3]:
        metric_card("Running jobs", str(running), "Persistent background jobs tracked under results/lab_runs")
    with cols[4]:
        accel = "CUDA" if probe.get("cuda_available") else ("MPS" if probe.get("mps_available") else "CPU")
        metric_card("Selected runtime", accel, f"Interpreter: {probe.get('python', python_command)}")

    quick_left, quick_right = st.columns([1.15, 0.95], gap="large")
    with quick_left:
        st.subheader("Canonical workflow")
        st.caption("The main research path is kept explicit: each card maps directly to a maintained CLI entry point.")
        for index, (name, description, command) in enumerate(WORKFLOW_STEPS, start=1):
            with st.container(border=True):
                st.markdown(f"**{index}. {name}**")
                st.caption(description)
                st.code(quote_command(command), language="bash")
    with quick_right:
        st.subheader("Environment signal")
        if not probe.get("ok"):
            st.error(probe.get("error", "Python runtime probe failed."))
        else:
            info_card("Python command", probe.get("python", python_command))
            inference_ok = module_ok(probe, "tgnn_solv.inference")
            pyg_ok = module_ok(probe, "torch_geometric")
            scipy_ok = module_ok(probe, "scipy")
            status_lines = [
                f"`tgnn_solv.inference`: {'ok' if inference_ok else 'broken'}",
                f"`torch_geometric`: {'ok' if pyg_ok else 'broken'}",
                f"`scipy`: {'ok' if scipy_ok else 'broken'}",
            ]
            st.markdown("\n".join(status_lines))
            if not inference_ok:
                st.warning(
                    "The selected interpreter cannot import the inference stack. Use the Environment page to inspect the failure and point the app at a working Python."
                )

        st.subheader("Recent jobs")
        if not jobs:
            st.info("No jobs have been launched yet.")
        else:
            for job in jobs[:5]:
                st.markdown(
                    f"""
                    <div class="lab-card">
                      <div style="display:flex;justify-content:space-between;gap:0.75rem;align-items:center;">
                        <strong>{job.get("name", "Unnamed job")}</strong>
                        {status_badge_html(str(job.get("status", "unknown")))}
                      </div>
                      <p class="lab-code-note">{quote_command(job.get("command", []))}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.subheader("Design studios")
    studio_cols = st.columns(3, gap="large")
    with studio_cols[0]:
        info_card(
            "Pipeline Studio",
            "Airflow-style DAG editor for the real CLI workflow: preset pipelines, dependency validation, node-level launch, and sequential shell export.",
        )
    with studio_cols[1]:
        info_card(
            "Model Architect",
            "Visual TGNN-Solv / DirectGNN editor with live config controls, forward-path diagram, structure-derived graph previews, and YAML export.",
        )
    with studio_cols[2]:
        info_card(
            "Inference Workbench",
            "Single-pair chemistry dashboard with solver decomposition, temperature scans, checkpoint inspection, and nearest-neighbor context.",
        )

    st.subheader("Applied use cases")
    app_cols = st.columns(3, gap="large")
    with app_cols[0]:
        info_card(
            "Applications",
            "Route-facing solvent screening for synthesis planning: evaluate hot-vs-cold crystallization windows per intermediate and rank explicit solvents instead of comparing single-point predictions in isolation.",
        )
    with app_cols[1]:
        info_card(
            "Developability",
            "Water and cosolvent screens that turn equilibrium solubility into a cautious preformulation readout: dose-pressure proxies, water margin, and honest limits on what the model can say about PK.",
        )
    with app_cols[2]:
        info_card(
            "Solvent Swap",
            "Crash-out and solvent-exchange stress testing for workup design, antisolvent ideas, and temperature-assisted isolation screens.",
        )

    families = split_family_options()
    if families:
        st.subheader("Dataset footprint")
        default_family = next(iter(families))
        family_name = st.selectbox("Processed split family", list(families), index=0)
        summary_df = split_summary_frame(families[family_name])
        cov_df = coverage_frame(families[family_name])
        left, right = st.columns([1.05, 1.0], gap="large")
        with left:
            render_dataframe(summary_df, use_container_width=True, hide_index=True)
        with right:
            fig = px.bar(
                cov_df,
                x="split",
                y="fraction",
                color="label",
                barmode="group",
                title=f"Label coverage in {family_name}",
                height=360,
            )
            fig.update_yaxes(tickformat=".0%")
            st.plotly_chart(style_plot(fig), use_container_width=True)

    image_candidates = available_images()
    if image_candidates:
        st.subheader("Artifact gallery")
        st.caption("Existing plots in checkpoints, figures, and results are surfaced here as a fast visual sanity check.")
        gallery_cols = st.columns(3, gap="large")
        for index, image_path in enumerate(image_candidates[:6]):
            with gallery_cols[index % 3]:
                st.image(str(image_path), caption=relative_label(image_path), use_container_width=True)


def render_data_page() -> None:
    families = split_family_options()
    page_header(
        "Data Explorer",
        "Inspect processed split families, label sparsity, temperature coverage, and representative chemistry before launching training or experiments.",
        eyebrow="Dataset",
        chips=[
            ("Split families", str(len(families))),
            ("Processed CSVs", str(filesystem_summary()["processed_splits"])),
            ("Preview", "real rows + RDKit structures"),
        ],
    )
    if not families:
        st.warning("No processed split families were found under notebooks/data/processed.")
        return

    family_name = st.selectbox("Split family", list(families), index=0)
    mapping = families[family_name]
    split_name = segmented_choice("Focus split", ["train", "val", "test"], key="data_split", default="train")
    df = cached_dataframe(str(mapping[split_name]))
    summary_df = split_summary_frame(mapping)
    cov_df = coverage_frame(mapping)

    top = st.columns(4)
    with top[0]:
        st.metric("Rows", f"{len(df):,}")
    with top[1]:
        st.metric("Solutes", f"{df['solute_smiles'].nunique():,}" if "solute_smiles" in df.columns else "—")
    with top[2]:
        st.metric("Solvents", f"{df['solvent_smiles'].nunique():,}" if "solvent_smiles" in df.columns else "—")
    with top[3]:
        st.metric("Supervised", f"{int(coerce_bool_series(df, 'has_solubility').sum()):,}")

    left, right = st.columns([1.05, 1.0], gap="large")
    with left:
        st.markdown("**Split summary**")
        render_dataframe(summary_df, use_container_width=True, hide_index=True)
        fig = px.bar(
            cov_df,
            x="split",
            y="fraction",
            color="label",
            barmode="group",
            title="Auxiliary label coverage",
            height=360,
        )
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(style_plot(fig), use_container_width=True)
    with right:
        if "temperature" in df.columns:
            fig = px.histogram(df, x="temperature", nbins=36, title=f"{split_name} temperature distribution", height=340)
            st.plotly_chart(style_plot(fig), use_container_width=True)
        if "ln_x2" in df.columns:
            sol_df = df.loc[coerce_bool_series(df, "has_solubility")].copy()
            if not sol_df.empty:
                fig = px.histogram(sol_df, x="ln_x2", nbins=36, title=f"{split_name} supervised ln x₂ distribution", height=340)
                st.plotly_chart(style_plot(fig), use_container_width=True)

    scatter_left, scatter_right = st.columns([1.0, 1.0], gap="large")
    with scatter_left:
        if {"temperature", "ln_x2", "source"} <= set(df.columns):
            sol_df = df.loc[coerce_bool_series(df, "has_solubility")].copy()
            if not sol_df.empty:
                sampled = sol_df.sample(min(len(sol_df), 2000), random_state=42)
                fig = px.scatter(
                    sampled,
                    x="temperature",
                    y="ln_x2",
                    color="source",
                    title=f"{split_name} supervised systems: temperature vs ln x₂",
                    height=380,
                    opacity=0.75,
                )
                st.plotly_chart(style_plot(fig), use_container_width=True)
    with scatter_right:
        preview_df = representative_system_frame(df)
        if not preview_df.empty:
            selected_label = st.selectbox("Representative system", preview_df["preview_label"].tolist(), key="data_preview_pair")
            preview_row = preview_df.loc[preview_df["preview_label"] == selected_label].iloc[0]
            mol_left, mol_right = st.columns(2, gap="large")
            with mol_left:
                render_molecule_panel(str(preview_row["solute_smiles"]), "Solute", str(preview_row.get("solute_name") or preview_row["solute_smiles"]))
            with mol_right:
                render_molecule_panel(str(preview_row["solvent_smiles"]), "Solvent", str(preview_row.get("solvent_name") or preview_row["solvent_smiles"]))
            preview_meta = pd.DataFrame(
                [
                    {"field": "temperature", "value": preview_row.get("temperature")},
                    {"field": "ln_x2", "value": preview_row.get("ln_x2")},
                    {"field": "source", "value": preview_row.get("source")},
                    {"field": "T_m", "value": preview_row.get("T_m")},
                    {"field": "dH_fus", "value": preview_row.get("dH_fus")},
                    {"field": "ln_gamma_inf", "value": preview_row.get("ln_gamma_inf")},
                ]
            )
            render_dataframe(preview_meta, use_container_width=True, hide_index=True)

    bottom_left, bottom_right = st.columns(2, gap="large")
    with bottom_left:
        top_solvents = top_counts_frame(df, "solvent_smiles", top_n=10, label="solvent")
        if not top_solvents.empty:
            fig = px.bar(top_solvents, x="count", y="solvent", orientation="h", title="Most frequent solvents", height=380)
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(style_plot(fig), use_container_width=True)
    with bottom_right:
        top_sources = top_counts_frame(df, "source", top_n=10, label="source")
        if not top_sources.empty:
            fig = px.bar(top_sources, x="source", y="count", color="count", title="Dominant sources", height=380)
            st.plotly_chart(style_plot(fig), use_container_width=True)

    with st.expander("Row preview", expanded=False):
        render_dataframe(df.head(200), use_container_width=True)


def render_training_page(python_command: str, probe: dict[str, Any]) -> None:
    configs = available_configs()
    default_train = PROCESSED_DIR / "train.csv"
    default_val = PROCESSED_DIR / "val.csv"
    default_test = PROCESSED_DIR / "test.csv"
    page_header(
        "Training Console",
        "Launch the maintained TGNN-Solv and DirectGNN training flows with explicit commands, config snapshots, curriculum context, and first-class access to Stage 0 warm starts, GPS configs, and descriptor-augmented TGNN variants.",
        eyebrow="Training",
        chips=[
            ("Configs", str(len(configs))),
            ("Devices", ", ".join(device_options_from_probe(probe))),
            ("Launch mode", "real repository scripts"),
        ],
    )
    mode = segmented_choice(
        "Training mode",
        ["TGNN-Solv", "DirectGNN", "Diagnostics"],
        key="training_mode",
        default="TGNN-Solv",
    )
    devices = device_options_from_probe(probe)

    if mode == "TGNN-Solv":
        with st.form("train_tgnn_form", border=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                config_path = render_path_select("Config", configs, CONFIG_DIR / "paper_config_tuned.yaml", "tgnn_config")
                train_path = st.text_input("Train CSV", value=str(default_train))
                val_path = st.text_input("Val CSV", value=str(default_val))
                seed = st.number_input("Seed", value=42, min_value=0, step=1)
            with c2:
                test_path = st.text_input("Test CSV", value=str(default_test))
                checkpoint_path = st.text_input("Checkpoint output", value=str(CHECKPOINTS_DIR / "lab_tgnn.pt"))
                device = st.selectbox("Device", devices, index=0)
                log_dir = st.text_input("Log directory", value=str(REPO_ROOT / "logs" / "tgnn_lab"))
            with c3:
                stage0_mode = st.selectbox(
                    "Stage 0 pretraining",
                    ["off", "run now", "load checkpoint"],
                    index=0,
                    help="`run now` calls `train.py --pretrain`; `load checkpoint` warms the encoder from a saved Stage 0 bundle.",
                )
                pretrain_data = st.text_input("Stage 0 source", value="zinc250k")
                pretrain_epochs = st.number_input("Stage 0 epochs", value=30, min_value=1, step=1)
                pretrain_batch_size = st.number_input("Stage 0 batch size", value=128, min_value=1, step=1)
                pretrain_lr = st.number_input("Stage 0 LR", value=3.0e-4, min_value=1.0e-6, step=1.0e-4, format="%.6f")
                pretrain_checkpoint = st.text_input("Stage 0 checkpoint", value=str(CHECKPOINTS_DIR / "pretrained_encoder.pt"))
                run_descriptor_probe = st.checkbox(
                    "Run descriptor probe after training",
                    value=True,
                    help="Launch the existing Ridge `g_sol -> descriptor` probe after the TGNN checkpoint is written.",
                )
                descriptor_probe_output_dir = st.text_input(
                    "Descriptor probe output",
                    value=str(RESULTS_DIR / "descriptor_probe"),
                )
                descriptor_probe_device = st.selectbox("Probe device", ["cpu", *devices], index=0)
            extra_args = st.text_area("Extra CLI args", value="--checkpoint-every 10")
            command = build_python_command(
                "scripts/training/train.py",
                "--config",
                config_path,
                "--train-data",
                train_path,
                "--val-data",
                val_path,
                "--test-data",
                test_path,
                "--seed",
                str(int(seed)),
                "--checkpoint",
                checkpoint_path,
                "--device",
                device,
                "--log-dir",
                log_dir,
                *parse_extra_args(extra_args),
                python_command_text=python_command,
            )
            if stage0_mode == "run now":
                command.extend(
                    [
                        "--pretrain",
                        "--pretrain-data",
                        pretrain_data,
                        "--pretrain-epochs",
                        str(int(pretrain_epochs)),
                        "--pretrain-batch-size",
                        str(int(pretrain_batch_size)),
                        "--pretrain-lr",
                        str(float(pretrain_lr)),
                    ]
                )
            elif stage0_mode == "load checkpoint":
                command.extend(["--pretrain-checkpoint", pretrain_checkpoint])
            if stage0_mode != "off":
                command.extend(["--pretrain-output", str(Path(checkpoint_path).with_name(f"{Path(checkpoint_path).stem}_pretrained_encoder.pt"))])
            if run_descriptor_probe:
                command.extend(
                    [
                        "--run-descriptor-probe",
                        "--descriptor-probe-output-dir",
                        descriptor_probe_output_dir,
                        "--descriptor-probe-device",
                        descriptor_probe_device,
                    ]
                )
            st.code(quote_command(command), language="bash")
            submitted = st.form_submit_button("Launch TGNN-Solv training", use_container_width=True)
            if submitted:
                launch_job("TGNN single run", "training", command, REPO_ROOT, [checkpoint_path, log_dir])
                st.success("Training job launched.")

        if Path(config_path).exists():
            phase_df, loss_df, meta = config_training_snapshot(config_path)
            feature_df = config_feature_rows(config_path)
            total_epochs = int(phase_df["epochs"].fillna(0).sum())
            cards = st.columns(5)
            with cards[0]:
                st.metric("Total epochs", str(total_epochs))
            with cards[1]:
                st.metric("Batch size", str(meta.get("batch_size", "—")))
            with cards[2]:
                encoder_type = meta.get("encoder_type", "mpnn")
                if encoder_type == "gps":
                    encoder_label = f"GPS / {meta.get('gps_positional_encoding', 'laplacian')}"
                else:
                    encoder_label = f"MPNN / {meta.get('hidden_dim', '—')}d"
                st.metric("Encoder", encoder_label)
            with cards[3]:
                st.metric("Pair-temp batching", "on" if meta.get("pair_temp_batching") else "off")
            with cards[4]:
                descriptor_flag = meta.get("use_descriptor_augmentation", False)
                st.metric("TGNN descriptors", "on" if descriptor_flag else "off")

            if stage0_mode != "off":
                st.markdown(
                    """
                    <div class="lab-callout">
                      Stage 0 is enabled for this launch. The command above is using the maintained `train.py` pretraining surface rather than a GUI-only wrapper, so the same behavior is reproducible from the CLI.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            left, right = st.columns([0.9, 1.1], gap="large")
            with left:
                meta_rows = [{"field": key, "value": value} for key, value in meta.items()]
                render_dataframe(pd.DataFrame(meta_rows), use_container_width=True, hide_index=True)
                render_dataframe(feature_df, use_container_width=True, hide_index=True)
            with right:
                fig = px.bar(phase_df, x="phase", y="epochs", color="phase", title="Curriculum phase budget", height=320)
                st.plotly_chart(style_plot(fig), use_container_width=True)
            if not loss_df.empty:
                loss_left, loss_right = st.columns([1.05, 0.95], gap="large")
                with loss_left:
                    fig = px.bar(loss_df.head(10), x="loss", y="weight", color="weight", title="Phase 2 loss weights", height=360)
                    fig.update_xaxes(tickangle=30)
                    st.plotly_chart(style_plot(fig), use_container_width=True)
                with loss_right:
                    timeline = go.Figure()
                    starts = [0, int(phase_df.iloc[0]["epochs"]), int(phase_df.iloc[0]["epochs"] + phase_df.iloc[1]["epochs"])]
                    colors = [theme_palette()["blue"], theme_palette()["green"], theme_palette()["orange"]]
                    for idx, row in phase_df.iterrows():
                        timeline.add_trace(
                            go.Bar(
                                x=[row["epochs"]],
                                y=["Curriculum"],
                                base=[starts[idx]],
                                orientation="h",
                                name=row["phase"],
                                marker_color=colors[idx],
                            )
                        )
                    timeline.update_layout(
                        barmode="stack",
                        title="Phase timeline",
                        height=360,
                        xaxis_title="Epoch",
                        yaxis_title="",
                        showlegend=True,
                    )
                    st.plotly_chart(style_plot(timeline), use_container_width=True)
            with st.expander("Raw config YAML", expanded=False):
                st.json(cached_yaml(config_path))

    elif mode == "DirectGNN":
        with st.form("train_directgnn_form", border=False):
            c1, c2 = st.columns(2)
            with c1:
                config_path = render_path_select(
                    "Config",
                    configs,
                    CONFIG_DIR / "paper_config_directgnn_tuned.yaml",
                    "direct_config",
                )
                train_path = st.text_input("Train CSV", value=str(default_train), key="direct_train")
                val_path = st.text_input("Val CSV", value=str(default_val), key="direct_val")
                seed = st.number_input("Seed", value=42, min_value=0, step=1, key="direct_seed")
            with c2:
                test_path = st.text_input("Test CSV", value=str(default_test), key="direct_test")
                checkpoint_path = st.text_input("Checkpoint output", value=str(CHECKPOINTS_DIR / "lab_directgnn.pt"))
                device = st.selectbox("Device", devices, index=0, key="direct_device")
                log_dir = st.text_input("Log directory", value=str(REPO_ROOT / "logs" / "directgnn_lab"), key="direct_log_dir")
            extra_args = st.text_area("Extra CLI args", value="", key="direct_extra")
            command = build_python_command(
                "scripts/training/train_directgnn.py",
                "--config",
                config_path,
                "--train-data",
                train_path,
                "--val-data",
                val_path,
                "--test-data",
                test_path,
                "--seed",
                str(int(seed)),
                "--checkpoint",
                checkpoint_path,
                "--device",
                device,
                "--log-dir",
                log_dir,
                *parse_extra_args(extra_args),
                python_command_text=python_command,
            )
            st.code(quote_command(command), language="bash")
            submitted = st.form_submit_button("Launch DirectGNN training", use_container_width=True)
            if submitted:
                launch_job("DirectGNN single run", "training", command, REPO_ROOT, [checkpoint_path, log_dir])
                st.success("DirectGNN training job launched.")

        if Path(config_path).exists():
            feature_df = config_feature_rows(config_path)
            render_dataframe(feature_df, use_container_width=True, hide_index=True)
            with st.expander("Raw config YAML", expanded=False):
                st.json(cached_yaml(config_path))

    else:
        with st.form("diagnose_form", border=False):
            mode = st.selectbox("Diagnostic mode", ["stats", "overfit"])
            sample_size = st.number_input("Sample size", value=1000, min_value=32, step=32)
            epochs = st.number_input("Epochs", value=200, min_value=1, step=10)
            extra_args = st.text_area("Extra CLI args", value="")
            command = build_python_command("scripts/training/diagnose_training.py", mode, python_command_text=python_command)
            if mode == "overfit":
                command += ["--sample-size", str(int(sample_size)), "--epochs", str(int(epochs))]
            command += parse_extra_args(extra_args)
            st.code(quote_command(command), language="bash")
            if st.form_submit_button("Launch diagnostic", use_container_width=True):
                launch_job(f"Training diagnostic: {mode}", "training", command, REPO_ROOT)
                st.success("Diagnostic job launched.")


def render_launcher_page(python_command: str, probe: dict[str, Any]) -> None:
    page_header(
        "Experiments & Scripts",
        "High-signal entry points are grouped here with maintained defaults, explicit outputs, and transparent commands.",
        eyebrow="Orchestration",
        chips=[
            ("Presets", "data · train · eval · reproduce"),
            ("Execution", "background jobs + logs"),
            ("Runtime", probe.get("python", python_command)),
        ],
    )
    outer_mode = segmented_choice(
        "Launcher area",
        ["Data prep", "Experiments", "Evaluation", "Paper & Figures", "Custom"],
        key="launcher_area",
        default="Data prep",
    )
    devices = device_options_from_probe(probe)

    if outer_mode == "Data prep":
        cards = st.columns(3)
        with cards[0]:
            info_card("Processed outputs", "Writes scaffold-aware train/val/test CSVs under the chosen processed directory.")
        with cards[1]:
            info_card("Split control", "Expose split mode and train/val/test ratios directly instead of hiding them in code.")
        with cards[2]:
            info_card("Safe mode", "Use `--skip-download` when raw files are already present and you want deterministic local rebuilds.")
        with st.form("prepare_data_form", border=False):
            output_dir = st.text_input("Output directory", value=str(PROCESSED_DIR))
            split_mode = st.selectbox("Split mode", ["solute_scaffold", "solute", "solvent"])
            seed = st.number_input("Seed", value=42, min_value=0, step=1)
            train_ratio = st.number_input("Train ratio", value=0.8, min_value=0.01, max_value=0.98, step=0.01)
            val_ratio = st.number_input("Val ratio", value=0.1, min_value=0.01, max_value=0.98, step=0.01)
            test_ratio = st.number_input("Test ratio", value=0.1, min_value=0.01, max_value=0.98, step=0.01)
            extra = st.text_area("Extra CLI args", value="--skip-download")
            command = build_python_command(
                "scripts/data/prepare_data.py",
                "--output-dir",
                output_dir,
                "--split-mode",
                split_mode,
                "--seed",
                str(int(seed)),
                "--train-ratio",
                str(float(train_ratio)),
                "--val-ratio",
                str(float(val_ratio)),
                "--test-ratio",
                str(float(test_ratio)),
                *parse_extra_args(extra),
                python_command_text=python_command,
            )
            st.code(quote_command(command), language="bash")
            if st.form_submit_button("Prepare data", use_container_width=True):
                launch_job("Prepare data", "data", command, REPO_ROOT, [output_dir])
                st.success("Data preparation launched.")

    elif outer_mode == "Experiments":
        exp_tab = segmented_choice(
            "Experiment preset",
            [
                "Run seeds",
                "Medium budget comparison",
                "Full budget diagnostic study",
                "Split comparisons",
                "External baselines",
                "Custom benchmark",
                "Optuna",
            ],
            key="experiment_preset",
            default="Run seeds",
        )
        if exp_tab == "Run seeds":
            with st.form("run_seeds_form", border=False):
                config_path = render_path_select("Config", available_configs(), CONFIG_DIR / "paper_config_tuned.yaml", "seeds_config")
                output_path = st.text_input("Output JSON", value=str(RESULTS_DIR / "multi_seed_results.json"))
                checkpoint_dir = st.text_input("Checkpoint dir", value=str(CHECKPOINTS_DIR / "seeds"))
                n_seeds = st.number_input("Seeds", value=5, min_value=1, step=1)
                base_seed = st.number_input("Base seed", value=42, min_value=0, step=1)
                device = st.selectbox("Device", devices, index=0, key="seeds_device")
                command = build_python_command(
                    "scripts/experiments/run_seeds.py",
                    "--config",
                    config_path,
                    "--train-data",
                    str(PROCESSED_DIR / "train.csv"),
                    "--val-data",
                    str(PROCESSED_DIR / "val.csv"),
                    "--test-data",
                    str(PROCESSED_DIR / "test.csv"),
                    "--n-seeds",
                    str(int(n_seeds)),
                    "--base-seed",
                    str(int(base_seed)),
                    "--output",
                    output_path,
                    "--checkpoint-dir",
                    checkpoint_dir,
                    "--device",
                    device,
                    python_command_text=python_command,
                )
                st.code(quote_command(command), language="bash")
                if st.form_submit_button("Launch multi-seed experiment", use_container_width=True):
                    launch_job("Multi-seed TGNN", "experiment", command, REPO_ROOT, [output_path, checkpoint_dir])
                    st.success("Multi-seed experiment launched.")
        elif exp_tab == "Medium budget comparison":
            with st.form("medium_budget_form", border=False):
                output_dir = st.text_input("Output dir", value=str(RESULTS_DIR / "medium_budget"))
                seed = st.number_input("Seed", value=42, min_value=0, step=1, key="medium_seed")
                device = st.selectbox("Device", devices, index=0, key="medium_device")
                extra = st.text_area("Extra CLI args", value="")
                command = build_python_command(
                    "scripts/experiments/run_medium_budget_comparison.py",
                    "--train-data",
                    str(PROCESSED_DIR / "train.csv"),
                    "--val-data",
                    str(PROCESSED_DIR / "val.csv"),
                    "--test-data",
                    str(PROCESSED_DIR / "test.csv"),
                    "--output-dir",
                    output_dir,
                    "--seed",
                    str(int(seed)),
                    "--device",
                    device,
                    *parse_extra_args(extra),
                    python_command_text=python_command,
                )
                st.code(quote_command(command), language="bash")
                if st.form_submit_button("Launch medium-budget comparison", use_container_width=True):
                    launch_job("Medium budget comparison", "experiment", command, REPO_ROOT, [output_dir])
                    st.success("Medium-budget comparison launched.")
        elif exp_tab == "Full budget diagnostic study":
            with st.form("full_budget_form", border=False):
                config_path = render_path_select("Config", available_configs(), CONFIG_DIR / "paper_config_tuned.yaml", "full_config")
                output_dir = st.text_input("Output dir", value=str(RESULTS_DIR / "full_budget_experiment"))
                seeds = st.text_input("Seeds", value="42")
                device = st.selectbox("Device", devices, index=0, key="full_device")
                extra = st.text_area("Extra CLI args", value="")
                command = build_python_command(
                    "scripts/experiments/run_full_budget_experiment.py",
                    "--config",
                    config_path,
                    "--train-data",
                    str(PROCESSED_DIR / "train.csv"),
                    "--val-data",
                    str(PROCESSED_DIR / "val.csv"),
                    "--test-data",
                    str(PROCESSED_DIR / "test.csv"),
                    "--seeds",
                    seeds,
                    "--output-dir",
                    output_dir,
                    "--device",
                    device,
                    *parse_extra_args(extra),
                    python_command_text=python_command,
                )
                st.code(quote_command(command), language="bash")
                if st.form_submit_button("Launch full-budget study", use_container_width=True):
                    launch_job("Full budget diagnostic study", "experiment", command, REPO_ROOT, [output_dir])
                    st.success("Full-budget study launched.")
        elif exp_tab == "Split comparisons":
            with st.form("split_comp_form", border=False):
                output_path = st.text_input("Output JSON", value=str(RESULTS_DIR / "split_comparisons.json"))
                results_dir = st.text_input("Results dir", value=str(RESULTS_DIR / "split_comparisons"))
                checkpoint_root = st.text_input("Checkpoint root", value=str(CHECKPOINTS_DIR / "split_comparisons"))
                splits = st.text_input("Splits", value="solute_scaffold,solute,solvent")
                models = st.text_input("Models", value="tgnn_solv,direct_gnn,rf_baseline")
                n_seeds = st.number_input("Seeds per split", value=3, min_value=1, step=1)
                base_seed = st.number_input("Base seed", value=42, min_value=0, step=1, key="split_base_seed")
                device = st.selectbox("Device", devices, index=0, key="split_device")
                config_path = render_path_select("Config", available_configs(), CONFIG_DIR / "paper_config_tuned.yaml", "split_config")
                extra = st.text_area("Extra CLI args", value="")
                command = build_python_command(
                    "scripts/experiments/run_split_comparisons.py",
                    "--processed-dir",
                    str(PROCESSED_DIR),
                    "--splits",
                    splits,
                    "--models",
                    models,
                    "--config",
                    config_path,
                    "--n-seeds",
                    str(int(n_seeds)),
                    "--base-seed",
                    str(int(base_seed)),
                    "--device",
                    device,
                    "--results-dir",
                    results_dir,
                    "--output",
                    output_path,
                    "--checkpoint-root",
                    checkpoint_root,
                    *parse_extra_args(extra),
                    python_command_text=python_command,
                )
                st.code(quote_command(command), language="bash")
                if st.form_submit_button("Launch split comparison", use_container_width=True):
                    launch_job("Split comparisons", "experiment", command, REPO_ROOT, [output_path, results_dir, checkpoint_root])
                    st.success("Split-comparison experiment launched.")
        elif exp_tab == "External baselines":
            cards = st.columns(3)
            with cards[0]:
                info_card("FastSolv", "Run either the pretrained ensemble, scratch training on repo splits, or both in one pass.")
            with cards[1]:
                info_card("SolProp", "Run zero-shot, calibrated, or native-retrained SolProp architectures under the same processed split.")
            with cards[2]:
                info_card("Artifacts", "Writes canonical report/predictions/summary bundles so the Results workspace can compare them immediately.")
            st.caption("If SolProp is not installed in the selected interpreter, extract the repo-local runtime once with `python scripts/external/install_solprop_runtime.py` and pass that folder via `SolProp runtime dir`.")
            st.caption("Recommended article-comparison mode: use `SolProp mode = native`. The maintained wrapper also still exposes stable room-temperature zero-shot and train-split calibration baselines. The upstream temperature-dependent SolProp branch remains available, but it is treated as experimental and may fall back row-wise.")
            with st.form("external_baselines_form", border=False):
                out_dir = st.text_input("Output dir", value=str(RESULTS_DIR / "external_baselines"))
                train_data = st.text_input("Train CSV", value=str(PROCESSED_DIR / "train.csv"))
                val_data = st.text_input("Val CSV", value=str(PROCESSED_DIR / "val.csv"))
                test_data = st.text_input("Test CSV", value=str(PROCESSED_DIR / "test.csv"))
                interp_left, interp_right = st.columns(2)
                with interp_left:
                    fastsolv_python = st.text_input("FastSolv Python (optional)", value="")
                with interp_right:
                    solprop_python = st.text_input("SolProp Python (optional)", value="")
                solprop_runtime_dir = st.text_input("SolProp runtime dir (optional)", value="")
                split_mode = st.selectbox("Split mode", ["solute_scaffold", "solute", "solvent", "custom"], index=0)
                col_a, col_b = st.columns(2)
                with col_a:
                    fastsolv_mode = st.selectbox("FastSolv mode", ["both", "pretrained", "scratch", "skip"], index=0)
                    fastsolv_batch = st.number_input("FastSolv batch size", value=256, min_value=1, step=32)
                    fastsolv_epochs = st.number_input("FastSolv scratch epochs", value=40, min_value=1, step=5)
                    fastsolv_patience = st.number_input("FastSolv patience", value=10, min_value=1, step=1)
                    fastsolv_nproc = st.number_input("FastSolv descriptor nproc", value=1, min_value=1, step=1)
                with col_b:
                    solprop_mode = st.selectbox("SolProp mode", ["native", "both", "all", "zero_shot", "calibrated", "skip"], index=0)
                    solprop_batch = st.number_input("SolProp batch size", value=256, min_value=1, step=32)
                    solprop_temperature_dependent = st.checkbox("Temperature-dependent SolProp", value=False)
                    solprop_include_temperature = st.checkbox("Use temperature in SolProp calibrator", value=True)
                    solprop_reduced_number = st.checkbox("Reduced-number SolProp ensemble", value=False)
                native_left, native_right = st.columns(2)
                with native_left:
                    solprop_native_epochs = st.number_input("SolProp native epochs", value=40, min_value=1, step=5)
                    solprop_native_patience = st.number_input("SolProp native patience", value=10, min_value=1, step=1)
                with native_right:
                    solprop_native_models = st.number_input("SolProp native ensemble", value=5, min_value=1, step=1)
                    solprop_native_device = st.selectbox("SolProp native device", ["auto", "cpu", "cuda"], index=0)
                continue_on_error = st.checkbox("Continue if one baseline fails", value=False)
                extra = st.text_area("Extra CLI args", value="")
                command = build_python_command(
                    "scripts/experiments/run_external_baseline_benchmark.py",
                    "--train-data",
                    train_data,
                    "--val-data",
                    val_data,
                    "--test-data",
                    test_data,
                    "--out-dir",
                    out_dir,
                    "--split-mode",
                    split_mode,
                    "--fastsolv-mode",
                    fastsolv_mode,
                    "--fastsolv-batch-size",
                    str(int(fastsolv_batch)),
                    "--fastsolv-epochs",
                    str(int(fastsolv_epochs)),
                    "--fastsolv-patience",
                    str(int(fastsolv_patience)),
                    "--fastsolv-descriptor-nproc",
                    str(int(fastsolv_nproc)),
                    "--solprop-mode",
                    solprop_mode,
                    "--solprop-batch-size",
                    str(int(solprop_batch)),
                    "--solprop-native-epochs",
                    str(int(solprop_native_epochs)),
                    "--solprop-native-patience",
                    str(int(solprop_native_patience)),
                    "--solprop-native-num-models",
                    str(int(solprop_native_models)),
                    "--solprop-native-device",
                    solprop_native_device,
                    *parse_extra_args(extra),
                    python_command_text=python_command,
                )
                if solprop_temperature_dependent:
                    command.append("--solprop-temperature-dependent")
                if solprop_include_temperature:
                    command.append("--solprop-include-temperature")
                if solprop_reduced_number:
                    command.append("--solprop-reduced-number")
                if fastsolv_python.strip():
                    command += ["--fastsolv-python", fastsolv_python.strip()]
                if solprop_python.strip():
                    command += ["--solprop-python", solprop_python.strip()]
                if solprop_runtime_dir.strip():
                    command += ["--solprop-runtime-dir", solprop_runtime_dir.strip()]
                if continue_on_error:
                    command.append("--continue-on-error")
                st.code(quote_command(command), language="bash")
                if st.form_submit_button("Launch external baseline benchmark", use_container_width=True):
                    launch_job("External baselines benchmark", "experiment", command, REPO_ROOT, [out_dir])
                    st.success("External baseline benchmark launched.")
        elif exp_tab == "Custom benchmark":
            cards = st.columns(3)
            with cards[0]:
                info_card("Bring your own model", "Benchmark either a plain predictions CSV or a repo-native Python adapter against the canonical TGNN-Solv bundle contract.")
            with cards[1]:
                info_card("Command mode", "Optionally let the lab run a custom command that writes predictions before benchmarking them.")
            with cards[2]:
                info_card("Visualization", "Outputs the same summary/report bundle as maintained models, including run manifests and benchmark cards, so all existing tables and plots keep working.")
            st.caption("Custom benchmark outputs use the same canonical artifact format as maintained models, so they automatically show up in `Results & Plots`, the artifact registry, compare views, and the new release-manifest workflow.")
            with st.form("custom_benchmark_form", border=False):
                model_name = st.text_input("Model name", value="custom_model")
                test_data = st.text_input("Test CSV", value=str(PROCESSED_DIR / "test.csv"), key="custom_benchmark_test")
                out_dir = st.text_input("Output dir", value=str(RESULTS_DIR / "custom_benchmarks" / "custom_model"))
                source_mode = st.selectbox(
                    "Prediction source",
                    ["Existing predictions CSV", "Command generates predictions", "Python adapter class"],
                )
                predictions_csv = st.text_input(
                    "Predictions CSV",
                    value=str(RESULTS_DIR / "custom_benchmarks" / "custom_model" / "predictions_input.csv"),
                    help="If `row_index` is present it will be used as the primary merge key. Otherwise the benchmark falls back to the pair identity.",
                )
                command_template = ""
                generated_predictions = predictions_csv
                adapter_ref = ""
                train_data = str(PROCESSED_DIR / "train.csv")
                val_data = str(PROCESSED_DIR / "val.csv")
                init_kwargs_json = ""
                fit_kwargs_json = ""
                predict_kwargs_json = ""
                if source_mode == "Command generates predictions":
                    generated_predictions = st.text_input(
                        "Generated predictions path",
                        value=str(RESULTS_DIR / "custom_benchmarks" / "custom_model" / "generated_predictions.csv"),
                    )
                    command_template = st.text_area(
                        "Command template",
                        value="python your_model.py --input {test_data} --output {predictions_output}",
                        height=120,
                        help="`{test_data}` and `{predictions_output}` will be substituted before execution.",
                    )
                elif source_mode == "Python adapter class":
                    adapter_ref = st.text_input(
                        "Adapter reference",
                        value="your_package.your_adapter:YourAdapter",
                        help="Implement `describe()`, `fit(...)`, and `predict_frame(...)` as documented in `tgnn_solv.benchmark_adapters`.",
                    )
                    adapter_cols = st.columns(2)
                    with adapter_cols[0]:
                        train_data = st.text_input("Train CSV", value=str(PROCESSED_DIR / "train.csv"))
                        init_kwargs_json = st.text_area("Init kwargs JSON", value="{}", height=100)
                    with adapter_cols[1]:
                        val_data = st.text_input("Val CSV", value=str(PROCESSED_DIR / "val.csv"))
                        fit_kwargs_json = st.text_area("Fit kwargs JSON", value="{}", height=100)
                    predict_kwargs_json = st.text_area("Predict kwargs JSON", value="{}", height=100)
                cols_left, cols_right = st.columns(2)
                with cols_left:
                    pred_lnx2_col = st.text_input("Predicted ln(x2) column", value="ln_x2_pred")
                    uncertainty_col = st.text_input("Uncertainty column (optional)", value="")
                with cols_right:
                    pred_logs_col = st.text_input("Predicted logS column (optional)", value="")
                    merge_on = st.selectbox("Merge mode", ["auto", "row_index", "pair"], index=0)
                metadata_json = st.text_input("Metadata JSON (optional)", value="")
                command = build_python_command(
                    "scripts/evaluation/benchmark_adapter_model.py" if source_mode == "Python adapter class" else "scripts/evaluation/benchmark_custom_model.py",
                    "--model-name",
                    model_name,
                    "--out-dir",
                    out_dir,
                    python_command_text=python_command,
                )
                if source_mode == "Python adapter class":
                    command += [
                        "--adapter",
                        adapter_ref,
                        "--test-data",
                        test_data,
                        "--train-data",
                        train_data,
                        "--val-data",
                        val_data,
                    ]
                else:
                    command += [
                        "--test-data",
                        test_data,
                        "--merge-on",
                        merge_on,
                    ]
                if source_mode == "Existing predictions CSV":
                    command += ["--predictions-csv", predictions_csv]
                elif source_mode == "Command generates predictions":
                    command += [
                        "--command",
                        command_template,
                        "--generated-predictions",
                        generated_predictions,
                    ]
                if source_mode == "Python adapter class":
                    if pred_lnx2_col.strip():
                        command += ["--pred-lnx2-col", pred_lnx2_col.strip()]
                    if pred_logs_col.strip():
                        command += ["--pred-logs-col", pred_logs_col.strip()]
                    if uncertainty_col.strip():
                        command += ["--uncertainty-col", uncertainty_col.strip()]
                    if init_kwargs_json.strip():
                        command += ["--init-kwargs-json", init_kwargs_json.strip()]
                    if fit_kwargs_json.strip():
                        command += ["--fit-kwargs-json", fit_kwargs_json.strip()]
                    if predict_kwargs_json.strip():
                        command += ["--predict-kwargs-json", predict_kwargs_json.strip()]
                else:
                    if pred_lnx2_col.strip():
                        command += ["--pred-lnx2-col", pred_lnx2_col.strip()]
                    if pred_logs_col.strip():
                        command += ["--pred-logs-col", pred_logs_col.strip()]
                    if uncertainty_col.strip():
                        command += ["--uncertainty-col", uncertainty_col.strip()]
                    if metadata_json.strip():
                        command += ["--metadata-json", metadata_json.strip()]
                st.code(quote_command(command), language="bash")
                submit_label = "Benchmark custom adapter" if source_mode == "Python adapter class" else "Benchmark custom model"
                if st.form_submit_button(submit_label, use_container_width=True):
                    launch_job("Custom model benchmark", "evaluation", command, REPO_ROOT, [out_dir])
                    st.success("Custom benchmark launched.")
        else:
            with st.form("optuna_form", border=False):
                models = st.text_input("Models", value="tgnn_solv,direct_gnn")
                n_trials = st.number_input("Trials", value=20, min_value=1, step=1)
                out_dir = st.text_input("Output dir", value=str(RESULTS_DIR / "optuna" / "lab"))
                device = st.selectbox("Device", devices, index=0, key="optuna_device")
                extra = st.text_area("Extra CLI args", value="")
                command = build_python_command(
                    "scripts/experiments/run_optuna.py",
                    "--train-csv",
                    str(PROCESSED_DIR / "train.csv"),
                    "--val-csv",
                    str(PROCESSED_DIR / "val.csv"),
                    "--test-csv",
                    str(PROCESSED_DIR / "test.csv"),
                    "--models",
                    models,
                    "--n-trials",
                    str(int(n_trials)),
                    "--device",
                    device,
                    "--out-dir",
                    out_dir,
                    *parse_extra_args(extra),
                    python_command_text=python_command,
                )
                st.code(quote_command(command), language="bash")
                if st.form_submit_button("Launch Optuna", use_container_width=True):
                    launch_job("Optuna search", "experiment", command, REPO_ROOT, [out_dir])
                    st.success("Optuna run launched.")

    elif outer_mode == "Evaluation":
        eval_mode = segmented_choice(
            "Evaluation task",
            ["Evaluate complete", "Validate physics"],
            key="evaluation_mode",
            default="Evaluate complete",
        )
        if eval_mode == "Evaluate complete":
            with st.form("eval_complete_form", border=False):
                checkpoint_path = render_path_select(
                    "Checkpoint",
                    available_checkpoints(),
                    CHECKPOINTS_DIR / "tgnn_solv_trained.pt",
                    "eval_checkpoint",
                )
                output_path = st.text_input("Output JSON", value=str(RESULTS_DIR / "lab_evaluation.json"))
                test_path = st.text_input("Test CSV", value=str(PROCESSED_DIR / "test.csv"))
                n_samples = st.number_input("Optional sample cap", value=0, min_value=0, step=100)
                command = build_python_command(
                    "scripts/evaluation/evaluate_complete.py",
                    "--test-data",
                    test_path,
                    "--tgnn-checkpoint",
                    checkpoint_path,
                    "--output",
                    output_path,
                    "--verbose",
                    python_command_text=python_command,
                )
                if int(n_samples) > 0:
                    command += ["--n-samples", str(int(n_samples))]
                st.code(quote_command(command), language="bash")
                if st.form_submit_button("Run evaluation", use_container_width=True):
                    launch_job("Evaluate complete", "evaluation", command, REPO_ROOT, [output_path])
                    st.success("Evaluation launched.")
        else:
            with st.form("validate_physics_form", border=False):
                checkpoint_path = render_path_select(
                    "Checkpoint",
                    available_checkpoints(),
                    CHECKPOINTS_DIR / "tgnn_solv_trained.pt",
                    "physics_checkpoint",
                )
                output_path = st.text_input("Output JSON", value=str(RESULTS_DIR / "physics_validation.json"))
                test_path = st.text_input("Test CSV", value=str(PROCESSED_DIR / "test.csv"), key="physics_test")
                device = st.selectbox("Device", devices, index=0, key="physics_device")
                n_pairs = st.number_input("van't Hoff pairs", value=200, min_value=1, step=10)
                n_points = st.number_input("Temperature points", value=50, min_value=5, step=5)
                command = build_python_command(
                    "scripts/evaluation/validate_physics.py",
                    "--checkpoint",
                    checkpoint_path,
                    "--test-data",
                    test_path,
                    "--output",
                    output_path,
                    "--n-vanthoff-pairs",
                    str(int(n_pairs)),
                    "--n-temp-points",
                    str(int(n_points)),
                    "--device",
                    device,
                    python_command_text=python_command,
                )
                st.code(quote_command(command), language="bash")
                if st.form_submit_button("Validate physics", use_container_width=True):
                    launch_job("Validate physics", "evaluation", command, REPO_ROOT, [output_path])
                    st.success("Physics validation launched.")

    elif outer_mode == "Paper & Figures":
        with st.form("paper_form", border=False):
            mode = st.selectbox(
                "Workflow",
                [
                    "Article reproduction",
                    "Generate paper figures",
                    "Generate supplementary",
                    "Legacy reproduce.sh",
                ],
            )
            repro_profile = st.selectbox("Reproduction profile", ["core", "article", "full"], index=1)
            repro_device = st.selectbox("Reproduction device", devices, index=0, key="paper_repro_device")
            extra = st.text_area("Extra CLI args", value="")
            if mode == "Article reproduction":
                command = build_python_command(
                    "scripts/experiments/reproduce_paper.py",
                    "--profile",
                    repro_profile,
                    "--device",
                    repro_device,
                    *parse_extra_args(extra),
                    python_command_text=python_command,
                )
                outputs = [str(RESULTS_DIR / "reproduction"), str(FIGURES_DIR), str(TABLES_DIR)]
            elif mode == "Legacy reproduce.sh":
                command = ["bash", "reproduce.sh", *parse_extra_args(extra)]
                outputs = [str(RESULTS_DIR), str(FIGURES_DIR), str(TABLES_DIR)]
            elif mode == "Generate paper figures":
                command = build_python_command(
                    "scripts/experiments/generate_paper_figures.py",
                    "--results-dir",
                    str(RESULTS_DIR),
                    "--output-dir",
                    str(FIGURES_DIR),
                    *parse_extra_args(extra),
                    python_command_text=python_command,
                )
                outputs = [str(FIGURES_DIR)]
            else:
                command = build_python_command(
                    "scripts/experiments/generate_supplementary.py",
                    "--results-dir",
                    str(RESULTS_DIR),
                    "--output-dir",
                    str(TABLES_DIR),
                    *parse_extra_args(extra),
                    python_command_text=python_command,
                )
                outputs = [str(TABLES_DIR)]
            st.code(quote_command(command), language="bash")
            if st.form_submit_button("Launch workflow", use_container_width=True):
                launch_job(mode, "paper", command, REPO_ROOT, outputs)
                st.success("Workflow launched.")

    else:
        with st.form("custom_cmd_form", border=False):
            cwd = st.text_input("Working directory", value=str(REPO_ROOT))
            command_text = st.text_area(
                "Shell command",
                value="python scripts/experiments/run_medium_budget_comparison.py --help",
                height=120,
            )
            submitted = st.form_submit_button("Launch custom command", use_container_width=True)
            if submitted:
                command = ["bash", "-lc", command_text]
                st.code(quote_command(command), language="bash")
                launch_job("Custom command", "custom", command, Path(cwd))
                st.success("Custom command launched.")


def render_hpo_page(python_command: str, probe: dict[str, Any]) -> None:
    trial_paths, best_paths = discover_optuna_artifacts()
    best_df = optuna_best_frame(best_paths)
    page_header(
        "HPO Lab",
        "Dedicated Optuna workspace for tuning TGNN-Solv and DirectGNN, reviewing saved studies, and turning trial artifacts into readable launch and comparison surfaces instead of raw CSVs.",
        eyebrow="HPO",
        chips=[
            ("Studies", str(len(trial_paths))),
            ("Best configs", str(len(best_paths))),
            ("Artifact root", relative_label(OPTUNA_DIR)),
            ("Runtime", probe.get("python", python_command)),
        ],
    )

    mode = segmented_choice(
        "HPO workspace",
        ["Launch search", "Study dashboard"],
        key="hpo_workspace",
        default="Launch search",
    )
    devices = device_options_from_probe(probe)

    if mode == "Launch search":
        cards = st.columns(3)
        with cards[0]:
            info_card("Model set", "Tune TGNN-Solv, DirectGNN, or both from the maintained Optuna wrapper.")
        with cards[1]:
            info_card("Search scope", "Fix batch size or disable architecture tuning when you only want optimizer/loss sweeps.")
        with cards[2]:
            info_card("Artifacts", "Every study can emit both `*_best.json` and `*_trials.csv` for later dashboard review.")

        with st.form("hpo_launch_form", border=False):
            config_path = render_path_select("Base config", available_configs(), CONFIG_DIR / "paper_config_tuned.yaml", "hpo_config")
            row1 = st.columns(4)
            with row1[0]:
                models = st.text_input("Models", value="tgnn_solv,direct_gnn")
            with row1[1]:
                n_trials = st.number_input("Trials", value=24, min_value=1, step=1)
            with row1[2]:
                timeout = st.number_input("Timeout (s, 0=off)", value=0, min_value=0, step=300)
            with row1[3]:
                device = st.selectbox("Device", devices, index=0, key="hpo_device")

            row2 = st.columns(4)
            with row2[0]:
                out_dir = st.text_input("Output dir", value=str(OPTUNA_DIR / "lab"))
            with row2[1]:
                study_name = st.text_input("Study name prefix", value="lab")
            with row2[2]:
                fixed_batch = st.number_input("Fixed batch size (0=tune)", value=0, min_value=0, step=16)
            with row2[3]:
                seed = st.number_input("Seed", value=42, min_value=0, step=1)

            row3 = st.columns(4)
            with row3[0]:
                no_tune_arch = st.checkbox("Disable architecture tuning", value=False)
            with row3[1]:
                baseline_epochs = st.number_input("Baseline epochs", value=200, min_value=20, step=10)
            with row3[2]:
                baseline_patience = st.number_input("Baseline patience", value=20, min_value=5, step=5)
            with row3[3]:
                num_workers = st.number_input("Workers", value=0, min_value=0, step=1)

            storage = st.text_input("Optuna storage URL (optional)", value="")
            extra = st.text_area("Extra CLI args", value="")
            command = build_python_command(
                "scripts/experiments/run_optuna.py",
                "--config",
                config_path,
                "--train-csv",
                str(PROCESSED_DIR / "train.csv"),
                "--val-csv",
                str(PROCESSED_DIR / "val.csv"),
                "--test-csv",
                str(PROCESSED_DIR / "test.csv"),
                "--models",
                models,
                "--n-trials",
                str(int(n_trials)),
                "--seed",
                str(int(seed)),
                "--device",
                device,
                "--num-workers",
                str(int(num_workers)),
                "--baseline-epochs",
                str(int(baseline_epochs)),
                "--baseline-patience",
                str(int(baseline_patience)),
                "--out-dir",
                out_dir,
                *(["--timeout", str(int(timeout))] if int(timeout) > 0 else []),
                *(["--study-name", study_name.strip()] if study_name.strip() else []),
                *(["--storage", storage.strip()] if storage.strip() else []),
                *(["--batch-size", str(int(fixed_batch))] if int(fixed_batch) > 0 else []),
                *(["--no-tune-arch"] if no_tune_arch else []),
                *parse_extra_args(extra),
                python_command_text=python_command,
            )
            st.code(quote_command(command), language="bash")
            if st.form_submit_button("Launch HPO study", use_container_width=True):
                launch_job("Optuna HPO", "experiment", command, REPO_ROOT, [out_dir])
                st.success("HPO study launched.")
    else:
        if best_df.empty and not trial_paths:
            st.info("No Optuna artifacts found yet. Launch a study first or point the launcher at an existing output directory.")
            return

        top_left, top_right = st.columns([0.95, 1.05], gap="large")
        with top_left:
            if not best_df.empty:
                st.markdown("### Best-study leaderboard")
                render_dataframe(best_df, use_container_width=True, hide_index=True)
            else:
                st.info("No `*_best.json` summaries found yet.")
        with top_right:
            if not best_df.empty:
                leader = px.bar(
                    best_df.head(10),
                    x="model",
                    y="best_value",
                    color="model",
                    title="Best validation objective by model",
                    height=420,
                )
                st.plotly_chart(style_plot(leader), use_container_width=True)

        if not trial_paths:
            st.info("No `*_trials.csv` files found for dashboard drilldown.")
            return
        labels = [relative_label(path) for path in trial_paths]
        selected_trials = st.selectbox("Study trials CSV", labels, index=0)
        trials_path = trial_paths[labels.index(selected_trials)]
        trials_df = cached_dataframe(str(trials_path))
        if trials_df.empty:
            st.warning("Selected trials CSV is empty.")
            return

        if "state" in trials_df.columns:
            filtered_trials = trials_df[trials_df["state"].astype(str).str.contains("COMPLETE", case=False, na=False)].copy()
            if filtered_trials.empty:
                filtered_trials = trials_df.copy()
        else:
            filtered_trials = trials_df.copy()
        filtered_trials = filtered_trials.sort_values("number") if "number" in filtered_trials.columns else filtered_trials
        objective_col = "value" if "value" in filtered_trials.columns else filtered_trials.columns[-1]
        best_row = filtered_trials.loc[filtered_trials[objective_col].astype(float).idxmin()] if objective_col in filtered_trials.columns else filtered_trials.iloc[0]
        param_columns = optuna_parameter_columns(filtered_trials)

        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("Trials", str(len(filtered_trials)))
        with metric_cols[1]:
            st.metric("Best objective", f"{float(best_row[objective_col]):.4f}")
        with metric_cols[2]:
            st.metric("Parameters tracked", str(len(param_columns)))
        with metric_cols[3]:
            st.metric("Study file", Path(trials_path).name)

        chart_left, chart_right = st.columns([1.0, 1.0], gap="large")
        with chart_left:
            trial_curve = px.line(
                filtered_trials,
                x="number" if "number" in filtered_trials.columns else filtered_trials.index,
                y=objective_col,
                markers=True,
                title="Objective across trials",
                height=460,
            )
            st.plotly_chart(style_plot(trial_curve), use_container_width=True)
        with chart_right:
            if param_columns:
                parameter = st.selectbox("Parameter view", param_columns, key="hpo_param_view")
                param_fig = px.scatter(
                    filtered_trials,
                    x=parameter,
                    y=objective_col,
                    color="state" if "state" in filtered_trials.columns else None,
                    title=f"{parameter} vs objective",
                    height=460,
                )
                st.plotly_chart(style_plot(param_fig), use_container_width=True)
            else:
                st.info("No `params_*` columns found in this trials CSV.")

        detail_left, detail_right = st.columns([0.95, 1.05], gap="large")
        with detail_left:
            st.markdown("### Best trial parameters")
            best_params = {
                str(column).replace("params_", ""): best_row[column]
                for column in param_columns
                if pd.notna(best_row[column])
            }
            if best_params:
                render_dataframe(
                    pd.DataFrame([{"parameter": key, "value": value} for key, value in best_params.items()]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No parameter columns were present for the best row.")
        with detail_right:
            st.markdown("### Raw trials table")
            render_dataframe(filtered_trials.head(200), use_container_width=True, hide_index=True)


def render_pipeline_studio(python_command: str) -> None:
    catalog = pipeline_preset_catalog()
    preset_labels = list(catalog)
    if "pipeline_studio_nodes" not in st.session_state:
        default_label = preset_labels[0]
        st.session_state["pipeline_studio_nodes"] = json_safe_copy(catalog[default_label]["nodes"])
        st.session_state["pipeline_studio_loaded_preset"] = default_label
        st.session_state["pipeline_studio_selected"] = st.session_state["pipeline_studio_nodes"][0]["id"]

    loaded_label = st.session_state.get("pipeline_studio_loaded_preset", preset_labels[0])
    if loaded_label not in catalog:
        loaded_label = preset_labels[0]
        st.session_state["pipeline_studio_loaded_preset"] = loaded_label
    nodes: list[dict[str, Any]] = st.session_state["pipeline_studio_nodes"]
    selected_id = st.session_state.get("pipeline_studio_selected", nodes[0]["id"] if nodes else "")
    selected_node = next((node for node in nodes if node["id"] == selected_id), nodes[0] if nodes else None)
    if selected_node is not None:
        st.session_state["pipeline_canvas_focus"] = selected_node["id"]

    page_header(
        "Pipeline Studio",
        "Visual DAG editor for the real TGNN-Solv workflow: maintain a dependency graph, persist your own repo-local presets, export launch scripts, and run either a single node or the whole active plan.",
        eyebrow="Pipeline",
        chips=[
            ("Loaded preset", loaded_label),
            ("Nodes", str(len(nodes))),
            ("Persistence", relative_label(PIPELINE_PRESETS_DIR)),
        ],
    )

    selected_catalog_label = st.selectbox(
        "Preset library",
        preset_labels,
        index=preset_labels.index(loaded_label) if loaded_label in preset_labels else 0,
    )
    selected_catalog_entry = catalog[selected_catalog_label]
    st.caption(selected_catalog_entry.get("description", ""))

    toolbar = st.columns([0.95, 0.72, 0.72, 0.72, 1.15], gap="small")
    with toolbar[0]:
        if st.button("Load preset", use_container_width=True):
            st.session_state["pipeline_studio_nodes"] = json_safe_copy(selected_catalog_entry["nodes"])
            st.session_state["pipeline_studio_loaded_preset"] = selected_catalog_label
            st.session_state["pipeline_studio_selected"] = st.session_state["pipeline_studio_nodes"][0]["id"]
            st.rerun()
    with toolbar[1]:
        if st.button("Add node", use_container_width=True):
            existing_ids = {node["id"] for node in nodes}
            new_id = slugify_label(f"custom_{len(nodes) + 1}")
            while new_id in existing_ids:
                new_id = slugify_label(f"{new_id}_{len(existing_ids)}")
            nodes.append(
                {
                    "id": new_id,
                    "label": "Custom step",
                    "category": "analysis",
                    "command": "python scripts/experiments/generate_paper_figures.py --help",
                    "depends_on": [],
                    "expected_outputs": [],
                    "notes": "Custom launch point.",
                    "launchable": True,
                    "active": True,
                }
            )
            st.session_state["pipeline_studio_selected"] = new_id
            st.rerun()
    with toolbar[2]:
        if selected_node is not None and st.button("Clone node", use_container_width=True):
            clone = copy.deepcopy(selected_node)
            clone["id"] = slugify_label(f"{selected_node['id']}_copy")
            existing_ids = {node["id"] for node in nodes}
            while clone["id"] in existing_ids:
                clone["id"] = slugify_label(f"{clone['id']}_x")
            clone["label"] = f"{clone['label']} copy"
            nodes.append(clone)
            st.session_state["pipeline_studio_selected"] = clone["id"]
            st.rerun()
    with toolbar[3]:
        if selected_node is not None and st.button("Delete node", use_container_width=True, disabled=len(nodes) <= 1):
            nodes = [node for node in nodes if node["id"] != selected_node["id"]]
            for node in nodes:
                node["depends_on"] = [dep for dep in node.get("depends_on", []) if dep != selected_node["id"]]
            st.session_state["pipeline_studio_nodes"] = nodes
            st.session_state["pipeline_studio_selected"] = nodes[0]["id"]
            st.rerun()
    with toolbar[4]:
        st.markdown(
            f"""
            <div class="lab-card">
              <div class="lab-eyebrow">Repo preset library</div>
              <h3>{len(repo_pipeline_presets())} saved presets</h3>
              <p>User DAG presets live inside the repository and can be versioned like normal project assets.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    status_df = pipeline_summary_frame(nodes)
    statuses = pipeline_status_map(nodes)
    validation_order, _, validation_errors = pipeline_topology(nodes)
    materialized = int((status_df["status"] == "materialized").sum()) if not status_df.empty else 0
    ready = int((status_df["status"] == "ready").sum()) if not status_df.empty else 0
    planned = int((status_df["status"] == "planned").sum()) if not status_df.empty else 0
    repo_count = len(repo_pipeline_presets())

    metrics = st.columns(5)
    with metrics[0]:
        st.metric("Materialized", str(materialized))
    with metrics[1]:
        st.metric("Ready frontier", str(ready))
    with metrics[2]:
        st.metric("Planned", str(planned))
    with metrics[3]:
        st.metric("Repo presets", str(repo_count))
    with metrics[4]:
        st.metric("Validation errors", str(len(validation_errors)))

    if validation_errors:
        for error in validation_errors:
            st.error(error)
    else:
        st.success("Topology is valid. The active nodes can be exported and executed as a sequential shell pipeline.")

    with st.container(border=True):
        st.markdown("### DAG canvas")
        st.caption("Drag blocks, connect dependencies, click a block to edit it immediately in the right-hand dock, and keep the whole CLI graph versionable inside the repo.")
        canvas_left, canvas_right = st.columns([1.4, 0.86], gap="large")
        with canvas_left:
            canvas_actions = st.columns([0.86, 0.72, 0.72], gap="small")
            with canvas_actions[0]:
                focus_choice = st.selectbox(
                    "Focus block",
                    [node["id"] for node in nodes],
                    index=[node["id"] for node in nodes].index(selected_node["id"]) if selected_node is not None else 0,
                    format_func=lambda node_id: next(node["label"] for node in nodes if node["id"] == node_id),
                    key="pipeline_canvas_focus",
                )
                st.session_state["pipeline_studio_selected"] = focus_choice
                selected_id = focus_choice
                selected_node = next((node for node in nodes if node["id"] == selected_id), selected_node)
            with canvas_actions[1]:
                if st.button("Auto-layout", key="pipeline_auto_layout", use_container_width=True):
                    nodes = auto_layout_pipeline_nodes(nodes)
                    st.session_state["pipeline_studio_nodes"] = nodes
                    st.session_state["pipeline_studio_flow_signature"] = ""
                    st.rerun()
            with canvas_actions[2]:
                if st.button("Refresh canvas", key="pipeline_refresh_canvas", use_container_width=True):
                    st.session_state["pipeline_studio_flow_signature"] = ""
                    st.rerun()

            if streamlit_flow is None:
                st.warning(f"Interactive flow editor unavailable in this environment: {FLOW_ERROR}")
                fig = pipeline_dag_figure(nodes, selected_id=selected_id)
                st.plotly_chart(style_plot(fig), use_container_width=True)
            else:
                flow_state = pipeline_canvas_state(nodes, selected_id)
                if flow_state is not None:
                    returned_state = streamlit_flow(
                        key="pipeline_studio_flow",
                        state=flow_state,
                        height=920,
                        fit_view=True,
                        show_controls=True,
                        show_minimap=True,
                        allow_new_edges=True,
                        animate_new_edges=True,
                        get_node_on_click=True,
                        get_edge_on_click=True,
                        enable_edge_menu=True,
                        enable_node_menu=True,
                        enable_pane_menu=True,
                        hide_watermark=True,
                        layout=ManualLayout(),
                    )
                    if flow_state_signature(returned_state) != flow_state_signature(flow_state):
                        nodes = sync_pipeline_from_flow(nodes, returned_state)
                        st.session_state["pipeline_studio_nodes"] = nodes
                        st.session_state["pipeline_studio_flow_state"] = returned_state
                        st.session_state["pipeline_studio_flow_signature"] = pipeline_flow_signature(nodes, returned_state.selected_id)
                        if returned_state.selected_id and any(node["id"] == returned_state.selected_id for node in nodes):
                            st.session_state["pipeline_studio_selected"] = returned_state.selected_id
                            selected_id = returned_state.selected_id
                    nodes = st.session_state["pipeline_studio_nodes"]
                    selected_id = st.session_state.get("pipeline_studio_selected", selected_id)
                    selected_node = next((node for node in nodes if node["id"] == selected_id), nodes[0] if nodes else None)

        with canvas_right:
            st.markdown("#### Selected block")
            if not nodes or selected_node is None:
                st.info("No blocks available.")
            else:
                upstream = ", ".join(selected_node.get("depends_on", [])) or "none"
                downstream = ", ".join(node["id"] for node in nodes if selected_node["id"] in node.get("depends_on", [])) or "none"
                st.markdown(status_badge_html(statuses.get(selected_node["id"], "planned")), unsafe_allow_html=True)
                st.caption(f"Upstream: {upstream}")
                st.caption(f"Downstream: {downstream}")

                other_ids = [node["id"] for node in nodes if node["id"] != selected_node["id"]]
                with st.form("pipeline_node_editor", border=False):
                    new_label = st.text_input("Label", value=selected_node["label"])
                    new_id = st.text_input("Stable id", value=selected_node["id"])
                    editor_cols = st.columns(2)
                    with editor_cols[0]:
                        categories = ["data", "training", "experiments", "evaluation", "analysis", "baseline", "paper"]
                        new_category = st.selectbox(
                            "Category",
                            categories,
                            index=categories.index(selected_node["category"]) if selected_node["category"] in categories else 0,
                        )
                        new_active = st.checkbox("Active", value=bool(selected_node.get("active", True)))
                    with editor_cols[1]:
                        new_launchable = st.checkbox("Launchable", value=bool(selected_node.get("launchable", True)))
                        new_depends = st.multiselect("Depends on", other_ids, default=selected_node.get("depends_on", []))
                    new_command = st.text_area("Command", value=selected_node["command"], height=160)
                    new_outputs = st.text_area(
                        "Expected outputs",
                        value="\n".join(selected_node.get("expected_outputs", [])),
                        height=100,
                    )
                    new_notes = st.text_area("Notes", value=selected_node.get("notes", ""), height=120)
                    submitted = st.form_submit_button("Apply block changes", use_container_width=True)
                    if submitted:
                        normalized_id = slugify_label(new_id)
                        collision = normalized_id != selected_node["id"] and any(node["id"] == normalized_id for node in nodes)
                        if collision:
                            st.error(f"Node id `{normalized_id}` already exists.")
                        else:
                            for node in nodes:
                                if node["id"] == selected_node["id"]:
                                    node.update(
                                        {
                                            "id": normalized_id,
                                            "label": new_label.strip() or normalized_id,
                                            "category": new_category,
                                            "command": new_command.strip(),
                                            "depends_on": new_depends,
                                            "expected_outputs": [line.strip() for line in new_outputs.splitlines() if line.strip()],
                                            "notes": new_notes.strip(),
                                            "launchable": bool(new_launchable),
                                            "active": bool(new_active),
                                        }
                                    )
                                else:
                                    node["depends_on"] = [normalized_id if dep == selected_node["id"] else dep for dep in node.get("depends_on", [])]
                            st.session_state["pipeline_studio_nodes"] = nodes
                            st.session_state["pipeline_studio_selected"] = normalized_id
                            st.session_state["pipeline_studio_flow_signature"] = ""
                            st.rerun()

                resolved = resolve_pipeline_command(selected_node["command"], python_command)
                st.markdown("**Resolved command**")
                st.code(quote_command(resolved) if resolved else "(empty command)", language="bash")
                quick_cols = st.columns(2)
                launch_disabled = not selected_node.get("launchable", True) or not selected_node.get("active", True) or not resolved
                with quick_cols[0]:
                    if st.button("Launch block", key="pipeline_launch_selected", use_container_width=True, disabled=launch_disabled):
                        launch_job(
                            f"Pipeline node: {selected_node['label']}",
                            "pipeline",
                            resolved,
                            REPO_ROOT,
                            selected_node.get("expected_outputs", []),
                        )
                        st.success("Pipeline node launched.")
                with quick_cols[1]:
                    if st.button("Duplicate block", key="pipeline_duplicate_inline", use_container_width=True):
                        clone = copy.deepcopy(selected_node)
                        clone["id"] = slugify_label(f"{selected_node['id']}_copy")
                        existing_ids = {node["id"] for node in nodes}
                        while clone["id"] in existing_ids:
                            clone["id"] = slugify_label(f"{clone['id']}_x")
                        clone["label"] = f"{clone['label']} copy"
                        clone["ui_pos"] = {
                            "x": float((selected_node.get("ui_pos") or {}).get("x", 60)) + 44,
                            "y": float((selected_node.get("ui_pos") or {}).get("y", 50)) + 44,
                        }
                        nodes.append(clone)
                        st.session_state["pipeline_studio_nodes"] = nodes
                        st.session_state["pipeline_studio_selected"] = clone["id"]
                        st.session_state["pipeline_studio_flow_signature"] = ""
                        st.rerun()
                if selected_node.get("notes"):
                    st.info(selected_node["notes"])

    workspace_left, workspace_right = st.columns([0.9, 1.1], gap="large")
    with workspace_left:
        st.markdown("### Execution summary")
        st.markdown(
            f"""
            <div class="lab-workspace-panel">
              <h4>Current graph state</h4>
              <p>
                The canvas now acts like a real operations surface: spatial edits stay with the DAG, edge rewiring updates dependencies,
                and the selected block editor is docked next to the graph instead of living in a disconnected section lower on the page.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Ready frontier", expanded=True):
            ready_nodes = status_df.loc[status_df["status"].isin(["ready", "materialized"]), ["label", "status", "category"]]
            if ready_nodes.empty:
                st.info("No nodes are currently ready or materialized.")
            else:
                render_dataframe(ready_nodes, use_container_width=True, hide_index=True)
        with st.expander("Node table", expanded=False):
            render_dataframe(status_df, use_container_width=True, hide_index=True)

    with workspace_right:
        st.markdown("### Import from lab history")
        history_entries = history_record_entries(limit=18)
        if not history_entries:
            st.info("No saved inference, uncertainty, or calibration runs are available for DAG import yet.")
        else:
            history_labels = [entry["label"] for entry in history_entries]
            selected_history_label = st.selectbox("Saved lab artifact", history_labels, key="pipeline_history_entry")
            selected_history_entry = history_entries[history_labels.index(selected_history_label)]
            st.markdown(
                f"""
                <div class="lab-workspace-panel">
                  <h4>{escape(str(selected_history_entry['title']))}</h4>
                  <p>{escape(str(selected_history_entry['subtitle']))}</p>
                  <p><code>{escape(relative_label(Path(str(selected_history_entry['path']))))}</code></p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Add history artifact block", use_container_width=True, key="pipeline_import_history"):
                existing_ids = {node["id"] for node in nodes}
                imported = pipeline_node_from_history_entry(selected_history_entry, existing_ids)
                nodes.append(imported)
                st.session_state["pipeline_studio_nodes"] = nodes
                st.session_state["pipeline_studio_selected"] = imported["id"]
                st.session_state["pipeline_studio_flow_signature"] = ""
                st.success("Saved lab artifact imported into the DAG.")
                st.rerun()

        st.markdown("### Repo presets and export")
        current_name = selected_catalog_entry.get("name", loaded_label.replace("Built-in · ", "").replace("Repo · ", ""))
        save_name = st.text_input("Preset name", value=current_name, key="pipeline_preset_save_name")
        save_description = st.text_area(
            "Preset description",
            value=selected_catalog_entry.get("description", ""),
            height=90,
            key="pipeline_preset_save_description",
        )
        save_cols = st.columns(2)
        with save_cols[0]:
            if st.button("Save current DAG to repo", use_container_width=True):
                target = save_repo_pipeline_preset(
                    name=save_name.strip() or current_name,
                    description=save_description.strip(),
                    nodes=nodes,
                    source_label=loaded_label,
                )
                st.success(f"Saved repo preset to {relative_label(target)}")
        with save_cols[1]:
            current_kind = selected_catalog_entry.get("kind")
            can_delete = current_kind == "repo"
            if st.button("Delete selected repo preset", use_container_width=True, disabled=not can_delete):
                if delete_repo_pipeline_preset_by_name(selected_catalog_entry["name"]):
                    st.success("Repo preset deleted.")
                    st.session_state["pipeline_studio_loaded_preset"] = next(iter(pipeline_preset_catalog()))
                    st.rerun()

        script_text = pipeline_shell_script(nodes, python_command)
        spec_text = json.dumps(
            {
                "preset": loaded_label,
                "description": save_description.strip() or selected_catalog_entry.get("description", ""),
                "nodes": nodes,
                "topological_order": validation_order,
            },
            indent=2,
            ensure_ascii=True,
        )
        with st.expander("Shell export", expanded=False):
            st.code(script_text, language="bash")
            download_cols = st.columns(2)
            with download_cols[0]:
                st.download_button(
                    "Download shell",
                    data=script_text,
                    file_name=f"{slugify_label(save_name or current_name)}.sh",
                    mime="text/x-shellscript",
                    use_container_width=True,
                )
            with download_cols[1]:
                st.download_button(
                    "Download JSON spec",
                    data=spec_text,
                    file_name=f"{slugify_label(save_name or current_name)}.json",
                    mime="application/json",
                    use_container_width=True,
                )

        st.markdown("**Sequential launch**")
        st.caption("Launch the whole active graph as one shell job while preserving node-level editability inside the studio.")
        if st.button("Launch active pipeline as one job", use_container_width=True, disabled=bool(validation_errors)):
            pipelines_dir = RUNS_DIR / "pipelines"
            pipelines_dir.mkdir(parents=True, exist_ok=True)
            script_path = pipelines_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_{slugify_label(save_name or current_name)}.sh"
            script_path.write_text(script_text, encoding="utf-8")
            os.chmod(script_path, 0o755)
            expected_outputs = []
            for node in nodes:
                if node.get("active", True):
                    expected_outputs.extend(node.get("expected_outputs", []))
            launch_job(
                f"Pipeline: {save_name or current_name}",
                "pipeline",
                ["bash", str(script_path)],
                REPO_ROOT,
                expected_outputs,
            )
            st.success(f"Pipeline script launched from {relative_label(script_path)}.")

        repo_presets = repo_pipeline_presets()
        with st.expander("Repo preset library", expanded=bool(repo_presets)):
            if not repo_presets:
                st.info("No repo-local presets have been saved yet.")
            else:
                repo_rows = []
                for name, payload in repo_presets.items():
                    repo_rows.append(
                        {
                            "name": name,
                            "saved_at": format_timestamp(payload.get("saved_at")),
                            "nodes": len(payload.get("nodes", [])),
                            "path": relative_label(Path(str(payload.get("_path", "")))),
                            "description": payload.get("description", ""),
                        }
                    )
                render_dataframe(pd.DataFrame(repo_rows), use_container_width=True, hide_index=True)



def render_model_architect(python_command: str, probe: dict[str, Any]) -> None:
    family_default = st.session_state.get("model_architect_family", "TGNN-Solv")
    family = segmented_choice(
        "Model family",
        ["TGNN-Solv", "DirectGNN"],
        key="model_architect_family",
        default=family_default,
    )
    default_config = ARCHITECTURE_DEFAULTS[family]
    config_candidates = available_configs()
    if family == "TGNN-Solv":
        config_candidates = [path for path in config_candidates if "directgnn" not in path.name.lower()]
    else:
        config_candidates = [path for path in config_candidates if "directgnn" in path.name.lower()]

    state_key = f"model_architect_doc_{family}"
    source_key = f"model_architect_source_{family}"
    if state_key not in st.session_state:
        st.session_state[state_key] = load_architecture_doc(family, default_config)
        st.session_state[source_key] = str(default_config)

    page_header(
        "Model Architect",
        "Visual editor for the maintained model families. Tweak real config flags, inspect the live forward path, compare TGNN-Solv against DirectGNN by active branches, preview real structure-derived graphs, and launch training from the edited design, including GPS encoder switches, TGNN descriptor augmentation, and optional Stage 0 warm starts.",
        eyebrow="Architecture",
        chips=[
            ("Family", family),
            ("Base config", relative_label(Path(st.session_state[source_key]))),
            ("Views", "map · diff · input graphs · export"),
        ],
    )

    architect_view = segmented_choice(
        "Architect workspace",
        ["Architecture map", "TGNN vs Direct diff", "Input graphs", "Export & launch"],
        key=f"architect_view_{family}",
        default="Architecture map",
    )

    selected_source = render_path_select("Base config", config_candidates, Path(st.session_state[source_key]), key=f"architect_source_{family}")
    control_bar = st.columns([0.86, 0.86, 1.28], gap="small")
    with control_bar[0]:
        if st.button("Load config into editor", key=f"architect_load_{family}", use_container_width=True):
            st.session_state[state_key] = load_architecture_doc(family, selected_source)
            st.session_state[source_key] = selected_source
            st.rerun()
    with control_bar[1]:
        if st.button("Reset edits", key=f"architect_reset_{family}", use_container_width=True):
            st.session_state[state_key] = load_architecture_doc(family, st.session_state[source_key])
            st.rerun()
    with control_bar[2]:
        st.markdown(
            f"""
            <div class="lab-card">
              <div class="lab-eyebrow">Loaded source</div>
              <h3>{relative_label(Path(st.session_state[source_key]))}</h3>
              <p>Edits stay in memory until you export or write a YAML copy.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    doc = copy.deepcopy(st.session_state[state_key])
    model = doc.setdefault("model", {})
    training = doc.setdefault("training", {})
    loss_weights = doc.setdefault("loss_weights", {})
    stage0 = doc.setdefault("stage0", {})
    base_doc = load_architecture_doc(family, st.session_state[source_key])

    with st.expander("Editable controls", expanded=architect_view == "Export & launch"):
        with st.container(border=True):
            control_cols = st.columns(3, gap="large")
            with control_cols[0]:
                st.markdown("#### Backbone")
                encoder_type = st.selectbox(
                    "Encoder type",
                    ["mpnn", "gps"],
                    index=["mpnn", "gps"].index(str(model.get("encoder_type", "mpnn"))),
                    key=f"{family}_encoder_type",
                )
                hidden_dim = st.slider("Hidden dim", 64, 512, int(model.get("hidden_dim", 256)), step=32, key=f"{family}_hidden_dim")
                n_gnn_layers = st.slider("GNN layers", 2, 10, int(model.get("n_gnn_layers", 6)), step=1, key=f"{family}_n_gnn_layers")
                encoder_role_mode = st.selectbox(
                    "Encoder role mode",
                    ["shared_residual", "split_late"],
                    index=["shared_residual", "split_late"].index(model.get("encoder_role_mode", "shared_residual")),
                    key=f"{family}_encoder_role_mode",
                )
                interaction_mode = st.selectbox(
                    "Interaction mode",
                    ["cross_attn", "bipartite"],
                    index=["cross_attn", "bipartite"].index(model.get("interaction_mode", "cross_attn")),
                    key=f"{family}_interaction_mode",
                )
                n_cross_attn_layers = st.slider("Interaction layers", 1, 6, int(model.get("n_cross_attn_layers", 3)), step=1, key=f"{family}_n_cross")
                n_attn_heads = st.slider("Attention heads", 1, 8, int(model.get("n_attn_heads", 8)), step=1, key=f"{family}_n_heads")
                pair_dim = st.slider("Pair dim", 128, 1024, int(model.get("pair_dim", 512)), step=64, key=f"{family}_pair_dim")
                dropout = st.slider("Dropout", 0.0, 0.4, float(model.get("dropout", 0.1)), step=0.02, key=f"{family}_dropout")
                if encoder_type == "gps":
                    gps_num_heads = st.slider("GPS heads", 1, 8, int(model.get("gps_num_heads", 4)), step=1, key=f"{family}_gps_heads")
                    gps_positional_encoding = st.selectbox(
                        "GPS positional encoding",
                        ["laplacian", "rwse"],
                        index=["laplacian", "rwse"].index(str(model.get("gps_positional_encoding", "laplacian"))),
                        key=f"{family}_gps_pe_kind",
                    )
                    gps_pe_dim = st.slider("GPS PE dim", 4, 32, int(model.get("gps_pe_dim", 8)), step=4, key=f"{family}_gps_pe_dim")
                    gps_use_edge_attr = st.toggle(
                        "GPS uses edge features",
                        value=bool(model.get("gps_use_edge_attr", True)),
                        key=f"{family}_gps_edge_attr",
                    )
                else:
                    gps_num_heads = int(model.get("gps_num_heads", 4))
                    gps_positional_encoding = str(model.get("gps_positional_encoding", "laplacian"))
                    gps_pe_dim = int(model.get("gps_pe_dim", 8))
                    gps_use_edge_attr = bool(model.get("gps_use_edge_attr", True))

            with control_cols[1]:
                st.markdown("#### Side information")
                set2set_steps = st.slider("Set2Set steps", 1, 6, int(model.get("set2set_steps", 3)), step=1, key=f"{family}_set2set")
                use_morgan_features = st.toggle("Morgan features", value=bool(model.get("use_morgan_features", False)), key=f"{family}_morgan")
                use_descriptor_augmentation = st.toggle(
                    "Descriptor augmentation",
                    value=bool(model.get("use_descriptor_augmentation", False)),
                    key=f"{family}_descriptor_aug",
                )
                if family == "TGNN-Solv":
                    if use_descriptor_augmentation:
                        descriptor_hidden_dim = st.slider(
                            "Descriptor hidden dim",
                            64,
                            512,
                            int(model.get("descriptor_hidden_dim", 128)),
                            step=32,
                            key=f"{family}_descriptor_hidden",
                        )
                        descriptor_augmentation_hidden_dim = st.slider(
                            "Descriptor fusion hidden dim",
                            64,
                            512,
                            int(model.get("descriptor_augmentation_hidden_dim", 128)),
                            step=32,
                            key=f"{family}_descriptor_aug_hidden",
                        )
                    else:
                        descriptor_hidden_dim = int(model.get("descriptor_hidden_dim", 128))
                        descriptor_augmentation_hidden_dim = int(model.get("descriptor_augmentation_hidden_dim", 128))
                    use_solvent_moe = st.toggle("Solvent-type MoE", value=bool(model.get("use_solvent_moe", True)), key=f"{family}_moe")
                    use_descriptor_priors = st.toggle("Descriptor priors", value=bool(model.get("use_descriptor_priors", False)), key=f"{family}_descriptor_priors")
                    use_group_priors = st.toggle("Group priors", value=bool(model.get("use_group_priors", False)), key=f"{family}_group_priors")
                    if use_descriptor_priors and use_group_priors:
                        st.warning("Descriptor priors and group priors are mutually exclusive. Group priors will be switched off.")
                        use_group_priors = False
                    use_gc_priors_crystal = st.toggle("GC crystal priors", value=bool(model.get("use_gc_priors_crystal", False)), key=f"{family}_gc_priors")
                else:
                    use_solvent_moe = False
                    use_descriptor_priors = False
                    use_group_priors = False
                    use_gc_priors_crystal = False
                    descriptor_hidden_dim = st.slider(
                        "Descriptor hidden dim",
                        64,
                        512,
                        int(model.get("descriptor_hidden_dim", 128)),
                        step=32,
                        key=f"{family}_descriptor_hidden",
                    )

            with control_cols[2]:
                st.markdown("#### Physics and training")
                batch_size = st.slider("Batch size", 16, 256, int(training.get("batch_size", 64)), step=16, key=f"{family}_batch")
                epochs_phase1 = st.slider("Phase 1 epochs", 0, 150, int(training.get("epochs_phase1", 50)), step=5, key=f"{family}_ep1")
                epochs_phase2 = st.slider("Phase 2 epochs", 0, 300, int(training.get("epochs_phase2", 200)), step=10, key=f"{family}_ep2")
                epochs_phase3 = st.slider("Phase 3 epochs", 0, 150, int(training.get("epochs_phase3", 50)), step=5, key=f"{family}_ep3")
                pair_temp_batching = st.toggle(
                    "Pair-temperature batching",
                    value=bool(training.get("use_pair_temperature_batching", True)),
                    key=f"{family}_pair_temp",
                )
                if family == "TGNN-Solv":
                    nrtl_tau_mode = st.selectbox(
                        "NRTL tau mode",
                        ["ref_invT", "legacy", "abc"],
                        index=["ref_invT", "legacy", "abc"].index(model.get("nrtl_tau_mode", "ref_invT")),
                        key=f"{family}_nrtl_mode",
                    )
                    use_temperature_in_nrtl_head = st.toggle(
                        "Temperature in NRTL head",
                        value=bool(model.get("use_temperature_in_nrtl_head", True)),
                        key=f"{family}_temp_nrtl",
                    )
                    use_oracle_injection = st.toggle(
                        "Oracle injection",
                        value=bool(model.get("use_oracle_injection", False)),
                        key=f"{family}_oracle",
                    )
                    use_implicit_diff = st.toggle(
                        "Implicit differentiation",
                        value=bool(model.get("use_implicit_diff", True)),
                        key=f"{family}_implicit",
                    )
                    stage0_enabled = st.toggle(
                        "Stage 0 warm start",
                        value=bool(stage0.get("enabled", False)),
                        key=f"{family}_stage0_enabled",
                    )
                    if stage0_enabled:
                        stage0_mode = st.selectbox(
                            "Stage 0 mode",
                            ["fresh", "checkpoint"],
                            index=["fresh", "checkpoint"].index(str(stage0.get("mode", "fresh"))),
                            key=f"{family}_stage0_mode",
                        )
                        pretrain_data = st.text_input(
                            "Stage 0 source",
                            value=str(stage0.get("pretrain_data", "zinc250k")),
                            key=f"{family}_stage0_source",
                        )
                        pretrain_checkpoint = st.text_input(
                            "Stage 0 checkpoint",
                            value=str(stage0.get("pretrain_checkpoint", "")),
                            key=f"{family}_stage0_checkpoint",
                        )
                        pretrain_epochs = st.number_input(
                            "Stage 0 epochs",
                            value=int(stage0.get("pretrain_epochs", 30)),
                            min_value=1,
                            step=1,
                            key=f"{family}_stage0_epochs",
                        )
                        pretrain_batch_size = st.number_input(
                            "Stage 0 batch size",
                            value=int(stage0.get("pretrain_batch_size", 128)),
                            min_value=1,
                            step=1,
                            key=f"{family}_stage0_batch",
                        )
                        pretrain_lr = st.number_input(
                            "Stage 0 LR",
                            value=float(stage0.get("pretrain_lr", 3.0e-4)),
                            min_value=1.0e-6,
                            step=1.0e-4,
                            format="%.6f",
                            key=f"{family}_stage0_lr",
                        )
                        pretrain_max_molecules = st.number_input(
                            "Stage 0 max molecules",
                            value=int(stage0.get("pretrain_max_molecules") or 0),
                            min_value=0,
                            step=1000,
                            key=f"{family}_stage0_max_mols",
                        )
                        pretrain_output = st.text_input(
                            "Stage 0 output",
                            value=str(stage0.get("pretrain_output", "")),
                            key=f"{family}_stage0_output",
                        )
                        run_descriptor_probe = st.toggle(
                            "Run descriptor probe",
                            value=bool(stage0.get("run_descriptor_probe", True)),
                            key=f"{family}_stage0_probe",
                        )
                        descriptor_probe_output_dir = st.text_input(
                            "Probe output",
                            value=str(stage0.get("descriptor_probe_output_dir", "")),
                            key=f"{family}_stage0_probe_output",
                        )
                        descriptor_probe_device = st.selectbox(
                            "Probe device",
                            ["cpu", *device_options_from_probe(probe)],
                            index=0 if str(stage0.get("descriptor_probe_device", "cpu")) == "cpu" else 1,
                            key=f"{family}_stage0_probe_device",
                        )
                    else:
                        stage0_mode = "fresh"
                        pretrain_data = str(stage0.get("pretrain_data", "zinc250k"))
                        pretrain_checkpoint = str(stage0.get("pretrain_checkpoint", ""))
                        pretrain_epochs = int(stage0.get("pretrain_epochs", 30))
                        pretrain_batch_size = int(stage0.get("pretrain_batch_size", 128))
                        pretrain_lr = float(stage0.get("pretrain_lr", 3.0e-4))
                        pretrain_max_molecules = int(stage0.get("pretrain_max_molecules") or 0)
                        pretrain_output = str(stage0.get("pretrain_output", ""))
                        run_descriptor_probe = bool(stage0.get("run_descriptor_probe", True))
                        descriptor_probe_output_dir = str(stage0.get("descriptor_probe_output_dir", ""))
                        descriptor_probe_device = str(stage0.get("descriptor_probe_device", "cpu"))
                else:
                    nrtl_tau_mode = "ref_invT"
                    use_temperature_in_nrtl_head = False
                    use_oracle_injection = False
                    use_implicit_diff = False
                    stage0_enabled = False
                    stage0_mode = "fresh"
                    pretrain_data = "zinc250k"
                    pretrain_checkpoint = ""
                    pretrain_epochs = 30
                    pretrain_batch_size = 128
                    pretrain_lr = 3.0e-4
                    pretrain_max_molecules = 0
                    pretrain_output = ""
                    run_descriptor_probe = False
                    descriptor_probe_output_dir = ""
                    descriptor_probe_device = "cpu"
                    st.info("DirectGNN keeps the shared encoder / interaction stack but removes the physics path in favor of a thermometer-plus-MLP head.")

    model["encoder_type"] = encoder_type
    model["gps_num_heads"] = gps_num_heads
    model["gps_use_edge_attr"] = gps_use_edge_attr
    model["gps_positional_encoding"] = gps_positional_encoding
    model["gps_pe_dim"] = gps_pe_dim
    model["hidden_dim"] = hidden_dim
    model["n_gnn_layers"] = n_gnn_layers
    model["encoder_role_mode"] = encoder_role_mode
    model["interaction_mode"] = interaction_mode
    model["n_cross_attn_layers"] = n_cross_attn_layers
    model["n_attn_heads"] = n_attn_heads
    model["pair_dim"] = pair_dim
    model["dropout"] = dropout
    model["set2set_steps"] = set2set_steps
    model["use_morgan_features"] = use_morgan_features
    model["use_descriptor_augmentation"] = use_descriptor_augmentation
    training["batch_size"] = batch_size
    training["epochs_phase1"] = epochs_phase1
    training["epochs_phase2"] = epochs_phase2
    training["epochs_phase3"] = epochs_phase3
    training["use_pair_temperature_batching"] = pair_temp_batching
    if family == "TGNN-Solv":
        model["descriptor_hidden_dim"] = descriptor_hidden_dim
        model["descriptor_augmentation_hidden_dim"] = descriptor_augmentation_hidden_dim
        model["use_solvent_moe"] = use_solvent_moe
        model["use_descriptor_priors"] = use_descriptor_priors
        model["use_group_priors"] = use_group_priors
        model["use_gc_priors_crystal"] = use_gc_priors_crystal
        model["nrtl_tau_mode"] = nrtl_tau_mode
        model["use_temperature_in_nrtl_head"] = use_temperature_in_nrtl_head
        model["use_oracle_injection"] = use_oracle_injection
        model["use_implicit_diff"] = use_implicit_diff
        stage0["enabled"] = stage0_enabled
        stage0["mode"] = stage0_mode
        stage0["pretrain_data"] = pretrain_data
        stage0["pretrain_checkpoint"] = pretrain_checkpoint
        stage0["pretrain_epochs"] = int(pretrain_epochs)
        stage0["pretrain_batch_size"] = int(pretrain_batch_size)
        stage0["pretrain_lr"] = float(pretrain_lr)
        stage0["pretrain_max_molecules"] = int(pretrain_max_molecules) if int(pretrain_max_molecules) > 0 else None
        stage0["pretrain_output"] = pretrain_output
        stage0["run_descriptor_probe"] = bool(run_descriptor_probe)
        stage0["descriptor_probe_output_dir"] = descriptor_probe_output_dir
        stage0["descriptor_probe_device"] = descriptor_probe_device
    else:
        model["descriptor_hidden_dim"] = descriptor_hidden_dim

    doc["model"] = model
    doc["training"] = training
    doc["loss_weights"] = loss_weights
    doc["stage0"] = stage0
    st.session_state[state_key] = doc

    solute = st.text_input("Sample solute SMILES", value=st.session_state.get(f"{family}_sample_solute", DEFAULT_SOLUTE_SMILES), key=f"{family}_sample_solute")
    solvent = st.text_input("Sample solvent SMILES", value=st.session_state.get(f"{family}_sample_solvent", DEFAULT_SOLVENT_SMILES), key=f"{family}_sample_solvent")
    summary = architecture_summary(family, doc)
    summary_cols = st.columns(8)
    summary_metrics = [
        ("Encoder", summary["encoder"]),
        ("Hidden dim", str(summary["hidden_dim"])),
        ("Readout dim", str(summary["readout_dim"])),
        ("Pair dim", str(summary["pair_dim"])),
        ("Active modules", str(summary["active_modules"])),
        ("Total epochs", str(summary["total_epochs"])),
        ("Stage 0", summary["stage0"]),
        ("Head type", summary["physics"]),
    ]
    for col, (label, value) in zip(summary_cols, summary_metrics):
        with col:
            st.metric(label, value)

    sibling_family = "DirectGNN" if family == "TGNN-Solv" else "TGNN-Solv"
    sibling_state_key = f"model_architect_doc_{sibling_family}"
    sibling_source_key = f"model_architect_source_{sibling_family}"
    sibling_doc = copy.deepcopy(
        st.session_state.get(sibling_state_key)
        or load_architecture_doc(sibling_family, ARCHITECTURE_DEFAULTS[sibling_family])
    )
    sibling_source = st.session_state.get(sibling_source_key, str(ARCHITECTURE_DEFAULTS[sibling_family]))

    tgnn_doc = doc if family == "TGNN-Solv" else sibling_doc
    direct_doc = doc if family == "DirectGNN" else sibling_doc
    branch_df = architecture_branch_rows(tgnn_doc, direct_doc)
    active_branch_items = [
        (row["module"], row["tgnn"] if family == "TGNN-Solv" else row["direct"])
        for _, row in branch_df.iterrows()
        if (row["tgnn"] if family == "TGNN-Solv" else row["direct"]) in {"core", "active"}
    ]
    active_branch_items = active_branch_items[:8]

    if architect_view == "Architecture map":
        with st.container(border=True):
            st.markdown("### Live architecture canvas")
            st.caption("Drag modules, connect branches, click a block to focus it, and edit the selected module directly in the docked inspector.")
            arch_left, arch_right = st.columns([1.38, 0.82], gap="large")
            with arch_left:
                st.markdown(branch_strip_html(f"{family} active branches", active_branch_items), unsafe_allow_html=True)
                if streamlit_flow is None:
                    st.warning(f"Interactive architecture editor unavailable in this environment: {FLOW_ERROR}")
                    st.markdown(architecture_svg(family, doc), unsafe_allow_html=True)
                else:
                    flow_state = architecture_canvas_state(family, doc)
                    if flow_state is not None:
                        returned_state = streamlit_flow(
                            key=f"architect_flow_{family}",
                            state=flow_state,
                            height=940,
                            fit_view=True,
                            show_controls=True,
                            show_minimap=True,
                            allow_new_edges=True,
                            animate_new_edges=True,
                            get_node_on_click=True,
                            get_edge_on_click=True,
                            enable_edge_menu=True,
                            enable_node_menu=True,
                            enable_pane_menu=True,
                            hide_watermark=True,
                            layout=ManualLayout(),
                        )
                        if flow_state_signature(returned_state) != flow_state_signature(flow_state):
                            sync_architecture_from_flow(family, returned_state)
                            st.session_state[f"architect_flow_state_{family}"] = returned_state
                            st.session_state[f"architect_flow_signature_{family}"] = architecture_visual_signature(family, doc)

            visual_payload = st.session_state.get(f"architect_visual_{family}", {})
            selected_visual_id = str(visual_payload.get("selected_id") or "")
            selected_visual = next((item for item in visual_payload.get("nodes", []) if item.get("id") == selected_visual_id), None)
            with arch_right:
                st.markdown("#### Selected module")
                if selected_visual is None:
                    st.info("Select a module on the architecture canvas to edit its visual note or toggle state.")
                else:
                    selected_label = selected_visual.get("label", selected_visual_id)
                    st.markdown(
                        f"""
                        <div class="lab-workspace-panel">
                          <h4>{escape(selected_label)}</h4>
                          <p>{escape(str(selected_visual.get('note', '')))}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.form(f"architect_visual_editor_{family}", border=False):
                        new_note = st.text_area("Module note", value=str(selected_visual.get("note", "")), height=130)
                        active_default = bool(selected_visual.get("active", True))
                        active_toggle = st.checkbox("Module active", value=active_default, disabled=selected_visual.get("kind") == "core")
                        save_visual = st.form_submit_button("Apply module changes", use_container_width=True)
                        if save_visual:
                            for item in visual_payload.get("nodes", []):
                                if item.get("id") == selected_visual_id:
                                    item["note"] = new_note.strip()
                                    item["active"] = bool(active_toggle)
                                    flag = item.get("flag")
                                    if flag:
                                        doc.setdefault("model", {})[flag] = bool(active_toggle)
                                        st.session_state[state_key] = doc
                                    if item.get("id") == "pre_head_priors" and not active_toggle:
                                        doc.setdefault("model", {})["use_descriptor_priors"] = False
                                        doc["model"]["use_group_priors"] = False
                                        doc["model"]["use_gc_priors_crystal"] = False
                                        st.session_state[state_key] = doc
                                    break
                            st.session_state[f"architect_visual_{family}"] = visual_payload
                            st.session_state[f"architect_flow_signature_{family}"] = ""
                            st.rerun()

                    if selected_visual.get("flag"):
                        st.caption(f"Mapped config flag: {selected_visual['flag']}")
                    st.markdown(
                        """
                        <div class="lab-callout">
                          Spatial edits stay with the visual architecture document, while supported toggles still write back into the edited YAML-backed model config.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    elif architect_view == "TGNN vs Direct diff":
        common_core = int(((branch_df["tgnn"] == "core") & (branch_df["direct"] == "core")).sum())
        tgnn_extra = int((branch_df["tgnn"].isin(["core", "active"]) & branch_df["direct"].isin(["removed", "off"])).sum())
        direct_extra = int((branch_df["direct"].isin(["core", "active"]) & branch_df["tgnn"].isin(["removed", "off"])).sum())
        diff_cols = st.columns(4)
        with diff_cols[0]:
            st.metric("Shared core modules", str(common_core))
        with diff_cols[1]:
            st.metric("TGNN-only active branches", str(tgnn_extra))
        with diff_cols[2]:
            st.metric("Direct-only active branches", str(direct_extra))
        with diff_cols[3]:
            backbone_match = int(shared_backbone_compare_frame(tgnn_doc, direct_doc)["match"].sum())
            st.metric("Shared backbone matches", str(backbone_match))

        strip_cols = st.columns(2, gap="large")
        with strip_cols[0]:
            tgnn_items = [(row["module"], row["tgnn"]) for _, row in branch_df.iterrows() if row["tgnn"] in {"core", "active"}]
            st.markdown(branch_strip_html("TGNN-Solv active/core path", tgnn_items[:10]), unsafe_allow_html=True)
        with strip_cols[1]:
            direct_items = [(row["module"], row["direct"]) for _, row in branch_df.iterrows() if row["direct"] in {"core", "active"}]
            st.markdown(branch_strip_html("DirectGNN active/core path", direct_items[:10]), unsafe_allow_html=True)

        with st.container(border=True):
            heatmap = architecture_branch_heatmap(tgnn_doc, direct_doc)
            st.plotly_chart(style_plot(heatmap), use_container_width=True)
        with st.container(border=True):
            balance_fig = architecture_track_balance_figure(branch_df)
            st.plotly_chart(style_plot(balance_fig), use_container_width=True)

        diff_left, diff_right = st.columns([0.92, 1.08], gap="large")
        with diff_left:
            st.markdown("### Shared-backbone parity")
            render_dataframe(shared_backbone_compare_frame(tgnn_doc, direct_doc), use_container_width=True, hide_index=True)
        with diff_right:
            st.markdown("### Branch rationale")
            rationale_rows = branch_df[branch_df["tgnn"] != branch_df["direct"]][["module", "track", "explanation"]]
            render_dataframe(rationale_rows, use_container_width=True, hide_index=True)

        with st.container(border=True):
            st.markdown("### TGNN-Solv path")
            st.caption(f"Current source: {relative_label(Path(st.session_state.get('model_architect_source_TGNN-Solv', ARCHITECTURE_DEFAULTS['TGNN-Solv'])))}")
            st.markdown(architecture_svg("TGNN-Solv", tgnn_doc), unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### DirectGNN path")
            st.caption(f"Current source: {relative_label(Path(sibling_source if family == 'TGNN-Solv' else st.session_state[source_key]))}")
            st.markdown(architecture_svg("DirectGNN", direct_doc), unsafe_allow_html=True)

    elif architect_view == "Input graphs":
        graph_cols = st.columns(2, gap="large")
        with graph_cols[0]:
            with st.container(border=True):
                render_molecule_showcase(
                    solute,
                    title="Solute",
                    subtitle="Compact RDKit structure and atom graph preview derived from the exact architect input.",
                    svg_size=(440, 300),
                    graph_height=360,
                    compact=True,
                )
        with graph_cols[1]:
            with st.container(border=True):
                render_molecule_showcase(
                    solvent,
                    title="Solvent",
                    subtitle="The same chemistry pipeline that feeds the models is used for this solvent preview as well.",
                    svg_size=(440, 300),
                    graph_height=360,
                    compact=True,
                )
        lower_left, lower_right = st.columns([1.0, 1.0], gap="large")
        with lower_left:
            st.markdown("### Input summary")
            render_dataframe(architecture_input_frame(solute, solvent), use_container_width=True, hide_index=True)
        with lower_right:
            st.markdown("### Descriptor snapshot")
            snap_cols = st.columns(2)
            with snap_cols[0]:
                st.json(descriptor_summary(solute) or {})
            with snap_cols[1]:
                st.json(descriptor_summary(solvent) or {})

    else:
        st.markdown("### Config delta and export")
        export_left, export_right = st.columns([0.9, 1.1], gap="large")
        diff_df = config_diff_frame(base_doc, doc)
        with export_left:
            with st.container(border=True):
                st.markdown("#### Delta from base config")
                if diff_df.empty:
                    st.info("No edits relative to the loaded base config.")
                else:
                    render_dataframe(diff_df, use_container_width=True, hide_index=True)

        with export_right:
            yaml_text = yaml_dump_text(doc)
            default_slug = slugify_label(Path(st.session_state[source_key]).stem or family)
            save_path = st.text_input(
                "Write YAML copy to",
                value=str(generated_config_path(family, default_slug)),
                key=f"architect_save_path_{family}",
            )
            action_cols = st.columns(2)
            with action_cols[0]:
                st.download_button(
                    "Download YAML",
                    data=yaml_text,
                    file_name=f"{default_slug}.yaml",
                    mime="application/x-yaml",
                    use_container_width=True,
                )
            with action_cols[1]:
                if st.button("Write YAML copy", key=f"architect_write_{family}", use_container_width=True):
                    target = Path(save_path)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(yaml_text, encoding="utf-8")
                    st.success(f"Wrote {relative_label(target)}")

            with st.container(border=True):
                st.markdown("**Launch training from the edited design**")
                launch_train = st.text_input("Train CSV", value=str(PROCESSED_DIR / "train.csv"), key=f"architect_train_{family}")
                launch_val = st.text_input("Val CSV", value=str(PROCESSED_DIR / "val.csv"), key=f"architect_val_{family}")
                launch_test = st.text_input("Test CSV", value=str(PROCESSED_DIR / "test.csv"), key=f"architect_test_{family}")
                checkpoint_default = CHECKPOINTS_DIR / ("architect_directgnn.pt" if family == "DirectGNN" else "architect_tgnn.pt")
                launch_checkpoint = st.text_input("Checkpoint output", value=str(checkpoint_default), key=f"architect_ckpt_{family}")
                launch_device = st.selectbox("Device", device_options_from_probe(probe), key=f"architect_device_{family}")
                command = build_architecture_training_command(
                    family,
                    save_path,
                    python_command,
                    doc=doc,
                    train_data=launch_train,
                    val_data=launch_val,
                    test_data=launch_test,
                    checkpoint=launch_checkpoint,
                    device=launch_device,
                )
                st.code(quote_command(command), language="bash")
                if st.button("Queue architect training", key=f"architect_launch_{family}", use_container_width=True):
                    target = Path(save_path)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(yaml_text, encoding="utf-8")
                    launch_job(
                        f"Architect launch: {family}",
                        "training",
                        command,
                        REPO_ROOT,
                        [launch_checkpoint, save_path],
                    )
                    st.success("Training job queued from the edited architecture.")
            with st.expander("Full edited YAML", expanded=False):
                st.code(yaml_text, language="yaml")
            with st.expander("Architecture notes", expanded=False):
                if family == "TGNN-Solv":
                    st.markdown(
                        "The editor drives the real TGNN path: shared MPNN/GPS encoder, optional descriptor augmentation and priors, interaction stack, `FusionHead`, `NRTLHead`, `SLESolver`, bounded correction, and optional Stage 0 warm-start flags that are exported back into the maintained training CLI."
                    )
                else:
                    st.markdown(
                        "The editor drives the maintained DirectGNN ablation: same shared MPNN/GPS encoder and interaction backbone, thermometer temperature encoding, optional descriptor augmentation, and a direct MLP to `ln(x₂)` with no solver bottleneck."
                    )


def render_results_page(python_command: str) -> None:
    palette = theme_palette()
    page_header(
        "Results & Plots",
        "Browse structured outputs, inspect experiment lineage, compare artifacts side by side, and drill into checkpoints, tables, and figures without leaving the repo.",
        eyebrow="Analytics",
        chips=[
            ("Artifacts", str(filesystem_summary()["artifacts"])),
            ("Evaluations", str(len(discover_evaluation_jsons()))),
            ("Images", str(len(available_images()))),
            ("Inference history", str(len(load_inference_history()))),
            ("Uncertainty history", str(len(load_uncertainty_history()))),
            ("Calibration history", str(len(load_calibration_history()))),
        ],
    )
    view_mode = segmented_choice(
        "Results view",
        ["Dashboard", "Benchmark studio", "Artifact explorer", "Experiment registry", "Lineage graph", "Artifact diff", "Image gallery"],
        key="results_view",
        default="Dashboard",
    )

    if view_mode == "Dashboard":
        eval_paths = discover_evaluation_jsons()
        metric_df = discover_metric_csvs()
        if not metric_df.empty:
            leaderboard = (
                metric_df.dropna(subset=["mae"])
                .sort_values("mae", ascending=True)
                .groupby("model", as_index=False)
                .first()[["model", "mae", "rmse", "r2", "artifact"]]
            )
            render_dataframe(leaderboard, use_container_width=True, hide_index=True)

        upper_left, upper_right = st.columns([1.0, 1.0], gap="large")
        with upper_left:
            if eval_paths:
                labels = [relative_label(Path(path)) for path in eval_paths]
                choice = st.selectbox("Evaluation JSON", labels, index=min(len(labels) - 1, 0))
                selected_path = eval_paths[labels.index(choice)]
                evaluation_report_view(cached_json(selected_path))
            else:
                st.info("No evaluation-style JSON payloads were found under results/.")
        with upper_right:
            if not metric_df.empty:
                metric = st.selectbox("Metric comparison", [col for col in ["mae", "rmse", "r2", "val_loss", "runtime_s"] if col in metric_df.columns])
                slice_df = metric_df.dropna(subset=[metric]).copy()
                fig = px.bar(
                    slice_df,
                    x="model",
                    y=metric,
                    color="artifact",
                    barmode="group",
                    title=f"{metric} across benchmark CSVs",
                    height=540,
                )
                fig.update_xaxes(tickangle=35)
                st.plotly_chart(style_plot(fig), use_container_width=True)
            else:
                st.info("No benchmark CSVs with `model` and `mae` columns were found.")

        if not metric_df.empty and {"mae", "rmse"} <= set(metric_df.columns):
            scatter_df = metric_df.dropna(subset=["mae", "rmse"]).copy()
            if not scatter_df.empty:
                fig = px.scatter(
                    scatter_df,
                    x="rmse",
                    y="mae",
                    color="model",
                    symbol="artifact" if "artifact" in scatter_df.columns else None,
                    hover_data=["artifact"] if "artifact" in scatter_df.columns else None,
                    title="RMSE vs MAE across benchmark CSVs",
                    height=420,
                )
                st.plotly_chart(style_plot(fig), use_container_width=True)

    elif view_mode == "Benchmark studio":
        render_benchmark_studio()

    elif view_mode == "Artifact explorer":
        artifacts = available_artifacts()
        if not artifacts:
            st.warning("No result artifacts were found under results/, checkpoints/, figures/, or tables/.")
            return
        query = st.text_input("Artifact filter", value="", help="Filter by filename or relative path.")
        filtered = [
            path
            for path in artifacts
            if not query.strip() or query.strip().lower() in relative_label(path).lower()
        ]
        labels = [relative_label(path) for path in filtered]
        if not labels:
            st.info("No artifacts match the current filter.")
            return
        selected_label = st.selectbox("Artifact", labels)
        selected_path = filtered[labels.index(selected_label)]
        st.code(relative_label(selected_path), language="bash")

        if selected_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"}:
            st.image(str(selected_path), caption=relative_label(selected_path), use_container_width=True)
        elif selected_path.suffix.lower() == ".json":
            json_summary_view(cached_json(str(selected_path)))
        elif selected_path.suffix.lower() == ".csv":
            df = cached_dataframe(str(selected_path))
            render_dataframe(df.head(300), use_container_width=True)
            dataframe_plot_builder(df, key_prefix=f"plot_{selected_path.stem}")

    elif view_mode == "Experiment registry":
        registry_df = artifact_registry_frame()
        if registry_df.empty:
            st.info("No artifacts were discovered for the registry.")
            return
        filter_cols = st.columns([0.8, 0.8, 1.4], gap="small")
        with filter_cols[0]:
            kinds = st.multiselect("Kinds", sorted(registry_df["kind"].unique().tolist()), default=sorted(registry_df["kind"].unique().tolist()))
        with filter_cols[1]:
            models = st.multiselect("Model family", sorted(registry_df["model_guess"].unique().tolist()), default=sorted(registry_df["model_guess"].unique().tolist()))
        with filter_cols[2]:
            query = st.text_input("Search", value="", help="Filter by filename, parent folder, or path fragment.")

        filtered = registry_df.copy()
        if kinds:
            filtered = filtered[filtered["kind"].isin(kinds)]
        if models:
            filtered = filtered[filtered["model_guess"].isin(models)]
        if query.strip():
            q = query.strip().lower()
            filtered = filtered[
                filtered["path"].astype(str).str.lower().str.contains(q, regex=False)
                | filtered["name"].astype(str).str.lower().str.contains(q, regex=False)
                | filtered["parent"].astype(str).str.lower().str.contains(q, regex=False)
            ]
        if filtered.empty:
            st.info("No artifacts match the current registry filter.")
            return

        metric_cols = st.columns(4)
        with metric_cols[0]:
            st.metric("Visible artifacts", str(len(filtered)))
        with metric_cols[1]:
            st.metric("Checkpoints", str(int((filtered["kind"] == "checkpoint").sum())))
        with metric_cols[2]:
            st.metric("Tables", str(int((filtered["kind"] == "csv").sum())))
        with metric_cols[3]:
            st.metric("JSON reports", str(int((filtered["kind"] == "json").sum())))

        labels = filtered["path"].tolist()
        selected_label = st.selectbox("Focused artifact", labels, index=0)
        selected_row = filtered.loc[filtered["path"] == selected_label].iloc[0]
        selected_path = Path(str(selected_row["abs_path"]))

        reg_left, reg_right = st.columns([1.02, 0.98], gap="large")
        with reg_left:
            st.markdown("### Registry table")
            render_dataframe(
                filtered[["path", "kind", "model_guess", "size_mb", "modified_at"]].head(300),
                use_container_width=True,
                hide_index=True,
            )
        with reg_right:
            st.markdown("### Focused artifact")
            st.code(relative_label(selected_path), language="bash")
            st.markdown(
                f"""
                <div class="lab-stat-grid">
                  <div class="lab-stat-tile"><span>Kind</span><strong>{escape(str(selected_row['kind']))}</strong><small>{escape(str(selected_row['suffix']))}</small></div>
                  <div class="lab-stat-tile"><span>Model</span><strong>{escape(str(selected_row['model_guess']))}</strong><small>{escape(str(selected_row['parent']))}</small></div>
                  <div class="lab-stat-tile"><span>Size</span><strong>{float(selected_row['size_mb']):.3f} MB</strong><small>filesystem size</small></div>
                  <div class="lab-stat-tile"><span>Modified</span><strong>{escape(str(selected_row['modified_at']))}</strong><small>local timestamp</small></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            selected_kind = artifact_kind(selected_path)
            if selected_kind == "checkpoint":
                ckpt = inspect_checkpoint(python_command, str(selected_path), selected_path.stat().st_mtime)
                if ckpt.get("error"):
                    st.warning(ckpt["error"])
                else:
                    top_rows = [
                        {"field": "node_feat_dim", "value": ckpt.get("node_feat_dim")},
                        {"field": "edge_feat_dim", "value": ckpt.get("edge_feat_dim")},
                        {"field": "top keys", "value": ", ".join(ckpt.get("top_level_keys", []))},
                    ]
                    render_dataframe(pd.DataFrame(top_rows), use_container_width=True, hide_index=True)
                    with st.expander("Checkpoint config", expanded=False):
                        st.json(ckpt.get("config", {}))
            elif selected_kind in {"json", "inference_history", "uncertainty_history", "calibration_history"}:
                payload = cached_json(str(selected_path))
                if selected_kind == "inference_history" and isinstance(payload, dict):
                    summary_rows = [
                        {"field": "pair", "value": f"{payload.get('solute_smiles', '')} in {payload.get('solvent_smiles', '')}"},
                        {"field": "temperature", "value": f"{float(payload.get('temperature', 0.0)):.2f} K"},
                        {"field": "checkpoint", "value": relative_label(Path(str(payload.get('checkpoint')))) if payload.get('checkpoint') else "—"},
                        {"field": "ln_x2", "value": (payload.get("prediction") or {}).get("ln_x2")},
                        {"field": "OOD confidence", "value": (payload.get("domain") or {}).get("confidence")},
                    ]
                    render_dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
                elif selected_kind == "uncertainty_history" and isinstance(payload, dict):
                    summary_rows = [
                        {"field": "pair", "value": f"{payload.get('solute_smiles', '')} in {payload.get('solvent_smiles', '')}"},
                        {"field": "temperature", "value": f"{float(payload.get('temperature', 0.0)):.2f} K"},
                        {"field": "n_models", "value": payload.get("n_models")},
                        {"field": "ensemble std", "value": (payload.get("ensemble") or {}).get("ln_x2_std")},
                        {"field": "MC std", "value": (payload.get("mc_dropout") or {}).get("ln_x2_std")},
                    ]
                    render_dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
                elif selected_kind == "calibration_history" and isinstance(payload, dict):
                    reports = payload.get("reports") or {}
                    summary_rows = [
                        {"field": "dataset", "value": relative_label(Path(str(payload.get('dataset_csv')))) if payload.get('dataset_csv') else "—"},
                        {"field": "rows", "value": payload.get("n_rows")},
                        {"field": "methods", "value": ", ".join(sorted(reports.keys())) or "—"},
                        {"field": "ensemble PICP_90", "value": (reports.get("ensemble") or {}).get("PICP_90")},
                        {"field": "mc_dropout PICP_90", "value": (reports.get("mc_dropout") or {}).get("PICP_90")},
                    ]
                    render_dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
                numeric = flatten_numeric_payload(payload)
                if numeric:
                    top_numeric = (
                        pd.DataFrame([{"metric": key, "value": value} for key, value in numeric.items()])
                        .sort_values("value", ascending=False)
                        .head(30)
                    )
                    render_dataframe(top_numeric, use_container_width=True, hide_index=True)
                with st.expander("JSON summary", expanded=True):
                    json_summary_view(payload)
            elif artifact_kind(selected_path) == "csv":
                df = cached_dataframe(str(selected_path))
                info_rows = [
                    {"field": "rows", "value": len(df)},
                    {"field": "columns", "value": len(df.columns)},
                    {"field": "numeric columns", "value": sum(pd.api.types.is_numeric_dtype(df[col]) for col in df.columns)},
                ]
                render_dataframe(pd.DataFrame(info_rows), use_container_width=True, hide_index=True)
                with st.expander("CSV preview", expanded=True):
                    render_dataframe(df.head(120), use_container_width=True, hide_index=True)
            elif artifact_kind(selected_path) == "image":
                st.image(str(selected_path), caption=relative_label(selected_path), use_container_width=True)

            related = related_artifact_frame(filtered, selected_path)
            with st.expander("Related artifacts", expanded=True):
                if related.empty:
                    st.info("No obvious neighbors for this artifact under the current filter.")
                else:
                    render_dataframe(related[["path", "kind", "model_guess", "modified_at"]], use_container_width=True, hide_index=True)

    elif view_mode == "Lineage graph":
        registry_df = artifact_registry_frame()
        if registry_df.empty:
            st.info("No artifacts available for lineage inspection.")
            return
        labels = registry_df["path"].tolist()
        focal_label = st.selectbox("Focal artifact", labels, index=0, key="lineage_focal_artifact")
        focal_row = registry_df.loc[registry_df["path"] == focal_label].iloc[0]
        focal_path = Path(str(focal_row["abs_path"]))
        focal_kind = artifact_kind(focal_path)
        jobs = load_jobs()
        planner_payload = load_planner_state()
        planner_tasks = planner_payload.get("tasks", []) if isinstance(planner_payload, dict) else []
        related = related_artifact_frame(registry_df, focal_path, limit=8)

        checkpoint_rows = registry_df[registry_df["kind"] == "checkpoint"].copy()
        checkpoint_candidates = pd.DataFrame()
        if focal_kind == "checkpoint":
            checkpoint_candidates = registry_df[registry_df["path"] == focal_label].copy()
        else:
            checkpoint_candidates = checkpoint_rows[checkpoint_rows["model_guess"] == str(focal_row["model_guess"])].head(2)
            if checkpoint_candidates.empty:
                checkpoint_candidates = checkpoint_rows.head(2)

        nodes: list[dict[str, Any]] = []
        edges: list[tuple[str, str]] = []
        node_ids: set[str] = set()

        def add_node(node_id: str, *, label: str, subtitle: str, kind: str, x: float, y: float) -> None:
            if node_id in node_ids:
                return
            node_ids.add(node_id)
            nodes.append({"id": node_id, "label": label, "subtitle": subtitle, "kind": kind, "x": x, "y": y})

        add_node(
            "focal",
            label=focal_path.name,
            subtitle=f"{focal_kind} · {focal_row['model_guess']}",
            kind="focal",
            x=2.8,
            y=0.0,
        )

        matched_job_rows = [job for job in jobs if job_references_artifact(job, focal_path)][:4]
        matched_planner_tasks = [task for task in planner_tasks if planner_task_references_artifact(task, focal_path)][:4]
        inspected_checkpoints: list[tuple[Path, dict[str, Any]]] = []
        for idx, (_, ckpt_row) in enumerate(checkpoint_candidates.iterrows()):
            ckpt_path = Path(str(ckpt_row["abs_path"]))
            inspected = inspect_checkpoint(python_command, str(ckpt_path), ckpt_path.stat().st_mtime)
            inspected_checkpoints.append((ckpt_path, inspected))
            ckpt_node_id = f"checkpoint_{idx}"
            add_node(
                ckpt_node_id,
                label=ckpt_path.name,
                subtitle=ckpt_row["model_guess"],
                kind="checkpoint",
                x=2.0,
                y=float(idx) * 1.4 - 0.7,
            )
            if focal_kind != "checkpoint" or ckpt_path != focal_path:
                edges.append((ckpt_node_id, "focal"))
            else:
                edges.append((ckpt_node_id, "focal"))

            nearest_cfg_path, diff_count = (None, 0)
            if not inspected.get("error"):
                nearest_cfg_path, diff_count = nearest_config_for_doc(inspected.get("config", {}))
            if nearest_cfg_path:
                cfg_node_id = f"config_{idx}"
                add_node(
                    cfg_node_id,
                    label=Path(nearest_cfg_path).name,
                    subtitle=f"nearest config · diff {diff_count}",
                    kind="config",
                    x=0.2,
                    y=float(idx) * 1.4 - 0.7,
                )
                if matched_job_rows:
                    for job_idx, job in enumerate(matched_job_rows):
                        job_node_id = f"job_{job_idx}"
                        add_node(
                            job_node_id,
                            label=str(job.get("name", "job")),
                            subtitle=str(job.get("status", "queued")),
                            kind="job",
                            x=1.1,
                            y=float(job_idx) * 0.9 - 0.45,
                        )
                        edges.append((cfg_node_id, job_node_id))
                        edges.append((job_node_id, ckpt_node_id))
                else:
                    synthetic_run_id = f"run_{idx}"
                    add_node(
                        synthetic_run_id,
                        label=ckpt_path.stem,
                        subtitle="synthetic run node",
                        kind="job",
                        x=1.1,
                        y=float(idx) * 1.4 - 0.7,
                    )
                    edges.append((cfg_node_id, synthetic_run_id))
                    edges.append((synthetic_run_id, ckpt_node_id))

        history_context = history_lineage_context(focal_path)
        if history_context:
            if history_context.get("pair_label"):
                add_node(
                    "history_pair",
                    label=str(history_context["pair_label"]),
                    subtitle="queried chemistry system",
                    kind="artifact",
                    x=1.1,
                    y=-2.0,
                )
                edges.append(("history_pair", "focal"))
            if history_context.get("dataset_label"):
                add_node(
                    "history_dataset",
                    label=str(history_context["dataset_label"]),
                    subtitle="calibration dataset",
                    kind="artifact",
                    x=1.1,
                    y=-2.0,
                )
                edges.append(("history_dataset", "focal"))
            for idx, dataset_value in enumerate(item for item in history_context.get("datasets", []) if item):
                dataset_path = Path(str(dataset_value))
                dataset_node_id = f"history_data_{idx}"
                add_node(
                    dataset_node_id,
                    label=dataset_path.name,
                    subtitle="dataset reference",
                    kind="artifact",
                    x=1.1,
                    y=float(idx) * 0.7 - 2.7,
                )
                edges.append((dataset_node_id, "focal"))
            for idx, method in enumerate(history_context.get("methods", [])):
                method_node_id = f"history_method_{idx}"
                add_node(
                    method_node_id,
                    label=str(method),
                    subtitle="lab analysis mode",
                    kind="job",
                    x=3.6,
                    y=float(idx) * 0.66 + 1.15,
                )
                edges.append(("focal", method_node_id))

        for idx, (_, artifact_row) in enumerate(related.iterrows()):
            artifact_node_id = f"artifact_{idx}"
            add_node(
                artifact_node_id,
                label=Path(str(artifact_row["path"])).name,
                subtitle=f"{artifact_row['kind']} · {artifact_row['model_guess']}",
                kind="artifact",
                x=3.6,
                y=float(idx) * 0.92 - 1.8,
            )
            edges.append(("focal", artifact_node_id))

        for idx, task in enumerate(matched_planner_tasks):
            task_node_id = f"planner_{idx}"
            add_node(
                task_node_id,
                label=str(task.get("title", task.get("id", "planner task"))),
                subtitle=f"planner · {task.get('status', 'Ready')}",
                kind="job",
                x=4.9,
                y=float(idx) * 0.8 - 0.4,
            )
            edges.append(("focal", task_node_id))

        lineage_left, lineage_right = st.columns([1.15, 0.85], gap="large")
        with lineage_left:
            fig = lineage_graph_figure(nodes, edges)
            st.plotly_chart(style_plot(fig), use_container_width=True)
        with lineage_right:
            st.markdown("### Lineage summary")
            info_rows = [
                {"field": "focal path", "value": relative_label(focal_path)},
                {"field": "kind", "value": focal_kind},
                {"field": "model guess", "value": focal_row["model_guess"]},
                {"field": "matched jobs", "value": len(matched_job_rows)},
                {"field": "planner tasks", "value": len(matched_planner_tasks)},
                {"field": "candidate checkpoints", "value": len(checkpoint_candidates)},
                {"field": "related artifacts", "value": len(related)},
            ]
            render_dataframe(pd.DataFrame(info_rows), use_container_width=True, hide_index=True)
            if matched_job_rows:
                with st.expander("Matched jobs", expanded=True):
                    render_dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "name": job.get("name"),
                                    "status": job.get("status"),
                                    "created_at": format_timestamp(job.get("created_at")),
                                    "command": quote_command(job.get("command", [])) if isinstance(job.get("command"), list) else str(job.get("command")),
                                }
                                for job in matched_job_rows
                            ]
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
            if matched_planner_tasks:
                with st.expander("Planner tasks", expanded=True):
                    render_dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "title": task.get("title"),
                                    "status": task.get("status"),
                                    "priority": task.get("priority"),
                                    "artifact": relative_label(Path(str(task.get("artifact_path")))) if task.get("artifact_path") else "—",
                                }
                                for task in matched_planner_tasks
                            ]
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
            if history_context:
                with st.expander("History anchors", expanded=True):
                    history_rows = []
                    if history_context.get("pair_label"):
                        history_rows.append({"field": "pair", "value": history_context["pair_label"]})
                    if history_context.get("dataset_label"):
                        history_rows.append({"field": "dataset", "value": history_context["dataset_label"]})
                    if history_context.get("checkpoints"):
                        history_rows.append(
                            {
                                "field": "checkpoints",
                                "value": ", ".join(relative_label(Path(str(item))) for item in history_context["checkpoints"]),
                            }
                        )
                    if history_context.get("methods"):
                        history_rows.append({"field": "methods", "value": ", ".join(history_context["methods"])})
                    if history_rows:
                        render_dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)
            if inspected_checkpoints:
                with st.expander("Checkpoint anchors", expanded=True):
                    anchor_rows = []
                    for path, payload in inspected_checkpoints:
                        nearest_cfg_path, diff_count = (None, 0)
                        if not payload.get("error"):
                            nearest_cfg_path, diff_count = nearest_config_for_doc(payload.get("config", {}))
                        anchor_rows.append(
                            {
                                "checkpoint": relative_label(path),
                                "nearest_config": relative_label(Path(nearest_cfg_path)) if nearest_cfg_path else "—",
                                "diff_fields": diff_count,
                                "node_feat_dim": payload.get("node_feat_dim") if isinstance(payload, dict) else "—",
                            }
                        )
                    render_dataframe(pd.DataFrame(anchor_rows), use_container_width=True, hide_index=True)

    elif view_mode == "Artifact diff":
        registry_df = artifact_registry_frame()
        if registry_df.empty:
            st.info("No artifacts available for comparison.")
            return
        labels = registry_df["path"].tolist()
        compare_cols = st.columns(2, gap="large")
        with compare_cols[0]:
            left_label = st.selectbox("Left artifact", labels, index=0, key="artifact_diff_left")
        with compare_cols[1]:
            right_label = st.selectbox("Right artifact", labels, index=min(1, len(labels) - 1), key="artifact_diff_right")

        left_row = registry_df.loc[registry_df["path"] == left_label].iloc[0]
        right_row = registry_df.loc[registry_df["path"] == right_label].iloc[0]
        left_path = Path(str(left_row["abs_path"]))
        right_path = Path(str(right_row["abs_path"]))
        left_kind = artifact_kind(left_path)
        right_kind = artifact_kind(right_path)

        diff_metrics = st.columns(4)
        with diff_metrics[0]:
            st.metric("Left kind", left_kind)
        with diff_metrics[1]:
            st.metric("Right kind", right_kind)
        with diff_metrics[2]:
            st.metric("Left size", f"{float(left_row['size_mb']):.3f} MB")
        with diff_metrics[3]:
            st.metric("Right size", f"{float(right_row['size_mb']):.3f} MB")

        if left_kind == "checkpoint" and right_kind == "checkpoint":
            left_ckpt = inspect_checkpoint(python_command, str(left_path), left_path.stat().st_mtime)
            right_ckpt = inspect_checkpoint(python_command, str(right_path), right_path.stat().st_mtime)
            if left_ckpt.get("error"):
                st.warning(left_ckpt["error"])
            if right_ckpt.get("error"):
                st.warning(right_ckpt["error"])
            if not left_ckpt.get("error") and not right_ckpt.get("error"):
                diff_df = config_diff_frame(
                    normalize_config_document(left_ckpt.get("config", {})),
                    normalize_config_document(right_ckpt.get("config", {})),
                )
                meta_df = pd.DataFrame(
                    [
                        {"field": "node_feat_dim", "left": left_ckpt.get("node_feat_dim"), "right": right_ckpt.get("node_feat_dim")},
                        {"field": "edge_feat_dim", "left": left_ckpt.get("edge_feat_dim"), "right": right_ckpt.get("edge_feat_dim")},
                    ]
                )
                left_col, right_col = st.columns([0.82, 1.18], gap="large")
                with left_col:
                    render_dataframe(meta_df, use_container_width=True, hide_index=True)
                with right_col:
                    if diff_df.empty:
                        st.success("Checkpoint configs match on flattened fields.")
                    else:
                        render_dataframe(diff_df.head(200), use_container_width=True, hide_index=True)

        elif left_kind == "json" and right_kind == "json":
            left_payload = flatten_numeric_payload(cached_json(str(left_path)))
            right_payload = flatten_numeric_payload(cached_json(str(right_path)))
            compare_df = compare_numeric_frames(left_payload, right_payload)
            if compare_df.empty:
                st.info("No numeric overlap between the selected JSON payloads.")
            else:
                render_dataframe(compare_df.head(200), use_container_width=True, hide_index=True)
                plot_df = compare_df.dropna(subset=["delta"]).copy().sort_values("delta", key=lambda s: s.abs(), ascending=False).head(30)
                if not plot_df.empty:
                    fig = px.bar(plot_df, x="metric", y="delta", color="delta", title="JSON metric deltas", height=460)
                    fig.update_xaxes(tickangle=35)
                    st.plotly_chart(style_plot(fig), use_container_width=True)

        elif left_kind == "csv" and right_kind == "csv":
            left_df = cached_dataframe(str(left_path))
            right_df = cached_dataframe(str(right_path))
            common_numeric = [
                column
                for column in left_df.columns
                if column in right_df.columns and pd.api.types.is_numeric_dtype(left_df[column]) and pd.api.types.is_numeric_dtype(right_df[column])
            ]
            if not common_numeric:
                st.info("No common numeric columns exist between the selected CSV files.")
            else:
                metric = st.selectbox("CSV metric", common_numeric, key="artifact_diff_csv_metric")
                stats_df = pd.DataFrame(
                    [
                        {"dataset": "left", "mean": left_df[metric].mean(), "std": left_df[metric].std(), "median": left_df[metric].median(), "rows": len(left_df)},
                        {"dataset": "right", "mean": right_df[metric].mean(), "std": right_df[metric].std(), "median": right_df[metric].median(), "rows": len(right_df)},
                    ]
                )
                render_dataframe(stats_df, use_container_width=True, hide_index=True)
                hist = go.Figure()
                hist.add_trace(go.Histogram(x=left_df[metric], name="left", opacity=0.7, marker_color=palette["blue"]))
                hist.add_trace(go.Histogram(x=right_df[metric], name="right", opacity=0.7, marker_color=palette["red"]))
                hist.update_layout(
                    barmode="overlay",
                    title=f"{metric} distribution",
                    height=460,
                    xaxis_title=metric,
                    yaxis_title="count",
                )
                st.plotly_chart(style_plot(hist), use_container_width=True)
        else:
            st.info("Mixed artifact types currently get best support through the registry view. Choose two checkpoints, two JSON reports, or two CSV tables for structured diffing.")

    else:
        images = available_images()
        if not images:
            st.info("No image artifacts were found.")
        else:
            cols = st.columns(3, gap="large")
            for index, image_path in enumerate(images[:30]):
                with cols[index % 3]:
                    st.image(str(image_path), caption=relative_label(image_path), use_container_width=True)


def render_inference_page(python_command: str, probe: dict[str, Any]) -> None:
    palette = theme_palette()
    checkpoints = available_checkpoints()
    history_records = load_inference_history()
    uncertainty_history_records = load_uncertainty_history()
    calibration_history_records = load_calibration_history()
    page_header(
        "Inference & Interpretation",
        "Detailed single-system workbench with persistent history, thermodynamic decomposition, applicability-domain checks, and a dedicated uncertainty lab for MC-dropout and ensemble analysis.",
        eyebrow="Inference",
        chips=[
            ("Checkpoints", str(len(checkpoints))),
            ("History", str(len(history_records))),
            ("Uncertainty runs", str(len(uncertainty_history_records))),
            ("Calibration runs", str(len(calibration_history_records))),
            ("Runtime", probe.get("python", python_command)),
            ("Scan output", "JSON + CSV history"),
            ("Uncertainty", "MC-dropout + ensemble"),
        ],
    )
    if not checkpoints:
        st.warning("No checkpoints were found under checkpoints/.")
        return

    if not module_ok(probe, "tgnn_solv.inference"):
        st.error(
            "The selected interpreter cannot import `tgnn_solv.inference`. Fix the runtime on the Environment page or point the app at the project’s training environment."
        )
        return

    workbench_checkpoints, rejected_checkpoints = workbench_compatible_checkpoints(python_command, checkpoints)
    uncertainty_supported_checkpoints, _ = tgnn_inference_checkpoints(python_command, checkpoints)
    uncertainty_family_map: dict[str, str] = {}
    for path in uncertainty_supported_checkpoints:
        payload = inspect_checkpoint(python_command, str(path), path.stat().st_mtime)
        uncertainty_family_map[str(path)] = checkpoint_family_from_payload(payload)
    if not workbench_checkpoints:
        st.error("No supported checkpoints are available for the inference workbench.")
        if rejected_checkpoints:
            reject_df = pd.DataFrame(
                [
                    {"checkpoint": relative_label(path), "reason": reason}
                    for path, reason in rejected_checkpoints
                ]
            )
            render_dataframe(reject_df, use_container_width=True, hide_index=True)
        return

    if rejected_checkpoints:
        with st.expander("Skipped unsupported checkpoints", expanded=False):
            reject_df = pd.DataFrame(
                [
                    {"checkpoint": relative_label(path), "reason": reason}
                    for path, reason in rejected_checkpoints
                ]
            )
            render_dataframe(reject_df, use_container_width=True, hide_index=True)

    workspace = segmented_choice(
        "Inference workspace",
        ["Run & inspect", "History & compare", "Uncertainty lab", "Calibration dashboard"],
        key="inference_workspace",
        default="Run & inspect",
    )

    editor_seed_solute = st.session_state.get("inference_solute", DEFAULT_SOLUTE_SMILES)
    editor_seed_solvent = st.session_state.get("inference_solvent", DEFAULT_SOLVENT_SMILES)
    editor_version = int(st.session_state.get("inference_editor_version", 0))

    with st.expander("Structure editor", expanded=False):
        st.caption(
            "Draw or edit the solute and solvent directly. The editor now shows the sanitized RDKit structure and atom graph before anything is pushed into live inference."
        )
        if st_ketcher is None:
            st.info(
                "The Ketcher editor is not available in this environment. "
                "Restart the lab from a Python environment with the GUI extras, for example "
                "`python scripts/launch_lab.py` after installing `pip install -e \".[gui,dev]\"`."
            )
            st.caption(f"Current Streamlit interpreter: `{sys.executable}`")
            if KETCHER_ERROR:
                st.caption(f"Editor import error: {KETCHER_ERROR}")
        else:
            editor_cols = st.columns(2, gap="large")
            solute_editor_key = f"inference_solute_editor_{editor_version}"
            solvent_editor_key = f"inference_solvent_editor_{editor_version}"
            with editor_cols[0]:
                st.markdown("#### Solute editor")
                drawn_solute = st_ketcher(
                    editor_seed_solute,
                    height=420,
                    molecule_format="SMILES",
                    key=solute_editor_key,
                )
                solute_editor_smiles, solute_editor_error = canonicalize_smiles(drawn_solute)
                if solute_editor_error:
                    st.warning(solute_editor_error)
                else:
                    st.caption("Canonical solute SMILES from the editor")
                    st.code(solute_editor_smiles or "", language="text")
                if st.button("Use as solute", key="apply_drawn_solute", use_container_width=True):
                    if solute_editor_smiles:
                        st.session_state["inference_solute"] = solute_editor_smiles
                        st.session_state["infer_solute_input"] = solute_editor_smiles
                        st.session_state["inference_editor_version"] = editor_version + 1
                        st.rerun()
                    st.error(solute_editor_error or "The solute editor did not produce a valid structure.")
            with editor_cols[1]:
                st.markdown("#### Solvent editor")
                drawn_solvent = st_ketcher(
                    editor_seed_solvent,
                    height=420,
                    molecule_format="SMILES",
                    key=solvent_editor_key,
                )
                solvent_editor_smiles, solvent_editor_error = canonicalize_smiles(drawn_solvent)
                if solvent_editor_error:
                    st.warning(solvent_editor_error)
                else:
                    st.caption("Canonical solvent SMILES from the editor")
                    st.code(solvent_editor_smiles or "", language="text")
                if st.button("Use as solvent", key="apply_drawn_solvent", use_container_width=True):
                    if solvent_editor_smiles:
                        st.session_state["inference_solvent"] = solvent_editor_smiles
                        st.session_state["infer_solvent_input"] = solvent_editor_smiles
                        st.session_state["inference_editor_version"] = editor_version + 1
                        st.rerun()
                    st.error(solvent_editor_error or "The solvent editor did not produce a valid structure.")

            st.markdown("### Editor-derived chemistry preview")
            st.caption(
                "The preview below is generated from the sanitized canonical SMILES exported by the editor, so it reflects the exact structure that would be sent into the model."
            )
            preview_cols = st.columns(2, gap="large")
            with preview_cols[0]:
                render_structure_editor_preview(
                    "Solute",
                    solute_editor_smiles,
                    raw_smiles=drawn_solute,
                    error=solute_editor_error,
                )
            with preview_cols[1]:
                render_structure_editor_preview(
                    "Solvent",
                    solvent_editor_smiles,
                    raw_smiles=drawn_solvent,
                    error=solvent_editor_error,
                )

            action_cols = st.columns([0.92, 0.96, 0.78, 1.24], gap="small")
            with action_cols[0]:
                if st.button("Use sanitized preview in inference", key="apply_both_drawings", use_container_width=True):
                    errors: list[str] = []
                    if not solute_editor_smiles:
                        errors.append("solute")
                    if not solvent_editor_smiles:
                        errors.append("solvent")
                    if errors:
                        st.error("The editor could not export a valid " + " and ".join(errors) + " structure.")
                    else:
                        st.session_state["inference_solute"] = solute_editor_smiles
                        st.session_state["inference_solvent"] = solvent_editor_smiles
                        st.session_state["infer_solute_input"] = solute_editor_smiles
                        st.session_state["infer_solvent_input"] = solvent_editor_smiles
                        st.session_state["inference_editor_version"] = editor_version + 1
                        st.rerun()
            with action_cols[1]:
                if st.button("Apply drawing + run inference", key="apply_and_run_drawings", use_container_width=True):
                    errors: list[str] = []
                    if not solute_editor_smiles:
                        errors.append("solute")
                    if not solvent_editor_smiles:
                        errors.append("solvent")
                    if errors:
                        st.error("The editor could not export a valid " + " and ".join(errors) + " structure.")
                    else:
                        st.session_state["inference_solute"] = solute_editor_smiles
                        st.session_state["inference_solvent"] = solvent_editor_smiles
                        st.session_state["infer_solute_input"] = solute_editor_smiles
                        st.session_state["infer_solvent_input"] = solvent_editor_smiles
                        st.session_state["inference_workspace"] = "Run & inspect"
                        st.session_state["inference_autorun"] = True
                        st.session_state["inference_editor_version"] = editor_version + 1
                        st.rerun()
            with action_cols[2]:
                if st.button("Reload from live fields", key="reset_structure_editors", use_container_width=True):
                    st.session_state["inference_editor_version"] = editor_version + 1
                    st.rerun()
            with action_cols[3]:
                st.markdown(
                    """
                    <div class="lab-workspace-panel">
                      <h4>Editor workflow</h4>
                      <p>
                        Use the sketcher to draw, inspect the sanitized preview, and only then sync it into the live inference inputs.
                        This keeps the workbench stable while still making the structure-editing loop immediate and visual.
                      </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with st.form("inference_form", border=False):
        default_checkpoint = CHECKPOINTS_DIR / "tgnn_solv_trained.pt"
        if default_checkpoint not in workbench_checkpoints:
            default_checkpoint = workbench_checkpoints[0]
        checkpoint_path = render_path_select("Checkpoint", workbench_checkpoints, default_checkpoint, "infer_checkpoint")
        c1, c2, c3 = st.columns([1.1, 1.1, 0.7])
        with c1:
            solute = st.text_input(
                "Solute SMILES",
                value=st.session_state.get("inference_solute", DEFAULT_SOLUTE_SMILES),
                key="infer_solute_input",
            )
        with c2:
            solvent = st.text_input(
                "Solvent SMILES",
                value=st.session_state.get("inference_solvent", DEFAULT_SOLVENT_SMILES),
                key="infer_solvent_input",
            )
        with c3:
            temperature = st.number_input(
                "Temperature (K)",
                value=float(st.session_state.get("inference_temperature", 298.15)),
                min_value=150.0,
                max_value=800.0,
                step=1.0,
                key="infer_temperature_input",
            )
        with st.expander("Advanced scan and uncertainty settings", expanded=False):
            d1, d2, d3, d4 = st.columns(4)
            with d1:
                scan_tmin = st.number_input("Scan Tmin", value=270.0, min_value=150.0, max_value=780.0, step=5.0, key="infer_scan_tmin")
            with d2:
                scan_tmax = st.number_input("Scan Tmax", value=360.0, min_value=160.0, max_value=800.0, step=5.0, key="infer_scan_tmax")
            with d3:
                scan_points = st.number_input("Scan points", value=15, min_value=5, max_value=60, step=1, key="infer_scan_points")
            with d4:
                mc_samples = st.number_input("MC samples", value=30, min_value=10, max_value=80, step=5, key="infer_mc_samples")
            run_mc = st.checkbox("Run MC-dropout summary", value=False, key="infer_run_mc")
            reference_csv = st.text_input(
                "Reference train CSV for nearest-neighbor similarity",
                value=str(PROCESSED_DIR / "train.csv"),
                key="infer_reference_csv",
            )
            ood_cols = st.columns(4)
            with ood_cols[0]:
                run_domain = st.checkbox("Run OOD / applicability-domain score", value=False, key="infer_run_domain")
            with ood_cols[1]:
                domain_fit_rows = st.number_input("AD fit rows", value=4096, min_value=512, max_value=50000, step=512, key="infer_domain_fit_rows")
            with ood_cols[2]:
                domain_mahal_pct = st.slider("Mahalanobis cutoff percentile", min_value=0.80, max_value=0.99, value=0.95, step=0.01, key="infer_domain_mahal_pct")
            with ood_cols[3]:
                domain_tani_threshold = st.slider("Tanimoto threshold", min_value=0.10, max_value=0.80, value=0.30, step=0.05, key="infer_domain_tani_threshold")
            domain_csv = st.text_input("Applicability-domain train CSV", value=str(PROCESSED_DIR / "train.csv"), key="infer_domain_csv")
        submitted = st.form_submit_button("Run inference", use_container_width=True)
    auto_run_inference = bool(st.session_state.pop("inference_autorun", False))
    submitted = bool(submitted or auto_run_inference)

    st.session_state["inference_solute"] = solute
    st.session_state["inference_solvent"] = solvent
    st.session_state["inference_temperature"] = float(temperature)

    checkpoint_file = Path(checkpoint_path)
    selected_checkpoint_info = (
        inspect_checkpoint(python_command, str(checkpoint_file), checkpoint_file.stat().st_mtime)
        if checkpoint_file.exists()
        else {}
    )
    selected_family = checkpoint_family_from_payload(selected_checkpoint_info)
    latest_uncertainty = st.session_state.get("uncertainty_last_payload")
    latest_uncertainty_meta = st.session_state.get("uncertainty_last_meta", {})
    latest_calibration = st.session_state.get("uncertainty_calibration_payload")
    latest_calibration_meta = st.session_state.get("uncertainty_calibration_meta", {})

    if workspace == "Run & inspect":
        family_label = "DirectGNN" if selected_family == "direct_gnn" else "TGNN-Solv"
        st.caption(
            f"Selected checkpoint family: {family_label}."
            + (
                " This path supports direct ln(x₂) inference and temperature scans, but not solver decomposition or OOD / MC-dropout diagnostics."
                if selected_family == "direct_gnn"
                else " Full physics decomposition, OOD screening, and MC-dropout are available."
            )
        )

    if workspace == "Uncertainty lab":
        uncertainty_mode = segmented_choice(
            "Uncertainty mode",
            ["Run & inspect", "History & compare"],
            key="uncertainty_lab_mode",
            default="Run & inspect",
        )
        available_uncertainty_families = [
            family
            for family in ("tgnn_solv", "direct_gnn")
            if any(value == family for value in uncertainty_family_map.values())
        ]
        family_label_map = {"tgnn_solv": "TGNN-Solv", "direct_gnn": "DirectGNN"}
        if not available_uncertainty_families:
            st.info("No compatible checkpoints are available for uncertainty analysis.")
            return
        selected_uncertainty_family = segmented_choice(
            "Checkpoint family",
            [family_label_map[value] for value in available_uncertainty_families],
            key="uncertainty_family",
            default=family_label_map[available_uncertainty_families[0]] if available_uncertainty_families else "TGNN-Solv",
        )
        selected_uncertainty_family_key = next(
            (key for key, label in family_label_map.items() if label == selected_uncertainty_family),
            "tgnn_solv",
        )
        family_checkpoints = [
            path for path in uncertainty_supported_checkpoints if uncertainty_family_map.get(str(path)) == selected_uncertainty_family_key
        ]
        checkpoint_labels = [relative_label(path) for path in family_checkpoints]
        label_to_path = {relative_label(path): str(path) for path in family_checkpoints}
        default_uncertainty = checkpoint_labels[: min(3, len(checkpoint_labels))]
        st.markdown("### Uncertainty lab")
        st.caption(
            "Use multiple trained checkpoints as a deep ensemble, optionally add MC-dropout on the first checkpoint, and inspect interval bands across temperature rather than only point estimates."
            + (
                " For DirectGNN this stays in the direct-prediction space with no solver decomposition."
                if selected_uncertainty_family_key == "direct_gnn"
                else " For TGNN-Solv this still reflects the full solver-guided prediction path."
            )
        )
        if not family_checkpoints:
            st.info("No checkpoints of the selected family are available for uncertainty analysis.")
            return
        if uncertainty_mode == "Run & inspect":
            with st.form("uncertainty_lab_form", border=False):
                selected_labels = st.multiselect(
                    "Ensemble checkpoints",
                    checkpoint_labels,
                    default=default_uncertainty,
                    help="Choose at least two checkpoints for a true ensemble, or one checkpoint if you only want MC-dropout.",
                )
                u_cols = st.columns(4)
                with u_cols[0]:
                    include_mc = st.checkbox("Also run MC-dropout on first checkpoint", value=True)
                with u_cols[1]:
                    uncertainty_mc_samples = st.number_input("MC samples", value=30, min_value=10, max_value=80, step=5, key="uncertainty_mc_samples")
                with u_cols[2]:
                    uncertainty_scan_points = st.number_input("Scan points", value=12, min_value=5, max_value=40, step=1, key="uncertainty_scan_points")
                with u_cols[3]:
                    show_member_table = st.checkbox("Show member table", value=True)
                uncertainty_submit = st.form_submit_button("Run uncertainty analysis", use_container_width=True)

            if uncertainty_submit:
                selected_paths = tuple(label_to_path[label] for label in selected_labels)
                if not selected_paths:
                    st.error("Select at least one checkpoint.")
                elif len(selected_paths) < 2 and not include_mc:
                    st.error("Select at least two checkpoints for an ensemble or enable MC-dropout.")
                else:
                    with st.spinner("Running ensemble / MC uncertainty analysis..."):
                        uncertainty_payload = run_uncertainty_inference(
                            python_command,
                            selected_paths,
                            solute,
                            solvent,
                            float(temperature),
                            float(scan_tmin),
                            float(scan_tmax),
                            int(uncertainty_scan_points),
                            int(uncertainty_mc_samples),
                            bool(include_mc),
                        )
                    if uncertainty_payload.get("error"):
                        st.error(uncertainty_payload["error"])
                    else:
                        record_path = save_uncertainty_record(
                            solute=solute,
                            solvent=solvent,
                            temperature=float(temperature),
                            scan_tmin=float(scan_tmin),
                            scan_tmax=float(scan_tmax),
                            scan_points=int(uncertainty_scan_points),
                            mc_samples=int(uncertainty_mc_samples),
                            checkpoints=selected_paths,
                            include_mc=bool(include_mc),
                            model_family=selected_uncertainty_family_key,
                            payload=uncertainty_payload,
                        )
                        st.session_state["uncertainty_last_payload"] = uncertainty_payload
                        st.session_state["uncertainty_last_meta"] = {
                            "solute": solute,
                            "solvent": solvent,
                            "temperature": float(temperature),
                            "selected_checkpoints": selected_paths,
                            "model_family": selected_uncertainty_family_key,
                            "record_path": str(record_path),
                        }
                        latest_uncertainty = uncertainty_payload
                        latest_uncertainty_meta = st.session_state["uncertainty_last_meta"]
                        uncertainty_history_records = load_uncertainty_history()
                        st.success(f"Uncertainty run saved to {relative_label(record_path)}")

            if not latest_uncertainty:
                st.info("Pick checkpoints and run the uncertainty lab to populate ensemble and MC-dropout visuals.")
                return

            if latest_uncertainty.get("error"):
                st.error(latest_uncertainty["error"])
                return

            if latest_uncertainty_meta.get("record_path"):
                st.caption(f"Latest uncertainty run: {relative_label(Path(str(latest_uncertainty_meta['record_path'])))}")

            member_df = pd.DataFrame(latest_uncertainty.get("member_predictions", []))
            metric_cols = st.columns(5)
            with metric_cols[0]:
                st.metric("Models", str(int(latest_uncertainty.get("n_models", 0))))
            with metric_cols[1]:
                st.metric("MC enabled", "yes" if latest_uncertainty.get("mc_dropout") else "no")
            with metric_cols[2]:
                ens = latest_uncertainty.get("ensemble") or {}
                st.metric("Ensemble ln x₂", f"{float(ens.get('ln_x2_mean', float('nan'))):.3f}" if ens else "—")
            with metric_cols[3]:
                st.metric("Ensemble std", f"{float(ens.get('ln_x2_std', float('nan'))):.3f}" if ens else "—")
            with metric_cols[4]:
                mc = latest_uncertainty.get("mc_dropout") or {}
                st.metric("MC std", f"{float(mc.get('ln_x2_std', float('nan'))):.3f}" if mc else "—")

            upper_left, upper_right = st.columns([1.05, 0.95], gap="large")
            with upper_left:
                st.markdown("#### Uncertainty Bands Across Temperature")
                st.caption("Mean curve and 90% interval are shown outside the title area so the plot region stays clear.")
                uncertainty_fig = go.Figure()
                ensemble_scan_df = pd.DataFrame(latest_uncertainty.get("ensemble_scan", []))
                if not ensemble_scan_df.empty:
                    uncertainty_fig.add_trace(go.Scatter(x=ensemble_scan_df["T"], y=ensemble_scan_df["ln_x2_q95"], mode="lines", line={"width": 0}, hoverinfo="skip", showlegend=False))
                    uncertainty_fig.add_trace(go.Scatter(x=ensemble_scan_df["T"], y=ensemble_scan_df["ln_x2_q05"], mode="lines", line={"width": 0}, fill="tonexty", fillcolor=hex_to_rgba(palette["blue"], 0.16), name="Ensemble 90% interval"))
                    uncertainty_fig.add_trace(go.Scatter(x=ensemble_scan_df["T"], y=ensemble_scan_df["ln_x2_mean"], mode="lines+markers", name="Ensemble mean", line={"color": palette["blue"], "width": 3}))
                mc_scan_df = pd.DataFrame(latest_uncertainty.get("mc_scan", []))
                if not mc_scan_df.empty:
                    uncertainty_fig.add_trace(go.Scatter(x=mc_scan_df["T"], y=mc_scan_df["ln_x2_mean"], mode="lines", name="MC-dropout mean", line={"color": palette["orange"], "width": 2, "dash": "dash"}))
                if not member_df.empty:
                    uncertainty_fig.add_trace(go.Scatter(x=[latest_uncertainty_meta.get("temperature", float(temperature))] * len(member_df), y=member_df["ln_x2"], mode="markers", name="Member predictions", marker={"color": palette["green"], "size": 10, "line": {"color": palette["surface"], "width": 0.8}}))
                uncertainty_fig.update_layout(
                    height=540,
                    xaxis_title="Temperature (K)",
                    yaxis_title="ln x₂",
                    legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0, "xanchor": "left"},
                    margin={"l": 18, "r": 12, "t": 18, "b": 12},
                )
                st.plotly_chart(style_plot(uncertainty_fig), use_container_width=True)
            with upper_right:
                if not member_df.empty:
                    st.markdown("#### Per-Checkpoint Prediction Spread")
                    st.caption("Checkpoint labels are shortened in the plot; full paths remain in hover.")
                    member_plot_df = member_df.copy()
                    member_plot_df["checkpoint_label"] = member_plot_df["checkpoint"].map(compact_path_label)
                    spread_fig = px.bar(
                        member_plot_df,
                        x="checkpoint_label",
                        y="ln_x2",
                        color="checkpoint_label",
                        custom_data=["checkpoint"],
                        height=540,
                    )
                    spread_fig.update_traces(
                        hovertemplate="checkpoint=%{customdata[0]}<br>ln x₂=%{y:.3f}<extra></extra>"
                    )
                    spread_fig.update_xaxes(tickangle=-20, title_text="Checkpoint")
                    spread_fig.update_yaxes(title_text="ln x₂")
                    spread_fig.update_layout(
                        showlegend=False,
                        margin={"l": 18, "r": 12, "t": 18, "b": 12},
                    )
                    st.plotly_chart(style_plot(spread_fig), use_container_width=True)
                else:
                    st.info("No member predictions available.")

            lower_left, lower_right = st.columns([0.92, 1.08], gap="large")
            with lower_left:
                comparison_rows = []
                if latest_uncertainty.get("ensemble"):
                    comparison_rows.append({"method": "Ensemble", "ln_x2_mean": latest_uncertainty["ensemble"]["ln_x2_mean"], "ln_x2_std": latest_uncertainty["ensemble"]["ln_x2_std"]})
                if latest_uncertainty.get("mc_dropout"):
                    comparison_rows.append({"method": "MC-dropout", "ln_x2_mean": latest_uncertainty["mc_dropout"]["ln_x2_mean"], "ln_x2_std": latest_uncertainty["mc_dropout"]["ln_x2_std"]})
                if comparison_rows:
                    st.markdown("#### MC vs Ensemble Summary")
                    st.caption("Mean prediction and spread are separated on dual axes without an in-plot title.")
                    compare_methods = pd.DataFrame(comparison_rows)
                    compare_fig = go.Figure()
                    compare_fig.add_trace(go.Bar(x=compare_methods["method"], y=compare_methods["ln_x2_mean"], name="mean", marker_color=palette["blue"]))
                    compare_fig.add_trace(go.Scatter(x=compare_methods["method"], y=compare_methods["ln_x2_std"], mode="markers+lines", name="std", yaxis="y2", marker={"color": palette["red"], "size": 11}))
                    compare_fig.update_layout(
                        height=400,
                        yaxis={"title": "ln x₂ mean"},
                        yaxis2={"title": "std", "overlaying": "y", "side": "right"},
                        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0, "xanchor": "left"},
                        margin={"l": 18, "r": 18, "t": 18, "b": 12},
                    )
                    st.plotly_chart(style_plot(compare_fig), use_container_width=True)
            with lower_right:
                st.markdown(
                    """
                    <div class="lab-workspace-panel">
                      <h4>How to read this panel</h4>
                      <p>
                        Ensemble spread answers whether independently trained checkpoints disagree. MC-dropout answers whether one checkpoint
                        remains locally uncertain when dropout is re-enabled at inference. When both are small, the prediction is not only sharp
                        but also stable across training randomness.
                      </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if show_member_table and not member_df.empty:
                    render_dataframe(member_df, use_container_width=True, hide_index=True)

            with st.expander("Uncertainty raw payload", expanded=False):
                st.json(latest_uncertainty)
            return

        if not uncertainty_history_records:
            st.info("No saved uncertainty runs yet. Run one analysis first.")
            return

        uncertainty_df = uncertainty_history_frame(uncertainty_history_records)
        render_dataframe(uncertainty_df, use_container_width=True, hide_index=True)
        labels = [uncertainty_history_label(record) for record in uncertainty_history_records]
        selected_labels = st.multiselect("Compare uncertainty runs", labels, default=labels[:2], key="uncertainty_history_compare")
        selected_records = [uncertainty_history_records[labels.index(label)] for label in selected_labels]
        action_cols = st.columns([0.7, 0.7, 1.6], gap="small")
        with action_cols[0]:
            if st.button("Delete selected uncertainty runs", use_container_width=True, disabled=not selected_records):
                deleted = delete_uncertainty_records([str(record.get("id")) for record in selected_records])
                st.success(f"Deleted {deleted} saved uncertainty runs.")
                st.rerun()
        with action_cols[1]:
            st.download_button(
                "Download uncertainty JSON",
                data=json.dumps({"runs": selected_records}, indent=2),
                file_name="uncertainty_compare.json",
                mime="application/json",
                use_container_width=True,
                disabled=not selected_records,
            )
        if not selected_records:
            st.info("Select one or more uncertainty runs to compare.")
            return
        compare_rows = []
        for record in selected_records:
            ensemble = record.get("ensemble") or {}
            mc = record.get("mc_dropout") or {}
            compare_rows.append(
                {
                    "run": uncertainty_history_label(record),
                    "n_models": record.get("n_models"),
                    "ensemble_mean": ensemble.get("ln_x2_mean"),
                    "ensemble_std": ensemble.get("ln_x2_std"),
                    "mc_mean": mc.get("ln_x2_mean"),
                    "mc_std": mc.get("ln_x2_std"),
                }
            )
        render_dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)
        compare_left, compare_right = st.columns([1.02, 0.98], gap="large")
        with compare_left:
            st.markdown("#### Ensemble Mean Overlay")
            st.caption("Saved uncertainty runs are overlaid directly, with the heading kept outside the plotting canvas.")
            fig = go.Figure()
            for record in selected_records:
                scan_df = pd.DataFrame(record.get("ensemble_scan", []))
                if scan_df.empty:
                    continue
                fig.add_trace(go.Scatter(x=scan_df["T"], y=scan_df["ln_x2_mean"], mode="lines+markers", name=uncertainty_history_label(record)))
            fig.update_layout(
                height=500,
                xaxis_title="Temperature (K)",
                yaxis_title="ln x₂",
                legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0, "xanchor": "left"},
                margin={"l": 18, "r": 12, "t": 18, "b": 12},
            )
            st.plotly_chart(style_plot(fig), use_container_width=True)
        with compare_right:
            st.markdown("#### Ensemble Spread By Run")
            st.caption("Single-value spread bars are kept clean by moving the title outside the figure.")
            band_fig = go.Figure()
            for record in selected_records:
                ensemble = record.get("ensemble") or {}
                if not ensemble:
                    continue
                band_fig.add_trace(
                    go.Bar(
                        x=[uncertainty_history_label(record)],
                        y=[ensemble.get("ln_x2_std")],
                        name="ensemble std",
                        marker_color=palette["blue"],
                    )
                )
            band_fig.update_layout(
                height=500,
                yaxis_title="std",
                showlegend=False,
                margin={"l": 18, "r": 12, "t": 18, "b": 12},
            )
            st.plotly_chart(style_plot(band_fig), use_container_width=True)
        return

    if workspace == "Calibration dashboard":
        calibration_mode = segmented_choice(
            "Calibration mode",
            ["Run & inspect", "History & compare"],
            key="uncertainty_calibration_mode",
            default="Run & inspect",
        )
        available_calibration_families = [
            family
            for family in ("tgnn_solv", "direct_gnn")
            if any(value == family for value in uncertainty_family_map.values())
        ]
        family_label_map = {"tgnn_solv": "TGNN-Solv", "direct_gnn": "DirectGNN"}
        if not available_calibration_families:
            st.info("No compatible checkpoints are available for calibration analysis.")
            return
        selected_calibration_family = segmented_choice(
            "Checkpoint family",
            [family_label_map[value] for value in available_calibration_families],
            key="calibration_family",
            default=family_label_map[available_calibration_families[0]] if available_calibration_families else "TGNN-Solv",
        )
        selected_calibration_family_key = next(
            (key for key, label in family_label_map.items() if label == selected_calibration_family),
            "tgnn_solv",
        )
        family_checkpoints = [
            path for path in uncertainty_supported_checkpoints if uncertainty_family_map.get(str(path)) == selected_calibration_family_key
        ]
        checkpoint_labels = [relative_label(path) for path in family_checkpoints]
        label_to_path = {relative_label(path): str(path) for path in family_checkpoints}
        default_labels = checkpoint_labels[: min(3, len(checkpoint_labels))]
        st.markdown("### Batch calibration dashboard")
        st.caption(
            "Evaluate whether uncertainty intervals are actually calibrated on a real held-out CSV using the maintained `calibration_report(...)` helper."
            + (
                " DirectGNN uses the same interval diagnostics, just without solver-facing terms."
                if selected_calibration_family_key == "direct_gnn"
                else ""
            )
        )
        if not family_checkpoints:
            st.info("No checkpoints of the selected family are available for calibration analysis.")
            return
        if calibration_mode == "Run & inspect":
            with st.form("uncertainty_calibration_form", border=False):
                calibration_labels = st.multiselect(
                    "Calibration checkpoints",
                    checkpoint_labels,
                    default=default_labels,
                    help="Choose at least one checkpoint for MC-dropout and at least two for ensemble calibration.",
                )
                calib_cols = st.columns(4)
                with calib_cols[0]:
                    calibration_csv = st.text_input("Dataset CSV", value=str(PROCESSED_DIR / "test.csv"))
                with calib_cols[1]:
                    calibration_rows = st.number_input("Sample rows", value=48, min_value=8, max_value=512, step=8)
                with calib_cols[2]:
                    calibration_mc_samples = st.number_input("MC samples", value=24, min_value=10, max_value=80, step=2)
                with calib_cols[3]:
                    st.caption("Sampling is deterministic for repeatability.")
                include_ensemble = st.checkbox("Run ensemble calibration", value=True)
                include_mc_calibration = st.checkbox("Run MC-dropout calibration", value=True)
                calibration_submit = st.form_submit_button("Run calibration", use_container_width=True)

            if calibration_submit:
                selected_paths = tuple(label_to_path[label] for label in calibration_labels)
                if not selected_paths:
                    st.error("Select at least one checkpoint.")
                elif not include_mc_calibration and not include_ensemble:
                    st.error("Enable at least one calibration method.")
                elif include_ensemble and len(selected_paths) < 2:
                    st.error("Ensemble calibration requires at least two checkpoints.")
                else:
                    with st.spinner("Running batch calibration..."):
                        calibration_payload = run_uncertainty_calibration(
                            python_command,
                            selected_paths,
                            calibration_csv,
                            int(calibration_rows),
                            int(calibration_mc_samples),
                            bool(include_mc_calibration),
                            bool(include_ensemble),
                        )
                    if calibration_payload.get("error"):
                        st.error(calibration_payload["error"])
                    else:
                        record_path = save_calibration_record(
                            dataset_csv=calibration_csv,
                            sample_rows=int(calibration_rows),
                            mc_samples=int(calibration_mc_samples),
                            checkpoints=selected_paths,
                            include_mc=bool(include_mc_calibration),
                            include_ensemble=bool(include_ensemble),
                            model_family=selected_calibration_family_key,
                            payload=calibration_payload,
                        )
                        st.session_state["uncertainty_calibration_payload"] = calibration_payload
                        st.session_state["uncertainty_calibration_meta"] = {
                            "dataset_csv": calibration_csv,
                            "selected_checkpoints": selected_paths,
                            "model_family": selected_calibration_family_key,
                            "record_path": str(record_path),
                        }
                        latest_calibration = calibration_payload
                        latest_calibration_meta = st.session_state["uncertainty_calibration_meta"]
                        calibration_history_records = load_calibration_history()
                        st.success(f"Calibration run saved to {relative_label(record_path)}")

            if not latest_calibration:
                st.info("Run calibration once to populate coverage, interval-width, and parity diagnostics.")
                return
            if latest_calibration.get("error"):
                st.error(latest_calibration["error"])
                return

            if latest_calibration_meta.get("record_path"):
                st.caption(f"Latest calibration run: {relative_label(Path(str(latest_calibration_meta['record_path'])))}")

            reports = latest_calibration.get("reports", {})
            if not reports:
                st.warning("Calibration payload did not contain any method reports.")
                return

            report_df = pd.DataFrame(
                [
                    {
                        "method": method,
                        "PICP_90": report.get("PICP_90"),
                        "MPIW": report.get("MPIW"),
                        "MAE": report.get("MAE"),
                        "RMSE": report.get("RMSE"),
                        "sharpness": report.get("sharpness"),
                        "n_samples": report.get("n_samples"),
                    }
                    for method, report in reports.items()
                ]
            )
            render_dataframe(report_df, use_container_width=True, hide_index=True)

            coverage_fig = go.Figure()
            coverage_fig.add_trace(go.Bar(x=report_df["method"], y=report_df["PICP_90"], name="PICP_90", marker_color=palette["blue"]))
            coverage_fig.add_trace(go.Scatter(x=report_df["method"], y=[0.9] * len(report_df), mode="lines+markers", name="target 0.90", marker={"color": palette["red"], "size": 10}))
            coverage_fig.update_layout(title="Coverage vs target", height=420, yaxis_title="coverage")
            st.plotly_chart(style_plot(coverage_fig), use_container_width=True)

            sample_frames = []
            for rows in (latest_calibration.get("samples") or {}).values():
                frame = pd.DataFrame(rows)
                if not frame.empty:
                    sample_frames.append(frame)
            if not sample_frames:
                st.warning("Calibration sample rows are empty.")
                return
            sample_df = pd.concat(sample_frames, ignore_index=True)

            pair_left, pair_right = st.columns([1.02, 0.98], gap="large")
            with pair_left:
                method_choice = st.selectbox("Calibration method", sorted(sample_df["method"].unique().tolist()), key="calibration_method_choice")
                method_df = sample_df[sample_df["method"] == method_choice].copy()
                parity = go.Figure()
                parity.add_trace(
                    go.Scatter(
                        x=method_df["true_ln_x2"],
                        y=method_df["pred_ln_x2_mean"],
                        mode="markers",
                        error_y={
                            "type": "data",
                            "symmetric": False,
                            "array": method_df["q95"] - method_df["pred_ln_x2_mean"],
                            "arrayminus": method_df["pred_ln_x2_mean"] - method_df["q05"],
                        },
                        marker={"color": np.where(method_df["covered"], palette["green"], palette["red"]), "size": 10},
                        text=method_df["solute_smiles"].astype(str).str.slice(0, 24) + " in " + method_df["solvent_smiles"].astype(str).str.slice(0, 18),
                        hovertemplate="%{text}<br>true=%{x:.3f}<br>pred=%{y:.3f}<extra></extra>",
                        name="sample",
                    )
                )
                axis_min = float(min(method_df["true_ln_x2"].min(), method_df["pred_ln_x2_mean"].min()))
                axis_max = float(max(method_df["true_ln_x2"].max(), method_df["pred_ln_x2_mean"].max()))
                parity.add_shape(type="line", x0=axis_min, y0=axis_min, x1=axis_max, y1=axis_max, line={"dash": "dash", "color": palette["slate"]})
                parity.update_layout(title=f"{method_choice} parity with uncertainty intervals", height=520, xaxis_title="true ln x₂", yaxis_title="predicted mean ln x₂")
                st.plotly_chart(style_plot(parity), use_container_width=True)
            with pair_right:
                width_fig = px.histogram(method_df, x="interval_width", color="covered", nbins=24, title="Interval width distribution", height=520)
                st.plotly_chart(style_plot(width_fig), use_container_width=True)

            coverage_left, coverage_right = st.columns([0.95, 1.05], gap="large")
            with coverage_left:
                aggregate_df = (
                    sample_df.groupby("method", as_index=False)
                    .agg(coverage=("covered", "mean"), abs_error=("abs_error", "mean"), interval_width=("interval_width", "mean"))
                )
                tradeoff = go.Figure()
                for _, row in aggregate_df.iterrows():
                    tradeoff.add_trace(
                        go.Scatterpolar(
                            r=[row["coverage"], 1.0 / max(row["abs_error"], 1e-6), 1.0 / max(row["interval_width"], 1e-6), row["coverage"]],
                            theta=["Coverage", "Inverse MAE", "Inverse Width", "Coverage"],
                            fill="toself",
                            name=row["method"],
                        )
                    )
                tradeoff.update_layout(title="Calibration trade-offs", height=440)
                st.plotly_chart(style_plot(tradeoff), use_container_width=True)
            with coverage_right:
                st.markdown(
                    """
                    <div class="lab-workspace-panel">
                      <h4>Reading the dashboard</h4>
                      <p>
                        `PICP_90` should sit near 0.90. Lower means under-covered intervals, higher means intervals are overly wide.
                        `MPIW` and `sharpness` tell you whether that coverage is achieved efficiently or just by inflating the interval.
                      </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                render_dataframe(method_df.head(120), use_container_width=True, hide_index=True)

            with st.expander("Calibration raw payload", expanded=False):
                st.json(latest_calibration)
            return

        if not calibration_history_records:
            st.info("No saved calibration runs yet. Run one calibration session first.")
            return

        calibration_df = calibration_history_frame(calibration_history_records)
        render_dataframe(calibration_df, use_container_width=True, hide_index=True)
        labels = [calibration_history_label(record) for record in calibration_history_records]
        selected_labels = st.multiselect("Compare calibration runs", labels, default=labels[:2], key="calibration_history_compare")
        selected_records = [calibration_history_records[labels.index(label)] for label in selected_labels]

        action_cols = st.columns([0.7, 0.7, 1.6], gap="small")
        with action_cols[0]:
            if st.button("Delete selected calibration runs", use_container_width=True, disabled=not selected_records):
                deleted = delete_calibration_records([str(record.get("id")) for record in selected_records])
                st.success(f"Deleted {deleted} saved calibration runs.")
                st.rerun()
        with action_cols[1]:
            st.download_button(
                "Download calibration JSON",
                data=json.dumps({"runs": selected_records}, indent=2),
                file_name="calibration_compare.json",
                mime="application/json",
                use_container_width=True,
                disabled=not selected_records,
            )

        if not selected_records:
            st.info("Select one or more calibration runs to compare.")
            return

        compare_rows = []
        sample_frames = []
        for record in selected_records:
            reports = record.get("reports") or {}
            for method, report in reports.items():
                compare_rows.append(
                    {
                        "run": calibration_history_label(record),
                        "method": method,
                        "rows": record.get("n_rows"),
                        "n_checkpoints": len(record.get("checkpoints", [])),
                        "PICP_90": report.get("PICP_90"),
                        "MPIW": report.get("MPIW"),
                        "MAE": report.get("MAE"),
                        "RMSE": report.get("RMSE"),
                        "sharpness": report.get("sharpness"),
                    }
                )
            for rows in (record.get("samples") or {}).values():
                frame = pd.DataFrame(rows)
                if frame.empty:
                    continue
                frame["run"] = calibration_history_label(record)
                sample_frames.append(frame)

        compare_df = pd.DataFrame(compare_rows)
        render_dataframe(compare_df, use_container_width=True, hide_index=True)

        summary_left, summary_right = st.columns([1.0, 1.0], gap="large")
        with summary_left:
            picp_fig = px.bar(
                compare_df,
                x="run",
                y="PICP_90",
                color="method",
                barmode="group",
                title="Coverage across saved calibration runs",
                height=480,
            )
            picp_fig.add_hline(y=0.9, line_dash="dash", line_color=palette["red"])
            picp_fig.update_xaxes(tickangle=28)
            st.plotly_chart(style_plot(picp_fig), use_container_width=True)
        with summary_right:
            tradeoff_fig = px.scatter(
                compare_df,
                x="MPIW",
                y="MAE",
                color="method",
                size="rows",
                hover_name="run",
                title="Calibration efficiency trade-off",
                height=480,
            )
            st.plotly_chart(style_plot(tradeoff_fig), use_container_width=True)

        if sample_frames:
            sample_df = pd.concat(sample_frames, ignore_index=True)
            detail_left, detail_right = st.columns([1.02, 0.98], gap="large")
            with detail_left:
                method_options = sorted(sample_df["method"].unique().tolist())
                compare_method = st.selectbox("Method overlay", method_options, key="calibration_history_method")
                method_df = sample_df[sample_df["method"] == compare_method].copy()
                parity = go.Figure()
                for run_label, run_df in method_df.groupby("run"):
                    parity.add_trace(
                        go.Scatter(
                            x=run_df["true_ln_x2"],
                            y=run_df["pred_ln_x2_mean"],
                            mode="markers",
                            name=run_label,
                            text=run_df["solute_smiles"].astype(str).str.slice(0, 24) + " in " + run_df["solvent_smiles"].astype(str).str.slice(0, 18),
                            hovertemplate="%{text}<br>true=%{x:.3f}<br>pred=%{y:.3f}<extra></extra>",
                        )
                    )
                axis_min = float(min(method_df["true_ln_x2"].min(), method_df["pred_ln_x2_mean"].min()))
                axis_max = float(max(method_df["true_ln_x2"].max(), method_df["pred_ln_x2_mean"].max()))
                parity.add_shape(type="line", x0=axis_min, y0=axis_min, x1=axis_max, y1=axis_max, line={"dash": "dash", "color": palette["slate"]})
                parity.update_layout(title=f"{compare_method} parity overlay", height=520, xaxis_title="true ln x₂", yaxis_title="predicted mean ln x₂")
                st.plotly_chart(style_plot(parity), use_container_width=True)
            with detail_right:
                width_fig = px.box(
                    sample_df,
                    x="method",
                    y="interval_width",
                    color="run",
                    points="all",
                    title="Interval width distribution by saved run",
                    height=520,
                )
                st.plotly_chart(style_plot(width_fig), use_container_width=True)
        return

    if workspace == "Run & inspect":
        if checkpoint_file.exists():
            ckpt = inspect_checkpoint(python_command, str(checkpoint_file), checkpoint_file.stat().st_mtime)
            with st.expander("Checkpoint inspector", expanded=False):
                if ckpt.get("error"):
                    st.error(ckpt["error"])
                else:
                    top_left, top_right = st.columns([0.8, 1.2], gap="large")
                    with top_left:
                        meta_rows = [
                            {"field": "node_feat_dim", "value": ckpt.get("node_feat_dim")},
                            {"field": "edge_feat_dim", "value": ckpt.get("edge_feat_dim")},
                            {"field": "metadata keys", "value": ", ".join(sorted((ckpt.get("metadata") or {}).keys())) or "—"},
                        ]
                        render_dataframe(pd.DataFrame(meta_rows), use_container_width=True, hide_index=True)
                    with top_right:
                        st.json(ckpt.get("config", {}))

        st.markdown("### Chemistry preview")
        preview_left, preview_right = st.columns(2, gap="large")
        with preview_left:
            with st.container(border=True):
                render_molecule_showcase(
                    solute,
                    title="Solute",
                    subtitle="Compact RDKit structure and atom graph preview before inference.",
                    svg_size=(440, 300),
                    graph_height=360,
                    compact=True,
                )
        with preview_right:
            with st.container(border=True):
                render_molecule_showcase(
                    solvent,
                    title="Solvent",
                    subtitle="The same chemistry parsing pipeline used in the architecture workspace and inference call.",
                    svg_size=(440, 300),
                    graph_height=360,
                    compact=True,
                )

    latest_payload = st.session_state.get("inference_last_payload")
    latest_meta = st.session_state.get("inference_last_meta", {})
    latest_record_path = st.session_state.get("inference_last_record_path")

    if submitted:
        if not checkpoint_file.exists():
            st.error(f"Checkpoint not found: {checkpoint_file}")
        elif selected_family not in {"tgnn_solv", "direct_gnn"}:
            st.error("The selected checkpoint is not supported by the inference workbench.")
        else:
            with st.spinner("Running model inference in the selected Python environment..."):
                if selected_family == "direct_gnn":
                    payload = run_direct_model_inference(
                        python_command,
                        str(checkpoint_file),
                        solute,
                        solvent,
                        float(temperature),
                        float(scan_tmin),
                        float(scan_tmax),
                        int(scan_points),
                    )
                else:
                    payload = run_model_inference(
                        python_command,
                        str(checkpoint_file),
                        solute,
                        solvent,
                        float(temperature),
                        float(scan_tmin),
                        float(scan_tmax),
                        int(scan_points),
                        bool(run_mc),
                        int(mc_samples),
                        bool(run_domain),
                        domain_csv,
                        int(domain_fit_rows),
                        float(domain_mahal_pct),
                        float(domain_tani_threshold),
                    )
            if payload.get("error"):
                st.error(payload["error"])
            else:
                record_path = save_inference_record(
                    checkpoint_path=str(checkpoint_file),
                    model_family=selected_family,
                    solute=solute,
                    solvent=solvent,
                    temperature=float(temperature),
                    scan_tmin=float(scan_tmin),
                    scan_tmax=float(scan_tmax),
                    scan_points=int(scan_points),
                    mc_samples=int(mc_samples),
                    run_mc=bool(run_mc),
                    reference_csv=reference_csv,
                    domain_csv=domain_csv,
                    run_domain=bool(run_domain),
                    payload=payload,
                )
                st.session_state["inference_last_payload"] = payload
                st.session_state["inference_last_meta"] = {
                    "checkpoint": str(checkpoint_file),
                    "model_family": selected_family,
                    "solute": solute,
                    "solvent": solvent,
                    "temperature": float(temperature),
                    "reference_csv": reference_csv,
                    "domain_csv": domain_csv,
                }
                st.session_state["inference_last_record_path"] = str(record_path)
                latest_payload = payload
                latest_meta = st.session_state["inference_last_meta"]
                latest_record_path = str(record_path)
                history_records = load_inference_history()
                st.success(f"Inference saved to {relative_label(record_path)}")

    if workspace == "History & compare":
        if not history_records:
            st.info("No inference runs have been saved yet. Run one pair first and it will appear here for later comparison.")
            return
        history_df = inference_history_frame(history_records)
        st.markdown("### Saved inference runs")
        render_dataframe(history_df, use_container_width=True, hide_index=True)

        labels = [inference_history_label(record) for record in history_records]
        default_labels = labels[:2]
        selected_labels = st.multiselect("Compare runs", labels, default=default_labels)
        selected_records = [history_records[labels.index(label)] for label in selected_labels]

        action_cols = st.columns([0.7, 0.7, 1.6], gap="small")
        with action_cols[0]:
            if st.button("Delete selected runs", use_container_width=True, disabled=not selected_records):
                deleted = delete_inference_records([str(record.get("id")) for record in selected_records])
                st.success(f"Deleted {deleted} saved runs.")
                st.rerun()
        with action_cols[1]:
            combined_payload = {"runs": selected_records}
            st.download_button(
                "Download compare JSON",
                data=json.dumps(combined_payload, indent=2),
                file_name="inference_compare.json",
                mime="application/json",
                use_container_width=True,
                disabled=not selected_records,
            )
        with action_cols[2]:
            st.markdown(
                """
                <div class="lab-callout">
                  The compare view is persistent across reruns. Every successful inference is stored under
                  <code>results/lab_runs/inference_history</code>, so the same systems can be revisited after new experiments or checkpoints land.
                </div>
                """,
                unsafe_allow_html=True,
            )

        if not selected_records:
            st.info("Select one or more saved runs to compare.")
            return

        compare_rows = []
        for record in selected_records:
            prediction = record.get("prediction", {})
            compare_rows.append(
                {
                    "run": inference_history_label(record),
                    "family": record.get("model_family", "tgnn_solv"),
                    "ln_x2": prediction.get("ln_x2"),
                    "x2": prediction.get("x2"),
                    "gamma_2": prediction.get("gamma_2"),
                    "Phi": prediction.get("Phi"),
                    "T_m": prediction.get("T_m"),
                    "dH_fus": prediction.get("dH_fus"),
                    "correction": prediction.get("correction"),
                    "gate": prediction.get("gate"),
                    "ood_confidence": (record.get("domain") or {}).get("confidence"),
                    "in_domain": (record.get("domain") or {}).get("in_domain"),
                }
            )
        compare_df = pd.DataFrame(compare_rows)

        compare_metric_cols = st.columns(4)
        with compare_metric_cols[0]:
            st.metric("Selected runs", str(len(selected_records)))
        with compare_metric_cols[1]:
            st.metric("Unique checkpoints", str(len({record.get("checkpoint") for record in selected_records})))
        with compare_metric_cols[2]:
            st.metric("Temperature span", f"{min(float(record.get('temperature', 0.0)) for record in selected_records):.1f}–{max(float(record.get('temperature', 0.0)) for record in selected_records):.1f} K")
        with compare_metric_cols[3]:
            ln_values = [float(record.get("prediction", {}).get("ln_x2", 0.0)) for record in selected_records]
            st.metric("ln x₂ spread", f"{max(ln_values) - min(ln_values):.3f}")

        summary_left, summary_right = st.columns([1.0, 1.0], gap="large")
        with summary_left:
            render_dataframe(compare_df, use_container_width=True, hide_index=True)
        with summary_right:
            decomp_rows = []
            for record in selected_records:
                prediction = record.get("prediction", {})
                if prediction.get("Phi") is not None:
                    decomp_rows.append({"run": inference_history_label(record), "term": "-Φ", "value": -float(prediction["Phi"])})
                if prediction.get("ln_gamma_2") is not None:
                    decomp_rows.append({"run": inference_history_label(record), "term": "-ln γ₂", "value": -float(prediction["ln_gamma_2"])})
                if prediction.get("correction") is not None:
                    decomp_rows.append({"run": inference_history_label(record), "term": "correction", "value": float(prediction["correction"])})
                if prediction.get("ln_x2") is not None:
                    decomp_rows.append({"run": inference_history_label(record), "term": "ln x₂", "value": float(prediction["ln_x2"])})
            if decomp_rows:
                decomp_fig = px.bar(
                    pd.DataFrame(decomp_rows),
                    x="term",
                    y="value",
                    color="run",
                    barmode="group",
                    title="Prediction term comparison across saved runs",
                    height=460,
                )
                st.plotly_chart(style_plot(decomp_fig), use_container_width=True)
            else:
                st.info("No comparable prediction-term decomposition is available for the selected runs.")

        overlay_left, overlay_right = st.columns([1.05, 0.95], gap="large")
        with overlay_left:
            scan_overlay = go.Figure()
            for record in selected_records:
                scan_df = pd.DataFrame(record.get("scan", []))
                if scan_df.empty:
                    continue
                scan_overlay.add_trace(
                    go.Scatter(
                        x=scan_df["T"],
                        y=scan_df["ln_x2"],
                        mode="lines+markers",
                        name=inference_history_label(record),
                    )
                )
            scan_overlay.update_layout(
                title="Temperature-scan overlay",
                height=520,
                xaxis_title="Temperature (K)",
                yaxis_title="ln x₂",
                legend={"orientation": "h", "y": 1.1},
            )
            st.plotly_chart(style_plot(scan_overlay), use_container_width=True)
        with overlay_right:
            solver_overlay = go.Figure()
            solver_added = False
            for record in selected_records:
                scan_df = pd.DataFrame(record.get("scan", []))
                if scan_df.empty or "x_ideal" not in scan_df.columns:
                    continue
                minus_phi = np.log(np.clip(scan_df["x_ideal"], 1e-12, None))
                solver_overlay.add_trace(
                    go.Scatter(
                        x=scan_df["T"],
                        y=minus_phi,
                        mode="lines",
                        name=f"-Φ · {short_smiles_label(str(record.get('solute_smiles', '')), 12)}",
                    )
                )
                solver_added = True
            if solver_added:
                solver_overlay.update_layout(
                    title="Crystal-demand overlay",
                    height=520,
                    xaxis_title="Temperature (K)",
                    yaxis_title="-Φ",
                    legend={"orientation": "h", "y": 1.1},
                )
                st.plotly_chart(style_plot(solver_overlay), use_container_width=True)
            else:
                st.info("Crystal-demand overlays are only available for TGNN-Solv runs with solver terms.")

        focus_labels = [inference_history_label(record) for record in selected_records]
        focus_label = st.selectbox(
            "Inspect one saved run",
            focus_labels,
            key="inference_history_focus_record",
        )
        focus_record = selected_records[focus_labels.index(focus_label)] if focus_labels else None
        if focus_record is not None:
            focus_left, focus_right = st.columns([1.0, 1.0], gap="large")
            with focus_left:
                with st.expander("Saved interpretation", expanded=True):
                    st.code(str(focus_record.get("interpretation", "")))
            with focus_right:
                with st.expander("Saved payload", expanded=False):
                    st.json(
                        {
                            "prediction": focus_record.get("prediction", {}),
                            "config": focus_record.get("config", {}),
                            "scan_points": focus_record.get("scan_points"),
                            "path": relative_label(Path(str(focus_record.get("_path", "")))),
                        }
                    )
        return

    if not latest_payload:
        st.info("Run inference once to populate the detailed workbench and the persistent comparison history.")
        return

    payload = latest_payload
    result = payload["prediction"]
    scan_df = pd.DataFrame(payload["scan"])
    model_family = str(
        payload.get("model_family")
        or result.get("model_family")
        or latest_meta.get("model_family")
        or "tgnn_solv"
    )

    if latest_record_path:
        st.caption(f"Latest saved run: {relative_label(Path(str(latest_record_path)))}")

    if model_family == "direct_gnn":
        metric_cols = st.columns(5)
        metric_values = [
            ("x₂", f"{result['x2']:.5f}", "mole fraction"),
            ("ln x₂", f"{result['ln_x2']:.3f}", "direct prediction"),
            ("Morgan path", "on" if result.get("uses_morgan") else "off", "feature side path"),
            ("Descriptors", "on" if result.get("uses_descriptors") else "off", "RDKit augmentation"),
            ("Family", "DirectGNN", "matched no-physics baseline"),
        ]
        for col, (label, value, caption) in zip(metric_cols, metric_values):
            with col:
                st.metric(label, value, help=caption)

        explainer_left, explainer_right = st.columns([1.0, 1.0], gap="large")
        with explainer_left:
            st.markdown(
                """
                <div class="lab-workspace-panel">
                  <h4>Direct baseline reading</h4>
                  <p>
                    This checkpoint uses the matched graph backbone, but predicts <code>ln(x₂)</code> directly.
                    There is no NRTL head, no SLE fixed-point solve, and no bounded correction branch, so this
                    view focuses on final predictions, temperature trends, and chemical context rather than
                    physics-term decomposition.
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with explainer_right:
            st.markdown("### Descriptor context")
            desc_cols = st.columns(2)
            with desc_cols[0]:
                st.json(descriptor_summary(latest_meta.get("solute", solute)) or {})
            with desc_cols[1]:
                st.json(descriptor_summary(latest_meta.get("solvent", solvent)) or {})

        panel = segmented_choice(
            "Inference panel",
            ["Prediction", "Temperature scan", "Chemical context", "Report & raw payload"],
            key="direct_inference_panel",
            default="Prediction",
        )
        if panel == "Prediction":
            pred_left, pred_right = st.columns([1.05, 0.95], gap="large")
            with pred_left:
                bar_df = pd.DataFrame(
                    [
                        {"metric": "ln x₂", "value": float(result["ln_x2"])},
                        {"metric": "x₂", "value": float(result["x2"])},
                    ]
                )
                fig = px.bar(bar_df, x="metric", y="value", color="metric", title="Direct prediction summary", height=460)
                st.plotly_chart(style_plot(fig), use_container_width=True)
            with pred_right:
                render_dataframe(
                    pd.DataFrame(
                        [
                            {"field": "family", "value": "DirectGNN"},
                            {"field": "solute", "value": result["solute"]},
                            {"field": "solvent", "value": result["solvent"]},
                            {"field": "temperature", "value": f"{float(result['T']):.2f} K"},
                            {"field": "uses_morgan", "value": bool(result.get("uses_morgan"))},
                            {"field": "uses_descriptors", "value": bool(result.get("uses_descriptors"))},
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
        elif panel == "Temperature scan":
            scan_left, scan_right = st.columns([1.05, 0.95], gap="large")
            with scan_left:
                scan_fig = go.Figure()
                scan_fig.add_trace(go.Scatter(x=scan_df["T"], y=scan_df["ln_x2"], mode="lines+markers", name="ln x₂"))
                scan_fig.add_trace(go.Scatter(x=scan_df["T"], y=scan_df["x2"], mode="lines", name="x₂", yaxis="y2"))
                scan_fig.update_layout(
                    title="DirectGNN temperature scan",
                    height=560,
                    yaxis={"title": "ln x₂"},
                    yaxis2={"title": "x₂", "overlaying": "y", "side": "right"},
                    xaxis={"title": "Temperature (K)"},
                    legend={"orientation": "h", "y": 1.08},
                )
                st.plotly_chart(style_plot(scan_fig), use_container_width=True)
            with scan_right:
                slope_df = scan_df.copy()
                slope_df["d_ln_x2"] = slope_df["ln_x2"].diff().fillna(0.0)
                slope_fig = px.bar(slope_df, x="T", y="d_ln_x2", title="Stepwise change across temperature scan", height=560)
                st.plotly_chart(style_plot(slope_fig), use_container_width=True)
                dl_left, dl_right = st.columns(2)
                with dl_left:
                    st.download_button(
                        "Download scan CSV",
                        data=scan_df.to_csv(index=False),
                        file_name="directgnn_temperature_scan.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                with dl_right:
                    st.download_button(
                        "Download inference JSON",
                        data=json.dumps(payload, indent=2),
                        file_name="directgnn_inference.json",
                        mime="application/json",
                        use_container_width=True,
                    )
        elif panel == "Chemical context":
            ref_path = Path(latest_meta.get("reference_csv", reference_csv))
            if ref_path.exists() and Chem is not None and AllChem is not None:
                fp_index = cached_fp_index(str(ref_path))
                sol_sim, sol_match = nearest_similarity(latest_meta.get("solute", solute), fp_index["solute_fps"], fp_index["solute_smiles"])
                slv_sim, slv_match = nearest_similarity(latest_meta.get("solvent", solvent), fp_index["solvent_fps"], fp_index["solvent_smiles"])
                context_left, context_right = st.columns([0.9, 1.1], gap="large")
                with context_left:
                    sim_df = pd.DataFrame(
                        [
                            {"role": "solute", "nearest_tanimoto": sol_sim},
                            {"role": "solvent", "nearest_tanimoto": slv_sim},
                        ]
                    )
                    fig = px.bar(sim_df, x="role", y="nearest_tanimoto", range_y=[0, 1], color="role", title="Nearest training similarity", height=420)
                    st.plotly_chart(style_plot(fig), use_container_width=True)
                with context_right:
                    render_dataframe(
                        pd.DataFrame(
                            [
                                {"role": "solute", "nearest_tanimoto": sol_sim, "nearest_smiles": sol_match},
                                {"role": "solvent", "nearest_tanimoto": slv_sim, "nearest_smiles": slv_match},
                            ]
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.info("Nearest-neighbor similarity is unavailable because RDKit or the reference CSV is missing.")
        else:
            report_left, report_right = st.columns([1.0, 1.0], gap="large")
            with report_left:
                st.code(str(payload.get("interpretation", "")))
            with report_right:
                st.json(payload)
        return

    scan_terms = scan_df.copy()
    scan_terms["minus_phi"] = np.log(np.clip(scan_terms["x_ideal"], 1e-12, None))
    scan_terms["minus_ln_gamma"] = -np.log(np.clip(scan_terms["gamma_2"], 1e-12, None))

    metric_cols = st.columns(6)
    metric_values = [
        ("x₂", f"{result['x2']:.5f}", "mole fraction"),
        ("ln x₂", f"{result['ln_x2']:.3f}", "final prediction"),
        ("γ₂", f"{result['gamma_2']:.3f}", "activity coefficient"),
        ("Φ", f"{result['Phi']:.3f}", "crystal penalty"),
        ("Tₘ", f"{result['T_m']:.1f} K", "predicted melting point"),
        ("ΔHfus", f"{result['dH_fus']:.0f} J/mol", "fusion enthalpy"),
    ]
    for col, (label, value, caption) in zip(metric_cols, metric_values):
        with col:
            st.metric(label, value, help=caption)

    explainer_left, explainer_right = st.columns([1.0, 1.0], gap="large")
    with explainer_left:
        crystal_share = abs(result["Phi"]) / max(abs(result["Phi"]) + abs(result["ln_gamma_2"]), 1e-8)
        st.markdown(
            f"""
            <div class="lab-workspace-panel">
              <h4>Physical reading</h4>
              <p>
                The crystal-side penalty contributes roughly <strong>{100 * crystal_share:.0f}%</strong> of the raw log-solubility magnitude,
                while the interaction term contributes <strong>{100 * (1 - crystal_share):.0f}%</strong>. The learned correction then nudges
                the solver output by <strong>{result['correction']:.3f}</strong> through a gate of <strong>{result['gate']:.3f}</strong>.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with explainer_right:
        st.markdown("### Descriptor context")
        desc_cols = st.columns(2)
        with desc_cols[0]:
            st.json(descriptor_summary(latest_meta.get("solute", solute)) or {})
        with desc_cols[1]:
            st.json(descriptor_summary(latest_meta.get("solvent", solvent)) or {})

    if payload.get("domain_error"):
        st.warning(f"Applicability-domain scoring failed: {payload['domain_error']}")

    panel = segmented_choice(
        "Inference panel",
        ["Decomposition", "Temperature scan", "Chemical context", "Domain & OOD", "Report & raw payload"],
        key="inference_panel",
        default="Decomposition",
    )
    if panel == "Decomposition":
        left, right = st.columns([1.08, 0.92], gap="large")
        with left:
            waterfall = go.Figure(
                go.Waterfall(
                    x=["-Φ", "-ln γ₂", "correction", "ln x₂"],
                    measure=["relative", "relative", "relative", "total"],
                    y=[-result["Phi"], -result["ln_gamma_2"], result["correction"], 0],
                    connector={"line": {"color": palette["slate"]}},
                )
            )
            waterfall.update_layout(title="Log-solubility decomposition", height=520)
            st.plotly_chart(style_plot(waterfall), use_container_width=True)
        with right:
            hansen_fig = go.Figure()
            hansen_axes = ["δd", "δp", "δh", "δd"]
            hansen_fig.add_trace(
                go.Scatterpolar(r=result["hansen_sol"] + [result["hansen_sol"][0]], theta=hansen_axes, fill="toself", name="solute")
            )
            hansen_fig.add_trace(
                go.Scatterpolar(r=result["hansen_slv"] + [result["hansen_slv"][0]], theta=hansen_axes, fill="toself", name="solvent")
            )
            hansen_fig.update_layout(title="Hansen parameter overlap", height=520)
            st.plotly_chart(style_plot(hansen_fig), use_container_width=True)

        extras = st.columns(4)
        with extras[0]:
            st.metric("Ra", f"{result['Ra']:.2f}")
        with extras[1]:
            st.metric("Correction", f"{result['correction']:.3f}")
        with extras[2]:
            st.metric("Gate", f"{result['gate']:.3f}")
        with extras[3]:
            st.metric("Ideal x₂", f"{result['x_ideal']:.5f}")

    elif panel == "Temperature scan":
        scan_left, scan_right = st.columns([1.05, 0.95], gap="large")
        with scan_left:
            scan_fig = go.Figure()
            scan_fig.add_trace(go.Scatter(x=scan_df["T"], y=scan_df["ln_x2"], mode="lines+markers", name="ln x₂"))
            scan_fig.add_trace(
                go.Scatter(
                    x=scan_df["T"],
                    y=np.log(np.clip(scan_df["x_ideal"], 1e-12, None)),
                    mode="lines",
                    name="ln x₂ ideal",
                )
            )
            scan_fig.add_trace(
                go.Scatter(
                    x=scan_df["T"],
                    y=scan_df["correction"],
                    mode="lines",
                    name="correction",
                    yaxis="y2",
                )
            )
            scan_fig.update_layout(
                title="Temperature scan",
                height=560,
                yaxis={"title": "ln x₂"},
                yaxis2={"title": "correction", "overlaying": "y", "side": "right"},
                xaxis={"title": "Temperature (K)"},
                legend={"orientation": "h", "y": 1.08},
            )
            st.plotly_chart(style_plot(scan_fig), use_container_width=True)
        with scan_right:
            term_fig = go.Figure()
            term_fig.add_trace(go.Scatter(x=scan_terms["T"], y=scan_terms["minus_phi"], mode="lines", name="-Φ"))
            term_fig.add_trace(go.Scatter(x=scan_terms["T"], y=scan_terms["minus_ln_gamma"], mode="lines", name="-ln γ₂"))
            term_fig.add_trace(go.Scatter(x=scan_terms["T"], y=scan_terms["correction"], mode="lines", name="correction"))
            term_fig.update_layout(
                title="Solver term trends across temperature",
                height=560,
                xaxis_title="Temperature (K)",
                yaxis_title="log contribution",
            )
            st.plotly_chart(style_plot(term_fig), use_container_width=True)

            dl_left, dl_right = st.columns(2)
            with dl_left:
                st.download_button(
                    "Download scan CSV",
                    data=scan_df.to_csv(index=False),
                    file_name="tgnn_temperature_scan.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with dl_right:
                st.download_button(
                    "Download inference JSON",
                    data=json.dumps(payload, indent=2),
                    file_name="tgnn_inference.json",
                    mime="application/json",
                    use_container_width=True,
                )

    elif panel == "Chemical context":
        ref_path = Path(latest_meta.get("reference_csv", reference_csv))
        if ref_path.exists() and Chem is not None and AllChem is not None:
            fp_index = cached_fp_index(str(ref_path))
            sol_sim, sol_match = nearest_similarity(latest_meta.get("solute", solute), fp_index["solute_fps"], fp_index["solute_smiles"])
            slv_sim, slv_match = nearest_similarity(latest_meta.get("solvent", solvent), fp_index["solvent_fps"], fp_index["solvent_smiles"])
            context_left, context_right = st.columns([0.9, 1.1], gap="large")
            with context_left:
                sim_df = pd.DataFrame(
                    [
                        {"role": "solute", "nearest_tanimoto": sol_sim},
                        {"role": "solvent", "nearest_tanimoto": slv_sim},
                    ]
                )
                fig = px.bar(sim_df, x="role", y="nearest_tanimoto", range_y=[0, 1], color="role", title="Nearest training similarity", height=420)
                st.plotly_chart(style_plot(fig), use_container_width=True)
            with context_right:
                render_dataframe(
                    pd.DataFrame(
                        [
                            {"role": "solute", "nearest_tanimoto": sol_sim, "nearest_smiles": sol_match},
                            {"role": "solvent", "nearest_tanimoto": slv_sim, "nearest_smiles": slv_match},
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("Nearest-neighbor similarity is unavailable because RDKit or the reference CSV is missing.")

        if payload.get("mc_dropout"):
            mc_result = payload["mc_dropout"]
            mc_cols = st.columns(4)
            mc_metrics = [
                ("ln x₂ mean", f"{mc_result['ln_x2_mean']:.3f}", f"std {mc_result['ln_x2_std']:.3f}"),
                ("x₂ mean", f"{mc_result['x2_mean']:.5f}", f"std {mc_result['x2_std']:.5f}"),
                ("γ₂ mean", f"{mc_result['gamma_2_mean']:.3f}", f"std {mc_result['gamma_2_std']:.3f}"),
                ("Tₘ mean", f"{mc_result['T_m_mean']:.1f} K", f"std {mc_result['T_m_std']:.1f}"),
            ]
            for col, (label, value, delta) in zip(mc_cols, mc_metrics):
                with col:
                    st.metric(label, value, delta=delta)

    elif panel == "Domain & OOD":
        domain_payload = payload.get("domain") or {}
        if not domain_payload:
            st.info("OOD scoring was not run for this inference. Enable applicability-domain scoring in Advanced settings and run again.")
        else:
            verdict = "In domain" if domain_payload.get("in_domain") else "Potentially OOD"
            verdict_color = palette["green"] if domain_payload.get("in_domain") else palette["red"]
            st.markdown(
                f"""
                <div class="lab-workspace-panel">
                  <h4 style="margin-bottom:0.2rem;">Applicability-domain verdict</h4>
                  <p style="margin-bottom:0.85rem;">
                    Interactive OOD scoring uses the maintained <code>tgnn_solv.domain</code> logic on a sampled fit of the selected training split.
                    That keeps the GUI responsive while preserving the same Mahalanobis-plus-Tanimoto decision path as the library helper.
                  </p>
                  <div class="lab-kicker-row">
                    <span class="lab-kicker" style="{accent_pill_style(verdict_color)}">{verdict}</span>
                    <span class="lab-kicker">fit rows: {int(domain_payload.get("fit_rows", 0)):,}</span>
                    <span class="lab-kicker">sampled: {"yes" if domain_payload.get("sampled") else "no"}</span>
                    <span class="lab-kicker">CSV: {escape(relative_label(Path(str(domain_payload.get("train_csv", latest_meta.get("domain_csv", domain_csv))))))}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            ood_cols = st.columns(5)
            metrics = [
                ("Confidence", f"{float(domain_payload.get('confidence', 0.0)):.2f}"),
                ("Mahalanobis", f"{float(domain_payload.get('mahalanobis', 0.0)):.2f}"),
                ("Cutoff", f"{float(domain_payload.get('mahalanobis_cutoff', 0.0)):.2f}"),
                ("Tanimoto solute", f"{float(domain_payload.get('tanimoto_solute', 0.0)):.2f}"),
                ("Tanimoto solvent", f"{float(domain_payload.get('tanimoto_solvent', 0.0)):.2f}"),
            ]
            for col, (label, value) in zip(ood_cols, metrics):
                with col:
                    st.metric(label, value)

            chart_left, chart_right = st.columns([0.92, 1.08], gap="large")
            with chart_left:
                gauge = go.Figure()
                gauge.add_trace(
                    go.Indicator(
                        mode="gauge+number",
                        value=float(domain_payload.get("confidence", 0.0)),
                        title={"text": "OOD confidence"},
                        gauge={
                            "axis": {"range": [0, 1]},
                            "bar": {"color": palette["blue"]},
                            "steps": [
                                {"range": [0, 0.35], "color": hex_to_rgba(palette["red"], 0.24)},
                                {"range": [0.35, 0.65], "color": hex_to_rgba(palette["orange"], 0.24)},
                                {"range": [0.65, 1.0], "color": hex_to_rgba(palette["green"], 0.24)},
                            ],
                        },
                    )
                )
                gauge.update_layout(height=420, margin=dict(l=24, r=24, t=40, b=20))
                st.plotly_chart(style_plot(gauge), use_container_width=True)
            with chart_right:
                comparison = pd.DataFrame(
                    [
                        {"metric": "Mahalanobis", "value": float(domain_payload.get("mahalanobis", 0.0)), "threshold": float(domain_payload.get("mahalanobis_cutoff", 0.0))},
                        {"metric": "Tanimoto solute", "value": float(domain_payload.get("tanimoto_solute", 0.0)), "threshold": float(domain_payload.get("tani_threshold", domain_tani_threshold))},
                        {"metric": "Tanimoto solvent", "value": float(domain_payload.get("tanimoto_solvent", 0.0)), "threshold": float(domain_payload.get("tani_threshold", domain_tani_threshold))},
                    ]
                )
                domain_fig = go.Figure()
                domain_fig.add_trace(go.Bar(x=comparison["metric"], y=comparison["value"], name="value", marker_color=palette["blue"]))
                domain_fig.add_trace(go.Scatter(x=comparison["metric"], y=comparison["threshold"], mode="markers+lines", name="threshold", marker=dict(color=palette["red"], size=10)))
                domain_fig.update_layout(title="Domain criteria vs thresholds", height=420, yaxis_title="score")
                st.plotly_chart(style_plot(domain_fig), use_container_width=True)

            exact_cols = st.columns(2)
            with exact_cols[0]:
                st.metric("Exact solute seen", "Yes" if domain_payload.get("solute_seen") else "No")
            with exact_cols[1]:
                st.metric("Exact solvent seen", "Yes" if domain_payload.get("solvent_seen") else "No")

            with st.expander("Applicability-domain report", expanded=True):
                st.code(payload.get("domain_report", ""))

    else:
        with st.expander("Interpretation report", expanded=True):
            st.code(payload["interpretation"])
        with st.expander("Raw inference payload", expanded=False):
            raw_payload = {
                "prediction": result,
                "scan": payload["scan"],
                "config": payload.get("config", {}),
                "domain": payload.get("domain"),
            }
            st.json(raw_payload)


def render_applications_page(python_command: str, probe: dict[str, Any]) -> None:
    checkpoints = available_checkpoints()
    page_header(
        "Applications & Translation",
        "Route-level solvent screening, solvent-swap stress tests, and honest developability readouts built on the maintained inference stack. This workspace translates TGNN-Solv from model benchmarking into process and formulation decisions without pretending that solubility alone is full PK/PD.",
        eyebrow="Applications",
        chips=[
            ("Checkpoints", str(len(checkpoints))),
            ("Screening library", str(len(BUILTIN_SOLVENT_LIBRARY) if BUILTIN_SOLVENT_LIBRARY else 0)),
            ("Synthesis library", str(len(SYNTHESIS_SOLVENT_LIBRARY))),
            ("Pharma media", str(len(PHARMA_MEDIA_LIBRARY))),
            ("Runtime", probe.get("python", python_command)),
        ],
    )
    if not checkpoints:
        st.warning("No checkpoints were found under checkpoints/.")
        return
    if not module_ok(probe, "tgnn_solv.inference"):
        st.error("The selected interpreter cannot import `tgnn_solv.inference`. Fix the runtime on the Environment page first.")
        return

    supported_checkpoints, rejected_checkpoints = workbench_compatible_checkpoints(python_command, checkpoints)
    if not supported_checkpoints:
        st.error("No supported TGNN-Solv or DirectGNN checkpoints are available for the applications workspace.")
        if rejected_checkpoints:
            render_dataframe(
                pd.DataFrame([{"checkpoint": relative_label(path), "reason": reason} for path, reason in rejected_checkpoints]),
                use_container_width=True,
                hide_index=True,
            )
        return

    workspace = segmented_choice(
        "Applications workspace",
        ["Process optimization", "Solvent screening", "Synthesis route screening", "Drug developability", "PK solubility profile", "Solvent swap"],
        key="applications_workspace",
        default="Process optimization",
    )
    default_checkpoint = CHECKPOINTS_DIR / "tgnn_solv_trained.pt"
    if default_checkpoint not in supported_checkpoints:
        default_checkpoint = supported_checkpoints[0]

    if workspace == "Process optimization":
        pending_process_cryst_solute = st.session_state.pop("applications_process_cryst_solute_input_pending", None)
        if pending_process_cryst_solute is not None:
            st.session_state["applications_process_cryst_solute"] = pending_process_cryst_solute
            st.session_state["applications_process_cryst_solute_input"] = pending_process_cryst_solute
        pending_process_extract_solute = st.session_state.pop("applications_process_extract_solute_input_pending", None)
        if pending_process_extract_solute is not None:
            st.session_state["applications_process_extract_solute"] = pending_process_extract_solute
            st.session_state["applications_process_extract_solute_input"] = pending_process_extract_solute
        pending_process_rxn_product = st.session_state.pop("applications_process_rxn_product_input_pending", None)
        if pending_process_rxn_product is not None:
            st.session_state["applications_process_rxn_product"] = pending_process_rxn_product
            st.session_state["applications_process_rxn_product_input"] = pending_process_rxn_product
        builtin_solvent_map = {str(entry["name"]): str(entry["smiles"]) for entry in BUILTIN_SOLVENT_LIBRARY}
        process_mode = segmented_choice(
            "Optimization mode",
            ["Crystallization", "Extraction", "Reaction medium"],
            key="applications_process_mode",
            default="Crystallization",
        )
        left, right = st.columns([1.02, 0.98], gap="large")
        with left:
            checkpoint_path = render_path_select("Checkpoint", supported_checkpoints, default_checkpoint, "applications_process_checkpoint")
            if process_mode == "Crystallization":
                solute_smiles = st.text_input(
                    "Target solute SMILES",
                    value=st.session_state.get("applications_process_cryst_solute", DEFAULT_SOLUTE_SMILES),
                    key="applications_process_cryst_solute_input",
                )
                temp_window = st.slider(
                    "Search temperature window (K)",
                    min_value=273,
                    max_value=400,
                    value=(273, 360),
                    step=1,
                    key="applications_process_cryst_window",
                )
                target_yield = float(
                    st.slider(
                        "Target yield",
                        min_value=0.10,
                        max_value=0.98,
                        value=0.80,
                        step=0.01,
                        key="applications_process_cryst_target_yield",
                    )
                )
                c1, c2, c3, c4 = st.columns(4, gap="small")
                with c1:
                    min_green = int(st.slider("Min green", 1, 10, 5, 1, key="applications_process_cryst_green"))
                with c2:
                    max_tox = int(st.slider("Max tox severity", 1, 3, 2, 1, key="applications_process_cryst_tox"))
                with c3:
                    min_dissolve = float(st.number_input("Min hot mg/mL", min_value=0.0, max_value=500.0, value=2.0, step=0.5, key="applications_process_cryst_dissolve"))
                with c4:
                    max_bp = float(st.number_input("Max bp (K)", min_value=300.0, max_value=700.0, value=450.0, step=5.0, key="applications_process_cryst_bp"))
                if st.button("Run crystallization optimization", key="applications_process_cryst_run", use_container_width=True):
                    canonical_solute, error = canonicalize_smiles(solute_smiles)
                    if not canonical_solute:
                        st.session_state["applications_process_result"] = {"error": error or "Invalid solute SMILES."}
                    else:
                        st.session_state["applications_process_cryst_solute"] = canonical_solute
                        st.session_state["applications_process_cryst_solute_input_pending"] = canonical_solute
                        st.session_state["applications_process_result"] = run_process_optimization_analysis(
                            python_command,
                            checkpoint_path,
                            "crystallization",
                            json.dumps(
                                {
                                    "solute_smiles": canonical_solute,
                                    "target_yield": target_yield,
                                    "T_min": float(temp_window[0]),
                                    "T_max": float(temp_window[1]),
                                    "constraints": {
                                        "min_green_score": min_green,
                                        "max_toxicity_class": max_tox,
                                        "min_dissolving_concentration_mg_mL": min_dissolve,
                                        "max_boiling_point_K": max_bp,
                                    },
                                }
                            ),
                        )
                        st.rerun()
            elif process_mode == "Extraction":
                solute_smiles = st.text_input(
                    "Target solute SMILES",
                    value=st.session_state.get("applications_process_extract_solute", DEFAULT_SOLUTE_SMILES),
                    key="applications_process_extract_solute_input",
                )
                source_options = list(builtin_solvent_map.keys())
                default_source = "Water" if "Water" in builtin_solvent_map else source_options[0]
                source_label = st.selectbox("Source solvent", options=source_options, index=source_options.index(default_source), key="applications_process_extract_source")
                temperature = float(st.number_input("Extraction temperature (K)", min_value=250.0, max_value=400.0, value=298.15, step=1.0, key="applications_process_extract_T"))
                c1, c2, c3, c4 = st.columns(4, gap="small")
                with c1:
                    min_green = int(st.slider("Min green", 1, 10, 4, 1, key="applications_process_extract_green"))
                with c2:
                    max_tox = int(st.slider("Max tox severity", 1, 3, 2, 1, key="applications_process_extract_tox"))
                with c3:
                    min_part = float(st.number_input("Min partition K", min_value=1.0, max_value=1000.0, value=3.0, step=0.5, key="applications_process_extract_partition"))
                with c4:
                    max_bp = float(st.number_input("Max bp (K)", min_value=300.0, max_value=700.0, value=420.0, step=5.0, key="applications_process_extract_bp"))
                if st.button("Run extraction optimization", key="applications_process_extract_run", use_container_width=True):
                    canonical_solute, error = canonicalize_smiles(solute_smiles)
                    if not canonical_solute:
                        st.session_state["applications_process_result"] = {"error": error or "Invalid solute SMILES."}
                    else:
                        st.session_state["applications_process_extract_solute"] = canonical_solute
                        st.session_state["applications_process_extract_solute_input_pending"] = canonical_solute
                        st.session_state["applications_process_result"] = run_process_optimization_analysis(
                            python_command,
                            checkpoint_path,
                            "extraction",
                            json.dumps(
                                {
                                    "solute_smiles": canonical_solute,
                                    "source_solvent": builtin_solvent_map[source_label],
                                    "temperature": temperature,
                                    "constraints": {
                                        "min_green_score": min_green,
                                        "max_toxicity_class": max_tox,
                                        "min_partition_coefficient": min_part,
                                        "max_boiling_point_K": max_bp,
                                    },
                                }
                            ),
                        )
                        st.rerun()
            else:
                reactants_text = st.text_area(
                    "Reactant SMILES",
                    value=st.session_state.get("applications_process_rxn_reactants", "CCO\nCCN"),
                    height=120,
                    key="applications_process_rxn_reactants",
                )
                product_smiles = st.text_input(
                    "Product SMILES",
                    value=st.session_state.get("applications_process_rxn_product", "CC(=O)O"),
                    key="applications_process_rxn_product_input",
                )
                temperature = float(st.number_input("Reaction temperature (K)", min_value=250.0, max_value=450.0, value=298.15, step=1.0, key="applications_process_rxn_T"))
                c1, c2, c3, c4 = st.columns(4, gap="small")
                with c1:
                    min_green = int(st.slider("Min green", 1, 10, 5, 1, key="applications_process_rxn_green"))
                with c2:
                    max_tox = int(st.slider("Max tox severity", 1, 3, 2, 1, key="applications_process_rxn_tox"))
                with c3:
                    min_react = float(st.number_input("Min reactant mg/mL", min_value=0.0, max_value=500.0, value=1.0, step=0.5, key="applications_process_rxn_react"))
                with c4:
                    min_selectivity = float(st.number_input("Min selectivity ratio", min_value=0.1, max_value=1000.0, value=2.0, step=0.5, key="applications_process_rxn_selectivity"))
                if st.button("Run reaction-medium optimization", key="applications_process_rxn_run", use_container_width=True):
                    reactants: list[str] = []
                    issues: list[str] = []
                    for token in re.split(r"[,\n;]+", reactants_text):
                        raw = token.strip()
                        if not raw:
                            continue
                        canonical, error = canonicalize_smiles(raw)
                        if canonical:
                            reactants.append(canonical)
                        elif error:
                            issues.append(error)
                    canonical_product, product_error = canonicalize_smiles(product_smiles)
                    if not reactants:
                        st.session_state["applications_process_result"] = {"error": "Provide at least one valid reactant SMILES."}
                    elif not canonical_product:
                        st.session_state["applications_process_result"] = {"error": product_error or "Invalid product SMILES."}
                    else:
                        st.session_state["applications_process_rxn_product"] = canonical_product
                        st.session_state["applications_process_rxn_product_input_pending"] = canonical_product
                        st.session_state["applications_process_result"] = run_process_optimization_analysis(
                            python_command,
                            checkpoint_path,
                            "reaction_medium",
                            json.dumps(
                                {
                                    "reactants": reactants,
                                    "product_smiles": canonical_product,
                                    "temperature": temperature,
                                    "constraints": {
                                        "min_green_score": min_green,
                                        "max_toxicity_class": max_tox,
                                        "min_reactant_solubility_mg_mL": min_react,
                                        "min_selectivity_ratio": min_selectivity,
                                    },
                                }
                            ),
                        )
                        if issues:
                            st.warning("Some reactants were skipped: " + "; ".join(issues))
                        st.rerun()

        with right:
            if process_mode == "Crystallization":
                render_molecule_showcase(
                    st.session_state.get("applications_process_cryst_solute", DEFAULT_SOLUTE_SMILES),
                    title="Crystallization target",
                    subtitle="Search operating windows over solvent identity and hot/cold endpoints, subject to dissolution, safety, and operability constraints.",
                    svg_size=(520, 320),
                    graph_height=360,
                    compact=True,
                )
            elif process_mode == "Extraction":
                render_molecule_showcase(
                    st.session_state.get("applications_process_extract_solute", DEFAULT_SOLUTE_SMILES),
                    title="Extraction target",
                    subtitle="Rank candidate extraction solvents by partition leverage against the source solvent, while preferring immiscibility and easy solvent removal.",
                    svg_size=(520, 320),
                    graph_height=360,
                    compact=True,
                )
            else:
                render_molecule_showcase(
                    st.session_state.get("applications_process_rxn_product", "CC(=O)O"),
                    title="Reaction product target",
                    subtitle="Look for media that dissolve the reactants but keep the target product comparatively less soluble to aid equilibrium or in situ precipitation.",
                    svg_size=(520, 320),
                    graph_height=360,
                    compact=True,
                )
            info_card(
                "Pareto view",
                "The optimizer returns simple screening heuristics rather than rigorous process economics. Use the scatter plots as a process-facing trade-off map, not as a closed-form optimum proof.",
            )
            info_card(
                "Temperature scans",
                "After ranking, inspect the top solvent through explicit temperature scans to see whether the recommendation is robust or only local to one operating point.",
            )

        process_payload = st.session_state.get("applications_process_result")
        if process_payload:
            if process_payload.get("error"):
                st.error(process_payload["error"])
            else:
                result_mode = str(process_payload.get("mode", "")).lower()
                if result_mode == "crystallization":
                    rows = process_payload.get("result", []) or []
                    rows_df = pd.DataFrame(rows)
                    if rows_df.empty:
                        st.warning("No crystallization solutions satisfied the current constraints.")
                    else:
                        top_row = rows_df.iloc[0]
                        render_stat_tiles(
                            [
                                ("Top solvent", str(top_row.get("solvent_name", "—")), "best ranked candidate"),
                                ("Best yield", f"{100.0 * float(top_row.get('yield', 0.0)):.1f}%", "equilibrium capture"),
                                ("Hot / cold", f"{float(top_row.get('T_hot', 0.0)):.0f} / {float(top_row.get('T_cold', 0.0)):.0f} K", "selected endpoints"),
                                ("Model family", str(process_payload.get("model_family", "unknown")), "active inference backend"),
                            ]
                        )
                        plot_left, plot_right = st.columns(2, gap="large")
                        with plot_left:
                            pareto = px.scatter(
                                rows_df,
                                x="hot_solubility_mg_mL",
                                y="yield",
                                color="green_score",
                                size="delta_T",
                                hover_name="solvent_name",
                                hover_data=["T_hot", "T_cold", "toxicity_class", "boiling_point_K"],
                                title="Crystallization Pareto front",
                            )
                            pareto.update_layout(height=420, xaxis_title="Hot-end approx. mg/mL", yaxis_title="Yield")
                            st.plotly_chart(style_plot(pareto), use_container_width=True)
                        with plot_right:
                            top_bar = px.bar(
                                rows_df.head(10),
                                x="solvent_name",
                                y="yield",
                                color="recommended",
                                hover_data=["T_hot", "T_cold", "green_score", "toxicity_class"],
                                title="Top crystallization candidates",
                            )
                            top_bar.update_layout(height=420, xaxis_title="Solvent", yaxis_title="Yield")
                            st.plotly_chart(style_plot(top_bar), use_container_width=True)
                        render_dataframe(
                            rows_df[["solvent_name", "T_hot", "T_cold", "yield", "hot_solubility_mg_mL", "cold_solubility_mg_mL", "green_score", "toxicity_class", "recommended"]],
                            use_container_width=True,
                            hide_index=True,
                        )
                        labels = [
                            f"{row['solvent_name']} | {float(row['T_hot']):.0f}/{float(row['T_cold']):.0f} K | {100.0 * float(row['yield']):.1f}%"
                            for row in rows
                        ]
                        selected_label = st.selectbox("Top candidate detail", labels, key="applications_process_cryst_selected")
                        selected_row = rows[labels.index(selected_label)]
                        scan_df = pd.DataFrame(selected_row.get("temperature_scan", []))
                        if not scan_df.empty:
                            scan_fig = px.line(scan_df, x="T", y="x2", title=f"Temperature scan for {selected_row['solvent_name']}")
                            scan_fig.add_vline(x=float(selected_row["T_hot"]), line_dash="dash", line_color="#2563EB")
                            scan_fig.add_vline(x=float(selected_row["T_cold"]), line_dash="dash", line_color="#EF4444")
                            scan_fig.update_layout(height=380, xaxis_title="Temperature (K)", yaxis_title="Predicted x2")
                            st.plotly_chart(style_plot(scan_fig), use_container_width=True)
                elif result_mode == "extraction":
                    rows_df = pd.DataFrame(process_payload.get("result", []) or [])
                    if rows_df.empty:
                        st.warning("No extraction solvents satisfied the current constraints.")
                    else:
                        top_row = rows_df.iloc[0]
                        render_stat_tiles(
                            [
                                ("Top solvent", str(top_row.get("solvent_name", "—")), "best extraction candidate"),
                                ("Best K", f"{float(top_row.get('partition_coefficient', 0.0)):.2f}", "x2(extract) / x2(source)"),
                                ("Miscible", "yes" if bool(top_row.get("miscible_with_source")) else "no", "with source solvent"),
                                ("Recommended", "yes" if bool(top_row.get("recommended")) else "no", "screening heuristic"),
                            ]
                        )
                        plot_left, plot_right = st.columns(2, gap="large")
                        with plot_left:
                            pareto = px.scatter(
                                rows_df,
                                x="partition_coefficient",
                                y="boiling_point_K",
                                color="recommended",
                                size="overall_score",
                                hover_name="solvent_name",
                                hover_data=["miscible_with_source", "green_score", "toxicity_class"],
                                title="Extraction trade-off map",
                            )
                            pareto.update_layout(height=420, xaxis_title="Partition coefficient", yaxis_title="Boiling point (K)")
                            st.plotly_chart(style_plot(pareto), use_container_width=True)
                        with plot_right:
                            k_bar = px.bar(
                                rows_df.head(12),
                                x="solvent_name",
                                y="partition_coefficient",
                                color="recommended",
                                title="Top extraction solvents by partition coefficient",
                            )
                            k_bar.update_layout(height=420, xaxis_title="Solvent", yaxis_title="K")
                            st.plotly_chart(style_plot(k_bar), use_container_width=True)
                        render_dataframe(
                            rows_df[["rank", "solvent_name", "partition_coefficient", "miscible_with_source", "boiling_point_K", "green_score", "toxicity_class", "recommended"]],
                            use_container_width=True,
                            hide_index=True,
                        )
                        selected_name = st.selectbox("Extraction candidate", rows_df["solvent_name"].astype(str).tolist(), key="applications_process_extract_selected")
                        selected_row = rows_df[rows_df["solvent_name"] == selected_name].iloc[0]
                        source_smiles = str(selected_row.get("source_solvent", ""))
                        source_scan = run_process_candidate_scan(
                            python_command,
                            str(process_payload.get("checkpoint_path", checkpoint_path)),
                            st.session_state.get("applications_process_extract_solute", DEFAULT_SOLUTE_SMILES),
                            source_smiles,
                            273.0,
                            353.0,
                            14,
                        )
                        candidate_scan = run_process_candidate_scan(
                            python_command,
                            str(process_payload.get("checkpoint_path", checkpoint_path)),
                            st.session_state.get("applications_process_extract_solute", DEFAULT_SOLUTE_SMILES),
                            str(selected_row.get("solvent_smiles", "")),
                            273.0,
                            353.0,
                            14,
                        )
                        overlay_rows = []
                        for label, payload in [("Source", source_scan), (selected_name, candidate_scan)]:
                            scan_df = pd.DataFrame(payload.get("scan", []))
                            if not scan_df.empty:
                                scan_df = scan_df.copy()
                                scan_df["system"] = label
                                overlay_rows.append(scan_df)
                        if overlay_rows:
                            overlay_df = pd.concat(overlay_rows, ignore_index=True)
                            overlay = px.line(overlay_df, x="T", y="x2", color="system", title="Temperature scan: source vs extraction solvent")
                            overlay.update_layout(height=360, xaxis_title="Temperature (K)", yaxis_title="Predicted x2")
                            st.plotly_chart(style_plot(overlay), use_container_width=True)
                elif result_mode == "reaction_medium":
                    rows_df = pd.DataFrame(process_payload.get("result", []) or [])
                    if rows_df.empty:
                        st.warning("No reaction solvents satisfied the current constraints.")
                    else:
                        top_row = rows_df.iloc[0]
                        reactant_cols = [col for col in rows_df.columns if col.startswith("reactant_") and col.endswith("_solubility_mg_mL")]
                        render_stat_tiles(
                            [
                                ("Top solvent", str(top_row.get("solvent_name", "—")), "best reaction medium"),
                                ("Reactant min mg/mL", f"{float(top_row.get('reactant_min_solubility_mg_mL', 0.0)):.2f}", "limiting reactant"),
                                ("Product mg/mL", f"{float(top_row.get('product_solubility_mg_mL', 0.0)):.2f}", "target product"),
                                ("Selectivity", f"{float(top_row.get('reactant_product_selectivity', 0.0)):.2f}", "reactant min / product"),
                            ]
                        )
                        plot_left, plot_right = st.columns(2, gap="large")
                        with plot_left:
                            pareto = px.scatter(
                                rows_df,
                                x="reactant_min_solubility_mg_mL",
                                y="reactant_product_selectivity",
                                color="recommended",
                                size="overall_score",
                                hover_name="solvent_name",
                                hover_data=["green_score", "toxicity_class", "boiling_point_K"],
                                title="Reaction-medium Pareto front",
                            )
                            pareto.update_layout(height=420, xaxis_title="Limiting reactant mg/mL", yaxis_title="Reactant/product selectivity")
                            st.plotly_chart(style_plot(pareto), use_container_width=True)
                        with plot_right:
                            selectivity_bar = px.bar(
                                rows_df.head(12),
                                x="solvent_name",
                                y="reactant_product_selectivity",
                                color="recommended",
                                title="Top reaction media by selectivity",
                            )
                            selectivity_bar.update_layout(height=420, xaxis_title="Solvent", yaxis_title="Selectivity ratio")
                            st.plotly_chart(style_plot(selectivity_bar), use_container_width=True)
                        display_cols = ["rank", "solvent_name", "reactant_min_solubility_mg_mL", "product_solubility_mg_mL", "reactant_product_selectivity", "green_score", "toxicity_class", "recommended"]
                        render_dataframe(rows_df[[col for col in display_cols if col in rows_df.columns]], use_container_width=True, hide_index=True)
                        selected_name = st.selectbox("Reaction-medium candidate", rows_df["solvent_name"].astype(str).tolist(), key="applications_process_rxn_selected")
                        selected_row = rows_df[rows_df["solvent_name"] == selected_name].iloc[0]
                        scan_rows = []
                        product_scan = run_process_candidate_scan(
                            python_command,
                            str(process_payload.get("checkpoint_path", checkpoint_path)),
                            str(selected_row.get("product_smiles", st.session_state.get("applications_process_rxn_product", "CC(=O)O"))),
                            str(selected_row.get("solvent_smiles", "")),
                            273.0,
                            353.0,
                            14,
                        )
                        product_df = pd.DataFrame(product_scan.get("scan", []))
                        if not product_df.empty:
                            product_df["species"] = "Product"
                            scan_rows.append(product_df)
                        for idx, reactant_col in enumerate(sorted(col for col in rows_df.columns if col.startswith("reactant_") and col.endswith("_smiles"))[:2], start=1):
                            reactant_smiles = str(selected_row.get(reactant_col, ""))
                            reactant_scan = run_process_candidate_scan(
                                python_command,
                                str(process_payload.get("checkpoint_path", checkpoint_path)),
                                reactant_smiles,
                                str(selected_row.get("solvent_smiles", "")),
                                273.0,
                                353.0,
                                14,
                            )
                            reactant_df = pd.DataFrame(reactant_scan.get("scan", []))
                            if not reactant_df.empty:
                                reactant_df["species"] = f"Reactant {idx}"
                                scan_rows.append(reactant_df)
                        if scan_rows:
                            overlay_df = pd.concat(scan_rows, ignore_index=True)
                            overlay = px.line(overlay_df, x="T", y="x2", color="species", title=f"Top candidate temperature scan in {selected_name}")
                            overlay.update_layout(height=360, xaxis_title="Temperature (K)", yaxis_title="Predicted x2")
                            st.plotly_chart(style_plot(overlay), use_container_width=True)

    elif workspace == "Solvent screening":
        screen_editor_version = int(st.session_state.get("applications_screen_editor_version", 0))
        pending_screen_solute = st.session_state.pop("applications_screen_solute_input_pending", None)
        if pending_screen_solute is not None:
            st.session_state["applications_screen_solute"] = pending_screen_solute
            st.session_state["applications_screen_solute_input"] = pending_screen_solute
        left, right = st.columns([1.05, 0.95], gap="large")
        solvent_classes = sorted({str(entry.get("solvent_class", "")) for entry in BUILTIN_SOLVENT_LIBRARY if entry.get("solvent_class")})
        with left:
            checkpoint_path = render_path_select("Checkpoint", supported_checkpoints, default_checkpoint, "applications_screen_checkpoint")
            solute_smiles = st.text_input(
                "Target solute SMILES",
                value=st.session_state.get("applications_screen_solute", DEFAULT_SOLUTE_SMILES),
                key="applications_screen_solute_input",
            )
            temp_cols = st.columns([1.1, 0.9], gap="small")
            with temp_cols[0]:
                temperature = float(
                    st.slider(
                        "Screen temperature (K)",
                        min_value=250,
                        max_value=400,
                        value=298,
                        step=1,
                        key="applications_screen_temperature",
                    )
                )
            with temp_cols[1]:
                top_k = int(
                    st.slider(
                        "Top K solvents",
                        min_value=5,
                        max_value=60,
                        value=20,
                        step=1,
                        key="applications_screen_top_k",
                    )
                )
            st.markdown("#### Filters")
            filter_cols = st.columns(3, gap="small")
            with filter_cols[0]:
                min_solubility = st.number_input(
                    "Min mg/mL",
                    min_value=0.0,
                    max_value=500.0,
                    value=0.0,
                    step=0.5,
                    key="applications_screen_min_solubility",
                )
                min_green = int(
                    st.slider(
                        "Min green score",
                        min_value=1,
                        max_value=10,
                        value=1,
                        step=1,
                        key="applications_screen_min_green",
                    )
                )
            with filter_cols[1]:
                max_toxicity = int(
                    st.slider(
                        "Max toxicity severity",
                        min_value=1,
                        max_value=3,
                        value=3,
                        step=1,
                        key="applications_screen_max_toxicity",
                    )
                )
                max_bp = float(
                    st.number_input(
                        "Max boiling point (K)",
                        min_value=280.0,
                        max_value=700.0,
                        value=700.0,
                        step=5.0,
                        key="applications_screen_max_bp",
                    )
                )
            with filter_cols[2]:
                require_water_miscible = st.toggle(
                    "Require water miscible",
                    value=False,
                    key="applications_screen_require_water_miscible",
                )
                exclude_classes = st.multiselect(
                    "Exclude classes",
                    options=solvent_classes,
                    default=[],
                    key="applications_screen_exclude_classes",
                )

            filters = {
                "min_solubility_mg_mL": float(min_solubility) if min_solubility > 0 else None,
                "max_toxicity_class": int(max_toxicity) if max_toxicity < 3 else None,
                "min_green_score": int(min_green) if min_green > 1 else None,
                "max_boiling_point_K": float(max_bp) if max_bp < 699.0 else None,
                "exclude_classes": exclude_classes,
                "require_water_miscible": bool(require_water_miscible),
            }
            filters = {key: value for key, value in filters.items() if value not in (None, [], False)}

            if st.button("Run solvent screen", key="applications_screen_run", use_container_width=True):
                canonical_solute, error = canonicalize_smiles(solute_smiles)
                if not canonical_solute:
                    st.session_state["applications_screen_result"] = {"error": error or "Invalid solute SMILES."}
                else:
                    st.session_state["applications_screen_solute"] = canonical_solute
                    st.session_state["applications_screen_solute_input_pending"] = canonical_solute
                    st.session_state["applications_screen_result"] = run_solvent_screening(
                        python_command,
                        checkpoint_path,
                        canonical_solute,
                        float(temperature),
                        int(top_k),
                        json.dumps(filters),
                    )
                    st.rerun()

        with right:
            render_molecule_showcase(
                st.session_state.get("applications_screen_solute", DEFAULT_SOLUTE_SMILES),
                title="Screening target",
                subtitle="Rank the built-in solvent library for one solute, then drill into crystallization leverage, drowning-out options, and greener replacements.",
                svg_size=(520, 320),
                graph_height=360,
                compact=True,
            )
            with st.expander("Structure editor", expanded=False):
                if st_ketcher is None:
                    st.info("Ketcher is unavailable in this environment. Restart the lab from the GUI-enabled Python environment.")
                    if KETCHER_ERROR:
                        st.caption(f"Editor import error: {KETCHER_ERROR}")
                else:
                    drawn_solute = st_ketcher(
                        st.session_state.get("applications_screen_solute", DEFAULT_SOLUTE_SMILES),
                        height=420,
                        molecule_format="SMILES",
                        key=f"applications_screen_editor_{screen_editor_version}",
                    )
                    editor_smiles, editor_error = canonicalize_smiles(drawn_solute)
                    render_structure_editor_preview(
                        "Solute",
                        editor_smiles,
                        raw_smiles=drawn_solute,
                        error=editor_error,
                    )
                    if st.button("Use drawing in solvent screening", key="applications_screen_apply_editor", use_container_width=True):
                        if editor_smiles:
                            st.session_state["applications_screen_solute"] = editor_smiles
                            st.session_state["applications_screen_solute_input_pending"] = editor_smiles
                            st.session_state["applications_screen_editor_version"] = screen_editor_version + 1
                            st.rerun()
                        st.error(editor_error or "The editor did not export a valid structure.")
            info_card(
                "Conversion assumption",
                "mg/mL is reported from a solvent-dominated volume approximation, using pure-solvent density and molecular weights. It is useful for screening, not for regulatory release values.",
            )
            info_card(
                "Confidence and Hansen space",
                "AD confidence is shown only when a fitted applicability-domain model is available. Hansen plots require TGNN-Solv because DirectGNN does not expose the physics-side decomposition.",
            )

        screening_payload = st.session_state.get("applications_screen_result")
        if screening_payload:
            if screening_payload.get("error"):
                st.error(screening_payload["error"])
            else:
                rows_df = pd.DataFrame(screening_payload.get("screening_rows", []))
                if rows_df.empty:
                    st.warning("No solvents satisfied the current filters.")
                else:
                    top_row = rows_df.iloc[0]
                    render_stat_tiles(
                        [
                            ("Ranked solvents", str(len(rows_df)), "after filters"),
                            ("Top solvent", str(top_row.get("solvent_name", "—")), "highest approximate mg/mL"),
                            ("Top mg/mL", f"{float(top_row.get('solubility_mg_mL', 0.0)):.2f}" if pd.notna(top_row.get("solubility_mg_mL")) else "—", "volume-based approximation"),
                            ("Model family", str(screening_payload.get("model_family", "unknown")), "active inference backend"),
                        ]
                    )
                    chart_left, chart_right = st.columns(2, gap="large")
                    with chart_left:
                        top_plot_df = rows_df.head(min(20, len(rows_df))).copy()
                        bar = px.bar(
                            top_plot_df,
                            x="solvent_name",
                            y="solubility_mg_mL",
                            color="solvent_class",
                            hover_data=["ln_x2", "x2", "green_score", "toxicity_class", "boiling_point_K"],
                            title="Top solvents by approximate mg/mL",
                        )
                        bar.update_layout(height=430, xaxis_title="Solvent", yaxis_title="Approx. solubility (mg/mL)")
                        st.plotly_chart(style_plot(bar), use_container_width=True)
                    with chart_right:
                        class_df = (
                            rows_df.groupby("solvent_class", as_index=False)
                            .agg(solubility_mg_mL=("solubility_mg_mL", "mean"), green_score=("green_score", "mean"))
                            .sort_values("solubility_mg_mL", ascending=False)
                        )
                        class_fig = px.bar(
                            class_df,
                            x="solvent_class",
                            y="solubility_mg_mL",
                            color="green_score",
                            title="Mean approximate solubility by solvent class",
                        )
                        class_fig.update_layout(height=430, xaxis_title="Solvent class", yaxis_title="Mean approx. mg/mL")
                        st.plotly_chart(style_plot(class_fig), use_container_width=True)

                    assumptions = screening_payload.get("assumptions") or {}
                    if assumptions:
                        with st.expander("Screening assumptions", expanded=False):
                            for label, text in assumptions.items():
                                st.markdown(f"**{label.replace('_', ' ').title()}**")
                                st.caption(str(text))

                    render_dataframe(
                        rows_df[
                            [
                                "rank",
                                "solvent_name",
                                "solvent_class",
                                "solubility_mg_mL",
                                "ln_x2",
                                "x2",
                                "green_score",
                                "toxicity_class",
                                "boiling_point_K",
                                "confidence",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                    solvent_names = rows_df["solvent_name"].astype(str).tolist()
                    detail_checkpoint_path = str(screening_payload.get("checkpoint_path", checkpoint_path))
                    detail_solute_smiles = str(screening_payload.get("solute_smiles", st.session_state.get("applications_screen_solute", DEFAULT_SOLUTE_SMILES)))
                    detail_temperature = float(screening_payload.get("temperature", temperature))
                    selected_solvent_name = st.selectbox(
                        "Selected solvent for detailed analysis",
                        options=solvent_names,
                        key="applications_screen_selected_solvent",
                    )
                    selected_row = rows_df[rows_df["solvent_name"] == selected_solvent_name].iloc[0]
                    detail_left, detail_right = st.columns([0.72, 1.28], gap="large")
                    with detail_left:
                        render_molecule_panel(
                            str(selected_row.get("solvent_smiles", "")),
                            f"Selected solvent: {selected_solvent_name}",
                            f"{selected_row.get('solvent_class', 'solvent')} | {selected_row.get('toxicity_class', 'toxicity n/a')} | green {selected_row.get('green_score', '—')}",
                            width=420,
                            height=280,
                        )
                        render_stat_tiles(
                            [
                                ("Approx. mg/mL", f"{float(selected_row.get('solubility_mg_mL', 0.0)):.2f}" if pd.notna(selected_row.get("solubility_mg_mL")) else "—", "screening approximation"),
                                ("ln x2", f"{float(selected_row.get('ln_x2', 0.0)):.2f}", "model prediction"),
                                ("Boiling point", f"{float(selected_row.get('boiling_point_K', 0.0)):.1f} K" if pd.notna(selected_row.get("boiling_point_K")) else "—", "operability proxy"),
                                ("Confidence", f"{float(selected_row.get('confidence', 0.0)):.2f}" if pd.notna(selected_row.get("confidence")) else "—", "AD if fitted"),
                            ]
                        )
                    with detail_right:
                        crystallization_payload = run_crystallization_window_analysis(
                            python_command,
                            detail_checkpoint_path,
                            detail_solute_smiles,
                            str(selected_row.get("solvent_smiles", "")),
                            None,
                            None,
                            18,
                        )
                        if crystallization_payload.get("error"):
                            st.error(crystallization_payload["error"])
                        else:
                            cryst_stats = [
                                ("Hot T", f"{float(crystallization_payload.get('T_hot', 0.0)):.1f} K", "default dissolution endpoint"),
                                ("Cold T", f"{float(crystallization_payload.get('T_cold', 0.0)):.1f} K", "default crystallization endpoint"),
                                ("Yield", f"{100.0 * float(crystallization_payload.get('theoretical_yield', 0.0)):.1f}%", "theoretical equilibrium capture"),
                                ("MZW", f"{float(crystallization_payload.get('metastable_zone_width_estimate', 0.0)):.1f} K", "heuristic from d ln x2 / dT"),
                            ]
                            render_stat_tiles(cryst_stats)
                            scan_df = pd.DataFrame(crystallization_payload.get("temperature_scan", []))
                            if not scan_df.empty:
                                scan_fig = px.line(
                                    scan_df,
                                    x="T",
                                    y="x2",
                                    title=f"Crystallization window for {selected_solvent_name}",
                                )
                                scan_fig.add_vrect(
                                    x0=float(crystallization_payload.get("T_cold", 0.0)),
                                    x1=float(crystallization_payload.get("T_hot", 0.0)),
                                    fillcolor="rgba(37,99,235,0.08)",
                                    line_width=0,
                                )
                                scan_fig.update_layout(height=380, xaxis_title="Temperature (K)", yaxis_title="Predicted x2")
                                st.plotly_chart(style_plot(scan_fig), use_container_width=True)
                                if "gamma_2" in scan_df.columns and scan_df["gamma_2"].notna().any():
                                    gamma_fig = px.line(
                                        scan_df,
                                        x="T",
                                        y="gamma_2",
                                        title="Activity coefficient over the cooling path",
                                    )
                                    gamma_fig.update_layout(height=280, xaxis_title="Temperature (K)", yaxis_title="gamma_2")
                                    st.plotly_chart(style_plot(gamma_fig), use_container_width=True)
                            st.caption(str(crystallization_payload.get("recommended_cooling_rate", "")))

                    if screening_payload.get("model_family") == "tgnn_solv":
                        hansen_cols = ["hansen_slv_d", "hansen_slv_p", "hansen_slv_h", "hansen_sol_d", "hansen_sol_p", "hansen_sol_h"]
                        if all(col in rows_df.columns for col in hansen_cols) and rows_df[hansen_cols[:3]].notna().any().all():
                            hansen_left, hansen_right = st.columns([1.2, 0.8], gap="large")
                            with hansen_left:
                                hansen_fig = go.Figure()
                                hansen_fig.add_trace(
                                    go.Scatter3d(
                                        x=rows_df["hansen_slv_d"],
                                        y=rows_df["hansen_slv_p"],
                                        z=rows_df["hansen_slv_h"],
                                        mode="markers",
                                        marker={
                                            "size": 6,
                                            "color": rows_df["solubility_mg_mL"].fillna(rows_df["x2"]),
                                            "colorscale": "Viridis",
                                            "showscale": True,
                                        },
                                        text=rows_df["solvent_name"],
                                        name="Solvents",
                                    )
                                )
                                hansen_fig.add_trace(
                                    go.Scatter3d(
                                        x=[float(selected_row.get("hansen_sol_d"))],
                                        y=[float(selected_row.get("hansen_sol_p"))],
                                        z=[float(selected_row.get("hansen_sol_h"))],
                                        mode="markers+text",
                                        marker={"size": 10, "color": "#EF4444"},
                                        text=["Solute"],
                                        textposition="top center",
                                        name="Solute",
                                    )
                                )
                                hansen_fig.update_layout(
                                    height=460,
                                    title="Hansen space: solute vs screened solvents",
                                    scene={
                                        "xaxis_title": "δd",
                                        "yaxis_title": "δp",
                                        "zaxis_title": "δh",
                                    },
                                )
                                st.plotly_chart(style_plot(hansen_fig), use_container_width=True)
                            with hansen_right:
                                delta_fig = px.scatter(
                                    rows_df,
                                    x="hansen_Ra",
                                    y="solubility_mg_mL",
                                    color="solvent_class",
                                    hover_name="solvent_name",
                                    title="Hansen distance vs approximate mg/mL",
                                )
                                delta_fig.update_layout(height=460, xaxis_title="Ra", yaxis_title="Approx. mg/mL")
                                st.plotly_chart(style_plot(delta_fig), use_container_width=True)
                        else:
                            st.info("Hansen-space visualization is available only when the selected checkpoint emits TGNN solvent/solute Hansen parameters.")
                    else:
                        st.info("Hansen-space visualization is disabled for DirectGNN because the baseline does not expose solver-side Hansen parameters.")

                    follow_left, follow_right = st.columns(2, gap="large")
                    with follow_left:
                        anti_payload = run_antisolvent_screening_analysis(
                            python_command,
                            detail_checkpoint_path,
                            detail_solute_smiles,
                            str(selected_row.get("solvent_smiles", "")),
                            detail_temperature,
                        )
                        if anti_payload.get("error"):
                            st.error(anti_payload["error"])
                        else:
                            anti_df = pd.DataFrame(anti_payload.get("rows", []))
                            st.markdown("### Antisolvent suggestions")
                            if anti_df.empty:
                                st.info("No antisolvent candidates were produced for this solvent.")
                            else:
                                anti_fig = px.bar(
                                    anti_df.head(12),
                                    x="antisolvent_name",
                                    y="solubility_ratio",
                                    color="recommended",
                                    title="Good-solvent / antisolvent solubility ratio",
                                )
                                anti_fig.update_layout(height=360, xaxis_title="Antisolvent", yaxis_title="x2(good) / x2(anti)")
                                st.plotly_chart(style_plot(anti_fig), use_container_width=True)
                                render_dataframe(
                                    anti_df[["rank", "antisolvent_name", "solubility_ratio", "miscible_with_good_solvent", "recommended", "toxicity_class", "green_score"]],
                                    use_container_width=True,
                                    hide_index=True,
                                )
                    with follow_right:
                        green_payload = run_green_replacement_analysis(
                            python_command,
                            detail_checkpoint_path,
                            detail_solute_smiles,
                            str(selected_row.get("solvent_smiles", "")),
                            detail_temperature,
                            0.5,
                        )
                        if green_payload.get("error"):
                            st.error(green_payload["error"])
                        else:
                            green_df = pd.DataFrame(green_payload.get("rows", []))
                            st.markdown("### Green replacement suggestions")
                            if green_df.empty:
                                st.info("No greener alternatives met the current retention threshold.")
                            else:
                                green_fig = px.scatter(
                                    green_df.head(20),
                                    x="solubility_retention",
                                    y="green_improvement",
                                    color="recommended",
                                    hover_name="solvent_name",
                                    title="Green improvement vs solubility retention",
                                )
                                green_fig.update_layout(height=360, xaxis_title="Retention vs current solvent", yaxis_title="Green-score improvement")
                                st.plotly_chart(style_plot(green_fig), use_container_width=True)
                                render_dataframe(
                                    green_df[["rank", "solvent_name", "green_score", "green_improvement", "solubility_retention", "toxicity_improvement", "recommended"]],
                                    use_container_width=True,
                                    hide_index=True,
                                )

    elif workspace == "Synthesis route screening":
        route_version = int(st.session_state.get("applications_route_editor_version", 0))
        route_seed_key = f"applications_route_seed_{route_version}"
        route_editor_key = f"applications_route_editor_{route_version}"
        if route_seed_key not in st.session_state:
            st.session_state[route_seed_key] = default_route_editor_frame()

        left, right = st.columns([1.25, 0.75], gap="large")
        with left:
            checkpoint_path = render_path_select("Checkpoint", supported_checkpoints, default_checkpoint, "applications_route_checkpoint")
            route_df = st.data_editor(
                st.session_state[route_seed_key],
                key=route_editor_key,
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "step_id": st.column_config.TextColumn("Step"),
                    "compound_smiles": st.column_config.TextColumn("Compound SMILES"),
                    "reaction_temp_k": st.column_config.NumberColumn("Reaction T (K)", format="%.2f"),
                    "isolation_temp_k": st.column_config.NumberColumn("Isolation T (K)", format="%.2f"),
                    "candidate_solvents": st.column_config.TextColumn("Candidate solvents"),
                    "goal": st.column_config.TextColumn("Goal"),
                },
            )
            action_cols = st.columns([0.9, 0.9, 1.1], gap="small")
            with action_cols[0]:
                if st.button("Load example route", key="applications_route_load_example", use_container_width=True):
                    new_version = route_version + 1
                    st.session_state["applications_route_editor_version"] = new_version
                    st.session_state[f"applications_route_seed_{new_version}"] = default_route_editor_frame()
                    st.rerun()
            with action_cols[1]:
                if st.button("Start empty route", key="applications_route_clear", use_container_width=True):
                    new_version = route_version + 1
                    st.session_state["applications_route_editor_version"] = new_version
                    st.session_state[f"applications_route_seed_{new_version}"] = pd.DataFrame(
                        [
                            {
                                "step_id": "S1",
                                "compound_smiles": DEFAULT_SOLUTE_SMILES,
                                "reaction_temp_k": 333.15,
                                "isolation_temp_k": 278.15,
                                "candidate_solvents": "",
                                "goal": "temperature-swing crystallization",
                            }
                        ]
                    )
                    st.rerun()
            with action_cols[2]:
                scan_points = int(
                    st.number_input(
                        "Scan points",
                        min_value=4,
                        max_value=30,
                        value=8,
                        step=1,
                        key="applications_route_scan_points",
                    )
                )

            parsed_steps: list[dict[str, Any]] = []
            route_issues: list[str] = []
            for row_index, (_, row) in enumerate(route_df.iterrows(), start=1):
                compound_smiles, compound_error = canonicalize_smiles(str(row.get("compound_smiles", "")))
                if not compound_smiles:
                    continue
                candidates = parse_smiles_tokens(str(row.get("candidate_solvents", "")), SYNTHESIS_SOLVENT_LIBRARY)
                if not candidates:
                    route_issues.append(f"Row {row_index}: no valid candidate solvents.")
                    continue
                parsed_steps.append(
                    {
                        "step_id": str(row.get("step_id", f"S{row_index}")).strip() or f"S{row_index}",
                        "compound_smiles": compound_smiles,
                        "reaction_temp_k": float(row.get("reaction_temp_k", 333.15)),
                        "isolation_temp_k": float(row.get("isolation_temp_k", 278.15)),
                        "goal": str(row.get("goal", "temperature-swing crystallization")).strip() or "temperature-swing crystallization",
                        "candidates": [{"label": label, "smiles": smiles} for label, smiles in candidates],
                    }
                )
                if compound_error:
                    route_issues.append(f"Row {row_index}: {compound_error}")

            with action_cols[0]:
                if st.button("Run route screen", key="applications_route_run", use_container_width=True):
                    st.session_state["applications_route_result"] = (
                        {"error": "No valid route steps to evaluate."}
                        if not parsed_steps
                        else run_synthesis_route_screen(
                            python_command,
                            checkpoint_path,
                            json.dumps({"steps": parsed_steps}),
                            scan_points,
                        )
                    )

        with right:
            st.markdown("### Route screening notes")
            st.caption(
                "This is a route-facing solvent utility layer, not a retrosynthesis engine. It scores explicit solvents for each intermediate based on the predicted hot-to-cold isolation window."
            )
            info_card(
                "How to read the score",
                "High route score means the compound looks loadable at the reaction temperature, drops materially on cooling, and stays comparatively insoluble at the isolation endpoint.",
            )
            info_card(
                "Candidate solvents",
                ", ".join(list(SYNTHESIS_SOLVENT_LIBRARY.keys())[:8]) + ", ... or enter exact solvent SMILES directly.",
            )
            if route_issues:
                render_dataframe(pd.DataFrame({"issue": route_issues}), use_container_width=True, hide_index=True)

        route_payload = st.session_state.get("applications_route_result")
        if route_payload:
            if route_payload.get("error"):
                st.error(route_payload["error"])
            else:
                summary = route_payload.get("summary", {})
                render_stat_tiles(
                    [
                        ("Steps", str(int(summary.get("n_steps", 0))), "intermediates evaluated"),
                        ("Candidates", str(int(summary.get("n_candidates", 0))), "solvent systems scored"),
                        ("Mean top score", f"{float(summary.get('mean_top_score', 0.0)):.1f}" if summary.get("mean_top_score") is not None else "—", "top solvent per step"),
                        ("Model family", str(route_payload.get("model_family", "unknown")), "active inference backend"),
                    ]
                )
                rows_df = pd.DataFrame(route_payload.get("rows", []))
                if not rows_df.empty:
                    top_df = rows_df.sort_values(["step_id", "route_score"], ascending=[True, False]).groupby("step_id", as_index=False).head(1)
                    fig_left, fig_right = st.columns(2, gap="large")
                    with fig_left:
                        scatter = px.scatter(
                            rows_df,
                            x="hot_ln_x2",
                            y="cold_ln_x2",
                            color="step_id",
                            size="route_score",
                            hover_name="solvent_label",
                            hover_data=["goal", "delta_ln_x2", "swing_ratio", "regime"],
                            title="Hot vs cold solubility map",
                        )
                        scatter.update_layout(height=460, xaxis_title="ln x2 at reaction temperature", yaxis_title="ln x2 at isolation temperature")
                        st.plotly_chart(style_plot(scatter), use_container_width=True)
                    with fig_right:
                        score_fig = px.bar(
                            top_df.sort_values("route_score", ascending=False),
                            x="step_id",
                            y="route_score",
                            color="solvent_label",
                            text="solvent_label",
                            title="Best solvent per route step",
                        )
                        score_fig.update_layout(height=460, xaxis_title="Route step", yaxis_title="Route score")
                        st.plotly_chart(style_plot(score_fig), use_container_width=True)
                    render_dataframe(
                        rows_df[["step_id", "solvent_label", "hot_ln_x2", "cold_ln_x2", "delta_ln_x2", "swing_ratio", "route_score", "regime"]],
                        use_container_width=True,
                        hide_index=True,
                    )

                    step_ids = [str(step.get("step_id", "")) for step in route_payload.get("steps", []) if step.get("step_id")]
                    if step_ids:
                        selected_step = st.selectbox("Route step detail", step_ids, key="applications_route_selected_step")
                        step_payload = next((step for step in route_payload.get("steps", []) if step.get("step_id") == selected_step), None)
                        if step_payload:
                            detail_left, detail_right = st.columns([0.8, 1.2], gap="large")
                            with detail_left:
                                render_molecule_panel(
                                    str(step_payload.get("compound_smiles", "")),
                                    f"Step {selected_step} compound",
                                    str(step_payload.get("goal", "")),
                                    width=520,
                                    height=360,
                                )
                            with detail_right:
                                ranked = pd.DataFrame(step_payload.get("ranked", []))
                                if not ranked.empty:
                                    score_bar = px.bar(
                                        ranked.head(6),
                                        x="solvent_label",
                                        y="route_score",
                                        color="delta_ln_x2",
                                        title=f"Step {selected_step} solvent ranking",
                                    )
                                    score_bar.update_layout(height=320, xaxis_title="Solvent", yaxis_title="Route score")
                                    st.plotly_chart(style_plot(score_bar), use_container_width=True)
                                    best = ranked.iloc[0]
                                    render_molecule_panel(
                                        str(best["solvent_smiles"]),
                                        f"Top solvent: {best['solvent_label']}",
                                        str(best["regime"]),
                                        width=360,
                                        height=240,
                                    )
                                scan_df = pd.DataFrame(step_payload.get("scan", []))
                                if not scan_df.empty and not ranked.empty:
                                    top_labels = ranked.head(3)["solvent_label"].tolist()
                                    overlay = px.line(
                                        scan_df[scan_df["solvent_label"].isin(top_labels)],
                                        x="T",
                                        y="ln_x2",
                                        color="solvent_label",
                                        title=f"Temperature scan for top step-{selected_step} solvents",
                                    )
                                    overlay.update_layout(height=360, xaxis_title="Temperature (K)", yaxis_title="Predicted ln x2")
                                    st.plotly_chart(style_plot(overlay), use_container_width=True)

    elif workspace == "Drug developability":
        drug_editor_version = int(st.session_state.get("applications_drug_editor_version", 0))
        pending_drug_solute = st.session_state.pop("applications_drug_solute_input_pending", None)
        if pending_drug_solute is not None:
            st.session_state["applications_drug_solute"] = pending_drug_solute
            st.session_state["applications_drug_solute_input"] = pending_drug_solute

        left, right = st.columns([1.05, 0.95], gap="large")
        with left:
            checkpoint_path = render_path_select("Checkpoint", supported_checkpoints, default_checkpoint, "applications_drug_checkpoint")
            solute_smiles = st.text_input(
                "Candidate SMILES",
                value=st.session_state.get("applications_drug_solute", DEFAULT_SOLUTE_SMILES),
                key="applications_drug_solute_input",
            )
            control_cols = st.columns(3, gap="small")
            with control_cols[0]:
                temperature = float(
                    st.number_input(
                        "Body-temperature screen (K)",
                        min_value=280.0,
                        max_value=340.0,
                        value=310.15,
                        step=1.0,
                        key="applications_drug_temperature",
                    )
                )
            with control_cols[1]:
                dose_mg = float(
                    st.number_input(
                        "Dose strength (mg)",
                        min_value=1.0,
                        max_value=5000.0,
                        value=500.0,
                        step=25.0,
                        key="applications_drug_dose",
                    )
                )
            with control_cols[2]:
                volume_ml = float(
                    st.number_input(
                        "Reference volume (mL)",
                        min_value=50.0,
                        max_value=1000.0,
                        value=250.0,
                        step=25.0,
                        key="applications_drug_volume",
                    )
                )
            counterions_raw = st.text_area(
                "Counterions / coformers (SMILES or known labels, one per line)",
                value=st.session_state.get("applications_drug_counterions", ""),
                height=120,
                key="applications_drug_counterions",
                help="Optional. Salt and cocrystal screening is approximate because the maintained model is trained on neutral molecules.",
            )
            if st.button("Run drug developability analysis", key="applications_drug_run", use_container_width=True):
                canonical_solute, error = canonicalize_smiles(solute_smiles)
                if not canonical_solute:
                    st.session_state["applications_drug_result"] = {"error": error or "Invalid candidate SMILES."}
                else:
                    counterions = [smiles for _, smiles in parse_smiles_tokens(counterions_raw)]
                    st.session_state["applications_drug_solute"] = canonical_solute
                    st.session_state["applications_drug_solute_input_pending"] = canonical_solute
                    st.session_state["applications_drug_result"] = run_drug_developability_analysis(
                        python_command,
                        checkpoint_path,
                        canonical_solute,
                        float(temperature),
                        float(dose_mg),
                        float(volume_ml),
                        json.dumps(counterions),
                    )
                    st.rerun()

        with right:
            render_molecule_showcase(
                st.session_state.get("applications_drug_solute", DEFAULT_SOLUTE_SMILES),
                title="Drug-developability target",
                subtitle="Translate TGNN-Solv predictions into an oral-developability readout: BCS-style dose pressure, crystal barrier, solvent latitude, and approximate salt / cocrystal leverage.",
                svg_size=(520, 320),
                graph_height=360,
                compact=True,
            )
            with st.expander("Structure editor", expanded=False):
                if st_ketcher is None:
                    st.info("Ketcher is unavailable in this environment. Restart the lab from the GUI-enabled Python environment.")
                    if KETCHER_ERROR:
                        st.caption(f"Editor import error: {KETCHER_ERROR}")
                else:
                    drawn_solute = st_ketcher(
                        st.session_state.get("applications_drug_solute", DEFAULT_SOLUTE_SMILES),
                        height=420,
                        molecule_format="SMILES",
                        key=f"applications_drug_editor_{drug_editor_version}",
                    )
                    editor_smiles, editor_error = canonicalize_smiles(drawn_solute)
                    render_structure_editor_preview(
                        "Candidate",
                        editor_smiles,
                        raw_smiles=drawn_solute,
                        error=editor_error,
                    )
                    if st.button("Use drawing in drug developability", key="applications_drug_apply_editor", use_container_width=True):
                        if editor_smiles:
                            st.session_state["applications_drug_solute"] = editor_smiles
                            st.session_state["applications_drug_solute_input_pending"] = editor_smiles
                            st.session_state["applications_drug_editor_version"] = drug_editor_version + 1
                            st.rerun()
                        st.error(editor_error or "The editor did not export a valid structure.")
            info_card(
                "BCS scope",
                "This page approximates the solubility limb of BCS from predicted equilibrium water solubility and combines it with descriptor-level permeability proxies. It is a triage tool, not a regulatory biowaiver claim.",
            )
            info_card(
                "Salt / cocrystal caveat",
                "Salt and cocrystal ranking uses disconnected API.counterion surrogates and should be interpreted qualitatively. It is useful for prioritization, not as a replacement for explicit solid-form characterization.",
            )

        dev_payload = st.session_state.get("applications_drug_result")
        if dev_payload:
            if dev_payload.get("error"):
                st.error(dev_payload["error"])
            else:
                palette = theme_palette()
                bcs_payload = dev_payload.get("bcs") or {}
                developability = dev_payload.get("developability") or {}
                media_df = pd.DataFrame(dev_payload.get("media_profile", []))
                reference_df = pd.DataFrame(dev_payload.get("reference_comparison", []))
                salt_df = pd.DataFrame(dev_payload.get("salt_cocrystal_screen", []))
                water_prediction = bcs_payload.get("water_prediction") or developability.get("water_prediction") or {}
                descriptor_profile = developability.get("descriptor_profile") or {}
                bcs_class = int(bcs_payload.get("bcs_class", 4)) if bcs_payload.get("bcs_class") is not None else 4
                badge_palette = {
                    1: (palette["green"], "Class I", "High solubility / high permeability"),
                    2: (palette["orange"], "Class II", "Low solubility / high permeability"),
                    3: (palette["blue"], "Class III", "High solubility / low permeability"),
                    4: (palette["red"], "Class IV", "Low solubility / low permeability"),
                }
                badge_color, badge_label, badge_caption = badge_palette[bcs_class]
                st.markdown(
                    f"""
                    <div class="lab-card" style="border:1px solid {hex_to_rgba(badge_color, 0.35)};">
                      <div class="lab-kicker-row">
                        <span class="lab-kicker" style="{accent_pill_style(badge_color)}">BCS {escape(badge_label)}</span>
                        <span class="lab-kicker">{escape(str(dev_payload.get("model_family", "unknown")))}</span>
                        <span class="lab-kicker">{escape(str(dev_payload.get("solute_smiles", "")))}</span>
                      </div>
                      <h3>{escape(badge_caption)}</h3>
                      <p>{escape(str(bcs_payload.get("formulation_challenge", "No formulation challenge summary available.")))}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                render_stat_tiles(
                    [
                        ("Aqueous mg/mL", f"{float(bcs_payload.get('solubility_intrinsic_mg_mL', 0.0)):.2f}" if bcs_payload.get("solubility_intrinsic_mg_mL") is not None else "—", "intrinsic water solubility at body temperature"),
                        ("Dose number", f"{float(bcs_payload.get('dose_number', 0.0)):.2f}" if bcs_payload.get("dose_number") is not None else "—", "worst-case over pH 1.0 / 4.5 / 6.8"),
                        ("Developability", f"{float(developability.get('developability_score', 0.0)):.2f}" if developability.get("developability_score") is not None else "—", str(developability.get("traffic_light", "—"))),
                        ("High permeability", "yes" if bcs_payload.get("high_permeability") else "no", "descriptor proxy"),
                        ("T_m", f"{float(water_prediction.get('T_m', 0.0)):.1f} K" if water_prediction.get("T_m") is not None else "—", "predicted crystal stability"),
                        ("ΔH_fus", f"{float(water_prediction.get('dH_fus', 0.0)) / 1000.0:.1f} kJ/mol" if water_prediction.get("dH_fus") is not None else "—", "fusion enthalpy"),
                        ("LogP", f"{float((bcs_payload.get('permeability_proxy') or {}).get('LogP', 0.0)):.2f}" if (bcs_payload.get("permeability_proxy") or {}).get("LogP") is not None else "—", "descriptor proxy"),
                        ("TPSA", f"{float((bcs_payload.get('permeability_proxy') or {}).get('TPSA', 0.0)):.1f}" if (bcs_payload.get("permeability_proxy") or {}).get("TPSA") is not None else "—", "A^2"),
                    ]
                )

                chart_left, chart_right = st.columns(2, gap="large")
                with chart_left:
                    solubility_profile = pd.DataFrame(
                        [
                            {"medium": "Intrinsic water", "solubility_mg_mL": bcs_payload.get("solubility_intrinsic_mg_mL")},
                            {"medium": "pH 1.0", "solubility_mg_mL": bcs_payload.get("solubility_pH1")},
                            {"medium": "pH 4.5", "solubility_mg_mL": bcs_payload.get("solubility_pH4_5")},
                            {"medium": "pH 6.8", "solubility_mg_mL": bcs_payload.get("solubility_pH6_8")},
                        ]
                    ).dropna(subset=["solubility_mg_mL"])
                    solubility_fig = px.bar(
                        solubility_profile,
                        x="medium",
                        y="solubility_mg_mL",
                        color="solubility_mg_mL",
                        title="BCS-relevant aqueous solubility profile",
                    )
                    solubility_fig.update_layout(height=420, xaxis_title="Medium", yaxis_title="Approx. solubility (mg/mL)")
                    st.plotly_chart(style_plot(solubility_fig), use_container_width=True)
                with chart_right:
                    component_scores = developability.get("component_scores") or {}
                    radar_df = pd.DataFrame(
                        {
                            "metric": list(component_scores.keys()),
                            "score": [float(value) for value in component_scores.values()],
                        }
                    )
                    if not radar_df.empty:
                        radar = go.Figure()
                        radar.add_trace(
                            go.Scatterpolar(
                                r=radar_df["score"].tolist() + [radar_df["score"].tolist()[0]],
                                theta=radar_df["metric"].tolist() + [radar_df["metric"].tolist()[0]],
                                fill="toself",
                                line={"color": palette["blue"], "width": 3},
                                fillcolor=hex_to_rgba(palette["blue"], 0.22),
                                name="Developability components",
                            )
                        )
                        radar.update_layout(
                            title="Developability radar",
                            height=420,
                            polar={"radialaxis": {"range": [0, 1], "tickformat": ".1f"}},
                            showlegend=False,
                        )
                        st.plotly_chart(style_plot(radar), use_container_width=True)
                    else:
                        st.info("Component-score radar becomes available after a successful developability run.")

                if not media_df.empty:
                    st.markdown("### Pharma-medium profile")
                    profile_left, profile_right = st.columns(2, gap="large")
                    with profile_left:
                        media_fig = px.bar(
                            media_df.sort_values("solubility_mg_mL", ascending=False),
                            x="medium",
                            y="solubility_mg_mL",
                            color="medium",
                            hover_data=["ln_x2", "x2", "fold_vs_water"],
                            title="Predicted solubility across formulation-relevant media",
                        )
                        media_fig.update_layout(height=420, xaxis_title="Medium", yaxis_title="Approx. solubility (mg/mL)")
                        st.plotly_chart(style_plot(media_fig), use_container_width=True)
                    with profile_right:
                        if "fold_vs_water" in media_df.columns and media_df["fold_vs_water"].notna().any():
                            uplift_fig = px.bar(
                                media_df.dropna(subset=["fold_vs_water"]).sort_values("fold_vs_water", ascending=False),
                                x="medium",
                                y="fold_vs_water",
                                color="medium",
                                title="Formulation uplift relative to water",
                            )
                            uplift_fig.update_layout(height=420, xaxis_title="Medium", yaxis_title="x2 / water x2")
                            st.plotly_chart(style_plot(uplift_fig), use_container_width=True)
                        else:
                            st.info("Water-relative uplift is unavailable because the media profile lacks a water anchor.")
                    render_dataframe(
                        media_df[[col for col in ["medium", "solubility_mg_mL", "ln_x2", "x2", "fold_vs_water", "green_score", "toxicity_class"] if col in media_df.columns]],
                        use_container_width=True,
                        hide_index=True,
                    )

                detail_left, detail_right = st.columns([1.1, 0.9], gap="large")
                with detail_left:
                    temp_scan_rows = ((developability.get("temperature_sensitivity") or {}).get("scan")) or []
                    if temp_scan_rows:
                        scan_df = pd.DataFrame(temp_scan_rows)
                        temp_fig = px.line(
                            scan_df,
                            x="T",
                            y="x2",
                            title="Water temperature sensitivity around body temperature",
                        )
                        temp_fig.update_layout(height=360, xaxis_title="Temperature (K)", yaxis_title="Predicted x2")
                        st.plotly_chart(style_plot(temp_fig), use_container_width=True)
                    if dev_payload.get("model_family") == "tgnn_solv":
                        hansen_cols = ["hansen_slv_d", "hansen_slv_p", "hansen_slv_h", "hansen_sol_d", "hansen_sol_p", "hansen_sol_h"]
                        if not media_df.empty and all(col in media_df.columns for col in hansen_cols):
                            hansen_fig = go.Figure()
                            hansen_fig.add_trace(
                                go.Scatter3d(
                                    x=media_df["hansen_slv_d"],
                                    y=media_df["hansen_slv_p"],
                                    z=media_df["hansen_slv_h"],
                                    mode="markers+text",
                                    marker={
                                        "size": 8,
                                        "color": media_df["solubility_mg_mL"].fillna(media_df["x2"]),
                                        "colorscale": "Viridis",
                                        "showscale": True,
                                    },
                                    text=media_df["medium"],
                                    textposition="top center",
                                    name="Media",
                                )
                            )
                            hansen_fig.add_trace(
                                go.Scatter3d(
                                    x=[float(media_df.iloc[0]["hansen_sol_d"])],
                                    y=[float(media_df.iloc[0]["hansen_sol_p"])],
                                    z=[float(media_df.iloc[0]["hansen_sol_h"])],
                                    mode="markers+text",
                                    marker={"size": 10, "color": palette["red"]},
                                    text=["Solute"],
                                    textposition="top center",
                                    name="Solute",
                                )
                            )
                            hansen_fig.update_layout(
                                title="Hansen space: candidate vs pharma media",
                                height=440,
                                scene={"xaxis_title": "δd", "yaxis_title": "δp", "zaxis_title": "δh"},
                            )
                            st.plotly_chart(style_plot(hansen_fig), use_container_width=True)
                        else:
                            st.info("Hansen-space visualization requires TGNN checkpoints that emit solvent and solute Hansen parameters.")
                    else:
                        st.info("Hansen-space visualization is unavailable for DirectGNN because the baseline does not expose physics-side Hansen parameters.")
                with detail_right:
                    st.markdown("### Recommendations")
                    for item in bcs_payload.get("recommendations", []):
                        st.markdown(f"- {item}")
                    for item in developability.get("recommendations", []):
                        st.markdown(f"- {item}")
                    if developability.get("key_risks"):
                        st.markdown("### Key risks")
                        for item in developability.get("key_risks", []):
                            st.markdown(f"- {item}")
                    caveats = list(dict.fromkeys([*bcs_payload.get("caveats", []), "Equilibrium solubility does not replace permeability, clearance, precipitation kinetics, or PBPK modelling."]))
                    if caveats:
                        st.markdown("### Caveats")
                        for item in caveats:
                            st.markdown(f"- {item}")

                if not salt_df.empty:
                    st.markdown("### Salt / cocrystal screening")
                    salt_left, salt_right = st.columns([1.0, 1.0], gap="large")
                    with salt_left:
                        salt_plot = px.bar(
                            salt_df.dropna(subset=["solubility_advantage"]),
                            x="counterion",
                            y="solubility_advantage",
                            color="confidence",
                            title="Approximate salt / cocrystal solubility leverage",
                        )
                        salt_plot.update_layout(height=360, xaxis_title="Counterion / coformer", yaxis_title="x2(salt surrogate) / x2(free form)")
                        st.plotly_chart(style_plot(salt_plot), use_container_width=True)
                    with salt_right:
                        render_dataframe(
                            salt_df[[col for col in ["counterion", "salt_smiles", "x2_freeform", "x2_salt", "solubility_advantage", "confidence", "caveats"] if col in salt_df.columns]],
                            use_container_width=True,
                            hide_index=True,
                        )

                if not reference_df.empty:
                    st.markdown("### Reference-drug comparison")
                    render_dataframe(reference_df, use_container_width=True, hide_index=True)

    elif workspace == "PK solubility profile":
        pk_editor_version = int(st.session_state.get("applications_pk_editor_version", 0))
        pending_pk_solute = st.session_state.pop("applications_pk_solute_input_pending", None)
        if pending_pk_solute is not None:
            st.session_state["applications_pk_solute"] = pending_pk_solute
            st.session_state["applications_pk_solute_input"] = pending_pk_solute

        left, right = st.columns([1.0, 1.0], gap="large")
        with left:
            checkpoint_path = render_path_select("Checkpoint", supported_checkpoints, default_checkpoint, "applications_pk_checkpoint")
            solute_smiles = st.text_input(
                "Candidate SMILES",
                value=st.session_state.get("applications_pk_solute", DEFAULT_SOLUTE_SMILES),
                key="applications_pk_solute_input",
            )
            dose_mg = float(
                st.number_input(
                    "Oral dose (mg)",
                    min_value=1.0,
                    max_value=5000.0,
                    value=500.0,
                    step=25.0,
                    key="applications_pk_dose",
                )
            )
            if st.button("Run PK solubility profile", key="applications_pk_run", use_container_width=True):
                canonical_solute, error = canonicalize_smiles(solute_smiles)
                if not canonical_solute:
                    st.session_state["applications_pk_result"] = {"error": error or "Invalid candidate SMILES."}
                else:
                    st.session_state["applications_pk_solute"] = canonical_solute
                    st.session_state["applications_pk_solute_input_pending"] = canonical_solute
                    st.session_state["applications_pk_result"] = run_pk_profile_analysis(
                        python_command,
                        checkpoint_path,
                        canonical_solute,
                        float(dose_mg),
                    )
                    st.rerun()

        with right:
            render_molecule_showcase(
                st.session_state.get("applications_pk_solute", DEFAULT_SOLUTE_SMILES),
                title="PK solubility target",
                subtitle="Estimate where dissolution becomes limiting along the GI tract, whether food likely helps, and which IV or topical vehicles provide the most practical solubility leverage.",
                svg_size=(520, 320),
                graph_height=360,
                compact=True,
            )
            with st.expander("Structure editor", expanded=False):
                if st_ketcher is None:
                    st.info("Ketcher is unavailable in this environment. Restart the lab from the GUI-enabled Python environment.")
                    if KETCHER_ERROR:
                        st.caption(f"Editor import error: {KETCHER_ERROR}")
                else:
                    drawn_solute = st_ketcher(
                        st.session_state.get("applications_pk_solute", DEFAULT_SOLUTE_SMILES),
                        height=420,
                        molecule_format="SMILES",
                        key=f"applications_pk_editor_{pk_editor_version}",
                    )
                    editor_smiles, editor_error = canonicalize_smiles(drawn_solute)
                    render_structure_editor_preview(
                        "Candidate",
                        editor_smiles,
                        raw_smiles=drawn_solute,
                        error=editor_error,
                    )
                    if st.button("Use drawing in PK profile", key="applications_pk_apply_editor", use_container_width=True):
                        if editor_smiles:
                            st.session_state["applications_pk_solute"] = editor_smiles
                            st.session_state["applications_pk_solute_input_pending"] = editor_smiles
                            st.session_state["applications_pk_editor_version"] = pk_editor_version + 1
                            st.rerun()
                        st.error(editor_error or "The editor did not export a valid structure.")
            info_card(
                "Scope",
                "This page is still a solubility-facing PK proxy. It estimates dissolution pressure, food-effect direction, and formulation latitude, but it does not replace PBPK, precipitation kinetics, or transporter models.",
            )
            info_card(
                "Biorelevant media",
                "FaSSGF / FeSSGF / FaSSIF / FeSSIF are approximated from water plus pH correction and heuristic surfactant or lipid enhancement factors. Read the outputs as triage guidance, not compendial measurements.",
            )

        pk_payload = st.session_state.get("applications_pk_result")
        if pk_payload:
            if pk_payload.get("error"):
                st.error(pk_payload["error"])
            else:
                palette = theme_palette()
                gi_payload = pk_payload.get("gi_profile") or {}
                media_payload = pk_payload.get("biorelevant_media") or {}
                gi_df = pd.DataFrame(gi_payload.get("compartments", []))
                media_df = pd.DataFrame(media_payload.get("media", []))
                iv_df = pd.DataFrame(pk_payload.get("iv_screen", []))
                topical_df = pd.DataFrame(pk_payload.get("topical_screen", []))

                render_stat_tiles(
                    [
                        ("f_abs estimate", f"{100.0 * float(gi_payload.get('f_abs_estimate', 0.0)):.1f}%" if gi_payload.get("f_abs_estimate") is not None else "—", "rough absorption fraction proxy"),
                        ("Max absorbable dose", f"{float(gi_payload.get('max_absorbable_dose', 0.0)):.0f} mg" if gi_payload.get("max_absorbable_dose") is not None else "—", "largest compartmental dissolved mass"),
                        ("Rate-limiting step", str(gi_payload.get("rate_limiting_step", "—")), "dominant current bottleneck"),
                        ("Food effect", str(media_payload.get("food_effect_prediction", "—")), "FeSSIF vs FaSSIF heuristic"),
                    ]
                )

                if not gi_df.empty:
                    st.markdown("### GI tract profile")
                    gi_left, gi_right = st.columns(2, gap="large")
                    with gi_left:
                        gi_diagram = go.Figure()
                        gi_diagram.add_trace(
                            go.Scatter(
                                x=gi_df["index"],
                                y=[1.0] * len(gi_df),
                                mode="lines+markers+text",
                                text=gi_df["label"],
                                textposition="top center",
                                marker={
                                    "size": 22,
                                    "color": gi_df["dissolved_fraction"],
                                    "colorscale": [[0.0, hex_to_rgba(palette["red"], 1.0)], [0.5, hex_to_rgba(palette["orange"], 1.0)], [1.0, hex_to_rgba(palette["green"], 1.0)]],
                                    "cmin": 0,
                                    "cmax": 1,
                                    "showscale": True,
                                },
                                line={"color": palette["border"], "width": 5},
                                hovertemplate="%{text}<br>Dissolved fraction=%{marker.color:.2f}<extra></extra>",
                                showlegend=False,
                            )
                        )
                        gi_diagram.update_layout(
                            title="GI compartment map",
                            height=320,
                            xaxis={"tickmode": "array", "tickvals": gi_df["index"], "ticktext": gi_df["label"], "title": "GI position"},
                            yaxis={"visible": False},
                            margin=dict(l=24, r=24, t=48, b=24),
                        )
                        st.plotly_chart(style_plot(gi_diagram), use_container_width=True)
                    with gi_right:
                        dissolved_fig = px.line(
                            gi_df,
                            x="label",
                            y="dissolved_fraction",
                            markers=True,
                            title="Dissolved fraction by GI compartment",
                        )
                        dissolved_fig.update_layout(height=320, xaxis_title="Compartment", yaxis_title="Dissolved fraction")
                        st.plotly_chart(style_plot(dissolved_fig), use_container_width=True)

                    comp_left, comp_right = st.columns(2, gap="large")
                    with comp_left:
                        sol_fig = px.bar(
                            gi_df,
                            x="label",
                            y="solubility_mg_mL",
                            color="dissolution_limited",
                            title="Solubility across GI compartments",
                        )
                        sol_fig.update_layout(height=360, xaxis_title="Compartment", yaxis_title="Approx. solubility (mg/mL)")
                        st.plotly_chart(style_plot(sol_fig), use_container_width=True)
                    with comp_right:
                        dose_fig = px.bar(
                            gi_df,
                            x="label",
                            y="dose_number",
                            color="dissolution_limited",
                            title="Dose-number pressure by compartment",
                        )
                        dose_fig.update_layout(height=360, xaxis_title="Compartment", yaxis_title="Dose number")
                        st.plotly_chart(style_plot(dose_fig), use_container_width=True)
                    render_dataframe(
                        gi_df[[col for col in ["label", "pH", "volume_mL", "solubility_mg_mL", "dissolved_fraction", "dose_number", "dissolution_limited"] if col in gi_df.columns]],
                        use_container_width=True,
                        hide_index=True,
                    )

                if not media_df.empty:
                    st.markdown("### Biorelevant media")
                    media_left, media_right = st.columns(2, gap="large")
                    with media_left:
                        media_fig = px.bar(
                            media_df,
                            x="label",
                            y="solubility_mg_mL",
                            color="enhancement_factor",
                            title="Biorelevant media solubility comparison",
                        )
                        media_fig.update_layout(height=380, xaxis_title="Medium", yaxis_title="Approx. solubility (mg/mL)")
                        st.plotly_chart(style_plot(media_fig), use_container_width=True)
                    with media_right:
                        comparison_fig = px.scatter(
                            media_df,
                            x="pH",
                            y="solubility_mg_mL",
                            size="enhancement_factor",
                            color="label",
                            title="pH and medium-effect map",
                        )
                        comparison_fig.update_layout(height=380, xaxis_title="pH", yaxis_title="Approx. solubility (mg/mL)")
                        st.plotly_chart(style_plot(comparison_fig), use_container_width=True)
                    st.markdown(
                        f"**Food effect prediction:** `{media_payload.get('food_effect_prediction', 'undetermined')}`. {media_payload.get('administration_recommendation', '')}"
                    )
                    render_dataframe(media_df, use_container_width=True, hide_index=True)

                if not iv_df.empty:
                    st.markdown("### IV formulation screening")
                    iv_left, iv_right = st.columns(2, gap="large")
                    with iv_left:
                        iv_fig = px.bar(
                            iv_df.head(10),
                            x="vehicle_name",
                            y="iv_estimated_concentration_37C_mg_mL",
                            color="recommended",
                            title="Estimated IV-compatible concentration at 37 C",
                        )
                        iv_fig.update_layout(height=380, xaxis_title="Vehicle", yaxis_title="Estimated concentration (mg/mL)")
                        st.plotly_chart(style_plot(iv_fig), use_container_width=True)
                    with iv_right:
                        osm_fig = px.scatter(
                            iv_df,
                            x="max_fraction_vv",
                            y="iv_estimated_concentration_37C_mg_mL",
                            color="osmolality_concern",
                            symbol="research_only",
                            hover_name="vehicle_name",
                            title="IV screening: capacity vs formulation stress",
                        )
                        osm_fig.update_layout(height=380, xaxis_title="Max compatible fraction", yaxis_title="Estimated concentration (mg/mL)")
                        st.plotly_chart(style_plot(osm_fig), use_container_width=True)
                    render_dataframe(
                        iv_df[[col for col in ["vehicle_name", "vehicle_type", "max_fraction_vv", "iv_estimated_concentration_25C_mg_mL", "iv_estimated_concentration_37C_mg_mL", "osmolality_concern", "research_only", "recommended", "note"] if col in iv_df.columns]],
                        use_container_width=True,
                        hide_index=True,
                    )

                if not topical_df.empty:
                    st.markdown("### Topical vehicle screening")
                    top_left, top_right = st.columns(2, gap="large")
                    with top_left:
                        top_fig = px.bar(
                            topical_df.head(10),
                            x="vehicle_name",
                            y="thermodynamic_activity",
                            color="recommended",
                            title="Thermodynamic activity by topical vehicle",
                        )
                        top_fig.update_layout(height=380, xaxis_title="Vehicle", yaxis_title="x2 * gamma2")
                        st.plotly_chart(style_plot(top_fig), use_container_width=True)
                    with top_right:
                        perm_fig = px.scatter(
                            topical_df,
                            x="solubility_mg_mL",
                            y="permeation_potential",
                            color="vehicle_type",
                            size="thermodynamic_activity",
                            hover_name="vehicle_name",
                            title="Topical screening: solubility vs permeation potential",
                        )
                        perm_fig.update_layout(height=380, xaxis_title="Approx. solubility (mg/mL)", yaxis_title="Permeation potential")
                        st.plotly_chart(style_plot(perm_fig), use_container_width=True)
                    render_dataframe(
                        topical_df[[col for col in ["vehicle_name", "vehicle_type", "solubility_mg_mL", "gamma_2", "thermodynamic_activity", "near_saturation_score", "permeation_potential", "recommended", "note"] if col in topical_df.columns]],
                        use_container_width=True,
                        hide_index=True,
                    )

    else:
        left, right = st.columns([1.0, 1.0], gap="large")
        with left:
            checkpoint_path = render_path_select("Checkpoint", supported_checkpoints, default_checkpoint, "applications_swap_checkpoint")
            solute_smiles = st.text_input("Compound SMILES", value=st.session_state.get("applications_swap_solute", DEFAULT_SOLUTE_SMILES), key="applications_swap_solute")
            donor_names = list(SYNTHESIS_SOLVENT_LIBRARY.keys())
            donor_default_index = donor_names.index("DMSO") if "DMSO" in SYNTHESIS_SOLVENT_LIBRARY else 0
            donor_label = st.selectbox("Donor solvent", donor_names, index=donor_default_index, key="applications_swap_donor")
            donor_smiles = SYNTHESIS_SOLVENT_LIBRARY[donor_label]
            acceptor_labels = st.multiselect(
                "Target solvents",
                options=donor_names,
                default=[label for label in ["Water", "Isopropanol", "Ethyl acetate"] if label in donor_names],
                key="applications_swap_acceptors",
            )
            transfer_temp = st.number_input("Transfer temperature (K)", min_value=250.0, max_value=420.0, value=298.15, step=1.0, key="applications_swap_transfer")
            isolation_temp = st.number_input("Isolation temperature (K)", min_value=230.0, max_value=400.0, value=278.15, step=1.0, key="applications_swap_isolation")
            scan_points = int(st.number_input("Scan points", min_value=4, max_value=24, value=8, step=1, key="applications_swap_scan_points"))
            if st.button("Run solvent-swap screen", key="applications_swap_run", use_container_width=True):
                acceptor_payload = [{"label": label, "smiles": SYNTHESIS_SOLVENT_LIBRARY[label]} for label in acceptor_labels if label != donor_label]
                st.session_state["applications_swap_result"] = run_solvent_swap_screen(
                    python_command,
                    checkpoint_path,
                    solute_smiles,
                    donor_smiles,
                    donor_label,
                    json.dumps(acceptor_payload),
                    float(transfer_temp),
                    float(isolation_temp),
                    scan_points,
                )
        with right:
            render_molecule_panel(
                st.session_state.get("applications_swap_solute", DEFAULT_SOLUTE_SMILES),
                "Solvent-swap target",
                "Estimate how aggressively the compound should crash out when moved from a donor solvent into a poorer target medium.",
                width=520,
                height=340,
            )
            render_molecule_panel(
                donor_smiles,
                f"Donor solvent: {donor_label}",
                "The donor is the starting medium before precipitation or solvent exchange.",
                width=360,
                height=240,
            )

        swap_payload = st.session_state.get("applications_swap_result")
        if swap_payload:
            if swap_payload.get("error"):
                st.error(swap_payload["error"])
            else:
                rows_df = pd.DataFrame(swap_payload.get("rows", []))
                if not rows_df.empty:
                    render_stat_tiles(
                        [
                            ("Targets", str(len(rows_df)), "acceptor solvents scored"),
                            ("Best transfer score", f"{float(rows_df['transfer_score'].max()):.1f}", "higher means stronger crash-out pressure"),
                            ("Donor", str(swap_payload.get("donor_label", "—")), "reference solvent"),
                            ("Model family", str(swap_payload.get("model_family", "unknown")), "active inference backend"),
                        ]
                    )
                    plot_left, plot_right = st.columns(2, gap="large")
                    with plot_left:
                        transfer_fig = px.bar(
                            rows_df.sort_values("transfer_score", ascending=False),
                            x="acceptor_label",
                            y="transfer_score",
                            color="delta_ln_x2",
                            title="Solvent-swap transfer score",
                        )
                        transfer_fig.update_layout(height=420, xaxis_title="Target solvent", yaxis_title="Transfer score")
                        st.plotly_chart(style_plot(transfer_fig), use_container_width=True)
                    with plot_right:
                        scatter = px.scatter(
                            rows_df,
                            x="acceptor_hot_ln_x2",
                            y="acceptor_cold_ln_x2",
                            color="acceptor_label",
                            size="transfer_score",
                            hover_data=["delta_ln_x2", "crash_ratio", "regime"],
                            title="Target-solvent hot/cold map",
                        )
                        scatter.update_layout(height=420, xaxis_title="ln x2 at transfer T", yaxis_title="ln x2 at isolation T")
                        st.plotly_chart(style_plot(scatter), use_container_width=True)
                    render_dataframe(
                        rows_df[["acceptor_label", "donor_hot_ln_x2", "acceptor_hot_ln_x2", "acceptor_cold_ln_x2", "delta_ln_x2", "crash_ratio", "transfer_score", "regime"]],
                        use_container_width=True,
                        hide_index=True,
                    )
                    scan_df = pd.DataFrame(swap_payload.get("scan", []))
                    if not scan_df.empty:
                        top_labels = rows_df.sort_values("transfer_score", ascending=False).head(3)["acceptor_label"].tolist()
                        scan_fig = px.line(
                            scan_df[scan_df["acceptor_label"].isin(top_labels)],
                            x="T",
                            y="ln_x2",
                            color="acceptor_label",
                            title="Top solvent-swap candidates across temperature",
                        )
                        scan_fig.update_layout(height=360, xaxis_title="Temperature (K)", yaxis_title="Predicted ln x2")
                        st.plotly_chart(style_plot(scan_fig), use_container_width=True)


def render_planner_page() -> None:
    palette = theme_palette()
    payload = load_planner_state()
    page_header(
        "Experiment Planner",
        "Persistent planning workspace with a repo-backed kanban board, detailed experiment todo items, and a simple calendar-style scheduler for the upcoming workload.",
        eyebrow="Planner",
        chips=[
            ("Board path", relative_label(PLANNER_STATE_PATH)),
            ("Tasks", str(len(payload.get("tasks", [])))),
            ("Drag/drop", "kanban enabled" if sort_items is not None else "fallback list"),
        ],
    )

    st.markdown("### Kanban board")
    st.caption("Move experiments across stages and the planner state will be saved back into the repository.")
    if sort_items is None:
        st.warning(f"Kanban drag/drop is unavailable in this environment: {SORTABLES_ERROR}")
        render_dataframe(planner_timeline_frame(payload), use_container_width=True, hide_index=True)
    else:
        board_labels = planner_board_labels(payload)
        updated_board = sort_items(
            board_labels,
            multi_containers=True,
            direction="horizontal",
            key="planner_kanban",
            custom_style=planner_sortable_style(),
        )
        if isinstance(updated_board, list):
            payload = sync_planner_board_from_labels(payload, updated_board)
            save_planner_state(payload)

    task_map = planner_task_map(payload)
    board_preview_cols = st.columns(5, gap="small")
    for column, col in zip(["Backlog", "Ready", "Running", "Blocked", "Done"], board_preview_cols):
        with col:
            st.markdown(f"**{column}**")
            ids = payload.get("board", {}).get(column, [])
            if not ids:
                st.caption("No tasks")
            for task_id in ids[:6]:
                task = task_map.get(task_id)
                if not task:
                    continue
                label = f"{task.get('priority', 'P2')} · {task.get('title', task_id)}"
                if st.button(label, key=f"planner_focus_{column}_{task_id}", use_container_width=True):
                    st.session_state["planner_selected_task"] = f"{task_id} | {task.get('priority', 'P2')} | {task.get('title', task_id)}"
                    st.rerun()

    planner_left, planner_right = st.columns([0.9, 1.1], gap="large")
    with planner_left:
        st.markdown("### Add experiment")
        with st.form("planner_add_task", border=True):
            title = st.text_input("Title", value="")
            columns = st.columns(2)
            with columns[0]:
                priority = st.selectbox("Priority", ["P1", "P2", "P3"], index=1)
                owner = st.text_input("Owner", value="research")
                start = st.date_input("Start date", value=datetime.now().date())
            with columns[1]:
                status = st.selectbox("Stage", ["Backlog", "Ready", "Running", "Blocked", "Done"], index=0)
                estimate = st.number_input("Estimate (hours)", value=4.0, min_value=0.5, step=0.5)
                finish = st.date_input("Finish date", value=datetime.now().date())
            notes = st.text_area("Notes", value="", height=100)
            command = st.text_input("Command", value="python scripts/experiments/run_medium_budget_comparison.py")
            add_task = st.form_submit_button("Add to planner", use_container_width=True)
            if add_task and title.strip():
                task_id = slugify_label(title)[:32]
                payload["tasks"].append(
                    {
                        "id": task_id,
                        "title": title.strip(),
                        "status": status,
                        "priority": priority,
                        "owner": owner.strip() or "research",
                        "start": start.isoformat(),
                        "end": finish.isoformat(),
                        "estimate_hours": float(estimate),
                        "notes": notes.strip(),
                        "command": command.strip(),
                    }
                )
                payload.setdefault("board", {}).setdefault(status, []).append(task_id)
                save_planner_state(payload)
                st.rerun()

        st.markdown("### Intake from lab history")
        history_entries = history_record_entries(limit=20)
        if not history_entries:
            st.info("No saved inference, uncertainty, or calibration runs are available yet.")
        else:
            history_labels = [entry["label"] for entry in history_entries]
            selected_history_label = st.selectbox("Saved lab run", history_labels, key="planner_history_entry")
            selected_history_entry = history_entries[history_labels.index(selected_history_label)]
            st.markdown(
                f"""
                <div class="lab-workspace-panel">
                  <h4>{escape(str(selected_history_entry['title']))}</h4>
                  <p>{escape(str(selected_history_entry['subtitle']))}</p>
                  <p><code>{escape(relative_label(Path(str(selected_history_entry['path']))))}</code></p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Create follow-up task", use_container_width=True, key="planner_add_from_history"):
                task_id, created = add_planner_task_from_history(payload, selected_history_entry)
                save_planner_state(payload)
                st.session_state["planner_selected_task"] = next(
                    (
                        f"{task['id']} | {task.get('priority', 'P2')} | {task.get('title', task['id'])}"
                        for task in payload.get("tasks", [])
                        if str(task.get("id")) == task_id
                    ),
                    st.session_state.get("planner_selected_task", ""),
                )
                if created:
                    st.success("Follow-up task added to the planner.")
                else:
                    st.info("A planner task for this saved lab artifact already exists.")
                st.rerun()

    tasks = payload.get("tasks", [])
    if not tasks:
        st.info("Planner is empty.")
        return

    task_labels = [f"{task['id']} | {task.get('priority', 'P2')} | {task['title']}" for task in tasks]
    default_task = st.session_state.get("planner_selected_task")
    default_index = task_labels.index(default_task) if default_task in task_labels else 0
    selected_label = st.selectbox("Focused task", task_labels, index=default_index, key="planner_selected_task")
    selected_id = selected_label.split(" | ", 1)[0]
    selected_task = next(task for task in tasks if str(task.get("id")) == selected_id)

    detail_left, detail_right = planner_left, planner_right
    with detail_left:
        st.markdown("### Task details")
        st.markdown(
            f"""
            <div class="lab-workspace-panel">
              <h4 style="margin-bottom:0.35rem;">{escape(selected_task.get('title', selected_id))}</h4>
              <div class="lab-kicker-row">
                <span class="lab-kicker" style="{accent_pill_style(task_priority_color(str(selected_task.get('priority', 'P2'))))}">{escape(str(selected_task.get('priority', 'P2')))}</span>
                <span class="lab-kicker">{escape(str(selected_task.get('status', 'Backlog')))}</span>
                <span class="lab-kicker">{escape(str(selected_task.get('owner', 'research')))}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("planner_edit_task", border=True):
            edit_title = st.text_input("Title", value=selected_task.get("title", ""))
            edit_cols = st.columns(2)
            with edit_cols[0]:
                edit_priority = st.selectbox("Priority", ["P1", "P2", "P3"], index=["P1", "P2", "P3"].index(selected_task.get("priority", "P2")))
                edit_owner = st.text_input("Owner", value=selected_task.get("owner", "research"))
                edit_start = st.date_input("Start", value=datetime.fromisoformat(str(selected_task.get("start"))).date())
            with edit_cols[1]:
                edit_status = st.selectbox("Status", ["Backlog", "Ready", "Running", "Blocked", "Done"], index=["Backlog", "Ready", "Running", "Blocked", "Done"].index(selected_task.get("status", "Backlog")))
                edit_hours = st.number_input("Estimate (hours)", value=float(selected_task.get("estimate_hours", 0.0)), min_value=0.5, step=0.5)
                edit_end = st.date_input("Finish", value=datetime.fromisoformat(str(selected_task.get("end"))).date())
            edit_notes = st.text_area("Notes", value=selected_task.get("notes", ""), height=120)
            edit_command = st.text_input("Command", value=selected_task.get("command", ""))
            save_cols = st.columns(2)
            with save_cols[0]:
                save_task = st.form_submit_button("Save task", use_container_width=True)
            with save_cols[1]:
                delete_task = st.form_submit_button("Delete task", use_container_width=True)
            if save_task:
                for task in payload["tasks"]:
                    if task["id"] == selected_id:
                        task.update(
                            {
                                "title": edit_title.strip(),
                                "priority": edit_priority,
                                "owner": edit_owner.strip(),
                                "status": edit_status,
                                "start": edit_start.isoformat(),
                                "end": edit_end.isoformat(),
                                "estimate_hours": float(edit_hours),
                                "notes": edit_notes.strip(),
                                "command": edit_command.strip(),
                            }
                        )
                payload["board"] = {column: [task_id for task_id in ids if task_id != selected_id] for column, ids in payload.get("board", {}).items()}
                payload["board"].setdefault(edit_status, []).append(selected_id)
                save_planner_state(payload)
                st.rerun()
            if delete_task:
                payload["tasks"] = [task for task in payload["tasks"] if task["id"] != selected_id]
                payload["board"] = {column: [task_id for task_id in ids if task_id != selected_id] for column, ids in payload.get("board", {}).items()}
                save_planner_state(payload)
                st.rerun()

        artifact_rows = []
        if selected_task.get("artifact_path"):
            artifact_rows.append({"field": "artifact", "value": relative_label(Path(str(selected_task["artifact_path"])))})
        if selected_task.get("related_dataset"):
            artifact_rows.append({"field": "dataset", "value": relative_label(Path(str(selected_task["related_dataset"]))) if str(selected_task["related_dataset"]).strip() else "—"})
        checkpoint_refs = [relative_label(Path(str(item))) for item in selected_task.get("related_checkpoints", []) if str(item).strip()]
        if checkpoint_refs:
            artifact_rows.append({"field": "checkpoints", "value": ", ".join(checkpoint_refs)})
        if artifact_rows:
            st.markdown("### Linked artifacts")
            render_dataframe(pd.DataFrame(artifact_rows), use_container_width=True, hide_index=True)

        if selected_task.get("command"):
            st.markdown("### Launch from planner")
            st.code(str(selected_task["command"]), language="bash")
            if st.button("Launch focused experiment", use_container_width=True):
                resolved = resolve_pipeline_command(str(selected_task["command"]), st.session_state.get("lab_python_command", suggested_python_command()))
                launch_job(
                    f"Planner: {selected_task['title']}",
                    "planner",
                    resolved,
                    REPO_ROOT,
                )
                st.success("Planner task launched.")

    with detail_right:
        st.markdown("### Time schedule")
        timeline_df = planner_timeline_frame(payload)
        if not timeline_df.empty:
            timeline = px.timeline(
                timeline_df,
                x_start="Start",
                x_end="Finish",
                y="Task",
                color="Status",
                hover_data=["Owner", "Priority", "Hours", "id"],
                height=max(420, 80 + 48 * len(timeline_df)),
                color_discrete_map={
                    "Backlog": palette["slate"],
                    "Ready": palette["blue"],
                    "Running": palette["green"],
                    "Blocked": palette["red"],
                    "Done": palette["purple"],
                },
            )
            timeline.update_yaxes(autorange="reversed")
            timeline.update_layout(margin=dict(l=12, r=12, t=36, b=12), legend={"orientation": "h", "y": 1.08})
            st.plotly_chart(style_plot(timeline), use_container_width=True)

        agenda_cols = st.columns(3)
        status_counts = timeline_df["Status"].value_counts().to_dict()
        with agenda_cols[0]:
            st.metric("Running", str(status_counts.get("Running", 0)))
        with agenda_cols[1]:
            st.metric("Ready", str(status_counts.get("Ready", 0)))
        with agenda_cols[2]:
            st.metric("Planned hours", f"{timeline_df['Hours'].sum():.1f}")

        st.markdown("### Planner table")
        render_dataframe(timeline_df[["id", "Task", "Status", "Owner", "Priority", "Hours"]], use_container_width=True, hide_index=True)


def render_documentation_page() -> None:
    pages = available_doc_pages()
    page_header(
        "Documentation",
        "Read the project documentation directly inside the app. Local markdown pages are available immediately, and the published MkDocs site can be opened in an embedded frame when you want the full themed documentation experience.",
        eyebrow="Docs",
        chips=[
            ("Local pages", str(len(pages))),
            ("Docs root", relative_label(DOCS_DIR)),
            ("Published site", PUBLISHED_DOCS_URL),
        ],
    )

    doc_mode = segmented_choice(
        "Documentation workspace",
        ["Local markdown", "Published site"],
        key="documentation_workspace",
        default="Local markdown",
    )

    if doc_mode == "Published site":
        st.caption("Embedded published documentation site.")
        components.iframe(PUBLISHED_DOCS_URL, height=980, scrolling=True)
        return

    if not pages:
        st.warning("No local markdown pages found under docs/.")
        return

    selected_page = st.selectbox(
        "Documentation page",
        pages,
        format_func=lambda path: relative_label(path),
    )
    doc_text = cached_text(str(selected_page))
    header_cols = st.columns([0.75, 0.25], gap="small")
    with header_cols[0]:
        st.markdown(f"### {relative_label(selected_page)}")
    with header_cols[1]:
        st.download_button(
            "Download markdown",
            data=doc_text,
            file_name=selected_page.name,
            mime="text/markdown",
            use_container_width=True,
        )

    view_mode = segmented_choice(
        "View mode",
        ["Rendered", "Raw markdown"],
        key="documentation_view_mode",
        default="Rendered",
    )
    if view_mode == "Rendered":
        st.markdown(doc_text)
    else:
        st.code(doc_text, language="markdown")


@st.cache_data(show_spinner=False)
def reproduction_profile_descriptions() -> dict[str, str]:
    from tgnn_solv.reproduction import reproduction_profiles

    return reproduction_profiles()


def reproduction_steps_for_ui(
    profile: str,
    *,
    python_command: str,
    device: str,
) -> list[dict[str, Any]]:
    from tgnn_solv.reproduction import ReproductionSettings, build_reproduction_steps

    settings = ReproductionSettings(
        profile=profile,
        python_command=python_command,
        device=device,
        processed_dir=str(PROCESSED_DIR),
        results_dir=str(RESULTS_DIR),
        checkpoints_dir=str(CHECKPOINTS_DIR),
        figures_dir=str(FIGURES_DIR),
        tables_dir=str(TABLES_DIR),
    )
    rows: list[dict[str, Any]] = []
    for step in build_reproduction_steps(settings):
        rows.append(
            {
                "step_id": step.step_id,
                "name": step.name,
                "description": step.description,
                "category": step.category,
                "command_preview": quote_command(step.command_preview),
                "expected_outputs": list(step.expected_outputs),
                "optional": bool(step.optional),
            }
        )
    return rows


def render_reproduce_page(python_command: str) -> None:
    profile_docs = reproduction_profile_descriptions()
    profile = segmented_choice(
        "Reproduction profile",
        ["core", "article", "full"],
        key="reproduce_profile",
        default="article",
    )
    device = st.selectbox("Runtime device", ["auto", "cpu", "cuda"], index=0, key="reproduce_device")
    steps = reproduction_steps_for_ui(profile, python_command=python_command, device=device)
    selected_step_ids = [row["step_id"] for row in steps]
    default_summary = RESULTS_DIR / "reproduction" / f"{profile}_summary.json"

    page_header(
        "Paper Reproduction",
        "Structured article-reproduction workspace: pick a maintained profile, inspect the exact step graph, launch the whole run or selected steps, and track the resulting outputs under one summary artifact.",
        eyebrow="Reproduce",
        chips=[
            ("Profile", profile),
            ("Workflow steps", str(len(steps))),
            ("Results dir", relative_label(RESULTS_DIR)),
            ("Figures dir", relative_label(FIGURES_DIR)),
            ("Summary", relative_label(default_summary)),
        ],
    )

    left, right = st.columns([1.05, 0.95], gap="large")
    with left:
        st.markdown("### Profile summary")
        st.caption(profile_docs.get(profile, ""))
        launch_cols = st.columns([1.0, 1.0], gap="small")
        selected_for_step_launch = st.multiselect(
            "Selected steps",
            selected_step_ids,
            default=selected_step_ids,
            help="The full-profile launcher ignores this selection; use it with the targeted step launcher below.",
        )
        full_command = build_python_command(
            "scripts/experiments/reproduce_paper.py",
            "--profile",
            profile,
            "--device",
            device,
            "--summary-json",
            str(default_summary),
            python_command_text=python_command,
        )
        with launch_cols[0]:
            st.code(quote_command(full_command), language="bash")
            if st.button("Launch full profile", use_container_width=True):
                launch_job(
                    f"Reproduce paper ({profile})",
                    "paper",
                    full_command,
                    REPO_ROOT,
                    [str(default_summary), str(RESULTS_DIR), str(FIGURES_DIR), str(TABLES_DIR)],
                )
                st.success("Structured reproduction profile launched.")
        with launch_cols[1]:
            step_command = build_python_command(
                "scripts/experiments/reproduce_paper.py",
                "--profile",
                profile,
                "--device",
                device,
                "--summary-json",
                str(default_summary),
                *sum([["--step", step_id] for step_id in selected_for_step_launch], []),
                python_command_text=python_command,
            )
            st.code(quote_command(step_command), language="bash")
            if st.button("Launch selected steps", use_container_width=True, disabled=not selected_for_step_launch):
                launch_job(
                    f"Reproduce steps ({profile})",
                    "paper",
                    step_command,
                    REPO_ROOT,
                    [str(default_summary)],
                )
                st.success("Selected reproduction steps launched.")

        st.markdown("### Step graph")
        for index, step in enumerate(steps, start=1):
            with st.container(border=True):
                tag = f"{step['category']}"
                if step["optional"]:
                    tag = f"{tag} · optional"
                st.markdown(f"**{index}. {step['name']}**")
                st.caption(f"`{step['step_id']}` · {tag}")
                st.markdown(step["description"])
                st.code(step["command_preview"], language="bash")
                if step["expected_outputs"]:
                    output_rows = pd.DataFrame({"expected_output": [compact_path_label(item, keep_segments=4) for item in step["expected_outputs"]]})
                    render_dataframe(output_rows, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Output status")
        status_rows = [
            {"path": "results/", "exists": RESULTS_DIR.exists()},
            {"path": "figures/", "exists": FIGURES_DIR.exists()},
            {"path": "tables/", "exists": TABLES_DIR.exists()},
            {"path": relative_label(default_summary), "exists": default_summary.exists()},
            {"path": "reproduce.sh", "exists": (REPO_ROOT / "reproduce.sh").exists()},
            {"path": "scripts/experiments/reproduce_paper.py", "exists": (REPO_ROOT / "scripts" / "experiments" / "reproduce_paper.py").exists()},
            {"path": "python command", "exists": bool(python_command.strip())},
        ]
        render_dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)
        st.markdown("### Legacy shell entrypoint")
        shell_path = REPO_ROOT / "reproduce.sh"
        if shell_path.exists():
            st.code(shell_path.read_text(encoding="utf-8"), language="bash")
            st.caption("`reproduce.sh` is now a compatibility shim that delegates to the structured Python runner with `--profile article` by default.")
        else:
            st.warning("reproduce.sh is missing.")
        st.markdown("### Workflow presets")
        for index, (name, description, command) in enumerate(WORKFLOW_STEPS, start=1):
            with st.container(border=True):
                st.markdown(f"**{index}. {name}**")
                st.caption(description)
                st.code(quote_command(command), language="bash")


def render_job_center() -> None:
    page_header(
        "Job Center",
        "Background jobs persist across reruns. Every job stores structured state and a log file under results/lab_runs.",
        eyebrow="Execution",
        chips=[
            ("State dir", relative_label(RUNS_DIR / "states")),
            ("Log dir", relative_label(RUNS_DIR / "logs")),
            ("Process model", "runner + target pid"),
        ],
    )
    jobs = load_jobs()
    if not jobs:
        st.info("No jobs have been launched yet.")
        return

    status_df = job_status_counts(jobs)
    status_cols = st.columns(5)
    for col, row in zip(status_cols, status_df.to_dict(orient="records")):
        with col:
            st.metric(row["status"].title(), str(row["count"]))

    filter_col, refresh_col = st.columns([1.0, 0.35])
    with filter_col:
        status_filter = st.multiselect("Filter by status", ["queued", "running", "stopping", "completed", "failed"], default=[])
    with refresh_col:
        if st.button("Refresh", use_container_width=True):
            st.rerun()

    filtered_jobs = [job for job in jobs if not status_filter or job.get("status") in status_filter]

    for job in filtered_jobs:
        state_path = Path(str(job["_state_path"]))
        log_path = Path(str(job.get("log_path", "")))
        with st.container(border=True):
            top_left, top_mid, top_right, top_last = st.columns([1.25, 0.8, 0.6, 0.65])
            with top_left:
                st.markdown(f"**{job.get('name', 'Unnamed job')}**")
                st.caption(job.get("category", "uncategorized"))
            with top_mid:
                st.markdown(status_badge_html(str(job.get("status", "unknown"))), unsafe_allow_html=True)
                st.caption(format_duration(job.get("started_at"), job.get("finished_at")))
            with top_right:
                st.caption("created")
                st.write(format_timestamp(job.get("created_at")))
            with top_last:
                if job.get("status") == "running":
                    if st.button("Stop", key=f"stop_{job.get('id')}", use_container_width=True):
                        if stop_job(job):
                            st.success("Stop signal sent.")
                        else:
                            st.error("Could not stop this job.")

            st.code(quote_command(job.get("command", [])), language="bash")
            st.caption(f"cwd: {job.get('cwd', '')}")

            meta_cols = st.columns(3)
            with meta_cols[0]:
                st.write("started", format_timestamp(job.get("started_at")))
            with meta_cols[1]:
                st.write("finished", format_timestamp(job.get("finished_at")))
            with meta_cols[2]:
                st.write("return code", job.get("returncode", "—"))

            if log_path.exists():
                log_text = tail_log(log_path)
                st.text_area("Log tail", value=log_text, height=220, key=f"log_{job.get('id')}")
                st.download_button(
                    "Download full log",
                    data=log_path.read_text(encoding="utf-8", errors="ignore"),
                    file_name=log_path.name,
                    mime="text/plain",
                    key=f"log_dl_{job.get('id')}",
                )
            else:
                st.info("Log file has not been created yet.")

            expected_outputs = job.get("expected_outputs", [])
            if expected_outputs:
                with st.expander("Expected outputs", expanded=False):
                    for path in expected_outputs:
                        exists = Path(path).exists()
                        st.write("exists" if exists else "missing", path)

            with st.expander("Job state JSON", expanded=False):
                st.json(read_json(state_path))


def render_environment_page(python_command: str, probe: dict[str, Any]) -> None:
    page_header(
        "Environment Doctor",
        "Validate the selected Python interpreter, dependency stack, and repo-facing runtime assumptions before you launch heavy jobs.",
        eyebrow="Runtime",
        chips=[
            ("Selected command", python_command),
            ("CUDA", "yes" if probe.get("cuda_available") else "no"),
            ("MPS", "yes" if probe.get("mps_available") else "no"),
        ],
    )

    if not probe.get("ok"):
        st.error(probe.get("error", "Probe failed."))
        st.code(f"{python_command} -c '<probe>'", language="bash")
        return

    meta_left, meta_right = st.columns([0.8, 1.2], gap="large")
    with meta_left:
        rows = [
            {"field": "python", "value": probe.get("python")},
            {"field": "platform", "value": probe.get("platform")},
            {"field": "CUDA available", "value": probe.get("cuda_available")},
            {"field": "MPS available", "value": probe.get("mps_available")},
            {"field": "repo root", "value": str(REPO_ROOT)},
            {"field": "src root", "value": str(SRC_ROOT)},
        ]
        render_dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with meta_right:
        module_rows = []
        for name, payload in probe.get("modules", {}).items():
            module_rows.append(
                {
                    "module": name,
                    "status": "ok" if payload.get("ok") else "broken",
                    "version": payload.get("version"),
                    "error": payload.get("error"),
                }
            )
        render_dataframe(pd.DataFrame(module_rows), use_container_width=True, hide_index=True)

    broken = [name for name, payload in probe.get("modules", {}).items() if not payload.get("ok")]
    if broken:
        st.warning("Broken imports detected: " + ", ".join(broken))
        if "tgnn_solv.inference" in broken or "torch_geometric" in broken or "scipy" in broken:
            st.info(
                "If this is the minimal GUI environment, keep Streamlit here and point the sidebar Python command at the real training environment, for example `conda run -n tgnn-solv python`."
            )
    else:
        st.success("The selected Python interpreter passed all module probes.")

    st.markdown("### Recommended install")
    st.code("pip install -e '.[gui,dev]'", language="bash")


def render_sidebar() -> tuple[str, dict[str, Any]]:
    st.sidebar.title("Experiment Lab")
    if st.session_state.get("_lab_probe_cache_version") != PROBE_CACHE_VERSION:
        probe_selected_python.clear()
        st.session_state["_lab_probe_cache_version"] = PROBE_CACHE_VERSION
    if st.sidebar.button("Clear UI caches", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.sidebar.success("Cleared Streamlit caches for this app session.")
    python_command = st.sidebar.text_input(
        "Python command",
        value=st.session_state.get("lab_python_command", suggested_python_command()),
        help="Interpreter used for training/evaluation/inference subprocesses. It can be a path like `/path/to/python` or a launcher like `conda run -n tgnn-solv python`.",
    )
    st.session_state["lab_python_command"] = python_command
    probe = probe_selected_python(python_command)

    summary = filesystem_summary()
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Repo state**")
    st.sidebar.write(f"Processed CSVs: {summary['processed_splits']}")
    st.sidebar.write(f"Checkpoints: {summary['checkpoints']}")
    st.sidebar.write(f"Artifacts: {summary['artifacts']}")
    st.sidebar.write(f"Jobs: {summary['jobs']}")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Selected runtime**")
    if probe.get("ok"):
        st.sidebar.write(f"CUDA: {'yes' if probe.get('cuda_available') else 'no'}")
        st.sidebar.write(f"MPS: {'yes' if probe.get('mps_available') else 'no'}")
        inference_ok = module_ok(probe, "tgnn_solv.inference")
        st.sidebar.write(f"Inference stack: {'ok' if inference_ok else 'broken'}")
    else:
        st.sidebar.error("Probe failed")

    jobs = load_jobs()
    running = [job for job in jobs if job.get("status") == "running"]
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Live jobs**")
    if running:
        for job in running[:4]:
            st.sidebar.markdown(
                f"{status_badge_html(str(job.get('status', 'unknown')))} {job.get('name', 'job')}",
                unsafe_allow_html=True,
            )
    else:
        st.sidebar.caption("No running jobs")

    if not probe.get("ok"):
        st.sidebar.markdown(
            "<div class='lab-sidebar-note'>The selected Python command is not healthy enough for model-facing work. Use the Environment page to inspect the exact failure.</div>",
            unsafe_allow_html=True,
        )

    return python_command, probe


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    ensure_runtime_cache_consistency()
    inject_css()
    ensure_layout()

    python_command, probe = render_sidebar()
    current_page = st.session_state.get("lab_page", "Overview")
    selected_page = workspace_button_panel(current_page)
    if selected_page != current_page:
        st.session_state["lab_page"] = selected_page
        st.rerun()
    page = st.session_state.get("lab_page", "Overview")

    if page == "Overview":
        render_overview(python_command, probe)
    elif page == "Data":
        render_data_page()
    elif page == "Training":
        render_training_page(python_command, probe)
    elif page == "Pipeline Studio":
        render_pipeline_studio(python_command)
    elif page == "Experiments":
        render_launcher_page(python_command, probe)
    elif page == "HPO Lab":
        render_hpo_page(python_command, probe)
    elif page == "Model Architect":
        render_model_architect(python_command, probe)
    elif page == "Results & Plots":
        render_results_page(python_command)
    elif page == "Inference":
        render_inference_page(python_command, probe)
    elif page == "Applications":
        render_applications_page(python_command, probe)
    elif page == "Planner":
        render_planner_page()
    elif page == "Documentation":
        render_documentation_page()
    elif page == "Reproduce":
        render_reproduce_page(python_command)
    elif page == "Job Center":
        render_job_center()
    elif page == "Environment":
        render_environment_page(python_command, probe)
    else:
        render_overview(python_command, probe)


if __name__ == "__main__":
    main()
