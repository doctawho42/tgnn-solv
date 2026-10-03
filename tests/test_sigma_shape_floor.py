"""Пол на члене формы: выключенный -- бит-в-бит прежний, включённый -- ровно обрезает.

ЗАЧЕМ. G4 (results/g4_descent_depth) измерил, что спуск sigma-супервизии к депонированному
профилю улучшает AAD на IDAC с 1.3142 до 0.8201, но у всех пяти сидов есть ВНУТРЕННИЙ оптимум
по глубине, и дальше оценка портится: выигрыш от глубины +0.5490 +- 0.1129, положителен 5/5.
Вмешательство -- пол на члене формы, ``relu(shape - floor)``: выше пола градиент прежний, на
полу и ниже -- нуль. Плечо стоит порядка 9 часов GPU, поэтому прибор проверяется до траты
квоты, как это уже делалось для detach-флага E2 (3818 против ровно нуля).

ТРИ УТВЕРЖДЕНИЯ, и третье не менее важно первых двух.
  1. При floor=0 выход И ГРАДИЕНТЫ бит-в-бит те же, что до правки. Ветвь пропускается целиком.
  2. Выше пола градиент бит-в-бит равен невзвешенному, а само значение сдвинуто ровно на пол:
     то есть пол не меняет НАПРАВЛЕНИЕ, только останавливает.
  3. На полу и ниже градиент РОВНО нуль, а не малый. Иначе плечо измеряло бы ослабление
     супервизии, а не её остановку -- разные вмешательства.
"""

from __future__ import annotations

import torch

from tgnn_solv.loss import sigma_profile_emd_loss

N_BINS = 51


def _batch(b: int = 6, seed: int = 0):
    gen = torch.Generator().manual_seed(seed)
    logit = torch.randn(b, N_BINS, generator=gen)
    target = torch.softmax(torch.randn(b, N_BINS, generator=gen), dim=-1)
    area_p = torch.rand(b, generator=gen) * 100 + 50
    area_t = torch.rand(b, generator=gen) * 100 + 50
    mask = torch.ones(b, dtype=torch.bool)
    return logit, target, area_p, area_t, mask


def _run(floor: float, seed: int = 0):
    logit, target, area_p, area_t, mask = _batch(seed=seed)
    logit = logit.clone().requires_grad_(True)
    area_p = area_p.clone().requires_grad_(True)
    total, comps = sigma_profile_emd_loss(
        torch.softmax(logit, dim=-1), target, area_p, area_t, mask,
        shape_floor=floor, return_components=True,
    )
    total.backward()
    return total.detach().clone(), logit.grad.clone(), area_p.grad.clone(), comps


def test_floor_zero_is_bit_identical() -> None:
    """Утверждение 1: выключенный пол не меняет ни выход, ни один градиент."""
    t0, g0, a0, c0 = _run(0.0)
    # Явный вызов БЕЗ аргумента вообще -- то, как зовёт контрольное плечо.
    logit, target, area_p, area_t, mask = _batch()
    logit = logit.clone().requires_grad_(True)
    area_p = area_p.clone().requires_grad_(True)
    total, comps = sigma_profile_emd_loss(
        torch.softmax(logit, dim=-1), target, area_p, area_t, mask,
        return_components=True,
    )
    total.backward()
    assert torch.equal(total.detach(), t0), (
        f"значение разошлось: {float(total)} против {float(t0)}"
    )
    assert torch.equal(logit.grad, g0) and torch.equal(area_p.grad, a0), (
        "градиент при floor=0 отличается от вызова без аргумента -- значит ветвь не "
        "пропускается, и контрольное плечо уже не контроль"
    )
    assert comps["sigma_shape"] == c0["sigma_shape"] == c0["sigma_shape_raw"]


def test_above_the_floor_only_the_value_shifts() -> None:
    """Утверждение 2: выше пола направление то же, значение сдвинуто ровно на пол."""
    t_raw, g_raw, a_raw, c_raw = _run(0.0)
    floor = c_raw["sigma_shape"] * 0.25          # заведомо ниже значения
    t_fl, g_fl, a_fl, c_fl = _run(floor)
    assert torch.equal(g_fl, g_raw), (
        "градиент по логитам изменился выше пола -- пол обязан только вычитать константу"
    )
    assert torch.equal(a_fl, a_raw), "градиент по площади не должен зависеть от пола формы"
    assert abs(float(t_raw - t_fl) - floor) < 1e-6, (
        f"сдвиг значения {float(t_raw - t_fl):.6f} не равен полу {floor:.6f}"
    )
    assert abs(c_fl["sigma_shape_raw"] - c_raw["sigma_shape"]) < 1e-6, (
        "sigma_shape_raw обязан нести НЕобрезанное значение: по нему идёт отбор чекпойнта "
        "разогрева, и он должен остаться сравнимым с контрольным плечом"
    )


def test_at_or_below_the_floor_the_gradient_is_exactly_zero() -> None:
    """Утверждение 3: на полу и ниже супервизия ОСТАНОВЛЕНА, а не ослаблена."""
    _, _, _, c_raw = _run(0.0)
    for mult in (1.0, 1.5, 10.0):                # пол на значении и выше него
        floor = c_raw["sigma_shape"] * mult
        t, g, a, c = _run(floor)
        assert float(g.abs().sum()) == 0.0, (
            f"при поле x{mult} от значения градиент по логитам не нуль, а "
            f"{float(g.abs().sum()):.3e} -- тогда плечо измеряет ослабление, не остановку"
        )
        assert c["sigma_shape"] == 0.0
        assert c["sigma_shape_raw"] > 0.0, "необрезанное значение обязано остаться видимым"
        assert float(a.abs().sum()) > 0.0, (
            "градиент по ПЛОЩАДИ обнулился вместе с формой -- пол обязан трогать только форму, "
            "иначе это два вмешательства, а не одно"
        )


def test_empty_mask_keeps_the_same_component_keys() -> None:
    """Набор ключей обязан совпадать: trainer симметризует словари по ключам.

    trainer.py строит {k: 0.5*(comps[k] + comps_slv[k]) for k in comps}, поэтому ветвь с
    пустой маской, отдающая другой набор ключей, уронила бы обучение по KeyError на смешанном
    батче -- и только на нём, то есть не на дымовом прогоне.
    """
    logit, target, area_p, area_t, _ = _batch()
    empty = torch.zeros(len(logit), dtype=torch.bool)
    _, c_empty = sigma_profile_emd_loss(
        torch.softmax(logit, -1), target, area_p, area_t, empty,
        shape_floor=0.4, return_components=True)
    _, c_full = _run(0.4)[3], None
    full_keys = set(_run(0.4)[3])
    assert set(c_empty) == full_keys, (
        f"ключи расходятся: пустая маска {sorted(c_empty)} против {sorted(full_keys)}"
    )
