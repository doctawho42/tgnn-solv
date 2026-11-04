#!/bin/bash
# A1 для detached2: штраф за подстановку на строках solvent_only, по ОБЕИМ базам.
#
# Правило: results/sigma_arms/PRE_DECLARATION.md, раздел A1. Пороги 0.381/0.457 измерены на
# ДЕПОНИРОВАННОМ плече (опубликованное дерево e5, посидово 0.456/0.381/0.457, среднее +0.431).
# Это другой коммит, а память проекта запрещает смешанные эстиманды, поэтому штраф считается
# ТАКЖЕ на свежем контроле этой же тройки, и вердикт читается на обеих базах -- как круг 2
# сделал для A2.
#
# Инструмент -- scripts/analysis/run_paradox_channel_split.py. Он несёт СВОЙ нуль: на строках
# класса neither не подставляется ничего, и два экспорта одного чекпойнта обязаны совпасть там
# до ~1e-6. Расхождение означает, что различаются условия экспорта, а не плечи.
#
# Подстановка делается side=both, ровно как плечо `oracle` драйвера e5; класс строки (кому
# эталон достался) считает сам скрипт по правилу самой подстановки.
set -u
B=/mnt/storage/doctawho42/tgnn-solv; R=$B/repo; PY=$B/env/bin/python
A=$B/sigma_arms; S=$B/read_a1
TEST=notebooks/data/processed/test.csv
ART=results/sigma_profile_artifact/sigma_profiles.csv
CARD="${1:-1}"
cd "$R" || exit 2

echo "=== ГЕЙТ КОДА ==="
git diff --name-only c8c0213 HEAD -- src configs | grep . && { echo "src/configs разошлись с c8c0213 -- экспорт НЕ идёт"; exit 2; }
git status --porcelain src/ scripts/ configs/ | grep . && { echo "дерево грязное -- экспорт НЕ идёт"; exit 2; }
echo "src/configs совпадают с c8c0213, дерево чисто, HEAD=$(git rev-parse --short HEAD)"
echo "карта $CARD:"; nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv,noheader -i "$CARD"

export CUDA_VISIBLE_DEVICES="$CARD"
export KMP_DUPLICATE_LIB_OK=TRUE

for spec in control:42:control/seed42 control:43:control/seed43 control:44:control/seed44 \
            detached2:42:detached2/seed42 detached2:43:detached2_gpu/seed43 detached2:44:detached2_gpu/seed44; do
  arm="${spec%%:*}"; rest="${spec#*:}"; seed="${rest%%:*}"; dir="${rest#*:}"
  out="$S/$arm/seed_$seed"; mkdir -p "$out"
  ln -sf "$A/$dir/out/seed_$seed/grounded_a_predictions.csv" "$out/grounded_a_predictions.csv"
  if [ -s "$out/oracle_predictions.csv" ]; then
    echo "--- $arm сид $seed: подстановка уже выгружена, пропуск (идемпотентно)"
    continue
  fi
  echo "--- $arm сид $seed ($dir): экспорт с подстановкой"
  T0=$(date +%s)
  "$PY" scripts/analysis/export_checkpoint_predictions.py \
    --checkpoint "$A/$dir/ckpt/grounded_a_seed$seed.pt" \
    --data "$TEST" --output "$out/oracle_predictions.csv.part" \
    --model-type tgnn --device cuda \
    --sigma-oracle --sigma-oracle-side both --sigma-artifact "$ART" \
    || { echo "ЭКСПОРТ УПАЛ: $arm сид $seed"; exit 3; }
  mv "$out/oracle_predictions.csv.part" "$out/oracle_predictions.csv"
  echo "    $(( $(date +%s) - T0 )) с"
done

for arm in control detached2; do
  echo; echo "=== РАЗБИЕНИЕ ПО КЛАССАМ СТРОК: $arm ==="
  "$PY" scripts/analysis/run_paradox_channel_split.py \
    --root "$S/$arm" --profiles "$ART" --out "$S/${arm}_channel_split.json" \
    || echo "РАЗБИЕНИЕ УПАЛО: $arm"
done
echo; echo "=== КОНЕЦ $(date -Is) ==="
