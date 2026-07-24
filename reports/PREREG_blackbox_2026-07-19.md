# Pre-registration — Track 3 "black-box": does the direct model know SLE thermodynamics?

Committed BEFORE any number is computed. Metrics, thresholds, and both readings are fixed here.

Date: 2026-07-19. Compute: probes on frozen representations are cheap (CPU / small GPU); distillation
(Study 3) and T-sweeps (Study 2) need GPU (GCP). Status at registration: no probe number computed yet.

## Overarch question
Does a black-box DirectGNN (trained on solubility, never given physics) internally represent the known SLE
structure `ln x2 = −Φ(T) − ln γ2` (crystal + activity, two additive terms) — and if not, by what
organisation does it generalise?

## Distinctive asset
An **external oracle for every term**, which emergent-physics-probing work lacks: crystal (Tm, ΔH_fus —
measured, ~31 solutes), activity (ln γ2∞ — ThermoML IDAC, n=44/60), σ-profile (VT-2005). The contribution
is not "probe for physics" (done) but **making the murkiness measurable against a known ground truth**.
Honest ceiling: competent-plus in a crowded field; value is as a calling-card program, not a landmark.

## Cross-cutting discipline (all studies)
1. Pre-registration commit before any number (this file).
2. Probe-artifact controls (the field flags these, not optional): capacity (linear AND MLP), selectivity
   (vs random targets), raw-feature null (RDKit/Morgan), shuffle null.
3. "Label = sum" trap: the label IS crystal + activity, so decode+decode ≈ label is trivial. The signal is
   **separability/factorisation** in the representation, not correlation.
4. Crystal↔activity co-correlation: both co-vary with structure; probe against **measured** oracles, and
   report partial effects (each controlling the other).
5. m-mediation: everything is downstream of the label; nulls isolate "structure beyond the label".
6. Effective-n by SOLUTES not rows (crystal oracle ~31, σ/activity 44/60) — leverage-fragile; 3 seeds, drop-one.
7. Checkpoint validity: real DirectGNN checkpoint at 1.70 MAE, confirmed layer (512-d pair representation),
   not a stand-in.

## Study 1 — does the model separate crystal and activity? (core, cheap, branches everything)
Frozen pair-representation `h_BB ∈ R^512`. Oracles: `Φ*(mol,T)` (crystal, ~31 solutes), `ln γ*` (activity, n=44/60),
`ŷ_BB` (model's own prediction).
- 1a decodability: linear AND MLP probes `h_BB → Φ*` and `h_BB → ln γ*`. **Pre-predict** R²(model) − R²(raw) ≥ 0.1,
  shuffle ≈ 0. **Kill:** no lift over raw features → decodability trivial → jump to Study 4.
- 1b separability (the SLE signal): principal angles between the crystal and activity subspaces;
  cross-decodability. **Confound (mandatory):** Φ* and ln γ* themselves correlate; test whether the crystal
  subspace decodes activity **beyond** `corr(Φ*, ln γ*)`, not beyond zero. Pre-predict: separability partial.
  **Kill/branch:** full entanglement → no two-term structure → Study 4.
- 1c additive reconstruction: is `−P_cryst(h_BB) − P_act(h_BB) ≈ ŷ_BB`? The non-trivial test is whether the
  model's OWN prediction decomposes additively onto the **separable** subspaces from 1b (not whether decode+decode
  hits the label). Kill: low reconstruction of ŷ_BB from separable parts → not additive in these factors.
- Capacity is decisive: linear separability/reconstruction = strong evidence; MLP-only = the probe manufactures
  the structure. Report both; lead on linear.

## Study 2 — temperature structure (functional form)
- 2a: fix a molecule, vary T; does the response factorise as `crystal(1/T) + activity(T)`?
- 2b: does `∂(ln x2)/∂(1/T)` recover the slope `ΔH_fus/R`? (direct test of learned crystal thermodynamics.)
Pre-predict: partial / probably not (structured van't-Hoff classes extrapolate T better than the box).
Kill: no factorisation and slope does not track ΔH_fus → informative negative feeding Study 4.
Discipline: crystal oracle ~31 solutes — leverage; report solute count.

## Study 3 — closure inside (folds in the separate closure-probe protocol)
Runs ONLY if Study 1 yields an activity subspace. Full Gate 1/2/3 of `PREREG` closure probe:
Gate 1 (encodes physics at all), **Gate 2 (killer): partial-R²(r | m)** — does the box encode the closure-error
*structure* beyond the scalar m; Gate 3: structural convergence with the 52-param residual (overlap ≫ m-driven null).
Most likely death at Gate 2 (everything downstream of m). That is an informative negative.

## Study 4 — if not physics, then what? ("murky made measurable" — the distinctive contribution)
Always run; also the fallback if 1–3 are negative/murky.
- 4a unsupervised structure of `h_BB`: dominant modes; do they answer to scaffold identity, solvent class, crude polarity?
- 4b does the box organise by **data-statistical** structure (scaffold/solvent clusters) rather than physical?
- 4c **quantify the physical fraction**: how much of the box's organisation is SLE-aligned vs not, **against the oracle**.
Pre-predict: a significant non-physical fraction; its characterisation is the contribution.

## Study 5 — synthesis: knowledge vs use
Relate what the box **learned** (physical fraction) vs what it **uses** (non-physical organisation), and the
consequence: does the physical fraction predict OOD transfer; does the non-physical part explain the
scaffold-transfer limit.

## Branch map (cannot-fail-to-inform at the program level)
- Clean positive (1–3 pass): the box rediscovers SLE thermodynamics from data.
- Murky/partial (expected per lit-check): the box is partly physical; here is the **measurable** physical
  fraction and what is not — the distinctive contribution (oracle makes murkiness measurable).
- Negative (Study 4 dominates): the box solves solubility by non-physical organisation; here it is, and here
  is why it limits scaffold transfer.
Each branch is a paper.

## Order
Gate 0 (lit-check done: neighbourhood mature; landmark not extractable — competent-plus ceiling, accepted) →
pre-registration commit (this file) → Study 1 (core, cheap, branches) → Study 2 → Study 3 (iff activity subspace)
→ Study 4 (always/fallback) → Study 5 (synthesis).
