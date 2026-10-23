#!/usr/bin/env python
"""Держится ли ступенька с ВКЛЮЧЁННОЙ водой. Правило -- из предзаявки, записанной до чисел.

`results/sigma_core_boundary_water/PRE_DECLARATION.md`. Читается ОДИН прогон (цель по ПВ 10.0) на
ДВУХ наборах растворителей -- все и те же без воды, -- поэтому разница между чтениями не может быть
эффектом величины возмущения: величина одна.

Правило БЕЗМАСШТАБНОЕ (отношение групп, а не разность), потому что цель вдвое меньше опорной и
абсолютный порог 0.15 дал бы ложное «ступеньки нет».
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

#: Объявлены до чисел.
RATIO_MIN = 3.0          # половина наименьшего наблюдённого отношения (6x при цели 20.82)
SIGN_MIN = 0.60
MIN_SEEDS = 4
TV_TOL = 0.5
WATER = "O"


def eq_penalty(per_row: pd.DataFrame, arm: str) -> dict[int, float]:
    out = {}
    for sd, g in per_row.groupby("seed"):
        a = g[g.arm == arm].groupby("solvent_smiles").abs_err.mean()
        c = g[g.arm == "control"].groupby("solvent_smiles").abs_err.mean()
        k = a.index.intersection(c.index)
        out[int(sd)] = float((a[k] - c[k]).mean())
    return out


def per_solvent(per_row: pd.DataFrame, arm: str) -> pd.Series:
    a = per_row[per_row.arm == arm].groupby(["seed", "solvent_smiles"]).abs_err.mean()
    c = per_row[per_row.arm == "control"].groupby(["seed", "solvent_smiles"]).abs_err.mean()
    k = a.index.intersection(c.index)
    return a[k] - c[k]


def read_one(per_row: pd.DataFrame, inside: list[int], outside: list[int], tag: str) -> dict:
    D = {k: eq_penalty(per_row, f"win_k{k}") for k in inside + outside}
    seeds = sorted(D[inside[0]])
    ins_mean = float(np.mean([np.mean(list(D[k].values())) for k in inside]))
    out_mean = float(np.mean([np.mean(list(D[k].values())) for k in outside]))
    ratio = out_mean / ins_mean if ins_mean > 0 else float("inf")
    delta = {sd: float(np.mean([D[k][sd] for k in outside]) - np.mean([D[k][sd] for k in inside]))
             for sd in seeds}
    sign = {}
    for sd in seeds:
        i = np.mean([per_solvent(per_row, f"win_k{k}").xs(sd, level=0) for k in inside], axis=0)
        o = np.mean([per_solvent(per_row, f"win_k{k}").xs(sd, level=0) for k in outside], axis=0)
        d = np.asarray(o) - np.asarray(i)
        sign[int(sd)] = {"fraction": float((d > 0).mean()), "median": float(np.median(d)),
                         "iqr": [float(np.percentile(d, 25)), float(np.percentile(d, 75))],
                         "n_solvents": int(len(d))}
    cond = {
        "ratio_at_least_3": bool(ratio >= RATIO_MIN),
        "delta_sign_in_4_of_5_seeds": bool(sum(1 for v in delta.values() if v > 0) >= MIN_SEEDS),
        "per_solvent_sign_above_60pct_in_4_seeds":
            bool(sum(1 for v in sign.values() if v["fraction"] > SIGN_MIN) >= MIN_SEEDS),
    }
    if all(cond.values()):
        verdict = "СТУПЕНЬКА ДЕРЖИТСЯ"
    elif not cond["ratio_at_least_3"] or not cond["delta_sign_in_4_of_5_seeds"]:
        verdict = "НЕ ДЕРЖИТСЯ"
    else:
        verdict = "НЕОПРЕДЕЛЁННО: есть в среднем, нет у типичного растворителя"
    return {"tag": tag, "n_solvents": int(per_row.solvent_smiles.nunique()),
            "D_eq": {str(k): {"seed_mean": float(np.mean(list(v.values()))), "per_seed": v}
                     for k, v in D.items()},
            "inside_mean": ins_mean, "outside_mean": out_mean, "ratio": ratio,
            "delta_per_seed": delta, "delta_seed_mean": float(np.mean(list(delta.values()))),
            "per_solvent_sign": sign, "conditions": cond, "verdict": verdict}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, required=True, help="каталог прогона при цели ПВ 10.0")
    ap.add_argument("--out", type=Path, default=Path("results/sigma_core_boundary_water"))
    a = ap.parse_args()
    per_row = pd.read_csv(a.dir / "per_row.csv")
    geom = pd.read_csv(a.dir / "geometry.csv")
    meta = json.loads((a.dir / "run_meta.json").read_text())

    inside = sorted(geom[geom.inside_core].window_k0.unique().tolist())
    outside = sorted(geom[~geom.inside_core].window_k0.unique().tolist())

    # ТОЛЬКО ПОДСТАВЛЯЕМЫЕ. `per_row` содержит все растворители тестовых строк (их 70), но
    # депонированный профиль есть лишь у части (64): остальные НЕ возмущаются вовсе, их разности
    # нулевые по построению, и они разбавляют знаковую долю к 50%. Опыт ступеньки читался на 63
    # подставляемых, поэтому без этого ограничения числа несравнимы.
    substituted = set(geom.smiles.astype(str))
    n_before = per_row.solvent_smiles.nunique()
    per_row = per_row[per_row.solvent_smiles.astype(str).isin(substituted)]
    print(f"ограничено подставляемыми: {per_row.solvent_smiles.nunique()} из {n_before} "
          f"растворителей тестовых строк")

    spread = geom.groupby("window_k0").tv_achieved.apply(lambda x: x.max() - x.min())
    gates = {
        "target_tv": meta.get("target_tv"),
        "tv_spread_max": float(spread.max()),
        "tv_gate_passed": bool(spread.max() <= TV_TOL),
        "dst_bins_constant": bool(geom.n_dst_bins.nunique() == 1),
        "identity_null": meta.get("identity_null"),
        "identity_null_is_zero": bool(abs(meta.get("identity_null", 1.0)) < 1e-6),
        "reachability_min": float(geom.groupby("window_k0").reached.mean().min()),
        "water_present": bool((per_row.solvent_smiles.astype(str) == WATER).any()),
        "H_floating_median": {int(k): float(v) for k, v in
                              geom.groupby("window_k0").hellinger_floating.median().items()},
    }
    res: dict = {"gates": gates, "thresholds_predeclared":
                 {"ratio_min": RATIO_MIN, "sign_min": SIGN_MIN, "min_seeds": MIN_SEEDS},
                 "inside_windows": inside, "outside_windows": outside}
    if not (gates["tv_gate_passed"] and gates["dst_bins_constant"]
            and gates["identity_null_is_zero"] and gates["reachability_min"] >= 0.9):
        res["verdict"] = "ЧТЕНИЕ ОТМЕНЕНО: ворота не пройдены"
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 3
    if not gates["water_present"]:
        res["verdict"] = "ЧТЕНИЕ ОТМЕНЕНО: воды в прогоне НЕТ, а опыт именно про неё"
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 3

    all64 = read_one(per_row, inside, outside, "все растворители (вода включена)")
    no_water = read_one(per_row[per_row.solvent_smiles.astype(str) != WATER],
                        inside, outside, "те же без воды")
    res["with_water"], res["without_water"] = all64, no_water
    res["water_changes_the_verdict"] = bool(all64["verdict"] != no_water["verdict"])
    res["water_question"] = ("ВЫВОД ЧУВСТВИТЕЛЕН К ВОДЕ" if res["water_changes_the_verdict"]
                             else "ВОДА НЕ МЕНЯЕТ ВЫВОД")

    # вода как ОДИН растворитель -- печатается, в правило не входит (один кластер)
    w = per_row[per_row.solvent_smiles.astype(str) == WATER]
    if len(w):
        wc = w[w.arm == "control"].abs_err.mean()
        res["water_alone_not_in_rule"] = {
            f"win_k{k}": float(w[w.arm == f'win_k{k}'].abs_err.mean() - wc)
            for k in inside + outside}

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "reading.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))

    print(f"ВОРОТА: цель ПВ {gates['target_tv']}, разброс {gates['tv_spread_max']:.4f}, "
          f"бины постоянны {gates['dst_bins_constant']}, нуль {gates['identity_null']:+.1e}, "
          f"достижимость {100*gates['reachability_min']:.0f}%, вода в наборе: {gates['water_present']}")
    for blk in (all64, no_water):
        print(f"\n--- {blk['tag']}, растворителей {blk['n_solvents']} ---")
        print(f"{'окно':>6}{'внутри':>8}{'D_eq':>9}")
        for k in inside + outside:
            print(f"{k:>6}{str(k in inside):>8}{blk['D_eq'][str(k)]['seed_mean']:>9.4f}")
        print(f"  ВНУТРИ {blk['inside_mean']:.4f}  ВНЕ {blk['outside_mean']:.4f}  "
              f"ОТНОШЕНИЕ {blk['ratio']:.2f}x  (порог {RATIO_MIN})")
        print(f"  Δ {blk['delta_seed_mean']:+.4f}, знак на "
              f"{sum(1 for v in blk['delta_per_seed'].values() if v>0)}/5 сидах")
        print("  знаковая доля: " + ", ".join(
            f"{sd}:{100*v['fraction']:.1f}%" for sd, v in blk["per_solvent_sign"].items()))
        print(f"  ВЕРДИКТ: {blk['verdict']}")
        bad = [k for k, v in blk["conditions"].items() if not v]
        if bad:
            print(f"    не выполнены: {bad}")
    print(f"\n=== ВОПРОС ПРО ВОДУ: {res['water_question']} ===")
    if "water_alone_not_in_rule" in res:
        print("  вода как один растворитель (в правило НЕ входит):")
        for k, v in res["water_alone_not_in_rule"].items():
            print(f"    {k}: {v:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
