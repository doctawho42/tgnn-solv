# PRE-REGISTRATION: the 2x2 sigma-substitution test for paradox item #1 (2026-07-18)

Written BEFORE running the 2x2. Purpose: separate the three confounded explanations of the verified
solvent-channel finding (both-reference paradox +0.017, solvent-only +0.418) so the headline is
reframed on a resolved cause, not an unseparated confound.

## The confound
`both-reference` rows are SIMULTANEOUSLY (i) "both channels substituted to reference" AND (ii) "easy,
small, VT-covered solute" (only 5.3% of solutes are VT-covered; MAE 1.24 there vs 1.90 on drug-like).
The +0.017 could be either "channel mixing broke it" or "these are low-B_closure molecules where the
closure is right, nothing to compensate." Opposite headlines follow.

## Design
On the both-reference subset (solute AND solvent in VT-2005; ~198 molecules/seed, seeds 42+43 -- the
only rows where all four conditions are computable because the solute has a reference profile), hold the
molecule and its crystal term Phi fixed and vary ONLY the sigma-pair fed to the fixed COSMO-SAC closure,
then re-solve the SLE for ln x2. Four conditions:
  (a) both-learned      : ln gamma = g(sigma_hat_solute,  sigma_hat_solvent)
  (b) both-reference    : ln gamma = g(sigma_ref_solute,  sigma_ref_solvent)
  (c) ref-solvent       : ln gamma = g(sigma_hat_solute,  sigma_ref_solvent)   [learned solute]
  (d) ref-solute        : ln gamma = g(sigma_ref_solute,  sigma_hat_solvent)   [learned solvent]
Report MAE(ln x2) per condition, averaged over the two complete seeds, on the SAME molecules.

## Pre-registered hypotheses and decision rule
Let MISMATCH = mean[MAE(c), MAE(d)] - mean[MAE(a), MAE(b)] (the cost of feeding one learned + one
reference channel vs. a matched pair, on identical easy molecules).

- **H_mixing (co-adaptation):** MISMATCH is LARGE (>= +0.2, i.e. comparable to the +0.42 solvent-only
  effect). Interpretation: the paradox is learned/reference INCONSISTENCY, not "true sigma is worse."
  => the solubility headline is substantively wrong and must be rewritten (a bad-news outcome).

- **H_chemistry:** MISMATCH is SMALL (< +0.1, ~0). Interpretation: mixing is NOT the cause; the +0.42 on
  solvent-only rows is then driven by SOLUTE CHEMISTRY (drug-like = high-B_closure, where the closure is
  misspecified and the learned latent compensates), and both-reference ~0 is simply the low-B_closure
  regime -- the same design-band structure as S6.2, now on the solubility axis. => the paradox is real;
  the headline survives with an explicit scope/regime caveat (a good-news outcome).

- Intermediate (+0.1 to +0.2): partial mixing; report both channels and reframe as "channel-consistency
  AND regime" jointly, no clean single-cause headline.

Secondary read: compare condition (c) here (ref-solvent+learned-solute on EASY solutes) against the
solvent-only subset (+0.42, same substitution pattern on DRUG-LIKE solutes). If (c)~0 here but +0.42
there, that difference is solute hardness (chemistry), isolating (ii) from (i) directly.

Commit this file before the run; report the numbers against it without moving the thresholds.
Same-molecules discipline (kills the design-vs-chemistry hiding place, as with the |ln gamma| frame).
