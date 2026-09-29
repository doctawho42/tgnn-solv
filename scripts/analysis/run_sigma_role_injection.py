#!/usr/bin/env python
"""Отделить РОЛЬ от ЗНАЧЕНИЙ в штрафе за подстановку sigma-профиля -- без переобучения.

ВОПРОС. Опубликованный штраф +0.408 ln x2 MAE (grounded_a 1.9275 -> oracle 2.3356, n=5608,
сиды 42-46) приписан целиком РАЗНИЦЕ ЗНАЧЕНИЙ между выученным и депонированным профилем. Но
выученный профиль ЗАВИСИТ ОТ РОЛИ (энкодер несёт два role-specific адаптера,
layers.py:280-283, и head_sigma зовётся на обоих слотах, model.py:535-536), а депонированный
VT-2005 роли не имеет вовсе. Значит подстановка делает две вещи разом: меняет значения и
подставляет безролевой массив туда, где модель ждёт ролевой. Если вторая половина несёт часть
штрафа, механизм в статье приписан неверно.

ПОЧЕМУ БЕЗ ПЕРЕОБУЧЕНИЯ, И ЭТО ГЛАВНОЕ РЕШЕНИЕ ЗДЕСЬ. Очевидный эксперимент -- обучить плечо со
связанными ролями и сравнить штрафы -- НЕ ставится, и отказ обоснован тремя убийцами,
найденными состязательным разбором 2026-09-28:

  (1) КОНФАУНД ДРЕЙФА. Оракул впрыскивает ТОТ ЖЕ артефакт
      (results/sigma_profile_artifact/sigma_profiles.csv), против которого голова обучалась в
      фазе 1: notebooks/data/processed_sigma_aux_stream_clean/summary.json записывает его как
      sigma_csv. То есть штраф -- это «насколько профиль уехал от собственной мишени». Связывание
      ролей меняет геометрию дрейфа НАПРЯМУЮ (одна компромиссная ветвь вместо двух свободных под
      SLE-лоссом при замороженной голове), поэтому уменьшившийся штраф на связанном плече
      объясняется «профиль стал ближе к VT-2005» ровно так же хорошо, как «роль несла часть
      цены». Проверка манипуляции ловит только ролевой зазор и НИЧЕГО не говорит о расстоянии до
      эталона.
  (2) НЕТ МОЩНОСТИ. Подстановочный штраф по сидам: 0.2578 / 0.5243 / 0.5618 / 0.3995 / 0.2972,
      sd 0.134. Разность двух пятисидовых плеч несёт SE 0.085, значит MDE при 80% -- 0.271, то
      есть 66% всего штрафа. Гипотезу в 0.10 такой дизайн не видит; для неё нужно ~28 сидов.
  (3) КОНФАУНД БАЗЫ С ПРЕДСКАЗАННЫМ ЗНАКОМ. По пяти сидам контроля corr(базовый MAE, штраф)
      = -0.516, наклон -0.661: чекпойнт, который сидит лучше, получает БОЛЬШИЙ штраф. Сдвиг базы
      на 0.15 (внутри допуска сравнимости!) двигает штраф на -0.099 -- весь гипотетический
      эффект, без всякой роли. Связанное плечо -- ограниченная модель, и априори сядет на худшую
      сторону допуска, то есть знак конфаунда совпадает со знаком гипотезы.

ВСЕ ТРИ ВХОДЯТ ЧЕРЕЗ ПЕРЕОБУЧЕНИЕ. На ФИКСИРОВАННЫХ весах их нет: геометрия дрейфа, ёмкость и
база одни и те же во всех плечах, потому что веса одни и те же. Поэтому здесь роль отделяется от
значений подменой ВХОДА, а не обучением.

ПЛЕЧИ (все -- один и тот же чекпойнт, один и тот же набор строк, разный впрыск)

  control                 без впрыска; воспроизводит MAE плеча
  identity_solvent        собственный профиль молекулы В РОЛИ РАСТВОРИТЕЛЯ обратно в слот
                          растворителя. НУЛЕВОЕ ПЛЕЧО: по построению no-op, обязан вернуть MAE
                          контроля до |dMAE| <= 1e-6. Прогоняет весь тракт впрыска -- маски,
                          torch.where, __force_sigma_oracle__, eval-счёт сегментов. Если двинул,
                          загрязнён КАЖДЫЙ штраф, когда-либо измеренный этим каналом.
  roleswap_solvent        собственный профиль молекулы В РОЛИ РАСТВОРЯЕМОГО в слот растворителя.
                          РЕШАЮЩЕЕ ПЛЕЧО: значения остаются собственными значениями модели,
                          меняется ТОЛЬКО роль.
  random_matched_solvent  случайный профиль на ТОМ ЖЕ расстоянии Хеллингера от собственного
                          профиля-растворителя, какое у этой молекулы между её двумя ролями.
                          ВТОРОЕ НУЛЕВОЕ ПЛЕЧО, и оно про мощность: если смещение ровно ролевого
                          размера в СЛУЧАЙНОМ направлении не двигает MAE, то ноль на roleswap --
                          это «не установлено», а не «опровергнуто». CLAUDE.md требует этого
                          различения прямо.
  oracle_solvent          VT-2005 в слот растворителя
  oracle_both             VT-2005 в оба слота -- конфигурация статьи, якорь к +0.408

ОДНА МАСКА НА ВСЕ ПЛЕЧИ. Подставляются ровно те строки, где VT-2005 знает растворителя, во всех
плечах. Иначе identity не был бы контролем к roleswap, а сравнивались бы разные наборы строк.

КЛАСТЕР -- РАСТВОРИТЕЛЬ, А НЕ РАСТВОРЯЕМОЕ, И ЭТО НЕ КОСМЕТИКА. Лечение назначается на уровне
растворителя: 8058 из 8066 затронутых строк -- слот растворителя, различных растворителей 66,
вода несёт 36.2%, топ-5 несут 62.0%, эффективное n по Кишу = 6.38. Строки с одним растворителем
делят ВЕСЬ впрыск и скоррелированы в лечении полностью. run_e5_cluster_bootstrap.py ресемплит
растворяемые (2634 кластера здесь) и своей же докстрокой говорит, что «интервал оценивает розыгрыш
тестовых растворяемых»; для ЭТОГО эстиманда это не та дисперсия. Здесь кластер -- растворитель.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_sigma_role_injection.py
    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_sigma_role_injection.py --seeds 42
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

# ТОТ ЖЕ ТРАКТ, ЧТО У ОПУБЛИКОВАННОГО ОРАКУЛЬНОГО ПЛЕЧА, а не свой собственный. build_loader и
# forward_batch берутся из export_checkpoint_predictions.py -- скрипта, которым посчитан штраф
# +0.408. Если бы здесь стоял свой вызов model(...), плечо oracle_both воспроизводило бы
# опубликованное число только по совпадению, и якорь ничего бы не стоил.
from export_checkpoint_predictions import build_loader, forward_batch            # noqa: E402
from run_sigma_profile_residual import build_model, hellinger, learned_profiles  # noqa: E402
from tgnn_solv.data.utils import canonicalize                                    # noqa: E402
from tgnn_solv.sigma_oracle import build_oracle_tensors, load_sigma_profiles     # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
TEST = ROOT / "notebooks/data/processed/test.csv"
OUT = ROOT / "results/sigma_role_injection"

#: Детерминированные плечи. Случайные добавляются по --random-draws как random_matched_solvent_d{k}
#: и усредняются в синтетическое random_matched_solvent на стадии анализа.
FIXED_ARMS = ["control", "identity_solvent", "roleswap_solvent", "oracle_solvent", "oracle_both"]
RANDOM_ARM = "random_matched_solvent"


def arm_names(draws: int) -> list[str]:
    """Порядок плеч прогона: сначала детерминированные, потом розыгрыши."""
    return FIXED_ARMS[:3] + [f"{RANDOM_ARM}_d{k}" for k in range(draws)] + FIXED_ARMS[3:]


def matched_random_profile(p_own: np.ndarray, target_h: float, rng: np.random.Generator,
                           tol: float = 1e-4, iters: int = 60) -> np.ndarray:
    """Случайный профиль ровно на расстоянии target_h по Хеллингеру от p_own, той же площади.

    СМЕШИВАНИЕ, А НЕ ГЕНЕРАЦИЯ С НУЛЯ. Случайный профиль сам по себе лежит от собственного на
    каком придётся расстоянии, и подогнать его площадь мало -- нужно подогнать РАССТОЯНИЕ, иначе
    плечо перестаёт быть контролем к roleswap. Поэтому берётся смесь (1-t)*p_own + t*p_rand,
    перенормированная на площадь p_own, и t ищется делением пополам: H монотонна по t от 0 до
    H(p_own, p_rand), так что корень единственный, если target_h внутри этого отрезка.
    """
    area = float(p_own.sum())
    if area <= 0 or not np.isfinite(target_h) or target_h <= 0:
        return p_own.copy()
    p_rand = rng.dirichlet(np.ones(len(p_own))) * area
    if hellinger(p_own, p_rand) < target_h:
        return p_rand                     # дальше смесью не уедешь: возвращаем предельный случай
    lo, hi = 0.0, 1.0
    for _ in range(iters):
        t = 0.5 * (lo + hi)
        mix = (1.0 - t) * p_own + t * p_rand
        s = float(mix.sum())
        mix = mix * (area / s) if s > 0 else p_own
        h = hellinger(p_own, mix)
        if abs(h - target_h) < tol:
            return mix
        lo, hi = (t, hi) if h < target_h else (lo, t)
    return mix


def build_injection_tables(model, cfg, solvents: list[str], template: pd.DataFrame,
                           boot_seed: int, draws: int) -> tuple[dict, float]:
    """SMILES -> (p_sigma, area) для каждого небазового плеча, по собственным профилям модели.

    НЕСКОЛЬКО РОЗЫГРЫШЕЙ, И ПОРЯДОК ИХ ВЫЧЕРПЫВАНИЯ ВЫБРАН НЕ СЛУЧАЙНО. Один генератор на сид,
    внешний цикл по розыгрышу, внутренний по молекуле, ровно один вызов dirichlet на молекулу.
    Поэтому розыгрыш d0 вычерпывает ту же последовательность, что вычерпывал единственный розыгрыш
    прогона 2026-09-28, и обязан воспроизвести его число. Это не изящество, а проверка: если d0
    разойдётся со старым депозитом, значит изменился не счёт розыгрышей, а что-то ещё.
    """
    as_solute, as_solvent = learned_profiles(model, cfg, solvents, template)
    rng = np.random.default_rng(boot_seed)
    tables: dict[str, dict[str, tuple[np.ndarray, float]]] = {
        "identity_solvent": {}, "roleswap_solvent": {}}
    gaps: list[float] = []
    prof: list[tuple[str, np.ndarray, np.ndarray, float]] = []
    for i, smi in enumerate(solvents):
        key = canonicalize(smi)
        if key is None:
            continue
        p_u, p_v = np.asarray(as_solute[i], dtype=float), np.asarray(as_solvent[i], dtype=float)
        h = hellinger(p_u, p_v)
        gaps.append(h)
        tables["identity_solvent"][key] = (p_v, float(p_v.sum()))
        tables["roleswap_solvent"][key] = (p_u, float(p_u.sum()))
        prof.append((key, p_u, p_v, h))
    for k in range(draws):
        name = f"{RANDOM_ARM}_d{k}"
        tables[name] = {}
        for key, _p_u, p_v, h in prof:
            p_r = matched_random_profile(p_v, h, rng)
            tables[name][key] = (p_r, float(p_r.sum()))
    return tables, float(np.median(gaps)) if gaps else float("nan")


def score_arm(model, cfg, df: pd.DataFrame, arm: str, oracle_table, inj_tables,
              n_bins: int, batch_size: int, device: torch.device) -> pd.DataFrame:
    """Один проход по тесту с впрыском плеча `arm`; возвращает построчные ошибки."""
    loader = build_loader(df, cfg, batch_size, 0)
    rows = []
    with torch.no_grad():
        for sol_b, slv_b, targets in loader:
            force = arm != "control"
            if force:
                # МАСКА ВСЕГДА VT-2005: набор подставляемых строк один во всех плечах.
                _, _, mask = build_oracle_tensors(targets["solvent_smiles"], oracle_table,
                                                  n_bins=n_bins)
                src = oracle_table if arm.startswith("oracle") else inj_tables[arm]
                p, a, _ = build_oracle_tensors(targets["solvent_smiles"], src, n_bins=n_bins)
                targets["sigma_oracle_p_solvent"] = p
                targets["sigma_oracle_area_solvent"] = a
                targets["sigma_oracle_mask_solvent"] = mask
                if arm == "oracle_both":
                    ps, as_, ms = build_oracle_tensors(targets["solute_smiles"], oracle_table,
                                                       n_bins=n_bins)
                    targets["sigma_oracle_p_solute"] = ps
                    targets["sigma_oracle_area_solute"] = as_
                    targets["sigma_oracle_mask_solute"] = ms
                targets["__force_sigma_oracle__"] = True
            out, _ = forward_batch("tgnn", model, sol_b, slv_b, targets, device,
                                   force_sigma_oracle=force)
            pred = out["ln_x2"].detach().cpu().numpy().astype(float)
            true = targets["ln_x2"].detach().cpu().numpy().astype(float)
            has = targets["has_solubility"].detach().cpu().numpy().astype(bool)
            for j in range(len(pred)):
                if not has[j]:
                    continue
                rows.append({"row_idx": len(rows),
                             "solute_smiles": str(targets["solute_smiles"][j]),
                             "solvent_smiles": str(targets["solvent_smiles"][j]),
                             "abs_err": abs(pred[j] - true[j])})
    return pd.DataFrame(rows)


def cluster_bootstrap(per_row: pd.DataFrame, arm: str, draws: int, boot_seed: int,
                      base: str = "control") -> tuple:
    """Перцентильный бутстрап контраста arm-минус-base, КЛАСТЕР -- РАСТВОРИТЕЛЬ.

    База -- параметр, потому что решающая величина пред-декларации это r - m, контраст ДВУХ
    плеч, а не плеча с контролем. Считать его вычитанием двух краевых оценок нельзя: их
    интервалы перекрываются, а парный контраст -- нет, и наоборот.

    ПАРА БЕРЁТСЯ ПО ПОЗИЦИИ СТРОКИ, А НЕ ПО SMILES. Первая версия сводила таблицу по
    (растворяемое, растворитель, сид) -- и на дымовом прогоне напечатала штраф +0.0528 там, где
    MAE УПАЛ на 0.074. Одна и та же пара стоит в тесте при нескольких температурах, и ключ из двух
    SMILES схлопывал их в одну строку, так что вычитались разные наборы. Загрузчик детерминирован
    (shuffle=False, num_workers=0, drop_last=False), поэтому row_idx -- точный ключ.

    Разность парная ВНУТРИ чекпойнта: веса одни и те же, меняется только вход, поэтому сидовый шум
    сюда не входит. Он печатается отдельно, как разброс по сидам.
    """
    w = per_row.pivot_table(index=["seed", "row_idx"], columns="arm", values="abs_err",
                            aggfunc="first")
    w = w.dropna(subset=[base, arm])
    diff = (w[arm] - w[base]).to_numpy()
    solvents = per_row.drop_duplicates(["seed", "row_idx"]).set_index(
        ["seed", "row_idx"]).loc[w.index, "solvent_smiles"].to_numpy()
    uniq = np.unique(solvents)
    idx = {s: np.flatnonzero(solvents == s) for s in uniq}
    rng = np.random.default_rng(boot_seed)
    stats = np.empty(draws)
    for b in range(draws):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        stats[b] = float(np.concatenate([diff[idx[s]] for s in pick]).mean())
    return float(diff.mean()), float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ckpt-dir", type=Path, default=CKPT_DIR)
    ap.add_argument("--arm-glob", default="grounded_a_seed*.pt")
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--max-rows", type=int, default=None,
                    help="только для дымового прогона; на усечённом тесте числа бессмысленны")
    ap.add_argument("--random-draws", type=int, default=5,
                    help="случайных розыгрышей на сид; d0 воспроизводит прогон 2026-09-28")
    ap.add_argument("--draws", type=int, default=4000, help="розыгрышей БУТСТРАПА")
    ap.add_argument("--boot-seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    arms = arm_names(a.random_draws)
    draw_arms = [x for x in arms if x.startswith(f"{RANDOM_ARM}_d")]
    device = torch.device(a.device)
    test = pd.read_csv(TEST, low_memory=False)
    df = test[test["ln_x2"].notna()].reset_index(drop=True)
    if a.max_rows:
        df = df.head(a.max_rows).reset_index(drop=True)
        print(f"ДЫМОВОЙ ПРОГОН на {len(df)} строках -- числа не являются результатом")
    template = pd.read_csv(TEST, nrows=1, low_memory=False)

    cks = sorted(a.ckpt_dir.glob(a.arm_glob))
    if not cks:
        print(f"нет чекпойнтов в {a.ckpt_dir}/{a.arm_glob}")
        return 1

    frames = []
    role_gaps: dict[int, float] = {}
    for ck in cks:
        model, ckd, cfg = build_model(ck)
        seed = int(ckd.get("seed", -1))
        if a.seeds and seed not in a.seeds:
            continue
        model.to(device)
        n_bins = int(cfg.cosmo_sac_n_bins)
        oracle_table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
        subs = sorted({s for s in df["solvent_smiles"].astype(str)
                       if canonicalize(s) in oracle_table})
        print(f"сид {seed}: {len(subs)} подставляемых растворителей, {len(df)} размеченных строк",
              flush=True)
        inj, gap = build_injection_tables(model, cfg, subs, template, a.boot_seed + seed,
                                          a.random_draws)
        role_gaps[seed] = gap
        print(f"  медианный ролевой зазор по Хеллингеру: {gap:.3f}", flush=True)
        for arm in arms:
            r = score_arm(model, cfg, df, arm, oracle_table, inj, n_bins, a.batch_size, device)
            r["arm"], r["seed"] = arm, seed
            frames.append(r)
            print(f"  {arm:26s} MAE {r.abs_err.mean():.4f}  (n={len(r)})", flush=True)

    per_row = pd.concat(frames, ignore_index=True)

    # СИНТЕТИЧЕСКОЕ ПЛЕЧО: построчное среднее по розыгрышам. Пред-декларация определяет m как цену
    # «случайного смещения такого размера» -- это ОЖИДАНИЕ, а не конкретный розыгрыш, и усреднение
    # оценивает его лучше. Один розыгрыш прошлого прогона остаётся в депозите как d0.
    avg = (per_row[per_row.arm.isin(draw_arms)]
           .groupby(["seed", "row_idx", "solute_smiles", "solvent_smiles"], as_index=False)
           .abs_err.mean())
    avg["arm"] = RANDOM_ARM
    per_row = pd.concat([per_row, avg], ignore_index=True)

    a.out.mkdir(parents=True, exist_ok=True)
    per_row.to_csv(a.out / "per_row.csv", index=False)
    per_seed = per_row.groupby(["seed", "arm"]).abs_err.mean().unstack()
    per_seed.to_csv(a.out / "per_seed.csv")

    reported = FIXED_ARMS[:3] + [RANDOM_ARM] + FIXED_ARMS[3:]
    summary = {"arms_run": arms, "arms_reported": reported,
               "seeds": sorted(per_seed.index.tolist()),
               "n_rows_per_arm": int(per_row.groupby(["seed", "arm"]).size().median()),
               "n_solvent_clusters": int(per_row.solvent_smiles.nunique()),
               "median_role_hellinger_gap": role_gaps,
               "cluster_unit": "solvent_smiles",
               "random_draws": a.random_draws, "bootstrap_draws": a.draws,
               "boot_seed": a.boot_seed,
               "mae": {arm: {"per_seed": per_seed[arm].round(6).to_dict(),
                             "mean": float(per_seed[arm].mean()),
                             "sd": float(per_seed[arm].std(ddof=1))} for arm in per_seed.columns},
               "random_draw_spread": {
                   "per_draw_mae_mean": {d: float(per_seed[d].mean()) for d in draw_arms},
                   "sd_across_draws": float(np.std([per_seed[d].mean() for d in draw_arms],
                                                   ddof=1)) if len(draw_arms) > 1 else None},
               "penalty_vs_control": {}, "paired_contrasts": {}}

    print(f"\n{'плечо':<26}{'MAE':>9}{'штраф':>9}{'CI95 (кластер=растворитель)':>32}")
    for arm in reported[1:]:
        point, lo, hi = cluster_bootstrap(per_row, arm, a.draws, a.boot_seed)
        pen = per_seed[arm] - per_seed["control"]
        summary["penalty_vs_control"][arm] = {"point": point, "ci95": [lo, hi],
                                              "per_seed": pen.round(6).to_dict(),
                                              "seed_sd": float(pen.std(ddof=1))}
        print(f"{arm:<26}{per_seed[arm].mean():>9.4f}{point:>9.4f}"
              f"{f'[{lo:+.4f}, {hi:+.4f}]':>32}")
    print(f"{'control':<26}{per_seed['control'].mean():>9.4f}")

    # РЕШАЮЩИЙ КОНТРАСТ пред-декларации и остаток за пределами ролевого масштаба -- считаются
    # ЗДЕСЬ, а не сниппетом в оболочке: заранее объявленную величину производит производитель.
    print(f"\n{'парный контраст':<26}{'оценка':>9}{'CI95':>32}")
    for name, arm, base in [("roleswap - random (РЕШАЮЩИЙ)", "roleswap_solvent", RANDOM_ARM),
                            ("oracle_both - roleswap", "oracle_both", "roleswap_solvent")]:
        point, lo, hi = cluster_bootstrap(per_row, arm, a.draws, a.boot_seed, base=base)
        excl = (lo > 0) or (hi < 0)
        summary["paired_contrasts"][f"{arm}__minus__{base}"] = {
            "point": point, "ci95": [lo, hi], "ci_excludes_zero": bool(excl),
            "per_seed": (per_seed[arm] - per_seed[base]).round(6).to_dict()}
        print(f"{name:<26}{point:>+9.4f}{f'[{lo:+.4f}, {hi:+.4f}]':>32}"
              f"  {'исключает 0' if excl else 'СОДЕРЖИТ 0'}")

    o = summary["penalty_vs_control"]["oracle_both"]["point"]
    r = summary["penalty_vs_control"]["roleswap_solvent"]["point"]
    summary["role_share_of_published_penalty"] = float(r / o) if o else None
    print(f"\n  доля роли в опубликованном штрафе: {100 * r / o:.1f}%")

    # ВОРОТА, ОБЪЯВЛЕННЫЕ ДО ЧИСЕЛ -- см. PRE_DECLARATION.md рядом с депозитом.
    ident = abs(summary["penalty_vs_control"]["identity_solvent"]["point"])
    power = abs(summary["penalty_vs_control"][RANDOM_ARM]["point"])
    summary["gates"] = {
        "identity_is_noop": {"threshold": 1e-6, "value": ident, "passed": ident <= 1e-6},
        "instrument_has_power_at_role_scale": {"threshold": 0.05, "value": power,
                                               "passed": power >= 0.05},
    }
    print("\nВОРОТА")
    for k, g in summary["gates"].items():
        print(f"  {'ok  ' if g['passed'] else 'НЕТ '} {k:38s} {g['value']:.6f} "
              f"против порога {g['threshold']}")
    if not summary["gates"]["instrument_has_power_at_role_scale"]["passed"]:
        print("\n  МОЩНОСТИ НЕТ. Ноль на roleswap читается как «НЕ УСТАНОВЛЕНО», не «опровергнуто».")
    (a.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    print(f"\nзаписано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
