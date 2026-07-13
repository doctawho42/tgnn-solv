#!/usr/bin/env python3
"""Free-GPU (Kaggle/Colab) orchestrator for the GPU-gated experiments.

Runs on a plain CUDA box -- no Modal. It shells out to the repo's own entrypoints
(train.py with the --resume-extend fix, the analysis scripts, the shell runners) and
writes each result to --out AS SOON AS it finishes, so a session timeout never loses
completed work. Select what to run with --do; re-run with a different --do in a second
session for the rest.

Experiments (priority order):
  onemodel  full-magnitude candidate-#2 isolation: train a grounded base (sigma warm-up),
            then --resume-extend a full unfrozen SLE, then the sigma_hat_SLE - sigma_hat_grounded
            compensation isolation (results/compensation/isolation_gpu.json + figure).
  tier3     closure-fix crossover done right: a FULL-SLE Stage-A base (Arm params zero-init,
            sigma head frozen so profiles stay grounded), then per (arm x seed) a short
            --resume-extend fine-tune of ONLY that arm's K params, then the crossover stat.
  dataeff   multi-seed data-efficiency sweep (light budget), 3 seeds, aggregated.
  dosed     M4b dosed crystal-grounding.

Usage on Kaggle (Internet ON, GPU ON), after the repo is cloned and the data tarball is
extracted into notebooks/data/:
  python scripts/cloud/kaggle_run.py --do all      --out /kaggle/working/results --device cuda
  python scripts/cloud/kaggle_run.py --do onemodel --out /kaggle/working/results --device cuda
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "notebooks" / "data" / "processed"
SIGMA = REPO / "notebooks" / "data" / "processed_sigma_aux_stream" / "sigma_train.csv"
SIGMA_VAL = REPO / "notebooks" / "data" / "processed_sigma_aux_stream" / "sigma_val.csv"
CRYSTAL = REPO / "notebooks" / "data" / "processed_crystal_aux_stream" / "crystal_train.csv"
CFG = REPO / "configs" / "cosmo_sac.yaml"


def run(cmd, env_extra=None, log=None):
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "KMP_DUPLICATE_LIB_OK": "TRUE",
           "PYTHONPATH": str(REPO / "src")}
    if env_extra:
        env.update(env_extra)
    cmd = [str(c) for c in cmd]
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=str(REPO), env=env)
    dt = time.time() - t0
    print(f"<<< rc={r.returncode}  ({dt/60:.1f} min)", flush=True)
    if r.returncode != 0:
        raise RuntimeError(f"failed ({r.returncode}): {' '.join(cmd)}")


def save(out: Path, name: str, obj):
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(json.dumps(obj, indent=2))
    print(f"[saved] {out / name}", flush=True)


# --------------------------------------------------------------------------- #
def do_onemodel(out: Path, device: str, ep_warm: int, ep_sle: int):
    """Full-magnitude candidate-#2 isolation on one model (warm-up -> unfrozen SLE)."""
    ck = out / "ckpt"; ck.mkdir(parents=True, exist_ok=True)
    base = ck / "grounded_base.pt"; sle = ck / "sle_model.pt"
    # 1. grounded base: sigma warm-up + phase-1, sigma head frozen in any later SLE (none here)
    run(["python", "scripts/train.py", "--config", CFG,
         "--train-data", DATA / "train.csv", "--val-data", DATA / "val.csv", "--test-data", DATA / "test.csv",
         "--sigma-train-data", SIGMA, "--sigma-steps-per-epoch", "21",
         "--crystal-train-data", CRYSTAL, "--crystal-steps-per-epoch", "8",
         "--device", device, "--epochs-phase1", 5, "--epochs-phase2", 0, "--epochs-phase3", 0,
         "--set", f"sigma_warmup_epochs={ep_warm}", "cosmo_sac_kernel_residual_rank=0",
         "--checkpoint", base])
    # 2. same model, full unfrozen SLE (sigma head trains -> drifts)
    run(["python", "scripts/train.py", "--config", CFG, "--resume", base, "--resume-extend",
         "--train-data", DATA / "train.csv", "--val-data", DATA / "val.csv", "--test-data", DATA / "test.csv",
         "--device", device, "--epochs-phase1", 0, "--epochs-phase2", ep_sle, "--epochs-phase3", 0,
         "--set", "freeze_sigma_head_during_sle=false", "sigma_warmup_epochs=0",
         "--checkpoint", sle])
    # 3. isolation analysis (same model: sle vs grounded)
    run(["python", "scripts/analysis/run_compensation_surrogate.py",
         "--checkpoint", sle, "--baseline-checkpoint", base, "--device", device,
         "--out-json", out / "isolation_gpu.json", "--fig-dir", out])
    print("[onemodel] done ->", out / "isolation_gpu.json", flush=True)


def do_tier3(out: Path, device: str, ep1: int, ep2: int, ep3: int, arm_ep2: int, seeds=(0, 1, 2)):
    """Closure-fix crossover with a FULL-SLE grounded base + per-arm resume-extend fine-tune."""
    ck = out / "ckpt"; ck.mkdir(parents=True, exist_ok=True)
    base = ck / "tier3_base.pt"
    R, r = 6, 1
    arch = [f"cosmo_sac_kernel_residual_rank={R}", f"sigma_head_adapter_rank={r}"]
    # Stage A: FULL SLE base (arm params zero-init & untrained; sigma head frozen in SLE so
    # the grounded profiles are preserved). This is a WORKING solubility model, unlike the
    # phase-1-only base that the arms could not rescue.
    run(["python", "scripts/train.py", "--config", CFG,
         "--train-data", DATA / "train.csv", "--val-data", DATA / "val.csv", "--test-data", DATA / "test.csv",
         "--sigma-train-data", SIGMA, "--sigma-steps-per-epoch", "21",
         "--crystal-train-data", CRYSTAL, "--crystal-steps-per-epoch", "8",
         "--device", device, "--epochs-phase1", ep1, "--epochs-phase2", ep2, "--epochs-phase3", ep3,
         "--set", *arch, "freeze_sigma_head_during_sle=true", "arm_trainable=None",
         "--checkpoint", base])

    def export_mae(ckpt, pred):
        run(["python", "scripts/analysis/export_checkpoint_predictions.py",
             "--checkpoint", ckpt, "--data", DATA / "test.csv", "--output", pred,
             "--model-type", "tgnn", "--device", device])
        d = json.loads(Path(str(pred)[:-4] + ".summary.json").read_text())
        return d.get("mae", d.get("MAE"))

    base_pred = out / "base_pred.csv"
    results = {"base_mae": export_mae(base, base_pred), "arms": {}}
    ARMS = {"C_closure": ["arm_trainable=kernel", "correction_output_mode=parameter"],
            "I_input":   ["arm_trainable=sigma_adapter", "correction_output_mode=parameter"],
            "O_output":  ["arm_trainable=correction", "correction_output_mode=ln_x2_residual",
                          "correction_force_open_gate=true", "correction_ln_x2_max_delta=2.0"]}
    for seed in seeds:
        for arm, extra in ARMS.items():
            cp = ck / f"arm_{arm}_seed{seed}.pt"; pred = out / f"arm_{arm}_seed{seed}_pred.csv"
            # resume-extend: load the frozen base, train ONLY this arm's K params in phase 2
            run(["python", "scripts/train.py", "--config", CFG, "--resume", base, "--resume-extend",
                 "--train-data", DATA / "train.csv", "--val-data", DATA / "val.csv", "--test-data", DATA / "test.csv",
                 "--device", device, "--seed", seed,
                 "--epochs-phase1", 0, "--epochs-phase2", arm_ep2, "--epochs-phase3", 0,
                 "--set", *arch, *extra, "freeze_sigma_head_during_sle=true",
                 "--checkpoint", cp])
            results["arms"][f"{arm}_seed{seed}"] = export_mae(cp, pred)
            save(out, "tier3_summary.json", results)   # incremental
    # crossover stat + deformation
    run(["python", "scripts/analysis/analyze_closure_fix.py",
         "--summary", out / "tier3_summary.json",
         "--armC-ckpt", ck / f"arm_C_closure_seed{seeds[0]}.pt",
         "--out-json", out / "tier3_crossover.json", "--fig-dir", out])
    print("[tier3] done ->", out / "tier3_crossover.json", flush=True)


def do_dataeff(out: Path, device: str):
    env = {"DEVICE": device, "OUT_DIR": str(out / "de"), "CKPT_DIR": str(out / "de_ckpt"),
           "EXTRA_TRAIN_ARGS": "--epochs-phase1 12 --epochs-phase2 40 --epochs-phase3 8"}
    summaries = []
    for seed in (42, 1, 2):
        e = {**env, "SEED": str(seed), "OUT_DIR": str(out / f"de_seed{seed}")}
        run(["bash", "scripts/experiments/run_data_efficiency.sh"], env_extra=e)
        summaries.append(str(out / f"de_seed{seed}" / "summary.json"))
    run(["python", "scripts/analysis/aggregate_data_efficiency_seeds.py", *summaries,
         "--out-json", out / "data_efficiency_multiseed.json"])
    print("[dataeff] done ->", out / "data_efficiency_multiseed.json", flush=True)


def do_dosed(out: Path, device: str):
    env = {"DEVICE": device, "OUT_DIR": str(out / "e2_dosed"), "CKPT_DIR": str(out / "e2_dosed_ckpt")}
    run(["bash", "scripts/experiments/run_e2_crystal_grounding_dosed.sh"], env_extra=env)
    print("[dosed] done ->", out / "e2_dosed", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--do", default="all",
                    help="comma list of {onemodel,tier3,dataeff,dosed} or 'all'")
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working/results"))
    ap.add_argument("--device", default="cuda")
    # budgets (trim for a shorter session)
    ap.add_argument("--warm", type=int, default=40); ap.add_argument("--sle", type=int, default=120)
    ap.add_argument("--t3-ep1", type=int, default=30); ap.add_argument("--t3-ep2", type=int, default=120)
    ap.add_argument("--t3-ep3", type=int, default=20); ap.add_argument("--t3-arm-ep2", type=int, default=60)
    ap.add_argument("--allow-cpu", action="store_true", help="permit the silent CPU fallback (do NOT on Kaggle)")
    args = ap.parse_args()

    # Fail fast instead of silently running on CPU for hours: train.py's resolve_device()
    # falls back to CPU when cuda is unavailable (~25x slower here, ~15 min/epoch on the
    # 112k-row corpus), which silently burns an entire Kaggle session.
    if args.device.startswith("cuda") and not args.allow_cpu:
        try:
            import torch
            _ok = torch.cuda.is_available()
            _name = torch.cuda.get_device_name(0) if _ok else ""
        except Exception as _e:  # noqa: BLE001
            _ok, _name = False, f"torch import failed: {_e}"
        if not _ok:
            sys.exit("FATAL: --device cuda but NO GPU is available -- this would silently run on CPU "
                     "(~25x slower, ~15 min/epoch on this corpus). In Kaggle: Settings -> Accelerator "
                     "-> GPU T4 x2 (then re-Add Data) and re-run. Pass --allow-cpu only to force CPU.")
        print(f"[gpu] CUDA OK: {_name}", flush=True)

    todo = ["onemodel", "tier3", "dataeff", "dosed"] if args.do == "all" else args.do.split(",")
    log = {"done": [], "failed": []}
    steps = {
        "onemodel": lambda: do_onemodel(args.out / "compensation", args.device, args.warm, args.sle),
        "tier3":    lambda: do_tier3(args.out / "closure_fix", args.device, args.t3_ep1, args.t3_ep2, args.t3_ep3, args.t3_arm_ep2),
        "dataeff":  lambda: do_dataeff(args.out, args.device),
        "dosed":    lambda: do_dosed(args.out, args.device),
    }
    for name in todo:
        name = name.strip()
        if name not in steps:
            print(f"[skip] unknown experiment {name!r}"); continue
        print(f"\n{'='*70}\n=== {name} ===\n{'='*70}", flush=True)
        try:
            steps[name]()
            log["done"].append(name)
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {name}: {e}", flush=True)
            log["failed"].append({"experiment": name, "error": str(e)})
        save(args.out, "kaggle_run_log.json", log)
    print(f"\nDONE. completed={log['done']} failed={[f['experiment'] for f in log['failed']]}", flush=True)


if __name__ == "__main__":
    main()
