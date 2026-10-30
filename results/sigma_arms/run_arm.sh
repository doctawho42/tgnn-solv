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

ARM="${1:?плечо: control|detached|roleinv}"
SEED="${2:?сид}"
CARD="${3:?номер карты}"

B=/mnt/storage/doctawho42/tgnn-solv; R=$B/repo; PY=$B/env/bin/python
# Объявленный коммит КОДА. Ворота ниже проверяют не равенство HEAD (коммит не может знать свой
# хеш, и правки в results/ или paper/ код не меняют), а что src/, scripts/ и configs/ НЕ ОТЛИЧАЮТСЯ
# от него и что он является предком HEAD. Так все три плеча гарантированно идут одним кодом.
WANT_COMMIT=75ce246

case "$ARM" in
  control)  EXTRA="" ;;
  detached) EXTRA="--set sigma_detached_from_closure=true" ;;
  roleinv)  EXTRA="--set sigma_role_invariant=true" ;;
  *) echo "неизвестное плечо: $ARM"; exit 3 ;;
esac

D=$B/sigma_arms/$ARM/seed$SEED
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
DIFF=$(git diff --name-only "$WANT_COMMIT" HEAD -- src scripts configs)
if [ -n "$DIFF" ]; then
  echo "  КОД ОТЛИЧАЕТСЯ от объявленного -- НЕ ЗАПУСКАЮСЬ:"; echo "$DIFF" | head -5; exit 2
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
{"arm": "$ARM", "seed": $SEED, "card": "$CARD", "commit": "$H",
 "extra_train_args": "$EXTRA", "started_at": "$(date -Is)",
 "python": "$($PY -c 'import sys,torch;print(sys.version.split()[0]+" torch "+torch.__version__)')",
 "rule": "results/sigma_arms/PRE_DECLARATION.md"}
EOF

[ -f "$B/seed43/vram_probe.sh" ] && { bash "$B/seed43/vram_probe.sh" "$CARD" "$D/vram.json" $$ & PROBE=$!; }

echo; echo "=== ОБУЧЕНИЕ плечо=$ARM сид=$SEED карта=$CARD старт $(date -Is) ==="
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
