#!/usr/bin/env python
"""4a: ПО-БИНОВАЯ карта цены замыкания и выведенный из неё вектор весов для T1.

ЗАЧЕМ ОТДЕЛЬНЫЙ СКРИПТ. results/closure_sensitivity_map даёт по-биновую карту только ПО ГРАДИЕНТУ,
а её собственный вывод запрещает ею взвешивать: градиент завышает отношение угол/ядро вчетверо
(62x против 15x на конечном переносе) и сидонеустойчив (9.4...62.0 по пяти сидам против 12.9...15.0
у конечной разности). По конечной разности там посчитаны ВСЕГО ТРИ числа -- ядро->ядро, ядро->угол
и их отношение. Вектора из 51 числа, которым можно взвесить лосс, не существует. Здесь он считается.

ЧТО ИМЕННО МЕРЯЕТСЯ, И ПОЧЕМУ ЭТО НЕ ТО ЖЕ, ЧТО ИНДЕКС EMD. Форменный член -- это
sum_k |cumsum(pred)_k - cumsum(target)_k| (loss.py:100-104). Слагаемое с индексом k оценивает
МАССУ, ПЕРЕСЕКАЮЩУЮ ГРАНИЦУ между бинами k и k+1, а карта чувствительности оценивает КОНЕЧНОЕ
ПОЛОЖЕНИЕ массы. Это две разные поверхности, и наивно повесить по-биновый вес прямо на индекс EMD
значит применить вес, измеренный на одной, к величине, живущей на другой -- ровно тот дефект,
против которого в CLAUDE.md написан блок ПОРОГИ.

Мост между поверхностями существует и он точный. Взвешенная сумма sum_k w_k |C_k(p) - C_k(q)| есть
1-D Вассерштейн по метрике, в которой расстояние между соседними узлами сетки равно w_k; в такой
метрике перенос из бина i в бин j стоит sum_{k=i}^{j-1} w_k. Если цена замыкания за размещение
единицы массы в бине j есть потенциал R(j), то перенос i->j стоит |R(j) - R(i)|, что совпадает со
взвешенным EMD при

    w_k = |R(k+1) - R(k)|.

То есть МЕРИТЬ надо потенциал размещения R (он же -- та поверхность, на которой карта и её нулевое
плечо уже проверены), а ВЕС лосса есть его дискретный градиент. Обычный EMD -- это частный случай
w_k = const, то есть предположение, что цена растёт равномерно по сетке; измерение этого
предположения не подтверждает (results/sigma_core_boundary_sweep: внутри ядра 0.024-0.037, вне
0.215-0.536, СТУПЕНЬ +0.359 на 5 из 5 сидов).

КАК МЕРЯЕТСЯ R. Для каждого бина-назначения k: забрать frac массы ядра и положить её ЦЕЛИКОМ в бин
k, площадь A сохранить, измерить средний |d ln gamma_2^inf| по строкам. Источник (ядро) и
перенесённая масса (frac от массы ядра) ОДИНАКОВЫ для всех 51 назначения -- меняется только
назначение, то есть контролируемая переменная одна.

НУЛЕВОЕ ПЛЕЧО: то же на случайных профилях той же площади. Если по-биновая карта на выученных
профилях повторяет форму случайной, она про геометрию сетки, а не про химию, и взвешивать ею
нечего.

ВСТРОЕННАЯ СВЕРКА: средний R по угловым бинам, поделённый на средний R по ядру, обязан лежать в
окрестности уже выложенных 12.9...15.0. Стимул не идентичен (там масса размазывалась по всему углу
Дирихле, здесь кладётся в один бин), так что совпадения до цифры ждать нельзя, но порядок обязан
воспроизвестись. Поэтому карта считается на ДВУХ наборах строк:

  --rows train  строки обучающей выборки. Это поверхность, с которой вес можно брать в T1, не
                выводя его на той выборке, на которой арм будут читать.
  --rows idac   строки results/published_idac_check. ТА ЖЕ поверхность, на которой посчитана
                выложенная карта, то есть единственная, на которой сверка с её числами законна.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_per_bin_sensitivity_weights.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts/analysis"))

from run_sigma_profile_residual import build_model, learned_profiles  # noqa: E402
from tgnn_solv.data.utils import canonicalize                  # noqa: E402
from tgnn_solv.layers import CosmoSacLayer                      # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles          # noqa: E402

PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
IDAC_RECORDS = ROOT / "results/published_idac_check/scored_records.csv"
TRAIN_ROWS = ROOT / "notebooks/data/processed/train.csv"
CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
OUT = ROOT / "results/per_bin_sensitivity_weights"


def load_rows(which: str, table: dict, max_rows: int, seed: int) -> pd.DataFrame:
    """Строки (solute, solvent, T), у которых ОБА компонента есть в эталонной таблице."""
    if which == "idac":
        d = pd.read_csv(IDAC_RECORDS)
        tcol = "T_K"
    else:
        d = pd.read_csv(TRAIN_ROWS, low_memory=False)
        tcol = "temperature"
    k2 = [canonicalize(str(s)) for s in d.solute_smiles]
    k1 = [canonicalize(str(s)) for s in d.solvent_smiles]
    ok = np.array([(x in table) and (y in table) for x, y in zip(k2, k1)])
    d = d[ok].reset_index(drop=True)
    print(f"  набор {which}: {int(ok.sum())} из {len(ok)} строк имеют оба профиля в эталоне")
    if len(d) > max_rows:
        # Подвыборка СЛУЧАЙНАЯ с фиксированным сидом, а не head(): у train.csv строки упорядочены
        # по источнику, и head() взял бы один источник целиком.
        d = d.sample(n=max_rows, random_state=seed).reset_index(drop=True)
    return d.rename(columns={tcol: "T_K"})


def ln_gamma(layer, p2, p1, A2, A1, T) -> np.ndarray:
    with torch.no_grad():
        return layer.ln_gamma_inf(
            torch.tensor(p2, dtype=torch.float), torch.tensor(p1, dtype=torch.float),
            torch.tensor(A2, dtype=torch.float), torch.tensor(A1, dtype=torch.float),
            None, None, torch.tensor(T, dtype=torch.float)).numpy()


def residence_map(layer, p2, p1, A2, A1, T, core, frac: float) -> np.ndarray:
    """R[k] = средний |d ln gamma| от переноса frac массы ядра ЦЕЛИКОМ в бин k. Площадь сохранена."""
    n_bins = p1.shape[1]
    base = ln_gamma(layer, p2, p1, A2, A1, T)
    R = np.zeros(n_bins)
    moved = frac * p1[:, core].sum(1, keepdims=True)
    for k in range(n_bins):
        q = p1.copy()
        q[:, core] *= (1.0 - frac)
        q[:, k] += moved[:, 0]
        q *= (A1[:, None] / q.sum(1, keepdims=True))
        R[k] = float(np.abs(ln_gamma(layer, p2, q, A2, A1, T) - base).mean())
    return R


def weights_from_potential(R: np.ndarray, floor_frac: float) -> np.ndarray:
    """w_k = |R(k+1) - R(k)| с полом, нормированный на mean(w) = 1.

    Пол нужен не для красоты: по измерению R почти плоский внутри ядра, и |dR| там близок к нулю.
    Нулевой вес означал бы, что супервизия ВООБЩЕ не получает сигнала о том, в какой бин ядра
    положить массу, а в ядре лежит её основная часть -- форма ядра уехала бы свободно. Пол задаётся
    долей от средней величины |dR| и объявляется в предзаявке вместе с ней.

    Длина вектора -- n_bins, последний элемент дублирует предыдущий: слагаемых |C_k - C_k| в EMD
    ровно n_bins, а границ между бинами n_bins-1, и последнее слагаемое (k = n_bins-1) есть полная
    разность масс, которая на нормированных формах тождественно нуль. Значение веса там ни на что
    не влияет, но длина должна совпадать с длиной суммы.
    """
    dR = np.abs(np.diff(R))
    w = np.maximum(dR, floor_frac * dR.mean())
    w = np.append(w, w[-1])
    return w / w.mean()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", choices=["train", "idac", "both"], default="both")
    ap.add_argument("--max-rows", type=int, default=1500)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--frac", type=float, default=0.05)
    ap.add_argument("--floor-frac", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    layer = CosmoSacLayer()
    layer.eval()
    n_bins = int(layer.n_bins)
    grid = layer.sigma_grid.numpy()
    core = np.abs(grid) <= float(layer.sigma_hb)
    corner = np.abs(grid) >= 0.016
    table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
    print(f"бинов {n_bins}; ядро {int(core.sum())}, угол {int(corner.sum())}; "
          f"перенос {100 * a.frac:.0f}% массы ядра, пол веса {100 * a.floor_frac:.0f}% от mean|dR|")

    res: dict = {"n_bins": n_bins, "fraction_moved": a.frac, "floor_frac": a.floor_frac,
                 "sigma_grid": grid.tolist(), "core": core.tolist(), "corner": corner.tolist(),
                 "seeds": list(a.seeds), "by_rows": {}}
    tpl = pd.read_csv(ROOT / "notebooks/data/processed/test.csv", nrows=1, low_memory=False)
    row_sets = ["train", "idac"] if a.rows == "both" else [a.rows]

    for which in row_sets:
        print(f"\n{'=' * 78}\nНАБОР СТРОК: {which}")
        d = load_rows(which, table, a.max_rows, a.seed)
        T = d["T_K"].to_numpy(float)
        k2 = [canonicalize(str(s)) for s in d.solute_smiles]
        A2 = np.array([table[k][1] for k in k2], float)
        p2 = np.stack([table[k][0] for k in k2])
        mols = sorted(set(d.solvent_smiles.astype(str)))
        print(f"  строк {len(d)}, растворителей {len(mols)}")

        per_seed, Rs = {}, []
        for s in a.seeds:
            ck = CKPT_DIR / f"grounded_a_seed{s}.pt"
            if not ck.exists():
                print(f"  сид {s}: чекпойнта нет, пропуск")
                continue
            model, _, cfg = build_model(ck)
            _, as_solvent = learned_profiles(model, cfg, mols, tpl)
            V = {m: np.asarray(as_solvent[i], float) for i, m in enumerate(mols)}
            p1 = np.stack([V[m] for m in d.solvent_smiles.astype(str)])
            A1 = p1.sum(1)
            R = residence_map(layer, p2, p1, A2, A1, T, core, a.frac)
            w = weights_from_potential(R, a.floor_frac)
            cc = float(R[corner].mean() / max(R[core].mean(), 1e-30))
            per_seed[str(s)] = {"R": R.tolist(), "w": w.tolist(),
                                "corner_over_core": cc,
                                "R_core_mean": float(R[core].mean()),
                                "R_corner_mean": float(R[corner].mean()),
                                "w_core_mean": float(w[:-1][core[:-1]].mean()),
                                "w_corner_mean": float(w[:-1][corner[:-1]].mean())}
            Rs.append(R)
            print(f"  сид {s}: R ядро {R[core].mean():.4f}  угол {R[corner].mean():.4f}  "
                  f"угол/ядро {cc:.1f}x;  вес ядро {w[:-1][core[:-1]].mean():.3f}  "
                  f"угол {w[:-1][corner[:-1]].mean():.3f}")

        # --- нулевое плечо: случайные профили той же площади -------------------------------
        rng = np.random.default_rng(a.seed)
        A1n = np.full(len(d), float(np.mean([table[k][1] for k in k2])))
        p1n = rng.dirichlet(np.ones(n_bins), size=len(d)) * A1n[:, None]
        Rn = residence_map(layer, p2, p1n, A2, A1n, T, core, a.frac)
        wn = weights_from_potential(Rn, a.floor_frac)
        cc_n = float(Rn[corner].mean() / max(Rn[core].mean(), 1e-30))
        print(f"  НУЛЬ (случайные профили): угол/ядро {cc_n:.2f}x")

        Rm = np.stack(Rs)
        wm = np.stack([np.asarray(v["w"]) for v in per_seed.values()])
        # посидовая устойчивость: по каждому бину разброс нормированного веса, и ранговое согласие
        from scipy.stats import spearmanr
        pairs = [float(spearmanr(wm[i], wm[j]).statistic)
                 for i in range(len(wm)) for j in range(i + 1, len(wm))]
        rho_null = float(spearmanr(wm.mean(0), wn).statistic)
        w_mean = wm.mean(0)
        res["by_rows"][which] = {
            "n_rows": int(len(d)), "n_solvents": len(mols),
            "per_seed": per_seed,
            "R_seed_mean": Rm.mean(0).tolist(),
            "w_seed_mean": w_mean.tolist(),
            "w_seed_sd": wm.std(0, ddof=1).tolist() if len(wm) > 1 else None,
            "corner_over_core_per_seed": [v["corner_over_core"] for v in per_seed.values()],
            "null": {"R": Rn.tolist(), "w": wn.tolist(), "corner_over_core": cc_n},
            "spearman_between_seeds": pairs,
            "spearman_weights_vs_null": rho_null,
        }
        ccs = np.array([v["corner_over_core"] for v in per_seed.values()])
        print(f"\n  ВОРОТА, набор {which}")
        print(f"   карта не плоская:      угол/ядро {ccs.min():.1f}...{ccs.max():.1f}x  "
              f"{'ok' if ccs.min() > 1.5 else 'ПЛОСКАЯ'}")
        print(f"   отличается от нуля:    медиана {np.median(ccs):.1f}x против {cc_n:.2f}x; "
              f"ранговое согласие с нулём rho = {rho_null:+.3f}  "
              f"{'ok' if abs(rho_null) < 0.5 else 'ПОХОЖА НА НУЛЬ -- вес про сетку'}")
        if pairs:
            print(f"   устойчива по сидам:    rho между сидами "
                  f"{min(pairs):+.3f}...{max(pairs):+.3f}  "
                  f"{'ok' if min(pairs) > 0.5 else 'НЕУСТОЙЧИВ -- вес сидозависим'}")
        print(f"   вес нормирован:        mean(w) = {w_mean.mean():.6f} (обязан быть 1)")
        print(f"   сверка с выложенной картой (12.9...15.0 на наборе idac, другой стимул): "
              f"{np.median(ccs):.1f}x")

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    # вектор для T1 берётся с TRAIN-строк: он не должен выводиться на поверхности, на которой
    # арм будут читать.
    src = "train" if "train" in res["by_rows"] else row_sets[0]
    np.save(a.out / "weights_t1.npy", np.asarray(res["by_rows"][src]["w_seed_mean"], np.float64))
    print(f"\nзаписано: {a.out}\nвектор весов для T1 взят с набора {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
