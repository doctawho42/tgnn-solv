#!/usr/bin/env bash
# P3 run_e5: decisive lever-C comparison — NRTL / DirectGNN-h64 / cosmo {ungrounded,
# grounded-A residual-only, grounded-B +SG} / oracle — on the corrected split, >=3 seeds,
# metrics intersection-locked by run_e5_comparison.py. REAL metrics need GPU; CPU = smoke.
#
# Usage (GPU):
#   DEVICE=cuda bash scripts/experiments/run_e5_sigma_grounding.sh
# 1-seed pilot (validate pipeline + read ungrounded std(lng) to calibrate --lngamma-band):
#   DEVICE=cuda SEEDS=42 bash scripts/experiments/run_e5_sigma_grounding.sh
# CPU smoke (no meaningful metrics — just checks the wiring):
#   DEVICE=cpu SEEDS=42 WARMUP_EPOCHS=1 SIGMA_STEPS=2 \
#     EXTRA_TRAIN_ARGS="--epochs-phase1 1 --epochs-phase2 1 --epochs-phase3 1" \
#     bash scripts/experiments/run_e5_sigma_grounding.sh
#
# PREEMPTION-SAFE (Colab / Studio Lab): re-running resumes automatically —
#   * an arm whose predictions.csv already exists is SKIPPED;
#   * an arm with a partial checkpoint RESUMES mid-training (--checkpoint-every/--resume).
# Point CKPT_DIR and OUT_DIR at a persistent location (e.g. mounted Drive) so progress
# survives a disconnect.
#
# Env overrides (defaults):
#   PY               $HOME/anaconda3/envs/tgnn-solv/bin/python
#   DEVICE           cuda            torch device for training/export
#   DATA_DIR         notebooks/data/processed       (the CORRECTED split)
#   SIGMA_DIR        notebooks/data/processed_sigma_aux_stream
#   OUT_DIR          results/e5_sigma_grounding
#   CKPT_DIR         checkpoints/e5
#   SEEDS            "42 43 44"      space-separated list of random seeds
#   ARMS             all six         space-separated arm subset (smoke: ARMS="ungrounded")
#   SIGMA_STEPS      21              sigma aux steps per epoch
#   WARMUP_EPOCHS    40              sigma warmup epochs before SLE
#   CHECKPOINT_EVERY 5               save a resumable training checkpoint every N epochs
#   EXTRA_TRAIN_ARGS ""              passed verbatim to TGNN train.py calls
#   SIGMA_ARTIFACT   results/sigma_profile_artifact/sigma_profiles.csv
set -euo pipefail
cd "$(dirname "$0")/../.."
export KMP_DUPLICATE_LIB_OK=TRUE   # rdkit/torch/sklearn libomp clash on macOS

PY="${PY:-$HOME/anaconda3/envs/tgnn-solv/bin/python}"
DEVICE="${DEVICE:-cuda}"
DATA_DIR="${DATA_DIR:-notebooks/data/processed}"
SIGMA_DIR="${SIGMA_DIR:-notebooks/data/processed_sigma_aux_stream}"
OUT_DIR="${OUT_DIR:-results/e5_sigma_grounding}"
CKPT_DIR="${CKPT_DIR:-checkpoints/e5}"
SEEDS="${SEEDS:-42 43 44}"
ARMS="${ARMS:-nrtl directgnn ungrounded grounded_a grounded_b oracle}"  # subset for smoke/targeting
SIGMA_STEPS="${SIGMA_STEPS:-21}"
WARMUP_EPOCHS="${WARMUP_EPOCHS:-40}"
CHECKPOINT_EVERY="${CHECKPOINT_EVERY:-5}"
EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS:-}"   # e.g. --epochs-phase1 1 --epochs-phase2 1 --epochs-phase3 1 for CPU smoke
SIGMA_ARTIFACT="${SIGMA_ARTIFACT:-results/sigma_profile_artifact/sigma_profiles.csv}"

TRAIN="${DATA_DIR}/train.csv"; VAL="${DATA_DIR}/val.csv"; TEST="${DATA_DIR}/test.csv"
mkdir -p "${OUT_DIR}" "${CKPT_DIR}"

echo "================================================================"
echo " run_e5: sigma-grounding decisive comparison"
echo "   device=${DEVICE}  data=${DATA_DIR}  sigma=${SIGMA_DIR}"
echo "   seeds=${SEEDS}  out=${OUT_DIR}  ckpt=${CKPT_DIR}  checkpoint_every=${CHECKPOINT_EVERY}"
echo "================================================================"

# --- 0. Guard: refuse to run on corrupted (+273 K) T_m labels ---
"${PY}" - "$TEST" <<'PYG'
import sys, pandas as pd
df = pd.read_csv(sys.argv[1], low_memory=False)
if "T_m" in df.columns:
    tm = pd.to_numeric(df["T_m"], errors="coerce")
    if "has_T_m" in df.columns:
        tm = tm[df["has_T_m"].astype(str).str.lower().isin({"true", "1", "1.0"})]
    med = float(tm.median())
    print(f"   test T_m median = {med:.1f} K", "(corrected)" if med < 560 else "(!! CORRUPTED)")
    assert med < 560, f"T_m median {med} looks +273 K corrupted -- run prepare_data with the fixed loader first."
print("T_m guard ok")
PYG

# --- Prereq: build the scaffold-disjoint sigma-VAL split if missing ---
if [ ! -f "${SIGMA_DIR}/sigma_val.csv" ]; then
  echo "== building sigma-VAL split (scaffold-disjoint from test+val) =="
  "${PY}" scripts/data/build_sigma_profile_aux_stream.py \
    --output-csv "${SIGMA_DIR}/sigma_train.csv" --output-val-csv "${SIGMA_DIR}/sigma_val.csv" \
    --val-fraction 0.1 --split-seed 0 \
    --exclude-scaffolds-from "${TEST}" "${VAL}"
fi

# --- Guard: oracle arm needs the VT-2005 sigma-profile artifact ---
if [ ! -f "${SIGMA_ARTIFACT}" ]; then
  echo "run_e5: missing VT-2005 oracle artifact ${SIGMA_ARTIFACT} — run scripts/data/ingest_vt2005_sigma_profiles.py first" >&2
  exit 1
fi

# --- Shared grounding args for the two grounded TGNN arms ---
# NOTE: any --set ... group must be LAST in the calling command (argparse nargs='*' is greedy).
COSMO_GROUND=(--sigma-train-data "${SIGMA_DIR}/sigma_train.csv" --sigma-val-data "${SIGMA_DIR}/sigma_val.csv" \
              --sigma-steps-per-epoch "${SIGMA_STEPS}" --sigma-warmup-epochs "${WARMUP_EPOCHS}" \
              --freeze-sigma-head-during-sle)

# --- Per-seed × per-arm loop ---
for SEED in ${SEEDS}; do
  SOUT="${OUT_DIR}/seed_${SEED}"; mkdir -p "${SOUT}"
  declare -a RUN_ARGS=()

  for arm in ${ARMS}; do
    ckpt="${CKPT_DIR}/${arm}_seed${SEED}.pt"
    pred="${SOUT}/${arm}_predictions.csv"
    echo "-- seed=${SEED}  arm=${arm}"

    # Arm-level resume: a finished arm (predictions written) is never retrained.
    if [ -f "${pred}" ]; then
      echo "   skip (predictions already exist: ${pred})"
      RUN_ARGS+=("--run" "${arm}=${pred}")
      continue
    fi

    # Mid-arm resume: continue a partial training checkpoint if present. Training args
    # for the heavy (TGNN/DirectGNN) arms; oracle is eval-only and ignores these.
    RESUME=()
    if [ -f "${ckpt}" ]; then echo "   resuming training from ${ckpt}"; RESUME=(--resume "${ckpt}"); fi
    CKPT_ARGS=(--checkpoint "${ckpt}" --checkpoint-every "${CHECKPOINT_EVERY}" "${RESUME[@]}")

    case "${arm}" in
      nrtl)
        "${PY}" scripts/train.py --config configs/paper_config_nrtl_h64L3.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" "${CKPT_ARGS[@]}" ${EXTRA_TRAIN_ARGS}
        "${PY}" scripts/analysis/export_checkpoint_predictions.py \
          --checkpoint "${ckpt}" --data "${TEST}" --output "${pred}" \
          --model-type tgnn --device "${DEVICE}" ;;
      directgnn)
        "${PY}" scripts/train_directgnn.py --config configs/paper_config_directgnn_h64L3.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" "${CKPT_ARGS[@]}"
        "${PY}" scripts/analysis/export_checkpoint_predictions.py \
          --checkpoint "${ckpt}" --data "${TEST}" --output "${pred}" \
          --model-type direct --device "${DEVICE}" ;;
      ungrounded)
        "${PY}" scripts/train.py --config configs/cosmo_sac.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" "${CKPT_ARGS[@]}" \
          --sigma-steps-per-epoch 0 --sigma-warmup-epochs 0 ${EXTRA_TRAIN_ARGS}
        "${PY}" scripts/analysis/export_checkpoint_predictions.py \
          --checkpoint "${ckpt}" --data "${TEST}" --output "${pred}" \
          --model-type tgnn --device "${DEVICE}" ;;
      grounded_a)
        "${PY}" scripts/train.py --config configs/cosmo_sac.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" "${CKPT_ARGS[@]}" \
          "${COSMO_GROUND[@]}" ${EXTRA_TRAIN_ARGS}
        "${PY}" scripts/analysis/export_checkpoint_predictions.py \
          --checkpoint "${ckpt}" --data "${TEST}" --output "${pred}" \
          --model-type tgnn --device "${DEVICE}" ;;
      grounded_b)
        # --set cosmo_sac_wire_volume=true must be LAST (argparse nargs='*' is greedy)
        "${PY}" scripts/train.py --config configs/cosmo_sac.yaml \
          --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
          --seed "${SEED}" --device "${DEVICE}" "${CKPT_ARGS[@]}" \
          "${COSMO_GROUND[@]}" ${EXTRA_TRAIN_ARGS} --set cosmo_sac_wire_volume=true
        "${PY}" scripts/analysis/export_checkpoint_predictions.py \
          --checkpoint "${ckpt}" --data "${TEST}" --output "${pred}" \
          --model-type tgnn --device "${DEVICE}" ;;
      oracle)
        # Reuse the grounded_a checkpoint; only the eval path changes (oracle sigma injection).
        # Measures the ceiling if the COSMO-SAC head had perfect sigma profiles.
        # Coverage ~5% of test rows (molecules with oracle profiles); rest are masked.
        # NOTE: comparison.json["per_arm"]["oracle"] is DILUTED (~grounded_a); the true
        # ceiling is the masked-subset block in this arm's *_predictions.summary.json.
        "${PY}" scripts/analysis/export_checkpoint_predictions.py \
          --checkpoint "${CKPT_DIR}/grounded_a_seed${SEED}.pt" \
          --data "${TEST}" --output "${pred}" \
          --model-type tgnn --device "${DEVICE}" \
          --sigma-oracle --sigma-oracle-side both \
          --sigma-artifact "${SIGMA_ARTIFACT}" ;;
    esac

    RUN_ARGS+=("--run" "${arm}=${pred}")
  done

  echo "== seed ${SEED}: running aggregator =="
  "${PY}" scripts/analysis/run_e5_comparison.py "${RUN_ARGS[@]}" \
    --direct-label directgnn --out-json "${SOUT}/comparison.json"
done

echo ""
echo "================================================================"
echo " run_e5 complete -> ${OUT_DIR}"
echo " Per-seed comparison.json written to seed_*/comparison.json."
echo " Aggregate across seeds for the decisive verdict."
echo "================================================================"
