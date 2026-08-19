# Concept note — The Grounding Budget

**A closure-Jacobian law for the minimum single-component supervision that converts an
imitating latent into a physical one.**

*Draft 2026-07-15. Fused top-pick from the "know-vs-imitate / recover-structure" ideation
(directions #2+#3+#4, with the escape move from #6).*

**Status: T0 PASSED (2026-07-15).** Synthetic kill-test
(`scripts/analysis/run_grounding_budget_t0_synthetic.py`, results
`reports/RESULTS_grounding_budget_t0_2026-07-15.txt`, 5 seeds): the H1 mechanism is confirmed —
Fisher-null-targeted labels collapse the compensation gauge to the noise floor at exactly
`k = ker_dim` (ker rel 0.037) while random labels do not (2.15): ~58× at equal budget. Two honest
caveats recorded: (i) the residual full-recovery error is encoder-limited *range* identification,
not the gauge — a live preview of Risk 2; (ii) H2 (firewall under misspecification) is directionally
demonstrated (full 1.24 vs 3.20) but high-variance.

**Update — H2 tightened and did NOT survive (2026-07-15).** A focused, robust co-design test
(`scripts/analysis/run_grounding_budget_t0_h2.py`, results `reports/RESULTS_grounding_budget_t0h2_2026-07-15.txt`;
gradient-clipped, median±IQR over seeds, clean encoder baseline): the earlier "demonstrated" was a
numerical-blow-up artifact of a few unclipped seeds. With that controlled, neither H2 signature
appears — the firewall's advantage does not grow with ε (Panel A: error even *falls* with ε), and the
cap-sweep shows no clean U-shape (Panel B). Diagnosis: the bilinear closure ψ(z)ᵀKψ(z) carries a
residual rotation gauge in ψ-space (K-metric-preserving rotations) that floors *range* recovery at
~1.2 and buries the O(ε) co-design signal; the ε-perturbation even *breaks* that gauge, explaining the
paradoxical improvement. **The toy structurally cannot test H2.** Honest consequence: **H2 (co-design)
is downgraded from a claim to an open conjecture** — to be tested directly on the real system (T1) or
in a purpose-built non-bilinear toy, not asserted. The program now stands on **H1 (robustly confirmed)
+ H3 (the experimental-γ∞ escape, concrete but untested).**

**Update — T0.5 run, program FALSIFIED on the real closure (2026-07-15).**
(`scripts/analysis/run_grounding_budget_t05_real_closure.py`, results
`reports/RESULTS_grounding_budget_t05_2026-07-15.txt`; real VT-2005 profiles, no training/checkpoint.)
The real COSMO-SAC σ→lnγ Jacobian is essentially **RANK-1** — participation ratio 1.0, second
eigenvalue <0.1% of the first, dominant eigenvector concentrated on ~2 σ-bins (the HB region). Robust
across composition (γ∞ and x₂=0.1), temperature, area-projection, and 100 solutes. So the ill-constrained
(compensation-prone) subspace is **~49/51**, not low-dimensional. The "cheap universal anchor basis"
premise (H1) requires a *low-dimensional* ill-constrained subspace; on the real closure there is none —
activity constrains ~1 direction, so grounding the profile needs ≈the full external profile (= supervised
σ-prediction, already solved), not a few clever anchors. **The grounding-budget program does not survive
contact with the real closure.** This is the pre-registered T0.5 falsification condition, in its extreme
form.

**What survives (the real, honest finding).** T0.5 produced a sharp, novel, quantitative result:
*the COSMO-SAC activity closure is a rank-1, HB-bin-localized bottleneck on the σ-profile.* This precisely
characterizes WHY the physics-informed σ-latent is non-identifiable (the grounding-paradox paper's core
claim) and gives it a physical locus (the HB bins). **Recommendation: fold this rank-1 characterization
back into the existing paper as a sharper mechanism for the non-identifiability; retire the standalone
grounding-budget program.** The kill-test ladder did its job — killed the speculative program in an
afternoon, on real data, and extracted a paper-strengthening finding.

---

## 0. The compass (why this, honestly)

The research question is not "beat FastSolv." It is the anti-black-box question:
**when has a scientific model learned real structure rather than a compensating imitation,
and can we make the structure be there and read it out?** The current solubility paper
answered a narrow instance in the *negative* (the end-to-end σ-profile latent is a
compensating surrogate, not the physics) and stopped at diagnosis — which is why it landed
"modest." This note flips the vector from **diagnosis to construction** on the same apparatus.

## 1. Core claims

- **H1 (the grounding-budget law).** For a fixed differentiable closure `C` (COSMO-SAC over a
  network-predicted σ-profile), the compensation lives predominantly in the directions of the
  σ-field that γ-fitting leaves *ill-constrained* — the low-singular-value subspace of the
  closure Jacobian `J = ∂γ/∂σ`. Therefore the minimal set of single-component anchor labels
  that pins the latent to the true physical field is **computable from `C` before any
  experiment**: `k* = eff-dim(ill-constrained subspace)`, and the anchor *identities* are that
  subspace's basis. Labels chosen to span it convert the latent at a strictly smaller budget
  than random/uniform labels (**targeted ≫ random at equal budget**).

- **H2 (the co-design refinement — the guessable-by-nobody part).** Under a *misspecified*
  closure, anchoring alone leaves `O(1)` latent error: the closure's error launders back into
  the very subspace the anchors were meant to pin, and the model re-compensates elsewhere. Only
  **jointly sizing the anchor set AND a bounded correction head from `J`** recovers `O(ε)`
  physicality. The anchor-budget and the correction-cap must be co-derived — a
  number-and-direction pair that neither optimal experimental design nor discrepancy-modeling
  yields separately.

- **H3 (recover what the closure cannot compute — the escape from "why not predict σ
  directly?").** The load-bearing positive result is not σ-profile reconstruction (a supervised
  predictor dominates that, and σ-profiles are low-rank so recovery is fakeable). It is that the
  grounded latent decodes, on **held-out** molecules, to a quantity the closure never labels and
  that was never in training — **experimental γ∞ (IDAC)** — proving the physics is genuinely
  present, not a low-rank coincidence.

## 2. The constructive object (deliverables, not a diagnostic)

1. **A design law + algorithm.** Point the tool at your differentiable closure; it reads the
   ill-constrained subspace of `J` and returns `k*` and the specific single-component labels to
   collect. A pre-training design rule: *"measure these, and the surrogate cannot survive."*
2. **A co-design theorem** (H2): anchor-budget × correction-cap → `O(ε)` physicality under
   bounded misspecification, with the separation that anchoring-without-correction cannot achieve.
3. **A positive recovery result** (H3): held-out γ∞ decoded from the grounded latent, beating the
   compensating baseline by a margin that tracks the closure-only-computed budget.

## 3. Novelty map (honest)

- **Scooped / not novel — do not sell as new:** identifiability up to a group from auxiliary
  variables (iVAE / nonlinear-ICA, Khemakhem–Hyvärinen); disentanglement impossibility
  (Locatello 2019); optimal experimental design / Fisher-information anchor selection for
  low-dim parametric grey-box models; symbolic-law recovery from GNN latents (Cranmer 2020);
  supervised σ-profile prediction (TeNNet-SAC, CNN/GCN on VT-2005) — already solved, so the
  trivial "label N → σ" baseline must be *beaten*, not reinvented; a-priori vs a-posteriori
  closure training (turbulence/PDE-ML) — direct supervision keeps a closure physical, end-to-end
  makes it compensate (a known dichotomy).
- **The genuinely open sliver (defensible):** (a) the closure-Jacobian null-space **label-selection
  rule** for a *fixed physical closure whose latent is a high-dim field absorbing misspecification*
  — the targeted-≫-random equal-budget separation is the one thing iVAE/OED/PINN-misspecification
  do **not** give; (b) the **co-design** theorem (H2); (c) recovering an **experimental** quantity
  the closure cannot compute as the proof of physicality (H3). The paper must **lead** with (a)+(b)+(c)
  and demote the correct-closure budget (textbook observability) to a sanity check.

## 4. Kill-test ladder (staged; each gate is decisive)

- **T0 — afternoon, MacBook CPU, no GNN.** Synthetic controlled closure: known low-rank `z*`, a
  COSMO-like nonlinear `F` with a *tunable* null space. Three arms at **equal label budget k**:
  (1) end-to-end, y-only; (2) + k **random** σ-labels; (3) + k **null-space-spanning** labels +
  capped-correction firewall. Metric: held-out `‖ẑ−z*‖` (mod known symmetry) vs y-fit.
  **Falsify the whole program if:** (3) does not decisively beat (1) *and* (2); OR (1) already
  recovers `z*` (no compensation to fix); OR targeted ties random at equal budget.
- **T0.5 — afternoon, MacBook.** On the *real* trained checkpoint, measure the effective rank of
  the `ẑ→σ` distortion (reuse `run_compensation_surrogate.py` PCA residual spectrum) and whether
  the ill-constrained subspace of the real closure Jacobian is approximately **global**
  (molecule-independent) across diverse solutes. This is the load-bearing real-closure assumption
  behind "a cheap *universal* anchor basis." **Falsify "cheap universal basis" if** the kernel is
  high-rank / strongly point-dependent (→ budget balloons to "label everything").
- **T1 — a few T4 GPU-hours.** Retrain with k **targeted** vs k **random** single-component labels
  (true σ from VT-2005), equal budget. Headline metrics on **held-out scaffolds**: (i) σ recovery
  vs QC truth; (ii) γ∞ recovery (IDAC); (iii) residual decomposed into **gauge error vs
  encoder-transfer error**. Success = targeted ≫ random on *generalized* recovery, with the
  transfer term reported separately (see Risk 2).
- **T2 — stretch.** "The law reads out": does the fixed COSMO-SAC `γ(σ,σ′)` relation predict
  activity on held-out pairs from the *recovered* field it was never supervised on.

## 5. Reuse (your current work is a genuine fragment)

| Need | Existing artifact |
|---|---|
| Premise: compensation is structured & low-rank | `run_compensation_surrogate.py`, `diagnostics/compensation.py` |
| Caveat that forces co-design (drift ≠ closure's 1st-order inverse) | `run_picard_compensation_test.py` |
| Verification backbone (closure-vs-input, Fisher) | `run_decomposition_identifiability.py`, `run_identifiability_fisher_audit.py` |
| The latent ẑ and the fixed closure | `heads.SigmaProfileHead`, `layers.CosmoSacLayer` |
| The capped correction head + stop-gradient firewall | bounded adaptive correction in `solver.SLESolver`; `diagnostics/gradient_flow.py` |
| External QC σ-profile oracle (**already ingested**) | `ingest_vt2005_sigma_profiles.py`, `build_sigma_profile_aux_stream.py` |
| The "closure-can't-compute" target: γ∞ | `build_idac_aux_stream.py`, `attach_idac_aux_to_fixed_splits.py` |
| Supervision/closure-fidelity dial (theory of when gauge is trivial) | `run_closure_fix_dial.py`, `run_b_insuff_leverage.py` |
| Closure-diversity secondary axis (dsp / variants) | `run_closure_variant_control.py`, `run_closure_flip_ci.py` |

## 6. New to build

- The **anchor-selection algorithm**: ill-constrained subspace of `J` → `k*` + anchor basis.
- The **co-design analysis** (H2): joint anchor-budget × correction-cap → `O(ε)`.
- The **synthetic controlled-closure testbed** (T0) with a tunable null space.
- The **global-vs-local kernel measurement** (T0.5) on the real closure.
- The **generalized-recovery + residual-decomposition** protocol (T1).

## 7. Deflation risks + escapes (neutralize before spending GPU)

1. **Textbook-shadow / scooping.** Correct-closure budget is observability theory; the
   misspecification frontier is actively worked by 2026 groups. *Escape:* make the **co-design
   separation** (H2) and **targeted ≫ random** (H1) the headline, **pre-registered** as a
   guess-in-advance number/direction that OED and discrepancy-modeling cannot produce separately.
2. **The transfer-limited encoder (test R²≈0.45) — the same wall that capped the current work.**
   Anchors pin the latent where you measured; recovery on unmeasured scaffolds is an
   encoder-generalization problem the gauge theory does not touch. *Escape:* headline = *generalized*
   (held-out) recovery; explicitly **decompose the residual into gauge error vs encoder-transfer
   error** and show anchors kill the gauge part while you report the transfer part honestly.
3. **"Why not predict σ directly?"** A supervised σ-predictor dominates recovery-of-σ. *Escape:* H3
   — recover **experimental γ∞** the closure cannot compute; that is "knowledge you could not
   otherwise extract is provably in there," not a re-derivation of COSMO's own input.

## 8. Pre-registered falsification (commit before running)

- T0: targeted must beat random *and* end-to-end at equal budget, else the novel core is dead.
- T0.5: the real closure's ill-constrained subspace must be approximately global, else no cheap
  universal basis.
- T1: targeted must beat random on **held-out** (not on-anchor) recovery, and γ∞ recovery must
  exceed the compensating baseline; a purely on-anchor win does **not** count.

## 9. Honest ceiling

**Borderline-top-ml** (both adversarial lenses agreed), constructive, **low compute** (every
decisive gate T0/T0.5 is synthetic/CPU on a MacBook; only T1 needs a few T4-hours). Two named
ways to deflate (§7.1, §7.2). This is **not a safe bet** — it is a real swing with a real chance
of missing, gated so a single afternoon (T0) tells you whether to continue. That risk profile is
the point: modest work is what you get by choosing the safe, diagnostic side of a capped problem;
this chooses the risky, constructive side.

## 10. Decision structure

```
T0 (afternoon, CPU) ──fail──▶ program dead; cost = one afternoon. Fold H1 into a smaller note.
        │ pass
T0.5 (afternoon, CPU) ──fail──▶ no universal basis; pivot to per-family basis or temperature axis.
        │ pass
T1 (few T4-hrs) ──fail──▶ encoder-transfer wall dominates; honest negative + the T0 synthetic law survives as the contribution.
        │ pass
T2 (stretch) ──▶ "the law reads out" headline.
```
