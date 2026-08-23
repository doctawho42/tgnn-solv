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

So this wrapper adds three things and duplicates nothing: a deadline anchored to the SESSION's
start rather than this script's, a hard stop on an arm that overruns it, and a completeness check
on each predictions file before it is allowed to count as done.

THE DEADLINE AND THE OVERRUN ARE SEPARATE GUARDS, and the 2026-08-23 kill needed both. The
pre-arm check refuses to start an arm that cannot be expected to finish; it was measuring from
its own start, so it never charged the budget for the twenty-odd minutes of pip install and data
staging that precede it, and nothing at all stopped an arm that beat the check and then missed
its estimate. Exit 137 followed, which is worse than a clean stop: Kaggle's kill lands before the
platform writes the notebook's output, so the session can lose arms it had already exported.

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
import signal
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
#: AND THEN 6.0 WAS WRONG IN THE OTHER DIRECTION, for the same reason in reverse: it is a ceiling
#: measured on a GCP GPU, quoted for a script whose docstring says "USAGE ON KAGGLE", and a T4 is
#: the slower card. Two Kaggle sessions have now measured this one directly -- 2026-08-19 reached
#: phase 2 epoch 39 of 70 and 2026-08-21 epoch 34, both against 30+70+10 epochs, so ~58% of an arm
#: per twelve GPU-hours. The number below is that: about 20 h an arm at the config batch size.
#: It is safe to carry the true figure now only because the pre-arm check no longer refuses work
#: on it (see the block at the arm loop); when it did, an honest 20 here would have refused
#: everything. A constant that can veto must be a ceiling; one that only informs must be the truth.
#: --batch-size 256 is the lever that moves it, at a cost stated on that flag.
ARM_HOURS_ASSUMED = 20.0
#: Applied to the median of arms this run has already timed. Wider while that median rests on one
#: or two observations, because a single arm is not a distribution.
ARM_TIME_MARGIN = 1.25
ARM_TIME_MARGIN_SMALL = 1.5
#: Where the notebook's first cell stamps the session's start. See _session_start.
SESSION_T0_FILE = Path("/kaggle/working/.session_t0")
#: Held back at the end of the budget so the platform can write the notebook's output. A session
#: killed at the cap dies before that write, which is how a run loses arms it had already exported.
SAVE_RESERVE_HOURS = 0.25
#: The least usable budget in which starting or resuming an arm buys anything. Below it the slice
#: cannot reach the next checkpoint, so the session would spend the time and save no progress.
#: Deliberately small: this is the only thing standing between the runner and a useful partial
#: session, and demanding a WHOLE arm here is what made two twelve-hour sessions return nothing.
MIN_USEFUL_SLICE_HOURS = 0.75


def _session_start(path: Path) -> tuple[float, str]:
    """When the SESSION started, which is not when this runner did.

    ``--hours`` is a budget against Kaggle's session cap, and that cap starts when the notebook
    starts. Everything before this script -- pip install, staging the repo, copying and hashing
    the data -- spends the budget invisibly, so a deadline taken from ``time.time()`` here is
    optimistic by exactly the setup time. The notebook's first cell stamps its own start; this
    reads it, and says so loudly when it is missing rather than quietly reverting to the
    optimistic clock.
    """
    try:
        t0 = float(path.read_text().strip())
    except (OSError, ValueError) as exc:
        print(f"!! no usable session stamp at {path} ({type(exc).__name__}): the deadline runs "
              f"from NOW and does not include this session's setup time. On Kaggle that means it "
              f"is optimistic by however long cells 1-5 took.", flush=True)
        return time.time(), "runner start (no stamp)"
    age = (time.time() - t0) / 3600
    if not -0.01 < age < 24:
        print(f"!! session stamp at {path} reads {age:.2f} h old, which is not a live session's "
              f"age; ignoring it and running the deadline from now.", flush=True)
        return time.time(), f"runner start (stamp {age:.2f} h rejected)"
    print(f"[clock] session started {age * 60:.1f} min ago; the budget runs from there.",
          flush=True)
    return t0, "session start"


def _run_arm(repo: Path, env: dict, timeout_s: float) -> tuple[int, bool]:
    """Run one arm, killing its whole process group if it outlives ``timeout_s``.

    ``start_new_session`` and ``killpg`` rather than ``subprocess.run(timeout=...)``: the child is
    a shell that spawns python, and terminating the shell alone orphans the trainer, which then
    keeps the GPU and runs on to the platform's kill anyway. The group gets SIGTERM first so the
    trainer can close its checkpoint, and SIGKILL only if it is still there two minutes later.
    """
    # A FLOOR, so that arithmetic which lands at or below zero cannot ask for an instant kill: the
    # pre-arm check is what refuses a hopeless arm, and this is only the backstop behind it.
    slice_s = max(timeout_s, 60.0)
    p = subprocess.Popen(["bash", "scripts/experiments/run_e5_sigma_grounding.sh"],
                         cwd=repo, env=env, start_new_session=True)
    try:
        return p.wait(timeout=slice_s), False
    except subprocess.TimeoutExpired:
        print(f"\n!! arm exceeded its {slice_s / 3600:.2f} h slice; stopping it.", flush=True)
        for sig, grace in ((signal.SIGTERM, 120), (signal.SIGKILL, 60)):
            try:
                os.killpg(os.getpgid(p.pid), sig)
            except (ProcessLookupError, PermissionError):
                break
            try:
                p.wait(timeout=grace)
                break
            except subprocess.TimeoutExpired:
                continue
        return (p.returncode if p.returncode is not None else -1), True


def _checkpoint_batch(path: Path) -> int | None:
    """The batch size a checkpoint was trained at, or None if it does not say."""
    try:
        import torch
        cfg = torch.load(path, map_location="cpu", weights_only=False).get("config") or {}
    except Exception:      # noqa: BLE001 -- a checkpoint we cannot read is not a mismatch
        return None
    cfg = vars(cfg) if hasattr(cfg, "__dict__") else cfg
    v = cfg.get("batch_size") if isinstance(cfg, dict) else None
    return int(v) if isinstance(v, (int, float)) else None


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
                    help="the session budget, measured from the SESSION's start (see "
                         "--session-t0-file), not from this script's. No arm is started that "
                         "cannot be expected to finish inside it, and one that overruns anyway "
                         "is killed rather than left for the platform to kill.")
    ap.add_argument("--session-t0-file", type=Path, default=SESSION_T0_FILE,
                    help="file holding the session's start as a unix timestamp; the generated "
                         "notebook writes it in its first cell")
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
    t0, t0_source = _session_start(a.session_t0_file)
    deadline = t0 + a.hours * 3600
    print(f"[clock] budget {a.hours:.2f} h from {t0_source}; "
          f"{(deadline - time.time()) / 3600:.2f} h left as this runner starts.", flush=True)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    a.ckpt_dir.mkdir(parents=True, exist_ok=True)
    progress = a.out_dir / "kaggle_progress.json"
    log: list[dict] = json.loads(progress.read_text()) if progress.exists() else []
    # THE SCHEDULE TRAVELS WITH THE NUMBERS. --batch-size changes the optimisation schedule, so
    # arms trained under it are comparable with each other and not with the published family, and
    # that fact has to be readable from the deposit rather than from a warning that scrolled past
    # in a notebook log nobody kept. Recorded per arm, because a resumed run can be given a
    # different value than the session that started it -- which would be a defect, and one this
    # field makes visible instead of silent.
    batch_note = a.batch_size or "config"

    # A truncated export from a killed session must not read as a finished arm.
    for seed in a.seeds:
        for arm in a.arms:
            pred = a.out_dir / f"seed_{seed}" / f"{arm}_predictions.csv"
            if pred.exists() and rows(pred) < EXPECTED_ROWS_MIN:
                print(f"!! {pred} has {rows(pred)} rows, below {EXPECTED_ROWS_MIN}: "
                      f"truncated by a killed session. Deleting so it re-exports.")
                pred.unlink()

    # AND A CHECKPOINT FROM A DIFFERENT SCHEDULE MUST NOT BE RESUMED INTO THIS ONE.
    # Resuming is what makes a multi-session run possible, and it is exactly what makes a changed
    # --batch-size dangerous: the optimiser state in the file belongs to the old batch, so an arm
    # resumed across the change is ONE arm trained under TWO schedules, which is neither of them
    # and is invisible in the result. The recovered 2026-08-21 checkpoint is the live case -- it
    # carries batch_size 64 and half of phase 2. Refuse rather than delete: 85 MB of GPU time is
    # not this script's to throw away, and the choice between restarting the arm and reverting
    # the flag belongs to whoever is running it.
    want = a.batch_size if a.batch_size else None
    for seed in a.seeds:
        for arm in a.arms:
            ck = a.ckpt_dir / f"{arm}_seed{seed}.pt"
            if not ck.exists():
                continue
            had = _checkpoint_batch(ck)
            if had is not None and want is not None and had != want:
                sys.exit(
                    f"FATAL: {ck} was trained at batch_size {had} and this run asks for {want}. "
                    f"Resuming it would train one arm under two optimisation schedules. Either "
                    f"drop --batch-size {want} to continue that arm as it was trained, or move "
                    f"the checkpoint aside to restart this arm at {want}.")

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
            # THE CHECK ASKS WHETHER THE SLICE IS USEFUL, NOT WHETHER THE ARM FITS.
            #
            # It used to demand room for a WHOLE arm, and that premise is wrong for work which
            # checkpoints. Its purpose was never completion -- it was to avoid Kaggle's hard kill,
            # which lands before the platform writes the notebook's output and so can lose arms
            # already exported. _run_arm now stops the arm itself, SAVE_RESERVE_HOURS before the
            # cap, so a session always ends cleanly and always saves. With that in hand, an arm
            # too big for one session is not a hazard: it advances, checkpoints, and resumes.
            #
            # Demanding completion was actively harmful here, because on this hardware an arm does
            # NOT fit. Two Kaggle sessions measured it: 2026-08-19 reached phase 2 epoch 39 of 70
            # and 2026-08-21 reached epoch 34, both against the 30+70+10 epochs cosmo_sac.yaml
            # asks for -- roughly 58% of one arm per twelve GPU-hours, so about 20 h an arm at the
            # config batch size, against the 6.0 h ceiling ARM_HOURS_ASSUMED carries from GCP-GPU
            # manifests. A completion check fed that number can only choose between refusing every
            # arm and starting one it cannot finish; neither produces a result, and both of those
            # sessions produced none. What produces a result is two sessions per arm.
            #
            # So the estimate stays, as INFORMATION -- it is what tells the reader how many more
            # sessions to expect -- and the decision to start is the smaller question of whether
            # there is time to reach the next checkpoint.
            # ONLY ARMS TRAINED AT THIS BATCH SIZE. The whole point of the flag is that it changes
            # what an arm costs, so a median pooled across values estimates neither. Entries
            # written before this field existed carry no batch_size and are excluded rather than
            # assumed to match: an unlabelled timing is not evidence about a labelled run.
            timed = [e["hours"] for e in log
                     if e.get("ok") and e.get("hours") and e.get("batch_size") == batch_note]
            if timed:
                margin = ARM_TIME_MARGIN if len(timed) >= 3 else ARM_TIME_MARGIN_SMALL
                need, need_src = statistics.median(timed) * margin, f"median of {len(timed)} timed"
            else:
                need, need_src = ARM_HOURS_ASSUMED, "assumed, unmeasured on this hardware"
            left = (deadline - time.time()) / 3600 - SAVE_RESERVE_HOURS
            if left < MIN_USEFUL_SLICE_HOURS:
                print(f"\n== stopping before seed {seed} arm {arm}: {left:.2f} h of usable budget "
                      f"left, below the {MIN_USEFUL_SLICE_HOURS:.2f} h it takes to reach a "
                      f"checkpoint worth saving.")
                print("   Save /kaggle/working/out as a dataset and run the same command again;")
                print("   finished arms are skipped, partial ones resume from their checkpoint.")
                break
            if left < need:
                print(f"\n!! seed {seed} arm {arm} will NOT finish this session: {left:.2f} h "
                      f"usable against about {need:.2f} h for an arm ({need_src}). Starting it "
                      f"anyway -- it checkpoints, and the next session resumes it.", flush=True)
            # `left` is in HOURS since the fit-check rewrite; this line still divided it by 3600
            # and printed "0.00 h left" beside every arm it started.
            print(f"\n{'=' * 70}\n== seed {seed} arm {arm}  ({left:.2f} h left)\n{'=' * 70}",
                  flush=True)
            arm_t0 = time.time()
            # THE PRE-ARM CHECK RESERVES ROOM FOR AN ESTIMATE, AND AN ESTIMATE CAN BE WRONG.
            # Until 2026-08-23 nothing stopped an arm once it had started, so an arm that missed
            # its estimate ran until Kaggle killed the container -- exit 137, which is worse than
            # it looks: the kill lands before the platform writes the notebook's output, so a run
            # can lose arms it had already finished and exported. Killing the child ourselves
            # ends the session cleanly with the output intact, and --checkpoint-every means the
            # interrupted arm resumes next session rather than restarting.
            cap = deadline - time.time() - SAVE_RESERVE_HOURS * 3600
            rc, timed_out = _run_arm(repo, {**env, "SEEDS": str(seed), "ARMS": arm}, cap)
            entry = {"seed": seed, "arm": arm, "returncode": rc,
                     "hours": round((time.time() - arm_t0) / 3600, 3),
                     "rows": rows(pred), "timed_out": timed_out, "batch_size": batch_note,
                     "schedule_matched_to_published_family": a.batch_size is None,
                     "ok": rc == 0 and rows(pred) >= EXPECTED_ROWS_MIN}
            log.append(entry)
            progress.write_text(json.dumps(log, indent=2) + "\n")
            print(f"-- {entry}")
            if timed_out:
                print(f"!! seed {seed} arm {arm} outran the session budget and was stopped at "
                      f"{entry['hours']:.2f} h, {SAVE_RESERVE_HOURS:.2f} h before the cap, so "
                      f"this notebook's output still gets written. Save /kaggle/working/out and "
                      f"re-run: this arm resumes from its checkpoint.")
                break
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
