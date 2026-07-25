# Black-box Study 4 — 2026-07-26: the representation is organised by scaffold, not by physics

Instrument: `scripts/experiments/blackbox_study4.py`. Raw: `results/blackbox/study4_2026-07-26.json`.
Three current-split checkpoints, zero GPU spend, minutes of CPU.

Study 4 escapes the bottleneck that limited 1a and 2. Those needed the crystal oracle and so ran
on 13 held-out solutes; 4a/4b need no oracle and run on the **whole test split**: 5608 supervised
rows, 147 solutes, 124 Murcko scaffolds, 70 solvents.

## Method and one thing that had to be got right

For each candidate organising factor we report the share of h_BB's total variance it accounts
for, against a permutation null. **The level of the null is not cosmetic.** η² is invariant to
relabelling groups, so permuting an identity factor at its own level is a no-op — the null equals
the observation and the excess is identically zero. So:

- **identity factors** (solute, solvent) take a **row-level** null: is this partition better than
  a random partition of the same shape?
- **factors derived from identity** (scaffold, logP, TPSA, MolWt, Φ*) take a **solute-level**
  null: is this particular labelling better than an arbitrary solute-level one? A row-level null
  for these destroys the within-solute block structure, which makes the null far too easy and
  turns any solute-level signal into "p = 0.000".

Scaffold is reported under both, because both questions matter.

## Result (excess over null; three seeds)

| factor | seed 42 | seed 43 | seed 44 | null level |
|---|---|---|---|---|
| solute identity (147 levels) | **+0.613** | +0.587 | +0.597 | row |
| solute scaffold (124 levels) | **+0.614** | +0.586 | +0.595 | row |
| scaffold beyond an arbitrary solute grouping | +0.082 | +0.082 | +0.082 | solute |
| solvent identity (70 levels) | +0.278 | +0.301 | +0.271 | row |
| temperature | +0.040 | +0.029 | +0.037 | row |
| logP (solute) | +0.089 | +0.048 | +0.028 | solute |
| TPSA (solute) | +0.060 | +0.061 | +0.042 | solute |
| MolWt (solute) | +0.032 | +0.013 | +0.018 | solute |

All p ≤ 0.01 except where noted. As a share of the solute-identity ceiling:

| | seed 42 | seed 43 | seed 44 |
|---|---|---|---|
| **scaffold** | **100.3 %** | **99.9 %** | **99.8 %** |
| logP | 13.6 % | 8.2 % | 4.7 % |
| TPSA | 9.0 % | 10.3 % | 7.1 % |
| MolWt | 5.3 % | 2.3 % | 3.1 % |

## Three findings

**1. The molecular organisation is scaffold-level, and essentially nothing finer.** 124 scaffolds
account for 99.8–100.3 % of what 147 individual solutes account for, across all three seeds. The
representation does not resolve molecules that share a Bemis–Murcko scaffold. It is also
specifically scaffold rather than "some solute grouping": against a solute-level null the excess
is +0.082 in every seed.

This is a direct, measured explanation of the project's scaffold-transfer limit. A test molecule
on an unseen scaffold is not a mild extrapolation for this model — it is outside the axis along
which the representation is organised at all.

**2. Decodability is not organisation.** Study 1a's positive control showed temperature is
decodable from h_BB at R² = 0.9997. Here temperature occupies **2.9–4.0 % of the representation's
variance**. A probe recovering a quantity says nothing about whether the representation is
*organised* by it. Both statements are true of the same 788-d vector, and only the second one
speaks to how the model works.

**3. It is not organising by crude physical character either.** logP, TPSA and molecular weight
together account for a small share of the solute-level structure (each below ~14 %, and below 8 %
in most seed-descriptor cells), against scaffold's ~100 %. The axis is structural identity, not
polarity or size.

## 4c and how it squares with Study 1a

On the 331 rows carrying a measured Φ*, Φ* accounts for 18.3 / 42.5 / 18.0 % of that subset's
own solute-identity ceiling. Read this cautiously: 8 solutes, and the seed spread is a factor of
two.

It does **not** contradict Study 1a's null. Φ* is a solute-level quantity and the representation
is organised by solute identity, so *any* solute-level variable shares variance with it in
sample. Study 1a asked the sharper question — does the mapping generalise to solutes the probe
never saw — and the answer there was no (R² = −0.51 / +0.11 / +0.03 on 13 held-out solutes). In
sample the box's organisation is partly aligned with Φ*; out of sample that alignment does not
transfer. Those are the two halves of the same picture.

## Program

This closes the pre-registered programme. 1a KILL, 1b/1c not estimable, 2 KILL, 3 dead by its
precondition, and 4 answered positively — the distinctive contribution the branch map called
"murky made measurable" is the one that survived. Study 5's question ("does the non-physical part
explain the scaffold-transfer limit") is answered by finding 1 above and needs no separate run.

## Self-correction recorded

The first version of this analysis applied one null level to everything. Applied blanket at the
solute level it made identity factors degenerate (excess ≡ 0, and shares printed as 7.4e16 %);
applied blanket at the row level it inflated every solute-level factor. Both were wrong for half
the table. The level is now chosen per factor and printed in the output so a reader can check it.
