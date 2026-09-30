"""Сходимость сегментной неподвижной точки НА РЕАЛЬНЫХ ПРОФИЛЯХ.

ПОЧЕМУ ЭТОТ ФАЙЛ ДОПОЛНЯЕТ test_cosmo_sac_iter_convergence.py, А НЕ ЗАМЕНЯЕТ ЕГО.
Тот тест устроен правильно: он сверяет n_iter_train с n_iter_eval И проверяет, что сам eval
сошёлся (n_eval против n_eval+20), включая жёсткий бимодальный «водяной» стимул при 273 К.
Слабость не в способе сравнения, а в СТИМУЛЕ. Измерено 2026-09-30 на 7889 записях PGL6ed
(results/segment_convergence):

    на стимулах того теста   ошибка при n=30 против сошедшейся точки:  0.0000
    на реальных профилях     та же величина:                          0.0734

Разница в 370 раз. Три гладких синтетических профиля при трёх температурах не достают до
жёсткого угла корпуса: им оказывается ВОДА КАК РАСТВОРИТЕЛЬ (средняя ошибка 0.0284, максимум
0.0734 на 3074 записях; следующий растворитель, метанол, даёт 0.0079/0.0221), и хуже всего
крупное гидрофобное растворяемое в воде при низкой температуре.

ЧТО ЭТОТ ТЕСТ ФИКСИРУЕТ. Что ошибка итерации при настроенном счётчике оценки не растёт
незаметно. Он НЕ утверждает, что 0.073 приемлемо: это больше, чем TOL=0.05 соседнего теста, и
означает, что n_iter_eval=30 на воде НЕ сошёлся. Поднимать счётчик здесь нельзя в одиночку --
веса фитились против этого оператора, и смена счётчика осиротит каждое сравнение плеч
(CLAUDE.md: один только счётчик двигает ln x2 MAE на 1.08). Это решение исследователя, а не
теста; тест его лишь делает видимым.

Профили -- реальные VT-2005, вложены сюда литералами, чтобы тест не зависел от артефакта в
results/.
"""

from __future__ import annotations

import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer

#: Сошедшийся счётчик: при n=1000 поправка до n=3000 составляет 1.9e-06 (измерено).
N_CONVERGED = 1000

#: Измеренная ошибка при n_iter_eval=30 на этой паре; тест ловит РОСТ, а не факт.
MEASURED_AT_EVAL = 0.0734
HEADROOM = 1.5

WATER = (
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.633946, 2.377619, 2.968565,
    1.444556, 1.822042, 2.003554, 2.545643, 1.958697, 0.996725,
    0.401364, 0.487173, 1.165355, 0.803501, 1.348667, 0.060873,
    0.018528, 0.836695, 1.078314, 0.499516, 1.156891, 0.733892,
    0.706733, 1.390222, 0.917418, 1.442661, 0.433118, 0.950354,
    1.229484, 2.308848, 2.324488, 2.722118, 1.368181, 2.053392,
    0.080147, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000,
)
DIBUTYL_PHTHALATE = (
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.305413,
    5.101602, 10.707924, 14.067671, 23.249400, 48.380738, 46.868654,
    36.958940, 31.989664, 28.682490, 32.078200, 19.565508, 3.176645,
    3.505249, 4.917536, 4.014272, 6.728445, 4.349985, 8.422024,
    10.048070, 0.929600, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000, 0.000000, 0.000000, 0.000000,
    0.000000, 0.000000, 0.000000,
)

def _stiff_pair(layer: CosmoSacLayer):
    """Худшая пара корпуса: крупный гидрофобный эфир в воде, 283.15 К."""
    p_solute = torch.tensor([DIBUTYL_PHTHALATE], dtype=torch.float)
    p_solvent = torch.tensor([WATER], dtype=torch.float)
    return (p_solute, p_solvent, p_solute.sum(-1), p_solvent.sum(-1),
            torch.tensor([1e-4]), torch.tensor([283.15]))


def test_eval_count_error_against_converged_fixed_point() -> None:
    """Ошибка при n_iter_eval против СОШЕДШЕЙСЯ точки, а не против n_eval+20."""
    layer = CosmoSacLayer(TGNNSolvConfig())
    p2, p1, A2, A1, x2, T = _stiff_pair(layer)
    g_eval = layer._residual_ln_gamma2(p2, p1, A2, A1, x2, T, n_iter=layer.n_iter_eval)
    g_conv = layer._residual_ln_gamma2(p2, p1, A2, A1, x2, T, n_iter=N_CONVERGED)
    err = float((g_eval - g_conv).abs().max())
    assert err < MEASURED_AT_EVAL * HEADROOM, (
        f"ошибка итерации при n_iter_eval={layer.n_iter_eval} выросла до {err:.4f} ln-единиц "
        f"против измеренных {MEASURED_AT_EVAL:.4f} на этой же паре. Либо изменился решатель, "
        f"либо счётчик. См. results/segment_convergence/."
    )


def test_stiff_corner_is_not_visible_to_the_nplus20_proxy() -> None:
    """Сравнение n_eval с n_eval+20 ЗАНИЖАЕТ расстояние до предела, и вот на сколько.

    Обе итерации подходят к пределу с одной стороны, поэтому их взаимное расхождение меньше
    расстояния каждой до предела. На синтетических стимулах соседнего теста это безразлично
    (обе сошлись), на воде -- нет. Тест фиксирует сам факт занижения, чтобы прокси не сочли
    доказательством сходимости.
    """
    layer = CosmoSacLayer(TGNNSolvConfig())
    p2, p1, A2, A1, x2, T = _stiff_pair(layer)
    n = layer.n_iter_eval
    f = lambda k: layer._residual_ln_gamma2(p2, p1, A2, A1, x2, T, n_iter=k)  # noqa: E731
    proxy = float((f(n) - f(n + 20)).abs().max())
    truth = float((f(n) - f(N_CONVERGED)).abs().max())
    assert truth > proxy, (
        f"прокси n-против-n+20 дал {proxy:.4f}, истинная ошибка {truth:.4f}; "
        "ожидалось, что прокси занижает"
    )


def test_convergence_residual_is_tracked_and_changes_nothing() -> None:
    """Флаг cosmo_sac_track_convergence НЕ меняет арифметику и заполняет невязку."""
    cfg_off, cfg_on = TGNNSolvConfig(), TGNNSolvConfig()
    cfg_on.cosmo_sac_track_convergence = True
    off, on = CosmoSacLayer(cfg_off), CosmoSacLayer(cfg_on)
    p2, p1, A2, A1, x2, T = _stiff_pair(off)
    g_off = off._residual_ln_gamma2(p2, p1, A2, A1, x2, T, n_iter=off.n_iter_eval)
    g_on = on._residual_ln_gamma2(p2, p1, A2, A1, x2, T, n_iter=on.n_iter_eval)
    assert torch.equal(g_off, g_on), "включение диагностики изменило результат"
    assert off.last_convergence is None
    assert on.last_convergence is not None
    assert on.last_convergence["n_iter"] == on.n_iter_eval
    # невязка должна падать с числом итераций
    on._residual_ln_gamma2(p2, p1, A2, A1, x2, T, n_iter=N_CONVERGED)
    far = on.last_convergence["residual_max"]
    on._residual_ln_gamma2(p2, p1, A2, A1, x2, T, n_iter=4)
    near = on.last_convergence["residual_max"]
    assert far < near, f"невязка не убывает: n=4 -> {near:.3e}, n={N_CONVERGED} -> {far:.3e}"
