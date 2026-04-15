# TGNN-Solv

TGNN-Solv is a physics-informed graph neural network for solid-liquid
equilibrium (SLE) solubility prediction. The main model does not predict
solubility directly by default: it predicts crystal and interaction
parameters, passes them through a differentiable thermodynamic solver, and
trains end-to-end through that physics bottleneck.

The repository also contains the key no-physics and descriptor baselines used
to judge whether that bottleneck helps:

- `TGNN-Solv`: physics-first GNN with SLE + NRTL
- `TGNN-Solv + descriptors`: same solver path with pair-level RDKit descriptor fusion
- `TGNN-Solv + GPS`: same downstream physics path with a GPS encoder
- `TGNN-Solv + TIMP`: same downstream physics path with thermodynamics-informed message passing
- `TGNN-Solv + TIMP + Hansen contrastive`: TIMP with representation-level Hansen regularization
- `TGNN-Solv + Stage 0`: warm-started encoder/readout before the main curriculum
- `DirectGNN`: matched GNN backbone with direct `ln(x2)` prediction
- `DirectGNN + descriptors`: DirectGNN plus shared RDKit descriptor side-channel
- `RF` baselines on RDKit descriptors, Morgan fingerprints, or both
- optional external baselines: FastSolv and SolProp, including native SolProp
  retraining on TGNN-Solv targets

Documentation site:

- https://doctawho42.github.io/tgnn-solv/

## Installation

```bash
git clone https://github.com/doctawho42/tgnn-solv.git
cd tgnn-solv

conda create -n tgnn-solv python=3.11
conda activate tgnn-solv

pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
pip install -e ".[dev]"
```

For the interactive GUI as well:

```bash
pip install -e ".[gui,dev]"
```

For the external baseline wrappers as well:

```bash
pip install -e ".[baselines]"
```

## Experiment Lab

The repository includes a maintained Streamlit control surface for the full
workflow:

```bash
python scripts/launch_lab.py
```

or:

```bash
python scripts/gui/launch_lab.py
```

The lab covers:

- training, experiment, evaluation, and reproduction launchers
- `Pipeline Studio` for repo-backed DAG editing and shell export
- `Model Architect` for visual TGNN-Solv / DirectGNN editing
- `Inference` with persistent history, uncertainty, calibration, and OOD
- `Applications` for solvent screening, process optimization, drug
  developability, and PK-relevant solubility profiling
- `Results & Plots` with `Benchmark Studio`, artifact registry, lineage graph, and diff
- `Planner` with a kanban board, schedule, and follow-up tasks from lab history
- in-app documentation browsing

The UI process can run in a lighter environment than the model runtime. The
sidebar `Python command` field decides which interpreter is used for training,
evaluation, checkpoint inspection, and inference subprocesses.

## Docker

The repository ships a current Docker image and compose file for the
maintained surfaces:

```bash
docker compose up lab
docker compose up docs
```

Available services include:

- `lab`
  - Streamlit Experiment Lab on `localhost:8501`
- `docs`
  - MkDocs site on `localhost:8000`
- `train`
  - one tuned TGNN training run on the canonical split
- `evaluate`
  - checkpoint evaluation
- `external-benchmarks`
  - FastSolv / native SolProp benchmark wrapper with optional baseline deps

## Project Layout

The preferred human-facing CLI layout is now grouped by purpose:

- `scripts/data/`
- `scripts/training/`
- `scripts/evaluation/`
- `scripts/experiments/`
- `scripts/external/`
- `scripts/applications/`

Additional research diagnostics and interpretation helpers live under:

- `scripts/analysis/`

The old top-level `scripts/*.py` entry points are still present as a
compatibility layer for tests, imports, and existing automation such as
`reproduce.sh`.

The internal Python package now follows the same principle:

- preferred grouped namespaces for navigation:
  - `tgnn_solv.core`
  - `tgnn_solv.chemistry`
  - `tgnn_solv.data`
  - `tgnn_solv.models`
  - `tgnn_solv.physics`
  - `tgnn_solv.training`
  - `tgnn_solv.evaluation`
  - `tgnn_solv.baselines`
  - `tgnn_solv.research`
  - `tgnn_solv.applications`
- legacy flat modules such as `tgnn_solv.model` and `tgnn_solv.trainer`
  remain supported as the compatibility layer

## Canonical Workflow

Prepare the processed splits:

```bash
python scripts/data/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42
```

Train one TGNN-Solv model with the original broad paper curriculum:

```bash
python scripts/training/train.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --device cuda
```

For the maintained tuned TGNN baseline used in current architecture
comparisons, prefer:

```bash
python scripts/training/train.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_tuned.pt \
    --device cuda
```

Run the canonical multi-seed comparison:

```bash
python scripts/experiments/run_seeds.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/multi_seed_results.json \
    --checkpoint-dir checkpoints/seeds \
    --device cuda
```

Evaluate a checkpoint:

```bash
python scripts/evaluation/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_tuned.pt \
    --output results/full_evaluation.json \
    --verbose
```

Run the maintained article-reproduction profile:

```bash
python scripts/experiments/reproduce_paper.py --profile article
```

The legacy shell entrypoint still works and delegates to the same structured runner:

```bash
bash reproduce.sh
```

## Most Useful Extra Experiments

DirectGNN tuned baseline:

```bash
python scripts/training/train_directgnn.py \
    --config configs/paper_config_directgnn_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn.pt \
    --device cuda
```

DirectGNN with shared RDKit descriptor augmentation:

```bash
python scripts/training/train_directgnn.py \
    --config configs/paper_config_directgnn_descriptors.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn_desc.pt \
    --device cuda
```

TGNN with Stage 0 pretraining:

```bash
python scripts/training/train_with_pretrain.py \
    --config configs/paper_config_tuned_pretrained.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_pretrained.pt \
    --pretrain-data zinc250k \
    --pretrain-epochs 30 \
    --device cuda
```

TGNN with the GPS encoder:

```bash
python scripts/training/train.py \
    --config configs/paper_config_tuned_gps.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_gps.pt \
    --device cuda
```

TGNN with the TIMP encoder:

```bash
python scripts/training/train.py \
    --config configs/paper_config_timp.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_timp.pt \
    --device cuda
```

TIMP with Hansen-contrastive regularization:

```bash
python scripts/training/train.py \
    --config configs/paper_config_hansen_contrastive.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_timp_hansen.pt \
    --device cuda
```

TGNN with pair-level descriptor augmentation:

```bash
python scripts/training/train.py \
    --config configs/paper_config_tuned_tgnn_descriptors.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_desc.pt \
    --device cuda
```

Split-wise comparison across scaffold, solute, and solvent protocols:

```bash
python scripts/experiments/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline,rf_morgan,rf_hybrid" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

Full-budget TGNN-vs-DirectGNN diagnostic run with intermediate physics export:

```bash
python scripts/experiments/run_full_budget_experiment.py \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --seeds 42 \
    --output-dir results/full_budget_experiment \
    --device cuda
```

Medium-budget architecture comparison on the full scaffold split:

```bash
python scripts/experiments/run_medium_budget_comparison.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/medium_budget \
    --device cuda
```

External article-comparison baselines on the same split:

```bash
python scripts/experiments/run_external_baseline_benchmark.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --out-dir results/external_baselines/article_benchmark \
    --split-mode solute_scaffold \
    --fastsolv-mode both \
    --solprop-mode native
```

Benchmark an arbitrary custom model predictions CSV:

```bash
python scripts/evaluation/benchmark_custom_model.py \
    --model-name my_model \
    --test-data notebooks/data/processed/test.csv \
    --predictions-csv results/custom_predictions.csv \
    --pred-lnx2-col ln_x2_pred \
    --out-dir results/custom_benchmarks/my_model
```

Benchmark a custom Python model through the formal adapter API:

```bash
python scripts/evaluation/benchmark_adapter_model.py \
    --adapter your_package.your_adapter:YourAdapter \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --out-dir results/custom_benchmarks/your_adapter
```

Freeze a paper-facing benchmark release with checksums:

```bash
python scripts/experiments/build_benchmark_release.py \
    --release-name article-benchmark \
    --version 0.1.0 \
    --processed-dir notebooks/data/processed \
    --bundle-root results/external_baselines/article_benchmark \
    --bundle-root results/custom_benchmarks \
    --out-dir results/releases/article_benchmark_v0_1_0
```

Selected post-hoc analysis utilities:

```bash
python scripts/analysis/diagnose_gradient_flow.py --help
python scripts/analysis/analyze_timp_channels.py --help
python scripts/analysis/sensitivity_analysis.py --help
python scripts/analysis/weight_analysis.py --help
```

The full-budget runner saves:

- aggregate metrics for TGNN, DirectGNN, and oracle-evaluated TGNN
- `tgnn_intermediates.csv` with `T_m`, `dH_fus`, NRTL, solver, and correction
  intermediates
- parity and consistency diagnostics for the predicted physical parameters

The medium-budget runner writes:

- `results/medium_budget/summary.json`
- `results/medium_budget/comparison_table.md`
- `results/medium_budget/per_model/<model>/...`

## Inference, Uncertainty, and OOD

The maintained inference helpers are library APIs:

- `tgnn_solv.inference.load_model`
- `tgnn_solv.inference.predict_solubility`
- `tgnn_solv.inference.temperature_scan`
- `tgnn_solv.inference.interpret_prediction`

Example:

```python
from tgnn_solv.inference import load_model, predict_solubility

model, cfg = load_model("checkpoints/tgnn_solv_trained.pt")
result = predict_solubility(
    model,
    solute_smiles="CC(=O)Nc1ccc(O)cc1",
    solvent_smiles="CCO",
    T=298.15,
)
print(result["ln_x2"], result["T_m"], result["tau_12"])
```

Post-hoc uncertainty and OOD helpers are also maintained:

- `tgnn_solv.uncertainty.MCDropoutPredictor`
- `tgnn_solv.uncertainty.EnsemblePredictor`
- `tgnn_solv.uncertainty.calibration_report`
- `tgnn_solv.domain.ApplicabilityDomain`

`MCDropoutPredictor` and `EnsemblePredictor` now support both maintained model
families:

- `TGNN-Solv`
- `DirectGNN`

Current OOD screening uses:

- Mahalanobis distance in pair latent space
- nearest-neighbor Morgan Tanimoto similarity for solute and solvent

It is not applied automatically inside `predict_solubility`; call
`ApplicabilityDomain` alongside inference when you want an explicit in-domain /
OOD check.

The same maintained surfaces are also exposed interactively in `Experiment Lab`
through:

- `Inference -> Run & inspect`
- `Inference -> History & compare`
- `Inference -> Uncertainty lab`
- `Inference -> Calibration dashboard`

For bundle-level robustness slices after you already have `predictions.csv`,
use:

```bash
python scripts/evaluation/run_thermo_stress_suite.py \
    --predictions-csv results/custom_benchmarks/my_model/predictions.csv \
    --train-data notebooks/data/processed/train.csv \
    --output results/custom_benchmarks/my_model/stress_suite.json
```

## Optional Stage 0 Pretraining

Beyond the main three-phase curriculum, the repo also supports standalone
encoder/readout pretraining through `tgnn_solv.pretrain.Pretrainer`.

This is separate from `Phase 1` in `trainer.py`:

- Stage 0
  - optional pre-curriculum molecular pretraining
- Phase 1
  - supervised auxiliary warmup on the processed training split

Minimal example:

```python
from tgnn_solv.pretrain import Pretrainer, download_zinc250k

smiles = download_zinc250k()
pretrainer = Pretrainer(model.gnn, model.readout, cfg)
history = pretrainer.pretrain(smiles, n_epochs=30)
```

The pretrainer modifies `model.gnn` and `model.readout` in place and discards
its temporary auxiliary heads after pretraining.

The maintained CLI surfaces are now:

- `python scripts/training/train.py --pretrain ...`
- `python scripts/training/train.py --pretrain-checkpoint ...`
- `python scripts/training/train_with_pretrain.py ...`

## Key Architecture Features

- shared or split-late dual-graph GNN encoder with `mpnn`, `gps`, or `timp`
  backbones
- cross-attention or bipartite solute-solvent interaction
- hardcoded SLE + NRTL solver with optional implicit differentiation
- bounded parameter-space correction head instead of a free direct bypass
- same-pair temperature batching and temperature-consistency regularization
- optional Morgan augmentation for TGNN-Solv and DirectGNN
- optional Gasteiger-charge and physical-edge augmentation for TIMP runs
- optional descriptor-conditioned or fixed group-count priors for `Hansen` and
  `V_m`
- optional crystal GC priors for `T_m`, `dH_fus`, and fixed `dCp_fus`
- train-only affine calibration of `T_m_gc` before it reaches `FusionHead`
- zero-initialized GC residual heads with optional early-Phase-1 freezing
- optional train-only Hansen-contrastive regularization for molecular, TIMP,
  and pair representations
- optional auxiliary direct-solubility head for interaction-gradient rescue
- optional training-time oracle injection for supervised crystal parameters
- optional Walden-rule consistency penalty
- resumable training checkpoints in the main TGNN and DirectGNN CLIs
- checkpoint sidecars:
  - `<checkpoint>.manifest.json`
  - `<checkpoint>.model_card.json`

## Provided Config Variants

- `configs/paper_config.yaml`
  - canonical TGNN-Solv training config
- `configs/paper_config_tuned.yaml`
  - maintained tuned TGNN baseline for architecture comparisons
- `configs/paper_config_tuned_tgnn_descriptors.yaml`
  - tuned TGNN with descriptor augmentation
- `configs/paper_config_tuned_regularized.yaml`
  - tuned TGNN with stronger regularization and early stopping
- `configs/paper_config_tuned_regularized_gc.yaml`
  - regularized TGNN with GC priors
- `configs/paper_config_tuned_regularized_descriptors.yaml`
  - regularized TGNN with descriptor augmentation
- `configs/paper_config_tuned_gps.yaml`
  - tuned TGNN with the GPS encoder
- `configs/paper_config_timp.yaml`
  - tuned TGNN with the TIMP encoder, Gasteiger charges, and physical edge
    features
- `configs/paper_config_timp_full.yaml`
  - TIMP plus thermo-biased cross-attention
- `configs/paper_config_hansen_contrastive.yaml`
  - TIMP plus Hansen-contrastive regularization and pseudo-Hansen fallback
- `configs/paper_config_tuned_pretrained.yaml`
  - tuned TGNN intended for Stage 0 + curriculum runs
- `configs/paper_config_tuned_pretrained_descriptors.yaml`
  - Stage 0 + descriptor-augmented TGNN
- `configs/paper_config_split_late.yaml`
  - same budget, `split_late` encoder
- `configs/paper_config_gc_priors.yaml`
  - crystal GC prior path with calibrated `T_m_gc` and residual warm-start
- `configs/paper_config_oracle.yaml`
  - training-time oracle substitution of supervised `T_m` / `dH_fus` in the
    solver
- `configs/paper_config_no_bridge.yaml`
  - disables bridge loss and enables Walden check
- `configs/paper_config_no_bridge_no_walden.yaml`
  - disables both bridge and Walden soft constraints
- `configs/paper_config_combined.yaml`
  - GC priors + no bridge + Walden + oracle injection
- `configs/paper_config_tuned_interaction_rescue.yaml`
  - tuned TGNN with a train-only auxiliary direct-solubility rescue head
- `configs/paper_config_directgnn_tuned.yaml`
  - maintained tuned DirectGNN baseline
- `configs/paper_config_directgnn_descriptors.yaml`
  - DirectGNN with shared RDKit descriptor augmentation
- `configs/paper_config_uniquac.yaml`
  - research activity-model comparison config
- `configs/paper_config_wilson.yaml`
  - research activity-model comparison config
- `configs/small_debug.yaml`
  - short debug budget

## Documentation Map

- `docs/index.md`: published documentation-site landing page
- `docs/getting_started/installation.md`: environment setup, extras, Docker,
  and validation
- `docs/getting_started/quick_start.md`: shortest path from clone to first
  tuned TGNN run
- `docs/architecture.md`: forward paths, loss structure, and current design
  choices
- `docs/config_cookbook.md`: when to use each maintained or research config
- `docs/data_preparation.md`: raw sources, processed CSV layout, split modes
- `docs/training.md`: training CLIs, standalone pretraining, config variants,
  and experiment runners
- `docs/evaluation.md`: inference API, uncertainty, OOD/applicability-domain,
  evaluation entry points, and diagnostic outputs
- `docs/experiments.md`: architecture-comparison, reproduction, and benchmark
  workflow guide
- `docs/applications.md`: solvent screening, process optimization,
  developability, BCS-facing heuristics, PK solubility profiling, and scope
  boundaries
- `docs/experiment_lab.md`: interactive GUI for orchestration, inference,
  lineage, planning, and documentation browsing
- `docs/baselines.md`: DirectGNN, RF, FastSolv, SolProp, and Ideal-SLE
  workflows plus canonical benchmark bundle semantics
- `docs/results.md`: benchmark bundle sidecars, release manifests, and result
  interpretation guidance
- `docs/model_zoo.md`: checkpoint conventions and current public-model status
- `docs/notebooks.md`: notebook walk-throughs mapped to maintained workflows
- `docs/reproducing_paper.md`: structured `core` / `article` / `full`
  reproduction profiles and validation guidance
- `docs/script_reference.md`: maturity map for scripts and notebooks
- `docs/faq.md`: practical and conceptual project questions
- `docs/troubleshooting.md`: setup, runtime, and workflow failure cases
- `docs/repository_audit.md`: current repo strengths, gaps, and known
  limitations
- `scripts/README.md`: grouped CLI layout and legacy-wrapper policy
- `tools/experiment_lab/README.md`: implementation notes for the Streamlit lab
- `scripts/launch_lab.py`: preferred CLI launcher for the lab
- `scripts/gui/launch_lab.py`: alternate namespaced launcher for the lab
- `src/tgnn_solv/README.md`: grouped internal package layout and preferred
  import surface
- `AGENTS.md`: concise architecture and workflow notes for coding agents
- `CONTRIBUTING.md`: contribution expectations and validation checklist

## Practical Notes

- The canonical processed data lives under `notebooks/data/processed/`.
- The canonical processed corpus now keeps supervised solvent-side water rows
  by default; use `--no-include-water-solubility` or
  `include_water_solubility: false` for the legacy ablation path.
- `scripts/training/train.py` uses pair-aware train batching by default.
- `scripts/training/train.py` and `scripts/training/train_directgnn.py` support
  `--checkpoint-every` and `--resume` for mid-run recovery.
- The repo includes an optional Stage 0 pretraining path via
  `tgnn_solv.pretrain.Pretrainer`, `scripts/training/train.py --pretrain`, and
  `scripts/training/train_with_pretrain.py`.
- `scripts/training/train.py` can also reuse `--pretrain-checkpoint` and run
  the built-in `g_sol -> descriptors` probe with `--run-descriptor-probe`.
- Research training aids include `paper_config_hansen_contrastive.yaml` for
  TIMP-channel Hansen regularization and
  `paper_config_tuned_interaction_rescue.yaml` for the auxiliary direct
  solubility rescue head.
- `TGNNSolvConfig.bridge_loss_weight` defaults to `0.0`, but
  `configs/paper_config.yaml` still enables bridge loss explicitly through the
  phase loss-weight overrides.
- Walden checking is optional and off by default.
- Oracle injection is never used in normal inference; it is training-only
  unless a diagnostic script explicitly forces it.
- Inference-time OOD checking is available via
  `tgnn_solv.domain.ApplicabilityDomain`.
- `paper_config_combined.yaml` enables oracle injection by default; the
  medium-budget architecture comparison derives a no-oracle training config
  from it and still runs oracle evaluation afterward.
- `use_gc_priors_crystal=True` now fits `gc_prior_tm_scale` and
  `gc_prior_tm_bias` on the training split only.
- DirectGNN descriptor augmentation sanitizes NaN/Inf RDKit descriptors and
  stores descriptor normalization stats in the checkpoint.
- Post-hoc research diagnostics now include gradient-flow comparison,
  TIMP-channel probing, local solver-sensitivity analysis, and architectural
  weight-distribution analysis under `scripts/analysis/`.
- FastSolv and SolProp are optional external dependency stacks; the repository
  degrades gracefully when they are absent.
- This documentation intentionally does not promise fixed benchmark numbers from
  the repo alone. Treat the generated JSON artifacts in your own run as the
  authoritative outputs.
