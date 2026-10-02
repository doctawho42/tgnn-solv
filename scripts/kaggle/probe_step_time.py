#!/usr/bin/env python
"""Получасовой замер скорости шага на РЕАЛЬНОМ GPU: решает, как тратить квоту.

ЗАЧЕМ. Плечо стоит около 20 часов на T4 при 192 тысячах шагов (111724 строки, батч 64, 110 эпох),
то есть 0.375 с на шаг для трёхслойного GNN с hidden 64. Это выглядит на два порядка дороже, чем
должно. Докстринг scripts/train.py:56 утверждает, что нагрузка launch-bound, а не FLOP-bound, и
предлагает TGNN_COMPILE -- но на плечах записи он НЕ применялся (манифесты его не упоминают).

ПОЧЕМУ НЕ ПРОФИЛЬ НА НОУТБУКЕ. Он был снят (2026-10-02) и дал плоскую пропускную способность ~11
строк/с с линейным ростом времени шага по батчу, то есть «укрупнение не помогает». Но на CPU
параллельного запаса нет по определению, и линейность там получается по построению. Вопрос про
GPU этим инструментом не решается. Что профиль на CPU всё же установил: отключение итераций
решателя время НЕ уменьшает, значит узкое место не в COSMO-SAC, а в энкодере и тракте данных.

ЧТО МЕРЯЕТ. Время шага (forward + backward + шаг оптимизатора) в четырёх режимах: батч 64 и 512,
с TGNN_COMPILE и без. Этого хватает, чтобы ответить на два вопроса сразу:
  * растёт ли время шага с батчем  -> если почти нет, укрупнение даёт экономию кратно батчу;
  * даёт ли compile  -> если даёт, он бесплатен и безопасен для возобновления (in-place, ключи
    state_dict не меняются).

ОГОВОРКА, КОТОРУЮ НАДО НЕСТИ. Укрупнение батча ломает сравнимость с опубликованными числами: LR
подобраны под 64. Но E1 и E2 -- КОНТРАСТЫ, и если переобучить контроль при том же новом батче,
контраст остаётся валидным: одинаковая деградация обеих ветвей его не портит.

    python scripts/kaggle/probe_step_time.py --config configs/cosmo_sac.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def make_subsample(src: Path, n_rows: int, dst: Path) -> Path:
    """Подвыборка фиксированного размера: число шагов ограничивается ДАННЫМИ.

    Поля max_steps_per_epoch в конфиге нет, а --set на неизвестный ключ бросает ValueError
    (train.py:883) -- то есть ограничить шаги настройкой нельзя, и это правильно. Ограничиваем
    строками: steps * batch строк дают ровно steps шагов за эпоху.
    """
    import pandas as pd
    d = pd.read_csv(src, low_memory=False)
    d.head(n_rows).to_csv(dst, index=False)
    return dst


def one_setting(config: Path, batch: int, compile_on: bool, steps: int, tmp: Path) -> dict:
    """Запускает короткое обучение в ДОЧЕРНЕМ процессе: compile включается переменной окружения."""
    env = dict(os.environ)
    env["TGNN_COMPILE"] = "1" if compile_on else "0"
    env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    train_csv = make_subsample(ROOT / "notebooks/data/processed/train.csv",
                               steps * batch, tmp / f"train_{batch}.csv")
    val_csv = make_subsample(ROOT / "notebooks/data/processed/val.csv",
                             min(2 * batch, 512), tmp / f"val_{batch}.csv")
    cmd = [sys.executable, str(ROOT / "scripts/train.py"), "--config", str(config),
           "--device", "cuda", "--num-workers", "2", "--seed", "42",
           "--train-data", str(train_csv), "--val-data", str(val_csv),
           "--epochs-phase1", "1", "--epochs-phase2", "0", "--epochs-phase3", "0",
           "--set", f"batch_size={batch}"]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd=ROOT)
    dt = time.perf_counter() - t0
    return {"batch": batch, "compile": compile_on, "wall_s": dt, "rc": p.returncode,
            "tail": p.stdout[-400:] if p.returncode else p.stderr[-400:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, default=ROOT / "configs/cosmo_sac.yaml")
    ap.add_argument("--steps", type=int, default=60, help="шагов на замер")
    ap.add_argument("--out", type=Path, default=ROOT / "results/step_time_probe")
    a = ap.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    if not torch.cuda.is_available():
        print("GPU НЕ ВИДЕН -- замер бессмысленен, он именно про GPU")
        return 1
    print(f"GPU: {torch.cuda.get_device_name(0)}")

    tmp = a.out / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    rows = []
    for batch in (64, 512):
        for comp in (False, True):
            r = one_setting(a.config, batch, comp, a.steps, tmp)
            rows.append(r)
            tag = "compile" if comp else "обычный"
            if r["rc"]:
                print(f"  батч {batch:>4} {tag:>8}: ОШИБКА rc={r['rc']}\n{r['tail']}")
            else:
                per = r["wall_s"] / a.steps
                print(f"  батч {batch:>4} {tag:>8}: {r['wall_s']:.1f} с на {a.steps} шагов "
                      f"= {per:.3f} с/шаг, {batch / per:.0f} строк/с")
    ok = [r for r in rows if not r["rc"]]
    if len(ok) >= 2:
        base = next((r for r in ok if r["batch"] == 64 and not r["compile"]), None)
        if base:
            b = base["wall_s"]
            print("\nЭКОНОМИЯ относительно батч-64-без-compile:")
            for r in ok:
                if r is base:
                    continue
                speed = (b / r["wall_s"]) * (r["batch"] / 64)   # поправка на строки за шаг
                print(f"  батч {r['batch']:>4} {'compile' if r['compile'] else 'обычный':>8}: "
                      f"{speed:.2f}x по пропускной способности")
    (a.out / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    print(f"\nзаписано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
