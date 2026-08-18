# What the article asserts, and what each assertion costs in words

Built 2026-08-19 against `paper/grounding_paradox.tex` at body length **18,066 prose words**
(comments stripped, floats excluded, LaTeX commands stripped). JCIM comparison, measured on 60 full
texts: median body ~6,800, maximum ~13,000; median Results section ~2,960, maximum 5,733.

Purpose: the length pass has exhausted everything that costs no claim. Free cuts are gone (~390
words), and a full compaction rewrite of every section is worth about 900 more, measured on the
Introduction where every claim and all 22 citations were held fixed and the return was 5%. What
remains is a decision about which assertions to stop making. This file prices them.

## How to read the columns

- **cost** — words the article spends on the assertion, including the scope clauses that travel
  with it. Deleting a claim without its caveats is not an option this project allows, so the caveat
  words are part of the price.
- **record** — whether the Supporting Information still carries the fact if the article drops it.
  `SI` means the record survives and only the article-level claim is lost. `NOWHERE` means deleting
  it deletes it from the corpus.
- **breaks** — cross-references from the other document that would dangle, and checker bindings
  that would need editing. These are work, not objections.

---

## Tier 1 — one decision, and it is the largest in the manuscript

| # | assertion | cost | record | breaks |
|---|---|---|---|---|
| 1 | **The second chemical domain (§3.6, pKa through a fixed Hammett relation).** That the instrument is not COSMO-SAC-specific; that the sign of grounding *reverses inside one closure* in the direction the construction fixes in advance; the clean/degraded poles; the K=20 oracle swap both ways; that the flip is in-distribution and the scaffold protocol does not certify it. | **1,341** | SI (`sec:pka` carries the construction, the estimator validation and the fidelity sweep) | 7 refs from the SI |

Dropping this makes the paper a solubility paper. What is lost is the only evidence that the
instrument generalises, and the only place a sign reversal is *predicted before measurement* and
then observed. The abstract's last clause and one Introduction sentence go with it.

## Tier 2 — displays that could live in the SI, which already prints them

| # | assertion | cost | record | breaks |
|---|---|---|---|---|
| 2 | **The two map tables** (`tab:map-article`, `tab:map-article-solute`) with their notes: all 15 boundable strata, their margins, sources and per-row verdicts. | **1,291** | SI (`sec:si-map-cells` prints all 59) | 0 SI refs; **2 checker CaptionSpecs** would move |
| 3 | **Table 2 and its paragraph** — the deployed closure against a published evaluation of the same closure, establishing that the error decomposed here is the error a published COSMO-SAC has. | **645** | partly SI | 6 SI refs to `tab:closure-anchor` |
| 4 | **The black-box probe** (§3.7) — that the thermodynamics is absent from the unconstrained control's representation; limitation (ix). | **414** | SI (`sec:si-blackbox`) | none |

## Tier 3 — results whose claim would go with them

| # | assertion | cost | record | breaks |
|---|---|---|---|---|
| 5 | **§3.2's ranking and recalibration block** — that the substitution costs the *decision* (which solvent the model picks) and not only the level; that a per-group affine map absorbs the MAE gap and not the ranking; the solute-blind floors. | **933** | SI (100% of its numerals) | 3 SI refs to `sec:decision` |
| 6 | **§3.2's shrinkage and tail paragraphs** — that every arm is severely shrunk, that the reference arm is the least shrunk and the worst, and where its worst region is. | **468** | partly SI | none |
| 7 | **The ΔCp exposure** (§2.1) — the omitted term is one-signed and worth a median 0.32 in ln x2 on the rows carrying a measured melting point. | **405** | SI + limitation (xiv) | cited by §3.3 |
| 8 | **§3.5.1's cross-fitted estimator deviation** — that the pre-declared estimator passed its gate, that the declaration required adopting it unconditionally, and that it was not adopted. | **259** | SI | none |

## What is not on this list, and why

**The licence chain.** Lemma 1, its four conditions of use, the one-sided reading rule, and the
composite definition of B_closure (§2.1.1, ~660 words). Every one licenses a claim made elsewhere;
removing them leaves those claims with nothing behind them. Verified 2026-08-19.

**The donor-window finding** (§3.3, 373 words) — 0.000 Å² for cyclohexane, acetone, toluene and THF
in the reference tabulation against 44.0/32.4/24.5/50.7 for the learned profile, with its
264-of-1003 evidence and its untrained-network null arm. It exists in **one place in the corpus**.
This is also the manuscript's most chemistry-legible result.

**§3.5.2** (184 words) — its closing sentence is a caveat on the headline: VT-2005, and therefore
the paradox's own oracle, is defined on this sub-design, and the two sets' agreement is a
consistency check and not corroboration. Deleting a caveat from the result it qualifies is what this
project's rules forbid.

**Gate B** (§3.3, 105 words) — none of its four numbers is deposited anywhere.

**The fourteen limitations** (694 words) — the JCIM measurement puts a limitations block at
400–750 words and this one is inside that band.

## The arithmetic

```
now                                                  18,066
full compaction rewrite, every claim held              -900
                                                    -------
                                                     17,166
Tier 2 entire (displays to the SI)                   -2,350
                                                    -------
                                                     14,816
Tier 1 (the second domain)                           -1,341
                                                    -------
                                                     13,475
Tier 3 items 5 and 6                                 -1,401
                                                    -------
                                                     12,074
```

Reaching the JCIM band requires Tier 1 **and** most of Tier 2 **and** part of Tier 3. Tier 2 alone,
with the compaction pass, lands at 14,816 — still above the corpus maximum of ~13,000, and it costs
no claim at all, only the article's copy of displays the SI prints.

## The recommendation, stated as a choice and not a decision

If the manuscript must enter the JCIM band, the cheapest path in claims is **Tier 2 first**
(-2,350 words, no assertion lost, two checker bindings to move), then **Tier 1** (-1,341, one
assertion lost, and it is the generality claim). Tier 3 is the most expensive per word, because
items 5 and 6 are the only evidence that the substitution damages a *decision* and not just a level.

If the manuscript may run long, Tier 2 alone plus compaction is the honest maximum: everything that
can go without the paper claiming less.
