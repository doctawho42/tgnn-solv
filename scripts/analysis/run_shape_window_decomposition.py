#!/usr/bin/env python
"""ГДЕ в форме профиля сидит дефект AAD -- в HB-окнах или в ядре?

ЗАЧЕМ, И ПОЧЕМУ ЭТО РЕШАЕТ ВОПРОС ОБ УЖЕ ПОСТАВЛЕННОМ ПЛЕЧЕ. Разложение формы и площади
(results/shape_vs_area) показало, что ФОРМА несёт 68.3% адресуемого разрыва: подстановка
эталонной формы при выученной площади двигает AAD с 1.7511 до 1.0780, парно положительно 5/5.
Но «форма» -- это 51 бин, и вмешательство plеча grounded_a_shapefloor глобальное: пол стоит на
СУММАРНОМ члене формы. Если дефект, который двигает AAD, сидит в HB-углу, то глобальный пол
может остановиться ДО того, как угол исправлен -- угол несёт меньше процента массы, и в
суммарный EMD он входит с этим же весом. Тогда плечо нацелено не туда, и узнать это надо до
траты квоты, а не после.

Основание подозревать именно угол: остаток выученного профиля обогащён в донорном окне в
2.4-4.2 раза (results/sigma_profile_residual), выученная масса в углу превышает эталонную в
2.9 раза, а эталон ровно нулевой в 95.6% угловых бинов.

ЧТО МЕРИТСЯ. Подстановка эталонной формы ТОЛЬКО В ОДНОМ ОКНЕ, площадь держится выученной:
  донорное окно      sigma <= -sigma_hb
  ядро               |sigma| < sigma_hb
  акцепторное окно   sigma >= +sigma_hb
  все бины           = плечо C разложения, потолок подстановки формы

НУЛЬ ПО РАСПОЛОЖЕНИЮ ОБЯЗАТЕЛЕН: подстановка в СЛУЧАЙНОМ наборе бинов того же размера, что у
проверяемого окна. Без него «донорное окно объясняет столько» не отличается от «подстановка
любых k бинов объясняет столько», а этот проект уже ловил себя на такой подмене.

ОГОВОРКА УСТРОЙСТВА, которую нельзя спрятать: заменить массу в окне и сохранить сумму нельзя
одновременно. Форма перенормируется на единицу ПОСЛЕ подстановки, поэтому бины ВНЕ окна
меняются на общий множитель. Это неизбежно при любой оконной подстановке и означает, что
«вклад окна» измеряется вместе с этим перемасштабированием -- именно поэтому нуль по
расположению и нужен: он несёт тот же артефакт.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_shape_window_decomposition.py
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

from run_shape_vs_area_decomposition import GATE_TOL, aad, score  # noqa: E402
from run_sigma_profile_residual import (  # noqa: E402
    PROFILES, TEST, build_model, learned_profiles,
)
from tgnn_solv.config import TGNNSolvConfig  # noqa: E402
from tgnn_solv.data.utils import canonicalize  # noqa: E402
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles  # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
RECORDS = ROOT / "results/published_idac_check/scored_records.csv"
OUT_DIR = ROOT / "results/shape_window_decomposition"


def substitute(learned_shape: np.ndarray, ref_shape: np.ndarray,
               window: np.ndarray) -> np.ndarray:
    """Эталонная форма в бинах ``window``, выученная вне; результат нормирован на единицу."""
    out = learned_shape.copy()
    out[:, window] = ref_shape[:, window]
    return out / np.clip(out.sum(-1, keepdims=True), 1e-30, None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--records", type=Path, default=RECORDS)
    ap.add_argument("--n-random", type=int, default=5,
                    help="сколько случайных наборов бинов на каждое окно (нуль по расположению)")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    a = ap.parse_args()

    cfg0 = TGNNSolvConfig(activity_model="cosmo_sac")
    n_bins = int(cfg0.cosmo_sac_n_bins)
    grid = np.linspace(cfg0.cosmo_sac_sigma_min, cfg0.cosmo_sac_sigma_max, n_bins)
    s_hb = float(cfg0.cosmo_sac_sigma_hb)
    windows = {
        "донорное окно": grid <= -s_hb,
        "ядро": np.abs(grid) < s_hb,
        "акцепторное окно": grid >= s_hb,
        "все бины (потолок)": np.ones(n_bins, bool),
    }
    print("окна: " + ", ".join(f"{k} {int(v.sum())} бинов" for k, v in windows.items()))

    layer = CosmoSacLayer()
    layer.eval()
    table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
    d = pd.read_csv(a.records, low_memory=False)
    k2 = [canonicalize(str(s)) for s in d.solute_smiles]
    k1 = [canonicalize(str(s)) for s in d.solvent_smiles]
    ref_p2 = np.stack([table[k][0] for k in k2])
    ref_A2 = np.array([table[k][1] for k in k2], float)
    ref_p1 = np.stack([table[k][0] for k in k1])
    ref_A1 = np.array([table[k][1] for k in k1], float)
    T = d["T_K"].to_numpy(float)

    g_ref = score(layer, ref_p2, ref_A2, ref_p1, ref_A1, T)
    dev = np.abs(g_ref - d["g_res"].to_numpy(float))
    keep = ~(dev > GATE_TOL)
    print(f"ВОРОТА: макс|Δ| {np.nanmax(dev):.3e}, отброшено {int((~keep).sum())} из {len(d)}")
    d = d[keep].reset_index(drop=True)
    k2 = [x for x, o in zip(k2, keep) if o]
    k1 = [x for x, o in zip(k1, keep) if o]
    T, ref_p2, ref_A2 = T[keep], ref_p2[keep], ref_A2[keep]
    ref_p1, ref_A1 = ref_p1[keep], ref_A1[keep]
    m = d["m"].to_numpy(float)
    aq = d["aqueous"].to_numpy(bool) if "aqueous" in d.columns else np.zeros(len(d), bool)
    rsh2 = ref_p2 / ref_A2[:, None]
    rsh1 = ref_p1 / ref_A1[:, None]
    mols = sorted(set(k2) | set(k1))
    template = pd.read_csv(TEST, nrows=1, low_memory=False)

    rows = []
    for seed in a.seeds:
        ck = CKPT_DIR / f"grounded_a_seed{seed}.pt"
        if not ck.exists():
            print(f"нет чекпойнта {ck}")
            continue
        model, _, cfg = build_model(ck)
        as_sol, as_slv = learned_profiles(model, cfg, mols, template)
        U = {s: np.asarray(as_sol[i], float) for i, s in enumerate(mols)}
        V = {s: np.asarray(as_slv[i], float) for i, s in enumerate(mols)}
        lp2 = np.stack([U[s] for s in k2])
        lA2 = lp2.sum(1)
        sh2 = lp2 / lA2[:, None]
        lp1 = np.stack([V[s] for s in k1])
        lA1 = lp1.sum(1)
        sh1 = lp1 / lA1[:, None]

        g0 = score(layer, sh2 * lA2[:, None], lA2, sh1 * lA1[:, None], lA1, T)
        base = aad(g0, m)
        rows.append({"seed": seed, "window": "ничего не подставлено", "n_bins": 0,
                     "aad": base, "aad_aqueous": aad(g0, m, aq),
                     "aad_nonaqueous": aad(g0, m, ~aq), "kind": "база"})
        print(f"  сид {seed} база AAD {base:.4f}")

        for name, w in windows.items():
            p2 = substitute(sh2, rsh2, w) * lA2[:, None]
            p1 = substitute(sh1, rsh1, w) * lA1[:, None]
            g = score(layer, p2, lA2, p1, lA1, T)
            rows.append({"seed": seed, "window": name, "n_bins": int(w.sum()),
                         "aad": aad(g, m), "aad_aqueous": aad(g, m, aq),
                         "aad_nonaqueous": aad(g, m, ~aq), "kind": "окно"})
            print(f"    {name:<22} {int(w.sum()):>3} бинов: AAD {rows[-1]['aad']:.4f} "
                  f"(выигрыш {base - rows[-1]['aad']:+.4f})")

        # НУЛЬ ПО РАСПОЛОЖЕНИЮ: случайные наборы того же размера, что донорное окно и ядро.
        rng = np.random.default_rng(seed)
        for ref_name in ("донорное окно", "ядро", "акцепторное окно"):
            k = int(windows[ref_name].sum())
            got = []
            for r in range(a.n_random):
                w = np.zeros(n_bins, bool)
                w[rng.choice(n_bins, k, replace=False)] = True
                p2 = substitute(sh2, rsh2, w) * lA2[:, None]
                p1 = substitute(sh1, rsh1, w) * lA1[:, None]
                got.append(aad(score(layer, p2, lA2, p1, lA1, T), m))
            rows.append({"seed": seed, "window": f"СЛУЧАЙНЫЕ {k} бинов (нуль к «{ref_name}»)",
                         "n_bins": k, "aad": float(np.mean(got)),
                         "aad_sd_over_draws": float(np.std(got, ddof=1)),
                         "kind": "нуль"})
            print(f"    случайные {k:>3} бинов: AAD {np.mean(got):.4f} ± {np.std(got, ddof=1):.4f} "
                  f"(выигрыш {base - np.mean(got):+.4f})")

    a.out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(a.out / "per_arm.csv", index=False)

    base_mean = df[df.window.eq("ничего не подставлено")].aad.mean()
    print(f"\nбаза (ничего не подставлено): {base_mean:.4f}")
    print(f"{'подстановка':<40}{'бинов':>7}{'AAD':>9}{'выигрыш':>10}{'sd':>8}{'5/5':>6}")
    piv = df.pivot_table(index="seed", columns="window", values="aad")
    agg = {}
    order = [w for w in df.window.unique() if w != "ничего не подставлено"]
    for w in order:
        sub = df[df.window.eq(w)]
        gain = (piv["ничего не подставлено"] - piv[w]) if w in piv.columns else None
        pos = int((gain > 0).sum()) if gain is not None else 0
        agg[w] = {"aad": float(sub.aad.mean()),
                  "gain": (float(gain.mean()) if gain is not None else None),
                  "gain_sd": (float(gain.std(ddof=1)) if gain is not None else None),
                  "positive": pos, "n_bins": int(sub.n_bins.iloc[0])}
        print(f"{w:<40}{agg[w]['n_bins']:>7}{agg[w]['aad']:>9.4f}"
              f"{agg[w]['gain']:>+10.4f}{agg[w]['gain_sd']:>8.4f}{pos:>4}/5")

    ceil_ = agg.get("все бины (потолок)", {}).get("gain")
    print()
    for w in ("донорное окно", "ядро", "акцепторное окно"):
        g = agg.get(w, {}).get("gain")
        null_key = next((k for k in agg if k.startswith("СЛУЧАЙНЫЕ")
                         and f"«{w}»" in k), None)
        gn = agg.get(null_key, {}).get("gain") if null_key else None
        if g is not None and ceil_:
            line = f"  {w:<20} {g / ceil_:>6.1%} потолка формы"
            if gn is not None:
                line += f"; нуль по расположению {gn / ceil_:>6.1%} -> сверх нуля {(g - gn) / ceil_:+.1%}"
            print(line)

    (a.out / "summary.json").write_text(json.dumps(
        {"n_rows": int(len(d)), "n_aqueous": int(aq.sum()), "seeds": a.seeds,
         "sigma_hb": s_hb, "n_bins": n_bins, "n_random_draws": a.n_random,
         "base_aad": base_mean, "per_window": agg, "rows": rows},
        ensure_ascii=False, indent=2))
    print(f"\n-> {a.out / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
