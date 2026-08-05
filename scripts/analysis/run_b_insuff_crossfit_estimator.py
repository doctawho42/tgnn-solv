#!/usr/bin/env python3
r"""PRE-DECLARATION: a cross-fitted B_insuff^up for the stratified map, declared before it is run.

Nothing in this file has been scored.  It is written and staged in git BEFORE any cross-fitted
margin exists, and it fixes -- in advance, in one place -- the estimator, the row set, the folds,
the reporting rule, the rule for which estimator the paper headlines, and the three verdicts.
The scoring pass is a LATER phase and MUST NOT alter anything above the `main' below; if the
estimator has to change, that is a new declaration in a new file, with the reason recorded, and
this one is reported as having been abandoned.

==================================================================================================
WHY THIS EXISTS
==================================================================================================

The instrument splits a fixed closure's error (Prop. `decomp'):

    MSE = E[(m - g(z*))^2]  =  B_insuff + B_closure,    B_insuff = E[Var(m | z*)],

and reports the margin  MSE - 2 B_insuff^up,  a lower bound on  B_closure - B_insuff.  Today
B_insuff^up is a COARSENING bound: the within-bin variance of m over 8 equal-count bins of the
scalar g(z*), Bessel within-bin variance (the manuscript's headline cell).  Because bin(g(z*)) is
a function of a function of z*, the law of total variance gives

    E[Var(m | bin(g(z*)))]  >=  E[Var(m | g(z*))]  >=  E[Var(m | z*)] = B_insuff,

so the bound is valid, and loose by an amount that grows with how coarse the partition is.

That looseness is not a nuisance in this deposit -- it is the reported structural finding.  Across
the 59 strata of `results/b_insuff/stratified_map.json' the coarsening bound is nearly FLAT and
LARGE while the error it is subtracted from is not:

    res convention:  range(B_insuff^up) = 0.1073   vs   range(MSE) = 2.1627   (ratio 20.2)
    full convention: range(B_insuff^up) = 0.0581   vs   range(MSE) = 2.3534   (ratio 40.5)

and the deposit already names the cause in `what_bounds_b_insuff': the level of B_insuff^up here
"is set by within-bin heterogeneity of the binning statistic, not by label noise", the direct
pair-conditional variance E[Var(m | pair)] being 0.0003-0.08 per stratum (0.0457 on the whole
broad set, 67 repeating pairs) against a whole-set coarsening bound of 0.482 (full) / 0.697 (res).
One to two orders of magnitude of slack, all of it estimator, none of it chemistry.

The consequence is the shape of the current result: only 15 of the 59 strata are boundable at the
fixed cell, the margins that exist are small, and the single surviving finding sits near the 90th
percentile of its own chemistry-blind multiplicity null (D = +2.0364, p = 0.1005).

The paper's OTHER domain does not use a coarsening.  In the pKa closure
(`scripts/analysis/run_pka_real_decomposition.py::_binsuff_within_scaffold'), B_insuff^up is the
out-of-fold residual mean square of a cross-fitted random forest of m on z*.  If a cross-fitted
regressor predicts m from z* better than an 8-bin histogram of a scalar summary of z* does, the
bound tightens, and since margin = MSE - 2 B_insuff^up, EVERY margin in the map grows at once.

==================================================================================================
WHY THIS IS A REAL RISK AND NOT A FREE WIN -- stated before the fact, not after
==================================================================================================

  * The regressor may LOSE to the bins.  z* is 102-dimensional here and the honest folds hold out
    whole clusters, so rhat must extrapolate to a pair it has never seen.  The one place this has
    already been measured -- the n=60 corner in `results/b_insuff/decomposition.json' -- the RF
    out-of-fold MSE is 0.5646 against a coarsening of 0.5295 (full) and 0.6180 (res): the RF LOSES
    under one convention and wins under the other, and it was fitted there with ROW-level folds,
    i.e. the leaky, optimistic version of itself.  A grouped-fold RF starts from behind that.
  * A tighter bound raises EVERY margin, including those of strata that currently fail, so the
    chemistry-blind multiplicity null moves too.  A richer map is a gain only if the null moves
    less than the map does.  Both are therefore re-run, and the verdict is stated in terms of the
    null p-values, not the count.
  * The paper already prints the neighbouring trap: the MINIMUM of two valid bounds is valid in
    population and biased low in finite samples.  Cross-fitting is the standard remedy for that
    bias and the entire case for this estimator rests on it, so the cross-fitting must be done
    properly or this is estimator shopping with extra steps.  Hence: the fold rule is fixed here,
    the per-cell minimum is FORBIDDEN here, and the headline is chosen once, globally, by a gate
    that never reads a margin.

==================================================================================================
1. THE ESTIMATOR
==================================================================================================

1.1 THE FEATURE VECTOR z*.  The closure's own argument list and nothing else:

        z* = [ sigma_solute(51), A_solute, sigma_solvent(51), A_solvent, T_K ]        (105 dims)

    read from the deposited VT-2005 artifact `results/sigma_profile_artifact/sigma_profiles.csv'
    (columns sigma_p_0..sigma_p_50 and sigma_area), the same artifact
    `run_published_idac_closure_check.py' scored g on, matched by FULL InChIKey with a first-block
    fallback -- the match rule the set was built under, recorded per row in `match_rule_solute' /
    `match_rule_solvent'.

    The cavity volume v_cosmo is DELIBERATELY EXCLUDED, and this is a validity requirement, not a
    convenience.  v_cosmo enters only the Staverman-Guggenheim combinatorial term, so it is an
    argument of the `full' closure and NOT of the deployed residual-only `res' closure.  Giving it
    to the regressor would estimate E[Var(m | z*_res, V)] <= E[Var(m | z*_res)] under `res' -- a
    quantity that is not an upper bound on the res-convention B_insuff, and subtracting twice it
    would inflate the margin invalidly.  The rule is therefore: THE FEATURE SET IS THE
    INTERSECTION OF THE TWO CONVENTIONS' ARGUMENT LISTS.  Conditioning on less than z* is safe
    (tower property: it can only raise the bound); conditioning on more is not.  Under `full' this
    makes the estimator conservative by exactly the information in v_cosmo, and that is the side
    to err on.

    Nothing outside z* is ever a feature: not source_doi, not journal, not method, not the
    molecule identity beyond what the profile carries, not m, not g, not the stratum label.

    Consequence, stated so it can be checked: B_insuff^cf depends only on (m, z*) and is therefore
    IDENTICAL under `full' and `res'.  The two conventions' cross-fitted margins differ only
    through MSE.  The deposited decomposition asserts the same convention-independence for its RF
    estimate; if the scoring pass ever prints two different B_insuff^cf for the two conventions,
    the implementation is wrong.

1.2 THE REGRESSOR.  Fixed now at the pKa domain's setting, unchanged, untuned:

        sklearn.ensemble.RandomForestRegressor(n_estimators=300, min_samples_leaf=5,
                                               random_state=0)

    the exact call of `run_pka_real_decomposition._oof_mse'.  The choice is made for cross-domain
    consistency, not for performance: the paper's second domain already headlines this estimator,
    and using a different one in the solubility domain would be indefensible.  No grid search, no
    early stopping, no feature selection, no per-stratum hyperparameters.

    ONE alternative family, Ridge(alpha=1.0) on standardised z*, is computed and printed as a
    sensitivity -- because a linear map is the one regressor that cannot overfit 102 dims at
    n=473 the way a forest can, and its absence would be a hole.  It is a SENSITIVITY.  It never
    headlines, under any outcome.

1.3 CROSS-FITTING.  The paper's unit is a cluster, and folds that split a cluster leak.

    PRIMARY (headline): 5-fold `sklearn.model_selection.GroupKFold' with
    groups = pair_key = "solute_smiles|solvent_smiles".  Deterministic, no shuffle, no seed.

    Why the pair and not the row: z* is a deterministic function of the pair up to T, so replicate
    rows of one pair -- across temperatures and across publications -- carry the SAME z* and
    correlated label error.  A row-level fold puts a row's own replicates in rhat's training set,
    rhat then reads the held-out row's own label through them, the cross term goes negative and
    the "bound" can fall BELOW B_insuff.  That is the leak, and it is the one the corner's
    deposited RF number has in it.

    CONSERVATIVE (reported alongside, never headlines): GroupKFold on `source_doi',
    n_splits = min(5, n_sources).  This additionally removes the shared-laboratory bias channel --
    replicates of one publication share a systematic error that is not independent across rows --
    and, because a publication tends to measure related chemistry, it also approximates a
    chemistry-held-out regime.  It is the stricter reading of "clustered".

    n_splits = min(5, n_groups) in both schemes; if n_groups < 3 the cross-fitted estimator is
    UNDEFINED and the cell prints the coarsening alone.

    SCOPE OF THE FIT.  rhat is fitted GLOBALLY -- once per (set, unit, fold scheme) on all rows of
    that set -- and the per-stratum quantity is the mean of the fixed out-of-fold squared
    residuals over that stratum's rows.  Validity is pointwise (Sec. 5) and therefore survives
    restriction to any subset defined without reference to the labels, which every stratum is by
    the map's own stratification rule (a pure function of SMILES).  Fitting within each stratum
    instead would hand a 40-row stratum a 102-dimensional regression, which is the version of this
    experiment designed to fail; it is computed and printed as a sensitivity, and never headlines.

    Fold assignment is made ONCE per (set, unit, scheme) and is then held fixed across every
    stratum, both conventions, the leave-one-source-out deletion test, the bootstrap and every
    draw of the multiplicity null.

    rhat is NOT REFITTED inside the leave-one-source-out deletion test.  The deletion test asks
    whether the SIGN of a margin survives removing a publication's rows from the EVALUATION set;
    refitting would confound that with a change of estimator.  The source-grouped fold scheme is
    the variant in which each row's own publication is already absent from rhat's training data,
    and it is reported for exactly this reason.

1.4 THE QUANTITY, per cell = (stratum x unit in {row, pair} x convention in {full, res}):

        B_insuff^bin = lotv(g, m, n_bins=8, ddof=1)                        [UNCHANGED, existing]
        B_insuff^cf  = mean_i (m_i - rhat_{-fold(i)}(z*_i))^2              [NEW]
        margin^bin   = MSE - 2 B_insuff^bin
        margin^cf    = MSE - 2 B_insuff^cf
        delta        = B_insuff^bin - B_insuff^cf     (> 0 iff the cross-fit is the tighter bound)

    plus, for the headline margin, the SAME two-way (solute x solvent) cluster bootstrap of
    `run_b_insuff_estimator_grid.two_way_margin_boot' -- 3000 draws, 90% interval -- with the
    within-draw B_insuff recomputed as the mean of the FIXED per-row out-of-fold squared residuals
    over the resampled rows.  rhat is held fixed across bootstrap draws (it is not refitted per
    draw).  This is standard and it is ANTI-conservative: it omits the estimator's own sampling
    variability, so the cross-fitted interval is narrower than a fully re-fitted one would be.
    Declared here rather than discovered later.

1.5 THE ROW SET.  The broad IDAC set restricted to rows whose BOTH profiles resolve in the
    deposited artifact: 473 of 477.  The 4 dropped rows are the three solutes with no VT-2005
    profile -- 4-vinylcyclohexene (BBDKZWKEPDTENS), 1,7-octadiene (XWJBRBSPAODJER), triethylamine
    (ZMANZCXQSJIPKH) -- spread over three publications.  The corner set (n=60) is fully covered.

    Both estimators are computed on the SAME rows, always.  THREE maps are deposited so that the
    restriction and the estimator are never confounded:

        (i)   the 477-row coarsening map                 -- already on disk, untouched
        (ii)  the 473-row coarsening map                 -- (i) -> (ii) isolates the 4-row loss
        (iii) the 473-row cross-fitted map               -- (ii) -> (iii) isolates the estimator

    Every verdict below is read off (ii) -> (iii).  A change that appears in (i) -> (ii) belongs to
    the restriction and is reported as such.

==================================================================================================
2. THE COMPARISON
==================================================================================================

The cross-fitted bound is reported ALONGSIDE the 8-bin coarsening, never instead of it.  Both
numbers, both margins and their difference are printed for EVERY cell of the map -- the 59 strata,
both units, both conventions, both sets, the boundable and the unboundable, the cells that favour
the paper and the cells that do not -- in the deposited JSON and in the CSV.  No cell reports one
estimator only.  The per-cell MINIMUM of the two is never formed, never printed and never
mentioned as a result: it is valid in population, biased low in finite samples, and the paper
already says so in print.

==================================================================================================
3. WHICH ONE THE PAPER HEADLINES -- FIXED NOW
==================================================================================================

THE RULE.  The cross-fitted estimator headlines UNCONDITIONALLY -- every cell, both sets, both
units, both conventions -- provided it passes the validity gate of Sec. 3.1, which never reads a
margin, an MSE, a g or a stratum label.  If the gate fails, the headline reverts to the 8-bin
coarsening FOR THE WHOLE MAP and the cross-fitted numbers are deposited as a sensitivity only.
The decision is ONE binary decision taken ONCE for the entire deposit.  It is never taken per
cell, per stratum, per unit, per convention or per set.

WHY UNCONDITIONALLY, AND NOT "WHICHEVER IS SMALLER".  Per-cell minimisation over two valid bounds
is the biased-low estimator the paper already disowns; taking it here would require a
finite-sample correction that I would have to invent after seeing the numbers, which is the
failure mode this declaration exists to prevent.  Choosing globally and in advance removes the
per-cell selection entirely, so there is no selection bias left to correct.

WHY THE CROSS-FIT AND NOT THE COARSENING.  Both are valid upper bounds.  They differ in the
slack: the coarsening's slack is the information destroyed by binning a scalar summary of a
102-dimensional input into 8 buckets, which is not estimable from these data and which the deposit
has already measured to be one to two orders of magnitude above the replicate floor; the
cross-fit's slack is the regressor's mean squared approximation error, which is at least
diagnosable -- gate G2 below is exactly a test that it is finite and beneficial.  Preferring the
bound whose looseness can be interrogated over the bound whose looseness cannot is a reason that
does not depend on which way the numbers come out.

WHAT THIS COMMITS ME TO.  If the cross-fit is LOOSER than the coarsening, the headline margins
SHRINK, cells that are certified today lose their certification, and the map gets poorer.  That
outcome is reported as the result, in the paper, with the same prominence a gain would have had.
It is verdict L1 below.

3.1 THE VALIDITY GATE.  Evaluated once, on the broad set at the row unit under the primary fold
    scheme, from (m, z*, pair_key, T) only.  No g, no MSE, no margin, no stratum enters it.

    G1  FOLD INTEGRITY.  No pair_key occurs in both the training and the test part of any fold.
        Asserted exactly, in code, and the assertion must hold; a violation is a bug, not a result.

    G2  NON-DEGENERACY.  The global out-of-fold R^2 of rhat on m, 1 - B_insuff^cf / Var(m), must
        be > 0.  A regressor that cannot beat the constant mean of m out of fold is reporting the
        marginal variance in disguise, and such a "bound" must not headline anything.

    G3  REPLICATE-FLOOR SANITY.  The global B_insuff^cf must not fall BELOW the deposited direct
        pair-conditional variance E[Var(m | pair)] = 0.0457 (67 repeating pairs, whole broad set).
        Since z* is a function of the pair, that quantity IS B_insuff on the repeating
        subpopulation, inflated by the within-pair temperature spread it also absorbs; a
        cross-fitted bound below it indicates that the folds are leaking despite G1.  CAVEAT,
        stated now: it is a subpopulation estimate, not a global lower bound, so G3 is a leak
        DIAGNOSTIC and not a proof of validity.  It is a gate anyway, because a number that fails
        it should stop the campaign rather than be explained.

==================================================================================================
4. THE VERDICTS -- WIN, LOSS, INCONCLUSIVE
==================================================================================================

The baseline is what is on disk today, under the coarsening, and is quoted here so it cannot be
restated later (`results/b_insuff/map_multiplicity_null.json', 59 strata, 2000 draws):

        A  cells admissible                                    35        null p = 0.548
        B  strata admissible in all four cells                  6        null p = 0.0115
        C  DISTINCT ROW SETS admissible AND positive             2        null p = 0.286
        D  largest headline-cell margin among them          2.0364        null p = 0.1005
        n_maximal                                                1

WIN -- all three of:
    W1  the bound tightens globally: B_insuff^cf < B_insuff^bin on the same 473 rows, broad set,
        row unit, primary fold scheme;
    W2  the map gains: C_cf > 2, by the UNCHANGED admissibility rule and the UNCHANGED maximality
        reduction;
    W3  the null does not move proportionally: the multiplicity null, re-run as it stands with
        B_insuff computed by the cross-fitted estimator, returns p(C >= C_cf) < 0.286 AND
        p(D >= D_cf) < 0.1005.

LOSS -- any one of:
    L1  W1 fails.  B_insuff^cf >= B_insuff^bin: the bound does not tighten, the margins do not
        grow, and under the headline rule of Sec. 3 the map is poorer than the deposited one.
    L2  W1 holds but C_cf <= 2: the tightening buys no certification.
    L3  W1 and W2 hold but BOTH re-run null p-values fail to improve (p_C >= 0.286 and
        p_D >= 0.1005): the extra certifications are chance capacity the estimator handed to the
        search, not evidence.

INCONCLUSIVE -- any one of:
    I1  the validity gate fails (G1, G2 or G3): the estimator never became admissible and nothing
        is scored;
    I2  W1 and W2 hold and EXACTLY ONE of the two null p-values improves;
    I3  the primary (pair-grouped) and conservative (source-grouped) fold schemes disagree on the
        SIGN of the change in C.

==================================================================================================
5. THE VALIDITY ARGUMENT
==================================================================================================

For a row i whose fold excludes it, and with rhat therefore independent of row i's label given
z*_i,

    E[(m_i - rhat(z*_i))^2 | z*_i, rhat]
        = Var(m | z*_i)  +  (E[m | z*_i] - rhat(z*_i))^2
        >= Var(m | z*_i),

the cross term vanishing because E[m - E[m|z*_i] | z*_i, rhat] = 0.  Averaging over rows,

    E[(m - rhat(z*))^2]  =  B_insuff  +  E[(E[m|z*] - rhat(z*))^2]  >=  B_insuff,

with slack exactly the regressor's mean squared approximation error.  Cross-fitting is what makes
the independence hold; fitted in sample, the cross term is negative and the "bound" can fall below
B_insuff.  Hence margin^cf = MSE - 2 B_insuff^cf is a lower bound on B_closure - B_insuff by the
same one-sided argument the coarsening version uses, and a positive margin^cf certifies
B_closure > 0 exactly as before.  A NON-positive margin remains a failure to separate and not a
certified reversal -- the instrument is one-sided in both estimators, and `licenses' per stratum
says so unchanged.

IT IS NOT AN UPPER BOUND WHEN:

  (a) THE FOLDS LEAK.  Rows sharing a cluster carry correlated label error: replicates of one pair
      (identical z*, different T or different laboratory) and rows of one publication (shared
      systematic bias).  If such a row is in training, rhat is correlated with the held-out row's
      own error, the cross term is negative, and the estimate falls below B_insuff.  Addressed by
      pair-grouped folds (primary) and source-grouped folds (conservative variant); tested by G1
      and diagnosed by G3.
  (b) THE FEATURES ARE FINER THAN z*.  Anything not a function of the closure's argument list --
      source, method, molecule identity, or v_cosmo under the residual-only convention -- makes
      the estimand E[Var(m | z*, extra)] <= B_insuff.  Addressed by Sec. 1.1.
  (c) THE ESTIMAND IS MISMATCHED IN T.  g is evaluated at each row's T on this set (273-403 K), so
      the decomposition conditions on (z*, T) and the regressor must too.  Dropping T would leave
      a still-valid but looser bound; adding a T-derived feature the closure does not use would
      break it.  T is in, alone, unadorned.
  (d) THE SELECTION IS PER CELL.  The minimum of two valid bounds is valid in population and
      biased low in finite samples.  Forbidden in Sec. 2; the headline is chosen once, globally,
      by an outcome-blind gate.
  (e) IT IS READ AS A GUARANTEE ON ONE STRATUM.  The bound is on an expectation.  A small
      stratum's sample mean of out-of-fold squared residuals fluctuates and can sit below B_insuff
      by chance; the two-way cluster bootstrap carries that, subject to the fixed-rhat caveat of
      Sec. 1.4.

==================================================================================================
6. WHAT IS NOT CHANGED
==================================================================================================

  * THE ADMISSIBILITY RULE, verbatim: a stratum may be stated only if it is (a) boundable -- n >= 40
    -- and (b) sign-stable under deletion of each single contributing publication, in all four
    unit x convention cells, with a single-publication stratum failing (b) by non-testability and a
    deletion that leaves fewer than 2 x n_bins rows failing (b) by undefinedness.  The strict
    variant is deposited as before.  n >= 40 was justified mechanically by "8 equal-count bins x
    >= 5 rows"; under a cross-fitted bound that justification lapses and the threshold becomes
    merely conservative.  IT IS KEPT UNCHANGED ANYWAY.  Relaxing it would be a second lever pulled
    in the same experiment, and the gain could not then be attributed.
  * THE STRATIFICATION RULE, the 59 strata, the two axes, the three granularities, the two units,
    the two conventions, the maximality reduction and the overlap table.
  * THE MULTIPLICITY NULL: the same chemistry-blind permutation of label triples over molecules,
    the same 2000 draws, the same four statistics, the same code path -- re-run with B_insuff
    computed by whichever estimator headlines.  Implementation note that follows from Sec. 1.3:
    the permutation moves only the stratum LABELS, never m, z*, the pair or the source, so the
    out-of-fold residuals are invariant across draws and the null re-groups the same fixed per-row
    residuals, exactly as it re-bins the same fixed rows today.
  * THE BOOTSTRAP: two-way solute x solvent cluster, 3000 draws, 90% interval, same seeds from
    `stable_seed'.

==================================================================================================
7. WHAT WILL NOT BE ADDED AFTER THE NUMBERS ARE SEEN
==================================================================================================

No further regressor family, no hyperparameter change, no third fold scheme, no alternative
feature set, no bin count, no re-weighting, no stratum, no exclusion.  The families, schemes and
scopes named above -- RF (headline), Ridge (sensitivity); pair-grouped (headline), source-grouped
(reported); global fit (headline), within-stratum fit (sensitivity) -- are the complete list, and
the headline is already assigned within each.  If the scoring pass shows the estimator to be
unusable, the outcome is I1 and the campaign stops; it is not repaired.

==================================================================================================
REPRODUCTION
==================================================================================================

    KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src \
        python scripts/analysis/run_b_insuff_crossfit_estimator.py            # prints this config
    # the scoring pass is added below `main' in a later phase and changes nothing above it.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

ROOT = Path(__file__).resolve().parents[2]

# ------------------------------------------------------------------------------------------------
# The declaration, pinned as values so the hyperparameters are not prose.  Do not edit these in the
# scoring phase; a change here is a new declaration in a new file.
# ------------------------------------------------------------------------------------------------
BROAD = ROOT / "paper" / "si_tables" / "broad_idac_set_477.csv"
CORNER = ROOT / "paper" / "si_tables" / "vt2005_matched_set_60.csv"
SIGMA = ROOT / "results" / "sigma_profile_artifact" / "sigma_profiles.csv"

SIGMA_BINS = 51                     # sigma_p_0 .. sigma_p_50
FEATURES = "sigma_solute(51) + sigma_area_solute + sigma_solvent(51) + sigma_area_solvent + T_K"
EXCLUDED_FEATURE = "v_cosmo"        # combinatorial-only: see Sec. 1.1
RF_KWARGS = {"n_estimators": 300, "min_samples_leaf": 5, "random_state": 0}   # == the pKa domain
RIDGE_ALPHA = 1.0                   # sensitivity only, never headlines
N_SPLITS = 5
PRIMARY_GROUP = "pair_key"          # "solute_smiles|solvent_smiles"
CONSERVATIVE_GROUP = "source_doi"
FIT_SCOPE = "global"                # per (set, unit, scheme); within-stratum is a sensitivity

N_BINS = 8                          # the coarsening, unchanged, reported alongside everywhere
DDOF = 1
MIN_BOUNDABLE = 40                  # unchanged; see Sec. 6
N_BOOT = 3000
N_NULL_DRAWS = 2000

GATE = {"G1_no_pair_across_folds": True,
        "G2_global_oof_r2_gt": 0.0,
        "G3_not_below_pair_conditional_var": 0.0457}

BASELINE = {"A_cells_admissible": 35, "A_null_p": 0.548,
            "B_strata_all_four_cells": 6, "B_null_p": 0.0115,
            "C_distinct_row_sets": 2, "C_null_p": 0.286,
            "D_max_margin": 2.0364272362273272, "D_null_p": 0.1005,
            "n_maximal": 1}

ROW_SET = {"broad_rows_total": 477, "broad_rows_with_zstar": 473,
           "dropped_solutes": ["BBDKZWKEPDTENS-MRVPVSSYSA-N",     # 4-vinylcyclohexene
                               "XWJBRBSPAODJER-UHFFFAOYSA-N",     # 1,7-octadiene
                               "ZMANZCXQSJIPKH-UHFFFAOYSA-N"],    # triethylamine
           "corner_rows": 60, "corner_coverage": "complete"}


def main() -> int:
    print(__doc__)
    print("PINNED CONFIGURATION")
    for k, v in (("features", FEATURES), ("excluded", EXCLUDED_FEATURE), ("rf", RF_KWARGS),
                 ("ridge_alpha", RIDGE_ALPHA), ("n_splits", N_SPLITS),
                 ("primary_group", PRIMARY_GROUP), ("conservative_group", CONSERVATIVE_GROUP),
                 ("fit_scope", FIT_SCOPE), ("coarsening_cell", (N_BINS, "Bessel", MIN_BOUNDABLE)),
                 ("gate", GATE), ("baseline", BASELINE), ("row_set", ROW_SET)):
        print(f"  {k:22s} {v}")
    print("\nNO MARGIN IS COMPUTED IN THIS PHASE.  The scoring pass is a later phase and must not "
          "alter anything above `main'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
