#!/usr/bin/env python
"""Drive run_e5_sigma_grounding.sh one (seed, arm) at a time under a wall-clock deadline.

WHY A WRAPPER AND NOT THE SHELL SCRIPT DIRECTLY
------------------------------------------------
The shell script already does everything that matters -- it owns the exact training and export
commands for every arm, it SKIPS an arm whose predictions exist, and it RESUMES one whose training
checkpoint does.  What it has no notion of is a session that ends at a fixed hour.  Kaggle stops a
GPU session at its limit and takes the container with it; an arm interrupted mid-epoch is fine
(--checkpoint-every leaves a resumable file) but an arm interrupted mid-EXPORT leaves a truncated
predictions.csv that the next session will treat as finished.  This project has already shipped one
truncated per-row file and had to recover it.

So this wrapper adds exactly two things and duplicates nothing: a deadline checked between arms,
and a completeness check on each predictions file before it is allowed to count as done.

USAGE ON KAGGLE
---------------
    python code/scripts/kaggle/run_arms.py \
        --arms grounded_a grounded_a_truetrain channel_swap --seeds 42 43 44 45 46 \
        --hours 11.0 --device cuda \
        --out-dir /kaggle/working/out/results --ckpt-dir /kaggle/working/out/checkpoints

Run it again in the next session with the previous session's output mounted and the same command:
finished arms are skipped, partial ones resume.

THE ORDER IS SEED-MAJOR ON PURPOSE.  All arms of one seed finish before the next seed starts, so a
run that is cut off yields COMPLETE SEEDS rather than a ragged matrix -- five arms at seed 42 is a
result, one arm at each of five seeds is not.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

#: An export that died mid-write leaves a short file.  The test split has this many rows, and a
#: predictions file with fewer has not finished -- it is deleted rather than trusted.
EXPECTED_ROWS_MIN = 8000


def rows(path: Path) -> int:
    try:
        with path.open("rb") as fh:
            return sum(1 for _ in fh) - 1
    except OSError:
        return -1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, default=Path.cwd(),
                    help="repo root (holds scripts/, src/, configs/)")
    ap.add_argument("--arms", nargs="+", required=True)
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--hours", type=float, default=11.0,
                    help="stop starting new arms after this many hours")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--allow-cpu", action="store_true",
                    help="permit the CPU fallback: skips the preflight below AND exports "
                         "TGNN_ALLOW_CPU_FALLBACK=1 to every child, which is what the flag "
                         "has to do -- skipping only this script's probe leaves the children "
                         "raising in resolve_device() and the flag guarantees the crash it "
                         "exists to prevent.")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--ckpt-dir", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, default=Path("notebooks/data/processed"))
    ap.add_argument("--sigma-dir", type=Path,
                    default=Path("notebooks/data/processed_sigma_aux_stream_rebuilt"))
    ap.add_argument("--num-workers", default="2")
    ap.add_argument("--smoke", action="store_true",
                    help="1-epoch phases and a 1-epoch warm-up: checks the WIRING on a "
                         "laptop. The metrics it produces are meaningless and must never "
                         "be reported.")
    a = ap.parse_args()

    repo = a.repo.resolve()
    deadline = time.time() + a.hours * 3600
    a.out_dir.mkdir(parents=True, exist_ok=True)
    a.ckpt_dir.mkdir(parents=True, exist_ok=True)
    progress = a.out_dir / "kaggle_progress.json"
    log: list[dict] = json.loads(progress.read_text()) if progress.exists() else []

    # A truncated export from a killed session must not read as a finished arm.
    for seed in a.seeds:
        for arm in a.arms:
            pred = a.out_dir / f"seed_{seed}" / f"{arm}_predictions.csv"
            if pred.exists() and rows(pred) < EXPECTED_ROWS_MIN:
                print(f"!! {pred} has {rows(pred)} rows, below {EXPECTED_ROWS_MIN}: "
                      f"truncated by a killed session. Deleting so it re-exports.")
                pred.unlink()

    # FAIL FAST ON A GPU THAT IS PRESENT BUT UNUSABLE.  resolve_device() asks
    # torch.cuda.is_available() and no more; this launches a kernel, which is what catches a
    # visible-but-too-old card.  The literal "cuda" default above is deliberate and this block
    # is what answers for it: 15 arms at ~25x slower is not a slow run, it is a wasted session,
    # and this project has already lost one to a silent CPU fallback.  Same probe and same
    # remedy text as scripts/cloud/kaggle_run.py.
    if a.device.startswith("cuda") and not a.allow_cpu:
        name = err = None
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                (torch.zeros(1, device="cuda") + 1).cpu()      # actually launch a kernel
            else:
                err = "no GPU visible"
        except Exception as e:      # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:140]}"
        if err is not None:
            sys.exit(f"FATAL: GPU unusable ({err}; device={name}). CPU would be ~25x slower and "
                     "would burn the session. If this is a Tesla P100 (compute 6.0 / sm_60) the "
                     "kernel-launch error means it is too old for the installed PyTorch (needs "
                     "sm_70+): set Kaggle Settings -> Accelerator -> GPU T4 x2 (sm_75) and "
                     "re-Add Data. Use --allow-cpu only to force CPU.")
        print(f"[gpu] CUDA OK: {name}", flush=True)

    env = dict(os.environ)
    env.update({
        "PY": sys.executable, "DEVICE": a.device,
        "DATA_DIR": str(a.data_dir), "SIGMA_DIR": str(a.sigma_dir),
        "OUT_DIR": str(a.out_dir), "CKPT_DIR": str(a.ckpt_dir),
        "NUM_WORKERS": a.num_workers, "KMP_DUPLICATE_LIB_OK": "TRUE",
        "PYTHONPATH": f"{repo / 'src'}:{env.get('PYTHONPATH', '')}",
    })
    if a.allow_cpu:
        env["TGNN_ALLOW_CPU_FALLBACK"] = "1"
        print("[gpu] --allow-cpu: preflight skipped and TGNN_ALLOW_CPU_FALLBACK=1 exported to "
              "every child. Expect ~25x slower.", flush=True)
    if a.smoke:
        env.update({"WARMUP_EPOCHS": "1", "SIGMA_STEPS": "2", "DIRECT_EPOCHS": "1",
                    "EXTRA_TRAIN_ARGS": "--epochs-phase1 1 --epochs-phase2 1 --epochs-phase3 1"})
        print("!! SMOKE MODE: 1-epoch phases. This checks the wiring and nothing else; the "
              "numbers it produces are not results.")

    for seed in a.seeds:                       # seed-major: complete seeds, not a ragged matrix
        for arm in a.arms:
            pred = a.out_dir / f"seed_{seed}" / f"{arm}_predictions.csv"
            if pred.exists() and rows(pred) >= EXPECTED_ROWS_MIN:
                print(f"== seed {seed} arm {arm}: already done ({rows(pred)} rows)")
                continue
            left = deadline - time.time()
            if left <= 0:
                print(f"\n== deadline reached; stopping before seed {seed} arm {arm}.")
                print("   Save /kaggle/working/out as a dataset and run the same command again.")
                break
            print(f"\n{'=' * 70}\n== seed {seed} arm {arm}  ({left / 3600:.2f} h left)\n{'=' * 70}",
                  flush=True)
            t0 = time.time()
            r = subprocess.run(["bash", "scripts/experiments/run_e5_sigma_grounding.sh"],
                               cwd=repo, env={**env, "SEEDS": str(seed), "ARMS": arm})
            entry = {"seed": seed, "arm": arm, "returncode": r.returncode,
                     "hours": round((time.time() - t0) / 3600, 3),
                     "rows": rows(pred), "ok": r.returncode == 0 and rows(pred) >= EXPECTED_ROWS_MIN}
            log.append(entry)
            progress.write_text(json.dumps(log, indent=2) + "\n")
            print(f"-- {entry}")
            if not entry["ok"]:
                print("!! this arm did not finish cleanly; it will be retried next session")
        else:
            continue
        break

    done = sum(1 for e in log if e["ok"])
    print(f"\n{'=' * 70}\n{done} arms finished across all sessions; progress in {progress}")
    for seed in a.seeds:
        have = [arm for arm in a.arms
                if (a.out_dir / f"seed_{seed}" / f"{arm}_predictions.csv").exists()
                and rows(a.out_dir / f"seed_{seed}" / f"{arm}_predictions.csv") >= EXPECTED_ROWS_MIN]
        print(f"  seed {seed}: {len(have)}/{len(a.arms)}  {' '.join(have)}")


if __name__ == "__main__":
    main()
