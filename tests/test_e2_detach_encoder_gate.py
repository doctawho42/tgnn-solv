"""Ворота контроля E2: `detach_crystal_from_encoder` режет ДРУГОЕ ребро, чем арм записи.

ЗАЧЕМ ЭТОТ ТЕСТ СУЩЕСТВУЕТ. E2 забанковал цену внешнего закрепления кристаллической ветви
(+0.2763 и +0.9275 `ln x2` на двух парах против пола 0.0744), но приписать её компенсации не
удалось: заявленная ось сменила знак между парами, разрез по давлению не сосредоточен. Остаётся
возражение, которое иначе назовёт референт: цена может быть ценой отрезания ЛЮБОГО
кристаллического градиентного пути, а не именно идентифицируемости. Контроль --
`detach_crystal_from_encoder`, и он стоит ~16 GPU-часов, то есть почти всю оставшуюся квоту.
Поэтому прибор проверяется ПЕРЕД тратой, а не после.

ЧТО ДЕЛАЕТ КАЖДЫЙ ФЛАГ (`model.py` раздел 6 и путь солвера):
  * ``detach_crystal_params_in_sle`` -- арм ЗАПИСИ. Режет путь солвер -> ПАРАМЕТРЫ кристалла:
    растворимость больше не может двигать T_m и dH_fus.
  * ``detach_crystal_from_encoder`` -- КОНТРОЛЬ. ``g_sol_for_crystal = g_sol_pre.detach()``
    (`model.py:1267`): кристаллическая голова читает отцеплённое вложение, то есть её потеря
    больше не формирует общий энкодер. Путь солвер -> параметры при этом ОСТАЁТСЯ ОТКРЫТ.

РЕШАЮЩЕЕ УТВЕРЖДЕНИЕ ЗДЕСЬ -- ЧЕТВЁРТОЕ. Если бы оба флага резали одно и то же ребро, контроль был
бы дубликатом арма записи и 16 часов ушли бы на повторение уже известного. Поэтому тест отдельно
проверяет, что при включённом контрольном флаге путь растворимости к параметрам кристалла ЖИВ -- то
есть контраст между двумя вмешательствами содержателен.
"""

from __future__ import annotations

import torch
from torch_geometric.data import Batch, Data

from tgnn_solv.config import TGNNSolvConfig
from tgnn_solv.model import TGNNSolv

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


def _model(**flags) -> TGNNSolv:
    cfg = TGNNSolvConfig(
        activity_model="cosmo_sac", hidden_dim=32, n_gnn_layers=2, n_cross_attn_layers=1,
        n_iter_train=2, n_iter_eval=2,
        cosmo_sac_gamma_iter_train=3, cosmo_sac_gamma_iter_eval=3,
        **flags,
    )
    torch.manual_seed(0)
    m = TGNNSolv(node_feat_dim=N_FEAT, edge_feat_dim=E_FEAT, cfg=cfg)
    m.train()
    return m


#: Модули, производящие ``g_sol_pre`` -- именно то вложение, которое флаг отцепляет. Имена взяты
#: из ``named_parameters`` живой модели, а не угаданы: словом «encoder» ни один параметр не назван,
#: и первая версия этого теста падала на пустом списке. Пост-взаимодействующие части
#: (``cross_attn_layers``, ``pair_repr``, ``solvent_moe``) сюда НЕ входят: они стоят после
#: разветвления и к отцепляемому ребру не относятся.
ENCODER_PREFIXES = ("gnn.", "readout.")


def _encoder_params(model: TGNNSolv):
    """Параметры общего энкодера, производящего отцепляемое вложение."""
    out = [(n, p) for n, p in model.named_parameters()
           if n.startswith(ENCODER_PREFIXES) and p.requires_grad]
    assert out, f"параметры энкодера не найдены по префиксам {ENCODER_PREFIXES}"
    return out


def _fusion_params(model: TGNNSolv):
    out = [(n, p) for n, p in model.named_parameters() if "fusion" in n.lower()]
    assert out, "кристаллическая голова не найдена -- тест смотрит не туда"
    return out


def _grad_sum(params) -> float:
    return sum(float(p.grad.abs().sum()) for _, p in params if p.grad is not None)


def _crystal_supervision_proxy(out) -> torch.Tensor:
    """Тот же канал, которым пользуется loss.py: ПРЕДсолверные выходы головы."""
    fp = out["fusion_params"]
    return fp["T_m"].sum() + fp["dH_fus"].sum()


def test_the_crystal_head_reaches_the_encoder_without_the_flag() -> None:
    """Нулевое плечо прибора: без флага потеря головы ДОЛЖНА формировать энкодер.

    Без этой половины нуль с флагом можно получить и потому, что ребра никогда не было, -- и тогда
    контроль отменяется, а не подтверждается.
    """
    model = _model(detach_crystal_from_encoder=False)
    sol, slv, tg = _pair()
    out, _ = model(sol, slv, tg["T"], targets=tg, return_intermediates=True)
    _crystal_supervision_proxy(out).backward()
    enc = _encoder_params(model)
    live = sum(1 for _, p in enc if p.grad is not None and float(p.grad.abs().sum()) > 0.0)
    assert live > 0, (
        "без флага кристаллическая голова не достаёт до энкодера -- значит резать нечего и "
        "контрольное плечо измерит не то, что заявлено")
    assert _grad_sum(enc) > 0.0


def test_the_flag_closes_the_head_to_encoder_edge_exactly() -> None:
    """С флагом градиент от головы в энкодер -- РОВНО нуль, а не малый."""
    model = _model(detach_crystal_from_encoder=True)
    sol, slv, tg = _pair()
    out, _ = model(sol, slv, tg["T"], targets=tg, return_intermediates=True)
    _crystal_supervision_proxy(out).backward()
    enc = _encoder_params(model)
    total = _grad_sum(enc)
    nonzero = sum(1 for _, p in enc if p.grad is not None and float(p.grad.abs().sum()) > 0.0)
    assert nonzero == 0 and total == 0.0, (
        f"при detach_crystal_from_encoder=True {nonzero} параметров энкодера всё ещё получают "
        f"градиент от кристаллической супервизии (суммарно {total:.3e}): ребро перекрыто НЕ "
        f"полностью, и контроль измерит ослабление, а не отсутствие")


def test_the_head_itself_still_learns_under_the_flag() -> None:
    """Голова жива: её собственные параметры получают градиент от своей супервизии.

    Иначе контрольное плечо сравнивало бы обученную голову с необученной, а не два способа её
    включения в граф.
    """
    model = _model(detach_crystal_from_encoder=True)
    sol, slv, tg = _pair()
    out, _ = model(sol, slv, tg["T"], targets=tg, return_intermediates=True)
    _crystal_supervision_proxy(out).backward()
    live = sum(1 for _, p in _fusion_params(model)
               if p.grad is not None and float(p.grad.abs().sum()) > 0.0)
    assert live > 0, "голова не учится даже на своей метке -- плечо сравнивало бы её с необученной"


def test_the_two_flags_cut_DIFFERENT_edges_so_the_control_is_not_a_duplicate() -> None:
    """РЕШАЮЩЕЕ. При контрольном флаге путь растворимость -> ПАРАМЕТРЫ кристалла обязан быть ЖИВ.

    Если оба флага перекрывают одно ребро, контроль -- дубликат арма записи, и 16 GPU-часов уйдут
    на повторение известного. Поэтому сравниваются оба флага на ОДНОМ канале: градиент от
    ``ln_x2`` (только растворимость, без кристаллической супервизии) в параметры головы.
    """
    def crystal_grad_from_solubility(**flags) -> float:
        model = _model(**flags)
        sol, slv, tg = _pair()
        out, _ = model(sol, slv, tg["T"], targets=tg, return_intermediates=True)
        out["ln_x2"].sum().backward()
        return _grad_sum(_fusion_params(model))

    base = crystal_grad_from_solubility()
    via_sle = crystal_grad_from_solubility(detach_crystal_params_in_sle=True)
    via_encoder = crystal_grad_from_solubility(detach_crystal_from_encoder=True)

    assert base > 0.0, "без флагов растворимость не давит на кристалл -- тест смотрит не туда"
    assert via_sle == 0.0, (
        "арм ЗАПИСИ обязан перекрывать этот путь ровно (это уже прибито "
        "test_e2_crystal_detach_gate.py; здесь -- опорная точка сравнения)")
    assert via_encoder > 0.0, (
        f"при detach_crystal_from_encoder=True путь растворимость -> параметры кристалла тоже "
        f"перекрыт (градиент {via_encoder:.3e}), то есть контроль РЕЖЕТ ТО ЖЕ РЕБРО, что арм "
        f"записи, и 16 GPU-часов уйдут на дубликат. Контроль в этом виде ставить нельзя.")
