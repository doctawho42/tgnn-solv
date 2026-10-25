#!/bin/bash
# Переобученный арм при cosmo_sac_sigma_hb = 0.012, затем развёртка с ЗАКРЕПЛЁННЫМ источником.
# Правило и ворота: results/sigma_hb_retrained/PRE_DECLARATION.md
set -u
B=/mnt/storage/doctawho42/tgnn-solv; R=$B/repo; PY=$B/env/bin/python; O=$B/retrained
cd "$R"; ulimit -n 65536
export CUDA_VISIBLE_DEVICES=0 KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src

echo "=== ГЕЙТ перед тратой ==="
$PY scripts/cluster/gpu_gate.py --json-out $O/gate.json || { echo "ГЕЙТ ПРОВАЛЕН -- не запускаюсь"; exit 1; }

echo; echo "=== соседство на старте ==="
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader

echo; echo "=== ОБУЧЕНИЕ при sigma_hb = 0.012, старт $(date -Is) ==="
S=$(date +%s)
PY=$PY DEVICE=cuda SEEDS=42 ARMS=grounded_a \
  OUT_DIR=$O/out CKPT_DIR=$O/ckpt \
  EXTRA_TRAIN_ARGS="--set cosmo_sac_sigma_hb=0.012" \
  bash scripts/experiments/run_e5_sigma_grounding.sh
RC=$?
E=$(date +%s)
echo "=== обучение кончило, код $RC, настенное $(( (E-S)/60 )) мин ==="
[ $RC -ne 0 ] && { echo "обучение упало -- развёртку не запускаю"; exit $RC; }

echo; echo "=== проверка: какой sigma_hb в чекпойнте ==="
$PY - <<'PYC'
import torch
from pathlib import Path
import os
ck = sorted(Path(os.environ["HOME"] if False else "/mnt/storage/doctawho42/tgnn-solv/retrained/ckpt").glob("grounded_a_seed42.pt"))
d = torch.load(ck[0], map_location="cpu", weights_only=False)
c = d.get("config") or d.get("cfg")
v = getattr(c, "cosmo_sac_sigma_hb", None) if not isinstance(c, dict) else c.get("cosmo_sac_sigma_hb")
print("  sigma_hb в чекпойнте =", v)
assert abs(float(v) - 0.012) < 1e-9, "ЧЕКПОЙНТ ОБУЧЕН НЕ ПРИ ТОМ ПОРОГЕ"
print("  верно")
PYC
[ $? -ne 0 ] && { echo "чекпойнт не тот -- развёртку не запускаю"; exit 3; }

echo; echo "=== РАЗВЁРТКА, источник закреплён на |k| <= 8 ==="
$PY scripts/analysis/run_sigma_core_boundary_sweep.py \
    --ckpt-dir $O/ckpt --arm-glob 'grounded_a_seed42.pt' --core-k 8 \
    --out $O/sweep 2>&1 | grep -vE "train:|it/s|Dataset:"
echo "########## ПЕРЕОБУЧЕННЫЙ АРМ ЗАВЕРШЁН ##########"
