#!/usr/bin/env python
"""Проверка: путь инференса сервиса воспроизводит метрику, записанную в чекпойнте.

ЗАЧЕМ. Сервис строит признаки не тем кодом, что обучение, а тем же -- но собирает его
сам: конфиг из чекпойнта, флаги в загрузчик пересечением сигнатур, вызов forward по
интроспекции. Любая ошибка в этой сборке даёт РАБОТАЮЩИЙ сервис с тихо другими числами.
Единственный способ это увидеть -- прогнать модель по тому самому тестовому набору, на
котором в чекпойнт записана MAE, и сравнить.

Расхождение больше нескольких тысячных означает, что признаки на входе сервиса не те,
что были при обучении, и числа сервиса ничего не стоят.

    python way2drug/verify_against_checkpoint.py
    python way2drug/verify_against_checkpoint.py --limit 1000     # быстрее, грубее
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "way2drug"))

from w2d_solubility.predictor import SolubilityPredictor  # noqa: E402

TEST = ROOT / "notebooks/data/processed/test.csv"
#: Насколько MAE сервиса может отличаться от записанной в чекпойнте.
#: Не ноль: порядок суммирования по батчам даёт расхождение в последних разрядах float32.
TOLERANCE = 0.005


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="взять только первые N строк")
    args = ap.parse_args()

    df = pd.read_csv(TEST, low_memory=False)
    labelled = df[df["ln_x2"].notna()].copy()
    if "has_solubility" in labelled.columns:
        labelled = labelled[labelled["has_solubility"].astype(bool)]
    if args.limit:
        labelled = labelled.head(args.limit)
    print(f"тестовых строк с меткой: {len(labelled)}"
          f"{' (усечено)' if args.limit else ''}")

    predictor = SolubilityPredictor()
    pairs = [(r.solute_smiles, r.solvent_smiles, float(r.temperature))
             for r in labelled.itertuples()]
    raw = predictor._predict_pairs(pairs)          # (n_models, n_rows)
    truth = labelled["ln_x2"].to_numpy(dtype=float)

    print(f"\n{'сид':>5} {'MAE сервиса':>13} {'MAE в чекпойнте':>17} {'расхождение':>13}")
    worst, failures = 0.0, []
    for i, seed in enumerate(predictor.seeds):
        mae = float(np.abs(raw[i] - truth).mean())
        recorded = predictor.reported_metrics[i].get("mae")
        if recorded is None:
            print(f"{seed:>5} {mae:>13.4f} {'нет записи':>17} {'-':>13}")
            continue
        delta = abs(mae - float(recorded))
        worst = max(worst, delta)
        flag = "" if delta <= TOLERANCE else "   <-- РАСХОЖДЕНИЕ"
        print(f"{seed:>5} {mae:>13.4f} {float(recorded):>17.4f} {delta:>13.4f}{flag}")
        if delta > TOLERANCE:
            failures.append((seed, mae, float(recorded)))

    ens = float(np.abs(raw.mean(axis=0) - truth).mean())
    print(f"\nансамбль из {len(predictor.seeds)}: MAE {ens:.4f}")
    print(f"лучший одиночный:      MAE {min(np.abs(raw[i] - truth).mean() for i in range(len(raw))):.4f}")

    if args.limit:
        print("\nЭто усечённый прогон: метрика в чекпойнте записана на полном наборе,\n"
              "поэтому расхождение здесь ожидаемо и ничего не доказывает. Для проверки\n"
              "запускайте без --limit.")
        return 0
    if failures:
        print(f"\nПРОВАЛ: {len(failures)} сид(ов) разошлись больше чем на {TOLERANCE}.\n"
              "  Признаки на входе сервиса не те, что были при обучении. Числа сервиса\n"
              "  использовать нельзя, пока это не устранено.")
        return 1
    print(f"\nОК: путь инференса воспроизводит записанные метрики "
          f"(худшее расхождение {worst:.4f} при допуске {TOLERANCE}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
