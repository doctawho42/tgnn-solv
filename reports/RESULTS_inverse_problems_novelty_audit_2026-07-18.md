# Inverse-problems novelty audit (2026-07-18)

Multi-agent literature sweep (6 sub-literatures + synthesis) to test whether three "novel" theory
claims are already known. Verdict below; full agent findings in the workflow journal
(`subagents/workflows/wf_4bdb7137-20b/journal.jsonl`).

> **CORRECTION (post-review, committed 251fdcf).** The CLAIM 1 "math fix" below ("drift-rank <=
> n-rank(J), drift in ker(J)") is only half right. The drift has TWO orthogonal components: the FREE
> one in ker(J) (dim ~ n-rank(J), = Lemma 1 non-identifiability, what Schwab/EHN/Hansen cover) and the
> COMPENSATION in row(J) = ker(J)^perp (dim <= rank(J), low-rank because J is sloppy, = the S6.3
> surrogate = J+(m-g)). Compensation MUST live in row(J) (cancelling B_closure requires moving g's
> output), so "<= n-rank(J)" is right only for the free component; the original "<= rank(J)" was right
> for the surrogate. In the paper the null-space cites now sit at Lemma 1 (the ker side), not
> S sec:surrogate; the row/ker rank geometry stays out of this paper (ML paper only).

## CLAIM 1 — compensating drift lives in the null / low-sensitivity directions of the fixed map, selected by the prior
**ESTABLISHED (renamed classical result). Niche NOT open.**
- The confinement geometry is 1990s regularization theory: for a forward map, the fit's non-uniqueness
  lives in ker(A); a regularizer/prior selects that component (Engl-Hanke-Neubauer 1996; Hansen 1998).
- Literal deep-learning restatement: **Schwab, Antholzer & Haltmeier 2019, "Deep Null Space Learning
  for Inverse Problems," Inverse Problems 35(2):025008** (arXiv:1806.06137). Also Chen & Davies 2020
  ("Deep Decomposition Learning"), DDNM (Wang et al. 2023).
- Nonlinear / small-singular-value reading = sloppy-model theory (Gutenkunst 2007; Transtrum-Machta-
  Sethna 2011): predictions near-invariant along small-eigenvalue Jacobian/FIM directions.
- **Bankable delta (cite-and-differentiate only):** (1) EMERGENT under free gradient training of a
  latent through a fixed map (null-space nets IMPOSE it via an explicit projector); (2) nonlinear
  LOCAL-Jacobian localization; (3) latent-drift-under-misspecification as a diagnostic.
- **MATH FIX (before publishing):** "drift-rank <= rank(J_g)" is backwards. The fit-invariant drift
  lives in ker(J_g), so the bound is drift-rank <= dim ker(J_g) = n - rank(J_g).
- Note: the DD paper's SI already frames this correctly (near-rank-one activity Fisher => sigma
  under-determined) and does NOT carry the backwards inequality; but §sec:surrogate should CITE the
  classical lineage (Schwab 2019 + Engl-Hanke-Neubauer + sloppy models) and claim only the delta.

## CLAIM 2 — oracle decomposition E[(m - g(z*))^2] = B_closure + B_insuff
**PARTIAL (true-but-shallow), unanimous.**
- An add-and-subtract-the-oracle bias/variance identity. B_closure = model discrepancy at the true
  input (**Kennedy & O'Hagan 2001**, already cited); B_insuff = input/parametric error (Geman-
  Bienenstock-Doursat 1992 algebraic template). Present as a diagnostic specialization, not a theorem.
- Caveats: (a) as literally written E[(m - g(z*))^2] is the CLOSURE term alone; the intended split is
  of the TOTAL error E[(m - g(h(x)))^2]; (b) "exact two-way" needs the cross-term to vanish -- state
  the orthogonality/oracle condition explicitly.

## CLAIM 3 — sign rule: true input helps iff the fixed map is well-specified
**PARTIAL, narrow the claim.**
- Phenomenon documented: **Brynjarsdottir & O'Hagan 2014** (cited), White 1982 (cited), CBM leakage
  (Mahinpei/Havasi, cited). The sharp two-sided iff tied to map fidelity is genuinely unclaimed.
- **Counterexample to uniform dominance:** under CORRECT specification an estimated nuisance can still
  beat the true one on EFFICIENCY (Hirano-Imbens-Ridder 2003; Robins-Ritov). So "true helps iff
  well-specified" holds for BIAS/CONSISTENCY, not uniform dominance -- narrow accordingly.
- This is the SAME phenomenon as the pKa competence crossover (learned sigma_hat beats oracle sigma*
  on the misspecified pole): grounding helps iff the fidelity-set oracle error is below what the
  learned arm achieves. The narrowed sign rule and the crossover law are one statement.
- Thin spot: the ML-native concept-leakage literature was adjacent, not a primary search target --
  verify there before finalizing the sign rule's novelty.

## Bottom line
The ML-paper's highest-risk claim (CLAIM 1) is a renamed classical result: cite null-space /
regularization theory (Schwab 2019 + Engl-Hanke-Neubauer), do not claim the confinement geometry as
novel, and fix the ker/co-rank inequality. Claims 2-3 are diagnostic specializations of known results
-- keep them as diagnostics, narrow the wording.
