#!/usr/bin/env python3
"""Собрать таблицу посидовых значений для Supporting Information.

ЗАЧЕМ. Разбросы по сидам стояли в бегущей прозе статьи, где они делали текст плотным и
где вентиль их видел только поштучно. Перенести их руками в таблицу значило бы переписать
пятнадцать диапазонов -- ровно та операция, на которой этот проект уже ошибался
(округлил, потом вычел; собрал общий множитель не из тех чисел). Поэтому таблица
ГЕНЕРИРУЕТСЯ из тех же депозитов, из которых читает таблица 1 статьи, по ключу.

ЧТО ЗДЕСЬ НЕ ДЕЛАЕТСЯ. Ни одно значение не вычисляется заново: берутся посидовые ряды,
которые депозит уже содержит, и печатаются. Сводка (медиана, среднее, ст. откл.) считается
из того же ряда, так что заголовок в статье и ряд здесь не могут разойтись.

Запуск:
    python scripts/analysis/make_si_spread_table_tex.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/sections/tab-si-spread.tex"


def load(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        raise SystemExit(f"депозита нет: {rel}")
    return json.loads(p.read_text(encoding="utf8"))


def fmt(vals: list[float], places: int) -> str:
    """Посидовый ряд через дробную черту, в том порядке, в каком идут сиды."""
    return " / ".join(f"${v:.{places}f}$" for v in vals)


def build() -> tuple[str, list]:
    """Собрать .tex таблицы и ряды, из которых она собрана."""
    rank = load("results/closure_rank_profile_space/summary.json")
    floor = load("results/t2_softmax_floor/summary.json")
    costs = load("results/t2_softmax_floor/pedestal_costs.json")["per_seed"]
    attrib = load("results/per_bin_sensitivity_weights/closure_error_attribution.json")
    wts = load("results/per_bin_sensitivity_weights/summary.json")["by_rows"]
    refst = load("results/reference_state_violation/summary.json")["per_seed"]
    idac = load("results/idac_learned_vs_reference/summary.json")
    chan = load("results/e5_sigma_grounding/section_s1_channel_split.json")["summary"]["classes"]

    seeds_rank = sorted(rank["per_seed"], key=int)
    # число направлений: депозит даёт его на каждую пару сид-растворитель, в статье напечатана
    # медиана по всем клеткам, поэтому здесь печатается медиана внутри сида
    dirs = [st.median([c["dirs_for_99pct"] for c in rank["per_seed"][s].values()])
            for s in seeds_rank]
    dirs_all = [c["dirs_for_99pct"] for s in seeds_rank for c in rank["per_seed"][s].values()]

    fs = sorted(floor["per_seed"], key=int)
    ped_u = [floor["per_seed"][s]["solute"]["pedestal_median"] for s in fs]
    ped_v = [floor["per_seed"][s]["solvent"]["pedestal_median"] for s in fs]
    below = [100 * floor["per_seed"][s][r]["share_of_zero_bins_below_1e_5"]
             for s in fs for r in ("solute", "solvent")]

    rs = sorted(refst, key=int)
    med_abs = [refst[s]["median_abs_n30"] for s in rs]
    p95_abs = [refst[s]["p95_abs_n30"] for s in rs]

    cs = sorted(costs, key=int)
    fixnz = [100 * costs[s]["recovered_fix_nonzero"] for s in cs]
    zerop = [100 * costs[s]["recovered_zero_pedestal"] for s in cs]

    ats = sorted(attrib["per_seed"], key=int)
    worse = [100 * sum(1 for a in attrib["per_seed"][s]["null_aad"]
                       if a > attrib["per_seed"][s]["base_aad"])
             / len(attrib["per_seed"][s]["null_aad"]) for s in ats]
    rec_null = [100 * r for s in ats for r in attrib["per_seed"][s]["null_recovered"]]

    ids = sorted(idac["arms"]["learned"]["per_seed"], key=int)
    aad = [idac["arms"]["learned"]["per_seed"][s]["aad"] for s in ids]
    so = chan["solvent_only"]
    pen = [so["per_seed"][s] for s in sorted(so["per_seed"], key=int)]

    #: (величина, раздел статьи, посидовый ряд, сводка, как она напечатана в статье)
    rows = [
        (r"directions carrying $99\%$ of the information, median over solvents",
         "sec:determined",
         fmt(dirs, 0) + rf" (range ${min(dirs_all)}$--${max(dirs_all)}$ over all "
                        rf"${len(dirs_all)}$ seed-solvent cells)",
         rf"median ${int(st.median(dirs_all))}$"),
        (r"pedestal, solute role", "sec:pedestal", fmt(ped_u, 3),
         rf"${st.mean(ped_u):.3f}\pm{st.stdev(ped_u):.3f}$"),
        (r"pedestal, solvent role", "sec:pedestal", fmt(ped_v, 3),
         rf"${st.mean(ped_v):.3f}\pm{st.stdev(ped_v):.3f}$"),
        (r"share of reference-zero bins below $10^{-5}$ (\%), both roles",
         "sec:pedestal", fmt(sorted(below), 0),
         rf"median ${st.median(below):.0f}$, range ${min(below):.0f}$--${max(below):.0f}$"),
        (r"median $|\ln\gamma|$ of a molecule in itself", "sec:refstate", fmt(med_abs, 3),
         rf"median ${st.median(med_abs):.3f}$"),
        (r"ninety-fifth percentile of the same", "sec:refstate", fmt(p95_abs, 2),
         rf"median ${st.median(p95_abs):.2f}$"),
        (r"edge-to-core cost ratio, training rows", "sec:cost",
         fmt(wts["train"]["corner_over_core_per_seed"], 1),
         rf"median ${st.median(wts['train']['corner_over_core_per_seed']):.0f}$"),
        (r"edge-to-core cost ratio, scoring rows", "sec:cost",
         fmt(wts["idac"]["corner_over_core_per_seed"], 1),
         rf"median ${st.median(wts['idac']['corner_over_core_per_seed']):.0f}$"),
        (r"random third worse than the learned profile (\% of 20 draws)",
         "sec:nonadditive", fmt(worse, 0), rf"mean ${st.mean(worse):.0f}$"),
        (r"gap recovered by a random third (\%), $20\times$ seeds",
         "sec:nonadditive", rf"range ${min(rec_null):.0f}$ to $+{max(rec_null):.0f}$",
         rf"${st.mean(rec_null):+.0f}$ on average"),
        (r"gap recovered, reference into the nonzero bins (\%)", "sec:attribution",
         fmt(fixnz, 0), rf"mean ${st.mean(fixnz):+.0f}$"),
        (r"gap recovered, exact zeros into the zero bins (\%)", "sec:attribution",
         fmt(zerop, 0), rf"mean ${st.mean(zerop):+.0f}$, sign varies"),
        (r"activity-coefficient AAD, learned profile", "sec:twosided", fmt(aad, 3),
         rf"${st.mean(aad):.3f}\pm{st.stdev(aad):.3f}$"),
        (r"solubility penalty on the solvent-only rows", "sec:twosided", fmt(pen, 3),
         rf"${st.mean(pen):.3f}\pm{st.stdev(pen):.3f}$"),
    ]

    body = "".join(f"{q} & \\ref{{{sec}}} & {series} & {head} \\\\\n" for q, sec, series, head in rows)
    tex = (
        "% GENERATED by scripts/analysis/make_si_spread_table_tex.py. Do not edit by hand.\n"
        "% Каждый ряд читается из депозита по ключу; правка здесь разошлась бы с артефактом молча.\n"
        "\\begin{table*}[t]\n\\centering\n{\\footnotesize\n"
        "\\begin{tabular}{@{}p{0.34\\linewidth}c p{0.30\\linewidth}p{0.24\\linewidth}@{}}\n"
        "\\toprule\n"
        "quantity & Sec. & per seed & summary \\\\\n\\midrule\n"
        + body +
        "\\bottomrule\n\\end{tabular}}\n"
        "\\caption{Seed-by-seed values behind the quantities the article reports as a median, a "
        "mean or a range. Seeds are in ascending order, $42$ to $46$, except the last row, where "
        "the deposit carries three. Every series is read by key from the deposit the corresponding "
        "measurement was produced from, and the summary is computed from the series printed beside "
        "it, so a summary and its seeds cannot disagree. The summary is the statistic the article "
        "quotes for that quantity where it quotes one.}\n"
        "\\label{tab:si-spread}\n\\end{table*}\n")
    return tex, rows


def main() -> int:
    tex, rows = build()
    OUT.write_text(tex, encoding="utf8")
    print(f"записано: {OUT.relative_to(ROOT)}  ({len(rows)} строк)")
    for q, _, series, head in rows:
        print(f"  {q[:50]:52s} {head[:34]:36s} {series[:46]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
