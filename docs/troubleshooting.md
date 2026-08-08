# Troubleshooting

This page collects the most common operational issues when training,
evaluating, or deploying TGNN-Solv.

## CUDA Is Unavailable

Symptom — the run stops immediately with:

```
RuntimeError: CUDA was requested (--device cuda) but is not available.
Refusing to run on CPU instead: ...
```

This is deliberate, and it is new. A set of training, evaluation and analysis
entry points resolve their `--device` through `tgnn_solv.device.resolve_device`,
which refuses to substitute CPU for an accelerator you named. Which entry points
is a question with a mechanical answer rather than a remembered one —
`grep -rl 'from tgnn_solv.device import' scripts src` — and it is the same
question `tests/test_device.py` re-asks of the tree on every test run. The old
behaviour was one `WARNING` line followed by a
run that trained at ~15 s/it instead of ~1 s/it and produced no error and no
wrong number, only a result that never arrived: on 2026-08-08 a kernel upgrade
left the gate box without its NVIDIA module and six runs burned ten hours that
way. `--device cuda` on a box without CUDA is now fatal.

The refusal is also ordered, and the order is most of what it is worth. A driver
reaches its scoring steps behind the training they score:
`run_compensation_surrogate.py` is step 3 of `kaggle_run.py --do onemodel`, and
the uncertainty and encoder-probe steps are the tail of
`run_corrected_split_reproduction.sh`. Those three used to build a device from
the flag without asking, so under `--allow-cpu` the training children warned and
ran to completion — 40 warm-up plus 120 SLE epochs — and the run then died in
`torch.load` with both checkpoints on disk unscored and no output file written.
They resolve now: `TGNN_ALLOW_CPU_FALLBACK` reaches every step of the sequence,
and a device this box does not have stops the first step rather than the last.
`tests/test_device_hot_paths.py` derives the receivers from the drivers and
asserts it, so a new scoring step cannot rejoin the old shape quietly.

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

The scan in `tests/test_device.py` is the authority for which scripts this error
protects, and the rules it scans by are stated at the top of that file. Neither a
list nor a count is the authority: a hand-written list cannot know about a script
written after it — the one that used to be here had already gone stale — and two
AST scans written a day apart disagreed on the total. If a script does not call
`resolve_device`, do not assume the error protects it.
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
those resolving scripts directly with no flag and it cannot fire: their defaults
are `cpu`, `auto`, or `default_device()`, which reads the machine (CUDA if
present, else CPU, and MPS for the ones written on a Mac). No default among them
names an accelerator, and `tests/test_device.py` asserts that over every script
its scan finds rather than over a list of names — including the two exempted from
the rule, which it separately requires to be scripts that never reach the raise.

One route types the flag for you, and raises this error on a box without CUDA
even though you passed nothing:

- **`scripts/cloud/kaggle_run.py`.** Its `--device` default is a deliberate
  literal `"cuda"` (`kaggle_run.py:548`), passed into every child it spawns,
  because a Kaggle session that quietly runs on CPU is a wasted session. Pass
  `--device cpu`, or `--allow-cpu` — see below.

The `scripts/experiments/*.sh` drivers were the other route until `DEVICE`
stopped defaulting to `cuda` in all six of them
(`run_corrected_split_reproduction.sh`, `run_data_efficiency.sh`,
`run_e2_crystal_grounding.sh`, `run_e3_temperature_extrapolation.sh`,
`run_e4_ablations.sh`, `run_e5_sigma_grounding.sh`). They now pass `--device`
only when you set the variable, so with nothing typed each child reads the box
through `default_device()` — the same rule as invoking it by hand. That is what
`DEVICE=cuda` was a wish for rather than a statement about: `run_e5` exports
`KMP_DUPLICATE_LIB_OK` for the macOS libomp clash and documents a CPU smoke mode
in its own header, so it is written to be run on a Mac, and on one it died at
the first arm.

Setting the variable is still the right thing on a GPU box, and it is the only
thing that makes a broken CUDA install fatal there rather than merely slow:

```bash
DEVICE=cuda bash scripts/experiments/run_e5_sigma_grounding.sh    # demand it
DEVICE=cpu  bash scripts/experiments/run_e2_crystal_grounding.sh  # or refuse it
```

(`run_e5_leakfree_followups.sh` keeps `DEVICE="${DEVICE:-cpu}"` — the same shape
pointed the other way. It cannot raise, but it does make a GPU box run that
script's exports on the CPU unless you say otherwise.)

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

## `TGNN-DEVICE`: a CPU Run On a Box That Has an NVIDIA Card

Symptom — a block of tagged lines on stderr, before anything else happens:

```
==============================================================================
TGNN-DEVICE  The --device default was read off this box as "cpu" -- but 1
TGNN-DEVICE  NVIDIA display device is on its PCI bus. The card is here;
TGNN-DEVICE  CUDA is not usable. Check `nvidia-smi` first. ...
==============================================================================
```

This is the *other* half of the failure above, the half no error can catch. With
no `--device` typed, nothing was requested, so `resolve_device` has nothing to
refuse: `default_device()` reads the machine and gets `cpu`. The Python drivers
then forward that answer to their children as an explicit `--device cpu`
(`run_seeds.py`, `learning_curves.py`, `run_split_comparisons.py`,
`temperature_extrapolation.py` all do), and `--device cpu` is a legitimate
request that raises nothing anywhere. On 2026-08-08 that is the path the gate
box took.

So `default_device()` announces itself when — and only when — it answers `cpu`
on a box that has an NVIDIA GPU on its PCI bus. It reads `/sys/bus/pci/devices`
to tell the two cases apart: a MacBook has no card to lose and prints nothing,
a box whose kernel module went missing still has its V100 bolted to it. The
banner names which of the two causes it is, since they need different repairs —
`torch.version.cuda is None` means the wheel is wrong and no driver will help;
a CUDA build that still reports `is_available()` False means the driver is.

It is not fatal and it refuses nothing. To silence it, say that CPU is what you
meant:

```bash
TGNN_ALLOW_CPU_FALLBACK=1 python scripts/run_seeds.py ...
```

`--device cpu` will not silence it — an argparse default is computed while the
parser is built, before your flags are parsed.

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
