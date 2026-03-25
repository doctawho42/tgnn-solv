# Evaluation Guide

## evaluate_complete.py

Lightweight checkpoint evaluation for reporting and figure generation:

```bash
python scripts/evaluate_complete.py \
    --test-data FILE           # Path to test CSV (default: notebooks/data/processed/test.csv)
    --tgnn-checkpoint FILE     # Path to model checkpoint (default: checkpoints/tgnn_solv_trained.pt)
    --output FILE              # Output JSON path (default: benchmarks/complete_evaluation.json)
    --n-samples N              # Evaluate on N random samples (optional, default: all)
    --verbose                  # Verbose logging
```

Output includes:

- overall metrics: MAE, RMSE, R², Pearson correlation, median error,
  max error, Q95 error,
- stratified metrics by temperature,
- stratified metrics by solubility range,
- `true_ln_x2` and `pred_ln_x2` arrays for plotting,
- JSON output for downstream analysis.

Recommended use:

- use `scripts/evaluate_complete.py` for quick reports, `results/full_evaluation.json`,
  and plotting inputs;
- use `scripts/benchmark_tgnn_solv.py` when you want richer `Evaluator`-backed
  stratification.
- use `scripts/run_split_comparisons.py` when you need fair split-wise
  comparison across scaffold, solute, and solvent protocols.

## Canonical Report Schema

`scripts/evaluate_complete.py` and `scripts/benchmark_tgnn_solv.py` now emit a
shared report layout:

```json
{
  "schema_version": "1.0",
  "report_type": "evaluation",
  "metadata": {...},
  "overall": {...},
  "stratified": {
    "temperature": {...},
    "solubility": {...},
    "solvent_type": {...},
    "solvent": {...},
    "aux_data": {...}
  },
  "predictions": {
    "true_ln_x2": [...],
    "pred_ln_x2": [...]
  }
}
```

Backward-compatible aliases such as `by_temperature`,
`by_solubility_range`, `by_solvent_type`, `true_ln_x2`, and `pred_ln_x2`
are still written for downstream scripts and older notebooks.

Example output (illustrative schema only; the numeric values below are not a
guaranteed benchmark for the current repository state):

```json
{
  "overall": {
    "n_samples": 7500,
    "mae": 0.58,
    "rmse": 0.95,
    "r2": 0.87,
    "pearson_r": 0.93
  },
  "by_temperature": {
    "T_298_to_323K": {
      "n_samples": 3000,
      "mae": 0.51,
      "r2": 0.89
    }
  },
  "by_solubility": {
    "low_solubility": {
      "n_samples": 2500,
      "mae": 0.62,
      "r2": 0.85
    }
  }
}
```

## compare_fastsolv_tgnn.py

Comparison with the FastSolv baseline:

```bash
python scripts/compare_fastsolv_tgnn.py \
    --test-data FILE            # Path to test CSV
    --tgnn-checkpoint FILE      # Path to TGNN model
    --fastsolv-checkpoint FILE  # Path to FastSolv ONNX (optional)
    --output FILE               # Output JSON path
    --n-samples N               # Number of samples (optional)
    --no-fastsolv               # Skip FastSolv (if unavailable)
```

FastSolv note:

- The repository uses pretrained FastSolv for inference.
- Training FastSolv from scratch is currently unreliable because of
  descriptor-path NaN failures.
- TGNN-Solv is the recommended path for custom training and comparison.
- `scripts/run_fastsolv.py compare` is the preferred FastSolv comparison
  wrapper when the FastSolv stack is installed.

## benchmark_tgnn_solv.py

Detailed benchmark script using `tgnn_solv.evaluate.Evaluator`:

```bash
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/results.json
```

Use `scripts/analyze_benchmark.py` to turn the resulting JSON into a compact
text report:

```bash
python scripts/analyze_benchmark.py \
    --results benchmarks/results.json \
    --output benchmarks/analysis.txt
```

## run_split_comparisons.py

Fair split-wise comparison runner:

```bash
python scripts/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

This script:

- resolves the canonical CSV triplets for each split mode,
- runs multi-seed experiments for the requested models,
- stores per-split JSON artifacts under `results/split_comparisons/`,
- emits an aggregate summary at `results/split_comparisons.json`,
- runs per-split significance tests when at least two models are available.

The aggregate JSON is consumed by:

- `scripts/generate_paper_figures.py` for `Figure S2`,
- `scripts/generate_supplementary.py` for `Table S9`.

## Examples

### Example 1: Quick diagnostic (2 minutes)

```bash
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --n-samples 100 \
    --output bench_quick.json
```

### Example 2: Full evaluation for paper (15 minutes)

```bash
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output paper_results.json
```

Then parse results:

```python
import json

with open("paper_results.json") as f:
    data = json.load(f)

print(f"Overall MAE: {data['overall']['mae']:.4f}")
print(f"Overall R²:  {data['overall']['r2']:.4f}")
print(f"Test samples: {data['overall']['n_samples']}")

for temp_range, metrics in data["by_temperature"].items():
    if metrics["n_samples"] > 0:
        print(f"{temp_range}: MAE={metrics['mae']:.4f}, R²={metrics['r2']:.4f}")
```

### Example 3: Compare model versions

```bash
# Train two models
jupyter notebook notebooks/02_train.ipynb  # Save as best_v1.pt
# Modify hyperparameters and retrain, then save as best_v2.pt

# Evaluate both
python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/best_v1.pt \
    --output eval_v1.json

python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/best_v2.pt \
    --output eval_v2.json
```

### Example 4: Evaluate on custom data

```bash
# Prepare your CSV with the required columns
python scripts/evaluate_complete.py \
    --test-data your_custom_data.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output custom_results.json
```

### Example 5: Filter and evaluate on subset

```python
import pandas as pd

df = pd.read_csv("notebooks/data/processed/test.csv")
ethanol_only = df[df["solvent_smiles"] == "CCO"].copy()
ethanol_only.to_csv("test_ethanol.csv", index=False)

print(f"Created test set with {len(ethanol_only)} ethanol samples")
```

```bash
python scripts/evaluate_complete.py \
    --test-data test_ethanol.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output ethanol_eval.json
```
