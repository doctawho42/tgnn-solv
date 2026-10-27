#!/bin/bash
# Сид 43, арм grounded_a_detachencoder, карта 1. Правило и ворота: results/e2_seed43_pair/PRE_DECLARATION.md
# КОД ДЕРЕВА НЕ ОБНОВЛЯЛСЯ: 78ec0cfe83, тот же, что у армов сида 42 (ворота 6).
set -u
B=/mnt/storage/doctawho42/tgnn-solv; R=$B/repo; PY=$B/env/bin/python; D=$B/seed43/detachencoder
mkdir -p "$D"
cd "$R"; ulimit -n 65536
export CUDA_VISIBLE_DEVICES=2 KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src

echo "=== ВОРОТА 6: коммит дерева ==="
H=$(git rev-parse HEAD)
echo "  HEAD = $H"
if [ "${H:0:10}" != "78ec0cfe83" ]; then echo "  РАСХОЖДЕНИЕ с армами сида 42 -- НЕ ЗАПУСКАЮСЬ"; exit 2; fi

echo "=== ГЕЙТ GPU ==="
$PY scripts/cluster/gpu_gate.py --json-out "$D/gate.json" || { echo "ГЕЙТ ПРОВАЛЕН -- обучение НЕ стартует"; exit 1; }

echo; echo "=== соседство на старте (печатается, а не замалчивается) ==="
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv,noheader | sed 's|/mnt/storage/doctawho42/|~/|'

bash $B/seed43/vram_probe.sh 2 "$D/vram.json" $$ &
PROBE=$!

echo; echo "=== ОБУЧЕНИЕ grounded_a_detachencoder, сид 43, старт $(date -Is) ==="
S=$(date +%s)
PY=$PY DEVICE=cuda SEEDS=43 ARMS=grounded_a_detachencoder OUT_DIR=$D/out CKPT_DIR=$D/ckpt \
  bash scripts/experiments/run_e5_sigma_grounding.sh
RC=$?
E=$(date +%s)
kill $PROBE 2>/dev/null
echo "=== кончило, код $RC, настенное $(( (E-S)/60 )) мин ==="
cat "$D/vram.json" 2>/dev/null
echo "########## grounded_a_detachencoder СИД 43 ЗАВЕРШЕНО код $RC ##########"
exit $RC
