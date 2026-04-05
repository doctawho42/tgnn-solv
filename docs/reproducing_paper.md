# Reproducing the Paper

## Entry Points

The maintained reproduction runner is now:

- `scripts/experiments/reproduce_paper.py`

The repository-level shell entrypoint remains:

- `reproduce.sh`

`reproduce.sh` is now a thin compatibility wrapper that delegates to:

```bash
python scripts/experiments/reproduce_paper.py --profile article
```

So both of the following are valid:

```bash
bash reproduce.sh
```

```bash
python scripts/experiments/reproduce_paper.py --profile article
```

## Profiles

The structured runner exposes three maintained profiles.

### `core`

Minimal maintained paper path:

1. prepare scaffold-aware processed data
2. run tuned TGNN-Solv multi-seed training
3. resolve and evaluate the best TGNN checkpoint
4. run split-wise comparisons
5. generate supplementary tables
6. generate paper figures

Use it when you want the smallest reproducible path that still regenerates the
main TGNN-facing artifacts.

### `article`

Current article-comparison path:

1. prepare scaffold-aware processed data
2. run tuned TGNN-Solv multi-seed training
3. run the medium-budget architecture comparison
4. run external baseline benchmarking:
   - FastSolv
   - native-retrained SolProp
5. resolve and evaluate the best TGNN checkpoint
6. run split-wise comparisons
7. generate supplementary tables
8. generate paper figures

This is the recommended profile for current paper reproduction because it
includes both the maintained in-repo baselines and the external competitors.

### `full`

Expanded diagnostic path:

- everything in `article`
- split-late multi-seed comparison
- DirectGNN multi-seed baseline
- error analysis
- ablation suite
- learning curves
- temperature extrapolation
- physics validation
- statistical tests
- full-budget diagnostic export

Use it when you want the article artifacts plus the heavier diagnostic bundle.

## Canonical Commands

### Recommended article reproduction

```bash
python scripts/experiments/reproduce_paper.py --profile article
```

### Minimal core reproduction

```bash
python scripts/experiments/reproduce_paper.py --profile core
```

### Full diagnostic reproduction

```bash
python scripts/experiments/reproduce_paper.py --profile full
```

### Inspect the planned step graph without running anything

```bash
python scripts/experiments/reproduce_paper.py --profile article --list-steps
```

### Run only selected steps

```bash
python scripts/experiments/reproduce_paper.py \
    --profile article \
    --step medium_budget \
    --step external_benchmarks
```

## Important Defaults

The structured runner now uses the maintained modern defaults:

- tuned TGNN config: `configs/paper_config_tuned.yaml`
- canonical split mode: `solute_scaffold`
- multi-seed count: `5`
- medium-budget comparison on the full scaffold split
- external baselines:
  - `FastSolv mode = both`
  - `SolProp mode = native`

That is different from the older shell script, which hardcoded a broader legacy
TGNN config and did not treat the external article baselines as part of the
default reproduction path.

## Expected Artifacts

### Core profile

- `results/multi_seed_results.json`
- `results/full_evaluation.json`
- `results/split_comparisons.json`
- `tables/`
- `figures/`
- `results/reproduction/core_summary.json`

### Article profile

- everything from `core`
- `results/medium_budget/`
- `results/external_baselines/article_benchmark/summary.csv`
- `results/external_baselines/article_benchmark/comparison.json`
- `results/reproduction/article_summary.json`
- benchmark sidecars under the generated bundles:
  - `run_manifest.json`
  - `benchmark_card.json`

### Full profile

- everything from `article`
- `results/split_late_multi_seed_results.json`
- `results/directgnn_multi_seed_results.json`
- `results/error_analysis.json`
- `results/ablation.json`
- `results/learning_curves.json`
- `results/temperature_extrapolation.json`
- `results/physics_validation.json`
- `results/significance.json`
- `results/full_budget_experiment/`
- `results/reproduction/full_summary.json`

## Supplementary Outputs

`scripts/experiments/generate_supplementary.py` now also looks for canonical
external/custom benchmark bundles and emits an additional table summarizing
those baselines when available.

That means the article profile can feed both:

- the `Benchmark Studio` inside the lab
- the supplementary-table generator

from the same canonical `summary.csv + report.json + predictions.csv` bundles.

If you want to freeze the resulting artifact snapshot for sharing or a paper
appendix, follow the reproduction run with:

```bash
python scripts/experiments/build_benchmark_release.py ...
```

## Validation Guidance

A successful reproduction run means:

- the structured runner completes or skips optional external steps with clear
  status in `results/reproduction/<profile>_summary.json`
- the best TGNN checkpoint resolves cleanly into `results/full_evaluation.json`
- figures and supplementary tables are regenerated from the produced artifacts
- benchmark bundles are present when the article or full profile is used

Exact numeric values still depend on:

- hardware
- optional dependency stacks
- runtime availability for FastSolv and SolProp
- seed reuse versus fresh retraining

Treat the generated artifacts from your run as the authoritative output.

## Scope Boundary

The structured runner is now the maintained paper-reproduction surface.
Standalone scripts such as:

- `scripts/experiments/run_full_budget_experiment.py`
- `scripts/experiments/run_medium_budget_comparison.py`
- `scripts/experiments/run_external_baseline_benchmark.py`

remain useful individually, but they are now also integrated into the
maintained reproduction profiles instead of living completely outside the
default paper path.
