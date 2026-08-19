# Out-of-sample test of the glycol-ether separation on ThermoML rows the search never saw

Written 2026-08-19. Everything from here to the line marked END OF PRE-DECLARATION was fixed
before any MSE, bound or margin was computed on these rows.

## Why this exists

`run_b_insuff_stratified_map.py` searches fifty-nine strata and states one: the glycol-ether
solvents of the broad IDAC set, 182 rows over 43 pairs from three publications, margin +2.04
[+1.25, +2.87] at the headline cell. `run_b_insuff_map_multiplicity_null.py` then relabels the
chemistry at random with the containment lattice, the stratum sizes and every row's m, g, source
and pair held fixed, and returns a certified margin of +2.04 or more in 10.1% of draws. The
observed margin sits near the ninetieth percentile of a chemistry-blind null. A number a blind
search returns that often is not, on the strength of that search alone, a located fact about
glycol ethers.

The pre-declared out-of-sample test returned **not testable**. `results/glycol_external_scope/scope.json`
(2026-08-11) established that this was a property of the two sets that were searched — the
14,900-row expanded pull and the PGL 6th-edition set — and not of the literature.

## What is already known, and what is not

**Known: the geometry**, from `scripts/analysis/build_glycol_oos_thermoml.py`, which computes no
outcome quantity. Of two machine-readable candidates, one delivers:

| | |
|---|---|
| source | 10.1016/j.jct.2013.05.011 (one DOI; see the limitation below) |
| rows extracted | 143, all on a pure-liquid-solute basis |
| net-new rows after excluding pairs the broad set carries | **95** (66.4%) |
| net-new pairs | 32 |
| solutes / solvents | 21 / 2 (diethylene and triethylene glycol) |
| temperatures | 333.2, 348.2, 363.2 K |
| VT-2005 profile coverage | 21/21 solutes, 2/2 solvents, **95/95 rows scorable on both sides** |

The second candidate, 10.1021/je0102107, contributes **nothing net-new**: its ethylene-glycol
pairs are all already in the broad set. That is true under the strict extractor and also under the
looser chromatographic admission rule declared in the builder — a rule written after it became
clear that a second source would change admissibility, and which did not in fact rescue it.

**Not known: any outcome quantity.** No MSE, no bound, no margin has been computed on these 95
rows.

## The estimator, fixed here

* **The cell.** Eight equal-count bins of `g(z*)`, the unbiased (Bessel-corrected) within-bin
  variance, the **row** unit, the **residual-only** combinatorial convention. This is the cell
  every margin in the paper is read at (§2.5). It is not swept and no other cell is reported as
  the answer.
* **The prediction side.** `g` is the deployed `CosmoSacLayer` evaluated on VT-2005 σ-profiles for
  both molecules, at the row's own temperature — the same construction as the broad set.
* **The quantity.** The separation margin `MSE − 2·B_insuff^up`, and its 90% interval by
  bootstrap over **pairs**, the only clustering this single-source set supports.
* **No re-selection.** The row set is the 95 rows above. No stratum inside it is searched, no
  solvent or temperature subset is reported as the finding, and no row is dropped after a margin
  is seen.

## The limitation, stated before the result

This set carries **one source DOI**. The map's own admissibility rule requires a margin to keep
its sign under deletion of each contributing publication, and a single-source set cannot be put to
that test. **Whatever this returns is therefore a descriptive out-of-sample reading and not an
admissible one**, and it is reported as such whichever way it falls. It is not made admissible by
a favourable outcome.

## The three outcomes, and what each licenses

**HOLDS** — margin > 0 and its 90% interval excludes zero.
The separation reproduces on 95 rows and 32 pairs the fifty-nine-fold search never saw. This does
not make the stratum admissible (one source), and the multiplicity null still stands over the
in-sample claim. What it licenses is one sentence: the survivor reproduces out of sample on this
set. The paper keeps its current hedged framing and adds that sentence.

**FAILS** — margin ≤ 0.
The separation does not reproduce out of sample. **The glycol-ether stratum is then demoted in the
paper from a stated finding to an instrument reading**: it leaves the abstract, it loses its star
in Figure 1b, and §3.2.1 states that the one row set the rule leaves standing does not reproduce
on independent rows. This is committed to here so that it is not renegotiated after the number is
seen.

**UNRESOLVED** — margin > 0 but its 90% interval spans zero.
The set has no resolution at this size. Reported as a third outcome, not folded into either of the
others, and the stratum keeps exactly the standing it has today.

## END OF PRE-DECLARATION

Producer: `scripts/analysis/run_glycol_oos_margin.py`, written after this file was hashed and
committed.
