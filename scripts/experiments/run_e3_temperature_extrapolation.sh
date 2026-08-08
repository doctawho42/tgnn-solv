#!/usr/bin/env bash
# E3: same-pair temperature extrapolation (tests T4 -- structured analytic curve
# beats an unstructured T-encoder outside the training temperature range).
#
# Protocol: build same-pair low-T train/val + high-T test, run the classical
# baselines (pair van't Hoff, pair linear-T, RF(Morgan+T), pair mean/last), then
# train the structured physics curve and DirectGNN on the SAME low-T split and
# evaluate on the high-T rows. Aggregate into one leaderboard.
#
# Usage (GPU): DEVICE=cuda bash scripts/experiments/run_e3_temperature_extrapolation.sh
# Naming the device is what makes a box whose CUDA broke stop rather than fall to CPU.
# Nothing typed: --device is not passed and each child reads this box for itself.
#
# Env overrides (defaults):
#   DEVICE             (unset)    see above
#   PHYSICS_CONFIG     configs/physics_grounded.yaml
#   DIRECT_CONFIG      configs/paper_config_directgnn_tuned.yaml
#   DATA_DIR           notebooks/data/processed
#   TRAIN_MAX_K        310        low-T train/val ceiling
#   TEST_MIN_K         330        high-T test floor
#   OUT_DIR            results/e3_temperature
#   CKPT_DIR           checkpoints/e3_temperature
#   PHYSICS_EXTRA      ""         extra args to physics train.py (e.g. crystal grounding)
#   EXTRA_TRAIN_ARGS   ""         extra args to BOTH train scripts (e.g. --epochs-phase2 120)
set -euo pipefail
cd "$(dirname "$0")/../.."

# DEVICE is a demand, not a default. Unset, --device is not passed at all and each child
# reads this box through tgnn_solv.device.default_device(); set, the string reaches every
# child, where resolve_device refuses to substitute CPU for an accelerator you named --
# which is the point of typing DEVICE=cuda on a GPU box. `DEVICE=cuda` used to be this
# line's default, and made a Mac with nothing typed die at the first train.py.
DEVICE="${DEVICE:-}"
DEV_ARGS=(); [ -n "${DEVICE}" ] && DEV_ARGS=(--device "${DEVICE}")
PHYSICS_CONFIG="${PHYSICS_CONFIG:-configs/physics_grounded.yaml}"
DIRECT_CONFIG="${DIRECT_CONFIG:-configs/paper_config_directgnn_tuned.yaml}"
DATA_DIR="${DATA_DIR:-notebooks/data/processed}"
TRAIN_MAX_K="${TRAIN_MAX_K:-310}"
TEST_MIN_K="${TEST_MIN_K:-330}"
OUT_DIR="${OUT_DIR:-results/e3_temperature}"
CKPT_DIR="${CKPT_DIR:-checkpoints/e3_temperature}"
PHYSICS_EXTRA="${PHYSICS_EXTRA:-}"
EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS:-}"

BASE_DIR="${OUT_DIR}/baselines"
SPLITS="${BASE_DIR}/splits"
mkdir -p "${OUT_DIR}" "${CKPT_DIR}"

echo "== E3 temperature extrapolation =="
echo "   device=${DEVICE:-per-script default (this box)} train_max_k=${TRAIN_MAX_K} test_min_k=${TEST_MIN_K}"

# --- 1. Build same-pair low/high split + classical baselines ---
echo "== [1/5] temperature split + classical baselines =="
python scripts/evaluation/run_temperature_extrapolation_baselines.py \
  --processed-dir "${DATA_DIR}" \
  --out-dir "${BASE_DIR}" \
  --train-max-k "${TRAIN_MAX_K}" --test-min-k "${TEST_MIN_K}" \
  --no-presentation-copy

TRAIN_LOW="${SPLITS}/train_low.csv"
VAL_LOW="${SPLITS}/val_low.csv"
TEST_HIGH="${SPLITS}/test_high.csv"

# --- 2. Train the structured physics analytic curve on the low-T split ---
PHYS_CKPT="${CKPT_DIR}/physics_temp.pt"
echo "== [2/5] train physics analytic curve =="
python scripts/train.py \
  --config "${PHYSICS_CONFIG}" \
  --train-data "${TRAIN_LOW}" --val-data "${VAL_LOW}" --test-data "${TEST_HIGH}" \
  --checkpoint "${PHYS_CKPT}" ${DEV_ARGS[@]+"${DEV_ARGS[@]}"} \
  ${PHYSICS_EXTRA} ${EXTRA_TRAIN_ARGS}

# --- 3. Train DirectGNN (unstructured T-encoder) on the same split ---
DIRECT_CKPT="${CKPT_DIR}/directgnn_temp.pt"
echo "== [3/5] train DirectGNN =="
python scripts/train_directgnn.py \
  --config "${DIRECT_CONFIG}" \
  --train-data "${TRAIN_LOW}" --val-data "${VAL_LOW}" --test-data "${TEST_HIGH}" \
  --checkpoint "${DIRECT_CKPT}" ${DEV_ARGS[@]+"${DEV_ARGS[@]}"} \
  ${EXTRA_TRAIN_ARGS}

# --- 4. Export high-T predictions + van't Hoff slope fidelity ---
echo "== [4/5] export high-T predictions =="
PHYS_PRED="${OUT_DIR}/physics/predictions.csv"
DIRECT_PRED="${OUT_DIR}/directgnn/predictions.csv"
python scripts/analysis/export_checkpoint_predictions.py \
  --checkpoint "${PHYS_CKPT}" --data "${TEST_HIGH}" \
  --output "${PHYS_PRED}" --model-type tgnn ${DEV_ARGS[@]+"${DEV_ARGS[@]}"}
python scripts/analysis/export_checkpoint_predictions.py \
  --checkpoint "${DIRECT_CKPT}" --data "${TEST_HIGH}" \
  --output "${DIRECT_PRED}" --model-type direct ${DEV_ARGS[@]+"${DEV_ARGS[@]}"}

python scripts/analysis/check_vant_hoff_slopes.py \
  --predictions "${PHYS_PRED}" \
  --output-dir "${OUT_DIR}/physics/vant_hoff" || true

# --- 5. Leaderboard (classical + physics + DirectGNN) ---
echo "== [5/5] leaderboard =="
python scripts/analysis/run_e3_temperature_comparison.py \
  --baselines-metrics "${BASE_DIR}/metrics_by_model.csv" \
  --physics-summary "${OUT_DIR}/physics/predictions.summary.json" \
  --directgnn-summary "${OUT_DIR}/directgnn/predictions.summary.json" \
  --vant-hoff-metrics "${OUT_DIR}/physics/vant_hoff/metrics_by_model.csv" \
  --out-json "${OUT_DIR}/leaderboard.json"

echo "== E3 done. Leaderboard: ${OUT_DIR}/leaderboard.json =="
