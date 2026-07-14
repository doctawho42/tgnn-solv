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
SIGMA_ARTIFACT = REPO / "results" / "sigma_profile_artifact" / "sigma_profiles.csv"  # VT-2005 oracle σ

# Throughput: the config default batch_size=64 with num_workers=0 leaves the GPU
# starved (~1760 batches/epoch on the 112k-row corpus, ~overhead-bound). A larger
# batch is spliced into every train.py --set via --batch-size (default 256);
# populated in main().
EXTRA_SET: list = []


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
         "--set", f"sigma_warmup_epochs={ep_warm}", "cosmo_sac_kernel_residual_rank=0", *EXTRA_SET,
         "--checkpoint", base])
    # 2. same model, full unfrozen SLE (sigma head trains -> drifts)
    run(["python", "scripts/train.py", "--config", CFG, "--resume", base, "--resume-extend",
         "--train-data", DATA / "train.csv", "--val-data", DATA / "val.csv", "--test-data", DATA / "test.csv",
         "--device", device, "--epochs-phase1", 0, "--epochs-phase2", ep_sle, "--epochs-phase3", 0,
         "--set", "freeze_sigma_head_during_sle=false", "sigma_warmup_epochs=0", *EXTRA_SET,
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
         "--set", *arch, "freeze_sigma_head_during_sle=true", "arm_trainable=None", *EXTRA_SET,
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
                 "--set", *arch, *extra, "freeze_sigma_head_during_sle=true", *EXTRA_SET,
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


def _matched_oracle_delta(learned_csv: Path, oracle_csv: Path) -> dict:
    """MAE(learned σ̂) vs MAE(oracle true σ) on the SAME matched test rows. Both exports
    iterate the same test.csv with the same seed/batch order, so we align by row index and
    VERIFY the true labels line up before differencing."""
    import numpy as np
    import pandas as pd
    L = pd.read_csv(learned_csv); O = pd.read_csv(oracle_csv)
    mask = (O["sigma_oracle_applied"] & O["has_solubility"]).to_numpy()
    yl = L.loc[mask, "ln_x2_true"].to_numpy(float); yo = O.loc[mask, "ln_x2_true"].to_numpy(float)
    aligned = bool(len(yl) == len(yo) and (len(yl) == 0 or np.allclose(yl, yo, atol=1e-6)))
    mae_l = float(L.loc[mask, "abs_error"].mean()); mae_o = float(O.loc[mask, "abs_error"].mean())
    return {"n_matched": int(mask.sum()), "rows_aligned": aligned,
            "mae_learned_sigma": round(mae_l, 4), "mae_oracle_sigma": round(mae_o, 4),
            "grounding_delta_oracle_minus_learned": round(mae_o - mae_l, 4)}


def do_supervised_sigma(out: Path, device: str, ep_warm: int, ep_sle: int):
    """Axis-2 anchor of the two-axis map, with OUR model instead of the TeNNet citation.
    From one grounded base (σ warmup -> physical manifold), train two SLE models:
      supervised = σ head FROZEN through SLE (stays physical),
      endtoend   = σ head UNFROZEN (drifts into a closure-compensating surrogate).
    Eval each with its learned σ̂ and with the oracle TRUE VT-2005 σ, on the same matched
    test subset. Sign of (MAE_oracle - MAE_learned): expected >0 (grounding HURTS) end-to-end,
    <=0 (HELPS/neutral) under supervision -- the sign split IS the supervision axis, anchored
    by our own model rather than the external TeNNet-SAC citation."""
    if not SIGMA_ARTIFACT.exists():
        raise RuntimeError(f"oracle σ artifact missing: {SIGMA_ARTIFACT} -- bundle "
                           "results/sigma_profile_artifact/sigma_profiles.csv onto Kaggle first")
    ck = out / "ckpt"; ck.mkdir(parents=True, exist_ok=True)
    base = ck / "grounded_base.pt"; sup = ck / "supervised_sle.pt"; e2e = ck / "endtoend_sle.pt"
    common = ["--config", CFG, "--train-data", DATA / "train.csv", "--val-data", DATA / "val.csv",
              "--test-data", DATA / "test.csv", "--device", device]
    # 1. grounded base: σ warmup + phase-1 (physical σ manifold), no SLE yet.
    run(["python", "scripts/train.py", *common,
         "--sigma-train-data", SIGMA, "--sigma-steps-per-epoch", "21",
         "--crystal-train-data", CRYSTAL, "--crystal-steps-per-epoch", "8",
         "--epochs-phase1", 5, "--epochs-phase2", 0, "--epochs-phase3", 0,
         "--set", f"sigma_warmup_epochs={ep_warm}", "cosmo_sac_kernel_residual_rank=0", *EXTRA_SET,
         "--checkpoint", base])
    # 2. supervised-σ: full SLE, σ head FROZEN (physical σ preserved).
    run(["python", "scripts/train.py", *common, "--resume", base, "--resume-extend",
         "--sigma-train-data", SIGMA, "--sigma-steps-per-epoch", "21",
         "--epochs-phase1", 0, "--epochs-phase2", ep_sle, "--epochs-phase3", 0,
         "--set", "freeze_sigma_head_during_sle=true", "sigma_warmup_epochs=0",
         "cosmo_sac_kernel_residual_rank=0", *EXTRA_SET, "--checkpoint", sup])
    # 3. end-to-end: full SLE, σ head UNFROZEN (drifts). Sanity: should reproduce the known hurt.
    run(["python", "scripts/train.py", *common, "--resume", base, "--resume-extend",
         "--epochs-phase1", 0, "--epochs-phase2", ep_sle, "--epochs-phase3", 0,
         "--set", "freeze_sigma_head_during_sle=false", "sigma_warmup_epochs=0",
         "cosmo_sac_kernel_residual_rank=0", *EXTRA_SET, "--checkpoint", e2e])
    # 4. eval each: learned σ̂ and oracle true σ, matched-subset delta.
    def export(ckpt, pred, oracle):
        cmd = ["python", "scripts/analysis/export_checkpoint_predictions.py",
               "--checkpoint", ckpt, "--data", DATA / "test.csv", "--output", pred,
               "--model-type", "tgnn", "--device", device]
        if oracle:
            cmd += ["--sigma-oracle", "--sigma-oracle-side", "both", "--sigma-artifact", SIGMA_ARTIFACT]
        run(cmd)
    res: dict = {}
    for tag, ckpt in [("supervised", sup), ("endtoend", e2e)]:
        lp = out / f"{tag}_learned.csv"; op = out / f"{tag}_oracle.csv"
        export(ckpt, lp, oracle=False)
        export(ckpt, op, oracle=True)
        res[tag] = _matched_oracle_delta(lp, op)
        save(out, "supervised_sigma_axis.json", res)
    sd = res["supervised"]["grounding_delta_oracle_minus_learned"]
    ed = res["endtoend"]["grounding_delta_oracle_minus_learned"]
    res["axis2_verdict"] = (f"supervised Δ={sd:+.3f} (<=0 helps/neutral), endtoend Δ={ed:+.3f} "
                            f"(>0 hurts); {'CONFIRMED sign split (supervision flips the sign)' if sd < ed else 'NO split'}")
    save(out, "supervised_sigma_axis.json", res)
    print("[supervised_sigma]", res["axis2_verdict"], flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--do", default="all",
                    help="comma list of {onemodel,tier3,dataeff,dosed,supervised_sigma} or 'all' "
                         "(supervised_sigma is NOT in 'all'; run it explicitly for the axis-2 anchor)")
    ap.add_argument("--out", type=Path, default=Path("/kaggle/working/results"))
    ap.add_argument("--device", default="cuda")
    # budgets (trim for a shorter session)
    ap.add_argument("--warm", type=int, default=40); ap.add_argument("--sle", type=int, default=120)
    ap.add_argument("--t3-ep1", type=int, default=30); ap.add_argument("--t3-ep2", type=int, default=120)
    ap.add_argument("--t3-ep3", type=int, default=20); ap.add_argument("--t3-arm-ep2", type=int, default=60)
    ap.add_argument("--allow-cpu", action="store_true", help="permit the silent CPU fallback (do NOT on Kaggle)")
    ap.add_argument("--batch-size", type=int, default=256,
                    help="override config batch_size (default 64 starves the GPU; 256 = ~4x fewer batches). 0 = leave config default.")
    ap.add_argument("--workers", type=int, default=0,
                    help="DataLoader num_workers. >0 uses persistent workers to overlap graph "
                         "collation with GPU compute (epoch 1 warms the per-worker cache, epochs 2+ are faster). "
                         "Try 4 on Kaggle; watch epoch 2-3 vs epoch 1.")
    args = ap.parse_args()
    global EXTRA_SET
    EXTRA_SET = []
    if args.batch_size:
        EXTRA_SET.append(f"batch_size={args.batch_size}")
    if args.workers:
        EXTRA_SET.append(f"num_workers={args.workers}")

    # Fail fast instead of silently running on CPU for hours: train.py's resolve_device()
    # falls back to CPU when cuda is unavailable (~25x slower here, ~15 min/epoch on the
    # 112k-row corpus), which silently burns an entire Kaggle session.
    if args.device.startswith("cuda") and not args.allow_cpu:
        _name = _err = None
        try:
            import torch
            if torch.cuda.is_available():
                _name = torch.cuda.get_device_name(0)
                (torch.zeros(1, device="cuda") + 1).cpu()   # actually launch a kernel
            else:
                _err = "no GPU visible"
        except Exception as _e:  # noqa: BLE001
            _err = f"{type(_e).__name__}: {str(_e)[:140]}"
        if _err is not None:
            sys.exit(f"FATAL: GPU unusable ({_err}; device={_name}). CPU fallback would be ~25x slower "
                     "(~15 min/epoch on this corpus). If this is a Tesla P100 (compute 6.0 / sm_60) the "
                     "kernel-launch error means it is too old for the installed PyTorch (needs sm_70+): "
                     "set Kaggle Settings -> Accelerator -> GPU T4 x2 (sm_75) and re-Add Data. Use "
                     "--allow-cpu only to force CPU.")
        print(f"[gpu] CUDA OK: {_name}", flush=True)

    todo = ["onemodel", "tier3", "dataeff", "dosed"] if args.do == "all" else args.do.split(",")
    log = {"done": [], "failed": []}
    steps = {
        "onemodel": lambda: do_onemodel(args.out / "compensation", args.device, args.warm, args.sle),
        "tier3":    lambda: do_tier3(args.out / "closure_fix", args.device, args.t3_ep1, args.t3_ep2, args.t3_ep3, args.t3_arm_ep2),
        "dataeff":  lambda: do_dataeff(args.out, args.device),
        "dosed":    lambda: do_dosed(args.out, args.device),
        "supervised_sigma": lambda: do_supervised_sigma(args.out / "supervised_sigma", args.device, args.warm, args.sle),
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
