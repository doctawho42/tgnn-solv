# Amendment 1 to the glycol out-of-sample pre-declaration

Written 2026-08-19, after `PRE_DECLARATION.md` (sha256 `8744f9e1b7311cfc82dcc247b4406b9e4c4c339187cd90342dd519750a580fba`)
was committed and **before any MSE, bound or margin was computed on these rows**. The commit order
is checkable in the history: the declaration lands in `6ca7017`, this amendment in the commit that
carries it, and the producer in a commit after both.

## What was wrong

The declaration fixed the prediction side as

> `g` is the deployed `CosmoSacLayer` evaluated on **VT-2005** σ-profiles for both molecules, at the
> row's own temperature — the same construction as the broad set.

The two halves of that sentence are not the same thing, and one of them is wrong.

**The temperature half is right**, and was checked rather than assumed. The deposited
`g_2002_res` of `paper/si_tables/broad_idac_set_477.csv` varies with the row's temperature: of the
67 pairs that appear at more than one row, all 67 span more than one temperature and all 67 carry
as many distinct `g` values. (`run_b_insuff_decomposition.py` evaluates at a fixed `T_REF = 298.15`,
which is correct for the 298 K matched set that script serves and is not the broad set's
construction.)

**The profile half is wrong.** The broad IDAC set is matched to the **UD** (University of Delaware)
database, not to VT-2005 — the CSV carries `solute_ud_key` / `solvent_ud_key` / `match_rule_*`
columns, matched by InChIKey (466 exact + 11 first-block on the solute side, 476 + 1 on the
solvent). The article says so in its own notation table. An out-of-sample test of an in-sample
margin has to hold the prediction side fixed, so naming VT-2005 would have tested a different
estimator against the same rows.

## The correction

`g` is the deployed `CosmoSacLayer` on **UD** σ-profiles, matched by InChIKey, evaluated at each
row's own temperature under the residual-only convention (`V = None`) — the construction that
produced `g_2002_res` for the broad set.

## What it costs the geometry: nothing

All **95** net-new rows carry a UD profile on both sides under the **exact** InChIKey rule (21/21
solutes, 2/2 solvents). The first-block fallback the broad set also uses is not needed and is not
applied. The row set, its 32 pairs, its solutes, its solvents and its three temperatures are
unchanged from the declaration.

## What is unchanged

The cell (eight equal-count bins, unbiased within-bin variance, row unit, residual-only), the
clustering (pairs), the no-re-selection rule, the single-source limitation, and the three outcomes
with what each licenses — including that a **FAILS** demotes the glycol stratum out of the abstract
and out of Figure 1b's star.

## END OF AMENDMENT
