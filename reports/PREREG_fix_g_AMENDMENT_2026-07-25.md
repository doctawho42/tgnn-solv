# Amendment to PREREG_fix_g_2026-07-19.md — 2026-07-25

Written **before** any number from the amended design was computed. It retires the original
decision rule, states why, and fixes two factual errors in the original document. The
original pre-registration is left in place unedited; this file supersedes it where they
conflict.

Everything below was established by free local measurement on existing artifacts. No GPU
spend informed this amendment.

---

## 1. Why the original decision rule is retired

### 1.1 The ρ_free = 0.51 anchor describes a different arm

The anchors came from `results/sur/surrogate_seeds/surrogate_seeds.json`
(`aggregate.sle_vs_true.mean = 0.5065`, `aggregate.grounded_vs_true.mean = 0.3638`). That
file's `recipe` is `{ep_warm: 40, ep_sle: 70}` — the model was **σ-grounded for 40 warmup
epochs and then drifted** by SLE training.

The Gate-1 free arm sets `sigma_warmup_epochs: 0` and `sigma_aux_steps_per_epoch: 0`. It is
**never grounded**. The 0.51 figure therefore does not describe it.

Measured on the one converged never-grounded artifact in the repo,
`checkpoints/cosmo_sac/tgnn_cosmo.pt` (`activity_model=cosmo_sac`, full 30/70/10 schedule,
Phase 2 early-stopped at 39, manifest sha256 identical to the live
`notebooks/data/processed/*.csv`):

```
rho = 0.8156   (drop-one 0.8084 - 0.8208, rank=0, n=44)
```

The honest expectation for the planned free arm is **≈ 0.82**. The pre-committed thresholds
were mis-anchored by roughly 0.3 in ρ.

### 1.2 The decision band straddles a molecule-blind constant

Reproduced by `scripts/experiments/rho_control_ladder.py` on the same n=44 set with the same
committed metric (`rho_dataset` = mean‖r‖ / mean‖ref‖, algebraically identical to
`rel_deviation` in `run_compensation_surrogate.py`):

| reference | ρ |
|---|---|
| original GO threshold | 0.46 |
| **leave-one-out corpus-mean profile — zero molecular information** | **0.4926** |
| original NO-GO threshold | 0.50 |
| original ρ_free anchor (grounded-then-drifted) | 0.51 |
| true profile of a *randomly permuted* molecule (5 derangement seeds) | 0.6505 – 0.6835 |
| converged never-grounded `tgnn_cosmo.pt` (measured) | 0.8156 |
| 2026-07-19 preliminary, both arms | 0.884 |
| uniform flat profile | 0.8886 |

The whole GO/PARTIAL/NO-GO band `[0.46, 0.50]` sits on top of **0.4926**, a predictor that
uses no molecular information at all. Under the original rule, "GO" would have certified
matching a constant.

A second reading of the ladder matters independently of the decision rule: the
never-grounded regime (0.82–0.89) scores **worse than assigning a real σ-profile to the
wrong molecule** (0.65–0.68). The free COSMO-SAC latent carries essentially no
molecule-specific σ shape.

### 1.3 Consequence for power

The original document's own predicted effect (failure mode 2) is ≈ 0.05 in ρ. Applied from
0.816 rather than 0.51, a true-hypothesis result lands near 0.77 — above every landmark in
the ladder and indistinguishable from no effect. **The pre-registered design cannot detect
the effect it predicts.** Additional seeds do not change this; the defect is the regime, not
the sample size.

---

## 2. Amended design: matched fork from a common measured origin

Both arms resume from the same parent, `checkpoints/cosmo_sac/tgnn_cosmo.pt`, via
`--resume ... --resume-extend`:

- **fixg** — `cosmo_sac_kernel_residual_rank=1`
- **free** — `cosmo_sac_kernel_residual_rank=0`

Rank 1 adds exactly 52 parameters (`kernel_B` 51 + `kernel_a` 1). `kernel_a` initializes to
zeros, so the residual is **exactly zero-effect at initialization**: the two arms are the
identical function at the fork, at a *measured* common origin ρ = 0.816. Both use seed 42,
the same schedule, and the same VM so preemption events are shared.

This removes the need for any external anchor: the quantity of interest is a contrast
between two arms that started identical.

**Scope, stated up front.** This tests *"can a low-capacity closure residual pull an
already-converged, never-grounded latent toward physical?"*. It does **not** test
from-scratch co-training. No oracle is consumed — the parent never saw VT-2005 — so the
original "without any oracle" thesis is preserved. The test is **one-sided**: a positive is
informative; a null is basin-confounded and must be reported as a bounded negative, not a
kill.

## 3. Amended decision rule

Primary quantity: `Δρ = ρ_free(E) − ρ_fixg(E)` at matched continuation epoch E, both arms
forked from the same parent.

- **GO** — `Δρ ≥ 0.05` **and** `ρ_fixg < 0.6505` (crosses below the wrong-molecule
  permutation band, i.e. σ̂ becomes molecule-specific) **and** val MAE within 10% of the free
  fork.
- **PARTIAL** — `Δρ ≥ 0.02` but `ρ_fixg ≥ 0.6505`.
- **NULL** — `Δρ < 0.02`. Reported as a bounded negative with the achieved resolution
  stated. Not "NO-GO", and not a kill of the hypothesis.

Implemented in `verdict()` in `scripts/experiments/fix_g_rho_eval.py`; the controls are
carried in the output JSON so a verdict cannot be read without them.

**Sanity check that gates everything:** at continuation epoch 0 both arms must read
ρ = 0.816 exactly. If they do not, the fork is broken and the run stops.

**Kill gate at continuation epoch 8** (≈ 1/3 of the budget): stop and bank the bounded
negative if `|ρ_fixg − ρ_free| < 0.005` and both remain above 0.80.

## 4. Factual corrections to the original document

- "full corpus n=5608" is wrong. `notebooks/data/processed/train.csv` has **111,724 rows**,
  **15,665 unique solutes**, 96,897 rows carrying a solubility label.
- "Gate 1 — core go/no-go (~1 GPU run…)" contradicts the same document's "3 seeds". The
  amended design runs **one matched fork pair, seed 42**. `rho_sd` will be 0.0 by
  construction; the arms share initialization bitwise and share data order, so there is no
  init noise in the contrast to average over. This buys power per dollar but does not
  satisfy the original "3 seeds" line, which is the reason this amendment exists.

## 5. What is given up

1. The from-scratch claim (restoration, not co-training from initialization).
2. Seed replication.
3. Gates 2b/2c and Gate 3 — unaffordable under either design.
4. Phase 3 is dropped. Worth recording separately: `src/tgnn_solv/loss.py` computes
   `d_lnx2_dT` via `torch.autograd.grad(..., create_graph=False)`, so the monotonicity
   penalty contributes no gradient to any parameter. Dropping Phase 3 costs nothing
   scientifically; the inert penalty is a latent bug to file on its own.
