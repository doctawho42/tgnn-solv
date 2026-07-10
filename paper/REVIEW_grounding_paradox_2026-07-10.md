# Adversarial peer review — `grounding_paradox.tex`

**Date:** 2026-07-10 · **Verdict: MAJOR REVISION** (0 fatal · 2 major · 11 minor)

> **STATUS 2026-07-10:** Track C (verify) **done** (§7). Track A (rewrite) **done** — m1/m3/m4/m5/m6/m7/m8/m9/m10 + M2 crystal-null all applied to `grounding_paradox.tex` + sections; compiles clean; figures regenerated; adversarial consistency-check passed. m2/m5 **code fixes done** — true COSMO `v_cosmo` wired through the decomposition; `decomposition.json` regenerated; σ-tests green. **Still open → M1 (Track B, repro contract):** commit the uncommitted σ-oracle/Gate-B machinery + fill the 4 `\pending` + deposit artifacts (needs your license/URL/Zenodo decisions). Nothing committed to git yet.

Provenance: 5 independent reviewer lenses (inferential validity / statistics / thermodynamics / reproducibility–data-reviewer / framing-novelty), each grounded in the `.tex` + result artifacts; every FATAL/MAJOR finding then defence-verified by an independent agent that tried to refute it (FATAL = 2 verifiers). 23 findings raised, 2 refuted, 21 survived. The one reviewer-FATAL (repro) was downgraded to MAJOR in verification because the deposit target is a `\pending` placeholder, not HEAD — nothing in the finalized text claims HEAD contains the machinery.

## 1. Editor summary

The paper stands as an honest, unusually well-hedged null/paradox result whose **core science is sound**: replacing the model's learned σ-profile with the true VT-2005 profile reliably makes activity *and* solubility prediction worse; the direction is seed-robust across three seeds; the primary paradox figure and the Table-2 B-decomposition both reproduce cleanly from committed artifacts. The externally-grounded-latent template for bounding closure-vs-insufficiency is genuinely useful. It clears the bar for a Digital-Discovery/MLST null-result venue **in principle**.

Two things block acceptance, both fixable:

1. **The reproducibility contract is not honored.** A fresh checkout at the (to-be-cited) commit *hard-crashes* on 2 of the 3 advertised "confirmations" and all of Gate B, because the machinery lives only in the working tree.
2. **The quantitatively decisive headline reverses for the deployed model.** The "assumption-free ~2× margin" is full-COSMO-SAC-convention only; under the deployed residual-only default the assumption-free (Jensen) bound flips (0.43 < 0.62). Abstract/title/contributions/discussion foreground it as if settled and general.

Neither is fatal — the direction is real, the deposit is an explicit placeholder, the framing fixes are cheap — but the repro contract must actually be honored and the headline re-scoped to what the *deployed* model and the n=60 low-γ corner support.

## 2. MAJOR blockers (acceptance-gating)

### M1 — Two of three "confirmations" + all of Gate B are non-reproducible from committed code  `[R4-a, R4-c]`
- **What:** `train_sigma_oracle`, `sigma_oracle_side`, `correction_force_open_gate`, the `model.py` train-mode oracle branch and `trainer._inject_sigma_oracle` exist **only as uncommitted working-tree edits**. `git show HEAD:src/tgnn_solv/config.py` does *not* contain these fields; `scripts/train.py` `apply_set_overrides` **raises `ValueError` on an unknown `--set` key** → a fresh checkout crashes at arg-parse on the `true-at-train` (MAE 1.98), `channel-swap` (2.08) and both Gate-B arms. Per-arm prediction/summary CSVs are untracked. The availability section is 4 blank `\pending` fields.
- **Why it matters:** for a venue whose data reviewer reruns the code, this is *the* acceptance criterion. Only the eval-time oracle arm (tracked `comparison.json`, 2.25 / R²−0.03) reproduces. No number is fabricated — but "triple-confirmed" + "the named scripts regenerate them" is false as written.
- **Fix:** commit the config/model/trainer machinery; deposit the untracked per-arm CSVs; fill the 4 fields and pin the availability commit to a SHA that contains the machinery; add a smoke test asserting `--set train_sigma_oracle=true sigma_oracle_side=both correction_force_open_gate=true` parses. Until then, downgrade "triple-confirmed" → "confirmed by the eval-time oracle" and mark the rest pending code release.

### M2 — The E2 crystal-null is the authors' own *mis-dosed* run, read in the opposite direction to their own verdict  `[R4-b, R1-e]`
- **What:** `crystal-null.tex` uses the melting-point-pool null as positive evidence that "the binding constraint is the closure (B_closure), not coverage (B_insuff)." But `results/PAPER_PHASE0_FINDINGS.md` (l.143, 163-168) titles this exact run **"E2 … INCONCLUSIVE (mis-dosed)"**: crystal aux = 8/1754 ≈ **0.46 %** of optimizer steps at weight 0.05; at the selected checkpoint the model had seen the 15,428-row pool **< 1 full pass**; the run did **not even reduce the MAE of the property it supervises** (T_m 45.0 → 46.6 K, i.e. *worse*). The authors' verbatim verdict: "this dilute dose does not help, NOT external crystal labels cannot help." Separately, B_closure/B_insuff was measured only on the *activity* closure — never for the crystal factor, whose "closure" is the near-exact ideal term Φ=(ΔH/R)(1/T−1/T_m), not a misspecified map — so "B_closure dominates" is not even the right frame.
- **Why it matters:** a non-improvement fully explained by the intervention not taking cannot license "coverage is not the ceiling"; reading it against the authors' own recorded verdict launders an inconclusive run into supporting evidence for the central thesis.
- **Fix:** either re-run E2 at an adequate dose (several full passes over the pool, higher weight, to convergence) before citing it, **or** re-scope to "a dilute crystal-aux dose does not move the ceiling (dose-limited, inconclusive per our own audit)" and drop it as support for "coverage is not the binding constraint." Reframe the flat T_m as the documented non-identifiability / transfer-limitation story.

## 3. MINOR but substantive (post-verification downgrades — the paper hedges *somewhere*, but the hedge is inadequate; still need fixes)

### m1 — The "assumption-free ~2× margin" REVERSES under the deployed convention  `[R5-a, R2-a, R2-d, R5-e]`  ← scientifically the sharpest
- Full COSMO-SAC: Jensen B_closure 0.71 > B_insuff 0.62. **Deployed residual-only: 0.426 < 0.618** (`decomposition.json conventions.res`) — the assumption-free bound points the *wrong way*; "near-tie" understates an actual reversal.
- The "~2× margin" (1.22 > 0.62) carries **no sampling CI**; eff. n ≈ 17 imbalanced solvent clusters (pyridine = 20/60). The only bootstrap in the artifact (≤ 0.88) attaches to the weaker 0.71-vs-bound comparison.
- The "0.80 vs 0.78" res-convention rescue numbers **do not appear in the tracked `decomposition.json`**.
- **Partial defence (real):** B_insuff is convention-*independent* (RF/ridge/kNN of m on z* with no g), so the *sharpened* res bound MSE_res − B_insuff_up ≈ 1.47 − 0.62 ≈ **0.85 > 0.62 still separates**; only the weaker constant-offset (Jensen) bound reverses. So the deployed conclusion survives — but not via the "assumption-free" claim the abstract leads with.
- **Fix:** lead abstract/contributions with the convention-robust Tier-2 + the sharpened convention-independent bound; state the assumption-free bound separates only under full COSMO-SAC and reverses under the deployed default; replace "near-tie" with "0.43 vs 0.62"; add a solvent-clustered bootstrap CI for the 1.22>0.62 margin or drop "decisive"; source or remove "0.80 vs 0.78."

### m2 — The "+combinatorial worse" Tier-2 pillar may be a geometric-basis artifact  `[R3-b]`  ← can change a number
- The Staverman-Guggenheim term mixes bases: `r_i = V_i/r0` uses a one-shot **RDKit MMFF gas-phase** `ComputeMolVolume`, while `q_i = A_i/q0` and the residual use the **COSMO cavity area / VT-2005 profile**. Standard Lin-Sandler COSMO-SAC derives r_i and q_i from the *same* cavity; mixing MMFF volume with COSMO area corrupts r/q. This −0.19 shift (mean_g +0.095 → −0.096) is exactly what inflates the offset and **manufactures the full-only Jensen jump 0.426 → 0.713 that IS the "2× margin."**
- **Fix:** recompute the SG term with r_i from the COSMO cavity volume (same source as σ); re-report whether "+combinatorial worse" survives. If VT-2005 lacks cavity volumes, state the comparison is basis-inconsistent and remove it from the "convention-robust" evidence.

### m3 — Attribution measured in a regime disjoint from — and easier than — the paradox it explains  `[R1-b, R3-e, R5-b]`
- The 60 matched pairs are near-ideal/low-γ IDAC/298 K (mean lnγ∞ 0.75, median 0.23, 38 % negative, 8 % in [1,2]; pyridine n=20 stratum MSE 0.07; 64 % of error is a between-solvent offset) — where COSMO-SAC is *most* accurate. The solubility paradox/physics tax peaks in the high-γ, strongly-H-bonding regime (water ΔMAE +0.52) **excluded** because VT-2005 lacks those profiles (unmatchable mean lnγ∞ 3.56, t=−7.44). Different operating point too (IDAC x₂→0 vs finite-saturation SLE). The qualitative decoder-not-inputs attribution is transported to the untested high-γ regime; "general procedure" is billed on one closure/target/temp/corner/n=60.
- **Fix:** restrict the causal claim to the low-γ IDAC regime and present the solubility-paradox explanation as a conjecture; add a B-decomposition on a higher-γ matchable subset or a synthetic high-γ stress test; downgrade "general procedure" → "a procedure, demonstrated here on one closure/regime" and move generality to a labeled conjecture in the intro (not only limitation iii).

### m4 — Chemistry-map ">0.8 Tanimoto: +0.51" is "load-bearing" and "exploratory" at once  `[R2-b, R2-e]`
- ±0.09 is SD across 3 *training* seeds on the same fixed test split (run-stability, not sampling uncertainty over which solutes land in the bin); the bin is the most extreme of several uncorrected strata families (garden of forking paths); no tracked artifact regenerates it (`run_e5_perrow_diagnostics.py` computes per-arm channel stats, not per-Tanimoto/per-solvent ΔMAE). Global tax "+0.14" averages per-seed 0.055/0.247/0.129 (~4.5× spread); several table ± (0.35–0.63) exceed their means.
- **Fix:** within-bin cluster/solute bootstrap CI, multiplicity correction, ship the regeneration script, annotate ± as 3-seed spread (n=3), report global tax as a range, and demote "load-bearing result" → "a suggestive pattern" unless it survives a multiplicity-controlled test.

### m5 — "Free head 4× better (MSE ~0.40)" — not reproducible, likely circular  `[R1-a]`
- `fig_parity()` in `make_paradox_figures.py` draws only the true-σ closure and computes no free-head series / no 0.40 (its own comment: the panel "has no free-head prediction, so only the closure is drawn"). The only 0.40 in the artifacts is `knn_in_zstar_biased_up = 0.40003` — the most flexible, in-sample B_insuff estimator, *below* the honest OOF bounds (RF 0.57, ridge 0.62). So "learned head ~0.40" either **is** the B_insuff estimate (making "4× better" a restatement of the bound arithmetic, not independent) or is an in-sample head unfairly vs a zero-parameter fixed closure. Fig-parity caption describes a teal series the script never plots.
- **Fix:** commit the exact estimator, report it out-of-fold, and either show it is a different object from the B_insuff estimators or reframe it as a flexible-regressor floor and drop "independent of the bound arithmetic." Fix the caption.

### m6 — Synthetic dial: unreproducible + internally inconsistent  `[R1-d, R3-d]`
- No committed generator (`make_paradox_figures.py` header: does NOT touch fig_dial — "separate synthetic generator"; dial absent from availability list), contradicting "every figure and table … available." On the paper's own monotone curve (F=0.38→−0.247, F=0.76→−0.096) the empirical −0.36 implies **F < 0.38, not 0.49** — where the dial predicts ~−0.18, a ~2× mismatch "same qualitative magnitude" papers over.
- **Fix:** commit the generator + the real-closure→F mapping and report the F that reproduces −0.36, or drop the numeric F≈0.49 and present the dial as a qualitative sketch.

### m7 — "σ_η² ≈ 0 / noise negligible / labels ruled out" asserts a measured fact where none exists  `[R2-c]`
- `decomposition.json`: `n_pairs_with_replicates = 0` → σ_η² is 0 **by construction, not by measurement**. External IDAC inter-lab scatter is ~0.2–0.5 in lnγ∞. Load-bearing Tier-1 offset is provably invariant to zero-mean noise, so not fatal — but "negligible/ruled out" is unsupported.
- **Fix:** "label noise unestimable in the matched set (no replicates); assumed 0"; drop "ruled out"; optionally import an external σ_η² and show the offset still exceeds B_insuff + σ_η².

### m8 — "Assumption-free" Tier-1 bound assumes convention-matching; its justification is circular  `[R1-c]`
- B_closure ≥ (E[m]−E[g])² = (0.748+0.096)² = 0.713 is a pure difference of means. "An independent recomputation reproduces the MSE, confirming g and m share the convention" is a non-sequitur — reproducing E[(m−g)²] only confirms g is recomputable, not that m is on the same mole-fraction Lewis-Randall reference state. A valid non-circular rebuttal exists in the authors' own data (pyridine stratum MSE 0.07 rules out a uniform offset) but isn't the argument made.
- **Fix:** verify ThermoML IDAC are mole-fraction Lewis-Randall referenced and/or lead with the pyridine-stratum argument; state "assumption-free" = "smoothness-free, conditional on convention-matching."

### m9 — Title headlines the disowned paradox, not the claimed contribution  `[R5-d]`
- The title advertises the paradox the authors call "unsurprising to a thermodynamics specialist" and explicitly disown as the contribution; the attribution/measurement they *do* claim is absent. Risks a desk read of "known negative result." **Fix:** retitle to foreground attribution (e.g. "…and Measuring Why: Closure Misspecification, Not Input Insufficiency").

### m10 — Residual methodological novelty is thin, stated as an "affordance"  `[R5-c]`
- Prop 2 is textbook conditional-variance/bias split (the paper says so); estimators are standard; B_insuff is only bounded. **Fix:** state method-new vs standard plainly (the only new element is exploiting an externally-measured latent to bound the split); lean the contribution's weight on the domain finding, not the "affordance."

## 4. Strengths to preserve

- Genuine scientific honesty — Tier-1/Tier-2 split, four named hedges, limitations i–iv, exploratory flags, theory correctly demoted to cited results.
- The qualitative core finding is real and reproducible where it matters (oracle 2.25/−0.03 vs grounded 1.85/0.33, seed-robust; +SG degrades 1.85→1.88 directly on n=5608).
- Primary paradox figure + Table-2 decomposition reproduce cleanly from committed artifacts; every spot-checked prose number reconciled.
- The externally-measured-latent template is a legitimately transferable diagnostic for physics-informed ML.
- Convention-independent B_insuff estimators make the sharpened res bound (~0.85 > 0.62) separate even under the deployed convention.

## 5. Angles the panel did NOT cover (do these before submission)

- **σ-profile normalization/grid/units in the oracle-injection path** — a silent normalization/discretization mismatch between VT-2005 and the model's σ-grid would *also* produce "true input hurts," orthogonal to the convention issue. **High-value: verify directly.**
- **Novelty positioning** vs the physics-informed-ML / COSMO-SAC-parameterization literature and the FastSolv/SolProp SOTA.
- **Paired vs unpaired** significance of the DirectGNN-vs-grounded gap on the shared 5608 rows (intersection-lock stated; paired test not shown).
- **Data licensing/redistribution** — can BigSolDBv2.1, ThermoML IDAC, Bradley MP, VT-2005 be legally redeposited under the (blank) Zenodo DOI/license?
- **Figure legibility / length / venue-fit** — not assessed.

## 6. Prioritized action plan

| Track | Items | Cost | Owner | Blocks submission? |
|---|---|---|---|---|
| **A. In-text honesty/scoping rewrites** | m1 reframe, m3 general→conjecture, m7 σ_η² wording, m8 "assumption-free" caveat, m9 title, m10 novelty, M2 re-scope option, m5/m6 caption fixes | low (text only) | me | yes (framing) |
| **B. Reproducibility contract** | M1: commit σ-oracle/Gate-B code + artifacts + smoke test; fill 4 `\pending` (repo URL, commit, **license**, **Zenodo DOI**); data-licensing check | med | me + **user** (license/URL/DOI) | **yes** |
| **C. Number-changing checks** | m2 SG recompute on COSMO volume; m5 free-head estimator provenance; σ-profile normalization audit; m6 dial generator | med (analysis) | me | maybe (may change 2× margin) |
| **D. GPU-gated** | M2 re-dose E2 properly; m3 high-γ B-decomposition / synthetic stress test; paired-significance test | high (compute) | **user** | only if choosing "re-run" over "re-scope" |

## 7. Track C verification (2026-07-10) — done, grounded in code + artifacts

**m2 — CONFIRMED, and FIXABLE (not "drop").** `_combinatorial_ln_gamma2` (layers.py:1555-1558) uses `r_i = V_i/r0` with V from RDKit MMFF gas-phase `ComputeMolVolume` (`run_b_insuff_decomposition.py:_mol_volume`), while `q_i = A_i/q0` uses the VT-2005 COSMO cavity area — a genuine mixed-basis error (canonical COSMO-SAC derives r_i and q_i from the *same* cavity). Arithmetic confirms the damage: the SG term shifts `mean_g` +0.095 → −0.096 (−0.19), and Jensen = (0.748 − mean_g)² gives res 0.426 / full 0.713 — i.e. **the entire full-only "2× margin" is manufactured by this −0.19 shift.** Deployed default is residual-only (`config.py:184 cosmo_sac_wire_volume=False`), so "full" is never shipped. **RECOMPUTED (2026-07-10, 44/44 coverage with true `Vcosmo, A3` from `index_v2.txt`): the effect SURVIVES.** res MSE 1.472 → full(RDKit) 1.793 / full(true Vcosmo) **1.800**; Jensen 0.426 → 0.714 / **0.717**; mean combinatorial contribution −0.192 / **−0.194**. Although true COSMO volumes are ~30% larger than RDKit MMFF (bromobenzene 104→139 Å³, acetonitrile 47→64), the SG term depends on r₂/r₁ **ratios**, so the scale factor nearly cancels and "+combinatorial worse" / the full-only margin are essentially unchanged (marginally stronger). **So the reviewer's artifact hypothesis is refuted by direct computation:** the mixed-basis error is real in code but numerically immaterial. **Action: fix the code to use `Vcosmo` for cleanliness/defensibility (cheap), and the paper may state the combinatorial comparison is robust to the volume basis (verified). Tier-2 pillar (i) is rehabilitated.**

**m5 — CONFIRMED (circular + non-reproducible).** The only 0.40 in the artifact is `knn_in_zstar_biased_up = 0.40003` — a B_insuff estimator (1-NN regressor of m on z*). `make_paradox_figures.py:13` states the parity panel "has no free-head prediction, so only the closure is drawn"; no other free-head activity MSE exists in committed code. So "free head fits 4× better, **independent of the bound arithmetic**" restates B_closure vs B_insuff (0.40 *is* the B_insuff estimate) — it is not independent, and the Fig-parity teal "free learned head" series is never plotted. **Fix:** drop "independent of the bound arithmetic"; reframe as "a flexible 1-NN regressor of m on z* reaches ~0.40 (= our B_insuff estimate), so the closure sits ~3.5–4.5× above the irreducible-variance floor" — honest, but the same object, not corroboration.

**σ-profile normalization/provenance audit — CLEAN (refutes the completeness-gap concern; strengthens the paper).** `results/sigma_profile_artifact/summary.json` shows the artifact was built by `ingest_vt2005_sigma_profiles.py` from **genuine VT-2005** (`Sigma_Profiles_v2`, 1432 compounds, `n_failed=0`), resampled onto the model's exact 51-bin grid (−0.025..0.025, matches `cfg`), with `sigma_area = sum(sigma_p)` **by construction** (ingest l.86-87). Raw `-PROF.txt` files confirm the native grid already matches. So "true input hurts" is **not** a normalization/grid artifact — the σ-oracle feeds faithful profiles. (Caveat: the artifact is **untracked** → must be deposited; reinforces M1/R4-c.)

### Net implication for the headline (updated after Track C recompute)
Better than the initial review read. Of the two Tier-2 "convention-robust" pillars, **(i) "+combinatorial worse" SURVIVES** the correct-volume recompute (rehabilitated; code fix only), and only **(ii) "free head 4× better, independent of the bound arithmetic" is a real casualty** (m5: the 0.40 IS the kNN B_insuff estimate — circular). The assumption-free constant-offset bound still **reverses** under the deployed residual-only convention (Jensen 0.43 < 0.62). So the deployed-model conclusion "closure dominates" now rests on **two solid legs**: (a) the convention-independent **sharpened bound** B_closure ≥ MSE_res − B_insuff_upper ≈ 1.47 − 0.62 ≈ **0.85–0.90 > 0.62 ≥ B_insuff** (artifact `b_closure_via_mse_minus_rf` res = 0.90; B_insuff depends only on (m, z*), convention-independent), and (b) "+combinatorial worse" (verified robust to the volume basis). **Reframe:** lead the abstract with the sharpened convention-independent bound + the verified combinatorial fact; demote the assumption-free constant-offset headline (full-convention only, reverses under res); **drop m5's "independent of the bound arithmetic"** and reframe 0.40 as the B_insuff floor; fix the SG code to use `Vcosmo`. The conclusion survives on a narrower but honest and now-verified base.
