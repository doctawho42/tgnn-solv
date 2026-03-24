# Reproducing Paper Results

## Entry Point

The end-to-end reproduction script is:

- [`reproduce.sh`](../reproduce.sh)

Run it from the repository root:

```bash
bash reproduce.sh
```

## What `reproduce.sh` Does

The script follows this sequence:

1. Check Python, PyTorch, PyG, and package installation.
2. Prepare processed data with `scripts/prepare_data.py` if needed.
3. Train TGNN-Solv across 5 seeds with `scripts/run_seeds.py`.
4. Run a matched 5-seed `split_late` backbone comparison with `scripts/run_seeds.py`
   and `configs/paper_config_split_late.yaml`.
5. Evaluate the best checkpoint with `scripts/evaluate_complete.py`.
6. Run detailed error analysis with `scripts/error_analysis.py`.
7. Run the multi-seed ablation study with `scripts/run_ablation.py`.
8. Run baseline steps, including DirectGNN and FastSolv when available.
9. Run learning-curve and temperature-extrapolation experiments.
10. Run physical-parameter validation with `scripts/validate_physics.py`.
11. Run split-wise comparison across scaffold, solute, and solvent protocols.
12. Generate figures, statistical tests, and supplementary tables.

Generated artifacts:

- `results/multi_seed_results.json`
- `results/split_late_multi_seed_results.json`
- `results/directgnn_multi_seed_results.json`
- `results/full_evaluation.json`
- `results/error_analysis.json`
- `results/ablation.json`
- `results/learning_curves.json`
- `results/temperature_extrapolation.json`
- `results/physics_validation.json`
- `results/split_comparisons.json`
- `results/significance.json`
- `results/fastsolv_predictions.csv` if FastSolv is installed
- `figures/`
- `tables/`

`results/full_evaluation.json` now also contains `true_ln_x2` and
`pred_ln_x2` arrays, which are consumed directly by
`scripts/generate_paper_figures.py` for parity, residual, and error
distribution plots.

## Recommended Reproduction Workflow

```bash
conda create -n tgnn-solv python=3.11
conda activate tgnn-solv
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install torch-geometric -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
pip install -e ".[dev]"

bash reproduce.sh
```

## Detailed Steps

### Step 1: Data preparation

Default command inside `reproduce.sh`:

```bash
python scripts/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42
```

### Step 2: Multi-seed training

```bash
python scripts/run_seeds.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/multi_seed_results.json \
    --checkpoint-dir checkpoints/seeds \
    --device cuda
```

### Step 2b: Split-late backbone comparison

`reproduce.sh` also runs a matched comparison against the asymmetric late-branch
encoder:

```bash
python scripts/run_seeds.py \
    --config configs/paper_config_split_late.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/split_late_multi_seed_results.json \
    --checkpoint-dir checkpoints/split_late_seeds \
    --device cuda
```

### Step 3: Full evaluation of the best seed

```bash
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/seeds/seed_<best>.pt \
    --output results/full_evaluation.json \
    --verbose
```

### Step 3b: Error analysis

```bash
python scripts/error_analysis.py \
    --predictions results/full_evaluation.json \
    --test-data notebooks/data/processed/test.csv \
    --output results/error_analysis.json
```

### Step 4: Ablation study

```bash
python scripts/run_ablation.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 3 \
    --output results/ablation.json
```

### Step 5: Baselines

DirectGNN is run as a multi-seed baseline through `scripts/run_seeds.py` and
`scripts/train_directgnn.py`:

```bash
python scripts/run_seeds.py \
    --train-script scripts/train_directgnn.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/directgnn_multi_seed_results.json \
    --checkpoint-dir checkpoints/directgnn_seeds
```

FastSolv is run only when `fastsolv` is installed:

```bash
python scripts/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/fastsolv_predictions.csv
```

### Step 5b: Learning curves

```bash
python scripts/learning_curves.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --fractions "0.01,0.05,0.1,0.2,0.5,1.0" \
    --n-seeds 3 \
    --output results/learning_curves.json \
    --models "tgnn_solv,rf_baseline"
```

### Step 5c: Temperature extrapolation

`reproduce.sh` assembles a temporary combined CSV from `train.csv`, `val.csv`,
and `test.csv`, then runs:

```bash
python scripts/temperature_extrapolation.py \
    --config configs/paper_config.yaml \
    --data combined.csv \
    --t-cuts "298.15,323.15,348.15,373.15" \
    --n-seeds 3 \
    --output results/temperature_extrapolation.json
```

### Step 5d: Physics validation

```bash
python scripts/validate_physics.py \
    --checkpoint checkpoints/seeds/seed_<best>.pt \
    --test-data notebooks/data/processed/test.csv \
    --output results/physics_validation.json
```

### Step 5e: Split protocol comparison

```bash
python scripts/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline" \
    --config configs/paper_config.yaml \
    --n-seeds 3 \
    --output results/split_comparisons.json
```

This step matters because many comparison baselines in the literature did not
use a scaffold holdout. The split-wise report makes it explicit how the model
behaves on:

- the strict `solute_scaffold` split,
- the less strict `solute` split,
- the solvent holdout split.

### Step 6: Statistical significance tests

```bash
python scripts/statistical_tests.py \
    --results results/multi_seed_results.json results/directgnn_multi_seed_results.json \
    --labels TGNN-Solv DirectGNN \
    --output results/significance.json
```

### Step 7: Supplementary tables

```bash
python scripts/generate_supplementary.py \
    --results-dir results/ \
    --output-dir tables/
```

This now includes `Table S8`, which compares the default `shared_residual`
backbone against the `split_late` encoder using the matched multi-seed runs and
their significance test output when available, plus `Table S9` for split-wise
comparison across scaffold, solute, and solvent protocols.

### Step 8: Figure generation

```bash
python scripts/generate_paper_figures.py \
    --results-dir results/ \
    --output-dir figures/
```

When `results/split_comparisons.json` exists, the figure script also produces
`Figure S2` for split-wise comparison.

## Expected Results

The repository does not currently ship a committed five-seed
`results/multi_seed_results.json`, so the table below should be treated as an
expected target range inferred from the README single-model benchmark and the
intended multi-seed workflow.

| Metric | Expected Mean ± Std | Notes |
|--------|---------------------|-------|
| MAE | ≈ 0.58 ± 0.05 | TGNN-Solv target on BigSolDBv2.1 test split |
| RMSE | ≈ 0.95 ± 0.10 | Should remain clearly below FastSolv |
| R² | ≈ 0.87 ± 0.03 | Stable positive fit on the held-out test set |

Reference baseline from `README.md`:

| Model | MAE | RMSE | R² |
|-------|-----|------|----|
| TGNN-Solv (trained) | 0.58 | 0.95 | 0.87 |
| FastSolv (pretrained) | 0.73 | 1.12 | 0.81 |

After running `reproduce.sh`, the authoritative numbers are the ones written to:

- `results/multi_seed_results.json`
- `results/full_evaluation.json`

## Expected Wall-Clock Time

Actual runtime depends strongly on GPU availability, storage speed, and whether
the raw data must be downloaded. Typical expectations on a single modern GPU:

| Stage | Expected Time |
|------|---------------|
| Data preparation | 5-20 minutes |
| 5-seed TGNN-Solv training | 4-12 hours |
| Full evaluation of the best checkpoint | 10-20 minutes |
| FastSolv prediction baseline | 5-20 minutes |
| Ablation study | many additional hours to more than 1 day |
| Learning curves + temperature extrapolation | many additional hours |
| Physics validation + tables + significance tests | 10-60 minutes |
| Full end-to-end paper reproduction | half a day to more than 1 day |

## Notes

- `reproduce.sh` still skips some steps when optional dependencies are not
  available, especially FastSolv and any workflow that depends on unfinished
  model-introspection support in a custom checkpoint.
- The FastSolv baseline is optional and depends on an external package.
- The notebooks remain useful for exploratory analysis, but the reproduction
  script now has dedicated CLI coverage for DirectGNN, ablations, learning
  curves, temperature extrapolation, and supplementary artifacts.
