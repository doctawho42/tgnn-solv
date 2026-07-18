# Reviewer panel on the demoted paper (2026-07-18, wf_b9e0b9b2)

5 personas + adversarial verification + AC. **Verdict: minor revision, reject risk ~25%.**
Recs: physchem/ml-stats/framing/repro = minor; adversarial = major (its reject reason REFUTED in verification).
41 findings: 16 CONFIRMED, 15 PARTIAL, 10 refuted/already-addressed. All 5 praised the paper's honesty.

## Biggest threat (perception, not substance)
The b/c coherence tension on the shared n=60 corner: two reviewers read it as "used both ways" (authoritative
when it certifies the closure as the ceiling; dismissible when the fair 2002->2010/dsp swap 1.757->0.765,
P~0.98, is statistically STRONGER than the P_boot=0.78 keystone). Verification: the paper reconciles it
in-text (ln 644-650) and the adversarial framing was REFUTED. But physchem warns it "risks reading as
motivated," lethal for an honesty-first paper. Fix = surface the reconciliation in the main text (certificate
terms): fair-2002=1.757 dominates on the corner (b, a 2002-specific property) while 2010/dsp=0.765 does not
generalize to representative n=477 (c). Cheap; the dominant path to rejection until done.

## CONFIRMED must-fix
1. **[verified subtraction] Surrogate EVR null is the population value, not finite-sample.** Paper: "72% vs
   isotropic ~4% (18x)". Correct finite-sample null at n=44/p=51 (mean-centred, 3000-sim) = **15.1%**, so
   72% is **4.8x** the null, not 18x. Signal still real; magnitude was inflated ~4x. Fix the null number +
   reframe the excess. The mean-centred OOS transfer (reviewer also wants it) rests on the corrected spectrum;
   a fresh 3-seed OOS test needs a GCP respin (headline checkpoints gone) -> soften transfer to the corrected
   spectrum rather than respin.
2. **[trivial, highest consensus - all 4] Floor quoted two incompatible ways.** "~4x above the floor" uses
   kNN B_insuff=0.40 (the estimator the decomposition brands "deflated/least conservative" and keeps OUT of
   the load-bearing bound); against the LOTV floor 0.62 it is ~2.4x. Using the disavowed estimator for the
   headline number reads as cherry-picking. Fix: quote ~2.4x vs 0.62 consistently (2 sites: paradox narrative
   + parity figure).
3. **[wording] Claims-ledger inconsistent.** The certified pKa crossover flip (P(oracle worse)=1.00, 20/20)
   sits only under OPEN as a cross-check while the weaker P_boot=0.78 is LIKELY; "certified" prose (bootstrap
   sense) vs ledger definition; third column labelled OPEN but caption says exploratory. Fix: add pKa-flip to
   the certified/likely tier, reconcile "certified" senses, align labels.
4. **[wording] b/c reconciliation** (the biggest threat, above) + drop/qualify the "corner gain is wrong-sign
   for a signal" claim (undercut by the paper's own localization: 90% of 2002 error on strong H-bond donors =
   exactly what 2010's typed kernel repairs).
5. **[compute, local] Provenance.** The committed flip JSONs use the withdrawn crippled 2002 arm (MSE 1.263),
   so the fair-2002 headline stats (1.757->0.765, P=0.98) and the n=477 null (P=0.62) exist only as in-text
   literals. Regenerate+deposit on the 1.757 baseline; fill repo/hash/license/Zenodo (DOI is the user's).
6. **[wording] Stat-hygiene nits.** (a) a-fortiori sentence direction (LOTV per-bin sparsity bias; RF/ridge
   immunity is SI-only); (b) estimator-conditional caveat (aggressive ridge inverts to B_insuff=0.88>0.59)
   SI-only while the bullet asserts "the closure term is the larger"; (c) two control MAEs (1.98/2.08) trace
   to no per-arm table/artifact.

## Named limits (honest disclosure; mostly ALREADY in the paper)
Keystone underpowered (74 pairs, CI spans zero, one ridge inverts -> keep "likely not certified"); regime
transfer conjecture; no fidelity lever on representative data; no accuracy claim; decomposition needs an
external oracle (caps the "so what"); surrogate magnitude unstable 16-82% (sign+structure load-bearing);
seed-44 truncation + unlogged surrogate split.

## Bottom line
The demote worked: the #1 validity hole from the prior panel is gone, and the surviving items are wording +
trivial + one local recompute + one verified null-subtraction. None reverses a core conclusion. This is a
clean minor-revision if the b/c perception fix and the two number-corrections (null, floor) are made.
