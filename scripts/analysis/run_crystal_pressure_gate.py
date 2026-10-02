#!/usr/bin/env python
"""Ворота E2: кто на самом деле двигает T_m -- внешняя метка или растворимость.

ЗАЧЕМ. План outreach/ПЛАН_физичная_модель.md предлагает закрепить кристаллическую ветвь снаружи и
не давать лоссу растворимости её двигать. Перед этим надо проверить, двигает ли он её вообще: если
кристаллические параметры и так стоят там, куда их поставила супервизия, замораживать нечего.

ПОЧЕМУ НЕ ПРЯМЫМ ИЗМЕРЕНИЕМ ДРЕЙФА. Задуманные ворота мерили бы, насколько T_m уехал за фазы 2-3 от
значения после фазы 1. Промежуточных чекпойнтов в дереве НЕТ, только финальные, поэтому дрейф
измерить нечем. Вместо него меряется ДАВЛЕНИЕ: какой градиент на T_m создаёт каждый из двух лоссов
в конечном состоянии, с весами своей фазы.

КАК СЧИТАЕТСЯ. Phi = (dH/R)(1/T - 1/T_m) при dCp = 0 (проверено: dCp_fus_solver тождественно нуль
на этих плечах), поэтому d(ln x2)/d(T_m) = -(dH/R)/T_m^2 построчно. Лосс растворимости -- Huber с
delta = 1.0 (loss.py:159), а MAE этих плеч около 1.93, то есть |ошибка| >> delta почти везде и
производная отсечена: |dL/d ln x2| = 1/N на строку. Кристаллическая супервизия -- masked MSE на
сыром выходе головы, scale 50 K (loss.py:155), значит dL/dT_m = 2(pred - target)/50^2. Веса фазы 2:
растворимость 1.0, кристалл 0.05 (trainer.py:70).

ЗНАКОВАЯ ВЕРСИЯ ОБЯЗАТЕЛЬНА. Каждое растворяемое встречается во многих строках, и если их градиенты
смотрят в разные стороны, сумма гасится. Поэтому считается И сумма модулей, И модуль суммы, и
печатается их отношение -- доля давления, пережившая сложение. Без этого число завышено.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_crystal_pressure_gate.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT / "results/e5_sigma_grounding_leakfree"
OUT = ROOT / "results/crystal_pressure_gate"

R_GAS = 8.31446261815324
S_TM = 50.0          # loss.py:155
W_SOL, W_TM = 1.0, 0.05   # trainer.py:70, фаза 2


def _flag(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.lower().isin({"true", "1", "1.0", "yes"})
            | (pd.to_numeric(s, errors="coerce").fillna(0) > 0))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", type=Path, default=TREE)
    ap.add_argument("--arm", default="grounded_a_predictions.csv")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    rows = []
    for f in sorted(a.tree.glob(f"seed_*/{a.arm}")):
        d = pd.read_csv(f)
        seed = f.parent.name
        sol = d[_flag(d["has_solubility"])].copy()
        tm = d[_flag(d["has_T_m"])]
        if sol.empty or tm.empty:
            continue
        n_sol, n_tm = len(sol), len(tm)
        assert np.allclose(d["dCp_fus_solver"], 0.0), "dCp не нуль -- формула Phi другая"
        sol["g"] = (np.sign(sol["ln_x2_pred"] - sol["ln_x2_true"])
                    * (sol["dH_fus_solver"] / R_GAS / sol["T_m_solver"] ** 2))
        signed = sol.groupby("solute_smiles")["g"].apply(lambda x: W_SOL * abs(x.sum()) / n_sol)
        absol = sol.groupby("solute_smiles")["g"].apply(lambda x: W_SOL * x.abs().sum() / n_sol)
        cry = tm.groupby("solute_smiles").apply(
            lambda x: W_TM * abs((2 * (x["T_m_solver"] - x["T_m"]) / S_TM ** 2).sum()) / n_tm,
            include_groups=False)
        j = pd.concat([signed.rename("signed"), absol.rename("abs"), cry.rename("cry")],
                      axis=1).dropna()
        rows.append({
            "seed": seed, "n_solutes": int(len(j)),
            "rows_per_solute": float(n_sol / sol["solute_smiles"].nunique()),
            "signed_over_crystal": float((j["signed"] / j["cry"]).median()),
            "abs_over_crystal": float((j["abs"] / j["cry"]).median()),
            "sign_survival": float((j["signed"] / j["abs"]).median()),
            "frac_sle_dominates": float((j["signed"] > j["cry"]).mean()),
        })

    if not rows:
        print(f"нет предсказаний в {a.tree}")
        return 1
    t = pd.DataFrame(rows)
    print("ДАВЛЕНИЕ НА T_m: растворимость против кристаллической супервизии (веса фазы 2)\n")
    print(t.to_string(index=False, float_format=lambda x: f"{x:.3g}"))
    med = float(t["signed_over_crystal"].median())
    surv = float(t["sign_survival"].median())
    print(f"\nВОРОТА E2: знаковое отношение {med:.2f}x  "
          f"{'ok -- есть что замораживать' if med > 1.5 else 'НЕТ -- кристалл и так стоит на метке'}")
    print(f"  доля давления, пережившая сложение по строкам: {surv:.2f}")
    print("  (близко к единице -- ошибки по строкам одного растворяемого ОДНОСТОРОННИ,")
    print("   давление не гасится, а копится; это и объясняет измеренный сдвиг T_m)")

    a.out.mkdir(parents=True, exist_ok=True)
    t.to_csv(a.out / "per_seed.csv", index=False)
    (a.out / "summary.json").write_text(json.dumps(
        {"phase_weights": {"sol": W_SOL, "T_m": W_TM}, "S_Tm": S_TM,
         "huber_delta_note": "|ошибка| >> delta=1, производная отсечена, |dL/dlnx2| = 1/N",
         "per_seed": rows, "signed_over_crystal_median": med,
         "sign_survival_median": surv}, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"\nзаписано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
