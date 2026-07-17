# Pre-registered prediction — reference-σ fidelity lever, in-house same-database (2026-07-18)

Committed **before** the computation is run. This is a falsification test; its value is
zero if the prediction is written after the number. (Thread lesson:
`feedback-posthoc-frame-dies-to-control-check`.)

## What is being measured

The **reference-σ arm only** (no learned head): feed the *reference* UD typed 3-profiles
through a fixed closure and predict, then compute MSE against experiment. Two closures,
same NIST engine (`cCOSMO`), same UD database, held to a **paired** per-pair comparison:

- **2002** = `cCOSMO.COSMO1` on the UD untyped σ-profile.
- **2010** = `cCOSMO.COSMO3` on the UD typed 3-profile, **dispersion OFF** (primary;
  the dsp term is transcribed but not numerically validated, and the paper's own numbers
  put 2010=0.77 vs dsp=0.79, i.e. ~0 difference — so dsp is a flagged secondary row only).

Two slices:
- **(A) ln γ∞ slice (clean):** IDAC∩UD activity pairs. No crystal term → isolates the closure.
- **(B) ln x2 slice (headline, confounded):** the n=163 UD-matchable solubility test pairs,
  through Φ(T) + SLE. The crystal term Φ uses predicted/group ΔH_fus,T_m (the test split has
  essentially no measured ΔH_fus), which is **common to both arms and therefore inflates both
  MSEs and compresses the relative difference** — so the effect reads weaker here than on (A),
  and a null on (B) alone is not decisive.

## Predictions (direction is what is tested)

1. **(A) clean ln γ slice — PRIMARY:** `MSE(ref→2010) < MSE(ref→2002)` by a clear margin.
   Direction is asserted with confidence; the paper's cross-database analog was 1.26→0.77
   (~40% drop), and the in-house same-database contrast should show the same sign and a
   comparable-order drop.
2. **(B) ln x2 slice — headline:** same sign `MSE(2010) < MSE(2002)`, but **compressed** by
   the shared crystal-term error; may be small.
3. **dsp:** `2010/dsp ≈ 2010` (negligible), reported as a flagged secondary row.
4. **Uncertainty:** two-way solute×solvent cluster bootstrap on the 114 solutes / 26 solvents
   (the first time this clustering is well-powered here — not the 17/41 of the corner).

## Falsification

If on the **clean ln γ slice (A)** `MSE(ref→2010) ≥ MSE(ref→2002)` (or the paired margin's
cluster-bootstrap CI spans/crosses zero), then **there is no closure-fidelity lever on this
in-house same-database measurement**, and §7's "closure fidelity, not input fidelity, is the
lever" does not hold where it can be measured cleanly — the claim would have to be retracted
to the cross-database observation only.

## Pre-registered scope caveat (name it before, not after)

UD covers only **4% of BigSolDB solutes** (114/2634) because UD is a small-molecule database
and BigSolDB is drug-like. So the 114 solutes are a **chemically non-representative,
small-molecule tail** of the corpus — the contrast is *not* measured on the drug-like corpus
the paradox lives on. This is the same cross-regime gap as §6.7 and must be stated in those
terms; a positive result here transfers to the headline corpus only by conjecture.
