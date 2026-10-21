"""Применить предзаявленное правило к развёртке по границе угла.

Написан ДО того, как числа развёртки были получены. Правило и пороги — в
`results/sigma_corner_threshold_sweep/PRE_DECLARATION.md` и продублированы здесь константами.

Ядро и control берутся из ДЕПОЗИТА: маска ядра задана `cosmo_sac_sigma_hb`, от границы угла не
зависит, и пересчёт дал бы тот же ответ за те же минуты.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

DEPOSIT = Path("results/sigma_displacement_geometry")
OUT = Path("results/sigma_corner_threshold_sweep")
ANCHOR = 0.016
#: Объявлены до чисел.
RHO_CONFIRM, RHO_ARBITRARY = 0.8, 0.5
LOW_POINT_FRACTION = 0.5
MIN_SEEDS_MONOTONE = 4
MIN_REACHED = 0.9
BOOT_SEED, BOOT_DRAWS = 20261021, 4000


def eq_weight(corner: pd.DataFrame, base: pd.DataFrame) -> dict[int, float]:
    """Контраст при РАВНОМ весе растворителям, по сидам."""
    out = {}
    for sd in sorted(set(corner.seed) & set(base.seed)):
        a = corner[corner.seed == sd].groupby("solvent_smiles").abs_err.mean()
        b = base[base.seed == sd].groupby("solvent_smiles").abs_err.mean()
        k = a.index.intersection(b.index)
        out[int(sd)] = float((a[k] - b[k]).mean())
    return out


def row_weight(corner: pd.DataFrame, base: pd.DataFrame) -> dict[int, float]:
    return {int(sd): float(corner[corner.seed == sd].abs_err.mean()
                           - base[base.seed == sd].abs_err.mean())
            for sd in sorted(set(corner.seed) & set(base.seed))}


def boot_eq(corner: pd.DataFrame, base: pd.DataFrame) -> tuple[float, float]:
    """Кластерный бутстрэп по растворителю на седовом среднем равновесного контраста."""
    rng = np.random.default_rng(BOOT_SEED)
    solvents = np.array(sorted(set(corner.solvent_smiles) & set(base.solvent_smiles)))
    ca = {s: g for s, g in corner.groupby("solvent_smiles")}
    cb = {s: g for s, g in base.groupby("solvent_smiles")}
    draws = np.empty(BOOT_DRAWS)
    for i in range(BOOT_DRAWS):
        pick = rng.choice(solvents, size=len(solvents), replace=True)
        vals = eq_weight(pd.concat([ca[s] for s in pick]), pd.concat([cb[s] for s in pick]))
        draws[i] = float(np.mean(list(vals.values())))
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-dir", type=Path, required=True,
                    help="каталог с подкаталогами th0.010/ th0.012/ ...")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    dep = pd.read_csv(DEPOSIT / "per_row.csv")
    base = dep[dep.arm == "core_to_core"]
    anchor_corner = dep[dep.arm == "core_to_corner"]

    # собрать все пороги: депонированный + прогнанные
    per_th: dict[float, pd.DataFrame] = {ANCHOR: anchor_corner}
    reached: dict[float, float] = {}
    gdep = pd.read_csv(DEPOSIT / "geometry.csv")
    reached[ANCHOR] = float(gdep[gdep.arm == "core_to_corner"].reached.mean())
    for d in sorted(a.sweep_dir.glob("th*")):
        try:
            th = float(d.name[2:])
        except ValueError:
            continue
        pr = d / "per_row.csv"
        if not pr.exists():
            print(f"  пропуск {d.name}: нет per_row.csv")
            continue
        per_th[th] = pd.read_csv(pr).query("arm == 'core_to_corner'")
        gs = [pd.read_csv(f) for f in sorted(d.glob("geom_seed*.csv"))]
        if gs:
            g = pd.concat(gs)
            reached[th] = float(g[g.arm == "core_to_corner"].reached.mean())

    ths = sorted(per_th)
    res: dict = {
        "thresholds": ths, "anchor": ANCHOR,
        "rule_predeclared": {"rho_confirm": RHO_CONFIRM, "rho_arbitrary": RHO_ARBITRARY,
                             "low_point_fraction": LOW_POINT_FRACTION,
                             "min_seeds_monotone": MIN_SEEDS_MONOTONE,
                             "min_reached": MIN_REACHED},
        "bootstrap": {"seed": BOOT_SEED, "draws": BOOT_DRAWS, "cluster_unit": "solvent_smiles"},
        "reached_fraction": reached, "per_threshold": {},
    }

    d_eq, d_row = {}, {}
    for th in ths:
        e = eq_weight(per_th[th], base)
        r = row_weight(per_th[th], base)
        d_eq[th], d_row[th] = e, r
        res["per_threshold"][str(th)] = {
            "D_eq_seed_mean": float(np.mean(list(e.values()))), "D_eq_per_seed": e,
            "D_row_seed_mean": float(np.mean(list(r.values()))), "D_row_per_seed": r,
            "n_bins_in_corner": None, "reached_fraction": reached.get(th),
        }

    # ворота воспроизведения на опорном пороге
    res["reproduction_gate"] = {
        "D_eq_anchor": res["per_threshold"][str(ANCHOR)]["D_eq_seed_mean"],
        "D_row_anchor": res["per_threshold"][str(ANCHOR)]["D_row_seed_mean"],
        "expected_D_eq": 0.2927, "expected_D_row": 1.0712,
    }
    g = res["reproduction_gate"]
    g["matches"] = bool(abs(g["D_eq_anchor"] - 0.2927) < 1e-3
                        and abs(g["D_row_anchor"] - 1.0712) < 1e-3)

    # монотонность: исключить пороги с плохой достижимостью, как объявлено
    usable = [t for t in ths if reached.get(t, 1.0) >= MIN_REACHED]
    res["usable_thresholds"] = usable
    res["excluded_for_reachability"] = [t for t in ths if t not in usable]

    means = [float(np.mean(list(d_eq[t].values()))) for t in usable]
    rho_mean, p_mean = spearmanr(usable, means) if len(usable) >= 3 else (float("nan"),) * 2
    seeds = sorted(d_eq[usable[0]]) if usable else []
    per_seed_rho = {}
    for sd in seeds:
        v = [d_eq[t][sd] for t in usable]
        rr, pp = spearmanr(usable, v)
        per_seed_rho[int(sd)] = {"rho": float(rr), "p": float(pp)}
    res["monotonicity"] = {
        "seed_mean_spearman": float(rho_mean), "p": float(p_mean),
        "per_seed": per_seed_rho,
        "seeds_with_rho_at_least_confirm": int(sum(1 for v in per_seed_rho.values()
                                                   if v["rho"] >= RHO_CONFIRM)),
    }

    low = min(usable) if usable else None
    if low is not None and low != ANCHOR:
        lo_v = float(np.mean(list(d_eq[low].values())))
        an_v = float(np.mean(list(d_eq[ANCHOR].values())))
        res["low_point"] = {"threshold": low, "D_eq": lo_v, "D_eq_anchor": an_v,
                            "ratio": lo_v / an_v if an_v else None,
                            "below_half": bool(lo_v < LOW_POINT_FRACTION * an_v)}

    # CI на каждом пороге
    for th in ths:
        lo, hi = boot_eq(per_th[th], base)
        res["per_threshold"][str(th)]["D_eq_ci95"] = [lo, hi]
        res["per_threshold"][str(th)]["excludes_zero"] = bool(lo > 0 or hi < 0)

    # ПРАВИЛО
    mono = res["monotonicity"]
    lp = res.get("low_point", {})
    cond = {
        "seed_mean_rho_at_least_0.8": bool(mono["seed_mean_spearman"] >= RHO_CONFIRM),
        "at_least_4_of_5_seeds_monotone":
            bool(mono["seeds_with_rho_at_least_confirm"] >= MIN_SEEDS_MONOTONE),
        "low_point_below_half_of_anchor": bool(lp.get("below_half", False)),
    }
    res["predeclared_conditions"] = cond
    if all(cond.values()):
        res["verdict"] = ("ЛОКАЛИЗАЦИЯ ПОДТВЕРЖДЕНА: граница угла несёт информацию, "
                          "цена растёт с продвижением назначения в HB-область")
    elif (abs(mono["seed_mean_spearman"]) < RHO_ARBITRARY
          or (lp and lp.get("D_eq", 0) >= lp.get("D_eq_anchor", 0))):
        res["verdict"] = ("ПОРОГ ПРОИЗВОЛЕН: граница не несёт информации, формулировку про окна "
                          "водородносвязанного ядра надо СНЯТЬ")
    else:
        res["verdict"] = "НЕМОНОТОННО: читать как артефакт геометрии, не как опровержение"
    res["failed_conditions"] = [k for k, v in cond.items() if not v]

    (OUT / "summary.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))

    print(f"ворота воспроизведения на {ANCHOR}: D_eq {g['D_eq_anchor']:.4f} (ожидалось 0.2927), "
          f"D_row {g['D_row_anchor']:.4f} (ожидалось 1.0712) -> {g['matches']}")
    print(f"\n{'порог':>8}{'бинов':>7}{'достиж.':>9}{'D_eq':>9}{'CI95':>22}{'D_row':>9}")
    for th in ths:
        t = res["per_threshold"][str(th)]
        ci = t.get("D_eq_ci95", [float('nan')] * 2)
        print(f"{th:>8.3f}{'':>7}{100*(reached.get(th, float('nan'))):>8.0f}%"
              f"{t['D_eq_seed_mean']:>9.4f}{f'[{ci[0]:+.3f}, {ci[1]:+.3f}]':>22}"
              f"{t['D_row_seed_mean']:>9.4f}")
    print(f"\nСпирмен(порог, D_eq) на седовом среднем = {mono['seed_mean_spearman']:+.3f} "
          f"(p = {mono['p']:.4f})")
    print("по сидам: " + ", ".join(f"{k}:{v['rho']:+.2f}" for k, v in per_seed_rho.items()))
    if lp:
        print(f"нижняя точка {lp['threshold']}: D_eq {lp['D_eq']:.4f} против опорной "
              f"{lp['D_eq_anchor']:.4f}, отношение {lp['ratio']:.3f}, ниже половины: {lp['below_half']}")
    if res["excluded_for_reachability"]:
        print(f"исключены по достижимости < {MIN_REACHED}: {res['excluded_for_reachability']}")
    print(f"\nВЕРДИКТ: {res['verdict']}")
    if res["failed_conditions"]:
        print("не выполнены:", res["failed_conditions"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
