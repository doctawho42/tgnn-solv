# fix-g Gate 1 — preliminary run (2026-07-19): INCONCLUSIVE

> **AMENDED 2026-07-25.** The original version of this file blamed the result on
> undertraining. That diagnosis was mostly wrong and is corrected below. Undertraining
> accounts for only ~0.07 of the discrepancy; the dominant cause is that the
> pre-registered anchor describes a **different model arm**, and the decision band sits
> on top of a molecule-blind constant. The run is still not a go/no-go verdict, but for
> different and more serious reasons. See `CONTROL_LADDER_2026-07-25.md`.

**Status: NOT a go/no-go verdict.** This file exists so the raw "NO-GO" string in
`gate1_prelim_rho_2026-07-19.json` is not later misread as a genuine kill of the
co-trainable-kernel hypothesis.

## What was run
- **Where:** transient GCP L4 VM (`tgnn-fixg`, us-west1-a), deleted immediately after.
- **Budget (deliberately cheap, cost-constrained):** 25k-row train subset, Phase 1 = 6
  epochs, Phase 2 = 8 epochs, Phase 3 = 0, σ-grounding OFF, CPU ρ-eval.
- **Two matched arms, same seed 0, same data:** `fixg` = `cosmo_sac_kernel_residual_rank=1`,
  `free` = `cosmo_sac_kernel_residual_rank=0`.
- **Metric:** ρ = mean‖σ̂−σ‖ / mean‖σ‖ on the fixed n=44 matched VT-2005 solutes.

## Result
| arm  | ρ     | drop-one range | rank |
|------|-------|----------------|------|
| fixg | 0.884 | 0.882–0.886    | 1    |
| free | 0.884 | 0.883–0.887    | 0    |

## Why this is invalid — corrected diagnosis (2026-07-25)

Three separate defects, established by free local measurement (no GPU spend):

**1. The ρ_free = 0.51 anchor describes a different arm.** It comes from
`results/sur/surrogate_seeds/surrogate_seeds.json` (`aggregate.sle_vs_true.mean = 0.5065`),
whose `recipe` is `{ep_warm: 40, ep_sle: 70}` — i.e. a model **σ-grounded for 40 warmup
epochs and then drifted** by SLE training. The Gate-1 free arm sets
`sigma_warmup_epochs: 0` and is **never grounded**. The two are not comparable objects.
Measured on the converged never-grounded Paper-1 checkpoint
`checkpoints/cosmo_sac/tgnn_cosmo.pt` (full 30/70/10 budget, full corpus, current split):

    ρ = 0.8156  (drop-one 0.808–0.821, rank=0)

So the honest expectation for the planned free arm is **~0.82, not 0.51**. The
pre-committed thresholds are mis-anchored by ~0.3 in ρ.

**2. Undertraining was a minor contributor, not the cause.** Converged free reads 0.816;
the cheap 25k/8-epoch run reads 0.884. The whole training deficit is worth ~0.07 — it does
not begin to explain the distance to 0.51. The original diagnosis in this file conflated
the two.

**3. The decision band certifies nothing.** Reproduced by
`scripts/experiments/rho_control_ladder.py` on the same n=44 set:

| reference | ρ |
|---|---|
| **GO threshold** | **0.46** |
| **leave-one-out corpus-mean profile (zero molecular information)** | **0.4926** |
| **NO-GO threshold** | **0.50** |
| true profile of a *randomly permuted* molecule (5 seeds) | 0.651–0.684 |
| converged never-grounded `tgnn_cosmo.pt` (measured) | 0.816 |
| this preliminary, both arms | 0.884 |
| uniform flat profile | 0.889 |

The entire GO/PARTIAL/NO-GO band `[0.46, 0.50]` straddles **0.4926, a molecule-blind
constant**. Passing GO would mean "matched a constant", not "recovered physics". Worse,
the never-grounded regime (0.82–0.89) is *above* the wrong-molecule permutation band
(0.65–0.68), meaning σ̂ there carries essentially no molecule-specific shape at all.

**Power consequence.** The pre-registration's own predicted effect size is ~0.05 in ρ.
Applied from 0.816 that lands at ~0.77 — still far above every landmark and
indistinguishable from zero. **Even if the hypothesis is true at its pre-registered
strength, the pre-registered run cannot detect it.** More seeds do not fix this.

## What a conclusive Gate 1 needs
Not more epochs of the same design. It needs (a) an anchor measured on the arm actually
being run, (b) a decision rule calibrated against the control ladder above, and (c) a
contrast between two arms sharing a common measured origin rather than an absolute
threshold. Plumbing, config (`configs/fix_g_gate1.yaml`) and the ρ-eval
(`scripts/experiments/fix_g_rho_eval.py`) are committed; `verdict()` in the latter still
encodes the invalid absolute thresholds and must be replaced before reuse.
