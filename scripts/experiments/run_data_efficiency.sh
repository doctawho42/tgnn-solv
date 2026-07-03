#!/usr/bin/env bash
# Data-efficiency sweep: does physics grounding beat the black box in the
# LOW-DATA regime? (The strongest scientific claim of the project.)
#
# For each training-data fraction we subsample the train split BY SOLUTE (fewer
# distinct molecules = the regime that matters for scaffold transfer), train the
# physics-grounded model (external crystal pool) and DirectGNN on the SAME
# subsample, evaluate on the FIXED scaffold test, and aggregate accuracy +
# ranking vs fraction. Physics should win at small fractions even if it ties at 1.0.
#
# Usage (GPU): DEVICE=cuda bash scripts/experiments/run_data_efficiency.sh
#
# Env (defaults):
#   DEVICE cuda ; FRACS "0.05 0.1 0.25 0.5 1.0" ; SEED 42
#   PHYSICS_CONFIG configs/physics_grounded.yaml ; DIRECT_CONFIG configs/paper_config_directgnn_tuned.yaml
#   DATA_DIR notebooks/data/processed ; CRYSTAL_CSV notebooks/data/processed_crystal_aux_stream/crystal_train.csv
#   CRYSTAL_STEPS 8 ; OUT_DIR results/data_efficiency ; CKPT_DIR checkpoints/data_efficiency
#   EXTRA_TRAIN_ARGS "" (e.g. "--epochs-phase2 120" for a cheaper curve)
set -euo pipefail
cd "$(dirname "$0")/../.."

DEVICE="${DEVICE:-cuda}"
FRACS="${FRACS:-0.05 0.1 0.25 0.5 1.0}"
SEED="${SEED:-42}"
PHYSICS_CONFIG="${PHYSICS_CONFIG:-configs/physics_grounded.yaml}"
DIRECT_CONFIG="${DIRECT_CONFIG:-configs/paper_config_directgnn_tuned.yaml}"
DATA_DIR="${DATA_DIR:-notebooks/data/processed}"
CRYSTAL_CSV="${CRYSTAL_CSV:-notebooks/data/processed_crystal_aux_stream/crystal_train.csv}"
CRYSTAL_STEPS="${CRYSTAL_STEPS:-8}"
OUT_DIR="${OUT_DIR:-results/data_efficiency}"
CKPT_DIR="${CKPT_DIR:-checkpoints/data_efficiency}"
EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS:-}"

VAL="${DATA_DIR}/val.csv"; TEST="${DATA_DIR}/test.csv"
mkdir -p "${OUT_DIR}/data" "${CKPT_DIR}"
ENTRIES=()

for FRAC in ${FRACS}; do
  TRAIN_SUB="${OUT_DIR}/data/train_f${FRAC}.csv"
  echo "== fraction ${FRAC}: subsample train by solute =="
  python - "$DATA_DIR/train.csv" "$FRAC" "$SEED" "$TRAIN_SUB" <<'PY'
import sys, pandas as pd
inp, frac, seed, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
df = pd.read_csv(inp, low_memory=False)
sol = pd.Series(df["solute_smiles"].dropna().unique())
keep = set(sol.sample(frac=frac, random_state=seed)) if frac < 1.0 else set(sol)
df[df["solute_smiles"].isin(keep)].to_csv(out, index=False)
print(f"   solutes {len(keep)}/{len(sol)}, rows {int(df['solute_smiles'].isin(keep).sum())}/{len(df)}")
PY

  for MODEL in physics direct; do
    RUN_DIR="${OUT_DIR}/${MODEL}/frac_${FRAC}"; mkdir -p "${RUN_DIR}"
    CKPT="${CKPT_DIR}/${MODEL}_f${FRAC}.pt"
    PRED="${RUN_DIR}/pred.csv"
    echo "== fraction ${FRAC}: train ${MODEL} =="
    if [[ "${MODEL}" == "physics" ]]; then
      python scripts/train.py --config "${PHYSICS_CONFIG}" \
        --train-data "${TRAIN_SUB}" --val-data "${VAL}" --test-data "${TEST}" \
        --checkpoint "${CKPT}" --device "${DEVICE}" \
        --crystal-train-data "${CRYSTAL_CSV}" --crystal-steps-per-epoch "${CRYSTAL_STEPS}" \
        ${EXTRA_TRAIN_ARGS}
      MT="tgnn"
    else
      python scripts/train_directgnn.py --config "${DIRECT_CONFIG}" \
        --train-data "${TRAIN_SUB}" --val-data "${VAL}" --test-data "${TEST}" \
        --checkpoint "${CKPT}" --device "${DEVICE}" ${EXTRA_TRAIN_ARGS}
      MT="direct"
    fi
    python scripts/analysis/export_checkpoint_predictions.py \
      --checkpoint "${CKPT}" --data "${TEST}" --output "${PRED}" \
      --model-type "${MT}" --device "${DEVICE}"
    python scripts/analysis/run_ranking_eval.py \
      --predictions-csv "${PRED}" --out-json "${RUN_DIR}/rank.json" || true
    ENTRIES+=("--entry" "${MODEL}:${FRAC}:${PRED%.csv}.summary.json:${RUN_DIR}/rank.json")
  done
done

echo "== aggregate data-efficiency curve =="
python scripts/analysis/run_data_efficiency_summary.py \
  "${ENTRIES[@]}" --out-json "${OUT_DIR}/summary.json"
echo "== done: ${OUT_DIR}/summary.json =="
