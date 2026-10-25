#!/usr/bin/env python
"""Знаковая доля и IQR для каждого опубликованного утверждения о РАСПОЛОЖЕНИИ.

ЗАЧЕМ. Утверждения о расположении публикуются как СРЕДНИЕ: «шестикратный разброс», «2.57x»,
«Δ = +0.3593». Но 2026-10-21 выяснилось, что у решающего контраста депозита среднее даёт 2.57x, а на
уровне РАСТВОРИТЕЛЯ знак сходится лишь в **54.0%** из 350 пар при IQR, широко накрывающем ноль. То
есть эффект есть в среднем и почти отсутствует у типичного растворителя -- и по одному среднему этого
не видно.

Референт, который посчитает знаковую долю сам, найдёт её за семь минут. Поэтому она должна стоять в
тексте РЯДОМ со средним, у каждого утверждения, в одних и тех же единицах. Этот скрипт и даёт такую
таблицу.

Единица лечения -- РАСТВОРИТЕЛЬ: так объявлено во всех депозитах (инъекция подменяет профиль
растворителя, строки одного растворителя делят всё возмущение). Пары берутся по (сид, растворитель).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tgnn_solv.data.utils import canonicalize  # noqa: E402

#: Депонированные σ-профили: ТОЛЬКО эти растворители подставляются.
PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"


def substituted_solvents() -> set[str]:
    """Растворители с депонированным профилем -- остальные НЕ возмущаются вовсе.

    ЗАЧЕМ ЭТО ОТДЕЛЬНО. `per_row.csv` содержит все 70 растворителей тестовых строк, но профиль есть
    у 64. У остальных шести обе руки дают ОДИН И ТОТ ЖЕ прогноз, разность РОВНО нуль, и эти нули
    разбавляют знаковую долю к 50%: измерено 32 нулевых пары из 350 (9.1%), и ограничение
    подставляемыми двигает решающую долю с 54.0% на 59.1%. Это третий случай одного дефекта
    поверхности в проекте, поэтому критерий взят универсальный -- наличие профиля, -- а не
    `geometry.csv`, которого у части депозитов нет.
    """
    tab = pd.read_csv(PROFILES)
    col = next((c for c in tab.columns if "smiles" in c.lower()), tab.columns[0])
    out = {canonicalize(str(x)) for x in tab[col].dropna().unique()}
    out.discard(None)
    return out

#: Утверждения: (депозит, плечо, база, подпись, опубликованное значение).
#: База None означает `control`.
CLAIMS = [
    ("sigma_displacement_geometry", "core_to_corner", "core_to_core",
     "угол минус ядро при согласованном H (РЕШАЮЩИЙ)", 1.0712),
    ("sigma_displacement_geometry", "core_to_corner", "control",
     "ядро -> угол против контроля", 1.2876),
    ("sigma_displacement_geometry", "core_to_core", "control",
     "ядро -> ядро против контроля", 0.2165),
    ("sigma_displacement_geometry", "oracle_solvent", "random_oracle_size",
     "оракул минус случайное того же размера", -0.2357),
    ("sigma_role_injection", "roleswap_solvent", "control",
     "ролевая подмена против контроля (29.1% от +0.4081)", 0.1187),
    # 0.0270, а НЕ 0.0459: последнее -- значение ОДНОГО розыгрыша, снятое самим депозитом
    # (`RESULTS.md`, «Пересчёт с пятью розыгрышами»). Ворота поймали именно эту подстановку.
    ("sigma_role_injection", "roleswap_solvent", "random_matched_solvent",
     "роль минус случайное при согласованном H (r - m)", 0.0270),
]


def paired(per_row: pd.DataFrame, arm: str, base: str) -> pd.Series:
    """Парные разности по (сид, растворитель). Единица лечения -- растворитель.

    Это РАВНОВЕСНАЯ величина: сперва среднее внутри растворителя, потом по растворителям. Знаковая
    доля существует только в этом виде -- у построчного среднего порастворительного знака нет.
    """
    a = per_row[per_row.arm == arm].groupby(["seed", "solvent_smiles"]).abs_err.mean()
    b = per_row[per_row.arm == base].groupby(["seed", "solvent_smiles"]).abs_err.mean()
    k = a.index.intersection(b.index)
    d = (a[k] - b[k]).dropna()
    sub = substituted_solvents()
    keep = [idx for idx in d.index if canonicalize(str(idx[1])) in sub]
    return d.loc[keep]


def row_weighted(per_row: pd.DataFrame, arm: str, base: str) -> float:
    """ПОСТРОЧНОЕ среднее по сидам -- в этом виде опубликованы значения депозитов.

    Нужно отдельно: ворота воспроизведения обязаны сверяться с тем весом, в котором число
    напечатано, иначе расхождение весов читается как дефект чтения. Я на это и наступил.
    """
    vals = []
    for sd, g in per_row.groupby("seed"):
        x, y = g[g.arm == arm], g[g.arm == base]
        if len(x) and len(y):
            vals.append(float(x.abs_err.mean() - y.abs_err.mean()))
    return float(np.mean(vals)) if vals else float("nan")


def describe(d: pd.Series) -> dict:
    per_seed = {}
    for sd, g in d.groupby(level=0):
        per_seed[int(sd)] = {"fraction_positive": float((g > 0).mean()),
                             "median": float(g.median()), "n": int(len(g))}
    return {
        "n_pairs": int(len(d)),
        "n_solvents": int(d.index.get_level_values(1).nunique()),
        "n_seeds": int(d.index.get_level_values(0).nunique()),
        "mean": float(d.mean()),
        "median": float(d.median()),
        "iqr": [float(d.quantile(0.25)), float(d.quantile(0.75))],
        "iqr_straddles_zero": bool(d.quantile(0.25) < 0 < d.quantile(0.75)),
        "fraction_positive": float((d > 0).mean()),
        "per_seed": per_seed,
        "seeds_above_60pct": int(sum(1 for v in per_seed.values()
                                     if v["fraction_positive"] > 0.60)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "results/location_sign_fractions")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    cache: dict[str, pd.DataFrame] = {}
    rows: list[dict] = []
    out: dict[str, dict] = {}
    for dep, arm, base, label, published in CLAIMS:
        p = ROOT / "results" / dep / "per_row.csv"
        if not p.exists():
            print(f"  ПРОПУСК {dep}/{arm}: построчного файла нет ({p.name})")
            continue
        if dep not in cache:
            cache[dep] = pd.read_csv(p)
        pr = cache[dep]
        if arm not in set(pr.arm) or base not in set(pr.arm):
            print(f"  ПРОПУСК {dep}: нет плеча {arm if arm not in set(pr.arm) else base}")
            continue
        d = paired(pr, arm, base)
        st = describe(d)
        rw = row_weighted(pr, arm, base)
        st.update({"deposit": dep, "arm": arm, "base": base, "label": label,
                   "published_mean_row_weighted": published,
                   "mean_row_weighted": rw, "mean_equal_weight": st["mean"]})
        # ВОРОТА сверяются с ПОСТРОЧНЫМ, потому что в этом весе число опубликовано.
        st["reproduces_published"] = bool(abs(rw - published) < 0.01)
        st["weighting_ratio_equal_over_row"] = (st["mean"] / rw) if rw else None
        out[f"{dep}:{arm}-{base}"] = st
        rows.append(st)

    (a.out / "summary.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"\n{'утверждение':<46}{'построч':>9}{'опубл':>8}{'равнов':>9}"
          f"{'медиана':>9}{'IQR':>20}{'знак+':>7}{'>60%':>6}")
    for st in rows:
        iqr = f"[{st['iqr'][0]:+.3f}, {st['iqr'][1]:+.3f}]"
        flag = "" if st["reproduces_published"] else "  !ВОРОТА"
        print(f"{st['label'][:45]:<46}{st['mean_row_weighted']:>9.4f}"
              f"{st['published_mean_row_weighted']:>8.4f}{st['mean_equal_weight']:>9.4f}"
              f"{st['median']:>9.4f}{iqr:>20}{100*st['fraction_positive']:>6.1f}%"
              f"{st['seeds_above_60pct']:>4}/{st['n_seeds']}{flag}")
    print(f"\n{'утверждение':<48}  знаковая доля по сидам")
    for st in rows:
        fr = ", ".join(f"{100*v['fraction_positive']:.1f}%" for v in st["per_seed"].values())
        print(f"{st['label'][:47]:<48}  {fr}")
    n_straddle = sum(1 for st in rows if st["iqr_straddles_zero"])
    print(f"\nутверждений разобрано: {len(rows)}; у {n_straddle} IQR накрывает ноль")
    print(f"записано: {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
