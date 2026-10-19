#!/usr/bin/env python
"""Разрез E2 по давлению растворимости: сосредоточено ли улучшение T_m там, где толкало сильнее.

ПРАВИЛА ОБЪЯВЛЕНЫ ДО ВЫЧИСЛЕНИЯ -- ``results/e2_crystal_detach/PRE_DECLARATION.md``, раздел
«Предзаявка на РАЗРЕЗ ПО ДАВЛЕНИЮ». Этот скрипт их исполняет и ничего к ним не добавляет.
Исполнять, а не помнить, здесь обязательно: на двух парах заявленная ось E2 сменила знак, и по
ОДНОЙ паре забанковался бы любой из двух взаимоисключающих выводов.

ЧТО СЧИТАЕТСЯ. Для каждого из 31 растворяемого с ИЗМЕРЕННЫМ ``T_m``:
``Delta_s = T_m_solver(флаг) - T_m_solver(контроль)``, знаковая -- в точности редукция
родительской оси. |смещение| докладывается отдельно, потому что при смене знака у отдельного
растворяемого две величины разойдутся; это капкан «редукция против порога», который дымовой тест
читателя пары уже один раз поймал.

ДАВЛЕНИЕ -- С КОНТРОЛЬНОГО ПЛЕЧА. У плеча с флагом путь растворимости к параметрам кристалла
отрезан по построению, поэтому мерить там давление бессмысленно. Формула и константы
переиспользуются из ``run_crystal_pressure_gate.py``, а не переписываются: расхождение двух копий
одной формулы -- отдельный способ получить неверное число.

ЧЕГО СКРИПТ НЕ ДЕЛАЕТ. Не цитирует внутрипарный кластерный бутстрэп как значимость: часть вторая
поправки измерила на этой оси антиконсервативность примерно втрое, а деление 31 кластера пополам
делает хуже. Бутстрэп печатается как ШИРИНА. Значимость даёт только нулевое плечо -- 2000
случайных разбиений 15/16 -- и только при согласии ОБЕИХ пар.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_pressure_stratified_e2.py \
        --pair 42=<каталог seed_42> --pair 43=<каталог seed_43>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

#: Константы -- те же, что в run_crystal_pressure_gate.py (loss.py:155, trainer.py:70, фаза 2).
#: Продублированы с явной ссылкой, а не импортированы, потому что тот скрипт -- CLI без
#: импортируемого ядра; расхождение ловится тестом test_pressure_strat_constants_match_the_gate.
R_GAS = 8.31446261815324
S_TM = 50.0
W_SOL, W_TM = 1.0, 0.05

BOOTSTRAP_SEED = 20261019
NULL_DRAWS = 2000
PROXY_RHO_LIMIT = 0.7

CONTROL = "grounded_a_predictions.csv"
TREATED = "grounded_a_detachcrystal_predictions.csv"


def _flag(s: pd.Series) -> pd.Series:
    if s.dtype == object:
        return s.map(lambda v: str(v).strip().lower() in ("true", "1"))
    return s.fillna(False).astype(bool)


def pressure_ratio(control: pd.DataFrame) -> pd.DataFrame:
    """Отношение давления растворимости к давлению супервизии, ПО РАСТВОРЯЕМОМУ, с контроля."""
    assert np.allclose(pd.to_numeric(control["dCp_fus_solver"], errors="coerce").fillna(0.0), 0.0), \
        "dCp не нуль -- формула Phi другая, и производная по T_m тоже"
    sol = control[_flag(control["has_solubility"])].copy()
    tm = control[_flag(control["has_T_m"])].copy()
    n_sol, n_tm = len(sol), len(tm)
    sol["g"] = (np.sign(sol["ln_x2_pred"] - sol["ln_x2_true"])
                * (sol["dH_fus_solver"] / R_GAS / sol["T_m_solver"] ** 2))
    signed = sol.groupby("solute_smiles")["g"].apply(lambda x: W_SOL * abs(x.sum()) / n_sol)
    cry = tm.groupby("solute_smiles").apply(
        lambda x: W_TM * abs((2 * (x["T_m_solver"] - x["T_m"]) / S_TM ** 2).sum()) / n_tm,
        include_groups=False)
    rows = sol.groupby("solute_smiles").size().rename("rows")
    tm_meas = tm.groupby("solute_smiles")["T_m"].mean().rename("T_m_meas")
    dh_meas = tm.groupby("solute_smiles")["dH_fus"].mean().rename("dH_meas")
    j = pd.concat([signed.rename("signed"), cry.rename("cry"), rows, tm_meas, dh_meas],
                  axis=1).dropna(subset=["signed", "cry"])
    j["ratio"] = j["signed"] / j["cry"]
    return j


def per_solute_shift(control: pd.DataFrame, treated: pd.DataFrame) -> pd.DataFrame:
    """Delta_s по растворяемому на страте ИЗМЕРЕННОГО T_m, знаковая и по модулю."""
    out = {}
    for name, df in (("ctrl", control), ("flag", treated)):
        s = df[_flag(df["has_solubility"]) & _flag(df["has_T_m"])]
        g = s.groupby("solute_smiles").agg(pred=("T_m_solver", "mean"), meas=("T_m", "mean"))
        out[name] = g
    common = out["ctrl"].index.intersection(out["flag"].index)
    d = pd.DataFrame(index=common)
    d["bias_ctrl"] = out["ctrl"].loc[common, "pred"] - out["ctrl"].loc[common, "meas"]
    d["bias_flag"] = out["flag"].loc[common, "pred"] - out["flag"].loc[common, "meas"]
    d["delta_signed"] = d["bias_flag"] - d["bias_ctrl"]
    d["delta_abs"] = d["bias_flag"].abs() - d["bias_ctrl"].abs()
    return d


def stratum_difference(delta: np.ndarray, high: np.ndarray) -> float:
    return float(delta[high].mean() - delta[~high].mean())


def null_distribution(delta: np.ndarray, n_high: int, rng: np.random.Generator) -> np.ndarray:
    """2000 СЛУЧАЙНЫХ разбиений того же размера -- иначе «сосредоточено» не проверено ни на чём."""
    out = np.empty(NULL_DRAWS)
    n = len(delta)
    for i in range(NULL_DRAWS):
        idx = rng.permutation(n)
        mask = np.zeros(n, dtype=bool)
        mask[idx[:n_high]] = True
        out[i] = stratum_difference(delta, mask)
    return out


def analyse_pair(seed: str, folder: Path, rng: np.random.Generator) -> dict:
    control = pd.read_csv(folder / CONTROL)
    treated = pd.read_csv(folder / TREATED)
    pres = pressure_ratio(control)
    shift = per_solute_shift(control, treated)
    common = pres.index.intersection(shift.index)
    pres, shift = pres.loc[common], shift.loc[common]

    cut = float(pres["ratio"].median())
    high = (pres["ratio"] > cut).to_numpy()
    delta = shift["delta_signed"].to_numpy(float)
    D = stratum_difference(delta, high)
    null = null_distribution(delta, int(high.sum()), rng)
    p95 = float(np.percentile(np.abs(null), 95))

    # Бутстрэп -- ТОЛЬКО как ширина. См. докстринг и часть вторую поправки.
    idx = rng.integers(0, len(delta), size=(4000, len(delta)))
    boot = np.array([stratum_difference(delta[row], high[row]) for row in idx])
    width = float(np.percentile(boot, 97.5) - np.percentile(boot, 2.5))

    rho = {k: float(pres["ratio"].corr(pres[k], method="spearman"))
           for k in ("rows", "T_m_meas", "dH_meas")}
    proxies = {k: v for k, v in rho.items() if abs(v) > PROXY_RHO_LIMIT}

    return {
        "seed": seed, "n_solutes": int(len(delta)),
        "n_high": int(high.sum()), "n_low": int((~high).sum()),
        "pressure_median_cut": cut,
        "mean_delta_high": float(delta[high].mean()),
        "mean_delta_low": float(delta[~high].mean()),
        "D": D, "null_p95_abs": p95, "exceeds_null": bool(abs(D) > p95),
        "bootstrap_ci_width_not_significance": width,
        "spearman_ratio_vs": rho, "proxy_violations": proxies,
        "mean_delta_abs_high": float(shift["delta_abs"].to_numpy(float)[high].mean()),
        "mean_delta_abs_low": float(shift["delta_abs"].to_numpy(float)[~high].mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", action="append", required=True, metavar="SEED=DIR",
                    help="сид и каталог с предсказаниями обоих плеч; нужны ОБЕ пары")
    ap.add_argument("--out", type=Path,
                    default=Path("results/e2_crystal_detach/pressure_stratified.json"))
    a = ap.parse_args()

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    pairs = []
    for spec in a.pair:
        seed, _, folder = spec.partition("=")
        pairs.append(analyse_pair(seed, Path(folder), rng))

    print("РАЗРЕЗ E2 ПО ДАВЛЕНИЮ РАСТВОРИМОСТИ (правила -- PRE_DECLARATION.md)\n")
    for r in pairs:
        print(f"=== сид {r['seed']}: {r['n_solutes']} растворяемых, "
              f"{r['n_high']} высокое / {r['n_low']} низкое давление ===")
        print(f"  Delta_s среднее: высокое {r['mean_delta_high']:+8.2f} K   "
              f"низкое {r['mean_delta_low']:+8.2f} K")
        print(f"  D = {r['D']:+.2f} K   нулевое плечо |D| p95 = {r['null_p95_abs']:.2f} K   "
              f"-> {'ПРЕВЫШАЕТ нуль' if r['exceeds_null'] else 'внутри нуля'}")
        print(f"  бутстрэп: ширина CI95 {r['bootstrap_ci_width_not_significance']:.2f} K "
              f"(ШИРИНА, не значимость -- на этой оси он антиконсервативен)")
        print(f"  по модулю: высокое {r['mean_delta_abs_high']:+8.2f} K   "
              f"низкое {r['mean_delta_abs_low']:+8.2f} K")
        print("  спирмен отношения с: " + ", ".join(
            f"{k}={v:+.2f}" for k, v in r["spearman_ratio_vs"].items()))
        if r["proxy_violations"]:
            print(f"  !! ПОДМЕНА: |rho| > {PROXY_RHO_LIMIT} с {list(r['proxy_violations'])} -- "
                  f"разрез идёт ПО ЭТОЙ переменной, а не по давлению")
        print()

    signs = {np.sign(r["D"]) for r in pairs}
    agree = len(signs) == 1
    both_exceed = all(r["exceeds_null"] for r in pairs)
    any_proxy = any(r["proxy_violations"] for r in pairs)
    verdict = (
        "ПОДМЕНА: отношение давления оказалось прокси -- докладывать как разрез по той переменной"
        if any_proxy else
        "СОСРЕДОТОЧЕНО: знак D совпал в обеих парах и |D| превысил нуль в обеих"
        if agree and both_exceed else
        "НЕ СОСРЕДОТОЧЕНО: знак совпал, но нуль не превышен в обеих парах -- направления нет"
        if agree else
        "НЕ БАНКУЕТСЯ: знак D РАСХОДИТСЯ между парами -- как и с delta_phi_mean")
    print(f"ВЕРДИКТ ПО ОБЪЯВЛЕННОМУ ПРАВИЛУ: {verdict}")
    print("\nЧЕГО ЭТОТ РАЗРЕЗ НЕ ГОВОРИТ: он не отделяет компенсацию от «голова лучше садится там, "
          "где метка информативнее», если давление коррелирует с информативностью; и при 31 "
          "кластере пополам он не даёт ВЕЛИЧИНЫ -- только направление.")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(
        {"pairs": pairs, "sign_agrees": agree, "both_exceed_null": both_exceed,
         "any_proxy_violation": any_proxy, "verdict": verdict,
         "null": {"draws": NULL_DRAWS, "seed": BOOTSTRAP_SEED},
         "rules": "results/e2_crystal_detach/PRE_DECLARATION.md, раздел о разрезе по давлению"},
        indent=2, ensure_ascii=False) + "\n")
    print(f"\nзаписано {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
