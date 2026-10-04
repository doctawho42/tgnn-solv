"""Ворота на два факта, от которых зависит ЧТЕНИЕ пары E2, а не её обучение.

Поправка к ``results/e2_crystal_detach/PRE_DECLARATION.md`` объявила пороги, опираясь на две
величины, измеренные на выложенной пятёрке сидов: число КЛАСТЕРОВ, которое допускает каждая ось, и
то, что плечо ``oracle`` -- не второе обучение. Обе могут измениться молча. Маску
``compensation_row_mask`` кто-нибудь расширит, или пересобранный сплит поменяет состав
растворяемых с измеренным ``T_m`` -- и объявленные пороги (0.36 для ``delta_phi_mean``, 13.94 K для
кристаллической страты) станут числами про другую поверхность, оставшись в предзаявке как будто
про эту. Поэтому гейт не на значения порогов, а на ФОРМУ поверхности, из которой они получены.

ПОЧЕМУ ИМЕННО ЧИСЛО КЛАСТЕРОВ. Вся вторая часть поправки держится на одном: кластерный бутстрэп
честен там, где кластерная дисперсия доминирует над сидовой, и это свойство оси. На одном кластере
он вырожден, на 31 антиконсервативен втрое, на 147 консервативен. Сдвинь число кластеров -- и
правило чтения меняется, а не уточняется.

ЭТИ ВОРОТА НЕ ВСТАЮТ ПО СТОЙКЕ «СМИРНО», КОГДА ЧТО-ТО ИЗМЕНИЛОСЬ. Предсказательные CSV -- по 5 МБ
и гитигнорятся, поэтому на свежем клоне тестов просто нет данных, и только тогда они пропускаются.
Если данные есть, а числа разошлись -- это ПАДЕНИЕ с просьбой перенаправить предзаявку, а не
пропуск: ровно так в этом проекте уже протухали значения в прозе, которые гейт структурно не видел.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tgnn_solv.diagnostics.compensation import (
    annotate_compensation_frame,
    compensation_row_mask,
)

DEPOSIT = Path("results/e5_sigma_grounding_leakfree")
SEED = 42
PRE_DECL = "results/e2_crystal_detach/PRE_DECLARATION.md"

#: Форма оценочной поверхности, на которой измерены объявленные пороги. Источник --
#: ``results/e2_crystal_detach/seed_floor.json``, скрипт
#: ``scripts/analysis/measure_paired_seed_floor.py``.
DECLARED_CLUSTERS = {"delta_phi_mean": 1, "T_m_bias_K": 31, "ln_x2_mae": 147}
DECLARED_ROWS = {"delta_phi_mean": 18, "T_m_bias_K": 1318, "ln_x2_mae": 5608}


def _flag(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].astype(str).str.lower().isin(("true", "1", "1.0"))


def _read(arm: str) -> pd.DataFrame:
    p = DEPOSIT / f"seed_{SEED}" / f"{arm}_predictions.csv"
    if not p.exists():
        pytest.skip(f"{p} отсутствует (гитигнорится, ~5 МБ); ворота идут только с депозитом")
    return pd.read_csv(p)


def test_the_declared_axes_still_admit_the_cluster_counts_the_thresholds_were_measured_on() -> None:
    ann = annotate_compensation_frame(_read("grounded_a"), label="grounded_a")
    locked = _flag(ann, "has_solubility")
    got = {
        "delta_phi_mean": ann[compensation_row_mask(ann)],
        "T_m_bias_K": ann[locked & _flag(ann, "has_T_m")],
        "ln_x2_mae": ann[locked],
    }
    for axis, sub in got.items():
        clusters = sub["solute_canonical"].nunique()
        assert clusters == DECLARED_CLUSTERS[axis], (
            f"ось {axis} допускает {clusters} кластеров растворяемых, а пороги поправки измерены "
            f"на {DECLARED_CLUSTERS[axis]}. Правило чтения кластерного бутстрэпа зависит от этого "
            f"числа, поэтому пороги в {PRE_DECL} надо перемерить скриптом "
            f"scripts/analysis/measure_paired_seed_floor.py и перенаправить, а не подогнать."
        )
        assert len(sub) == DECLARED_ROWS[axis], (
            f"ось {axis}: {len(sub)} строк против {DECLARED_ROWS[axis]} в поправке"
        )


def test_the_declared_axis_really_is_one_molecule() -> None:
    """Отдельно и по имени: причина непригодности заявленной оси -- измеренный dH_fus у одного."""
    df = _read("grounded_a")
    dh = _flag(df, "has_dH_fus")
    assert df.loc[dh, "solute_smiles"].nunique() == 1, (
        "измеренный dH_fus появился больше чем у одного растворяемого -- это СНИМАЕТ главное "
        f"возражение поправки против заявленной оси E2, и {PRE_DECL} надо переписать: ось могла "
        "стать пригодной."
    )


def test_oracle_is_not_a_second_training_so_its_zeros_are_not_a_contrast() -> None:
    """Парные полы опираются на ОДИН подлинный контраст. Если oracle станет вторым обучением,
    таблица полов в поправке получит вторую опору -- и это надо заметить, а не унаследовать."""
    g, o, u = _read("grounded_a"), _read("oracle"), _read("ungrounded")
    assert (g.pair_key.values == o.pair_key.values).all()
    assert (g.pair_key.values == u.pair_key.values).all()

    def gap(a: pd.DataFrame, b: pd.DataFrame, col: str) -> float:
        x, y = a[col].to_numpy(float), b[col].to_numpy(float)
        m = np.isfinite(x) & np.isfinite(y)
        return float(np.abs(x[m] - y[m]).max())

    oracle_gap, ungrounded_gap = gap(g, o, "T_m_solver"), gap(g, u, "T_m_solver")
    assert _flag(o, "sigma_oracle_applied").any(), (
        "в плече oracle нет ни одной строки с sigma_oracle_applied=True -- значит это уже не "
        "подстановка профиля, и его роль в таблице полов надо пересмотреть"
    )
    assert oracle_gap < 1.0, (
        f"T_m_solver плеча oracle расходится с grounded_a на {oracle_gap:.3g} K. Поправка в "
        f"{PRE_DECL} исходит из того, что это ТЕ ЖЕ веса с подставленным профилем (измерено "
        f"6.4e-4 K), и именно поэтому его нули на кристаллических осях -- не контраст. Если это "
        f"больше не так, парные полы надо перемерить с oracle как вторым контрастом."
    )
    assert ungrounded_gap > 10.0, (
        f"T_m_solver плеча ungrounded расходится с grounded_a всего на {ungrounded_gap:.3g} K. "
        "Это ЕДИНСТВЕННЫЙ подлинный контраст двух обучений, на который опираются все парные полы; "
        "если он выродился, у поправки не осталось ни одной опоры."
    )


# --------------------------------------------------------------------------------------------
# РЕДУКЦИЯ ОСИ -- то, на чём читатель пары уже один раз сломался.
#
# `scripts/analysis/read_e2_pair.py` сравнивает сдвиг с порогом из
# `measure_paired_seed_floor.py`. Пороги измерены в РАЗНЫХ редукциях: `ln x2` MAE и
# `delta_phi_mean` построчно, смещение `T_m` -- по растворяемым. Первая версия читателя считала
# все три по растворяемым, и на известном контрасте это дало 0.1319 вместо 0.1487, то есть
# сравнение с порогом шло бы для величины, к которой порог не относится. Поймал дымовой тест;
# держит -- этот.
# --------------------------------------------------------------------------------------------

import importlib.util  # noqa: E402
import sys as _sys  # noqa: E402


def _reader():
    spec = importlib.util.spec_from_file_location(
        "read_e2_pair", Path("scripts/analysis/read_e2_pair.py"))
    mod = importlib.util.module_from_spec(spec)
    _sys.modules["read_e2_pair"] = mod
    spec.loader.exec_module(mod)
    return mod


def _keys(mod, frames):
    return set(mod.lock(frames))


def test_the_reader_reproduces_the_deposited_mae_which_pins_the_row_reduction() -> None:
    """Построчная редукция `ln x2` MAE -- та же, что в депонированной сводке, до 1e-9.

    Это и есть проверка редукции: среднее по растворяемым дало бы 2.12 вместо 1.887, и сравнение
    с порогом 0.0744 стало бы сравнением с чужим числом.
    """
    mod = _reader()
    import json
    frames = {"control": mod._load(DEPOSIT / f"seed_{SEED}" / "grounded_a_predictions.csv"),
              "treated": mod._load(DEPOSIT / f"seed_{SEED}" / "ungrounded_predictions.csv")}
    keys = _keys(mod, frames)
    assert len(keys) == 1 * DECLARED_ROWS["ln_x2_mae"], (
        f"замок {len(keys)} против {DECLARED_ROWS['ln_x2_mae']}: все пороги измерены на этом наборе")
    dep = json.loads((DEPOSIT / f"seed_{SEED}" / "grounded_a_predictions.summary.json").read_text())
    got = mod.headline(frames["control"], "ln_x2_mae", keys)
    assert abs(got - dep["mae"]) < 1e-9, (
        f"построчная редукция даёт {got!r} против депонированного {dep['mae']!r}. Порог 0.0744 "
        f"измерен в ЭТОЙ редукции, поэтому расхождение означает, что читатель сравнивает с чужим "
        f"числом -- см. read_e2_pair.headline()")


def test_the_two_reductions_are_provably_different_so_a_silent_swap_cannot_pass() -> None:
    """Без этого предыдущий тест прошёл бы и в мире, где обе редукции совпадают по совпадению."""
    mod = _reader()
    frames = {"control": mod._load(DEPOSIT / f"seed_{SEED}" / "grounded_a_predictions.csv"),
              "treated": mod._load(DEPOSIT / f"seed_{SEED}" / "ungrounded_predictions.csv")}
    keys = _keys(mod, frames)
    row = mod.headline(frames["control"], "ln_x2_mae", keys)
    clust = float(mod.per_solute(frames["control"], "ln_x2_mae", keys).mean())
    assert abs(row - clust) > 0.1, (
        f"построчная {row:.4f} и покластерная {clust:.4f} редукции сошлись -- тогда предыдущий "
        f"тест не различает их, и подмена редукции прошла бы молча")


def test_the_crystal_axis_bootstrap_is_marked_unquotable() -> None:
    """Запрет из второй поправки живёт в КОДЕ, а не только в прозе.

    Измерено: на кристаллической страте сидовая дисперсия превышает кластерную, и единственный
    сид с уверенным внутрисидовым CI -- 42, тот самый, на котором идёт E2, причём по знаку он
    неверен. Если кто-нибудь снимет этот флаг, читатель начнёт докладывать уверенный эффект там,
    где поперёк сидов его нет.
    """
    mod = _reader()
    assert mod.AXES["T_m_bias_K"]["bootstrap_quotable"] is False
    assert mod.AXES["delta_phi_mean"]["bootstrap_quotable"] is False
    assert mod.AXES["ln_x2_mae"]["bootstrap_quotable"] is True
    assert mod.AXES["ln_x2_mae"]["reduction"] == "построчно"
    assert mod.AXES["delta_phi_mean"]["reduction"] == "построчно"
    assert mod.AXES["T_m_bias_K"]["reduction"] == "по растворяемым"
