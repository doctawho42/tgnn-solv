# The closure-damage ladder: it does not order the effect, and here is what killed it

2026-08-11. Pre-registration: `PREREGISTRATION.md` in this directory, written before any penalty
was computed. Nothing below revises a rung or a severity rank. No training was run; substitution is
pure scoring. Nothing is committed or pushed.

**Verdict: the ladder is dead, by the kill rule written down in advance.** The a priori severity
ordering does not order the substitution penalty (ρ = +0.095, p = 0.84), and the placebo — a rung
that formally lowers fidelity while changing nothing physical for the rows it is scored on — moves
the penalty by +1.77 ln x2 with an interval that excludes zero. The mechanism is identified and it
is not a bug in the harness: **the model's learned σ-profile is not a σ-profile.** It puts a third
of its surface area in the hydrogen-bond donor window for solvents that have no donor.

---

## 1. Harness identity check — PASS (three ways)

Deposit: `harness_identity.json`.

| check | reference | result |
|---|---|---|
| rung 0 (n=30), learned arm | `results/cosmo_sac/test_predictions.csv`, written by the untouched `export_checkpoint_predictions.py` on 2026-06-21 | max &#124;Δ&#124; = **1.45e-05** over the 5,608 scored rows; MAE 2.6128986 vs 2.6128988 |
| rung 0 (n=30), oracle arm | `export_checkpoint_predictions.py --sigma-oracle --sigma-oracle-side both`, re-run today | max &#124;Δ&#124; = **3.6e-15**; MAE 9.0002789 vs 9.0002789 |
| `NO_SG` (see §5) | rung 0 | **bit-identical**, 0.0 in both arms |

The learned-arm check is not bit-identical over all 8,103 rows: 15 rows differ, up to 1.92 ln x2.
All 15 carry `has_solubility = False`, are exotic phosphorane/macrocycle graphs, and enter no
metric anywhere. Two scored rows differ, both below 1.5e-5. I report this rather than rounding it
away; it is a featurisation-determinism difference between June and today, not a ladder effect.

Two apparatus facts recorded here because they change how the table reads:

* **Rung 0 is scored at n = 8**, the segment count in this checkpoint's `model_card.json`
  (`cosmo_sac_gamma_iter_train`), not at the config's eval count of 30. Both are reported.
* **The adaptive correction contributes exactly nothing.** The confidence gate sits at 1.0000, so
  `ln_x2_final ≡ ln_x2_physics` to the last bit at every rung and in both arms. The pre-registered
  worry that the correction might absorb closure damage does not arise here, and the two columns
  are one column.

## 2. The placebo — FAIL, and the reason is the intermediate, not the instrument

Deposits: `placebo_hb_activity.csv`, `placebo_profile_diagnosis.csv`, `ladder_table.csv`.

The `CHB_0` rung deletes the hydrogen-bond kernel. It is inactive unless the pair supplies both a
donor-type segment (σ < −σ_hb) and an acceptor-type segment (σ > +σ_hb). The placebo subset is the
894 substituted rows over 31 solvents where **neither solute nor solvent has any H-bond donor**
(explicit heteroatom-H SMARTS; note that `rdkit.Lipinski.NumHDonors` scores *water* as zero donors
and would have placed the corpus's most H-bonding solvent inside the placebo — that near-miss is
recorded in the script). The matched active subset is the 2,416 rows over 23 solvents where both
sides carry ≥1 donor and ≥1 acceptor.

| subset | rows | solvent clusters | `CHB_0` effect on the penalty (ln x2) |
|---|---|---|---|
| placebo, H-bond-inactive chemistry | 894 | 31 | **+1.769  [+1.081, +2.545]** |
| matched active chemistry | 2,416 | 23 | +2.872  [+0.587, +4.641] |

Both pre-registered kill conditions fire: the placebo interval excludes zero, and the placebo effect
is 62% of the active one, above the 50% threshold. 94.7% of placebo rows moved at all.

**Why.** The reference (VT-2005) profiles behave exactly as the physics says: for every placebo
solvent the donor-window area is **0.000 Å²**. The *learned* profile does not:

| solvent | rows | learned donor-window area (Å²) | reference (Å²) | learned donor fraction of total area |
|---|---|---|---|---|
| acetone | 147 | 32.4 | 0.000 | 0.356 |
| DMF | 105 | 26.6 | 0.000 | 0.331 |
| ethyl acetate | 95 | 36.8 | 0.000 | 0.333 |
| toluene | 80 | 24.5 | 0.000 | 0.240 |
| cyclohexane | 50 | 44.0 | 0.000 | 0.233 |
| 1,4-dioxane | 49 | 61.8 | 0.000 | 0.299 |
| THF | 39 | 50.7 | 0.000 | 0.314 |

**100% of rows** in the placebo subset — and in every other subset — have both donor-window and
acceptor-window mass in the learned profile. The H-bond kernel is fully active on every row of the
learned arm regardless of chemistry, so deleting it is never a no-op there.

This matters for how the failure is read. The placebo's premise ("fidelity fell, physically nothing
changed") is violated *inside the apparatus*: the term is not inactive, because the intermediate it
reads is not physical. So the strict conclusion is not "the instrument responds to alteration rather
than to damage" — it is worse and more specific:

> The a priori severity ranking was argued from what each term *means physically*. That argument
> does not reach an apparatus whose intermediate does not encode the physics the term is about.
> Damaging the H-bond kernel here does not degrade the closure's treatment of hydrogen bonding; it
> reweights an arbitrary region of a learned vector.

And note there is **no fully clean placebo available on this estimand**. The substitution penalty is
a difference between two arms, and one of them always carries the learned intermediate. Even on the
297 both-sides-matched rows the learned arm is still learned. The placebo cannot be repaired by
choosing a better subset.

## 3. The rank correlation and its null — no ordering

Deposit: `rank_correlation.json`. Null is the **exact** permutation distribution over all orderings
of the rungs (40,320 for 8 rungs; 362,880 for 9), two-sided.

| row set | rungs | ρ | p |
|---|---|---|---|
| substituted (5,571 rows / 64 solvents) | 8 (`NO_SG` dropped) | **+0.095** | **0.840** |
| substituted | 9 (`NO_SG` in) | +0.100 | 0.800 |
| solvent-only (5,274 / 61) | 8 | +0.095 | 0.840 |
| both-sides (297 / 18 / **7 distinct solutes**) | 8 | +0.738 | 0.046 |
| both-sides | 9 | +0.803 | 0.012 |

**The both-sides cell is not a positive result, and it is reported here so that nobody later
reports it as one.** Four reasons, in order of weight: (i) the placebo failed, and the
pre-registration says the rank correlation is not read as evidence unless it passes; (ii) every one
of the eight `both_sides` effect intervals crosses zero — the ordering is over quantities that are
individually indistinguishable from no effect; (iii) 297 rows resolve to **7 distinct solutes** and
18 solvent clusters, so the effective n is single digits; (iv) the sign arises the wrong way round
mechanically — on that subset the *low*-severity rungs carry the most negative effects
(`ALPHA_2.0` −0.18, `SIGHB_0.5` −0.13) and the high-severity rungs sit at ≈ 0, so severity
correlates with the penalty *returning to baseline*, which is not the fidelity law's mechanism
(damage should push the penalty up, not back to zero).

## 4. The per-rung table

Substituted set: **5,571 rows over 64 solvent clusters**; the top five solvents carry 45% of rows
(`cluster_structure.json`). Intervals are solvent-cluster bootstraps, 10,000 resamples, percentile
2.5/97.5. Full table including `ln_x2_physics`, `solvent_only`, `both_sides`, placebo and active
subsets: `ladder_table.csv`.

Rung-0 substitution penalty: **+4.320 [+3.623, +5.232]** ln x2 (64 clusters). Between-seed spread of
this penalty on the e5 `grounded_a` family: **sd 0.036, range 0.077** (`rung0_seed_spread.json`).

| rung | a priori severity | MAE learned | MAE oracle | penalty | effect vs R0 | 95% CI on effect | clusters |
|---|---|---|---|---|---|---|---|
| `R0` (n=8) | — | 1.922 | 6.241 | +4.320 | 0 | — | 64 |
| `ALPHA_0.5` | 1 | 1.993 | 6.559 | +4.566 | **+0.246** | [+0.068, +0.359] | 64 |
| `ALPHA_2.0` | 2 | 1.999 | 5.825 | +3.826 | **−0.494** | [−0.630, −0.314] | 64 |
| `SIGHB_0.5` | 3 | 2.273 | 7.875 | +5.602 | **+1.282** | [+0.340, +2.035] | 64 |
| `ITER_2` | 4 | 2.189 | 4.968 | +2.780 | **−1.540** | [−2.555, −0.795] | 64 |
| `SIGHB_2.0` | 5 | 2.385 | 8.189 | +5.804 | **+1.484** | [+0.949, +1.985] | 64 |
| `NO_SG` | 5 (void) | 1.922 | 6.241 | +4.320 | 0.000 | exact | 64 |
| `CHB_0` | 6 | 2.334 | 8.751 | +6.417 | **+2.097** | [+0.917, +3.011] | 64 |
| `ITER_1` | 7 | 2.291 | 3.445 | +1.153 | **−3.166** | [−4.123, −2.350] | 64 |
| `ALPHA_0` | 8 | 2.165 | 7.031 | +4.866 | **+0.546** | [+0.151, +0.804] | 64 |
| `R0_iter30` (*not damage*) | — | 2.616 | 9.046 | +6.430 | **+2.110** | [+1.562, +2.684] | 64 |

The damage landed: every rung raises the closure's own error (MAE learned 1.92 → 2.17–2.39) and
moves the exchange-energy kernel measurably (`delta_w_shift_rms` 2.8–5.5 kcal/mol for the kernel
rungs; the iteration rungs leave the kernel untouched by construction). The effects are far larger
than the 0.036 rung-0 seed spread, so they are real movements — they are simply not ordered.

Three readings that survive the table:

* **The effects are not monotone and several are strongly negative.** The two most severely damaged
  closures in the ranking that also destroy the fixed point — `ITER_1` and `ITER_2` — give the
  *smallest* penalties in the whole ladder (+1.15 and +2.78 against +4.32 undamaged). A closure whose
  segment activity is one damped step from unity cannot be hurt much by a wrong σ-profile.
* **`ALPHA_0`, the rung I ranked most severe, sits mid-table at +0.55.** Deleting the electrostatic
  misfit term entirely moves the penalty a quarter as much as deleting the H-bond term.
* **A free hyperparameter that is not damage at all outranks almost every rung.** Moving the segment
  count from the fitted 8 to the config's eval 30 changes the penalty by **+2.11** — more than
  every rung except `CHB_0`. This is the CLAUDE.md segment-count trap showing up directly in the
  grounding estimand, quantified here for the first time on the substitution penalty: 4.32 → 6.43.

## 5. `NO_SG`: a pre-registered rung that turned out to be a second null

`CosmoSacLayer.ln_gamma_2` applies the Staverman–Guggenheim term only `if self.use_combinatorial and
V2 is not None and V1 is not None`, and `V` is `None` unless `cosmo_sac_wire_volume` is set. That
field does not appear in this checkpoint's `model_card.json` at all, so it defaults to `False`:
**the combinatorial term was never wired.** Removing it is a provable no-op, and it came back
bit-identical in both arms — a second, independent confirmation that the damage harness does not
leak. Recorded in `PREREGISTRATION.md` §8b at the moment it was found, which was after the run
started and before any penalty had been read.

Consequence for reading everything above: **rung 0 is residual-only COSMO-SAC, not textbook
COSMO-SAC.** Every fidelity statement here is relative to that baseline.

## 6. The competing explanation, tested

If the penalty is not tracking fidelity, is it tracking the closure's *sensitivity* to the
intermediate — how much ln γ₂ moves when the σ-profile is swapped? That quantity,
S(r) = mean |ln γ₂(oracle) − ln γ₂(learned)|, is a property of the operator and uses no solubility
label. Deposit: `sensitivity_table.csv`, `sensitivity_vs_severity.json`.

| predictor of the penalty across the 8 rungs | ρ | p (exact permutation) |
|---|---|---|
| a priori severity | +0.095 | 0.840 |
| closure sensitivity S(r) | **+0.500** | 0.216 |

Sensitivity predicts the penalty better than severity does, and the two rungs that drive it are the
truncation rungs (S = 3.7 and 8.4 against 21.0 undamaged, penalties +1.15 and +2.78). But it is not
significant at n = 8 either, and `CHB_0` breaks it outright (S = 14.6, below baseline, yet the
largest penalty in the ladder). So the honest statement is that the ladder's spread is *partly*
explained by how responsive the damaged closure remains to its input, and not explained by how
wrong it is — but "sensitivity" is not established as the governing variable, only as a better
candidate than severity.

## 7. What this licenses the manuscript to say

The manuscript may now say the following, and should not say more. A closure-damage ladder — nine
named, scoring-time mutilations of the deployed COSMO-SAC layer whose severity was ranked in
advance from what each modification removes, and applied identically to both arms so that the
train/score mismatch cancels in the difference — **does not order the reference-substitution penalty**
(Spearman ρ = +0.10 against an exact permutation null, p = 0.84, over 5,571 solubility rows in 64
solvent clusters, single seed). The penalty is not monotone in severity and changes sign across the
ladder: truncating the segment fixed point, one of the most destructive modifications available,
*reduces* the penalty from +4.32 to +1.15 ln x2, while deleting the electrostatic misfit term
entirely moves it by only +0.55. A placebo that lowers formal fidelity while leaving the scored
chemistry untouched moves the penalty by +1.77 [+1.08, +2.55], and the diagnosis is that the
learned intermediate is not physical — it assigns a quarter to a third of every molecule's surface
area to the hydrogen-bond donor window, including for cyclohexane and toluene, where the reference
profile assigns exactly zero. Finally, a hyperparameter that is not damage at all, the segment
fixed-point iteration count, moves the same penalty by +2.11 (4.32 at n = 8, 6.43 at n = 30), which
exceeds eight of the nine deliberate mutilations. **The substitution penalty is therefore not a
readout of closure fidelity on this apparatus, and the fidelity law cannot be de-circularised this
way.**

What remains circular after this is the whole of it: nothing here supplies an independent estimate of
closure fidelity, so the law's original circularity is untouched — the ladder was an attempt to
supply the missing side by construction, and the attempt failed at the instrument, not at the
statistics. Three further limits belong in any restatement. The ladder ran on **one seed**, because
the σ-grounded e5 checkpoints (`checkpoints/e5/grounded_a_seed*.pt`) are absent from this machine
and the deposited e5 per-row files do not carry the learned σ-profile; the rung-0 seed spread quoted
beside the effects (sd 0.036) is borrowed from the e5 `grounded_a` family and is not this
checkpoint's own. The baseline closure is **residual-only**: the Staverman–Guggenheim term was never
wired in this checkpoint, so "undamaged COSMO-SAC" here already lacks a term the published model
has. And the checkpoint is **σ-ungrounded**, which is precisely why its learned profile is
unphysical and why its rung-0 penalty (+4.32) is an order of magnitude above the σ-grounded e5
arms' (+0.43). The one repair that could revive this design is to rerun the identical ladder on a
σ-supervised checkpoint, where the learned intermediate might satisfy the placebo's premise; that
needs either the missing e5 checkpoints or GPU time, and until it is done the correct statement is
that the ladder is **refuted on the ungrounded apparatus and untested on the grounded one** — not
that closure fidelity fails to govern grounding.

## 8. Files

| file | what |
|---|---|
| `PREREGISTRATION.md` | rungs, severity ranks and reasoning, placebo definition and kill rule, all fixed before any penalty was computed; §8b logs the `NO_SG` discovery mid-run |
| `ladder_table.csv` | every rung × {substituted, solvent_only, both_sides, placebo, active} × {`ln_x2_final`, `ln_x2_physics`}: MAE per arm, penalty, effect, cluster-bootstrap intervals, cluster counts, kernel shift |
| `rank_correlation.json` | ρ and exact-permutation p for every row set, with and without `NO_SG` |
| `harness_identity.json` | the three identity checks |
| `placebo_hb_activity.csv`, `placebo_profile_diagnosis.csv` | per-subset and per-solvent H-bond-window occupancy, learned vs reference |
| `sensitivity_table.csv`, `sensitivity_vs_severity.json` | the competing sensitivity explanation |
| `rung0_seed_spread.json`, `cluster_structure.json` | seed spread and the solvent-cluster structure |
| `scripts/` | `run_ladder.py`, `subsets.py`, `analyze.py`, `profiles.py`, `sensitivity.py`, `deposit.py` |

Reproduce: `KMP_DUPLICATE_LIB_OK=TRUE python scripts/run_ladder.py` (≈62 min, CPU, no training),
then `subsets.py`, `profiles.py`, `analyze.py`, `sensitivity.py`, `deposit.py`.
