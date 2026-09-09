#!/usr/bin/env python
"""Сборка ассетов сервиса из обучающих данных проекта.

Пишет два файла, которые сервис читает на старте:

  solvent_panel.json   — панель растворителей: SMILES, название, опора в обучающей выборке,
                         молярная масса и плотность при 298.15 K (или null, если её нет).
  train_domain.npz     — упакованные Morgan-фингерпринты уникальных растворяемых веществ
                         обучающей выборки; по ним считается область применимости.

ПОЧЕМУ ПАНЕЛЬ СОБИРАЕТСЯ, А НЕ ПИШЕТСЯ РУКАМИ. Сервис обязан предлагать только те
растворители, на которых модель обучалась, и порог опоры должен быть виден в коде, а не
жить в чьей-то памяти. Рукописный список устаревает молча: ровно так в этом проекте
список депозита Zenodo полгода называл семейство прогонов, из которого числа статьи
давно ушли.

    python way2drug/build_assets.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, rdFingerprintGenerator

RDLogger.DisableLog("rdApp.*")

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
TRAIN = ROOT / "notebooks/data/processed/train.csv"
DENSITIES = ROOT / "notebooks/data/raw/BigSolDBv2.1_densities.csv"

#: Растворитель попадает в панель, если модель видела его хотя бы с таким числом РАЗНЫХ
#: веществ. Считаем именно вещества, а не строки: тысяча измерений одного вещества при
#: разных температурах не учит модель этому растворителю.
MIN_DISTINCT_SOLUTES = 100

#: Температура, на которой сервис отвечает по умолчанию.
T_REF = 298.15
#: Насколько далеко от T_REF разрешено брать плотность.
T_TOL = 0.6

FP_RADIUS, FP_BITS = 2, 2048


def morgan_matrix(smiles: list[str]) -> tuple[np.ndarray, list[str]]:
    """Упакованные битовые фингерпринты и SMILES, для которых они построились."""
    gen = rdFingerprintGenerator.GetMorganGenerator(radius=FP_RADIUS, fpSize=FP_BITS)
    bits, kept = [], []
    for smi in smiles:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        arr = np.zeros(FP_BITS, dtype=np.uint8)
        for b in gen.GetFingerprint(mol).GetOnBits():
            arr[b] = 1
        bits.append(np.packbits(arr))
        kept.append(smi)
    return np.vstack(bits), kept


def main() -> int:
    if not TRAIN.exists():
        print(f"НЕТ ФАЙЛА: {TRAIN}\n  Обучающая выборка не сгенерирована; см. CLAUDE.md, "
              f"раздел про prepare_data.py.")
        return 1

    tr = pd.read_csv(TRAIN, low_memory=False)
    print(f"обучающая выборка: {len(tr)} строк, "
          f"{tr.solute_smiles.nunique()} веществ, {tr.solvent_smiles.nunique()} растворителей")

    # ---- панель растворителей ---------------------------------------------------------
    grp = (tr.groupby("solvent_smiles")
             .agg(rows=("solute_smiles", "size"),
                  solutes=("solute_smiles", "nunique"),
                  name=("solvent_name",
                        lambda s: s.dropna().mode().iat[0] if s.dropna().size else ""))
             .sort_values("solutes", ascending=False))
    panel = grp[grp.solutes >= MIN_DISTINCT_SOLUTES].copy()

    dens = pd.read_csv(DENSITIES)
    # ДЕСЯТИЧНАЯ ЗАПЯТАЯ. Часть строк таблицы плотностей записана как "0,86618", часть как
    # "0.86618" -- источники сливались из разных публикаций. float() на первой же запятой
    # падает, а pd.to_numeric без этой замены молча вернул бы NaN и растворитель тихо
    # остался бы без плотности.
    col = "Density_g/cm^3"
    dens[col] = pd.to_numeric(
        dens[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    near = dens[(dens["Temperature_K"] - T_REF).abs() <= T_TOL]
    dmap = {str(row.Solvent).strip().lower(): float(row[col])
            for _, row in near.iterrows() if pd.notna(row[col])}

    entries, no_density = [], []
    for smi, row in panel.iterrows():
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            print(f"  ПРОПУСК: RDKit не разобрал SMILES растворителя {smi!r}")
            continue
        name = str(row["name"]).strip()
        rho = dmap.get(name.lower())
        if rho is None:
            no_density.append(name or smi)
        entries.append({
            "smiles": smi,
            "name": name,
            "molar_mass_g_per_mol": round(float(Descriptors.MolWt(mol)), 4),
            "density_g_per_cm3_298K": rho,
            "train_rows": int(row["rows"]),
            "train_distinct_solutes": int(row["solutes"]),
        })

    out = {
        "reference_temperature_K": T_REF,
        "min_distinct_solutes": MIN_DISTINCT_SOLUTES,
        "built_from": str(TRAIN.relative_to(ROOT)),
        "n_solvents": len(entries),
        # Растворители без плотности остаются в панели: концентрацию в г/л для них
        # посчитать не из чего, но мольную долю модель предсказывает так же, и
        # выбрасывать их только ради одной колонки было бы хуже для пользователя.
        "solvents_without_density": sorted(no_density),
        "solvents": entries,
    }
    (HERE / "solvent_panel.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"панель: {len(entries)} растворителей "
          f"(без плотности: {', '.join(no_density) or 'нет'})")

    # ---- шаблон строки ------------------------------------------------------------------
    # Датасет читает из таблицы два десятка колонок (маски, вспомогательные метки,
    # температурные поля). Собирать их вручную -- значит второй раз описать формат, который
    # уже описан в коде датасета, и разойтись с ним при первом же изменении. Вместо этого
    # берём ОДНУ реальную строку и подменяем в ней SMILES с температурой.
    #
    # Она кладётся в ассеты, а не читается на лету: иначе сервису на платформе понадобилась
    # бы вся обработанная выборка ради одной строки, и он читал бы CSV на каждый запрос.
    template_src = ROOT / "notebooks/data/processed/test.csv"
    tmpl = pd.read_csv(template_src, nrows=1, low_memory=False)
    for col in ("solute_smiles", "solvent_smiles"):
        tmpl[col] = ""                      # чтобы никого не ввести в заблуждение остатком
    tmpl["ln_x2"] = 0.0
    tmpl.to_csv(HERE / "template_row.csv", index=False)
    print(f"шаблон строки: {len(tmpl.columns)} колонок")

    # ---- область применимости ---------------------------------------------------------
    solutes = sorted(tr.solute_smiles.dropna().astype(str).unique())
    mat, kept = morgan_matrix(solutes)

    # РАЗМЕР ХРАНИТСЯ ОТДЕЛЬНО, И ВОТ ПОЧЕМУ. Двоичный Morgan-фингерпринт радиуса 2 слеп
    # к длине молекулы: у полимера и его короткого олигомера включены одни и те же биты.
    # Измерено на этих ассетах: макроцикл C21 даёт Танимото 1.000 к циклопропану, ПЭГ-20 --
    # к тримеру ПЭГ, декапептид глицина -- 0.900 к дипептиду. Сходство одно, без второго
    # сторожа, объявило бы полимер «внутри области применимости».
    mw, heavy = [], []
    for smi in kept:
        mol = Chem.MolFromSmiles(smi)
        mw.append(float(Descriptors.MolWt(mol)))
        heavy.append(int(mol.GetNumHeavyAtoms()))
    mw_arr, heavy_arr = np.array(mw), np.array(heavy)
    # p1/p99, а не min/max: у хвоста обучающей выборки единичные молекулы до 1701 г/моль,
    # и по ним граница применимости была бы пустой формальностью.
    envelope = np.array([np.percentile(mw_arr, 1), np.percentile(mw_arr, 99),
                         np.percentile(heavy_arr, 1), np.percentile(heavy_arr, 99)])

    np.savez_compressed(HERE / "train_domain.npz", fingerprints=mat,
                        radius=FP_RADIUS, n_bits=FP_BITS, n=len(kept),
                        envelope=envelope)
    print(f"область применимости: {len(kept)} из {len(solutes)} веществ "
          f"({mat.nbytes/1e6:.1f} МБ упакованных фингерпринтов)")
    print(f"  обучающий конверт: M {envelope[0]:.0f}-{envelope[1]:.0f} г/моль, "
          f"тяжёлых атомов {envelope[2]:.0f}-{envelope[3]:.0f} (p1-p99)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
