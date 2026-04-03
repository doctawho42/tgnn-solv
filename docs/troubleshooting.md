# Troubleshooting

This page collects the most common operational issues when training,
evaluating, or deploying TGNN-Solv.

## CUDA Is Unavailable

Symptom:

- `torch.cuda.is_available()` is `False`
- training falls back to CPU

Checks:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Actions:

- verify the correct PyTorch build is installed
- reinstall with the CUDA wheel index if needed
- make sure the selected device matches the hardware

```bash
pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu121
```

## MPS Training Gets Killed or Crashes

Typical symptom on Apple Silicon:

- process terminated with `SIGKILL`
- training dies during large Phase 2 workloads

Practical mitigations:

- reduce batch size
- reduce pair-temperature group chunk size
- prefer resumable checkpoints with `--checkpoint-every`
- use CPU if the run is too memory-heavy for `mps`

This is especially relevant for the full dataset and medium-budget runs.

## `resource_tracker` Leaked Semaphore Warning

Symptom:

```text
resource_tracker: There appear to be leaked semaphore objects to clean up at shutdown
```

Interpretation:

- this is usually cleanup noise from Python multiprocessing
- it is often not the root cause of the actual failure

Check the earlier stack trace or training log for the real exception.

## Pair-Temperature Losses Explode

Most relevant losses:

- `pair_temp_rank`
- `vant_hoff_local`

Known failure mode:

- very small `|1/T_j - 1/T_i|` amplifies the van't Hoff slope term

Current maintained safeguards:

- minimum clamp on inverse-temperature difference
- per-pair hard cap on van't Hoff loss
- smaller `vant_hoff_local` weight
- per-component loss logging in training

If training still becomes dominated by regularizers:

- inspect the logged weighted loss components
- make sure `loss/sol_fraction` remains healthy
- reduce the relevant regularizer weights before trusting the run

## Out of Memory

Symptoms:

- CUDA OOM
- MPS memory pressure and kill
- extreme slowdown before failure

Mitigations:

- lower `batch_size`
- reduce `hidden_dim`
- reduce the training budget for smoke tests
- use `small_debug.yaml` for wiring tests
- checkpoint frequently and resume

## RDKit Import or Descriptor Failures

Symptom:

- `ImportError` for RDKit
- descriptor generation fails
- downstream descriptor baselines or descriptor-augmented DirectGNN break

Action:

```bash
conda install -c conda-forge rdkit
```

Important note:

- the maintained descriptor paths sanitize non-finite values
- if descriptor generation fails entirely, the issue is usually environment
  setup rather than the model code

## FastSolv Produces NaNs

This is a known external-stack issue when training FastSolv from scratch on
TGNN-Solv data.

Recommended policy:

- treat FastSolv as an optional pretrained external baseline
- do not treat scratch FastSolv training as a maintained default workflow

See `FASTSOLV_NaN_ROOT_CAUSE.md` for the detailed note.

## Resume Does Not Work As Expected

Check that you are using the same checkpoint path for saving and resuming:

```bash
python scripts/training/train.py \
    --resume checkpoints/tgnn_resume.pt \
    --checkpoint checkpoints/tgnn_resume.pt
```

Also verify:

- the checkpoint file exists
- the checkpoint came from the same model family
- config changes are not incompatible with the saved state

## DirectGNN Descriptor Augmentation Looks Wrong

Things to verify:

- `use_descriptor_augmentation=true`
- the checkpoint contains `descriptor_mean` and `descriptor_std`
- train and inference are using the same descriptor feature path

If those normalization statistics are missing, the checkpoint is not a valid
descriptor-augmentation artifact.

## The Site Shows Raw Markdown Instead of Styled MkDocs Pages

Symptom:

- button classes appear as literal text
- admonitions such as `!!! abstract` render raw
- Material icons show up literally

Cause:

- GitHub Pages is serving raw markdown rather than the built MkDocs site

Fix:

- set repository `Settings -> Pages -> Source` to `GitHub Actions`
- let `.github/workflows/docs.yml` deploy the built `site/` artifact

## The Wrong Split Was Used

This is one of the easiest ways to invalidate a comparison.

Checks:

- confirm the dataset paths
- inspect `split_manifest.json`
- verify whether the run used:
  - `train.csv`, `val.csv`, `test.csv`
  - or one of the `_solute` / `_solvent` split families

For architecture comparisons, the maintained default is the full
`solute_scaffold` split.

## I Need a Cheap Smoke Test Before Launching a Long Run

Use:

- `configs/small_debug.yaml`
- tiny local subsets
- `scripts/training/diagnose_training.py`

This is the right place for debugging:

- environment wiring
- checkpoint save / resume
- loss logging
- feature-path correctness

It is not the right place for architectural conclusions.

## If You Still Cannot Isolate the Problem

Capture:

- command used
- config file
- device
- exact log excerpt
- whether the failure happens in:
  - data loading
  - forward pass
  - solver
  - loss computation
  - checkpoint save / resume

That is usually enough to reduce the issue from "training failed" to a specific
subsystem.

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Installation](getting_started/installation.md)
- [Training](training.md)
- [FAQ](faq.md)
- [Free GPU / Preemptible Training](free_gpu_training.md)

</div>
