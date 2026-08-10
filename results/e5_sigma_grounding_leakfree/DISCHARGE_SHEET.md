# Discharge sheet for the §2.2 / `sec:si-repro` leak-free re-run pre-commitment

**Built 2026-08-10 at HEAD `1df7ccd`, with seeds 42/43/44 landed and 45/46 in training.**
This sheet is *derived from* the display inventory that lives at `paper/sections/SI.tex`
`\label{sec:si-repro}` — resolve it through the .aux; the number it prints at has already moved once, on 2026-08-10. **That inventory is settled and this sheet does
not amend it.** Where this sheet records something the inventory does not, it says so in the
`WATCH` section at the end and takes no action there — the inventory may not be edited once the
five-seed numbers exist, and this sheet exists so that nothing *has* to be.

Every label below was resolved off `paper/grounding_paradox.aux` and `paper/grounding_paradox_si.aux`
(built 2026-08-10 01:51, against `sections/SI.tex` mtime 01:50 — the `.aux` is current). Every printed
page was resolved off the compiled PDFs (`pdftotext`, page N of the article = printed page N; page N of
the SI = printed S-N). **No display below is addressed by its printed number** — printed numbers drift,
and the inventory's own fourth run recorded an S-number that had drifted three places.

Article 33 pp. SI S-84. The sheet has **36 rows**.

---


> **Addresses in this sheet are LABELS, not printed section numbers.** They were numbers until
> 2026-08-10, when merging the two pKa sections removed a section ahead of the pre-commitment: five
> occurrences of "§S9" then pointed at the black-box probe instead of at the protocol they name, and
> the Supporting Information split §S3 into twelve subsections under them. Nothing had moved that a
> reader would notice; the sheet had simply stopped meaning what it said. Resolve a label through
> `paper/grounding_paradox_si.aux` when you need its printed number, and do not write the number down.


## 0. Preconditions — two of them are currently blocking

Nothing in §1 can be discharged until these are true. Both are facts about this working copy, checked
2026-08-10.

**P0.1 — the leak-free per-row prediction CSVs are not here.**
`results/e5_sigma_grounding_leakfree/seed_{42,43,44}/` holds only
`{ungrounded,grounded_a}_predictions.summary.json` and `comparison_both_arms.json`. There is **no
`*_predictions.csv`**. Every row below whose artifact is a per-row CSV — the parity figure, the
ranking tables, the row-class split, the chemistry maps, the `log10 S` RMSE column of the baselines
table, the per-row deposit audit — cannot run until the CSVs are fetched from the compute host.

**P0.2 — `checkpoints/e5_leakfree/` does not exist here.**
`certify_leakfree_rerun.py` takes `--manifest-root checkpoints/e5_leakfree`, and that directory is
where `scripts/train.py` writes `<arm>_seed<N>.manifest.json` — the files that carry the stream
SHA-256 beside the three split SHA-256s. Without them **criteria 1–4 of the certificate cannot be
evaluated at all**, and criteria 1–4 are the whole evidential basis of disposition D (rows 30–33).
The script's own docstring says: *"If the GPU host is torn down without copying that directory back,
criteria 1-4 cannot be checked at all; fetch it with the results."*

**P0.3 — the σ-oracle arm of the re-run does not exist yet, at any seed.**
The re-run trains two arms. The third enrolled arm — the σ-oracle — is the grounded checkpoint
re-evaluated with ζ\* substituted, and it is produced by **step 3** of
`scripts/experiments/run_e5_leakfree_followups.sh`, which has not been run. Rows 8, 9, 10, 12, 13, 15,
17, 23, 24 and 34 all carry an oracle value and are blocked on it. It needs the checkpoints
(`grounded_a_seed<N>.pt`), i.e. P0.2, and it is an inference pass, not a training run.

**P0.4 — the stream file.** `notebooks/data/processed_sigma_aux_stream_clean/sigma_train.csv` must be
the build the runs consumed, so the leak check is recomputed here rather than trusted. The
`GATE_A1_RECORD.md` certification at three seeds was run **after** those three seeds finished (the
2026-08-08 relaunch called `run_e5_sigma_grounding.sh` directly and skipped
`scripts/cloud/gcp_a1_leakfree.sh`); the 45/46 launch runs it first.

**The fetch, then the four follow-up steps, are one command:**

```bash
# after copying back results/e5_sigma_grounding_leakfree/seed_*/ , checkpoints/e5_leakfree/ ,
# and notebooks/data/processed_sigma_aux_stream_clean/sigma_train.csv
SEEDS="42 43 44 45 46" bash scripts/experiments/run_e5_leakfree_followups.sh
```

which runs, in order: (1) `certify_leakfree_rerun.py` → `provenance_certificate.json`;
(2) `verify_perrow_deposit.py` → `perrow_deposit_audit.json`; (3) the evaluation-only substitution on
each clean checkpoint, then `run_e5_comparison.py` re-aggregating all three arms onto one lock per
seed; (4) the n=44 profile probe with piperidine excluded.

**Read before quoting step 4.** Its own header: the 51±2 % departure and the 4.1±0.5× transfer of
§3.3 were measured on a *different* set of runs (σ head left unfrozen); step 4's arms carry
`--freeze-sigma-head-during-sle`. Step 4 does **not** reproduce those two numbers and a value from it
must not be set against them. Rows 5 (mechanism block) and 6 are unaffected by this: the mechanism
rows of Table S2 are outside the boundary.

---

## 1. The rows

Legend for **DISPOSITION**: **R** = regenerated from the five-seed arms; **K** = keeps its published
value with the five-seed one printed beside it and the caption saying so; **D** = a caveat passage
removed/rewritten in all three branches. **BRANCH**: which of the three branches changes the row —
`1|2|3` means all three (the inventory fixes the *scope of replacement* in all three branches alike);
`2` or `2,3` marks the wording changes the decision rule alone triggers.

---

### Row 1 — the abstract's seed count and its leak-free clause
- **Inventory name / label:** *"the abstract's seed count and its leak-free clause, which carry no value of their own"*. No `\label` (achemso `abstract` environment).
- **Prints:** `paper/grounding_paradox.tex` **L266–288** (clause at **L272**); printed **p. 1**.
- **Prints now:** `lowers mean absolute error, over three seeds, not certified leak-free`. No numerals anywhere in the abstract, by standing rule (three rules at L267–288).
- **Disposition:** **R** — "over three seeds" → five; the leak-free clause goes.
- **Artifact:** `results/e5_sigma_grounding_leakfree/provenance_certificate.json` (the clause), and the seed list itself.
- **Command:** *none produces this prose.* It is hand-edited. The only mechanical gate is the word ceiling: `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/wc_abstract.py` — take the number the script prints, under its third rule ("as rendered"), ceiling 250.
- **Branch:** `1|2|3` for the seed count and the clause. Under **branch 2** the abstract's *claim* is also rewritten (supervision recorded as unresolved).

### Row 2 — §3.1 entire
- **Inventory name / label:** *"§\ref{sec:paradox} entire … the per-seed gains and the seed-42 values included wherever they now print"* — `\label{sec:paradox}`.
- **Prints:** `paper/grounding_paradox.tex` **L508–551** (heading L508, label L509); printed **pp. 12–13**.
- **Prints now:** `5608` of `8103`; ungrounded `2.043\pm0.040` → grounded `1.846\pm0.053`, *"a gain of `0.20` over three seeds"*; `MAE 1.85 vs 2.25`; the headline `+0.41`; at seed 42 `+0.18` (`1.803\to1.981`) against `+0.43` (`1.803\to2.232`); *"a share of `0.59` at seed 42"*, with `0.83` and `0.61` beside it; channel swap `+0.27`, to `2.08`; *"about twice what supervision gains (`+0.41` against `-0.20`)"*; per-seed gains `0.237`, `0.075`, `0.281`.
- **Disposition:** **R**, except the three K-numbers that live inside it (rows 27–29), which keep their published value with the five-seed one beside.
- **Artifact:** `results/e5_sigma_grounding_leakfree/seed_*/comparison.json` (all three arms, after follow-up step 3) and `.../seed_*/{ungrounded,grounded_a,oracle}_predictions.summary.json`.
- **Command:** per seed, `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_e5_comparison.py --run ungrounded=<seed>/ungrounded_predictions.csv --run grounded_a=<seed>/grounded_a_predictions.csv --run oracle=<seed>/oracle_predictions.csv --direct-label grounded_a --out-json <seed>/comparison.json` (this is exactly what follow-up step 3 does). The **prose is hand-transcribed from those JSONs** — no script writes §3.1.
- **Branch:** `1|2|3` for every value. **Branch 2** additionally rewrites the section's claim and (row 35) its heading.

### Row 3 — §3.2, which carries the slopes, the ranking contrast and the solute-blind comparison
- **Inventory name / label:** *"§\ref{sec:decision}, which carries the regression slopes read off Fig.~\ref{fig:parity-lnx2}, the ranking contrast and the solute-blind comparison"* — `\label{sec:decision}`.
- **Prints:** `paper/grounding_paradox.tex` **L567–658**; printed **pp. 13–15**.
- **Prints now:** slopes `0.515` DirectGNN / `0.416` ungrounded / `0.528` grounded / `0.690` reference, *"all four at seed 42"*; `0.013`; `823` groups over `107` solutes; Spearman `0.592/0.546/0.598` → `0.365/0.369/0.410`, pooled `-0.197` `[-0.282,-0.117]`, largest seed-replicate difference `0.060`; nDCG@3 `-0.084` `[-0.124,-0.043]`; top-1 `-0.107` `[-0.192,-0.020]`; the selected solvent changes in `40` to `53\%` of groups; best-solvent hit rates `20.0/23.2/21.5\%` against `6.2/14.5/12.2\%`; affine recalibration removes `86\%`, `+0.431` `[+0.308,+0.553]` → `+0.060` `[+0.021,+0.101]`; out-of-sample `+1.09` `[+0.3,+2.2]`, `550` groups, `+0.28/+0.07/+0.04`; map decreases in `10` to `12\%` / `17` to `19\%`; `589` of `823`, ρ `-0.148` `[-0.218,-0.079]`, nDCG@3 `-0.068` `[-0.110,-0.026]`; twenty-four intervals, `[-0.0008,+0.0762]`; permutation floor `\rho=0.00\pm0.02`.
- **Disposition:** **R**.
- **Artifact:** slopes — `paper/figs/fig_parity_lnx2.numbers.json` (field `ols_slope_pred_on_meas`); ranking — `results/e5_sigma_grounding_leakfree/ranking/rank_final.json` and `rank_final_floorci.json` (to be produced).
- **Command:** slopes — `make_parity_figure.py … --dump-json` (row 9). Ranking — `python results/e5_sigma_grounding/ranking/rank_final.py <outdir>` then `rank_final_floorci.py`. **Friction:** `rank_final.py` hard-codes `BASE = REPO/"results/e5_sigma_grounding"` and `SEEDS = (42,43,44)` at module scope (L30, L36) with **no CLI override** — it must be edited, or copied, to point at the leak-free tree and five seeds.
- **Branch:** `1|2|3`.

### Row 4 — §3.4's channel paragraph
- **Inventory name / label:** *"§\ref{sec:notdecided}, which carries its channel paragraph"* — `\label{sec:notdecided}`.
- **Prints:** `paper/grounding_paradox.tex` **L688–692**; printed **p. 18**.
- **Prints now:** *"the both-channel substitution the attribution would need covers only `\approx7` solutes"*.
- **Disposition:** **R**.
- **Artifact:** `results/e5_sigma_grounding_leakfree/seed_*/oracle_predictions.csv` (the substitution flag), against `notebooks/data/processed/test.csv`.
- **Command:** the counts come from the match-rule audit that also feeds row 15; the `7 / 297` pair is recomputed by the same pass. **No dedicated script emits the `\approx7`** — it is transcribed. The reference table and match rule are unchanged by the re-run, so this row is expected to be a *check*, not a change.
- **Branch:** `1|2|3`.

### Row 5 — the five rows of Table S2 under *the two senses of grounding*
- **Inventory name / label:** *"the five rows of Table~\ref{tab:claims} under \emph{the two senses of grounding}"* — `\label{tab:claims}` (part 1).
- **Prints:** `paper/sections/SI.tex` **L647–673** (caption L649–651, label L652, block head **L660**, the five rows **L661, 663, 665, 667, 669**); printed **p. S-10**.
- **Prints now:** row 1 `1.85\to2.25`; row 2 `1.80\to1.98` (own baseline `1.80\to2.23`), seed `42`; row 3 `share 0.59 on one seed`; row 4 `2.04\to1.85`, per-seed gains `0.237/0.075/0.281`, straddling `+0.18`; row 5 `823` groups / `107` solutes, ρ `-0.197` `[-0.282,-0.117]`, nDCG@3 `-0.084` `[-0.124,-0.043]`, top-1 `-0.107` `[-0.192,-0.020]`, `\max|\Delta\Phi|=4.2\times10^{-4}`, `86\%`, `589` of `823`. Set column: `labelled test rows ($5608$ of $8103$), 3 seeds`.
- **Disposition:** **R** (rows 2 and 3 are the K-numbers of row 29 — published value kept, five-seed beside).
- **Artifact:** same as rows 2, 3 and 13.
- **Command:** **none.** The ledger is hand-written LaTeX; no generator exists for it. *This is a row that will be missed.*
- **Branch:** `1|2|3` for the values; **branch 2** rewrites the supervision row (row 4 of the block) to record the operation as unresolved — the decision rule names it explicitly.

### Row 6 — the `+0.14` accuracy row of Table S2, part 3
- **Inventory name / label:** *"the $+0.14$ of the accuracy row of Table~\ref{tab:claims-cont2}, the ledger's third part"* — `\label{tab:claims-cont2}` (part 3, `\ContinuedFloat`).
- **Prints:** `paper/sections/SI.tex` **L720–762** (caption L723–724, label L725, accuracy block head **L742**, the row **L743**); printed **p. S-12**.
- **Prints now:** `Physics arm vs.\ DirectGNN accuracy ($\Delta$MAE) & labelled test rows ($5608$ of $8103$) & $+0.14$ between separately tuned pipelines`.
- **Disposition:** **R** — the physics side only; DirectGNN is not retrained.
- **Artifact:** grounded five-seed mean from `results/e5_sigma_grounding_leakfree/seed_*/comparison.json`, **against the published** `results/e5_sigma_grounding/seed_*/directgnn_predictions.csv` control mean.
- **Command:** **none.** Hand-written cell; the arithmetic is §2 item 3 below.
- **Branch:** `1|2|3`.

### Row 7 — the σ-grounding row of Table S25, entire
- **Inventory name / label:** *"the $\sigma$-grounding row of Table~\ref{tab:runs} entire---its seed list, the mean$\pm$sd cell that carries it, and the $+0.41$ and $-0.20$ its third column prints"* — `\label{tab:runs}`.
- **Prints:** `paper/sections/SI.tex` **L3122–3175** (the row at **L3134–3136**); printed **p. S-69**.
- **Prints now:** `$42,43,44$, mean$\pm$sd on the $n{=}5608$ labelled test rows` | `Figs.~\ref{fig:paradox} and~\ref{fig:parity-lnx2}, Table~\ref{tab:si-arms}, the $+0.41$ and $-0.20$ of \S\ref{sec:paradox}`.
- **Disposition:** **R**, all three cells together *"so that no cell of that row states a seed policy the cell beside it contradicts"*.
- **Artifact:** as row 2.
- **Command:** **none.** Hand-written table.
- **Branch:** `1|2|3`. Note the float-note under the table (`L3172–3174`: *"every row of every arm at every seed is re-analysable from the deposit"*) is a claim about the deposit and moves with row 23's audit.

### Row 8 — Fig. 2's ungrounded, grounded and oracle bars, with their R²
- **Inventory name / label:** *"the ungrounded, grounded and oracle bars of Fig.~\ref{fig:paradox} with their $R^2$"* — `\label{fig:paradox}` = Figure 2.
- **Prints:** float at `paper/grounding_paradox.tex` **L553–565** (caption L559–563, label L564), graphic `paper/figs/fig_paradox.pdf`; printed **p. 14**.
- **Prints now:** the figure carries **no numerals per bar** (axis ticks only, checked on the printed page). The bar heights it draws are the three-seed means of Table S3: ungrounded MAE `2.04\pm0.04`, R² `+0.19\pm0.01`; grounded `1.85\pm0.05`, `+0.33\pm0.05`; σ-oracle `2.25\pm0.02`, `-0.03\pm0.04`. Caption prints `5608` and *"Solid bars: three seeds"*.
- **Disposition:** **R** (three of the eight arms; NRTL, DirectGNN, `grounded+comb.` and the two hatched seed-42 controls stay as drawn).
- **Artifact:** `results/e5_sigma_grounding_leakfree/seed_*/` per-row CSVs.
- **Command:** `KMP_DUPLICATE_LIB_OK=TRUE python scripts/analysis/make_paradox_figures.py --e5-dir results/e5_sigma_grounding_leakfree --seeds 42 43 44 45 46 --out-dir paper/figs` — **but** the figure draws all eight arms from one `--e5-dir`, and the five non-re-run arms live in `results/e5_sigma_grounding`. The two trees must be merged into one directory (or the script taught two roots) before this runs. Caption edit (row 34) is separate and manual.
- **Branch:** `1|2|3`.

### Row 9 — panels (b), (c) and (d) of Fig. 3
- **Inventory name / label:** *"panels (b), (c) and (d) of Fig.~\ref{fig:parity-lnx2}"* — `\label{fig:parity-lnx2}` = Figure 3.
- **Prints:** float at `paper/sections/fig-parity-lnx2.tex` **L17–36**, graphic `paper/figs/fig_parity_lnx2.pdf`; printed **p. 16**.
- **Prints now** (from `paper/figs/fig_parity_lnx2.numbers.json`, which is what the panel headers print): (b) ungrounded MAE `2.040`, R² `+0.187`; (c) grounded `1.803`, `+0.370`; (d) ref. σ (eval) `2.232`, `-0.036`. Panel (a) DirectGNN `1.749` / `+0.385` is **outside**. Caption prints `5608`, `763` pairs, `147` solutes, `70` solvents, `248`–`368` K, *"seed $42$ of three"*, *"at most $0.05$ in MAE"*.
- **Disposition:** **R** — and the inventory fixes that *"Fig.~\ref{fig:parity-lnx2} remains one seed for all four of its panels, the new seed $42$ in three of them and the published one in the control."* Do not turn it into a five-seed figure.
- **Artifact:** `results/e5_sigma_grounding_leakfree/seed_42/{ungrounded,grounded_a,oracle}_predictions.csv` + published `seed_42/directgnn_predictions.csv`.
- **Command:** `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/make_parity_figure.py --e5-dir <merged tree> --seed 42 --out-dir paper/figs --dump-json paper/figs/fig_parity_lnx2.numbers.json`. Same merged-tree caveat as row 8. The caption's `at most 0.05 in MAE` must be re-derived against the new five-seed means.
- **Branch:** `1|2|3`. **Row 3 depends on this row** — §3.2's four slopes are read off this figure's `--dump-json`.

### Row 10 — the block-1 grounded and σ-oracle rows of Tables 3 and S17
- **Inventory name / label:** *"the block-1 grounded and $\sigma$-oracle rows, which print in Tables~\ref{tab:baselines} and~\ref{tab:si-baselines-full} off one source of record, so a regenerated value lands in both"*.
- **Prints:** one source file, two floats. Source: `paper/si_tables/external_baselines_rows.tex` — block head **L43**, grounded row **L46**, σ-oracle row **L47**; and `paper/si_tables/external_baselines_rows_article.tex` (the article's cut) — block head **L109**, grounded row **L112**, σ-oracle row **L113**. Floats: `\label{tab:baselines}` = Table 3, `paper/grounding_paradox.tex` **L1314–1325** (caption L1316–1320, label L1321), printed **p. 28**; `\label{tab:si-baselines-full}`, `paper/sections/SI.tex` **L2293–2340** (caption L2295–2299, label L2300), printed **p. S-43**.
- **Prints now:** grounded row `$5608$ / $5440$ | $1.85\pm0.05$ | $1.39\pm0.19$ | $0.33\pm0.05$`; σ-oracle row `$5608$ / $5440$ | $2.25\pm0.02$ | $1.60\pm0.14$ | $-0.03\pm0.04$`. Block head (both files): *"three unless the row says otherwise"*.
- **Disposition:** **R**, in both files. The DirectGNN, NRTL and predict-the-mean rows are **outside**.
- **Artifact:** `results/external_baseline_comparison/{table_rows.csv,table_article.tex,summary.json}`.
- **Command:** `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_external_baseline_comparison.py`. **Friction:** the script hard-codes `E5 = REPO/"results/e5_sigma_grounding"` (L101) and `SEEDS = (42, 43, 44)` (L104); only `--out-dir` is a flag. Both constants must be edited. Then re-transcribe into `external_baselines_rows.tex` re-applying its four listed typesetting edits, and **re-cut** `external_baselines_rows_article.tex` from it (drop the `Test set` column, the as-published block and the two random-pair rows, restore `\pmsd`). The width arithmetic in both headers is load-bearing — re-measure if any cell widens (2.4 pt of headroom on the line).
- **Branch:** `1|2|3`.

### Row 11 — the clip sweep, the fuller sweep of §S4, and §3.7's readings off both
- **Inventory name / label:** *"with the clip sweep in the note of the second, the fuller sweep of \S\ref{sec:si-baselines} and the readings \S\ref{sec:discussion} takes from both"* — `\label{sec:si-baselines}`, `\label{sec:discussion}`.
- **Prints:** clip note `paper/sections/SI.tex` **L2314–2331** (inside the `\tabnotes` block L2305–2339), printed **p. S-43**; §S4's reading paragraph **L2342–2378**, printed **pp. S-43 to S-44**; §3.7's paragraph `paper/grounding_paradox.tex` **L1270**, printed **p. 27**.
- **Prints now:** clip note — *"$12$ to $195$ rows per seed for the three physics arms, none for the control"*, and without the clip the σ-oracle reads `0.26` lower, grounded `0.31`, NRTL `0.48`; sweep from `1-10^{-3}` to `1-10^{-10}`, control at `1.00` throughout. §S4 — control `1.00`, at one seed `0.97`; published leaders `0.83` to `0.99`, cycle `1.43` to `2.16`; physics arms `1.39` to `1.60`; scale reference `1.33`; seed-42 grounded `1.13` against `1.33`; `0.75` aleatoric; `0.61`/`0.45` random-pair; FastSolv `1.44` vs `1.02`, SolProp encoder `1.62` vs `0.64`; re-scored by-solute `0.84`. §3.7 — the same `1.00` / `0.83`–`0.99` / `1.43`–`2.16` / `1.39`–`1.60` sentence.
- **Disposition:** **R** for the grounded and σ-oracle cells and every reading that quotes them. The FastSolv/SolProp/published values and the control are **outside**.
- **Artifact:** `results/external_baseline_comparison/summary.json` (the clip sweep block).
- **Command:** same as row 10 — the sweep is emitted by the same script. **The §S4 and §3.7 prose is hand-transcribed and no command produces it.**
- **Branch:** `1|2|3`.

### Row 12 — Table S3, and the unrounded means / per-seed values / arm orderings `sec:si-tables` reads off it
- **Inventory name / label:** *"Table~\ref{tab:si-arms} and the unrounded means, per-seed values and arm orderings \S\ref{sec:si-tables} reads off it"* — `\label{tab:si-arms}` and `\label{sec:si-tables}` — resolve both through the .aux rather than trusting a number written here.
- **Prints:** table `paper/sections/SI.tex` **L836–860** (caption L838–841, label L842, rows **`\input` at L857**, and since 2026-08-10 the rows themselves live in `paper/si_tables/si_arms_rows.tex`, generated — see **Command**), printed **p. S-14**; the reading paragraphs **L812–834** and the four-decimal list **L862–869**, printed **pp. S-13 to S-14**. (Line numbers re-resolved 2026-08-10 after the rewiring; the float still sets as Table S3 on p. S-14 and the SI is still 84 pp.)
- **Prints now (table):** DirectGNN `1.70\pm0.03 / +0.42\pm0.03 / 1.749/1.674/1.684`; NRTL `1.79\pm0.07 / +0.34\pm0.03 / 1.734/1.758/1.894`; grounded `1.85\pm0.05 / +0.33\pm0.05 / 1.803/1.921/1.813`; `+SG comb.` `1.88\pm0.09 / +0.32\pm0.05 / 1.805/2.007/1.824`; ungrounded `2.04\pm0.04 / +0.19\pm0.01 / 2.040/1.996/2.093`; σ-oracle `2.25\pm0.02 / -0.03\pm0.04 / 2.232/2.281/2.242`.
  **Prints now (prose):** four-decimal means `1.7022, 1.7950, 1.8457, 1.8788, 2.0434, 2.2517`, population sd `0.033, 0.071, 0.053, 0.091, 0.040, 0.021`; NRTL rounding note `1.7953` / `1.794975` / `1.79`; `2.0434\to1.8457` (helps, `-0.20`), `1.8457\to2.2517` (hurts, `+0.41`); `0.1435` quoted as `+0.14` against rounded `1.85`/`1.70` differing by `0.15`; NRTL `1.734` against control `1.749` at seed 42; `1.8457\to1.8788`; `\sqrt{3/2}`; oracle-control block `1.98`, `2.08`, `1.803`, `1.921`, `+0.27` is `2.3` times the range, `+0.18` one and a half times it; `1.981-1.803=0.177` against `2.232-1.803=0.428`, share `0.59`; `0.118`, `\pm0.27`, `0.83` and `0.61`; `(0.406-0.177)/0.406=0.56`.
- **Disposition:** **R** for the ungrounded, grounded and σ-oracle rows and every derived figure above; DirectGNN, NRTL and `+SG comb.` rows are **outside** (but the four-decimal list and the orderings that mix them are rewritten).
- **Artifact:** `results/e5_sigma_grounding_leakfree/seed_*/comparison.json`, plus the published `results/e5_sigma_grounding/THREE_SEED_SUMMARY.md` pattern for the arms that stay.
- **Command:** ~~**no generator writes this table.**~~ **Updated 2026-08-10: one does now, and the table is wired to it.**
  ```bash
  KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/make_si_arms_table.py \
      --root results/e5_sigma_grounding_leakfree          # --root defaults to the published tree
  ```
  **Corrected 2026-08-10.** Pointed at the leak-free tree the script first emitted a **three-row**
  Table S3: the re-run trains only the ungrounded, grounded and σ-oracle arms, and DirectGNN, NRTL
  and `+SG comb.` — whose disposition here is **outside**, i.e. they stand as printed — were
  dropped without a word on stdout or in the generated header, and the module's own
  row-reproduction test passed on the truncated table. Arms absent from `--root` are now read from
  `--published-root` (default: the published tree) at that tree's own seeds, each row carrying its
  source tree and seed list into the header and the JSON; an arm in **neither** tree stops the
  script. Because the `+0.14` `sec:si-tables` quotes is then a difference between an arm in one tree and an arm
  in the other, the two locks are compared key by key and a difference is fatal unless
  `--allow-lock-mismatch` stamps it on the header.
  `scripts/analysis/make_si_arms_table.py` writes `paper/si_tables/si_arms_rows.tex` (the column
  header, `\midrule` and every row, `\input` by `sections/SI.tex` between `\toprule` and
  `\bottomrule`) and `paper/si_tables/si_arms_table.json` (unrounded means, per-seed MAE and R²,
  the two single-seed controls, and the derived quantities `sec:si-tables`'s prose reads off the table:
  `-0.1977`, `+0.4059`, `0.1435`, the NRTL `1.7953`/`1.794975` pair, the per-seed gains, the
  seed-42 control block with the between-seed range and both shares). It imports
  `run_e5_comparison.py` and calls its `intersection_keys`/`_metrics_on_keys`, so the lock is that
  file's code and not a second copy of it; seeds are discovered from `seed_*`, so five need no
  flag; the `±` is a population sd, as the caption says. Verified against the published tree: it
  reproduces all six rows and both controls **character for character on the numerals**.
  `--check` writes nothing and exits non-zero on any drift; `tests/test_si_arms_table.py` runs that
  check against the tree the generated file's own `% ROOT:` header names, so the gate follows the
  re-run without being edited, and additionally gates the four-decimal list, the NRTL rounding note
  and the two-senses sentence in `sec:si-tables`'s prose, which are still hand-transcribed.
  *This was the second row that would have been missed, and it is the source of record for six of the
  derived numbers in §2.* What is still hand-work here: the caption (seed count, `n`), and every
  prose figure above that the JSON supplies but does not typeset.
  **Corrected 2026-08-10 (second).** `sec:si-tables`'s sensitivity on the `0.59` share — *"a spread the size of the
  learned arm's `0.118` would move the share by about `±0.27`"* — was recorded as not being a function
  of the artifacts and so not dischargeable by any generator. It is
  `learned_sigma_between_seed_range / evaluation_only_gap` = `0.11769350 / 0.42825139` = `0.2748 →
  0.27`, and **both operands were already in this generator's own JSON** under
  `derived.single_seed_controls`. It is deposited now as
  `share_shift_per_learned_arm_sized_spread` and gated in `tests/test_si_arms_table.py` beside the
  `0.177`/`0.428`/`0.59` sentence, so it moves with the five seeds instead of standing stale.
- **Branch:** `1|2|3`.

### Row 13 — Table S19, and §S6.1's ranking and recalibration readings
- **Inventory name / label:** *"Table~\ref{tab:ranking} with the ranking and per-group recalibration readings \S\ref{sec:supporting} sets around it, whose two columns are the grounded checkpoint and its own $\sigma$-oracle re-evaluation and nothing else"* — `\label{tab:ranking}`, `\label{sec:supporting}`.
- **Prints:** `paper/sections/supporting.tex` **L65–107** (the float; caption L67–83, label L84, rows L92–103) and **L109–135** (the readings); printed **p. S-53** (table), **pp. S-52 to S-53** (readings).
- **Prints now:** ρ `0.592/0.546/0.598` vs `0.365/0.369/0.410`, `-0.197` `[-0.282,-0.117]`; τ `0.518/0.469/0.521` vs `0.303/0.306/0.333`, `-0.188` `[-0.263,-0.118]`; nDCG@3 `0.796/0.748/0.792` vs `0.697/0.690/0.698`, `-0.084` `[-0.124,-0.043]`; top-1 `0.586/0.515/0.548` vs `0.447/0.428/0.454`, `-0.107` `[-0.192,-0.020]`; shuffled-profile floor margins `+0.120/+0.209/+0.264` vs `+0.039/+0.033/+0.079`; label floor `+0.240/+0.207/+0.273` vs `+0.038/+0.037/+0.080`; `24` vs `0` of 24; permutation floor `0.00\pm0.02`. Readings add `-0.028`, `[-0.005,+0.165]`, `[-0.0008,+0.0762]`, `16` groups / `807` groups `-0.212/-0.158/-0.172`, jackknife `[-0.239,-0.211]`, `[-0.190,-0.157]`, `[-0.203,-0.171]`, `|\Delta\rho|\le0.060`, DirectGNN-minus-learned `-0.056/+0.053/-0.040`.
- **Disposition:** **R** — *both* columns are re-run arms.
- **Artifact:** `results/e5_sigma_grounding_leakfree/ranking/{rank_final.json,rank_final_floorci.json}` (to be produced).
- **Command:** `python results/e5_sigma_grounding/ranking/rank_final.py <outdir>` then `rank_final_floorci.py <outdir>`. Same hard-coded-`BASE`/`SEEDS` friction as row 3. The generic `scripts/analysis/run_ranking_eval.py --predictions-csv … --out-json …` computes the four metrics but **not** the floors, the clustered bootstrap or the recalibration, so it does not discharge this row alone.
- **Branch:** `1|2|3`.

### Row 14 — `sec:map` with Tables S21 and S22
- **Inventory name / label:** *"\S\ref{sec:map} with Tables~\ref{tab:solvent-map} and~\ref{tab:solute-map}, which resolve that same $+0.14$ along chemical axes and restate the two arm means it is taken from"*.
- **Prints:** `paper/sections/chemistry-map.tex` (65 lines) — heading+label **L1**, body **L3–14**, Table S21 **L16–37** (caption L18–20, label L21), Table S22 **L41–63** (caption L43–47, label L48), closing paragraph **L65**; printed **p. S-57** (§ and Table S21), **p. S-58** (Table S22).
- **Prints now:** prose `1.70\pm0.03` control, `1.85\pm0.05` grounded, `\Delta MAE = +0.14`, per-seed span `+0.05` to `+0.25`, rounded pair differing by `0.15`, amide `-0.22\pm0.11`. Table S21: Water `+0.52\pm0.35`, Carboxylic acid `+0.39\pm0.16`, Sulfoxide `+0.26\pm0.24`, Nitrile `+0.20\pm0.19` (**was `+0.21`; repaired 2026-08-10, see Command**), Alcohol `+0.15\pm0.14`, Aromatic `+0.03\pm0.63`, Hydrocarbon `+0.02\pm0.50`, Halogenated `-0.29\pm0.36`, Amide `-0.22\pm0.11`. Table S22: Oxygenated `+0.32`, Polyaromatic `+0.27`, Heterocycle `+0.17`, Halogenated-aromatic `\approx0`, Charged/salt `-0.04\pm0.19`, Tanimoto ≤0.3 `-0.04\pm0.18`, Tanimoto >0.8 `+0.51\pm0.09`.
- **Disposition:** **R** on the physics side only; the control side stays published, and both captions must say so (row 34).
- **Artifact:** ~~**none found.**~~ **Updated 2026-08-10:** `results/e5_sigma_grounding/chemistry_map.json`, written by the generator below. Every cell carries its per-seed values, both spread conventions, its row count and the conservation check.
- **Command:** ~~**none exists.**~~ **Updated 2026-08-10: one does now.**
  ```bash
  KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_e5_chemistry_map.py \
      --check --out-json results/e5_sigma_grounding/chemistry_map.json
  # leak-free discharge (disposition R on the physics side only — the control stays published):
  KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/run_e5_chemistry_map.py \
      --root results/e5_sigma_grounding_leakfree \
      --control-root results/e5_sigma_grounding --control-seeds 42 43 44 --check
  ```
  **Corrected 2026-08-10.** The leak-free invocation as first written here carried `--seeds 42 43 44
  45 46 --control-seeds 42 43 44 42 43`, and both halves of that were wrong. `--seeds` is now
  discovered from the tree (the old hard-coded default `[42,43,44]` meant that pointing the script
  at the five-seed tree *without* the flag silently used three and said nothing about the other
  two). And padding the three control seeds out to five by repeating 42 and 43 counted those two
  runs twice, which moved the DirectGNN control cell from the published `1.70 ± 0.03` to
  `1.71 ± 0.04` — a cell whose disposition is that it does **not** move, since DirectGNN is not
  retrained. A repeated seed is now refused. Unequal seed lists are **pooled**: the control's
  stratum MAE is averaged over its own three seeds and each physics seed is differenced against
  that one number, so every cell's `±` is the physics side's spread alone (which is what row 34
  requires both captions to say) and the control's own mean and sd stay the published ones.
  `control_pairing` in the JSON records which rule ran.
  Definitions the generator pins, none of which was recorded anywhere before: solvent class =
  `tgnn_solv.data.solvent_types.solvent_type_from_smiles` (the nine printed classes are exactly
  `SOLVENT_TYPE_NAMES` minus `other`); solute class = `_coarse_solute_class`, imported live out of
  `scripts/evaluation/run_prediction_error_slices.py` so it cannot drift; novelty stratum = maximum
  Morgan(r=2, 2048-bit) Tanimoto of the test solute against the unique train solutes of
  `notebooks/data/processed/train.csv`. **The two spread conventions in this section differ and both
  are needed:** the section's two arm means print a *population* sd, every table cell a *sample* sd.
  `tests/test_e5_chemistry_map.py` is the gate.
  **Fifteen of the seventeen values reproduced to the printed decimal on the first pass. Both
  exceptions were settled the same day, one by repairing the table and one by withdrawing a wrong
  write-off; all seventeen now reproduce, and `--check` reports `19 of 19`.**
  - **Nitrile printed `+0.21`; the tree gives `+0.2048`, i.e. `+0.20`. REPAIRED in the `.tex`
    2026-08-10.** The sd (`0.19`) was right and the stratum is acetonitrile alone (n=252), so this
    was a last-digit slip and not a definitional question: the value misses the `0.205` rounding
    boundary by `2\times10^{-4}`. (Averaging the per-seed values after rounding each to 2 dp does
    give `+0.21`, but that rule then breaks Water `+0.51` vs `+0.52` and Amide `-0.21` vs `-0.22`,
    so it was not the table's rule. `tests/test_e5_chemistry_map.py` asserts that, rather than the
    prose asserting it.) `+0.21` is now a **retired numeral** for the C6 re-grep.
  - **Charged / salt `-0.04\pm0.19` IS recoverable: `multifrag_neutral`, and the 2026-08-10
    write-off of this cell is WITHDRAWN.** The write-off ran: the one mask that hits both digits —
    multi-fragment **with no formal charge**, `-0.0355\pm0.1877`, 416 rows — "excludes every charged
    solute in the test set, so it cannot be what the row's name denotes", and the cell is therefore
    unregenerable *in principle*. That does not survive enumerating the solutes. **In this corpus a
    formal charge is mostly a nitro group.** Of the 31 formally-charged solutes on the locked rows
    (735 rows), **18 (355 rows) have every fragment net-neutral** — nitroaromatics and nitramines,
    `[N+](=O)[O-]` as RDKit writes it, not ions. The **13 that carry a net-charged fragment (380
    rows) are exactly `explicit_salt`**, i.e. salts written *with* their charges. So the mask does
    not exclude the charged solutes; it excludes the nitro compounds and one spelling of a salt, and
    what it selects is the other spelling: nine acid-addition salts (drug hydrochlorides, two
    tosylate forms, a phosphate, a malate) and four hydrates. That is a stated, reproducible
    definition and it is now the generator's default (`--salt-def multifrag_neutral`,
    `DEFAULT_SALT_DEF`), checked like its neighbours, with the nitro-versus-ion count deposited as
    `salt_audit/formal_charge_is_not_ionicity`. **What is true and stays on the record:** the
    printed row is the un-ionised salts only, *not* the union of both spellings — the 380
    explicitly-ionised rows are outside it, and the union (`salt_candidate/multifrag`,
    `+0.07\pm0.34`) is deposited beside it so the exclusion cannot be lost. The five-seed
    substitution has a defined quantity to write into this cell.
  Two further facts the section does not state and the generator now reports: Table S21's nine classes
  cover **4368 of the 5608 locked rows** — the tenth class, `other`, holds **1240 rows (22.1%)** at
  `+0.136\pm0.048` and is printed nowhere, and it is the ester/ketone/ether block (ethyl acetate 393,
  acetone 375, dioxane 103, THF 74, …), i.e. aprotic dipolar acceptors like the amide class the section
  reads its sign reversal off, sitting at `+0.14` rather than negative; Table S22's four classes cover
  **5107**, leaving **501** (`sulfur_or_phosphorus` 277 at `-0.12`, `other` 224 at `+0.41`). Both
  taxonomies do partition the locked rows, and the row-weighted recombination returns the global
  `+0.1435` to `10^{-16}`.
- **Branch:** `1|2|3`.

### Row 15 — the row-class split of the substitution, `sec:si-methods`
- **Inventory name / label:** *"the row-class split of the substitution in \S\ref{sec:si-methods}, whose $-0.000$, $+0.431$ and $+0.006$ put the $+0.41$ on the solvent channel"*.
- **Prints:** `paper/sections/SI.tex` **L214–229** (the paragraph *What the match rule reaches, and which side carries the effect*); printed **p. S-5**.
- **Prints now:** `5571` (`99.3\%`; `64` of `70` solvents), `297` (`5.3\%`; `7` of `147` solutes), split `37` / `5274` / `297`; MAE differences `-0.000\pm0.000`, `+0.431\pm0.036`, `+0.006\pm0.025`; agreement to `5\times10^{-6}`.
- **Disposition:** **R**.
- **Artifact:** `results/e5_sigma_grounding_leakfree/seed_*/{grounded_a,oracle}_predictions.csv` (the per-row substitution flag).
- **Command:** **none usable as is.** `scripts/analysis/run_paradox_channel_split.py` computes this slice, but it has **no argparse at all**: it hard-codes `ROOT` to an absolute path (L12) and iterates `for seed in ["seed_42", "seed_43"]` over `results/e5_sigma_grounding/` (L23–25) — two seeds, the published tree. It must be edited to five seeds and the leak-free tree, or the split done by hand over the per-row CSVs. The coverage counts (`5571`, `297`, `7`, `64`) are properties of the reference table and the split, not of the arms, so they are a check.
- **Branch:** `1|2|3`.

### Row 16 — the label-noise-floor paragraph of §2.2
- **Inventory name / label:** *"the label-noise-floor paragraph of \S\ref{sec:data}, whose scaffold-split range $1.70$ to $1.85$ takes its upper endpoint, and the factor of five it reads against the floor, from the grounded arm"*.
- **Prints:** `paper/sections/methods.tex` **L228–244**; printed **p. 7**.
- **Prints now:** floor `0.15` on `3948` groups and `0.31` on `349`; medians `0.03` and `0.09`; de-duplicated `0.16` over `4261`; *"The scaffold-split MAE reported here (`1.70` to `1.85`) is above the larger functional by a factor of five"*; `0.75` inter-lab RMSE on `34` duplicates.
- **Disposition:** **R** — only the `1.85` endpoint and the factor. The floor statistics themselves are **outside** (run family "Noise floor and encoder probe", seeds: none).
- **Artifact:** grounded five-seed mean (row 12) against `results/noise_floor/` (produced by `scripts/analysis/run_noise_floor_estimate.py`).
- **Command:** **none for the enrolled part.** The factor of five is a hand division; `run_noise_floor_estimate.py` regenerates the floor side only, which does not move.
- **Branch:** `1|2|3`.

### Row 17 — the deposit-recovery paragraph of `sec:si-repro`
- **Inventory name / label:** *"the deposit-recovery paragraph below, whose before-and-after cells are that same $\sigma$-oracle row and move with it, the repair standing as a fact about the published deposit"*.
- **Prints:** `paper/sections/SI.tex` **L3933–3949** (the paragraph; `All twenty-two pass` at **L3949**) and **L3951–3958** (the follow-on carrying the σ-oracle row's before/after cells); printed **p. S-78**.
- **Prints now:** `295` of `8103` rows; `198{,}190` bytes of `5{,}213{,}388`; the summary block `n_{rows}=8103`, `n` labelled `=5608`, MAE `2.24199`, RMSE `2.96058`, `R^2=0.01768`, bias `1.00945`, matched subset `n=5571` MAE `2.24373`; `37` rows, `5\times10^{-6}`; **`All twenty-two pass`**; and the row move `2.26\pm0.02 \to 2.25\pm0.02` MAE, `1.57\pm0.17 \to 1.60\pm0.14` log₁₀S RMSE, `-0.05\pm0.02 \to -0.03\pm0.04` R².
- **Disposition:** **R** for the sentence stating what the Table 3 σ-oracle row *now is* (*"a three-seed mean like the rest of its block"*) and for `All twenty-two pass`. The repair itself — the byte counts, the recomputed summary — is a fact about the **published** deposit and stands.
- **Artifact:** `results/e5_sigma_grounding_leakfree/perrow_deposit_audit.json`.
- **Command:** `KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/verify_perrow_deposit.py --root results/e5_sigma_grounding_leakfree --json results/e5_sigma_grounding_leakfree/perrow_deposit_audit.json` (follow-up step 2). The prose is hand-edited.
- **Branch:** `1|2|3`. **The `twenty-two` here and the `twenty-two` in row 23 are one number, not two** — the inventory says so explicitly. Move them together.

### Row 18 — the freeze contrast of §3.3
- **Inventory name / label:** *"the freeze contrast of \S\ref{sec:surrogate}, whose closing clause sets its $65\%$ against \emph{the $+0.41$ headline arms of \S\ref{sec:paradox}} by name"*.
- **Prints:** `paper/sections/compensation-surrogate.tex` **L111–121** (the quoted `+0.41` at **L115–116**); printed **p. 17**.
- **Prints now:** *"cuts the reference-input penalty by `65\%` (`\Delta MAE` from `+0.40` to `+0.14` over `n{=}5571` matched test rows)"*, and *"not the `+0.41` headline arms of \S\ref{sec:paradox}"*.
- **Disposition:** **R** for the quoted `+0.41` only. *"the runs it contrasts them with staying as published"* — the `65\%`, `+0.40`, `+0.14` and `n=5571` are a separate matched pair of runs and do **not** move under branch 1.
- **Artifact:** row 12's five-seed grounded/oracle means (for the `+0.41`).
- **Command:** **none.** Hand edit.
- **Branch:** `1|2|3` for the quoted `+0.41`. Under **branches 2 and 3** the decision rule additionally requires the *whole* freeze contrast to be **restated**, *"because the warm-up state whose quality it turns on is the supervised one"*.

### Row 19 — §2.4's row-set paragraph
- **Inventory name / label:** *"\S\ref{sec:eval}'s row-set paragraph, which says the controlled comparisons are run at \emph{three} seeds and that the lock's finite-prediction clause removes no row from any arm \emph{at any seed}"*.
- **Prints:** `paper/sections/methods.tex` **L476–485**; printed **p. 10**.
- **Prints now:** *"are run at three seeds and reported as mean$\pm$sd"*; `5608`; `8103`; `2495`; *"the lock's finite-prediction clause is inert, removing no row from any arm at any seed"*; `twelve families`.
- **Disposition:** **R** — the seed count, and the per-seed universal, which is a claim over five seeds once they exist.
- **Artifact:** `results/e5_sigma_grounding_leakfree/perrow_deposit_audit.json` (non-finite counts) and `provenance_certificate.json` (criterion 5, the row lock).
- **Command:** `verify_perrow_deposit.py` and `certify_leakfree_rerun.py` as above; the prose is hand-edited. The `twelve families` count is a **check** — it does not change, the σ-grounding family being one family at five seeds rather than a new one.
- **Branch:** `1|2|3`.

### Row 20 — the compute ledger's *(three seeds)*
- **Inventory name / label:** *"the compute ledger's \emph{(three seeds)}"*, in `sec:si-repro`.
- **Prints:** `paper/sections/SI.tex` **L3901–3922** (the parenthetical at **L3902**); printed **p. S-77**.
- **Prints now:** *"The headline $\sigma$-grounding comparison (Fig.~\ref{fig:paradox}, Table~\ref{tab:si-arms}) is a full-corpus GPU run (three seeds)"*.
- **Disposition:** **R**.
- **Artifact / command:** none — a printed seed count, hand-edited. Cross-check against `provenance_certificate.json`'s seed list so the two cannot disagree.
- **Branch:** `1|2|3`.

### Row 21 — the seeds-and-determinism paragraph's `{42,43,44}`
- **Inventory name / label:** *"the seeds-and-determinism paragraph's \emph{$\{42,43,44\}$}, which is a second printed seed list for the same three arms"*.
- **Prints:** `paper/sections/SI.tex` **L3923–3931** (the list at **L3924**); printed **p. S-78**.
- **Prints now:** *"The controlled comparisons of \S\ref{sec:paradox} use seeds $\{42,43,44\}$"*; then `\{0,1,2\}` for the surrogate isolation and *"seed $42$ only"* for the four seed-42 families.
- **Disposition:** **R** — the first list only. `\{0,1,2\}` and the seed-42 list are **outside**.
- **Artifact / command:** none — hand-edited.
- **Branch:** `1|2|3`.
- **Note on the address:** the inventory's own record places this paragraph at S-77 against the protocol at S-74. Resolved off today's build it is **S-78** against **S-74**. The `\ref`-and-paragraph-name address in the operative list resolves correctly; only the parenthetical page drifted.

### Row 22 — `sec:si-methods`'s substitution-perturbation paragraph, *over the three seeds*
- **Inventory name / label:** *"in \S\ref{sec:si-methods} the substitution-perturbation paragraph's \emph{over the three seeds}, whose three maxima are taken across the same arms"*.
- **Prints:** `paper/sections/SI.tex` **L199–212**; printed **p. S-5**.
- **Prints now:** `0.025` K against a median of `450` K; `4.6` J mol⁻¹ against `3.7\times10^{4}`; `\Phi` by at most `7\times10^{-4}` against a median magnitude of `4.7`; on unsubstituted rows `1.2\times10^{-4}` K, `0.045` J mol⁻¹, `6\times10^{-6}`.
- **Disposition:** **R** — the seed count and the three maxima, which are maxima *across seeds* and gain two more.
- **Artifact:** `results/e5_sigma_grounding_leakfree/seed_*/{grounded_a,oracle}_predictions.csv` (per-row `Phi`, `T_m`, `dH_fus`).
- **Command:** **none dedicated.** Hand pass over the per-row CSVs.
- **Branch:** `1|2|3`.

### Row 23 — the opening two paragraphs of `sec:si-lock`
- **Inventory name / label:** *"the opening two paragraphs of \S\ref{sec:si-lock}, which are bookkeeping over these arms' deposits and move on two axes at once"* — narrowed on 2026-08-10 from "`sec:si-lock` entire" to these two paragraphs.
- **Prints:** `paper/sections/SI.tex` **L782–787** (para 1) and **L789–802** (para 2); printed **p. S-9**.
- **Prints now:** `5608`, `8103`, `2495`, *"decomposes with no remainder, identically at all three seeds"*, `0` duplicate-key rows; *"Audited over all **twenty-two** per-row prediction files … the five intersecting arms and the $\sigma$-oracle **at each of the three seeds**, plus the two co-adaptation controls and the two output-residual arms at seed $42$"*; *"All twenty-two are full length"*; *"(**Twenty-one** were full length as first deposited …)"*.
- **Disposition:** **R** — the count `22 → 28` (see §2 item 11), the two seed statements, and the parenthetical, *"rewritten together"*, with the twin `All twenty-two pass` of row 17 moving as one number.
- **Artifact:** `results/e5_sigma_grounding_leakfree/perrow_deposit_audit.json`.
- **Command:** `verify_perrow_deposit.py` as in row 17. The prose is hand-edited.
- **Branch:** `1|2|3`.

### Row 24 — the Conclusions' *second* sentence
- **Inventory name / label:** *"the Conclusions' second sentence (\S\ref{sec:conclusion}), whose first half asserts that training the intermediate toward its reference improved the model and whose second half asserts that supplying it at prediction time hurt \emph{at every seed}"*.
- **Prints:** `paper/grounding_paradox.tex` **L1413–1415**; printed **pp. 28–29** (the sentence straddles the break).
- **Prints now:** *"Training the intermediate toward its reference improved the model, on a contrast this work does not certify leak-free; supplying that reference at prediction time made the model worse, at every seed, and no question of certification reaches that second half."* No numerals.
- **Disposition:** **R**, on both halves and its per-seed universal. The inventory is explicit that the substitution's *sign* is fixed in all three branches but the per-seed universal is **not verified** at five seeds until the oracle re-evaluation lands at all five.
- **Artifact:** `results/e5_sigma_grounding_leakfree/seed_*/comparison.json`, per-seed grounded vs oracle MAE.
- **Command:** **none.** Hand edit. The per-seed universal is checkable off `certify_leakfree_rerun.py`'s per-seed table.
- **Branch:** `1|2|3`. **This sentence is also row 33** (disposition D, its leak-free clause). Two dispositions, one sentence, deliberately. Do not merge them; and do not confuse it with the *first* sentence (row 36).

### Row 25 — §1's copy of the same per-seed universal
- **Inventory name / label:** *"the same universal where \S\ref{sec:intro} states it---\emph{here it degrades prediction at every seed}"*.
- **Prints:** `paper/grounding_paradox.tex` **L378–380**; printed **p. 3**.
- **Prints now:** *"substituting a reference value for it at prediction time is not a safe improvement but a change of regime; here it degrades prediction at every seed."* No numerals.
- **Disposition:** **R**, with row 24.
- **Artifact / command:** as row 24. Hand edit.
- **Branch:** `1|2|3`.

### Row 26 — the graphic for the table of contents
- **Inventory name / label:** *"the graphic for the table of contents, whose caveat that training on the reference is not certified leak-free is removed in all three branches alike"*. No `\label` (achemso `tocentry`).
- **Prints:** `\begin{tocentry}` at `paper/grounding_paradox.tex` **L167–169**, graphic `paper/figs/fig_toc.pdf`; printed **p. 33** (achemso sets the TOC entry at the end of the article PDF).
- **Prints now** (three lines, hard-coded at `scripts/analysis/make_toc_figure.py` **L134–137**): *"Grounding is two operations on one database, with opposite signs / (solubility MAE on held-out scaffolds, three seeds; magnitudes in the text). / Training on it is not certified leak-free; a re-run is pre-committed."* Plus four arrow labels: *train on it / MAE improves* and *feed it in instead / MAE degrades*. **No magnitude is printed, by standing decision.**
- **Disposition:** **R** — the third line goes, in all three branches.
- **Artifact:** none — the figure reads no data file. Every string is a literal in the script.
- **Command:** `MPLBACKEND=Agg python scripts/analysis/make_toc_figure.py` — **but the script must be edited first**; re-running it unchanged reproduces the caveat verbatim. Do not restore a magnitude here (the script's docstring carries the argument).
- **Branch:** `1|2|3` for the caveat. Under **branches 2 and 3** the graphic is additionally *redrawn to what is then reported*, since it prints the two senses and their opposite signs.

---

### Rows 27–29 — the three K-numbers: published value kept, five-seed value beside it, caption saying so

### Row 27 — the Staverman–Guggenheim contrast `1.8457 → 1.8788`
- **Inventory name:** *"the Staverman--Guggenheim contrast $1.8457\to1.8788$, whose combinatorial arm is not retrained"*.
- **Prints:** `paper/sections/SI.tex` **L831–834** (`sec:si-tables`, above Table S3); printed **p. S-13**. Restated in §3.1 as the sixth arm of Fig. 2 (`paper/grounding_paradox.tex` L523–526, p. 12) and as Table S3's `+SG comb.` row `1.88\pm0.09`.
- **Prints now:** `1.8457\to1.8788`.
- **Disposition:** **K**. Left side is a re-run arm; right side (`grounded_b`) is not.
- **Artifact:** published `results/e5_sigma_grounding/seed_*/grounded_b_predictions.csv`; new grounded mean from row 12.
- **Command:** none — the pair is transcribed.
- **Branch:** `1|2|3`.

### Row 28 — the channel swap's `+0.27`
- **Inventory name:** *"the channel swap's $+0.27$, a seed-$42$ checkpoint that is not retrained either"*.
- **Prints:** `paper/grounding_paradox.tex` **L540–541** (`A channel-swap control costs $+0.27$, to $2.08$`), printed **p. 13**; and `paper/sections/SI.tex` **L887–899**, printed **p. S-14**.
- **Prints now:** `+0.27`, `2.08`, *"$2.3$ times the learned arm's full between-seed range"*.
- **Disposition:** **K**.
- **Artifact:** published `results/e5_sigma_grounding/seed_42/channel_swap_predictions.csv`.
- **Command:** none.
- **Branch:** `1|2|3`.

### Row 29 — the co-adaptation control's `+0.18` and the `0.59` share
- **Inventory name:** *"the co-adaptation control's $+0.18$ together with the $0.59$ share of \S\ref{sec:paradox}, which move only if the separate five-seed pass above is run"*.
- **Prints:** `paper/grounding_paradox.tex` **L532–540** (p. 13); `paper/sections/SI.tex` **L887–918** (p. S-14); Table S2 rows 2 and 3, `paper/sections/SI.tex` **L663** and **L665** (p. S-10).
- **Prints now:** `+0.18` (`1.803\to1.981`), `+0.43` (`1.803\to2.232`), share `0.59`, alternatives `0.83` and `0.61`, `1.981-1.803=0.177`, `2.232-1.803=0.428`, `(0.406-0.177)/0.406=0.56`, `\pm0.27`, `0.118`.
- **Disposition:** **K**.
- **Artifact:** published `results/e5_sigma_grounding/seed_42/grounded_a_truetrain_predictions.csv`.
- **Command:** the five-seed co-adaptation pass is **not committed to** by the protocol. If it is run anyway: `SEEDS="42 43 44 45 46" ARMS="grounded_a_truetrain" SIGMA_DIR=… OUT_DIR=… CKPT_DIR=… bash scripts/experiments/run_e5_sigma_grounding.sh` on the same stream build (GPU).
- **Branch:** `1|2|3`.

---

### Rows 30–33 — disposition D: four passages carrying no arm value that state the `0.20` is uncertified

All four are answered by the in-run certification, *"so each is rewritten to what the re-run certifies"*, **in all three branches alike**. All four rest on `provenance_certificate.json`, i.e. on precondition P0.2.

### Row 30 — the disclosure paragraph of §2.2
- **Prints:** `paper/sections/methods.tex` **L245–262**; printed **p. 8**.
- **Prints now:** `91` of `1425` rows; `7` of the `147` solutes and `8` with a scaffold relative, on `297` and `351` rows; *"the $0.20$ gain of \S\ref{sec:paradox} stays uncertified until the leak-free re-run"*; *"We therefore do not assert the scaffold guarantee for these runs."*
- **Command:** `certify_leakfree_rerun.py` (follow-up step 1). Prose hand-edited.
- **Branch:** `1|2|3`.

### Row 31 — limitation (xii) of §3.7
- **Prints:** `paper/grounding_paradox.tex` **L1383–1386**; printed **p. 25**.
- **Prints now:** *"the $0.20$ supervision gain is the one reported number a leak could inflate and is uncertified until the leak-free re-run"*.
- **Disposition:** **D**, and *"limitation~(xii)'s $0.20$ moves with \S\ref{sec:paradox}'s"* — so this row also carries a value and is coupled to row 2.
- **Command:** none. Hand edit.
- **Branch:** `1|2|3`.

### Row 32 — the grounding-stream provenance paragraph of `sec:si-repro`
- **Prints:** `paper/sections/SI.tex` **L3379–3440** (the uncertified clause at **L3433–3434**); printed **pp. S-73 to S-74**.
- **Prints now:** `1319` of `1427`; `1425` rows, `106` (`99` train, `7` validation), `2702` scaffolds; `91` / `65` / `64` / `26`; `2634` and `2467` distinct solutes; `5608` / `147`; `7` and `8`, `297` and `351`, `5.3\%` and `6.3\%`; `57` remaining leaked molecules; *"it stays uncertified against the scaffold split until the leak-free re-run"*.
- **Command:** `certify_leakfree_rerun.py`. Prose hand-edited. The *published* build's leak counts stand as a fact about that build.
- **Branch:** `1|2|3`.

### Row 33 — the Conclusions' second sentence, its leak-free clause
- **Prints:** `paper/grounding_paradox.tex` **L1413–1414**; printed **p. 28**.
- **Prints now:** *"on a contrast this work does not certify leak-free"*.
- **Disposition:** **D**. Same sentence as row 24, different disposition; the inventory's note is explicit that this is sentence **2**, not sentence 1.
- **Command:** none. Hand edit.
- **Branch:** `1|2|3`.

---

### Row 34 — the caption rule
- **Inventory name:** *"Seven of those floats … then carry re-run arms beside arms that were not re-run, so each states in its caption which of its arms came from the re-run"*, plus the two map captions and the two explicit out-verdicts.
- **The seven floats, by label, with file/line of the caption and printed page:**
  1. `fig:paradox` — caption `grounding_paradox.tex` **L559–563**, label L564, p. 14.
  2. `fig:parity-lnx2` — caption `sections/fig-parity-lnx2.tex` **L20–34**, label L35, p. 16. *(Already carries "from seed 42 of three"; the inventory fixes that it stays one seed.)*
  3. `tab:baselines` — caption `grounding_paradox.tex` **L1316–1320**, label L1321, p. 28. Block-1 head already carries *"three unless the row says otherwise"* (`si_tables/external_baselines_rows_article.tex` **L109**).
  4. `tab:si-baselines-full` — caption `sections/SI.tex` **L2295–2299**, label L2300, p. S-43. Same block head (`si_tables/external_baselines_rows.tex` **L43**).
  5. `tab:si-arms` — caption `sections/SI.tex` **L838–841**, label L842, p. S-14.
  6. `tab:claims` — caption `sections/SI.tex` **L649–651**, label L652, p. S-10. *(Three re-run rows beside the two seed-42 co-adaptation rows; the caption statement is required by row 29's K-disposition anyway.)*
  7. `tab:claims-cont2` — caption `sections/SI.tex` **L723–724**, label L725, p. S-12. *(The enrolled `+0.14` beside the `\{0,1,2\}` mechanism rows.)*
- **Two further captions:** `tab:solvent-map` (caption `sections/chemistry-map.tex` **L18–20**, label L21, p. S-57) and `tab:solute-map` (caption **L43–47**, label L48, p. S-58) *"print no arm at all, every cell being a difference against the control, so each says in its caption that only the physics side is five-seed."*
- **Two out-verdicts, recorded so the next pass re-derives rather than patches:** `tab:claims-cont` (Table S2 part 2, `sections/SI.tex` **L677–714**, p. S-11) **carries no re-run arm and stays out**; `tab:runs` **meets the criterion but discharges it in its seed column row by row, so its caption takes no addition**; `tab:ranking` **needs no statement, both its arms being re-run**.
- **Disposition:** **R** (caption text).
- **Artifact / command:** none. Every caption is hand-edited LaTeX.
- **Branch:** `1|2|3`.

---

### Rows 35–36 — the two rewrites the decision rule triggers in branch 2 only

### Row 35 — the heading of §3.1
- **Prints:** `paper/grounding_paradox.tex` **L508**; printed **p. 12**.
- **Prints now:** *"Supervising the intermediate toward the reference, and substituting it at prediction time"*.
- **Disposition:** rewritten *"to say so"* under branch 2. The 2026-08-07 pass recorded that the heading now names the two **operations** and not their signs, *"so branch 2's rewrite of that heading is a check rather than a change"*.
- **Command:** none.
- **Branch:** `2` only.

### Row 36 — the Conclusions' *first* sentence
- **Prints:** `paper/grounding_paradox.tex` **L1412–1413**; printed **p. 28**.
- **Prints now:** *"Grounding a learned physical intermediate in reference values is two operations, not one, and here they had opposite signs."* No caveat, no numerals.
- **Disposition:** *"opposite signs"* is the claim that fails if the per-seed gains straddle zero; branch 2 rewrites it.
- **Command:** none.
- **Branch:** `2` only. **Do not** discharge disposition D here — that is sentence 2 (row 33).

---

### Outside the boundary — recorded so it is not re-derived

*"Nothing else moves"*: neither the DirectGNN control nor the NRTL arm is retrained, so **their rows in
`tab:baselines`, `tab:si-baselines-full` and `tab:si-arms` stand as printed**; the endpoint comparison of
`sec:data-efficiency` (§S6.5, p. S-58) is the NRTL arm against that control and stands; `sec:measure`
(§3.5) uses no trained model at all. Also banked outside by earlier passes: `fig:overview` (Fig. 1 —
`make_overview_figure.py` opens only `results/b_insuff/stratified_map_table.csv`); `fig:arch`;
`tab:si-temp`; the three DirectGNN black-box-probe tables (`tab:crystal-decode`, `tab:temp-response`,
`tab:factor-variance`) and the article's probe paragraph; the n=44 surrogate runs, the freeze contrast's
own runs and the E2 crystal null; Gate B's two seed-42 arms; the nineteenth ledger row (OPERA pKa);
SI limitation (vii). **Trap, recorded because it will be met again:** Fig. 1 panel (b)'s glycol-ether
MSE prints as `2.252` in squared ln γ, which is the σ-oracle arm's ln x₂ MAE of `2.2517` to four
figures. Different axis, different unit, different set, **not an arm value** — do not "update" it.

---

## 2. The arithmetic of each derived number

Written as a formula over the arm means, with the **current** values substituted so that the current
printed value reproduces. Arm means to four decimals are Table S3's own list (`sections/SI.tex` L851–853).
Substituting five-seed means into the same formulae is the whole of the substitution.

Let `U`, `G`, `O`, `D`, `N`, `Gb` be the mean ln x₂ MAE of the ungrounded, grounded, σ-oracle,
DirectGNN, NRTL and grounded+combinatorial arms; a subscript is a seed.

**1. The supervision gain, printed `-0.20` (and as "a gain of `0.20`").**
`gain = U − G = 2.0434 − 1.8457 = 0.1977 → 0.20`. Printed as the pair `2.043±0.040 → 1.846±0.053`.
Per-seed: `U₄₂−G₄₂ = 2.040−1.803 = 0.237`; `U₄₃−G₄₃ = 1.996−1.921 = 0.075`; `U₄₄−G₄₄ = 2.093−1.813 = 0.280`,
printed `0.281` because it is taken on the unrounded per-seed values, not on the printed triples
(Table S3's caption states this rule).
*Leak-free, three seeds so far:* `2.1241 ± 0.0540 → 1.8908 ± 0.0063`, per-seed gain `0.2333 ± 0.0603`
(`0.1855 / 0.2134 / 0.3011`), one sign at all three, no per-seed overlap.

**2. The substitution penalty, printed `+0.41`.**
`+0.41 = O − G = 2.2517 − 1.8457 = 0.4060 → 0.41`. Printed elsewhere as the pair `1.85 vs 2.25`.
Seed 42: `O₄₂ − G₄₂ = 2.232 − 1.803 = 0.429 → +0.43`.

**3. The physics penalty, printed `+0.14`.**
`ΔMAE = G − D = 1.8457 − 1.7022 = 0.1435 → +0.14`. The rounded cells `1.85` and `1.70` differ by
`0.15`; the paper prints `+0.14` and says why in three places (Table S3's prose, `sec:map`'s footnote,
§3.7). **Only `G` moves.**

**4. The `0.59` share.**
`share = 1 − (T₄₂ − G₄₂)/(O₄₂ − G₄₂)` where `T` is the training-time (co-adapted) injection arm.
`= 1 − (1.981 − 1.803)/(2.232 − 1.803) = 1 − 0.177/0.428 = 0.5864 → 0.59`.
The two alternatives hold the numerator's arm at `1.981` and change the baseline:
seed 43 `1 − (1.981−1.921)/(2.281−1.921) = 1 − 0.060/0.360 = 0.833 → 0.83`;
seed 44 `1 − (1.981−1.813)/(2.242−1.813) = 1 − 0.168/0.429 = 0.608 → 0.61`.
The SI also prints the ratio that is *"a share of nothing"*: `(0.406 − 0.177)/0.406 = 0.56`.
And the sensitivity beside it: the numerator was measured once, so a spread the size of the learned
arm's own between-seed range would move the share by `range/(O₄₂−G₄₂)` = `0.11769/0.42825` = `0.2748
→ ±0.27`. Both operands are Table S3's, so this substitutes with everything else; it is deposited as
`derived.single_seed_controls.share_shift_per_learned_arm_sized_spread`.

**5. The Staverman–Guggenheim contrast.** `G → Gb = 1.8457 → 1.8788`, i.e. `+0.0331`. Only the left
side is a re-run arm; hence disposition **K**.

**6. The co-adaptation control, `+0.18`.** `T₄₂ − G₄₂ = 1.981 − 1.803 = 0.178 → +0.18`. Only the
subtrahend is a re-run arm; hence **K**.

**7. The channel swap, `+0.27`.** `C₄₂ − G₄₂ = 2.08 − 1.803 = 0.277 → +0.27`. Same structure; **K**.

**8. The freeze contrast, `65 %`.** `(0.40 − 0.14)/0.40 = 0.65`. Both endpoints are the separate
matched pair of runs on `n=5571`; only the `+0.41` the clause names is enrolled.

**9. The affine recalibration, `86 %`.** `(0.431 − 0.060)/0.431 = 0.861 → 86 %`, the MAE gap before
and after a per-group affine map fitted in sample.

**10. The noise-floor factor of five.** `1.70/0.31 = 5.5` and `1.85/0.31 = 6.0`, against the *larger*
functional (the mean over groups backed by three sources). Only the `1.85` endpoint moves; `0.31` is
a property of the corpus.

**11. The deposit count, `22 → 28`.**
Now: `6 arms × 3 seeds = 18` (the five intersecting arms plus the σ-oracle) `+ 4` seed-42 files
(two co-adaptation controls, two output-residual arms) `= 22`.
After: `+4` trained deposits (ungrounded and grounded at seeds 45 and 46) `+2` σ-oracle
re-evaluations (seeds 45, 46) `= 28`. `Twenty-one as first deposited` becomes `twenty-seven`
by the same arithmetic (the one repaired file is still one file). Nine of the standing 22 are
*replaced*, not merely joined: ungrounded, grounded and oracle at 42/43/44.

**12. Per-seed R² for Fig. 2's three enrolled bars** — arithmetic mean and population sd over seeds,
`σ_pop`, not `σ_sample`; the SI states the convention and that a sample sd would be larger by `√(3/2)`
(which becomes `√(5/4)` at five seeds — check the sentence at `sections/SI.tex` **L815–816**).

---

## 3. The order, and why each dependency exists

Discharge strictly downward. Each arrow is a real read-off, not a preference.

```
P0 fetch: seed_*/ per-row CSVs, checkpoints/e5_leakfree/, sigma_train.csv
        │
        ├─► A. certify_leakfree_rerun.py ──────────────────► rows 30,31,32,33 (disposition D)
        │      (the certificate is the evidence the caveats are answered;      row 19 (row lock)
        │       rewriting a caveat before it exists is the failure this        row 1 (leak-free clause)
        │       whole protocol exists to prevent)
        │
        ├─► B. verify_perrow_deposit.py ───────────────────► rows 17, 23 (one number, two copies)
        │                                                    row 19 (per-seed universal)
        │
        └─► C. oracle re-evaluation (followups step 3)
                 └─► D. run_e5_comparison.py per seed  ← the source of record for every arm mean
                          │
                          ├─► E. Table S3 + its four-decimal list  ......................... row 12
                          │        (every derived number in §2 is read off this list, so the
                          │         table must exist before any of §2's substitutions)
                          │        └─► rows 2, 5, 6, 7, 16, 18, 24, 25, 27, 28, 29, 31
                          │
                          ├─► F. make_paradox_figures.py → Fig. 2 ...................... row 8
                          │        └─► row 2's R² sentence reads the figure
                          │
                          ├─► G. make_parity_figure.py --dump-json → Fig. 3 + numbers.json  row 9
                          │        └─► row 3's four OLS slopes are read OFF the figure
                          │
                          ├─► H. rank_final.py, rank_final_floorci.py → Table S19 ....... row 13
                          │        └─► row 3's ranking prose, row 5's ledger row 5
                          │
                          ├─► I. run_external_baseline_comparison.py → table_rows.csv
                          │        └─► transcribe → external_baselines_rows.tex
                          │             └─► re-cut → external_baselines_rows_article.tex   row 10
                          │                  └─► Tables 3 and S17, then the clip-sweep
                          │                       readings of §S4 and §3.7 ............... row 11
                          │
                          ├─► J. row-class split over the per-row CSVs .................. row 15
                          │        └─► row 4's ≈7 solutes; row 22's three maxima
                          │
                          └─► K. chemistry map (run_e5_chemistry_map.py; 17/17 — see §5) row 14
                                   └─► needs row 6's +0.14 to be settled first, since
                                       `sec:map` restates the two arm means it is taken from

then, and only then:
   L. tab:claims / tab:claims-cont2 / tab:runs cells ........... rows 5, 6, 7
        (a table before the caption that states what its rows are)
   M. the seven float captions + the two map captions .......... row 34
   N. the branch-dependent prose: §3.1 heading, Conclusions s.1  rows 35, 36
   O. the TOC graphic (edit the script, then run it) ........... row 26
   P. the abstract, LAST, then wc_abstract.py ................. row 1
```

**Why each ordering constraint exists.**
- **A before 30–33.** The four caveat passages assert that the guard is *not certified*. They may only
  be rewritten once the certificate exists and passes; and the certificate is exactly what P0.2 blocks.
- **B before 17 and 23.** `22 → 28` is an audit result, not an arithmetic guess; the SI states the count
  as the outcome of a pass that *"exits non-zero if any file fails"*.
- **C before D before everything.** `run_e5_comparison.py` locks all three arms to one cross-arm
  intersection. Aggregating two arms and adding the oracle later would produce a *different* lock, and
  the paper's single most-repeated claim is that every arm scores identical rows. Note the trap
  recorded in `GATE_A1_RECORD.md`: the per-seed `comparison.json` currently holds **one arm**, because
  the two arms ran as separate processes and the later overwrote the file. Do not quote it; step 3
  rewrites it with all three arms.
- **E before every derived number.** The `−0.20`, `+0.41`, `+0.14`, `0.59` and the SG contrast are all
  differences of Table S3's unrounded means. Recomputing any of them from rounded cells reintroduces
  the `0.14`-vs-`0.15` defect the SI spends a paragraph on.
- **G before row 3.** §3.2's four slopes are *"read off Fig.~\ref{fig:parity-lnx2}"* — the inventory
  says so in those words. Regenerating the prose from anything but the figure's own `--dump-json`
  would let the figure and the sentence disagree.
- **H before row 5's fifth row.** The ledger cell restates Table S19's intervals; the table is the
  source, the cell is the index.
- **I's three-step chain.** Two floats read **one** source file. `external_baselines_rows_article.tex`
  is cut *from* `external_baselines_rows.tex`, never the other way. Regenerating one and not the other
  is the exact failure the 2026-08-10 pass caught.
- **L after E–I.** A caption that states what its rows are cannot be written before the rows exist.
- **P last.** The abstract is the only display with a hard word ceiling, and its scope clause depends on
  the branch. Edit it after the branch is known, then re-run `wc_abstract.py` and take the script's
  number, not a carried-forward one.

---

## 4. The checks that must pass afterwards

Run in this order. The last one is the one that matters.

**C1 — build both documents, interleaved.**
```bash
cd paper && make clean && make both
```
`make article` or `make si` alone leaves cross-document references printing `??`, and LaTeX calls that
a warning, not an error.

**C2 — undefined references and duplicate labels.**
```bash
cd paper && make check     # == python3 ../scripts/analysis/check_split_refs.py
```
Fails on any undefined reference, any `??` in either PDF, and any label defined in both documents.
The build's exit status does **not** prove the references resolved; this does.

**C3 — number conservation, over the submission as a whole.**
```bash
KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=src python scripts/analysis/check_number_conservation.py \
    --baseline HEAD --allowlist paper/retired_numbers.txt \
    --report results/e5_sigma_grounding_leakfree/number_conservation_after_rerun.txt
```
Use its **default `--tex` arguments** (both roots). Passing a single root compares the article against
a baseline that contained the appendices and reports the whole SI as gone. Every number this discharge
retires — `2.043`, `1.846`, `0.20`, `0.198`, `0.237/0.075/0.281`, `2.0434`, `1.8457`, `2.2517`, `0.40`,
`0.033`, `0.053`, `0.021`, `+0.19`, `+0.33`, `-0.03`, `2.040/1.996/2.093`, `1.803/1.921/1.813`,
`2.232/2.281/2.242`, `twenty-two`, `twenty-one`, and every value in rows 10–15 — must either reappear
in its new form or get a line in `paper/retired_numbers.txt` **naming the artifact it came from**. The
file's own header states the rule: *"Every entry here was checked against the artifact it came from; a
number that is gone for any other reason is a defect, not an entry."*

**C4 — floats and overfull boxes.** Grep both build logs for `Overfull \hbox` and `Overfull \vbox`, and
diff the counts against the pre-substitution build. Three floats are on thin margins and will not
complain audibly if they overflow: `tab:baselines` (tabular 498.75 pt, line 502.08 pt, **2.4 pt of
headroom**, and an over-wide tabular in a centred float does *not* reliably raise an Overfull box —
re-measure with `pdftotext -f 28 -l 28 -bbox-layout`), `tab:si-baselines-full`, and the three ledger
parts (all six block headings are `p`-cells of the tabular's width; a longer caption or cell re-breaks
them). If a five-seed cell is wider than a three-seed one — and `2.1241 ± 0.0540` is wider than
`2.04 ± 0.04` — **re-measure before believing a clean build.**

**C5 — page counts.** Article **33 pp** and SI **S-84** at HEAD `1df7ccd`. Read the new counts off the
build and record them; a five-seed table with a per-seed column of five values will grow, and the
ledger's three parts are already sized to their pages.

**C6 — the re-grep for every retired numeral. This is the one that matters.**
The failure mode of a substitution is not a bad new number; it is a stale copy left behind in a passage
nobody remembered — which is precisely what the inventory's third, fourth and fifth passes each
found once. So, after the substitution, grep **both compiled PDFs** (not the source: macros build
numbers the source does not contain, and commented-out paragraphs contain numbers the reader never
sees) for every retired numeral:

```bash
cd paper && pdftotext grounding_paradox.pdf - > /tmp/a.txt \
         && pdftotext grounding_paradox_si.pdf - > /tmp/s.txt
for v in 2.043 1.846 0.198 2.0434 1.8457 2.2517 1.7950 1.8788 1.7022 \
         0.237 0.075 0.281 2.040 1.996 2.093 1.803 1.921 1.813 \
         2.232 2.281 2.242 0.406 0.428 0.177 ; do
  printf '%-8s article:%s si:%s\n' "$v" \
    "$(grep -c -- "$v" /tmp/a.txt)" "$(grep -c -- "$v" /tmp/s.txt)"
done
```
plus the word-form counts: `three seeds`, `twenty-two`, `twenty-one`, `{42, 43, 44}`, `at every seed`,
`not certified leak-free`, `at each of the three seeds`, `identically at all three seeds`,
`over the three seeds`, `all twenty-two pass`. **Every hit must be either (a) a row of this sheet
already discharged, (b) an explicitly-outside arm — DirectGNN `1.7022`/`1.749`/`1.674`/`1.684`, NRTL
`1.7950`/`1.734`/`1.758`/`1.894`, `grounded_b` `1.8788`/`1.805`/`2.007`/`1.824` — or (c) a K-number
printed beside its five-seed partner.** A hit that is none of the three is a stale copy, and the whole
point of this sheet is that it should be findable in one pass rather than reconstructed.

**C7 — the twin check.** Three consecutive inventory passes found the same class of defect: one copy of
an assertion enrolled and its twin not. Verify by grep that each of these pairs moved **together**:
`twenty-two` (rows 17 and 23); `at every seed` (rows 24 and 25); `three seeds` (rows 19, 20, 21, 22, and
the TOC graphic's second line — see WATCH); the block-1 rows of `tab:baselines` and
`tab:si-baselines-full` (row 10, one source file, two floats); the `+0.41` in §3.1, in `tab:runs`'s third
column and in §3.3's freeze clause (rows 2, 7, 18); the `+0.14` in `tab:claims-cont2`, in `sec:map`'s prose,
in §3.7 and in Table S3's rounding sentence (rows 6, 14, 11, 12).

---

## 5. Enrolled items with no command or no artifact behind them

This is the real output of the sheet. Ordered worst first.

**(1) `sec:map` and Tables S21/S22 — the chemistry maps (row 14). ~~NO ARTIFACT AND NO COMMAND.~~
~~DISCHARGED 2026-08-10 EXCEPT ONE CELL.~~ FULLY DISCHARGED 2026-08-10.** All seventeen printed values
used to occur **only** in `paper/sections/chemistry-map.tex`; a grep of the whole repository returned
that file and nothing else. `scripts/analysis/run_e5_chemistry_map.py` now bins the e5 per-row
predictions by solvent class, solute class and nearest-train Tanimoto and differences the arms, writes
`results/e5_sigma_grounding/chemistry_map.json`, and is gated by `tests/test_e5_chemistry_map.py`.
(`make_map_table_tex.py` / `make_stratified_map_figure.py` remain the *b_insuff* activity-axis map, a
different object on a different axis and a different set.) Fifteen of the seventeen reproduced on the
first pass; **both exceptions were settled the same day and `--check` now reports `19 of 19`.** Nitrile
printed `+0.21` where the data give `+0.20` — a last-digit slip, and **the table was repaired**. And
**Charged / salt `-0.04±0.19` was written off as having no recoverable definition; that write-off is
WITHDRAWN.** The mask that reproduces it (`multifrag_neutral`) was rejected for excluding every
formally charged solute, but in this corpus a formal charge is mostly a nitro group: of 31
formally-charged solutes, 18 have every fragment net-neutral, and the 13 real ions are exactly the
salts written *with* their charges. The mask selects the same chemistry written *without* them —
hydrochlorides, tosylates, a phosphate, a malate, hydrates — which is what the row names. It is the
generator's default now, and the cell has a defined quantity for the five-seed substitution. **A
negative gets the same audit as a positive: this one was banked for less than a day and was already
wrong, and the thing that broke it was enumerating the thirteen molecules it was a claim about.**

**(2) Table S3 (row 12) — NO GENERATOR.** The per-arm table and its four-decimal mean list are the source
of record for six of the eleven derived numbers in §2, and nothing writes them.
`results/e5_sigma_grounding/THREE_SEED_SUMMARY.md` documents the recipe but is itself hand-written.

**(3) The claims ledger (rows 5, 6) — NO GENERATOR.** Three `table*` floats, nineteen rows, six block
heads, all hand-written LaTeX. Every enrolled cell is a hand transcription.

**(4) Table S25, the run-family table (row 7) — NO GENERATOR.** Hand-written; the inventory requires all
three cells of its σ-grounding row to move together.

**(5) The chemistry-map, ledger, run-family and baseline captions (row 34) — NO COMMAND.** Nine captions,
all hand-edited.

**(6) The TOC graphic (row 26) — ARTIFACT-FREE BY CONSTRUCTION.** `make_toc_figure.py` reads no data
file; the caveat is a string literal at L134–137. Re-running the script does **not** discharge the row;
the script must be edited first.

**(7) Every enrolled prose passage — NO COMMAND.** §3.1, §3.2, §3.4, §S4's reading paragraph, §3.7's,
§2.2's noise-floor and disclosure paragraphs, §2.4's row-set paragraph, the compute ledger, the
seeds-and-determinism paragraph, `sec:si-methods`'s two paragraphs, `sec:si-lock`'s two paragraphs, the deposit-recovery
paragraph, §3.3's freeze clause, limitation (xii), §1's sentence, the Conclusions' two sentences, the
abstract. Twenty-one of the thirty-six rows are prose, and every one is a hand transcription from a JSON.
`wc_abstract.py` is the only mechanical gate anywhere in that set, and it checks a word count, not a value.

**(8) Row 15 (the row-class split) and row 22 (the substitution perturbation).**
`run_paradox_channel_split.py` does compute row 15's slice but has **no argparse**, hard-codes an absolute
`ROOT`, and loops over `seed_42` and `seed_43` of the *published* tree only — two seeds, wrong tree. Row
22's three maxima have no script at all.

**(9) Two scripts that exist but cannot be pointed at the new tree without editing:**
`run_external_baseline_comparison.py` (`E5` and `SEEDS` are module constants, L101/L104; only
`--out-dir` is a flag) and `results/e5_sigma_grounding/ranking/rank_final.py` (`REPO`, `BASE`, `SEEDS`
are module constants, L29–36; no argparse, the output directory is `sys.argv[1]`). Both are on the
critical path, and `run_paradox_channel_split.py` (row 15) is a third.

**(10) `make_paradox_figures.py` and `make_parity_figure.py` take one `--e5-dir`** but must draw
re-run arms beside non-re-run ones (Fig. 2 has eight arms, three enrolled; Fig. 3 has four panels, three
enrolled). Either merge the two result trees into one directory or teach the scripts a second root.

---

## WATCH — observations recorded, no action taken

The inventory is settled and is **not** amended by anything here. These are facts about what the
documents print, recorded so that whoever executes the discharge sees them.

- **The TOC graphic prints a seed count.** Its second line reads *"(solubility MAE on held-out
  scaffolds, three seeds; magnitudes in the text)"* (`make_toc_figure.py` L135). The inventory enrols
  the graphic and names *the caveat* as what is removed; the printed `three seeds` is a seed count of
  the kind the fourth and fifth passes were convened to catch. The display is enrolled either way, so
  regenerating it in all three branches reaches this string — but check it explicitly, because the
  enrolment's wording points at line three and the seed count is on line two.
- **The `GATE_A1_RECORD.md` per-seed `comparison.json` files carry one arm, not two**, and their
  `rescue` criterion is vacuous (`--direct-label ungrounded` on a run with no `directgnn` arm). Neither
  is a finding; both are documented in that file. Follow-up step 3 rewrites those files with three arms.
- **`n_acyclic` is 0 and the `acyclic` stratum is empty** in both the published and the leak-free runs.
  It prints as though informative and is not. No enrolled row reads it.
- **Page drift in the inventory's own dated record.** The seeds-and-determinism paragraph resolves to
  **S-78** today, against the **S-77** recorded in the 2026-08-10 fourth-run note. The operative list
  addresses it by `\ref` and paragraph name and resolves correctly; only the parenthetical drifted. Left
  as written, per that record's own rule.
