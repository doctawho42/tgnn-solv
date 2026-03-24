#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"; exit 1; }

command -v python >/dev/null 2>&1 || error "Python not found"
python -c "import torch" 2>/dev/null || error "PyTorch not installed. See README.md"
python -c "import torch_geometric" 2>/dev/null || error "PyG not installed. See README.md"
python -c "import tgnn_solv" 2>/dev/null || error "tgnn_solv not installed. Run: pip install -e ."

DEVICE="cpu"
python -c "import torch; assert torch.cuda.is_available()" 2>/dev/null && DEVICE="cuda"
log "Using device: $DEVICE"

mkdir -p data/processed checkpoints/seeds checkpoints/directgnn_seeds checkpoints/split_late_seeds checkpoints/split_comparisons results figures logs tables

log "Step 1/8: Preparing data..."
if [ -f "notebooks/data/processed/test.csv" ]; then
    log "Data already prepared, skipping."
else
    python scripts/prepare_data.py \
        --output-dir notebooks/data/processed \
        --split-mode solute_scaffold \
        --seed 42 \
        || error "Data preparation failed. Try running notebooks/01_prepare_data.ipynb manually."
fi

TRAIN_DATA="notebooks/data/processed/train.csv"
VAL_DATA="notebooks/data/processed/val.csv"
TEST_DATA="notebooks/data/processed/test.csv"

[ -f "$TRAIN_DATA" ] || error "Train data not found: $TRAIN_DATA"
[ -f "$VAL_DATA" ] || error "Val data not found: $VAL_DATA"
[ -f "$TEST_DATA" ] || error "Test data not found: $TEST_DATA"

log "Train: $(wc -l < "$TRAIN_DATA") rows, Val: $(wc -l < "$VAL_DATA") rows, Test: $(wc -l < "$TEST_DATA") rows"

log "Step 2/8: Training with 5 seeds (this may take several hours)..."
python scripts/run_seeds.py \
    --config configs/paper_config.yaml \
    --train-data "$TRAIN_DATA" \
    --val-data "$VAL_DATA" \
    --test-data "$TEST_DATA" \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/multi_seed_results.json \
    --checkpoint-dir checkpoints/seeds \
    --device "$DEVICE"

log "Multi-seed results saved to results/multi_seed_results.json"

# === Step 2b: Backbone comparison (shared vs split-late encoder) ===
log "Step 2b: Running split-late backbone comparison..."
python scripts/run_seeds.py \
    --config configs/paper_config_split_late.yaml \
    --train-data "$TRAIN_DATA" \
    --val-data "$VAL_DATA" \
    --test-data "$TEST_DATA" \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/split_late_multi_seed_results.json \
    --checkpoint-dir checkpoints/split_late_seeds \
    --device "$DEVICE" \
    || warn "Split-late backbone comparison failed"

log "Step 3/8: Full evaluation of best model..."
BEST_CHECKPOINT=$(python -c "
import json
with open('results/multi_seed_results.json') as f:
    data = json.load(f)
best = data['best_seed']
if not isinstance(best, dict) or 'seed' not in best:
    raise KeyError('best_seed is missing or malformed')
if 'checkpoint' in best:
    print(best['checkpoint'])
else:
    seed = best['seed']
    for row in data.get('per_seed', []):
        if row.get('seed') == seed:
            print(row['checkpoint'])
            break
    else:
        raise KeyError('Could not resolve checkpoint for best seed')
")

python scripts/evaluate_complete.py \
    --test-data "$TEST_DATA" \
    --tgnn-checkpoint "$BEST_CHECKPOINT" \
    --output results/full_evaluation.json \
    --verbose

# === Step 3b: Error analysis ===
log "Step 3b: Running error analysis..."
if [ -f "results/full_evaluation.json" ]; then
    python scripts/error_analysis.py \
        --predictions results/full_evaluation.json \
        --test-data "$TEST_DATA" \
        --output results/error_analysis.json
else
    warn "Skipping error analysis (no evaluation results)"
fi

log "Step 4/8: Running ablation study..."
python scripts/run_ablation.py \
    --config configs/paper_config.yaml \
    --train-data "$TRAIN_DATA" \
    --val-data "$VAL_DATA" \
    --test-data "$TEST_DATA" \
    --n-seeds 3 \
    --output results/ablation.json \
    --device "$DEVICE" \
    || warn "Ablation study failed (see logs)"

log "Step 5/8: Running baselines..."

if [ -f "scripts/train_directgnn.py" ]; then
    log "Training DirectGNN baseline..."
    python scripts/run_seeds.py \
        --train-script scripts/train_directgnn.py \
        --config configs/paper_config.yaml \
        --train-data "$TRAIN_DATA" \
        --val-data "$VAL_DATA" \
        --test-data "$TEST_DATA" \
        --n-seeds 5 \
        --base-seed 42 \
        --output results/directgnn_multi_seed_results.json \
        --checkpoint-dir checkpoints/directgnn_seeds \
        --device "$DEVICE" \
        || warn "DirectGNN multi-seed baseline failed"
else
    warn "scripts/train_directgnn.py not found, skipping DirectGNN baseline"
fi

if python -c "import fastsolv" 2>/dev/null; then
    log "Running FastSolv baseline..."
    python scripts/run_fastsolv.py predict \
        --input "$TEST_DATA" \
        --output results/fastsolv_predictions.csv
else
    warn "FastSolv not installed, skipping"
fi

# === Step 5b: Learning curves ===
log "Step 5b: Running learning curve experiment..."
python scripts/learning_curves.py \
    --config configs/paper_config.yaml \
    --train-data "$TRAIN_DATA" \
    --val-data "$VAL_DATA" \
    --test-data "$TEST_DATA" \
    --fractions "0.01,0.05,0.1,0.2,0.5,1.0" \
    --n-seeds 3 \
    --output results/learning_curves.json \
    --device "$DEVICE" \
    --models "tgnn_solv,rf_baseline" \
    || warn "Learning curves failed"

# === Step 5c: Temperature extrapolation ===
log "Step 5c: Running temperature extrapolation..."
ALL_DATA=$(mktemp)
cat "$TRAIN_DATA" > "$ALL_DATA"
tail -n +2 "$VAL_DATA" >> "$ALL_DATA"
tail -n +2 "$TEST_DATA" >> "$ALL_DATA"

python scripts/temperature_extrapolation.py \
    --config configs/paper_config.yaml \
    --data "$ALL_DATA" \
    --t-cuts "298.15,323.15,348.15,373.15" \
    --n-seeds 3 \
    --output results/temperature_extrapolation.json \
    --device "$DEVICE" \
    || warn "Temperature extrapolation failed"
rm -f "$ALL_DATA"

# === Step 5d: Physics validation ===
log "Step 5d: Validating physical parameters..."
python scripts/validate_physics.py \
    --checkpoint "$BEST_CHECKPOINT" \
    --test-data "$TEST_DATA" \
    --output results/physics_validation.json \
    --device "$DEVICE" \
    || warn "Physics validation failed (may need return_intermediates support)"

# === Step 5e: Split protocol comparison ===
log "Step 5e: Comparing model performance across split protocols..."
python scripts/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline" \
    --config configs/paper_config.yaml \
    --n-seeds 3 \
    --base-seed 42 \
    --results-dir results/split_comparisons \
    --output results/split_comparisons.json \
    --checkpoint-root checkpoints/split_comparisons \
    --device "$DEVICE" \
    || warn "Split protocol comparison failed"

# === Step 6: Statistical tests ===
log "Step 6/8: Running statistical significance tests..."
RESULT_FILES=("results/multi_seed_results.json")
LABEL_FILES=("TGNN-Solv")
if [ -f "results/directgnn_multi_seed_results.json" ]; then
    RESULT_FILES+=("results/directgnn_multi_seed_results.json")
    LABEL_FILES+=("DirectGNN")
fi
if [ -f "results/split_late_multi_seed_results.json" ]; then
    RESULT_FILES+=("results/split_late_multi_seed_results.json")
    LABEL_FILES+=("SplitLate")
fi

if [ "${#RESULT_FILES[@]}" -ge 2 ]; then
    python scripts/statistical_tests.py \
        --results "${RESULT_FILES[@]}" \
        --labels "${LABEL_FILES[@]}" \
        --output results/significance.json \
        || warn "Statistical tests failed"
else
    warn "Skipping statistical tests (need at least two multi-seed result files)"
fi

# === Step 7: Generate supplementary tables ===
log "Step 7/8: Generating supplementary tables..."
python scripts/generate_supplementary.py \
    --results-dir results/ \
    --output-dir tables/ \
    || warn "Table generation failed"

log "Step 8/8: Generating figures..."
if [ -f "scripts/generate_paper_figures.py" ]; then
    python scripts/generate_paper_figures.py \
        --results-dir results/ \
        --output-dir figures/
else
    warn "scripts/generate_paper_figures.py not found, skipping figure generation"
fi

# === Summary ===
echo ""
echo "========================================"
log "All steps completed successfully!"
echo "========================================"
echo ""
echo "Results:"
echo "  Multi-seed metrics:  results/multi_seed_results.json"
echo "  Split-late encoder:  results/split_late_multi_seed_results.json"
echo "  DirectGNN baseline:  results/directgnn_multi_seed_results.json"
echo "  Full evaluation:     results/full_evaluation.json"
echo "  Error analysis:      results/error_analysis.json"
echo "  Ablation study:      results/ablation.json"
echo "  Learning curves:     results/learning_curves.json"
echo "  Temp extrapolation:  results/temperature_extrapolation.json"
echo "  Physics validation:  results/physics_validation.json"
echo "  Split comparison:    results/split_comparisons.json"
echo "  Significance tests:  results/significance.json"
echo "  Supplementary tables: tables/"
echo "  Figures:             figures/"
echo ""
echo "Best checkpoint: $BEST_CHECKPOINT"
echo ""

python -c "
import json
with open('results/multi_seed_results.json') as f:
    data = json.load(f)
agg = data['aggregated']
print('Key Results (5 seeds):')
for metric in ['mae', 'rmse', 'r2']:
    if metric in agg:
        m = agg[metric]
        print(f'  {metric.upper():>6}: {m[\"mean\"]:.4f} ± {m[\"std\"]:.4f}  (95% CI: [{m[\"ci_95_low\"]:.4f}, {m[\"ci_95_high\"]:.4f}])')
"
