#!/usr/bin/env python
"""Обогащение σ-остатка на ЧИСТОМ пуле, как машинно-читаемый депозит.

ЗАЧЕМ. `results/sigma_profile_residual/summary.json` несёт снятые числа: его пул собран фильтром
`ln_x2.notna()`, который впустил 2495 вспомогательных строк с `ln_x2` РОВНО 0.0 вместо NaN
(`results/row_filter_audit/`), и 55 из 126 молекул депозита не встречаются ни в одной размеченной
тестовой строке. Поправленные значения существуют только прозой, в таблице внутри SUPERSEDED.md.
Число, которое печатает статья, обязано быть привязано к данным, а не к абзацу в снимающей заметке,
поэтому здесь оно пересчитывается из `per_molecule.csv` с правильным отбором и кладётся рядом.

ВОРОТА. Пересчёт обязан воспроизвести четыре значения, которые SUPERSEDED.md называет чистыми
(3.97 / 2.03 / 0.88 донорное, акцепторное и неполярное у растворяемого и 3.78 донорное у
растворителя). Если не воспроизводит, расходится либо отбор, либо смысл колонок, и печатать нельзя
ни то, ни другое.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/read_sigma_residual_clean_pool.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from tgnn_solv.data.utils import canonicalize  # noqa: E402

DEP = ROOT / "results/sigma_profile_residual"
TEST = ROOT / "notebooks/data/processed/test.csv"
EXPECT = {("solute", "donor"): 3.97, ("solute", "acceptor"): 2.03,
          ("solute", "nonpolar"): 0.88, ("solvent", "donor"): 3.78}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dep", type=Path, default=DEP,
                    help="каталог с per_molecule.csv; по умолчанию референсное плечо")
    ap.add_argument("--label", default="reference", help="как назвать плечо в депозите")
    a = ap.parse_args()
    dep = a.dep
    # ВОРОТА ТОЛЬКО ДЛЯ РЕФЕРЕНСНОГО ПЛЕЧА: ожидаемые четыре значения измерены на нём, и
    # применять их к другому плечу значило бы гейтить не ту поверхность.
    gate_on = dep.resolve() == DEP.resolve()
    d = pd.read_csv(dep / "per_molecule.csv")
    t = pd.read_csv(TEST, low_memory=False)
    if "has_solubility" not in t.columns:
        raise SystemExit("test.csv без has_solubility: отбор по ln_x2.notna() и есть тот дефект")
    lab = t[t["has_solubility"].astype(bool)]
    keep = {canonicalize(str(s)) for s in pd.concat([lab.solute_smiles, lab.solvent_smiles])}
    d["key"] = [canonicalize(str(s)) for s in d.smiles]
    clean = d[d["key"].isin(keep)].copy()
    n_all, n_clean = d["key"].nunique(), clean["key"].nunique()
    print(f"молекул в депозите {n_all}, из них встречаются в РАЗМЕЧЕННОЙ тестовой строке {n_clean}")

    res = {"n_molecules_deposit": int(n_all), "n_molecules_clean": int(n_clean),
           "seeds": sorted(int(s) for s in d.seed.unique()), "median_enrichment": {}}
    bad = []
    for role in ("solute", "solvent"):
        res["median_enrichment"][role] = {}
        for region in ("donor", "acceptor", "nonpolar"):
            col = f"enrichment_{region}_{role}"
            if col not in clean.columns:
                continue
            v = float(np.median(clean[col].astype(float).dropna()))
            res["median_enrichment"][role][region] = v
            want = EXPECT.get((role, region)) if gate_on else None
            mark = ""
            if want is not None:
                ok = abs(v - want) < 0.02
                mark = f"  ворота: {want} {'ok' if ok else 'РАСХОДИТСЯ'}"
                if not ok:
                    bad.append(f"{role}/{region}: {v:.3f} против {want}")
            print(f"  {role:8s} {region:9s} медиана обогащения {v:.3f}{mark}")
    if bad:
        raise SystemExit("ворота не прошли: " + "; ".join(bad))
    (dep / "clean_pool.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                         encoding="utf8")
    res["arm"] = a.label
    print(f"\nзаписано: {dep / 'clean_pool.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
