#!/usr/bin/env python
"""Ворота перед покупкой T2: ВЫНУЖДАЕТ ли софтмакс пьедестал, или голова его выбирает.

ЧТО УТВЕРЖДАЕТ СВЯЗКА 3 рамки J. Часть свободы, которой пользуется голова, навязана
архитектурой: софтмакс не умеет выдавать ровные нули, а у эталонного профиля 57% бинов ровно
нулевые. Отсюда замысел T2 -- голова, способная на нули (sparsemax/entmax).

ПОЧЕМУ ЭТО НАДО ПРОВЕРИТЬ ДО АРМА. Софтмакс не умеет выдавать РОВНЫЙ нуль, но умеет выдавать
сколь угодно малое: при разрыве логитов в десять он доходит до ~5.6e-07, а в
tests/test_donor_window_per_seed_binds.py уже записано, что обученные плечи оставляют в крайних
бинах 0.015 массы -- на ЧЕТЫРЕ ПОРЯДКА выше этого пола. Если так же обстоит дело во всех
эталонно-нулевых бинах, то связывающего ограничения нет: голова кладёт туда массу не потому, что
не может иначе, а потому, что так получается при обучении, и нуль-способная голова не снимет
ограничения, которого нет.

РЕШАЮЩЕЕ СРАВНЕНИЕ ВНУТРИ ОДНОГО ЧЕКПОЙНТА, А НЕ С ТЕОРЕТИЧЕСКИМ ПОЛОМ. Теоретический пол зависит
от разрыва логитов, который сам есть свойство обученной сети, так что сравнивать с 5.6e-07 значило
бы сравнивать с числом из другого режима. Вместо этого спрашивается: ДОХОДИТ ли эта же голова на
этом же корпусе до малых значений где-нибудь? Если минимальная масса бина у неё 1e-06, а в
эталонно-нулевых бинах она кладёт 1e-02, то разница в четыре порядка есть выбор головы, а не
предел софтмакса. Это сравнение не требует никакой внешней величины.

НУЛЕВОЕ ПЛЕЧО: та же статистика на НЕобученной голове той же архитектуры. У неё пьедестал обязан
быть выше (ей никто не говорил, где нули), и если обученная от необученной не отличается, то
измеряется инициализация, а не обучение.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/read_t2_softmax_floor_is_binding.py
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
CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
OUT = ROOT / "results/t2_softmax_floor"


def stats(shape: np.ndarray, zero_mask: np.ndarray) -> dict:
    """shape: (n_mol, n_bins), нормирован на 1. zero_mask: где эталон РОВНО нуль."""
    ped = np.array([shape[i, zero_mask[i]].sum() for i in range(len(shape))])
    in_zero = np.concatenate([shape[i, zero_mask[i]] for i in range(len(shape))])
    in_nz = np.concatenate([shape[i, ~zero_mask[i]] for i in range(len(shape))])
    return {
        "pedestal_median": float(np.median(ped)),
        "pedestal_mean": float(ped.mean()),
        "pedestal_p95": float(np.quantile(ped, 0.95)),
        "pedestal_max": float(ped.max()),
        "min_bin_mass_anywhere": float(shape.min()),
        "median_bin_mass_in_zero_bins": float(np.median(in_zero)),
        "p01_bin_mass_in_zero_bins": float(np.quantile(in_zero, 0.01)),
        "median_bin_mass_in_nonzero_bins": float(np.median(in_nz)),
        "orders_between_min_and_zero_bin_median": float(
            np.log10(max(np.median(in_zero), 1e-300) / max(shape.min(), 1e-300))),
        "share_of_zero_bins_below_1e_5": float((in_zero < 1e-5).mean()),
        "share_of_zero_bins_below_1e_3": float((in_zero < 1e-3).mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    n_bins = int(CosmoSacLayer().n_bins)
    table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
    d = pd.read_csv(RECORDS)
    mols = sorted({str(s) for s in pd.concat([d.solute_smiles, d.solvent_smiles])
                   if canonicalize(str(s)) in table})
    ref = np.stack([np.asarray(table[canonicalize(m)][0], float) for m in mols])
    ref = ref / np.maximum(ref.sum(1, keepdims=True), 1e-30)
    zero = ref == 0.0
    print(f"молекул с эталонным профилем: {len(mols)}; бинов {n_bins}")
    print(f"эталонно-нулевых бинов: {100 * zero.mean():.1f}% всех клеток "
          f"(по молекуле медиана {int(np.median(zero.sum(1)))} из {n_bins})")

    tpl = pd.read_csv(ROOT / "notebooks/data/processed/test.csv", nrows=1, low_memory=False)
    res: dict = {"n_molecules": len(mols), "n_bins": n_bins,
                 "share_reference_zero_cells": float(zero.mean()),
                 "median_zero_bins_per_molecule": int(np.median(zero.sum(1))),
                 "per_seed": {}}

    for s in a.seeds:
        ck = CKPT_DIR / f"grounded_a_seed{s}.pt"
        if not ck.exists():
            print(f"сид {s}: чекпойнта нет, пропуск")
            continue
        model, _, cfg = build_model(ck)
        for role, prof in zip(("solute", "solvent"), learned_profiles(model, cfg, mols, tpl)):
            p = np.asarray(prof, float)
            p = p / np.maximum(p.sum(1, keepdims=True), 1e-30)
            st = stats(p, zero)
            res["per_seed"].setdefault(str(s), {})[role] = st
            print(f"  сид {s} {role:8s}: пьедестал медиана {st['pedestal_median']:.4f}  "
                  f"мин.масса бина {st['min_bin_mass_anywhere']:.2e}  "
                  f"медиана в нулевых бинах {st['median_bin_mass_in_zero_bins']:.2e}  "
                  f"порядков между ними {st['orders_between_min_and_zero_bin_median']:.1f}")

    # --- НУЛЕВОЕ ПЛЕЧО: необученная голова той же архитектуры -----------------------------
    from tgnn_solv.config import TGNNSolvConfig
    from tgnn_solv.heads import SigmaProfileHead
    torch.manual_seed(0)
    cfg0 = TGNNSolvConfig()
    head = SigmaProfileHead(input_dim=256, cfg=cfg0)
    head.eval()
    with torch.no_grad():
        g = torch.randn(len(mols), 256)
        p0 = head(g)["p_shape"].numpy().astype(float)
    res["untrained_null"] = stats(p0, zero)
    n0 = res["untrained_null"]
    print(f"\n  НУЛЬ, необученная голова: пьедестал медиана {n0['pedestal_median']:.4f}  "
          f"мин.масса {n0['min_bin_mass_anywhere']:.2e}")

    ks = list(res["per_seed"])
    if ks:
        print(f"\n{'=' * 78}\nВОРОТА: связывает ли софтмакс")
        for role in ("solute", "solvent"):
            ped = np.array([res["per_seed"][k][role]["pedestal_median"] for k in ks])
            mn = np.array([res["per_seed"][k][role]["min_bin_mass_anywhere"] for k in ks])
            med0 = np.array([res["per_seed"][k][role]["median_bin_mass_in_zero_bins"]
                             for k in ks])
            orders = np.array([res["per_seed"][k][role]
                               ["orders_between_min_and_zero_bin_median"] for k in ks])
            below = np.array([res["per_seed"][k][role]["share_of_zero_bins_below_1e_5"]
                              for k in ks])
            print(f"\n  {role}")
            print(f"   пьедестал (доля массы в эталонно-нулевых бинах): медиана по сидам "
                  f"{np.median(ped):.4f}, разброс {ped.min():.4f}...{ped.max():.4f}")
            print(f"   против необученной головы {n0['pedestal_median']:.4f}  "
                  f"{'ok, обучение двигает' if ped.max() < 0.8 * n0['pedestal_median'] else 'НЕ ОТЛИЧАЕТСЯ от инициализации'}")
            print(f"   эта же голова доходит до {mn.min():.2e} где-то на корпусе, "
                  f"а в нулевых бинах кладёт {np.median(med0):.2e}")
            print(f"   разница: {np.median(orders):.1f} порядков (посидово "
                  f"{orders.min():.1f}...{orders.max():.1f})")
            print(f"   доля эталонно-нулевых клеток, где голова УЖЕ ниже 1e-5: "
                  f"{100 * np.median(below):.2f}%")
            verdict = ("СОФТМАКС НЕ СВЯЗЫВАЕТ -- пьедестал есть выбор головы, "
                       "нуль-способность снимает ограничение, которого нет"
                       if np.median(orders) > 2.0 else
                       "софтмакс связывает -- голова упирается в пол, T2 имеет смысл")
            print(f"   ВЕРДИКТ: {verdict}")

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    print(f"\nзаписано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
