#!/usr/bin/env bash
# E2 headline experiment: crystal grounding WITHOUT vs WITH the external pool.
#
# Tests the conditional-optimality claim (T3): grounding the crystal branch on a
# large external single-component T_m / dH_fus pool improves scaffold T_m
# extrapolation + decomposition quality, without hurting downstream ln x2.
#
# Two full-corpus runs differ ONLY by the crystal auxiliary stream. Everything
# downstream (export -> GC-reference compensation -> comparison) is reused from
# the existing analysis surface.
#
# Usage (when a GPU is available) — name the device, so a box whose CUDA broke stops
# instead of falling to CPU:
#   DEVICE=cuda bash scripts/experiments/run_e2_crystal_grounding.sh
# Nothing typed: --device is not passed and each child reads this box for itself.
#
# Env overrides (with defaults):
#   DEVICE              (unset)         torch device for training/export; see above
#   CONFIG              configs/physics_grounded.yaml
#   DATA_DIR           notebooks/data/processed
#   CRYSTAL_CSV        notebooks/data/processed_crystal_aux_stream/crystal_train.csv
#   CRYSTAL_STEPS      8               crystal aux batches per epoch (WITH run)
#   OUT_DIR            results/e2_crystal_grounding
#   CKPT_DIR           checkpoints/e2_crystal_grounding
#   EXTRA_TRAIN_ARGS   ""              passed verbatim to both train.py calls
#                                      (e.g. "--epochs-phase2 120" for a cheaper run)
set -euo pipefail
cd "$(dirname "$0")/../.."

# DEVICE is a demand, not a default. Unset, --device is not passed at all and each child
# reads this box through tgnn_solv.device.default_device(); set, the string reaches every
# child, where resolve_device refuses to substitute CPU for an accelerator you named --
# which is the point of typing DEVICE=cuda on a GPU box. `DEVICE=cuda` used to be this
# line's default, and made a Mac with nothing typed die at the first train.py.
DEVICE="${DEVICE:-}"
DEV_ARGS=(); [ -n "${DEVICE}" ] && DEV_ARGS=(--device "${DEVICE}")
CONFIG="${CONFIG:-configs/physics_grounded.yaml}"
DATA_DIR="${DATA_DIR:-notebooks/data/processed}"
CRYSTAL_CSV="${CRYSTAL_CSV:-notebooks/data/processed_crystal_aux_stream/crystal_train.csv}"
CRYSTAL_STEPS="${CRYSTAL_STEPS:-8}"
OUT_DIR="${OUT_DIR:-results/e2_crystal_grounding}"
CKPT_DIR="${CKPT_DIR:-checkpoints/e2_crystal_grounding}"
EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS:-}"

TRAIN="${DATA_DIR}/train.csv"
VAL="${DATA_DIR}/val.csv"
TEST="${DATA_DIR}/test.csv"

mkdir -p "${OUT_DIR}" "${CKPT_DIR}"
echo "== E2 crystal grounding =="
echo "   device=${DEVICE:-per-script default (this box)} config=${CONFIG} crystal_steps=${CRYSTAL_STEPS}"
echo "   out=${OUT_DIR} ckpt=${CKPT_DIR}"

# --- 0. Build the external crystal aux stream (scaffold-leak-guarded) if absent ---
if [[ ! -f "${CRYSTAL_CSV}" ]]; then
  echo "== [0/5] building external crystal aux stream =="
  python scripts/data/build_crystal_aux_stream.py \
    --output-csv "${CRYSTAL_CSV}" \
    --exclude-scaffolds-from "${TEST}" "${VAL}"
fi

# --- 1. Train WITHOUT crystal grounding (control) ---
WITHOUT_CKPT="${CKPT_DIR}/physics_grounded_without_crystal.pt"
echo "== [1/5] train WITHOUT crystal pool =="
python scripts/train.py \
  --config "${CONFIG}" \
  --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
  --checkpoint "${WITHOUT_CKPT}" ${DEV_ARGS[@]+"${DEV_ARGS[@]}"} \
  --crystal-steps-per-epoch 0 \
  ${EXTRA_TRAIN_ARGS}

# --- 2. Train WITH crystal grounding (only difference: the aux stream) ---
WITH_CKPT="${CKPT_DIR}/physics_grounded_with_crystal.pt"
echo "== [2/5] train WITH crystal pool =="
python scripts/train.py \
  --config "${CONFIG}" \
  --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
  --checkpoint "${WITH_CKPT}" ${DEV_ARGS[@]+"${DEV_ARGS[@]}"} \
  --crystal-train-data "${CRYSTAL_CSV}" --crystal-steps-per-epoch "${CRYSTAL_STEPS}" \
  ${EXTRA_TRAIN_ARGS}

# --- 3. Export row-level predictions (with crystal intermediates) on the test set ---
WITHOUT_PRED="${OUT_DIR}/without/predictions.csv"
WITH_PRED="${OUT_DIR}/with/predictions.csv"
echo "== [3/5] export predictions =="
python scripts/analysis/export_checkpoint_predictions.py \
  --checkpoint "${WITHOUT_CKPT}" --data "${TEST}" \
  --output "${WITHOUT_PRED}" --model-type tgnn ${DEV_ARGS[@]+"${DEV_ARGS[@]}"}
python scripts/analysis/export_checkpoint_predictions.py \
  --checkpoint "${WITH_CKPT}" --data "${TEST}" \
  --output "${WITH_PRED}" --model-type tgnn ${DEV_ARGS[@]+"${DEV_ARGS[@]}"}

# --- 4. Robust GC-reference compensation per run ---
echo "== [4/5] GC-reference compensation =="
python scripts/analysis/run_gc_reference_compensation.py \
  --predictions-csv "${WITHOUT_PRED}" --label without_crystal \
  --out-json "${OUT_DIR}/without/gc_compensation.json"
python scripts/analysis/run_gc_reference_compensation.py \
  --predictions-csv "${WITH_PRED}" --label with_crystal \
  --out-json "${OUT_DIR}/with/gc_compensation.json"

# --- 5. Headline comparison (T3) + scaffold-distance error structure ---
echo "== [5/5] headline comparison =="
python scripts/analysis/run_e2_crystal_grounding_comparison.py \
  --without-csv "${WITHOUT_PRED}" --with-csv "${WITH_PRED}" \
  --train-data "${TRAIN}" \
  --out-json "${OUT_DIR}/comparison.json"

python scripts/analysis/scaffold_distance_error_analysis.py \
  --train "${TRAIN}" --test-predictions "${WITH_PRED}" \
  --output-dir "${OUT_DIR}/with/scaffold_distance" || true
python scripts/analysis/scaffold_distance_error_analysis.py \
  --train "${TRAIN}" --test-predictions "${WITHOUT_PRED}" \
  --output-dir "${OUT_DIR}/without/scaffold_distance" || true

echo "== E2 done. Headline table: ${OUT_DIR}/comparison.json =="
