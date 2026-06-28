# Design: σ-grounded COSMO-SAC — hardening + decisive test of lever C

- **Date:** 2026-06-28
- **Status:** Approved (brainstorming) → ready for implementation planning
- **Scope decision:** Full hardening (all review findings) **before** launching the decisive run.
- **Compute:** Real training on cloud GPU (local = smoke / code-path only). GPU setup is a **separate prerequisite spec** (see §9), not part of this one.
- **Repo:** `~/PycharmProjects/tgnn-solv`

---

## 1. Motivation

The project's headline thesis is **"conditional optimality of physics"**: the SLE factorization

```
ln x2 = −Φ(crystal, single-component)  −  ln γ₂(activity, pair)
```

helps OOD / scaffold generalization **only if** each factor is (a) separately identifiable and
(b) separately more transferable than the joint target — which requires **grounding each factor
with abundant single-component data**
(`paper/conditional_optimality_skeleton.tex:103-233`; `PROJECT_DESCRIPTION.md:624-653`).

**Lever C** is the activity-side instantiation: a zero-learnable-parameter differentiable
COSMO-SAC layer (`CosmoSacLayer`, `layers.py:1447-1607`) consumes a 51-bin σ-profile shape +
cavity area produced by a shared `SigmaProfileHead` (`heads.py:572-611`), grounded by an external
VT-2005 σ-profile auxiliary stream (1432 ingested → **1319** scaffold-disjoint rows,
`results/sigma_profile_artifact/summary.json`, `results/PAPER_PHASE0_FINDINGS.md:207-209`).

**The empirical fact that motivates this work:** the only completed COSMO-SAC-layer run is
**ungrounded** and it *destroys* solubility prediction — test R² **−0.310** (MAE 2.613, bias +1.959),
vs the NRTL baseline R² **0.32** on the same corrected split
(`results/cosmo_sac/test_predictions.summary.json`; `results/PAPER_PHASE0_FINDINGS.md:184-201`).
It does, however, genuinely narrow the activity range (pred_std_ratio 0.805) — i.e. the constraint is
real but binds to a *wrong σ-manifold* because the head is unsupervised.

**The pre-registered decisive test:** does external σ-grounding *rescue* ln x2 **while keeping the
activity constraint**? Falsifier: "if not, the constrained-activity route is not viable at this scale."

**Why this spec exists:** a multi-agent architecture review (2026-06-27/28) found that the COSMO-SAC
physics and the VT-2005 data are sound, but the experiment **as currently wired cannot deliver an
interpretable verdict** — a *null* would be unattributable, and the grounding may not even "take" due
to training-dynamics defects. This spec removes every such source of ambiguity/ineffectiveness before
the run.

---

## 2. Goals / Non-goals

### Goals
- Make the σ-grounded vs ungrounded comparison **interpretable and falsifiable**, including an
  attributable *null*.
- Ground **both** roles (solute *and* solvent) of the σ-profile head.
- Make σ-manifold learning **robust** (not under-dosed, not de-grounded by SLE, not loss-imbalanced).
- Establish a **fair benchmark** (matched-capacity DirectGNN on the current corrected split) and
  **pre-registered numeric success criteria**.
- Harden silent-failure surfaces (grid/bin contract, config/seed pinning, eval-denominator drift).

### Non-goals (explicit)
- **No new graph encoder.** The encoder is transfer-limited, not expressivity-limited
  (linear probe train R² 0.76 / test R² 0.45, `results/PAPER_PHASE0_FINDINGS.md:380-388`).
- **No chasing absolute scaffold MAE** — it sits near the aleatoric label-noise floor.
- **Do NOT flip the dCp / Prausnitz sign** in the ideal term — it is CORRECT
  (`PROJECT_DESCRIPTION.md:185-198`; standing project caveat). An audit agent has wrongly "confirmed"
  an inversion before; do not touch it.

---

## 3. Resolved design decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| Scope | How much to fix before launch | **Full hardening → then decisive run** | Maximum rigor; null must be interpretable. |
| Compute | Where the full run happens | **Cloud GPU (separate spec)** | Local MPS/CPU give meaningless metrics (MAE 3+, R²~0). |
| D2 | Solvent-side grounding | **Symmetrize: 2nd aux pass `role='solvent'`** | Dilute-limit residual is dominated by the solvent profile, which VT-2005 never supervised today (solute-only, `trainer.py:867-868`). |
| D3 | `head_sigma` training policy | **Stage-0 pretrain + freeze during SLE** | Decouples manifold learning from the under-dosed sidecar and from the T_m weight schedule; lets us verify area anchors before any SLE step can drift the head. |
| D6 | Combinatorial (Staverman-Guggenheim) term | **Ablation: residual-only vs +SG** | Currently dead code (`V=None`, `model.py:528-529`); ablation answers "does the size term matter" cleanly. |
| D1,D4,D5,D7 + | Auto (full hardening) | grid-contract assert; oracle + σ-VAL controls; DirectGNN h64 retrain; loss rebalance; multi-seed; pin config/seed | See §6 fixes table. |

---

## 4. Target architecture (after this spec)

```
solute graph ─┐                          ┌─ role='solute' embedding ─┐
              ├─ GNNEncoder (role-cond) ──┤                          ├─ SigmaProfileHead (SHARED)
solvent graph ┘   (UNCHANGED)             └─ role='solvent' embedding ┘        │
                                                                              ▼
                                              p_shape(51 bins, softmax) · area(softplus)  →  p_sigma
                                                                              │
                                              CosmoSacLayer (0 learnable params)           │
                                              fixed σ-grid [-0.025,0.025], 51 bins         │
                                              Δw = misfit(≥0) + HB(≤0)  →  Boltzmann E      │
                                              damped segment fixed point (n_iter)          │
                                              residual ln γ₂  [+ SG combinatorial (arm B)] │
                                                                              ▼
                                              SLESolver: ln x2 = −Φ − ln γ₂ (unrolled, back-propped)
```

Key invariants kept: `Σ p_sigma = area` (`heads.py:610`, the cavity-area invariant the mixture math
assumes, `layers.py:1536-1543`); native VT-2005 files lie exactly on the layer grid so the resample is
an identity no-op.

**Changes vs today:**
1. σ-head grounded from **both roles** (was solute-only).
2. New **Stage-0 σ-pretrain** phase + `head_sigma` **freeze** during SLE phases.
3. **V_m units resolved**; SG combinatorial term wired behind a flag (arm B).
4. Loss/dose/contract hardening (see §6).

---

## 5. Experiment matrix & pre-registered criteria

All models on the **same corrected split**, **matched capacity h64**, metrics computed on the
**intersection of `n_supervised` rows** across all models (the ungrounded run dropped ~31%:
n_rows 8103, n_supervised 5608 — eval denominator must not drift between runs).

| Model | Role |
|-------|------|
| NRTL (existing recipe) | weak milestone bar (R²≈0.32) |
| **DirectGNN h64 (RETRAIN on corrected split)** | **the real bar to beat** — discard the orphaned 0.48 (old split, h128) |
| cosmo_sac **ungrounded** (pinned config/seed) | control |
| cosmo_sac **grounded** — arm A: residual-only | treatment |
| cosmo_sac **grounded** — arm B: +SG combinatorial | size-term ablation |
| **Oracle-profile** (true VT-2005 profiles → layer for test solutes with an entry) | ceiling of lever C |

Plus a **scaffold-disjoint σ-VAL split** and **≥3 paired seeds** at a fixed epoch / early-stop budget.

### Pre-registered success criteria (locked before the run; user-approved)
- **"rescue"** = grounded cosmo_sac R² **≥ matched DirectGNN h64** R² (NRTL 0.32 = weaker milestone only).
- **"keeps constraint"** = `std(ln γ)` within a fixed band, calibrated from the ungrounded run.
- **area-anchor gate** passed (predicted areas track VT-2005 anchors: water ≈ 43, ethanol ≈ 88,
  hexane ≈ 157 Å², within tolerance).
- **`n_supervised`** reported as a first-class outcome, locked to the cross-model intersection.

### Null disambiguation (so a failure is attributable)
- Grounded profiles accurate vs σ-VAL **and** oracle also fails → **residual-only physics inadequate**
  (not a learning failure).
- Oracle succeeds **but** learned fails → **manifold learning / transfer** problem (encoder ceiling
  R²~0.45 / σ-coverage).
- **Stratify rescue by aux regime**: ring-bearing (~421 effective rows, matches the ~100% ring-bearing
  crystalline test set) vs acyclic (~68% of the pool). Do not interpret a null without this split —
  the falsifier is explicitly "at this scale".

---

## 6. The fixes (review findings → phases)

Severity from the synthesis: 3 blocker, 5 high, 4 medium, 2 low. Mapped to build phases below.

| ID | Sev | Finding (file anchor) | Fix |
|----|-----|------------------------|-----|
| B1 | blocker | Solvent profile never grounded — solute-only (`trainer.py:867-868`) | **P1**: 2nd aux pass `role='solvent'` (symmetrize) |
| B2 | blocker | DirectGNN benchmark orphaned: old split (~22-24% overlap), h128 vs h64 | **P3**: retrain DirectGNN h64 on corrected split; numeric thresholds |
| B3 | blocker | Null unattributable: aux grounds only single-component head; physics residual-only | **P3**: oracle-profile control + σ-VAL split |
| H1 | high | Weight schedule backwards; head SLE-trained-but-ungrounded in phase 2; `head_sigma` in no CD branch list (`trainer.py:625-636`, `48-123`) | **P1**: freeze `head_sigma` during SLE (per D3) |
| H2 | high | Under-dosed (`sigma_aux_steps_per_epoch=0` default; example 8 ≈ 0.5-2%), front-loaded burst (`config.py:190`, `trainer.py:1257-1264,1506-1515`) | **P0**: interleave + ≥1 full pass + config; sweep dose |
| H3 | high | Loss imbalanced: EMD mean-over-bins (~0.02-0.05) vs area MSE scale=200 vs pool std ~75 (`loss.py:59-88`) | **P0**: SUM-EMD / explicit shape weight + `area_scale≈75`; log both terms |
| H4 | high | Cavity area A = free scalar linearly scaling ln γ, grounded weakly/solute-only (`heads.py:605-606`) | **P0/P1**: meaningful dose + area-anchor gate; log clamp/saturation rates |
| H5 | high | Effective ring-bearing aux coverage ~421, not 1319; scale-conditioned falsifier ambiguous | **P3**: stratify rescue by regime; report ring-bearing coverage |
| M1 | med | No runtime grid/bin validation; positional registration; build hardcodes `--n-bins 51` vs ingest reads cfg (`dataset.py:891-907`, `build:46,131`) | **P0**: load-time assert `cols == cfg.cosmo_sac_n_bins`; store/verify endpoints metadata; build reads cfg |
| M2 | med | SG combinatorial dead code (`V=None`, `model.py:528-529`) | **P2**: resolve V_m units, wire SG behind flag (arm B) |
| M3 | med | No pinned cosmo config/seed; eval denominator can drift | **P3**: freeze `cosmo_sac.yaml` + seed; lock `n_supervised` intersection; `run_e5` orchestrator |
| M4 | med | Single-seed / early-convergence confound (best val ep9, early-stop ep39/70) | **P3**: ≥3 paired seeds, fixed budget, report dispersion |
| L1 | low | Acyclic scaffold-leak-guard bypass (`utils.py:73-74`); shared-optimizer Adam-state dilution; missing `sigma_area` defaults to 0.0 | **P0**: handle acyclic in guard (or assert test/val have none); separate aux optimizer state; make missing area a hard error |
| L2 | low | train(8)/eval(30) segment-iteration mismatch (`config.py:184-185`) | **P0**: match iters or confirm n=8 converged across T-range |

---

## 7. Build sequence (each phase → a step in the implementation plan)

### P0 — Correctness / contract (no-regret, no new science)
- Grid/bin contract: assert `sigma_p_*` column count == `cfg.cosmo_sac_n_bins`; store grid
  endpoints+order as CSV metadata and validate against cfg; make `build_sigma_profile_aux_stream.py`
  read `cfg.cosmo_sac_n_bins` instead of the hardcoded `--n-bins 51`.
- Loss rebalance: SUM-over-bins EMD (or explicit shape weight) + `area_scale ≈ pool std (~75)`;
  log shape and area terms separately.
- Dosing: `sigma_aux_steps_per_epoch` as a defined %-of-main-steps with ≥1 full-pool pass (~21 @ batch 64),
  **interleaved** across the epoch (not front-loaded); run the phase-1 σ step on label-free batches too.
- Separate optimizer / Adam state for the σ-grounding; missing `sigma_area` → hard error.
- Match train/eval segment iters (or document n=8 convergence).
- Acyclic scaffold-guard handling.
- **Done when:** existing suite (277+ tests) green + new tests for the contract assert, loss balance,
  dose interleaving.

### P1 — σ-manifold learning (per D2, D3)
- Solvent symmetrization: 2nd aux pass encoding each VT-2005 molecule with `role='solvent'`.
- Stage-0 σ-pretrain pipeline: `encoder + head_sigma` on the full σ-pool to convergence with
  **aux-VAL early-stop** (uses the σ-VAL split from P3 — sequence note below); area-anchor gate.
- Freeze `head_sigma` during SLE phases.
- **Done when:** stage-0 reaches an area-anchor gate threshold; freeze verified (no `head_sigma` grad
  during SLE); smoke run exercises both role passes.

### P2 — Combinatorial term (per D6)
- Resolve the V_m unit conversion (cm³/mol → Å³/molecule for `r0=66.69`; AuxPropsHead V_m is almost
  certainly cm³/mol → convert via ×1e24/N_A).
- Wire `V` through `CosmoSacLayer` behind a flag → arm B; keep residual-only as arm A.
- **Done when:** SG term active under flag, off by default; unit test on a known size-asymmetric pair.

### P3 — Experiment harness & controls
- σ-VAL scaffold-disjoint split (also feeds P1 stage-0 early-stop — build this artifact early).
- Oracle-profile injection path in eval (feed true VT-2005 profiles into `CosmoSacLayer` for test
  solutes with a VT-2005 entry).
- DirectGNN h64 retrain on the corrected split; discard the orphaned 0.48.
- `run_e5` orchestrator: runs {NRTL, ungrounded, grounded-A, grounded-B, oracle} differing only by the
  intended knob; pins `cosmo_sac.yaml` + seed; locks metrics to the `n_supervised` intersection;
  ≥3 paired seeds; rescue stratified by aux regime.
- **Done when:** orchestrator produces the comparable bundle (`summary.csv`, `report.json`,
  `predictions.csv`, `run_manifest.json`, `benchmark_card.json`) with the pre-registered fields.

> **Sequencing note:** the σ-VAL split (nominally P3) is a dependency of P1 stage-0 early-stop. Build
> the split artifact first (small, data-only), then P0 → P1 → P2 → P3-rest. The implementation plan
> should pull "build σ-VAL split" to the front as a shared prerequisite.

---

## 8. Testing strategy

- Unit tests per fix (contract assert, loss balance, dose interleave, freeze policy, SG units, oracle path).
- Keep the full suite green (`KMP_DUPLICATE_LIB_OK=TRUE python -m pytest tests/ -q`).
- Local **smoke only** for end-to-end (tiny config) to verify code paths — smoke numbers are
  meaningless and must not be reported as results.
- Real metrics ⇒ cloud GPU (§9).

## 9. Out of scope (separate specs / follow-ons)
- **GPU/cloud training setup** (resumable cloud runs per `docs/free_gpu_training.md`) — its own spec,
  to be written when we are code-ready. This design assumes that capability exists at run time.
- Dispersion term in COSMO-SAC (a known omission; not required for the lever-C verdict).

## 10. Risks & open questions
- **Stage-0 over/under-fitting** on ~1319 rows (ring-bearing ~421): mitigated by aux-VAL early-stop +
  regime stratification, but coverage may still cap a positive result — surfaced, not eliminated.
- **Frozen `head_sigma` vs encoder drift:** freezing the head but not the encoder during SLE could
  still move the profiles via the shared trunk; plan should decide whether to also freeze the encoder
  trunk feeding `head_sigma` or accept controlled drift (flag for the implementation plan).
- **Oracle coverage:** only test solutes with a VT-2005 entry get an oracle number; report coverage.
- **V_m unit conversion** correctness is load-bearing for arm B; needs an explicit unit test.

## 11. References (anchors)
- Layer/head/solver: `layers.py:1447-1607`, `heads.py:572-611`, `solver.py:39-40,413-473`,
  `model.py:520-546`.
- Config: `config.py:172-194`.
- Training/loss/data: `trainer.py:48-123,625-636,829-887,1257-1264,1506-1515`, `loss.py:59-88`,
  `data/dataset.py:891-907`.
- Data build: `scripts/data/build_sigma_profile_aux_stream.py:46,131-178`; CLI `scripts/train.py:254-274,1107-1122`.
- Empirics/theory: `results/PAPER_PHASE0_FINDINGS.md:181-212,302-337,380-388`,
  `results/cosmo_sac/test_predictions.summary.json`, `paper/conditional_optimality_skeleton.tex:103-233`,
  `PROJECT_DESCRIPTION.md:185-198,624-653`.
