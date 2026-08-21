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
import statistics
import subprocess
import sys
import time
from pathlib import Path

#: An export that died mid-write leaves a short file.  The test split has this many rows, and a
#: predictions file with fewer has not finished -- it is deleted rather than trusted.
EXPECTED_ROWS_MIN = 8000
#: How long one arm takes before any has been timed in this run, and the margin applied to the
#: median once three have. Wall-clock hours on a Kaggle T4 x2 session.
#: THE ASSUMED VALUE IS MEASURED, NOT GUESSED, and the guess it replaces was 2.0. The 2026-08-19
#: session logged Phase 2 at 1745 batches an epoch and 2.25 it/s -- 12.9 min an epoch against the
#: 30+70+10 epochs configs/cosmo_sac.yaml asks for -- and its checkpoint came back at phase 2,
#: epoch 39. Twelve hours bought 63% of one arm. At a larger batch this falls and the number here
#: should be re-measured rather than argued down.
#: WHAT AN ARM COSTS BEFORE THIS RUN HAS TIMED ONE. Sourced from the ten checkpoint manifests of
#: the deposited leak-free family (checkpoints/e5_leakfree/*.manifest.json, created_at deltas on a
#: GCP GPU): ungrounded arms land ~0.4 h apart and grounded ones 1.2-6.2 h, the larger gaps
#: including idle. Six hours is the top of that range, and a T4 is slower than the card those ran
#: on, so it is a ceiling and not an estimate.
#: THIS CONSTANT WAS 19.0 AND THAT NUMBER WAS NEVER MEASURED. It came from a lost Kaggle session
#: and survived the day the manifests refuted it, because the retraction was written down and the
#: constant was not. At 19.0 the guard refused to start any arm at all inside a 12 h session --
#: a check meant to prevent a hard kill instead prevented the work.
ARM_HOURS_ASSUMED = 6.0
#: Applied to the median of arms this run has already timed. Wider while that median rests on one
#: or two observations, because a single arm is not a distribution.
ARM_TIME_MARGIN = 1.25
ARM_TIME_MARGIN_SMALL = 1.5


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
    # THROUGHPUT, and the reason this flag exists rather than a constant.
    # The 2026-08-19 session ran twelve GPU-hours and finished no arm. Its log gives the cost
    # exactly: Phase 2 is 1745 batches an epoch at 2.25 it/s, so 12.9 min an epoch, and
    # configs/cosmo_sac.yaml asks for 30+70+10 epochs -- about nineteen hours for ONE arm, against
    # the two this wrapper assumed. 1745 x 64 = the 112k corpus, so it was running at the config
    # default batch size.
    # scripts/cloud/kaggle_run.py has known since it was written that this default starves the
    # GPU, and splices --batch-size 256 into every child for that reason; this runner never
    # carried that over. The lever is exposed here rather than hard-coded, because raising the
    # batch changes the optimisation schedule: the fifteen arms stay comparable WITH EACH OTHER at
    # any single value, but they stop being schedule-matched to the published three-seed family,
    # and that is a decision about what the run is for, not a throughput setting.
    ap.add_argument("--batch-size", type=int, default=None,
                    help="override the config batch size for every arm. Unset keeps the config's "
                         "value, which is what the published family trained at.")
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
        # A KAGGLE LOG KEEPS ONLY ITS TAIL, and progress bars fill it. The 2026-08-19 session
        # returned 6.2 MB of "Phase 2 train: 60%|...", which pushed every structural line this
        # runner prints -- the per-arm banners, the timings, the completion records -- out of the
        # retained window, so the log could not answer how far the run got. tqdm reads this.
        "TQDM_DISABLE": "1",
        "PYTHONPATH": f"{repo / 'src'}:{env.get('PYTHONPATH', '')}",
    })
    if a.allow_cpu:
        env["TGNN_ALLOW_CPU_FALLBACK"] = "1"
        print("[gpu] --allow-cpu: preflight skipped and TGNN_ALLOW_CPU_FALLBACK=1 exported to "
              "every child. Expect ~25x slower.", flush=True)
    if a.batch_size:
        extra = env.get("EXTRA_TRAIN_ARGS", "")
        env["EXTRA_TRAIN_ARGS"] = f"{extra} --set batch_size={a.batch_size}".strip()
        print(f"!! batch_size={a.batch_size} for every arm, overriding the config. These arms are "
              f"comparable with each other and NOT schedule-matched to the published family.",
              flush=True)
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
            # THE DEADLINE MUST RESERVE ROOM FOR AN ARM, NOT MERELY REFUSE WHEN IT IS SPENT.
            # The first version asked `left <= 0`, so an arm starting six minutes before the
            # cut-off ran until Kaggle killed the session at twelve hours -- exit 137, and the
            # in-flight arm lost. Every FINISHED arm survived that (its predictions and the
            # progress file are written as each one lands), so the damage was bounded, but a hard
            # kill is worse than a clean stop: it wastes the tail of the session and, on a bad
            # day, the notebook's saved output with it.
            # The budget comes from this run's own history rather than a guess. Arms differ in
            # cost -- channel_swap has no sigma warm-up -- so the estimate is the median of the
            # arms already timed, times a margin, and falls back to a conservative constant until
            # three have been timed.
            # USE EVIDENCE AS SOON AS THERE IS ANY. Waiting for three timed arms means the
            # blunt fallback governs the whole of a short session, which is how a 12 h session
            # can finish with nothing started. One timed arm is worth more than the ceiling.
            timed = [e["hours"] for e in log if e.get("ok") and e.get("hours")]
            if timed:
                margin = ARM_TIME_MARGIN if len(timed) >= 3 else ARM_TIME_MARGIN_SMALL
                need = statistics.median(timed) * margin
            else:
                need = ARM_HOURS_ASSUMED
            left = (deadline - time.time()) / 3600
            if left < need:
                print(f"\n== stopping before seed {seed} arm {arm}: {left:.2f} h left and an arm "
                      f"needs about {need:.2f} h "
                      f"({'median of ' + str(len(timed)) + ' timed' if timed else 'assumed'}).")
                print("   Save /kaggle/working/out as a dataset and run the same command again;")
                print("   finished arms are skipped, so the next session resumes here.")
                break
            # `left` is in HOURS since the fit-check rewrite; this line still divided it by 3600
            # and printed "0.00 h left" beside every arm it started.
            print(f"\n{'=' * 70}\n== seed {seed} arm {arm}  ({left:.2f} h left)\n{'=' * 70}",
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
