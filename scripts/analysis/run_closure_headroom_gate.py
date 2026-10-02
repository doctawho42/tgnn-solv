#!/usr/bin/env python
"""Ворота E4: сколько запаса даёт ядро COSMO-SAC-2010 над 2002 на БОЛЬШОМ наборе.

ЗАЧЕМ. План outreach/ПЛАН_физичная_модель.md ставит переход на ядро 2010 последним и самым дорогим
экспериментом: слой CosmoSac2010Layer существует (layers.py:1678) и отдельно провалидирован, но в
модель НЕ подключён (solver.py:414 создаёт только 2002), голова даёт 51 нетипизированный бин вместо
153 типизированных, и потока супервизии для трёхканальных профилей нет. Три-пять недель работы.
Прежде чем их тратить, надо знать запас.

ЧТО УЖЕ БЫЛО. results/b_insuff/closure_variant_control.json меряет его на 60 сопоставленных парах:
MSE 1.2631 у 2002 против 0.7653 у 2010, срез 39%. Этого мало: n=60, и набор -- узкий,
VT-2005-сопоставленный. Здесь то же самое на 7888 записях PGL6ed, тех же, на которых измерен
основной результат статьи.

ЧИСТОТА СРАВНЕНИЯ. Оба ядра считаются ОДНОЙ реализацией (NIST cCOSMO, Bell et al. JCTC 2020) на
ОДНИХ профилях (база Delaware, UD). Меняется только ядро. Это и есть запас в чистом виде.
Сравнение с нашим собственным плечом (AAD 0.765 на профилях VT-2005 через наш слой) идёт отдельной
строкой и с оговоркой: там отличаются и реализация, и источник профилей, поэтому разницу нельзя
приписывать ядру.

ЧТЕНИЕ, ОБЪЯВЛЕННОЕ ДО ЧИСЕЛ.
  * 2010 срезает AAD заметно (скажем, на четверть и более) -> запас есть, E4 оправдан, и
    приоритет между E1 и E4 решается стоимостью, а не величиной.
  * 2010 срезает мало или не срезает -> три-пять недель не окупаются, E4 закрывается, и остаётся
    линия супервизии.
  * Покрытие базой UD мало (скажем, меньше половины записей) -> ворота не отвечают, и это надо
    сказать, а не выдать результат на огрызке.

    KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/run_closure_headroom_gate.py \
        --ud-dir ~/COSMOSAC/profiles/UD
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

RECORDS = ROOT / "results/published_idac_check/scored_records.csv"
OUT = ROOT / "results/closure_headroom"


def ud_resolver(ud_dir: Path):
    exact, by14 = {}, {}
    for ln in (ud_dir / "complist.txt").read_text().splitlines()[1:]:
        t = ln.split()
        if len(t) < 5:
            continue
        ik = t[-1]
        exact[ik] = ik
        by14.setdefault(ik.split("-")[0], ik)

    def resolve(smiles):
        m = Chem.MolFromSmiles(str(smiles))
        if m is None:
            return None
        k = Chem.MolToInchiKey(m)
        return exact.get(k) or by14.get(k.split("-")[0])
    return resolve


def metrics(m: np.ndarray, g: np.ndarray) -> dict:
    ok = np.isfinite(m) & np.isfinite(g)
    m, g = m[ok], g[ok]
    if m.size == 0:
        return {"n": 0}
    d = g - m
    return {"n": int(m.size), "aad": float(np.abs(d).mean()),
            "rmse": float(np.sqrt((d ** 2).mean())), "mse": float((d ** 2).mean()),
            "r2": float(1 - (d ** 2).sum() / ((m - m.mean()) ** 2).sum())}


def main() -> int:
    import cCOSMO
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ud-dir", type=Path, default=Path.home() / "COSMOSAC/profiles/UD")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    resolve = ud_resolver(a.ud_dir)
    db = cCOSMO.DelawareProfileDatabase(str(a.ud_dir / "complist.txt"),
                                        str(a.ud_dir / "sigma3") + "/")
    d = pd.read_csv(RECORDS)
    print(f"записей в наборе: {len(d)}")

    # разрешаем молекулы один раз, затем строим объект на ПАРУ (он от температуры не зависит)
    uniq = sorted(set(d.solute_smiles.astype(str)) | set(d.solvent_smiles.astype(str)))
    key = {s: resolve(s) for s in uniq}
    n_res = sum(v is not None for v in key.values())
    print(f"молекул {len(uniq)}, разрешено в базе UD: {n_res} ({100 * n_res / len(uniq):.1f}%)")

    d = d[[key.get(str(u)) is not None and key.get(str(v)) is not None
           for u, v in zip(d.solute_smiles, d.solvent_smiles)]].reset_index(drop=True)
    print(f"записей с обеими молекулами в UD: {len(d)}")
    if len(d) < 0.4 * 7888:
        print("  ВНИМАНИЕ: покрытие ниже 40% -- ворота отвечают на огрызок, читать осторожно")

    added, eps, rows, failed = set(), 1e-8, [], 0
    cache: dict[tuple[str, str], tuple] = {}
    for i, r in enumerate(d.itertuples()):
        su, sv = key[str(r.solute_smiles)], key[str(r.solvent_smiles)]
        try:
            for iden in (su, sv):
                if iden not in added:
                    db.add_profile(db.normalize_identifier(iden))
                    added.add(iden)
            if (su, sv) not in cache:
                cache[(su, sv)] = (cCOSMO.COSMO1([su, sv], db), cCOSMO.COSMO3([su, sv], db))
            c1, c3 = cache[(su, sv)]
            x = np.array([eps, 1 - eps])
            T = float(r.T_K)
            rows.append({"m": float(r.m), "solvent_smiles": str(r.solvent_smiles),
                         "g2002": float(c1.get_lngamma(T, x)[0]),
                         "g2010": float((c3.get_lngamma_comb(T, x)
                                         + c3.get_lngamma_resid(T, x))[0]),
                         "gdsp": float(c3.get_lngamma(T, x)[0])})
        except Exception:  # noqa: BLE001
            failed += 1
        if i and i % 2000 == 0:
            print(f"  ... {i}/{len(d)}", flush=True)
    print(f"посчитано {len(rows)}, отказов {failed}, уникальных пар {len(cache)}")

    t = pd.DataFrame(rows)
    m = t.m.to_numpy(float)
    res = {"n_records_scored": len(t), "n_pairs": len(cache),
           "molecules_resolved_in_ud": n_res, "molecules_total": len(uniq),
           "reference": "NIST cCOSMO (Bell et al. JCTC 2020), Delaware (UD) profile database",
           "closures": {}}
    print(f"\n{'ядро':<28}{'AAD':>9}{'RMSE':>9}{'MSE':>9}{'R2':>9}")
    for nm, col in (("COSMO-SAC-2002", "g2002"), ("COSMO-SAC-2010", "g2010"),
                    ("COSMO-SAC-2010+dsp", "gdsp")):
        e = metrics(m, t[col].to_numpy(float))
        res["closures"][col] = e
        print(f"{nm:<28}{e['aad']:>9.4f}{e['rmse']:>9.4f}{e['mse']:>9.4f}{e['r2']:>9.4f}")

    a2002 = res["closures"]["g2002"]["aad"]
    for col, nm in (("g2010", "2010"), ("gdsp", "2010+dsp")):
        cut = 1 - res["closures"][col]["aad"] / a2002
        res["closures"][col]["aad_cut_vs_2002"] = float(cut)
        print(f"\n  {nm} срезает AAD на {100 * cut:+.1f}% относительно 2002")

    print("\nдля сверки, ОТДЕЛЬНОЙ строкой и с оговоркой:")
    print("  наш слой, ядро 2002, профили VT-2005, 7888 записей: AAD 0.765")
    print("  (отличаются и реализация, и источник профилей -- разницу ядру не приписывать)")

    a.out.mkdir(parents=True, exist_ok=True)
    t.to_csv(a.out / "per_row.csv", index=False)
    (a.out / "summary.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    print(f"\nзаписано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
