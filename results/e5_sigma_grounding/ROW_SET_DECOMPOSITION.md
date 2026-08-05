# The scored row set: 8103 -> 5608, decomposed

Backs the SI section "The scored row set, and why it is not arm-dependent" and the
§2.4 sentence that defines the lock. Regenerate from the per-row deposits in this
directory; nothing else is needed.

## The lock as the code builds it

`scripts/analysis/run_e5_comparison.py::intersection_keys` intersects, over arms,
the rows that are

1. unique on `(solute_smiles, solvent_smiles, round(T, 6))`  — arm-independent
2. `has_solubility == True`                                   — arm-independent
3. `np.isfinite(ln_x2_pred)`                                  — **per-arm, outcome-dependent**

Criterion (3) is the one that could bias the comparison: intersecting on it removes
from *every* arm's score the rows *some* arm failed on. The question this file
answers is whether it removes anything.

## Decomposition, identical at seeds 42, 43 and 44

| reason | rows |
|---|---|
| duplicate `(solute, solvent, T)` keys, second and later copies | 0 |
| `has_solubility == False` — a melting point, no solubility measurement | 2495 |
| non-finite `ln_x2_pred` in some arm | **0** |
| scored | 5608 |
| total test rows | 8103 |

No remainder. The 2495 unlabelled rows carry `ln_x2` as a placeholder `0.0`, all
2495 carry `has_T_m`, none is a self-solvation row, and 2487 of them carry water as
the nominal solvent field. They are unscorable for solubility in every arm, the
control included. `notebooks/data/processed/test.csv` agrees: `has_solubility` is
True on exactly 5608 of its 8103 rows.

## The finiteness clause is inert

Audited over **all 22 per-row prediction files** in `seed_{42,43,44}/` — the five
intersecting arms (`nrtl`, `directgnn`, `ungrounded`, `grounded_a`, `grounded_b`)
and `oracle` at each of the three seeds, plus `channel_swap`,
`grounded_a_truetrain`, `grounded_a_truetrain_residual` and
`grounded_a_truetrain_residual_v2` at seed 42:

- non-finite `ln_x2_pred`: **0 in every file**, over all 8103 rows and not merely
  the labelled ones;
- non-finite `ln_x2_true`: 0 in every file;
- 21 files are full length and each carries exactly 5608 labelled rows; the 22nd is
  the truncated `seed_44/oracle_predictions.csv` (295 rows, all finite), which the
  paper already discloses as a defective deposit;
- the five intersecting arms' labelled key sets are **identical as sets**, not
  merely equal in size, at every seed.

Consequently the lock computed with criterion (3) deleted is the same 5608 rows.

## What moves if the lock is made arm-independent

Nothing. Recomputing every arm's MAE and R² on the labelled rows with the
finiteness clause deleted reproduces `seed_*/comparison.json` exactly:

| arm | 3-seed MAE (ln x2) | sd (ddof=0) |
|---|---|---|
| directgnn | 1.702177 | 0.033014 |
| nrtl | 1.794975 | 0.070548 |
| grounded_a | 1.845723 | 0.053458 |
| grounded_b | 1.878810 | 0.091024 |
| ungrounded | 2.043394 | 0.039690 |
| oracle (seeds 42, 43 only) | 2.256495 | 0.024797 |

Largest per-arm, per-seed deviation from the deposited value: 1.1e-16 in R²
(floating-point summation order), 0 in MAE.

## Not the same event as saturation

Table 5 note *a* counts rows whose predicted `x_2` approaches 1, where the unit
conversion to log10 S diverges while `ln x_2` itself stays finite. Those rows are
inside the 5608 and are scored, under the clip that note discloses. They are not
counted here and are not removed by criterion (3).
