#!/bin/bash
# Сертификационный арм: grounded_a сид 42, полный конфиг, на общей карте.
# Критерий сертификации объявлен ДО запуска: results/cluster_certification/PRE_DECLARATION.md
set -u
BASE=/mnt/storage/doctawho42/tgnn-solv
R=$BASE/repo; PY=$BASE/env/bin/python; CERT=$BASE/certification
cd "$R"
ulimit -n 65536
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-2}
export KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src

echo "=== ГЕЙТ перед тратой (обучение не стартует при провале) ==="
if ! $PY scripts/cluster/gpu_gate.py --json-out "$CERT/gate.json"; then
  echo "ГЕЙТ ПРОВАЛЕН -- обучение НЕ запускается"; exit 1
fi

echo; echo "=== соседство на карте в момент старта (печатается, а не замалчивается) ==="
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv,noheader | sed 's|/mnt/storage/doctawho42/|~/|'

echo; echo "=== старт: $(date -Is) ==="
START=$(date +%s)
PY=$PY DEVICE=cuda SEEDS=42 ARMS=grounded_a \
  OUT_DIR=$CERT/out CKPT_DIR=$CERT/ckpt \
  bash scripts/experiments/run_e5_sigma_grounding.sh
RC=$?
END=$(date +%s)
echo "=== финиш: $(date -Is), настенное время $(( (END-START)/60 )) мин, код $RC ==="
echo "=== соседство на финише ==="
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
exit $RC
