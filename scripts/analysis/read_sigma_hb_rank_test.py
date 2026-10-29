#!/usr/bin/env python3
"""Точный ранговый тест правила sigma_hb: нормированное положение окна внутри своего арма.

Правило, пол и мощность: ``results/sigma_hb_rank_rule/PRE_DECLARATION.md``. Этот скрипт его
применяет и НЕ меняет.

ДВА ЧТЕНИЯ, и оба печатаются, потому что ворота предзаявки на сиде 43 ПРОВАЛИЛИСЬ:

  (A) ЗАМОК ПРЕДЗАЯВКИ (63 растворителя опорного арма), сид 43 ОТМЕНЁН воротами ПВ.
      Переобученных сидов 2, точное p = 1/21 при полном разделении.
  (B) ПЕРЕСЕЧЕНИЕ по ВСЕМ армам сравнения. Это ОТСТУПЛЕНИЕ от ворот 3 предзаявки, и оно
      объявлено отступлением, а не исправлением: замок опорного опыта определён как
      растворители, взявшие цель во всех окнах и на всех сидах, так что расширение сравнения
      новыми армами расширяет и пересечение -- но набор, на котором посчитаны опорные p, при
      этом меняется, и пол вместе с ним.

Если два чтения совпадают по вердикту, вывод устойчив к выбору. Если расходятся -- это и есть
находка, и так будет сказано.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/read_sigma_hb_rank_test.py
"""
from __future__ import annotations

import json
import sys
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "results/sigma_core_boundary_sweep"
CL = ROOT / "results/sigma_hb_rank_rule/cluster"
TREATED = {42: CL / "seed42_resweep", 43: CL / "seed43/sweep", 44: CL / "seed44/sweep"}
OUT = ROOT / "results/sigma_hb_rank_rule/reading.json"
INSIDE, OUTSIDE, DECISIVE = ("1", "5"), ("13", "17", "21"), "9"
TV_TOL = 0.5


def eq_penalty(per_row: pd.DataFrame, arm: str) -> dict[int, float]:
    """Побайтовая копия линейки опорного читателя: равный вес растворителям, по сидам."""
    out = {}
    for sd, g in per_row.groupby("seed"):
        a = g[g.arm == arm].groupby("solvent_smiles").abs_err.mean()
        c = g[g.arm == "control"].groupby("solvent_smiles").abs_err.mean()
        k = a.index.intersection(c.index)
        out[int(sd)] = float((a[k] - c[k]).mean())
    return out


def d_eq(dirpath: Path, lock: set[str]) -> dict[int, dict[str, float]]:
    pr = pd.read_csv(dirpath / "per_row.csv")
    pr = pr[pr.solvent_smiles.astype(str).isin(lock)]
    per_window: dict[str, dict[int, float]] = {}
    for w in (*INSIDE, DECISIVE, *OUTSIDE):
        per_window[w] = eq_penalty(pr, f"win_k{w}")
    seeds = sorted(per_window[DECISIVE])
    return {s: {w: per_window[w][s] for w in per_window} for s in seeds}


def position(g: dict[str, float]) -> float:
    inm = np.mean([g[w] for w in INSIDE])
    outm = np.mean([g[w] for w in OUTSIDE])
    return (g[DECISIVE] - inm) / (outm - inm)


def tv_spread(dirpath: Path, lock: set[str]) -> float:
    g = pd.read_csv(dirpath / "geometry.csv")
    g = g[g.smiles.astype(str).isin(lock)]
    return float(g.groupby("window_k0").tv_achieved.apply(lambda x: x.max() - x.min()).max())


def reach_ok(dirpath: Path, lock: set[str]) -> bool:
    g = pd.read_csv(dirpath / "geometry.csv")
    g = g[g.smiles.astype(str).isin(lock)]
    return bool(g.reached.astype(bool).all())


def intersection_lock(base: set[str]) -> set[str]:
    keep = set(base)
    for p in (REF, *TREATED.values()):
        g = pd.read_csv(p / "geometry.csv")
        g = g[g.smiles.astype(str).isin(base)]
        bad = set(g[~g.reached.astype(bool)].smiles.astype(str))
        keep -= bad
    return keep


def rank_test(ref_p: list[float], tre_p: list[float]) -> dict:
    n, m = len(ref_p), len(tre_p)
    all_below = max(tre_p) < min(ref_p)
    all_above = min(tre_p) > max(ref_p)
    p_exact = 1.0 / comb(n + m, m)
    return {"n_reference": n, "m_treated": m,
            "treated_all_below_reference": bool(all_below),
            "treated_all_above_reference": bool(all_above),
            "p_exact_if_fully_separated": p_exact,
            "separated": bool(all_below or all_above)}


def read(label: str, lock: set[str], treated_seeds: list[int], note: str) -> dict:
    print("=" * 78)
    print(f"ЧТЕНИЕ {label}:  замок {len(lock)} растворителей, переобученных сидов {len(treated_seeds)}")
    print(f"  {note}")
    print("=" * 78)
    ref = d_eq(REF, lock)
    ref_p = {s: position(g) for s, g in ref.items()}
    print(f"  ОПОРНЫЙ арм (sigma_hb = 0.0084), ворота ПВ {tv_spread(REF, lock):.4f}, "
          f"достижимость {'ok' if reach_ok(REF, lock) else 'ПРОВАЛ'}")
    for s in sorted(ref_p):
        print(f"     сид {s}: p = {ref_p[s]:.4f}")
    arr = np.array([ref_p[s] for s in sorted(ref_p)])
    print(f"     среднее {arr.mean():.4f}  sd {arr.std(ddof=1):.4f}")

    tre_p = {}
    print("\n  ПЕРЕОБУЧЕННЫЕ (sigma_hb = 0.012)")
    for s in treated_seeds:
        g = d_eq(TREATED[s], lock)[s]
        tre_p[s] = position(g)
        print(f"     сид {s}: p = {tre_p[s]:.4f}   ворота ПВ {tv_spread(TREATED[s], lock):.4f}"
              f"   достижимость {'ok' if reach_ok(TREATED[s], lock) else 'ПРОВАЛ'}")

    rt = rank_test([ref_p[s] for s in sorted(ref_p)], [tre_p[s] for s in treated_seeds])
    print(f"\n  РАНГОВЫЙ ТЕСТ: n={rt['n_reference']}, m={rt['m_treated']}")
    print(f"     все переобученные НИЖЕ всех опорных: {rt['treated_all_below_reference']}")
    print(f"     все переобученные ВЫШЕ всех опорных: {rt['treated_all_above_reference']}")
    print(f"     точное p при полном разделении: 1/{comb(rt['n_reference']+rt['m_treated'], rt['m_treated'])}"
          f" = {rt['p_exact_if_fully_separated']:.4f}")
    if rt["separated"]:
        p = rt["p_exact_if_fully_separated"]
        if p <= 0.05 and rt["treated_all_below_reference"]:
            v = "ЗАМЫКАНИЕ ЗАДАЁТ ГРАНИЦУ"
        elif p <= 0.05 and rt["treated_all_above_reference"]:
            v = "ОТВЕРГНУТО В ДРУГУЮ СТОРОНУ"
        else:
            v = "МАССА ЗАДАЁТ ГРАНИЦУ (разделение есть, но p > 0.05)"
    else:
        v = "МАССА ЗАДАЁТ ГРАНИЦУ (обменимость не отвергнута)"
    print(f"     ВЕРДИКТ: {v}")
    return {"lock_size": len(lock), "reference_p": {str(k): v_ for k, v_ in ref_p.items()},
            "treated_p": {str(k): v_ for k, v_ in tre_p.items()}, **rt, "verdict": v}


def main() -> int:
    base = set(pd.read_csv(REF / "locked_solvents.csv").solvent_smiles.astype(str))
    res = {"lock_predeclared_size": len(base)}

    # ворота предзаявки, по арму
    print("=" * 78)
    print("ВОРОТА ПРЕДЗАЯВКИ на замке опорного арма")
    print("=" * 78)
    cancelled = []
    for s, p in TREATED.items():
        spread, ok = tv_spread(p, base), reach_ok(p, base)
        passed = spread <= TV_TOL and ok
        print(f"  сид {s}: разброс ПВ {spread:.4f} (порог {TV_TOL}), достижимость "
              f"{'ok' if ok else 'ПРОВАЛ'}  ->  {'пройдено' if passed else 'ПРОВАЛЕНО, сид отменяется'}")
        if not passed:
            cancelled.append(s)
    res["cancelled_on_predeclared_lock"] = cancelled
    kept = [s for s in sorted(TREATED) if s not in cancelled]

    print()
    res["reading_A"] = read("A", base, kept,
                            f"замок предзаявки; отменены сиды {cancelled or 'нет'}")
    print()
    inter = intersection_lock(base)
    dropped = sorted(base - inter)
    print(f"  ПЕРЕСЕЧЕНИЕ по всем армам убирает {len(dropped)}: {dropped}")
    res["intersection_dropped"] = dropped
    res["reading_B"] = read("B", inter, sorted(TREATED),
                            "ОТСТУПЛЕНИЕ от ворот 3: пересечение по всем армам сравнения")

    print("\n" + "=" * 78)
    agree = res["reading_A"]["verdict"] == res["reading_B"]["verdict"]
    print(f"ДВА ЧТЕНИЯ {'СОВПАЛИ' if agree else 'РАСХОДЯТСЯ'}")
    print(f"  A: {res['reading_A']['verdict']}")
    print(f"  B: {res['reading_B']['verdict']}")
    if agree:
        print("  Вывод устойчив к выбору замка.")
    else:
        print("  Это и есть находка: вывод зависит от выбора замка, и ни одно чтение не банкуется.")
    res["readings_agree"] = bool(agree)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"\nзаписано: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
