# Execution roadmap — SCOPE LOCKED TO **A++** (2026-07-11)

> **A++ (method-forward exhaustive-negative), chosen after the data-efficiency null.** Thesis: a reusable, proved method to locate where a physics prior's ceiling lives (closure vs inputs vs labels), hooked on the grounding paradox, with the exhaustive negatives (full-corpus tax, temperature=van't-Hoff-class-not-model, crystal dose-limited null, **data-efficiency loses at every budget**) marshaled as evidence that the ceiling is STRUCTURAL (non-identifiability + closure misspecification), not incidental. **No accuracy claim.** What it buys (modest): decomposition, calibration, ranking. Tighter than B, no fake positive; earns the general claim by exhaustiveness. Fixed invariant: "no accuracy claim; contribution = reusable ceiling-localization method + proved structural account." Venue: chemistry (JCIM/DD/MLST). _(Superseded the broad "what helps/hurts" B framing — there is no accuracy-helps side.)_

---

# (prior) Option B roadmap — "Physics-informed solubility: what helps, what doesn't, and why"

_Decisions (2026-07-11): **Scope B** (broad field-map) · **data-efficiency GPU run now** · **Lemmas 1–3 as proved (body)** · **chemistry venue (JCIM / Digital Discovery / MLST)**. Basis: [SCOPE_MEMO_2026-07-11.md](SCOPE_MEMO_2026-07-11.md)._

## Thesis reframe
From the narrow "grounding paradox" (a clean negative) → a **controlled field map**: where the thermodynamic bottleneck **helps** (temperature extrapolation, ranking, calibrated uncertainty, crystal grounding on external labels, low-data efficiency) vs **hurts** (the σ-grounding paradox, scaffold MAE), unified by (i) structural non-identifiability, (ii) the closure/insufficiency decomposition, (iii) transfer-limited representation. The paradox becomes one instrument in a larger honest map, not the whole paper.

## Two tracks

### Track G — GPU (user-run, parallel)
- **Data-efficiency curve** — `DEVICE=cuda bash scripts/experiments/run_data_efficiency.sh`. Physics-grounded vs DirectGNN across train-by-solute fractions {0.05,0.1,0.25,0.5,1.0} on the fixed scaffold test → `results/data_efficiency/summary.json`. Prereqs verified present. **RECALIBRATION (2026-07-11, verified):** this curve was NEVER run (`results/data_efficiency/` absent; PHASE0 = GPU-pending hypothesis). And the prior is NEGATIVE — DirectGNN ≥ physics at every budget actually measured (proxy temp-extrap DirectGNN −0.326 MAE; full corpus 1.70 vs 1.85; medium-budget correction inert). So run it not as a presumed positive headline but to **close the last hypothesis**: if physics does not win even in low-data (likely), that STRENGTHENS the "it's the closure/identifiability, not the data" story; if it does win, that's a genuine surprise headline. Run 1 seed first (`EXTRA_TRAIN_ARGS="--epochs-phase2 60"`), then seeds 43/44.
- **Do NOT frame B around a presumed positive.** Honest "positives" are thinner than the audit implied: temperature extrapolation 3.5× is the van't Hoff CLASS (0.368) vs RF (1.290), NOT the trained physics model (which is weaker than van't Hoff; DirectGNN beats TGNN on the proxy) — the paper already says so. Real, modest positives = interpretable decomposition, ranking (Spearman 0.51), calibrated uncertainty. B's thesis = honest field-map, not a manufactured win.
- (later, optional) non-proxy reruns of the supporting diagnostics currently on proxy/smoke.

### Track W — writing / CPU (assistant; ~80% relocation + formalization of existing work)
Ordered by dependency:

1. **Correctness pre-fixes** (gate submission):
   - `ident-compensation.tex`: the compensation section carries the **withdrawn** anticonservative CI [−0.965,−0.958] and presents δΦ≈−7.1 as the metric, but PHASE0 shows −7.1 is mostly reference error (absurd Joback + the +273 K T_m bug → −1.47 capped). **Refresh on the corrected split with recalibrated Joback, or cut to the qualitative "correlation is a trivial accounting artifact" point** (which the section already makes). Lead the rigorous ID evidence with E1 Fisher/CRLB, not this E0 metric.
   - (σ-oracle "2.42" already fixed; not an issue.)
2. **Methods section** (biggest structural gap) — `sections/methods.tex`: data/splits/labels; graph featurization + encoder variants (MPNN/GPS/TIMP); interaction + readout + pair rep; crystal head + ideal term; the **three closures** (NRTL / γ∞ / COSMO-SAC) with equations; **SLE solver + implicit differentiation** (the 1/(1+x₂η) stability criterion — a real method contribution, currently absent); adaptive correction; the σ-oracle intervention; 3-phase curriculum + **aux-stream grounding pattern**; loss (grouped, load-bearing only); DirectGNN control; reproducibility. **[IN PROGRESS this session.]**
3. **Theory: Lemmas 1–3 as proved** (App. + body statements):
   - L1 structural non-identifiability at infinite dilution (explicit 2-D null space; finite-dilution (1−x₂)² perturbation bound). Soften "Fisher vanishes" → "vanishes at infinite dilution; near-degenerate otherwise".
   - L2 class-dependent efficient information (semiparametric efficient-score projection; honest corollary: restricting the class gives finite-but-unusable CRLB 8,251 J/mol; only an external label closes the rank → 1,689).
   - L3 the B-split + two bound-lemmas (LOTV upper bound on B_insuff; Jensen lower bound on B_closure; convention-independence of B_insuff). **Highest-value rigor upgrade.**
   - Keep T4/T5 informal remarks; **cut Prop 6 (A-optimal)** — unsupported orphan; **keep T3 out** (refuted).
4. **Fold in the forgotten positives** (promote to body Results subsections + tables):
   - Temperature extrapolation (van't Hoff 0.368/R²0.887 vs RF 1.290 — full 5-model table).
   - External baselines head-to-head (our-corpus FastSolv/SolProp from `results/external_baselines`).
   - Three-closure comparison (NRTL 1.795 / γ∞ / COSMO-SAC).
   - Chemistry map promoted; corrupted-twin non-identifiability demo.
   - Data-efficiency curve (when Track G lands) — headline.
5. **SI** (S1–S9 per memo): Methods-full, proofs, per-arm tables, B-decomposition robustness, external baselines, ablations, supplementary mechanism (corrupted-twin, 45 K crystal grounding, dCp audit, fusion-scarcity, TGNN internal collapse, UMAP ΔMAE), temperature, data provenance/repro. Create `sections/SI.tex` + wire.
6. **Figures/schematics**: full architecture (three closures + σ-oracle + DirectGNN bypass), SLE solver + implicit-diff, aux-stream data-flow, UMAP ΔMAE (translate the RU interpretation table), data-efficiency curve, B-decomposition concept.
7. **Reframe shell**: title/abstract/intro/contributions/section list for the B thesis.
8. **Readability surgery LAST** (memo P0–P6): abstract rewrite (3 movements, few numbers); de-densify §Results; collapse Tier-1/2; tabulate scattered deltas; global hedge-pass (one caveat/sentence). Protect the good physical-intuition passages.

## Remaining M1 / data-availability (needs user)
Fill 4 `\pending` (repo URL / commit / **license** / **Zenodo DOI**), deposit gitignored artifacts (`sigma_profiles.csv`, per-arm CSVs), confirm redistribution rights (BigSolDB / VT-2005 / ThermoML).

## Status
- [x] Decisions locked · roadmap · GPU prereqs verified
- [x] (2) Methods section — `sections/methods.tex` drafted + wired + compiles clean
- [x] (5) SI skeleton — `sections/SI.tex` with stable labels (S1 methods, proofs, tables, baselines, mechanism, repro) wired; sections still to be populated
- [x] (1) compensation fix — `ident-compensation.tex` second diagnostic rewritten (withdrawn CI dropped, corr framed as accounting artifact w/ permutation null, −7.1 flagged reference-contaminated →−1.5, non-identifiability rested on E1 Fisher/CRLB, figures → SI)
- [x] (3) theory lemmas — §3 restructured: Prop1/2/3 → **Lemma 1/2/3** (non-identifiability w/ inf-dilution sharpening + finite-dilution O(x₂²); class-dependent efficient info w/ honest 8,251 vs 1,689 corollary; exact B-split + Jensen/LOTV/convention-indep bounds); **Prop 6 (A-optimal) cut**, T4/T5 folded to a remark; **proofs written in SI** (`sec:si-proofs`); all Prop→Lemma cross-refs updated; abstract synced; compiles clean. _(Adversarial proof-check running; known likely fix: Lemma-2 proof cites raue2009 for the semiparametric efficient-score — should cite van der Vaart / BKRW or drop.)_
- [x] **Track G data-efficiency — DONE (it ran on Modal `tgnn-e5/data_efficiency/`, retrieved 2026-07-11).** RESULT: physics-grounded loses to DirectGNN at EVERY fraction (ΔMAE phys−dir: +0.08/+0.37/+1.12/+1.14/+1.01 at frac 0.05/0.1/0.25/0.5/1.0; physics R² negative throughout). Gap is smallest (near-tie) at the lowest data and GROWS with data — the OPPOSITE of "physics wins in low-data." **Hypothesis REFUTED.** Curve committed to `results/data_efficiency/summary.json`. (Nuance: physics top-1 solvent ranking is higher at frac 0.05 (0.42 vs 0.26) — ranking utility ≠ MAE, consistent with the existing ranking story. Absolutes here exceed the headline runs → lighter budget → read as within-budget relative comparison.)
- [x] **A++ reframe core (2026-07-11)** — data-efficiency folded into body as capstone (`sections/data-efficiency.tex` + table); Discussion "the accuracy case is closed, exhaustively" paragraph (full-corpus/temperature/crystal/data-eff → structural ceiling via Lemma 1 + closure measurement); Contributions updated (exhaustive-negative bullet + proved-lemmas bullet; dropped "no theorem claimed"); **abstract rewritten** readable+method-forward (closes readability P0). Compiles clean; no stale "field map"/"no theorem".
- [ ] remaining: SI population (S3 per-arm · S5 external baselines · S6 ablations/three-closure · S7 mechanism); figures (architecture schematic, data-eff curve); readability P1–P6 (de-densify §4.1/§4.2, tabulate deltas, hedge-pass); fill 4 `\pending` + Zenodo (needs user)

## STRATEGIC UPDATE (2026-07-11) — B's positive premise is dead; reframe
B was chosen partly hoping data-efficiency would give a positive "here's when physics helps" headline. It does not: physics loses at every data budget. This is a CLEAN valuable NEGATIVE result that STRENGTHENS the core thesis (even in the low-data regime where a physics prior should help most, it does not beat the black box → it is the closure/identifiability, not the data). **Reframe B accordingly:** NOT "what helps vs what hurts on accuracy" (no accuracy-helps side exists) but "physics-informed decomposition does not beat the black box at ANY data budget — here is the rigorous why (identifiability + closure misspecification) — and here is what it DOES buy (interpretable decomposition, calibrated uncertainty, useful ranking)." The data-efficiency null becomes a genuine contribution. B and A+ converge on an honest negative field-map. _(Flagged to user; awaiting confirmation that the honest reframe is acceptable vs any change of course.)_
