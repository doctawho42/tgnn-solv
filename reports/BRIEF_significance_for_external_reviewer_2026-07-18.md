# Significance brief for an external reviewer

**Purpose.** A prior internal review flagged *significance* (not correctness) as the dominant rejection
risk for this manuscript. Correctness/consistency issues have been addressed; the significance question is
a framing/venue-fit judgment that we want an independent assessment on. This brief is self-contained: it
assumes no prior knowledge of the project. Please read it and give a considered opinion on the questions at
the end.

---

## 1. What the paper studies

A graph neural network predicts solid--liquid solubility by routing its prediction through an explicit,
**fixed** thermodynamic closure (COSMO-SAC), which converts a learned per-molecule latent (a
"sigma-profile", a 51-bin screening-charge-density histogram) into an activity coefficient and hence a
solubility. The closure has **no fitted parameters**; only the graph encoder that produces the latent is
trained.

Because that latent is a *physical* quantity, there exists an **external oracle** for it: quantum-chemical
reference sigma-profiles (the VT-2005 database) computed independently of any solubility data. This oracle
is the paper's central methodological affordance.

## 2. The phenomenon (the entry point)

Substituting the network's *own learned* sigma-profile with the *external quantum-chemical reference*
profile, through the same fixed closure, makes the solubility prediction **worse** (MAE 1.85 -> 2.25 in
ln x2; R^2 collapses to ~0; three seeds, three injection controls). Truer physical inputs hurt. This is the
"grounding paradox".

The paper deliberately treats this solubility paradox as a **motivating symptom, not the causal carrier**,
for a data reason: only ~7 of 147 drug-like test solutes have a reference profile at all, so on solubility
the reference substitution lands almost entirely on the *solvent* channel. The clean, per-molecule causal
evidence therefore lives on the **activity axis** (infinite-dilution activity coefficients), not the
solubility axis.

## 3. The four core claims and their graded evidence

The paper grades every claim in an explicit evidence ledger (certified / likely / open):

| # | claim | evidence | grade | novel? |
|---|-------|----------|-------|--------|
| A | **Paradox (symptom):** reference sigma degrades solubility | 3 seeds, 3 controls, n=5608 | **certified** | no -- it is the demoted symptom |
| B | **Exact decomposition (instrument):** with an external oracle, the reference-input risk splits *exactly*, with no model fit, into a closure-misspecification term B_closure and an input-insufficiency term B_insuff (a law-of-total-variance identity) | proof | **certified** | the *identity* is standard (the paper says so); the *application* (oracle on a learned latent through a fixed operator) is the contribution |
| C | **Closure dominates:** on a matched infinite-dilution set (n=60) B_closure > B_insuff, i.e. the ceiling is the closure not the inputs | one-sided bounds, two-way cluster bootstrap P~0.78 | **likely** (not certified) | yes |
| D | **Compensating-surrogate mechanism:** the end-to-end latent departs from the reference profile (n=44, ~50% low-rank transferable drift) and cancels the closure's error rather than reporting physics | 3 seeds, low-rank structure seed-stable, magnitude within-version | **likely** | yes |
| E | **Sign rule + a second closure:** grounding a learned latent helps or hurts by a *predictable sign* -- it helps iff the learned arm's error exceeds a fidelity-set oracle threshold. Demonstrated *bidirectionally* in a second, independent domain (pKa via a Hammett relationship): the same oracle swap **helps** meta/para (error 0.48 -> 0.315) and **hurts** ortho (0.83 -> 1.62), 20/20 within-scaffold splits, P(oracle worse)=1.00 | K=20 splits, cluster bootstrap | **certified** | yes -- predicts *both* signs of grounding's effect |

A secondary result (F): a fair, validated 2002-vs-modern (2010/dsp) closure comparison finds **no
established fidelity lever** on representative data (the modern kernel helps on a curated low-gamma corner
but is no better than the old kernel on a representative set) -- i.e. the located ceiling is not removed by
the standard closure upgrade. This is a **negative** result.

## 4. The significance concern (precisely)

Look at the last two columns of the table. **No claim in the solubility story is simultaneously certified
AND novel:**

- The **certified** claims are either the *demoted symptom* (A) or a *standard identity* (B, whose
  application is the novel part but whose grade rests on the identity).
- The **novel, load-bearing** claims (C closure-dominance, D surrogate mechanism) are graded **likely**,
  not certified.

Two compounding problems for the novel core (C, D):

1. **Evidence strength.** They are "likely" (n=60/n=44, one-sided bounds, P~0.78), explicitly not certified
   at conventional confidence. One aggressive estimator choice inverts the closure-dominance ordering; the
   separation rests on a sparsity-biased but leakage-robust bound.
2. **Regime.** They are measured on a matched **infinite-dilution / 298 K / low-gamma** set, whereas the
   headline paradox lives at **finite composition, all gamma**. The paper concedes the transfer of the
   attribution back to the paradox's own regime is *"a conjecture, not a measured fact, and is the first
   place a referee should press."*

So a reviewer reading the ledger before the abstract sees: the striking result (the paradox) is a symptom;
the deep results (why) are likely and measured out of the regime they claim to explain. That is the
significance exposure. It is a real feature of the evidence, not a presentation defect -- **no relabeling or
re-analysis closes it** without new experiments the data cannot currently support.

## 5. The candidate resolution (and why it is currently buried)

There **is** one claim that is simultaneously certified, novel, and load-bearing: **claim E, the sign rule
demonstrated by the certified bidirectional pKa flip.** It is in the certified tier; it is novel (it
predicts *both* directions of grounding's effect from a stated inequality, not just "grounding helps" or
"grounding hurts"); and it is the paper's theoretical spine. Crucially, the pKa demonstration is
**in-distribution** (K=20 within-scaffold splits), so this certified anchor does **not** depend on the
out-of-regime transfer that weakens C and D.

The current manuscript **buries** claim E as a "second closure / cross-check" and headlines the *surrogate
mechanism* (D, likely, out-of-regime). This is a residue of an earlier, deliberate reframe ("demote") that
correctly moved the headline off the dirty solubility paradox but landed it on the surrogate rather than on
the sign rule.

## 6. The framing options on the table

- **(i) Instrument / sign-rule forward.** Co-headline the reusable oracle-instrument (B) and the sign rule
  (E), with the certified pKa flip as its clean in-distribution demonstration; keep the surrogate (D) and
  closure-dominance (C) as the *likely* solubility findings the instrument produced. Pro: names a real
  certified+novel+load-bearing claim; reduces out-of-regime exposure (the anchor is in-distribution). Con:
  it is a *third* framing pivot for this manuscript.
- **(ii) Calibrated-negative only.** No further reframe; add one paragraph positioning the paper explicitly
  as a careful negative/diagnostic result and target a venue that values negative results. Pro: low effort,
  honest. Con: leaves the novel core graded "likely" and the headline on the surrogate.
- **(iii) Disclose only.** State plainly in the discussion that no single claim is simultaneously certified,
  novel, and load-bearing, and let reviewers weigh it. Most conservative; does not contest the perception.

## 7. Questions for the external reviewer

1. Is the significance concern in section 4 correctly stated, or is it overweighted? In particular, does
   the exact-decomposition **application** (B) or the **sign rule** (E) clear the "novel + certified +
   load-bearing" bar in your judgment, or not?
2. Of the three framing options in section 6, which best addresses the concern -- and would any of them move
   a paper like this from "likely reject at a competitive venue" toward acceptance, or is the out-of-regime
   limit (section 4.2) dispositive regardless of framing?
3. Independent of framing: is a *calibrated-negative / diagnostic* result of this kind (a reusable
   measurement instrument + a certified cross-domain sign rule + a likely, out-of-regime mechanistic
   attribution + a negative "no lever" result) publishable, and if so where -- a methods/ML-for-science
   venue, a physical-chemistry venue, or a negative-results venue?
4. Is there a fourth option we are missing?

*Context note: this is a revised manuscript; correctness issues (a fidelity-lever labeling error, an
ablation subset reversal, several consistency slips) have been fixed. The question here is strictly
significance/framing, deliberately isolated.*
