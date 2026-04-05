#!/usr/bin/env python3
"""Compatibility wrapper for `scripts/evaluation/benchmark_adapter_model.py`."""

from __future__ import annotations

from pathlib import Path
import runpy
import sys

_SCRIPTS_ROOT = Path(__file__).resolve().parent
_GROUPED_SCRIPT = _SCRIPTS_ROOT / "evaluation" / "benchmark_adapter_model.py"

if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

if __name__ == "__main__":
    runpy.run_path(str(_GROUPED_SCRIPT), run_name="__main__")
