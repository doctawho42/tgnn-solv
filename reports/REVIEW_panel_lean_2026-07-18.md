# Lean reviewer panel (2026-07-18, wf_2c1eaaf5) — 3 reviewers + AC inline-verify

**Verdict: minor revision, reject risk ~45%** (up from ~25%). All 3 reviewers = minor. AC verified majors
against the deposited artifacts + .tex. Two drivers: (1) SIGNIFICANCE (strategic, not revision-fixable);
(2) the fidelity-lever mislabel cluster (fixable, data in hand, but corrupts a headline number).

## CONFIRMED, fixable (data in hand)
1. **Fidelity-lever mislabel (the big one).** The corner "2002->2010/dsp: 1.757->0.765" is WRONG: 0.765 is
   2010 dispersion-OFF (my script `use_dispersion=False`). Corner and representative use DIFFERENT modern
   closures, so "the same swap / single small effect" is false. Corrected 2x3 (MSE ln gamma_inf):
   |            | 2002  | 2010 no-dsp | 2010/dsp |
   |------------|-------|-------------|----------|
   | corner n=60| 1.757 | 0.765       | 0.785 (cCOSMO; my-layer dsp 7.43 diverges) |
   | repr. n=477| 1.911 | 1.978       | 1.855    |
   The correction STRENGTHENS "no lever": on the representative set the modern closure does NOT help
   (2010-no-dsp 1.978 is WORSE than 2002 1.911; 2010/dsp 1.855 = only +3%, P=0.62). Fix: report the 2x3,
   relabel the corner as "2010 (dispersion off)", disclose the in-house dsp divergence + cCOSMO-ref 0.785,
   drop "same swap", report repr 2010-no-dsp=1.978. Propagates to abstract/intro/contribution(c)/Fig1/
   overview-figure/conclusion.
2. **Loss-ablation both-reference reversal unreported.** loss_ablation_analysis.json: both-reference-subset
   paradox = -0.23 (minimal) vs +0.22 (full) -- a sign flip on the 7-solute subset the mechanism needs --
   while the SI headlines only the solvent-dominated overall +1.13 as "strengthens". Fix: report -0.23 vs
   +0.22 with the n=297/~7-solute caveat; temper "strengthens" to "the overall, solvent-dominated paradox".
3. **"1.758 / two independent ways" unbacked.** The second cross-check (1.758, cCOSMO reformatting) appears
   only in prose (l.636, SI:32); the deposited script produces 1.757 (in-house) + cCOSMO crippled 1.263,
   not 1.758. Fix: drop the "two independent ways / 1.758" claim, rest on the in-house 1.757.
4. **Trivials:** "reproduced by finite differences" (main) contradicts SI (autograd 1.00 vs FD 1.25) -> drop
   it; Table 2 caption "convention-independent" is false for the LOTV row (0.53 full vs 0.62 res) -> scope
   it; Conclusion's bare "51+/-2%" -> lead with sign+structure, magnitude indicative.

## PARTIAL (reframing/wording)
5. **Keystone estimator bracket.** Verdict is B_insuff < MSE/2 = 0.74; every estimator that CLEARS it is
   downward-biased (LOTV sparsity; RF/ridge random-fold + kNN leakage), every leakage-FREE one FAILS
   (blocked RF 3.65, distinct-solvent kNN 1.46, aggressive ridge 0.88, leave-one-solvent RF 2/17). Give the
   full bracket + leave-one-solvent-out RF the same billing as the ridge sensitivity; downgrade LOTV from
   "load-bearing" to "best-available-but-sparsity-biased, likely".
6. **Asymmetric trust of the corner, explicit.** The corner upgrade (P=0.98) is bootstrap-stronger than the
   decomposition (P_boot=0.78) it is dismissed against; "no lever" survives only on the n=477 null. State it.

## Biggest threat: SIGNIFICANCE (strategic, NOT revision-fixable)
The certified content is non-novel (the variance identity, "not new" l.343) or is the demoted symptom;
the novel + load-bearing core (surrogate mechanism, closure-dominance) is graded "likely" AND measured in an
infinite-dilution/298K/low-gamma regime the paper admits does not transfer to the finite-composition regime
the paradox lives in ("a conjecture, not a measured fact, the first place a referee should press"). No
relabel/reanalysis closes this; it is a venue-fit judgment on whether a calibrated-negative/diagnostic
paper with a "likely + out-of-regime" novel core clears the bar. AC options: frame explicitly as a
calibrated-negative result; and/or name the one claim that is certified + novel + load-bearing (candidate:
the external-oracle affordance that turns concept-leakage into a measured, sign-predicted split on a fixed
operator) or state plainly none clears all three.

## Named limits (disclosure only, mostly already in paper)
out-of-regime transfer; B_insuff upper-bounded not point-identified; surrogate magnitude within-version;
transferable-vs-weak-null; single-method IDAC (no between-method noise); SG-volume breaks strict convention-
independence (residual-only result unaffected).
