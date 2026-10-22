"""Сдвиг `sigma_hb` ПРИСВОЕНИЕМ АТРИБУТА ничего не меняет -- и это надо помнить.

ЗАЧЕМ ЭТОТ ТЕСТ. 2026-10-22 я поставил опыт «едет ли ступенька вместе с sigma_hb», выставляя
`layer.sigma_hb = X` перед оцениванием. Опыт отработал и дал при 0.0060 ровно те же шесть чисел,
что при 0.0084, расхождение 0.0000. Для настоящего эффекта такое совпадение невозможно -- оно и
вскрыло, что ручка отсоединена: матрица обменной энергии `delta_w_base` предвычисляется один раз в
`__init__` ("depends only on the fixed grid -> precompute once") и лежит буфером, поэтому forward
читает старое значение.

Тест держит ОБА факта: присвоение атрибута буфер не трогает (ловушка), а пересборка трогает
(лечение). Первое важнее: именно оно делает молчаливый отказ возможным.
"""
from __future__ import annotations

import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import CosmoSacLayer


def _layer(sigma_hb: float = 0.0084) -> CosmoSacLayer:
    cfg = TGNNSolvConfig(activity_model="cosmo_sac", cosmo_sac_sigma_hb=sigma_hb)
    return CosmoSacLayer(cfg=cfg)


def _rebuild_kernel(layer: CosmoSacLayer) -> None:
    """Та же пересборка, что в `run_sigma_core_boundary_sweep.py`."""
    g = layer.sigma_grid
    sm, sn = g.view(-1, 1), g.view(1, -1)
    misfit = 0.5 * layer.alpha_prime * (sm + sn) ** 2
    acc, don = torch.maximum(sm, sn), torch.minimum(sm, sn)
    hb = layer.c_hb * torch.clamp(acc - layer.sigma_hb, min=0.0) * torch.clamp(
        don + layer.sigma_hb, max=0.0)
    layer.delta_w_base = misfit + hb


def test_setting_the_attribute_alone_does_NOT_move_the_kernel() -> None:
    """ЛОВУШКА. Именно это сделало опыт недействительным, и именно это легко не заметить."""
    layer = _layer()
    before = layer.delta_w_base.detach().clone()
    layer.sigma_hb = 0.0060
    moved = float((layer.delta_w_base - before).abs().max())
    assert moved == 0.0, (
        "присвоение атрибута внезапно стало двигать ядро -- если это намеренно, тест надо "
        "переписать; пока же он фиксирует, что САМО ПРИСВОЕНИЕ бессильно")


def test_rebuilding_the_kernel_does_move_it() -> None:
    layer = _layer()
    before = layer.delta_w_base.detach().clone()
    layer.sigma_hb = 0.0060
    _rebuild_kernel(layer)
    moved = float((layer.delta_w_base - before).abs().max())
    assert moved > 0.0, "ядро не изменилось даже после пересборки -- лечение не работает"


def test_the_kernel_moves_monotonically_with_sigma_hb() -> None:
    """Проверка направления: чем выше порог, тем слабее водородносвязанный член."""
    mags = []
    for hb in (0.0060, 0.0084, 0.0120, 0.0160):
        layer = _layer()
        layer.sigma_hb = hb
        _rebuild_kernel(layer)
        g = layer.sigma_grid
        sm, sn = g.view(-1, 1), g.view(1, -1)
        misfit = 0.5 * layer.alpha_prime * (sm + sn) ** 2
        mags.append(float((layer.delta_w_base - misfit).abs().sum()))
    assert mags == sorted(mags, reverse=True), (
        f"HB-член не убывает монотонно с порогом: {mags}")
    assert mags[0] > mags[-1] * 2, "сдвиг порога почти не меняет HB-член -- эксперимент бессилен"


def test_a_layer_built_with_a_different_sigma_hb_differs_from_a_rebuilt_one_only_slightly() -> None:
    """Пересборка обязана давать то же, что постройка с этим порогом с самого начала."""
    rebuilt = _layer(0.0084)
    rebuilt.sigma_hb = 0.0120
    _rebuild_kernel(rebuilt)
    native = _layer(0.0120)
    assert torch.allclose(rebuilt.delta_w_base, native.delta_w_base, atol=1e-6), (
        "пересобранное ядро не совпало с построенным сразу -- пересборка воспроизводит не то")
