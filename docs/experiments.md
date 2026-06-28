# Experiments and Benchmarks

This page summarizes the maintained experiment surfaces that are most useful
for architecture decisions and reproducible comparisons.

## At a Glance

### Reproduce the maintained article workflow

Use the structured reproduction runner when you want the maintained
end-to-end article workflow.

- [Open reproduction guide](reproducing_paper.md)

### Run the medium-budget comparison

Use the full-scaffold medium-budget runner for architecture triage across TGNN
variants, DirectGNN variants, and RF.

### Run the full-budget diagnostic study

Use the matched-budget TGNN-vs-DirectGNN study when you need physical
intermediates and oracle diagnostics.

### Run the multi-seed diagnostic wrapper

Use the phase-1 diagnostic wrapper when you want TGNN, DirectGNN, optional RF
baselines, oracle exports, and paired tests in one output tree.

### Compare split protocols

Use the split-comparison runner when you need scaffold, solute, and solvent
generalization results from one consistent code path.

## Canonical Reproduction

The maintained reproduction runner is:

```bash
python scripts/experiments/reproduce_paper.py --profile article
```

The legacy shell wrapper still works:

```bash
bash reproduce.sh
```

Use this when you want the closest thing to the repository's current
article-comparison workflow. It orchestrates data preparation, tuned TGNN
multi-seed training, medium-budget comparison, external FastSolv/SolProp
benchmarking, evaluation, split comparisons, supplementary tables, and figure
generation.

See [Reproducing the Paper](reproducing_paper.md) for the exact sequence and
scope boundary.

## Medium-Budget Architecture Comparison

This is the maintained architecture-triage runner on the full scaffold split:

```bash
python scripts/experiments/run_medium_budget_comparison.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/medium_budget \
    --device cuda
```

It evaluates:

- tuned TGNN
- TGNN + GC priors
- TGNN + no bridge
- TGNN + GC priors + no bridge
- tuned DirectGNN
- DirectGNN + descriptors
- RF on descriptors

Current follow-up lanes built around the same scaffold split and matched-budget
logic include:

- TGNN + descriptor augmentation
- TGNN + GPS encoder
- TGNN + TIMP encoder
- TGNN + TIMP + thermo cross-attention
- TIMP + Hansen-contrastive regularization
- interaction-gradient rescue via the auxiliary direct-solubility head
- Stage 0 pretrained TGNN variants

Expected outputs:

- `results/medium_budget/summary.json`
- `results/medium_budget/comparison_table.md`
- `results/medium_budget/per_model/<model>/...`

Use this runner when you want a fair comparison between the main maintained
architectural choices without paying full paper-scale cost.

## Full-Budget TGNN-vs-DirectGNN Diagnostic Study

Use the full-budget experiment when you need rich physical diagnostics in
addition to headline metrics:

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

This experiment exports:

- TGNN metrics
- DirectGNN metrics
- oracle-evaluated TGNN metrics
- `tgnn_intermediates.csv`
- detailed diagnostics JSON

Use it when you need to inspect whether errors are coming from:

- crystal property prediction
- NRTL parameterization
- correction magnitude
- oracle-vs-predicted solver inputs

This runner is also the main source of `tgnn_intermediates.csv` for post-hoc
diagnostics such as:

- `scripts/analysis/sensitivity_analysis.py`
- `scripts/analysis/weight_analysis.py`

## Split-Wise Comparison

Use the split-comparison runner when you need the same model family evaluated
under different generalization protocols:

```bash
python scripts/experiments/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline,rf_morgan,rf_hybrid" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

This is the safest way to avoid split drift when comparing:

- scaffold generalization
- exact-solute generalization
- solvent-held-out generalization

## Multi-Seed Diagnostic Wrapper

Use the phase-1 diagnostic wrapper when you want one multi-seed tree covering
TGNN, DirectGNN, optional RF baselines, oracle exports, and significance tests:

```bash
python scripts/experiments/run_phase1_diagnostic.py \
    --seeds 42,123,456 \
    --budget 50,200,50 \
    --config configs/paper_config_tuned.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --output-dir results/phase1_diagnostic \
    --device cuda
```

Typical outputs include:

- per-seed `tgnn`, `tgnn_oracle`, `directgnn`, and optional `rf` subtrees
- `aggregate_metrics.json`
- `statistical_tests.json`
- `summary.md`

Use this when you want stronger seed-level evidence than a single
full-budget run, but still want richer diagnostics than a minimal metrics-only
wrapper.

## Hyperparameter Tuning

For CLI-driven tuning:

```bash
python scripts/experiments/run_optuna.py \
    --models tgnn_solv,tgnn_solv_gps,tgnn_solv_descriptors,direct_gnn,direct_gnn_descriptors \
    --n-trials 20
```

For interactive tuning and analysis, use
[08_optuna_tuning.ipynb](https://github.com/doctawho42/tgnn-solv/blob/main/notebooks/08_optuna_tuning.ipynb).

Current scope note:

- `Stage 0` pretraining is intentionally not part of the default Optuna loop
  because rerunning ZINC-scale pretraining inside every trial would dominate
  the cost of the actual TGNN search

## Visual Orchestration

For the same workflows in an interactive control surface, use
[Experiment Lab](experiment_lab.md):

- `Pipeline Studio`
  - Airflow-style DAG editing, repo-backed presets, and shell export
- `Planner`
  - kanban board, experiment schedule, and follow-up tasks derived from saved lab history
- `HPO Lab`
  - Optuna launcher and study dashboard

The visual surfaces are not separate research code paths. They wrap the same
maintained CLI entry points documented on this page.

## Ablations and Targeted Studies

Several maintained but more research-oriented entry points live under
`scripts/experiments/`:

- `run_ablation.py`
- `learning_curves.py`
- `temperature_extrapolation.py`
- `statistical_tests.py`
- `generate_supplementary.py`
- `build_benchmark_release.py`

Use the [Script Reference](script_reference.md) if you need the maturity level
and intended role of each script before running it.

Related post-hoc analysis utilities live under `scripts/analysis/`:

- `diagnose_gradient_flow.py`
- `analyze_timp_channels.py`
- `sensitivity_analysis.py`
- `weight_analysis.py`

These are not benchmark runners themselves. They consume checkpoints,
benchmark bundles, or `tgnn_intermediates.csv` exports after the main
experiment run.

## Which Runner Should You Use?

| If you want to... | Use this |
| --- | --- |
| reproduce the repository's current article-comparison workflow | `scripts/experiments/reproduce_paper.py --profile article` |
| keep the old shell entrypoint for compatibility | `reproduce.sh` |
| compare maintained architectures on the full scaffold split | `run_medium_budget_comparison.py` |
| inspect TGNN physical intermediates and oracle diagnostics | `run_full_budget_experiment.py` |
| run multi-seed TGNN vs DirectGNN diagnostics with paired tests | `run_phase1_diagnostic.py` |
| compare scaffold, solute, and solvent protocols | `run_split_comparisons.py` |
| tune hyperparameters | `run_optuna.py` or `08_optuna_tuning.ipynb` |

## Common Output Pattern

Most experiment runners write machine-readable artifacts under `results/`.
The common pattern is:

- aggregate JSON summary
- per-model or per-seed subdirectories
- markdown comparison tables for quick review
- CSV exports when intermediate predictions matter
- canonical benchmark bundles with sidecars when the output is meant to be
  comparable across families:
  - `summary.csv`
  - `report.json`
  - `predictions.csv`
  - `run_manifest.json`
  - `benchmark_card.json`

That convention is intentional so downstream reporting and figure-generation
scripts can consume the outputs consistently.

When a local benchmark snapshot should become paper-facing instead of just
inspectable, freeze it with:

```bash
python scripts/experiments/build_benchmark_release.py ...
```

For post-benchmark robustness slicing on an existing `predictions.csv`, use:

```bash
python scripts/evaluation/run_thermo_stress_suite.py ...
```

For checkpoint- or intermediate-level interpretation after training, use the
analysis surfaces under `scripts/analysis/`.

## run\_e5 — Decisive Lever-C Comparison (σ-Grounding)

`scripts/experiments/run_e5_sigma_grounding.sh` is the P3 orchestrator for the
decisive σ-grounding experiment. It trains six arms across ≥ 3 seeds on the
corrected scaffold split, exports per-row predictions (including γ), and calls
`run_e5_comparison.py` to produce an intersection-locked metric table per seed.

### Six arms

| Arm | Model | Training recipe |
| --- | --- | --- |
| `nrtl` | TGNNSolv | standard NRTL proxy (`paper_config_tuned.yaml`) |
| `directgnn` | DirectGNN h64-L3 | direct end-to-end (`paper_config_directgnn_h64L3.yaml`) |
| `ungrounded` | TGNNSolv + COSMO-SAC | COSMO-SAC head, zero σ-aux steps (`cosmo_sac.yaml`, `--sigma-steps-per-epoch 0`) |
| `grounded_a` | TGNNSolv + COSMO-SAC | residual-only grounding: σ-aux stream, SLE warmup, frozen σ-head during SLE |
| `grounded_b` | TGNNSolv + COSMO-SAC | same as A + `--set cosmo_sac_wire_volume=true` (volume-coupled SG) |
| `oracle` | grounded\_a ckpt | oracle σ-profile injection at export time (`--sigma-oracle --sigma-oracle-side both`); reuses `grounded_a` checkpoint, no retraining |

### GPU command (≥ 3 seeds, ~6 h per seed)

```bash
DEVICE=cuda bash scripts/experiments/run_e5_sigma_grounding.sh
```

Override env vars as needed (all have defaults):

```bash
DEVICE=cuda SEEDS="42 43 44" DATA_DIR=notebooks/data/processed \
  SIGMA_DIR=notebooks/data/processed_sigma_aux_stream \
  OUT_DIR=results/e5_sigma_grounding CKPT_DIR=checkpoints/e5 \
  bash scripts/experiments/run_e5_sigma_grounding.sh
```

CPU smoke (checks wiring only; no meaningful metrics):

```bash
DEVICE=cpu SEEDS=42 WARMUP_EPOCHS=1 SIGMA_STEPS=2 \
  EXTRA_TRAIN_ARGS="--epochs-phase1 1 --epochs-phase2 1 --epochs-phase3 1" \
  bash scripts/experiments/run_e5_sigma_grounding.sh
```

### Pre-registered criteria (evaluated by `run_e5_comparison.py`)

- **Rescue criterion:** `grounded_a` (or `grounded_b`) achieves lower ln x₂ MAE
  than `directgnn` on the intersection of molecules with valid σ profiles.
- **Keeps-constraint:** `std(ln γ_pred)` stays within the calibrated band
  `[--lngamma-band lo hi]` (calibrate `lo`/`hi` from the `ungrounded` run before
  declaring the keeps-constraint met; default band 1.0–2.0 is a placeholder).
- **Stratified rescue:** ring-bearing vs acyclic subsets reported separately.

### Outputs

```
results/e5_sigma_grounding/
  seed_42/comparison.json        # per-seed aggregated metrics + criteria flags
  seed_43/comparison.json
  seed_44/comparison.json
  seed_42/<arm>_predictions.csv  # per-arm row-level predictions (ln x2, ln γ, ...)
  ...
```

Aggregate across seeds (mean ± std of key metrics from each `comparison.json`)
for the decisive verdict.

### Caveats

- **Oracle coverage ~5%:** the oracle arm only has σ profiles for a small fraction
  of test molecules; the oracle metric is an upper bound on a filtered subset, not
  a representative score. Interpret separately from the grounded-arm metrics.
- **Real metrics need GPU:** the CPU smoke verifies the wiring but produces
  meaningless numbers due to the severely truncated training budget.
- **Calibrate `--lngamma-band` before claiming keeps-constraint:** run the
  `ungrounded` arm first, extract `std(ln γ_pred)` from its predictions, and use
  that as the reference band. The default `[1.0, 2.0]` is a conservative prior.

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Results](results.md)
- [Experiment Lab](experiment_lab.md)
- [Reproducing the Paper](reproducing_paper.md)
- [Script Reference](script_reference.md)
- [Troubleshooting](troubleshooting.md)

</div>
