# The solubility "grounding paradox" is a solvent-channel effect (2026-07-18)

Verification of a reviewer finding (peer-review workflow, R2/Phys-Chem): is the locked e5 solubility
paradox (grounded learned-sigma -> reference-sigma oracle) driven by the solvent channel, and ~0 on the
both-reference subset? Reproduced from the committed per-row predictions
(`results/e5_sigma_grounding/seed_{42,43}/{grounded_a,oracle}_predictions.csv`), sliced by VT-2005
coverage of solute vs solvent (`results/sigma_profile_artifact/sigma_profiles.csv`, 1424 canonical
SMILES). Script: `scripts/analysis/run_paradox_channel_split.py`.

## Result (seeds 42+43, position-aligned; reconciles with the 3-seed headline grounded 1.846 -> oracle 2.252)

| subset | n/seed | grounded MAE | oracle MAE | paradox (oracle - grounded) |
|---|---|---|---|---|
| ALL supervised | 3738 | 1.862 | 2.256 | **+0.394** |
| both-reference (solute AND solvent in VT-2005) | ~198 | 1.237 | 1.254 | **+0.017 (~0)** |
| solvent-only in VT (solute NOT) | ~3516 | 1.898 | 2.317 | **+0.418** |
| neither in VT | ~24 | 1.753 | 1.753 | 0.000 |

Coverage: solvent in VT-2005 on 99.3% of rows, solute on only 5.3% (7 of 147 unique solutes; ~198
rows/seed both-reference). There are ZERO solute-only rows (solvents are essentially always covered).

## Conclusion
The headline +0.40 MAE / R2-collapse paradox is carried almost entirely by rows where the reference
substitutes the SOLVENT sigma while the SOLUTE sigma stays learned (solvent-only, +0.418). On the
both-reference subset -- the only place the substitution is a clean "true inputs for both channels" --
the paradox is +0.017 ~ 0. So the effect is solvent-channel co-adaptation breakage (a mixed
reference-solvent / learned-solute state), not a clean "grounding the solute in its true profile
hurts." VT-2005's coverage asymmetry (simple solvents covered, drug-like solutes not) is the structural
reason the substitution lands almost entirely on the solvent.

Does NOT refute the paper's mechanism: the compensating-surrogate (n=44) and the closure/insufficiency
decomposition (n=60) are ACTIVITY-level (ln gamma) on the matched both-reference activity sets and are
untouched. What needs reframing is the SOLUBILITY-level headline (title/abstract/Fig. paradox): report
both-reference vs solvent-only separately, disclose the asymmetry, and load the causal claim onto the
matched n=60/n=44 activity results (or compute reference profiles for a sample of drug-like solutes to
test the solute channel directly).

## Data-integrity note
seed_44's oracle per-row file is truncated to 295 rows (the 3-seed summary's 2.242 was computed at
runtime, but the saved CSV did not persist the full 5571) -- a save bug; this analysis uses the two
complete seeds. Flag for the reproducibility pass.
