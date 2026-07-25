# fix-g matched fork — final result (2026-07-25): **NULL**

Pre-registration: `reports/PREREG_fix_g_2026-07-19.md`, superseded where they conflict by
`reports/PREREG_fix_g_AMENDMENT_2026-07-25.md`. Run: L4 spot, europe-west3-a, both arms
concurrently on one VM, 24 phase-2 epochs each, ~6.5 GPU-hours, ≈$2.2. VM deleted; no GCP
resources remain.

## Design and what was verified before spending

Both arms resumed from the same converged parent `checkpoints/cosmo_sac/tgnn_cosmo.pt`
(`--resume --resume-extend`), identical in all 239 config keys but one:
`cosmo_sac_kernel_residual_rank` = 1 (fixg) vs 0 (free). Same seed 42, same data order, same
VM. Verified before launch:

- the fork adds exactly 2 tensors / 52 values and drops nothing (the run log names them);
- `‖B·diag(a)·Bᵀ‖_F = 0.000e+00` at init, so the arms are the identical function at the fork;
- both arms read ρ = 0.8155713527 there, difference 0.000e+00;
- gradient reaches `kernel_a` (9.27e-4 on a real batch) while `kernel_B.grad` = 0, exactly as
  `∂/∂B ∝ a = 0` predicts.

Neither arm restores optimizer state (`--resume-extend` nulls `resume_state`), and the 51
extra `torch.randn` draws cannot desynchronise data order — `PairTemperatureBatchSampler`
builds its own `random.Random(seed + _epoch)`.

## Two metrics, never mixed

`ρ_dataset` = mean‖r‖ / mean‖ref‖ (the committed `rel_deviation`; the control ladder is on
this scale): parent = **0.8156**. Mean of per-molecule ratios (what the paired analysis
averages): parent = **0.8231**. The paired Δ is unaffected — the offset is common to both
arms and cancels — but no absolute-scale statement may subtract one from the other.

## Trajectory (paired, epoch-matched, mean-of-ratios)

| epoch | ρ_fixg | ρ_free | Δρ | 95% CI | wins | sign p |
|---|---|---|---|---|---|---|
| 4 | 0.7890 | 0.7938 | +0.0048 | [+0.0016, +0.0082] | 27/44 | 8.7e-02 |
| 8 | 0.7768 | 0.7923 | +0.0155 | [+0.0110, +0.0199] | 39/44 | 7.0e-08 |
| 12 | 0.7611 | 0.7672 | +0.0061 | [+0.0032, +0.0088] | 34/44 | 1.9e-04 |
| 16 | 0.7580 | 0.7668 | +0.0089 | [+0.0060, +0.0118] | 37/44 | 2.7e-06 |
| 20 | 0.7539 | 0.7617 | +0.0078 | [+0.0047, +0.0109] | 34/44 | 1.9e-04 |
| **final (selected)** | **0.8231** | **0.8231** | **+0.0000** | [0, 0] | **0/44** | 1.0 |

Least-squares slope over the five in-training points: **−1.6e-5 per epoch**. The contrast
does not accumulate. Epoch 8 sits 4.2 sd above the other four and is a transient.

## The decisive row is the last one

Both arms' **selected** models are byte-equivalent in σ̂ and equal to the parent. The trainer
restores the best-validation model, and validation never improved on the parent: val MAE
2.726 (parent) → 3.098 (fixg) / 3.096 (free) at epoch 23, R² −0.355 → ≈ −0.66, while train
loss fell 0.477 → 0.322. **Twenty-four epochs of continued training produced nothing that
passed the project's own model-selection criterion in either arm.** Every checkpoint carrying
the Δρ signal is one that model selection discards as worse at the actual task.

That row is also a clean negative control on the measurement chain: two independently trained
processes, restored to the same parent, give exactly 0.0000 on 0/44 molecules. ρ evaluation
is bitwise deterministic and the pipeline adds no spurious difference.

## Verdict: NULL

The amended rule: GO = Δρ ≥ 0.05 **and** ρ_fixg < 0.6505 **and** val MAE within 10% of free;
PARTIAL = Δρ ≥ 0.02; NULL = Δρ < 0.02.

The largest Δρ observed is 0.0155, at a transient; the stable level is 0.005–0.009. That is
~2–4× under the PARTIAL bar and ~6× under GO. The second GO condition is not closing:
ρ_fixg = 0.7539 at epoch 20 against the 0.6505 wrong-molecule band, ~101 epochs away at the
observed descent. The third condition is satisfied between arms (3.098 vs 3.096) but is not a
passed control — it is blind to the shared degradation from the parent.

**Bounded negative, resolution ~0.008 within one fork.** This excludes a GO-scale effect for
*this* residual parameterisation. It says nothing about a differently parameterised closure
fix, and it is not a kill of the underlying hypothesis.

## What must not be claimed

- **"The residual absorbed closure error" / "made σ̂ more physical."** The residual is
  thermodynamically inert forward: max |B·diag(a)·Bᵀ| = 2.6e-4 kcal/mol against RT(298 K) =
  0.5925, i.e. 4.4e-4 of RT, moving ln Γ by ~1e-6 relative. And σ̂ is read from the
  solute-only pre-interaction embedding and never passes through `CosmoSacLayer`. The only
  permissible mechanism is *the residual changed the gradient that trains the σ-head*.
  (Worth stating alongside: all aux streams are off in this fork, so `head_sigma` is trained
  **only** through `CosmoSacLayer` — which is why the residual could steer ρ at all.)
- **"Small but reliably nonzero."** "Reliably" is a claim about run-to-run reproducibility
  that nothing here measures: effective n over forks is 1. The CIs and sign tests are over 44
  molecules spanning only 8 unique Bemis–Murcko scaffolds. Within a *single* arm, a 4-epoch
  step produces paired ρ changes of the same magnitude and significance — so these statistics
  certify "two different models", which the design guarantees anyway. Say instead:
  *consistently positive at five matched checkpoints of a single fork pair.*
- **"The residual makes σ̂ molecule-specific."** Centred R² is negative at every checkpoint in
  both arms, and replacing each molecule's σ̂ with the model's own corpus-mean σ̂ *lowers* ρ by
  ~0.021 in both. Per-molecule variation is net harmful in both arms.
- **"ρ improved" without the task metric beside it.** ρ descended while val MAE worsened ~14%.
- Any absolute-scale sentence mixing the two ρ definitions above.

## Surviving threats

1. **Optimizer-trajectory divergence — not ruled out; the load-bearing gap.** The arms differ
   by 1.80e-2 over shared tensors at epoch 4 (8.98e-2 in `head_sigma` alone), before any ρ is
   scored. Training-time nondeterminism is unbounded: `seed.py` sets
   `use_deterministic_algorithms(True, warn_only=True)` and `CUBLAS_WORKSPACE_CONFIG` is unset.
2. **Global gradient clipping is an unmeasured coupling channel.** `grad_clip = 2.0` is applied
   to the whole parameter set, so when it binds the 52 extra parameters rescale the update for
   all 5.32M shared ones.
3. **The window is an overfitting transient under a 10× LR restart** — `--resume-extend`
   restarts phase 2 at `lr_phase2 = 8.53e-5` against the `lr_phase3 = 8.53e-6` the parent
   finished on.
4. **The inferential population is smaller than n = 44** — 8 scaffolds, 24 acyclic molecules.
5. Both arms' predictions fail the control ladder throughout (0.754–0.792 against 0.4926 for a
   molecule-blind constant profile and 0.6505 for a randomly permuted molecule's true profile).
   That floor belongs in the same paragraph as any statement of the effect.

## The one next measurement, if compute returns

**A sham fork**: same parent, seed and schedule, `rank = 1` with `kernel_a` frozen at exactly
0. The residual is then identically zero all run, while the 52 parameters still exist, still
receive gradients, and still enter the global grad-norm — holding constant every channel the
audit could not separate and removing only the thing the effect is attributed to. If the sham
also lands ~+0.008 below free, the effect is trajectory separation and the observation dies;
if it lands at zero, the +0.008 becomes attributable. One arm, ~6 GPU-hours.

Do **not** run a plain `free2` re-run instead: it is configuration-identical to `free` and
would return Δρ ≡ 0 by construction.

## Corrections to earlier readings in this thread

- An intermediate reading reported Δρ = +0.0034 and "not growing". It compared fixg@epoch-4
  against free@epoch-8: the rolling checkpoint is rewritten only every `--checkpoint-every`
  epochs, so `fixg_5`…`fixg_9` are byte-identical (md5 `b679b6f7…`). `fix_g_paired_delta.py`
  now reads each checkpoint's `(phase, epoch)` from `resume_state` and refuses mismatched
  pairs.
- `results/fix_g/gate_e8_2026-07-25.md` projected Δρ → +0.058 at epoch 24 from the epoch-4→8
  pair. That was a two-point extrapolation through what the full trajectory shows to be a
  4.2-sd transient; a two-point fit has no degrees of freedom with which to distinguish a
  trend from a spike. The realised value is +0.0078 at epoch 20 and +0.0000 at selection.
