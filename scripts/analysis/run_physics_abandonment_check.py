#!/usr/bin/env python
"""Проверка пост-хок наблюдения E2: отказ плеча с флагом от своего физического пути.

ПРАВИЛА ОБЪЯВЛЕНЫ ДО ВЫЧИСЛЕНИЯ -- ``results/e2_crystal_detach/PRE_DECLARATION.md``, раздел
«Предзаявка на ПРОВЕРКУ ПОСТ-ХОК НАБЛЮДЕНИЯ». Скрипт их исполняет и ничего не добавляет.

ГЛАВНАЯ ОПАСНОСТЬ, КОТОРУЮ ЭТОТ СКРИПТ РАЗДЕЛЯЕТ. Наблюдение «модель отказывается от физики»
может быть пересказом уже забанкованной цены: если физический путь испортился, поправка ДОЛЖНА
открыться, в этом её назначение. Тривиальное чтение -- уверенность упала ТАМ, ГДЕ физика плоха;
нетривиальное -- упала неизбирательно, в том числе где физика хороша, то есть сломана калибровка
доверия, а не точность.

ЧТО УЖЕ БЫЛО ВИДЕНО ДО ЭТОГО СКРИПТА (и потому не является предметом проверки): медиана и среднее
``correction_gate`` по плечам, среднее |``ln_x2_final`` − ``ln_x2_physics``|, доля строк с
отклонением > 0.01. Это наблюдение. Предмет проверки -- величины (A), (B), (C) ниже.

НУЛЕВОЕ ПЛЕЧО ОСОБОЕ. У контроля ``correction_gate`` ровно 1.0 на ВСЕХ строках, то есть гейт
НАСЫЩЕН, а не калиброван, и калибровочной кривой для сравнения контроль не даёт. Что он даёт --
нуль для (B) и (C): у него ``e_final`` тождественно ``e_phys``, значит любая ненулевая (B) или (C)
у плеча с флагом есть свойство ВМЕШАТЕЛЬСТВА, а не измерителя. Скрипт это проверяет, а не
предполагает.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_physics_abandonment_check.py \
        --pair 42=<каталог seed_42> --pair 43=<каталог seed_43>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

BOOTSTRAP_SEED = 20261019
BOOTSTRAP_DRAWS = 4000

#: Границы объявлены в предзаявке и здесь только исполняются.
RHO_INDISCRIMINATE = 0.2      # |rho| ниже -- неизбирательный обвал
RHO_WORKING_GATE = 0.4        # |rho| выше -- работающий гейт; между -- не разрешено
CONST_SHIFT_LIMIT = 0.25      # sd / |среднее| ниже -- отход есть выученная константа

CONTROL = "grounded_a_predictions.csv"
TREATED = "grounded_a_detachcrystal_predictions.csv"


def _flag(s: pd.Series) -> pd.Series:
    if s.dtype == object:
        return s.map(lambda v: str(v).strip().lower() in ("true", "1"))
    return s.fillna(False).astype(bool)


def _locked(df: pd.DataFrame) -> pd.DataFrame:
    d = df[_flag(df["has_solubility"])].copy()
    for c in ("ln_x2_physics", "ln_x2_final", "ln_x2_true", "correction_gate"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["e_phys"] = (d["ln_x2_physics"] - d["ln_x2_true"]).abs()
    d["e_final"] = (d["ln_x2_final"] - d["ln_x2_true"]).abs()
    d["dev_signed"] = d["ln_x2_final"] - d["ln_x2_physics"]
    return d.dropna(subset=["e_phys", "e_final", "correction_gate", "dev_signed"])


def cluster_bootstrap_mean(values: pd.Series, groups: pd.Series,
                           rng: np.random.Generator) -> tuple[float, float, bool]:
    """CI95 среднего с ресэмплом по КЛАСТЕРАМ растворяемых (на этом наборе он консервативен)."""
    frames = [g.to_numpy(float) for _, g in values.groupby(groups)]
    n = len(frames)
    means = np.empty(BOOTSTRAP_DRAWS)
    for i in range(BOOTSTRAP_DRAWS):
        pick = rng.integers(0, n, size=n)
        means[i] = np.concatenate([frames[j] for j in pick]).mean()
    lo, hi = float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
    return lo, hi, bool(lo > 0 or hi < 0)


def analyse_pair(seed: str, folder: Path, rng: np.random.Generator) -> dict:
    ctrl, flag = _locked(pd.read_csv(folder / CONTROL)), _locked(pd.read_csv(folder / TREATED))

    # Нулевое плечо: у контроля отход должен быть ТОЖДЕСТВЕННО нулевым, а гейт -- насыщенным.
    null_arm = {
        "control_gate_min": float(ctrl["correction_gate"].min()),
        "control_gate_max": float(ctrl["correction_gate"].max()),
        "control_gate_sd": float(ctrl["correction_gate"].std(ddof=0)),
        "control_max_abs_dev": float(ctrl["dev_signed"].abs().max()),
        "control_mean_e_final_minus_e_phys": float((ctrl["e_final"] - ctrl["e_phys"]).mean()),
    }
    null_arm["gate_saturated"] = bool(null_arm["control_gate_sd"] < 1e-9)
    null_arm["deviation_identically_zero"] = bool(null_arm["control_max_abs_dev"] < 1e-9)

    # (A) избирательность гейта в плече с флагом
    rho = float(flag["correction_gate"].corr(flag["e_phys"], method="spearman"))
    zone = ("неизбирательный обвал" if abs(rho) < RHO_INDISCRIMINATE else
            "работающий гейт" if abs(rho) > RHO_WORKING_GATE else "НЕ РАЗРЕШЕНО")
    # обязательное условие читаемости (A): у e_phys должен быть разброс
    ep = flag["e_phys"]
    ep_spread = {"mean": float(ep.mean()), "sd": float(ep.std(ddof=0)),
                 "p10": float(ep.quantile(0.10)), "p50": float(ep.median()),
                 "p90": float(ep.quantile(0.90))}
    ep_spread["cv"] = ep_spread["sd"] / ep_spread["mean"] if ep_spread["mean"] else float("nan")
    ep_spread["readable"] = bool(ep_spread["cv"] > 0.25)

    # (B) покупает ли отход хоть что-то
    gain = flag["e_final"] - flag["e_phys"]
    lo, hi, excl = cluster_bootstrap_mean(gain, flag["solute_smiles"], rng)
    buys = {"mean_e_final_minus_e_phys": float(gain.mean()), "ci95": [lo, hi],
            "excludes_zero": excl,
            "verdict": ("отход СНИЖАЕТ ошибку" if gain.mean() < 0 else
                        "отход НЕ снижает ошибку")}

    # (C) константа или структура
    dev = flag["dev_signed"]
    ratio = float(dev.std(ddof=0) / abs(dev.mean())) if dev.mean() else float("inf")
    shape = {"mean_signed_dev": float(dev.mean()), "sd_signed_dev": float(dev.std(ddof=0)),
             "sd_over_abs_mean": ratio,
             "verdict": ("выученная КОНСТАНТА" if ratio < CONST_SHIFT_LIMIT else "структура")}

    return {"seed": seed, "n_locked_rows": int(len(flag)),
            "n_solutes": int(flag["solute_smiles"].nunique()),
            "null_arm": null_arm,
            "A_gate_selectivity": {"spearman_gate_vs_e_phys": rho, "zone": zone,
                                   "e_phys_spread": ep_spread},
            "B_does_abandonment_buy_anything": buys,
            "C_constant_or_structure": shape}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", action="append", required=True, metavar="SEED=DIR")
    ap.add_argument("--out", type=Path,
                    default=Path("results/e2_crystal_detach/physics_abandonment.json"))
    a = ap.parse_args()

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    pairs = []
    for spec in a.pair:
        seed, _, folder = spec.partition("=")
        pairs.append(analyse_pair(seed, Path(folder), rng))

    print("ПРОВЕРКА ОТКАЗА ОТ ФИЗИКИ (правила -- PRE_DECLARATION.md)\n")
    for r in pairs:
        n = r["null_arm"]
        print(f"=== сид {r['seed']}: {r['n_locked_rows']} запертых строк, "
              f"{r['n_solutes']} растворяемых ===")
        print(f"  НУЛЕВОЕ ПЛЕЧО (контроль): гейт [{n['control_gate_min']:.4f}, "
              f"{n['control_gate_max']:.4f}], sd {n['control_gate_sd']:.2e} -> "
              f"{'НАСЫЩЕН' if n['gate_saturated'] else 'варьирует'};  "
              f"max|отход| {n['control_max_abs_dev']:.2e} -> "
              f"{'тождественно нуль' if n['deviation_identically_zero'] else 'НЕ нуль'}")
        A = r["A_gate_selectivity"]
        s = A["e_phys_spread"]
        print(f"  (A) спирмен гейта с ошибкой физики: {A['spearman_gate_vs_e_phys']:+.3f}  "
              f"-> {A['zone']}")
        print(f"      разброс ошибки физики: средн {s['mean']:.3f}, sd {s['sd']:.3f}, "
              f"cv {s['cv']:.2f}, p10/p50/p90 {s['p10']:.2f}/{s['p50']:.2f}/{s['p90']:.2f}  "
              f"-> (A) {'читается' if s['readable'] else 'НЕ ЧИТАЕТСЯ: разброса нет'}")
        B = r["B_does_abandonment_buy_anything"]
        print(f"  (B) |итог−истина| − |физика−истина| = {B['mean_e_final_minus_e_phys']:+.4f}  "
              f"CI95 [{B['ci95'][0]:+.4f}, {B['ci95'][1]:+.4f}]  "
              f"исключает нуль: {'да' if B['excludes_zero'] else 'нет'}  -> {B['verdict']}")
        C = r["C_constant_or_structure"]
        print(f"  (C) знаковый отход: среднее {C['mean_signed_dev']:+.4f}, "
              f"sd {C['sd_signed_dev']:.4f}, sd/|среднее| {C['sd_over_abs_mean']:.2f}  "
              f"-> {C['verdict']}")
        print()

    agree = {}
    for key, pick in (("A", lambda r: r["A_gate_selectivity"]["zone"]),
                      ("B", lambda r: r["B_does_abandonment_buy_anything"]["verdict"]),
                      ("C", lambda r: r["C_constant_or_structure"]["verdict"])):
        zones = {pick(r) for r in pairs}
        agree[key] = {"zones": sorted(zones), "agrees": len(zones) == 1}
        print(f"  {key}: {'СОГЛАСНО в обеих парах' if len(zones) == 1 else 'РАСХОДИТСЯ'} "
              f"-> {sorted(zones)}")

    nulls_ok = all(r["null_arm"]["gate_saturated"] and r["null_arm"]["deviation_identically_zero"]
                   for r in pairs)
    print(f"\nнулевое плечо ведёт себя как объявлено в обеих парах: {nulls_ok}")
    print("ЧЕГО ПРОВЕРКА НЕ ГОВОРИТ: почему гейт двухсоставен -- насыщение на 1.0 у контроля значит, "
          "что его калибровка на этих данных никогда не проверялась; различить это могло бы плечо "
          "с промежуточной силой вмешательства, которого нет.")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(
        {"pairs": pairs, "agreement": agree, "null_arm_behaves_as_declared": nulls_ok,
         "thresholds": {"rho_indiscriminate": RHO_INDISCRIMINATE,
                        "rho_working_gate": RHO_WORKING_GATE,
                        "const_shift_limit": CONST_SHIFT_LIMIT},
         "bootstrap": {"seed": BOOTSTRAP_SEED, "draws": BOOTSTRAP_DRAWS,
                       "note": "кластерный по растворяемым запертого набора; часть вторая "
                               "измерила его консервативность на этом наборе"},
         "rules": "results/e2_crystal_detach/PRE_DECLARATION.md, раздел о пост-хок наблюдении"},
        indent=2, ensure_ascii=False) + "\n")
    print(f"\nзаписано {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
