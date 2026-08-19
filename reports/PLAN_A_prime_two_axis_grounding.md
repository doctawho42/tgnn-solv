# Path A′ — the two-axis "when does physical grounding help vs hurt" reframe

_Fallback if the onemodel run collapses C2, but a stronger/more honest frame than the current
"double-edged grounding" even if C2 survives — the headline does not depend on C2._

## Thesis (the organizing claim)

> **Whether grounding a learned molecular latent in its true physical value HELPS or HURTS
> downstream prediction is not a fixed fact. It is governed by two axes: (1) how the latent is
> trained — supervised toward truth vs. shaped end-to-end through a fixed map — and (2) the fidelity
> of the fixed physical map (closure). We give a quantified, mechanistic map of this for the
> COSMO-SAC family, and a decomposition that says which term (the map or the inputs) binds.**

This turns the individually-known pieces (2010 > 2002; supervised-σ helps; our end-to-end paradox)
into a *synthesis with a takeaway*, instead of "new closure beats old." Not a general ML theory,
not an accuracy SOTA — a measurement/organizing paper for a domain venue (JCIM / Digital Discovery /
JCTC).

## The three real anchors (+ dial)

| anchor | latent supervision | closure fidelity | grounding effect | source |
|---|---|---|---|---|
| **TeNNet-SAC** (JCIM 2025) | high (σ supervised on QC) | learned Γ | true σ **helps** (MAE 0.030<0.065) | cite |
| **ours** | none (σ end-to-end through fixed closure) | low (2002 residual-only) | true σ **hurts** (paradox); σ→surrogate | our result |
| **2010/dsp control** | n/a (true inputs both) | high (2010 donor/acceptor HB) | hurts **less**; B_closure 0.70→0.20, verdict flips closure→inputs | our result (done) |
| **synthetic dial** | — | swept F | traces the helps↔hurts boundary directly | existing §dial |

## Section-by-section: what each current piece becomes

- **Abstract / Intro** — reframe around "does grounding help or hurt? it depends — here is the
  two-axis map." Drop the "double-edged" slogan and the "general instrument for any g(h(x))" top-ML
  framing (panel found it hollow). Keep the paradox as the hook.
- **Related work** — ADD TeNNet-SAC (JCIM 2025) + the help-vs-hurt lineage the novelty check found
  (HESS 2026 "when physics gets in the way"; Ray 2025 "physics-constraint paradox"; concept-bottleneck
  leakage Margeloiu 2021 / Havasi 2022). Position: "the sign of the grounding effect is known to
  vary; we give a *quantified, mechanistic* map for the COSMO-SAC family." Honestly concede C1
  (interpretability-illusion) and C3 (grounding-hurts) are anticipated — we contribute the map + the
  measurement, not the existence of either.
- **Methods** — the differentiable fixed COSMO-SAC closure + the σ-head + the decomposition; keep the
  cCOSMO reference validation (RMSE 0.003) — it now certifies the *measurement instrument*.
- **Results**
  1. *The paradox* (our anchor: end-to-end σ + 2002 → hurts). Hook.
  2. *The decomposition = the instrument* (measures the ceiling = B_closure for the 2002 anchor).
     **Demoted** from headline to tool; keep honestly graded (P≈0.78, LOTV bound, robustness battery).
  3. *Closure-fidelity axis — the 2010/dsp control* (DONE): B_closure −70%, verdict flips to inputs.
     **First-class result**, the decision-relevant one.
  4. *Latent-supervision axis — TeNNet reconciliation + the surrogate mechanism*: supervised σ helps
     (TeNNet); end-to-end σ becomes a compensating surrogate → hurts (ours). **Surrogate demoted to
     "mechanism for this axis," honestly graded.** If C2 lives (strong clean transferability), this
     sub-result strengthens (structured/transferable); if C2 dies, it stays a qualitative mechanism
     note. Either way the map's headline is unaffected.
  5. *The synthetic dial* (existing): controlled F-sweep traces the boundary.
  6. **NEW map figure**: 2-D schematic, axes = latent-supervision × closure-fidelity, with the three
     anchors + the dial placed; shaded "grounding helps" / "grounding hurts" regions; the physics-tax
     sign rule as the boundary.
  7. *Supporting negatives* (data-eff, Gate-B, pKa, transfer-limited encoder) — demoted to
     context/robustness, not headline contributions.
- **Discussion** — the two-axis map is the takeaway; the physics-tax sign rule is the *formal account
  of the sign* (Δ∞ vs variance saved), conceded textbook but honest scaffolding. Practical
  prescription: "if your closure is misspecified and your latent is end-to-end, grounding hurts and
  the latent isn't physical — either supervise the latent toward truth, or raise closure fidelity
  (e.g. 2010/dsp)." Honest scope: COSMO-SAC family, low-γ/298K measurement corner, no accuracy claim.

## What A′ CUTS / DEMOTES (all already-flagged over-claims)
- "double-edged grounding" slogan → gone.
- "interpretability is illusory" as co-headline → mechanism note (scooped: NeurIPS Takeishi 2021,
  Havasi 2022, BINN-2026, σ-profile-ML "lack physical significance").
- uncertified P≈0.78 keystone as headline → demoted to "the instrument's reading on the 2002 anchor."
- "general instrument for any composed predictor" → gone.
- "proved account / reusable diagnostic" over-claims → already downgraded (commit 45bd2fa).

## Assets already in hand (nothing to re-run for A′)
- 2010/dsp control: `results/b_insuff/closure_variant_control.json` (done).
- cCOSMO reference validation: `results/b_insuff/closure_reference_validation.json` (done).
- decomposition + robustness battery: `results/b_insuff/{decomposition,keystone_robustness,leverage_robustness,regime}.json` (done).
- synthetic dial, Gate-B, pKa, data-efficiency, encoder probe: existing sections.
- surrogate analysis: `results/compensation/*.json` (+ onemodel when it lands).
- TeNNet-SAC: cite JCIM 2025 (10.1021/acs.jcim.5c01804 / PMC12529776).

## Trigger (mechanical, decided in advance)
When onemodel returns: if clean one-model transferability < ~3–5× vs identity AND drift not clearly
climbing toward the confounded ~82% → treat C2 as not-robust, execute A′ (surrogate = mechanism
note). If strong → keep A′ structure but promote the latent-supervision-axis sub-result (structured,
transferable compensation) to a genuine secondary contribution.

## Honest scope of A′
A modest but real, honest, decision-relevant domain paper: a quantified mechanistic map of *when*
physical grounding of a learned latent helps vs hurts for COSMO-SAC-family models, with a
reference-validated measurement instrument. Not a field-changer; a solid, citable brick with an
actual takeaway — and (per the redirect plan) its learnings seed a stronger next project
(fully-learned-but-thermo-consistent, à la TeNNet, or the encoder/pretraining lever).
