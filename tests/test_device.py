"""Tests for the shared device resolver.

The behaviour under test is the one `cbfadee` introduced in `scripts/train.py` and this
module now holds for all twelve scripts that carried a copy: an accelerator requested by
name and not available is a hard error, not a WARNING line followed by a ten-hour CPU
run. `cbfadee` itself changed only `scripts/train.py`; the other eleven copies stayed
lenient until this consolidation, so nothing below is a regression it caused.

The other half is `default_device`, and it is what keeps the strict rule from breaking
the arms as it spreads. Raising is right when the user named the accelerator and wrong
when argparse named it for them, and eleven of the thirteen entry points that now call
`default_device` hardcoded a bare `default="cuda"` or `default="mps"` -- so making the
raise universal without it would make the DirectGNN control arm die on a MacBook with no
flag typed, and the DirectGNN error diagnostics die on every box that is not a Mac.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from tgnn_solv.device import default_device, resolve_device


REPO_ROOT = Path(__file__).resolve().parents[1]

# Every script that used to carry its own copy of resolve_device.
SHARED_RESOLVER_SCRIPTS = (
    "scripts/train.py",
    "scripts/train_directgnn.py",
    "scripts/evaluate_complete.py",
    "scripts/run_ablation.py",
    "scripts/run_full_budget_experiment.py",
    "scripts/validate_physics.py",
    "scripts/probe_gsol_descriptor_recovery.py",
    "scripts/analysis/export_checkpoint_predictions.py",
    "scripts/analysis/weight_analysis.py",
    "scripts/analysis/visualize_attribution.py",
    "scripts/analysis/diagnose_gradient_flow.py",
    "scripts/analysis/analyze_timp_channels.py",
)

# Scripts that reached resolve_device through *another script's* module namespace --
# run_full_budget_experiment for three of them, validate_physics for
# analyze_intermediates. They would resolve only because that host script's own
# `from tgnn_solv.device import ...` re-binds the name, so an unused-import sweep over
# the host would break them with an ImportError while the rest of this file stayed
# green. They now import it directly; this is the assertion that keeps them that way.
FORMER_REEXPORT_IMPORTERS = (
    "scripts/analyze_intermediates.py",
    "scripts/run_medium_budget_comparison.py",
    "scripts/run_phase1_diagnostic.py",
    "scripts/evaluation/run_directgnn_error_structure_diagnostics.py",
)

# Every script whose --device default is now read off the machine. Eleven of them
# hardcoded a bare accelerator name -- a wish about the hardware that argparse then
# handed to resolve_device as a demand. The two exceptions already asked the machine,
# in two different ad-hoc spellings: scripts/train.py ("cuda" if available else "cpu",
# unchanged since da35f1b) and run_medium_budget_comparison.py (the full cuda/mps/cpu
# ladder). They are listed so neither spelling can drift back to a literal.
AVAILABILITY_AWARE_DEFAULT_SCRIPTS = (
    "scripts/train.py",
    "scripts/train_directgnn.py",
    "scripts/run_ablation.py",
    "scripts/run_full_budget_experiment.py",
    "scripts/validate_physics.py",
    "scripts/run_phase1_diagnostic.py",
    "scripts/run_medium_budget_comparison.py",
    "scripts/run_seeds.py",
    "scripts/run_split_comparisons.py",
    "scripts/learning_curves.py",
    "scripts/temperature_extrapolation.py",
    "scripts/evaluation/run_directgnn_error_structure_diagnostics.py",
    "scripts/analysis/export_checkpoint_predictions.py",
)


def test_cpu_request_is_honoured() -> None:
    assert resolve_device("cpu") == torch.device("cpu")


def test_availability_check_ignores_case_and_space(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalisation applies to the availability check only, as in all eight copies.

    Eight of the twelve copies called `.strip().lower()` and then passed the raw string
    to `torch.device`; the four `scripts/analysis` `_resolve_device` copies compared the
    unnormalised string instead, so `"AUTO"` or `" mps"` missed their branches entirely.
    """
    monkeypatch.delenv("TGNN_ALLOW_CPU_FALLBACK", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    with pytest.raises(RuntimeError, match="CUDA was requested"):
        resolve_device(" CUDA ")

    # The string itself still reaches torch.device untouched, so a padded or
    # miscased device that *is* available fails there exactly as it always did.
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    with pytest.raises(RuntimeError, match="Invalid device string"):
        resolve_device(" CUDA ")


def test_unavailable_cuda_raises_instead_of_falling_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TGNN_ALLOW_CPU_FALLBACK", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    with pytest.raises(RuntimeError) as excinfo:
        resolve_device("cuda")

    message = str(excinfo.value)
    assert "CUDA" in message
    # The message has to tell the caller both ways out, or it just moves the problem.
    assert "--device cpu" in message
    assert "TGNN_ALLOW_CPU_FALLBACK=1" in message


def test_unavailable_cuda_index_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TGNN_ALLOW_CPU_FALLBACK", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    with pytest.raises(RuntimeError):
        resolve_device("cuda:1")


def test_unavailable_mps_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TGNN_ALLOW_CPU_FALLBACK", raising=False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)

    with pytest.raises(RuntimeError) as excinfo:
        resolve_device("mps")

    assert "MPS" in str(excinfo.value)


@pytest.mark.parametrize("flag", ["1", "true", "TRUE", "yes", "on"])
def test_opt_out_restores_the_old_warning_and_cpu(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flag: str,
) -> None:
    monkeypatch.setenv("TGNN_ALLOW_CPU_FALLBACK", flag)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    device = resolve_device("cuda")

    assert device == torch.device("cpu")
    # Byte-identical to the line the six lenient copies printed, in case a log is grepped.
    assert (
        "WARNING: CUDA requested but unavailable; falling back to CPU."
        in capsys.readouterr().out
    )


def test_available_accelerator_is_not_second_guessed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)

    assert resolve_device("cuda") == torch.device("cuda")


def _patch_tf32_surface(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Capture the three global switches TF32 flips, without needing a GPU."""
    calls: dict[str, object] = {}
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(
        torch,
        "set_float32_matmul_precision",
        lambda precision: calls.__setitem__("precision", precision),
    )
    monkeypatch.setattr(
        torch.backends.cuda, "matmul", SimpleNamespace(allow_tf32=False)
    )
    monkeypatch.setattr(torch.backends, "cudnn", SimpleNamespace(allow_tf32=False))
    return calls


def test_tf32_env_is_ignored_unless_the_caller_opts_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evaluation callers keep FP32 even with TGNN_MATMUL_TF32 exported for training."""
    calls = _patch_tf32_surface(monkeypatch)
    monkeypatch.setenv("TGNN_MATMUL_TF32", "1")

    resolve_device("cuda")

    assert calls == {}
    assert torch.backends.cuda.matmul.allow_tf32 is False
    assert torch.backends.cudnn.allow_tf32 is False


def test_tf32_env_applies_for_training_callers(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _patch_tf32_surface(monkeypatch)
    monkeypatch.setenv("TGNN_MATMUL_TF32", "high")

    resolve_device("cuda", allow_tf32_from_env=True)

    assert calls == {"precision": "high"}
    assert torch.backends.cuda.matmul.allow_tf32 is True
    assert torch.backends.cudnn.allow_tf32 is True


def test_tf32_stays_off_on_cpu_for_training_callers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_tf32_surface(monkeypatch)
    monkeypatch.setenv("TGNN_MATMUL_TF32", "1")

    resolve_device("cpu", allow_tf32_from_env=True)

    assert calls == {}


def test_auto_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """"auto" is a question about the box, not a demand, so it resolves on any box.

    Four of the five scripts/analysis copies accepted it; the other eight, including
    that directory's export_checkpoint_predictions.py, would have handed it straight to
    torch.device("auto") and died there.
    """
    monkeypatch.delenv("TGNN_ALLOW_CPU_FALLBACK", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)

    assert resolve_device("auto") == torch.device("cpu")

    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert resolve_device("auto") == torch.device("mps")

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert resolve_device("auto") == torch.device("cuda")


def test_default_device_prefers_cuda_then_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert default_device() == "cuda"
    assert default_device(prefer_mps=True) == "cuda"

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    # prefer_mps is off by default, preserving scripts/train.py's historical cuda-else-cpu.
    assert default_device() == "cpu"
    assert default_device(prefer_mps=True) == "mps"

    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    assert default_device() == "cpu"
    assert default_device(prefer_mps=True) == "cpu"


def test_every_default_device_result_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    """The two halves have to agree: a default must never trip the raise it feeds.

    This is the regression that shipped -- `default="cuda"` on a Mac, then a resolver
    that refuses it -- expressed as an assertion over all four availability worlds.
    """
    monkeypatch.delenv("TGNN_ALLOW_CPU_FALLBACK", raising=False)
    for cuda in (True, False):
        for mps in (True, False):
            monkeypatch.setattr(torch.cuda, "is_available", lambda cuda=cuda: cuda)
            monkeypatch.setattr(
                torch.backends.mps, "is_available", lambda mps=mps: mps
            )
            for prefer_mps in (False, True):
                requested = default_device(prefer_mps=prefer_mps)
                assert resolve_device(requested).type == requested


def _load_kaggle_run():
    spec = importlib.util.spec_from_file_location(
        "_kaggle_run_under_test", REPO_ROOT / "scripts" / "cloud" / "kaggle_run.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("allow_cpu, expected", [(True, "1"), (False, None)])
def test_kaggle_allow_cpu_reaches_the_child(
    monkeypatch: pytest.MonkeyPatch, allow_cpu: bool, expected: str | None
) -> None:
    """--allow-cpu has to grant the permission where the raise happens: in the child.

    It used to skip only kaggle_run's own preflight, while children were still spawned
    with `--device cuda` -- so on a CPU box the flag advertised as permitting the
    fallback instead guaranteed a RuntimeError out of the first child, which run() then
    re-raised.
    """
    module = _load_kaggle_run()
    monkeypatch.setattr(module, "_ALLOW_CPU", allow_cpu)
    seen: dict[str, str] = {}

    def fake_subprocess_run(cmd, cwd=None, env=None):
        seen.update(env)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)
    module.run(["python", "-c", "pass"])

    assert seen.get("TGNN_ALLOW_CPU_FALLBACK") == expected


@pytest.mark.parametrize("script", SHARED_RESOLVER_SCRIPTS)
def test_scripts_use_the_shared_resolver(script: str) -> None:
    """Guard against the copy coming back.

    One lenient copy cost the gate box ten hours on 2026-08-08; twelve copies is why
    fixing that one in cbfadee left seven others that would still fall through to CPU
    on a `--device cuda` run -- six behind a WARNING line, one behind nothing.
    """
    source = (REPO_ROOT / script).read_text()

    assert "from tgnn_solv.device import" in source
    assert "resolve_device" in source
    assert re.search(r"^def _?resolve_device\(", source, flags=re.MULTILINE) is None


@pytest.mark.parametrize("script", FORMER_REEXPORT_IMPORTERS)
def test_indirect_importers_are_pinned_to_the_module(script: str) -> None:
    source = (REPO_ROOT / script).read_text()

    assert "from tgnn_solv.device import" in source
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.module != "tgnn_solv.device":
            imported = {alias.name for alias in node.names}
            assert "resolve_device" not in imported, (
                f"{script} takes resolve_device from {node.module!r} rather than "
                "tgnn_solv.device; an unused-import sweep over that module would "
                "break this script with an ImportError and leave the suite green."
            )


def _device_defaults(script: str) -> list[ast.expr]:
    """Every `default=` passed alongside a `--device` add_argument in `script`."""
    source = (REPO_ROOT / script).read_text()
    defaults: list[ast.expr] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if not any(
            isinstance(arg, ast.Constant) and arg.value == "--device"
            for arg in node.args
        ):
            continue
        defaults += [kw.value for kw in node.keywords if kw.arg == "default"]
    return defaults


@pytest.mark.parametrize("script", AVAILABILITY_AWARE_DEFAULT_SCRIPTS)
def test_device_defaults_are_read_off_the_machine(script: str) -> None:
    """No entry point may hardcode an accelerator as its --device default.

    argparse typing "cuda" for a user who typed nothing is not a request, and
    resolve_device is obliged to treat it as one.
    """
    hardcoded: list[str] = []
    for value in _device_defaults(script):
        if isinstance(value, ast.Constant) and value.value in {"cuda", "mps"}:
            hardcoded.append(value.value)
        else:
            assert isinstance(value, ast.Call), (
                f"{script}: --device default is neither a literal nor a call; "
                "check by hand that it asks the machine."
            )
            assert value.func.id == "default_device"
    assert not hardcoded, f"{script} hardcodes --device default={hardcoded}"


@pytest.mark.parametrize(
    "script", SHARED_RESOLVER_SCRIPTS + FORMER_REEXPORT_IMPORTERS
)
def test_no_resolving_script_can_raise_on_its_own_default(script: str) -> None:
    """Every script that resolves --device survives being run with no flag typed.

    docs/troubleshooting.md tells the operator whose CUDA box just broke that these
    sixteen cannot produce the error unless they asked for an accelerator. That holds
    only while none of their defaults names one: the seven that predate `default_device`
    default to "cpu" or "auto", the rest call it.
    """
    for value in _device_defaults(script):
        assert not (
            isinstance(value, ast.Constant) and value.value in {"cuda", "mps"}
        ), (
            f"{script} resolves --device but defaults to {value.value!r}, so a bare "
            "invocation on a box without it now raises. Use default_device()."
        )
