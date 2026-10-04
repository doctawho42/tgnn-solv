#!/usr/bin/env python
"""Измерить ПОЛ по сиду для осей E2 на уже выложенной пятёрке сидов -- без обучения.

ЗАЧЕМ. Предзаявка E2 (``results/e2_crystal_detach/PRE_DECLARATION.md``) задаёт порог 0.07 по
``ln x2`` из опубликованных межсидовых sd и честно пишет: «Пола для ``delta_phi_mean`` на одном
сиде нет вовсе. Он появится только с репликатом». Это неверно: пол измерим прямо сейчас и
бесплатно. В ``results/e5_sigma_grounding_leakfree/`` лежат предсказания ТРЁХ плеч на ПЯТИ сидах
одного сплита, и в них есть все физические промежуточные величины. Пол, стоящий 9 GPU-часов
ожидания, стоит пяти секунд pandas.

ЧТО ИМЕННО МЕРИТСЯ, И ПОЧЕМУ ДВА ПОЛА, А НЕ ОДИН. Для E2 важен пол ПАРНОЙ разницы двух плеч на
одном сиде, а не маргинальный разброс одного плеча: если сид входит в оба плеча одинаково,
разность его гасит и пара читается точнее, чем каждое плечо по отдельности. Это надежда, а не
факт, и она проверяема -- поэтому считаются оба и печатается их отношение. Там, где отношение
больше единицы, сидовые эффекты плеч НЕ общие, и разность шумнее любого из плеч.

ЕДИНСТВЕННЫЙ ПОДЛИННЫЙ КОНТРАСТ ЗДЕСЬ ОДИН. Плечо ``oracle`` -- это ТЕ ЖЕ веса, оценённые с
подставленным σ-профилем (колонка ``sigma_oracle_applied``), а не второе обучение: его
``T_m_solver`` отличается от ``grounded_a`` на 6.4e-4 K, тогда как у ``ungrounded`` -- на 224 K.
Поэтому разность ``oracle - grounded_a`` даёт на кристаллических осях почти ровные нули, и читать
их как «контраст не двигает кристалл» нельзя: это один и тот же кристалл. Пол парной разницы
опирается на ``ungrounded - grounded_a`` -- один контраст, пять сидов. Узкая база, но измеренная.

ОСИ. (1) ``delta_phi_mean`` под штатной ``compensation_row_mask`` -- ЗАЯВЛЕННАЯ ось E2; маска
требует и измеренного ``T_m``, и измеренного ``dH_fus``, а второй есть у одного растворяемого.
(2) Смещение ``T_m`` в кельвинах на страте с ИЗМЕРЕННЫМ ``T_m`` запертых строк, агрегированное
СНАЧАЛА по растворяемому -- потому что эффективное n это число кластеров, а не строк.
(3) ``ln x2`` MAE на запертых строках -- ось задачи и единственная, для которой порог уже заявлен.

ВТОРАЯ ЧАСТЬ: КАКУЮ НЕОПРЕДЕЛЁННОСТЬ ОДНА ПАРА ВПРАВЕ ЦИТИРОВАТЬ. Между-сидовый sd отвечает на
вопрос «дал бы другой сид другой ответ» -- и ОДНОЙ паре он недоступен, потому что сид у неё один.
Доступен ей бутстрэп по кластерам растворяемых внутри своего сида. Это РАЗНЫЕ величины, и
подменять одну другой нельзя. Поэтому для каждой оси считаются обе и печатается, на скольких сидах
внутрисидовый CI исключает нуль -- то есть как часто одна пара доложила бы уверенный эффект там,
где поперёк сидов его нет. Если такие сиды есть и знаки среди них расходятся, внутрисидовый
бутстрэп не просто занижает неопределённость, а производит уверенные ответы противоположного знака,
и цитировать его в одиночку нельзя.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from tgnn_solv.diagnostics.compensation import (
    annotate_compensation_frame,
    compensation_row_mask,
)

SEEDS = (42, 43, 44, 45, 46)
#: ``grounded_a`` -- база. ``ungrounded`` -- ЕДИНСТВЕННОЕ второе обучение. ``oracle`` считается
#: тоже, но только чтобы напечатать, что он не контраст: иначе его нули кто-нибудь прочтёт.
ARMS = ("grounded_a", "oracle", "ungrounded")
BASE = "grounded_a"
TRUE_CONTRASTS = ("ungrounded",)


def _bool(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col].astype(str).str.lower().isin(("true", "1", "1.0"))


def arm_axes(path: Path) -> dict[str, float | int]:
    df = pd.read_csv(path)
    ann = annotate_compensation_frame(df, label=path.stem)

    declared = ann[compensation_row_mask(ann)]
    locked = ann[_bool(ann, "has_solubility")]
    tm_stratum = ann[_bool(ann, "has_solubility") & _bool(ann, "has_T_m")]
    per_solute = tm_stratum.groupby("solute_canonical").agg(
        measured=("T_m", "mean"), predicted=("T_m_solver", "mean"))

    return {
        "delta_phi_mean": float(declared["delta_phi"].mean()),
        "delta_phi_rows": int(len(declared)),
        "delta_phi_solutes": int(declared["solute_canonical"].nunique()),
        "T_m_bias_K": float((per_solute["predicted"] - per_solute["measured"]).mean()),
        "T_m_solutes": int(len(per_solute)),
        "T_m_rows": int(len(tm_stratum)),
        "ln_x2_mae": float((locked["ln_x2_pred"] - locked["ln_x2_true"]).abs().mean()),
        "locked_rows": int(len(locked)),
        "locked_solutes": int(locked["solute_canonical"].nunique()),
    }


#: Бутстрэп детерминирован по сиду: иначе артефакт не воспроизводится, а в этом проекте
#: воспроизводимый артефакт -- выше всякой прозы.
BOOTSTRAP_SEED = 20261004
BOOTSTRAP_DRAWS = 20000


def per_solute_values(path: Path, axis: str) -> pd.Series:
    """Значение оси ПО РАСТВОРЯЕМОМУ -- единица репликации для бутстрэпа по кластерам."""
    df = pd.read_csv(path)
    ann = annotate_compensation_frame(df, label=path.stem)
    if axis == "delta_phi_mean":
        sub = ann[compensation_row_mask(ann)]
        return sub.groupby("solute_canonical")["delta_phi"].mean()
    if axis == "T_m_bias_K":
        sub = ann[_bool(ann, "has_solubility") & _bool(ann, "has_T_m")]
        g = sub.groupby("solute_canonical").agg(m=("T_m", "mean"), p=("T_m_solver", "mean"))
        return g["p"] - g["m"]
    if axis == "ln_x2_mae":
        sub = ann[_bool(ann, "has_solubility")].copy()
        sub["ae"] = (sub["ln_x2_pred"] - sub["ln_x2_true"]).abs()
        return sub.groupby("solute_canonical")["ae"].mean()
    raise ValueError(axis)


def cluster_bootstrap(diff: np.ndarray, rng: np.random.Generator) -> dict:
    """95% CI среднего парной разности, ресэмпл по КЛАСТЕРАМ.

    При одном кластере CI вырожден в точку. Это не ошибка, а главная находка про заявленную ось
    E2: неопределённость, доступная одной паре, там равна нулю по построению, то есть её нет.
    """
    n = len(diff)
    if n < 2:
        return {"n": n, "mean": float(diff.mean()) if n else float("nan"),
                "ci95": [float("nan"), float("nan")], "excludes_zero": False,
                "degenerate": True}
    idx = rng.integers(0, n, size=(BOOTSTRAP_DRAWS, n))
    means = diff[idx].mean(axis=1)
    lo, hi = (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))
    return {"n": n, "mean": float(diff.mean()), "sd_across_clusters": float(diff.std(ddof=1)),
            "ci95": [lo, hi], "excludes_zero": bool(lo > 0 or hi < 0), "degenerate": False}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pred-dir", type=Path,
                    default=Path("results/e5_sigma_grounding_leakfree"))
    ap.add_argument("--out", type=Path, default=Path("results/e2_crystal_detach/seed_floor.json"))
    a = ap.parse_args()

    table: dict[tuple[int, str], dict] = {}
    for seed in SEEDS:
        for arm in ARMS:
            p = a.pred_dir / f"seed_{seed}" / f"{arm}_predictions.csv"
            if not p.exists():
                raise SystemExit(f"нет {p}: пол считается только по полной пятёрке")
            table[(seed, arm)] = arm_axes(p)

    shape = {k: table[(SEEDS[0], BASE)][k] for k in
             ("delta_phi_rows", "delta_phi_solutes", "T_m_rows", "T_m_solutes",
              "locked_rows", "locked_solutes")}
    print("форма оценочной поверхности:", json.dumps(shape, ensure_ascii=False))
    print("\nВНИМАНИЕ: эффективное n заявленной оси E2 = "
          f"{shape['delta_phi_solutes']} растворяемых ({shape['delta_phi_rows']} строк).")

    floors: dict[str, dict] = {}
    for key, label in (("delta_phi_mean", "delta_phi_mean (заявленная ось)"),
                       ("T_m_bias_K", "смещение T_m, K (измеренный T_m, по растворяемым)"),
                       ("ln_x2_mae", "ln x2 MAE (ось задачи)")):
        print(f"\n=== {label} ===")
        head = "сид " + " ".join(f"{x:>12s}" for x in ARMS)
        print(head + "   " + " ".join(f"{'Δ ' + x[:9]:>12s}" for x in ARMS[1:]))
        for seed in SEEDS:
            vals = [table[(seed, x)][key] for x in ARMS]
            print(f"{seed} " + " ".join(f"{v:12.4f}" for v in vals) + "   "
                  + " ".join(f"{v - vals[0]:12.4f}" for v in vals[1:]))

        marginal = np.array([table[(s, BASE)][key] for s in SEEDS], dtype=float)
        entry = {"marginal_sd": float(marginal.std(ddof=1)),
                 "marginal_mean": float(marginal.mean()), "paired": {}}
        print(f"  маргинальный sd {BASE} по сидам : {entry['marginal_sd']:.4f}")
        for arm in ARMS[1:]:
            d = np.array([table[(s, arm)][key] - table[(s, BASE)][key] for s in SEEDS], float)
            genuine = arm in TRUE_CONTRASTS
            entry["paired"][arm] = {"sd": float(d.std(ddof=1)), "mean": float(d.mean()),
                                    "is_a_second_training": genuine}
            note = "" if genuine else "   <- НЕ второе обучение, не пол"
            print(f"  ПАРНЫЙ sd ({arm} - {BASE}): {d.std(ddof=1):.4f}  "
                  f"среднее {d.mean():+.4f}  "
                  f"= {d.std(ddof=1) / entry['marginal_sd']:.0%} маргинального{note}")
        floors[key] = entry

    # ===== какую неопределённость одна пара вправе цитировать =====
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    within: dict[str, dict] = {}
    for axis in ("delta_phi_mean", "T_m_bias_K", "ln_x2_mae"):
        print(f"\n=== {axis}: внутрисидовый бутстрэп по кластерам против между-сидового sd ===")
        print(f"{'сид':>4} {'кластеров':>10} {'средняя Δ':>12} {'bootstrap 95% CI':>26} "
              f"{'исключает 0':>12}")
        rows, signs = [], []
        for seed in SEEDS:
            base_v = per_solute_values(
                a.pred_dir / f"seed_{seed}" / f"{BASE}_predictions.csv", axis)
            out_rows = {}
            for arm in TRUE_CONTRASTS:
                arm_v = per_solute_values(
                    a.pred_dir / f"seed_{seed}" / f"{arm}_predictions.csv", axis)
                common = base_v.index.intersection(arm_v.index)
                d = (arm_v[common] - base_v[common]).to_numpy(float)
                bs = cluster_bootstrap(d, rng)
                out_rows[arm] = bs
                ci = ("вырожден" if bs["degenerate"]
                      else f"[{bs['ci95'][0]:9.3f}, {bs['ci95'][1]:9.3f}]")
                print(f"{seed:>4} {bs['n']:>10} {bs['mean']:12.3f} {ci:>26} "
                      f"{('ДА' if bs['excludes_zero'] else 'нет'):>12}")
                if bs["excludes_zero"]:
                    signs.append((seed, float(np.sign(bs["mean"]))))
            rows.append({"seed": seed, **out_rows})
        between = floors[axis]["paired"][TRUE_CONTRASTS[0]]["sd"]
        confident = len(signs)
        conflict = len({sg for _, sg in signs}) > 1
        print(f"  между-сидовый sd той же парной разности : {between:.4f}")
        print(f"  сидов, где внутрисидовый CI исключает нуль: {confident} из {len(SEEDS)}"
              + (f"  -> {signs}" if signs else ""))
        if conflict:
            print("  ЗНАКИ СРЕДИ УВЕРЕННЫХ СИДОВ РАСХОДЯТСЯ: внутрисидовый бутстрэп производит "
                  "уверенные ответы ПРОТИВОПОЛОЖНОГО знака. Цитировать его в одиночку нельзя.")
        within[axis] = {"per_seed": rows, "between_seed_paired_sd": between,
                        "seeds_with_confident_nonzero": confident,
                        "confident_signs_conflict": conflict,
                        "confident_seeds": [{"seed": s_, "sign": sg} for s_, sg in signs]}

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(
        {"surface": shape, "seeds": list(SEEDS), "arms": list(ARMS), "base": BASE,
         "true_contrasts": list(TRUE_CONTRASTS),
         "bootstrap": {"seed": BOOTSTRAP_SEED, "draws": BOOTSTRAP_DRAWS},
         "per_seed": {f"{s}|{arm}": table[(s, arm)] for s in SEEDS for arm in ARMS},
         "floors": floors, "within_seed_vs_between_seed": within},
        indent=2, ensure_ascii=False) + "\n")
    print(f"\nзаписано {a.out}")


if __name__ == "__main__":
    main()
