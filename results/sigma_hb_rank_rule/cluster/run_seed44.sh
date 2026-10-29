#!/bin/bash
# Переобученный арм при cosmo_sac_sigma_hb = 0.012, сид 44, карта 1.
# Правило, пол и мощность: results/sigma_hb_rank_rule/PRE_DECLARATION.md
# Поправка 1 той же предзаявки: развёртка всех трёх переобученных сидов идёт ОДНОЙ версией скрипта.
set -u
B=/mnt/storage/doctawho42/tgnn-solv; R=$B/repo; PY=$B/env/bin/python; O=$B/hbrank/seed44
mkdir -p "$O"

# АТОМАРНЫЙ ЗАМОК. 2026-10-27: первый запуск этих армов ушёл ЧЕТЫРЕ раза, потому что драйвер был
# обёрнут в цикл повторов, написанный для ЧТЕНИЙ: связь рвалась ПОСЛЕ старта, ssh возвращал ошибку,
# цикл запускал заново, а setsid оставлял предыдущий жить. Четыре пары писали в одни каталоги.
# mkdir атомарен, поэтому второй экземпляр проиграет гонку и выйдет, а не испортит прогон.
if ! mkdir "$O/.lock" 2>/dev/null; then
  echo "УЖЕ ЗАПУЩЕН: есть $O/.lock -- второй экземпляр НЕ стартует."
  echo "Если прошлый прогон убит жёстко, снимите замок вручную: rmdir $O/.lock"
  exit 4
fi
trap 'rmdir "$O/.lock" 2>/dev/null' EXIT
cd "$R"; ulimit -n 65536
export CUDA_VISIBLE_DEVICES=1 KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src

echo "=== ВОРОТА 4: код и железо ==="
H=$(git rev-parse HEAD); echo "  HEAD = $H"
[ "${H:0:10}" = "78ec0cfe83" ] || { echo "  РАСХОЖДЕНИЕ с опорным семейством -- НЕ ЗАПУСКАЮСЬ"; exit 2; }

echo "=== ГЕЙТ GPU ==="
$PY scripts/cluster/gpu_gate.py --json-out "$O/gate.json" || { echo "ГЕЙТ ПРОВАЛЕН"; exit 1; }
grep -o '"gpu_name": "[^"]*"' "$O/gate.json" | sed 's/^/  /'

echo; echo "=== соседство на старте (печатается, а не замалчивается) ==="
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader

bash $B/seed43/vram_probe.sh 1 "$O/vram.json" $$ &
PROBE=$!

echo; echo "=== ОБУЧЕНИЕ sigma_hb = 0.012, сид 44, старт $(date -Is) ==="
S=$(date +%s)
PY=$PY DEVICE=cuda SEEDS=44 ARMS=grounded_a OUT_DIR=$O/out CKPT_DIR=$O/ckpt \
  EXTRA_TRAIN_ARGS="--set cosmo_sac_sigma_hb=0.012" \
  bash scripts/experiments/run_e5_sigma_grounding.sh
RC=$?
E=$(date +%s)
kill $PROBE 2>/dev/null
echo "=== обучение кончило, код $RC, настенное $(( (E-S)/60 )) мин ==="
cat "$O/vram.json" 2>/dev/null
[ $RC -ne 0 ] && { echo "обучение упало -- развёртку не запускаю"; exit $RC; }

echo; echo "=== ВОРОТА: тот ли порог в чекпойнте ==="
$PY - <<'PYC'
import torch
from pathlib import Path
ck = sorted(Path("/mnt/storage/doctawho42/tgnn-solv/hbrank/seed44/ckpt").glob("grounded_a_seed44.pt"))
d = torch.load(ck[0], map_location="cpu", weights_only=False)
c = d.get("config") or d.get("cfg")
v = getattr(c, "cosmo_sac_sigma_hb", None) if not isinstance(c, dict) else c.get("cosmo_sac_sigma_hb")
print("  sigma_hb в чекпойнте =", v, " сид =", d.get("seed"))
assert abs(float(v) - 0.012) < 1e-9, "ЧЕКПОЙНТ ОБУЧЕН НЕ ПРИ ТОМ ПОРОГЕ"
assert int(d.get("seed", -1)) == 44, "СИД НЕ ТОТ"
print("  верно")
PYC
[ $? -ne 0 ] && { echo "чекпойнт не тот -- развёртку не запускаю"; exit 3; }

echo; echo "=== РАЗВЁРТКА, источник закреплён --core-k 8 ==="
cp $B/retrained/sweep/locked_solvents.csv "$O/sweep_lock.csv" 2>/dev/null || true
$PY scripts/analysis/run_sigma_core_boundary_sweep.py \
    --ckpt-dir $O/ckpt --arm-glob 'grounded_a_seed44.pt' --core-k 8 \
    --out $O/sweep 2>&1 | grep -vE "train:|it/s|Dataset:"
echo "########## СИД 44 ПРИ 0.012 ЗАВЕРШЁН ##########"
