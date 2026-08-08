#!/usr/bin/env bash
# E4: ablate the identifiability closers from the full grounded model.
#
# The full model grounds the crystal branch (external pool + GC priors) and
# stop-grads Phi into the activity residual. Each ablation removes ONE closer;
# a closer "matters" if removing it worsens crystal T_m MAE and/or the
# decomposition (|delta_phi_mean|), ideally without improving ln x2 (which would
# just be compensation). This is the empirical side of the A-optimality story.
#
# Usage (GPU): DEVICE=cuda bash scripts/experiments/run_e4_ablations.sh
# Naming the device is what makes a box whose CUDA broke stop rather than fall to CPU.
# Nothing typed: --device is not passed and each child reads this box for itself.
#
# Env overrides (defaults):
#   DEVICE            (unset)   see above
#   CONFIG            configs/physics_grounded.yaml
#   DATA_DIR          notebooks/data/processed
#   CRYSTAL_CSV       notebooks/data/processed_crystal_aux_stream/crystal_train.csv
#   CRYSTAL_STEPS     8
#   OUT_DIR           results/e4_ablations
#   CKPT_DIR          checkpoints/e4_ablations
#   ABLATIONS         "full no_external_crystal no_gc_priors no_stopgrad"
#                     (add with_unifac to also test the activity prior)
#   EXTRA_TRAIN_ARGS  ""   passed to every train.py (e.g. --epochs-phase2 120)
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
OUT_DIR="${OUT_DIR:-results/e4_ablations}"
CKPT_DIR="${CKPT_DIR:-checkpoints/e4_ablations}"
ABLATIONS="${ABLATIONS:-full no_external_crystal no_gc_priors no_stopgrad}"
EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS:-}"

TRAIN="${DATA_DIR}/train.csv"
VAL="${DATA_DIR}/val.csv"
TEST="${DATA_DIR}/test.csv"
mkdir -p "${OUT_DIR}" "${CKPT_DIR}"
echo "== E4 ablations =="
echo "   device=${DEVICE:-per-script default (this box)} config=${CONFIG} ablations=${ABLATIONS}"

CRYSTAL_ON="--crystal-train-data ${CRYSTAL_CSV} --crystal-steps-per-epoch ${CRYSTAL_STEPS}"
CRYSTAL_OFF="--crystal-steps-per-epoch 0"

# Per-label extra args. NOTE: any `--set ...` group must be LAST in the command
# (argparse nargs='*' is greedy), so train.py is called as:
#   ... <EXTRA_TRAIN_ARGS> <ablation extra ending in --set ...>
ablation_args() {
  case "$1" in
    full)                echo "${CRYSTAL_ON}" ;;
    no_external_crystal) echo "${CRYSTAL_OFF}" ;;
    no_gc_priors)        echo "${CRYSTAL_ON} --set use_gc_priors_crystal=false" ;;
    no_stopgrad)         echo "${CRYSTAL_ON} --set detach_crystal_params_in_sle=false detach_crystal_from_encoder=false" ;;
    with_unifac)         echo "${CRYSTAL_ON} --set use_unifac_gamma_prior=true" ;;
    *) echo "__UNKNOWN__" ;;
  esac
}

# Build the crystal aux stream once if needed.
if [[ ! -f "${CRYSTAL_CSV}" ]]; then
  echo "== building external crystal aux stream =="
  python scripts/data/build_crystal_aux_stream.py \
    --output-csv "${CRYSTAL_CSV}" --exclude-scaffolds-from "${TEST}" "${VAL}"
fi

RUN_ARGS=()
for label in ${ABLATIONS}; do
  extra="$(ablation_args "${label}")"
  if [[ "${extra}" == "__UNKNOWN__" ]]; then
    echo "!! unknown ablation '${label}', skipping"; continue
  fi
  ckpt="${CKPT_DIR}/${label}.pt"
  pred="${OUT_DIR}/${label}/predictions.csv"
  echo "== ablation: ${label}  (${extra}) =="
  python scripts/train.py \
    --config "${CONFIG}" \
    --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
    --checkpoint "${ckpt}" ${DEV_ARGS[@]+"${DEV_ARGS[@]}"} \
    ${EXTRA_TRAIN_ARGS} ${extra}
  python scripts/analysis/export_checkpoint_predictions.py \
    --checkpoint "${ckpt}" --data "${TEST}" \
    --output "${pred}" --model-type tgnn ${DEV_ARGS[@]+"${DEV_ARGS[@]}"}
  RUN_ARGS+=("--run" "${label}=${pred}")
done

echo "== ablation summary =="
python scripts/analysis/run_e4_ablation_summary.py \
  "${RUN_ARGS[@]}" \
  --reference-label full \
  --out-json "${OUT_DIR}/ablation_summary.json"

echo "== E4 done. Summary: ${OUT_DIR}/ablation_summary.json =="
