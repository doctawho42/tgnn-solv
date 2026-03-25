# Training Guide

## Overview

TGNN-Solv uses a three-phase curriculum:

1. **Phase 1: Property pretraining**
   - Trains auxiliary physical property heads.
   - No solubility loss is used yet.
   - The correction gate remains frozen.
2. **Phase 2: Full SLE training**
   - Adds the main solubility objective.
   - Keeps auxiliary/property losses deliberately light so `ln x₂` fitting dominates.
   - Unfreezes the bounded residual correction at `phase2_correction_unfreeze_epoch`.
   - Uses early stopping on validation MAE.
3. **Phase 3: Fine-tuning**
   - Uses a lower learning rate.
   - Uses moderate monotonicity and correction regularization.
   - Restores the best state at the end.

The v2 architecture keeps temperature out of the crystal-property encoder path
by default. `T_m`, `ΔH_fus`, and other temperature-invariant properties are
predicted from the solute graph alone, while temperature enters explicitly in
the NRTL/state block and the bounded residual corrector.

The maintained configs also keep `ΔCp_fus` fixed at `0.0` by default. The
solver still supports the extended heat-capacity term, but per-sample `ΔCp_fus`
prediction is now opt-in through `predict_dCp_fus=True`, because that variable
otherwise acts like an unsupervised latent degree of freedom.

The maintained configs now use the compact `ref_invT` NRTL parameterization by
default. In that mode the network predicts `tau(T_ref)` and one inverse-
temperature slope per direction, while older `legacy` and `abc` layouts remain
supported for compatibility with older checkpoints and experiments.

Morgan fingerprints can also be enabled as optional side information through
`use_morgan_features=True`. In that mode the training pipeline computes
fingerprints in the dataset/loader path and injects them into the learned
molecular representations before the crystal-property heads and pair block.

The maintained codebase also supports experimental descriptor-conditioned
priors for the `Hansen` and `V_m` heads. When `use_descriptor_priors=True`,
the dataset computes a compact fixed RDKit descriptor vector per molecule, a
small descriptor-side network predicts coarse priors, and the graph heads
learn only bounded residuals around those priors. This path is optional and
disabled by default.

The codebase also supports a stricter deterministic prior path through
`use_group_priors=True`. In that mode the dataset computes fixed
fragment-count features per molecule, and the `Hansen` / `V_m` heads learn
bounded residuals around a fixed group-contribution prior. The descriptor-prior
and group-prior modes are mutually exclusive.

The implementation lives in `src/tgnn_solv/trainer.py`, and the phase-specific
defaults are defined in `src/tgnn_solv/trainer.py::DEFAULT_PHASE_WEIGHTS` and
then merged with any config overrides inside `TGNNSolvTrainer`.

The current v3 training objective also includes two same-pair temperature
regularizers, and the canonical `scripts/train.py` path now uses pair-aware
train batching so these constraints are exercised whenever the dataset
contains multiple temperatures for the same `(solute, solvent)` pair:

- `pair_temp_rank`: encourages `ln x₂` to increase with temperature
- `vant_hoff_local`: encourages local linearity in `ln x₂` vs `1/T`

The relevant config controls are:

- `use_pair_temperature_batching`
- `pair_temperature_min_group_size`
- `pair_temperature_group_chunk_size`
- `encoder_role_mode`
- `encoder_role_specific_layers`
- `use_morgan_features`
- `morgan_radius`
- `morgan_n_bits`
- `morgan_hidden_dim`
- `use_descriptor_priors`
- `descriptor_prior_*`
- `use_group_priors`
- `group_prior_*`

The canonical processed split for both CLI and notebook training is:

- `notebooks/data/processed/train.csv`
- `notebooks/data/processed/val.csv`
- `notebooks/data/processed/test.csv`

The additional `*_solute.csv` and `*_solvent.csv` files are comparison splits
and are not the default training path.

## Run Training from the CLI

Use the training script directly once processed CSV files are available:

```bash
python scripts/train.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --device cuda
```

Useful optional overrides:

```bash
python scripts/train.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/debug.pt \
    --device cpu \
    --hidden-dim 128 \
    --n-gnn-layers 4 \
    --batch-size 32 \
    --lr 1e-4
```

For repeated runs with different random seeds, use:

```bash
python scripts/run_seeds.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv
```

For split-aware comparisons against baselines or older literature, prefer the
dedicated runner:

```bash
python scripts/run_split_comparisons.py \
    --processed-dir notebooks/data/processed \
    --splits "solute_scaffold,solute,solvent" \
    --models "tgnn_solv,direct_gnn,rf_baseline" \
    --config configs/paper_config.yaml \
    --output results/split_comparisons.json
```

For a matched backbone comparison against the asymmetric late-branch encoder,
run the same sweep with the dedicated comparison config:

```bash
python scripts/run_seeds.py \
    --config configs/paper_config_split_late.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --n-seeds 5 \
    --base-seed 42 \
    --output results/split_late_multi_seed_results.json \
    --checkpoint-dir checkpoints/split_late_seeds
```

`configs/paper_config_split_late.yaml` mirrors the default paper config and
changes only the encoder mode to `split_late`, so the comparison stays
apples-to-apples.

`scripts/train.py` and `scripts/run_seeds.py` can be launched directly from a
repository checkout and do not require a prior `pip install -e .` just to show
their CLI help.

## Run Training from Notebooks

Notebook workflow:

```bash
jupyter notebook notebooks/01_prepare_data.ipynb
jupyter notebook notebooks/02_train.ipynb
```

Recommended notebook sequence:

1. Prepare processed CSVs in `notebooks/01_prepare_data.ipynb`.
2. Train the main model in `notebooks/02_train.ipynb`.
3. Inspect inference examples in `notebooks/03_inference.ipynb`.
4. Run evaluation in `notebooks/04_evaluation.ipynb`.

## Hyperparameter Tuning with Optuna

Run Optuna from the CLI:

```bash
python scripts/run_optuna.py --models tgnn_solv,direct_gnn --n-trials 20
```

Useful tuning options include baseline-specific budgets:

```bash
python scripts/run_optuna.py \
    --models tgnn_solv,direct_gnn \
    --n-trials 20 \
    --baseline-epochs 200 \
    --baseline-patience 20
```

Notebook alternative:

```bash
jupyter notebook notebooks/08_optuna_tuning.ipynb
```

## Diagnostics

Quick dataset and training diagnostics:

```bash
python scripts/diagnose_training.py stats
python scripts/diagnose_training.py overfit --sample-size 1000 --epochs 200
```

Use these checks when:

- training does not converge,
- validation MAE is unstable,
- a new config appears to overfit or collapse,
- you need a fast sanity check before a longer training run.

`scripts/diagnose_training.py` is intentionally lightweight and is meant as a
sanity-check tool, not a full experiment runner.

## Related Script Roles

- `scripts/train.py` — canonical single-run training CLI
- `scripts/run_seeds.py` — canonical multi-seed wrapper
- `scripts/run_optuna.py` — tuning utility
- `scripts/diagnose_training.py` — pre-flight diagnostics
- `notebooks/02_train.ipynb` — interactive/manual training notebook
- `notebooks/08_optuna_tuning.ipynb` — interactive tuning notebook

## Recommended Workflow

```bash
python scripts/prepare_data.py \
    --output-dir notebooks/data/processed \
    --split-mode solute_scaffold \
    --seed 42

python scripts/train.py \
    --config configs/paper_config.yaml \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --checkpoint checkpoints/tgnn_solv_trained.pt \
    --device cuda

python scripts/evaluate_complete.py \
    --test-data notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --output results/full_evaluation.json
```
