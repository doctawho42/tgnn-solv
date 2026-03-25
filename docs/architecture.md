# TGNN-Solv Architecture

## Table of Contents

- [Forward Pass Pipeline](#forward-pass-pipeline)
- [Training: Three-Phase Curriculum](#training-three-phase-curriculum)
- [Data Pipeline](#data-pipeline)
- [Key Design Decisions](#key-design-decisions)
- [Other Modules](#other-modules)
- [Configuration](#configuration)
- [Molecular Featurization](#molecular-featurization)

## Forward Pass Pipeline

The `TGNNSolv` forward pass runs in this sequence:

1. **GNNEncoder** (`layers.py`) — the default `shared_residual` backbone uses
   a shared 6-layer MPNN for both solute and solvent, then applies lightweight
   role-specific adapters at the end. An alternative `split_late` mode keeps
   early layers shared but gives the last few message-passing layers separate
   solute/solvent weights for direct shared-vs-asymmetric comparison. In the
   v2 architecture, encoder outputs used by crystal-property heads are
   temperature-invariant by default.
2. **Auxiliary heads** (`heads.py`) — `HansenHead` and a lightweight
   `AuxPropsHead` run *before* interaction on the pre-interaction
   representations. In the maintained architecture the auxiliary head predicts
   only molar volume `V_m`, because that is the only auxiliary quantity used by
   the current objective.
3. **Interaction** (`layers.py`) — default
   `SoluteSolventCrossAttention` (stacked Transformer cross-attention with
   global tokens), optional `BipartiteMessagePassing` (complete bipartite
   message passing between solute/solvent atoms). Temperature can be injected
   here, but the default paper config keeps it out of the encoder and
   interaction stack to avoid leakage into crystal-property heads. Requires
   padding via `pad_atom_features()`.
4. **PhysicsAwareReadout** (`layers.py`) — concatenates attention pooling +
   Set2Set pooling → 3× hidden_dim vector per molecule.
5. **Optional Morgan augmentation** (`features.py`, `heads.py`) — when
   `use_morgan_features=True`, solute and solvent Morgan fingerprints are
   projected into the graph-level representation space and added to the
   pre-head and post-interaction molecular vectors. This supplements the GNN
   representation without bypassing the thermodynamic path.
6. **Optional molecular priors** (`features.py`, `heads.py`) — the codebase
   supports two mutually exclusive prior modes for `Hansen` and `V_m`:
   learned descriptor-conditioned priors (`use_descriptor_priors=True`) and
   deterministic fixed fragment-count group priors (`use_group_priors=True`).
   In both modes the graph-side heads predict only a bounded residual around
   the coarse prior, so the path stays physics-first.
7. **PairRepresentation** (`heads.py`) — combines
   `[g_sol, g_slv, g_sol * g_slv, |g_sol - g_slv|]` into a single pair vector.
8. **SolventTypeMoE** (`heads.py`) — optional mixture-of-experts routing based
   on solvent type, applied to the pair vector.
9. **Prediction heads** — `FusionHead` (T_m, ΔH_fus, and by default a fixed
   `ΔCp_fus = 0` unless explicit `ΔCp_fus` prediction is enabled),
   `NRTLHead` (default compact `ref_invT` form with `tau(T_ref)` +
   inverse-temperature slopes; legacy `dg/a_T` and `abc` remain supported)
   receives explicit temperature features, `HansenHead`, and a `V_m`-only
   `AuxPropsHead`.
10. **SLESolver** (`solver.py`) — iterative fixed-point solver (SLE + NRTL)
   with **zero learnable parameters**. Uses `SLESolverFunction`
   (custom `torch.autograd.Function`) with implicit differentiation via the
   implicit function theorem for stable training gradients. The v2 solver adds
   residual-based stopping, adaptive damping, and an explicit temperature
   gradient term in the implicit backward.
11. **AdaptivePhysicsCorrection** (`heads.py`) — per-sample gating between
   the physics prediction and a bounded parameter-space proposal. The module
   predicts bounded deltas for `T_m`, `ΔH_fus`, `tau_12(T)`, and `tau_21(T)`,
   re-runs the corrected parameters through the SLE solver, then blends the
   resulting residual:
   `ln(x₂)_proposal = SLE(theta + delta_theta)`,
   `ln(x₂) = ln(x₂)_physics + (1 - σ(w)) · clip(ln(x₂)_proposal - ln(x₂)_physics)`.

## Training: Three-Phase Curriculum

- **Phase 1** (50 epochs): Property pretraining only — no solubility loss.
  Trains heads on T_m, ΔH_fus, Hansen, γ∞. Correction gate is frozen.
- **Phase 2** (200 epochs): Full SLE training with solubility loss.
  Maintained configs keep auxiliary/property losses deliberately light so
  `ln x₂` fitting dominates, and the correction gate unfreezes at
  `phase2_correction_unfreeze_epoch` (paper default: 20). Early stopping still
  uses val MAE.
- **Phase 3** (50 epochs): Fine-tuning — lower LR, moderate monotonicity and
  correction penalties. Restores best model at end.

Loss components (weights vary by phase, see
`src/tgnn_solv/trainer.py::DEFAULT_PHASE_WEIGHTS` and config overrides):
`sol` (Huber on ln x₂), `T_m`, `dH`, `hansen`, `gamma_inf`, `mono`
(dx₂/dT ≥ 0 penalty), `res` (correction magnitude), `bridge`
 (Hansen–NRTL consistency), `tau_reg`, `phys_pref`, `direct_reg`
 (keep the residual proposal local), `direct_nll`
 (uncertainty on the residual proposal), `pair_temp_rank`
 (same-pair temperature monotonicity), `vant_hoff_local`
 (local linearity in `ln x₂` vs `1/T`), `moe_balance`,
 `descriptor_prior`, `group_prior`.

## Data Pipeline

- `sources.py` — downloads/parses BigSolDBv2.1 (primary ~121k solubility
  records), Bradley melting points, curated NIST values, Hansen parameters,
  and IDAC (γ∞) data. LogS→x₂ uses density/3D-volume estimates when x₂ is
  missing.
- `builder.py` — `DataBuilder` merges all sources via left join on canonical
  SMILES. Also appends "auxiliary-only" records (compounds with T_m but no
  solubility) for Phase 1 pretraining.
- `split.py` — group-based train/val/test split using greedy bin-packing.
  Modes: `solute_scaffold` (default), `solute` (random by solute SMILES),
  `solvent` (no solvent overlap).
- `dataset.py` — `TGNNSolvDataset` returns
  `(solute_graph, solvent_graph, targets_dict)` triples. All auxiliary targets
  have boolean mask columns (`has_T_m`, `has_dH_fus`, etc.) since most records
  are missing some auxiliary labels. The train-loader utilities in the same
  module also expose `PairTemperatureBatchSampler`, which groups repeated
  `(solute, solvent)` pairs across temperatures into the same minibatch.
- `solvent_types.py` — solvent type classification used for MoE routing.

## Key Design Decisions

- **Implicit differentiation**: During training, `SLESolverFunction` runs
  successive substitution *without* gradient tracking in the forward pass, then
  computes exact gradients through the converged fixed point using the implicit
  function theorem. The solver now also propagates the NRTL contribution to
  `d ln(x₂) / dT`, so monotonicity regularization no longer depends on a
  separate explicit-only path by default. Controlled by
  `TGNNSolvConfig.use_implicit_diff`.
- **Temperature enters the state block explicitly**: The default v2 setup keeps
  `T` out of the crystal-property encoder path and injects it directly into the
  NRTL head / correction summary instead. This reduces temperature leakage into
  `T_m`, `ΔH_fus`, and other temperature-invariant predictions.
- **Morgan fingerprints are optional chemical side information**: the
  maintained implementation can inject Morgan fingerprints into the molecular
  representations used by the crystal-property heads and pair block, but the
  thermodynamic solver and correction logic remain unchanged.
- **Descriptor priors are optional chemical side information**: the
  maintained implementation can map fixed RDKit descriptors to coarse `Hansen`
  and `V_m` priors, then let the graph heads learn only bounded residuals.
  This path is experimental, remains disabled by default, and is mutually
  exclusive with fixed group priors.
- **Fixed group priors are optional chemical side information**: the
  maintained implementation can also map deterministic fragment-count features
  to coarse `Hansen` and `V_m` priors, then let the graph heads learn only a
  bounded residual. This is the stricter, hand-crafted prior ablation relative
  to the learned descriptor-prior adapter.
- **Compact NRTL parameterization**: The default configuration now uses the
  more identifiable `ref_invT` mode, where the model predicts `tau(T_ref)` and
  one inverse-temperature slope per direction. The solver converts this form to
  the ABC representation internally, while `legacy` and `abc` layouts remain
  supported for older checkpoints and experiments.
- **Switchable encoder asymmetry**: The maintained default is still the current
  shared backbone (`encoder_role_mode="shared_residual"`). The codebase also
  supports `encoder_role_mode="split_late"` for direct shared-vs-asymmetric
  comparisons without changing the rest of the architecture.
- **Minimal auxiliary-property path**: The maintained architecture predicts
  only `V_m` in `AuxPropsHead`. Earlier unsupervised outputs such as `eps_r`,
  `mu`, and `n_D` were removed because they were not used anywhere in the loss
  and only introduced underconstrained latent capacity.
- **Physics layers have zero learnable parameters**:
  `IdealSolubilityLayer`, `NRTLLayer`, and `HansenDistanceLayer` are fully
  hardcoded thermodynamic equations.
- **Constrained activations**: All physical outputs are range-constrained
  (T_m via sigmoid in [100, 700] K; α via sigmoid in [0.1, 0.6];
  ΔH_fus via softplus > 0).
- **Bounded correction**: The residual-correction head cannot replace the
  physics solution with an arbitrary direct predictor. It can only propose
  bounded parameter deltas, and the resulting solubility residual is clipped
  within `±correction_max_abs`.
- **Same-pair temperature regularization**: The canonical training loader uses
  pair-aware batching so minibatches systematically contain multiple
  temperatures for the same `(solute, solvent)` pair when the data allows it.
  The loss then adds ranking and local van't Hoff consistency penalties, making
  the train-time objective closer to the evaluation-time extrapolation
  analyses.
- **SLE runs in float32**: The SLE solver casts to float32 for numerical
  stability even when training in mixed precision.
- **Scatter without torch_scatter**: `scatter_add` and `scatter_mean` are
  implemented natively in `layers.py` to avoid the `torch_scatter` dependency.

## Other Modules

- `progress.py` — lightweight progress-bar helpers (`progress()`, `trange()`)
  with graceful fallback to plain iterables when tqdm is unavailable. Used
  throughout training and inference loops.
- `eval_temperature.py` — temperature-dependent evaluation: stratified metrics
  (T=298K vs other), extrapolation analysis (train on T≤T_cut, test on T>T_cut),
  van't Hoff consistency checks, per-pair temperature curves.
- `evaluate.py` — `Evaluator` class with stratified metrics by solvent type,
  solubility range, temperature, and auxiliary data availability.
- `uncertainty.py` — `MCDropoutPredictor` (N forward passes with dropout
  active) and `EnsemblePredictor` (K trained models).
- `domain.py` — `ApplicabilityDomain`: Mahalanobis distance in
  pair-representation space + Tanimoto similarity to training set.
  Call `ad.fit(train_loader)` once, then `ad.score(smi_solute, smi_solvent, T)`.
- `pretrain.py` — optional Stage 0 GNN pretraining on ZINC250k:
  masked subgraph + bond prediction + contrastive + RDKit property prediction.
- `ablation.py` — full ablation study framework. The current CLI variants
  include the reference model, fixed-group-prior ablation, split-late encoder,
  no cross-attn, no NRTL, no curriculum, no aux losses, no correction,
  no implicit diff, DirectGNN, and small/large scaling variants.
- `baselines/` — `DirectGNN`: same GNN + cross-attention backbone but with
  direct MLP → ln(x₂) prediction (no physics). Used as the key ablation to
  validate physics adds value. `ThermometerEncoder`: ordinal temperature
  encoding with fractional bin filling for smooth gradients.

## Configuration

All hyperparameters live in `TGNNSolvConfig` (a `dataclass`). Key fields:

- `hidden_dim=256`, `n_gnn_layers=6`, `n_cross_attn_layers=3`, `pair_dim=512`
- `encoder_role_mode="shared_residual"` (default) or `"split_late"`
- `encoder_role_specific_layers` — number of late role-specific GNN layers in
  `split_late` mode
- `n_iter_train=5`, `n_iter_eval=20` — SLE fixed-point iterations
- `solver_tol_train`, `solver_tol_eval`, `solver_adaptive_damping` —
  residual-based convergence control for the solver
- `use_implicit_diff=True` — use implicit differentiation in backward pass
- `interaction_mode="cross_attn"` (default) or `"bipartite"`
- `set2set_steps=3`
- `nrtl_tau_mode="ref_invT"` (default), `"legacy"`, or `"abc"`
- `use_solvent_moe=True`, `solvent_moe_experts`, `solvent_moe_hidden`,
  `solvent_type_emb_dim`
- `use_temperature_in_encoder=False`,
  `use_temperature_in_interaction=False`,
  `use_temperature_in_nrtl_head=True` — default v2 temperature routing
- `use_morgan_features=False`, `morgan_radius=2`, `morgan_n_bits=2048`,
  `morgan_hidden_dim=256` — optional Morgan fingerprint augmentation for
  TGNN-Solv and DirectGNN
- `use_descriptor_priors=False`, `descriptor_prior_hidden_dim=128`,
  `descriptor_prior_hansen_residual_max=5.0`,
  `descriptor_prior_vm_residual_max=30.0`,
  `descriptor_prior_reg_weight=0.0` — optional descriptor-conditioned
  `prior + residual` path for `Hansen` and `V_m`
- `use_group_priors=False`, `group_prior_hansen_residual_max=5.0`,
  `group_prior_vm_residual_max=30.0`, `group_prior_reg_weight=0.0` —
  optional fixed fragment-count group priors for `Hansen` and `V_m`;
  mutually exclusive with `use_descriptor_priors`
- `correction_max_abs=2.0` — trust-region width for bounded residual correction
- `predict_dCp_fus=False`, `fixed_dCp_fus=0.0` — keep the ideal-solubility
  branch identifiable unless direct `ΔCp_fus` labels are introduced
- `phase2_correction_unfreeze_epoch=20` — epoch index inside Phase 2 where the
  bounded correction starts training
- `correction_Tm_max_delta`, `correction_dH_fraction`,
  `correction_tau_max_delta` — bounds for parameter-space correction
- `use_pair_temperature_batching=True`,
  `pair_temperature_min_group_size`,
  `pair_temperature_group_chunk_size` — controls for same-pair temperature
  batching during training
- Scale factors (`S_H`, `S_g`, `S_delta`, etc.) normalize head outputs into
  physically stable ranges.

## Molecular Featurization

`smiles_to_graph(smiles)` → PyG `Data`.

- Atom features (35-dim): atomic number (one-hot over 12 elements),
  hybridization, formal charge, H count, aromaticity, ring membership,
  electronegativity, vdW radius, polarizability.
- Bond features (8-dim): bond type (single/double/triple/aromatic),
  conjugated, in ring, stereo E/Z.
- `smiles_to_morgan_fp(smiles)` returns an optional Morgan fingerprint vector,
  and `compute_pair_morgan_features(...)` builds pair-level fingerprint +
  temperature features for baseline experiments.
- `smiles_to_descriptor_prior_features(smiles)` returns a compact fixed RDKit
  descriptor vector used by the optional `Hansen` / `V_m` prior heads.
