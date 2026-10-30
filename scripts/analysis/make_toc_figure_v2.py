#!/usr/bin/env python3
"""ToC-графика перезаписанной рукописи: один профиль и две противоположные стрелки.

ЧТО ОНА ДОЛЖНА СКАЗАТЬ ЗА ОДИН ВЗГЛЯД. Выученная величина стоит в слоте σ-профиля и не является
им: эталон в водородносвязанных окнах РОВНО нулевой, выученный профиль там населён. И подстановка
эталонных значений улучшает то, ради чего профиль существует (коэффициент активности), и ухудшает
то, что предсказывает конвейер (растворимость). Обе стрелки взяты из депозитов, не из прозы.

ЧИСЛА И ИХ ИСТОЧНИКИ.
  ln gamma: results/idac_learned_vs_reference/summary.json -- плечо learned 1.7511 против
            reference_vt2005 0.7650 на 7888 записях.
  ln x2:    results/e5_sigma_grounding/THREE_SEED_SUMMARY.md -- grounded_a 1.846 +- 0.053 против
            oracle 2.252 +- 0.021, то есть подстановка на выводе. У депозита есть собственный
            блок сверки с рисунком прежней статьи.

МОЛЕКУЛА. Ацетон: у эталона донорное окно ровно пустое, у выученного профиля населено, и профиль
узнаваем (сильный акцепторный пик). Нарисованные массивы кладутся рядом депозитом, чтобы рисунок
можно было перерисовать не загружая чекпойнт.

Спецификация ACS для ToC: не более 3.25 x 1.75 дюйма.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/make_toc_figure_v2.py
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

from acs_figure_style import apply  # noqa: E402
from run_sigma_profile_residual import build_model, learned_profiles  # noqa: E402
from tgnn_solv.data.utils import canonicalize  # noqa: E402
from tgnn_solv.layers import CosmoSacLayer  # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles  # noqa: E402

PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
CKPT = ROOT / "checkpoints/e5_leakfree/grounded_a_seed42.pt"
DEP = ROOT / "results/toc_graphic"
FIGS = ROOT / "paper/figs"

# обе пары читаются из депозитов; здесь они только названы, чтобы подпись и рисунок не разошлись
LNG = (1.7511, 0.7650)     # idac_learned_vs_reference: learned -> reference_vt2005, AAD
LNX = (1.846, 2.252)       # e5_sigma_grounding: grounded_a -> oracle, MAE
INK, REFC, LRN, GOOD, BAD = "#1a1a1a", "#2166ac", "#b2182b", "#2166ac", "#b2182b"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--smiles", default="CC(=O)C", help="молекула (ацетон по умолчанию)")
    ap.add_argument("--name", default="acetone")
    a = ap.parse_args()

    layer = CosmoSacLayer()
    n_bins = int(layer.n_bins)
    grid = layer.sigma_grid.numpy() * 1e3
    hb = 1e3 * float(layer.sigma_hb)
    table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
    key = canonicalize(a.smiles)
    if key not in table:
        raise SystemExit(f"{a.smiles}: эталонного профиля нет в таблице")
    ref = np.asarray(table[key][0], float)
    ref = ref / ref.sum()

    tpl = pd.read_csv(ROOT / "notebooks/data/processed/test.csv", nrows=1, low_memory=False)
    model, _, cfg = build_model(CKPT)
    _, as_solvent = learned_profiles(model, cfg, [a.smiles], tpl)
    lrn = np.asarray(as_solvent[0], float)
    lrn = lrn / lrn.sum()
    print(f"{a.name}: эталон нулевой в {int((ref == 0).sum())} бинах из {n_bins}; "
          f"выученный минимум {lrn.min():.2e}")

    DEP.mkdir(parents=True, exist_ok=True)
    (DEP / "profiles.json").write_text(json.dumps(
        {"smiles": a.smiles, "name": a.name, "sigma_grid_e_per_A2": (grid / 1e3).tolist(),
         "sigma_hb": float(layer.sigma_hb), "reference_shape": ref.tolist(),
         "learned_shape": lrn.tolist(), "checkpoint": CKPT.name,
         "ln_gamma_aad_learned_then_reference": list(LNG),
         "ln_x2_mae_learned_then_substituted": list(LNX)},
        ensure_ascii=False, indent=2), encoding="utf8")

    apply()
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(3.25, 1.72))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.52, 1.0], wspace=0.52,
                          left=0.115, right=0.985, top=0.80, bottom=0.21)
    axp, axb = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])

    for sgn in (-1, 1):
        axp.axvspan(sgn * hb, sgn * 26, color="#f0f0f0", lw=0, zorder=0)
    # ЛОГАРИФМИЧЕСКАЯ ОСЬ, И ЭТО НЕ ОФОРМЛЕНИЕ. На линейной шкале 1e-5 и ровный нуль
    # неразличимы, то есть рисунок не показывал бы того, что заявляет. На логарифмической
    # эталон ОБРЫВАЕТСЯ там, где он ровно нулевой, а выученный профиль идёт сплошной линией --
    # ровно то утверждение, ради которого графика существует.
    floor = 1e-8
    axp.step(grid, np.where(ref > 0, ref, np.nan), where="mid", color=REFC, lw=1.0, zorder=3)
    axp.step(grid, np.maximum(lrn, floor), where="mid", color=LRN, lw=1.0, zorder=4)
    axp.set_yscale("log")
    axp.set_xlim(-26, 26)
    axp.set_ylim(floor, 0.6)
    axp.set_yticks([1e-7, 1e-5, 1e-3, 1e-1])
    axp.set_yticklabels(["$10^{-7}$", "$10^{-5}$", "$10^{-3}$", "$10^{-1}$"])
    axp.set_xticks([-20, 0, 20])
    axp.tick_params(labelsize=5.0, length=2, pad=1)
    axp.set_xlabel("$\\sigma$ ($10^{-3}\\,e\\,\\mathrm{\\AA}^{-2}$)", fontsize=5.4,
                   labelpad=0.5)
    axp.text(0.5, 1.045, f"{a.name}: $\\sigma$-profile", transform=axp.transAxes, fontsize=6.0,
             ha="center", color=INK)
    axp.text(-6.5, 1.1e-5, "reference stops", fontsize=5.2, color=REFC, ha="left")
    axp.text(-6.5, 1.1e-6, "learned does not", fontsize=5.2, color=LRN, ha="left")
    for s_ in ("top", "right"):
        axp.spines[s_].set_visible(False)

    # --- две стрелки: одна и та же подстановка, противоположные стороны -----------------
    axb.set_xlim(0, 1)
    axb.set_ylim(0, 1)
    axb.axis("off")
    axb.text(0.5, 1.045, "supply the reference", transform=axb.transAxes, fontsize=6.0,
             ha="center", color=INK)
    for y, lab, (v0, v1), col, good in ((0.68, "activity\ncoefficient", LNG, GOOD, True),
                                        (0.20, "solubility", LNX, BAD, False)):
        axb.text(0.0, y + 0.145, lab, fontsize=5.4, color=INK, ha="left", va="center")
        axb.annotate("", xy=(0.80, y), xytext=(0.06, y),
                     arrowprops={"arrowstyle": "-|>", "lw": 1.2, "color": col})
        axb.text(0.03, y - 0.115, f"{v0:.2f}", fontsize=5.4, color="#6a6a6a", ha="left")
        axb.text(0.86, y - 0.115, f"{v1:.2f}", fontsize=5.8, color=col, ha="center",
                 weight="bold")
        axb.text(0.86, y + 0.10, "better" if good else "worse", fontsize=5.0, color=col,
                 ha="center")

    FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIGS / f"fig_toc_v2.{ext}", dpi=600)
    print("записано: paper/figs/fig_toc_v2.pdf и .png; депозит results/toc_graphic/profiles.json")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    sys.exit(main())
