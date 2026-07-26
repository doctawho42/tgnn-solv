# The top-2 EVR claim: the isotropic null is wrong, but the claim survives a proper one

Raised by the reviewer panel as blocking, verified independently, and then narrowed. Tooling:
`scripts/analysis/run_evr_structured_null.py`. No new training; all figures are CPU-cheap.

## What the paper said

The compensating-surrogate section reads the top-2 explained-variance ratio (EVR) of the
mean-centred σ-deviation as $72\pm1\%$, against a finite-sample **isotropic** null of $\approx15\%$,
and calls the drift low-rank at "$4.8\times$ the null".

## The isotropic null is the wrong reference — confirmed

Any smooth function on the 51-bin σ grid has a concentrated spectrum whether or not it carries
information. Smoothing iid noise alone reproduces the effect:

| Gaussian kernel | 1 bin | 2 bins | 4 bins | 8 bins |
|---|---|---|---|---|
| top-2 EVR | 0.247 | 0.371 | 0.577 | 0.832 |

And structure-carrying references on the same 44 molecules sit at or above the observed value:
the VT-2005 profiles themselves give 0.7685, a leave-one-out corpus-mean drift 0.7685, and the
true profile of a randomly chosen other molecule 0.740–0.784. Against those, the observed 0.718
is not distinguished. **The "$4.8\times$" multiple must be withdrawn.**

## But the panel's replacement null is too strong

The wrong-molecule and corpus-mean controls are differences between two real profiles, so they
inherit the low dimensionality of the σ-profile manifold itself — far more concentration than a
compensation drift needs. Failing to exceed them does not refute a shared direction; it only says
the drift is less concentrated than the manifold it lives on.

The reference that isolates the actual claim is **phase randomisation**: per row, randomise the
Fourier phases and keep the amplitude spectrum. Each deviation keeps its own roughness exactly;
only the alignment *between* molecules is destroyed. That is precisely what "low-rank,
transferable" asserts.

## Measured

On the deviation of a grounded checkpoint's σ̂ from the VT-2005 reference
(`results/closure_fix/ckpt/arm_base.pt`, n = 44):

| reference | top-2 EVR | verdict |
|---|---|---|
| observed | **0.3994** | |
| isotropic null (what the paper used) | 0.1514 | ratio 2.64×, meaningless |
| **phase-randomised null** | **0.2206 ± 0.011** | **p < 0.001, exceeded** |
| wrong-molecule null | 0.7721 ± 0.023 | p = 1.000, not exceeded |

So a shared direction across molecules is real, at about **1.8× a smoothness-matched null** rather
than 4.8× an isotropic one.

## What this licenses, and what it does not

The claim that the drift has a component shared across molecules survives, with the multiple cut
by roughly a factor of three and the reference changed. What does **not** survive is the specific
"$4.8\times$ the null" figure and any reading of the isotropic comparison as evidence of low rank.

**Scope limit, stated plainly.** The measurement above is on the σ̂-versus-reference deviation of a
locally available grounded checkpoint. The paper's headline $72\pm1\%$ is the *isolation* drift
(fine-tuned minus grounded) from a three-seed cloud run whose checkpoints are not on this machine,
so it has not itself been re-tested against the smoothness-matched null. The two are different
deviations and their values are not comparable; the local pair
(`arm_C_closure_seed0` versus `arm_base`) cannot substitute, because those two checkpoints share a
σ head and their drift is identically zero.

## Guard added

The tool refuses a degenerate deviation. The first run of the isolation case returned a NaN EVR
(zero drift), and because NaN compares false against every null it printed the *favourable*
verdict. The script now aborts on a non-finite or identically zero deviation rather than reporting
one.
