# TGNN-Solv Benchmarking Guide

## Quick Start

### 1. Basic Benchmarking

Eval your model on the test set:

```bash
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/results.json
```

**Output:**
```
MAE:            0.5432
RMSE:           0.8765
R²:             0.7654
Bias:           0.0123
```

### 2. Key Metrics Explained

| Метрика | Что означает | Хорошее значение |
|---------|------------|-----------------|
| **MAE** | Mean Absolute Error | < 0.5 |
| **RMSE** | Root Mean Squared Error | < 1.0 |
| **R²** | Coefficient of determination | > 0.7 |
| **Bias** | Systematic error | Close to 0 |
| **MAPE** | Mean Absolute Percentage Error | < 20% |

### 3. Stratified Evaluation

- **Solvent type**: Water vs Organic
- **Solubility range**: High / Moderate / Low / Very Low
- **Temperature**: Standard (298K) vs Non-standard
- **Data availability**: With/without auxiliary properties (T_m, dH_fus, etc.)

```json
{
  "by_solvent_type": {
    "water": {"mae": 0.45, "r2": 0.82, "n": 500},
    "organic": {"mae": 0.62, "r2": 0.71, "n": 1200}
  },
  "by_solubility_range": {
    "high": {"mae": 0.32, "r2": 0.88, "n": 300},
    "very_low": {"mae": 0.89, "r2": 0.45, "n": 150}
  }
}
```

### 4. Comparing Multiple Models

Compare two checkpoints:

```bash
# Baseline model
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/model_v1.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/v1.json

# Improved model
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/model_v2.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/v2.json

# Compare
python -m json.tool benchmarks/v1.json > /tmp/v1.txt
python -m json.tool benchmarks/v2.json > /tmp/v2.txt
diff /tmp/v1.txt /tmp/v2.txt
```

### 5. Cross-Dataset Evaluation

Compare performance on different sets:

```bash
# On validation set
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/val.csv \
    --output benchmarks/val_results.json

# On training set (overfitting check)
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/train.csv \
    --output benchmarks/train_results.json
```

## Advanced Benchmarking

### Using Evaluator Directly in Python

```python
from tgnn_solv.inference import load_model
from tgnn_solv.evaluate import Evaluator
from torch.utils.data import DataLoader

# Load model
model, cfg = load_model("checkpoints/tgnn_solv_trained.pt")

# Create evaluator
evaluator = Evaluator(model, cfg)

# Evaluate on loader
report = evaluator.evaluate(test_loader, test_df)

# Access results
print(f"Overall MAE: {report['overall']['mae']:.4f}")
print(f"R² by solvent type:")
for solvent_type, metrics in report['by_solvent_type'].items():
    print(f"  {solvent_type}: {metrics['r2']:.4f}")
```

### Custom Metrics

Add your own metrics by modifying `compute_benchmark_metrics` in `scripts/benchmark_tgnn_solv.py`:

```python
from scripts.benchmark_tgnn_solv import compute_benchmark_metrics

# Your predictions and ground truth
predictions = model(batch)  # (N,)
ground_truth = batch.y     # (N,)

# Compute metrics
metrics = compute_benchmark_metrics(
    pred=predictions.cpu().numpy(),
    true=ground_truth.cpu().numpy()
)

print(metrics)  # {'n': 500, 'mae': 0.54, 'rmse': 0.87, 'r2': 0.77, 'bias': 0.01, 'mape': 0.12}
```

## Benchmarking Workflow

### 1. Train Model
```bash
python notebooks/02_train.ipynb
```

### 2. Benchmark on Test Set
```bash
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/test_results.json
```

### 3. Analyze Results

```python
import json
import pandas as pd

# Load results
with open('benchmarks/test_results.json') as f:
    results = json.load(f)

# Create summary table
summary = pd.DataFrame([
    {
        'Metric': metric,
        'Value': value
    }
    for metric, value in results['overall'].items()
])

print(summary)

# Identify problematic categories
for solvent_type, metrics in results['by_solvent_type'].items():
    if metrics['r2'] < 0.7:
        print(f"⚠️  {solvent_type}: Low R² = {metrics['r2']:.4f}")

for sol_range, metrics in results['by_solubility_range'].items():
    if metrics['mae'] > 1.0:
        print(f"⚠️  {sol_range}: High MAE = {metrics['mae']:.4f}")
```

### 4. Report Generation

```bash
# Create human-readable report
python scripts/benchmark_tgnn_solv.py \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --test-data notebooks/data/processed/test.csv \
    --output benchmarks/report.json \
    --verbose > benchmarks/report.txt
```

## Typical Performance Ranges

### For Solubility Prediction

| Model Type | MAE (ln_x2) | RMSE | R² | Notes |
|-----------|-----------|------|----|----|
| Random baseline | ~3.5 | ~4.2 | 0.0 | Theoretical lower bound |
| Simple ML (RF) | 1.2-1.5 | 1.8-2.2 | 0.4-0.5 | Standard approach |
| TGNN-Solv (expected) | 0.5-0.7 | 0.8-1.0 | 0.72-0.82 | Target range |
| Ensemble (3 models) | 0.4-0.5 | 0.6-0.8 | 0.78-0.85 | With aggregation |

### Solvent-specific Performance

- **Water**: Typically MAE 0.3-0.5 (easier to predict)
- **Organic solvents**: Typically MAE 0.6-0.8 (more challenging)

## Troubleshooting

### Low R² on Test Set

1. **Check training curves** — look for overfitting in notebooks/02_train.ipynb
2. **Validate data quality** — check for outliers and anomalies
3. **Try ensemble** — average predictions from multiple checkpoints
4. **Increase model capacity** — use --hidden-dim 512 during training

### High MAE on Specific Categories

1. **Check data distribution** — is the category underrepresented?
2. **Examine failure cases** — which molecules are predicted poorly?
3. **Stratified resampling** — retrain with balanced categories

### GPU Memory Issues

1. **Reduce batch size** — use --batch-size 32 in benchmark script
2. **Use CPU** — set `device='cpu'` in load_model()

## Next Steps

- 📊 **Visualize Results** — use 04_evaluation.ipynb notebook
- 🔧 **Hyperparameter Tuning** — use 08_optuna_tuning.ipynb
- 📈 **Temperature Dependency** — use 07_temperature.ipynb
- 🧪 **Ablation Study** — use 06_ablations.ipynb

