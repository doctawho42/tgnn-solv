#!/usr/bin/env python
"""Воротв перед покупкой T1: указывает ли вектор весов туда, где лежит ошибка профиля.

ПОЧЕМУ ЭТО СЧИТАЕТСЯ ДО АРМА, А НЕ ПОСЛЕ. Вес из results/per_bin_sensitivity_weights выведен из
ЦЕНЫ ЗАМЫКАНИЯ: сколько стоит положить массу не туда. Он ничего не знает о том, где выученный
профиль на самом деле ошибается. Перевзвешивание супервизии может помочь только если эти две карты
пересекаются: если ошибка уже сидит в дорогих бинах, усиление супервизии там даёт оптимизатору тягу
по делу; если ошибка сидит в дешёвых бинах, которые вес ПРИГЛУШАЕТ, арм предсказуемо ничего не
изменит, и платить за него нечем.

Измеряется на ПЯТИ уже лежащих чекпойнтах референсного плеча, то есть бесплатно.

ДВЕ ПОВЕРХНОСТИ, И ЭТО НЕ ДЕТАЛЬ. Вектор для T1 выведен на train-строках, а читать арм придётся на
IDAC. По измерению асимметрия веса по знаку sigma у этих наборов ПРОТИВОПОЛОЖНАЯ и это свойство
набора, а не сида (train: отношение w(s>0)/w(s<0) = 2.26...2.97 по пяти сидам, idac: 0.55...0.75,
диапазоны не пересекаются). Поэтому согласие "вес против ошибки" считается отдельно для каждого
вектора, и расхождение между ними есть предсказание о том, чего от арма ждать нельзя.

НУЛЕВОЕ ПЛЕЧО: тот же вес с ПЕРЕМЕШАННЫМИ бинами. Доля ошибки в дорогих бинах обязана отличаться от
того, что даёт случайная расстановка тех же весов, иначе "вес указывает на ошибку" есть
арифметическое следствие формы ошибки, а не свойство веса.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/read_t1_weight_points_at_error.py
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
sys.path.insert(0, str(ROOT / "scripts/analysis"))

from run_sigma_profile_residual import build_model, learned_profiles  # noqa: E402
from tgnn_solv.data.utils import canonicalize                  # noqa: E402
from tgnn_solv.layers import CosmoSacLayer                      # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles          # noqa: E402

PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
IDAC_RECORDS = ROOT / "results/published_idac_check/scored_records.csv"
WEIGHTS = ROOT / "results/per_bin_sensitivity_weights/summary.json"
CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
OUT = ROOT / "results/per_bin_sensitivity_weights"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--n-shuffle", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    layer = CosmoSacLayer()
    n_bins = int(layer.n_bins)
    table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
    W = json.loads(WEIGHTS.read_text(encoding="utf8"))
    vecs = {k: np.asarray(W["by_rows"][k]["w_seed_mean"], float) for k in W["by_rows"]}

    # Растворители IDAC -- та поверхность, на которой арм будут читать.
    d = pd.read_csv(IDAC_RECORDS)
    mols = sorted({str(s) for s in d.solvent_smiles
                   if canonicalize(str(s)) in table})
    tpl = pd.read_csv(ROOT / "notebooks/data/processed/test.csv", nrows=1, low_memory=False)
    ref = np.stack([table[canonicalize(m)][0] for m in mols])
    ref = ref / np.maximum(ref.sum(1, keepdims=True), 1e-30)
    print(f"растворителей IDAC с эталонным профилем: {len(mols)}; бинов {n_bins}")

    res: dict = {"n_solvents": len(mols), "n_bins": n_bins, "seeds": list(a.seeds),
                 "n_shuffle": a.n_shuffle, "by_weight_vector": {}}
    errs = []
    for s in a.seeds:
        ck = CKPT_DIR / f"grounded_a_seed{s}.pt"
        if not ck.exists():
            print(f"  сид {s}: чекпойнта нет, пропуск")
            continue
        model, _, cfg = build_model(ck)
        _, as_solvent = learned_profiles(model, cfg, mols, tpl)
        lp = np.asarray(as_solvent, float)
        lp = lp / np.maximum(lp.sum(1, keepdims=True), 1e-30)
        errs.append(np.abs(lp - ref).mean(0))          # средняя по молекулам |d| в каждом бине
    E = np.stack(errs)
    res["per_bin_abs_error_seed_mean"] = E.mean(0).tolist()
    res["per_bin_abs_error_seed_sd"] = E.std(0, ddof=1).tolist()
    print(f"посчитано по {len(E)} сидам; |d| по бинам: медиана {np.median(E.mean(0)):.5f}, "
          f"макс {E.mean(0).max():.5f} в бине {int(E.mean(0).argmax())}")

    rng = np.random.default_rng(a.seed)
    from scipy.stats import spearmanr
    for name, w in vecs.items():
        # доля ошибки, попавшая в дорогую треть бинов, и в дешёвую
        hi = w >= np.quantile(w, 2 / 3)
        lo = w <= np.quantile(w, 1 / 3)
        per_seed = []
        for e in E:
            en = e / e.sum()
            per_seed.append({"share_in_expensive_third": float(en[hi].sum()),
                             "share_in_cheap_third": float(en[lo].sum()),
                             "spearman_w_vs_error": float(spearmanr(w, e).statistic),
                             # то, что лосс реально увидит: взвешенная ошибка против невзвешенной
                             "weighted_over_unweighted": float((w * e).sum() / e.sum())})
        em = E.mean(0)
        emn = em / em.sum()
        # НУЛЬ: те же веса, перемешанные по бинам
        null_hi, null_rho = [], []
        for _ in range(a.n_shuffle):
            wp = rng.permutation(w)
            h = wp >= np.quantile(wp, 2 / 3)
            null_hi.append(float(emn[h].sum()))
            null_rho.append(float(spearmanr(wp, em).statistic))
        obs = float(emn[hi].sum())
        p = float((np.asarray(null_hi) >= obs).mean())
        rho = float(spearmanr(w, em).statistic)
        res["by_weight_vector"][name] = {
            "n_expensive_bins": int(hi.sum()), "n_cheap_bins": int(lo.sum()),
            "share_in_expensive_third": obs,
            "share_in_cheap_third": float(emn[lo].sum()),
            "spearman_w_vs_error": rho,
            "null_share_mean": float(np.mean(null_hi)),
            "null_share_p95": float(np.quantile(null_hi, 0.95)),
            "p_one_sided_vs_shuffled_weights": p,
            "per_seed": per_seed,
        }
        shares = [x["share_in_expensive_third"] for x in per_seed]
        rhos = [x["spearman_w_vs_error"] for x in per_seed]
        print(f"\nвектор {name}  ({int(hi.sum())} дорогих бинов из {n_bins}, "
              f"то есть {100 * hi.sum() / n_bins:.0f}% сетки)")
        print(f"  доля ошибки в ДОРОГОЙ трети: {100 * obs:.1f}%  "
              f"(посидово {100 * min(shares):.1f}...{100 * max(shares):.1f}%)")
        print(f"  доля ошибки в ДЕШЁВОЙ трети: {100 * emn[lo].sum():.1f}%")
        print(f"  нуль (перемешанные веса):    {100 * np.mean(null_hi):.1f}%, "
              f"p95 {100 * np.quantile(null_hi, 0.95):.1f}%  ->  p = {p:.4f}")
        print(f"  Спирмен(вес, ошибка) = {rho:+.3f}  (посидово "
              f"{min(rhos):+.3f}...{max(rhos):+.3f})")

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "weight_points_at_error.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"\nзаписано: {a.out / 'weight_points_at_error.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
