# Pre-registration: the closure-damage ladder

Written **before any penalty was computed**. Nothing below was chosen by looking at an
outcome. Where I already knew a fact that bears on a rung's a priori direction, it is
stated here rather than discovered later.

Date: 2026-08-11. Branch `sigma-grounded-cosmosac`. Nothing here is committed or pushed.

---

## 1. The claim being tested

The project's fidelity law says: **the fidelity of the closure sets the sign of whether
grounding an intermediate helps.** As it stands the claim is circular — closure fidelity is
estimated from the same data that measures the grounding effect.

The circle is broken by *construction*: damage COSMO-SAC in named ways whose severity
ordering is known a priori, because I know what I removed, without consulting any outcome.
Then ask whether the measured grounding effect follows that ordering.

**Directional prediction (pre-registered).** Severity up ⇒ the substitution penalty becomes
more positive (grounding an intermediate with a reference value hurts more through a worse
closure). Spearman ρ between a priori severity rank and the damage effect is predicted
**positive**.

## 2. Apparatus

* Checkpoint `checkpoints/cosmo_sac/tgnn_cosmo.pt` (seed 42, `activity_model=cosmo_sac`,
  MPNN h64 L3, phases 30/70/10, CPU, 2026-06-21, commit `7e11376`). Its manifest names
  train/val/test with sha256 `419b3b2e…`/`974ea451…`/`7871e8a9…`, which are **bit-identical
  to the current `notebooks/data/processed/*.csv`** — the checkpoint is on the current
  `solute_scaffold` split, post the +273 K `T_m` repair (`eb314d8` is an ancestor of
  `7e11376`).
* **Why this checkpoint and not `results/e5_sigma_grounding/`'s.** The e5 σ-grounding
  checkpoints (`checkpoints/e5/grounded_a_seed{42,43,44}.pt`) **do not exist on this box**
  (`checkpoints/e5/` is absent; a filesystem-wide search finds no `grounded_a_seed*.pt`),
  and the deposited e5 per-row CSVs do not carry the learned σ-profile, so the substitution
  operation cannot be re-run from them at a damaged closure. The e5 deposits are used only
  for the rung-0 **seed spread** (§7), which they can supply.
* Reference σ-profiles: `results/sigma_profile_artifact/sigma_profiles.csv` (1424 molecules,
  VT-2005).
* Scored rows: `notebooks/data/processed/test.csv`, 8103 rows, 5608 with `has_solubility`.
* No training. Substitution is pure scoring.

### The segment count

`cosmo_sac_gamma_iter_train = 8`, `cosmo_sac_gamma_iter_eval = 30` in this checkpoint's
`model_card.json`. Per CLAUDE.md the operator a checkpoint is scored through must be the one
it was fit against, so **every rung is scored at n = 8**, the count this checkpoint trained
at. Rung 0 is additionally scored at n = 30 and both are reported. The truncation rungs
(n = 1, 2) are damage *relative to 8*, not relative to 30.

## 3. The rungs

Each is a named modification of `CosmoSacLayer` (`src/tgnn_solv/layers.py:1452`), applied at
**scoring time only**, to `model.sle_solver.cosmo_sac_layer`. Both arms of every comparison
run through the same damaged layer, so "the checkpoint was not trained for this closure"
cancels in the difference.

Terms that exist in *this* implementation and are therefore eligible: `alpha_prime` (misfit
prefactor), `c_hb`, `sigma_hb`, `use_combinatorial` (Staverman–Guggenheim), `a_eff`, the
segment fixed-point iteration count, `damping`, `coord_z/q0/r0`. **A profile-averaging
radius `r_av` does not exist here** — the σ-profile arrives pre-averaged from
`SigmaProfileHead` or from the VT-2005 table — so no averaging rung is built.

| id | damage | a priori severity rank |
|---|---|---|
| `R0` | none (identity) | 0 |
| `ALPHA_0.5` | `alpha_prime` × 0.5 | 1 |
| `ALPHA_2.0` | `alpha_prime` × 2.0 | 2 |
| `SIGHB_0.5` | `sigma_hb` × 0.5 (0.0084 → 0.0042) | 3 |
| `ITER_2` | segment fixed point truncated to 2 | 4 |
| `SIGHB_2.0` | `sigma_hb` × 2.0 (0.0084 → 0.0168) | 5 |
| `NO_SG` | combinatorial (Staverman–Guggenheim) removed | 5 (tied; **direction contested**, see below) |
| `CHB_0` | `c_hb` → 0 (H-bond term removed entirely) | 6 |
| `ITER_1` | segment fixed point truncated to 1 | 7 |
| `ALPHA_0` | `alpha_prime` → 0 (misfit term removed entirely) | 8 |

### Why this ordering, argued only from what is removed

1. **Removing a whole term outranks mis-scaling a coefficient.** A coefficient error keeps
   the functional form; a removal deletes a physical interaction the model is defined by.
2. **The misfit term is the electrostatic core.** `0.5·α′(σ_m+σ_n)²` is the only term active
   for *every* segment pair. Setting `α′ = 0` leaves an exchange energy that is zero
   everywhere the H-bond window does not reach, so most segment pairs become athermal. That
   is the largest structural loss available ⇒ rank 8.
3. **The H-bond term is conditionally active**: only for `σ_acc > +σ_hb` and
   `σ_don < −σ_hb`. Deleting it (`c_hb = 0`) destroys associating chemistry but leaves
   nonpolar pairs untouched ⇒ severe, but strictly below deleting the always-on misfit
   ⇒ rank 6.
4. **Raising the cutoff (`SIGHB_2.0`) approximates deleting the H-bond term** — the window
   retreats to |σ| > 0.0168 where little profile area lies — so it sits just under `CHB_0`
   ⇒ rank 5. **Lowering the cutoff (`SIGHB_0.5`)** switches the H-bond term on for weakly
   polarised segments: a distortion (over-counting), not a deletion ⇒ rank 3, below both.
5. **Truncating the segment fixed point** means Γ(σ) is never solved. At n = 1 the segment
   activity is one damped step from unity, which discards the self-consistency that defines
   COSMO-SAC ⇒ rank 7; n = 2 retains one round of feedback ⇒ rank 4.
6. **α′ × 2 outranks α′ × 0.5.** In kernel units the perturbation is |Δδw| = 1.0 × the base
   misfit for ×2 against 0.5 × for ×0.5, so ×2 moves the operator further ⇒ ranks 2 and 1.
7. **Least confident adjacency:** `ALPHA_0` (8) vs `ITER_1` (7). One deletes the energetics,
   the other fails to solve them. I commit to this order and flag it.

### The contested rung, declared in advance

I have read `reports/REVIEW_grounding_paradox_2026-07-13.md` before writing this. It records
that the project's *deployed* closure in the `b_insuff` line was residual-only (SG removed),
that **adding** SG moved IDAC MSE 1.47 → 1.80, and that a referee attributed this to the
documented miscalibration of the unmodified Staverman–Guggenheim term for size-asymmetric
pairs. So the a priori claim "removing SG lowers fidelity" is contested by domain literature
and by this project's own measurement. `NO_SG` is kept in the ladder at rank 5 because on a
"what did I remove" argument it is a term removal, but the rank correlation is reported
**twice**: with `NO_SG` in, and with `NO_SG` dropped. Neither is the "real" number; both are.

## 4. Estimand

For a rung *r*, on the substituted row set:

* `P(r)` = MAE(`ln x2` | reference σ substituted) − MAE(`ln x2` | learned σ) — the
  **substitution penalty**. Positive = substituting the reference profile hurts.
* `E(r)` = `P(r) − P(R0)` — the **damage effect**, the quantity the ladder is meant to order.
* Reported on `ln_x2_final` (primary) and on `ln_x2_physics` (pre-correction), because the
  adaptive correction reads `physics_out` and can absorb closure damage.
* Also reported per rung: the closure's own error level (MAE, R², mean |ln γ₂|) so a reader
  can see the damage landed.
* Both substitution cells are reported apart, as the paper reports them apart: **solvent-only**
  (reference σ for the solvent, learned σ for the solute) and **both-sides**.

## 5. Clustering and intervals

Clusters are **solvents**. The substituted set is ~5,571 rows over ~64 solvents with the top
five carrying ~45%, and water's per-solvent median is several times the pooled one, so rows
are not the unit of information. Every interval is a solvent-cluster bootstrap (10,000
resamples, seed 0, percentile 2.5/97.5) and **the cluster count is printed beside it**.
Effective n is the number of solvent clusters, not the number of rows.

## 6. The placebo (the null that decides this)

**Definition, fixed now.** Break a term that is *inactive for the chemistry of the rows
scored*. The `CHB_0` rung deletes an interaction that requires the pair to supply both an
H-bond donor segment (σ < −σ_hb) and an acceptor segment (σ > +σ_hb). If **neither the
solute nor the solvent has any H-bond donor**, no donor-type segment exists and the term is
inactive: fidelity has formally fallen, physically nothing changed for those rows.

* **Placebo subset**: substituted rows with `rdkit.Chem.Lipinski.NumHDonors(solute) == 0`
  **and** `NumHDonors(solvent) == 0`. Chosen from chemistry alone, before any scoring.
* **Matched active subset**: substituted rows where both solute and solvent have ≥1 donor
  and ≥1 acceptor.
* **Verification of the subset, on inputs only**: report the reference-σ area lying beyond
  ±σ_hb for the molecules in each subset. This inspects an *input*, never an outcome.
* **Decision rule, fixed now**: if `|E(CHB_0)|` on the placebo subset is not materially
  smaller than on the matched active subset — concretely, if the placebo's interval excludes
  zero, or if the placebo effect exceeds half the active effect — then the instrument is
  measuring "the closure was altered", not "the closure got worse", **and the ladder is
  dead**. That verdict is reported first regardless of what the rank correlation says.

## 7. The other two required nulls

* **Rung 0 twice.** The undamaged closure is scored through the damaged-closure code path
  with the damage set to identity, and separately through the untouched path. They must
  agree bit-for-bit. If they do not, the harness is the finding.
* **Seed spread.** The rung-0 penalty's between-seed spread is read off
  `results/e5_sigma_grounding/section_s1_channel_split.json` (seeds 42/43/44, same
  substitution operation, `grounded_a` vs `oracle`) and reported beside every rung's effect.
  A rung effect smaller than the seed spread is not an effect. Note the caveat honestly: that
  spread is measured on the e5 `grounded_a` checkpoint family, not on this checkpoint, whose
  ladder runs at **one seed only** — this is the weakest joint in the design and is not
  repairable without the missing e5 checkpoints or a GPU.

## 8. Statistic and its null

Primary: Spearman ρ between the a priori severity rank and `E(r)` over the nine damaged
rungs. Null: the exact permutation distribution of ρ over all orderings of the nine rungs
(two-sided p). Reported with `NO_SG` in and out. **The rank correlation is not read as
evidence unless the placebo passes.**

## 8b. Addendum, logged mid-run, before any penalty was read

While auditing `TGNNSolv._build_sigma_activity_params` (`src/tgnn_solv/model.py:512`) I found
that the Staverman–Guggenheim term is gated on molar volume being supplied:
`CosmoSacLayer.ln_gamma_2` applies it only `if self.use_combinatorial and V2 is not None and
V1 is not None`, and `V` is `None` unless `cosmo_sac_wire_volume` is set. That field **does
not appear in this checkpoint's `model_card.json` at all** (it post-dates the run), so it
takes its dataclass default `False`. **The combinatorial term is not wired in this
checkpoint.** The deployed closure is residual-only — the same fact the 2026-07-13 referee
raised about the `b_insuff` line.

Two consequences, both recorded now rather than discovered later:

1. `NO_SG` is **not a fidelity rung** for this checkpoint. It removes a term that is already
   inactive, so it is a *provable structural no-op* and is reclassified as a **second null**:
   a formally rank-5 structural removal that must produce a bit-identical prediction. If it
   moves anything, the harness is broken. It is dropped from the rank correlation, and the
   "with `NO_SG`" variant is retained only as a record of the pre-registered ordering.
2. **Rung 0 is residual-only COSMO-SAC, not textbook COSMO-SAC.** Every fidelity statement
   below is relative to that baseline, and must say so.

Timing, for the record: at the moment this was written the ladder had produced only the two
rung-0 passes; no damaged rung had been scored and no penalty had been computed.

## 9. What each outcome means

* **Ladder orders the effect** (ρ > 0, p small, placebo passes): the fidelity law has a
  non-circular measurement — severity fixed by construction, effect measured at fixed
  closure.
* **Ladder does not order it**: the claim is not measurable this way. That closes a
  direction honestly and will be reported as the result, not massaged.
