from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_state(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, state: dict[str, object]) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=True), encoding="utf-8")


def update_state(path: Path, **patch: object) -> dict[str, object]:
    state = read_state(path)
    state.update(patch)
    write_state(path, state)
    return state


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python job_runner.py <state.json>")

    state_path = Path(sys.argv[1]).resolve()
    state = update_state(
        state_path,
        status="running",
        runner_pid=os.getpid(),
        started_at=utc_now(),
    )

    command = state["command"]
    if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
        update_state(
            state_path,
            status="failed",
            returncode=2,
            finished_at=utc_now(),
            error="State file does not contain a valid command list.",
        )
        return 2

    cwd = Path(str(state.get("cwd") or Path.cwd())).resolve()
    log_path = Path(str(state["log_path"])).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    with log_path.open("a", encoding="utf-8") as log_handle:
        log_handle.write(f"[{utc_now()}] Starting job\n")
        log_handle.write(f"[cwd] {cwd}\n")
        log_handle.write(f"[cmd] {shlex.join(command)}\n\n")
        log_handle.flush()

        try:
            proc = subprocess.Popen(
                command,
                cwd=str(cwd),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                start_new_session=True,
            )
            update_state(state_path, target_pid=proc.pid)
            returncode = proc.wait()
        except Exception as exc:  # pragma: no cover - defensive path
            log_handle.write("\n[runner-error]\n")
            log_handle.write("".join(traceback.format_exception(exc)))
            log_handle.flush()
            update_state(
                state_path,
                status="failed",
                returncode=1,
                finished_at=utc_now(),
                error=str(exc),
            )
            return 1

        log_handle.write(f"\n[{utc_now()}] Job finished with return code {returncode}\n")
        log_handle.flush()

    update_state(
        state_path,
        status="completed" if returncode == 0 else "failed",
        returncode=returncode,
        finished_at=utc_now(),
    )
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
