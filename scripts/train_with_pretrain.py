#!/usr/bin/env python3
"""Run the maintained TGNN training CLI with Stage 0 pretraining enabled."""

from __future__ import annotations

from pathlib import Path
import runpy
import sys


_SCRIPT_PATH = Path(__file__).resolve()
_TRAIN_SCRIPT = _SCRIPT_PATH.with_name("train.py")

if str(_SCRIPT_PATH.parent) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_PATH.parent))

argv = sys.argv[1:]
if "--pretrain" not in argv and "--pretrain-checkpoint" not in argv:
    sys.argv.insert(1, "--pretrain")
if "--run-descriptor-probe" not in argv:
    sys.argv.insert(1, "--run-descriptor-probe")

if __name__ == "__main__":
    runpy.run_path(str(_TRAIN_SCRIPT), run_name="__main__")
