# Running the GPU-gated experiments on Kaggle (free T4/P100)

The **code** (with the `--resume-extend` fix) is on the `sigma-grounded-cosmosac` GitHub branch;
the ~23 MB of **processed data** is gitignored, so it rides in as a small Kaggle Dataset. Flow:
upload the data once, then in the notebook *clone → install → run*.

Kaggle gives ~30 GPU-hours/week; a single **Save & Run All** (commit) runs headless up to ~12 h.
The full suite is ~13–19 GPU-h, so **split it across two sessions** (the orchestrator saves each
result as soon as it finishes, so nothing is lost if a session times out).

> Prefer a one-clone flow with no dataset step? Tell me and I'll force-add the 23 MB into the
> branch instead (it's derived from public sources, so it's safe to commit — I just didn't want to
> put data in your repo unasked).

---

## One-time setup

1. **Upload the data as a Kaggle Dataset** (once): <https://www.kaggle.com/datasets> → **New Dataset**
   → drag in `tgnn_gpu_data.tar.gz` (I'll give you the local path) → name it e.g. `tgnn-gpu-data` →
   Create. Note its slug (`your-username/tgnn-gpu-data`).
2. Go to <https://www.kaggle.com/code> → **New Notebook**.
3. Right panel → **Settings**:
   - **Accelerator** → `GPU T4 x2` (or P100).
   - **Internet** → **On** (needed for `git clone` + `pip`).
   - **Add Data** → search your `tgnn-gpu-data` dataset → **Add**.
4. Paste the cells below (replace `<DATASET-SLUG>` with your dataset's folder under `/kaggle/input/`).

---

## Cell 1 — clone, install, sanity-check GPU + data

```python
import torch, subprocess
print("CUDA:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")

!git clone --depth 1 --branch sigma-grounded-cosmosac https://github.com/doctawho42/tgnn-solv.git
%cd tgnn-solv

# Kaggle already has torch; add the two graph/chem deps + install the package (no-deps).
!pip -q install "torch-geometric>=2.4" "rdkit>=2023.9.1" pyyaml
!pip -q install -e . --no-deps

# unpack the attached data (tarball holds processed/, processed_sigma_aux_stream/, processed_crystal_aux_stream/)
!mkdir -p notebooks/data
!tar -xzf /kaggle/input/<DATASET-SLUG>/tgnn_gpu_data.tar.gz -C notebooks/data
!ls -la notebooks/data/processed/train.csv notebooks/data/processed_sigma_aux_stream/sigma_train.csv
```

## Cell 2 — run the experiments

**Session 1** (highest value first — candidate #2 full magnitude, then the closure-fix crossover):

```python
!python scripts/cloud/kaggle_run.py --do onemodel,tier3 --out /kaggle/working/results --device cuda
```

**Session 2** (a second notebook run, later — the secondary hardening):

```python
!python scripts/cloud/kaggle_run.py --do dataeff,dosed --out /kaggle/working/results --device cuda
```

Or everything at once if you think it fits your window: `--do all`. Trim budgets with e.g.
`--sle 80 --t3-ep2 80 --t3-arm-ep2 40` if you need it shorter.

## Cell 3 — package results for download

```python
!cd /kaggle/working && tar -czf results.tar.gz results && ls -la results.tar.gz
```

Then **Save Version → Save & Run All (Commit)** so it runs headless. When it finishes, open the
version’s **Output** tab and download `results.tar.gz` (and the `.png` figures under `results/`).

---

## What each experiment produces

| `--do` | Output | The claim it settles |
|---|---|---|
| `onemodel` | `results/compensation/isolation_gpu.json` + `fig_compensation_surrogate.*` | Full-magnitude candidate-#2: one model, σ̂ drifts off the grounded profile under SLE (closes the smoke 16%→82% caveat in `sec:surrogate`). |
| `tier3` | `results/closure_fix/tier3_crossover.json` + `fig_closure_fix_deformation.*` | The closure-fix crossover on a **working** full-SLE base (the resume-extend fix makes the arms actually train): does Arm C beat Arm I at matched K. |
| `dataeff` | `results/data_efficiency_multiseed.json` | Multi-seed physics−direct gap per fraction (blind-review Major 3 error bars). |
| `dosed` | `results/e2_dosed/comparison.json` | M4b: is the crystal-null dose-limited? |

## Bring the results home

Send me `results.tar.gz` (or paste the key JSONs). I run the local analyzers/paper edits:
- `onemodel` → update the `sec:surrogate` caveat with the converged magnitude.
- `tier3` → `analyze_closure_fix.py` already ran on Kaggle; I fold the crossover verdict + figure in.
- `dataeff` / `dosed` → the data-efficiency table and crystal-null section.

## If something breaks

- `pip install -e .` fails → re-run Cell 1; Kaggle occasionally needs `pip install --upgrade pip` first.
- OOM → drop to a single GPU (`GPU T4 x1`) and/or trim budgets (`--sle 60 --t3-ep2 60`).
- Session times out mid-suite → the `results/kaggle_run_log.json` shows what finished; re-run with
  `--do <the-unfinished-ones>`.
