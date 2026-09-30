#!/usr/bin/env python
"""Убийца для вывода «штраф за подстановку -- функционал ВЕЛИЧИНЫ, а не направления».

ЧТО ОН ПРОВЕРЯЕТ. results/sigma_role_injection установил, что смещение ролевого размера в
СЛУЧАЙНОМ направлении стоит столько же, сколько в ролевом (r - m = +0.0270 [-0.0442, +0.0963]).
Отсюда был сделан вывод, что цена определяется размером смещения. У вывода два незакрытых места,
и оба названы синтезом разбора 2026-09-30 ДО того, как что-либо написано:

  (1) РАЗМЕР НЕ ТОТ. Ролевое смещение по Хеллингеру имеет медиану 0.82, а оракульное -- 2.81.
      Ноль на ролевом масштабе ничего не говорит о масштабе, на котором измерен опубликованный
      штраф 0.4081. Вопрос: дотягивает ли случайное смещение ОРАКУЛЬНОГО размера до 0.408?
  (2) МЕТРИКА СЛЕПА К РАСПОЛОЖЕНИЮ. Хеллингер безразличен к тому, КУДА уехала масса, а
      results/substitution_mechanism записал, что при согласованной норме L2 смещение в угол
      профиля покупает в 30-60 раз больше, чем в центр. Если так, «согласовано по размеру»
      согласовало не тот функционал, и направление всё-таки выделено.

ПОЧЕМУ ПЛЕЧИ НЕ ТАКИЕ, КАК БЫЛИ ЗАКАЗАНЫ. Заказывалось «смещение, ограниченное углом
(|sigma| >= 0.016), при согласованном H». ИЗМЕРЕНО, что это геометрически невозможно: у
выученного профиля в углу лежит медиана 0.1 A^2, и перекладыванием массы ВНУТРИ угла достижима
медиана H = 0.16; цель H=1.0 берут 16% растворителей, H=3.0 -- ноль. Двигать там нечего.
Ядро (|sigma| <= 0.0084) несёт 133.3 A^2 и достаёт до H = 8.17.

Поэтому контраст переставлен с «откуда» на «КУДА»: масса в обоих плечах берётся из ядра, где она
есть, и уезжает либо обратно в ядро, либо в угол. Это и есть вопрос о расположении, заданный так,
чтобы на него можно было ответить.

ПЛЕЧИ (все -- те же веса, те же строки, одна маска VT-2005, впрыск в слот растворителя)

  control                   без впрыска
  identity_solvent          нулевое плечо: собственный профиль обратно, обязан дать ровно 0
  oracle_solvent            VT-2005, якорь
  random_oracle_size        случайное НЕограниченное смещение на СОБСТВЕННОМ оракульном H
                            молекулы. Отвечает на (1).
  core_to_core              масса берётся из ядра и раскладывается случайно ПО ЯДРУ, тот же H
  core_to_corner            масса берётся из ядра и уезжает в УГОЛ, тот же H
                            Пара core_to_core / core_to_corner отвечает на (2).

ЧТО ПЕЧАТАЕТСЯ ОБЯЗАТЕЛЬНО. Достигнутое H по каждой молекуле и число молекул, где цель НЕ взята.
Без этого плечо не является тестом: тихий недолёт неотличим от отсутствия эффекта.

ЧТЕНИЕ, ОБЪЯВЛЕННОЕ ДО ЧИСЕЛ
  * random_oracle_size >= 0.408  ->  величина объясняет весь опубликованный штраф; вывод о
    функционале величины становится заголовком в единицах опубликованного числа.
  * random_oracle_size сильно ниже 0.408 (скажем <= 0.15)  ->  конкретное направление VT-2005
    покупает большую часть штрафа, вывод переворачивается.
  * core_to_corner заметно дороже core_to_core при равном H  ->  ноль прошлого прибора был
    артефактом метрики Хеллингера, направление выделено, и заявление о функционале величины
    снимается.
  * core_to_corner ~ core_to_core  ->  расположение не выделено и на оракульном масштабе тоже.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_sigma_displacement_geometry.py
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

from run_sigma_profile_residual import build_model, hellinger, learned_profiles  # noqa: E402
from run_sigma_role_injection import cluster_bootstrap, score_arm                # noqa: E402
from tgnn_solv.data.utils import canonicalize                                    # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles                           # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
TEST = ROOT / "notebooks/data/processed/test.csv"
OUT = ROOT / "results/sigma_displacement_geometry"

ARMS = ["control", "identity_solvent", "random_oracle_size",
        "core_to_core", "core_to_corner", "oracle_solvent"]


def displace(p: np.ndarray, target_h: float, src: np.ndarray, dst: np.ndarray,
             rng: np.random.Generator, iters: int = 80, tol: float = 1e-3) -> tuple[np.ndarray, bool]:
    """Перенести массу из бинов `src` в случайное распределение по `dst` до расстояния target_h.

    Площадь сохраняется точно. Доля переносимой массы ищется делением пополам: H монотонна по
    ней от 0 до переноса всей массы src, так что корень единственный, если цель внутри отрезка.
    Возвращает (профиль, достигнута_ли_цель) -- второе печатается, а не замалчивается.
    """
    area = float(p.sum())
    if area <= 0 or not np.isfinite(target_h) or target_h <= 0 or not src.any() or not dst.any():
        return p.copy(), False
    w = rng.dirichlet(np.ones(int(dst.sum())))          # куда именно внутри dst
    lo, hi, best = 0.0, 1.0, None
    for _ in range(iters):
        t = 0.5 * (lo + hi)
        q = p.copy()
        moved = t * p[src].sum()
        q[src] = p[src] * (1.0 - t)
        q[dst] = q[dst] + moved * w
        s = float(q.sum())
        if s > 0:
            q = q * (area / s)
        h = hellinger(p, q)
        best = q
        if abs(h - target_h) < tol:
            return q, True
        lo, hi = (t, hi) if h < target_h else (lo, t)
    return best, abs(hellinger(p, best) - target_h) < 10 * tol


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ckpt-dir", type=Path, default=CKPT_DIR)
    ap.add_argument("--arm-glob", default="grounded_a_seed*.pt")
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--max-rows", type=int, default=None, help="только дымовой прогон")
    ap.add_argument("--draws", type=int, default=4000)
    ap.add_argument("--boot-seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    device = torch.device(a.device)
    test = pd.read_csv(TEST, low_memory=False)
    df = test[test["ln_x2"].notna()].reset_index(drop=True)
    if a.max_rows:
        df = df.head(a.max_rows).reset_index(drop=True)
        print(f"ДЫМОВОЙ ПРОГОН на {len(df)} строках -- числа не результат")
    template = pd.read_csv(TEST, nrows=1, low_memory=False)

    # ВОЗОБНОВЛЯЕМОСТЬ. Прогон 2026-09-30 убили через минуту после старта из-за перегруза
    # системы, и он унёс всё. Каждый сид теперь ложится на диск сразу, а при повторном запуске
    # уже посчитанные сиды читаются и пропускаются.
    a.out.mkdir(parents=True, exist_ok=True)
    frames, geo = [], []
    done: set[int] = set()
    for f in sorted(a.out.glob("part_seed*.csv")):
        part = pd.read_csv(f)
        frames.append(part)
        done.add(int(part["seed"].iloc[0]))
        gf = a.out / f.name.replace("part_seed", "geom_seed")
        if gf.exists():
            geo.append(pd.read_csv(gf))
    if done:
        print(f"уже посчитаны и пропускаются сиды: {sorted(done)}")

    for ck in sorted(a.ckpt_dir.glob(a.arm_glob)):
        model, ckd, cfg = build_model(ck)
        seed = int(ckd.get("seed", -1))
        if a.seeds and seed not in a.seeds:
            continue
        if seed in done:
            continue
        model.to(device)
        n_bins = int(cfg.cosmo_sac_n_bins)
        grid = np.linspace(cfg.cosmo_sac_sigma_min, cfg.cosmo_sac_sigma_max, n_bins)
        core = np.abs(grid) <= float(cfg.cosmo_sac_sigma_hb)
        corner = np.abs(grid) >= 0.016
        oracle_table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
        subs = sorted({s for s in df["solvent_smiles"].astype(str)
                       if canonicalize(s) in oracle_table})
        print(f"\nсид {seed}: {len(subs)} подставляемых растворителей", flush=True)
        _, as_solvent = learned_profiles(model, cfg, subs, template)
        rng = np.random.default_rng(a.boot_seed + seed)
        seed_geo: list[dict] = []
        inj: dict[str, dict] = {k: {} for k in ARMS if k not in ("control", "oracle_solvent")}
        for i, s in enumerate(subs):
            key = canonicalize(s)
            lv = np.asarray(as_solvent[i], float)
            ref = np.asarray(oracle_table[key][0], float)
            h_or = hellinger(lv, ref)
            inj["identity_solvent"][key] = (lv, float(lv.sum()))
            allb = np.ones(n_bins, dtype=bool)
            for arm, src, dst in (("random_oracle_size", allb, allb),
                                  ("core_to_core", core, core),
                                  ("core_to_corner", core, corner)):
                q, hit = displace(lv, h_or, src, dst, rng)
                inj[arm][key] = (q, float(q.sum()))
                seed_geo.append({"seed": seed, "smiles": s, "arm": arm, "H_target": h_or,
                                 "H_achieved": hellinger(lv, q), "reached": bool(hit)})
        seed_rows = []
        for arm in ARMS:
            r = score_arm(model, cfg, df, arm, oracle_table, inj, n_bins, a.batch_size, device)
            r["arm"], r["seed"] = arm, seed
            seed_rows.append(r)
            print(f"  {arm:22s} MAE {r.abs_err.mean():.4f}", flush=True)
        part = pd.concat(seed_rows, ignore_index=True)
        part.to_csv(a.out / f"part_seed{seed}.csv", index=False)
        pd.DataFrame(seed_geo).to_csv(a.out / f"geom_seed{seed}.csv", index=False)
        frames.append(part)
        geo.append(pd.DataFrame(seed_geo))
        print(f"  сид {seed} записан на диск", flush=True)

    per_row = pd.concat(frames, ignore_index=True)
    g = pd.concat(geo, ignore_index=True)
    per_row.to_csv(a.out / "per_row.csv", index=False)
    g.to_csv(a.out / "geometry.csv", index=False)

    print("\nГЕОМЕТРИЯ СМЕЩЕНИЯ -- достигнуто ли целевое расстояние")
    print(f"{'плечо':<22}{'цель H (мед.)':>14}{'достигнуто':>12}{'взято цели':>12}")
    for arm, sub in g.groupby("arm"):
        print(f"{arm:<22}{sub.H_target.median():>14.2f}{sub.H_achieved.median():>12.2f}"
              f"{100 * sub.reached.mean():>11.0f}%")

    per_seed = per_row.groupby(["seed", "arm"]).abs_err.mean().unstack()
    print(f"\n{'плечо':<22}{'MAE':>9}{'штраф':>9}{'CI95 (кластер=растворитель)':>32}")
    summary = {"arms": ARMS, "seeds": sorted(per_seed.index.tolist()),
               "cluster_unit": "solvent_smiles", "bootstrap_draws": a.draws,
               "geometry": {arm: {"H_target_median": float(s.H_target.median()),
                                  "H_achieved_median": float(s.H_achieved.median()),
                                  "reached_fraction": float(s.reached.mean())}
                            for arm, s in g.groupby("arm")},
               "penalty_vs_control": {}}
    for arm in ARMS[1:]:
        pt, lo, hi = cluster_bootstrap(per_row, arm, a.draws, a.boot_seed)
        summary["penalty_vs_control"][arm] = {
            "point": pt, "ci95": [lo, hi],
            "per_seed": (per_seed[arm] - per_seed["control"]).round(6).to_dict()}
        print(f"{arm:<22}{per_seed[arm].mean():>9.4f}{pt:>9.4f}{f'[{lo:+.4f}, {hi:+.4f}]':>32}")
    print(f"{'control':<22}{per_seed['control'].mean():>9.4f}")

    print(f"\n{'парный контраст':<26}{'оценка':>9}{'CI95':>32}")
    for nm, arm, base in (("угол минус ядро (РЕШАЮЩИЙ)", "core_to_corner", "core_to_core"),
                          ("оракул минус случайное", "oracle_solvent", "random_oracle_size")):
        pt, lo, hi = cluster_bootstrap(per_row, arm, a.draws, a.boot_seed, base=base)
        excl = (lo > 0) or (hi < 0)
        summary["paired_contrasts"] = summary.get("paired_contrasts", {})
        summary["paired_contrasts"][f"{arm}__minus__{base}"] = {
            "point": pt, "ci95": [lo, hi], "ci_excludes_zero": bool(excl)}
        print(f"{nm:<26}{pt:>+9.4f}{f'[{lo:+.4f}, {hi:+.4f}]':>32}"
              f"  {'исключает 0' if excl else 'СОДЕРЖИТ 0'}")

    (a.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    print(f"\nзаписано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
