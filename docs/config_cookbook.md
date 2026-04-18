# Config Cookbook

This page answers the practical question:

> Which config should I actually use for this task?

All configs live under `configs/`. The maintained ones fall into three groups:

- TGNN-Solv baselines and ablations
- DirectGNN baselines
- research extensions and workflow helpers

## Default Recommendation

If you need one starting point for the current maintained TGNN baseline, use:

- `configs/paper_config_tuned.yaml`

If you need the matched no-physics baseline, use:

- `configs/paper_config_directgnn_tuned.yaml`

If you are preparing an article-facing comparison bundle, pair those configs
with the canonical scaffold split and the maintained benchmark runners so the
resulting checkpoints also receive manifest and model-card sidecars.

## Maintained TGNN Configs

### `paper_config_tuned.yaml`

Use this when:

- you want the current maintained TGNN baseline
- you are running the standard full scaffold comparison
- you want the tuned shared-residual architecture without special priors

Key properties:

- `hidden_dim=256`
- `n_gnn_layers=6`
- `encoder_role_mode="shared_residual"`
- `interaction_mode="cross_attn"`
- `nrtl_tau_mode="ref_invT"`
- no GC crystal priors
- no oracle injection
- bridge active only through the explicit phase-loss tables

### `paper_config_tuned_tgnn_descriptors.yaml`

Use this when:

- you want to enrich TGNN pair representations with shared RDKit descriptors
- you want the descriptor-augmented TGNN path without changing the solver

Key properties:

- `use_descriptor_augmentation=true`
- descriptor normalization is fit on the training split and stored in the checkpoint
- `descriptor_augmentation_hidden_dim=128`
- higher dropout than the pure tuned baseline

Trade-off:

- stronger chemical side information
- less pure as a graph-only encoder comparison

### `paper_config_tuned_regularized.yaml`

Use this when:

- the tuned baseline is overfitting at the intended budget
- you want a safer medium-budget TGNN baseline

Key properties:

- `dropout=0.15`
- `weight_decay=1e-4`
- stronger Phase 2 `tau_reg`
- phase-local early stopping

### `paper_config_tuned_regularized_gc.yaml`

Use this when:

- you want the regularized schedule plus crystal GC priors

Key properties:

- everything from `paper_config_tuned_regularized.yaml`
- `use_gc_priors_crystal=true`

### `paper_config_tuned_regularized_descriptors.yaml`

Use this when:

- you want the regularized schedule plus TGNN descriptor augmentation

Key properties:

- everything from `paper_config_tuned_regularized.yaml`
- `use_descriptor_augmentation=true`

### `paper_config_tuned_gps.yaml`

Use this when:

- you want to replace the local-only MPNN encoder with GPS
- you want a graph-transformer-style encoder while keeping the rest of TGNN unchanged

Key properties:

- `encoder_type="gps"`
- `gps_positional_encoding="laplacian"` by default
- can be switched to `rwse` without changing the rest of TGNN
- shared GPS encoder output shape matches the standard MPNN path

### `paper_config_timp.yaml`

Use this when:

- you want the TIMP backbone while keeping the rest of TGNN-Solv unchanged
- you want graph message passing to split into dispersive and polar channels
- you want the maintained configuration that turns on TIMP-specific graph features

Key properties:

- `encoder_type="timp"`
- `use_gasteiger_charges=true`
- `use_phys_edge_features=true`
- `use_thermo_cross_attention=false`
- enables TIMP Hansen channel probes during training through the default trainer schedule

Trade-off:

- more physically structured graph updates before the solver
- higher featurization complexity than the default MPNN and GPS paths

### `paper_config_timp_full.yaml`

Use this when:

- you want the full TIMP stack, including thermo-biased cross-attention
- you want to test whether interaction-level thermodynamic bias helps on top of TIMP

Key properties:

- everything from `paper_config_timp.yaml`
- `use_thermo_cross_attention=true`
- `thermo_cross_attention_beta_init=0.1`

Trade-off:

- richest maintained TIMP path
- adds one more interaction-time inductive bias beyond the encoder itself

### `paper_config_tuned_explicit_h_small.yaml`

Use this when:

- you want the tuned TGNN baseline with explicit hydrogens for small molecules
- you are testing whether water/simple-solvent graph topology is limiting
  aqueous predictions

Key properties:

- `explicit_h_small_molecules=true`
- `explicit_h_max_heavy_atoms=3`
- water changes from a one-node self-loop graph to a 3-node O-H graph
- node and edge feature dimensions are unchanged, so the model architecture does
  not need shape changes

Use `paper_config_directgnn_tuned_explicit_h_small.yaml` as the matched
DirectGNN control for the same representation ablation. If you want the
combined "explicit H + RDKit descriptors" variant, use
`paper_config_tuned_tgnn_descriptors_explicit_h_small.yaml` with
`paper_config_directgnn_descriptors_explicit_h_small.yaml`.

### `paper_config_hansen_contrastive.yaml`

Use this when:

- you want the TIMP backbone plus explicit representation-level Hansen-distance
  regularization
- you want molecular, channel, and pair embeddings to reflect measured or
  pseudo-Hansen structure
- you are running channel-analysis follow-up work rather than the default
  headline benchmark

Key properties:

- everything from `paper_config_timp.yaml`
- `use_hansen_contrastive=true`
- `use_pseudo_hansen=true`
- explicit `hansen_contrastive_mol`, `hansen_contrastive_channel`, and
  `hansen_contrastive_pair` phase weights

Trade-off:

- strongest TIMP-structure supervision path currently in the repo
- more diagnostic / representation-focused than the maintained default

### `paper_config_tuned_pretrained.yaml`

Use this when:

- you want the tuned TGNN baseline together with Stage 0 pretraining
- you plan to launch training via `--pretrain` or `train_with_pretrain.py`

Important note:

- Stage 0 is activated by the CLI, not by the YAML alone
- the maintained runtime surfaces are `scripts/training/train.py --pretrain`,
  `--pretrain-checkpoint`, and `scripts/training/train_with_pretrain.py`

### `paper_config_tuned_pretrained_descriptors.yaml`

Use this when:

- you want Stage 0 plus TGNN descriptor augmentation

Key properties:

- `use_descriptor_augmentation=true`
- intended for `--pretrain` / `--pretrain-checkpoint` workflows
- useful when Stage 0 and pair-level descriptor fusion are being tested
  together against the same downstream scaffold split

### `paper_config_tuned_entropy_fusion.yaml`

Use this when:

- you want to test the thermodynamic identity `T_m = dH_fus / dS_fus`
  directly in the crystal branch
- you want `FusionHead` to predict `dH_fus` and `dS_fus` rather than
  independent `T_m` and `dH_fus`
- you are running a controlled physics-bottleneck ablation, not changing the
  maintained default

Key properties:

- starts from `paper_config_tuned.yaml`
- `fusion_output_mode="entropy_coupled"`
- `fusion_entropy_min=20`, `fusion_entropy_max=150`
- `use_walden_check=true`

Trade-off:

- enforces a physically coupled crystal representation
- current processed scaffold split has dense `T_m` labels but sparse
  `dH_fus` labels, so this is a regularization experiment rather than a
  substitute for collecting more fusion-enthalpy supervision

### `paper_config_gc_priors.yaml`

Use this when:

- you want TGNN with crystal GC priors
- you want to test whether better `T_m` / `dH_fus` anchoring helps
- you specifically care about crystal-property factorization quality

Key properties:

- `use_gc_priors_crystal=true`
- zero-initialized residual crystal heads
- `gc_prior_residual_freeze_epochs=5`
- calibrated `T_m_gc` prior during training

Trade-off:

- stronger inductive bias around the crystal branch
- more assumptions about prior quality

### `paper_config_no_bridge.yaml`

Use this when:

- you want to remove the bridge regularizer while keeping the rest of tuned TGNN
- you suspect the bridge term is constraining the solver path too aggressively

Key properties:

- `bridge_loss_weight=0.0`
- phase-level `bridge` weights explicitly set to `0.0`
- `use_walden_check=true`

Trade-off:

- less solver-parameter coupling pressure
- still keeps Walden consistency as a soft physics regularizer

### `paper_config_combined.yaml`

Use this when:

- you want the strongest maintained TGNN variant in terms of added structure
- you want GC priors plus no bridge plus oracle-injection capability

Key properties:

- `use_gc_priors_crystal=true`
- `use_oracle_injection=true`
- bridge disabled
- Walden enabled

Important note:

- the medium-budget architecture-comparison runner derives a no-oracle training
  variant from this config, because that benchmark is intended to isolate
  architectural changes rather than oracle-assisted training

### `paper_config_oracle.yaml`

Use this when:

- you want to study whether the TGNN bottleneck is mainly limited by missing
  crystal labels
- you want a controlled oracle-injection training experiment

Key properties:

- `use_oracle_injection=true`
- `oracle_injection_prob=1.0` at config level

Trade-off:

- useful for diagnosis
- not a standard deployment or benchmark setting

### `paper_config_no_bridge_no_walden.yaml`

Use this when:

- you want the most weakly regularized maintained TGNN variant
- you want to isolate the role of bridge and Walden together

Key properties:

- bridge disabled
- Walden disabled

Trade-off:

- most freedom for the model
- least explicit soft-physics guidance outside the solver

### `paper_config_split_late.yaml`

Use this when:

- you want the maintained encoder-role ablation
- you want to compare late role-specific GNN blocks against the default shared
  residual encoder

Key property:

- `encoder_role_mode="split_late"`

This is mainly an architectural ablation, not the default production config.

### `paper_config_tuned_interaction_rescue.yaml`

Use this when:

- you suspect the physics bottleneck is under-training the interaction block
- you want a train-only auxiliary direct `ln(x2)` head on the pair
  representation
- you plan to inspect gradient-flow diagnostics rather than report a new
  default benchmark

Key properties:

- tuned TGNN baseline plus `use_aux_direct_sol_loss=true`
- `aux_direct_sol` is active in Phases 2 and 3
- `detach_crystal_from_encoder=true`

Trade-off:

- useful for diagnosing weak interaction gradients without removing the solver
- intentionally not the default maintained comparison config

## Maintained DirectGNN Configs

### `paper_config_directgnn_tuned.yaml`

Use this when:

- you want the matched no-physics baseline
- you need the fairest direct competitor to TGNN-Solv

Key properties:

- flat direct `ln(x2)` training schedule
- shared-residual encoder
- cross-attention interaction stack
- no descriptor augmentation

### `paper_config_directgnn_descriptors.yaml`

Use this when:

- you want to test whether hand-crafted chemistry closes the gap
- you want the strongest maintained in-repo non-physics baseline

Key properties:

- `use_descriptor_augmentation=true`
- full RDKit descriptor vectors for both molecules
- train-set descriptor normalization stored in the checkpoint

Trade-off:

- stronger baseline
- less pure as a "graph-only" comparison

This is also the strongest maintained DirectGNN family for:

- DirectGNN uncertainty experiments
- calibration studies without the physics bottleneck
- adapter-based benchmark comparisons against descriptor-heavy custom models

## Legacy / Research Starting Points

### `paper_config.yaml`

Use this when:

- you want the original broad paper-style TGNN config
- you want compatibility with the older default workflow

Important note:

- this file is still maintained, but it is not the best current architecture
  baseline for comparisons

### `paper_config_uniquac.yaml` and `paper_config_wilson.yaml`

Use these when:

- you are explicitly comparing activity models
- you are doing solver-parameterization research

These are research extensions, not the main maintained benchmark configs.

### `small_debug.yaml`

Use this when:

- you want a cheap smoke test
- you need to verify wiring, logging, or hardware

Do not use it for architectural conclusions.

## Fast Selection Table

| Goal | Recommended config |
| --- | --- |
| current maintained TGNN baseline | `paper_config_tuned.yaml` |
| tuned TGNN + descriptors | `paper_config_tuned_tgnn_descriptors.yaml` |
| tuned TGNN + stronger regularization | `paper_config_tuned_regularized.yaml` |
| tuned TGNN + GPS encoder | `paper_config_tuned_gps.yaml` |
| tuned TGNN + TIMP encoder | `paper_config_timp.yaml` |
| tuned TGNN + TIMP + thermo cross-attn | `paper_config_timp_full.yaml` |
| TIMP + Hansen-contrastive regularization | `paper_config_hansen_contrastive.yaml` |
| tuned TGNN + Stage 0 pretraining | `paper_config_tuned_pretrained.yaml` |
| TGNN with crystal priors | `paper_config_gc_priors.yaml` |
| TGNN without bridge | `paper_config_no_bridge.yaml` |
| strongest structured TGNN variant | `paper_config_combined.yaml` |
| TGNN interaction-gradient rescue | `paper_config_tuned_interaction_rescue.yaml` |
| matched no-physics baseline | `paper_config_directgnn_tuned.yaml` |
| strongest in-repo non-physics baseline | `paper_config_directgnn_descriptors.yaml` |
| oracle diagnosis | `paper_config_oracle.yaml` |
| fast wiring test | `small_debug.yaml` |

## Common Choice Patterns

### I want the fairest TGNN vs DirectGNN comparison

Use:

- `paper_config_tuned.yaml`
- `paper_config_directgnn_tuned.yaml`

### I want to know whether crystal priors help

Compare:

- `paper_config_tuned.yaml`
- `paper_config_gc_priors.yaml`

### I want to know whether the bridge term is hurting

Compare:

- `paper_config_tuned.yaml`
- `paper_config_no_bridge.yaml`
- optionally `paper_config_no_bridge_no_walden.yaml`

### I want to know whether descriptors solve the problem without physics

Compare:

- `paper_config_directgnn_tuned.yaml`
- `paper_config_directgnn_descriptors.yaml`
- optionally RF descriptor baselines

### I want to test thermodynamics-informed message passing before changing the solver

Compare:

- `paper_config_tuned.yaml`
- `paper_config_timp.yaml`
- optionally `paper_config_timp_full.yaml`

### I want to know whether TIMP channels align better with Hansen structure

Compare:

- `paper_config_timp.yaml`
- `paper_config_hansen_contrastive.yaml`

### I want to diagnose weak interaction gradients without deleting the solver

Use:

- `paper_config_tuned_interaction_rescue.yaml`
- `scripts/analysis/diagnose_gradient_flow.py`

## Output Sidecars and Provenance

Both maintained training entry points now emit sidecars next to the
checkpoint:

- `<checkpoint>.manifest.json`
- `<checkpoint>.model_card.json`

That applies regardless of which config file you pick. The main difference is
what the sidecar says about the resulting model family and supported capability
surface:

- TGNN configs
  - solver-aware interpretation
  - physics diagnostics
  - thermodynamic stress evaluation
- DirectGNN configs
  - direct uncertainty and calibration paths
  - no synthetic solver-term reporting

## Related Pages

- [Training](training.md)
- [Baselines](baselines.md)
- [Results](results.md)
- [Experiments & Benchmarks](experiments.md)
