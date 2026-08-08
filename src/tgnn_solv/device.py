"""One home for turning a requested device string into a `torch.device`.

Twelve scripts each carried a copy of this function, and they gave three different
answers to "you named an accelerator this box does not have". `cbfadee` changed exactly
one of them -- it touched two files, `scripts/train.py` and
`scripts/experiments/run_e5_sigma_grounding.sh` -- so that an accelerator asked for by
name and not delivered is an error rather than a warning. Of the eleven it left:

- Six, `train_directgnn.py` (the DirectGNN control arm) among them, printed one
  `WARNING:` line and ran on the CPU.
- `scripts/analysis/export_checkpoint_predictions.py`, the prediction exporter seven of
  the nine `scripts/experiments` drivers call, did the same with no line at all.
- The four `scripts/analysis` `_resolve_device` copies never fell back on CUDA: they
  handed the string to `torch.device` and died at the first `.to(device)`. They fell
  back only for MPS, behind a bracketed tag line rather than a `WARNING:` one.

This module is one behaviour, the strict one. All twelve import it, as do the four
scripts that had been reaching a copy through another script's module namespace;
`tests/test_device.py` names both sets, and those lists are the authority for what is
protected -- a count quoted in prose is not, because two AST scans written a day apart
disagreed on the total. Many other entry points take a `--device` flag without coming
through here. A minority hand it to a child process that does; most build a
`torch.device` in the same process and get no check at all. Five are worse than
unchecked: `run_pka_flip_certify.py`, `run_pka_lambda_frontier.py` and `run_solprop.py`
rewrite a named `--device cuda` to CPU with no message, and `run_pka_n_sweep.py` and
`run_pka_flip_competence.py` accept the flag and then hardcode CPU regardless.

Two knobs, both because the copies genuinely disagreed:

- `allow_tf32_from_env`: the two training scripts honoured `TGNN_MATMUL_TF32`, the
  other ten did not, and turning TF32 on underneath an evaluation would move reported
  metrics whenever that variable happened to be exported for training. It defaults to
  off and the training scripts opt in.
- `"auto"`: four of the five `scripts/analysis` copies accepted it and the other eight
  would have handed it to `torch.device("auto")` and died. It is accepted here, and
  means the same thing `default_device(prefer_mps=True)` returns.

`default_device` is not a repair of an older regression; it is a precondition of this
one. Raising on an undelivered accelerator is right when the *user* named it and wrong
when argparse did, and eleven of the thirteen entry points that now call it hardcoded a
bare `default="cuda"` (or `"mps"`) that argparse hands over with no flag typed. Making
the raise universal is what would kill the DirectGNN control arm on a MacBook and the
DirectGNN error diagnostics on every box that is not a Mac. Neither died after
`cbfadee`: at `cbfadee` `train_directgnn.py` still had its own lenient copy, and the
diagnostics imported the equally lenient one from `run_full_budget_experiment`.

Those eleven now read the machine here, alongside `scripts/train.py` and
`run_medium_budget_comparison.py`, which already asked it in two ad-hoc spellings.
Two entry points keep a literal accelerator default on purpose:
`scripts/cloud/kaggle_run.py`, because a Kaggle session that quietly runs on CPU is a
wasted session and it answers for that with its own kernel-launch preflight and
`--allow-cpu`, and `scripts/experiments/run_pka_trained_comparison.py`, which never
reaches this resolver. An argparse default has to be a statement about the machine,
not a wish.
"""

from __future__ import annotations

import os

import torch

_TRUTHY = ("1", "true", "yes", "on")
_TF32_TRUTHY = ("1", "true", "high", "yes", "on")


def _env_is_set(name: str, truthy: tuple[str, ...] = _TRUTHY) -> bool:
    """Return True when environment variable `name` holds an affirmative value."""
    return os.environ.get(name, "").lower() in truthy


def default_device(*, prefer_mps: bool = False) -> str:
    """The device string to use as an argparse default: what this box actually has.

    A hardcoded `default="cuda"` turns "the user did not say" into "the user demanded an
    accelerator", which `resolve_device` is now obliged to treat as fatal. Call this
    instead, so that no-flag-typed means the best device present.

    Args:
        prefer_mps: Whether Apple MPS counts as an acceleration to fall back to when
            CUDA is absent. False -- CUDA else CPU -- for the training entry points,
            matching the default `scripts/train.py` has had since `da35f1b` added it;
            several of them run graph ops that MPS has historically been the wrong
            place for, and a local smoke run wants to be boring rather than fast. True
            for the two that hardcoded `default="mps"` and were plainly written on a
            Mac (`export_checkpoint_predictions.py`, the DirectGNN error diagnostics),
            and for `run_medium_budget_comparison.py`, whose own ladder already fell
            through to MPS.
    """
    if torch.cuda.is_available():
        return "cuda"
    if prefer_mps and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def resolve_device(
    device_str: str,
    *,
    allow_tf32_from_env: bool = False,
) -> torch.device:
    """Resolve a requested device, refusing to substitute CPU for an accelerator.

    The fallback used to be silent-ish: one WARNING line, then 300 KB of tqdm output on
    top of it. On 2026-08-08 a kernel upgrade left the gate box without its NVIDIA
    module, six `--device cuda` runs fell through to CPU, and they trained for ten hours
    at 15 s/it against ~1 s/it on the V100 -- roughly two months to a result -- without
    a single error line. An accelerator asked for by name and quietly not delivered is
    never what the caller wanted, so it is an error now. Set TGNN_ALLOW_CPU_FALLBACK=1
    to restore the old behaviour for a smoke run.

    Args:
        device_str: The device as requested on the command line ("cuda", "cuda:1",
            "mps", "cpu", or "auto"). Case and surrounding space are ignored when
            deciding whether the device is available; the string itself is then handed
            to `torch.device` unchanged, so "  CPU " raises there as it always has.
            "auto" never raises -- it is a question about the box, not a demand.
        allow_tf32_from_env: Whether `TGNN_MATMUL_TF32` may switch this process to TF32
            matmul once a CUDA device is resolved. True only in the training scripts;
            an evaluation must not silently change precision under an environment
            variable that was exported for a training run.
    """
    requested = device_str.strip().lower()
    if requested == "auto":
        device_str = default_device(prefer_mps=True)
        requested = device_str
    allow_fallback = _env_is_set("TGNN_ALLOW_CPU_FALLBACK")
    unavailable = None
    if requested.startswith("cuda") and not torch.cuda.is_available():
        unavailable = "CUDA"
    elif requested == "mps" and not torch.backends.mps.is_available():
        unavailable = "MPS"
    if unavailable is not None:
        if not allow_fallback:
            raise RuntimeError(
                f"{unavailable} was requested (--device {device_str}) but is not available. "
                f"Refusing to run on CPU instead: on this corpus that is a ~15x slowdown "
                f"that produces no error and no wrong number, only a run that never finishes. "
                f"Pass --device cpu if CPU is what you meant, or set "
                f"TGNN_ALLOW_CPU_FALLBACK=1 to fall back silently."
            )
        print(f"WARNING: {unavailable} requested but unavailable; falling back to CPU.")
        return torch.device("cpu")
    dev = torch.device(device_str)
    if dev.type == "cuda" and allow_tf32_from_env and _env_is_set(
        "TGNN_MATMUL_TF32", _TF32_TRUTHY
    ):
        # TF32 matmul: large speedup on Ampere+/Blackwell (a no-op on T4, which has
        # no TF32), numerically negligible for training. Opt-in so default FP32 runs
        # stay bit-comparable across seeds.
        torch.set_float32_matmul_precision("high")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        print("   TF32 matmul enabled (TGNN_MATMUL_TF32).")
    return dev
