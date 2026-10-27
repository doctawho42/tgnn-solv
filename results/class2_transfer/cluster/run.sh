#!/bin/bash
set -u
B=/mnt/storage/doctawho42/tgnn-solv; R=$B/repo; PY=$B/env/bin/python; C=$B/current_code_arms
cd "$R"; ulimit -n 65536
export KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src CUDA_VISIBLE_DEVICES=""
echo "=== на ЦПУ намеренно: карты заняты сторонними задачами, это инференс ==="
for spec in "run_sigma_profile_residual sigma_profile_residual" "run_donor_window_rescore donor_window_rescore" "run_idac_learned_vs_reference idac_learned_vs_reference"; do
  set -- $spec
  echo; echo "################ $1 ################"; date -Is
  $PY scripts/analysis/$1.py --ckpt-dir "$C" --out "$B/class2/$2" 2>&1 | grep -vE "bottleneck|from pandas" | tail -40
  echo "--- код $? ---"
done
echo "########## КЛАСС2 ЗАВЕРШЕНО ##########"
