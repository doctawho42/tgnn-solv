"""Держится ли «цену определяет РАСПОЛОЖЕНИЕ» без воды и без доминирующих растворителей.

ЗАЧЕМ. Контраст «угол минус ядро при одинаковом Хеллингере» (+1.0712, положителен на всех пяти
сидах, `results/sigma_displacement_geometry/RESULTS.md`) предлагается сделать спиной статьи.
Кластеризация там по растворителю, и возражение референта очевидно: не несёт ли шестикратный
эффект один доминирующий растворитель, в первую очередь вода.

ЧЕГО ЭТОТ СКРИПТ НЕ ДЕЛАЕТ. Развёртки по порогу угла (|sigma| >= 0.016) здесь нет: плечи
сконструированы с порогом внутри, другой порог — другая подстановка, то есть новый прогон модели.
Проверяется устойчивость к СОСТАВУ РАСТВОРИТЕЛЕЙ, и только она.

Правило чтения и порог 0.5 объявлены до счёта в
`results/sigma_location_robustness/PRE_DECLARATION.md`.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path("results/sigma_displacement_geometry")
OUT = Path("results/sigma_location_robustness")
WATER = "O"
TREATED, BASE, NULL = "core_to_corner", "core_to_core", "identity_solvent"
BOOT_SEED, BOOT_DRAWS = 20261021, 4000
#: Объявлен в предзаявке ДО счёта: заявление — шестикратный разброс, половина оставляет ~трёхкратный.
SURVIVE_FRACTION = 0.5


def kish(counts: np.ndarray) -> float:
    """Эффективное n по Кишу: (sum w)^2 / sum w^2."""
    w = np.asarray(counts, dtype=float)
    return float(w.sum() ** 2 / (w ** 2).sum())


def seed_mean_contrast(df: pd.DataFrame, weight_by_solvent_equally: bool = False) -> tuple[float, list[float]]:
    """D = седовое среднее от (MAE угла − MAE ядра). Приведение построчное, как у порога."""
    per_seed = []
    for _, g in df.groupby("seed"):
        a, b = g[g.arm == TREATED], g[g.arm == BASE]
        if weight_by_solvent_equally:
            # каждый растворитель весит одинаково: сначала среднее внутри растворителя
            ma = a.groupby("solvent_smiles").abs_err.mean()
            mb = b.groupby("solvent_smiles").abs_err.mean()
            common = ma.index.intersection(mb.index)
            per_seed.append(float((ma[common] - mb[common]).mean()))
        else:
            per_seed.append(float(a.abs_err.mean() - b.abs_err.mean()))
    return float(np.mean(per_seed)), per_seed


def cluster_bootstrap(df: pd.DataFrame, equal: bool = False) -> tuple[float, float]:
    """Кластерный бутстрэп по РАСТВОРИТЕЛЮ на седовом среднем."""
    rng = np.random.default_rng(BOOT_SEED)
    solvents = df.solvent_smiles.unique()
    by_solvent = {s: g for s, g in df.groupby("solvent_smiles")}
    draws = np.empty(BOOT_DRAWS)
    for i in range(BOOT_DRAWS):
        pick = rng.choice(solvents, size=len(solvents), replace=True)
        draws[i] = seed_mean_contrast(pd.concat([by_solvent[s] for s in pick]), equal)[0]
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(SRC / "per_row.csv")
    arms = df[df.arm.isin([TREATED, BASE])]

    res: dict = {"source": str(SRC), "bootstrap": {"seed": BOOT_SEED, "draws": BOOT_DRAWS,
                                                   "cluster_unit": "solvent_smiles"},
                 "survive_fraction_predeclared": SURVIVE_FRACTION}

    # --- ворота воспроизведения ---
    d_all, per_seed_all = seed_mean_contrast(arms)
    res["reproduction_gate"] = {
        "D_all": d_all, "per_seed": per_seed_all,
        "deposit_D": 1.0712, "deposit_per_seed": [1.002, 0.935, 1.545, 1.275, 0.598],
        "matches": bool(abs(d_all - 1.0712) < 1e-3),
    }
    assert abs(d_all - 1.0712) < 1e-3, (
        f"ВОРОТА ВОСПРОИЗВЕДЕНИЯ ПРОВАЛЕНЫ: D_all={d_all:.4f} против депонированного 1.0712 -- "
        "пересчёт идёт по ДРУГОЙ поверхности, дальше читать нельзя")

    # --- нулевое плечо: identity обязано быть нулём при каждом перевзвешивании ---
    null = df[df.arm.isin([NULL, "control"])]
    null_rowwise = float(np.mean([g[g.arm == NULL].abs_err.mean() - g[g.arm == "control"].abs_err.mean()
                                  for _, g in null.groupby("seed")]))
    nulls = {"rowwise_all": null_rowwise}
    for tag, sub in (("nowater", null[null.solvent_smiles != WATER]), ("all", null)):
        vals = []
        for _, g in sub.groupby("seed"):
            ma = g[g.arm == NULL].groupby("solvent_smiles").abs_err.mean()
            mb = g[g.arm == "control"].groupby("solvent_smiles").abs_err.mean()
            c = ma.index.intersection(mb.index)
            vals.append(float((ma[c] - mb[c]).mean()))
        nulls[f"eqweight_{tag}"] = float(np.mean(vals))
    res["null_arm"] = nulls
    res["null_arm_is_zero_everywhere"] = bool(max(abs(v) for v in nulls.values()) < 1e-6)

    # --- инвентаризация состава ---
    one = df[(df.seed == 42) & (df.arm == "control")]
    counts = one.solvent_smiles.value_counts()
    res["composition"] = {
        "n_solvents": int(len(counts)), "n_rows": int(counts.sum()),
        "kish_effective_n": kish(counts.values),
        "water_row_fraction": float(counts.get(WATER, 0) / counts.sum()),
        "top5_fraction": float(counts.head(5).sum() / counts.sum()),
        "kish_effective_n_nowater": kish(counts.drop(index=WATER, errors="ignore").values),
    }

    # --- плечо 1: без воды ---
    nw = arms[arms.solvent_smiles != WATER]
    d_nw, ps_nw = seed_mean_contrast(nw)
    lo, hi = cluster_bootstrap(nw)
    res["D_nowater"] = {"D": d_nw, "per_seed": ps_nw, "ci95": [lo, hi],
                        "excludes_zero": bool(lo > 0 or hi < 0),
                        "signs_positive": int(sum(1 for x in ps_nw if x > 0)),
                        "ratio_to_D_all": d_nw / d_all}

    # --- плечо 2: равный вес растворителям ---
    d_eq, ps_eq = seed_mean_contrast(arms, weight_by_solvent_equally=True)
    lo2, hi2 = cluster_bootstrap(arms, equal=True)
    res["D_eqweight"] = {"D": d_eq, "per_seed": ps_eq, "ci95": [lo2, hi2],
                         "excludes_zero": bool(lo2 > 0 or hi2 < 0),
                         "signs_positive": int(sum(1 for x in ps_eq if x > 0)),
                         "ratio_to_D_all": d_eq / d_all}

    # --- плечо 3: складной нож по растворителям ---
    jack = {}
    for s in sorted(arms.solvent_smiles.unique()):
        d_s, _ = seed_mean_contrast(arms[arms.solvent_smiles != s])
        jack[s] = {"D_without": d_s, "shift": d_s - d_all}
    worst = max(jack.items(), key=lambda kv: abs(kv[1]["shift"]))
    res["jackknife"] = {
        "n_solvents": len(jack),
        "max_abs_shift": abs(worst[1]["shift"]), "most_influential_solvent": worst[0],
        "most_influential_shift": worst[1]["shift"],
        "any_single_solvent_moves_more_than_half": bool(abs(worst[1]["shift"]) > SURVIVE_FRACTION * d_all),
        "top10_by_influence": {k: v for k, v in sorted(jack.items(), key=lambda kv: -abs(kv[1]["shift"]))[:10]},
    }

    # --- плечо 4: контроль сопоставления (штраф не должен идти за достигнутым H) ---
    geom = pd.read_csv(SRC / "geometry.csv")
    g_t = geom[geom.arm == TREATED].set_index(["seed", "smiles"]).H_achieved
    g_b = geom[geom.arm == BASE].set_index(["seed", "smiles"]).H_achieved
    rows = []
    for (sd, slv), _ in arms.groupby(["seed", "solvent_smiles"]):
        if (sd, slv) in g_t.index and (sd, slv) in g_b.index:
            sub = arms[(arms.seed == sd) & (arms.solvent_smiles == slv)]
            pen = sub[sub.arm == TREATED].abs_err.mean() - sub[sub.arm == BASE].abs_err.mean()
            rows.append({"seed": sd, "solvent": slv, "penalty": pen,
                         "dH": float(g_t[(sd, slv)] - g_b[(sd, slv)])})
    md = pd.DataFrame(rows)
    from scipy.stats import spearmanr
    per_seed_rho = {}
    for sd, g in md.groupby("seed"):
        rho, p = spearmanr(g.penalty, g.dH)
        per_seed_rho[int(sd)] = {"rho": float(rho), "p": float(p), "n_solvents": int(len(g))}
    res["matching_control"] = {
        "question": "идёт ли штраф за РАЗНИЦЕЙ достигнутого H, а не за расположением",
        "per_seed_spearman_penalty_vs_dH": per_seed_rho,
        "median_dH": float(md.dH.median()),
        "note": "ядро достигает чуть МЕНЬШЕГО H (депозит печатает 2.6%), что завышает контраст; "
                "если штраф идёт за dH, контраст не про «куда»",
    }
    md.to_csv(OUT / "per_solvent.csv", index=False)

    # --- ПРАВИЛО, объявленное до чисел ---
    cond = {
        "D_nowater_at_least_half": bool(d_nw >= SURVIVE_FRACTION * d_all),
        "D_eqweight_at_least_half": bool(d_eq >= SURVIVE_FRACTION * d_all),
        "nowater_ci_excludes_zero": res["D_nowater"]["excludes_zero"],
        "eqweight_ci_excludes_zero": res["D_eqweight"]["excludes_zero"],
        "nowater_signs_at_least_4of5": bool(res["D_nowater"]["signs_positive"] >= 4),
        "eqweight_signs_at_least_4of5": bool(res["D_eqweight"]["signs_positive"] >= 4),
        "no_single_solvent_carries_it": not res["jackknife"]["any_single_solvent_moves_more_than_half"],
    }
    res["predeclared_conditions"] = cond
    if all(cond.values()):
        res["verdict"] = "ДЕРЖИТСЯ: локализация не несётся водой и не несётся одним растворителем"
    elif res["jackknife"]["any_single_solvent_moves_more_than_half"]:
        res["verdict"] = ("ОПИРАЕТСЯ НА ОДИН РАСТВОРИТЕЛЬ: "
                          f"{res['jackknife']['most_influential_solvent']!r}")
    else:
        res["verdict"] = "НЕ ДЕРЖИТСЯ: обобщение «расположение, а не величина» снимается"
    res["failed_conditions"] = [k for k, v in cond.items() if not v]

    (OUT / "summary.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in res.items() if k != "jackknife"}, indent=2, ensure_ascii=False))
    print("\nскладной нож, 10 самых влиятельных:")
    for k, v in res["jackknife"]["top10_by_influence"].items():
        print(f"  {k!r:28s} D без него = {v['D_without']:+.4f}  сдвиг {v['shift']:+.4f}")
    print(f"\nВЕРДИКТ: {res['verdict']}")
    if res["failed_conditions"]:
        print("не выполнены:", res["failed_conditions"])


if __name__ == "__main__":
    main()
