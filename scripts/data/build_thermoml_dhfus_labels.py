#!/usr/bin/env python
"""Собрать измеренные `dH_fus` из ThermoML для запертых растворяемых теста, с ФИЗИЧЕСКИМИ воротами.

ЗАЧЕМ. δΦ записан как «закрытый, неразрешимый этим корпусом»: маска `compensation_row_mask`
требует измеренных И `T_m`, И `dH_fus`, а последний в обработанном сплите есть у ОДНОЙ молекулы
(фенантрен, 18 строк). Один кластер -- бутстрэп вырожден, и вывод был закрыт.

Но корпус не был исчерпан: исчерпан был обработанный СПЛИТ. `results/thermoml_crystal/`, извлечённый
2026-10 из 3721 файла ThermoML, несёт **473 растворяемых с совместными T_m и dH_fus**, и 8 из них
лежат среди запертых 147. То есть закрытие было преждевременным -- ровно тот случай, про который
в CLAUDE.md сказано различать «не держится» и «никогда не устанавливалось».

ЧТО ЭТО НЕ ЕСТЬ. Метки предназначены для ДИАГНОСТИКИ (δΦ считается против них), а не для обучения.
Это строки ТЕСТА: использовать их как обучающий сигнал было бы утечкой. Скрипт помечает выход
`usage: diagnostic_only`, чтобы граница была в самом артефакте, а не только в чьей-то памяти.

ВОРОТА, две независимые:
  1. СОГЛАСИЕ ИСТОЧНИКОВ -- при n_dois >= 2 относительный разброс std/dH_fus не должен превышать
     порога; одно-источниковые помечаются отдельно, а не выбрасываются молча.
  2. ЭНТРОПИЯ ПЛАВЛЕНИЯ dS = dH_fus / T_m должна лежать в физичном окне. Для органических твёрдых
     правило Уолдена даёт около 56 Дж/моль/К при широком разбросе; окно взято 20..110, и выход за
     него означает, что величина скорее не энтальпия плавления (сублимация, переход фазы, опечатка
     порядка).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tgnn_solv.data.utils import canonicalize  # noqa: E402

#: Окно энтропии плавления, Дж/моль/К. Правило Уолдена ~56; окно щедрое с обеих сторон.
DS_MIN, DS_MAX = 20.0, 110.0
#: Относительный разброс между источниками, выше которого метка признаётся спорной.
REL_STD_MAX = 0.15


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", type=Path, default=ROOT / "notebooks/data/processed/test.csv")
    ap.add_argument("--thermoml", type=Path,
                    default=ROOT / "results/thermoml_crystal/thermoml_crystal_aggregated.csv")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "results/thermoml_dhfus_labels")
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)

    test = pd.read_csv(a.test, low_memory=False)
    locked = test[test["has_solubility"].astype(bool)].copy()
    locked["can"] = locked["solute_smiles"].map(lambda s: canonicalize(str(s)))
    locked_solutes = set(locked["can"].dropna())
    already = set(locked.loc[locked["has_dH_fus"].astype(bool), "can"].dropna())

    ag = pd.read_csv(a.thermoml)
    ag["can"] = ag["solute_smiles"].map(lambda s: canonicalize(str(s)))
    cand = ag[ag["can"].isin(locked_solutes) & ag["dH_fus"].notna()
              & ag["T_m"].notna()].copy()

    cand["dS_fus"] = cand["dH_fus"] / cand["T_m"]
    cand["rel_std"] = (cand["dH_fus_std"] / cand["dH_fus"]).where(
        cand["dH_fus_n_dois"].fillna(0) >= 2)
    cand["gate_entropy"] = cand["dS_fus"].between(DS_MIN, DS_MAX)
    cand["gate_agreement"] = cand["rel_std"].isna() | (cand["rel_std"] <= REL_STD_MAX)
    cand["single_source"] = cand["dH_fus_n_dois"].fillna(0) < 2
    cand["accepted"] = cand["gate_entropy"] & cand["gate_agreement"]
    cand["already_labelled"] = cand["can"].isin(already)

    keep = ["solute_smiles", "can", "solute_name", "T_m", "dH_fus", "dS_fus",
            "dH_fus_n_measurements", "dH_fus_n_dois", "dH_fus_std", "rel_std",
            "gate_entropy", "gate_agreement", "single_source", "accepted",
            "already_labelled", "dH_fus_example_doi", "dH_fus_protocol"]
    out = cand[[c for c in keep if c in cand.columns]].sort_values("dS_fus")
    out.to_csv(a.out_dir / "candidate_labels.csv", index=False)

    acc = out[out["accepted"]]
    rows_gained = locked[locked["can"].isin(set(acc["can"]))]
    summary = {
        "usage": "diagnostic_only -- это строки ТЕСТА; обучать на них было бы утечкой",
        "source": str(a.thermoml.relative_to(ROOT)),
        "thermoml_joint_solutes_total": int(ag["dH_fus"].notna().sum()),
        "locked_solutes": len(locked_solutes),
        "already_measured_solutes": len(already),
        "already_measured_rows": int(locked["has_dH_fus"].astype(bool).sum()),
        "candidates": int(len(out)),
        "accepted": int(len(acc)),
        "rejected_entropy": int((~out["gate_entropy"]).sum()),
        "rejected_agreement": int((~out["gate_agreement"]).sum()),
        "single_source_among_accepted": int(acc["single_source"].sum()),
        "solutes_after": len(set(acc["can"]) | already),
        "rows_after": int(len(rows_gained) | 0) if len(rows_gained) else 0,
        "gates": {"dS_window_J_per_mol_K": [DS_MIN, DS_MAX], "rel_std_max": REL_STD_MAX},
    }
    summary["rows_after"] = int(len(rows_gained))
    (a.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print(f"запертых растворяемых: {summary['locked_solutes']}; "
          f"сейчас с измеренным dH_fus: {summary['already_measured_solutes']} "
          f"({summary['already_measured_rows']} строк)")
    print(f"\nкандидатов из ThermoML: {len(out)}")
    print(f"{'dS':>7}{'dH_fus':>9}{'T_m':>8}{'DOI':>5}{'отн.std':>9}  ворота            название")
    for _, r in out.iterrows():
        g = ("ok" if r["accepted"] else
             ("ЭНТРОПИЯ" if not r["gate_entropy"] else "СОГЛАСИЕ"))
        rs = f"{r['rel_std']:.2f}" if pd.notna(r.get("rel_std")) else "один"
        mark = " (уже была)" if r["already_labelled"] else ""
        print(f"{r['dS_fus']:>7.1f}{r['dH_fus']:>9.0f}{r['T_m']:>8.1f}"
              f"{int(r['dH_fus_n_dois']):>5}{rs:>9}  {g:<17} {str(r.get('solute_name'))[:22]}{mark}")
    print(f"\nпринято: {summary['accepted']}  (отклонено по энтропии {summary['rejected_entropy']}, "
          f"по согласию {summary['rejected_agreement']})")
    print(f"из принятых одно-источниковых: {summary['single_source_among_accepted']}")
    print(f"\nбыло: {summary['already_measured_solutes']} растворяемых / "
          f"{summary['already_measured_rows']} строк")
    print(f"станет: {summary['solutes_after']} растворяемых / {summary['rows_after']} строк")
    print(f"\nзаписано: {a.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
