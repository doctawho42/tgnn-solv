# FastSolv Training NaN Issue

## Summary

Earlier debugging showed that FastSolv scratch training could produce NaN
predictions from the first epoch on TGNN-Solv data. The failure mode was tied
to the external FastSolv descriptor pipeline, not to the maintained
TGNN-Solv or DirectGNN descriptor paths.

## Observed Failure Mode

During the original debugging pass, FastSolv descriptor generation returned
non-finite values before training even started. Once those NaNs entered the
model, all downstream metrics became NaN as well.

That originally led to a conservative practical conclusion:

- FastSolv works best in this repo as a pretrained external baseline
- scratch training should be treated as environment-sensitive until it is
  validated in the current runtime

## Current Maintained Status

The repository now does expose a maintained scratch-train wrapper through:

- `scripts/external/run_fastsolv.py train`
- `scripts/experiments/run_external_baseline_benchmark.py --fastsolv-mode scratch|both`

That means scratch FastSolv is no longer completely absent from the maintained
surface. The caveat is narrower:

- the wrapper path is supported
- the underlying FastSolv stack is still more brittle than the in-repo TGNN /
  DirectGNN paths
- if NaNs reappear, treat it as an external-baseline runtime issue first

## Scope Boundary

This issue is specific to the FastSolv stack.

It does not imply the same problem for the maintained descriptor baselines in
this repository:

- DirectGNN descriptor augmentation computes RDKit descriptors through the
  shared TGNN-Solv feature helper
- those descriptors are sanitized to finite values before model use
- descriptor normalization is computed on the training split only and stored in
  the checkpoint
- the RF descriptor baseline uses the same shared descriptor helper

## Recommended Usage

Safest usage modes remain:

```bash
python scripts/external/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/fastsolv_predictions.csv

python scripts/external/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics results/fastsolv_compare.json
```

If you want the scratch-training route, prefer the shared external benchmark
runner so the output lands in the canonical benchmark bundle contract:

```bash
python scripts/experiments/run_external_baseline_benchmark.py \
    --train-data notebooks/data/processed/train.csv \
    --val-data notebooks/data/processed/val.csv \
    --test-data notebooks/data/processed/test.csv \
    --out-dir results/external_baselines/article_benchmark \
    --fastsolv-mode both \
    --solprop-mode skip
```

The grouped `scripts/external/` layout remains the preferred navigation
surface. Legacy top-level wrappers remain available for compatibility.

If you need a trainable in-repo baseline on the same data, use one of:

- `DirectGNN`
- `DirectGNN + descriptors`
- `RF(descriptors)`
- `TGNN-Solv`

## If Custom FastSolv Training Is Necessary

Treat it as external-stack debugging, not a standard repo workflow. You will
need to validate:

- descriptor generation
- descriptor normalization
- expected FastSolv feature schema
- environment compatibility with the upstream FastSolv stack

The repo documents FastSolv honestly as optional and environment-sensitive for
that reason.
