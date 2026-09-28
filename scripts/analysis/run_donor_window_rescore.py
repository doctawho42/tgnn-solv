#!/usr/bin/env python
"""Переизмерение донорного окна на ПЛЕЧАХ ЗАПИСИ, в схеме отозванного депозита.

ЗАЧЕМ. Sec. 3.3 и Fig. donor-window стоят на results/closure_ladder/placebo_profile_diagnosis.csv
-- прогоне, отозванном и лежащем вне всех деревьев, о чём предупреждает докстринг его же гейта.
Измерение 2026-09-28 (scripts/analysis/run_sigma_profile_residual.py) показало, что на плечах,
откуда берутся заголовочные 1.93 -> 2.34, донорная площадь выученного профиля меньше в десятки
раз. Этот скрипт повторяет ту же таблицу на grounded_a, сиды 42-46, чтобы раздел можно было
переставить на своё же плечо, а не переобъявлять.

СХЕМА СОВПАДАЕТ СО СТАРЫМ ДЕПОЗИТОМ построчно и поколоночно: те же растворители, те же
n_rows из размеченного теста, те же learned_donor_window_area / reference_donor_window_area /
learned_total_area / learned_donor_fraction. Иначе сравнение было бы не сравнением.

РОЛЬ РАСТВОРИТЕЛЯ, А НЕ РАСТВОРЯЕМОГО. Выученный профиль зависит от роли молекулы (энкодер
несёт два role-specific слоя: этанол выходит 88.3 A^2 как растворяемое и 108.0 A^2 как
растворитель). В этой таблице все молекулы -- растворители, поэтому берётся роль растворителя.
Старый депозит роль не называет; это ещё одна причина, по которой его числа не с чем было
сверять.

    python scripts/analysis/run_donor_window_rescore.py
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
from tgnn_solv.data.utils import canonicalize                          # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles                 # noqa: E402

CKPT_DIR = ROOT / "checkpoints/e5_leakfree"
RETIRED = ROOT / "results/closure_ladder/placebo_profile_diagnosis.csv"
PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
TEST = ROOT / "notebooks/data/processed/test.csv"
OUT = ROOT / "results/donor_window_rescore"

#: Четыре растворителя, чьи площади Sec. 3.3 печатает поимённо.
NAMED = {"C1CCCCC1": "cyclohexane", "CC(C)=O": "acetone",
         "Cc1ccccc1": "toluene", "C1CCOC1": "THF"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=16, help="сколько рисует фигура")
    args = ap.parse_args()

    old = pd.read_csv(RETIRED)
    solvents = [str(s) for s in old["solvent_smiles"]]
    print(f"растворителей в отозванном депозите: {len(solvents)}")

    cks = sorted(CKPT_DIR.glob("grounded_a_seed*.pt"))
    if not cks:
        print(f"нет чекпойнтов в {CKPT_DIR}")
        return 1

    _, _, cfg0 = build_model(cks[0])
    n_bins = int(cfg0.cosmo_sac_n_bins)
    grid = np.linspace(cfg0.cosmo_sac_sigma_min, cfg0.cosmo_sac_sigma_max, n_bins)
    donor = grid <= -float(cfg0.cosmo_sac_sigma_hb)

    table = load_sigma_profiles(str(PROFILES), n_bins=n_bins)
    ref_area, missing_ref = {}, []
    for s in solvents:
        key = canonicalize(s)
        hit = table.get(key) if key else None
        if hit is None:
            missing_ref.append(s)
            ref_area[s] = float("nan")
        else:
            ref_area[s] = float(np.asarray(hit[0])[donor].sum())
    if missing_ref:
        print(f"  без эталонного профиля: {len(missing_ref)} -> {missing_ref[:4]}")

    test = pd.read_csv(TEST, low_memory=False)
    scored = test[test["ln_x2"].notna()]
    n_rows = scored["solvent_smiles"].astype(str).value_counts()

    template = pd.read_csv(TEST, nrows=1, low_memory=False)
    per_seed: dict[int, np.ndarray] = {}
    for ck in cks:
        model, ckd, cfg = build_model(ck)
        seed = int(ckd.get("seed", -1))
        print(f"  сид {seed} ...", flush=True)
        _, as_solvent = learned_profiles(model, cfg, solvents, template)
        per_seed[seed] = as_solvent

    rows = []
    for i, s in enumerate(solvents):
        d_by_seed = {sd: float(p[i][donor].sum()) for sd, p in per_seed.items()}
        t_by_seed = {sd: float(p[i].sum()) for sd, p in per_seed.items()}
        d_vals, t_vals = np.array(list(d_by_seed.values())), np.array(list(t_by_seed.values()))
        rows.append({
            "solvent_smiles": s,
            "n_rows": int(n_rows.get(s, 0)),
            "learned_donor_window_area": float(d_vals.mean()),
            "learned_donor_window_area_sd": float(d_vals.std(ddof=1)),
            "reference_donor_window_area": ref_area[s],
            "learned_total_area": float(t_vals.mean()),
            "learned_donor_fraction": float((d_vals / t_vals).mean()),
            "retired_learned_donor_window_area": float(
                old.loc[old.solvent_smiles == s, "learned_donor_window_area"].iloc[0]),
            "retired_learned_donor_fraction": float(
                old.loc[old.solvent_smiles == s, "learned_donor_fraction"].iloc[0]),
        })
    df = pd.DataFrame(rows).sort_values("n_rows", ascending=False).reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "per_solvent.csv", index=False)

    top = df.head(args.top)
    named_frac = [float(df.loc[df.solvent_smiles == s, "learned_donor_fraction"].iloc[0])
                  for s in NAMED if (df.solvent_smiles == s).any()]
    summary = {
        "arms": "e5_leakfree/grounded_a", "seeds": sorted(per_seed),
        "n_solvents": len(df), "figure_top": int(args.top),
        "empty_reference_count_in_top": int((top["reference_donor_window_area"] <= 1e-9).sum()),
        "named_solvents": {NAMED[s]: {
            "learned_area": float(df.loc[df.solvent_smiles == s, "learned_donor_window_area"].iloc[0]),
            "retired_area": float(df.loc[df.solvent_smiles == s, "retired_learned_donor_window_area"].iloc[0]),
            "reference_area": float(df.loc[df.solvent_smiles == s, "reference_donor_window_area"].iloc[0]),
            "learned_fraction": float(df.loc[df.solvent_smiles == s, "learned_donor_fraction"].iloc[0]),
        } for s in NAMED if (df.solvent_smiles == s).any()},
        "named_fraction_range": [min(named_frac), max(named_frac)] if named_frac else None,
        "retired_named_fraction_range": [
            float(old.loc[old.solvent_smiles.isin(NAMED), "learned_donor_fraction"].min()),
            float(old.loc[old.solvent_smiles.isin(NAMED), "learned_donor_fraction"].max())],
        "median_learned_donor_fraction": float(df["learned_donor_fraction"].median()),
        "retired_median_learned_donor_fraction": float(old["learned_donor_fraction"].median()),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                      encoding="utf8")

    print(f"\n{'растворитель':<16}{'n':>5}{'эталон':>9}{'отозв.':>9}{'запись':>9}{'доля, %':>10}")
    for r in top.itertuples():
        print(f"  {r.solvent_smiles:<14}{r.n_rows:>5}{r.reference_donor_window_area:>9.2f}"
              f"{r.retired_learned_donor_window_area:>9.1f}{r.learned_donor_window_area:>9.2f}"
              f"{100*r.learned_donor_fraction:>10.1f}")
    nf, rf = summary["named_fraction_range"], summary["retired_named_fraction_range"]
    print(f"\n  доля донорной площади по четырём поимённым:")
    print(f"    Sec. 3.3 (отозванный):  {100*rf[0]:.0f}-{100*rf[1]:.0f}%")
    print(f"    плечи записи:           {100*nf[0]:.1f}-{100*nf[1]:.1f}%")
    print(f"  медиана по всем {len(df)}:   отозв. {100*summary['retired_median_learned_donor_fraction']:.1f}%"
          f"  ->  запись {100*summary['median_learned_donor_fraction']:.1f}%")
    print(f"  в топ-{args.top} с ПУСТЫМ эталоном: {summary['empty_reference_count_in_top']} "
          f"(в подписи к фигуре стоит 12 из 16)")
    print(f"\nзаписано: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
