# SPEC — Frontier experiments (confession → instrument)

Date: 2026-07-16. Author thread: sigma-grounded-cosmosac.
Successor to the length-cut pass. Turns the paper's *frame* (schematic Fig 13, the
oracle-swap as a single point, the Fig 9 null) into *measured instruments*.

Two experiments. **A (spine)** is the load-bearing claim; **B (salvage)** is a
sub-result that rides A's synthetic machinery. Ordering: build A first, cheapest
anchor first.

Verified premises this rests on (workflow `wmwz40sov`, 2026-07-16):
- σ-head and crystal head read the **pre-interaction, solute-only** embedding
  `g_sol_pre` (V1/V2 = FALSE, adversarially confirmed). ẑ_solute is
  solvent-independent **by construction**. There is no solvent-conditional
  compensation channel. → the "illegal channel" program is dead; A and B do not
  depend on it.
- The n=44 §6.3 numbers are a well-defined per-solute quantity (V3 = TRUE); the
  53%/73%/3.3× story stands unchanged.
- pKa arm is genuinely partner-free (V6 = TRUE): a clean second closure for A.

---

## Experiment A — the physicality–accuracy frontier; slope = misspecification

### Claim
In a fixed-closure composed predictor `ŷ = g(ẑ)`, sweeping the latent-supervision
weight λ (how hard ẑ is pinned toward the physical reference z*) traces a curve in

    (latent physicality  ‖ẑ − z*‖ ,  task error  MAE).

The **magnitude of that curve's slope**, `S := |d MAE / d‖ẑ−z*‖|`, is a measure of
closure misspecification:

- **well-specified closure ⇒ S = 0**: making ẑ physical costs no accuracy
  (physicality and accuracy are aligned; no trade-off).
- **misspecified closure ⇒ S > 0**, growing with misspecification: forcing ẑ toward
  the physical z* removes the head's ability to compensate g's error, so accuracy
  degrades.

The oracle substitution the current paper headlines is the **λ → ∞ endpoint** of this
curve — one point of a law. This is the "confession → instrument" conversion: the
reader gets a procedure (sweep supervision, read the slope) that diagnoses *their*
closure, needing an external latent reference only to fix the physicality axis.

### Falsifiable null
`S = 0` at a correct closure. If S > 0 even at a well-specified closure, the
slope-as-misspecification reading is wrong. Reported per anchor.

### Three anchors (cheap → expensive)

**A1 — synthetic (CPU, now).** `scripts/analysis/run_physicality_frontier.py`.
Reuses the dial's teacher families (linear, monotone-nonlinear, kinetics-exp,
pde-field) and misspecification shapes. Adds what the dial lacks: a **learned latent**
`ẑ = h_θ(x)` (a shared MLP, so it cannot compensate per-sample — only systematically)
trained through the **fixed** misspecified closure `g_F` with

    L(θ) = mean (m − g_F(ẑ))²  +  λ · mean‖ẑ − z*‖².

Sweep (F, λ) grid × families × shapes. For each F, fit S = slope of MAE vs
physicality across λ. **Predict S(F=1) ≈ 0, S increasing as F falls.** Output: the
frontier curves + S(F). This is the clean law with a controllable null (F is the
knob, S(1)=0 is checkable).

**A2 — pKa / Hammett (CPU, now).** Extend
`scripts/experiments/run_pka_trained_comparison.py`. The physics arm currently learns
σ̂ from the pKa loss alone. Add a supervision term `λ·MSE(σ̂, g.sigma)` (true Hammett
σ is already on every graph) and sweep λ. Measure `(mean|σ̂−σ|, pKa MAE)` **stratified**:
meta/para (Hammett LFER well-specified) vs ortho (steric/proximity → misspecified).
**Predict S ≈ 0 in meta/para, S > 0 in ortho.** A real-data anchor with a natural
fidelity contrast built into the chemistry, no GPU.

**A3 — solubility / COSMO-SAC (GPU, later).** Sweep the `sigma_profile` loss weight
(per-phase loss weight, `--set`-able on `train.py`) over ≈3 values. Per λ, retrain,
then measure `rel = ‖σ̂−σ‖/‖σ‖` (row-mean norm ratio, exactly
`run_compensation_surrogate.py`'s a1/a2 metric) and test `ln x2` MAE on the matched
rows. Three points suffice: λ=0 (free), λ=warmup (the 33%-off grounded point), λ→∞
(= the oracle swap, MAE 2.25, already in hand). Places the deployed system on the
curve; S > 0 quantifies COSMO-SAC-2002 misspecification in the same units as A1/A2.
Cost: 2 new training runs (the 3rd point exists) on the L4.

### Deliverable
Fig 13 stops being a schematic. It becomes: three measured frontier curves (synthetic
sweep of F, pKa meta/para vs ortho, solubility) on one (physicality, error) plane, each
annotated with its slope S. The oracle-swap becomes the labelled λ→∞ endpoint. The
"physics tax" gets a per-system misspecification number.

---

## Experiment B — Fig 9 is a distribution-mismatch artifact, not a power failure

### Claim
The compensating drift `δ_X = ẑ_X − z*_X` is the per-molecule first-order closure
compensation **averaged over the training partner distribution** D_train:

    δ_X  ≈  E_{S ~ D_train} [ J⁺ (m_{X,S} − g(z*_X, z*_S)) ],   J = ∂g/∂z_X.

Fig 9 found median cosine −0.00 because it probed `J⁺(m−g)` on a **single pair from a
different distribution** — the VT-2005-matched window D_match (n=60, 298 K), not
D_train (BigSolDB, many partners per molecule). The drift was optimised under D_train;
the residual was sampled once from D_match ≠ D_train, so zero alignment follows
**without any appeal to sample size**. (The "1 pair ⇒ average is that pair" objection
is exactly why this must be stated as a distribution mismatch, not an averaging fix.)

### Why synthetic-only
On real data J is the autograd Jacobian of the COSMO-SAC fixed point, already
documented as numerically unstable (‖∂g/∂σ_solvent‖ ∼ 10¹⁵ at infinite dilution;
Fig 9 footnote). Only on a synthetic teacher is J known analytically **and** D_train
controllable.

### Setup
Pair teacher `m_{X,S} = T(z*_X, z*_S) + noise`; fixed misspecified closure `g_F` with
known `J = ∂g/∂z_X`; head learns **one** ẑ_X per molecule over all its D_train
partners; drift `δ_X = ẑ_X − z*_X`. Shares A1's misspecification-shape and closure
machinery; adds a partner axis and a two-latent teacher.

### Two numbers, one rig
1. `cos( δ_X , E_{S~D_train}[ J⁺(m−g) ] )` → **high** (the resolution).
2. `cos( δ_X , J⁺(m_{X,S0}−g) )`, single `S0 ~ D_match ≠ D_train` → **low = reproduces
   Fig 9**.

Same engine yields the null *and* its resolution: the *wrong* object gives exactly
Fig 9, the *right* object aligns.

### Clean null (stated up front, to not repeat the circular-averaging error)
If δ_X does not align with the D_train-averaged J⁺ either, B is dead and Fig 9 stays an
honest underpower result. Reported either way.

### Scope / ranking
Sub-result of the synthetic track, strictly synthetic (J known). Converts an existing
negative (Fig 9, "not enough power") into a positive ("measured the wrong object"). One
sentence of distribution-mismatch reasoning goes in-paper, pre-empting the referee.

---

## Build order
1. A1 synthetic frontier — `run_physicality_frontier.py` (this turn).
2. A2 pKa λ-sweep — extend the pKa comparison rig (CPU).
3. B synthetic distribution-mismatch — new pair-teacher component (synthetic).
4. A3 solubility 2-point sweep — GPU, on the L4, folded with the surrogate-seeds run.
