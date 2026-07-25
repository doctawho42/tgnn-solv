# Black-box Study 1a (confirmatory) — 2026-07-26: **KILL on all three seeds**

Protocol: `reports/PREREG_blackbox_AMENDMENT_2026-07-25.md` §A3–A4. Instrument:
`scripts/experiments/blackbox_study1a.py`. Raw output:
`results/blackbox/study1a_confirmatory_2026-07-25.json`. Zero GPU spend; ~2.5 CPU-hours.

Checkpoints: `checkpoints/e5_current_split/directgnn_seed{42,43,44}.pt`, whose manifests pin
train/val/test sha256 **identical to the current split on disk** (`419b3b2e / 974ea451 /
7871e8a9`), config `paper_config_directgnn_h64L3.yaml`, recorded MAE 1.7485 / 1.6741 / 1.6839
(mean 1.702, n = 5608). Blinding intact: no audit had computed probe numbers on these weights.

## Sample

| | |
|---|---|
| probe fit | 152 solutes / 14 348 rows |
| held out | **13 solutes** / 527 rows |
| solute overlap fit ∩ held-out | **0** (no leakage) |
| Φ* between-solute variance share | **0.922** |
| h_BB dimension (measured, not derived) | **788** |

Effective n is 13 clusters, not 527 rows.

## Result

| seed | R²(model) | permutation p | jackknife range | sign flips | verdict |
|---|---|---|---|---|---|
| 42 | **−0.5056** | 0.894 | [−1.151, −0.228] | 0/13 | KILL |
| 43 | **+0.1106** | 0.055 | [−0.286, +0.333] | 3/13 | KILL |
| 44 | **+0.0272** | 0.177 | [−0.253, +0.237] | 6/13 | KILL |

GO required R² ≥ 0.30 **and** p ≤ 0.01 **and** jackknife min > 0. No seed meets any of the
three. 1000 permutation draws per seed, α re-selected per draw.

## Controls

**Positive (the one that licenses a negative).** A row-misalignment bug in extraction produces
exactly the same signature as "not decodable". Probing quantities h_BB provably carries:

| target | held-out R² |
|---|---|
| the model's own prediction ŷ | **+0.9796** |
| temperature | **+0.9997** |
| Φ* (the actual target) | +0.1836 (test-only, 8 solutes) |

The same probe on the same representation recovers the model's own output almost perfectly and
temperature essentially exactly, and fails on the measured crystal term. The negative is a
property of the representation, not of the pipeline. This control is now enforced inside the
script: it aborts if ŷ decodes below R² = 0.8.

**Negative.** Random-target selectivity −0.0006 (all seeds) — the probe manufactures nothing.
Molecule-blind constant profile −0.0151. Raw descriptors: set A −0.5143, set B −0.9284.

**Leverage.** Top solute carries 20.7 / 27.0 / 23.3 % of held-out SSE; top three 56–60 %.

**Null calibration.** Per-seed null p95 = +0.105 / +0.117 / +0.096; null max = +0.316 / +0.380 /
+0.346. The GO bar of 0.30 sits *inside* the null's observed range, so the minimum reliably
detectable effect at this n is ≥ 0.30 and arguably higher.

## Two findings beyond the verdict

**1. The between-seed spread exceeds every individual value.** R² = −0.506 / +0.111 / +0.027;
range 0.616, sd 0.334, mean −0.123. A single-seed run would have been uninterpretable in either
direction — and seed 43 alone (R² = +0.11, p = 0.055) would have read as a near-miss worth
chasing. The pre-registration's three-seed requirement is what makes this readable.

**2. The retired rule would have declared success.** Applying the original gate
`ΔR² = R²(model) − R²(raw) ≥ 0.10` to these very numbers:

| seed | R² | Δ vs descriptor set A | Δ vs set B |
|---|---|---|---|
| 42 | −0.506 | +0.009 (miss) | **+0.423 (GO)** |
| 43 | +0.111 | **+0.625 (GO)** | **+1.039 (GO)** |
| 44 | +0.027 | **+0.542 (GO)** | **+0.956 (GO)** |

With descriptor set B **all three seeds clear the bar — including seed 42, whose probe is worse
than a molecule-blind constant.** The verdict was set by an unregistered analyst choice, not by
the model. The amendment retired this rule on 2026-07-25, before these numbers existed.

## The claim this licenses

> A ridge probe of the 788-d pair representation of a DirectGNN baseline (three seeds, current
> split, test MAE 1.67–1.75) does not recover the measured ideal-solubility term Φ*(mol, T) on
> 13 held-out solutes: R² = −0.51 / +0.11 / +0.03, none significant against a 1000-draw
> molecule-identity permutation null, against a positive control in which the same probe recovers
> the model's own prediction at R² = 0.98 and temperature at R² = 0.9997.

**It is a bound, not a point.** At n = 13 held-out clusters the null reaches R² ≈ 0.32–0.38, so
this design cannot say "the box does not encode Φ*" — only that **an effect of R² ≳ 0.30 would
have been seen and was not**. Whether a weaker crystal signal is present is beyond the oracle's
reach, and per amendment §A5 the oracle cannot be enlarged on the held-out axis.

## Program consequence

Study 1a is answered. 1b/1c remain struck (§A5: the crystal ∩ activity oracle intersection is
the common-solvent set, 66% of training rows). Study 3 dies with its precondition. **Study 2
(temperature structure) and Study 4 (what the box organises by, if not physics) are the
remaining live program** — and note that the positive control already establishes h_BB encodes
temperature at R² = 0.9997, which is where Study 2 starts.
