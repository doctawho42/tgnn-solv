# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Orientation (read these first; do not duplicate their content)

- `PROJECT_DESCRIPTION.md` — the authoritative conceptual/architecture/theory map (why the model exists, the thermodynamics, what is known empirically). Start here.
- `AGENTS.md` — installation, package layout, the full catalogue of canonical CLI commands and config families.
- `PROJECT_MEMORY.md` — 367 KB dated operational log of every experiment/decision; read in slices (`grep '## '` then read relevant dated entries), don't load whole.
- `results/PAPER_PHASE0_FINDINGS.md` — running results log for the current research thread (noise floor, COSMO-SAC, benchmark, conformal, encoder probe, data-efficiency).

When these disagree, trust reproducible artifacts in `results/`/`logs/` and the maintained source over the narrative docs.

**A negative gets the same audit as a positive.** Added 2026-08-06, after four of this project's
refuted claims were re-examined and all four came back *never established* rather than refuted — a
probe that scores an untrained network like a trained one, a grounding pool that was 97.8%
duplicates, an audit stratum whose rows were already molten, and an arm whose three "repair" commits
never touched it. A wrong positive is caught by a referee; a wrong negative closes a direction and is
never looked at again. So before recording that something does not work: run a **null arm** (does the
instrument fire on noise, or on an untrained model?), get a **seed replicate on both arms**, convert
the effect into the units of the claim before comparing it with anything, name the **split** it was
measured on, and distinguish *holds* from *never established*. When a repair lands, cross-date it
against every negative measured before it whose estimand it moves.

## Setup, tests, lint

```bash
pip install -e .                  # editable install (Python >=3.10)
python -m pytest tests/ -q        # full suite (~280 tests)
python -m pytest tests/test_loss.py::test_name -q   # single test
ruff check src tests scripts      # lint (no committed config; defaults)
```

**Critical environment gotcha.** RDKit, PyTorch and scikit-learn each ship their own libomp; importing more than one aborts with `OMP: Error #15 ... libomp already initialized`. `tests/conftest.py` sets `KMP_DUPLICATE_LIB_OK=TRUE` so the suite is fine, **but ad-hoc `python -c`/`python - <<EOF` snippets that import torch+rdkit will crash** — prefix them with `KMP_DUPLICATE_LIB_OK=TRUE`.

**Compute reality.** Development is local (MacBook, MPS/CPU). Local runs are tiny smoke configs (e.g. `--hidden-dim 32 --epochs-phase1 1 ...`) that are **non-converged and produce meaningless metrics** (MAE 3+, R²~0). Do not treat smoke numbers as results; real numbers require a GPU run on the full corpus. Use smoke runs only to verify a code path executes end-to-end.

**COSMO-SAC scoring gotcha: the segment fixed point is a free hyperparameter between fitting and scoring.** `cosmo_sac_gamma_iter_train` (16) and `cosmo_sac_gamma_iter_eval` (30) are *different numbers* (`config.py:185-186`, `configs/cosmo_sac.yaml:34-35`). Today's pair is safe by construction — 16 was chosen in `3a6c3da` precisely because it lands within 6e-5 of 30 — but that convergence is a property of the *weights*, not of the count, so any checkpoint trained at a different count is being scored through an operator it was never fit against. Sweeping the count alone, weights and rows held fixed, moves ln x2 MAE from **1.92 (n=8) to 3.01 (n=300, converged)** and R² from +0.27 to −0.74: a 1.08-wide ln-MAE interval, several times the largest arm gap the project argues about. The retired 2026-06-21 ungrounded run trained at 8 and was scored at 30, and +0.690 of its +0.802 published penalty was that mismatch alone (audited 2026-08-06). **Read both counts out of a run's `model_card.json` before comparing it with anything; score at the count it trained at, or report both.** NRTL has no segment fixed point, so a NRTL-vs-COSMO comparison carries this lever on one side only.

**LaTeX** (`paper/grounding_paradox.tex`, `paper/grounding_paradox_si.tex`) compiles with **XeLaTeX** (`xelatex`, run twice for refs/TOC), main font **STIX Two Text** — CMU Serif / a Cyrillic monospace are NOT installed in this environment, so `\setmonofont{STIX Two Text}`.

## Data preparation (regenerating the processed splits)

`notebooks/data/processed/{train,val,test}.csv` are built from cached raw sources (`notebooks/data/raw/`, e.g. `BigSolDBv2.1.csv`, `bradley_mp.csv`) via:

```bash
python scripts/prepare_data.py --config configs/paper_config_tuned.yaml \
    --split-mode solute_scaffold --seed 42 --skip-download
```

`builder.filter_for_sle` (miscibility/structure/self-solvation, T_m-independent) drives row membership; crystal `T_m`/`dH_fus`, Hansen and γ∞ are merged on as per-solute labels. Two non-obvious traps:
- **The seeded `solute_scaffold` split is NOT stable across pipeline versions.** Regenerating after the data code has changed reshuffles which scaffolds land in test (observed ~76% turnover) — every checkpoint/result computed on the prior split is then orphaned. Treat any regeneration as a *new* split and recompute downstream artifacts; never compare metrics across splits.
- **Melting-point source files may be °C or Kelvin.** `data.sources._melting_points_to_kelvin` auto-detects by column median (a past bug double-converted the already-Kelvin Bradley table → every `T_m` was +273 K too high). `T_m` feeds the ideal term Φ = (ΔH/R)(1/T − 1/T_m), so after any data change sanity-check the distribution (drug-like solids: `has_T_m` median ≈ 410 K, not ≈ 690 K).

## Architecture: the big picture (spans several files)

The thesis is a controlled comparison: does an explicit thermodynamic bottleneck beat the same graph backbone trained directly? Two models share an encoder:

- **`TGNNSolv`** (`src/tgnn_solv/model.py`): `forward` encodes solute+solvent graphs → interaction/readout → **crystal head** (`heads.FusionHead`: predicts `T_m`, `dH_fus` → ideal term Φ(T)) and **activity head** → `solver.SLESolver` solves `ln x2 = -Φ(T) - ln γ2` (a damped fixed point; `IdealSolubilityLayer` + an activity layer) → a bounded "adaptive correction" → `ln_x2`. Returns a large dict (physics intermediates, params, representations).
- **`DirectGNN`** (`src/tgnn_solv/baselines/direct_gnn.py`): same encoder/readout, no solver — emits `ln_x2` directly. **This is the control**, not a throwaway baseline; the TGNN−Direct gap measures the cost/benefit of the physics bottleneck.

Everything is driven by one big dataclass **`config.TGNNSolvConfig`** (`from_yaml` flattens nested `model:`/`training:`/`loss_weights:` sections and silently ignores unknown keys; `--set key=value` on `train.py` overrides any field). Key switches:
- `activity_model`: `"nrtl"` (default) or `"cosmo_sac"`. `nrtl_tau_mode="gamma_inf"` collapses NRTL to a single-parameter symmetric activity. `"cosmo_sac"` swaps in `layers.CosmoSacLayer` (differentiable COSMO-SAC over a predicted σ-profile from `heads.SigmaProfileHead`) — wired through `solver.SLESolver` and `model.forward`; the NRTL path is untouched.
- `branch_training_mode`: `"standard"` or `"coordinate_descent"` (freezes activity/crystal branches by phase).

**Training (`trainer.py`)** is a fixed three-phase curriculum: Phase 1 auxiliary-property pretraining (crystal/Hansen/γ∞; no SLE loss; uses the lightweight `_forward_phase1`), Phase 2 full SLE training, Phase 3 low-LR fine-tuning (monotonicity etc.). `loss.py` is a single weighted sum of ~30 components with per-phase weights (`DEFAULT_PHASE_WEIGHTS`).

**The auxiliary-stream pattern is THE extension mechanism** for external single-component grounding (the project's core research lever — "ground each physical factor with abundant single-component data"). To add a stream, mirror the existing IDAC/crystal/σ-profile streams across these touch points:
1. builder `scripts/data/build_*_aux_stream.py` → a sidecar CSV in processed-dataset format, rows are **self-solvent** (`solvent_smiles = solute_smiles`), `has_solubility=False`, only the target's mask on. **Two mandatory guards, both reported in the build summary.** (a) *Scaffold leak*: exclude pool solutes whose Bemis–Murcko scaffold is in the test/val split (else the scaffold benchmark is invalid). (b) *Net-new count*: report how many pool molecules are not already labelled for that target in train, by canonical SMILES. The E2 crystal pool was **97.76% redundant** — 15,082 of 15,427 molecules already carried a T_m in train, 98.2% of them bit-identical — and the head moved −12.2 K on the 345 net-new against −0.37 K on the duplicates. A stream that is mostly duplicates tests nothing, and the null it produces will be read as "grounding does not help".
2. `src/tgnn_solv/data/dataset.py` parses the new columns/mask in `__getitem__`.
3. `loss.py` adds the loss term/helper.
4. `trainer.py` adds `_train_<x>_aux_batch` + threads a loader through `train_epoch`/`train_phase`/`train_full` + a `config.<x>_aux_steps_per_epoch`.
5. `scripts/train.py` adds `--<x>-train-data/--<x>-steps-per-epoch`.
Reference implementations: crystal pool (`build_crystal_aux_stream.py`, `_train_crystal_aux_batch`) and σ-profiles (`build_sigma_profile_aux_stream.py`, `_train_sigma_aux_batch`).

`scripts/` has both top-level (`scripts/train.py`, verified working) and a grouped surface (`scripts/{data,training,analysis,evaluation,experiments,external}/`). Flat imports (`from tgnn_solv.model import TGNNSolv`) work alongside the grouped `tgnn_solv.*` namespaces.

## Research framing (so you don't optimize the wrong thing)

- On the hard `solute_scaffold` split the physics path trails DirectGNN *in the seed mean*; both ≈ RF. **Do not quote the old "MAE 1.74 vs 1.65" pair** (still in `PROJECT_DESCRIPTION.md` §12): those are two single-seed checkpoints from separate April runs (`checkpoints/proxy/`, 2026-04-13/14) on the split that was rebuilt out from under them on 2026-06-19, and the data-preparation rule above forbids comparing metrics across splits. They also predate the `T_m` +273 K fix (`eb314d8`, 2026-06-20). The measurement of record is `results/e5_sigma_grounding/THREE_SEED_SUMMARY.md` — seeds 42/43/44, intersection-locked to the n=5608 labelled test rows, one shared schedule (`configs/cosmo_sac.yaml`): **DirectGNN 1.702 ± 0.033 against the NRTL closure at 1.795 ± 0.071.** Two apparatus caveats travel with that gap and should travel with any restatement of it: the arms are separately tuned, so the difference is not attributable to the bottleneck alone; and the per-seed values overlap, with the ordering reversing at seed 42 (NRTL 1.734 vs DirectGNN 1.749), so "physics trails" is a property of the seed-mean column, not of the arms at every seed. External SOTA on new-solute extrapolation is **FastSolv** (~0.83–0.95 log10 RMSE) — a *direct black-box* (descriptors+ensembles+cleaner data), while the physics-informed SolProp is behind it. Absolute MAE is near the aleatoric label-noise floor (~0.3–0.7 log10 inter-lab). **Chasing scaffold MAE is near-futile**; the project's value is interpretable decomposition, temperature extrapolation, data-efficiency, calibrated uncertainty, and the identifiability/conditional-optimality theory.
- The crystal/activity split is **structurally non-identifiable** from solubility alone (rank deficiency, closed only by external single-component labels — hence the aux-stream pattern). Two diagnostic caveats. (a) `corr(δΦ, δγ) → −1` *trivially* as `ln x2` fit improves; report `delta_phi_mean` instead (`src/tgnn_solv/diagnostics/compensation.py`). (b) **Stratify every crystal-term audit by whether `T_m` is measured or Joback-predicted** — otherwise the statistic is an extrapolation-distance fact wearing a crystal-chemistry costume. `ln|δΦ| = ln(dCp/R) + ln ψ` identically, and over the 88224 plausible-GC rows `var(ln ψ) = 1.989` against `var(ln dCp) = 0.070`, so ψ (the distance you extrapolate below `T_m`) carries **96.6%** of the spread; dCp is nearly constant at ≈60 J/mol/K across this corpus. Concretely (audited 2026-08-06): the published median |δΦ| of 1.482 ln x2 (`results/dcp_correction_audit/summary.json`) repairs to **0.451**, it was measured on a "near-melting" stratum that was 99.4% Joback `T_m` and — wherever melting was actually known — 100% already molten, everything within 100 K of a measured melting point sits at **≤0.24 ln x2**, and the whole tail past 250 K of extrapolation uses a fabricated `T_m`. So the quantity that needs a guard is **ψ / `T_m_gc`**, not the GC dCp scale (clipping dCp addresses ~26% of the tail); calibrating the GC dCp against measured `dH_fus/T_m` moves the correction by −2%, i.e. nothing.
- A new graph encoder is unlikely to help, and pretraining / better inputs / coverage are the levers — but cite this to the arm comparisons in `results/proxy_comparison`, **not** to the linear probe. **The "transfer-limited, not expressivity-limited" diagnosis is withdrawn (audited 2026-08-06).** The probe cannot support it: an untrained, randomly-initialised encoder of the same architecture scores 0.707/0.415/0.291 against the trained 0.758/0.448/0.310 and is awarded the *identical* verdict by the decision rule at `run_encoder_linear_probe.py:178`; trained-minus-random bootstrap CIs cross zero on all three quantities; a second random seed moves the gap to 0.194 and flips the verdict string, so the 0.25 threshold sits inside its own null's spread; and Gaussian noise features at d=768, n=700 reach train R² 0.979 — higher than the trained encoder, so a high train R² here is ridge geometry. Seed alone moves the gap 0.22 (three DirectGNN checkpoints: 0.602/0.970/0.578). What survives is only that training adds ≈0.11 R² of linear decodability on train solutes and 0.00 ± 0.07 on test. TIMP's failure is an observation, not explained by this. **The encoder question is unmeasured, not closed.**

Analysis surface for these claims lives in `scripts/analysis/run_*` (noise floor, identifiability Fisher audit, compensation, ranking, conformal calibration, encoder linear probe) and `scripts/experiments/run_*` (E2 crystal grounding, E3 temperature extrapolation, E4 ablations, data-efficiency curve).
