#!/usr/bin/env bash
# E2 crystal grounding at a PROPER dose (referee M4b).
#
# The headline crystal-grounding null (sections/crystal-null.tex) was dose-limited: at the
# selected early best-val checkpoint the model had seen the ~15.4k-row melting-point pool
# LESS THAN ONE full pass, at a low auxiliary loss weight. This wrapper raises the dose so
# the crystal stream is genuinely exercised, then re-runs the identical E2 without-vs-with
# comparison. If the ceiling still does not move at a proper dose, the null is no longer
# dose-limited and the "external crystal labels do not help" reading is earned; if it does
# move, the paper must say so.
#
# Dose (vs the homeopathic run):
#   * CRYSTAL_STEPS 8 -> 48  (~6x aux batches/epoch: with batch 64 and 200 phase-2 epochs
#     that is >=4 passes over the pool even by epoch 20, vs ~0.66 before)
#   * crystal-aux loss weight (unset/low) -> 1.0 across all three phases
#
# Usage (GPU):
#   DEVICE=cuda bash scripts/experiments/run_e2_crystal_grounding_dosed.sh
# CPU smoke (wiring only, NO meaningful metrics):
#   DEVICE=cpu CRYSTAL_STEPS=2 \
#     EXTRA_TRAIN_ARGS="--epochs-phase1 1 --epochs-phase2 1 --epochs-phase3 1" \
#     OUT_DIR results/e2_crystal_dosed_smoke CKPT_DIR checkpoints/e2_crystal_dosed_smoke \
#     bash scripts/experiments/run_e2_crystal_grounding_dosed.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

export CRYSTAL_STEPS="${CRYSTAL_STEPS:-48}"
export OUT_DIR="${OUT_DIR:-results/e2_crystal_grounding_dosed}"
export CKPT_DIR="${CKPT_DIR:-checkpoints/e2_crystal_grounding_dosed}"
# Unit crystal-aux loss weight across all phases, appended to any caller-supplied args.
export EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS:-} --set crystal_aux_phase1_weight=1.0 --set crystal_aux_phase2_weight=1.0 --set crystal_aux_phase3_weight=1.0"

echo "== E2 crystal grounding (DOSED, referee M4b): CRYSTAL_STEPS=${CRYSTAL_STEPS}, unit aux weight =="
echo "   out=${OUT_DIR} ckpt=${CKPT_DIR}"
exec bash scripts/experiments/run_e2_crystal_grounding.sh
