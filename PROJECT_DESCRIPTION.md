# TGNN-Solv: Full Project Description For Agents

Last updated: 2026-04-18

This file is an orientation document for coding and research agents. It explains
what the project is, why the architecture exists, what mathematical assumptions
it uses, how the code is organized conceptually, and what is currently known
empirically.

Operational memory still lives in `PROJECT_MEMORY.md`. If this file, `main.tex`,
presentation assets, and fresh result bundles disagree, use the following order:

1. Reproducible artifacts under `results/`, `logs/`, and generated summaries.
2. Maintained source code and configs.
3. `PROJECT_MEMORY.md`.
4. This file.
5. Older narrative files such as `main.tex` and presentation text.

This file was assembled from `main.tex`, `presentation/seminar_talk.tex`,
`presentation/talk_text*.md`, and current project memory.

## 1. Project In One Paragraph

TGNN-Solv is a physics-informed graph neural network for predicting solid-liquid
equilibrium solubility. The target is the natural logarithm of the solute mole
fraction in a saturated solution, `ln(x2)`, for a row defined by
`(solute, solvent, temperature)`. The central research question is not simply
"can a neural network predict solubility", but whether an explicit thermodynamic
bottleneck helps relative to the same graph backbone trained directly on
`ln(x2)`. The controlled comparison is therefore `TGNN-Solv` versus
`DirectGNN`: same molecular graph encoder and pair-interaction stack, but TGNN
predicts physical parameters and solves the SLE equation, while DirectGNN emits
`ln(x2)` directly.

## 2. Practical Motivation

Solubility controls crystallization, extraction, purification, solvent selection,
anti-solvent design, reaction medium choice, and early pharmaceutical screening.
For a library of solutes, solvents, and temperatures, exhaustive experimental
measurement quickly becomes combinatorial:

```text
N_solutes x N_solvents x N_temperatures -> many thousands to millions of points
```

The model is intended as a fast screening and ranking tool. It should answer
questions like:

- Which solvent gives the highest solubility for a compound?
- How does solubility change with temperature?
- Which anti-solvent should be used for crystallization?
- Is a candidate likely to be practically insoluble in aqueous conditions?

The target scale is logarithmic because mole fractions span many orders of
magnitude. Typical values are roughly `ln(x2) in [-25, 0]`.

Interpretation of MAE in `ln(x2)`:

```text
MAE 0.5 -> multiplicative error exp(0.5) = 1.65
MAE 1.0 -> multiplicative error exp(1.0) = 2.72
MAE 2.0 -> multiplicative error exp(2.0) = 7.39
```

## 3. Data Model

One supervised SLE row is:

```text
solute_smiles, solvent_smiles, T, ln_x2
```

Optional auxiliary labels can include:

- `T_m`: melting point of the solute.
- `dH_fus`: enthalpy of fusion of the solute.
- `dCp_fus`: heat-capacity difference on fusion, usually unavailable.
- Hansen parameters: `(delta_d, delta_p, delta_h)`.
- IDAC / gamma-infinity: `ln(gamma_inf)` for infinite-dilution activity.
- group-contribution priors for crystal or activity terms.

Current maintained corpus facts from `PROJECT_MEMORY.md`:

- Full merged frame: `120,197` rows.
- Solubility-supervised subset: `108,287` rows.
- Solubility-supervised unique pairs: `12,129` `(solute, solvent)` pairs.
- Solvents: `212`.
- Median temperatures per pair: `9`.
- Water is intentionally kept in the supervised subset.
- Water rows: `6,524` supervised rows.

Important split families:

- `solute_scaffold`: canonical maintained split for structural generalization.
- `solute`: unseen solute generalization.
- `solvent`: unseen solvent generalization.
- `pair_random`: unseen pair, but both components may be seen.
- `row_random`: row-level random split; leakage-friendly for this corpus.
- temperature interpolation/extrapolation splits for same-pair temperature tests.

The main difficulty is not generic pair novelty. It is new-solute / new-scaffold
generalization.

## 4. Component Convention

Throughout the thermodynamic derivation:

- Component `1` is the solvent.
- Component `2` is the solid solute.
- `x_i` is the mole fraction of component `i`.
- `x1 + x2 = 1`.
- The target is `y = ln(x2)`.

NRTL indices are asymmetric:

- `tau_12` describes an effective interaction direction associated with solvent
  around solute.
- `tau_21` describes the reverse local-composition direction.
- They should not be assumed equal.

## 5. Thermodynamic Foundation

### 5.1 Chemical Potential And SLE Equilibrium

For component `i` in a liquid mixture:

```math
mu_i^liq(T, P, x) = mu_i^{liq,0}(T, P) + R T ln(gamma_i x_i)
```

For a pure solid solute:

```math
mu_2^sol(T, P) = mu_2^{sol,0}(T, P)
```

At solid-liquid equilibrium:

```math
mu_2^{sol,0}(T) = mu_2^{liq,0}(T) + R T ln(gamma_2 x_2)
```

Define the Gibbs free energy of fusion:

```math
Delta G_fus(T) = mu_2^{liq,0}(T) - mu_2^{sol,0}(T)
```

Then the master SLE equation is:

```math
ln x_2 = - Delta G_fus(T) / (R T) - ln gamma_2
```

This is the central equation of the project.

### 5.2 Structural Decomposition

Define:

```math
Phi(T) = Delta G_fus(T) / (R T)
```

Then:

```math
ln x_2 = -Phi(T) - ln gamma_2
```

Interpretation:

- `-Phi(T)` is the crystal / ideal-solubility contribution.
- `-ln gamma_2` is the solution nonideality contribution.

The crystal term depends on pure-solute properties:

- `T_m`
- `Delta H_fus`
- optionally `Delta C_p^fus`
- temperature `T`

The activity term depends on the solute-solvent pair and composition.

### 5.3 Fusion Free Energy

With constant `Delta C_p^fus`:

```math
Phi(T) = Delta H_fus/R * (1/T - 1/T_m)
       - Delta C_p^fus/R * [(T_m/T - 1) - ln(T_m/T)]
```

The default historical approximation is `Delta C_p^fus = 0`, giving:

```math
Phi(T) = Delta H_fus/R * (1/T - 1/T_m)
```

This is the Hildebrand / Schroeder-van Laar style simplification. It is simple
and identifiable, but it can create systematic errors. For paracetamol-like
conditions, omitting `Delta C_p` can shift ideal `ln(x2)` by about `0.8`, which
is comparable to the target accuracy of the whole model.

### 5.4 Ideal Solubility

If `gamma_2 = 1`:

```math
ln x_2^ideal = -Phi(T)
```

Properties:

- At `T = T_m`, `Phi = 0`, so `x2^ideal = 1`.
- At low temperature, `Phi -> +infinity`, so `x2^ideal -> 0`.
- For positive enthalpy of fusion, ideal solubility increases with temperature.

## 6. Activity Model: NRTL

TGNN-Solv currently uses NRTL as the default activity-coefficient model.

NRTL defines:

```math
G_12 = exp(-alpha tau_12)
G_21 = exp(-alpha tau_21)
```

and for the solute activity coefficient:

```math
ln gamma_2 = x_1^2 [
  tau_12 * (G_12 / (x_2 + x_1 G_12))^2
  + tau_21 G_21 / (x_1 + x_2 G_21)^2
]
```

At infinite dilution (`x2 -> 0`, `x1 -> 1`):

```math
ln gamma_2^infty = tau_12 + tau_21 exp(-alpha tau_21)
```

This analytic infinite-dilution formula is used for IDAC supervision.

The non-randomness parameter is constrained to a physical range:

```math
alpha in [0.1, 0.6]
```

### Temperature Dependence Of NRTL Parameters

The maintained `nrtl_tau_mode` is `ref_invT`:

```math
tau_12(T) = tau_12^ref + beta_12 * (1/T - 1/T_ref)
tau_21(T) = tau_21^ref + beta_21 * (1/T - 1/T_ref)
```

This is physically motivated because if the underlying interaction energy is
roughly constant, `tau = Delta g / (R T)` is approximately linear in `1/T`.

## 7. SLE Solver

Because `gamma_2` depends on `x2`, the master equation is implicit:

```math
x_2 = exp(-Phi(T) - ln gamma_2(x_2))
```

Equivalently:

```math
F(x_2) = ln x_2 + Phi(T) + ln gamma_2(x_2) = 0
```

The solver treats this as a fixed-point problem:

```math
x_2^(0) = exp(-Phi)
x_2^(k+1) = lambda * exp(-Phi - ln gamma_2(x_2^k))
          + (1 - lambda) * x_2^k
```

where `lambda` is damping. The output is:

```math
ln x_2^physics = ln x_2^(N_iter)
```

The solver has no trainable parameters. It is a deterministic layer receiving
predicted physical parameters.

### Implicit Differentiation

The project uses a custom autograd path for the solver rather than backpropagating
through every fixed-point iteration. For parameters `theta`:

```math
d ln x_2^* / d theta
= - partial(Phi + ln gamma_2)/partial theta / (1 + x_2^* eta)
```

where:

```math
eta = partial ln gamma_2 / partial x_2 evaluated at x_2^*
```

This is one of the main mathematical justifications for the differentiable
physics layer. It avoids growing the computation graph with solver iterations
and exposes where gradients can become unstable: when `1 + x_2^* eta` is small.

## 8. Model Architecture

### 8.1 High-Level Forward Path

The maintained TGNN-Solv forward path is:

```text
solute graph, solvent graph, T
  -> graph encoder
  -> optional auxiliary molecular heads
  -> solute-solvent interaction stack
  -> physics-aware readout
  -> pair representation
  -> crystal heads and NRTL head
  -> SLE solver
  -> bounded physics-preserving correction
  -> ln_x2_final
```

DirectGNN keeps the same graph encoder, interaction stack, and readout, but
replaces the physics heads and solver with a direct MLP:

```math
ln x_2 = MLP(g_pair, T, optional descriptors)
```

This makes DirectGNN the critical controlled baseline.

### 8.2 Graph Representation

Molecules are represented as graphs:

- nodes are atoms;
- edges are chemical bonds;
- node features include atom type, valence, aromaticity, charge-like features,
  hydrogen count, and related RDKit-derived atom descriptors;
- edge features include bond type and optional physical edge features.

Supported encoder variants:

- `mpnn`: standard message-passing GNN.
- `gps`: hybrid local message passing plus global attention.
- `timp`: thermodynamically-informed message passing.

Water is a special graph case. Heavy-atom-only water is a one-node graph (`O`),
so the project now supports `explicit_h_small_molecules`, which turns water into
an explicit O-H graph for small molecules. This helps message passing and TIMP
channels operate on water and other small solvents.

### 8.3 MPNN Message Passing

A generic message-passing layer updates each atom using messages from neighbors:

```math
h_i^(l+1) = Update(h_i^l, sum_{j in N(i)} Message(h_i^l, h_j^l, e_ij))
```

After several layers, atom states are pooled into molecular states.

### 8.4 TIMP: Thermodynamically-Informed Message Passing

TIMP is an encoder modification motivated by the fact that solubility depends on
different physical interaction types:

- dispersive / polarizable contacts;
- polar and electrostatic contacts;
- hydrogen-bond and association effects.

TIMP splits message passing into physical channels. A simplified message form is:

```math
m_ij = phi_disp(...) * sqrt(alpha_i alpha_j)
     + phi_polar(...) * softplus(delta q_i delta q_j)
```

where `alpha_i` is a polarizability-like quantity and `delta q_i` is a partial
charge-like feature. TIMP can also use extra physical edge features:

- electronegativity difference;
- van der Waals radius difference;
- bond polarity;
- hydrogen-bond capability.

The intended role of TIMP is not to change SLE thermodynamics. It improves the
representation fed into the NRTL and pair-interaction heads.

Hansen supervision can be used to prevent channel collapse:

- dispersive channel should encode `delta_d`-like information;
- polar channel should encode `delta_p` and `delta_h`-like information.

### 8.5 Crystal / Fusion Head

The crystal head predicts pure-solute properties before interaction with the
solvent:

```math
T_m = 100 + 600 * sigmoid(MLP_Tm(g_solute_pre))
Delta H_fus = S_H * softplus(MLP_H(g_solute_pre))
```

Thus:

- `T_m in [100, 700] K`.
- `Delta H_fus > 0`.

A newer optional mode is entropy-coupled fusion:

```math
T_m = Delta H_fus / Delta S_fus
```

This enforces the thermodynamic identity relating enthalpy, entropy, and melting
point. The entropy is constrained to a physically plausible Walden-like range.

### 8.6 Hansen Head

The Hansen head predicts molecular parameters:

```math
(delta_d, delta_p, delta_h) = MLP_Hansen(g_mol_pre)
```

These are used as auxiliary supervision and as compatibility structure, not as
the final solubility model.

The project now also contains an explicit Hansen delta objective:

```math
Delta delta_pred = Hansen(solute) - Hansen(solvent)
Delta delta_true = Hansen_eff(solute) - Hansen_eff(solvent)
```

This targets pair compatibility rather than only isolated molecule properties.

### 8.7 Solute-Solvent Interaction

Default interaction is cross-attention:

```math
Attn(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V
```

Solute atoms attend to solvent atoms and vice versa. This is intended to model
which atom-level contacts matter for the pair.

### 8.8 Pair Representation

After interaction and readout, pair representation is formed as:

```math
g_pair = MLP([g_sol, g_slv, g_sol * g_slv, |g_sol - g_slv|])
```

This combines:

- solute identity;
- solvent identity;
- compatibility / interaction product;
- difference / mismatch vector.

Optional descriptor augmentation can concatenate RDKit descriptors for both
molecules and pairwise descriptor interactions.

### 8.9 NRTL Head

The NRTL head receives `g_pair` and temperature information and predicts:

- `tau_12^ref`, `beta_12`;
- `tau_21^ref`, `beta_21`;
- `alpha`.

These are converted to temperature-dependent NRTL parameters and passed to the
SLE solver.

### 8.10 Adaptive Physics Correction

The hard SLE+NRTL physics path is approximate. TGNN-Solv therefore includes a
bounded correction mechanism that changes physical parameters, re-solves SLE,
and blends the result:

```math
T_m' = T_m + delta T_m
Delta H' = Delta H + delta H
tau_12' = tau_12 + delta tau_12
tau_21' = tau_21 + delta tau_21
ln x_2^proposal = SLE_Solve(T_m', Delta H', tau_12', tau_21', alpha, T)
ln x_2^final = ln x_2^physics + (1 - w) * clip(ln x_2^proposal - ln x_2^physics)
```

The correction is bounded, gated, and still physics-preserving because it works
by changing physical parameters and re-solving the equation rather than using an
arbitrary residual MLP directly on `ln(x2)`.

## 9. DirectGNN Baseline

DirectGNN is not a weaker baseline. It is the controlled answer to:

```text
What happens if we remove the physics bottleneck but keep the same learned graph
and pair representation machinery?
```

DirectGNN uses:

- same encoder;
- same interaction stack;
- same readout;
- same optional descriptor augmentation;
- thermometer temperature encoding;
- direct MLP output to `ln(x2)`.

The TGNN-vs-DirectGNN gap is the best estimate of the cost or benefit of the
explicit physics bottleneck under comparable representation capacity.

## 10. Training Scheme

### 10.1 Stage 0 Encoder Pretraining

Optional Stage 0 pretraining trains the graph encoder and readout before the
main solubility task.

Maintained tasks:

1. Masked subgraph / atom-feature recovery.
2. Bond type prediction.
3. RDKit descriptor prediction.
4. Graph contrastive learning on augmented views.
5. Optional pairwise solubility-contrastive pretraining.

The fifth task was added because solubility is a pair property. Single-molecule
pretraining on ZINC250k improves isolated molecular representations but does not
teach thermodynamic compatibility between solute and solvent.

The pairwise contrastive artifact contains rows:

```text
solute_A, solute_B, solvent, label, weight
```

Labels are built within a shared solvent:

- positive: structurally similar and similar mean `ln(x2)`;
- hard negative: structurally similar but large solubility gap;
- easy negative: structurally dissimilar and large solubility gap.

### 10.2 Main Three-Phase Curriculum

Canonical budget is `50 / 200 / 50` epochs.

Phase 1: auxiliary property pretraining.

- Solubility loss off.
- Train crystal, Hansen, and related auxiliary heads.
- Goal: give the solver reasonable physical inputs before full SLE training.

Phase 2: full SLE training.

- Main `ln(x2)` loss active.
- Auxiliary losses still active but downweighted.
- NRTL and solver path trained.
- Correction path may be unfrozen after a configured delay.

Phase 3: low-learning-rate fine-tuning.

- Lower LR and stronger regularization.
- More emphasis on monotonicity, van't Hoff consistency, and limiting correction
  magnitude.
- Goal is not to relearn, but to stabilize the physical solution.

### 10.3 Loss Components

Main loss:

```math
L_sol = mean Huber(ln x_2^pred - ln x_2^true)
```

Auxiliary and regularization losses include:

- `T_m` regression.
- `Delta H_fus` regression.
- Hansen regression.
- Hansen delta compatibility.
- IDAC / `ln gamma_inf` supervision.
- monotonicity in temperature.
- pair-temperature rank consistency.
- van't Hoff local consistency.
- residual/correction magnitude regularization.
- physics-preference gate regularization.
- NRTL tau regularization.
- optional bridge losses, now treated carefully because Regular Solution priors
  can be counterproductive for associating systems.

Current IDAC supervision is passed as a separate auxiliary stream, not by
appending gamma-only rows into the main SLE CSV. This matters because IDAC is not
solubility; it is an auxiliary activity-coefficient target.

### 10.4 Pair-Aware Temperature Batching

For multi-temperature pairs, the loader can place several temperatures from the
same `(solute, solvent)` pair into the same batch. This enables:

- rank consistency over temperature;
- local van't Hoff consistency;
- pair-temperature delta losses;
- temperature interpolation/extrapolation diagnostics.

## 11. Mathematical Identifiability

The inverse problem is underdetermined.

For one observation at one temperature:

```math
ln x_2 = -Phi(T; T_m, Delta H, Delta C_p)
         - ln gamma_2(x_2; tau_12, tau_21, alpha)
```

One scalar equation constrains many latent parameters. For a parameter vector
with `p` degrees of freedom, the solution set is typically a `(p - 1)`-dimensional
manifold. Many different physical parameter combinations can reproduce the same
observed `ln(x2)`.

Multi-temperature data helps but does not fully solve the problem because:

- temperature contributions can be collinear;
- `Delta H/T` and NRTL `beta/T` terms can mimic each other;
- closely spaced temperatures produce poorly conditioned sensitivity matrices;
- noise in `ln(x2)` causes large uncertainty in inferred physical parameters.

This explains compensatory degeneracy: NRTL can absorb errors in crystal heads,
or crystal heads and NRTL can co-adapt to fit `ln(x2)` without physically correct
factorization.

Important consequence for agents: do not assume a lower solubility MAE means
intermediate physical parameters are correct. Always inspect intermediate
physics and diagnostics.

## 12. Current Empirical State

Current accepted scaffold-split numbers from `PROJECT_MEMORY.md`:

| Model | MAE | R2 | Interpretation |
|---|---:|---:|---|
| DirectGNN | 1.652 | 0.478 | best current MAE |
| RF hybrid | 1.722 | 0.449 | strong descriptor baseline |
| TGNN MPNN | 1.741 | 0.438 | physics path currently behind DirectGNN |

Physics tax:

```text
TGNN MAE - DirectGNN MAE = +0.089
```

Interpretation:

- DirectGNN currently beats the best maintained RF baseline.
- TGNN is close, but the explicit hard physics path currently costs about
  `+0.09 MAE` on scaffold.
- This does not prove physics is useless; it localizes a training/representation
  bottleneck in the current implementation.

External baseline state:

- SolProp native on solute split: `MAE 1.624`, `R2 0.388`.
- DirectGNN on comparable solute setup: `MAE 1.652`, `R2 0.478`.
- DirectGNN has slightly worse MAE but higher R2 than SolProp native.

KNN/modelability diagnostics:

- 1-NN pair Tanimoto on maintained split: `MAE 2.530`, `R2 -0.192`.
- This is much worse than RF and DirectGNN.
- Therefore, poor KNN does not imply the dataset is unusable; learned models
  extract structure that nearest-neighbor lookup does not.

Split difficulty using RF baseline:

| Split | MAE | R2 | Main meaning |
|---|---:|---:|---|
| row_random | 0.166 | 0.987 | leakage-friendly rows |
| pair_random | 0.783 | 0.806 | new pair but seen components |
| solvent | 0.732 | 0.735 | new solvent |
| solute | 1.642 | 0.420 | new solute |
| scaffold | 1.703 | 0.462 | new scaffold plus target shift |

The hardest real problem is structural generalization to new solutes/scaffolds.

## 13. Temperature Extrapolation Findings

Same-pair low-to-high temperature extrapolation revealed a key fact:

| Model | High-T MAE | R2 | Notes |
|---|---:|---:|---|
| pair Van't Hoff | 0.368 | 0.887 | two-parameter pair fit |
| pair linear T | 0.414 | 0.850 | simple pair curve |
| RF(Morgan+T) | 1.290 | 0.658 | weak direction accuracy |
| DirectGNN proxy | 1.619 | 0.283 | poor temperature extrapolation |
| TGNN proxy | 1.945 | 0.060 | worse than DirectGNN in proxy |

This is a central narrative update:

- Physics works when the pair-specific temperature structure is known.
- Current neural models do not yet exploit this structure well enough.
- The most honest near-term target for TGNN is to win on same-pair temperature
  extrapolation, even if scaffold MAE remains close to DirectGNN.

## 14. Known Bottlenecks And Accepted Diagnoses

### 14.1 NRTL Supervision Is The Weakest Link

NRTL parameters are highly influential, but direct supervision is sparse. IDAC
provides a direct auxiliary signal for `ln gamma_inf`, but not independent labels
for each of `tau_12`, `tau_21`, and `alpha`.

Expanded ThermoML/NIST IDAC work has increased the available auxiliary stream
in newer artifacts, but it is still an auxiliary task and does not directly cover
most SLE pairs.

### 14.2 Crystal Head Can Capture The Encoder

`T_m` supervision is much more available than NRTL supervision. This can bias a
shared encoder toward pure-crystal features rather than liquid-phase pair
compatibility. Mitigations under discussion or implementation include:

- detach crystal gradients in phase 2;
- split encoders / adapters for crystal and interaction branches;
- auxiliary direct-solubility head for pair-branch gradient rescue.

### 14.3 Solver Gradients Can Starve Or Destabilize Interaction Learning

The SLE solver routes the main signal through implicit derivatives. If NRTL
parameters are random early in training, gradients can be noisy, weak, or poorly
conditioned. Aux direct heads and IDAC streams help provide more direct signal to
the pair branch.

### 14.4 Bridge Loss Can Be Harmful

Regular Solution bridge constraints are physically appealing but can be wrong for
systems with strong specific interactions, hydrogen bonding, or association.
Bridge losses should be treated as optional and ablated, not assumed beneficial.

### 14.5 `Delta C_p = 0` Can Create Systematic Error

The default crystal term omits heat-capacity effects. This can shift ideal
solubility by `~0.5-1.0` in `ln(x2)` for some high-melting compounds. A future
route is fixed group-contribution `Delta C_p` rather than an unconstrained neural
latent.

## 15. Water And Small-Molecule Graphs

Water is important and cannot be removed casually. It is one of the most common
solvents in the corpus.

Problem:

- SMILES `O` gives one heavy atom and no heavy-atom bonds.
- Standard MPNN message passing degenerates because the node has no real
  neighbors.
- TIMP physical channels also need edges to activate.

Maintained fix:

- `explicit_h_small_molecules=True` adds explicit hydrogens for molecules with
  at most a configured number of heavy atoms.
- Water becomes O-H-H graph with O-H edges.
- This preserves feature dimensions while improving topology.

Tests cover water graph construction and TGNN/TIMP forward passes with water as
solvent.

## 16. Structural Extrapolation Strategy

ZINC250k single-molecule pretraining is useful but insufficient because the
missing signal is pair compatibility:

```text
molecule -> chemical features       is not enough
(molecule A, molecule B) -> compatibility is needed
```

Implemented or planned structural-extrapolation aids:

- pairwise solubility contrastive Stage 0 objective;
- Hansen delta objective;
- expanded IDAC auxiliary stream;
- UNIFAC / group-contribution priors for activity;
- split encoder or branch-specific adapters;
- functional-group tokenization / fragment-level encoder;
- cross-solvent transfer tasks;
- few-shot/meta-learning for pair-specific adaptation.

Current CPU diagnostics show:

- BRICS full fragment coverage of scaffold test is low enough that fragment
  recombination alone is not sufficient.
- Solubility cliffs exist and justify hard-negative contrastive sampling.
- Current UNIFAC coverage is useful but too low to be the only solution.

## 17. Current Implemented Research Extensions

As of 2026-04-18, recent implemented/plumbed extensions include:

- explicit-H small-molecule graphs;
- entropy-coupled fusion mode;
- auxiliary direct solubility head for pair-branch rescue;
- detach crystal from encoder option;
- IDAC auxiliary stream rather than appending gamma-only rows;
- UNIFAC prior and auxiliary stream utilities;
- pairwise solubility contrastive artifact builder;
- optional Stage 0 pairwise compatibility BCE loss;
- Hansen delta compatibility loss;
- structural rescue config tying several of these together.

These are not all fully GPU-benchmarked. Treat them as implemented research
plumbing until result bundles exist.

## 18. Baselines And Benchmark Philosophy

Maintained internal baselines:

- `DirectGNN`: same backbone, no solver.
- RF descriptors.
- RF Morgan.
- RF hybrid.
- Ideal SLE without learning.
- Wilson and UNIQUAC activity-model variants.

External baselines:

- FastSolv.
- SolProp native retraining.
- Future or optional COSMO-RS/COSMO-SAC benchmark subset.

Evaluation must specify:

- split;
- seed(s);
- budget;
- target scale (`ln_x2` vs `logS`);
- whether water is included;
- whether auxiliary streams are used;
- whether descriptor augmentation is enabled;
- exact checkpoint/config.

## 19. Applications Layer

The application layer is a solubility-first decision layer, not a complete
chemical design platform. It builds on model inference to support:

- solvent screening;
- process temperature optimization;
- anti-solvent crystallization reasoning;
- greener solvent replacement ranking;
- drug developability / BCS-like checks;
- PK-style solubility profile sketches across GI conditions;
- route-level solvent selection support.

These applications rely on predicted `ln(x2)` or temperature scans, plus
uncertainty/applicability-domain checks where available.

## 20. Repository Concept Map

Key files and directories:

- `PROJECT_MEMORY.md`: canonical operational memory.
- `AGENTS.md`: instructions for coding agents.
- `main.tex`: long Russian technical report; rich theory, partly stale results.
- `presentation/seminar_talk.tex`: current seminar slides.
- `presentation/talk_text*.md`: spoken narrative and slide notes.
- `src/tgnn_solv/model.py`: TGNN-Solv and DirectGNN architecture surface.
- `src/tgnn_solv/trainer.py`: three-phase curriculum and resume logic.
- `src/tgnn_solv/loss.py`: multi-component TGNN loss.
- `src/tgnn_solv/pretrain.py`: Stage 0 pretraining.
- `src/tgnn_solv/data/dataset.py`: dataset and graph construction.
- `src/tgnn_solv/features.py`: molecular graph features.
- `src/tgnn_solv/unifac.py`: UNIFAC-related utilities.
- `scripts/training/`: maintained training wrappers.
- `scripts/data/`: data preparation and auxiliary stream builders.
- `scripts/evaluation/`: metrics, benchmarks, extrapolation diagnostics.
- `scripts/analysis/`: research diagnostics.
- `configs/`: experiment configurations.
- `results/`: reproducible outputs and diagnostics.
- `docs/`: user-facing documentation.

## 21. How Agents Should Reason About This Project

When modifying the code or planning experiments:

1. Always identify whether the change targets representation, physics, training,
   data, or evaluation protocol.
2. Do not optimize only scaffold MAE without checking whether the physics path
   remains interpretable.
3. Treat DirectGNN as the primary controlled baseline, not as an unrelated model.
4. Treat RF hybrid as a strong practical baseline.
5. Treat temperature extrapolation as the most physics-sensitive test.
6. Keep IDAC as an auxiliary activity stream, not as SLE rows.
7. Be careful with source drift: `main.tex` has valuable derivations but some
   old empirical numbers are stale.
8. After significant experimental or protocol changes, update `PROJECT_MEMORY.md`.

## 22. Short Current Narrative

The project has not failed, but the original simple hypothesis has become more
specific. DirectGNN currently wins the scaffold MAE comparison by about `0.09`,
so the hard physics bottleneck is not yet a headline accuracy win. However,
physics clearly wins in same-pair temperature extrapolation when pair-specific
Van't Hoff structure is fitted. Therefore the current research goal is to make
TGNN-Solv actually exploit its physics: improve the input to NRTL, give the pair
branch direct supervision, rescue gradient flow, and test the resulting model on
same-pair temperature extrapolation and then structural extrapolation.

The scientific value is the controlled diagnosis: if the physics bottleneck wins
on extrapolation, it justifies the added structure. If it does not, the project
still yields a well-instrumented comparison showing where hard physics can hurt
and which softer physics constraints are more practical.
