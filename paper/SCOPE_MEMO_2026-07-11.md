# Scope & Completeness Audit — Strategic Memo (2026-07-11)

_Produced by a 6-reader repo-wide audit workflow + synthesis. **Two verification corrections to Section 0 (checked against results/PAPER_PHASE0_FINDINGS.md):**_
- _**MUST-FIX #1 (σ-oracle "2.42/−0.09") is ALREADY DONE** — the current tex cites 2.25/−0.03 everywhere; the agent read a stale note in THREE_SEED_SUMMARY.md, not the paper. No action._
- _**MUST-FIX #2 is REAL but mis-stated** — "−4.99" is the E2 crystal |δΦ| (a different quantity), not the fix. The real issue: `ident-compensation.tex` cites the anticonservative row-bootstrap CI [−0.965,−0.958] (PHASE0 says use the solute-cluster CI) and presents δΦ≈−7.1 as the trusted metric, but PHASE0 shows −7.1 is mostly reference error (absurd Joback + the +273 K T_m bug) → −1.47 when Joback is capped. Refresh on the corrected split or cut to the qualitative point._

---

# STRATEGIC MEMO — Scope & Shape of the Grounding-Paradox Paper

**To:** author · **From:** senior co-author · **Re:** what this paper should BE before we invest the next work session
**TL;DR:** The tight paper is honest and its spine is real (E5 3-seed GPU, B-split, dial, Fisher). Your three worries are each *partly* justified but not equally: readability is the most fixable, "no rigorous theory" is *fixable* (3 real lemmas exist), and "reflects a small fraction of the work" is true but the right fix is an **SI + Methods**, not a rebrand. **Two live number bugs must be fixed before any submission regardless of scope.** Recommendation: **Option A+ (tight paradox spine + real Methods + real SI + 3 proved lemmas), not a broad survey and not yet a two-paper split.**

---

## 0. MUST-FIX BEFORE ANY SUBMISSION (correctness, not scope)

Flagged independently by exp-core, arch, and coverage — these are wrong numbers in the current tex, not stylistic:

1. **Stale σ-oracle number.** Paper text cites oracle "MAE 2.42, R²=−0.09" — appears in **no seed** (all three are 2.23–2.28, R²−0.03±0.04). Purge; replace with the 3-seed value.
2. **Pre-correction compensation numbers in `ident-compensation.tex`.** `corr(δΦ,δγ)=−0.962`, `δΦ_mean≈−7.1` are pre-T_m-bug / anticonservative-CI values the repo itself *withdrew*; corrected-split value is δΦ≈−4.99 (capping→−1.47). Currently cited as a "consistency check." Reviewer-fatal if caught. Refresh on corrected split or cut.
3. Also honesty-tighten: "R²=−0.03±0.04 crosses zero" → headline as "R²≈0", not "worse than the mean."

These are ~half a day and gate everything else.

---

## 1. WORK-vs-PAPER GAP MAP — "what we forgot"

Tags: **PW** paper-worthy (headline/body) · **SI** SI-worthy · **DIAG** diagnostic-only · **INV** invalidated/superseded. Status: RUN(real) / GPU / PROXY(directional) / SMOKE / GPU-PENDING.

### The genuinely-forgotten positives (highest strategic signal)

| Result | Artifact | Status | Finding | Tag |
|---|---|---|---|---|
| **Temperature extrapolation** | `results/temperature_extrapolation_baselines/summary.json` | RUN, n=3343 | van't Hoff class MAE **0.368 (R²0.887)** vs RF-Morgan+T **1.290** — physics wins ~3.5×; 99% vs 40% direction accuracy | **PW** (currently 1 paragraph in supporting) |
| **Corrupted-twin non-identifiability** | `results/proxy_corrupted_twin/twin_vs_corrected_comparison.json` | RUN | +273 K-corrupted vs corrected T_m → solubility unchanged (1.835 vs 1.812) but crystal grounding 258 K vs 45 K. Clean empirical proof of Prop 1 | **SI** (better evidence than the Fisher audit; absent) |
| **Crystal grounding on physical labels** | `results/proxy_corrupted_cpu` | RUN | Predicts measured T_m to **45 K MAE, skill 0.31, ~4× better than Joback** | **SI** (only the E2 null survives in-paper) |
| **In-house FastSolv/SolProp** | `results/external_baselines/{solute,pair_random}/*contract_v2/metrics.json` | RUN, n=10287 | Retrained on-corpus: FastSolv ln_x2 MAE **1.94**/logS 0.87; SolProp native too. Paper cites only *literature* numbers | **PW→table** (we ran it, we don't report it) |
| **NRTL closure arm** | `results/e5_sigma_grounding` 3-seed lock | GPU | NRTL MAE **1.795±0.071** — the "three closures" (NRTL/γ∞/COSMO-SAC) story is invisible in the paper | **PW/SI** |

### Structural results omitted or compressed

| Result | Artifact | Status | Tag |
|---|---|---|---|
| Split-difficulty ladder (RF row_random 0.17 → scaffold 1.70) | `results/split_comparisons`, `extended_split_diagnostics` | RUN | SI |
| Ablation table (NRTL vs COSMO-SAC, γ∞ mode, coord-descent) | `results/ablation_proxy` + `run_e4_ablation_summary.py` | PROXY | SI |
| UMAP ΔMAE cluster map (8 clusters, signed physics−direct) | `results/chemical_space_projection/cluster_class_interpretation.*` | RUN+PROXY | **SI figure** (interp table is in **Russian** — translate) |
| TGNN internal-collapse forensics (NRTL branch numerically dead: std(τ12)=4.8e-5) | `temperature_extrapolation_failure_diagnostics/tgnn_internal_summary.json` | PROXY | SI (frame as NRTL companion, not COSMO-SAC) |
| dCp (omitted heat-capacity) audit | `results/dcp_correction_audit/summary.json` | RUN, 108k rows | SI (names a model-form error orthogonal to closure; pre-empts reviewer) |
| Fusion-supervision scarcity (test/val have **zero** dH_fus; 1279 dH rows/31 solutes) | `results/fusion_supervision_audit/SUMMARY.md` | RUN | SI (the quantitative backbone under crystal-null) |
| BRICS compositional OOD (45% test "mostly novel", gap +0.46) | `compositional_generalization` | RUN+PROXY | SI |
| Implicit-diff SLE solver + convergence audit (n=16 vs 30 within 6e-5; n=8 failed) | `src/tgnn_solv/solver.py:208/394` | RUN | **PW method** (a real methodological contribution, absent) |
| Data-efficiency curve ("strongest science claim" per PHASE0) | `run_data_efficiency.sh` | **GPU-PENDING** | PW-if-run (honestly deferred) |
| Encoder linear probe, noise floor, ranking, conformal, chemistry map, Fisher audit | various | RUN/PROXY | **already in paper (a)** |

### Diagnostic-only (correctly excluded — do NOT promote)
embedding_geometry, embedding_interpretability, directgnn_error_structure, regime_diagnostics, solubility_cliffs, difficult_ionic_systems, gradient_flow, attribution_smoke (single system), example_system_casebook (curated, PROXY), metric_diagnosis*, physics_bottleneck*, source_uncertainty_audit*, thermoml/unifac inventories, optuna/lab_runs infra.

### Invalidated / superseded (must be firewalled)
- **All pre-2026-06-19 (+273 K T_m) checkpoints/splits** — Bradley double-C→K bug; new split overlaps old ~24%. `architecture_review_bundle.md` (MAE 4.4, R²−2.9) is smoke/pre-correction — never cite.
- **`conditional_optimality_skeleton.tex`** — T1–T5 / A-opt-iff; **Thm 3 refuted**, empirically false (physics trails Direct). Correctly dropped; reference-only.
- **COSMO-SAC ungrounded `results/cosmo_sac/` (R²−0.31)** — superseded by 3-seed E5 ungrounded arm.
- **TIMP channel interpretability** — scripted, **never produced output**; TIMP≈MPNN (1.847). Do not resurrect.

**The honest one-line summary of "what we forgot":** the paper suppresses its own *positive* physics results (temperature extrapolation 3.5× win, 45 K crystal grounding, the corrupted-twin ID demonstration) and its own *reproduced* external baselines to protect a clean negative-result thesis. Nothing headline was lost by accident; the loss is asymmetric — the **Methods/architecture half of the paper barely exists**, and a coherent SI's worth of run-with-real-numbers material sits unused.

---

## 2. SCOPE OPTIONS — the core decision

### Option A+ — Tight paradox spine, real Methods, real SI, 3 proved lemmas  ★ RECOMMENDED
- **Thesis (unchanged):** truer inputs (measured VT-2005 σ) fed through a differentiable COSMO-SAC closure make activity+solubility *worse*; we measure B=B_closure+B_insuff and the closure binds.
- **Includes:** current 6 result sections; **NEW** Methods (encoder/interaction/three closures/implicit-diff solver/3-phase curriculum/aux-stream); **NEW** SI (proofs of Lemmas 1–3, per-arm tables, external-baseline table, ablation table, the 4 hedges, temperature + corrupted-twin + dCp + fusion-scarcity as supplementary mechanism); readability surgery; two bug fixes.
- **Venue fit:** excellent for **TMLR** (rewards rigorous honest measurement, no-novelty-required), **Machine Learning: Sci. & Tech. (MLST)**, **Digital Discovery**, **JCIM**. The negative/measurement result is a *feature* at these venues.
- **Strengths:** keeps the one clean, defensible, GPU-backed thesis; converts three stated worries (theory, SI, readability) to done; low new-experiment risk (almost all CPU-reproducible).
- **Risks:** still a "physics doesn't help here" story — reviewers at a chemistry venue may want the positive counterweight (mitigated by SI temperature win). Thin-n keystone (60 pairs) remains — SI robustness tables must carry it.
- **Effort:** **medium.** ~1 wk writing (Methods+SI+abstract), ~2–3 days proofs, ~1 day baseline/ablation tables, bug fixes. No new GPU except optional compensation refresh.

### Option B — Broad "physics-informed solubility: what helps, what doesn't, and why"
- **Thesis:** a controlled map of where the physics bottleneck helps (temperature extrapolation, ranking, calibration, crystal grounding on external labels) vs hurts (the σ-grounding paradox, scaffold MAE), unified by identifiability + the B-decomposition.
- **Includes:** everything in A+ **as co-headlines** — temperature 3.5× win, external head-to-head, NRTL/γ∞/COSMO-SAC comparison, data-efficiency curve (**needs GPU**), encoder-transfer story, chemistry map promoted.
- **Venue fit:** **JCIM / Digital Discovery / MLST full paper.** A "field map" is a natural fit; more citable, more complete.
- **Strengths:** reflects the true scale of the work; positive + negative balance reads as mature science; the strongest potential claim (data-efficiency) becomes headline.
- **Risks:** **dilutes the sharp paradox** (its rhetorical power is that it's one surprising thing measured cleanly); requires the GPU data-efficiency run to land; more surface area = more reviewer attack points; the "helps" and "hurts" arms live on different splits/compute tiers (proxy vs GPU) — honesty bookkeeping balloons.
- **Effort:** **high.** +1–2 wk, plus GPU for data-efficiency and ideally a non-proxy rerun of the supporting diagnostics.

### Option C — Two-paper split (methods+theory · vs · paradox measurement)
- **Thesis:** Paper 1 = the differentiable-COSMO-SAC-over-predicted-σ architecture + implicit-diff solver + aux-stream grounding pattern + identifiability theory (Lemmas 1–3). Paper 2 = the paradox measurement (current paper).
- **Venue fit:** Paper 1 → methods venue; Paper 2 → TMLR/MLST.
- **Strengths:** each paper is clean; the architecture/solver finally gets a home.
- **Risks:** **Paper 1 has no converged flagship accuracy result to anchor a "methods" paper** — the physics path trails DirectGNN; a methods paper whose method loses is a hard sell. Splitting now doubles writing for one deliverable's worth of results.
- **Effort:** **very high**; not justified until there's a positive accuracy anchor (e.g. data-efficiency or crystal-grounding win).

### Option D — Theory-forward paper
- **Thesis:** structural non-identifiability of the SLE crystal/activity split + the B-decomposition, proved.
- **Venue fit:** would need NeurIPS/ICML-grade theorems.
- **Strengths:** answers "no rigorous proofs" head-on.
- **Risks:** the provable core is **3 modest lemmas** (one textbook), not a headline theorem; the ambitious tower (T3, A-opt) is refuted/unprovable. A theory-forward framing over-promises exactly what was correctly dropped. **Do not.**

**Recommendation: Option A+.** It resolves all three of your stated worries at medium effort and zero new-thesis risk, and it *stages* Option B — every SI asset (temperature, external baselines, ablations, corrupted-twin) is written once and can be promoted to body if you later decide to broaden. Revisit B only if the **data-efficiency GPU run lands as a positive** result; that single result is the difference between "physics doesn't help" (A+) and "here's exactly when physics helps" (B). Do C only after a positive accuracy anchor exists.

---

## 3. ADDITIONS MENU (value × effort)

### 3a. Theory + proofs — add a compact Theory/SI appendix (per theory report)
| Item | What a real proof needs | Value×Effort |
|---|---|---|
| **Lemma 1 — structural non-identifiability** (Prop 1) | State at **infinite dilution** (exactly affine in 1/T → explicit 2-D null space); add first-order (1−x₂)² perturbation bound for finite dilution. **Soften "Fisher vanishes"** to "vanishes at infinite dilution; near-degenerate (λ_min=0.054, cond 2.3e5) otherwise." | **High value, low-med effort** |
| **Lemma 2 — class-dependent efficient information** (Prop 2) | Real semiparametric efficient-score projection onto orthocomplement of nuisance tangent space (van der Vaart). **Best "real theorem" candidate.** Must include the honest corollary: restricting the activity class gives finite-but-unusable CRLB (8,251 J/mol); only an **external label** closes the rank (→1,689). | **High value, med effort** |
| **Lemma 3 + two bound-lemmas — the B-split** (Prop 3, KEYSTONE) | The identity is one paragraph (cross-term=0). The rigor is in the **currently-prose bounds**: (i) B_insuff ≤ E[Var(m\|bin)] by LOTV; (ii) B_closure ≥ (E m−E g)² by Jensen; (iii) **convention-independence of B_insuff**. State as short lemmas with assumptions. **This is the paper's empirical keystone — highest-value rigor upgrade.** | **Highest value, low-med effort** |
| van't Hoff extrapolation (T4), info-geometry (T5) | Keep **informal/remark** (trivial OLS variance; corollary of L1). | keep cited |
| A-optimal weights (Prop 6) | **Unproven, likely overstated.** Keep as design heuristic or **cut** (orphan from dropped draft; no in-paper experiment supports it). | cut/heuristic |
| Conditional-optimality iff (T3) | **Refuted.** Keep out. | — |

Net: the paper can honestly say "the decomposition and its one-sided bounds are proved (App. X)" instead of "no theorem claimed" — strictly stronger, still honest.

### 3b. SI structure (concrete section list)
1. **S1 Methods in full** (see 3d).
2. **S2 Proofs** — Lemmas 1–3 + two bound-lemmas.
3. **S3 Per-arm exact tables** — the numbers evicted from §4.1 (all σ-grounding arms, 3 seeds, triple-confirmation).
4. **S4 B-decomposition robustness** — full/res conventions, LOTV/RF/Ridge/kNN estimators, solvent-clustered bootstrap, pyridine stratum, the 4 hedges.
5. **S5 External baselines** — FastSolv/SolProp contract-v2 head-to-head table.
6. **S6 Ablations** — NRTL vs γ∞ vs COSMO-SAC, combinatorial-term on/off, coordinate-descent.
7. **S7 Supplementary mechanism** — corrupted-twin ID demo, 45 K crystal grounding, dCp audit, fusion-supervision scarcity, TGNN internal-collapse (NRTL companion), UMAP ΔMAE cluster map.
8. **S8 Temperature extrapolation** — full 5-model table + direction accuracy.
9. **S9 Data provenance & reproducibility** — BigSolDB/VT-2005/ThermoML, split construction, °C/K trap, solver iters, COSMO constants, seeds, proxy-vs-GPU compute ledger.

### 3c. Figures / schematics to add
| Figure | Value×Effort |
|---|---|
| **Full architecture schematic** (two-graph encoder → interaction/readout → 3 parallel closures → SLE solver → correction, with σ-oracle + DirectGNN bypass marked). Current Fig.1 is COSMO-only. | **High × med** |
| **SLE fixed-point + implicit-diff schematic** (damped iteration + custom backward, the 1/(1+x₂η) stability criterion). | High × low |
| **Aux-stream data-flow schematic** (self-solvent sidecars → which deficient Fisher direction each closes → ties Prop 1↔mechanism). | High × low |
| **UMAP colored by signed ΔMAE** (physics-wins vs physics-loses clusters) — ready-made SI figure, legible version of chemistry-map. | High × low (translate RU table) |
| **Data-efficiency curve** | High × **high (GPU-pending)** — only if Option B |
| B=B_closure+B_insuff conceptual schematic (where oracle/RF-floor/bounds sit) | Med × low |

### 3d. Methods section outline (currently absent — the biggest structural gap)
Graph featurization → encoder variants (MPNN/GPS/TIMP) + interaction/readout → the three closures with equations (NRTL / γ∞ / COSMO-SAC over predicted σ) → SLE solver + implicit differentiation → 3-phase curriculum + aux-stream protocol + scaffold-leak guard → loss taxonomy (**grouped**, not all ~40 terms; only huber + aux σ/crystal/IDAC + van't Hoff are load-bearing) → data provenance + split + °C/K trap → reproducibility (seeds, solver iters n=16/30, COSMO constants). **Value×Effort: highest × med** — this alone moves the paper from workshop-shaped to journal-shaped.

---

## 4. READABILITY PLAN (from readability report, prioritized)

- **P0 — Rewrite the abstract (highest leverage).** One 35-line number-dump paragraph → 3 short movements: (1) setup+paradox with **one number** (true σ makes it worse, MAE 2.25 vs 1.85, R²→0); (2) measurement in plain words (input is externally known → error splits with no fit into "is the map wrong" vs "are inputs insufficient") + verdict (closure binds); (3) consequences (correction fixes calibration not accuracy; no new theory). **Delete** the 4-term inequality chain, convention names, 0.85 confidence, label-noise clause. Promote the current coda ("we measure where a physics prior's ceiling lies") to the front.
- **P1 — De-densify §4.1 (paradox).** ~11 inline numbers → 2 (MAE gap + ~4×); triple-confirmation (1.98/1.80/2.08) → a 3-row table; stop restating figure numbers in body *and* caption. Lead with the "misspecified map, not missing information" line (currently 5th sentence).
- **P2 — Restructure §4.2 (measure).** Collapse Tier-1/Tier-2 into one paragraph, **one** number in prose; move the 4-hedge enumerate to SI (or 2 sentences); explain "Tier" once as a concept (convention-independent bound vs bookkeeping-free qualitative effect); thin Table 2's paragraph-caption to a legend.
- **P3 — Demote theory (§3).** Body keeps **only** Prop 1 (ident) + Prop 3 (decomp), each with a plain-English gloss above the equation; fold semiparam/temp/geom/aopt into one "supporting structural facts" paragraph or SI (presenting them as numbered Propositions signals "new theory" the paper disclaims).
- **P4 — Tabulate scattered deltas.** ΔT sweep → Fisher-table rows; crystal-null 4 before/after pairs → 2-line table; chemistry-map solute-axis + novelty inversion → one small table. Frees prose to carry the (excellent) physical intuition.
- **P5 — Build the promised SI.** Text says "transcribed in the SI" repeatedly; no SI file exists. Create it (§3b) and route every evicted number there.
- **P6 — Global hedge-pass.** One caveat per result sentence, not three. Use §4.3 (Gate B) — the most readable subsection — as the register template.
- **Protect:** chemistry-map's H-bond-donor-strength narrative and "masked on novel, exposed on easy" (best physical intuition); Gate B's "fix reliability not resolution"; the "misspecified map vs missing information" thesis sentence. Also fill all `\pending` placeholders (repo URL, commit, license, Zenodo DOI, co-authors) — currently un-submittable.

---

## 5. OPEN QUESTIONS FOR THE AUTHOR (decide before we execute)

1. **Scope commitment: A+ or B?** Do you want the sharp single-result paper (A+) or the field map (B)? This is the fork everything else hangs on. My vote: A+, stage B.
2. **Will you spend GPU on the data-efficiency curve now?** It's the only asset that can flip A+→B as a *positive* headline. If yes → we may reconsider B. If no → A+ and defer honestly.
3. **How much theory do you want in the body vs SI?** Are you comfortable stating Lemmas 1–3 as *proved* (App. X) — the honest, strictly-stronger position — or do you prefer to keep the current "no theorem claimed" posture and put proofs only in SI?
4. **Venue target?** TMLR (measurement/negative-result friendly, no novelty bar) vs a chemistry venue (JCIM/Digital Discovery/MLST, will want the positive counterweight). This changes how hard we push the temperature/crystal positives.
5. **Do the omitted positives go in SI (A+) or body (B)?** Specifically temperature extrapolation (3.5×) and the corrupted-twin ID demo — SI keeps the thesis clean; body broadens it.
6. **Compensation section: refresh on the corrected split (needs a short rerun) or cut it?** It currently carries withdrawn numbers; it must change one way or the other.
7. **Cut Prop 6 (A-optimal weights)?** It's an unsupported orphan from the dropped draft. Recommend cut; confirm.
8. **Translate the Russian UMAP interpretation table** for the cluster-ΔMAE figure — worth it, or drop that figure? (cheap, high-legibility payoff.)

**Bottom line:** the fix is ~80% *relocation and formalization of work you've already done* (prose→table/SI, three provable lemmas, a Methods section) plus abstract surgery and two bug fixes — not new science. Option A+ ships a rigorous, readable, complete-looking paper without gambling the clean thesis; keep every SI asset written-once so Option B remains one GPU run away.