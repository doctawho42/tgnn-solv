# PRE-REGISTRATION: minimal-loss ablation of the compensating-surrogate paradox (2026-07-18)

Written BEFORE running `kaggle_run.py --do loss_ablation`. Purpose: answer the reviewer-adjacent
question "does the paradox need the ~30-term objective, or is the loss zoo incidental?" and fill the
`\pending` stub at `\label{sec:si-lossablation}` with a real number.

## The question
Of the ~32 loss components, 17 sit at weight 0 (tabulated in `tab:loss`) and most of the remaining ~15
are small structural priors. If the compensating-surrogate paradox (learned sigma_hat through a fixed
COSMO-SAC closure beats the true VT-2005 reference profile) is an artifact of some particular auxiliary
term rather than an intrinsic property of a sloppy closure fed a fitted low-rank latent, that would
undercut the mechanism. So: strip the objective to the minimum and see if the paradox survives.

## Design
`configs/cosmo_sac_minimal.yaml` zeros EVERY auxiliary-grounding and regulariser weight, keeping only:
  - `sol` (the bin-weighted Huber on ln x2, the task), weight 1.0 in the SLE phases;
  - `T_m`, `dH` (the crystal factor feeding the ideal term Phi).
Dropped: `hansen`, `gamma_inf`, `res`, `bridge`, `phys_pref`, `direct_reg`, `direct_nll`,
`pair_temp_rank`, `vant_hoff_local`, and every zero-weight prior. Note `hansen`/`gamma_inf` carry
weight **0.5** in phase 1 of the full loss (not the ~0.05 of phase 2), so this is a real perturbation
to how the sigma head is grounded, not a cosmetic one.

KEPT (deliberately, not under test): the sigma-EMD warmup stream and the crystal pool stream. These ARE
the single-component grounding whose necessity the paper argues FOR; the ablation questions the dense
per-pair aux/reg terms, not the grounding-stream mechanism. The whole pipeline is retrained from scratch
under the minimal loss (5 phase-1 epochs + 15 SLE epochs, seed 42, L4), then the end-to-end grounded
checkpoint is evaluated learned-vs-reference exactly as in `paradox_2x2`.

## Pre-registered quantity and decision rule
On the both-reference subset (solute AND solvent in VT-2005, the only rows where the reference condition
is defined), define
  PARADOX = mean(R2 | both_reference) - mean(R2 | both_learned).
A NEGATIVE value means the learned profile beats the true reference => paradox present. Let PARADOX_full
be the same quantity from `paradox_2x2` (the full-loss run, same subset, same seed).

- **H_intrinsic (expected):** PARADOX_min stays the same SIGN and within ~1 sd of PARADOX_full
  (operationally |PARADOX_min - PARADOX_full| <= 0.05 R2, and both negative on the drift-bearing regime).
  Interpretation: the surrogate mechanism is a property of the closure + fitted latent, not the loss zoo.
  => the ~30-term objective is engineering convenience; the SI can say the paradox is loss-robust and the
  minimal loss reproduces it. (Good-news outcome; matches the theory in S4-S6.)

- **H_loss-dependent:** PARADOX_min FLIPS sign or collapses toward 0 (|PARADOX_min| < 0.5 |PARADOX_full|).
  Interpretation: some dropped term was load-bearing for the drift. => the mechanism claim needs the
  qualifier "under the full objective," and the SI must name which family (aux-grounding vs regulariser)
  by a follow-up drop-one ablation. (Bad-news outcome; do NOT hide it.)

Guardrail read (sanity, not a hypothesis): the minimal-loss model must still TRAIN -- if val ln x2 does
not converge to within ~0.3 of the full-loss base (i.e. the crystal+sol-only model is degenerate), the
ablation is uninformative and only bounds "the paradox needs SOME activity grounding," which we already
know. Report the minimal-base val alongside PARADOX_min so a degenerate run is visible, not silently read
as H_loss-dependent.

Commit this file before the run; report against it without moving the thresholds.
