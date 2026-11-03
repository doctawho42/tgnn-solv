#!/bin/bash
# Одно плечо σ-промежуточного, один сид, одна карта.
#   bash run_arm.sh {control|detached|roleinv} <seed> <card>
#
# Правило чтения и пороги: results/sigma_arms/PRE_DECLARATION.md
#
# ТРИ ПЛЕЧА, А НЕ ДВА. Референсные чекпойнты обучены на другом коммите (и, для августовских, на
# другой машине), а память проекта фиксирует, что разница версий НЕ РАЗРЕШЕНА и на одном сиде
# переворачивается. Поэтому контроль обучается заново, здесь же и на том же коммите, и сравнение
# идёт внутри одной тройки.
#
# ЗАМОК. Запуск обучения НЕ идемпотентен: обёртка с повтором уже однажды стартовала в этом проекте
# два плеча ЧЕТЫРЕ раза. Каталог прогона создаётся атомарным mkdir и служит замком; trap снимает
# его только если он пуст, то есть если обучение так и не начало ничего писать.
set -u

ARM="${1:?плечо: control|detached|detached2|roleinv}"
SEED="${2:?сид}"
CARD="${3:?номер карты}"
# Необязательная метка каталога. Нужна, когда то же плечо и тот же сид запускаются на ДРУГОЙ
# машине: архитектура карты и версия драйвера есть своя ось, и прогон-зонд обязан лежать отдельно
# от прогона записи, а не затирать его и не упираться в его замок.
TAG="${4:-}"

B=/mnt/storage/doctawho42/tgnn-solv; R=$B/repo; PY=$B/env/bin/python
# Объявленный коммит КОДА. Ворота ниже проверяют не равенство HEAD (коммит не может знать свой
# хеш, и правки в results/ или paper/ код не меняют), а что src/, scripts/ и configs/ НЕ ОТЛИЧАЮТСЯ
# от него и что он является предком HEAD. Так все три плеча гарантированно идут одним кодом.
# ПЕРЕОБЪЯВЛЕНО 2026-11-03 с 75ce246 на 4d62f94. Два изменения обучающего пути: Phase 3
# выключена (epochs_phase3 0, причина и измерение -- в комментарии configs/cosmo_sac.yaml),
# и состояние её входа депонируется явно. Всё, обученное отсюда, идёт ДРУГОЙ версией кода,
# чем десять завершённых прогонов в sigma_arms/ и два, что шли на момент правки, а память
# проекта держит версионную разницу НЕРАЗРЕШЁННОЙ: на одном сиде она переворачивается.
# Поэтому следующее сравнение -- новая тройка целиком, и смешивать её с тем, что уже лежит
# здесь, нельзя. Какой коммит нёс каждый прогон, записано в его provenance.json.
WANT_COMMIT=4d62f94

case "$ARM" in
  control)  EXTRA="" ;;
  detached) EXTRA="--set sigma_detached_from_closure=true" ;;
  # Исправленная конструкция: профиль недостижим для градиента цели, но ядро сегментной
  # активности обучаемо -- то есть "дообучать только выходную голову Г". Ранг 1 по прецеденту
  # results/fix_g. См. поправку в PRE_DECLARATION.md от 2026-11-01.
  detached2) EXTRA="--set sigma_detached_from_closure=true --set cosmo_sac_kernel_residual_rank=1" ;;
  roleinv)  EXTRA="--set sigma_role_invariant=true" ;;
  *) echo "неизвестное плечо: $ARM"; exit 3 ;;
esac

D=$B/sigma_arms/${ARM}${TAG:+_$TAG}/seed$SEED
mkdir -p "$(dirname "$D")"
if ! mkdir "$D" 2>/dev/null; then
  echo "каталог $D уже существует -- НЕ ЗАПУСКАЮСЬ (повтор обёртки или прерванный прогон)"
  exit 4
fi
trap 'rmdir "$D" 2>/dev/null' EXIT

cd "$R"; ulimit -n 65536
export CUDA_VISIBLE_DEVICES="$CARD" KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src

echo "=== ВОРОТА: коммит дерева ==="
H=$(git rev-parse HEAD)
echo "  HEAD = $H, объявленный код = $WANT_COMMIT"
if ! git merge-base --is-ancestor "$WANT_COMMIT" HEAD 2>/dev/null; then
  echo "  объявленный коммит НЕ предок HEAD -- НЕ ЗАПУСКАЮСЬ"; exit 2
fi
# ЖЁСТКО: обучающий путь. Сопоставимость плеч держится на src/ и configs/, и расхождение здесь
# останавливает запуск.
DIFF=$(git diff --name-only "$WANT_COMMIT" HEAD -- src configs)
if [ -n "$DIFF" ]; then
  echo "  ОБУЧАЮЩИЙ КОД ОТЛИЧАЕТСЯ от объявленного -- НЕ ЗАПУСКАЮСЬ:"; echo "$DIFF" | head -5
  exit 2
fi
# МЯГКО: аналитика. Она обучение не меняет и при чтении всё равно запускается одним коммитом, но
# расхождение ПЕЧАТАЕТСЯ, а не исчезает: полный HEAD уходит в provenance.json.
ADIFF=$(git diff --name-only "$WANT_COMMIT" HEAD -- scripts)
if [ -n "$ADIFF" ]; then
  echo "  аналитика разошлась с объявленным (на обучение не влияет, записано в provenance):"
  echo "$ADIFF" | sed "s/^/    /" | head -6
fi
if [ -n "$(git status --porcelain src/ scripts/ configs/)" ]; then
  echo "  ДЕРЕВО ГРЯЗНОЕ в src/scripts/configs -- НЕ ЗАПУСКАЮСЬ"
  git status --porcelain src/ scripts/ configs/ | head -5
  exit 2
fi

echo "=== ГЕЙТ GPU ==="
$PY scripts/cluster/gpu_gate.py --json-out "$D/gate.json" || {
  echo "ГЕЙТ ПРОВАЛЕН -- обучение НЕ стартует"; exit 1; }

echo; echo "=== соседство на старте (печатается, а не замалчивается) ==="
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv,noheader \
  | sed 's|/mnt/storage/doctawho42/|~/|'

cat > "$D/provenance.json" <<EOF
{"arm": "$ARM", "tag": "${TAG:-}", "host": "$(hostname)",
 "gpu": "$(nvidia-smi --query-gpu=name --format=csv,noheader -i "$CARD" | head -1)",
 "driver": "$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)",
 "seed": $SEED, "card": "$CARD", "commit": "$H",
 "extra_train_args": "$EXTRA", "started_at": "$(date -Is)",
 "python": "$($PY -c 'import sys,torch;print(sys.version.split()[0]+" torch "+torch.__version__)')",
 "rule": "results/sigma_arms/PRE_DECLARATION.md"}
EOF

[ -f "$B/seed43/vram_probe.sh" ] && { bash "$B/seed43/vram_probe.sh" "$CARD" "$D/vram.json" $$ & PROBE=$!; }

echo; echo "=== ОБУЧЕНИЕ плечо=$ARM${TAG:+ метка=$TAG} сид=$SEED карта=$CARD узел=$(hostname) старт $(date -Is) ==="
echo "    EXTRA_TRAIN_ARGS=[$EXTRA]"
S=$(date +%s)
PY=$PY DEVICE=cuda SEEDS="$SEED" ARMS=grounded_a OUT_DIR="$D/out" CKPT_DIR="$D/ckpt" \
  EXTRA_TRAIN_ARGS="$EXTRA" bash scripts/experiments/run_e5_sigma_grounding.sh
RC=$?
E=$(date +%s)
[ -n "${PROBE:-}" ] && kill $PROBE 2>/dev/null

echo "=== кончило, код $RC, настенное $(( (E-S)/60 )) мин ==="
cat "$D/vram.json" 2>/dev/null
echo "########## $ARM СИД $SEED ЗАВЕРШЕНО код $RC ##########"
exit $RC
