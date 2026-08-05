import json, hashlib
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path('/Users/nikitapolomosnov/PycharmProjects/tgnn-solv')
OUT = ROOT/'results'/'b_insuff'
t = pd.read_csv(OUT/'crossfit_map_table.csv')
nul = json.loads((OUT/'crossfit_multiplicity_null.json').read_text())
mp  = json.loads((OUT/'crossfit_map.json').read_text())
h = t[(t.set=='broad_473')&(t.fold_scheme=='pair')&(t.model=='rf')]
row_res = h[(h.unit=='row')&(h.convention=='res')]
B_cf = float(row_res[row_res.stratum=='all'].b_insuff_cf.iloc[0])
B_bin_res = float(row_res[row_res.stratum=='all'].b_insuff_bin.iloc[0])
B_bin_full = float(h[(h.unit=='row')&(h.convention=='full')&(h.stratum=='all')].b_insuff_bin.iloc[0])
n0, n1 = nul['nulls']['bin8_473'], nul['nulls']['crossfit_473']
verdict = {
 "declaration": {"file": "scripts/analysis/run_b_insuff_crossfit_estimator.py",
                 "sha256": mp['declaration']['sha256'],
                 "scoring_pass": "scripts/analysis/run_b_insuff_crossfit_scoring.py",
                 "scoring_sha256": hashlib.sha256(
                     (ROOT/'scripts/analysis/run_b_insuff_crossfit_scoring.py').read_bytes()).hexdigest()},
 "gate": mp['gate'],
 "W1_bound_tightens_globally": {
     "B_insuff_cf": B_cf, "B_insuff_bin_res": B_bin_res, "B_insuff_bin_full": B_bin_full,
     "cf_minus_bin_res": B_cf - B_bin_res, "cf_minus_bin_full": B_cf - B_bin_full,
     "passes": bool(B_cf < B_bin_res and B_cf < B_bin_full)},
 "W2_map_gains": {"C_bin_473": n0['observed']['C_distinct_row_sets_admissible_and_positive'],
                  "C_cf_473": n1['observed']['C_distinct_row_sets_admissible_and_positive'],
                  "C_baseline_477": 2,
                  "passes": bool(n1['observed']['C_distinct_row_sets_admissible_and_positive'] > 2)},
 "W3_null_does_not_move_proportionally": {
     "p_C_cf": n1['p_C'], "p_C_threshold": 0.286, "p_C_improves": bool(n1['p_C'] < 0.286),
     "p_D_cf": n1['p_D'], "p_D_threshold": 0.1005, "p_D_improves": bool(n1['p_D'] < 0.1005),
     "p_C_bin_473": n0['p_C'], "p_D_bin_473": n0['p_D'],
     "p_D_given_certified_bin": n0['p_D_given_a_certified_cell'],
     "p_D_given_certified_cf": n1['p_D_given_a_certified_cell'],
     "passes": bool(n1['p_C'] < 0.286 and n1['p_D'] < 0.1005)},
 "I3_fold_schemes_agree_on_sign_of_change_in_C": {
     "C_bin": 2, "C_cf_pair_folds": 1, "C_cf_source_folds":
        nul['nulls']['crossfit_473_source_folds']['observed'][
            'C_distinct_row_sets_admissible_and_positive'],
     "agree": True},
 "VERDICT": "LOSS / L1",
 "verdict_reason": ("W1 fails: the cross-fitted bound is LOOSER than the 8-bin coarsening on the "
                    "same 473 rows (0.8557 vs 0.7043 res / 0.4890 full), so under the "
                    "declaration's unconditional headline rule every margin shrinks and "
                    "certifications are lost.  L2 fires independently (C: 2 -> 1)."),
}
(OUT/'crossfit_verdict.json').write_text(json.dumps(verdict, indent=2))
print(json.dumps(verdict, indent=2))
