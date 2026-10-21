#!/usr/bin/env python
"""Применить предзаявленное правило к развёртке по границе ядра.

Написан ДО того, как числа прогона получены. Правило и все пороги -- в
`results/sigma_core_boundary_sweep/PRE_DECLARATION.md`, здесь продублированы константами.

ОСОБЕННОСТЬ ЭТОГО ЧИТАТЕЛЯ: он требует ДВУХ вещей одновременно -- агрегатной ступеньки И
порастворительной знаковой доли выше 60%. Второе добавлено потому, что в депозитном контрасте
среднее показывало 2.57x, а знак -- 54.0% при 350 парах, то есть эффект был хвостовым.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

OUT = Path("results/sigma_core_boundary_sweep")
#: Объявлены до чисел.
STEP_MIN = 0.15             # Δ должна превысить половину наблюдённого контраста 0.2927
RHO_SMOOTH = 0.8            # «плавный рост»: Спирмен по всем шести
RHO_WITHIN_OUTSIDE = 0.5    # внутри группы ВНЕ: тренда быть не должно для ступеньки
RHO_IMMATERIAL = 0.5
SIGN_MIN = 0.60             # порастворительная знаковая доля
MIN_SEEDS = 4
BOOT_SEED, BOOT_DRAWS = 20261021, 4000


def eq_penalty(per_row: pd.DataFrame, arm: str) -> dict[int, float]:
    """Штраф плеча против control при РАВНОМ весе растворителям, по сидам."""
    out = {}
    for sd, g in per_row.groupby("seed"):
        a = g[g.arm == arm].groupby("solvent_smiles").abs_err.mean()
        c = g[g.arm == "control"].groupby("solvent_smiles").abs_err.mean()
        k = a.index.intersection(c.index)
        out[int(sd)] = float((a[k] - c[k]).mean())
    return out


def per_solvent_penalty(per_row: pd.DataFrame, arm: str) -> pd.Series:
    a = per_row[per_row.arm == arm].groupby(["seed", "solvent_smiles"]).abs_err.mean()
    c = per_row[per_row.arm == "control"].groupby(["seed", "solvent_smiles"]).abs_err.mean()
    k = a.index.intersection(c.index)
    return (a[k] - c[k])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=OUT)
    a = ap.parse_args()
    per_row = pd.read_csv(a.dir / "per_row.csv")
    geom = pd.read_csv(a.dir / "geometry.csv")
    meta = json.loads((a.dir / "run_meta.json").read_text())

    # ЗАМОК (поправка 1 предзаявки): годен растворитель, взявший цель во ВСЕХ окнах и на ВСЕХ сидах.
    # Применяется ДО ворот, и ворота пересчитываются здесь, а не берутся из run_meta прогона.
    lock_file = a.dir / "locked_solvents.csv"
    if lock_file.exists():
        locked = set(pd.read_csv(lock_file).solvent_smiles.astype(str))
        n_before = geom.smiles.nunique()
        geom = geom[geom.smiles.astype(str).isin(locked)]
        per_row = per_row[per_row.solvent_smiles.astype(str).isin(locked)]
        meta = dict(meta)
        meta["locked_solvents"] = len(locked)
        meta["excluded_solvents"] = n_before - len(locked)
        tol = meta.get("tv_tolerance", 0.5)
        meta["tv_gate_passed"] = bool(
            geom.groupby("window_k0").tv_achieved.apply(lambda x: x.max() - x.min()).max() <= tol)
        meta["dst_bins_constant"] = bool(geom.n_dst_bins.nunique() == 1)
        print(f"ЗАМОК применён: {len(locked)} растворителей, исключено "
              f"{meta['excluded_solvents']}; ворота пересчитаны на запертом наборе")

    inside = sorted(geom[geom.inside_core].window_k0.unique().tolist())
    outside = sorted(geom[~geom.inside_core].window_k0.unique().tolist())
    ladder = inside + outside
    res: dict = {"inside_windows": inside, "outside_windows": outside,
                 "thresholds_predeclared": {
                     "step_min": STEP_MIN, "rho_smooth": RHO_SMOOTH,
                     "rho_within_outside": RHO_WITHIN_OUTSIDE,
                     "rho_immaterial": RHO_IMMATERIAL, "sign_min": SIGN_MIN,
                     "min_seeds": MIN_SEEDS},
                 "run_meta": meta}

    # --- ВОРОТА, объявленные обязательными ---
    tv_spread = float(geom.tv_achieved.max() - geom.tv_achieved.min())
    gates = {
        "tv_gate_passed": bool(meta.get("tv_gate_passed")),
        "tv_spread": tv_spread,
        "dst_bins_constant": bool(meta.get("dst_bins_constant")),
        "identity_null_is_zero": bool(abs(meta.get("identity_null", 1.0)) < 1e-6),
        "reachability_all_windows": {int(k): float(v) for k, v in
                                     geom.groupby("window_k0").reached.mean().items()},
    }
    gates["all_windows_reachable"] = bool(min(gates["reachability_all_windows"].values()) >= 0.9)
    res["gates"] = gates
    if not (gates["tv_gate_passed"] and gates["dst_bins_constant"]
            and gates["identity_null_is_zero"] and gates["all_windows_reachable"]):
        res["verdict"] = "ЧТЕНИЕ ОТМЕНЕНО: ворота не пройдены"
        (a.dir / "reading.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
        print(json.dumps(res["gates"], indent=2, ensure_ascii=False))
        print("\nВЕРДИКТ:", res["verdict"])
        return 3

    # --- величины ---
    D = {k0: eq_penalty(per_row, f"win_k{k0}") for k0 in ladder}
    res["D_eq"] = {str(k0): {"seed_mean": float(np.mean(list(v.values()))), "per_seed": v}
                   for k0, v in D.items()}
    means = [float(np.mean(list(D[k0].values()))) for k0 in ladder]
    res["H_floating_median"] = {int(k): float(v) for k, v in
                                geom.groupby("window_k0").hellinger_floating.median().items()}

    # Δ = ВНЕ минус ВНУТРИ, по сидам
    seeds = sorted(D[ladder[0]])
    delta = {sd: float(np.mean([D[k][sd] for k in outside]) - np.mean([D[k][sd] for k in inside]))
             for sd in seeds}
    res["delta_per_seed"] = delta
    res["delta_seed_mean"] = float(np.mean(list(delta.values())))
    res["delta_sign_seeds"] = int(sum(1 for v in delta.values() if v > 0))

    rho_all, p_all = spearmanr(ladder, means)
    out_means = [float(np.mean(list(D[k0].values()))) for k0 in outside]
    rho_out, p_out = spearmanr(outside, out_means)
    res["monotonicity"] = {"spearman_all_six": float(rho_all), "p_all": float(p_all),
                           "spearman_within_outside": float(rho_out), "p_within": float(p_out)}

    # порастворительная знаковая доля: ВНЕ против ВНУТРИ, парно по растворителю
    sign = {}
    for sd in seeds:
        ins = np.mean([per_solvent_penalty(per_row, f"win_k{k}").xs(sd, level=0) for k in inside],
                      axis=0)
        ous = np.mean([per_solvent_penalty(per_row, f"win_k{k}").xs(sd, level=0) for k in outside],
                      axis=0)
        d = np.asarray(ous) - np.asarray(ins)
        sign[int(sd)] = {"fraction_outside_dearer": float((d > 0).mean()),
                         "median_diff": float(np.median(d)),
                         "iqr": [float(np.percentile(d, 25)), float(np.percentile(d, 75))],
                         "n_solvents": int(len(d))}
    res["per_solvent_sign"] = sign
    res["seeds_sign_above_threshold"] = int(sum(1 for v in sign.values()
                                                if v["fraction_outside_dearer"] > SIGN_MIN))

    # кластерный бутстрэп на Δ
    rng = np.random.default_rng(BOOT_SEED)
    solvents = np.array(sorted(per_row.solvent_smiles.unique()))
    by = {s: g for s, g in per_row.groupby("solvent_smiles")}
    draws = np.empty(BOOT_DRAWS)
    for i in range(BOOT_DRAWS):
        pick = rng.choice(solvents, size=len(solvents), replace=True)
        sub = pd.concat([by[s] for s in pick])
        Db = {k0: eq_penalty(sub, f"win_k{k0}") for k0 in ladder}
        dd = [np.mean([Db[k][sd] for k in outside]) - np.mean([Db[k][sd] for k in inside])
              for sd in seeds]
        draws[i] = float(np.mean(dd))
    res["delta_ci95"] = [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]
    res["delta_excludes_zero"] = bool(res["delta_ci95"][0] > 0 or res["delta_ci95"][1] < 0)

    # --- ПРАВИЛО ---
    cond_step = {
        "delta_at_least_min": bool(res["delta_seed_mean"] >= STEP_MIN),
        "sign_holds_in_4_of_5_seeds": bool(res["delta_sign_seeds"] >= MIN_SEEDS),
        "no_trend_within_outside": bool(abs(rho_out) < RHO_WITHIN_OUTSIDE),
        "per_solvent_sign_above_60pct_in_4_seeds":
            bool(res["seeds_sign_above_threshold"] >= MIN_SEEDS),
    }
    cond_smooth = {
        "spearman_all_six_at_least_0.8": bool(rho_all >= RHO_SMOOTH),
        "spearman_within_outside_positive": bool(rho_out >= RHO_WITHIN_OUTSIDE),
    }
    cond_immaterial = {
        "abs_delta_below_min": bool(abs(res["delta_seed_mean"]) < STEP_MIN),
        "abs_spearman_below_0.5": bool(abs(rho_all) < RHO_IMMATERIAL),
    }
    res["conditions"] = {"step": cond_step, "smooth": cond_smooth, "immaterial": cond_immaterial}
    if all(cond_step.values()):
        res["verdict"] = "СТУПЕНЬКА НА sigma_hb: цену определяет пересечение порога замыкания"
    elif all(cond_smooth.values()):
        res["verdict"] = ("ПЛАВНЫЙ РОСТ С РАССТОЯНИЕМ: дело в расстоянии, а НЕ в пороге замыкания; "
                          "гипотеза про sigma_hb не поддержана")
    elif all(cond_immaterial.values()):
        res["verdict"] = "РАСПОЛОЖЕНИЕ НЕСУЩЕСТВЕННО при согласованной массе"
    else:
        res["verdict"] = "НЕРАЗРЕШЕНО: докладывать односторонней границей, не точкой"

    (a.dir / "reading.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))

    print("ВОРОТА: ПВ разброс %.3f, бины постоянны %s, нулевое плечо %.1e, достижимость min %.0f%%"
          % (tv_spread, gates["dst_bins_constant"], meta["identity_null"],
             100 * min(gates["reachability_all_windows"].values())))
    print(f"\n{'окно':>7}{'внутри':>8}{'D_eq':>9}{'H (отпущен)':>13}   посидово")
    for k0 in ladder:
        v = D[k0]
        print(f"{k0:>7}{str(k0 in inside):>8}{np.mean(list(v.values())):>9.4f}"
              f"{res['H_floating_median'][k0]:>13.4f}   "
              + " ".join(f"{x:+.3f}" for x in v.values()))
    print(f"\nΔ = ВНЕ − ВНУТРИ: {res['delta_seed_mean']:+.4f}  "
          f"CI95 {res['delta_ci95']}  знак на {res['delta_sign_seeds']}/5 сидах")
    print(f"Спирмен по всем шести = {rho_all:+.3f}  внутри группы ВНЕ = {rho_out:+.3f}")
    print("\nпорастворительная знаковая доля «вне дороже внутри»:")
    for sd, v in sign.items():
        print(f"  сид {sd}: {100*v['fraction_outside_dearer']:>5.1f}%  медиана {v['median_diff']:+.3f}"
              f"  IQR [{v['iqr'][0]:+.3f}, {v['iqr'][1]:+.3f}]  n={v['n_solvents']}")
    print(f"сидов со знаковой долей > {100*SIGN_MIN:.0f}%: {res['seeds_sign_above_threshold']}/5")
    print(f"\nВЕРДИКТ: {res['verdict']}")
    for nm, c in res["conditions"].items():
        bad = [k for k, v in c.items() if not v]
        if bad:
            print(f"  ветвь «{nm}» не прошла: {bad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
