# Pre-registration — Track 2 "fix-g": ground the map, not the concept

Committed BEFORE any number is computed. Metrics, thresholds, and both readings are fixed here;
results that deviate must be reported against this document, not a post-hoc target.

Date: 2026-07-19. Compute: GCP (full-corpus GPU). Status at registration: no fix-g number computed yet.

## Thesis
The physicality of a learned latent is governed by the specification of the fixed map that consumes it,
not by supervising the latent. Replacing per-molecule grounding with a **low-capacity physical correction
to the closure** should restore a physical latent without any oracle, and should invert the grounding
paradox. This is the constructive inverse of the paper's non-identifiability result: `(z, g)` is
non-identified from `(x, m)`; identifying a physical `z` requires anchoring exactly one side of the split.
Grounding anchors `z` (and conflicts when `B_closure > 0` → the paradox); a low-capacity correction anchors
`g` (non-conflicting, costs `d` parameters, not `N` labels). The correction's **capacity is the anchor**:
a symmetric rank-`r` residual on the exchange kernel `ΔW` (`g_φ = g_0 + a·(b bᵀ)`) can move the physical
object (segment exchange energies) but cannot encode per-molecule drift.

## Primary metric (fixed)
`ρ = ‖σ̂ − σ‖ / ‖σ‖` on n=44 matched VT-2005 solutes, **paired per molecule, 3 seeds, drop-one leverage**.
Anchors from Paper 1 (committed): free latent `ρ_free = 0.51`; grounded latent `ρ_grounded = 0.36`.
Closure gap to explain: 0.51 → 0.36 (15 points).

## Decision thresholds (fixed, pre-committed)
- **GO** = ρ closes more than 1/3 of the gap (`ρ ≤ 0.46`) with solubility prediction preserved
  (MAE within 10% of the co-trained-free baseline).
- **NO-GO** = ρ unmoved from 0.51 (closure < 5 points, `ρ ≥ 0.50`) OR solubility MAE degrades > 10%.
- **PARTIAL** = `0.46 < ρ < 0.50`: the defect is only partly within the correction's capacity
  (the honest most-likely outcome; see failure mode 2). Still publishable as a predictive-scope result.

## Gates (cheapest first; each a kill)
- **Gate 0 — literature (0 compute).** Cite-and-differentiate vs Universal Differential Equations,
  gray-box/hybrid modelling, Havasi "Addressing Leakage in CBM", null-space learning (Schwab). Delta =
  (latent physicality ⟺ B_closure) + (anchor the map, not the concept) + (the oracle decomposition
  predicts the outcome a priori). Kill if the exact method already exists on molecular activity.
- **Gate 1 — core go/no-go (~1 GPU run, existing artifacts).** Co-train encoder + 52-parameter symmetric
  residual `a·(b bᵀ)` on `ΔW`, end-to-end, **σ-grounding off**, full corpus n=5608. Measure ρ on n=44.
  Predict `ρ ≤ 0.46`, solubility preserved. Kill if `ρ ≈ 0.51`.
- **Gate 2 — identifiability (conditional on Gate 1).**
  - 2a capacity sweep: rank r ∈ {1,2,4,8,…}; predict ρ falls monotonically to a plateau. Flat/non-monotone → kill.
  - 2b independent-fit agreement: cosine/subspace overlap between the co-trained correction and the
    52-param residual fit directly on reference profiles (Paper 1). High overlap = physical defect absorbed,
    not memorised.
  - 2c prediction parity: MAE(co-trained) vs MAE(free); both objectives must hold (physicality up AND
    prediction preserved). A trade-off is not a win.
- **Gate 3 — prize (conditional on Gate 2).** Same oracle-swap (learned σ̂ → reference σ) on the
  co-trained-closure model, 3 seeds. Predict `ΔMAE ≤ 0` (grounding no longer hurts) — the sign rule shown
  by construction.

## Failure modes (pre-declared)
1. Identifiability collapse — g and z co-adapt, z stays non-physical. Mitigated by low residual capacity;
   Gate 2a/2b catch it.
2. Defect outside g's parametrisation — Paper 1: the residual removes ~49% of the closure error, rank-2
   overfits. So the defect is only partly reachable → the likely outcome is **PARTIAL** (ρ: 0.51 → ~0.44–0.47),
   not full. This is an honest expected result; the GO threshold is set for it (> 1/3 of the gap).
3. Physicality/prediction trade-off — Gate 2c.
4. Small physicality n (44) — paired test + 3 seeds + drop-one; training is on n=5608 (stronger than the diagnostic).

## Most likely honest outcome
**PARTIAL GO.** The residual reaches ~half of the closure defect → ρ shifts partway toward physical, the
paradox weakens but does not vanish. That is sufficient: "anchoring the map partially restores physicality
without grounding, to the degree the defect is expressible by the correction — and the oracle decomposition
predicts that degree in advance." Full GO (paradox inverts) is the upside scenario.

## Assets
Existing: `heads.SigmaProfileHead`, differentiable `layers.CosmoSacLayer` (2002), the 52-param symmetric
residual on `ΔW` (`scripts/analysis/run_local_closure_fix.py`, fit post-hoc on reference input), the
grounding streams (to switch σ-supervision off via `sigma_aux_*` weights = 0), the ρ metric, n=44 eval,
n=5608 train. New: the co-train path (encoder + φ jointly, σ-grounding off), the capacity sweep over rank r,
the overlap metric between co-trained φ and the independently-fit residual.
