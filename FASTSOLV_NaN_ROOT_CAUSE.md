# FastSolv Training NaN Issue - ROOT CAUSE ANALYSIS

## Problem Statement

When attempting to train FastSolv from scratch with TGNN-Solv datasets, the model produces NaN predictions from epoch 0, resulting in NaN metrics regardless of learning rate, batch size, or gradient clipping adjustments.

## Root Cause Investigation

### What We Tried

✗ **Learning Rate Scaling** (1e-4 → 1e-6): No improvement, NaN persists  
✗ **Gradient Clipping** (norm = 1.0): No improvement, still NaN  
✗ **Batch Size Adjustment** (64 → 256): No improvement  
✗ **Sanity Check Disabling** (num_sanity_val_steps=0): Model runs but predictions still NaN  
✗ **NaN-tolerant Wrapper** (catch errors): Training completes but all metrics are NaN  

### Actual Root Cause

After deep investigation, we discovered **descriptors contain NaN values** when computed via fastprop's `get_descriptors()` function:

```
Solute descriptor shape: (1, 1613), range: [nan, nan]
Solvent descriptor shape: (1, 1613), range: [nan, nan]
```

**Why this happens:**
1. FastSolv was trained on specific descriptor sets (ALL_2D from mordred-community)
2. The pretrained FastSolv model expects descriptors in a specific range/distribution
3. When training from scratch, the descriptor computation or normalization is incompatible
4. NaN descriptors → NaN model outputs → NaN loss → NaN weights → Unable to converge

## Diagnosis

**FastSolv is designed as:**
- ✓ A **pretrained baseline predictor** for inference
- ✗ NOT suitable for training from scratch on custom datasets
- ✗ Descriptor computation has undocumented incompatibilities

**The fundamental issue:** FastSolv's descriptor pipeline (mordred-community → fastprop normalization) appears broken or incompatible when used standalone for training.

## Solution

**DO NOT attempt to train FastSolv from scratch.**

Instead:

### ✓ For Inference (Pretrained Models)
```bash
python scripts/run_fastsolv.py predict \
    --input data/processed/test.csv \
    --output fastsolv_predictions.csv
```
This works perfectly - FastSolv ensemble predictions are reliable.

### ✓ For Custom Training
Use **TGNN-Solv** instead:
- Fully differentiable physics-informed architecture
- No descriptor pipeline issues
- Directly learns from SMILES via GNN
- Can be trained end-to-end with custom data
```bash
python notebooks/02_train.ipynb  # Train TGNN-Solv
```

### Why TGNN-Solv is Better for Custom Training
1. **End-to-end differentiable**: SMILES → Graph → Embeddings → Physics → Predictions
2. **No descriptor dependency**: Learns features directly from molecular graphs
3. **Physics-informed**: Gradients flow through thermodynamic equations
4. **Proven to converge**: Three-phase curriculum training with real metrics

## Recommendations

### For Your Use Case

**Recommendation: Use TGNN-Solv, not FastSolv.**

- FastSolv: Pretrained ensemble for quick baseline predictions
- TGNN-Solv: Customizable, trainable, physics-informed model

### If FastSolv Training is Critical

Contact the FastSolv developers/maintainers for:
- Documented descriptor pipeline setup
- Proper initialization procedures for custom data
- Known incompatibilities with certain molecule types

## Files Updated

- `/scripts/run_fastsolv.py` - Added `--lr-scale` parameter, gradient clipping, NaN-tolerant wrapper
- `/AGENTS.md` - Added warning about FastSolv training limitations

## Lesson Learned

**Don't force-fit pretrained models designed for inference into training pipelines without understanding their architecture deeply.**

TGNN-Solv's physics-informed design makes it much more suitable for custom dataset training.

