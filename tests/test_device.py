"""Tests for the shared device resolver.

The behaviour under test is the one `a569307` introduced in `scripts/train.py` and this
module now holds for all twelve scripts that carried a copy: an accelerator requested by
name and not available is a hard error, not a WARNING line followed by a ten-hour CPU
run. `a569307` itself changed only `scripts/train.py`; the other eleven copies stayed
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
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from tgnn_solv import device as device_module
from tgnn_solv.device import default_device, resolve_device


REPO_ROOT = Path(__file__).resolve().parents[1]

# ======================================================================================
# The scan, and the rules it uses.
#
# Three hand-written tuples of script paths stood here: the scripts that had carried a
# copy of `resolve_device`, the ones that had reached a copy through another script's
# namespace, and the ones whose `--device` default is read off the machine. A list of
# the files that must not have the bug, maintained by hand, is the same shape as the bug
# it guards -- a copy of the truth that goes stale in silence. This one went stale the
# same day it was written. `run_compensation_surrogate.py`, `run_encoder_linear_probe.py`
# and `run_uncertainty_calibration.py`, all in `scripts/analysis`, were given
# `resolve_device` calls by a separate repair a few hours later; all three appeared in
# none of the three tuples, so all three were guarded by nothing. Nobody had done
# anything wrong. A list cannot know about work that has not happened yet, and the
# author of that work has no reason to look here.
#
# So the lists are gone and what follows walks the tree on each run. What is written
# down in their place is the rules, because the rule is the part that has to be
# reproducible: two AST scans of this tree written a day apart disagreed on how many
# scripts own a `--device` flag (52/19/33 against 47/16/31) and neither had said what
# counts. Nothing below asserts or prints a total. A total is the thing that goes stale;
# the rule is not, and the tree is read fresh on every run.
#
# DOMAIN. Every `*.py` path git knows about -- tracked, plus untracked files that are
# not ignored -- read from the working tree. Two properties, and both are needed. A
# script is covered from the moment it is written, before it is staged, let alone
# committed. And the answer does not depend on what is lying around this particular
# machine: ignored paths are excluded, so a `results/` directory full of one operator's
# old snapshots cannot redden a suite that is green in a fresh clone. (There is one such
# file here today -- an untracked `results/diagnostic_experiments/run_summary.py` that
# both reaches `resolve_device` through `run_full_budget_experiment`'s namespace and
# defaults `--device` to a bare "mps". It is a local artifact, not part of the
# repository, and a guard that failed on it would be reporting on this laptop rather
# than on the project.) Without git, the fallback is a walk of every `*.py` outside
# `_SKIP_DIRS`, which can only ever scan more files than git would, never fewer.
#
# Only files whose raw text contains one of `_TRIGGERS` are parsed, which is safe
# because a file containing neither substring cannot satisfy either rule; a triggered
# file that does not parse is a failure rather than a skip, since a file that cannot be
# read escapes every rule below.
#
# RULE 1, "declares --device": a call to `add_argument` -- any receiver -- carrying the
# string `"--device"` among its positional arguments. Narrower than "the text mentions
# --device" on purpose. `src/tgnn_solv/reproduction.py` and `tools/experiment_lab/app.py`
# pass `"--device"` positionally to argv builders that hand it to a child process, which
# is use of somebody else's flag rather than declaration of one's own; a scan that
# counts those and a scan that does not will differ by two files and a few dozen call
# sites, which is one of the two ways the earlier scans disagreed.
#
# RULE 2, "resolves --device": a call whose callee name is `resolve_device` or
# `_resolve_device`, bare or dotted. The private spelling is included because it is what
# the `scripts/analysis` copies were called.
#
# RULE 3, "an accelerator literal": a string default that `resolve_device` would read as
# a demand for an accelerator -- stripped, lower-cased, starting with `cuda` or `mps`.
# Mirroring the resolver instead of testing against a two-element set is what makes
# `default="cuda:0"` a failure too; the tuple this replaces would have passed it.
# ======================================================================================

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
_TRIGGERS = ("--device", "resolve_device")
_RESOLVER_NAMES = frozenset({"resolve_device", "_resolve_device"})
DEVICE_MODULE = "tgnn_solv.device"
DEVICE_MODULE_PATH = "src/tgnn_solv/device.py"

# The two entry points allowed to hardcode an accelerator as their `--device` default,
# with the argument for each. This list is asserted in *both* directions
# (`test_the_accelerator_exemptions_are_exactly_the_files_that_need_them`): a third
# script that hardcodes one fails the suite instead of joining a list nobody re-reads,
# and an entry that stops needing its exemption fails too, because a line that exempts
# nothing still reads as a standing permission.
LITERAL_ACCELERATOR_DEFAULT_EXEMPTIONS = {
    "scripts/cloud/kaggle_run.py": (
        "A Kaggle session that quietly runs on CPU is a wasted session, and this script "
        "answers for the literal itself: a kernel-launch preflight that catches a "
        "visible-but-unusable card, and --allow-cpu, which exports the escape into "
        "every child it spawns."
    ),
    "scripts/kaggle/run_arms.py": (
        "Same argument as kaggle_run.py and the same probe: 15 training arms at ~25x slower "
        "is a burned 12-hour session, not a slow one, and this project has already lost one "
        "to a silent CPU fallback. The script answers for the literal with a kernel-launch "
        "preflight -- not torch.cuda.is_available() alone, which passes on a card too old to "
        "run a kernel -- and with --allow-cpu, which it exports into every child."
    ),
    "scripts/experiments/run_pka_trained_comparison.py": (
        "Never reaches resolve_device, and says so in a comment at its own device line: "
        "the arm trains small per-molecule MLPs in seconds, so a CPU fallback costs a "
        "coffee rather than the ten hours this guard exists for."
    ),
}


def _dotted(node: ast.expr) -> str | None:
    """`a.b.c` as "a.b.c"; None for a callee this scan cannot name (a call, a subscript).

    Returning None rather than reaching for `.id` is deliberate: the check this feeds
    used to read `value.func.id`, which raises AttributeError on any dotted callee --
    `tgnn_solv.device.default_device()` would have crashed the test rather than passing
    it, and crashed with a traceback rather than a verdict.
    """
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _is_accelerator_literal(value: object) -> bool:
    """RULE 3: would `resolve_device` read this default as a demand for an accelerator?"""
    return isinstance(value, str) and value.strip().lower().startswith(("cuda", "mps"))


def _python_files() -> list[Path]:
    """The DOMAIN above: what git carries, else every `*.py` outside `_SKIP_DIRS`."""
    try:
        listing = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.split("\n")
    except (OSError, subprocess.SubprocessError):
        return [
            path
            for path in sorted(REPO_ROOT.rglob("*.py"))
            if not any(
                part in _SKIP_DIRS for part in path.relative_to(REPO_ROOT).parts
            )
        ]
    # A tracked path that has been deleted in the working tree is still listed.
    return sorted({REPO_ROOT / line for line in listing if line.strip()})


def _scan_tree() -> SimpleNamespace:
    unparseable: list[str] = []
    defines: list[str] = []
    declares: list[str] = []
    resolves: list[str] = []
    defaults: dict[str, list[ast.expr]] = {}
    resolver_calls: dict[str, set[str]] = {}
    resolver_imports: dict[str, set[str | None]] = {}

    for path in _python_files():
        if not path.is_file():
            continue
        relative = path.relative_to(REPO_ROOT)
        source = path.read_text(encoding="utf-8", errors="replace")
        if not any(trigger in source for trigger in _TRIGGERS):
            continue
        script = relative.as_posix()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            unparseable.append(script)
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in _RESOLVER_NAMES
            ):
                defines.append(script)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in _RESOLVER_NAMES:
                        resolver_imports.setdefault(script, set()).add(node.module)
            elif isinstance(node, ast.Call):
                name = _dotted(node.func)
                tail = name.rpartition(".")[2] if name else ""
                if tail in _RESOLVER_NAMES:
                    resolves.append(script)
                    resolver_calls.setdefault(script, set()).add(name or tail)
                elif tail == "add_argument" and any(
                    isinstance(arg, ast.Constant) and arg.value == "--device"
                    for arg in node.args
                ):
                    declares.append(script)
                    defaults.setdefault(script, []).extend(
                        keyword.value
                        for keyword in node.keywords
                        if keyword.arg == "default"
                    )

    return SimpleNamespace(
        unparseable=tuple(sorted(set(unparseable))),
        defines=tuple(sorted(set(defines))),
        declares=tuple(sorted(set(declares))),
        resolves=tuple(sorted(set(resolves))),
        defaults=defaults,
        resolver_calls=resolver_calls,
        resolver_imports=resolver_imports,
    )


_SCAN = _scan_tree()

# Files checked one by one, so a failure names the file rather than a set difference.
# The exempted two are dropped here and pinned by their own two-way test instead.
GUARDED_DEVICE_FLAG_FILES = tuple(
    script
    for script in _SCAN.declares
    if script not in LITERAL_ACCELERATOR_DEFAULT_EXEMPTIONS
)

# The `scripts/experiments/*.sh` drivers say the same thing in the other language --
# `DEVICE="${DEVICE:-cuda}"`, then `--device "${DEVICE}"` to every child -- and no AST
# scan of Python will ever see them. They are guarded in tests/test_device_shell_drivers.py,
# by a glob over that directory rather than by a list.


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


def _fake_bus(root: Path, devices: dict[str, tuple[str, str | None]]) -> str:
    """Write a sysfs-shaped PCI tree: a directory per function, holding vendor and class.

    Slot names and ids are the real ones. `0x10de` is NVIDIA; `0x030200` is the 3D
    controller class a V100 or an A100 presents, `0x030000` the VGA class of a
    workstation card, `0x040300` the HDMI-audio function that ships on the same card and
    carries the same vendor id.
    """
    for slot, (vendor, pci_class) in devices.items():
        entry = root / slot
        entry.mkdir(parents=True)
        (entry / "vendor").write_text(f"{vendor}\n")
        if pci_class is not None:
            (entry / "class").write_text(f"{pci_class}\n")
    return str(root)


def _untag(err: str) -> str:
    """The announcement as one string: rules dropped, tags stripped, lines rejoined.

    Every line carries the tag so the block survives a log, which means no sentence in
    it is contiguous in the raw stream. Assertions about *what it says* go through here;
    assertions about the shape it says it in read the raw lines.
    """
    return " ".join(
        line[len("TGNN-DEVICE") :].strip()
        for line in err.splitlines()
        if line.startswith("TGNN-DEVICE")
    )


def _gpu_box(monkeypatch: pytest.MonkeyPatch, root: str) -> None:
    """A box with no usable accelerator, whose PCI bus is `root`, having said nothing yet."""
    monkeypatch.delenv("TGNN_ALLOW_CPU_FALLBACK", raising=False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    monkeypatch.setattr(device_module, "_PCI_DEVICE_ROOT", root)
    monkeypatch.setattr(device_module, "_CPU_DEFAULT_ANNOUNCED", False)


def test_the_bus_scan_counts_nvidia_display_devices_only(tmp_path: Path) -> None:
    """What is on the bus is a different question from what the driver can reach.

    `torch.cuda.is_available()` answered False on the gate box on 2026-08-08 and the
    V100 was still bolted to it. sysfs is the cheapest place that distinction is legible.
    """
    root = _fake_bus(
        tmp_path / "bus",
        {
            "0000:00:04.0": ("0x10de", "0x030200"),  # the V100
            "0000:00:04.1": ("0x10de", "0x040300"),  # its own audio function
            "0000:00:05.0": ("0x10de", "0x0c0330"),  # its own USB-C controller
            "0000:00:02.0": ("0x8086", "0x030000"),  # an Intel iGPU
            "0000:00:1f.6": ("0x8086", "0x020000"),  # a NIC
        },
    )

    assert device_module.nvidia_gpus_on_the_bus(root) == 1


def test_the_bus_scan_survives_a_bus_it_cannot_read(tmp_path: Path) -> None:
    """A guess about the hardware must never be able to break device selection.

    Every unreadable case fails closed to "not counted" except a missing class, which
    is counted: the vendor already matched, and this detector's failure mode should be a
    banner nobody needed rather than the silence it exists to end.
    """
    assert device_module.nvidia_gpus_on_the_bus(str(tmp_path / "no-such-bus")) == 0

    root = _fake_bus(
        tmp_path / "bus",
        {
            "0000:00:04.0": ("0x10de", None),  # class unreadable -> counted
            "0000:00:06.0": ("0x10DE", "0x030200"),  # sysfs is lower case; this is not
        },
    )
    (Path(root) / "0000:00:07.0").mkdir()  # a device with no attributes at all
    (Path(root) / "0000:00:08.0").write_text("not a directory\n")

    assert device_module.nvidia_gpus_on_the_bus(root) == 2


def test_a_cpu_default_says_nothing_where_there_is_no_gpu_to_lose(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The MacBook case. Silence here is what keeps the shout worth reading elsewhere.

    A laptop that is told about its own lack of CUDA on every smoke run learns to skip
    the line, and then skips it on the box where it mattered.
    """
    _gpu_box(monkeypatch, _fake_bus(tmp_path / "bus", {}))

    assert default_device() == "cpu"
    assert default_device(prefer_mps=True) == "cpu"

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_a_cpu_default_shouts_on_a_box_that_owns_an_nvidia_card(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The gate-box case: the signal that was there on 2026-08-08 and then was not.

    `a569307` and the consolidation together took the old WARNING line away from the
    no-flag path -- `default_device` picked CPU silently, the drivers forwarded
    `--device cpu`, and `resolve_device("cpu")` is a legitimate request -- so this path
    had less signal than on the day the failure happened.
    """
    _gpu_box(
        monkeypatch,
        _fake_bus(tmp_path / "bus", {"0000:00:04.0": ("0x10de", "0x030200")}),
    )

    assert default_device() == "cpu"

    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.strip().splitlines()
    # Every line tagged, so one grep finds the block in a 300 KB log and so it stays
    # legible interleaved with tqdm, which writes to this same stream.
    tagged = [line for line in lines if line.startswith("TGNN-DEVICE")]
    assert len(tagged) >= 4
    assert lines[0].startswith("=") and lines[-1].startswith("=")
    assert len(tagged) == len(lines) - 2
    body = _untag(captured.err)
    assert "1 NVIDIA display device is on its PCI bus" in body
    assert '"cpu"' in body
    # Both ways out: what to look at, and how to say CPU was what was meant.
    assert "nvidia-smi" in body
    assert "TGNN_ALLOW_CPU_FALLBACK=1" in body


def test_the_shout_separates_a_dead_driver_from_a_cpu_only_torch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Two causes reach the same silence, and `torch.version.cuda` is free to read."""
    bus = _fake_bus(tmp_path / "bus", {"0000:00:04.0": ("0x10de", "0x030200")})

    _gpu_box(monkeypatch, bus)
    monkeypatch.setattr(torch.version, "cuda", "12.1")
    default_device()
    body = _untag(capsys.readouterr().err)
    assert "built against CUDA 12.1" in body
    assert "modinfo nvidia" in body

    _gpu_box(monkeypatch, bus)
    monkeypatch.setattr(torch.version, "cuda", None)
    default_device()
    body = _untag(capsys.readouterr().err)
    assert "no CUDA in it at all" in body
    assert "reinstall from the CUDA wheel index" in body


def test_the_shout_happens_once_per_process(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Loud once. Repeated per parser it would be noise, and noise is what it fixes."""
    _gpu_box(
        monkeypatch,
        _fake_bus(tmp_path / "bus", {"0000:00:04.0": ("0x10de", "0x030200")}),
    )

    default_device()
    assert capsys.readouterr().err != ""

    default_device()
    default_device(prefer_mps=True)
    assert capsys.readouterr().err == ""


def test_allow_cpu_fallback_silences_the_shout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The one escape, and it is the knob that already means "CPU is what I meant".

    `--device cpu` cannot be the escape: an argparse default is computed while the
    parser is built, before anyone has parsed the flag that would have silenced it.
    """
    _gpu_box(
        monkeypatch,
        _fake_bus(tmp_path / "bus", {"0000:00:04.0": ("0x10de", "0x030200")}),
    )
    monkeypatch.setenv("TGNN_ALLOW_CPU_FALLBACK", "1")

    assert default_device() == "cpu"
    assert capsys.readouterr().err == ""


def test_auto_shouts_through_the_same_reading_of_the_machine(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """`resolve_device("auto")` asks `default_device`, so it inherits the announcement.

    "auto" resolving to CPU on a box with a V100 in it is the same event as a bare
    invocation resolving to CPU there, and four analysis entry points default to it.
    """
    _gpu_box(
        monkeypatch,
        _fake_bus(tmp_path / "bus", {"0000:00:04.0": ("0x10de", "0x030200")}),
    )

    assert resolve_device("auto") == torch.device("cpu")
    assert "NVIDIA display device" in _untag(capsys.readouterr().err)


def test_an_accelerator_default_neither_shouts_nor_reads_the_bus(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The fast path pays nothing: the bus is only read once CPU has been decided."""
    def _explode(root: str | None = None) -> int:
        raise AssertionError("the PCI bus was read on a path that found an accelerator")

    monkeypatch.setattr(device_module, "_CPU_DEFAULT_ANNOUNCED", False)
    monkeypatch.setattr(device_module, "nvidia_gpus_on_the_bus", _explode)

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert default_device() == "cuda"

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert default_device(prefer_mps=True) == "mps"

    assert capsys.readouterr().err == ""


def test_reading_the_machine_imports_nothing_heavy() -> None:
    """An argparse default runs before the program does, and may not cost anything.

    Which rules out every richer way of asking whether the box has a GPU: `nvidia-smi`
    through `subprocess`, `libcuda` through `ctypes`, `pynvml`. It also rules out the
    lazy import inside the function that hides such a cost from this assertion.
    """
    tree = ast.parse((REPO_ROOT / DEVICE_MODULE_PATH).read_text())

    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert imported <= {"__future__", "os", "sys", "textwrap", "torch"}, (
        f"{DEVICE_MODULE_PATH} imports {sorted(imported)}; widening this is a decision "
        "about what an argparse default may spend, not a detail. os, sys and textwrap "
        "are stdlib and already loaded by the time torch is."
    )

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            assert not isinstance(inner, (ast.Import, ast.ImportFrom)), (
                f"{node.name}() imports at call time, which is where a heavy "
                "dependency would hide from the check above."
            )


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


def test_the_scan_can_read_every_file_it_is_responsible_for() -> None:
    """A file the scan cannot parse is outside every rule below, silently."""
    assert _SCAN.unparseable == (), (
        f"{list(_SCAN.unparseable)} mention --device or resolve_device and do not "
        "parse, so no rule in this module applies to them."
    )


def test_the_scan_finds_the_files_it_is_meant_to_be_watching() -> None:
    """A scan that matches nothing passes every rule it has.

    RULE 1 and RULE 2 are written narrowly, and a narrow rule that stops matching --
    argparse replaced by click, `add_argument` reached through a helper -- would empty
    the parametrised guards below and turn the whole section green. The anchors are the
    load-bearing entry points: the two training arms, the exporter the experiment
    drivers call, and the control arm's diagnostics. No count is asserted, only that
    the rules still see the things they were written to see.
    """
    assert {"scripts/train.py", "scripts/train_directgnn.py"} <= set(_SCAN.resolves)
    assert {
        "scripts/train.py",
        "scripts/train_directgnn.py",
        "scripts/analysis/export_checkpoint_predictions.py",
        "scripts/evaluation/run_directgnn_error_structure_diagnostics.py",
    } <= set(_SCAN.declares)


def test_the_resolver_is_defined_in_exactly_one_place() -> None:
    """Guard against the copy coming back, anywhere in the tree.

    One lenient copy cost the gate box ten hours on 2026-08-08, and the reason fixing
    that one in `a569307` was not enough is that eleven others existed to be found by
    hand. This is the assertion that no longer has to know their names.
    """
    assert _SCAN.defines == (DEVICE_MODULE_PATH,), (
        f"resolve_device is defined in {list(_SCAN.defines)}; it belongs in "
        f"{DEVICE_MODULE_PATH} alone. A second definition is how twelve of them "
        "accumulated, each free to answer 'you named an accelerator this box does not "
        "have' differently."
    )


@pytest.mark.parametrize("script", _SCAN.resolves)
def test_every_resolver_call_comes_from_the_module(script: str) -> None:
    """RULE 2's files must take `resolve_device` from `tgnn_solv.device` and nowhere else.

    Four scripts used to reach it through another script's module namespace -- three
    through `run_full_budget_experiment`, one through `validate_physics` -- where it
    resolves only because that host's own `from tgnn_solv.device import ...` re-binds
    the name. An unused-import sweep over the host breaks those callers with an
    ImportError while the rest of this file stays green. All four were repaired before
    this rule existed, so what it protects against is the next one, which is why it runs
    over whatever the scan finds rather than over their four names.
    """
    for name in sorted(_SCAN.resolver_calls[script]):
        prefix, _, tail = name.rpartition(".")
        if prefix:
            assert prefix == DEVICE_MODULE, (
                f"{script} calls {name}(); the resolver lives at {DEVICE_MODULE} and a "
                "call through any other module is either a copy or a re-export."
            )
            continue
        assert tail == "resolve_device", (
            f"{script} calls {tail}(), the private spelling the scripts/analysis copies "
            f"used. Import resolve_device from {DEVICE_MODULE}."
        )
        sources = _SCAN.resolver_imports.get(script, set())
        assert sources == {DEVICE_MODULE}, (
            f"{script} calls resolve_device but imports it from "
            f"{sorted(str(source) for source in sources)} rather than exactly "
            f"[{DEVICE_MODULE!r}]. Taking it out of another script's namespace means an "
            "unused-import sweep over that script breaks this one with an ImportError, "
            "and leaves this suite green."
        )


@pytest.mark.parametrize("script", GUARDED_DEVICE_FLAG_FILES)
def test_no_device_default_is_a_bare_accelerator(script: str) -> None:
    """RULE 1's files must not hardcode an accelerator as their `--device` default.

    argparse typing "cuda" for a user who typed nothing is not a request, and
    `resolve_device` is obliged to treat it as one. The rule covers every declaring
    file, not only the ones that resolve in-process: a default is handed to child
    processes and read by operators, and `--device cuda` typed by a script is the same
    wish about the hardware wherever it is eventually honoured.
    """
    for value in _SCAN.defaults[script]:
        if isinstance(value, ast.Constant):
            # A literal that is not an accelerator -- "cpu", "auto", None -- is a
            # statement this box can always satisfy, and passes here. The check this
            # replaces sent every non-accelerator literal down its `else` branch and
            # failed a plain `default="cpu"` with "neither a literal nor a call".
            assert not _is_accelerator_literal(value.value), (
                f"{script} declares --device with default={value.value!r}. On a box "
                "without it, a bare invocation now raises out of resolve_device. Call "
                "default_device() instead, or -- if the wish is deliberate and answered "
                "for -- add the file to LITERAL_ACCELERATOR_DEFAULT_EXEMPTIONS with the "
                "argument for it."
            )
            continue
        if isinstance(value, ast.Call):
            callee = _dotted(value.func)
            assert callee is not None and callee.rpartition(".")[2] == "default_device", (
                f"{script} builds its --device default by calling "
                f"{callee or ast.unparse(value.func)}(), not default_device(). Only "
                "default_device reads this machine; anything else is a wish with "
                "parentheses on it."
            )
            continue
        pytest.fail(
            f"{script} builds its --device default from a {type(value).__name__} "
            f"({ast.unparse(value)}), which this scan cannot read. Check by hand that "
            "it asks the machine, then teach RULE 3 to recognise the spelling -- do "
            "not leave it unreadable, because unreadable passes."
        )


def test_the_accelerator_exemptions_are_exactly_the_files_that_need_them() -> None:
    """Both directions, so neither a new exemption nor a dead one can sit unread."""
    offenders = {
        script
        for script, values in _SCAN.defaults.items()
        for value in values
        if isinstance(value, ast.Constant) and _is_accelerator_literal(value.value)
    }
    exempt = set(LITERAL_ACCELERATOR_DEFAULT_EXEMPTIONS)

    assert offenders - exempt == set(), (
        f"{sorted(offenders - exempt)} hardcode an accelerator as their --device "
        "default. If that is deliberate, say why in "
        "LITERAL_ACCELERATOR_DEFAULT_EXEMPTIONS; a third exemption should have to be "
        "argued for rather than read as intentional because it is already there."
    )
    assert exempt - offenders == set(), (
        f"{sorted(exempt - offenders)} are exempted from the accelerator-default rule "
        "and no longer need it. Delete the entries: an exemption that exempts nothing "
        "still reads as standing permission for the next person."
    )


def test_no_script_that_resolves_in_process_is_exempt() -> None:
    """The exemptions may not overlap RULE 2, which is what the docs promise operators.

    docs/troubleshooting.md tells the operator whose CUDA box just broke that invoking
    any of the resolving scripts directly, with no flag, cannot produce the error. That
    holds exactly while no resolving script's own default names an accelerator -- so the
    two files allowed to name one must be files that never reach the raise. They are:
    kaggle_run.py hands its literal to child processes and answers for it with a
    preflight, and run_pka_trained_comparison.py builds its torch.device by hand.
    """
    both = set(_SCAN.resolves) & set(LITERAL_ACCELERATOR_DEFAULT_EXEMPTIONS)
    assert not both, (
        f"{sorted(both)} call resolve_device and are exempted from the "
        "accelerator-default rule, so a bare invocation raises on a box without the "
        "accelerator -- the one failure docs/troubleshooting.md promises cannot happen."
    )


