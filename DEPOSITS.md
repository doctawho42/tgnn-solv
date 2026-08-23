# Where every printed number comes from

A number in a paper that a reader cannot open is a number they have to take on trust. This maps the
manuscript's claims to the artifact each was computed from, the script that regenerates it, and the
gate that fails the build if the two stop agreeing.

**Paths in this file are checked.** `verify.sh` asserts that every artifact and script named below
exists, so this document cannot quietly rot the way the documentation site did.

## How the three layers fit

- **`results/…`** — the deposits. Most of `results/` is local scratch; the tracked subset is
  curated, and `.gitignore` carries a comment for every whitelisted artifact explaining *why that
  one* is versioned. Read those comments before adding or removing anything there.
- **`scripts/analysis/run_*.py`** — the analyses. Each writes a deposit and is re-runnable.
- **`scripts/analysis/check_*.py`** — the gates. Each re-reads a deposit and compares it against
  what the manuscript prints. `./verify.sh` runs all eight.

Anything too large to version — the per-row prediction files (~5 MB each) and the bulk analysis
artifacts — goes to the Zenodo archive whose DOI is registered at submission. See
`ZENODO_DEPOSIT.md`.

## The claims and their artifacts

### The decomposition — MSE, the input-insufficiency bound, the closure bound

The keystone. `B_insuff ∈ [0, MSE]`, margin = `MSE − 2·B_insuff`, `B_clos_lb = MSE − B_insuff`.

| what | artifact |
|---|---|
| the n=60 VT-2005-matched pairs, with targets and both closure conventions | `results/b_insuff/matched_pairs.csv` |
| the headline decomposition | `results/b_insuff/decomposition.json` |
| the stratified map and its admissibility | `results/b_insuff/stratified_map_table.csv`, `results/b_insuff/admissibility.json` |
| the binning-convention enumeration | `results/b_insuff/binning_conventions.json` |
| the input-fixed kernel control | `results/b_insuff/fidelity_lever_inputfixed.json` |
| the cross-fitted map | `results/b_insuff/crossfit_map.json` |

**Every number here names an estimator cell**: bins × bin edges × variance convention (ddof) ×
combinatorial convention (full or residual-only) × unit (row or pair). The headline cell is 8
equal-count bins, unbiased within-bin variance, row unit, residual-only. A value quoted without its
cell is not checkable — `results/b_insuff/binning_conventions.json` exists to show how far the
answer moves across cells.

Gates: `check_hand_transcribed_displays.py`, `check_deviation_paragraph.py`,
`check_vt2005_leverage_counts.py`.

### The arms — what the physics bottleneck costs

| what | artifact |
|---|---|
| the five-seed leak-free re-run (the measurement of record) | `results/e5_sigma_grounding_leakfree/GATE_A1_RECORD.md`, per-seed `comparison_both_arms.json` |
| the published three-seed family | `results/e5_sigma_grounding/THREE_SEED_SUMMARY.md`, per-seed `comparison.json` |
| which run family produced which number, and at how many seeds | `results/e5_sigma_grounding/ROW_SET_DECOMPOSITION.md` |
| solvent ranking, floors, recalibration | `results/e5_sigma_grounding/ranking/rank_final.json` and its `_oos` / `_floorci` companions |

The arms are separately tuned. The difference between them is therefore not attributable to the
bottleneck alone, and the manuscript says so wherever it quotes the gap.

### The mechanism — what fine-tuning does to the learned σ-profile

| what | artifact | producer |
|---|---|---|
| three-seed drift, transfer ratio, ladder rungs | `results/sur/surrogate_seeds/surrogate_seeds.json` | `scripts/analysis/run_compensation_surrogate.py` |
| the structured null the top-two share is read against | `results/compensation/evr_structured_null.json` | `scripts/analysis/run_evr_structured_null.py` |
| the constant-offset control on the transfer | `results/compensation/offset_control.json` | `scripts/analysis/run_surrogate_offset_control.py` |
| the two-MSE cancellation check | `results/compensation/two_mse_check.json` | `scripts/analysis/run_surrogate_two_mse.py` |
| the closure's own-axis hydrogen-bond sweep | `results/b_insuff/closure_validation.json` | `scripts/analysis/run_closure_validation.py` |

Two scope limits travel with this section and are stated in it: the structured null is measured on
the σ̂-versus-reference deviation of a grounded checkpoint, **not** on the fine-tuning drift the
headline share describes; and the whole section sits at infinite dilution, so its transfer to the
finite-composition regime that generates the drift is not established.

`run_evr_structured_null.py` at its defaults scores a *different* checkpoint from the deposited
one. Pass `--checkpoint results/closure_fix/ckpt/arm_base.pt` to reproduce the deposit, and read
`results/compensation/EVR_NULL_REVISION_2026-07-26.md` for why.

### The external comparison

| what | artifact |
|---|---|
| this work against FastSolv and SolProp, re-run and as published | `results/external_baseline_comparison/summary.json`, `table_rows.csv` |
| the deployed closure against a published evaluation of the same closure | `results/published_idac_check/summary.json`, `scored_records.csv` |

The blocks may not be read across: this work is on the solute-scaffold split, the external models
were re-run here on an easier by-solute split. The table fixes a scale; it does not rank anything.

### Everything else the manuscript prints

| claim | artifact |
|---|---|
| data-efficiency curve | `results/data_efficiency/summary.json` |
| the σ-profile reference tabulation | `results/sigma_profile_artifact/sigma_profiles.csv` |
| the group-contribution ΔCp audit | `results/dcp_correction_audit/summary.json` |
| fusion-label scarcity | `results/fusion_supervision_audit/summary.json` |
| temperature extrapolation | `results/temperature_extrapolation_baselines/summary.json` |
| the corrupted-twin identifiability demonstration | `results/proxy_corrupted_twin/twin_vs_corrected_comparison.json` |
| solver iteration-count sensitivity | `results/b_insuff/iteration_count_sweep.json` |
| the σ-stream rebuild equivalence | `results/stream_equivalence.json` |

### Frozen pre-declarations

`results/b_insuff/glycol_oos_thermoml/` holds a pre-registration written and hashed **before** the
outcome it governs was computed. `scripts/analysis/run_glycol_oos_margin.py` gates on the sha256 of
those files.

**Never edit them, and never repoint a commit hash inside them** — a remap is an edit, and it
breaks the gate that gives the pre-declaration its force. The mapping from the pre-rewrite hashes to
the current ones lives beside them in `COMMIT_HASHES_AFTER_HISTORY_REWRITE.md`.

## Retired numbers

`paper/retired_numbers.txt` records every value deliberately removed from the manuscript, with the
reason. `check_number_conservation.py --allowlist paper/retired_numbers.txt` fails if a value
disappears without an entry, which is how a number that quietly stopped being printed gets caught.
