#!/usr/bin/env bash
# Reproduce the full proxy + DirectGNN comparison and all orphaned analyses on the
# CORRECTED (post-+273-K-T_m-fix) solute_scaffold split, in one GPU run.
#
# The data fix + fresh re-split orphaned every prior checkpoint/result (old split,
# corrupted T_m). This regenerates paper-grade numbers on the corrected split:
# trains the physics model (TGNNSolv) and the DirectGNN control with the SAME
# recipe, exports predictions, and re-runs the analysis surface (decomposition /
# compensation / crystal grounding / ranking / uncertainty / encoder probe /
# baselines).
#
# Usage (GPU):
#   DEVICE=cuda bash scripts/experiments/run_corrected_split_reproduction.sh
# Cheaper smoke of the wiring (CPU, meaningless metrics — just checks it runs):
#   DEVICE=cpu EXTRA_TRAIN_ARGS="--hidden-dim 32 --n-gnn-layers 2 --epochs-phase1 1 --epochs-phase2 1 --epochs-phase3 1 --epochs 1" \
#     bash scripts/experiments/run_corrected_split_reproduction.sh
#
# Env overrides (defaults):
#   DEVICE            cuda            torch device for training/export
#   DATA_DIR          notebooks/data/processed       (the CORRECTED split)
#   TGNN_CONFIG       configs/paper_config_tuned.yaml
#   DIRECT_CONFIG     configs/paper_config_directgnn_tuned.yaml
#   OUT_DIR           results/corrected_split_reproduction
#   CKPT_DIR          checkpoints/corrected_split_reproduction
#   SEED              42
#   EXTRA_TRAIN_ARGS  ""              passed verbatim to BOTH training calls
#   SKIP_TRAIN        ""              set=1 to reuse existing checkpoints (analyses only)
#   RUN_E2            ""              set=1 to also run E2 crystal grounding (corrected pool)
set -euo pipefail
cd "$(dirname "$0")/../.."
export KMP_DUPLICATE_LIB_OK=TRUE   # rdkit/torch/sklearn libomp clash on macOS

DEVICE="${DEVICE:-cuda}"
DATA_DIR="${DATA_DIR:-notebooks/data/processed}"
TGNN_CONFIG="${TGNN_CONFIG:-configs/paper_config_tuned.yaml}"
DIRECT_CONFIG="${DIRECT_CONFIG:-configs/paper_config_directgnn_tuned.yaml}"
OUT_DIR="${OUT_DIR:-results/corrected_split_reproduction}"
CKPT_DIR="${CKPT_DIR:-checkpoints/corrected_split_reproduction}"
SEED="${SEED:-42}"
EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS:-}"
SKIP_TRAIN="${SKIP_TRAIN:-}"
RUN_E2="${RUN_E2:-}"

TRAIN="${DATA_DIR}/train.csv"; VAL="${DATA_DIR}/val.csv"; TEST="${DATA_DIR}/test.csv"
TGNN_CKPT="${CKPT_DIR}/tgnn_proxy.pt"
DIRECT_CKPT="${CKPT_DIR}/directgnn.pt"
TGNN_PREDS="${OUT_DIR}/tgnn_test_predictions.csv"
DIRECT_PREDS="${OUT_DIR}/directgnn_test_predictions.csv"
mkdir -p "${OUT_DIR}" "${CKPT_DIR}"

declare -a FAILED=()
run_step() {  # run_step "name" cmd...  -> logs PASS/FAIL, never aborts the script
  local name="$1"; shift
  echo "── ${name}"
  if "$@"; then echo "   ok: ${name}"; else echo "   FAILED: ${name} (continuing)"; FAILED+=("${name}"); fi
}

echo "================================================================"
echo " Corrected-split reproduction"
echo "   device=${DEVICE}  data=${DATA_DIR}"
echo "   out=${OUT_DIR}  ckpt=${CKPT_DIR}  seed=${SEED}"
echo "================================================================"

# --- 0. Guard: refuse to run on corrupted (+273 K) T_m labels ---
python - "$TEST" <<'PY'
import sys, pandas as pd
d = pd.read_csv(sys.argv[1], low_memory=False)
tm = pd.to_numeric(d["T_m"], errors="coerce")
if "has_T_m" in d.columns:
    tm = tm[d["has_T_m"].astype(str).str.lower().isin({"true", "1", "1.0"})]
med = float(tm.median())
print(f"   test T_m median = {med:.1f} K", "(corrected)" if med < 560 else "(!! CORRUPTED)")
assert med < 560, "T_m looks +273 K corrupted -- run prepare_data with the fixed loader first."
PY

# --- 1. Train TGNNSolv (physics) + DirectGNN (control) on the SAME corrected split ---
if [ -z "${SKIP_TRAIN}" ]; then
  echo "── train TGNNSolv proxy (${TGNN_CONFIG})"
  python scripts/train.py --config "${TGNN_CONFIG}" \
    --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
    --device "${DEVICE}" --seed "${SEED}" \
    --checkpoint "${TGNN_CKPT}" --experiment-name corrected_tgnn ${EXTRA_TRAIN_ARGS}
  echo "── train DirectGNN control (${DIRECT_CONFIG})"
  python scripts/train_directgnn.py --config "${DIRECT_CONFIG}" \
    --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
    --device "${DEVICE}" --seed "${SEED}" \
    --checkpoint "${DIRECT_CKPT}" --experiment-name corrected_direct ${EXTRA_TRAIN_ARGS}
else
  echo "   SKIP_TRAIN set -- reusing ${TGNN_CKPT} / ${DIRECT_CKPT}"
fi

# --- 2. Export row-level predictions (with physics intermediates) ---
run_step "export TGNN preds" python scripts/analysis/export_checkpoint_predictions.py \
  --checkpoint "${TGNN_CKPT}" --data "${TEST}" --output "${TGNN_PREDS}" --model-type tgnn --device "${DEVICE}"
run_step "export DirectGNN preds" python scripts/analysis/export_checkpoint_predictions.py \
  --checkpoint "${DIRECT_CKPT}" --data "${TEST}" --output "${DIRECT_PREDS}" --model-type direct --device "${DEVICE}"

# --- 3. Decomposition / compensation / crystal grounding (TGNN only) ---
run_step "decomposition-identifiability" python scripts/analysis/run_decomposition_identifiability.py \
  --predictions-csv "${TGNN_PREDS}" --out-json "${OUT_DIR}/decomposition_identifiability.json"
run_step "gc-reference compensation" python scripts/analysis/run_gc_reference_compensation.py \
  --predictions-csv "${TGNN_PREDS}" --out-json "${OUT_DIR}/gc_reference_summary.json"
run_step "crystal T_m grounding" python scripts/analysis/run_crystal_grounding.py \
  --predictions-csv "${TGNN_PREDS}" --out-json "${OUT_DIR}/crystal_grounding.json"

# --- 4. Ranking (both) + calibrated uncertainty (TGNN) ---
run_step "ranking TGNN" python scripts/analysis/run_ranking_eval.py \
  --predictions-csv "${TGNN_PREDS}" --out-json "${OUT_DIR}/ranking_tgnn.json"
run_step "ranking DirectGNN" python scripts/analysis/run_ranking_eval.py \
  --predictions-csv "${DIRECT_PREDS}" --out-json "${OUT_DIR}/ranking_directgnn.json"
run_step "conformal calibration" python scripts/analysis/run_conformal_calibration.py \
  --predictions-csv "${TGNN_PREDS}" --out-json "${OUT_DIR}/conformal_tgnn.json"
run_step "uncertainty (MC-dropout)" python scripts/analysis/run_uncertainty_calibration.py \
  --checkpoint "${TGNN_CKPT}" --model-type tgnn --test-data "${TEST}" --device "${DEVICE}" \
  --out-json "${OUT_DIR}/uncertainty_tgnn.json"

# --- 5. Encoder transfer probe (is the encoder transfer- or expressivity-limited?) ---
run_step "encoder linear probe" python scripts/analysis/run_encoder_linear_probe.py \
  --checkpoint "${TGNN_CKPT}" --model-type tgnn --train-data "${TRAIN}" --test-data "${TEST}" \
  --device "${DEVICE}" --out-json "${OUT_DIR}/encoder_probe.json"

# --- 6. Classical baseline ---
run_step "ideal-SLE baseline" python scripts/evaluation/run_ideal_sle_baseline.py \
  --test-data "${TEST}" --output-dir "${OUT_DIR}/ideal_sle_baseline"

# --- 7. (optional) E2 crystal grounding on the corrected external pool ---
if [ -n "${RUN_E2}" ]; then
  echo "── E2 crystal grounding (corrected open-crystal pool)"
  run_step "build crystal aux stream" python scripts/data/build_crystal_aux_stream.py \
    --exclude-scaffolds-from "${VAL}" "${TEST}"
  ( DEVICE="${DEVICE}" DATA_DIR="${DATA_DIR}" OUT_DIR="${OUT_DIR}/e2" CKPT_DIR="${CKPT_DIR}/e2" \
      EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS}" bash scripts/experiments/run_e2_crystal_grounding.sh ) \
    || { echo "   FAILED: E2 (continuing)"; FAILED+=("E2"); }
fi

# --- 8. Headline summary ---
echo ""
echo "================================================================"
echo " SUMMARY"
echo "================================================================"
python - "${OUT_DIR}" <<'PY' || true
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
def load(p):
    try: return json.loads(Path(p).read_text())
    except Exception: return {}
def g(d, *ks):
    for k in ks:
        if isinstance(d, dict) and k in d and d[k] is not None: return d[k]
    return "?"
for name, p in [("TGNN", "logs/corrected_tgnn/test_metrics.json"),
                ("DirectGNN", "logs/corrected_direct/test_metrics.json")]:
    m = load(p)
    print(f"  {name:10s} ln x2  MAE={g(m,'mae'):>7}  RMSE={g(m,'rmse'):>7}  R2={g(m,'r2'):>7}")
cg = load(out / "crystal_grounding.json")
print(f"  crystal T_m grounding: MAE={g(cg,'Tm_mae_K')} K  bias={g(cg,'Tm_bias_K')} K  "
      f"skill={g(cg,'skill_over_mean')}  (Joback {g(cg,'joback_mae_K')} K, n={g(cg,'n_solutes')})")
dc = load(out / "decomposition_identifiability.json")
print(f"  compensation: corr={g(dc,'corr_observed')}  perm-null={g(dc,'corr_permutation_null_mean')}  "
      f"delta_phi_mean={g(dc,'delta_phi_mean')}")
rt, rd = load(out / "ranking_tgnn.json"), load(out / "ranking_directgnn.json")
print(f"  ranking Spearman: TGNN={g(rt,'spearman','spearman_mean')}  DirectGNN={g(rd,'spearman','spearman_mean')}")
PY
echo ""
echo "Outputs:"; ls -1 "${OUT_DIR}"/*.json 2>/dev/null || true
if [ "${#FAILED[@]}" -gt 0 ]; then
  echo ""
  echo "WARN: ${#FAILED[@]} analysis step(s) failed (independent; training/exports above are unaffected):"
  printf '  - %s\n' "${FAILED[@]}"
fi
echo "Done."
