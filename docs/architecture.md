# TGNN-Solv Architecture

## System Overview

The repository maintains two closely related model families:

- `TGNN-Solv`
  - predicts crystal and interaction parameters, solves SLE, then applies a
    bounded correction in solver parameter space
- `DirectGNN`
  - reuses the same graph backbone but predicts `ln(x2)` directly without the
    thermodynamic bottleneck

The central comparison is whether the explicit physics bottleneck helps
relative to the same backbone trained directly on solubility.

## Internal Package Map

The implementation still lives in the legacy flat modules such as:

- `src/tgnn_solv/model.py`
- `src/tgnn_solv/trainer.py`
- `src/tgnn_solv/inference.py`

For contributor navigation, the package now also exposes grouped namespaces:

- `tgnn_solv.models`
- `tgnn_solv.physics`
- `tgnn_solv.training`
- `tgnn_solv.evaluation`
- `tgnn_solv.chemistry`
- `tgnn_solv.core`

Those grouped imports are thin compatibility re-exports over the legacy flat
modules. They do not change runtime behavior.

## Optional Stage 0 Pretraining

Outside the main paper curriculum, the repository also implements a standalone
encoder/readout pretraining stage in `src/tgnn_solv/pretrain.py`.

This is distinct from `Phase 1` in `trainer.py`:

- `Stage 0`
  - optional pre-curriculum molecular pretraining on large SMILES sets
- `Phase 1`
  - supervised auxiliary warmup on the processed solubility training split

The maintained `Pretrainer` updates:

- `model.gnn`
- `model.readout`

in place, using four tasks:

- masked subgraph atom reconstruction
- bond-type prediction
- RDKit property prediction
- graph contrastive learning

The temporary Stage 0 heads are discarded after pretraining, so the downstream
model remains the normal TGNN-Solv architecture.

## TGNN-Solv Forward Pass

The maintained `TGNNSolv` path in `src/tgnn_solv/model.py` runs in this order.

### 1. Dual-graph encoder

`GNNEncoder` encodes solute and solvent graphs with:

- `encoder_role_mode="shared_residual"` by default
- optional `encoder_role_mode="split_late"` for late role-specific blocks

Temperature is typically excluded from the crystal-property encoder path:

- `use_temperature_in_encoder=False`
- `use_temperature_in_interaction=False`
- `use_temperature_in_nrtl_head=True`

This keeps the crystal heads mostly temperature-invariant and injects
temperature later where it matters physically.

### 2. Pre-interaction auxiliary heads

Before solute-solvent interaction, the model predicts:

- `HansenHead`
- `AuxPropsHead` for `V_m`

Two optional prior paths can bound those predictions:

- `use_descriptor_priors=True`
  - learned adapter from compact RDKit-derived prior features
- `use_group_priors=True`
  - fixed fragment-count priors

In either mode, the graph branch predicts a bounded residual around the prior.

### 3. Optional Morgan side information

If `use_morgan_features=True`, Morgan fingerprints are projected into the
molecular representation space:

- before the crystal-property heads
- again after interaction/readout

This augments the graph branch without bypassing the physics path.

### 4. Solute-solvent interaction and pair representation

The default interaction block is stacked cross-attention:

- `interaction_mode="cross_attn"`

An alternative bipartite message-passing block is also supported:

- `interaction_mode="bipartite"`

`PhysicsAwareReadout` produces graph-level vectors, and the pair vector is then
constructed as:

`[g_sol, g_slv, g_sol * g_slv, |g_sol - g_slv|]`

Optional solvent-type routing is handled by `SolventTypeMoE`.

### 5. `FusionHead` crystal-property prediction

`FusionHead` predicts:

- `T_m`
- `dH_fus`
- `dCp_fus`

There are two maintained crystal modes.

Standard mode:

- `T_m = T_m_min + (T_m_max - T_m_min) * sigmoid(...)`
- `dH_fus = S_H * softplus(...)`
- `dCp_fus = fixed_dCp_fus` unless `predict_dCp_fus=True`

Crystal GC-prior mode:

- enabled with `use_gc_priors_crystal=True`
- raw `T_m_gc`, `dH_fus_gc`, and `dCp_fus_gc` are computed per solute in
  `group_contribution.py`
- raw GC priors come from SMARTS-based Joback-style fragmentation
- partial fragmentation is allowed; the hard `400 K` fallback is used only when
  no usable counts exist or a required increment is missing
- `scripts/training/train.py` fits a train-only affine calibration for the melting prior:
  - `T_m_gc_calibrated = gc_prior_tm_scale * T_m_gc + gc_prior_tm_bias`
- `FusionHead` then predicts only bounded residuals around the calibrated GC
  priors:
  - `T_m = T_m_gc_calibrated + gc_prior_Tm_residual_max * tanh(...)`
  - `dH_fus = dH_fus_gc * zero_centered_scale(...)`
  - `dCp_fus = dCp_fus_gc`

Important implementation details:

- the last linear layers of the GC residual branches are zero-initialized
- at initialization, the GC crystal prediction is exactly the calibrated prior
- `gc_prior_residual_freeze_epochs` can freeze those residual branches during
  the early part of Phase 1
- `use_gc_priors_crystal=True` requires `predict_dCp_fus=False`

### 6. `NRTLHead`

`NRTLHead` predicts binary interaction parameters from the pair vector plus
explicit temperature features.

Supported parameterizations:

- `ref_invT` (default)
  - predicts `tau(T_ref)` plus one inverse-temperature slope per direction
- `abc`
- `legacy`

`ref_invT` is the maintained compact form.

### 7. Solver-facing substitution and oracle injection

Before the SLE solver is called, the model can alter which crystal parameters
are sent into the solver while keeping the raw head outputs available for
auxiliary losses.

Relevant mechanisms:

- GC crystal priors
  - determine how `FusionHead` builds crystal predictions
- oracle injection
  - enabled with `use_oracle_injection=True`
  - during training, supervised `T_m` and/or `dH_fus` can replace predicted
    values in the solver path
  - raw `fusion_params` still store the model prediction, not the substituted
    value

`model.forward(...)` therefore exposes both:

- `fusion_params`
  - raw head predictions used by losses
- `solver_fusion_params`
  - actual values sent into the solver
- `fusion_gc_priors`
  - present when crystal GC priors are enabled
- `oracle_injection_masks`
  - present when oracle injection is active

For diagnostics, evaluation can force oracle injection explicitly without
changing normal inference behavior.

### 8. `SLESolver`

`SLESolver` contains zero learnable parameters. It combines:

- ideal solubility
- NRTL activity-coefficient terms
- iterative fixed-point solution

Key properties:

- training uses `n_iter_train`, evaluation uses `n_iter_eval`
- solver math runs in float32 for stability
- implicit differentiation is controlled by `use_implicit_diff`
- in GC crystal mode, `dCp_fus_gc` flows into the ideal-solubility term through
  the solver-facing fusion parameters

### 9. `AdaptivePhysicsCorrection`

The correction path is still structured around solver parameters. It does not
replace `ln(x2)` with an unconstrained direct bypass.

It:

1. predicts bounded deltas for `T_m`, `dH_fus`, `tau_12`, and `tau_21`
2. reruns the solver with those corrected parameters
3. blends the corrected result through a learned gate

## DirectGNN

`src/tgnn_solv/baselines/direct_gnn.py` reuses:

- the same encoder
- the same interaction stack
- the same readout
- thermometer temperature features

It removes:

- `FusionHead`
- `NRTLHead`
- `SLESolver`
- `AdaptivePhysicsCorrection`

and replaces them with a direct MLP to `ln(x2)`.

Optional DirectGNN feature paths:

- `use_morgan_features=True`
- `use_descriptor_augmentation=True`

### Descriptor augmentation

The maintained descriptor path now does the following:

- computes the full RDKit descriptor vector for solute and solvent
- sanitizes non-finite values to zero before model use
- normalizes descriptors with train-set mean/std only
- stores `descriptor_mean` and `descriptor_std` in the checkpoint
- reuses one shared descriptor MLP for both molecular roles
- augments the pair representation with
  `[d_sol, d_slv, d_sol * d_slv, |d_sol - d_slv|]`

## Training Behavior

`src/tgnn_solv/trainer.py` implements a three-phase curriculum:

- Phase 1
  - supervised property warmup only
  - no solubility loss
  - correction frozen
  - GC crystal residual branches can be frozen for the first
    `gc_prior_residual_freeze_epochs`
- Phase 2
  - full SLE training
  - correction unfreezes at `phase2_correction_unfreeze_epoch`
  - oracle injection, if enabled, anneals over the last part of the phase

## Inference-Time Utilities

The repository also ships post-training utilities that sit outside
`model.forward(...)` but are part of the maintained surface:

- `src/tgnn_solv/inference.py`
  - checkpoint loading/saving
  - single-system prediction
  - temperature scans
  - human-readable interpretation
- `src/tgnn_solv/uncertainty.py`
  - MC-dropout and deep-ensemble uncertainty estimation
- `src/tgnn_solv/domain.py`
  - applicability-domain / OOD screening

These are deployment and diagnostics layers, not extra learnable blocks inside
TGNN-Solv itself.

### Applicability domain

The current OOD helper fits on the training loader and combines:

- Mahalanobis distance in pair latent space
- nearest-neighbor Morgan Tanimoto similarity for solute and solvent

It also reports exact seen/unseen flags for the queried solute and solvent.

Despite some older high-level references, leverage is not part of the current
implementation’s decision path.
- Phase 3
  - low-learning-rate fine-tuning
  - oracle injection forced off

The canonical paper budget remains `50 / 200 / 50`.

## Pair-Aware Temperature Batching

The main TGNN training path uses pair-aware batching by default so losses like:

- `pair_temp_rank`
- `vant_hoff_local`

can observe multiple temperatures from the same `(solute, solvent)` pair in one
batch.

DirectGNN reuses the same batching controls where applicable.

## High-Signal Config Flags

The easiest configuration flags to miss are:

- `encoder_role_mode`
- `nrtl_tau_mode`
- `use_morgan_features`
- `use_descriptor_augmentation`
- `use_descriptor_priors`
- `use_group_priors`
- `use_gc_priors_crystal`
- `gc_prior_tm_scale`
- `gc_prior_tm_bias`
- `gc_prior_residual_freeze_epochs`
- `use_oracle_injection`
- `bridge_loss_weight`
- `use_walden_check`
- `use_pair_temperature_batching`

All live in `src/tgnn_solv/config.py`.

## Dataset Outputs

`TGNNSolvDataset` returns `(solute_graph, solvent_graph, targets_dict)`.

Core keys include:

- `T`
- `ln_x2`
- `has_solubility`
- `pair_key`
- `solvent_type`
- `T_m`, `T_m_mask`, `has_T_m`
- `dH_fus`, `dH_mask`, `has_dH_fus`
- `hansen_sol`, `hansen_mask`
- `ln_gamma_inf`, `gamma_mask`

Optional keys appear when their feature paths are enabled:

- `solute_morgan_fp`, `solvent_morgan_fp`
- `solute_descriptors`, `solvent_descriptors`
- `solute_descriptor_prior_features`, `solvent_descriptor_prior_features`
- `solute_group_prior_features`, `solvent_group_prior_features`
- `T_m_gc`, `dH_fus_gc`, `dCp_fus_gc`

## Checkpoints and Resume

The main training CLIs now support resumable checkpoints:

- `scripts/training/train.py --checkpoint-every ... --resume ...`
- `scripts/training/train_directgnn.py --checkpoint-every ... --resume ...`

The heavy experiment runners reuse those checkpoints automatically:

- `scripts/experiments/run_full_budget_experiment.py`
- `scripts/experiments/run_medium_budget_comparison.py`

## Artifact and Benchmark Metadata

The architecture layer now extends beyond the forward graph itself. Maintained
training and evaluation entry points emit structured sidecars so downstream
benchmarking and reproduction can recover provenance without relying on shell
history:

- checkpoint sidecars
  - `<checkpoint>.manifest.json`
  - `<checkpoint>.model_card.json`
- benchmark bundle sidecars
  - `run_manifest.json`
  - `benchmark_card.json`

These metadata files are built through `tgnn_solv.artifacts` and describe:

- model family
- resolved config path
- input data paths and checksums
- git commit and dirty state
- output artifact paths
- supported capability flags such as uncertainty, OOD, and physics reporting

That provenance layer is now part of the maintained system architecture, not an
optional afterthought.

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Training](training.md)
- [Baselines](baselines.md)
- [Config Cookbook](config_cookbook.md)
- [Evaluation & Inference](evaluation.md)

</div>
