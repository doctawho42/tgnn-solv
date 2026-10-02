#!/usr/bin/env python
"""P0+P1: карта чувствительности замыкания по бинам и сверка с давлением супервизии.

ВОРОТА ДЛЯ ЭКСПЕРИМЕНТА E1 (взвешенный лосс). План outreach/ПЛАН_физичная_модель.md ставит первым
платным экспериментом перевзвешивание sigma-супервизии чувствительностью замыкания: сейчас лосс
тратит одинаковое усилие на бин, который ничего не стоит, и на бин, который стоит шестикратно
(results/sigma_displacement_geometry: при равном расстоянии Хеллингера ядро стоит +0.217, угол
+1.288). Прежде чем тратить GPU, надо проверить две вещи, и обе на ноутбуке.

P0 -- ЕСТЬ ЛИ ЧТО ПЕРЕВЗВЕШИВАТЬ. Чувствительность d(ln gamma)/d(масса в бине), взятая автоградом
через сам слой на реальных парах. Если она почти плоская по бинам, перевзвешивать нечего и E1
отменяется.

  НУЛЕВОЕ ПЛЕЧО: та же карта на СЛУЧАЙНЫХ профилях той же площади. Если карта на реальных
  профилях неотличима от случайной, она отражает геометрию ядра обмена, а не химию корпуса, и
  «взвесить по чувствительности» означало бы «взвесить по форме сетки».

  ВСТРОЕННАЯ СВЕРКА: карта должна предсказывать уже измеренное. Отношение чувствительности в
  угловом окне к ядерному обязано воспроизводить порядок шестикратного контраста из
  results/sigma_displacement_geometry. Если не воспроизводит -- карта считает не то.

P1 -- РАСХОДИТСЯ ЛИ С НЕЙ СУПЕРВИЗИЯ. Куда сейчас давит градиент sigma-лосса по бинам.

ПОПРАВКА К ЗАМЫСЛУ, СДЕЛАННАЯ ПО КОДУ. Форменный член -- это 1-D Wasserstein (EMD) по упорядоченной
сетке, sum|cumsum(pred) - cumsum(target)| (loss.py:94-96), и он НЕ безразличен к расположению: из-за
кумулятивной суммы перенос массы на k бинов стоит пропорционально k. Первая формулировка задачи
(«обе части лосса безразличны к тому, где лежит масса») была неверна и исправлена здесь.

Но «далеко по сетке» и «дорого для замыкания» -- разные вещи. EMD взвешивает РАССТОЯНИЕ переноса,
замыкание взвешивает КОНЕЧНОЕ ПОЛОЖЕНИЕ: перенос на пять бинов внутри ядра и такой же перенос,
кончающийся в водородносвязанном углу, для EMD равны, а по цене различаются. P1 меряет именно это
расхождение.

Если градиент супервизии и так сосредоточен в дорогих бинах, перевзвешивание ничего не даст и E1
отменяется вторыми воротами.

НА КАКИХ ПРОФИЛЯХ СЧИТАТЬ, И ЭТО НЕ ДЕТАЛЬ. Первая версия брала градиент на ЭТАЛОННЫХ профилях и
выдала максимум 6.9e+06 при размахе 1e8 -- численный взрыв, а не карта. Причина: у эталона 57%
бинов РОВНО нулевые, а сегментная Gamma там упирается в 1/(den + eps), и производная в такой точке
бессмысленна. Это та же ошибка метрики, что в первой диагностике сходимости, где максимум по всем
бинам показывал невязку ~1.0 после 20000 итераций.

Карта считается на ВЫУЧЕННЫХ профилях, и это не заплатка, а правильная поверхность: лосс действует
именно на них, и они строго положительны во всех бинах (софтмакс), так что производная существует.

ПРОВЕРКА КОНЕЧНОЙ РАЗНОСТЬЮ обязательна. Градиент -- локальная величина, а перевзвешивать лосс мы
собираемся под КОНЕЧНЫЕ смещения. Карта обязана предсказывать отношение цены угол/ядро, измеренное
в results/sigma_displacement_geometry на реальных переносах массы. Если не предсказывает -- она
считает не то, что нужно.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_closure_sensitivity_map.py
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
RECORDS = ROOT / "results/published_idac_check/scored_records.csv"
OUT = ROOT / "results/closure_sensitivity_map"


def sensitivity(layer, p2, A2, p1, A1, T, batch: int = 512) -> np.ndarray:
    """d(ln gamma_2^inf)/d(p_solvent[bin]), (n_rows, n_bins). Автоград через сам слой."""
    out = []
    for i in range(0, len(T), batch):
        sl = slice(i, i + batch)
        q1 = torch.tensor(p1[sl], dtype=torch.float, requires_grad=True)
        g = layer.ln_gamma_inf(torch.tensor(p2[sl], dtype=torch.float), q1,
                               torch.tensor(A2[sl], dtype=torch.float),
                               torch.tensor(A1[sl], dtype=torch.float),
                               None, None, torch.tensor(T[sl], dtype=torch.float))
        g.sum().backward()
        out.append(q1.grad.detach().numpy().copy())
    return np.concatenate(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-rows", type=int, default=3000)
    ap.add_argument("--ckpt", type=Path,
                    default=ROOT / "checkpoints/e5_leakfree/grounded_a_seed42.pt")
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
    d = pd.read_csv(RECORDS)
    k2 = [canonicalize(str(s)) for s in d.solute_smiles]
    k1 = [canonicalize(str(s)) for s in d.solvent_smiles]
    ok = np.array([(x in table) and (y in table) for x, y in zip(k2, k1)])
    d = d[ok].reset_index(drop=True).head(a.max_rows)
    k2 = [x for x, o in zip(k2, ok) if o][:len(d)]
    k1 = [y for y, o in zip(k1, ok) if o][:len(d)]
    T = d["T_K"].to_numpy(float)
    A2 = np.array([table[k][1] for k in k2], float)
    p2 = np.stack([table[k][0] for k in k2])

    # ВЫУЧЕННЫЕ профили растворителя -- та поверхность, на которой действует лосс.
    model, ckd, cfg = build_model(a.ckpt)
    tpl = pd.read_csv(ROOT / "notebooks/data/processed/test.csv", nrows=1, low_memory=False)
    mols = sorted(set(d.solvent_smiles.astype(str)))
    _, as_solvent = learned_profiles(model, cfg, mols, tpl)
    V = {s: np.asarray(as_solvent[i], float) for i, s in enumerate(mols)}
    p1 = np.stack([V[s] for s in d.solvent_smiles.astype(str)])
    A1 = p1.sum(1)
    print(f"строк {len(d)}, бинов {n_bins}; ядро {core.sum()} бинов, угол {corner.sum()}")
    print(f"минимальная масса бина у выученного профиля: {p1.min():.3e} "
          f"(у эталона {np.stack([table[k][0] for k in k1]).min():.3e} -- там производная не живёт)")

    # --- P0, реальные профили --------------------------------------------------------------
    S = sensitivity(layer, p2, A2, p1, A1, T)
    # --- P0, нулевое плечо: случайные профили той же площади --------------------------------
    rng = np.random.default_rng(a.seed)
    p1_rand = rng.dirichlet(np.ones(n_bins), size=len(d)) * A1[:, None]
    S_rand = sensitivity(layer, p2, A2, p1_rand, A1, T)

    def profile(S_, name):
        m = np.abs(S_).mean(0)
        rng_ratio = float(m.max() / max(m.min(), 1e-30))
        cc = float(m[corner].mean() / max(m[core].mean(), 1e-30))
        print(f"\n{name}")
        print(f"  |d lnγ / d p| по бинам: мин {m.min():.3e}  медиана {np.median(m):.3e}  "
              f"макс {m.max():.3e}")
        print(f"  размах макс/мин: {rng_ratio:.1f}x;  угол/ядро: {cc:.2f}x")
        return {"per_bin_abs_mean": m.tolist(), "range_ratio": rng_ratio,
                "corner_over_core": cc}

    res = {"n_rows": int(len(d)), "n_bins": n_bins,
           "real": profile(S, "P0 ВЫУЧЕННЫЕ профили"),
           "random_null": profile(S_rand, "P0 НУЛЕВОЕ ПЛЕЧО (случайные профили)")}

    r_real, r_rand = res["real"]["corner_over_core"], res["random_null"]["corner_over_core"]
    print("\nВОРОТА P0")
    print(f"  карта не плоская:        угол/ядро {r_real:.2f}x  "
          f"{'ok' if r_real > 1.5 else 'ПЛОСКАЯ -- E1 отменяется'}")
    print(f"  отличается от случайной: {r_real:.2f}x против {r_rand:.2f}x  "
          f"{'ok' if abs(r_real - r_rand) > 0.3 * max(r_real, 1e-9) else 'НЕ ОТЛИЧАЕТСЯ -- карта про сетку, не про химию'}")
    print("  сверка с измеренным: contrasts из results/sigma_displacement_geometry дали "
          "угол/ядро ~5.9x по ЦЕНЕ")

    # --- ПРОВЕРКА КОНЕЧНОЙ РАЗНОСТЬЮ -------------------------------------------------------
    # Переносим одну и ту же долю массы из ядра в ядро и из ядра в угол и смотрим, предсказывает
    # ли градиентная карта отношение цен, измеренное на реальных переносах.
    frac = 0.05
    rngf = np.random.default_rng(a.seed + 1)
    def move(src, dst):
        q = p1.copy()
        moved = frac * q[:, src].sum(1, keepdims=True)
        q[:, src] *= (1.0 - frac)
        w = rngf.dirichlet(np.ones(int(dst.sum())), size=len(q))
        q[:, dst] += moved * w
        return q * (A1[:, None] / q.sum(1, keepdims=True))
    with torch.no_grad():
        base = layer.ln_gamma_inf(torch.tensor(p2, dtype=torch.float),
                                  torch.tensor(p1, dtype=torch.float),
                                  torch.tensor(A2, dtype=torch.float),
                                  torch.tensor(A1, dtype=torch.float), None, None,
                                  torch.tensor(T, dtype=torch.float)).numpy()
        fd = {}
        for nm, dst in (("ядро->ядро", core), ("ядро->угол", corner)):
            q = move(core, dst)
            g = layer.ln_gamma_inf(torch.tensor(p2, dtype=torch.float),
                                   torch.tensor(q, dtype=torch.float),
                                   torch.tensor(A2, dtype=torch.float),
                                   torch.tensor(A1, dtype=torch.float), None, None,
                                   torch.tensor(T, dtype=torch.float)).numpy()
            fd[nm] = float(np.abs(g - base).mean())
    ratio_fd = fd["ядро->угол"] / max(fd["ядро->ядро"], 1e-30)
    res["finite_difference"] = {"fraction_moved": frac, **fd, "corner_over_core": ratio_fd}
    print("\nПРОВЕРКА КОНЕЧНОЙ РАЗНОСТЬЮ (перенос 5% массы ядра)")
    print(f"  ядро->ядро  средний |d lnγ| = {fd['ядро->ядро']:.4f}")
    print(f"  ядро->угол  средний |d lnγ| = {fd['ядро->угол']:.4f}")
    print(f"  отношение угол/ядро: {ratio_fd:.2f}x  против {r_real:.2f}x по градиентной карте")

    # --- P1: куда давит градиент супервизии -------------------------------------------------
    # d(EMD)/d p_i = sum_{k>=i} sign(cumsum(pred)_k - cumsum(target)_k) -- замкнутая форма.
    tgt = np.stack([table[canonicalize(str(s))][0] for s in d.solvent_smiles.astype(str)])
    ps = p1 / p1.sum(1, keepdims=True)
    ts = tgt / np.maximum(tgt.sum(1, keepdims=True), 1e-30)
    sgn = np.sign(np.cumsum(ps, 1) - np.cumsum(ts, 1))
    g_emd = np.abs(sgn[:, ::-1].cumsum(1)[:, ::-1])          # |сумма знаков от i до конца|
    sup = g_emd.mean(0)
    sens = np.abs(S).mean(0)
    sup_n, sens_n = sup / sup.sum(), sens / sens.sum()
    from scipy.stats import spearmanr
    rho = float(spearmanr(sup, sens).statistic)
    # доля давления супервизии в дешёвых бинах против доли в дорогих
    cheap = sens < np.median(sens)
    res["P1"] = {
        "spearman_supervision_vs_sensitivity": rho,
        "supervision_share_in_cheap_half": float(sup_n[cheap].sum()),
        "sensitivity_share_in_cheap_half": float(sens_n[cheap].sum()),
        "supervision_share_in_corner": float(sup_n[corner].sum()),
        "sensitivity_share_in_corner": float(sens_n[corner].sum()),
    }
    print("\nP1 -- ГДЕ ДАВИТ СУПЕРВИЗИЯ ПРОТИВ ТОГО, ГДЕ ДОРОГО")
    print(f"  Спирмен(давление супервизии, чувствительность) = {rho:+.3f}")
    print(f"  доля давления в ДЕШЁВОЙ половине бинов: {100 * sup_n[cheap].sum():.1f}%  "
          f"(доля чувствительности там же {100 * sens_n[cheap].sum():.1f}%)")
    print(f"  доля давления в УГЛУ:                   {100 * sup_n[corner].sum():.1f}%  "
          f"(доля чувствительности {100 * sens_n[corner].sum():.1f}%)")
    mis = sup_n[cheap].sum() - sens_n[cheap].sum()
    print(f"\nВОРОТА P1: расхождение {100 * mis:+.1f} процентных пункта  "
          f"{'ok -- есть что перевзвешивать' if abs(mis) > 0.10 else 'СОВПАДАЮТ -- E1 отменяется'}")

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    np.save(a.out / "sensitivity_real.npy", S.astype(np.float32))
    print(f"\nзаписано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
