"""Векторизованный мост плоское/плотное тождественен четырём питоновским циклам.

ЗАЧЕМ ЭТОТ ФАЙЛ. ``TGNNSolv.forward`` раньше собирал вход cross-attention так: резал плоский
атомный тензор на B кусков булевой индексацией (``_split_atoms_by_graph``), приклеивал к
каждому глобальный токен (``_append_global_token``), сваливал список в плотный тензор
присваиванием B срезов (``pad_atom_features``), а на обратном пути нарезал обратно
(``_slice_padded``) и ЗАНОВО собирал вектор принадлежности графам из B вызовов ``full``
(``build_batch_from_lists``). Шесть циклов по 64 графам на сторону, две стороны.

Профиль настоящего шага на T4 (2026-10-02, results/real_step_profile/summary.json) показал,
что именно этот класс операций и есть цена шага: 63% диспатчей растут РОВНО пропорционально
батчу, то есть платятся за молекулу, а не за шаг, и крупный батч их не амортизирует (батч x8
дал всего x1.39 строк в секунду при падении загрузки карты с 22% до 17%). Поэтому мост
переписан на ``to_dense_batch`` плюс один ``index_put``.

ЧТО ЗДЕСЬ ПРОВЕРЯЕТСЯ -- три утверждения, на которых держится правка, и каждое по отдельности:
  1. плотный тензор и маска совпадают со старой цепочкой побитово;
  2. ``dense[atom_mask]`` возвращает атомы в ИСХОДНОМ плоском порядке -- именно поэтому
     обратный путь больше не восстанавливает вектор принадлежности, а берёт ``data.batch``;
  3. позиции токенов совпадают со старыми ``lengths - 1``.

Стимул включает вырожденные случаи, на которых правка и могла бы разойтись: граф из одного
атома, граф ровно на N_max (его токен попадает в ДОПОЛНЕННЫЙ столбец, а не в padding), и
порядок размеров, при котором самый большой граф идёт не последним.
"""

from __future__ import annotations

import pytest
import torch
from torch_geometric.data import Batch, Data

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.layers import pad_atom_features
from tgnn_solv.model import TGNNSolv

D = 8

#: Наборы размеров графов. Последний -- тот, где самый большой граф не последний в батче.
SIZE_SETS = [
    [1],
    [1, 1],
    [3, 1, 5],
    [5, 3, 1],
    [7, 7, 7],
    [2, 9, 4, 1, 9],
]


def _batch(sizes: list[int]) -> tuple[Batch, torch.Tensor]:
    """Batch из графов заданных размеров плюс плоский тензор признаков в его порядке."""
    gen = torch.Generator().manual_seed(len(sizes) * 100 + sum(sizes))
    datas = [Data(x=torch.randn(n, D, generator=gen)) for n in sizes]
    b = Batch.from_data_list(datas)
    return b, b.x.clone()


def _old_bridge(model: TGNNSolv, h: torch.Tensor, data: Batch, token: torch.Tensor):
    """Ровно старая цепочка, через те же помощники, которые из репозитория не удалены."""
    lst = model._append_global_token(
        model._split_atoms_by_graph(h, data.batch), token
    )
    padded, full_mask = pad_atom_features(lst)
    lengths = [t.shape[0] for t in lst]
    flat_no_token = torch.cat(
        [padded[i, : lengths[i] - 1, :] for i in range(len(lengths))], dim=0
    )
    tokens = padded[
        torch.arange(len(lengths)), torch.tensor([n - 1 for n in lengths])
    ]
    return padded, full_mask, flat_no_token, tokens, lengths


@pytest.fixture(scope="module")
def model() -> TGNNSolv:
    cfg = TGNNSolvConfig(activity_model="cosmo_sac", hidden_dim=D)
    return TGNNSolv(node_feat_dim=D, edge_feat_dim=4, cfg=cfg)


@pytest.mark.parametrize("sizes", SIZE_SETS, ids=[str(s) for s in SIZE_SETS])
def test_dense_bridge_matches_the_python_loops(model: TGNNSolv, sizes: list[int]) -> None:
    """Утверждения 1 и 3: плотный тензор, маска и позиции токенов -- те же."""
    data, h = _batch(sizes)
    # Форма как у настоящего параметра: model.py:253 -- nn.Parameter(torch.zeros(1, 1, F)),
    # и _append_global_token берёт token[0], рассчитывая получить (1, D).
    token = torch.randn(1, 1, D, generator=torch.Generator().manual_seed(7))

    dense, atom_mask, full_mask, counts = model._to_dense_with_token(h, data, token)
    padded_old, full_old, _, tokens_old, lengths = _old_bridge(model, h, data, token)

    assert dense.shape == padded_old.shape, (
        f"формы разошлись: {tuple(dense.shape)} против {tuple(padded_old.shape)}. "
        "Cross-attention увидит другой N_max, то есть это уже другой оператор."
    )
    assert torch.equal(dense, padded_old), (
        f"плотный тензор разошёлся, max|Δ| = {(dense - padded_old).abs().max():.3e}"
    )
    assert torch.equal(full_mask, full_old), "маска вместе с токеном разошлась"
    assert counts.tolist() == [n - 1 for n in lengths], (
        f"позиции токенов разошлись: {counts.tolist()} против {[n - 1 for n in lengths]}"
    )
    assert torch.equal(model._gather_tokens(dense, counts), tokens_old), (
        "выбранные глобальные токены разошлись"
    )


@pytest.mark.parametrize("sizes", SIZE_SETS, ids=[str(s) for s in SIZE_SETS])
def test_atom_mask_restores_the_original_flat_order(
    model: TGNNSolv, sizes: list[int]
) -> None:
    """Утверждение 2 -- то, ради чего убрана сборка вектора принадлежности.

    Если бы ``dense[atom_mask]`` возвращал атомы в другом порядке, то readout получал бы
    признаки одного графа с метками другого, и ошибка была бы тихой: формы совпадают,
    градиенты текут, метрики просто хуже. Поэтому проверяется и порядок, и то, что
    ``data.batch`` ему соответствует.
    """
    data, h = _batch(sizes)
    # Форма как у настоящего параметра: model.py:253 -- nn.Parameter(torch.zeros(1, 1, F)),
    # и _append_global_token берёт token[0], рассчитывая получить (1, D).
    token = torch.randn(1, 1, D, generator=torch.Generator().manual_seed(7))
    dense, atom_mask, _, _ = model._to_dense_with_token(h, data, token)

    assert torch.equal(dense[atom_mask], h), (
        "обратный путь вернул атомы НЕ в исходном порядке -- значит data.batch им больше "
        "не соответствует, и readout смешает графы молча"
    )
    _, _, flat_old, _, _ = _old_bridge(model, h, data, token)
    assert torch.equal(dense[atom_mask], flat_old), "расхождение со старой нарезкой"
    assert int(atom_mask.sum()) == h.shape[0], "маска по атомам покрывает не все атомы"
    assert data.batch.shape[0] == h.shape[0]


def test_graph_count_needs_no_host_sync(model: TGNNSolv) -> None:
    """B берётся из формы ``ptr``, а не чтением значения тензора на CPU.

    ``batch.max().item()`` -- блокирующая синхронизация: профиль насчитал 531.5 таких точек
    на шаг. ``ptr.numel()`` -- запрос формы, он бесплатен. Запасной путь для данных без
    ``ptr`` сохранён, и он тоже проверяется.
    """
    data, _ = _batch([3, 1, 5])
    assert model._graph_count(data) == 3
    assert data.ptr is not None, "у Batch должен быть ptr, иначе правка теряет смысл"

    class NoPtr:
        ptr = None
        batch = torch.tensor([0, 0, 1, 2, 2])

    assert model._graph_count(NoPtr()) == 3
