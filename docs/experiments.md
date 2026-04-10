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

## Which Runner Should You Use?

| If you want to... | Use this |
| --- | --- |
| reproduce the repository's current article-comparison workflow | `scripts/experiments/reproduce_paper.py --profile article` |
| keep the old shell entrypoint for compatibility | `reproduce.sh` |
| compare maintained architectures on the full scaffold split | `run_medium_budget_comparison.py` |
| inspect TGNN physical intermediates and oracle diagnostics | `run_full_budget_experiment.py` |
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

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Results](results.md)
- [Experiment Lab](experiment_lab.md)
- [Reproducing the Paper](reproducing_paper.md)
- [Script Reference](script_reference.md)
- [Troubleshooting](troubleshooting.md)

</div>
