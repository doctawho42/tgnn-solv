#!/bin/bash
# Та же величина (штраф за подстановку на solvent_only), но на парах ОДИН АРМ + ОДИН СИД +
# ОДИН КОММИТ, ДРУГОЙ УЗЕЛ. Нужна, потому что объявленная полоса 0.381..0.457 измерена на
# депонированном дереве (другой коммит И другая машина), а свежая полоса на gpu вышла
# 0.329..0.761. Пока эти две оси не разведены, неизвестно, чему принадлежит расширение.
#   control/seed42 (gpu, 0.7608)      против control_ripper3/seed42 и control_ripper3rep2/seed42
#   detached2_gpu/seed43 (0.4228)     против detached2_ripper3/seed43
set -u
B=/mnt/storage/doctawho42/tgnn-solv; R=$B/repo; PY=$B/env/bin/python
A=$B/sigma_arms; S=$B/read_a1
TEST=notebooks/data/processed/test.csv
ART=results/sigma_profile_artifact/sigma_profiles.csv
CARD="${1:-1}"
cd "$R" || exit 2
git diff --name-only c8c0213 HEAD -- src configs | grep . && { echo "src/configs разошлись -- стоп"; exit 2; }
export CUDA_VISIBLE_DEVICES="$CARD" KMP_DUPLICATE_LIB_OK=TRUE

for spec in ripper3_c42:42:control_ripper3/seed42 ripper3rep2_c42:42:control_ripper3rep2/seed42 ripper3_d43:43:detached2_ripper3/seed43; do
  lbl="${spec%%:*}"; rest="${spec#*:}"; seed="${rest%%:*}"; dir="${rest#*:}"
  out="$S/$lbl/seed_$seed"; mkdir -p "$out"
  ln -sf "$A/$dir/out/seed_$seed/grounded_a_predictions.csv" "$out/grounded_a_predictions.csv"
  if [ ! -s "$out/oracle_predictions.csv" ]; then
    echo "--- $lbl ($dir) сид $seed"
    "$PY" scripts/analysis/export_checkpoint_predictions.py \
      --checkpoint "$A/$dir/ckpt/grounded_a_seed$seed.pt" \
      --data "$TEST" --output "$out/oracle_predictions.csv.part" \
      --model-type tgnn --device cuda \
      --sigma-oracle --sigma-oracle-side both --sigma-artifact "$ART" \
      || { echo "ЭКСПОРТ УПАЛ: $lbl"; exit 3; }
    mv "$out/oracle_predictions.csv.part" "$out/oracle_predictions.csv"
  fi
  "$PY" scripts/analysis/run_paradox_channel_split.py \
    --root "$S/$lbl" --profiles "$ART" --out "$S/${lbl}_channel_split.json" >/dev/null \
    || echo "РАЗБИЕНИЕ УПАЛО: $lbl"
done
echo "DONE $(date -Is)"
