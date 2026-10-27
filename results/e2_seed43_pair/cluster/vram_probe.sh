#!/bin/bash
# Пик VRAM СНАРУЖИ: src/ не правим (предзаявка seed43, ворота 6), поэтому пик снимается опросом.
# $1 = физический индекс карты, $2 = куда писать json, $3 = pid, за которым следить (его дерево)
set -u
IDX=$1; OUT=$2; WATCH=$3
PEAK=0; TOTAL=$(nvidia-smi -i "$IDX" --query-gpu=memory.total --format=csv,noheader,nounits | tr -d ' ')
while kill -0 "$WATCH" 2>/dev/null; do
  while read -r pid mem; do
    pid=${pid%,}; mem=${mem%% *}
    [ -r "/proc/$pid/cmdline" ] || continue
    tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q 'scripts/train.py' || continue
    [ "$mem" -gt "$PEAK" ] 2>/dev/null && PEAK=$mem
  done < <(nvidia-smi -i "$IDX" --query-compute-apps=pid,used_memory --format=csv,noheader,nounits)
  printf '{"device_index": %s, "peak_vram_mib": %s, "gpu_mem_total_mib": %s, "sampled_at": "%s"}\n' \
    "$IDX" "$PEAK" "$TOTAL" "$(date -Is)" > "$OUT"
  sleep 20
done
printf '{"device_index": %s, "peak_vram_mib": %s, "gpu_mem_total_mib": %s, "finished_at": "%s"}\n' \
  "$IDX" "$PEAK" "$TOTAL" "$(date -Is)" > "$OUT"
