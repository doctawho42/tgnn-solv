# Readability & completeness revision plan (readability-audit workflow, 2026-07-12)

Source: 4-dimension fan-out audit (terms / number-density / figure-gaps / flow) + synthesis.
Rule for all edits: preserve EVERY hedge and caveat; readability never at the cost of honesty.
Figures are real TikZ/data schematics, NOT decorative AI images.

## Batch 1 — P0 (text, S/M effort)
- [ ] TIMP: expand "Thermodynamically-Informed Message Passing (TIMP)"; footnote it does not beat MPNN (transfer- not expressivity-limited). [methods.tex]
- [ ] COSMO-SAC: gloss at first use (COnductor-like Screening MOdel–Segment Activity Coefficient; activity-coeff from surface screening-charge); cite lin2002 in Methods. [abstract/setup]
- [ ] VT-2005: expand (Virginia Tech 2005 QC screening-charge-density profiles, ~1400 cmpds; cite mullins2006). [setup]
- [ ] σ-profile: one-clause gloss at first substantive use. [setup]
- [ ] SLE: bind acronym in Setup + one intuition sentence before Eq. [setup]
- [ ] Abstract opener: split ~45-word sentence into 3–4. [abstract]
- [ ] Contributions item 5: break nested caveat out of the "we prove X,Y,Z" list. [intro]
- [ ] Contributions item 2: gloss "convention-independent" at first use. [intro]
- [ ] Efficient-information lemma: add "In words:" gloss. [theory]
- [ ] §4.1 paradox de-densify: add true-σ-at-train (1.98) + channel-swap (2.08) rows to tab:si-arms; trim inline to "1.85 vs 2.25"; drop n=5608/R²≈0 from prose. [grounding_paradox + SI]
- [ ] §4.2 separation de-densify: one inline inequality (B_clos ≳ 0.9 > B_insuff ≲ 0.62); cite tab:decomp; push residual-only inversion to SI hedge. [grounding_paradox]

## Batch 2 — P1 (figures + medium rewrites)
New figures (dependency order): fig:composed (TikZ, sets x→h→z→g→y vocab) → fig:decomp-concept (matplotlib schematic) → fig:ident (TikZ vectors) → fig:phase (conceptual); revise fig:arch (DirectGNN solid branch + annotate B_clos/B_insuff/tax).
Number-table moves: ident ΔT→tab:fisher; dial pts→fig:dial; ranking metrics→small table; chemistry-map/temperature/crystal-null/pKa/Gate-B trims; solute-class companion table; units pass (ln x₂ / (ln γ)²).
Medium rewrites: §measure first sentence + Tier-2 split; Tier 1/2 definition; §paradox two-facts split + SG gloss; σ/Hammett glyph disambiguation; NRTL/ThermoML/Bemis–Murcko glosses; low-γ; Abstract physics-tax split; assumption-free bullet reword.

## Batch 3 — P2 (polish)
Acronym glosses: GPS(rampasek2022), SOTA, LFER, UNIFAC(fredenslund1975), Hansen, van't Hoff, CRLB, LOTV, RF, Walden, Lin–Sandler(lin2002), ΔC_p, Bayes predictor. Citation-dump reflow (model-discrepancy…underspecification). Jensen-precision + aleatoric-count trims. Optional fig:conflation cartoon if not folded into fig:decomp-concept.

## Bib entries to add (references_verified.bib)
mullins2006 (VT-2005 σ-profile DB), lin2002 (COSMO-SAC), renon1968 (NRTL), frenkel2011thermoml (ThermoML), rampasek2022 (GPS), fredenslund1975 (UNIFAC).
