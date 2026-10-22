#!/usr/bin/env python
"""Определяет ли цену ПЕРЕСЕЧЕНИЕ sigma_hb -- порога водородной связи самого замыкания.

Правила, пороги и обязательные к печати величины объявлены ДО кода в
`results/sigma_core_boundary_sweep/PRE_DECLARATION.md`.

ПОЧЕМУ ЭТО ОТДЕЛЬНЫЙ СКРИПТ. `run_sigma_displacement_geometry.py` произвёл депозит, на который
опирается заголовок. Любая правка в нём рискует сдвинуть расход ГПСЧ или путь оценивания, поэтому он
не трогается: ворота воспроизведения целы по построению.

ДВА ИСПРАВЛЕНИЯ ПРОТИВ РАЗВЁРТКИ ПО УГЛУ, оба обязательны (см. предзаявку):
  1. Согласуется МАССА, а не Хеллингер. Контролируется полная вариация 0.5*sum|p-q| -- чистая
     переложенная масса. Хеллингер отпущен и печатается. Одинаковая доля `t` не годится: у окон
     ВНУТРИ источника часть массы возвращается в свои же бины.
  2. Ширина назначения ПОСТОЯННА. Окна заданы по ИНДЕКСАМ бинов, а не сравнением float (которое
     дало бы 8/7/8/7), -- ровно 8 бинов в каждом.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_sigma_profile_residual import build_model, hellinger, learned_profiles  # noqa: E402
from run_sigma_role_injection import score_arm                                   # noqa: E402
from tgnn_solv.data.utils import canonicalize                                    # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles                           # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
TEST = ROOT / "notebooks/data/processed/test.csv"
OUT = ROOT / "results/sigma_core_boundary_sweep"

#: Начала окон по индексу |k| (шаг сетки 0.001). Ширина 4 значения |k| -> ровно 8 бинов.
LADDER = [1, 5, 9, 13, 17, 21]
WINDOW_WIDTH = 4
#: Цель по полной вариации: медиана плеча `core_to_corner` из депозита. Объявлена в предзаявке.
TARGET_TV = 20.82
#: Допуск на контролируемую величину. При превышении чтение отменяется -- это ворота, не оговорка.
TV_TOL = 0.5


def total_variation(p: np.ndarray, q: np.ndarray) -> float:
    return 0.5 * float(np.abs(p - q).sum())


def displace_to_tv(p: np.ndarray, target_tv: float, src: np.ndarray, dst: np.ndarray,
                   rng: np.random.Generator, iters: int = 80,
                   tol: float = 1e-3) -> tuple[np.ndarray, bool, float]:
    """Перенести массу из `src` в случайное распределение по `dst` до заданной ПОЛНОЙ ВАРИАЦИИ.

    Площадь сохраняется точно. Делением пополам по доле `t`, как в депозитном `displace`, но цель --
    чистая переложенная масса, а не Хеллингер. Монотонность ПВ по `t` не предполагается, а
    ПРОВЕРЯЕТСЯ: если цель вне достижимого отрезка [ПВ(0), ПВ(1)], возвращается reached=False.
    """
    area = float(p.sum())
    if area <= 0 or not np.isfinite(target_tv) or target_tv <= 0 or not src.any() or not dst.any():
        return p.copy(), False, 0.0
    w = rng.dirichlet(np.ones(int(dst.sum())))      # куда именно внутри окна

    def at(t: float) -> np.ndarray:
        q = p.copy()
        moved = t * p[src].sum()
        q[src] = p[src] * (1.0 - t)
        q[dst] = q[dst] + moved * w
        s = float(q.sum())
        return q * (area / s) if s > 0 else q

    tv_max = total_variation(p, at(1.0))
    if target_tv > tv_max:                          # окно не может принять столько массы
        q = at(1.0)
        return q, False, total_variation(p, q)
    lo, hi, best = 0.0, 1.0, None
    for _ in range(iters):
        t = 0.5 * (lo + hi)
        q = at(t)
        tv = total_variation(p, q)
        best = q
        if abs(tv - target_tv) < tol:
            return q, True, tv
        lo, hi = (t, hi) if tv < target_tv else (lo, t)
    tv = total_variation(p, best)
    return best, abs(tv - target_tv) < 10 * tol, tv


def window_mask(n_bins: int, k0: int, width: int) -> np.ndarray:
    """Окно по ИНДЕКСАМ: |k| in [k0, k0+width-1], оба знака. Ровно 2*width бинов при k0 >= 1."""
    zero = n_bins // 2
    m = np.zeros(n_bins, dtype=bool)
    for k in range(k0, k0 + width):
        if 0 <= zero - k:
            m[zero - k] = True
        if zero + k < n_bins:
            m[zero + k] = True
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ckpt-dir", type=Path, default=CKPT_DIR)
    ap.add_argument("--arm-glob", default="grounded_a_seed*.pt")
    ap.add_argument("--seeds", type=int, nargs="*", default=None)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--max-rows", type=int, default=None, help="только дымовой прогон")
    ap.add_argument("--boot-seed", type=int, default=0)
    ap.add_argument("--target-tv", type=float, default=TARGET_TV)
    ap.add_argument("--sigma-hb-score", type=float, default=None,
                    help="оценивать при ДРУГОМ sigma_hb. Инъекции строятся по ИСХОДНОМУ из "
                         "конфига, поэтому стимул побитово тот же и меняется только оператор "
                         "оценивания. Веса обучены при исходном -- асимметрия силы объявлена "
                         "в results/sigma_hb_shift/PRE_DECLARATION.md")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    device = torch.device(a.device)
    test = pd.read_csv(TEST, low_memory=False)
    # НЕ ln_x2.notna(): вспомогательные строки несут ln_x2 = 0.0, не NaN (см. results/row_filter_audit).
    if "has_solubility" in test.columns:
        df = test[test["has_solubility"].astype(bool)].reset_index(drop=True)
    else:
        df = test[test["ln_x2"].notna()].reset_index(drop=True)
    assert not (df["ln_x2"] == 0.0).all(), "отобраны строки-заполнители, а не измерения"
    if a.max_rows:
        df = df.head(a.max_rows).reset_index(drop=True)
        print(f"ДЫМОВОЙ ПРОГОН на {len(df)} строках -- числа не являются результатом")
    template = pd.read_csv(TEST, nrows=1, low_memory=False)

    cks = sorted(a.ckpt_dir.glob(a.arm_glob))
    if not cks:
        print(f"нет чекпойнтов в {a.ckpt_dir}/{a.arm_glob}")
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    arm_names = [f"win_k{k0}" for k0 in LADDER]
    frames, geo = [], []

    for ck in cks:
        model, ckd, cfg = build_model(ck)
        seed = int(ckd.get("seed", -1))
        if a.seeds and seed not in a.seeds:
            continue
        model.to(device)
        n_bins = int(cfg.cosmo_sac_n_bins)
        step = (cfg.cosmo_sac_sigma_max - cfg.cosmo_sac_sigma_min) / (n_bins - 1)
        k_hb = int(np.floor(float(cfg.cosmo_sac_sigma_hb) / step))
        core = window_mask(n_bins, 0, k_hb + 1)
        # Сдвиг порога ЗАМЫКАНИЯ применяется ПОСЛЕ вычисления core: источник и окна остаются на
        # исходном sigma_hb, поэтому инъекции не меняются и сравнение изолирует оператор.
        sigma_hb_used = float(cfg.cosmo_sac_sigma_hb)
        if a.sigma_hb_score is not None:
            layer = getattr(model.sle_solver, "cosmo_sac_layer", None)
            if layer is None:
                raise SystemExit("нет cosmo_sac_layer -- сдвигать sigma_hb негде")
            layer.sigma_hb = float(a.sigma_hb_score)
            sigma_hb_used = float(a.sigma_hb_score)
            print(f"  sigma_hb при ОЦЕНИВАНИИ = {sigma_hb_used} (источник и окна -- по "
                  f"{float(cfg.cosmo_sac_sigma_hb)})", flush=True)
        table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
        subs = sorted({s for s in df["solvent_smiles"].astype(str) if canonicalize(s) in table})
        print(f"\nсид {seed}: {len(subs)} подставляемых растворителей, ядро {int(core.sum())} бинов, "
              f"|k| <= {k_hb}", flush=True)
        _, as_solvent = learned_profiles(model, cfg, subs, template)

        rng = np.random.default_rng(a.boot_seed + seed)
        inj: dict[str, dict] = {nm: {} for nm in arm_names + ["identity_solvent"]}
        seed_geo = []
        for i, s in enumerate(subs):
            key = canonicalize(s)
            lv = np.asarray(as_solvent[i], float)
            inj["identity_solvent"][key] = (lv, float(lv.sum()))
            # ГПСЧ расходуется окнами В ПОРЯДКЕ LADDER, по одному вызову dirichlet на окно.
            for k0 in LADDER:
                dst = window_mask(n_bins, k0, WINDOW_WIDTH)
                q, hit, tv = displace_to_tv(lv, a.target_tv, core, dst, rng)
                inj[f"win_k{k0}"][key] = (q, float(q.sum()))
                seed_geo.append({"seed": seed, "smiles": s, "window_k0": k0,
                                 "n_dst_bins": int(dst.sum()),
                                 "inside_core": bool(k0 + WINDOW_WIDTH - 1 <= k_hb),
                                 "tv_target": a.target_tv, "tv_achieved": tv, "reached": bool(hit),
                                 "hellinger_floating": hellinger(lv, q),
                                 "profile_area": float(lv.sum()),
                                 "sigma_hb_scoring": sigma_hb_used,
                                 "sigma_hb_construction": float(cfg.cosmo_sac_sigma_hb),
                                 "k_hb_construction": k_hb})
        seed_rows = []
        for arm in ["control", "identity_solvent"] + arm_names:
            r = score_arm(model, cfg, df, arm, table, inj, n_bins, a.batch_size, device)
            r["arm"], r["seed"] = arm, seed
            seed_rows.append(r)
            print(f"  {arm:14s} MAE {r.abs_err.mean():.4f}", flush=True)
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

    # --- ОБЯЗАТЕЛЬНЫЕ К ПЕЧАТИ ВЕЛИЧИНЫ (пункты 1-4, 6, 7 предзаявки) ---
    print(f"\n{'окно':>8}{'бинов':>7}{'внутри':>8}{'ПВ медиана':>12}{'ПВ разброс':>12}"
          f"{'H (отпущен)':>13}{'достиж.':>9}")
    gate_ok = True
    for k0, sub in g.groupby("window_k0"):
        spread = float(sub.tv_achieved.max() - sub.tv_achieved.min())
        gate_ok &= spread <= TV_TOL
        print(f"{k0:>8}{int(sub.n_dst_bins.iloc[0]):>7}{str(bool(sub.inside_core.iloc[0])):>8}"
              f"{sub.tv_achieved.median():>12.3f}{spread:>12.3f}"
              f"{sub.hellinger_floating.median():>13.4f}{100*sub.reached.mean():>8.0f}%")
    nulls = per_row[per_row.arm == "identity_solvent"].abs_err.mean() - \
        per_row[per_row.arm == "control"].abs_err.mean()
    print(f"\nнулевое плечо identity (обязано быть нулём): {nulls:+.3e}")
    print(f"ВОРОТА на контролируемую величину (разброс ПВ <= {TV_TOL}): "
          f"{'ПРОЙДЕНЫ' if gate_ok else 'ПРОВАЛЕНЫ -- чтение отменяется'}")
    bins_const = g.groupby("window_k0").n_dst_bins.nunique().eq(1).all() and \
        g.n_dst_bins.nunique() == 1
    print(f"ширина назначения постоянна во всех окнах: {bool(bins_const)}")

    (a.out / "run_meta.json").write_text(json.dumps({
        "ladder_k0": LADDER, "window_width_k": WINDOW_WIDTH,
        "target_tv": a.target_tv, "tv_tolerance": TV_TOL,
        "sigma_hb_scoring": float(a.sigma_hb_score) if a.sigma_hb_score is not None else None,
        "tv_gate_passed": bool(gate_ok), "dst_bins_constant": bool(bins_const),
        "identity_null": float(nulls), "boot_seed": a.boot_seed,
        "n_rows_per_arm": int(len(per_row[per_row.arm == 'control']) // max(1, per_row.seed.nunique())),
        "seeds": sorted(per_row.seed.unique().tolist()),
    }, indent=2, ensure_ascii=False))
    print(f"\nзаписано: {a.out}")
    return 0 if gate_ok else 3


if __name__ == "__main__":
    sys.exit(main())
