# fix-g Gate 1 — preliminary run (2026-07-19): INCONCLUSIVE (underpowered)

**Status: NOT a go/no-go verdict.** The cheap preliminary undertrained both arms, so
the ρ signal never reached the regime where the pre-registered thresholds apply. This
file exists so the raw "NO-GO" string in `gate1_prelim_rho_2026-07-19.json` is not later
misread as a genuine kill of the co-trainable-kernel hypothesis.

## What was run
- **Where:** transient GCP L4 VM (`tgnn-fixg`, us-west1-a), deleted immediately after.
- **Budget (deliberately cheap, cost-constrained):** 25k-row train subset
  (`head -n 25001 train.csv`), Phase 1 = 6 epochs, Phase 2 = 8 epochs, Phase 3 = 0,
  σ-grounding OFF (`sigma_steps_per_epoch=0`, `sigma_warmup_epochs=0`), CPU ρ-eval.
- **Two matched arms, same seed 0, same data:**
  - `fixg` = `cosmo_sac_kernel_residual_rank=1` (co-trainable 52-param residual ON)
  - `free` = `cosmo_sac_kernel_residual_rank=0` (residual OFF)
- **Metric:** ρ = mean‖σ̂−σ‖ / mean‖σ‖ on the fixed n=44 matched VT-2005 solutes
  (`fix_g_rho_eval.py`, reusing `rel_deviation` from `run_compensation_surrogate.py`).

## Result
| arm  | ρ     | drop-one range | rank |
|------|-------|----------------|------|
| fixg | 0.884 | 0.882–0.886    | 1    |
| free | 0.884 | 0.883–0.887    | 0    |

Pre-registered anchors: ρ_free ≈ 0.51 (converged free baseline), ρ_grounded ≈ 0.36,
GO ≤ 0.46, NO-GO ≥ 0.50.

## Why this is invalid, not a NO-GO
Both arms sit at ρ ≈ **0.88**, far above the ρ_free ≈ **0.51** anchor that a *converged*
free model reaches. The subset + short budget never trained the σ-head to the point where
σ̂ carries physical structure, so there is nothing for the kernel residual to move: fixg = free
= 0.88 means "both equally undertrained," not "the residual does not help." Per the standing
discipline (*never run a separating test on a checkpoint that does not reproduce the
phenomenon*), these checkpoints do not reproduce the ρ_free ≈ 0.51 baseline, so the
separating comparison is uninformative.

## What a conclusive Gate 1 needs
Full-corpus training to convergence (free ρ must land near 0.51 before the fixg−free
contrast is meaningful), 3 seeds per arm. This is expensive on the slow cosmo-SLE path
(~19 min/epoch full corpus, 16–30 fixed-point iters/forward) and is deferred under the
current cost constraint. Plumbing, config (`configs/fix_g_gate1.yaml`), and the ρ-eval
(`scripts/experiments/fix_g_rho_eval.py`) are all committed and ready.
