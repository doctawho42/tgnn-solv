#!/usr/bin/env python
"""Ноутбук-зонд: измерить минуты-на-эпоху на самом T4 прежде, чем тратить квоту на плечо.

ЗАЧЕМ. README этого каталога несёт правило, выведенное дорогой ценой: **arm-hours ~ 1.8 x
минут-на-эпоху** (110 эпох = 30+70+10), и совет «прочти время одной эпохи в первые двадцать минут
сессии и узнаешь, продолжать ли, вместо того чтобы выяснять это на двенадцатичасовом убийстве».
Там же записано, что ускорение от большего батча **на этом железе не измерено**, а
`TGNN_COMPILE` по манифестам плеч записи ни разу не применялся.

Зонд закрывает обе дыры за двадцать минут: четыре режима (батч 64 и 512, с compile и без),
по одной эпохе фазы 1 на подвыборке, с пересчётом на полный корпус и в часы-на-плечо.

ЧЕГО ЗОНД НЕ РЕШАЕТ. Укрупнение батча ломает сравнимость с опубликованными числами: LR подобраны
под 64. Но E1 и E2 -- КОНТРАСТЫ, и если переобучить контроль при том же батче, контраст остаётся
валидным: одинаковая деградация обеих ветвей его не портит. Это решение исследователя, зонд лишь
даёт цену.

ПОЧЕМУ ФАЗА 1. Она идёт без решателя SLE (_forward_phase1) и потому дешевле за эпоху, чем фазы
2-3. Правило 1.8x выведено на полном графике, так что перенос с фазы 1 на плечо завышает скорость;
число читать как ВЕРХНЮЮ границу, и это написано в выводе зонда.

    python scripts/kaggle/make_probe_notebook.py --out /tmp/kaggle_probe/probe.ipynb
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from make_notebook import ENV, INSTALL, STAGE  # noqa: E402

PROBE = '''
import json, subprocess, sys, time, os
from pathlib import Path
import pandas as pd

OUT = Path("/kaggle/working/out"); OUT.mkdir(parents=True, exist_ok=True)
FULL_ROWS = len(pd.read_csv("notebooks/data/processed/train.csv", low_memory=False))
SUB_ROWS = {sub_rows}
EPOCH_SCALE = FULL_ROWS / SUB_ROWS
print(f"полный корпус {{FULL_ROWS}} строк; замер на {{SUB_ROWS}}, масштаб x{{EPOCH_SCALE:.1f}}")

sub = Path("probe_data"); sub.mkdir(exist_ok=True)
pd.read_csv("notebooks/data/processed/train.csv", low_memory=False).head(SUB_ROWS) \\
    .to_csv(sub / "train.csv", index=False)
pd.read_csv("notebooks/data/processed/val.csv", low_memory=False).head(512) \\
    .to_csv(sub / "val.csv", index=False)

rows = []
for batch in {batches}:
    for comp in (False, True):
        env = dict(os.environ)
        env["TGNN_COMPILE"] = "1" if comp else "0"
        env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        cmd = [sys.executable, "scripts/train.py", "--config", "configs/cosmo_sac.yaml",
               "--device", "cuda", "--num-workers", "2", "--seed", "42",
               "--train-data", str(sub / "train.csv"), "--val-data", str(sub / "val.csv"),
               "--epochs-phase1", str({p1}), "--epochs-phase2", str({p2}),
               "--epochs-phase3", "0",
               "--set", f"batch_size={{batch}}",
               "--experiment-name", f"probe_b{{batch}}_c{{int(comp)}}"]
        t0 = time.perf_counter()
        p = subprocess.run(cmd, env=env, capture_output=True, text=True)
        dt = time.perf_counter() - t0
        tag = "compile" if comp else "обычный"
        if p.returncode:
            print(f"  батч {{batch:>4}} {{tag:>8}}: ОШИБКА rc={{p.returncode}}")
            print((p.stderr or p.stdout)[-1200:])
            rows.append({{"batch": batch, "compile": comp, "rc": p.returncode}})
            continue
        n_ep = {p1} + {p2}
        epoch_min = dt / 60.0 * EPOCH_SCALE / n_ep
        arm_h = 1.8 * epoch_min
        print(f"  батч {{batch:>4}} {{tag:>8}}: {{dt:6.1f}} с на подвыборку  ->  "
              f"{{epoch_min:5.2f}} мин/эпоха  ->  {{arm_h:5.1f}} ч/плечо")
        rows.append({{"batch": batch, "compile": comp, "rc": 0, "wall_s": dt,
                      "epoch_min_full": epoch_min, "arm_hours": arm_h}})

ok = [r for r in rows if r["rc"] == 0]
if ok:
    base = next((r for r in ok if r["batch"] == {batches}[0] and not r["compile"]), ok[0])
    print("\\nУСКОРЕНИЕ относительно базового режима:")
    for r in ok:
        print(f"  батч {{r['batch']:>4}} {{'compile' if r['compile'] else 'обычный':>8}}: "
              f"{{base['arm_hours'] / r['arm_hours']:.2f}}x")
    best = min(ok, key=lambda r: r["arm_hours"])
    print(f"\\nлучший режим: батч {{best['batch']}}, compile={{best['compile']}}, "
          f"{{best['arm_hours']:.1f}} ч/плечо против {{base['arm_hours']:.1f}} базовых")
    print("ЧИТАТЬ КАК ВЕРХНЮЮ ГРАНИЦУ СКОРОСТИ: замер на фазе 1, которая идёт без решателя SLE,")
    print("а правило 1.8x выведено на полном графике 30+70+10.")

(OUT / "step_time_probe.json").write_text(json.dumps(
    {{"full_rows": FULL_ROWS, "sub_rows": SUB_ROWS, "rows": rows}},
    ensure_ascii=False, indent=2))
print("\\nзаписано: /kaggle/working/out/step_time_probe.json")
'''


def cell(src: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": src.strip("\n").splitlines(keepends=True)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sub-rows", type=int, default=24000,
                    help="строк подвыборки на замер; 24000 даёт ~20 минут на четыре режима")
    ap.add_argument("--batches", type=int, nargs="+", default=[64, 512])
    ap.add_argument("--phase1", type=int, default=1, help="эпох фазы 1 на замер")
    ap.add_argument("--phase2", type=int, default=0,
                    help="эпох фазы 2 (с решателем SLE) -- именно они дороги")
    a = ap.parse_args()

    nb = {
        "cells": [cell(ENV), cell(INSTALL), cell(STAGE),
                  cell(PROBE.format(sub_rows=a.sub_rows, batches=tuple(a.batches),
                                      p1=a.phase1, p2=a.phase2))],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                    "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf8")
    print(f"записан {a.out}")
    print(f"  подвыборка {a.sub_rows} строк, батчи {a.batches}, "
          f"фаза1={a.phase1} фаза2={a.phase2} эпох на режим")
    return 0


if __name__ == "__main__":
    sys.exit(main())
