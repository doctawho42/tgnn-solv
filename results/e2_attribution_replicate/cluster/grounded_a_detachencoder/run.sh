#!/bin/bash
# Репликат контроля атрибуции: плечо grounded_a_detachencoder, сид 42, карта 2.
# Правило и ворота: results/e2_attribution_replicate/PRE_DECLARATION.md
set -u
B=/mnt/storage/doctawho42/tgnn-solv; R=$B/repo; PY=$B/env/bin/python; D=/mnt/storage/doctawho42/tgnn-solv/replicate/grounded_a_detachencoder
cd "$R"; ulimit -n 65536
export CUDA_VISIBLE_DEVICES=2 KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src
echo "=== ГЕЙТ ==="
$PY scripts/cluster/gpu_gate.py --json-out $D/gate.json || { echo "ГЕЙТ ПРОВАЛЕН"; exit 1; }
echo; echo "=== соседство на старте ==="
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
echo; echo "=== ОБУЧЕНИЕ grounded_a_detachencoder, старт $(date -Is) ==="
S=$(date +%s)
PY=$PY DEVICE=cuda SEEDS=42 ARMS=grounded_a_detachencoder OUT_DIR=$D/out CKPT_DIR=$D/ckpt \
  bash scripts/experiments/run_e5_sigma_grounding.sh
RC=$?
E=$(date +%s)
echo "=== кончило, код $RC, настенное $(( (E-S)/60 )) мин ==="
echo "########## grounded_a_detachencoder ЗАВЕРШЕНО ##########"
exit $RC
