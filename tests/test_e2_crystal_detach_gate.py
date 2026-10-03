"""E2: флаг действительно перекрывает путь градиента из растворимости в кристаллическую ветвь.

ЗАЧЕМ ЭТОТ ТЕСТ СУЩЕСТВУЕТ. E2 спрашивает: если не просить растворимость идентифицировать
T_m и dH_fus, перестанет ли активностная ветвь прятать в них свою ошибку? Вмешательство --
один флаг ``detach_crystal_params_in_sle``, а цена ответа -- порядка 20 GPU-часов на плечо.
Поэтому прежде чем их тратить, надо убедиться, что ПРИБОР ВООБЩЕ СРАБАТЫВАЕТ: что флаг
перекрывает именно тот канал, о котором идёт речь, и что без флага канал открыт. Проект уже
терял направления на обратном -- на зонде, который оценивал необученную сеть так же, как
обученную, и на арме, чьи три "ремонтных" коммита её ни разу не касались.

ОСНОВАНИЕ САМОГО E2 -- теорема, не догадка: при dCp = 0 член Phi аффинен по 1/T, активностный
класс эту плоскость натягивает, и профилированная информация Фишера по dH_fus равна НУЛЮ
(SI.tex:697). Эмпирически на оценочной поверхности dH_fus измерен у одного растворяемого, T_m
у 31 из 147. Бесплатные ворота (коммит 8126156) показали, что градиентное давление из потери
растворимости на T_m превышает давление кристаллической супервизии в 4.7 раза, то есть
замораживать есть что.

ЧТО ЗДЕСЬ МЕРИТСЯ. Градиент берётся ТОЛЬКО от члена растворимости (``ln_x2.sum()``), без
кристаллической супервизии -- иначе нулевого контраста не получить, потому что головы
обязаны продолжать учиться на внешних метках, и это часть замысла, а не побочный эффект.
"""

from __future__ import annotations

import torch

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.model import TGNNSolv
from torch_geometric.data import Batch, Data

N_FEAT, E_FEAT = 16, 4


def _pair(n_atoms: int = 5, b: int = 3):
    gen = torch.Generator().manual_seed(11)

    def one():
        datas = []
        for _ in range(b):
            ei = torch.stack([torch.arange(n_atoms - 1), torch.arange(1, n_atoms)])
            ei = torch.cat([ei, ei.flip(0)], dim=1)
            datas.append(Data(x=torch.randn(n_atoms, N_FEAT, generator=gen),
                              edge_index=ei,
                              edge_attr=torch.randn(ei.shape[1], E_FEAT, generator=gen)))
        return Batch.from_data_list(datas)

    targets = {
        "T": torch.full((b,), 298.15),
        "T_m": torch.full((b,), 400.0),
        "dH_fus": torch.full((b,), 20000.0),
        "has_T_m": torch.ones(b, dtype=torch.bool),
        "has_dH_fus": torch.ones(b, dtype=torch.bool),
    }
    return one(), one(), targets


def _crystal_grad_from_solubility(detach: bool) -> tuple[float, int, int]:
    """Суммарный |grad| кристаллической головы от одного только ln_x2."""
    cfg = TGNNSolvConfig(
        activity_model="cosmo_sac", hidden_dim=32, n_gnn_layers=2, n_cross_attn_layers=1,
        n_iter_train=2, n_iter_eval=2,
            cosmo_sac_gamma_iter_train=3, cosmo_sac_gamma_iter_eval=3,
        detach_crystal_params_in_sle=detach,
    )
    torch.manual_seed(0)
    model = TGNNSolv(node_feat_dim=N_FEAT, edge_feat_dim=E_FEAT, cfg=cfg)
    model.train()
    sol, slv, tg = _pair()
    out, _ = model(sol, slv, tg["T"], targets=tg, return_intermediates=True)
    out["ln_x2"].sum().backward()
    params = [(n, p) for n, p in model.named_parameters() if "fusion" in n.lower()]
    total = sum(p.grad.abs().sum().item() for _, p in params if p.grad is not None)
    nonzero = sum(1 for _, p in params
                  if p.grad is not None and float(p.grad.abs().sum()) > 0.0)
    return total, nonzero, len(params)


def test_the_channel_is_open_without_the_flag() -> None:
    """Нулевое плечо прибора: без флага растворимость ДОЛЖНА давить на кристалл.

    Без этой половины тест бесполезен: нуль с флагом можно получить и потому, что канала
    никогда не было, и тогда E2 отменяется, а не подтверждается.
    """
    total, nonzero, n = _crystal_grad_from_solubility(detach=False)
    assert n > 0, "кристаллическая голова не найдена -- тест смотрит не туда"
    assert nonzero == n, (
        f"только {nonzero} из {n} параметров кристаллической головы получают градиент из "
        "ln_x2. Значит канал уже частично перекрыт чем-то другим, и контраст E2 измерит не "
        "то, что заявлено."
    )
    assert total > 0.0


def test_the_flag_closes_the_channel_exactly() -> None:
    """С флагом градиент из растворимости в кристалл -- РОВНО нуль, а не малый."""
    total, nonzero, n = _crystal_grad_from_solubility(detach=True)
    assert nonzero == 0 and total == 0.0, (
        f"при detach_crystal_params_in_sle=True {nonzero} из {n} параметров всё ещё получают "
        f"градиент из ln_x2 (суммарно {total:.3e}). Путь перекрыт НЕ полностью, и плечо E2 "
        "будет измерять ослабление канала, а не его отсутствие."
    )


def test_the_contrast_is_not_an_artifact_of_a_dead_head() -> None:
    """Голова жива: кристаллическая супервизия давит на неё при ЛЮБОМ значении флага.

    Замысел E2 -- оставить головам внешние метки и отнять у них только растворимость. Если бы
    флаг заодно убивал обучение по меткам, плечо сравнивало бы обученную голову с
    необученной, а не два способа её обучать.
    """
    for detach in (False, True):
        cfg = TGNNSolvConfig(
            activity_model="cosmo_sac", hidden_dim=32, n_gnn_layers=2, n_cross_attn_layers=1,
            n_iter_train=2, n_iter_eval=2,
            cosmo_sac_gamma_iter_train=3, cosmo_sac_gamma_iter_eval=3,
            detach_crystal_params_in_sle=detach,
        )
        torch.manual_seed(0)
        model = TGNNSolv(node_feat_dim=N_FEAT, edge_feat_dim=E_FEAT, cfg=cfg)
        model.train()
        sol, slv, tg = _pair()
        out, _ = model(sol, slv, tg["T"], targets=tg, return_intermediates=True)
        # Прокси кристаллической супервизии: тот же канал, которым пользуется loss.py.
        # T_m и dH_fus лежат в out["fusion_params"] -- это ПРЕДсолверные значения, то есть
        # ровно те, по которым идёт супервизия внешними метками; out["solver_fusion_params"]
        # взяты уже после detach и для этой проверки не годятся по построению.
        fp = out["fusion_params"]
        (fp["T_m"].sum() + fp["dH_fus"].sum()).backward()
        params = [p for n, p in model.named_parameters() if "fusion" in n.lower()]
        live = sum(1 for p in params
                   if p.grad is not None and float(p.grad.abs().sum()) > 0.0)
        assert live > 0, (
            f"при detach={detach} кристаллическая голова не получает градиента даже от своей "
            "СОБСТВЕННОЙ супервизии -- значит плечо E2 сравнивало бы необученную голову с "
            "обученной, а не две схемы обучения"
        )
