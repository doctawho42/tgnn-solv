#!/usr/bin/env python3
"""Определитель: можно ли сказать заранее, где эталонному σ-профилю верить.

Правило, ограда и пороги: ``results/substitution_identifier/PRE_DECLARATION.md``.

ЦЕЛЬ — сделать условный закон операционным: не «подстановка вредит», а «вредит здесь, помогает
там, и это видно заранее».

ТРИ ВЕЩИ, БЕЗ КОТОРЫХ ЭТО БЫЛО БЫ ТЕАТРОМ, и все три жёстко закодированы здесь:

  1. ЗАПРЕЩЁННЫЕ ПРИЗНАКИ проверяются по имени, и запрещённое поле роняет прогон.  Метка считается
     из ошибок ОБОИХ плеч, поэтому любой выход плеча в признаках -- протечка.
  2. ПРОВЕРКА ПО РАСТВОРИТЕЛЯМ, не по строкам.  Эффективное n здесь 70 растворителей, а не 28040
     строк; групповые фолды не пересекаются, и это проверяется, а не предполагается.
  3. НУЛЕВОЕ ПЛЕЧО на перемешанных метках, в том же прогоне.  Если оно тоже «предсказывает» --
     признаки протекают, и вердикт отменяется.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_substitution_identifier.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

TREE = ROOT / "results/e5_sigma_grounding_leakfree"
PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
RESID = ROOT / "results/sigma_profile_residual/per_molecule.csv"
OUT = ROOT / "results/substitution_identifier"
SEEDS = (42, 43, 44, 45, 46)
BASE_RATE = 0.613        # предзаявлено: доля строк, где подстановка вредит
N_BOOT = 4000
RNG = np.random.default_rng(20261030)

#: Проверяется ПО ИМЕНИ. Любое из этих полей в признаках -- протечка, прогон падает.
FORBIDDEN = {"abs_error", "error", "ln_x2_pred", "ln_x2_true", "ln_gamma_2", "ln_gamma_inf",
             "Phi", "Phi_true", "T_m_solver", "dH_fus_solver", "delta", "solvent_smiles",
             "solute_smiles"}


def region_masks(n_bins: int, sigma_hb: float = 0.0084):
    grid = np.linspace(-0.025, 0.025, n_bins)
    return grid, grid <= -sigma_hb, grid >= sigma_hb


def geometry(p: np.ndarray, donor, acceptor) -> dict[str, float]:
    a = float(p.sum())
    if a <= 0:
        return {"area": 0.0, "donor_frac": 0.0, "acceptor_frac": 0.0, "zero_frac": 1.0}
    return {"area": a,
            "donor_frac": float(p[donor].sum() / a),
            "acceptor_frac": float(p[acceptor].sum() / a),
            "zero_frac": float((p <= 0).mean())}


def hellinger(p, q) -> float:
    p = np.clip(p, 0, None)
    q = np.clip(q, 0, None)
    return float(np.sqrt(0.5 * np.sum((np.sqrt(p) - np.sqrt(q)) ** 2)))


def build_table() -> pd.DataFrame:
    from tgnn_solv.data.utils import canonicalize
    from tgnn_solv.sigma_oracle import load_sigma_profiles
    ref = load_sigma_profiles(str(PROFILES), n_bins=51)
    _, donor, acceptor = region_masks(51)

    # выученная геометрия по молекуле и роли, из уже депонированного перескора
    rp = pd.read_csv(RESID)
    learned = {}
    for (smi,), g in rp.groupby(["smiles"]):
        learned[smi] = {
            "learn_area_solute": float(g.area_solute.median()),
            "learn_area_solvent": float(g.area_solvent.median()),
            "learn_donor_frac_solute": float(g.area_frac_donor_solute.median()),
            "learn_donor_frac_solvent": float(g.area_frac_donor_solvent.median()),
            "learn_H_to_ref_solute": float(g.hellinger_solute_vs_reference.median()),
            "learn_H_to_ref_solvent": float(g.hellinger_solvent_vs_reference.median()),
            "learn_role_gap": float(g.hellinger_solute_vs_solvent.median()),
        }

    frames = []
    for s in SEEDS:
        b = pd.read_csv(TREE / f"seed_{s}/grounded_a_predictions.csv", low_memory=False)
        o = pd.read_csv(TREE / f"seed_{s}/oracle_predictions.csv", low_memory=False)
        b = b[b.has_solubility.astype(bool)].reset_index(drop=True)
        o = o[o.has_solubility.astype(bool)].reset_index(drop=True)
        assert len(b) == len(o) == 5608, (len(b), len(o))
        frames.append(pd.DataFrame({
            "seed": s, "solvent_smiles": b.solvent_smiles.values,
            "solute_smiles": b.solute_smiles.values, "T": b["T"].values,
            "delta": o.abs_error.values - b.abs_error.values}))
    D = pd.concat(frames, ignore_index=True)

    recs = []
    for _, r in D.iterrows():
        cv = canonicalize(str(r.solvent_smiles))
        cu = canonicalize(str(r.solute_smiles))
        rec = {"seed": r.seed, "solvent_smiles": r.solvent_smiles,
               "solute_smiles": r.solute_smiles, "T": r["T"], "delta": r.delta}
        for tag, c in (("slv", cv), ("sol", cu)):
            g = geometry(ref[c][0], donor, acceptor) if c in ref else {
                "area": np.nan, "donor_frac": np.nan, "acceptor_frac": np.nan, "zero_frac": np.nan}
            for k, v in g.items():
                rec[f"ref_{tag}_{k}"] = v
        for tag, c in (("slv", cv), ("sol", cu)):
            L = learned.get(c, {})
            rec[f"B_{tag}_H_to_ref"] = L.get("learn_H_to_ref_solvent" if tag == "slv"
                                             else "learn_H_to_ref_solute", np.nan)
            rec[f"B_{tag}_role_gap"] = L.get("learn_role_gap", np.nan)
            rec[f"B_{tag}_donor_frac"] = L.get("learn_donor_frac_solvent" if tag == "slv"
                                               else "learn_donor_frac_solute", np.nan)
            la = L.get("learn_area_solvent" if tag == "slv" else "learn_area_solute", np.nan)
            ra = rec[f"ref_{tag}_area"]
            rec[f"B_{tag}_area_ratio"] = (la / ra) if (ra and ra == ra and ra > 0) else np.nan
        recs.append(rec)
    return pd.DataFrame(recs)


def evaluate(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray, label: str,
             shuffle: bool = False) -> dict:
    bad = sorted(set(X.columns) & FORBIDDEN)
    if bad:
        raise SystemExit(f"ОГРАДА: запрещённые признаки в наборе {label}: {bad}")
    if shuffle:
        # НУЛЕВОЕ ПЛЕЧО НА УРОВНЕ ГРУПП, а не строк.  Построчная перестановка ломает и связь
        # признак-метка, И связь метка-группа, из-за чего нуль получается смещённым: обученный на
        # шуме предсказатель почти постоянен, а бутстрэп по растворителям такой конфигурации не
        # пересэмплирует.  Проверка идёт по растворителям, значит и перестановка обязана быть по
        # растворителям: метки растворителей переставляются БЛОКАМИ, внутри блока порядок цел.
        uniq_g = np.unique(groups)
        perm = RNG.permutation(uniq_g)
        mapping = dict(zip(uniq_g, perm))
        yy = np.empty_like(y)
        pools = {g: list(np.where(groups == g)[0]) for g in uniq_g}
        for g in uniq_g:
            src = pools[mapping[g]]
            dst = pools[g]
            take = (src * (len(dst) // len(src) + 1))[: len(dst)]
            yy[dst] = y[take]
    else:
        yy = y
    pred = np.full(len(y), np.nan)
    gkf = GroupKFold(n_splits=5)
    for tr, te in gkf.split(X, yy, groups=groups):
        assert not (set(groups[tr]) & set(groups[te])), "ФОЛДЫ ПЕРЕСЕКЛИСЬ по растворителю"
        m = HistGradientBoostingRegressor(max_depth=4, max_iter=300, learning_rate=0.06,
                                          random_state=0)
        m.fit(X.iloc[tr], yy[tr])
        # ЦЕНТРИРОВАНИЕ ВНУТРИ ФОЛДА.  Без него уровни разных фолдов различаются (каждый учится на
        # своём среднем), и при почти постоянном предсказателе эта разница САМА даёт ранговую связь:
        # нулевое плечо выдавало ро = +0.23 против +0.04 у настоящего, то есть перебивало сигнал.
        # Нас интересует порядок ВНУТРИ фолда, а не межфолдовый уровень.
        pf = m.predict(X.iloc[te])
        pred[te] = pf - pf.mean()
    rho = float(spearmanr(pred, yy).statistic)
    sign_acc = float(((pred > 0) == (yy > 0)).mean())
    mae = float(np.abs(pred - yy).mean())
    mae_const = float(np.abs(yy.mean() - yy).mean())
    # бутстрэп ПО РАСТВОРИТЕЛЯМ
    uniq = np.unique(groups)
    draws = np.empty(N_BOOT)
    accs = np.empty(N_BOOT)
    idx_by_g = {g: np.where(groups == g)[0] for g in uniq}
    for i in range(N_BOOT):
        pick = RNG.choice(uniq, size=len(uniq), replace=True)
        ii = np.concatenate([idx_by_g[g] for g in pick])
        draws[i] = spearmanr(pred[ii], yy[ii]).statistic
        accs[i] = ((pred[ii] > 0) == (yy[ii] > 0)).mean()
    lo, hi = np.percentile(draws, [2.5, 97.5])
    alo, ahi = np.percentile(accs, [2.5, 97.5])
    return {"label": label, "shuffled": shuffle, "n": int(len(y)),
            "n_solvents": int(len(uniq)), "spearman": rho,
            "spearman_ci95": [float(lo), float(hi)], "spearman_excludes_zero": bool(not lo <= 0 <= hi),
            "sign_accuracy": sign_acc, "sign_accuracy_ci95": [float(alo), float(ahi)],
            "beats_base_rate": bool(alo > BASE_RATE),
            "mae": mae, "mae_constant_baseline": mae_const}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    T = build_table()
    print(f"таблица: {len(T)} строк, растворителей {T.solvent_smiles.nunique()}, "
          f"растворяемых {T.solute_smiles.nunique()}")
    y = T.delta.to_numpy(float)
    groups = T.solvent_smiles.astype(str).to_numpy()
    setA = [c for c in T.columns if c.startswith("ref_")] + ["T"]
    setB = setA + [c for c in T.columns if c.startswith("B_")]
    print(f"набор A: {len(setA)} признаков (только химия)   набор B: {len(setB)} (+ профиль модели)")
    res = {"base_rate_predeclared": BASE_RATE, "n_rows": int(len(T)),
           "features_A": setA, "features_B": setB, "readings": []}
    for label, cols in (("A", setA), ("B", setB)):
        for sh in (False, True):
            r = evaluate(T[cols].astype(float), y, groups, label, shuffle=sh)
            res["readings"].append(r)
            tag = "ПЕРЕМЕШАНО" if sh else "настоящее  "
            print(f"  набор {label} {tag}: ро = {r['spearman']:+.4f} "
                  f"CI [{r['spearman_ci95'][0]:+.4f}, {r['spearman_ci95'][1]:+.4f}]"
                  f"{'  исключает ноль' if r['spearman_excludes_zero'] else '  НАКРЫВАЕТ'}"
                  f"   знак {100*r['sign_accuracy']:.1f}% "
                  f"CI [{100*r['sign_accuracy_ci95'][0]:.1f}, {100*r['sign_accuracy_ci95'][1]:.1f}]"
                  f"{'  выше ставки' if r['beats_base_rate'] else '  НЕ выше ставки'}")
    a.out.mkdir(parents=True, exist_ok=True)
    T.to_csv(a.out / "table.csv", index=False)
    (a.out / "reading.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    print(f"записано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
