#!/usr/bin/env python
"""G3: сколько взвешивание σ-супервизии способно купить ПРИ ИДЕАЛЬНО ОПТИМИЗИРУЕМОЙ ГОЛОВЕ.

ЗАЧЕМ ЭТО РАСЧЁТ МОЩНОСТИ, А НЕ ПРОВЕРКА ГИПОТЕЗЫ. Разведка E1 (PROJECT_MEMORY.md,
2026-10-03) установила две вещи. Первая: объявленный механизм недостижим одним членом лосса --
профиль есть softmax, якобиан даёт множитель p_i, выученная масса в углу меньше процента, и на
предписанном P0 весе 15x лосс ОСТАЁТСЯ анти-согласованным (rho -0.564). Вторая: объявленная
метрика физичности циркулярна -- вес E1 это d(ln gamma_inf)/d(p_bin) через CosmoSacLayer, а AAD
на IDAC это mean|CosmoSacLayer.ln_gamma_inf(p) - m| того же слоя, то есть вес есть производная
метрики по оптимизируемой переменной.

Отсюда замысел. Первое отказало на ОПТИМИЗИРУЕМОСТИ, а не на направлении: веса не доходят до
угла из-за параметризации, а не потому что указывают не туда. Значит остаётся вопрос, который
решается без квоты: ЕСЛИ голову оптимизировать идеально -- не через сеть, а прямо по логитам, --
сколько из разрыва 1.755 -> 1.131 (эталонная форма при выученной площади) взвешивание купит?

И здесь циркулярность работает НА НАС. Она смещает сравнение в пользу взвешенного плеча: метрика
есть первопорядковый образ того, по чему взвешенный член спускается. Поэтому МАЛЫЙ выигрыш здесь
-- это решающий негатив: если даже с подыгрывающей метрикой и снятым ограничением сети купить
нечего, то купить нечего и на GPU. Большой выигрыш решающим НЕ является и означает лишь, что
нужна независимая метрика.

КАК ОБЕСПЕЧЕН СОГЛАСОВАННЫЙ БЮДЖЕТ, и почему без этого сравнение бессмысленно. Взвешенный и
невзвешенный члены имеют РАЗНУЮ норму градиента, поэтому одинаковый шаг оптимизатора означает
разное пройденное расстояние, и «лучше» спуталось бы с «дальше». Здесь плечи сравниваются на
РАВНОМ ПРОЙДЕННОМ РАССТОЯНИИ В ПРОСТРАНСТВЕ ПРОФИЛЯ: спуск идёт до первого шага, на котором
||p - p0||_1 превышает заданную цель, и дальше профиль не двигается. Цели берутся сеткой, так
что читается вся траектория, а не одна точка.

ТРИ ПЛЕЧА, И ТРЕТЬЕ ОБЯЗАТЕЛЬНО. Невзвешенный член -- нулевое плечо по направлению. Взвешенный
по карте чувствительности -- проверяемое. И ПЕРЕМЕШАННЫЙ вес: тот же вектор с теми же mean и rms,
расставленный случайно. Без него «взвешивание помогает» не отличается от «любая неоднородность
помогает» -- та же ошибка, что проект уже ловил на функционале величины против расположения.

Параметризация: z инициализируется как log(p0) выученного профиля, так что softmax(z) = p0 в
точности и якобиан в начальной точке тот же, что у настоящей головы. Сеть при этом снята --
в этом и состоит «идеальная оптимизируемость».

    python scripts/analysis/run_g3_weight_reachability.py --seeds 42 --limit 40
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/analysis"))

from run_sigma_profile_residual import (  # noqa: E402
    PROFILES, TEST, build_model, hellinger, learned_profiles,
)
from tgnn_solv.data.utils import canonicalize  # noqa: E402
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles  # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
SENS = ROOT / "results/closure_sensitivity_map/sensitivity_real.npy"
OUT_DIR = ROOT / "results/g3_weight_reachability"


def _norm(x: np.ndarray) -> np.ndarray:
    """Нормировка профиля на единичную сумму -- форма без площади."""
    return x / np.clip(x.sum(-1, keepdims=True), 1e-30, None)


def emd_shape(p: torch.Tensor, t: torch.Tensor,
              w: torch.Tensor | None = None) -> torch.Tensor:
    """Член формы, как в loss.py:91-96: L1 между накопленными суммами нормированных профилей.

    ``w`` -- вес ПО БИНАМ на поэлементное кумулятивное отклонение. Это ровно та правка, которую
    E1 и предлагает (план, раздел 4, шаг 2): взвесить |C_k| до суммирования. При w=None порядок
    операций тот же, что в действующем лоссе.
    """
    ps = p / p.sum(-1, keepdim=True).clamp_min(1e-30)
    ts = t / t.sum(-1, keepdim=True).clamp_min(1e-30)
    d = (torch.cumsum(ps, -1) - torch.cumsum(ts, -1)).abs()
    if w is not None:
        d = w * d
    return d.sum(-1).mean()


def descend(p0: np.ndarray, target: np.ndarray, weight: np.ndarray | None,
            budgets: list[float], *, lr: float, max_steps: int) -> dict[float, np.ndarray]:
    """Спуск по логитам до каждого бюджета пройденного расстояния ||p-p0||_1.

    Возвращает профиль (в тех же единицах площади, что p0) на каждом бюджете. Площадь
    СОХРАНЯЕТСЯ: softmax даёт нормированную форму, которая домножается на исходную площадь.
    Это и есть «E1 трогает форму, не площадь».
    """
    area = p0.sum(-1, keepdims=True)
    shape0 = p0 / np.clip(area, 1e-30, None)
    z = torch.tensor(np.log(np.clip(shape0, 1e-12, None)), dtype=torch.float32,
                     requires_grad=True)
    t = torch.tensor(target / np.clip(target.sum(-1, keepdims=True), 1e-30, None),
                     dtype=torch.float32)
    w = None if weight is None else torch.tensor(weight, dtype=torch.float32)
    s0 = torch.tensor(shape0, dtype=torch.float32)
    # ПРОСТОЙ SGD, И ЭТО НЕ ВКУСОВОЕ РЕШЕНИЕ. Adam делит градиент каждой координаты на её
    # собственный RMS, а он масштабируется тем же весом w_k -- то есть Adam СОКРАЩАЕТ
    # взвешивание, и плечи стали бы неразличимы по построению оптимизатора, а не потому, что
    # направление не несёт информации. Первый прогон этого скрипта шёл на Adam и дал разницу
    # -0.0001; это был артефакт оптимизатора, а не результат. При согласовании по ПРОЙДЕННОМУ
    # расстоянию масштаб шага неважен, поэтому простого SGD достаточно и он честен.
    # ШАГ НОРМИРУЕТСЯ ПО НАЧАЛЬНОМУ ГРАДИЕНТУ. У взвешенного члена норма градиента меньше
    # (вес нормирован на mean 1, но анти-коррелирует с |C_k|), поэтому при одном lr он просто
    # НЕ ДОХОДИТ до больших бюджетов за разумное число шагов -- и сравнение потерялось бы не
    # на существе, а на числе итераций. Нормировка законна именно потому, что согласование
    # идёт по ПРОЙДЕННОМУ РАССТОЯНИЮ: длина отдельного шага на сравнение не влияет.
    _z0 = z.detach().clone().requires_grad_(True)
    emd_shape(torch.softmax(_z0, -1), t, w).backward()
    _g0 = float(_z0.grad.norm())
    opt = torch.optim.SGD([z], lr=lr / max(_g0, 1e-12))
    out: dict[float, np.ndarray] = {}
    todo = sorted(budgets)
    for _ in range(max_steps):
        if not todo:
            break
        opt.zero_grad()
        emd_shape(torch.softmax(z, -1), t, w).backward()
        opt.step()
        with torch.no_grad():
            moved = float((torch.softmax(z, -1) - s0).abs().sum(-1).mean())
        while todo and moved >= todo[0]:
            b = todo.pop(0)
            out[b] = (torch.softmax(z, -1).detach().numpy() * area)
    for b in todo:                                  # бюджет не достигнут за max_steps
        out[b] = None
    return out


def score_closure(p_solute: np.ndarray, p_solvent: np.ndarray, smiles: list[str],
                  records: pd.DataFrame) -> dict:
    """AAD на IDAC в ТОЧНОЙ конвенции депозита run_idac_learned_vs_reference.py.

    Три вещи скопированы оттуда дословно, и каждая меняла бы функционал:
      * ``CosmoSacLayer()`` с УМОЛЧАНИЯМИ -- тот же вызов, которым посчитан депонированный
        столбец ``g_res``; подставить cfg чекпойнта значило бы сравнивать с другим оператором;
      * ``V2=V1=None`` -- только ОСТАТОЧНЫЙ член. Комбинаторный требует мольных объёмов, у
        выученной стороны они не подключены, и ``g_res`` посчитан в той же конвенции ``res``;
      * ключи через ``canonicalize`` -- иначе SMILES пула не сойдутся с SMILES записей.

    Цель -- столбец ``m`` (ln gamma_inf опыта), как в depозите; разбиение по воде берётся из
    готового столбца ``aqueous``, а не из сравнения SMILES с "O".
    """
    layer = CosmoSacLayer()
    layer.eval()
    idx = {canonicalize(str(s)): i for i, s in enumerate(smiles)}
    k2 = [canonicalize(str(s)) for s in records.solute_smiles]
    k1 = [canonicalize(str(s)) for s in records.solvent_smiles]
    keep = np.array([(a in idx) and (b in idx) for a, b in zip(k2, k1)])
    if not keep.any():
        return {"n": 0}
    i2 = [idx[a] for a, ok in zip(k2, keep) if ok]
    i1 = [idx[b] for b, ok in zip(k1, keep) if ok]
    sub = records[keep]
    p2 = torch.tensor(p_solute[i2], dtype=torch.float)
    p1 = torch.tensor(p_solvent[i1], dtype=torch.float)
    with torch.no_grad():
        lng = layer.ln_gamma_inf(p2, p1, p2.sum(-1), p1.sum(-1), None, None,
                                 torch.tensor(sub["T_K"].to_numpy(), dtype=torch.float)).numpy()
    m = sub["m"].to_numpy(dtype=float)
    ok = np.isfinite(m) & np.isfinite(lng)
    d = (lng - m)[ok]
    aq = sub["aqueous"].to_numpy().astype(bool)[ok] if "aqueous" in sub.columns \
        else np.zeros(ok.sum(), dtype=bool)
    return {"n": int(ok.sum()), "aad": float(np.abs(d).mean()),
            "aad_water": (float(np.abs(d[aq]).mean()) if aq.any() else None),
            "aad_nonwater": (float(np.abs(d[~aq]).mean()) if (~aq).any() else None),
            "n_iter_eval": int(layer.n_iter_eval)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42])
    ap.add_argument("--limit", type=int, default=0, help="взять только N молекул пула")
    ap.add_argument("--budgets", type=float, nargs="+",
                    default=[0.02, 0.05, 0.10, 0.15, 0.20, 0.25],
                    help="цели по пройденному расстоянию ||p-p0||_1 в нормированной форме. "
                         "ВСЯ доступная дистанция до мишени измерена и равна ~0.2575, поэтому "
                         "бюджеты крупнее требуют пройти ДАЛЬШЕ, чем мишень находится")
    ap.add_argument("--lr", type=float, default=0.5,
                    help="шаг простого SGD по логитам; масштаб не влияет на "
                         "сравнение (оно на равном пройденном расстоянии), но влияет на "
                         "устойчивость: измерено, что при 0.5 невзвешенный спуск доходит до "
                         "мишени (остаётся 0.030 из 0.258), при 5.0 перелетает, при 50.0 "
                         "расходится -- поэтому крупный шаг не ускоряет, а ломает")
    ap.add_argument("--max-steps", type=int, default=4000)
    ap.add_argument("--records", type=Path,
                    default=ROOT / "results/published_idac_check/scored_records.csv")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    a = ap.parse_args()

    sens = np.load(SENS)
    sens = np.abs(sens).mean(0) if sens.ndim > 1 else np.abs(sens)
    sens = sens / sens.mean()                        # нормировка на mean 1, как при загрузке в E1
    rng = np.random.default_rng(0)
    shuffled = sens.copy()
    rng.shuffle(shuffled)                            # нуль по РАСПОЛОЖЕНИЮ: те же mean и rms

    records = pd.read_csv(a.records) if a.records.exists() else None
    if records is None:
        print(f"нет файла записей {a.records}; AAD считаться не будет")

    ref_table = load_sigma_profiles(str(PROFILES), n_bins=51)
    template = pd.read_csv(TEST, low_memory=False)

    rows, per_seed = [], {}
    for seed in a.seeds:
        ck = CKPT_DIR / f"grounded_a_seed{seed}.pt"
        if not ck.exists():
            print(f"нет чекпойнта {ck}")
            continue
        model, ckd, cfg = build_model(ck)
        n_iter = int(ckd["config"].get("cosmo_sac_gamma_iter_eval", cfg.cosmo_sac_gamma_iter_eval))
        # Ключи ref_table уже канонические (load_sigma_profiles канонизирует), а SMILES теста
        # сырые -- поэтому пересечение берётся по КАНОНИЧЕСКИМ с обеих сторон, иначе пул
        # молча вышел бы почти пустым.
        in_test = {canonicalize(str(x)) for col in ("solute_smiles", "solvent_smiles")
                   for x in template[col].dropna().unique()}
        pool = [s for s in ref_table if isinstance(s, str) and s in in_test]
        if a.limit:
            pool = pool[: a.limit]
        print(f"сид {seed}: молекул {len(pool)}, счёт итераций оценки {n_iter} (из ck['config'])")
        p_sol, p_slv = learned_profiles(model, cfg, pool, template)
        ref = np.vstack([ref_table[s][0] for s in pool])   # table[smi] = (p_sigma, area)

        base = {"seed": seed, "arm": "исходный выученный", "budget": 0.0,
                "h_to_ref_solute": float(np.mean([hellinger(p_sol[i], ref[i])
                                                  for i in range(len(pool))]))}
        if records is not None:
            base.update(score_closure(p_sol, p_slv, pool, records))
        rows.append(base)
        print(f"  исходный: AAD {base.get('aad')}, записей {base.get('n')}, "
              f"H до эталона {base['h_to_ref_solute']:.4f}")

        ARMS = (("невзвешенный", None), ("по чувствительности", sens),
                ("перемешанный вес", shuffled))
        for tag, w in ARMS:
            got_sol = descend(p_sol, ref, w, a.budgets, lr=a.lr, max_steps=a.max_steps)
            got_slv = descend(p_slv, ref, w, a.budgets, lr=a.lr, max_steps=a.max_steps)
            for b in a.budgets:
                ps, pv = got_sol.get(b), got_slv.get(b)
                if ps is None or pv is None:
                    print(f"  {tag:<22} бюджет {b}: НЕ достигнут за {a.max_steps} шагов")
                    rows.append({"seed": seed, "arm": tag, "budget": b, "unreached": True})
                    continue
                r = {"seed": seed, "arm": tag, "budget": b,
                     "l1_left_to_target": float(np.abs(_norm(ps) - _norm(ref)).sum(-1).mean()),
                     "h_to_ref_solute": float(np.mean([hellinger(ps[i], ref[i])
                                                       for i in range(len(pool))]))}
                if records is not None:
                    r.update(score_closure(ps, pv, pool, records))
                rows.append(r)
                print(f"  {tag:<22} бюджет {b:<5}: AAD {r.get('aad'):.4f}, "
                      f"до мишени {r['l1_left_to_target']:.4f}, H {r['h_to_ref_solute']:.4f}")
        per_seed[seed] = {"n_pool": len(pool), "n_iter_eval": n_iter}

    a.out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(a.out / "per_arm.csv", index=False)
    (a.out / "summary.json").write_text(json.dumps(
        {"seeds": a.seeds, "budgets": a.budgets, "lr": a.lr, "max_steps": a.max_steps,
         "per_seed": per_seed,
         "weight": {"source": str(SENS), "mean": 1.0,
                    "rms": float((sens ** 2).mean() ** 0.5),
                    "max_over_min": float(sens.max() / max(sens.min(), 1e-30))},
         "rows": rows}, ensure_ascii=False, indent=2))
    print(f"\n-> {a.out / 'summary.json'}")

    # --- Чтение: сколько купил каждый вес ПРИ РАВНОМ пройденном расстоянии ---
    if "aad" in df.columns:
        base_aad = df[df.arm.eq("исходный выученный")].aad.mean()
        print(f"\nAAD исходного выученного: {base_aad:.4f}")
        print(f"{'бюджет':>8}  {'невзвеш.':>10}  {'по чувств.':>11}  {'перемеш.':>10}  "
              f"{'выигрыш взвеш.':>15}  {'нуль располож.':>15}")
        for b in a.budgets:
            cut = df[df.budget.eq(b)]
            g = {t: cut[cut.arm.eq(t)].aad.mean() for t in
                 ("невзвешенный", "по чувствительности", "перемешанный вес")}
            if any(pd.isna(v) for v in g.values()):
                continue
            print(f"{b:>8}  {g['невзвешенный']:>10.4f}  {g['по чувствительности']:>11.4f}  "
                  f"{g['перемешанный вес']:>10.4f}  "
                  f"{g['невзвешенный'] - g['по чувствительности']:>+15.4f}  "
                  f"{g['невзвешенный'] - g['перемешанный вес']:>+15.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
