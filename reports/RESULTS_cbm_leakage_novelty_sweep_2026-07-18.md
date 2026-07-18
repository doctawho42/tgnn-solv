# CBM-leakage novelty sweep (2026-07-18)

Verified the paper's §2 concept-bottleneck-leakage claims. Two scouts completed (measurement/detection;
soft-vs-hard/side-channels); two more + the synthesis died on transient API/network errors, but the two
that returned read all the canonical papers and agreed on every verdict.

## CLAIM A -- leakage framing ("a learned concept silently encodes surplus info; interpretation misleading")
**ESTABLISHED (both scouts).** Canonical; the paper's citations are correct: Mahinpei et al. 2021
(Promises and Pitfalls, arXiv:2106.13314), Margeloiu et al. 2021 (Do CBMs Learn as Intended?,
arXiv:2105.04289), Havasi et al. 2022 (Addressing Leakage in CBMs, NeurIPS). Keep as-is.

## CLAIM B -- "the reverse-causation / frozen-head direction is unnamed" (the risky one)
**PARTIAL -- OVERSTATED. Softened + cited.** The downstream-driven route is already named:
**Parisini et al. 2025, "Leakage and Interpretability in Concept-Based Models" (arXiv:2504.14094)** --
"if the final head is not flexible enough to learn the ground-truth y=f(c) dependence... the model
tends to store the necessary dependences into the learnt concepts, which are thereby deformed" -- i.e.,
a misspecified/inflexible head FORCES the encoder to absorb the error. The frozen-head ingredient is in
**Espinosa Zarlenga et al. 2025, "Avoiding Leakage Poisoning" (arXiv:2504.17921)** (the label predictor
is pre-trained and fixed). Action taken: §2 no longer claims the distinction is novel/unnamed; it now
credits Parisini + leakage-poisoning and keeps only the genuinely-specific delta (the downstream map is
a FIXED PHYSICAL operator, uncorrectable in principle).

## CLAIM C -- "the leak is low-rank / structured / transferable, not diffuse"
**NOT_FOUND -- genuinely novel (strongest novelty claim).** No CBM-leakage work characterizes leakage
as low-rank / a shared low-dimensional side-channel / cross-domain-transferable. The measurement
literature treats it as scalar mutual information (arXiv:2504.09459), data-subset splits
(arXiv:2410.06352), or per-example distribution deformation (Parisini). Kept in §2, asserted carefully
as "not characterized this way in CBM leakage."

## CLAIM D -- sign rule (true/intervened concepts help iff head well-specified)
**PARTIAL.** The "intervention can HURT under misspecification" half is documented: leakage poisoning
(Espinosa Zarlenga 2025) -- overwriting a frozen head's concepts with ground truth degrades OOD
accuracy; Parisini -- concept supervision cannot compensate for final-head misspecification. The crisp
biconditional is a reasonable synthesis, not an unprecedented rule. Consistent with the pKa competence
crossover; presented as such, not as unclaimed.

## Must-cite (added)
- Parisini et al. 2025 (arXiv:2504.14094) -- pre-empts CLAIM B, supports D. ADDED (parisini2025).
- Espinosa Zarlenga et al. 2025 "Avoiding Leakage Poisoning" (arXiv:2504.17921). ADDED (espinosa2025leakage).
- (Optional contrast for C, not added: arXiv:2504.09459 info-theoretic, arXiv:2410.06352 tree-based.)
- (Foundational, not added: Koh et al. 2020 CBMs; Espinosa Zarlenga 2022 Concept Embedding Models.)

## Bottom line
§2's CBM-leakage claims are now safe: framing correctly cited (A), the previously-overstated
reverse-causation novelty softened and cited to Parisini/leakage-poisoning (B, D), and the one durable
novelty -- the low-rank, transferable structure of the leak -- kept and cited against the contrast (C).
