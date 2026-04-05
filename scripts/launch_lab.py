#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "tools" / "experiment_lab" / "app.py"
GUI_REQUIRED_MODULES = (
    "streamlit",
    "plotly",
    "streamlit_flow",
    "streamlit_sortables",
    "streamlit_ketcher",
)


def candidate_python_paths() -> list[Path]:
    env_override = os.environ.get("TGNN_SOLV_LAB_PYTHON")
    candidates = [
        Path(env_override).expanduser() if env_override else None,
        REPO_ROOT / ".venv" / "bin" / "python",
        Path.home() / "anaconda3" / "envs" / "tgnn-solv" / "bin" / "python",
        Path.home() / "miniforge3" / "envs" / "tgnn-solv" / "bin" / "python",
        Path.home() / "mambaforge" / "envs" / "tgnn-solv" / "bin" / "python",
        Path(sys.executable),
    ]
    seen: set[str] = set()
    resolved: list[Path] = []
    for candidate in candidates:
        if candidate is None:
            continue
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(candidate)
    return resolved


def python_supports_gui_stack(python_path: Path) -> bool:
    if not python_path.exists():
        return False
    probe = (
        "import importlib.util, json; "
        f"mods={list(GUI_REQUIRED_MODULES)!r}; "
        "missing=[name for name in mods if importlib.util.find_spec(name) is None]; "
        "print(json.dumps({'ok': not missing, 'missing': missing}))"
    )
    try:
        completed = subprocess.run(
            [str(python_path), "-c", probe],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return "\"ok\": true" in completed.stdout


def select_streamlit_python() -> Path:
    for candidate in candidate_python_paths():
        if python_supports_gui_stack(candidate):
            return candidate
    return Path(sys.executable)


def main() -> int:
    python_path = select_streamlit_python()
    if not python_supports_gui_stack(python_path):
        missing = ", ".join(GUI_REQUIRED_MODULES)
        raise SystemExit(
            "Could not find a Python environment with the required GUI stack "
            f"({missing}). Install it with `pip install -e '.[gui,dev]'` or set "
            "`TGNN_SOLV_LAB_PYTHON=/path/to/python`."
        )

    if python_path != Path(sys.executable):
        print(f"[launch_lab] using GUI interpreter: {python_path}", file=sys.stderr)

    command = [str(python_path), "-m", "streamlit", "run", str(APP_PATH), *sys.argv[1:]]
    env = os.environ.copy()
    env.setdefault("TGNN_SOLV_LAB_PYTHON", str(python_path))
    try:
        return subprocess.call(command, cwd=str(REPO_ROOT), env=env)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
