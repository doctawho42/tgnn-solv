#!/bin/bash
# Карта 1 занята последовательно: база, затем КОНТРОЛЬ. Карта 0 отдана прогону GROMACS
# пользователя (gmx mdrun -plumed, 7 ч на момент запуска) и не занимается.
set -u
B=/mnt/storage/doctawho42/tgnn-solv/seed43
bash "$B/run_base.sh" > "$B/base.out" 2>&1
echo "=== база кончила, код $?; запускаю КОНТРОЛЬ на той же карте ==="
bash "$B/run_detachencoder.sh" > "$B/detachencoder.out" 2>&1
echo "=== ЦЕПОЧКА КАРТЫ 1 ЗАВЕРШЕНА код $? ==="
