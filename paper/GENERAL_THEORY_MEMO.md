# General-theory expansion memo — "When does a differentiable physical bottleneck pay?"

Status: VERIFIED + CORRECTED (2026-07-11) after a hostile-referee pass. Scope decision: user chose "1+2"
(T1+T2 abstraction + synthetic cross-domain, AND T3 phase diagram + one real second domain).

**Verification outcome (adversarial referee, 2026-07-11).** T1.1–T1.4, the T1.3 identity, the T2 sign
rule, and corollaries C1/C2 are all **algebraically correct under the explicit assumptions A1+A2** — two
worked finite counterexamples could not break the sandwich `0 ≤ Γ ≤ B_clos` within A1+A2. BUT:
- **A1 (`φ*∈H`, encoder recovers the true intermediate) is empirically FALSE here** (linear-probe test
  R²≈0.45). Without A1, `Γ ≥ 0` is not guaranteed (Counterexample B: `Γ=−1/4`).
- **A2 (lossless/sufficient bottleneck) is unverifiable** without the oracle, and physically dubious for
  σ-profiles (the graph carries H-bond/conformer information the profile discards). Without A2 the
  certificate fails: **Counterexample A gives `B_clos=0` yet `Γ=1>0`** — a positive grounding gap can be
  pure input-insufficiency, not closure bias.
This forced the corrected framing below: **the assumption-light instrument is the decomposition (Lemma 3);
`Γ` is a *symptom / corollary* whose proxy-validity is characterized, not the headline certificate.** This
avoids repeating the refuted "conditional-optimality iff" at a larger scale.

This memo lifts the solubility-specific result of `grounding_paradox.tex` to a general theory of
**composed predictors** `ŷ = g(h(x))` with a *fixed* physical closure `g` and a *learned* physical
intermediate `z = h(x)`. Solubility becomes one instance. The three existing Lemmas (non-identifiability,
class-dependent efficient information, exact closure/insufficiency decomposition) are already stated at
this level of generality — this memo adds the two claims that make the theory *predictive* rather than
merely descriptive, and does so **without** reintroducing the refuted "conditional-optimality iff"
(all new claims are about the SIGN / a DIAGNOSTIC, never about an optimum).

---

## General setup (domain-free)

- Inputs `X`; the physical quantity the closure produces `m` (in solubility: `m = lnγ` activity target).
- A physical intermediate / latent `Z` that the closure consumes (in solubility: the σ-profile).
  **Grounding premise:** the intermediate is recoverable from inputs, `Z = φ*(X)` for some `φ* ∈ H`.
- A **fixed** (non-fitted) closure `g : Z → m̂` (in solubility: differentiable COSMO-SAC). NOT trained.
- Encoder class `H` (maps `X → Z`). The composed predictor is `g∘h`, `h ∈ H`.
- External oracle supplies the true `Z*` at evaluation (the σ-oracle arm).

Population quantities (all expectations over the data law):

| symbol | definition | meaning |
|---|---|---|
| `B_insuff` | `E[Var(m | Z*)]` | input insufficiency — irreducible given the intermediate |
| `B_clos`   | `E[(E[m|Z*] − g(Z*))²]` | closure mis-map — systematic decoder error |
| `R_orc`    | `E[(m − g(Z*))²]` | oracle-through-closure risk |
| `R_e2e`    | `inf_{h∈H} E[(m − g(h(X)))²]` | best end-to-end composed risk |
| `R_free`   | `E[(m − E[m|X])²] = E[Var(m|X)]` | Bayes risk of a free predictor on X (black box) |

**Lemma 3 (already in paper), unconditional for fixed `g`:** `R_orc = B_insuff + B_clos`
(cross term vanishes because `E[m|Z*] − g(Z*)` is `Z*`-measurable).

---

## T1 — Grounding-gap theorem (misspecification certificate)  [NEW, provable]

**Assumptions.**
- (A1) *Representability:* `φ* ∈ H`, so `h = φ*` is feasible and `g(φ*(X)) = g(Z*)`.
- (A2) *Lossless bottleneck (sufficiency):* `E[m|X] = E[m|Z*]` — the physical intermediate carries all
  input information about `m`. (This is *the premise under which grounding is supposed to work*; a
  violation is itself diagnostic, see Remark.)

Define the **grounding gap** `Γ := R_orc − R_e2e` (measurable: oracle arm minus end-to-end arm).

**Claims.**
1. **(unconditional under A1)** `R_e2e ≤ R_orc`, i.e. `Γ ≥ 0`. *Proof:* `φ*` is a feasible `h`, so the
   infimum defining `R_e2e` is `≤` its value at `φ*`, which is `R_orc`. ∎
2. **(sandwich, under A1+A2)** `0 ≤ Γ ≤ B_clos`. *Proof:* every `g(h(X))` is `σ(X)`-measurable, so
   `R_e2e ≥ R_free`. Under A2, `R_free = E[Var(m|X)] = E[Var(m|Z*)] = B_insuff` (equal conditional
   variances: `Var(m) = E[Var(m|X)] + Var(E[m|X]) = E[Var(m|Z*)] + Var(E[m|Z*])`, and A2 makes the two
   `Var(E[·])` terms equal). Then `Γ = R_orc − R_e2e ≤ R_orc − R_free = (B_insuff + B_clos) − B_insuff = B_clos`. ∎
3. **(equality / full compensation, under A2 + attainment)** `Γ = B_clos − (R_e2e − R_free)` where
   `R_e2e − R_free ≥ 0` is the *residual composed-approximation error* (unconditional: every `g(h(X))` is
   `σ(X)`-measurable so `R_e2e ≥ R_free`). Hence `Γ = B_clos ⟺ R_e2e = R_free`. (State it as
   `R_e2e = R_free`, **not** as "∃h: g(h(X))=E[m|X] a.s." — the latter is strictly stronger unless the
   infimum is attained, i.e. `H` is closed in L². Witness: `X∼U[0,1]`, `m=X`, `g=\mathrm{id}`,
   `H={h_c:cx, c∈[0,1)}` gives `R_e2e=R_free=0` with no attaining `h`.)
4. **(proxy, NOT a standalone certificate)** Under A1+A2: if `g` is well-specified on the support
   (`B_clos=0`) then `Γ=0`, so within A1+A2 `Γ>0 ⟹ B_clos>0`. **This certificate holds ONLY under A1+A2.
   Both fail here, so `Γ>0` alone does not certify closure misspecification** (see Remark).

**Interpretation.** Under A1+A2, `Γ` is "how much of the closure bias the encoder silently absorbs by
feeding the closure a *wrong-but-useful* intermediate" — the formal content of the paper's prose ("a free
head can silently absorb crystal error"). `Γ` is a cheap *symptom* (one oracle ablation), not the
instrument. Two caveats on measurement: (i) the estimate uses the *trained* e2e model, whose risk is
`R_e2e + V_phys(n) ≥ R_e2e`, so `Γ̂` is **downward-biased** — a positive reading conservatively signals
`Γ>0`, a non-positive reading is inconclusive; (ii) `R_orc` and `R_e2e` must be scored on the identical
test law for `Γ` to be meaningful.

**Remark (the grounding gap conflates two causes — this is the contribution, not a footnote).**
`Γ>0` has **two** possible causes, and A1/A2 are exactly what would rule the second one out:
- (i) *closure bias:* `g` is misspecified on the true `Z*` (`B_clos>0`) — the intended reading;
- (ii) *input-insufficiency / off-support exploitation:* the intermediate is a **lossy** bottleneck
  (A2 fails, `E[m|X]≠E[m|Z*]`), and the encoder smuggles input information the intermediate discards by
  driving a *correct* `g` off-support as a lookup table.
  **Counterexample A (worked):** `X∈{a,b}` uniform; `Z*≡0` (A1 holds, constant map); `m(a)=+1,m(b)=−1`;
  `g(−1,0,1)=(−1,0,1)`. Then on `supp(Z*)={0}`, `g(0)=0=E[m|Z*]`, so `B_clos=0`; `R_orc=1`; an encoder
  `h†(a)=1,h†(b)=−1` gives `g(h†(X))=m`, `R_e2e=0`, so **`Γ=1>0` with `B_clos=0`.** The sandwich
  `Γ≤B_clos` reads `1≤0` — it genuinely needs A2.
**Therefore certification of closure misspecification does not rest on `Γ`. It rests on the
convention-independent decomposition (Lemma 3), which needs neither A1 nor A2:** the Jensen lower bound
`B_clos ≥ (E[m]−E[g])²` and the LOTV/RF upper bounds on `B_insuff`. In the solubility instance these give
`B_clos ≥ 0.72` (nats², `full` closure) with `B_insuff` separately bounded, so `B_clos` dominates *by
direct measurement*; the observed `Γ>0` (σ-oracle worse than learned-σ) is then **corroboration**, not the
proof. The honest headline is: *the decomposition is the instrument; `Γ` is the symptom that motivates it;
distinguishing cause (i) from cause (ii) is what the decomposition buys.*

---

## T2 — Physics-tax sign rule and the critical data budget  [NEW; structural claims provable, V(n) empirical]

Finite-sample comparison of the *trained* physics model vs the *trained* black box. Decompose expected
test risk of each into population asymptote + estimation variance:

    E[R̂_phys(n)]   ≈  R_e2e   + V_phys(n)
    E[R̂_direct(n)] ≈  R_free  + V_direct(n)

with `V(n) ↓ 0` as `n → ∞`. The **physics tax** is

    T(n) := E[R̂_phys(n)] − E[R̂_direct(n)]  ≈  Δ∞ + [V_phys(n) − V_direct(n)],
    where  Δ∞ := R_phys,∞ − R_direct,∞     (fair asymptotic gap of the two trained arms).

**Honest definition of Δ∞ (referee fix).** The clean identity `Δ∞ = R_e2e − R_free = B_clos − Γ` holds
**only if the control is asymptotically Bayes on X** (`R_direct,∞ = R_free`, universal approximation +
consistency) AND A2. The deployed DirectGNN shares our encoder and has its own approximation error
`A_direct = R_direct,∞ − R_free ≥ 0`, so the *fair* asymptotic tax is `Δ∞ = R_e2e − R_direct,∞`, whose
sign is **not** pinned to `≥0` a priori — physics could in principle win asymptotically. We therefore treat
`Δ∞` as an **empirically measured** quantity (the large-`n` end of the data-efficiency sweep), and the
identity `Δ∞ = B_clos − Γ` as the *idealized-Bayes-control* interpretation, flagged as such. Empirically
`Δ∞ > 0` (physics trails at full data), which is what the corollaries consume.

- **Sign rule (algebra, given the decomposition):** `T(n) < 0` (physics helps) ⟺
  `V_direct(n) − V_phys(n) > Δ∞`. The variance benefit (`V_phys ≤ V_direct`, fewer effective DOF through
  the bottleneck) must exceed the asymptotic gap `Δ∞`.
- **Corollary C1 (critical budget).** If `Δ∞ > 0` and the variance gap `D(n) := V_direct(n) − V_phys(n) →
  0` (both arms consistent), there exists a **critical `n*`** beyond which `T(n) > 0` for all `n > n*`.
  *(Existence of `n*` needs only `D(n)→0`, not monotonicity.)* The stronger "hurts at **every** `n`"
  reading additionally needs `D(n)` to stay below `Δ∞` throughout, which we take as an empirical
  observation, not a theorem. → *Retrodicts the data-efficiency null:* tax `+0.08` at 5% up to `+1.0` at full.
- **Corollary C2 (aleatoric floor).** Backbone inequality `D(n) ≤ V_direct(n)` (since `V_phys ≥ 0`): the
  variance benefit can never exceed the control's own estimation variance. As the black box nears the
  noise floor `V_direct(n) → 0`, so `D(n) → 0` and `T(n) → Δ∞ ≥ 0` (empirically). → *Retrodicts the
  novelty-inversion:* the physics tax is largest on the *cleanest / best-covered* chemistry, not the hardest.

**Which parts are theorems vs empirics.** Provable: `R_e2e ≥ R_free` (unconditional); the sign-rule
algebra; existence of `n*` given `Δ∞>0` and `D(n)→0`; the `D(n) ≤ V_direct(n)` backbone. Idealized (needs
Bayes control + A2): the identity `Δ∞ = B_clos − Γ`. Empirical: the *shapes* of `V(n)`, the sign
`Δ∞ > 0`, and the "every-`n`" strengthening. We claim no closed form for `V(n)`.

---

## "When does this recur?" (the user's question, answered by the theory)

A differentiable physical bottleneck is **predicted to hurt** exactly when both hold:
1. **Un-compensatable closure bias** `Δ∞ = B_clos − Γ > 0` — the closure is misspecified *and* the
   encoder cannot fully undo it (measure via T1: oracle-vs-e2e gap `Γ`, and oracle-vs-blackbox asymptote).
2. **Mature-data / low-noise regime** `n > n*` or near the aleatoric floor — where the variance benefit
   that a prior buys has evaporated (T2, C1/C2).

This is precisely the regime modern ML lives in (large corpora, expressive encoders near the label-noise
floor), which is why the failure is not idiosyncratic to solubility. The *diagnostic protocol* is
reusable and is **decomposition-first, not `Γ`-first**: (i) measure the split `B = B_insuff + B_clos` via
its convention-independent bounds (needs no A1/A2); (ii) if `B_clos` dominates, the closure — not the
inputs — is the ceiling; (iii) the oracle gap `Γ>0` corroborates and cheaply flags it, but only
*certifies* misspecification when combined with (i), because `Γ` alone conflates closure bias with
input-insufficiency (Counterexample A). (iv) estimate `Δ∞` empirically from the large-`n` asymptote; if
`Δ∞>0`, the physics bottleneck loses past `n*`.

## What we still do NOT claim (guardrail against the refuted iff — and now against a second over-reach)
- No "optimal grounding" theorem; no necessary-and-sufficient condition for OOD accuracy improvement.
- **`Γ>0` is NOT a standalone certificate of closure misspecification** (it needs A1+A2, both of which
  fail/are-unverifiable here). The certificate is the decomposition; `Γ` is a symptom.
- All surviving claims are about the **sign** of the tax and an assumption-light **decomposition**, never
  an optimum. `B_insuff`, `B_clos` (bounds), and `Δ∞` are *measured*; A1/A2 are named where used.

---

## Execution roadmap for "1+2"

**Phase 1 — theory abstraction (LOCAL, no GPU).** Restate Lemma 3 at the `g∘h` level (already is);
add T1 (statement+proof) and T2 (statement, provable corollaries) to `sec:framework` with solubility as
the running instance. Adversarially verify before committing. *[this memo = the draft]*

**Phase 2 — synthetic cross-domain (LOCAL, no GPU).** Write the **general fidelity-dial engine** as a
committed, reusable script `scripts/analysis/run_fidelity_dial.py` parameterized by
`(teacher map, closure family, misspecification functional, F, n, sufficiency-flag)`. It must:
(a) *reproduce* the paper's current dial numbers (F=1.00→0, 0.76→−0.096, 0.38→−0.247, −0.50→−0.605) —
closing the reproducibility hole;
(b) instantiate 2–3 **non-chemistry** teacher/closure families (kinetics-like exponential closure, a
PDE-surrogate-like closure, a generic monotone-nonlinear closure) to show the decomposition + T2 (`n*`
appears) hold across domains — *pays for "general"* cheaply;
(c) **turn Counterexample A into a figure:** with `sufficiency-flag` we CONTROL A2. Show (i) under A2,
`Γ` tracks `B_clos` (the proxy is valid); (ii) violate A2 with a *well-specified* closure and exhibit
`Γ>0` while `B_clos=0` — demonstrating empirically why `Γ` alone is not a certificate and why the
convention-independent decomposition is the actual instrument. This converts the referee's strongest
attack into the paper's cleanest didactic result.

**Phase 3 — one REAL second domain = pKa via a fixed Hammett/Taft LFER closure.**
CLOSURE CORRECTION: Henderson–Hasselbalch is the WRONG map (it predicts a solution's pH from a known
pKa, not pKa from structure — not misspecifiable in the needed sense). The right fixed physical closure is
the **Hammett/Taft LFER** `g(σ) = pKa₀ − ρ·σ`: a fixed, approximate map over the physical intermediate
`σ` (electronic substituent effect), with a **tabulated oracle** (Hansch–Leo σ constants) — the tight
analog of COSMO-SAC-over-σ-profile. The two classic LFER failure modes map exactly onto the two channels:
*resonance saturation* (a nonlinearity in σ the linear closure can't represent) → `B_clos`; *ortho/steric
field effects* (absent from tabulated σ) → `B_insuff`.
Scope decision (user): **fidelity-sweep** over classic aromatic series (benzoic acids / phenols / anilines
/ pyridines), split high-F (para) vs low-F (ortho/proximal/polyfunctional) → **multiple phase-diagram
points** that test the theory's *predictive* claim (predict the sign of the tax from measured F̂/`B_clos`
before the accuracy comparison), not just "another null."

*Local scaffolding — DONE & validated (`scripts/analysis/run_pka_hammett_probe.py`,
`results/pka_hammett/probe.json`, `paper/figs/fig_pka_hammett.{pdf,png}`):* Hammett closure + Hansch–Leo σ
table + the grounding-test/decomposition harness, checked on a semi-synthetic Hammett series with
closed-form ground-truth `B_clos`/`B_insuff`. Estimators match truth (e.g. `B_clos` true/est 0.20/0.21,
0.40/0.40, 0.81/0.81); LOTV upper bound valid; the fidelity sweep shows `Γ` tracking `B_clos` and the
ortho-insufficiency sweep reproduces Counterexample A in the pKa domain (`B_clos=0`, `Γ>0`).

*Dataset locked (2026-07-11, user "любой, главное качество и полнота"):* **DataWarrior/OPERA curated
EXPERIMENTAL pKa set** (Mansouri et al. 2019, J. Cheminform.; public domain → redistribution-clean;
~7.9k, rich in monofunctional aromatics). Deliberately AVOID ChEMBL/Epik *calculated* pKa (circular for a
study of model/closure behavior). Quality caveats baked into the pipeline: macro-vs-micro pKa (restrict to
monoprotic aromatics with an unambiguous ionizing group), and ortho→`B_insuff` (not noise).

*Production substituent→σ parser — DONE & self-tested (`scripts/data/build_pka_hammett_subset.py`):*
scaffold detection (benzoic acid / phenol / anilinium / pyridinium), ring-distance position assignment
(ortho/meta/para), substituent→Hansch-Leo σ mapping (~19 substituents), high_F (meta/para) vs low_F
(ortho/unknown) binning = the fidelity sweep. Self-test 7/7; and it already exhibits the closure
misspecification on real molecules (p-nitrophenol LFER 8.25 vs exp ~7.15; p-nitroaniline 2.44 vs ~1.0 —
σ⁻ resonance saturation the linear closure cannot represent = `B_clos` in the wild).

*Still gated (Modal + get the file):* (1) obtain the public-domain OPERA/DataWarrior CSV (do not download
without confirmation) → run the builder → real Hammett subset; (2) shared graph encoder + DirectGNN
control trained on real pKa (Modal); (3) place the real `(F̂, Δ∞, n)` points on the phase diagram.
Alternatives if pKa data stalls: vapor pressure (Antoine/Clausius–Clapeyron), viscosity (fixed correlation).

**Phase 4 — phase diagram + reframe.** Assemble the `(closure fidelity, rank-deficiency, n, aleatoric
floor)` axes into a predicted help/hurt boundary; overlay solubility + synthetic families + the real
second domain. Retitle/reframe the paper from a solubility null to a general diagnostic
("the grounding test") + phase diagram. Solubility stays as the anchoring case study.
