"""The call-graph half of the device rule: what a driver reaches *after* it has trained.

`tests/test_device.py` asks whether a script resolves its own `--device`;
`tests/test_device_shell_drivers.py` asks whether a driver wishes for an accelerator in
its `DEVICE="${DEVICE:-...}"` line. Neither asks the question that this one does, and it
is the question that decides what an unhonourable device costs: *when* in a driver's
sequence does the refusal land.

The answer used to depend on which step you were in. `scripts/analysis/export_checkpoint_predictions.py`
resolves, so on a broken CUDA box the driver stopped at its first export. Three scoring
steps did not, and a driver reaches all three behind the training they score:
`run_compensation_surrogate.py` is step 3 of `kaggle_run.do_onemodel`, behind a warm-up
and a full unfrozen SLE run, and `run_uncertainty_calibration.py` and
`run_encoder_linear_probe.py` are the later steps of
`run_corrected_split_reproduction.sh`. Two of them built `torch.device(args.device)` raw
and the third handed the bare string to `load_model`; either way the accelerator went
unquestioned until `torch.load`. So `--allow-cpu` bought the *training* children a
`TGNN_ALLOW_CPU_FALLBACK` that the scoring step never read: they warned, ran to
completion, and the run then died with both checkpoints on disk unscored and no output
file written. The compute was spent and nothing was learned from it -- strictly worse
than the crash the flag was avoiding, which at least happened in the first minute.

RULE 4, then: a script a driver hands a device to must resolve it. The receivers are
discovered rather than listed, because the list is a call graph and a call graph is what
nobody re-derives by hand:

  * A *driver* is any `.sh` in the tree that mentions `DEVICE` or `--device` outside a
    comment -- the `${DEVICE:-...}` knob the experiment drivers open with, and the bare
    `--device cuda` `gcp_bootstrap.sh` writes onto its one command -- or any `.py` that
    builds an argv list containing `"--device"`.
  * A *receiver* is any `scripts/`- or `tools/`-relative `.py` path named by that driver
    which declares a `--device` flag of its own. The declaration filter is what keeps the
    post-processing steps out: `run_ranking_eval.py` and `run_conformal_calibration.py`
    are named on the same lines and take no device at all.

The `.sh` side deliberately does not require `--device` on the same command as the script
path. `run_corrected_split_reproduction.sh` now passes the flag through a
`DEV_ARGS=(--device "${DEVICE}")` array expansion, so a rule that reads command lines
would have gone blind to the very driver these three scoring steps sit in -- silently,
and while still passing.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

_SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".venv",
        "venv",
        "env",
        ".env",
        "build",
        "dist",
        "__pycache__",
        "node_modules",
        ".ruff_cache",
        ".pytest_cache",
        ".mypy_cache",
        ".ipynb_checkpoints",
        "site-packages",
        ".eggs",
        ".tox",
    }
)

DEVICE_MODULE = "tgnn_solv.device"

# A repo-relative script path as it appears in a command line or an argv list, preceded
# by a boundary so that a substring of a longer path cannot match.
_SCRIPT_PATH = re.compile(r"(?:^|[\s\"'=])((?:scripts|tools)/[\w./-]+\.py)")

# Receivers that do not resolve in-process, each with the argument for it. Asserted in
# both directions by `test_the_hot_path_exemptions_are_exactly_the_files_that_need_them`,
# so a third one fails the suite rather than joining a list nobody re-reads, and an entry
# that stops needing its exemption fails too.
HOT_PATH_EXEMPTIONS = {
    "scripts/cloud/kaggle_run.py": (
        "Answers for its device itself, and earlier than resolve_device could: a "
        "preflight that launches a real kernel, which catches a visible-but-sm_60 card "
        "that torch.cuda.is_available() reports as fine, plus --allow-cpu, which exports "
        "TGNN_ALLOW_CPU_FALLBACK into every child it spawns."
    ),
    "scripts/run_solprop.py": (
        "Known defect, not a decision, and the one hot-path receiver that still fails in "
        "the direction this rule exists for. _normalize_native_device (run_solprop.py) "
        "rewrites a named `--device cuda` to `cpu` with no message, so the SolProp native "
        "arm trains to completion on the CPU saying nothing -- the ten-hour failure, in "
        "the training step rather than the scoring step. It is named on "
        "docs/troubleshooting.md among the five that are worse than unchecked; this entry "
        "is here so the claim is asserted somewhere that fails when it stops being true."
    ),
}


def _repo_files(suffix: str) -> list[tuple[str, Path]]:
    found = []
    for path in sorted(REPO_ROOT.rglob(f"*{suffix}")):
        relative = path.relative_to(REPO_ROOT)
        if any(part in _SKIP_DIRS for part in relative.parts):
            continue
        found.append((relative.as_posix(), path))
    return found


def _declares_device_flag(tree: ast.AST) -> bool:
    """RULE 1's test, restated locally: an `add_argument` call carrying "--device"."""
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and any(
            isinstance(arg, ast.Constant) and arg.value == "--device"
            for arg in node.args
        )
        for node in ast.walk(tree)
    )


def _resolves_through_the_module(tree: ast.AST) -> bool:
    """Calls `resolve_device`, and imports that name from `tgnn_solv.device`.

    Both halves, because either alone passes for the wrong reason: a script can call a
    `resolve_device` it inherited from another script's namespace, and a script can
    import the name and never use it. The walk covers function bodies as well as module
    scope -- `run_uncertainty_calibration.py` imports inside `_generate_mc_dropout`, so
    that its post-hoc CSV half never has to import torch at all.
    """
    imported = any(
        isinstance(node, ast.ImportFrom)
        and node.module == DEVICE_MODULE
        and any(alias.name == "resolve_device" for alias in node.names)
        for node in ast.walk(tree)
    )
    called = any(
        isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "resolve_device")
            or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "resolve_device"
            )
        )
        for node in ast.walk(tree)
    )
    return imported and called


def _strip_shell_comments(text: str) -> str:
    """Whole-line comments only. A usage example in a header is not an invocation."""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def _scan() -> tuple[dict[str, set[str]], dict[str, ast.AST]]:
    """Map each receiver to the drivers that name it, plus each receiver's parsed tree."""
    declarers: dict[str, ast.AST] = {}
    for script, path in _repo_files(".py"):
        source = path.read_text(encoding="utf-8", errors="replace")
        if "--device" not in source:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        if _declares_device_flag(tree):
            declarers[script] = tree

    receivers: dict[str, set[str]] = {}

    for driver, path in _repo_files(".sh"):
        body = _strip_shell_comments(path.read_text(encoding="utf-8", errors="replace"))
        # Either spelling: the `${DEVICE:-...}` knob the experiment drivers open with, or
        # a `--device` written straight onto the command, as gcp_bootstrap.sh does.
        if "DEVICE" not in body and "--device" not in body:
            continue
        for script in set(_SCRIPT_PATH.findall(body)):
            if script in declarers:
                receivers.setdefault(script, set()).add(driver)

    for driver, path in _repo_files(".py"):
        source = path.read_text(encoding="utf-8", errors="replace")
        if "--device" not in source:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.List, ast.Tuple)):
                continue
            literals = [
                element.value
                for element in node.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            ]
            if "--device" not in literals:
                continue
            for literal in literals:
                for script in _SCRIPT_PATH.findall(literal):
                    if script in declarers and script != driver:
                        receivers.setdefault(script, set()).add(driver)

    return receivers, declarers


_RECEIVERS, _DECLARERS = _scan()

GUARDED_RECEIVERS = tuple(
    script for script in sorted(_RECEIVERS) if script not in HOT_PATH_EXEMPTIONS
)


def test_the_scan_finds_the_drivers_it_is_meant_to_be_watching() -> None:
    """A discovery that matches nothing passes every rule it has.

    Both halves of the discovery are narrow, and both have already been broken once by a
    repair rather than by a regression: the `.sh` half by `DEV_ARGS=(--device ...)`, the
    `.py` half by any driver that stops building argv as a list literal. These are the
    two shapes the rule was written to see -- a shell driver and a python one -- and the
    three scoring steps this file exists for. No count is asserted.
    """
    assert "scripts/analysis/export_checkpoint_predictions.py" in _RECEIVERS
    assert {
        "scripts/analysis/run_compensation_surrogate.py",
        "scripts/analysis/run_uncertainty_calibration.py",
        "scripts/analysis/run_encoder_linear_probe.py",
    } <= set(_RECEIVERS)
    assert "scripts/cloud/kaggle_run.py" in _RECEIVERS[
        "scripts/analysis/run_compensation_surrogate.py"
    ]
    assert "scripts/experiments/run_corrected_split_reproduction.sh" in _RECEIVERS[
        "scripts/analysis/run_encoder_linear_probe.py"
    ]


@pytest.mark.parametrize("script", GUARDED_RECEIVERS)
def test_every_script_a_driver_hands_a_device_to_resolves_it(script: str) -> None:
    """RULE 4. The refusal has to land before the compute, not after it."""
    assert _resolves_through_the_module(_DECLARERS[script]), (
        f"{script} is handed --device by {sorted(_RECEIVERS[script])} and does not "
        f"resolve it through {DEVICE_MODULE}. On a driver that trains first, an "
        "unavailable accelerator then costs the whole training before anyone hears "
        "about it, and TGNN_ALLOW_CPU_FALLBACK does not reach this step at all."
    )


@pytest.mark.parametrize("script", GUARDED_RECEIVERS)
def test_no_hot_path_receiver_builds_a_device_from_its_own_flag(script: str) -> None:
    """`torch.device(args.device)` is the specific shape RULE 4 replaces.

    It constructs happily on a CPU box -- `torch.device("cuda")` is not a claim that CUDA
    exists -- so it defers the failure to `torch.load` or the first `.to(device)`, and it
    reads no environment, so the documented escape hatch does not apply to it. A literal
    (`torch.device("cpu")`) is a different statement and passes: it names a device every
    box has.
    """
    offenders = [
        f"line {node.lineno}: torch.device({ast.unparse(node.args[0])})"
        for node in ast.walk(_DECLARERS[script])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "device"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "torch"
        and node.args
        and not isinstance(node.args[0], ast.Constant)
    ]
    assert not offenders, (
        f"{script} builds a torch.device from an expression rather than resolving it: "
        f"{offenders}. Call resolve_device() -- it is the only path that both refuses an "
        "undelivered accelerator and honours TGNN_ALLOW_CPU_FALLBACK."
    )


def test_the_hot_path_exemptions_are_exactly_the_files_that_need_them() -> None:
    """Both directions, so neither a new exemption nor a dead one can sit unread."""
    unresolved = {
        script
        for script in _RECEIVERS
        if not _resolves_through_the_module(_DECLARERS[script])
    }
    exempt = set(HOT_PATH_EXEMPTIONS)

    assert unresolved - exempt == set(), (
        f"{sorted(unresolved - exempt)} are handed a device by a driver and do not "
        "resolve it. Route them through tgnn_solv.device, or -- if the file answers for "
        "its device some other way -- add it to HOT_PATH_EXEMPTIONS with the argument."
    )
    assert exempt - unresolved == set(), (
        f"{sorted(exempt - unresolved)} are exempted from RULE 4 and no longer need it. "
        "Delete the entries: an exemption that exempts nothing still reads as standing "
        "permission for the next person."
    )
