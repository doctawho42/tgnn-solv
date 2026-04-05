#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "tools" / "experiment_lab" / "app.py"


def main() -> int:
    try:
        import streamlit  # noqa: F401
    except ImportError as exc:  # pragma: no cover - user environment path
        raise SystemExit(
            "streamlit is not installed. Run: pip install -e '.[gui]'"
        ) from exc

    command = [sys.executable, "-m", "streamlit", "run", str(APP_PATH), *sys.argv[1:]]
    return subprocess.call(command, cwd=str(REPO_ROOT), env=os.environ.copy())


if __name__ == "__main__":
    raise SystemExit(main())
