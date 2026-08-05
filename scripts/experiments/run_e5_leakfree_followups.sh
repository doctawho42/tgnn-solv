#!/usr/bin/env bash
# The readings the leak-free re-run needs BESIDES the two training arms, in the order
# a referee asked for them. Nothing here trains a model from scratch; every step is an
# inference pass or an audit over deposited artifacts, so all of it runs on a laptop
# once the compute host's outputs are fetched.
#
# WHAT MUST COME BACK FROM THE COMPUTE HOST FIRST
#   results/e5_sigma_grounding_leakfree/seed_*/     per-row predictions, comparison.json
#   checkpoints/e5_leakfree/                        the .pt files AND the .manifest.json
#                                                   files beside them -- the manifests are
#                                                   what carry the stream hash beside the
#                                                   split hashes, and they are written to
#                                                   the checkpoint directory, not to the
#                                                   results directory
#   notebooks/data/processed_sigma_aux_stream_clean/sigma_train.csv
#                                                   the stream build the runs actually
#                                                   consumed, so the leak check can be
#                                                   recomputed here rather than trusted
#
# STEPS
#   1  provenance certificate: one split, one stream build, one 5608-row lock, both arms,
#      every seed, with per-seed MAE printed (referee 1a/1b, referee 2 items 1 and 2)
#   2  per-row deposit audit: complete files, no non-finite prediction, summaries recompute
#   3  the evaluation-only substitution on the clean checkpoints (referee 1c, referee 2
#      item 3) -- eval only, reuses each grounded_a checkpoint, then re-aggregates so the
#      per-seed comparison.json carries all three arms on one lock
#   4  the n=44 profile probe on the clean checkpoints with piperidine removed
#
# READ BEFORE QUOTING STEP 4 AGAINST THE PUBLISHED PROBE. The 51+/-2% departure and the
# 4.1+/-0.5x transfer ratio of Sec. 3.3 were measured on a DIFFERENT set of three runs --
# the sigma head left UNFROZEN through fine-tuning -- and those checkpoints were not
# retained. The arms here carry --freeze-sigma-head-during-sle, the schedule of the
# headline arms. So step 4 measures the departure on leak-free checkpoints of the
# headline schedule, which is what referee 2's item 3 asks for and what the SI concedes
# was never measured; it does NOT reproduce 51+/-2% or 4.1+/-0.5x, and a number from it
# must not be set against those two. Reproducing THOSE needs the unfrozen schedule
# retrained on the clean stream, which is a GPU pass and is not in this script.
#
# The co-adaptation control at five seeds (referee 1d) is NOT here: it is a training arm
# (grounded_a_truetrain) and needs the GPU. Queue it with
#   SEEDS="42 43 44 45 46" ARMS="grounded_a_truetrain" SIGMA_DIR=... OUT_DIR=... CKPT_DIR=... \
#     bash scripts/experiments/run_e5_sigma_grounding.sh
# on the same stream build, or the +0.18 stays a single seed.
set -euo pipefail
cd "$(dirname "$0")/../.."
export KMP_DUPLICATE_LIB_OK=TRUE
export PYTHONPATH="${PYTHONPATH:-}:src"

PY="${PY:-$HOME/anaconda3/envs/tgnn-solv/bin/python}"
OUT_DIR="${OUT_DIR:-results/e5_sigma_grounding_leakfree}"
CKPT_DIR="${CKPT_DIR:-checkpoints/e5_leakfree}"
SEEDS="${SEEDS:-42 43 44 45 46}"
STREAM_CSV="${STREAM_CSV:-notebooks/data/processed_sigma_aux_stream_clean/sigma_train.csv}"
SIGMA_ARTIFACT="${SIGMA_ARTIFACT:-results/sigma_profile_artifact/sigma_profiles.csv}"
MATCHED_CSV="${MATCHED_CSV:-results/b_insuff/matched_pairs.csv}"
DEVICE="${DEVICE:-cpu}"
# The one molecule a correct guard would have removed from the n=44 matched set.
LEAK_MOLECULE="${LEAK_MOLECULE:-C1CCNCC1}"

echo "== 1. provenance certificate =="
"${PY}" scripts/analysis/certify_leakfree_rerun.py \
  --results-root "${OUT_DIR}" --manifest-root "${CKPT_DIR}" \
  --seeds ${SEEDS} --stream-csv "${STREAM_CSV}" \
  --report "${OUT_DIR}/provenance_certificate.json"

echo "== 2. per-row deposit audit =="
"${PY}" scripts/analysis/verify_perrow_deposit.py --root "${OUT_DIR}" \
  --json "${OUT_DIR}/perrow_deposit_audit.json"

echo "== 3. evaluation-only substitution on the clean checkpoints =="
for SEED in ${SEEDS}; do
  SOUT="${OUT_DIR}/seed_${SEED}"
  pred="${SOUT}/oracle_predictions.csv"
  if [ -f "${pred}" ]; then
    echo "   seed ${SEED}: oracle predictions already exist, skipping export"
  else
    "${PY}" scripts/analysis/export_checkpoint_predictions.py \
      --checkpoint "${CKPT_DIR}/grounded_a_seed${SEED}.pt" \
      --data notebooks/data/processed/test.csv --output "${pred}" \
      --model-type tgnn --device "${DEVICE}" \
      --sigma-oracle --sigma-oracle-side both --sigma-artifact "${SIGMA_ARTIFACT}"
  fi
  "${PY}" scripts/analysis/run_e5_comparison.py \
    --run "ungrounded=${SOUT}/ungrounded_predictions.csv" \
    --run "grounded_a=${SOUT}/grounded_a_predictions.csv" \
    --run "oracle=${pred}" \
    --direct-label grounded_a --out-json "${SOUT}/comparison.json"
done

echo "== 4. n=44 profile probe, piperidine removed =="
for SEED in ${SEEDS}; do
  "${PY}" scripts/analysis/run_compensation_surrogate.py \
    --checkpoint "${CKPT_DIR}/grounded_a_seed${SEED}.pt" \
    --sigma-profiles "${SIGMA_ARTIFACT}" --matched-csv "${MATCHED_CSV}" \
    --device "${DEVICE}" --exclude-smiles "${LEAK_MOLECULE}" \
    --out-json "${OUT_DIR}/seed_${SEED}/surrogate_noleak.json" \
    --fig-dir "${OUT_DIR}/seed_${SEED}/figs"
done

echo ""
echo "done. The certificate is ${OUT_DIR}/provenance_certificate.json; it is the file that"
echo "answers 'which build fed which arm', and it exits non-zero if it cannot."
