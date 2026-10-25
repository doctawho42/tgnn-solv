#!/usr/bin/env python3
"""Apply the pre-declared reading rule to the oracle-side segment sweep.

WRITTEN BEFORE THE NUMBERS EXISTED, which is the point: the rule in
``results/oracle_segment_sweep/PRE_DECLARATION.md`` is applied by this script and not by eye.

It answers one question.  The article reports a substitution contrast of +0.41 in ln x2 MAE,
measured at ``cosmo_sac_gamma_iter_eval = 30``.  The learned profile converges about twice as slowly
as the tabulated one, so the count can move the two arms by DIFFERENT amounts, and then part of the
contrast is an artifact of the count.  Both arms are re-scored on the same five frozen checkpoints
over the same 5608 labelled rows, through the same code path.

THE GATE RUNS FIRST AND IS FATAL.  At n=30 the oracle sweep must reproduce the deposited oracle arm
per seed to 1e-3; the deposited values are read out of ``block1_cells.json`` rather than typed here.
A failure means the deposited arm came from a different path, and then the +0.41 denominator is not
measured by this instrument -- so the reading is cancelled rather than reported with a caveat.

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/read_oracle_segment_sweep.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ORACLE = ROOT / "results/oracle_segment_sweep/summary.json"
LEARNED = ROOT / "results/segment_convergence/summary.json"
CELLS = ROOT / "results/e5_sigma_grounding_leakfree/block1_cells.json"
OUT = ROOT / "results/oracle_segment_sweep/reading.json"

GATE_TOL = 1e-3          # pre-declared
LARGE = 0.05             # pre-declared: |delta(300) - delta(30)| at or above this is "large"
EVAL_COUNT, CONVERGED = "30", "300"


def main() -> int:
    for p in (ORACLE, LEARNED, CELLS):
        if not p.exists():
            print(f"нет файла: {p}")
            return 1
    orc = json.loads(ORACLE.read_text())["part_b"]
    lrn = json.loads(LEARNED.read_text())["part_b"]
    cells = json.loads(CELLS.read_text())
    seeds = [str(s) for s in cells["seeds"]]
    deposited = dict(zip(seeds, cells["cells"]["oracle"]["mae"]["per_seed"]))

    print("=" * 78)
    print("ВОРОТА -- воспроизводит ли развёртка депонированное плечо при n=30")
    print("=" * 78)
    gate = {}
    failed = []
    for s in seeds:
        got = orc["mae_per_seed"][s][EVAL_COUNT]
        want = deposited[s]
        d = abs(got - want)
        gate[s] = {"recomputed": got, "deposited": want, "abs_diff": d, "pass": d < GATE_TOL}
        print(f"  сид {s}: пересчитано {got:.6f}  депонировано {want:.4f}  |Δ|={d:.2e}"
              f"  {'OK' if d < GATE_TOL else 'ПРОВАЛ'}")
        if d >= GATE_TOL:
            failed.append(s)
    if failed:
        print(f"\nВОРОТА НЕ ПРОЙДЕНЫ на сидах {failed}. По предзаявке чтение ОТМЕНЕНО:")
        print("депонированное плечо получено другим путём, и знаменатель +0.41 измерен не этим")
        print("прибором. Расхождение само есть находка; Δ(n) публиковать нельзя.")
        OUT.write_text(json.dumps({"gate": gate, "reading": "CANCELLED"},
                                  ensure_ascii=False, indent=2), encoding="utf8")
        return 2
    print("  ворота пройдены на всех сидах\n")

    counts = [c for c in orc["mae_per_seed"][seeds[0]] if c in lrn["mae_per_seed"][seeds[0]]]
    counts = sorted(counts, key=int)
    print("=" * 78)
    print("КОНТРАСТ Δ(n) = MAE_подстановка(n) − MAE_выученный(n)")
    print("=" * 78)
    print(f"{'n':>6}{'подстановка':>14}{'выученный':>12}{'Δ':>10}   посидово")
    delta: dict[str, dict] = {}
    for c in counts:
        o = np.array([orc["mae_per_seed"][s][c] for s in seeds])
        ln = np.array([lrn["mae_per_seed"][s][c] for s in seeds])
        d = o - ln
        delta[c] = {"oracle_mean": float(o.mean()), "learned_mean": float(ln.mean()),
                    "delta_mean": float(d.mean()), "delta_per_seed": [float(x) for x in d],
                    "delta_sd": float(d.std(ddof=0))}
        print(f"{c:>6}{o.mean():>14.4f}{ln.mean():>12.4f}{d.mean():>10.4f}   "
              + " ".join(f"{x:+.3f}" for x in d))

    d30 = np.array(delta[EVAL_COUNT]["delta_per_seed"])
    d300 = np.array(delta[CONVERGED]["delta_per_seed"])
    shift = d300 - d30
    mean_shift = float(shift.mean())
    same_dir = int((np.sign(shift) == np.sign(mean_shift)).sum())
    lo, hi = float(shift.min()), float(shift.max())

    print("\n" + "=" * 78)
    print("ПРАВИЛО, объявленное до чисел")
    print("=" * 78)
    print(f"  Δ(30)  = {d30.mean():+.4f}   посидово " + " ".join(f"{x:+.3f}" for x in d30))
    print(f"  Δ(300) = {d300.mean():+.4f}   посидово " + " ".join(f"{x:+.3f}" for x in d300))
    print(f"  сдвиг контраста Δ(300)−Δ(30) = {mean_shift:+.4f}"
          f"   ({abs(mean_shift) / delta[EVAL_COUNT]['delta_mean'] * 100:+.1f}% от Δ(30))")
    print("  посидово: " + " ".join(f"{x:+.4f}" for x in shift))
    print(f"  в одну сторону: {same_dir} из {len(seeds)}   диапазон по сидам [{lo:+.4f}, {hi:+.4f}]"
          f"   {'НАСЧИТЫВАЕТ НУЛЬ' if lo < 0 < hi else 'нуль вне диапазона'}")

    verdict = "COUNT_SENSITIVE" if abs(mean_shift) >= LARGE else "COUNT_INSENSITIVE"
    widens = mean_shift > 0
    print(f"\n  |сдвиг| {abs(mean_shift):.4f} против порога {LARGE}  ->  {verdict}")
    if verdict == "COUNT_INSENSITIVE":
        print("  Фраза о неизмеренности в §S1 заменяется этим числом; раскрытие закрывается.")
    else:
        print("  Контраст чувствителен к счётчику. Это ограничение на ГОЛОВНОЕ число, не сноска.")
    print("  направление: сходимость "
          + ("РАСШИРЯЕТ контраст -- головное число консервативно" if widens
             else "СУЖАЕТ контраст -- в статье должна стоять сошедшаяся величина"))
    if same_dir < 4:
        print(f"  ВНИМАНИЕ: согласие {same_dir}/5 -- сдвиг среднего направлением НЕ называется")

    OUT.write_text(json.dumps({
        "gate": gate, "gate_tolerance": GATE_TOL, "large_threshold": LARGE,
        "seeds": seeds, "delta_by_count": delta,
        "contrast_shift_30_to_converged": {
            "mean": mean_shift, "per_seed": [float(x) for x in shift],
            "seeds_same_direction": same_dir, "range": [lo, hi],
            "straddles_zero": bool(lo < 0 < hi)},
        "verdict": verdict,
        "direction": "widens" if widens else "narrows",
        "oracle_coverage": orc.get("oracle_coverage"),
    }, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"\nзаписано: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
