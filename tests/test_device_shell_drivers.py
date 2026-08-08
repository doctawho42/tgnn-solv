"""The shell half of the device rule, which `tests/test_device.py` cannot see.

That file guards the Python entry points: no `--device` default may name an accelerator,
because argparse typing "cuda" for a user who typed nothing is a wish about the hardware
and `resolve_device` is obliged to treat it as a demand. Six `scripts/experiments/*.sh`
drivers said the same wish in shell -- `DEVICE="${DEVICE:-cuda}"`, then
`--device "${DEVICE}"` to every child -- so on a MacBook with nothing typed they died at
the first arm, one of them being `run_e5_sigma_grounding.sh`, the driver behind
`results/e5_sigma_grounding/THREE_SEED_SUMMARY.md`.

The drivers are discovered by glob rather than listed. A hand-maintained list is the
shape of the bug this whole area exists to fix: twelve copies of one function drifted
into three behaviours because nothing enumerated them. `test_the_discovery_finds_the_six`
is the null arm -- a glob that matches nothing would leave every assertion below green.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DRIVER_DIR = REPO_ROOT / "scripts" / "experiments"

# The six that opened `DEVICE="${DEVICE:-cuda}"`. Named here as the null arm's expected
# floor, not as the list under test: the assertions run over whatever the glob finds.
DRIVERS_THAT_WISHED = frozenset(
    {
        "run_corrected_split_reproduction.sh",
        "run_data_efficiency.sh",
        "run_e2_crystal_grounding.sh",
        "run_e3_temperature_extrapolation.sh",
        "run_e4_ablations.sh",
        "run_e5_sigma_grounding.sh",
    }
)

# `DEVICE="${DEVICE:-...}"` -- the default a driver applies when the caller typed nothing.
_DEVICE_DEFAULT = re.compile(r'^DEVICE="\$\{DEVICE:-([^}]*)\}"', re.MULTILINE)
# The unguarded pass-through. Harmless while the default is a device name; a syntax error
# waiting to happen once the default is empty, since it expands to `--device ""`.
_BARE_PASSTHROUGH = '--device "${DEVICE}"'


def _drivers_passing_a_device() -> list[str]:
    """Every `scripts/experiments/*.sh` that hands a `--device` to a child."""
    return sorted(
        path.name
        for path in DRIVER_DIR.glob("*.sh")
        if "--device" in path.read_text()
    )


DRIVERS = _drivers_passing_a_device()


def test_the_discovery_finds_the_six() -> None:
    """Without this, an empty glob would make every parametrised test below vacuous."""
    assert DRIVERS_THAT_WISHED.issubset(DRIVERS), (
        f"glob over {DRIVER_DIR} found {DRIVERS}, which is missing "
        f"{sorted(DRIVERS_THAT_WISHED.difference(DRIVERS))}"
    )


@pytest.mark.parametrize("driver", DRIVERS)
def test_no_driver_defaults_device_to_an_accelerator(driver: str) -> None:
    """`DEVICE="${DEVICE:-cuda}"` is the same wish as `default="cuda"`, in shell.

    A driver may still demand CUDA -- that is what typing `DEVICE=cuda` in front of it
    means, and on a GPU box it is the right thing, because it is what turns a broken
    driver into an error instead of a ten-hour CPU run. It may not demand it on the
    caller's behalf.
    """
    source = (DRIVER_DIR / driver).read_text()
    for default in _DEVICE_DEFAULT.findall(source):
        assert not default.strip().lower().startswith(("cuda", "mps")), (
            f"{driver} defaults DEVICE to {default!r}, so a bare invocation on a box "
            "without it raises out of the first child. Leave it empty and pass "
            "--device only when the caller sets it."
        )


@pytest.mark.parametrize("driver", DRIVERS)
def test_an_empty_device_is_never_passed_as_a_flag(driver: str) -> None:
    """The other half: with no default, the flag has to disappear, not go out empty.

    `--device ""` reaches `torch.device("")`, which raises where nothing about the
    message mentions the device the caller never chose.
    """
    source = (DRIVER_DIR / driver).read_text()
    defaults = [d.strip() for d in _DEVICE_DEFAULT.findall(source)]
    if not defaults or any(defaults):
        return  # this driver always has a device string to pass
    # The one line allowed to spell it is the guard that only runs when DEVICE is set.
    unguarded = [
        line.strip()
        for line in source.splitlines()
        if _BARE_PASSTHROUGH in line and "DEV_ARGS=(" not in line
    ]
    assert not unguarded, (
        f"{driver} leaves DEVICE empty but still passes {_BARE_PASSTHROUGH} at "
        f"{unguarded}; expand the guarded array instead."
    )
    assert "DEV_ARGS" in source, f"{driver} leaves DEVICE empty and never builds DEV_ARGS"
