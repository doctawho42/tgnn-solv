#!/usr/bin/env python3
"""Print the redone multiplicity null: both distributions, and where the findings fall."""
import json
from pathlib import Path

D = Path(__file__).resolve().parent
r = json.loads((D / "redo_null.json").read_text())
dep = json.loads(Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv/results/b_insuff/"
                      "crossfit_multiplicity_null.json").read_text())["nulls"]
old = json.loads(Path("/Users/nikitapolomosnov/PycharmProjects/tgnn-solv/results/b_insuff/"
                      "map_multiplicity_null.json").read_text())["null"]

B, C, S = r["bin8_473"], r["crossfit_473_pairfolds"], r["crossfit_473_sourcefolds"]
A477 = r["bin8_477"]
f = r["fidelity_rewrite_equals_original"]

print("=" * 96)
print("FIDELITY.  the rewritten search with sq=None vs run_b_insuff_map_multiplicity_null.search")
print(f"  per-draw statistics identical on all {f['n_draws_compared']} draws : "
      f"{f['all_identical']}      observed identical: {f['observed_identical']}")
print(f"  {'; '.join(k + '=' + str(v) for k, v in f['per_draw_statistics_identical'].items())}")

print("\n" + "=" * 96)
print("ANCHOR.  the 477-row null re-run with the ORIGINAL script's own search, unchanged")
o = A477["observed"]
print(f"  observed  A={o['A_cells_admissible']}  B={o['B_strata_admissible_in_every_cell']}  "
      f"C={o['C_distinct_row_sets_admissible_and_positive']}  "
      f"D={o['D_max_headline_margin_among_them']:.4f}  n_maximal={o['n_maximal']}")
print(f"  re-run    p_A={A477['p_A']}  p_B={A477['p_B']}  p_C={A477['p_C']}  p_D={A477['p_D']}")
print(f"  deposited p_A={old['A_cells_admissible']['p_at_least_observed']}  "
      f"p_B={old['B_strata_admissible_in_every_cell']['p_at_least_observed']}  "
      f"p_C={old['C_distinct_row_sets_admissible_and_positive']['p_at_least_observed']}  "
      f"p_D={old['D_max_headline_margin_among_them']['p_at_least_observed_over_all_draws']}")

print("\n" + "=" * 96)
print("THE TWO NULLS, 2000 draws, same seed, SAME permutations, same 473 rows")
print(f"{'':52s}{'8-bin coarsening':>20s}{'cross-fit (pair)':>20s}")
rows = [
    ("OBSERVED  A  cells admissible", "observed", "A_cells_admissible", "{:d}"),
    ("OBSERVED  B  strata admissible in all 4 cells", "observed",
     "B_strata_admissible_in_every_cell", "{:d}"),
    ("OBSERVED  C  distinct certified row sets", "observed",
     "C_distinct_row_sets_admissible_and_positive", "{:d}"),
    ("OBSERVED  D  largest certified margin", "observed",
     "D_max_headline_margin_among_them", "{:.4f}"),
    ("OBSERVED  n_maximal", "observed", "n_maximal", "{:d}"),
]
for lab, blk, key, fmt in rows:
    a, b = B[blk][key], C[blk][key]
    print(f"  {lab:50s}{fmt.format(a):>20s}{fmt.format(b):>20s}")
print()
for lab, key in (("NULL median A", "A_cells_admissible"),
                 ("NULL median B", "B_strata_admissible_in_every_cell"),
                 ("NULL median C", "C_distinct_row_sets_admissible_and_positive"),
                 ("NULL median n_maximal", "n_maximal")):
    print(f"  {lab:50s}{B['null_medians'][key]:>20.1f}{C['null_medians'][key]:>20.1f}")
print(f"  {'NULL draws certifying anything (C>=1)':50s}"
      f"{B['C_freq_at_least_one']:>19.1%}{C['C_freq_at_least_one']:>20.1%}")
print(f"  {'NULL draws certifying two (C>=2)':50s}"
      f"{B['C_freq_at_least_two']:>19.1%}{C['C_freq_at_least_two']:>20.1%}")
print(f"  {'NULL C distribution':50s}{str(B['C_distribution']):>20s}")
print(f"  {'':50s}{str(C['C_distribution']):>20s}")

print("\n  D among the draws that certify SOMETHING:")
qa, qb = B["D_quantiles_over_certifying_draws"], C["D_quantiles_over_certifying_draws"]
print(f"  {'draws with a certified cell':50s}"
      f"{B['n_draws_with_any_certified_cell']:>20d}{C['n_draws_with_any_certified_cell']:>20d}")
for p in ("5", "25", "50", "75", "90", "95", "99"):
    print(f"  {'  null D p' + p:50s}{qa[p]:>20.4f}{qb[p]:>20.4f}")
print(f"  {'  null D max':50s}{B['D_max']:>20.4f}{C['D_max']:>20.4f}")

print("\n  WHERE THE SURVIVING FINDING FALLS:")
print(f"  {'observed D':50s}"
      f"{B['observed']['D_max_headline_margin_among_them']:>20.4f}"
      f"{C['observed']['D_max_headline_margin_among_them']:>20.4f}")
print(f"  {'observed D  -  null median certified D':50s}"
      f"{B['D_observed_minus_null_median']:>+20.4f}{C['D_observed_minus_null_median']:>+20.4f}")
print(f"  {'p_D  over all draws':50s}{B['p_D']:>20.4f}{C['p_D']:>20.4f}")
print(f"  {'p_D  given a certified cell':50s}"
      f"{B['p_D_given_a_certified_cell']:>20.4f}{C['p_D_given_a_certified_cell']:>20.4f}")
print(f"  {'p_C':50s}{B['p_C']:>20.4f}{C['p_C']:>20.4f}")
print(f"  {'p_B':50s}{B['p_B']:>20.4f}{C['p_B']:>20.4f}")
print(f"  {'p_A':50s}{B['p_A']:>20.4f}{C['p_A']:>20.4f}")

print("\n  LIKE-FOR-LIKE, null rate at a FIXED threshold (the observed statistic also moved):")
for k in ("1", "2", "3"):
    fa = sum(v for kk, v in B["C_distribution"].items() if int(kk) >= int(k)) / B["n_draws"]
    fb = sum(v for kk, v in C["C_distribution"].items() if int(kk) >= int(k)) / C["n_draws"]
    print(f"  {'  P(null C >= ' + k + ')':50s}{fa:>20.4f}{fb:>20.4f}")

print("\n  THE NULL'S OWN PERMISSIVENESS DIAGNOSTIC (observed / null median):")
for lab, key in (("leave-one-source-out pass rate among boundable cells",
                  "loso_pass_rate_among_boundable_cells"),
                 ("cells boundable with a margin", "cells_boundable_with_a_margin"),
                 ("sources per boundable stratum", "median_sources_per_boundable_stratum")):
    pa, pb = B["permissiveness_diagnostic"], C["permissiveness_diagnostic"]
    print(f"  {lab:50s}{str(pa[key + '_observed']) + ' / ' + str(pa[key + '_null_median']):>20s}"
          f"{str(pb[key + '_observed']) + ' / ' + str(pb[key + '_null_median']):>20s}")

print("\n" + "=" * 96)
print("PAIRED (the same 2000 permutations drive both columns)")
p = r["paired_bin8_vs_crossfit"]
for k, v in p.items():
    if k != "note":
        print(f"  {k:50s}{v}")

print("\n" + "=" * 96)
print("THE CONSERVATIVE FOLD SCHEME (source-grouped; reported, never headlines)")
so = S["observed"]
print(f"  observed  A={so['A_cells_admissible']}  B={so['B_strata_admissible_in_every_cell']}  "
      f"C={so['C_distinct_row_sets_admissible_and_positive']}  "
      f"D={so['D_max_headline_margin_among_them']}  n_maximal={so['n_maximal']}")
print(f"  p_A={S['p_A']}  p_B={S['p_B']}  p_C={S['p_C']}  p_D={S['p_D']}")
print(f"  null draws certifying anything: {S['C_freq_at_least_one']:.1%}   "
      f"null median B={S['null_medians']['B_strata_admissible_in_every_cell']:.0f}")

print("\n" + "=" * 96)
print("REPLICATION of the deposited scoring pass (results/b_insuff/crossfit_multiplicity_null.json)")
for mine, tag in ((B, "bin8_473"), (C, "crossfit_473"), (S, "crossfit_473_source_folds")):
    d = dep[tag]
    ok = (abs(mine["p_C"] - d["p_C"]) < 5e-4
          and (mine["p_D"] is None) == (d["p_D"] is None)
          and (mine["p_D"] is None or abs(mine["p_D"] - d["p_D"]) < 5e-4))
    print(f"  {tag:26s} mine p_C={mine['p_C']:.4f} p_D={str(mine['p_D']):>7s}   "
          f"deposited p_C={d['p_C']:.4f} p_D={str(round(d['p_D'], 4) if d['p_D'] else d['p_D']):>7s}"
          f"   match={ok}")

print("\n" + "=" * 96)
print("VERDICT ARITHMETIC (declaration Sec. 4, W3 thresholds are the deposited 477-row values)")
print(f"  W3 needs  p_C < 0.286  AND  p_D < 0.1005")
print(f"  got       p_C = {C['p_C']}  ({'PASS' if C['p_C'] < 0.286 else 'FAIL'})"
      f"     p_D = {C['p_D']}  ({'PASS' if C['p_D'] < 0.1005 else 'FAIL'})")
print(f"  W3 passes: {C['p_C'] < 0.286 and C['p_D'] < 0.1005}")
