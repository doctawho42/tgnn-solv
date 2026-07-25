# Amendment 1 to PREREG_blackbox_2026-07-19.md — 2026-07-25

Recorded BEFORE any confirmatory run, from zero-cost local computation on CPU. The amendment is
**adverse** to the study: it withdraws two discipline items as factually wrong, retires the 1a
decision rule, converts 1a to exploratory, and declares 1b/1c not estimable.

All Study-1 numbers below were measured on `checkpoints/proxy/directgnn_tuned.pt` with
`notebooks/data/processed_backup_precorrection/`.

## A1. Item 7 is withdrawn and replaced — all three clauses were wrong

- **"1.70 MAE"** — this checkpoint measures **1.6520** (n = 5826). The 1.702 ± 0.033 figure is the
  three-seed aggregate in `results/e5_sigma_grounding/THREE_SEED_SUMMARY.md:10`, on the **current**
  split (n = 5608). Those checkpoints are not on this machine (the `seed_*/` directories hold
  prediction CSVs only, no `.pt`).
- **"512-d pair representation"** — DirectGNN never reads `cfg.pair_dim`; that key is consumed by
  `TGNNSolv`. The pair representation is `pair_input`, **1556-d** = 4·(3·128)+20, built at
  `src/tgnn_solv/baselines/direct_gnn.py:458-464`. Define **h_BB := pair_input, dim 1556**.
- **"confirmed layer"** — no module matching `*pair*` exists. `return_debug_tensors` is gated at
  `direct_gnn.py:527-529` on descriptor/ionic features and returns `{}` for this checkpoint.
  Extraction is by `register_forward_pre_hook` on `prediction_head`; verified shape (2596, 1556)
  in 11 s on CPU.
- **Split provenance is pinned.** This checkpoint's manifest inputs are `9be883c1/46a1eb61/e08ede23`
  = `notebooks/data/processed_backup_precorrection/`. Every Study-1 number is on that split and may
  **not** be compared with any current-split number (`419b3b2e/974ea451/7871e8a9`; ~76% test
  turnover). All 14 DirectGNN `.pt` files on disk are on that old split, or are subset/smoke runs.

## A2. Item 6's effective n is withdrawn and replaced — measured

Crystal oracle = `results/open_crystal_artifact/open_crystal_solute.csv`, joined on
`solute_smiles`, supervised rows with T < T_m. **Not** the `has_T_m`/`has_dH_fus` mask columns in
the split CSVs, which are stale (current split: 10 supervised train solutes, 1 test).

| split | train | val | test |
|---|---|---|---|
| checkpoint-matched | 152 solutes / 14 366 rows | 7 / 288 | 6 / 221 |
| current (reference only) | 152 / 14 348 | 5 / 196 | 8 / 331 |

Activity oracle = `notebooks/data/raw/idac_expanded.csv`: 14 900 rows / 136 solutes / 3 145 pairs.
Only **11** of 136 solutes are absent from the checkpoint's training molecules; **9** have both
molecules unseen (555 rows / 117 pairs) — C5–C7 cycloalkanes, alkenes, MTBE, 2-ethylfuran,
caprolactam, cyclohexanone oxime. Not drug-like: a held-out activity arm exists but answers a
different question.

**Effective n is held-out clusters, never rows: 13 solutes (crystal, val+test pooled), 9 solutes /
117 pairs (activity).** Φ* is **93.8% between-solute variance**, so 509 rows carry the information
of 13 points.

## A3. The 1a decision rule `R²(model) − R²(raw) ≥ 0.1` is RETIRED

Measured grounds (200-draw solute-permutation null; ridge α by grouped 5-fold CV on the fit split
only):

- **P(null ΔR² ≥ 0.10) = 0.155** (13 held-out solutes), 0.260 (test-only), 0.305 (val-only). The
  gate fires on 15–30% of pure-noise draws, not 5%.
- ΔR² is unbounded below through `R²(raw)`: it measures how badly the raw baseline fails. Swapping
  one arbitrary 20-descriptor RDKit set for another moves ΔR² by **+0.182 — 1.8× the entire bar**.
  The subtrahend is an unregistered analyst choice worth more than the effect.
- Observed ΔR² = +0.417 held-out. It clears the bar. It means nothing.

This is the same pathology the fix-g pre-registration had (`PREREG_fix_g_AMENDMENT_2026-07-25.md`):
a decision band that a trivial or arbitrary choice can satisfy.

**Replacement, gated on `R²(model)` alone against a solute-permutation null:**

- **GO** (crystal term decodable): held-out `R²(model) ≥ 0.30` **and** permutation p ≤ 0.01
  (≥ 1000 draws) **and** min over drop-one-solute jackknife > 0. The 0.30 comes from the measured
  null: p95 = +0.158, max over 200 draws = +0.267.
- **KILL** otherwise — licensing only *"not distinguishable from chance at n = 13"*, an upper
  bound, **not** "the box contains no crystal structure". Minimum detectable effect at this n is
  R² ≈ 0.30; any true effect below that is invisible and must be reported as such.
- `R²(raw)` is still reported, as a **level** beside `R²(model)`, never as a subtrahend.
- The regularisation protocol (α grid 1e-1…1e7, grouped 5-fold by solute, selected on the fit split
  only) is fixed here and applied identically to model, raw and every null draw. The verdict is
  known to move with α, so α may not be chosen after seeing the target.

## A4. Control ladder — mandatory; every reported probe number carries all eight

1. Solute-permutation null, ≥ 1000 draws, α re-selected per draw; report p, null median, p95.
2. Raw-feature reference as a level, under **two** independent descriptor sets; their spread is the
   irreducible arbitrariness of the baseline.
3. Molecule-blind constant predictor, held-out R².
4. Random-target selectivity control (Gaussian target, same solute/row structure).
5. Drop-one-cluster jackknife: range, sd, and sign flips.
6. Leverage: share of held-out SSE carried by the top solute and top-3 (measured here: 20.9% and
   51.3% — report, do not hide).
7. Capacity ladder: ridge (lead) **and** MLP; MLP-only signal is reported as probe-manufactured.
8. Effective n stated as clusters, with the between-cluster variance fraction of the target.

## A5. Studies 1b and 1c are NOT ESTIMABLE and are struck from the program

Not underpowered — **unpurchasable**. Crystal-oracle ∩ activity-oracle = **25 solutes, none of them
absent from the checkpoint's training corpus, and the 25 *are* the common-solvent set**: water,
C1–C4 alcohols, acetone, MeCN, AcOH, THF, cyclohexane, C6–C14 alkanes, toluene, chloroform,
chlorobenzene, benzene, pyridine, naphthalene, biphenyl, benzaldehyde.

Excluding all 25 from training removes **73 412 / 111 035 = 66.1%** of training rows (61.3% of
supervised rows). Only 5 appear solely as solutes (tridecane, tetradecane, benzaldehyde, biphenyl,
naphthalene); holding just those out costs 168 rows (0.15%) and leaves **n = 5 molecules / 16 IDAC
pairs**.

So 1b's *mandatory* `corr(Φ*, ln γ*)` confound control has no held-out sample and cannot acquire
one: the only molecules carrying both measured oracles are the ones a solubility model cannot be
trained without. 1c consumes 1b's subspaces and dies with it.

**This finding replaces 1b/1c in the program.** It is itself a result about the pre-registration's
"distinctive asset" claim (line 14, "an external oracle for every term"): the oracles exist, but
they are **structurally disjoint on the held-out axis**, and their intersection is the one molecule
class that cannot be held out.

## A6. Blinding is broken on 1a for this checkpoint

Four independent pre-spend audits each computed Study 1a's headline statistic on
`checkpoints/proxy/directgnn_tuned.pt`. Now in the record: held-out R²(model) = +0.135 (p = 0.080),
test-only +0.220 (p = 0.080), ΔR² +0.417 / +0.187.

**Study 1a on this checkpoint is EXPLORATORY from this point** and must be labelled so in any
write-up. A confirmatory 1a requires a checkpoint whose probe numbers no audit has seen — the
`e5_sigma_grounding` current-split seeds (42/43/44). Those weights are not on this machine; only
prediction CSVs are. Fetching them would also satisfy item 6's three-seed requirement, which no
local artifact can.

## A7. Order changed

Study 2 (temperature structure) does not depend on 1b and is unaffected by A5; it is promoted ahead
of Study 3. **Study 3 is struck by its own precondition** ("runs ONLY if Study 1 yields an activity
subspace" — A5 establishes that no held-out activity subspace is estimable). **Study 4 becomes the
program spine**, as its own fallback clause anticipated.

## The honest ceiling

The strongest sentence Study 1 could print, with everything going as well as the data allow:

> On a frozen DirectGNN baseline (test MAE 1.65), a ridge probe of the 1556-d pair representation
> recovers the measured ideal-solubility term Φ*(mol, T) on 13 held-out solutes with R² = 0.13
> (p = 0.08 against a solute-permutation null; drop-one-solute range −0.15 to +0.27), so at the
> sample size the external oracles permit we cannot distinguish the black box's crystal-term
> decodability from chance; the corresponding crystal-versus-activity separability test is not
> estimable at any sample size in this corpus, because the only 25 molecules carrying both a
> measured crystal and a measured activity oracle are the common solvents, which supply 66% of the
> model's training rows and therefore cannot be held out of it.

The negative is a **bound, not a point**: at n = 13 the minimum detectable R² is ≈ 0.30, so "the box
does not encode Φ*" is a claim this design cannot make — only "an effect of R² ≥ 0.30 would have
been seen, and was not".
