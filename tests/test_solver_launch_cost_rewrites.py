"""Два перепиcывания, сделанных ради скорости, НИЧЕГО не меняют численно.

ПОЧЕМУ ОНИ ПОЯВИЛИСЬ. Диагностика на Kaggle T4 (2026-10-02,
scripts/kaggle/make_bottleneck_notebook.py) показала, что шаг стоит 331 мс при батче 64,
а карта занята на 25% (p90 34%), при том что загрузчик отдаёт 648-714 строк/с против
потолка счёта 193 строк/с. То есть ни данные, ни арифметика не узкое место: время уходит
на ВЫДАЧУ работы с CPU -- порядка 1.8 тысячи крошечных ядер на шаг плюс блокирующие
синхронизации хоста внутри решателя.

Отсюда две правки, и обе должны быть ТОЖДЕСТВЕННЫ по смыслу:
  1. Сегментная точка для смеси и чистого растворяемого решается ОДНИМ стопкой вызовом
     (layers._segment_matvec умеет (B,K,G)) вместо двух последовательных. Точка независима
     по строкам, поэтому это точно, а не приближённо.
  2. Ранний выход внешнего цикла по solver_tol выключен НА ПУТИ COSMO-SAC
     (config.solver_cosmo_break_on_tol=False): его residual.max().item() -- блокирующая
     синхронизация CUDA n_iter раз за forward, а срабатывает он там, по
     scripts/analysis/run_solver_break_audit.py, ни в одной из 144 невырожденных клеток.
     На пути NRTL выход ОСТАВЛЕН. На штатных счётчиках он и там не срабатывает (ближайшая
     клетка -- 4.8x от tol), но при нештатных n_iter_eval=30 / tol=1e-8, которые берёт
     test_physics_verification.py, срабатывает на итерации 16 из 30, и выключение сдвинуло бы
     x2 на 2.3e-09 вместо нуля -- мало как физика, но это разница между проверенным
     тождеством и необъявленной сменой оператора.

ЧТО ЭТОТ ФАЙЛ ЛОВИТ. Что ни одна из правок не начала менять числа. Для (1) допуск -- шум
порядка суммирования float32: сам проект уже принял 1.9e-06 как собственную невязку
самопроверки сегментного решателя (results/segment_convergence/summary.json,
reference_self_check_max), и измеренный сдвиг стопки той же величины. Для (2) допуска нет
вовсе -- побитовое равенство, иначе правка не операторно-нейтральна.

Стимул -- реальная ВОДА при 273 К, жёсткий угол корпуса: синтетические профили в этом
решателе показывают 0.0000 там, где реальные дают 0.0734 (см.
test_segment_convergence_real_profiles.py, откуда литералы и взяты).
"""

from __future__ import annotations

import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSac2010Layer, CosmoSacLayer
from tgnn_solv.solver import SLESolver
from test_segment_convergence_real_profiles import DIBUTYL_PHTHALATE, WATER

#: Невязка самопроверки сегментного решателя, уже принятая проектом как float32-шум.
REDUCTION_NOISE = 1.9073486328125e-06


def _stimulus(n_bins: int) -> tuple[torch.Tensor, ...]:
    """Вода как растворитель, дибутилфталат как растворяемое, плюс вырожденная строка.

    Третья строка -- вся масса в одном бине: там сегментная Gamma вырождена, и если стопка
    и последовательность расходятся где-то, то скорее здесь.
    """
    water = torch.tensor(WATER, dtype=torch.float)
    solute = torch.tensor(DIBUTYL_PHTHALATE, dtype=torch.float)
    if n_bins != water.numel():
        # 2010 работает на 153-сетке из блоков NHB/OH/OT. Нулевые OH и OT оставили бы
        # типизированное HB-ядро c_hb(type_m,type_n) выключенным -- то есть тест не касался
        # бы той части оператора, которой 2010 и отличается от 2002. Поэтому вода
        # раскладывается по трём блокам с донорским перевесом (она и есть жёсткий угол),
        # а растворяемое -- почти целиком неполярное.
        water = torch.cat((0.3 * water, 0.5 * water, 0.2 * water))
        solute = torch.cat((0.8 * solute, 0.05 * solute, 0.15 * solute))
    p2 = torch.stack((solute, solute, torch.zeros(n_bins)))
    p2[2, 10] = 5.0
    p1 = torch.stack((water, water, water))
    A2, A1 = p2.sum(-1), p1.sum(-1)
    return p2, p1, A2, A1, A2 * 1.2, A1 * 1.2


def test_stacked_segment_solve_equals_two_sequential_solves() -> None:
    """Правка (1): стопка (B,2,G) против двух вызовов -- в пределах шума суммирования."""
    for cls, n_bins in ((CosmoSacLayer, 51), (CosmoSac2010Layer, 153)):
        layer = cls(TGNNSolvConfig(activity_model="cosmo_sac"))
        layer.eval()
        p2, p1, A2, A1, _, _ = _stimulus(n_bins)
        T = torch.tensor([273.15, 298.15, 273.15])
        for x2 in (0.0, 1e-6, 0.3, 0.9):
            x2_t = torch.full((3,), float(x2))
            x1_t = 1.0 - x2_t
            E = (layer._E_matrix(T) if hasattr(layer, "_E_matrix") else None)
            if E is None:                                  # 2010 строит E внутри
                rt = (layer.R_kcal * T).clamp_min(layer.eps).view(-1, 1, 1)
                E = torch.exp((-layer._delta_w(T) / rt).clamp(-layer.exp_clamp, layer.exp_clamp))
            A_mix = (x2_t * A2 + x1_t * A1).clamp_min(layer.eps)
            p_mix = (x2_t.unsqueeze(-1) * p2 + x1_t.unsqueeze(-1) * p1) / A_mix.unsqueeze(-1)
            p2_pure = p2 / A2.clamp_min(layer.eps).unsqueeze(-1)
            with torch.no_grad():
                stacked = layer._segment_ln_gamma(torch.stack((p_mix, p2_pure), 1), E, 30)
                seq_mix = layer._segment_ln_gamma(p_mix, E, 30)
                seq_pure = layer._segment_ln_gamma(p2_pure, E, 30)
            d = max((stacked[:, 0] - seq_mix).abs().max().item(),
                    (stacked[:, 1] - seq_pure).abs().max().item())
            assert d <= REDUCTION_NOISE, (
                f"{cls.__name__} при x2={x2}: стопка расходится с последовательностью на "
                f"{d:.3e}, что больше принятого проектом float32-шума {REDUCTION_NOISE:.3e}. "
                "Это уже не порядок суммирования -- проверьте транспонирование в "
                "layers._segment_matvec."
            )


def test_disabling_the_tol_break_is_bit_identical() -> None:
    """Правка (2): solver_cosmo_break_on_tol=False даёт РОВНО те же числа, что и True.

    Допуска нет сознательно: если бы выход срабатывал, это была бы смена оператора, и её
    нельзя прятать в оптимизацию скорости -- веса плеч фитились против конкретного
    решателя (CLAUDE.md про счётчик сегментов).
    """
    p2, p1, A2, A1, V2, V1 = _stimulus(51)
    T = torch.tensor([273.15, 298.15, 273.15])
    params = {"p_solute": p2, "p_solvent": p1, "A_solute": A2, "A_solvent": A1,
              "V_solute": V2, "V_solvent": V1}
    for training in (True, False):
        # Phi=0 -- ровно температура плавления: чистое растворяемое там само неподвижная
        # точка с невязкой 0, то есть единственная клетка, где выход вообще срабатывает.
        for Phi in (torch.zeros(3), torch.tensor([0.5, 4.0, 8.0])):
            out = {}
            for flag in (True, False):
                solver = SLESolver(TGNNSolvConfig(
                    activity_model="cosmo_sac", solver_cosmo_break_on_tol=flag))
                solver.train(training)
                with torch.no_grad():
                    out[flag] = solver(T, {"Phi_override": Phi}, params)["ln_x2"]
            assert torch.equal(out[True], out[False]), (
                f"training={training}, Phi={Phi.tolist()}: ранний выход ВЛИЯЕТ на ln x2 "
                f"(макс. расхождение {(out[True] - out[False]).abs().max():.3e}). "
                "Значит он срабатывает, и выключать его по умолчанию нельзя без "
                "пересчёта всех плеч -- см. run_solver_break_audit.py."
            )
