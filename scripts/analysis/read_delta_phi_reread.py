#!/usr/bin/env python3
"""Прочитать δΦ на семи кластерах ThermoML по правилу, записанному до чисел.

Правило: ``results/delta_phi_reread/PRE_DECLARATION.md``. Этот скрипт его применяет и НЕ меняет.

ЧТО ЗДЕСЬ ВАЖНО ПОНИМАТЬ ПРО ВОРОТА 2.  Предзаявка требует «непрерывности по фенантрену»: его δΦ
по метке ThermoML не должен отличаться от «исходного депонированного значения» больше чем на 0.366.
Эти ворота БЕССИЛЬНЫ, и скрипт это печатает, а не обходит:

  * в БУКВАЛЬНОЙ форме депонированное значение (0.08844 контроль / 0.93657 плечо) посчитано на
    армах Kaggle, то есть сравнение смешивало бы подмену метки со сменой окружения -- а окружения
    расходятся по MAE на ±0.2 (``results/e2_seed43_pair/RESULTS.md``);
  * в ВЫПОЛНИМОЙ форме (один и тот же арм, метка сплита против ThermoML) проверка ТАВТОЛОГИЧНА:
    δΦ = Φ_pred − Φ_true, подмена метки меняет только Φ_true, и ровно эта разница ОПРЕДЕЛИЛА порог
    0.282/0.366 в самой предзаявке.

Поэтому скрипт считает разницу метк как АРИФМЕТИЧЕСКУЮ сверку своего конвейера (должна выйти
0.282 в медиане и 0.366 в максимуме), и называет её сверкой, а не воротами.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/read_delta_phi_reread.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.diagnostics.compensation import annotate_compensation_frame  # noqa: E402

LABELS = ROOT / "results/thermoml_dhfus_labels/candidate_labels.csv"
OUT = ROOT / "results/delta_phi_reread/reading.json"

PAIRS = {
    42: {"base": ROOT / "results/cluster_certification/cluster/out/seed_42/grounded_a_predictions.csv",
         "treated": ROOT / "results/e2_attribution_replicate/cluster/grounded_a_detachcrystal/out/seed_42/grounded_a_detachcrystal_predictions.csv"},
    43: {"base": ROOT / "results/e2_seed43_pair/cluster/base/out/seed_43/grounded_a_predictions.csv",
         "treated": ROOT / "results/e2_seed43_pair/cluster/detachcrystal/out/seed_43/grounded_a_detachcrystal_predictions.csv"},
}

FLOOR = 0.282            # измеренный пол шума метки, предзаявлен
N_SOLUTES, N_ROWS = 7, 298
BOOT = 10000
RNG = np.random.default_rng(20261027)


def load(path: Path, labels: pd.DataFrame) -> pd.DataFrame:
    d = pd.read_csv(path, low_memory=False)
    d = d[d["has_solubility"].astype(str).str.lower().isin({"true", "1", "1.0"})
          | (d["has_solubility"] == True)]  # noqa: E712
    keep = dict(zip(labels["solute_smiles"].astype(str), labels.index))
    d = d[d["solute_smiles"].astype(str).isin(keep)].copy()
    # МЕТКИ ТОЛЬКО ThermoML: значение сплита ЗАМЕНЯЕТСЯ, а не дополняется (предзаявка).
    lab = labels.set_index(labels["solute_smiles"].astype(str))
    d["T_m_split"], d["dH_fus_split"] = d["T_m"], d["dH_fus"]
    d["T_m"] = d["solute_smiles"].astype(str).map(lab["T_m"])
    d["dH_fus"] = d["solute_smiles"].astype(str).map(lab["dH_fus"])
    return annotate_compensation_frame(d, label=path.stem)


def main() -> int:
    labels = pd.read_csv(LABELS)
    labels = labels[labels["accepted"].astype(bool)].reset_index(drop=True)
    res: dict = {"floor_predeclared": FLOOR, "labels_source": "ThermoML only",
                 "n_accepted_labels": len(labels)}

    print("=" * 78)
    print("ВОРОТА 1 -- маска действительно расширилась")
    print("=" * 78)
    frames = {}
    g1 = True
    for seed, paths in PAIRS.items():
        for arm, p in paths.items():
            f = load(p, labels)
            frames[(seed, arm)] = f
            ns, nr = f["solute_canonical"].nunique(), len(f)
            ok = ns == N_SOLUTES and nr == N_ROWS
            g1 &= ok
            print(f"   сид {seed} {arm:8s}: растворяемых {ns}, строк {nr}  "
                  f"{'OK' if ok else 'ПРОВАЛ (нужно 7/298)'}")
    res["gate1_mask"] = bool(g1)
    if not g1:
        print("\nВОРОТА 1 ПРОВАЛЕНЫ -- по предзаявке чтение ОТМЕНЕНО")
        res["verdict"] = "CANCELLED_GATE1"
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf8")
        return 2

    print("\n" + "=" * 78)
    print("СВЕРКА КОНВЕЙЕРА (не ворота -- ворота 2 бессильны, см. docstring)")
    print("=" * 78)
    f = frames[(42, "base")]
    ph = f[f["solute_canonical"].str.contains("c1ccc2c", regex=False, na=False)]
    if len(ph):
        from tgnn_solv.diagnostics.compensation import compute_phi
        dcp = ph["dCp_fus_solver"] if "dCp_fus_solver" in ph else None
        phi_split = compute_phi(ph["T"], ph["T_m_split"], ph["dH_fus_split"], dcp)
        diff = (phi_split - ph["Phi_true"]).abs()
        print(f"   фенантрен, {len(ph)} строк: |Φ(сплит) − Φ(ThermoML)| медиана {diff.median():.3f}, "
              f"макс {diff.max():.3f}")
        print("   предзаявка вывела пол из ровно этой разницы: 0.282 медиана, 0.366 макс")
        res["pipeline_check_phenanthrene"] = {"median": float(diff.median()),
                                              "max": float(diff.max()), "n_rows": int(len(ph))}

    print("\n" + "=" * 78)
    print("ИЗМЕРЕНИЕ -- delta_phi_mean, построчное приведение")
    print("=" * 78)
    shifts = {}
    for seed in PAIRS:
        b, t = frames[(seed, "base")], frames[(seed, "treated")]
        mb, mt = float(b["delta_phi"].mean()), float(t["delta_phi"].mean())
        sh = mt - mb
        shifts[seed] = sh
        print(f"   сид {seed}: база {mb:+.4f}  плечо {mt:+.4f}  СДВИГ {sh:+.4f}")
        res[f"seed_{seed}"] = {"base": mb, "treated": mt, "shift": sh}

    print("\n" + "=" * 78)
    print("ПРАВИЛО, объявленное до чисел")
    print("=" * 78)
    conds = {}
    for seed in PAIRS:
        b, t = frames[(seed, "base")], frames[(seed, "treated")]
        # кластерный бутстрэп по РАСТВОРЯЕМЫМ (7 кластеров)
        sol = sorted(set(b["solute_canonical"]) & set(t["solute_canonical"]))
        gb = {s: b[b.solute_canonical == s]["delta_phi"].to_numpy(float) for s in sol}
        gt = {s: t[t.solute_canonical == s]["delta_phi"].to_numpy(float) for s in sol}
        draws = np.empty(BOOT)
        for i in range(BOOT):
            pick = RNG.choice(len(sol), size=len(sol), replace=True)
            bb = np.concatenate([gb[sol[j]] for j in pick])
            tt = np.concatenate([gt[sol[j]] for j in pick])
            draws[i] = tt.mean() - bb.mean()
        lo, hi = np.percentile(draws, [2.5, 97.5])
        excl = not (lo <= 0.0 <= hi)
        # складной нож по растворяемым
        jk = {}
        for s in sol:
            bj = np.concatenate([gb[x] for x in sol if x != s])
            tj = np.concatenate([gt[x] for x in sol if x != s])
            jk[s] = float(tj.mean() - bj.mean())
        signs_hold = all(np.sign(v) == np.sign(shifts[seed]) for v in jk.values())
        conds[seed] = {"ci95": [float(lo), float(hi)], "excludes_zero": bool(excl),
                       "above_floor": bool(abs(shifts[seed]) > FLOOR),
                       "jackknife": jk, "jackknife_sign_holds": bool(signs_hold),
                       "n_clusters": len(sol)}
        print(f"   сид {seed}: CI95 [{lo:+.4f}, {hi:+.4f}] исключает ноль: {excl}")
        print(f"            |сдвиг| {abs(shifts[seed]):.4f} > пол {FLOOR}: {abs(shifts[seed]) > FLOOR}")
        print(f"            складной нож по 7 растворяемым, знак держится: {signs_hold}")
        print("            " + "  ".join(f"{v:+.3f}" for v in jk.values()))
    sign_agree = np.sign(shifts[42]) == np.sign(shifts[43])
    print(f"\n   знак совпадает между парами: {sign_agree}  "
          f"({shifts[42]:+.4f} и {shifts[43]:+.4f})")

    informative = (sign_agree
                   and all(conds[s]["excludes_zero"] for s in PAIRS)
                   and all(conds[s]["above_floor"] for s in PAIRS)
                   and all(conds[s]["jackknife_sign_holds"] for s in PAIRS))
    verdict = "INFORMATIVE" if informative else "NOT_INFORMATIVE"
    res["conditions"] = {str(k): v for k, v in conds.items()}
    res["sign_agrees_across_pairs"] = bool(sign_agree)
    res["verdict"] = verdict
    res["bootstrap_honesty"] = ("7 кластеров: честность НЕ ИЗМЕРЕНА; проект мерил на 147 "
                                "(консервативен), 31 (антиконсервативен ~3x) и 1 (вырожден). "
                                "Вероятно антиконсервативен, степень неизвестна.")
    print("\n" + "=" * 78)
    print(f"ВЕРДИКТ: δΦ {'ИНФОРМАТИВЕН' if informative else 'НЕ ИНФОРМАТИВЕН'}")
    print("=" * 78)
    if not informative:
        print("  По предзаявке это ПОДТВЕРЖДАЕТ исходный негатив С МОЩНОСТЬЮ,")
        print("  что сильнее прежнего «закрыт как неразрешимый».")
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"\nзаписано: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
