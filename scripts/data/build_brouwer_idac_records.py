#!/usr/bin/env python
"""Собрать набор IDAC Брауэра в схему PGL6ed, чтобы его можно было прогнать тем же прибором.

ИСТОЧНИК. Brouwer, Kersten, Bargeman, Schuur, "Trends in solvent impact on infinite dilution
activity coefficients of solutes...", Sep. Purif. Technol. 272 (2021) 118727,
doi 10.1016/j.seppur.2021.118727. Открытая база в сопроводительных материалах: 77173 точки,
268 растворяемых, 692 растворителя, 243-556 K. Лист "Data Treatment" несёт gamma_inf,
экстра/интерполированную к 298.15 K по уравнению Вант-Гоффа, с ошибкой.

ЗАЧЕМ. results/idac_learned_vs_reference на наборе PGL6ed показал, что выученный sigma-профиль
хуже депонированного в 2.29 раза, и что вся деградация сидит в ВОДЕ (+2.44 против медианы -0.03
по остальным). Гипотезу «это непрерывная зависимость от доли водородносвязанной поверхности»
проверка на PGL6ed НЕ подтвердила: по корзинам доли HB медианы шли -0.631 / +0.561 / -0.003 /
+0.070 / +0.053, без дозовой зависимости, а выше 40% в корпусе стоит одна вода. Этот набор
добавляет независимые пары в диапазоне 0.05-0.36, включая глицерин и N-метилформамид, которых в
PGL6ed как растворителей не было.

ЧЕГО ОН НЕ ДАЁТ, И ЭТО НАДО НЕСТИ ВМЕСТЕ С НИМ. Разрыв у воды НЕ закрывается. В пересечении с
таблицей VT-2005 вода стоит на 0.675, следующий растворитель на 0.363, между ними пусто. Молекулы
таблицы выше 0.40 (пероксид водорода, гидроксиламин, формамид, гидразин, фосфорная кислота) не
являются практичными растворителями газожидкостной хроматографии, поэтому их нет ни в одной базе
IDAC. n=1 у режима воды -- свойство химии растворителей, а не пробел в данных.

ОТБОР СМЕЩЁН, И ЭТО НАЗВАНО. Имена Брауэра отображаются в SMILES по словарю имён PGL6ed
(results/published_idac_check/scored_records.csv), другого офлайн-источника имя->структура здесь
нет. Поэтому проходят преимущественно молекулы, которые в PGL6ed и так были: 41 растворитель из
451 и 119 растворяемых из 347. Новыми оказываются ПАРЫ (208 из 487), а не молекулы. Считать это
независимой репликацией по молекулам нельзя; по парам и по источнику измерений -- можно.

    python scripts/data/build_brouwer_idac_records.py --xlsx /path/to/mmc1.xlsx
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from tgnn_solv.data.utils import canonicalize              # noqa: E402
from tgnn_solv.sigma_oracle import load_sigma_profiles     # noqa: E402

PROFILES = ROOT / "results/sigma_profile_artifact/sigma_profiles.csv"
PGL = ROOT / "results/published_idac_check/scored_records.csv"
OUT = ROOT / "results/idac_brouwer"
T_REF = 298.15


def _norm(s: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xlsx", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    d = pd.read_excel(a.xlsx, sheet_name="Data Treatment")
    d.columns = ["solvent", "type", "solute", "n_pts", "T_min", "T_max",
                 "gamma_inf", "err_g", "H_inf", "err_H", "S_inf", "err_S"]
    n_all = len(d)
    d = d[(d["type"] == 1) & d["gamma_inf"].notna()]        # только молекулярные растворители
    d = d[d["gamma_inf"] > 0]
    print(f"строк в листе: {n_all};  молекулярных с положительным gamma_inf: {len(d)}")

    pgl = pd.read_csv(PGL)
    name2smi: dict[str, str] = {}
    for col_n, col_s in (("solute_name", "solute_smiles"), ("solvent_name", "solvent_smiles")):
        for nm, smi in zip(pgl[col_n].astype(str), pgl[col_s].astype(str)):
            name2smi[_norm(nm)] = smi
    d["solute_smiles"] = [name2smi.get(_norm(s)) for s in d["solute"]]
    d["solvent_smiles"] = [name2smi.get(_norm(s)) for s in d["solvent"]]
    d = d[d["solute_smiles"].notna() & d["solvent_smiles"].notna()]

    table = load_sigma_profiles(str(PROFILES), n_bins=51)
    keep = [(canonicalize(str(u)) in table) and (canonicalize(str(v)) in table)
            for u, v in zip(d["solute_smiles"], d["solvent_smiles"])]
    d = d[keep].reset_index(drop=True)

    out = pd.DataFrame({
        "solute_smiles": d["solute_smiles"], "solvent_smiles": d["solvent_smiles"],
        "solute_name": d["solute"], "solvent_name": d["solvent"],
        "T_K": T_REF, "gamma_inf_exp": d["gamma_inf"], "m": np.log(d["gamma_inf"]),
        "err_gamma": d["err_g"], "n_source_points": d["n_pts"],
        "T_min_source": d["T_min"], "T_max_source": d["T_max"],
        "aqueous": [canonicalize(str(v)) == canonicalize("O") for v in d["solvent_smiles"]],
        "record_set": "Brouwer2021",
    })
    a.out.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out / "records.csv", index=False)

    pgl_pairs = {(canonicalize(str(u)), canonicalize(str(v)))
                 for u, v in zip(pgl["solute_smiles"], pgl["solvent_smiles"])}
    new_pairs = {(canonicalize(str(u)), canonicalize(str(v)))
                 for u, v in zip(out["solute_smiles"], out["solvent_smiles"])}
    summary = {
        "source": "Brouwer et al., Sep. Purif. Technol. 272 (2021) 118727, "
                  "doi 10.1016/j.seppur.2021.118727, SI sheet 'Data Treatment'",
        "gamma_at_K": T_REF,
        "n_records": int(len(out)), "n_solvents": int(out["solvent_smiles"].nunique()),
        "n_solutes": int(out["solute_smiles"].nunique()),
        "pairs_shared_with_pgl6ed": len(new_pairs & pgl_pairs),
        "pairs_new_vs_pgl6ed": len(new_pairs - pgl_pairs),
        "mapping": "name -> SMILES via the PGL6ed name vocabulary; SELECTION IS BIASED toward "
                   "molecules PGL6ed already carried -- new PAIRS, largely familiar MOLECULES",
        "water_gap": "water sits at HB fraction 0.675; the next solvent in the VT-2005 "
                     "intersection is 0.363. The gap is a property of solvent chemistry, not of "
                     "this database: nothing above 0.40 is a practical GLC solvent.",
    }
    (a.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                        encoding="utf8")
    print(f"записей {len(out)}, растворителей {summary['n_solvents']}, "
          f"растворяемых {summary['n_solutes']}")
    print(f"  общих пар с PGL6ed {summary['pairs_shared_with_pgl6ed']}, "
          f"новых {summary['pairs_new_vs_pgl6ed']}")
    print(f"записано: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
