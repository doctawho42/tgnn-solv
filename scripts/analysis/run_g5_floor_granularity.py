#!/usr/bin/env python
"""G5: пол на члене формы -- по пулёвому среднему или НА МОЛЕКУЛУ?

ЗАЧЕМ. Плечо grounded_a_shapefloor (коммит a67de03) ставит пол на ПУЛЁВОМ СРЕДНЕМ, потому что
именно его мерил G4: спуск там минимизировал среднее по пулу, и выигрыш +0.5490 +- 0.1129
относится к этому режиму. Но разброс EMD ПО МОЛЕКУЛАМ внутри сида оказался в 4.5 раза больше
межсидового (sd 0.4349 против 0.0973, размах p10..p90 от 0.299 до 1.403), и 21.3% молекул
СТАРТУЮТ уже ниже порога 0.40. Значит пол по среднему продавливает эту пятую часть далеко за
её собственный оптимум, пока среднее идёт к порогу.

Отсюда вопрос, который надо решить ДО траты квоты: не лучше ли останавливать КАЖДУЮ молекулу
на её собственной глубине. Вариант «на молекулу» G4 не мерил, поэтому ставить его в плечо без
замера значило бы отклониться от измеренного основания -- ровно та ошибка, за которую этот
проект уже платил.

ЧЕМ ЭТО ОТЛИЧАЕТСЯ ОТ G3 И G4. Там сравнение шло на РАВНОМ ПРОЙДЕННОМ расстоянии, потому что
вопрос был о направлении (вес) и о глубине. Здесь вопрос о ГРАНУЛЯРНОСТИ остановки, поэтому
оба плеча идут до своего естественного останова по одному и тому же порогу, а пройденное
расстояние у них законно разное -- оно и есть предмет сравнения.

ТРЕТЬЕ ПЛЕЧО ОБЯЗАТЕЛЬНО: спуск до того же ПУЛЁВОГО среднего, но без всякой остановки по
молекулам, обрезанный на том же числе шагов. Без него «на молекулу лучше» не отличается от
«просто меньше суммарного смещения».

    python scripts/analysis/run_g5_floor_granularity.py --seeds 42 43 44 45 46
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

from run_g3_weight_reachability import (  # noqa: E402
    _norm, score_closure,
)
from run_sigma_profile_residual import (  # noqa: E402
    PROFILES, TEST, build_model, hellinger, learned_profiles,
)
from tgnn_solv.data.utils import canonicalize  # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles  # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
OUT_DIR = ROOT / "results/g5_floor_granularity"


def per_mol_emd(shape: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """EMD на молекулу -- то же, что считает член формы, но без усреднения."""
    return (torch.cumsum(shape, -1) - torch.cumsum(target, -1)).abs().sum(-1)


def descend_to_floor(p0: np.ndarray, target: np.ndarray, floor: float, *,
                     granularity: str, lr: float, max_steps: int) -> dict:
    """Спуск до пола; ``granularity`` -- "mean" или "per_molecule".

    "mean": шаг делается по среднему, и спуск прекращается, когда СРЕДНЕЕ достигло пола --
    ровно то, что делает relu(mean - floor) в лоссе и что мерил G4.
    "per_molecule": молекула ЗАМОРАЖИВАЕТСЯ, как только её собственный EMD достиг пола;
    остальные продолжают. Реализуется маской на градиент, а не остановкой цикла.
    """
    area = p0.sum(-1, keepdims=True)
    s0 = p0 / np.clip(area, 1e-30, None)
    z = torch.tensor(np.log(np.clip(s0, 1e-12, None)), dtype=torch.float32, requires_grad=True)
    t = torch.tensor(_norm(target), dtype=torch.float32)
    s0_t = torch.tensor(s0, dtype=torch.float32)

    # ОБЪЕКТИВ ОДИН И ТОТ ЖЕ В ОБОИХ ПЛЕЧАХ: сумма по молекулам, ДЕЛЁННАЯ НА ПОЛНОЕ ИХ
    # число. Тогда градиент на молекулу не зависит от того, сколько других ещё активно, и
    # единственное различие плеч -- маска. Первая версия нормировала шаг по .mean(), а
    # спускалась по .sum(): эффективный шаг был в N=126 раз больше задуманного, спуск
    # разошёлся (смещение 1.71 при доступной дистанции 0.39, AAD 11.8 против стартовых 1.33),
    # и третье плечо дало числа, тождественные первому -- признак поломки, а не результат.
    n_mol = len(s0)
    z0 = z.detach().clone().requires_grad_(True)
    (per_mol_emd(torch.softmax(z0, -1), t).sum() / n_mol).backward()
    opt = torch.optim.SGD([z], lr=lr / max(float(z0.grad.norm()), 1e-12))
    # Доступная дистанция до мишени -- масштаб, против которого ловится расходимость.
    d_to_target = float((s0_t - t).abs().sum(-1).mean())

    steps_used, frozen_at = 0, np.full(len(s0), -1)
    for step in range(1, max_steps + 1):
        with torch.no_grad():
            e = per_mol_emd(torch.softmax(z, -1), t)
        if granularity == "mean":
            if float(e.mean()) <= floor:
                break
            active = torch.ones_like(e, dtype=torch.bool)
        else:
            active = e > floor
            newly = (~active.numpy()) & (frozen_at < 0)
            frozen_at[newly] = step
            if not bool(active.any()):
                break
        opt.zero_grad()
        # Маска на ВКЛАД: замороженная молекула не получает градиента вовсе. Делитель --
        # ПОЛНОЕ число молекул, а не число активных, иначе масштаб шага на молекулу менялся
        # бы по ходу заморозки и плечи различались бы ещё и этим.
        ((per_mol_emd(torch.softmax(z, -1), t) * active.float()).sum() / n_mol).backward()
        opt.step()
        steps_used = step
        if step % 200 == 0:
            with torch.no_grad():
                moved_now = float((torch.softmax(z, -1) - s0_t).abs().sum(-1).mean())
            if moved_now > 2.0 * d_to_target:
                raise RuntimeError(
                    f"спуск разошёлся на шаге {step}: смещение {moved_now:.3f} превысило "
                    f"удвоенную дистанцию до мишени {d_to_target:.3f}. Уменьшите --lr; "
                    "возвращать такие числа нельзя, их читают как результат")

    with torch.no_grad():
        shape = torch.softmax(z, -1)
        e = per_mol_emd(shape, t)
        moved = float((shape - s0_t).abs().sum(-1).mean())
    return {"profile": shape.numpy() * area, "steps": steps_used,
            "emd_mean": float(e.mean()), "emd_max": float(e.max()),
            "frac_below_floor": float((e.numpy() <= floor + 1e-6).mean()),
            "l1_moved_mean": moved,
            "n_frozen": int((frozen_at > 0).sum()) if granularity != "mean" else 0}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--floor", type=float, default=0.40)
    ap.add_argument("--lr", type=float, default=0.5)
    ap.add_argument("--max-steps", type=int, default=12000)
    ap.add_argument("--records", type=Path,
                    default=ROOT / "results/published_idac_check/scored_records.csv")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    a = ap.parse_args()

    ref_table = load_sigma_profiles(str(PROFILES), n_bins=51)
    template = pd.read_csv(TEST, low_memory=False)
    in_test = {canonicalize(str(x)) for c in ("solute_smiles", "solvent_smiles")
               for x in template[c].dropna().unique()}
    pool = [s for s in ref_table if isinstance(s, str) and s in in_test]
    ref = np.vstack([ref_table[s][0] for s in pool])
    records = pd.read_csv(a.records) if a.records.exists() else None
    print(f"пул {len(pool)} молекул, пол {a.floor}")

    rows = []
    for seed in a.seeds:
        ck = CKPT_DIR / f"grounded_a_seed{seed}.pt"
        if not ck.exists():
            print(f"нет чекпойнта {ck}")
            continue
        model, ckd, cfg = build_model(ck)
        p_sol, p_slv = learned_profiles(model, cfg, pool, template)

        base = {"seed": seed, "arm": "исходный выученный"}
        if records is not None:
            base.update(score_closure(p_sol, p_slv, pool, records))
        base["h_solute"] = float(np.mean([hellinger(p_sol[i], ref[i])
                                          for i in range(len(pool))]))
        rows.append(base)
        print(f"  сид {seed} исходный: AAD {base.get('aad'):.4f}, H {base['h_solute']:.4f}")

        got = {}
        for gran in ("mean", "per_molecule"):
            r_sol = descend_to_floor(p_sol, ref, a.floor, granularity=gran,
                                     lr=a.lr, max_steps=a.max_steps)
            r_slv = descend_to_floor(p_slv, ref, a.floor, granularity=gran,
                                     lr=a.lr, max_steps=a.max_steps)
            got[gran] = (r_sol, r_slv)
            row = {"seed": seed, "arm": gran, "steps": r_sol["steps"],
                   "emd_mean": r_sol["emd_mean"], "emd_max": r_sol["emd_max"],
                   "frac_below_floor": r_sol["frac_below_floor"],
                   "l1_moved_mean": r_sol["l1_moved_mean"], "n_frozen": r_sol["n_frozen"],
                   "h_solute": float(np.mean([hellinger(r_sol["profile"][i], ref[i])
                                              for i in range(len(pool))]))}
            if records is not None:
                row.update(score_closure(r_sol["profile"], r_slv["profile"], pool, records))
            rows.append(row)
            print(f"  {gran:<13} шагов {r_sol['steps']:>5}, EMD среднее "
                  f"{r_sol['emd_mean']:.4f} макс {r_sol['emd_max']:.4f}, "
                  f"смещение {r_sol['l1_moved_mean']:.4f}, AAD {row.get('aad'):.4f}")

        # ТРЕТЬЕ ПЛЕЧО: пулёвый спуск, обрезанный на числе шагов, которое потратил
        # помолекулярный. Отличает "на молекулу лучше" от "просто меньше смещения".
        n_steps_pm = got["per_molecule"][0]["steps"]
        r_sol = descend_to_floor(p_sol, ref, -1.0, granularity="mean",
                                 lr=a.lr, max_steps=n_steps_pm)
        r_slv = descend_to_floor(p_slv, ref, -1.0, granularity="mean",
                                 lr=a.lr, max_steps=n_steps_pm)
        row = {"seed": seed, "arm": "пулёвый, равные шаги", "steps": r_sol["steps"],
               "emd_mean": r_sol["emd_mean"], "emd_max": r_sol["emd_max"],
               "l1_moved_mean": r_sol["l1_moved_mean"],
               "h_solute": float(np.mean([hellinger(r_sol["profile"][i], ref[i])
                                          for i in range(len(pool))]))}
        if records is not None:
            row.update(score_closure(r_sol["profile"], r_slv["profile"], pool, records))
        rows.append(row)
        print(f"  {'пулёвый, равные шаги':<13} шагов {r_sol['steps']:>5}, "
              f"смещение {r_sol['l1_moved_mean']:.4f}, AAD {row.get('aad'):.4f}")

    a.out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(a.out / "per_arm.csv", index=False)
    (a.out / "summary.json").write_text(json.dumps(
        {"floor": a.floor, "lr": a.lr, "max_steps": a.max_steps, "seeds": a.seeds,
         "n_pool": len(pool), "rows": rows}, ensure_ascii=False, indent=2))

    if "aad" in df.columns:
        print(f"\n{'плечо':<24}{'AAD':>10}{'sd':>9}{'смещение':>11}{'шагов':>8}")
        for arm in ("исходный выученный", "mean", "per_molecule", "пулёвый, равные шаги"):
            sub = df[df.arm.eq(arm)]
            if sub.empty:
                continue
            print(f"{arm:<24}{sub.aad.mean():>10.4f}{sub.aad.std(ddof=1):>9.4f}"
                  f"{sub.get('l1_moved_mean', pd.Series([np.nan])).mean():>11.4f}"
                  f"{sub.get('steps', pd.Series([np.nan])).mean():>8.0f}")
        piv = df[df.arm.isin(("mean", "per_molecule"))].pivot_table(
            index="seed", columns="arm", values="aad")
        if {"mean", "per_molecule"} <= set(piv.columns):
            d = piv["mean"] - piv["per_molecule"]
            print(f"\nПАРНО по сидам, mean минус per_molecule: среднее {d.mean():+.4f}, "
                  f"sd {d.std(ddof=1):.4f}, в пользу per_molecule {int((d > 0).sum())}/{len(d)}")
    print(f"\n-> {a.out / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
