#!/usr/bin/env python
"""Прочитать пару E2 по правилам, записанным ДО того, как пришли её числа.

ЭТОТ СКРИПТ НАПИСАН ПРЕЖДЕ ЧИСЕЛ, И В ЭТОМ ВЕСЬ СМЫСЛ. Плечи ``grounded_a`` и
``grounded_a_detachcrystal`` на сиде 42 обучались, когда он создавался (ядро ``tgnn-solv-e2rb``,
2026-10-04). Предзаявка ``results/e2_crystal_detach/PRE_DECLARATION.md`` и три её поправки задают,
какую ось с какой неопределённостью сравнивать и с каким порогом; здесь это исполняется кодом, а не
памятью, потому что в этом проекте уже умирали рамки, придуманные после взгляда на числа.

ЧТО ЭТОТ СКРИПТ НЕ УМЕЕТ ПО ПОСТРОЕНИЮ. Он не может доложить уверенный эффект на кристаллической
страте по внутрисидовому бутстрэпу. Поправка часть вторая измерила, что там кластерная дисперсия
НЕ доминирует над сидовой (парный межсидовый sd 13.94 K против бутстрэпной SE ~8.2 K), и что
единственный сид, на котором внутрисидовый CI исключает нуль, -- это сид 42, тот самый, на котором
идёт E2, и по знаку он неверен (поперёк сидов величина равна -2.27 +- 13.94 K, а сид 43 даёт +17.5 K
противоположного знака). Поэтому на этой оси скрипт печатает ОБА числа и помечает вывод как
незаконный к одиночному цитированию. На оси задачи, где бутстрэп консервативен (полуширина 0.21
против 0.146 от межсидового sd) и оба его уверенных вызова по знаку верны, цитировать его можно, и
скрипт это разрешает. На заявленной оси бутстрэп вырожден -- один кластер.

ПОРОГИ, ОБЪЯВЛЕННЫЕ ЗАРАНЕЕ (источник ``results/e2_crystal_detach/seed_floor.json``):
  * ``ln x2`` MAE: 0.0744 -- парный sd единственного подлинного контраста двух обучений на пяти
    выложенных сидах. Независимо подтверждает 0.07, выведенный в предзаявке из маргинальных
    опубликованных sd. Внутри подсемейства сидов 42/43/44 парный sd равен 0.0267, то есть 0.0744
    консервативен.
  * ``delta_phi_mean``: 0.36 -- ЗАИМСТВОВАННЫЙ, потому что на одном кластере пара не может
    измерить собственную неопределённость.
  * смещение ``T_m``: 13.94 K, и ось объявлена ПОДДЕРЖИВАЮЩЕЙ, а не решающей.

ЧЕГО ЧИТАТЕЛЬ НЕ ДЕЛАЕТ. Он не объявляет исход. Он печатает, какому из четырёх заранее записанных
исходов соответствует наблюдённое, и отдельно -- что эта пара сказать не может: одна пара не банкует
ни негатив, ни позитив, и исход 3 («не двигается») не банкуется ею вовсе, потому что отсутствие
сдвига при поле 0.36 на одной молекуле -- односторонняя граница, а не нуль.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from tgnn_solv.diagnostics.compensation import (
    annotate_compensation_frame,
    compensation_row_mask,
)

KEY = ["solute_smiles", "solvent_smiles", "T"]
BOOTSTRAP_SEED = 20261004
BOOTSTRAP_DRAWS = 20000

#: Пороги и правило цитирования -- ОДНО место, и оно читается из предзаявки, а не изобретается.
#: ``bootstrap_quotable`` -- это и есть содержание второй поправки: доминирует ли кластерная
#: дисперсия над сидовой НА ЭТОЙ ОСИ. Не свойство метода, а свойство оси, поэтому поле.
AXES = {
    "ln_x2_mae": {
        "label": "ln x2 MAE на запертых строках (ось задачи)",
        "threshold": 0.0744, "unit": "", "reduction": "построчно",
        "bootstrap_quotable": True,
        "note": ("парный sd пяти выложенных сидов; внутри подсемейства 42/43/44 равен 0.0267, "
                 "поэтому порог консервативен. Бутстрэп здесь консервативен и его уверенные "
                 "вызовы по знаку верны -- цитировать можно."),
    },
    "delta_phi_mean": {
        "label": "delta_phi_mean под штатной маской (ЗАЯВЛЕННАЯ ось)",
        "threshold": 0.36, "unit": "", "reduction": "построчно",
        "bootstrap_quotable": False,
        "note": ("ОДИН кластер: измеренный dH_fus есть у одного растворяемого, 18 строк. Порог "
                 "ЗАИМСТВОВАН -- собственной неопределённости у пары здесь нет, бутстрэп вырожден."),
    },
    "T_m_bias_K": {
        "label": "смещение T_m на страте ИЗМЕРЕННОГО T_m, по растворяемым (поддерживающая)",
        "threshold": 13.94, "unit": " K", "reduction": "по растворяемым",
        "bootstrap_quotable": False,
        "note": ("сидовая дисперсия ПРЕВЫШАЕТ кластерную (13.94 K против SE ~8.2 K); единственный "
                 "сид с уверенным внутрисидовым CI -- 42, и по знаку он неверен. Внутрисидовый CI "
                 "здесь НЕЗАКОНЕН к одиночному цитированию."),
    },
}


def _bool(s: pd.Series) -> pd.Series:
    if s.dtype == object:
        return s.map(lambda v: str(v).strip().lower() in ("true", "1"))
    return s.fillna(False).astype(bool)


def _load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["T"] = df["T"].round(6)
    return df.drop_duplicates(KEY, keep="first")


def lock(frames: dict[str, pd.DataFrame]) -> list[tuple]:
    """Пересечение плеч по (растворяемое, растворитель, T), как в run_e5_comparison.py.

    Запирание обязательно: иначе плечи сравниваются на разных наборах строк, и разность несёт
    состав набора. Конъюнкция с конечностью предсказания ЗАВИСИТ ОТ ИСХОДА -- она убрала бы у
    всех плеч строки, на которых какое-то одно провалилось, в пользу того, кто провалился чаще.
    На выложенных прогонах она инертна (0 неконечных на 8103 строках), поэтому неконечные здесь
    СЧИТАЮТСЯ И ПЕЧАТАЮТСЯ по плечам, а не вырезаются.
    """
    common = None
    for name, df in frames.items():
        sup = df[_bool(df["has_solubility"])]
        n_bad = int((~np.isfinite(sup["ln_x2_pred"].to_numpy(float))).sum())
        if n_bad:
            print(f"!! плечо {name}: {n_bad} неконечных ln_x2_pred на размеченных строках. "
                  f"Они НЕ вырезаны -- вырезание сделало бы замок зависящим от исхода. "
                  f"Разберись с ними прежде, чем читать числа.")
        keys = set(map(tuple, sup[KEY].itertuples(index=False, name=None)))
        common = keys if common is None else (common & keys)
    return sorted(common or set())


def _in_lock(df: pd.DataFrame, axis: str, keys: set[tuple]) -> pd.DataFrame:
    ann = annotate_compensation_frame(df, label=axis)
    ann["_k"] = list(map(tuple, ann[KEY].itertuples(index=False, name=None)))
    inlock = ann[ann["_k"].isin(keys)]
    if axis == "delta_phi_mean":
        return inlock[compensation_row_mask(inlock)]
    if axis == "T_m_bias_K":
        return inlock[_bool(inlock["has_T_m"])]
    if axis == "ln_x2_mae":
        out = inlock.copy()
        out["ae"] = (out["ln_x2_pred"] - out["ln_x2_true"]).abs()
        return out
    raise ValueError(axis)


def headline(df: pd.DataFrame, axis: str, keys: set[tuple]) -> float:
    """Заголовочная статистика ТОЧНО тем способом, которым измерен её порог.

    ЭТО НЕ ПРИДИРКА, И ДЫМОВОЙ ТЕСТ ЕЁ ПОЙМАЛ. Первая версия этой функции считала все три оси как
    среднее ПО РАСТВОРЯЕМЫМ, тогда как ``measure_paired_seed_floor.py::arm_axes`` -- источник всех
    трёх порогов -- считает ``ln x2`` MAE и ``delta_phi_mean`` ПОСТРОЧНО, а смещение ``T_m`` по
    растворяемым. На контрасте ungrounded-grounded_a сида 42 расхождение между двумя редукциями
    ``ln x2`` MAE составило 0.1319 против 0.1487, то есть сравнение шло бы с порогом, к которому
    величина не относится. Поэтому редукция каждой оси прибита здесь и в тесте, а не выведена из
    того, что кажется естественным.
    """
    sub = _in_lock(df, axis, keys)
    if axis == "delta_phi_mean":
        return float(sub["delta_phi"].mean())                      # ПОСТРОЧНО
    if axis == "ln_x2_mae":
        return float(sub["ae"].mean())                             # ПОСТРОЧНО
    if axis == "T_m_bias_K":
        g = sub.groupby("solute_canonical").agg(m=("T_m", "mean"), p=("T_m_solver", "mean"))
        return float((g["p"] - g["m"]).mean())                     # ПО РАСТВОРЯЕМЫМ
    raise ValueError(axis)


def per_solute(df: pd.DataFrame, axis: str, keys: set[tuple]) -> pd.Series:
    """Вектор по кластерам -- ТОЛЬКО для бутстрэпа, не для заголовка (см. ``headline``)."""
    sub = _in_lock(df, axis, keys)
    if axis == "delta_phi_mean":
        return sub.groupby("solute_canonical")["delta_phi"].mean()
    if axis == "T_m_bias_K":
        g = sub.groupby("solute_canonical").agg(m=("T_m", "mean"), p=("T_m_solver", "mean"))
        return g["p"] - g["m"]
    if axis == "ln_x2_mae":
        return sub.groupby("solute_canonical")["ae"].mean()
    raise ValueError(axis)


def boot(diff: np.ndarray, rng: np.random.Generator) -> dict:
    n = len(diff)
    if n < 2:
        return {"n": n, "mean": float(diff.mean()) if n else float("nan"), "degenerate": True}
    idx = rng.integers(0, n, size=(BOOTSTRAP_DRAWS, n))
    m = diff[idx].mean(axis=1)
    lo, hi = float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
    return {"n": n, "mean": float(diff.mean()), "sd_clusters": float(diff.std(ddof=1)),
            "ci95": [lo, hi], "excludes_zero": bool(lo > 0 or hi < 0), "degenerate": False}


def stratify_T_m(control: pd.DataFrame, treated: pd.DataFrame, keys: set[tuple]) -> dict:
    """Правило проекта: ЛЮБОЙ аудит кристаллического члена расслаивается по измеренному/Joback T_m.

    Без этого статистика -- факт о дистанции экстраполяции в костюме кристаллохимии.
    """
    out = {}
    for name, df in (("control", control), ("treated", treated)):
        ann = annotate_compensation_frame(df, label=name)
        ann["_k"] = list(map(tuple, ann[KEY].itertuples(index=False, name=None)))
        inlock = ann[ann["_k"].isin(keys)]
        meas = _bool(inlock["has_T_m"])
        out[name] = {
            "measured_T_m_rows": int(meas.sum()),
            "measured_T_m_solutes": int(inlock.loc[meas, "solute_canonical"].nunique()),
            "joback_T_m_rows": int((~meas).sum()),
            "joback_T_m_solutes": int(inlock.loc[~meas, "solute_canonical"].nunique()),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--control", type=Path, required=True,
                    help="grounded_a_predictions.csv (контроль, флаг выключен)")
    ap.add_argument("--treated", type=Path, required=True,
                    help="grounded_a_detachcrystal_predictions.csv (флаг включён)")
    ap.add_argument("--out", type=Path, default=Path("results/e2_crystal_detach/pair_reading.json"))
    a = ap.parse_args()

    frames = {"control": _load(a.control), "treated": _load(a.treated)}
    keys = set(lock(frames))
    print(f"замок: {len(keys)} строк в пересечении плеч")
    if len(keys) != 5608:
        print(f"!! ожидалось 5608 -- предзаявка и все три поправки измерены на этом наборе. "
              f"{len(keys)} означает ДРУГУЮ поверхность, и пороги к ней не относятся.")

    strata = stratify_T_m(frames["control"], frames["treated"], keys)
    print("расслоение по T_m:", json.dumps(strata["control"], ensure_ascii=False))

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    report: dict[str, dict] = {}
    for axis, spec in AXES.items():
        # Заголовок -- в редукции порога; бутстрэп -- по кластерам. Две разные вещи, см. headline().
        h_c = headline(frames["control"], axis, keys)
        h_t = headline(frames["treated"], axis, keys)
        shift = h_t - h_c
        c = per_solute(frames["control"], axis, keys)
        t = per_solute(frames["treated"], axis, keys)
        common = c.index.intersection(t.index)
        d = (t[common] - c[common]).to_numpy(float)
        bs = boot(d, rng)
        thr = spec["threshold"]
        exceeds = bool(abs(shift) > thr) if np.isfinite(shift) else False

        print(f"\n=== {spec['label']} ===")
        print(f"  контроль {h_c:.4f}{spec['unit']}   флаг {h_t:.4f}{spec['unit']}   "
              f"сдвиг {shift:+.4f}{spec['unit']}   кластеров {bs['n']}  "
              f"(редукция: {spec['reduction']})")
        print(f"  порог {thr}{spec['unit']}  ->  "
              + ("ПРЕВЫШЕН" if exceeds else "НЕ превышен (внутри поля)"))
        if bs["degenerate"]:
            print("  внутрисидовый бутстрэп ВЫРОЖДЕН (один кластер): собственной "
                  "неопределённости у этой пары на этой оси нет")
        elif spec["bootstrap_quotable"]:
            print(f"  внутрисидовый CI95 [{bs['ci95'][0]:+.4f}, {bs['ci95'][1]:+.4f}]"
                  f"  исключает нуль: {'да' if bs['excludes_zero'] else 'нет'}  "
                  f"-- ЦИТИРОВАТЬ МОЖНО (на этой оси кластерная дисперсия доминирует)")
        else:
            print(f"  внутрисидовый CI95 [{bs['ci95'][0]:+.4f}, {bs['ci95'][1]:+.4f}]"
                  f"  исключает нуль: {'да' if bs['excludes_zero'] else 'нет'}")
            print("  !! ЦИТИРОВАТЬ В ОДИНОЧКУ НЕЗАКОННО на этой оси -- измерено, что сидовая "
                  "дисперсия превышает кластерную, и уверенный вызов на сиде 42 по знаку неверен")
        print(f"  {spec['note']}")
        report[axis] = {**spec, "control": h_c, "treated": h_t, "shift": shift,
                        "exceeds_threshold": exceeds,
                        "cluster_mean_shift_for_reference": bs["mean"], "bootstrap": bs}

    # ===== соответствие заранее записанным исходам, БЕЗ объявления исхода =====
    dphi = report["delta_phi_mean"]
    mae = report["ln_x2_mae"]
    dphi_falls = dphi["shift"] < -dphi["threshold"]
    dphi_rises = dphi["shift"] > dphi["threshold"]
    mae_worse = mae["shift"] > mae["threshold"]
    if dphi_falls and not mae_worse:
        matched = "1 (delta_phi_mean падает, ln x2 не хуже порога)"
    elif dphi_falls and mae_worse:
        matched = "2 (delta_phi_mean падает, ln x2 хуже -- измерена цена идентифицируемости)"
    elif dphi_rises:
        matched = "4 (delta_phi_mean РАСТЁТ -- непредусмотренный исход, докладывается как есть)"
    else:
        matched = "3 (delta_phi_mean не двигается за порогом)"
    print(f"\nсоответствует заранее записанному исходу: {matched}")
    print("ЧТО ЭТА ПАРА СКАЗАТЬ НЕ МОЖЕТ: одна пара не банкует ни негатив, ни позитив -- правило "
          "проекта требует репликата на ОБОИХ плечах. Исход 3 не банкуется ею вовсе: отсутствие "
          "сдвига при заимствованном поле 0.36 на ОДНОМ кластере -- односторонняя граница, а не "
          "нуль. Вспомогательная точность кристаллической головы сдвинется по причине, не связанной "
          "с компенсацией: флаг отнимает у головы один из двух источников градиента.")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(
        {"n_locked": len(keys), "strata": strata, "axes": report,
         "matched_predeclared_outcome": matched,
         "bootstrap": {"seed": BOOTSTRAP_SEED, "draws": BOOTSTRAP_DRAWS}},
        indent=2, ensure_ascii=False) + "\n")
    print(f"\nзаписано {a.out}")


if __name__ == "__main__":
    main()
