#!/usr/bin/env python
"""Что несёт дефект AAD на IDAC -- ФОРМА профиля или его ПЛОЩАДЬ?

ЗАЧЕМ. Вокруг этого вопроса дважды строились выводы, и оба раза без замера. Разведка E1
(PROJECT_MEMORY, 2026-10-03) многократно утверждала, что вся деградация 1.751 -- это ПЛОЩАДЬ
воды, а значит любое вмешательство в форму даст нуль гарантированно. Утверждение проверяемо
пересчётом, без обучения, и проверять его надо до того, как на его основании закрывается или
открывается направление.

ЧЕТЫРЕ ПЛЕЧА -- МАТРИЦА 2x2, и в ней вся суть: форма берётся выученная или эталонная,
площадь -- выученная или эталонная, второе держится фиксированным. Профиль собирается как
(нормированная форма) x (площадь), поэтому подстановка одного множителя не задевает другой.

    A  выученная форма  + выученная площадь     -- плечо записи
    B  выученная форма  + ЭТАЛОННАЯ площадь    -- исправлена только площадь
    C  ЭТАЛОННАЯ форма  + выученная площадь    -- исправлена только форма
    D  эталон оба                               -- потолок подстановки

ВОРОТА, без которых читать нельзя. Плечо D пересчитывается из артефакта по каноническому
SMILES и обязано воспроизвести депонированный столбец ``g_res``. Строки, где не воспроизводит,
отбрасываются и их число печатается: расхождение означает несовпадение ключей (у депозита
InChIKey, здесь SMILES), и тогда выученные плечи сравниваются не с тем эталоном.

КОНВЕНЦИЯ ЗАМЫКАНИЯ держится фиксированной и совпадает с депозитом: ``CosmoSacLayer()`` с
умолчаниями, ``V=None`` (только остаточный член -- мольных объёмов у выученной стороны нет,
и ``g_res`` посчитан так же). Меняется ТОЛЬКО источник профиля.

РОЛЬ. Энкодер несёт два role-specific адаптера, поэтому одна молекула даёт разный профиль как
растворяемое и как растворитель. Назначение естественное: растворяемое в слот растворяемого,
растворитель в слот растворителя. У эталона роли нет по построению.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_shape_vs_area_decomposition.py
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

from run_sigma_profile_residual import (  # noqa: E402
    PROFILES, TEST, build_model, learned_profiles,
)
from tgnn_solv.data.utils import canonicalize  # noqa: E402
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles  # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
RECORDS = ROOT / "results/published_idac_check/scored_records.csv"
OUT_DIR = ROOT / "results/shape_vs_area"
GATE_TOL = 1e-6


def score(layer, p2, A2, p1, A1, T, batch: int = 2048) -> np.ndarray:
    """ln gamma_2^inf по паре профилей, конвенция ``res`` (V=None), как в депозите."""
    out = []
    with torch.no_grad():
        for i in range(0, len(T), batch):
            s = slice(i, i + batch)
            out.append(layer.ln_gamma_inf(
                torch.tensor(p2[s], dtype=torch.float),
                torch.tensor(p1[s], dtype=torch.float),
                torch.tensor(A2[s], dtype=torch.float),
                torch.tensor(A1[s], dtype=torch.float),
                None, None,
                torch.tensor(T[s], dtype=torch.float)).numpy())
    return np.concatenate(out) if out else np.zeros(0)


def aad(g: np.ndarray, m: np.ndarray, sel: np.ndarray | None = None) -> float:
    sel = np.ones(len(g), bool) if sel is None else sel
    ok = np.isfinite(g[sel]) & np.isfinite(m[sel])
    return float(np.abs(g[sel][ok] - m[sel][ok]).mean()) if ok.any() else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--records", type=Path, default=RECORDS)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    a = ap.parse_args()

    layer = CosmoSacLayer()
    layer.eval()
    table = load_sigma_profiles(str(PROFILES), n_bins=51)
    d = pd.read_csv(a.records, low_memory=False)
    k2 = [canonicalize(str(s)) for s in d.solute_smiles]
    k1 = [canonicalize(str(s)) for s in d.solvent_smiles]
    missing = [k for k in set(k2) | set(k1) if k not in table]
    if missing:
        raise SystemExit(f"{len(missing)} SMILES записей отсутствуют в артефакте профилей, "
                         f"например {missing[:3]} -- ворота читать нельзя")
    ref_p2 = np.stack([table[k][0] for k in k2])
    ref_A2 = np.array([table[k][1] for k in k2], float)
    ref_p1 = np.stack([table[k][0] for k in k1])
    ref_A1 = np.array([table[k][1] for k in k1], float)
    T = d["T_K"].to_numpy(float)

    # --- ВОРОТА: эталон, пересчитанный здесь, против депонированного g_res ---
    g_ref_all = score(layer, ref_p2, ref_A2, ref_p1, ref_A1, T)
    dev = np.abs(g_ref_all - d["g_res"].to_numpy(float))
    keep = ~(dev > GATE_TOL)
    print(f"ВОРОТА: макс|Δ| до отбрасывания {np.nanmax(dev):.3e}; "
          f"неоднозначных строк {int((~keep).sum())} из {len(d)}; "
          f"после отбрасывания {np.nanmax(dev[keep]):.3e}")
    d = d[keep].reset_index(drop=True)
    k2 = [x for x, o in zip(k2, keep) if o]
    k1 = [x for x, o in zip(k1, keep) if o]
    T, ref_p2, ref_A2 = T[keep], ref_p2[keep], ref_A2[keep]
    ref_p1, ref_A1 = ref_p1[keep], ref_A1[keep]
    m = d["m"].to_numpy(float)
    aq = d["aqueous"].to_numpy(bool) if "aqueous" in d.columns else np.zeros(len(d), bool)
    print(f"строк {len(d)}, из них водных {int(aq.sum())} ({aq.mean():.1%})")

    mols = sorted(set(k2) | set(k1))
    template = pd.read_csv(TEST, nrows=1, low_memory=False)
    rsh2 = ref_p2 / ref_A2[:, None]
    rsh1 = ref_p1 / ref_A1[:, None]

    rows = []
    for seed in a.seeds:
        ck = CKPT_DIR / f"grounded_a_seed{seed}.pt"
        if not ck.exists():
            print(f"нет чекпойнта {ck}")
            continue
        model, _, cfg = build_model(ck)
        as_solute, as_solvent = learned_profiles(model, cfg, mols, template)
        U = {s: np.asarray(as_solute[i], float) for i, s in enumerate(mols)}
        V = {s: np.asarray(as_solvent[i], float) for i, s in enumerate(mols)}
        lp2 = np.stack([U[s] for s in k2])
        lA2 = lp2.sum(1)
        sh2 = lp2 / lA2[:, None]
        lp1 = np.stack([V[s] for s in k1])
        lA1 = lp1.sum(1)
        sh1 = lp1 / lA1[:, None]

        arms = {
            "A выученные форма+площадь": (sh2 * lA2[:, None], lA2, sh1 * lA1[:, None], lA1),
            "B выученная форма + эталонная площадь":
                (sh2 * ref_A2[:, None], ref_A2, sh1 * ref_A1[:, None], ref_A1),
            "C эталонная форма + выученная площадь":
                (rsh2 * lA2[:, None], lA2, rsh1 * lA1[:, None], lA1),
            "D эталон оба": (ref_p2, ref_A2, ref_p1, ref_A1),
        }
        for name, (p2, A2, p1, A1) in arms.items():
            g = score(layer, p2, A2, p1, A1, T)
            rows.append({"seed": seed, "arm": name, "aad": aad(g, m),
                         "aad_aqueous": aad(g, m, aq), "aad_nonaqueous": aad(g, m, ~aq)})
            print(f"  сид {seed} {name:<38} AAD {rows[-1]['aad']:.4f}  "
                  f"водные {rows[-1]['aad_aqueous']:.4f}  неводные {rows[-1]['aad_nonaqueous']:.4f}")
        w = canonicalize("O")
        if w in V:
            print(f"    площадь воды как растворителя: выучено {V[w].sum():.1f} против "
                  f"эталона {table[w][1]:.1f} A^2")

    a.out.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(a.out / "per_arm.csv", index=False)

    print(f"\n{'плечо':<40}{'AAD':>9}{'sd':>8}{'водные':>9}{'неводные':>10}")
    agg = {}
    for name in df.arm.unique():
        sub = df[df.arm.eq(name)]
        agg[name] = {"aad": float(sub.aad.mean()),
                     "sd": (float(sub.aad.std(ddof=1)) if len(sub) > 1 else None),
                     "aqueous": float(sub.aad_aqueous.mean()),
                     "nonaqueous": float(sub.aad_nonaqueous.mean()), "n_seeds": len(sub)}
        sd = agg[name]["sd"]
        print(f"{name:<40}{agg[name]['aad']:>9.4f}"
              f"{(f'{sd:.4f}' if sd else '--'):>8}"
              f"{agg[name]['aqueous']:>9.4f}{agg[name]['nonaqueous']:>10.4f}")

    A = agg.get("A выученные форма+площадь", {}).get("aad")
    B = agg.get("B выученная форма + эталонная площадь", {}).get("aad")
    C = agg.get("C эталонная форма + выученная площадь", {}).get("aad")
    D = agg.get("D эталон оба", {}).get("aad")
    verdict = {}
    if None not in (A, B, C, D):
        addressable = A - D
        verdict = {"addressable_gap_A_minus_D": addressable,
                   "area_only_B_minus_A": B - A, "shape_only_A_minus_C": A - C,
                   "shape_share_of_addressable": (A - C) / addressable if addressable else None}
        print(f"\nадресуемый разрыв A-D: {addressable:+.4f}")
        print(f"  исправление ТОЛЬКО площади (B-A): {B - A:+.4f}"
              f"{'  -- УХУДШАЕТ' if B > A else ''}")
        print(f"  исправление ТОЛЬКО формы  (A-C): {A - C:+.4f} "
              f"= {(A - C) / addressable:.1%} адресуемого")
        # Парно по сидам -- межсидовый sd поглощает разброс уровней.
        piv = df.pivot_table(index="seed", columns="arm", values="aad")
        kA, kC = "A выученные форма+площадь", "C эталонная форма + выученная площадь"
        if {kA, kC} <= set(piv.columns):
            dd = piv[kA] - piv[kC]
            verdict["shape_gain_paired"] = {"mean": float(dd.mean()),
                                            "sd": float(dd.std(ddof=1)),
                                            "positive": int((dd > 0).sum()), "n": len(dd)}
            print(f"  ПАРНО по сидам, выигрыш формы: {dd.mean():+.4f} +- {dd.std(ddof=1):.4f}, "
                  f"положителен {int((dd > 0).sum())}/{len(dd)}")

    (a.out / "summary.json").write_text(json.dumps(
        {"n_rows": int(len(d)), "n_aqueous": int(aq.sum()), "seeds": a.seeds,
         "n_iter_eval": int(layer.n_iter_eval), "gate_tol": GATE_TOL,
         "per_arm": agg, "verdict": verdict, "rows": rows}, ensure_ascii=False, indent=2))
    print(f"\n-> {a.out / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
