# Baselines

## Overview

The repository currently contains or references the following baselines:

- FastSolv
- DirectGNN
- SolProp
- Random Forest baseline on RDKit descriptors
- Ideal SLE baseline

These baselines cover both learned alternatives and physics-only references.

For script maturity and overlap notes, see `docs/script_reference.md` and
`docs/repository_audit.md`.

## FastSolv

FastSolv is a descriptor-based baseline.

Predict with the pretrained ensemble:

```bash
python scripts/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output notebooks/data/processed/fastsolv_pred.csv
```

Train on your own splits:

```bash
python scripts/run_fastsolv.py train \
    --train notebooks/data/processed/train.csv \
    --val notebooks/data/processed/val.csv \
    --test notebooks/data/processed/test.csv \
    --outdir checkpoints/fastsolv_run \
    --metrics checkpoints/fastsolv_run/metrics.json
```

Warning: custom FastSolv retraining is still vulnerable to descriptor-path NaN
failures on some data regimes. The pretrained `predict` / `compare` flows are
the safer default when you need a baseline rather than a debugging target.

Compare FastSolv vs TGNN-Solv:

```bash
python scripts/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics checkpoints/fastsolv_compare.json
```

This is the preferred FastSolv comparison path. The older
`scripts/compare_fastsolv_tgnn.py` script remains available as a lighter
utility, but `run_fastsolv.py compare` is the main wrapper.

## DirectGNN

DirectGNN is the main no-physics ablation:

- same GNN backbone,
- same cross-attention stack,
- direct prediction of `ln_x2`,
- no SLE solver and no NRTL physics.

Current run paths:

```bash
python scripts/train_directgnn.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/directgnn.pt
```

For a fair multi-split comparison against TGNN-Solv:

```bash
python scripts/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

For automated hyperparameter tuning:

```bash
python scripts/run_optuna.py --models direct_gnn --n-trials 20
```

For exploratory debugging and side-by-side notebook analysis:

```bash
jupyter notebook notebooks/05_baselines.ipynb
```

## SolProp

SolProp is an external baseline and typically uses a separate conda
environment.

Inference:

```bash
conda activate solprop
python scripts/run_solprop.py \
    --input notebooks/data/processed/test.csv \
    --output notebooks/data/processed/solprop_predictions.csv \
    --temperature_dependent
```

Calibration and evaluation on your splits:

```bash
conda activate solprop
python scripts/run_solprop.py train \
    --train notebooks/data/processed/train.csv \
    --val notebooks/data/processed/val.csv \
    --test notebooks/data/processed/test.csv \
    --outdir checkpoints/solprop_run \
    --temperature_dependent \
    --include_temperature \
    --export_preds
```

## RF Baseline

The Random Forest baseline supports three feature modes:

- `descriptors` — concatenated RDKit 2D descriptors for the solute and solvent
- `morgan` — concatenated Morgan fingerprints for the solute and solvent
- `hybrid` — RDKit descriptors + Morgan fingerprints

Run it directly:

```bash
python -m tgnn_solv.baselines.rf_baseline \
    --train notebooks/data/processed/train.csv \
    --test notebooks/data/processed/test.csv \
    --feature-mode descriptors \
    --output results/rf_baseline.json
```

You can switch to Morgan or hybrid features with:

```bash
python -m tgnn_solv.baselines.rf_baseline \
    --train notebooks/data/processed/train.csv \
    --test notebooks/data/processed/test.csv \
    --feature-mode morgan \
    --morgan-n-bits 2048 \
    --output results/rf_morgan.json
```

Requirements:

- RDKit
- scikit-learn

The RF baseline is also supported by `scripts/run_split_comparisons.py` as
`rf_baseline`, `rf_morgan`, and `rf_hybrid`.

## Ideal SLE

The Ideal SLE baseline assumes `γ = 1` and predicts:

- `ln(x₂) = -(ΔH_fus / R) * (1 / T - 1 / T_m)`
- or the ΔCp-corrected variant when `dCp_fus` is available.

If `dH_fus` is missing, the implementation falls back to Walden's rule.

Run it directly:

```bash
python -m tgnn_solv.baselines.ideal_sle \
    --train notebooks/data/processed/train.csv \
    --test notebooks/data/processed/test.csv \
    --output results/ideal_sle_baseline.json
```

The current baseline automation coverage is intentionally uneven:

- FastSolv has a dedicated multi-mode CLI.
- SolProp has a dedicated prediction/calibration CLI.
- DirectGNN has a dedicated training CLI and can also be launched through
  `scripts/run_seeds.py` for multi-seed comparisons.
- `scripts/run_split_comparisons.py` is the canonical way to compare TGNN-Solv,
  DirectGNN, and RF across `solute_scaffold`, `solute`, and `solvent` split
  protocols.
- Ideal SLE and RF baselines are lightweight package modules rather than
  top-level orchestration scripts.

## Suggested Comparison Order

If you want a compact but informative baseline set:

1. Ideal SLE
2. Random Forest
3. FastSolv
4. DirectGNN
5. TGNN-Solv

This progression isolates the incremental value of:

- pure thermodynamics,
- classical descriptors,
- external pretrained descriptor models,
- a learned graph-only model,
- the full physics-informed GNN.
