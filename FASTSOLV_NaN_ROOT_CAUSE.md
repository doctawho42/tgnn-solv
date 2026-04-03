# FastSolv Training NaN Issue

## Summary

Training FastSolv from scratch on TGNN-Solv data can produce NaN predictions
from the first epoch. The failure mode is tied to the external FastSolv
descriptor pipeline, not to the maintained TGNN-Solv or DirectGNN descriptor
paths.

## Observed Failure Mode

During the original debugging pass, FastSolv descriptor generation returned
non-finite values before training even started. Once those NaNs entered the
model, all downstream metrics became NaN as well.

That led to a simple practical conclusion:

- FastSolv works best in this repo as a pretrained external baseline
- training FastSolv from scratch on these splits is not a maintained workflow

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

Use FastSolv in one of these two modes:

```bash
python scripts/external/run_fastsolv.py predict \
    --input notebooks/data/processed/test.csv \
    --output results/fastsolv_predictions.csv

python scripts/external/run_fastsolv.py compare \
    --input notebooks/data/processed/test.csv \
    --tgnn-checkpoint checkpoints/tgnn_solv_trained.pt \
    --metrics results/fastsolv_compare.json
```

The grouped `scripts/external/` path is the preferred navigation surface.
Legacy top-level wrappers remain available for compatibility.

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
