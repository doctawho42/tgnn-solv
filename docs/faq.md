# FAQ

## Why doesn't TGNN-Solv predict `ln(x2)` directly?

Because the main research question is whether an explicit thermodynamic
bottleneck helps. TGNN-Solv predicts crystal and interaction parameters first,
passes them through an SLE solver, and only then applies a bounded correction.

If you want the matched direct alternative, use `DirectGNN`.

## What is the main comparison in this repository?

The maintained comparison is:

- `TGNN-Solv`
- `DirectGNN`
- `DirectGNN + descriptors`
- descriptor-centric RF baselines

The key question is whether the explicit physics bottleneck helps relative to
the same backbone trained directly on solubility.

## What is the difference between Stage 0 and Phase 1?

They are not the same thing.

- `Stage 0`
  - optional standalone encoder/readout pretraining from `pretrain.py`
- `Phase 1`
  - the first supervised stage of normal TGNN training on the processed
    solubility split

Stage 0 is optional and not run automatically by `scripts/training/train.py`.

## When should I use `paper_config_tuned.yaml`?

Use it when you want the current maintained TGNN baseline for architecture
comparison on the scaffold split.

## When should I use `DirectGNN + descriptors`?

Use it when you want to test whether hand-crafted chemical descriptors explain
the gap without requiring the TGNN physics bottleneck.

It is the strongest maintained in-repo non-physics baseline.

## What are GC priors?

GC priors are group-contribution-derived crystal-property estimates used to
anchor the crystal branch of TGNN-Solv. In the maintained crystal-GC mode:

- the model starts from calibrated `T_m_gc`, `dH_fus_gc`, and `dCp_fus_gc`
- the network learns bounded residuals around those priors

Use this path when you suspect crystal-property factorization is underconstrained.

## Why isn't OOD detection built into `predict_solubility(...)` automatically?

Because applicability-domain checks are a separate decision layer. The
maintained inference API keeps prediction and OOD scoring decoupled:

- `predict_solubility(...)` returns the model prediction
- `ApplicabilityDomain` estimates whether the query is close enough to training
  support

That makes it easier to:

- use the model without AD when not needed
- swap in stricter or alternative AD policies later

## What does OOD / applicability domain currently mean here?

The maintained implementation combines:

- Mahalanobis distance in latent pair space
- nearest-neighbor Morgan Tanimoto similarity for solute and solvent

It does not currently use leverage in the actual decision path.

## Why are scaffold-split results worse than random or exact-solute splits?

Because `solute_scaffold` is a stricter and more realistic generalization test.
It holds out structural motifs rather than only rows.

If a model looks good on easier splits but degrades strongly on
`solute_scaffold`, that usually means the learned chemistry is not robust
enough yet.

## Are proxy runs enough for architecture decisions?

No. Proxy runs are useful for:

- debugging
- smoke tests
- rough hyperparameter search

But they are not reliable enough for architectural conclusions, especially when
the budget is so small that the models underfit.

## Why does the repo still keep legacy `scripts/*.py` wrappers?

For compatibility:

- tests still import some legacy paths
- `reproduce.sh` still uses them
- older automation can continue to work

The preferred human-facing navigation surface is the grouped layout under:

- `scripts/data/`
- `scripts/training/`
- `scripts/evaluation/`
- `scripts/experiments/`
- `scripts/external/`

## What should I report for TGNN besides MAE / RMSE / `R²`?

For serious TGNN evaluation, also report:

- `T_m` MAE
- `T_m` Pearson `r`
- oracle sensitivity when relevant
- GC-prior `T_m` quality when using GC priors
- NRTL parameter statistics when doing bottleneck analysis

## Is there an official public checkpoint bundle yet?

Not yet. The repository currently documents checkpoint conventions and local
artifact layouts, but it does not yet publish a versioned checkpoint catalog on
the site.

## Where should I start if I am new?

The fastest reading path is:

1. [Quick Start Workflow](getting_started/quick_start.md)
2. [Architecture](architecture.md)
3. [Training](training.md)
4. [Evaluation & Inference](evaluation.md)
5. [Experiments & Benchmarks](experiments.md)

<div class="tgnn-page-nav" markdown="1">

## Related Pages

- [Troubleshooting](troubleshooting.md)
- [Config Cookbook](config_cookbook.md)
- [Results](results.md)
- [Model Zoo](model_zoo.md)

</div>
