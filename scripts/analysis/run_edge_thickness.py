#!/usr/bin/env python
"""Толщина двух кристаллических рёбер: что КАЖДЫЙ флаг фактически убирает, в долях.

ЗАЧЕМ. Предзаявка контроля атрибуции E2 (`results/e2_crystal_detach/PRE_DECLARATION.md`, раздел о
плече `grounded_a_detachencoder`) объявила это измерение ЧАСТЬЮ ОТЧЁТА: без него отношение цен двух
вмешательств читается как «цена ребра», хотя может быть «толщина ребра». Если одно ребро несёт в
разы больше градиента, разная цена объясняется этим и ничем больше.

КАК ОПЕРАЦИОНАЛИЗИРОВАНО, И ПОЧЕМУ ИМЕННО ТАК. Соблазн -- самому выписать, какой градиент течёт по
какому пути, и сложить. Это полагалось бы на моё понимание графа, а графы в этом проекте уже
обманывали: селектор параметров энкодера в первой версии ворот искал слово «encoder», которого ни в
одном имени нет. Поэтому рёбра определяются САМИМИ ФЛАГАМИ: считается градиент с флагом и без, и
берётся разница. Что флаг убирает -- то и есть его ребро, по определению.

Прямое сравнение суммарных |grad| двух каналов было бы сопоставлением несопоставимого: они идут в
РАЗНЫЕ наборы параметров (голова против энкодера). Поэтому сравниваются ДОЛИ -- какую часть полного
градиента своего назначения уносит каждое ребро.

ЧЕГО ЭТО ИЗМЕРЕНИЕ НЕ ГОВОРИТ. Толщина взята в ОБУЧЕННОМ состоянии КОНТРОЛЬНОГО плеча, на реальных
строках. Флаги меняют динамику обучения, поэтому толщина в оптимуме контроля -- не толщина на
протяжении обучения. Это одна точка траектории, и так это и надо докладывать.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_edge_thickness.py \
        --checkpoint <grounded_a_seedNN.pt> --data notebooks/data/processed/test.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import torch

from tgnn_solv.data.dataset import make_loader
from tgnn_solv.inference import load_model

#: Каналы, по которым берётся градиент: потеря растворимости и кристаллическая супервизия.
#: Супервизия берётся с ПРЕДсолверных выходов головы -- тот же канал, которым пользуется loss.py.
ENCODER_PREFIXES = ("gnn.", "readout.")
HEAD_SUBSTRING = "fusion"


def _grad_sum(model: torch.nn.Module, select) -> float:
    return sum(float(p.grad.abs().sum()) for n, p in model.named_parameters()
               if select(n) and p.grad is not None)


def _is_encoder(name: str) -> bool:
    return name.startswith(ENCODER_PREFIXES)


def _is_head(name: str) -> bool:
    return HEAD_SUBSTRING in name.lower()


#: Формы и веса -- как в настоящей потере, а НЕ сумма сырых выходов. Huber delta=1.0 на ln_x2
#: (`loss.py:159`), masked MSE на выходе головы со шкалой 50 K (`loss.py:155`), веса фазы 2:
#: растворимость 1.0, кристалл 0.05 (`trainer.py:70`). Те же константы, что в
#: `run_crystal_pressure_gate.py`.
#: Единый сид маскирования: все три конфигурации видят ОДНИ маски dropout (парное сравнение).
DROPOUT_SEED = 20261019
#: Изменяется из main по --dropout-seed; список, чтобы measure() читал текущее значение.
_dropout_seed = [DROPOUT_SEED]
HUBER_DELTA = 1.0
S_TM = 50.0
W_SOL, W_CRY = 1.0, 0.05


def both_channels(out: dict, tg: dict) -> torch.Tensor:
    """Взвешенная потеря двух каналов, которые режут флаги.

    ПЕРВАЯ ВЕРСИЯ ЭТОЙ ФУНКЦИИ БЫЛА НЕВЕРНА, и числа это показали. Она складывала СЫРЫЕ выходы --
    ``ln_x2.sum() + T_m.sum() + dH_fus.sum()``. Член с ``T_m`` измеряется в сотнях кельвинов и
    подавлял ``ln_x2`` на порядки: суммарные |grad| вышли 1e8-1e9, ребро A показало -0.0%
    (хотя ворота ДОКАЗАЛИ, что флаг зануляет его ровно), а ребро B -- 100%, потому что при
    доминирующем кристаллическом члене почти весь градиент энкодера и идёт через кристаллическую
    голову. Это ровно «измерил не ту поверхность»: удобная сумма вместо потери, которую обучение
    минимизирует.
    """
    pred = out["ln_x2"]
    true = tg["ln_x2"] if "ln_x2" in tg else tg.get("ln_x2_true")
    assert true is not None, "в батче нет истинного ln_x2 -- канал растворимости не построить"
    mask = tg.get("has_solubility")
    r = pred - true.to(pred)
    hub = torch.where(r.abs() <= HUBER_DELTA, 0.5 * r ** 2,
                      HUBER_DELTA * (r.abs() - 0.5 * HUBER_DELTA))
    if mask is not None:
        m = mask.to(pred.device).bool()
        hub = hub[m]
    sol_loss = hub.mean() if hub.numel() else pred.sum() * 0.0

    fp = out["fusion_params"]
    cry_terms = []
    for key, scale in (("T_m", S_TM), ("dH_fus", None)):
        if key not in fp or key not in tg:
            continue
        has = tg.get(f"has_{key}")
        d = (fp[key] - tg[key].to(fp[key])) / (scale if scale else tg[key].abs().clamp(min=1.0))
        if has is not None:
            hm = has.to(d.device).bool()
            d = d[hm]
        if d.numel():
            cry_terms.append((d ** 2).mean())
    cry_loss = sum(cry_terms) / len(cry_terms) if cry_terms else sol_loss * 0.0
    return W_SOL * sol_loss + W_CRY * cry_loss


def measure(model, batches, *, flag: str | None) -> dict[str, float]:
    """Суммарный |grad| в голове и в энкодере при заданном флаге (или без флагов).

    ФЛАГ ПЕРЕКЛЮЧАЕТСЯ В ``model.cfg``, А НЕ ПЕРЕДАЁТСЯ В forward, и это не обход. ``forward``
    принимает kwarg только для одного из двух флагов (``model.py:1026``), второй читается из
    конфига (``model.py:1281``) -- первая версия этого скрипта упала на
    ``unexpected keyword argument``. Сам тренер делает ровно это:
    ``self.model.cfg.detach_crystal_params_in_sle = ...`` (``trainer.py:328``). То есть
    переключается ТОТ ЖЕ выключатель, которым пользуется обучение, и единообразно для обоих рёбер.
    """
    # ОДИН И ТОТ ЖЕ DROPOUT НА ВСЕ ТРИ КОНФИГУРАЦИИ. Первая версия этого не делала, и числа
    # поплыли между прогонами (80.3 -> 80.7%, 52.8 -> 54.3%): три конфигурации видели РАЗНЫЕ маски,
    # поэтому их различия несли ещё и разницу масок, а не только эффект флага. Сравнение обязано
    # быть ПАРНЫМ, иначе измеряется сумма эффекта и шума маскирования.
    torch.manual_seed(_dropout_seed[0])
    saved = {k: getattr(model.cfg, k) for k in
             ("detach_crystal_params_in_sle", "detach_crystal_from_encoder")}
    if flag is not None:
        setattr(model.cfg, flag, True)
    try:
        model.zero_grad(set_to_none=True)
        for sol, slv, tg in batches:
            out, _ = model(sol, slv, tg["T"], targets=tg, return_intermediates=True)
            both_channels(out, tg).backward()
        return {"head": _grad_sum(model, _is_head), "encoder": _grad_sum(model, _is_encoder)}
    finally:
        for k, v in saved.items():
            setattr(model.cfg, k, v)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--data", default="notebooks/data/processed/test.csv")
    ap.add_argument("--batches", type=int, default=8, help="сколько батчей усреднять")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--dropout-seed", type=int, default=DROPOUT_SEED,
                    help="сид маскирования. Парность он обеспечивает при любом значении; "
                         "менять его стоит, чтобы узнать, с какой точностью докладывать ДОЛИ -- "
                         "различия устойчивы по построению, абсолютные доли условны по розыгрышу.")
    ap.add_argument("--out", type=Path,
                    default=Path("results/e2_crystal_detach/edge_thickness.json"))
    a = ap.parse_args()

    _dropout_seed[0] = int(a.dropout_seed)
    device = torch.device("cpu")
    model, cfg = load_model(a.checkpoint, device=device)
    model.train()                      # градиенты, а не оценка; dropout влияет на величину, не на знак
    assert cfg.detach_crystal_params_in_sle is False and cfg.detach_crystal_from_encoder is False, \
        "толщину рёбер мерим на КОНТРОЛЬНОМ плече, где оба ребра целы"

    df = pd.read_csv(a.data)
    loader = make_loader(df, a.batch_size, shuffle=False, num_workers=0)
    batches = []
    for i, batch in enumerate(loader):
        if i >= a.batches:
            break
        sol, slv, tg = batch[0], batch[1], batch[2]
        batches.append((sol, slv, tg))
    assert batches, "ни одного батча не собрано"

    base = measure(model, batches, flag=None)
    no_sle = measure(model, batches, flag="detach_crystal_params_in_sle")
    no_enc = measure(model, batches, flag="detach_crystal_from_encoder")

    # Что каждый флаг УБИРАЕТ у своего назначения, в долях полного градиента этого назначения.
    edge_a = (base["head"] - no_sle["head"]) / base["head"] if base["head"] else float("nan")
    edge_b = (base["encoder"] - no_enc["encoder"]) / base["encoder"] if base["encoder"] else float("nan")

    # ПОЛНЫЙ КРЕСТ оказался информативнее, чем объявленное сравнение толщин, и вот чем.
    # Флаг ЗАПИСИ режет 80% градиента ГОЛОВЫ и ~47% градиента ЭНКОДЕРА; флаг КОНТРОЛЯ не трогает
    # голову вовсе и режет ~53% энкодера. То есть по энкодеру два вмешательства почти СОГЛАСОВАНЫ,
    # а различаются на канале головы. Значит контраст двух плеч изолирует канал головы при почти
    # совпадающем возмущении энкодера -- это довод в пользу контроля, которого предзаявка не
    # предвидела, и он сильнее, чем просто «рёбра сопоставимы по толщине».
    cross = {
        "head": {"by_detach_params_in_sle": (base["head"] - no_sle["head"]) / base["head"],
                 "by_detach_from_encoder": (base["head"] - no_enc["head"]) / base["head"]},
        "encoder": {"by_detach_params_in_sle": (base["encoder"] - no_sle["encoder"]) / base["encoder"],
                    "by_detach_from_encoder": (base["encoder"] - no_enc["encoder"]) / base["encoder"]},
    }

    rec = {
        "checkpoint": a.checkpoint, "data": a.data,
        "cross_shares_removed": cross,
        "encoder_perturbation_matched": abs(
            cross["encoder"]["by_detach_params_in_sle"]
            - cross["encoder"]["by_detach_from_encoder"]) < 0.15,
        "batches": len(batches), "batch_size": a.batch_size,
        "grad_sums": {"no_flags": base, "detach_params_in_sle": no_sle,
                      "detach_from_encoder": no_enc},
        "edge_A_share_of_head_gradient_removed": edge_a,
        "edge_B_share_of_encoder_gradient_removed": edge_b,
        "thickness_ratio_A_over_B": edge_a / edge_b if edge_b else None,
        "what_this_does_not_say": (
            "Толщина взята в ОБУЧЕННОМ состоянии контрольного плеча, одна точка траектории. "
            "Флаги меняют динамику обучения, поэтому это не толщина на протяжении обучения."),
    }

    print("ТОЛЩИНА ДВУХ КРИСТАЛЛИЧЕСКИХ РЁБЕР (контрольное плечо, оба ребра целы)\n")
    print(f"  батчей {len(batches)} по {a.batch_size}; градиент от двух каналов "
          f"(растворимость + кристаллическая супервизия)\n")
    print(f"{'конфигурация':34s} {'|grad| голова':>16s} {'|grad| энкодер':>16s}")
    for lbl, v in (("без флагов", base), ("detach_params_in_sle", no_sle),
                   ("detach_from_encoder", no_enc)):
        print(f"{lbl:34s} {v['head']:16.4e} {v['encoder']:16.4e}")
    print()
    print(f"  РЕБРО A (режет арм ЗАПИСИ): убирает {100 * edge_a:.1f}% градиента ГОЛОВЫ")
    print(f"  РЕБРО B (режет КОНТРОЛЬ):   убирает {100 * edge_b:.1f}% градиента ЭНКОДЕРА")
    if edge_b:
        print(f"  отношение долей A/B = {edge_a / edge_b:.2f}  (это отношение ДОЛЕЙ у РАЗНЫХ "
              f"знаменателей, не отношение абсолютных толщин)")
    print()
    print("  ПОЛНЫЙ КРЕСТ -- что каждый флаг убирает у каждого назначения:")
    print(f"{'':30s} {'голова':>12s} {'энкодер':>12s}")
    for lbl, key in (("флаг ЗАПИСИ", "by_detach_params_in_sle"),
                     ("флаг КОНТРОЛЯ", "by_detach_from_encoder")):
        print(f"  {lbl:28s} {100 * cross['head'][key]:11.1f}% {100 * cross['encoder'][key]:11.1f}%")
    d = abs(cross["encoder"]["by_detach_params_in_sle"]
            - cross["encoder"]["by_detach_from_encoder"])
    print(f"  расхождение по ЭНКОДЕРУ между флагами: {100 * d:.1f} п.п. -> "
          f"{'возмущение энкодера ПОЧТИ СОГЛАСОВАНО' if d < 0.15 else 'НЕ согласовано'}")
    print("  (если согласовано, контраст двух плеч изолирует канал ГОЛОВЫ -- довод в пользу "
          "контроля, которого предзаявка не предвидела)")
    print(f"\n{rec['what_this_does_not_say']}")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    print(f"\nзаписано {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
