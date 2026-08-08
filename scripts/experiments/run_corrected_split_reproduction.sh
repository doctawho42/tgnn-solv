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
# Usage (GPU) — name the device, so a box whose CUDA broke stops instead of falling to CPU:
#   DEVICE=cuda bash scripts/experiments/run_corrected_split_reproduction.sh
# Nothing typed: --device is not passed and each child reads this box for itself.
# Cheaper smoke of the wiring (CPU, meaningless metrics — just checks it runs):
#   DEVICE=cpu EXTRA_TRAIN_ARGS="--hidden-dim 32 --n-gnn-layers 2 --epochs-phase1 1 --epochs-phase2 1 --epochs-phase3 1 --epochs 1" \
#     bash scripts/experiments/run_corrected_split_reproduction.sh
#
# Env overrides (defaults):
#   DEVICE            (unset)         torch device for training/export; see above
#   DATA_DIR          notebooks/data/processed       (the CORRECTED split)
#   TGNN_CONFIG       configs/paper_config_tuned.yaml
#   DIRECT_CONFIG     configs/paper_config_directgnn_tuned.yaml
#   OUT_DIR           results/corrected_split_reproduction
#   CKPT_DIR          checkpoints/corrected_split_reproduction
#   SEED              42
#   EXTRA_TRAIN_ARGS  ""              passed verbatim to BOTH training calls
#   SKIP_TRAIN        ""              set=1 to reuse existing checkpoints (analyses only)
#   RUN_E2            ""              set=1 to also run E2 crystal grounding (corrected pool)
#
# Exit status: 0 only if every step ran and succeeded. Any failed step -- including
# ones this script deliberately runs past to collect the rest -- exits 1. The summary
# prints a number only when the file carrying it was written after this run started;
# anything older is a leftover from a previous run and is withheld, not printed.
set -euo pipefail
cd "$(dirname "$0")/../.."
export KMP_DUPLICATE_LIB_OK=TRUE   # rdkit/torch/sklearn libomp clash on macOS

RUN_START="$(date +%s)"            # everything this run produces is newer than this

# DEVICE is a demand, not a default. Unset, --device is not passed at all and each child
# picks its own; set, the string reaches every child, where resolve_device refuses to
# substitute CPU for an accelerator you named -- which is the point of typing DEVICE=cuda
# on a GPU box. `DEVICE=cuda` used to be this line's default, and made a Mac with nothing
# typed die at the first train.py.
#
# "Its own" is not one answer here. train.py, train_directgnn.py and
# export_checkpoint_predictions.py read the box through default_device(); the two
# analysis steps below (run_uncertainty_calibration.py, run_encoder_linear_probe.py)
# default to a literal "cpu", so with DEVICE unset they stay on the CPU even where a GPU
# is present. Type DEVICE=cuda on a GPU box and all five follow it.
DEVICE="${DEVICE:-}"
DEV_ARGS=(); [ -n "${DEVICE}" ] && DEV_ARGS=(--device "${DEVICE}")
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
run_step() {  # run_step "name" cmd...  -> logs PASS/FAIL and runs on, but the failure is
              # carried to the exit status; the analyses below it are independent of it.
  local name="$1"; shift
  echo "── ${name}"
  if "$@"; then echo "   ok: ${name}"; else echo "   FAILED: ${name} (continuing)"; FAILED+=("${name}"); fi
}

require_fresh() {  # require_fresh path "what reads it"  -> abort unless THIS run wrote it
  local path="$1" consumers="$2"
  if [ ! -e "${path}" ]; then
    echo "ABORT: ${path} was not written -- ${consumers} have nothing to read." >&2
    exit 1
  fi
  if ! python -c 'import os,sys; sys.exit(0 if os.path.getmtime(sys.argv[1]) >= float(sys.argv[2]) else 1)' \
       "${path}" "${RUN_START}"; then
    echo "ABORT: ${path} is left over from an EARLIER run -- the step that writes it failed." >&2
    echo "       ${consumers} would read it, succeed, and report last run's checkpoint as this one's." >&2
    exit 1
  fi
}

echo "================================================================"
echo " Corrected-split reproduction"
echo "   device=${DEVICE:-per-script default (this box)}  data=${DATA_DIR}"
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
    ${DEV_ARGS[@]+"${DEV_ARGS[@]}"} --seed "${SEED}" \
    --checkpoint "${TGNN_CKPT}" --experiment-name corrected_tgnn ${EXTRA_TRAIN_ARGS}
  echo "── train DirectGNN control (${DIRECT_CONFIG})"
  python scripts/train_directgnn.py --config "${DIRECT_CONFIG}" \
    --train-data "${TRAIN}" --val-data "${VAL}" --test-data "${TEST}" \
    ${DEV_ARGS[@]+"${DEV_ARGS[@]}"} --seed "${SEED}" \
    --checkpoint "${DIRECT_CKPT}" --experiment-name corrected_direct ${EXTRA_TRAIN_ARGS}
else
  echo "   SKIP_TRAIN set -- reusing ${TGNN_CKPT} / ${DIRECT_CKPT}"
fi

# --- 2. Export row-level predictions (with physics intermediates) ---
run_step "export TGNN preds" python scripts/analysis/export_checkpoint_predictions.py \
  --checkpoint "${TGNN_CKPT}" --data "${TEST}" --output "${TGNN_PREDS}" --model-type tgnn ${DEV_ARGS[@]+"${DEV_ARGS[@]}"}
run_step "export DirectGNN preds" python scripts/analysis/export_checkpoint_predictions.py \
  --checkpoint "${DIRECT_CKPT}" --data "${TEST}" --output "${DIRECT_PREDS}" --model-type direct ${DEV_ARGS[@]+"${DEV_ARGS[@]}"}

# The exports are prerequisites, not independent steps: sections 3-4 read nothing but
# these two CSVs. A failed export leaves the previous run's file in place, so those
# sections would run to completion on stale rows. Stop here instead.
require_fresh "${TGNN_PREDS}"   "the decomposition / compensation / grounding / ranking / conformal steps"
require_fresh "${DIRECT_PREDS}" "the DirectGNN ranking step"

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
  --checkpoint "${TGNN_CKPT}" --model-type tgnn --test-data "${TEST}" ${DEV_ARGS[@]+"${DEV_ARGS[@]}"} \
  --out-json "${OUT_DIR}/uncertainty_tgnn.json"

# --- 5. Encoder transfer probe (is the encoder transfer- or expressivity-limited?) ---
run_step "encoder linear probe" python scripts/analysis/run_encoder_linear_probe.py \
  --checkpoint "${TGNN_CKPT}" --model-type tgnn --train-data "${TRAIN}" --test-data "${TEST}" \
  ${DEV_ARGS[@]+"${DEV_ARGS[@]}"} --out-json "${OUT_DIR}/encoder_probe.json"

# --- 6. Classical baseline ---
run_step "ideal-SLE baseline" python scripts/evaluation/run_ideal_sle_baseline.py \
  --test-data "${TEST}" --output-dir "${OUT_DIR}/ideal_sle_baseline"

# --- 7. (optional) E2 crystal grounding on the corrected external pool ---
if [ -n "${RUN_E2}" ]; then
  echo "── E2 crystal grounding (corrected open-crystal pool)"
  run_step "build crystal aux stream" python scripts/data/build_crystal_aux_stream.py \
    --exclude-scaffolds-from "${VAL}" "${TEST}"
  # DEVICE forwards as-is, empty included: E2 opens with the same `${DEVICE:-}`, which
  # reads an empty value and an unset one alike, so "nothing typed" survives the hop.
  ( DEVICE="${DEVICE}" DATA_DIR="${DATA_DIR}" OUT_DIR="${OUT_DIR}/e2" CKPT_DIR="${CKPT_DIR}/e2" \
      EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS}" bash scripts/experiments/run_e2_crystal_grounding.sh ) \
    || { echo "   FAILED: E2 (continuing)"; FAILED+=("E2"); }
fi

# --- 8. Headline summary ---
echo ""
echo "================================================================"
echo " SUMMARY"
echo "================================================================"
if ! python - "${RUN_START}" "${OUT_DIR}" <<'PY'
import json, sys, time
from pathlib import Path

run_start = float(sys.argv[1])
out = Path(sys.argv[2])
withheld = []

def load(p):
    """(payload, status). A file older than this run is a previous run's, so it is
    never parsed -- its numbers are not this reproduction's and must not be printed."""
    p = Path(p)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return {}, f"{p} does not exist"
    if mtime < run_start:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
        return {}, f"{p} was last written {when}, before this run started"
    try:
        return json.loads(p.read_text()), ""
    except Exception as exc:
        return {}, f"{p} could not be parsed ({type(exc).__name__})"

def g(d, *ks):
    for k in ks:
        if isinstance(d, dict) and k in d and d[k] is not None: return d[k]
    return "?"

def hold(label, why):
    withheld.append(label)
    print(f"  {label}: WITHHELD -- {why}")

for name, p in [("TGNN", "logs/corrected_tgnn/test_metrics.json"),
                ("DirectGNN", "logs/corrected_direct/test_metrics.json")]:
    m, why = load(p)
    if why: hold(f"{name} ln x2", why)
    else: print(f"  {name:10s} ln x2  MAE={g(m,'mae'):>7}  RMSE={g(m,'rmse'):>7}  R2={g(m,'r2'):>7}")
cg, why = load(out / "crystal_grounding.json")
if why: hold("crystal T_m grounding", why)
else:
    print(f"  crystal T_m grounding: MAE={g(cg,'Tm_mae_K')} K  bias={g(cg,'Tm_bias_K')} K  "
          f"skill={g(cg,'skill_over_mean')}  (Joback {g(cg,'joback_mae_K')} K, n={g(cg,'n_solutes')})")
dc, why = load(out / "decomposition_identifiability.json")
if why: hold("compensation", why)
else:
    print(f"  compensation: corr={g(dc,'corr_observed')}  perm-null={g(dc,'corr_permutation_null_mean')}  "
          f"delta_phi_mean={g(dc,'delta_phi_mean')}")
rt, why_t = load(out / "ranking_tgnn.json")
rd, why_d = load(out / "ranking_directgnn.json")
if why_t or why_d: hold("ranking Spearman", why_t or why_d)
else:
    print(f"  ranking Spearman: TGNN={g(rt,'spearman','spearman_mean')}  "
          f"DirectGNN={g(rd,'spearman','spearman_mean')}")

if withheld:
    print("")
    print(f"  {len(withheld)} line(s) withheld. A number is printed only when the file carrying it")
    print("  was written after this run started; the rest is an earlier run's and is not reported.")
PY
then
  echo "  (summary failed to run)"
  FAILED+=("summary")
fi
echo ""
echo "Outputs:"; ls -1 "${OUT_DIR}"/*.json 2>/dev/null || true
if [ "${#FAILED[@]}" -gt 0 ]; then
  echo ""
  echo "FAILED: ${#FAILED[@]} step(s) did not complete -- this run did NOT reproduce the corrected split:"
  printf '  - %s\n' "${FAILED[@]}"
  echo "Done (with failures)."
  exit 1
fi
echo "Done."
