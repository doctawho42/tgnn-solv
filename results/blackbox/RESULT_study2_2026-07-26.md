# Black-box Study 2 (temperature structure) — 2026-07-26: **KILL, feeding Study 4**

Instrument: `scripts/experiments/blackbox_study2.py`. Raw: `results/blackbox/study2_2026-07-26.json`.
Same three current-split checkpoints as Study 1a. Zero GPU spend; minutes of CPU.

Slopes are fitted at **fixed (solute, solvent)** across temperature — a slope pooled across
solvents would confound activity differences with temperature.

## The ceiling, measured before any model was touched

The pre-registration asks whether `d(ln x2)/d(1/T)` recovers `−ΔH_fus/R`. The SLE identity says
it cannot do so cleanly:

    d(ln x2)/d(1/T) = −ΔH_fus/R − d(ln γ2)/d(1/T)

so the question is first of all about the **data**, not the model.

| sample | pairs / solutes | corr(empirical slope, −ΔH_fus/R) |
|---|---|---|
| train | 1353 / 151 | **+0.239** |
| held out | 66 / 13 | **−0.125** (permutation p = 0.581) |

The slopes themselves are precisely determined — median \|slope\|/SE = **66.6** held out, 49.4 on
train, and only 1 of 1353 pairs has the wrong sign. This is not a noise problem. **The crystal
enthalpy simply explains about 6% of the variance in the observed van't Hoff slope** (r² from the
train correlation); the activity term's temperature dependence carries the rest.

Consequence: a model reproducing the data exactly would score ≈ +0.24, not 1.0. And on the 13
held-out solutes the data's own ceiling is **indistinguishable from zero**, so the model-side
crystal test is unanswerable on that sample by construction.

## Model results (three seeds)

| | seed 42 | seed 43 | seed 44 |
|---|---|---|---|
| **2b-fair** corr(model, empirical slope) | +0.294 (p = 0.069) | +0.406 (p = 0.075) | +0.195 (p = 0.357) |
| **2b-crystal** corr(model, −ΔH/R) | +0.066 (p = 0.721) | −0.283 (p = 0.243) | −0.028 (p = 0.905) |
| median \|model − empirical\| slope | 1329 | 1088 | 1007 |
| **2a** curvature in 1/T, model | 1.99e6 | 2.14e6 | 2.27e6 |

Data curvature for the same pairs: **6.81e5**. Permutation nulls are 2000 draws over solute
identity.

**2b-fair.** The model tracks the empirical slope only weakly and not significantly at n = 13
solutes; the sign is at least consistent across seeds. Median absolute slope error 1000–1330
against a typical \|slope\| ≈ 3700, i.e. roughly 30%.

**2b-crystal.** Inconsistent in sign across seeds and non-significant throughout. Nothing to
read: the sample cannot support the test, as the ceiling row already showed.

**2a.** The model's response is about **3× more curved in 1/T than the data**. A pure van't Hoff
form is linear in 1/T; the model is not behaving like one, and its extra curvature is not present
in the measurements it was trained on.

## Verdict

The pre-registration's kill condition — "no factorisation **and** slope does not track ΔH_fus" —
is met on both clauses. **KILL, and per the branch map this is the informative negative that
feeds Study 4.**

The useful statement is about the corpus rather than the model:

> On this corpus the observed van't Hoff slope carries only a weak trace of the crystal
> enthalpy (r = +0.24 over 1353 solute–solvent pairs spanning 151 solutes, r² ≈ 0.06), because
> the temperature dependence of the activity coefficient dominates it. On the 13 held-out
> solutes carrying a measured ΔH_fus that trace is not distinguishable from zero, so a
> temperature-structure probe cannot decide what the model learned about crystal thermodynamics
> there. What can be said is that the model reproduces the observed slope only loosely (r = 0.20
> to 0.41 across seeds, ~30% median error) and that its response is roughly three times more
> curved in 1/T than the data, so it is not representing solubility in a van't Hoff-like form.

## Corrections made during this study

- **A metric of mine was invalid and is fixed.** The first run reported "fraction of ceiling"
  = r_crystal / ceiling, giving values like +2.27 and −0.53. Dividing by a ceiling that is
  itself indistinguishable from zero manufactures large ratios out of denominator noise. The
  script now reports it as undefined unless the ceiling clears p ≤ 0.05.
- **An alarm of mine was wrong.** The feasibility scout flagged empirical slopes up to +5715 as
  "thermodynamically impossible", implying the data were unusable. That was a single outlier
  pair: 1 of 1353 on train and 1 of 66 held out. The slopes are in fact very well resolved.

## Program state

1a answered (KILL). 1b/1c struck as not estimable. 2 answered (KILL). 3 dead by its own
precondition. **Study 4 — what the box organises by, if not physics — is now the whole remaining
program**, exactly as its own fallback clause anticipated. Study 1a's positive control already
supplies one input to it: h_BB encodes temperature at R² = 0.9997 and the model's own prediction
at 0.98, so the representation is far from empty; the question is what fills it.
