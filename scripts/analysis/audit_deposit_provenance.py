#!/usr/bin/env python
"""Какие депозиты результатов несут утверждение, но НЕ несут провенанса.

ЗАЧЕМ. 2026-10-23 выяснилось, что центральное сравнение проекта -- nrtl 1.795 против
directgnn 1.702 из `results/e5_sigma_grounding/THREE_SEED_SUMMARY.md` -- посчитано с CSV
предсказаний, у которых НЕТ ни манифеста, ни коммита, ни даты обучения, ни записи об окружении, и
которые к тому же не отслеживаются гитом. Узнать это удалось только прямым поиском. Этот скрипт
делает такой поиск воспроизводимым.

ТРИ УРОВНЯ, и различать их важно:
  * МАШИННЫЙ -- есть `*.manifest.json`, `run_meta.json` или `provenance.json`: провенанс можно
    прочитать программой и сверить.
  * ПРОЗА -- `RESULTS.md` называет чекпойнты И дату прогона. Человек восстановит, программа нет.
  * НЕТ -- ни того, ни другого. Утверждение неаудируемо.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

#: Файлы, наличие которых означает «здесь сделано утверждение».
CLAIM_FILES = ("RESULTS.md", "summary.json", "comparison.json", "reading.json")
CLAIM_GLOBS = ("*SUMMARY*.md", "*VERDICT*.json", "*verdict*.json")
#: Файлы машинного провенанса.
PROV_GLOBS = ("*.manifest.json", "run_meta.json", "provenance.json", "gate.json")
DATE = re.compile(r"20\d\d-\d\d-\d\d")
CKPT = re.compile(r"checkpoints?/[A-Za-z0-9_./{}-]+")


def classify(d: Path) -> dict:
    claims = [f.name for f in d.iterdir()
              if f.is_file() and (f.name in CLAIM_FILES
                                  or any(f.match(g) for g in CLAIM_GLOBS))]
    if not claims:
        return {}
    machine = sorted({f.name for g in PROV_GLOBS for f in d.glob(g)})
    prose_ck, prose_date = set(), set()
    for md in list(d.glob("*.md")):
        try:
            t = md.read_text(encoding="utf8", errors="replace")
        except OSError:
            continue
        prose_ck |= set(CKPT.findall(t))
        prose_date |= set(DATE.findall(t))
    if machine:
        level = "МАШИННЫЙ"
    elif prose_ck and prose_date:
        level = "ПРОЗА"
    else:
        level = "НЕТ"
    return {"claims": sorted(claims), "machine": machine, "level": level,
            "checkpoints_named": sorted(prose_ck)[:3], "dates_named": sorted(prose_date)[:2]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path("results"))
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--fail-on-none", action="store_true",
                    help="код 1, если есть депозиты уровня НЕТ -- для ворот в CI")
    a = ap.parse_args()

    rows: dict[str, dict] = {}
    for d in sorted(p for p in a.root.rglob("*") if p.is_dir()):
        info = classify(d)
        if info:
            rows[str(d)] = info

    by_level: dict[str, list[str]] = {"НЕТ": [], "ПРОЗА": [], "МАШИННЫЙ": []}
    for k, v in rows.items():
        by_level[v["level"]].append(k)

    print(f"депозитов с утверждениями: {len(rows)}")
    for lvl in ("НЕТ", "ПРОЗА", "МАШИННЫЙ"):
        print(f"  {lvl:10s} {len(by_level[lvl])}")
    if by_level["НЕТ"]:
        print("\n=== НЕАУДИРУЕМЫЕ (утверждение есть, провенанса нет) ===")
        for k in by_level["НЕТ"]:
            print(f"  {k}")
            print(f"      утверждения: {', '.join(rows[k]['claims'][:4])}")
    if by_level["ПРОЗА"]:
        print("\n=== ПРОЗА (человек восстановит, программа нет) ===")
        for k in by_level["ПРОЗА"]:
            ck = rows[k]["checkpoints_named"]
            print(f"  {k}  <- {ck[0] if ck else '?'}  {rows[k]['dates_named'][:1]}")

    if a.json_out:
        Path(a.json_out).write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    return 1 if (a.fail_on_none and by_level["НЕТ"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
