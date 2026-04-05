#!/usr/bin/env python3
"""Structured wrapper for `scripts/train_with_pretrain.py`."""

from __future__ import annotations

from pathlib import Path
import runpy
import sys

_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
_LEGACY_SCRIPT = _SCRIPTS_ROOT / "train_with_pretrain.py"

if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

if __name__ == "__main__":
    runpy.run_path(str(_LEGACY_SCRIPT), run_name="__main__")
