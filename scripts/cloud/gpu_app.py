"""Modal GPU harness for the TGNN-Solv headline experiments.

Fills the gap flagged in CLAUDE.md ("Modal is result STORAGE only -- there is NO
Modal training app in the repo"): wraps the full-corpus training entrypoints on a
Modal GPU so the two GPU-gated referee items can actually be run to completion:

  * multi-seed data-efficiency sweep  (blind reviewer Major 3: the single-seed
    +0.08 low-data gap needs error bars)
  * M4b dosed crystal-grounding run   (referee M4b: is the crystal-null dose-limited?)

Runs are self-contained: the image bakes the src package, scripts, configs and the
~63 MB of processed splits + crystal aux stream. Results land on the ``tgnn-results``
Modal Volume AND are returned to the caller as parsed JSON.

Usage (from the repo root, so add_local_dir paths resolve):
  modal run scripts/cloud/gpu_app.py::smoke                      # ~1-epoch wiring check
  modal run scripts/cloud/gpu_app.py::data_efficiency --seed 1   # one full seed
  modal run scripts/cloud/gpu_app.py::dosed_crystal              # M4b

Pull the full artifacts back with:
  modal volume get tgnn-results /data_efficiency_seed1 ./results/data_efficiency_multiseed

Every `--device cuda` below, and the `DEVICE=cuda` handed to the shell drivers, stays a
literal. The six scripts/experiments drivers dropped theirs because they run on whatever
box the author is sitting at, where naming CUDA was a wish about the hardware; each
function here is decorated `gpu=GPU` and cannot start without one, so the demand is a
statement about the machine. It also has to be typed: with `DEVICE` unset a driver now
lets each child read the box, which on a Modal container whose CUDA broke would train on
CPU for the whole timeout instead of raising in the first minute.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import modal

REPO = "/root/tgnn"
GPU = os.environ.get("TGNN_GPU", "A10G")

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git")
    .pip_install(
        "torch==2.3.1",
        "torch-geometric>=2.4",
        "rdkit>=2023.9.1",
        "numpy>=1.24,<2",
        "pandas>=2.0",
        "scikit-learn",
        "scipy",
        "pyyaml",
        "tqdm",
        "requests",
    )
    # --- editable install needs pyproject + README + src at build time ---
    .add_local_file("pyproject.toml", f"{REPO}/pyproject.toml", copy=True)
    .add_local_file("README.md", f"{REPO}/README.md", copy=True)
    .add_local_dir("src", f"{REPO}/src", copy=True)
    .run_commands(f"cd {REPO} && pip install -e . --no-deps")
    # --- runtime assets (order after the install is fine; not needed to build) ---
    .add_local_dir("scripts", f"{REPO}/scripts", copy=True)
    .add_local_dir("configs", f"{REPO}/configs", copy=True)
    .add_local_dir(
        "notebooks/data/processed", f"{REPO}/notebooks/data/processed", copy=True
    )
    .add_local_dir(
        "notebooks/data/processed_crystal_aux_stream",
        f"{REPO}/notebooks/data/processed_crystal_aux_stream",
        copy=True,
    )
    .add_local_dir(
        "notebooks/data/processed_sigma_aux_stream",
        f"{REPO}/notebooks/data/processed_sigma_aux_stream",
        copy=True,
    )
    .env({"KMP_DUPLICATE_LIB_OK": "TRUE", "TOKENIZERS_PARALLELISM": "false"})
)

app = modal.App("tgnn-gpu")
vol = modal.Volume.from_name("tgnn-results", create_if_missing=True)

DATA_DIR = f"{REPO}/notebooks/data/processed"
VAL = f"{DATA_DIR}/val.csv"
TEST = f"{DATA_DIR}/test.csv"
CRYSTAL = f"{REPO}/notebooks/data/processed_crystal_aux_stream/crystal_train.csv"
SIGMA = f"{REPO}/notebooks/data/processed_sigma_aux_stream/sigma_train.csv"


def _run(cmd, extra_env=None):
    """Run a subprocess in the repo, streaming output; raise on non-zero exit."""
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "KMP_DUPLICATE_LIB_OK": "TRUE"}
    if extra_env:
        env.update(extra_env)
    print(">>>", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], cwd=REPO, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"command failed (rc={r.returncode}): {' '.join(map(str, cmd))}")


# ---------------------------------------------------------------------------
# Data-efficiency sweep (blind reviewer Major 3): one seed per call.
# ---------------------------------------------------------------------------
@app.function(image=image, gpu=GPU, timeout=6 * 3600, volumes={"/vol": vol})
def data_efficiency(
    seed: int = 42,
    fracs: str = "0.05 0.1 0.25 0.5 1.0",
    ep1: int = 30,
    ep2: int = 120,
    ep3: int = 30,
    crystal_steps: int = 8,
):
    """Subsample train BY SOLUTE at each fraction; train physics + DirectGNN on the
    identical subsample with a FIXED budget; export -> rank -> aggregate. The whole
    sweep uses one ``seed`` (drives both the subsample draw and the model init), so
    calling this at several seeds yields the multi-seed error bars Major 3 asked for.
    """
    import pandas as pd

    os.chdir(REPO)
    out = Path(f"/vol/data_efficiency_seed{seed}")
    (out / "data").mkdir(parents=True, exist_ok=True)
    ckpt = out / "ckpt"
    ckpt.mkdir(exist_ok=True)

    train_full = pd.read_csv(f"{DATA_DIR}/train.csv", low_memory=False)
    solutes = pd.Series(train_full["solute_smiles"].dropna().unique())

    entries = []
    for frac in fracs.split():
        fr = float(frac)
        sub = out / "data" / f"train_f{frac}.csv"
        keep = set(solutes.sample(frac=fr, random_state=seed)) if fr < 1.0 else set(solutes)
        mask = train_full["solute_smiles"].isin(keep)
        train_full[mask].to_csv(sub, index=False)
        print(f"== seed {seed} frac {frac}: {len(keep)}/{len(solutes)} solutes, "
              f"{int(mask.sum())}/{len(train_full)} rows ==", flush=True)

        for model in ("physics", "direct"):
            rd = out / model / f"frac_{frac}"
            rd.mkdir(parents=True, exist_ok=True)
            cp = ckpt / f"{model}_f{frac}.pt"
            pred = rd / "pred.csv"
            if model == "physics":
                _run([
                    "python", "scripts/train.py", "--config", "configs/physics_grounded.yaml",
                    "--train-data", sub, "--val-data", VAL, "--test-data", TEST,
                    "--checkpoint", cp, "--device", "cuda", "--seed", seed,
                    "--crystal-train-data", CRYSTAL, "--crystal-steps-per-epoch", crystal_steps,
                    "--epochs-phase1", ep1, "--epochs-phase2", ep2, "--epochs-phase3", ep3,
                ])
                mt = "tgnn"
            else:
                _run([
                    "python", "scripts/train_directgnn.py",
                    "--config", "configs/paper_config_directgnn_tuned.yaml",
                    "--train-data", sub, "--val-data", VAL, "--test-data", TEST,
                    "--checkpoint", cp, "--device", "cuda", "--seed", seed,
                    "--epochs", ep2,
                ])
                mt = "direct"

            _run([
                "python", "scripts/analysis/export_checkpoint_predictions.py",
                "--checkpoint", cp, "--data", TEST, "--output", pred,
                "--model-type", mt, "--device", "cuda",
            ])
            try:
                _run([
                    "python", "scripts/analysis/run_ranking_eval.py",
                    "--predictions-csv", pred, "--out-json", rd / "rank.json",
                ])
            except RuntimeError as e:
                print(f"   ranking eval failed (non-fatal): {e}", flush=True)
            summary_json = str(pred)[:-4] + ".summary.json"
            entries += ["--entry", f"{model}:{frac}:{summary_json}:{rd / 'rank.json'}"]
        vol.commit()  # persist after each fraction so partial progress survives a drop

    _run([
        "python", "scripts/analysis/run_data_efficiency_summary.py",
        *entries, "--out-json", out / "summary.json",
    ])
    vol.commit()
    return json.loads((out / "summary.json").read_text())


# ---------------------------------------------------------------------------
# M4b: dosed crystal grounding (reuses the shell wrapper; both trainers are train.py).
# ---------------------------------------------------------------------------
@app.function(image=image, gpu=GPU, timeout=6 * 3600, volumes={"/vol": vol})
def dosed_crystal(ep1: int = 50, ep2: int = 200, ep3: int = 50, crystal_steps: int = 48):
    os.chdir(REPO)
    out = "/vol/e2_crystal_dosed"
    ck = "/vol/e2_crystal_dosed_ckpt"
    env = {
        "DEVICE": "cuda",
        "CRYSTAL_STEPS": str(crystal_steps),
        "OUT_DIR": out,
        "CKPT_DIR": ck,
        # only the epoch budget here; the wrapper appends the unit crystal-aux weights.
        "EXTRA_TRAIN_ARGS": f"--epochs-phase1 {ep1} --epochs-phase2 {ep2} --epochs-phase3 {ep3}",
    }
    _run(["bash", "scripts/experiments/run_e2_crystal_grounding_dosed.sh"], extra_env=env)
    vol.commit()
    comp = Path(out) / "comparison.json"
    return json.loads(comp.read_text()) if comp.exists() else {"note": "no comparison.json", "out": out}


# ---------------------------------------------------------------------------
# Tier-3 closure-fix crossover: does a matched budget spent on the COSMO-SAC
# MAP (Arm C) beat the same budget on the sigma-profile head (Arm I)?  Because
# B_clos dominates (the keystone), Arm C should win. Arm O = the inert Gate-B
# output residual. Stage A builds ONE grounded frozen base (phase-1 only, arch
# with R,r zero-init); Stage B branches per (arm x seed), training ONLY the
# arm's K params via arm_trainable, so the frozen intermediate is byte-identical.
# ---------------------------------------------------------------------------
@app.function(image=image, gpu=GPU, timeout=12 * 3600, volumes={"/vol": vol})
def closure_fix(rank_R: int = 6, rank_r: int = 1, seeds=(0, 1, 2),
                ep2: int = 80, ep3: int = 20, smoke: bool = False):
    os.chdir(REPO)
    out = Path("/vol/closure_fix")
    ck = out / "ckpt"
    ck.mkdir(parents=True, exist_ok=True)
    cfg = "configs/cosmo_sac.yaml"
    train = f"{DATA_DIR}/train.csv"
    base = ck / "arm_base.pt"
    arch = [f"cosmo_sac_kernel_residual_rank={rank_R}", f"sigma_head_adapter_rank={rank_r}"]

    def _mae(pred_csv):
        s = Path(str(pred_csv)[:-4] + ".summary.json")
        d = json.loads(s.read_text())
        for k in ("mae", "MAE", "ln_x2_mae", "test_mae"):
            if k in d:
                return d[k]
        return d  # fall back: return whole dict so we can see the keys

    def _export(ckpt, pred):
        _run(["python", "scripts/analysis/export_checkpoint_predictions.py",
              "--checkpoint", str(ckpt), "--data", TEST, "--output", str(pred),
              "--model-type", "tgnn", "--device", "cuda"])

    # --- Stage A: grounded frozen base, phase-1 only (arch present, zero-init => exact COSMO-SAC) ---
    stageA_smoke = (["--epochs-phase1", "1"] if smoke else [])
    stageA_sets = (["sigma_warmup_epochs=1"] if smoke else [])  # warmup is separate from phase-1 epochs
    _run(["python", "scripts/train.py", "--config", cfg,
          "--train-data", train, "--val-data", VAL, "--test-data", TEST,
          "--sigma-train-data", SIGMA, "--sigma-steps-per-epoch", "21",
          "--crystal-train-data", CRYSTAL, "--crystal-steps-per-epoch", "8",
          "--device", "cuda", "--epochs-phase2", "0", "--epochs-phase3", "0",
          *stageA_smoke,
          "--set", *arch, "correction_output_mode=parameter", *stageA_sets,
          "--checkpoint", str(base)])
    vol.commit()

    base_pred = out / "base_pred.csv"
    _export(base, base_pred)
    results = {"config": {"rank_R": rank_R, "rank_r": rank_r, "seeds": list(seeds),
                          "K_C": 52 * rank_R, "note": "K_I=(D_r+128)*r, D_r=192 at hidden_dim=64 => 320r"},
               "base_mae": _mae(base_pred), "arms": {}}

    # --- Stage B: per (arm x seed), train ONLY the arm's K params (resume the frozen base) ---
    ARMS = {
        "C_closure":  ["arm_trainable=kernel", "correction_output_mode=parameter"],
        "I_input":    ["arm_trainable=sigma_adapter", "correction_output_mode=parameter"],
        "O_output":   ["arm_trainable=correction", "correction_output_mode=ln_x2_residual",
                       "correction_force_open_gate=true", "correction_ln_x2_max_delta=2.0"],
    }
    smoke_B = (["--epochs-phase2", "1", "--epochs-phase3", "0"] if smoke
               else ["--epochs-phase2", str(ep2), "--epochs-phase3", str(ep3)])
    for seed in seeds:
        for arm, extra in ARMS.items():
            cp = ck / f"arm_{arm}_seed{seed}.pt"
            pred = out / f"arm_{arm}_seed{seed}_pred.csv"
            _run(["python", "scripts/train.py", "--config", cfg,
                  "--train-data", train, "--val-data", VAL, "--test-data", TEST,
                  "--resume", str(base), "--device", "cuda", "--seed", str(seed),
                  "--epochs-phase1", "0", *smoke_B,
                  "--set", *arch, *extra,
                  "--checkpoint", str(cp)])
            _export(cp, pred)
            results["arms"][f"{arm}_seed{seed}"] = _mae(pred)
            vol.commit()

    (out / "closure_fix_summary.json").write_text(json.dumps(results, indent=2))
    vol.commit()
    return results


# ---------------------------------------------------------------------------
# Cheap end-to-end wiring check (pennies of GPU): 1 epoch, one fraction.
# ---------------------------------------------------------------------------
@app.local_entrypoint()
def smoke():
    print("=== SMOKE: data-efficiency, frac 0.05, 1 epoch/phase ===", flush=True)
    r = data_efficiency.remote(seed=42, fracs="0.05", ep1=1, ep2=1, ep3=1, crystal_steps=2)
    print(json.dumps(r, indent=2)[:3000], flush=True)


@app.local_entrypoint()
def smoke_dosed():
    print("=== SMOKE: dosed crystal, 1 epoch/phase, CRYSTAL_STEPS=2 ===", flush=True)
    r = dosed_crystal.remote(ep1=1, ep2=1, ep3=1, crystal_steps=2)
    print(json.dumps(r, indent=2)[:3000], flush=True)


@app.local_entrypoint()
def data_efficiency_seed(seed: int = 1):
    r = data_efficiency.remote(seed=seed)
    print(json.dumps(r, indent=2), flush=True)


@app.local_entrypoint()
def run_dosed():
    r = dosed_crystal.remote()
    print(json.dumps(r, indent=2), flush=True)


@app.local_entrypoint()
def closure_fix_smoke():
    print("=== SMOKE: closure-fix Stage A(1ep) + Stage B(1ep) x 1 seed ===", flush=True)
    r = closure_fix.remote(rank_R=6, rank_r=1, seeds=(0,), smoke=True)
    print(json.dumps(r, indent=2), flush=True)


@app.local_entrypoint()
def run_closure_fix():
    r = closure_fix.remote(rank_R=6, rank_r=1, seeds=(0, 1, 2))
    print(json.dumps(r, indent=2), flush=True)


@app.local_entrypoint()
def launch_all():
    """Fire-and-forget: spawn all GPU jobs server-side (persist regardless of client),
    print their FunctionCall ids, and exit. Results land on the tgnn-results volume;
    poll it with `modal volume ls tgnn-results`. Robust to client disconnects."""
    ids = {}
    for s in (42, 1, 2):
        ids[f"data_efficiency_seed{s}"] = data_efficiency.spawn(seed=s).object_id
    ids["dosed_crystal"] = dosed_crystal.spawn().object_id
    print("SPAWNED (running server-side, poll the volume for results):")
    print(json.dumps(ids, indent=2), flush=True)
