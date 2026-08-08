# Troubleshooting

This page collects the most common operational issues when training,
evaluating, or deploying TGNN-Solv.

## CUDA Is Unavailable

Symptom — the run stops immediately with:

```
RuntimeError: CUDA was requested (--device cuda) but is not available.
Refusing to run on CPU instead: ...
```

This is deliberate, and it is new. The training, evaluation and analysis entry
points listed in `tests/test_device.py` — sixteen of the forty-seven scripts
that take a `--device` flag — resolve it through
`tgnn_solv.device.resolve_device`, which refuses to substitute CPU for an
accelerator you named. The old behaviour was one `WARNING` line followed by a
run that trained at ~15 s/it instead of ~1 s/it and produced no error and no
wrong number, only a result that never arrived: on 2026-08-08 a kernel upgrade
left the gate box without its NVIDIA module and six runs burned ten hours that
way. `--device cuda` on a box without CUDA is now fatal.

Every other script that owns a `--device` flag falls into one of three classes.
Some hand the string to a child process that does resolve it (`run_seeds.py`,
`learning_curves.py`, `run_split_comparisons.py`, `temperature_extrapolation.py`
all spawn `scripts/train.py` or `train_directgnn.py`; so do the
`scripts/experiments/*.sh` drivers). Most build a `torch.device` from it
themselves and get no check at all — `torch.device("cuda")` constructs happily
on a CPU box and fails at the first `.to(device)`.

Five are worse than unchecked, because they fail in the direction this page
exists to warn about. `run_pka_flip_certify.py:160`,
`run_pka_lambda_frontier.py:120` and `run_solprop.py:474` rewrite a named
`--device cuda` to CPU with no message; `run_pka_n_sweep.py:123` and
`run_pka_flip_competence.py:96` accept the flag and then hardcode CPU
regardless. Under the failure above these five run to completion on the CPU
saying nothing.

The lists in `tests/test_device.py` are the authority for which scripts this
error protects; a count quoted in prose is not, because two AST scans written a
day apart disagreed on it. If a script is not in those lists, do not assume the
error protects it.
`scripts/experiments/run_pka_trained_comparison.py` opts out on purpose and
says so in a comment: its arm trains small per-molecule MLPs in seconds, so a
CPU fallback costs a coffee rather than ten hours.

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

If CPU is genuinely what you want, say so — pass `--device cpu`. Invoke any of
those sixteen scripts directly with no flag and it cannot fire: their defaults
are `cpu`, `auto`, or `default_device()`, which reads the machine (CUDA if
present, else CPU, and MPS for the three written on a Mac). No default among
them names an accelerator, and `tests/test_device.py` asserts that.

Two routes type the flag for you, and both raise this error on a box without
CUDA even though you passed nothing:

- **The `scripts/experiments/*.sh` drivers.** Six open with
  `DEVICE="${DEVICE:-cuda}"` and hand `--device "${DEVICE}"` to every child:
  `run_corrected_split_reproduction.sh`, `run_data_efficiency.sh`,
  `run_e2_crystal_grounding.sh`, `run_e3_temperature_extrapolation.sh`,
  `run_e4_ablations.sh`, `run_e5_sigma_grounding.sh`. Set the variable rather
  than editing the script:

  ```bash
  DEVICE=cpu bash scripts/experiments/run_e2_crystal_grounding.sh
  ```

  (`run_e5_leakfree_followups.sh` already defaults to `cpu`.)

- **`scripts/cloud/kaggle_run.py`.** Its `--device` default is a deliberate
  literal `"cuda"` (`kaggle_run.py:548`), passed into every child it spawns,
  because a Kaggle session that quietly runs on CPU is a wasted session. Pass
  `--device cpu`, or `--allow-cpu` — see below.

`TGNN_ALLOW_CPU_FALLBACK=1` restores the old warn-and-continue behaviour for
the whole process, including `--device cuda`:

```bash
TGNN_ALLOW_CPU_FALLBACK=1 python scripts/train.py --config ... --device cuda
```

Use it only when a command line with a hardcoded `--device cuda` has to run on
a CPU box anyway — a smoke test of the wiring, or reproducing a driver script
verbatim. It reintroduces exactly the failure above, so never set it for a run
whose numbers you intend to keep. `scripts/cloud/kaggle_run.py --allow-cpu` is
the same permission for a Kaggle session: it skips that script's own
kernel-launch preflight and exports `TGNN_ALLOW_CPU_FALLBACK=1` to every child
it spawns.

The preflight in `kaggle_run.py` is a stronger check than `resolve_device`'s,
which only asks `torch.cuda.is_available()`. It launches a real kernel, so it
also catches a card that is visible but too old for the installed PyTorch — a
Tesla P100 (`sm_60`) reports as available and then fails on first use.

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

## `pytest` Uses the Wrong Python Environment

Symptom:

- tests fail during import with missing `numpy`, `pandas`, `torch`, or RDKit
- the project code itself is fine when run from the intended conda env

Cause:

- `pytest` or `python` resolved to a system interpreter instead of the project
  runtime

Practical fix:

```bash
/Users/nikitapolomosnov/anaconda3/envs/tgnn-solv/bin/python -m pytest tests/ -v
```

or activate the intended environment first before running the CLI.

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

## Custom Adapter Benchmark Fails To Load

Symptom:

- `benchmark_adapter_model.py` raises an import error
- the adapter object does not satisfy the expected contract

Checks:

- adapter reference is in `module:ClassOrFactory` form
- the module is importable from the selected Python environment
- the object implements:
  - `describe()`
  - `fit(...)`
  - `predict_frame(...)`

If the adapter works locally but not from the lab, inspect the lab sidebar's
`Python command` field and make sure it points at the environment where the
adapter module is installed.

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
